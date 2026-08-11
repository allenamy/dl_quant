"""[e] CONTROLLED EXPERIMENT for 0C: does score_post_fix mutate the log it scores?

0C judged my 17:03Z evidence UNKNOWN and was right: I hashed the LIVE production tree, which a
concurrent anchor can write to for reasons unrelated to the scorer. A hash that can move for two
reasons cannot attribute the movement to either.

Controls:
  1. the subject is a COPY of the production tree, which no anchor can touch;
  2. the window is clear (next anchor 20:00Z, verified against the run log before starting);
  3. the copy's byte digest is taken immediately before and after each scorer run;
  4. a NEGATIVE control: the same digest taken across a no-op interval, to show the digest is
     stable when nothing runs (otherwise "unchanged" proves nothing about the scorer);
  5. a POSITIVE control: a deliberate append, to show the digest CAN move (otherwise "unchanged"
     is what a broken digest also reports).
Read-only with respect to production.
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time

REPO = "/Users/haosiyu/dl_quant_live"
for d in ("live", "ops", "signal"):
    sys.path.insert(0, os.path.join(REPO, d))
SRC = os.path.join(REPO, "state/testnet/pilot_log")
RID, DAY = "A1785067246", "20260726"


def digest(root):
    h = hashlib.sha256()
    for day in sorted(os.listdir(root)):
        p = os.path.join(root, day, "orders.jsonl")
        if os.path.isfile(p):
            h.update(open(p, "rb").read())
    return h.hexdigest()


def nrows(root):
    n = 0
    for day in sorted(os.listdir(root)):
        p = os.path.join(root, day, "orders.jsonl")
        if os.path.isfile(p):
            n += sum(1 for l in open(p) if l.strip())
    return n


log = subprocess.run(["tail", "-3", os.path.join(REPO, "state/anchor_runs.log")],
                     capture_output=True, text=True).stdout.strip().splitlines()
print("last run-log lines (to show no anchor is mid-flight):")
for l in log:
    print("   ", l[:110])
print("now:", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "| next anchor 20:00Z\n")

work = tempfile.mkdtemp(prefix="e_controlled_")
tree = os.path.join(work, "pilot_log")
shutil.copytree(SRC, tree)
d0, n0 = digest(tree), nrows(tree)
print(f"copy made      digest={d0[:16]}  rows={n0}")

time.sleep(2)
d_noop = digest(tree)
print(f"NEGATIVE ctrl  digest={d_noop[:16]}  rows={nrows(tree)}   "
      f"(nothing ran) -> {'stable' if d_noop == d0 else 'MOVED — digest is not a valid instrument'}")

import score_post_fix as SPF
r1 = SPF.score(root=tree, day=DAY, rebalance_id=RID)
d1, n1 = digest(tree), nrows(tree)
print(f"scorer run #1  digest={d1[:16]}  rows={n1}   -> {'UNCHANGED' if d1 == d0 else 'MUTATED'}")

r2 = SPF.score(root=tree, day=DAY, rebalance_id=RID)
d2, n2 = digest(tree), nrows(tree)
print(f"scorer run #2  digest={d2[:16]}  rows={n2}   -> {'UNCHANGED' if d2 == d0 else 'MUTATED'}")

with open(os.path.join(tree, DAY, "orders.jsonl"), "a") as f:
    f.write("\n")
d3 = digest(tree)
print(f"POSITIVE ctrl  digest={d3[:16]}  rows={nrows(tree)}   "
      f"(one byte appended) -> {'MOVED as it must' if d3 != d0 else 'DID NOT MOVE — instrument blind'}")

print("\nverdicts identical across the two runs:",
      json.dumps(r1.get('overall')) == json.dumps(r2.get('overall')))
print("E5b both runs:", r1.get("E5b_5b_silent", {}).get("n_latest"),
      r2.get("E5b_5b_silent", {}).get("n_latest"))
print("\nRESULT:", "PASS — two scorer runs left the copy byte-identical, with both controls valid"
      if (d1 == d0 and d2 == d0 and d_noop == d0 and d3 != d0) else "FAIL / INCONCLUSIVE")
shutil.rmtree(work, ignore_errors=True)
