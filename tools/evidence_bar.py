#!/usr/bin/env python3
"""The evidence bar: how close each invention is to "anyone could rebuild it and it would work".

Stdlib only:  python tools/evidence_bar.py          (writes src/data/evidence.json)
              python tools/evidence_bar.py --check  (exit 1 if the stored bar no longer matches its sources)
build.py runs the check on every build, so the bar can never drift from its evidence.

Seven stages, as stages rather than a percentage:
  idea → designed → simulated → red-teamed → bench-tested → built by someone else → rebuilt independently
The first four are desk evidence and can fill at most 4 of 7. The last three move only on real-world reports:
checked reports of real builds that the owner forwards from info@x-wow.com (src/data/ladder_results.json, recorded
with tools/ladder_results.py; email only since 2026-10-11, no GitHub issues). Every stage says what it is made of. All sources are public files in this repo:
the latest SWELL zip's file list (design pieces, risk register), the simulation JSON with its checks, the red
team's score, and the claim tags on the invention's own page.
"""
from __future__ import annotations

import io
import json
import re
import sys
import zipfile
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
SRC = SITE / "src"
OUT = SRC / "data" / "evidence.json"
NUM_OUT = SRC / "data" / "numbers_evidence.json"   # the counts pages quote in prose, so no page types them

STAGES = [
    ("idea", "Idea", "想法"),
    ("designed", "Designed", "设计"),
    ("simulated", "Simulated", "模拟"),
    ("red_teamed", "Blind-tested", "盲测"),
    ("bench_tested", "Bench-tested", "台面实测"),
    ("built_by_others", "Built by someone else", "别人造出来"),
    ("rebuilt", "Rebuilt independently", "独立复现"),
]
DESK = 4  # the first four stages are desk evidence

# What "designed" is made of for SWELL: each piece is present when the latest package contains it.
SWELL_PIECES = [
    ("concept and calculations", "设计计算", ["docs/design/calc_v0.md"]),
    ("optics on paper", "光学设计", ["docs/design/optics_v1.md"]),
    ("bill of materials (most lines not yet priced)", "物料清单（大部分条目还没查价）", ["docs/BOM.md"]),
    ("QC pipeline and strain map", "质控流水线与应变图", ["docs/design/strain_map_v2.md", "docs/design/strain_map_v1.md"]),
    ("pre-image design", "膨胀前成像设计", ["docs/design/preimage_v1.md"]),
    ("wet-lab protocol", "湿实验流程", ["protocols/SWELL-ExM4-v0.1.md"]),
    ("safety pack", "安全资料包", ["protocols/safety/"]),
    ("mechanical CAD", "机械 CAD", ["hardware/cad/"]),
    ("instrument software", "仪器软件", ["software/swell/"]),
]


def latest_zip():
    zips = sorted((SRC / "downloads").glob("swell-g0-*.zip"))
    return zips[-1] if zips else None


def zip_names(path):
    with zipfile.ZipFile(path) as z:
        return [n for n in z.namelist() if not n.endswith("/") and not n.endswith(".gitkeep")]


def risks_from_zip(path):
    """Counts of open and closed risks in pm/RISKS.md inside the package (status = last table column)."""
    with zipfile.ZipFile(path) as z:
        try:
            text = z.read("pm/RISKS.md").decode("utf-8")
        except KeyError:
            return None
    open_, closed = 0, 0
    for line in text.splitlines():
        if re.match(r"^\| R\d+ \|", line):
            status = line.rstrip(" |").rsplit("|", 1)[-1].strip().lower()
            if status.startswith(("open", "in progress")):
                open_ += 1
            else:
                closed += 1
    return {"open": open_, "retired_or_mitigated": closed}


def claim_tags(slug):
    counts = {"verified": 0, "cited": 0, "sim": 0, "predicted": 0, "untested": 0}
    dirs = [SRC / "pages" / slug] + sorted((SRC / "pages").glob(slug + "~*"))   # a front page and its sub-pages
    for f in sorted(f for d in dirs for f in d.glob("[0-9]*.html")):
        for m in re.finditer(r'class="tag (verified|cited|sim|predicted|untested)">(?![\u3400-\u9fff])', f.read_text(encoding="utf-8")):
            counts[m.group(1)] += 1
    return counts


def ladder():
    f = SRC / "data" / "ladder_results.json"
    if not f.exists():
        return {"fetched": None, "rungs_passed": {}, "built": 0, "rebuilt": 0}
    return json.loads(f.read_text(encoding="utf-8"))


def swell():
    z = latest_zip()
    names = zip_names(z) if z else []
    pieces = []
    for en, zh, paths in SWELL_PIECES:
        have = any(any(n == p or n.startswith(p) for n in names) for p in paths)
        pieces.append({"en": en, "zh": zh, "present": have})
    n_have = sum(p["present"] for p in pieces)
    v2_path = SRC / "data" / "swell" / "strain_map_v2.json"
    v2 = json.loads(v2_path.read_text(encoding="utf-8")) if v2_path.exists() else {}
    checks = v2.get("checks", [])
    c = {"pass": sum(x["result"] == "pass" for x in checks), "fail": sum(x["result"] == "fail" for x in checks),
         "below_limit": sum(x["result"] == "below limit" for x in checks)}
    s3 = (v2.get("S3") or {}).get("score")
    lad = ladder()
    rungs = {str(k): int(v) for k, v in (lad.get("rungs_passed") or {}).items()}
    home_rungs = sum(1 for r in ("1", "2", "3") if rungs.get(r, 0) > 0)
    # rung 1 (laser on raw chicken) is a warm-up: it measures chicken, not SWELL's ruler, so it never counts as a bench test
    ruler_rungs = sum(1 for r in ("2", "3") if rungs.get(r, 0) > 0)
    stages = {}
    stages["idea"] = {"status": "done", "made_of_en": "a public page with the problem, the idea and its sources",
                      "made_of_zh": "一个公开页面：问题、想法和出处"}
    stages["designed"] = {"status": "done" if n_have == len(pieces) else ("partial" if n_have else "none"),
                          "made_of_en": f"{n_have} of {len(pieces)} design pieces written: "
                                        + "; ".join(("✓ " if p["present"] else "✗ ") + p["en"] for p in pieces),
                          "made_of_zh": f"{len(pieces)} 份设计文件写好了 {n_have} 份："
                                        + "；".join(("✓ " if p["present"] else "✗ ") + p["zh"] for p in pieces)}
    stages["simulated"] = {"status": "done" if checks and c["fail"] == 0 else ("partial" if checks else "none"),
                           "made_of_en": f"{c['pass']} simulated checks pass, {c['fail']} fail, {c['below_limit']} below "
                                         "the detection limit (synthetic gels)",
                           "made_of_zh": f"模拟检查 {c['pass']} 项通过、{c['fail']} 项未通过、{c['below_limit']} 项低于"
                                         "检测下限（合成凝胶）"}
    if s3:
        # the red-team stage is complete only when its headline checks pass; otherwise it is partial
        def g(*path):
            d = s3
            for k in path:
                d = d.get(k) if isinstance(d, dict) else None
            return d
        heads = [
            ("pairing", "配对", (g("matching", "precision") or 0) >= 0.99 and (g("matching", "recall") or 0) >= 0.95),
            ("debris rejected", "排除碎屑", (g("debris", "rejection") or 0) >= 0.95),
            ("gel-mean axial factor", "整体轴向倍数", abs(g("gel_mean_E_ax", "rel_error_pct") or 99) <= 0.5),
            ("per-myofibril axial precision ≤ 1%", "单根轴向精度 ≤ 1%", (g("E_ax_correct_matches", "rms") or 1) <= 0.01),
            ("transverse ruler and anisotropy call", "横向标尺与各向异性判断", bool(g("anisotropy", "call_right"))),
            ("planted defects flagged", "人为缺陷被标出",
             all(d["flagged_frac"] >= 0.8 for d in (g("defects", "per_defect") or [{"flagged_frac": 0}]))),
            ("false flags ≤ 5%", "误报 ≤ 5%", (g("false_flags", "false_flag_frac") or 1) <= 0.05),
        ]
        n_ok = sum(ok for _, _, ok in heads)
        s3_counts = {"s3_pass": n_ok, "s3_total": len(heads)}
        stages["red_teamed"] = {
            "status": "done" if n_ok == len(heads) else "partial",
            "made_of_en": f"a synthetic test gel built separately from the analysis code, scored by its builder's own script and published as scored: "
                          f"{n_ok} of {len(heads)} headline checks pass ("
                          + "; ".join(("✓ " if ok else "✗ ") + en for en, _, ok in heads) + ")",
            "made_of_zh": f"一块由另一个 AI 智能体造的红队凝胶，由红队自己的脚本评分并原样公布：{len(heads)} 项主要检查通过 {n_ok} 项（"
                          + "；".join(("✓ " if ok else "✗ ") + zh for _, zh, ok in heads) + "）"}
    else:
        s3_counts = {}
        stages["red_teamed"] = {"status": "none", "made_of_en": "no separately built test gel scored yet",
                                "made_of_zh": "还没有红队凝胶的评分"}
    stages["bench_tested"] = {"status": "done" if ruler_rungs == 2 else ("partial" if ruler_rungs else "none"),
                              "made_of_en": f"{ruler_rungs} of 2 ruler rungs (2: see the stripes, 3: fragment lengths) "
                                            f"passed by a checked report; rung 1 (a laser on chicken) is a warm-up and "
                                            f"does not count ({home_rungs} of 3 home rungs passed in all)",
                              "made_of_zh": f"标尺的 2 级阶梯（第 2 级看见条纹、第 3 级碎片长度）中，有 {ruler_rungs} 级有经核对的"
                                            f"及格报告；第 1 级（用激光量鸡肉）只是热身，不算（3 级在家阶梯共通过 {home_rungs} 级）"}
    built, rebuilt = int(lad.get("built", 0)), int(lad.get("rebuilt", 0))
    stages["built_by_others"] = {"status": "done" if built else "none",
                                 "made_of_en": f"{built} checked report(s) of a working build by someone else",
                                 "made_of_zh": f"{built} 份经核对的他人成功制造报告"}
    stages["rebuilt"] = {"status": "done" if rebuilt else "none",
                         "made_of_en": f"{rebuilt} independent rebuild(s) passing the same QC thresholds",
                         "made_of_zh": f"{rebuilt} 次独立复现并通过同样的质控门限"}
    order = [k for k, _, _ in STAGES]
    current = 0
    for i, k in enumerate(order):
        if stages[k]["status"] == "none":
            break
        current = i + 1
    # the next step is the frontier: the stage after the current one (earlier partial stages show as hatched)
    nxt = order[current] if current < len(order) else None
    next_en = {"designed": "write the missing design pieces (protocol, safety pack, CAD, instrument software)",
               "simulated": "fix the failing simulated checks or state them as open problems",
               "red_teamed": "have someone who never saw the pipeline build a test gel",
               "bench_tested": "rung 2 of the evidence ladder: see the stripes under any 40× microscope",
               "built_by_others": "a builder outside X-WOW reports a working build",
               "rebuilt": "an independent rebuild passes the same QC thresholds"}
    next_zh = {"designed": "补齐缺的设计文件（流程、安全资料包、CAD、仪器软件）",
               "simulated": "修好未通过的模拟检查，或写明为未解问题",
               "red_teamed": "请一个没看过流水线的红队造一块测试凝胶",
               "bench_tested": "证据阶梯第 2 级：用任何 40 倍显微镜看见条纹",
               "built_by_others": "X-WOW 以外的建造者报告造出了能用的机器",
               "rebuilt": "一次独立复现通过同样的质控门限"}
    # rung 1 is a warm-up that cannot move the bar, so the next step is always rung 2
    risks = risks_from_zip(z) if z else None
    return {"slug": "swell", "stage": current, "stages_total": len(order), "desk_stages": DESK,
            "next": nxt, "next_en": next_en.get(nxt, ""), "next_zh": next_zh.get(nxt, ""),
            "stages": stages, "claims": claim_tags("swell"), "risks": risks,
            "counts": {"design_written": n_have, "design_total": len(pieces),
                       "design_missing_en": [p["en"] for p in pieces if not p["present"]],
                       "design_missing_zh": [p["zh"] for p in pieces if not p["present"]], **s3_counts},
            "sources": {"package": z.name if z else None, "simulation": "src/data/swell/strain_map_v2.json",
                        "ladder": "src/data/ladder_results.json", "ladder_fetched": lad.get("fetched")}}


def compute():
    return {"swell": swell()}


def _list_en(items):
    items = ["the " + i for i in items]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _list_zh(items):
    if not items:
        return "无"
    head = "、".join(items[:-1])
    if not head:
        return items[-1]
    sep = " 和" if head[-1].isascii() and head[-1].isalnum() else "和"  # a space after a Latin word, as the pages write it
    return head + sep + items[-1]


def numbers(data):
    """The counts the pages quote in prose ({{n:evidence.*}}), computed here so a page never types them."""
    k = data["swell"]["counts"]
    src = "src/data/evidence.json: swell.counts"
    how = "computed by tools/evidence_bar.py from the latest SWELL package and the blind test's score"
    out = {
        "evidence.swell_design_written": {"value": str(k["design_written"]), "source": src, "how": how},
        "evidence.swell_design_total": {"value": str(k["design_total"]), "source": src, "how": how},
        "evidence.swell_design_missing_en": {"value": _list_en(k["design_missing_en"]) if k["design_missing_en"] else "none",
                                             "source": src, "how": how},
        "evidence.swell_design_missing_zh": {"value": _list_zh(k["design_missing_zh"]), "source": src, "how": how},
    }
    if "s3_total" in k:
        out.update({
            "evidence.swell_s3_pass": {"value": str(k["s3_pass"]), "source": src, "how": how},
            "evidence.swell_s3_fail": {"value": str(k["s3_total"] - k["s3_pass"]), "source": src, "how": how},
            "evidence.swell_s3_total": {"value": str(k["s3_total"]), "source": src, "how": how}})
    return out


def main():
    data = compute()
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    nums = numbers(data)
    if "--check" in sys.argv:
        old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else None
        old_n = json.loads(NUM_OUT.read_text(encoding="utf-8")) if NUM_OUT.exists() else None
        if old != data or old_n != nums:
            print("evidence bar is stale: run python tools/evidence_bar.py", file=sys.stderr)
            sys.exit(1)
        print("evidence bar matches its sources")
        return
    OUT.write_text(text, encoding="utf-8", newline="\n")
    NUM_OUT.write_text(json.dumps(nums, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    s = data["swell"]
    print(f"SWELL: stage {s['stage']} of {s['stages_total']} ({STAGES[s['stage'] - 1][1]}); next: {s['next_en']}")


if __name__ == "__main__":
    main()
