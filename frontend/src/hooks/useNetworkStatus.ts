import { useEffect, useState } from "react";

export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState<boolean>(window.navigator.onLine);
  const [wasOffline, setWasOffline] = useState<boolean>(false);
  const [lastChangedAt, setLastChangedAt] = useState<string>(new Date().toISOString());

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setLastChangedAt(new Date().toISOString());
    };
    const handleOffline = () => {
      setIsOnline(false);
      setWasOffline(true);
      setLastChangedAt(new Date().toISOString());
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return { isOnline, wasOffline, lastChangedAt };
}
