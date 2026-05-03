import { Textarea } from "../ui/Textarea";
import type { SourceDocumentCheckInput, SourceDocumentRequirement } from "../../types";

function getCheckValue(checks: SourceDocumentCheckInput[], name: string) {
  return (
    checks.find((item) => item.source_document_name === name) ?? {
      source_document_name: name,
      available: null,
      complete: null,
      legible: null,
      missing_pages: null,
      comment: null,
    }
  );
}

export function SourceDocumentChecklist({
  requirements,
  checks,
  onChange,
  disabled,
}: {
  requirements: SourceDocumentRequirement[];
  checks: SourceDocumentCheckInput[];
  onChange: (nextChecks: SourceDocumentCheckInput[]) => void;
  disabled: boolean;
}) {
  const updateCheck = (
    sourceDocumentName: string,
    updates: Partial<SourceDocumentCheckInput>,
  ) => {
    const current = getCheckValue(checks, sourceDocumentName);
    const nextValue = { ...current, ...updates };
    const nextChecks = checks.some((item) => item.source_document_name === sourceDocumentName)
      ? checks.map((item) => (item.source_document_name === sourceDocumentName ? nextValue : item))
      : [...checks, nextValue];
    onChange(nextChecks);
  };

  return (
    <div className="space-y-4">
      {requirements.map((requirement) => {
        const current = getCheckValue(checks, requirement.name);
        return (
          <section key={requirement.id} className="rounded-xl border border-brand-border bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-brand-text">{requirement.name}</h3>
                <p className="mt-1 text-xs text-brand-muted">{requirement.description ?? "No extra notes."}</p>
              </div>
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-muted">
                {requirement.is_required ? "Required" : "Optional"}
              </span>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {([
                { field: "available", label: "Available", invert: false },
                { field: "complete", label: "Complete", invert: false },
                { field: "legible", label: "Legible", invert: false },
                { field: "missing_pages", label: "All pages present", invert: true },
              ] as const).map(({ field, label, invert }) => {
                const rawValue = Boolean(current[field as keyof SourceDocumentCheckInput]);
                const displayChecked = invert ? !rawValue : rawValue;
                return (
                  <label key={field} className="flex items-center gap-2 rounded-lg bg-brand-surface px-3 py-2 text-sm text-brand-text">
                    <input
                      type="checkbox"
                      checked={displayChecked}
                      onChange={(event) => {
                        const nextValue = invert ? !event.target.checked : event.target.checked;
                        updateCheck(requirement.name, {
                          [field]: nextValue,
                        } as Partial<SourceDocumentCheckInput>);
                      }}
                      disabled={disabled}
                      className="h-4 w-4"
                    />
                    {label}
                  </label>
                );
              })}
            </div>
            <div className="mt-4">
              <Textarea
                rows={3}
                placeholder="Document notes"
                value={current.comment ?? ""}
                onChange={(event) => updateCheck(requirement.name, { comment: event.target.value || null })}
                disabled={disabled}
              />
            </div>
          </section>
        );
      })}
    </div>
  );
}
