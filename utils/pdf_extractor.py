import PyPDF2
import re
from datetime import datetime

class PDFExtractor:
    def __init__(self):
        self.common_tests = [
            'WBC', 'RBC', 'Hemoglobin', 'Hematocrit', 'Platelets',
            'Glucose', 'Creatinine', 'BUN', 'ALT', 'AST',
            'Cholesterol', 'Triglycerides', 'HDL', 'LDL',
            'TSH', 'T3', 'T4'
        ]
    
    def extract_from_pdf(self, pdf_path):
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                
                metadata = self.extract_metadata(text)
                lab_values = self.extract_lab_values(text)
                
                return {
                    'success': True,
                    'text': text,
                    'metadata': metadata,
                    'lab_values': lab_values,
                    'num_pages': len(pdf_reader.pages)
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def extract_metadata(self, text):
        metadata = {
            'patient_name': None,
            'patient_id': None,
            'date': None,
            'hospital': None,
            'doctor': None
        }
        
        name_patterns = [
            r'Patient\s*Name\s*[:\-]?\s*([A-Za-z\s]+)',
            r'Name\s*[:\-]?\s*([A-Za-z\s]+)',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['patient_name'] = match.group(1).strip()
                break
        
        id_patterns = [
            r'Patient\s*ID\s*[:\-]?\s*([A-Z0-9]+)',
            r'MRN\s*[:\-]?\s*([A-Z0-9]+)',
            r'ID\s*[:\-]?\s*([A-Z0-9]+)'
        ]
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['patient_id'] = match.group(1).strip()
                break
        
        date_patterns = [
            r'Date\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'Report\s*Date\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                metadata['date'] = match.group(1).strip()
                break
        
        hospital_patterns = [
            r'Hospital\s*[:\-]?\s*([A-Za-z\s&]+)',
            r'Laboratory\s*[:\-]?\s*([A-Za-z\s&]+)',
            r'Clinic\s*[:\-]?\s*([A-Za-z\s&]+)'
        ]
        for pattern in hospital_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                hospital_name = match.group(1).strip()
                if len(hospital_name) > 5:
                    metadata['hospital'] = hospital_name
                    break
        
        doctor_patterns = [
            r'Dr\.\s*([A-Za-z\s]+)',
            r'Physician\s*[:\-]?\s*([A-Za-z\s]+)',
            r'Doctor\s*[:\-]?\s*([A-Za-z\s]+)'
        ]
        for pattern in doctor_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['doctor'] = match.group(1).strip()
                break
        
        return metadata
    
    def extract_lab_values(self, text):
        lab_values = {}
        
        lines = text.split('\n')
        
        for test_name in self.common_tests:
            patterns = [
                rf'{test_name}\s*[:\-]?\s*([\d.]+)',
                rf'{test_name}\s+(\d+\.?\d*)',
                rf'{test_name.upper()}\s*[:\-]?\s*([\d.]+)',
                rf'{test_name.lower()}\s*[:\-]?\s*([\d.]+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        value = float(matches[0])
                        lab_values[test_name] = value
                        break
                    except ValueError:
                        continue
        
        alternative_names = {
            'White Blood Cell': 'WBC',
            'White Blood Cells': 'WBC',
            'Leukocytes': 'WBC',
            'Red Blood Cell': 'RBC',
            'Red Blood Cells': 'RBC',
            'Erythrocytes': 'RBC',
            'Hb': 'Hemoglobin',
            'HGB': 'Hemoglobin',
            'HCT': 'Hematocrit',
            'PLT': 'Platelets',
            'Blood Sugar': 'Glucose',
            'Fasting Blood Sugar': 'Glucose',
            'FBS': 'Glucose',
            'Total Cholesterol': 'Cholesterol',
            'Alanine Aminotransferase': 'ALT',
            'SGPT': 'ALT',
            'Aspartate Aminotransferase': 'AST',
            'SGOT': 'AST',
            'Blood Urea Nitrogen': 'BUN',
        }
        
        for alt_name, standard_name in alternative_names.items():
            if standard_name not in lab_values:
                pattern = rf'{alt_name}\s*[:\-]?\s*([\d.]+)'
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        value = float(matches[0])
                        lab_values[standard_name] = value
                    except ValueError:
                        continue
        
        return lab_values
    
    def validate_lab_values(self, lab_values):
        validated = {}
        
        reasonable_ranges = {
            'WBC': (0, 50000),
            'RBC': (0, 10),
            'Hemoglobin': (0, 25),
            'Hematocrit': (0, 100),
            'Platelets': (0, 1000000),
            'Glucose': (0, 500),
            'Creatinine': (0, 20),
            'BUN': (0, 200),
            'ALT': (0, 1000),
            'AST': (0, 1000),
            'Cholesterol': (0, 500),
            'Triglycerides': (0, 1000),
            'HDL': (0, 150),
            'LDL': (0, 400),
            'TSH': (0, 100),
            'T3': (0, 500),
            'T4': (0, 50)
        }
        
        for test, value in lab_values.items():
            if test in reasonable_ranges:
                min_val, max_val = reasonable_ranges[test]
                if min_val <= value <= max_val:
                    validated[test] = value
        
        return validated
    
    def extract_additional_info(self, text):
        info = {
            'clinical_notes': [],
            'test_method': None,
            'reference_lab': None
        }
        
        lines = text.split('\n')
        
        note_keywords = ['note', 'comment', 'remark', 'observation']
        for line in lines:
            if any(keyword in line.lower() for keyword in note_keywords):
                if len(line.strip()) > 10:
                    info['clinical_notes'].append(line.strip())
        
        method_pattern = r'Method\s*[:\-]?\s*([A-Za-z\s]+)'
        match = re.search(method_pattern, text, re.IGNORECASE)
        if match:
            info['test_method'] = match.group(1).strip()
        
        lab_pattern = r'Reference\s*Lab\s*[:\-]?\s*([A-Za-z\s&]+)'
        match = re.search(lab_pattern, text, re.IGNORECASE)
        if match:
            info['reference_lab'] = match.group(1).strip()
        
        return info