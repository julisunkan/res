# AI Resume & Cover Letter Creator

A full-stack Progressive Web App (PWA) built with Python Flask — an AI-powered job application assistant.

## Features

- **Resume Builder**: Upload PDF/DOCX, optimize with AI, generate ATS-friendly resume + cover letter, match scoring
- **Job Tracker**: Add/edit/delete job applications, track status (Applied / Interview / Offer / Rejected), analytics dashboard
- **Interview Prep**: Generate AI interview questions + sample answers from any job description
- **Career Chat**: AI career assistant chatbot (resume tips, salary negotiation, career advice)
- **LinkedIn Optimizer**: AI-improved headline and About section
- **Student Mode**: Generate a professional resume from skills + education only
- **Section Editor**: Rewrite specific resume sections
- **PDF Export**: Download optimized resume and cover letter as PDF
- **PWA**: Installable, offline-capable via service worker

## Tech Stack

- **Backend**: Python 3.11, Flask, Flask-SQLAlchemy, Flask-CORS
- **Database**: SQLite (via SQLAlchemy ORM)
- **AI**: Groq API (llama3-70b-8192 model)
- **File Parsing**: pdfplumber (PDF), python-docx (DOCX)
- **PDF Export**: ReportLab
- **Frontend**: HTML5, CSS3 (custom dark theme), Vanilla JavaScript

## Project Structure

```
app.py              # App factory
extensions.py       # Shared SQLAlchemy instance
requirements.txt    # Python dependencies

routes/
  resume.py         # Resume upload, optimize, analyze, export
  jobs.py           # Job tracker CRUD + analytics
  interview.py      # Interview question generation
  chat.py           # Career chatbot
  linkedin.py       # LinkedIn profile optimizer

utils/
  parser.py         # PDF/DOCX text extraction
  ai_engine.py      # Groq API calls (all AI functions)
  analyzer.py       # Match analysis + job description analysis
  pdf_exporter.py   # ReportLab PDF generation

models/
  resume.py         # Resume SQLAlchemy model
  job.py            # Job SQLAlchemy model

templates/
  base.html             # Base layout with navigation
  index.html            # Dashboard
  resume_builder.html   # Resume Builder (4 tabs)
  job_tracker.html      # Job Tracker (3 tabs)
  interview_prep.html   # Interview Prep
  career_chat.html      # Career Chat
  linkedin_optimizer.html # LinkedIn Optimizer

static/
  css/style.css       # Dark theme styles
  manifest.json       # PWA manifest
  service-worker.js   # PWA service worker
  favicon.ico
  images/icon-192.png, icon-512.png
```

## Environment Variables / Secrets

- `GROQ_API_KEY` (required) — Groq API key for all AI features. Get one free at https://console.groq.com
- `SECRET_KEY` (optional) — Flask secret key (defaults to a dev key)

## Admin Panel

Hidden admin panel at `/julisunkan` — not linked anywhere on the public site.

**Default password:** `admin123` — change it immediately in the Security tab.

### Admin capabilities:
- **Overview** — live stats and AI connection status
- **AI Config** — enter Groq API key, select model, set max tokens
- **App Settings** — change app name, tagline, upload limits
- **Resumes** — view, edit, delete all saved resumes (bulk delete supported)
- **Job Applications** — view, edit, delete all tracked jobs
- **Security** — change admin password, nuke all content

## Running

The app starts automatically via the "Start application" workflow on port 5000.

To run manually:
```bash
python3 app.py
```
