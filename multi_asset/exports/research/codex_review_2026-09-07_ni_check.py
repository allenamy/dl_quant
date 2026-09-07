import json,glob,os
# scan archived judge jsons for every "− yearly*" pair and apply a PROPER non-inferiority test at delta=0.05
# our rule: Delta >= -0.05 AND (CI contains 0 OR lower>0).  proper NI at margin d: CI lower > -d.
D="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/retrain_2026-09"
rows=[]
for p in glob.glob(D+"/**/*.json",recursive=True):
    try: J=json.load(open(p))
    except Exception: continue
    if not isinstance(J,dict) or "deltas" not in J: continue
    for name,d in J.get("deltas",{}).items():
        if "yearly" not in name: continue
        w=d.get("windows",{})
        for wn in ("FROZEN 2025-03->26<=cut",):
            b=w.get(wn)
            if not b: continue
            mu,lo,hi=b["mean"],b["lo"],b["hi"]
            ours = (mu>=-0.05) and ((lo<=0<=hi) or lo>0)
            ni   = lo > -0.05
            rows.append((os.path.basename(os.path.dirname(os.path.dirname(p))),name,mu,lo,hi,ours,ni))
seen=set(); out=[]
for r in rows:
    k=(r[1],round(r[2],6))
    if k in seen: continue
    seen.add(k); out.append(r)
print(f"{'pair':52s} {'Delta':>8s} {'CI lo':>8s} {'CI hi':>8s}  ourRule  NI@0.05")
n_ours=n_ni=0
for src,name,mu,lo,hi,ours,ni in sorted(out,key=lambda x:x[1]):
    n_ours+=ours; n_ni+=ni
    print(f"{name[:52]:52s} {mu:+8.3f} {lo:+8.3f} {hi:+8.3f}   {'PASS' if ours else 'fail':5s}   {'PASS' if ni else 'FAIL':5s}")
print(f"\n冻结窗 'not worse than yearly' 型对照 {len(out)} 个: 我方规则通过 {n_ours}; 真正非劣检验(δ=0.05, CI下界>−0.05)通过 {n_ni}")
