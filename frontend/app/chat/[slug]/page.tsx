"use client";

import { use } from "react";
import Link from "next/link";
import { chatApi } from "@/lib/api";
import { ChatWindow } from "@/components/ChatWindow";

export default function RoomPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);

  return (
    <div className="space-y-3">
      <Link href="/chat" className="text-sm text-indigo-400">← Open chat</Link>
      <ChatWindow
        title={`#${slug}`}
        wsPath={`/ws/room/${slug}/`}
        loadHistory={() => chatApi.roomMessages(slug)}
      />
    </div>
  );
}
