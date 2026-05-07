import { useEffect, useState, type FormEvent } from "react";
import { ChevronDown, ChevronUp, KeyRound, ShieldCheck } from "lucide-react";
import { Card } from "../components/ui/Card";
import { useAuth } from "../hooks/useAuth";
import { systemService } from "../services/systemService";
import { dhis2Service } from "../services/dhis2Service";
import type { Dhis2ConnectionStatus, SystemInfo } from "../types";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

const DHIS2_MANAGER_ONLY_COPY =
  "Only managers can sign in to DHIS2. Assessors use the DHIS2 values pre-synced by the manager before fieldwork.";

function readApiError(error: unknown, fallback: string) {
  if (error && typeof error === "object" && "response" in error) {
    const response = (error as { response?: { status?: number; data?: { detail?: string } } }).response;
    if (response?.status === 403) {
      return "Only managers can sign in to DHIS2. Sign in as a manager account to manage DHIS2.";
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

function statusTone(status: Dhis2ConnectionStatus | null): "success" | "warning" | "danger" | "neutral" {
  if (!status) return "neutral";
  if (status.signed_in && status.connected) return "success";
  if (status.signed_in) return "warning";
  if (status.connected) return "warning";
  return "danger";
}

function statusLabel(status: Dhis2ConnectionStatus | null): string {
  if (!status) return "Not checked";
  if (status.signed_in && status.connected) return "Signed in";
  if (status.signed_in) return "Session retained";
  if (status.connected) return "Reachable, not signed in";
  return "Unreachable";
}

export function SettingsPage() {
  const { user } = useAuth();
  const isManager = user?.role === "MANAGER";
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [dhis2Status, setDhis2Status] = useState<Dhis2ConnectionStatus | null>(null);
  const [checkingDhis2, setCheckingDhis2] = useState(false);
  const [dhis2Login, setDhis2Login] = useState({ base_url: "", username: "", password: "" });
  const [dhis2Error, setDhis2Error] = useState<string | null>(null);
  const [dhis2SigningIn, setDhis2SigningIn] = useState(false);
  const [dhis2SigningOut, setDhis2SigningOut] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [showSafetyDetails, setShowSafetyDetails] = useState(false);

  useEffect(() => {
    const loadSettings = async () => {
      const info = await systemService.getSystemInfo().catch(() => null);
      setSystemInfo(info);
      setDhis2Login((current) => ({
        ...current,
        base_url: current.base_url || info?.dhis2_base_url || "https://hmis.health.go.ug/api",
      }));
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
    if (!isManager) {
      setDhis2Error("Only managers can sign in to DHIS2.");
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
      <Card title="DHIS2 sign-in" subtitle={DHIS2_MANAGER_ONLY_COPY}>
        <div className="flex flex-wrap items-center gap-3">
          <Badge tone={statusTone(dhis2Status)}>{statusLabel(dhis2Status)}</Badge>
          <Button className="px-3 py-2 text-xs" variant="secondary" onClick={() => void testDhis2Connection()} disabled={checkingDhis2}>
            {checkingDhis2 ? "Testing..." : "Test connection"}
          </Button>
          {dhis2Status?.signed_in && isManager ? (
            <Button className="px-3 py-2 text-xs" variant="ghost" onClick={() => void signOutFromDhis2()} disabled={dhis2SigningOut}>
              {dhis2SigningOut ? "Signing out..." : "Sign out DHIS2"}
            </Button>
          ) : null}
          {dhis2Status?.last_checked_at ? (
            <span className="text-xs text-brand-muted">Last checked: {new Date(dhis2Status.last_checked_at).toLocaleString()}</span>
          ) : null}
        </div>

        {dhis2Status?.message ? <p className="mt-3 text-sm text-brand-muted">{dhis2Status.message}</p> : null}
        {dhis2Error ? (
          <p className="mt-3 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm font-semibold text-brand-danger">
            {dhis2Error}
          </p>
        ) : null}

        {isManager ? (
          <form className="mt-5 space-y-4" onSubmit={(event) => void signInToDhis2(event)}>
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
            <button
              type="button"
              onClick={() => setShowSafetyDetails((value) => !value)}
              className="flex items-center gap-2 text-xs font-semibold text-brand-teal"
            >
              <KeyRound size={14} />
              Why is my password safe?
              {showSafetyDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {showSafetyDetails ? (
              <p className="rounded-2xl border border-brand-border bg-brand-surface px-4 py-3 text-xs text-brand-muted">
                The password is sent once to the FastAPI backend over your signed-in UCMB session. The backend keeps an active DHIS2
                session for API calls, stores the DHIS2 password only server-side in encrypted form so Render restarts do not silently
                drop the session, and clears the password from this form after sign-in. The password is never stored in the browser and
                never returned in any frontend API response. Use Sign out DHIS2 when you intentionally want to clear it.
              </p>
            ) : null}
          </form>
        ) : (
          <div className="mt-5 rounded-2xl border border-brand-border bg-brand-surface px-4 py-4">
            <div className="flex items-center gap-3 text-brand-teal">
              <ShieldCheck size={18} />
              <p className="text-sm font-semibold text-brand-text">Manager access required</p>
            </div>
            <p className="mt-2 text-sm text-brand-muted">{DHIS2_MANAGER_ONLY_COPY}</p>
          </div>
        )}
      </Card>

      <Card
        title="Advanced system info"
        subtitle="Read-only configuration details. Click to expand."
      >
        <button
          type="button"
          onClick={() => setAdvancedOpen((value) => !value)}
          className="flex items-center gap-2 text-sm font-semibold text-brand-teal"
        >
          {advancedOpen ? "Hide details" : "Show details"}
          {advancedOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {advancedOpen ? (
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between gap-4 rounded-2xl border border-brand-border bg-white px-4 py-3">
              <dt className="text-brand-muted">Application</dt>
              <dd className="text-right font-semibold text-brand-text">
                {systemInfo
                  ? `${systemInfo.app_name}${systemInfo.app_version ? ` · ${systemInfo.app_version}` : ""}`
                  : "Loading..."}
              </dd>
            </div>
            <div className="flex justify-between gap-4 rounded-2xl border border-brand-border bg-white px-4 py-3">
              <dt className="text-brand-muted">Environment</dt>
              <dd className="font-semibold text-brand-text">{systemInfo?.environment ?? "Loading..."}</dd>
            </div>
            <div className="flex justify-between gap-4 rounded-2xl border border-brand-border bg-white px-4 py-3">
              <dt className="text-brand-muted">Database</dt>
              <dd className="font-semibold text-brand-text">{systemInfo?.database_status?.toUpperCase() ?? "Loading..."}</dd>
            </div>
            <div className="flex justify-between gap-4 rounded-2xl border border-brand-border bg-white px-4 py-3">
              <dt className="text-brand-muted">DHIS2 base URL</dt>
              <dd className="break-all text-right font-semibold text-brand-text">
                {systemInfo?.dhis2_base_url ?? "Loading..."}
              </dd>
            </div>
          </dl>
        ) : null}
      </Card>
    </div>
  );
}
