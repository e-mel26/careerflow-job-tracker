from flask import Flask, render_template, request, redirect, url_for
import os

from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Secret key from environment (Render)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-secret-key")

# Database URL from Render environment variables
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Fallback to SQLite locally
app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///jobs.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# =========================
# MODELS
# =========================
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    jobs = db.relationship("Job", backref="user", lazy=True)


class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(255), nullable=False)
    position = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create tables at startup
with app.app_context():
    db.create_all()


# =========================
# AUTH ROUTES
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = generate_password_hash(request.form["password"])

        existing = User.query.filter_by(username=username).first()
        if existing:
            return "Username already exists"

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
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
    # sort order
    jobs = (
        Job.query.filter_by(user_id=current_user.id)
        .order_by(
            db.case(
                (Job.status == "Applied", 1),
                (Job.status == "Interview", 2),
                (Job.status == "Rejected", 3),
                else_=4,
            )
        )
        .all()
    )

    total = Job.query.filter_by(user_id=current_user.id).count()
    applied_count = Job.query.filter_by(user_id=current_user.id, status="Applied").count()
    interview_count = Job.query.filter_by(user_id=current_user.id, status="Interview").count()
    rejected_count = Job.query.filter_by(user_id=current_user.id, status="Rejected").count()

    return render_template(
        "index.html",
        jobs=jobs,
        total=total,
        applied_count=applied_count,
        interview_count=interview_count,
        rejected_count=rejected_count
    )


@app.route("/add", methods=["GET", "POST"])
@login_required
def add_job():
    if request.method == "POST":
        company = request.form["company"].strip()
        position = request.form["position"].strip()
        status = request.form["status"]

        job = Job(company=company, position=position, status=status, user_id=current_user.id)
        db.session.add(job)
        db.session.commit()

        return redirect(url_for("home"))

    return render_template("add_job.html")


@app.route("/delete/<int:job_id>")
@login_required
def delete_job(job_id):
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if job:
        db.session.delete(job)
        db.session.commit()
    return redirect(url_for("home"))


@app.route("/edit/<int:job_id>", methods=["GET", "POST"])
@login_required
def edit_job(job_id):
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return redirect(url_for("home"))

    if request.method == "POST":
        job.company = request.form["company"].strip()
        job.position = request.form["position"].strip()
        job.status = request.form["status"]
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("edit_job.html", job=job)


if __name__ == "__main__":
    app.run(debug=True)