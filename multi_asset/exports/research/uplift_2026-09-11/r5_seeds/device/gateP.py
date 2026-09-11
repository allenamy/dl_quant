"""GATE P (ROUND 5). My device instance, knobs off, at the ARCHIVED cost plane (STD = costb_fee_steady.json)
must reproduce the archived A0 arrays BITWISE on every seat x seed cell, for BOTH d30_n2_c42_rec and _W.
Paths tested: A0 (native) and XIBPAR (the FEMAT injection path the arm rides on, which must be a no-op).
Also verifies E-0911-A warm-up / frozen-window non-overlap, and that the contrast arm actually differs."""
import numpy as np, json, os, sys, time, calendar
A="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
M="/workspace/uplift_2026-09-11/r5_seeds/arms"
KEYS=("d30_n2_c42_rec","d30_n2_c42_W","S0_rec","S0_W","legs_king","legs_rev24","legs_fund","legs_ts")
def cmp(pa,pb):
    a=np.load(pa,allow_pickle=True); b=np.load(pb,allow_pickle=True); r={}
    for k in KEYS:
        x=np.asarray(a[k],float); y=np.asarray(b[k],float)
        if x.shape!=y.shape: r[k]="shape %s vs %s"%(x.shape,y.shape); continue
        nx=np.isnan(x); ny=np.isnan(y)
        bw=bool(np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny]))
        r[k]={"bitwise":bw,"n_diff":int(((x!=y)&~(nx&ny)).sum()),"maxabs":0.0 if bw else float(np.nanmax(np.abs(x-y)))}
    r["symbols_equal"]=bool([str(s) for s in a["symbols"]]==[str(s) for s in b["symbols"]])
    r["device_sha256"]=json.loads(str(a["config_json"]))["HEALTH"]["device_sha256"]
    return r
OUT={"gate":"P_BITWISE_round5","device":"/workspace/uplift_2026-09-11/w10_sleeve.py","cost_plane":"STD costb_fee_steady.json"}
ok=True
for arm in ("A0","XIBPAR"):
    for seat in ("dyn","fix"):
        for s in ("42","2027"):
            pm="%s/w10_ablation_series_R5_STD_%s_%s_s%s.npz"%(M,arm,seat,s)
            pa="%s/w10_ablation_series_V4_A0_%s_s%s.npz"%(A,seat,s)
            r=cmp(pm,pa); OUT["%s_%s_s%s"%(arm,seat,s)]=r
            ok &= all(isinstance(r[k],dict) and r[k]["bitwise"] for k in KEYS) and r["symbols_equal"]
r=cmp("%s/w10_ablation_series_R5_STD_XIBLAG50_dyn_s42.npz"%M,"%s/w10_ablation_series_V4_A0_dyn_s42.npz"%A)
OUT["XIBLAG50_MUST_DIFFER"]={k:r[k] for k in ("d30_n2_c42_rec","legs_fund")}
OUT["contrast_differs"]=not r["d30_n2_c42_rec"]["bitwise"]
Z=np.load("%s/w10_ablation_series_R5_STD_A0_dyn_s42.npz"%M,allow_pickle=True)
cols=[str(c) for c in Z["cols"]]; R=np.asarray(Z["d30_n2_c42_rec"],float); ts=np.round(R[:,cols.index("ts")]).astype(np.int64)
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
lo,hi=T(2025,3,1),T(2026,8,10,20)+1
warm=np.zeros(len(ts),bool); warm[:900]=True; inwin=(ts>=lo)&(ts<hi)
postwarm=(~warm)&(ts<hi)
OUT["E0911A"]={"n_anchors":int(len(ts)),"warm_last":time.strftime("%F %HZ",time.gmtime(int(ts[899]))),
  "frozen_first":time.strftime("%F %HZ",time.gmtime(int(ts[inwin][0]))),"n_frozen":int(inwin.sum()),
  "n_full_postwarm":int(postwarm.sum()),"warm_cap_frozen":int((warm&inwin).sum())}
ok &= OUT["contrast_differs"] and OUT["E0911A"]["warm_cap_frozen"]==0
# the FIT plane must differ from STD on net_ex but be BITWISE identical on positions / seat / gross
pf="%s/w10_ablation_series_R5_FIT_A0_dyn_s42.npz"%M
if os.path.exists(pf):
    a=np.load(pf,allow_pickle=True); b=np.load("%s/w10_ablation_series_R5_STD_A0_dyn_s42.npz"%M,allow_pickle=True)
    ca=[str(c) for c in a["cols"]]; RA=np.asarray(a["d30_n2_c42_rec"],float); RB=np.asarray(b["d30_n2_c42_rec"],float)
    same=[c for c in ("ts","gross_total","turnover","w3_king","w3_fund","pnl_ex","carry_ex") if np.array_equal(RA[:,ca.index(c)],RB[:,ca.index(c)])]
    OUT["FIT_vs_STD"]={"cols_bitwise_equal":same,"W_bitwise":bool(np.array_equal(np.asarray(a["d30_n2_c42_W"]),np.asarray(b["d30_n2_c42_W"]))),
      "cost_ex_mean_STD":float(RB[:,ca.index("cost_ex")].mean()),"cost_ex_mean_FIT":float(RA[:,ca.index("cost_ex")].mean())}
    ok &= OUT["FIT_vs_STD"]["W_bitwise"] and len(same)==7
OUT["PASS"]=bool(ok)
print(json.dumps(OUT,indent=1))
json.dump(OUT,open("/workspace/uplift_2026-09-11/r5_seeds/receipts/GATE_P.json","w"),indent=1)
sys.exit(0 if ok else 3)
