"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { gamesApi, ApiError, Engine, Visibility, Genre, GENRES } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { FolderIcon, ImageIcon, UploadIcon, XIcon } from "@/components/icons";

interface Entry {
  path: string;
  file: File;
}

// Minimal typing for the drag-drop directory API (not in the standard DOM lib).
interface FSEntry {
  isFile: boolean;
  isDirectory: boolean;
  name: string;
  file?: (cb: (f: File) => void, err: (e: unknown) => void) => void;
  createReader?: () => { readEntries: (cb: (e: FSEntry[]) => void, err: (e: unknown) => void) => void };
}

async function walkEntry(entry: FSEntry, prefix: string, out: Entry[]) {
  if (entry.isFile && entry.file) {
    const file = await new Promise<File>((res, rej) => entry.file!(res, rej));
    out.push({ path: prefix + file.name, file });
  } else if (entry.isDirectory && entry.createReader) {
    const reader = entry.createReader();
    const readBatch = () =>
      new Promise<FSEntry[]>((res, rej) => reader.readEntries(res, rej));
    let batch = await readBatch();
    while (batch.length > 0) {
      for (const e of batch) await walkEntry(e, prefix + entry.name + "/", out);
      batch = await readBatch();
    }
  }
}

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function UploadPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const folderRef = useRef<HTMLInputElement>(null);
  const thumbRef = useRef<HTMLInputElement>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [engine, setEngine] = useState<Engine>("html");
  const [genre, setGenre] = useState<Genre>("action");
  const [visibility, setVisibility] = useState<Visibility>("public");
  const [isPaid, setIsPaid] = useState(false);
  const [price, setPrice] = useState("");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [thumbnail, setThumbnail] = useState<File | null>(null);
  const [thumbPreview, setThumbPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function pickThumb(file: File | null) {
    setThumbnail(file);
    setThumbPreview((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return file ? URL.createObjectURL(file) : null;
    });
  }

  if (!loading && !user) {
    if (typeof window !== "undefined") router.push("/login");
    return null;
  }

  function mergeEntries(added: Entry[]) {
    setEntries((prev) => {
      const map = new Map(prev.map((e) => [e.path, e]));
      for (const e of added) map.set(e.path, e);
      return [...map.values()];
    });
  }

  function addFromFileList(list: FileList | null) {
    if (!list) return;
    const added: Entry[] = Array.from(list).map((file) => ({
      path: (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name,
      file,
    }));
    mergeEntries(added);
  }

  async function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const items = e.dataTransfer.items;
    const out: Entry[] = [];
    const roots: FSEntry[] = [];
    for (let i = 0; i < items.length; i++) {
      const it = items[i] as DataTransferItem & { webkitGetAsEntry?: () => FSEntry | null };
      const entry = it.webkitGetAsEntry?.();
      if (entry) roots.push(entry);
    }
    if (roots.length > 0) {
      for (const r of roots) await walkEntry(r, "", out);
      mergeEntries(out);
    } else {
      addFromFileList(e.dataTransfer.files);
    }
  }

  const hasIndex = entries.some((e) => e.path.split("/").pop()?.toLowerCase() === "index.html");
  const totalSize = entries.reduce((n, e) => n + e.file.size, 0);
  const isSingleZip = entries.length === 1 && entries[0].path.toLowerCase().endsWith(".zip");

  async function onDeploy() {
    setError(null);
    if (entries.length === 0) {
      setError("Add your game files or folder first.");
      return;
    }
    setBusy(true);
    try {
      const meta = {
        title,
        description,
        engine,
        genre,
        visibility,
        is_paid: isPaid,
        price: isPaid ? Number(price) : 0,
      };
      // A single .zip is still accepted (extracted server-side); otherwise the
      // files/folders are uploaded directly.
      const game = isSingleZip
        ? await gamesApi.create(meta, entries[0].file, thumbnail)
        : await gamesApi.createFromFiles(meta, entries, thumbnail);
      router.push(`/games/${game.slug}`);
    } catch (err) {
      if (err instanceof ApiError && err.data && typeof err.data === "object") {
        const first = Object.values(err.data as Record<string, string[]>)[0];
        setError(Array.isArray(first) ? first[0] : String(first));
      } else {
        setError(err instanceof Error ? err.message : "Deploy failed.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">New game</h1>
        <button
          onClick={onDeploy}
          disabled={busy || !title || entries.length === 0}
          className="rounded-lg bg-indigo-500 px-5 py-2 font-semibold text-white hover:bg-indigo-600 disabled:opacity-50"
        >
          {busy ? "Deploying…" : "Deploy"}
        </button>
      </div>

      <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-5 space-y-4">
        <Labeled label="Title">
          <input value={title} onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 outline-none focus:border-indigo-500" />
        </Labeled>

        <Labeled label="Description">
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
            className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 outline-none focus:border-indigo-500" />
        </Labeled>

        <div className="grid grid-cols-2 gap-4">
          <Labeled label="Engine">
            <select value={engine} onChange={(e) => setEngine(e.target.value as Engine)}
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2">
              <option value="html">HTML / JS / WebGL</option>
              <option value="unity_webgl">Unity WebGL</option>
            </select>
          </Labeled>
          <Labeled label="Genre">
            <select value={genre} onChange={(e) => setGenre(e.target.value as Genre)}
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2">
              {GENRES.map((g) => (
                <option key={g.value} value={g.value}>{g.label}</option>
              ))}
            </select>
          </Labeled>
          <Labeled label="Visibility">
            <select value={visibility} onChange={(e) => setVisibility(e.target.value as Visibility)}
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2">
              <option value="public">Public</option>
              <option value="followers">Followers only</option>
              <option value="private">Private (only me)</option>
            </select>
          </Labeled>
          <Labeled label="Thumbnail (cover image)">
            <div className="flex items-center gap-3">
              <div className="flex h-14 w-24 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-neutral-300 dark:border-neutral-700 bg-neutral-100 dark:bg-neutral-800">
                {thumbPreview ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={thumbPreview} alt="" className="h-full w-full object-cover" />
                ) : (
                  <ImageIcon className="h-5 w-5 text-neutral-400" />
                )}
              </div>
              <button type="button" onClick={() => thumbRef.current?.click()}
                className="rounded-lg border border-neutral-300 dark:border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800">
                {thumbnail ? "변경" : "이미지 선택"}
              </button>
              {thumbnail && (
                <button type="button" onClick={() => pickThumb(null)} className="text-neutral-500 hover:text-red-400">
                  <XIcon className="h-4 w-4" />
                </button>
              )}
              <input ref={thumbRef} type="file" accept="image/*" hidden
                onChange={(e) => pickThumb(e.target.files?.[0] ?? null)} />
            </div>
          </Labeled>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isPaid} onChange={(e) => setIsPaid(e.target.checked)}
              className="h-4 w-4 accent-indigo-500" />
            Paid game
          </label>
          {isPaid && (
            <input type="number" min="0" step="0.01" value={price} placeholder="Price (USD)"
              onChange={(e) => setPrice(e.target.value)}
              className="w-40 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-1.5" />
          )}
        </div>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`rounded-2xl border-2 border-dashed p-8 text-center transition-colors ${
          dragging ? "border-indigo-500 bg-indigo-500/5" : "border-neutral-300 dark:border-neutral-700"
        }`}
      >
        <UploadIcon className="mx-auto h-8 w-8 text-neutral-400" />
        <p className="mt-3 font-medium">Drag & drop your game folder or files here</p>
        <p className="mt-1 text-xs text-neutral-500">
          Must contain <code>index.html</code>. Folder structure is preserved — no zipping needed.
          Unity WebGL: drop the whole export folder (index.html + Build/).
        </p>
        <div className="mt-4 flex justify-center gap-3">
          <button
            type="button"
            onClick={() => folderRef.current?.click()}
            className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800"
          >
            <FolderIcon className="h-4 w-4" /> Choose folder
          </button>
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800"
          >
            <UploadIcon className="h-4 w-4" /> Choose files
          </button>
        </div>
        {/* @ts-expect-error webkitdirectory is non-standard but supported */}
        <input ref={folderRef} type="file" webkitdirectory="" directory="" multiple hidden
          onChange={(e) => { addFromFileList(e.target.files); e.target.value = ""; }} />
        <input ref={fileRef} type="file" multiple hidden
          onChange={(e) => { addFromFileList(e.target.files); e.target.value = ""; }} />
      </div>

      {/* Selected files */}
      {entries.length > 0 && (
        <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
          <div className="flex items-center justify-between border-b border-neutral-200 dark:border-neutral-800 px-4 py-2.5 text-sm">
            <span className="font-medium">
              {entries.length} file{entries.length > 1 ? "s" : ""} · {humanSize(totalSize)}
            </span>
            <button onClick={() => setEntries([])} className="text-xs text-neutral-500 hover:text-red-400">
              Clear all
            </button>
          </div>
          {!hasIndex && !isSingleZip && (
            <p className="border-b border-amber-500/20 bg-amber-500/10 px-4 py-2 text-xs text-amber-500">
              No <code>index.html</code> found. Your game needs one as its entry point.
            </p>
          )}
          <ul className="max-h-64 divide-y divide-neutral-100 dark:divide-neutral-800 overflow-auto">
            {entries.map((e) => (
              <li key={e.path} className="flex items-center justify-between px-4 py-2 text-sm">
                <span className="min-w-0 flex-1 truncate font-mono text-xs text-neutral-500">
                  {e.path}
                  {e.path.split("/").pop()?.toLowerCase() === "index.html" && (
                    <span className="ml-2 rounded bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-medium text-emerald-500">entry</span>
                  )}
                </span>
                <span className="ml-3 shrink-0 text-xs text-neutral-400">{humanSize(e.file.size)}</span>
                <button
                  onClick={() => setEntries((prev) => prev.filter((x) => x.path !== e.path))}
                  className="ml-2 text-neutral-500 hover:text-red-400"
                >
                  <XIcon className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  );
}

function Labeled({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-sm text-neutral-500">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}
