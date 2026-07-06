"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { postsApi, Post, PostVisibility, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PostCard } from "@/components/PostCard";

export default function CommunityPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<"timeline" | "explore">("timeline");
  const [posts, setPosts] = useState<Post[] | null>(null);

  // composer
  const [body, setBody] = useState("");
  const [visibility, setVisibility] = useState<PostVisibility>("public");
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function load(which: "timeline" | "explore") {
    setPosts(null);
    const rows = await postsApi.list(which === "explore" ? { feed: "explore" } : {});
    setPosts(rows);
  }

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push("/login");
      return;
    }
    load(tab).catch(() => setPosts([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, loading, tab]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim() && files.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      await postsApi.create(body.trim(), visibility, files);
      setBody("");
      setFiles([]);
      if (fileRef.current) fileRef.current.value = "";
      await load(tab);
    } catch (err) {
      setError(err instanceof ApiError ? "Could not post." : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold">Community</h1>

      {/* Composer */}
      <form onSubmit={submit} className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-4 space-y-3">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Share something…"
          rows={3}
          className="w-full resize-none rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 outline-none focus:border-indigo-500"
        />
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            accept="image/*,video/*"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            className="text-sm"
          />
          <select
            value={visibility}
            onChange={(e) => setVisibility(e.target.value as PostVisibility)}
            className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-2 py-1.5 text-sm"
          >
            <option value="public">Public</option>
            <option value="followers">Followers</option>
            <option value="private">Private</option>
          </select>
          <button
            disabled={busy || (!body.trim() && files.length === 0)}
            className="ml-auto rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600 disabled:opacity-50"
          >
            {busy ? "Posting…" : "Post"}
          </button>
        </div>
        {files.length > 0 && (
          <p className="text-xs text-emerald-500">{files.length} file(s) attached</p>
        )}
        {error && <p className="text-sm text-red-500">{error}</p>}
      </form>

      {/* Tabs */}
      <div className="flex gap-2 text-sm">
        {(["timeline", "explore"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={
              tab === t
                ? "rounded-full bg-indigo-500 px-4 py-1.5 font-medium text-white"
                : "rounded-full border border-neutral-300 dark:border-neutral-700 px-4 py-1.5"
            }
          >
            {t === "timeline" ? "Following" : "Explore"}
          </button>
        ))}
      </div>

      {/* Feed */}
      {posts === null ? (
        <p className="text-neutral-500">Loading…</p>
      ) : posts.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-neutral-300 dark:border-neutral-700 p-10 text-center text-neutral-500">
          {tab === "timeline"
            ? "Your timeline is empty. Follow people or switch to Explore."
            : "No public posts yet."}
        </div>
      ) : (
        <div className="space-y-4">
          {posts.map((p) => (
            <PostCard key={p.id} post={p} />
          ))}
        </div>
      )}
    </div>
  );
}
