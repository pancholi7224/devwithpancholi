"""
UJJIVAN Hospital Pathology System
FINAL VERSION - Works with minimal dependencies
"""

import tkinter as tk
from tkinter import messagebox
import webbrowser
import os
from datetime import datetime
import sqlite3
import json
import threading
import time
import re
from flask import Flask, request, jsonify, send_from_directory
import urllib.parse
import subprocess
import sys

class PathologySystem:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("UJJIVAN Hospital Pathology System")
        self.root.geometry("700x550")
        self.root.configure(bg="#f0e1c6")
        
        # Create directories
        self.create_directories()
        
        # Initialize database
        self.init_database()
        
        # Test normal ranges
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
            "SGOT/AST": "0-35 U/L",
            "SGPT/ALT": "0-40 U/L",
            "Haemoglobin": "14-18 gm% (M)/12-15 gm% (F)",
            "Total leukocyte count": "4000-10,000/cu mm",
            "Platelet Count": "1.5-4.5 lac/cu mm",
            "RBC Count": "3.5-5.5 million/cu mm",
            "HbsAg": "Negative",
            "HIV (1+2)": "Negative",
            "HCV": "Negative",
            "VDRL": "Non-reactive",
            "CRP": "<6 mg/L"
        }
        
        # Test categories
        self.tests = {
            "BIOCHEMISTRY": ["Glucose (F)/RI", "Post Prandial / after 2 Hrs", "HbA1c"],
            "RENAL FUNCTION": ["Urea", "Creatinine", "S. Uric Acid", "BUN"],
            "LIPID PROFILE": ["Cholesterol", "Triglyceride", "HDL"],
            "LIVER FUNCTION": ["Bilirubin Total", "SGOT/AST", "SGPT/ALT"],
            "HAEMATOLOGY": ["Haemoglobin", "Total leukocyte count", "Platelet Count", "RBC Count"],
            "SEROLOGY": ["HbsAg", "HIV (1+2)", "HCV", "VDRL", "CRP"]
        }
        
        # Setup GUI
        self.setup_gui()
        
        # Start Flask
        self.start_flask()
        
    def create_directories(self):
        """Create required directories"""
        os.makedirs('reports', exist_ok=True)
        os.makedirs('reports/completed', exist_ok=True)
        os.makedirs('database', exist_ok=True)
        
    def init_database(self):
        """Initialize SQLite database"""
        try:
            self.conn = sqlite3.connect('database/pathology.db', check_same_thread=False)
            self.cursor = self.conn.cursor()
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_name TEXT,
                    patient_age TEXT,
                    patient_gender TEXT,
                    patient_mobile TEXT,
                    doctor_name TEXT,
                    test_results TEXT,
                    report_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
            print("✅ Database initialized")
        except Exception as e:
            print(f"❌ Database error: {e}")
            
    def setup_gui(self):
        """Setup main GUI"""
        # Title
        title = tk.Label(self.root, text="🏥 UJJIVAN HOSPITAL", 
                        font=("Arial", 24, "bold"), bg="#f0e1c6", fg="#003366")
        title.pack(pady=(30,5))
        
        subtitle = tk.Label(self.root, text="Pathology Laboratory System", 
                           font=("Arial", 16), bg="#f0e1c6", fg="#003366")
        subtitle.pack(pady=(0,20))
        
        # Info box
        info_frame = tk.Frame(self.root, bg="white", relief="ridge", bd=2)
        info_frame.pack(pady=20, padx=30, fill="x")
        
        info_text = """📋 Quick Guide:
1. Click 'Start System' to open web interface
2. Enter patient details
3. Select required tests
4. Enter results
5. Report is saved and WhatsApp opens"""
        
        info = tk.Label(info_frame, text=info_text, bg="white", 
                       font=("Arial", 11), justify=tk.LEFT, padx=15, pady=15)
        info.pack()
        
        # Start button
        self.start_btn = tk.Button(self.root, text="🚀 START SYSTEM", 
                                   command=self.start_system,
                                   bg="#28a745", fg="white", 
                                   font=("Arial", 18, "bold"),
                                   height=2, width=20, cursor="hand2")
        self.start_btn.pack(pady=30)
        
        # Status
        self.status = tk.Label(self.root, text="⚫ System Ready", 
                              font=("Arial", 11), bg="#f0e1c6", fg="#666")
        self.status.pack()
        
        # Reports button
        reports_btn = tk.Button(self.root, text="📁 Open Reports Folder", 
                               command=self.open_reports,
                               bg="#007bff", fg="white", font=("Arial", 10))
        reports_btn.pack(pady=10)
        
    def start_flask(self):
        """Start Flask server"""
        self.app = Flask(__name__)
        self.setup_routes()
        
        def run_server():
            self.app.run(host='127.0.0.1', port=5050, debug=False, use_reloader=False)
            
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        time.sleep(2)
        self.status.config(text="✅ Server running on http://localhost:5050", fg="green")
        
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def home():
            return self.get_home_page()
            
        @self.app.route('/form')
        def form():
            patient = request.args.get('patient', '{}')
            tests = request.args.get('tests', '[]')
            try:
                patient_data = json.loads(patient)
                selected_tests = json.loads(tests)
                return self.get_test_form(patient_data, selected_tests)
            except:
                return "Invalid data", 400
                
        @self.app.route('/submit', methods=['POST'])
        def submit():
            try:
                data = request.get_json()
                patient = data.get('patient', {})
                results = data.get('results', {})
                
                # Generate report
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"report_{patient['name'].replace(' ', '_')}_{timestamp}.html"
                filepath = os.path.join('reports', 'completed', filename)
                
                html = self.generate_report(patient, results)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html)
                
                # Save to database
                self.cursor.execute('''
                    INSERT INTO reports (patient_name, patient_age, patient_gender, 
                    patient_mobile, doctor_name, test_results, report_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    patient['name'], patient['age'], patient['gender'],
                    patient['mobile'], patient.get('doctor', ''),
                    json.dumps(results), filepath
                ))
                self.conn.commit()
                
                # WhatsApp
                report_url = f"http://localhost:5050/report/{filename}"
                self.send_whatsapp(patient['mobile'], patient['name'], report_url)
                
                return jsonify({'success': True, 'url': report_url})
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
                
        @self.app.route('/report/<filename>')
        def view_report(filename):
            return send_from_directory('reports/completed', filename)
            
    def get_home_page(self):
        """Home page HTML"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        tests_html = ""
        for category, test_list in self.tests.items():
            tests_html += f'<div class="category"><h5>{category}</h5>'
            for test in test_list:
                tests_html += f'''
                <div class="form-check">
                    <input class="form-check-input test-checkbox" type="checkbox" value="{test}">
                    <label class="form-check-label">{test}</label>
                </div>'''
            tests_html += '</div>'
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>UJJIVAN Hospital</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ background: #f0e1c6; padding: 20px; }}
                .container {{ max-width: 1000px; margin: auto; }}
                .header {{ background: #003366; color: white; padding: 30px; border-radius: 15px; margin-bottom: 20px; }}
                .category {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; }}
                .btn-start {{ background: #28a745; color: white; font-size: 1.2rem; padding: 15px 40px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header text-center">
                    <h1>🏥 UJJIVAN HOSPITAL</h1>
                    <h3>Pathology Laboratory</h3>
                </div>
                
                <div class="card p-4">
                    <h4>Patient Information</h4>
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label>Full Name *</label>
                            <input type="text" class="form-control" id="name" required>
                        </div>
                        <div class="col-md-3 mb-3">
                            <label>Age *</label>
                            <input type="number" class="form-control" id="age" required>
                        </div>
                        <div class="col-md-3 mb-3">
                            <label>Gender *</label>
                            <select class="form-control" id="gender" required>
                                <option value="">Select</option>
                                <option value="Male">Male</option>
                                <option value="Female">Female</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label>Mobile *</label>
                            <input type="tel" class="form-control" id="mobile" required>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label>Doctor</label>
                            <input type="text" class="form-control" id="doctor">
                        </div>
                        <div class="col-md-4 mb-3">
                            <label>Date</label>
                            <input type="date" class="form-control" id="date" value="{today}">
                        </div>
                    </div>
                    
                    <h4 class="mt-4">Select Tests</h4>
                    {tests_html}
                    
                    <button class="btn btn-start mt-4" onclick="startForm()">Continue to Results</button>
                </div>
            </div>
            
            <script>
                function startForm() {{
                    const patient = {{
                        name: document.getElementById('name').value,
                        age: document.getElementById('age').value,
                        gender: document.getElementById('gender').value,
                        mobile: document.getElementById('mobile').value,
                        doctor: document.getElementById('doctor').value,
                        date: document.getElementById('date').value
                    }};
                    
                    if (!patient.name || !patient.age || !patient.gender || !patient.mobile) {{
                        alert('Please fill all required fields');
                        return;
                    }}
                    
                    const tests = [];
                    document.querySelectorAll('.test-checkbox:checked').forEach(cb => {{
                        tests.push(cb.value);
                    }});
                    
                    if (tests.length === 0) {{
                        alert('Select at least one test');
                        return;
                    }}
                    
                    window.location.href = '/form?patient=' + encodeURIComponent(JSON.stringify(patient)) + 
                                          '&tests=' + encodeURIComponent(JSON.stringify(tests));
                }}
            </script>
        </body>
        </html>
        '''
        
    def get_test_form(self, patient, tests):
        """Test entry form HTML"""
        rows = ""
        serial = 1
        
        for category, test_list in self.tests.items():
            category_tests = [t for t in test_list if t in tests]
            if category_tests:
                rows += f'<tr class="category-row"><td colspan="3">{category}</td></tr>'
                for test in category_tests:
                    normal = self.normal_ranges.get(test, '')
                    rows += f'''
                    <tr>
                        <td>{serial}</td>
                        <td>{test}<br><small class="text-muted">{normal}</small></td>
                        <td><input type="text" class="form-control result-input" name="{test}"></td>
                    </tr>'''
                    serial += 1
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Enter Results</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ padding: 20px; background: #f8f9fa; }}
                .container {{ max-width: 800px; margin: auto; }}
                .header {{ background: #003366; color: white; padding: 20px; border-radius: 10px; }}
                .category-row {{ background: #e9ecef; font-weight: bold; }}
                table {{ background: white; }}
                .btn-submit {{ background: #25D366; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header mb-4">
                    <h3>🏥 UJJIVAN HOSPITAL</h3>
                    <p>Patient: {patient['name']} | Age: {patient['age']} | Mobile: {patient['mobile']}</p>
                </div>
                
                <table class="table table-bordered">
                    <thead class="table-light">
                        <tr><th>S.No</th><th>Test</th><th>Result</th></tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
                
                <button class="btn btn-submit btn-lg w-100" onclick="submitResults()">
                    📱 Submit & Open WhatsApp
                </button>
            </div>
            
            <script>
                function submitResults() {{
                    const results = {{}};
                    document.querySelectorAll('.result-input').forEach(input => {{
                        if (input.value.trim()) {{
                            results[input.name] = input.value;
                        }}
                    }});
                    
                    if (Object.keys(results).length === 0) {{
                        alert('Enter at least one result');
                        return;
                    }}
                    
                    fetch('/submit', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            patient: {json.dumps(patient)},
                            results: results
                        }})
                    }})
                    .then(r => r.json())
                    .then(data => {{
                        if (data.success) {{
                            alert('✅ Report saved!');
                            window.open(data.url, '_blank');
                        }} else {{
                            alert('Error: ' + data.error);
                        }}
                    }});
                }}
            </script>
        </body>
        </html>
        '''
        
    def generate_report(self, patient, results):
        """Generate HTML report"""
        rows = ""
        for test, result in results.items():
            normal = self.normal_ranges.get(test, '')
            rows += f'<tr><td>{test}</td><td>{normal}</td><td><strong>{result}</strong></td></tr>'
            
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Pathology Report</title>
            <style>
                body {{ font-family: Arial; padding: 40px; }}
                .header {{ text-align: center; border-bottom: 2px solid #003366; padding-bottom: 20px; }}
                .hospital {{ color: #003366; font-size: 28px; font-weight: bold; }}
                .info {{ background: #f8f9fa; padding: 15px; margin: 20px 0; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #000; padding: 10px; }}
                th {{ background: #e9ecef; }}
                .footer {{ margin-top: 40px; text-align: right; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="hospital">UJJIVAN HOSPITAL</div>
                <p>Pathology Laboratory, Vidyut Nagar, Gautam Budh Nagar</p>
            </div>
            
            <div class="info">
                <p><strong>Patient:</strong> {patient['name']} | <strong>Age/Sex:</strong> {patient['age']}/{patient['gender']}</p>
                <p><strong>Mobile:</strong> {patient['mobile']} | <strong>Doctor:</strong> {patient.get('doctor', 'N/A')}</p>
                <p><strong>Date:</strong> {patient.get('date', datetime.now().strftime('%Y-%m-%d'))}</p>
            </div>
            
            <h3>Test Results</h3>
            <table>
                <tr><th>Test</th><th>Normal Range</th><th>Result</th></tr>
                {rows}
            </table>
            
            <div class="footer">
                <p>_________________________</p>
                <p>Pathologist</p>
            </div>
        </body>
        </html>
        '''
        
    def send_whatsapp(self, mobile, name, url):
        """Send WhatsApp message"""
        try:
            # Clean mobile
            mobile = re.sub(r'\D', '', str(mobile))
            if len(mobile) == 10:
                mobile = '91' + mobile
                
            message = f"🔬 UJJIVAN HOSPITAL\nDear {name}, your pathology report is ready.\nView: {url}"
            encoded = urllib.parse.quote(message)
            webbrowser.open(f"https://web.whatsapp.com/send?phone={mobile}&text={encoded}")
        except:
            pass
            
    def open_reports(self):
        """Open reports folder"""
        path = os.path.join(os.getcwd(), 'reports', 'completed')
        if os.path.exists(path):
            os.startfile(path)
            
    def start_system(self):
        """Start the system"""
        webbrowser.open('http://localhost:5050')
        self.status.config(text="✅ Web interface opened in browser", fg="green")
        
    def run(self):
        """Run the application"""
        self.root.mainloop()

if __name__ == "__main__":
    # Install required packages if missing
    try:
        import flask
        import requests
    except ImportError:
        print("Installing required packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "requests"])
    
    # Run the application
    app = PathologySystem()
    app.run()