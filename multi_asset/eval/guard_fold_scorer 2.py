"""GUARD-FOLD SCORER — judge a new arch/loss ARM fold vs FROZEN Run1 on the canonical raw-y caliber.

Discipline (locked with the lead 2026-07-07):
- Caliber = the 0B-verified raw-y one: denorm q50->bps = (pred[:,1]*y_sigma+y_median)*1e4; realized =
  production CSV RAW y_true_ret_bps (NOT the ±5σ-clipped npz targets — those corr only ~0.88 to raw).
- Arm and Run1 are scored on the SAME nodes (intersection of timestamps, both mask-valid & raw-y) so
  the Δ is apples-to-apples. Node-identity is reported.
- JUDGE ON IC (Pearson + Spearman) ONLY. β / σŷ/σy are DIAGNOSTIC, not gates (IC/β rule). But σŷ/σy<0.02
  is flagged as a variance-COLLAPSE (abort-at-ep5 signal), and P/S DIVERGENCE is flagged (anti-pattern #12).

PRE-REGISTERED GATES (locked — do not tune):
  2025_10  role=PROTECT (crown jewel, Run1 raw-y cd≈0.1003): KILL if Δcd < −0.005 OR ΔS_cd < −0.005.
  2026_01  role=LIFT    (drift, Run1 raw-y cd≈0.0253):       ADVANCE only if Δcd ≥ +0.005 AND ΔS_cd ≥ 0
                                                             (holds/improves) AND no P/S divergence.
                                                             within-noise or divergent => LINE CLOSED.

Run:  python multi_asset/eval/guard_fold_scorer.py --arm <arm.npz> --month 2025_10 [--run1 <npz>] [--label NAME]
"""
from __future__ import annotations
import numpy as np, pandas as pd, argparse, os
from scipy.stats import pearsonr, spearmanr

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
PROD_CSV = MA + "/exports/final_l01/y600_backtest_dataset.csv"
RUN1_NPZ = MA + "/experiments/d1gate/d1_%s_run1/fold_0/ema_test_preds.npz"
HZ = 600*1000; DAY = 86400*1000                         # timestamp_ms (MILLISECONDS)
SIG_MIN = 0.02

GATES = {
    "2025_10": dict(role="PROTECT", run1_cd=0.1003, kill_dcd=-0.005, kill_ds=-0.005),
    "2026_01": dict(role="LIFT",    run1_cd=0.0253, adv_dcd=+0.005),
}

# ---------------- verified metric fns (identical to run1_production_report.py) ----------------
def _P(q,y):  return float(pearsonr(q,y)[0])  if len(q)>10 and q.std()>1e-12 and y.std()>1e-12 else np.nan
def _S(q,y):  return float(spearmanr(q,y)[0]) if len(q)>10 and q.std()>1e-12 and y.std()>1e-12 else np.nan
def _beta(q,y): return float(np.cov(y,q)[0,1]/q.var()) if q.var()>1e-18 else np.nan
def _sigr(q,y): return float(q.std()/y.std()) if y.std()>1e-12 else np.nan

def clean_pool(t):
    o=np.argsort(t); keep=[]; dk=t[o]//DAY
    for d in np.unique(dk):
        di=o[dk==d]; last=-1<<62
        for i in di:
            if t[i]-last>=HZ: keep.append(i); last=t[i]
    return np.array(sorted(keep),int)

def cd_perday(q,y,t,fn=_P):
    dk=t//DAY; rs=[]
    for d in np.unique(dk):
        idx=np.where(dk==d)[0]; ti=t[idx]; o=np.argsort(ti); last=-1<<62; sel=[]
        for j in o:
            if ti[j]-last>=HZ: sel.append(j); last=ti[j]
        if len(sel)>20:
            r=fn(q[idx][sel],y[idx][sel])
            if np.isfinite(r): rs.append(r)
    return float(np.mean(rs)) if rs else np.nan

def diracc(q,y):
    m=y!=0; return float(np.mean(np.sign(q[m])==np.sign(y[m]))) if m.sum()>0 else np.nan
def diracc_big(q,y):
    s=y.std(); m=(np.abs(y)>s)&(y!=0); return float(np.mean(np.sign(q[m])==np.sign(y[m]))) if m.sum()>10 else np.nan
def diracc_tail(q,y,frac=0.2):
    qd=q-q.mean(); thr=np.quantile(np.abs(qd),1-frac); m=(np.abs(qd)>=thr)&(y!=0)
    return float(np.mean(np.sign(q[m])==np.sign(y[m]))) if m.sum()>10 else np.nan

def bin_mono(q,y,nb=10):
    if len(q)<nb*5: return np.nan,0,0
    edges=np.quantile(q,np.linspace(0,1,nb+1)); edges[-1]+=1e-9
    idx=np.clip(np.digitize(q,edges)-1,0,nb-1)
    means=np.array([y[idx==b].mean() if (idx==b).sum()>0 else np.nan for b in range(nb)])
    v=np.isfinite(means)
    sp=float(spearmanr(np.arange(nb)[v],means[v])[0]) if v.sum()>2 else np.nan
    return sp, int(np.sum(np.diff(means[v])>0)), int(v.sum()-1)

# ---------------- load raw-y aligned preds ----------------
def load_rawy(npz, cy):
    z=np.load(npz,allow_pickle=True); pr=z["predictions"]
    q=(pr[:,1] if pr.ndim==2 else pr).astype(float)
    ts=z["timestamps"].astype(np.int64)
    ysig=float(z["y_sigma"]) if "y_sigma" in z.files else 1.0
    ymed=float(z["y_median"]) if "y_median" in z.files else 0.0
    pb=(q*ysig+ymed)*1e4
    m=z["mask"].astype(bool) if "mask" in z.files else np.ones(len(q),bool)
    ts_ms=ts//1000 if ts[0]>3e12 else ts
    yt=np.array([cy.get(int(t),np.nan) for t in ts_ms])
    keep=m & np.isfinite(yt)
    return dict(ts=ts_ms[keep].astype(np.int64), p=pb[keep], y=yt[keep], n_valid=int(m.sum()), n_raw=int(keep.sum()))

def battery(p,y,t):
    ci=clean_pool(t); pc,yc,tc=p[ci],y[ci],t[ci]
    spm,up,steps=bin_mono(pc,yc)
    return dict(P_cd=cd_perday(p,y,t,_P), S_cd=cd_perday(p,y,t,_S), P_den=_P(p,y), S_den=_S(p,y),
                DA=diracc(pc,yc), DAbig=diracc_big(pc,yc), DAtail=diracc_tail(pc,yc),
                mono=spm, up=up, steps=steps, beta=_beta(pc,yc),
                sigr=_sigr(pc,yc), sigr_den=_sigr(p,y), n_cl=len(ci))

def score(arm_npz, run1_npz, month, label):
    prod=pd.read_csv(PROD_CSV); cy=dict(zip(prod.timestamp_ms.values.astype(np.int64), prod.y_true_ret_bps.values.astype(float)))
    A=load_rawy(arm_npz,cy); Rn=load_rawy(run1_npz,cy)
    # align on common timestamps (fair Δ)
    common=np.intersect1d(A["ts"], Rn["ts"])
    ai={int(t):i for i,t in enumerate(A["ts"])}; ri={int(t):i for i,t in enumerate(Rn["ts"])}
    idxa=np.array([ai[int(t)] for t in common]); idxr=np.array([ri[int(t)] for t in common])
    pa,ya,ta=A["p"][idxa], A["y"][idxa], A["ts"][idxa]
    pr_,yr_,tr=Rn["p"][idxr], Rn["y"][idxr], Rn["ts"][idxr]
    assert np.array_equal(ta,tr) and np.allclose(ya,yr_), "node/y misalignment"
    ma=battery(pa,ya,ta); mr=battery(pr_,yr_,tr)

    print(f"\n================ GUARD-FOLD SCORE  [{label}]  month={month} ================")
    g=GATES.get(month,{})
    print(f"role={g.get('role','?')}  |  nodes: arm valid={A['n_valid']} raw-y={A['n_raw']} | run1 raw-y={Rn['n_raw']} | COMMON scored={len(common)} (clean n={ma['n_cl']})")
    print(f"{'metric':>10s} {'ARM':>9s} {'RUN1':>9s} {'Δ':>9s}")
    for k,nm in [("P_cd","Pearson_cd"),("S_cd","Spearman_cd"),("P_den","Pearson_dense"),("S_den","Spearman_dense"),
                 ("DA","DirAcc"),("DAbig","DA|y|>σ"),("DAtail","DA_tail20"),("mono","bin_mono")]:
        print(f"{nm:>10s} {ma[k]:+9.4f} {mr[k]:+9.4f} {ma[k]-mr[k]:+9.4f}")
    print(f"{'β·σŷ/σy':>10s}  arm β{ma['beta']:+.2f} σr(clean){ma['sigr']:.3f} σr(dense){ma['sigr_den']:.3f}"
          f"   run1 β{mr['beta']:+.2f} σr(dense){mr['sigr_den']:.3f}   (DIAGNOSTIC, not a gate)")
    dcd=ma["P_cd"]-mr["P_cd"]; ds=ma["S_cd"]-mr["S_cd"]

    # variance-COLLAPSE flag — RELATIVE to the healthy frozen Run1 (Run1's own drift-month clean σŷ/σy
    # is legitimately ~0.014–0.018, below the trainer's 0.02 val floor; so an absolute clean-0.02 gate
    # would false-flag the crown jewel). Flag only a genuine collapse: dense σŷ/σy below a hard
    # degeneracy floor (0.010) OR less than half the frozen Run1's dense σŷ/σy on this same month.
    collapse = (ma["sigr_den"] < 0.010) or (ma["sigr_den"] < 0.5*mr["sigr_den"])
    if collapse:
        print(f"⚠ VARIANCE-COLLAPSE: arm σŷ/σy(dense)={ma['sigr_den']:.4f} vs run1 {mr['sigr_den']:.4f} "
              f"(floor 0.010 / half-of-run1 {0.5*mr['sigr_den']:.4f}) — abort-at-ep5 signal (degenerate preds).")

    # gate verdict
    print("\n--- PRE-REGISTERED GATE ---")
    if g.get("role")=="PROTECT":
        kill = (dcd < g["kill_dcd"]) or (ds < g["kill_ds"])
        v = "KILL — regressed the crown jewel" if kill else "SURVIVES protect (no material regression)"
        print(f"PROTECT 2025_10: Δcd={dcd:+.4f} (kill<{g['kill_dcd']}) | ΔS_cd={ds:+.4f} (kill<{g['kill_ds']})  => {v}")
    elif g.get("role")=="LIFT":
        divergence = (dcd>=g["adv_dcd"]) and (ds < 0)
        advance = (dcd >= g["adv_dcd"]) and (ds >= 0) and not divergence
        if advance: v="ADVANCE — clean lift (P AND S)"
        elif divergence: v="CLOSE — P/S DIVERGENCE (anti-pattern #12)"
        else: v=f"CLOSE — within noise (Δcd={dcd:+.4f} < +{g['adv_dcd']} or ΔS<0)"
        print(f"LIFT 2026_01: Δcd={dcd:+.4f} (advance≥+{g['adv_dcd']}) | ΔS_cd={ds:+.4f} (need≥0)  => {v}")
    else:
        print(f"(no locked gate for month {month}) Δcd={dcd:+.4f} ΔS_cd={ds:+.4f}")
    print(f"P/S consistency: sign(Δcd)={np.sign(dcd):+.0f} sign(ΔS)={np.sign(ds):+.0f}"
          f"  {'AGREE' if np.sign(dcd)==np.sign(ds) else 'DIVERGE ⚠'}")
    print("DONE_GUARD_SCORE")
    return dict(dcd=dcd, ds=ds, collapse=collapse)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--arm", required=True); ap.add_argument("--month", required=True)
    ap.add_argument("--run1", default=None); ap.add_argument("--label", default="arm")
    a=ap.parse_args()
    run1=a.run1 or (RUN1_NPZ % a.month)
    score(a.arm, run1, a.month, a.label)

if __name__=="__main__":
    main()
