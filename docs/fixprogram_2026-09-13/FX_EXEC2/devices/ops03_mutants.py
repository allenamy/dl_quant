#!/usr/bin/python3
"""OPS-03 A — MUTANT runner for the sliding weight shaper (FIXPROGRAM §0 step 3/5).

Same contract as `cdrift_mutants.py`: each mutant is one textual substitution in the executor clone's working tree,
each declares the CELL that must go red, and a mutant scored KILLED only when that named cell is in the FAILED list.
A suite that exits 1 without a summary line CRASHED, which is not the same as a cell going red. The tree is restored
byte-for-byte, including on failure.

★ ONE MUTANT IS DELIBERATELY NOT A HANG. "Remove the oversize guard" would spin forever rather than fail, so the
  mutant instead makes the oversize path DROP the spend silently — the realistic wrong answer, and one a suite can
  actually catch.

Usage: /usr/bin/python3 ops03_mutants.py <executor_clone> <out_receipt.json>
No network, no ledger writes, no venue.
"""
import hashlib
import json
import os
import subprocess
import sys

CLONE, RECEIPT = sys.argv[1:3]
SUITE = os.path.join(CLONE, "live", "tests_weight_shaper_sliding.py")
WATCHED = ["live/rate_budget.py", "live/tests_weight_shaper_sliding.py"]

MUTANTS = [
    ("M1_back_to_fixed_window",
     "live/rate_budget.py",
     "                self._w = [(t, w) for t, w in self._w if now - t < 60]\n"
     "                used = sum(w for _, w in self._w)",
     "                if self._w and now - self._w[0][0] >= 60:\n"
     "                    self._w = []\n"
     "                used = sum(w for _, w in self._w)",
     "reinstate a FIXED window (drop the whole window when its first entry ages out) — the defect itself",
     "no sliding 60s window of admitted weight"),
    ("M2_oversize_dropped_silently",
     "live/rate_budget.py",
     "                        self._w.append((now, weight))\n"
     "                        self.stats[\"weight_spent\"] += weight\n"
     "                        self.stats[\"weight_oversize_spends\"] += 1",
     "                        self.stats[\"weight_oversize_spends\"] = "
     "self.stats.get(\"weight_oversize_spends\", 0)",
     "drop an oversized spend instead of admitting and naming it — a silent loss of a real request",
     "admitted once and NAMED in stats"),
    ("M3_off_by_one_at_the_cap",
     "live/rate_budget.py",
     "                if used + weight > WEIGHT_PER_MIN:",
     "                if used + weight >= WEIGHT_PER_MIN:",
     "wait at the cap instead of above it — spends summing to exactly the cap would now block",
     "exactly the cap are admitted with 0 waits"),
    ("M4_window_never_pruned",
     "live/rate_budget.py",
     "                self._w = [(t, w) for t, w in self._w if now - t < 60]",
     "                self._w = list(self._w)",
     "never expire entries, so the window grows without bound and the shaper eventually blocks everything",
     "the blocked spend waits"),
    ("M5_weight_in_window_running_total",
     "live/rate_budget.py",
     "                        weight_in_window=sum(w for t, w in self._w if _now - t < 60),",
     "                        weight_in_window=self.stats[\"weight_spent\"],",
     "report the lifetime total as the window figure — the exact confusion OPS-03 C is correcting in the log line",
     "weight_in_window is the SLIDING sum"),
    ("M6_wait_not_counted",
     "live/rate_budget.py",
     "                    self.stats[\"weight_waits\"] += 1",
     "                    pass",
     "shape the traffic but do not record that anything was shaped — the acceptance line would read waits=0",
     "the blocked spend waits, is counted"),
    ("M7_wait_for_a_whole_window",
     "live/rate_budget.py",
     "                    need = used + weight - WEIGHT_PER_MIN",
     "                    need = float('inf')",
     "always sleep for the OLDEST entry regardless of how much room is needed — safe but needlessly slow; this "
     "mutant is expected to SURVIVE, and it is here to show the suite does not pretend to test cost",
     "__EXPECTED_TO_SURVIVE__"),
]


def sha_tree():
    return {f: hashlib.sha256(open(os.path.join(CLONE, f), "rb").read()).hexdigest() for f in WATCHED}


def run_suite():
    p = subprocess.run(["/usr/bin/python3", "-B", SUITE], capture_output=True, text=True, cwd=CLONE, timeout=600)
    failed, saw = [], False
    for line in p.stdout.splitlines():
        if line.startswith("FAILED: "):
            failed = [x.strip() for x in line[len("FAILED: "):].split(";")]
        if line.startswith("FAILED:") and not failed:
            failed = []
        if line.strip().endswith(" passed"):
            saw = True
    if not failed:                      # this suite prints FAILED: then one name per line
        names, grab = [], False
        for line in p.stdout.splitlines():
            if line.startswith("FAILED:"):
                grab = True
                continue
            if grab and line.startswith("  "):
                names.append(line.strip())
        failed = names
    return p.returncode, failed, (p.stdout + "\n" + p.stderr) if not saw else p.stdout


before = sha_tree()
results = []
rc0, failed0, _ = run_suite()
results.append({"id": "BASELINE", "rc": rc0, "n_failed": len(failed0), "failed": failed0,
                "verdict": "green" if rc0 == 0 else "NOT GREEN — fix the tree first"})

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
        expect_survive = want == "__EXPECTED_TO_SURVIVE__"
        hit = [] if expect_survive else [f for f in failed if want in f]
        crashed = bool(applied and rc == 1 and not failed)
        if not applied:
            v = "NOT APPLIED — fragment not found, mutant is stale"
        elif crashed:
            v = "CRASHED — not a red cell"
        elif expect_survive:
            v = "SURVIVED AS DECLARED" if rc == 0 else "UNEXPECTEDLY KILLED — the suite tests more than it claims"
        elif rc == 1 and hit:
            v = "KILLED"
        elif rc == 0:
            v = "SURVIVED — SUITE HOLE"
        else:
            v = "RED BUT NOT IN THE NAMED CELL"
        results.append({"id": mid, "file": rel, "applied": applied, "breaks": what,
                        "expected_red_cell_contains": want, "rc": rc, "n_failed": len(failed),
                        "which": hit[:2], "failed": failed[:6], "crashed_no_summary": crashed,
                        "tail": (sout[-600:] if crashed else None), "verdict": v})
        print(f"{mid:<34} {v}")
finally:
    after = sha_tree()

killable = [r for r in results[1:] if r["expected_red_cell_contains"] != "__EXPECTED_TO_SURVIVE__"]
rec = {"device": os.path.basename(__file__),
       "device_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
       "clone": CLONE,
       "clone_head": subprocess.run(["git", "-C", CLONE, "rev-parse", "HEAD"],
                                    capture_output=True, text=True).stdout.strip(),
       "file_sha_before": before, "file_sha_after": after, "tree_restored_bitwise": before == after,
       "n_mutants": len(MUTANTS), "n_killable": len(killable),
       "n_killed": sum(1 for r in killable if r["verdict"] == "KILLED"),
       "n_survived_as_declared": sum(1 for r in results[1:]
                                     if r["verdict"] == "SURVIVED AS DECLARED"),
       "results": results}
json.dump(rec, open(RECEIPT, "w"), ensure_ascii=False, indent=1)
print(f"\nkilled {rec['n_killed']}/{rec['n_killable']} killable "
      f"(+{rec['n_survived_as_declared']} declared survivor)  tree restored bitwise: {rec['tree_restored_bitwise']}")
print(f"receipt -> {RECEIPT}")
sys.exit(0 if (rec["n_killed"] == rec["n_killable"] and rec["tree_restored_bitwise"] and rc0 == 0) else 1)
