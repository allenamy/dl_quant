#!/usr/bin/env python3
"""Part 3 (EXACT, no inversion): the trade-decay profile and the intra-anchor latency profile.
Uses ONLY stored book weights + the producer's own 5m cache. Everything here is bit-consistent
with shadow_loop_v3's own scorer (validated max|diff| 5e-4 bps on 146 anchors)."""
import os, json, glob, time
import numpy as np
exec(open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/smooth_latency_core.py").read().split("# ---- 1.")[0])

def series(SM, anchors, label):
    A = [a for a in anchors if y4_of(a) is not None and (a-14400) in SM]
    return A

# ---------- the two books ----------
KA = [a for a in kw if (a - 14400) in SMK and y4_of(a) is not None]
CA = [a for a in cw if (a - 14400) in SMC and y4_of(a) is not None]
print(f"king anchors scoreable {len(KA)}  combo anchors scoreable {len(CA)}")

def unit(w):
    g = np.abs(w).sum()
    return w / g if g > 1e-12 else w

# ---------- 0. deployed-book paper return, and the king/combo divergence ----------
def paper(SM, A):
    out = []
    for a in A:
        y = np.nan_to_num(y4_of(a), nan=0.0)
        out.append(float((SM[a] * y).sum() * 1e4))
    return np.array(out)

def paper_unit(SM, A):
    out = []
    for a in A:
        y = np.nan_to_num(y4_of(a), nan=0.0)
        out.append(float((unit(SM[a]) * y).sum() * 1e4))
    return np.array(out)

gk = paper(SMK, KA); gc = paper(SMC, CA)
gku = paper_unit(SMK, KA); gcu = paper_unit(SMC, CA)
ov = [a for a in CA if a in set(KA)]
gk_ov = paper(SMK, ov); gc_ov = paper(SMC, ov)
print(f"\n[BOOK GROSS bps/anchor, file caliber (gross as stored)]")
print(f"  king  (shadow_log 'score' book) n={len(KA)} mean {gk.mean():+.4f} sd {gk.std(ddof=1):.3f}")
print(f"  combo (ACTUALLY DEPLOYED)       n={len(CA)} mean {gc.mean():+.4f} sd {gc.std(ddof=1):.3f}")
print(f"  same anchors n={len(ov)}: king {gk_ov.mean():+.4f}  combo {gc_ov.mean():+.4f}  diff {gc_ov.mean()-gk_ov.mean():+.4f}")
print(f"[BOOK GROSS bps/anchor, UNIT-GROSS caliber (what the executor deploys: w/|w|_1)]")
print(f"  king  mean {gku.mean():+.4f}   combo mean {gcu.mean():+.4f} sd {gcu.std(ddof=1):.3f}")
print(f"  mean stored gross: king {np.mean([np.abs(SMK[a]).sum() for a in KA]):.4f} combo {np.mean([np.abs(SMC[a]).sum() for a in CA]):.4f}")

# ---------- 1. structural: how deep is the deadband, in units of a mean position ----------
rows=[]
for a in KA:
    w = SMK[a]; nz = np.abs(w) > 1e-12
    rows.append((int(nz.sum()), float(np.abs(w[nz]).mean()) if nz.any() else np.nan,
                 float(np.abs(w[nz]).max()) if nz.any() else np.nan))
n_held = np.array([r[0] for r in rows]); mw = np.array([r[1] for r in rows])
print(f"\n[DEADBAND GEOMETRY] held names/anchor {n_held.mean():.0f}; mean |w| per held name {mw.mean():.6f}")
print(f"  EMA step for a name whose target is X away from book = alpha*X = 0.1*X")
print(f"  band {BAND} on the STEP  =>  a name trades only if |tgt-H| > band/alpha = {BAND/ALPHA:.5f}")
print(f"  that threshold = {BAND/ALPHA/mw.mean():.2f} x the mean held |w|  (i.e. ~one whole average position)")

# ---------- 2. EXACT trade-decay profile: dw_t . y4_{t+k} ----------
def decay(SM, A, K=13):
    tab = np.full((len(A), K), np.nan)
    for i, a in enumerate(A):
        dw = SM[a] - SM[a - 14400]
        for k in range(K):
            b = a + 14400 * k
            y = y4_of(b)
            if y is None: continue
            tab[i, k] = float((dw * np.nan_to_num(y, nan=0.0)).sum() * 1e4)
    return tab

TK = decay(SMK, KA); TC = decay(SMC, CA)
print(f"\n[EXACT TRADE-DECAY]  dw_t . y4_{{t+k}} in bps of unit gross, mean over anchors")
print(f"  k(anchors)  hours   king mean    (t)      combo mean    (t)      n")
cumk = 0.0; cumc = 0.0
for k in range(13):
    ck = TK[:, k]; ck = ck[np.isfinite(ck)]
    cc = TC[:, k]; cc = cc[np.isfinite(cc)]
    tk = ck.mean()/(ck.std(ddof=1)/np.sqrt(len(ck))) if len(ck)>2 else np.nan
    tc = cc.mean()/(cc.std(ddof=1)/np.sqrt(len(cc))) if len(cc)>2 else np.nan
    cumk += ck.mean(); cumc += cc.mean()
    print(f"   k={k:<2d}  {k*4:>3d}h   {ck.mean():+8.4f} ({tk:+5.2f})   {cc.mean():+8.4f} ({tc:+5.2f})   {len(ck):3d}/{len(cc):3d}   cum {cumk:+7.3f}/{cumc:+7.3f}")
np.save(f"{OUT}/trade_decay_king.npy", TK); np.save(f"{OUT}/trade_decay_combo.npy", TC)
np.save(f"{OUT}/anchors_king.npy", np.array(KA)); np.save(f"{OUT}/anchors_combo.npy", np.array(CA))

# ---------- 3. EXACT intra-anchor latency profile ----------
# The executor reads target_live at N+24min and quotes for k_seconds=900 (config/book.json:43).
# So the trade dw_t is in the book only from roughly N+25..N+40. Everything the trade earns
# before that is NOT captured by the live book (it was still holding sm_{t-1}).
def intra(SM, A):
    acc = np.full((len(A), 48), np.nan); accb = np.full((len(A), 48), np.nan)
    for i, a in enumerate(A):
        s = seg_of(a)
        if s is None: continue
        dw = SM[a] - SM[a - 14400]
        hold = SM[a - 14400]
        r = np.nan_to_num(s, nan=0.0)
        acc[i] = (r * dw[None, :]).sum(1) * 1e4        # incremental-trade pnl per 5m bar
        accb[i] = (r * hold[None, :]).sum(1) * 1e4     # previously-held book pnl per 5m bar
    return acc, accb

IK, IKB = intra(SMK, KA); IC, ICB = intra(SMC, CA)
print(f"\n[EXACT INTRA-ANCHOR]  bps per 5m bar, mean over anchors; bar m covers [N+5m, N+5(m+1)m)")
def blk(M, lo, hi):
    v = np.nansum(M[:, lo:hi], 1)
    v = v[np.isfinite(v)]
    return v.mean(), v.std(ddof=1)/np.sqrt(len(v)), len(v)
for nm_, M in (("king dw", IK), ("combo dw", IC)):
    tot = blk(M, 0, 48)
    print(f"  {nm_}: whole 4h {tot[0]:+.4f}+-{tot[1]:.4f}")
    for lo, hi, lab in ((0,5,"N+0..25m  (BEFORE the book is built)"), (5,8,"N+25..40m (the quote window)"),
                        (8,12,"N+40..60m"), (12,24,"N+1..2h"), (24,48,"N+2..4h")):
        m_, se, n_ = blk(M, lo, hi)
        print(f"      {lab:<38s} {m_:+8.4f} +- {se:.4f}   ({100*m_/tot[0] if tot[0]!=0 else np.nan:6.1f}% of the 4h total)")
np.save(f"{OUT}/intra_king_dw.npy", IK); np.save(f"{OUT}/intra_combo_dw.npy", IC)
np.save(f"{OUT}/intra_king_hold.npy", IKB); np.save(f"{OUT}/intra_combo_hold.npy", ICB)
