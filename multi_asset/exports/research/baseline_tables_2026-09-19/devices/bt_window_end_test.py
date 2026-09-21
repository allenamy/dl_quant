#!/usr/bin/env python3
"""bt_window_end_test.py — the test for E-0921-B: a configured cutoff may decide WHETHER something happened; it may never
decide WHAT A TERMINAL VALUE IS.

THE DEFECT. `bt_p2_reading.py`'s quarterly-start loop computed `upto_i` from the configured `breach_by` and passed it to
`p2_of`, which turned it into `hi = upto_i + 1` and used that one slice for BOTH the breach test AND the window-end value.
All three P2 configs pin `breach_by = 2026-08-31T00:00:00Z`, including `RUN_CONFIG_P2reading_A0ext_*`, whose run reaches
`2026-09-18T20:00Z`. So the renderer printed a number under a heading that said "window end" while it had been truncated at
a date the run had long passed — 23 of 34 rows on the extended run, worst 17.179963 pp. The sibling `bt_p_reading.py` got
this right by calling `halt_of` twice; P2 called it once.

WHAT IS TESTED, in order, and nothing is claimed on a baseline that was not asserted green first:

  B0  BASELINE GREEN — the fixed devices run on a fixture, the window-end sweep measures a NON-ZERO number of carriers,
      and it finds no violation. (A sweep that measured nothing is not a sweep that found nothing wrong.)
  N1  THE REAL NUMBERS — the six-anchor fixture the round-7 review used: returns 1..6 %, `breach_by` at the third anchor,
      no stop anywhere. The PRE-FIX device (extracted from a PINNED git blob, not from the working tree) returns 6.1106 %;
      the fixed device's `to_window_end` returns 22.825141712 %, which is the plain compounding of all six.
  R1  RED ON THE OLD SHAPE — the pre-fix quarterly cell, which carries only the cutoff reading, is REFUSED by
      `assert_every_quarterly_start_reports_both`. This is the assertion that makes the old shape unrepresentable.
  R2  RED — a terminal value whose scope says `run_window_end` but whose anchor is not the run's last anchor.
  R3  RED, FAIL CLOSED — a terminal-value carrier whose `window_scope` is absent, and one whose scope is a name nobody
      declared. Both are REFUSED rather than skipped: "the key isn't there so this isn't my problem" is the single defect
      family that has bitten this project most often.
  R4  RED, NOT VACUOUS — a document with zero carriers is REFUSED, so the sweep cannot pass by measuring nothing.
  R5  THE RENDERER — a pre-fix receipt is REFUSED by `bt_p2_render.py` instead of being rendered. Renaming the column was
      explicitly rejected: a renamed column still sits beside correctly-computed window ends and invites the comparison.

This device REQUIRES the research git repository (it runs the pre-fix device from a pinned blob), so it runs
on the repo host, not on pod2.
usage: /usr/bin/python3 bt_window_end_test.py <scratch_dir> <out.json>
"""
import os, sys, json, time, shutil, subprocess

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_p_reading as PR
import bt_p2_reading as P2

# The pre-fix device is taken from a PINNED commit, never from the working tree and never from a moving reference: a green
# obtained in a dirty tree certifies the tree, not the commit (E-0918-R).
PREFIX_COMMIT = "6bba6e9fe65d27d8d65912aa522f21763556848c"
PREFIX_BLOB = "586ce296e854352562f5970d6fe612efedacf7cd"      # bt_p2_reading.py at that commit
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))

T0 = time.time(); SCR, OUTP = sys.argv[1], sys.argv[2]
assert "/runs/" not in os.path.abspath(SCR), "fixtures never go into a run directory"
shutil.rmtree(SCR, ignore_errors=True); os.makedirs(SCR, exist_ok=True)
RES = []
H4 = 14400
A0 = PR.ts("2024-01-01T00:00:00Z")


def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail))
    print(("PASS " if cond else "FAIL ") + name, json.dumps(detail, default=str)[:420] if detail is not None else "", flush=True)
    return bool(cond)


def refuses(fn, *a, **kw):
    """returns (did_it_refuse, the message) — a red case must refuse, and the message must name the thing"""
    try:
        fn(*a, **kw)
        return False, "it did NOT refuse"
    except Exception as e:
        return True, "%s: %s" % (type(e).__name__, e)


def write_run(dirname, series, flattens, n_seeds=None):
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
        json.dump({"seed": s, "npz_sha256": PR.sha(st + ".npz"),
                   "flatten_log": [[PR.iso(t), "fixture"] for t in fl]}, open(st + ".json", "w"))
    return d


def cfg_for(dirs, breach_by, starts, n=2, h_main=12, tag=""):
    c = {"paths_R": n, "pins": {"prereg_amendment_2": {"sha256": "fixture"},
                                "prereg_amendment_3": {"sha256": "fixture", "doc": "AMENDMENT 3"}},
         "p_reading": {"threshold_cum_return": -0.25, "caliber": "fixture", "halt_semantics": "fixture",
                       "breach_by": breach_by, "starts": list(starts),
                       "bases": [{"label": "base", "anchor": PR.iso(A0)}]},
         "p2_reading": {"resume_hours_main": h_main, "resume_hours_sensitivity": [8, 20],
                        "include_sim_rule": True, "include_never": True},
         "runs": [{"label": os.path.basename(d), "dir": d} for d in dirs]}
    p = os.path.join(SCR, "cfg_%s_%d.json" % (tag, int(time.time() * 1e6) % 10 ** 9)); json.dump(c, open(p, "w"), indent=1)
    return p


# ══════════════════════════════════════════════════════ B0 · BASELINE GREEN, asserted before anything is mutated ══════
n = 30
d0 = write_run("FIX_WE", [np.full(n, 0.01), np.full(n, 0.005)], [[], []])
cfg0 = cfg_for([d0], PR.iso(A0 + H4 * 9), [PR.iso(A0)], tag="base")     # cutoff at anchor 9, run reaches anchor 29
o0 = P2.run(cfg0, os.path.join(SCR, "o0.json"))
R0 = o0["runs"]["FIX_WE"]
WC = R0["window_end_contract"]
A_fix = np.arange(A0, A0 + H4 * n, H4, dtype=np.int64)
ok("B0.BASELINE_GREEN the fixed device wrote a receipt and its window-end sweep found no violation",
   WC["violations"] == [] and WC["run_window_last_anchor"] == PR.iso(A_fix[-1]),
   {"violations": WC["violations"], "run_window_last_anchor": WC["run_window_last_anchor"],
    "configured_cutoff_anchor": WC["configured_cutoff_anchor"]})
ok("B0.BASELINE_GREEN the sweep measured a NON-ZERO number of carriers, of BOTH scopes (not a vacuous pass)",
   WC["carriers"] > 0 and WC["run_window_end"] > 0 and WC["configured_cutoff"] > 0,
   {"carriers": WC["carriers"], "run_window_end": WC["run_window_end"], "configured_cutoff": WC["configured_cutoff"]})
ok("B0.BASELINE_GREEN every quarterly start reports BOTH readings",
   WC["quarterly"]["every_one_reports_both"] and WC["quarterly"]["quarterly_starts_checked"] > 0, WC["quarterly"])

# ══════════════════════════════════════════ N1 · the numbers, pre-fix device from a PINNED blob vs the fixed one ══════
n6 = 6
r6 = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
d6 = write_run("FIX_SIX", [r6, r6], [[], []])
cut6 = PR.iso(A0 + H4 * 2)                                              # breach_by lands on the THIRD anchor
cfg6 = cfg_for([d6], cut6, [PR.iso(A0)], tag="six")

prefix_src = os.path.join(SCR, "prefix_device")
os.makedirs(prefix_src, exist_ok=True)
blob = subprocess.run(["git", "-C", REPO, "cat-file", "blob", PREFIX_BLOB], capture_output=True)
if not blob.stdout:
    sys.exit("REFUSED: this device needs the research git repository, because it runs the PRE-FIX device from a pinned "
             "blob rather than from any working tree. Run it where the repo is (%s). git said: %s"
             % (REPO, blob.stderr.decode()[:200]))
open(os.path.join(prefix_src, "bt_p2_reading.py"), "wb").write(blob.stdout)
for dep in ("bt_p_reading.py", "bt_agg.py"):
    open(os.path.join(prefix_src, dep), "wb").write(
        subprocess.run(["git", "-C", REPO, "show", "%s:multi_asset/exports/research/baseline_tables_2026-09-19/devices/%s"
                        % (PREFIX_COMMIT, dep)], capture_output=True).stdout)
pre = subprocess.run([sys.executable, "-B", "-c",
                      "import sys,json;sys.path.insert(0,%r);import bt_p2_reading as P;"
                      "o=P.run(%r,%r);print('OK')" % (prefix_src, cfg6, os.path.join(SCR, "o6_prefix.json"))],
                     capture_output=True, text=True)
pre_ok = os.path.exists(os.path.join(SCR, "o6_prefix.json"))
o6_pre = json.load(open(os.path.join(SCR, "o6_prefix.json"))) if pre_ok else None
o6 = P2.run(cfg6, os.path.join(SCR, "o6.json"))
cutk = "breach_by_" + cut6[:10]
cell_new = o6["runs"]["FIX_SIX"]["p_start"][PR.iso(A0)]["never"]["W_ENTRY"]
v_end = cell_new["to_window_end"]["end_return_P2"]["measured"]["mean"]
v_cut = cell_new[cutk]["end_return_P2"]["measured"]["mean"]
v_pre = (o6_pre["runs"]["FIX_SIX"]["p_start"][PR.iso(A0)]["never"]["W_ENTRY"]["end_return_P2"]["measured"]["mean"]
         if pre_ok else None)
compounded = float(np.prod([1 + x for x in r6]) - 1)
ok("N1.the PRE-FIX device (pinned blob %s) returned the value truncated at the cutoff" % PREFIX_BLOB[:12],
   pre_ok and abs(v_pre - 0.061106) < 1e-9,
   {"pre_fix_device_value_pct": None if v_pre is None else round(100 * v_pre, 6), "expected_pct": 6.1106,
    "pinned_commit": PREFIX_COMMIT, "pinned_blob": PREFIX_BLOB, "stderr_tail": pre.stderr[-200:] if not pre_ok else ""})
ok("N1.the FIXED device's to_window_end is the plain compounding of all six anchors",
   abs(v_end - compounded) < 1e-12 and abs(100 * v_end - 22.825141712) < 1e-6,
   {"to_window_end_pct": round(100 * v_end, 9), "hand_compounded_pct": round(100 * compounded, 9),
    "review_expected_pct": 22.825141712})
ok("N1.the FIXED device still reports the cutoff reading, and it equals what the pre-fix device published",
   pre_ok and abs(v_cut - v_pre) < 1e-15,
   {"cutoff_reading_pct": round(100 * v_cut, 6), "pre_fix_published_pct": (None if v_pre is None else round(100 * v_pre, 6)),
    "why": "the cutoff reading is not deleted — it is the answer to a DIFFERENT question and is now labelled as such"})
ok("N1.the gap between the two readings on this fixture",
   pre_ok and abs((v_end - v_cut) - (compounded - 0.061106)) < 1e-9,
   {"gap_pp": round(100 * (v_end - v_cut), 9)})
ok("N1.the window-end value was read at the RUN's last anchor, not at the cutoff",
   cell_new["to_window_end"]["mean_path"]["window_last_anchor"] == PR.iso(A0 + H4 * (n6 - 1))
   and cell_new[cutk]["mean_path"]["window_last_anchor"] == cut6,
   {"to_window_end_read_at": cell_new["to_window_end"]["mean_path"]["window_last_anchor"],
    "cutoff_read_at": cell_new[cutk]["mean_path"]["window_last_anchor"], "run_last_anchor": PR.iso(A0 + H4 * (n6 - 1))})

# ══════════════════════════════════════════════════════════════ R1–R4 · red cases, on the green baseline above ════════
last = PR.iso(A_fix[-1]); cut = WC["configured_cutoff_anchor"]

# R1 — the PRE-FIX SHAPE: a quarterly cell that carries only the cutoff reading
old_shape = {PR.iso(A0): {"in_window": True, "12": {"W_ENTRY": {"end_return_P2": {},
                                                                "mean_path": {"window_last_anchor": cut,
                                                                              "window_scope": "configured_cutoff"}}}}}
red, msg = refuses(PR.assert_every_quarterly_start_reports_both, old_shape, "R1 old shape")
ok("R1.RED_ON_THE_OLD_SHAPE a quarterly cell carrying ONLY the cutoff reading is refused", red, {"refusal": msg[:300]})
red2, _ = refuses(PR.assert_every_quarterly_start_reports_both, o6["runs"]["FIX_SIX"]["p_start"], "R1 new shape")
ok("R1.GREEN_ON_THE_NEW_SHAPE the same assertion accepts the fixed device's own document", not red2, {"refused": red2})

# R2 — a window-end value read at the wrong anchor
bad = json.loads(json.dumps(R0))
bad["p_start"][PR.iso(A0)]["12"]["W_ENTRY"]["to_window_end"]["mean_path"]["window_last_anchor"] = cut
red, msg = refuses(PR.assert_window_ends, bad, A_fix, cut, "R2")
ok("R2.RED a value whose scope is run_window_end but whose anchor is the cutoff is refused, and the refusal NAMES it",
   red and "read_at_anchor" in msg, {"refusal": msg[:300]})

# R3 — fail closed: an unclassified carrier
for label, mutate in (("window_scope absent", lambda c: c.pop("window_scope")),
                      ("window_scope is a name nobody declared", lambda c: c.__setitem__("window_scope", "to_the_end_ish"))):
    bad = json.loads(json.dumps(R0))
    mutate(bad["p_start"][PR.iso(A0)]["12"]["W_ENTRY"]["to_window_end"]["mean_path"])
    red, msg = refuses(PR.assert_window_ends, bad, A_fix, cut, "R3")
    ok("R3.RED_FAIL_CLOSED a terminal-value carrier with %s is refused, not skipped" % label,
       red and "WINDOW_SCOPES" in msg, {"refusal": msg[:300]})

# R4 — not vacuous
red, msg = refuses(PR.assert_window_ends, {"nothing": {"here": [1, 2, 3]}}, A_fix, cut, "R4")
ok("R4.RED_NOT_VACUOUS a document with zero terminal-value carriers is refused", red and "measured NOTHING" in msg,
   {"refusal": msg[:300]})

# ══════════════════════════════════════════════════════════════════════════ R5 · the renderer refuses the old shape ══
# the renderer prints per-flatten medians, so its fixture must contain a flatten event on every path — otherwise the
# renderer fails on an unrelated degenerate cell and the test would not be discriminating between old and new shapes.
dR = write_run("FIX_REND", [np.full(20, 0.01), np.full(20, 0.005)], [[A0 + H4 * 5 + 3600], [A0 + H4 * 5 + 3600]])
cfgR = cfg_for([dR], PR.iso(A0 + H4 * 6), [PR.iso(A0)], tag="rend")
subprocess.run([sys.executable, "-B", "-c", "import sys;sys.path.insert(0,%r);import bt_p2_reading as P;"
                "P.run(%r,%r)" % (prefix_src, cfgR, os.path.join(SCR, "oR_prefix.json"))], capture_output=True, text=True)
P2.run(cfgR, os.path.join(SCR, "oR.json"))
pre_ok = pre_ok and os.path.exists(os.path.join(SCR, "oR_prefix.json"))
if pre_ok:
    rr = subprocess.run([sys.executable, "-B", os.path.join(HERE, "bt_p2_render.py"),
                         os.path.join(SCR, "oR_prefix.json"), os.path.join(SCR, "r_prefix.md")],
                        capture_output=True, text=True)
    rn = subprocess.run([sys.executable, "-B", os.path.join(HERE, "bt_p2_render.py"),
                         os.path.join(SCR, "oR.json"), os.path.join(SCR, "r_new.md")], capture_output=True, text=True)
    ok("R5.RED the renderer REFUSES a pre-fix receipt instead of printing its truncated number under 'window end'",
       rr.returncode != 0 and "REFUSED" in (rr.stdout + rr.stderr),
       {"returncode": rr.returncode, "message": (rr.stdout + rr.stderr).strip().splitlines()[-1][:260]})
    _md = open(os.path.join(SCR, "r_new.md")).read() if rn.returncode == 0 else ""
    ok("R5.GREEN the renderer renders the fixed receipt, and its quarterly table states the E-0921-B caliber",
       rn.returncode == 0 and "E-0921-B 口径" in _md and "判到截止日" in _md,
       {"returncode": rn.returncode, "stdout": rn.stdout.strip()[:120],
        "caliber_line_present": "E-0921-B 口径" in _md})
else:
    ok("R5.the renderer cases could not run because the pinned pre-fix device did not produce a receipt", False,
       {"stderr_tail": pre.stderr[-400:]})

nfail = sum(1 for r in RES if not r["ok"])
doc = {"device": "bt_window_end_test.py", "self_sha256": PR.sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ledger": "E-0921-B", "review": "round-7 G-01",
       "pinned_pre_fix": {"commit": PREFIX_COMMIT, "blob_bt_p2_reading": PREFIX_BLOB},
       "checks": RES, "n_checks": len(RES), "n_failed": nfail, "runtime_s": round(time.time() - T0, 1)}
json.dump(doc, open(OUTP, "w"), indent=1, default=str)
print(("BT_WINDOW_END_TEST VERDICT: ALL PASS %d/%d checks (baseline asserted green first; the pre-fix device run from a "
       "pinned blob; every red case red)" % (len(RES), len(RES))) if not nfail else
      ("BT_WINDOW_END_TEST VERDICT: FAILURES %d/%d checks: %s" % (nfail, len(RES), [r["check"] for r in RES if not r["ok"]])),
      flush=True)
sys.exit(0 if not nfail else 3)
