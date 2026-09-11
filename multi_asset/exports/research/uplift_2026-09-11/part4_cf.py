#!/usr/bin/env python3
"""Part 4: recover the PRE-SMOOTHING target series, then price alternative (alpha, band).
Two estimators, both stated:
  E1 'hold'   : banded names get tgt = H      (minimal-motion; biased TOWARD the deployed smoother)
  E2 'interp' : banded names get tgt interpolated between the anchors where that name DID move
                (exact wherever the band did not bind; the band-held gaps are filled from the
                 name's own neighbouring exact targets)
Diagnostic that discriminates them: the true chain L1-normalises, so sum|tgt| == 1.0000 exactly.
"""
import os, json, glob, time
import numpy as np
exec(open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/smooth_latency_core.py").read().split("# ---- 1.")[0])

def build(SM, anchors):
    A = [a for a in anchors if (a - 14400) in SM]
    T = len(A)
    EX = np.full((T, NW), np.nan)     # exactly-known target
    HH = np.zeros((T, NW)); SS = np.zeros((T, NW))
    for i, a in enumerate(A):
        H = SM[a - 14400]; sm = SM[a]
        HH[i] = H; SS[i] = sm
        d = sm - H
        forced = (sm == 0.0) & (np.abs(H) > 1e-12)
        moved = (np.abs(d) > 1e-12) & (~forced)
        EX[i, moved] = H[moved] + d[moved] / ALPHA
        EX[i, forced] = 0.0
    return A, EX, HH, SS

def fill_interp(EX):
    """per name, linearly interpolate the exactly-known targets across banded gaps."""
    T, N = EX.shape
    out = EX.copy()
    idx = np.arange(T)
    for j in range(N):
        col = EX[:, j]
        k = np.isfinite(col)
        if k.sum() == 0:
            out[:, j] = 0.0
        elif k.sum() == 1:
            out[:, j] = col[k][0]
        else:
            out[:, j] = np.interp(idx, idx[k], col[k])
    return out

def renorm(TG, HH):
    """the real chain guarantees sum|tgt|=1 and sum(tgt over sel)=0. Impose both on the estimate."""
    out = TG.copy()
    for i in range(out.shape[0]):
        act = (np.abs(out[i]) > 1e-12) | (np.abs(HH[i]) > 1e-12)
        if act.sum() == 0: continue
        v = out[i].copy()
        v[act] -= v[act].mean()
        g = np.abs(v).sum()
        if g > 1e-12: v /= g
        out[i] = v
    return out

def sim(TG, A, alpha, band, H0, cap_exit=None):
    """re-run the producer's smoother with (alpha, band) on the recovered target series."""
    H = H0.copy(); bps = []; tover = []
    for i, a in enumerate(A):
        tgt = TG[i]
        smv = H + alpha * (tgt - H)
        tr = smv - H
        smv = np.where(np.abs(tr) < band, H, smv)
        if cap_exit is not None:                   # replicate forced exits exactly as observed
            smv = np.where(cap_exit[i], 0.0, smv)
        tr = smv - H
        y = np.nan_to_num(y4_of(a), nan=0.0)
        g = np.abs(smv).sum()
        bps.append(float((smv / g * y).sum() * 1e4) if g > 1e-12 else 0.0)
        tover.append(float(np.abs(tr).sum() / max(g, 1e-12)))
        H = smv
    return np.array(bps), np.array(tover)

for LBL, SM, ANCH in (("KING", SMK, kw), ("COMBO(deployed)", SMC, cw)):
    A, EX, HH, SS = build(SM, ANCH)
    keep = [i for i, a in enumerate(A) if y4_of(a) is not None]
    A = [A[i] for i in keep]; EX = EX[keep]; HH = HH[keep]; SS = SS[keep]
    T1 = np.where(np.isfinite(EX), EX, HH)              # E1 hold
    T2 = fill_interp(EX)                                # E2 interp
    forced = (SS == 0.0) & (np.abs(HH) > 1e-12)
    print(f"\n================ {LBL}  n_anchors={len(A)} =================")
    print(f"  exactly-known tgt cells/anchor: {np.isfinite(EX).sum(1).mean():.1f}   band-held: {(~np.isfinite(EX)).sum(1).mean():.0f} of {NW} cols")
    for nm_, TT in (("E1 hold", T1), ("E2 interp", T2)):
        g = np.abs(TT).sum(1)
        print(f"  [{nm_:9s}] recovered sum|tgt| mean {g.mean():.4f} sd {g.std():.4f}  (TRUTH = 1.0000)  "
              f"median {np.median(g):.4f}")
    T1n = renorm(T1, HH); T2n = renorm(T2, HH)
    for nm_, TT in (("E1n", T1n), ("E2n", T2n)):
        # forward-consistency: does the deployed smoother reproduce the observed book?
        b0, t0 = sim(TT, A, ALPHA, BAND, HH[0], forced)
        y = np.array([float((SS[i]/max(np.abs(SS[i]).sum(),1e-12) * np.nan_to_num(y4_of(a), nan=0.0)).sum()*1e4) for i, a in enumerate(A)])
        print(f"  [{nm_}] replay@deployed(a=.1,band=2.5e-4): mean {b0.mean():+.4f} vs OBSERVED book {y.mean():+.4f}  "
              f"corr {np.corrcoef(b0,y)[0,1]:.4f}  turnover {t0.mean():.4f} vs observed {np.mean([np.abs(SS[i]-HH[i]).sum()/max(np.abs(SS[i]).sum(),1e-12) for i in range(len(A))]):.4f}")
    np.save(f"{OUT}/TGT_{LBL.split('(')[0]}_E2n.npy", T2n)
    np.save(f"{OUT}/TGT_{LBL.split('(')[0]}_E1n.npy", T1n)
    np.save(f"{OUT}/TGT_{LBL.split('(')[0]}_H0.npy", HH[0])
    np.save(f"{OUT}/TGT_{LBL.split('(')[0]}_forced.npy", forced)
    np.save(f"{OUT}/TGT_{LBL.split('(')[0]}_A.npy", np.array(A))
