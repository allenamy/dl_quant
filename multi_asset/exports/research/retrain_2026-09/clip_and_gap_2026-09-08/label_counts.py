import numpy as np, calendar, time
TG=np.load("/workspace/dlw/data/dlw_targets.npz",allow_pickle=True) if False else None
import glob
c=glob.glob("/workspace/**/dlw_targets.npz",recursive=True)
print("dlw_targets found:",c[:3])
T=np.load(c[0],allow_pickle=True); ets=T["E_ts"].astype(np.int64); y4s=T["y4s"]
print("y4s shape",y4s.shape,"finite labels %d (%.1f%% of cells)"%(np.isfinite(y4s).sum(),100*np.isfinite(y4s).mean()))
F=np.load("/workspace/review_scratch/clip_flags.npz",allow_pickle=True)
fts=F["E_ts"].astype(np.int64); has=F["has"]
gi={t:i for i,t in enumerate(fts)}
n=0; nf=0
for i,t in enumerate(ets):
    if int(t) not in gi: continue
    h=has[gi[int(t)]]; n+=int(h.sum()); nf+=int((h&np.isfinite(y4s[i])).sum())
print("training-label cells with >=1 clipped bar: %d ; of which finite (actually used): %d"%(n,nf))
print("share of finite labels: %.5f%%"%(100*nf/np.isfinite(y4s).sum()))
CUT=calendar.timegm((2026,8,10,20,0,0)); HOLE=calendar.timegm((2026,8,13,0,5,0))
print("\ncut=%s  hole starts=%s  -> hole entirely AFTER cut: %s"%(time.strftime("%F %H:%MZ",time.gmtime(CUT)),time.strftime("%F %H:%MZ",time.gmtime(HOLE)),HOLE>CUT))
print("training labels at anchors inside the hole window: %d anchors"%int(((ets>=HOLE)&(ets<=calendar.timegm((2026,8,24,4,0,0)))).sum()))
