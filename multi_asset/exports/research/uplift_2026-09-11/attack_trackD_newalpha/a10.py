import numpy as np, calendar, glob, os, json
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C=dict((c,i) for i,c in enumerate(COLS))
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HC="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"; TD="/workspace/uplift_2026-09-11/trackD_v4"
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); R=np.asarray(A[key] if key in A.files else A["rec"],float)
    return np.round(R[:,0]).astype(np.int64),R
FROZ=(T(2025,3,1),T(2026,8,10,20)+1); EXT=(T(2026,8,11),T(2026,8,31,20)+1)
t0,R0=load(HC+"/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec")
f0=t0[(t0>=FROZ[0])&(t0<FROZ[1])]; e0=t0[(t0>=EXT[0])&(t0<EXT[1])]
print("A0 frozen n=%d  ext n=%d  (RESULT doc table states ext n=60)"%(len(f0),len(e0)))
bad=[]
for f in sorted(glob.glob(TD+"/SL_*.npz"))+sorted(glob.glob(TD+"/IB_*.npz")):
    ts,_=load(f); fa=ts[(ts>=FROZ[0])&(ts<FROZ[1])]
    if len(fa)!=len(f0) or not (fa==f0).all(): bad.append((os.path.basename(f),len(fa)))
print("arms with frozen-window anchor set NOT identical to A0:",bad if bad else "NONE (claim holds)")
# but: do the LOB arms have the same FULL-cycle set?
for nm in ["SL_LOBDEPTH__m","SL_LOBIMB1__p"]:
    ts,_=load(TD+"/"+nm+".npz"); print("  %s total anchors %d vs A0 %d"%(nm,len(ts),len(t0)))
