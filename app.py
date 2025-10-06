import os
import sqlite3
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from huggingface_hub import InferenceClient
from db import get_connection, seed_data
import extract_pdf
from plotting_helper import plot_balance_sheet

load_dotenv()

HF_TOKEN = os.environ.get("HF_API_KEY")
if not HF_TOKEN:
    raise ValueError("HF_API_KEY not found in environment variables.")

client = InferenceClient(token=HF_TOKEN)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "uploads"
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def check_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, role, company_id FROM users WHERE username=? AND password=?",
        (username, password),
    )
    result = cur.fetchone()
    conn.close()
    if result:
        user_id, role, company_id = result
        return {"id": user_id, "username": username, "role": role.lower(), "company_id": company_id}
    return None

def list_companies(user):
    conn = get_connection()
    cur = conn.cursor()
    if user["role"] == "groupadmin":
        cur.execute("SELECT id, name FROM companies")
    else:
        cur.execute("SELECT id, name FROM companies WHERE id=?", (user["company_id"],))
    companies = cur.fetchall()
    conn.close()
    return [{"id": cid, "name": name} for cid, name in companies]

def get_balance_sheet(user, company_id=None, year_from=None, year_to=None):
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT year, revenue, assets, liabilities, profit FROM balance_sheets WHERE 1=1"
    params = []

    if user["role"] != "groupadmin":
        query += " AND company_id=?"
        params.append(user["company_id"])
    elif company_id:
        query += " AND company_id=?"
        params.append(company_id)

    if year_from:
        query += " AND year >= ?"
        params.append(year_from)
    if year_to:
        query += " AND year <= ?"
        params.append(year_to)

    query += " ORDER BY year ASC"
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    conn.close()
    return rows

def ask_deepseek(context, question):
    prompt = f"Answer the question based on the balance sheet data below:\n\n{context}\n\nQuestion: {question}\nAnswer concisely:"
    try:
        response = client.chat_completion(
            model="deepseek-ai/DeepSeek-V3.2-Exp",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        if "response" in response:
            return response["response"]
        elif "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]
        else:
            return "[No text returned from model]"
    except Exception as e:
        return f"[Error contacting DeepSeek: {e}]"



@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "analyst").lower()
    company_id = data.get("company_id")

    if role != "groupadmin" and not company_id:
        return jsonify({"success": False, "error": "Non-admin users must have a company_id"}), 400

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password, role, company_id) VALUES (?,?,?,?)",
            (username, password, role, company_id)
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "error": "Username already exists"}), 400

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    user = check_user(username, password)
    if user:
        return jsonify({"success": True, "token": user})
    return jsonify({"success": False, "error": "Invalid username/password"}), 401

@app.route("/companies", methods=["GET"])
def companies():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Missing Authorization"}), 401
    user = json.loads(token)
    return jsonify(list_companies(user))

@app.route("/ask", methods=["POST"])
def ask():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Missing Authorization"}), 401
    user = json.loads(token)

    data = request.json
    question = data.get("question")
    company_id = data.get("company_id")

    if not question:
        return jsonify({"error": "Question is required"}), 400

    rows = get_balance_sheet(user, company_id)
    context = "\n".join([str(r) for r in rows])
    answer = ask_deepseek(context, question)
    return jsonify({"answer": answer})

@app.route("/balance_sheet_filtered", methods=["GET"])
def balance_sheet_filtered():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Missing Authorization"}), 401
    user = json.loads(token)

    company_id = request.args.get("company_id")
    year_from = request.args.get("year_from")
    year_to = request.args.get("year_to")

    rows = get_balance_sheet(user, company_id, year_from, year_to)
    balance_sheets = [{"year": r[0], "revenue": r[1], "assets": r[2], "liabilities": r[3], "profit": r[4]} for r in rows]
    return jsonify({"balance_sheets": balance_sheets})

@app.route("/upload-pdf", methods=["POST"])
def upload_pdf():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Missing Authorization"}), 401
    user = json.loads(token)

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    try:
        extract_pdf.extract_and_save(file_path, user)
        return jsonify({"success": True, "filename": file.filename})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/plot/<int:company_id>", methods=["GET"])
def plot(company_id):
    conn = get_connection()
    cur = conn.cursor()
    company = cur.execute("SELECT name FROM companies WHERE id=?", (company_id,)).fetchone()
    conn.close()
    if not company:
        return jsonify({"error": "Company not found"}), 404
    company_name = company[0]
    try:
        plot_balance_sheet(company_name)
        return jsonify({"success": True, "company": company_name})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

from flask import render_template

@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    seed_data()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
