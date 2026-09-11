#!/usr/bin/env python
"""READ-ONLY: backtest daily-tail distribution + intraday dependence, from the archived
health_check main-arm series (same artifact giveback_diag used). Writes nothing."""
import numpy as np, json, time, calendar, hashlib, sys
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={k:i for i,k in enumerate(COLS)}
L=2.0
def T(s): return int(calendar.timegm(time.strptime(s,"%Y-%m-%d")))
def sha16(p): return hashlib.sha256(open(p,"rb").read()).hexdigest()[:16]
def daily(g, ts):
    r = L*g/1e4; d = ts//86400; ud,inv = np.unique(d,return_inverse=True)
    return ud, np.expm1(np.bincount(inv, np.log1p(r)))
out={}
for seed in (42,2027):
    p=f"/workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s{seed}_ccal.npz"
    Z=np.load(p,allow_pickle=True)
    assert [str(c) for c in Z["cols"]]==COLS
    R=Z["d30_n2_c42_rec"]
    ts=R[:,0].astype(np.int64); g=R[:,C["net_ex"]]/R[:,C["gross_total"]]
    o={"path":p,"sha16":sha16(p),"n_anchors":int(len(ts)),
       "t0":time.strftime("%Y-%m-%d",time.gmtime(int(ts.min()))),
       "t1":time.strftime("%Y-%m-%d",time.gmtime(int(ts.max())))}
    wins={"2024->26":(T("2024-01-01"),2**40),
          "2026->08-30":(T("2026-01-01"),2**40),
          "2026-06..08":(T("2026-06-01"),2**40),
          "2026-08":(T("2026-08-01"),2**40)}
    o["windows"]={}
    rng=np.random.default_rng(20260911)
    for wn,(lo,hi) in wins.items():
        m=(ts>=lo)&(ts<hi); gw=g[m]; tw=ts[m]
        if m.sum()<12: continue
        ud,dr=daily(gw,tw)
        rr=L*gw/1e4
        # anchors per day
        cnt=np.bincount(np.unique(tw//86400,return_inverse=True)[1])
        full=cnt==6
        drf=dr[full]
        vr=float(np.var(dr,ddof=1)/(6*np.var(rr,ddof=1)))
        vrf=float(np.var(drf,ddof=1)/(6*np.var(rr,ddof=1)))
        # autocorrelation of per-anchor g (consecutive anchors)
        ac=[float(np.corrcoef(gw[:-k],gw[k:])[0,1]) for k in (1,2,3,4,5,6)]
        # independence null: shuffle anchors, re-bucket into groups of 6, count tails
        NB=4000; tails4=[];tails268=[];sds=[]
        n6=(len(rr)//6)*6
        for _ in range(NB):
            perm=rng.permutation(len(rr))[:n6]
            blk=np.expm1(np.log1p(rr[perm]).reshape(-1,6).sum(1))
            tails4.append(float((blk<=-0.04).mean())); tails268.append(float((blk<=-0.0268).mean()))
            sds.append(float(blk.std(ddof=1)))
        o["windows"][wn]={
            "n_anchors":int(m.sum()),"n_days":int(len(dr)),"n_full_days":int(full.sum()),
            "mean_bps":float(gw.mean()),"sd_bps_anchor":float(gw.std(ddof=1)),
            "sd_pct_anchor_2x":float(rr.std(ddof=1)*100),
            "daily_mean_pct":float(dr.mean()*100),"daily_sd_pct":float(dr.std(ddof=1)*100),
            "daily_sd_pct_fulldays":float(drf.std(ddof=1)*100),
            "sqrt6_x_anchor_sd_pct":float(rr.std(ddof=1)*100*np.sqrt(6)),
            "variance_ratio_all":vr,"variance_ratio_fulldays":vrf,
            "autocorr_g_lag1_6":ac,
            "days_le_200":int((dr<=-0.02).sum()),"days_le_268":int((dr<=-0.0268).sum()),
            "days_le_400":int((dr<=-0.04).sum()),"worst_day_pct":float(dr.min()*100),
            "iid_shuffle_p_le400_mean":float(np.mean(tails4)),
            "iid_shuffle_p_le400_ci":[float(np.percentile(tails4,2.5)),float(np.percentile(tails4,97.5))],
            "iid_shuffle_p_le268_mean":float(np.mean(tails268)),
            "iid_shuffle_sd_pct_mean":float(np.mean(sds)*100),
            "anchors_le_40bps_frac":float((gw<=-40).mean()),
            "g_pct_1_5":[float(np.percentile(gw,1)),float(np.percentile(gw,5))],
        }
    out[f"s{seed}"]=o
print(json.dumps(out,indent=1))
