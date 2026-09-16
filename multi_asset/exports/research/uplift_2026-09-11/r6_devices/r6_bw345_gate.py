"""R6 GATES BW-3 / BW-4 / X4 / X5 on the extended king features + DL targets (PREREG §6.1, §6.2, §7).
BW-3  king FEA + meta: of the 10182 pre-existing anchors, 10177 must be bitwise equal on ALL 82 columns; the 5
      whitelisted anchors (2026-08-31 04Z..20Z) may change ONLY in fund_ema/fund_now and ONLY NaN->finite.
BW-4  DL targets: all 10212 pre-existing anchors bitwise equal (y4s looks 48 rows forward, all inside the old range).
X4    funding completeness: members-only finite fraction of fund_ema >= 0.95 on every anchor entering a judged window.
X5    axis parity: the extended axis's pre-existing part equals the incumbent E_ts bitwise; the new anchors are
      EXACTLY the expected set; the whole axis is strictly 4h-regular with no duplicates.
"""
import numpy as np, json, time, os, hashlib, sys
def U(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
def sha(p):
    h = hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda: f.read(1<<24), b""): h.update(c)
    return h.hexdigest()
OUT = "/workspace/uplift_2026-09-11/r6/out"
R = {"finished_utc": None}
WL_TS = [1787803200 + 14400*k for k in range(5)]   # 2026-08-31 04:00Z .. 20:00Z
# ---------- BW-3 ----------
M0 = np.load("/workspace/data/wide_fea_v4_meta.npz", allow_pickle=True)
M1 = np.load(f"{OUT}/wide_fea_v4_meta_x0910.npz", allow_pickle=True)
E0 = M0["E_ts"].astype(np.int64); E1 = M1["E_ts"].astype(np.int64)
n0 = len(E0)
names0 = [str(x) for x in M0["names"]]; names1 = [str(x) for x in M1["names"]]
x5 = {"names_identical": names0 == names1,
      "prefix_E_ts_bitwise_equal": bool(np.array_equal(E0, E1[:n0])),
      "incumbent_n": int(n0), "extended_n": int(len(E1)),
      "new_anchors_n": int(len(E1) - n0),
      "new_first": U(E1[n0]) if len(E1) > n0 else None, "new_last": U(E1[-1]),
      "expected_new_set_equal": None, "grid_4h_strict": bool(np.all(np.diff(E1) == 14400)),
      "no_duplicates": bool(len(np.unique(E1)) == len(E1))}
exp_new = [int(E0[-1]) + 14400*k for k in range(1, len(E1)-n0+1)]
x5["expected_new_set_equal"] = bool(list(map(int, E1[n0:])) == exp_new)
x5["symmetric_difference"] = sorted(U(t) for t in set(map(int, E1[n0:])) ^ set(exp_new))
R["X5_axis_parity_king"] = x5
F0 = np.load("/workspace/data/wide_fea_v4.npy", mmap_mode="r")
F1 = np.load(f"{OUT}/wide_fea_v4_x0910.npy", mmap_mode="r")
assert F0.shape[1:] == F1.shape[1:]
ci = {n: i for i, n in enumerate(names1)}
c_fe, c_fn = ci["fund_ema"], ci["fund_now"]
wl_rows = {int(np.searchsorted(E0, t)): t for t in WL_TS}
bad = []; wl_detail = []; eq_all = 0; cells = 0
BLK = 200
for s in range(0, n0, BLK):
    e = min(s+BLK, n0)
    A = np.asarray(F0[s:e]); B = np.asarray(F1[s:e])
    ua, ub = A.view(np.uint16), B.view(np.uint16)
    same = (ua == ub)
    cells += A.size; eq_all += int(same.sum())
    if not same.all():
        for r in np.unique(np.nonzero(~same)[0]):
            gi = s + int(r)
            cols = np.unique(np.nonzero(~same[r])[1])
            rec = {"anchor": U(E0[gi]), "row": gi, "changed_cols": [names1[c] for c in cols],
                   "n_changed_cells": int((~same[r]).sum())}
            if gi in wl_rows and set(cols.tolist()) <= {c_fe, c_fn}:
                a_fe = A[r][:, [c_fe, c_fn]]; b_fe = B[r][:, [c_fe, c_fn]]
                ch = ~same[r][:, [c_fe, c_fn]]
                rec["direction_nan_to_finite_only"] = bool(np.all(np.isnan(a_fe[ch])) and np.all(np.isfinite(b_fe[ch])))
                rec["other_80_cols_bitwise_equal"] = True
                wl_detail.append(rec)
            else:
                bad.append(rec)
R["BW3_king_fea"] = {"cells_compared": int(cells), "bitwise_equal": int(eq_all), "bitwise_diff": int(cells-eq_all),
                     "anchors_compared": int(n0), "whitelist_anchors_changed": len(wl_detail),
                     "whitelist_detail": wl_detail, "out_of_whitelist_changes": bad[:20],
                     "n_out_of_whitelist": len(bad)}
R["BW3_king_fea"]["verdict"] = "PASS" if (not bad and all(d.get("direction_nan_to_finite_only") for d in wl_detail)) else "FAIL"
for k in ("members", "y4", "qvk"):
    a, b = M0[k], M1[k][:n0]
    R["BW3_king_fea"][f"meta_{k}_prefix_equal"] = bool(
        all(np.array_equal(a[i], b[i]) for i in range(n0)) if k == "members"
        else np.array_equal(a, b, equal_nan=True))
# ---------- BW-4 ----------
T0 = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)
T1 = np.load(f"{OUT}/dlw_targets_x0910.npz", allow_pickle=True)
t0a = T0["E_ts"].astype(np.int64); t1a = T1["E_ts"].astype(np.int64); m0 = len(t0a)
bw4 = {"incumbent_n": int(m0), "extended_n": int(len(t1a)), "new_anchors_n": int(len(t1a)-m0),
       "prefix_E_ts_bitwise_equal": bool(np.array_equal(t0a, t1a[:m0])),
       "new_last": U(t1a[-1]), "grid_4h_strict": bool(np.all(np.diff(t1a) == 14400))}
for k in ("y4s", "YR4s", "YRZ", "y4old", "qvk", "btcv", "has_panel", "yrs", "E_row"):
    if k not in T0.files: continue
    a = T0[k]; b = T1[k][:m0]
    bw4[f"{k}_prefix_bitwise_equal"] = bool(np.array_equal(a, b, equal_nan=True) if a.dtype.kind == "f" else np.array_equal(a, b))
bw4["members_prefix_equal"] = bool(all(np.array_equal(T0["members"][i], T1["members"][i]) for i in range(m0)))
bw4["verdict"] = "PASS" if all(v for k, v in bw4.items() if k.endswith("_equal") or k.endswith("_strict")) else "FAIL"
R["BW4_dl_targets"] = bw4
# ---------- X4 on the extended king features ----------
mem1 = M1["members"]
viol = []; tail = []
i0 = int(np.searchsorted(E1, 1740787200))     # 2025-03-01
for i in range(i0, len(E1)):
    m = mem1[i]; a = np.asarray(F1[i, m, c_fe]); f = float(np.isfinite(a).mean())
    if f < 0.95: viol.append({"anchor": U(E1[i]), "frac": round(f, 4)})
    if i >= len(E1)-70: tail.append({"anchor": U(E1[i]), "members": int(len(m)), "fund_ema_finite": int(np.isfinite(a).sum()), "frac": round(f,4)})
R["X4_extended"] = {"scanned_from": "2025-03-01", "violations_n": len(viol), "violations": viol[:20],
                    "tail_last70": tail, "verdict": "PASS" if not viol else "FAIL"}
R["shas"] = {"fea_x0910": sha(f"{OUT}/wide_fea_v4_x0910.npy"), "meta_x0910": sha(f"{OUT}/wide_fea_v4_meta_x0910.npz"),
             "dlw_x0910": sha(f"{OUT}/dlw_targets_x0910.npz")}
R["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(R, open("/workspace/uplift_2026-09-11/r6/RECEIPT_BW345.json", "w"), indent=1)
print(json.dumps({"BW3": R["BW3_king_fea"]["verdict"], "BW3_diff_cells": R["BW3_king_fea"]["bitwise_diff"],
                  "BW3_wl_anchors": R["BW3_king_fea"]["whitelist_anchors_changed"],
                  "BW3_out_of_wl": R["BW3_king_fea"]["n_out_of_whitelist"],
                  "BW4": bw4["verdict"], "X4": R["X4_extended"]["verdict"], "X4_viol": len(viol),
                  "X5": x5}, indent=1), flush=True)
