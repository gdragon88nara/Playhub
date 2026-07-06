"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { friendsApi, usersApi, PublicUser, FollowRequestItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Tab = "followers" | "following" | "requests";

export default function FriendsPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("followers");
  const [followers, setFollowers] = useState<PublicUser[]>([]);
  const [following, setFollowing] = useState<PublicUser[]>([]);
  const [requests, setRequests] = useState<FollowRequestItem[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      if (tab === "followers") setFollowers(await friendsApi.followers(user.username));
      else if (tab === "following") setFollowing(await friendsApi.following(user.username));
      else setRequests(await friendsApi.requests());
    } finally {
      setLoading(false);
    }
  }, [tab, user]);

  useEffect(() => {
    load();
  }, [load]);

  async function unfollow(username: string) {
    await usersApi.unfollow(username);
    setFollowing((f) => f.filter((u) => u.username !== username));
  }

  async function resolve(id: number, action: "accept" | "reject") {
    // Optimistically remove; if it fails (e.g. already handled), reload the list.
    setRequests((r) => r.filter((x) => x.id !== id));
    try {
      await friendsApi.resolve(id, action);
    } catch {
      try {
        setRequests(await friendsApi.requests());
      } catch {
        /* ignore */
      }
    }
  }

  if (!user) return null;

  return (
    <>
      <h1 className="text-xl font-bold">친구 관리</h1>
      <div className="flex gap-1 rounded-lg border border-neutral-800 bg-neutral-900 p-1 text-sm">
        {(["followers", "following", "requests"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 rounded-md px-3 py-1.5 ${tab === t ? "bg-indigo-500 text-white" : "text-neutral-400 hover:bg-neutral-800"}`}
          >
            {t === "followers" ? "팔로워" : t === "following" ? "팔로잉" : "요청"}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-neutral-500">Loading…</p>
      ) : tab === "requests" ? (
        <ul className="divide-y divide-neutral-800 rounded-2xl border border-neutral-800 bg-neutral-900">
          {requests.length === 0 && <li className="p-4 text-sm text-neutral-500">받은 팔로우 요청이 없습니다.</li>}
          {requests.map((r) => (
            <li key={r.id} className="flex items-center justify-between p-4">
              <Link href={`/u/${r.requester.username}`} className="text-sm">
                <span className="font-medium">@{r.requester.username}</span>
                <span className="ml-2 text-neutral-500">님이 팔로우를 요청했습니다</span>
              </Link>
              <div className="flex gap-2">
                <button onClick={() => resolve(r.id, "accept")} className="rounded-lg bg-indigo-500 px-3 py-1.5 text-sm font-medium text-white">수락</button>
                <button onClick={() => resolve(r.id, "reject")} className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm">거절</button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <ul className="divide-y divide-neutral-800 rounded-2xl border border-neutral-800 bg-neutral-900">
          {(tab === "followers" ? followers : following).length === 0 && (
            <li className="p-4 text-sm text-neutral-500">아직 없습니다.</li>
          )}
          {(tab === "followers" ? followers : following).map((u) => (
            <li key={u.id} className="flex items-center justify-between p-4">
              <Link href={`/u/${u.username}`} className="flex items-center gap-3">
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-neutral-700 text-xs font-semibold">
                  {u.username.slice(0, 2).toUpperCase()}
                </span>
                <span className="text-sm">
                  <span className="block font-medium">{u.display_name || u.username}</span>
                  <span className="block text-xs text-neutral-500">@{u.username}</span>
                </span>
              </Link>
              {tab === "following" && (
                <button onClick={() => unfollow(u.username)} className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800">
                  언팔로우
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
