import json, numpy as np
J=json.load(open("/workspace/uplift_2026-09-11/trackD_v4/JUDGE_trackD.json"))
b=J["baseline"]
print("=== A0 (in-service form, v4 caliber, dyn seat s42) ===")
for w in ["full","frozen","2024on","2022","2023","2024","2025","2026"]:
    s=b.get(w)
    if s: print(f"  {w:8s} n={s['n']:5d} mean {s['mean']:+.3f} Sh {s['sharpe']:+.2f}+-{s['se_sharpe']:.2f} dd {s['maxdd']:7.1f} turn {s['turnover']:.4f} cost {s['cost_bps']:+.3f} carry {s['carry_bps']:+.3f}")
print("  full CI", [round(x,3) for x in b["full_ci"]])
rows=[]
for tag,e in J["arms"].items():
    f=e.get("full"); fr=e.get("frozen")
    if not f: continue
    yrs=[e.get(y,{}).get("mean") if e.get(y) else None for y in ["2022","2023","2024","2025","2026"]]
    npos=sum(1 for v in yrs if v is not None and v>0)
    rows.append((tag,f["mean"],f["sharpe"],f["se_sharpe"],npos,e["corr_frozen"],e["corr_2024on"],
                 e["full_ci"],f["turnover"],f["cost_bps"],f["carry_bps"],
                 (fr["mean"] if fr else None),(fr["sharpe"] if fr else None),
                 e["blend50"].get("full",{}).get("sharpe"), yrs, e["anchor_axis_equals_A0_frozen"]))
rows.sort(key=lambda r:-r[2])
print("\n=== SLEEVE ARMS, sorted by full-cycle Sharpe (2022-01 -> 2026-08-10 20Z) ===")
print(f"{'arm':30s} {'mean':>7s} {'Sh':>6s} {'+-':>5s} {'yr+':>3s} {'corrFZ':>7s} {'corr24':>7s} {'CI95_full':>18s} {'turn':>6s} {'cost':>6s} {'carry':>6s} {'blend50Sh':>9s}")
for r in rows:
    ci=f"[{r[7][0]:+.3f},{r[7][1]:+.3f}]"
    print(f"{r[0]:30s} {r[1]:+7.3f} {r[2]:+6.2f} {r[3]:5.2f} {r[4]:3d} {r[5]:+7.3f} {r[6]:+7.3f} {ci:>18s} {r[8]:6.4f} {r[9]:+6.3f} {r[10]:+6.3f} {(r[13] if r[13] is not None else float('nan')):+9.2f}")
print("\n=== yearly means (bps/anchor/gross) for arms with full Sharpe > 0.8 ===")
print(f"{'arm':30s} {'2022':>7s} {'2023':>7s} {'2024':>7s} {'2025':>7s} {'2026':>7s}   frozen mean/Sh")
for r in rows:
    if r[2] > 0.8:
        y=" ".join(f"{(v if v is not None else float('nan')):+7.3f}" for v in r[14])
        print(f"{r[0]:30s} {y}   {r[11]:+.3f}/{r[12]:+.2f}")
axok=all(r[15] for r in rows)
print("\nanchor axis == A0 frozen axis for every arm:", axok)
