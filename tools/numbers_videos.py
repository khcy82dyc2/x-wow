#!/usr/bin/env python3
"""Numbers for the science-videos pages: when the channel's videos came out (src/data/numbers_videos.json).

    python tools/numbers_videos.py

In:  the private YouTube Data API dump the project keeps outside this repo (<SWELL repo>/pm/site/youtube-comments/
     raw-*.json.gz, git-ignored), which holds each video's publish date. Only publish dates are read: no comment,
     title or person. On a public checkout without the dump, the numbers recorded last time are kept.
Out: src/data/numbers_videos.json. Stdlib only.
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
RAW = SITE.parent / "pm" / "site" / "youtube-comments"
OUT = SITE / "src" / "data" / "numbers_videos.json"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def month(ym: str, zh=False) -> str:
    y, m = ym.split("-")
    return f"{y} 年 {int(m)} 月" if zh else f"{MONTHS[int(m) - 1]} {y}"


def main():
    dumps = sorted(RAW.glob("raw-*.json.gz")) if RAW.exists() else []
    if not dumps:
        if OUT.exists():
            print(f"no private dump here: keeping {OUT.relative_to(SITE)} as recorded")
            return
        sys.exit("numbers_videos: no private dump and no recorded numbers")
    dump = dumps[-1]
    d = json.load(gzip.open(dump, "rt", encoding="utf-8"))
    dates = sorted(v["published_at"][:7] for v in d["videos"].values())   # YYYY-MM only
    n = len(dates)
    years = sorted({x[:4] for x in dates})
    # the smallest span of whole years that holds at least 90% of the dated videos
    best = None
    for i, a in enumerate(years):
        for b in years[i:]:
            k = sum(a <= x[:4] <= b for x in dates)
            if k >= 0.9 * n and (best is None or int(b) - int(a) < int(best[1]) - int(best[0])):
                best = (a, b, k)
    a, b, k_years = best
    core = sum("2021-09" <= x <= "2022-09" for x in dates)
    src = (f"YouTube Data API videos.list, publish dates read {d['fetched_at'][:10]} "
           "(public on each video's YouTube page; tools/numbers_videos.py)")
    N = {
        "videos.n_dated": {"value": str(n), "source": src, "how": "videos with a publish date in the dump"},
        "videos.n_channel": {"value": str(d["channel"]["video_count"]), "source": src, "how": "video count the channel reported"},
        "videos.core_years": {"value": a if a == b else f"{a}–{b}", "source": src,
                              "how": "the shortest span of whole years holding at least 90% of the dated videos"},
        "videos.n_core_years": {"value": str(k_years), "source": src, "how": "dated videos inside those years"},
        "videos.n_core": {"value": str(core), "source": src, "how": "dated videos published September 2021 to September 2022"},
        "videos.first": {"value": month(dates[0]), "source": src, "how": "month of the first dated video"},
        "videos.last": {"value": month(dates[-1]), "source": src, "how": "month of the last dated video"},
        "videos.first_zh": {"value": month(dates[0], True), "source": src, "how": "the same, in Chinese"},
        "videos.last_zh": {"value": month(dates[-1], True), "source": src, "how": "the same, in Chinese"},
    }
    OUT.write_text(json.dumps(N, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(SITE)}: {n} dated videos, {k_years} in {N['videos.core_years']['value']}, "
          f"{core} from September 2021 to September 2022")


if __name__ == "__main__":
    main()
