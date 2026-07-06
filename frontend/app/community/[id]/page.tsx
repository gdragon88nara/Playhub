"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { postsApi, Post, Comment, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PostCard } from "@/components/PostCard";

export default function PostDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const postId = Number(id);
  const { user } = useAuth();
  const [post, setPost] = useState<Post | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "denied">("loading");
  const [comments, setComments] = useState<Comment[]>([]);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setPost(await postsApi.get(postId));
        setComments(await postsApi.comments(postId));
        setState("ready");
      } catch (err) {
        setState(err instanceof ApiError && err.status === 403 ? "denied" : "denied");
      }
    })();
  }, [postId]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim()) return;
    const c = await postsApi.addComment(postId, draft.trim());
    setComments([...comments, c]);
    setDraft("");
  }

  if (state === "loading") return <p className="text-neutral-500">Loading…</p>;
  if (state === "denied" || !post)
    return <p className="text-neutral-500">This post is private or unavailable.</p>;

  return (
    <div className="space-y-4">
      <Link href="/community" className="text-sm text-indigo-500">← Community</Link>
      <PostCard post={post} />

      <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-5">
        <h2 className="font-semibold">Comments</h2>
        {user && (
          <form onSubmit={submit} className="mt-3 flex gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Add a comment…"
              className="flex-1 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 text-sm outline-none focus:border-indigo-500"
            />
            <button className="rounded-lg bg-indigo-500 px-4 text-sm font-medium text-white">Post</button>
          </form>
        )}
        <ul className="mt-4 space-y-3">
          {comments.map((c) => (
            <li key={c.id} className="text-sm">
              <Link href={`/u/${c.user.username}`} className="font-medium text-indigo-500">
                @{c.user.username}
              </Link>{" "}
              <span className="text-neutral-700 dark:text-neutral-300">{c.body}</span>
            </li>
          ))}
          {comments.length === 0 && <li className="text-sm text-neutral-400">No comments yet.</li>}
        </ul>
      </div>
    </div>
  );
}
