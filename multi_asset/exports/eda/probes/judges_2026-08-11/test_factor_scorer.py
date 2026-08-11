"""Validate factor_scorer vs backtest_longshort (same rank-IC operator) + invariants."""
import sys, json, numpy as np
sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.eval.factor_scorer import (load_panel, _perts_ic, ic_summary, incremental_ic,
                                            factor_corr, ic_decay, shuffle_null, score_factor)
EXPORT="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
import glob, os.path as op
# pick a tag that has fold preds
tags=[op.basename(op.dirname(f)) for f in glob.glob(EXPORT+"/*/panel_ref.npz")
      if glob.glob(op.join(op.dirname(f),"fold_*_preds.npz"))]
tag=sorted(tags)[0]; print("using tag:", tag)
P=load_panel(tag,EXPORT); pred,Y,CL=P["pred"],P["Y"],P["CL"]
cov=np.isfinite(pred).any(1).sum(); print(f"panel T={Y.shape[0]} S={Y.shape[1]} pred-cov-ts={cov}")

# 1) my gate_a mean_ic vs backtest_longshort's inline mean_rank_ic (must match to rounding)
ics,brd=_perts_ic(pred,Y,CL); ga=ic_summary(ics,brd,"pred")
print("gate_a:", ga)
# reproduce backtest_longshort's exact IC loop
from scipy.stats import spearmanr
MIN=5; ref_ics=[]
for t in range(Y.shape[0]):
    v=CL[t]&np.isfinite(pred[t])&np.isfinite(Y[t])
    if v.sum()<MIN: continue
    ic=spearmanr(pred[t,v],Y[t,v]).correlation
    if np.isfinite(ic): ref_ics.append(ic)
print(f"CROSS-CHECK mean_rank_ic: scorer={ga['mean_ic']:.4f}  backtest_operator={np.mean(ref_ics):.4f}  "
      f"MATCH={abs(ga['mean_ic']-np.mean(ref_ics))<1e-9}")

# 2) invariants
inc,_=incremental_ic(pred,pred,Y,CL); print(f"INVARIANT incremental_ic(pred vs base=pred) mean={np.mean(inc):+.4f} (expect ~0, factor adds nothing beyond itself)")
print(f"INVARIANT factor_corr(pred,pred)={factor_corr(pred,pred,CL)} (expect 1.0)")

# 3) shuffle null + decay
print("shuffle_null:", shuffle_null(pred,Y,CL,n=15))
print("ic_decay(entry-delay):", ic_decay(pred,Y,CL))
print("DONE_TEST")
