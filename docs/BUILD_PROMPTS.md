# UCMB HMIS 105 DQA Platform - Build Prompts

This document records the delivery sequence used to build the V1 platform. Prompt 1 through Prompt 6 are now implemented in the current codebase.

## Master Correction Pass - DHIS2 Metadata Import and Field Team Workflow

Status: Implemented and verified.

Delivered:

- Manager DHIS2 sign-in/logout endpoints with backend-only active session handling
- Backend-only DHIS2 connection status endpoint
- Live DHIS2 facility search through FastAPI
- Idempotent DHIS2 facility import into PostgreSQL
- Live DHIS2 data element search through FastAPI
- Idempotent DHIS2 data element import into the indicator library
- Confirmed HMIS 105 seed workflow verification
- Assessment-level Team Lead and Team Member model
- Team-aware My Assessments, workspace access, data entry, and submit permissions
- Assessment round builder field-team assignment step
- Publish validation requiring a Team Lead for each selected facility
- Manager DHIS2 connection status display in Settings

## Final Workflow Refinement Pass - Field UX, Sync, and Dashboard Cleanup

Status: Implemented and verified.

Delivered:

- Removed internal build-stage wording from user-facing frontend screens
- Simplified assessor navigation to Dashboard, My Assessments, and Settings
- Redesigned the assessment workspace as a single clean field workflow
- Removed the technical DHIS2 side panel from the workspace
- Added compact percentage-difference and flag display in the main values table
- Added one general facility assessment comment at assignment level
- Replaced separate technical actions with `Sync with DHIS2`
- Added `Send to Manager` as the field-team final submission language
- Added an assessment selector and focused progress summary to the manager dashboard
- Added migration and tests for persisted general facility comments

## Prompt 1 - Foundation, Documentation, Backend Skeleton, Frontend Skeleton

Status: Implemented.

Delivered:

- Monorepo structure and project documentation
- PostgreSQL-only backend foundation
- FastAPI app shell, SQLAlchemy setup, and Alembic scaffolding
- React + TypeScript + Vite + Tailwind frontend shell
- Premium UI foundations and navigation shell
- Confirmed HMIS 105 indicator mapping seed context

## Prompt 2 - Authentication, Roles, Facilities, Indicator Library

Status: Implemented.

Delivered:

- JWT authentication and current-user endpoint
- Role-aware access control for manager, assessor, reviewer, and viewer
- User CRUD for managers
- Facility registry with DHIS2 org unit UID support
- Indicator library CRUD with simple UID and operand parsing
- Confirmed UCMB indicator seed endpoint
- Audit log foundation

## Prompt 3 - Assessment Round Builder and Manager-Selected Data Elements

Status: Implemented.

Delivered:

- Assessment round data model and APIs
- Round indicator selection and ordering
- Facility selection from the local registry
- Assessor assignment to selected facilities
- Publish, close, archive, and progress tracking
- Assessor package preparation for later workspace/offline use

## Prompt 4A - Online Assessor Workspace and DHIS2 Auto-Population

Status: Implemented and verified.

Delivered:

- Online assessment workspace for assigned facilities only
- DHIS2 field-time pull through the backend using stored UIDs and operands
- Register and HMIS 105 online data entry
- Source document checklist
- Final submit workflow
- Manager and reviewer read-only workspace view

## Prompt 4B - Offline Draft Entry and Sync

Status: Implemented and verified.

Delivered:

- IndexedDB package caching
- IndexedDB local draft autosave
- Pending sync queue and sync history
- Manual sync flow
- Relogin-required handling when token expiry blocks sync
- Idempotent sync batches and safe server upserts
- Lightweight conflict handling for locally edited assessor fields

## Prompt 5 - DQA Comparison Engine, Analytics, and Corrective Actions

Status: Implemented and verified.

Delivered:

- Three-source comparison engine using register, HMIS 105, and `dhis2_value_at_assessment`
- Null-safe and zero-safe discrepancy calculations
- Severity and issue classification rules
- High-risk and death-indicator stricter handling
- Facility scoring and score categories
- Round, facility, indicator, source document, and heatmap analytics
- Corrective action tracking with verification and closure workflow

## Prompt 6 - Reporting, Exports, Final Polish, and Deployment Guidance

Status: Implemented and verified.

Delivered:

- AI-safe report generation with template fallback
- Structured facility, consolidated, corrective-action, and executive-summary reports
- Review, approval, archive, and export workflow
- DOCX, PDF, and XLSX exports
- Final dashboard, settings, and report UX polish
- System info endpoint and safe configuration display
- Deployment guide for Render, Railway, VPS, and institutional server hosting
- Prompt 6 report/export backend tests and final frontend build verification

## V1 Status

All six build prompts are complete in the current codebase.

The V1 platform now supports:

- authentication and role-aware access
- facility and indicator management
- assessment round planning
- online and offline assessor workflow
- DHIS2 auto-population
- comparison, scoring, analytics, and heatmaps
- corrective action management
- AI-assisted but manager-reviewed reporting
- DOCX, PDF, and XLSX exports

Future work after V1 should focus on operational refinements, not new foundational architecture:

- stronger reviewer workflow refinements
- deeper conflict-resolution UX for offline drafts
- richer validation and production observability
- institutional deployment hardening and user onboarding support
