"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { searchApi, mediaUrl, SearchResults } from "@/lib/api";
import { GameCard } from "@/components/GameCard";
import { SearchIcon, HeartIcon, CommentIcon } from "@/components/icons";

type Tab = "all" | "users" | "games" | "posts";

function SearchInner() {
  const params = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [tab, setTab] = useState<Tab>("all");
  const [res, setRes] = useState<SearchResults | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const term = q.trim();
    if (!term) {
      setRes(null);
      return;
    }
    setLoading(true);
    const id = setTimeout(() => {
      searchApi.search(term, tab)
        .then(setRes)
        .catch(() => setRes(null))
        .finally(() => setLoading(false));
    }, 300);
    return () => clearTimeout(id);
  }, [q, tab]);

  const showUsers = (tab === "all" || tab === "users") && res && res.users.length > 0;
  const showGames = (tab === "all" || tab === "games") && res && res.games.length > 0;
  const showPosts = (tab === "all" || tab === "posts") && res && res.posts.length > 0;
  const empty = res && !showUsers && !showGames && !showPosts;

  return (
    <div className="space-y-5">
      <div className="relative">
        <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          autoFocus
          placeholder="게임 · 게시물 · 유저 검색"
          className="w-full rounded-xl border border-neutral-700 bg-neutral-900 py-3 pl-11 pr-4 outline-none focus:border-indigo-500"
        />
      </div>

      <div className="flex gap-2">
        {(["all", "users", "games", "posts"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-full px-3 py-1.5 text-sm ${
              tab === t ? "bg-indigo-500 text-white" : "border border-neutral-700 text-neutral-400 hover:bg-neutral-800"
            }`}
          >
            {t === "all" ? "전체" : t === "users" ? "유저" : t === "games" ? "게임" : "게시물"}
          </button>
        ))}
      </div>

      {!q.trim() ? (
        <p className="text-sm text-neutral-500">게임, 게시물, 유저를 검색해 보세요.</p>
      ) : loading && !res ? (
        <p className="text-neutral-500">검색 중…</p>
      ) : empty ? (
        <p className="text-sm text-neutral-500">‘{q.trim()}’에 대한 결과가 없습니다.</p>
      ) : (
        <div className="space-y-8">
          {showUsers && (
            <section className="space-y-2">
              <h2 className="text-sm font-semibold text-neutral-400">유저</h2>
              <ul className="divide-y divide-neutral-800 rounded-2xl border border-neutral-800 bg-neutral-900">
                {res!.users.map((u) => (
                  <li key={u.id}>
                    <Link href={`/u/${u.username}`} className="flex items-center gap-3 p-3 hover:bg-neutral-800/50">
                      <span className="inline-flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-indigo-500 text-xs font-semibold text-white">
                        {u.avatar ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={mediaUrl(u.avatar) ?? undefined} alt="" className="h-full w-full object-cover" />
                        ) : (
                          u.username.slice(0, 2).toUpperCase()
                        )}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium">{u.display_name || u.username}</span>
                        <span className="block truncate text-xs text-neutral-500">@{u.username}</span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {showGames && (
            <section className="space-y-2">
              <h2 className="text-sm font-semibold text-neutral-400">게임</h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {res!.games.map((g) => (
                  <GameCard key={g.id} game={g} />
                ))}
              </div>
            </section>
          )}

          {showPosts && (
            <section className="space-y-2">
              <h2 className="text-sm font-semibold text-neutral-400">게시물</h2>
              <ul className="divide-y divide-neutral-800 rounded-2xl border border-neutral-800 bg-neutral-900">
                {res!.posts.map((p) => (
                  <li key={p.id}>
                    <Link href={`/community/${p.id}`} className="block p-4 hover:bg-neutral-800/50">
                      <span className="text-xs text-neutral-500">@{p.author.username}</span>
                      <p className="mt-1 line-clamp-2 text-sm text-neutral-200">{p.body || "(미디어 게시물)"}</p>
                      <div className="mt-2 flex items-center gap-3 text-xs text-neutral-500">
                        <span className="inline-flex items-center gap-1"><HeartIcon className="h-3.5 w-3.5" /> {p.likes_count}</span>
                        <span className="inline-flex items-center gap-1"><CommentIcon className="h-3.5 w-3.5" /> {p.comments_count}</span>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<p className="text-neutral-500">Loading…</p>}>
      <SearchInner />
    </Suspense>
  );
}
