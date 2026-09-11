import numpy as np, json, time, calendar
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={k:i for i,k in enumerate(COLS)}
def T(s): return int(calendar.timegm(time.strptime(s,"%Y-%m-%d")))
out={}
for seed in (42,2027):
    p=f"/workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s{seed}_ccal.npz"
    Z=np.load(p,allow_pickle=True); R=Z["d30_n2_c42_rec"]
    ts=R[:,0].astype(np.int64); gt=R[:,C["gross_total"]]
    carry=R[:,C["carry_ex"]]/gt; cost=R[:,C["cost_ex"]]/gt; pnl=R[:,C["pnl_ex"]]/gt; net=R[:,C["net_ex"]]/gt
    o={}
    for wn,(lo,hi) in {"2024->26":(T("2024-01-01"),2**40),"2026->08-30":(T("2026-01-01"),2**40),
                       "2026-06..08":(T("2026-06-01"),2**40),"2026-08":(T("2026-08-01"),2**40),
                       "2026-08-22..30":(T("2026-08-22"),2**40)}.items():
        m=(ts>=lo)&(ts<hi)
        if m.sum()<6: continue
        o[wn]={"n":int(m.sum()),"carry_bps_per_anchor":float(carry[m].mean()),
               "carry_bps_per_day":float(carry[m].mean()*6),
               "cost_bps_per_anchor":float(cost[m].mean()),
               "pnl_bps_per_anchor":float(pnl[m].mean()),
               "net_bps_per_anchor":float(net[m].mean()),
               "carry_p05_p95":[float(np.percentile(carry[m],5)),float(np.percentile(carry[m],95))],
               "carry_min":float(carry[m].min()),"carry_max":float(carry[m].max())}
    out[f"s{seed}"]=o
print(json.dumps(out,indent=1))
