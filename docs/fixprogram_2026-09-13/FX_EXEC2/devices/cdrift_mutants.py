#!/usr/bin/python3
"""LED-08 drift check — MUTANT runner (FIXPROGRAM §0 step 3/5).

A green suite proves nothing on its own: it has to be the case that BREAKING the fix turns it red, and red in the
CELL that is supposed to notice. Each mutant below is a single textual substitution in the executor clone's working
tree; the suite is run; the tree is restored byte-for-byte (sha256 checked before and after). A mutant that leaves
the suite green is a HOLE in the suite and is reported as such.

Each mutant declares WHICH cell must go red, and the runner checks that named cell actually appears in the FAILED
list — not merely that the exit code was 1. "It went red" and "it went red for this reason" are different claims.

Usage: /usr/bin/python3 cdrift_mutants.py <executor_clone> <out_receipt.json>
No network, no ledger writes, no venue. The clone's tracked files are restored on exit, including on failure.
"""
import hashlib
import json
import os
import subprocess
import sys

CLONE, RECEIPT = sys.argv[1:3]
SUITE = os.path.join(CLONE, "live", "tests_cost_drift.py")

# (id, file, old_fragment, new_fragment, what it breaks, substring of the cell label that MUST go red)
MUTANTS = [
    ("M1_band_not_reference",
     "live/cost_drift.py",
     "thr = None if rmad is None else k * MAD_TO_SIGMA * rmad",
     "thr = None if cur.get('mad') is None else k * MAD_TO_SIGMA * float(cur.get('mad'))",
     "scale the threshold by the CURRENT band's dispersion instead of the frozen reference's — i.e. make the drift "
     "check self-calibrating again, which is the very defect being fixed",
     "the line came from the FROZEN reference"),
    ("M2_delta_in_trip_condition",
     "live/cost_drift.py",
     '"warn": bool(why is None and d is not None and thr is not None and abs(d) > thr),',
     '"warn": bool(why is None and d is not None and thr is not None and abs(d) > thr '
     'and abs((d or 0) * (taker_fee_bps - maker_fee_bps) * (_fin(turnover) or 0)) > delta_bps),',
     "fold the frozen K2 delta into the trip condition, so an economically small but real level shift is silenced",
     "mutating the frozen"),
    ("M3_unavailable_reads_as_match",
     "live/cost_drift.py",
     'return {"status": "reference_window_unavailable", "n_eligible": n_elig or 0,',
     'return {"status": "match", "n_eligible": n_elig or 0,',
     "let a reference window that is no longer in the ledger read as a clean MATCH — the silent-skip defect family",
     "reference_window_unavailable"),
    ("M4_degenerate_mad_warns",
     "live/cost_drift.py",
     'why = "reference MAD is 0 (degenerate dispersion) — no scale for a threshold"',
     'why = None',
     "drop the degenerate-reference guard, so a zero-MAD reference gives a threshold of 0 and warns on a float wobble",
     "zero-MAD reference"),
    ("M5_rebuild_not_excluded",
     "live/cost_drift.py",
     "        if t in rebuild:\n            n_rebuild += 1\n            continue",
     "        if t in rebuild:\n            n_rebuild += 1",
     "include rebuild anchors in the reference levels, so the two sides stop being the same population",
     "excludes them from the levels"),
    ("M6_min_n_ignored",
     "live/cost_drift.py",
     "MIN_N = 12",
     "MIN_N = 1",
     "drop the minimum-sample requirement, so a three-anchor band can issue a verdict",
     "thin CURRENT band"),
    ("M7_reference_level_not_printed",
     "live/cost_drift.py",
     'return (f"参照({cfg.get(\'window_name\')}): taker 中位 {_pct(t.get(\'reference_median\'), 1)} "',
     'return (f"({cfg.get(\'window_name\')}): taker 中位 {_pct(t.get(\'reference_median\'), 1)} "',
     "stop labelling the per-anchor line as the frozen reference, so the operator cannot tell the two levels apart",
     "carries the FROZEN reference level"),
    ("M8_summary_raises_no_warning",
     "live/cost_drift.py",
     "    w = []\n    for key in KEYS:",
     "    w = []\n    for key in []:",
     "keep the drift BLOCK but raise no warning from it, so the daily summary prints numbers and no verdict",
     "raises the drift VERDICT"),
]


def sha_tree():
    p = subprocess.run(["git", "-C", CLONE, "status", "--porcelain"], capture_output=True, text=True)
    files = ["live/cost_drift.py", "live/tests_cost_drift.py", "ops/anchor_report.py", "ops/daily_summary.py"]
    return {f: hashlib.sha256(open(os.path.join(CLONE, f), "rb").read()).hexdigest() for f in files}, p.stdout


def run_suite():
    p = subprocess.run(["/usr/bin/python3", "-B", SUITE], capture_output=True, text=True, cwd=CLONE, timeout=900)
    failed, saw_summary = [], False
    for line in p.stdout.splitlines():
        if line.startswith("FAILED: "):
            failed = [x.strip() for x in line[len("FAILED: "):].split(";")]
        if line.strip().endswith(" pass"):
            saw_summary = True
    # ★ rc 1 with NO summary line means the suite CRASHED. A crash is not "the named cell went red"; it is a cell
    #   that could not run. It is reported separately so a mutant is never scored KILLED by a traceback.
    return p.returncode, failed, (p.stdout + "\n" + p.stderr) if not saw_summary else p.stdout


before, dirty_before = sha_tree()
results = []
rc0, failed0, out0 = run_suite()
results.append({"id": "BASELINE", "rc": rc0, "n_failed": len(failed0), "failed": failed0,
                "expected_red_cell": None, "verdict": "green" if rc0 == 0 else "NOT GREEN — fix the tree first"})

try:
    for mid, rel, old, new, what, want in MUTANTS:
        path = os.path.join(CLONE, rel)
        src = open(path).read()
        applied = old in src
        if applied:
            open(path, "w").write(src.replace(old, new, 1))
        try:
            rc, failed, sout = run_suite() if applied else (None, [], "")
        finally:
            open(path, "w").write(src)
        hit = [f for f in failed if want in f]
        crashed = bool(applied and rc == 1 and not failed)
        results.append({
            "id": mid, "file": rel, "applied": applied, "breaks": what,
            "expected_red_cell_contains": want, "rc": rc, "n_failed": len(failed),
            "named_cell_went_red": bool(hit), "which": hit[:2], "failed": failed[:6],
            "crashed_no_summary": crashed,
            "tail": (sout[-600:] if crashed else None),
            "verdict": ("CRASHED — not a red cell" if crashed else
                        "KILLED" if (applied and rc == 1 and hit)
                        else ("SURVIVED — SUITE HOLE" if applied and rc == 0
                              else ("RED BUT NOT IN THE NAMED CELL" if applied
                                    else "NOT APPLIED — fragment not found, mutant is stale"))),
        })
        print(f"{mid:<32} {results[-1]['verdict']}")
finally:
    after, dirty_after = sha_tree()

rec = {"device": os.path.basename(__file__),
       "device_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
       "clone": CLONE,
       "clone_head": subprocess.run(["git", "-C", CLONE, "rev-parse", "HEAD"],
                                    capture_output=True, text=True).stdout.strip(),
       "file_sha_before": before, "file_sha_after": after,
       "tree_restored_bitwise": before == after,
       "n_mutants": len(MUTANTS),
       "n_killed": sum(1 for r in results[1:] if r["verdict"] == "KILLED"),
       "results": results}
json.dump(rec, open(RECEIPT, "w"), ensure_ascii=False, indent=1)
print(f"\nkilled {rec['n_killed']}/{rec['n_mutants']}  tree restored bitwise: {rec['tree_restored_bitwise']}")
print(f"receipt -> {RECEIPT}")
sys.exit(0 if (rec["n_killed"] == rec["n_mutants"] and rec["tree_restored_bitwise"] and rc0 == 0) else 1)
