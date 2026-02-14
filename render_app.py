from flask import Flask, send_file, send_from_directory, abort
import os

BASE_DIR = os.path.dirname(__file__)
app = Flask(__name__)

@app.get("/")
def home():
    html_path = os.path.join(BASE_DIR, "PO.HTML")
    if os.path.exists(html_path):
        return send_file(html_path)
    return "Render app is running", 200

@app.get("/<path:filename>")
def serve_root_file(filename):
    file_path = os.path.join(BASE_DIR, filename)
    if os.path.isfile(file_path):
        return send_from_directory(BASE_DIR, filename)
    return abort(404)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
