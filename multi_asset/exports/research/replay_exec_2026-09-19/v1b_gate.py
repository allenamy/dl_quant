#!/usr/bin/env python3
"""replay_exec 2026-09-19 · V1b gate v2 (revision after independent review 5b R5B-01 / R5B-02 / R5B-03 of v1 = sha 31650235, archived as
archive/v1b_gate_31650235.py). Written and committed BEFORE any judgement under it. V1 (v1_gate.py, unchanged) stays the
CALIBRATION-PERIOD RECONCILIATION of v1/v2 — never "validation".

WHAT V1b VALIDATES: the CONDITIONAL MEAN of each 4h window's price-and-trading / funding / fee / turnover (the per-window mean over R
seeded simulator paths) against the one live path. It does NOT validate path risk — variance, halt / stop incidence, tails, maxDD. Those
are reported as diagnostics from the per-seed path artifacts (plus the Monte Carlo standard error of every window item). R >= 32 paths is
a minimum amount of computation, not a precision guarantee.

VERDICTS (stable names, never a crash; exit code in brackets):
  PASS [0]           every item passes
  FAIL [1]           a judged item fails (named in the item list)
  INVALID_INPUT [2]  E0 fails: a numeric input is non-finite (NaN / ±Inf at any position), or the time axis is not strictly increasing,
                     or a window has non-positive length — nothing else is judged
  UNAVAILABLE [3]    the live side is not a closed cash identity on every judged window (LIVE_G cash_ok), or
                     the receipt cannot be verified (R5B-01): any approved file differs from its pinned sha; the receipt's claimed shas
                     differ from the files; a knob is missing or on; the sealed initial-state artifact is missing, does not re-hash to
                     the claimed sha, or does not equal the executor's own readback / NAV at t0 recomputed from the manifest-verified
                     mirror; a seed has no path artifact, an artifact does not re-hash, names another seed / simulator / calibration /
                     initial state, or the receipt's window means differ from the means recomputed here from the artifacts; the
                     calibration file is not reproduced byte-for-byte in params / estimands by re-running the pinned calibrator on the
                     manifest-verified mirror inside its declared anchor population and stop boundary. Every judged number comes from
                     the recomputation, never from the receipt's own summary.

PERIODS (the population = every LIVE_G window whose start anchor lies in [first, last]; no gross0 filter, no dropped windows; the
first window of each run is warm-up because in-flight orders at the t0 readback are not simulated):
  CAL                      anchors 08-26 04Z .. 09-10 20Z — calibration period, IN-SAMPLE (continuous run from the 08-26 00Z readback)
  HIST_DIAG                anchors 09-11 00Z .. 09-18 20Z — HISTORY DIAGNOSTIC AFTER TIME-TRUNCATED REFIT (not independent validation:
                           the week was seen during v1/v2 calibration and diagnosis); run restarted from the 09-10 20Z readback
  HIST_DIAG_CONTINUOUS     the same windows from the continuous CAL run (state drift included) — diagnostic
  FORWARD                  the pre-registered forward validation: the first FORWARD_N_WINDOWS = 42 complete live windows whose start
                           anchor is >= --forward-first-anchor (fixed in the pre-registration document, after the freeze commit); fewer
                           than 42 existing ⇒ UNAVAILABLE (no readout before the anchors exist). Inputs: a NEW mirror + manifest, live-
                           window file and transfer file passed on the command line; simulator, calibrator and calibration stay pinned
                           below, the calibration re-derivation uses the ORIGINAL mirror (--calib-mirror, manifest pinned below).

ITEMS (after E0):
  E1 population   sim window count == live count; live windows contiguous (|t1_k − t0_{k+1}| <= 1 s) and exactly the declared population
  E2 t0 / E3 t1   max_w |t_sim − t_live| <= T_ALIGN_S = 1 s. ONE time contract: once E1–E3 pass, every pair is judged on the LIVE time
                  axis (the T items are computed here, not through v1_gate.judge's 1e-6 assert, so a permitted 0.5 s offset cannot crash)
  W  per window, c in {price_and_trading, funding, fee, turnover}: e_w = sim_w − live_w, s_c = mean_w |live_w|; reported mean / p90 / max
     |e|; tol_w = rtol·|live_w| + k_atol·s_c; PASS iff mean|e|/s_c <= m_max AND p90_w(|e_w|/tol_w) <= 1 AND max_w(|e_w|/tol_w) <= t_max.
     ZERO CASES: s_c = 0 and every e_w = 0 ⇒ PASS ("exact zero/zero"); s_c = 0 and some e_w ≠ 0 ⇒ FAIL ("zero live scale, nonzero sim").
         c                   rtol   k_atol   m_max   t_max
         price_and_trading   0.25   0.25     0.35    3.0
         funding             0.25   0.10     0.25    3.0
         fee                 0.25   0.10     0.25    3.0
         turnover            0.25   0.10     0.25    3.0
     These are pre-declared ENGINEERING tolerances (set after the v2 in-sample correlation 0.988 was known), not a statistical
     equivalence test, and no guarantee for other regimes.
  T  the four V1 totals with V1's formulas (fee / funding ratio, turnover-over-gross ratio in [0.8, 1.25]; price total within
     max(|Σ live|, 0.5 bps × Σ live gross0) and the UTC-day block-bootstrap CI (B 20000, seed 20260919) containing 0). ZERO CASES: 0/0
     ⇒ PASS ("exact zero/zero"); x/0 with x ≠ 0 ⇒ FAIL ("zero live, nonzero sim"). Evaluated only when E1–E3 pass.
usage: v1b_gate.py <SIM.json> <CAL|HIST_DIAG|HIST_DIAG_CONTINUOUS|FORWARD> <out.json> [--mirror D] [--manifest M] [--live-g F]
                   [--transfers F] [--forward-first-anchor A] [--calib-mirror D]
       v1b_gate.py --selftest [mirror]
"""
import collections, contextlib, copy, io, json, math, os, sys, tempfile, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simlib as L
import v1_gate as V1

GATE_VERSION = "v2"
H4 = 14400
PERIODS = {
    "CAL": {"first_anchor": 1787716800, "last_anchor": 1789070400, "run_start_anchor": 1787702400, "sim_label": "CAL",
            "role": "calibration period, IN-SAMPLE for the pooled v3 parameters"},
    "HIST_DIAG": {"first_anchor": 1789084800, "last_anchor": 1789761600, "run_start_anchor": 1789070400, "sim_label": "HIST_DIAG",
                  "role": "history diagnostic after time-truncated refit (not independent validation: the week was seen during v1/v2 calibration and diagnosis)"},
    "HIST_DIAG_CONTINUOUS": {"first_anchor": 1789084800, "last_anchor": 1789761600, "run_start_anchor": 1787702400, "sim_label": "CAL",
                             "role": "diagnostic: the history-diagnostic windows taken from the continuous CAL run"},
    "FORWARD": {"first_anchor": None, "last_anchor": None, "run_start_anchor": None, "sim_label": "FORWARD",
                "role": "pre-registered forward validation (live anchors after the freeze commit)"},
}
FORWARD_N_WINDOWS = 42
CALIB_ANCHORS = (1787702400, 1789070400)      # the v3 pooled calibration uses anchors 08-26 00Z .. 09-10 20Z only
R_MIN = 32
T_ALIGN_S = 1.0
BOUNDS = {
    "price_and_trading": {"rtol": 0.25, "k_atol": 0.25, "m_max": 0.35, "t_max": 3.0},
    "funding": {"rtol": 0.25, "k_atol": 0.10, "m_max": 0.25, "t_max": 3.0},
    "fee": {"rtol": 0.25, "k_atol": 0.10, "m_max": 0.25, "t_max": 3.0},
    "turnover": {"rtol": 0.25, "k_atol": 0.10, "m_max": 0.25, "t_max": 3.0},
}
FIELD = {"price_and_trading": "price_trade", "funding": "funding", "fee": "fee", "turnover": "turnover"}
EXIT = {"PASS": 0, "FAIL": 1, "INVALID_INPUT": 2, "UNAVAILABLE": 3}

# ── APPROVED TABLE (R5B-01): the simulator, calibrator, calibration and every dependency, pinned by sha256 ──
_VR = os.path.join("docs", "fixprogram_2026-09-13", "FP3_receipts", "venue_readonly_2026-09-19")
APPROVED = {
    "exec_sim.py": (os.path.join(HERE, "exec_sim.py"), "29679672e68d4842a62616e40c5fc57143f724b9ebfa6bbde927670624247c24"),
    "simlib.py": (os.path.join(HERE, "simlib.py"), "55246fe98da2d57a33bbbe0f22fc67e6581da539c353b026d8ef41673dfec2f1"),
    "calib_v3.py": (os.path.join(HERE, "calib_v3.py"), "14357bbadd6076fed5f31b9d9fe5095c41c5f3b37a40c7624501f88102d05e96"),
    "calibration": (os.path.join(HERE, "CALIBRATION_v3_POOLED_20260826_20260910.json"), "fda342431d39703e8a2cc49d566f0cdd89155248c1f7bd46a6e46b3ffbc937e6"),
    "v1_gate.py": (os.path.join(HERE, "v1_gate.py"), "c97d9b3d49212b49ea2cde883d7a06fe749f43ed23f3aef7de6345a4d8075d0d"),
    "fills_reader.py": (os.path.join(L.TOOLS, "fills_reader.py"), "4a906fba23dbeb3f147af4b2e7713c139fd379464b91f22fbede5301c2e7ff48"),
    "MISSING_TRADES": (L.MISSING_TRADES, "6faee16057e9def54947c11ca1ca20ee3ff2075d8a680f9fcd45ef4713827629"),
    "BNB_INDEX": (L.BNB_INDEX, "c7e2c147e434a82045ae479ca414335b45b8b5b4a5ed02838e938bb151cd2149"),
    "FLATTEN-20260821T201600Z": (L.FLATTEN_RAW[0], "7ef07956f9f1112c095c3721dcaf0d7f5b310a724cff7d11a20620f8884b6156"),
    "FLATTEN-20260826T124702Z": (L.FLATTEN_RAW[1], "ebda127010c3708f5b4f9c9ca71a6f292ed5a4deb744a2bc1163b794e52f8941"),
    "FLATTEN-20260906T084608Z": (L.FLATTEN_RAW[2], "88b86525b1cd3ececbb6b035fed5ec3d5a24effb2ca703003cca813472ec1da8"),
    "FLATTEN-20260909T164536Z": (L.FLATTEN_RAW[3], "3a218bc856ab86709366b65b4180ea76021a9e63dab973684cbd36cf66c3dc3f"),
    "FLATTEN-20260912T124737Z": (L.FLATTEN_RAW[4], "4b25e0f2bd7c327bc7ab1f5f75865d58a29003518d334fc3d0e82018967febcd"),
}
# historical inputs (CAL / HIST_DIAG*); FORWARD brings its own, recorded in its receipt; the calibration re-derivation always uses these
APPROVED_HISTORICAL = {
    "manifest": (os.path.join(HERE, "INPUT_MANIFEST.json"), "59875e5a69db415f5ce20b35b888f2d49a31427fdde8b7b847a9645ee135a5ae"),
    "live_g": (L.LIVE_G, "ddb4e09225e33336a52cea3e6928ff04aeb3102547d3a3f5d8f7573f5a9f4360"),
    "transfers": (L.INCOME_TRANSFER, "9a85c9140c1831e96d7dec5aafe6d959a1c8a11ace01028ef5e9f686e3efb352"),
}
SIM_VERSION = "v3.1"
_CALIB_CACHE = {}


def self_sha():
    return L.sha_file(os.path.abspath(__file__))


def live_windows_from(path):
    W = json.load(open(path))["windows"]
    out = []
    for i, w in enumerate(W):
        if i + 1 < len(W) and W[i + 1]["from"] == w["to"]:
            t1 = float(W[i + 1]["t0"])
        else:
            t1 = time.mktime(time.strptime("2026-" + w["to"], "%Y-%m-%d %H:%M:%SZ")) - time.timezone
        out.append(dict(w, t1=t1, idx=i))
    return out


def forward_population(windows, first_anchor):
    """the first FORWARD_N_WINDOWS live windows whose start anchor >= first_anchor, or None if fewer exist yet"""
    w = [x for x in windows if L.nominal(x["t0"]) >= first_anchor][:FORWARD_N_WINDOWS]
    return w if len(w) == FORWARD_N_WINDOWS else None


def population(label, windows=None, forward_first_anchor=None):
    W = windows if windows is not None else L.live_windows()[0]
    if label == "FORWARD":
        return forward_population(W, forward_first_anchor)
    p = PERIODS[label]
    return [w for w in W if p["first_anchor"] <= L.nominal(w["t0"]) <= p["last_anchor"]]


# ─────────────────────────────── E0 · input validity (R5B-02) ───────────────────────────────
def _finite(x):
    try:
        return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))
    except Exception:
        return False


def validate(sim_w, live_w, live_turn):
    """every numeric input finite; times strictly increasing; positive window length. Returns a list of named violations."""
    bad = []
    for side, rows in (("sim", sim_w), ("live", live_w)):
        for k, w in enumerate(rows):
            for f in ("t0", "t1", "gross0") + tuple(FIELD.values()):
                if side == "live" and f == "turnover":
                    continue
                if f not in w or not _finite(w[f]):
                    bad.append(f"{side}[{k}].{f} not finite: {w.get(f)!r}")
            if _finite(w.get("t0")) and _finite(w.get("t1")) and not float(w["t1"]) > float(w["t0"]):
                bad.append(f"{side}[{k}] non-positive length: t0 {w['t0']} t1 {w['t1']}")
        for k in range(1, len(rows)):
            a, b = rows[k - 1].get("t0"), rows[k].get("t0")
            if _finite(a) and _finite(b) and not float(b) > float(a):
                bad.append(f"{side}[{k}] t0 not strictly increasing: {a} -> {b}")
    for k, x in enumerate(live_turn):
        if not _finite(x):
            bad.append(f"live_turnover[{k}] not finite: {x!r}")
    return bad


# ─────────────────────────────── W and T items (zero cases explicit) ───────────────────────────────
def window_item(c, sim_v, live_v):
    b = BOUNDS[c]
    e = np.asarray(sim_v, float) - np.asarray(live_v, float)
    lv = np.abs(np.asarray(live_v, float)); ae = np.abs(e)
    s = float(lv.mean())
    base = {"scale_mean_abs_live": s, "mean_abs_err": float(ae.mean()), "p90_abs_err": float(np.percentile(ae, 90)),
            "max_abs_err": float(ae.max()), "bounds": dict(b)}
    if s == 0.0:
        ok = bool(np.all(ae == 0.0))
        return dict(base, mean_abs_err_over_scale=0.0 if ok else None, p90_err_over_tol=0.0 if ok else None, max_err_over_tol=0.0 if ok else None,
                    n_windows_outside_tol=0 if ok else int((ae > 0).sum()), argmax_window=int(ae.argmax()),
                    zero_case="exact zero/zero" if ok else "zero live scale, nonzero sim", **{"pass": ok})
    tol = b["rtol"] * lv + b["k_atol"] * s                     # > 0 everywhere because s > 0
    ratio = ae / tol
    it = dict(base, mean_abs_err_over_scale=float(ae.mean() / s), p90_err_over_tol=float(np.percentile(ratio, 90)),
              max_err_over_tol=float(ratio.max()), n_windows_outside_tol=int((ratio > 1.0).sum()), argmax_window=int(ratio.argmax()))
    it["pass"] = bool(it["mean_abs_err_over_scale"] <= b["m_max"] and it["p90_err_over_tol"] <= 1.0 and it["max_err_over_tol"] <= b["t_max"])
    return it


def _ratio_item(sim_tot, live_tot, band=V1.BAND):
    if live_tot == 0.0:
        ok = sim_tot == 0.0
        return {"sim": sim_tot, "live": live_tot, "ratio": 1.0 if ok else None, "band": band,
                "zero_case": "exact zero/zero" if ok else "zero live, nonzero sim", "pass": ok}
    r = sim_tot / live_tot
    return {"sim": sim_tot, "live": live_tot, "ratio": r, "band": band, "pass": bool(band[0] <= r <= band[1])}


def totals(sim_w, live_w, live_turn):
    """the four V1 totals, V1's formulas, on the LIVE time axis (called only after E1–E3 pass)"""
    S = lambda rows, k: sum(float(r[k]) for r in rows)
    items = {"fee": _ratio_item(S(sim_w, "fee"), S(live_w, "fee")), "funding": _ratio_item(S(sim_w, "funding"), S(live_w, "funding"))}
    sg, lg = S(sim_w, "gross0"), S(live_w, "gross0")
    st, lt = S(sim_w, "turnover"), float(sum(live_turn))
    if sg == 0.0 or lg == 0.0:
        ok = st == 0.0 and lt == 0.0 and sg == lg
        items["turnover_over_gross"] = {"sim": None, "live": None, "ratio": 1.0 if ok else None, "band": V1.BAND,
                                        "zero_case": "exact zero/zero" if ok else "zero gross with nonzero turnover", "pass": ok}
    else:
        it = _ratio_item(st / sg, lt / lg)
        items["turnover_over_gross"] = dict(it, sim_turnover=st, live_turnover=lt, sim_sum_gross0=sg, live_sum_gross0=lg)
    days = collections.OrderedDict()
    for a, b in zip(sim_w, live_w):
        d = V1.day_of(b["t0"]); days.setdefault(d, 0.0); days[d] += float(a["price_trade"]) - float(b["price_trade"])
    mean, lo, hi = V1.block_bootstrap_mean_ci(list(days.values()))
    tot = S(sim_w, "price_trade") - S(live_w, "price_trade")
    tol = max(abs(S(live_w, "price_trade")), V1.PRICE_BPS * 1e-4 * lg)
    ci_ok = lo <= 0.0 <= hi
    tot_ok = abs(tot) <= tol if tol > 0 else tot == 0.0
    items["price_and_trading"] = {"sim": S(sim_w, "price_trade"), "live": S(live_w, "price_trade"), "total_diff": tot, "tolerance": tol,
                                  "n_days": len(days), "daily_diff_mean": mean, "daily_diff_ci95": [lo, hi], "ci_contains_0": ci_ok,
                                  "total_within_tol": tot_ok, "per_day_diff": dict(days),
                                  **({"zero_case": "exact zero/zero"} if tol == 0 and tot == 0 else {}), "pass": bool(ci_ok and tot_ok)}
    return items


def judge_v1b(sim_w, live_w, live_turn, label=None, declared=None):
    """pure. Returns (verdict, items). Never raises on bad numbers: E0 names them and nothing else is judged."""
    items = collections.OrderedDict()
    bad = validate(sim_w, live_w, live_turn)
    items["E0_input_validity"] = {"violations": bad[:20], "n_violations": len(bad), "pass": not bad}
    if bad:
        return "INVALID_INPUT", items
    n_ok = len(sim_w) == len(live_w) == len(live_turn)
    contig = all(abs(float(a["t1"]) - float(b["t0"])) <= T_ALIGN_S for a, b in zip(live_w, live_w[1:]))
    same_pop = True if declared is None else (len(declared) == len(live_w) and all(abs(float(a["t0"]) - float(b["t0"])) <= 1e-6 for a, b in zip(declared, live_w)))
    in_period = True
    if label is not None and label != "FORWARD" and live_w:
        p = PERIODS[label]
        in_period = all(p["first_anchor"] <= L.nominal(w["t0"]) <= p["last_anchor"] for w in live_w)
    items["E1_population"] = {"n_sim": len(sim_w), "n_live": len(live_w), "live_contiguous": contig, "declared_population": same_pop,
                              "live_in_period": in_period, "pass": bool(n_ok and contig and same_pop and in_period and len(live_w) > 0)}
    d0 = max((abs(float(a["t0"]) - float(b["t0"])) for a, b in zip(sim_w, live_w)), default=0.0) if n_ok else float("inf")
    d1 = max((abs(float(a["t1"]) - float(b["t1"])) for a, b in zip(sim_w, live_w)), default=0.0) if n_ok else float("inf")
    items["E2_t0"] = {"max_abs_dt0_s": d0, "tol_s": T_ALIGN_S, "pass": bool(d0 <= T_ALIGN_S)}
    items["E3_t1"] = {"max_abs_dt1_s": d1, "tol_s": T_ALIGN_S, "pass": bool(d1 <= T_ALIGN_S)}
    aligned = items["E1_population"]["pass"] and items["E2_t0"]["pass"] and items["E3_t1"]["pass"]
    for c, f in FIELD.items():
        if not n_ok:
            items["W_" + c] = {"pass": False, "why": "window lists differ in length"}; continue
        lv = live_turn if c == "turnover" else [float(w[f]) for w in live_w]
        items["W_" + c] = window_item(c, [float(w[f]) for w in sim_w], lv)
    if aligned:
        t = totals(sim_w, live_w, live_turn)
        for k in ("fee", "turnover_over_gross", "funding", "price_and_trading"):
            items["T_" + k] = t[k]
    else:
        for k in ("fee", "turnover_over_gross", "funding", "price_and_trading"):
            items["T_" + k] = {"pass": False, "why": "not evaluable: E1–E3 failed (misaligned windows cannot be summed against each other)"}
    return ("PASS" if all(it["pass"] for it in items.values()) else "FAIL"), items


# ─────────────────────────────── provenance (R5B-01) ───────────────────────────────
def _calibration_rederived(calib_mirror):
    """re-run the PINNED calibrator on the manifest-verified ORIGINAL mirror; params / estimands / population / boundary must be
    reproduced exactly. Cached per process."""
    key = calib_mirror
    if key in _CALIB_CACHE:
        return _CALIB_CACHE[key]
    import calib_v3 as C
    pinned = json.load(open(APPROVED["calibration"][0]))
    tmp = tempfile.mkdtemp(prefix="v1b_calib_")
    out = os.path.join(tmp, "calib_rederived.json")
    argv0 = sys.argv
    try:
        sys.argv = ["calib_v3.py", out, calib_mirror]
        with contextlib.redirect_stdout(io.StringIO()):
            C.main()
        new = json.load(open(out))
    except Exception as e:
        _CALIB_CACHE[key] = [f"calibration re-derivation failed: {type(e).__name__}: {str(e)[:120]}"]
        return _CALIB_CACHE[key]
    finally:
        sys.argv = argv0
    bad = []
    for k in ("kind", "frozen_before_holdout", "calibration_anchors", "trade_time_range_utc", "device_sha256", "inputs_sha256", "params", "estimands"):
        if json.dumps(new.get(k), sort_keys=True) != json.dumps(pinned.get(k), sort_keys=True):
            bad.append(f"calibration not reproduced by the pinned calibrator: field {k}")
    if tuple(pinned.get("calibration_anchors") or ()) != CALIB_ANCHORS:
        bad.append(f"calibration anchors {pinned.get('calibration_anchors')} != declared {CALIB_ANCHORS}")
    if pinned.get("trade_time_range_utc") != ["08-26 00:00:00Z", "09-11 00:00:00Z"]:
        bad.append(f"calibration stop boundary {pinned.get('trade_time_range_utc')} != declared [08-26 00:00:00Z, 09-11 00:00:00Z)")
    _CALIB_CACHE[key] = bad
    return bad


def check_provenance(doc, label, sim_path, M, inputs, forward_first_anchor=None, calib_mirror=L.MIRROR_DEFAULT, check_calibration=True):
    """returns (violations, recomputed). recomputed = {'paths': [...], 'mean': [...]} built only from the artifacts."""
    bad = []
    base_dir = os.path.dirname(os.path.abspath(sim_path))
    # A · approved files on disk
    for name, (p, sha) in APPROVED.items():
        if not os.path.exists(p):
            bad.append(f"approved file missing: {name}"); continue
        if L.sha_file(p) != sha:
            bad.append(f"approved file changed: {name} ({L.sha_file(p)[:12]} != {sha[:12]})")
    if label != "FORWARD":
        for name, (p, sha) in APPROVED_HISTORICAL.items():
            if os.path.abspath(inputs[name]) != os.path.abspath(p) or L.sha_file(inputs[name]) != sha:
                bad.append(f"historical input {name} is not the approved file")
    # B · receipt identity claims vs files
    if doc.get("version") != SIM_VERSION:
        bad.append(f"simulator version {doc.get('version')!r} != approved {SIM_VERSION!r}")
    if doc.get("device_sha256") != APPROVED["exec_sim.py"][1]:
        bad.append("receipt's simulator sha is not the approved simulator")
    if L.sha_file(APPROVED["exec_sim.py"][0]) != APPROVED["exec_sim.py"][1]:
        return bad + ["the simulator file on disk is not the approved one — nothing further is read"], {"paths": [], "mean": None}
    import exec_sim as ES
    kn = doc.get("knobs")
    if not isinstance(kn, dict) or set(kn) != set(ES.KNOBS):
        bad.append(f"knobs missing or unknown: {sorted(set(ES.KNOBS) ^ set(kn or {}))}")
    elif any(kn.values()):
        bad.append(f"knobs on: {[k for k, v in kn.items() if v]}")
    if doc.get("mode") != "live":
        bad.append("mode must be live")
    per = doc.get("period") or {}
    want_rs = (forward_first_anchor - H4) if label == "FORWARD" else PERIODS[label]["run_start_anchor"]
    if per.get("label") != PERIODS[label]["sim_label"] or per.get("run_start_anchor") != want_rs:
        bad.append(f"period {per.get('label')}/{per.get('run_start_anchor')} != declared {PERIODS[label]['sim_label']}/{want_rs}")
    if label == "FORWARD" and per.get("forward_first_anchor") != forward_first_anchor:
        bad.append("forward first anchor differs from the one passed to the gate")
    cal = doc.get("calibration") or {}
    if cal.get("sha256") != APPROVED["calibration"][1] or os.path.abspath(os.path.join(L.REPO, cal.get("path", ""))) != os.path.abspath(APPROVED["calibration"][0]):
        bad.append("receipt's calibration is not the approved calibration file")
    deps = doc.get("dependencies_sha256") or {}
    want = {"exec_sim.py": APPROVED["exec_sim.py"], "simlib.py": APPROVED["simlib.py"], "calibration": APPROVED["calibration"],
            "fills_reader.py": APPROVED["fills_reader.py"]}
    for k, (p, _) in want.items():
        if deps.get(k) != L.sha_file(p):
            bad.append(f"dependency claim {k} differs from the file")
    if deps.get("v1b_gate.py (period source)") != self_sha():
        bad.append("the simulator ran with a different v1b_gate.py (period source) than this gate")
    for k in ("manifest", "live_g", "transfers"):
        if deps.get(k) != L.sha_file(inputs[k]):
            bad.append(f"dependency claim {k} differs from the input file the gate uses")
    man = M.manifest or {}
    tree = (man.get("executor_tree") or {}).get("files_sha256") or {}
    claims = doc.get("executor_code_files_sha256") or {}
    if not claims:
        bad.append("no executor code file claims")
    for rel, sha in claims.items():               # the manifest entry AND the mirror bytes (verify_manifest does not cover the exported tree)
        if tree.get(rel) != sha:
            bad.append(f"executor code file claim not in the manifest: {rel}")
        elif not os.path.exists(os.path.join(M.root, rel)) or L.sha_file(os.path.join(M.root, rel)) != sha:
            bad.append(f"executor code file in the mirror differs from the manifest: {rel}")
    # C · mirror bytes
    mb = M.verify_manifest()
    if mb:
        bad.append(f"mirror differs from the manifest: {len(mb)} files, e.g. {mb[:3]}")
    # D · calibration re-derivation (population + stop boundary)
    if check_calibration:
        bad += _calibration_rederived(calib_mirror)
    # E · sealed initial state vs the executor's own readback at t0 (recomputed from the verified mirror)
    ini = doc.get("initial_state_sealed") or {}
    sp = os.path.join(base_dir, ini.get("sealed_file") or "\0missing")
    sealed_sha = None
    if not ini.get("sealed_before_run") or not os.path.exists(sp):
        bad.append("sealed initial-state artifact missing")
    else:
        sf = json.load(open(sp)); st = sf.get("state") or {}
        sealed_sha = ES.canon_sha(st)
        if not (sealed_sha == sf.get("sha256") == ini.get("sha256")):
            bad.append("sealed initial state does not re-hash to the claimed sha")
        Wall = live_windows_from(inputs["live_g"])
        w0 = [w for w in Wall if L.nominal(w["t0"]) == want_rs]
        if not w0:
            bad.append("no live window at the run start")
        else:
            t0 = float(w0[0]["t0"])
            day = time.strftime("%Y%m%d", time.gmtime(t0))
            q = {r["symbol"]: float(r["venue_position_qty"]) for r in M.rows(day, "position_readback")
                 if abs(float(r["read_ts"]) - t0) < 1.0 and float(r["venue_position_qty"]) != 0.0}
            if not q or st.get("positions_qty") != dict(sorted(q.items())) or st.get("n_positions") != len(q):
                bad.append(f"sealed positions differ from the executor's readback at t0 ({len(q)} names)")
            if st.get("t0") != t0 or st.get("nav0_usdt") != float(w0[0]["nav0_usdt"]):
                bad.append("sealed t0 / NAV differ from the live window at the run start")
    # F · per-seed path artifacts
    pp = doc.get("paths") or {}
    seeds = pp.get("seeds") or []
    files = {f.get("seed"): f for f in (pp.get("files") or [])}
    if len(seeds) < R_MIN or list(seeds) != list(range(len(seeds))):
        bad.append(f"seeds must be 0..R-1 with R >= {R_MIN}")
    if sorted(files) != list(seeds):
        bad.append("not exactly one path artifact per seed")
    paths = []
    for sd in seeds:
        f = files.get(sd)
        fp = os.path.join(base_dir, (f or {}).get("file") or "\0missing")
        if f is None or not os.path.exists(fp):
            bad.append(f"path artifact missing for seed {sd}"); continue
        if L.sha_file(fp) != f.get("sha256"):
            bad.append(f"path artifact of seed {sd} does not re-hash"); continue
        r = json.load(open(fp))
        if r.get("seed") != sd or r.get("exec_sim_sha256") != APPROVED["exec_sim.py"][1] or r.get("calibration_sha256") != APPROVED["calibration"][1] \
                or r.get("initial_state_sha256") != sealed_sha or r.get("run_start_anchor") != want_rs:
            bad.append(f"path artifact of seed {sd} names another seed / simulator / calibration / initial state / run start"); continue
        paths.append(r)
    rec = {"paths": paths, "mean": None}
    if paths and len(paths) == len(seeds):
        ref = [(w["idx"], w["t0"], w["t1"]) for w in paths[0]["windows"]]
        if any([(w["idx"], w["t0"], w["t1"]) for w in p["windows"]] != ref for p in paths):
            bad.append("path artifacts disagree on the window axis")
        else:
            mean = []
            for i, (idx, t0, t1) in enumerate(ref):
                row = {"idx": idx, "t0": t0, "t1": t1, "from": paths[0]["windows"][i]["from"], "to": paths[0]["windows"][i]["to"]}
                for f_ in ("gross0",) + tuple(FIELD.values()):
                    row[f_] = float(np.mean([float(p["windows"][i][f_]) for p in paths]))
                mean.append(row)
            rw = doc.get("windows") or []

            def same(x, y):          # NaN-safe: NaN == NaN and inf == inf count as consistent (E0 then names them), anything else must be close
                x, y = float(x), float(y)
                return x == y or (math.isnan(x) and math.isnan(y)) or abs(x - y) <= 1e-9 * max(1.0, abs(y))
            if len(rw) != len(mean) or not all(same(a[f_], b[f_]) and same(a["t0"], b["t0"]) and same(a["t1"], b["t1"])
                                               for a, b in zip(rw, mean) for f_ in ("gross0",) + tuple(FIELD.values())):
                bad.append("receipt window means differ from the means recomputed from the path artifacts")
            rec["mean"] = mean
    return bad, rec


# ─────────────────────────────── diagnostics from the artifacts (not verdict items) ───────────────────────────────
def mc_and_path_diagnostics(paths, pop_idx, live_w, live_turn, items):
    """Monte Carlo standard error per window item and path-distribution diagnostics — V1b validates conditional means only"""
    R = len(paths)
    sel = [[w for w in p["windows"] if w["idx"] in pop_idx] for p in paths]
    out = {"statement": "V1b validates the conditional MEAN of each window item only; it does not validate path risk (variance, halt / stop incidence, tails, maxDD). R >= 32 is a minimum amount of computation, not a precision guarantee.",
           "R": R, "mc_standard_error": {}, "live_inside_path_p05_p95_share": {}}
    for c, f in FIELD.items():
        X = np.array([[float(w[f]) for w in s] for s in sel])               # R × n
        se = X.std(axis=0, ddof=1) / math.sqrt(R)
        lv = np.abs(np.asarray(live_turn if c == "turnover" else [float(w[f]) for w in live_w], float))
        s = lv.mean()
        b = BOUNDS[c]; tol = b["rtol"] * lv + b["k_atol"] * s if s > 0 else np.full(len(lv), np.nan)
        tot = X.sum(axis=1)
        lvv = np.asarray(live_turn if c == "turnover" else [float(w[f]) for w in live_w], float)
        lo, hi = np.percentile(X, 5, axis=0), np.percentile(X, 95, axis=0)
        out["mc_standard_error"][c] = {"per_window_mean": float(se.mean()), "per_window_max": float(se.max()),
                                       "max_se_over_window_tol": (float(np.nanmax(se / tol)) if s > 0 else None),
                                       "se_of_population_total": float(tot.std(ddof=1) / math.sqrt(R))}
        out["live_inside_path_p05_p95_share"][c] = float(np.mean((lvv >= lo) & (lvv <= hi)))
    net = np.array([[float(w["price_trade"]) + float(w["funding"]) - float(w["fee"]) for w in s] for s in sel])
    nav = np.array([[float(w["nav0"]) for w in s] for s in sel])

    def maxdd(r):
        idx = np.cumprod(1.0 + r); peak = np.maximum.accumulate(np.r_[1.0, idx])[1:]
        return float((idx / peak - 1.0).min())
    dd = [maxdd(np.where(n > 0, x / np.where(n > 0, n, 1.0), 0.0)) for x, n in zip(net, nav)]
    lnet = np.array([float(w["price_trade"]) + float(w["funding"]) - float(w["fee"]) for w in live_w])
    lnav = np.array([float(w.get("nav0_usdt") or 0.0) for w in live_w])
    t_lo, t_hi = float(live_w[0]["t0"]), float(live_w[-1]["t1"])

    def in_pop(e):
        t = time.mktime(time.strptime("2026-" + e["utc"], "%Y-%m-%d %H:%M:%SZ")) - time.timezone
        return t_lo < t <= t_hi
    stops = [sum(1 for e in p.get("stops", []) if in_pop(e)) for p in paths]
    flats = [sum(1 for e in p.get("flattens", []) if in_pop(e)) for p in paths]

    def dist(v):
        v = np.asarray(v, float)
        return {"mean": float(v.mean()), "sd": float(v.std(ddof=1)), "p05": float(np.percentile(v, 5)), "p50": float(np.median(v)),
                "p95": float(np.percentile(v, 95)), "min": float(v.min()), "max": float(v.max())}
    out["path_distribution"] = {"net_total_usdt": dist(net.sum(axis=1)), "maxdd_of_transfer_free_return_index": dist(dd),
                                "stops_in_population": dist(stops), "flattens_in_population": dist(flats),
                                "live_net_total_usdt": float(lnet.sum()),
                                "live_maxdd_same_index": maxdd(np.where(lnav > 0, lnet / np.where(lnav > 0, lnav, 1.0), 0.0))}
    return out


def verdict_lines(label, verdict, items, reasons=None):
    tag = f"V1b[{label}]"
    out = []
    if verdict == "UNAVAILABLE":
        out.append(f"{tag} VERDICT: UNAVAILABLE ({len(reasons)} provenance violations: " + "; ".join(reasons[:6]) + (" …" if len(reasons) > 6 else "") + ")")
        return out
    e0 = items["E0_input_validity"]
    out.append(f"{tag} E0 input validity    {e0['n_violations']} violations  {'PASS' if e0['pass'] else 'FAIL'}" + (f"  e.g. {e0['violations'][:3]}" if not e0["pass"] else ""))
    if verdict == "INVALID_INPUT":
        out.append(f"{tag} VERDICT: INVALID_INPUT (E0 failed; nothing else judged)")
        return out
    e = items["E1_population"]
    out.append(f"{tag} E1 population        sim {e['n_sim']} windows, live {e['n_live']}  contiguous {e['live_contiguous']}  "
               f"declared {e['declared_population']}  in-period {e['live_in_period']}  {'PASS' if e['pass'] else 'FAIL'}")
    out.append(f"{tag} E2 t0 alignment      max |Δt0| {items['E2_t0']['max_abs_dt0_s']:.3f} s ≤ 1 s  {'PASS' if items['E2_t0']['pass'] else 'FAIL'}")
    out.append(f"{tag} E3 t1 alignment      max |Δt1| {items['E3_t1']['max_abs_dt1_s']:.3f} s ≤ 1 s  {'PASS' if items['E3_t1']['pass'] else 'FAIL'}")
    for c in FIELD:
        it = items["W_" + c]
        if "scale_mean_abs_live" not in it:
            out.append(f"{tag} W {c:<18} {it.get('why')}  FAIL"); continue
        if it.get("zero_case"):
            out.append(f"{tag} W {c:<18} {it['zero_case']}  {'PASS' if it['pass'] else 'FAIL'}"); continue
        b = it["bounds"]
        out.append(f"{tag} W {c:<18} s=mean|live| {it['scale_mean_abs_live']:,.2f}  |e| mean {it['mean_abs_err']:,.2f} "
                   f"({it['mean_abs_err_over_scale']:.3f}·s ≤ {b['m_max']})  p90 {it['p90_abs_err']:,.2f}  max {it['max_abs_err']:,.2f}  "
                   f"e/tol p90 {it['p90_err_over_tol']:.3f} ≤ 1  max {it['max_err_over_tol']:.3f} ≤ {b['t_max']}  "
                   f"({it['n_windows_outside_tol']} outside)  {'PASS' if it['pass'] else 'FAIL'}")
    for k in ("fee", "turnover_over_gross", "funding"):
        it = items["T_" + k]
        if "why" in it or it.get("zero_case"):
            out.append(f"{tag} T {k:<18} {it.get('why') or it.get('zero_case')}  {'PASS' if it['pass'] else 'FAIL'}"); continue
        out.append(f"{tag} T {k:<18} sim {it['sim']:>14,.4f}  live {it['live']:>14,.4f}  ratio {it['ratio']:.4f}  band [0.8, 1.25]  "
                   f"{'PASS' if it['pass'] else 'FAIL'}")
    p = items["T_price_and_trading"]
    if "tolerance" in p:
        out.append(f"{tag} T price_and_trading  sim {p['sim']:,.2f}  live {p['live']:,.2f}  total diff {p['total_diff']:+,.2f}  tol {p['tolerance']:,.2f}  "
                   f"daily-diff mean {p['daily_diff_mean']:+,.2f} CI95 [{p['daily_diff_ci95'][0]:+,.2f}, {p['daily_diff_ci95'][1]:+,.2f}] "
                   f"(n_days {p['n_days']})  {'PASS' if p['pass'] else 'FAIL'}")
    else:
        out.append(f"{tag} T price_and_trading  {p.get('why')}  FAIL")
    n_pass = sum(1 for it in items.values() if it["pass"])
    out.append(f"{tag} VERDICT: {verdict} ({n_pass}/{len(items)} items)")
    return out


def live_side_violations(live_w):
    """the live side must itself be a closed cash identity on every judged window (LIVE_G cash_ok is True)"""
    open_w = [w.get("from") for w in live_w if w.get("cash_ok") is not True]
    return [f"live cash identity not closed (cash_ok) on {len(open_w)} windows, e.g. {open_w[:3]}"] if open_w else []


def run_gate(sim_p, label, out_p, mirror=L.MIRROR_DEFAULT, manifest=None, live_g=None, transfers=None, forward_first_anchor=None,
             calib_mirror=L.MIRROR_DEFAULT, check_calibration=True, extra=None):
    """the full entry: provenance → recomputation → E0 → items → receipt. Returns the verdict name."""
    inputs = {"manifest": manifest or APPROVED_HISTORICAL["manifest"][0], "live_g": live_g or APPROVED_HISTORICAL["live_g"][0],
              "transfers": transfers or APPROVED_HISTORICAL["transfers"][0]}
    if L.sha_file(APPROVED["exec_sim.py"][0]) == APPROVED["exec_sim.py"][1]:
        import exec_sim as ES                         # imported only after its sha is verified
        M = ES.WideMirror(mirror)
    else:
        M = L.Mirror(mirror)                          # provenance will report the unapproved simulator
    M.manifest = json.load(open(inputs["manifest"]))
    L.install_readonly_guard()
    try:
        doc = json.load(open(sim_p))
    except Exception as e:
        doc = {}
    reasons, rec = check_provenance(doc, label, sim_p, M, inputs, forward_first_anchor, calib_mirror, check_calibration)
    Wall = live_windows_from(inputs["live_g"])
    live_w = population(label, Wall, forward_first_anchor)
    if live_w is None:
        reasons.append(f"FORWARD: fewer than {FORWARD_N_WINDOWS} complete live windows exist yet — no readout")
    else:
        reasons += live_side_violations(live_w)
    items, diag, verdict = {}, {}, None
    if reasons or rec.get("mean") is None:
        verdict = "UNAVAILABLE"
        if not reasons:
            reasons.append("no recomputable path artifacts")
    else:
        pop = {L.nominal(w["t0"]) for w in live_w}
        sim_w = [w for w in rec["mean"] if L.nominal(w["t0"]) in pop]
        lt, _ = V1.live_turnover(M, live_w)
        verdict, items = judge_v1b(sim_w, live_w, lt, label=label, declared=population(label, Wall, forward_first_anchor))
        if verdict != "INVALID_INPUT" and items["E1_population"]["pass"]:
            diag = mc_and_path_diagnostics(rec["paths"], {w["idx"] for w in sim_w}, live_w, lt, items)
    lines = verdict_lines(label, verdict, items, reasons)
    if diag:
        for c, v in diag["mc_standard_error"].items():
            lines.append(f"V1b[{label}] diag MC s.e. {c:<18} per-window mean {v['per_window_mean']:,.3f}  max {v['per_window_max']:,.3f}  "
                         f"max s.e./tol {v['max_se_over_window_tol'] if v['max_se_over_window_tol'] is None else round(v['max_se_over_window_tol'], 3)}  "
                         f"s.e. of total {v['se_of_population_total']:,.2f}  (R {diag['R']})")
        pdist = diag["path_distribution"]
        lines.append(f"V1b[{label}] diag paths: net total mean {pdist['net_total_usdt']['mean']:+,.2f} sd {pdist['net_total_usdt']['sd']:,.2f} "
                     f"[p05 {pdist['net_total_usdt']['p05']:+,.2f}, p95 {pdist['net_total_usdt']['p95']:+,.2f}] vs live {pdist['live_net_total_usdt']:+,.2f}; "
                     f"maxDD mean {pdist['maxdd_of_transfer_free_return_index']['mean']:+.4f} [min {pdist['maxdd_of_transfer_free_return_index']['min']:+.4f}] "
                     f"vs live {pdist['live_maxdd_same_index']:+.4f}; stops mean {pdist['stops_in_population']['mean']:.1f}; "
                     f"flattens mean {pdist['flattens_in_population']['mean']:.1f} — NOT a verdict item: V1b does not validate path risk")
    out = {"device": "v1b_gate.py", "gate_version": GATE_VERSION, "device_sha256": self_sha(), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "rerun": "/usr/bin/python3 " + " ".join([os.path.relpath(os.path.abspath(__file__), L.REPO)] + sys.argv[1:]),
           "label": label, "role": PERIODS[label]["role"], "forward_first_anchor": forward_first_anchor, "bounds": BOUNDS,
           "approved_table": {k: v[1] for k, v in APPROVED.items()}, "inputs": {k: {"path": os.path.abspath(v), "sha256": L.sha_file(v)} for k, v in inputs.items()},
           "sim_receipt": {"path": os.path.abspath(sim_p), "sha256": L.sha_file(sim_p) if os.path.exists(sim_p) else None,
                           "version": doc.get("version"), "device_sha256": doc.get("device_sha256")},
           "verdict": verdict, "provenance_violations": reasons, "verdict_lines": lines, "items": items, "diagnostics": diag, **(extra or {})}
    with open(out_p + ".part", "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    os.replace(out_p + ".part", out_p)
    print("\n".join(lines))
    return verdict


def reviewer_counterexample(shift_t1=7200.0, anti=True):
    """R5-07 reviewer probe: 24 UTC days × 6 windows, live price ±1000 alternating; sim = −live price and every t1 shifted"""
    live = [{"t0": d * 86400 + j * 14400, "t1": d * 86400 + (j + 1) * 14400, "fee": 1, "funding": -1, "turnover": 100, "gross0": 1000,
             "price_trade": 1000 if j % 2 else -1000} for d in range(24) for j in range(6)]
    sim = [dict(w, price_trade=(-w["price_trade"] if anti else w["price_trade"]), t1=w["t1"] + shift_t1) for w in live]
    return sim, live, [100] * len(live)


def selftest(mirror):
    """no simulator: judge(live, live) on CAL must PASS; the R5-07 counterexample must FAIL; E0 catches NaN / Inf / axis defects"""
    M = L.Mirror(mirror)
    L.install_readonly_guard()
    res = []

    def chk(name, ok, detail):
        res.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)
    live_w = population("CAL")
    lt, _ = V1.live_turnover(M, live_w)
    same = [dict(w, turnover=t) for w, t in zip(live_w, lt)]
    v, it = judge_v1b(same, live_w, lt, label="CAL", declared=population("CAL"))
    chk("judge(live, live) on CAL passes every item", v == "PASS", f"{v}, {sum(x['pass'] for x in it.values())}/{len(it)}")
    v, it = judge_v1b(*reviewer_counterexample())
    chk("R5-07 counterexample (anti-correlated, t1 +2 h) is not PASS", v == "FAIL", v)
    bad = copy.deepcopy(same); bad[len(bad) // 2]["t1"] = float("nan")
    v, _ = judge_v1b(bad, live_w, lt, label="CAL", declared=population("CAL"))
    chk("NaN t1 in the middle window ⇒ INVALID_INPUT", v == "INVALID_INPUT", v)
    n_ok = sum(res)
    print(f"V1b v2 SELFTEST: {'ALL PASS' if n_ok == len(res) else 'FAILURES'} {n_ok}/{len(res)} checks")
    return n_ok, len(res)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        n_ok, n = selftest(sys.argv[2] if len(sys.argv) > 2 else L.MIRROR_DEFAULT)
        sys.exit(0 if n_ok == n else 1)
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("sim"); ap.add_argument("label", choices=tuple(PERIODS)); ap.add_argument("out")
    ap.add_argument("--mirror", default=L.MIRROR_DEFAULT); ap.add_argument("--manifest", default=None)
    ap.add_argument("--live-g", default=None); ap.add_argument("--transfers", default=None)
    ap.add_argument("--forward-first-anchor", type=int, default=None); ap.add_argument("--calib-mirror", default=L.MIRROR_DEFAULT)
    a = ap.parse_args()
    if a.label == "FORWARD" and a.forward_first_anchor is None:
        print("V1b[FORWARD] VERDICT: UNAVAILABLE (1 provenance violations: --forward-first-anchor not given)"); sys.exit(EXIT["UNAVAILABLE"])
    v = run_gate(a.sim, a.label, a.out, a.mirror, a.manifest, a.live_g, a.transfers, a.forward_first_anchor, a.calib_mirror)
    sys.exit(EXIT[v])


if __name__ == "__main__":
    main()
