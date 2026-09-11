import json
r=json.load(open("/workspace/r9okx/RESULT_okxrho.json"))
print(json.dumps({k:r[k] for k in r if k!="arms"},indent=1))
hdr="ARM                  n   rho(A0 s42)        CI95              rho(A0 s2027)  |  rho in A0-loss (s42)     CI95            q20  | meang    CI95mean            SR      turn     cost    carry   gross"
print(hdr)
for tag in ["OKX","OKX_noFTRIM","OKX_SUP","BINCOLD_SUP","BINCOLD388","BINCOLD388_noFTRIM","BINWARM388","BINCOLD","BINCOLD_noFTRIM","BINWARM","BINPANEL","BINPANEL_noFTRIM"]:
    e=r["arms"].get(tag)
    if not e: continue
    a=e["A0_dyn_s42"]; b=e["A0_dyn_s2027"]; s=e["standalone"]
    print("{:18s} {:4d}  {:+.4f} [{:+.4f},{:+.4f}]  {:+.4f} | {:+.4f} [{:+.4f},{:+.4f}] {:+.4f} | {:+7.4f} [{:+7.4f},{:+7.4f}] {:+6.3f} {:.5f} {:.4f} {:+.4f} {:.4f}".format(
        tag,a["n"],a["pearson"],a["ci95"][0],a["ci95"][1],b["pearson"],
        a["pearson_in_A0_loss"],a["ci95_in_A0_loss"][0],a["ci95_in_A0_loss"][1],a["pearson_in_A0_worst_quintile"],
        s["mean_g"],s["ci95_mean_g"][0],s["ci95_mean_g"][1],s["sharpe_ann"],s["turnover_mean"],s["cost_ex_mean"],s["carry_ex_mean"],s["gross_total_mean"]))
print()
print("CROSS-ARM rho on the same 418 anchors")
for k,v in r.get("cross_arm_rho",{}).items():
    print("  {:28s} n={:4d} rho={:+.4f} CI95[{:+.4f},{:+.4f}]".format(k,v["n"],v["pearson"],v["ci95"][0],v["ci95"][1]))
