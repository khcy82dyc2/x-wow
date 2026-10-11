#!/usr/bin/env python3
"""Label every simulation figure on the site, on the image itself and in its file metadata.

    python tools/label_figures.py           (needs Pillow; run once per new figure)

Each figure listed in src/data/figures.json gets a strip added ABOVE it (the figure's own pixels are not covered,
only re-encoded once as JPEG) saying in both languages that it is a simulation, plus the same words in the JPEG's
EXIF ImageDescription and a JPEG comment. A figure that already carries the label is left alone, so the script can
be run any number of times. build.py (stdlib only) fails if a listed figure lacks the label, or if an image in the
SWELL image folder isn't listed. The unlabelled originals are the simulation outputs in the SWELL download
(docs/design/figs/), which this site's web copies were cut from.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SITE = Path(__file__).resolve().parents[1]
MANIFEST = SITE / "src" / "data" / "figures.json"
MARK = "X-WOW SIMULATION"   # build.py looks for these bytes


def font(names, size):
    for n in names:   # Pillow also looks in the system font folders
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    sys.exit("no font found for the label strip: " + ", ".join(names))


def label(path: Path, fig: dict) -> str:
    im = Image.open(path)
    desc = (im.getexif() or {}).get(270, "")
    if isinstance(desc, str) and desc.startswith(MARK):
        return "already labelled"
    im = im.convert("RGB")
    w, h = im.size
    sh = max(30, round(w * 0.034))                    # strip height scales with the figure
    out = Image.new("RGB", (w, h + sh), (5, 8, 13))
    out.paste(im, (0, sh))
    d = ImageDraw.Draw(out)
    size = round(sh * 0.5)
    en = font(["segoeuib.ttf", "DejaVuSans-Bold.ttf", "Helvetica.ttc"], size)
    zh = font(["msyhbd.ttc", "msyh.ttc", "NotoSansCJK-Bold.ttc", "NotoSansCJKsc-Bold.otf", "PingFang.ttc"], size)
    x, y = round(sh * 0.35), round((sh - size) / 2) - 1
    t_en = "SIMULATION · synthetic data, not a measurement"
    d.text((x, y), t_en, font=en, fill=(255, 181, 71))
    x += d.textlength(t_en, font=en) + size
    d.text((x, y), "模拟 · 合成数据，不是测量", font=zh, fill=(255, 181, 71))
    exif = Image.Exif()
    exif[270] = (f"{MARK}: synthetic data from SWELL's simulation, not a measurement. Source: {fig['source']}. "
                 "Label strip added above the figure by tools/label_figures.py; the figure itself is unchanged.")
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=88, optimize=True, progressive=True, exif=exif,
             comment=f"{MARK}: synthetic data, not a measurement".encode("ascii"))
    path.write_bytes(buf.getvalue())
    return f"labelled ({w}x{h} -> {w}x{h + sh}, {len(buf.getvalue()) // 1024} KiB)"


def main():
    figs = json.loads(MANIFEST.read_text(encoding="utf-8"))["figures"]
    for fig in figs:
        p = SITE / "src" / fig["file"]
        print(f"{fig['file']}: {label(p, fig)}")


if __name__ == "__main__":
    main()
