import type { ColumnDef } from "@tanstack/react-table";
import { Table } from "../ui/Table";
import type { IndicatorAnalyticsItem } from "../../types";

const columns: ColumnDef<IndicatorAnalyticsItem>[] = [
  { accessorKey: "indicator_name", header: "Indicator" },
  { accessorKey: "hmis_code", header: "HMIS Code" },
  { accessorKey: "exact_match_rate", header: "Exact Match", cell: ({ row }) => `${row.original.exact_match_rate.toFixed(1)}%` },
  { accessorKey: "average_discrepancy_percent", header: "Avg % Diff", cell: ({ row }) => row.original.average_discrepancy_percent === null ? "-" : `${row.original.average_discrepancy_percent.toFixed(1)}%` },
  { accessorKey: "major_discrepancy_count", header: "Major" },
  { accessorKey: "critical_discrepancy_count", header: "Critical" },
  { accessorKey: "common_issue_type", header: "Common Issue" },
];

export function IndicatorIssueTable({ items }: { items: IndicatorAnalyticsItem[] }) {
  return <Table data={items} columns={columns} emptyMessage="No indicator analytics available yet." />;
}
