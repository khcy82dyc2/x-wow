#!/usr/bin/env python3
"""Make every X-WOW logo file the site uses, from the two original files of the old x-wow.com.

    python tools/make_brand.py                   (needs Pillow and NumPy; build.py itself stays stdlib-only)
    python tools/make_brand.py --no-registered   the same, without the (R) mark (only if the registration lapses)

Inputs, never edited (src/assets/img/brand/original/):
  xwow-logo-original.png   the old site's header logo, 2274 x 2004, on white
  xwow-icon-original.png   the old site's favicon, 952 x 948, transparent
Nothing is redrawn. The white around the logo becomes transparent: each edge pixel is un-mixed
into white plus the logo's own flat colours, so no white fringe shows on a dark page. The white
inside the ring stays, as in the original, so the dark parts of the microscope stay visible
(the old favicon's see-through centre is filled with white to match).
On dark backgrounds the black (R) mark is shown in the page's light text colour.
Proof: the transparent logo laid back over white must reproduce the original (printed at the end).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "src" / "assets" / "img"
BRAND = IMG / "brand"
ORIG = BRAND / "original"

# The logo's flat colours, read from the original (each one fills thousands of pixels).
FLAT = np.array([
    (235, 84, 54), (238, 69, 70), (252, 125, 20), (51, 51, 51), (244, 49, 135),
    (226, 44, 126), (252, 214, 6), (11, 176, 196), (102, 102, 102), (193, 39, 44)], float)
WHITE = np.array([255.0, 255.0, 255.0])
BG = (5, 8, 13)            # site --bg
LIGHT = (216, 238, 246)    # site --text: the (R) mark on dark backgrounds
NO_R = "--no-registered" in sys.argv[1:]
DARK_HEIGHTS = (64, 128, 192, 288)   # header, footer and boot screen (srcset)
LIGHT_HEIGHTS = (192, 288)           # README on GitHub's light theme


def ring_fit(fg, guess, r_lo, r_hi):
    """Circle through the ring's outer edge: the farthest foreground pixel per half-degree."""
    ys, xs = np.nonzero(fg)
    dx, dy = xs - guess[0], ys - guess[1]
    r = np.hypot(dx, dy)
    k = (r > r_lo) & (r < r_hi)
    ang = np.round(np.degrees(np.arctan2(dy[k], dx[k])) * 2).astype(int)
    order = np.lexsort((-r[k], ang))
    _, first = np.unique(ang[order], return_index=True)
    i = order[first]
    x, y = xs[k][i] + 0.5, ys[k][i] + 0.5
    A = np.column_stack([x, y, np.ones_like(x)])
    D, E, F = np.linalg.lstsq(A, -(x * x + y * y), rcond=None)[0]
    cx, cy = -D / 2, -E / 2
    R = float(np.sqrt(cx * cx + cy * cy - F))
    # ring thickness: walk inwards from the outer edge until the background shows
    t = []
    for a in np.radians(np.arange(0, 360, 3)):
        for s in np.arange(0.5, 80, 0.5):
            px, py = int(cx + (R - s) * np.cos(a)), int(cy + (R - s) * np.sin(a))
            if not fg[py, px]:
                t.append(s)
                break
    return float(cx), float(cy), R, float(np.median(t)), len(i)


def disc(shape, cx, cy, r):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return np.hypot(xx + 0.5 - cx, yy + 0.5 - cy) < r


def unmix(p):
    """Model each pixel as white plus at most two flat colours: p = W - a(W - Ci) - b(W - Cj).
    Returns alpha = a + b, the un-mixed colour and the fit residual (0-255 units)."""
    D = WHITE - FLAT
    V = WHITE - p
    n = len(p)
    best = np.full(n, np.inf)
    alpha = np.zeros(n)
    rec = np.zeros((n, 3))
    for i in range(len(FLAT)):  # one colour
        a = np.clip(V @ D[i] / (D[i] @ D[i]), 0, 1)
        r = a[:, None] * D[i]
        res = np.linalg.norm(V - r, axis=1)
        w = res < best
        best[w], alpha[w], rec[w] = res[w], a[w], r[w]
    for i in range(len(FLAT)):  # two colours (where two flat colours and white meet)
        for j in range(i + 1, len(FLAT)):
            G = np.array([[D[i] @ D[i], D[i] @ D[j]], [D[i] @ D[j], D[j] @ D[j]]])
            if np.linalg.det(G) < 1e-6 * G[0, 0] * G[1, 1]:
                continue  # two greys: a single colour already covers this mix
            ab = np.linalg.solve(G, np.stack([V @ D[i], V @ D[j]]))
            a, b = ab
            over = a + b > 1  # no white in the mix: slide along the edge between the two colours
            if over.any():
                d = FLAT[i] - FLAT[j]
                s = np.clip(((p[over] - FLAT[j]) @ d) / (d @ d), 0, 1)
                a, b = a.copy(), b.copy()
                a[over], b[over] = s, 1 - s
            ok = (a >= 0) & (b >= 0)
            r = a[:, None] * D[i] + b[:, None] * D[j]
            res = np.where(ok, np.linalg.norm(V - r, axis=1), np.inf)
            w = res < best - 1.0  # a pair must clearly beat a single colour
            best[w], alpha[w], rec[w] = res[w], (a + b)[w], r[w]
    colour = np.where(alpha[:, None] > 0, WHITE - rec / np.maximum(alpha, 1e-9)[:, None], 0)
    return alpha, colour, best


def make_logo():
    src = Image.open(ORIG / "xwow-logo-original.png").convert("RGB")
    p = np.asarray(src).astype(float)
    H, W, _ = p.shape
    fg = p.min(-1) < 250
    cx, cy, R, t, npts = ring_fit(fg, (1131, 760), 400, 500)
    inside = disc((H, W), cx, cy, R - t / 2)  # the ring's centre line: white stays white inside it
    print(f"logo ring: centre ({cx:.1f}, {cy:.1f}), outer radius {R:.1f} px, thickness {t:.1f} px ({npts} edge points)")

    alpha = np.ones((H, W))
    col = p.copy()
    ink = np.zeros((H, W), bool)
    # the (R) mark: dark, colourless pixels above and beyond the ring; its box gets a grey-ink model
    sat = p.max(-1) - p.min(-1)
    yy, xx = np.mgrid[0:H, 0:W]
    beyond = (np.hypot(xx + 0.5 - cx, yy + 0.5 - cy) > R + 6) & (yy < cy)
    rmark = beyond & (sat < 40) & (p.min(-1) < 200)
    ys, xs = np.nonzero(rmark)
    y0, y1, x0, x1 = ys.min() - 8, ys.max() + 9, xs.min() - 8, xs.max() + 9
    ink[y0:y1, x0:x1] = True
    print(f"(R) mark box: x {x0}-{x1}, y {y0}-{y1}")
    q = p[ink]
    a = np.clip((255 - q.mean(-1)) / (255 - 20), 0, 1)
    alpha[ink] = 0 if NO_R else a
    col[ink] = np.where(a[:, None] > 0, WHITE - (WHITE - q) / np.maximum(a, 1e-9)[:, None], 0)

    pure = (p == 255).all(-1)  # plain white background: fully transparent
    alpha[(~inside) & (~ink) & pure] = 0
    rest = (~inside) & (~ink) & ~pure
    q = p[rest]
    a, c, res = unmix(q)
    keep = res > 12  # pixels the model can't explain stay exactly as they are, fully opaque
    a[keep], c[keep] = 1, q[keep]
    solid = a > 0.995
    a[solid], c[solid] = 1, q[solid]
    a[a < 0.004] = 0
    alpha[rest], col[rest] = a, c
    edge = (a > 0) & (a < 1)
    print(f"edge pixels un-mixed: {int(edge.sum())}; kept as they are: {int(keep.sum())}")

    # proof: lay the result back over white and compare with the original
    back = alpha[..., None] * col + (1 - alpha[..., None]) * WHITE
    diff = np.abs(np.round(back) - p).max(-1)
    if NO_R:
        diff[ink] = 0  # the (R) is left out on purpose
    print(f"fidelity over white: max diff {diff.max():.0f}/255, mean {diff.mean():.3f}, "
          f"pixels off by more than 2: {int((diff > 2).sum())} of {diff.size}")

    ys, xs = np.nonzero(alpha > 0)
    box = (xs.min() - 12, ys.min() - 12, xs.max() + 13, ys.max() + 13)
    col[alpha == 0] = 0
    rgba = np.dstack([np.clip(np.round(col), 0, 255), np.round(alpha * 255)]).astype(np.uint8)
    light = Image.fromarray(rgba, "RGBA").crop(box)
    dark_rgba = rgba.copy()
    m = ink & (alpha > 0)
    dark_rgba[m, :3] = LIGHT
    dark = Image.fromarray(dark_rgba, "RGBA").crop(box)
    return light, dark, (cx - box[0], cy - box[1], R)


def make_icon():
    src = Image.open(ORIG / "xwow-icon-original.png").convert("RGBA")
    a = np.asarray(src)
    H, W, _ = a.shape
    fg = a[..., 3] > 127
    cx, cy, R, t, npts = ring_fit(fg, (W / 2, H / 2), min(H, W) * 0.40, min(H, W) * 0.52)
    print(f"icon ring: centre ({cx:.1f}, {cy:.1f}), outer radius {R:.1f} px, thickness {t:.1f} px ({npts} edge points)")
    side = max(H, W)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    ox, oy = (side - W) // 2, (side - H) // 2
    white = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    ImageDraw.Draw(white).ellipse([ox + cx - R + t / 2, oy + cy - R + t / 2, ox + cx + R - t / 2, oy + cy + R - t / 2],
                                  fill=(255, 255, 255, 255))
    sq.alpha_composite(white)
    sq.alpha_composite(src, (ox, oy))
    return sq


def shrink(im, h):
    w = round(im.width * h / im.height)
    return im.resize((w, h), Image.Resampling.LANCZOS, reducing_gap=3.0)


def tile(icon, size, frac):
    """The round icon centred on a dark square (home-screen icons; Android masks need about 80%)."""
    out = Image.new("RGBA", (size, size), BG + (255,))
    d = round(size * frac)
    out.alpha_composite(icon.resize((d, d), Image.Resampling.LANCZOS, reducing_gap=3.0), ((size - d) // 2, (size - d) // 2))
    return out.convert("RGB")


def font(names, size, required=False):
    for n in names:  # Pillow also looks in the system font folders
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    if required:  # without a CJK font the Chinese line would come out as empty boxes
        sys.exit("no font found for the social preview: " + ", ".join(names))
    return ImageFont.load_default(size)


def make_og(dark, ring):
    """1200 x 630 social preview: the logo under a loupe-style reticle, with the site's line."""
    W, H = 1200, 630
    CYAN, GOLD = (79, 216, 255), (255, 181, 71)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for x in range(0, W, 48):
        d.line([(x, 0), (x, H)], fill=(12, 26, 34))
    for y in range(0, H, 48):
        d.line([(0, y), (W, y)], fill=(12, 26, 34))
    cx, cy = 902, 315
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    g = ImageDraw.Draw(glow)
    for r, w in [(290, 2), (258, 1)]:
        g.ellipse([cx - r, cy - r, cx + r, cy + r], outline=CYAN, width=w)
    for k in range(96):
        a = 2 * np.pi * k / 96
        r1, r2 = (265, 282) if k % 8 else (262, 286)
        g.line([(cx + r1 * np.cos(a), cy + r1 * np.sin(a)), (cx + r2 * np.cos(a), cy + r2 * np.sin(a))], fill=CYAN, width=2)
    g.arc([cx - 274, cy - 274, cx + 274, cy + 274], start=-60, end=10, fill=GOLD, width=4)
    for (x0, y0, x1, y1) in [(cx, cy - 312, cx, cy - 296), (cx, cy + 296, cx, cy + 312), (cx - 320, cy, cx - 296, cy), (cx + 296, cy, cx + 320, cy)]:
        g.line([(x0, y0), (x1, y1)], fill=CYAN, width=2)
    blur = glow.filter(ImageFilter.GaussianBlur(6))
    img = Image.composite(blur, img, blur.convert("L").point(lambda v: int(v * 0.6)))
    img.paste(glow, (0, 0), glow.convert("L").point(lambda v: int(v * 0.5)))
    # logo: its ring centred on the reticle, sized so the whole lockup fits inside the inner circle
    h = 290
    logo = shrink(dark, h)
    s = h / dark.height
    lx, ly = round(cx - ring[0] * s), round(cy - ring[1] * s)
    base = img.convert("RGBA")
    base.alpha_composite(logo, (lx, ly))
    img = base.convert("RGB")
    d = ImageDraw.Draw(img)
    mono = font(["consolab.ttf", "DejaVuSansMono-Bold.ttf", "Menlo.ttc"], 30)
    big = font(["segoeuib.ttf", "DejaVuSans-Bold.ttf", "Helvetica.ttc"], 74)
    zh = font(["msyhbd.ttc", "msyh.ttc", "NotoSansCJK-Bold.ttc", "NotoSansCJKsc-Bold.otf", "PingFang.ttc"], 54, required=True)
    small = font(["segoeui.ttf", "DejaVuSans.ttf", "Helvetica.ttc"], 28)
    d.text((72, 120), "X-WOW  ·  BORDERLESS INVENTION", font=mono, fill=CYAN)
    d.text((72, 190), "Inventions to", font=big, fill=(234, 247, 252))
    d.text((72, 275), "steal, happily.", font=big, fill=GOLD)
    d.text((72, 385), "好发明，开心偷。", font=zh, fill=(234, 247, 252))
    d.text((72, 478), "Free, open designs.", font=small, fill=(134, 167, 181))
    d.text((72, 516), "Whoever builds it claims the success.", font=small, fill=(134, 167, 181))
    return img


def save(im, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, optimize=True)
    kb = path.stat().st_size / 1024
    print(f"  {path.relative_to(ROOT).as_posix():48s} {im.width:4d} x {im.height:<4d} {kb:6.1f} KB")
    if kb > 300:
        sys.exit(f"{path.name} is over 300 KB")


def main():
    light, dark, ring = make_logo()
    icon = make_icon()
    print("written:")
    save(light, BRAND / "xwow-logo.png")
    save(dark, BRAND / "xwow-logo-dark.png")
    for h in DARK_HEIGHTS:
        save(shrink(dark, h), BRAND / f"xwow-logo-dark-{h}.png")
    for h in LIGHT_HEIGHTS:
        save(shrink(light, h), BRAND / f"xwow-logo-{h}.png")
    save(icon, BRAND / "xwow-icon.png")
    save(tile(icon, 180, 0.84), BRAND / "apple-touch-icon.png")
    for n in (192, 512):
        save(tile(icon, n, 0.76), BRAND / f"icon-{n}.png")
    ico = ROOT / "src" / "favicon.ico"
    sizes = [16, 32, 48]
    frames = [icon.resize((n, n), Image.Resampling.LANCZOS, reducing_gap=3.0) for n in sizes]
    frames[-1].save(ico, sizes=[(n, n) for n in sizes], append_images=frames[:-1])
    print(f"  {ico.relative_to(ROOT).as_posix():48s} 16/32/48        {ico.stat().st_size / 1024:6.1f} KB")
    save(make_og(dark, ring), IMG / "og-xwow.png")


if __name__ == "__main__":
    main()
