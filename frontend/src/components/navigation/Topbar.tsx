import { Bell, LogOut, ShieldCheck, Wifi, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import {
  OFFLINE_STORE_EVENT,
  getFailedSyncCount,
  getPendingSyncCount,
} from "../../services/offlineStore";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

const pageTitles: Record<string, string> = {
  "/dashboard": "Operational Data Quality Dashboard",
  "/users": "Users / Team Accounts",
  "/facilities": "Facilities",
  "/indicators": "Indicator Library",
  "/assessment-rounds": "Assessment Rounds",
  "/assessment-facilities": "Assessment Workspace Review",
  "/submissions": "Submissions",
  "/my-assessments": "My Assessments",
  "/analytics": "Analytics",
  "/assessment-results": "Assessment Results",
  "/facility-dqa": "Facility DQA Profile",
  "/indicator-analytics": "Indicator Analytics",
  "/corrective-actions": "Corrective Actions",
  "/reports": "Reports",
  "/settings": "Settings",
};

export function Topbar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { isOnline } = useNetworkStatus();
  const [pendingSyncCount, setPendingSyncCount] = useState(0);
  const [failedSyncCount, setFailedSyncCount] = useState(0);
  const currentTitle =
    Object.entries(pageTitles).find(([path]) => location.pathname === path || location.pathname.startsWith(`${path}/`))?.[1] ??
    "UCMB HMIS 105 DQA";

  useEffect(() => {
    const refreshOfflineStatus = async () => {
      setPendingSyncCount(await getPendingSyncCount().catch(() => 0));
      setFailedSyncCount(await getFailedSyncCount().catch(() => 0));
    };

    void refreshOfflineStatus();
    const handler = () => {
      void refreshOfflineStatus();
    };
    window.addEventListener(OFFLINE_STORE_EVENT, handler);
    return () => window.removeEventListener(OFFLINE_STORE_EVENT, handler);
  }, []);

  return (
    <header className="sticky top-0 z-10 border-b border-white/70 bg-white/80 backdrop-blur">
      <div className="page-shell flex flex-col gap-4 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-brand-teal">UCMB HMIS 105 Platform</p>
          <h2 className="mt-1 text-2xl font-bold text-brand-text">{currentTitle}</h2>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Badge tone={isOnline ? "success" : "warning"} className="gap-1 rounded-xl px-3 py-2 text-sm">
            {isOnline ? <Wifi size={14} /> : <WifiOff size={14} />}
            {isOnline ? "Online" : "Offline"}
          </Badge>
          <Badge
            tone={failedSyncCount > 0 ? "warning" : pendingSyncCount > 0 ? "info" : "success"}
            className="gap-1 rounded-xl px-3 py-2 text-sm"
          >
            <ShieldCheck size={14} />
            {failedSyncCount > 0
              ? `${failedSyncCount} sync issue${failedSyncCount === 1 ? "" : "s"}`
              : pendingSyncCount > 0
                ? `${pendingSyncCount} pending sync`
                : "Sync clear"}
          </Badge>
          <button className="rounded-2xl border border-brand-border bg-white p-3 text-brand-muted shadow-sm transition hover:text-brand-text">
            <Bell size={18} />
          </button>
          <div className="flex items-center gap-3 rounded-2xl border border-brand-border bg-white px-3 py-2 shadow-sm">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-navy text-sm font-bold text-white">
              {(user?.full_name ?? "U")
                .split(" ")
                .map((part) => part[0])
                .join("")
                .slice(0, 2)
                .toUpperCase()}
            </div>
            <div>
              <p className="text-sm font-semibold text-brand-text">{user?.full_name ?? "Authenticated user"}</p>
              <p className="text-xs text-brand-muted">{user?.role ?? "Unknown role"}</p>
            </div>
          </div>
          <Button variant="secondary" className="gap-2" onClick={() => void logout()}>
            <LogOut size={16} />
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
