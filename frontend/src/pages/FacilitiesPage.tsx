import { useEffect, useState } from "react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { useAuth } from "../hooks/useAuth";
import { dhis2Service } from "../services/dhis2Service";
import { facilityService } from "../services/facilityService";
import type { Dhis2FacilitySearchResult } from "../types";

export function FacilitiesPage() {
  const { user } = useAuth();
  const canManage = user?.role === "MANAGER";

  const [dhis2Search, setDhis2Search] = useState("");
  const [dhis2Results, setDhis2Results] = useState<Dhis2FacilitySearchResult[]>([]);
  const [dhis2Searching, setDhis2Searching] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!canManage || dhis2Search.trim().length < 2) {
      setDhis2Results([]);
      return;
    }
    const timer = window.setTimeout(async () => {
      setDhis2Searching(true);
      setError(null);
      try {
        const results = await dhis2Service.searchFacilities(dhis2Search.trim());
        setDhis2Results(results);
      } catch {
        setError("Could not connect to DHIS2. Check DHIS2 credentials or network.");
        setDhis2Results([]);
      } finally {
        setDhis2Searching(false);
      }
    }, 400);
    return () => window.clearTimeout(timer);
  }, [canManage, dhis2Search]);

  const importFacility = async (result: Dhis2FacilitySearchResult) => {
    setSubmitting(true);
    setError(null);
    try {
      await facilityService.importFromDhis2({
        ...result,
        ownership: result.ownership ?? "Other",
      });
      setMessage(`${result.facility_name} imported and ready for assessment setup.`);
      const refreshed = await dhis2Service.searchFacilities(dhis2Search.trim());
      setDhis2Results(refreshed);
    } catch {
      setError("Unable to import this DHIS2 facility.");
    } finally {
      setSubmitting(false);
    }
  };

  if (!canManage) {
    return (
      <Card title="Facilities" subtitle="Facility import is managed by managers.">
        <p className="text-sm text-brand-muted">
          Managers search and import facilities from DHIS2 before they are used in assessment setup.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card
        title="Search facilities in DHIS2"
        subtitle="Import facilities from the DHIS2 facility registry for UCMB assessments. Managers can preload facilities before fieldwork so network issues do not block assessment setup later."
      >
        <div className="space-y-4">
          <Input
            placeholder="Search DHIS2 by facility name, district, code, or UID"
            value={dhis2Search}
            onChange={(event) => setDhis2Search(event.target.value)}
          />
          {error ? <p className="text-sm text-brand-danger">{error}</p> : null}
          {message ? <p className="text-sm text-brand-teal">{message}</p> : null}
          <div className="mt-4">
            {dhis2Searching ? (
              <div className="rounded-xl border border-brand-border bg-brand-surface p-4 text-sm text-brand-muted">
                Searching DHIS2...
              </div>
            ) : dhis2Search.trim().length >= 2 && dhis2Results.length === 0 ? (
              <div className="rounded-xl border border-dashed border-brand-border bg-brand-surface p-4 text-sm text-brand-muted">
                No DHIS2 facilities found for this search.
              </div>
            ) : dhis2Results.length > 0 ? (
              <div className="overflow-x-auto rounded-xl border border-brand-border">
                <table className="min-w-full divide-y divide-slate-100 text-sm">
                  <thead className="bg-slate-50 text-left text-xs uppercase tracking-[0.16em] text-brand-muted">
                    <tr>
                      <th className="px-4 py-3">Facility</th>
                      <th className="px-4 py-3">District</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">DHIS2 UID</th>
                      <th className="px-4 py-3">Code</th>
                      <th className="px-4 py-3">Parent</th>
                      <th className="px-4 py-3">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {dhis2Results.map((result) => (
                      <tr key={result.dhis2_org_unit_uid}>
                        <td className="px-4 py-3 font-semibold text-brand-text">{result.facility_name}</td>
                        <td className="px-4 py-3">{result.district}</td>
                        <td className="px-4 py-3">{result.facility_type}</td>
                        <td className="px-4 py-3 font-mono text-xs">{result.dhis2_org_unit_uid}</td>
                        <td className="px-4 py-3">{result.dhis2_code ?? "-"}</td>
                        <td className="px-4 py-3">{result.dhis2_parent_name ?? "-"}</td>
                        <td className="px-4 py-3">
                          {result.already_imported ? (
                            <Badge tone="success">Already imported</Badge>
                          ) : (
                            <Button className="px-3 py-2 text-xs" onClick={() => void importFacility(result)} disabled={submitting}>
                              Import
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        </div>
      </Card>
    </div>
  );
}
