import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SourceDocumentAnalyticsItem } from "../../types";

export function SourceDocumentChart({ items }: { items: SourceDocumentAnalyticsItem[] }) {
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={items}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5EDF5" />
          <XAxis dataKey="source_document_name" stroke="#64748B" angle={-18} textAnchor="end" height={80} interval={0} />
          <YAxis stroke="#64748B" />
          <Tooltip />
          <Bar dataKey="availability_rate" fill="#00A6A6" radius={[8, 8, 0, 0]} />
          <Bar dataKey="completeness_rate" fill="#102A43" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
