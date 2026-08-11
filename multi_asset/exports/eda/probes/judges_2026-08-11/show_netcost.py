import json
d = json.load(open("multi_asset/exports/eda/qim_verdict_audit_raw.json"))
print("YEAR | grossSh | BE_full | net@0 | net@2.3 | net@5.0 | net@9.5 | turn | gross_bps | decMono | breadth | IC-IR")
for y, v in d["multiyear"].items():
    nc = v["netcost"]
    g0 = nc["netSharpe_full_c0.0"]; g23 = nc["netSharpe_full_c2.3"]
    g5 = nc["netSharpe_full_c5.0"]; g95 = nc["netSharpe_full_c9.5"]
    print("%s | %6.2f | %6.2f | %6.2f | %6.2f | %6.2f | %6.2f | %.2f | %.3f | %+.3f | %.0f | %.1f" % (
        y, nc["gross_sharpe"], nc["be_fullturn"], g0, g23, g5, g95,
        nc["turnover"], nc["gross_bps"], nc["decile_monotonicity"], nc["avg_breadth"],
        v["ens_resid_ic_ir"]))
    ba = nc["best_alpha"]
    a = ba["alpha"]
    print("     best-EMA a=%s BE=%.2f turn=%.2f net@2.3=%.2f net@5.0=%.2f net@9.5=%.2f | decile_bps=%s" % (
        a, ba["be"], ba["turnover"], ba["netSharpe_a%s_c2.3" % a], ba["netSharpe_a%s_c5.0" % a],
        ba["netSharpe_a%s_c9.5" % a], nc["decile_mean_bps"]))
