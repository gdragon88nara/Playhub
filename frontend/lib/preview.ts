// Live webview preview — a CodePen / Live Server style renderer that runs a
// web project entirely in the browser, no server round-trip.
//
// Given the project's files (path -> content) and an entry HTML, it inlines the
// referenced stylesheets and scripts into a single self-contained document that
// an <iframe srcDoc> can render. `.ts`/`.tsx` sources are transpiled to JS with
// the same lightweight stripper the backend uses on deploy (backend
// ide/transpile.py), so the live preview matches the deployed bundle.

/** Lightweight TypeScript -> JavaScript: strips type-only syntax. Not a real
 *  compiler; mirrors backend ide/transpile.py. */
export function stripTypes(src: string): string {
  let s = src;
  s = s.replace(/^[ \t]*import\s+type\s+[^;\n]*;?[ \t]*$/gm, "");
  s = s.replace(/^[ \t]*export\s+type\s+[^;\n]*;?[ \t]*$/gm, "");
  // interface Blocks
  s = s.replace(/^[ \t]*(?:export\s+)?(?:declare\s+)?interface\s+\w+[^{]*\{[\s\S]*?^\}[ \t]*;?\s*$/gm, "");
  // type Alias = ...;
  s = s.replace(/^[ \t]*(?:export\s+)?type\s+\w+[^=]*=[\s\S]*?;[ \t]*$/gm, "");
  // as Casts
  s = s.replace(/\s+as\s+[A-Za-z_$][\w$.<>[\] |]*/g, "");
  // return-type Annotations: `): Type {` / `): Type =>` / `): Type;`
  s = s.replace(/\)\s*:\s*[A-Za-z_$][\w$.<>[\] |]*(?=\s*(?:\{|=>|;))/g, ")");
  // : Type annotations (only when the type looks like a type, not an object key)
  const annotation = /(\b[A-Za-z_$][\w$]*\??)\s*:\s*([A-Za-z_$][\w$.]*(?:\s*<[^;={}()]*>)?(?:\s*\[\s*\])*(?:\s*\|\s*[A-Za-z_$][\w$.[\] ]*)*)/g;
  const primitives = new Set([
    "string", "number", "boolean", "any", "unknown", "void", "never",
    "object", "bigint", "symbol", "null", "undefined", "this",
  ]);
  const repl = (m: string, name: string, type: string) => {
    const head = type.split("<")[0].split("[")[0].split("|")[0].trim();
    return primitives.has(head) || /^[A-Z]/.test(head) ? name : m;
  };
  for (let i = 0; i < 2; i++) s = s.replace(annotation, repl);
  // non-null Assertions (postfix `!` after ident/`)`/`]`; not `!=`, not prefix `!`)
  s = s.replace(/([\w)\]])!(?=[.\s;,)\]])/g, "$1");
  return s;
}

function normalize(ref: string): string {
  return ref.replace(/^\.?\//, "").replace(/^\//, "");
}

/** Resolve a referenced path to file content, tolerating ./ and / prefixes and
 *  compiling `.ts`/`.tsx` when a `.js` reference has only a TS source. */
function lookupScript(files: Record<string, string>, ref: string): string | null {
  const key = normalize(ref);
  if (key in files) {
    return /\.(ts|tsx)$/.test(key) ? stripTypes(files[key]) : files[key];
  }
  if (key.endsWith(".js")) {
    const base = key.slice(0, -3);
    for (const ext of [".ts", ".tsx"]) {
      if (base + ext in files) return stripTypes(files[base + ext]);
    }
  }
  return null;
}

function lookupText(files: Record<string, string>, ref: string): string | null {
  const key = normalize(ref);
  return key in files ? files[key] : null;
}

/** Build a self-contained HTML document for the preview iframe. */
export function buildPreviewDoc(files: Record<string, string>, entry: string): string {
  const html = files[entry] ?? "";
  if (typeof window === "undefined" || typeof DOMParser === "undefined") return html;

  let doc: Document;
  try {
    doc = new DOMParser().parseFromString(html, "text/html");
  } catch {
    return html;
  }

  doc.querySelectorAll('link[rel="stylesheet"][href]').forEach((link) => {
    const css = lookupText(files, link.getAttribute("href") || "");
    if (css != null) {
      const style = doc.createElement("style");
      style.textContent = css;
      link.replaceWith(style);
    }
  });

  doc.querySelectorAll("script[src]").forEach((sc) => {
    const code = lookupScript(files, sc.getAttribute("src") || "");
    if (code != null) {
      const script = doc.createElement("script");
      const type = sc.getAttribute("type");
      // A TS module becomes plain JS; keep real module types, drop TS ones.
      if (type && type !== "text/typescript" && type !== "application/typescript") {
        script.setAttribute("type", type);
      }
      script.textContent = code;
      sc.replaceWith(script);
    }
  });

  return "<!doctype html>\n" + doc.documentElement.outerHTML;
}

/** Which entry HTML to preview (root index.html preferred). */
export function webEntry(files: Record<string, string>): string | null {
  for (const name of ["index.html", "index.htm"]) if (name in files) return name;
  let best: string | null = null;
  let depth = Infinity;
  for (const path of Object.keys(files)) {
    const base = path.split("/").pop()!.toLowerCase();
    if (base === "index.html" || base === "index.htm") {
      const d = path.split("/").length;
      if (d < depth) { best = path; depth = d; }
    }
  }
  return best;
}
