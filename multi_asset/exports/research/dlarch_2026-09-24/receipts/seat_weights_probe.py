import numpy as np, calendar, time, json
W="/dev/shm/news2_2026-09-23"
leg=np.load(W+"/work/legs.npz"); a=leg["E_ts"].astype(np.int64); WL=leg["WL"]; ready=leg["ready"]
def ts(s): return calendar.timegm(time.strptime(s,"%Y-%m-%dT%H:%M:%SZ"))
SEG={"2023H2":("2023-06-30T04:00:00Z","2023-12-31T20:00:00Z"),"2024":("2024-01-01T00:00:00Z","2024-12-31T20:00:00Z"),
     "2025":("2025-01-01T00:00:00Z","2025-12-31T20:00:00Z"),"pre2026":("2023-06-30T04:00:00Z","2025-12-31T20:00:00Z"),
     "2026":("2026-01-01T00:00:00Z","2026-08-31T00:00:00Z")}
out={}
for s,(lo,hi) in SEG.items():
    m=(a>=ts(lo))&(a<=ts(hi))&ready&np.isfinite(WL).all(1)
    w=WL[m]; den=w[:,0]+w[:,2]
    ok=den>1e-12
    w0=np.where(ok,w[:,0]/np.where(ok,den,1),0.5); w2=1.0-w0
    out[s]={"n":int(m.sum()),"raw_WL_mean":[float(x) for x in w.mean(0)],
            "masked_w0_model":float(w0.mean()),"masked_w2_fund":float(w2.mean()),
            "masked_w0_p10":float(np.percentile(w0,10)),"masked_w0_p90":float(np.percentile(w0,90)),
            "degenerate_den_anchors":int((~ok).sum()),
            "eff_f10_weight_in_raw_0.45xw0":float((0.45*w0).mean()),
            "eff_king_weight_in_raw_0.55xw0":float((0.55*w0).mean()),
            "eff_fund_weight_in_raw_w2":float(w2.mean())}
print(json.dumps(out,indent=1))
