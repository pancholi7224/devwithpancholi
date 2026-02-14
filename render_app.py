from flask import Flask, send_file
import os

app = Flask(__name__)

@app.get("/")
def home():
    html_path = os.path.join(os.path.dirname(__file__), "PO.HTML")
    if os.path.exists(html_path):
        return send_file(html_path)
    return "Render app is running", 200
