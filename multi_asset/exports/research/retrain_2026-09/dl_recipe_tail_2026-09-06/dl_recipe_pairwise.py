#!/usr/bin/env python3
"""dl_recipe_pairwise.py — read-only: pairwise Δ among the leading DL recipe arms ("which recipe is best?").
POST-HOC pairings (the frozen gates were vs yearly_s42 / vs CONST42 / vs P0e0), labelled as such. Same device and
bootstrap as the judges: paired by anchor, UTC-day-block bootstrap 2000, seed 20260905; g = net_ex/gross_total."""
import json, time, calendar, hashlib
import numpy as np
J = "/workspace/review_scratch/allweather_trackB/pretrain/results/judge_gate_addendum5.json"
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {k: i for i, k in enumerate(COLS)}; NB, SEED = 2000, 20260905
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20*3600
WIN = {"FROZEN 2025-03->cut": (T("2025-03-01"), CUT+1), "FULL 2025-01->cut": (T("2025-01-01"), CUT+1)}
def load(p, sha_exp):
    z = np.load(p, allow_pickle=True); assert [str(c) for c in z["cols"]] == COLS
    assert hashlib.sha256(open(p, "rb").read()).hexdigest()[:16] == sha_exp
    R = np.asarray(z["d30_n2_c42_rec"], float)
    return R[:, C["ts"]].astype(np.int64), R[:, C["net_ex"]]/R[:, C["gross_total"]]
def boot(d, ts):
    days = ts//86400; ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    s1 = np.bincount(inv, d); c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(SEED); ii = rng.integers(0, nd, size=(NB, nd)); m = s1[ii].sum(1)/c[ii].sum(1)
    return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)), float((m > 0).mean())
D = json.load(open(J)); arms = D["arms"]; G = {}
for n in ("W2","W1","FLOOR5","P0e0","P0e1","yearly_s42","CONST42"):
    if n in arms: G[n] = load(arms[n]["artifact"], arms[n]["sha256_16"])
PAIRS = [("W2","W1"),("W2","FLOOR5"),("W2","P0e0"),("W1","FLOOR5"),("P0e0","FLOOR5"),("P0e0","P0e1"),("FLOOR5","yearly_s42")]
out = {"caveat": "POST-HOC pairwise comparisons among leading arms; frozen gates were vs yearly_s42/CONST42/P0e0. Single seed 42.", "pairs": {}}
print("| pair | window | Δg [CI95] P(Δ>0) |"); print("|---|---|---|")
for a, b in PAIRS:
    if a not in G or b not in G: continue
    ts, ga = G[a]; tsb, gb = G[b]; assert np.array_equal(ts, tsb)
    out["pairs"][f"{a} − {b}"] = {}
    for wn, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi)
        mu, l, h, p = boot((ga-gb)[m], ts[m])
        out["pairs"][f"{a} − {b}"][wn] = {"delta": mu, "ci": [l, h], "p_gt0": p}
        print(f"| {a} − {b} | {wn} | {mu:+.3f} [{l:+.3f}, {h:+.3f}] P{p:.2f} |")
json.dump(out, open("/workspace/review_scratch/allweather_trackB/pretrain/results/dl_recipe_pairwise.json", "w"), indent=1, default=float)
print("\nPAIRWISE_DONE")
