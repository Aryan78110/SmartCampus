import os
import random
import sqlite3
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "smartcampus_master_secret_2026"
DB_FILE = "campus.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_no TEXT NOT NULL,
            mobile TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE NOT NULL,
            student_mobile TEXT NOT NULL,
            student_name TEXT NOT NULL,
            roll_no TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'Pending Review',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    search_ticket = request.args.get("search_ticket")
    complaint_data = None
    searched = False

    if search_ticket:
        searched = True
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticket_id, student_name, roll_no, category, description, status, created_at 
            FROM complaints 
            WHERE UPPER(ticket_id) = UPPER(?)
        """, (search_ticket.strip(),))
        complaint_data = cursor.fetchone()
        conn.close()

    return render_template("index.html", complaint_data=complaint_data, searched=searched, search_ticket=search_ticket)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll_no = request.form.get("roll_no", "").strip()
        mobile = request.form.get("mobile", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not all([name, roll_no, mobile, email, password]):
            flash("All fields are required!", "danger")
            return redirect(url_for("register"))

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE mobile = ?", (mobile,))
        if cursor.fetchone():
            conn.close()
            flash("Mobile number already registered! Please log in.", "warning")
            return redirect(url_for("login"))
        conn.close()

        otp = str(random.randint(100000, 999999))
        session['temp_user'] = {
            "name": name,
            "roll_no": roll_no,
            "mobile": mobile,
            "email": email,
            "password": password
        }
        session['otp_code'] = otp
        flash(f"Demo Mode: Verification OTP is {otp}", "info")
        return redirect(url_for("verify_otp"))

    return render_template("register.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if 'temp_user' not in session or 'otp_code' not in session:
        return redirect(url_for("register"))

    user_info = session.get('temp_user')

    if request.method == "POST":
        entered_otp = request.form.get("otp", "").strip()
        if entered_otp == session.get("otp_code"):
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (name, roll_no, mobile, email, password)
                VALUES (?, ?, ?, ?, ?)
            """, (user_info['name'], user_info['roll_no'], user_info['mobile'], user_info['email'], user_info['password']))
            conn.commit()
            conn.close()

            session.pop('temp_user', None)
            session.pop('otp_code', None)

            flash("Registration Successful! Please sign in with your mobile and password.", "success")
            return redirect(url_for("login"))
        else:
            flash("Incorrect OTP! Please check and try again.", "danger")

    return render_template("verify_otp.html", email=user_info.get('email'), mobile=user_info.get('mobile'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("mobile", "").strip()
        password = request.form.get("password", "").strip()

        # Admin Login credentials: aryan / aryan1234
        if username.lower() == "aryan" and password == "aryan1234":
            session['is_admin'] = True
            return redirect(url_for("admin"))

        # Student Login
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, roll_no, mobile, email 
            FROM users 
            WHERE (mobile = ? OR email = ?) AND password = ?
        """, (username, username, password))
        student = cursor.fetchone()
        conn.close()

        if student:
            session['student'] = {
                "id": student[0],
                "name": student[1],
                "roll_no": student[2],
                "mobile": student[3],
                "email": student[4]
            }
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid Mobile/Username or Password. Please try again.", "danger")

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if 'student' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    student = session['student']
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ticket_id, category, description, status, created_at 
        FROM complaints 
        WHERE student_mobile = ? 
        ORDER BY id DESC
    """, (student['mobile'],))
    my_complaints = cursor.fetchall()
    conn.close()

    return render_template("dashboard.html", student=student, complaints=my_complaints)

@app.route("/submit-complaint", methods=["POST"])
def submit_complaint():
    if 'student' not in session:
        return redirect(url_for("login"))

    student = session['student']
    category = request.form.get("category")
    description = request.form.get("description")
    ticket_id = f"CMP-{random.randint(1000, 9999)}"

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO complaints (ticket_id, student_mobile, student_name, roll_no, category, description, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending Review')
    """, (ticket_id, student['mobile'], student['name'], student['roll_no'], category, description))
    conn.commit()
    conn.close()

    flash(ticket_id, "ticket_success")
    return redirect(url_for("dashboard"))

@app.route("/admin")
def admin():
    if not session.get('is_admin'):
        flash("Admin login required.", "warning")
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT ticket_id, student_name, roll_no, student_mobile, category, description, status, created_at FROM complaints ORDER BY id DESC")
    all_complaints = cursor.fetchall()
    conn.close()

    return render_template("admin.html", complaints=all_complaints)

# BULLETPROOF STATUS UPDATE (Works via both GET and POST)
@app.route("/update-status", methods=["GET", "POST"])
def update_status():
    if not session.get('is_admin'):
        return redirect(url_for("login"))

    ticket_id = request.values.get("ticket_id")
    new_status = request.values.get("status")

    if ticket_id and new_status:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE complaints SET status = ? WHERE ticket_id = ?", (new_status.strip(), ticket_id.strip()))
        conn.commit()
        conn.close()
        flash(f"Status for {ticket_id} successfully changed to '{new_status}'!", "success")

    return redirect(url_for("admin"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
