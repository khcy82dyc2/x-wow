#!/usr/bin/env python3
"""Write src/data/numbers_swell.json: every SWELL number on the site, with its source.

Stdlib only:  python tools/numbers_swell.py

Inputs are the SWELL design outputs, copied unchanged into src/data/swell/:
  strain_map_v1.json  whole-gel strain map (synthetic gels S0, S1, S1b, S2)
  optics_v1.json      sampling, Strehl, tiles and SNR for the specified optics
  calc_v0.json        first design calculations (resolution, rulers, SNR)
  budget_v1.json      priced BOM totals per basket
A few numbers exist only in the project's prose notes or in its BOM table (which
is not published because it carries private notes). Those are quoted below with
the exact file and line, and marked how = "quoted". When this script runs inside
the SWELL project repo (one level above the site), it finds each quote again,
records its current line, and fails if a quote has disappeared. In a public
checkout without those notes it keeps the lines recorded in the last output.
"""
import json
import math
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
DATA = SITE / "src" / "data" / "swell"
OUT = SITE / "src" / "data" / "numbers_swell.json"
PROJECT = SITE.parent  # the private SWELL repo, if this checkout sits inside it

MINUS, DASH = "−", "–"
PREV = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
N = {}


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def put(key, value, source, how):
    key = "swell." + key
    if key in N:
        sys.exit(f"duplicate key {key}")
    N[key] = {"value": value, "source": source, "how": how}


def num(x, d):
    s = f"{x:.{d}f}"
    if float(s) == 0:
        s = f"{0:.{d}f}"  # never print -0.00
    return s.replace("-", MINUS)


def pct(x, d=2, plus=False):
    s = num(x * 100, d)
    if plus and not s.startswith(MINUS) and float(s) != 0:
        s = "+" + s
    return s + "%"


def gbp(x):
    return f"£{round(x):,}"


def gbp_range(lo, hi):
    return gbp(lo) if round(lo) == round(hi) else f"{gbp(lo)}{DASH}{gbp(hi)}"


SM = load("strain_map_v1.json")
OP = load("optics_v1.json")
CA = load("calc_v0.json")
BU = load("budget_v1.json")
F_SM = "src/data/swell/strain_map_v1.json"
F_OP = "src/data/swell/optics_v1.json"
F_CA = "src/data/swell/calc_v0.json"
F_BU = "src/data/swell/budget_v1.json"
sc = SM["scenarios"]
blind = sc["S1b"]["metrics"]
blind_s = sc["S1b"]["scenario"]

# ---------------------------------------------------------------- what it is
p = CA["params"]
put("e_a", f"{num(min(p['e_4x']), 0)}{DASH}{num(max(p['e_4x']), 1)}×", F_CA + ": params.e_4x",
    "min–max of the Track A expansion factors the design is computed for")
put("e_b", f"{num(p['e_10x'], 0)}×", F_CA + ": params.e_10x", "Track B expansion factor")
put("e_sim", f"{num(SM['constants']['E0'], 1)}×", F_SM + ": constants.E0", "expansion factor of the synthetic gels")
put("sl_breast", f"{num(p['sl_breast_mean'], 2)} µm", F_CA + ": params.sl_breast_mean",
    "mean sarcomere length assumed for supermarket breast (fact F-10, cited: read from an abstract by an AI)")
put("myofibril_d", f"{num(p['myofibril_thickness'][0], 0)}{DASH}{num(p['myofibril_thickness'][1], 0)} µm",
    F_CA + ": params.myofibril_thickness", "myofibril thickness range used in the design")
a45 = OP["scan"]["A_E4.5"]
put("punch_a", f"{num(a45['punch_mm'], 1)} mm", F_OP + ": scan.A_E4.5.punch_mm", "punch diameter, Track A")
put("expanded_a", f"{num(a45['expanded_diam_mm'], 2)} mm", F_OP + ": scan.A_E4.5.expanded_diam_mm",
    "punch × E 4.5")
put("n_fibrils", f"{blind['n_fibrils']:,}", F_SM + ": scenarios.S1b.metrics.n_fibrils",
    "myofibrils in each synthetic gel")

# ---------------------------------------------------------------- why it works
lam = p["lam_em"]
for t, na_key, e_key in (("a", "na_4x", "4x"), ("b", "na_10x", "10x")):
    na = p[na_key]
    lens = 0.61 * lam / na * 1000  # Rayleigh, nm (kit/03: 0.61·λ/NA)
    exp_ = CA["resolution"][e_key]["rayleigh_nm"]
    put(f"na_{t}", num(na, 2), F_CA + f": params.{na_key}", "objective numerical aperture")
    put(f"res_lens_{t}", f"{round(lens)} nm", F_CA + f": params.lam_em, params.{na_key}",
        "Rayleigh 0.61·λ/NA of the lens alone, λ = emission wavelength")
    put(f"res_exp_{t}", f"{round(exp_)} nm", F_CA + f": resolution.{e_key}.rayleigh_nm",
        "Rayleigh ÷ E, in original-specimen units")
    put(f"res_e_{t}", f"{num(lens / exp_, 1).rstrip('0').rstrip('.')}×", F_CA + f": resolution.{e_key}",
        "lens-alone Rayleigh ÷ expanded Rayleigh = the E used in the calculation")
put("lam_em", f"{round(lam * 1000)} nm", F_CA + ": params.lam_em", "emission wavelength used")
put("aband_usable_a", pct(CA["rulers"]["4x"]["fraction_usable_normal_breast"], 0),
    F_CA + ": rulers.4x.fraction_usable_normal_breast", "sarcomeres long enough for the A-band ruler at 4×")
rowA = next(r for r in OP["sampling"]["A"]["rows"] if r["d_mm"] == 25.0)
rowB = next(r for r in OP["sampling"]["B"]["rows"] if r["d_mm"] == 25.0)
put("tube_f", f"{num(OP['parts']['tube_lens']['f_mm'], 0)} mm", F_OP + ": parts.tube_lens.f_mm", "tube-lens focal length")
put("tube_d", f"{num(rowA['d_mm'], 0)} mm", F_OP + ": sampling.A.rows[d_mm=25]",
    "lens distance behind the objective shoulder chosen in D-29")
put("mag_a", f"{num(rowA['M'], 1)}×", F_OP + ": sampling.A.rows[d_mm=25].M", "total magnification, Track A")
put("px_a", f"{num(rowA['px_um'], 3)} µm", F_OP + ": sampling.A.rows[d_mm=25].px_um", "pixel size at the sample")
put("nyq_px_a", f"{num(OP['sampling']['A']['nyquist_px_um'], 3)} µm", F_OP + ": sampling.A.nyquist_px_um",
    "Nyquist pixel for NA 0.65")
put("nyq_a", f"{num(rowA['nyquist_ratio'], 2)}×", F_OP + ": sampling.A.rows[d_mm=25].nyquist_ratio",
    "sampling ÷ Nyquist (pass band 0.8–1.25)")
put("mag_b", f"{num(rowB['M'], 1)}×", F_OP + ": sampling.B.rows[d_mm=25].M", "total magnification, Track B")
put("nyq_b", f"{num(rowB['nyquist_ratio'], 2)}×", F_OP + ": sampling.B.rows[d_mm=25].nyquist_ratio",
    "sampling ÷ Nyquist (pass band 0.8–1.25)")
cam = OP["parts"]["camera"]
put("cam_format", f"{cam['w']} × {cam['h']} px, {num(cam['px_um'], 2)} µm", F_OP + ": parts.camera",
    "sensor format of the mono IMX296")

# ---------------------------------------------------------------- the numbers
pr = CA["period_ratio_rel_error"]
at10 = [v["10"] for v in pr.values()]
put("first_est", f"{num(min(at10) * 100, 2)}{DASH}{num(max(at10) * 100, 2)}%",
    F_CA + ": period_ratio_rel_error[*]['10']",
    "min–max over the three assumed pre-image contrast cases, 10 sarcomeres, perfectly periodic sarcomeres")
put("first_est_n", "10", F_CA + ": period_ratio_rel_error[*]['10']", "segment length in sarcomeres")
rms = {k: v["metrics"]["per_fibril_Eax_rms"] for k, v in sc.items()}
put("ladder_final", f"{num(min(rms.values()) * 100, 2)}{DASH}{num(max(rms.values()) * 100, 2)}%",
    F_SM + ": scenarios[*].metrics.per_fibril_Eax_rms", "min–max over the four gels of the final run")
put("ladder_blind", pct(blind["per_fibril_Eax_rms"]), F_SM + ": scenarios.S1b.metrics.per_fibril_Eax_rms",
    "per-myofibril RMS error of the axial factor, blind gel")
out2 = max(v["metrics"]["per_fibril_Eax_outliers_2pct"] for v in sc.values())
put("ladder_outliers_final", pct(out2), F_SM + ": scenarios[*].metrics.per_fibril_Eax_outliers_2pct",
    "worst share of myofibrils beyond ±2% over the four gels of the final run")
put("blind_mean_err", pct(blind["gel_mean_E_err"]), F_SM + ": scenarios.S1b.metrics.gel_mean_E_err",
    "gel-mean expansion error vs truth")
put("blind_map_rms", pct(blind["map_rms_vs_truth"]), F_SM + ": scenarios.S1b.metrics.map_rms_vs_truth",
    "local E map RMS error vs truth, same kernel")
put("blind_false", pct(blind["false_flag_rate"]), F_SM + ": scenarios.S1b.metrics.false_flag_rate",
    "share of defect-free gel area flagged")
put("blind_dist_dev", pct(blind["distortion_curve_max_dev"], 3),
    F_SM + ": scenarios.S1b.metrics.distortion_curve_max_dev", "worst deviation of the distortion curve from truth")
put("blind_hotspot", pct(-blind_s["hotspot"], 0), F_SM + ": scenarios.S1b.scenario.hotspot", "planted under-expanded hotspot")
put("blind_undig", pct(-blind_s["undig"], 0), F_SM + ": scenarios.S1b.scenario.undig", "planted under-digested patch")
put("blind_stretch", pct(blind_s["band"], 1, plus=True), F_SM + ": scenarios.S1b.scenario.band", "planted stretched patch")
put("blind_tear", f"{num(blind_s['tear_open'], 1)} µm", F_SM + ": scenarios.S1b.scenario.tear_open", "planted tear opening")
det, anyd = blind["detection"], blind["detection_any_flag"]
put("blind_hotspot_own", pct(det["hotspot"], 0), F_SM + ": scenarios.S1b.metrics.detection.hotspot",
    "area flagged by its own detector")
put("blind_undig_own", pct(det["under-digested patch"], 0),
    F_SM + ": scenarios.S1b.metrics.detection['under-digested patch']", "area flagged by its own detector")
put("blind_stretch_own", pct(det["stretched patch"], 0), F_SM + ": scenarios.S1b.metrics.detection['stretched patch']",
    "area flagged by its own (stretch) detector")
put("blind_stretch_any", pct(anyd["stretched patch"], 0),
    F_SM + ": scenarios.S1b.metrics.detection_any_flag['stretched patch']", "area flagged by any detector")
s1 = sc["S1"]
put("dev_tear", f"{num(s1['scenario']['tear_open'], 0)} µm", F_SM + ": scenarios.S1.scenario.tear_open",
    "planted tear opening on development gel S1")
put("dev_tear_own", pct(s1["metrics"]["detection"]["tear"], 0), F_SM + ": scenarios.S1.metrics.detection.tear",
    "area of the S1 tear flagged")
nb, nd = blind["n_period"], sc["S0"]["metrics"]["n_period"]
put("coverage_blind_n", f"{nb:,}", F_SM + ": scenarios.S1b.metrics.n_period",
    "myofibrils long enough for the axial ruler, blind gel")
put("coverage_blind_pct", pct(nb / blind["n_fibrils"], 0), F_SM + ": scenarios.S1b.metrics.n_period / n_fibrils",
    "share of myofibrils long enough for the axial ruler, blind gel")
put("coverage_dev_n", f"{nd:,}", F_SM + ": scenarios.S0.metrics.n_period", "same, development gels (seed 7)")
put("coverage_dev_pct", pct(nd / sc["S0"]["metrics"]["n_fibrils"], 0), F_SM + ": scenarios.S0.metrics.n_period / n_fibrils",
    "same share, development gels (seed 7)")
s2 = sc["S2"]
an, ori = s2["metrics"]["anisotropy"], s2["metrics"]["orientation"]
put("aniso_est", f"{pct(an['est'])} [{pct(an['ci'][0])}, {pct(an['ci'][1])}]",
    F_SM + ": scenarios.S2.metrics.anisotropy", "estimate [95% CI], development gel S2")
put("aniso_truth", pct(an["truth"]), F_SM + ": scenarios.S2.metrics.anisotropy.truth", "true value in S2")
put("orient_amp", pct(ori["amplitude"]), F_SM + ": scenarios.S2.metrics.orientation.amplitude",
    "gel-stretch amplitude found by the orientation test")
put("orient_axis", f"{round(ori['axis_deg'])}°", F_SM + ": scenarios.S2.metrics.orientation.axis_deg",
    "gel-stretch axis found by the orientation test")
put("orient_truth_amp", pct(s2["scenario"]["gel_stretch"]), F_SM + ": scenarios.S2.scenario.gel_stretch",
    "planted gel stretch")
put("orient_truth_axis", f"{round(math.degrees(s2['scenario']['gel_psi']))}°", F_SM + ": scenarios.S2.scenario.gel_psi",
    "planted stretch axis (radians → degrees)")
put("etr_blind", f"{pct(blind['per_fibril_Etr_bias'])} ± {pct(blind['per_fibril_Etr_sd'])}",
    F_SM + ": scenarios.S1b.metrics.per_fibril_Etr_bias, per_fibril_Etr_sd",
    "transverse factor per myofibril: bias ± SD, blind gel")
w = SM["width_mc"]
put("tr_boxy_dpc", pct(w["dpc | boxy section (n = 4) assumed elliptical"]["bias"], 1),
    F_SM + ": width_mc['dpc | boxy section (n = 4) assumed elliptical']", "bias, oblique/DPC before-image")
put("tr_boxy_pol", pct(w["pol | boxy section (n = 4) assumed elliptical"]["bias"], 1),
    F_SM + ": width_mc['pol | boxy section (n = 4) assumed elliptical']", "bias, crossed-polariser before-image")
post = [abs(w[k]["bias"]) for k in w if "from post" in k or "shape from post" in k]
put("tr_shape_post", "≤ " + pct(max(post)), F_SM + ": width_mc['* | … shape from post …']",
    "worst |bias| when each cross-section's shape is measured from the post z-projection")
psf5 = [w[k]["bias"] for k in w if "PSF calibrated 5%" in k]
put("tr_psf5", f"{num(min(psf5) * 100, 2)}{DASH}{num(max(psf5) * 100, 2)}%", F_SM + ": width_mc['* | PSF calibrated 5% wide']",
    "bias when the pre-image blur is calibrated 5% wide")
g1 = max(w[k]["bias"] for k in w if "PSF calibrated 2%" in k)
put("tr_worst_g1", pct(g1), F_SM + ": width_mc['* | PSF calibrated 2% wide (G1 target)']",
    "worst transverse bias at the G1 calibration target")
put("tr_gate_used", pct(0.01 + g1), F_SM + ": width_mc + D-32", "1% + worst bias at the G1 target (D-32)")

st = OP["strehl"]
put("strehl_a_all", num(min(r["strehl"] for r in st["A"]), 2), F_OP + ": strehl.A[*].strehl", "minimum over all depths")
put("strehl_depth_a", f"{num(min(r['depth_um'] for r in st['A']), 0)}{DASH}{num(max(r['depth_um'] for r in st['A']), 0)} µm",
    F_OP + ": strehl.A[*].depth_um", "depth range simulated into water, Track A")
put("strehl_a", num(OP["strehl_min"]["A_0_to_9um"], 2), F_OP + ": strehl_min.A_0_to_9um", "worst Strehl over the specimen depth, Track A")
put("strehl_b", num(OP["strehl_min"]["B_0_to_20um"], 2), F_OP + ": strehl_min.B_0_to_20um", "worst Strehl over the specimen depth, Track B")
put("fwhm_a", f"{num(st['A'][0]['fwhm_lat_um'], 3)} µm", F_OP + ": strehl.A[0].fwhm_lat_um", "lateral PSF FWHM, Track A")
put("tiles_a", f"{a45['tiles_per_plane']:,}", F_OP + ": scan.A_E4.5.tiles_per_plane", "tiles per plane, E 4.5 gel")
put("zplanes_a", str(a45["z_planes"]), F_OP + ": scan.A_E4.5.z_planes", "z-planes per tile")
put("gb_a", f"{num(a45['raw_GB'], 1)} GB", F_OP + ": scan.A_E4.5.raw_GB", "raw data per gel")
h = sorted(a45["hours_fast_slow"])
put("hours_a", f"{num(h[0], 1)}{DASH}{num(h[1], 1)} h", F_OP + ": scan.A_E4.5.hours_fast_slow", "scan time, fast–slow motors")
worst = next(r for r in OP["snr_pedestal"] if r["f_lab"] == 0.005 and r["myofibril_um"] == 2.0)
put("snr_worst", f"{num(worst['snr_no_pedestal'], 1)} → {num(worst['snr_with_pedestal'], 1)}",
    F_OP + ": snr_pedestal[f_lab=0.005, myofibril_um=2]", "SNR without → with the out-of-focus pedestal")
put("dose_worst", f"{num(worst['dose_factor_for_snr10'], 1)}×", F_OP + ": snr_pedestal[f_lab=0.005, myofibril_um=2]",
    "dose (exposure × irradiance) needed for SNR 10")
put("lab_worst", pct(worst["f_lab"], 1), F_OP + ": snr_pedestal[*].f_lab", "lowest labelled-amine fraction simulated")
put("fib_worst", f"{num(worst['myofibril_um'], 0)} µm", F_OP + ": snr_pedestal[*].myofibril_um", "thickest myofibril simulated")
put("snr_target", "10", F_OP + ": checks[6].check", "SNR threshold named in the check")
snr = [r["snr_cheap"] for r in CA["snr_first_pass"]["rows"]]
put("snr_first", f"{round(min(snr))}{DASH}{round(max(snr))}", F_CA + ": snr_first_pass.rows[*].snr_cheap",
    "first-pass SNR range at 4× before the pedestal was modelled")

# ---------------------------------------------------------------- money
# D-78 (2026-10-11): a total is the sum of the listed lines only, a floor written "≥ £X" with how many lines it covers;
# an unpriced line shows no number; no target comparison or ratio is drawn until every line in a total is listed.
core, build, tg = BU["core"], BU["build"], BU["targets_D15"]


def floor(t):   # rounded down: a floor rounded up would overstate it
    return f"≥ £{math.floor(t['listed'] + 1e-9):,}" if t["n_listed"] else "—"


put("core_floor", floor(core), F_BU + ": core.listed", "sum of the listed lines only (a floor), GBP incl. VAT")
put("core_target", "≤ " + gbp(tg["core"]), F_BU + ": targets_D15.core", "cost target D-15")
put("core_n_priced", str(core["n_listed"]), F_BU + ": core.n_listed", "lines priced from supplier pages")
put("core_n_est", str(core["n_estimate"]), F_BU + ": core.n_estimate", "lines whose price is not yet read")
put("core_n", str(core["n"]), F_BU + ": core.n", "lines in the imager core")
put("build_floor", floor(build), F_BU + ": build.listed", "sum of the listed lines only (a floor), GBP incl. VAT")
put("build_target", "≤ " + gbp(tg["build"]), F_BU + ": targets_D15.build", "cost target D-15")
put("ceiling", gbp(tg["ceiling"]), F_BU + ": targets_D15.ceiling", "hard ceiling D-15")
put("build_n_priced", str(build["n_listed"]), F_BU + ": build.n_listed", "lines priced from supplier pages")
put("build_n_est", str(build["n_estimate"]), F_BU + ": build.n_estimate", "lines whose price is not yet read")
put("build_n", str(build["n"]), F_BU + ": build.n", "lines in the full build")
for b in ("C", "T", "O", "W"):
    bb = BU["baskets"][b]
    put(f"basket_{b.lower()}", floor(bb), F_BU + f": baskets.{b}.listed", "sum of the listed lines only (a floor)")
    put(f"basket_{b.lower()}_n_est", str(bb["n_estimate"]), F_BU + f": baskets.{b}.n_estimate", "lines whose price is not yet read")
    put(f"basket_{b.lower()}_n", str(bb["n"]), F_BU + f": baskets.{b}.n", "lines in the basket")
pe = BU["project_excl_tools"]
put("project_floor", floor(pe), F_BU + ": project_excl_tools.listed", "all baskets except tools, listed lines only (a floor)")
put("project_n_est", str(pe["n_estimate"]), F_BU + ": project_excl_tools.n_estimate", "lines whose price is not yet read, all baskets except tools")
put("project_n", str(pe["n"]), F_BU + ": project_excl_tools.n", "lines, all baskets except tools")
put("fx", f"EUR {BU['fx']['EUR']}, USD {BU['fx']['USD']}", F_BU + ": fx", "assumed exchange rates to GBP")

# ---------------------------------------------------------------- price dates (life 8)
# From the public BOM CSV (src/downloads/swell-bom-<date>.csv, the same bytes as the download's pm/BOM.csv):
# the first and last dates in its date_checked column.
import csv  # noqa: E402
_boms = sorted((SITE / "src" / "downloads").glob("swell-bom-*.csv"))
if len(_boms) != 1:
    sys.exit(f"expected one swell-bom-*.csv in src/downloads, found {[b.name for b in _boms]}")
_rows = csv.DictReader(ln for ln in _boms[0].open(encoding="utf-8-sig") if not ln.startswith("#"))
_dates = sorted({r["date_checked"] for r in _rows if r["date_checked"]})
_src = f"src/downloads/{_boms[0].name}: column date_checked"
put("price_date", _dates[0], _src, "the first date a BOM line was checked")
put("price_date_last", _dates[-1], _src, "the last date a BOM line was checked")

# ---------------------------------------------------------------- every box line's price (life 12)
# From the same public CSV, converted as software/sim/budget.py converts (the FX in budget_v1.json; 20% VAT added where
# vat_incl is "no"); since D-78 every line's price comes from here, and an unpriced line shows "—". A single price keeps
# its pence, as docs/BOM.md shows it; a range is in whole pounds.
_fx = BU["fx"]


def _line_gbp(r, col):
    x = float(r[col]) * _fx[r["currency"]] * float(r["qty"])
    return x if r["vat_incl"] == "yes" else x * 1.2


for _r in csv.DictReader(ln for ln in _boms[0].open(encoding="utf-8-sig") if not ln.startswith("#")):
    _key = "line_" + _r["line_id"].lower().replace("-", "")
    if _r["box"] not in ("core", "build") or "swell." + _key in N:
        continue
    if _r["price_basis"] != "listed":   # D-78: an unpriced line shows no number
        put(_key, "—", f"src/downloads/{_boms[0].name}: line {_r['line_id']}", "price not yet read (D-78)")
        continue
    _lo, _hi = _line_gbp(_r, "unit_low"), _line_gbp(_r, "unit_high")
    _v = (f"£{_lo:,.2f}" if abs(_lo - round(_lo)) > 0.004 else gbp(_lo)) if abs(_lo - _hi) < 0.005 else gbp_range(_lo, _hi)
    put(_key, _v, f"src/downloads/{_boms[0].name}: line {_r['line_id']}", _r["price_basis"])

# ---------------------------------------------------------------- quoted (prose only)
Q = [
    # key, value, file, line, needle that must appear on that line
    ("checks_pass", "31", "docs/design/strain_map_v1.md", 5, "31 of 33 pass"),
    ("checks_total", "33", "docs/design/strain_map_v1.md", 5, "31 of 33 pass"),
    ("checks_fail", "1", "docs/design/strain_map_v1.md", 5, "1 fail"),
    ("checks_below", "1", "docs/design/strain_map_v1.md", 5, "1 below the detection limit"),
    ("first_run_fail", "15", "docs/design/strain_map_v1.md", 11, "the first run failed 15 checks"),
    ("jitter", "3%", "docs/design/strain_map_v1.md", 7, "3% sarcomere-to-sarcomere jitter"),
    ("detect_threshold", "80%", "docs/design/strain_map_v1.md", 35, "flagged over ≥ 80% of its area"),
    ("min_sarc", "8", "docs/design/strain_map_v1.md", 5, "≥ 8 sarcomeres"),
    ("seg_range", "8–20", "docs/design/strain_map_v1.md", 16, "segments of 8–20 sarcomeres"),
    ("ladder_d33", "0.3–0.6%", "pm/DECISIONS.md", 23, "0.3–0.6% RMS per myofibril"),
    ("ladder_outliers_d33", "≤ 0.8%", "pm/DECISIONS.md", 23, "≤ 0.8% of myofibrils beyond ±2%"),
    ("sidelobe_frac", "10–17%", "pm/DECISIONS.md", 23, "10–17% of myofibrils off by 7–19%"),
    ("sidelobe_err", "7–19%", "pm/DECISIONS.md", 23, "off by 7–19%"),
    ("contrast_range", "5–50%", "pm/DECISIONS.md", 116, "assumed contrast of 5–50%"),
    ("tear_limit", "~2 µm", "pm/DECISIONS.md", 14, "limit (~2 µm)"),
    ("tr_gate", "±3%", "pm/DECISIONS.md", 32, "within ±3% (95% CI, n ≥ 200)"),
    ("tr_n", "200", "pm/DECISIONS.md", 32, "n ≥ 200"),
    ("psf_cal", "±2%", "pm/DECISIONS.md", 36, "G1 calibrates to ±2%"),
    ("ofm_stock_nyq", "0.66×", "docs/design/optics_v1.md", 23, "0.66× Nyquist"),
    ("obj_a_eur", "€109", "pm/DECISIONS.md", 61, "€109 ex VAT"),
    ("cam_price", "£49.87", "pm/BOM.csv", 10, "49.87,49.87,GBP"),
    # (the example host-lab shortlist and its prices left the site on 2026-10-10; no page uses them)
    ("v_max", "24 V DC", "pm/INVARIANTS.md", 20, "≤ 24 V DC inside the instrument"),
    ("t_cutoff", "50 °C", "pm/INVARIANTS.md", 10, "rated ≤ 50 °C"),
    ("t_denature", "95 °C", "pm/INVARIANTS.md", 23, "95 °C steps never happen on the stage"),
    # the acrylamide stock as the U-ExM protocol lists it (F-8; kit/10 left the download on 2026-10-10)
    ("aa_stock", "40%", "pm/VERIFIED_FACTS.md", 14, "stocks 40% AA"),
    ("aps_conc", "10% w/v", "pm/DECISIONS.md", 95, "10% w/v in ≥ 1 g batches"),
    ("aps_batch", "1 g", "pm/DECISIONS.md", 95, "10% w/v in ≥ 1 g batches"),
    ("aband_discard", "~87%", "pm/DECISIONS.md", 116, "discards ~87% of data"),
    ("sl_wooden", "1.91 µm", "pm/VERIFIED_FACTS.md", 16, "1.91 µm wooden breast"),
    # (t_fridge, t_freezer, t_incubator came from a private enquiry draft that is never public; removed 2026-10-10)
]
Q += [
    ("tr_base", "1%", "pm/DECISIONS.md", 35, "it is 1% plus the worst transverse bias"),
    ("outlier_band", "±2%", "pm/DECISIONS.md", 23, "beyond ±2%"),
]
put("a_band", f"{num(p['a_band'], 1)} µm", F_CA + ": params.a_band",
    "A-band length assumed for chicken (fact F-17: not verified)")
put("track_a", "4×", F_CA + ": resolution['4x']", "name of the ~4× expansion track (Track A)")
put("track_b", "10×", F_CA + ": resolution['10x']", "name of the ~10× expansion track (Track B)")
put("blind_hotspot_any", pct(anyd["hotspot"], 0), F_SM + ": scenarios.S1b.metrics.detection_any_flag.hotspot",
    "area flagged by any detector")
put("blind_undig_any", pct(anyd["under-digested patch"], 0),
    F_SM + ": scenarios.S1b.metrics.detection_any_flag['under-digested patch']", "area flagged by any detector")
put("psf5_case", "5%", F_SM + ": width_mc key '… PSF calibrated 5% wide'", "simulated pre-image blur calibration error")
put("aniso_planted", pct(abs(s2["scenario"]["ax_aniso"]), 0), F_SM + ": scenarios.S2.scenario.ax_aniso",
    "planted intrinsic axial anisotropy (axial shorter than transverse)")
put("scan_e", f"{num(a45['E'], 1)}×", F_OP + ": scan.A_E4.5.E", "expansion factor of the scan case")
# Stable anchors for quotes from files whose line numbers move (new decisions are added at the top).
ANCHOR = {
    "ladder_d33": "D-33", "ladder_outliers_d33": "D-33", "sidelobe_frac": "D-33", "sidelobe_err": "D-33",
    "outlier_band": "D-33", "contrast_range": "D-4", "aband_discard": "D-4", "tear_limit": "D-34",
    "tr_gate": "D-32", "tr_n": "D-32", "psf_cal": "D-32", "tr_base": "D-32", "obj_a_eur": "D-29",
    "aps_conc": "D-24", "aps_batch": "D-24", "v_max": "INV-5", "t_cutoff": "INV-2", "t_denature": "INV-6", "sl_wooden": "F-10", "aa_stock": "F-8",
    "cam_price": "line H-09",  # the other lines' prices come from the public BOM CSV (life 12)
}
checked = skipped = 0
for key, value, f, line, needle in Q:
    path = PROJECT / f
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
        hits = [i + 1 for i, t in enumerate(lines) if needle in t]
        if f == "pm/DECISIONS.md" and ANCHOR.get(key, "").startswith("D-"):
            # the quote must come from the decision its label names, not from a later entry that repeats it
            owner, cur = {}, None
            for i, t in enumerate(lines, 1):
                m = re.match(r"- \*\*\d{4}-\d{2}-\d{2} · (D-\d+) ·", t)
                cur = m.group(1) if m else (None if t.startswith("#") else cur)
                owner[i] = cur
            hits = [i for i in hits if owner.get(i) == ANCHOR[key]]
        if not hits:
            sys.exit(f"quote for swell.{key} not found in {f} (looked for {needle!r})")
        line = min(hits, key=lambda i: abs(i - line))  # the occurrence nearest the recorded line
        checked += 1
    else:
        skipped += 1  # public checkout: keep the line recorded when this file was last generated
        old = PREV.get("swell." + key, {}).get("source", "")
        m = re.match(re.escape(f) + r":(\d+) ", old)
        line = int(m.group(1)) if m else line
    if key in ANCHOR:  # the ID is what a reader can find in the download's copy; its line numbers differ
        put(key, value, f"{f}, {ANCHOR[key]} (SWELL project notes)", "quoted")
    else:
        put(key, value, f"{f}:{line} (SWELL project notes)", "quoted")


# ---------------------------------------------------------------- self-checks
def recount_checks():
    """Recount the strain-map pass/fail table from the JSON metrics, using the thresholds in its labels."""
    r = []
    for s in sc.values():
        m = s["metrics"]
        r += [abs(m["gel_mean_E_err"]) <= 0.005, m["per_fibril_Eax_rms"] <= 0.01, m["map_rms_vs_truth"] <= 0.01,
              m["distortion_curve_max_dev"] <= 0.005, m["false_flag_rate"] <= 0.05]
        r += ["below" if v is None else v >= 0.80 for v in m["detection"].values()]
    a, o = s2["metrics"]["anisotropy"], s2["metrics"]["orientation"]
    r += [a["n"] >= 200 and (a["ci"][0] > 0 or a["ci"][1] < 0), abs(a["est"] - a["truth"]) <= 0.005, o["p"] < 0.05]
    r += [max(abs(w[k]["bias"]) for k in w if "boxy" in k and "post" in k) <= 0.01, 0.01 + g1 <= 0.03]
    return r.count(True), r.count(False), r.count("below"), len(r)


ok, bad, below, total = recount_checks()
assert (str(ok), str(total)) == (N["swell.checks_pass"]["value"], N["swell.checks_total"]["value"]), (ok, total)
assert str(bad) == N["swell.checks_fail"]["value"] and str(below) == N["swell.checks_below"]["value"]
for k in ("checks_pass", "checks_total", "checks_fail", "checks_below"):
    N["swell." + k]["how"] = "quoted; recounted from strain_map_v1.json metrics with the thresholds in the check labels: agrees"
# The first estimate quoted in D-4 must match what calc_v0.json gives.
assert N["swell.first_est"]["value"] == "0.21–0.35%", N["swell.first_est"]["value"]

OUT.write_text(json.dumps(dict(sorted(N.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"wrote {OUT.relative_to(SITE)}: {len(N)} numbers; quotes checked against project notes: {checked}, "
      f"skipped (notes not present): {skipped}; strain-map recount {ok}/{bad}/{below} of {total} agrees")
