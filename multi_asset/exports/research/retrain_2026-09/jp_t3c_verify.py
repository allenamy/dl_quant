"""T3c(DL 调节 z×(1+0.5·xz(F10)))换装前核验: V1 极端名贡献(书层 W×y4, |ret| 前5% 名), V2 regime 分档, V7 权重差, 月度命中。"""
import numpy as np, time
PD="probe_artifacts"; B="pod_backup_2026-08-21"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); y4=M["y4"]; mrow={int(t):i for i,t in enumerate(E)}
P=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=P["ts"].astype(np.int64); FN=P["f_fund_now"]; IV=P["f_fund_iv"]; prow={int(t):j for j,t in enumerate(pts)}
def load(tag):
    z=np.load(f"{PD}/w10_{tag}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]; g=lambda k: rec[:,cols.index(k)].astype(float)
    return rec[:,cols.index("ts")].astype(np.int64), g("net_ex"), g("nsel"), z["d30_n2_c42_W"]
yr=lambda ts: np.array([time.gmtime(int(t)).tm_year for t in ts]); ym=lambda ts: np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in ts])
sh=lambda x: x.mean()/(x.std()+1e-12)*np.sqrt(2190)
def sigfund(ts):
    out=np.full(len(ts),np.nan)
    for k,t in enumerate(ts):
        j=prow.get(int(t)); 
        if j is None: continue
        f=FN[j]; iv=np.where(np.isfinite(IV[j])&(IV[j]>0),IV[j],8.0); r=f*(8.0/iv); r=r[np.isfinite(r)]
        if len(r)>50: out[k]=np.std(r)*1e4
    return out
for base,arm,lab in (("uni2_N829T400F_ms_s42","fu_t3c_f10mod_ms_s42","s42"),("uni2_N829T400F_ms_s2027","fu_t3c_f10mod_ms_s2027","s2027")):
    tb,nb,ns,Wb=load(base); ta,na,_,Wa=load(arm); assert (tb==ta).all(); Y=yr(tb); d=na-nb
    # V1 极端名贡献: 书 P&L 中 |y4| 前 5% 名的贡献(bps of gross), 基 vs 臂, 2025-26 与 2023+
    def ext_contrib(W, sel):
        tot=[]; ext=[]
        for p in np.where(sel)[0]:
            i=mrow.get(int(tb[p])); 
            if i is None: continue
            w=W[p]; g=np.abs(w).sum()
            if g<=0: continue
            r=np.expm1(np.nan_to_num(y4[i],nan=0.0)); nz=w!=0; thr=np.quantile(np.abs(r[nz]),0.95) if nz.sum()>20 else np.inf
            e=nz&(np.abs(r)>=thr); tot.append(float((w/g*r).sum()*1e4)); ext.append(float((w[e]/g*r[e]).sum()*1e4))
        return np.mean(tot), np.mean(ext)
    for per,sel in (("2023+",Y>=2023),("2025-26",Y>=2025)):
        tb_,eb_=ext_contrib(Wb,sel); ta_,ea_=ext_contrib(Wa,sel)
        print(f"[{lab}] V1 {per}: 价格 P&L 均 基 {tb_:+.2f} → 臂 {ta_:+.2f} bps/锚 | 其中 |ret| 前5% 极端名贡献 基 {eb_:+.2f} → 臂 {ea_:+.2f}")
    # V2 regime
    sf=sigfund(tb)
    for per,sel0 in (("2023+",Y>=2023),("2025-26",Y>=2025)):
        q=np.nanpercentile(sf[sel0],[33,67]); qn=np.nanpercentile(ns[sel0],[33,67]); parts=[]
        for nm,v,qq in (("σ_fund",sf,q),("广度",ns,qn)):
            for lo,hi,tag in ((-np.inf,qq[0],"低"),(qq[0],qq[1],"中"),(qq[1],np.inf,"高")):
                s=sel0&(v>lo)&(v<=hi); parts.append(f"{nm}{tag} Δ{d[s].mean():+.3f}/ΔS{sh(na[s])-sh(nb[s]):+.2f}")
        print(f"[{lab}] V2 {per}: "+" | ".join(parts))
    mm=ym(tb[Y>=2025]); dm=d[Y>=2025]; months=np.unique(mm); print(f"[{lab}] 月度 Δ>0 命中 {np.mean([dm[mm==m].sum()>0 for m in months]):.0%} ({len(months)} 月) | 最差月 {min(dm[mm==m].sum() for m in months):+.1f} bps")
    G=np.abs(Wb).sum(1); dw=np.abs(Wa-Wb).sum(1)/np.maximum(G,1e-9); print(f"[{lab}] V7 权重差 Σ|Δw|/gross 末 30 锚中位 {np.median(dw[-30:]):.3f} | 2025-26 中位 {np.median(dw[Y>=2025]):.3f} ⇒ 首锚换手增量 ≈ {0.1*np.median(dw[-30:]):.3f}")
print("T3C_VERIFY_DONE")
