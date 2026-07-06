"use client";

import { useEffect, useState } from "react";
import { meApi, ActivitySummary } from "@/lib/api";

const CARDS: { key: keyof ActivitySummary; label: string }[] = [
  { key: "games", label: "내 게임" },
  { key: "posts", label: "내 게시물" },
  { key: "comments", label: "작성한 댓글" },
  { key: "likes_given", label: "누른 좋아요" },
  { key: "likes_received", label: "받은 좋아요" },
  { key: "followers", label: "팔로워" },
  { key: "following", label: "팔로잉" },
];

export default function ActivityPage() {
  const [a, setA] = useState<ActivitySummary | null>(null);

  useEffect(() => {
    meApi.activity().then(setA).catch(() => setA(null));
  }, []);

  return (
    <>
      <h1 className="text-xl font-bold">나의 활동</h1>
      {!a ? (
        <p className="text-neutral-500">Loading…</p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {CARDS.map((c) => (
            <div key={c.key} className="rounded-2xl border border-neutral-800 bg-neutral-900 p-4">
              <div className="text-2xl font-bold">{a[c.key] as number}</div>
              <div className="mt-1 text-xs text-neutral-500">{c.label}</div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
