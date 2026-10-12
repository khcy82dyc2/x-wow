#!/usr/bin/env python3
"""Write src/data/numbers_tested.json: the numbers of the "Tested harder" section (Life 5), with their sources.

Stdlib only:  python tools/numbers_tested.py
Inputs, copied unchanged into src/data/swell/:
  strain_map_v2.json  the blind pipeline on every synthetic gel, and the red-team gel S3 with its own scorer
  preimage_v1.json    contrast-to-precision curve, illumination slope, pre-image mode physics
  labelling_v1.json   dye density needed for SNR 10 vs what an NHS-ester stain gives
A few numbers are settings in the simulation code or a line in the red team's notes, not outputs. Those are read
from the published SWELL package (src/downloads/swell-g0-*.zip, the latest, as tools/evidence_bar.py reads it): a
function's default or a module constant, parsed with ast, or one quoted table cell, so no number is typed here.
"""
import ast
import json
import math
import re
import sys
import zipfile
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
DATA = SITE / "src" / "data" / "swell"
OUT = SITE / "src" / "data" / "numbers_tested.json"
MINUS = "−"
N = {}
_ZIPS = sorted((SITE / "src" / "downloads").glob("swell-g0-*.zip"))
if not _ZIPS:
    sys.exit("no swell-g0-*.zip in src/downloads: the code settings below are read from the package")
ZIP = _ZIPS[-1]
FZ = f"src/downloads/{ZIP.name}!"


def zip_text(name):
    with zipfile.ZipFile(ZIP) as z:
        return z.read(name).decode("utf-8")


def _func(name, func):
    for node in ast.walk(ast.parse(zip_text(name))):
        if isinstance(node, ast.FunctionDef) and node.name == func:
            return node
    sys.exit(f"{name} in {ZIP.name}: no function {func}()")


def py_defaults(name, func):
    """{parameter: default} of a function in a .py file inside the package."""
    a = _func(name, func).args
    pos = a.args[len(a.args) - len(a.defaults):]
    return {p.arg: ast.literal_eval(v) for p, v in zip(pos, a.defaults)}


def py_const(name, var):
    """A module-level constant (NAME = literal, or A, B = literal, literal) in a .py file inside the package."""
    for node in ast.parse(zip_text(name)).body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == var:
                    return ast.literal_eval(node.value)
                if isinstance(t, ast.Tuple) and isinstance(node.value, ast.Tuple):
                    for tt, vv in zip(t.elts, node.value.elts):
                        if isinstance(tt, ast.Name) and tt.id == var:
                            return ast.literal_eval(vv)
    sys.exit(f"{name} in {ZIP.name}: no module constant {var}")


def calls_keep_defaults(name, func, max_pos, names):
    """Fail unless every call of func in this package file passes at most max_pos positional arguments and none of
    the named parameters by keyword, so those parameters ran at the defaults read with py_defaults()."""
    found = 0
    for node in ast.walk(ast.parse(zip_text(name))):
        if isinstance(node, ast.Call) and func in (getattr(node.func, "id", None), getattr(node.func, "attr", None)):
            found += 1
            if len(node.args) > max_pos or any(k.arg is None or k.arg in names for k in node.keywords):
                sys.exit(f"{name} in {ZIP.name}: a call of {func}() may set {sorted(names)}, so its defaults are not what ran")
    if not found:
        sys.exit(f"{name} in {ZIP.name}: no call of {func}()")


def harmonic_weights(name, func):
    """(w1, w2) in the label-free profile model 1 + m(w1 cos 2πφ + w2 cos 4πφ) inside func."""
    w = {}
    for node in ast.walk(_func(name, func)):
        if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult) and isinstance(node.left, ast.Constant)
                and isinstance(node.right, ast.Call) and getattr(node.right.func, "attr", "") == "cos"):
            arg = node.right.args[0]
            while isinstance(arg, ast.BinOp):
                arg = arg.left
            if isinstance(arg, ast.Constant):
                w[arg.value] = node.left.value      # cos(2π…) is the fundamental, cos(4π…) the second harmonic
    if set(w) != {2, 4}:
        sys.exit(f"{name} in {ZIP.name}: {func}() no longer has the profile 1 + m(w1 cos 2πφ + w2 cos 4πφ)")
    return w[2], w[4]


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
# Q-11 (S2): the bootstrap interval resamples myofibrils as if independent; how often it misses a known truth
ci_miss = [g for g in gels if not (dev[g]["metrics"]["anisotropy"]["ci95"][0] <= dev[g]["metrics"]["anisotropy"]["truth"]
                                   <= dev[g]["metrics"]["anisotropy"]["ci95"][1])]
put("v2_ci_miss", str(len(ci_miss)), F2 + ": dev[S0,S1,S1b,S2,S4].metrics.anisotropy (ci95 against truth)",
    "own gels whose 95% CI for the anisotropy misses the true value (" + ", ".join(ci_miss) + ")")
put("v2_n_gels", str(len(gels)), F2 + ": dev[S0,S1,S1b,S2,S4]", "own synthetic gels in version 2 (S4_no_clock is S4 rerun)")
etr = [dev[g]["metrics"]["per_fibril_Etr_bias"] for g in gels]
put("v2_etr_bias", f"{pct(min(etr), 2, True)} to {pct(max(etr), 2, True)}",
    F2 + ": dev[S0,S1,S1b,S2,S4].metrics.per_fibril_Etr_bias",
    "range over the five own gels of the mean of (measured ÷ true transverse factor − 1) per myofibril")
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
s3put("drift", ("residual_drift", "slope_pct_per_h"), lambda v: num(v, 2) + "%/h",
      "residual drift after the clock: straight-line slope of the axial error against time, correct matches with error < 5%")
# Q-11 (N1 b): what that slope can and can't show
s3put("drift_se", ("residual_drift", "slope_se_pct_per_h"), lambda v: num(v, 2) + "%/h", "standard error of that slope")
s3put("drift_uncorr", ("residual_drift", "uncorrected_drift_slope_pct_per_h"),
      lambda v: ("+" if v > 0 else "") + num(v, 2) + "%/h",
      "the same slope for the planted drift itself: what a pipeline with no drift correction would show")
s3put("drift_all", ("residual_drift", "slope_all_pct_per_h"), lambda v: num(v, 2) + "%/h",
      "the slope over every correct match, the errors beyond 5% included")
_rd = dig(SC, "residual_drift") or {}
s3put("drift_excluded", ("residual_drift", "excluded_abs_err_over_5pct"), lambda v: f"{int(v):,}",
      "correct matches left out of the slope for an axial error beyond 5%")
s3put("drift_n", ("residual_drift", "n"), lambda v: f"{int(v):,}", "correct matches with a time and an axial ratio")
_bins = [b.get("median") for b in _rd.get("binned_median_rel_err_pct", [])]
if _bins and all(isinstance(b, (int, float)) for b in _bins):
    _worst = max(abs(b) for b in _bins)                  # the scorer gives these medians in %
    _bound = (math.floor(_worst * 10) + 1) / 10          # the next tenth of a percent above the largest
    put("s3_drift_bins", f"{num(_bound, 1)}%", F2 + ": S3.score.residual_drift.binned_median_rel_err_pct[*].median",
        f"a bound: every one of the {len(_bins)} time-binned median axial errors lies within ± this "
        f"(largest {num(_worst, 4)}%; red team's scorer)")
else:
    put("s3_drift_bins", "not yet run", F2 + ": S3.score.residual_drift.binned_median_rel_err_pct", "red team's scorer")
_u, _se = dig(SC, "residual_drift", "uncorrected_drift_slope_pct_per_h"), dig(SC, "residual_drift", "slope_se_pct_per_h")
if isinstance(_u, (int, float)) and isinstance(_se, (int, float)) and not abs(_u) < _se:
    sys.exit("45-tested.html says the planted drift's own slope is smaller than the slope's standard error: no longer true")
if SC and dig(SC, "anisotropy", "ci_covers_truth") is not False:
    sys.exit("45-tested.html says S3's anisotropy interval misses its truth too: no longer true")
# the drift the red team planted: one cell of its table of planted defects (the README in the package)
_m = re.search(r"\|\s*Expansion drift\s*\|[^|\n]*\|\s*rise to (\+?\d+(?:\.\d+)?) ?%", zip_text("software/redteam/README.md"))
if not _m:
    sys.exit(f"software/redteam/README.md in {ZIP.name}: the 'Expansion drift' row no longer says 'rise to …%'")
put("s3_drift_planted", f"{_m.group(1)}%", FZ + "software/redteam/README.md, table of planted defects, row 'Expansion drift'",
    "quoted: the peak of the scan-time expansion drift the red team planted in S3, before it fell back")
# the map flags (swell-ruler): a local change must beat max(FLOOR, 4 standard errors) after Gaussian smoothing
F_SMAP = "software/swell_ruler/swell_ruler/strainmap.py"
put("flag_floor", pct(py_const(F_SMAP, "FLOOR"), 0), FZ + F_SMAP + ": FLOOR",
    "smallest smoothed local change a map flag can fire on (four standard errors where that is larger)")
put("flag_kernel", f"{num(py_const(F_SMAP, 'KERNEL'), 0)} µm", FZ + F_SMAP + ": KERNEL",
    "standard deviation of the Gaussian that smooths the maps before the flags are judged")
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
# Q-11 (N1 c): the same demo with even light, and how many draws each figure rests on
put("slope0_v1", pct(sd["slope 0% | v1"]), FP + ": slope_demo['slope 0% | v1']", "even light, mean removed only (v1)")
put("slope0_v2", pct(sd["slope 0% | v2"]), FP + ": slope_demo['slope 0% | v2']", "even light, flat-fielded (v2)")
F_PRE = "software/sim/preimage_v1.py"
calls_keep_defaults(F_PRE, "slope_demo", 0, {"trials", "seed"})
put("slope_trials", f"{py_defaults(F_PRE, 'slope_demo')['trials']:,}", FZ + F_PRE + ": slope_demo(trials=…)",
    "random draws behind each figure; every case draws its own, and no confidence interval is computed")
if not sd["slope 20% | v2"] < sd["slope 0% | v2"]:
    sys.exit("45-tested.html says the new code reads lower with a 20% slope than with even light: no longer true")
modes = PI["modes"]
dpc = modes["DPC, 4 oblique LEDs (σ 0.85), 4 frame pairs"]
put("dpc_m", pct(dpc["m_best"], 1), FP + ": modes['DPC, 4 …'].m_best", "predicted striation modulation, DPC")
put("dpc_q", num(dpc["q_best"], 0), FP + ": modes['DPC, 4 …'].q_best", "predicted q with 4 frame pairs")
put("dpc_n", f"{dpc['N_best']:,.0f}", FP + ": modes['DPC, 4 …'].N_best",
    "photo-electrons (detected photons) per sample that this q assumes, 4 frame pairs, shot noise only")
# Q-11 (S4): the before-image the own-gel simulations assumed (v1 strain_map_sim.py and v2 gen_dev.py share it)
F_GEN, F_V1SIM, F_V2SIM = "software/sim/gen_dev.py", "software/sim/strain_map_sim.py", "software/sim/strain_map_v2.py"
_g2, _g1 = py_defaults(F_GEN, "generate"), py_defaults(F_V1SIM, "pre_post_profiles")
_w2, _w1 = harmonic_weights(F_GEN, "pre_axial"), harmonic_weights(F_V1SIM, "pre_post_profiles")
calls_keep_defaults(F_V2SIM, "generate", 3, {"m_pre", "photons_pre"})
calls_keep_defaults(F_V1SIM, "pre_post_profiles", 3, {"m_pre", "photons_pre"})
if (_g2["m_pre"], _g2["photons_pre"], _w2) != (_g1["m_pre"], _g1["photons_pre"], _w1):
    sys.exit("the v1 and v2 own-gel generators no longer share their before-image settings")
_m_fund = _w2[0] * _g2["m_pre"]
_src = (FZ + F_GEN + ": generate(m_pre=…, photons_pre=…) and pre_axial()'s weight on cos 2πφ (the same in "
        + F_V1SIM + ": pre_post_profiles())")
put("sim_m_fund", pct(_m_fund, 1), _src,
    f"fundamental striation contrast of the simulated before-image: weight {_w2[0]} × m_pre {_g2['m_pre']}")
put("sim_photons_pre", f"{_g2['photons_pre']:,.0f}", _src,
    "mean detected photons per sample of the simulated before-image, with Poisson (shot) noise only")
put("sim_q", num(_m_fund * math.sqrt(_g2["photons_pre"]), 1), _src,
    "q = m·√N of the simulated before-image, as D-46 defines q")
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
kit = LA["kit_2ug_ml_fraction"]
put("lab_kit_range", f"{pct(kit[0], 3)}–{pct(kit[1], 2)}", FL + ": kit_2ug_ml_fraction",
    "the kit's stain over every input range (pan-ExM's range ÷ 10)")
if not (kit[0] < pan[1] / 10 < min(mf.values()) <= kit[1]):
    sys.exit("45-tested.html says the kit's stain probably falls short and only the top of its range reaches the need: "
             "no longer true")

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
