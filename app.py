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
import urllib.parse
import subprocess
import sys
import platform

# PDF generation libraries (optional)
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False
    print("pdfkit not available. Using HTML reports.")

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("weasyprint not available. Using HTML reports.")

class PathologyTestsForm(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("UJJIVAN Hospital Pathology System")
        self.geometry("600x450")
        self.configure(bg="#f0e1c6")
        
        # Create necessary directories
        os.makedirs('reports/completed_reports', exist_ok=True)
        os.makedirs('reports/temp', exist_ok=True)
        
        # Initialize database
        self.init_database()
        
        # WhatsApp Configuration
        self.whatsapp_enabled = True
        self.whatsapp_method = "web"  # Options: "web", "api", "desktop"
        
        # WhatsApp API Configuration (for future use)
        self.whatsapp_api_url = "https://graph.facebook.com/v17.0/"
        self.whatsapp_phone_number_id = ""  # Add your Phone Number ID here
        self.whatsapp_access_token = ""  # Add your Access Token here
        
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
        
        # GUI Setup
        self.setup_gui()
        
        # Start Flask server
        self.flask_app = Flask(__name__)
        self.setup_flask_routes()
        self.start_flask_server()
        
    def setup_gui(self):
        """Setup the main GUI window"""
        # Main title
        title_label = tk.Label(self, text="🏥 UJJIVAN HOSPITAL", 
                              font=("Arial", 24, "bold"), bg="#f0e1c6", fg="#003366")
        title_label.pack(pady=(20,5))
        
        subtitle_label = tk.Label(self, text="Pathology Laboratory System", 
                                 font=("Arial", 16), bg="#f0e1c6", fg="#003366")
        subtitle_label.pack(pady=(0,5))
        
        address_label = tk.Label(self, text="Vidyut Nagar, Gautam Budh Nagar, Uttar Pradesh - 201008", 
                                font=("Arial", 10), bg="#f0e1c6")
        address_label.pack(pady=(0,20))
        
        # Info frame
        info_frame = tk.Frame(self, bg="#f0e1c6", relief="ridge", bd=2)
        info_frame.pack(pady=10, padx=20, fill="x")
        
        info_text = """This system will open in your web browser where you can:
• Enter patient information
• Select pathology tests
• Enter test results
• Generate PDF reports
• Send reports via WhatsApp"""
        
        info_label = tk.Label(info_frame, text=info_text, bg="white", 
                             font=("Arial", 11), justify=tk.LEFT, padx=10, pady=10)
        info_label.pack(padx=5, pady=5, fill="x")
        
        # Launch button
        launch_btn = tk.Button(self, text="🚀 Launch Web Application", 
                              fg="white", bg="#28a745", font=("Arial", 16, "bold"), 
                              command=self.launch_web_app, height=2, width=25,
                              cursor="hand2")
        launch_btn.pack(pady=20)
        
        # Status frame
        status_frame = tk.Frame(self, bg="#f0e1c6")
        status_frame.pack(fill="x", padx=20, pady=10)
        
        # Status indicator
        self.status_canvas = tk.Canvas(status_frame, width=20, height=20, 
                                       bg="#f0e1c6", highlightthickness=0)
        self.status_canvas.pack(side="left", padx=(0,10))
        self.status_indicator = self.status_canvas.create_oval(2, 2, 18, 18, 
                                                              fill="green", outline="")
        
        self.status_label = tk.Label(status_frame, text="Server running on http://localhost:5000", 
                                   font=("Arial", 10), bg="#f0e1c6", fg="#666")
        self.status_label.pack(side="left")
        
        # Reports directory link
        reports_btn = tk.Button(self, text="📁 Open Reports Folder", 
                              command=self.open_reports_folder,
                              bg="#007bff", fg="white", font=("Arial", 10))
        reports_btn.pack(pady=5)
        
    def open_reports_folder(self):
        """Open the reports folder in file explorer"""
        reports_path = os.path.join(os.getcwd(), 'reports', 'completed_reports')
        if os.path.exists(reports_path):
            if platform.system() == 'Windows':
                os.startfile(reports_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', reports_path])
            else:  # Linux
                subprocess.run(['xdg-open', reports_path])
        else:
            messagebox.showerror("Error", "Reports folder not found!")

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
        
        @self.flask_app.route('/')
        def home():
            """Serve the main web form with patient info and test selection"""
            html = self.get_main_web_form()
            return html

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
                    return "Error: No patient data provided", 400
                
                # Generate the HTML form with current data
                html_content = self.generate_exact_format_html_form(patient_data, selected_tests)
                return html_content
                
            except Exception as e:
                return f"Error loading form: {str(e)}", 500

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
                
                # Generate report files
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                patient_name_clean = patient_data.get('name', 'Unknown').replace(' ', '_').replace('/', '_').replace('\\', '_')
                
                # Generate HTML report
                html_content = self.generate_pdf_html(patient_data, test_results)
                html_filename = f"Pathology_Report_{patient_name_clean}_{timestamp}.html"
                html_filepath = os.path.join('reports', 'completed_reports', html_filename)
                
                with open(html_filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # Try to generate PDF if possible
                pdf_generated = False
                pdf_url = f"http://localhost:5000/view-report/{html_filename}"
                
                if PDFKIT_AVAILABLE or WEASYPRINT_AVAILABLE:
                    pdf_filename = f"Pathology_Report_{patient_name_clean}_{timestamp}.pdf"
                    pdf_filepath = os.path.join('reports', 'completed_reports', pdf_filename)
                    
                    if self.generate_pdf(html_content, pdf_filepath):
                        pdf_generated = True
                        pdf_url = f"http://localhost:5000/view-report/{pdf_filename}"
                        print(f"✅ PDF saved to: {pdf_filepath}")
                
                # Send WhatsApp message with report link
                whatsapp_success, whatsapp_message = self.send_whatsapp_message(
                    patient_data.get('mobile', ''), 
                    patient_data,
                    pdf_url
                )
                
                # Store in database
                report_path = pdf_filepath if pdf_generated else html_filepath
                db_success = self.store_completed_report(
                    patient_data, 
                    test_results, 
                    report_path, 
                    whatsapp_success, 
                    whatsapp_message
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Report submitted successfully!',
                    'whatsapp_status': 'sent' if whatsapp_success else 'failed',
                    'whatsapp_message': whatsapp_message,
                    'pdf_path': report_path,
                    'pdf_url': pdf_url,
                    'report_type': 'pdf' if pdf_generated else 'html'
                })
                    
            except Exception as e:
                print(f"❌ Error in form submission: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'message': f'Server Error: {str(e)}'
                }), 500

        @self.flask_app.route('/view-report/<filename>')
        def view_report(filename):
            """View report in browser"""
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
                elif filename.lower().endswith('.html'):
                    mimetype = 'text/html'
                else:
                    mimetype = 'application/octet-stream'
                
                return send_from_directory(directory, filename, mimetype=mimetype)
                    
            except Exception as e:
                return jsonify({'error': str(e)}), 404

        @self.flask_app.route('/static/<path:filename>')
        def serve_static(filename):
            """Serve static files"""
            return send_from_directory('static', filename)

        @self.flask_app.after_request
        def after_request(response):
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            return response

    def get_main_web_form(self):
        """Return the main web form HTML"""
        today_date = datetime.now().strftime('%Y-%m-%d')
        
        html = f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>UJJIVAN Hospital - Pathology System</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    min-height: 100vh;
                    padding: 20px;
                }}
                .hospital-card {{
                    background: white;
                    border-radius: 20px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                    padding: 30px;
                    margin-bottom: 20px;
                }}
                .hospital-header {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 3px solid #003366;
                }}
                .hospital-header h1 {{
                    color: #003366;
                    font-weight: 700;
                    font-size: 2.5rem;
                    margin-bottom: 10px;
                }}
                .hospital-header h3 {{
                    color: #666;
                    font-size: 1.2rem;
                }}
                .section-title {{
                    background: #003366;
                    color: white;
                    padding: 15px 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                    font-size: 1.2rem;
                    font-weight: 600;
                }}
                .test-category {{
                    background: #f8f9fa;
                    border-left: 4px solid #28a745;
                    padding: 15px;
                    margin-bottom: 15px;
                    border-radius: 5px;
                }}
                .test-category h5 {{
                    color: #003366;
                    margin-bottom: 15px;
                    font-weight: 600;
                }}
                .form-label {{
                    font-weight: 600;
                    color: #495057;
                }}
                .btn-generate {{
                    background: #28a745;
                    color: white;
                    font-weight: 600;
                    padding: 15px 30px;
                    font-size: 1.2rem;
                    border: none;
                    border-radius: 10px;
                    width: 100%;
                    transition: all 0.3s;
                }}
                .btn-generate:hover {{
                    background: #218838;
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(40,167,69,0.3);
                }}
                .info-box {{
                    background: #e7f3ff;
                    border-radius: 10px;
                    padding: 15px;
                    margin-bottom: 20px;
                    border: 1px solid #b8daff;
                }}
                .required-field::after {{
                    content: " *";
                    color: red;
                }}
                @media (max-width: 768px) {{
                    .hospital-header h1 {{
                        font-size: 1.8rem;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="hospital-card">
                    <div class="hospital-header">
                        <h1>🏥 UJJIVAN HOSPITAL</h1>
                        <h3>Pathology Laboratory System</h3>
                        <p class="text-muted">Vidyut Nagar, Gautam Budh Nagar, Uttar Pradesh - 201008</p>
                    </div>
                    
                    <div class="info-box">
                        <h5>📋 Instructions:</h5>
                        <ul class="mb-0">
                            <li>Fill in all patient details (fields marked with * are required)</li>
                            <li>Select the tests to be performed</li>
                            <li>Click "Generate Fillable Form" to enter test results</li>
                            <li>After entering results, submit to generate report and send via WhatsApp</li>
                        </ul>
                    </div>
                    
                    <div class="section-title">
                        <i class="bi bi-person"></i> Patient Information
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label required-field">Patient Name</label>
                            <input type="text" class="form-control" id="patientName" placeholder="Enter full name" required>
                        </div>
                        <div class="col-md-3 mb-3">
                            <label class="form-label required-field">Age</label>
                            <input type="number" class="form-control" id="patientAge" placeholder="Age" required>
                        </div>
                        <div class="col-md-3 mb-3">
                            <label class="form-label required-field">Gender</label>
                            <select class="form-control" id="patientGender" required>
                                <option value="">Select Gender</option>
                                <option value="Male">Male</option>
                                <option value="Female">Female</option>
                                <option value="Other">Other</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label class="form-label required-field">Mobile Number</label>
                            <input type="tel" class="form-control" id="patientMobile" placeholder="10 digit mobile" required>
                            <small class="text-muted">WhatsApp reports will be sent to this number</small>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Doctor Name</label>
                            <input type="text" class="form-control" id="doctorName" placeholder="Referring doctor">
                        </div>
                        <div class="col-md-2 mb-3">
                            <label class="form-label">OPD No</label>
                            <input type="text" class="form-control" id="opdNo" placeholder="OPD number">
                        </div>
                        <div class="col-md-2 mb-3">
                            <label class="form-label">Sample Date</label>
                            <input type="date" class="form-control" id="sampleDate" value="{today_date}">
                        </div>
                    </div>
                    
                    <div class="section-title">
                        <i class="bi bi-clipboard-check"></i> Select Tests
                    </div>
                    
                    <div class="row">
        '''
        
        # Add test categories
        for category, tests in self.tests.items():
            html += f'''
                <div class="col-md-6">
                    <div class="test-category">
                        <h5>{category}</h5>
                        <div class="row">
            '''
            
            for test in tests:
                test_id = f"test_{category}_{test.replace(' ', '_').replace('-', '_').replace('/', '_')}"
                html += f'''
                            <div class="col-12 mb-2">
                                <div class="form-check">
                                    <input class="form-check-input test-checkbox" type="checkbox" 
                                           value="{test}" id="{test_id}">
                                    <label class="form-check-label" for="{test_id}">
                                        {test}
                                    </label>
                                </div>
                            </div>
                '''
            
            html += '''
                        </div>
                    </div>
                </div>
            '''
        
        html += '''
                    </div>
                    
                    <button class="btn-generate" onclick="generateForm()">
                        📋 Generate Fillable Form
                    </button>
                </div>
            </div>
            
            <script>
                function generateForm() {
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
                    if (!patientData.name) {
                        alert('Please enter patient name');
                        return;
                    }
                    if (!patientData.age) {
                        alert('Please enter patient age');
                        return;
                    }
                    if (!patientData.gender) {
                        alert('Please select patient gender');
                        return;
                    }
                    if (!patientData.mobile) {
                        alert('Please enter mobile number');
                        return;
                    }
                    
                    // Validate mobile number (10 digits)
                    const mobileRegex = /^[0-9]{10}$/;
                    if (!mobileRegex.test(patientData.mobile)) {
                        alert('Please enter a valid 10-digit mobile number');
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

                    // Show loading state
                    const btn = document.querySelector('.btn-generate');
                    const originalText = btn.innerHTML;
                    btn.innerHTML = '⏳ Loading...';
                    btn.disabled = true;

                    // Redirect to fillable form
                    const params = new URLSearchParams({
                        patient_data: JSON.stringify(patientData),
                        selected_tests: JSON.stringify(selectedTests)
                    });
                    
                    window.open('/fillable-form?' + params.toString(), '_blank');
                    
                    // Reset button
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }
            </script>
        </body>
        </html>
        '''
        return html

    def generate_exact_format_html_form(self, patient_data, selected_tests):
        """Generate HTML form for entering test results"""
        serial_no = 1
        
        # Start building the HTML
        html = f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Enter Test Results - UJJIVAN Hospital</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{
                    background: #f8f9fa;
                    font-family: 'Times New Roman', serif;
                    padding: 20px;
                }}
                .report-container {{
                    background: white;
                    border: 2px solid #003366;
                    border-radius: 15px;
                    padding: 30px;
                    max-width: 1200px;
                    margin: 0 auto;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    border-bottom: 3px solid #003366;
                    margin-bottom: 25px;
                    padding-bottom: 15px;
                }}
                .header h2 {{
                    color: #003366;
                    font-weight: bold;
                    font-size: 2rem;
                    margin-bottom: 5px;
                }}
                .header p {{
                    color: #666;
                    margin-bottom: 5px;
                }}
                .patient-info {{
                    background: #f0f7ff;
                    border: 1px solid #003366;
                    border-radius: 10px;
                    padding: 15px;
                    margin-bottom: 25px;
                }}
                .patient-info p {{
                    margin-bottom: 8px;
                    font-size: 1rem;
                }}
                .section-title {{
                    background: #003366;
                    color: white;
                    padding: 10px 15px;
                    border-radius: 5px;
                    margin: 20px 0 15px 0;
                    font-weight: bold;
                    font-size: 1.2rem;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }}
                th, td {{
                    border: 1px solid #003366;
                    padding: 10px;
                    vertical-align: middle;
                }}
                th {{
                    background: #e8f0ff;
                    font-weight: 600;
                    color: #003366;
                    text-align: center;
                }}
                input.result {{
                    width: 100%;
                    border: none;
                    border-bottom: 2px solid #ccc;
                    padding: 5px;
                    font-size: 1rem;
                    transition: border-color 0.3s;
                }}
                input.result:focus {{
                    outline: none;
                    border-bottom-color: #28a745;
                }}
                .normal-range {{
                    font-size: 0.9rem;
                    color: #666;
                    font-style: italic;
                }}
                .footer {{
                    margin-top: 40px;
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-end;
                }}
                .signature {{
                    text-align: right;
                }}
                .signature-line {{
                    width: 200px;
                    border-bottom: 2px solid #000;
                    margin-top: 10px;
                }}
                .btn-submit {{
                    background: #28a745;
                    color: white;
                    font-weight: bold;
                    padding: 15px 40px;
                    font-size: 1.2rem;
                    border: none;
                    border-radius: 10px;
                    transition: all 0.3s;
                }}
                .btn-submit:hover {{
                    background: #218838;
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(40,167,69,0.3);
                }}
                .btn-clear {{
                    background: #6c757d;
                    color: white;
                    font-weight: bold;
                    padding: 10px 30px;
                    border: none;
                    border-radius: 5px;
                }}
                .abnormal-value {{
                    color: #dc3545;
                    font-weight: bold;
                }}
                @media print {{
                    body {{
                        background: white;
                        padding: 0;
                    }}
                    .report-container {{
                        border: 1px solid #000;
                        box-shadow: none;
                        padding: 20px;
                    }}
                    .btn-submit, .btn-clear {{
                        display: none;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="report-container">
                <div class="header">
                    <h2>🏥 UJJIVAN HOSPITAL</h2>
                    <p>Pathology Laboratory • Vidyut Nagar, Gautam Budh Nagar, UP - 201008</p>
                    <p>📞 Hospital: 0120-1234567 | 📧 Email: pathology@ujjivanhospital.com</p>
                </div>
                
                <div class="patient-info">
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>Patient Name:</strong> {patient_data['name']}</p>
                            <p><strong>Age/Sex:</strong> {patient_data['age']} / {patient_data['gender']}</p>
                            <p><strong>Mobile:</strong> {patient_data['mobile']}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>OPD No:</strong> {patient_data['opd_no'] or 'N/A'}</p>
                            <p><strong>Doctor:</strong> {patient_data['doctor'] or 'N/A'}</p>
                            <p><strong>Sample Date:</strong> {patient_data['sample_date']}</p>
                        </div>
                    </div>
                </div>
        '''
        
        # Group tests by category
        test_categories = {}
        for category, tests in self.tests.items():
            category_tests = [t for t in tests if t in selected_tests]
            if category_tests:
                test_categories[category] = category_tests
        
        # Add each category
        for category, tests in test_categories.items():
            html += f'''
                <div class="section-title">{category}</div>
                <table>
                    <thead>
                        <tr>
                            <th style="width: 5%">S.No</th>
                            <th style="width: 40%">Test Description</th>
                            <th style="width: 25%">Normal Range</th>
                            <th style="width: 30%">Result Value</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            
            for test in tests:
                normal_range = self.normal_ranges.get(test, "Not specified")
                test_id = test.replace(' ', '_').replace('-', '_').replace('/', '_').replace("'", "").replace(",", "")
                
                html += f'''
                        <tr>
                            <td class="text-center">{serial_no}</td>
                            <td><strong>{test}</strong></td>
                            <td class="normal-range">{normal_range}</td>
                            <td>
                                <input type="text" class="result" 
                                       placeholder="Enter value" 
                                       name="{test}" 
                                       id="{test_id}"
                                       data-test="{test}"
                                       data-normal="{normal_range}"
                                       onchange="checkAbnormal(this)">
                            </td>
                        </tr>
                '''
                serial_no += 1
            
            html += '''
                    </tbody>
                </table>
            '''
        
        html += f'''
                <div class="footer">
                    <div>
                        <p><strong>Test Date:</strong> {patient_data['sample_date']}</p>
                        <p><strong>Report Date:</strong> {datetime.now().strftime('%d-%m-%Y')}</p>
                    </div>
                    <div class="signature">
                        <p><strong>Signature</strong></p>
                        <div class="signature-line"></div>
                        <p><small>(Pathologist)</small></p>
                    </div>
                </div>
                
                <div class="row mt-4">
                    <div class="col-md-12 text-center">
                        <button class="btn-submit" onclick="submitForm()">
                            ✅ Submit & Send WhatsApp Report
                        </button>
                    </div>
                </div>
            </div>
            
            <script>
                function checkAbnormal(input) {{
                    const value = input.value.trim();
                    const testName = input.getAttribute('data-test');
                    const normalRange = input.getAttribute('data-normal');
                    
                    if (value) {{
                        // Simple abnormal detection based on keywords
                        const lowerValue = value.toLowerCase();
                        if (lowerValue.includes('positive') || 
                            lowerValue.includes('reactive') || 
                            lowerValue.includes('abnormal') ||
                            lowerValue.includes('high') ||
                            lowerValue.includes('low')) {{
                            input.style.borderBottom = '2px solid #dc3545';
                            input.style.color = '#dc3545';
                        }} else {{
                            input.style.borderBottom = '2px solid #28a745';
                            input.style.color = '#000';
                        }}
                    }}
                }}
                
                function submitForm() {{
                    const inputs = document.querySelectorAll('input.result');
                    const testResults = {{}};
                    let hasValues = false;
                    
                    inputs.forEach(input => {{
                        if (input.value.trim() !== '') {{
                            testResults[input.name] = input.value;
                            hasValues = true;
                        }}
                    }});
                    
                    if (!hasValues) {{
                        alert('Please enter at least one test result.');
                        return;
                    }}
                    
                    // Confirm submission
                    if (!confirm('Are you sure you want to submit this report? It will be sent to the patient via WhatsApp.')) {{
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
                    
                    // Show loading state
                    const btn = document.querySelector('.btn-submit');
                    const originalText = btn.innerHTML;
                    btn.innerHTML = '⏳ Submitting...';
                    btn.disabled = true;
                    
                    fetch('http://localhost:5000/submit-report', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify(submissionData)
                    }})
                    .then(response => {{
                        if (!response.ok) {{
                            return response.json().then(err => {{
                                throw new Error(err.message || 'Server error');
                            }}).catch(() => {{
                                throw new Error('HTTP error ' + response.status);
                            }});
                        }}
                        return response.json();
                    }})
                    .then(data => {{
                        if (data.success) {{
                            alert(`✅ Report submitted successfully!\\n\\n{data.message}\\n\\nWhatsApp Status: {data.whatsapp_message}\\n\\nThe patient can view their report at:\\n{data.pdf_url}`);
                            
                            // Open report in new tab
                            if (data.pdf_url) {{
                                window.open(data.pdf_url, '_blank');
                            }}
                            
                            // Ask if user wants to print
                            if (confirm('Do you want to print the report?')) {{
                                window.print();
                            }}
                        }} else {{
                            alert('❌ Error: ' + data.message);
                        }}
                    }})
                    .catch(error => {{
                        alert('❌ Error submitting form: ' + error);
                        console.error('Error:', error);
                    }})
                    .finally(() => {{
                        // Reset button
                        btn.innerHTML = originalText;
                        btn.disabled = false;
                    }});
                }}
            </script>
        </body>
        </html>
        '''
        return html

    def generate_pdf_html(self, patient_data, test_results):
        """Generate HTML for PDF with filled results"""
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Pathology Report - {patient_data.get('name', '')}</title>
            <style>
                body {{ 
                    font-family: 'Times New Roman', serif; 
                    margin: 20px;
                    line-height: 1.4;
                }}
                .header {{ 
                    text-align: center; 
                    border-bottom: 2px solid #003366; 
                    padding-bottom: 10px; 
                    margin-bottom: 20px; 
                }}
                .header h1 {{
                    color: #003366;
                    margin-bottom: 5px;
                    font-size: 24px;
                }}
                .hospital-info {{
                    font-size: 12px;
                    color: #666;
                }}
                .patient-info {{ 
                    margin-bottom: 20px;
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    border: 1px solid #003366;
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
                @media print {{
                    body {{ margin: 0; padding: 10px; }}
                }}
                .watermark {{
                    position: fixed;
                    bottom: 10px;
                    right: 10px;
                    opacity: 0.1;
                    font-size: 50px;
                    color: #003366;
                    z-index: -1;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>UJJIVAN HOSPITAL</h1>
                <div class="hospital-info">
                    <p>Pathology Laboratory</p>
                    <p>Vidyut Nagar, Gautam Budh Nagar, Uttar Pradesh - 201008</p>
                    <p>Phone: 0120-1234567 | Email: pathology@ujjivanhospital.com</p>
                </div>
                <h2>PATHOLOGY REPORT</h2>
            </div>
            
            <div class="patient-info">
                <p><strong>Patient Name:</strong> {patient_data.get('name', '')}</p>
                <p><strong>Age/Gender:</strong> {patient_data.get('age', '')}/{patient_data.get('gender', '')}</p>
                <p><strong>Mobile:</strong> {patient_data.get('mobile', '')}</p>
                <p><strong>Doctor:</strong> {patient_data.get('doctor', '')}</p>
                <p><strong>OPD No:</strong> {patient_data.get('opd_no', 'N/A')}</p>
                <p><strong>Sample Date:</strong> {patient_data.get('sample_date', '')}</p>
                <p><strong>Report Date:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M')}</p>
                <p><strong>Report ID:</strong> RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}</p>
            </div>
            
            <div class="section">
                <div class="section-title">TEST RESULTS</div>
                <table>
                    <thead>
                        <tr>
                            <th width="5%">S.No</th>
                            <th width="40%">Test Name</th>
                            <th width="25%">Normal Range</th>
                            <th width="30%">Result</th>
                        </tr>
                    </thead>
                    <tbody>
        '''
        
        # Group tests by category
        test_categories = {}
        for category, tests in self.tests.items():
            test_categories[category] = []
        
        # Add results to categories
        for test_name, result in test_results.items():
            category_found = False
            for category, tests in self.tests.items():
                if test_name in tests:
                    test_categories[category].append((test_name, result))
                    category_found = True
                    break
            if not category_found:
                test_categories.get("OTHER TESTS", []).append((test_name, result))
        
        # Generate table rows
        serial_no = 1
        for category, tests in test_categories.items():
            if tests:
                html_content += f'''
                    <tr>
                        <td colspan="4" style="background: #e8f0ff; font-weight: bold; text-align: center; font-size: 14px;">
                            {category}
                        </td>
                    </tr>
                '''
                
                for test_name, result in tests:
                    normal_range = self.normal_ranges.get(test_name, "Not specified")
                    
                    # Check for abnormal values
                    status_class = "normal"
                    result_str = str(result).lower()
                    if any(word in result_str for word in ['positive', 'high', 'low', 'abnormal', 'reactive', 'detected']):
                        status_class = "abnormal"
                    
                    html_content += f'''
                        <tr>
                            <td>{serial_no}</td>
                            <td><strong>{test_name}</strong></td>
                            <td><span class="normal-range">{normal_range}</span></td>
                            <td class="{status_class}"><strong>{result}</strong></td>
                        </tr>
                    '''
                    serial_no += 1
        
        html_content += '''
                    </tbody>
                </table>
            </div>
            
            <div class="footer">
                <p><strong>Dr. [Name]</strong></p>
                <p>Pathologist</p>
                <p>License No: PATH/2024/001</p>
                <p>_________________________</p>
                <p>Signature</p>
            </div>
            
            <div style="margin-top: 20px; font-size: 10px; color: #666; text-align: center; border-top: 1px solid #eee; padding-top: 10px;">
                <p>This is a computer generated report. For any queries, please contact the laboratory.</p>
                <p>Report generated on: ''' + datetime.now().strftime('%d-%m-%Y %H:%M:%S') + '''</p>
            </div>
            
            <div class="watermark">UJJIVAN HOSPITAL</div>
        </body>
        </html>
        '''
        return html_content

    def generate_pdf(self, html_content, output_path):
        """Generate PDF from HTML content using available methods"""
        try:
            # Try WeasyPrint first (better quality)
            if WEASYPRINT_AVAILABLE:
                try:
                    HTML(string=html_content, encoding='utf-8').write_pdf(output_path)
                    print(f"✅ PDF generated with WeasyPrint: {output_path}")
                    return True
                except Exception as e:
                    print(f"WeasyPrint failed: {e}")
            
            # Try pdfkit next
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
                    
                    # Try to find wkhtmltopdf
                    possible_paths = [
                        '/usr/bin/wkhtmltopdf',
                        '/usr/local/bin/wkhtmltopdf',
                        'C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe',
                        'C:/wkhtmltopdf/bin/wkhtmltopdf.exe'
                    ]
                    
                    config = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            config = pdfkit.configuration(wkhtmltopdf=path)
                            break
                    
                    if config:
                        pdfkit.from_string(html_content, output_path, options=options, configuration=config)
                    else:
                        pdfkit.from_string(html_content, output_path, options=options)
                    
                    print(f"✅ PDF generated with pdfkit: {output_path}")
                    return True
                    
                except Exception as e:
                    print(f"pdfkit failed: {e}")
            
            print("⚠️ No PDF generation method available. Using HTML report.")
            return False
            
        except Exception as e:
            print(f"❌ Error generating PDF: {e}")
            return False

    def store_completed_report(self, patient_data, test_results, report_path, whatsapp_success, whatsapp_message):
        """Store completed report in database"""
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
                report_path,
                whatsapp_status,
                whatsapp_message
            ))
            
            self.conn.commit()
            print(f"✅ Report stored in database. WhatsApp: {whatsapp_status}")
            return True
            
        except Exception as e:
            print(f"❌ Error storing report: {e}")
            return False

    def validate_mobile_number(self, mobile_number):
        """Validate and format mobile number"""
        try:
            # Remove any non-digit characters
            cleaned = re.sub(r'\D', '', str(mobile_number))
            
            # Check if it's a valid Indian mobile number
            if len(cleaned) == 10 and cleaned[0] in ['6', '7', '8', '9']:
                return f"91{cleaned}", None
            elif len(cleaned) == 12 and cleaned.startswith('91'):
                return cleaned, None
            else:
                return None, "Invalid mobile number format. Please enter a valid 10-digit Indian mobile number."
                
        except Exception as e:
            return None, f"Mobile validation error: {str(e)}"

    def send_whatsapp_message(self, mobile_number, patient_data, report_url):
        """Send WhatsApp message with report link"""
        try:
            # Validate mobile number
            formatted_mobile, mobile_error = self.validate_mobile_number(mobile_number)
            if mobile_error:
                return False, mobile_error
            
            print(f"📱 Preparing WhatsApp for: {formatted_mobile}")
            
            # Create message
            message = self.create_whatsapp_message(patient_data, report_url)
            
            # Method 1: Try WhatsApp Web (opens in browser)
            try:
                encoded_message = urllib.parse.quote(message)
                whatsapp_url = f"https://web.whatsapp.com/send?phone={formatted_mobile}&text={encoded_message}"
                
                # Open in default browser
                webbrowser.open(whatsapp_url)
                
                print("✅ WhatsApp Web opened in browser")
                return True, "WhatsApp Web opened - please send manually"
                
            except Exception as e:
                print(f"WhatsApp Web failed: {e}")
            
            # Method 2: Try WhatsApp Desktop app
            try:
                if platform.system() == 'Windows':
                    # Try to open WhatsApp Desktop
                    encoded_message = urllib.parse.quote(message)
                    whatsapp_url = f"whatsapp://send?phone={formatted_mobile}&text={encoded_message}"
                    webbrowser.open(whatsapp_url)
                    return True, "WhatsApp Desktop opened - please send manually"
            except:
                pass
            
            # Method 3: Show message in dialog
            self.show_message_dialog(patient_data, report_url)
            
            return True, f"Report URL generated: {report_url}"
            
        except Exception as e:
            error_msg = f"WhatsApp preparation failed: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def show_message_dialog(self, patient_data, report_url):
        """Show dialog with message to copy"""
        message = self.create_whatsapp_message(patient_data, report_url)
        
        # Create a simple dialog
        dialog = tk.Toplevel(self)
        dialog.title("WhatsApp Message Ready")
        dialog.geometry("600x500")
        dialog.configure(bg="white")
        
        # Make it modal
        dialog.transient(self)
        dialog.grab_set()
        
        # Title
        tk.Label(dialog, text="📱 WhatsApp Message", font=("Arial", 16, "bold"), 
                bg="white", fg="#003366").pack(pady=10)
        
        # Instructions
        tk.Label(dialog, text="Copy this message and send it to the patient via WhatsApp", 
                font=("Arial", 10), bg="white", fg="#666").pack(pady=5)
        
        # Message text area
        text_frame = tk.Frame(dialog, bg="white")
        text_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        text_widget = tk.Text(text_frame, wrap="word", font=("Arial", 10), 
                             height=20, width=60)
        text_widget.insert("1.0", message)
        text_widget.config(state="normal")
        
        # Add scrollbar
        scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        button_frame = tk.Frame(dialog, bg="white")
        button_frame.pack(pady=10)
        
        def copy_message():
            dialog.clipboard_clear()
            dialog.clipboard_append(message)
            tk.Label(button_frame, text="✓ Copied!", fg="green", bg="white").pack(side="left", padx=5)
        
        def open_whatsapp():
            encoded_message = urllib.parse.quote(message)
            whatsapp_url = f"https://web.whatsapp.com/send?text={encoded_message}"
            webbrowser.open(whatsapp_url)
        
        tk.Button(button_frame, text="📋 Copy Message", command=copy_message,
                 bg="#007bff", fg="white", font=("Arial", 10)).pack(side="left", padx=5)
        
        tk.Button(button_frame, text="🌐 Open WhatsApp Web", command=open_whatsapp,
                 bg="#25D366", fg="white", font=("Arial", 10)).pack(side="left", padx=5)
        
        tk.Button(button_frame, text="✅ Close", command=dialog.destroy,
                 bg="#6c757d", fg="white", font=("Arial", 10)).pack(side="left", padx=5)
        
        # Report URL
        url_frame = tk.Frame(dialog, bg="white", relief="ridge", bd=1)
        url_frame.pack(padx=20, pady=10, fill="x")
        
        tk.Label(url_frame, text="Report URL:", font=("Arial", 10, "bold"), 
                bg="white").pack(pady=5)
        
        url_entry = tk.Entry(url_frame, width=50, font=("Arial", 9))
        url_entry.insert(0, report_url)
        url_entry.config(state="readonly")
        url_entry.pack(pady=5, padx=10)
        
        def copy_url():
            dialog.clipboard_clear()
            dialog.clipboard_append(report_url)
            tk.Label(url_frame, text="URL copied!", fg="green", bg="white").pack()
        
        tk.Button(url_frame, text="📋 Copy URL", command=copy_url,
                 bg="#28a745", fg="white", font=("Arial", 9)).pack(pady=5)

    def create_whatsapp_message(self, patient_data, report_url):
        """Create WhatsApp message content"""
        return f"""🔬 *UJJIVAN HOSPITAL - PATHOLOGY REPORT*

Dear {patient_data.get('name', 'Patient')},

Your pathology test report is ready.

*Patient Details:*
• Name: {patient_data.get('name', '')}
• Age: {patient_data.get('age', '')}
• Gender: {patient_data.get('gender', '')}
• Doctor: {patient_data.get('doctor', 'N/A')}
• Sample Date: {patient_data.get('sample_date', '')}
• OPD No: {patient_data.get('opd_no', 'N/A')}

📄 *View Your Report Online:*
{report_url}

*Instructions:*
1. Click/tap the link above
2. Your report will open in browser
3. You can download/print if needed

*Report ID:* {patient_data.get('opd_no', 'N/A')}
*Generated on:* {datetime.now().strftime('%d-%m-%Y %I:%M %p')}

*Note:* This link is valid for 30 days. Contact hospital for queries.

Thank you for choosing UJJIVAN Hospital.
📍 Vidyut Nagar, Gautam Budh Nagar, UP - 201008
📞 Hospital: 0120-1234567
"""

    def start_flask_server(self):
        """Start Flask server in a separate thread"""
        def run_flask():
            try:
                print("="*50)
                print("🚀 Starting UJJIVAN Hospital Pathology System")
                print("="*50)
                print(f"📅 Date: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
                print(f"📁 Reports directory: {os.path.abspath('reports/completed_reports')}")
                print(f"🌐 Web interface: http://localhost:5000")
                print(f"📱 WhatsApp integration: {'Enabled' if self.whatsapp_enabled else 'Disabled'}")
                print("="*50)
                
                self.flask_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                print(f"❌ Flask server error: {e}")
                self.status_label.config(text=f"Server error: {e}")
        
        self.flask_thread = threading.Thread(target=run_flask, daemon=True)
        self.flask_thread.start()
        time.sleep(2)  # Give server time to start

    def launch_web_app(self):
        """Launch the web application in browser"""
        self.status_label.config(text="Opening web application...")
        
        flask_url = "http://localhost:5000/"
        webbrowser.open(flask_url)
        
        self.status_label.config(text="✅ Web application opened in browser!")
        messagebox.showinfo("Success", 
            f"Web application opened in browser!\n\n"
            f"If it doesn't load automatically, visit:\n{flask_url}\n\n"
            f"📁 Reports are saved in:\n{os.path.abspath('reports/completed_reports')}")

if __name__ == "__main__":
    app = PathologyTestsForm()
    
    # Handle window close
    def on_closing():
        try:
            app.conn.close()
        except:
            pass
        app.destroy()
    
    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()