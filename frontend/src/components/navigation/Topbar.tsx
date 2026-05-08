import { Bell, LogOut, Moon, ShieldCheck, Sun, Wifi, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import {
  OFFLINE_STORE_EVENT,
  getFailedSyncCount,
  getPendingSyncCount,
} from "../../services/offlineStore";
import { notificationService } from "../../services/notificationService";
import type { ManagerNotification } from "../../types";
import { BrandLogo } from "../ui/BrandLogo";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

const pageTitles: Record<string, string> = {
  "/dashboard": "Operational Data Quality Dashboard",
  "/assessment-rounds": "Assessment Rounds",
  "/assessment-facilities": "Assessment Workspace Review",
  "/submissions": "Submissions",
  "/my-assessments": "My Assessments",
  "/reports": "Generated Report",
  "/analytics": "Analytics",
  "/assessment-results": "Assessment Results",
  "/facility-dqa": "Facility DQA Profile",
  "/indicator-analytics": "Indicator Analytics",
  "/corrective-actions": "Corrective Actions",
  "/settings": "Settings",
};

function relativeTime(value: string) {
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) {
    return "";
  }
  const seconds = Math.max(Math.round((Date.now() - timestamp) / 1000), 0);
  if (seconds < 60) return "Just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return new Date(value).toLocaleDateString();
}

export function Topbar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { isOnline } = useNetworkStatus();
  const [pendingSyncCount, setPendingSyncCount] = useState(0);
  const [failedSyncCount, setFailedSyncCount] = useState(0);
  const [notifications, setNotifications] = useState<ManagerNotification[]>([]);
  const [openPanelNotifications, setOpenPanelNotifications] = useState<ManagerNotification[]>([]);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
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

  useEffect(() => {
    if (user?.role !== "MANAGER") {
      setNotifications([]);
      return;
    }

    const refreshNotifications = async () => {
      const data = await notificationService.listManagerNotifications(12).catch(() => []);
      setNotifications(data);
    };

    void refreshNotifications();
    const intervalId = window.setInterval(() => {
      void refreshNotifications();
    }, 30000);
    return () => window.clearInterval(intervalId);
  }, [user?.role]);

  const handleNotificationBellClick = () => {
    if (notificationsOpen) {
      setNotificationsOpen(false);
      setOpenPanelNotifications([]);
      return;
    }

    const notificationsToShow = notifications;
    if (notificationsToShow.length === 0) {
      setNotificationsOpen(false);
      setOpenPanelNotifications([]);
      return;
    }

    setOpenPanelNotifications(notificationsToShow);
    setNotificationsOpen(true);
    setNotifications([]);
    void notificationService
      .markManagerNotificationsSeen(notificationsToShow.map((item) => item.id))
      .catch(() => undefined);
  };

  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-brand-navy text-white shadow-panel">
      <div className="page-shell flex flex-col gap-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-4">
          <BrandLogo className="rounded-[20px] px-2 py-1.5 shadow-none" imageClassName="w-[150px]" />
          <div>
            <p className="text-[10px] uppercase tracking-[0.26em] text-emerald-200">UCMB HMIS 105 Platform</p>
            <h2 className="mt-1 font-display text-2xl font-semibold text-white">{currentTitle}</h2>
          </div>
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
          <Button
            variant="secondary"
            className="border-white/15 bg-white/10 text-white hover:bg-white/20"
            onClick={toggleTheme}
          >
            {theme === "day" ? <Moon size={16} /> : <Sun size={16} />}
            {theme === "day" ? "Night mode" : "Day mode"}
          </Button>
          {user?.role === "MANAGER" ? (
            <div className="relative">
              <button
                type="button"
                className="relative rounded-2xl border border-white/10 bg-white/10 p-3 text-white/75 shadow-sm transition hover:bg-white/20 hover:text-white"
                onClick={handleNotificationBellClick}
                aria-label="Manager notifications"
              >
                <Bell size={18} />
                {notifications.length > 0 ? (
                  <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-brand-danger px-1 text-[10px] font-bold text-white">
                    {Math.min(notifications.length, 9)}
                  </span>
                ) : null}
              </button>
              {notificationsOpen ? (
                <div className="absolute right-0 top-14 z-50 w-[min(360px,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-brand-border bg-white text-brand-text shadow-panel">
                  <div className="border-b border-brand-border bg-brand-surface px-4 py-3">
                    <p className="text-sm font-bold text-brand-navy">Assessor activity</p>
                    <p className="mt-1 text-xs text-brand-muted">New assessor updates. Opening this panel marks them as seen.</p>
                  </div>
                  <div className="max-h-96 overflow-y-auto">
                    {openPanelNotifications.length === 0 ? (
                      <p className="px-4 py-5 text-sm text-brand-muted">No new assessor activity.</p>
                    ) : (
                      openPanelNotifications.map((item) => (
                        <Link
                          key={item.id}
                          to={item.entity_id ? `/assessment-facilities/${item.entity_id}/workspace` : "/submissions"}
                          className="block border-b border-brand-border px-4 py-3 transition hover:bg-brand-surface"
                          onClick={() => setNotificationsOpen(false)}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <p className="text-sm font-semibold text-brand-text">{item.title}</p>
                            <span className="shrink-0 text-[11px] text-brand-muted">{relativeTime(item.created_at)}</span>
                          </div>
                          <p className="mt-1 text-xs text-brand-muted">{item.message}</p>
                        </Link>
                      ))
                    )}
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
          <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/8 px-3 py-2 shadow-sm">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-teal text-sm font-bold text-white">
              {(user?.full_name ?? "U")
                .split(" ")
                .map((part) => part[0])
                .join("")
                .slice(0, 2)
                .toUpperCase()}
            </div>
            <div>
              <p className="text-sm font-semibold text-white">{user?.full_name ?? "Authenticated user"}</p>
              <p className="text-xs text-white/60">{user?.role ?? "Unknown role"}</p>
            </div>
          </div>
          <Button variant="secondary" className="border-white/15 bg-white/10 text-white hover:bg-white/20" onClick={() => void logout()}>
            <LogOut size={16} />
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
