import type { AssessmentRoundSummary, DashboardStat, RecentAssessment, WorkspaceRow } from "../types";

export const dashboardStats: DashboardStat[] = [
  {
    label: "Facilities assessed",
    value: "12",
    trend: "+2 this month",
    description: "Facilities already opened in the current assessment cycle.",
  },
  {
    label: "Pending assessments",
    value: "04",
    trend: "3 due this week",
    description: "Assigned facilities still awaiting final assessor submission.",
  },
  {
    label: "Exact match rate",
    value: "86%",
    trend: "+5.4% improvement",
    description: "Share of rows where register, report, and DHIS2 values align.",
  },
  {
    label: "Major discrepancies",
    value: "09",
    trend: "Requires review",
    description: "Rows with clear variance across the three data sources.",
  },
];

export const performanceTrend = [
  { name: "Jan", exactMatchRate: 72, majorDiscrepancies: 14 },
  { name: "Feb", exactMatchRate: 75, majorDiscrepancies: 11 },
  { name: "Mar", exactMatchRate: 81, majorDiscrepancies: 8 },
  { name: "Apr", exactMatchRate: 86, majorDiscrepancies: 5 },
];

export const recentAssessments: RecentAssessment[] = [
  {
    facility: "Masaka HC IV",
    round: "Q2 Maternal & Newborn DQA",
    period: "2026-03",
    status: "In Progress",
    exactMatchRate: "82%",
  },
  {
    facility: "Mengo Hospital",
    round: "Q2 Maternal & Newborn DQA",
    period: "2026-03",
    status: "Submitted",
    exactMatchRate: "91%",
  },
  {
    facility: "Naggalama Hospital",
    round: "Q2 Maternal & Newborn DQA",
    period: "2026-03",
    status: "Assigned",
    exactMatchRate: "Pending",
  },
];

export const indicatorLibraryRows = [
  {
    name: "Total deliveries in the unit",
    hmisCode: "105-MA04",
    identifier: "idXOxt69W0e",
    identifierType: "data_element",
    dataset: "HMIS 105:02-03",
    status: "Confirmed",
  },
  {
    name: "Live births total",
    hmisCode: "105-MA05A1",
    identifier: "fEz9wGsA6YU",
    identifierType: "data_element",
    dataset: "HMIS 105:02-03",
    status: "Confirmed",
  },
  {
    name: "PNC attendance at 24 hours",
    hmisCode: "105-PN01",
    identifier: "RYcEItpNCUp.K01CbPXaICz",
    identifierType: "operand",
    dataset: "HMIS 105:02-03",
    status: "Confirmed",
  },
  {
    name: "PNC attendance at 6 weeks",
    hmisCode: "105-PN01",
    identifier: "RYcEItpNCUp.YftbycyVKYC",
    identifierType: "operand",
    dataset: "HMIS 105:02-03",
    status: "Confirmed",
  },
];

export const assessmentRounds: AssessmentRoundSummary[] = [
  {
    name: "Q2 Maternal & Newborn DQA",
    description: "Manager-selected maternity, ANC, and postnatal HMIS 105 indicators for March 2026.",
    status: "Active",
    period: "Mar 2026",
    assessors: "8 assessors",
    facilities: "12 facilities",
    indicators: "18 selected indicators",
  },
  {
    name: "ANC Quality Sweep",
    description: "Focused ANC indicator review round prepared for rollout.",
    status: "Draft",
    period: "Apr 2026",
    assessors: "Planned",
    facilities: "9 facilities",
    indicators: "12 selected indicators",
  },
];

export const workspaceRows: WorkspaceRow[] = [
  {
    id: "1",
    indicator: "Total deliveries in the unit",
    hmisCode: "105-MA04",
    registerValue: "124",
    reportValue: "124",
    dhis2Value: 124,
    status: "Exact match",
  },
  {
    id: "2",
    indicator: "Live births total",
    hmisCode: "105-MA05A1",
    registerValue: "118",
    reportValue: "116",
    dhis2Value: 116,
    status: "Review",
  },
  {
    id: "3",
    indicator: "Maternal deaths",
    hmisCode: "105-MA13",
    registerValue: "2",
    reportValue: "1",
    dhis2Value: 0,
    status: "Major discrepancy",
  },
  {
    id: "4",
    indicator: "PNC attendance at 24 hours",
    hmisCode: "105-PN01",
    registerValue: "",
    reportValue: "",
    dhis2Value: 93,
    status: "Pending",
  },
];
