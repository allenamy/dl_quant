"""BUILD 2 step 1: reproduce round 7's motivating numbers FIRST-HAND from the archived leg/A0 arrays.
Caliber: g = net_ex/gross_total, bps/4h anchor per unit gross; post-warm drop 900 (E-0911-A);
cut 2026-08-30 20Z for PHI>0 arms (E-0911-D); fitted cost r3k/costb_PWR_G230k.json.
Gauge: LIVE (829 qvk base INTERSECT m1 CRYPTO umask) from r7f1/out/sigma_variants.npz.
Day-block bootstrap B=4000, seeds fixed, same estimator as r7f1/r7_final.py."""
import numpy as np, calendar, time, json, hashlib, os
ENV_WL=[]   # E-0826-D: this device reads NO environment variable
assert all(k not in os.environ for k in ENV_WL)
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
U="/workspace/uplift_2026-09-11"; APY=2190; WARM=900; CUT=T(2026,8,30,20); B=4000; TAU=4.75
S=np.load(U+"/r7f1/out/sigma_variants.npz",allow_pickle=True)
C=[str(c) for c in S["cols"]]; SR_=S["rec"]; si={c:i for i,c in enumerate(C)}
GL=dict(zip(SR_[:,0].astype(np.int64),SR_[:,si["LIVE_sig"]]))
def load(p,cut=CUT):
    Z=np.load(p,allow_pickle=True); cc=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cc)}
    k="rec" if "rec" in Z.files else "d30_n2_c42_rec"
    R=np.asarray(Z[k],float)[WARM:]; ts=np.round(R[:,ix["ts"]]).astype(np.int64)
    g=R[:,ix["net_ex"]]/R[:,ix["gross_total"]]; m=ts<=cut
    s=np.array([GL.get(int(t),np.nan) for t in ts[m]]); ok=np.isfinite(s)
    return ts[m][ok],g[m][ok],s[ok]
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY)) if len(x)>5 else float("nan")
def bstat(ts,fn,seed=1):
    d=ts//86400; ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    order=np.argsort(inv); st=np.searchsorted(inv[order],np.arange(nd)); en=np.append(st[1:],len(order))
    rng=np.random.default_rng([20260912,seed]); pick=rng.integers(0,nd,size=(B,nd)); out=[]
    for b in range(B):
        ii=np.concatenate([order[st[j]:en[j]] for j in pick[b]]); out.append(fn(ii))
    return np.array(out,float)
def ci(v,lo=2.5,hi=97.5):
    v=v[np.isfinite(v)]; return (float(np.percentile(v,lo)),float(np.percentile(v,hi)))
A={"A0_s42":U+"/r3k/arms/A0_PWR230k_s42.npz",
   "A0_s2027":U+"/r3k/arms/A0_PWR230k_s2027.npz",
   "FUND":U+"/r7f2/dev/probe_artifacts/w10_ablation_series_R7_LEGFUND_PWR_s42.npz",
   "KING":U+"/r7f2/dev/probe_artifacts/w10_ablation_series_R7_LEGKING_PWR_s42.npz"}
OUT={"caliber":"g = net_ex/gross_total bps/anchor per unit gross; post-warm 900; cut 2026-08-30 20Z; fitted cost costb_PWR_G230k.json",
     "gauge":"LIVE (829 qvk base INTER m1 CRYPTO umask), sigma_variants.npz","B":B,"TAU":TAU,
     "files":{k:v for k,v in A.items()},
     "file_sha16":{k:hashlib.sha256(open(v,'rb').read()).hexdigest()[:16] for k,v in A.items()}}
for nm,p in A.items():
    # single-leg PHI=0 arms have no coverage ceiling; still cut at the same date for comparability
    ts,g,s=load(p)
    row={"n":len(g),"span":[time.strftime("%Y-%m-%d %HZ",time.gmtime(int(ts[0]))),
                            time.strftime("%Y-%m-%d %HZ",time.gmtime(int(ts[-1])))],
         "mean_g":round(float(g.mean()),4),"SR_full":round(sr(g),4)}
    lo=s<TAU; hi=~lo
    for lab,m,sd_ in (("low_sigma_lt_4.75",lo,21),("high_sigma_ge_4.75",hi,22)):
        b=bstat(ts[m],lambda ii: g[m][ii].mean(),sd_)
        row[lab]={"n":int(m.sum()),"mean_g":round(float(g[m].mean()),4),
                  "CI95":[round(x,4) for x in ci(b)],"SR":round(sr(g[m]),4)}
    yr=np.array([time.gmtime(int(t)).tm_year for t in ts])
    row["by_year_mean_g"]={int(y):round(float(g[yr==y].mean()),4) for y in sorted(set(yr.tolist()))}
    row["by_year_n_low"]={int(y):int(((yr==y)&lo).sum()) for y in sorted(set(yr.tolist()))}
    OUT[nm]=row
    print(nm,json.dumps(row["low_sigma_lt_4.75"]),"SR_full",row["SR_full"],"n",row["n"],flush=True)
# A0 unconditional planning number
ts,g,s=load(A["A0_s42"])
b=bstat(ts,lambda ii: g[ii].mean(),31)
OUT["A0_s42_unconditional"]={"n":len(g),"mean_g":round(float(g.mean()),4),
    "CI95":[round(x,4) for x in ci(b)],"SR":round(sr(g),4)}
print("A0 uncond",json.dumps(OUT["A0_s42_unconditional"]))
# seat blindness: corr(sigma, w3_fund) reproduced
Z=np.load(A["A0_s42"],allow_pickle=True); cc=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cc)}
k="rec" if "rec" in Z.files else "d30_n2_c42_rec"
R=np.asarray(Z[k],float)[WARM:]; tsa=np.round(R[:,ix["ts"]]).astype(np.int64)
m=tsa<=CUT; w3f=R[m,ix["w3_fund"]]; ss=np.array([GL.get(int(t),np.nan) for t in tsa[m]])
ok=np.isfinite(ss)&np.isfinite(w3f)
OUT["seat_blindness"]={"corr_sigma_w3fund":round(float(np.corrcoef(ss[ok],w3f[ok])[0,1]),4),
    "w3_fund_mean_low_sigma":round(float(w3f[ok&(ss<TAU)].mean()),4),
    "w3_fund_mean_high_sigma":round(float(w3f[ok&(ss>=TAU)].mean()),4)}
qs=np.quantile(ss[ok],np.linspace(0,1,11)); qs[0]-=1e-9; qs[-1]+=1e-9
OUT["seat_blindness"]["w3_fund_by_sigma_decile"]=[round(float(w3f[ok][(ss[ok]>qs[k2])&(ss[ok]<=qs[k2+1])].mean()),4) for k2 in range(10)]
print("seat",json.dumps(OUT["seat_blindness"]))
OUT["self_sha256"]=hashlib.sha256(open(__file__,'rb').read()).hexdigest()
json.dump(OUT,open(U+"/r8b2/out/R8_REPRO.json","w"),indent=1)
print("REPRO_DONE")
