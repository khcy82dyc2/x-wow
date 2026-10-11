#!/usr/bin/env python3
"""Numbers for the £5 laser-diffraction sarcomere experiment (stdlib only).

Run:  python tools/numbers_laser.py            (from site/)
In:   the reference sarcomere lengths, fact F-10 of the SWELL repo (pm/VERIFIED_FACTS.md), copied unchanged
      into src/data/swell/laser_F-10.md whenever the private repo is present, and read from that copy.
Out:  src/data/numbers_laser.json   (keys laser.*, each {value, source, how})

Physics: a muscle fibre is a grating with period SL (sarcomere length). Order m leaves at angle θ_m with
SL · sin θ_m = m λ. On a screen at distance L the spot sits x = L · tan θ_m from the centre, and back again
sin θ = x / √(x² + L²), so SL = m λ √(x² + L²) / x.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
REPO_FACTS = SITE.parent / "pm" / "VERIFIED_FACTS.md"
COPY = SITE / "src" / "data" / "swell" / "laser_F-10.md"
OUT = SITE / "src" / "data" / "numbers_laser.json"
COPY_REL = "src/data/swell/laser_F-10.md"
SCRIPT = "tools/numbers_laser.py"

LAMBDA_NM = {"red": 650.0, "green": 532.0}   # nominal wavelengths printed on class-2 pointers
L_CM = (10, 20)                              # worked-example screen distances
# A7-11 (2026-10-10): a price read from a UK distributor's page that itself states the class and wavelength.
# Rapid Electronics 35-6024, Whadda MP1000: "Output: <1 mW (class II)", "Wavelength: 650 nm", 2x AAA cells;
# "Unit Price (Ex VAT)" £14.86, read 2026-10-10. Named as a price source only.
COST_EX_VAT = 14.86
COST_SRC = ("Rapid Electronics product page, order code 35-6024 (Whadda MP1000: Class 2, <1 mW, 650 nm, AAA cells), "
            "https://www.rapidonline.com/whadda-mp1000-laser-pointer-abs-housing-35-6024, £14.86 ex VAT, read 2026-10-10")


def refresh_copy() -> None:
    """Copy the F-10 row (and its table header) unchanged from the private repo, if it is here."""
    if not REPO_FACTS.is_file():
        return
    lines = REPO_FACTS.read_text(encoding="utf-8").splitlines()
    header = [ln for ln in lines if ln.startswith("| ID |") or ln.startswith("|---|")][:2]
    row = [ln for ln in lines if ln.startswith("| F-10 |")]
    if len(header) != 2 or len(row) != 1:
        raise SystemExit("numbers_laser: could not find the F-10 row in pm/VERIFIED_FACTS.md")
    COPY.parent.mkdir(parents=True, exist_ok=True)
    COPY.write_text("\n".join(header + row) + "\n", encoding="utf-8")


def reference_sl() -> tuple[float, float]:
    text = COPY.read_text(encoding="utf-8")
    m = re.search(r"SL: ([0-9.]+) µm normal vs ([0-9.]+) µm wooden breast", text)
    if not m:
        raise SystemExit("numbers_laser: F-10 text no longer matches")
    return float(m.group(1)), float(m.group(2))


def x_mm(order: int, lam_um: float, sl_um: float, l_mm: float) -> float | None:
    s = order * lam_um / sl_um
    if s >= 1:
        return None
    return l_mm * math.tan(math.asin(s))


def sl_from_x(order: int, lam_um: float, x: float, l_mm: float) -> float:
    return order * lam_um * math.hypot(x, l_mm) / x


def main() -> None:
    refresh_copy()
    sl = dict(zip(("normal", "wb"), reference_sl()))
    src_f10 = f"{COPY_REL} (SWELL pm/VERIFIED_FACTS.md F-10; Soglia, Petracci & Puolanne 2020, doi:10.1080/1828051X.2020.1761271)"
    n: dict[str, dict[str, str]] = {}

    def put(key: str, value: str, source: str, how: str) -> None:
        n[key] = {"value": value, "source": source, "how": how}

    put("laser.sl.normal", f"{sl['normal']:.2f} µm", src_f10, "F-10 as published (laser diffraction, normal breast)")
    put("laser.sl.wb", f"{sl['wb']:.2f} µm", src_f10, "F-10 as published (laser diffraction, wooden breast)")
    put("laser.ref.normal_um", f"{sl['normal']:.2f}", src_f10, "F-10 normal, bare number for the calculator")
    put("laser.ref.wb_um", f"{sl['wb']:.2f}", src_f10, "F-10 wooden breast, bare number for the calculator")
    put("laser.sl.diff", f"{sl['wb'] - sl['normal']:.2f} µm", src_f10, "wooden breast minus normal")
    put("laser.sl.diff_pct", f"{round(100 * (sl['wb'] / sl['normal'] - 1))}%", src_f10, "wooden breast / normal - 1")
    for c, lam in LAMBDA_NM.items():
        put(f"laser.lambda.{c}", f"{lam:.0f} nm", SCRIPT, "nominal pointer wavelength (input)")
    put("laser.cost", f"£{COST_EX_VAT * 1.2:.2f}", COST_SRC,
        "one price source, with UK VAT (20%) added; named as a price source only, not as a place to buy")
    for c, lam_nm in LAMBDA_NM.items():
        lam = lam_nm / 1000.0
        for l_cm in L_CM:
            l_mm = 10.0 * l_cm
            tag = f"{c}.L{l_cm}"
            how_x = f"x = L·tan(asin(mλ/SL)), λ {lam_nm:.0f} nm, L {l_cm} cm"
            for s, slv in sl.items():
                x1 = x_mm(1, lam, slv, l_mm)
                x2 = x_mm(2, lam, slv, l_mm)
                put(f"laser.theta.{tag}.{s}", f"{math.degrees(math.asin(lam / slv)):.1f}°", f"{SCRIPT} + {COPY_REL}",
                    f"first-order angle asin(λ/SL), λ {lam_nm:.0f} nm")
                put(f"laser.x1.{tag}.{s}", f"{x1:.1f} mm", f"{SCRIPT} + {COPY_REL}", how_x + ", m = 1")
                put(f"laser.span.{tag}.{s}", f"{2 * x1:.1f} mm", f"{SCRIPT} + {COPY_REL}",
                    "distance between the two first-order spots, 2x")
                put(f"laser.x2.{tag}.{s}", "none" if x2 is None else f"{x2:.0f} mm", f"{SCRIPT} + {COPY_REL}",
                    how_x + ", m = 2 (none if 2λ/SL ≥ 1)")
            gap = x_mm(1, lam, sl["normal"], l_mm) - x_mm(1, lam, sl["wb"], l_mm)
            put(f"laser.gap.{tag}", f"{gap:.1f} mm", f"{SCRIPT} + {COPY_REL}",
                "x1(normal) - x1(wooden breast): how far apart the two predictions land")
            x1n = x_mm(1, lam, sl["normal"], l_mm)
            dsl = lam * l_mm ** 2 / (x1n ** 2 * math.hypot(x1n, l_mm))
            put(f"laser.dsl.{tag}", f"{dsl:.3f} µm", f"{SCRIPT} + {COPY_REL}",
                "|dSL/dx| = λL²/(x²√(x²+L²)) at the normal SL: SL change for a 1 mm misreading of x")
    # A worked measurement: read the red, 20 cm, normal-meat spot to the nearest millimetre and go back to SL.
    x_read = round(x_mm(1, LAMBDA_NM["red"] / 1000, sl["normal"], 200.0))
    put("laser.demo.x", f"{x_read} mm", f"{SCRIPT} + {COPY_REL}", "x1 for red, L 20 cm, normal SL, rounded to 1 mm")
    put("laser.demo.x_mm", f"{x_read}", f"{SCRIPT} + {COPY_REL}", "laser.demo.x as a bare number (calculator default)")
    put("laser.demo.sl", f"{sl_from_x(1, LAMBDA_NM['red'] / 1000, x_read, 200.0):.2f} µm", SCRIPT,
        "SL = λ√(x²+L²)/x with that rounded x (red, L 20 cm)")
    put("laser.demo.L", "20 cm", SCRIPT, "worked-measurement screen distance (input)")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(n, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(SITE).as_posix()}: {len(n)} keys")
    for k in ("laser.x1.red.L10.normal", "laser.x1.red.L10.wb", "laser.x1.red.L20.normal", "laser.x1.green.L20.wb",
              "laser.gap.red.L20", "laser.dsl.red.L10", "laser.dsl.red.L20", "laser.demo.sl", "laser.x2.red.L10.normal"):
        print(f"  {k} = {n[k]['value']}")


if __name__ == "__main__":
    main()
