"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { gamesApi, GameListItem, GENRES, GENRE_LABELS, Genre } from "@/lib/api";
import { GameCard } from "@/components/GameCard";

export default function Home() {
  const { user, loading } = useAuth();
  const [games, setGames] = useState<GameListItem[] | null>(null);
  const [active, setActive] = useState<Genre | "all">("all");

  useEffect(() => {
    if (!user) return;
    gamesApi.list().then(setGames).catch(() => setGames([]));
  }, [user]);

  // Genres that actually have games, in display order.
  const usedGenres = useMemo(() => {
    if (!games) return [];
    return GENRES.map((g) => g.value).filter((v) => games.some((game) => game.genre === v));
  }, [games]);

  if (loading) return <p className="text-neutral-500">Loading…</p>;

  if (!user) {
    return (
      <section className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-8 text-center">
        <h1 className="text-2xl font-bold">Upload. Play. Follow.</h1>
        <p className="mt-2 text-neutral-500">
          A home for Unity WebGL and browser games.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link href="/register" className="rounded-lg bg-indigo-500 px-5 py-2.5 font-medium text-white hover:bg-indigo-600">
            Create account
          </Link>
          <Link href="/login" className="rounded-lg border border-neutral-300 dark:border-neutral-700 px-5 py-2.5 font-medium hover:bg-neutral-100 dark:hover:bg-neutral-800">
            Log in
          </Link>
        </div>
      </section>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Discover</h1>
        <Link href="/upload" className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600">
          + Upload game
        </Link>
      </div>

      {games === null ? (
        <p className="text-neutral-500">Loading games…</p>
      ) : games.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-neutral-300 dark:border-neutral-700 p-10 text-center text-neutral-500">
          No games yet. Be the first to{" "}
          <Link href="/upload" className="text-indigo-500 font-medium">deploy one</Link>.
        </div>
      ) : (
        <>
          {/* Genre filter chips */}
          <div className="flex flex-wrap gap-2">
            <Chip active={active === "all"} onClick={() => setActive("all")}>전체</Chip>
            {usedGenres.map((g) => (
              <Chip key={g} active={active === g} onClick={() => setActive(g)}>
                {GENRE_LABELS[g]}
              </Chip>
            ))}
          </div>

          {active === "all" ? (
            // Sectioned by genre.
            <div className="space-y-8">
              {usedGenres.map((g) => (
                <section key={g} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h2 className="font-semibold">{GENRE_LABELS[g]}</h2>
                    <button onClick={() => setActive(g)} className="text-xs text-indigo-400 hover:underline">
                      더 보기
                    </button>
                  </div>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {games.filter((game) => game.genre === g).map((game) => (
                      <GameCard key={game.id} game={game} />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {games.filter((game) => game.genre === active).map((game) => (
                <GameCard key={game.id} game={game} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-3 py-1.5 text-sm ${
        active ? "bg-indigo-500 text-white" : "border border-neutral-300 dark:border-neutral-700 text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"
      }`}
    >
      {children}
    </button>
  );
}
