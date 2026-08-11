"""M0 seed-stability: 3 seeds (orig + s43 + s44). Per-seed standalone rank-IC on funding's ≥3600 CL,
cross-seed pred corr (same signal?), per-seed funding+M0 blend net-Sh + seed-median. Closes the single-seed limit."""
import sys, numpy as np
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset"; sys.path.insert(0, MA)
from multi_asset.eval.portfolio_scorecard import load_panel, blend, book_stats, _zc
from multi_asset.eval.factor_scorer import factor_corr, _perts_ic

TR = MA+"/multi_asset/exports/train"
F = load_panel("fund_ema_h3600", TR)
Y, CL, ts, day = F["Y"], F["CL"], F["ts"].astype(np.int64), F["day"].astype(np.int64)
funding = F["pred"]
seeds = {"orig": "fund_resid_h3600", "s43": "fund_resid_h3600_s43", "s44": "fund_resid_h3600_s44"}
M = {k: load_panel(v, TR)["pred"] for k, v in seeds.items()}

print("=== (1) per-seed standalone rank-IC on funding ≥3600 CL (orig ref +0.0355) ===")
ics = {}
for k in seeds:
    ic, _ = _perts_ic(M[k], Y, CL); ics[k] = float(ic.mean())
    print(f"  {k}: rank-IC {ic.mean():+.4f} (n {len(ic)})")
print(f"  seed IC: mean {np.mean(list(ics.values())):+.4f}  std {np.std(list(ics.values())):.4f}  "
      f"range [{min(ics.values()):+.4f}, {max(ics.values()):+.4f}]")

print("\n=== (2) cross-seed pred correlation (same signal?) ===")
ks = list(seeds)
for i in range(len(ks)):
    for j in range(i+1, len(ks)):
        print(f"  corr({ks[i]},{ks[j]}) = {factor_corr(M[ks[i]], M[ks[j]], CL)}")

print("\n=== (3) per-seed funding+M0 blend net-Sharpe (equal-risk) ===")
netsh = {}
for k in seeds:
    comb = blend([funding, M[k]], Y, CL)
    st = book_stats(comb, Y, CL, ts, day, 3600, cost_bps=2.0)
    netsh[k] = st["net_sh_c2"]
    print(f"  {k}: blend net-Sh@2bps {st['net_sh_c2']} | BE {st['be']} | @5/@10 {st['net_sh_grid'][5.0]}/{st['net_sh_grid'][10.0]} | per-fold {st['per_fold_net_sh']}")
vals = list(netsh.values())
print(f"  blend net-Sh@2bps: median {np.median(vals):.2f}  mean {np.mean(vals):.2f}  std {np.std(vals):.2f}  range [{min(vals):.2f}, {max(vals):.2f}]")
print("DONE")
