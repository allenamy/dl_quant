"""ADVERSARIAL recompute of TRACK B. Independent of judge_tb.py."""
import numpy as np, calendar, os, json
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FR=(T(2025,3,1),T(2026,8,10,20)+1)
V4="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_%s_dyn_s%s.npz"
TB="/workspace/uplift_2026-09-11/dev_tb/probe_artifacts/w10_ablation_series_TB_%s_dyn_s%s.npz"
def load(p):
    R=np.load(p,allow_pickle=True)["d30_n2_c42_rec"]
    ts=np.round(R[:,0].astype(np.float64)).astype(np.int64)
    return ts,R
def boot_diff(ts,d,ci,lo=FR[0],hi=FR[1]):
    m=(ts>=lo)&(ts<hi); dd=d[m]
    rng=np.random.default_rng([20260905,ci])
    ud,inv=np.unique(ts[m]//86400,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=dd,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(dd.mean()),float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean()),int(m.sum())

print("=== 1. VALIDATION: reproduce published A1-A0 dyn ===")
for s,exp in (("42",(0.061,-0.168,0.287)),("2027",(0.048,-0.171,0.270))):
    ta,Ra=load(V4%("A1",s)); tb,Rb=load(V4%("A0",s))
    assert np.array_equal(ta,tb)
    ga=Ra[:,C["net_ex"]]/Ra[:,C["gross_total"]]; gb=Rb[:,C["net_ex"]]/Rb[:,C["gross_total"]]
    r=boot_diff(ta,ga-gb,0)
    print(f"  s{s}: {r[0]:+.4f} [{r[1]:+.4f},{r[2]:+.4f}] p={r[3]:.3f} n={r[4]}  published {exp}")

print("\n=== 2. A0/A1 pinned levels ===")
for nm in ("A0","A1"):
    for s in ("42","2027"):
        p=V4%(nm,s)
        if not os.path.exists(p): continue
        ts,R=load(p); m=(ts>=FR[0])&(ts<FR[1]); v=(R[:,C["net_ex"]]/R[:,C["gross_total"]])[m]
        print(f"  {nm} s{s}: g={v.mean():+.4f} SR={v.mean()/v.std(ddof=1)*np.sqrt(2190):.3f} n={m.sum()}")

ARMS=["BASE","BAND35e5","BAND45e5","BAND5e4","BAND6e4","BAND75e5","BAND1e3","EMA015","EMA020","EMA007","EMA005","EMA004","EMA003","B5E5","B5E15","TOPD50","TOPD100","TOPD200","CAD2","CAD3","CAD6","HOLD2","HOLD3","HOLD6"]
print("\n=== 3. ATTACK: mean-of-ratios g vs AGGREGATE g (sum net / sum gross) ===")
print("%-9s %-4s %9s %9s %9s %9s %9s %9s %9s"%("arm","seed","dG_mor","dG_agg","g_mor","g_agg","gross","absnet","SR_agg"))
out={}
for ai,nm in enumerate(ARMS):
    for s in ("42","2027"):
        p=TB%(nm,s)
        if not os.path.exists(p): continue
        ts,R=load(p); m=(ts>=FR[0])&(ts<FR[1])
        ne=R[m,C["net_ex"]]; gt=R[m,C["gross_total"]]
        if (gt<=0).any(): print(f"{nm:9s} s{s:4s} DEGENERATE"); continue
        g_mor=(ne/gt).mean(); g_agg=ne.sum()/gt.sum()
        # constant-gross series: rescale each anchor's book to the BASE mean gross -> net/gross * meangross_base
        out[(nm,s)]=dict(g_mor=g_mor,g_agg=g_agg,gross=gt.mean(),absnet=ne.mean(),ts=ts,ne=ne,gt=gt,m=m,R=R)
for ai,nm in enumerate(ARMS):
    for s in ("42","2027"):
        if (nm,s) not in out: continue
        o=out[(nm,s)]; b=out[("BASE",s)]
        dmor=o["g_mor"]-b["g_mor"]; dagg=o["g_agg"]-b["g_agg"]
        srag=(o["ne"]/o["gt"].mean())  # constant-gross normalisation (book rescaled to its own mean gross, no per-anchor ratio)
        SRa=srag.mean()/srag.std(ddof=1)*np.sqrt(2190)
        print("%-9s %-4s %+9.4f %+9.4f %+9.4f %+9.4f %9.4f %+9.4f %9.3f"%(nm,s,dmor,dagg,o["g_mor"],o["g_agg"],o["gross"],o["absnet"],SRa))
json.dump({f"{k[0]}_s{k[1]}":{kk:float(vv) for kk,vv in v.items() if kk in("g_mor","g_agg","gross","absnet")} for k,v in out.items()},open("/workspace/uplift_2026-09-11/attackB_agg.json","w"),indent=1)
