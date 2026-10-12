#!/usr/bin/env python3
"""Render a concept model for the Realistic view, start to finish, in one command.

    python tools/render/realistic_view.py swell [--blender PATH] [--samples 256] [--views front,top]
                                                [--work DIR] [--check-only]

Any concept model works: its file (src/assets/js/models/<id>.js) may carry a `renders` block with its own camera
angles, view names, alt-text descriptions and a note on what its renders leave out; without one, four plain angles
(DEFAULT_VIEWS) and plain words are used, so no model's images are ever described with another model's words.
1. export: opens the model in the site's own viewer (Playwright, headless Chrome), takes every part's meshes in world
   space at the assembled position, exactly as a visitor's browser builds them, and checks the part count;
2. render: Blender (Cycles) builds them in a plain studio (tools/render/scene.py), checks each part's size against
   the export and records which parts each view can see;
3. finish: adds the label "Rendered concept · not yet built" (渲染概念图 · 尚未造出) to every image and writes the
   same words into its EXIF and XMP metadata, then saves WebP and AVIF at 1600 and 800 px wide, and an 800 px JPEG
   for browsers that show neither (the page's <img> fallback);
4. lists them in src/data/renders.json under the model's hash (tools/realistic.py), which build.py checks.
Needs Blender 4.2 or later (--blender, or the BLENDER environment variable), Playwright with a Chrome or Chromium, and
Pillow 11.3 or later (WebP and AVIF). build.py stays stdlib-only: it reads only what this writes.
Old renders of the model are moved into the work folder, never deleted (earlier committed ones stay in git history).
The label is drawn with two fonts that ship with Blender (DejaVu Sans Mono; Noto Sans CJK SC, SIL OFL 1.1).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.server
import io
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

SITE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SITE / "tools"))
import realistic  # noqa: E402

SRC = SITE / "src"
SCENE = Path(__file__).resolve().parent / "scene.py"
WIDTHS = (1600, 800)
JPEG_WIDTH = 800
GOLD, MUTED, BG = (255, 181, 71), (138, 163, 179), (5, 8, 13)

# used for a model whose file has no `renders.views`: plain angles and words that fit any model
DEFAULT_VIEWS = [
    {"id": "front", "az": 34, "el": 21, "name": {"en": "Front right", "zh": "右前方"},
     "alt": {"en": "from the front right, a little above", "zh": "从右前方稍高处看"}},
    {"id": "left", "az": 304, "el": 18, "name": {"en": "Front left", "zh": "左前方"},
     "alt": {"en": "from the front left, a little above", "zh": "从左前方稍高处看"}},
    {"id": "top", "az": 18, "el": 58, "name": {"en": "From above", "zh": "俯视"},
     "alt": {"en": "from high above the front", "zh": "从前上方高处往下看"}},
    {"id": "back", "az": 214, "el": 20, "name": {"en": "Back left", "zh": "左后方"},
     "alt": {"en": "from the back left, a little above", "zh": "从左后方稍高处看"}},
]


def model_views(data: dict) -> list[dict]:
    """The model's own views (its file's `renders.views`), or DEFAULT_VIEWS; each needs an id, angles and both words."""
    views = ((data.get("renders") or {}).get("views")) or DEFAULT_VIEWS
    ids = [v.get("id") for v in views]
    for v in views:
        ok = (isinstance(v.get("id"), str) and v["id"].replace("-", "").isalnum() and v["id"].islower()
              and all(isinstance(v.get(k), (int, float)) for k in ("az", "el"))
              and all(isinstance((v.get(k) or {}).get(L), str) and v[k][L].strip() for k in ("name", "alt") for L in ("en", "zh")))
        if not ok:
            raise SystemExit(f"export: a view in the model's renders block is incomplete: {json.dumps(v, ensure_ascii=False)[:160]}")
    if len(set(ids)) != len(ids):
        raise SystemExit("export: two views in the model's renders block share an id")
    return views

HARNESS = """<!doctype html><html lang="en" data-lang="en"><head><meta charset="utf-8"><title>export</title>
<style>:root{--cyan:#4fd8ff;--cyan-dim:#2a7f99;--gold:#ffb547;--red:#ff5a4f;--ok:#5cf2b5;--bg:#05080d}
body{margin:0}.cm-stage{position:relative;width:800px;height:600px}</style></head>
<body><section><div data-model="MODEL"><div class="cm-stage"></div></div></section>
<script type="module" src="/assets/js/concept-model.js"></script></body></html>"""

EXPORT_JS = """async () => {
  const root = document.querySelector('[data-model]');
  for (let i = 0; i < 400 && !root.cmModel; i++) await new Promise((r) => setTimeout(r, 50));
  if (!root.cmModel) throw new Error('the viewer never built the model');
  const { THREE, MODEL, parts } = root.cmModel;
  const out = { model: MODEL.id, title: MODEL.title || null, renders: MODEL.renders || null, unit: 'cm', up: 'y',
                count: MODEL.parts.length, parts: [] };
  const t = new THREE.Vector3();
  for (const p of parts) {
    p.group.updateMatrixWorld(true);
    const meshes = [];
    const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
    p.group.traverse((o) => {
      if (!o.isMesh) return;
      const g = o.geometry, pos = g.attributes.position, v = [];
      for (let i = 0; i < pos.count; i++) {
        t.fromBufferAttribute(pos, i).applyMatrix4(o.matrixWorld);
        const c = [t.x, t.y, t.z];
        for (let a = 0; a < 3; a++) { lo[a] = Math.min(lo[a], c[a]); hi[a] = Math.max(hi[a], c[a]); v.push(+c[a].toFixed(5)); }
      }
      const idx = g.index ? Array.from(g.index.array) : Array.from({ length: pos.count }, (_, i) => i);
      meshes.push({ shape: o.userData.shape, mat: o.userData.mat || (MODEL.mats || {})[p.id] || 'pla', v, i: idx });
    });
    out.parts.push({ id: p.id, index: p.index, label: p.label, name: p.name, bbox: [...lo, ...hi], meshes });
  }
  return out;
}"""


# ------------------------------------------------------------------------------------------------------------ export
class Handler(http.server.SimpleHTTPRequestHandler):
    harness = b""
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript"}

    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(SRC), **k)

    def do_GET(self):  # noqa: N802
        if self.path.split("?")[0] == "/__export__.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(self.harness)))
            self.end_headers()
            self.wfile.write(self.harness)
            return
        super().do_GET()

    def log_message(self, *a):
        pass


def export(model: str, work: Path) -> dict:
    from playwright.sync_api import sync_playwright
    Handler.harness = HARNESS.replace("MODEL", model).encode()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            try:
                b = p.chromium.launch(channel="chrome", headless=True)
            except Exception:  # noqa: BLE001  (no Chrome installed: Playwright's own Chromium)
                b = p.chromium.launch(headless=True)
            page = b.new_page(viewport={"width": 800, "height": 600})
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(f"http://127.0.0.1:{srv.server_address[1]}/__export__.html", wait_until="load")
            page.click(".cm-load", timeout=20000)
            data = page.evaluate(EXPORT_JS)
            b.close()
    finally:
        srv.shutdown()
    if errs:
        raise SystemExit("export: the viewer threw: " + "; ".join(errs[:3]))
    if len(data["parts"]) != data["count"] or any(not p["meshes"] for p in data["parts"]):
        raise SystemExit(f"export: {len(data['parts'])} parts built, the model file lists {data['count']}")
    data["views"] = [{"id": v["id"], "az": v["az"], "el": v["el"]} for v in model_views(data)]   # scene.py's cameras
    (work / "export.json").write_text(json.dumps(data), encoding="utf-8")
    meshes = sum(len(p["meshes"]) for p in data["parts"])
    print(f"export: {len(data['parts'])} parts, {meshes} meshes")
    return data


# ------------------------------------------------------------------------------------------------------------ render
def find_blender(arg: str | None) -> Path:
    cand = arg or os.environ.get("BLENDER")
    if not cand:
        raise SystemExit("render: say where Blender is (--blender PATH or the BLENDER environment variable)")
    p = Path(cand)
    if p.is_dir():
        p = p / ("blender.exe" if os.name == "nt" else "blender")
    if not p.exists():
        raise SystemExit(f"render: no Blender at {p}")
    return p


def render(blender: Path, work: Path, samples: int, views: str) -> dict:
    cmd = [str(blender), "-b", "--factory-startup", "-noaudio", "--python-exit-code", "1", "--python", str(SCENE), "--",
           "--input", str(work / "export.json"), "--out", str(work), "--samples", str(samples), "--views", views]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (work / "blender.log").write_text(r.stdout + r.stderr, encoding="utf-8")
    for line in r.stdout.splitlines():
        if line.startswith("scene.py:"):
            print("  " + line)
    if r.returncode:
        raise SystemExit(f"render: Blender failed (log in {work / 'blender.log'}):\n" + (r.stdout + r.stderr)[-1500:])
    return json.loads((work / "render-info.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------------------------ finish
def fonts(blender: Path):
    from PIL import ImageFont
    found = sorted(blender.parent.glob("*/datafiles/fonts"))
    if not found:
        raise SystemExit("finish: Blender's bundled fonts (datafiles/fonts) not found")
    d = found[-1]
    return (lambda s: ImageFont.truetype(str(d / "DejaVuSansMono.woff2"), s),
            lambda s: ImageFont.truetype(str(d / "Noto Sans CJK Regular.woff2"), s))


def xmp(title: str, desc_en: str, desc_zh: str) -> bytes:
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")  # noqa: E731
    return ('<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
            '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            '<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
            'Iptc4xmpExt:DigitalSourceType="http://cv.iptc.org/newscodes/digitalsourcetype/algorithmicMedia">'
            f'<dc:title><rdf:Alt><rdf:li xml:lang="x-default">{esc(title)}</rdf:li></rdf:Alt></dc:title>'
            f'<dc:description><rdf:Alt><rdf:li xml:lang="x-default">{esc(desc_en)}</rdf:li>'
            f'<rdf:li xml:lang="zh-Hans">{esc(desc_zh)}</rdf:li></rdf:Alt></dc:description>'
            '<dc:rights><rdf:Alt><rdf:li xml:lang="x-default">CC0 1.0 Universal (the X-WOW name and logo are not '
            'covered)</rdf:li></rdf:Alt></dc:rights>'
            '</rdf:Description></rdf:RDF></x:xmpmeta>\n<?xpacket end="w"?>').encode("utf-8")


def labelled(im, width: int, mono, cjk, right: str):
    """The render at this width with a strip below it carrying the label; the render's own pixels are not covered."""
    from PIL import Image, ImageDraw
    h = round(im.height * width / im.width)
    body = im.resize((width, h), Image.LANCZOS) if width != im.width else im.copy()
    sh = max(36, round(width * 0.034))
    out = Image.new("RGB", (width, h + sh), BG)
    out.paste(body, (0, 0))
    d = ImageDraw.Draw(out)
    size = round(sh * 0.42)
    f_en, f_zh, f_small = mono(size), cjk(size), mono(max(11, round(size * 0.78)))
    x = round(sh * 0.4)
    y = h + (sh - size) // 2 - 1
    t_en = realistic.LABEL["en"].upper()
    d.text((x, y), t_en, font=f_en, fill=GOLD)
    x += d.textlength(t_en, font=f_en) + size
    d.text((x, y - round(size * 0.12)), realistic.LABEL["zh"], font=f_zh, fill=GOLD)
    x += d.textlength(realistic.LABEL["zh"], font=f_zh) + size
    tw = d.textlength(right, font=f_small)
    if width - round(sh * 0.4) - tw > x:   # the right-hand note only where it fits
        d.text((width - round(sh * 0.4) - tw, h + (sh - f_small.size) // 2), right, font=f_small, fill=MUTED)
    return out


def finish(model: str, data: dict, info: dict, work: Path, blender: Path, views: list[str]) -> dict:
    from PIL import Image
    mono, cjk = fonts(blender)
    title = (data.get("title") or {}).get("en") or model.upper()
    title_zh = (data.get("title") or {}).get("zh") or title
    n = len(data["parts"])
    words = {v["id"]: v for v in model_views(data)}
    folder = SRC / "assets" / "renders" / model
    if folder.exists():   # superseded renders go to the work folder, whole
        keep = work / "superseded" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        keep.mkdir(parents=True)
        for f in folder.iterdir():
            shutil.move(str(f), str(keep / f.name))
    folder.mkdir(parents=True, exist_ok=True)
    entries = []
    for v in info["views"]:
        vid = v["id"]
        if vid not in views:
            continue
        im = Image.open(work / f"{vid}.png").convert("RGB")
        k = len(v["visible"])
        name = words[vid]["name"]
        desc_en = (f"{realistic.MARK}: not a photograph. A Blender (Cycles) render of the {title} concept model "
                   f"({name['en'].lower()} view; it shows {k} of the model's {n} parts, at least in part), made by an "
                   f"AI agent (Claude) for X-WOW from the model's own shapes (edges slightly rounded, open tubes given "
                   f"1 mm walls), with materials guessed from its parts list and nothing added. {title} has not been "
                   f"built.")
        desc_zh = (f"{realistic.MARK}：这不是照片。用 Blender（Cycles）渲染的 {title_zh} 概念模型（{name['zh']}视角；"
                   f"画面里能看到模型 {n} 个部件中的 {k} 个，至少看到一部分），由 AI 智能体（Claude）为 X-WOW 按模型自身的形状制作"
                   f"（棱角稍微倒圆，开口的管子加了 1 毫米的壁），材质按零件清单推测，没有添加任何东西。{title_zh} 尚未造出。")
        exif = Image.Exif()
        exif[270] = desc_en          # ImageDescription
        exif[305] = f"Blender {info['blender']} (Cycles); tools/render/realistic_view.py"   # Software
        exif[33432] = "CC0 1.0 Universal (the X-WOW name and logo are not covered)"        # Copyright
        meta = {"exif": exif.tobytes(), "xmp": xmp(f"{title} · {realistic.LABEL['en']}", desc_en, desc_zh)}
        files = {"avif": {}, "webp": {}, "jpg": {}}
        sizes = {}
        for w in WIDTHS:
            out = labelled(im, w, mono, cjk, f"{title} · {name['en']}")
            sizes[w] = out.size
            kinds = [("avif", "AVIF", {"quality": 60, "speed": 4}), ("webp", "WEBP", {"quality": 82, "method": 6})]
            if w == JPEG_WIDTH:   # for browsers that show neither AVIF nor WebP (Safari before 14): the <img> fallback
                kinds.append(("jpg", "JPEG", {"quality": 82, "optimize": True, "progressive": True}))
            for fmt, pil, kw in kinds:
                rel = f"assets/renders/{model}/{vid}-{w}.{fmt}"
                buf = io.BytesIO()
                out.save(buf, pil, **kw, **meta)
                (SRC / rel).write_bytes(buf.getvalue())
                if realistic.MARK.encode() not in buf.getvalue():
                    raise SystemExit(f"finish: {rel} lost its metadata label on saving")
                files[fmt][str(w)] = rel
        w0, h0 = sizes[WIDTHS[0]]
        a = words[vid]["alt"]
        entries.append({
            "id": vid, "name": name,
            "alt": {"en": f"Rendered concept, not a photograph: the {title} concept model {a['en']}, on a plain dark floor. "
                          f"It shows {k} of the model's {n} parts, at least in part.",
                    "zh": f"渲染概念图，不是照片：{title_zh} 概念模型，{a['zh']}，放在朴素的深色地面上。画面里能看到模型 {n} 个部件中的 {k} 个（至少看到一部分）。"},
            "visible": v["visible"], "width": w0, "height": h0, "files": files,
            "camera": {"azimuth_deg": v["az"], "elevation_deg": v["el"], "distance_m": v["distance_m"],
                       "target_cm": v["target_cm"], "shift_x": v["shift_x"], "shift_y": v["shift_y"],
                       "lens_mm": info["lens_mm"], "sensor_mm": 36, "sensor_fit": "horizontal"},
            "render_s": v["render_s"],
        })
        print(f"finish: {vid}: {k}/{n} parts visible; "
              + ", ".join(f"{Path(f).name} {(SRC / f).stat().st_size // 1024} KiB" for fmt in files.values() for f in fmt.values()))
    return {"entries": entries}


# ------------------------------------------------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("model")
    ap.add_argument("--blender")
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--views", default="", help="only these view ids (default: every view the model's file lists)")
    ap.add_argument("--work", default=str(SITE / ".render-work"))
    ap.add_argument("--check-only", action="store_true", help="say whether the model's renders are fresh, then stop")
    a = ap.parse_args(argv)
    st, entry = realistic.status(a.model)
    print(f"{a.model}: renders {st} (model {realistic.model_hash(a.model)[:19]}…)")
    if a.check_only:
        return 0 if st == "fresh" else 1
    blender = find_blender(a.blender)
    work = Path(a.work).resolve() / a.model
    work.mkdir(parents=True, exist_ok=True)
    h = realistic.model_hash(a.model)
    data = export(a.model, work)
    known = [v["id"] for v in data["views"]]
    views = [v for v in a.views.split(",") if v] or known
    if set(views) - set(known):
        raise SystemExit(f"no view {', '.join(sorted(set(views) - set(known)))} in {a.model}'s file (it has {', '.join(known)})")
    info = render(blender, work, a.samples, ",".join(views))
    if not info["scale_ok"]:
        raise SystemExit(f"render: a part's size in Blender differs from the export (import {info['worst_raw_cm']} cm, "
                         f"with bevels {info['worst_eval_cm']} cm)")
    if [p["id"] for p in info["parts"]] != [p["id"] for p in data["parts"]]:
        raise SystemExit("render: Blender's parts differ from the export's")
    seen = set().union(*(set(v["visible"]) for v in info["views"]))
    missing = [p["id"] for p in data["parts"] if p["id"] not in seen]
    if missing:
        raise SystemExit("render: no view shows " + ", ".join(missing) + " (add or move a view)")
    if realistic.model_hash(a.model) != h:
        raise SystemExit("render: the model file changed while it was rendering; run again")
    out = finish(a.model, data, info, work, blender, views)
    manifest = realistic.load()
    manifest["about"] = ("Every Realistic view render on the site, keyed to the SHA-256 of its model's source files "
                         "(tools/realistic.py). Written by tools/render/realistic_view.py; build.py leaves a model's button "
                         "out, and its renders unpublished, when the hash no longer matches, and fails on any render that "
                         "lacks its label or isn't listed here.")
    title = (data.get("title") or {})
    own = (data.get("renders") or {}).get("note") or {}   # what this model's renders leave out, in its own words
    n = len(data["parts"])
    manifest.setdefault("models", {})[a.model] = {
        "hash": h, "sources": realistic.sources(a.model),
        "parts": len(data["parts"]), "part_ids": [p["id"] for p in data["parts"]],
        "rendered": dt.date.today().isoformat(),
        "renderer": {"blender": info["blender"], "engine": "Cycles", "device": "GPU" if info["device"] != "CPU" else "CPU", "samples": info["samples"],
                     "seed": info["seed"], "denoiser": "OpenImageDenoise", "lens_mm": info["lens_mm"],
                     "resolution": info["resolution"]},
        "scene": "tools/render/scene.py sha256:" + hashlib.sha256(SCENE.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "scale": {"ok": info["scale_ok"], "worst_import_cm": info["worst_raw_cm"], "worst_with_bevels_cm": info["worst_eval_cm"]},
        "label_fonts": ("DejaVu Sans Mono (Bitstream Vera and Arev font licences; DejaVu changes public domain) and Noto Sans CJK SC (SIL Open Font License 1.1), the fonts bundled with Blender, as its license/license.md lists them; only their drawn letters are in the images, not the font files"),
        "note": {
            "en": (f"An AI agent rendered this page's {n}-part concept model in Blender (Cycles): the same shapes and "
                   "proportions with slightly rounded edges and 1 mm walls on its open tubes, and nothing added. The "
                   "materials are guesses from the parts "
                   f"list. {own.get('en', '').strip()} Not a photograph: {title.get('en') or a.model.upper()} has never "
                   "been built.").replace("  ", " "),
            "zh": (f"由 AI 智能体用 Blender（Cycles）渲染本页这个 {n} 个部件的概念模型：形状和比例不变（只把棱角稍微倒圆，并给开口的管子加了 1 毫米的壁），"
                   f"没有添加任何东西。材质是按零件清单猜的。{own.get('zh', '').strip()}这不是照片："
                   f"{title.get('zh') or a.model.upper()} 从来没有造出来过。"),
        },
        "views": out["entries"],
    }
    realistic.MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    problems = realistic.check(manifest)
    if problems:
        raise SystemExit("check: " + "; ".join(problems))
    print(f"{a.model}: {len(out['entries'])} views written; renders.json updated; renders fresh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
