"""judge_additivity.py — 总效应与可加性(PREREG §5.2 B1 收尾)。
总 = M1_UPIT(FTRIM=zero) − NOFTRIM_MEM_UPIT(scope=members, FTRIM=off) = 在役两项(M1+FTRIM)相对全关基线。
部分之和 = [M1_UPIT − MEM_UPIT](M1) + [MEM_UPIT − NOFTRIM_MEM_UPIT](FTRIM 在窄秩基下)。
可加性残差 = 总 − 和 = 两项的交互。自举 UTC 日块 2000 种子 20260905。单位链由脚本打印。"""
import json,time,itertools
import numpy as np
H="/workspace/review_scratch/health_check"; ARM="d30_n2_c42"; NB=2000; SEED=20260905
def get(tag,cal,seed,cost):
    d="dev" if cal=="log" else "dev_alt"
    z=np.load(f"{H}/{d}/probe_artifacts/w10_ablation_series_{tag}_{cal}_s{seed}_{cost}.npz",allow_pickle=True)
    cols=[str(c) for c in z["cols"]]; R=z[f"{ARM}_rec"]
    return {c:R[:,i] for i,c in enumerate(cols)}
def boot(x,days,rng):
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    s=np.bincount(inv,weights=x,minlength=nd); c=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(NB,nd)); return s[idx].sum(1)/c[idx].sum(1)
print("=== 总效应(在役 M1+FTRIM vs 两者全关) 与 可加性")
print("%-16s %-10s %9s %20s %6s | %9s %9s %9s" % ("格","窗","总Δ","CI95","P>0","M1分量","FTRIM分量","交互残差"))
OUT={}
for cal,seed in itertools.product(("log","prod"),("42","2027")):
    L=get("M1_UPIT",cal,seed,"ccal"); M=get("MEM_UPIT",cal,seed,"ccal"); Z=get("NOFTRIM_MEM_UPIT",cal,seed,"ccal")
    ts=L["ts"].astype(np.int64)
    assert np.array_equal(ts,M["ts"].astype(np.int64)) and np.array_equal(ts,Z["ts"].astype(np.int64))
    yrs=np.array([time.gmtime(int(t)).tm_year for t in ts])
    days=np.array([time.strftime("%Y-%m-%d",time.gmtime(int(t))) for t in ts])
    tot=L["net_ex"]-Z["net_ex"]; p_m1=L["net_ex"]-M["net_ex"]; p_ft=M["net_ex"]-Z["net_ex"]
    resid=tot-(p_m1+p_ft)
    cell={}
    for wn,m in (("2024->26",yrs>=2024),("2025->26",yrs>=2025),("2024",yrs==2024),("2025",yrs==2025),("2026",yrs==2026)):
        if m.sum()<10: continue
        rng=np.random.default_rng(SEED); bs=boot(tot[m],days[m],rng)
        cell[wn]={"tot":round(float(tot[m].mean()),4),"lo":round(float(np.percentile(bs,2.5)),4),
                  "hi":round(float(np.percentile(bs,97.5)),4),"P>0":round(float((bs>0).mean()),4),
                  "m1":round(float(p_m1[m].mean()),4),"ftrim":round(float(p_ft[m].mean()),4),
                  "resid":round(float(resid[m].mean()),6)}
        if wn in ("2024->26","2025->26"):
            v=cell[wn]; print("%-16s %-10s %+9.4f [%+7.4f,%+7.4f] %6.3f | %+9.4f %+9.4f %+9.6f" % (f"{cal}/s{seed}",wn,v["tot"],v["lo"],v["hi"],v["P>0"],v["m1"],v["ftrim"],v["resid"]))
    ta=float(L["turnover"].mean()); tz=float(Z["turnover"].mean())
    cell["dturn_pct"]=round((ta/tz-1)*100,2)
    OUT[f"{cal}/s{seed}"]=cell
print()
for w in ("2024->26","2025->26","2024","2025","2026"):
    vs=[c[w]["tot"] for c in OUT.values() if w in c]; los=[c[w]["lo"] for c in OUT.values() if w in c]
    rs=[abs(c[w]["resid"]) for c in OUT.values() if w in c]
    print("  >> %-10s n=%d 正 %d/%d  CI下界>0 %d  范围 [%+.4f,%+.4f]  |交互| max %.2e" % (w,len(vs),sum(1 for v in vs if v>0),len(vs),sum(1 for l in los if l>0),min(vs),max(vs),max(rs)))
print("  >> 换手 Δ%%: %s" % [c["dturn_pct"] for c in OUT.values()])
print()
print("=== 单位链(脚本打印): bps/锚 每 NAV @回放 gross -> %/年")
g=float(np.mean(get("M1_UPIT","log","42","ccal")["gross_total"]))
print("  回放 gross_total 均值 = %.4f" % g)
for w in ("2024->26","2025->26"):
    vs=[c[w]["tot"] for c in OUT.values()]
    lo,hi=min(vs),max(vs)
    print("  %s 总Δ %.4f~%.4f bps/锚/NAV  x2190/100 = %.3f~%.3f %%/年(回放 gross)  ; 折到 2x gross 约 x%.2f = %.2f~%.2f %%NAV/年" % (w,lo,hi,lo*2190/100,hi*2190/100,2/g,lo*2190/100*2/g,hi*2190/100*2/g))
json.dump(OUT,open(f"{H}/judge_additivity.json","w"),indent=1)
