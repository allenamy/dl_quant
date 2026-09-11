"""Track F step 2: ex-ante regime labels + the per-regime arsenal table (PREREG §1-2).
Labels: expanding-median split of sig_fund and disp24, burn-in 2190 anchors, strictly past data.
Arsenal: g = net_ex/gross_total per anchor for each replayed form, bucketed by label.
"""
import numpy as np, time, json, calendar, os
R = "/workspace/uplift_2026-09-11/trackF"
Z = np.load(f"{R}/regime_vars.npz", allow_pickle=True)
RC = [str(c) for c in Z["cols"]]; V = Z["V"]; K = {c: i for i, c in enumerate(RC)}
ts_r = V[:, 0].astype(np.int64)

BURN = 2190
def expanding_median_label(x):
    """lab[i] in {0,1} vs the expanding median of x over indices < i (finite only); -1 during burn-in."""
    lab = np.full(len(x), -1, np.int8)
    for i in range(len(x)):
        if i < BURN: continue
        past = x[:i]; past = past[np.isfinite(past)]
        if len(past) < BURN // 2 or not np.isfinite(x[i]): continue
        lab[i] = 1 if x[i] > np.median(past) else 0
    return lab
LF = expanding_median_label(V[:, K["sig_fund"]])
LD = expanding_median_label(V[:, K["disp24"]])
LAB = np.full(len(ts_r), -1, np.int8)
ok = (LF >= 0) & (LD >= 0)
LAB[ok] = LF[ok] * 2 + LD[ok]          # 0=LL 1=LH 2=HL 3=HH   (first letter = sig_fund, second = disp24)
NAMES = {-1: "WARM", 0: "LL", 1: "LH", 2: "HL", 3: "HH"}
np.savez_compressed(f"{R}/regime_labels.npz", ts=ts_r, lab=LAB, lf=LF, ld=LD)

# ---- G4(i) leakage assertion: label at i is invariant to any permutation of rows > i
rng = np.random.default_rng(20260911)
for i in (3000, 6000, 9000):
    x = V[:, K["sig_fund"]].copy(); y = V[:, K["disp24"]].copy()
    p = rng.permutation(len(x) - i - 1) + i + 1
    x2 = x.copy(); x2[i + 1:] = x[p]; y2 = y.copy(); y2[i + 1:] = y[p]
    pf = x2[:i]; pf = pf[np.isfinite(pf)]; pd = y2[:i]; pd = pd[np.isfinite(pd)]
    l2 = (1 if x2[i] > np.median(pf) else 0) * 2 + (1 if y2[i] > np.median(pd) else 0)
    assert l2 == LAB[i], f"G4(i) FAIL at {i}: {l2} vs {LAB[i]}"
print("G4(i) future-shuffle invariance of the regime label: PASS at i=3000,6000,9000")

COLSR = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLSR)}
def load(tag, pref="w10_ablation_series__"):
    A = np.load(f"{R}/dev_v4F/probe_artifacts/{pref}{tag}.npz", allow_pickle=True)
    Rr = A["d30_n2_c42_rec"]; ts = np.round(Rr[:, 0]).astype(np.int64)
    return ts, Rr[:, C["net_ex"]] / Rr[:, C["gross_total"]], Rr, A
def stat(v):
    n = len(v)
    if n < 3: return dict(n=n, mean=float("nan"), sharpe=float("nan"), se_sharpe=float("nan"), se_mean=float("nan"))
    s = v.mean() / v.std(ddof=1) * np.sqrt(2190)
    return dict(n=n, mean=float(v.mean()), sharpe=float(s), se_sharpe=float(np.sqrt(2190 / n)), se_mean=float(v.std(ddof=1) / np.sqrt(n)))

ARMS = ["PARITY_A0_dyn_s42", "AR_KF_p0", "AR_FUND", "AR_KING", "AR_REV", "AR_ALL3_p45", "AR_ALL3_p0", "AR_F10", "AR_KF_noftrim"]
LBL = {"PARITY_A0_dyn_s42": "A0 in-service (king+fund, PHI.45)", "AR_KF_p0": "king+fund, no DL",
       "AR_FUND": "fund leg only", "AR_KING": "king leg only", "AR_REV": "rev24 leg only",
       "AR_ALL3_p45": "3 legs + DL", "AR_ALL3_p0": "3 legs, no DL", "AR_F10": "DL-slot book (PHI=1)",
       "AR_KF_noftrim": "A0 without FTRIM"}
tsA, gA, RA, AA = load(ARMS[0])
lmap = {int(t): LAB[i] for i, t in enumerate(ts_r)}
labA = np.array([lmap.get(int(t), -1) for t in tsA])
yr = np.array([time.gmtime(int(t)).tm_year for t in tsA])
out = {"labels": {}, "arsenal": {}, "regime_years": {}}
print("\n=== regime cell sizes (anchors) and year composition ===")
for L in (-1, 0, 1, 2, 3):
    m = labA == L
    if not m.any(): continue
    comp = {str(y): int((yr[m] == y).sum()) for y in range(2022, 2027)}
    out["regime_years"][NAMES[L]] = comp
    print(f"{NAMES[L]:5s} n={int(m.sum()):5d}  " + " ".join(f"{y}:{comp[str(y)]:5d}" for y in range(2022, 2027)))

print("\n=== ARSENAL: mean g [bps/anchor/gross] by regime cell (book layer, arm d30_n2_c42, dyn seat, s42) ===")
hdr = f"{'form':34s}" + "".join(f"{NAMES[L]:>16s}" for L in (0, 1, 2, 3)) + f"{'ALL(post-burn)':>18s}"
print(hdr)
for a in ARMS:
    try: ts, g, Rr, _ = load(a)
    except FileNotFoundError: print(f"{LBL[a]:34s}  MISSING"); continue
    lb = np.array([lmap.get(int(t), -1) for t in ts])
    row = {}
    line = f"{LBL[a]:34s}"
    for L in (0, 1, 2, 3):
        v = g[lb == L]; s = stat(v); row[NAMES[L]] = s
        line += f"{s['mean']:9.3f}({s['sharpe']:5.2f})" if np.isfinite(s['mean']) else f"{'--':>16s}"
    v = g[lb >= 0]; s = stat(v); row["ALL"] = s
    line += f"{s['mean']:11.3f}({s['sharpe']:5.2f})"
    out["arsenal"][a] = {"label": LBL[a], "cells": row,
                         "by_year": {str(y): stat(g[np.array([time.gmtime(int(t)).tm_year for t in ts]) == y]) for y in range(2022, 2027)}}
    print(line)

print("\n=== per-year g by form ===")
print(f"{'form':34s}" + "".join(f"{y:>10d}" for y in range(2022, 2027)))
for a in ARMS:
    if a not in out["arsenal"]: continue
    print(f"{LBL[a]:34s}" + "".join(f"{out['arsenal'][a]['by_year'][str(y)]['mean']:10.3f}" for y in range(2022, 2027)))

print("\n=== regime variable means per cell (descriptive) ===")
for L in (0, 1, 2, 3):
    m = LAB == L
    print(f"{NAMES[L]:5s} sig_fund {np.nanmean(V[m, K['sig_fund']]):7.2f}  disp24 {np.nanmean(V[m, K['disp24']]):7.4f}  "
          f"frac_neg {np.nanmean(V[m, K['frac_neg']]):6.3f}  vol7 {np.nanmean(V[m, K['vol7_med']]):7.4f}  "
          f"young30 {np.nanmean(V[m, K['young30']]):6.3f}  nmem {np.nanmean(V[m, K['nmem']]):6.1f}")
json.dump(out, open(f"{R}/RESULT_arsenal.json", "w"), indent=1)
print("\nwrote", f"{R}/RESULT_arsenal.json")
