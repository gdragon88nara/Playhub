"use client";

import { useRef, useState } from "react";
import { meApi, mediaUrl, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function ProfilePage() {
  const { user, refreshMe } = useAuth();
  const fileRef = useRef<HTMLInputElement>(null);
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [bio, setBio] = useState(user?.bio ?? "");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    setMsg(null);
    try {
      await meApi.update({ display_name: displayName, bio });
      const file = fileRef.current?.files?.[0];
      if (file) await meApi.updateAvatar(file);
      await refreshMe();
      setMsg("저장되었습니다.");
    } catch (err) {
      setMsg(err instanceof ApiError ? "저장 실패: 입력을 확인해 주세요." : "저장 실패");
    } finally {
      setBusy(false);
    }
  }

  if (!user) return null;

  return (
    <>
      <h1 className="text-xl font-bold">프로필 수정</h1>
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-5 space-y-4">
        <div className="flex items-center gap-4">
          <span className="inline-flex h-16 w-16 items-center justify-center overflow-hidden rounded-full bg-indigo-500 text-lg font-semibold text-white">
            {user.avatar ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={mediaUrl(user.avatar) ?? undefined} alt="" className="h-full w-full object-cover" />
            ) : (
              user.username.slice(0, 2).toUpperCase()
            )}
          </span>
          <button
            onClick={() => fileRef.current?.click()}
            className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800"
          >
            아바타 변경
          </button>
          <input ref={fileRef} type="file" accept="image/*" hidden onChange={() => setMsg(null)} />
        </div>

        <label className="block">
          <span className="text-sm text-neutral-500">표시 이름</span>
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="mt-1 w-full rounded-lg border border-neutral-700 bg-transparent px-3 py-2 outline-none focus:border-indigo-500"
          />
        </label>

        <label className="block">
          <span className="text-sm text-neutral-500">소개</span>
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            rows={3}
            maxLength={200}
            className="mt-1 w-full rounded-lg border border-neutral-700 bg-transparent px-3 py-2 outline-none focus:border-indigo-500"
          />
        </label>

        <div className="flex items-center gap-3">
          <button
            onClick={save}
            disabled={busy}
            className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600 disabled:opacity-50"
          >
            {busy ? "저장 중…" : "저장"}
          </button>
          <span className="text-xs text-neutral-500">@{user.username}</span>
          {msg && <span className="text-sm text-emerald-400">{msg}</span>}
        </div>
      </div>
    </>
  );
}
