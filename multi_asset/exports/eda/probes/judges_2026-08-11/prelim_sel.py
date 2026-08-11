import json, os, numpy as np
from scipy.stats import pearsonr, spearmanr
HZ=600*1_000_000; DAY=86400*1_000_000
def clean_idx(ts):
    o=np.argsort(ts);k=[];last=-1e18
    for i in range(len(o)):
        if ts[o[i]]-last>=HZ:k.append(o[i]);last=ts[o[i]]
    return np.array(k,int)
def cdclean(f):
    if not os.path.exists(f): return np.nan
    z=np.load(f,allow_pickle=True);pr=z["predictions"].astype(np.float64);q=pr[:,1] if pr.ndim==2 else pr
    y=z["targets"].astype(np.float64);ts=z["timestamps"].astype(np.int64)
    if "mask" in z.files: m=z["mask"].astype(bool);q,y,ts=q[m],y[m],ts[m]
    dk=ts//DAY;rs=[]
    for d in np.unique(dk):
        mm=dk==d;k=clean_idx(ts[mm])
        if len(k)>20 and q[mm][k].std()>1e-12:
            r=pearsonr(q[mm][k],y[mm][k])[0]
            if np.isfinite(r):rs.append(r)
    return float(np.mean(rs)) if rs else np.nan
MENUS=[("d1_2026_01_run1","experiments/d1gate"),("d1_2026_01_run2","experiments/d1gate"),
 ("spec_2026_01","experiments/arms"),("spec_2026_04","experiments/arms"),("spec_2025_12","experiments/arms"),
 ("tail_2026_01","experiments/arms"),("tail_2026_04","experiments/arms")]
WARM=5
print(f"{'menu':16s} {'shipEP':>6s} {'S2pick':>10s} {'S4pick':>10s} {'S4<ship':>7s} {'shipCD':>7s}")
for mk,base in MENUS:
    fd=f"{base}/{mk}/fold_0"; mp=f"{fd}/metrics.json"
    if not os.path.exists(mp): print(f"{mk:16s} no metrics"); continue
    m=json.load(open(mp)); vh=m.get("val_hist") or []
    ship=(m.get("selection") or {}).get("ema_best_epoch") or m.get("best_epoch")
    # candidates: raw epochs + ema epochs (post-warmup)
    cand=[]
    for e in vh:
        ep=e["epoch"]; r=e.get("raw"); em=e.get("ema")
        if r: cand.append(("raw",ep,r["composite"],r["beta"],r["sigma_ratio"]))
        if em and ep>=WARM: cand.append(("ema",ep,em["composite"],em["beta"],em["sigma_ratio"]))
    # S2 health-gated: eligible beta in[.5,1.8] & sig in[.02,.12], max composite; else nearest band
    elig=[c for c in cand if .5<=c[3]<=1.8 and .02<=c[4]<=.12]
    S2=(max(elig,key=lambda c:c[2]) if elig else max(cand,key=lambda c:c[2]))
    # S4 proxy: earliest (by epoch) within 1SE of max composite over cand; SE=std(composite trajectory)/sqrt(n)
    comps=np.array([c[2] for c in cand]); se=comps.std()/max(np.sqrt(len(comps)),1); thr=comps.max()-se
    S4=min([c for c in cand if c[2]>=thr], key=lambda c:c[1])
    shipcd=cdclean(f"{fd}/ema_test_preds.npz")
    print(f"{mk:16s} {str(ship):>6s} {S2[0]+str(S2[1]):>10s} {S4[0]+str(S4[1]):>10s} "
          f"{'YES' if S4[1]<(ship or 99) else 'no':>7s} {shipcd:+7.4f}")
