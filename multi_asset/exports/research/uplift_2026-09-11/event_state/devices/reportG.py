import json,numpy as np
J=json.load(open("/workspace/uplift_2026-09-11/event_state/JUDGE_G.json"))
b=J["baseline"]
print("=== A0 (GATE P artifact, v4, dyn s42) ===")
for w in ["full","frozen","2024on","ext","2022","2023","2024","2025","2026"]:
    s=b.get(w)
    if s: print("  %-8s n=%5d mean %+.3f Sh %+.2f+-%.2f dd %7.1f turn %.4f cost %+.3f carry %+.3f pnl %+.3f"%(w,s["n"],s["mean"],s["sharpe"],s["se_sharpe"],s["maxdd"],s["turnover"],s["cost_bps"],s["carry_bps"],s["pnl_bps"]))
print("  full CI95",[round(x,3) for x in b["full_ci"]])
rows=[]
for tag,e in J["arms"].items():
    f=e.get("full")
    if not f: continue
    yrs=[(e.get(y) or {}).get("mean") for y in ["2022","2023","2024","2025","2026"]]
    npos=sum(1 for v in yrs if v is not None and v>0)
    rows.append((tag,f,npos,e,yrs))
rows.sort(key=lambda r:-r[1]["sharpe"])
print("\n=== arms sorted by full-cycle Sharpe  (K=%d, Bonf alpha=%.4f%%) ==="%(J["meta"]["K"],J["meta"]["bonf_alpha_pct"]))
h="%-28s %7s %6s %4s %7s %7s %7s %18s %18s %6s %6s %7s %7s"
print(h%("arm","mean","Sh","yr+","corrFZ","corr24","corrFUL","CI95_full","BONF_full","turn","cost","carry/n","blend50"))
for tag,f,npos,e,yrs in rows:
    ci="[%+.3f,%+.3f]"%tuple(e["full_ci"]); bf="[%+.3f,%+.3f]"%tuple(e["full_bonf"])
    cf=e["carry_fraction_of_net"]
    bl=(e["blend50"].get("full") or {}).get("sharpe")
    print(h%(tag,"%+.3f"%f["mean"],"%+.2f"%f["sharpe"],npos,"%+.3f"%(e["corr_frozen"] or 0),"%+.3f"%(e["corr_2024on"] or 0),"%+.3f"%(e["corr_full"] or 0),ci,bf,"%.4f"%f["turnover"],"%+.3f"%f["cost_bps"],("%+.2f"%cf if cf is not None else "na"),("%+.2f"%bl if bl is not None else "na")))
print("\n=== yearly + frozen + ext for arms with full Sharpe > 0.6 ===")
print("%-28s %7s %7s %7s %7s %7s | %8s %8s"%("arm","2022","2023","2024","2025","2026","frozen","ext"))
for tag,f,npos,e,yrs in rows:
    if f["sharpe"]>0.6:
        y=" ".join("%+7.3f"%(v if v is not None else float("nan")) for v in yrs)
        fr=e.get("frozen"); ex=e.get("ext")
        print("%-28s %s | %+.3f/%+.2f %+.3f/%+.2f"%(tag,y,fr["mean"],fr["sharpe"],ex["mean"],ex["sharpe"]))
print("\nanchor axis == A0 frozen axis for every arm:",all(e["anchor_axis_equals_A0_frozen"] for _,_,_,e,_ in rows))
