# MediQ-Insight

MediQ-Insight is a medical lab report interpretation system designed to extract, analyze, and present information from medical laboratory reports in an understandable format.

## Key Features

- Upload and process medical lab reports in PDF format
- Extract laboratory values from reports
- Analyze report content using BioBERT-based semantic processing
- Quantum-enhanced embedding approach for semantic analysis
- Identify and interpret abnormal laboratory values
- Separate patient and doctor dashboards
- Compare current and previous lab reports
- Patient-doctor communication system
- Store and manage analyzed reports

## Technologies Used

- Python
- Flask
- BioBERT
- PyTorch
- Transformers
- Qiskit
- PyPDF2
- HTML
- CSS
- JavaScript

## Project Structure

- `app.py` - Main Flask application
- `models/` - BioBERT and report analysis modules
- `utils/` - PDF extraction and lab parsing
- `database/` - Database and chat handling
- `templates/` - HTML templates
- `static/` - CSS, JavaScript and other static resources
- `config.py` - Application configuration

## Installation

Clone the repository:

git clone https://github.com/manojkumar435/mediq-insight.git

Install the required packages:

pip install -r requirements.txt

Run the application:

python app.py

Then open the local Flask server in your browser.

## Author

**Manoj Kumar R**

B.Tech Computer Science and Engineering
