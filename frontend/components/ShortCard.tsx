"use client";

import { useState } from "react";
import Link from "next/link";
import { shortsApi, mediaUrl, Short } from "@/lib/api";
import { HeartIcon } from "@/components/icons";

export function ShortCard({ short }: { short: Short }) {
  const [liked, setLiked] = useState(short.is_liked_by_me);
  const [likes, setLikes] = useState(short.likes_count);

  async function toggleLike() {
    const r = await shortsApi.like(short.id, !liked);
    setLiked(r.liked);
    setLikes(r.likes_count);
  }

  return (
    <div className="relative mx-auto w-full max-w-sm overflow-hidden rounded-2xl border border-neutral-800 bg-black">
      <video
        src={mediaUrl(short.video_url) ?? undefined}
        className="aspect-[9/16] w-full bg-black object-contain"
        controls
        loop
        playsInline
      />
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
        <Link href={`/u/${short.author.username}`} className="text-sm font-semibold text-white">
          @{short.author.username}
        </Link>
        {short.caption && <p className="mt-1 text-sm text-neutral-200">{short.caption}</p>}
        <button
          onClick={toggleLike}
          className={`mt-2 inline-flex items-center gap-1.5 text-sm ${liked ? "text-rose-500" : "text-white"}`}
        >
          <HeartIcon filled={liked} className="h-5 w-5" /> {likes}
        </button>
      </div>
    </div>
  );
}
