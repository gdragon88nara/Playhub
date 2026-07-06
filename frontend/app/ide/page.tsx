"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ideApi, ProjectSummary } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function IdeHome() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [templates, setTemplates] = useState<{ id: string; label: string }[]>([]);
  const [name, setName] = useState("");
  const [template, setTemplate] = useState("html_game");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push("/login");
      return;
    }
    ideApi.projects().then(setProjects).catch(() => setProjects([]));
    ideApi.templates().then(setTemplates).catch(() => {});
  }, [user, loading, router]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      const p = await ideApi.create(name.trim(), template);
      router.push(`/ide/${p.slug}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Developer IDE</h1>

      <form onSubmit={create} className="rounded-2xl border border-neutral-800 bg-neutral-900 p-4 space-y-3">
        <p className="text-sm text-neutral-400">
          New project. Files are named <code className="text-neutral-200">name.ext</code>; the
          extension sets the language mark. Default config code is added for you.
        </p>
        <div className="flex flex-wrap gap-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Project name"
            className="flex-1 min-w-40 rounded-lg border border-neutral-700 bg-transparent px-3 py-2 text-sm outline-none focus:border-indigo-500"
          />
          <select
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
            className="rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
          >
            {templates.map((t) => (
              <option key={t.id} value={t.id}>{t.label}</option>
            ))}
          </select>
          <button
            disabled={busy || !name.trim()}
            className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            Create
          </button>
        </div>
      </form>

      <div className="space-y-2">
        <h2 className="font-semibold">Your projects</h2>
        {projects === null ? (
          <p className="text-neutral-500">Loading…</p>
        ) : projects.length === 0 ? (
          <p className="text-sm text-neutral-500">No projects yet.</p>
        ) : (
          <ul className="divide-y divide-neutral-800 rounded-2xl border border-neutral-800 bg-neutral-900">
            {projects.map((p) => (
              <li key={p.id}>
                <Link href={`/ide/${p.slug}`} className="flex items-center justify-between p-4 hover:bg-neutral-800/50">
                  <span>
                    <span className="font-medium">{p.name}</span>
                    <span className="ml-2 rounded-full bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400">{p.kind}</span>
                  </span>
                  {p.deployed_slug && (
                    <span className="text-xs text-emerald-400">deployed</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
