"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError(
        err instanceof ApiError ? "Invalid email or password." : "Something went wrong.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-6">
        <h1 className="text-xl font-bold">Log in</h1>
        <form onSubmit={onSubmit} className="mt-4 space-y-3">
          <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" />
          <Field label="Password" type="password" value={password} onChange={setPassword} autoComplete="current-password" />
          {error && <p className="text-sm text-red-500">{error}</p>}
          <button
            disabled={busy}
            className="w-full rounded-lg bg-indigo-500 px-4 py-2.5 font-medium text-white hover:bg-indigo-600 disabled:opacity-50"
          >
            {busy ? "…" : "Log in"}
          </button>
        </form>
      </div>
      <p className="mt-4 text-center text-sm text-neutral-500">
        No account?{" "}
        <Link href="/register" className="font-medium text-indigo-500">
          Sign up
        </Link>
      </p>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  autoComplete?: string;
}) {
  return (
    <label className="block">
      <span className="text-sm text-neutral-500">{label}</span>
      <input
        type={type}
        value={value}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 outline-none focus:border-indigo-500"
        required
      />
    </label>
  );
}
