# UCMB HMIS 105 Data Quality Assessment Platform

UCMB HMIS 105 Data Quality Assessment Platform is a lightweight, production-ready web application for comparing three HMIS 105 data sources:

1. Source register recount value
2. HMIS 105 monthly report value
3. DHIS2 system value pulled automatically through the DHIS2 API

The platform is a clean modular monolith built for a relatively small operational user base. The backend is Python-first, PostgreSQL is mandatory in every environment, and Docker is optional only.

**Production hosting target:** [Render](https://render.com) for the FastAPI backend and the static React frontend, with [Neon](https://neon.tech) serverless Postgres as the database. See the [Deploy to Render with Neon Postgres](#deploy-to-render-with-neon-postgres) section below.

## V1 Feature Status

Prompt 1 through Prompt 6 are implemented in the current codebase.

Current V1 capabilities:

- JWT authentication and role-aware access control
- backend-mediated DHIS2 connection testing
- live DHIS2 facility search and idempotent facility import
- live DHIS2 data element search and idempotent indicator import
- facility registry with DHIS2 org unit UIDs, codes, paths, parents, and levels
- HMIS 105 indicator library, confirmed seed mappings, and imported DHIS2 data elements
- manager assessment round builder with Team Lead and Team Member assignment
- online assessment workspace with DHIS2 auto-population, compact difference flags, and one general facility comment
- offline IndexedDB drafts and manual sync
- DQA comparison engine and scoring
- analytics dashboard, facility results, indicator analytics, and heatmap
- corrective action workflow with verification states
- AI-safe report generation with template fallback
- DOCX, PDF, and XLSX exports
- final dashboard and settings polish

## Tech Stack

- Backend: FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, pydantic-settings, python-jose, passlib, httpx
- Database: PostgreSQL only
- Frontend: React, TypeScript, Vite, Tailwind CSS
- Charts and tables: Recharts, TanStack Table
- Forms: React Hook Form, Zod
- Exports: python-docx, openpyxl, ReportLab

## PostgreSQL-Only Rule

This codebase supports PostgreSQL only. SQLite is not used or assumed anywhere in development, tests, staging, or production.

## Deploy to Render with Neon Postgres

The repository ships with a `render.yaml` Blueprint that provisions one Python web service. That single Render service builds the React frontend, runs FastAPI, serves the compiled frontend from `/`, and serves the backend API from `/api`. The database is **external Neon Postgres**; Render runs the application process and connects to Neon via a connection string env var.

### 1. Create the Neon database

1. Sign in at [console.neon.tech](https://console.neon.tech).
2. Create a new project (free tier is fine for piloting).
3. Inside the project, ensure a database named `ucmb_dqa` exists (create one if Neon defaulted to `neondb`).
4. Open the Connection Details panel and copy the **pooled** connection string. It looks like:

   ```text
   postgresql://USER:PASSWORD@ep-xxxxxxx-pooler.REGION.aws.neon.tech/ucmb_dqa?sslmode=require
   ```

   Notes:
   - The `?sslmode=require` suffix is mandatory — Neon enforces TLS.
   - Use the **pooled** endpoint (the host with `-pooler` in it) for serverless-friendly connections under FastAPI. The non-pooled endpoint also works but uses more connections.
   - Keep the password safe; it will live only in Render env vars, never in source control.

### 2. Push this repository to GitHub

This repository is already configured to push to:

```text
https://github.com/Isaac25-lgtm/DHIS2-DQA-tool
```

Push the `main` branch (or whichever branch you want Render to deploy from). Make sure `.env` is **never** committed (already covered by `.gitignore`).

### 3. Create the Render Blueprint

1. In the [Render dashboard](https://dashboard.render.com), click **New +** → **Blueprint**.
2. Connect the GitHub account that owns the `DHIS2-DQA-tool` repository.
3. Pick the repository. Render auto-detects `render.yaml` and lists one service:
   - `ucmb-dqa-platform` (Python web service serving both frontend and API)
4. Render prompts you for the env vars marked `sync: false` (they are intentionally **not** stored in `render.yaml`). Fill them in:

   | Variable | Where it goes | Value |
   |---|---|---|
   | `DATABASE_URL` | backend | The Neon connection string from Step 1 (full URL, including `?sslmode=require`) |
   | `SECRET_KEY` | backend | A long random string. Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
   | `DEFAULT_MANAGER_PASSWORD` | backend | Required only if you temporarily set `SEED_DEFAULT_MANAGER=true`. Use a strong password, not `ChangeMe123!` |
   | `AI_API_KEY` | backend | Your DeepSeek (or other provider) API key. Optional — leave blank to use deterministic template fallback reporting |
   | `AI_PROVIDER` | backend | e.g. `deepseek` |
   | `AI_MODEL` | backend | e.g. `deepseek-v4-pro` |
   | `VITE_API_BASE_URL` | app | Already set to `/api` in `render.yaml` for same-origin deployment |

5. Click **Apply**. Render builds the frontend, installs the backend, runs `alembic upgrade head`, then starts Uvicorn. The schema is created in Neon on the first boot.

### 4. Seed the default manager (one-time)

`render.yaml` ships with `SEED_DEFAULT_MANAGER=false` for safety. To create the first manager account:

1. After the first successful deploy, open the `ucmb-dqa-platform` service in the Render dashboard.
2. Either set `SEED_DEFAULT_MANAGER=true` plus `DEFAULT_MANAGER_EMAIL` and a strong `DEFAULT_MANAGER_PASSWORD` env var and trigger a redeploy (the lifespan creates the manager on next boot if the email does not yet exist), or
3. Use the Render shell tab and run a one-off Python script that inserts a manager user via `app.services.user_service`.

Either way, turn `SEED_DEFAULT_MANAGER=false` again after the first manager exists. The backend refuses to boot outside development if seeding is enabled with the scaffold password `ChangeMe123!`.

### 5. Verify the deployment

- App readiness: `https://ucmb-dqa-platform.onrender.com/api/ready` returns `{"status":"ready"}` only when Postgres and the core schema are reachable. Render points its health check here.
- App status: `https://ucmb-dqa-platform.onrender.com/api/health` returns process status and database availability for inspection.
- Frontend: open the service URL Render assigned to `ucmb-dqa-platform`. The login page should render from the same origin as the API.
- Sign in as the default manager.
- Open Settings - DHIS2 sign-in as a manager to enable live DHIS2 search, import, and pre-sync.

### Notes about the Render free tier

- Render free web services **spin down after 15 minutes of inactivity**. The first request after sleep takes 30–60 seconds while the service wakes up.
- Neon free databases also pause after periods of inactivity. The first query after pause takes ~1–3 seconds.
- For real production use, upgrade both Render and Neon to paid plans so the service stays warm.

### Aligning local development with the same env shape

When developing locally with a Neon database (instead of local Postgres), set these in your local `.env`:

```env
DATABASE_URL=postgresql://USER:PASSWORD@ep-xxxxxxx-pooler.REGION.aws.neon.tech/ucmb_dqa?sslmode=require
TEST_DATABASE_URL=postgresql://USER:PASSWORD@ep-xxxxxxx-pooler.REGION.aws.neon.tech/ucmb_dqa_test?sslmode=require
```

You may want to create the test database as a **branch** in Neon so the production data stays untouched.

## Project Structure

```text
ucmb-dqa-platform/
|-- README.md
|-- .env.example
|-- docs/
|-- backend/
`-- frontend/
```

Key docs:

- `docs/PROJECT_CONTEXT.md`
- `docs/BUILD_PROMPTS.md`
- `docs/SYSTEM_ARCHITECTURE.md`
- `docs/UI_STYLE_GUIDE.md`
- `docs/DATA_MODEL.md`
- `docs/DHIS2_MAPPING_SEED.md`
- `docs/DEPLOYMENT.md`

## Backend Setup

From the project root:

```bash
cd backend
python -m venv .venv
```

Activate the environment:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` at the project root and set real values.

Run migrations:

```bash
alembic upgrade head
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

Backend base URL:

```text
http://localhost:8000
```

## Frontend Setup

From the project root:

```bash
cd frontend
npm install
npm run dev
```

Frontend base URL:

```text
http://localhost:5173
```

Optional frontend API override:

```bash
# Linux / macOS
export VITE_API_BASE_URL=http://localhost:8000/api

# Windows PowerShell
$env:VITE_API_BASE_URL="http://localhost:8000/api"
```

## Database Setup

Create the application database:

```sql
CREATE DATABASE ucmb_dqa;
```

Create the test database:

```sql
CREATE DATABASE ucmb_dqa_test;
```

Set:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ucmb_dqa
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ucmb_dqa_test
```

## Environment Variables

Key variables from `.env.example`:

```env
APP_NAME=UCMB HMIS 105 DQA Platform
APP_VERSION=0.6.0
ENVIRONMENT=development
# Local Postgres
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ucmb_dqa
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ucmb_dqa_test
# Neon Postgres (production / cloud development) — note the mandatory ?sslmode=require
# DATABASE_URL=postgresql://USER:PASSWORD@ep-xxxxxxx-pooler.REGION.aws.neon.tech/ucmb_dqa?sslmode=require
SECRET_KEY=change-this-secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
DHIS2_BASE_URL=https://hmis.health.go.ug/api
DHIS2_USERNAME=
DHIS2_PASSWORD=
AI_API_KEY=
AI_PROVIDER=deepseek
AI_MODEL=deepseek-v4-pro
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
DEFAULT_MANAGER_NAME=System Manager
DEFAULT_MANAGER_EMAIL=admin@ucmb-dqa.local
DEFAULT_MANAGER_PASSWORD=ChangeMe123!
SEED_DEFAULT_MANAGER=true
```

`CORS_ORIGINS` is parsed as either a JSON array (recommended) or a comma-separated list. The Render Blueprint uses same-origin `/api` calls, so it sets `CORS_ORIGINS=[]`; only add origins if you later host a separate frontend domain.

## Default Manager Seed

When `SEED_DEFAULT_MANAGER=true`, the backend startup creates the default manager only if the email does not already exist.

Default local login:

```text
Email: admin@ucmb-dqa.local
Password: ChangeMe123! (development only; production startup rejects this password when `SEED_DEFAULT_MANAGER=true`)
```

Change this password immediately in any shared or production-like environment.

## Confirmed Indicator Seed

Manager-only seed endpoint:

```text
POST /api/indicators/seed-confirmed
```

This seeds the confirmed UCMB HMIS 105 mappings stored in:

- `docs/DHIS2_MAPPING_SEED.md`
- `backend/app/seed/indicator_seed.py`

## DHIS2 Sign-In

DHIS2 credentials are not hard-coded in source code and are not stored in frontend/browser storage.

Configure the DHIS2 base URL in the backend environment:

```env
DHIS2_BASE_URL=https://hmis.health.go.ug/api
```

Optionally set `DHIS2_USERNAME` and `DHIS2_PASSWORD` server-side if this local or deployed backend should keep DHIS2 sync available after process restarts. If those are blank, a manager must sign in from Settings after every backend restart before live DHIS2 search, import, or pre-sync can run.

After signing into the UCMB DQA Platform, a Manager opens Settings and signs into DHIS2 using their DHIS2 username and password. The password is sent to FastAPI over the authenticated UCMB session, verified against DHIS2, and kept only in server memory for backend DHIS2 API calls.

The active DHIS2 session is cleared when the manager signs out of DHIS2 or when the backend process restarts. If no server-side DHIS2 username/password is configured, a manager must sign in again before live DHIS2 search, import, or pre-sync can run.

DHIS2 behavior:

- managers can test backend DHIS2 connectivity from Settings
- managers must sign in to DHIS2 from Settings before live DHIS2 operations
- managers can search DHIS2 organisation units and import facilities into the local registry
- managers can search DHIS2 data elements and import indicators into the local library
- existing DHIS2 operands remain supported; a richer live category option combo picker is a future refinement for cases where managers must choose exact category options
- managers pre-sync DHIS2 values before publishing so assessors open assignments with the system figures already available
- both simple UIDs and operands are supported
- `dhis2_value_at_assessment` is the authoritative DQA comparison value
- later refresh values can be stored separately without replacing the field-time pull

DHIS2 management endpoints:

- `POST /api/dhis2/session/login`
- `POST /api/dhis2/session/logout`
- `GET /api/dhis2/connection-status`
- `GET /api/dhis2/facilities/search?query=<text>`
- `GET /api/dhis2/data-elements/search?query=<text>`
- `POST /api/facilities/import-from-dhis2`
- `POST /api/indicators/import-from-dhis2`

These endpoints require UCMB DQA authentication and never expose the DHIS2 password.

## Assessment Team Assignment

Assessment facilities now support a field team model:

- broad platform role: `ASSESSOR`
- assessment-level roles: `TEAM_LEAD`, `TEAM_MEMBER`
- Team Lead and Team Members can enter data when allowed
- only Team Lead, or a Team Member with `can_submit=true`, can submit final assessment data
- every selected facility must have a Team Lead before publishing

Team endpoints:

- `GET /api/assessment-facilities/{assessment_facility_id}/team-members`
- `POST /api/assessment-facilities/{assessment_facility_id}/team-members`
- `PUT /api/assessment-facilities/{assessment_facility_id}/team-members`
- `DELETE /api/assessment-facilities/{assessment_facility_id}/team-members/{team_member_id}`

## AI Reporting Safety

AI report generation is constrained by design:

- AI never changes DQA values
- AI never updates DHIS2
- AI never creates official corrections
- AI never invents missing numbers, facilities, indicators, causes, or actions
- comments are excluded by default
- comments are included only when `include_comments=true`
- report generation logs are stored for auditability
- if `AI_API_KEY` is missing, the system uses deterministic template fallback reporting

## Offline Workflow

Offline workflow is lightweight and device-local:

1. User logs in online.
2. User opens an assigned assessment online once.
3. Workspace package is cached in IndexedDB.
4. User continues draft entry offline if needed.
5. Local drafts autosave in IndexedDB.
6. User manually syncs pending drafts later.
7. If the token expired, relogin is required before sync.

The platform does not use service workers or heavy background sync for V1.

## Comparison and Analytics

Prompt 5 introduced:

- null-safe and zero-safe comparison rules
- discrepancy classification
- severity handling
- death and high-risk indicator stricter treatment
- facility scoring and score categories
- round, facility, indicator, source-document, and heatmap analytics
- corrective action suggestions and lifecycle tracking

## Reports and Exports

Supported report types:

- `FACILITY_DQA_REPORT`
- `CONSOLIDATED_UCMB_DQA_REPORT`
- `CORRECTIVE_ACTION_REPORT`
- `EXECUTIVE_SUMMARY`

Supported report workflow:

1. Generate report
2. Review report
3. Approve report
4. Export report
5. Archive if needed

Supported export endpoints:

- `GET /api/reports/{report_id}/export/docx`
- `GET /api/reports/{report_id}/export/pdf`
- `GET /api/reports/{report_id}/export/xlsx`

## Current API Surface

Authentication:

- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

Core management:

- users
- facilities
- `POST /api/facilities/import-from-dhis2`
- indicators
- `POST /api/indicators/import-from-dhis2`
- assessment rounds
- assessment facility team-member endpoints

DHIS2:

- `POST /api/dhis2/session/login`
- `POST /api/dhis2/session/logout`
- `GET /api/dhis2/connection-status`
- `GET /api/dhis2/facilities/search`
- `GET /api/dhis2/data-elements/search`

Workspace and sync:

- `GET /api/my-assessments`
- `GET /api/my-assessments/{assessment_facility_id}`
- `GET /api/my-assessments/{assessment_facility_id}/workspace`
- `POST /api/my-assessments/{assessment_facility_id}/pull-dhis2`
- `POST /api/my-assessments/{assessment_facility_id}/sync-with-dhis2`
- `POST /api/my-assessments/{assessment_facility_id}/values`
- `POST /api/my-assessments/{assessment_facility_id}/source-documents`
- `POST /api/my-assessments/{assessment_facility_id}/general-comment`
- `POST /api/my-assessments/{assessment_facility_id}/submit`
- `POST /api/my-assessments/{assessment_facility_id}/send-to-manager`
- `POST /api/sync/assessment-draft`
- `POST /api/assessment-rounds/{round_id}/sync-dhis2-values`
- `POST /api/assessment-facilities/{assessment_facility_id}/refresh-dhis2-values`

Comparison and analytics:

- `POST /api/assessment-facilities/{assessment_facility_id}/run-comparison`
- `GET /api/assessment-facilities/{assessment_facility_id}/comparison-results`
- `POST /api/assessment-rounds/{round_id}/run-comparison`
- `GET /api/assessment-rounds/{round_id}/comparison-summary`
- analytics summary, facility, indicator, source-document, and heatmap endpoints

Corrective actions:

- list, create, update, resolve, verify, close
- assessment-level and round-level suggestion endpoints

Reports and exports:

- `POST /api/reports/generate`
- `GET /api/reports`
- `GET /api/reports/{report_id}`
- `PUT /api/reports/{report_id}`
- `POST /api/reports/{report_id}/review`
- `POST /api/reports/{report_id}/approve`
- `POST /api/reports/{report_id}/archive`
- export endpoints listed above

System:

- `GET /api/health`
- `GET /api/ready`
- `GET /api/system/info`

## Testing and Verification

The test suite uses PostgreSQL through `TEST_DATABASE_URL`.

Prompt 4, Prompt 5, and Prompt 6 verification in this implementation included:

- backend compile check
- backend report/export tests
- backend workspace/sync/comparison analytics tests
- backend DHIS2 import and field-team workflow tests
- frontend production build

Example local test command:

```powershell
$env:PYTHONPATH='f:\MY FILES\DATA SCIENCE\UCMB DQA\ucmb-dqa-platform\backend'
$env:TEST_DATABASE_URL='postgresql://postgres:YOUR_PASSWORD@localhost:5432/ucmb_dqa_test'
python -m pytest backend\tests -q
```

## Lightweight Deployment

Deployment guidance is in `docs/DEPLOYMENT.md`.

Recommended shape:

- one FastAPI backend service
- one static React frontend
- one PostgreSQL database (Neon serverless Postgres recommended)
- HTTPS
- environment variables stored server-side

The default deployment target supported by this repository is **Render + Neon** — see [Deploy to Render with Neon Postgres](#deploy-to-render-with-neon-postgres) above for the full step-by-step.

Other supported targets:

- Railway
- VPS
- institutional server

## AI Provider

The report generator supports deterministic template fallback plus live AI generation.

For DeepSeek:

```env
AI_PROVIDER=deepseek
AI_MODEL=deepseek-v4-pro
AI_API_KEY=your-deepseek-api-key
```

The backend calls DeepSeek's chat-completions API server-side only. The API key is never exposed through frontend system-info responses.

This repo includes `render.yaml` for a Render Blueprint with:

- one Python web service (`ucmb-dqa-platform`) that serves both the React frontend and FastAPI API
- **external Neon Postgres** as the database (provided via the `DATABASE_URL` env var, not provisioned by Render)

Before first Render deploy, set the env vars marked `sync: false` in `render.yaml`:

- `DATABASE_URL`: your full Neon connection string (with `?sslmode=require`)
- `SECRET_KEY`: a strong random string
- `AI_API_KEY`, `AI_PROVIDER`, `AI_MODEL`: optional, for AI report drafting
- `SEED_DEFAULT_MANAGER`, `DEFAULT_MANAGER_EMAIL`, `DEFAULT_MANAGER_PASSWORD`: only for the first manager seed

The full step-by-step lives in [Deploy to Render with Neon Postgres](#deploy-to-render-with-neon-postgres).

## Production Checklist

- strong `SECRET_KEY`
- restricted `CORS_ORIGINS`
- HTTPS enabled
- DHIS2 password never stored in frontend; active DHIS2 session is backend-only and cleared on sign-out or restart
- AI API key stored server-side only
- PostgreSQL backups enabled
- default manager password changed
- test accounts reviewed or removed
- report privacy settings reviewed before using `include_comments=true`

## V1 Limitations

- no automatic DHIS2 corrections
- no AI-driven system-data updates
- no service-worker-heavy offline architecture
- no Docker requirement baked into the runtime path
- no microservices or distributed workflow engine

## Next Steps After V1

- richer reviewer workflow refinements
- more advanced conflict-resolution UX for offline drafts
- operational observability and deployment hardening
- optional provider abstraction improvements for AI reporting
