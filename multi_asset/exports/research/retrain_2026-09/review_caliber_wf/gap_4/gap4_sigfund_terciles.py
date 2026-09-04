"""GAP#4: σ_fund tercile breakdown on pod port series (CAL=log + Π-caliber alt_true_new_*), 2024→26.
sigfund()/roll copied verbatim from jp_allweather.py L10-17 / L40. Units: net_ex = bps/anchor per NAV with book gross=gross_total
(w10_universe.py: pnl_r=(smr[m]*yv).sum()*1e4; gt=|sm|.sum()); per-gross = mean(net_ex)/mean(gross_total) (pod_units_table.py L11)."""
import numpy as np, time, json, os, sys, hashlib
OUT="/workspace/review_scratch/gap_4"; os.makedirs(OUT,exist_ok=True)
PANEL_LINK="/workspace/port_w10/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz"
PANEL=os.path.realpath(PANEL_LINK); print("PANEL realpath:",PANEL, "size",os.path.getsize(PANEL))
P=np.load(PANEL,allow_pickle=True); pts=P["ts"].astype(np.int64); FN=P["f_fund_now"]; IV=P["f_fund_iv"]; prow={int(t):j for j,t in enumerate(pts)}
print("panel ts",len(pts),time.strftime("%Y-%m-%d %H:%M",time.gmtime(int(pts[0]))),"→",time.strftime("%Y-%m-%d %H:%M",time.gmtime(int(pts[-1]))),"FN",FN.shape,"IV",IV.shape)
def sigfund(ts):   # verbatim jp_allweather.py L10-17
    out=np.full(len(ts),np.nan)
    for k,t in enumerate(ts):
        j=prow.get(int(t))
        if j is None: continue
        f=FN[j]; iv=IV[j]; iv=np.where(np.isfinite(iv)&(iv>0),iv,8.0); r=f*(8.0/iv); r=r[np.isfinite(r)]
        if len(r)>50: out[k]=np.std(r)*1e4
    return out
yr=lambda ts: np.array([time.gmtime(int(t)).tm_year for t in ts])
def dci(x, seed=0):  # jp_allweather.py L29-31 block bootstrap (6-anchor blocks, 4000 resamples)
    rng=np.random.default_rng(seed); nb=len(x)//6
    if nb<5: return np.nan,np.nan
    blocks=x[:nb*6].reshape(nb,6).sum(1); boots=np.array([blocks[rng.integers(0,nb,nb)].mean() for _ in range(4000)])/6
    return float(np.quantile(boots,0.025)), float(np.quantile(boots,0.975))
SER=[("pod_live_w3fix_callog_s42","/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_w3fix_callog_s42.npz","live form, W3FIX 0.21/0/0.79, CAL=log"),
     ("pod_live_callog_s42","/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_callog_s42.npz","live form, dynamic msharpe seat, CAL=log"),
     ("alt_true_new_w3fix","/workspace/review_scratch/refute_C6_1/dev/probe_artifacts/w10_ablation_series_alt_true_new_w3fix.npz","live form, W3FIX, y4=Π-caliber expm1(Σlog1p r5) window (E,E+4h], CAL=log"),
     ("alt_true_new_dyn","/workspace/review_scratch/refute_C6_1/dev/probe_artifacts/w10_ablation_series_alt_true_new_dyn.npz","live form, dynamic seat, y4=Π-caliber (E,E+4h], CAL=log"),
     ("pod_live_w3fix_calsimple_s42 [CONTAMINATED ref]","/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_w3fix_calsimple_s42.npz","live form, W3FIX, CAL=simple (expm1 pseudo-convexity) — reference only"),
     ("pod_live_calsimple_s42 [CONTAMINATED ref]","/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_calsimple_s42.npz","live form, dynamic seat, CAL=simple — reference only")]
res={}
def tstats(ne,gt,ts):
    n=len(ne); m=float(ne.mean()); sd=float(ne.std(ddof=1)); g=float(gt.mean()); per_g=m/g; ann_g=per_g*2190/100; sh=m/sd*np.sqrt(2190)
    lo,hi=dci(ne); x=2.0*ne/gt/1e4; eq=np.cumprod(1+x); comp2=eq[-1]**(2190/n)-1; dd=float((eq/np.maximum.accumulate(eq)-1).min())
    Y=yr(ts); comp={int(y):int((Y==y).sum()) for y in np.unique(Y)}
    return dict(n=n,net_ex_mean_bps_perNAV=round(m,4),ci95_lo=round(lo,4),ci95_hi=round(hi,4),gross_total_mean=round(g,4),per_gross_bps_anchor=round(per_g,4),
                pct_per_gross_per_yr=round(ann_g,2),pct_NAV_per_yr_at_2x_gross_arith=round(2*ann_g,2),sharpe=round(float(sh),3),comp_ann_2x_gross=round(float(comp2)*100,2),maxDD_2x_gross_pct=round(dd*100,2),years=comp)
for tag,f,desc in SER:
    if not os.path.exists(f): print("MISSING",tag,f); continue
    z=np.load(f,allow_pickle=True); cols=[str(c) for c in z["cols"]]; R=z["d30_n2_c42_rec"]; cfg=json.loads(str(z["config_json"]))
    ts=R[:,cols.index("ts")].astype(np.int64); ne=R[:,cols.index("net_ex")].astype(float); gt=R[:,cols.index("gross_total")].astype(float); w3k=R[:,cols.index("w3_king")].astype(float)
    sf=sigfund(ts); roll=np.array([np.nanmean(sf[max(0,i-29):i+1]) for i in range(len(sf))])   # jp_allweather.py L40
    Y=yr(ts); h=hashlib.sha256(open(f,"rb").read()).hexdigest()[:16]
    print(f"\n=== {tag} | {desc}\n    file={f} sha256[:16]={h} n={len(ts)} CAL={cfg['CAL']} W3FIX={cfg['W3FIX']} M={cfg['MEMBERS_TOPN']} T={cfg['TRADE_TOPN']} FTRIM={cfg['FTRIM']} FSEED={cfg['FSEED']}")
    print("    σ_fund(30-anchor roll) mean by year [bps]: "+", ".join(f"{y}:{np.nanmean(roll[Y==y]):.1f}" for y in sorted(set(Y.tolist()))))
    res[tag]={"file":f,"sha256_16":h,"config":cfg,"periods":{}}
    for per,sel0 in (("2024-26",Y>=2024),("2023-26 [supp]",Y>=2023)):
        sel=sel0&np.isfinite(roll); q=np.quantile(roll[sel],[1/3,2/3])
        print(f"  -- period {per}: n={int(sel.sum())} (roll-nan dropped {int((sel0&~np.isfinite(roll)).sum())}); tercile cuts on 30-anchor roll σ_fund: q1/3={q[0]:.2f} q2/3={q[1]:.2f} bps")
        out={}
        for nm,s in (("LOW",sel&(roll<=q[0])),("MID",sel&(roll>q[0])&(roll<=q[1])),("HIGH",sel&(roll>q[1]))):
            st=tstats(ne[s],gt[s],ts[s]); st["sigfund_roll_mean_bps"]=round(float(np.nanmean(roll[s])),2); st["w3_king_mean"]=round(float(w3k[s].mean()),3); out[nm]=st
            print(f"     {nm:4s} σ_fund≈{st['sigfund_roll_mean_bps']:5.1f}bp n={st['n']:4d} | net_ex {st['net_ex_mean_bps_perNAV']:+.3f} bps/anchor(perNAV) CI95[{st['ci95_lo']:+.3f},{st['ci95_hi']:+.3f}] | gross {st['gross_total_mean']:.3f} → {st['per_gross_bps_anchor']:+.3f} bps/anchor(per gross) = {st['pct_per_gross_per_yr']:+.1f} %/gross/yr ⇒ 2×gross {st['pct_NAV_per_yr_at_2x_gross_arith']:+.1f} %NAV/yr (arith) | comp 2×gross {st['comp_ann_2x_gross']:+.1f}%/yr maxDD {st['maxDD_2x_gross_pct']:.1f}% | Sharpe {st['sharpe']:+.2f} | w3_king {st['w3_king_mean']:.2f} | years {st['years']}")
        # sensitivity: raw (un-rolled) sf terciles with nanpercentile [33,67] as jp_live_caliber_tables.py L44
        selr=sel0&np.isfinite(sf); qr=np.nanpercentile(sf[selr],[33,67]); alt={}
        for nm,s in (("LOW",selr&(sf<=qr[0])),("MID",selr&(sf>qr[0])&(sf<=qr[1])),("HIGH",selr&(sf>qr[1]))):
            st=tstats(ne[s],gt[s],ts[s]); alt[nm]=st
        print(f"     [sens: raw sf p33/p67={qr[0]:.2f}/{qr[1]:.2f}] "+" | ".join(f"{k}: {v['net_ex_mean_bps_perNAV']:+.3f}bps → {v['pct_per_gross_per_yr']:+.1f}%/gross/yr S{v['sharpe']:+.2f} n{v['n']}" for k,v in alt.items()))
        res[tag]["periods"][per]={"cuts_roll":[float(q[0]),float(q[1])],"terciles_roll":out,"cuts_raw_p33_p67":[float(qr[0]),float(qr[1])],"terciles_raw":alt}
json.dump(res,open(f"{OUT}/gap4_sigfund_terciles.json","w"),indent=1,default=str); print("\nwrote",f"{OUT}/gap4_sigfund_terciles.json"); print("GAP4_DONE")
