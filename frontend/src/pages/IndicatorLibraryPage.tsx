import { useCallback, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { AlertTriangle } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Table } from "../components/ui/Table";
import { useAuth } from "../hooks/useAuth";
import { dhis2Service } from "../services/dhis2Service";
import { indicatorService } from "../services/indicatorService";
import type { Dhis2DataElementSearchResult, Indicator, IndicatorFilters } from "../types";

const groupOptions = [
  "Maternity",
  "ANC",
  "PNC",
  "KMC / Newborn Care",
  "Birth Asphyxia",
  "Referrals",
  "Uterotonics / PPH",
];

export function IndicatorLibraryPage() {
  const { user } = useAuth();
  const canManage = user?.role === "MANAGER";
  const canRead = user?.role === "MANAGER";

  const [indicators, setIndicators] = useState<Indicator[]>([]);
  const [filters, setFilters] = useState<IndicatorFilters>({ search: "", group: "", hmis_section: "" });
  const [dhis2Search, setDhis2Search] = useState("");
  const [dhis2Results, setDhis2Results] = useState<Dhis2DataElementSearchResult[]>([]);
  const [dhis2Searching, setDhis2Searching] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadIndicators = useCallback(async () => {
    if (!canRead) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const params: IndicatorFilters = {};
      if (filters.search) {
        params.search = filters.search;
      }
      if (filters.group) {
        params.group = filters.group;
      }
      if (filters.hmis_section) {
        params.hmis_section = filters.hmis_section;
      }
      const data = await indicatorService.listIndicators(params);
      setIndicators(data);
    } catch {
      setError("Unable to load indicators right now.");
    } finally {
      setLoading(false);
    }
  }, [canRead, filters.group, filters.hmis_section, filters.search]);

  useEffect(() => {
    void loadIndicators();
  }, [loadIndicators]);

  useEffect(() => {
    if (!canManage || dhis2Search.trim().length < 2) {
      setDhis2Results([]);
      return;
    }
    const timer = window.setTimeout(async () => {
      setDhis2Searching(true);
      setError(null);
      try {
        const results = await dhis2Service.searchDataElements(dhis2Search.trim());
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

  const inferGroup = (result: Dhis2DataElementSearchResult) => {
    const code = (result.hmis_code ?? result.name).toUpperCase();
    if (code.includes("-AN")) return "ANC";
    if (code.includes("-PN")) return "PNC";
    if (code.includes("-MA")) return "Maternity";
    if (code.includes("KMC")) return "KMC / Newborn Care";
    if (code.includes("REF")) return "Referrals";
    return "Maternity";
  };

  const importDataElement = async (result: Dhis2DataElementSearchResult) => {
    setSubmitting(true);
    setError(null);
    try {
      await indicatorService.importFromDhis2({
        ...result,
        indicator_group: inferGroup(result),
        hmis_section: result.dataset_name?.includes("HMIS 105") ? "HMIS 105" : null,
        source_register: result.hmis_code?.includes("-AN") ? "ANC register" : result.hmis_code?.includes("-PN") ? "PNC register" : "Maternity register",
      });
      setMessage(`${result.name} imported into the indicator library.`);
      await loadIndicators();
      const refreshed = await dhis2Service.searchDataElements(dhis2Search.trim());
      setDhis2Results(refreshed);
    } catch {
      setError("Unable to import this DHIS2 data element.");
    } finally {
      setSubmitting(false);
    }
  };

  const columns = useMemo<ColumnDef<Indicator>[]>(
    () => [
      {
        accessorKey: "indicator_name",
        header: "Indicator / data element",
      },
      {
        accessorKey: "indicator_group",
        header: "Group",
      },
      {
        accessorKey: "hmis_code",
        header: "HMIS Code",
      },
      {
        accessorKey: "dhis2_uid_or_operand",
        header: "DHIS2 UID / Operand",
        cell: ({ row }) =>
          row.original.dhis2_uid_or_operand ? (
            <span className="font-mono text-xs text-brand-text">{row.original.dhis2_uid_or_operand}</span>
          ) : (
            <div className="inline-flex items-center gap-2 rounded-full bg-rose-100 px-3 py-1 text-xs font-semibold text-rose-700">
              <AlertTriangle size={12} />
              Missing UID
            </div>
          ),
      },
      {
        accessorKey: "dataset_name",
        header: "Dataset",
      },
      {
        accessorKey: "hmis_section",
        header: "HMIS Section",
      },
      {
        accessorKey: "source_register",
        header: "Source Register",
      },
      {
        accessorKey: "is_active",
        header: "Status",
        cell: ({ row }) => (
          <Badge tone={row.original.is_active ? "success" : "danger"}>
            {row.original.is_active ? "Active" : "Inactive"}
          </Badge>
        ),
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) =>
          canManage ? (
            <div className="flex flex-wrap gap-2">
              {row.original.is_active ? (
                <Button
                  variant="ghost"
                  className="px-3 py-2 text-xs"
                  onClick={async () => {
                    try {
                      await indicatorService.deactivateIndicator(row.original.id);
                      setMessage("Indicator deactivated.");
                      await loadIndicators();
                    } catch {
                      setError("Unable to deactivate the indicator right now.");
                    }
                  }}
                >
                  Deactivate
                </Button>
              ) : (
                <Button
                  variant="secondary"
                  className="px-3 py-2 text-xs"
                  onClick={async () => {
                    try {
                      await indicatorService.activateIndicator(row.original.id);
                      setMessage("Indicator activated.");
                      await loadIndicators();
                    } catch {
                      setError("Unable to activate the indicator right now.");
                    }
                  }}
                >
                  Activate
                </Button>
              )}
            </div>
          ) : (
            <span className="text-xs text-brand-muted">Read-only</span>
          ),
      },
    ],
    [canManage, loadIndicators],
  );

  const seedConfirmed = async () => {
    setSeeding(true);
    setError(null);
    try {
      const result = await indicatorService.seedConfirmedIndicators();
      setMessage(
        `${result.message} Created ${result.created}, updated ${result.updated}, skipped ${result.skipped}.`,
      );
      await loadIndicators();
    } catch {
      setError("Unable to run the confirmed indicator seed right now.");
    } finally {
      setSeeding(false);
    }
  };

  if (!canRead) {
    return (
      <Card title="Indicator Library" subtitle="Read access required">
        <p className="text-sm text-brand-muted">You do not have permission to view indicators.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
        <Card
          title="Indicator Library"
          subtitle="Search and import HMIS 105 data elements from DHIS2 for assessment rounds."
        >
          <div className="grid gap-3 lg:grid-cols-[1.2fr_0.8fr_0.8fr_auto]">
            <Input
              placeholder="Search by name, HMIS code, dataset, or UID"
              value={filters.search ?? ""}
              onChange={(event) => setFilters({ ...filters, search: event.target.value })}
            />
            <Select
              value={filters.group ?? ""}
              onChange={(event) => setFilters({ ...filters, group: event.target.value })}
            >
              <option value="">All groups</option>
              {groupOptions.map((group) => (
                <option key={group} value={group}>
                  {group}
                </option>
              ))}
            </Select>
            <Input
              placeholder="Filter by HMIS section"
              value={filters.hmis_section ?? ""}
              onChange={(event) => setFilters({ ...filters, hmis_section: event.target.value })}
            />
            {canManage ? (
              <Button onClick={seedConfirmed} disabled={seeding}>
                {seeding ? "Seeding..." : "Seed confirmed"}
              </Button>
            ) : null}
          </div>
          {error ? <p className="mt-4 text-sm text-brand-danger">{error}</p> : null}
          {message ? <p className="mt-4 text-sm text-brand-teal">{message}</p> : null}
        </Card>

        {canManage ? (
          <Card title="Search DHIS2 HMIS 105 data elements" subtitle="Find data elements by HMIS code, name, short name, or UID and import them into the local library.">
            <Input
              placeholder="Search DHIS2 by HMIS code, data element name, or UID"
              value={dhis2Search}
              onChange={(event) => setDhis2Search(event.target.value)}
            />
            <div className="mt-4">
              {dhis2Searching ? (
                <div className="rounded-xl border border-brand-border bg-brand-surface p-4 text-sm text-brand-muted">
                  Searching DHIS2...
                </div>
              ) : dhis2Search.trim().length >= 2 && dhis2Results.length === 0 ? (
                <div className="rounded-xl border border-dashed border-brand-border bg-brand-surface p-4 text-sm text-brand-muted">
                  No DHIS2 data elements found for this search.
                </div>
              ) : dhis2Results.length > 0 ? (
                <div className="overflow-x-auto rounded-xl border border-brand-border">
                  <table className="min-w-full divide-y divide-slate-100 text-sm">
                    <thead className="bg-slate-50 text-left text-xs uppercase tracking-[0.16em] text-brand-muted">
                      <tr>
                        <th className="px-4 py-3">Data element</th>
                        <th className="px-4 py-3">HMIS code</th>
                        <th className="px-4 py-3">DHIS2 UID</th>
                        <th className="px-4 py-3">Dataset</th>
                        <th className="px-4 py-3">Category combo</th>
                        <th className="px-4 py-3">Value type</th>
                        <th className="px-4 py-3">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {dhis2Results.map((result) => (
                        <tr key={result.dhis2_uid_or_operand}>
                          <td className="px-4 py-3 font-semibold text-brand-text">{result.name}</td>
                          <td className="px-4 py-3">{result.hmis_code ?? "-"}</td>
                          <td className="px-4 py-3 font-mono text-xs">{result.dhis2_uid_or_operand}</td>
                          <td className="px-4 py-3">{result.dataset_name ?? "-"}</td>
                          <td className="px-4 py-3">{result.category_combo ?? "-"}</td>
                          <td className="px-4 py-3">{result.value_type ?? "-"}</td>
                          <td className="px-4 py-3">
                            {result.already_imported ? (
                              <Badge tone="success">Already imported</Badge>
                            ) : (
                              <Button className="px-3 py-2 text-xs" onClick={() => void importDataElement(result)} disabled={submitting}>
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
          </Card>
        ) : null}

        <Card className="overflow-hidden">
          {loading ? (
            <div className="rounded-2xl border border-brand-border bg-brand-surface p-6 text-sm text-brand-muted">
              Loading indicators...
            </div>
          ) : (
            <Table data={indicators} columns={columns} emptyMessage="No indicators found yet." />
          )}
        </Card>
    </div>
  );
}
