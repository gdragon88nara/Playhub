"use client";

import { useEffect, useRef, useState } from "react";
import { ChatMessage, dmApi, mediaUrl, wsUrl } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ImageIcon } from "@/components/icons";

export function ChatWindow({
  wsPath,
  loadHistory,
  title,
  threadId,
}: {
  wsPath: string;
  loadHistory: () => Promise<ChatMessage[]>;
  title: string;
  // When set (DM), enables sending image/file attachments over REST.
  threadId?: number;
}) {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const [draft, setDraft] = useState("");
  const [uploading, setUploading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function onAttach(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !threadId) return;
    setUploading(true);
    try {
      const msg = await dmApi.sendAttachment(threadId, file);
      setMessages((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]));
    } finally {
      setUploading(false);
    }
  }

  useEffect(() => {
    let alive = true;
    loadHistory().then((h) => alive && setMessages(h)).catch(() => {});

    const ws = new WebSocket(wsUrl(wsPath));
    wsRef.current = ws;
    ws.onopen = () => alive && setConnected(true);
    ws.onclose = () => alive && setConnected(false);
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data) as ChatMessage;
      setMessages((prev) =>
        prev.some((m) => m.id === data.id) ? prev : [...prev, data],
      );
    };
    return () => {
      alive = false;
      ws.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsPath]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  function send(e: React.FormEvent) {
    e.preventDefault();
    const body = draft.trim();
    if (!body || wsRef.current?.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ body }));
    setDraft("");
  }

  return (
    <div className="flex h-[70vh] flex-col rounded-2xl border border-neutral-800 bg-neutral-900">
      <header className="flex items-center justify-between border-b border-neutral-800 px-4 py-3">
        <span className="font-semibold">{title}</span>
        <span className={`text-xs ${connected ? "text-emerald-400" : "text-neutral-500"}`}>
          {connected ? "Live" : "Connecting…"}
        </span>
      </header>

      <div ref={scrollRef} className="flex-1 space-y-2 overflow-y-auto p-4">
        {messages.map((m) => {
          const mine = m.sender_id === user?.id;
          return (
            <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[75%] rounded-2xl px-3 py-2 text-sm ${
                  mine ? "bg-indigo-600 text-white" : "bg-neutral-800 text-neutral-100"
                }`}
              >
                {!mine && <div className="mb-0.5 text-xs text-neutral-400">@{m.sender}</div>}
                {m.attachment_url && m.attachment_type === "image" ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={mediaUrl(m.attachment_url) ?? undefined}
                    alt={m.attachment_name || "image"}
                    className="max-h-60 rounded-lg"
                  />
                ) : m.attachment_url ? (
                  <a
                    href={mediaUrl(m.attachment_url) ?? undefined}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 underline"
                  >
                    <ImageIcon className="h-4 w-4" /> {m.attachment_name || "file"}
                  </a>
                ) : null}
                {m.body && <div className="whitespace-pre-wrap break-words">{m.body}</div>}
              </div>
            </div>
          );
        })}
        {messages.length === 0 && (
          <p className="text-center text-sm text-neutral-500">No messages yet. Say hello.</p>
        )}
      </div>

      <form onSubmit={send} className="flex gap-2 border-t border-neutral-800 p-3">
        {threadId && (
          <>
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              title="Send an image or file"
              className="rounded-lg border border-neutral-700 px-3 text-neutral-300 hover:bg-neutral-800 disabled:opacity-50"
            >
              <ImageIcon className="h-4 w-4" />
            </button>
            <input ref={fileRef} type="file" hidden onChange={onAttach} />
          </>
        )}
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={uploading ? "Uploading…" : "Message…"}
          className="flex-1 rounded-lg border border-neutral-700 bg-transparent px-3 py-2 text-sm outline-none focus:border-indigo-500"
        />
        <button
          disabled={!connected || !draft.trim()}
          className="rounded-lg bg-indigo-500 px-4 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
