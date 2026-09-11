import numpy as np, time, json, collections
PAN="/workspace/data/wide_panel_4h_v2holefix.npz"
MET="/workspace/data/wide_fea_v4_meta.npz"
P=np.load(PAN,allow_pickle=True); M=np.load(MET,allow_pickle=True)
pts=P["ts"].astype(np.int64); syms=[str(s) for s in P["symbols"]]
FN=P["f_fund_now"]; FE=P["f_fund_ema_v1"]
row={int(t):j for j,t in enumerate(pts)}
E_ts=M["E_ts"].astype(np.int64); members=M["members"]; y4=M["y4"]
nA=len(E_ts)
btc=syms.index("BTCUSDT")
# first finite y4 anchor per column (listing age proxy)
fin=np.isfinite(y4)
firstA=np.full(y4.shape[1], 10**9, np.int64)
for j in range(y4.shape[1]):
    w=np.nonzero(fin[:,j])[0]
    if w.size: firstA[j]=w[0]
rows=[]
prev=None
for i in range(nA):
    m=np.asarray(members[i],dtype=np.int64)
    yv=y4[i,m]; ok=np.isfinite(yv); mm=m[ok]; yv=yv[ok]
    if mm.size<30:
        prev=set(mm.tolist()); continue
    j=row.get(int(E_ts[i]))
    fn=FN[j,mm] if j is not None else np.full(mm.size,np.nan)
    fe=FE[j,mm] if j is not None else np.full(mm.size,np.nan)
    fnf=fn[np.isfinite(fn)]; fef=fe[np.isfinite(fe)]
    xs=float(yv.mean()); sd=float(yv.std())
    b=float(y4[i,btc]) if np.isfinite(y4[i,btc]) else np.nan
    cur=set(mm.tolist())
    turn=np.nan
    if prev:
        turn=1.0-len(cur&prev)/max(len(cur|prev),1)
    age=(E_ts[i]-E_ts[firstA[mm]])/86400.0
    rows.append(dict(ts=int(E_ts[i]), n=int(mm.size),
        xs_mean_bps=xs*1e4, disp_bps=sd*1e4, btc_bps=(b*1e4 if b==b else np.nan),
        altmbtc_bps=((xs-b)*1e4 if b==b else np.nan),
        comov=abs(xs)/sd if sd>0 else np.nan,
        breadth_pos=float((yv>0).mean()),
        fund_med=float(np.median(fnf)) if fnf.size else np.nan,
        fund_absp75=float(np.percentile(np.abs(fnf),75)) if fnf.size else np.nan,
        fund_sd=float(fnf.std()) if fnf.size else np.nan,
        fundema_sd=float(fef.std()) if fef.size else np.nan,
        turnover=turn, share_new90=float((age<90).mean()), med_age_d=float(np.median(age))))
    prev=cur
np.save("/workspace/codex_research/uplift_regime_v4_rows.npy", np.array(rows,dtype=object), allow_pickle=True)
import csv
keys=list(rows[0].keys())
with open("/workspace/codex_research/uplift_regime_v4.csv","w",newline="") as f:
    w=csv.DictWriter(f,keys); w.writeheader(); w.writerows(rows)
print("wrote",len(rows),"anchors", time.strftime("%Y-%m-%d",time.gmtime(rows[0]["ts"])), time.strftime("%Y-%m-%d",time.gmtime(rows[-1]["ts"])))
