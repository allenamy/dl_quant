"""GAP#6 stats: shifted window [E+6,E+53] vs unshifted (E,E+4h] (refute_C6_2 altrun) vs base meta; same stats formula as refute_C6_2/final_stats.py."""
import numpy as np, json, time, calendar
CUT=calendar.timegm(time.strptime("2026-08-10 20:00","%Y-%m-%d %H:%M"))
C6="/workspace/review_scratch/refute_C6_2/altrun"
G6="/workspace/review_scratch/gap_6/altrun"; PORT="/workspace/port_w10/probe_artifacts"
def load(p):
    z=np.load(p,allow_pickle=True); cols=[str(c) for c in z["cols"]]; c={n:k for k,n in enumerate(cols)}; R=z["d30_n2_c42_rec"]; return R,c,json.loads(str(z["config_json"]))
def yr(ts): return np.array([time.gmtime(int(t)).tm_year for t in ts])
def ym(ts): return np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in ts])
def stats(R,c,m):
    a=R[m,c["net_ex"]]; g=R[m,c["gross_total"]]; mean=a.mean(); sd=a.std(ddof=1); sh=mean/sd*np.sqrt(2190); cum=np.cumsum(a); dd=np.max(np.maximum.accumulate(cum)-cum)
    pg=mean/g.mean(); pg2=np.mean(a/g)
    mm=ym(R[m,c["ts"]].astype(np.int64)); wm=min(((a[mm==k].sum(),k) for k in np.unique(mm)))
    return dict(n=int(m.sum()),mean=mean,S=sh,maxDD=dd,pnl=R[m,c["pnl_ex"]].mean(),carry=R[m,c["carry_ex"]].mean(),cost=R[m,c["cost_ex"]].mean(),gross=g.mean(),pg=pg,pg_yr=pg*21.9,pg2=pg2,pg2_yr=pg2*21.9,worst_month=wm[0],worst_month_k=int(wm[1]),w3k=R[m,c["w3_king"]].mean())
def fmt(s): return f"n={s['n']:4d} mean={s['mean']:+.4f} S={s['S']:.3f} maxDD={s['maxDD']:.0f} | pnl {s['pnl']:+.4f} carry {s['carry']:.4f} cost {s['cost']:.4f} gross {s['gross']:.3f} w3k {s['w3k']:.3f} | /gross mean/mean(g)={s['pg']:+.4f} ({s['pg_yr']:+.1f}%/yr, 2x {2*s['pg_yr']:+.1f}%) mean(a/g)={s['pg2']:+.4f} ({s['pg2_yr']:+.1f}%/yr) | worst month {s['worst_month']:+.0f} bps ({s['worst_month_k']})"
PER=(("2024",lambda y,ts:y==2024),("2025",lambda y,ts:y==2025),("2026 all",lambda y,ts:y==2026),("2026<=08-10",lambda y,ts:(y==2026)&(ts<=CUT)),("2024on",lambda y,ts:y>=2024),("2024on<=08-10",lambda y,ts:(y>=2024)&(ts<=CUT)))
RUNS={"base_w3fix":f"{G6}/base/probe_artifacts/w10_ablation_series_alt_base_w3fix.npz","base_dyn":f"{G6}/base/probe_artifacts/w10_ablation_series_alt_base_dyn.npz",
"newsum_w3fix":f"{C6}/newsum/probe_artifacts/w10_ablation_series_alt_newsum_w3fix.npz","newprod_w3fix":f"{C6}/newprod/probe_artifacts/w10_ablation_series_alt_newprod_w3fix.npz",
"newsum_dyn":f"{C6}/newsum/probe_artifacts/w10_ablation_series_alt_newsum_dyn.npz","newprod_dyn":f"{C6}/newprod/probe_artifacts/w10_ablation_series_alt_newprod_dyn.npz",
"shiftsum_w3fix":f"{G6}/shiftsum/probe_artifacts/w10_ablation_series_alt_shiftsum_w3fix.npz","shiftprod_w3fix":f"{G6}/shiftprod/probe_artifacts/w10_ablation_series_alt_shiftprod_w3fix.npz",
"shiftsum_dyn":f"{G6}/shiftsum/probe_artifacts/w10_ablation_series_alt_shiftsum_dyn.npz","shiftprod_dyn":f"{G6}/shiftprod/probe_artifacts/w10_ablation_series_alt_shiftprod_dyn.npz"}
# bitwise anchors
for a,b in (("base_w3fix",f"{PORT}/w10_ablation_series_pod_live_w3fix_callog_s42.npz"),("base_dyn",f"{PORT}/w10_ablation_series_pod_live_callog_s42.npz")):
    Ra,ca,_=load(RUNS[a]); Rb,cb,_=load(b); print(f"BITWISE gap_6 {a} vs port: rec array_equal {np.array_equal(Ra,Rb)} max|Δ net_ex| {np.max(np.abs(Ra[:,ca['net_ex']]-Rb[:,cb['net_ex']]))}")
for a,b in (("base_w3fix",f"{C6}/base/probe_artifacts/w10_ablation_series_alt_base_w3fix.npz"),("base_dyn",f"{C6}/base/probe_artifacts/w10_ablation_series_alt_base_dyn.npz")):
    Ra,ca,_=load(RUNS[a]); Rb,cb,_=load(b); print(f"BITWISE gap_6 {a} vs refute_C6_2 base: rec array_equal {np.array_equal(Ra,Rb)}")
ALL={}
for nm,p in RUNS.items():
    R,c,cfg=load(p); ts=R[:,c["ts"]].astype(np.int64); y=yr(ts); ALL[nm]={}
    print("=====",nm,"| CONFIG CAL=",cfg["CAL"],"W3FIX=",cfg["W3FIX"],"MEMBERS_TOPN=",cfg["MEMBERS_TOPN"],"TRADE_TOPN=",cfg["TRADE_TOPN"],"FTRIM=",cfg["FTRIM"],"LEGS=",cfg["LEGS"],"n anchors",len(ts))
    for lab,f in PER:
        s=stats(R,c,f(y,ts)); ALL[nm][lab]=s; print(f"  {lab:14s} {fmt(s)}")
print("\n===== SHIFT EFFECT (shifted [E+6,E+53] minus unshifted (E,E+4h]); retention = shifted/unshifted mean")
for form in ("w3fix","dyn"):
    for cal in ("sum","prod"):
        u=ALL[f"new{cal}_{form}"]; s=ALL[f"shift{cal}_{form}"]
        print(f"--- {form} {cal.upper()}")
        for lab,_ in PER:
            du=u[lab]; ds=s[lab]; ret=ds["mean"]/du["mean"] if abs(du["mean"])>0.05 else float("nan")
            print(f"  {lab:14s} unshift {du['mean']:+.4f} (S {du['S']:.3f}, DD {du['maxDD']:.0f}) -> shift {ds['mean']:+.4f} (S {ds['S']:.3f}, DD {ds['maxDD']:.0f})  Δ {ds['mean']-du['mean']:+.4f}  ΔS {ds['S']-du['S']:+.3f}  retention {ret*100:.0f}%  | Δpnl {ds['pnl']-du['pnl']:+.4f} Δcarry {ds['carry']-du['carry']:+.4f} Δcost {ds['cost']-du['cost']:+.4f} Δgross {ds['gross']-du['gross']:+.4f}")
print("\n===== DEDUCTION CHAIN (per-gross, bps of gross/anchor): shifted Π mean/mean(g) − 0.3 exec fidelity (AUDIT_live_vs_replay_2026-09-04.md L10)")
for form in ("w3fix","dyn"):
    for lab,_ in PER:
        s=ALL[f"shiftprod_{form}"][lab]; u=ALL[f"newprod_{form}"][lab]; b=ALL[f"base_{form}"][lab]
        for tag,d in (("Σ[E,E+47] base",b),("Π(E,E+4h]",u),("Π[E+6,E+53]",s)):
            pg=d["pg"]; print(f"  {form:5s} {lab:14s} {tag:14s} net_ex {d['mean']:+.4f} /gross {pg:+.4f} ({pg*21.9:+.1f}%/yr; 2x {pg*43.8:+.1f}%)  −0.3 ⇒ {pg-0.3:+.4f} ({(pg-0.3)*21.9:+.1f}%/yr; 2x {(pg-0.3)*43.8:+.1f}%)  [NAV-book: {d['mean']-0.3*d['gross']:+.4f} bps/anchor]")
json.dump({k:{l:{kk:(float(v) if not isinstance(v,int) else v) for kk,v in s.items()} for l,s in d.items()} for k,d in ALL.items()},open("/workspace/review_scratch/gap_6/final_stats_gap6.json","w"),indent=1)
print("STATS_DONE")
