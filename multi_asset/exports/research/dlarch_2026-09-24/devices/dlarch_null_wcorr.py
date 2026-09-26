"""Is condition 2's <=0.8 reachable at all? Null control on the weight correlation.

The residual prediction's book came out 0.966/0.969 correlated with King's book, failing lead's <=0.8.
Before reporting that as a fact about T2, ask whether ANY f10 input could pass: combo_target builds
    zkc = w[0]*king_rank + w[2]*fund_rank
    zfc = w[0]*zf        + w[2]*fund_rank
so both books carry the SAME funding term at the SAME weight. With 2026's masked seats (0.589/0.411) and
rank-uniform variances the z-level floor for INDEPENDENT signals is only ~0.33, so the shared term alone
does not explain 0.97 -- which points at the `chain` (EMA alpha .1, dead band, cap, renorm).

Control: feed a f10 whose cross-sectional ordering is DESTROYED (per-anchor name shuffle, marginal kept --
the population-preserving form, per AMENDMENT_2). If the median weight correlation stays ~0.95+, the
chain manufactures the correlation and lead's <=0.8 is unreachable for any arm; if it drops, 0.97 is a
real property of the residual prediction.
"""
import os, sys, json, calendar, numpy as np
W = "/dev/shm/news2_2026-09-23"
sys.path.insert(0, f"{W}/devices"); sys.path.insert(0, f"{W}/engine")
from continuous_combo import evolve
from book_universe import align as align_universe, PATH as UPATH
MASK = "/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"
Y2026 = calendar.timegm((2026, 1, 1, 0, 0, 0)); MIN_NAMES = 20
F = np.load(f"{W}/work/NEWS_FEATURES.npz"); leg = np.load(f"{W}/work/legs.npz")
a = F["anchors"].astype(np.int64); syms = F["symbols"]
off, mm = F["off"], F["m"].astype(np.int64)
members = [mm[off[i]:off[i+1]] for i in range(len(a))]
u = np.load(UPATH); mk = np.load(MASK)
crypto = np.load(f"{W}/receipts/P1_members_2025H2on.npz")["crypto"]
cand = mk["mask"] & crypto[None, :]
use = (a >= 1672531200) & (a <= u["ts"][-1]); au = a[use]
legal = align_universe(au, syms, u) & cand[use]
params = json.loads(open(f"{W}/inputs/bundle_config.json").read())["params"]
EV = dict(anchors=au, king=leg["KZ"][use].astype(np.float64), fund=leg["ZFD"][use].astype(np.float64),
          seats=leg["WL"][use].astype(np.float64), rn8=leg["RN8"][use].astype(np.float64),
          members=[members[i] for i in np.flatnonzero(use)], qv=leg["QV"][use].astype(np.float64),
          legal=legal, ready=leg["ready"][use])
sel = np.flatnonzero(au >= Y2026)

def med_wcorr(f10):
    P = evolve(f10=f10, params=params, publication="scaled_diagnostic", **EV)
    kc, fc = P["kc"], P["fc"]; wp = []
    for j in sel:
        k, f = kc[j], fc[j]
        nz = (np.abs(k) > 1e-12) | (np.abs(f) > 1e-12)
        if nz.sum() >= MIN_NAMES and k[nz].std() > 0 and f[nz].std() > 0:
            wp.append(float(np.corrcoef(k[nz], f[nz])[0, 1]))
    return float(np.median(wp)), len(wp)

Z = np.load(sys.argv[1], allow_pickle=False)
res = np.nan_to_num(Z["lgbm"][use], nan=0.0).astype(np.float64)
out = {}
out["residual_lgbm"] = med_wcorr(res)
rng = np.random.default_rng([20260926, 1])
sh = res.copy()
for i in range(sh.shape[0]):                      # per-anchor name shuffle: marginal kept, ordering gone
    row = sh[i]; nz = np.flatnonzero(row != 0)
    if len(nz) > 1: v = row[nz].copy(); rng.shuffle(v); row[nz] = v
out["null_shuffled"] = med_wcorr(sh)
out["king_itself"] = med_wcorr(np.nan_to_num(leg["KZ"][use], nan=0.0).astype(np.float64))
for k, v in out.items():
    print("%-16s median weight corr = %.4f  (n=%d anchors)" % (k, v[0], v[1]))
print()
print("reachability reading: if null_shuffled is also ~0.95+, the chain manufactures the correlation and")
print("lead's <=0.8 cannot be met by ANY arm; the number then measures the chain, not the arm.")
