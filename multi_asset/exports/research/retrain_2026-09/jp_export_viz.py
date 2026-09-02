"""可视化数据导出: 四条回放序列(msharpe/W3FIX × 基线/FTRIM)2023+ 日频净额(bps of gross)+ 2.0x 常杠杆权益 + 回撤; 逐年 净/夏普; regime 条件 Δ; σ_fund 日频。→ viz_backtest.json"""
import numpy as np, time, json
PD="/mnt/storage/private/work_hsy/probe_artifacts"; B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
def load(run):
    z=np.load(f"{PD}/{run}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
    return rec[:,cols.index("ts")].astype(np.int64), rec[:,cols.index("net_ex")].astype(float), rec[:,cols.index("turnover")].astype(float)
SER={"msharpe_base":"w10_canonpred_s42","msharpe_ftrim":"w10_band_pre_all10_zero","w3fix_base":"w10_canonfix_s42","w3fix_ftrim":"w10_band_fix_all10z"}
out={"series":{},"yearly":{},"regime":{},"lev":{}}
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); prow={int(t):j for j,t in enumerate(pts)}; Y4=PW["Y4"]
def daily(ts,net):
    d={}
    for t,x in zip(ts,net): d.setdefault(time.strftime("%Y-%m-%d",time.gmtime(int(t))),[]).append(x)
    days=sorted(d); v=np.array([np.sum(d[k]) for k in days]); return days, v
for k,run in SER.items():
    ts,net,to=load(run); yrs=np.array([time.gmtime(int(t)).tm_year for t in ts]); sel=yrs>=2023; ts=ts[sel]; net=net[sel]; to=to[sel]; yrs=yrs[sel]
    days,dv=daily(ts,net); r=2.0*dv*1e-4; eq=np.cumprod(1+r); dd=eq/np.maximum.accumulate(eq)-1
    out["series"][k]={"days":days,"daily_bps":[round(float(x),3) for x in dv],"eq2x":[round(float(x),5) for x in eq],"dd2x":[round(float(x),5) for x in dd]}
    out["yearly"][k]={int(Y):{"net":round(float(net[yrs==Y].mean()),3),"sharpe":round(float(net[yrs==Y].mean()/(net[yrs==Y].std()+1e-12)*np.sqrt(2190)),2),"turnover":round(float(to[yrs==Y].mean()),4)} for Y in (2023,2024,2025,2026)}
    for L in (1.5,2.0,2.5):
        rr=L*dv*1e-4; e=np.cumprod(1+rr); ddL=(e/np.maximum.accumulate(e)-1).min(); ann=e[-1]**(365/len(rr))-1
        out["lev"].setdefault(k,{})[str(L)]={"ann":round(float(ann),4),"maxdd":round(float(ddL),4),"worst_day":round(float(rr.min()),4),"days_le_m4":int((rr<=-0.04).sum())}
# regime 条件 Δ(FTRIM−基线) 两口径
def regime_feats(ts):
    mk=np.full(len(ts),np.nan); sg=np.full(len(ts),np.nan)
    for i,t in enumerate(ts):
        j=prow.get(int(t))
        if j is None: continue
        y=Y4[j]; y=y[np.isfinite(y)]
        if len(y)>50: mk[i]=np.median(y); sg[i]=np.std(y)
    return mk,sg
for cal,(bn,an) in {"msharpe":("w10_canonpred_s42","w10_band_pre_all10_zero"),"w3fix":("w10_canonfix_s42","w10_band_fix_all10z")}.items():
    tb,nb,_=load(bn); ta,na,_=load(an); mb={int(t):i for i,t in enumerate(tb)}; ia=[];ib=[]
    for k2,t in enumerate(ta):
        i=mb.get(int(t))
        if i is not None: ia.append(k2); ib.append(i)
    ia=np.array(ia); ib=np.array(ib); ts=tb[ib]; yrs=np.array([time.gmtime(int(t)).tm_year for t in ts]); sel=yrs>=2023
    d=(na[ia]-nb[ib])[sel]; ts=ts[sel]; mk,sg=regime_feats(ts)
    q=np.nanquantile(sg,[1/3,2/3]); t3=np.where(sg<=q[0],0,np.where(sg<=q[1],1,2))
    out["regime"][cal]={"disp_tercile":[round(float(d[(t3==k)&np.isfinite(sg)].mean()),3) for k in range(3)],
        "market":{"down":round(float(d[mk<-0.01].mean()),3),"flat":round(float(d[np.abs(mk)<=0.01].mean()),3),"up":round(float(d[mk>0.01].mean()),3)},
        "yearly":{int(Y):round(float(d[yrs[sel]==Y].mean()),3) for Y in (2023,2024,2025,2026)}, "total":round(float(d.mean()),3)}
H=np.load(f"{PD}/regime_hist.npz"); hts=H["ts"].astype(np.int64); sig=H["sig_fund"]
dd={}
for t,x in zip(hts,sig):
    if np.isfinite(x): dd.setdefault(time.strftime("%Y-%m-%d",time.gmtime(int(t))),[]).append(x)
out["sig_fund_daily"]={"days":sorted(dd),"v":[round(float(np.mean(dd[k])),2) for k in sorted(dd)]}
json.dump(out, open(f"{PD}/viz_backtest.json","w")); print("VIZ_EXPORT_DONE", {k:len(v["days"]) for k,v in out["series"].items()})
