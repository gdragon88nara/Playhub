"use client";

import { useState } from "react";
import Link from "next/link";
import { postsApi, mediaUrl, Post } from "@/lib/api";
import { CommentIcon, HeartIcon } from "@/components/icons";

export function PostCard({ post }: { post: Post }) {
  const [liked, setLiked] = useState(post.is_liked_by_me);
  const [likes, setLikes] = useState(post.likes_count);

  async function toggleLike() {
    const r = await postsApi.like(post.id, !liked);
    setLiked(r.liked);
    setLikes(r.likes_count);
  }

  return (
    <article className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 overflow-hidden">
      <header className="flex items-center gap-3 p-4">
        <Link href={`/u/${post.author.username}`} className="flex items-center gap-2">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-indigo-500 text-white text-xs font-semibold">
            {post.author.username.slice(0, 2).toUpperCase()}
          </span>
          <span className="font-medium">@{post.author.username}</span>
        </Link>
        {post.visibility !== "public" && (
          <span className="ml-auto rounded-full bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5 text-xs text-neutral-500">
            {post.visibility === "followers" ? "Followers" : "Private"}
          </span>
        )}
      </header>

      {post.media.length > 0 && (
        <div className={post.media.length > 1 ? "grid grid-cols-2 gap-0.5" : ""}>
          {post.media.map((m) =>
            m.media_type === "video" ? (
              <video
                key={m.id}
                src={mediaUrl(m.url) ?? undefined}
                controls
                className="w-full bg-black max-h-[70vh]"
              />
            ) : (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={m.id}
                src={mediaUrl(m.url) ?? undefined}
                alt=""
                className="w-full object-cover max-h-[70vh]"
              />
            ),
          )}
        </div>
      )}

      <div className="p-4 space-y-2">
        <div className="flex items-center gap-4">
          <button
            onClick={toggleLike}
            className={`inline-flex items-center gap-1.5 ${liked ? "text-rose-500" : "text-neutral-400"}`}
          >
            <HeartIcon filled={liked} className="h-5 w-5" /> {likes}
          </button>
          <Link
            href={`/community/${post.id}`}
            className="inline-flex items-center gap-1.5 text-neutral-400"
          >
            <CommentIcon className="h-5 w-5" /> {post.comments_count}
          </Link>
        </div>
        {post.body && <p className="whitespace-pre-wrap text-sm">{post.body}</p>}
      </div>
    </article>
  );
}
