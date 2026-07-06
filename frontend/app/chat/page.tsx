"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { chatApi, ChatRoom } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function ChatRoomsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [rooms, setRooms] = useState<ChatRoom[] | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push("/login");
      return;
    }
    chatApi.rooms().then(setRooms).catch(() => setRooms([]));
  }, [user, loading, router]);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Open chat</h1>
      <p className="text-sm text-neutral-500">Live public rooms — everyone can join and talk in realtime.</p>
      {rooms === null ? (
        <p className="text-neutral-500">Loading…</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {rooms.map((r) => (
            <div key={r.id} className="rounded-xl border border-neutral-800 bg-neutral-900 p-4">
              <Link href={`/chat/${r.slug}`} className="block hover:opacity-80">
                <div className="font-semibold">#{r.slug}</div>
                <div className="text-sm text-neutral-500">{r.description}</div>
              </Link>
              <div className="mt-3 flex gap-2 text-xs">
                <Link href={`/chat/${r.slug}`} className="rounded-md border border-neutral-700 px-2 py-1 hover:bg-neutral-800">
                  Open chat
                </Link>
                <Link href={`/voice/${r.slug}`} className="rounded-md border border-neutral-700 px-2 py-1 hover:bg-neutral-800">
                  Join voice
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
