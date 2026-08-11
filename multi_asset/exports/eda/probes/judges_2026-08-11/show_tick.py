import json, numpy as np
d = json.load(open("multi_asset/exports/eda/tick_vs_1s_raw.json"))
fg = [str(x) for x in d["fgrid"]]
print("=== fill-rate tick(T) vs bar1s(B) at k=300 ===")
print("day        " + " ".join("f%s" % f for f in fg))
for day in d["days"]:
    t = d["per_day"][day]["tick"]; b = d["per_day"][day]["bar1s"]
    if not t or not b:
        continue
    print("%s T " % day + " ".join("%.2f" % t["fill_rate"]["300"][f] for f in fg))
    print("%s B " % day + " ".join("%.2f" % b["fill_rate"]["300"][f] for f in fg))
print("\n=== fill(f=1%) vs k, tick vs bar ===")
for day in d["days"]:
    t = d["per_day"][day]["tick"]; b = d["per_day"][day]["bar1s"]
    if not t:
        continue
    print("%s T " % day + " ".join("k%s=%.2f" % (k, t["fill_rate"][k]["0.01"]) for k in ["60", "300", "900"]) +
          " | B " + " ".join("k%s=%.2f" % (k, b["fill_rate"][k]["0.01"]) for k in ["60", "300", "900"]))
print("\n=== markout tick vs bar (bps, D=60s) + ratios ===")
frr = []; mkt = []; mkb = []
for day in d["days"]:
    t = d["per_day"][day]["tick"]; b = d["per_day"][day]["bar1s"]
    if not t:
        continue
    r = t["fill_rate"]["300"]["0.01"] / b["fill_rate"]["300"]["0.01"]
    frr.append(r); mkt.append(t["markout_mean"]); mkb.append(b["markout_mean"])
    print("%s  tick mk %+.3f (p25 %+.3f) | bar mk %+.3f | fill-ratio T/B %.2f | cancel-clear %.2f" % (
        day, t["markout_mean"], t["markout_p25"], b["markout_mean"], r, t["cancel_clear_frac"]))
print("\nMEAN fill-ratio T/B %.2f | tick markout %.2f (range %.2f..%.2f) | bar markout %.2f" % (
    np.mean(frr), np.mean(mkt), min(mkt), max(mkt), np.mean(mkb)))
