"""judge_ftrim.py — FTRIM 孤立臂判官(PREREG_king_window_ftrim_cap_2026-09-07 §5.2 B1)。
Δ = M1_UPIT(FTRIM=zero, 在役) − NOFTRIM_M1_UPIT(FTRIM=off)。Δ>0 表示 FTRIM 有帮助。
臂 d30_n2_c42, 列 net_ex(bps/锚 每 NAV, 执行器口径); 锚按 ts 配对并断言集合相同。
自举: UTC 日历日块, 2000 次有放回, 种子 20260905, CI95 = 2.5/97.5 分位。
窗: 2024 | 2025 | 2026 | 2024->26 | 2025->26。不设录取门(功效补全)。"""
import json, glob, time, hashlib, os
import numpy as np
H="/workspace/review_scratch/health_check"; ARM="d30_n2_c42"; NB=2000; SEED=20260905
def load(tag, cal):
    d = "dev" if cal=="log" else "dev_alt"
    p = f"{H}/{d}/probe_artifacts/w10_ablation_series_{tag}.npz"
    z = np.load(p, allow_pickle=True); cols=[str(c) for c in z["cols"]]; R=z[f"{ARM}_rec"]
    cfg = json.loads(str(z["config_json"]))
    return {c: R[:,i] for i,c in enumerate(cols)}, cfg, hashlib.sha256(open(p,"rb").read()).hexdigest()[:16]
def boot(x, days, rng):
    ud, inv = np.unique(days, return_inverse=True); nd=len(ud)
    s=np.bincount(inv, weights=x, minlength=nd); c=np.bincount(inv, minlength=nd)
    idx=rng.integers(0,nd,size=(NB,nd)); return s[idx].sum(1)/c[idx].sum(1)
OUT={"judge":"judge_ftrim.py","arm":ARM,"NB":NB,"seed":SEED,"delta":"M1_UPIT(FTRIM=zero) - NOFTRIM(FTRIM=off)","cells":{}}
rows=[]
for cal in ("log","prod"):
    for seed in ("42","2027"):
        for cost in ("ccal","cdef"):
            a=f"M1_UPIT_{cal}_s{seed}_{cost}"; b=f"NOFTRIM_M1_UPIT_{cal}_s{seed}_{cost}"
            try: A,ca,sa=load(a,cal); B,cb,sb=load(b,cal)
            except FileNotFoundError as e: print("SKIP",a,e); continue
            assert np.array_equal(A["ts"].astype(np.int64),B["ts"].astype(np.int64)), ("ts mismatch",a)
            assert ca.get("FTRIM")=="zero" and cb.get("FTRIM","off")=="off", (ca.get("FTRIM"),cb.get("FTRIM"))
            for k in ("UMASK_SCOPE","MEMBERS_TOPN","PHI","LOOK","WRULE","LEGS","FSEED"):
                assert ca.get(k)==cb.get(k), (k,ca.get(k),cb.get(k))
            ts=A["ts"].astype(np.int64); yrs=np.array([time.gmtime(int(t)).tm_year for t in ts])
            days=np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in ts])
            d=A["net_ex"]-B["net_ex"]
            rng=np.random.default_rng(SEED)
            cell={}
            for wname, m in (("2024",yrs==2024),("2025",yrs==2025),("2026",yrs==2026),
                             ("2024->26",yrs>=2024),("2025->26",yrs>=2025)):
                if m.sum()<10: continue
                bs=boot(d[m],days[m],rng)
                cell[wname]={"n":int(m.sum()),"mean":round(float(d[m].mean()),4),
                             "lo":round(float(np.percentile(bs,2.5)),4),"hi":round(float(np.percentile(bs,97.5)),4),
                             "P>0":round(float((bs>0).mean()),4)}
            ta=float(A["turnover"].mean()); tb=float(B["turnover"].mean())
            cell["turnover"]={"ftrim_on":round(ta,5),"ftrim_off":round(tb,5),"dpct":round((ta/tb-1)*100,2)}
            cell["shas"]={"on":sa,"off":sb}
            OUT["cells"][f"{cal}/s{seed}/{cost}"]=cell
            rows.append((f"{cal}/s{seed}/{cost}",cell))
json.dump(OUT, open(f"{H}/judge_ftrim.json","w"), indent=1)
print("=== FTRIM 孤立效应  Δ = 有FTRIM − 无FTRIM  (bps/锚 每 NAV; Δ>0 = FTRIM 有帮助)")
print("%-20s %-10s %8s %20s %7s" % ("格","窗","dmean","CI95","P>0"))
for k,c in rows:
    for w in ("2024->26","2025->26","2024","2025","2026"):
        if w not in c: continue
        v=c[w]; print("%-20s %-10s %+8.4f [%+7.4f,%+7.4f] %7.3f" % (k,w,v["mean"],v["lo"],v["hi"],v["P>0"]))
    print("%-20s %-10s turnover on %.5f / off %.5f  d%%=%+.2f" % ("","",c["turnover"]["ftrim_on"],c["turnover"]["ftrim_off"],c["turnover"]["dpct"]))
