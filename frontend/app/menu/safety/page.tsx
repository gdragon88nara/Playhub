"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { safetyApi, BlockItem, ApiError, ReportKind, ReportReason } from "@/lib/api";

const REASONS: { value: ReportReason; label: string }[] = [
  { value: "spam", label: "스팸" },
  { value: "abuse", label: "괴롭힘" },
  { value: "hate", label: "혐오 발언" },
  { value: "sexual", label: "성적/노골적 콘텐츠" },
  { value: "illegal", label: "불법/위험" },
  { value: "other", label: "기타" },
];

export default function SafetyPage() {
  const [blocks, setBlocks] = useState<BlockItem[]>([]);
  const [blockName, setBlockName] = useState("");
  const [blockMsg, setBlockMsg] = useState<string | null>(null);

  const [kind, setKind] = useState<ReportKind>("user");
  const [target, setTarget] = useState("");
  const [reason, setReason] = useState<ReportReason>("spam");
  const [note, setNote] = useState("");
  const [reportMsg, setReportMsg] = useState<string | null>(null);

  useEffect(() => {
    safetyApi.blocks().then(setBlocks).catch(() => setBlocks([]));
  }, []);

  async function block() {
    setBlockMsg(null);
    const name = blockName.trim().replace(/^@/, "");
    if (!name) return;
    try {
      await safetyApi.block(name);
      setBlocks(await safetyApi.blocks());
      setBlockName("");
    } catch (err) {
      setBlockMsg(err instanceof ApiError ? "차단할 수 없습니다. 사용자명을 확인해 주세요." : "실패");
    }
  }

  async function unblock(username: string) {
    await safetyApi.unblock(username);
    setBlocks((b) => b.filter((x) => x.blocked.username !== username));
  }

  async function submitReport(e: React.FormEvent) {
    e.preventDefault();
    setReportMsg(null);
    try {
      await safetyApi.report({ kind, target: target.trim(), reason, note: note.trim() });
      setReportMsg("신고가 접수되었습니다. 검토 후 조치하겠습니다.");
      setTarget("");
      setNote("");
    } catch {
      setReportMsg("신고 접수에 실패했습니다.");
    }
  }

  return (
    <>
      <h1 className="text-xl font-bold">차단 및 신고</h1>

      {/* 차단 */}
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-5 space-y-3">
        <p className="text-sm font-medium">차단</p>
        <div className="flex gap-2">
          <input
            value={blockName}
            onChange={(e) => setBlockName(e.target.value)}
            placeholder="차단할 사용자명 (@handle)"
            className="flex-1 rounded-lg border border-neutral-700 bg-transparent px-3 py-2 text-sm outline-none focus:border-indigo-500"
          />
          <button onClick={block} className="rounded-lg bg-red-500/90 px-4 py-2 text-sm font-medium text-white hover:bg-red-500">차단</button>
        </div>
        {blockMsg && <p className="text-xs text-red-400">{blockMsg}</p>}
        <ul className="divide-y divide-neutral-800">
          {blocks.length === 0 && <li className="py-2 text-sm text-neutral-500">차단한 사용자가 없습니다.</li>}
          {blocks.map((b) => (
            <li key={b.id} className="flex items-center justify-between py-2">
              <Link href={`/u/${b.blocked.username}`} className="text-sm">@{b.blocked.username}</Link>
              <button onClick={() => unblock(b.blocked.username)} className="rounded-md border border-neutral-700 px-3 py-1 text-xs hover:bg-neutral-800">차단 해제</button>
            </li>
          ))}
        </ul>
      </div>

      {/* 신고 */}
      <form onSubmit={submitReport} className="rounded-2xl border border-neutral-800 bg-neutral-900 p-5 space-y-3">
        <p className="text-sm font-medium">신고하기</p>
        <div className="grid grid-cols-2 gap-3">
          <select value={kind} onChange={(e) => setKind(e.target.value as ReportKind)} className="rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm">
            <option value="user">사용자</option>
            <option value="game">게임</option>
            <option value="post">게시물</option>
            <option value="comment">댓글</option>
            <option value="other">기타</option>
          </select>
          <select value={reason} onChange={(e) => setReason(e.target.value as ReportReason)} className="rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm">
            {REASONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </div>
        <input
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          placeholder="대상 (사용자명, 게임 slug, 링크 등)"
          className="w-full rounded-lg border border-neutral-700 bg-transparent px-3 py-2 text-sm outline-none focus:border-indigo-500"
        />
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          placeholder="자세한 내용 (선택)"
          className="w-full rounded-lg border border-neutral-700 bg-transparent px-3 py-2 text-sm outline-none focus:border-indigo-500"
        />
        <div className="flex items-center gap-3">
          <button className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600">신고 제출</button>
          {reportMsg && <span className="text-sm text-emerald-400">{reportMsg}</span>}
        </div>
      </form>
    </>
  );
}
