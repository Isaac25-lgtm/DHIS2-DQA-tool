import type { ColumnDef } from "@tanstack/react-table";
import { Badge } from "../ui/Badge";
import { Table } from "../ui/Table";
import type { FacilityAnalyticsItem } from "../../types";

const columns: ColumnDef<FacilityAnalyticsItem>[] = [
  { accessorKey: "facility_name", header: "Facility" },
  { accessorKey: "dqa_score", header: "DQA Score", cell: ({ row }) => `${row.original.dqa_score.toFixed(1)}%` },
  {
    accessorKey: "score_category",
    header: "Category",
    cell: ({ row }) => <Badge tone={row.original.score_category === "EXCELLENT" ? "success" : row.original.score_category === "POOR" ? "danger" : "warning"}>{row.original.score_category}</Badge>,
  },
  { accessorKey: "major_count", header: "Major" },
  { accessorKey: "critical_count", header: "Critical" },
  { accessorKey: "open_corrective_actions", header: "Open Actions" },
];

export function FacilityScoreTable({ items }: { items: FacilityAnalyticsItem[] }) {
  return <Table data={items} columns={columns} emptyMessage="No facility scores available yet." />;
}
