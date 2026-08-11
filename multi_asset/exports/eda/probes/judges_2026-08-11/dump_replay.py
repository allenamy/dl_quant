import json, sys
E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda"
d = json.load(open(E + "/megacap_funding_replay.json"))
for h in ["1h", "2h"]:
    print("--- %s ---" % h)
    yr = d[h]
    for y in sorted(yr):
        r = yr[y]
        print("  %s: IC=%+.4f z=%+.2f grossSh=%+.2f netSh=%+.2f BE=%.1f turn=%.3f n_ts=%s" % (
            y, r.get("ic",float("nan")), r.get("z",float("nan")), r.get("gross_sh",float("nan")),
            r.get("net_sh",float("nan")), r.get("be_bps",float("nan")), r.get("turnover",float("nan")), r.get("n_ts")))
