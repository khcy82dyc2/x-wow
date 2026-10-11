#!/usr/bin/env python3
"""Write src/data/numbers_tested.json: the numbers of the "Tested harder" section (Life 5), with their sources.

Stdlib only:  python tools/numbers_tested.py
Inputs, copied unchanged into src/data/swell/:
  strain_map_v2.json  the blind pipeline on every synthetic gel, and the red-team gel S3 with its own scorer
  preimage_v1.json    contrast-to-precision curve, illumination slope, pre-image mode physics
  labelling_v1.json   dye density needed for SNR 10 vs what an NHS-ester stain gives
"""
import json
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
DATA = SITE / "src" / "data" / "swell"
OUT = SITE / "src" / "data" / "numbers_tested.json"
MINUS = "−"
N = {}


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


# the pipeline's call words, as the 中文 page shows them (a call missing here fails the run)
CALL_ZH = {"isotropic": "各向同性", "anisotropic": "各向异性", "blocked": "不予判定", "not yet run": "尚未运行"}


def put(key, value, source, how):
    key = "tested." + key
    if key in N:
        sys.exit(f"duplicate key {key}")
    N[key] = {"value": value, "source": source, "how": how}


def num(x, d):
    s = f"{x:.{d}f}"
    if float(s) == 0:
        s = f"{0:.{d}f}"
    return s.replace("-", MINUS)


def pct(x, d=2, plus=False):
    s = num(x * 100, d)
    if plus and not s.startswith(MINUS) and float(s) != 0:
        s = "+" + s
    return s + "%"


V2 = load("strain_map_v2.json")
PI = load("preimage_v1.json")
LA = load("labelling_v1.json")
F2, FP, FL = "src/data/swell/strain_map_v2.json", "src/data/swell/preimage_v1.json", "src/data/swell/labelling_v1.json"
dev = V2["dev"]
gels = ("S0", "S1", "S1b", "S2", "S4")

# ---------------------------------------------------------------- blind pipeline on the development gels
means = [dev[g]["metrics"]["gel_mean_E_err"] for g in gels]
put("v2_mean_err", f"{pct(min(means), 2, True)} to {pct(max(means), 2, True)}", F2 + ": dev[S0,S1,S1b,S2,S4].metrics.gel_mean_E_err",
    "range over the five gels: gel-mean axial E minus truth")
rms = [dev[g]["metrics"]["per_fibril_Eax_rms"] for g in gels if g != "S4"]
put("v2_rms", f"{pct(min(rms))}–{pct(max(rms))}", F2 + ": dev[S0,S1,S1b,S2].metrics.per_fibril_Eax_rms",
    "per-myofibril axial error, gels without drift")
rec = [dev[g]["metrics"]["match_recall"] for g in gels]
put("v2_match", f"{pct(min(rec), 1)}–{pct(max(rec), 1)}", F2 + ": dev[*].metrics.match_recall",
    "pre↔post pairs found with no pairing given")
blind = dev["S1b"]["metrics"]
put("v2_blind_stretch_own", pct(blind["detection"]["stretched patch"], 0), F2 + ": dev.S1b.metrics.detection['stretched patch']",
    "area of the blind gel's stretched patch flagged by its own detector")
put("v2_blind_stretch_any", pct(blind["detection_any_flag"]["stretched patch"], 0),
    F2 + ": dev.S1b.metrics.detection_any_flag['stretched patch']", "same, by any detector")
a0 = dev["S0"]["metrics"]["anisotropy"]
put("v2_s0_aniso", f"{pct(a0['est'])} [{pct(a0['ci95'][0])}, {pct(a0['ci95'][1])}]", F2 + ": dev.S0.metrics.anisotropy",
    "estimate and 95% CI on the perfect gel")
put("v2_s0_call", a0["call"], F2 + ": dev.S0.metrics.anisotropy.call", "the effect-size call")
put("v2_s0_call_zh", CALL_ZH[a0["call"]], F2 + ": dev.S0.metrics.anisotropy.call", "the effect-size call, in Chinese")
a2 = dev["S2"]["metrics"]["anisotropy"]
put("v2_s2_aniso", f"{pct(a2['est'])} [{pct(a2['ci95'][0])}, {pct(a2['ci95'][1])}]", F2 + ": dev.S2.metrics.anisotropy",
    "estimate and 95% CI on the gel with a planted anisotropy")
put("v2_s2_truth", pct(a2["truth"]), F2 + ": dev.S2.metrics.anisotropy.truth", "true value")
d4, d4n = dev["S4"]["metrics"], dev["S4_no_clock"]["metrics"]
put("drift_slope_clock", f"{num(d4['drift_slope_pct_per_h'], 3)}%/h", F2 + ": dev.S4.metrics.drift_slope_pct_per_h",
    "slope of the axial error against acquisition time, clock correction on")
put("drift_slope_none", f"{num(d4n['drift_slope_pct_per_h'], 2)}%/h", F2 + ": dev.S4_no_clock.metrics.drift_slope_pct_per_h",
    "same, with the clock removed")
put("drift_mean_clock", pct(d4["gel_mean_E_err"], 2, True), F2 + ": dev.S4.metrics.gel_mean_E_err", "gel-mean error, clock on")
put("drift_mean_none", pct(d4n["gel_mean_E_err"], 2, True), F2 + ": dev.S4_no_clock.metrics.gel_mean_E_err",
    "gel-mean error, clock removed")

# ---------------------------------------------------------------- red-team gel S3 (scored by the red team's own script)
s3 = V2.get("S3") or {}
SC = s3.get("score") or {}


def dig(d, *path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def s3put(key, path, fmt, label):
    v = dig(SC, *path)
    if v is None or isinstance(v, str):
        val = "not yet run" if not SC else ("not provided" if v is None else v)
    else:
        val = fmt(v)
    put("s3_" + key, val, F2 + ": S3.score." + ".".join(path), label + " (red team's scorer)")


put("s3_ran", "yes" if SC else "not yet", F2 + ": S3.score", "whether the red-team gel was scored in this build")
s3put("recall", ("matching", "recall"), lambda v: pct(v, 1), "pre/post pairs found")
s3put("precision", ("matching", "precision"), lambda v: pct(v, 1), "pairs that were right")
s3put("wrong", ("matching", "wrong_partner"), lambda v: str(int(v)), "fibrils paired with the wrong partner")
s3put("debris", ("debris", "rejection"), lambda v: pct(v, 0), "debris objects rejected")
s3put("mean_err", ("gel_mean_E_ax", "rel_error_pct"), lambda v: num(v, 2) + "%", "gel-mean axial error, correct matches")
s3put("median_err", ("gel_mean_E_ax", "median_rel_error_pct"), lambda v: num(v, 2) + "%", "gel-median axial error")
s3put("ax_rms", ("E_ax_correct_matches", "rms"), lambda v: pct(v, 1), "per-myofibril axial RMS error")
s3put("ax_robust", ("E_ax_correct_matches", "robust_sd"), lambda v: pct(v, 2), "per-myofibril axial robust spread")
s3put("ax_beyond", ("E_ax_correct_matches", "frac_beyond_2pct"), lambda v: pct(v, 1), "myofibrils beyond ±2%")
s3put("ax_n", ("E_ax_correct_matches", "n"), lambda v: f"{int(v):,}", "myofibrils with an axial ratio")
s3put("coverage", ("E_ax_coverage",), lambda v: pct(v, 0), "true pairs that got an axial ratio")
s3put("tr_bias", ("E_tr_correct_matches", "bias"), lambda v: pct(v, 1), "transverse ruler bias")
s3put("false", ("false_flags", "false_flag_frac"), lambda v: pct(v, 1), "false flags on clean gel")
s3put("aniso_est", ("anisotropy", "estimate"), lambda v: pct(v, 1, True), "anisotropy estimate (E_ax/E_tr − 1)")
s3put("aniso_truth", ("anisotropy", "truth"), lambda v: pct(v, 1, True), "true anisotropy (E_tr/E_ax − 1)")
s3put("drift", ("residual_drift", "slope_pct_per_h"), lambda v: num(v, 3) + "%/h", "residual drift after the clock")
# the red team's scorer states the truth as E_tr/E_ax − 1 while the pipeline reports E_ax/E_tr − 1: same convention here
t_tr_ax = dig(SC, "anisotropy", "truth")
put("s3_aniso_truth_axtr", pct(1 / (1 + t_tr_ax) - 1, 1, True) if isinstance(t_tr_ax, (int, float)) else "not provided",
    F2 + ": S3.score.anisotropy.truth", "true anisotropy converted to the pipeline's convention: 1/(1 + truth) − 1")
# S3 rerun with the TRUE blur widths (development): does calibration explain the transverse bias?
TP = load("s3_true_psf.json")
put("s3_true_psf_bias", pct(TP["transverse_bias_median"], 1, True) if TP else "not run",
    "src/data/swell/s3_true_psf.json: transverse_bias_median",
    "transverse bias on S3 rerun with the red team's true core blur widths (development)")
# S3 rerun with the current pipeline (development only: S3 has been seen) — the rulers-disagree guard
R = (V2.get("S3_rerun") or {}).get("gel", {}).get("anisotropy", {})
put("s3r_aniso_call", R.get("call", "not yet run"), F2 + ": S3_rerun.gel.anisotropy.call",
    "anisotropy call on S3 by the current pipeline (development rerun)")
put("s3r_aniso_call_zh", CALL_ZH[R.get("call", "not yet run")], F2 + ": S3_rerun.gel.anisotropy.call",
    "the same call, in Chinese")
put("s3r_tr_vs_land", pct(R["tr_vs_landmark"], 1, True) if isinstance(R.get("tr_vs_landmark"), (int, float)) else "n/a",
    F2 + ": S3_rerun.gel.anisotropy.tr_vs_landmark", "median E_tr/E_land_tr − 1 over fibrils (development rerun)")
for d in (dig(SC, "defects", "per_defect") or []):
    put("s3_flag_" + d["kind"], pct(d["flagged_frac"], 0), F2 + f": S3.score.defects.per_defect[{d['kind']}]",
        f"area of the planted {d['kind']} region flagged by any flag (red team's scorer)")
# ---------------------------------------------------------------- pre-image contrast
q = PI["q_go"]["10"]
put("q_go", num(q["rms_1pct"], 1), FP + ": q_go['10'].rms_1pct", "q = m·√N for 1% per-fibril error at 10 sarcomeres")
put("q_half", num(q["rms_0.5pct"], 1), FP + ": q_go['10']['rms_0.5pct']", "q for 0.5%")
sd = PI["slope_demo"]
put("slope_v1", pct(sd["slope 20% | v1"]), FP + ": slope_demo['slope 20% | v1']", "20% illumination slope, mean removed only")
put("slope_v2", pct(sd["slope 20% | v2"]), FP + ": slope_demo['slope 20% | v2']", "same, flat-fielded (v2)")
modes = PI["modes"]
dpc = modes["DPC, 4 oblique LEDs (σ 0.85), 4 frame pairs"]
put("dpc_m", pct(dpc["m_best"], 1), FP + ": modes['DPC, 4 …'].m_best", "predicted striation modulation, DPC")
put("dpc_q", num(dpc["q_best"], 0), FP + ": modes['DPC, 4 …'].q_best", "predicted q with 4 frame pairs")
lin = {k: v for k, v in modes.items() if k.startswith("crossed linear")}
put("pol_cover", "–".join(pct(v["covered"], 0) for v in sorted(lin.values(), key=lambda v: v["covered"])),
    FP + ": modes['crossed linear …'].covered", "fibril orientations reaching the go q, cheap to good film")
ph = PI["physics"]["SL 1.69"]["0.94 µm path"]
put("ret_nm", f"{num(ph['pol_A_band_retardance_nm'], 1)} nm", FP + ": physics['SL 1.69']['0.94 µm path'].pol_A_band_retardance_nm",
    "A-band retardance of a typical myofibril")
put("phase_mrad", f"{num(1e3 * ph['phase_fundamental_rad'], 0)} mrad", FP + ": physics[…].phase_fundamental_rad",
    "fundamental of the striation phase profile")

# ---------------------------------------------------------------- labelling (R30)
mf = LA["min_fraction_snr10"]
put("lab_min_100", f"{pct(mf['100 ms | 1 µm myofibril'])}–{pct(mf['100 ms | 2 µm myofibril'])}",
    FL + ": min_fraction_snr10['100 ms | *']", "labelled amines needed for SNR 10 at 100 ms, 1–2 µm myofibrils")
put("lab_min_200", f"{pct(mf['200 ms | 1 µm myofibril'])}–{pct(mf['200 ms | 2 µm myofibril'])}",
    FL + ": min_fraction_snr10['200 ms | *']", "same at 200 ms")
pan = LA["panexm_20ug_ml_fraction"]
put("lab_pan", pct(pan[1], 1), FL + ": panexm_20ug_ml_fraction[1]", "central estimate at 20 µg/mL NHS ester")
put("lab_pan_range", f"{pct(pan[0])}–{pct(pan[2], 1)}", FL + ": panexm_20ug_ml_fraction[0,2]", "over every input range")
put("lab_kit", pct(pan[1] / 10, 2), FL + ": panexm_20ug_ml_fraction[1] / 10", "the kit's 2 µg/mL: ten times less dye")

# ---------------------------------------------------------------- evidence ladder pass marks (D-50)
F_D = "pm/DECISIONS.md D-50 (evidence-ladder pass marks)"
put("rung1_sl", "1.5–2.0 µm", F_D, "rung 1: the sarcomere length must fall inside this range")
put("rung1_spread", "±5%", F_D, "rung 1: three strips agree within this of their mean")
put("rung2_n", "10", F_D, "rung 2: myofibrils with ≥ 10 sarcomeres needed")
put("rung3_pass", "40%", F_D, "rung 3: fragments with ≥ 8 sarcomeres needed")
s0 = dev["S0"]["metrics"]
put("rung3_sim", pct(s0["n_eligible"] / s0["n_fibrils"], 0), F2 + ": dev.S0.metrics.n_eligible / n_fibrils",
    "fraction of simulated fragments with ≥ 8 whole sarcomeres")
put("rung4_gels", "3", F_D, "rung 4: gels that must pass")
put("rung4_prec", "≤ 1%", F_D, "rung 4: per-myofibril axial precision")
put("rung4_mean", "±0.5%", F_D, "rung 4: the gate D-50 set on the gel-mean axial factor against the overview camera's factor; dropped 2026-10-10 (D-68), quoted for the record")
put("rung4_iso", "±3%", "pm/DECISIONS.md D-32 (the transverse gate D-50 points to)", "rung 4: isotropy gate")

OUT.write_text(json.dumps(N, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
print(f"wrote {len(N)} numbers -> {OUT.relative_to(SITE)}")
