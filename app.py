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
import platform
import urllib.parse
import io
import tempfile
from flask import Flask, request, jsonify, send_from_directory, Response, render_template_string

class PathologyTestsForm(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("UJJIVAN Hospital Pathology System Launcher")
        self.geometry("600x400")
        self.configure(bg="#f0e1c6")

        # detect PDF library availability once and store on instance
        try:
            import pdfkit  # noqa: F401
            self.PDFKIT_AVAILABLE = True
        except Exception:
            self.PDFKIT_AVAILABLE = False
            print("pdfkit not available. Using alternative PDF generation.")

        try:
            if platform.system() == 'Windows':
                # WeasyPrint on Windows often needs extra deps (GTK); skip by default
                self.WEASYPRINT_AVAILABLE = False
                print("WeasyPrint not recommended on Windows. Using alternative methods.")
            else:
                from weasyprint import HTML  # noqa: F401
                self.WEASYPRINT_AVAILABLE = True
        except Exception:
            self.WEASYPRINT_AVAILABLE = False
            print("weasyprint not available. Using HTML fallback.")

        # Create necessary directories first
        os.makedirs('reports/completed_reports', exist_ok=True)

        # Initialize database
        self.init_database()

        # WhatsApp API Configuration (placeholders)
        self.whatsapp_api_url = "https://graph.facebook.com/v17.0/"
        self.whatsapp_phone_number_id = "7987089890"
        self.whatsapp_access_token = "YOUR_ACCESS_TOKEN"

        # Store current report data
        self.current_patient_data = {}
        self.current_selected_tests = []

        # Normal ranges dictionary
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
            # ... keep as needed
        }

        # Start Flask server for handling form submissions
        self.flask_app = Flask(__name__)
        self.setup_flask_routes()
        self.start_flask_server()

        # Simple launcher UI
        title_label = tk.Label(self, text="UJJIVAN HOSPITAL PATHOLOGY SYSTEM", 
                            font=("Arial", 20, "bold"), bg="#f0e1c6", fg="#003366")
        title_label.pack(pady=(20,10))

        subtitle_label = tk.Label(self, text="Vidyut Nagar, Gautam Budh Nagar, Uttar Pradesh - 201008", 
                                 font=("Arial", 12), bg="#f0e1c6")
        subtitle_label.pack(pady=(0,20))

        info_label = tk.Label(self, text="This system will open in your web browser\nwhere you can fill patient information and select tests", 
                            font=("Arial", 12), bg="#f0e1c6", justify=tk.CENTER)
        info_label.pack(pady=(0,30))

        launch_btn = tk.Button(self, text="Ã°Å¸Å¡â‚¬ Launch Web Application", 
                            fg="white", bg="#28a745", font=("Arial", 16, "bold"), 
                            command=self.launch_web_app, height=3, width=25)
        launch_btn.pack(pady=(0, 20))

        self.status_label = tk.Label(self, text="Ready to launch...", 
                                    font=("Arial", 10), bg="#f0e1c6", fg="#666")
        self.status_label.pack(pady=(10,5))

        # Pathology tests data (concise for brevity)
        self.tests = {
            "BIOCHEMISTRY": ["Glucose (F)/RI", "Post Prandial / after 2 Hrs", "HbA1c"],
            "RENAL FUNCTION": ["Urea", "Creatinine", "S. Uric Acid", "BUN"],
            "LIPID PROFILE": ["Cholesterol", "Triglyceride", "HDL", "LDL"],
            "LIVER FUNCTION": ["Bilirubin Total", "Bilirubin (Conjugated)", "Bilirubin (Unconjugated)", "SGOT/AST", "SGPT/ALT"],
            "ELECTROLYTES": ["S. Calcium", "S. Sodium", "S. Potassium"],
            "OTHER TESTS": ["Urine Protein (24 Hrs)", "Urine micro protein (albumin)", "CK-MB", "S. Phosphorous", "S. Amylase", "TROP-T"],
            "HAEMATOLOGY": ["Haemoglobin", "Total leukocyte count", "Platelet Count", "RBC Count"],
            "SEROLOGY": ["HbsAg", "HIV (1+2)", "HCV", "VDRL"]
        }

    def init_database(self):
        """Initialize SQLite database for storing reports"""
        try:
            self.conn = sqlite3.connect('pathology_reports.db', check_same_thread=False)
            self.cursor = self.conn.cursor()
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
        MAIN_WEB_FORM = '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>UJJIVAN HOSPITAL PATHOLOGY TESTS</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style> body{background:#f0e1c6;font-family:Arial} .hospital-header{background:white;padding:20px;border-radius:8px}</style>
        </head>
        <body>
        <div class="container mt-3">
            <div class="hospital-header">
                <h2 style="color:#003366">UJJIVAN HOSPITAL PATHOLOGY TESTS</h2>
                <p>Vidyut Nagar, Gautam Budh Nagar, Uttar Pradesh - 201008</p>
                <div class="row">
                    <div class="col-md-6">
                        <h5>Patient Information</h5>
                        <input id="patientName" class="form-control mb-2" placeholder="Patient Name">
                        <input id="patientAge" class="form-control mb-2" placeholder="Age">
                        <select id="patientGender" class="form-control mb-2"><option value="">Gender</option><option>Male</option><option>Female</option><option>Other</option></select>
                        <input id="patientMobile" class="form-control mb-2" placeholder="Mobile">
                    </div>
                    <div class="col-md-6">
                        <h5>Doctor & Sample</h5>
                        <input id="doctorName" class="form-control mb-2" placeholder="Doctor Name">
                        <input id="opdNo" class="form-control mb-2" placeholder="OPD No">
                        <input id="sampleDate" type="date" class="form-control mb-2" value="''' + datetime.now().strftime('%Y-%m-%d') + '''">
                    </div>
                </div>

                <div class="mt-3">
                    <h5>Select Tests</h5>
                    {% for category, test_list in tests.items() %}
                    <div style="background:#e8f0ff;padding:8px;margin-bottom:8px;border-radius:6px">
                        <strong>{{ category }}</strong>
                        <div class="row mt-2">
                        {% for test in test_list %}
                            <div class="col-md-6"><label><input type="checkbox" class="testchk" value="{{ test }}"> {{ test }}</label></div>
                        {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                </div>

                <button class="btn btn-success w-100" onclick="generateFillableForm()">ðŸ“‹ Generate Fillable Form</button>
            </div>
        </div>

        <script>
        function generateFillableForm(){
            const patientData = {
                name: document.getElementById('patientName').value,
                age: document.getElementById('patientAge').value,
                gender: document.getElementById('patientGender').value,
                mobile: document.getElementById('patientMobile').value,
                doctor: document.getElementById('doctorName').value,
                opd_no: document.getElementById('opdNo').value,
                sample_date: document.getElementById('sampleDate').value
            };
            if(!patientData.name||!patientData.age||!patientData.gender||!patientData.mobile){ alert('Fill required fields'); return; }
            const checks = document.querySelectorAll('.testchk:checked');
            const selected = [];
            checks.forEach(c=>selected.push(c.value));
            if(selected.length===0){ alert('Select at least one test'); return; }
            const params = new URLSearchParams({patient_data: JSON.stringify(patientData), selected_tests: JSON.stringify(selected)});
            window.open('/fillable-form?'+params.toString(), '_blank');
        }
        </script>
        </body>
        </html>
        '''

        @self.flask_app.route('/')
        def index():
            return render_template_string(MAIN_WEB_FORM, tests=self.tests)

        @self.flask_app.route('/fillable-form')
        def fillable_form():
            try:
                patient_data_json = request.args.get('patient_data')
                selected_tests_json = request.args.get('selected_tests')
                if not patient_data_json or not selected_tests_json:
                    return "Error: missing data", 400
                patient_data = json.loads(patient_data_json)
                selected_tests = json.loads(selected_tests_json)
                html_content = self.generate_exact_format_html_form(patient_data, selected_tests)
                return html_content
            except Exception as e:
                return f"Error: {e}", 500

        @self.flask_app.route('/submit-report', methods=['POST', 'OPTIONS'])
        def handle_form_submission():
            if request.method == 'OPTIONS':
                return jsonify({'status': 'ok'}), 200
            try:
                if not request.is_json:
                    return jsonify({'success': False, 'message': 'Content-Type must be application/json'}), 400
                data = request.get_json()
                patient_data = data.get('patient_data', {})
                test_results = data.get('test_results', {})

                required_fields = ['name', 'age', 'gender', 'mobile']
                for f in required_fields:
                    if not patient_data.get(f):
                        return jsonify({'success': False, 'message': f'Missing {f}'}), 400

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                patient_name_clean = patient_data.get('name','Unknown').replace(' ','_').replace('/','_').replace('\\','_')
                pdf_filename = f"Pathology_Report_{patient_name_clean}_{timestamp}.pdf"
                pdf_filepath = os.path.join('reports','completed_reports', pdf_filename)
                os.makedirs('reports/completed_reports', exist_ok=True)

                html_content = self.generate_pdf_html(patient_data, test_results)
                pdf_success, pdf_bytes = self.generate_pdf_bytes(html_content)
                if pdf_success and pdf_bytes:
                    with open(pdf_filepath, 'wb') as f:
                        f.write(pdf_bytes)
                    pdf_url = f"http://localhost:5000/view-pdf/{pdf_filename}"
                    whatsapp_success, whatsapp_message = self.send_whatsapp_direct(patient_data.get('mobile',''), patient_data, pdf_url)
                    self.store_completed_report(patient_data, test_results, pdf_filepath, whatsapp_success, whatsapp_message)
                    return jsonify({'success': True, 'message': 'Report submitted', 'whatsapp_status': 'sent' if whatsapp_success else 'failed', 'whatsapp_message': whatsapp_message, 'pdf_path': pdf_filepath, 'pdf_url': pdf_url})
                else:
                    # fallback to HTML file
                    html_filename = f"Pathology_Report_{patient_name_clean}_{timestamp}.html"
                    html_filepath = os.path.join('reports','completed_reports', html_filename)
                    with open(html_filepath, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    html_url = f"http://localhost:5000/view-pdf/{html_filename}"
                    whatsapp_success, whatsapp_message = self.send_whatsapp_direct(patient_data.get('mobile',''), patient_data, html_url)
                    self.store_completed_report(patient_data, test_results, html_filepath, whatsapp_success, whatsapp_message)
                    return jsonify({'success': True, 'message': 'Report submitted (HTML)', 'whatsapp_status': 'sent' if whatsapp_success else 'failed', 'whatsapp_message': whatsapp_message, 'pdf_path': html_filepath, 'pdf_url': html_url})
            except Exception as e:
                import traceback
                traceback.print_exc()
                return jsonify({'success': False, 'message': str(e)}), 500

        @self.flask_app.route('/view-pdf/<filename>')
        def view_pdf(filename):
            try:
                if '..' in filename or filename.startswith('/'):
                    return jsonify({'error': 'Invalid filename'}), 400
                directory = os.path.join(os.getcwd(),'reports','completed_reports')
                filepath = os.path.join(directory, filename)
                if not os.path.exists(filepath):
                    return jsonify({'error': 'File not found'}), 404
                if filename.lower().endswith('.pdf'):
                    return send_from_directory(directory, filename, as_attachment=False, mimetype='application/pdf')
                if filename.lower().endswith('.html'):
                    with open(filepath,'r',encoding='utf-8') as f:
                        return Response(f.read(), mimetype='text/html')
                return send_from_directory(directory, filename, as_attachment=True)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.flask_app.after_request
        def after_request(response):
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            return response

    def start_flask_server(self):
        def run_flask():
            try:
                print("Starting Flask server on http://0.0.0.0:5000")
                self.flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                print(f"Flask server error: {e}")
        self.flask_thread = threading.Thread(target=run_flask, daemon=True)
        self.flask_thread.start()
        time.sleep(1)

    def launch_web_app(self):
        self.status_label.config(text="Opening web application...")
        flask_url = "http://5000/"
        webbrowser.open(flask_url)
        self.status_label.config(text="Web application opened in browser!")
        messagebox.showinfo("Success", f"Web application opened in browser!\n\nIf it doesn't load automatically, visit:\n{flask_url}")

    def generate_exact_format_html_form(self, patient_data, selected_tests):
        serial_no = 1
        html_content = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><title>Pathology Form</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>body{{font-family:Times New Roman,serif;padding:15px}}.result{{border:none;border-bottom:1px solid #888;width:100%}}</style></head><body>
        <div class="container"><h3>Pathology Test Report - Fill Results</h3>
        <div><strong>Patient:</strong> {patient_data.get('name','')} | <strong>Age/Gender:</strong> {patient_data.get('age','')}/{patient_data.get('gender','')}</div><br/>'''
        # build sections
        # Example: BIOCHEMISTRY
        if any(test in selected_tests for test in ["Glucose (F)/RI", "Post Prandial / after 2 Hrs", "HbA1c"]):
            html_content += '<h5>BIOCHEMISTRY</h5><table class="table table-sm table-bordered"><thead><tr><th>S.No</th><th>Test</th><th>Normal</th><th>Result</th></tr></thead><tbody>'
            biochemistry_tests = [("Glucose (F)/RI","70-110 mg/dl"),("Post Prandial / after 2 Hrs","Up to 140 mg/dl"),("HbA1c","4.5-6.5 %")]
            for t,n in biochemistry_tests:
                if t in selected_tests:
                    html_content += f'<tr><td>{serial_no}</td><td>{t}</td><td>{n}</td><td><input class="result" name="{t}" /></td></tr>'
                    serial_no += 1
            html_content += '</tbody></table>'
        # other sections similar (kept concise)
        # Add submit JS
        html_content += f'''
        <div class="mt-3"><button class="btn btn-success" onclick="submitForm()">âœ… Submit & Send WhatsApp Report</button></div>
        </div>
        <script>
        function submitForm(){{
            const inputs = document.querySelectorAll('input.result');
            const testResults = {{}};
            inputs.forEach(i=>{{ if(i.value.trim()!='' && i.name) testResults[i.name]=i.value; }});
            if(Object.keys(testResults).length===0){{ alert('Enter at least one result'); return; }}
            const submissionData = {{
                patient_data: {{
                    name: "{patient_data.get('name','')}",
                    age: "{patient_data.get('age','')}",
                    gender: "{patient_data.get('gender','')}",
                    mobile: "{patient_data.get('mobile','')}",
                    doctor: "{patient_data.get('doctor','')}",
                    opd_no: "{patient_data.get('opd_no','')}",
                    sample_date: "{patient_data.get('sample_date','')}"
                }},
                test_results: testResults
            }};
            fetch('/submit-report', {{
                method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify(submissionData)
            }}).then(r=>r.json()).then(data=>{{ if(data.success){{ alert('Submitted. ' + data.message); if(data.pdf_url) window.open(data.pdf_url,'_blank'); }} else {{ alert('Error: '+data.message); }} }}).catch(e=>{{ alert('Submit error: '+e); }});
        }}
        </script>
        </body></html>'''
        return html_content

    def generate_pdf_html(self, patient_data, test_results):
        html_content = f'''
        <!DOCTYPE html><html><head><meta charset="utf-8"><style>
        body{{font-family:Times New Roman,serif;margin:20px}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #000;padding:6px}}th{{background:#e9ecef}}
        .normal{{color:#28a745}}.abnormal{{color:#dc3545}}
        </style></head><body>
        <h2>UJJIVAN HOSPITAL PATHOLOGY REPORT</h2>
        <div><strong>Patient:</strong> {patient_data.get('name','')} | <strong>Age/Gender:</strong> {patient_data.get('age','')}/{patient_data.get('gender','')}</div>
        <div><strong>Mobile:</strong> {patient_data.get('mobile','')} | <strong>Doctor:</strong> {patient_data.get('doctor','')}</div>
        <hr/>
        <h4>Test Results</h4>
        <table><tr><th>Test</th><th>Normal Range</th><th>Result</th></tr>
        '''
        for test_name, result in test_results.items():
            normal = self.normal_ranges.get(test_name, "")
            cls = "normal"
            rs = str(result).lower()
            if any(k in rs for k in ['positive','high','low','abnormal','reactive']):
                cls = "abnormal"
            html_content += f'<tr><td>{test_name}</td><td>{normal}</td><td class="{cls}">{result}</td></tr>'
        html_content += f'''
        </table>
        <div style="margin-top:30px">Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        </body></html>
        '''
        return html_content

    def generate_pdf_bytes(self, html_content):
        """Generate PDF bytes from HTML content using available methods (self.PDFKIT_AVAILABLE, self.WEASYPRINT_AVAILABLE)"""
        try:
            # WeasyPrint
            if getattr(self, "WEASYPRINT_AVAILABLE", False):
                try:
                    from weasyprint import HTML
                    pdf_bytes = HTML(string=html_content, encoding='utf-8').write_pdf()
                    return True, pdf_bytes
                except Exception as e:
                    print(f"WeasyPrint failed: {e}")

            # pdfkit
            if getattr(self, "PDFKIT_AVAILABLE", False):
                try:
                    import pdfkit
                    options = {'page-size':'A4','encoding':'UTF-8'}
                    config = None
                    possible_paths = [
                        '/usr/bin/wkhtmltopdf','/usr/local/bin/wkhtmltopdf',
                        r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
                        r'C:\wkhtmltopdf\bin\wkhtmltopdf.exe'
                    ]
                    for p in possible_paths:
                        if os.path.exists(p):
                            config = pdfkit.configuration(wkhtmltopdf=p)
                            break
                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                        tmp_path = tmp.name
                    if config:
                        pdfkit.from_string(html_content, tmp_path, options=options, configuration=config)
                    else:
                        pdfkit.from_string(html_content, tmp_path, options=options)
                    with open(tmp_path, 'rb') as f:
                        data = f.read()
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                    return True, data
                except Exception as e:
                    print(f"pdfkit failed: {e}")

            # xhtml2pdf
            try:
                from xhtml2pdf import pisa
                pdf_io = io.BytesIO()
                pisa_status = pisa.CreatePDF(html_content, dest=pdf_io)
                if pisa_status.err:
                    raise Exception("xhtml2pdf error")
                data = pdf_io.getvalue()
                pdf_io.close()
                return True, data
            except Exception as e:
                print(f"xhtml2pdf not available or failed: {e}")

            # reportlab basic fallback
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                pdf_io = io.BytesIO()
                c = canvas.Canvas(pdf_io, pagesize=letter)
                c.drawString(100, 750, "UJJIVAN HOSPITAL PATHOLOGY REPORT (HTML version available)")
                c.save()
                data = pdf_io.getvalue()
                pdf_io.close()
                return True, data
            except Exception as e:
                print(f"reportlab fallback failed: {e}")

            print("No PDF method available, returning failure")
            return False, None
        except Exception as e:
            print(f"Error generating PDF bytes: {e}")
            return False, None

    def store_report_in_database(self, patient_data, selected_tests):
        try:
            selected_tests_json = json.dumps(selected_tests)
            self.cursor.execute('''
                INSERT INTO form_submissions (patient_name, patient_age, patient_gender, patient_mobile, doctor_name, opd_no, sample_date, selected_tests)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_data.get('name',''),
                patient_data.get('age',''),
                patient_data.get('gender',''),
                patient_data.get('mobile',''),
                patient_data.get('doctor',''),
                patient_data.get('opd_no',''),
                patient_data.get('sample_date',''),
                selected_tests_json
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error storing form submission: {e}")
            return False

    def store_completed_report(self, patient_data, test_results, pdf_path, whatsapp_success, whatsapp_message):
        try:
            test_results_json = json.dumps(test_results)
            whatsapp_status = "sent" if whatsapp_success else "failed"
            self.cursor.execute('''
                INSERT INTO completed_reports (patient_name, patient_age, patient_gender, patient_mobile, doctor_name, opd_no, sample_date, test_results, pdf_path, whatsapp_status, whatsapp_error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_data.get('name',''),
                patient_data.get('age',''),
                patient_data.get('gender',''),
                patient_data.get('mobile',''),
                patient_data.get('doctor',''),
                patient_data.get('opd_no',''),
                patient_data.get('sample_date',''),
                test_results_json,
                pdf_path,
                whatsapp_status,
                whatsapp_message
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error storing completed report: {e}")
            return False

    def validate_mobile_number(self, mobile_number):
        try:
            cleaned = re.sub(r'\D', '', str(mobile_number))
            if len(cleaned) == 10 and cleaned.startswith(('6','7','8','9')):
                return f"91{cleaned}", None
            if len(cleaned) == 12 and cleaned.startswith('91'):
                return cleaned, None
            return None, "Invalid mobile number format"
        except Exception as e:
            return None, str(e)

    def send_whatsapp_direct(self, mobile_number, patient_data, pdf_url):
        try:
            formatted, err = self.validate_mobile_number(mobile_number)
            if err:
                return False, f"Mobile number error: {err}"
            # Try API
            api_success, api_msg = self.send_whatsapp_api(formatted, patient_data, pdf_url)
            if api_success:
                return True, api_msg
            # Try web
            web_success, web_msg = self.send_whatsapp_web(formatted, patient_data, pdf_url)
            if web_success:
                return True, web_msg
            # Fallback simple message
            return self.send_simple_message(formatted, patient_data, pdf_url)
        except Exception as e:
            return False, str(e)

    def send_whatsapp_api(self, mobile_number, patient_data, pdf_url):
        try:
            if (self.whatsapp_phone_number_id == "YOUR_PHONE_NUMBER_ID" or self.whatsapp_access_token == "YOUR_ACCESS_TOKEN"):
                return False, "WhatsApp Business API not configured"
            url = f"{self.whatsapp_api_url}{self.whatsapp_phone_number_id}/messages"
            headers = {"Authorization": f"Bearer {self.whatsapp_access_token}", "Content-Type": "application/json"}
            body = self.create_whatsapp_message(patient_data, pdf_url)
            payload = {"messaging_product":"whatsapp","to":mobile_number,"type":"text","text":{"body":body}}
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code in (200,201):
                return True, "WhatsApp message sent via Business API"
            return False, f"API Error: {resp.status_code} - {resp.text}"
        except Exception as e:
            return False, f"API method failed: {e}"

    def send_whatsapp_web(self, mobile_number, patient_data, pdf_url):
        try:
            message_body = self.create_whatsapp_message(patient_data, pdf_url)
            encoded = urllib.parse.quote(message_body)
            whatsapp_url = f"https://web.whatsapp.com/send?phone={mobile_number}&text={encoded}"
            webbrowser.open(whatsapp_url)
            return True, "WhatsApp Web opened - please send manually"
        except Exception as e:
            return False, f"WhatsApp Web failed: {e}"

    def send_simple_message(self, mobile_number, patient_data, pdf_url):
        try:
            message_body = self.create_whatsapp_message(patient_data, pdf_url)
            print("Prepared message:")
            print(message_body)
            messagebox.showinfo("Report Ready", f"Report generated!\n\nPatient: {patient_data.get('name','')}\nMobile: {mobile_number}\n\nReport URL:\n{pdf_url}")
            return True, f"Message prepared. URL: {pdf_url}"
        except Exception as e:
            return False, str(e)

    def create_whatsapp_message(self, patient_data, pdf_url):
        return f"""ðŸ”¬ UJJIVAN HOSPITAL - PATHOLOGY REPORT

Dear {patient_data.get('name','Patient')},

Your pathology test report is ready.

Patient: {patient_data.get('name','')}
Age/Gender: {patient_data.get('age','')}/{patient_data.get('gender','')}
Doctor: {patient_data.get('doctor','')}

View report: {pdf_url}

Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}
"""

    def send_sms_fast2sms(self, mobile_number, message):
        try:
            api_key = "YOUR_FAST2SMS_API_KEY"
            url = "https://www.fast2sms.com/dev/bulkV2"
            payload = {"message": message, "language": "english", "route": "q", "numbers": mobile_number}
            headers = {'authorization': api_key, 'Content-Type': "application/x-www-form-urlencoded"}
            resp = requests.post(url, data=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                return True, "SMS sent via Fast2SMS"
            return False, f"SMS failed: {resp.text}"
        except Exception as e:
            return False, str(e)

if __name__ == "__main__":
    gui = PathologyTestsForm()
    gui.mainloop()
