"""Safe writing of an uploaded game bundle to a protected directory.

Two entry points, both landing files under ``dest_abs`` and returning the
detected entry document (relative, e.g. ``index.html``):

* :func:`extract_bundle` — from a single uploaded ``.zip``.
* :func:`save_files`     — from many files uploaded directly (a folder/file
  selection), each with its relative path. This is the primary path: creators
  drop their code files and folders, no zipping required.
"""

import os
import shutil
import zipfile

# Guardrails against zip bombs / abuse.
MAX_TOTAL_BYTES = 300 * 1024 * 1024   # 300 MB uncompressed
MAX_FILES = 5000


class BundleError(Exception):
    pass


def _is_within(base: str, target: str) -> bool:
    base = os.path.abspath(base)
    target = os.path.abspath(target)
    return os.path.commonpath([base]) == os.path.commonpath([base, target])


def _safe_relpath(name: str) -> str:
    """Normalise an uploaded relative path, rejecting traversal/absolute paths."""
    norm = name.replace("\\", "/").lstrip("/")
    parts = [p for p in norm.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise BundleError(f"Unsafe path in upload: {name}")
    if not parts:
        raise BundleError("A file has no name.")
    return "/".join(parts)


def _reset_dir(dest_abs: str) -> str:
    dest_abs = str(dest_abs)
    if os.path.exists(dest_abs):
        shutil.rmtree(dest_abs)
    os.makedirs(dest_abs, exist_ok=True)
    return dest_abs


def save_files(entries, dest_abs: str) -> str:
    """Write ``entries`` — an iterable of ``(relative_path, uploaded_file)`` — into
    ``dest_abs`` and return the detected entry file. Applies the same guardrails
    as ZIP extraction (no traversal, size/count limits, single-root hoist)."""
    dest_abs = _reset_dir(dest_abs)
    entries = list(entries)
    if not entries:
        raise BundleError("No files uploaded.")
    if len(entries) > MAX_FILES:
        raise BundleError(f"Too many files (>{MAX_FILES}).")

    total = 0
    for raw_name, uploaded in entries:
        rel = _safe_relpath(raw_name)
        total += getattr(uploaded, "size", 0) or 0
        if total > MAX_TOTAL_BYTES:
            raise BundleError("Bundle exceeds the 300 MB size limit.")
        out_path = os.path.join(dest_abs, *rel.split("/"))
        if not _is_within(dest_abs, out_path):
            raise BundleError(f"Path escapes upload dir: {raw_name}")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as dst:
            for chunk in uploaded.chunks():
                dst.write(chunk)

    _hoist_single_root(dest_abs)
    entry = _find_entry(dest_abs)
    if entry is None:
        raise BundleError("No index.html found in the uploaded files.")
    return entry


def extract_bundle(uploaded_zip, dest_abs: str) -> str:
    """Extract ``uploaded_zip`` into the absolute dir ``dest_abs`` and return the
    detected entry file (relative to the extracted root, e.g. ``index.html``).

    Rejects path traversal (Zip-Slip), absolute paths, and oversized bundles.
    If the archive has a single top-level directory, its contents are hoisted
    so the entry file sits at the root.
    """
    dest_abs = str(dest_abs)
    if os.path.exists(dest_abs):
        shutil.rmtree(dest_abs)
    os.makedirs(dest_abs, exist_ok=True)

    try:
        zf = zipfile.ZipFile(uploaded_zip)
    except zipfile.BadZipFile as exc:
        raise BundleError("Uploaded file is not a valid ZIP archive.") from exc

    with zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        if not infos:
            raise BundleError("Archive is empty.")
        if len(infos) > MAX_FILES:
            raise BundleError(f"Too many files (>{MAX_FILES}).")
        total = sum(i.file_size for i in infos)
        if total > MAX_TOTAL_BYTES:
            raise BundleError("Bundle exceeds the 300 MB size limit.")

        for info in infos:
            name = info.filename
            if name.startswith("/") or name.startswith("\\") or ".." in name.split("/"):
                raise BundleError(f"Unsafe path in archive: {name}")
            out_path = os.path.join(dest_abs, name)
            if not _is_within(dest_abs, out_path):
                raise BundleError(f"Path escapes extraction dir: {name}")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with zf.open(info) as src, open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

    _hoist_single_root(dest_abs)
    entry = _find_entry(dest_abs)
    if entry is None:
        raise BundleError("No index.html found in the bundle.")
    return entry


def _hoist_single_root(dest_abs: str) -> None:
    entries = os.listdir(dest_abs)
    if len(entries) == 1 and os.path.isdir(os.path.join(dest_abs, entries[0])):
        inner = os.path.join(dest_abs, entries[0])
        for item in os.listdir(inner):
            shutil.move(os.path.join(inner, item), os.path.join(dest_abs, item))
        os.rmdir(inner)


def _find_entry(dest_abs: str) -> str | None:
    # Prefer a root-level index.html; otherwise the shallowest index.html.
    if os.path.isfile(os.path.join(dest_abs, "index.html")):
        return "index.html"
    best = None
    best_depth = 1_000_000
    for root, _dirs, files in os.walk(dest_abs):
        if "index.html" in files:
            rel = os.path.relpath(os.path.join(root, "index.html"), dest_abs)
            depth = rel.count(os.sep)
            if depth < best_depth:
                best, best_depth = rel.replace(os.sep, "/"), depth
    return best
