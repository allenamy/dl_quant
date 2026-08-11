import numpy as np, os, json
from scipy.stats import pearsonr, spearmanr
MONTHS=["2025_08","2025_09","2025_10","2025_11","2025_12","2026_01","2026_02","2026_03","2026_04","2026_05"]
REG={"2025_08":"normal","2025_09":"normal","2025_10":"STRONG","2025_11":"strong","2025_12":"choppy",
     "2026_01":"drift","2026_02":"drift","2026_03":"drift","2026_04":"drift","2026_05":"drift"}
HZ=600*1_000_000; DAY=86400*1_000_000
def clean_idx(ts):
    o=np.argsort(ts);keep=[];last=-1e18
    for i in range(len(o)):
        if ts[o[i]]-last>=HZ: keep.append(o[i]);last=ts[o[i]]
    return np.array(keep,int)
def load(f):
    if not os.path.exists(f): return None
    z=np.load(f,allow_pickle=True);pr=z["predictions"].astype(np.float64)
    q=pr[:,1] if pr.ndim==2 else pr; y=z["targets"].astype(np.float64); ts=z["timestamps"].astype(np.int64)
    if "mask" in z.files: k=z["mask"].astype(bool); q,y,ts=q[k],y[k],ts[k]
    return q,y,ts
def cdclean(q,y,ts):
    dk=ts//DAY; rs=[]
    for d in np.unique(dk):
        m=dk==d; k=clean_idx(ts[m])
        if len(k)>20:
            qk=q[m][k];yk=y[m][k]
            if qk.std()>1e-12:
                r=pearsonr(qk,yk)[0]
                if np.isfinite(r): rs.append(r)
    return np.mean(rs) if rs else np.nan
rows=[]
print(f"{'month':8s} {'reg':7s} | {'be_raw':>6s} {'be_ema':>6s} {'ran':>4s} {'patgap':>6s} {'stop@pat':>8s} | {'valC_ema':>8s} {'vσ_raw':>7s} {'vσ_ema':>7s} | {'tst_BEST':>8s} {'tst_EMA':>8s} {'regret':>7s} | src(best/ema)")
for mk in MONTHS:
    base=f"experiments_local/wfEMA/wf_{mk}/fold_0"
    mp=f"{base}/metrics.json"
    Lb=load(f"{base}/test_preds.npz"); Le=load(f"{base}/ema_test_preds.npz")
    tb=cdclean(*Lb) if Lb else np.nan; te=cdclean(*Le) if Le else np.nan
    regret=(max(tb,te)-te) if (np.isfinite(tb) and np.isfinite(te)) else np.nan
    if os.path.exists(mp):
        mj=json.load(open(mp))
        be=mj.get("best_epoch"); eb=(mj.get("ema") or {}).get("best_epoch")
        ran=len(mj.get("train_loss_hist",[])); pat=(ran-be) if (be is not None and ran) else None
        stop="yes" if (be and ran and be<ran) else "cap?"
        vce=(mj.get("ema") or {}).get("val_composite",np.nan)
        vsr=mj.get("best_ckpt_sigma_ratio",np.nan); vse=mj.get("ema_ckpt_sigma_ratio",np.nan)
        prov=mj.get("ckpt_provenance",{}); src=f"{prov.get('best_source','?')}/{prov.get('ema_source','?')}"
    else:
        be=eb=ran=pat=None; stop="?"; vce=vsr=vse=np.nan; src="NO metrics.json"
    rows.append((mk,be,vce,te,tb,regret,REG[mk]))
    print(f"{mk:8s} {REG[mk]:7s} | {str(be):>6s} {str(eb):>6s} {str(ran):>4s} {str(pat):>6s} {stop:>8s} | {vce:+8.4f} {vsr:7.3f} {vse:7.3f} | {tb:+8.4f} {te:+8.4f} {regret:+7.4f} | {src}")
have=[r for r in rows if np.isfinite(r[2]) and np.isfinite(r[3])]
vce=np.array([r[2] for r in have]); te=np.array([r[3] for r in have])
drift=[r for r in rows if r[6]=="drift" and np.isfinite(r[5])]
y25=[r for r in rows if not r[0].startswith("2026") and np.isfinite(r[5])]
print(f"\nval→test alignment (folds w/ metrics, n={len(have)}): Spearman(valC_ema, test_cdCLEAN_ema)={spearmanr(vce,te).statistic:+.2f} (p={spearmanr(vce,te).pvalue:.3f})")
print(f"regret (best-of-{{BEST,EMA}} − shipped EMA): ALL={np.mean([r[5] for r in rows if np.isfinite(r[5])]):+.4f} | DRIFT={np.mean([r[5] for r in drift]):+.4f} | 2025={np.mean([r[5] for r in y25]):+.4f}")
print(f"drift best_epoch(raw): {[r[1] for r in rows if r[6]=='drift']}  |  2025 best_epoch(raw): {[r[1] for r in rows if not r[0].startswith('2026')]}")
