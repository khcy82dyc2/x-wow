#!/usr/bin/env python3
"""Build the SWELL G0 download zip from the private SWELL repo, scrubbed (stdlib only).

Run:    python tools/make_swell_zip.py                 (from site/, or give the full path)
Out:    src/downloads/swell-g0-<DATE>.zip  and  src/data/numbers_download.json
Review: python tools/make_swell_zip.py --dump DIR      (also writes the scrubbed tree to DIR)
Check:  python tools/make_swell_zip.py --check PATH... (scan files or folders for forbidden tokens; exit 1 on a hit)

What goes in: tracked files at the pinned SWELL commit (REV) that are on the allowlist, plus the regenerable data/sim/*.csv,
plus a README, the official licence texts (pinned by SHA-256) and nothing else. The original brief (kit/) stays out: it
was written for a home wet lab, a plan that was withdrawn, and the finished zip is refused if home-lab text is found.

Scrubbing is driven by a PRIVATE rules file that lives outside this public repo: forbidden tokens,
sentence redactions, path renames and replacements (format in that file). Default location:
<SWELL repo>/pm/site/forbidden.txt, or set SWELL_SCRUB_RULES. Without it this script refuses to build.
The build is deterministic (sorted members, fixed timestamps), so the SHA-256 is reproducible.
"""
from __future__ import annotations

import argparse
import ast
import csv
import functools
import hashlib
import html
import io
import json
import os
import re
import struct
import subprocess
import sys
import tarfile
import textwrap
import zipfile
import zlib
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
REPO = SITE.parent
ORIGINAL_DATE = "2026-10-09"   # first publication; that zip is no longer offered (it carried the withdrawn home plan)
DATE = "2026-10-11"            # this version (v0.2.0, never published before this date); --date overrides
for _i, _a in enumerate(sys.argv):
    if _a == "--date" and _i + 1 < len(sys.argv):
        DATE = sys.argv[_i + 1]
# The SWELL commit to build from, pinned so a rebuild is reproducible. Moved on 2026-10-10 (runner life 8, audit
# A-11) from b3655b2 to the commit that carries A-11's changes and round 1 of its AI review's fixes (D-69); moved on
# 2026-10-11 (runner life 11, Q-A8) from e9978f2 to 83153af (branch zip-pin-v0.2.0): e9978f2 plus BOM H-16's wording
# only (D-46), because moving along master would also drag in the runner's later DECISIONS entries; moved on
# 2026-10-11 (runner life 12, N-20) to branch zip-pin-v0.2.0-n20, now be4681e: 83153af plus the hot tools designed
# out (pm/BOM.csv, docs/BOM.md, docs/design/budget_v1.json, D-75 with its two dated corrections, and its IDEAS line)
# only; moved on 2026-10-11 (runner life 18, D-78) to branch zip-pin-v0.2.0-d78, ff2b610: be4681e plus the BOM totals
# that sum listed lines only (software/sim/budget.py, docs/BOM.md, docs/design/budget_v1.json), H-21 priced from its
# shop page and H-10 not yet read (pm/BOM.csv, a dated F-30 line in pm/VERIFIED_FACTS.md), floors rounded down and
# a dated R29 correction (pm/RISKS.md), and nothing else.
# Moving REV is a deliberate act; --rev overrides it for one run. data/sim/*.csv still come from disk.
REV = "ff2b610482f737ab5dce24bd0641106bd318b335"
for _i, _a in enumerate(sys.argv):
    if _a == "--rev" and _i + 1 < len(sys.argv):
        REV = sys.argv[_i + 1]
VERSION = {"2026-10-09": "v0.1.0-g0", "2026-10-11": "v0.2.0", "2026-10-12": "v0.2.1"}.get(DATE, DATE)
ZIP_NAME = f"swell-g0-{DATE}.zip"
OUT_ZIP = SITE / "src" / "downloads" / ZIP_NAME
ORIGINAL_ZIP = SITE / "src" / "downloads" / f"swell-g0-{ORIGINAL_DATE}.zip"
OUT_NUMBERS = SITE / "src" / "data" / "numbers_download.json"
RULES = Path(os.environ.get("SWELL_SCRUB_RULES", str(REPO / "pm" / "site" / "forbidden.txt")))
FIXED_TIME = tuple(int(x) for x in DATE.split("-")) + (0, 0, 0)
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

# Only SWELL's own software goes in: anything else under software/ stays out unless it is added here on purpose.
SWELL_SOFTWARE = ("software/redteam/", "software/sim/", "software/swell_ruler/", "software/tests/",
                  "software/requirements.in", "software/requirements.lock")
# kit/ (the original brief) is left out: it plans the gel chemistry in a home wet lab, a plan withdrawn on 2026-10-09
# (pm/ERRATA.md E-18), and that plan runs through its workspace, equipment, protocol, sourcing and risk files.
ALLOW_DIRS = ("docs/",) + SWELL_SOFTWARE
# Decision entries taken out of the zip's copy of pm/DECISIONS.md (the private log keeps them): D-56 is about the slide
# game; D-51 and D-53 are about the videos page and its comment wall, and tie the owner to the channel; D-31 lists the
# labs near where the owner planned to work. D-57 to D-64 (added to the log after 2026-10-10 03:17) are about the
# agent that runs X-WOW, its accounts and channels, the slide game's hosting and the containment of the live site,
# not the SWELL design. D-65 and D-67 are about this package and the website and cite the project's private
# rules by file name; D-69 restates what they decided about SWELL. The README names each one.
DROP_DECISIONS = ("D-56", "D-51", "D-53", "D-31", "D-57", "D-58", "D-59", "D-60", "D-61", "D-62", "D-63", "D-64",
                  "D-65", "D-67")
# The finished zip must not point at the slide game, its bucket or its Worker (checked in code, case-sensitive for
# the name so the verb "shrink" stays allowed).
NOT_SWELL = re.compile(r"\bSHRINK\b|(?i:x-wow\.com/shrink|slide game|openseadragon|pmtiles)|r2\.dev"
                       r"|r2\.cloudflarestorage|workers\.dev|data\.x-wow\.com|software/slides/")
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
            elif kind == "ZIPONLY" and len(parts) == 2:   # forbidden in the zip only; site/build.py skips tab lines
                r.forbidden.append(re.compile(parts[1].strip(), re.IGNORECASE))
            elif kind in ("REPLACE", "PATH", "REDACT", "ZIPONLY"):
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
    # Rows written for the withdrawn home plan, or that a reader could follow into harm: left out of this copy, marked
    # in place (the private records keep them).
    ("pm/AUDIT.md", re.compile(r"^\| AU-26 \|.*$", re.MULTILINE),
     "| AU-26 | Low | *Left out of this copy: its fix suggested making a calibration item yourself.* | | |"),
    ("pm/AUDIT.md", re.compile(r"^\| AU-34 \|.*$", re.MULTILINE),
     "| AU-34 | Low | *Left out of this copy: its fix suggested a shop-bought substitute for the practice gels.* | | |"),
    ("pm/VERIFIED_FACTS.md", re.compile(r"^\| F-9 \|.*$", re.MULTILINE),
     "| F-9 | *Left out of this copy: a note on making sodium acrylate from acrylic acid, written for the withdrawn "
     "plan to do the chemistry outside a lab. The lab-only fallback is D-21.* | | |"),
    ("pm/IDEAS.md", re.compile(r"^- \*\*\[Claude\] Teaching variant:\*\*.*$", re.MULTILINE),
     "- *Left out of this copy: an idea for schools that used water beads, an ingestion hazard for children.*"),
    # Audit A-10 (life 6): F-8 re-read from the primary protocol, F-13 checked against HSE's GB list; marked in place.
    ("pm/VERIFIED_FACTS.md", re.compile(r"^\| F-8 \|.*$", re.MULTILINE),
     "| F-8 | \"U-ExM of diverse samples\", protocols.io V.1, 2025-06-13 (Mikus, Dudin, Dey; DOI "
     "10.17504/protocols.io.261gee4qwg47/v1). 250 µL MS: 10% AA, 19% SA, 0.1% BIS, 1× PBS; stocks 40% AA, 4 M (38%) SA, "
     "2% BIS; −20 °C < 2 weeks; prepare ≥ 4 h ahead. *Re-read for this copy, 2026-10-10, from the protocol's PDF and "
     "page (CC BY):* its monomer table gives, per 250 µL, 62.5 µL 40% AA, 125 µL 4 M (38%) SA, 12.5 µL 2% BIS and 25 µL "
     "10× PBS (finals 10%, 19%, 0.1%, 1×; the four add to 225 µL); it says \"Prepare at least 4 hours in advance\" and "
     "to store aliquots at −20 °C \"for no more than 2 weeks\"; its gelation table adds 1 µL each of TEMED and APS to "
     "18 µL of monomer solution (4 + 4 to 72 µL for a 12 mm coverslip). It does not state the TEMED and APS stock "
     "strengths. | verified 2026-10-10 (AI: read from the protocol's PDF and page by the X-WOW agent and re-derived by "
     "a separate AI review; was \"partial, search extract\") | "
     "https://www.protocols.io/view/u-exm-of-diverse-samples-d7ys9pwe.html |"),
    ("pm/VERIFIED_FACTS.md", re.compile(r"^\| F-13 \|.*$", re.MULTILINE),
     "| F-13 | N,N′-methylenebisacrylamide: harmonised Muta 1B (H340), index 616-243-00-6, per a database. Supplier SDSs "
     "range from H302 only to H340/H350/H372. *Checked for this copy, 2026-10-10:* HSE's GB mandatory classification "
     "list (legally binding in Great Britain) has N,N′-methylenediacrylamide, 616-243-00-6, as Muta. 1B (H340), in "
     "legal effect from 2025-09-23; Fisher's GB SDS for its bis-acrylamide solution (BP1404-250, rev. 2023-10-13) lists "
     "the component as Muta. 1B, Carc. 1B, Repr. 2, STOT RE 1 and acutely toxic, but leaves the solution unclassified. "
     "| verified 2026-10-10 (AI: the X-WOW agent read HSE's GB list and a separate AI review re-derived it; was "
     "\"partial, GB MCL check pending\") | "
     "https://www.hse.gov.uk/chemical-classification/classification/mcl-list.htm ; https://nextsds.com/substances/110-26-9 |"),
    ("pm/ERRATA.md", re.compile(re.escape("Confirm against the protocols.io PDF in Order 2.")),
     "Confirm against the protocols.io PDF in Order 2. *Re-read for this copy, 2026-10-10 (F-8): the protocol's "
     "gelation table adds TEMED and APS at 1 µL each per 18 µL of monomer solution, the same 90 + 5 + 5 ratio; it does "
     "not state their stock strengths, so the 10% stocks and 0.5% finals here are not confirmed by it.*"),
    ("pm/AUDIT.md", re.compile(re.escape("Re-read the PDF in Order 2; write it into protocol v0.1.")),
     "Re-read the PDF in Order 2; write it into protocol v0.1. *Re-read for this copy, 2026-10-10: see F-8 and E-1.*"),
    # S3 was made by another AI agent, not a person, and no AI-made test is called independent.
    ("software/redteam/README.md",
     re.compile(re.escape("S3 is an independent, adversarial but honest test gel for the ruler pipeline. It was built "
                          "from the data contract\nalone (`docs/design/obs_schema_v1.md`) by someone who has never seen "
                          "the pipeline.")),
     "S3 is an adversarial but honest test gel for the ruler pipeline. It was built from the data contract\nalone "
     "(`docs/design/obs_schema_v1.md`) by a separate AI agent (another Claude instance, not a person) that had never "
     "seen the pipeline."),
]

# Audit A-11 (life 8): two record lines call an AI review "fresh" without saying it was an AI; marked in this copy
# (the private records keep their words, and D-69 records the correction).
RELEASE_EDITS += [
    ("pm/DECISIONS.md", re.compile(re.escape("  - A fresh reviewer found 1 blocker (the text implied draft CAD")),
     "  - A fresh reviewer *(an AI session, not a person; noted in this copy)* found 1 blocker (the text implied "
     "draft CAD"),
    ("pm/AUDIT.md", re.compile(re.escape("*Revised after a fresh OWNER_PRINCIPLES-only review the same day:")),
     "*Revised after a fresh OWNER_PRINCIPLES-only review (an AI session, not a person; noted in this copy) the "
     "same day:"),
    # D-66 cites two sections of the project's private rules by number; this copy names what they say instead
    ("pm/DECISIONS.md", re.compile(r"they are the design's evidence; §\d allows lab theory"),
     "they are the design's evidence; the project's safety rules allow lab theory"),
    ("pm/DECISIONS.md", re.compile(r"sheets from search snippets \(\w+ \d+\)"),
     "sheets from search snippets (the project's rule: never cite a snippet)"),
    ("pm/DECISIONS.md", re.compile(r"hot tools against §\d"), "hot tools against the project's safety rules"),
    ("pm/VERIFIED_FACTS.md", re.compile(re.escape("**verified** (primary or vendor source read)")),
     "**verified** (primary or vendor source read, by an AI, the X-WOW agent, unless a row names another "
     "checker; noted in this copy)"),
]

# Home-lab text: the finished zip is refused if any of these words appear, except in the reviewed phrases below, which
# name the withdrawn plan only to rule it out or use the word in another sense. Every phrase must still be found, so
# the list can't go stale.
HOME_LAB = re.compile(r"(?i)kitchen|\bdomestic\b|\bhousehold\b|\bgarage\b|spare room|lockable room|\bat home\b"
                      r"|\bhome[- ]?(?:lab|wet|made|address|condition|variant|substitut|method)|homemade|\bgarden\b"
                      r"|water[- ]storing|\bnappy|\bresidential\b|\bDIY\b")
HOME_LAB_OK = (
    ("pm/DECISIONS.md", "nothing chemical at home"),          # D-26: the decision that moved all wet work to a lab
    ("pm/DECISIONS.md", "the kit's home variant"),            # D-26: "Rejected: the kit's home variant"
    ("pm/DECISIONS.md", "household bins"),                    # INV-10, quoted in D-26: nothing hazardous into them
    ("pm/DECISIONS.md", "kitchen salt only"),                 # D-50: rung 2 uses table salt, a food
    ("pm/ERRATA.md", "home wet lab"),                         # E-18: the erratum that withdrew the home plan
    ("pm/INVARIANTS.md", "household bins"),                   # INV-10
    ("README.md", "planned the gel chemistry at home"),       # README: why kit/ is left out
)


# Lab-only safety (life 5): SAFETY.md is built from the reviewed safety section of the SWELL page, so the zip and the
# site say the same thing; every record file that mentions a reagent gets a banner pointing to it.
SAFETY_SRC = SITE / "src" / "pages" / "swell~safety" / "60-safety.html"
REAGENTS = re.compile(r"(?i)acrylamide|\bTEMED\b|\bAPS\b|persulfate|formaldehyde|sodium acrylate|acrylic acid|\bDMSO\b"
                      r"|Triton|NHS[- ]?(?:ester|label)|\bPLL\b|poly-L-lysine|proteinase|monomer solution"
                      r"|glutaraldehyde|\bAcX\b")
LAB_BANNER = ("> **Lab only.** The reagents, amounts and steps in this file are design notes for a laboratory with a fume "
              "hood,\n> working under its own risk assessments. They are not a method to follow. Each reagent's hazards "
              "and handling:\n> `SAFETY.md`.\n\n")

# Audit A-10 (life 6): every record step that gives reagent amounts carries its hazards beside it in this copy, built
# from the page's SDS-cited rows (step_note). Each anchor must match exactly once; the finished zip is refused if a
# record line names a reagent with an amount and carries neither the note nor a reviewed reason (STEP_OK).
STEP_MARK = "Hazards beside this step"
_GEL = ["acrylamide", "bis", "sa", "temed", "aps"]
_GEL_CONTROL = "fume hood, double nitrile gloves, goggles and lab coat; never on the microscope stage"
_DYE_CONTROL = ("gloves, because DMSO carries the dissolved dye through skin; no dye is chosen yet, so read its own SDS "
                "once one is")
_APS_CONTROL = "weigh into closed, pre-tared vials with minimal dust; keep away from combustible materials"
_ANCHOR_CONTROL = ("open the formaldehyde and make the anchoring mix only in a fume hood (as a substance, the GB "
                   "list classes formaldehyde fatal if inhaled, H330); anchoring runs overnight in a sealed box off "
                   "the stage; only the polymerised, rinsed gel reaches the stage")
STEP_HAZARDS = [
    ("pm/AUDIT.md", r"^\| AU-24 \|.*$", ["sa", "aa_naoh"],
     "fume hood only, with goggles, gloves and lab coat; neutralising the acid gives off heat"),
    ("pm/AUDIT.md", r"^\| AU-25 \|.*$", ["aps"], _APS_CONTROL),
    ("pm/AUDIT.md", r"^\| AU-28 \|.*$", ["imidazole"],
     "the rigor buffer is made with imidazole (D-22): weigh the solid only in a fume hood; EGTA has no hazard class "
     "in its sheet (SAFETY.md)"),
    ("pm/AUDIT.md", r"^\| AU-29 \|.*$", _GEL, _GEL_CONTROL),
    ("pm/AUDIT.md", r"^\| AU-33 \|.*$", ["dmso"], _DYE_CONTROL),
    ("pm/AUDIT.md", r"^\| AU-43 \|.*$", ["acrylamide", "bis"],
     "leftover monomer stays CMR waste until the lab's waste route says otherwise"),
    ("pm/DECISIONS.md", r"^- \*\*2026-10-09 · D-22 ·.*$", ["imidazole"],
     "weigh the solid under local exhaust ventilation with gloves and goggles; the lab's risk assessment must cover a "
     "reproductive toxicant"),
    ("pm/DECISIONS.md", r"^- \*\*2026-10-09 · D-24 ·.*$", ["aps"], _APS_CONTROL),
    ("pm/DECISIONS.md", r"^  - \*\*How:\*\* image the polymerised gel.*$", ["formaldehyde", "acrylamide"], _ANCHOR_CONTROL),
    ("pm/DECISIONS.md", r"^- \*\*2026-10-10 · D-49 ·.*$", ["dmso"], _DYE_CONTROL),
    ("pm/ERRATA.md", r"^- \*\*E-1 ·.*$", _GEL, _GEL_CONTROL),
    ("pm/ERRATA.md", r"^- \*\*E-8 ·.*$", ["temed", "bis"], _GEL_CONTROL + " (this line cites a published recipe; "
     "it is not a method to follow)"),
    ("pm/ERRATA.md", r"^- \*\*E-13 ·.*$", ["aps"], _APS_CONTROL),
    ("pm/ERRATA.md", r"^- \*\*E-17 ·.*$", ["dmso"], _DYE_CONTROL),
    ("pm/ERRATA.md", r"^- \*\*E-21 ·.*$", ["formaldehyde", "acrylamide"], _ANCHOR_CONTROL),
    ("pm/ERRATA.md", r"^- \*\*E-22 ·.*$", ["dmso"], _DYE_CONTROL),
    ("pm/VERIFIED_FACTS.md", r"^\| F-7 \|.*$", ["temed", "bis"], _GEL_CONTROL + " (this line cites a published "
     "recipe; it is not a method to follow)"),
    ("pm/VERIFIED_FACTS.md", r"^\| F-8 \|.*$", ["acrylamide", "sa", "bis", "temed", "aps"], _GEL_CONTROL),
    ("pm/VERIFIED_FACTS.md", r"^\| F-18 \|.*$", ["dmso"], _DYE_CONTROL),
    ("pm/ORDERS.md", r"^- imidazole rigor buffer \(D-22\)$", ["imidazole"],
     "weigh the solid under local exhaust ventilation; the lab's risk assessment must cover a reproductive toxicant"),
    ("pm/ORDERS.md", r"^- NHS-ester dye titration, 2 / 6 / 20 .*$", ["dmso"], _DYE_CONTROL),
    ("pm/ORDERS.md", r"^- APS stock per D-24$", ["aps"], _APS_CONTROL),
    ("pm/ORDERS.md", r"^- \*\*Buttons B \+ C on paper.*$", ["acrylamide", "bis", "formaldehyde", "sds"],
     "on paper only; built only after A-1, G4 and a signed risk assessment"),
    ("pm/RISKS.md", r"^\| R30 \|.*$", ["dmso"], _DYE_CONTROL),
    # life 8: lines added to the records by lives 6 and 7
    ("pm/ERRATA.md", r"^- \*\*E-24 ·.*$", ["temed", "aps"], _GEL_CONTROL + " (this line cites a published "
     "recipe; it is not a method to follow)"),
    ("pm/VERIFIED_FACTS.md", r"^\| F-8 \(2026-10-10\) \|.*$", ["acrylamide", "sa", "bis", "temed", "aps"],
     _GEL_CONTROL + " (this line cites a published recipe; it is not a method to follow)"),
]
STEP_REAGENT = re.compile(r"(?i)acrylamide|bis-?acryl|\bBIS\b|\bTEMED\b|\bAPS\b|persulfate|formaldehyde|sodium acrylate"
                          r"|acrylic acid|\bNaOH\b|sodium hydroxide|\bDMSO\b|Triton|NHS[- ]?ester|imidazole"
                          r"|monomer solution|\bSDS\b")
STEP_AMOUNT = re.compile(r"\d+(?:\.\d+)?\s*(?:%|µL|uL|mL|µg/mL|ug/mL|mg\b|µM|mM\b|M\b|ppm|°C|g\b|h\b|min\b)")
# Lines that name a reagent next to a number but give no step to follow (each phrase must still be found).
STEP_OK = (
    ("pm/AUDIT.md", "The denaturation buffer contains 50 mM Tris"),        # AU-31: a finding about amine carry-over
    ("pm/ORDERS.md", "exchanges needed per wash (e.g. Tris < 0.1 mM"),     # a simulation to write, not a step
    ("pm/DECISIONS.md", "**Public corrections** (dated note on the page; E-23)"),  # D-66: hazard classes corrected
    ("pm/ERRATA.md", "**E-23 · SWELL page safety table (corrected 2026-10-10"),   # hazard classes, not a step
    ("pm/VERIFIED_FACTS.md", "| F-13 (2026-10-10) | HSE's GB mandatory classification list"),  # a legal class
    ("pm/VERIFIED_FACTS.md", "| F-34 | The 40% acrylamide solution is Acute Tox. 4"),   # hazard classes
    ("pm/VERIFIED_FACTS.md", "| F-35 | Acrylamide carries EH40/2005's skin notation"),  # exposure limits
)


def add_step_hazards(path: str, text: str, log: list) -> str:
    for p, rx, keys, control in STEP_HAZARDS:
        if p != path:
            continue
        found = list(re.finditer(rx, text, re.MULTILINE))
        if len(found) != 1:
            die(f"step-hazard anchor for {path} matched {len(found)} times (expected 1): /{rx[:48]}/")
        m, note = found[0], step_note(keys, control)
        line = m.group(0).rstrip()
        if line.startswith("|") and line.endswith("|"):      # a table row: the note joins the last cell with an amount
            cells = [c.strip() for c in line[1:-1].split("|")]
            at = max((i for i, c in enumerate(cells) if STEP_AMOUNT.search(c)), default=len(cells) - 1)
            cells[at] = f"{cells[at]} {note}"
            new = "| " + " | ".join(cells) + " |"
        else:
            new = f"{line} {note}"
        text = text[:m.start()] + new + text[m.end():]
        log.append((path, "step hazard", 1))
    return text


def step_problems(name: str, text: str) -> tuple[list[str], set]:
    """Record lines that name a reagent with an amount but carry no hazard note and no reviewed reason."""
    problems, used = [], set()
    if not (name.startswith("pm/") and name.endswith(".md")):
        return problems, used
    for n, line in enumerate(text.splitlines(), 1):
        if not (STEP_REAGENT.search(line) and STEP_AMOUNT.search(line)) or STEP_MARK in line:
            continue
        ok = [(p, ph) for p, ph in STEP_OK if p == name and ph in line]
        if ok:
            used |= set(ok)
        else:
            problems.append(f"{name}:{n}: names a reagent with an amount but has no hazard beside it: {line[:90]}")
    return problems, used


def _numbers() -> dict[str, str]:
    out = {}
    for f in sorted((SITE / "src" / "data").glob("numbers_*.json")):
        out.update({k: v["value"] for k, v in json.loads(f.read_text(encoding="utf-8")).items()})
    return out


def _href(h: str) -> str:
    """A link as the zip can show it: an anchor on the SWELL page becomes its full address."""
    h = html.unescape(h).replace("{{root}}", "https://x-wow.com/")
    return "https://x-wow.com/swell/" + h if h.startswith("#") else h


def _en(fragment: str, nums: dict[str, str]) -> str:
    """The English text of a bilingual page fragment, as plain Markdown, with {{n:key}} numbers filled in."""
    m = re.search(r'<span class="en">(.*?)</span>\s*<span class="zh"', fragment, re.S)
    t = m.group(1) if m else re.sub(r'<span class="zh">.*?</span>', "", fragment, flags=re.S)
    t = re.sub(r"</?strong>", "**", t)
    t = t.replace('<span class="sds">', " · ")                      # the row's SDS citation, on its own line on the page
    t = re.sub(r'<a href="([^"]+)"[^>]*>(.*?)</a>', lambda a: f"{a.group(2)} ({_href(a.group(1))})", t, flags=re.S)
    t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t))).strip()

    def num(mm: re.Match) -> str:
        if mm.group(1) not in nums:
            die(f"{SAFETY_SRC.name}: no number {mm.group(1)}")
        return nums[mm.group(1)]
    return re.sub(r"\{\{n:([\w.]+)\}\}", num, t).replace("|", "/")


# Every reagent row (data-sds other than "none") must cite the supplier's SDS it was read from, with the sheet's
# revision date; the zip is refused otherwise (audit A-10).
SDS_CITE = re.compile(r"SDS(?: \(the solid\))?: [^·]*?\brev\. \d{4}-\d{2}-\d{2}")
H_CODE = re.compile(r"\bH\d{3}[A-Za-z]{0,2}\b")
# A row's sentence about HSE's GB classification of the substance (higher than the product's label) sits in its own
# span: its H-codes come from the GB list, not from the sheet, so the sheet checks and the step notes skip it.
GB_SPAN = re.compile(r'<span class="gb">.*?</span>', re.S)
# Short names for the hazard notes put beside record steps (keys are the rows' data-sds values).
STEP_NAMES = {"acrylamide": "acrylamide", "bis": "bis-acrylamide", "formaldehyde": "formaldehyde", "aps": "APS",
              "temed": "TEMED", "sa": "sodium acrylate", "aa_naoh": "acrylic acid and sodium hydroxide",
              "sds": "SDS (the detergent)", "dmso": "DMSO", "triton": "Triton X-100", "imidazole": "imidazole"}


@functools.lru_cache(maxsize=1)
def safety_rows() -> dict[str, dict[str, str]]:
    """The reagent rows of the page's safety table: data-sds key -> English reagent, hazard and handling text."""
    page, nums = SAFETY_SRC.read_text(encoding="utf-8"), _numbers()
    body = re.search(r"<tbody>(.*?)</tbody>", page, re.S)
    out: dict[str, dict[str, str]] = {}
    for n, (key, r) in enumerate(re.findall(r'<tr data-sds="([\w-]+)">(.*?)</tr>', body.group(1) if body else "", re.S)):
        cells = re.findall(r"<td>(.*?)</td>", r, re.S)
        if len(cells) != 3:
            die(f"{SAFETY_SRC.name}: a reagent row without three cells")
        reagent, hazard, handling = (_en(c, nums) for c in cells)
        if key != "none" and not SDS_CITE.search(hazard):
            die(f"{SAFETY_SRC.name}: the {key} row cites no supplier SDS with its revision date (A-10)")
        codes = list(dict.fromkeys(H_CODE.findall(_en(re.sub(GB_SPAN, "", cells[1]), nums))))   # the sheet's codes
        out[key if key != "none" else f"none-{n}"] = {"reagent": reagent, "hazard": hazard, "handling": handling,
                                                      "codes": codes}
    if len(re.findall(r"<tr\b", body.group(1) if body else "")) != len(out):
        die(f"{SAFETY_SRC.name}: every safety table row needs a data-sds key (\"none\" for rows with no SDS)")
    missing = set(STEP_NAMES) - set(out)
    if missing:
        die(f"{SAFETY_SRC.name}: no row for {sorted(missing)}")
    return out


SDS_RECORD = REPO / "pm" / "xwow" / "sds" / "2026-10-10.json"     # private record of the sheets read (SHA-256 each)
_MONTHS = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}


def _iso(printed: str) -> str:
    m = re.fullmatch(r"(\d{2})-([A-Z][a-z]{2})-(\d{4})", printed or "")
    return f"{m.group(3)}-{_MONTHS[m.group(2)]:02d}-{m.group(1)}" if m else (printed or "")


def check_sds_citations(page: str) -> None:
    """Every product code the safety section cites must carry the revision date (and number) of the sheet actually
    read, as recorded with its SHA-256 in the private record; a typo or a stale citation stops the build."""
    if not SDS_RECORD.is_file():
        die(f"{SDS_RECORD} not found: the SDS citations can't be checked against what was read")
    rec, known = json.loads(SDS_RECORD.read_text(encoding="utf-8")), {}
    for it in rec["sds"]:
        for code in [it["fetched_as"]] + [c.strip() for c in (it["product_codes"] or "").split(";")]:
            known[code] = (_iso(it["revision_date_as_printed"]), it["revision_number"])
    sec = re.search(r'<section class="block" id="safety">(.*?)</section>', page, re.S).group(1)
    pieces = re.findall(r'<span class="sds">(.*?)</span>', sec, re.S)
    pieces += re.findall(r"<li data-sds=\"(?!mcl)[\w-]+\">(.*?)</li>", sec, re.S)
    pieces += re.findall(r'<p class="en muted" id="sds-also">(.*?)</p>', sec, re.S)
    checked = 0
    # every code in the record, plus the shapes of Fisher and Glentham codes, so a code that was never read is caught
    code_rx = re.compile(r"\b(" + "|".join(re.escape(c) for c in sorted(known, key=len, reverse=True) if c)
                         + r"|BP\d{3,4}-\d+|GX\d{4})\b")
    for piece in pieces:
        piece = html.unescape(re.sub(r"<[^>]+>", "", piece))          # links out: their item codes aren't citations
        for m in code_rx.finditer(piece):
            code, window = m.group(1), piece[m.end():m.end() + 160]
            date, num = known.get(code, (None, None))
            if not date:
                die(f"{SAFETY_SRC.name}: cites {code}, which is not in {SDS_RECORD.name}")
            if date not in window or ("revision" in window and num and f"revision {num}" not in window):
                die(f"{SAFETY_SRC.name}: {code} is not cited with the sheet read (rev. {date}, number {num})")
            checked += 1
    if checked < 25:
        die(f"{SAFETY_SRC.name}: only {checked} SDS citations found to check")
    # each row's H-codes, in both languages, are the ones its sheets print (label, else classification; for a sheet
    # that leaves the product unclassified, the component codes recorded from its section 3)
    for key, row in re.findall(r'<tr data-sds="([\w-]+)">(.*?)</tr>', sec, re.S):
        if key == "none":
            continue
        cell = re.sub(GB_SPAN, "", re.findall(r"<td>(.*?)</td>", row, re.S)[1])   # GB-list classes aren't the sheet's
        en = re.search(r'<span class="en">(.*?)</span>\s*<span class="zh"', cell, re.S).group(1)
        zh = cell[cell.index('<span class="zh">'):]
        page_en = set(H_CODE.findall(re.sub(r"<[^>]+>", "", en)))
        page_zh = set(H_CODE.findall(re.sub(r"<[^>]+>", "", zh)))
        sheet = set()
        for it in rec["sds"]:
            if it["page_key"] == key:
                label = {c for s in it["h_statements_label"] for c in H_CODE.findall(s)}
                sheet |= label or set(it["h_codes_in_classification"])
                if it["not_classified"]:
                    sheet |= set(H_CODE.findall(it["note"]))
        if page_en != sheet or page_zh != page_en:
            die(f"{SAFETY_SRC.name}: the {key} row's H-codes (EN {sorted(page_en)}, 中文 {sorted(page_zh)}) are not "
                f"the ones its sheets print ({sorted(sheet)})")


def step_note(keys: list[str], control: str) -> str:
    """The hazard note put beside a record step in this copy, built from the page's SDS-cited rows."""
    rows = safety_rows()
    parts = []
    for k in keys:
        codes = rows[k]["codes"]
        parts.append(f"{STEP_NAMES[k]} {', '.join(codes)}" if codes else f"{STEP_NAMES[k]} (no hazard class; see its row)")
    return (f"*{STEP_MARK} (lab only; from the supplier SDSs listed in `SAFETY.md`): {'; '.join(parts)}. "
            f"Control: {control}. Waste: the lab's hazardous-waste route; nothing down the drain.*")


def safety_md() -> str:
    page, nums = SAFETY_SRC.read_text(encoding="utf-8"), _numbers()
    check_sds_citations(page)
    rows = safety_rows()
    table = [f"| {r['reagent']} | {r['hazard']} | {r['handling']} |" for r in rows.values()]
    red = re.search(r'<div class="panel red">(.*?)</div>', page, re.S)
    never = [f"- {_en(li, nums)}" for li in re.findall(r"<li>(.*?)</li>", red.group(1) if red else "", re.S)]
    also = re.search(r'<p class="en muted" id="sds-also">(.*?)</p>', page, re.S)
    refs_ol = re.search(r'<ol class="en sds-refs">(.*?)</ol>', page, re.S)
    refs = [f"- {_en(li, nums)}" for li in re.findall(r"<li[^>]*>(.*?)</li>", refs_ol.group(1) if refs_ol else "", re.S)]
    if len(table) < 12 or len(never) < 6 or not also or len(refs) < 12:
        die(f"{SAFETY_SRC.name}: the safety section no longer has the expected table, sources and list")
    rows_md = "\n".join(table)
    never_md = "\n".join(never)
    refs_md = "\n".join(refs)
    return f"""# SWELL: safety for the chemistry and the instrument

**The gel chemistry happens only in a laboratory with a fume hood, under that lab's own induction, risk assessments
and waste route.** Several of the reagents are carcinogens, mutagens or reproductive toxicants (CMR substances). This
package holds no wet-lab protocol: where its records mention reagents, amounts or steps, they are design notes, not a
method to follow, and each such step has its hazards beside it.

The table, the sources and the list below are copied from the safety section of the SWELL page on x-wow.com when this
zip was built. Each chemical's hazard is read from a named supplier's safety data sheet (SDS), cited in its row and
listed under "Safety data sheets read", all read on 2026-10-10; raw chicken has no sheet.
Suppliers' sheets differ and change: check the current one for the product you use. This is a starting list, not a
risk assessment; the hosting lab's own assessment comes first. An AI read these sheets and wrote this table, and a
separate AI review re-checked it against them; no person has checked it.

| Reagent | Hazard, from the SDS cited where there is one | Handling: the project's notes, checked against the sheets |
|---|---|---|
{rows_md}

{textwrap.fill(_en(also.group(1), nums), width=118)}

## Safety data sheets read
Naming a supplier is not an endorsement, and nothing here is a place to buy: these are the sheets that could be
opened, from suppliers the project's notes name, plus one UK supplier for sodium acrylate.

{refs_md}

## Waste
Hazardous waste goes through the lab's licensed route, with records. Nothing hazardous goes down the drain or into
general waste.

## The instrument: never bypassed, in code or in design
{never_md}

## The parts' safety ratings
Every BOM line's safety rating is in `pm/BOM.csv` (column `safety_rating`) and in `docs/BOM.md` (section "Safety
ratings"): read from the maker's own datasheet where the BOM names a part, or the rating the part must carry where it
names none.

## The law (UK), in short
UK REACH Annex XVII (entries 28-30) bars supplying CMR substances such as acrylamide and formaldehyde to the general
public, so the chemistry needs a laboratory. Research use only: no diagnostic claims, no human material, no live
animals. This is a summary, not legal advice; check the current rules where you are.
"""


# Audit A-10 (life 6): each BOM line's safety rating, from the maker's own datasheet where the BOM names a part, or
# the rating the part must carry where none is chosen. One tracked source (BOM_SAFETY) feeds the zip's pm/BOM.csv
# column and docs/BOM.md section; the SWELL page's ratings table must show the same lines with the same words.
BOM_SAFETY = SITE / "src" / "data" / "swell" / "bom_safety.json"
BOM_SRC = SITE / "src" / "pages" / "swell~parts" / "50-bom.html"
BOM_KINDS = {"maker-rating": "maker's rating", "required": "requirement (no maker rating)", "none": "none"}


@functools.lru_cache(maxsize=1)
def bom_safety() -> dict[str, dict]:
    data = json.loads(BOM_SAFETY.read_text(encoding="utf-8"))
    out = {}
    for e in data["lines"]:
        if e["kind"] not in BOM_KINDS or not e.get("rating_en"):
            die(f"{BOM_SAFETY.name}: {e.get('line')} needs a kind and a rating_en")
        if e["kind"] == "maker-rating" and not (e.get("source") or {}).get("url"):
            die(f"{BOM_SAFETY.name}: {e['line']} claims a maker's rating without the datasheet it came from")
        if "|" in e["rating_en"]:
            die(f"{BOM_SAFETY.name}: {e['line']}: no '|' in a rating (it goes into Markdown tables)")
        out[e["line"]] = e
    page = BOM_SRC.read_text(encoding="utf-8")
    shown = dict(re.findall(r'<tr data-line="([A-Z]-\d+)">.*?<td class="rating"><span class="en">(.*?)</span>', page, re.S))
    want = {k: v["rating_en"] for k, v in out.items() if v["kind"] != "none"}
    plain = {k: html.unescape(re.sub(r"<[^>]+>", "", v)).strip() for k, v in shown.items()}
    if plain != want:
        diff = sorted(set(plain.items()) ^ set(want.items()))[:3]
        die(f"{BOM_SRC.name}: the safety-ratings table differs from {BOM_SAFETY.name}: {diff}")
    return out


def check_main_table(bom: bytes) -> None:
    """Builder S8 (life 8): every part number in the SWELL page's main BOM table is pm/BOM.csv's primary_part_no
    ("—" where the BOM names none), so the table can't drift from the list it summarises."""
    want = {r["line_id"]: (r["primary_part_no"].strip() or "—")
            for r in csv.DictReader(io.StringIO(bom.decode("utf-8")))}
    page = BOM_SRC.read_text(encoding="utf-8")
    shown = re.findall(r'<tr><td>([A-Z]-\d+)</td>(?:(?!<tr).)*?<td class="partno">(.*?)</td>', page, re.S)
    rows = re.findall(r'<tr><td>([A-Z]-\d+)</td>', page)
    if len(shown) < 10 or [k for k, _ in shown] != rows or len(shown) != page.count('<td class="partno">'):
        die(f"{BOM_SRC.name}: every row of the main table needs one part-number cell "
            f"(rows {len(rows)}, cells read {len(shown)})")
    bad = [(k, html.unescape(v), want.get(k)) for k, v in shown if html.unescape(v) != want.get(k)]
    if bad:
        die(f"{BOM_SRC.name}: part numbers differ from pm/BOM.csv: {bad[:3]}")


def _bom_cell(e: dict) -> str:
    srcs = [s for s in (e.get("source"), e.get("source2")) if s and s.get("url")]
    parts = []
    for s in srcs:
        title = re.sub(r" *\[[^]]*\]", "", s["title"])          # drop the sourcing notes in square brackets
        parts.append(f" (source: {s['publisher']}, {title}, read {s['read']}: {s['url']})")
    return f"{BOM_KINDS[e['kind']]}: {e['rating_en']}{''.join(parts)}"


def add_bom_safety(path: str, text: str) -> str:
    """pm/BOM.csv gains a safety_rating column; docs/BOM.md gains a marked section listing every line's rating."""
    ratings = bom_safety()
    if path == "pm/BOM.csv":
        rows = list(csv.reader(io.StringIO(text)))
        ids = [r[0] for r in rows[1:] if r]
        if set(ids) != set(ratings):
            die(f"{BOM_SAFETY.name} and pm/BOM.csv list different lines: {sorted(set(ids) ^ set(ratings))}")
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(rows[0] + ["safety_rating"])
        h = {k: i for i, k in enumerate(rows[0])}
        for r in rows[1:]:
            if r:
                if r[h["price_basis"]] == "estimate":   # D-78: a typed estimate is not a price; the public copy blanks it
                    r[h["unit_low"]] = r[h["unit_high"]] = ""
                w.writerow(r + [_bom_cell(ratings[r[0]])])
        return buf.getvalue()
    if path == "docs/BOM.md":
        lines = ["", "## Safety ratings (added in this copy, 2026-10-10; updated 2026-10-11)", "",
                 "From the `safety_rating` column of `pm/BOM.csv` in this copy (`software/sim/budget.py` does not print it "
                 "yet). Where the BOM names a maker's part, the rating is read from that maker's own documents; where it "
                 "names none, or the part carries no rating, the line says what rating the part must carry. An AI "
                 "gathered these ratings and a separate AI review re-checked the makers' ratings and the sourced "
                 "requirements against their documents; no person has checked them. Shops are named elsewhere in this BOM only as "
                 "price sources; nothing here is a place to buy.", "",
                 "| line | item | safety rating |", "|---|---|---|"]
        # item names from this file's own (already scrubbed) "## Lines" table, in its order
        items = dict(re.findall(r"^\| ([A-Z]-\d+) \| [A-Z] \| (.*?) \| ", text.split("## Lines", 1)[-1], re.M))
        if set(items) != set(ratings):
            die(f"docs/BOM.md's line table and {BOM_SAFETY.name} list different lines: {sorted(set(items) ^ set(ratings))}")
        for line_id, item in items.items():
            lines.append(f"| {line_id} | {item} | {_bom_cell(ratings[line_id])} |")
        return text.rstrip("\n") + "\n" + "\n".join(lines) + "\n"
    return text


def home_lab_hits(name: str, text: str) -> list[str]:
    for path, phrase in HOME_LAB_OK:
        if path == name:
            text = text.replace(phrase, "")
    return sorted({m.group(0) for m in HOME_LAB.finditer(text)})


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
    return add_bom_safety(path, add_step_hazards(path, text, log))


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


# the one public address (D-51: info@x-wow.com is on every page); every other x-wow.com mailbox stays forbidden
PUBLIC_ALLOW = ["info@x-wow.com"]


def hits(text: str, rules: Rules) -> list[str]:
    for allowed in PUBLIC_ALLOW:
        text = text.replace(allowed, "")
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
    names = git("ls-tree", "-r", "--name-only", REV).decode("utf-8").splitlines()
    keep = []
    for n in names:
        if NEVER.match(n) or n.endswith(".gitkeep"):
            continue
        if n.startswith(ALLOW_DIRS) or n in ALLOW_FILES:
            keep.append(n)
    return sorted(keep)


def read_tracked(paths: list[str]) -> dict[str, bytes]:
    tar = tarfile.open(fileobj=io.BytesIO(git("archive", "--format=tar", REV, "--", *paths)))
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
CHANGES_BY_VERSION = {
    "v0.2.0": """After a fresh AI review of v0.1.0-g0 (2026-10-09; another Claude instance, not a person), see
`docs/design/strain_map_v2.md` first:
- **Red-team test:** gel S3, built by a separate AI agent from the data format alone and scored by its own
  script (`docs/design/s3_frozen_68194b0.json`). The pipeline now matches pre to post objects itself. Results are
  published as scored, failures included: the transverse ruler is biased about -18% by a blur shape it does not
  model (true blur widths do not fix it), and small local expansion changes go unflagged. Since then the
  anisotropy call is blocked while the transverse and landmark rulers disagree by more than 3% (development fix).
- **Axial ruler:** end Z-discs of broken fragments ignored (the v1 -0.1% bias is gone on the development gels);
  flat-fielding of the pre profile; anisotropy and stretch calls by effect size instead of "CI excludes 0".
- **Pre-image:** a go/no-go defined and tested in simulation (q = m*sqrt(N) >= 1.2) and the physics of each mode
  (`docs/design/preimage_v1.md`): DPC with four oblique LEDs chosen.
- **Protocol decisions (lab only):** the reference pre-image moves to after gelation, with the gap measured on the first gels (E-21);
  stain titration 6/20/40 ug/mL (E-22, D-49; the reason is the dye-density estimate in
  `docs/design/labelling_v1.md`, which still names the older 2/6/20). The dye goes on in DMSO, which carries it
  through skin: gloves (`SAFETY.md`).
- **Safety (lab only):** `SAFETY.md` cites a named supplier's SDS for each hazardous reagent in its table (GB format
  wherever one could be opened; none yet for the dye, which is not chosen, poly-L-lysine or PBS) and HSE's GB
  mandatory classification list; imidazole, the rigor buffer's reproductive toxicant, is added;
  each record step that gives amounts has its hazards beside it; F-8 (re-read from the protocol itself) and F-13
  (checked against the GB list) are updated in this copy of `pm/VERIFIED_FACTS.md`; every BOM line carries its
  safety rating, from the maker's own document where the BOM names a part (`pm/BOM.csv` column `safety_rating`,
  `docs/BOM.md` section "Safety ratings").
- **Drift:** a clock tile re-imaged every 50 tiles corrects scan-time drift.
- **Tool:** `software/swell_ruler`, the pipeline as a standalone package with an image front-end and tests.
  Its demo scores itself PASS/FAIL: the axial factor passes; the transverse factor and the planted patch fail.
- **Credit:** `docs/design/prior_art.md` (Zhang et al. 2016 and Sheard et al. 2019 got there first).
- **Package:** the original brief (`kit/`) is left out, and so are a few decisions and rows, each marked
  where it stood (Status, above). The licence texts and the X-WOW name and logo are labelled with their own
  terms (Licences).
- **Rebuilt for audit A-11 (2026-10-10, D-69):** water beads are out of the design (`pm/BOM.csv`, `docs/BOM.md`,
  `SAFETY.md`; P2's swelling check moves to the first real gel); the stepper gears get printed covers (H-27),
  the pumps enclosed roller heads, and opening the lid now stops every motor as well as the LED (a second
  switch pole drives a relay that opens both motor rails, INV-19); the pumps get a 12 V rail (H-28, whose
  maker warns it can get hot enough to burn; its placement inside the instrument isn't designed yet); the
  BOM's line table gives part numbers. The tool's README credits Chen, Tillberg & Boyden 2015 and GelMap and
  narrows what it claims to add. Every figure carries a SIMULATION
  label. `docs/design/prior_art.md` marks its wrong line about myofibril rulers and credits Chen, Tillberg &
  Boyden 2015 where the pairing is pitched. The red-team scripts carry no local paths, and `s3_gen.py` writes
  its gzip files with no time stamp, so two runs give identical files. Reports say synthetic data "tests" the
  pipeline, not "proves" it, and AI reviews are named as AI. `swell_ruler` 0.1.2 changes wording and messages
  only (it says when it skips a figure or a TIFF file, and labels the demo's figure); what it computes is
  unchanged.
- **Rebuilt for N-20 (2026-10-11, D-75):** the build needs no hot tools. The 3D printer and the soldering iron leave
  the BOM: a print service prints the parts (H-29), and every join the builder makes is a screw or lever terminal
  (H-31) or a ready-made plug-in lead, with no soldering and no crimping. The pumps' 12 V rail is now an enclosed
  DIN-rail converter with screw terminals (H-28, MEAN WELL DDR-60G-12), mounted out of reach in a closed electronics
  compartment that opens only with a screwdriver (H-30, not drawn yet). Prices and safety ratings change with it
  (`pm/BOM.csv`, `docs/BOM.md`).
- **Prices (2026-10-11, D-78):** a typed estimate is not a price. `pm/BOM.csv` keeps a price only for lines read on a
  supplier page, and `docs/BOM.md`'s totals add those lines alone, rounded down, with how many lines they cover. H-21
  is priced from its shop page; H-10's price came from a search result, so it is not yet read (`pm/VERIFIED_FACTS.md`,
  F-30). `pm/RISKS.md` R29 carries a dated correction.""",
}
CHANGES_BY_VERSION["v0.2.1"] = CHANGES_BY_VERSION["v0.2.0"] + """
- **Rebuilt 2026-10-12 (v0.2.1):** `SAFETY.md` and the BOM's safety ratings carry the stricter light rule of that
  day: the excitation light, LED plus diffuser, must be in IEC 62471's Exempt or Risk Group 1 group as fitted,
  inside the box whose lid cuts it, and the white and oblique LEDs in the Exempt group. Passages of D-54 and
  D-55 in `pm/DECISIONS.md` about a comment wall, which held counts drawn from a third-party platform's data, are
  left out of this copy, marked where they stood. Two wording updates follow the site: BOM line W-01 names the
  Safety and lab page, and `SAFETY.md`'s link to the laser experiment's safety box is a full address."""


def resolution_line(calc: dict) -> str:
    """The README's resolution sentence, from the package's own docs/design/calc_v0.json (no typed numbers)."""
    p, r = calc["params"], calc["resolution"]
    out = []
    for track, na in (("4x", p["na_4x"]), ("10x", p["na_10x"])):
        exp_nm = r[track]["rayleigh_nm"]
        e = 0.61 * p["lam_em"] / na * 1000 / exp_nm          # lens-alone Rayleigh / expanded Rayleigh
        out.append((round(exp_nm), f"{na:.2f}", f"{e:.1f}".rstrip("0").rstrip(".")))
    (a_nm, a_na, a_e), (b_nm, b_na, b_e) = out
    lo, hi = min(p["e_4x"]), p["e_10x"]
    return (f"SWELL is a design for an automated expansion-microscopy (ExM) imager, meant to be cheap. A hydrogel\n"
            f"would swell a specimen about {lo:g}-{hi:g}x, so that, on paper, an objective of NA {a_na} could resolve about {a_nm} nm in\n"
            f"the original specimen at {a_e}x expansion, and one of NA {b_na} about {b_nm} nm at {b_e}x (Rayleigh\n"
            f"criterion, `docs/design/calc_v0.md`); supermarket chicken myofibrils would carry their own rulers, so\n"
            f"every gel could check its own expansion. None of it has been built or measured.")


def readme(counts: dict[str, int], calc: dict) -> str:
    inside = "\n".join(f"| `{k}` | {v} |" for k, v in sorted(counts.items()))
    CHANGES = CHANGES_BY_VERSION.get(VERSION, "First published version.")
    return f"""# SWELL: G0 design package, {VERSION} ({DATE})

{resolution_line(calc)}
This zip is the desk-stage project, given away; what it leaves out, and why, is listed under Status.

## Status: read this first
- **Stage G0 (desk stage). Never built.** No part was bought, printed or wired; no gel was ever made.
- **Every result in here is simulated** (software/sim/ -> docs/design/, data/sim/). Nothing was measured
  on a real machine. Treat every number as a prediction until someone builds it.
- Facts checked against sources are listed with their verdicts in `pm/VERIFIED_FACTS.md`.
- **Costs: most lines are not yet priced.** Only lines whose price was read on a supplier page carry a price
  (`pm/BOM.csv`, `docs/BOM.md`); every total is a floor of those lines alone, and no total is compared with a
  cost target (D-78, 2026-10-11). Cost ranges and target comparisons in older records under `pm/` (decisions,
  risks, orders, audit) were built from typed estimates and are withdrawn; they stay as history.
- Personal details of the owner were removed from the private project files before release; each removal
  is marked `{REDACTED}` (postcodes as `[postcode removed]`). The removed lines concern the owner's own
  equipment, circumstances and schedule, and where the owner planned to work, not the SWELL design.
- **Chemistry only in a laboratory.** Several of the gel reagents are carcinogens, mutagens or reproductive
  toxicants (CMR substances). The chemistry belongs only in a laboratory with a fume hood, under that lab's own safety rules
  and risk assessments. This package holds no wet-lab protocol: where the records mention reagents, amounts or
  steps, they are design notes, not a method to follow, and each such file opens with a "Lab only" note.
  `SAFETY.md` gives the hazards of each hazardous reagent in its table as read from a named supplier's safety data
  sheet (cited with its revision date, all read on 2026-10-10; none yet for the dye, poly-L-lysine or PBS), their
  handling, the waste route and the instrument's safety rules. In this
  copy, each record step that gives reagent amounts has its hazards beside it.
- **Not included: the original brief (`kit/`).** It planned the gel chemistry at home, a plan withdrawn on
  2026-10-09 (`pm/ERRATA.md` E-18, `pm/DECISIONS.md` D-26), and that plan runs through its workspace,
  equipment, protocol, sourcing and risk files. Its design and QC were revised since: see `pm/AUDIT.md`,
  `pm/DECISIONS.md` and `docs/design/`. The records still refer to the brief's files (`kit/08`, "Kit 05" and so
  on) and to a project folder that holds no protocol yet (`protocols/`). The first version of this package
  ({ORIGINAL_DATE}) included the brief.
- **Also left out of this copy, and marked where they stood:** from `pm/DECISIONS.md`, D-31 (labs near where
  the owner planned to work), D-51 and D-53 (the X-WOW videos page and its comment wall), D-56 (the slide
  game), D-57 to D-64 (the AI agent that runs X-WOW, its accounts and channels, hosting for another X-WOW
  project, and taking parts of the live site down), and D-65 and D-67 (decisions about this package and the
  website; D-69 restates what they decided about SWELL); rows AU-26 and AU-34 of `pm/AUDIT.md`, row F-9 of `pm/VERIFIED_FACTS.md` and one schools idea in
  `pm/IDEAS.md`. The private records keep them.
- Some records cite project files that are not in this zip: anything under `pm/` other than the files listed
  under What is inside (for example the record of the safety data sheets read, with their hashes, audits, site
  notes, archived originals and working notes such as `pm/OPEN_FINDINGS.md`). Each safety data sheet's code and
  revision date are in `SAFETY.md`.
- Where the records disagree with `pm/ERRATA.md`, a later decision or this README, the later text wins. Any
  line saying results or IP stay with the owner is superseded by this free release (D-35, D-37; licence map
  below).
- Written, designed and simulated by an AI (Claude by Anthropic, via Claude Code), working from the owner's
  original brief and orders. The project stopped before its first gate (G0) was passed, and the checks were
  run by fresh AI sessions, not by an independent person. Check the code yourself.

## What changed in this version
{CHANGES}

## What is inside
| folder | files |
|---|---|
{inside}

- `SAFETY.md`: each hazardous reagent's hazards from its supplier's SDS (cited), their handling, the waste route and
  the instrument's safety rules (lab only).
- `pm/`: audit, decisions log, errata, invariants, risks, verified facts, orders, ideas, and the BOM with each
  part's safety rating (CSV; most lines not yet priced).
- `docs/`: design reports, figures, BOM, toolchain notes. `software/`: simulation code and tests. Every figure in
  `docs/design/figs/` is a simulation output, labelled SIMULATION on the image and in its PNG metadata by
  `software/sim/simlabel.py`. `strain_map_v2_S3.png` is frozen as first scored (commit 68194b0): its title's
  "independent generator" means a separate AI agent; `strain_map_v2_S3_rerun.png` is the current pipeline.
- `data/sim/`: per-myofibril tables from the strain-map simulation. `tools/`: the toolchain scripts.
- `software/swell_ruler/`: the ruler pipeline as a pip-installable tool (`pip install ./software/swell_ruler`).
- `software/redteam/`: the red-team gel S3 (generator, validator, scorer), written by a separate AI
  agent that read only `docs/design/obs_schema_v1.md`.

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
python software/redteam/s3_gen.py       # -> data/sim/S3/ (the red-team gel; about 100 s)
python software/sim/strain_map_v2.py    # -> docs/design/strain_map_v2.*: every gel run blind, S3 scored by the red team's scorer
python software/sim/preimage_v1.py      # -> docs/design/preimage_v1.*: contrast go/no-go and pre-image physics
python software/sim/labelling_v1.py     # -> docs/design/labelling_v1.*: dye density vs SNR (R30)
python -m pytest software/tests -q
cd software/swell_ruler && python -m pytest -q
```
`tools/setup_tools.sh` rebuilds the whole isolated toolchain (Windows + Git Bash; its paths assume the
project sits at D:/SWELL, so edit `tools/env.sh` / `tools/env.ps1` for your machine).

## Licences
| what | licence |
|---|---|
| Docs, text and data (everything not listed below) | CC0 1.0 Universal (`LICENSES/CC0-1.0.txt`) |
| Hardware design files: the bills of materials (`docs/BOM.md`, `pm/BOM.csv`) and any CAD, drawings or BOMs added later | CERN-OHL-P v2 (`LICENSES/CERN-OHL-P-2.0.txt`) |
| Software (the simulation code in `software/`, the scripts in `tools/`) | CC0 1.0 Universal |
| The licence texts in `LICENSES/` | their publishers' own terms; copied unmodified (CERN's text says "The CERN-OHL-P is copyright CERN 2020. Anyone is welcome to use it, in unmodified form only.") |

- **The X-WOW name and logo are trade marks, not covered by either licence;** the logo is a registered UK
  trade mark (UK00003425680). This zip contains no logo artwork.
- Short quotations from other people's papers (for example in `docs/design/prior_art.md`) stay theirs and
  are cited where they appear.
- Any part later forked from the OpenFlexure Microscope keeps OpenFlexure's own licence: its repository's
  License file is CERN-OHL-S v2 (strongly reciprocal), checked 2026-10-09 (`LICENSES.md`). This zip contains no
  OpenFlexure files.
- Third-party tools and packages keep their own licences (`LICENSES.md`).
- **Patents:** expansion microscopy is covered by MIT patents (e.g. US 10,309,879 B2; US 10,317,321 B2;
  US 11,408,890 B2). Commercial use may need a licence from MIT; research exemptions vary by country.
  These licences grant no patent rights held by others. This is not legal advice.
- **No warranty.** Provided as is. If you build it, its safety and legality are yours: the chemistry needs
  professional-user access (a lab), because UK REACH restricts the reagents.
- This package is a dated public disclosure ({DATE}; first version {ORIGINAL_DATE}), published so the design
  is prior art. The first version is no longer offered: it carried the withdrawn home plan (pm/ERRATA.md E-18).
- Trademarks belong to their owners; naming a product implies no endorsement.

Published by X-WOW: https://x-wow.com
"""


# ---------------------------------------------------------------- main
def drop_decisions(text: str) -> str:
    """Replace each DROP_DECISIONS entry (its "- **date · D-nn ·" bullet and the indented lines under it) with a
    one-line marker, so the gap shows where the entry stood."""
    lines, out, skip, dropped = text.split("\n"), [], False, set()
    for ln in lines:
        head = re.match(r"- \*\*(\d{4}-\d{2}-\d{2}) · (D-\d+) ·", ln)
        if head or ln.startswith(("- **", "#")):          # a new entry or a heading ends the one before
            skip = bool(head and head.group(2) in DROP_DECISIONS)
            if skip:
                dropped.add(head.group(2))
                out.append(f"- **{head.group(1)} · {head.group(2)} ·** *Left out of this copy (see README.md).*")
        if not skip:
            out.append(ln)
    if dropped != set(DROP_DECISIONS):
        die(f"pm/DECISIONS.md: could not find {sorted(set(DROP_DECISIONS) - dropped)} to leave out")
    return "\n".join(out)


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
        if path == "pm/DECISIONS.md":
            out = drop_decisions(out.decode("utf-8")).encode("utf-8")
        if path.endswith(".md") and REAGENTS.search(out.decode("utf-8")):
            out = (LAB_BANNER + out.decode("utf-8")).encode("utf-8")
        members[rename(path, rules)] = out

    check_main_table(members["pm/BOM.csv"])
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
    counts["SAFETY.md"] = 1
    members["SAFETY.md"] = safety_md().encode("utf-8")
    counts["README.md"] = 1
    members["README.md"] = readme(counts, json.loads(members["docs/design/calc_v0.json"])).encode("utf-8")

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
        problems += zip_problems({n: z.read(n) for n in names}, rules)
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
        "download.size_mb": {"value": mb(len(blob)), "source": rel_zip,
                             "how": f"zip size, {len(blob):,} bytes, in decimal megabytes (1 MB = 1,000,000 bytes)"},
        "download.files": {"value": str(len(names)), "source": rel_zip, "how": "number of files in the zip"},
        "download.date": {"value": ORIGINAL_DATE, "source": "tools/make_swell_zip.py: ORIGINAL_DATE",
                          "how": "first-publication date of the G0 package"},
        "download.version_date": {"value": DATE, "source": "tools/make_swell_zip.py: DATE",
                                  "how": "date of this version (also in the zip name)"},
        "download.version": {"value": VERSION, "source": "tools/make_swell_zip.py: VERSION",
                             "how": "release name of this version"},
        "download.zip_name": {"value": ZIP_NAME, "source": "tools/make_swell_zip.py: ZIP_NAME",
                              "how": "file name of this version"},
    }
    # The version this one replaced keeps its fingerprint on the public record (a hash republishes nothing): v0.2.0,
    # replaced on 2026-10-12, as recorded in src/data/numbers_download.json at site commit aa482a7.
    if VERSION == "v0.2.1":
        src_prev = "src/data/numbers_download.json at site commit aa482a7 (v0.2.0's own record)"
        numbers.update({
            "download.prev_version": {"value": "v0.2.0", "source": src_prev, "how": "the version this one replaced"},
            "download.prev_date": {"value": "2026-10-11", "source": src_prev, "how": "its version date"},
            "download.prev_sha256": {"value": "9996b636b5b0bfd7c5e6f6e3674afd0dd40aec179b7b804f01266406a71dfb49",
                                     "source": src_prev, "how": "SHA-256 of its zip, as it was published"}})
    if ORIGINAL_ZIP.exists() and ORIGINAL_ZIP != OUT_ZIP:      # the dated original keeps its own fingerprint
        ob = ORIGINAL_ZIP.read_bytes()
        with zipfile.ZipFile(io.BytesIO(ob)) as oz:
            n_orig = len(oz.namelist())
        rel_o = ORIGINAL_ZIP.relative_to(SITE).as_posix()
        numbers.update({
            "download.orig_sha256": {"value": hashlib.sha256(ob).hexdigest(), "source": rel_o,
                                     "how": "SHA-256 of the original zip, unchanged since first publication"},
            "download.orig_size_mb": {"value": mb(len(ob)), "source": rel_o,
                                      "how": f"zip size, {len(ob):,} bytes, in decimal megabytes"},
            "download.orig_files": {"value": str(n_orig), "source": rel_o, "how": "number of files in the zip"},
            "download.orig_name": {"value": ORIGINAL_ZIP.name, "source": rel_o, "how": "file name of the original"}})
    elif OUT_NUMBERS.exists():   # the original is no longer offered: keep the facts recorded while it was on disk
        old = json.loads(OUT_NUMBERS.read_text(encoding="utf-8"))
        kept = {k: v for k, v in old.items() if k.startswith("download.orig_")}
        if "download.orig_size_kb" in kept:   # once: bytes/1024 labelled KB becomes decimal MB, from the file
            kept.pop("download.orig_size_kb")   # as published (git history), checked against its recorded hash
            kept["download.orig_size_mb"] = original_size(kept["download.orig_sha256"]["value"])
        if len(kept) != 4:
            die(f"the original zip is gone and {OUT_NUMBERS.name} holds {len(kept)} of its 4 recorded facts")
        for v in kept.values():
            if "no longer offered" not in v["how"]:
                v["how"] += " (recorded while it was on disk; the file is no longer offered)"
        numbers.update(kept)
    numbers.update(bom_csv(members["pm/BOM.csv"]))
    numbers.update(wheel_numbers(members))
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


def mb(n: int) -> str:
    return f"{n / 1e6:.1f} MB"


def original_size(sha: str) -> dict:
    """The withdrawn original's size: the version in this repo's git history whose SHA-256 is the recorded one (the
    file changed before it was published, so the first version is not the one that was offered)."""
    rel = f"src/downloads/swell-g0-{ORIGINAL_DATE}.zip"
    res = subprocess.run(["git", "-C", str(SITE), "log", "--all", "--format=%H", "--", rel],
                         capture_output=True, text=True)
    for commit in res.stdout.split():
        got = subprocess.run(["git", "-C", str(SITE), "show", f"{commit}:{rel}"], capture_output=True)
        if got.returncode == 0 and hashlib.sha256(got.stdout).hexdigest() == sha:
            return {"value": mb(len(got.stdout)), "source": rel,
                    "how": f"zip size, {len(got.stdout):,} bytes, in decimal megabytes; read from git history "
                           f"(commit {commit[:7]}) and checked against the recorded SHA-256; the file is no longer "
                           "offered"}
    die(f"no version of {rel} in git history has the recorded SHA-256")


# Builder S8 (life 8): the zip's pm/BOM.csv, with its safety_rating column, is also offered on its own, so the page
# can link the full list directly; it is the same bytes as the zip's member, checked by the same final gate.
OUT_BOM = SITE / "src" / "downloads" / f"swell-bom-{DATE}.csv"


BOM_HEAD = ("# SWELL bill of materials: pm/BOM.csv from {zip} with these three lines added. Written by an AI (Claude by "
            "Anthropic via Claude Code) at the X-WOW owner's direction. Never built; most lines are not yet priced: their price "
            "columns are blank (price_basis 'estimate' means not yet read; D-78).\n"
            "# Licence: CERN-OHL-P v2 (a hardware design file); the X-WOW name and logo are trade marks and not covered. "
            "Shops are named only as price sources and never as places to buy.\n"
            "# More: https://x-wow.com/swell/#bom\n")


def bom_csv(data: bytes) -> dict:
    """The public CSV: a UTF-8 byte-order mark (so spreadsheets read µ, – and °), three '#' lines saying what it
    is, who made it and its licence, then the zip's pm/BOM.csv byte for byte."""
    head = BOM_HEAD.format(zip=ZIP_NAME)
    if not all(ln.startswith("# ") for ln in head.splitlines()):
        die("the BOM CSV's header lines must each start with '# '")
    OUT_BOM.write_bytes(b"\xef\xbb\xbf" + head.encode("utf-8") + data)
    n = sum(1 for r in csv.reader(io.StringIO(data.decode("utf-8"))) if r) - 1
    rel = OUT_BOM.relative_to(SITE).as_posix()
    return {"download.bom_csv": {"value": OUT_BOM.name, "source": rel,
                                 "how": "pm/BOM.csv from this zip, after a UTF-8 byte-order mark and three '#' lines "
                                        "(what it is, AI authorship, licence)"},
            "download.bom_lines": {"value": str(n), "source": rel, "how": "lines in the BOM, header excluded"}}


WHEELS = SITE / "src" / "downloads"


def wheel_numbers(members: dict[str, bytes]) -> dict:
    """The one swell_ruler wheel offered: its name and SHA-256, and a check that it was built from the same source as
    the zip's software/swell_ruler (same version, same module files byte for byte)."""
    wheels = sorted(WHEELS.glob("swell_ruler-*.whl"))
    if len(wheels) != 1:
        die(f"expected exactly one swell_ruler wheel in {WHEELS}, found {[w.name for w in wheels]}")
    whl = wheels[0]
    version = re.search(r'^version = "([^"]+)"', members["software/swell_ruler/pyproject.toml"].decode(), re.M).group(1)
    if whl.name != f"swell_ruler-{version}-py3-none-any.whl":
        die(f"{whl.name} is not version {version}, the zip's software/swell_ruler/pyproject.toml")
    with zipfile.ZipFile(whl) as w:
        inside = {n: w.read(n) for n in w.namelist() if n.startswith("swell_ruler/") and n.endswith(".py")}
    source = {n[len("software/swell_ruler/"):]: b for n, b in members.items()
              if n.startswith("software/swell_ruler/swell_ruler/") and n.endswith(".py")}
    if inside != source:
        die(f"{whl.name} was not built from the zip's software/swell_ruler: "
            f"{sorted(set(inside.items()) ^ set(source.items()))[:2]}")
    rel = whl.relative_to(SITE).as_posix()
    return {"download.wheel_name": {"value": whl.name, "source": rel, "how": "file name of the swell-ruler wheel"},
            "download.wheel_version": {"value": version, "source": "software/swell_ruler/pyproject.toml in the zip",
                                       "how": "version of the wheel and of the source in the zip (checked equal)"},
            "download.wheel_sha256": {"value": hashlib.sha256(whl.read_bytes()).hexdigest(), "source": rel,
                                      "how": "SHA-256 of the wheel; its modules match the zip's source byte for byte"}}


def zip_problems(members: dict[str, bytes], rules: Rules) -> list[str]:
    """Every check a finished zip must pass: private tokens, the never-list, kit/, the software allowlist, the slide
    game, and home-lab text (with the reviewed phrases, each of which must still be found)."""
    problems, used, steps_used = [], set(), set()
    if "SAFETY.md" not in members:
        problems.append("SAFETY.md: missing (the records name hazardous reagents, so the zip carries their hazards)")
    else:
        safety = members["SAFETY.md"].decode("utf-8", "replace")
        if "## Safety data sheets read" not in safety or "Not yet done" in safety:
            problems.append("SAFETY.md: no list of the supplier SDSs read (A-10)")
    if "pm/BOM.csv" in members:
        bom = list(csv.reader(io.StringIO(members["pm/BOM.csv"].decode("utf-8", "replace"))))
        col = bom[0].index("safety_rating") if bom and "safety_rating" in bom[0] else None
        if col is None or any(r and not r[col].strip() for r in bom[1:]):
            problems.append("pm/BOM.csv: every line needs its safety_rating (A-10)")
    if "docs/BOM.md" in members and "## Safety ratings" not in members["docs/BOM.md"].decode("utf-8", "replace"):
        problems.append("docs/BOM.md: no safety ratings section (A-10)")
    for name, data in members.items():
        if NEVER.match(name):
            problems.append(f"{name}: on the never-list")
        if name.startswith("kit/"):
            problems.append(f"{name}: the original brief stays out (it plans a home wet lab)")
        problems += check_member(name, data, rules)
        if name.startswith("software/") and not name.startswith(SWELL_SOFTWARE):
            problems.append(f"{name}: not on the SWELL software allowlist")
        if name.endswith(".png"):
            continue
        text = data.decode("utf-8", "replace")
        if NOT_SWELL.search(text):
            problems.append(f"{name}: points at the slide game, its bucket or its Worker")
        problems += [f"{name}: home-lab text /{h}/" for h in home_lab_hits(name, text)]
        if (name.endswith(".md") and name not in ("README.md", "SAFETY.md") and REAGENTS.search(text)
                and not text.startswith(LAB_BANNER)):
            problems.append(f"{name}: names reagents without the Lab only note at its top")
        used |= {(p, ph) for p, ph in HOME_LAB_OK if p == name and ph in text}
        sp, su = step_problems(name, text)
        problems += sp
        steps_used |= su
    problems += [f"{p}: reviewed phrase no longer found: {ph!r} (update HOME_LAB_OK)" for p, ph in HOME_LAB_OK
                 if (p, ph) not in used]
    problems += [f"{p}: reviewed step phrase no longer found: {ph!r} (update STEP_OK)" for p, ph in STEP_OK
                 if (p, ph) not in steps_used]
    return problems


def check_paths(paths: list[str]) -> int:
    rules = load_rules(RULES)
    bad = 0
    for p in paths:
        root = Path(p)
        files = [root] if root.is_file() else [f for f in root.rglob("*") if f.is_file()]
        for f in files:
            if f.suffix.lower() in {".zip"}:
                with zipfile.ZipFile(f) as z:
                    probs = [f"{f.name}: {x}" for x in zip_problems({n: z.read(n) for n in z.namelist()}, rules)]
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
    ap.add_argument("--rev", help="SWELL commit to build from (read at import time; default: the pinned REV)")
    ap.add_argument("--date", help="version date (read at import time; default: the current version)")
    ap.add_argument("--check", nargs="+", metavar="PATH", help="only scan these files/folders for forbidden tokens")
    a = ap.parse_args()
    if a.check:
        sys.exit(check_paths(a.check))
    build(a.dump)
