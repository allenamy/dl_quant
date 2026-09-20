#!/usr/bin/env python3
"""bt_p2_reading_test.py — test of bt_p2_reading.py (reading P2, AMENDMENT 3) on FIXTURES ONLY: hand-built PATH npz/json files whose day-stop
flattens, returns and halt points are known by construction. No run output is read. Baselines green first, every mutation red, exit 0 only then.

  U0  the withholding window: with H = 12 h, exactly the anchors in [t, t + 12 h) after a flatten at t are withheld, the resume anchor is the
      first one at or after t + 12 h, and the withheld anchors contribute exactly 0 to the compounded return (checked against a hand-built
      reference series, not against the device's own arithmetic)
  U1  H = "never": every anchor from the first flatten on is withheld ⇒ the path's window-end return equals its cumulative return at that
      flatten (the strict lower bound the review asks for)
  U2  H = "sim": P2 reproduces the published reading P on the same fixture — the same halt anchor and the same window-end return (cross-device
      equality, so P2 cannot silently drift from P)
  U3  §4-4 still bites under P2: a fixture that keeps falling after its day-stop halts at the first window end below −25 %, and the P2 end
      return is that cumulative value
  U4  monotonicity: a longer H never withholds fewer anchors
  U5  flatten costs are reported per flatten window (turnover over gross, window fee in bps of gross)
  mutations (must go red): a withheld anchor that still contributes its return; H = 8 h vs 20 h giving the same answer on a fixture where the
      windows differ; the sha of a path npz changed after its json was written
usage: /usr/bin/python3 bt_p2_reading_test.py <scratch_dir> <out.json>
"""
import os, sys, json, time, shutil

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_p_reading as PR
import bt_p2_reading as P2

T0 = time.time(); SCR, OUTP = sys.argv[1], sys.argv[2]
assert "/runs/" not in os.path.abspath(SCR), "fixtures never go into a run directory"
shutil.rmtree(SCR, ignore_errors=True); os.makedirs(SCR, exist_ok=True)
RES = []
H4 = 14400
A0 = PR.ts("2024-01-01T00:00:00Z")


def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail)); print(("PASS " if cond else "FAIL ") + name, json.dumps(detail, default=str)[:260] if detail is not None else "", flush=True)


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


def cfg_for(dirs, h_main=12, sens=(8, 20), starts=("2024-01-01T00:00:00Z",), base="2024-01-01T00:00:00Z", n=2, thr=-0.25):
    c = {"paths_R": n, "pins": {"prereg_amendment_2": {"sha256": "fixture"}, "prereg_amendment_3": {"sha256": "fixture", "doc": "AMENDMENT 3"}},
         "p_reading": {"threshold_cum_return": thr, "caliber": "fixture", "halt_semantics": "fixture", "breach_by": "2026-08-31T00:00:00Z",
                       "starts": list(starts), "bases": [{"label": "base", "anchor": base}]},
         "p2_reading": {"resume_hours_main": h_main, "resume_hours_sensitivity": list(sens), "include_sim_rule": True, "include_never": True},
         "runs": [{"label": os.path.basename(d), "dir": d} for d in dirs]}
    p = os.path.join(SCR, "p2_cfg_%d.json" % int(time.time() * 1e6 % 1e9)); json.dump(c, open(p, "w"), indent=1)
    return p


# a 40-window fixture: a flatten at window 10's end, then steady returns
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
p0 = B["12"]["per_path"][0]
ok("U0.withheld_anchors_are_exactly_the_window_[t, t+H)", p0["anchors_withheld_by_day_stop"] == int(w_ref.sum()) == 3,
   {"device": p0["anchors_withheld_by_day_stop"], "reference": int(w_ref.sum())})
ok("U0.end_return_matches_a_hand_built_reference_series", abs(p0["end_return_P2"] - ref_end) < 1e-12, {"device": p0["end_return_P2"], "reference": ref_end})
ok("U0.a_path_without_a_flatten_is_untouched", B["12"]["per_path"][1]["anchors_withheld_by_day_stop"] == 0 and
   abs(B["12"]["per_path"][1]["end_return_P2"] - (np.prod(1 + r_b) - 1)) < 1e-12, B["12"]["per_path"][1])
mut("a withheld anchor that still contributes its return is a different number", abs(ref_end - (np.prod(1 + r_a) - 1)) > 1e-6,
    {"withheld": ref_end, "not_withheld": float(np.prod(1 + r_a) - 1)})
nev = B["never"]["per_path"][0]
ok("U1.never_resumes_ends_the_path_at_the_first_flatten", abs(nev["end_return_P2"] - (np.prod(1.0 + r_a[:11]) - 1.0)) < 1e-12,
   {"device": nev["end_return_P2"], "reference": float(np.prod(1.0 + r_a[:11]) - 1.0), "withheld": nev["anchors_withheld_by_day_stop"]})
sim = B["sim"]["per_path"][0]
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
c12 = o2["runs"]["FIX_P2_FALL"]["bases"]["base @ 2024-01-01T00:00:00Z"]["12"]["per_path"][0]
ok("U3.cum25_still_halts_under_P2", c12["fired_cum25"] and c12["end_return_P2"] < -0.25 and abs(c12["end_return_P2"] - c12["cum_at_cum25"]) < 1e-15, c12)
# U4 / U5
w8 = o1["runs"]["FIX_P2"]["bases"]["base @ 2024-01-01T00:00:00Z"]["8"]["per_path"][0]["anchors_withheld_by_day_stop"]
w20 = o1["runs"]["FIX_P2"]["bases"]["base @ 2024-01-01T00:00:00Z"]["20"]["per_path"][0]["anchors_withheld_by_day_stop"]
ok("U4.a_longer_resume_delay_never_withholds_fewer_anchors", w8 <= p0["anchors_withheld_by_day_stop"] <= w20, {"8h": w8, "12h": p0["anchors_withheld_by_day_stop"], "20h": w20})
mut("8 h and 20 h differ on this fixture (otherwise the sensitivity is vacuous)", w8 != w20, {"8h": w8, "20h": w20})
fc = o1["runs"]["FIX_P2"]["flatten_costs_per_path"]
i_flat = int(np.searchsorted(A_fix, t_flat, "right")) - 1                      # the fixture's own NAV at that window sets the denominator
nav_at = 100000.0 * float(np.prod(1.0 + r_a[:i_flat])) if i_flat else 100000.0   # (try 1 of this test used 0.15, i.e. NAV still at its initial value)
ok("U5.flatten_costs_reported_per_event", fc["example_path_seed00"]
   and abs(fc["example_path_seed00"][0]["turnover_flatten_over_gross"] - 30000.0 / (2.0 * nav_at)) < 1e-9
   and abs(fc["example_path_seed00"][0]["window_fee_bps_of_gross"] - 1e4 * 12.0 / (2.0 * nav_at)) < 1e-9,
   {"device": fc["example_path_seed00"][:1], "reference_turnover": 30000.0 / (2.0 * nav_at)})
d3 = write_run("FIX_P2_TAMPER", [r_a, r_b], [[t_flat], []], tamper=True)
try:
    P2.run(cfg_for([d3]), os.path.join(SCR, "o3.json")); red = False; msg = "no error"
except P2.P2Error as e:
    red = "npz sha" in str(e); msg = str(e)[:120]
mut("a path npz changed after its json was written is refused", red, msg)

fails = [r["check"] for r in RES if not r["ok"]]
out = dict(device="bt_p2_reading_test.py", self_sha256=PR.sha(os.path.abspath(__file__)), tested=PR.sha(os.path.join(HERE, "bt_p2_reading.py")),
           argv=sys.argv, numpy=np.__version__, checks=RES, failed=fails, VERDICT="PASS" if not fails else "RED", runtime_s=round(time.time() - T0, 1))
json.dump(out, open(OUTP, "w"), indent=1, default=str)
print("BT_P2_READING_TEST VERDICT: " + ("ALL PASS %d/%d checks (baselines green, every mutation red)" % (len(RES), len(RES)) if not fails else "FAILURES %d/%d: %s" % (len(fails), len(RES), fails)), flush=True)
sys.exit(0 if not fails else 3)
