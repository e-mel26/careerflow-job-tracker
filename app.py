from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# =========================
# DATABASE SETUP
# =========================
def init_db():
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            position TEXT NOT NULL,
            status TEXT NOT NULL,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# USER CLASS
# =========================
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return User(user[0], user[1])
    return None

# =========================
# AUTH ROUTES
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        conn = sqlite3.connect("jobs.db")
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except:
            return "Username already exists"

        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("jobs.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            login_user(User(user[0], user[1]))
            return redirect(url_for("home"))

        return "Invalid credentials"

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# =========================
# MAIN ROUTES
# =========================
@app.route("/")
@login_required
def home():
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM jobs
        WHERE user_id = ?
        ORDER BY 
            CASE status
                WHEN 'Interview' THEN 1
                WHEN 'Applied' THEN 2
                WHEN 'Rejected' THEN 3
            END
    """, (current_user.id,))

    jobs = cursor.fetchall()

    # Counts
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE user_id = ?", (current_user.id,))
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='Applied' AND user_id = ?", (current_user.id,))
    applied_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='Interview' AND user_id = ?", (current_user.id,))
    interview_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='Rejected' AND user_id = ?", (current_user.id,))
    rejected_count = cursor.fetchone()[0]

    conn.close()

    return render_template("index.html",
                           jobs=jobs,
                           total=total,
                           applied_count=applied_count,
                           interview_count=interview_count,
                           rejected_count=rejected_count)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add_job():
    if request.method == "POST":
        company = request.form["company"]
        position = request.form["position"]
        status = request.form["status"]

        conn = sqlite3.connect("jobs.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO jobs (company, position, status, user_id)
            VALUES (?, ?, ?, ?)
        """, (company, position, status, current_user.id))

        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    return render_template("add_job.html")

@app.route("/delete/<int:job_id>")
@login_required
def delete_job(job_id):
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ? AND user_id = ?", (job_id, current_user.id))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))

@app.route("/edit/<int:job_id>", methods=["GET", "POST"])
@login_required
def edit_job(job_id):
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()

    if request.method == "POST":
        company = request.form["company"]
        position = request.form["position"]
        status = request.form["status"]

        cursor.execute("""
            UPDATE jobs
            SET company = ?, position = ?, status = ?
            WHERE id = ? AND user_id = ?
        """, (company, position, status, job_id, current_user.id))

        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    cursor.execute("SELECT * FROM jobs WHERE id = ? AND user_id = ?", (job_id, current_user.id))
    job = cursor.fetchone()
    conn.close()

    return render_template("edit_job.html", job=job)

if __name__ == "__main__":
    app.run(debug=True)