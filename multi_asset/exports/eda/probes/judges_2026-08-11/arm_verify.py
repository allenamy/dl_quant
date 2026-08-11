import os, glob, json, numpy as np
from multi_asset.train.train_dual_lob import _build_folds
from multi_asset.train.arm_utils import choppy_filter_days, tail_sample_weights
npz="data/npz_v2arch"
days=sorted(p[:-4].split("/")[-1] for p in glob.glob(f"{npz}/*.npz") if p.split("/")[-1][0].isdigit())
tcfg=json.load(open("configs/arms/spec_2026_01.json"))["training"]
fold=_build_folds(days, tcfg, int(tcfg.get("embargo_days",0)))[0]
print("fold train days:", len(fold["train"]), fold["train"][0], "..", fold["train"][-1])
# ARM A
kept, st = choppy_filter_days(npz, fold["train"], quantile=0.34)
print(f"[ARM A] day_filter kept {st['n_kept']}/{st['n_in']} (ER<={st['threshold']:.3f}) er[min/med/max]={st['er_min']:.3f}/{st['er_median']:.3f}/{st['er_max']:.3f}")
# ARM B (data-only: use raw y_600 across train days as y_norm proxy)
ys=[]; ms=[]
for d in fold["train"]:
    z=np.load(f"{npz}/{d}.npz"); ys.append(z["y_600"]); ms.append(z["y_mask_600"])
y=np.concatenate(ys); m=np.concatenate(ms)
w, thr=tail_sample_weights(y, m, k=2.0, quantile=0.8)
print(f"[ARM B] tail_weight thr={thr:.5f} tailfrac(w>1)={ (w>1).mean():.3f} zerofrac(w==0)={ (w==0).mean():.3f} n_drawable={int((w>0).sum())}")
