"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { meApi, MyComment } from "@/lib/api";

export default function MyCommentsPage() {
  const [items, setItems] = useState<MyComment[] | null>(null);

  useEffect(() => {
    meApi.comments().then(setItems).catch(() => setItems([]));
  }, []);

  return (
    <>
      <h1 className="text-xl font-bold">내 댓글</h1>
      {!items ? (
        <p className="text-neutral-500">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-neutral-500">작성한 댓글이 없습니다.</p>
      ) : (
        <ul className="divide-y divide-neutral-800 rounded-2xl border border-neutral-800 bg-neutral-900">
          {items.map((c) => (
            <li key={c.id} className="p-4">
              <Link href={c.url} className="block hover:opacity-90">
                <span className="mb-1 flex items-center gap-2 text-xs text-neutral-500">
                  <span className={`rounded px-1.5 py-0.5 ${c.kind === "game" ? "bg-indigo-500/15 text-indigo-400" : "bg-emerald-500/15 text-emerald-400"}`}>
                    {c.kind === "game" ? "게임" : "게시물"}
                  </span>
                  <span className="truncate">{c.target}</span>
                  <span>· {new Date(c.created_at).toLocaleDateString()}</span>
                </span>
                <span className="text-sm text-neutral-200">{c.body}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
