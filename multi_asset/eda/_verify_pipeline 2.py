"""VERIFY the bar-data pipeline end-to-end (label / windowing / features / model load).
Different label + data => must confirm correctness before trusting any result.
Runs on the EXACT windowed NPZ the DL used. HDF5_USE_FILE_LOCKING=FALSE."""
import numpy as np, os.path as p, sys, glob
sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
from scipy.stats import spearmanr, pearsonr

WIN="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/windowed_npz/bnfbtc"
RUN="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train/btc_dualpath_run1/fold_0"

# ---------- 1. Inspect a windowed test-day NPZ ----------
day="20250301"
z=np.load(p.join(WIN,f"{day}.npz"), allow_pickle=True)
feats=list(z["features"]); X=z["X"]; y=z["y_600"]; ts=z["timestamps"]; m=z["y_mask_600"].astype(bool)
print(f"[1] windowed NPZ {day}: X{X.shape} feats={len(feats)} y_600 n={len(y)} valid={m.sum()}")
print(f"    y_600 stats (bps): mean={np.nanmean(y[m])*1e4:+.3f} std={np.nanstd(y[m])*1e4:.3f} (BTC ~13bps expected)")

# ---------- 2. Label correctness: recompute y_600 from RAW bars at the same pred timestamps ----------
from multi_asset.data.bar_loader import load_day_panel
P=load_day_panel(int(day),["bnfbtc"]); bar_ts=P.ts; mid=P.data["bnfbtc"][:,P.cols.index("mid")].astype(float)
ts_to_i={int(t):i for i,t in enumerate(bar_ts)}
# windowed pred ts -> bar index; manual y = log(mid[i+600]/mid[i])
chk=[]
for k in range(0,len(ts),500):
    t=int(ts[k]);
    if t not in ts_to_i: continue
    i=ts_to_i[t]
    if i+600>=len(mid) or not np.isfinite(mid[i]) or not np.isfinite(mid[i+600]): continue
    manual=np.log(mid[i+600]/mid[i])
    chk.append((y[k], manual))
chk=np.array(chk)
if len(chk):
    diff=np.abs(chk[:,0]-chk[:,1]).max()
    print(f"[2] LABEL CHECK: windowed y_600 vs manual forward-600s mid logret — max|diff|={diff:.2e} over {len(chk)} pts "
          f"=> {'MATCH ✓' if diff<1e-6 else 'MISMATCH ✗✗✗'}")

# ---------- 3. Feature-label sanity: last-token of a known-strong OLD feature vs y_600 ----------
# old features include ret_mid_300s; last timestep of the window
for fname in ["ret_mid_300s","ret_mid_60s","obi_L1","tflow_qty_imb_300s"]:
    if fname in feats:
        fi=feats.index(fname)
        lasttok=X[:,-1,fi]   # value at pred bar (window end)
        good=m & np.isfinite(lasttok) & np.isfinite(y)
        s=spearmanr(lasttok[good],y[good]).correlation
        print(f"[3] feature '{fname}' (last-token) vs y_600: Spearman={s:+.4f} n={good.sum()}")

# ---------- 4. Multi-day feature-label correlation (pooled, clean) to confirm signal magnitude ----------
allf={}; ally=[]
testdays=sorted(int(p.basename(f)[:8]) for f in glob.glob(p.join(WIN,"*.npz")))
testdays=[d for d in testdays if 20250209<=d<=20250509][:30]
Xs,ys=[],[]
for d in testdays:
    zz=np.load(p.join(WIN,f"{d}.npz"),allow_pickle=True)
    Xs.append(zz["X"][:,-1,:]); ys.append(zz["y_600"]*np.where(zz["y_mask_600"].astype(bool),1,np.nan))
Xall=np.concatenate(Xs); yall=np.concatenate(ys)
g=np.isfinite(yall)
print(f"\n[4] POOLED ({len(testdays)} test days, n={g.sum()}): top features by |Spearman| vs y_600")
rows=[]
for i,fn in enumerate(feats):
    col=Xall[:,i]; gg=g&np.isfinite(col)
    if gg.sum()<500: continue
    rows.append((fn,spearmanr(col[gg],yall[gg]).correlation))
for fn,s in sorted(rows,key=lambda r:-abs(r[1]))[:8]:
    print(f"    {fn:22s} {s:+.4f}")

# ---------- 5. Model load: does eval model match trained (param count) ----------
import torch
ck=torch.load(p.join(RUN,"best_model.pt"),map_location="cpu",weights_only=False)
cfg=dict(ck["config"]); cfg["use_film_multistage"]=True
from src.model.dual_path_model_v3 import DualPathLOBModelV3
mdl=DualPathLOBModelV3(**cfg);
try:
    mdl.load_state_dict(ck["state"],strict=True); ok="strict-load OK ✓"
except Exception as e: ok=f"LOAD FAIL: {e}"
npar=sum(p_.numel() for p_ in mdl.parameters())
print(f"\n[5] MODEL LOAD: params={npar} (trained log said 108,286) {ok}")
