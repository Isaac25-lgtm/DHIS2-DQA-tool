import { useEffect } from "react";
import { AuthProvider } from "./hooks/useAuth";
import { Dhis2StatusProvider } from "./hooks/useDhis2Status";
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
        <Dhis2StatusProvider>
          <AppRoutes />
        </Dhis2StatusProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
