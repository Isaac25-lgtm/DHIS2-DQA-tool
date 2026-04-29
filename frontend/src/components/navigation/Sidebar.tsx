import {
  ActivitySquare,
  ClipboardList,
  ClipboardX,
  ClipboardCheck,
  Gauge,
  PackageCheck,
  Settings,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { hasAnyRole } from "../../lib/auth";
import { cn } from "../../lib/cn";
import type { UserRole } from "../../types";
import { BrandLogo } from "../ui/BrandLogo";

interface NavItem {
  to: string;
  label: string;
  icon: typeof Gauge;
  roles: UserRole[];
}

const navItems: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: Gauge, roles: ["MANAGER", "ASSESSOR", "REVIEWER", "VIEWER"] },
  { to: "/assessment-rounds", label: "Assessments", icon: ClipboardList, roles: ["MANAGER", "REVIEWER"] },
  { to: "/submissions", label: "Submissions", icon: ClipboardCheck, roles: ["MANAGER", "REVIEWER"] },
  { to: "/analytics", label: "Analytics", icon: ActivitySquare, roles: ["REVIEWER", "VIEWER"] },
  { to: "/corrective-actions", label: "Corrective Actions", icon: ClipboardX, roles: ["REVIEWER"] },
  { to: "/my-assessments", label: "My Assessments", icon: PackageCheck, roles: ["ASSESSOR"] },
  { to: "/settings", label: "Settings", icon: Settings, roles: ["MANAGER", "ASSESSOR", "REVIEWER"] },
];

export function Sidebar() {
  const { user } = useAuth();
  const allowedNavItems = navItems.filter((item) => hasAnyRole(user?.role, item.roles));

  return (
    <aside className="border-b border-white/10 bg-brand-blue text-white shadow-panel lg:sticky lg:top-0 lg:min-h-screen lg:w-64 lg:border-b-0 lg:border-r lg:border-white/10">
      <div className="px-5 py-5 lg:px-6">
        <BrandLogo className="w-full rounded-[26px] p-3" imageClassName="w-full max-w-[210px]" />
        <div className="mt-3">
          <p className="text-[10px] uppercase tracking-[0.28em] text-emerald-200">Uganda Catholic Medical Bureau</p>
          <h1 className="mt-1 text-base font-bold text-white">HMIS 105 DQA Platform</h1>
        </div>
      </div>

      <nav className="flex gap-2 overflow-x-auto px-4 pb-4 lg:flex-col lg:overflow-visible lg:px-5">
        {allowedNavItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/dashboard"}
            className={({ isActive }) =>
              cn(
                "inline-flex min-w-fit items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold transition",
                isActive
                  ? "bg-brand-teal text-white shadow-soft"
                  : "text-white/68 hover:bg-white/10 hover:text-white",
              )
            }
          >
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="hidden px-5 pb-5 pt-3 lg:block">
        <div className="rounded-[18px] border border-white/10 bg-white/5 px-4 py-3">
          <p className="text-[10px] uppercase tracking-[0.24em] text-white/45">Role</p>
          <p className="mt-1 text-sm font-semibold text-white">{user?.role ?? "Authenticated"}</p>
          <p className="mt-3 text-[10px] uppercase tracking-[0.24em] text-white/45">Organisation</p>
          <p className="mt-1 text-sm font-semibold text-emerald-100">UCMB</p>
        </div>
      </div>
    </aside>
  );
}
