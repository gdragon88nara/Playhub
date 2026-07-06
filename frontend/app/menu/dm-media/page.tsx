"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { dmApi, mediaUrl, DmMediaItem } from "@/lib/api";
import { ImageIcon } from "@/components/icons";

export default function DmMediaPage() {
  const [items, setItems] = useState<DmMediaItem[] | null>(null);

  useEffect(() => {
    dmApi.media().then(setItems).catch(() => setItems([]));
  }, []);

  return (
    <>
      <h1 className="text-xl font-bold">DM 자료</h1>
      <p className="text-sm text-neutral-500">DM으로 주고받은 이미지와 파일을 모아봤습니다.</p>

      {!items ? (
        <p className="text-neutral-500">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-neutral-500">
          아직 주고받은 자료가 없습니다. 메시지 대화에서 이미지나 파일을 보내보세요.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {items.map((m) => (
            <div key={m.id} className="overflow-hidden rounded-xl border border-neutral-800 bg-neutral-900">
              <Link href={`/messages/${m.thread_id}`} className="block">
                {m.attachment_type === "image" && m.url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={mediaUrl(m.url) ?? undefined} alt={m.name} className="aspect-square w-full object-cover" />
                ) : (
                  <div className="flex aspect-square w-full items-center justify-center bg-neutral-800 text-neutral-500">
                    <ImageIcon className="h-8 w-8" />
                  </div>
                )}
              </Link>
              <div className="p-2 text-xs">
                <div className="truncate text-neutral-300">{m.name || "파일"}</div>
                <div className="mt-0.5 truncate text-neutral-500">
                  {m.from_me ? "→ " : "← "}@{m.other} · {new Date(m.created_at).toLocaleDateString()}
                </div>
                {m.url && (
                  <a
                    href={mediaUrl(m.url) ?? undefined}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 inline-block text-indigo-400 hover:underline"
                  >
                    열기
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
