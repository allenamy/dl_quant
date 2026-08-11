"""Idempotently insert basis_2026_01 then basis_2025_10 into the D1 queue,
RIGHT AFTER the currently-running d1_2025_11_run2 line, AHEAD of the remaining
completeness Run2 folds. basis_2026_01 first (drift/decisive), then basis_2025_10."""
import os
Q = "/mnt/storage/private/work_hsy/quant_research_multi_asset/experiments/d1gate/queue.txt"
ANCHOR = "configs/d1gate/d1_2025_11_run2.json"
INSERT = ["configs/d1gate/basis_2026_01.json", "configs/d1gate/basis_2025_10.json"]

lines = [l.rstrip("\n") for l in open(Q)]
# remove any existing occurrences of the basis lines (idempotent)
lines = [l for l in lines if l.strip() not in INSERT]
out, done = [], False
for l in lines:
    out.append(l)
    if l.strip() == ANCHOR and not done:
        out.extend(INSERT)
        done = True
if not done:
    raise SystemExit(f"ANCHOR {ANCHOR} not found in queue — abort (no blind append)")
open(Q, "w").write("\n".join(out) + "\n")
# echo the neighborhood
print("inserted after", ANCHOR)
for i, l in enumerate(out, 1):
    if ANCHOR in l or "basis_" in l or "d1_2025_12_run2" in l:
        print(f"  {i:>3}  {l}")
