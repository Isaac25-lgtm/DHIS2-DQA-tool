import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { dhis2Service } from "../services/dhis2Service";
import { useAuth } from "./useAuth";
import { useNetworkStatus } from "./useNetworkStatus";
import type { Dhis2ConnectionStatus, Dhis2Reachability } from "../types";

interface Dhis2StatusContextValue {
  status: Dhis2ConnectionStatus | null;
  reachability: Dhis2Reachability;
  signedIn: boolean;
  loading: boolean;
  lastCheckedAt: string | null;
  refresh: () => Promise<void>;
}

const Dhis2StatusContext = createContext<Dhis2StatusContextValue | null>(null);

const POLL_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export function Dhis2StatusProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { isOnline } = useNetworkStatus();
  const [status, setStatus] = useState<Dhis2ConnectionStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    if (!user || !isOnline) {
      return;
    }
    setLoading(true);
    try {
      const next = await dhis2Service.getConnectionStatus();
      setStatus(next);
    } catch {
      // Endpoint failed — treat as unreachable rather than crashing the UI
      setStatus((current) => current ?? {
        connected: false,
        signed_in: false,
        base_url: "",
        last_checked_at: new Date().toISOString(),
        message: "DHIS2 status check failed.",
        reachability: "unreachable",
      });
    } finally {
      setLoading(false);
    }
  }, [user, isOnline]);

  // Initial fetch + polling whenever the user is authenticated and online
  useEffect(() => {
    if (!user || !isOnline) {
      setStatus(null);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    void refresh();
    intervalRef.current = setInterval(() => void refresh(), POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [user, isOnline, refresh]);

  const value = useMemo<Dhis2StatusContextValue>(
    () => ({
      status,
      reachability: status?.reachability ?? (status ? (status.connected ? "reachable" : "unreachable") : "not_configured"),
      signedIn: Boolean(status?.signed_in),
      loading,
      lastCheckedAt: status?.last_checked_at ?? null,
      refresh,
    }),
    [status, loading, refresh],
  );

  return <Dhis2StatusContext.Provider value={value}>{children}</Dhis2StatusContext.Provider>;
}

export function useDhis2Status(): Dhis2StatusContextValue {
  const ctx = useContext(Dhis2StatusContext);
  if (!ctx) {
    throw new Error("useDhis2Status must be used within a Dhis2StatusProvider");
  }
  return ctx;
}
