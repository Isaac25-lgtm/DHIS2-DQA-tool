# Deployment Guide

## Deployment Philosophy

This platform is intentionally lightweight.

Recommended production shape:

- one FastAPI backend service
- one static React frontend
- one PostgreSQL database
- HTTPS termination
- environment variables stored server-side

Do not make Docker required. A virtual environment plus PostgreSQL is the primary deployment path.

## Supported Deployment Targets

- Render
- Railway
- VPS
- Institutional server

## Backend Deployment

### 1. Prepare Python environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure environment variables

Required variables:

```env
APP_NAME=UCMB HMIS 105 DQA Platform
APP_VERSION=0.6.0
ENVIRONMENT=production
DATABASE_URL=postgresql://...
SECRET_KEY=strong-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
DHIS2_BASE_URL=https://hmis.health.go.ug/api
AI_API_KEY=
AI_PROVIDER=
AI_MODEL=
CORS_ORIGINS=https://your-frontend.example.org
DEFAULT_MANAGER_NAME=System Manager
DEFAULT_MANAGER_EMAIL=admin@example.org
DEFAULT_MANAGER_PASSWORD=change-me
SEED_DEFAULT_MANAGER=false
```

### 3. Run migrations

```bash
cd backend
alembic upgrade head
```

### 4. Start the backend

Development-style command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Recommended production command:

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Frontend Deployment

### 1. Install and build

```bash
cd frontend
npm install
npm run build
```

### 2. Serve the static build

You can serve the built output from:

- Nginx
- Render static site
- Railway static hosting
- an institutional static hosting layer

If needed, set:

```env
VITE_API_BASE_URL=https://your-backend.example.org/api
```

## PostgreSQL Setup

### 1. Create the database

```sql
CREATE DATABASE ucmb_dqa;
```

### 2. Apply migrations

```bash
cd backend
alembic upgrade head
```

### 3. Backups

Enable regular PostgreSQL backups before production use.

## Reverse Proxy and HTTPS

Use HTTPS in production.

Typical setup:

- frontend served over HTTPS
- backend proxied behind HTTPS
- CORS restricted to the real frontend origin

## DHIS2 Connectivity

DHIS2 access is backend-only. Configure the base URL on the backend service, never in the frontend static site:

```env
DHIS2_BASE_URL=https://hmis.health.go.ug/api
```

After deployment, log in as a Manager, open Settings, and sign into DHIS2 with an authorized DHIS2 account. The backend validates the credentials and keeps the active DHIS2 session in backend process memory for organisation unit search, data element search, analytics pulls, and review refreshes.

The active DHIS2 session is cleared on DHIS2 sign-out or backend restart. Do not expose DHIS2 credentials in browser config, JavaScript bundles, logs, or public deployment dashboards.

## Operational Checklist

- set a strong `SECRET_KEY`
- restrict `CORS_ORIGINS`
- change the default manager password
- disable `SEED_DEFAULT_MANAGER` after initial setup
- keep DHIS2 password out of frontend storage and use manager DHIS2 sign-in from Settings
- test DHIS2 connection from Settings after deployment
- confirm live facility and data element search before creating production rounds
- keep AI API key server-side only
- enable PostgreSQL backups
- verify report privacy process before allowing `include_comments=true`
- monitor application logs
- remove test accounts before go-live

## Render Example

This repo includes `render.yaml` for a lightweight Render Blueprint:

- `ucmb-dqa-backend`: Python web service from `backend/`
- `ucmb-dqa-frontend`: static React site from `frontend/`
- `ucmb-dqa-postgres`: managed PostgreSQL database

Render setup notes:

- connect the GitHub repository to Render
- create services from the Blueprint
- set `SECRET_KEY` on the backend service
- set `CORS_ORIGINS` on the backend service to the deployed frontend URL
- set `VITE_API_BASE_URL` on the frontend static service to `https://<backend-service>.onrender.com/api`
- keep `SEED_DEFAULT_MANAGER=false` after initial setup
- the backend start command runs `alembic upgrade head` before starting Uvicorn
- sign into DHIS2 from Manager Settings after deployment; DHIS2 passwords are not stored in Render environment variables

## Railway Example

- Backend: Python service
- Frontend: static or separate web service
- Database: PostgreSQL plugin/service
- Set the same environment variables
- Run migrations before serving traffic

## VPS or Institutional Server Example

- Install Python 3.12+
- Install Node.js for frontend build
- Install PostgreSQL
- Build frontend
- Run backend under `gunicorn` + `uvicorn.workers.UvicornWorker`
- Use Nginx or Apache as reverse proxy
- Enable HTTPS

## What This Deployment Guide Avoids

- no Kubernetes
- no microservices
- no mandatory Docker workflow
- no distributed background workers
- no service-worker-heavy offline infrastructure

The goal is a maintainable UCMB-ready deployment path, not a platform-engineering project.
