import { ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { useAuth } from "../hooks/useAuth";

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginPage() {
  const navigate = useNavigate();
  const { login, user, loading } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    defaultValues: {
      email: "admin@ucmb-dqa.local",
      password: "ChangeMe123!",
    },
  });

  useEffect(() => {
    if (!loading && user) {
      navigate("/dashboard", { replace: true });
    }
  }, [loading, user, navigate]);

  const onSubmit = async (values: LoginFormValues) => {
    const result = loginSchema.safeParse(values);
    if (!result.success) {
      return;
    }

    setSubmitting(true);
    setServerError(null);
    try {
      await login(result.data);
      navigate("/dashboard", { replace: true });
    } catch {
      setServerError("Unable to sign in. Check your email and password, then try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-hero-grid">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col justify-center gap-10 px-4 py-10 lg:flex-row lg:items-center">
        <div className="max-w-xl text-brand-text">
          <div className="inline-flex items-center gap-3 rounded-full border border-brand-border bg-white/80 px-4 py-2 text-sm text-brand-muted shadow-soft">
            <ShieldCheck size={18} className="text-brand-teal" />
            Lightweight modular monolith for UCMB HMIS 105 DQA
          </div>
          <h1 className="mt-6 text-4xl font-extrabold leading-tight text-brand-navy sm:text-5xl">
            Secure operations for facilities, round planning, and field-ready HMIS 105 DQA.
          </h1>
          <p className="mt-5 max-w-lg text-lg text-brand-muted">
            Manage assessment rounds, import DHIS2 facilities and data elements, and support field teams with online and offline DQA workspaces.
          </p>
        </div>

        <Card
          className="w-full max-w-md rounded-[28px] p-6 sm:p-8"
          title="Secure Sign In"
          subtitle="Use the seeded manager account from your environment variables or a manager-created user."
        >
          <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
            <div>
              <label className="mb-2 block text-sm font-semibold text-brand-text">Email</label>
              <Input {...register("email")} type="email" placeholder="admin@ucmb-dqa.local" />
              {errors.email ? <p className="mt-2 text-sm text-brand-danger">Enter a valid email address.</p> : null}
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-brand-text">Password</label>
              <Input {...register("password")} type="password" placeholder="********" />
              {errors.password ? (
                <p className="mt-2 text-sm text-brand-danger">Password must be at least 8 characters.</p>
              ) : null}
            </div>
            {serverError ? <p className="text-sm text-brand-danger">{serverError}</p> : null}
            <Button className="w-full" type="submit" disabled={submitting}>
              {submitting ? "Signing in..." : "Continue to platform"}
            </Button>
            <div className="rounded-2xl bg-brand-surface p-4 text-sm text-brand-muted">
              <p className="font-semibold text-brand-text">Default local manager</p>
              <p className="mt-1">Email: admin@ucmb-dqa.local</p>
              <p>Password: ChangeMe123!</p>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
