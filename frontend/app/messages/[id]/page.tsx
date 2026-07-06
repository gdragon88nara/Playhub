"use client";

import { use } from "react";
import Link from "next/link";
import { chatApi } from "@/lib/api";
import { ChatWindow } from "@/components/ChatWindow";

export default function DMPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const threadId = Number(id);

  return (
    <div className="space-y-3">
      <Link href="/messages" className="text-sm text-indigo-400">← Messages</Link>
      <ChatWindow
        title="Direct message"
        wsPath={`/ws/dm/${threadId}/`}
        loadHistory={() => chatApi.threadMessages(threadId)}
        threadId={threadId}
      />
    </div>
  );
}
