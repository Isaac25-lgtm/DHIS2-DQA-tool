import type { ColumnDef } from "@tanstack/react-table";
import { Table } from "../ui/Table";
import { Button } from "../ui/Button";
import { ReportStatusBadge } from "./ReportStatusBadge";
import type { Report } from "../../types";

export function ReportListTable({
  reports,
  onOpen,
}: {
  reports: Report[];
  onOpen: (reportId: string) => void;
}) {
  const columns: ColumnDef<Report>[] = [
    { accessorKey: "title", header: "Title" },
    { accessorKey: "report_type", header: "Type" },
    { accessorKey: "status", header: "Status", cell: ({ row }) => <ReportStatusBadge status={row.original.status} /> },
    {
      accessorKey: "generated_at",
      header: "Generated",
      cell: ({ row }) => (row.original.generated_at ? new Date(row.original.generated_at).toLocaleString() : "-"),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <Button variant="secondary" onClick={() => onOpen(row.original.id)}>
          Open
        </Button>
      ),
    },
  ];
  return <Table data={reports} columns={columns} emptyMessage="No reports generated yet." />;
}
