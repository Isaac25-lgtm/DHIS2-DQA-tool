import { Card } from "../ui/Card";
import type { HeatmapCell } from "../../types";

const colorMap: Record<HeatmapCell["color"], string> = {
  GREEN: "bg-emerald-500",
  YELLOW: "bg-amber-400",
  ORANGE: "bg-orange-500",
  RED: "bg-red-500",
  GRAY: "bg-slate-300",
};

export function DqaHeatmap({ cells }: { cells: HeatmapCell[] }) {
  if (cells.length === 0) {
    return (
      <Card>
        <p className="text-sm text-brand-muted">No heatmap cells are available yet.</p>
      </Card>
    );
  }

  const facilities = Array.from(new Set(cells.map((cell) => cell.facility_name)));
  const indicators = Array.from(new Set(cells.map((cell) => `${cell.hmis_code}|${cell.indicator_name}`)));
  const cellMap = new Map(cells.map((cell) => [`${cell.facility_name}|${cell.hmis_code}|${cell.indicator_name}`, cell]));

  return (
    <div className="overflow-x-auto rounded-2xl border border-brand-border bg-white">
      <table className="min-w-full divide-y divide-slate-100 text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.18em] text-brand-muted">Facility</th>
            {indicators.map((indicator) => {
              const [code, name] = indicator.split("|");
              return (
                <th key={indicator} className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-[0.18em] text-brand-muted">
                  <span className="block">{code}</span>
                  <span className="normal-case tracking-normal text-[11px]">{name}</span>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {facilities.map((facility) => (
            <tr key={facility}>
              <td className="px-4 py-3 font-medium text-brand-text">{facility}</td>
              {indicators.map((indicator) => {
                const [code, name] = indicator.split("|");
                const cell = cellMap.get(`${facility}|${code}|${name}`);
                return (
                  <td key={`${facility}-${indicator}`} className="px-3 py-3">
                    <div
                      title={cell ? `${cell.severity ?? "N/A"} - ${cell.issue_type ?? "No issue"}` : "No data"}
                      className={`h-7 w-7 rounded-lg ${cell ? colorMap[cell.color] : "bg-slate-200"}`}
                    />
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
