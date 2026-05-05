import {
  ActivitySquare,
  Building2,
  ClipboardCheck,
  ClipboardList,
  ClipboardX,
  FileText,
  Gauge,
  ListChecks,
  PackageCheck,
  Settings,
  Users,
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

interface NavSection {
  heading: string;
  roles: UserRole[];
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    heading: "Manager",
    roles: ["MANAGER"],
    items: [
      { to: "/dashboard", label: "Dashboard", icon: Gauge, roles: ["MANAGER"] },
      { to: "/assessment-rounds", label: "Assessments", icon: ClipboardList, roles: ["MANAGER"] },
      { to: "/facilities", label: "Facilities", icon: Building2, roles: ["MANAGER"] },
      { to: "/indicators", label: "Indicators", icon: ListChecks, roles: ["MANAGER"] },
      { to: "/submissions", label: "Submissions", icon: ClipboardCheck, roles: ["MANAGER"] },
      { to: "/analytics", label: "Analytics", icon: ActivitySquare, roles: ["MANAGER"] },
      { to: "/corrective-actions", label: "Corrective Actions", icon: ClipboardX, roles: ["MANAGER"] },
      { to: "/reports", label: "Reports", icon: FileText, roles: ["MANAGER"] },
      { to: "/users", label: "Users", icon: Users, roles: ["MANAGER"] },
      { to: "/settings", label: "Settings", icon: Settings, roles: ["MANAGER"] },
    ],
  },
  {
    heading: "Assessor",
    roles: ["ASSESSOR"],
    items: [
      { to: "/dashboard", label: "Dashboard", icon: Gauge, roles: ["ASSESSOR"] },
      { to: "/my-assessments", label: "My Assessments", icon: PackageCheck, roles: ["ASSESSOR"] },
      { to: "/settings", label: "Settings", icon: Settings, roles: ["ASSESSOR"] },
    ],
  },
];

export function Sidebar() {
  const { user } = useAuth();
  const visibleSections = navSections
    .filter((section) => hasAnyRole(user?.role, section.roles))
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => hasAnyRole(user?.role, item.roles)),
    }))
    .filter((section) => section.items.length > 0);

  return (
    <aside className="border-b border-white/10 bg-brand-blue text-white shadow-panel lg:sticky lg:top-0 lg:min-h-screen lg:w-64 lg:border-b-0 lg:border-r lg:border-white/10">
      <div className="px-5 py-5 lg:px-6">
        <BrandLogo className="w-full rounded-[26px] p-3" imageClassName="w-full max-w-[210px]" />
        <div className="mt-3">
          <p className="text-[10px] uppercase tracking-[0.28em] text-emerald-200">Uganda Catholic Medical Bureau</p>
          <h1 className="mt-1 text-base font-bold text-white">HMIS 105 DQA Platform</h1>
        </div>
      </div>

      <nav className="flex flex-col gap-4 px-4 pb-4 lg:px-5">
        {visibleSections.map((section) => (
          <div key={section.heading} className="flex flex-col gap-2">
            <p className="px-2 text-[10px] uppercase tracking-[0.28em] text-white/55">{section.heading}</p>
            <div className="flex gap-2 overflow-x-auto lg:flex-col lg:overflow-visible">
              {section.items.map(({ to, label, icon: Icon }) => (
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
            </div>
          </div>
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
