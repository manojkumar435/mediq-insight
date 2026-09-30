import sqlite3
import json
from datetime import datetime
import os

class DatabaseHandler:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                user_type TEXT NOT NULL,
                full_name TEXT,
                phone TEXT,
                date_of_birth TEXT,
                gender TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                report_file TEXT NOT NULL,
                report_text TEXT,
                lab_values TEXT,
                metadata TEXT,
                analysis_result TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS doctor_patient_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER NOT NULL,
                patient_id INTEGER NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doctor_id) REFERENCES users (id),
                FOREIGN KEY (patient_id) REFERENCES users (id),
                UNIQUE(doctor_id, patient_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_user(self, email, password, user_type, full_name=None, phone=None, date_of_birth=None, gender=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (email, password, user_type, full_name, phone, date_of_birth, gender)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (email, password, user_type, full_name, phone, date_of_birth, gender))
            
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return {'success': True, 'user_id': user_id}
        except sqlite3.IntegrityError:
            conn.close()
            return {'success': False, 'error': 'Email already exists'}
    
    def authenticate_user(self, email, password):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, user_type, full_name FROM users
            WHERE email = ? AND password = ?
        ''', (email, password))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'success': True,
                'user': {
                    'id': user[0],
                    'email': user[1],
                    'user_type': user[2],
                    'full_name': user[3]
                }
            }
        else:
            return {'success': False, 'error': 'Invalid credentials'}
    
    def get_user_by_id(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, user_type, full_name, phone, date_of_birth, gender, created_at
            FROM users WHERE id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'email': user[1],
                'user_type': user[2],
                'full_name': user[3],
                'phone': user[4],
                'date_of_birth': user[5],
                'gender': user[6],
                'created_at': user[7]
            }
        return None
    
    def save_report(self, user_id, report_file, report_text, lab_values, metadata, analysis_result):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reports (user_id, report_file, report_text, lab_values, metadata, analysis_result)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            report_file,
            report_text,
            json.dumps(lab_values),
            json.dumps(metadata),
            json.dumps(analysis_result)
        ))
        
        conn.commit()
        report_id = cursor.lastrowid
        conn.close()
        
        return report_id
    
    def get_user_reports(self, user_id, limit=10):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, report_file, lab_values, metadata, analysis_result, uploaded_at
            FROM reports
            WHERE user_id = ?
            ORDER BY uploaded_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        reports = cursor.fetchall()
        conn.close()
        
        result = []
        for report in reports:
            result.append({
                'id': report[0],
                'report_file': report[1],
                'lab_values': json.loads(report[2]) if report[2] else {},
                'metadata': json.loads(report[3]) if report[3] else {},
                'analysis_result': json.loads(report[4]) if report[4] else {},
                'uploaded_at': report[5]
            })
        
        return result
    
    def get_report_by_id(self, report_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_id, report_file, report_text, lab_values, metadata, analysis_result, uploaded_at
            FROM reports
            WHERE id = ?
        ''', (report_id,))
        
        report = cursor.fetchone()
        conn.close()
        
        if report:
            return {
                'id': report[0],
                'user_id': report[1],
                'report_file': report[2],
                'report_text': report[3],
                'lab_values': json.loads(report[4]) if report[4] else {},
                'metadata': json.loads(report[5]) if report[5] else {},
                'analysis_result': json.loads(report[6]) if report[6] else {},
                'uploaded_at': report[7]
            }
        return None
    
    def assign_patient_to_doctor(self, doctor_id, patient_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO doctor_patient_mapping (doctor_id, patient_id)
                VALUES (?, ?)
            ''', (doctor_id, patient_id))
            
            conn.commit()
            conn.close()
            return {'success': True}
        except sqlite3.IntegrityError:
            conn.close()
            return {'success': False, 'error': 'Mapping already exists'}
    
    def get_doctor_patients(self, doctor_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.id, u.email, u.full_name, u.phone, u.date_of_birth, u.gender
            FROM users u
            INNER JOIN doctor_patient_mapping dpm ON u.id = dpm.patient_id
            WHERE dpm.doctor_id = ?
        ''', (doctor_id,))
        
        patients = cursor.fetchall()
        conn.close()
        
        result = []
        for patient in patients:
            result.append({
                'id': patient[0],
                'email': patient[1],
                'full_name': patient[2],
                'phone': patient[3],
                'date_of_birth': patient[4],
                'gender': patient[5]
            })
        
        return result
    
    def get_patient_doctors(self, patient_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.id, u.email, u.full_name, u.phone
            FROM users u
            INNER JOIN doctor_patient_mapping dpm ON u.id = dpm.doctor_id
            WHERE dpm.patient_id = ?
        ''', (patient_id,))
        
        doctors = cursor.fetchall()
        conn.close()
        
        result = []
        for doctor in doctors:
            result.append({
                'id': doctor[0],
                'email': doctor[1],
                'full_name': doctor[2],
                'phone': doctor[3]
            })
        
        return result
    
    def get_patient_reports_for_doctor(self, doctor_id, patient_id, limit=10):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.id, r.report_file, r.lab_values, r.metadata, r.analysis_result, r.uploaded_at
            FROM reports r
            INNER JOIN doctor_patient_mapping dpm ON r.user_id = dpm.patient_id
            WHERE dpm.doctor_id = ? AND r.user_id = ?
            ORDER BY r.uploaded_at DESC
            LIMIT ?
        ''', (doctor_id, patient_id, limit))
        
        reports = cursor.fetchall()
        conn.close()
        
        result = []
        for report in reports:
            result.append({
                'id': report[0],
                'report_file': report[1],
                'lab_values': json.loads(report[2]) if report[2] else {},
                'metadata': json.loads(report[3]) if report[3] else {},
                'analysis_result': json.loads(report[4]) if report[4] else {},
                'uploaded_at': report[5]
            })
        
        return result
    
    def search_users_by_email(self, email_query, user_type=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_type:
            cursor.execute('''
                SELECT id, email, full_name, user_type
                FROM users
                WHERE email LIKE ? AND user_type = ?
                LIMIT 10
            ''', (f'%{email_query}%', user_type))
        else:
            cursor.execute('''
                SELECT id, email, full_name, user_type
                FROM users
                WHERE email LIKE ?
                LIMIT 10
            ''', (f'%{email_query}%',))
        
        users = cursor.fetchall()
        conn.close()
        
        result = []
        for user in users:
            result.append({
                'id': user[0],
                'email': user[1],
                'full_name': user[2],
                'user_type': user[3]
            })
        
        return result
    
    def delete_report(self, report_id, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM reports
            WHERE id = ? AND user_id = ?
        ''', (report_id, user_id))
        
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        
        return deleted