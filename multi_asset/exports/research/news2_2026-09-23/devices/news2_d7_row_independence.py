"""Is stable_trend_block row-independent? If it is, F8_TREND_ROWS=last is bitwise equal to =all at the
extracted row BY CONSTRUCTION, and the admission gate is confirming an implementation, not discovering
a numerical fact. That distinction decides how much a NO-SIGNAL sample costs.

Measured, not read: compute the block for a whole hi vector, then for each hi ALONE, and compare.
"""
import hashlib, json, os, sys, time
import numpy as np
sys.path.insert(0, sys.argv[1])
from stable_trend_reference import stable_trend_block

rng = np.random.default_rng(11)
TT, nc = 12000, 12
r = rng.normal(0, 0.003, (TT, nc))
fin = rng.random((TT, nc)) > 0.04            # gaps, so the support band is populated
r[~fin] = np.nan
rz = np.where(np.isfinite(r), r, 0.0)
first = np.array([int(np.argmax(np.isfinite(r[:, j]))) for j in range(nc)])
pm = np.arange(TT)[:, None] >= first[None, :]
lr = np.log1p(rz)
hi = np.arange(9000, TT, 48)

rows = []
for w in (288, 2016):
    allrows = stable_trend_block(lr, pm, hi, w, chunk_syms=2)
    ndiff = 0
    for k in range(len(hi)):
        one = stable_trend_block(lr, pm, hi[k:k + 1], w, chunk_syms=2)
        a, b = allrows[k], one[0]
        ndiff += int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum())
    rows.append({"w": w, "n_rows": int(len(hi)), "n_cols": nc,
                 "cells_compared": int(len(hi) * nc), "cells_differing": ndiff})
    print(json.dumps(rows[-1]), flush=True)

tot = sum(x["cells_differing"] for x in rows)
out = {"device": "rowindep.py", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "question": "does computing one hi alone give the same row as computing the whole hi vector?",
       "rows": rows, "total_cells_differing": tot,
       "VERDICT": "ROW_INDEPENDENT (F8_TREND_ROWS=last equals =all at the extracted row by construction)"
                  if tot == 0 else f"NOT ROW INDEPENDENT: {tot} cells differ",
       "consequence": ("if row-independent, the E4(a) admission gate confirms the indexing of the "
                       "optimisation, not a numerical risk; a sample with no D7-signal anchor therefore "
                       "fails to exercise the column, but does not leave a numerical hazard unmeasured")}
json.dump(out, open(sys.argv[2], "w"), indent=1)
print("ROWINDEP", out["VERDICT"], flush=True)
