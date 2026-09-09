"""Receipt for the fea89 C:trend_288 outside-neighbourhood diffs. Recompute the RAW C:trend_288 (verbatim formula, pod_f8_build_ext.py L204-L216:
global cumsums of the log price p over the whole cache axis) from BOTH caches (holefix2 vs holefix) at the 'outside' anchors (step1_diag2) and a
control set, for all symbols. Expected mechanism: non-filled symbols bitwise equal; filled symbols differ at numerical-residue level (global-cumsum
cancellation) and only matter through float32 ties at the clipped saturation |rho|=1 -> cross-sectional rank (anchor_rank_block) tie groups.
Verifies also that anchor_rank_block(raw) reproduces the fea89 column in both trees."""
import numpy as np, json, time
from scipy.stats import rankdata
t0 = time.time()
def log(*a): print(f"[{time.time()-t0:6.0f}s]", *a, flush=True)
H = np.load("/workspace/review_scratch/holefix2_cells.npz", allow_pickle=True); FILLED = set(np.unique(H["col"]).tolist())
TG = np.load("/workspace/dlw_hf3/data/dlw_targets.npz", allow_pickle=True); E = TG["E_row"].astype(np.int64); Ets = TG["E_ts"].astype(np.int64); MS = TG["members"]; nA = len(E)
D2 = json.load(open("/workspace/review_scratch/v4_gates/step1_diag2.json"))
# outside anchors: rebuild from fea89 diff anchors (diag2 stored months only) -> recompute quickly from the two fea89 files for column C:trend_288
NW = 829
def fea_col(path, name):
    F = np.load(path, allow_pickle=True); names = [str(x) for x in F["names"]]; j = names.index(name); return F["pair_a"].astype(np.int64), F["pair_s"].astype(np.int64), F["X"][:, j].astype(np.float32)
pa4, ps4, x4 = fea_col("/workspace/f8_v4/data/f8_fea89.npz", "C:trend_288"); pa2, ps2, x2 = fea_col("/workspace/f8_hf2/data/f8_fea89.npz", "C:trend_288")
k4 = pa4 * NW + ps4; k2 = pa2 * NW + ps2; com = np.intersect1d(k4, k2); i4 = np.searchsorted(k4, com); i2 = np.searchsorted(k2, com); assert np.array_equal(k4[i4], com) and np.array_equal(k2[i2], com)
d = x4[i4] != x2[i2]; d &= ~(np.isnan(x4[i4]) & np.isnan(x2[i2])); diff_anchors = np.unique(com[d] // NW)
NEIGH = H["neigh_rows"]; nn = np.full(len(diff_anchors), -1)
for k, (lo, hi) in enumerate(NEIGH): nn[(E[diff_anchors] >= lo) & (E[diff_anchors] <= hi + 288)] = k   # +288: AMENDMENT 3 bound
OUT = diff_anchors[nn < 0]; log(f"trend_288 rank-diff anchors {len(diff_anchors)}, outside [start-48, end+8640+288]: {len(OUT)}")
rng = np.random.default_rng(20260909); CTRL = np.sort(rng.choice(np.setdiff1d(np.arange(nA), diff_anchors), 60, replace=False)); SEL = np.concatenate([OUT, CTRL]); SELROWS = E[SEL]
def raw_trend(cache):
    Z = np.load(cache); CD = Z["data"]; TT = CD.shape[0]; tidx = np.arange(TT, dtype=np.float64); hi = SELROWS + 1; lo = np.maximum(hi - 288, 0); out = np.full((len(SEL), NW), np.nan, np.float32)
    def cs(a): return np.concatenate([np.zeros((1, a.shape[1])), np.cumsum(a, 0, dtype=np.float64)])
    for c0 in range(0, NW, 128):
        ch = np.arange(c0, min(c0 + 128, NW)); r = CD[:, ch, 0].astype(np.float32); fin = np.isfinite(r); rz = np.where(fin, r, 0).astype(np.float64)
        p = np.cumsum(np.log1p(rz), 0); first = np.where(fin.any(0), fin.argmax(0), TT); pm = (np.arange(TT)[:, None] >= first[None, :]); pz = np.where(pm, p, 0.0); pmf = pm.astype(np.float64)
        CSpm = cs(pmf); CSp = cs(pz); CSp2 = cs(pz ** 2); CSt = cs(tidx[:, None] * pmf); CSt2 = cs(tidx[:, None] ** 2 * pmf); CStp = cs(tidx[:, None] * pz)
        n = CSpm[hi] - CSpm[lo]; nn_ = np.maximum(n, 1); Sp = CSp[hi] - CSp[lo]; Sp2 = CSp2[hi] - CSp2[lo]; St = CSt[hi] - CSt[lo]; St2 = CSt2[hi] - CSt2[lo]; Stp = CStp[hi] - CStp[lo]
        cov = Stp / nn_ - (St / nn_) * (Sp / nn_); vt = St2 / nn_ - (St / nn_) ** 2; vp = Sp2 / nn_ - (Sp / nn_) ** 2
        rho = cov / np.sqrt(np.maximum(vt * vp, 1e-30)); rho = np.clip(rho, -1, 1); tr = np.sign(rho) * rho ** 2; tr[(n < 144) | (vp <= 1e-20)] = np.nan
        out[:, ch] = tr.astype(np.float32); del CSpm, CSp, CSp2, CSt, CSt2, CStp, p, pz
    del CD, Z; return out
R4 = raw_trend("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"); log("raw trend holefix2 done"); R2 = raw_trend("/workspace/data/dlnative_5m_wide829_f16_holefix.npz"); log("raw trend holefix done")
def rank_block(v):
    v = np.asarray(v, np.float64); ok = np.isfinite(v); nok = ok.sum(); Rk = rankdata(v, nan_policy="omit"); Zr = (Rk - (nok + 1) / 2) / max(nok - 1, 1); Zr[~ok] = 0.0
    if nok < 10: Zr[:] = 0.0
    return Zr.astype(np.float32)
res = {"n_outside_anchors": int(len(OUT)), "n_control": int(len(CTRL)), "nonfilled_raw_bitwise_equal": True, "filled_raw_maxabs": 0.0, "filled_raw_n_diff": 0, "filled_raw_n_diff_saturation_only": 0, "rank_reproduces_fea89_v4": 0, "rank_reproduces_fea89_hf2": 0, "n_checked": 0, "control_all_equal": True, "examples": []}
kmap4 = {int(k): i for i, k in enumerate(k4)}; kmap2 = {int(k): i for i, k in enumerate(k2)}
for q, a in enumerate(SEL):
    m = MS[a]; ra = R4[q, m]; rb = R2[q, m]; fm = np.array([int(s) in FILLED for s in m]); ea = np.isnan(ra) & np.isnan(rb); neq = (ra != rb) & ~ea
    if (neq & ~fm).any(): res["nonfilled_raw_bitwise_equal"] = False
    if q >= len(OUT):
        if neq.any(): res["control_all_equal"] = False
        continue
    dd = np.abs(ra.astype(np.float64) - rb.astype(np.float64))[neq & fm]
    if dd.size: res["filled_raw_maxabs"] = max(res["filled_raw_maxabs"], float(dd.max())); res["filled_raw_n_diff"] += int(dd.size); res["filled_raw_n_diff_saturation_only"] += int(((np.abs(ra) == 1.0) | (np.abs(rb) == 1.0))[neq & fm].sum())
    za = rank_block(ra); zb = rank_block(rb); f4 = np.array([x4[kmap4[int(a * NW + s)]] for s in m]); f2 = np.array([x2[kmap2[int(a * NW + s)]] for s in m])
    res["n_checked"] += 1; res["rank_reproduces_fea89_v4"] += int(np.allclose(za, f4, atol=2e-7, equal_nan=True)); res["rank_reproduces_fea89_hf2"] += int(np.allclose(zb, f2, atol=2e-7, equal_nan=True))
    if len(res["examples"]) < 5 and neq.any():
        s0 = np.nonzero(neq)[0][0]; res["examples"].append({"anchor": time.strftime("%F %H:%MZ", time.gmtime(int(Ets[a]))), "symbol": int(m[s0]), "filled": bool(fm[s0]), "raw_v4": float(ra[s0]), "raw_hf2": float(rb[s0]), "n_rank_changed": int((za != zb).sum()), "n_tied_at_pm1_v4": int((np.abs(ra) == 1.0).sum()), "n_tied_at_pm1_hf2": int((np.abs(rb) == 1.0).sum())})
print(json.dumps(res, indent=1)); json.dump(res, open("/workspace/review_scratch/v4_gates/trend288_receipt.json", "w"), indent=1); log("TREND288_RECEIPT_DONE")
