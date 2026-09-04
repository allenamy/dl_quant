import numpy as np, json, time, os
os.chdir("/workspace/port_w10")
def f(t): return time.strftime("%m-%d %HZ", time.gmtime(int(t)))
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); sy=[str(s) for s in PW["symbols"]]
sel=pts>=1787616000
np.savez_compressed("/workspace/review_scratch/gap_1/panel_fund_tail.npz", ts=pts[sel], symbols=np.array(sy), f_fund_now=PW["f_fund_now"][sel], f_fund_iv=PW["f_fund_iv"][sel], f_fund_ema_v1=PW["f_fund_ema_v1"][sel])
print("panel tail rows", int(sel.sum()), f(pts[sel][0]), f(pts[sel][-1]))
res={}
for tag in ("pod_live_w3fix_callog_s42","pod_live_callog_s42","pod_canon_w3fix_callog_s42"):
    z=np.load(f"probe_artifacts/w10_ablation_series_{tag}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; R=z["d30_n2_c42_rec"]; W=z["d30_n2_c42_W"]; ts=R[:,cols.index("ts")].astype(np.int64)
    s=ts>=1787616000
    res[tag]={"cols":cols,"rows":R[s].tolist(),"W_ts":ts[s].tolist(),"W":W[s].astype(float).tolist()}
    for lab,t0 in (("overlap 08-26 04Z->",1787713600),("Aug",1785542400),("2026",1767225600)):
        ss=ts>=t0; c=R[ss,cols.index("carry_ex")]; g=R[ss,cols.index("gross_total")]; n=R[ss,cols.index("net_ex")]
        print(tag, lab, "n=%d %s->%s carry_ex mean %+.3f per-gross(mean of ratio) %+.3f gross %.3f net_ex %+.3f" % (ss.sum(), f(ts[ss].min()), f(ts[ss].max()), c.mean(), (c/g).mean(), g.mean(), n.mean()))
    print("  W shape", W.shape, "gross_total check", float(np.abs(W[s][0]).sum()), float(R[s][0, cols.index("gross_total")]))
json.dump(res, open("/workspace/review_scratch/gap_1/replay_tail_rows.json","w"))
print("saved")
