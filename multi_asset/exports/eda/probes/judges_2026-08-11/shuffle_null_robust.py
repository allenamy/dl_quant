"""Robust shuffle-null: 50 shuffles to get the TRUE null distribution + where real sits.
Distinguishes (a) weak/seed-fragile test [null mean ~0, big std] from (b) engine bias
[null mean systematically != 0]. Also reports whether real GROSS is distinguishable
from the shuffle band (economic: does the taker strategy carry real gross alpha?)."""
import sys, numpy as np
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.eval.taker_backtest import (load_preds, nonoverlap_grid, decision_center,
    calibrate_offtest, run_strategy, DAY)
df = load_preds("/mnt/storage/private/work_hsy/quant_research_multi_asset/exports/final_l01/y600_backtest_dataset.csv")
G = nonoverlap_grid(df); ts=G.ts.values.astype(np.int64); y=G.y.values; p=G.p.values; mon=G.month.values
W=12; day=ts//DAY
eh = calibrate_offtest(p-decision_center(p,W), y, mon)
real_gross = float(np.sum(run_strategy(eh,y,1.0,1.0,0.5,0.3,1)[1]*y))
real_net10 = float(np.sum(run_strategy(eh,y,1.0,1.0,0.5,0.3,1)[0]))

N=50; rng=np.random.default_rng(2024); gs=[]
for _ in range(N):
    ps=p.copy()
    for dd in np.unique(day):
        idx=np.where(day==dd)[0]; ps[idx]=p[idx][rng.permutation(len(idx))]
    ds=ps-decision_center(ps,W); ehs=calibrate_offtest(ds,y,mon)
    gs.append(float(np.sum(run_strategy(ehs,y,1.0,1.0,0.5,0.3,1)[1]*y)))
gs=np.array(gs)
mu,sd=gs.mean(),gs.std()
z=(real_gross-mu)/(sd+1e-9)
pct=float((gs<real_gross).mean())
print(f"REAL gross={real_gross:.1f} bps | net@cost1={real_net10:.1f} bps  (over {len(G)} periods)")
print(f"SHUFFLE null ({N}): mean={mu:.1f}  std={sd:.1f}  min={gs.min():.1f}  max={gs.max():.1f}")
print(f"  null mean ~0? |{mu:.1f}| vs std {sd:.1f} -> {'UNBIASED (engine clean)' if abs(mu)<0.5*sd else 'BIASED (investigate)'}")
print(f"  real vs null: z={z:.2f}  percentile={pct*100:.0f}%  -> real gross {'DISTINGUISHABLE' if abs(z)>2 else 'NOT distinguishable'} from shuffle noise")
print(f"NOTE for 0C: battery [2] uses 5 shuffles + a loose |mean|<0.5|real|+1 gate -> SEED-FRAGILE (my seed flipped it). Recommend {N}+ shuffles + z/percentile.")
