"""build_alt_meta_hist.py — 'prod' caliber meta for dev_alt (same method as rolling_king dev_alt / refute_C6_2/build_alt_meta.py, sha printed):
rebuilt hist meta with y4 swapped for y4s = Π_{rows E+1..E+48}(1+ret5) − 1 (= expm1 of the log1p cumsum difference, NaN if <46 finite bars),
recomputed from the rebuilt hist cache for every meta anchor. Parity receipts: (1) Σ-simple over [E,E+47] recomputed == meta y4 bitwise;
(2) recomputed y4s == stage-7 dlw_targets_hist.y4s bitwise on common anchors; (3) recomputed Σ == dlw y4old bitwise. Also per-year cell-level
differences (bps). Output: data/meta_hist_newprod.npz (E_ts, members, y4:=y4s, qvk, names)."""
import os, sys, json, time, hashlib
import numpy as np
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")   # JR_ROOT only for the dry-test harness
sys.path.insert(0, f"{ROOT}/src"); from zload import zload
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
t0 = time.time()
Z = zload(f"{ROOT}/data/dlnative_5m_wide829_f16_hist.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); D = Z["data"]
r5 = D[:, :, 0].astype(np.float32); fin = np.isfinite(r5); r5z = np.where(fin, r5, 0).astype(np.float64); NW = r5.shape[1]; del D
CS_r = np.concatenate([np.zeros((1, NW)), np.cumsum(r5z, 0)]); CS_L = np.concatenate([np.zeros((1, NW)), np.cumsum(np.log1p(r5z), 0)]); CS_f = np.concatenate([np.zeros((1, NW), np.int32), np.cumsum(fin, 0, dtype=np.int32)])
print("cumsums", round(time.time() - t0, 1), "s", flush=True)
MT = np.load(f"{ROOT}/data/wide_fea_hist_meta_rebuilt.npz", allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]; names = MT["names"]
row = {int(t): k for k, t in enumerate(CTS)}; r = np.array([row[int(t)] for t in E_ts]); assert (r + 49 <= len(CTS)).all()
lo = r + 1; hi = r + 49; n = CS_f[hi] - CS_f[lo]
newprod = np.expm1(CS_L[hi] - CS_L[lo]).astype(np.float32); newprod[n < 46] = np.nan
oldsum = (CS_r[r + 48] - CS_r[r]).astype(np.float32); oldsum[(CS_f[r + 48] - CS_f[r]) < 46] = np.nan
rep = {"self_sha256": sha(os.path.abspath(__file__)), "method_ref": "refute_C6_2/build_alt_meta.py (pod2, 2026-09-04)"}
b = np.isfinite(oldsum) & np.isfinite(y4)
rep["parity_oldsum_vs_meta_y4"] = {"cells": int(b.sum()), "exact_eq": float((oldsum[b] == y4[b]).mean()), "max_abs": float(np.max(np.abs(oldsum[b] - y4[b]))), "nan_mismatch": int((np.isfinite(oldsum) ^ np.isfinite(y4)).sum())}
print("PARITY oldsum(rebuilt) vs meta y4:", rep["parity_oldsum_vs_meta_y4"], flush=True)
DT = np.load(f"{ROOT}/data/dlw_hist/data/dlw_targets.npz", allow_pickle=True); dts = DT["E_ts"].astype(np.int64); y4s = DT["y4s"]; y4old = DT["y4old"]
assert [str(s) for s in DT["symbols"]] == [str(s) for s in Z["symbols"]]
dm = {int(t): k for k, t in enumerate(dts)}; a = []; bb = []
for k, t in enumerate(E_ts):
    j = dm.get(int(t))
    if j is not None: a.append(k); bb.append(j)
a = np.array(a); bb = np.array(bb)
for nm, X, Y in (("newprod_vs_dlw_y4s", newprod[a], y4s[bb]), ("oldsum_vs_dlw_y4old", oldsum[a], y4old[bb])):
    m = np.isfinite(X) & np.isfinite(Y); rep[nm] = {"common_anchors": int(len(a)), "cells": int(m.sum()), "exact_eq": float((X[m] == Y[m]).mean()), "max_abs": float(np.max(np.abs(X[m] - Y[m]))), "nan_mismatch": int((np.isfinite(X) ^ np.isfinite(Y)).sum())}
    print("PARITY", nm, rep[nm], flush=True)
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); rep["by_year_bps"] = {}
for yv in sorted(set(yrs.tolist())):
    m = (yrs == yv)[:, None] & np.isfinite(oldsum) & np.isfinite(newprod)
    rep["by_year_bps"][str(yv)] = {"cells": int(m.sum()), "mean_newprod_minus_oldsum": float(np.mean(newprod[m] - oldsum[m]) * 1e4), "mean_abs": float(np.mean(np.abs(newprod[m] - oldsum[m])) * 1e4)}
print("by year (bps):", rep["by_year_bps"], flush=True)
np.savez(f"{ROOT}/data/meta_hist_newprod.npz", E_ts=E_ts, members=members, y4=newprod, qvk=qvk, names=names)
rep["out_sha256"] = sha(f"{ROOT}/data/meta_hist_newprod.npz"); rep["anchors_with_finite_newprod"] = int(np.isfinite(newprod).any(1).sum())
json.dump(rep, open(f"{ROOT}/results/alt_meta_receipt.json", "w"), indent=1)
print("saved", round(time.time() - t0, 1), "s; ALT_META_DONE", flush=True)
assert rep["parity_oldsum_vs_meta_y4"]["exact_eq"] == 1.0 and rep["newprod_vs_dlw_y4s"]["exact_eq"] == 1.0
