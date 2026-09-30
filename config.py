import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mediq-insight-secret-key-2025'
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'pdf'}
    
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'mediq.db')
    
    BIOBERT_MODEL = 'dmis-lab/biobert-v1.1'
    N_QUBITS = 6
    QUANTUM_LAYERS = 2
    
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    LAB_RANGES = {
        'WBC': {'min': 4000, 'max': 11000, 'unit': '/μL'},
        'RBC': {'min': 4.5, 'max': 5.9, 'unit': 'million/μL'},
        'Hemoglobin': {'min': 13.5, 'max': 17.5, 'unit': 'g/dL'},
        'Hematocrit': {'min': 38.8, 'max': 50.0, 'unit': '%'},
        'Platelets': {'min': 150000, 'max': 400000, 'unit': '/μL'},
        'Glucose': {'min': 70, 'max': 100, 'unit': 'mg/dL'},
        'Creatinine': {'min': 0.7, 'max': 1.3, 'unit': 'mg/dL'},
        'BUN': {'min': 7, 'max': 20, 'unit': 'mg/dL'},
        'ALT': {'min': 7, 'max': 56, 'unit': 'U/L'},
        'AST': {'min': 10, 'max': 40, 'unit': 'U/L'},
        'Cholesterol': {'min': 125, 'max': 200, 'unit': 'mg/dL'},
        'Triglycerides': {'min': 0, 'max': 150, 'unit': 'mg/dL'},
        'HDL': {'min': 40, 'max': 60, 'unit': 'mg/dL'},
        'LDL': {'min': 0, 'max': 100, 'unit': 'mg/dL'},
        'TSH': {'min': 0.4, 'max': 4.0, 'unit': 'mIU/L'},
        'T3': {'min': 80, 'max': 200, 'unit': 'ng/dL'},
        'T4': {'min': 4.5, 'max': 12.0, 'unit': 'μg/dL'},
    }
    
    @staticmethod
    def init_app(app):
        pass