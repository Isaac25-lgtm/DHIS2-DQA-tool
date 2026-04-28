import { Card } from "../ui/Card";

export function ReportPreview({ title, content }: { title: string; content: string }) {
  return (
    <Card title={title} subtitle="Preview the current report content before review or export.">
      <div className="max-h-[36rem] overflow-y-auto rounded-2xl border border-brand-border bg-white p-5">
        <pre className="whitespace-pre-wrap font-sans text-sm leading-7 text-brand-text">{content}</pre>
      </div>
    </Card>
  );
}
