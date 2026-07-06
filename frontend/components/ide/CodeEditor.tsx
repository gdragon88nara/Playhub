"use client";

import { useLayoutEffect, useMemo, useRef } from "react";

// A dependency-free code editor: line-number gutter + a transparent <textarea>
// layered over a highlighted <pre> (the classic overlay trick). Highlighting is
// best-effort and never blocks editing — on any failure it falls back to plain
// escaped text.

const JS_KW = new Set("await async break case catch class const continue debugger default delete do else export extends finally for function if import in instanceof let new of return static super switch this throw try typeof var void while with yield true false null undefined".split(" "));
const TS_KW = new Set([...JS_KW, ...("interface type enum implements namespace declare readonly public private protected abstract as satisfies keyof infer".split(" "))]);
const PY_KW = new Set("and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield True False None self print range".split(" "));
const CSS_KW = new Set("important inherit initial unset auto none flex grid block inline absolute relative fixed".split(" "));

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function highlightCode(code: string, keywords: Set<string>, lineComment: string): string {
  const lc = lineComment.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(
    `(${lc}[^\\n]*|/\\*[\\s\\S]*?\\*/)` +
      "|(`(?:\\\\.|[^`\\\\])*`|\"(?:\\\\.|[^\"\\\\])*\"|'(?:\\\\.|[^'\\\\])*')" +
      "|(\\b\\d[\\w.]*\\b)" +
      "|([A-Za-z_$][\\w$]*)",
    "g",
  );
  let out = "";
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(code))) {
    if (m.index > last) out += esc(code.slice(last, m.index));
    if (m[1]) out += `<span class="tok-c">${esc(m[1])}</span>`;
    else if (m[2]) out += `<span class="tok-s">${esc(m[2])}</span>`;
    else if (m[3]) out += `<span class="tok-n">${esc(m[3])}</span>`;
    else out += keywords.has(m[4]) ? `<span class="tok-k">${esc(m[4])}</span>` : esc(m[4]);
    last = re.lastIndex;
  }
  out += esc(code.slice(last));
  return out;
}

function highlightMarkup(code: string): string {
  const re = /(<!--[\s\S]*?-->)|(<\/?[A-Za-z][\w-]*|\/?>)|("(?:\\.|[^"])*"|'(?:\\.|[^'])*')/g;
  let out = "";
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(code))) {
    if (m.index > last) out += esc(code.slice(last, m.index));
    if (m[1]) out += `<span class="tok-c">${esc(m[1])}</span>`;
    else if (m[2]) out += `<span class="tok-t">${esc(m[2])}</span>`;
    else out += `<span class="tok-s">${esc(m[3])}</span>`;
    last = re.lastIndex;
  }
  out += esc(code.slice(last));
  return out;
}

function highlight(code: string, ext: string): string {
  try {
    if (["html", "htm", "xml", "svg"].includes(ext)) return highlightMarkup(code);
    if (["ts", "tsx"].includes(ext)) return highlightCode(code, TS_KW, "//");
    if (["js", "mjs", "cjs", "jsx", "json"].includes(ext)) return highlightCode(code, JS_KW, "//");
    if (["py"].includes(ext)) return highlightCode(code, PY_KW, "#");
    if (["css"].includes(ext)) return highlightCode(code, CSS_KW, "/*dummy*/");
    if (["c", "h", "cpp", "cc", "hpp", "rs", "go", "java", "cs"].includes(ext))
      return highlightCode(code, JS_KW, "//");
    return esc(code);
  } catch {
    return esc(code);
  }
}

export function CodeEditor({
  value,
  ext,
  onChange,
  onCursor,
  disabled,
}: {
  value: string;
  ext: string;
  onChange: (v: string) => void;
  onCursor?: (line: number, col: number) => void;
  disabled?: boolean;
}) {
  const taRef = useRef<HTMLTextAreaElement>(null);
  const preRef = useRef<HTMLPreElement>(null);
  const gutterRef = useRef<HTMLDivElement>(null);

  const lineCount = useMemo(() => value.split("\n").length, [value]);
  const html = useMemo(() => highlight(value, ext) + "\n", [value, ext]);

  // Keep the highlight layer and gutter scroll-synced with the textarea.
  function syncScroll() {
    const ta = taRef.current;
    if (!ta) return;
    if (preRef.current) {
      preRef.current.scrollTop = ta.scrollTop;
      preRef.current.scrollLeft = ta.scrollLeft;
    }
    if (gutterRef.current) gutterRef.current.scrollTop = ta.scrollTop;
  }
  useLayoutEffect(syncScroll, [value]);

  function reportCursor() {
    const ta = taRef.current;
    if (!ta || !onCursor) return;
    const upto = ta.value.slice(0, ta.selectionStart);
    const lines = upto.split("\n");
    onCursor(lines.length, lines[lines.length - 1].length + 1);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    const ta = taRef.current;
    if (!ta) return;
    if (e.key === "Tab") {
      e.preventDefault();
      const s = ta.selectionStart;
      const en = ta.selectionEnd;
      const next = value.slice(0, s) + "  " + value.slice(en);
      onChange(next);
      requestAnimationFrame(() => {
        ta.selectionStart = ta.selectionEnd = s + 2;
      });
    }
  }

  const shared = "m-0 p-3 font-mono text-[13px] leading-[1.5] whitespace-pre";
  const tab = { tabSize: 2 } as const;

  return (
    <div className="flex min-h-0 flex-1 overflow-hidden bg-neutral-950">
      <div
        ref={gutterRef}
        aria-hidden
        className="select-none overflow-hidden border-r border-neutral-800 bg-neutral-950 py-3 pr-2 pl-3 text-right font-mono text-[13px] leading-[1.5] text-neutral-600"
      >
        {Array.from({ length: lineCount }, (_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </div>
      <div className="relative min-w-0 flex-1">
        <pre
          ref={preRef}
          aria-hidden
          style={tab}
          className={`${shared} pointer-events-none absolute inset-0 overflow-auto text-neutral-100`}
          dangerouslySetInnerHTML={{ __html: html }}
        />
        <textarea
          ref={taRef}
          value={value}
          disabled={disabled}
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
          wrap="off"
          style={tab}
          onChange={(e) => onChange(e.target.value)}
          onScroll={syncScroll}
          onKeyUp={reportCursor}
          onClick={reportCursor}
          onKeyDown={onKeyDown}
          className={`${shared} absolute inset-0 resize-none overflow-auto border-0 bg-transparent text-transparent caret-white outline-none`}
        />
      </div>
    </div>
  );
}
