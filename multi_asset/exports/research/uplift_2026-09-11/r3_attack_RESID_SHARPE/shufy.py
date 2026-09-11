"""Evaluate the shuffle-future (SHUFY) RESID_SHARPE runs through the unmodified device."""
import numpy as np, os, sys, time
sys.path.insert(0,"/workspace/uplift_2026-09-11/r3_attack_b9646")
from null import run, sym, pts, OFF, W, R2
jobs=[]
for s in (42,2027):
    p=R2+"/preds/RESID_SHARPE_SHUFY_s%d.npy"%s
    if not os.path.exists(p): print("missing",p); continue
    P=np.load(p)[OFF:OFF+len(pts)]
    f=W+"/sig/SHUFY_s%d.npz"%s; np.savez(f,symbols=sym,ts=pts,mat=np.asarray(P,np.float32))
    jobs.append(("NULL_SHUFY_s%d"%s,f))
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=2) as ex:
    for r in ex.map(lambda a: run(*a), jobs): print(r,flush=True)
print("SHUFY_EVAL_DONE")
