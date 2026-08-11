"""0C independent recompute of shadow paper P&L (verify arithmetic + cost/fill/regime application vs
pnl_summary.json). Reuses the live panel but re-implements the formula independently. Hand-prints 2-3
anchors. Writes /tmp/0c_pnl_check.json."""
import glob, json, sys, numpy as np, pandas as pd
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
from engine.panel_source import PanelSource
src = PanelSource(panel=MA + "/exports/live/wide_dl_live.npz", king=MA + "/exports/live/king_pred_live.npz",
                  s2=MA + "/exports/live/s2_pred_live.npz")
tj = {int(t): i for i, t in enumerate(src.ts)}; sym2j = {s: j for j, s in enumerate(src.symbols)}
FILL = 0.51; CC, CS, RVS = 1.9, 2.9, 18.0
files = sorted(glob.glob(MA + "/exports/live/positions/positions_*.json"))
rows = {"A": [], "B": []}; prev = {"A": np.zeros(src.N), "B": np.zeros(src.N)}
handchecks = []
for f in files:
    rec = json.load(open(f)); ti = tj.get(int(rec["anchor_ts_ms"]))
    if ti is None: continue
    ret = src.Y4[ti]
    if not np.isfinite(ret).any(): continue
    rvol = src.btc_rvol_bps_min(ti); cost = CS if (np.isfinite(rvol) and rvol > RVS) else CC
    d = pd.to_datetime(src.ts[ti], unit="ms", utc=True)
    for curve, key in (("A", "A_provisional_3leg"), ("B", "B_backfilled_4leg")):
        w = np.zeros(src.N)
        for s, wt in rec["curve"][key]["positions"].items():
            if s in sym2j: w[sym2j[s]] = wt
        ok = np.isfinite(ret); gross = float(np.nansum(w[ok] * ret[ok]))
        turn = float(np.abs(w - prev[curve]).sum()); prev[curve] = w
        net = FILL * (gross - turn * cost * 1e-4)
        rows[curve].append(dict(day=d.strftime("%Y-%m-%d"), gross=gross, turn=turn, cost=cost, net=net, rvol=float(rvol) if np.isfinite(rvol) else None))
        if curve == "A" and len(handchecks) < 3:
            handchecks.append(dict(anchor=d.isoformat(), curve="A", gross=round(gross,6), turnover=round(turn,4),
                                   cost_bps=cost, net_formula=f"0.51*({gross:.6f}-{turn:.4f}*{cost}*1e-4)", net=round(net,6)))
out = {}
for c in ("A", "B"):
    df = pd.DataFrame(rows[c]); dl = df.groupby("day").agg(net=("net","sum")).reset_index()
    out[c] = dict(n_anchors=len(df), cum_net=round(float(dl["net"].sum()),6), worst_day=round(float(dl["net"].min()),6),
                  stress_frac=round(float((df["cost"]==CS).mean()),3), max_btc_rvol=round(float(df["rvol"].dropna().max() if df["rvol"].notna().any() else 0),2))
out["handchecks"] = handchecks
print(json.dumps(out, indent=1))
json.dump(out, open("/tmp/0c_pnl_check.json","w"), indent=1)
print("\nvs summary: A cum 0.035548 worst -0.001196 | B cum 0.035252 worst -0.000774 | stress_frac 0.0")
