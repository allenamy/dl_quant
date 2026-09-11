"""P6 step 5: (a) the FAIL-OPEN mode of the Amihud definition under missing 5m bars, quantified;
(b) the producer-side compute cost of the one extra window statistic."""
import numpy as np, json, time, sys
sys.path.insert(0,"/workspace")
from zload import zload
Z=zload("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz",allow_pickle=True)
CTS=Z["ts"].astype(np.int64); CD=Z["data"]; NW=CD.shape[1]; TT=CD.shape[0]
grid=np.where(CTS%14400==0)[0]; E=grid[(grid>=8640)&(grid+288<=TT)]
qv=np.where(np.isfinite(CD[:,:,3]),CD[:,:,3],np.nan).astype(np.float32)
del CD,Z
V=np.load("/workspace/uplift_2026-09-11/p6/AM_variants.npz",allow_pickle=True)
AM=V["AM_P"]
fin=np.isfinite(qv)
CSf=np.concatenate([np.zeros((1,NW),np.int32),np.cumsum(fin,0,dtype=np.int32)])
cov=(CSf[E]-CSf[E-288])/288.0
OUT={}
ok=np.isfinite(AM)
OUT["coverage_of_finite_amihud_cells"]={
  "n":int(ok.sum()),
  "frac_cov_lt_1.00":float((cov[ok]<1.0).mean()),
  "frac_cov_lt_0.95":float((cov[ok]<0.95).mean()),
  "frac_cov_lt_0.80":float((cov[ok]<0.80).mean()),
  "frac_cov_lt_0.50":float((cov[ok]<0.50).mean()),
  "min_cov":float(cov[ok].min())}
# where do LOW-coverage cells land in the per-anchor Amihud rank? (high rank = illiquid = what the sleeve buys)
from scipy.stats import rankdata
pct_low=[]; pct_full=[]
for i in range(0,AM.shape[0],7):
    v=AM[i]; o=np.isfinite(v); n=o.sum()
    if n<50: continue
    r=rankdata(v[o])/max(n-1,1)-0.5
    c=cov[i][o]
    if (c<0.95).any(): pct_low.append(float(r[c<0.95].mean()))
    pct_full.append(float(r[c>=0.95].mean()))
OUT["mean_amihud_zrank"]={"cells_cov_lt_0.95":float(np.mean(pct_low)),"cells_cov_ge_0.95":float(np.mean(pct_full)),
                          "n_anchors_with_low_cov":int(len(pct_low)),"n_anchors_sampled":int(len(pct_full)),
                          "note":"z-rank in [-0.5,+0.5]; larger = more illiquid = the tail the sleeve goes long of"}
# (b) producer-side compute cost of ONE extra 288-bar window statistic over the live cube shape
cube=np.asarray(qv[-11520:,:400],np.float16)     # CACHE_ROWS=11520 x NTOP-ish live width
ai=cube.shape[0]-1
t=[]
for _ in range(20):
    t0=time.perf_counter()
    CDf=cube.astype(np.float32)
    seg=CDf[ai+1-288:ai+1]
    f=np.isfinite(seg)
    q=np.where(f,np.expm1(np.clip(seg,0,30)),0).astype(np.float32).astype(np.float64).sum(0)
    t.append(time.perf_counter()-t0)
t2=[]
for _ in range(20):
    CDf=cube.astype(np.float32)
    t0=time.perf_counter()
    seg=CDf[ai+1-288:ai+1]
    f=np.isfinite(seg)
    q=np.where(f,np.expm1(np.clip(seg,0,30)),0).astype(np.float32).astype(np.float64).sum(0)
    t2.append(time.perf_counter()-t0)
OUT["producer_compute_ms"]={"incl_cube_f16_to_f32_cast_ms":float(np.median(t)*1e3),
                            "window_stat_only_ms":float(np.median(t2)*1e3),
                            "shape":[11520,400],"note":"CDf cast already happens once per anchor in shadow_loop_v3 L355; only window_stat_only is NEW work"}
json.dump(OUT,open("/workspace/uplift_2026-09-11/p6/P6_OPS.json","w"),indent=1)
print(json.dumps(OUT,indent=1))
