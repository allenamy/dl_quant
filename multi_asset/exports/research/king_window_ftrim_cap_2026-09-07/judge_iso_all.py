"""judge_iso_all.py — M1 / T400 / FTRIM 孤立效应总判官(PREREG_king_window_ftrim_cap_2026-09-07 §5.2 B1 功效补全)。
scope 语义(装置 w10_health.py L50): members = 掩码缩小成员集(秩基 AND 交易集); m1 = 在役 M1(fund z 在 829 基内取秩, 其余腿与交易集在宇宙内); trade = 掩码只限交易集(秩基保持 829)。
配对: M1孤立 = M1_UPIT − MEM_UPIT | 全腿变宽 = UPIT − MEM_UPIT | 超出fund的额外变宽 = UPIT − M1_UPIT | T400孤立 = T400_M1_UPIT − M1_UPIT | FTRIM孤立 = M1_UPIT − NOFTRIM_M1_UPIT
臂 d30_n2_c42, 列 net_ex; 锚按 ts 断言相同; 自举 UTC 日块 2000 种子 20260905。不设录取门。
三项分解: Δnet = Δpnl − Δcarry − Δcost, 恒等逐锚断言。"""
import json, time, itertools
import numpy as np
H="/workspace/review_scratch/health_check"; ARM="d30_n2_c42"; NB=2000; SEED=20260905
def load(tag,cal):
    d="dev" if cal=="log" else "dev_alt"
    z=np.load(f"{H}/{d}/probe_artifacts/w10_ablation_series_{tag}_{cal}_s{{seed}}_{{cost}}.npz".format(),allow_pickle=True)
    return z
def get(tag,cal,seed,cost):
    d="dev" if cal=="log" else "dev_alt"
    p=f"{H}/{d}/probe_artifacts/w10_ablation_series_{tag}_{cal}_s{seed}_{cost}.npz"
    z=np.load(p,allow_pickle=True); cols=[str(c) for c in z["cols"]]; R=z[f"{ARM}_rec"]
    cfg=json.loads(str(z["config_json"]))
    return {c:R[:,i] for i,c in enumerate(cols)}, cfg
def boot(x,days,rng):
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    s=np.bincount(inv,weights=x,minlength=nd); c=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(NB,nd)); return s[idx].sum(1)/c[idx].sum(1)
PAIRS=[("M1 孤立(fund 秩基→829)","M1_UPIT","MEM_UPIT"),
       ("全腿变宽","UPIT","MEM_UPIT"),
       ("超出 fund 的额外变宽","UPIT","M1_UPIT"),
       ("T400 孤立","T400_M1_UPIT","M1_UPIT"),
       ("FTRIM 孤立","M1_UPIT","NOFTRIM_M1_UPIT")]
OUT={"judge":"judge_iso_all.py","arm":ARM,"NB":NB,"seed":SEED,"pairs":{}}
print("=== 孤立效应 Δ = x − ref (bps/锚 每 NAV; Δ>0 表示该项有帮助)")
for label,x,ref in PAIRS:
    print("\n" + "="*96); print(f"### {label}   [{x}] − [{ref}]")
    print("%-16s %-10s %9s %20s %6s | %9s %9s %9s" % ("格","窗","dnet","CI95","P>0","dpnl","dcarry","dcost"))
    cells={}
    for cal,seed,cost in itertools.product(("log","prod"),("42","2027"),("ccal","cdef")):
        try: A,ca=get(x,cal,seed,cost); B,cb=get(ref,cal,seed,cost)
        except FileNotFoundError: continue
        ts=A["ts"].astype(np.int64); assert np.array_equal(ts,B["ts"].astype(np.int64))
        for X in (A,B):
            assert np.abs(X["net_ex"]-(X["pnl_ex"]-X["carry_ex"]-X["cost_ex"])).max()<1e-6
        yrs=np.array([time.gmtime(int(t)).tm_year for t in ts])
        days=np.array([time.strftime("%Y-%m-%d",time.gmtime(int(t))) for t in ts])
        dn=A["net_ex"]-B["net_ex"]; dp=A["pnl_ex"]-B["pnl_ex"]; dc=A["carry_ex"]-B["carry_ex"]; dk=A["cost_ex"]-B["cost_ex"]
        cell={}
        for wn,m in (("2024->26",yrs>=2024),("2025->26",yrs>=2025),("2024",yrs==2024),("2025",yrs==2025),("2026",yrs==2026)):
            if m.sum()<10: continue
            rng=np.random.default_rng(SEED); bs=boot(dn[m],days[m],rng)
            cell[wn]={"n":int(m.sum()),"dnet":round(float(dn[m].mean()),4),
                      "lo":round(float(np.percentile(bs,2.5)),4),"hi":round(float(np.percentile(bs,97.5)),4),
                      "P>0":round(float((bs>0).mean()),4),
                      "dpnl":round(float(dp[m].mean()),4),"dcarry":round(float(dc[m].mean()),4),"dcost":round(float(dk[m].mean()),4)}
        ta=float(A["turnover"].mean()); tb=float(B["turnover"].mean())
        cell["dturn_pct"]=round((ta/tb-1)*100,2)
        cells[f"{cal}/s{seed}/{cost}"]=cell
        for wn in ("2024->26","2025->26"):
            if wn not in cell: continue
            v=cell[wn]; print("%-16s %-10s %+9.4f [%+7.4f,%+7.4f] %6.3f | %+9.4f %+9.4f %+9.4f" % (f"{cal}/s{seed}/{cost}",wn,v["dnet"],v["lo"],v["hi"],v["P>0"],v["dpnl"],v["dcarry"],v["dcost"]))
    OUT["pairs"][label]={"x":x,"ref":ref,"cells":cells}
    # 汇总: 主窗八格符号与显著性
    for wn in ("2024->26","2025->26"):
        vs=[c[wn]["dnet"] for c in cells.values() if wn in c]
        los=[c[wn]["lo"] for c in cells.values() if wn in c]; his=[c[wn]["hi"] for c in cells.values() if wn in c]
        if not vs: continue
        npos=sum(1 for v in vs if v>0); sig_pos=sum(1 for l in los if l>0); sig_neg=sum(1 for h in his if h<0)
        print("  >> %s: n=%d 格, 正 %d/%d, CI下界>0 的 %d 格, CI上界<0 的 %d 格, Δ 范围 [%+.4f, %+.4f]" % (wn,len(vs),npos,len(vs),sig_pos,sig_neg,min(vs),max(vs)))
    dts=[c["dturn_pct"] for c in cells.values()]
    if dts: print("  >> 换手 Δ%%: %+.2f ~ %+.2f" % (min(dts),max(dts)))
json.dump(OUT,open(f"{H}/judge_iso_all.json","w"),indent=1)
print("\nSAVED judge_iso_all.json")
