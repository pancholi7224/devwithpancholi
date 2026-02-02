import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import os
from datetime import datetime
import sqlite3
import json
import threading
import time
import re
import requests
from flask import Flask, request, jsonify, send_from_directory, Response
from flask import render_template_string
import base64
import tempfile

# Try to import pdfkit, if not available we'll use alternative methods
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False
    print("pdfkit not available. Using alternative PDF generation.")

# Alternative PDF generation using weasyprint - handle import error
try:
    # Check if we're on Windows
    import platform
    if platform.system() == 'Windows':
        # On Windows, weasyprint requires GTK which is difficult to install
        # So we'll skip it and use alternative methods
        WEASYPRINT_AVAILABLE = False
        print("WeasyPrint not recommended on Windows. Using alternative methods.")
    else:
        from weasyprint import HTML
        WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("weasyprint not available. Using HTML fallback.")
except Exception as e:
    WEASYPRINT_AVAILABLE = False
    print(f"Error importing weasyprint: {e}. Using alternative methods.")

# Import for HTML to PDF alternative
import sys

class PathologyTestsForm(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("UJJIVAN Hospital Pathology System Launcher")
        self.geometry("600x400")
        self.configure(bg="#f0e1c6")
        
        # Create necessary directories first
        os.makedirs('reports/completed_reports', exist_ok=True)
        
        # Initialize database
        self.init_database()
        
        # WhatsApp API Configuration
        self.whatsapp_api_url = "https://graph.facebook.com/v17.0/"
        self.whatsapp_phone_number_id = "YOUR_PHONE_NUMBER_ID"
        self.whatsapp_access_token = "YOUR_ACCESS_TOKEN"
        self.whatsapp_web_url = "https://web.whatsapp.com/send?phone={phone}&text={message}"
        
        # Store current report data
        self.current_patient_data = {}
        self.current_selected_tests = []
        
        # Test normal ranges dictionary
        self.normal_ranges = {
            "Glucose (F)/RI": "70-110 mg/dl",
            "Post Prandial / after 2 Hrs": "Up to 140 mg/dl",
            "HbA1c": "4.5-6.5 %",
            "Urea": "10-40 mg/dl",
            "Creatinine": "0.6-1.4 mg/dl",
            "S. Uric Acid": "2.8-7.0 mg/dl",
            "BUN": "5-20 mg/dl",
            "Cholesterol": "150-200 mg/dl",
            "Triglyceride": "0-170 mg/dl",
            "HDL": "30-96 (F)/30-70 (M) mg/dl",
            "LDL": "<100 mg/dl",
            "Bilirubin Total": "0.1-1.2 mg/dl",
            "Bilirubin (Conjugated)": "0.0-0.3 mg/dl",
            "Bilirubin (Unconjugated)": "0.1-1.0 mg/dl",
            "SGOT/AST": "0-35 U/L",
            "SGPT/ALT": "0-40 U/L",
            "Alk. Phosphatase": "175-575 U/L",
            "Total Protein": "6.5-8.0 gm/dl",
            "Albumin": "3.5-5.0 gm/dl",
            "Globulin": "2.3-3.5 gm/dl",
            "A/G Ratio": "1.0-2.5",
            "GGT": "8-60 U/L",
            "S. Calcium": "8.8-11.0 mg/dl",
            "S. Sodium": "138-148 meq/l",
            "S. Potassium": "3.8-4.8 meq/l",
            "Urine Protein (24 Hrs)": "24-120 mg/24 Hrs",
            "Urine micro protein (albumin)": "28-150 mg/24 Hrs",
            "CK-MB": "0-24 U/L",
            "S. Phosphorous": "2.7-4.5 mg/dl",
            "S. Amylase": "0-110 U/L",
            "TROP-T": "Negative",
            "Haemoglobin": "14-18 gm% (M)/12-15 gm% (F)",
            "Total leukocyte count": "4000-10,000/cu mm",
            "Differential WBC count - Polymorphs": "40-75%",
            "Differential WBC count - Lymphocytes": "20-45%",
            "Differential WBC count - Eosinophils": "1-6%",
            "Differential WBC count - Monocytes": "0-10%",
            "Differential WBC count - Basophiles": "0-1%",
            "AEC": "40-500 No/cu mm",
            "E.S.R. (Westergren)": "0-12 mm (F), 0-10 mm (M)",
            "Platelet Count": "1.5-4.5 lac/cu mm",
            "RBC Count": "F=3.5-5.0, M=4.2-5.5 million/cu mm",
            "Reticulocyte count": "2-5% of RBC",
            "Haematocrit/PCV": "M=39-49%, F=33-43%",
            "MCV": "76-100 fl",
            "MCH": "29.5 ± 2.5 pg",
            "MCHC": "32.5 ± 2.5 gm/dl",
            "Malaria Parasite": "Negative",
            "BLOOD GROUP": "Rh = Positive/Negative",
            "Bleeding Time": "2-7 Min.",
            "Clotting Time": "6 Min.",
            "Prothrombin Time": "10-14 Sec.",
            "PERIPHERAL BLOOD SMEAR - RBC": "Normal morphology",
            "PERIPHERAL BLOOD SMEAR - WBC": "Normal morphology",
            "PERIPHERAL BLOOD SMEAR - PLATELET": "Adequate",
            "PERIPHERAL BLOOD SMEAR - HAEMOPARASITE": "Negative",
            "HbsAg": "Negative",
            "HIV (1+2)": "Negative",
            "HCV": "Negative",
            "VDRL": "Non-reactive",
            "ASO Titer": "<200 IU/ml",
            "R.A. factor": "<20 IU/ml",
            "CRP": "<6 mg/L",
            "Gravindex (PREGNANCY)": "Negative",
            "WIDAL TEST - S. Typhi, 'O'": "Negative (<1:80)",
            "WIDAL TEST - S. Typhi, 'H'": "Negative (<1:160)",
            "WIDAL TEST - S. Paratyphi, 'AH'": "Negative (<1:80)",
            "WIDAL TEST - S. Paratyphi, 'BH'": "Negative (<1:80)",
            "Dengue NS1": "Negative",
            "Typhi Dot": "Negative"
        }
        
        # Start Flask server for handling form submissions
        self.flask_app = Flask(__name__)
        self.setup_flask_routes()
        self.start_flask_server()
        
        # Main title
        title_label = tk.Label(self, text="UJJIVAN HOSPITAL PATHOLOGY SYSTEM", 
                              font=("Arial", 20, "bold"), bg="#f0e1c6", fg="#003366")
        title_label.pack(pady=(20,10))
        
        subtitle_label = tk.Label(self, text="Vidyut Nagar, Gautam Budh Nagar, Uttar Pradesh - 201008", 
                                 font=("Arial", 12), bg="#f0e1c6")
        subtitle_label.pack(pady=(0,20))

        # Info text
        info_label = tk.Label(self, text="This system will open in your web browser\nwhere you can fill patient information and select tests", 
                             font=("Arial", 12), bg="#f0e1c6", justify=tk.CENTER)
        info_label.pack(pady=(0,30))

        # Launch button
        launch_btn = tk.Button(self, text="🚀 Launch Web Application", 
                              fg="white", bg="#28a745", font=("Arial", 16, "bold"), 
                              command=self.launch_web_app, height=3, width=25)
        launch_btn.pack(pady=(0, 20))

        # Status label
        self.status_label = tk.Label(self, text="Ready to launch...", 
                                   font=("Arial", 10), bg="#f0e1c6", fg="#666")
        self.status_label.pack(pady=(10,5))

        # Pathology tests data
        self.tests = {
            "BIOCHEMISTRY": [
                "Glucose (F)/RI", "Post Prandial / after 2 Hrs", "HbA1c"
            ],
            "RENAL FUNCTION": [
                "Urea", "Creatinine", "S. Uric Acid", "BUN"
            ],
            "LIPID PROFILE": [
                "Cholesterol", "Triglyceride", "HDL", "LDL"
            ],
            "LIVER FUNCTION": [
                "Bilirubin Total", "Bilirubin (Conjugated)", "Bilirubin (Unconjugated)", 
                "SGOT/AST", "SGPT/ALT", "Alk. Phosphatase", "Total Protein", 
                "Albumin", "Globulin", "A/G Ratio", "GGT"
            ],
            "ELECTROLYTES": [
                "S. Calcium", "S. Sodium", "S. Potassium"
            ],
            "OTHER TESTS": [
                "Urine Protein (24 Hrs)", "Urine micro protein (albumin)", 
                "CK-MB", "S. Phosphorous", "S. Amylase", "TROP-T"
            ],
            "HAEMATOLOGY": [
                "Haemoglobin", "Total leukocyte count", "Differential WBC count - Polymorphs",
                "Differential WBC count - Lymphocytes", "Differential WBC count - Eosinophils",
                "Differential WBC count - Monocytes", "Differential WBC count - Basophiles",
                "AEC", "E.S.R. (Westergren)", "Platelet Count", "RBC Count", 
                "Reticulocyte count", "Haematocrit/PCV", "MCV", "MCH", "MCHC",
                "Malaria Parasite", "BLOOD GROUP", "Bleeding Time", "Clotting Time",
                "Prothrombin Time", "PERIPHERAL BLOOD SMEAR - RBC", 
                "PERIPHERAL BLOOD SMEAR - WBC", "PERIPHERAL BLOOD SMEAR - PLATELET",
                "PERIPHERAL BLOOD SMEAR - HAEMOPARASITE"
            ],
            "SEROLOGY": [
                "HbsAg", "HIV (1+2)", "HCV", "VDRL", "ASO Titer", "R.A. factor", 
                "CRP", "Gravindex (PREGNANCY)", "WIDAL TEST - S. Typhi, 'O'",
                "WIDAL TEST - S. Typhi, 'H'", "WIDAL TEST - S. Paratyphi, 'AH'",
                "WIDAL TEST - S. Paratyphi, 'BH'", "Dengue NS1", "Typhi Dot"
            ]
        }

    def init_database(self):
        """Initialize SQLite database for storing reports"""
        try:
            self.conn = sqlite3.connect('pathology_reports.db', check_same_thread=False)
            self.cursor = self.conn.cursor()
            
            # Create table for form submissions
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS form_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_name TEXT,
                    patient_age TEXT,
                    patient_gender TEXT,
                    patient_mobile TEXT,
                    doctor_name TEXT,
                    opd_no TEXT,
                    sample_date TEXT,
                    selected_tests TEXT,
                    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create table for completed reports
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS completed_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_name TEXT,
                    patient_age TEXT,
                    patient_gender TEXT,
                    patient_mobile TEXT,
                    doctor_name TEXT,
                    opd_no TEXT,
                    sample_date TEXT,
                    test_results TEXT,
                    pdf_path TEXT,
                    whatsapp_status TEXT,
                    whatsapp_error TEXT,
                    report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.conn.commit()
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Error initializing database: {e}")

    def setup_flask_routes(self):
        """Setup Flask routes for handling form submissions and file serving"""
        
        # HTML template for main web form
        MAIN_WEB_FORM = '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>UJJIVAN HOSPITAL PATHOLOGY TESTS</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {
                    background: #f0e1c6;
                    font-family: Arial, sans-serif;
                    padding: 20px;
                }
                .hospital-header {
                    background: white;
                    border: 2px solid #003366;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                .main-title {
                    color: #003366;
                    font-weight: bold;
                    text-align: center;
                    margin-bottom: 5px;
                }
                .subtitle {
                    text-align: center;
                    color: #666;
                    margin-bottom: 20px;
                }
                .form-section {
                    background: white;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .section-title {
                    background: #003366;
                    color: white;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 15px 0;
                    font-weight: bold;
                }
                .test-category {
                    background: #e8f0ff;
                    border-left: 4px solid #003366;
                    padding: 15px;
                    margin-bottom: 15px;
                    border-radius: 5px;
                }
                .test-checkbox {
                    margin: 5px 0;
                }
                .btn-generate {
                    background: #28a745;
                    color: white;
                    font-weight: bold;
                    padding: 15px 30px;
                    font-size: 18px;
                    border: none;
                    border-radius: 10px;
                    width: 100%;
                    margin-top: 20px;
                }
                .btn-generate:hover {
                    background: #218838;
                }
                .patient-info-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                }
                @media (max-width: 768px) {
                    .patient-info-grid {
                        grid-template-columns: 1fr;
                    }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="hospital-header">
                    <h1 class="main-title">UJJIVAN HOSPITAL PATHOLOGY TESTS</h1>
                    <p class="subtitle">Vidyut Nagar, Gautam Budh Nagar, Uttar Pradesh - 201008</p>
                    
                    <div class="form-section">
                        <h3 style="color: #003366; margin-bottom: 20px;">📋 Generate Fillable Form</h3>
                        
                        <div class="patient-info-grid">
                            <div>
                                <h5>Patient Information</h5>
                                <div class="mb-3">
                                    <label class="form-label">Patient Name *</label>
                                    <input type="text" class="form-control" id="patientName" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Age *</label>
                                    <input type="text" class="form-control" id="patientAge" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Gender *</label>
                                    <select class="form-control" id="patientGender" required>
                                        <option value="">Select Gender</option>
                                        <option value="Male">Male</option>
                                        <option value="Female">Female</option>
                                        <option value="Other">Other</option>
                                    </select>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Mobile *</label>
                                    <input type="tel" class="form-control" id="patientMobile" required>
                                </div>
                            </div>
                            
                            <div>
                                <h5>Doctor & Sample Information</h5>
                                <div class="mb-3">
                                    <label class="form-label">Doctor Name</label>
                                    <input type="text" class="form-control" id="doctorName">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">OPD No</label>
                                    <input type="text" class="form-control" id="opdNo">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Sample Date</label>
                                    <input type="date" class="form-control" id="sampleDate" value="''' + datetime.now().strftime('%Y-%m-%d') + '''">
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="form-section">
                        <h3 style="color: #003366; margin-bottom: 20px;">Select Pathology Tests</h3>
                        
                        {% for category, test_list in tests.items() %}
                        <div class="test-category">
                            <h6 style="color: #003366; margin-bottom: 10px;">{{ category }}</h6>
                            <div class="row">
                                {% for test in test_list %}
                                <div class="col-md-6 test-checkbox">
                                    <div class="form-check">
                                        <input class="form-check-input test-checkbox" type="checkbox" value="{{ test }}" id="test_{{ loop.index }}_{{ category }}">
                                        <label class="form-check-label" for="test_{{ loop.index }}_{{ category }}">
                                            {{ test }}
                                        </label>
                                    </div>
                                </div>
                                {% endfor %}
                            </div>
                        </div>
                        {% endfor %}
                    </div>

                    <button class="btn-generate" onclick="generateFillableForm()">
                        📋 Generate Fillable Form
                    </button>
                </div>
            </div>

            <script>
                function generateFillableForm() {
                    // Get patient data
                    const patientData = {
                        name: document.getElementById('patientName').value,
                        age: document.getElementById('patientAge').value,
                        gender: document.getElementById('patientGender').value,
                        mobile: document.getElementById('patientMobile').value,
                        doctor: document.getElementById('doctorName').value,
                        opd_no: document.getElementById('opdNo').value,
                        sample_date: document.getElementById('sampleDate').value
                    };

                    // Validate required fields
                    if (!patientData.name || !patientData.age || !patientData.gender || !patientData.mobile) {
                        alert('Please fill in all required patient information (Name, Age, Gender, Mobile)');
                        return;
                    }

                    // Get selected tests
                    const selectedTests = [];
                    const checkboxes = document.querySelectorAll('.test-checkbox:checked');
                    checkboxes.forEach(checkbox => {
                        selectedTests.push(checkbox.value);
                    });

                    if (selectedTests.length === 0) {
                        alert('Please select at least one test');
                        return;
                    }

                    // Redirect to fillable form with data as URL parameters
                    const params = new URLSearchParams({
                        patient_data: JSON.stringify(patientData),
                        selected_tests: JSON.stringify(selectedTests)
                    });
                    
                    window.open('/fillable-form?' + params.toString(), '_blank');
                }
            </script>
        </body>
        </html>
        '''

        @self.flask_app.route('/')
        def home():
            """Serve the main web form with patient info and test selection"""
            return render_template_string(MAIN_WEB_FORM, tests=self.tests)

        @self.flask_app.route('/fillable-form')
        def fillable_form():
            """Serve the fillable form with selected tests"""
            try:
                # Get data from URL parameters
                patient_data_json = request.args.get('patient_data')
                selected_tests_json = request.args.get('selected_tests')
                
                if patient_data_json and selected_tests_json:
                    patient_data = json.loads(patient_data_json)
                    selected_tests = json.loads(selected_tests_json)
                else:
                    return "Error: No patient data provided"
                
                # Generate the HTML form with current data
                html_content = self.generate_exact_format_html_form(patient_data, selected_tests)
                return html_content
                
            except Exception as e:
                return f"Error loading form: {str(e)}"

        @self.flask_app.route('/submit-report', methods=['POST', 'OPTIONS'])
        def handle_form_submission():
            if request.method == 'OPTIONS':
                return jsonify({'status': 'ok'}), 200
                
            try:
                # Ensure content type is JSON
                if not request.is_json:
                    return jsonify({
                        'success': False,
                        'message': 'Content-Type must be application/json'
                    }), 400
                
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False, 
                        'message': 'No JSON data received'
                    }), 400
                    
                patient_data = data.get('patient_data', {})
                test_results = data.get('test_results', {})
                
                print(f"Received submission for: {patient_data.get('name', 'Unknown')}")
                print(f"Mobile Number: {patient_data.get('mobile', 'Not provided')}")
                print(f"Test results received: {len(test_results)} tests")
                
                # Validate required fields
                required_fields = ['name', 'age', 'gender', 'mobile']
                for field in required_fields:
                    if not patient_data.get(field):
                        return jsonify({
                            'success': False,
                            'message': f'Missing required field: {field}'
                        }), 400
                
                # Generate PDF from filled data
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                patient_name_clean = patient_data.get('name', 'Unknown').replace(' ', '_').replace('/', '_').replace('\\', '_')
                pdf_filename = f"Pathology_Report_{patient_name_clean}_{timestamp}.pdf"
                pdf_filepath = os.path.join('reports', 'completed_reports', pdf_filename)
                
                # Ensure directory exists
                os.makedirs('reports/completed_reports', exist_ok=True)
                
                # Generate HTML content for PDF WITH FILLED RESULTS
                html_content = self.generate_pdf_html(patient_data, test_results)
                
                # Generate PDF using available method
                pdf_success, pdf_bytes = self.generate_pdf_bytes(html_content)
                
                if pdf_success and pdf_bytes:
                    # Save PDF to file
                    with open(pdf_filepath, 'wb') as f:
                        f.write(pdf_bytes)
                    
                    print(f"✅ PDF saved to: {pdf_filepath}")
                    
                    # Generate view URL for the PDF
                    pdf_url = f"http://localhost:5000/view-pdf/{pdf_filename}"
                    
                    # Send WhatsApp message with PDF view link
                    whatsapp_success, whatsapp_message = self.send_whatsapp_direct(
                        patient_data.get('mobile', ''), 
                        patient_data,
                        pdf_url
                    )
                    
                    # Store in database with WhatsApp status
                    db_success = self.store_completed_report(
                        patient_data, 
                        test_results, 
                        pdf_filepath, 
                        whatsapp_success, 
                        whatsapp_message
                    )
                    
                    return jsonify({
                        'success': True,
                        'message': 'Report submitted successfully! PDF generated and WhatsApp message sent.',
                        'whatsapp_status': 'sent' if whatsapp_success else 'failed',
                        'whatsapp_message': whatsapp_message,
                        'pdf_path': pdf_filepath,
                        'pdf_url': pdf_url
                    })
                else:
                    # If PDF generation fails, still store the data and return HTML option
                    html_filename = f"Pathology_Report_{patient_name_clean}_{timestamp}.html"
                    html_filepath = os.path.join('reports', 'completed_reports', html_filename)
                    
                    with open(html_filepath, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    # Use view-pdf for HTML files as well
                    html_url = f"http://localhost:5000/view-pdf/{html_filename}"
                    
                    whatsapp_success, whatsapp_message = self.send_whatsapp_direct(
                        patient_data.get('mobile', ''), 
                        patient_data,
                        html_url
                    )
                    
                    self.store_completed_report(
                        patient_data, 
                        test_results, 
                        html_filepath, 
                        whatsapp_success, 
                        whatsapp_message
                    )
                    
                    return jsonify({
                        'success': True,
                        'message': 'Report submitted successfully! (HTML version - PDF generation failed)',
                        'whatsapp_status': 'sent' if whatsapp_success else 'failed',
                        'whatsapp_message': whatsapp_message,
                        'pdf_path': html_filepath,
                        'pdf_url': html_url
                    })
                    
            except Exception as e:
                print(f"❌ Error in form submission: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'message': f'Server Error: {str(e)}'
                }), 500

        # Route for VIEWING PDF in browser
        @self.flask_app.route('/view-pdf/<filename>')
        def view_pdf(filename):
            try:
                if '..' in filename or filename.startswith('/'):
                    return jsonify({'error': 'Invalid filename'}), 400
                    
                directory = os.path.join(os.getcwd(), 'reports', 'completed_reports')
                filepath = os.path.join(directory, filename)
                
                if not os.path.exists(filepath):
                    return jsonify({'error': f'File not found: {filename}'}), 404
                
                # Determine content type
                if filename.lower().endswith('.pdf'):
                    mimetype = 'application/pdf'
                    print(f"📄 Serving PDF: {filename}")
                    return send_from_directory(
                        directory, 
                        filename, 
                        as_attachment=False,
                        mimetype=mimetype
                    )
                elif filename.lower().endswith('.html'):
                    mimetype = 'text/html'
                    with open(filepath, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    return Response(html_content, mimetype=mimetype)
                else:
                    return send_from_directory(directory, filename, as_attachment=True)
                    
            except Exception as e:
                return jsonify({'error': str(e)}), 404

        @self.flask_app.after_request
        def after_request(response):
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            return response

    def start_flask_server(self):
        """Start Flask server in a separate thread"""
        def run_flask():
            try:
                print("🚀 Starting Flask server on http://127.0.0.1:5000")
                print("📁 Reports directory: reports/completed_reports/")
                self.flask_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                print(f"❌ Flask server error: {e}")
        
        self.flask_thread = threading.Thread(target=run_flask, daemon=True)
        self.flask_thread.start()
        time.sleep(2)  # Give server time to start

    def launch_web_app(self):
        """Launch the web application in browser"""
        self.status_label.config(text="Opening web application...")
        
        flask_url = "http://localhost:5000/"
        webbrowser.open(flask_url)
        
        self.status_label.config(text="Web application opened in browser!")
        messagebox.showinfo("Success", f"Web application opened in browser!\n\nIf it doesn't load automatically, visit:\n{flask_url}")

    def generate_exact_format_html_form(self, patient_data, selected_tests):
        """Generate HTML form in the exact format as provided"""
        serial_no = 1
        
        # Start building the HTML content
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>UJJIVAN Hospital Pathology Report</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">

  <style>
    body {{
      background: #f8f9fa;
      font-family: 'Times New Roman', serif;
    }}

    .report-container {{
      background: #fff;
      border: 2px solid #000;
      padding: 40px 50px;
      max-width: 900px;
      margin: 30px auto;
      box-shadow: 0 0 10px rgba(0,0,0,0.15);
    }}

    .header {{
      text-align: center;
      border-bottom: 2px solid #000;
      margin-bottom: 15px;
      padding-bottom: 8px;
    }}

    .header h2 {{
      font-weight: bold;
      text-transform: uppercase;
      color: #003366;
    }}

    .hospital-info {{
      font-size: 13px;
    }}

    .patient-info {{
      font-size: 14px;
      margin-bottom: 15px;
    }}

    .section-title {{
      background: #e8f0ff;
      color: #003366;
      font-weight: bold;
      border: 1px solid #003366;
      padding: 6px 8px;
      text-transform: uppercase;
      margin-top: 20px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 10px;
      font-size: 14px;
    }}

    th, td {{
      border: 1px solid #666;
      padding: 6px;
    }}

    th {{
      background: #e9ecef;
      text-align: center;
    }}

    input.result {{
      border: none;
      border-bottom: 1px solid #888;
      width: 100%;
      outline: none;
      text-align: center;
      background: #fefefe;
      font-weight: bold;
    }}

    .footer {{
      text-align: right;
      margin-top: 40px;
      font-weight: bold;
    }}

    @media print {{
      body {{
        background: white;
      }}
      .report-container {{
        box-shadow: none;
        border: 1px solid #000;
        margin: 0;
      }}
      input.result {{
        border: none;
      }}
    }}
  </style>
</head>
<body>

  <div class="report-container">

    <div class="header">
      <h2>Pathology Test Report</h2>
      <div class="hospital-info">
        <p>UJJIVAN Hospital, Vidyut Nagar, Gautam Budh Nagar, Uttar Pradesh - 201008</p>
      </div>
    </div>

    <div class="row patient-info">
      <div class="col-6">
        <strong>OPD No:</strong> <input type="text" class="result" placeholder="" value="{patient_data['opd_no']}" id="opd_no"><br>
        <strong>Patient Name:</strong> <input type="text" class="result" placeholder="" value="{patient_data['name']}" id="patient_name"><br>
        <strong>Age/Sex:</strong> <input type="text" class="result" placeholder="" value="{patient_data['age']}/{patient_data['gender']}" id="age_gender">
      </div>
      <div class="col-6 text-end">
        <strong>Doctor Name:</strong> <input type="text" class="result" placeholder="" value="{patient_data['doctor']}" id="doctor_name"><br>
        <strong>Sample Date:</strong> <input type="text" class="result" placeholder="" value="{patient_data['sample_date']}" id="sample_date">
      </div>
    </div>
'''
        
        # BIOCHEMISTRY Section
        if any(test in selected_tests for test in ["Glucose (F)/RI", "Post Prandial / after 2 Hrs", "HbA1c"]):
            html_content += '''
    <!-- BIOCHEMISTRY -->
    <div class="section-title">BIOCHEMISTRY</div>
    <table>
      <thead>
        <tr>
          <th>S.No</th>
          <th>Test Description</th>
          <th>Normal Value</th>
          <th>Result Value</th>
        </tr>
      </thead>
      <tbody>
'''
            biochemistry_tests = [
                ("Glucose (F)/RI", "70-110 mg/dl"),
                ("Post Prandial / after 2 Hrs", "Up to 140 mg/dl"),
                ("HbA1c", "4.5-6.5 %")
            ]
            
            for test_name, normal_value in biochemistry_tests:
                if test_name in selected_tests:
                    html_content += f'        <tr><td>{serial_no}</td><td>{test_name}</td><td>{normal_value}</td><td><input type="text" class="result" placeholder="Enter value" name="{test_name}" id="{test_name.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "").replace(" ", "")}"></td></tr>\n'
                    serial_no += 1
            
            html_content += '''      </tbody>
    </table>
'''

        # RENAL FUNCTION Section
        if any(test in selected_tests for test in ["Urea", "Creatinine", "S. Uric Acid", "BUN"]):
            html_content += '''
    <!-- RENAL FUNCTION -->
    <div class="section-title">RENAL FUNCTION</div>
    <table>
      <thead>
        <tr>
          <th>S.No</th>
          <th>Test Description</th>
          <th>Normal Value</th>
          <th>Result Value</th>
        </tr>
      </thead>
      <tbody>
'''
            renal_tests = [
                ("Urea", "10-40 mg/dl"),
                ("Creatinine", "0.6-1.4 mg/dl"),
                ("S. Uric Acid", "2.8-7.0 mg/dl"),
                ("BUN", "5-20 mg/dl")
            ]
            
            for test_name, normal_value in renal_tests:
                if test_name in selected_tests:
                    html_content += f'        <tr><td>{serial_no}</td><td>{test_name}</td><td>{normal_value}</td><td><input type="text" class="result" placeholder="Enter value" name="{test_name}" id="{test_name.replace(" ", "_").replace(".", "").replace(" ", "")}"></td></tr>\n'
                    serial_no += 1
            
            html_content += '''      </tbody>
    </table>
'''

        # LIPID PROFILE Section
        if any(test in selected_tests for test in ["Cholesterol", "Triglyceride", "HDL", "LDL"]):
            html_content += '''
    <!-- LIPID PROFILE -->
    <div class="section-title">LIPID PROFILE</div>
    <table>
      <thead>
        <tr>
          <th>S.No</th>
          <th>Test Description</th>
          <th>Normal Value</th>
          <th>Result Value</th>
        </tr>
      </thead>
      <tbody>
'''
            lipid_tests = [
                ("Cholesterol", "150-200 mg/dl"),
                ("Triglyceride", "0-170 mg/dl"),
                ("HDL", "30-96 (F)/30-70 (M) mg/dl"),
                ("LDL", "<100 mg/dl")
            ]
            
            for test_name, normal_value in lipid_tests:
                if test_name in selected_tests:
                    html_content += f'        <tr><td>{serial_no}</td><td>{test_name}</td><td>{normal_value}</td><td><input type="text" class="result" placeholder="Enter value" name="{test_name}" id="{test_name.replace(" ", "_")}"></td></tr>\n'
                    serial_no += 1
            
            html_content += '''      </tbody>
    </table>
'''

        # LIVER FUNCTION Section
        if any(test in selected_tests for test in ["Bilirubin Total", "Bilirubin (Conjugated)", "Bilirubin (Unconjugated)", "SGOT/AST", "SGPT/ALT", "Alk. Phosphatase", "Total Protein", "Albumin", "Globulin", "A/G Ratio", "GGT"]):
            html_content += '''
    <!-- LIVER FUNCTION -->
    <div class="section-title">LIVER FUNCTION</div>
    <table>
      <thead>
        <tr>
          <th>S.No</th>
          <th>Test Description</th>
          <th>Normal Value</th>
          <th>Result Value</th>
        </tr>
      </thead>
      <tbody>
'''
            liver_tests = [
                ("Bilirubin Total", "0.1-1.2 mg/dl (new born 1.0-12.0)"),
                ("Bilirubin (Conjugated)", "0.0-0.3 mg/dl"),
                ("Bilirubin (Unconjugated)", "0.1-1.0 mg/dl"),
                ("SGOT/AST", "0-35 U/L"),
                ("SGPT/ALT", "0-40 U/L"),
                ("Alk. Phosphatase", "175-575 U/L (<15 years) + (10-290 U/L (<15 years))"),
                ("Total Protein", "6.5-8.0 gm/dl"),
                ("Albumin", "3.5-5.0 gm/dl"),
                ("Globulin", "2.3-3.5 gm/dl"),
                ("A/G Ratio", "1.0-2.5"),
                ("GGT", "8-60 U/L")
            ]
            
            for test_name, normal_value in liver_tests:
                if test_name in selected_tests:
                    html_content += f'        <tr><td>{serial_no}</td><td>{test_name}</td><td>{normal_value}</td><td><input type="text" class="result" placeholder="Enter value" name="{test_name}" id="{test_name.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "").replace(".", "").replace(" ", "")}"></td></tr>\n'
                    serial_no += 1
            
            html_content += '''      </tbody>
    </table>
'''

        # ELECTROLYTES Section
        if any(test in selected_tests for test in ["S. Calcium", "S. Sodium", "S. Potassium"]):
            html_content += '''
    <!-- ELECTROLYTES -->
    <div class="section-title">ELECTROLYTES</div>
    <table>
      <thead>
        <tr>
          <th>S.No</th>
          <th>Test Description</th>
          <th>Normal Value</th>
          <th>Result Value</th>
        </tr>
      </thead>
      <tbody>
'''
            electrolyte_tests = [
                ("S. Calcium", "8.8-11.0 mg/dl"),
                ("S. Sodium", "138-148 meq/l"),
                ("S. Potassium", "3.8-4.8 meq/l")
            ]
            
            for test_name, normal_value in electrolyte_tests:
                if test_name in selected_tests:
                    html_content += f'        <tr><td>{serial_no}</td><td>{test_name}</td><td>{normal_value}</td><td><input type="text" class="result" placeholder="Enter value" name="{test_name}" id="{test_name.replace(" ", "_").replace(".", "").replace(" ", "")}"></td></tr>\n'
                    serial_no += 1
            
            html_content += '''      </tbody>
    </table>
'''

        # OTHER TESTS Section
        if any(test in selected_tests for test in ["Urine Protein (24 Hrs)", "Urine micro protein (albumin)", "CK-MB", "S. Phosphorous", "S. Amylase", "TROP-T"]):
            html_content += '''
    <!-- OTHER TESTS -->
    <div class="section-title">OTHER TESTS</div>
    <table>
      <thead>
        <tr>
          <th>S.No</th>
          <th>Test Description</th>
          <th>Normal Value</th>
          <th>Result Value</th>
        </tr>
      </thead>
      <tbody>
'''
            other_tests = [
                ("Urine Protein (24 Hrs)", "24-120 mg/24 Hrs"),
                ("Urine micro protein (albumin)", "28-150 mg/24 Hrs (24 hrs.) (<10mg/dl for ran)"),
                ("CK-MB", "0-24 U/L"),
                ("S. Phosphorous", "2.7-4.5 mg/dl"),
                ("S. Amylase", "0-110 U/L"),
                ("TROP-T", "-")
            ]
            
            for test_name, normal_value in other_tests:
                if test_name in selected_tests:
                    html_content += f'        <tr><td>{serial_no}</td><td>{test_name}</td><td>{normal_value}</td><td><input type="text" class="result" placeholder="Enter value" name="{test_name}" id="{test_name.replace(" ", "_").replace("(", "").replace(")", "").replace(".", "").replace(" ", "")}"></td></tr>\n'
                    serial_no += 1
            
            html_content += '''      </tbody>
    </table>
'''

        # HAEMATOLOGY Section - NEW
        if any(test in selected_tests for test in ["Haemoglobin", "Total leukocyte count", "Differential WBC count - Polymorphs", 
                                                  "Differential WBC count - Lymphocytes", "Differential WBC count - Eosinophils",
                                                  "Differential WBC count - Monocytes", "Differential WBC count - Basophiles",
                                                  "AEC", "E.S.R. (Westergren)", "Platelet Count", "RBC Count", 
                                                  "Reticulocyte count", "Haematocrit/PCV", "MCV", "MCH", "MCHC",
                                                  "Malaria Parasite", "BLOOD GROUP", "Bleeding Time", "Clotting Time",
                                                  "Prothrombin Time", "PERIPHERAL BLOOD SMEAR - RBC", 
                                                  "PERIPHERAL BLOOD SMEAR - WBC", "PERIPHERAL BLOOD SMEAR - PLATELET",
                                                  "PERIPHERAL BLOOD SMEAR - HAEMOPARASITE"]):
            html_content += '''
    <!-- HAEMATOLOGY -->
    <div class="section-title">HAEMATOLOGY</div>
    <table>
      <thead>
        <tr>
          <th>S.No</th>
          <th>Test Description</th>
          <th>Normal Value</th>
          <th>Result Value</th>
        </tr>
      </thead>
      <tbody>
'''
            haematology_tests = [
                ("Haemoglobin", "14-18 gm% (M)/12-15 gm% (F)"),
                ("Total leukocyte count", "4000-10,000/cu mm of blood"),
                ("Differential WBC count - Polymorphs", "40-75%"),
                ("Differential WBC count - Lymphocytes", "20-45%"),
                ("Differential WBC count - Eosinophils", "1-6%"),
                ("Differential WBC count - Monocytes", "0-10%"),
                ("Differential WBC count - Basophiles", "0-1%"),
                ("AEC", "40-500 No/cu mm"),
                ("E.S.R. (Westergren)", "0-12 mm (F), 0-10 mm (M) at the end of 1st hr."),
                ("Platelet Count", "1.5-4.5 lac/cu mm of blood"),
                ("RBC Count", "F=3.5 to 5.0, M=4.2-5.5 lac/cu mm"),
                ("Reticulocyte count", "2-5% of RBC"),
                ("Haematocrit/PCV", "M=39-49%, F=33-43%"),
                ("MCV", "76-100 fl"),
                ("MCH", "29.5 ± 2.5 pg"),
                ("MCHC", "32.5 ± 2.5 gm/dl"),
                ("Malaria Parasite", "-"),
                ("BLOOD GROUP", "Rh = Positive/Negative"),
                ("Bleeding Time", "2-7 Min. (Ivy's method)"),
                ("Clotting Time", "6 Min. (Lee & White, 37°C)"),
                ("Prothrombin Time", "10-14 Sec."),
                ("PERIPHERAL BLOOD SMEAR - RBC", "-"),
                ("PERIPHERAL BLOOD SMEAR - WBC", "-"),
                ("PERIPHERAL BLOOD SMEAR - PLATELET", "-"),
                ("PERIPHERAL BLOOD SMEAR - HAEMOPARASITE", "-")
            ]
            
            for test_name, normal_value in haematology_tests:
                if test_name in selected_tests:
                    html_content += f'        <tr><td>{serial_no}</td><td>{test_name}</td><td>{normal_value}</td><td><input type="text" class="result" placeholder="Enter value" name="{test_name}" id="{test_name.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "").replace(".", "").replace(" ", "").replace("-", "_")}"></td></tr>\n'
                    serial_no += 1
            
            html_content += '''      </tbody>
    </table>
'''

        # SEROLOGY Section - NEW
        if any(test in selected_tests for test in ["HbsAg", "HIV (1+2)", "HCV", "VDRL", "ASO Titer", "R.A. factor", 
                                                  "CRP", "Gravindex (PREGNANCY)", "WIDAL TEST - S. Typhi, 'O'",
                                                  "WIDAL TEST - S. Typhi, 'H'", "WIDAL TEST - S. Paratyphi, 'AH'",
                                                  "WIDAL TEST - S. Paratyphi, 'BH'", "Dengue NS1", "Typhi Dot"]):
            html_content += '''
    <!-- SEROLOGY -->
    <div class="section-title">SEROLOGY</div>
    <table>
      <thead>
        <tr>
          <th>S.No</th>
          <th>Test Description</th>
          <th>Normal Value</th>
          <th>Result Value</th>
        </tr>
      </thead>
      <tbody>
'''
            serology_tests = [
                ("HbsAg", "Negative"),
                ("HIV (1+2)", "Negative"),
                ("HCV", "Negative"),
                ("VDRL", "Non-reactive"),
                ("ASO Titer", "<200 IU/ml"),
                ("R.A. factor", "<20 IU/ml"),
                ("CRP", "<6 mg/L"),
                ("Gravindex (PREGNANCY)", "Negative"),
                ("WIDAL TEST - S. Typhi, 'O'", "Negative (<1:80)"),
                ("WIDAL TEST - S. Typhi, 'H'", "Negative (<1:160)"),
                ("WIDAL TEST - S. Paratyphi, 'AH'", "Negative (<1:80)"),
                ("WIDAL TEST - S. Paratyphi, 'BH'", "Negative (<1:80)"),
                ("Dengue NS1", "Negative"),
                ("Typhi Dot", "Negative")
            ]
            
            for test_name, normal_value in serology_tests:
                if test_name in selected_tests:
                    html_content += f'        <tr><td>{serial_no}</td><td>{test_name}</td><td>{normal_value}</td><td><input type="text" class="result" placeholder="Enter value" name="{test_name}" id="{test_name.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "").replace(".", "").replace(" ", "").replace("-", "_").replace("'", "").replace(",", "")}"></td></tr>\n'
                    serial_no += 1
            
            html_content += '''      </tbody>
    </table>
'''

        html_content += f'''
    <div class="footer">
      Signature<br>(Pathologist)
    </div>

    <!-- ✅ Submit Button -->
    <div class="d-grid gap-2 d-md-flex justify-content-md-end mt-4">
      <button type="button" class="btn btn-success me-md-2" onclick="submitForm()">
        ✅ Submit & Send WhatsApp Report
      </button>
      <button type="reset" class="btn btn-secondary">Clear Form</button>
    </div>

  </div>

  <script>
    function submitForm() {{
      const inputs = document.querySelectorAll('input.result');
      const testResults = {{}};
      
      inputs.forEach(input => {{
        if (input.value.trim() !== '' && input.name) {{
          testResults[input.name] = input.value;
        }}
      }});
      
      // Validate that at least one test result is entered
      if (Object.keys(testResults).length === 0) {{
        alert('Please enter at least one test result.');
        return;
      }}
      
      const submissionData = {{
        patient_data: {{
          name: "{patient_data['name']}",
          age: "{patient_data['age']}",
          gender: "{patient_data['gender']}",
          mobile: "{patient_data['mobile']}",
          doctor: "{patient_data['doctor']}",
          opd_no: "{patient_data['opd_no']}",
          sample_date: "{patient_data['sample_date']}"
        }},
        test_results: testResults
      }};
      
      console.log('Submitting data:', submissionData);
      
      fetch('http://localhost:5000/submit-report', {{
        method: 'POST',
        headers: {{
          'Content-Type': 'application/json',
        }},
        body: JSON.stringify(submissionData)
      }})
      .then(response => {{
        if (!response.ok) {{
          // Try to parse error response as JSON first
          return response.json().then(err => {{
            throw new Error(err.message || 'HTTP error ' + response.status);
          }}).catch(() => {{
            throw new Error('HTTP error ' + response.status);
          }});
        }}
        return response.json();
      }})
      .then(data => {{
        if (data.success) {{
          alert('✅ Report submitted successfully!\\\\n\\\\n' + data.message + '\\\\n\\\\nWhatsApp Status: ' + data.whatsapp_message + '\\\\n\\\\nThe patient will receive this link to view their report:\\\\n' + data.pdf_url);
          if (data.pdf_url) {{
            window.open(data.pdf_url, '_blank');
          }}
        }} else {{
          alert('❌ Error: ' + data.message);
        }}
      }})
      .catch(error => {{
        alert('❌ Error submitting form: ' + error);
        console.error('Error:', error);
      }});
    }}
  </script>
</body>
</html>'''
        return html_content

    def generate_pdf_html(self, patient_data, test_results):
        """Generate HTML for PDF with filled results including normal ranges"""
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ 
                    font-family: 'Times New Roman', serif; 
                    margin: 20px;
                    line-height: 1.4;
                }}
                .header {{ 
                    text-align: center; 
                    border-bottom: 2px solid #000; 
                    padding-bottom: 10px; 
                    margin-bottom: 20px; 
                }}
                .header h1 {{
                    color: #003366;
                    margin-bottom: 5px;
                    font-size: 24px;
                }}
                .patient-info {{ 
                    margin-bottom: 20px;
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    border: 1px solid #ddd;
                }}
                .patient-info p {{
                    margin: 5px 0;
                    font-size: 14px;
                }}
                .section {{ 
                    margin-bottom: 20px; 
                }}
                .section-title {{ 
                    background: #003366; 
                    color: white; 
                    padding: 8px 12px; 
                    font-weight: bold;
                    border-radius: 3px;
                    margin-bottom: 10px;
                    font-size: 16px;
                }}
                table {{ 
                    width: 100%; 
                    border-collapse: collapse; 
                    margin-bottom: 15px;
                    font-size: 12px;
                }}
                th, td {{ 
                    border: 1px solid #000; 
                    padding: 8px; 
                    text-align: left; 
                }}
                th {{ 
                    background: #e9ecef; 
                    font-weight: bold;
                    font-size: 13px;
                }}
                .normal-range {{
                    color: #666;
                    font-size: 11px;
                }}
                .footer {{
                    margin-top: 40px; 
                    text-align: right;
                    border-top: 1px solid #000;
                    padding-top: 20px;
                }}
                .abnormal {{
                    color: #dc3545;
                    font-weight: bold;
                }}
                .normal {{
                    color: #28a745;
                }}
                .hospital-info {{
                    font-size: 12px;
                    color: #666;
                }}
                @media print {{
                    body {{ margin: 0; padding: 10px; }}
                    .header {{ border-bottom: 2px solid #000; }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>UJJIVAN HOSPITAL PATHOLOGY REPORT</h1>
                <div class="hospital-info">
                    <p>Vidyut Nagar, Gautam Budh Nagar, Uttar Pradesh - 201008</p>
                    <p>Phone: [Hospital Phone] | Email: [Hospital Email]</p>
                </div>
            </div>
            
            <div class="patient-info">
                <p><strong>Patient Name:</strong> {patient_data.get('name', '')}</p>
                <p><strong>Age/Gender:</strong> {patient_data.get('age', '')}/{patient_data.get('gender', '')}</p>
                <p><strong>Mobile:</strong> {patient_data.get('mobile', '')}</p>
                <p><strong>Doctor:</strong> {patient_data.get('doctor', '')}</p>
                <p><strong>OPD No:</strong> {patient_data.get('opd_no', '')}</p>
                <p><strong>Sample Date:</strong> {patient_data.get('sample_date', '')}</p>
                <p><strong>Report Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            </div>
            
            <div class="section">
                <div class="section-title">TEST RESULTS</div>
                <table>
                    <tr>
                        <th width="40%">Test Name</th>
                        <th width="30%">Normal Range</th>
                        <th width="30%">Result</th>
                    </tr>
        '''
        
        # Group tests by category for better organization
        test_categories = {
            "BIOCHEMISTRY": [],
            "RENAL FUNCTION": [],
            "LIPID PROFILE": [],
            "LIVER FUNCTION": [],
            "ELECTROLYTES": [],
            "OTHER TESTS": [],
            "HAEMATOLOGY": [],
            "SEROLOGY": []
        }
        
        # Categorize tests
        for test_name, result in test_results.items():
            category_found = False
            for category, tests in self.tests.items():
                if test_name in tests:
                    test_categories[category].append((test_name, result))
                    category_found = True
                    break
            if not category_found:
                test_categories["OTHER TESTS"].append((test_name, result))
        
        # Generate table rows for each category
        serial_no = 1
        for category, tests in test_categories.items():
            if tests:
                html_content += f'''
                    <tr>
                        <td colspan="3" style="background: #e8f0ff; font-weight: bold; text-align: center; font-size: 14px;">
                            {category}
                        </td>
                    </tr>
                '''
                
                for test_name, result in tests:
                    normal_range = self.normal_ranges.get(test_name, "Not specified")
                    
                    # Simple check for abnormal values
                    status_class = "normal"
                    result_str = str(result).lower()
                    if any(word in result_str for word in ['positive', 'high', 'low', 'abnormal', 'reactive']):
                        status_class = "abnormal"
                    elif test_name in ["Glucose (F)/RI", "HbA1c", "Urea", "Creatinine"] and result.replace('.', '').replace('-', '').isdigit():
                        try:
                            value = float(result)
                            if test_name == "Glucose (F)/RI" and (value < 70 or value > 110):
                                status_class = "abnormal"
                            elif test_name == "HbA1c" and (value < 4.5 or value > 6.5):
                                status_class = "abnormal"
                            elif test_name == "Urea" and (value < 10 or value > 40):
                                status_class = "abnormal"
                            elif test_name == "Creatinine" and (value < 0.6 or value > 1.4):
                                status_class = "abnormal"
                        except:
                            pass
                    
                    html_content += f'''
                    <tr>
                        <td>{serial_no}. {test_name}</td>
                        <td><span class="normal-range">{normal_range}</span></td>
                        <td class="{status_class}"><strong>{result}</strong></td>
                    </tr>
                    '''
                    serial_no += 1
        
        html_content += '''
                </table>
            </div>
            
            <div class="footer">
                <p><strong>Signature</strong></p>
                <p>_________________________</p>
                <p>(Pathologist)</p>
                <p>UJJIVAN Hospital Pathology Department</p>
                <p>License No: [Pathology License Number]</p>
            </div>
            
            <div style="margin-top: 20px; font-size: 10px; color: #666; text-align: center; border-top: 1px solid #eee; padding-top: 10px;">
                <p>This is a computer generated report. For any queries, please contact the laboratory.</p>
                <p>Report ID: ''' + datetime.now().strftime('%Y%m%d%H%M%S') + ''' | Generated on: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
            </div>
        </body>
        </html>
        '''
        return html_content

    def generate_pdf_bytes(self, html_content):
        """Generate PDF bytes from HTML content using available methods"""
        try:
            # Method 1: Try WeasyPrint (only if available and not Windows)
            if WEASYPRINT_AVAILABLE:
                try:
                    from weasyprint import HTML
                    
                    # Generate PDF
                    pdf_bytes = HTML(string=html_content, encoding='utf-8').write_pdf()
                    
                    print("✅ PDF generated successfully with WeasyPrint")
                    return True, pdf_bytes
                    
                except Exception as e:
                    print(f"❌ WeasyPrint failed: {e}")
            
            # Method 2: Try pdfkit
            if PDFKIT_AVAILABLE:
                try:
                    options = {
                        'page-size': 'A4',
                        'margin-top': '0.5in',
                        'margin-right': '0.5in',
                        'margin-bottom': '0.5in',
                        'margin-left': '0.5in',
                        'encoding': "UTF-8",
                        'no-outline': None,
                        'quiet': ''
                    }
                    
                    config = None
                    possible_paths = [
                        '/usr/bin/wkhtmltopdf',
                        '/usr/local/bin/wkhtmltopdf',
                        'C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe',
                        'C:/wkhtmltopdf/bin/wkhtmltopdf.exe'
                    ]
                    
                    for path in possible_paths:
                        if os.path.exists(path):
                            config = pdfkit.configuration(wkhtmltopdf=path)
                            break
                    
                    # Create temporary PDF file
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                        tmp_path = tmp.name
                    
                    if config:
                        pdfkit.from_string(html_content, tmp_path, options=options, configuration=config)
                    else:
                        pdfkit.from_string(html_content, tmp_path, options=options)
                    
                    # Read PDF bytes
                    with open(tmp_path, 'rb') as f:
                        pdf_bytes = f.read()
                    
                    # Clean up temp file
                    os.unlink(tmp_path)
                    
                    print("✅ PDF generated successfully with pdfkit")
                    return True, pdf_bytes
                    
                except Exception as e:
                    print(f"❌ pdfkit failed: {e}")
            
            # Method 3: Try alternative using xhtml2pdf (pure Python)
            try:
                from xhtml2pdf import pisa
                import io
                
                # Create a PDF in memory
                pdf_bytes = io.BytesIO()
                pisa_status = pisa.CreatePDF(html_content, dest=pdf_bytes)
                
                if pisa_status.err:
                    print("❌ xhtml2pdf failed")
                    raise Exception("PDF generation failed")
                
                pdf_data = pdf_bytes.getvalue()
                pdf_bytes.close()
                
                print("✅ PDF generated successfully with xhtml2pdf")
                return True, pdf_data
                
            except ImportError:
                print("⚠️ xhtml2pdf not available.")
            except Exception as e:
                print(f"❌ xhtml2pdf failed: {e}")
            
            # Method 4: Try alternative using reportlab (basic PDF)
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                from reportlab.lib.utils import ImageReader
                import io
                
                # Create a simple PDF with reportlab
                pdf_bytes = io.BytesIO()
                c = canvas.Canvas(pdf_bytes, pagesize=letter)
                width, height = letter
                
                # Add simple text to PDF
                c.setFont("Helvetica", 12)
                c.drawString(100, height - 100, "UJJIVAN HOSPITAL PATHOLOGY REPORT")
                c.drawString(100, height - 120, "Patient Report - HTML version available")
                c.drawString(100, height - 140, "Please view the HTML report for detailed results")
                c.save()
                
                pdf_data = pdf_bytes.getvalue()
                pdf_bytes.close()
                
                print("✅ Basic PDF generated with reportlab")
                return True, pdf_data
                
            except ImportError:
                print("⚠️ reportlab not available.")
            except Exception as e:
                print(f"❌ reportlab failed: {e}")
            
            # Method 5: Final fallback - generate HTML file only
            print("⚠️ No PDF generation method available. Using HTML fallback.")
            return False, None
            
        except Exception as e:
            print(f"❌ Error in PDF generation: {e}")
            return False, None

    def store_report_in_database(self, patient_data, selected_tests):
        """Store form submission in database"""
        try:
            selected_tests_json = json.dumps(selected_tests)
            
            self.cursor.execute('''
                INSERT INTO form_submissions 
                (patient_name, patient_age, patient_gender, patient_mobile, doctor_name, opd_no, sample_date, selected_tests)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_data['name'],
                patient_data['age'],
                patient_data['gender'],
                patient_data['mobile'],
                patient_data['doctor'],
                patient_data['opd_no'],
                patient_data['sample_date'],
                selected_tests_json
            ))
            
            self.conn.commit()
            print("Form submission stored in database")
            
        except Exception as e:
            print(f"Error storing form submission: {e}")

    def store_completed_report(self, patient_data, test_results, pdf_path, whatsapp_success, whatsapp_message):
        """Store completed report in database with WhatsApp status"""
        try:
            test_results_json = json.dumps(test_results)
            whatsapp_status = "sent" if whatsapp_success else "failed"
            
            self.cursor.execute('''
                INSERT INTO completed_reports 
                (patient_name, patient_age, patient_gender, patient_mobile, doctor_name, opd_no, sample_date, test_results, pdf_path, whatsapp_status, whatsapp_error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_data.get('name', ''),
                patient_data.get('age', ''),
                patient_data.get('gender', ''),
                patient_data.get('mobile', ''),
                patient_data.get('doctor', ''),
                patient_data.get('opd_no', ''),
                patient_data.get('sample_date', ''),
                test_results_json,
                pdf_path,
                whatsapp_status,
                whatsapp_message
            ))
            
            self.conn.commit()
            print(f"✅ Completed report stored in database. WhatsApp: {whatsapp_status}")
            return True
            
        except Exception as e:
            print(f"❌ Error storing completed report: {e}")
            return False

    def validate_mobile_number(self, mobile_number):
        """Validate and format mobile number"""
        try:
            # Remove any non-digit characters
            cleaned = re.sub(r'\D', '', str(mobile_number))
            
            # Check if it's a valid Indian mobile number
            if len(cleaned) == 10 and cleaned.startswith(('6', '7', '8', '9')):
                return f"91{cleaned}", None
            elif len(cleaned) == 12 and cleaned.startswith('91'):
                return cleaned, None
            else:
                return None, "Invalid mobile number format"
                
        except Exception as e:
            return None, f"Mobile validation error: {str(e)}"

    def send_whatsapp_direct(self, mobile_number, patient_data, pdf_url):
        """Send WhatsApp message directly using multiple methods"""
        try:
            # Validate and format mobile number
            formatted_mobile, mobile_error = self.validate_mobile_number(mobile_number)
            if mobile_error:
                return False, f"Mobile number error: {mobile_error}"
            
            print(f"📱 Attempting to send WhatsApp to: {formatted_mobile}")
            
            # Method 1: WhatsApp Business API
            api_success, api_message = self.send_whatsapp_api(formatted_mobile, patient_data, pdf_url)
            if api_success:
                return True, api_message
            
            # Method 2: WhatsApp Web (Manual)
            web_success, web_message = self.send_whatsapp_web(formatted_mobile, patient_data, pdf_url)
            if web_success:
                return True, web_message
            
            # Method 3: Simple SMS-style message (fallback)
            return self.send_simple_message(formatted_mobile, patient_data, pdf_url)
            
        except Exception as e:
            error_msg = f"WhatsApp sending failed: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def send_whatsapp_api(self, mobile_number, patient_data, pdf_url):
        """Send WhatsApp using WhatsApp Business API"""
        try:
            # This requires WhatsApp Business API setup
            # You need to get these from Facebook Developer Portal
            if (self.whatsapp_phone_number_id == "YOUR_PHONE_NUMBER_ID" or 
                self.whatsapp_access_token == "YOUR_ACCESS_TOKEN"):
                return False, "WhatsApp Business API not configured"
            
            url = f"{self.whatsapp_api_url}{self.whatsapp_phone_number_id}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.whatsapp_access_token}",
                "Content-Type": "application/json"
            }
            
            message_body = self.create_whatsapp_message(patient_data, pdf_url)
            
            payload = {
                "messaging_product": "whatsapp",
                "to": mobile_number,
                "type": "text",
                "text": {
                    "body": message_body
                }
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                print("✅ WhatsApp message sent via API!")
                return True, "WhatsApp message sent via Business API"
            else:
                return False, f"API Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return False, f"API method failed: {str(e)}"

    def send_whatsapp_web(self, mobile_number, patient_data, pdf_url):
        """Send WhatsApp using WhatsApp Web (opens browser)"""
        try:
            message_body = self.create_whatsapp_message(patient_data, pdf_url)
            
            # URL encode the message
            import urllib.parse
            encoded_message = urllib.parse.quote(message_body)
            
            # Create WhatsApp Web URL
            whatsapp_url = f"https://web.whatsapp.com/send?phone={mobile_number}&text={encoded_message}"
            
            # Open in browser
            webbrowser.open(whatsapp_url)
            
            print("✅ WhatsApp Web opened. Please send manually.")
            return True, "WhatsApp Web opened - please send manually"
            
        except Exception as e:
            return False, f"WhatsApp Web method failed: {str(e)}"

    def send_simple_message(self, mobile_number, patient_data, pdf_url):
        """Send simple message (fallback method)"""
        try:
            message_body = self.create_whatsapp_message(patient_data, pdf_url)
            
            print(f"📱 Message ready for {mobile_number}:")
            print("="*50)
            print(message_body)
            print("="*50)
            print(f"📄 Report URL that will be sent to patient: {pdf_url}")
            print("\n✅ The patient can click this link to view/download their report.")
            
            # Show message box with the URL
            messagebox.showinfo("Report Ready", 
                f"Report generated successfully!\n\n"
                f"Patient: {patient_data.get('name', '')}\n"
                f"Mobile: {mobile_number}\n\n"
                f"Report URL:\n{pdf_url}\n\n"
                f"Copy this URL and send it to the patient via WhatsApp or SMS.")
            
            return True, f"Message prepared. URL: {pdf_url}"
            
        except Exception as e:
            return False, f"Simple message method failed: {str(e)}"

    def create_whatsapp_message(self, patient_data, pdf_url):
        """Create WhatsApp message content with user-friendly URL"""
        return f"""
🔬 *UJJIVAN HOSPITAL - PATHOLOGY REPORT*

Dear {patient_data.get('name', 'Patient')},

Your pathology test report is ready for viewing.

*Patient Details:*
• Name: {patient_data.get('name', '')}
• Age: {patient_data.get('age', '')}
• Gender: {patient_data.get('gender', '')}
• Doctor: {patient_data.get('doctor', '')}
• Sample Date: {patient_data.get('sample_date', '')}

📄 *View Your Report Online:*
{pdf_url}

*Instructions:*
1. Click/tap the link above
2. Your report will open in browser
3. You can download/print if needed

*Report ID:* {patient_data.get('opd_no', 'N/A')}
*Generated on:* {datetime.now().strftime('%d-%m-%Y %I:%M %p')}

*Note:* This link is valid for 30 days. Contact hospital for queries.

Thank you for choosing UJJIVAN Hospital.
📍 Vidyut Nagar, Gautam Budh Nagar, UP - 201008
"""

    def send_sms_fast2sms(self, mobile_number, message):
        """Example SMS integration with Fast2SMS"""
        try:
            # You need to sign up at https://www.fast2sms.com/
            api_key = "YOUR_FAST2SMS_API_KEY"
            url = "https://www.fast2sms.com/dev/bulkV2"
            
            payload = {
                "message": message,
                "language": "english",
                "route": "q",
                "numbers": mobile_number
            }
            
            headers = {
                'authorization': api_key,
                'Content-Type': "application/x-www-form-urlencoded",
                'Cache-Control': "no-cache"
            }
            
            response = requests.post(url, data=payload, headers=headers)
            
            if response.status_code == 200:
                return True, "SMS sent via Fast2SMS"
            else:
                return False, f"SMS failed: {response.text}"
                
        except Exception as e:
            return False, f"SMS method failed: {str(e)}"

if __name__ == "__main__":
    app = PathologyTestsForm()
    app.mainloop()