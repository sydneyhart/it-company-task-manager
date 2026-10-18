# Taskline — IT Company Task Manager

A Django portfolio project for an IT team's day-to-day work: clear priorities,
shared ownership, and a useful view of what's next.

## Features

- Overview dashboard with active, completed, overdue, and team counts.
- Task creation, editing, deletion, deadlines, four priorities, and task types.
- Multiple assignees per task, plus **Assign to me / Leave task** actions.
- Explicit **Mark as completed / Reopen task** actions.
- Search by task name or description; combine status, priority, type, tag, and
  “assigned to me” filters. Pagination retains the filters.
- Worker creation with Django's UserCreationForm, profile editing, deletion,
  and a searchable people directory.
- Searchable CRUD catalogs for positions, task types, and tags.
- Optional features: many-to-many task tags and separate active/completed task
  sections on every worker profile.
- Bootstrap 5, Crispy Forms, a custom responsive layout, and mobile navigation.
- Django admin registrations, demo data, and GitHub Actions checks.

All workspace pages require authentication. Like the course Taxi Service example,
authenticated teammates can manage shared records. This is a collaborative
workspace, not a multi-tenant application with role-based record permissions.
Profile forms cannot change staff/superuser flags or raw passwords.

## Run locally

Requires Python 3.12+.

    git clone https://github.com/sydneyhart/it-company-task-manager.git
    cd it-company-task-manager
    git checkout develop
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt
    python manage.py migrate
    python manage.py seed_demo
    python manage.py runserver

Open [Taskline locally](http://127.0.0.1:8000/).

Local demo credentials:

- Username: demo.user
- Password: Taskline-demo-2026!

The seed_demo command creates six workers and twelve tasks with relative deadlines.
Running it again does not duplicate records, reset existing passwords, or overwrite
edits. Use the --password option to choose the password when creating the demo
account for the first time. Other demo workers have unusable passwords; add real
teammates through People or Django admin.

The demo account is not a superuser. To use /admin/, first create positions with
seed_demo or the app, then run:

    python manage.py createsuperuser

Enter an existing position's primary key when prompted.

Do not seed demo data on a public production deployment. The sample credentials
above are intentionally public and are only for local evaluation.

## Checks

    flake8
    python manage.py check
    python manage.py makemigrations --check --dry-run
    python manage.py test

The 26 tests cover rendered pages, authentication, task and worker workflows,
password hashing, protection against privilege escalation in profile forms,
CSRF-protected POST actions, filter combinations, pagination encoding,
protected deletion, escaping, and repeatable demo seeding.

GitHub Actions runs the same checks on Python 3.12 for pushes and pull requests.

## Data model

![Taskline database diagram](docs/schema.png)

The editable source is [docs/schema.drawio](docs/schema.drawio). Open it in
[draw.io](https://app.diagrams.net/) to edit it. The PNG was exported from draw.io
and includes the optional Tag model and Django's two many-to-many join tables.

- Worker extends AbstractUser and belongs to a Position.
- Task belongs to a TaskType and has many workers and tags.
- In-use positions and task types are protected from deletion.
- Removing a worker or tag only removes its task connections; tasks remain.
- Deleting a task removes its assignment/tag links, leaving workers and tags intact.

## Configuration and deployment

Defaults are for local development with SQLite. The database, virtual environment,
and secrets are excluded from Git.

| Environment variable | Purpose | Default |
| --- | --- | --- |
| DJANGO_SECRET_KEY | Secret signing key | Development-only fallback |
| DJANGO_DEBUG | 1 for development, 0 for production | 1 |
| DJANGO_ALLOWED_HOSTS | Comma-separated hosts | localhost, 127.0.0.1, [::1] |
| DJANGO_TIME_ZONE | Workspace IANA timezone | UTC |

For deployment, provide a unique secret, set DJANGO_DEBUG=0, configure real hosts,
and run migrations and:

    python manage.py collectstatic --noinput

The app refuses to start with debug disabled unless a secret is supplied.
Run the WSGI application with:

    gunicorn config.wsgi:application

Serve staticfiles/ with your web server and put the application behind an HTTPS
reverse proxy. Configure secure cookies and other deployment settings for that
environment, and run:

    python manage.py check --deploy

The project does not include hosting or a live deployment.

Bootstrap loads from jsDelivr, and the DM Sans/Manrope fonts load from Google
Fonts. The interface falls back to system fonts if those resources are unavailable.
Django's console email backend is used for local development.

## Portfolio review

Implementation is on develop, with separate commits for models, workflows,
each new page, tests, and documentation. The review PR targets main.
Screenshots of every custom page, mobile layouts, and the database diagram are
attached in the PR's comment area.
