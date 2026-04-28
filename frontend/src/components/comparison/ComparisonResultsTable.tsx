import type { ColumnDef } from "@tanstack/react-table";
import { Badge } from "../ui/Badge";
import { Table } from "../ui/Table";
import type { ComparisonRow } from "../../types";

function toneForSeverity(severity: string | null): "neutral" | "success" | "warning" | "danger" | "info" {
  if (severity === "EXACT") return "success";
  if (severity === "MINOR") return "info";
  if (severity === "MODERATE") return "warning";
  if (severity === "MAJOR" || severity === "CRITICAL" || severity === "MISSING") return "danger";
  return "neutral";
}

const columns: ColumnDef<ComparisonRow>[] = [
  { accessorKey: "indicator_name", header: "Indicator" },
  { accessorKey: "hmis_code", header: "HMIS Code" },
  { accessorKey: "register_value", header: "Register" },
  { accessorKey: "hmis105_value", header: "HMIS 105" },
  { accessorKey: "dhis2_value_at_assessment", header: "DHIS2" },
  { accessorKey: "register_vs_hmis_difference", header: "Reg vs HMIS" },
  { accessorKey: "hmis_vs_dhis2_difference", header: "HMIS vs DHIS2" },
  { accessorKey: "register_vs_dhis2_difference", header: "Reg vs DHIS2" },
  {
    accessorKey: "discrepancy_percent",
    header: "Discrepancy %",
    cell: ({ row }) => (row.original.discrepancy_percent === null ? "-" : `${row.original.discrepancy_percent.toFixed(2)}%`),
  },
  { accessorKey: "issue_type", header: "Issue Type", cell: ({ row }) => <Badge tone="info">{row.original.issue_type ?? "N/A"}</Badge> },
  {
    accessorKey: "severity",
    header: "Severity",
    cell: ({ row }) => <Badge tone={toneForSeverity(row.original.severity)}>{row.original.severity ?? "N/A"}</Badge>,
  },
  { accessorKey: "comparison_notes", header: "Notes" },
];

export function ComparisonResultsTable({ rows }: { rows: ComparisonRow[] }) {
  return <Table data={rows} columns={columns} emptyMessage="No comparison rows are available yet." />;
}
