#!/usr/bin/env python3
"""dl_recipe_tail.py — read-only: apply the giveback_diag tail metric (2× UTC-day compounding, days ≤ −2.68%/−4%, maxDD,
worst month, worst 3/6-anchor window) to the DL retrain-recipe arms, so recipe changes sit in the same table as the tail levers.
Arms + artifact paths + shas are taken verbatim from pretrain/results/judge_gate_addendum5.json (no path invention).
Units chain (E-0904-G): g = net_ex/gross_total [bps/anchor per unit gross]; NAV at 2×: r = 2g/1e4; UTC-day compounding."""
import json, time, calendar, hashlib, sys
import numpy as np
J = "/workspace/review_scratch/allweather_trackB/pretrain/results/judge_gate_addendum5.json"
L, THR1, THR2, APY = 2.0, -0.0268, -0.04, 2190
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {k: i for i, k in enumerate(COLS)}
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20*3600
WIN = {"2025-01->08-30": (T("2025-01-01"), 2**40), "FROZEN 2025-03->cut": (T("2025-03-01"), CUT+1), "2024->26": (T("2024-01-01"), 2**40)}
def r4(v): return None if v is None or (isinstance(v,float) and not np.isfinite(v)) else round(float(v), 4)
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def sharpe(x): return float(x.mean()/x.std(ddof=1)*np.sqrt(APY)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def daily(g, ts):
    r = L*g/1e4; days = ts//86400; ud, inv = np.unique(days, return_inverse=True); dl = np.bincount(inv, np.log1p(r)); return ud, np.expm1(dl)
def metrics(g, ts):
    out = {}
    for wn, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi); gw, tw = g[m], ts[m]
        if m.sum() < 12: out[wn] = {"n": int(m.sum())}; continue
        r = L*gw/1e4; nav = np.cumprod(1+r); dd = float((1 - nav/np.maximum.accumulate(nav)).max()*100)
        ud, dr = daily(gw, tw)
        months = np.array([time.gmtime(int(d*86400)).tm_year*100 + time.gmtime(int(d*86400)).tm_mon for d in ud]); um = np.unique(months)
        mret = np.array([np.expm1(np.log1p(dr[months == mm]).sum()) for mm in um])
        k3 = np.expm1(np.convolve(np.log1p(r), np.ones(3), "valid")); k6 = np.expm1(np.convolve(np.log1p(r), np.ones(6), "valid"))
        out[wn] = {"n": int(m.sum()), "n_days": int(len(ud)), "mean_bps_gross": r4(gw.mean()), "sharpe": r4(sharpe(gw)),
                   "maxdd_pct_2x": r4(dd), "worst_month_pct_2x": r4(mret.min()*100), "worst_month": str(int(um[np.argmin(mret)])),
                   "days_le_268": int((dr <= THR1).sum()), "days_le_400": int((dr <= THR2).sum()), "days_le_200": int((dr <= -0.02).sum()),
                   "worst_day_pct_2x": r4(dr.min()*100), "worst3_pct_2x": r4(k3.min()*100), "worst3_end": iso(tw[int(np.argmin(k3))+2]),
                   "worst6_pct_2x": r4(k6.min()*100), "anchors_le_40bps": int((gw <= -40).sum()), "turn_per_gross": r4(float(np.mean(gw*0 + (tw*0))) ) }
        out[wn]["turn_per_gross"] = None
    return out
D = json.load(open(J)); arms = D["arms"]
res = {"source_judge": J, "units": "g = net_ex/gross_total bps/anchor per gross; 2x NAV r = 2g/1e4; UTC-day compounding; thresholds -2.68%/-4.0%", "arms": {}}
for name, meta in arms.items():
    p = meta["artifact"]
    try: z = np.load(p, allow_pickle=True)
    except Exception as e: res["arms"][name] = {"error": str(e)[:120]}; continue
    assert [str(c) for c in z["cols"]] == COLS, (name, "cols differ")
    sha = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    assert sha == meta["sha256_16"], (name, sha, meta["sha256_16"])
    R = np.asarray(z["d30_n2_c42_rec"], float); ts = R[:, C["ts"]].astype(np.int64)
    g = R[:, C["net_ex"]]/R[:, C["gross_total"]]; turn = R[:, C["turnover"]]/R[:, C["gross_total"]]
    met = metrics(g, ts)
    for wn, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi)
        if m.sum() >= 12: met[wn]["turn_per_gross"] = r4(float(turn[m].mean()))
    res["arms"][name] = {"artifact": p, "sha16": sha, "metrics": met}
json.dump(res, open("/workspace/review_scratch/allweather_trackB/pretrain/results/dl_recipe_tail.json", "w"), indent=1, default=float)
order = ["R0_s42","CONST42","yearly_s42","FLOOR5","P0e10","P0e3","P0e1","P0e0","W1","W2","yearly_s2027"]
hdr = "| arm | mean g | Sharpe | maxDD 2× | worst month | days ≤−2.68% | ≤−4% | ≤−2% | worst day | worst 3-anchor | anchors ≤−40 bps | turn/gross |"
for wn in WIN:
    print(f"\n### {wn}"); print(hdr); print("|" + "---|"*12)
    for k in order + [a for a in res["arms"] if a not in order]:
        v = res["arms"].get(k)
        if not v or "metrics" not in v or wn not in v["metrics"] or "sharpe" not in v["metrics"][wn]: continue
        m = v["metrics"][wn]
        print(f"| {k} | {m['mean_bps_gross']:+.3f} | {m['sharpe']:.2f} | {m['maxdd_pct_2x']:.1f}% | {m['worst_month_pct_2x']:+.1f}% ({m['worst_month']}) | {m['days_le_268']} | {m['days_le_400']} | {m['days_le_200']} | {m['worst_day_pct_2x']:+.2f}% | {m['worst3_pct_2x']:+.2f}% | {m['anchors_le_40bps']} | {m['turn_per_gross']:.5f} |")
print("\nDL_RECIPE_TAIL_DONE")
