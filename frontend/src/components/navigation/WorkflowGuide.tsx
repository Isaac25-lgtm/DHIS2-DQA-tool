import { X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { Button } from "../ui/Button";

function messageFor(role: string | undefined, path: string) {
  if (role === "MANAGER") {
    if (path.startsWith("/submissions")) {
      return "Review submitted assessments here first: select the round, open a facility submission, refresh analysis if needed, then download Excel.";
    }
    if (path.startsWith("/assessment-rounds")) {
      return "Set up work here: import DHIS2 facilities and indicators first, create an assessment, assign teams, then publish.";
    }
    if (path.startsWith("/facilities")) {
      return "Start by searching DHIS2 and importing facilities you will assess. Imported facilities remain available later if the network is weak.";
    }
    if (path.startsWith("/indicators")) {
      return "Search DHIS2 HMIS 105 data elements and import only mapped indicators that should appear in assessments.";
    }
    if (path.startsWith("/reports")) {
      return "Generate formal reports after submissions have been analyzed and reviewed.";
    }
    return "Manager flow: import DHIS2 facilities and indicators, create an assessment, assign teams, then review submitted data in Submissions.";
  }
  if (role === "ASSESSOR") {
    if (path.startsWith("/my-assessments/")) {
      return "Enter register and HMIS 105 values, save locally as you work, sync with DHIS2 when online, then Send to Manager.";
    }
    return "Open My Assessments, choose your assigned facility, and work from the cached assessment package if the network drops.";
  }
  if (role === "REVIEWER") {
    return "Reviewer flow: inspect submissions, run or refresh analysis, review corrective actions, and support final reporting.";
  }
  if (role === "VIEWER") {
    return "Viewer flow: use approved reports and summary analytics only. This role is read-only.";
  }
  return null;
}

export function WorkflowGuide() {
  const { user } = useAuth();
  const location = useLocation();
  const [visible, setVisible] = useState(false);

  const message = useMemo(() => messageFor(user?.role, location.pathname), [location.pathname, user?.role]);
  const storageKey = `ucmb-guide:${user?.role ?? "guest"}:${location.pathname.split("/").slice(0, 3).join("/")}`;

  useEffect(() => {
    if (!message || window.localStorage.getItem(storageKey) === "dismissed") {
      setVisible(false);
      return;
    }
    setVisible(true);
    const timer = window.setTimeout(() => setVisible(false), 12000);
    return () => window.clearTimeout(timer);
  }, [message, storageKey]);

  if (!message || !visible) {
    return null;
  }

  return (
    <div className="mb-5 rounded-2xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm text-brand-navy shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <p>{message}</p>
        <Button
          variant="ghost"
          className="shrink-0 px-2 py-1"
          onClick={() => {
            window.localStorage.setItem(storageKey, "dismissed");
            setVisible(false);
          }}
        >
          <X size={16} />
        </Button>
      </div>
    </div>
  );
}
