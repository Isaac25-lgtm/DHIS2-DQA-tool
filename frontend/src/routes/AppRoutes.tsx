import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { AppLayout } from "../layouts/AppLayout";
import { AnalyticsDashboardPage } from "../pages/AnalyticsDashboardPage";
import { useAuth } from "../hooks/useAuth";
import { hasAnyRole } from "../lib/auth";
import { AssessmentRoundBuilderPage } from "../pages/AssessmentRoundBuilderPage";
import { AssessmentRoundDetailPage } from "../pages/AssessmentRoundDetailPage";
import { AssessmentRoundsPage } from "../pages/AssessmentRoundsPage";
import { AssessmentResultsPage } from "../pages/AssessmentResultsPage";
import { AssessmentWorkspacePage } from "../pages/AssessmentWorkspacePage";
import { CorrectiveActionsPage } from "../pages/CorrectiveActionsPage";
import { DashboardPage } from "../pages/DashboardPage";
import { FacilityDqaProfilePage } from "../pages/FacilityDqaProfilePage";
import { FacilitiesPage } from "../pages/FacilitiesPage";
import { IndicatorLibraryPage } from "../pages/IndicatorLibraryPage";
import { IndicatorAnalyticsPage } from "../pages/IndicatorAnalyticsPage";
import { LoginPage } from "../pages/LoginPage";
import { MyAssessmentsPage } from "../pages/MyAssessmentsPage";
import { ReportDetailPage } from "../pages/ReportDetailPage";
import { ReportGeneratorPage } from "../pages/ReportGeneratorPage";
import { ReportsPage } from "../pages/ReportsPage";
import { SettingsPage } from "../pages/SettingsPage";
import { UserManagementPage } from "../pages/UserManagementPage";
import type { UserRole } from "../types";

function ProtectedOutlet() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="page-shell flex min-h-screen items-center justify-center">
        <div className="rounded-2xl border border-brand-border bg-white px-6 py-5 text-sm text-brand-muted shadow-soft">
          Restoring your secure session...
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <AppLayout>
      <Outlet />
    </AppLayout>
  );
}

function RoleRoute({ allowedRoles }: { allowedRoles: UserRole[] }) {
  const { user } = useAuth();
  if (!hasAnyRole(user?.role, allowedRoles)) {
    return <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedOutlet />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route element={<RoleRoute allowedRoles={["MANAGER"]} />}>
          <Route path="/users" element={<UserManagementPage />} />
        </Route>
        <Route element={<RoleRoute allowedRoles={["MANAGER", "REVIEWER"]} />}>
          <Route path="/facilities" element={<FacilitiesPage />} />
        </Route>
        <Route element={<RoleRoute allowedRoles={["MANAGER", "REVIEWER", "VIEWER"]} />}>
          <Route path="/indicators" element={<IndicatorLibraryPage />} />
        </Route>
        <Route element={<RoleRoute allowedRoles={["MANAGER", "REVIEWER"]} />}>
          <Route path="/assessment-rounds" element={<AssessmentRoundsPage />} />
          <Route path="/assessment-rounds/:id" element={<AssessmentRoundDetailPage />} />
          <Route path="/assessment-facilities/:assessmentFacilityId/workspace" element={<AssessmentWorkspacePage />} />
        </Route>
        <Route element={<RoleRoute allowedRoles={["MANAGER"]} />}>
          <Route path="/assessment-rounds/new" element={<AssessmentRoundBuilderPage />} />
        </Route>
        <Route element={<RoleRoute allowedRoles={["ASSESSOR"]} />}>
          <Route path="/my-assessments" element={<MyAssessmentsPage />} />
          <Route path="/my-assessments/:assessmentFacilityId" element={<AssessmentWorkspacePage />} />
        </Route>
        <Route element={<RoleRoute allowedRoles={["MANAGER", "REVIEWER", "VIEWER"]} />}>
          <Route path="/analytics" element={<AnalyticsDashboardPage />} />
          <Route path="/assessment-results/:assessmentFacilityId" element={<AssessmentResultsPage />} />
          <Route path="/facility-dqa/:assessmentFacilityId" element={<FacilityDqaProfilePage />} />
          <Route path="/indicator-analytics" element={<IndicatorAnalyticsPage />} />
        </Route>
        <Route element={<RoleRoute allowedRoles={["MANAGER", "REVIEWER", "ASSESSOR"]} />}>
          <Route path="/corrective-actions" element={<CorrectiveActionsPage />} />
        </Route>
        <Route element={<RoleRoute allowedRoles={["MANAGER", "REVIEWER", "VIEWER"]} />}>
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/reports/:reportId" element={<ReportDetailPage />} />
        </Route>
        <Route element={<RoleRoute allowedRoles={["MANAGER", "REVIEWER"]} />}>
          <Route path="/reports/generate" element={<ReportGeneratorPage />} />
        </Route>
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
