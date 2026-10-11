#!/usr/bin/env python3
"""Numbers for the Slide Library page: each slide's size, the total pixels and the upload dates.

    python tools/numbers_slides.py           (from the stored snapshot; no network)
    python tools/numbers_slides.py --fetch   (re-read the image host's public metadata first, one request a second)

The slides are the image-host links in src/pages/slide-library/30-slides.html. --fetch reads each one's public
metadata (https://www.easyzoom.com/api/image/urlaccess/<id>) and keeps only the fields used here in
src/data/slides/easyzoom-<date>.json. Out: src/data/numbers_slides.json. Stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
PAGE = SITE / "src" / "pages" / "slide-library" / "30-slides.html"
SNAP_DIR = SITE / "src" / "data" / "slides"
OUT = SITE / "src" / "data" / "numbers_slides.json"
API = "https://www.easyzoom.com/api/image/urlaccess/"
KEEP = ("Id", "Title", "Width", "Height", "DateAdded")


def ids() -> list[str]:
    return re.findall(r"easyzoom\.com/imageaccess/([0-9a-f]{32})", PAGE.read_text(encoding="utf-8"))


def fetch() -> Path:
    rows = []
    for i in ids():
        req = urllib.request.Request(API + i, headers={"User-Agent": "X-WOW site check (info@x-wow.com)",
                                                       "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        rows.append({"link_id": i, **{k: d.get(k) for k in KEEP}})
        time.sleep(1)
    snap = SNAP_DIR / f"easyzoom-{date.today().isoformat()}.json"
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    snap.write_text(json.dumps({"read": date.today().isoformat(), "api": API + "<link id>", "slides": rows},
                               ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return snap


def main():
    snap = fetch() if "--fetch" in sys.argv else max(SNAP_DIR.glob("easyzoom-*.json"), default=None)
    if snap is None:
        sys.exit("numbers_slides: no snapshot yet: run with --fetch")
    s = json.loads(snap.read_text(encoding="utf-8"))
    by_id = {r["link_id"]: r for r in s["slides"]}
    missing = [i for i in ids() if i not in by_id]
    if missing:
        sys.exit(f"numbers_slides: the page links {len(missing)} slide(s) the snapshot lacks: run with --fetch")
    src = f"src/data/slides/{snap.name} (the image host's public metadata, read {s['read']})"
    N, total, dates = {}, 0, []
    for i in ids():
        r = by_id[i]
        w, h = r["Width"], r["Height"]
        total += w * h
        dates.append(r["DateAdded"][:10])
        N[f"slides.{i[:8]}.size"] = {"value": f"{w:,} × {h:,} px · {round(w * h / 1e6):,} MP", "source": src,
                                     "how": "width × height in pixels, and their product in megapixels (10⁶ pixels)"}
    biggest = max(ids(), key=lambda i: by_id[i]["Width"] * by_id[i]["Height"])
    if biggest[:8] != "72f25122":   # the page's loupe names the ant as the biggest
        sys.exit("numbers_slides: the biggest slide is no longer the ant; update the Slide Library's loupe")
    N["slides.max_mp"] = {"value": str(round(by_id[biggest]["Width"] * by_id[biggest]["Height"] / 1e6)), "source": src,
                          "how": "the biggest slide (the ant) in megapixels"}
    N["slides.n"] = {"value": str(len(ids())), "source": src, "how": "slides linked on the page"}
    N["slides.total_bn"] = {"value": f"{total / 1e9:.1f}", "source": src, "how": "sum of width × height, in billions of pixels"}
    N["slides.total_yi"] = {"value": f"{round(total / 1e8)}", "source": src, "how": "the same, in 亿 (10⁸ pixels)"}
    N["slides.first_upload"] = {"value": min(dates), "source": src, "how": "earliest upload date (DateAdded)"}
    N["slides.last_upload"] = {"value": max(dates), "source": src, "how": "latest upload date (DateAdded)"}
    OUT.write_text(json.dumps(N, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(SITE)}: {len(ids())} slides, {total / 1e9:.2f} billion pixels, "
          f"uploaded {min(dates)} to {max(dates)}")


if __name__ == "__main__":
    main()
