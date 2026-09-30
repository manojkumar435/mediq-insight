import re
from datetime import datetime
from config import Config

class ReportAnalyzer:
    def __init__(self, quantum_model):
        self.quantum_model = quantum_model
        self.lab_ranges = Config.LAB_RANGES
    
    def analyze_report(self, report_text, lab_values, user_type='patient'):
        quantum_analysis = self.quantum_model.analyze_lab_report(report_text, lab_values)
        
        abnormal_values = self.detect_abnormal_values(lab_values)
        
        if user_type == 'patient':
            interpretation = self.generate_patient_summary(
                lab_values, 
                abnormal_values, 
                quantum_analysis
            )
        else:
            interpretation = self.generate_doctor_summary(
                lab_values, 
                abnormal_values, 
                quantum_analysis
            )
        
        return {
            'interpretation': interpretation,
            'abnormal_values': abnormal_values,
            'quantum_analysis': quantum_analysis,
            'severity': quantum_analysis['complexity_level'],
            'timestamp': datetime.now().isoformat()
        }
    
    def detect_abnormal_values(self, lab_values):
        abnormal = []
        
        for test_name, value in lab_values.items():
            if test_name in self.lab_ranges:
                range_info = self.lab_ranges[test_name]
                
                try:
                    numeric_value = float(value)
                    
                    if numeric_value < range_info['min']:
                        status = 'Low'
                        severity = self._calculate_severity(
                            numeric_value, 
                            range_info['min'], 
                            range_info['max'], 
                            'low'
                        )
                    elif numeric_value > range_info['max']:
                        status = 'High'
                        severity = self._calculate_severity(
                            numeric_value, 
                            range_info['min'], 
                            range_info['max'], 
                            'high'
                        )
                    else:
                        continue
                    
                    abnormal.append({
                        'test': test_name,
                        'value': numeric_value,
                        'status': status,
                        'severity': severity,
                        'normal_range': f"{range_info['min']}-{range_info['max']} {range_info['unit']}",
                        'unit': range_info['unit']
                    })
                except ValueError:
                    continue
        
        abnormal.sort(key=lambda x: x['severity'], reverse=True)
        return abnormal
    
    def _calculate_severity(self, value, min_val, max_val, direction):
        if direction == 'low':
            deviation = (min_val - value) / min_val
        else:
            deviation = (value - max_val) / max_val
        
        if deviation > 0.5:
            return 'Critical'
        elif deviation > 0.2:
            return 'Moderate'
        else:
            return 'Mild'
    
    def generate_patient_summary(self, lab_values, abnormal_values, quantum_analysis):
        summary = {
            'overview': '',
            'key_findings': [],
            'recommendations': [],
            'next_steps': ''
        }
        
        if not abnormal_values:
            summary['overview'] = "Great news! All your lab results are within normal ranges. This indicates good overall health."
            summary['recommendations'] = [
                "Continue maintaining your current healthy lifestyle",
                "Keep up with regular check-ups as recommended by your doctor",
                "Stay hydrated and maintain a balanced diet"
            ]
            summary['next_steps'] = "Schedule a routine follow-up as per your doctor's advice."
        else:
            critical_count = sum(1 for v in abnormal_values if v['severity'] == 'Critical')
            moderate_count = sum(1 for v in abnormal_values if v['severity'] == 'Moderate')
            
            if critical_count > 0:
                summary['overview'] = f"Your lab report shows {critical_count} critical finding(s) that require immediate medical attention. Please consult your doctor as soon as possible."
            elif moderate_count > 0:
                summary['overview'] = f"Your lab report shows {moderate_count} value(s) outside normal range. These should be discussed with your doctor during your next visit."
            else:
                summary['overview'] = "Your lab report shows some minor variations from normal ranges. These are typically not concerning but should be monitored."
            
            for abnormal in abnormal_values[:5]:
                finding = self._patient_friendly_explanation(abnormal)
                summary['key_findings'].append(finding)
            
            summary['recommendations'] = self._generate_patient_recommendations(abnormal_values)
            summary['next_steps'] = self._generate_patient_next_steps(abnormal_values)
        
        return summary
    
    def generate_doctor_summary(self, lab_values, abnormal_values, quantum_analysis):
        summary = {
            'clinical_overview': '',
            'abnormal_findings': [],
            'clinical_significance': [],
            'recommendations': [],
            'quantum_insights': quantum_analysis
        }
        
        summary['clinical_overview'] = f"Analysis reveals {len(abnormal_values)} abnormal value(s). Quantum-enhanced analysis indicates {quantum_analysis['complexity_level']} complexity case."
        
        for abnormal in abnormal_values:
            finding = {
                'parameter': abnormal['test'],
                'value': f"{abnormal['value']} {abnormal['unit']}",
                'status': abnormal['status'],
                'severity': abnormal['severity'],
                'normal_range': abnormal['normal_range'],
                'clinical_note': self._clinical_interpretation(abnormal)
            }
            summary['abnormal_findings'].append(finding)
        
        summary['clinical_significance'] = self._generate_clinical_significance(abnormal_values)
        summary['recommendations'] = self._generate_clinical_recommendations(abnormal_values)
        
        return summary
    
    def _patient_friendly_explanation(self, abnormal):
        test = abnormal['test']
        status = abnormal['status']
        severity = abnormal['severity']
        
        explanations = {
            'WBC': {
                'High': f"Your white blood cell count is {status.lower()}. This could indicate an infection or inflammation in your body.",
                'Low': f"Your white blood cell count is {status.lower()}. This might make you more susceptible to infections."
            },
            'RBC': {
                'High': f"Your red blood cell count is {status.lower()}. This could affect oxygen delivery in your body.",
                'Low': f"Your red blood cell count is {status.lower()}. This might cause fatigue or weakness (anemia)."
            },
            'Hemoglobin': {
                'High': f"Your hemoglobin level is {status.lower()}. This affects how oxygen is carried in your blood.",
                'Low': f"Your hemoglobin level is {status.lower()}. This can cause tiredness and weakness (anemia)."
            },
            'Glucose': {
                'High': f"Your blood sugar level is {status.lower()}. This needs monitoring as it relates to diabetes risk.",
                'Low': f"Your blood sugar level is {status.lower()}. You may experience dizziness or weakness."
            },
            'Cholesterol': {
                'High': f"Your cholesterol level is {status.lower()}. This is a risk factor for heart disease.",
                'Low': f"Your cholesterol level is {status.lower()}."
            }
        }
        
        default_msg = f"Your {test} level is {status.lower()} (Severity: {severity}). Please discuss this with your doctor."
        
        return explanations.get(test, {}).get(status, default_msg)
    
    def _clinical_interpretation(self, abnormal):
        test = abnormal['test']
        status = abnormal['status']
        
        interpretations = {
            'WBC': {
                'High': 'Leukocytosis - Consider infection, inflammation, leukemia, or stress response',
                'Low': 'Leukopenia - Evaluate for bone marrow disorders, autoimmune conditions, or medication effects'
            },
            'RBC': {
                'High': 'Polycythemia - Rule out dehydration, lung disease, or polycythemia vera',
                'Low': 'Anemia - Investigate iron deficiency, B12/folate deficiency, or chronic disease'
            },
            'Glucose': {
                'High': 'Hyperglycemia - Screen for diabetes mellitus, assess HbA1c',
                'Low': 'Hypoglycemia - Evaluate insulin levels, rule out insulinoma'
            },
            'Creatinine': {
                'High': 'Elevated creatinine - Assess renal function, calculate GFR',
                'Low': 'Low muscle mass or decreased protein intake'
            }
        }
        
        return interpretations.get(test, {}).get(status, f'{test} {status} - Clinical correlation advised')
    
    def _generate_patient_recommendations(self, abnormal_values):
        recommendations = []
        
        critical = any(v['severity'] == 'Critical' for v in abnormal_values)
        
        if critical:
            recommendations.append("⚠️ Contact your doctor immediately to discuss these results")
            recommendations.append("Do not delay medical attention for critical values")
        else:
            recommendations.append("Schedule an appointment with your doctor to review these results")
        
        test_types = [v['test'] for v in abnormal_values]
        
        if any(t in ['Glucose', 'Cholesterol', 'Triglycerides'] for t in test_types):
            recommendations.append("Focus on a balanced diet low in sugar and saturated fats")
            recommendations.append("Regular exercise can help improve these values")
        
        if 'WBC' in test_types:
            recommendations.append("Ensure adequate rest and avoid exposure to infections")
        
        recommendations.append("Follow any medications prescribed by your doctor")
        recommendations.append("Stay hydrated and maintain a healthy lifestyle")
        
        return recommendations
    
    def _generate_patient_next_steps(self, abnormal_values):
        critical = any(v['severity'] == 'Critical' for v in abnormal_values)
        moderate = any(v['severity'] == 'Moderate' for v in abnormal_values)
        
        if critical:
            return "Urgent: Contact your doctor within 24 hours or visit emergency care if you have symptoms."
        elif moderate:
            return "Important: Schedule a follow-up appointment with your doctor within 1-2 weeks."
        else:
            return "Routine: Discuss these results during your next scheduled check-up."
    
    def _generate_clinical_significance(self, abnormal_values):
        significance = []
        
        test_groups = {
            'hematology': ['WBC', 'RBC', 'Hemoglobin', 'Hematocrit', 'Platelets'],
            'metabolic': ['Glucose', 'Creatinine', 'BUN'],
            'hepatic': ['ALT', 'AST'],
            'lipid': ['Cholesterol', 'Triglycerides', 'HDL', 'LDL'],
            'thyroid': ['TSH', 'T3', 'T4']
        }
        
        for group_name, tests in test_groups.items():
            affected = [v for v in abnormal_values if v['test'] in tests]
            if affected:
                significance.append(f"{group_name.capitalize()} panel shows {len(affected)} abnormality(ies)")
        
        return significance
    
    def _generate_clinical_recommendations(self, abnormal_values):
        recommendations = []
        
        critical = [v for v in abnormal_values if v['severity'] == 'Critical']
        if critical:
            recommendations.append(f"Immediate intervention required for {len(critical)} critical value(s)")
            recommendations.append("Consider hospitalization or urgent outpatient management")
        
        recommendations.append("Obtain detailed clinical history and physical examination")
        recommendations.append("Consider additional diagnostic workup based on abnormal findings")
        recommendations.append("Repeat testing in 1-2 weeks to assess trend")
        recommendations.append("Review current medications and adjust as necessary")
        
        return recommendations
    
    def compare_reports(self, current_values, previous_values):
        comparison = {
            'improved': [],
            'worsened': [],
            'stable': [],
            'new_abnormal': []
        }
        
        for test, current_val in current_values.items():
            if test in previous_values:
                prev_val = previous_values[test]
                try:
                    curr_num = float(current_val)
                    prev_num = float(prev_val)
                    
                    change_percent = ((curr_num - prev_num) / prev_num) * 100
                    
                    if abs(change_percent) < 5:
                        comparison['stable'].append({
                            'test': test,
                            'current': curr_num,
                            'previous': prev_num,
                            'change': change_percent
                        })
                    elif change_percent > 0:
                        if test in self.lab_ranges:
                            if curr_num > self.lab_ranges[test]['max']:
                                comparison['worsened'].append({
                                    'test': test,
                                    'current': curr_num,
                                    'previous': prev_num,
                                    'change': change_percent
                                })
                            else:
                                comparison['improved'].append({
                                    'test': test,
                                    'current': curr_num,
                                    'previous': prev_num,
                                    'change': change_percent
                                })
                    else:
                        if test in self.lab_ranges:
                            if curr_num < self.lab_ranges[test]['min']:
                                comparison['worsened'].append({
                                    'test': test,
                                    'current': curr_num,
                                    'previous': prev_num,
                                    'change': change_percent
                                })
                            else:
                                comparison['improved'].append({
                                    'test': test,
                                    'current': curr_num,
                                    'previous': prev_num,
                                    'change': change_percent
                                })
                except ValueError:
                    continue
        
        return comparison