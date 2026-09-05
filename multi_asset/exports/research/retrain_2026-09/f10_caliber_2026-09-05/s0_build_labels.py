#!/usr/bin/env python
"""s0_build_labels.py — PREREG_f10_caliber_sensitivity_2026-09-05: label parity receipts + §2 dev_alt2 meta (label (ii) Σ-simple over [E+1,E+48]).
Labels come from labels_lib.build_labels() (construction verbatim from refute_C6_2/build_alt_meta.py). No intermediate label file is written (volume at quota);
s1_decompose.py rebuilds the same arrays in-process from the same function.
Receipts: (i) bitwise vs meta y4; (iii) bitwise vs refute_C6_2 meta_newprod.npz y4 and vs dlw_targets y4s; (ii) bitwise vs refute_C6_2 meta_newsum.npz y4;
meta/meta_newsum_f10cal.npz written with the same npz keys as meta_newprod (E_ts, members, y4, qvk, names; np.savez uncompressed) and re-read: y4 bitwise == (ii).
Writes only meta/meta_newsum_f10cal.npz and results/s0_receipts.json. Run with WRITE_META=0 to produce receipts only.
"""
import numpy as np, time, json, hashlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from labels_lib import build_labels, CACHE, META
ROOT = "/workspace/review_scratch/f10_caliber"
NEWPROD = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz"; NEWSUM_REF = "/workspace/review_scratch/refute_C6_2/altrun/meta_newsum.npz"
DLW = "/workspace/port_w10/dlw_2026-08-22/data/dlw_targets.npz"; WRITE_META = int(os.environ.get("WRITE_META", "1"))
t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
rep = {"self_sha256": sha(os.path.abspath(__file__)), "labels_lib_sha256": sha(os.path.join(os.path.dirname(os.path.abspath(__file__)), "labels_lib.py")),
       "inputs": {k: sha(p) for k, p in (("cache", CACHE), ("meta", META), ("meta_newprod", NEWPROD), ("meta_newsum_ref", NEWSUM_REF), ("dlw_targets", DLW))},
       "label_rule": {"i": "sum r5 rows [E, E+47] (CS_r[E+48]-CS_r[E]), NaN if finite bars < 46", "ii": "sum r5 rows [E+1, E+48] (CS_r[E+49]-CS_r[E+1]), NaN if finite bars < 46",
                      "iii": "expm1(CS_L[E+49]-CS_L[E+1]) with CS_L = cumsum(log1p(r5)), NaN if finite bars < 46", "cache_ts": "bar close (pod_merge_cache_ext.py L24: ts = open_time + 5min)"}}
log("input sha256", json.dumps(rep["inputs"]))
Lb = build_labels(log); E_ts = Lb["E_ts"]; oldsum, newsum, newprod = Lb["oldsum"], Lb["newsum"], Lb["newprod"]; conv = Lb["conv"]; rk = Lb["rk"]; rE48 = Lb["rE48"]; syms5 = Lb["symbols"]
y4 = Lb["meta"]["y4"]; members = Lb["meta"]["members"]; qvk = Lb["meta"]["qvk"]; names = Lb["meta"]["names"]
def parity(nm, X, Yv):
    b = np.isfinite(X) & np.isfinite(Yv); d = np.abs(X[b].astype(np.float64) - Yv[b].astype(np.float64))
    out = {"cells_both_finite": int(b.sum()), "exact_eq_frac": float((X[b] == Yv[b]).mean()) if b.sum() else None, "max_abs_diff": float(d.max()) if b.sum() else None, "nan_pattern_mismatch": int((np.isfinite(X) ^ np.isfinite(Yv)).sum())}
    print(f"PARITY {nm}: {json.dumps(out)}", flush=True); return out
rep["receipts"] = {}
rep["receipts"]["(i) oldsum vs meta y4"] = parity("(i) oldsum vs meta y4", oldsum, y4)
NP = np.load(NEWPROD, allow_pickle=True); assert np.array_equal(NP["E_ts"].astype(np.int64), E_ts)
rep["receipts"]["(iii) newprod vs refute_C6_2 meta_newprod y4"] = parity("(iii) newprod vs meta_newprod y4", newprod, NP["y4"])
NS = np.load(NEWSUM_REF, allow_pickle=True); assert np.array_equal(NS["E_ts"].astype(np.int64), E_ts)
rep["receipts"]["(ii) newsum vs refute_C6_2 meta_newsum y4"] = parity("(ii) newsum vs meta_newsum y4", newsum, NS["y4"])
DT = np.load(DLW, allow_pickle=True); dts = DT["E_ts"].astype(np.int64); assert [str(s) for s in DT["symbols"]] == syms5
dm = {int(t): k for k, t in enumerate(dts)}; a = []; bb = []
for k, t in enumerate(E_ts):
    j = dm.get(int(t))
    if j is not None: a.append(k); bb.append(j)
a = np.array(a); bb = np.array(bb)
rep["receipts"]["(iii) newprod vs dlw y4s (common anchors)"] = dict(parity("(iii) newprod vs dlw y4s", newprod[a], DT["y4s"][bb]), common_anchors=int(len(a)))
rep["receipts"]["(i) oldsum vs dlw y4old (common anchors)"] = dict(parity("(i) oldsum vs dlw y4old", oldsum[a], DT["y4old"][bb]), common_anchors=int(len(a)))
b = np.isfinite(oldsum) & np.isfinite(newsum) & np.isfinite(rk[3]) & np.isfinite(rE48)
d1 = (newsum[b].astype(np.float64) - oldsum[b]) - (rE48[b].astype(np.float64) - rk[3][b])
b2 = np.isfinite(newsum) & np.isfinite(newprod) & np.isfinite(conv)
d2 = (newprod[b2].astype(np.float64) - newsum[b2]); c2 = 0.5 * conv[b2].astype(np.float64)
rep["identities"] = {"(ii)-(i) == r_E48 - r_E : max_abs_dev": float(np.abs(d1).max()), "cells": int(b.sum()),
                     "(iii)-(ii) vs 0.5*conv : corr": float(np.corrcoef(d2, c2)[0, 1]), "mean (iii)-(ii) bps": float(d2.mean() * 1e4), "mean 0.5*conv bps": float(c2.mean() * 1e4), "cells2": int(b2.sum())}
print("IDENTITIES", json.dumps(rep["identities"]), flush=True)
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); rep["cell_means_by_year_bps"] = {}
for yv in (2022, 2023, 2024, 2025, 2026):
    m = yrs == yv; bm = m[:, None] & np.isfinite(oldsum) & np.isfinite(newsum) & np.isfinite(newprod)
    rep["cell_means_by_year_bps"][str(yv)] = {"cells": int(bm.sum()), "mean(ii)-(i)": float(np.mean(newsum[bm] - oldsum[bm]) * 1e4), "mean|(ii)-(i)|": float(np.mean(np.abs(newsum[bm] - oldsum[bm])) * 1e4),
                                             "mean(iii)-(ii)": float(np.mean(newprod[bm] - newsum[bm]) * 1e4), "mean|(iii)-(ii)|": float(np.mean(np.abs(newprod[bm] - newsum[bm])) * 1e4)}
print("CELL_MEANS", json.dumps(rep["cell_means_by_year_bps"]), flush=True)
os.makedirs(f"{ROOT}/meta", exist_ok=True); os.makedirs(f"{ROOT}/results", exist_ok=True)
if WRITE_META:
    np.savez(f"{ROOT}/meta/meta_newsum_f10cal.npz", E_ts=E_ts, members=members, y4=newsum, qvk=qvk, names=names)
    M2 = np.load(f"{ROOT}/meta/meta_newsum_f10cal.npz", allow_pickle=True)
    assert np.array_equal(M2["y4"], newsum, equal_nan=True) and np.array_equal(M2["E_ts"], E_ts) and np.array_equal(M2["qvk"], qvk, equal_nan=True) and list(M2.files) == list(NP.files), (list(M2.files), list(NP.files))
    assert all(np.array_equal(M2["members"][k], members[k]) for k in range(len(E_ts)))
    rep["outputs"] = {"meta_newsum_f10cal": sha(f"{ROOT}/meta/meta_newsum_f10cal.npz"), "meta_keys": list(M2.files), "meta_newsum_f10cal y4 bitwise == (ii)": True,
                      "meta_newsum_f10cal y4 bitwise == refute_C6_2 meta_newsum y4": bool(np.array_equal(M2["y4"], NS["y4"], equal_nan=True)), "size_bytes": os.path.getsize(f"{ROOT}/meta/meta_newsum_f10cal.npz")}
else:
    rep["outputs"] = {"meta_newsum_f10cal": "NOT WRITTEN (WRITE_META=0)"}
json.dump(rep, open(f"{ROOT}/results/s0_receipts.json", "w"), indent=1)
print("OUTPUTS", json.dumps(rep["outputs"]), flush=True)
log("DONE")
