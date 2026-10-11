#!/usr/bin/env python3
"""Record checked real-world results in src/data/ladder_results.json (stdlib only; no network).

Reports come only by email to info@x-wow.com (the owner's decision, 2026-10-11: email only, no GitHub issues). A result
counts only after the owner forwards a report and it has been checked; then one line records it:

  python tools/ladder_results.py add rung-N passed      a passed rung of the evidence ladder (N = 1..4)
  python tools/ladder_results.py add build built        a working build by someone outside X-WOW
  python tools/ladder_results.py add build rebuilt      an independent rebuild that passes the same QC thresholds
  python tools/ladder_results.py show

The file holds counts, the date each was recorded and nothing about the person who sent the report (no name, handle,
address or place). Run tools/evidence_bar.py afterwards. Until 2026-10-11 this script counted labelled GitHub issues
through api.github.com; every count was 0 when that stopped.
"""
import datetime as dt
import json
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
OUT = SITE / "src" / "data" / "ladder_results.json"
SOURCE = "checked reports of real builds that the owner forwards from info@x-wow.com"


def load():
    d = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    d.setdefault("rungs_passed", {str(n): 0 for n in (1, 2, 3, 4)})
    d.setdefault("built", 0)
    d.setdefault("rebuilt", 0)
    d.setdefault("recorded", [])
    d["source"] = SOURCE
    return d


def main(argv):
    d = load()
    if argv[:1] == ["add"] and len(argv) == 3:
        kind, result = argv[1], argv[2]
        if kind.startswith("rung-") and kind[5:] in d["rungs_passed"] and result == "passed":
            d["rungs_passed"][kind[5:]] += 1
        elif kind == "build" and result in ("built", "rebuilt"):
            d[result] += 1
        else:
            sys.exit(f"unknown result: {kind} {result}")
        today = dt.date.today().isoformat()
        d["recorded"].append({"date": today, "kind": kind, "result": result})
        d["fetched"] = today   # read by evidence_bar.py as the date of the last change
        OUT.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    elif argv not in ([], ["show"]):
        sys.exit(__doc__)
    print(json.dumps(d, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
