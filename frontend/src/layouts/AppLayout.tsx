import type { ReactNode } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "../components/navigation/Sidebar";
import { Topbar } from "../components/navigation/Topbar";
import { useAuth } from "../hooks/useAuth";

export function AppLayout({ children }: { children?: ReactNode }) {
  const { loading } = useAuth();

  if (loading) {
    return (
      <div className="page-shell flex min-h-screen items-center justify-center">
        <div className="rounded-2xl border border-brand-border bg-white px-6 py-5 text-sm text-brand-muted shadow-soft">
          Loading UCMB HMIS 105 DQA Platform...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen lg:flex">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <Topbar />
        <main className="page-shell">{children ?? <Outlet />}</main>
      </div>
    </div>
  );
}
