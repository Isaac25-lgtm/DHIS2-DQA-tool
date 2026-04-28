# Data Model

This platform is PostgreSQL-only. All tables, constraints, indexes, and tests assume PostgreSQL.

## Design Rules

- UUID primary keys for core entities
- audit-friendly timestamps on operational records
- unique constraints to prevent duplicate selections and duplicate sync rows
- explicit enum-backed workflow states where they improve safety and readability
- browser offline drafts live in IndexedDB, not PostgreSQL

## Core Security and Identity Tables

### `users`

Purpose: authenticated users with role-based access.

Key fields:

- `id`
- `full_name`
- `email`
- `hashed_password`
- `role`
- `is_active`
- `last_login_at`
- `created_at`
- `updated_at`

Indexes and constraints:

- unique `email`
- index on `email`
- index on `role`

### `audit_logs`

Purpose: write-focused audit trail for important business events.

Key fields:

- `id`
- `actor_user_id`
- `action`
- `entity_type`
- `entity_id`
- `description`
- `ip_address`
- `user_agent`
- `created_at`

## Registry Tables

### `facilities`

Purpose: local registry of assessable facilities imported from DHIS2 or manually entered as a fallback.

Key fields:

- `id`
- `facility_name`
- `district`
- `facility_type`
- `ownership`
- `dhis2_org_unit_uid`
- `dhis2_code`
- `dhis2_path`
- `dhis2_parent_name`
- `dhis2_level`
- `is_active`
- `notes`
- `created_at`
- `updated_at`

Indexes and constraints:

- unique (`facility_name`, `district`)
- index on `dhis2_org_unit_uid`
- index on `dhis2_code`
- index on `is_active`

### `indicators`

Purpose: manager-controlled HMIS 105 indicator and data-element library.

Key fields:

- `id`
- `indicator_name`
- `indicator_group`
- `hmis_code`
- `dhis2_uid_or_operand`
- `data_element_uid`
- `category_option_combo_uid`
- `dataset_name`
- `hmis_section`
- `source_register`
- `category_combo`
- `value_type`
- `aggregation_type`
- `is_active`
- `is_required_by_default`
- `default_discrepancy_threshold_percent`
- `is_death_indicator`
- `sort_order`
- `notes`
- `created_at`
- `updated_at`

Indexes and constraints:

- unique `dhis2_uid_or_operand` when present
- index on `hmis_code`
- index on `dhis2_uid_or_operand`
- index on `indicator_group`
- index on `hmis_section`
- index on `is_active`

## Assessment Planning Tables

### `assessment_rounds`

Purpose: the manager-defined DQA planning unit.

Key fields:

- `id`
- `name`
- `description`
- `reporting_period`
- `period_type`
- `start_date`
- `end_date`
- `deadline`
- `status`
- `created_by_user_id`
- `published_at`
- `closed_at`
- `notes`
- `scoring_settings_json`
- `created_at`
- `updated_at`

Indexes:

- `status`
- `reporting_period`
- `created_by_user_id`

### `assessment_round_indicators`

Purpose: ordered indicator selection for a round.

Key fields:

- `id`
- `assessment_round_id`
- `indicator_id`
- `display_order`
- `is_required`
- `custom_threshold_percent`
- `notes`
- `created_at`
- `updated_at`

Indexes and constraints:

- unique (`assessment_round_id`, `indicator_id`)
- index on `assessment_round_id`

### `assessment_facilities`

Purpose: facility selection and workflow status inside a round. The newer team assignment table is the main model for field team access; `assigned_assessor_id` remains as a backward-compatible Team Lead reference.

Key fields:

- `id`
- `assessment_round_id`
- `facility_id`
- `assigned_assessor_id`
- `status`
- `started_at`
- `submitted_at`
- `reviewed_at`
- `reviewed_by_user_id`
- `manager_comment`
- `general_assessment_comment`
- `created_at`
- `updated_at`

Indexes and constraints:

- unique (`assessment_round_id`, `facility_id`)
- index on `status`
- index on `assigned_assessor_id`
- index on `assessment_round_id`

### `assessment_facility_team_members`

Purpose: assessment-level field team assignment for a selected facility.

Key fields:

- `id`
- `assessment_facility_id`
- `user_id`
- `team_role`
- `can_enter_data`
- `can_submit`
- `is_active`
- `assigned_by_user_id`
- `created_at`
- `updated_at`

Rules:

- `team_role` is `TEAM_LEAD` or `TEAM_MEMBER`.
- a facility assessment must have at least one active Team Lead before publishing.
- Team Lead defaults to `can_enter_data=true` and `can_submit=true`.
- Team Members can enter data when `can_enter_data=true`.
- Team Members cannot submit unless `can_submit=true`.

Indexes and constraints:

- unique (`assessment_facility_id`, `user_id`)
- index on `assessment_facility_id`
- index on `user_id`
- index on `team_role`
- index on `is_active`

### `source_document_requirements`

Purpose: round-level checklist definition for expected source documents.

Key fields:

- `id`
- `assessment_round_id`
- `name`
- `description`
- `is_required`
- `display_order`
- `created_at`
- `updated_at`

Indexes:

- `assessment_round_id`

## Assessment Execution Tables

### `dqa_values`

Purpose: one row per indicator per assigned assessment facility, storing all three source values plus comparison output.

Key fields:

- `id`
- `assessment_facility_id`
- `indicator_id`
- `register_value`
- `hmis105_value`
- `dhis2_value_at_assessment`
- `dhis2_extracted_at`
- `dhis2_api_status`
- `dhis2_error_message`
- `dhis2_value_latest`
- `dhis2_latest_extracted_at`
- `dhis2_latest_api_status`
- `dhis2_latest_error_message`
- `assessor_comment`
- `manager_comment`
- `value_status`
- comparison fields:
  - `register_vs_hmis_difference`
  - `hmis_vs_dhis2_difference`
  - `register_vs_dhis2_difference`
  - `absolute_discrepancy`
  - `discrepancy_percent`
  - `verification_factor`
  - `issue_type`
  - `severity`
  - `comparison_status`
  - `comparison_notes`
  - `compared_at`
  - `compared_by_user_id`
- `created_by_user_id`
- `updated_by_user_id`
- `created_at`
- `updated_at`

Indexes and constraints:

- unique (`assessment_facility_id`, `indicator_id`)
- index on `assessment_facility_id`
- index on `indicator_id`
- index on `value_status`
- index on `issue_type`
- index on `severity`
- index on `comparison_status`
- index on `compared_at`

Validation rules:

- source values remain nullable
- null is not zero
- source values must be `>= 0` if present

### `source_document_checks`

Purpose: saved checklist state for one assigned assessment facility.

Key fields:

- `id`
- `assessment_facility_id`
- `source_document_name`
- `available`
- `complete`
- `legible`
- `missing_pages`
- `comment`
- `created_by_user_id`
- `updated_by_user_id`
- `created_at`
- `updated_at`

Indexes and constraints:

- unique (`assessment_facility_id`, `source_document_name`)
- index on `assessment_facility_id`
- index on `source_document_name`

### `dhis2_extraction_logs`

Purpose: audit record of field-time and later review-time DHIS2 pulls.

Key fields:

- `id`
- `assessment_facility_id`
- `triggered_by_user_id`
- `extraction_type`
- `period`
- `facility_dhis2_org_unit_uid`
- `requested_dx`
- `status`
- `error_message`
- `extracted_at`
- `created_at`

Indexes:

- `assessment_facility_id`
- `status`
- `extracted_at`

### `sync_logs`

Purpose: idempotent record of offline draft sync batches.

Key fields:

- `id`
- `assessment_facility_id`
- `user_id`
- `client_batch_id`
- `status`
- `items_received`
- `items_saved`
- `failed_items_json`
- `error_message`
- `synced_at`
- `created_at`

Indexes and constraints:

- unique (`assessment_facility_id`, `user_id`, `client_batch_id`)
- index on `assessment_facility_id`
- index on `client_batch_id`
- index on `user_id`
- index on `status`
- index on `synced_at`

## Comparison and Follow-Up Tables

### `corrective_actions`

Purpose: structured follow-up for major, critical, missing, or review-worthy issues.

Key fields:

- `id`
- `assessment_facility_id`
- `dqa_value_id`
- `indicator_id`
- `facility_id`
- `assessment_round_id`
- `issue_type`
- `severity`
- `action_description`
- `recommended_action`
- `responsible_person`
- `deadline`
- `status`
- `manager_comment`
- `assessor_comment`
- `resolution_comment`
- `verification_comment`
- `created_by_user_id`
- `assigned_to_user_id`
- `resolved_by_user_id`
- `verified_by_user_id`
- `closed_by_user_id`
- `resolved_at`
- `verified_at`
- `closed_at`
- `created_at`
- `updated_at`

Indexes:

- `assessment_round_id`
- `assessment_facility_id`
- `facility_id`
- `indicator_id`
- `status`
- `severity`
- `deadline`
- `created_at`

## Reporting and Export Tables

### `reports`

Purpose: stored AI-assisted or template-based report drafts and approved narratives.

Key fields:

- `id`
- `assessment_round_id`
- `assessment_facility_id`
- `facility_id`
- `report_type`
- `title`
- `status`
- `generated_content`
- `edited_content`
- `final_content`
- `structured_input_json`
- `prompt_version`
- `ai_provider`
- `ai_model`
- `include_comments`
- `generated_by_user_id`
- `reviewed_by_user_id`
- `approved_by_user_id`
- `exported_by_user_id`
- `generated_at`
- `reviewed_at`
- `approved_at`
- `exported_at`
- `created_at`
- `updated_at`

Indexes:

- `assessment_round_id`
- `assessment_facility_id`
- `facility_id`
- `report_type`
- `status`
- `generated_at`

### `ai_generation_logs`

Purpose: auditable log of AI or template report generation attempts.

Key fields:

- `id`
- `report_id`
- `assessment_round_id`
- `assessment_facility_id`
- `generated_by_user_id`
- `prompt_version`
- `ai_provider`
- `ai_model`
- `input_payload_json`
- `output_text`
- `status`
- `error_message`
- `created_at`

Indexes:

- `report_id`
- `assessment_round_id`
- `assessment_facility_id`
- `status`
- `created_at`

### `export_logs`

Purpose: export audit trail for DOCX, PDF, and XLSX generation.

Key fields:

- `id`
- `report_id`
- `exported_by_user_id`
- `export_type`
- `file_name`
- `status`
- `error_message`
- `exported_at`
- `created_at`

Indexes:

- `report_id`
- `export_type`
- `status`
- `exported_at`

## Browser-Side Offline State

The following are intentionally browser-side only and do not live in PostgreSQL:

- cached assessment packages
- cached DHIS2 workspace responses
- local drafts
- pending sync queue
- sync history for a device/browser context

These are stored in IndexedDB so the platform remains lightweight and field-friendly without introducing server-side offline orchestration.
