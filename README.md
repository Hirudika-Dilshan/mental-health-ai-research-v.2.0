# Mental Health AI Research v2.0

Research-focused web application scaffold with a React frontend and FastAPI backend for mental-health-related workflows.

## Current Scope

This version currently includes:
- User sign up and login flows
- Supabase-backed authentication through a FastAPI API
- Protected dashboard with direct action cards
- Post-login routes for:
  - Self Anxiety Test
  - Depression Test
  - General Chat
- Profile section on the dashboard
- Session-based auth state in the browser (`sessionStorage`)

The broader research roadmap (assessment automation, anomaly detection, linguistic analysis) is captured in [`simplified_project.txt`](./simplified_project.txt).

## Tech Stack

- Frontend: React + Vite + React Router
- Backend: FastAPI + Uvicorn + HTTPX
- Auth/Data provider: Supabase

## Project Structure

```text
.
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   `-- __init__.py
|   `-- requirements.txt
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |-- context/
|   |   `-- pages/
|   |-- package.json
|   `-- vite.config.js
`-- simplified_project.txt
```

## Prerequisites

- Node.js 18+
- Python 3.11+
- A Supabase project

## Environment Variables

Create `backend/.env`:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=your_supabase_service_role_key
SUPABASE_ANON_KEY=your_supabase_anon_key
FRONTEND_URL=http://localhost:5173
```

Optional frontend env (`frontend/.env`):

```env
VITE_API_URL=http://localhost:8000
```

If `VITE_API_URL` is not set, the frontend defaults to `http://localhost:8000`.

## Run Locally

### 1. Start backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend default URL: `http://localhost:5173`

## API Endpoints

- `GET /health` - Health check
- `POST /register` - Create user (via Supabase admin API)
- `POST /login` - Authenticate user and return tokens + profile info

## Frontend Routes

- `/signup` - Registration page
- `/login` - Login page
- `/dashboard` - Main post-login home (action selection + profile)
- `/anxiety-test` - Anxiety assessment page (UI scaffold)
- `/depression-test` - Depression assessment page (UI scaffold)
- `/general-chat` - General conversation page (UI scaffold)

## Notes

- Do not expose `SUPABASE_SERVICE_KEY` in frontend code.
- This is a research prototype and not production-hardened.
- CORS is restricted to `FRONTEND_URL` from backend env.
- If you get `Cannot reach Supabase` / `502`, verify `SUPABASE_URL` exactly matches your Supabase project URL from `Settings -> API`.

## Next Steps

- Add conversational chat and message persistence
- Implement PHQ-9/GAD-7 conversational assessments
- Add linguistic feature extraction and anomaly detection modules
- Add experiment logging and evaluation notebooks
