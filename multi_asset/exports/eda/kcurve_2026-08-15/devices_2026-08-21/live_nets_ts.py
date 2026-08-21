import sys, numpy as np, datetime
PD="/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0,PD)
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0,MA); sys.path.insert(0,MA+"/engine/live"); sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
import engine.replay_fullhist as RF
src=RF.get_src(None,f"{PD}/king_pred_newgen.npz",f"{PD}/s2_pred_newgen.npz")
a,yr=RF._all_anchors(src)
ts=None
for c in [x for x in dir(src) if 'ts' in x.lower() or 'time' in x.lower()]:
    try:
        arr=np.asarray(getattr(src,c))
        if arr.ndim==1 and len(arr)>len(a) and arr.dtype.kind in 'if': ts=arr; break
    except Exception: pass
tss=ts//1000 if ts[1]-ts[0]>=3600*1000 else ts
ats=np.array([tss[int(t)] for t in a],dtype='int64')
for nm in ("net_S0","net_S1"):
    n=np.load(f"{PD}/{nm}.npy"); assert len(n)==len(ats)
    np.save(f"{PD}/{nm}_ts.npy", np.stack([ats.astype(float), n],1))
print("ok", len(ats), datetime.datetime.utcfromtimestamp(int(ats[0])).date(), datetime.datetime.utcfromtimestamp(int(ats[-1])).date())
