#!/usr/bin/env python3
"""dl_vs_live_recipe.py — read-only: paired Δ of each DL recipe arm against R0_s42 (= THE LIVE RECIPE: monthly full-history
refit, seed per fold, embargo 1 anchor). The frozen prereg gates compared arms to yearly/CONST; this pairing against the
live form is POST-HOC decision framing, labelled as such, not a gate. Same device/bootstrap as the judges: paired by anchor,
UTC-day-block bootstrap 2000, seed 20260905, g = net_ex/gross_total [bps/anchor per unit gross]."""
import json, time, calendar, hashlib
import numpy as np
J = "/workspace/review_scratch/allweather_trackB/pretrain/results/judge_gate_addendum5.json"
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {k: i for i, k in enumerate(COLS)}; NB, SEED, L = 2000, 20260905, 2.0
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20*3600
WIN = {"FROZEN 2025-03->cut": (T("2025-03-01"), CUT+1), "2025-01->08-30": (T("2025-01-01"), 2**40), "2025 full": (T("2025-01-01"), T("2026-01-01")), "2026<=cut": (T("2026-01-01"), CUT+1)}
def load(p, sha_exp):
    z = np.load(p, allow_pickle=True); assert [str(c) for c in z["cols"]] == COLS
    sha = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]; assert sha == sha_exp, (p, sha, sha_exp)
    R = np.asarray(z["d30_n2_c42_rec"], float)
    return R[:, C["ts"]].astype(np.int64), R[:, C["net_ex"]]/R[:, C["gross_total"]], R[:, C["turnover"]]/R[:, C["gross_total"]]
def boot(d, ts):
    days = ts//86400; ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    s1 = np.bincount(inv, d); c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(SEED); ii = rng.integers(0, nd, size=(NB, nd)); m = s1[ii].sum(1)/c[ii].sum(1)
    return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)), float((m > 0).mean())
D = json.load(open(J)); arms = D["arms"]
ts0, g0, t0 = load(arms["R0_s42"]["artifact"], arms["R0_s42"]["sha256_16"])
out = {"reference": "R0_s42 = live recipe (monthly full-history refit, seed per fold, embargo 1)", "caveat": "POST-HOC pairing vs the live form; the frozen gates were vs yearly_s42 and CONST42. Single seed 42 for W/P0 arms.", "pairs": {}}
names = ["yearly_s42","CONST42","FLOOR5","P0e0","P0e1","P0e3","P0e10","W1","W2"]
print("| arm − R0(live recipe) | window | Δg [CI95] P(Δ>0) | Δ NAV %/yr @2× | Δturn% |"); print("|---|---|---|---|---|")
for n in names:
    if n not in arms: continue
    ts1, g1, t1 = load(arms[n]["artifact"], arms[n]["sha256_16"]); assert np.array_equal(ts1, ts0), n
    out["pairs"][n] = {}
    for wn, (lo, hi) in WIN.items():
        m = (ts0 >= lo) & (ts0 < hi)
        if m.sum() < 12: continue
        mu, l, h, p = boot((g1-g0)[m], ts0[m]); dt = (t1[m].mean()/t0[m].mean()-1)*100
        nav = mu*L/1e4*2190*100
        out["pairs"][n][wn] = {"delta": mu, "ci": [l, h], "p_gt0": p, "nav_pct_yr_2x": nav, "turn_pct": dt}
        print(f"| {n} | {wn} | {mu:+.3f} [{l:+.3f}, {h:+.3f}] P{p:.2f} | {nav:+.1f}% | {dt:+.1f}% |")
json.dump(out, open("/workspace/review_scratch/allweather_trackB/pretrain/results/dl_vs_live_recipe.json", "w"), indent=1, default=float)
print("\nDL_VS_LIVE_DONE")
