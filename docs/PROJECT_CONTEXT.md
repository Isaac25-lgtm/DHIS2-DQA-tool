# UCMB HMIS 105 Data Quality Assessment Platform - Project Context

## System Name

UCMB HMIS 105 Data Quality Assessment Platform

## Purpose

This platform helps UCMB compare three sources of HMIS 105 data for a selected facility and reporting period:

1. Register recount value
2. HMIS 105 monthly report value
3. DHIS2 system value pulled through the backend DHIS2 API adapter

It is a full workflow platform, not only a dashboard. It supports planning, assignment, online and offline assessment entry, DHIS2 auto-population, comparison, scoring, analytics, corrective actions, reporting, and exports.

## Non-Negotiable Architecture Rules

- Python backend only
- PostgreSQL only in development, test, staging, and production
- React + TypeScript + Vite + Tailwind frontend
- Lightweight modular monolith
- No microservices
- No Kubernetes
- No SQLite
- No heavy queueing or distributed infrastructure
- No Docker requirement

## User Roles

1. Manager
2. Assessor
3. Reviewer
4. Viewer

All users authenticate before accessing the platform.

## Core Workflow

1. Manager signs into DHIS2 from Settings after signing into the UCMB platform.
2. Manager tests the backend DHIS2 connection from Settings.
3. Manager searches DHIS2 facilities live and imports selected org units into the local facility registry.
4. Manager searches DHIS2 HMIS 105 data elements live and imports selected data elements or operands into the local indicator library.
5. Manager maintains imported facilities and the indicator library.
6. Manager creates an assessment round.
7. Manager selects the indicators that appear in that round.
8. Manager selects facilities from the local imported registry.
9. Manager assigns a Team Lead and optional Team Members to each selected facility.
10. Manager publishes the round only after each facility has a Team Lead.
11. Team Lead and Team Members open only assigned workspaces.
12. Backend pulls DHIS2 values using:
   - facility DHIS2 org unit UID
   - assessment reporting period
   - manager-selected data element UIDs or operands
13. Team members capture register and HMIS 105 values.
14. Only the Team Lead, or a Team Member explicitly granted `can_submit`, submits final assessment data.
15. Assessors can continue on cached packages offline and sync later.
16. Managers and reviewers run comparison, analytics, and corrective action workflows.
17. Managers and reviewers generate structured reports, review them, approve them, and export them.

## Core Product Principles

### Three-Source DQA Principle

Each comparison row is grounded in:

- `register_value`
- `hmis105_value`
- `dhis2_value_at_assessment`

`dhis2_value_at_assessment` is the authoritative DHIS2 value for the DQA comparison engine. `dhis2_value_latest` is only a later review reference.

### Manager-Selected Indicator Principle

- Assessors do not choose which indicators appear.
- Managers choose the indicators per round.
- The selected list is persisted and later reused by online and offline assessor workspaces, comparison, analytics, and reports.

### Facility Registry Principle

- Assessment facilities come from the local facility registry after manager import from DHIS2.
- Managers can search DHIS2 organisation units by name, code, UID, or parent/district context through the backend.
- Managers must explicitly sign into DHIS2 in Settings before live DHIS2 calls are available.
- Imported facilities store DHIS2 org unit UID, code, path, parent name, level, and facility metadata for later API pulls.
- Manual facility creation is supported as a fallback only and is not the primary workflow.

### Live DHIS2 Indicator Import Principle

- Managers can search DHIS2 data elements by HMIS code, UID, short name, or full name through the backend.
- DHIS2 credentials are not hard-coded in source code or stored in the browser.
- The active DHIS2 password is kept server-side only in backend process memory and is cleared on DHIS2 logout or backend restart.
- Imported indicators store the DHIS2 UID or operand, data element UID, optional category option combo UID, dataset, category combo, value type, and aggregation type.
- Confirmed UCMB seed mappings remain supported and can be loaded into PostgreSQL idempotently.
- The frontend never calls DHIS2 directly.
- Existing operands remain supported; a richer live category option combo picker is a documented future refinement where exact category option combo selection is needed.

### Assessment Team Principle

- Broad user role remains `ASSESSOR`.
- Assessment-level team roles are `TEAM_LEAD` and `TEAM_MEMBER`.
- A user can be Team Lead for one facility assessment and Team Member for another.
- Team Lead and Team Members can enter data when `can_enter_data=true`.
- Final submission requires Team Lead or explicit `can_submit=true`.
- Existing `assigned_assessor_id` remains as a backward-compatible lead field, but `assessment_facility_team_members` is the main assignment model going forward.

### Low-Network Field Use Principle

- A workspace must first be opened online while authenticated.
- After that, the package can be cached for offline use on that device.
- Drafts save to IndexedDB.
- Sync is manual and visible.
- Token expiry never deletes drafts.
- Relogin is required before sync if the token is no longer valid.

## Prompt Status

### Prompt 1

Implemented. Foundation, docs, backend shell, frontend shell, PostgreSQL setup, and UI style guide.

### Prompt 2

Implemented. Authentication, roles, facility registry, indicator library, audit log foundation.

### Prompt 3

Implemented. Assessment rounds, manager-selected indicators, facility selection, assessor assignment, round publish/close flow.

### Prompt 4A

Implemented and verified. Online assessor workspace, DHIS2 auto-population, source document checks, final submit, reviewer read-only view.

### Prompt 4B

Implemented and verified. IndexedDB cached packages, local draft autosave, pending sync queue, manual sync, relogin-required state, idempotent sync.

### Prompt 5

Implemented and verified. Comparison engine, discrepancy classification, severity handling, scoring, analytics, heatmap, corrective actions.

### Prompt 6

Implemented and verified. AI-safe reporting, template fallback reporting, review and approval workflow, DOCX/PDF/XLSX exports, final dashboard polish, settings page, and deployment guidance.

### Master Correction Pass

Implemented and verified. Added live backend-mediated DHIS2 connection testing, facility search/import, data element search/import, assessment-level Team Lead and Team Member assignment, team-aware workspace permissions, and stricter publish validation requiring a Team Lead per selected facility.

### Final Workflow Refinement Pass

Implemented and verified. Cleaned user-facing build-stage language from the frontend, simplified role-based navigation for assessment teams, redesigned the field workspace around the three core values, replaced separate technical sync actions with `Sync with DHIS2`, added `Send to Manager`, added a general facility assessment comment, and made the manager dashboard assessment-centered.

## Current Backend Capabilities

- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`
- `POST /api/dhis2/session/login`
- `POST /api/dhis2/session/logout`
- `GET /api/dhis2/connection-status`
- `GET /api/dhis2/facilities/search`
- `GET /api/dhis2/data-elements/search`
- user, facility, and indicator management APIs
- DHIS2 facility and data element import APIs
- assessment round APIs
- assessment facility team APIs
- assessor workspace and sync APIs
- general facility assessment comment API
- comparison APIs
- analytics APIs
- corrective action APIs
- reporting and export APIs
- safe system-info API for frontend settings

## Comparison and Scoring Rules

- Null is never treated as zero.
- Missing register, HMIS 105, or DHIS2 values are classified explicitly.
- Zero-safe logic avoids divide-by-zero errors.
- Death and high-risk indicators use stricter severity handling.
- Custom round thresholds override indicator defaults when configured.
- Score weights are stored in `assessment_rounds.scoring_settings_json`.

## AI Reporting Safety Rules

- AI never changes DQA values.
- AI never updates DHIS2.
- AI never creates official corrections.
- AI receives structured findings only.
- Comments are excluded by default.
- Comments are included only if `include_comments=true`.
- All AI generation attempts are logged.
- Reports are generated as draft/generated artifacts and still require review and approval.
- If `AI_API_KEY` is missing, the backend uses deterministic template fallback reporting.

## Report and Export Workflow

Supported report types:

- `FACILITY_DQA_REPORT`
- `CONSOLIDATED_UCMB_DQA_REPORT`
- `CORRECTIVE_ACTION_REPORT`
- `EXECUTIVE_SUMMARY`

Supported export types:

- DOCX
- PDF
- XLSX

Workflow:

1. Generate report
2. Review report
3. Approve report
4. Export report
5. Archive report if needed

## Corrective Action Rule

- `RESOLVED` means someone reports the action as completed.
- `VERIFIED` means a reviewer or manager confirms the correction through evidence or follow-up.
- `CLOSED` is the managerial closure state.

## What Not To Overbuild

- no microservices
- no Kubernetes
- no distributed workflow engine
- no automatic DHIS2 correction
- no AI-driven data modification
- no service-worker-heavy offline platform
- no SQLite fallback
- no fake completeness for unfinished behavior

## Confirmed HMIS 105 Mapping Source

The confirmed UCMB indicator and operand mapping list remains the source of truth in:

- `docs/DHIS2_MAPPING_SEED.md`
- `backend/app/seed/indicator_seed.py`

## Final V1 State

The codebase now represents a complete V1 UCMB HMIS 105 DQA platform that is:

- lightweight
- PostgreSQL-only
- backend-first and secure
- field-friendly in unstable networks
- manager-controlled in planning
- assessor-friendly in execution
- reviewer-friendly in verification
- ready for formal reporting and exports
