# ADDENDUM 5 §A5.3/§A5.4-2. Series = d30_n2_c42_rec; axis = rec ts col (NOT legs_ts: U-FROZEN drops 30 rows from rec).
# g = net_ex/gross_total  [bps/anchor per gross]  -- EXACTLY health_metrics.py L112 / judge_ca.py. No 1e4.
import numpy as np, json, time, calendar
D="dev_alt/probe_artifacts/w10_ablation_series_%s.npz"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; CUT=calendar.timegm((2026,8,10,20,0,0)); APY=2190
def load(tag):
    z=np.load(D%tag,allow_pickle=True); assert [str(x) for x in z["cols"]]==COLS
    R=z["d30_n2_c42_rec"]; return R[:,C["ts"]].astype(np.int64), R[:,C["net_ex"]]/R[:,C["gross_total"]], R, z["d30_n2_c42_W"]
def T(y,m=1,d=1): return calendar.timegm((y,m,d,0,0,0))
# ---------- SC2 on the rec axis ----------
print("== SC2 (rec axis, UPIT vs UCRYPTO) ==")
sc2=True
for pref in ["M1","MEM","FIX"]:
    for s in ["42","2027"]:
        ta,_,Ra,Wa=load("%s_UPIT_prod_s%s_ccal"%(pref,s)); tb,_,Rb,Wb=load("%s_UCRYPTO_prod_s%s_ccal"%(pref,s))
        ax=ta.shape==tb.shape and bool((ta==tb).all()); e=ta<T(2026)
        m1=float(np.abs(np.nan_to_num(Ra[e])-np.nan_to_num(Rb[e])).max()); m2=float(np.abs(np.nan_to_num(Wa[e].astype(float))-np.nan_to_num(Wb[e].astype(float))).max())
        d1=float(np.abs(np.nan_to_num(Ra[~e])-np.nan_to_num(Rb[~e])).max()); ok=ax and m1==0.0 and m2==0.0 and d1>0; sc2&=ok
        print("  %-12s n=%d axis_eq=%s 2022-25 rec/W maxabs=%.3e/%.3e (%d cells) 2026 maxabs=%.4g -> %s"%(pref+"_s"+s,len(ta),ax,m1,m2,int(Ra[e].size+Wa[e].size),d1,"OK" if ok else "FAIL"))
print("SC2_ALL","PASS" if sc2 else "FAIL"); assert sc2
# ---------- SC5: reproduce the published per-window means before reporting anything ----------
print("== SC5 reproduction vs results/*.json ==")
WKEY={"2024":(T(2024),T(2025)),"2025":(T(2025),T(2026)),"2026->cut":(T(2026),CUT+1),"2024->26":(T(2024),CUT+1)}
rep=True
for tag in ["M1_UPIT_prod_s42_ccal","M1_UPIT_prod_s2027_ccal","M1_UCRYPTO_prod_s42_ccal","M1_UCRYPTO_prod_s2027_ccal","M1_UFROZEN_prod_s42_ccal","M1_UFROZEN_prod_s2027_ccal","MEM_UCRYPTO_prod_s42_ccal","FIX_UCRYPTO_prod_s42_ccal"]:
    j=json.load(open("results/%s.json"%tag)); ts,g,_,_=load(tag)
    for w,(lo,hi) in WKEY.items():
        pub=j["windows"][w]["per_gross"]["mean_bps_anchor"]; m=(ts>=lo)&(ts<hi)&(ts<=CUT)
        mine=round(float(g[m].mean()),4); okk=abs(mine-pub)<=1e-4; rep&=okk
        if not okk: print("  MISMATCH %s %s mine=%.4f pub=%.4f"%(tag,w,mine,pub))
    print("  %-28s reproduced 4/4 windows"%tag)
print("SC5",("PASS" if rep else "FAIL")); assert rep
# ---------- three-way split ----------
WIN={"2024":(T(2024),T(2025)),"2025":(T(2025),T(2026)),"2026->cut":(T(2026),CUT+1),"2024->26":(T(2024),CUT+1),"full->cut":(0,CUT+1)}
rng=np.random.default_rng(20260905)
def judge(a,b):
    ta,ga,_,_=load(a); tb,gb,_,_=load(b)
    com=np.intersect1d(ta,tb); ia={t:i for i,t in enumerate(ta)}; ib={t:i for i,t in enumerate(tb)}
    ts=com; ga=ga[[ia[t] for t in com]]; gb=gb[[ib[t] for t in com]]; d=gb-ga
    res={"n_a":len(ta),"n_b":len(tb),"n_common":len(com)}
    for w,(lo,hi) in WIN.items():
        m=(ts>=lo)&(ts<hi)
        if m.sum()<12: continue
        v=d[m]; dk=ts[m]//86400; ud,inv=np.unique(dk,return_inverse=True); nd=len(ud)
        S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
        idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
        res[w]={"n":int(m.sum()),"a":round(float(ga[m].mean()),4),"b":round(float(gb[m].mean()),4),"delta":round(float(v.mean()),4),
                "ci95":[round(float(np.percentile(mn,2.5)),4),round(float(np.percentile(mn,97.5)),4)],"p_gt0":round(float((mn>0).mean()),3),
                "a_pct_yr_2x":round(float(ga[m].mean()*APY/1e4*100*2),3),"b_pct_yr_2x":round(float(gb[m].mean()*APY/1e4*100*2),3)}
    return res
out={}
for s in ["42","2027"]:
    P,Cc,F=("M1_UPIT_prod_s%s_ccal"%s,"M1_UCRYPTO_prod_s%s_ccal"%s,"M1_UFROZEN_prod_s%s_ccal"%s)
    out["s"+s]={"IC__UCRYPTO_minus_UPIT":judge(P,Cc),"LA__UFROZEN_minus_UCRYPTO":judge(Cc,F),"GAP__UFROZEN_minus_UPIT":judge(P,F)}
    out["s"+s+"_MEM_minus_M1_on_UCRYPTO"]=judge("M1_UCRYPTO_prod_s%s_ccal"%s,"MEM_UCRYPTO_prod_s%s_ccal"%s)
    out["s"+s+"_FIXSEAT_minus_M1_on_UCRYPTO"]=judge("M1_UCRYPTO_prod_s%s_ccal"%s,"FIX_UCRYPTO_prod_s%s_ccal"%s)
json.dump(out,open("results/ADDENDUM5_threeway.json","w"),indent=1)
print("== THREE-WAY (bps/anchor per gross) ==")
for s in ["42","2027"]:
    print(" seed %s"%s)
    for k in ["IC__UCRYPTO_minus_UPIT","LA__UFROZEN_minus_UCRYPTO","GAP__UFROZEN_minus_UPIT"]:
        r=out["s"+s][k]; print("  %-28s n_common=%d"%(k,r["n_common"]))
        for w in ["2024","2025","2026->cut","2024->26","full->cut"]:
            if w in r: print("     %-10s n=%5d  a=%+.4f b=%+.4f  D=%+.4f  CI[%+.4f,%+.4f] p=%.3f"%(w,r[w]["n"],r[w]["a"],r[w]["b"],r[w]["delta"],r[w]["ci95"][0],r[w]["ci95"][1],r[w]["p_gt0"]))
    for k in ["_MEM_minus_M1_on_UCRYPTO","_FIXSEAT_minus_M1_on_UCRYPTO"]:
        r=out["s"+s+k]; print("  %-28s"%k, " ".join("%s D=%+.4f"%(w,r[w]["delta"]) for w in ["2024","2025","2026->cut","2024->26"] if w in r))
    for w in ["2024","2025","2026->cut","2024->26","full->cut"]:
        ic=out["s"+s]["IC__UCRYPTO_minus_UPIT"].get(w); la=out["s"+s]["LA__UFROZEN_minus_UCRYPTO"].get(w); gp=out["s"+s]["GAP__UFROZEN_minus_UPIT"].get(w)
        if ic and la and gp:
            share=100*ic["delta"]/gp["delta"] if gp["delta"]!=0 else float("nan")
            print("     ADDITIVITY %-10s IC %+.4f + LA %+.4f = %+.4f  vs GAP %+.4f  (resid %+.2e)  IC share of GAP = %.1f%%"%(w,ic["delta"],la["delta"],ic["delta"]+la["delta"],gp["delta"],ic["delta"]+la["delta"]-gp["delta"],share))
