"use client";

import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ideApi, ProjectDetail, ProjectFile, RunResult, ApiError } from "@/lib/api";
import { buildPreviewDoc, webEntry } from "@/lib/preview";
import { CodeEditor } from "@/components/ide/CodeEditor";
import { FileTree } from "@/components/ide/FileTree";
import {
  FilesIcon,
  MonitorIcon,
  PlayIcon,
  PlusIcon,
  RefreshIcon,
  RocketIcon,
  TerminalIcon,
  XIcon,
} from "@/components/icons";

export default function IdeEditor({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [openTabs, setOpenTabs] = useState<number[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);

  const [previewOpen, setPreviewOpen] = useState(true);
  const [previewDoc, setPreviewDoc] = useState("");
  const [panelOpen, setPanelOpen] = useState(false);
  const [panelTab, setPanelTab] = useState<"terminal" | "problems">("terminal");
  const [term, setTerm] = useState<RunResult | null>(null);

  const [running, setRunning] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [deployedSlug, setDeployedSlug] = useState<string | null>(null);
  const [saved, setSaved] = useState(true);
  const [cursor, setCursor] = useState({ line: 1, col: 1 });
  const [msg, setMsg] = useState<string | null>(null);

  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const previewTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    ideApi.get(slug).then((p) => {
      setProject(p);
      const first = p.files.find((f) => f.path.endsWith(".html")) ?? p.files[0];
      if (first) {
        setActiveId(first.id);
        setOpenTabs([first.id]);
      }
      setDeployedSlug(p.deployed_slug);
    });
  }, [slug]);

  const active = project?.files.find((f) => f.id === activeId) ?? null;

  const filesMap = useMemo(() => {
    const m: Record<string, string> = {};
    project?.files.forEach((f) => (m[f.path] = f.content));
    return m;
  }, [project]);

  const entry = useMemo(() => webEntry(filesMap), [filesMap]);

  const rebuildPreview = useCallback(() => {
    if (!entry) {
      setPreviewDoc("");
      return;
    }
    setPreviewDoc(buildPreviewDoc(filesMap, entry));
  }, [filesMap, entry]);

  // Live webview: rebuild (debounced) whenever the code changes and the pane is open.
  useEffect(() => {
    if (!previewOpen) return;
    if (previewTimer.current) clearTimeout(previewTimer.current);
    previewTimer.current = setTimeout(rebuildPreview, 300);
    return () => {
      if (previewTimer.current) clearTimeout(previewTimer.current);
    };
  }, [previewOpen, rebuildPreview]);

  function openFile(f: ProjectFile) {
    setActiveId(f.id);
    setOpenTabs((t) => (t.includes(f.id) ? t : [...t, f.id]));
  }

  function closeTab(id: number, e?: React.MouseEvent) {
    e?.stopPropagation();
    setOpenTabs((t) => {
      const next = t.filter((x) => x !== id);
      if (activeId === id) setActiveId(next[next.length - 1] ?? null);
      return next;
    });
  }

  function updateContent(content: string) {
    if (!project || !active) return;
    setProject({
      ...project,
      files: project.files.map((f) => (f.id === active.id ? { ...f, content } : f)),
    });
    setSaved(false);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      await ideApi.saveFile(active.id, content);
      setSaved(true);
    }, 600);
  }

  async function addFile() {
    const path = prompt("New file (name.ext, may include a folder e.g. src/level.js)");
    if (!path || !project) return;
    try {
      const f = await ideApi.addFile(slug, path.trim());
      setProject({ ...project, files: [...project.files, f] });
      openFile(f);
    } catch (err) {
      alert(err instanceof ApiError ? JSON.stringify(err.data) : "Could not add file");
    }
  }

  async function delFile(f: ProjectFile) {
    if (!project || !confirm(`Delete ${f.path}?`)) return;
    await ideApi.deleteFile(f.id);
    setProject({ ...project, files: project.files.filter((x) => x.id !== f.id) });
    closeTab(f.id);
  }

  async function run() {
    setRunning(true);
    setMsg(null);
    try {
      const result = await ideApi.run(slug);
      setTerm(result);
      if (result.mode === "preview") {
        setPreviewOpen(true);
        rebuildPreview();
      } else {
        setPanelOpen(true);
        setPanelTab("terminal");
      }
    } finally {
      setRunning(false);
    }
  }

  async function deploy() {
    setDeploying(true);
    setMsg(null);
    try {
      const game = await ideApi.deploy(slug);
      setDeployedSlug(game.slug);
      setMsg("Deployed successfully.");
    } catch (err) {
      setMsg(err instanceof ApiError ? `Deploy failed: ${readErr(err)}` : "Deploy failed");
      setPanelOpen(true);
      setPanelTab("problems");
    } finally {
      setDeploying(false);
    }
  }

  if (!project) return <p className="text-neutral-500">Loading…</p>;

  const tabFiles = openTabs
    .map((id) => project.files.find((f) => f.id === id))
    .filter((f): f is ProjectFile => !!f);

  return (
    <div className="mx-[calc(50%-50vw)] flex h-[calc(100vh-7rem)] w-screen flex-col overflow-hidden border-y border-neutral-800 bg-neutral-900 text-sm">
      {/* Title / toolbar */}
      <header className="flex h-10 shrink-0 items-center justify-between border-b border-neutral-800 bg-neutral-950 px-3">
        <div className="flex items-center gap-3">
          <Link href="/ide" className="text-neutral-400 hover:text-neutral-100">← IDE</Link>
          <span className="font-medium">{project.name}</span>
          <span className="rounded bg-neutral-800 px-1.5 py-0.5 text-[11px] text-neutral-400">{project.kind}</span>
        </div>
        <div className="flex items-center gap-2">
          <ToolbarButton onClick={() => setPreviewOpen((v) => !v)} active={previewOpen} title="Toggle webview preview">
            <MonitorIcon className="h-4 w-4" /> Preview
          </ToolbarButton>
          <ToolbarButton onClick={run} disabled={running} title="Run (F5)">
            <PlayIcon className="h-4 w-4" /> {running ? "Running…" : "Run"}
          </ToolbarButton>
          <button
            onClick={deploy}
            disabled={deploying}
            className="inline-flex items-center gap-1.5 rounded-md bg-indigo-500 px-3 py-1.5 font-semibold text-white hover:bg-indigo-600 disabled:opacity-50"
          >
            <RocketIcon className="h-4 w-4" /> {deploying ? "Deploying…" : "Deploy"}
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* Activity bar */}
        <nav className="flex w-12 shrink-0 flex-col items-center gap-1 border-r border-neutral-800 bg-neutral-950 py-2">
          <ActivityIcon active title="Explorer"><FilesIcon className="h-5 w-5" /></ActivityIcon>
          <ActivityIcon onClick={run} title="Run"><PlayIcon className="h-5 w-5" /></ActivityIcon>
          <ActivityIcon onClick={() => setPreviewOpen((v) => !v)} active={previewOpen} title="Preview">
            <MonitorIcon className="h-5 w-5" />
          </ActivityIcon>
          <ActivityIcon onClick={() => setPanelOpen((v) => !v)} active={panelOpen} title="Terminal">
            <TerminalIcon className="h-5 w-5" />
          </ActivityIcon>
        </nav>

        {/* Explorer sidebar */}
        <aside className="flex w-56 shrink-0 flex-col overflow-hidden border-r border-neutral-800 bg-neutral-900">
          <div className="flex items-center justify-between px-3 pt-3 pb-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Explorer</span>
            <button onClick={addFile} className="text-neutral-400 hover:text-neutral-100" title="New file">
              <PlusIcon className="h-4 w-4" />
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-auto">
            <FileTree files={project.files} activeId={activeId} onSelect={openFile} onDelete={delFile} />
          </div>
        </aside>

        {/* Editor group + preview */}
        <section className="flex min-w-0 flex-1 flex-col">
          <div className="flex min-h-0 flex-1">
            {/* Editor */}
            <div className="flex min-w-0 flex-1 flex-col border-r border-neutral-800">
              {/* Tabs */}
              <div className="flex h-9 shrink-0 items-stretch overflow-x-auto border-b border-neutral-800 bg-neutral-950">
                {tabFiles.length === 0 && (
                  <span className="flex items-center px-3 text-xs text-neutral-600">No file open</span>
                )}
                {tabFiles.map((f) => (
                  <div
                    key={f.id}
                    onClick={() => setActiveId(f.id)}
                    className={`group flex cursor-pointer items-center gap-2 border-r border-neutral-800 px-3 text-xs ${
                      f.id === activeId ? "bg-neutral-900 text-white" : "text-neutral-400 hover:bg-neutral-900/60"
                    }`}
                  >
                    <span className="inline-block h-2 w-2 rounded-sm" style={{ backgroundColor: f.language.color }} />
                    <span className="whitespace-nowrap">{f.path.split("/").pop()}</span>
                    <button onClick={(e) => closeTab(f.id, e)} className="text-neutral-600 opacity-0 group-hover:opacity-100 hover:text-neutral-200">
                      <XIcon className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>

              {active ? (
                <CodeEditor
                  key={active.id}
                  value={active.content}
                  ext={active.language.ext}
                  onChange={updateContent}
                  onCursor={(line, col) => setCursor({ line, col })}
                />
              ) : (
                <div className="flex flex-1 items-center justify-center text-neutral-600">
                  Select a file to start editing.
                </div>
              )}
            </div>

            {/* Webview preview */}
            {previewOpen && (
              <div className="flex w-1/2 min-w-0 flex-col bg-white">
                <div className="flex h-9 shrink-0 items-center justify-between border-b border-neutral-800 bg-neutral-950 px-3 text-xs text-neutral-400">
                  <span className="inline-flex items-center gap-1.5">
                    <MonitorIcon className="h-4 w-4" /> Webview {entry ? `· ${entry}` : ""}
                  </span>
                  <div className="flex items-center gap-2">
                    <button onClick={rebuildPreview} className="hover:text-neutral-100" title="Reload preview">
                      <RefreshIcon className="h-4 w-4" />
                    </button>
                    <button onClick={() => setPreviewOpen(false)} className="hover:text-neutral-100" title="Close preview">
                      <XIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                {entry ? (
                  <iframe
                    title="preview"
                    srcDoc={previewDoc}
                    className="min-h-0 flex-1 border-0 bg-white"
                    sandbox="allow-scripts allow-pointer-lock allow-modals allow-forms allow-popups"
                  />
                ) : (
                  <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-neutral-500">
                    Add an <code className="mx-1 rounded bg-neutral-100 px-1 text-neutral-800">index.html</code> to
                    preview it live here — just like CodePen.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Bottom panel */}
          {panelOpen && (
            <div className="flex h-48 shrink-0 flex-col border-t border-neutral-800 bg-neutral-950">
              <div className="flex h-8 shrink-0 items-center gap-4 border-b border-neutral-800 px-3 text-xs">
                <PanelTab label="Terminal" active={panelTab === "terminal"} onClick={() => setPanelTab("terminal")} />
                <PanelTab label="Problems" active={panelTab === "problems"} onClick={() => setPanelTab("problems")} />
                <button onClick={() => setPanelOpen(false)} className="ml-auto text-neutral-500 hover:text-neutral-200">
                  <XIcon className="h-3.5 w-3.5" />
                </button>
              </div>
              <div className="min-h-0 flex-1 overflow-auto p-3 font-mono text-xs">
                {panelTab === "terminal" ? (
                  term ? (
                    <>
                      <div className="text-neutral-500">$ {term.command}</div>
                      {term.stdout && <div className="whitespace-pre-wrap text-neutral-100">{term.stdout}</div>}
                      {term.stderr && <div className="whitespace-pre-wrap text-red-400">{term.stderr}</div>}
                      {term.mode === "terminal" && (
                        <div className={term.exit_code === 0 ? "text-emerald-400" : "text-red-400"}>
                          [exit {term.exit_code}]
                        </div>
                      )}
                      {term.mode === "preview" && <div className="text-emerald-400">Running in the webview →</div>}
                    </>
                  ) : (
                    <span className="text-neutral-600">Press Run. Web projects open the webview; Python runs here.</span>
                  )
                ) : (
                  <span className={msg ? "text-red-400" : "text-neutral-600"}>{msg ?? "No problems detected."}</span>
                )}
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Status bar */}
      <footer className="flex h-6 shrink-0 items-center justify-between bg-indigo-600 px-3 text-[11px] text-white">
        <div className="flex items-center gap-3">
          {deployedSlug ? (
            <Link href={`/games/${deployedSlug}`} className="hover:underline">● Deployed — Open game</Link>
          ) : (
            <span>Draft</span>
          )}
          <button onClick={() => setPanelOpen((v) => !v)} className="inline-flex items-center gap-1 hover:underline">
            <TerminalIcon className="h-3 w-3" /> Terminal
          </button>
        </div>
        <div className="flex items-center gap-3">
          <span>{saved ? "Saved" : "Saving…"}</span>
          <span>Ln {cursor.line}, Col {cursor.col}</span>
          <span>Spaces: 2</span>
          <span>{active ? active.language.label : "Plain Text"}</span>
        </div>
      </footer>
    </div>
  );
}

function readErr(err: ApiError): string {
  if (err.data && typeof err.data === "object") {
    const v = Object.values(err.data as Record<string, unknown>)[0];
    return Array.isArray(v) ? String(v[0]) : String(v);
  }
  return String(err.data);
}

function ToolbarButton({
  children,
  active,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      {...rest}
      className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 disabled:opacity-50 ${
        active ? "border-indigo-500 bg-indigo-500/10 text-indigo-300" : "border-neutral-700 text-neutral-200 hover:bg-neutral-800"
      }`}
    >
      {children}
    </button>
  );
}

function ActivityIcon({
  children,
  active,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      {...rest}
      className={`flex h-10 w-10 items-center justify-center rounded-md ${
        active ? "text-white" : "text-neutral-500 hover:text-neutral-200"
      }`}
    >
      {children}
    </button>
  );
}

function PanelTab({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`border-b-2 py-1.5 ${active ? "border-indigo-400 text-neutral-100" : "border-transparent text-neutral-500 hover:text-neutral-300"}`}
    >
      {label}
    </button>
  );
}
