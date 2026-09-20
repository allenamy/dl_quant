#!/usr/bin/env python3
"""bt_p2_reading_test.py — test of bt_p2_reading.py (reading P2, AMENDMENT 3 + AMENDMENT 4) on FIXTURES ONLY: hand-built PATH npz/json
files whose day-stop flattens, returns and halt points are known by construction. No run output is read. Baselines green first, every
mutation red, exit 0 only then.

  U0  the withholding window: with H = 12 h, exactly the anchors in [t, t + 12 h) after a flatten at t are withheld, the resume anchor is
      the first one at or after t + 12 h, and the withheld anchors contribute exactly 0 to the compounded return (checked against a
      hand-built reference series, not against the device's own arithmetic)
  U1  H = "never": every anchor from the first IN-SCOPE flatten on is withheld ⇒ the path's window-end return equals its cumulative
      return at that flatten (the strict lower bound the review asks for)
  U2  H = "sim": P2 reproduces the published reading P on the same fixture — the same halt anchor and the same window-end return
      (cross-device equality, so P2 cannot silently drift from P)
  U3  §4-4 still bites under P2: a fixture that keeps falling after its day-stop halts at the first window end below −25 %
  U4  monotonicity: a longer H never withholds fewer anchors
  U5  flatten costs are reported per flatten window, and the BY_BASE scope counts only the events inside that base's window
      (AMENDMENT 4 §B-5: the pre-fix device walked the whole path while the doc quoted the number as a window fact)

  AMENDMENT 4 cases, on a fixture built so that one path's ONLY day-stop happens BEFORE the reporting base — the E-0920-C shape:
  W1  W_CARRY: that path traded no anchor of the window ⇒ has_measurement is False, end_return_P2 is None (NOT 0.0) and the device
      NAMES the reason
  W2  W_CARRY summary: the headline `measured` mean excludes it and equals the hand-built mean of the paths that did trade; the named
      subset lists its seed; `whole_population` still reports the pre-fix number under its named convention, and the gap between the
      two is the size of the defect
  W3  W_ENTRY (the main reading): the same path DOES have a measurement, equal to a hand-built reference, because a halt that began
      before the window is not inherited
  W4  a path whose day-stop is INSIDE the window is identical under both semantics — so W1–W3 are about pre-window halts, not about a
      device that changed everywhere
  W5  B4-a / B4-b: at a base that is the path start, and at H = "sim", the two semantics agree bit for bit (the device asserts this
      itself and refuses otherwise; here the receipt's own assertion list is checked)
  W6  the structural sweep really ran on the emitted document, and every persisted mean carries n_eff

  mutations (must go red): a withheld anchor that still contributes its return; H = 8 h vs 20 h giving the same answer on a fixture
      where the windows differ; the sha of a path npz changed after its json was written; an unmeasured member that still carries a
      value (A5); a document with an aggregate that has no n_eff beside it (A4, injected into the real device output)
usage: /usr/bin/python3 bt_p2_reading_test.py <scratch_dir> <out.json>
"""
import os, sys, json, time, shutil

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_p_reading as PR
import bt_p2_reading as P2
import bt_agg as AG

T0 = time.time(); SCR, OUTP = sys.argv[1], sys.argv[2]
assert "/runs/" not in os.path.abspath(SCR), "fixtures never go into a run directory"
shutil.rmtree(SCR, ignore_errors=True); os.makedirs(SCR, exist_ok=True)
RES = []
H4 = 14400
A0 = PR.ts("2024-01-01T00:00:00Z")


def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail)); print(("PASS " if cond else "FAIL ") + name, json.dumps(detail, default=str)[:300] if detail is not None else "", flush=True)


def mut(name, red, detail=None): ok("[mutation red] " + name, red, detail)


def write_run(dirname, series, flattens, tamper=False):
    """series: per-path list of per-window returns; flattens: per-path list of flatten times (epoch)"""
    d = os.path.join(SCR, dirname); os.makedirs(d, exist_ok=True); tag = dirname
    n = len(series[0])
    for s, (rr, fl) in enumerate(zip(series, flattens)):
        A = np.arange(A0, A0 + H4 * n, H4, dtype=np.int64)
        navm1 = 100000.0 * np.cumprod(1.0 + np.asarray(rr, float)); navm0 = np.concatenate([[100000.0], navm1[:-1]])
        tf = np.zeros(n); fee = np.zeros(n)
        for t in fl:
            i = int(np.searchsorted(A, t, "right")) - 1
            if 0 <= i < n: tf[i] = 30000.0; fee[i] = 12.0
        st = os.path.join(d, f"PATH_{tag}_seed_{s:02d}")
        np.savez(st + ".npz", A=A, navm0=navm0, navm1=navm1, nav0=navm0.copy(), nav1=navm1.copy(), status=np.zeros(n, np.int8),
                 turnover_flatten=tf, fee=fee, gross0=2.0 * navm0)
        J = {"seed": s, "npz_sha256": PR.sha(st + ".npz"), "flatten_log": [[PR.iso(t), "§4-2 fixture"] for t in fl]}
        if tamper and s == 0:
            Z = dict(np.load(st + ".npz")); Z["navm1"] = Z["navm1"] * 1.01; np.savez(st + ".npz", **Z)
        json.dump(J, open(st + ".json", "w"))
    return d


def cfg_for(dirs, h_main=12, sens=(8, 20), starts=("2024-01-01T00:00:00Z",), bases=(("base", "2024-01-01T00:00:00Z"),), n=2, thr=-0.25):
    c = {"paths_R": n, "pins": {"prereg_amendment_2": {"sha256": "fixture"}, "prereg_amendment_3": {"sha256": "fixture", "doc": "AMENDMENT 3"}},
         "p_reading": {"threshold_cum_return": thr, "caliber": "fixture", "halt_semantics": "fixture", "breach_by": "2026-08-31T00:00:00Z",
                       "starts": list(starts), "bases": [{"label": l, "anchor": a} for l, a in bases]},
         "p2_reading": {"resume_hours_main": h_main, "resume_hours_sensitivity": list(sens), "include_sim_rule": True, "include_never": True},
         "runs": [{"label": os.path.basename(d), "dir": d} for d in dirs]}
    p = os.path.join(SCR, "p2_cfg_%d.json" % int(time.time() * 1e6 % 1e9)); json.dump(c, open(p, "w"), indent=1)
    return p


def E(cell, sem="W_ENTRY"): return cell[sem]


# ================================================================ a 40-window fixture: a flatten at window 10's end, then steady returns
n = 40
r_a = np.full(n, 0.01); r_a[12] = -0.05
r_b = np.full(n, 0.005)
t_flat = A0 + H4 * 10 + 3600                                  # inside window 10
d1 = write_run("FIX_P2", [r_a, r_b], [[t_flat], []])
o1 = P2.run(cfg_for([d1]), os.path.join(SCR, "o1.json"))
B = o1["runs"]["FIX_P2"]["bases"]["base @ 2024-01-01T00:00:00Z"]
A_fix = np.arange(A0, A0 + H4 * n, H4, dtype=np.int64)
w_ref = (A_fix >= t_flat) & (A_fix < t_flat + 12 * 3600)
ref_end = float(np.prod(1.0 + np.where(w_ref, 0.0, r_a)) - 1.0)
p0 = E(B["12"])["per_path"][0]
ok("U0.withheld_anchors_are_exactly_the_window_[t, t+H)", p0["anchors_withheld_by_day_stop"] == int(w_ref.sum()) == 3,
   {"device": p0["anchors_withheld_by_day_stop"], "reference": int(w_ref.sum())})
ok("U0.end_return_matches_a_hand_built_reference_series", abs(p0["end_return_P2"] - ref_end) < 1e-12, {"device": p0["end_return_P2"], "reference": ref_end})
ok("U0.a_path_without_a_flatten_is_untouched", E(B["12"])["per_path"][1]["anchors_withheld_by_day_stop"] == 0 and
   abs(E(B["12"])["per_path"][1]["end_return_P2"] - (np.prod(1 + r_b) - 1)) < 1e-12, E(B["12"])["per_path"][1])
mut("a withheld anchor that still contributes its return is a different number", abs(ref_end - (np.prod(1 + r_a) - 1)) > 1e-6,
    {"withheld": ref_end, "not_withheld": float(np.prod(1 + r_a) - 1)})
nev = E(B["never"])["per_path"][0]
ok("U1.never_resumes_ends_the_path_at_the_first_flatten", abs(nev["end_return_P2"] - (np.prod(1.0 + r_a[:11]) - 1.0)) < 1e-12,
   {"device": nev["end_return_P2"], "reference": float(np.prod(1.0 + r_a[:11]) - 1.0), "withheld": nev["anchors_withheld_by_day_stop"]})
sim = E(B["sim"])["per_path"][0]
ok("U2.H=sim_withholds_nothing_extra", sim["anchors_withheld_by_day_stop"] == 0 and abs(sim["end_return_P2"] - (np.prod(1 + r_a) - 1)) < 1e-12, sim)
pcfg = json.load(open(cfg_for([d1])))                          # the same fixture through the PUBLISHED P device
pp = os.path.join(SCR, "p_cfg_cross.json"); json.dump({k: v for k, v in pcfg.items() if k != "p2_reading"}, open(pp, "w"), indent=1)
oP = PR.run(pp, os.path.join(SCR, "oP.json"))
bP = oP["runs"]["FIX_P2"]["bases"]["base @ 2024-01-01T00:00:00Z"]["per_path"][0]
ok("U2.P2_with_H=sim_equals_the_published_reading_P (cross-device)", abs(sim["end_return_P2"] - bP["end_return_phalt"]) < 1e-12 and sim["fired_cum25"] == bP["fired"],
   {"P2": sim["end_return_P2"], "P": bP["end_return_phalt"]})
# U3: a fixture that keeps falling after its day-stop
r_c = np.concatenate([np.full(11, -0.01), np.full(n - 11, -0.02)])
d2 = write_run("FIX_P2_FALL", [r_c, r_c], [[t_flat], [t_flat]])
o2 = P2.run(cfg_for([d2]), os.path.join(SCR, "o2.json"))
c12 = E(o2["runs"]["FIX_P2_FALL"]["bases"]["base @ 2024-01-01T00:00:00Z"]["12"])["per_path"][0]
ok("U3.cum25_still_halts_under_P2", c12["fired_cum25"] and c12["end_return_P2"] < -0.25 and abs(c12["end_return_P2"] - c12["cum_at_cum25"]) < 1e-15, c12)
# U4 / U5
w8 = E(B["8"])["per_path"][0]["anchors_withheld_by_day_stop"]
w20 = E(B["20"])["per_path"][0]["anchors_withheld_by_day_stop"]
ok("U4.a_longer_resume_delay_never_withholds_fewer_anchors", w8 <= p0["anchors_withheld_by_day_stop"] <= w20, {"8h": w8, "12h": p0["anchors_withheld_by_day_stop"], "20h": w20})
mut("8 h and 20 h differ on this fixture (otherwise the sensitivity is vacuous)", w8 != w20, {"8h": w8, "20h": w20})
fc = o1["runs"]["FIX_P2"]["flatten_costs_per_path_WHOLE_PATH"]
i_flat = int(np.searchsorted(A_fix, t_flat, "right")) - 1                      # the fixture's own NAV at that window sets the denominator
nav_at = 100000.0 * float(np.prod(1.0 + r_a[:i_flat])) if i_flat else 100000.0   # (try 1 of this test used 0.15, i.e. NAV still at its initial value)
ok("U5.flatten_costs_reported_per_event", fc["example_path_seed00"]
   and abs(fc["example_path_seed00"][0]["turnover_flatten_over_gross"] - 30000.0 / (2.0 * nav_at)) < 1e-9
   and abs(fc["example_path_seed00"][0]["window_fee_bps_of_gross"] - 1e4 * 12.0 / (2.0 * nav_at)) < 1e-9,
   {"device": fc["example_path_seed00"][:1], "reference_turnover": 30000.0 / (2.0 * nav_at)})
ok("U5.the path with no flatten is a NAMED subset of the cost aggregate, not a member a comprehension dropped",
   fc["turnover_flatten_over_gross"]["population"]["n"] == 2 and fc["turnover_flatten_over_gross"]["measured"]["n_eff"] == 1
   and fc["turnover_flatten_over_gross"]["no_measurement"]["by_reason"][P2.NO_FLATTEN]["members"] == [1],
   {"population_n": fc["turnover_flatten_over_gross"]["population"]["n"], "n_eff": fc["turnover_flatten_over_gross"]["measured"]["n_eff"],
    "named": list(fc["turnover_flatten_over_gross"]["no_measurement"]["by_reason"])})

# ================================================================ AMENDMENT 4: the E-0920-C shape, built on purpose
# path 0: its ONLY day-stop is at window 2 — BEFORE the reporting base at index 12.  path 1: its day-stop is at window 20 — INSIDE it.
# path 2: no day-stop at all.
r0 = np.full(n, -0.004); r1 = np.full(n, -0.006); r2v = np.full(n, 0.002)
t_pre = A0 + H4 * 2 + 3600
t_in = A0 + H4 * 20 + 3600
BASE_I = 12
d4 = write_run("FIX_P2_PREWIN", [r0, r1, r2v], [[t_pre], [t_in], []])
cfg4 = cfg_for([d4], n=3, bases=(("path start", "2024-01-01T00:00:00Z"), ("mid", PR.iso(A0 + H4 * BASE_I))))
o4 = P2.run(cfg4, os.path.join(SCR, "o4.json"))
R4 = o4["runs"]["FIX_P2_PREWIN"]
MID = R4["bases"]["mid @ " + PR.iso(A0 + H4 * BASE_I)]
carry0 = MID["never"]["W_CARRY"]["per_path"][0]
entry0 = MID["never"]["W_ENTRY"]["per_path"][0]
ok("W1.W_CARRY: a path halted BEFORE the window has NO window-end return — None, not 0.0 (this is E-0920-C)",
   carry0["has_measurement"] is False and carry0["end_return_P2"] is None and carry0["anchors_traded_in_window"] == 0
   and "no anchor of this window was ever traded" in (carry0["no_measurement_reason"] or ""),
   {"end_return_P2": carry0["end_return_P2"], "reason": carry0["no_measurement_reason"]})
sC = MID["never"]["W_CARRY"]["summary"]["end_return_P2"]
meas_ref = float(np.mean([MID["never"]["W_CARRY"]["per_path"][i]["end_return_P2"] for i in (1, 2)]))
ok("W2.W_CARRY summary: the headline mean is over the paths that traded, and equals a hand-built mean of exactly those",
   sC["measured"]["n_eff"] == 2 and abs(sC["measured"]["mean"] - meas_ref) < 1e-15 and sC["population"]["n"] == 3,
   {"measured_mean": sC["measured"]["mean"], "hand_built": meas_ref, "n_eff": sC["measured"]["n_eff"], "population_n": sC["population"]["n"]})
ok("W2.W_CARRY summary: the unmeasured path is NAMED and listed by seed",
   sC["no_measurement"]["n"] == 1 and list(sC["no_measurement"]["by_reason"].values())[0]["members"] == [0], sC["no_measurement"])
old_style = float(np.mean([0.0] + [MID["never"]["W_CARRY"]["per_path"][i]["end_return_P2"] for i in (1, 2)]))
ok("W2.W_CARRY summary: whole_population still reports the PRE-FIX number, under its named convention — the old figure is not hidden",
   abs(sC["whole_population"]["mean"] - old_style) < 1e-15 and sC["whole_population"]["equals_measured"] is False
   and sC["whole_population"]["n_eff"] == 3 and "flat-book" in sC["whole_population"]["convention"],
   {"whole_population": sC["whole_population"]["mean"], "pre_fix_arithmetic": old_style, "measured": sC["measured"]["mean"],
    "gap_pp": 100 * (sC["whole_population"]["mean"] - sC["measured"]["mean"])})
ok("W2.the two figures actually differ on this fixture (otherwise W2 would be vacuous)",
   abs(sC["whole_population"]["mean"] - sC["measured"]["mean"]) > 1e-6,
   {"gap_pp": 100 * (sC["whole_population"]["mean"] - sC["measured"]["mean"])})
entry_ref = float(np.prod(1.0 + r0[BASE_I:]) - 1.0)              # no in-scope flatten at all ⇒ nothing withheld
ok("W3.W_ENTRY (main): the same path DOES have a measurement — a halt that began before the window is not inherited",
   entry0["has_measurement"] is True and abs(entry0["end_return_P2"] - entry_ref) < 1e-12 and entry0["anchors_withheld_by_day_stop"] == 0,
   {"device": entry0["end_return_P2"], "hand_built": entry_ref})
ok("W3.W_ENTRY summary has no unmeasured member on this fixture, so its whole_population equals its measured figure",
   MID["never"]["W_ENTRY"]["summary"]["end_return_P2"]["no_measurement"]["n"] == 0
   and MID["never"]["W_ENTRY"]["summary"]["end_return_P2"]["whole_population"]["equals_measured"] is True,
   MID["never"]["W_ENTRY"]["summary"]["end_return_P2"]["measured"])
ok("W4.a path whose day-stop is INSIDE the window is identical under both semantics (the change is about pre-window halts only)",
   MID["never"]["W_ENTRY"]["per_path"][1]["end_return_P2"] == MID["never"]["W_CARRY"]["per_path"][1]["end_return_P2"]
   and MID["never"]["W_ENTRY"]["per_path"][2]["end_return_P2"] == MID["never"]["W_CARRY"]["per_path"][2]["end_return_P2"],
   {"seed1": MID["never"]["W_ENTRY"]["per_path"][1]["end_return_P2"], "seed2": MID["never"]["W_ENTRY"]["per_path"][2]["end_return_P2"]})
a_start = [a for a in o4["assertions"] if a["base_index"] == 0]
a_sim = [a for a in o4["assertions"] if a["H"] == "sim"]
ok("W5.B4-a: at the base that IS the path start, the two semantics agree bit for bit on every H",
   len(a_start) == 5 and all(a["W_ENTRY_equals_W_CARRY"] for a in a_start), {"n": len(a_start)})
ok("W5.B4-b: at H='sim' the two semantics agree bit for bit on every base",
   len(a_sim) == 2 and all(a["W_ENTRY_equals_W_CARRY"] for a in a_sim), {"n": len(a_sim)})
ok("W5.B4 is not vacuous: at the mid base under H='never' the two semantics DISAGREE on this fixture",
   any(a["base_index"] != 0 and a["H"] == "never" and not a["W_ENTRY_equals_W_CARRY"] for a in o4["assertions"]),
   [a for a in o4["assertions"] if a["H"] == "never"])
sw = o4["aggregation_contract"]["sweep"]
ok("W6.the structural sweep ran on the emitted document and found aggregates to inspect",
   sw["violations"] == 0 and sw["aggregate_blocks_swept"] >= 2 * sw["min_blocks_required"] // 2 and sw["aggregate_blocks_swept"] > 20, sw)
ok("W6.every persisted mean in the real device output carries n_eff (re-swept here, independently of the device's own call)",
   AG.sweep_or_refuse(json.load(open(os.path.join(SCR, "o4.json"))), min_blocks=20)["violations"] == 0,
   AG.sweep_or_refuse(json.load(open(os.path.join(SCR, "o4.json"))), min_blocks=20))

# ================================================================ mutations
d3 = write_run("FIX_P2_TAMPER", [r_a, r_b], [[t_flat], []], tamper=True)
try:
    P2.run(cfg_for([d3]), os.path.join(SCR, "o3.json")); red = False; msg = "no error"
except P2.P2Error as e:
    red = "npz sha" in str(e); msg = str(e)[:120]
mut("a path npz changed after its json was written is refused", red, msg)
try:
    AG.block("x", [{"s": 0, "v": -0.25}], lambda m: m["v"], lambda m: P2.NOT_TRADED, population_name="p", id_of=lambda m: m["s"])
    red5 = False; msg5 = "no error"
except AG.AggRefusal as e:
    red5 = "(A5)" in str(e); msg5 = str(e)[:160]
mut("a member named 'traded nothing' that still carries a value is refused (A5)", red5, msg5)
doc = json.load(open(os.path.join(SCR, "o4.json")))
doc["someone_adds_this_next_week"] = {"mean": 0.0, "median": 0.0}
try:
    AG.sweep_or_refuse(doc, min_blocks=20); red6 = False; msg6 = "no error"
except AG.AggRefusal as e:
    red6 = "someone_adds_this_next_week" in str(e); msg6 = str(e)[:200]
mut("an aggregate added to the REAL device output tomorrow, with no n_eff beside it, is refused by the sweep", red6, msg6)

fails = [r["check"] for r in RES if not r["ok"]]
out = dict(device="bt_p2_reading_test.py", self_sha256=PR.sha(os.path.abspath(__file__)), tested=PR.sha(os.path.join(HERE, "bt_p2_reading.py")),
           tested_bt_agg=PR.sha(os.path.join(HERE, "bt_agg.py")),
           argv=sys.argv, numpy=np.__version__, checks=RES, failed=fails, VERDICT="PASS" if not fails else "RED", runtime_s=round(time.time() - T0, 1))
json.dump(out, open(OUTP, "w"), indent=1, default=str)
print("BT_P2_READING_TEST VERDICT: " + ("ALL PASS %d/%d checks (baselines green, every mutation red)" % (len(RES), len(RES)) if not fails else "FAILURES %d/%d: %s" % (len(fails), len(RES), fails)), flush=True)
sys.exit(0 if not fails else 3)
