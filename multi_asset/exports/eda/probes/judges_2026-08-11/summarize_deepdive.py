import json, numpy as np
EDA = "multi_asset/exports/eda/"

# Part 2: bar regime — fill invariance + spread widening by BTC rvol regime
br = json.load(open(EDA + "bar_regime_raw.json"))
rows = []
for day, d in br["per_day"].items():
    rv = d["btc_rvol_bps_min"]; pc = d["per_coin"]
    # cross-liquidity fill spread at f=1%,k300: coefficient of variation across coins
    fills = [pc[c]["fill_rate"]["300"]["0.01"] for c in pc]
    sprs = [pc[c]["spread_bps"] for c in pc]
    rows.append((day, rv, np.mean(fills), np.std(fills), np.median(sprs)))
rows.sort(key=lambda x: x[1])
print("=== bar regime (sorted by BTC rvol) — fill invariance + spread ===")
print("day       rvol  meanFill  fillStd(x-coin)  medSpread")
for day, rv, mf, sf, ms in rows:
    print("%s  %5.1f   %.2f      %.3f          %.3f" % (day, rv, mf, sf, ms))
# regime buckets
calm = [r for r in rows if r[1] < 7]; norm = [r for r in rows if 7 <= r[1] < 18]; stress = [r for r in rows if r[1] >= 18]
for nm, b in [("calm", calm), ("normal", norm), ("stress", stress)]:
    if b:
        print("%s: n=%d meanFill %.2f fillStd(x-coin) %.3f medSpread %.3f" % (
            nm, len(b), np.mean([x[2] for x in b]), np.mean([x[3] for x in b]), np.mean([x[4] for x in b])))

# tick markout by regime
tk = json.load(open(EDA + "tick_vs_1s_raw.json"))
print("\n=== tick markout by regime (BTC) ===")
mrows = []
for day in tk["days"]:
    t = tk["per_day"][day]["tick"]
    if t:
        mrows.append((day, t["rvol_bps_min"], t["markout_mean"], t["markout_p25"], t["fill_rate"]["300"]["0.01"]))
mrows.sort(key=lambda x: x[1])
for day, rv, mk, p25, fl in mrows:
    print("%s rvol %5.1f  mk %+.2f  p25 %+.1f  fill %.2f" % (day, rv, mk, p25, fl))
calm = [r for r in mrows if r[1] < 7]; norm = [r for r in mrows if 7 <= r[1] < 18]; stress = [r for r in mrows if r[1] >= 18]
for nm, b in [("calm", calm), ("normal", norm), ("stress", stress)]:
    if b:
        print("%s: n=%d markout %.2f p25 %.1f fill %.2f" % (nm, len(b), np.mean([x[2] for x in b]), np.mean([x[3] for x in b]), np.mean([x[4] for x in b])))

# $5M tick-corrected
tc = json.load(open(EDA + "tickcorrected_apply_raw.json"))
print("\n=== tick-corrected $5M ===")
yrs = ["2022", "2023", "2024", "2025", "2026"]
for tag, r in tc["scenarios"].items():
    if "AUM5M" in tag and ("_calib" in tag or "_full" in tag) and "k900" not in tag:
        print("%s: net %s cost24 %s fill24 %s" % (tag, [r.get(y, {}).get("net_sh") for y in yrs],
              r.get("2024", {}).get("eff_cost_bps"), r.get("2024", {}).get("fill")))
