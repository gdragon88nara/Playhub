"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { chatApi, DirectThread } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function MessagesPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [threads, setThreads] = useState<DirectThread[] | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push("/login");
      return;
    }
    chatApi.threads().then(setThreads).catch(() => setThreads([]));
  }, [user, loading, router]);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Messages</h1>
      {threads === null ? (
        <p className="text-neutral-500">Loading…</p>
      ) : threads.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-neutral-700 p-10 text-center text-neutral-500">
          No conversations yet. Open someone&apos;s profile and press Message.
        </div>
      ) : (
        <ul className="divide-y divide-neutral-800 rounded-2xl border border-neutral-800 bg-neutral-900">
          {threads.map((t) => (
            <li key={t.id}>
              <Link href={`/messages/${t.id}`} className="flex items-center gap-3 p-4 hover:bg-neutral-800/50">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-indigo-500 text-sm font-semibold text-white">
                  {t.other.username.slice(0, 2).toUpperCase()}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-medium">@{t.other.username}</span>
                  <span className="block truncate text-sm text-neutral-500">
                    {t.last_message || "No messages yet"}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
