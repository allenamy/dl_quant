"""Convert the prior-gate row-layout predictions into (nA x 829) score matrices saved as preds/."""
import numpy as np
R2="/workspace/uplift_2026-09-11/r2_learned"
TG=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True)
nA,NW=TG["y4s"].shape
FE=np.load("/workspace/dlw_v4raw/data/dlw_fea82.npz",allow_pickle=True)
pa=FE["pair_a"].astype(np.int64); ps=FE["pair_s"].astype(np.int64)
PG=np.load(R2+"/prior_gate_preds.npz")
for k in PG.files:
    M=np.full((nA,NW),np.nan,np.float32)
    v=PG[k]; ok=np.isfinite(v)
    M[pa[ok],ps[ok]]=v[ok]
    np.save(R2+"/preds/PG_%s.npy"%k,M)
    print("PG_%s"%k, int(np.isfinite(M).any(1).sum()),"finite anchors")
