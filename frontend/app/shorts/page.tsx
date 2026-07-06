"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { shortsApi, Short, PostVisibility, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ShortCard } from "@/components/ShortCard";

export default function ShortsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [shorts, setShorts] = useState<Short[] | null>(null);
  const [open, setOpen] = useState(false);

  // composer
  const [caption, setCaption] = useState("");
  const [visibility, setVisibility] = useState<PostVisibility>("public");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    setShorts(null);
    setShorts(await shortsApi.list());
  }

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push("/login");
      return;
    }
    load().catch(() => setShorts([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, loading]);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Choose a video.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await shortsApi.create(caption.trim(), visibility, file);
      setCaption("");
      if (fileRef.current) fileRef.current.value = "";
      setOpen(false);
      await load();
    } catch (err) {
      if (err instanceof ApiError && err.data && typeof err.data === "object") {
        const first = Object.values(err.data as Record<string, string[]>)[0];
        setError(Array.isArray(first) ? first[0] : String(first));
      } else {
        setError("Upload failed.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Shorts</h1>
        <button
          onClick={() => setOpen((v) => !v)}
          className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600"
        >
          {open ? "Close" : "Upload short"}
        </button>
      </div>

      {open && (
        <form onSubmit={upload} className="rounded-2xl border border-neutral-800 bg-neutral-900 p-4 space-y-3">
          <input
            ref={fileRef}
            type="file"
            accept="video/*"
            className="text-sm"
          />
          <textarea
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            placeholder="Caption…"
            rows={2}
            className="w-full resize-none rounded-lg border border-neutral-700 bg-transparent px-3 py-2 text-sm outline-none focus:border-indigo-500"
          />
          <div className="flex items-center gap-3">
            <select
              value={visibility}
              onChange={(e) => setVisibility(e.target.value as PostVisibility)}
              className="rounded-lg border border-neutral-700 bg-transparent px-2 py-1.5 text-sm"
            >
              <option value="public">Public</option>
              <option value="followers">Followers</option>
              <option value="private">Private</option>
            </select>
            <button
              disabled={busy}
              className="ml-auto rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {busy ? "Uploading…" : "Post short"}
            </button>
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
        </form>
      )}

      {shorts === null ? (
        <p className="text-neutral-500">Loading…</p>
      ) : shorts.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-neutral-700 p-10 text-center text-neutral-500">
          No shorts yet. Upload the first one.
        </div>
      ) : (
        <div className="space-y-6">
          {shorts.map((s) => (
            <ShortCard key={s.id} short={s} />
          ))}
        </div>
      )}
    </div>
  );
}
