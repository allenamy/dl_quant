#!/usr/bin/env python3
"""replay_exec 2026-09-19 · V1b gate — PRE-DECLARED (written and committed BEFORE any exec_sim v3 number exists; review round 5
R5-07). V1 (v1_gate.py, unchanged) stays the CALIBRATION-PERIOD RECONCILIATION of v1/v2 — it is not renamed "validation".

Why a new gate (R5-07, reviewer probe `anti_correlated_and_wrong_t1_pass`): V1 checks t0 only, and judges whole-period sums plus
a CI on UTC-DAY sums of the price difference. A perfectly anti-correlated 4h path with 2,000 USD per-window errors that cancel
inside each day, with every t1 two hours late, passes all four V1 items. V1b judges every 4h window.

POPULATION (fixed here, before any number): the LIVE_G_DECOMPOSITION windows whose start anchor nominal(t0) lies in the period's
[first_anchor, last_anchor] — ALL of them (no gross0 > 0 filter, no dropping of empty / flat-start / halted windows; the two live
windows that span 8 h because an anchor produced no NAV row are kept as they are). The simulator must report exactly that list.
  CAL      anchors 08-26 04Z .. 09-10 20Z  role: calibration period (IN-SAMPLE for the pooled v3 parameters)
           sim run = one continuous run started from the executor's own readback at the t0 of the 08-26 00Z window; that first
           window is warm-up (declared here, not gated): its t0 readback is taken after the 00Z anchor's maker leg and before its
           top-up leg, and in-flight orders at t0 are not simulated.
  HOLDOUT  anchors 09-11 00Z .. 09-18 20Z  role: HOLD-OUT (parameters re-calibrated on 08-26 00Z .. 09-10 20Z only, frozen first)
           sim run = restarted from the executor's own readback at the t0 of the 09-10 20Z window (real positions, real stop state,
           real NAV); that window is warm-up. THIS is the verdict of record for out-of-sample.
  HOLDOUT_CONTINUOUS_DIAG  same windows as HOLDOUT, taken from the continuous run started 08-26 00Z (state drift included).
           DIAGNOSTIC only — reported, never the verdict of record.

SIM-SIDE CONTRACT (the receipt is refused otherwise): exec_sim version "v3"; every knob off; calibration = a v3 POOLED calibration
file with frozen_before_holdout = true whose sha256 matches; the per-window values are the MEAN over R >= 32 seeded paths with seeds
exactly 0..R-1 (no seed selection); the receipt carries the sealed initial state and its sha; its period label and run-start
anchor equal the ones declared above. Frame rule (stated here before any number, implemented in exec_sim v3): the live window
boundary t0(A) is the executor's own post-run readback of anchor A, and every live fill of anchor A precedes it (measured on the
calibration period: 0.0% of rebalance fill notional after the own-anchor NAV row); the simulator therefore orders its own fills of
anchor A before that readback instant. It changes WHEN a fill is booked by at most the gap to the readback, never how much.

ITEMS (every one must PASS; the verdict line counts them):
  E1 population   sim window count == live window count; the live windows are contiguous (t1_k == t0_{k+1} within 1 s) and are
                  exactly the declared population (first / last start anchor inside the period, none dropped)
  E2 t0           max_w |t0_sim − t0_live| <= 1 s
  E3 t1           max_w |t1_sim − t1_live| <= 1 s
  W  per window, for c in {price_and_trading, funding, fee, turnover}: e_w = sim_w − live_w (USDT), s_c = mean_w |live_w| over the
     population. Reported: mean |e|, p90 |e|, max |e| (USDT). Per-window equivalence bound tol_w = rtol·|live_w| + atol, atol =
     k_atol · s_c. PASS iff  mean|e| / s_c <= m_max  AND  p90_w(|e_w| / tol_w) <= 1 (at least 90% of windows inside their own
     bound)  AND  max_w(|e_w| / tol_w) <= t_max (tail: no window beyond t_max times its bound). numpy percentile, linear.
         c                   rtol   k_atol   m_max   t_max     rationale
         price_and_trading   0.25   0.25     0.35    3.0       P&L is not a level: the atol floor (a quarter of the typical window
                                                               P&L) absorbs the irreducible fill-lottery noise of ONE live path
         funding             0.25   0.10     0.25    3.0       levels: rtol = the program's total band [0.8, 1.25] applied per
         fee                 0.25   0.10     0.25    3.0       window; atol only guards windows whose live value is ~0 (halted /
         turnover            0.25   0.10     0.25    3.0       flat windows)
     A simulator with no skill (sim = 0) has mean|e|/s = 1 and fails every W item; the reviewer's anti-correlated path has 2.
  T  the four V1 totals unchanged (v1_gate.judge: fee, turnover/gross, funding ratios in [0.8, 1.25]; price total within
     max(|Σ live|, 0.5 bps × Σ live gross0) and the UTC-day block-bootstrap CI of the mean daily difference contains 0).
     Evaluated only when E1–E3 pass (misaligned windows cannot be summed against each other) — otherwise the four items FAIL.
Live side exactly as V1: price_and_trading / funding / fee from LIVE_G_DECOMPOSITION (closed cash identity), live turnover = Σ
|quote notional| of every executed trade in (t0, t1] (v1_gate.live_turnover). Hold-out limitation stated up front: 8 days, 48
windows, one live path; a PASS is equivalence at these bounds on that week, not a guarantee for other regimes.
usage: v1b_gate.py <SIM_v3.json> <CAL|HOLDOUT|HOLDOUT_CONTINUOUS_DIAG> <out.json> [mirror]
       v1b_gate.py --selftest [mirror]   (judge(live, live) on CAL + the reviewer's counterexamples; no simulator involved)
"""
import collections, json, math, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simlib as L
import v1_gate as V1

H4 = 14400
PERIODS = {
    "CAL": {"first_anchor": 1787716800, "last_anchor": 1789070400, "run_start_anchor": 1787702400,
            "role": "calibration period (in-sample for the pooled v3 parameters)"},
    "HOLDOUT": {"first_anchor": 1789084800, "last_anchor": 1789761600, "run_start_anchor": 1789070400,
                "role": "hold-out (pooled parameters calibrated on 08-26 00Z..09-10 20Z only) — verdict of record"},
    "HOLDOUT_CONTINUOUS_DIAG": {"first_anchor": 1789084800, "last_anchor": 1789761600, "run_start_anchor": 1787702400,
                                "role": "diagnostic: hold-out windows of the continuous run (not the verdict of record)"},
}
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


def population(label, windows=None):
    """the declared live population for a period: every LIVE_G window whose start anchor lies in [first, last]"""
    p = PERIODS[label]
    W = windows if windows is not None else L.live_windows()[0]
    return [w for w in W if p["first_anchor"] <= L.nominal(w["t0"]) <= p["last_anchor"]]


def window_item(c, sim_v, live_v):
    b = BOUNDS[c]
    e = np.asarray(sim_v, float) - np.asarray(live_v, float)
    lv = np.abs(np.asarray(live_v, float))
    s = float(lv.mean()) if len(lv) else float("nan")
    ae = np.abs(e)
    tol = b["rtol"] * lv + b["k_atol"] * s
    ratio = np.where(tol > 0, ae / np.where(tol > 0, tol, 1.0), np.where(ae > 0, np.inf, 0.0))
    it = {"scale_mean_abs_live": s, "mean_abs_err": float(ae.mean()), "p90_abs_err": float(np.percentile(ae, 90)),
          "max_abs_err": float(ae.max()), "mean_abs_err_over_scale": float(ae.mean() / s) if s > 0 else float("inf"),
          "p90_err_over_tol": float(np.percentile(ratio, 90)), "max_err_over_tol": float(ratio.max()),
          "n_windows_outside_tol": int((ratio > 1.0).sum()), "argmax_window": int(ratio.argmax()), "bounds": dict(b)}
    it["pass"] = bool(it["mean_abs_err_over_scale"] <= b["m_max"] and it["p90_err_over_tol"] <= 1.0 and it["max_err_over_tol"] <= b["t_max"])
    return it


def judge_v1b(sim_w, live_w, live_turn, label=None, declared=None):
    """pure: V1b items from the sim window list and the declared live population (same order). `declared` = the population
    the gate itself derived for `label` (identity of the live list is checked, so a caller cannot hand in a trimmed list)."""
    items = collections.OrderedDict()
    n_ok = len(sim_w) == len(live_w)
    contig = all(abs(a["t1"] - b["t0"]) <= T_ALIGN_S for a, b in zip(live_w, live_w[1:]))
    same_pop = True
    if declared is not None:
        same_pop = len(declared) == len(live_w) and all(abs(a["t0"] - b["t0"]) <= 1e-6 for a, b in zip(declared, live_w))
    in_period = True
    if label is not None and live_w:
        p = PERIODS[label]
        in_period = all(p["first_anchor"] <= L.nominal(w["t0"]) <= p["last_anchor"] for w in live_w)
    items["E1_population"] = {"n_sim": len(sim_w), "n_live": len(live_w), "live_contiguous": contig, "declared_population": same_pop,
                              "live_in_period": in_period, "pass": bool(n_ok and contig and same_pop and in_period and len(live_w) > 0)}
    if n_ok:
        d0 = max((abs(float(a["t0"]) - float(b["t0"])) for a, b in zip(sim_w, live_w)), default=0.0)
        d1 = max((abs(float(a["t1"]) - float(b["t1"])) for a, b in zip(sim_w, live_w)), default=0.0)
    else:
        d0 = d1 = float("inf")
    items["E2_t0"] = {"max_abs_dt0_s": d0, "tol_s": T_ALIGN_S, "pass": bool(d0 <= T_ALIGN_S)}
    items["E3_t1"] = {"max_abs_dt1_s": d1, "tol_s": T_ALIGN_S, "pass": bool(d1 <= T_ALIGN_S)}
    aligned = items["E1_population"]["pass"] and items["E2_t0"]["pass"] and items["E3_t1"]["pass"]
    for c, f in FIELD.items():
        if not n_ok:
            items["W_" + c] = {"pass": False, "why": "window lists differ in length"}
            continue
        lv = live_turn if c == "turnover" else [float(w[f]) for w in live_w]
        items["W_" + c] = window_item(c, [float(w[f]) for w in sim_w], lv)
    if aligned:
        t = V1.judge(sim_w, live_w, live_turn)
        for k in ("fee", "turnover_over_gross", "funding", "price_and_trading"):
            items["T_" + k] = t[k]
    else:
        for k in ("fee", "turnover_over_gross", "funding", "price_and_trading"):
            items["T_" + k] = {"pass": False, "why": "not evaluable: E1–E3 failed (misaligned windows cannot be summed against each other)"}
    return items


def verdict_lines(label, items):
    tag = f"V1b[{label}]"
    out = []
    e = items["E1_population"]
    out.append(f"{tag} E1 population        sim {e['n_sim']} windows, live {e['n_live']}  contiguous {e['live_contiguous']}  "
               f"declared {e['declared_population']}  in-period {e['live_in_period']}  {'PASS' if e['pass'] else 'FAIL'}")
    out.append(f"{tag} E2 t0 alignment      max |Δt0| {items['E2_t0']['max_abs_dt0_s']:.3f} s ≤ 1 s  {'PASS' if items['E2_t0']['pass'] else 'FAIL'}")
    out.append(f"{tag} E3 t1 alignment      max |Δt1| {items['E3_t1']['max_abs_dt1_s']:.3f} s ≤ 1 s  {'PASS' if items['E3_t1']['pass'] else 'FAIL'}")
    for c in FIELD:
        it = items["W_" + c]
        if "scale_mean_abs_live" not in it:
            out.append(f"{tag} W {c:<18} {it.get('why')}  FAIL"); continue
        b = it["bounds"]
        out.append(f"{tag} W {c:<18} s=mean|live| {it['scale_mean_abs_live']:,.2f}  |e| mean {it['mean_abs_err']:,.2f} "
                   f"({it['mean_abs_err_over_scale']:.3f}·s ≤ {b['m_max']})  p90 {it['p90_abs_err']:,.2f}  max {it['max_abs_err']:,.2f}  "
                   f"e/tol p90 {it['p90_err_over_tol']:.3f} ≤ 1  max {it['max_err_over_tol']:.3f} ≤ {b['t_max']}  "
                   f"({it['n_windows_outside_tol']} outside)  {'PASS' if it['pass'] else 'FAIL'}")
    for k in ("fee", "turnover_over_gross", "funding"):
        it = items["T_" + k]
        if "ratio" not in it:
            out.append(f"{tag} T {k:<18} {it.get('why')}  FAIL"); continue
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
    out.append(f"{tag} VERDICT: {'PASS' if n_pass == len(items) else 'FAIL'} ({n_pass}/{len(items)} items)")
    return out


def check_sim_receipt(doc, label):
    """the sim-side contract; returns a list of violations (empty = acceptable)"""
    bad = []
    if doc.get("version") != "v3":
        bad.append(f"exec_sim version {doc.get('version')!r} != 'v3'")
    if any((doc.get("knobs") or {}).values()):
        bad.append(f"knobs not all off: {doc.get('knobs')}")
    if doc.get("mode") != "live":
        bad.append("mode must be live (the actual protective timeline) for a live comparison")
    seeds = (doc.get("paths") or {}).get("seeds")
    if not seeds or len(seeds) < R_MIN or list(seeds) != list(range(len(seeds))):
        bad.append(f"paths.seeds must be 0..R-1 with R >= {R_MIN}: got {seeds if not seeds else (seeds[0], seeds[-1], len(seeds))}")
    per = doc.get("period") or {}
    if per.get("run_start_anchor") != PERIODS[label]["run_start_anchor"]:
        bad.append(f"run_start_anchor {per.get('run_start_anchor')} != declared {PERIODS[label]['run_start_anchor']}")
    cal = doc.get("calibration") or {}
    cp = os.path.join(L.REPO, cal.get("path", ""))
    if not cal.get("path") or not os.path.exists(cp):
        bad.append("calibration file missing")
    else:
        cj = json.load(open(cp))
        if L.sha_file(cp) != cal.get("sha256"):
            bad.append("calibration sha differs from the receipt")
        if cj.get("frozen_before_holdout") is not True or cj.get("kind") != "v3_pooled":
            bad.append("calibration is not a frozen v3 pooled file")
        if tuple(cj.get("calibration_anchors") or ()) != CALIB_ANCHORS:
            bad.append(f"calibration anchors {cj.get('calibration_anchors')} != declared {CALIB_ANCHORS}")
    ini = doc.get("initial_state_sealed") or {}
    if not ini.get("sha256") or not ini.get("sealed_before_run"):
        bad.append("initial state not sealed before the run")
    return bad


def main_gate(sim_p, label, out_p, mirror):
    M = L.Mirror(mirror)
    L.install_readonly_guard()
    doc = json.load(open(sim_p))
    bad = check_sim_receipt(doc, label)
    assert not bad, f"sim receipt refused by the V1b sim-side contract: {bad}"
    live_w = population(label)
    lt, n_tr = V1.live_turnover(M, live_w)
    p = PERIODS[label]
    sim_w = [w for w in doc["windows"] if p["first_anchor"] <= L.nominal(w["t0"]) <= p["last_anchor"]]
    items = judge_v1b(sim_w, live_w, lt, label=label, declared=population(label))
    lines = verdict_lines(label, items)
    all_pass = all(it["pass"] for it in items.values())
    diag = {"per_window": [{"from": b["from"], "to": b["to"], **{c: {"sim": float(a[FIELD[c]]), "live": (float(t) if c == "turnover" else float(b[FIELD[c]]))}
                                                                 for c in FIELD}} for a, b, t in zip(sim_w, live_w, lt)],
            "window_price_corr": float(np.corrcoef([w["price_trade"] for w in sim_w], [w["price_trade"] for w in live_w])[0, 1]) if len(sim_w) > 2 else None,
            "path_band_coverage": doc.get("path_band_coverage_note")}
    if "windows_path_p05" in doc and "windows_path_p95" in doc:
        cov = collections.Counter()
        lo = [w for w in doc["windows_path_p05"] if p["first_anchor"] <= L.nominal(w["t0"]) <= p["last_anchor"]]
        hi = [w for w in doc["windows_path_p95"] if p["first_anchor"] <= L.nominal(w["t0"]) <= p["last_anchor"]]
        for c in FIELD:
            lv = lt if c == "turnover" else [float(w[FIELD[c]]) for w in live_w]
            cov[c] = sum(1 for a, b, x in zip(lo, hi, lv) if float(a[FIELD[c]]) <= x <= float(b[FIELD[c]])) / max(1, len(lv))
        diag["share_of_windows_live_inside_sim_path_p05_p95"] = dict(cov)
    rec = {"device": "v1b_gate.py", "device_sha256": L.sha_file(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "rerun": "/usr/bin/python3 " + " ".join([os.path.relpath(os.path.abspath(__file__), L.REPO)] + sys.argv[1:]),
           "label": label, "period": PERIODS[label], "bounds": BOUNDS,
           "inputs_sha256": dict(L.input_shas(M), **{os.path.relpath(os.path.abspath(sim_p), L.REPO): L.sha_file(sim_p)}),
           "sim_device_sha256": doc.get("device_sha256"), "calibration": doc.get("calibration"),
           "n_live_trades_in_population": n_tr, "verdict_lines": lines, "all_pass": all_pass, "items": items, "diagnostics": diag}
    with open(out_p + ".part", "w") as fh:
        json.dump(rec, fh, indent=1, default=str)
    os.replace(out_p + ".part", out_p)
    print("\n".join(lines))
    return all_pass


def reviewer_counterexample(shift_t1=7200.0, anti=True):
    """R5-07 reviewer probe, verbatim construction: 24 UTC days × 6 windows, live price ±1000 alternating, fee 1, funding −1,
    turnover 100, gross0 1000; sim = −live price (correlation −1, per-window error 2,000 USD) and every t1 shifted"""
    live = [{"t0": d * 86400 + j * 14400, "t1": d * 86400 + (j + 1) * 14400, "fee": 1, "funding": -1, "turnover": 100, "gross0": 1000,
             "price_trade": 1000 if j % 2 else -1000} for d in range(24) for j in range(6)]
    sim = [dict(w, price_trade=(-w["price_trade"] if anti else w["price_trade"]), t1=w["t1"] + shift_t1) for w in live]
    return sim, live, [100] * len(live)


def selftest(mirror):
    """no simulator involved: judge(live, live) on the CAL population must PASS; the reviewer's counterexample must FAIL V1b
    (and is shown to PASS the old V1); each detector is shown separately. Returns (n_ok, n)."""
    M = L.Mirror(mirror)
    L.install_readonly_guard()
    res = []

    def chk(name, ok, detail):
        res.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)
    live_w = population("CAL")
    lt, _ = V1.live_turnover(M, live_w)
    same = [dict(w, turnover=t) for w, t in zip(live_w, lt)]
    it = judge_v1b(same, live_w, lt, label="CAL", declared=population("CAL"))
    chk("V1b judge(live, live) on the CAL population passes every item", all(x["pass"] for x in it.values()),
        f"{sum(x['pass'] for x in it.values())}/{len(it)} items, {len(live_w)} windows")
    ho = population("HOLDOUT")
    contig = all(abs(a["t1"] - b["t0"]) <= T_ALIGN_S for a, b in zip(ho, ho[1:]))
    chk("HOLDOUT population is well formed (structure only; no hold-out magnitude is printed)", len(ho) > 0 and contig,
        f"{len(ho)} windows, contiguous {contig}")
    sim, live, turn = reviewer_counterexample()
    old = V1.judge([dict(w, t1=w["t1"]) for w in sim], live, turn)
    chk("reviewer counterexample PASSES the old V1 (the defect R5-07 names is real)", all(x["pass"] for x in old.values()),
        {k: v["pass"] for k, v in old.items()})
    it = judge_v1b(sim, live, turn)
    chk("reviewer counterexample (anti-correlated, t1 +2 h) FAILS V1b", not all(x["pass"] for x in it.values()),
        {k: v["pass"] for k, v in it.items()})
    sim2, live2, turn2 = reviewer_counterexample(shift_t1=0.0, anti=True)
    it2 = judge_v1b(sim2, live2, turn2)
    chk("anti-correlated path alone (t1 correct) FAILS the W price item", not it2["W_price_and_trading"]["pass"] and it2["E3_t1"]["pass"],
        f"mean|e|/s {it2['W_price_and_trading']['mean_abs_err_over_scale']:.2f}, e/tol max {it2['W_price_and_trading']['max_err_over_tol']:.2f}")
    sim3, live3, turn3 = reviewer_counterexample(shift_t1=7200.0, anti=False)
    it3 = judge_v1b(sim3, live3, turn3)
    chk("t1 shift alone (prices identical) FAILS E3", not it3["E3_t1"]["pass"] and it3["W_price_and_trading"]["pass"],
        f"max |Δt1| {it3['E3_t1']['max_abs_dt1_s']:.0f} s")
    it4 = judge_v1b(same[:-1], live_w, lt, label="CAL", declared=population("CAL"))
    chk("dropping one window FAILS E1", not it4["E1_population"]["pass"], it4["E1_population"])
    it5 = judge_v1b(same[1:], live_w[1:], lt[1:], label="CAL", declared=population("CAL"))
    chk("handing in a trimmed live list FAILS E1 (population identity)", not it5["E1_population"]["pass"], it5["E1_population"])
    for c, f in (("fee", 1.4), ("funding", 1.4), ("turnover", 1.4)):
        m = [dict(w, **{FIELD[c]: w[FIELD[c]] * f}) for w in same]
        it6 = judge_v1b(m, live_w, lt, label="CAL", declared=population("CAL"))
        chk(f"{c} ×{f} in every window FAILS W_{c}", not it6["W_" + c]["pass"], f"mean|e|/s {it6['W_' + c]['mean_abs_err_over_scale']:.3f}")
    s = np.mean([abs(w["price_trade"]) for w in live_w])
    m = [dict(w, price_trade=w["price_trade"] + (1.0 if k % 2 else -1.0) * 2.0 * s) for k, w in enumerate(same)]
    it7 = judge_v1b(m, live_w, lt, label="CAL", declared=population("CAL"))
    chk("±2·s alternating price error on the real CAL windows (largely cancels within each UTC day) FAILS W price", not it7["W_price_and_trading"]["pass"],
        f"mean|e|/s {it7['W_price_and_trading']['mean_abs_err_over_scale']:.2f}; T price {it7['T_price_and_trading']['pass']}")
    n_ok = sum(res)
    print(f"V1b SELFTEST: {'ALL PASS' if n_ok == len(res) else 'FAILURES'} {n_ok}/{len(res)} checks")
    return n_ok, len(res)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        n_ok, n = selftest(sys.argv[2] if len(sys.argv) > 2 else L.MIRROR_DEFAULT)
        sys.exit(0 if n_ok == n else 1)
    ok = main_gate(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else L.MIRROR_DEFAULT)
    sys.exit(0 if ok else 1)
