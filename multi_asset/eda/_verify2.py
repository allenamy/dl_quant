"""Focused verify: pooled feature->y correlation (server-local NPZ only, NO share read) + model load."""
import numpy as np, glob, os.path as p, sys
sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
from scipy.stats import spearmanr, pearsonr
WIN="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/windowed_npz/bnfbtc"
RUN="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train/btc_dualpath_run1/fold_0"
days=sorted(int(p.basename(f)[:8]) for f in glob.glob(p.join(WIN,"*.npz")))
test=[d for d in days if 20250209<=d<=20250509]
Xs,ys=[],[]; feats=None
for d in test:
    z=np.load(p.join(WIN,f"{d}.npz"),allow_pickle=True)
    if feats is None: feats=list(z["features"])
    Xs.append(z["X"][:,-1,:]); ys.append(z["y_600"]*np.where(z["y_mask_600"].astype(bool),1.0,np.nan))
X=np.concatenate(Xs); y=np.concatenate(ys); g=np.isfinite(y)
# clean stride: every 4th window (~720s non-overlap)
gi=np.where(g)[0][::4]
print(f"pooled test n={g.sum()} clean(every4)={len(gi)}")
rows=[]
for i,fn in enumerate(feats):
    c=X[:,i]; ok=np.isfinite(c[gi])
    rows.append((fn, spearmanr(c[gi][ok],y[gi][ok]).correlation, pearsonr(c[gi][ok],y[gi][ok])[0]))
print("\nTop features by |Spearman| (CLEAN pooled test 2025-02..05):")
for fn,s,pe in sorted(rows,key=lambda r:-abs(r[1]))[:10]:
    print(f"  {fn:24s} S={s:+.4f} P={pe:+.4f}")
best_s=max(abs(r[1]) for r in rows)
print(f"\nBEST single feature |Spearman| = {best_s:.4f}  vs  DL got S=0.039")
print("=> if best single feat >> DL, the MODEL is underperforming the signal (not data/features).")
# model load
import torch
ck=torch.load(p.join(RUN,"best_model.pt"),map_location="cpu",weights_only=False)
cfg=dict(ck["config"]); cfg["use_film_multistage"]=True
from src.model.dual_path_model_v3 import DualPathLOBModelV3
mdl=DualPathLOBModelV3(**cfg)
try: mdl.load_state_dict(ck["state"],strict=True); ok="strict-load OK"
except Exception as e: ok=f"FAIL {e}"
print(f"\nMODEL: params={sum(x.numel() for x in mdl.parameters())} (trained=108286) {ok}")
print(f"config use_film_multistage in ckpt: {ck['config'].get('use_film_multistage','ABSENT')} | n_levels={ck['config'].get('n_levels')} | n_features={ck['config'].get('n_features','auto')}")
