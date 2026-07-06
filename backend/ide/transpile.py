"""A tiny, dependency-free TypeScript→JavaScript stripper.

This is NOT a real compiler — it removes the most common type-only syntax so a
``.ts`` file can run in the browser (live preview and deployed game). It handles
the constructs used by our starter templates and typical gameplay code:
type-only imports, ``interface`` / ``type`` declarations, and ``: Type``
annotations on parameters, variables and return types, ``as`` casts and the
non-null ``!`` operator.

The source is never mutated in place — if a project needs full TypeScript, add a
real build step. Worst case a mis-strip shows a runtime error in the preview; no
source is lost. The frontend mirrors this logic in ``lib/preview.ts`` so the live
webview and the deployed bundle behave the same.
"""

import re

_INTERFACE = re.compile(r"^[ \t]*(?:export\s+)?(?:declare\s+)?interface\s+\w+[^{]*\{[\s\S]*?^\}[ \t]*;?\s*$", re.M)
_TYPE_ALIAS = re.compile(r"^[ \t]*(?:export\s+)?type\s+\w+[^=]*=[\s\S]*?;[ \t]*$", re.M)
_IMPORT_TYPE = re.compile(r"^[ \t]*import\s+type\s+[^;\n]*;?[ \t]*$", re.M)
_EXPORT_TYPE = re.compile(r"^[ \t]*export\s+type\s+[^;\n]*;?[ \t]*$", re.M)
# `: Type` annotations up to a delimiter — keeps ternaries (`? :`) intact by
# requiring the colon to hug the identifier it annotates.
_ANNOTATION = re.compile(
    r"(\b[A-Za-z_$][\w$]*\??)\s*:\s*"
    r"([A-Za-z_$][\w$.]*(?:\s*<[^;={}()]*>)?(?:\s*\[\s*\])*(?:\s*\|\s*[A-Za-z_$][\w$.\[\] ]*)*)"
)
_AS_CAST = re.compile(r"\s+as\s+[A-Za-z_$][\w$.<>\[\] |]*")
# Return-type annotations: `): Type {` / `): Type =>` / `): Type;`.
_RETURN_TYPE = re.compile(
    r"\)\s*:\s*[A-Za-z_$][\w$.<>\[\] |]*(?=\s*(?:\{|=>|;))"
)
# Postfix non-null `!` (after an identifier, ) or ]) — not `!=`, not prefix `!`.
_NON_NULL = re.compile(r"([\w)\]])\!(?=[.\s;,)\]])")


def strip_types(src: str) -> str:
    s = src
    s = _IMPORT_TYPE.sub("", s)
    s = _EXPORT_TYPE.sub("", s)
    s = _INTERFACE.sub("", s)
    s = _TYPE_ALIAS.sub("", s)
    s = _AS_CAST.sub("", s)
    s = _RETURN_TYPE.sub(")", s)
    # Only strip annotations on lines that look like declarations/params to avoid
    # eating object-literal colons; run a couple of passes for chained params.
    for _ in range(2):
        s = _ANNOTATION.sub(_annotation_repl, s)
    s = _NON_NULL.sub(r"\1", s)
    return s


def _annotation_repl(m: re.Match) -> str:
    name = m.group(1)
    # Preserve object-literal keys ("foo: bar") — those are followed by a value,
    # not a type in declaration position. Heuristic: a capitalised type or a
    # known primitive after the colon is treated as a type annotation.
    type_txt = m.group(2)
    head = type_txt.split("<")[0].split("[")[0].split("|")[0].strip()
    primitives = {
        "string", "number", "boolean", "any", "unknown", "void", "never",
        "object", "bigint", "symbol", "null", "undefined", "this",
    }
    if head in primitives or (head[:1].isupper()):
        return name
    return m.group(0)  # leave untouched (likely an object literal key)


def to_js_name(path: str) -> str:
    """``game.ts`` / ``game.tsx`` → ``game.js`` (leaves other names unchanged)."""
    for ext in (".tsx", ".ts"):
        if path.endswith(ext):
            return path[: -len(ext)] + ".js"
    return path
