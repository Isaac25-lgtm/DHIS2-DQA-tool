export type UserRole = "MANAGER" | "ASSESSOR" | "REVIEWER" | "VIEWER";
export type PeriodType = "MONTHLY" | "QUARTERLY" | "ANNUAL" | "CUSTOM";
export type AssessmentRoundStatus = "DRAFT" | "PUBLISHED" | "IN_PROGRESS" | "CLOSED" | "ARCHIVED";
export type AssessmentFacilityStatus =
  | "NOT_STARTED"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "DRAFT_SAVED"
  | "PENDING_SYNC"
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "RETURNED_FOR_CORRECTION"
  | "APPROVED"
  | "CLOSED";
export type WorkspaceMode = "EDIT" | "READ_ONLY";
export type ComparisonStatus = "NOT_COMPARED" | "COMPARED" | "NEEDS_REVIEW" | "COMPARISON_FAILED";
export type DqaIssueType =
  | "NO_ISSUE"
  | "REGISTER_TO_HMIS_SUMMARIZATION_ERROR"
  | "DHIS2_DATA_ENTRY_ERROR"
  | "MULTIPLE_STAGE_ERROR"
  | "SOURCE_DOCUMENT_ISSUE"
  | "HMIS105_REPORT_MISSING"
  | "DHIS2_VALUE_MISSING"
  | "VALUE_MISSING"
  | "REQUIRES_REVIEW"
  | "NOT_APPLICABLE";
export type SeverityLevel = "EXACT" | "MINOR" | "MODERATE" | "MAJOR" | "CRITICAL" | "MISSING" | "NOT_APPLICABLE";
export type CorrectiveActionStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "VERIFIED" | "CLOSED" | "OVERDUE" | "CANCELLED";
export type ReportStatus = "DRAFT" | "GENERATED" | "REVIEWED" | "APPROVED" | "EXPORTED" | "ARCHIVED";
export type ReportType =
  | "FACILITY_DQA_REPORT"
  | "CONSOLIDATED_UCMB_DQA_REPORT"
  | "CORRECTIVE_ACTION_REPORT"
  | "EXECUTIVE_SUMMARY";

export interface ApiMessage {
  message: string;
}

export interface AuthUser {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
}

export interface User extends AuthUser {
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ManagerNotification {
  id: string;
  action: string;
  title: string;
  message: string;
  entity_type: string;
  entity_id: string | null;
  description: string;
  actor_user_id: string | null;
  actor_name: string | null;
  created_at: string;
}

export interface UserFormPayload {
  full_name: string;
  email: string;
  password?: string;
  role: UserRole;
  is_active: boolean;
}

export interface Facility {
  id: string;
  facility_name: string;
  district: string;
  facility_type: string;
  ownership: string;
  dhis2_org_unit_uid: string | null;
  dhis2_code: string | null;
  dhis2_path: string | null;
  dhis2_parent_name: string | null;
  dhis2_level: number | null;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface FacilityFormPayload {
  facility_name: string;
  district: string;
  facility_type: string;
  ownership: string;
  dhis2_org_unit_uid: string | null;
  dhis2_code?: string | null;
  dhis2_path?: string | null;
  dhis2_parent_name?: string | null;
  dhis2_level?: number | null;
  notes: string | null;
  is_active: boolean;
}

export interface Indicator {
  id: string;
  indicator_name: string;
  indicator_group: string;
  hmis_code: string;
  dhis2_uid_or_operand: string | null;
  data_element_uid: string | null;
  category_option_combo_uid: string | null;
  dataset_name: string | null;
  hmis_section: string | null;
  source_register: string | null;
  category_combo: string | null;
  value_type: string;
  aggregation_type: string | null;
  is_active: boolean;
  is_required_by_default: boolean;
  default_discrepancy_threshold_percent: number;
  is_death_indicator: boolean;
  sort_order: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface IndicatorFormPayload {
  indicator_name: string;
  indicator_group: string;
  hmis_code: string;
  dhis2_uid_or_operand: string | null;
  dataset_name: string | null;
  hmis_section: string | null;
  source_register: string | null;
  category_combo: string | null;
  value_type: string;
  aggregation_type?: string | null;
  is_active: boolean;
  is_required_by_default: boolean;
  default_discrepancy_threshold_percent: number;
  is_death_indicator: boolean;
  sort_order: number;
  notes: string | null;
}

export interface IndicatorFilters {
  active?: boolean;
  group?: string;
  hmis_section?: string;
  search?: string;
}

export interface IndicatorSeedResponse {
  created: number;
  updated: number;
  skipped: number;
  message: string;
}

export interface SourceDocumentRequirement {
  id: string;
  name: string;
  description: string | null;
  is_required: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface SourceDocumentRequirementPayload {
  name: string;
  description: string | null;
  is_required: boolean;
  display_order: number;
}

export interface SelectedIndicator {
  id: string;
  indicator_id: string;
  display_order: number;
  is_required: boolean;
  custom_threshold_percent: number | null;
  notes: string | null;
  indicator_name: string;
  indicator_group: string;
  hmis_code: string;
  dhis2_uid_or_operand: string | null;
  source_register: string | null;
  dataset_name: string | null;
  hmis_section: string | null;
  category_combo: string | null;
  value_type: string;
  is_death_indicator: boolean;
  created_at: string;
  updated_at: string;
}

export interface SelectedIndicatorPayload {
  indicator_id: string;
  display_order?: number;
  is_required: boolean;
  custom_threshold_percent: number | null;
  notes: string | null;
}

export interface AssessmentFacilityAssignment {
  id: string;
  assessment_round_id: string;
  facility_id: string;
  assigned_assessor_id: string | null;
  status: AssessmentFacilityStatus;
  started_at: string | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  reviewed_by_user_id: string | null;
  manager_comment: string | null;
  general_assessment_comment: string | null;
  created_at: string;
  updated_at: string;
  facility: Facility;
  assigned_assessor: AuthUser | null;
  team_members: AssessmentTeamMember[];
}

export interface AssessmentRound {
  id: string;
  assessment_code: string;
  name: string;
  description: string | null;
  reporting_period: string;
  period_type: PeriodType;
  start_date: string | null;
  end_date: string | null;
  deadline: string | null;
  status: AssessmentRoundStatus;
  created_by_user_id: string;
  published_at: string | null;
  closed_at: string | null;
  notes: string | null;
  scoring_settings_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  indicator_count: number;
  facility_count: number;
  assigned_facility_count: number;
  completion_percent: number;
  selected_indicators: SelectedIndicator[];
  selected_facilities: AssessmentFacilityAssignment[];
  source_document_requirements: SourceDocumentRequirement[];
}

export interface AssessmentRoundPackageSummary {
  id: string;
  assessment_code: string;
  name: string;
  description: string | null;
  reporting_period: string;
  period_type: PeriodType;
  start_date: string | null;
  end_date: string | null;
  deadline: string | null;
  status: AssessmentRoundStatus;
  published_at: string | null;
  notes: string | null;
  scoring_settings_json: Record<string, unknown> | null;
}

export interface AssessmentRoundListItem {
  id: string;
  assessment_code: string;
  name: string;
  description: string | null;
  reporting_period: string;
  period_type: PeriodType;
  start_date: string | null;
  end_date: string | null;
  deadline: string | null;
  status: AssessmentRoundStatus;
  facility_count: number;
  indicator_count: number;
  assigned_facility_count: number;
  completion_percent: number;
  created_at: string;
  updated_at: string;
}

export interface AssessmentRoundPayload {
  template_round_id?: string | null;
  name: string;
  description: string | null;
  reporting_period: string;
  period_type: PeriodType;
  start_date: string | null;
  end_date: string | null;
  deadline: string | null;
  notes: string | null;
  scoring_settings_json?: Record<string, unknown> | null;
  source_document_requirements?: SourceDocumentRequirementPayload[];
}

export interface AssessmentRoundProgress {
  assessment_round_id: string;
  total_facilities: number;
  assigned_facilities: number;
  submitted_facilities: number;
  approved_facilities: number;
  pending_facilities: number;
  by_status: Record<string, number>;
}

export interface AssessmentRoundPackage {
  assessment_round: AssessmentRoundPackageSummary;
  facility: Facility;
  assigned_assessor: AuthUser | null;
  selected_indicators: SelectedIndicator[];
  source_document_requirements: SourceDocumentRequirement[];
  values: DqaValue[];
  status: AssessmentFacilityStatus;
  deadline: string | null;
  offline_cache_version: string;
}

export interface Dhis2Value {
  indicator_id: string;
  dhis2_uid_or_operand: string | null;
  value: number | null;
  status: string;
  error: string | null;
  extracted_at: string | null;
}

export interface DqaValue {
  id: string;
  indicator_id: string;
  register_value: number | null;
  hmis105_value: number | null;
  dhis2_value_at_assessment: number | null;
  dhis2_extracted_at: string | null;
  dhis2_api_status: string | null;
  dhis2_error_message: string | null;
  dhis2_value_latest: number | null;
  dhis2_latest_extracted_at: string | null;
  dhis2_latest_api_status: string | null;
  dhis2_latest_error_message: string | null;
  assessor_comment: string | null;
  manager_comment: string | null;
  register_vs_hmis_difference: number | null;
  hmis_vs_dhis2_difference: number | null;
  register_vs_dhis2_difference: number | null;
  absolute_discrepancy: number | null;
  discrepancy_percent: number | null;
  verification_factor: number | null;
  issue_type: DqaIssueType | null;
  severity: SeverityLevel | null;
  comparison_status: ComparisonStatus | null;
  comparison_notes: string | null;
  compared_at: string | null;
  compared_by_user_id: string | null;
  value_status:
    | "NOT_STARTED"
    | "DRAFT"
    | "SAVED"
    | "SUBMITTED"
    | "REVIEWED"
    | "RETURNED_FOR_CORRECTION";
  created_at: string;
  updated_at: string;
}

export interface AssessmentComment {
  id: string;
  assessment_facility_id: string;
  indicator_id: string | null;
  author_user_id: string | null;
  author_name: string | null;
  comment_type: "GENERAL" | "INDICATOR" | string;
  comment_text: string;
  created_at: string;
  updated_at: string;
}

export interface DqaValueInput {
  indicator_id: string;
  register_value: number | null;
  hmis105_value: number | null;
  assessor_comment: string | null;
  local_client_id?: string | null;
}

export interface SourceDocumentCheck {
  id: string;
  assessment_facility_id: string;
  source_document_name: string;
  available: boolean | null;
  complete: boolean | null;
  legible: boolean | null;
  missing_pages: boolean | null;
  comment: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourceDocumentCheckInput {
  source_document_name: string;
  available: boolean | null;
  complete: boolean | null;
  legible: boolean | null;
  missing_pages: boolean | null;
  comment: string | null;
}

export interface AssessmentWorkspace {
  assessment_facility: AssessmentFacilityAssignment;
  assessment_round: AssessmentRoundPackageSummary;
  facility: Facility;
  selected_indicators: SelectedIndicator[];
  values: DqaValue[];
  comments: AssessmentComment[];
  source_document_checks: SourceDocumentCheck[];
  source_document_requirements: SourceDocumentRequirement[];
  workspace_mode: WorkspaceMode;
  offline_cache_version: string;
  dhis2_pull_message: string | null;
}

export interface FacilityScore {
  score_percent: number;
  score_category: string;
  earned_points: number;
  possible_points: number;
  exact_count: number;
  minor_count: number;
  moderate_count: number;
  major_count: number;
  critical_count: number;
  missing_count: number;
  not_applicable_count: number;
}

export interface ComparisonRow extends DqaValue {
  assessment_facility_id: string;
  indicator_name: string;
  hmis_code: string;
  custom_threshold_percent: number | null;
  is_death_indicator: boolean;
}

export interface AssessmentComparisonResults {
  facility: Facility;
  assessment_round: AssessmentRoundPackageSummary;
  assessment_facility_id: string;
  assessment_status: string;
  dqa_score: FacilityScore;
  comparison_rows: ComparisonRow[];
  source_document_summary: Record<string, number>;
  issue_counts: Record<string, number>;
  severity_counts: Record<string, number>;
}

export interface ComparisonRunResponse {
  assessment_facility_id: string;
  compared_rows: number;
  issue_counts: Record<string, number>;
  severity_counts: Record<string, number>;
  dqa_score: FacilityScore;
  compared_at: string;
}

export interface AssessmentRoundComparisonSummary {
  assessment_round_id: string;
  facilities_compared: number;
  issue_counts: Record<string, number>;
  severity_counts: Record<string, number>;
  average_score_percent: number;
  facility_scores: Array<{
    assessment_facility_id: string;
    facility_name: string;
    score_percent: number;
    score_category: string;
  }>;
}

export interface AnalyticsSummary {
  facilities_assessed: number;
  facilities_pending: number;
  indicators_assessed: number;
  exact_match_rate: number;
  major_discrepancy_rate: number;
  critical_discrepancy_count: number;
  register_to_hmis_error_count: number;
  dhis2_entry_error_count: number;
  multiple_stage_error_count: number;
  missing_value_count: number;
  source_document_completeness_rate: number;
  open_corrective_actions: number;
  overdue_corrective_actions: number;
}

export interface SubmissionStats {
  total_facilities: number;
  submitted_facilities: number;
  pending_facilities: number;
  in_progress_facilities: number;
  not_started_facilities: number;
  completion_percent: number;
  remaining_percent: number;
  total_submitted_rows: number;
  exact_count: number;
  within_threshold_count: number;
  flagged_count: number;
  critical_count: number;
  missing_count: number;
  average_score_percent: number;
}

export interface SubmissionListItem {
  assessment_facility_id: string;
  assessment_round_id: string;
  assessment_round_name: string;
  reporting_period: string;
  facility_id: string;
  facility_name: string;
  district: string;
  status: AssessmentFacilityStatus;
  team_lead_user_id: string | null;
  team_lead: string | null;
  team_members: string[];
  submitted_at: string | null;
  last_synced_at: string | null;
  completed_indicators: number;
  total_indicators: number;
  flagged_rows: number;
  critical_rows: number;
  dqa_score: number;
  score_category: string;
  general_assessment_comment: string | null;
}

export interface SubmissionValueRow {
  dqa_value_id: string | null;
  indicator_id: string;
  indicator_name: string;
  hmis_code: string;
  source_register: string | null;
  register_value: number | null;
  hmis105_value: number | null;
  dhis2_value_at_assessment: number | null;
  register_vs_hmis_difference: number | null;
  hmis_vs_dhis2_difference: number | null;
  register_vs_dhis2_difference: number | null;
  register_hmis_percent_diff: number | null;
  hmis_dhis2_percent_diff: number | null;
  register_dhis2_percent_diff: number | null;
  max_percent_diff: number | null;
  discrepancy_percent: number | null;
  issue_type: string | null;
  severity: string | null;
  flag: string;
  comparison_notes: string | null;
  assessor_comment: string | null;
  manager_comment: string | null;
}

export interface SubmissionDetail {
  summary: SubmissionListItem;
  values: SubmissionValueRow[];
}

export interface SubmissionDashboard {
  stats: SubmissionStats;
  team_leads: Array<{ user_id: string; full_name: string }>;
  submissions: SubmissionListItem[];
}

export interface FacilityAnalyticsItem {
  assessment_facility_id: string;
  facility_id: string;
  facility_name: string;
  dqa_score: number;
  score_category: string;
  exact_count: number;
  minor_count: number;
  moderate_count: number;
  major_count: number;
  critical_count: number;
  missing_count: number;
  open_corrective_actions: number;
  status: string;
}

export interface IndicatorAnalyticsItem {
  indicator_id: string;
  indicator_name: string;
  hmis_code: string;
  facilities_assessed: number;
  exact_match_rate: number;
  average_discrepancy_percent: number | null;
  major_discrepancy_count: number;
  critical_discrepancy_count: number;
  common_issue_type: string | null;
  worst_facilities: string[];
}

export interface SourceDocumentAnalyticsItem {
  source_document_name: string;
  availability_rate: number;
  completeness_rate: number;
  legibility_rate: number;
}

export interface HeatmapCell {
  assessment_facility_id: string;
  facility_id: string;
  facility_name: string;
  indicator_id: string;
  indicator_name: string;
  hmis_code: string;
  dqa_value_id: string;
  register_value: number | null;
  hmis105_value: number | null;
  dhis2_value_at_assessment: number | null;
  severity: string | null;
  issue_type: string | null;
  color: "GREEN" | "YELLOW" | "ORANGE" | "RED" | "GRAY";
}

export interface AssessmentFacilityAnalyticsSummary {
  assessment_facility_id: string;
  facility_id: string;
  facility_name: string;
  score_percent: number;
  score_category: string;
  exact_count: number;
  minor_count: number;
  moderate_count: number;
  major_count: number;
  critical_count: number;
  missing_count: number;
  open_corrective_actions: number;
}

export interface CorrectiveAction {
  id: string;
  assessment_facility_id: string | null;
  dqa_value_id: string | null;
  indicator_id: string | null;
  facility_id: string | null;
  assessment_round_id: string | null;
  issue_type: DqaIssueType;
  severity: SeverityLevel;
  action_description: string;
  recommended_action: string | null;
  responsible_person: string | null;
  deadline: string | null;
  status: CorrectiveActionStatus;
  manager_comment: string | null;
  assessor_comment: string | null;
  resolution_comment: string | null;
  verification_comment: string | null;
  created_by_user_id: string | null;
  assigned_to_user_id: string | null;
  resolved_by_user_id: string | null;
  verified_by_user_id: string | null;
  closed_by_user_id: string | null;
  resolved_at: string | null;
  verified_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
  facility_name: string | null;
  indicator_name: string | null;
}

export interface CorrectiveActionPayload {
  assessment_facility_id?: string | null;
  dqa_value_id?: string | null;
  indicator_id?: string | null;
  facility_id?: string | null;
  assessment_round_id?: string | null;
  issue_type: DqaIssueType;
  severity: SeverityLevel;
  action_description: string;
  recommended_action?: string | null;
  responsible_person?: string | null;
  deadline?: string | null;
  manager_comment?: string | null;
  assessor_comment?: string | null;
  assigned_to_user_id?: string | null;
}

export interface CorrectiveActionSuggestionResponse {
  created: number;
  skipped: number;
  actions: CorrectiveAction[];
}

export interface ExportLog {
  id: string;
  report_id: string;
  export_type: "DOCX" | "PDF" | "XLSX";
  file_name: string;
  status: "SUCCESS" | "FAILED";
  error_message: string | null;
  exported_at: string;
  created_at: string;
  exported_by_user_id: string | null;
}

export interface Report {
  id: string;
  assessment_round_id: string | null;
  assessment_facility_id: string | null;
  facility_id: string | null;
  report_type: ReportType;
  title: string;
  status: ReportStatus;
  generated_content: string;
  edited_content: string | null;
  final_content: string | null;
  display_content: string;
  structured_input_json: Record<string, unknown>;
  prompt_version: string;
  ai_provider: string | null;
  ai_model: string | null;
  include_comments: boolean;
  generated_by_user_id: string | null;
  reviewed_by_user_id: string | null;
  approved_by_user_id: string | null;
  exported_by_user_id: string | null;
  generated_at: string | null;
  reviewed_at: string | null;
  approved_at: string | null;
  exported_at: string | null;
  created_at: string;
  updated_at: string;
  export_logs: ExportLog[];
}

export interface ReportGeneratePayload {
  assessment_round_id?: string | null;
  assessment_facility_id?: string | null;
  team_lead_user_id?: string | null;
  report_type: ReportType;
  include_comments: boolean;
}

export interface SystemInfo {
  app_name: string;
  app_version: string;
  environment: string;
  dhis2_base_url: string;
  ai_provider: string | null;
  ai_model: string | null;
  database_status: string;
}

export interface MyAssessmentListItem {
  id: string;
  assessment_round_id: string;
  round_name: string;
  facility_name: string;
  district: string;
  reporting_period: string;
  deadline: string | null;
  status: AssessmentFacilityStatus;
  sync_status?: "READY" | "CACHED";
  my_team_role?: "TEAM_LEAD" | "TEAM_MEMBER" | "LEGACY_LEAD" | null;
  can_submit?: boolean;
}

export interface AssessmentFacilitySelectionPayload {
  facility_ids: string[];
}

export interface AssessmentAssignmentPayload {
  assignments: {
    facility_id: string;
    assessor_id: string;
  }[];
}

export type AssessmentTeamRole = "TEAM_LEAD" | "TEAM_MEMBER";

export interface AssessmentTeamMember {
  id: string;
  assessment_facility_id: string;
  user_id: string;
  team_role: AssessmentTeamRole;
  can_enter_data: boolean;
  can_submit: boolean;
  is_active: boolean;
  assigned_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  user: AuthUser | null;
}

export interface AssessmentTeamMemberPayload {
  user_id: string;
  team_role: AssessmentTeamRole;
  can_enter_data: boolean;
  can_submit: boolean;
}

export interface AssessmentTeamAssignmentPayload {
  team_members: AssessmentTeamMemberPayload[];
}

export type Dhis2Reachability = "reachable" | "unreachable" | "not_configured";

export interface Dhis2ConnectionStatus {
  connected: boolean;
  base_url: string;
  last_checked_at: string;
  message: string;
  signed_in: boolean;
  reachability?: Dhis2Reachability;
}

export interface Dhis2LoginPayload {
  base_url?: string | null;
  username: string;
  password: string;
}

export interface Dhis2FacilitySearchResult {
  dhis2_org_unit_uid: string;
  dhis2_code: string | null;
  facility_name: string;
  district: string;
  facility_type: string;
  ownership: string | null;
  dhis2_path: string | null;
  dhis2_parent_name: string | null;
  dhis2_level: number | null;
  already_imported: boolean;
}

export interface Dhis2DataElementSearchResult {
  data_element_uid: string;
  dhis2_uid_or_operand: string;
  name: string;
  short_name: string | null;
  hmis_code: string | null;
  value_type: string | null;
  aggregation_type: string | null;
  category_combo: string | null;
  dataset_name: string | null;
  already_imported: boolean;
}

export interface AssessmentPublishPayload {
  allow_unassigned_facilities: boolean;
}

export interface CachedAssessmentPackage {
  assessment_facility_id: string;
  round_details: AssessmentRoundPackageSummary;
  facility_details: Facility;
  selected_indicators: SelectedIndicator[];
  source_document_requirements: SourceDocumentRequirement[];
  values: DqaValue[];
  status: AssessmentFacilityStatus;
  deadline: string | null;
  fetched_at: string;
  cache_version: string;
}

export interface CachedAssessmentWorkspace {
  assessment_facility_id: string;
  workspace: AssessmentWorkspace;
  assessment_status: AssessmentFacilityStatus;
  workspace_mode: WorkspaceMode;
  fetched_at: string;
  cache_version: string;
}

export type LocalDraftSyncStatus =
  | "LOCAL_DRAFT"
  | "DRAFT_SAVED_LOCALLY"
  | "PENDING_SYNC"
  | "SYNCING"
  | "SYNCED"
  | "SYNC_FAILED"
  | "RELOGIN_REQUIRED";

export interface DraftValueInput extends DqaValueInput {
  updated_at_client: string;
}

export interface DraftSourceDocumentCheckInput extends SourceDocumentCheckInput {
  updated_at_client: string;
}

export interface AssessmentDraft {
  assessment_facility_id: string;
  client_draft_id: string;
  client_batch_id: string;
  values: DraftValueInput[];
  source_document_checks: DraftSourceDocumentCheckInput[];
  general_assessment_comment: string | null;
  submit_final: boolean;
  sync_status: LocalDraftSyncStatus;
  last_saved_at: string;
  last_sync_attempt_at: string | null;
  last_synced_at: string | null;
  error_message: string | null;
}

export interface PendingSyncQueueItem {
  assessment_facility_id: string;
  client_draft_id: string;
  client_batch_id: string;
  submit_final: boolean;
  sync_status: LocalDraftSyncStatus;
  last_saved_at: string;
  last_sync_attempt_at: string | null;
  last_synced_at: string | null;
  error_message: string | null;
}

export interface SyncHistoryRecord {
  id: string;
  assessment_facility_id: string;
  client_batch_id: string;
  status: "SYNCED" | "FAILED" | "RELOGIN_REQUIRED";
  synced_at: string;
  message: string;
  items_received: number;
  items_saved: number;
}

export interface SyncAssessmentDraftPayload {
  assessment_facility_id: string;
  client_batch_id: string;
  client_saved_at: string;
  values: DraftValueInput[];
  source_document_checks: DraftSourceDocumentCheckInput[];
  general_assessment_comment: string | null;
  submit_final: boolean;
}

export interface SyncFailedItem {
  item_key: string;
  reason: string;
}

export interface SyncAssessmentDraftResponse {
  status: string;
  synced_at: string;
  items_received: number;
  items_saved: number;
  failed_items: SyncFailedItem[];
  assessment_status: AssessmentFacilityStatus;
  duplicate_batch: boolean;
  message?: string | null;
}

export interface SyncDraftResult {
  status: "SYNCED" | "FAILED" | "RELOGIN_REQUIRED" | "NO_PENDING_DRAFTS";
  syncedCount: number;
  failedCount: number;
  message: string;
  response?: SyncAssessmentDraftResponse;
}

export interface SaveValuesResponse {
  status: string;
  message: string;
  assessment_status: AssessmentFacilityStatus;
  values: DqaValue[];
}

export interface SaveSourceDocumentsResponse {
  status: string;
  message: string;
  assessment_status: AssessmentFacilityStatus;
  checks: SourceDocumentCheck[];
}

export interface SubmitAssessmentResponse {
  message: string;
  assessment_status: AssessmentFacilityStatus;
  submitted_at: string;
}

export interface DashboardStat {
  label: string;
  value: string;
  trend: string;
  description: string;
}

export interface RecentAssessment {
  facility: string;
  round: string;
  period: string;
  status: "Assigned" | "In Progress" | "Submitted";
  exactMatchRate: string;
}

export interface AssessmentRoundSummary {
  name: string;
  description: string;
  status: "Draft" | "Active";
  period: string;
  assessors: string;
  facilities: string;
  indicators: string;
}

export interface WorkspaceRow {
  id: string;
  indicator: string;
  hmisCode: string;
  registerValue: string;
  reportValue: string;
  dhis2Value: number | null;
  status: "Pending" | "Exact match" | "Review" | "Major discrepancy";
}
