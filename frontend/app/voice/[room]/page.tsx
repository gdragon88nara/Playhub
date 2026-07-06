"use client";

import { use } from "react";
import Link from "next/link";
import { useCall } from "@/lib/call";

export default function VoiceRoomPage({ params }: { params: Promise<{ room: string }> }) {
  const { room } = use(params);
  const { room: active, peers, join, leave } = useCall();
  const inThisRoom = active === room;

  return (
    <div className="space-y-4">
      <Link href="/chat" className="text-sm text-indigo-400">← Chat</Link>
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-6 text-center">
        <h1 className="text-xl font-bold">Voice · #{room}</h1>
        <p className="mt-1 text-sm text-neutral-400">
          High-quality peer-to-peer audio. The call keeps running while you browse
          or play a game.
        </p>

        {inThisRoom ? (
          <div className="mt-5 space-y-3">
            <p className="text-sm text-emerald-400">Connected ({peers.length + 1} in call)</p>
            <ul className="text-sm text-neutral-300">
              <li>@you</li>
              {peers.map((p) => (
                <li key={p.id}>@{p.username}</li>
              ))}
            </ul>
            <button onClick={leave} className="rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white hover:bg-red-600">
              Leave call
            </button>
          </div>
        ) : (
          <button
            onClick={() => join(room)}
            disabled={!!active}
            className="mt-5 rounded-lg bg-indigo-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-600 disabled:opacity-50"
          >
            {active ? `Already in #${active}` : "Join voice"}
          </button>
        )}
      </div>
    </div>
  );
}
