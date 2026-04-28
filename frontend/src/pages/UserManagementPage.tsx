import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Table } from "../components/ui/Table";
import { useAuth } from "../hooks/useAuth";
import { userService } from "../services/userService";
import type { User, UserFormPayload, UserRole } from "../types";

const emptyForm: UserFormPayload = {
  full_name: "",
  email: "",
  password: "",
  role: "ASSESSOR",
  is_active: true,
};

const roleOptions: UserRole[] = ["MANAGER", "ASSESSOR", "REVIEWER", "VIEWER"];

export function UserManagementPage() {
  const { user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [form, setForm] = useState<UserFormPayload>(emptyForm);
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await userService.listUsers();
      setUsers(data);
    } catch {
      setError("Unable to load users right now.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadUsers();
  }, []);

  const columns = useMemo<ColumnDef<User>[]>(
    () => [
      {
        accessorKey: "full_name",
        header: "Full name",
      },
      {
        accessorKey: "email",
        header: "Email",
      },
      {
        accessorKey: "role",
        header: "Role",
        cell: ({ row }) => <Badge tone="info">{row.original.role}</Badge>,
      },
      {
        accessorKey: "is_active",
        header: "Status",
        cell: ({ row }) => (
          <Badge tone={row.original.is_active ? "success" : "danger"}>
            {row.original.is_active ? "Active" : "Inactive"}
          </Badge>
        ),
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              className="px-3 py-2 text-xs"
              onClick={() => {
                setEditingUserId(row.original.id);
                setForm({
                  full_name: row.original.full_name,
                  email: row.original.email,
                  password: "",
                  role: row.original.role,
                  is_active: row.original.is_active,
                });
                setMessage(null);
                setError(null);
              }}
            >
              Edit
            </Button>
            {row.original.is_active ? (
              <Button
                variant="ghost"
                className="px-3 py-2 text-xs"
                onClick={async () => {
                  try {
                    await userService.deactivateUser(row.original.id);
                    setMessage("User deactivated.");
                    await loadUsers();
                  } catch {
                    setError("Unable to deactivate the user right now.");
                  }
                }}
              >
                Deactivate
              </Button>
            ) : (
              <Button
                variant="secondary"
                className="px-3 py-2 text-xs"
                onClick={async () => {
                  try {
                    await userService.activateUser(row.original.id);
                    setMessage("User activated.");
                    await loadUsers();
                  } catch {
                    setError("Unable to activate the user right now.");
                  }
                }}
              >
                Activate
              </Button>
            )}
          </div>
        ),
      },
    ],
    [],
  );

  const submitForm = async () => {
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const payload: UserFormPayload = {
        ...form,
        password: form.password?.trim() ? form.password : undefined,
      };
      if (editingUserId) {
        await userService.updateUser(editingUserId, payload);
        setMessage("User updated successfully.");
      } else {
        await userService.createUser(payload);
        setMessage("User created successfully.");
      }
      setForm(emptyForm);
      setEditingUserId(null);
      await loadUsers();
    } catch {
      setError("Unable to save the user. Check the form values and try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (user?.role !== "MANAGER") {
    return (
      <Card title="User Management" subtitle="Managers only">
        <p className="text-sm text-brand-muted">You do not have access to manage users.</p>
      </Card>
    );
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <Card title="Users" subtitle="Create and manage platform accounts and roles.">
        {error ? <p className="mb-4 text-sm text-brand-danger">{error}</p> : null}
        {message ? <p className="mb-4 text-sm text-brand-teal">{message}</p> : null}
        {loading ? (
          <div className="rounded-2xl border border-brand-border bg-brand-surface p-6 text-sm text-brand-muted">
            Loading users...
          </div>
        ) : (
          <Table data={users} columns={columns} emptyMessage="No users found yet." />
        )}
      </Card>

      <Card
        title={editingUserId ? "Edit User" : "Create User"}
        subtitle="Managers can add assessors, reviewers, viewers, and other managers."
      >
        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-semibold text-brand-text">Full name</label>
            <Input value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} />
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-brand-text">Email</label>
            <Input
              type="email"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-brand-text">
              Password {editingUserId ? "(leave blank to keep current)" : ""}
            </label>
            <Input
              type="password"
              value={form.password ?? ""}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-brand-text">Role</label>
            <Select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value as UserRole })}>
              {roleOptions.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex gap-2">
            <Button onClick={submitForm} disabled={submitting}>
              {submitting ? "Saving..." : editingUserId ? "Update user" : "Create user"}
            </Button>
            {editingUserId ? (
              <Button
                variant="secondary"
                onClick={() => {
                  setEditingUserId(null);
                  setForm(emptyForm);
                }}
              >
                Cancel edit
              </Button>
            ) : null}
          </div>
        </div>
      </Card>
    </div>
  );
}
