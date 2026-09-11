"""A0 headline reproduction: own-support post-warm reading of my A0M run vs the round-5 brief's A0 = 1.4150."""
import numpy as np,json
R="/workspace/uplift_2026-09-11/r5nd"
def rd(p):
    Z=np.load(p,allow_pickle=True); Rr=np.asarray(Z["rec"],float); ix={str(c):i for i,c in enumerate(Z["cols"])}
    ts=Rr[:,ix["ts"]].astype(np.int64)
    g=np.where(Rr[:,ix["gross_total"]]>0,Rr[:,ix["net_ex"]]/np.maximum(Rr[:,ix["gross_total"]],1e-12),np.nan)
    return ts,g
def ep(s): return int((np.datetime64(s)-np.datetime64("1970-01-01T00:00:00"))/np.timedelta64(1,"s"))
out={}
for seat in ("dyn","fix"):
  for sd in ("42","2027"):
    for tag,path in (("A0M_mine",R+"/arms/R5U_A0M_%s_s%s.npz"%(seat,sd)),
                     ("A0_r4",  "/workspace/uplift_2026-09-11/r4_p1/arms/R4B1_A0_%s_s%s.npz"%(seat,sd))):
        ts,g=rd(path)
        for span,(lo,hi) in {"FULL_pw":(ep("2022-01-01T00:00"),ep("2026-08-10T20:00")),
                             "FULL_all":(0,1<<62)}.items():
            m=(ts>=lo)&(ts<=hi)&np.isfinite(g); m[:900]=False
            x=g[m]; out["%s|%s|s%s|%s"%(tag,seat,sd,span)]={"n":int(m.sum()),
                "g":round(float(x.mean()),4),"SR":round(float(x.mean()/x.std(ddof=1)*np.sqrt(2190)),4),
                "SE_SR":round(float(np.sqrt(2190/m.sum())),4)}
for k,v in out.items(): print("%-32s %s"%(k,json.dumps(v)))
json.dump(out,open(R+"/A0_headline_check.json","w"),indent=1)
