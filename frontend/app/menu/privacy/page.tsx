"use client";

import { useState } from "react";
import { meApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function PrivacyPage() {
  const { user, refreshMe } = useAuth();
  const [busy, setBusy] = useState(false);

  async function setPrivate(isPrivate: boolean) {
    setBusy(true);
    try {
      await meApi.update({ is_private: isPrivate });
      await refreshMe();
    } finally {
      setBusy(false);
    }
  }

  if (!user) return null;

  return (
    <>
      <h1 className="text-xl font-bold">계정 공개 범위</h1>
      <div className="space-y-3">
        <Option
          active={!user.is_private}
          disabled={busy}
          onClick={() => setPrivate(false)}
          title="공개 계정"
          desc="누구나 내 게임과 게시물을 보고 팔로우할 수 있습니다."
        />
        <Option
          active={user.is_private}
          disabled={busy}
          onClick={() => setPrivate(true)}
          title="비공개 계정"
          desc="승인한 팔로워만 내 콘텐츠를 볼 수 있습니다. 팔로우는 요청 후 승인이 필요합니다."
        />
      </div>
      <p className="text-xs text-neutral-500">
        게시물마다 별도로 공개 범위(공개 / 팔로워 전용 / 나만 보기)를 지정할 수도 있습니다.
      </p>
    </>
  );
}

function Option({ active, disabled, onClick, title, desc }: {
  active: boolean; disabled: boolean; onClick: () => void; title: string; desc: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`block w-full rounded-2xl border p-4 text-left disabled:opacity-60 ${
        active ? "border-indigo-500 bg-indigo-500/10" : "border-neutral-800 bg-neutral-900 hover:bg-neutral-800/50"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="font-medium">{title}</span>
        {active && <span className="text-xs text-indigo-400">● 사용 중</span>}
      </div>
      <p className="mt-1 text-sm text-neutral-400">{desc}</p>
    </button>
  );
}
