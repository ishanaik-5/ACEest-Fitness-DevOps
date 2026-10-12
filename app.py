"""ACEest Fitness & Gym: Flask + SQLite demo for DevOps Assignment 1."""
from __future__ import annotations

import os
import random
import sqlite3
from datetime import date, datetime
from functools import wraps
from io import BytesIO
from pathlib import Path

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   send_file, session, url_for)
from fpdf import FPDF
from werkzeug.security import check_password_hash, generate_password_hash

PROGRAM_TEMPLATES = {
    "Fat Loss": ["Full Body HIIT", "Circuit Training", "Cardio + Weights"],
    "Muscle Gain": ["Push/Pull/Legs", "Upper/Lower Split", "Full Body Strength"],
    "Beginner": ["Full Body 3x/week", "Light Strength + Mobility"],
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('Admin','Staff'))
);
CREATE TABLE IF NOT EXISTS clients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL COLLATE NOCASE UNIQUE,
  age INTEGER NOT NULL, height_cm REAL NOT NULL, weight_kg REAL NOT NULL,
  program TEXT NOT NULL DEFAULT '', calories INTEGER NOT NULL,
  target_weight_kg REAL, target_adherence INTEGER NOT NULL DEFAULT 80,
  membership_status TEXT NOT NULL DEFAULT 'Active', membership_end TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workouts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  workout_date TEXT NOT NULL, workout_type TEXT NOT NULL,
  duration_min INTEGER NOT NULL, notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS progress (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  week_label TEXT NOT NULL, adherence INTEGER NOT NULL CHECK(adherence BETWEEN 0 AND 100)
);
CREATE TABLE IF NOT EXISTS exercises (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
  name TEXT NOT NULL, sets INTEGER NOT NULL CHECK(sets BETWEEN 1 AND 100),
  reps INTEGER NOT NULL CHECK(reps BETWEEN 1 AND 1000),
  weight_kg REAL CHECK(weight_kg IS NULL OR weight_kg BETWEEN 0 AND 1000)
);
CREATE TABLE IF NOT EXISTS metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  metric_date TEXT NOT NULL, weight_kg REAL NOT NULL CHECK(weight_kg BETWEEN 1 AND 500),
  waist_cm REAL CHECK(waist_cm IS NULL OR waist_cm BETWEEN 1 AND 300),
  body_fat_pct REAL CHECK(body_fat_pct IS NULL OR body_fat_pct BETWEEN 0 AND 100)
);
"""


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "local-dev-only-change-this-secret"),
        DATABASE=os.environ.get("DATABASE_PATH", str(Path(app.instance_path) / "aceest_fitness.db")),
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    def connect_db():
        connection = sqlite3.connect(app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_db():
        db = connect_db()
        try:
            db.executescript(SCHEMA)
            # Demo accounts are seeded only when absent. Override these demo passwords
            # before using the app outside a local assignment environment.
            for username, password, role in [
                ("admin", os.environ.get("ACEEST_ADMIN_PASSWORD", "Admin@123"), "Admin"),
                ("staff", os.environ.get("ACEEST_STAFF_PASSWORD", "Staff@123"), "Staff"),
            ]:
                existing = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
                if not existing:
                    db.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                               (username, generate_password_hash(password), role))
            db.commit()
        finally:
            db.close()

    with app.app_context():
        init_db()

    @app.before_request
    def load_current_user():
        user_id = session.get("user_id")
        g.current_user = None
        if user_id:
            db = connect_db()
            try:
                row = db.execute("SELECT id, username, role FROM users WHERE id=?", (user_id,)).fetchone()
                g.current_user = dict(row) if row else None
                if row is None:
                    session.clear()
            finally:
                db.close()

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.current_user is None:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def roles_required(*roles):
        def decorator(view):
            @wraps(view)
            @login_required
            def wrapped(*args, **kwargs):
                if g.current_user["role"] not in roles:
                    abort(403)
                return view(*args, **kwargs)
            return wrapped
        return decorator

    def get_client(db, client_id):
        row = db.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        return dict(row) if row else None

    def get_activity(db, client_id, table, order_by):
        # Table/order values are internal constants, never user input.
        return [dict(row) for row in db.execute(
            f"SELECT * FROM {table} WHERE client_id=? ORDER BY {order_by}", (client_id,)
        ).fetchall()]

    @app.get("/login")
    def login():
        if g.current_user:
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    @app.post("/login")
    def login_post():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = connect_db()
        try:
            user = db.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone()
        finally:
            db.close()
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "error")
            return render_template("login.html"), 401
        session.clear()
        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['username']}.", "success")
        next_url = request.args.get("next", "")
        # Only allow a local path to prevent open redirects.
        if next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(url_for("dashboard"))

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def dashboard():
        db = connect_db()
        try:
            clients = [dict(row) for row in db.execute("SELECT * FROM clients ORDER BY name COLLATE NOCASE").fetchall()]
            total_workouts = db.execute("SELECT COUNT(*) FROM workouts").fetchone()[0]
            active_memberships = db.execute("SELECT COUNT(*) FROM clients WHERE membership_status='Active'").fetchone()[0]
            progress_count = db.execute("SELECT COUNT(*) FROM progress").fetchone()[0]
        finally:
            db.close()
        return render_template("dashboard.html", clients=clients, total_workouts=total_workouts,
                               active_memberships=active_memberships, progress_count=progress_count)

    @app.get("/health")
    def health():
        return {"status": "healthy", "application": "ACEest Fitness & Gym"}, 200

    @app.get("/clients")
    @login_required
    def clients_api():
        db = connect_db()
        try:
            clients = [dict(row) for row in db.execute("SELECT * FROM clients ORDER BY name COLLATE NOCASE").fetchall()]
        finally:
            db.close()
        return {"count": len(clients), "clients": clients}, 200

    @app.route("/clients/new", methods=["GET", "POST"])
    @roles_required("Admin")
    def new_client():
        if request.method == "GET":
            return render_template("client_form.html", client={})
        name = request.form.get("name", "").strip()
        try:
            age = int(request.form.get("age", ""))
            height = float(request.form.get("height_cm", ""))
            weight = float(request.form.get("weight_kg", ""))
            target_raw = request.form.get("target_weight_kg", "").strip()
            target_weight = float(target_raw) if target_raw else None
            adherence = int(request.form.get("target_adherence", "80"))
            status = request.form.get("membership_status", "Active").strip()
            end = request.form.get("membership_end", "").strip() or None
            if not name or len(name) > 100 or not 1 <= age <= 120 or not 30 <= height <= 260 or not 1 <= weight <= 500:
                raise ValueError
            if target_weight is not None and not 1 <= target_weight <= 500:
                raise ValueError
            if not 0 <= adherence <= 100 or status not in {"Active", "Inactive", "Expired"}:
                raise ValueError
            if end:
                date.fromisoformat(end)
        except (ValueError, TypeError):
            flash("Please enter valid client details. Check the age, height, weight, date and adherence fields.", "error")
            return render_template("client_form.html", client=request.form), 400
        db = connect_db()
        try:
            try:
                db.execute("""INSERT INTO clients(name,age,height_cm,weight_kg,calories,target_weight_kg,
                    target_adherence,membership_status,membership_end,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (name, age, height, weight, round(weight * 24), target_weight, adherence, status, end,
                     datetime.utcnow().isoformat(timespec="seconds")))
                db.commit()
            except sqlite3.IntegrityError:
                flash("A client with that name already exists.", "error")
                return render_template("client_form.html", client=request.form), 409
        finally:
            db.close()
        flash(f"Client {name} was registered successfully.", "success")
        return redirect(url_for("dashboard"))

    @app.get("/clients/<int:client_id>")
    @login_required
    def client_detail(client_id):
        db = connect_db()
        try:
            client = get_client(db, client_id)
            if client is None:
                abort(404)
            workouts = get_activity(db, client_id, "workouts", "workout_date DESC, id DESC")
            progress = get_activity(db, client_id, "progress", "id ASC")
            metrics = get_activity(db, client_id, "metrics", "metric_date DESC, id DESC")
            exercises = [dict(row) for row in db.execute(
                "SELECT e.*, w.client_id, w.workout_date, w.workout_type FROM exercises e "
                "JOIN workouts w ON w.id=e.workout_id WHERE w.client_id=? ORDER BY w.workout_date DESC, e.id DESC",
                (client_id,)).fetchall()]
        finally:
            db.close()
        chart_progress = progress[-12:]
        chart_points = []
        for index, item in enumerate(chart_progress):
            x = 40 if len(chart_progress) == 1 else 40 + index * (520 / (len(chart_progress) - 1))
            y = 180 - (item["adherence"] * 1.4)
            chart_points.append({"x": round(x, 1), "y": round(y, 1), "label": item["week_label"], "adherence": item["adherence"]})
        return render_template("client_detail.html", client=client, workouts=workouts,
                               progress=progress, chart_points=chart_points, metrics=metrics,
                               exercises=exercises, today=date.today().isoformat())

    @app.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
    @roles_required("Admin")
    def edit_client(client_id):
        db = connect_db()
        try:
            client = get_client(db, client_id)
            if client is None:
                abort(404)
            if request.method == "GET":
                return render_template("client_form.html", client=client, editing=True)
            name = request.form.get("name", "").strip()
            try:
                age = int(request.form.get("age", "")); height = float(request.form.get("height_cm", "")); weight = float(request.form.get("weight_kg", ""))
                target_raw = request.form.get("target_weight_kg", "").strip(); target_weight = float(target_raw) if target_raw else None
                adherence = int(request.form.get("target_adherence", "80")); status = request.form.get("membership_status", ""); end = request.form.get("membership_end", "").strip() or None
                if not name or len(name) > 100 or not 1 <= age <= 120 or not 30 <= height <= 260 or not 1 <= weight <= 500: raise ValueError
                if target_weight is not None and not 1 <= target_weight <= 500: raise ValueError
                if not 0 <= adherence <= 100 or status not in {"Active", "Inactive", "Expired"}: raise ValueError
                if end: date.fromisoformat(end)
            except (ValueError, TypeError):
                flash("Please check the entered client details.", "error")
                return render_template("client_form.html", client=request.form, editing=True), 400
            try:
                db.execute("UPDATE clients SET name=?,age=?,height_cm=?,weight_kg=?,calories=?,target_weight_kg=?,target_adherence=?,membership_status=?,membership_end=? WHERE id=?",
                           (name, age, height, weight, round(weight*24), target_weight, adherence, status, end, client_id))
                db.commit()
            except sqlite3.IntegrityError:
                flash("Another client already uses that name.", "error")
                return render_template("client_form.html", client=request.form, editing=True), 409
        finally:
            db.close()
        flash("Client details updated.", "success")
        return redirect(url_for("client_detail", client_id=client_id))

    @app.post("/clients/<int:client_id>/delete")
    @roles_required("Admin")
    def delete_client(client_id):
        db = connect_db()
        try:
            if not get_client(db, client_id): abort(404)
            db.execute("DELETE FROM exercises WHERE workout_id IN (SELECT id FROM workouts WHERE client_id=?)", (client_id,))
            db.execute("DELETE FROM workouts WHERE client_id=?", (client_id,))
            db.execute("DELETE FROM progress WHERE client_id=?", (client_id,))
            db.execute("DELETE FROM metrics WHERE client_id=?", (client_id,))
            db.execute("DELETE FROM clients WHERE id=?", (client_id,))
            db.commit()
        finally:
            db.close()
        flash("Client and associated records deleted.", "success")
        return redirect(url_for("dashboard"))

    @app.post("/clients/<int:client_id>/generate-program")
    @roles_required("Admin")
    def generate_program(client_id):
        program_type = request.form.get("program_type", "Beginner")
        if program_type not in PROGRAM_TEMPLATES:
            flash("Select a valid programme category.", "error")
            return redirect(url_for("client_detail", client_id=client_id))
        db = connect_db()
        try:
            if not get_client(db, client_id): abort(404)
            selected = random.choice(PROGRAM_TEMPLATES[program_type])
            db.execute("UPDATE clients SET program=? WHERE id=?", (selected, client_id)); db.commit()
        finally:
            db.close()
        flash(f"Programme generated: {selected}.", "success")
        return redirect(url_for("client_detail", client_id=client_id))

    @app.post("/clients/<int:client_id>/workouts")
    @roles_required("Admin", "Staff")
    def add_workout(client_id):
        workout_date = request.form.get("workout_date", "").strip(); workout_type = request.form.get("workout_type", "").strip()
        duration_raw = request.form.get("duration_min", "").strip(); notes = request.form.get("notes", "").strip()
        try:
            date.fromisoformat(workout_date); duration = int(duration_raw)
            if not workout_type or len(workout_type)>80 or not 1<=duration<=600 or len(notes)>500: raise ValueError
        except (ValueError, TypeError):
            flash("Enter a valid date, workout type, duration (1–600 minutes) and notes (up to 500 characters).", "error")
            return redirect(url_for("client_detail", client_id=client_id))
        db = connect_db()
        try:
            if not get_client(db, client_id): abort(404)
            db.execute("INSERT INTO workouts(client_id,workout_date,workout_type,duration_min,notes) VALUES(?,?,?,?,?)", (client_id,workout_date,workout_type,duration,notes)); db.commit()
        finally: db.close()
        flash("Workout recorded.", "success")
        return redirect(url_for("client_detail", client_id=client_id))

    @app.post("/clients/<int:client_id>/progress")
    @roles_required("Admin", "Staff")
    def add_progress(client_id):
        week = request.form.get("week_label", "").strip()
        try:
            adherence = int(request.form.get("adherence", ""))
            if not week or len(week)>30 or not 0<=adherence<=100: raise ValueError
        except (ValueError, TypeError):
            flash("Enter a week label and adherence from 0 to 100.", "error")
            return redirect(url_for("client_detail", client_id=client_id))
        db = connect_db()
        try:
            if not get_client(db, client_id): abort(404)
            db.execute("INSERT INTO progress(client_id,week_label,adherence) VALUES(?,?,?)", (client_id,week,adherence)); db.commit()
        finally: db.close()
        flash("Progress entry saved.", "success")
        return redirect(url_for("client_detail", client_id=client_id))


    @app.post("/clients/<int:client_id>/exercises")
    @roles_required("Admin", "Staff")
    def add_exercise(client_id):
        workout_raw = request.form.get("workout_id", "").strip()
        name = request.form.get("exercise_name", "").strip()
        try:
            workout_id = int(workout_raw)
            sets = int(request.form.get("sets", ""))
            reps = int(request.form.get("reps", ""))
            weight_raw = request.form.get("weight_kg", "").strip()
            weight = float(weight_raw) if weight_raw else None
            if not name or len(name) > 100 or not 1 <= sets <= 100 or not 1 <= reps <= 1000:
                raise ValueError
            if weight is not None and not 0 <= weight <= 1000:
                raise ValueError
        except (ValueError, TypeError):
            flash("Enter a valid exercise, workout, sets, reps and optional weight.", "error")
            return redirect(url_for("client_detail", client_id=client_id))
        db = connect_db()
        try:
            if not get_client(db, client_id):
                abort(404)
            workout = db.execute("SELECT id FROM workouts WHERE id=? AND client_id=?", (workout_id, client_id)).fetchone()
            if workout is None:
                flash("Select a workout belonging to this client.", "error")
                return redirect(url_for("client_detail", client_id=client_id))
            db.execute("INSERT INTO exercises(workout_id,name,sets,reps,weight_kg) VALUES(?,?,?,?,?)",
                        (workout_id, name, sets, reps, weight))
            db.commit()
        finally:
            db.close()
        flash("Exercise recorded.", "success")
        return redirect(url_for("client_detail", client_id=client_id))

    @app.post("/clients/<int:client_id>/metrics")
    @roles_required("Admin", "Staff")
    def add_metric(client_id):
        metric_date = request.form.get("metric_date", "").strip()
        try:
            date.fromisoformat(metric_date)
            weight = float(request.form.get("weight_kg", ""))
            waist_raw = request.form.get("waist_cm", "").strip()
            body_fat_raw = request.form.get("body_fat_pct", "").strip()
            waist = float(waist_raw) if waist_raw else None
            body_fat = float(body_fat_raw) if body_fat_raw else None
            if not 1 <= weight <= 500:
                raise ValueError
            if waist is not None and not 1 <= waist <= 300:
                raise ValueError
            if body_fat is not None and not 0 <= body_fat <= 100:
                raise ValueError
        except (ValueError, TypeError):
            flash("Enter a valid date and weight; waist and body-fat values are optional.", "error")
            return redirect(url_for("client_detail", client_id=client_id))
        db = connect_db()
        try:
            if not get_client(db, client_id):
                abort(404)
            db.execute("INSERT INTO metrics(client_id,metric_date,weight_kg,waist_cm,body_fat_pct) VALUES(?,?,?,?,?)",
                        (client_id, metric_date, weight, waist, body_fat))
            db.execute("UPDATE clients SET weight_kg=?, calories=? WHERE id=?", (weight, round(weight * 24), client_id))
            db.commit()
        finally:
            db.close()
        flash("Body metrics saved.", "success")
        return redirect(url_for("client_detail", client_id=client_id))

    @app.get("/clients/<int:client_id>/report")
    @login_required
    def client_report(client_id):
        db = connect_db()
        try:
            client = get_client(db, client_id)
            if client is None: abort(404)
            workouts = get_activity(db, client_id, "workouts", "workout_date DESC, id DESC")
            progress = get_activity(db, client_id, "progress", "id ASC")
            metrics = get_activity(db, client_id, "metrics", "metric_date DESC, id DESC")
            exercises = [dict(row) for row in db.execute(
                "SELECT e.name,e.sets,e.reps,e.weight_kg,w.workout_date FROM exercises e "
                "JOIN workouts w ON w.id=e.workout_id WHERE w.client_id=? ORDER BY w.workout_date DESC,e.id DESC",
                (client_id,)).fetchall()]
        finally: db.close()
        pdf = FPDF(); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page(); pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 12, "ACEest Fitness & Gym - Client Report", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=11); pdf.cell(0, 8, f"Client: {client['name']}", new_x="LMARGIN", new_y="NEXT")
        for label, value in [("Age",client["age"]),("Height (cm)",client["height_cm"]),("Weight (kg)",client["weight_kg"]),("Programme",client["program"] or "Not assigned"),("Estimated calories",client["calories"]),("Target weight (kg)",client["target_weight_kg"] or "Not set"),("Target adherence (%)",client["target_adherence"]),("Membership",client["membership_status"]),("Membership end",client["membership_end"] or "Not set")]:
            pdf.cell(0, 7, f"{label}: {value}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4); pdf.set_font("Helvetica", "B", 12); pdf.cell(0,8,"Recent workouts",new_x="LMARGIN",new_y="NEXT"); pdf.set_font("Helvetica",size=10)
        for workout in workouts[:20]: pdf.multi_cell(0,6,f"{workout['workout_date']} | {workout['workout_type']} | {workout['duration_min']} min")
        pdf.ln(2); pdf.set_font("Helvetica","B",12); pdf.cell(0,8,"Progress and adherence",new_x="LMARGIN",new_y="NEXT"); pdf.set_font("Helvetica",size=10)
        for item in progress[:20]: pdf.cell(0,6,f"{item['week_label']}: {item['adherence']}%",new_x="LMARGIN",new_y="NEXT")
        pdf.ln(2); pdf.set_font("Helvetica","B",12); pdf.cell(0,8,"Body metrics history",new_x="LMARGIN",new_y="NEXT"); pdf.set_font("Helvetica",size=10)
        for item in metrics[:20]: pdf.cell(0,6,f"{item['metric_date']} | Weight: {item['weight_kg']} kg | Waist: {item['waist_cm'] if item['waist_cm'] is not None else 'N/A'} cm | Body fat: {item['body_fat_pct'] if item['body_fat_pct'] is not None else 'N/A'}%",new_x="LMARGIN",new_y="NEXT")
        pdf.ln(2); pdf.set_font("Helvetica","B",12); pdf.cell(0,8,"Exercises",new_x="LMARGIN",new_y="NEXT"); pdf.set_font("Helvetica",size=10)
        for item in exercises[:30]: pdf.cell(0,6,f"{item['workout_date']} | {item['name']} | {item['sets']} sets x {item['reps']} reps | Weight: {item['weight_kg'] if item['weight_kg'] is not None else 'N/A'} kg",new_x="LMARGIN",new_y="NEXT")
        payload = BytesIO(pdf.output()); payload.seek(0)
        safe_name = "".join(c for c in client["name"] if c.isalnum() or c in ("-","_" )).strip() or "client"
        return send_file(payload,mimetype="application/pdf",as_attachment=True,download_name=f"{safe_name}_report.pdf")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
