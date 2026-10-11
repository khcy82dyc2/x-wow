#!/usr/bin/env python3
"""Write src/data/numbers_gel.json: the fingerprints of red-team gel S3 and the rerun check, for the download section.

Stdlib only:  python tools/numbers_gel.py [ORIGINAL_DIR] [RERUN_DIR]
Defaults (in the SWELL repo, next to site/; data/ is git-ignored there, so the numbers are the record):
  ../data/sim/S3           the gel the red-team score was computed on (software/redteam/s3_gen.py)
  ../data/sim/S3_regen_dry  a rerun of the same script into another folder (2026-10-10)
Refuses to write unless both runs decompress to identical bytes and their .json.gz differ only inside the gzip
MTIME field (header bytes 4-7, RFC 1952).
"""
import gzip
import hashlib
import json
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
REPO = SITE.parent
ORIG = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "data" / "sim" / "S3"
RERUN = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO / "data" / "sim" / "S3_regen_dry"
OUT = SITE / "src" / "data" / "numbers_gel.json"
MTIME = range(4, 8)
N = {}


def put(key, value, source, how):
    key = "gel." + key
    if key in N:
        sys.exit(f"duplicate key {key}")
    N[key] = {"value": value, "source": source, "how": how}


for name in ("obs", "truth"):
    a, b = (ORIG / f"{name}.json.gz").read_bytes(), (RERUN / f"{name}.json.gz").read_bytes()
    ja, jb = gzip.decompress(a), gzip.decompress(b)
    if ja != jb:
        sys.exit(f"{name}.json: the rerun differs once decompressed; the page's claim would be false")
    diff = [i for i in range(max(len(a), len(b))) if i >= min(len(a), len(b)) or a[i] != b[i]]
    if any(i not in MTIME for i in diff):
        sys.exit(f"{name}.json.gz: bytes outside the gzip MTIME field differ: {diff[:10]}")
    src = (f"data/sim/S3/{name}.json.gz (our private project files, not in the download; "
           "regenerate it with software/redteam/s3_gen.py from the download)")
    put(f"{name}_sha256", hashlib.sha256(ja).hexdigest(), src,
        "SHA-256 of the decompressed JSON; the rerun gave the same bytes (tools/numbers_gel.py)")
    put(f"{name}_bytes", f"{len(ja):,}", src, "size of the decompressed JSON in bytes")

OUT.write_text(json.dumps(N, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
print(f"wrote {len(N)} numbers -> {OUT.relative_to(SITE)}")
