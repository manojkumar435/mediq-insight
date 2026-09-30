import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector
import warnings
warnings.filterwarnings('ignore')

class QuantumEmbeddingLayer(nn.Module):
    def __init__(self, input_dim=768, n_qubits=6, n_layers=2):
        super().__init__()
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.input_dim = input_dim
        
        self.classical_projection = nn.Linear(input_dim, n_qubits)
        self.quantum_params = nn.Parameter(torch.randn(n_layers, n_qubits, 3))
        
        self.simulator = AerSimulator(method='statevector')
    
    def create_quantum_circuit(self, input_features, params):
        qc = QuantumCircuit(self.n_qubits)
        
        for i in range(self.n_qubits):
            qc.ry(input_features[i].item() * np.pi, i)
        
        for layer in range(self.n_layers):
            for i in range(self.n_qubits):
                qc.rx(params[layer, i, 0].item(), i)
                qc.ry(params[layer, i, 1].item(), i)
                qc.rz(params[layer, i, 2].item(), i)
            
            for i in range(self.n_qubits - 1):
                qc.cx(i, i + 1)
            if self.n_qubits > 1:
                qc.cx(self.n_qubits - 1, 0)
        
        return qc
    
    def forward(self, x):
        batch_size, seq_len, _ = x.shape
        
        projected = self.classical_projection(x)
        projected = torch.tanh(projected)
        
        quantum_features = []
        
        for b in range(batch_size):
            batch_quantum = []
            for s in range(seq_len):
                qc = self.create_quantum_circuit(projected[b, s], self.quantum_params)
                
                statevector = Statevector.from_instruction(qc)
                amplitudes = statevector.data
                
                probs = np.abs(amplitudes) ** 2
                phases = np.angle(amplitudes)
                
                quantum_feature = np.concatenate([probs, phases])
                
                batch_quantum.append(quantum_feature)
            quantum_features.append(batch_quantum)
        
        quantum_tensor = torch.tensor(quantum_features, dtype=torch.float32, device=x.device)
        
        return quantum_tensor

class QuantumBioBERT(nn.Module):
    def __init__(self, model_name='dmis-lab/biobert-v1.1', n_qubits=6):
        super().__init__()
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.biobert = AutoModel.from_pretrained(model_name)
        
        self.quantum_layer = QuantumEmbeddingLayer(
            input_dim=768,
            n_qubits=n_qubits,
            n_layers=2
        )
        
        self.fusion_layer = nn.Linear(768 + (2 ** (n_qubits + 1)), 768)
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.to(self.device)
    
    def forward(self, input_ids, attention_mask):
        biobert_output = self.biobert(input_ids=input_ids, attention_mask=attention_mask)
        embeddings = biobert_output.last_hidden_state
        
        quantum_features = self.quantum_layer(embeddings)
        
        classical_pooled = embeddings.mean(dim=1)
        quantum_pooled = quantum_features.mean(dim=1)
        
        combined = torch.cat([classical_pooled, quantum_pooled], dim=1)
        
        fused = self.fusion_layer(combined)
        
        return fused
    
    def encode_text(self, text):
        inputs = self.tokenizer(
            text,
            return_tensors='pt',
            max_length=512,
            truncation=True,
            padding='max_length'
        )
        
        input_ids = inputs['input_ids'].to(self.device)
        attention_mask = inputs['attention_mask'].to(self.device)
        
        with torch.no_grad():
            features = self.forward(input_ids, attention_mask)
        
        return features

class QuantumBioBERTAnalyzer:
    def __init__(self, model_name='dmis-lab/biobert-v1.1', n_qubits=6):
        self.model = QuantumBioBERT(model_name=model_name, n_qubits=n_qubits)
        self.model.eval()
    
    def analyze_lab_report(self, report_text, lab_values):
        features = self.model.encode_text(report_text)
        
        feature_norm = torch.norm(features).item()
        severity_score = min(feature_norm / 10.0, 1.0)
        
        analysis = {
            'quantum_magnitude': feature_norm,
            'severity_score': severity_score,
            'complexity_level': self._get_complexity_level(severity_score)
        }
        
        return analysis
    
    def _get_complexity_level(self, score):
        if score > 0.7:
            return 'High'
        elif score > 0.4:
            return 'Moderate'
        else:
            return 'Low'
    
    def generate_embeddings(self, text):
        features = self.model.encode_text(text)
        return features.cpu().numpy()