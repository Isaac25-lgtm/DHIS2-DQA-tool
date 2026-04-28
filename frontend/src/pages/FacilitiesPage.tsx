import { useEffect, useState } from "react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Textarea } from "../components/ui/Textarea";
import { useAuth } from "../hooks/useAuth";
import { dhis2Service } from "../services/dhis2Service";
import { facilityService } from "../services/facilityService";
import type { Dhis2FacilitySearchResult, FacilityFormPayload } from "../types";

const facilityTypes = ["Hospital", "HC IV", "HC III", "HC II", "Other"];
const ownershipTypes = ["PNFP", "Government", "Private", "Other"];

const emptyForm: FacilityFormPayload = {
  facility_name: "",
  district: "",
  facility_type: "Hospital",
  ownership: "PNFP",
  dhis2_org_unit_uid: "",
  dhis2_code: "",
  dhis2_path: "",
  dhis2_parent_name: "",
  dhis2_level: null,
  notes: "",
  is_active: true,
};

export function FacilitiesPage() {
  const { user } = useAuth();
  const canManage = user?.role === "MANAGER";

  const [form, setForm] = useState<FacilityFormPayload>(emptyForm);
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

  const submitForm = async () => {
    if (!canManage) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        ...form,
        dhis2_org_unit_uid: form.dhis2_org_unit_uid?.trim() || null,
        dhis2_code: form.dhis2_code?.trim() || null,
        dhis2_path: form.dhis2_path?.trim() || null,
        dhis2_parent_name: form.dhis2_parent_name?.trim() || null,
        notes: form.notes?.trim() || null,
      };
      await facilityService.createFacility(payload);
      setMessage("Facility created successfully.");
      setForm(emptyForm);
    } catch {
      setError("Unable to save the facility. Check for duplicates or invalid values.");
    } finally {
      setSubmitting(false);
    }
  };

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
      <Card title="Search facilities in DHIS2" subtitle="Import facilities from the DHIS2 facility registry for UCMB assessments.">
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

      <Card
        title="Manual fallback"
        subtitle="Use manual entry only when a facility cannot be found in DHIS2."
      >
          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-sm font-semibold text-brand-text">Facility name</label>
              <Input
                value={form.facility_name}
                onChange={(event) => setForm({ ...form, facility_name: event.target.value })}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-brand-text">District</label>
              <Input value={form.district} onChange={(event) => setForm({ ...form, district: event.target.value })} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-semibold text-brand-text">Facility type</label>
                <Select
                  value={form.facility_type}
                  onChange={(event) => setForm({ ...form, facility_type: event.target.value })}
                >
                  {facilityTypes.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <label className="mb-2 block text-sm font-semibold text-brand-text">Ownership</label>
                <Select
                  value={form.ownership}
                  onChange={(event) => setForm({ ...form, ownership: event.target.value })}
                >
                  {ownershipTypes.map((ownership) => (
                    <option key={ownership} value={ownership}>
                      {ownership}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-brand-text">DHIS2 org unit UID</label>
              <Input
                value={form.dhis2_org_unit_uid ?? ""}
                onChange={(event) => setForm({ ...form, dhis2_org_unit_uid: event.target.value })}
                placeholder="Optional for now, but required later for DHIS2 pulls"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-brand-text">Notes</label>
              <Textarea value={form.notes ?? ""} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
            </div>
            <div className="flex gap-2">
              <Button onClick={submitForm} disabled={submitting}>
                {submitting ? "Saving..." : "Create facility"}
              </Button>
            </div>
          </div>
      </Card>
    </div>
  );
}
