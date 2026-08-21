#!/usr/bin/env python3
"""ARM-IPCA (race arm #1, CPU) — linear conditional factor scaffold on the wide hourly panel.

Paradigm (Kelly-Pruitt-Su restricted IPCA; crypto precedent Bianchi-Babiak N~250): model each
period's asset loadings as a linear map of its CHARACTERISTICS,  beta_{i,t} = z_{i,t} Gamma
(Gamma: L x K), and estimate latent factors f_t + Gamma by alternating least squares on the
managed-portfolio moments  x_t = Z_t' r_t,  W_t = Z_t' Z_t.

WHY this arm (not a backbone swap): the restricted-IPCA conditional MEAN forecast collapses to a
static linear tilt  Z_t (Gamma * E[f])  == cross-sectional Ridge on characteristics, so it adds
nothing new as a return forecast. The DIFFERENTIATOR is the IPCA RESIDUAL  eps = r - Z Gamma f:
it is cross-sectionally orthogonal to the SPAN of [funding+zoo] characteristics BY CONSTRUCTION,
so residual-momentum / residual-reversal built on eps are, mechanically, incremental-over-carry
candidates. Pre-reg (paradigm doc row 5): IPCA residual-mom/rev +>=0.002 orthogonal rank-IC,
per-fold sign-consistent; K=8 must NOT beat K<=4 (overfit check).

Leak safety: Gamma is fit on TRAIN periods only. Per-period f_t is a cross-sectional projection
(contemporaneous r_t) used only to DEFINE the residual; the residual-momentum signal at hour t
uses eps_{<t} exclusively (shift-by-1 cumulative), so the tradeable feature is strictly causal.
Scored on the incremental target YR{H} (already [funding+zoo]-residualised) + raw Y{H} for context.

Usage:
  PYTHONPATH=. python multi_asset/data/arm_ipca.py --smoke
  PYTHONPATH=. python multi_asset/data/arm_ipca.py --K 4 --nperm 30
"""
from __future__ import annotations
import argparse
import json
import os.path as p

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from multi_asset.data.wide_factory import build_factors, _ic_days

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
PANEL = E + "/wide_panel.npz"
WIDE_DL = E + "/wide_dl.npz"
HOUR_MS = 3_600_000

# instrument set = the causal characteristic suite (funding + zoo). IPCA residual is orthogonal to
# the cross-sectional span of THESE, which is exactly the [funding+zoo] baseline we want to beat.
DROP_INSTR = ()   # keep all build_factors characteristics as instruments


def _xs_rank_std(A, MEM):
    """Cross-sectionally rank-standardise each characteristic to [-0.5, 0.5] per ts over active,
    finite assets (KPS convention). Non-members / non-finite -> 0 (neutral instrument)."""
    Z = np.zeros_like(A, dtype=np.float64)
    for i in range(A.shape[0]):
        v = MEM[i] & np.isfinite(A[i])
        n = int(v.sum())
        if n >= 8:
            r = rankdata(A[i, v]) - 1.0
            Z[i, v] = r / (n - 1) - 0.5
    return Z


def build_instruments(z, MEM):
    """(T, N, L) rank-standardised characteristic tensor + names, from build_factors."""
    F = build_factors(z)
    names, mats = [], []
    for nm, (Xf, _sign) in F.items():
        if nm in DROP_INSTR:
            continue
        names.append(nm)
        mats.append(_xs_rank_std(np.asarray(Xf, dtype=np.float64), MEM))
    Z = np.stack(mats, axis=2)                              # (T,N,L)
    return Z, names


def ipca_als(Z, R, MEM, day_mask, K, n_iter=50, tol=1e-6, ridge=1e-6, seed=0):
    """Restricted IPCA via managed-portfolio ALS on the TRAIN periods (day_mask True).
    Z (T,N,L), R (T,N) returns, MEM (T,N) bool. Returns Gamma (L,K)."""
    T, N, L = Z.shape
    # per-period managed moments over TRAIN periods with >=K+2 active finite-return assets
    xs, Ws, tr_idx = [], [], []
    for t in np.where(day_mask)[0]:
        v = MEM[t] & np.isfinite(R[t])
        if v.sum() < K + 2:
            continue
        Zt = Z[t, v, :]                                    # (n,L)
        rt = R[t, v]                                       # (n,)
        n = Zt.shape[0]
        xs.append(Zt.T @ rt / n)                           # (L,)
        Ws.append(Zt.T @ Zt / n)                           # (L,L)
        tr_idx.append(t)
    X = np.stack(xs)                                       # (Tt,L)
    Wst = np.stack(Ws)                                     # (Tt,L,L)
    Tt = X.shape[0]
    rng = np.random.default_rng(seed)
    # init Gamma from the top-K eigenvectors of mean managed 2nd moment
    M = np.mean([x[:, None] * x[None, :] for x in X], axis=0)
    w, V = np.linalg.eigh(M + ridge * np.eye(L))
    Gamma = V[:, -K:].copy()
    prev = np.inf
    Ilr = ridge * np.eye(L * K)
    for it in range(n_iter):
        # 1) f_t = (G' W_t G)^-1 G' x_t
        Fmat = np.zeros((Tt, K))
        for j in range(Tt):
            A = Gamma.T @ Wst[j] @ Gamma + ridge * np.eye(K)
            Fmat[j] = np.linalg.solve(A, Gamma.T @ X[j])
        # 2) vec(Gamma) = [sum (f f' kron W)]^-1 [sum (f kron x)]
        Aacc = np.zeros((L * K, L * K)); bacc = np.zeros(L * K)
        for j in range(Tt):
            f = Fmat[j]
            Aacc += np.kron(np.outer(f, f), Wst[j])
            bacc += np.kron(f, X[j])
        vecG = np.linalg.solve(Aacc + Ilr, bacc)
        Gamma = vecG.reshape(K, L).T                        # vec stacks columns -> (L,K)
        # convergence on fit residual of the managed moments
        err = 0.0
        for j in range(Tt):
            err += float(np.sum((X[j] - Wst[j] @ Gamma @ Fmat[j]) ** 2))
        if abs(prev - err) / (abs(prev) + 1e-12) < tol:
            break
        prev = err
    return Gamma


def ipca_residuals(Z, R, MEM, Gamma, ridge=1e-6):
    """Per-period f_t (cross-sectional projection given Gamma) + residual eps = r - Z Gamma f.
    Computed on ALL periods; residual is contemporaneous (its use downstream is shift-by-1)."""
    T, N, L = Z.shape
    K = Gamma.shape[1]
    eps = np.full((T, N), np.nan)
    for t in range(T):
        v = MEM[t] & np.isfinite(R[t])
        if v.sum() < K + 2:
            continue
        Zt = Z[t, v, :]; rt = R[t, v]
        B = Zt @ Gamma                                     # (n,K) conditional betas
        f = np.linalg.solve(B.T @ B + ridge * np.eye(K), B.T @ rt)
        eps[t, v] = rt - B @ f
    return eps


def resid_signals(eps, MEM):
    """Causal residual-momentum / reversal candidates from eps (T,N). Each uses PAST residuals only
    (shift-by-1 cumulative), so the feature at hour t is strictly <t."""
    T, N = eps.shape
    e0 = np.where(np.isfinite(eps), eps, 0.0)
    fin = np.isfinite(eps).astype(np.float64)
    df = pd.DataFrame(e0); dc = pd.DataFrame(fin)
    out = {}
    for k in (24, 72, 168):                                # residual momentum (sum past-k, shifted)
        s = df.rolling(k, min_periods=k // 2).sum().shift(1).values
        c = dc.rolling(k, min_periods=k // 2).sum().shift(1).values
        sig = np.where(c > k // 2, s, np.nan)
        out[f"ipca_resmom_{k}h"] = (sig, +1)               # momentum -> long past winners
    for k in (1, 3):                                       # residual reversal (short recent)
        s = df.rolling(k, min_periods=1).sum().shift(1).values
        c = dc.rolling(k, min_periods=1).sum().shift(1).values
        sig = np.where(c >= 1, s, np.nan)
        out[f"ipca_resrev_{k}h"] = (sig, -1)               # reversal -> fade recent residual
    return out


def _resid_target(Y, MEM):
    """xsec-demean raw Y over active assets per ts (for the raw-Y context score)."""
    Yr = np.full_like(Y, np.nan)
    for i in range(len(Y)):
        v = MEM[i] & np.isfinite(Y[i])
        if v.sum() >= 8:
            Yr[i, v] = Y[i, v] - Y[i, v].mean()
    return Yr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--K", type=int, default=0, help="0 -> sweep {3,4,5,8}; else single K")
    ap.add_argument("--nperm", type=int, default=20)
    ap.add_argument("--smoke", action="store_true", help="fit on a short slice, K=4, few candidates")
    a = ap.parse_args()

    z = np.load(PANEL, allow_pickle=True)
    ts = z["ts"].astype(np.int64); Y1 = z["Y"].astype(np.float64); MEM = z["MEMBER"]
    logc = np.log(np.where(z["CLOSE"].astype(np.float64) > 0, z["CLOSE"].astype(np.float64), np.nan))
    R = logc - np.vstack([np.full((1, logc.shape[1]), np.nan), logc[:-1]])   # 1h log return (t vs t-1)
    dayidx = ((ts - ts[0]) // (HOUR_MS * 24)).astype(np.int64)
    nD = int(dayidx.max()) + 1

    # incremental target YR4 (already [funding+zoo]-residualised) from wide_dl, ts-aligned
    dl = np.load(WIDE_DL, allow_pickle=True)
    assert np.array_equal(dl["ts"].astype(np.int64), ts), "panel/wide_dl ts mismatch"
    YR4 = dl["YR4"].astype(np.float64); Yraw4 = dl["Y4"].astype(np.float64)
    Yraw4_r = _resid_target(Yraw4, MEM)

    Z, instr = build_instruments(z, MEM)
    print(f"[ipca] panel T={len(ts)} N={MEM.shape[1]} active={int(MEM.any(0).sum())} "
          f"instruments L={len(instr)}: {instr}", flush=True)

    # walk-forward: fit Gamma on train (all days < test block start - embargo), eval on 3 OOS blocks
    if a.smoke:
        nD_use = min(nD, 220)
        folds = [(nD_use - 60, nD_use)]
        Ks = [4]
    else:
        folds = [(nD - 240, nD - 160), (nD - 160, nD - 80), (nD - 80, nD)]
        Ks = [a.K] if a.K else [3, 4, 5, 8]
    fold_days = [np.arange(a0, a1) for a0, a1 in folds]
    all_days = np.concatenate(fold_days)
    rng = np.random.default_rng(0)

    results = []
    for K in Ks:
        # fit ONE Gamma per fold on that fold's train window, stitch residuals over the OOS block
        eps = np.full_like(R, np.nan)
        for (a0, a1) in folds:
            train_mask = dayidx < (a0 - 2)                 # 2-day embargo before the block
            if train_mask.sum() < 200:
                continue
            Gamma = ipca_als(Z, R, MEM, train_mask, K)     # Gamma fit on TRAIN periods only
            ep = ipca_residuals(Z, R, MEM, Gamma)
            blk = np.isin(dayidx, np.arange(a0, a1))
            eps[blk] = ep[blk]                              # block ALWAYS uses its own fold Gamma
            # backfill the momentum lookback (<=168h) ONLY for rows no block has filled yet, so a
            # later fold never overwrites an earlier block; every filled hour keeps a Gamma trained
            # before it (causal). Row-level: a pred-hour is filled all-or-nothing per fold.
            unfilled = ~np.isfinite(eps).any(axis=1)        # (T,) rows with no residual yet
            pre = np.isin(dayidx, np.arange(max(0, a0 - 8), a0)) & unfilled
            eps[pre] = ep[pre]
        cands = resid_signals(eps, MEM)
        if a.smoke:
            cands = {k: v for k, v in cands.items() if k in ("ipca_resmom_72h", "ipca_resrev_1h")}
        for nm, (Xf, sign) in cands.items():
            # rank-IC is invariant to per-ts demean, so score vs YR4 directly (already residualised).
            icY = _ic_days(Xf, YR4, MEM, dayidx, all_days, sign)
            pf = [_ic_days(Xf, YR4, MEM, dayidx, fd, sign) for fd in fold_days]
            icraw = _ic_days(Xf, Yraw4_r, MEM, dayidx, all_days, sign)
            null = []
            for _ in range(a.nperm):
                Yp = YR4[rng.permutation(len(YR4))]
                null.append(_ic_days(Xf, Yp, MEM, dayidx, all_days, sign))
            null = np.array([x for x in null if np.isfinite(x)])
            mu, sd = (float(null.mean()), float(null.std())) if len(null) else (np.nan, np.nan)
            zt = (icY - mu) / (sd + 1e-9) if np.isfinite(icY) else np.nan
            signs = set(int(np.sign(x)) for x in pf if np.isfinite(x) and x != 0)
            results.append(dict(K=K, name=nm, sign=sign,
                                ic_YR4=round(icY, 4) if np.isfinite(icY) else None,
                                ic_rawY4=round(icraw, 4) if np.isfinite(icraw) else None,
                                z=round(zt, 2) if np.isfinite(zt) else None,
                                perfold=[round(x, 4) if np.isfinite(x) else None for x in pf],
                                sign_consistent=(len(signs) == 1),
                                pass_gate=bool(np.isfinite(icY) and icY >= 0.002
                                               and np.isfinite(zt) and abs(zt) >= 2.0
                                               and len(signs) == 1)))
    results.sort(key=lambda r: (-(abs(r["z"]) if r["z"] is not None else 0)))
    print(f"\n{'K':>2s} {'candidate':18s} {'sgn':>3s} {'IC_YR4':>8s} {'IC_rawY4':>9s} {'z':>6s}  "
          f"{'perfold':>22s}  gate")
    for r in results:
        pf = "/".join(f"{x:+.3f}" if x is not None else " NA" for x in r["perfold"])
        icY = f"{r['ic_YR4']:+.4f}" if r["ic_YR4"] is not None else "   NaN"
        icr = f"{r['ic_rawY4']:+.4f}" if r["ic_rawY4"] is not None else "   NaN"
        zs = f"{r['z']:+.2f}" if r["z"] is not None else "  NaN"
        print(f"{r['K']:>2d} {r['name']:18s} {r['sign']:>+3d} {icY:>8s} {icr:>9s} {zs:>6s}  "
              f"{pf:>22s}  {'PASS' if r['pass_gate'] else ''}")
    if not a.smoke:
        out = dict(analysis="arm_ipca_residmom", instruments=instr, folds=folds,
                   K_sweep=Ks, table=results)
        op = p.join(E, "eda/arm_ipca.json")
        json.dump(out, open(op, "w"), indent=2)
        print(f"\n-> {op}")


if __name__ == "__main__":
    main()
