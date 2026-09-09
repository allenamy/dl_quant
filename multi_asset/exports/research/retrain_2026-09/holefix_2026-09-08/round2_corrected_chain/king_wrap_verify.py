"""Hypothesis: pod_fea_ext.py L48-56 index cumsums with E - w UNCLAMPED; for anchors with E_row < 8640 the index is
negative and Python wraps to the END of the cumsum (cache tail). Verify numerically on one changed cell, both caches."""
import numpy as np, sys, time, calendar
sys.path.insert(0, "/workspace"); from zload import zload
def T(s): return time.strftime("%F %H:%MZ", time.gmtime(int(s)))
MO = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); eo = MO["E_ts"].astype(np.int64); names = [str(x) for x in MO["names"]]
E0 = calendar.timegm((2022, 1, 11, 0, 0, 0)); i = int(np.where(eo == E0)[0][0])
sym = [str(s) for s in zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)["symbols"]]; j = sym.index("AVAXUSDT")
col_v = names.index("cpos_mean_8640_v")
FO = np.load("/workspace/data/wide_fea_v2ext.npy", mmap_mode="r"); FN = np.load("/workspace/data/wide_fea_v2holefix.npy", mmap_mode="r")
print("anchor %s AVAXUSDT cpos_mean_8640_v : old %.6f new %.6f" % (T(E0), float(FO[i, j, col_v]), float(FN[i, j, col_v])))
for tag, path in (("OLD", "/workspace/data/dlnative_5m_wide829_f16_ext.npz"), ("NEW", "/workspace/data/dlnative_5m_wide829_f16_holefix.npz")):
    Z = zload(path, allow_pickle=True); CTS = Z["ts"].astype(np.int64); x = Z["data"][:, j, 2].astype(np.float32)   # cpos channel, one symbol
    fin = np.isfinite(x); s_ = np.concatenate([[0.0], np.cumsum(np.where(fin, x, 0).astype(np.float64))]); f_ = np.concatenate([[0], np.cumsum(fin)])
    E = int(np.where(CTS == E0)[0][0]); w = 8640; TT = len(s_)
    wrap = (s_[E] - s_[E - w]) / max(f_[E] - f_[E - w], 1)            # what the code does (E-w<0 -> wraps)
    clamp = (s_[E] - s_[max(E - w, 0)]) / max(f_[E] - f_[max(E - w, 0)], 1)
    print("  %s cache: E_row %d, E-w = %d -> wrapped row %d = %s | wrap-semantics value %.6f | clamp-semantics value %.6f"
          % (tag, E, E - w, TT + (E - w), T(CTS[TT - 1 + (E - w)]), wrap, clamp))
CTS0 = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)["ts"].astype(np.int64); rowof = {int(t): k for k, t in enumerate(CTS0)}
n_under = int(sum(1 for t in eo if rowof[int(t)] < 8640))
print("anchors in the deployed king meta with E_row < 8640 (30 days): %d (first %s .. last %s)" % (n_under, T(eo[0]), T(eo[n_under - 1])))
print("columns using the 8640 window: %s" % [n for n in names if "8640" in n])
