#!/usr/bin/env python3
"""d10_make_symlists.py <inventory.json> <outdir> -- per-month symbol lists, from the inventory.

WHY: a blind census probes all 832 symbols in all 81 months = 67,392 requests, of which 47,103 are 404s
for files the venue does not have. The inventory (D10_S1_ARCHIVE_INVENTORY.json) already lists exactly
which (symbol, month) files exist, so those 47,103 probes are known-answer requests. Pruning them takes
the census from a measured ~18.8 h to ~8.7 h at the same 0.77 s/request rate, with NO loss of coverage.

WHAT CHANGES IN WHAT THE RECEIPTS ATTEST, stated because it is a real change: a pruned month manifest no
longer carries 404 entries, so "the venue has no file for this (symbol, month)" is attested by the
INVENTORY receipt rather than by a 404 line in the month manifest. n_404 = 0 in a pruned manifest is
therefore expected and is not evidence that every symbol had a file.
"""
import json, os, sys

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW  # every file this device writes goes through it (news2 class fix 2026-09-27)

inv = json.load(open(sys.argv[1]))["inventory"]
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
per = {}
for s, d in inv.items():
    for m in d["months"]:
        per.setdefault(m, []).append(s)
tot = 0
for m, syms in sorted(per.items()):
    DW.write_bytes(os.path.join(out, f"{m}.txt"), ("\n".join(sorted(syms)) + "\n").encode())
    tot += len(syms)
print(f"wrote {len(per)} per-month symbol lists, {tot} symbol-months total, into {out}")
print("months with the most symbols:", sorted(((len(v), k) for k, v in per.items()), reverse=True)[:3])
