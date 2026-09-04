import numpy as np, json, time, itertools, sys
R="/workspace/review_scratch/combo_recheck"; P="/workspace/port_w10/probe_artifacts"
ARMS={  # (caliber, arm, seed) -> npz path
 ("log","A","42"):f"{R}/dev/probe_artifacts/w10_ablation_series_A_callog.npz",
 ("log","B","42"):f"{R}/dev/probe_artifacts/w10_ablation_series_B_callog.npz",
 ("log","C","42"):f"{R}/dev/probe_artifacts/w10_ablation_series_C_callog_s42.npz",
 ("log","C","2027"):f"{R}/dev/probe_artifacts/w10_ablation_series_C_callog_s2027.npz",
 ("log","D","42"):f"{P}/w10_ablation_series_pod_canon_callog_s42.npz",
 ("log","D","2027"):f"{R}/dev/probe_artifacts/w10_ablation_series_D_callog_s2027.npz",
 ("simple","A","42"):f"{R}/dev/probe_artifacts/w10_ablation_series_A_calsimple.npz",
 ("simple","B","42"):f"{R}/dev/probe_artifacts/w10_ablation_series_B_calsimple.npz",
 ("simple","C","42"):f"{R}/dev/probe_artifacts/w10_ablation_series_C_calsimple_s42.npz",
 ("simple","C","2027"):f"{R}/dev/probe_artifacts/w10_ablation_series_C_calsimple_s2027.npz",
 ("simple","D","42"):f"{P}/w10_ablation_series_pod_canon_calsimple_s42.npz",
 ("simple","D","2027"):f"{R}/dev/probe_artifacts/w10_ablation_series_D_calsimple_s2027.npz",
 ("prod","A","42"):f"{R}/dev_alt/probe_artifacts/w10_ablation_series_A_prod.npz",
 ("prod","B","42"):f"{R}/dev_alt/probe_artifacts/w10_ablation_series_B_prod.npz",
 ("prod","C","42"):f"{R}/dev_alt/probe_artifacts/w10_ablation_series_C_prod_s42.npz",
 ("prod","C","2027"):f"{R}/dev_alt/probe_artifacts/w10_ablation_series_C_prod_s2027.npz",
 ("prod","D","42"):f"{R}/dev_alt/probe_artifacts/w10_ablation_series_D_prod_s42.npz",
 ("prod","D","2027"):f"{R}/dev_alt/probe_artifacts/w10_ablation_series_D_prod_s2027.npz",
}
EXPECT={"A":("111",0.0),"B":("101",0.0),"C":("111",0.45),"D":("101",0.45)}
REC=sys.argv[1] if len(sys.argv)>1 else "d30_n2_c42_rec"
D={}; cfgs={}
for k,p in ARMS.items():
    z=np.load(p,allow_pickle=True); cols=[str(c) for c in z["cols"]]; cfg=json.loads(str(z["config_json"])); cfgs[k]=cfg
    assert cfg["LEGS"]==EXPECT[k[1]][0] and abs(cfg["PHI"]-EXPECT[k[1]][1])<1e-12, (k,cfg["LEGS"],cfg["PHI"])
    assert cfg["CAL"]==("simple" if k[0]=="simple" else "log"), (k,cfg["CAL"])
    if cfg["PHI"]>0: assert cfg["FSEED"]==k[2], (k,cfg["FSEED"])
    for kk in ("MEMBERS_TOPN","TRADE_TOPN"): assert cfg[kk]==0,(k,kk,cfg[kk])
    assert cfg["FTRIM"]=="off" and cfg["W3FIX"] is None and cfg["LOOK"]==900 and cfg["WRULE"]=="msharpe" and cfg["SLOW_NPY"]=="/workspace/shadow_bundle_v3/slow_pred_pinned.npy", (k,cfg)
    D[k]={c:z[REC][:,i] for i,c in enumerate(cols)}
# anchor-set check
ts0=D[("log","A","42")]["ts"].astype(np.int64)
for k in D: assert np.array_equal(D[k]["ts"].astype(np.int64),ts0), ("ts mismatch",k)
print("REC",REC,"| all",len(D),"arms share identical anchor set: n=",len(ts0),"first",time.strftime("%Y-%m-%d %H:%M",time.gmtime(int(ts0[0]))),"last",time.strftime("%Y-%m-%d %H:%M",time.gmtime(int(ts0[-1]))))
# F10 coverage cut: last anchor with finite F10 preds (s42 file), via dlw_targets E_ts alignment
_pd=np.load("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy"); _TG=np.load("/workspace/data/dlw_targets.npz",allow_pickle=True); _dts=_TG["E_ts"].astype(np.int64)
fin_rows=np.isfinite(_pd).any(1); last_f10=int(_dts[fin_rows].max()); first_f10=int(_dts[fin_rows].min())
print("F10 s42 preds finite rows: first",time.strftime("%Y-%m-%d %H:%M",time.gmtime(first_f10)),"last",time.strftime("%Y-%m-%d %H:%M",time.gmtime(last_f10)),"| rows",int(fin_rows.sum()),"/",len(_dts))
_pd2=np.load("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy"); fr2=np.isfinite(_pd2).any(1); print("F10 s2027 last finite",time.strftime("%Y-%m-%d %H:%M",time.gmtime(int(_dts[fr2].max()))),"rows",int(fr2.sum()))
CUT=last_f10
yrs=np.array([time.gmtime(int(t)).tm_year for t in ts0]); days=np.array([time.strftime("%Y-%m-%d",time.gmtime(int(t))) for t in ts0])
WIN={"2024":yrs==2024,"2025":yrs==2025,"2026<=cut":(yrs==2026)&(ts0<=CUT),"2026all":yrs==2026,"2024on":yrs>=2024,"2024on<=cut":(yrs>=2024)&(ts0<=CUT),"2025on":yrs>=2025,"2025on<=cut":(yrs>=2025)&(ts0<=CUT)}
print("window sizes:",{k:int(v.sum()) for k,v in WIN.items()})
def sharpe(x): return float(x.mean()/x.std(ddof=1)*np.sqrt(2190)) if len(x)>2 and x.std(ddof=1)>0 else float("nan")
def maxdd(x): c=np.cumsum(x); return float(np.max(np.maximum.accumulate(c)-c)) if len(x) else float("nan")
def stats(d,m):
    x=d["net_ex"][m]
    return {"n":int(m.sum()),"mean":round(float(x.mean()),4),"sharpe":round(sharpe(x),3),"maxDD":round(maxdd(x),1),"gross":round(float(d["gross_total"][m].mean()),4),
            "w_king":round(float(d["w3_king"][m].mean()),4),"w_rev24":round(float(d["w3_rev24"][m].mean()),4),"w_fund":round(float(d["w3_fund"][m].mean()),4),
            "turn":round(float(d["turnover"][m].mean()),5),"carry":round(float(d["carry_ex"][m].mean()),4),"cost":round(float(d["cost_ex"][m].mean()),4)}
OUT={"REC":REC,"cut_ts":CUT,"cut_iso":time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(CUT)),"n_anchors":int(len(ts0)),"windows":{k:int(v.sum()) for k,v in WIN.items()},"arms":{},"deltas":{}}
NAMES={"A":"A LEGS=111 PHI=0 (pre-combo three legs)","B":"B LEGS=101 PHI=0 (drop rev24 only)","C":"C LEGS=111 PHI=0.45 (add V2MAIN only)","D":"D LEGS=101 PHI=0.45 (combo = deployed)"}
for cal in ("log","simple","prod"):
    print(f"\n===== CAL={cal}  [{'raw Σ-simple y4, no transform' if cal=='log' else 'expm1(Σ-simple y4)' if cal=='simple' else 'compounded Π(1+r5)-1 over [E+1,E+48], no transform'}]  rec={REC}")
    print(f"{'arm':14s}{'seed':6s}| " + " | ".join(f"{w:>20s}" for w in ("2024","2025","2026<=cut","2026all","2024on","2025on")) + " | gross w_king w_rev w_fund turn(2024on)")
    for arm in "ABCD":
        for seed in ("42","2027"):
            k=(cal,arm,seed)
            if k not in D: continue
            d=D[k]; row={w:stats(d,WIN[w]) for w in WIN}; OUT["arms"][f"{cal}/{arm}/s{seed}"]=row
            s24=row["2024on"]
            print(f"{arm:14s}{seed:6s}| " + " | ".join(f"{row[w]['mean']:+.3f} S{row[w]['sharpe']:+.2f} DD{row[w]['maxDD']:.0f}".rjust(20) for w in ("2024","2025","2026<=cut","2026all","2024on","2025on")) + f" | {s24['gross']:.3f} {s24['w_king']:.3f} {s24['w_rev24']:.3f} {s24['w_fund']:.3f} {s24['turn']:.4f}")
# bootstrap
rng=np.random.default_rng(20260904); NB=2000
def boot(delta,m):
    x=delta[m]; dd=days[m]; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
    sums=np.bincount(inv,weights=x,minlength=nd); cnts=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(NB,nd)); means=(sums[idx].sum(1))/(cnts[idx].sum(1))
    return float(x.mean()),float(np.percentile(means,2.5)),float(np.percentile(means,97.5)),float((means>0).mean()),nd
PAIRS=[("D","A","combo vs pre-combo"),("B","A","drop-rev24 effect"),("C","A","add-V2MAIN effect"),("D","B","V2MAIN effect given no rev24"),("D","C","drop-rev24 effect given V2MAIN")]
for cal in ("log","simple","prod"):
    print(f"\n===== DELTAS CAL={cal} (net_ex bps/anchor, paired by anchor; day-block bootstrap {NB} resamples, CI95)")
    print(f"{'pair':10s}{'seed':6s}| {'2024on: Δ [CI95] P>0':34s} | {'2025on: Δ [CI95] P>0':34s} | {'2024on<=cut':22s} | {'2025on<=cut':22s} | per-year Δ 2024/2025/2026<=cut/2026all | ΔSharpe 2024on/2025on | Δturn 2024on")
    for x,y,lab in PAIRS:
        for seed in ("42","2027"):
            kx=(cal,x,seed if x in "CD" else "42"); ky=(cal,y,seed if y in "CD" else "42")
            if kx not in D or ky not in D: continue
            if seed=="2027" and x in "AB" and y in "AB": continue
            delta=D[kx]["net_ex"]-D[ky]["net_ex"]
            res={}
            for w in ("2024on","2025on","2024on<=cut","2025on<=cut"):
                mu,lo,hi,p,nd=boot(delta,WIN[w]); res[w]={"mean":round(mu,4),"lo":round(lo,4),"hi":round(hi,4),"P>0":round(p,4),"n_days":int(nd)}
            py={w:round(float(delta[WIN[w]].mean()),4) for w in ("2024","2025","2026<=cut","2026all")}
            dsh={w:round(sharpe(D[kx]["net_ex"][WIN[w]])-sharpe(D[ky]["net_ex"][WIN[w]]),3) for w in ("2024on","2025on")}
            dturn=round(float((D[kx]["turnover"]-D[ky]["turnover"])[WIN["2024on"]].mean()),5)
            OUT["deltas"][f"{cal}/{x}-{y}/s{seed}"]={"label":lab,"windows":res,"per_year":py,"dSharpe":dsh,"dturn_2024on":dturn}
            f=lambda w: f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] {res[w]['P>0']:.3f}"
            print(f"{x}-{y:8s}{seed:6s}| {f('2024on'):34s} | {f('2025on'):34s} | {res['2024on<=cut']['mean']:+.3f} [{res['2024on<=cut']['lo']:+.3f},{res['2024on<=cut']['hi']:+.3f}] | {res['2025on<=cut']['mean']:+.3f} [{res['2025on<=cut']['lo']:+.3f},{res['2025on<=cut']['hi']:+.3f}] | {py['2024']:+.3f}/{py['2025']:+.3f}/{py['2026<=cut']:+.3f}/{py['2026all']:+.3f} | {dsh['2024on']:+.2f}/{dsh['2025on']:+.2f} | {dturn:+.4f}")
json.dump(OUT,open(f"{R}/stats_{REC}.json","w"),indent=1)
print("\nwrote",f"{R}/stats_{REC}.json")
