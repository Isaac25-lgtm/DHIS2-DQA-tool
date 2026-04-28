import {
  ActivitySquare,
  Building2,
  ClipboardList,
  ClipboardX,
  FileSpreadsheet,
  Gauge,
  Layers3,
  PackageCheck,
  Settings,
  Users,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { hasAnyRole } from "../../lib/auth";
import { cn } from "../../lib/cn";
import type { UserRole } from "../../types";

interface NavItem {
  to: string;
  label: string;
  icon: typeof Gauge;
  roles: UserRole[];
}

const navItems: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: Gauge, roles: ["MANAGER", "ASSESSOR", "REVIEWER", "VIEWER"] },
  { to: "/users", label: "Users", icon: Users, roles: ["MANAGER"] },
  { to: "/facilities", label: "Facilities", icon: Building2, roles: ["MANAGER"] },
  { to: "/indicators", label: "Indicator Library", icon: Layers3, roles: ["MANAGER"] },
  { to: "/assessment-rounds", label: "Assessments", icon: ClipboardList, roles: ["MANAGER", "REVIEWER"] },
  { to: "/analytics", label: "Analytics", icon: ActivitySquare, roles: ["MANAGER", "REVIEWER", "VIEWER"] },
  { to: "/corrective-actions", label: "Corrective Actions", icon: ClipboardX, roles: ["MANAGER", "REVIEWER"] },
  { to: "/my-assessments", label: "My Assessments", icon: PackageCheck, roles: ["ASSESSOR"] },
  { to: "/reports", label: "Reports", icon: FileSpreadsheet, roles: ["MANAGER", "REVIEWER"] },
  { to: "/reports", label: "Approved Reports", icon: FileSpreadsheet, roles: ["VIEWER"] },
  { to: "/settings", label: "Settings", icon: Settings, roles: ["MANAGER", "ASSESSOR", "REVIEWER"] },
];

export function Sidebar() {
  const { user } = useAuth();
  const allowedNavItems = navItems.filter((item) => hasAnyRole(user?.role, item.roles));

  return (
    <aside className="glass-panel border-b border-white/70 lg:min-h-screen lg:w-72 lg:border-b-0 lg:border-r">
      <div className="flex items-center gap-3 px-5 py-5 lg:px-6">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-navy text-white shadow-panel">
          <span className="text-sm font-extrabold tracking-[0.2em]">UC</span>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-brand-teal">UCMB Analytics</p>
          <h1 className="text-base font-bold text-brand-text">HMIS 105 DQA</h1>
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
                  : "text-brand-muted hover:bg-white hover:text-brand-text",
              )
            }
          >
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
