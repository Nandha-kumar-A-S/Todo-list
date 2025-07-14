from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Database setup
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'todo.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Login manager
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Task model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    due_date = db.Column(db.DateTime, nullable=True)
    category = db.Column(db.String(100), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for("register"))
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        # Toggle complete
        if "toggle" in request.form:
            task_id = request.form["toggle"]
            task = Task.query.get(task_id)
            if task and task.user_id == current_user.id:
                task.completed = not task.completed
                db.session.commit()
            return redirect(url_for("index"))

        # Edit task
        elif "edit_id" in request.form:
            task_id = request.form["edit_id"]
            new_content = request.form.get("edit_content")
            task = Task.query.get(task_id)
            if task and task.user_id == current_user.id:
                task.content = new_content
                db.session.commit()
            return redirect(url_for("index"))

        # Delete task
        elif "delete" in request.form:
            task_id = request.form["delete"]
            task = Task.query.get(task_id)
            if task and task.user_id == current_user.id:
                db.session.delete(task)
                db.session.commit()
            return redirect(url_for("index"))

        # Add new task
        else:
            content = request.form.get("task")
            due_date_str = request.form.get("due_date")
            category = request.form.get("category")
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d") if due_date_str else None

            new_task = Task(
                content=content,
                user_id=current_user.id,
                due_date=due_date,
                category=category,
                completed=False
            )
            db.session.add(new_task)
            db.session.commit()
            return redirect(url_for("index"))

    # Handle filtering
    filter_option = request.args.get("filter", "all")
    query = Task.query.filter_by(user_id=current_user.id)

    if filter_option == "completed":
        query = query.filter_by(completed=True)
    elif filter_option == "incomplete":
        query = query.filter_by(completed=False)

    tasks = query.all()
    return render_template("index.html", tasks=tasks, filter_option=filter_option)

@app.route("/api/tasks")
@login_required
def get_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    task_list = [{
        "id": t.id,
        "content": t.content,
        "completed": t.completed,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "category": t.category
    } for t in tasks]
    return jsonify(task_list)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
