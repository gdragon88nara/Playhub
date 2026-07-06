"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { meApi, GameListItem, Post } from "@/lib/api";
import { PlayIcon, HeartIcon } from "@/components/icons";

export default function FavoritesPage() {
  const [games, setGames] = useState<GameListItem[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    meApi.favorites()
      .then((d) => { setGames(d.games); setPosts(d.posts); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-neutral-500">Loading…</p>;

  return (
    <>
      <h1 className="text-xl font-bold">즐겨찾기</h1>
      <p className="text-sm text-neutral-500">좋아요한 게임과 게시물이 모여 있습니다.</p>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-neutral-400">게임 ({games.length})</h2>
        {games.length === 0 ? (
          <p className="text-sm text-neutral-500">좋아요한 게임이 없습니다.</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {games.map((g) => (
              <Link key={g.id} href={`/games/${g.slug}`} className="rounded-2xl border border-neutral-800 bg-neutral-900 p-4 hover:bg-neutral-800/50">
                <div className="font-medium">{g.title}</div>
                <div className="mt-1 flex items-center gap-3 text-xs text-neutral-500">
                  <span className="inline-flex items-center gap-1"><PlayIcon className="h-3.5 w-3.5" /> {g.play_count}</span>
                  <span className="inline-flex items-center gap-1"><HeartIcon className="h-3.5 w-3.5" filled /> {g.likes_count}</span>
                  <span>@{g.owner.username}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-neutral-400">게시물 ({posts.length})</h2>
        {posts.length === 0 ? (
          <p className="text-sm text-neutral-500">좋아요한 게시물이 없습니다.</p>
        ) : (
          <ul className="divide-y divide-neutral-800 rounded-2xl border border-neutral-800 bg-neutral-900">
            {posts.map((p) => (
              <li key={p.id}>
                <Link href={`/community/${p.id}`} className="block p-4 hover:bg-neutral-800/50">
                  <span className="text-xs text-neutral-500">@{p.author.username}</span>
                  <p className="mt-1 line-clamp-2 text-sm text-neutral-200">{p.body || "(미디어 게시물)"}</p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
