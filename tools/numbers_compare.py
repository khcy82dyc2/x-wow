#!/usr/bin/env python3
"""How SWELL's estimated build compares with what labs pay for the same job (src/data/numbers_compare.json).

    python tools/numbers_compare.py

In:  src/data/swell/comparators.json (UK public contract awards, with URLs and read date) and
     src/data/swell/budget_v1.json (SWELL's build: the sum of its listed lines and how many lines are still unpriced).
Out: src/data/numbers_compare.json. D-78 (2026-10-11): no ratio is drawn while any build line is unpriced, because the
     sum of the listed lines is only a floor; the commercial prices are still given. Once every line is listed, a ratio
     is a commercial price divided by SWELL's priced build, written "times SWELL's priced build", never "times cheaper",
     because the commercial systems do more and SWELL has never been built. Stdlib only.
"""
from __future__ import annotations

import json
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DATA = SITE / "src" / "data"
OUT = DATA / "numbers_compare.json"


def gbp(x: float) -> str:
    return f"£{x:,.0f}"


def main():
    c = json.loads((DATA / "swell" / "comparators.json").read_text(encoding="utf-8"))
    b = json.loads((DATA / "swell" / "budget_v1.json").read_text(encoding="utf-8"))["build"]
    like = [r["price_gbp"] / r["per"] for r in c["like_for_like"]]
    floor = [r["price_gbp"] / r["per"] for r in c["manual_floor"]]
    years = sorted(r["awarded"][:4] for r in c["like_for_like"])
    src = f"src/data/swell/comparators.json (UK public contract awards, read {c['read']}) and src/data/swell/budget_v1.json: build"
    how = "commercial price per instrument ÷ SWELL's priced build (every line listed)"
    N = {
        "compare.like_n": {"value": str(len(like)), "source": src, "how": "awards for motorised or automated widefield fluorescence microscopes"},
        "compare.like_years": {"value": f"{years[0]}–{years[-1]}", "source": src, "how": "years of those awards"},
        "compare.like_min": {"value": gbp(min(like)), "source": src, "how": "lowest price per instrument"},
        "compare.like_max": {"value": gbp(max(like)), "source": src, "how": "highest price per instrument (a two-system award divided by two)"},
        "compare.read": {"value": c["read"], "source": src, "how": "date the award notices were read"},
    }
    if b["n_estimate"] == 0:   # D-78: a ratio only against a build whose every line is listed
        t = b["listed"]
        N["compare.ratio_like"] = {"value": f"{min(like) / t:.0f}–{max(like) / t:.0f}×", "source": src, "how": how}
        N["compare.ratio_floor"] = {"value": f"{min(floor) / t:.0f}–{max(floor) / t:.0f}×", "source": src,
                                    "how": "the same against two manual inverted fluorescence microscopes with a camera (no motorised stage)"}
    OUT.write_text(json.dumps(N, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    ratio = (f"like-for-like {N['compare.ratio_like']['value']}, manual floor {N['compare.ratio_floor']['value']}"
             if "compare.ratio_like" in N else f"no ratio: {b['n_estimate']} of {b['n']} build lines not yet priced (D-78)")
    print(f"wrote {OUT.relative_to(SITE)}: {ratio} ({N['compare.like_min']['value']}–{N['compare.like_max']['value']})")


if __name__ == "__main__":
    main()
