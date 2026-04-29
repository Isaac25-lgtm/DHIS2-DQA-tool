import { useEffect, useState, type FormEvent } from "react";
import { Database, HardDriveDownload, KeyRound, Link2, ShieldCheck } from "lucide-react";
import { Card } from "../components/ui/Card";
import { useAuth } from "../hooks/useAuth";
import {
  getFailedSyncCount,
  getPendingSyncCount,
  listCachedAssessments,
  listPendingSyncItems,
} from "../services/offlineStore";
import { systemService } from "../services/systemService";
import { dhis2Service } from "../services/dhis2Service";
import type { Dhis2ConnectionStatus, SystemInfo } from "../types";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

function readApiError(error: unknown, fallback: string) {
  if (error && typeof error === "object" && "response" in error) {
    const response = (error as { response?: { status?: number; data?: { detail?: string } } }).response;
    if (response?.status === 403) {
      return "Only manager accounts can sign in to DHIS2. Sign out and log back in as a manager.";
    }
    if (response?.status === 401) {
      return "Your UCMB session has expired. Please sign in again before connecting DHIS2.";
    }
    if (response?.data?.detail) {
      return response.data.detail;
    }
  }
  return fallback;
}

export function SettingsPage() {
  const { user } = useAuth();
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [pendingSyncCount, setPendingSyncCount] = useState(0);
  const [failedSyncCount, setFailedSyncCount] = useState(0);
  const [cachedAssessments, setCachedAssessments] = useState(0);
  const [draftCount, setDraftCount] = useState(0);
  const [dhis2Status, setDhis2Status] = useState<Dhis2ConnectionStatus | null>(null);
  const [checkingDhis2, setCheckingDhis2] = useState(false);
  const [dhis2Login, setDhis2Login] = useState({ base_url: "", username: "", password: "" });
  const [dhis2Error, setDhis2Error] = useState<string | null>(null);
  const [dhis2SigningIn, setDhis2SigningIn] = useState(false);
  const [dhis2SigningOut, setDhis2SigningOut] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSettings = async () => {
      setLoading(true);
      try {
        const [info, pendingCount, failedCount, cachedItems, drafts] = await Promise.all([
          systemService.getSystemInfo().catch(() => null),
          getPendingSyncCount().catch(() => 0),
          getFailedSyncCount().catch(() => 0),
          listCachedAssessments().catch(() => []),
          listPendingSyncItems().catch(() => []),
        ]);
        setSystemInfo(info);
        setDhis2Login((current) => ({
          ...current,
          base_url: current.base_url || info?.dhis2_base_url || "https://hmis.health.go.ug/api",
        }));
        setPendingSyncCount(pendingCount);
        setFailedSyncCount(failedCount);
        setCachedAssessments(cachedItems.length);
        setDraftCount(drafts.length);
      } finally {
        setLoading(false);
      }
    };

    void loadSettings();
  }, []);

  const testDhis2Connection = async () => {
    setCheckingDhis2(true);
    setDhis2Error(null);
    try {
      const status = await dhis2Service.getConnectionStatus();
      setDhis2Status(status);
      if (!status.connected) {
        setDhis2Error(status.message);
      }
    } catch (error) {
      setDhis2Error(readApiError(error, "Unable to test DHIS2 connection."));
    } finally {
      setCheckingDhis2(false);
    }
  };

  const signInToDhis2 = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (user?.role !== "MANAGER") {
      setDhis2Error("Only manager accounts can sign in to DHIS2 for backend sync.");
      return;
    }
    setDhis2SigningIn(true);
    setDhis2Error(null);
    try {
      const status = await dhis2Service.login({
        base_url: dhis2Login.base_url || null,
        username: dhis2Login.username,
        password: dhis2Login.password,
      });
      setDhis2Status(status);
      setDhis2Login((current) => ({ ...current, password: "" }));
      if (!status.connected) {
        setDhis2Error(status.message);
      }
    } catch (error) {
      setDhis2Error(readApiError(error, "Unable to sign in to DHIS2."));
    } finally {
      setDhis2SigningIn(false);
    }
  };

  const signOutFromDhis2 = async () => {
    setDhis2SigningOut(true);
    setDhis2Error(null);
    try {
      const status = await dhis2Service.logout();
      setDhis2Status(status);
      setDhis2Login((current) => ({ ...current, password: "" }));
    } catch (error) {
      setDhis2Error(readApiError(error, "Unable to sign out of DHIS2."));
    } finally {
      setDhis2SigningOut(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card
        title="Platform Settings"
        subtitle="Environment visibility, DHIS2 sign-in, connectivity references, and offline storage status."
      >
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-brand-surface px-5 py-5">
            <div className="flex items-center gap-3 text-brand-teal">
              <Database size={18} />
              <p className="text-sm font-semibold text-brand-text">Database</p>
            </div>
            <p className="mt-3 text-3xl font-bold text-brand-navy">
              {loading ? "--" : systemInfo?.database_status?.toUpperCase() ?? "UNKNOWN"}
            </p>
            <p className="mt-2 text-sm text-brand-muted">Health endpoint exposes database availability only, not credentials.</p>
          </div>

          <div className="rounded-2xl bg-brand-surface px-5 py-5">
            <div className="flex items-center gap-3 text-brand-teal">
              <HardDriveDownload size={18} />
              <p className="text-sm font-semibold text-brand-text">Offline storage</p>
            </div>
            <p className="mt-3 text-3xl font-bold text-brand-navy">{loading ? "--" : cachedAssessments}</p>
            <p className="mt-2 text-sm text-brand-muted">Cached assessment packages currently stored in this browser.</p>
          </div>

          <div className="rounded-2xl bg-brand-surface px-5 py-5">
            <div className="flex items-center gap-3 text-brand-teal">
              <ShieldCheck size={18} />
              <p className="text-sm font-semibold text-brand-text">Pending sync</p>
            </div>
            <p className="mt-3 text-3xl font-bold text-brand-navy">{loading ? "--" : pendingSyncCount}</p>
            <p className="mt-2 text-sm text-brand-muted">
              {failedSyncCount > 0
                ? `${failedSyncCount} draft${failedSyncCount === 1 ? "" : "s"} currently need retry or relogin.`
                : "No sync failures are currently flagged on this device."}
            </p>
          </div>

        </div>
      </Card>

      <section className="grid gap-6 xl:grid-cols-2">
        <Card title="Runtime information" subtitle="Visible configuration that is safe to surface to signed-in users.">
          <dl className="space-y-4">
            <div className="rounded-2xl border border-brand-border bg-white px-4 py-4">
              <dt className="text-xs uppercase tracking-[0.18em] text-brand-muted">Application</dt>
              <dd className="mt-2 text-sm font-semibold text-brand-text">
                {loading ? "Loading..." : `${systemInfo?.app_name ?? "UCMB HMIS 105 DQA"}${systemInfo?.app_version ? ` · ${systemInfo.app_version}` : ""}`}
              </dd>
            </div>
            <div className="rounded-2xl border border-brand-border bg-white px-4 py-4">
              <dt className="text-xs uppercase tracking-[0.18em] text-brand-muted">Environment</dt>
              <dd className="mt-2 text-sm font-semibold text-brand-text">{loading ? "Loading..." : systemInfo?.environment ?? "Unknown"}</dd>
            </div>
            <div className="rounded-2xl border border-brand-border bg-white px-4 py-4">
              <dt className="text-xs uppercase tracking-[0.18em] text-brand-muted">DHIS2 base URL</dt>
              <dd className="mt-2 flex items-center gap-2 text-sm font-semibold text-brand-text">
                <Link2 size={14} className="text-brand-teal" />
                {loading ? "Loading..." : systemInfo?.dhis2_base_url ?? "Not configured"}
              </dd>
            </div>
            <div className="rounded-2xl border border-brand-border bg-white px-4 py-4">
              <dt className="text-xs uppercase tracking-[0.18em] text-brand-muted">DHIS2 connection</dt>
              <dd className="mt-3 flex flex-wrap items-center gap-3">
                <Badge tone={dhis2Status?.connected ? "success" : dhis2Status ? "danger" : "neutral"}>
                  {dhis2Status ? (dhis2Status.signed_in ? "Signed in" : dhis2Status.connected ? "Connected" : "Not signed in") : "Not checked"}
                </Badge>
                <Button className="px-3 py-2 text-xs" variant="secondary" onClick={() => void testDhis2Connection()} disabled={checkingDhis2}>
                  {checkingDhis2 ? "Testing..." : "Test DHIS2 Connection"}
                </Button>
                {dhis2Status?.signed_in ? (
                  <Button className="px-3 py-2 text-xs" variant="ghost" onClick={() => void signOutFromDhis2()} disabled={dhis2SigningOut}>
                    {dhis2SigningOut ? "Signing out..." : "Sign out DHIS2"}
                  </Button>
                ) : null}
              </dd>
              <p className="mt-2 text-sm text-brand-muted">
                {dhis2Status?.message ?? "Managers must sign in to DHIS2 here before live search, import, and auto-pull can run."}
              </p>
              {dhis2Error ? (
                <p className="mt-2 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm font-semibold text-brand-danger">
                  {dhis2Error}
                </p>
              ) : null}
              {dhis2Status?.last_checked_at ? (
                <p className="mt-1 text-xs text-brand-muted">Last checked: {new Date(dhis2Status.last_checked_at).toLocaleString()}</p>
              ) : null}
            </div>
            <div className="rounded-2xl border border-brand-border bg-white px-4 py-4">
              <dt className="text-xs uppercase tracking-[0.18em] text-brand-muted">Offline drafts on this device</dt>
              <dd className="mt-2 text-sm font-semibold text-brand-text">
                {loading ? "Loading..." : `${draftCount} draft${draftCount === 1 ? "" : "s"}`}
              </dd>
            </div>
          </dl>
        </Card>

        <Card title="DHIS2 manager sign-in" subtitle="Use a DHIS2 account with permission to read organisation units, data elements, and analytics.">
          {user?.role === "MANAGER" ? (
            <form className="space-y-4" onSubmit={(event) => void signInToDhis2(event)}>
              <div className="rounded-2xl border border-brand-border bg-white px-4 py-4">
                <div className="flex items-center gap-3 text-brand-teal">
                  <KeyRound size={18} />
                  <p className="text-sm font-semibold text-brand-text">DHIS2 credentials are not stored in the browser</p>
                </div>
                <p className="mt-2 text-sm text-brand-muted">
                  The password is sent once to the FastAPI backend over your signed-in UCMB session. The backend keeps an active DHIS2 session in server memory for API calls and clears the password from this form after sign-in.
                </p>
              </div>
              {dhis2Error ? (
                <p className="rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm font-semibold text-brand-danger">
                  {dhis2Error}
                </p>
              ) : null}
              <label className="block">
                <span className="text-sm font-semibold text-brand-text">DHIS2 base URL</span>
                <input
                  className="mt-2 w-full rounded-2xl border border-brand-border px-4 py-3 text-sm outline-none focus:border-brand-teal focus:ring-2 focus:ring-brand-teal/20"
                  value={dhis2Login.base_url}
                  onChange={(event) => setDhis2Login((current) => ({ ...current, base_url: event.target.value }))}
                  placeholder="https://hmis.health.go.ug/api"
                />
              </label>
              <label className="block">
                <span className="text-sm font-semibold text-brand-text">DHIS2 username</span>
                <input
                  className="mt-2 w-full rounded-2xl border border-brand-border px-4 py-3 text-sm outline-none focus:border-brand-teal focus:ring-2 focus:ring-brand-teal/20"
                  value={dhis2Login.username}
                  onChange={(event) => setDhis2Login((current) => ({ ...current, username: event.target.value }))}
                  autoComplete="username"
                  placeholder="Your DHIS2 username"
                  required
                />
              </label>
              <label className="block">
                <span className="text-sm font-semibold text-brand-text">DHIS2 password</span>
                <input
                  type="password"
                  className="mt-2 w-full rounded-2xl border border-brand-border px-4 py-3 text-sm outline-none focus:border-brand-teal focus:ring-2 focus:ring-brand-teal/20"
                  value={dhis2Login.password}
                  onChange={(event) => setDhis2Login((current) => ({ ...current, password: event.target.value }))}
                  autoComplete="current-password"
                  placeholder="Your DHIS2 password"
                  required
                />
              </label>
              <Button type="submit" disabled={dhis2SigningIn || !dhis2Login.username || !dhis2Login.password}>
                {dhis2SigningIn ? "Signing in..." : "Sign in to DHIS2"}
              </Button>
            </form>
          ) : (
            <div className="rounded-2xl border border-brand-border bg-brand-surface px-4 py-4">
              <div className="flex items-center gap-3 text-brand-teal">
                <KeyRound size={18} />
                <p className="text-sm font-semibold text-brand-text">Manager access required</p>
              </div>
              <p className="mt-2 text-sm text-brand-muted">
                DHIS2 sign-in is only available to manager accounts. Assessment team, reviewer, and viewer accounts cannot connect DHIS2 credentials.
              </p>
            </div>
          )}
        </Card>

        <Card title="Configuration boundaries" subtitle="Sensitive credentials stay outside frontend API responses and browser storage.">
          <div className="space-y-4">
            <div className="rounded-2xl border border-brand-border bg-white px-4 py-4">
              <p className="text-sm font-semibold text-brand-text">What stays server-side</p>
              <p className="mt-2 text-sm text-brand-muted">
                DHIS2 password, AI API key, JWT secret key, and full database connection details are never exposed in frontend API responses.
              </p>
            </div>
            <div className="rounded-2xl border border-brand-border bg-white px-4 py-4">
              <p className="text-sm font-semibold text-brand-text">Manager-only configuration</p>
              <p className="mt-2 text-sm text-brand-muted">
                {user?.role === "MANAGER"
                  ? "Dedicated editable configuration screens can be added later without exposing secrets here."
                  : "Editable environment configuration remains manager-only and is intentionally not exposed in this page."}
              </p>
            </div>
          </div>
        </Card>
      </section>
    </div>
  );
}
