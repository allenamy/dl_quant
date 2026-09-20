#!/usr/bin/env python3
"""bt_p_reading_test.py — test of bt_p_reading.py (reading P, AMENDMENT 2) on FIXTURES ONLY: hand-built PATH npz/json files with NAV series
whose halt points are known by construction. No run output is read. Every baseline must be green and every mutation red; exit 0 only then.

  T0  a path that touches EXACTLY −25.00 % does NOT halt there (the rule is strictly below), and halts at the next anchor that is below it;
      its P-halt window-end return equals the cumulative return at the halt even though the no-halt path recovers afterwards
  T1  a path that never goes below the line does not fire, and its two calibers give the same window-end return
  T2  the base matters: the same series based at a later anchor (higher starting equity ⇒ deeper cumulative loss) halts earlier
  T3  breach_by: a breach after the breach_by date is not counted as a breach by that date, but is still visible in the window-end block
  T4  the per-path spread: fired_paths / percentiles over a mixed set of paths
  T5  named refusals: a base or a start that is not an anchor; a PATH npz whose sha does not match its json; paths with different axes
  mutations (must go red): the threshold moved to −24.99 % turns the exactly-on-the-line anchor into a halt; a NAV cell edited after the
      json was written is refused by the sha check; the recovery after the halt leaking into the P-halt end return
usage: /usr/bin/python3 bt_p_reading_test.py <scratch_dir> <out.json>
"""
import os, sys, json, time, hashlib, shutil

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_p_reading as PR

T0 = time.time(); SCR, OUTP = sys.argv[1], sys.argv[2]
assert "runs" not in os.path.abspath(SCR).split(os.sep), "fixtures never go into a run directory"
shutil.rmtree(SCR, ignore_errors=True); os.makedirs(SCR, exist_ok=True)
RES = []
H4 = 14400
A0 = PR.ts("2023-01-01T00:00:00Z")


def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail)); print(("PASS " if cond else "FAIL ") + name, json.dumps(detail, default=str)[:260] if detail is not None else "", flush=True)


def mut(name, red, detail=None): ok("[mutation red] " + name, red, detail)


def write_run(dirname, series, tamper_npz=False, axis_shift=None):
    """series: list of per-path lists of cumulative returns from the first anchor (one value per window end)"""
    d = os.path.join(SCR, dirname); os.makedirs(d, exist_ok=True); tag = dirname
    n = len(series[0])
    for s, cum in enumerate(series):
        A = np.arange(A0, A0 + H4 * n, H4, dtype=np.int64)
        if axis_shift and s == 1: A = A + H4
        navm1 = 100000.0 * (1.0 + np.asarray(cum, float)); navm0 = np.concatenate([[100000.0], navm1[:-1]])
        st = os.path.join(d, f"PATH_{tag}_seed_{s:02d}")
        np.savez(st + ".npz", A=A, navm0=navm0, navm1=navm1)
        J = {"seed": s, "npz_sha256": PR.sha(st + ".npz")}
        if tamper_npz and s == 0:                       # edit the npz AFTER the json recorded its sha
            Z = dict(np.load(st + ".npz")); Z["navm1"][0] *= 1.0001; np.savez(st + ".npz", **Z)
        json.dump(J, open(st + ".json", "w"))
    return d


def cfg_for(dirs, starts, bases, breach_by="2026-08-31T00:00:00Z", threshold=-0.25, n=None):
    c = {"paths_R": n, "pins": {"prereg_amendment_2": {"sha256": "52ae1969522d8620" + "0" * 48, "doc": "fixture"}},
         "p_reading": {"threshold_cum_return": threshold, "caliber": "cumulative return from starting equity (live watchdog §4-4)",
                       "breach_by": breach_by, "starts": starts, "bases": bases},
         "runs": [{"label": os.path.basename(d), "dir": d} for d in dirs]}
    p = os.path.join(SCR, "p_cfg_%d.json" % int(time.time() * 1e6 % 1e9)); json.dump(c, open(p, "w"), indent=1)
    return p


# T0 / T1: exactly on the line, then below, then recovery — and a path that never breaches
cum_a = [0.0, -0.10, -0.18, -0.22, -0.24, -0.2500, -0.24, -0.2501, -0.10, +0.50]
cum_b = [0.0, -0.05, -0.10, -0.15, -0.20, -0.2400, -0.20, -0.1000, +0.10, +0.30]
d1 = write_run("FIX_ONE", [cum_a, cum_b])
cfg1 = cfg_for([d1], ["2023-01-01T00:00:00Z"], [{"label": "window start", "anchor": "2023-01-01T00:00:00Z"}], n=2)
o1 = PR.run(cfg1, os.path.join(SCR, "out1.json"))
b1 = o1["runs"]["FIX_ONE"]["bases"]["window start @ 2023-01-01T00:00:00Z"]["per_path"]
ok("T0.exactly_-25.00pct_is_not_a_halt_and_the_next_lower_anchor_is", b1[0]["fired"] and b1[0]["halt_index"] == 7 and abs(b1[0]["cum_at_halt"] + 0.2501) < 1e-12, b1[0])
ok("T0.P-halt_end_return_is_the_return_at_the_halt_not_the_recovery", abs(b1[0]["end_return_phalt"] + 0.2501) < 1e-12 and abs(b1[0]["end_return_nohalt"] - 0.50) < 1e-12, b1[0])
ok("T0.anchors_after_halt_counted", b1[0]["anchors_after_halt"] == 2 and abs(b1[0]["share_anchors_after_halt"] - 0.2) < 1e-12, b1[0])
ok("T1.no_breach_path_does_not_fire_and_both_calibers_agree", (not b1[1]["fired"]) and b1[1]["end_return_phalt"] == b1[1]["end_return_nohalt"]
   and abs(b1[1]["end_return_nohalt"] - 0.30) < 1e-12, b1[1])          # try 1 of this test compared the float to 0.30 exactly and went red on 0.30000000000000004
ok("T4.spread_block", o1["runs"]["FIX_ONE"]["bases"]["window start @ 2023-01-01T00:00:00Z"]["summary"]["fired_paths"] == 1
   and o1["runs"]["FIX_ONE"]["bases"]["window start @ 2023-01-01T00:00:00Z"]["summary"]["n_paths"] == 2,
   o1["runs"]["FIX_ONE"]["bases"]["window start @ 2023-01-01T00:00:00Z"]["summary"])

# T2: a later base (starting equity at that anchor) halts earlier on the same series
base2 = PR.iso(A0 + 4 * H4)
cfg2 = cfg_for([d1], ["2023-01-01T00:00:00Z"], [{"label": "window start", "anchor": "2023-01-01T00:00:00Z"}, {"label": "later base", "anchor": base2}], n=2)
o2 = PR.run(cfg2, os.path.join(SCR, "out2.json"))
late = o2["runs"]["FIX_ONE"]["bases"]["later base @ " + base2]["per_path"][0]
early = o2["runs"]["FIX_ONE"]["bases"]["window start @ 2023-01-01T00:00:00Z"]["per_path"][0]
ok("T2.a_different_base_gives_a_different_verdict", late["fired"] != early["fired"] or late["halt_index"] != early["halt_index"] or abs((late["cum_at_halt"] or 0) - (early["cum_at_halt"] or 0)) > 1e-12,
   {"early": early, "late": late})

# T3: breach_by before the breach
cfg3 = cfg_for([d1], ["2023-01-01T00:00:00Z"], [{"label": "window start", "anchor": "2023-01-01T00:00:00Z"}], breach_by=PR.iso(A0 + 6 * H4), n=2)
o3 = PR.run(cfg3, os.path.join(SCR, "out3.json"))
ps = o3["runs"]["FIX_ONE"]["p_start"]["2023-01-01T00:00:00Z"]
key = [k for k in ps if k.startswith("breach_by_")][0]
ok("T3.a_breach_after_breach_by_is_not_counted_by_that_date", ps[key]["fired_paths"] == 0 and ps["to_window_end"]["fired_paths"] == 1, {"by_date": ps[key]["fired_paths"], "to_end": ps["to_window_end"]["fired_paths"]})

# T5: named refusals
def refuses(fn, needle):
    try:
        fn(); return False, "no error"
    except PR.PReadingError as e:
        return needle in str(e), str(e)[:140]


r, msg = refuses(lambda: PR.run(cfg_for([d1], ["2023-01-01T00:00:00Z"], [{"label": "bad", "anchor": "2023-01-01T02:00:00Z"}], n=2), os.path.join(SCR, "x.json")), "is not an anchor")
ok("T5.base_not_on_the_anchor_axis_is_refused", r, msg)
d_t = write_run("FIX_TAMPER", [cum_a, cum_b], tamper_npz=True)
r, msg = refuses(lambda: PR.run(cfg_for([d_t], ["2023-01-01T00:00:00Z"], [{"label": "w", "anchor": "2023-01-01T00:00:00Z"}], n=2), os.path.join(SCR, "y.json")), "npz sha")
mut("a NAV cell edited after its json was written is refused", r, msg)
d_a = write_run("FIX_AXIS", [cum_a, cum_b], axis_shift=True)
r, msg = refuses(lambda: PR.run(cfg_for([d_a], ["2023-01-01T00:00:00Z"], [{"label": "w", "anchor": "2023-01-01T00:00:00Z"}], n=2), os.path.join(SCR, "z.json")), "one anchor axis")
ok("T5.paths_with_different_axes_are_refused", r, msg)
ok("T5.a_start_outside_the_window_is_reported_not_silently_skipped",
   PR.run(cfg_for([d1], ["2025-01-01T00:00:00Z"], [{"label": "w", "anchor": "2023-01-01T00:00:00Z"}], n=2), os.path.join(SCR, "w.json"))["runs"]["FIX_ONE"]["p_start"]["2025-01-01T00:00:00Z"]["in_window"] is False)

# mutation: the threshold
cfg_m = cfg_for([d1], ["2023-01-01T00:00:00Z"], [{"label": "w", "anchor": "2023-01-01T00:00:00Z"}], threshold=-0.2499, n=2)
om = PR.run(cfg_m, os.path.join(SCR, "m.json"))["runs"]["FIX_ONE"]["bases"]["w @ 2023-01-01T00:00:00Z"]["per_path"][0]
mut("threshold −24.99 % turns the exactly-on-the-line anchor into a halt", om["halt_index"] == 5, om)
mut("the recovery after the halt cannot leak into the P-halt end return", abs(b1[0]["end_return_phalt"] - b1[0]["end_return_nohalt"]) > 0.7, {"phalt": b1[0]["end_return_phalt"], "nohalt": b1[0]["end_return_nohalt"]})

fails = [r["check"] for r in RES if not r["ok"]]
out = dict(device="bt_p_reading_test.py", self_sha256=PR.sha(os.path.abspath(__file__)), tested=PR.sha(os.path.join(HERE, "bt_p_reading.py")),
           argv=sys.argv, numpy=np.__version__, checks=RES, failed=fails, VERDICT="PASS" if not fails else "RED", runtime_s=round(time.time() - T0, 1))
json.dump(out, open(OUTP, "w"), indent=1, default=str)
print("BT_P_READING_TEST VERDICT: " + ("ALL PASS %d/%d checks (baselines green, every mutation red)" % (len(RES), len(RES)) if not fails else "FAILURES %d/%d: %s" % (len(fails), len(RES), fails)), flush=True)
sys.exit(0 if not fails else 3)
