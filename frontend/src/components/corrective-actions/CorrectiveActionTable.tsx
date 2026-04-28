import type { ColumnDef } from "@tanstack/react-table";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Table } from "../ui/Table";
import type { CorrectiveAction, CorrectiveActionStatus } from "../../types";

const toneForStatus = (status: CorrectiveActionStatus): "neutral" | "success" | "warning" | "danger" | "info" => {
  if (status === "VERIFIED" || status === "CLOSED") return "success";
  if (status === "OPEN" || status === "IN_PROGRESS") return "warning";
  if (status === "OVERDUE" || status === "CANCELLED") return "danger";
  return "info";
};

export function CorrectiveActionTable({
  items,
  onResolve,
  onVerify,
  onClose,
}: {
  items: CorrectiveAction[];
  onResolve?: (action: CorrectiveAction) => void;
  onVerify?: (action: CorrectiveAction) => void;
  onClose?: (action: CorrectiveAction) => void;
}) {
  const columns: ColumnDef<CorrectiveAction>[] = [
    { accessorKey: "action_description", header: "Action" },
    { accessorKey: "facility_name", header: "Facility" },
    { accessorKey: "indicator_name", header: "Indicator" },
    { accessorKey: "issue_type", header: "Issue Type" },
    { accessorKey: "severity", header: "Severity", cell: ({ row }) => <Badge tone="danger">{row.original.severity}</Badge> },
    { accessorKey: "responsible_person", header: "Responsible" },
    { accessorKey: "deadline", header: "Deadline" },
    { accessorKey: "status", header: "Status", cell: ({ row }) => <Badge tone={toneForStatus(row.original.status)}>{row.original.status}</Badge> },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-2">
          {onResolve ? <Button variant="secondary" className="px-3 py-2 text-xs" onClick={() => onResolve(row.original)}>Resolve</Button> : null}
          {onVerify ? <Button variant="secondary" className="px-3 py-2 text-xs" onClick={() => onVerify(row.original)}>Verify</Button> : null}
          {onClose ? <Button variant="secondary" className="px-3 py-2 text-xs" onClick={() => onClose(row.original)}>Close</Button> : null}
        </div>
      ),
    },
  ];

  return <Table data={items} columns={columns} emptyMessage="No corrective actions have been recorded yet." />;
}
