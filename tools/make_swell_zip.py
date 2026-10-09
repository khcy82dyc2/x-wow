#!/usr/bin/env python3
"""Build the SWELL G0 download zip from the private SWELL repo, scrubbed (stdlib only).

Run:    python tools/make_swell_zip.py                 (from site/, or give the full path)
Out:    src/downloads/swell-g0-2026-10-09.zip  and  src/data/numbers_download.json
Review: python tools/make_swell_zip.py --dump DIR      (also writes the scrubbed tree to DIR)
Check:  python tools/make_swell_zip.py --check PATH... (scan files or folders for forbidden tokens; exit 1 on a hit)

What goes in: tracked files at git HEAD that are on the allowlist, plus the regenerable data/sim/*.csv,
plus a README, the official licence texts (pinned by SHA-256) and nothing else.

Scrubbing is driven by a PRIVATE rules file that lives outside this public repo: forbidden tokens,
sentence redactions, path renames and replacements (format in that file). Default location:
<SWELL repo>/pm/site/forbidden.txt, or set SWELL_SCRUB_RULES. Without it this script refuses to build.
The build is deterministic (sorted members, fixed timestamps), so the SHA-256 is reproducible.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import os
import re
import struct
import subprocess
import sys
import tarfile
import zipfile
import zlib
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
REPO = SITE.parent
DATE = "2026-10-09"
ZIP_NAME = f"swell-g0-{DATE}.zip"
OUT_ZIP = SITE / "src" / "downloads" / ZIP_NAME
OUT_NUMBERS = SITE / "src" / "data" / "numbers_download.json"
RULES = Path(os.environ.get("SWELL_SCRUB_RULES", str(REPO / "pm" / "site" / "forbidden.txt")))
FIXED_TIME = (2026, 10, 9, 0, 0, 0)
REDACTED = "[personal detail removed]"

# Official licence texts, stored unmodified next to this script and pinned by hash.
LICENCE_FILES = {
    "LICENSES/CC0-1.0.txt": (
        SITE / "tools" / "licenses" / "CC0-1.0.txt",
        "a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499",
        "https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt"),
    "LICENSES/CERN-OHL-P-2.0.txt": (
        SITE / "tools" / "licenses" / "CERN-OHL-P-2.0.txt",
        "6e471d647db50527d0c75ee5f1a55a74012ab177c73282bef0bdc7f6562b7ded",
        "https://ohwr.org/cern_ohl_p_v2.txt"),
}

ALLOW_DIRS = ("kit/", "docs/", "software/")
ALLOW_FILES = {
    "pm/AUDIT.md", "pm/DECISIONS.md", "pm/ERRATA.md", "pm/INVARIANTS.md", "pm/RISKS.md",
    "pm/VERIFIED_FACTS.md", "pm/ORDERS.md", "pm/IDEAS.md", "pm/BOM.csv", "LICENSES.md",
    "tools/env.sh", "tools/env.ps1", "tools/setup_tools.sh", "tools/smoke_tools.py",
}
UNTRACKED_GLOB = ("data/sim", "*.csv")
NEVER = re.compile(
    r"^(?:CLAUDE\.md|pm/LEDGER\.md|pm/briefs\.log|pm/inbox/|pm/receipts/|pm/HUMAN_QUEUE\.md|pm/OUTREACH\.md"
    r"|pm/APPROVALS\.md|pm/STATUS\.md|pm/LESSONS\.md|pm/site/|tools/backup\.sh|tools/brief\.py|\.tools/|\.venv/|site/)")
TEXT_EXT = {".md", ".py", ".json", ".csv", ".txt", ".sh", ".ps1", ".in", ".lock", ".toml", ".yml", ".yaml", ".cfg"}
BINARY_EXT = {".png"}


def die(msg: str) -> None:
    print(f"make_swell_zip: FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- private rules
class Rules:
    def __init__(self) -> None:
        self.forbidden: list[re.Pattern] = []
        self.replace: list[tuple[re.Pattern, str]] = []
        self.redact: dict[str, list[tuple[str, str]]] = {}
        self.paths: list[tuple[re.Pattern, str]] = []


def _unescape(s: str) -> str:
    return s.replace("\\n", "\n")


def load_rules(path: Path) -> Rules:
    if not path.is_file():
        die(f"private scrub rules not found at {path}; refusing to build (set SWELL_SCRUB_RULES)")
    r = Rules()
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        kind = parts[0]
        try:
            if kind == "REPLACE" and len(parts) == 3:
                r.replace.append((re.compile(parts[1]), parts[2]))
            elif kind == "PATH" and len(parts) == 3:
                r.paths.append((re.compile(parts[1]), parts[2]))
            elif kind == "REDACT" and len(parts) in (3, 4):
                repl = _unescape(parts[3]) if len(parts) == 4 else REDACTED
                r.redact.setdefault(parts[1], []).append((_unescape(parts[2]), repl))
            elif kind in ("REPLACE", "PATH", "REDACT"):
                die(f"rules line {n}: wrong number of tab-separated fields")
            else:
                r.forbidden.append(re.compile(line.strip(), re.IGNORECASE))
        except re.error as e:
            die(f"rules line {n}: bad regex ({e})")
    if not r.forbidden:
        die("rules file has no forbidden patterns; refusing to build")
    return r


# ---------------------------------------------------------------- scrubbing
_LINE_START = re.compile(r"\s*(?:(?:[-*+>]|\d+\.|#{1,6})\s+)?(?:\*\*)?")
_AFTER_STOP = re.compile(r"[.!?](?:\*\*)?\s+(?:\*\*)?$")


def _sentence_start(s: str, i: int) -> bool:
    prefix = s[s.rfind("\n", 0, i) + 1:i]
    return bool(_LINE_START.fullmatch(prefix) or _AFTER_STOP.search(prefix))


def _cap(repl: str):
    def f(m: re.Match) -> str:
        if repl[:1].islower() and _sentence_start(m.string, m.start()):
            return repl[:1].upper() + repl[1:]
        return repl
    return f


# Non-personal edits for the release (anchor text must match exactly once).
RELEASE_EDITS = [
    ("LICENSES.md",
     re.compile(r"^SWELL's own licence is decided at G6.*$", re.MULTILINE),
     "SWELL's own licence (set at the G0 public release, 2026-10-09): CC0 1.0 for docs, text, data and the "
     "simulation code; CERN-OHL-P v2 for hardware design files. See README.md and LICENSES/. Third-party items "
     "marked \"(confirm)\" below were not re-checked for this release, except OpenFlexure (see README.md)."),
    ("LICENSES.md",
     re.compile(r"CERN Open Hardware Licence \(variant: confirm\)"),
     "CERN Open Hardware Licence v2, strongly reciprocal (CERN-OHL-S-2.0: the project's License file, "
     "checked 2026-10-09)"),
]


def scrub_text(path: str, text: str, rules: Rules, log: list) -> str:
    for old, new in rules.redact.get(path, []):
        k = text.count(old)
        if k == 0:
            die(f"a redaction anchor for {path} no longer matches (update the private rules file)")
        text = text.replace(old, new)
        log.append((path, "redact", k))
    for rx, new in rules.replace:
        text, k = rx.subn(_cap(new), text)
        if k:
            log.append((path, f"replace /{rx.pattern[:24]}…/", k))
    for p, rx, new in RELEASE_EDITS:
        if p == path:
            text, k = rx.subn(new.replace("\\", "\\\\"), text)
            if k != 1:
                die(f"release edit for {path} matched {k} times (expected 1)")
            log.append((path, "release edit", k))
    return text


def rename(path: str, rules: Rules) -> str:
    for rx, new in rules.paths:
        path = rx.sub(new, path)
    return path


# ---------------------------------------------------------------- checks
def png_texts(data: bytes) -> list[str]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        die("a .png member is not a PNG")
    out, i = [], 8
    while i < len(data):
        (n,) = struct.unpack(">I", data[i:i + 4])
        ctype = data[i + 4:i + 8]
        body = data[i + 8:i + 8 + n]
        if ctype == b"tEXt":
            out.append(body.decode("latin-1"))
        elif ctype == b"zTXt":
            k, _, rest = body.partition(b"\0")
            out.append(k.decode("latin-1") + " " + zlib.decompress(rest[1:]).decode("latin-1"))
        elif ctype == b"iTXt":
            out.append(body.decode("utf-8", "replace"))
        elif ctype == b"IEND":
            break
        i += 12 + n
    return out


def hits(text: str, rules: Rules) -> list[str]:
    return [rx.pattern for rx in rules.forbidden if rx.search(text)]


def check_member(name: str, data: bytes, rules: Rules) -> list[str]:
    problems = [f"{name}: path matches /{p}/" for p in hits(name, rules)]
    ext = Path(name).suffix.lower()
    if ext in BINARY_EXT:
        # only the PNG text chunks: regex scans over compressed pixels give random false hits
        texts = png_texts(data)
    else:
        try:
            texts = [data.decode("utf-8")]
        except UnicodeDecodeError:
            return problems + [f"{name}: not UTF-8 text and not an allowed binary type"]
    for t in texts:
        problems += [f"{name}: contains /{p}/" for p in hits(t, rules)]
    return problems


def validate_syntax(name: str, text: str) -> None:
    ext = Path(name).suffix.lower()
    try:
        if ext == ".py":
            ast.parse(text, filename=name)
        elif ext == ".json":
            json.loads(text)
        elif ext == ".csv":
            rows = list(csv.reader(io.StringIO(text)))
            widths = {len(r) for r in rows if r and not (r[0].startswith("#") and len(r) == 1)}
            if len(widths) > 1 and not name.startswith("data/sim/"):
                die(f"{name}: ragged CSV after scrub ({sorted(widths)})")
    except (SyntaxError, ValueError) as e:
        die(f"{name}: no longer parses after scrub ({e})")


# ---------------------------------------------------------------- sources
def git(*args: str) -> bytes:
    res = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)
    if res.returncode != 0:
        die(f"git {' '.join(args)}: {res.stderr.decode(errors='replace').strip()}")
    return res.stdout


def tracked_selection() -> list[str]:
    names = git("ls-tree", "-r", "--name-only", "HEAD").decode("utf-8").splitlines()
    keep = []
    for n in names:
        if NEVER.match(n) or n.endswith(".gitkeep"):
            continue
        if n.startswith(ALLOW_DIRS) or n in ALLOW_FILES:
            keep.append(n)
    return sorted(keep)


def read_tracked(paths: list[str]) -> dict[str, bytes]:
    tar = tarfile.open(fileobj=io.BytesIO(git("archive", "--format=tar", "HEAD", "--", *paths)))
    out = {}
    for m in tar.getmembers():
        if m.isfile():
            out[m.name] = tar.extractfile(m).read()
    missing = set(paths) - set(out)
    if missing:
        die(f"git archive did not return {sorted(missing)}")
    return out


def read_untracked() -> dict[str, bytes]:
    d, pattern = UNTRACKED_GLOB
    files = sorted((REPO / d).glob(pattern))
    if not files:
        die(f"no {d}/{pattern} found: regenerate with software/sim/strain_map_sim.py first")
    return {f"{d}/{f.name}": f.read_bytes() for f in files}


# ---------------------------------------------------------------- README
def readme(counts: dict[str, int]) -> str:
    inside = "\n".join(f"| `{k}` | {v} |" for k, v in sorted(counts.items()))
    return f"""# SWELL: G0 design package ({DATE})

SWELL is a design for a cheap, automated expansion-microscopy (ExM) imager: a hydrogel swells a specimen
4-10x so cheap optics resolve ~80-130 nm, and supermarket chicken myofibrils carry their own rulers so
every gel can check its own expansion. This zip is the whole desk-stage project, given away.

## Status: read this first
- **Stage G0 (desk stage). Never built.** No part was bought, printed or wired; no gel was ever made.
- **Every result in here is simulated** (software/sim/ -> docs/design/, data/sim/). Nothing was measured
  on a real machine. Treat every number as a prediction until someone builds it.
- Facts checked against sources are listed with their verdicts in `pm/VERIFIED_FACTS.md`.
- Personal details of the owner were removed from the private project files before release; each removal
  is marked `{REDACTED}` (postcodes as `[postcode removed]`). The removed lines concern the owner's own
  equipment, circumstances and schedule, not the SWELL design.
- `kit/` is the original brief, kept as written apart from those removals. Where it disagrees with
  `pm/ERRATA.md`, `pm/DECISIONS.md` or this README, the later files win.
- Designed, simulated and documented with AI assistance (Claude by Anthropic, via Claude Code); the owner set
  the direction and approved every gate. Check the code yourself.

## What is inside
| folder | files |
|---|---|
{inside}

- `kit/`: the original brief (science, design, BOM, protocol, QC, roadmap, risks, safety and legal).
- `pm/`: audit, decisions log, errata, invariants, risks, verified facts, orders, ideas, priced BOM (CSV).
- `docs/`: design reports, figures, BOM, toolchain notes. `software/`: simulation code and tests.
- `data/sim/`: per-myofibril tables from the strain-map simulation. `tools/`: the toolchain scripts.

## Rebuild the simulations
Python 3.12. The full pinned environment is `software/requirements.lock` (Windows, 250 packages);
the simulations themselves need only numpy, scipy, matplotlib, MicroscPSF-Py (for optics_v1.py) and pytest.

```
python -m venv .venv
.venv/bin/pip install numpy scipy matplotlib MicroscPSF-Py pytest   # Windows: .venv\\Scripts\\pip
python software/sim/design_calc.py      # -> docs/design/calc_v0.md, calc_v0.json
python software/sim/optics_v1.py        # -> docs/design/optics_v1.md, optics_v1.json
python software/sim/strain_map_sim.py   # -> docs/design/strain_map_v1.*, figs/, data/sim/*.csv
python software/sim/budget.py           # -> docs/BOM.md, docs/design/budget_v1.json
python -m pytest software/tests -q
```
`tools/setup_tools.sh` rebuilds the whole isolated toolchain (Windows + Git Bash; its paths assume the
project sits at D:/SWELL, so edit `tools/env.sh` / `tools/env.ps1` for your machine).

## Licences
| what | licence |
|---|---|
| Docs, text and data (everything not listed below) | CC0 1.0 Universal (`LICENSES/CC0-1.0.txt`) |
| Hardware design files: the bills of materials (`docs/BOM.md`, `pm/BOM.csv`) and any CAD, drawings or BOMs added later | CERN-OHL-P v2 (`LICENSES/CERN-OHL-P-2.0.txt`) |
| Software (the simulation code in `software/`, the scripts in `tools/`) | CC0 1.0 Universal |

- Any part later forked from the OpenFlexure Microscope keeps OpenFlexure's own licence: its repository's
  License file is CERN-OHL-S v2 (strongly reciprocal), checked {DATE}. This zip contains no OpenFlexure files.
- Third-party tools and packages keep their own licences (`LICENSES.md`).
- **Patents:** expansion microscopy is covered by MIT patents (e.g. US 10,309,879 B2; US 10,317,321 B2;
  US 11,408,890 B2). Commercial use may need a licence from MIT; research exemptions vary by country.
  These licences grant no patent rights held by others. This is not legal advice.
- **No warranty.** Provided as is. If you build it, its safety and legality are yours: the chemistry needs
  professional-user access (a lab), because UK REACH restricts the reagents.
- This package is a dated public disclosure ({DATE}), published so the design is prior art.
- Trademarks belong to their owners; naming a product implies no endorsement.

Published by X-WOW: https://x-wow.com
"""


# ---------------------------------------------------------------- main
def build(dump: Path | None) -> None:
    rules = load_rules(RULES)
    for zname, (src, sha, _url) in LICENCE_FILES.items():
        if not src.is_file() or hashlib.sha256(src.read_bytes()).hexdigest() != sha:
            die(f"{src} is missing or not the pinned official text")

    raw = read_tracked(tracked_selection())
    raw.update(read_untracked())
    members: dict[str, bytes] = {}
    log: list = []
    for path in sorted(raw):
        if NEVER.match(path):
            die(f"never-list path selected: {path}")
        data = raw[path]
        ext = Path(path).suffix.lower()
        if ext in BINARY_EXT:
            out = data
        elif ext in TEXT_EXT or b"\0" not in data[:4096]:
            text = scrub_text(path, data.decode("utf-8"), rules, log)
            validate_syntax(path, text)
            out = text.encode("utf-8")
        else:
            die(f"{path}: unknown binary type")
        members[rename(path, rules)] = out

    unused = [p for p in rules.redact if p not in raw]
    if unused:
        die(f"redaction rules name files that are not in the package: {unused}")

    counts: dict[str, int] = {}
    for n in members:
        top = n.split("/")[0] + "/" if "/" in n else n
        counts[top] = counts.get(top, 0) + 1
    for zname, (src, _sha, _url) in LICENCE_FILES.items():
        members[zname] = src.read_bytes()
    counts["LICENSES/"] = len(LICENCE_FILES)
    counts["README.md"] = 1
    members["README.md"] = readme(counts).encode("utf-8")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name in sorted(members):
            zi = zipfile.ZipInfo(name, FIXED_TIME)
            zi.create_system = 3
            zi.external_attr = (0o100755 if name.endswith(".sh") else 0o100644) << 16
            zi.compress_type = zipfile.ZIP_STORED if name.endswith(".png") else zipfile.ZIP_DEFLATED
            z.writestr(zi, members[name], compresslevel=9)
    blob = buf.getvalue()

    # Final gate: re-read the finished zip and scan every member, then write it.
    problems = []
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names = z.namelist()
        for name in names:
            if NEVER.match(name):
                problems.append(f"{name}: on the never-list")
            problems += check_member(name, z.read(name), rules)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        die(f"{len(problems)} forbidden hit(s) in the finished zip; nothing written")

    OUT_ZIP.parent.mkdir(parents=True, exist_ok=True)
    OUT_ZIP.write_bytes(blob)
    sha = hashlib.sha256(blob).hexdigest()
    rel_zip = OUT_ZIP.relative_to(SITE).as_posix()
    numbers = {
        "download.sha256": {"value": sha, "source": rel_zip,
                            "how": "SHA-256 of the zip bytes (tools/make_swell_zip.py; deterministic build)"},
        "download.size_kb": {"value": f"{round(len(blob) / 1024):,} KB", "source": rel_zip,
                             "how": "zip size in bytes / 1024, rounded"},
        "download.files": {"value": str(len(names)), "source": rel_zip, "how": "number of files in the zip"},
        "download.date": {"value": DATE, "source": "tools/make_swell_zip.py: DATE",
                          "how": "first-publication date of the G0 package (also in the zip name)"},
    }
    OUT_NUMBERS.parent.mkdir(parents=True, exist_ok=True)
    OUT_NUMBERS.write_text(json.dumps(numbers, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if dump:
        for name in names:
            p = dump / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(members[name])
    red = sum(k for _, kind, k in log if kind == "redact")
    print(f"OK {rel_zip}: {len(names)} files, {len(blob):,} bytes, sha256 {sha}")
    nrep = sum(k for _, kind, k in log if kind.startswith("replace"))
    print(f"   {red} sentence redactions, {nrep} token replacements")
    for k, v in sorted(counts.items()):
        print(f"   {k:<12} {v}")


def check_paths(paths: list[str]) -> int:
    rules = load_rules(RULES)
    bad = 0
    for p in paths:
        root = Path(p)
        files = [root] if root.is_file() else [f for f in root.rglob("*") if f.is_file()]
        for f in files:
            if f.suffix.lower() in {".zip"}:
                with zipfile.ZipFile(f) as z:
                    probs = [x for n in z.namelist() for x in check_member(n, z.read(n), rules)]
            else:
                probs = check_member(f.as_posix(), f.read_bytes(), rules) if f.suffix.lower() in BINARY_EXT \
                    else [f"{f}: contains /{h}/" for h in hits(f.read_bytes().decode("utf-8", "replace"), rules)]
            for x in probs:
                print(x)
            bad += len(probs)
    print(f"check: {bad} hit(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", type=Path, help="also write the scrubbed tree here for review")
    ap.add_argument("--check", nargs="+", metavar="PATH", help="only scan these files/folders for forbidden tokens")
    a = ap.parse_args()
    if a.check:
        sys.exit(check_paths(a.check))
    build(a.dump)
