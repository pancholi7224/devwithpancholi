try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    TK_AVAILABLE = True
except Exception:
    tk = None
    ttk = None
    messagebox = None
    TK_AVAILABLE = False
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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
except Exception as e:
    WEASYPRINT_AVAILABLE = False
    print(f"weasyprint not available ({e}). Using HTML reports.")

TkBase = tk.Tk if TK_AVAILABLE else object

class PathologyTestsForm(TkBase):
    def __init__(self, enable_gui=True, auto_start_server=True):
        self.enable_gui = enable_gui and TK_AVAILABLE
        self.auto_start_server = auto_start_server

        if self.enable_gui:
            super().__init__()
            self.title("UJJIVAN Hospital Pathology System")
            self.geometry("600x450")
            self.configure(bg="#f0e1c6")
        
        # Create necessary directories
        # NOTE: On Vercel serverless deployments, filesystem writes are ephemeral.
        # Report files may be created during runtime but will not persist across cold starts.
        os.makedirs('reports/completed_reports', exist_ok=True)
        os.makedirs('reports/temp', exist_ok=True)
        
        # Initialize database
        self.init_database()
        
        # WhatsApp Configuration
        self.whatsapp_enabled = True
        self.whatsapp_method = "web"  # Options: "web", "api", "desktop"
        
        # WhatsApp API configuration
        self.whatsapp_api_url = os.getenv("WHATSAPP_API_URL", "https://graph.facebook.com/v17.0/").strip()
        if not self.whatsapp_api_url.endswith("/"):
            self.whatsapp_api_url += "/"
        self.whatsapp_phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
        self.whatsapp_access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
        self.whatsapp_default_country_code = re.sub(
            r"\D", "", os.getenv("WHATSAPP_DEFAULT_COUNTRY_CODE", "91")
        ) or "91"
        self.whatsapp_template_name = os.getenv("WHATSAPP_TEMPLATE_NAME", "").strip()
        self.whatsapp_template_lang = os.getenv("WHATSAPP_TEMPLATE_LANG", "en_US").strip()
        template_vars_raw = os.getenv("WHATSAPP_TEMPLATE_BODY_VARS", "")
        self.whatsapp_template_body_vars = [
            item.strip() for item in template_vars_raw.split(",") if item.strip()
        ]

        # Fast2SMS configuration
        self.fast2sms_enabled = os.getenv("FAST2SMS_ENABLED", "true").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        self.fast2sms_api_key = os.getenv(
            "FAST2SMS_API_KEY",
            "h78RGZEINSaQV2wyvWu3cdfzBqYMtH5lTOsr4ejA0bCPxJ19XkkIftcr0isUQ54Co3hqxaG7zTFSlVRw",
        ).strip()
        self.fast2sms_route = os.getenv("FAST2SMS_ROUTE", "q").strip()
        self.fast2sms_language = os.getenv("FAST2SMS_LANGUAGE", "english").strip()
        self.fast2sms_send_always = os.getenv("FAST2SMS_SEND_ALWAYS", "true").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        
        # Hospital Contact Configuration
        self.hospital_phone = os.getenv("HOSPITAL_PHONE", "0120-1234567").strip()
        self.hospital_email = os.getenv("HOSPITAL_EMAIL", "support@ujjivanhospital.com").strip()
        
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
        # Start Flask server
        self.flask_app = Flask(__name__)
        self.setup_flask_routes()

        if self.enable_gui:
            # GUI Setup
            self.setup_gui()

        if self.auto_start_server:
            self.start_flask_server()
        
    def setup_gui(self):
        """Setup the main GUI window"""
        # Main title
        title_label = tk.Label(self, text=" UJJIVAN HOSPITAL", 
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
 Enter patient information
 Select pathology tests
 Enter test results
 Generate PDF reports
 Send reports via WhatsApp
 Patients can send messages to hospital"""
        
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
        reports_btn.pack(pady=10)

    def open_reports_folder(self):
        """Open the reports folder in file explorer"""
        reports_path = os.path.abspath('reports/completed_reports')
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
        """Initialize SQLite database for storing reports and messages"""
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
                    sms_status TEXT DEFAULT 'not_attempted',
                    sms_error TEXT,
                    report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Add SMS columns for existing databases created before SMS integration.
            self.cursor.execute("PRAGMA table_info(completed_reports)")
            existing_columns = {col[1] for col in self.cursor.fetchall()}
            if "test_results" not in existing_columns:
                self.cursor.execute("ALTER TABLE completed_reports ADD COLUMN test_results TEXT")
            if "pdf_path" not in existing_columns:
                self.cursor.execute("ALTER TABLE completed_reports ADD COLUMN pdf_path TEXT")
            if "whatsapp_status" not in existing_columns:
                self.cursor.execute("ALTER TABLE completed_reports ADD COLUMN whatsapp_status TEXT")
            if "whatsapp_error" not in existing_columns:
                self.cursor.execute("ALTER TABLE completed_reports ADD COLUMN whatsapp_error TEXT")
            if "sms_status" not in existing_columns:
                self.cursor.execute(
                    "ALTER TABLE completed_reports ADD COLUMN sms_status TEXT DEFAULT 'not_attempted'"
                )
            if "sms_error" not in existing_columns:
                self.cursor.execute("ALTER TABLE completed_reports ADD COLUMN sms_error TEXT")
            
            # Create table for patient messages
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS patient_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_name TEXT,
                    patient_email TEXT,
                    patient_mobile TEXT,
                    subject TEXT,
                    message TEXT,
                    message_type TEXT,
                    status TEXT DEFAULT 'unread',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    replied_at TIMESTAMP,
                    reply_message TEXT
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
                return f"Error: {str(e)}", 400

        @self.flask_app.route('/submit-report', methods=['POST'])
        def submit_report():
            """Handle report submission with WhatsApp integration"""
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
                base_url = self.get_public_base_url()
                pdf_url = f"{base_url}/view-report/{urllib.parse.quote(html_filename)}"
                
                if PDFKIT_AVAILABLE or WEASYPRINT_AVAILABLE:
                    pdf_filename = f"Pathology_Report_{patient_name_clean}_{timestamp}.pdf"
                    pdf_filepath = os.path.join('reports', 'completed_reports', pdf_filename)
                    
                    if self.generate_pdf(html_content, pdf_filepath):
                        pdf_generated = True
                        pdf_url = f"{base_url}/view-report/{urllib.parse.quote(pdf_filename)}"
                        print(f"PDF saved to: {pdf_filepath}")
                
                # Send WhatsApp message with report link
                whatsapp_success, whatsapp_message = self.send_whatsapp_message(
                    patient_data.get('mobile', ''), 
                    patient_data,
                    pdf_url
                )
                whatsapp_manual_url = None
                manual_mobile, manual_mobile_error = self.validate_mobile_number(patient_data.get('mobile', ''))
                if not manual_mobile_error:
                    whatsapp_manual_url = self.build_whatsapp_web_url(
                        manual_mobile,
                        self.create_whatsapp_message(patient_data, pdf_url),
                    )

                # Send SMS (always by default, or only when WhatsApp fails if FAST2SMS_SEND_ALWAYS=false)
                sms_success = None
                sms_message = "SMS not attempted."
                should_send_sms = self.fast2sms_enabled and (self.fast2sms_send_always or not whatsapp_success)
                if should_send_sms:
                    sms_success, sms_message = self.send_sms_via_fast2sms(
                        patient_data.get('mobile', ''),
                        self.create_sms_message(patient_data, pdf_url)
                    )

                delivery_success = bool(whatsapp_success) or bool(sms_success)
                delivery_status = "sent" if delivery_success else "failed"
                response_message = (
                    "Report submitted and notification sent successfully!"
                    if delivery_success
                    else "Report submitted, but message delivery failed."
                )
                
                # Store in database
                report_path = pdf_filepath if pdf_generated else html_filepath
                db_success = self.store_completed_report(
                    patient_data, 
                    test_results, 
                    report_path, 
                    whatsapp_success, 
                    whatsapp_message,
                    sms_success,
                    sms_message
                )
                
                return jsonify({
                    'success': True,
                    'message': response_message,
                    'delivery_status': delivery_status,
                    'delivery_success': delivery_success,
                    'whatsapp_status': 'sent' if whatsapp_success else 'failed',
                    'whatsapp_message': whatsapp_message,
                    'whatsapp_manual_url': whatsapp_manual_url,
                    'sms_status': 'not_attempted' if sms_success is None else ('sent' if sms_success else 'failed'),
                    'sms_message': sms_message,
                    'pdf_path': report_path,
                    'pdf_url': pdf_url,
                    'report_type': 'pdf' if pdf_generated else 'html'
                })
                    
            except Exception as e:
                print(f"Error in form submission: {e}")
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

        @self.flask_app.route('/contact-hospital')
        def contact_hospital():
            """Serve the patient contact form"""
            return self.get_contact_form_html()

        @self.flask_app.route('/submit-message', methods=['POST'])
        def submit_message():
            """Handle patient message submission"""
            try:
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
                
                # Validate required fields
                required_fields = ['name', 'email', 'mobile', 'subject', 'message']
                for field in required_fields:
                    if not data.get(field):
                        return jsonify({
                            'success': False,
                            'message': f'Missing required field: {field}'
                        }), 400
                
                # Store message in database
                try:
                    self.cursor.execute('''
                        INSERT INTO patient_messages 
                        (patient_name, patient_email, patient_mobile, subject, message, message_type, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        data.get('name'),
                        data.get('email'),
                        data.get('mobile'),
                        data.get('subject'),
                        data.get('message'),
                        data.get('message_type', 'general'),
                        'unread'
                    ))
                    self.conn.commit()
                    message_id = self.cursor.lastrowid
                    print(f"Patient message stored: ID {message_id}")
                except Exception as db_error:
                    print(f"Database error: {db_error}")
                    return jsonify({
                        'success': False,
                        'message': 'Failed to store message'
                    }), 500
                
                return jsonify({
                    'success': True,
                    'message': 'Your message has been sent successfully! We will respond within 24 hours.',
                    'message_id': message_id
                })
                
            except Exception as e:
                print(f"Error in message submission: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'message': f'Server Error: {str(e)}'
                }), 500

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
                    margin-bottom: 10px;
                }}
                .btn-generate:hover {{
                    background: #218838;
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(40,167,69,0.3);
                }}
                .btn-contact {{
                    background: #007bff;
                    color: white;
                    font-weight: 600;
                    padding: 15px 30px;
                    font-size: 1.2rem;
                    border: none;
                    border-radius: 10px;
                    width: 100%;
                    transition: all 0.3s;
                }}
                .btn-contact:hover {{
                    background: #0056b3;
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0,86,179,0.3);
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
                .quick-links {{
                    display: flex;
                    gap: 10px;
                    margin-top: 20px;
                    flex-wrap: wrap;
                }}
                .quick-links a {{
                    flex: 1;
                    min-width: 150px;
                    padding: 10px;
                    text-align: center;
                    border-radius: 5px;
                    text-decoration: none;
                    font-weight: 600;
                    transition: all 0.3s;
                }}
                .quick-links .whatsapp-link {{
                    background: #25D366;
                    color: white;
                }}
                .quick-links .whatsapp-link:hover {{
                    background: #1fa857;
                    transform: translateY(-2px);
                }}
                .quick-links .phone-link {{
                    background: #ffc107;
                    color: #333;
                }}
                .quick-links .phone-link:hover {{
                    background: #e0a800;
                    transform: translateY(-2px);
                }}
                @media (max-width: 768px) {{
                    .hospital-header h1 {{
                        font-size: 1.8rem;
                    }}
                    .quick-links {{
                        flex-direction: column;
                    }}
                    .quick-links a {{
                        min-width: auto;
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
                            <li>Have questions? Use the "Contact Hospital" button below to send a message</li>
                        </ul>
                    </div>
                    
                    <div class="section-title">
                        👤 Patient Information
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
                        ✅ Select Tests
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
                    
                    <button class="btn-contact" onclick="goToContactForm()">
                        💬 Contact Hospital / Send Message
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
                    
                    window.location.href = '/fillable-form?' + params.toString();
                }
                
                function goToContactForm() {
                    window.location.href = '/contact-hospital';
                }
            </script>
        </body>
        </html>
        '''
        return html

    def get_contact_form_html(self):
        """Return the contact/messaging form HTML for patients"""
        html = '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Contact UJJIVAN Hospital</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    min-height: 100vh;
                    padding: 20px;
                }
                .contact-card {
                    background: white;
                    border-radius: 20px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                    padding: 30px;
                    max-width: 700px;
                    margin: 0 auto;
                }
                .contact-header {
                    text-align: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 3px solid #003366;
                }
                .contact-header h1 {
                    color: #003366;
                    font-weight: 700;
                    font-size: 2rem;
                    margin-bottom: 10px;
                }
                .contact-header p {
                    color: #666;
                    font-size: 1.1rem;
                }
                .form-label {
                    font-weight: 600;
                    color: #495057;
                }
                .required-field::after {
                    content: " *";
                    color: red;
                }
                .btn-submit {
                    background: #28a745;
                    color: white;
                    font-weight: 600;
                    padding: 12px 30px;
                    font-size: 1.1rem;
                    border: none;
                    border-radius: 10px;
                    width: 100%;
                    transition: all 0.3s;
                    margin-top: 20px;
                }
                .btn-submit:hover {
                    background: #218838;
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(40,167,69,0.3);
                }
                .btn-back {
                    background: #6c757d;
                    color: white;
                    font-weight: 600;
                    padding: 12px 30px;
                    font-size: 1rem;
                    border: none;
                    border-radius: 10px;
                    width: 100%;
                    transition: all 0.3s;
                    margin-top: 10px;
                }
                .btn-back:hover {
                    background: #5a6268;
                    transform: translateY(-2px);
                }
                .info-box {
                    background: #e7f3ff;
                    border-radius: 10px;
                    padding: 15px;
                    margin-bottom: 20px;
                    border: 1px solid #b8daff;
                }
                .success-message {
                    display: none;
                    background: #d4edda;
                    border: 1px solid #c3e6cb;
                    color: #155724;
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }
                .error-message {
                    display: none;
                    background: #f8d7da;
                    border: 1px solid #f5c6cb;
                    color: #721c24;
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }
                .message-type-group {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }
                textarea {
                    resize: vertical;
                    min-height: 150px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="contact-card">
                    <div class="contact-header">
                        <h1>💬 Contact UJJIVAN Hospital</h1>
                        <p>Send us a message and we'll respond within 24 hours</p>
                    </div>
                    
                    <div id="successMessage" class="success-message">
                        ✅ Your message has been sent successfully! We will respond within 24 hours.
                    </div>
                    
                    <div id="errorMessage" class="error-message">
                        ❌ <span id="errorText"></span>
                    </div>
                    
                    <div class="info-box">
                        <h5>📞 Quick Contact:</h5>
                        <p><strong>Phone:</strong> 0120-1234567</p>
                        <p><strong>Email:</strong> support@ujjivanhospital.com</p>
                        <p><strong>WhatsApp:</strong> Reply to the report message you received</p>
                    </div>
                    
                    <form id="contactForm">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label required-field">Full Name</label>
                                <input type="text" class="form-control" id="patientName" placeholder="Your full name" required>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label required-field">Email</label>
                                <input type="email" class="form-control" id="patientEmail" placeholder="Your email" required>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label required-field">Mobile Number</label>
                            <input type="tel" class="form-control" id="patientMobile" placeholder="10 digit mobile number" required>
                        </div>
                        
                        <div class="message-type-group">
                            <label class="form-label required-field">Message Type</label>
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="messageType" id="typeGeneral" value="general" checked>
                                <label class="form-check-label" for="typeGeneral">
                                    General Inquiry
                                </label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="messageType" id="typeReport" value="report_query">
                                <label class="form-check-label" for="typeReport">
                                    Report Query / Clarification
                                </label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="messageType" id="typeComplaint" value="complaint">
                                <label class="form-check-label" for="typeComplaint">
                                    Complaint / Feedback
                                </label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="messageType" id="typeAppointment" value="appointment">
                                <label class="form-check-label" for="typeAppointment">
                                    Appointment Request
                                </label>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label required-field">Subject</label>
                            <input type="text" class="form-control" id="messageSubject" placeholder="What is this about?" required>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label required-field">Message</label>
                            <textarea class="form-control" id="messageContent" placeholder="Please describe your message..." required></textarea>
                        </div>
                        
                        <button type="submit" class="btn-submit">
                            📤 Send Message
                        </button>
                        
                        <button type="button" class="btn-back" onclick="goHome()">
                            ← Back to Home
                        </button>
                    </form>
                </div>
            </div>
            
            <script>
                document.getElementById('contactForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const name = document.getElementById('patientName').value;
                    const email = document.getElementById('patientEmail').value;
                    const mobile = document.getElementById('patientMobile').value;
                    const messageType = document.querySelector('input[name="messageType"]:checked').value;
                    const subject = document.getElementById('messageSubject').value;
                    const message = document.getElementById('messageContent').value;
                    
                    // Validate mobile
                    const mobileRegex = /^[0-9]{10}$/;
                    if (!mobileRegex.test(mobile)) {
                        showError('Please enter a valid 10-digit mobile number');
                        return;
                    }
                    
                    const submitBtn = document.querySelector('.btn-submit');
                    const originalText = submitBtn.innerHTML;
                    submitBtn.innerHTML = '⏳ Sending...';
                    submitBtn.disabled = true;
                    
                    try {
                        const response = await fetch('/submit-message', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                name: name,
                                email: email,
                                mobile: mobile,
                                subject: subject,
                                message: message,
                                message_type: messageType
                            })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            showSuccess(data.message);
                            document.getElementById('contactForm').reset();
                            setTimeout(() => {
                                window.location.href = '/';
                            }, 3000);
                        } else {
                            showError(data.message || 'Failed to send message');
                        }
                    } catch (error) {
                        showError('Error: ' + error.message);
                    } finally {
                        submitBtn.innerHTML = originalText;
                        submitBtn.disabled = false;
                    }
                });
                
                function showSuccess(message) {
                    const successDiv = document.getElementById('successMessage');
                    const errorDiv = document.getElementById('errorMessage');
                    errorDiv.style.display = 'none';
                    successDiv.textContent = message;
                    successDiv.style.display = 'block';
                }
                
                function showError(message) {
                    const errorDiv = document.getElementById('errorMessage');
                    const successDiv = document.getElementById('successMessage');
                    successDiv.style.display = 'none';
                    document.getElementById('errorText').textContent = message;
                    errorDiv.style.display = 'block';
                }
                
                function goHome() {
                    window.location.href = '/';
                }
            </script>
        </body>
        </html>
        '''
        return html

    def get_public_base_url(self):
        """Resolve public base URL for patient-facing links."""
        explicit_base_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
        if explicit_base_url:
            return explicit_base_url

        # If inside an HTTP request, derive the public host from headers.
        # This supports reverse proxies (Render, Nginx, etc.).
        try:
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip()
            forwarded_host = request.headers.get("X-Forwarded-Host", "").split(",")[0].strip()
            host = forwarded_host or request.host
            scheme = forwarded_proto or request.scheme or "http"
            if host:
                return f"{scheme}://{host}".rstrip("/")
        except Exception:
            pass

        # Fallback for local/offline execution.
        port = os.getenv("PORT", "5000").strip() or "5000"
        return f"http://localhost:{port}"

    def generate_exact_format_html_form(self, patient_data, selected_tests):
        """Generate the fillable form for entering test results"""
        today_date = datetime.now().strftime('%Y-%m-%d')
        
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
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    min-height: 100vh;
                    padding: 20px;
                }}
                .form-card {{
                    background: white;
                    border-radius: 20px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                    padding: 30px;
                    margin-bottom: 20px;
                }}
                .form-header {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 3px solid #003366;
                }}
                .form-header h1 {{
                    color: #003366;
                    font-weight: 700;
                    font-size: 2rem;
                    margin-bottom: 10px;
                }}
                .patient-info {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                    border-left: 4px solid #003366;
                }}
                .patient-info p {{
                    margin: 5px 0;
                    font-size: 0.95rem;
                }}
                .section-title {{
                    background: #003366;
                    color: white;
                    padding: 15px 20px;
                    border-radius: 10px;
                    margin: 20px 0 15px 0;
                    font-size: 1.1rem;
                    font-weight: 600;
                }}
                .form-label {{
                    font-weight: 600;
                    color: #495057;
                }}
                .form-control {{
                    border-radius: 5px;
                    border: 1px solid #ddd;
                }}
                .form-control:focus {{
                    border-color: #003366;
                    box-shadow: 0 0 0 0.2rem rgba(0, 51, 102, 0.25);
                }}
                .btn-submit {{
                    background: #28a745;
                    color: white;
                    font-weight: 600;
                    padding: 15px 30px;
                    font-size: 1.1rem;
                    border: none;
                    border-radius: 10px;
                    width: 100%;
                    transition: all 0.3s;
                    margin-top: 20px;
                }}
                .btn-submit:hover {{
                    background: #218838;
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(40,167,69,0.3);
                }}
                .btn-back {{
                    background: #6c757d;
                    color: white;
                    font-weight: 600;
                    padding: 12px 30px;
                    font-size: 1rem;
                    border: none;
                    border-radius: 10px;
                    width: 100%;
                    transition: all 0.3s;
                    margin-top: 10px;
                }}
                .btn-back:hover {{
                    background: #5a6268;
                    transform: translateY(-2px);
                }}
                .normal-range {{
                    font-size: 0.85rem;
                    color: #666;
                    font-style: italic;
                }}
                .success-message {{
                    display: none;
                    background: #d4edda;
                    border: 1px solid #c3e6cb;
                    color: #155724;
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }}
                .error-message {{
                    display: none;
                    background: #f8d7da;
                    border: 1px solid #f5c6cb;
                    color: #721c24;
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="form-card">
                    <div class="form-header">
                        <h1>📊 Enter Test Results</h1>
                        <p>Please enter the test results for the selected tests</p>
                    </div>
                    
                    <div id="successMessage" class="success-message">
                        ✅ Report submitted successfully!
                    </div>
                    
                    <div id="errorMessage" class="error-message">
                        ❌ <span id="errorText"></span>
                    </div>
                    
                    <div class="patient-info">
                        <h6 style="color: #003366; font-weight: 600; margin-bottom: 10px;">Patient Information</h6>
                        <p><strong>Name:</strong> {patient_data.get('name', '')}</p>
                        <p><strong>Age/Gender:</strong> {patient_data.get('age', '')}/{patient_data.get('gender', '')}</p>
                        <p><strong>Mobile:</strong> {patient_data.get('mobile', '')}</p>
                        <p><strong>Doctor:</strong> {patient_data.get('doctor', 'N/A')}</p>
                        <p><strong>OPD No:</strong> {patient_data.get('opd_no', 'N/A')}</p>
                    </div>
                    
                    <form id="resultsForm">
        '''
        
        # Group tests by category
        test_categories = {}
        for category, tests in self.tests.items():
            test_categories[category] = []
        
        # Add selected tests to categories
        for test_name in selected_tests:
            category_found = False
            for category, tests in self.tests.items():
                if test_name in tests:
                    test_categories[category].append(test_name)
                    category_found = True
                    break
            if not category_found:
                test_categories.get("OTHER TESTS", []).append(test_name)
        
        # Generate form fields for each test
        for category, tests in test_categories.items():
            if tests:
                html += f'''
                        <div class="section-title">{category}</div>
                        <div class="row">
                '''
                
                for test_name in tests:
                    normal_range = self.normal_ranges.get(test_name, "Not specified")
                    test_id = f"test_{test_name.replace(' ', '_').replace('-', '_').replace('/', '_')}"
                    
                    html += f'''
                            <div class="col-md-6 mb-3">
                                <label class="form-label" for="{test_id}">
                                    {test_name}
                                </label>
                                <input type="text" class="form-control" id="{test_id}" 
                                       name="{test_name}" placeholder="Enter result">
                                <small class="normal-range">Normal: {normal_range}</small>
                            </div>
                    '''
                
                html += '''
                        </div>
                '''
        
        # Store patient data as hidden fields
        html += f'''
                        <input type="hidden" id="patientData" value='{json.dumps(patient_data)}'>
                        
                        <button type="submit" class="btn-submit">
                            ✅ Submit Report & Send via WhatsApp
                        </button>
                        
                        <button type="button" class="btn-back" onclick="goHome()">
                            ← Back to Home
                        </button>
                    </form>
                </div>
            </div>
            
            <script>
                document.getElementById('resultsForm').addEventListener('submit', async function(e) {{
                    e.preventDefault();
                    
                    const patientData = JSON.parse(document.getElementById('patientData').value);
                    const testResults = {{}};
                    
                    // Collect all test results
                    const inputs = document.querySelectorAll('#resultsForm input[name]');
                    inputs.forEach(input => {{
                        if (input.value.trim()) {{
                            testResults[input.name] = input.value.trim();
                        }}
                    }});
                    
                    if (Object.keys(testResults).length === 0) {{
                        showError('Please enter at least one test result');
                        return;
                    }}
                    
                    const submitBtn = document.querySelector('.btn-submit');
                    const originalText = submitBtn.innerHTML;
                    submitBtn.innerHTML = '⏳ Submitting...';
                    submitBtn.disabled = true;
                    
                    try {{
                        const response = await fetch('/submit-report', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify({{
                                patient_data: patientData,
                                test_results: testResults
                            }})
                        }});
                        
                        const data = await response.json();
                        
                        if (data.success) {{
                            const whatsappInfo = data.whatsapp_message || 'WhatsApp not attempted';
                            const smsInfo = data.sms_message || 'SMS not attempted';
                            const deliveryFailed = data.delivery_status === 'failed' || data.delivery_success === false;
                            if (deliveryFailed) {{
                                if (data.whatsapp_manual_url) {{
                                    showSuccess('Report saved. WhatsApp API did not send automatically.\\n\\nWhatsApp: ' + whatsappInfo + '\\n\\nOpening WhatsApp Web now. Please click Send there.\\n\\nIf popup is blocked, open this link manually:\\n' + data.whatsapp_manual_url);
                                    setTimeout(() => {{
                                        const opened = window.open(data.whatsapp_manual_url, '_blank');
                                        if (!opened) {{
                                            window.location.href = data.whatsapp_manual_url;
                                        }}
                                    }}, 200);
                                }} else {{
                                    showError('Report saved but message was not sent.\\n\\nWhatsApp: ' + whatsappInfo + '\\n\\nSMS: ' + smsInfo + '\\n\\nPlease fix API setup and retry.');
                                }}
                            }} else {{
                                showSuccess((data.message || 'Report submitted successfully!') + '\\n\\nWhatsApp: ' + whatsappInfo + '\\n\\nSMS: ' + smsInfo + '\\n\\nRedirecting...');
                                setTimeout(() => {{
                                    window.location.href = '/';
                                }}, 3000);
                            }}
                        }} else {{
                            showError(data.message || 'Failed to submit report');
                        }}
                    }} catch (error) {{
                        showError('Error: ' + error.message);
                    }} finally {{
                        submitBtn.innerHTML = originalText;
                        submitBtn.disabled = false;
                    }}
                }});
                
                function showSuccess(message) {{
                    const successDiv = document.getElementById('successMessage');
                    const errorDiv = document.getElementById('errorMessage');
                    errorDiv.style.display = 'none';
                    successDiv.textContent = message;
                    successDiv.style.display = 'block';
                }}
                
                function showError(message) {{
                    const errorDiv = document.getElementById('errorMessage');
                    const successDiv = document.getElementById('successMessage');
                    successDiv.style.display = 'none';
                    document.getElementById('errorText').textContent = message;
                    errorDiv.style.display = 'block';
                }}
                
                function goHome() {{
                    window.location.href = '/';
                }}
            </script>
        </body>
        </html>
        '''
        return html

    def generate_pdf_html(self, patient_data, test_results):
        """Generate HTML content for PDF report"""
        html_content = f'''<!DOCTYPE html>
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
                    print(f"PDF generated with WeasyPrint: {output_path}")
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
                    
                    print(f"PDF generated with pdfkit: {output_path}")
                    return True
                    
                except Exception as e:
                    print(f"pdfkit failed: {e}")
            
            print("PDF generation not available. Saving as HTML instead.")
            return False
            
        except Exception as e:
            print(f"PDF generation error: {e}")
            return False

    def store_completed_report(
        self,
        patient_data,
        test_results,
        report_path,
        whatsapp_success,
        whatsapp_message,
        sms_success,
        sms_message,
    ):
        """Store completed report in database"""
        try:
            whatsapp_status = "sent" if whatsapp_success else "failed"
            sms_status = "not_attempted" if sms_success is None else ("sent" if sms_success else "failed")
            
            self.cursor.execute('''
                INSERT INTO completed_reports 
                (patient_name, patient_age, patient_gender, patient_mobile, doctor_name, opd_no, sample_date, test_results, pdf_path, whatsapp_status, whatsapp_error, sms_status, sms_error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_data.get('name'),
                patient_data.get('age'),
                patient_data.get('gender'),
                patient_data.get('mobile'),
                patient_data.get('doctor'),
                patient_data.get('opd_no'),
                patient_data.get('sample_date'),
                json.dumps(test_results),
                report_path,
                whatsapp_status,
                whatsapp_message,
                sms_status,
                sms_message
            ))
            
            self.conn.commit()
            print(f"Report stored in database. WhatsApp: {whatsapp_status}, SMS: {sms_status}")
            return True
            
        except Exception as e:
            print(f"Error storing report: {e}")
            return False

    def send_sms_via_fast2sms(self, mobile_number, message):
        """Send SMS via Fast2SMS API."""
        if not self.fast2sms_enabled:
            return False, "Fast2SMS is disabled."
        if not self.fast2sms_api_key:
            return False, "Fast2SMS API key is missing."

        try:
            mobile_clean = re.sub(r"\D", "", str(mobile_number or ""))
            if len(mobile_clean) == 12 and mobile_clean.startswith("91"):
                mobile_clean = mobile_clean[2:]
            if len(mobile_clean) == 11 and mobile_clean.startswith("0"):
                mobile_clean = mobile_clean[1:]
            if len(mobile_clean) != 10:
                return False, "Invalid mobile number for Fast2SMS (expected 10 digits)."

            url = "https://www.fast2sms.com/dev/bulkV2"
            params = {
                "message": message,
                "language": self.fast2sms_language,
                "route": self.fast2sms_route,
                "numbers": mobile_clean,
            }
            headers = {
                "cache-control": "no-cache",
                "authorization": self.fast2sms_api_key,
            }

            # Try primary request style first (header auth + query params).
            response = requests.get(url, params=params, headers=headers, timeout=12)

            # Fallback for compatibility: some accounts/workflows expect authorization in query string.
            if response.status_code in (401, 403):
                params_with_auth = dict(params)
                params_with_auth["authorization"] = self.fast2sms_api_key
                fallback_headers = {"cache-control": "no-cache"}
                response = requests.get(url, params=params_with_auth, headers=fallback_headers, timeout=12)

            response.raise_for_status()

            try:
                response_json = response.json()
            except Exception:
                return False, f"Fast2SMS returned non-JSON response: {response.text}"

            return_flag = response_json.get("return")
            is_success = return_flag is True or str(return_flag).strip().lower() == "true"
            if is_success:
                request_id = str(response_json.get("request_id", "")).strip()
                if request_id:
                    return True, f"SMS sent successfully via Fast2SMS (request_id: {request_id})"
                return True, "SMS sent successfully via Fast2SMS."

            error_text = response_json.get("message", "Unknown error")
            if isinstance(error_text, list):
                error_text = "; ".join(str(item) for item in error_text)
            error_text = str(error_text)

            code_hint = response_json.get("code")
            if code_hint:
                return False, f"Fast2SMS error [{code_hint}]: {error_text}"
            return False, f"Fast2SMS error: {error_text}"

        except requests.exceptions.RequestException as e:
            return False, f"Fast2SMS API request failed: {str(e)}"
        except Exception as e:
            return False, f"Error sending SMS via Fast2SMS: {str(e)}"

    def validate_mobile_number(self, mobile_number):
        """Validate and normalize number for WhatsApp Cloud API."""
        try:
            mobile_clean = re.sub(r"\D", "", str(mobile_number or ""))
            if not mobile_clean:
                return None, "Mobile number is required."

            # Remove international prefix "00" if provided.
            if mobile_clean.startswith("00"):
                mobile_clean = mobile_clean[2:]

            # Normalize common local format like 0XXXXXXXXXX.
            if len(mobile_clean) == 11 and mobile_clean.startswith("0"):
                mobile_clean = mobile_clean[1:]

            # If only local 10-digit number is given, prepend configured country code.
            if len(mobile_clean) == 10:
                mobile_clean = f"{self.whatsapp_default_country_code}{mobile_clean}"

            # Cloud API expects international format digits (typically 8-15 digits).
            if not (8 <= len(mobile_clean) <= 15):
                return None, (
                    "Invalid mobile number format. Use international format digits only, "
                    "for example 919876543210."
                )

            return mobile_clean, None
        except Exception as e:
            return None, f"Mobile validation error: {str(e)}"

    def build_whatsapp_web_url(self, mobile_number, message):
        """Build a client-openable WhatsApp URL with prefilled message."""
        encoded_message = urllib.parse.quote(str(message or "").strip())
        mobile_digits = re.sub(r"\D", "", str(mobile_number or ""))
        return f"https://wa.me/{mobile_digits}?text={encoded_message}"

    def send_whatsapp_message(self, mobile_number, patient_data, report_url):
        """Send WhatsApp message with report link."""
        try:
            formatted_mobile, mobile_error = self.validate_mobile_number(mobile_number)
            if mobile_error:
                return False, mobile_error

            print(f"Preparing WhatsApp for: {formatted_mobile}")
            message = self.create_whatsapp_message(patient_data, report_url)

            # Method 1: Cloud API (works in Render/server mode).
            api_success, api_message = self.send_whatsapp_via_cloud_api(
                formatted_mobile,
                message,
                report_url=report_url,
                patient_data=patient_data,
            )
            if api_success:
                return True, api_message

            # Method 2: WhatsApp Web fallback (local desktop usage).
            if self.enable_gui:
                try:
                    whatsapp_url = self.build_whatsapp_web_url(formatted_mobile, message)
                    opened = webbrowser.open(whatsapp_url)
                    if opened:
                        return True, "WhatsApp Web opened - please send manually"
                except Exception as e:
                    print(f"WhatsApp Web fallback failed: {e}")

                # Method 3: WhatsApp desktop deep-link fallback.
                try:
                    if platform.system() == "Windows":
                        encoded_message = urllib.parse.quote(message)
                        whatsapp_url = f"whatsapp://send?phone={formatted_mobile}&text={encoded_message}"
                        opened = webbrowser.open(whatsapp_url)
                        if opened:
                            return True, "WhatsApp Desktop opened - please send manually"
                except Exception:
                    pass

            # Method 4: GUI dialog fallback for local app.
            if self.enable_gui:
                self.show_message_dialog(patient_data, report_url)
                return True, f"Report URL generated: {report_url}"

            # Server mode fallback: be explicit and fail.
            config_hint = ""
            if not self.whatsapp_phone_number_id or not self.whatsapp_access_token:
                config_hint = " Configure WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN."
            return False, (
                f"{api_message}. WhatsApp Web/Desktop fallback is unavailable on server mode. "
                f"{config_hint}".strip()
            )

        except Exception as e:
            error_msg = f"WhatsApp preparation failed: {str(e)}"
            print(f"WhatsApp error: {error_msg}")
            return False, error_msg

    def _extract_cloud_api_error(self, response):
        """Extract normalized error details from Cloud API response."""
        try:
            details = response.json()
        except Exception:
            details = {"raw": response.text}

        if isinstance(details, dict):
            error_obj = details.get("error", {})
            if not isinstance(error_obj, dict):
                error_obj = {}
        else:
            error_obj = {}

        error_code = str(error_obj.get("code", "")).strip()
        error_message = str(error_obj.get("message", "")).strip() or str(details)
        return error_code, error_message

    def _should_try_template_fallback(self, error_code, error_message):
        """Template fallback helps when text is blocked by conversation window rules."""
        message_lc = (error_message or "").lower()
        if error_code in {"131047", "470"}:
            return True
        return (
            "24-hour" in message_lc
            or "24 hour" in message_lc
            or "outside the allowed window" in message_lc
        )

    def _build_template_parameters(self, patient_data, report_url):
        params = []
        for field_name in self.whatsapp_template_body_vars:
            key = field_name.strip()
            if not key:
                continue

            if key == "report_url":
                value = str(report_url or "").strip()
            else:
                value = str((patient_data or {}).get(key, "")).strip()

            params.append({"type": "text", "text": value or "-"})
        return params

    def send_whatsapp_template_via_cloud_api(self, mobile_number, patient_data, report_url):
        """Send WhatsApp template via Meta Cloud API (for business-initiated messages)."""
        if not self.whatsapp_template_name:
            return False, "WHATSAPP_TEMPLATE_NAME is not configured"

        url = f"{self.whatsapp_api_url}{self.whatsapp_phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.whatsapp_access_token}",
            "Content-Type": "application/json",
        }
        template_obj = {
            "name": self.whatsapp_template_name,
            "language": {"code": self.whatsapp_template_lang},
        }
        template_params = self._build_template_parameters(patient_data, report_url)
        if template_params:
            template_obj["components"] = [
                {
                    "type": "body",
                    "parameters": template_params,
                }
            ]

        payload = {
            "messaging_product": "whatsapp",
            "to": mobile_number,
            "type": "template",
            "template": template_obj,
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
        except Exception as e:
            return False, f"Template API request failed: {str(e)}"

        if response.status_code in (200, 201):
            return True, f"WhatsApp template sent ({self.whatsapp_template_name})"

        error_code, error_message = self._extract_cloud_api_error(response)
        return False, (
            f"Template API error {response.status_code} "
            f"(code {error_code or 'n/a'}): {error_message}"
        )

    def send_whatsapp_via_cloud_api(self, mobile_number, message, report_url=None, patient_data=None):
        """Send WhatsApp text via Meta Cloud API, with optional template fallback."""
        try:
            if not self.whatsapp_phone_number_id or not self.whatsapp_access_token:
                return False, "WhatsApp Cloud API is not configured"

            url = f"{self.whatsapp_api_url}{self.whatsapp_phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.whatsapp_access_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": mobile_number,
                "type": "text",
                "text": {
                    "preview_url": True,
                    "body": message,
                },
            }

            response = requests.post(url, json=payload, headers=headers, timeout=20)
            if response.status_code in (200, 201):
                return True, "WhatsApp message sent via Cloud API"

            error_code, error_message = self._extract_cloud_api_error(response)

            if self.whatsapp_template_name and self._should_try_template_fallback(
                error_code, error_message
            ):
                template_success, template_message = self.send_whatsapp_template_via_cloud_api(
                    mobile_number,
                    patient_data or {},
                    report_url,
                )
                if template_success:
                    return True, template_message
                return False, (
                    f"Cloud text message blocked ({error_message}). "
                    f"Template fallback failed: {template_message}"
                )

            if error_code == "131030":
                return False, (
                    "Recipient number is not allowed for current WhatsApp test setup. "
                    "Add the patient number as a test recipient in Meta dashboard. "
                    f"Details: {error_message}"
                )

            if error_code == "131026":
                return False, (
                    "Recipient number format is invalid for Cloud API. "
                    "Use international digits only, for example 919876543210. "
                    f"Details: {error_message}"
                )

            return False, (
                f"Cloud API error {response.status_code} "
                f"(code {error_code or 'n/a'}): {error_message}"
            )

        except Exception as e:
            return False, f"Cloud API request failed: {str(e)}"

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

    def create_sms_message(self, patient_data, report_url):
        """Create concise SMS content with report link."""
        patient_name = str((patient_data or {}).get("name", "Patient")).strip() or "Patient"
        report_url = str(report_url or "").strip()
        return (
            f"Dear {patient_name}, your pathology report is ready. "
            f"View it here: {report_url} - UJJIVAN Hospital"
        )

    def create_whatsapp_message(self, patient_data, report_url):
        """Create WhatsApp message content with patient messaging CTA"""
        report_url = str(report_url or "").strip()
        contact_url = f"{self.get_public_base_url()}/contact-hospital"
        return f"""📬 *UJJIVAN HOSPITAL - PATHOLOGY REPORT*

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
2. If it is not clickable, copy and paste it in browser
3. You can download/print if needed

*Report ID:* {patient_data.get('opd_no', 'N/A')}
*Generated on:* {datetime.now().strftime('%d-%m-%Y %I:%M %p')}

*Have Questions?*
💬 Reply to this message on WhatsApp
📞 Call us: {self.hospital_phone}
📧 Email: {self.hospital_email}

Or visit our website to send a message: {contact_url}

*Note:* This link is valid for 30 days. Contact hospital for queries.

Thank you for choosing UJJIVAN Hospital.
🏥 Vidyut Nagar, Gautam Budh Nagar, UP - 201008
"""

    def start_flask_server(self):
        """Start Flask server in a separate thread"""
        def run_flask():
            try:
                print("="*50)
                print("Starting UJJIVAN Hospital Pathology System")
                print("="*50)
                print(f"Date: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
                print(f"Reports directory: {os.path.abspath('reports/completed_reports')}")
                print("Web interface: http://localhost:5000")
                print(f"WhatsApp integration: {'Enabled' if self.whatsapp_enabled else 'Disabled'}")
                print("Patient Messaging: Enabled")
                print("="*50)
                
                self.flask_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                print(f"Flask server error: {e}")
                if self.enable_gui and hasattr(self, "status_label"):
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
    app = PathologyTestsForm(enable_gui=True, auto_start_server=True)

    # Handle window close
    def on_closing():
        try:
            app.conn.close()
        except:
            pass
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()
else:
    # Render / Gunicorn entrypoint: run Flask routes without desktop GUI.
    app = PathologyTestsForm(enable_gui=False, auto_start_server=False).flask_app
