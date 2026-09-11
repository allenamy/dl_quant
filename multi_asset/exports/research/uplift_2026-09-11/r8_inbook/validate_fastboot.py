import numpy as np, json, calendar, sys
sys.path.insert(0,"/workspace/uplift_2026-09-11/r8_inbook")
from fastboot import boot_dsr_dg
APY=2190; WARM=900
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL_HI=T(2026,8,10,20)+1
def load(path):
    Z=np.load(path,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    Rr=np.asarray(Z["rec"],float)[WARM:]; ts=np.round(Rr[:,ix["ts"]]).astype(np.int64); m=ts<FULL_HI
    Rr=Rr[m]; ts=ts[m]; gt=Rr[:,ix["gross_total"]]
    return ts,Rr[:,ix["net_ex"]]/gt
ta,a=load("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz")
tb,b=load("/workspace/uplift_2026-09-11/r5_basis/arms/R5_FBSLOPE_NOLAG.npz")
com,ia,ib=np.intersect1d(ta,tb,return_indices=True); a=a[ia]; s=b[ib]; days=com//86400
al=0.10; C=(1-al)*a+al*s
D,_=boot_dsr_dg(a,C,days,0,2000); D9,_=boot_dsr_dg(a,C,days,9,2000)
out={"fast_k0":[float(np.percentile(D,2.5)),float(np.percentile(D,97.5))],
     "fast_k9":[float(np.percentile(D9,2.5)),float(np.percentile(D9,97.5))],
     "round5_loop_k0":[0.012059663151513642,0.21855843005929257],
     "round5_loop_k9":[0.006693338588335342,0.22023355147801668]}
out["maxabs_k0"]=max(abs(x-y) for x,y in zip(out["fast_k0"],out["round5_loop_k0"]))
out["maxabs_k9"]=max(abs(x-y) for x,y in zip(out["fast_k9"],out["round5_loop_k9"]))
out["PASS"]=bool(out["maxabs_k0"]<1e-9 and out["maxabs_k9"]<1e-9)
print(json.dumps(out,indent=1))
json.dump(out,open("/workspace/uplift_2026-09-11/r8_inbook/VALIDATE_FASTBOOT.json","w"),indent=1)
