import numpy as np, calendar, time, json
W="/dev/shm/news2_2026-09-23"
leg=np.load(W+"/work/legs.npz"); a=leg["E_ts"].astype(np.int64); WL=leg["WL"]; ready=leg["ready"]
def ts(s): return calendar.timegm(time.strptime(s,"%Y-%m-%dT%H:%M:%SZ"))
SEG={"2023H2":("2023-06-30T04:00:00Z","2023-12-31T20:00:00Z"),"2024":("2024-01-01T00:00:00Z","2024-12-31T20:00:00Z"),
     "2025":("2025-01-01T00:00:00Z","2025-12-31T20:00:00Z"),"pre2026":("2023-06-30T04:00:00Z","2025-12-31T20:00:00Z"),
     "2026":("2026-01-01T00:00:00Z","2026-08-31T00:00:00Z")}
for s,(lo,hi) in SEG.items():
    m=(a>=ts(lo))&(a<=ts(hi))&ready&np.isfinite(WL).all(1)
    w=WL[m]; den=w[:,0]+w[:,2]; w0=np.where(den>1e-12,w[:,0]/np.where(den>1e-12,den,1),0.5)
    print("%-8s n=%5d w0_mean=%.4f  frac(w0==1)=%.4f frac(w0==0)=%.4f frac(0.02<w0<0.98)=%.4f  raw_w3_equal_third=%.4f" % (
        s, m.sum(), w0.mean(), (w0>=1-1e-9).mean(), (w0<=1e-9).mean(), ((w0>0.02)&(w0<0.98)).mean(),
        (np.abs(w-1/3).max(1)<1e-6).mean()))
