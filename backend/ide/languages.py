"""Map file extensions to a language name, mark colour, and *runtime class*.

The IDE names files as ``name.ext`` (e.g. ``main.py``); the language, its
coloured mark, and how it runs are derived from the extension. Kept in one place
so the API and the frontend agree.

runtime classes
---------------
* ``browser``  — runs live in the in-IDE webview preview (CodePen / Live Server
  style). HTML/CSS/JS/TS and WebAssembly all execute in the browser sandbox.
* ``terminal`` — runs in the server terminal (e.g. ``python main.py``).
* ``compiled`` — compiles to WebAssembly / native for the game engine and needs
  the hardened sandbox runtime (Rust, C, C++, …). This is where the big engine
  performance comes from: these compile down to WASM that runs at near-native
  speed in the browser.
* ``asset``    — data/markup with no run step of its own (json, md, glsl, …).
"""

# ext -> (language label, hex colour, runtime class)
LANGUAGES = {
    # -- browser (live preview) ------------------------------------------------
    "html": ("HTML", "#E34F26", "browser"),
    "htm": ("HTML", "#E34F26", "browser"),
    "css": ("CSS", "#1572B6", "browser"),
    "js": ("JavaScript", "#F7DF1E", "browser"),
    "mjs": ("JavaScript", "#F7DF1E", "browser"),
    "cjs": ("JavaScript", "#F7DF1E", "browser"),
    "jsx": ("React (JSX)", "#61DAFB", "browser"),
    "ts": ("TypeScript", "#3178C6", "browser"),
    "tsx": ("React (TSX)", "#61DAFB", "browser"),
    "wasm": ("WebAssembly", "#654FF0", "browser"),
    "wat": ("WebAssembly Text", "#654FF0", "browser"),
    # -- terminal --------------------------------------------------------------
    "py": ("Python", "#3776AB", "terminal"),
    "rb": ("Ruby", "#701516", "terminal"),
    "php": ("PHP", "#4F5D95", "terminal"),
    "sh": ("Shell", "#89E051", "terminal"),
    # -- compiled → WebAssembly / native (game-engine performance path) --------
    "rs": ("Rust", "#DEA584", "compiled"),
    "c": ("C", "#555555", "compiled"),
    "h": ("C Header", "#555555", "compiled"),
    "cpp": ("C++", "#00599C", "compiled"),
    "cc": ("C++", "#00599C", "compiled"),
    "cxx": ("C++", "#00599C", "compiled"),
    "hpp": ("C++ Header", "#00599C", "compiled"),
    "cs": ("C#", "#178600", "compiled"),
    "java": ("Java", "#B07219", "compiled"),
    "go": ("Go", "#00ADD8", "compiled"),
    # -- assets ----------------------------------------------------------------
    "json": ("JSON", "#CBCB41", "asset"),
    "glsl": ("GLSL", "#5686A5", "asset"),
    "vert": ("GLSL Vertex", "#5686A5", "asset"),
    "frag": ("GLSL Fragment", "#5686A5", "asset"),
    "md": ("Markdown", "#9E9E9E", "asset"),
    "txt": ("Text", "#9E9E9E", "asset"),
    "svg": ("SVG", "#FFB13B", "asset"),
}

DEFAULT = ("Text", "#9E9E9E", "asset")


def ext_of(path: str) -> str:
    return path.rsplit(".", 1)[-1].lower() if "." in path else ""


def language_for(path: str):
    label, color, runtime = LANGUAGES.get(ext_of(path), DEFAULT)
    return {"ext": ext_of(path), "label": label, "color": color, "runtime": runtime}


def runtime_for(path: str) -> str:
    return LANGUAGES.get(ext_of(path), DEFAULT)[2]
