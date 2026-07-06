"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { authApi, ApiError } from "@/lib/api";

export default function RegisterPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    email: "",
    username: "",
    display_name: "",
    password: "",
    is_private: false,
    become_seller: false,
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function set<K extends keyof typeof form>(key: K, val: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: val }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await authApi.register(form);
      await login(form.email, form.password);
      router.push(form.become_seller ? "/" : "/");
    } catch (err) {
      if (err instanceof ApiError && err.data && typeof err.data === "object") {
        const first = Object.values(err.data as Record<string, string[]>)[0];
        setError(Array.isArray(first) ? first[0] : String(first));
      } else {
        setError("Something went wrong.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-6">
        <h1 className="text-xl font-bold">Create your account</h1>
        <form onSubmit={onSubmit} className="mt-4 space-y-3">
          <Field label="Email" type="email" value={form.email} onChange={(v) => set("email", v)} />
          <Field label="Username (@handle)" value={form.username} onChange={(v) => set("username", v)} />
          <Field label="Display name" value={form.display_name} onChange={(v) => set("display_name", v)} required={false} />
          <Field label="Password" type="password" value={form.password} onChange={(v) => set("password", v)} hint="At least 10 characters." />

          <Toggle
            label="Private account"
            desc="Only accepted followers can see your games & posts."
            checked={form.is_private}
            onChange={(v) => set("is_private", v)}
          />
          <Toggle
            label="Seller account"
            desc="Sell games. Payout details are collected later via a secure provider — never stored here."
            checked={form.become_seller}
            onChange={(v) => set("become_seller", v)}
          />

          {error && <p className="text-sm text-red-500">{error}</p>}
          <button
            disabled={busy}
            className="w-full rounded-lg bg-indigo-500 px-4 py-2.5 font-medium text-white hover:bg-indigo-600 disabled:opacity-50"
          >
            {busy ? "…" : "Sign up"}
          </button>
        </form>
      </div>
      <p className="mt-4 text-center text-sm text-neutral-500">
        Have an account?{" "}
        <Link href="/login" className="font-medium text-indigo-500">
          Log in
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
  required = true,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="text-sm text-neutral-500">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 outline-none focus:border-indigo-500"
        required={required}
      />
      {hint && <span className="text-xs text-neutral-400">{hint}</span>}
    </label>
  );
}

function Toggle({
  label,
  desc,
  checked,
  onChange,
}: {
  label: string;
  desc: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-3 rounded-lg border border-neutral-200 dark:border-neutral-800 p-3 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 h-4 w-4 accent-indigo-500"
      />
      <span>
        <span className="block text-sm font-medium">{label}</span>
        <span className="block text-xs text-neutral-500">{desc}</span>
      </span>
    </label>
  );
}
