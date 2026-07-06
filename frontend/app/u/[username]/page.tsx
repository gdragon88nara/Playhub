"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { usersApi, gamesApi, chatApi, PublicUser, GameListItem, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { GameCard } from "@/components/GameCard";

export default function ProfilePage({
  params,
}: {
  params: Promise<{ username: string }>;
}) {
  const { username } = use(params);
  const { user: me } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<PublicUser | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "notfound">("loading");
  const [pending, setPending] = useState(false);
  const [games, setGames] = useState<GameListItem[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  async function load() {
    try {
      setProfile(await usersApi.get(username));
      setStatus("ready");
      try {
        setGames(await gamesApi.list({ owner: username }));
      } catch {
        setGames([]); // private/followers-only content is filtered server-side
      }
    } catch (err) {
      setStatus(err instanceof ApiError && err.status === 404 ? "notfound" : "ready");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [username]);

  async function toggleFollow() {
    if (!profile || me?.username === profile.username) return;
    setPending(true);
    setMsg(null);
    try {
      const st = profile.follow_status;
      // Following or a pending request → undo (unfollow also cancels a request).
      if (st === "following" || st === "requested" || profile.is_followed_by_me) {
        await usersApi.unfollow(profile.username);
      } else {
        await usersApi.follow(profile.username);
      }
      await load();
    } catch (err) {
      setMsg(
        err instanceof ApiError
          ? "요청을 처리할 수 없습니다. 잠시 후 다시 시도해 주세요."
          : "네트워크 오류가 발생했습니다.",
      );
    } finally {
      setPending(false);
    }
  }

  function followLabel(): string {
    if (!profile) return "Follow";
    switch (profile.follow_status) {
      case "following":
        return "팔로잉";
      case "requested":
        return "요청됨";
      default:
        return profile.is_private ? "팔로우 요청" : "팔로우";
    }
  }

  if (status === "loading") return <p className="text-neutral-500">Loading…</p>;
  if (status === "notfound" || !profile)
    return <p className="text-neutral-500">User not found.</p>;

  const isMe = me?.username === profile.username;

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-6">
        <div className="flex items-center gap-5">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-indigo-500 text-2xl font-bold text-white">
            {profile.username.slice(0, 2).toUpperCase()}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold">@{profile.username}</h1>
              {profile.is_private && (
                <span className="rounded-full bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5 text-xs text-neutral-500">
                  Private
                </span>
              )}
              {profile.is_seller && (
                <span className="rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 text-xs">
                  Seller
                </span>
              )}
            </div>
            {profile.display_name && (
              <p className="text-neutral-600 dark:text-neutral-300">{profile.display_name}</p>
            )}
            <div className="mt-2 flex gap-4 text-sm text-neutral-500">
              <span><b className="text-neutral-800 dark:text-neutral-100">{profile.followers_count}</b> followers</span>
              <span><b className="text-neutral-800 dark:text-neutral-100">{profile.following_count}</b> following</span>
            </div>
          </div>
        </div>

        {profile.bio && <p className="mt-4 text-sm">{profile.bio}</p>}

        {!isMe && me && profile.follow_status !== "self" && (
          <div className="mt-4 flex gap-2">
            <button
              onClick={toggleFollow}
              disabled={pending}
              className={
                profile.follow_status === "following" || profile.follow_status === "requested"
                  ? "rounded-lg border border-neutral-300 dark:border-neutral-700 px-4 py-2 text-sm font-medium hover:bg-neutral-100 dark:hover:bg-neutral-800 disabled:opacity-50"
                  : "rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-50"
              }
            >
              {followLabel()}
            </button>
            <button
              onClick={async () => {
                const thread = await chatApi.startWith(profile.username);
                router.push(`/messages/${thread.id}`);
              }}
              className="rounded-lg border border-neutral-700 px-4 py-2 text-sm font-medium hover:bg-neutral-800"
            >
              Message
            </button>
          </div>
        )}
        {msg && <p className="mt-2 text-sm text-red-400">{msg}</p>}
      </div>

      {games.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {games.map((g) => (
            <GameCard key={g.id} game={g} />
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-neutral-300 dark:border-neutral-700 p-8 text-center text-sm text-neutral-500">
          {profile.is_private && !profile.is_followed_by_me && !isMe
            ? "This account is private. Follow to see their games."
            : "No games yet."}
        </div>
      )}
    </div>
  );
}
