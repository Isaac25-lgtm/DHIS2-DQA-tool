import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { cn } from "../../lib/cn";

interface TableProps<TData> {
  data: TData[];
  columns: ColumnDef<TData>[];
  emptyMessage?: string;
  className?: string;
}

export function Table<TData>({
  data,
  columns,
  emptyMessage = "No records available.",
  className,
}: TableProps<TData>) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className={cn("overflow-hidden rounded-[18px] border border-brand-border bg-white shadow-sm", className)}>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-brand-border/70">
          <thead className="bg-brand-blue">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-white/80"
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-brand-border/70">
            {table.getRowModel().rows.length > 0 ? (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="transition hover:bg-brand-surface/80">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3 text-sm text-brand-text">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td
                  className="px-4 py-8 text-center text-sm text-brand-muted"
                  colSpan={columns.length}
                >
                  {emptyMessage}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
