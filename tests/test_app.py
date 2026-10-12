"""Tests for authentication, role restrictions and fitness workflows."""
import pytest
from app import create_app


@pytest.fixture()
def client(tmp_path):
    database = tmp_path / "test_aceest.db"
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database)})
    with app.test_client() as test_client:
        yield test_client


def login(client, username="admin", password="Admin@123"):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def register_client(client, name="Aanya Sharma"):
    return client.post("/clients/new", data={
        "name": name, "age": "27", "height_cm": "165", "weight_kg": "62.5",
        "target_weight_kg": "58", "target_adherence": "85", "membership_status": "Active",
        "membership_end": "2027-01-31",
    }, follow_redirects=True)


@pytest.fixture(autouse=True)
def login_admin_for_each_test(request, client):
    # Tests marked no_login exercise the unauthenticated flow.
    if "no_login" not in request.keywords:
        login(client)


def test_dashboard_requires_login(client):
    client.post("/logout", follow_redirects=True)
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_page_loads(client):
    client.post("/logout")
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Welcome back" in response.data


def test_invalid_login_rejected(client):
    client.post("/logout")
    response = client.post("/login", data={"username": "admin", "password": "wrong"})
    assert response.status_code == 401
    assert b"Invalid username or password" in response.data


def test_staff_login_and_role_restriction(client):
    client.post("/logout")
    response = login(client, "staff", "Staff@123")
    assert response.status_code == 200
    assert b"Staff" in response.data
    forbidden = client.get("/clients/new")
    assert forbidden.status_code == 403


def test_health_endpoint(client):
    assert client.get("/health").get_json()["status"] == "healthy"


def test_clients_api_starts_empty(client):
    response = client.get("/clients")
    assert response.status_code == 200
    assert response.get_json() == {"count": 0, "clients": []}


def test_register_client_and_persistence(client):
    response = register_client(client)
    assert response.status_code == 200
    assert b"registered successfully" in response.data
    result = client.get("/clients").get_json()
    assert result["count"] == 1
    assert result["clients"][0]["name"] == "Aanya Sharma"
    assert result["clients"][0]["calories"] == 1500
    client.post("/logout")
    login(client)
    assert client.get("/clients").get_json()["count"] == 1


def test_duplicate_client_is_rejected(client):
    register_client(client)
    response = register_client(client)
    assert response.status_code == 409
    assert b"already exists" in response.data


@pytest.mark.parametrize("age", ["0", "121", "abc"])
def test_invalid_age_is_rejected(client, age):
    response = client.post("/clients/new", data={"name":"Bad Age", "age":age, "height_cm":"165", "weight_kg":"60", "target_adherence":"80", "membership_status":"Active"})
    assert response.status_code == 400


def test_invalid_adherence_is_rejected(client):
    response = client.post("/clients/new", data={"name":"Bad Adherence", "age":"25", "height_cm":"165", "weight_kg":"60", "target_adherence":"150", "membership_status":"Active"})
    assert response.status_code == 400


def test_program_generation(client, monkeypatch):
    register_client(client)
    record = client.get("/clients").get_json()["clients"][0]
    monkeypatch.setattr("app.random.choice", lambda options: options[0])
    response = client.post(f"/clients/{record['id']}/generate-program", data={"program_type":"Fat Loss"}, follow_redirects=True)
    assert response.status_code == 200 and b"Full Body HIIT" in response.data


def test_workout_can_be_recorded(client):
    register_client(client); record = client.get("/clients").get_json()["clients"][0]
    response = client.post(f"/clients/{record['id']}/workouts", data={"workout_date":"2026-10-12", "workout_type":"Strength training", "duration_min":"45", "notes":"Upper body"}, follow_redirects=True)
    assert response.status_code == 200 and b"Workout recorded" in response.data and b"Strength training" in response.data


def test_invalid_workout_duration_is_rejected(client):
    register_client(client); record = client.get("/clients").get_json()["clients"][0]
    response = client.post(f"/clients/{record['id']}/workouts", data={"workout_date":"2026-10-12", "workout_type":"Strength", "duration_min":"0", "notes":""}, follow_redirects=True)
    assert response.status_code == 200 and b"Enter a valid date" in response.data


def test_progress_and_chart(client):
    register_client(client); record = client.get("/clients").get_json()["clients"][0]
    response = client.post(f"/clients/{record['id']}/progress", data={"week_label":"Week 1", "adherence":"90"}, follow_redirects=True)
    assert response.status_code == 200 and b"Progress entry saved" in response.data
    assert b"90%" in response.data and b"adherence-chart" in response.data


def test_client_edit(client):
    register_client(client); record = client.get("/clients").get_json()["clients"][0]
    response = client.post(f"/clients/{record['id']}/edit", data={"name":"Aanya Updated", "age":"28", "height_cm":"165", "weight_kg":"61", "target_weight_kg":"57", "target_adherence":"90", "membership_status":"Active", "membership_end":""}, follow_redirects=True)
    assert response.status_code == 200 and b"Aanya Updated" in response.data


def test_client_report_returns_pdf(client):
    register_client(client); record = client.get("/clients").get_json()["clients"][0]
    response = client.get(f"/clients/{record['id']}/report")
    assert response.status_code == 200 and response.mimetype == "application/pdf" and response.data.startswith(b"%PDF")


def test_missing_client_returns_404(client):
    assert client.get("/clients/9999").status_code == 404


def test_delete_client_removes_related_data(client):
    register_client(client); record = client.get("/clients").get_json()["clients"][0]
    client.post(f"/clients/{record['id']}/workouts", data={"workout_date":"2026-10-12", "workout_type":"Cardio", "duration_min":"30", "notes":""})
    response = client.post(f"/clients/{record['id']}/delete", follow_redirects=True)
    assert response.status_code == 200 and client.get("/clients").get_json()["count"] == 0


def test_logout_clears_session(client):
    response = client.post("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert client.get("/", follow_redirects=False).status_code == 302


def test_exercise_can_be_recorded_and_is_shown(client):
    register_client(client)
    record = client.get("/clients").get_json()["clients"][0]
    client.post(f"/clients/{record['id']}/workouts", data={
        "workout_date": "2026-10-12", "workout_type": "Strength", "duration_min": "45", "notes": "Leg day"
    })
    db_path = client.application.config["DATABASE"]
    import sqlite3
    connection = sqlite3.connect(db_path)
    workout_id = connection.execute("SELECT id FROM workouts WHERE client_id=?", (record["id"],)).fetchone()[0]
    connection.close()
    response = client.post(f"/clients/{record['id']}/exercises", data={
        "workout_id": str(workout_id), "exercise_name": "Squat", "sets": "3", "reps": "10", "weight_kg": "40"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Exercise recorded" in response.data
    assert b"Squat" in response.data
    assert "3 × 10".encode("utf-8") in response.data


def test_exercise_cannot_be_attached_to_another_clients_workout(client):
    register_client(client, "Client One")
    register_client(client, "Client Two")
    records = client.get("/clients").get_json()["clients"]
    first, second = records[0], records[1]
    client.post(f"/clients/{first['id']}/workouts", data={
        "workout_date": "2026-10-12", "workout_type": "Strength", "duration_min": "45", "notes": ""
    })
    import sqlite3
    connection = sqlite3.connect(client.application.config["DATABASE"])
    workout_id = connection.execute("SELECT id FROM workouts WHERE client_id=?", (first["id"],)).fetchone()[0]
    connection.close()
    response = client.post(f"/clients/{second['id']}/exercises", data={
        "workout_id": str(workout_id), "exercise_name": "Squat", "sets": "3", "reps": "10", "weight_kg": "40"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Select a workout belonging to this client" in response.data


def test_body_metrics_are_saved_and_update_current_weight(client):
    register_client(client)
    record = client.get("/clients").get_json()["clients"][0]
    response = client.post(f"/clients/{record['id']}/metrics", data={
        "metric_date": "2026-10-12", "weight_kg": "60.5", "waist_cm": "75", "body_fat_pct": "22.5"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Body metrics saved" in response.data
    assert b"60.5" in response.data and b"75.0" in response.data and b"22.5" in response.data
    updated = client.get("/clients").get_json()["clients"][0]
    assert updated["weight_kg"] == 60.5
    assert updated["calories"] == 1452


def test_invalid_body_metrics_are_rejected(client):
    register_client(client)
    record = client.get("/clients").get_json()["clients"][0]
    response = client.post(f"/clients/{record['id']}/metrics", data={
        "metric_date": "2026-10-12", "weight_kg": "60", "waist_cm": "75", "body_fat_pct": "101"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Enter a valid date and weight" in response.data


def test_report_includes_metrics_and_exercises(client):
    register_client(client)
    record = client.get("/clients").get_json()["clients"][0]
    client.post(f"/clients/{record['id']}/metrics", data={
        "metric_date": "2026-10-12", "weight_kg": "60", "waist_cm": "75", "body_fat_pct": "22"
    })
    client.post(f"/clients/{record['id']}/workouts", data={
        "workout_date": "2026-10-12", "workout_type": "Strength", "duration_min": "45", "notes": ""
    })
    import sqlite3
    connection = sqlite3.connect(client.application.config["DATABASE"])
    workout_id = connection.execute("SELECT id FROM workouts WHERE client_id=?", (record["id"],)).fetchone()[0]
    connection.close()
    client.post(f"/clients/{record['id']}/exercises", data={
        "workout_id": str(workout_id), "exercise_name": "Squat", "sets": "3", "reps": "10", "weight_kg": "40"
    })
    response = client.get(f"/clients/{record['id']}/report")
    assert response.status_code == 200 and response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")


def test_staff_can_add_exercises_and_metrics_but_cannot_delete_client(client):
    register_client(client)
    record = client.get("/clients").get_json()["clients"][0]
    client.post("/logout")
    login(client, "staff", "Staff@123")
    response = client.post(f"/clients/{record['id']}/metrics", data={
        "metric_date": "2026-10-12", "weight_kg": "61", "waist_cm": "76", "body_fat_pct": "23"
    }, follow_redirects=True)
    assert response.status_code == 200 and b"Body metrics saved" in response.data
    assert client.post(f"/clients/{record['id']}/delete").status_code == 403
