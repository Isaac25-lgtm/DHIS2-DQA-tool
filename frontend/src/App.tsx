import { useEffect } from "react";
import { AuthProvider } from "./hooks/useAuth";
import { ThemeProvider } from "./hooks/useTheme";
import { AppRoutes } from "./routes/AppRoutes";
import { initOfflineStore } from "./services/offlineStore";

export default function App() {
  useEffect(() => {
    void initOfflineStore().catch(() => undefined);
  }, []);

  return (
    <ThemeProvider>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ThemeProvider>
  );
}
