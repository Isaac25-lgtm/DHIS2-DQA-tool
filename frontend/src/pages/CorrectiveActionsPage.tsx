import { useEffect, useState } from "react";
import { CorrectiveActionForm } from "../components/corrective-actions/CorrectiveActionForm";
import { CorrectiveActionTable } from "../components/corrective-actions/CorrectiveActionTable";
import { Card } from "../components/ui/Card";
import { correctiveActionService } from "../services/correctiveActionService";
import { useAuth } from "../hooks/useAuth";
import type { CorrectiveAction, CorrectiveActionPayload } from "../types";

export function CorrectiveActionsPage() {
  const { user } = useAuth();
  const [actions, setActions] = useState<CorrectiveAction[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    setActions(await correctiveActionService.listActions());
  };

  useEffect(() => {
    void load();
  }, []);

  const managerLike = user?.role === "MANAGER" || user?.role === "REVIEWER";

  return (
    <div className="space-y-6">
      {managerLike ? (
        <CorrectiveActionForm
          onSubmit={async (payload: CorrectiveActionPayload) => {
            await correctiveActionService.createAction(payload);
            setMessage("Corrective action created.");
            await load();
          }}
        />
      ) : null}

      {message ? (
        <Card>
          <p className="text-sm text-brand-teal">{message}</p>
        </Card>
      ) : null}

      <Card title="Corrective Actions" subtitle="Track follow-up work and verification status for DQA issues.">
        <CorrectiveActionTable
          items={actions}
          onResolve={
            managerLike
              ? async (action) => {
                  await correctiveActionService.resolve(action.id, action.resolution_comment);
                  await load();
                }
              : undefined
          }
          onVerify={
            managerLike
              ? async (action) => {
                  await correctiveActionService.verify(action.id, action.verification_comment);
                  await load();
                }
              : undefined
          }
          onClose={
            user?.role === "MANAGER"
              ? async (action) => {
                  await correctiveActionService.close(action.id, action.manager_comment);
                  await load();
                }
              : undefined
          }
        />
      </Card>
    </div>
  );
}
