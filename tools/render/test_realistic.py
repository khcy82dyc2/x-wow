#!/usr/bin/env python3
"""Tests for the Realistic view, run on a throwaway copy of the site so the real tree is never touched.

    python tools/render/test_realistic.py            the build cases (stdlib only)
    python tools/render/test_realistic.py --browser  also the button in headless Chrome (Playwright); screenshots in
                                                     .render-work/test/shots/

Build cases, each on a fresh copy of src/, tools/ and build.py in .render-work/test/:
  fresh      the renders match the model: the button and its view list are on the SWELL page, the renders are copied;
  stale      one comment added to the model file: the build still passes, says so, leaves the button out and
             publishes no render;
  kit        one comment added to the shared shape kit: stale the same way;
  unlisted   a stray file in the renders folder: the build fails;
  unlabelled a listed render replaced by one without the label in its metadata: the build fails;
  missing    a listed render deleted from the copy: the build fails.
"""
from __future__ import annotations

import http.server
import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path

SITE = Path(__file__).resolve().parents[2]
WORK = SITE / ".render-work" / "test"
OK, FAILS = [], []


def copy_site(name: str) -> Path:
    dst = WORK / name
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    shutil.copytree(SITE / "src", dst / "src")
    shutil.copytree(SITE / "tools", dst / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    for f in ("build.py", "README.md", ".zenodo.json", "CITATION.cff", "LICENSE"):
        if (SITE / f).exists():
            shutil.copy(SITE / f, dst / f)
    return dst


def build(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(root / "build.py")], cwd=root, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def expect(name: str, cond: bool, detail: str = ""):
    (OK if cond else FAILS).append(name + ("" if cond else f": {detail}"))
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else f": {detail}"))


def page(root: Path) -> str:
    return (root / "docs" / "swell" / "index.html").read_text(encoding="utf-8")


def build_cases():
    r = build(c := copy_site("fresh"))
    expect("fresh: build passes", r.returncode == 0, r.stderr[-300:])
    expect("fresh: the button is on the page", 'data-act="realistic"' in page(c))
    expect("fresh: its view list is on the page", 'class="rv-data"' in page(c))
    expect("fresh: the renders are published", any((c / "docs" / "assets" / "renders" / "swell").glob("*.avif")))
    views = json.loads((c / "src" / "data" / "renders.json").read_text(encoding="utf-8"))["models"]["swell"]["views"]
    expect("fresh: every view has an 800 px JPEG for browsers without AVIF or WebP, published",
           all((c / "docs" / v["files"].get("jpg", {}).get("800", "missing")).is_file() for v in views))

    for name, rel in (("stale", "src/assets/js/models/swell.js"), ("kit", "src/assets/js/model-kit.js")):
        c = copy_site(name)
        with (c / rel).open("a", encoding="utf-8") as f:
            f.write("\n// a change the renders haven't seen\n")
        r = build(c)
        expect(f"{name}: build still passes", r.returncode == 0, r.stderr[-300:])
        expect(f"{name}: the build says the renders are stale", "WARN realistic view swell: renders stale" in r.stdout)
        expect(f"{name}: no button", 'data-act="realistic"' not in page(c) and "rv-data" not in page(c))
        expect(f"{name}: no render published", not (c / "docs" / "assets" / "renders" / "swell").exists())

    c = copy_site("unlisted")
    (c / "src" / "assets" / "renders" / "swell" / "stray.webp").write_bytes(b"RIFF")
    r = build(c)
    expect("unlisted: build fails", r.returncode != 0 and "doesn't list" in r.stdout + r.stderr, r.stdout[-300:])

    c = copy_site("unlabelled")
    man = json.loads((c / "src" / "data" / "renders.json").read_text(encoding="utf-8"))
    first = man["models"]["swell"]["views"][0]["files"]["webp"]["800"]
    from_bytes = (c / "src" / first).read_bytes()
    (c / "src" / first).write_bytes(from_bytes.replace(b"X-WOW RENDERED CONCEPT", b"X-WOW something else!!"))
    r = build(c)
    expect("unlabelled: build fails", r.returncode != 0 and "without its label" in r.stdout + r.stderr, r.stdout[-300:])

    c = copy_site("missing")
    (c / "src" / first).unlink()
    r = build(c)
    expect("missing: build fails", r.returncode != 0 and "is missing" in r.stdout + r.stderr, r.stdout[-300:])


class Quiet(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript",
                      ".avif": "image/avif", ".webp": "image/webp"}

    def log_message(self, *a):
        pass


def browser_cases():
    from playwright.sync_api import sync_playwright
    docs = WORK / "fresh" / "docs"
    shots = WORK / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    handler = lambda *a, **k: Quiet(*a, directory=str(docs), **k)  # noqa: E731
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/swell/"
    try:
        with sync_playwright() as p:
            try:
                b = p.chromium.launch(channel="chrome", headless=True)
            except Exception:  # noqa: BLE001
                b = p.chromium.launch(headless=True)
            for label, args, q in (
                    ("desktop-en", {"viewport": {"width": 1366, "height": 900}}, ""),
                    ("desktop-zh", {"viewport": {"width": 1366, "height": 900}}, "&lang=zh"),
                    ("phone-en", {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 2, "is_mobile": True,
                                  "has_touch": True}, ""),
                    ("phone-zh", {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 2, "is_mobile": True,
                                  "has_touch": True}, "&lang=zh"),
                    # small phones (life 10's AI review: at 360 px or less the render shrank to about 200 px under the note)
                    ("phone360-en", {"viewport": {"width": 360, "height": 740}, "device_scale_factor": 2, "is_mobile": True,
                                     "has_touch": True}, ""),
                    ("phone320-zh", {"viewport": {"width": 320, "height": 640}, "device_scale_factor": 2, "is_mobile": True,
                                     "has_touch": True}, "&lang=zh")):
                ctx = b.new_context(reduced_motion="reduce", **args)
                pg = ctx.new_page()
                errs, renders = [], []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
                pg.on("request", lambda r: renders.append(r.url) if "/assets/renders/" in r.url else None)
                pg.goto(base + "?noboot=1" + q, wait_until="load")
                pg.wait_for_timeout(600)
                btn = pg.locator('#hero .cm-tools [data-act="realistic"]')
                expect(f"{label}: the button shows before the 3D model loads", btn.is_visible())
                expect(f"{label}: the model's own buttons wait for the model",
                       not pg.locator('#hero .cm-tools [data-act="explode"]').is_visible())
                expect(f"{label}: no render is fetched before the button is pressed", not renders, str(renders[:2]))
                btn.scroll_into_view_if_needed()
                btn.click()
                pg.wait_for_function("() => { const i = document.querySelector('#hero .rv-img'); return i && i.complete && i.naturalWidth > 0; }",
                                     timeout=15000)
                fallback = pg.evaluate("() => document.querySelector('#hero .rv-img').getAttribute('src')")
                expect(f"{label}: the <img> fallback is the labelled JPEG", (fallback or "").endswith("-800.jpg"), str(fallback))
                info = pg.evaluate("""() => { const i = document.querySelector('#hero .rv-img');
                    return { src: i.currentSrc, w: i.naturalWidth, alt: i.alt, pressed: document.querySelector('#hero [data-act=realistic]').getAttribute('aria-pressed'),
                             note: document.querySelector('#hero .rv-note').innerText, honest: document.querySelector('#hero .rv-honest').innerText }; }""")
                phone = label.startswith("phone")
                # naturalWidth is in CSS pixels for a srcset image (1600 w at sizes 1100px reads 1100), so check the file
                expect(f"{label}: AVIF loads ({'800' if phone else '1600'} px)",
                       info["src"].endswith(f"-{800 if phone else 1600}.avif") and info["w"] > 0, json.dumps(info)[:200])
                zh = label.endswith("zh")
                expect(f"{label}: label, alt and note in the page's language",
                       ("渲染概念图" in info["honest"] and "不是照片" in info["alt"] and "个部件中的" in info["note"]) if zh
                       else ("RENDERED CONCEPT" in info["honest"] and "not a photograph" in info["alt"]
                             and "of the model's" in info["note"]),
                       json.dumps(info, ensure_ascii=False)[:240])
                pg.locator("#hero .cm").screenshot(path=str(shots / f"{label}-front.png"))
                if phone:
                    m = pg.evaluate("""() => { const cm = document.querySelector('#hero .cm'), rv = cm.querySelector('.rv'),
                        img = rv.querySelector('.rv-img'), note = rv.querySelector('.rv-note');
                        return { vw: innerWidth, img: img.getBoundingClientRect().width, cm: cm.getBoundingClientRect().height,
                                 rv: rv.getBoundingClientRect().height, noteBottom: note.getBoundingClientRect().bottom,
                                 cmBottom: cm.getBoundingClientRect().bottom }; }""")
                    expect(f"{label}: the picture keeps most of the screen's width",
                           m["img"] >= 0.8 * m["vw"], json.dumps(m))
                    expect(f"{label}: the stage grows to the panel, so nothing is cut off",
                           m["cm"] + 1 >= m["rv"] and m["noteBottom"] <= m["cmBottom"] + 1, json.dumps(m))
                pg.locator("#hero .rv-view").nth(2).click()
                pg.wait_for_function("() => document.querySelector('#hero .rv-img').currentSrc.includes('/top-')", timeout=10000)
                pg.wait_for_function("() => { const i = document.querySelector('#hero .rv-img'); return i.complete && i.naturalWidth > 0; }", timeout=10000)
                expect(f"{label}: the angle buttons switch the render", True)
                if phone:
                    btn.focus()
                    pg.keyboard.press("Escape")
                    expect(f"{label}: Escape on the button closes it and gives the stage its height back",
                           not pg.locator("#hero .rv").is_visible()
                           and pg.evaluate("() => document.querySelector('#hero .cm').style.height") == "")
                if label == "desktop-en":
                    pg.locator("#hero .cm").screenshot(path=str(shots / f"{label}-top.png"))
                    pg.keyboard.press("Escape")
                    expect(f"{label}: Escape closes it", not pg.locator("#hero .rv").is_visible())
                    pg.locator("#hero .cm-load").click()
                    pg.wait_for_selector("#hero .cm.is-live", timeout=30000)
                    expect(f"{label}: the model's buttons appear once it is live",
                           pg.locator('#hero .cm-tools [data-act="explode"]').is_visible())
                    btn.click()
                    expect(f"{label}: the render covers the live model", pg.locator("#hero .rv").is_visible())
                    pg.locator('#hero .cm-tools [data-act="explode"]').click()
                    expect(f"{label}: a model button brings the model back",
                           not pg.locator("#hero .rv").is_visible() and btn.get_attribute("aria-pressed") == "false")
                    pg.locator("#hero").screenshot(path=str(shots / f"{label}-toolbar-live.png"))
                expect(f"{label}: no errors", not errs, "; ".join(errs[:2]))
                ctx.close()
            # Safari before 14 (old iPads) has no MediaQueryList.addEventListener: the button must still work
            ctx = b.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
            ctx.add_init_script("Object.defineProperty(MediaQueryList.prototype, 'addEventListener', {value: undefined});")
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(base + "?noboot=1", wait_until="load")
            pg.wait_for_timeout(400)
            pg.locator('#hero .cm-tools [data-act="realistic"]').click()
            try:
                pg.wait_for_function("() => { const i = document.querySelector('#hero .rv-img'); return i && i.complete && i.naturalWidth > 0; }",
                                     timeout=10000)
                opened = True
            except Exception:  # noqa: BLE001
                opened = False
            expect("old Safari (no MediaQueryList.addEventListener): the button still opens the renders", opened and not errs,
                   "; ".join(errs[:2]))
            ctx.close()
            b.close()
    finally:
        srv.shutdown()


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    build_cases()
    if "--browser" in sys.argv[1:]:
        browser_cases()
    print(f"{len(OK)} passed, {len(FAILS)} failed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
