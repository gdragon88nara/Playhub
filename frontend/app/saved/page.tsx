"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { gamesApi, GameListItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { GameCard } from "@/components/GameCard";

export default function SavedPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [games, setGames] = useState<GameListItem[] | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push("/login");
      return;
    }
    gamesApi.saved().then((rows) => setGames(rows.map((r) => r.game))).catch(() => setGames([]));
  }, [user, loading, router]);

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold">Saved games</h1>
      {games === null ? (
        <p className="text-neutral-500">Loading…</p>
      ) : games.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-neutral-300 dark:border-neutral-700 p-10 text-center text-neutral-500">
          Nothing saved yet. Tap Save on any game.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {games.map((g) => (
            <GameCard key={g.id} game={g} />
          ))}
        </div>
      )}
    </div>
  );
}
