import re
from datetime import datetime

class LabParser:
    def __init__(self):
        self.unit_mapping = {
            'WBC': ['/μL', '/uL', 'cells/μL', 'K/μL'],
            'RBC': ['million/μL', 'M/μL', 'million/uL'],
            'Hemoglobin': ['g/dL', 'g/dl', 'gm/dL'],
            'Hematocrit': ['%', 'percent'],
            'Platelets': ['/μL', '/uL', 'K/μL'],
            'Glucose': ['mg/dL', 'mg/dl'],
            'Creatinine': ['mg/dL', 'mg/dl'],
            'BUN': ['mg/dL', 'mg/dl'],
            'ALT': ['U/L', 'IU/L'],
            'AST': ['U/L', 'IU/L'],
            'Cholesterol': ['mg/dL', 'mg/dl'],
            'Triglycerides': ['mg/dL', 'mg/dl'],
            'HDL': ['mg/dL', 'mg/dl'],
            'LDL': ['mg/dL', 'mg/dl'],
            'TSH': ['mIU/L', 'μIU/mL'],
            'T3': ['ng/dL', 'ng/dl'],
            'T4': ['μg/dL', 'ug/dL']
        }
    
    def parse_lab_line(self, line):
        line = line.strip()
        
        test_pattern = r'([A-Za-z\s]+?)\s*[:\-]?\s*([\d.]+)\s*([A-Za-z/μ%]+)?'
        match = re.match(test_pattern, line)
        
        if match:
            test_name = match.group(1).strip()
            value = match.group(2)
            unit = match.group(3) if match.group(3) else None
            
            return {
                'test': test_name,
                'value': float(value),
                'unit': unit,
                'raw_line': line
            }
        
        return None
    
    def normalize_test_name(self, test_name):
        test_name = test_name.strip().upper()
        
        normalization_map = {
            'WHITE BLOOD CELL': 'WBC',
            'WHITE BLOOD CELLS': 'WBC',
            'LEUKOCYTES': 'WBC',
            'RED BLOOD CELL': 'RBC',
            'RED BLOOD CELLS': 'RBC',
            'ERYTHROCYTES': 'RBC',
            'HB': 'HEMOGLOBIN',
            'HGB': 'HEMOGLOBIN',
            'HCT': 'HEMATOCRIT',
            'PLT': 'PLATELETS',
            'BLOOD SUGAR': 'GLUCOSE',
            'FASTING BLOOD SUGAR': 'GLUCOSE',
            'FBS': 'GLUCOSE',
            'TOTAL CHOLESTEROL': 'CHOLESTEROL',
            'ALANINE AMINOTRANSFERASE': 'ALT',
            'SGPT': 'ALT',
            'ASPARTATE AMINOTRANSFERASE': 'AST',
            'SGOT': 'AST',
            'BLOOD UREA NITROGEN': 'BUN'
        }
        
        if test_name in normalization_map:
            return normalization_map[test_name]
        
        return test_name
    
    def convert_units(self, test_name, value, from_unit, to_unit):
        conversion_factors = {
            ('Glucose', 'mmol/L', 'mg/dL'): 18.0,
            ('Cholesterol', 'mmol/L', 'mg/dL'): 38.67,
            ('Triglycerides', 'mmol/L', 'mg/dL'): 88.57,
            ('Creatinine', 'μmol/L', 'mg/dL'): 0.0113,
        }
        
        key = (test_name, from_unit, to_unit)
        
        if key in conversion_factors:
            return value * conversion_factors[key]
        
        return value
    
    def parse_date(self, date_string):
        date_formats = [
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%m-%d-%Y',
            '%Y-%m-%d',
            '%d %b %Y',
            '%d %B %Y',
            '%b %d, %Y',
            '%B %d, %Y'
        ]
        
        for date_format in date_formats:
            try:
                return datetime.strptime(date_string.strip(), date_format)
            except ValueError:
                continue
        
        return None
    
    def extract_reference_ranges(self, text):
        ranges = {}
        
        range_pattern = r'([A-Za-z\s]+?)\s*[:\-]?\s*([\d.]+)\s*[-–]\s*([\d.]+)\s*([A-Za-z/μ%]+)?'
        
        matches = re.finditer(range_pattern, text)
        
        for match in matches:
            test_name = self.normalize_test_name(match.group(1))
            min_val = float(match.group(2))
            max_val = float(match.group(3))
            unit = match.group(4) if match.group(4) else None
            
            ranges[test_name] = {
                'min': min_val,
                'max': max_val,
                'unit': unit
            }
        
        return ranges
    
    def categorize_tests(self, lab_values):
        categories = {
            'Complete Blood Count': ['WBC', 'RBC', 'Hemoglobin', 'Hematocrit', 'Platelets'],
            'Metabolic Panel': ['Glucose', 'Creatinine', 'BUN'],
            'Liver Function': ['ALT', 'AST'],
            'Lipid Panel': ['Cholesterol', 'Triglycerides', 'HDL', 'LDL'],
            'Thyroid Function': ['TSH', 'T3', 'T4']
        }
        
        categorized = {}
        
        for category, tests in categories.items():
            category_values = {}
            for test in tests:
                if test in lab_values:
                    category_values[test] = lab_values[test]
            
            if category_values:
                categorized[category] = category_values
        
        other_tests = {}
        all_categorized_tests = [test for tests in categories.values() for test in tests]
        for test, value in lab_values.items():
            if test not in all_categorized_tests:
                other_tests[test] = value
        
        if other_tests:
            categorized['Other Tests'] = other_tests
        
        return categorized
    
    def validate_report_completeness(self, lab_values):
        validation = {
            'is_complete': False,
            'missing_tests': [],
            'coverage_percentage': 0
        }
        
        essential_tests = ['WBC', 'RBC', 'Hemoglobin', 'Platelets', 'Glucose']
        
        found_tests = sum(1 for test in essential_tests if test in lab_values)
        validation['coverage_percentage'] = (found_tests / len(essential_tests)) * 100
        
        validation['missing_tests'] = [test for test in essential_tests if test not in lab_values]
        
        validation['is_complete'] = validation['coverage_percentage'] >= 60
        
        return validation
    
    def detect_flags(self, test_name, value, normal_ranges):
        if test_name not in normal_ranges:
            return None
        
        range_info = normal_ranges[test_name]
        
        if value < range_info['min']:
            deviation = ((range_info['min'] - value) / range_info['min']) * 100
            if deviation > 50:
                return 'CRITICAL LOW'
            elif deviation > 20:
                return 'LOW'
            else:
                return 'BORDERLINE LOW'
        elif value > range_info['max']:
            deviation = ((value - range_info['max']) / range_info['max']) * 100
            if deviation > 50:
                return 'CRITICAL HIGH'
            elif deviation > 20:
                return 'HIGH'
            else:
                return 'BORDERLINE HIGH'
        else:
            return 'NORMAL'
    
    def generate_summary_statistics(self, lab_values, normal_ranges):
        stats = {
            'total_tests': len(lab_values),
            'normal': 0,
            'abnormal': 0,
            'critical': 0,
            'abnormal_tests': []
        }
        
        for test, value in lab_values.items():
            flag = self.detect_flags(test, value, normal_ranges)
            
            if flag == 'NORMAL':
                stats['normal'] += 1
            elif flag and 'CRITICAL' in flag:
                stats['critical'] += 1
                stats['abnormal'] += 1
                stats['abnormal_tests'].append({'test': test, 'value': value, 'flag': flag})
            elif flag and flag != 'NORMAL':
                stats['abnormal'] += 1
                stats['abnormal_tests'].append({'test': test, 'value': value, 'flag': flag})
        
        return stats