from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'smartcampus_secret_key_secure'

def init_db():
    conn = sqlite3.connect('campus.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            roll_no TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('campus.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM complaints ORDER BY id DESC')
    complaints = cursor.fetchall()
    conn.close()
    return render_template('index.html', complaints=complaints)

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    roll_no = request.form['roll_no']
    category = request.form['category']
    description = request.form['description']
    
    conn = sqlite3.connect('campus.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO complaints (student_name, roll_no, category, description) VALUES (?, ?, ?, ?)',
                   (name, roll_no, category, description))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            error = 'Invalid credentials. Please try again.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('campus.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM complaints ORDER BY id DESC')
    complaints = cursor.fetchall()
    conn.close()
    return render_template('admin.html', complaints=complaints)

@app.route('/update/<int:id>/<string:status>')
def update_status(id, status):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('campus.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE complaints SET status = ? WHERE id = ?', (status, id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
