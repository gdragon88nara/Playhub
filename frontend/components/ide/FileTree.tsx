"use client";

import { useMemo, useState } from "react";
import { ProjectFile } from "@/lib/api";

// Turns the flat path list (e.g. "src/level.js") into a collapsible folder tree.

interface Dir {
  name: string;
  path: string;
  dirs: Map<string, Dir>;
  files: ProjectFile[];
}

function buildTree(files: ProjectFile[]): Dir {
  const root: Dir = { name: "", path: "", dirs: new Map(), files: [] };
  for (const f of files) {
    const parts = f.path.split("/");
    let dir = root;
    for (let i = 0; i < parts.length - 1; i++) {
      const seg = parts[i];
      if (!dir.dirs.has(seg)) {
        dir.dirs.set(seg, {
          name: seg,
          path: dir.path ? `${dir.path}/${seg}` : seg,
          dirs: new Map(),
          files: [],
        });
      }
      dir = dir.dirs.get(seg)!;
    }
    dir.files.push(f);
  }
  return root;
}

function DirView({
  dir,
  depth,
  activeId,
  onSelect,
  onDelete,
}: {
  dir: Dir;
  depth: number;
  activeId: number | null;
  onSelect: (f: ProjectFile) => void;
  onDelete: (f: ProjectFile) => void;
}) {
  const [open, setOpen] = useState(true);
  const pad = { paddingLeft: 8 + depth * 12 };
  const dirs = [...dir.dirs.values()].sort((a, b) => a.name.localeCompare(b.name));
  const files = [...dir.files].sort((a, b) => a.path.localeCompare(b.path));

  return (
    <>
      {depth > 0 && (
        <button
          onClick={() => setOpen((o) => !o)}
          style={pad}
          className="flex w-full items-center gap-1 py-1 text-left text-sm text-neutral-300 hover:bg-neutral-800/60"
        >
          <span className="text-neutral-500">{open ? "▾" : "▸"}</span>
          <span className="truncate">{dir.name}</span>
        </button>
      )}
      {open && (
        <>
          {dirs.map((d) => (
            <DirView
              key={d.path}
              dir={d}
              depth={depth + 1}
              activeId={activeId}
              onSelect={onSelect}
              onDelete={onDelete}
            />
          ))}
          {files.map((f) => (
            <div
              key={f.id}
              style={{ paddingLeft: 8 + (depth + 1) * 12 }}
              className={`group flex items-center gap-2 py-1 pr-2 text-sm ${
                f.id === activeId ? "bg-neutral-800 text-white" : "text-neutral-300 hover:bg-neutral-800/50"
              }`}
            >
              <span
                className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
                style={{ backgroundColor: f.language.color }}
                title={f.language.label}
              />
              <button onClick={() => onSelect(f)} className="min-w-0 flex-1 truncate text-left">
                {f.path.split("/").pop()}
              </button>
              <button
                onClick={() => onDelete(f)}
                className="text-neutral-600 opacity-0 group-hover:opacity-100 hover:text-red-400"
                title="Delete"
              >
                ×
              </button>
            </div>
          ))}
        </>
      )}
    </>
  );
}

export function FileTree({
  files,
  activeId,
  onSelect,
  onDelete,
}: {
  files: ProjectFile[];
  activeId: number | null;
  onSelect: (f: ProjectFile) => void;
  onDelete: (f: ProjectFile) => void;
}) {
  const root = useMemo(() => buildTree(files), [files]);
  return (
    <div className="py-1">
      <DirView dir={root} depth={0} activeId={activeId} onSelect={onSelect} onDelete={onDelete} />
    </div>
  );
}
