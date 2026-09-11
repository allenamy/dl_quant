"""LIVE producer combo book: gross, per-name step distribution, band-freeze fraction.
Compare with the replay BASE which the arms were measured on."""
import numpy as np, glob, os
fs=sorted(glob.glob('/Users/haosiyu/wide_shadow/state/weights_combo/*.npz'))
prev=None; rows=[]
for f in fs:
    a=np.load(f); idx=a['idx']; val=a['val'].astype(np.float64)
    d={int(i):float(v) for i,v in zip(idx,val)}
    if prev is not None:
        keys=set(d)|set(prev)
        cur=np.array([d.get(k,0.0) for k in keys]); pr=np.array([prev.get(k,0.0) for k in keys])
        step=np.abs(cur-pr); g=np.abs(cur).sum()
        held=np.abs(pr)>1e-12
        frozen=held&(step<1e-12)
        rows.append(dict(g=g,n=len(d),
            frozen_frac_gross=float(np.abs(cur[frozen]).sum()/g),
            frozen_frac_names=float(frozen.sum()/max(held.sum(),1)),
            med_step=float(np.median(step[step>1e-12])) if (step>1e-12).any() else np.nan,
            mean_absw=float(np.abs(cur[np.abs(cur)>1e-12]).mean()),
            tov=float(step.sum())))
    prev=d
import statistics as S
def q(k): 
    v=[r[k] for r in rows]; return np.percentile(v,[10,50,90])
print("LIVE combo producer, %d anchor-pairs (2026-08-26 -> 09-11)"%len(rows))
for k in ("g","n","frozen_frac_gross","frozen_frac_names","med_step","mean_absw","tov"):
    v=np.array([r[k] for r in rows],float)
    print(f"  {k:20s} p10 {np.percentile(v,10):10.5f}  median {np.median(v):10.5f}  p90 {np.percentile(v,90):10.5f}")
print("  turnover/gross median %.5f"%np.median([r["tov"]/r["g"] for r in rows]))
print("\nREPLAY BASE (frozen window, from the arm npz): gross mean 0.6343, turnover/gross 0.0551, nsel 328.8")
print("BAND at 2.5e-4 vs live median per-name step above => band/step ratio LIVE = %.2f"%(2.5e-4/np.median([r["med_step"] for r in rows])))
