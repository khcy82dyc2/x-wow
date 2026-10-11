"""The Realistic view's bookkeeping, stdlib only (build.py imports it; tools/render/realistic_view.py makes the renders).

A concept model lives in src/assets/js/models/<id>.js and is built with src/assets/js/model-kit.js. Its renders live in
src/assets/renders/<id>/ and are listed in src/data/renders.json under the SHA-256 of those two files (line endings
normalised, so a Windows checkout and a Linux one agree). When a model file changes, its hash no longer matches: the
build leaves the Realistic view button out and does not publish the old renders, and says which command renders the
model again. A render can never show a model that has moved on.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
SRC = SITE / "src"
MANIFEST = SRC / "data" / "renders.json"
MARK = "X-WOW RENDERED CONCEPT"   # every render carries these bytes in its metadata; build.py looks for them
LABEL = {"en": "Rendered concept · not yet built", "zh": "渲染概念图 · 尚未造出"}


def sources(model: str) -> list[str]:
    if not re.fullmatch(r"[a-z0-9-]+", model):
        raise ValueError(f"bad model id {model!r}")
    return ["assets/js/model-kit.js", f"assets/js/models/{model}.js"]


def model_hash(model: str) -> str:
    h = hashlib.sha256()
    for rel in sources(model):
        text = (SRC / rel).read_bytes().replace(b"\r\n", b"\n")
        h.update(rel.encode() + b"\n" + text + b"\n")
    return "sha256:" + h.hexdigest()


def load() -> dict:
    if not MANIFEST.exists():
        return {"models": {}}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def status(model: str, manifest: dict | None = None) -> tuple[str, dict | None]:
    """('fresh', entry) when the renders match the model; ('stale', entry) when the model has changed since;
    ('none', None) when it has never been rendered."""
    entry = (manifest or load()).get("models", {}).get(model)
    if not entry:
        return "none", None
    return ("fresh" if entry.get("hash") == model_hash(model) else "stale"), entry


def files(entry: dict) -> list[str]:
    return [f for v in entry["views"] for fmt in v["files"].values() for f in fmt.values()]


def button_html(model: str, root: str, entry: dict) -> str:
    """The toolbar button plus the view list it reads (inline JSON: the images load only when it is pressed)."""
    data = {
        "model": model, "parts": entry["parts"], "label": LABEL,
        "views": [{"id": v["id"], "name": v["name"], "alt": v["alt"], "visible": len(v["visible"]),
                   "width": v["width"], "height": v["height"],
                   "files": {fmt: {w: root + f for w, f in sizes.items()} for fmt, sizes in v["files"].items()}}
                  for v in entry["views"]],
        "note": entry["note"],
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return ('<button type="button" class="cm-btn" data-act="realistic" aria-pressed="false" '
            f'data-renders="{html.escape(model, quote=True)}"><span class="en">Realistic view</span>'
            '<span class="zh">写实效果图</span></button>'
            f'<script type="application/json" class="rv-data" data-renders="{html.escape(model, quote=True)}">{blob}</script>')


def check(manifest: dict | None = None) -> list[str]:
    """Problems that fail the build: a listed file missing or unlabelled, an unlisted file in the renders folder, a
    view list that doesn't account for every part."""
    manifest = manifest or load()
    problems, listed = [], set()
    for model, entry in manifest.get("models", {}).items():
        try:
            sources(model)
        except ValueError as e:
            problems.append(f"renders.json: {e}")
            continue
        ids = entry.get("part_ids", [])
        if len(ids) != entry.get("parts") or len(set(ids)) != len(ids):
            problems.append(f"renders.json: {model}: part_ids don't match its part count")
        seen = set()
        for v in entry.get("views", []):
            seen.update(v.get("visible", []))
            for f in [f for fmt in v["files"].values() for f in fmt.values()]:
                listed.add(f)
                p = SRC / f
                if not p.exists():
                    problems.append(f"renders.json: {f} is missing")
                elif MARK.encode() not in p.read_bytes():
                    problems.append(f"{f}: a render without its label in the file metadata ({MARK})")
        if seen != set(ids):
            problems.append(f"renders.json: {model}: the views show {len(seen)} of its {len(ids)} parts "
                            f"(missing: {', '.join(sorted(set(ids) - seen))})")
    folder = SRC / "assets" / "renders"
    for p in sorted(folder.rglob("*")) if folder.exists() else []:
        rel = p.relative_to(SRC).as_posix()
        if p.is_file() and rel not in listed:
            problems.append(f"{rel}: a file in the renders folder that src/data/renders.json doesn't list")
    return problems
