import { AlertTriangle, RefreshCcw, WifiOff } from "lucide-react";
import { useState } from "react";
import { useDhis2Status } from "../../hooks/useDhis2Status";

/**
 * Persistent top-of-page banner that surfaces DHIS2 connectivity state to every
 * authenticated user. Hides itself entirely when DHIS2 is reachable and a
 * manager is signed in (the happy path). Otherwise renders a contextual
 * message and a Retry button so the user can re-check on demand.
 */
export function Dhis2StatusBanner() {
  const { status, reachability, signedIn, loading, refresh } = useDhis2Status();
  const [retrying, setRetrying] = useState(false);

  if (!status) return null;
  if (reachability === "reachable" && signedIn) return null;

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await refresh();
    } finally {
      setRetrying(false);
    }
  };

  if (reachability === "unreachable") {
    return (
      <div className="rounded-[14px] border border-amber-300 bg-amber-50 px-4 py-3 shadow-sm">
        <div className="flex items-start gap-3">
          <WifiOff className="mt-0.5 shrink-0 text-amber-700" size={18} />
          <div className="flex-1 text-sm">
            <p className="font-semibold text-amber-900">DHIS2 is currently unreachable.</p>
            <p className="mt-1 text-amber-800">
              Field assessments can continue. Register and HMIS 105 values are saved as normal - the DHIS2 column populates from the
              values the manager pre-synced before publishing. Once DHIS2 returns, a manager can refresh values from the assessment
              round. Comparison and analysis still run; rows without a DHIS2 value will show as
              <span className="font-semibold"> Incomplete</span> until the manager refreshes them.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void handleRetry()}
            disabled={retrying || loading}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-amber-400 bg-white px-3 py-1.5 text-xs font-semibold text-amber-900 shadow-sm transition hover:bg-amber-100 disabled:opacity-60"
          >
            <RefreshCcw size={14} className={retrying ? "animate-spin" : undefined} />
            {retrying ? "Checking..." : "Retry now"}
          </button>
        </div>
      </div>
    );
  }

  if (reachability === "not_configured") {
    return (
      <div className="rounded-[14px] border border-slate-300 bg-slate-50 px-4 py-3 shadow-sm">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 shrink-0 text-slate-700" size={18} />
          <div className="flex-1 text-sm">
            <p className="font-semibold text-slate-900">DHIS2 base URL is not configured.</p>
            <p className="mt-1 text-slate-700">
              The platform is running without a DHIS2 endpoint. Set <code className="font-mono">DHIS2_BASE_URL</code> on the backend
              service and redeploy to enable live DHIS2 sync.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-[14px] border border-sky-300 bg-sky-50 px-4 py-3 shadow-sm">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 shrink-0 text-sky-700" size={18} />
        <div className="flex-1 text-sm">
          <p className="font-semibold text-sky-900">DHIS2 is reachable but no manager is signed in.</p>
          <p className="mt-1 text-sky-800">
            A manager must sign in from{" "}
            <a href="/settings" className="font-semibold underline">Settings - DHIS2 sign-in</a> to enable DHIS2 search, import, and pre-sync.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleRetry()}
          disabled={retrying || loading}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-sky-400 bg-white px-3 py-1.5 text-xs font-semibold text-sky-900 shadow-sm transition hover:bg-sky-100 disabled:opacity-60"
        >
          <RefreshCcw size={14} className={retrying ? "animate-spin" : undefined} />
          {retrying ? "Checking..." : "Retry"}
        </button>
      </div>
    </div>
  );
}
