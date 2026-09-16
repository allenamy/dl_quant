"""R6 BW-3/BW-4 whitelist re-verification. The first pass mis-classified because WL_TS used a wrong epoch
(1787803200 = 2026-08-27 04:00Z, not 2026-08-31 04:00Z). The COMPARISON was correct; only the labelling was wrong.
This re-runs the classification with the right anchors, adds the NaN->finite DIRECTION check the whitelist requires,
and LOCALISES the DL-target differences (YR4s / YRZ / has_panel) instead of asserting a whole-array equality."""
import numpy as np, json, time, calendar
def U(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
WL_TS = [calendar.timegm((2026, 8, 31, h, 0, 0)) for h in (4, 8, 12, 16, 20)]
print("whitelist anchors:", [U(t) for t in WL_TS])
OUT = "/workspace/uplift_2026-09-11/r6/out"
R = {}
# ---- BW-3 ----
M0 = np.load("/workspace/data/wide_fea_v4_meta.npz", allow_pickle=True)
M1 = np.load(f"{OUT}/wide_fea_v4_meta_x0910.npz", allow_pickle=True)
E0 = M0["E_ts"].astype(np.int64); n0 = len(E0)
names = [str(x) for x in M1["names"]]; ci = {n: i for i, n in enumerate(names)}
c_fe, c_fn = ci["fund_ema"], ci["fund_now"]
F0 = np.load("/workspace/data/wide_fea_v4.npy", mmap_mode="r")
F1 = np.load(f"{OUT}/wide_fea_v4_x0910.npy", mmap_mode="r")
wl_rows = {}
for t in WL_TS:
    i = int(np.searchsorted(E0, t)); assert int(E0[i]) == t, (U(t), U(E0[i]))
    wl_rows[i] = t
det = []; bad = []
BLK = 300
for s in range(0, n0, BLK):
    e = min(s+BLK, n0)
    A = np.asarray(F0[s:e]); B = np.asarray(F1[s:e])
    same = (A.view(np.uint16) == B.view(np.uint16))
    if same.all(): continue
    for r in np.unique(np.nonzero(~same)[0]):
        gi = s + int(r); cols = np.unique(np.nonzero(~same[r])[1])
        rec = {"anchor": U(E0[gi]), "row": gi, "changed_cols": [names[c] for c in cols],
               "n_changed_cells": int((~same[r]).sum())}
        if gi in wl_rows and set(cols.tolist()) <= {c_fe, c_fn}:
            ch = ~same[r][:, [c_fe, c_fn]]
            a = A[r][:, [c_fe, c_fn]]; b = B[r][:, [c_fe, c_fn]]
            rec["all_changed_were_NaN_before"] = bool(np.all(np.isnan(a[ch])))
            rec["all_changed_are_finite_now"] = bool(np.all(np.isfinite(b[ch])))
            rec["finite_to_other_finite"] = int((np.isfinite(a[ch]) & np.isfinite(b[ch])).sum())
            rec["finite_to_NaN"] = int((np.isfinite(a[ch]) & np.isnan(b[ch])).sum())
            other = [c for c in range(len(names)) if c not in (c_fe, c_fn)]
            rec["other_80_cols_bitwise_equal"] = bool(same[r][:, other].all())
            det.append(rec)
        else:
            bad.append(rec)
ok3 = (not bad) and all(d["all_changed_were_NaN_before"] and d["all_changed_are_finite_now"]
                        and d["finite_to_NaN"] == 0 and d["finite_to_other_finite"] == 0
                        and d["other_80_cols_bitwise_equal"] for d in det)
R["BW3"] = {"verdict": "PASS (whitelist only)" if ok3 else "FAIL",
            "cells_compared": int(n0*829*82), "changed_cells": sum(d["n_changed_cells"] for d in det) + sum(b["n_changed_cells"] for b in bad),
            "anchors_changed": len(det), "out_of_whitelist": bad, "whitelist_detail": det,
            "anchors_bitwise_identical": int(n0 - len(det) - len(bad))}
print("BW3:", R["BW3"]["verdict"], "| changed anchors", len(det), "| out-of-whitelist", len(bad))
for d in det: print("   ", json.dumps(d))
# ---- BW-4 localisation ----
T0 = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)
T1 = np.load(f"{OUT}/dlw_targets_x0910.npz", allow_pickle=True)
t0a = T0["E_ts"].astype(np.int64); m0 = len(t0a)
loc = {}
for k in ("YR4s", "YRZ", "has_panel"):
    a = T0[k]; b = T1[k][:m0]
    if a.dtype.kind == "f":
        d = ~((a == b) | (np.isnan(a) & np.isnan(b)))
        rows = np.unique(np.nonzero(d)[0])
    else:
        d = (a != b); rows = np.unique(np.nonzero(d)[0]) if d.ndim == 1 else np.unique(np.nonzero(d)[0])
    loc[k] = {"rows_differing": [U(t0a[r]) for r in rows], "n_rows": int(len(rows)),
              "cells_differing": int(d.sum())}
    if k in ("YR4s", "YRZ") and len(rows):
        sub_a = a[rows]; sub_b = b[rows]
        loc[k]["was_all_NaN_before"] = bool(np.all(np.isnan(sub_a)))
        loc[k]["finite_now"] = int(np.isfinite(sub_b).sum())
    if k == "has_panel" and len(rows):
        loc[k]["before"] = [bool(x) for x in a[rows]]; loc[k]["after"] = [bool(x) for x in b[rows]]
wl_set = set(U(t) for t in WL_TS)
ok4 = all(set(v["rows_differing"]) <= wl_set for v in loc.values())
R["BW4"] = {"verdict": "PASS (whitelist only)" if ok4 else "FAIL", "localisation": loc,
            "equal_keys": ["E_ts", "y4s", "y4old", "qvk", "btcv", "yrs", "E_row", "members"]}
print("BW4:", R["BW4"]["verdict"])
for k, v in loc.items(): print("   ", k, json.dumps(v)[:300])
json.dump(R, open("/workspace/uplift_2026-09-11/r6/RECEIPT_BW345_corrected.json", "w"), indent=1)
print("DONE")
