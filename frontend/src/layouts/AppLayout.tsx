import type { ReactNode } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "../components/navigation/Sidebar";
import { Topbar } from "../components/navigation/Topbar";
import { WorkflowGuide } from "../components/navigation/WorkflowGuide";
import { BrandLogo } from "../components/ui/BrandLogo";
import { useAuth } from "../hooks/useAuth";

export function AppLayout({ children }: { children?: ReactNode }) {
  const { loading } = useAuth();

  if (loading) {
    return (
      <div className="page-shell flex min-h-screen items-center justify-center">
        <div className="flex max-w-md flex-col items-center gap-5 rounded-[28px] border border-brand-border bg-white px-6 py-7 text-center text-sm text-brand-muted shadow-soft">
          <BrandLogo className="rounded-[26px] px-4 py-3" imageClassName="w-full max-w-[280px]" />
          <div>
            <p className="font-semibold text-brand-text">Loading UCMB HMIS 105 DQA Platform...</p>
            <p className="mt-1">Preparing your workspace and assessment data.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen lg:flex">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <Topbar />
        <main className="page-shell">
          <WorkflowGuide />
          {children ?? <Outlet />}
        </main>
      </div>
    </div>
  );
}
