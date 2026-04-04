# AI Resume & Cover Letter Creator

## Overview
A full-stack Progressive Web App (PWA) that uses Groq's AI (Llama 3) to help users with resume optimization, cover letter generation, job tracking, interview preparation, LinkedIn profile optimization, and career chat.

## Running the App
The app runs via gunicorn on port 5000:
```
python3 -m gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

## Architecture
- **Framework**: Flask (Python)
- **Database**: SQLite (`resume_app.db`) via Flask-SQLAlchemy
- **AI**: Groq API (Llama 3.3-70b) — configured via the Admin Panel at `/julisunkan`
- **File parsing**: pdfplumber (PDF), python-docx (DOCX)
- **PDF generation**: reportlab
- **Frontend**: Jinja2 templates + vanilla JS + CSS (PWA-enabled)

## Key Files
- `main.py` — App entry point
- `app.py` — Flask application factory, blueprint registration, DB init
- `extensions.py` — SQLAlchemy db instance
- `routes/` — Blueprint route handlers (resume, jobs, interview, chat, linkedin, admin, job_board)
- `models/` — SQLAlchemy models (resume, job, settings, job_post)
- `utils/ai_engine.py` — Groq AI integration
- `utils/parser.py` — PDF/DOCX text extraction
- `utils/job_aggregator.py` — External job board API fetching
- `templates/` — Jinja2 HTML templates
- `static/` — CSS, images, PWA manifest, service worker

## Configuration
- **Groq API Key**: Set via Admin Panel at `/julisunkan` (stored in DB Settings model) or via `GROQ_API_KEY` environment secret
- **Secret Key**: `SECRET_KEY` env var (defaults to a built-in value)
- **Admin Panel**: Protected at `/julisunkan`

## Dependencies
All dependencies listed in `requirements.txt`. Key packages:
- flask, flask-sqlalchemy, flask-cors
- groq
- pdfplumber, python-docx, reportlab
- gunicorn, psycopg2-binary, email_validator
