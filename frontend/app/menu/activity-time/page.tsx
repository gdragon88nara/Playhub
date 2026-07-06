"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

export default function ActivityTimePage() {
  const { user } = useAuth();
  // Time-derived values are computed after mount to keep render pure.
  const [clock, setClock] = useState<{ days: number; now: string } | null>(null);

  useEffect(() => {
    if (!user) return;
    const joined = new Date(user.date_joined).getTime();
    setClock({
      days: Math.max(0, Math.floor((Date.now() - joined) / 86400000)),
      now: new Date().toLocaleString(),
    });
  }, [user]);

  if (!user) return null;

  const joined = new Date(user.date_joined);
  const lastActive = user.last_active ? new Date(user.last_active) : null;

  return (
    <>
      <h1 className="text-xl font-bold">활동 시간</h1>
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900 divide-y divide-neutral-800">
        <Row label="가입일" value={joined.toLocaleString()} />
        <Row label="최근 접속" value={lastActive ? lastActive.toLocaleString() : "방금"} />
        <Row label="함께한 기간" value={clock ? `${clock.days}일` : "…"} />
        <Row label="현재 시각" value={clock ? clock.now : "…"} />
      </div>
      <p className="text-xs text-neutral-500">
        최근 접속은 프로필을 불러올 때마다 갱신됩니다.
      </p>
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between px-4 py-3 text-sm">
      <span className="text-neutral-500">{label}</span>
      <span className="text-neutral-100">{value}</span>
    </div>
  );
}
