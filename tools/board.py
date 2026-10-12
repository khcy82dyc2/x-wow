"""The Inventions board (x-wow.com/inventions): every bar computed from files, every date from the card's record.

Data: src/data/inventions.json (one structured file: the ladder, the fields and every invention with the paths of its
stage artifacts). A stage counts only when its artifact exists and passes a small check of its form (below). The bar is
the sum of the weights of the stages that count; the label is the furthest stage reached with no gap before it. Each counted
stage's date is the card's record (inventions.json "stage_dates": the day that stage's proof file first existed in X-WOW's
own records); "last advanced" is the latest of them. Not git: a squashed push gives every file the push's date (life 10's
AI review). A counted stage without a valid recorded date, or with one in the future, is a build problem.
Stdlib only; build.py calls html() for the {{board}} placeholder and fails on any broken artifact path.
"""
from __future__ import annotations

import csv
import html as H
import io
import json
import re
import zipfile
from datetime import date
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
SRC = SITE / "src"
DATA = SRC / "data" / "inventions.json"
SPARKS = SRC / "data" / "sparks.json"  # the Sparks lane and the Killed list (no bars, no novelty claims)
FRESH_DAYS = 7  # "new" and "moved" marks: within this many days of the build date
# Drawings, schematics and CAD: the only files that can count for the "design" stage. CAD and schematic formats count
# by their type; an SVG or PDF counts only when its path says it is a drawing, schematic or CAD file; a raster image
# (a plot, a render, a photo) never counts, because nothing in its form says it is a design.
DESIGN_EXT = {".dxf", ".dwg", ".step", ".stp", ".stl", ".3mf", ".scad", ".fcstd", ".kicad_sch", ".kicad_pcb", ".sch", ".brd"}
DESIGN_DOC_EXT = {".svg", ".pdf"}
DESIGN_WORDS = ("drawing", "schematic", "cad")


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def read(path: str) -> bytes | None:
    """src-relative path, or zip:<src-relative zip>!<member>."""
    if path.startswith("zip:"):
        z, member = path[4:].split("!", 1)
        f = SRC / z
        if not f.exists():
            return None
        with zipfile.ZipFile(f) as zf:
            return zf.read(member) if member in zf.namelist() else None
    f = SRC / path
    if f.is_dir():
        return b"".join(p.read_bytes() for p in sorted(f.rglob("*")) if p.is_file()) or None
    return f.read_bytes() if f.exists() else None


def form_ok(stage: str, raw: bytes, path: str) -> bool:
    t = raw.decode("utf-8", "ignore")
    if stage == "concept":
        return all(h in t for h in ("## Gate 0", "## The twelve principles", "## Prior-art search", "## Expert"))
    if stage == "theory":
        return len(re.findall(r"\d+(?:\.\d+)?", t)) >= 3
    if stage == "parts":
        rows = list(csv.DictReader(io.StringIO(t)))
        if len(rows) < 5:
            return False
        keys = {k.lower(): k for k in rows[0]}
        price = next((keys[k] for k in ("unit_low", "unit_price", "price", "price_gbp") if k in keys),
                     next((keys[k] for k in keys if "price" in k and "basis" not in k), None))
        link = next((keys[k] for k in keys if "url" in k or "link" in k), None)
        when = next((keys[k] for k in keys if "date" in k), None)
        # D-78 (2026-10-11): a typed estimate is not a price, so a row whose basis column says "estimate" isn't priced
        basis = next((keys[k] for k in keys if "basis" in k), None)
        unpriced = any(basis and (r.get(basis) or "").strip().lower() == "estimate" for r in rows)
        return bool(price and link and when) and not unpriced and all((r.get(price) or "").strip() != "" for r in rows)
    if stage == "guide":
        return "## Safety" in t and bool(re.search(r"^\s*1\.", t, re.M))
    if stage == "design":
        # the ladder's proof is "a design document with drawings, a schematic or CAD": a text file alone never counts
        member = path.split("!")[-1]
        ext = Path(member).suffix.lower()
        return ext in DESIGN_EXT or (ext in DESIGN_DOC_EXT and any(w in member.lower() for w in DESIGN_WORDS))
    if stage == "prototype":
        # hardware: a build report checked by someone outside X-WOW; software: a public working version at an address
        return "## Build report" in t and "## Checked by" in t or bool(re.search(r"^## Public version\s*\n+\s*https://\S+", t, re.M))
    if stage == "validated":
        return all(h in t for h in ("## Claims tested", "## Results", "## Checked by"))
    return False  # an unknown stage never counts


def stage_date(inv: dict, stage: str, problems: list) -> str:
    when = (inv.get("stage_dates") or {}).get(stage, "")
    try:
        ok = date.fromisoformat(when) <= date.today() and len(when) == 10
    except ValueError:
        ok = False
    if not ok:
        problems.append(f"{inv['id']}: the {stage} stage counts, but stage_dates.{stage} is missing, malformed or in the future ({when!r})")
    return when if ok else ""


def compute() -> dict:
    d = load()
    ladder = d["ladder"]
    cards, events, problems = [], [], []
    for inv in d["inventions"]:
        reached, last = [], ""
        for st in ladder:
            paths = inv["artifacts"].get(st["id"], [])
            ok_paths = []
            for p in paths:
                raw = read(p)
                if raw is None:
                    problems.append(f"{inv['id']}: {st['id']} artifact missing: {p}")
                elif form_ok(st["id"], raw, p):
                    ok_paths.append(p)
            if ok_paths:
                when = stage_date(inv, st["id"], problems)
                reached.append({"id": st["id"], "date": when, "files": ok_paths})
                events.append({"date": when, "inv": inv["id"], "stage": st["id"]})
                last = max(last, when)
        got = {r["id"] for r in reached}
        pct = sum(st["weight"] for st in ladder if st["id"] in got)
        # the label is the furthest stage with every stage before it counted, so it never implies a skipped stage
        top = -1
        for i, st in enumerate(ladder):
            if st["id"] not in got:
                break
            top = i
        if "theory" in got and not (inv.get("theory_checked_by_en") and inv.get("theory_checked_by_zh")):
            problems.append(f"{inv['id']}: the theory stage counts, but the card doesn't name who checked it (theory_checked_by_en/zh)")
        cards.append({**inv, "reached": reached, "pct": pct, "top": top, "last": last})
    events.sort(key=lambda e: (e["date"], ladder.index(next(s for s in ladder if s["id"] == e["stage"]))), reverse=True)
    gi = next(i for i, s in enumerate(ladder) if s["id"] == "guide")
    ti = next(i for i, s in enumerate(ladder) if s["id"] == "theory")
    today = date.today()

    def fresh(d: str) -> bool:
        try:
            return 0 <= (today - date.fromisoformat(d)).days < FRESH_DAYS
        except ValueError:
            return False
    sp = json.loads(SPARKS.read_text(encoding="utf-8")) if SPARKS.exists() else {"sparks": [], "killed": []}
    arrivals = [x.get("added", "") for x in sp["sparks"]] + [r["date"] for c in cards for r in c["reached"] if r["id"] == "concept"]
    newest = max([a for a in arrivals if a] or [""])
    for c in cards:
        concept = next((r["date"] for r in c["reached"] if r["id"] == "concept"), "")
        c["mark"] = "new" if concept and concept == newest else ("moved" if fresh(c["last"]) else "")
    for x in sp["sparks"] + sp["killed"]:
        when = x.get("added") or x.get("date") or ""
        try:
            ok = date.fromisoformat(when) <= today
        except ValueError:
            ok = False
        if not ok:
            problems.append(f"sparks.json: {x.get('id')} has a missing, malformed or future date ({when!r})")
    for x in sp["sparks"]:
        x["mark"] = "new" if x.get("added") and x.get("added") == newest else ""
    counters = {"ideas": len(cards), "past_theory": sum(1 for c in cards if c["top"] >= ti),
                "guides": sum(1 for c in cards if any(r["id"] == "guide" for r in c["reached"])),
                "sparks": sum(1 for x in sp["sparks"] if x.get("status") == "spark"),
                "moved_week": sum(1 for c in cards for r in c["reached"] if fresh(r["date"])),
                "killed": len(sp["killed"]), "today": today.isoformat()}
    return {"ladder": ladder, "fields": d["fields"], "cards": cards, "events": events[:8], "counters": counters,
            "sparks": sp["sparks"], "killed": sp["killed"], "newest": newest, "problems": problems, "_ti": ti, "_gi": gi}


def html(root: str, numbers: dict) -> tuple[str, list[str]]:
    """The board, in the order the owner set on 2026-10-12: a stats strip, the cards straight away (sortable and
    filterable), then the Sparks lane, then the Killed list (collapsed). Labels are single-language spans, so only
    the page's active language ever shows (option text, which can't hold spans, is English: the site is English-only)."""
    b = compute()
    lad, fields = b["ladder"], {f["id"]: f for f in b["fields"]}
    names = {c["id"]: c for c in b["cards"]}
    e = H.escape

    def both(en, zh):
        return f'<span class="en">{e(en)}</span><span class="zh">{e(zh)}</span>'

    def mark(m):
        return (f' <span class="bd-mark bd-mark-{m}">{both("new", "新")}</span>' if m == "new" else
                f' <span class="bd-mark bd-mark-{m}">{both("moved", "前进")}</span>' if m == "moved" else "")

    def cost_value(c):
        if c.get("cost_key") and c["cost_key"] in numbers:
            return str(numbers[c["cost_key"]]["value"])
        return None

    def cost(c):
        v = cost_value(c)
        if v is not None:
            return both(c["cost_en"].replace("{}", v), c["cost_zh"].replace("{}", v))
        return both(c["cost_en"], c["cost_zh"])

    def cost_num(c):   # priced-so-far, for sorting; unpriced cards sort last
        v = cost_value(c)
        m = re.search(r"\d[\d,]*(?:\.\d+)?", v or "")
        return m.group(0).replace(",", "") if m else ""

    k = b["counters"]
    # the latest motion, folded into the stats strip
    feed = [("stage", ev["date"], ev) for ev in b["events"]]
    feed += [("spark", x["added"], x) for x in sorted(b["sparks"], key=lambda x: x["name_en"]) if x.get("status") == "spark" and x.get("added")]
    feed.sort(key=lambda t: t[1], reverse=True)   # newest day first; within a day, names A-Z (the same rule as the home page)
    last = ""
    if feed:
        kind, when, ev = feed[0]
        if kind == "spark":
            what = both("spark: " + ev["name_en"], "火花：" + ev["name_zh"])
        else:
            st = next(x for x in lad if x["id"] == ev["stage"])
            what = both(names[ev["inv"]]["name_en"] + " → " + st["en"], names[ev["inv"]]["name_zh"] + " → " + st["zh"])
        last = f'<li class="bd-last">{both("last moved", "最近前进")} <time>{e(when)}</time>: {what}</li>'
    out = [f'<ul class="bd-stats" aria-label="Board totals">'
           f'<li><b>{k["ideas"]}</b> {both("invention" if k["ideas"] == 1 else "inventions", "项发明")}</li>'
           f'<li><b>{k["past_theory"]}</b> {both("past the theory check", "项已过理论核对")}</li>'
           f'<li><b>{k["guides"]}</b> {both("build guides", "份制作指南")}</li>'
           f'<li><a href="#sparks"><b>{k["sparks"]}</b> {both("sparks", "个火花")}</a></li>'
           f'<li><a href="#killed"><b>{k["killed"]}</b> {both("killed", "个被否决")}</a></li>'
           f'{last}<li class="bd-asof">{both("as of " + k["today"], "截至 " + k["today"])}</li></ul>']

    used = [f for f in b["fields"] if f["id"] in {c["field"] for c in b["cards"]}]
    fopts = "".join(f'<option value="{e(f["id"])}">{e(f["en"])}</option>' for f in used)
    sopts = "".join(f'<option value="{i}">{e(s["en"])}</option>' for i, s in enumerate(lad))
    out.append(
        '<div class="bd-filter" role="group" aria-label="Sort and filter the inventions">'
        f'<label>{both("Sort", "排序")} <select data-sort>'
        '<option value="pct">Completion</option><option value="last">Recently moved</option>'
        '<option value="new">Newest</option><option value="cost">Cheapest (priced so far)</option>'
        '<option value="field">Category</option></select></label>'
        f'<label>{both("Category", "类别")} <select data-field><option value="">All</option>{fopts}</select></label>'
        f'<label>{both("Reached at least", "至少到达")} <select data-stage><option value="-1">Any stage</option>{sopts}</select></label>'
        '</div>')
    cards = []
    for c in sorted(b["cards"], key=lambda c: (-c["pct"], c["name_en"])):
        got = {r["id"] for r in c["reached"]}
        segs = "".join(f'<i class="{"on" if s["id"] in got else ""}" style="flex:{s["weight"]}" title="{e(s["en"])}"></i>' for s in lad)
        label = lad[c["top"]] if c["top"] >= 0 else {"en": "Not started", "zh": "未开始"}
        f = fields.get(c["field"], {"en": c["field"], "zh": c["field"]})
        concept = next((r["date"] for r in c["reached"] if r["id"] == "concept"), "")
        link = (f'<a class="bd-more" href="{root}{e(c["page"])}">{both("See the invention", "看看这个发明")} →</a>') if c.get("page") else ""
        files = " · ".join(f'<a href="{root}{e(p)}">{both(s["en"].lower(), s["zh"])}</a>' for s in lad for r in c["reached"] if r["id"] == s["id"]
                           for p in r["files"][:1] if not p.startswith("zip:"))
        cards.append(
            f'<article class="bd-card panel" data-field="{e(c["field"])}" data-fieldname="{e(f["en"])}" data-pct="{c["pct"]}" data-top="{c["top"]}" '
            f'data-last="{e(c["last"])}" data-new="{e(concept)}" data-cost="{cost_num(c)}" data-name="{e(c["name_en"])}">'
            f'<p class="bd-field">{both(f["en"], f["zh"])}{mark(c["mark"])}</p><h3>{both(c["name_en"], c["name_zh"])}</h3>'
            f'<p class="bd-hook">{both(c["hook_en"], c["hook_zh"])}</p><p class="bd-what">{both(c["what_en"], c["what_zh"])}</p>'
            f'<p class="bd-cost">{cost(c)}</p>'
            f'<div class="bd-bar" role="img" aria-label="{c["pct"]}% of the stage ladder">{segs}</div>'
            f'<p class="bd-stage"><b>{c["pct"]}%</b> · {both(label["en"], label["zh"])} · {both("last advanced", "上次前进")} <time>{e(c["last"] or "–")}</time>'
            f' <a class="bd-q" href="#how-counted" title="How the bar is counted" aria-label="How the bar is counted">?</a></p>'
            f'<p class="bd-files">{both("Proof files: ", "证据文件：")}{files or "–"}</p>'
            + (f'<p class="bd-checked">{both("Theory checked by: " + c["theory_checked_by_en"], "理论由谁核对：" + c["theory_checked_by_zh"])}</p>'
               if any(r["id"] == "theory" for r in c["reached"]) else "")
            + (f'<p class="bd-gate">{both(c["gate_en"], c["gate_zh"])}</p>' if c.get("gate_en") else "")
            + f'<p class="bd-steal">{both("Steal this happily: no credit needed.", "开心拿走：不用署名。")}</p>{link}</article>')
    out.append('<div class="bd-grid">' + "".join(cards) + "</div>")

    live = sorted((x for x in b["sparks"] if x.get("status") == "spark"), key=lambda x: x["name_en"])
    live.sort(key=lambda x: x.get("added", ""), reverse=True)  # newest day first, names A-Z within a day

    def prior(x):
        st = x.get("prior_art_status") or "not yet searched"
        return f'<span class="bd-pa bd-pa-{e(st.replace(" ", "-"))}">{both("Prior art: " + st, "在先技术：" + st)}</span>'
    sparks = "".join(
        f'<li class="bd-spark panel" data-new="{e(x.get("added", ""))}" data-name="{e(x["name_en"])}" data-pa="{e(x.get("prior_art_status") or "not yet searched")}">'
        f'<p class="bd-field">{both("spark", "火花")} · <time>{e(x["added"])}</time>{mark(x["mark"])} {prior(x)}</p>'
        f'<h3>{both(x["name_en"], x["name_zh"])}</h3><p>{both(x["line_en"], x["line_zh"])}</p>'
        f'<details class="bd-spark-more"><summary>{both("Why it might matter, and where it came from", "可能的意义和来源")}</summary>'
        f'<p class="bd-why">{both(x["why_en"], x["why_zh"])}</p>'
        f'<p class="bd-files">{both("From: " + x["from_en"] + ". Earlier work: " + x["prior_art_en"] + ".", "来源：" + x["from_zh"] + "。前人的工作：" + x["prior_art_zh"] + "。")}</p></details></li>'
        for x in live)
    out.append(f'<section class="bd-sparks" id="sparks" aria-labelledby="sparks-h"><h2 class="kicker" id="sparks-h">{both("Sparks", "火花")} ({len(live)})</h2>'
               f'<p class="bd-lane-note">{both("Ideas that passed the first test: each could make something hidden visible. Untested, not claims: none is called new before its search for earlier work, and none has a bar until it is a card.", "通过了第一关的点子：每一个都可能让藏着的、太小的、太快的或太暗的东西被看见。是还没检验的点子，不是结论：在查完前人的工作之前，不说任何一个是新的；变成卡片之前，也没有进度条。")}</p>'
               f'<div class="bd-filter" role="group" aria-label="Sort the sparks"><label>{both("Sort sparks", "火花排序")} <select data-spark-sort>'
               '<option value="new">Newest</option><option value="name">Name</option><option value="pa">Prior-art result</option></select></label></div>'
               f'<ul class="bd-spark-list">{sparks}</ul></section>')
    dead = sorted(b["killed"], key=lambda x: x["name_en"])
    dead.sort(key=lambda x: x["date"], reverse=True)
    out.append(f'<details class="bd-killed" id="killed"><summary>{both("Killed, and why", "被否决的点子，以及原因")} ({len(dead)})</summary><ul>'
               + "".join(f'<li><time>{e(x["date"])}</time> <b>{both(x["name_en"], x["name_zh"])}</b>: {both(x["reason_en"], x["reason_zh"])}</li>' for x in dead)
               + "</ul></details>")
    return "\n".join(out), b["problems"]


if __name__ == "__main__":
    b = compute()
    for c in b["cards"]:
        print(f"{c['id']:10s} {c['pct']:3d}%  top={b['ladder'][c['top']]['id'] if c['top'] >= 0 else '-'}  last={c['last']}  "
              f"stages={[r['id'] for r in c['reached']]}")
    print("counters", b["counters"], "| problems", b["problems"])


def newest_spark(root: str) -> str:
    """One line for the home page: the newest spark on the board, linking to the lane."""
    b = compute()
    live = [x for x in b["sparks"] if x.get("status") == "spark"]
    if not live:
        return ""
    x = sorted(sorted(live, key=lambda x: x["name_en"]), key=lambda x: x.get("added", ""), reverse=True)[0]   # newest day, then A-Z
    e = H.escape
    return (f'<p class="home-spark"><span class="en">Newest spark ({e(x["added"])}): <b>{e(x["name_en"])}</b>. '
            f'{e(x["line_en"])} <a href="{root}inventions/#sparks">All {len(live)} sparks</a></span>'
            f'<span class="zh">最新火花（{e(x["added"])}）：<b>{e(x["name_zh"])}</b>。{e(x["line_zh"])} '
            f'<a href="{root}inventions/#sparks">全部 {len(live)} 个火花</a></span></p>')
