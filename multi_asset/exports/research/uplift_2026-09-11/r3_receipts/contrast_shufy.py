"""THE ADVERSARIAL CONTRAST THE OBJECT HAS NEVER FACED:
the arm minus its own shuffled-label twin, on the SAME anchors, with the SAME device and seed.
SHUFY destroys the anchor<->target pairing at training time and changes nothing else, so whatever
survives it is the label-free floor of this architecture+objective+book machine. The right
statistic for "is there alpha in the labels" is arm - SHUFY, not arm - 0."""
import numpy as np, json, hashlib
R3="/workspace/uplift_2026-09-11/r3_resid"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires",
      "leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; APY=2190
import calendar
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
WINS={"full":(T(2022,1,1),T(2026,8,10,20)+1),"frozen":(T(2025,3,1),T(2026,8,10,20)+1),
      "f23":(T(2023,1,1),T(2026,8,10,20)+1)}
def load(p):
    A=np.load(p,allow_pickle=True); R=A["rec"] if "rec" in A.files else A["d30_n2_c42_rec"]
    ts=np.round(np.asarray(R[:,0],float)).astype(np.int64)
    return ts,R[:,C["net_ex"]]/R[:,C["gross_total"]],R
A0=np.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz",allow_pickle=True)
warm=set(np.round(A0["d30_n2_c42_rec"][:,0]).astype(np.int64)[np.abs(A0["d30_n2_c42_rec"][:,15])>1e-9].tolist())
def key(n): return int(hashlib.sha1(n.encode()).hexdigest()[:6],16)
def boot(v,days,name,n=2000):
    rng=np.random.default_rng([20260905,key(name)])
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(n,nd)); return S[idx].sum(1)/N[idx].sum(1)
def bootSR(a,b,days,name,n=2000):
    rng=np.random.default_rng([20260905,key(name)+1])
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    grp=[np.nonzero(inv==z)[0] for z in range(nd)]
    ib=rng.integers(0,nd,size=(n,nd)); o=[]
    for r in range(n):
        sel=np.concatenate([grp[z] for z in ib[r]])
        x=a[sel];y=b[sel]
        if x.std(ddof=1)>0 and y.std(ddof=1)>0:
            o.append(x.mean()/x.std(ddof=1)*np.sqrt(APY)-y.mean()/y.std(ddof=1)*np.sqrt(APY))
    return np.array(o)
ta,ga,Ra=load(R3+"/out/SL_RS_s42_FC.npz")
tb,gb,Rb=load(R3+"/out/SL_RSSHUFY_s42_FC.npz")
assert np.array_equal(ta,tb)
keep=np.array([t not in warm for t in ta])
out={}
for w,(lo,hi) in WINS.items():
    m=(ta>=lo)&(ta<hi)&keep
    x=ga[m]; y=gb[m]; d=x-y; dts=ta[m]//86400
    mn=boot(d,dts,"shufycontrast_mean_"+w)
    dsh=bootSR(x,y,dts,"shufycontrast_SR_"+w)
    a2=100.0*(0.05/2)/2.0
    out[w]={"n":int(m.sum()),
            "arm_mean":round(float(x.mean()),4),"shufy_mean":round(float(y.mean()),4),
            "arm_SR":round(float(x.mean()/x.std(ddof=1)*np.sqrt(APY)),3),
            "shufy_SR":round(float(y.mean()/y.std(ddof=1)*np.sqrt(APY)),3),
            "arm_turnover":round(float(Ra[m,C["turnover"]].mean()),5),
            "shufy_turnover":round(float(Rb[m,C["turnover"]].mean()),5),
            "arm_gross":round(float(Ra[m,C["gross_total"]].mean()),4),
            "shufy_gross":round(float(Rb[m,C["gross_total"]].mean()),4),
            "dmean":round(float(d.mean()),4),
            "dmean_ci95":[round(float(np.percentile(mn,2.5)),4),round(float(np.percentile(mn,97.5)),4)],
            "dmean_bonf2":[round(float(np.percentile(mn,a2)),4),round(float(np.percentile(mn,100-a2)),4)],
            "dmean_p_pos":round(float((mn>0).mean()),4),
            "dSharpe":round(float(x.mean()/x.std(ddof=1)*np.sqrt(APY)-y.mean()/y.std(ddof=1)*np.sqrt(APY)),3),
            "dSharpe_ci95":[round(float(np.percentile(dsh,2.5)),3),round(float(np.percentile(dsh,97.5)),3)],
            "dSharpe_p_pos":round(float((dsh>0).mean()),4),
            "corr_arm_shufy":round(float(np.corrcoef(x,y)[0,1]),4)}
    print(w,json.dumps(out[w]),flush=True)
json.dump(out,open(R3+"/CONTRAST_SHUFY.json","w"),indent=1)
