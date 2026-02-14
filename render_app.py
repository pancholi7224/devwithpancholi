from flask import Flask, request, jsonify, send_file, send_from_directory
import os
import sqlite3

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "data.db")

app = Flask(__name__)

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            test TEXT,
            result TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- WEB ----------
@app.get("/")
def home():
    html_path = os.path.join(BASE_DIR, "PO.HTML")
    if os.path.exists(html_path):
        return send_file(html_path)
    return "Server running"

# ---------- API ----------
@app.post("/api/add-patient")
def add_patient():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO patients (name, test, result) VALUES (?, ?, ?)",
        (data["name"], data["test"], data["result"])
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.get("/api/patients")
def get_patients():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM patients")
    rows = c.fetchall()
    conn.close()

    return jsonify(rows)

if __name__ == "__main__":
    app.run()
