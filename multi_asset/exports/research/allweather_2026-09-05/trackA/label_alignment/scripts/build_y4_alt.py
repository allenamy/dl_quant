"""build_y4_alt.py — target-alignment receipts and alternative targets (diagnostic layer for the S1 admission of A1).
FACT (from pod_fea_ext.py L33-34 + pod_build_wide_ext.py row convention): META y4 = Σ ret5 over cache rows E..E+47 where row E holds the bar that
CLOSES at the anchor (ret from close(E-5m) to close(E)); i.e. the frozen S1 target starts at the E-5min close = the same price time as the panel's
last feature bar (row E-1 closes at E-5m). A price-level feature evaluated at that close (spot/perp basis) shares its noise with the target's start
price (bid-ask bounce). This script builds:
  y4_startE.npz  : y4_alt = Σ ret5 over rows E+1..E+48 (target starts at the E close; NaN if < 46 finite bars, same rule as the meta) -> S1 sensitivity
  meta_exec25.npz: copy of the prod-caliber meta (meta_newprod) with y4 := Π(1+ret5) - 1 over rows E+6..E+48 (from the E+25min close, the first full
                   bar after the live N+23 execution; NaN if any bar missing) -> S2 secondary caliber
and prints the meta_newprod row-convention check (max |meta_newprod y4 - Π(1+r)-1 over rows E+a..E+b| for the candidate (a,b) windows).
env: ROOT META_IN META_PROD"""
import os, sys, json, hashlib
import numpy as np
ROOT = os.environ.get("ROOT", "/workspace/review_scratch/allweather_trackA"); SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
sys.path.insert(0, "/workspace")
from zload import zload
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); T0 = int(CTS[0]); RET = np.asarray(Z["data"][:, :, 0], np.float32); del Z
MT = np.load(os.environ.get("META_IN", "/workspace/data/wide_fea_v2ext_meta.npz"), allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); y4 = MT["y4"]
MP = np.load(os.environ.get("META_PROD", "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz"), allow_pickle=True); y4p = MP["y4"]
assert np.array_equal(MP["E_ts"].astype(np.int64), E_ts)
Ei = (E_ts - T0) // 300; assert np.all(CTS[Ei] == E_ts)
fin = np.isfinite(RET); CS = np.concatenate([np.zeros((1, 829)), np.cumsum(np.where(fin, RET, 0), 0, dtype=np.float64)]); CN = np.concatenate([np.zeros((1, 829), int), np.cumsum(fin, 0)])
CL = np.concatenate([np.zeros((1, 829)), np.cumsum(np.where(fin, np.log1p(np.clip(RET, -0.99, None)), 0), 0, dtype=np.float64)])
def ssum(a, b): return CS[Ei + b + 1] - CS[Ei + a], CN[Ei + b + 1] - CN[Ei + a]
def prod(a, b): s = CL[Ei + b + 1] - CL[Ei + a]; n = CN[Ei + b + 1] - CN[Ei + a]; return np.expm1(s), n
rec = {"self_sha256": SELF}
if os.environ.get("ACC_ONLY") == "1":   # PREREG_king_label_alignment §1 ALT_ACC: Π(1+r)−1 over rows E+1..E+48 by the same method, same NaN rule as y4_startE; writes only this file
    pa, na = prod(1, 48); yacc = pa.astype(np.float32); yacc[na < 46] = np.nan; yacc[~np.isfinite(y4)] = np.nan
    np.savez_compressed(f"{ROOT}/features/y4_startE_acc.npz", y4=yacc, E_ts=E_ts, definition="prod(1+ret5)-1 over rows E+1..E+48 (accounting form, target starts at the E close), NaN where meta y4 NaN or <46 bars", self_sha256=SELF)
    okc = np.isfinite(yacc) & np.isfinite(y4p); print(f"y4_startE_acc finite {np.isfinite(yacc).sum()} vs meta_newprod y4 on {okc.sum()} common cells max|Δ| {np.abs(yacc - y4p)[okc].max():.3e}", flush=True)
    print("Y4ACC_DONE", flush=True); sys.exit(0)
s, n = ssum(0, 47); ok = np.isfinite(y4) & (n >= 46); rec["meta_y4_vs_sum_rows_E..E+47"] = {"max_abs": float(np.abs(s - y4)[ok].max()), "n": int(ok.sum())}
s1, n1 = ssum(1, 48); ok1 = np.isfinite(y4) & (n1 >= 46); rec["meta_y4_vs_sum_rows_E+1..E+48"] = {"max_abs": float(np.abs(s1 - y4)[ok1].max()), "share_gt_1e-3": float((np.abs(s1 - y4)[ok1] > 1e-3).mean())}
for a, b in ((0, 47), (1, 48)):
    p, n = prod(a, b); ok = np.isfinite(y4p) & (n == 48); rec[f"meta_newprod_vs_prod_rows_E+{a}..E+{b}"] = {"max_abs": float(np.abs(p - y4p)[ok].max()), "p999": float(np.percentile(np.abs(p - y4p)[ok], 99.9)), "n": int(ok.sum())}
print(json.dumps(rec, indent=1), flush=True)
# y4 alt (simple sum, start at E close)
ya = s1.astype(np.float32); ya[n1 < 46] = np.nan; ya[~np.isfinite(y4)] = np.nan   # keep the meta's finite support (members were selected on it)
np.savez_compressed(f"{ROOT}/features/y4_startE.npz", y4=ya, E_ts=E_ts, definition="sum ret5 rows E+1..E+48 (target starts at the E close), NaN where meta y4 NaN or <46 bars", self_sha256=SELF)
print(f"y4_startE finite {np.isfinite(ya).sum()} (meta {np.isfinite(y4).sum()})", flush=True)
# prod-caliber exec-window meta
pe, ne = prod(6, 48); ye = pe.astype(np.float32); ye[ne < 43] = np.nan; ye[~np.isfinite(y4p)] = np.nan
np.savez_compressed(f"{ROOT}/features/meta_exec25.npz", E_ts=E_ts, members=MP["members"], y4=ye, qvk=MP["qvk"], names=MP["names"],
                    definition="prod caliber Π(1+ret5)-1 over rows E+6..E+48 (from the E+25min close), NaN where meta_newprod NaN or any bar missing", self_sha256=SELF)
print(f"meta_exec25 finite {np.isfinite(ye).sum()} (meta_newprod {np.isfinite(y4p).sum()}) mean|y4| exec {np.nanmean(np.abs(ye))*1e4:.1f} bps vs prod {np.nanmean(np.abs(y4p))*1e4:.1f} bps", flush=True)
json.dump(rec, open(f"{ROOT}/results/target_alignment_receipt.json", "w"), indent=1); print("Y4ALT_DONE", flush=True)
