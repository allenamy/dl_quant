import json
d = json.load(open("multi_asset/exports/eda/makerfill_calib_raw.json"))
pc = d["per_coin"]
fg = [str(x) for x in d["fgrid"]]
print("fill-rate vs f (order/hourly-notl) at k=300s:")
print("coin  hrN_M  " + " ".join("%6s" % f for f in fg))
for s in sorted(pc, key=lambda x: -pc[x]["hourly_notl_usd"]):
    fr = pc[s]["fill_rate"]["300"]
    print("%5s %6.1f " % (s, pc[s]["hourly_notl_usd"] / 1e6) + " ".join("%6.2f" % fr[f] for f in fg))
print("\neff-maker-cost-if-filled (=-markout-half_spread, NEG=profit) + taker(=half+1.5):")
for s in sorted(pc, key=lambda x: -pc[x]["hourly_notl_usd"]):
    c = pc[s]; eff = -c["markout_mean_bps"] - c["half_spread_bps"]; tk = c["half_spread_bps"] + 1.5
    print("%5s hrN %6.1fM mk %+.3f half %.3f eff_if_fill %+.3f taker %.2f" % (
        s, c["hourly_notl_usd"] / 1e6, c["markout_mean_bps"], c["half_spread_bps"], eff, tk))
# fill vs k for a small coin at f=5%
print("\nfill-rate vs k at f=0.05 (5% of hourly):")
for s in ["btc", "sol", "ltc", "fil", "etc", "trx"]:
    print("%5s " % s + " ".join("k%s=%.2f" % (k, pc[s]["fill_rate"][k]["0.05"]) for k in ["60", "300", "900"]))
