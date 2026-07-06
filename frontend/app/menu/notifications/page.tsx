"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { meApi, Notification } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function NotificationsPage() {
  const { user, refreshMe } = useAuth();
  const [items, setItems] = useState<Notification[] | null>(null);

  useEffect(() => {
    meApi.notifications().then(setItems).catch(() => setItems([]));
  }, []);

  async function toggle(key: "notify_follows" | "notify_likes" | "notify_comments", value: boolean) {
    await meApi.update({ [key]: value });
    await refreshMe();
    setItems(await meApi.notifications());
  }

  if (!user) return null;

  return (
    <>
      <h1 className="text-xl font-bold">알림</h1>

      {/* 알림 세부 설정 */}
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-4">
        <p className="mb-3 text-sm font-medium text-neutral-300">알림 세부 설정</p>
        <div className="space-y-2 text-sm">
          <Toggle label="새 팔로워 / 팔로우 요청" checked={user.notify_follows} onChange={(v) => toggle("notify_follows", v)} />
          <Toggle label="좋아요" checked={user.notify_likes} onChange={(v) => toggle("notify_likes", v)} />
          <Toggle label="댓글" checked={user.notify_comments} onChange={(v) => toggle("notify_comments", v)} />
        </div>
      </div>

      {!items ? (
        <p className="text-neutral-500">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-neutral-500">새로운 알림이 없습니다.</p>
      ) : (
        <ul className="divide-y divide-neutral-800 rounded-2xl border border-neutral-800 bg-neutral-900">
          {items.map((n) => (
            <li key={n.id}>
              <Link href={n.url} className="flex items-start gap-3 p-4 hover:bg-neutral-800/50">
                <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-700 text-xs font-semibold">
                  {n.actor.username.slice(0, 2).toUpperCase()}
                </span>
                <span className="min-w-0 text-sm">
                  <span className="font-medium">@{n.actor.username}</span>{" "}
                  <span className="text-neutral-300">{n.text}</span>
                  <span className="mt-0.5 block text-xs text-neutral-500">{new Date(n.created_at).toLocaleString()}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center justify-between">
      <span className="text-neutral-300">{label}</span>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="h-4 w-4 accent-indigo-500" />
    </label>
  );
}
