# ACEest Fitness & Gym — DevOps Assignment 1

A Flask web adaptation of the supplied ACEest Fitness & Gym Tkinter reference. It includes SQLite persistence, login with Admin/Staff roles, client management, fitness programmes, memberships, workout logging, progress/adherence charting and PDF reports. The repository also includes Pytest, Docker, Jenkins and GitHub Actions configuration.

## Features

- Login/logout with hashed passwords and Flask sessions.
- **Admin**: register, edit and delete clients; generate programmes; view reports and manage activity.
- **Staff**: view client details and record workouts and weekly progress; cannot create/edit/delete clients or generate programmes.
- SQLite database created automatically on first run; no separate database server is required.
- Client fields: age, height, weight, estimated calories, target weight/adherence and membership details.
- Suggested programmes in Fat Loss, Muscle Gain and Beginner categories. These are random template selections, not an AI model.
- Workout history, exercise-level tracking (exercise name, sets, reps and optional weight), weekly adherence records and an SVG line chart.
- Body metrics history for weight, waist circumference and body-fat percentage. Saving a weight measurement also updates the current client weight and demonstration calorie estimate.
- Downloadable PDF client reports include client details, workouts, exercises, progress/adherence and body metrics.
- Health endpoint at `/health`.
- Automated tests, Docker image, Jenkins pipeline and GitHub Actions workflow.

## Technology

Python 3.12, Flask, SQLite (Python's built-in `sqlite3`), Werkzeug password hashing, fpdf2, Pytest, Docker, Jenkins and GitHub Actions.

## Project structure

```text
ACEest-Fitness-DevOps/
├── app.py
├── requirements.txt
├── Dockerfile
├── Jenkinsfile
├── README.md
├── templates/ (login, dashboard, client forms and details)
├── static/style.css
├── tests/test_app.py
└── .github/workflows/main.yml
```

## Local setup — Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. On first startup, Flask creates `instance/aceest_fitness.db` and seeds two demo users if they do not already exist.

### Demo accounts

| Role | Username | Default password |
|---|---|---|
| Admin | `admin` | `Admin@123` |
| Staff | `staff` | `Staff@123` |

Set `ACEEST_ADMIN_PASSWORD` and `ACEEST_STAFF_PASSWORD` environment variables before the **first** startup to choose different initial passwords. Existing account passwords are not overwritten on later starts. Change the defaults before exposing the application beyond a local assignment demo. Set a strong `SECRET_KEY` environment variable for Flask sessions.

### Database and persistence

SQLite is included with Python; a separate database server or installation is not required. The app automatically creates its schema and the `instance/aceest_fitness.db` file. Client, workout, exercise, body-metric, progress and user records persist across app restarts. To use a different location, set `DATABASE_PATH` to a writable file path.

For Docker, the database lives at `/app/instance/aceest_fitness.db` inside the container. To preserve it when replacing/recreating containers, mount a host volume at `/app/instance`, for example:

```bash
docker build -t aceest-fitness .
docker run --rm -p 5000:5000 -v aceest-data:/app/instance -e SECRET_KEY="replace-with-a-long-random-secret" aceest-fitness
```

The sample passwords are for local assessment only. Use strong environment-supplied credentials and a secret key for any shared deployment. This educational app does not implement password reset, account administration, CSRF protection, or production-grade account lockout.

## Manual validation

1. Log in as `admin`; register a client and assign a programme.
2. Open the client profile; record a workout, add exercises to that workout, save body measurements and add weekly adherence; inspect the chart and measurement history.
3. Download a PDF report, edit the client, then log out.
4. Log in as `staff`; confirm that workout/progress forms work and admin-only client management actions return HTTP 403.
5. Restart the app and confirm saved records remain in the SQLite database.

## Tests and CI/CD

```powershell
python -m compileall -q app.py tests
python -m pytest -v
```

- **Docker:** builds a minimal Python image and runs Gunicorn as a non-root user.
- **GitHub Actions:** runs on every push and pull request; installs dependencies, checks syntax, runs Pytest, builds Docker and runs Pytest in the image.
# ACEest Fitness & Gym — DevOps Assignment 1

A Flask web adaptation of the supplied ACEest Fitness & Gym Tkinter reference. It includes SQLite persistence, login with Admin/Staff roles, client management, fitness programmes, memberships, workout logging, progress/adherence charting and PDF reports. The repository also includes Pytest, Docker, Jenkins and GitHub Actions configuration.

## Features

- Login/logout with hashed passwords and Flask sessions.
- **Admin**: register, edit and delete clients; generate programmes; view reports and manage activity.
- **Staff**: view client details and record workouts and weekly progress; cannot create/edit/delete clients or generate programmes.
- SQLite database created automatically on first run; no separate database server is required.
- Client fields: age, height, weight, estimated calories, target weight/adherence and membership details.
- Suggested programmes in Fat Loss, Muscle Gain and Beginner categories. These are random template selections, not an AI model.
- Workout history, exercise-level tracking (exercise name, sets, reps and optional weight), weekly adherence records and an SVG line chart.
- Body metrics history for weight, waist circumference and body-fat percentage. Saving a weight measurement also updates the current client weight and demonstration calorie estimate.
- Downloadable PDF client reports include client details, workouts, exercises, progress/adherence and body metrics.
- Health endpoint at `/health`.
- Automated tests, Docker image, Jenkins pipeline and GitHub Actions workflow.

## Technology

Python 3.12, Flask, SQLite (Python's built-in `sqlite3`), Werkzeug password hashing, fpdf2, Pytest, Docker, Jenkins and GitHub Actions.

## Project structure

```text
ACEest-Fitness-DevOps/
├── app.py
├── requirements.txt
├── Dockerfile
├── Jenkinsfile
├── README.md
├── templates/ (login, dashboard, client forms and details)
├── static/style.css
├── tests/test_app.py
└── .github/workflows/main.yml
```

## Local setup — Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. On first startup, Flask creates `instance/aceest_fitness.db` and seeds two demo users if they do not already exist.

### Demo accounts

| Role | Username | Default password |
|---|---|---|
| Admin | `admin` | `Admin@123` |
| Staff | `staff` | `Staff@123` |

Set `ACEEST_ADMIN_PASSWORD` and `ACEEST_STAFF_PASSWORD` environment variables before the **first** startup to choose different initial passwords. Existing account passwords are not overwritten on later starts. Change the defaults before exposing the application beyond a local assignment demo. Set a strong `SECRET_KEY` environment variable for Flask sessions.

### Database and persistence

SQLite is included with Python; a separate database server or installation is not required. The app automatically creates its schema and the `instance/aceest_fitness.db` file. Client, workout, exercise, body-metric, progress and user records persist across app restarts. To use a different location, set `DATABASE_PATH` to a writable file path.

For Docker, the database lives at `/app/instance/aceest_fitness.db` inside the container. To preserve it when replacing/recreating containers, mount a host volume at `/app/instance`, for example:

```bash
docker build -t aceest-fitness .
docker run --rm -p 5000:5000 -v aceest-data:/app/instance -e SECRET_KEY="replace-with-a-long-random-secret" aceest-fitness
```

The sample passwords are for local assessment only. Use strong environment-supplied credentials and a secret key for any shared deployment. This educational app does not implement password reset, account administration, CSRF protection, or production-grade account lockout.

## Manual validation

1. Log in as `admin`; register a client and assign a programme.
2. Open the client profile; record a workout, add exercises to that workout, save body measurements and add weekly adherence; inspect the chart and measurement history.
3. Download a PDF report, edit the client, then log out.
4. Log in as `staff`; confirm that workout/progress forms work and admin-only client management actions return HTTP 403.
5. Restart the app and confirm saved records remain in the SQLite database.

## Tests and CI/CD

```powershell
python -m compileall -q app.py tests
python -m pytest -v
```

- **Docker:** builds a minimal Python image and runs Gunicorn as a non-root user.
- **GitHub Actions:** runs on every push and pull request; installs dependencies, checks syntax, runs Pytest, builds Docker and runs Pytest in the image.
- **Jenkins:** The `Jenkinsfile` checks out the GitHub repository, creates a Python virtual environment, installs dependencies, checks Python syntax, runs Pytest and builds the Docker image tagged `aceest-fitness:jenkins`. The Jenkins agent requires Git, Python 3, pip, virtual-environment support and Docker Engine access. The Workspace Cleanup plugin is required for `cleanWs()`.

## Notes

The calorie number is a basic demonstration estimate, not medical advice. Programme generation randomly chooses a static template. This project is for coursework and should receive a security review before production use.


## Notes

The calorie number is a basic demonstration estimate, not medical advice. Programme generation randomly chooses a static template. This project is for coursework and should receive a security review before production use.
