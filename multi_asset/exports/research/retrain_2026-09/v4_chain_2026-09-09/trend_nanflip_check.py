"""Verify the reviewer's finding on my own device: NaN<->finite flips of raw trend_288 for filled symbols between holefix and holefix2, and that my
receipt's max|Δ| silently excluded them (NaN propagation in max). Recompute raw trend_288 at the reviewer's example (FTMUSDT 2025-01-08 08Z) and count flips over the 247 outside anchors."""
import numpy as np, json, time
def cs(a): return np.concatenate([np.zeros((1, a.shape[1])), np.cumsum(a, 0, dtype=np.float64)])
TG = np.load("/workspace/dlw_hf3/data/dlw_targets.npz", allow_pickle=True); E = TG["E_row"].astype(np.int64); Ets = TG["E_ts"].astype(np.int64); syms = [str(s) for s in TG["symbols"]]
H = np.load("/workspace/review_scratch/holefix2_cells.npz", allow_pickle=True); FILLED = sorted(set(np.unique(H["col"][H["row"] < 100000]).tolist()))   # 2022 fills only (49 symbols)
rec = json.load(open("/workspace/review_scratch/v4_gates/trend288_receipt.json")); ex_a = int(np.where(Ets == 1736323200)[0][0]) if (Ets == 1736323200).any() else None   # 2025-01-08 08Z
def raw_trend(cache, cols, rows):
    Z = np.load(cache); CD = Z["data"]; TT = CD.shape[0]; tidx = np.arange(TT, dtype=np.float64); hi = rows + 1; lo = np.maximum(hi - 288, 0)
    r = CD[:, cols, 0].astype(np.float32); fin = np.isfinite(r); rz = np.where(fin, r, 0).astype(np.float64); p = np.cumsum(np.log1p(rz), 0); first = np.where(fin.any(0), fin.argmax(0), TT); pm = (np.arange(TT)[:, None] >= first[None, :]); pz = np.where(pm, p, 0.0); pmf = pm.astype(np.float64)
    CSpm = cs(pmf); CSp = cs(pz); CSp2 = cs(pz ** 2); CSt = cs(tidx[:, None] * pmf); CSt2 = cs(tidx[:, None] ** 2 * pmf); CStp = cs(tidx[:, None] * pz)
    n = CSpm[hi] - CSpm[lo]; nn = np.maximum(n, 1); Sp = CSp[hi] - CSp[lo]; Sp2 = CSp2[hi] - CSp2[lo]; St = CSt[hi] - CSt[lo]; St2 = CSt2[hi] - CSt2[lo]; Stp = CStp[hi] - CStp[lo]
    cov = Stp / nn - (St / nn) * (Sp / nn); vt = St2 / nn - (St / nn) ** 2; vp = Sp2 / nn - (Sp / nn) ** 2; rho = np.clip(cov / np.sqrt(np.maximum(vt * vp, 1e-30)), -1, 1); tr = np.sign(rho) * rho ** 2; tr[(n < 144) | (vp <= 1e-20)] = np.nan
    del CD, Z; return tr.astype(np.float32), vp
# outside anchors from the receipt run: re-derive the same set (247) by reading the diag2 anchor list is not stored; use all anchors of 2023+ for the 49 filled symbols instead (superset), count NaN flips
rows = E[Ets >= 1672531200]; cols = np.array(FILLED)
t4, vp4 = raw_trend("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz", cols, rows); t2, vp2 = raw_trend("/workspace/data/dlnative_5m_wide829_f16_holefix.npz", cols, rows)
n4, n2 = np.isnan(t4), np.isnan(t2); flips = (n4 != n2); both = ~n4 & ~n2
print("2023+ anchors", len(rows), "x filled symbols", len(cols), "| NaN<->finite flips", int(flips.sum()), "| both-finite cells differing", int((both & (t4 != t2)).sum()), "| both-finite max|Δ|", float(np.abs(t4[both] - t2[both]).max()))
fl = np.argwhere(flips); bysym = {}
for r_, c_ in fl: bysym.setdefault(syms[cols[c_]], 0); bysym[syms[cols[c_]]] += 1
print("flips by symbol:", bysym)
if ex_a is not None:
    ri = int(np.where(rows == E[ex_a])[0][0]) if (rows == E[ex_a]).any() else None; ci = FILLED.index(syms.index("FTMUSDT")) if "FTMUSDT" in syms and syms.index("FTMUSDT") in FILLED else None
    if ri is not None and ci is not None: print("FTMUSDT 2025-01-08 08Z: holefix vp", float(vp2[ri, ci]), "trend", float(t2[ri, ci]), "| holefix2 vp", float(vp4[ri, ci]), "trend", float(t4[ri, ci]))
print("my receipt filled_raw_maxabs =", rec["filled_raw_maxabs"], "(computed on neq & both-finite cells only where NaN entered as NaN -> excluded by max(prev, nan))")
