"""Which 2026 condition lifts the null floor from 0.365 to 0.944? One condition changed at a time.

lead 2026-09-26 (substitution method). Order is SEATS FIRST, because a correction I sent moments earlier
makes the seats the prime suspect rather than the chain:

    masked+renormalised seat means   [King, -, funding]
      pre-2026   [0.6460, 0, 0.3540]   King-dominated
      2026       [0.3142, 0, 0.6858]   funding-dominated -- reversed

Both books carry the SAME w[2]*fund_rank term, so for independent signals the floor is w2^2/(w0^2+w2^2):
      pre-2026   0.2309   (measured null floor 0.3651 -> chain adds +0.1342)
      2026       0.8265   (measured null floor 0.9441 -> chain adds +0.1176)
The chain's contribution is nearly CONSTANT; the flip is carried by the seats. My earlier claim that the
chain caused it used the WHOLE-AXIS census [0.589/0.411] instead of the per-segment weights -- retracted.

PREDICTIONS, written before running (so the probes can falsify them):
  A baseline          -> must reproduce 0.9441 (a known-number control; if it does not, stop)
  B seats<-pre2026    -> floor falls to ~0.35  (0.2309 + ~0.12 chain)
  C w[2]=0            -> floor falls well below that: the shared term is gone, leaving ~the chain's ~0.12
  D dead band off     -> small change only, since the chain's total contribution is ~0.12

ONE null f10, ONE shuffle seed, shared by every arm: only the substituted condition differs.
Nothing frozen is modified -- each arm is a mechanical substitution in the inputs/params assembled here.
"""
import os, sys, json, calendar, numpy as np
W = "/dev/shm/news2_2026-09-23"
sys.path.insert(0, f"{W}/devices"); sys.path.insert(0, f"{W}/engine")
from continuous_combo import evolve
from book_universe import align as align_universe, PATH as UPATH
MASK = "/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"
Y26 = calendar.timegm((2026, 1, 1, 0, 0, 0))
LO, HI = calendar.timegm((2023, 6, 30, 4, 0, 0)), calendar.timegm((2025, 12, 31, 20, 0, 0))
MIN_NAMES = 20
F = np.load(f"{W}/work/NEWS_FEATURES.npz"); leg = np.load(f"{W}/work/legs.npz")
a = F["anchors"].astype(np.int64); syms = F["symbols"]
off, mm = F["off"], F["m"].astype(np.int64)
members = [mm[off[i]:off[i+1]] for i in range(len(a))]
u = np.load(UPATH); mk = np.load(MASK)
crypto = np.load(f"{W}/receipts/P1_members_2025H2on.npz")["crypto"]
cand = mk["mask"] & crypto[None, :]
use = (a >= 1672531200) & (a <= u["ts"][-1]); au = a[use]
legal = align_universe(au, syms, u) & cand[use]
params0 = json.loads(open(f"{W}/inputs/bundle_config.json").read())["params"]
WL = leg["WL"][use].astype(np.float64)
ready = leg["ready"][use]; fin = np.isfinite(leg["WL"]).all(1)
pre_mask = (a >= LO) & (a <= HI) & leg["ready"] & fin
pre_mean = leg["WL"][pre_mask].mean(0).astype(np.float64)
sel = np.flatnonzero(au >= Y26)
is26 = au >= Y26

Z = np.load(sys.argv[1], allow_pickle=False)
base = np.nan_to_num(Z["lgbm"][use], nan=0.0).astype(np.float64)
rng = np.random.default_rng([20260926, 1])       # SAME seed as the original null control
null = base.copy()
for i in range(null.shape[0]):
    row = null[i]; nz = np.flatnonzero(row != 0)
    if len(nz) > 1:
        v = row[nz].copy(); rng.shuffle(v); row[nz] = v

def med(kc, fc):
    wp = []
    for j in sel:
        k, f = kc[j], fc[j]
        nz = (np.abs(k) > 1e-12) | (np.abs(f) > 1e-12)
        if nz.sum() >= MIN_NAMES and k[nz].std() > 0 and f[nz].std() > 0:
            wp.append(float(np.corrcoef(k[nz], f[nz])[0, 1]))
    return (float(np.median(wp)), float(np.mean(wp)), len(wp)) if wp else (None, None, 0)

def run(seats, params, label):
    P = evolve(f10=null, params=params, publication="scaled_diagnostic",
               anchors=au, king=leg["KZ"][use].astype(np.float64), fund=leg["ZFD"][use].astype(np.float64),
               seats=seats, rn8=leg["RN8"][use].astype(np.float64),
               members=[members[i] for i in np.flatnonzero(use)],
               qv=leg["QV"][use].astype(np.float64), legal=legal, ready=ready)
    m, mn, n = med(P["kc"], P["fc"])
    print("%-22s median %.4f  mean %.4f  (n=%d)" % (label, m, mn, n), flush=True)
    return {"median": m, "mean": mn, "n": n}

out = {}
out["A_baseline"] = run(WL, params0, "A baseline")
Wb = WL.copy(); Wb[is26] = pre_mean
out["B_seats_pre2026"] = run(Wb, params0, "B seats<-pre2026")
Wc = WL.copy(); Wc[is26, 2] = 0.0
out["C_w2_zero"] = run(Wc, params0, "C w[2]=0 on 2026")
pd = dict(params0); pd["band"] = 0.0
out["D_band_off"] = run(WL, pd, "D dead band off")
out["_pre_mean_raw_WL"] = [float(x) for x in pre_mean]
print()
print("pre-2026 raw WL mean used for arm B:", out["_pre_mean_raw_WL"])
json.dump(out, open(sys.argv[2], "w"), indent=1)
print("written", sys.argv[2])
