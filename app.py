from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from config import Config
from database.db_handler import DatabaseHandler
from database.chat_handler import ChatHandler
from models.quantum_biobert import QuantumBioBERTAnalyzer
from models.report_analyzer import ReportAnalyzer
from utils.pdf_extractor import PDFExtractor
from utils.lab_parser import LabParser

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)

db = DatabaseHandler(Config.DATABASE_PATH)
chat_handler = ChatHandler(Config.DATABASE_PATH)
pdf_extractor = PDFExtractor()
lab_parser = LabParser()

print("Loading Quantum BioBERT model...")
quantum_model = QuantumBioBERTAnalyzer(model_name=Config.BIOBERT_MODEL, n_qubits=Config.N_QUBITS)
report_analyzer = ReportAnalyzer(quantum_model)
print("Model loaded successfully!")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if 'user_id' in session:
        if session['user_type'] == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        else:
            return redirect(url_for('patient_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        result = db.authenticate_user(email, password)
        
        if result['success']:
            session['user_id'] = result['user']['id']
            session['email'] = result['user']['email']
            session['user_type'] = result['user']['user_type']
            session['full_name'] = result['user']['full_name']
            
            if result['user']['user_type'] == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        date_of_birth = request.form.get('date_of_birth')
        gender = request.form.get('gender')
        
        result = db.create_user(email, password, user_type, full_name, phone, date_of_birth, gender)
        
        if result['success']:
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash(result['error'], 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/patient/dashboard')
def patient_dashboard():
    if 'user_id' not in session or session['user_type'] != 'patient':
        return redirect(url_for('login'))
    
    reports = db.get_user_reports(session['user_id'], limit=10)
    doctors = db.get_patient_doctors(session['user_id'])
    unread_count = chat_handler.get_unread_count(session['user_id'])
    
    return render_template('patient_dashboard.html', 
                         reports=reports, 
                         doctors=doctors,
                         unread_count=unread_count,
                         user=session)

@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'user_id' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('login'))
    
    patients = db.get_doctor_patients(session['user_id'])
    unread_count = chat_handler.get_unread_count(session['user_id'])
    
    return render_template('doctor_dashboard.html', 
                         patients=patients,
                         unread_count=unread_count,
                         user=session)

@app.route('/upload_report', methods=['POST'])
def upload_report():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    if 'report_file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['report_file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{session['user_id']}_{timestamp}_{filename}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        extraction_result = pdf_extractor.extract_from_pdf(filepath)
        
        if not extraction_result['success']:
            return jsonify({'success': False, 'error': 'Failed to extract PDF content'})
        
        report_text = extraction_result['text']
        lab_values = extraction_result['lab_values']
        metadata = extraction_result['metadata']
        
        lab_values = pdf_extractor.validate_lab_values(lab_values)
        
        user_type = 'patient' if session['user_type'] == 'patient' else 'doctor'
        analysis_result = report_analyzer.analyze_report(report_text, lab_values, user_type)
        
        report_id = db.save_report(
            session['user_id'],
            filename,
            report_text,
            lab_values,
            metadata,
            analysis_result
        )
        
        return jsonify({
            'success': True,
            'report_id': report_id,
            'analysis': analysis_result
        })
    
    return jsonify({'success': False, 'error': 'Invalid file type'})

@app.route('/get_report/<int:report_id>')
def get_report(report_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    report = db.get_report_by_id(report_id)
    
    if not report:
        return jsonify({'success': False, 'error': 'Report not found'})
    
    if session['user_type'] == 'patient':
        if report['user_id'] != session['user_id']:
            return jsonify({'success': False, 'error': 'Unauthorized'})
    elif session['user_type'] == 'doctor':
        patients = db.get_doctor_patients(session['user_id'])
        patient_ids = [p['id'] for p in patients]
        if report['user_id'] not in patient_ids:
            return jsonify({'success': False, 'error': 'Unauthorized'})
    
    return jsonify({'success': True, 'report': report})

@app.route('/compare_reports', methods=['POST'])
def compare_reports():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    current_report_id = request.json.get('current_report_id')
    previous_report_id = request.json.get('previous_report_id')
    
    current_report = db.get_report_by_id(current_report_id)
    previous_report = db.get_report_by_id(previous_report_id)
    
    if not current_report or not previous_report:
        return jsonify({'success': False, 'error': 'Reports not found'})
    
    comparison = report_analyzer.compare_reports(
        current_report['lab_values'],
        previous_report['lab_values']
    )
    
    return jsonify({'success': True, 'comparison': comparison})

@app.route('/chat')
def chat_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conversations = chat_handler.get_conversations(session['user_id'])
    
    return render_template('chat.html', 
                         conversations=conversations,
                         user=session)

@app.route('/chat/<int:other_user_id>')
def chat_with_user(other_user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    messages = chat_handler.get_messages(session['user_id'], other_user_id)
    chat_handler.mark_messages_as_read(session['user_id'], other_user_id)
    
    other_user = db.get_user_by_id(other_user_id)
    
    return render_template('chat.html',
                         messages=messages,
                         other_user=other_user,
                         user=session)

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    receiver_id = request.json.get('receiver_id')
    message = request.json.get('message')
    
    if not receiver_id or not message:
        return jsonify({'success': False, 'error': 'Missing parameters'})
    
    result = chat_handler.send_message(session['user_id'], receiver_id, message)
    
    return jsonify(result)

@app.route('/')
def root():
    return redirect(url_for('login'))

@app.route('/get_messages/<int:other_user_id>')
def get_messages(other_user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    messages = chat_handler.get_messages(session['user_id'], other_user_id)
    chat_handler.mark_messages_as_read(session['user_id'], other_user_id)
    
    return jsonify({'success': True, 'messages': messages})

@app.route('/assign_patient', methods=['POST'])
def assign_patient():
    if 'user_id' not in session or session['user_type'] != 'doctor':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    patient_email = request.json.get('patient_email')
    
    patients = db.search_users_by_email(patient_email, 'patient')
    
    if not patients:
        return jsonify({'success': False, 'error': 'Patient not found'})
    
    patient_id = patients[0]['id']
    
    result = db.assign_patient_to_doctor(session['user_id'], patient_id)
    
    return jsonify(result)

@app.route('/get_patient_reports/<int:patient_id>')
def get_patient_reports(patient_id):
    if 'user_id' not in session or session['user_type'] != 'doctor':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    reports = db.get_patient_reports_for_doctor(session['user_id'], patient_id)
    
    return jsonify({'success': True, 'reports': reports})

@app.route('/delete_report/<int:report_id>', methods=['DELETE'])
def delete_report(report_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    deleted = db.delete_report(report_id, session['user_id'])
    
    if deleted:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to delete report'})

@app.route('/search_users')
def search_users():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    query = request.args.get('query', '')
    user_type = request.args.get('user_type')
    
    users = db.search_users_by_email(query, user_type)
    
    return jsonify({'success': True, 'users': users})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)