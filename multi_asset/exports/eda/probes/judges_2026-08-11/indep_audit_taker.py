"""INDEPENDENT audit of taker_backtest.py — re-derive the load-bearing properties
with my own probes (not 0C's battery), to catch a bug 0C's tests could mask.
Focus: (A) calibration is PAST-only not future-leaking (0C's probe under-covers this),
(B) cost side-counting on a hand-built flip path, (C) non-overlap spacing,
(D) oracle direction+cost, (E) shuffle-null. Imports 0C's FROZEN functions."""
import sys, numpy as np
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.eval.taker_backtest import (
    load_preds, nonoverlap_grid, decision_center, calibrate_offtest,
    run_strategy, _trans_cost, MONTHS, HZ, DAY)

df = load_preds("/mnt/storage/private/work_hsy/quant_research_multi_asset/exports/final_l01/y600_backtest_dataset.csv")
G = nonoverlap_grid(df); ts=G.ts.values.astype(np.int64); y=G.y.values; p=G.p.values; mon=G.month.values
W=12
d = p - decision_center(p, W)
eh = calibrate_offtest(d, y, mon)
print(f"grid {len(G)} periods, months present: {sorted(set(mon))}")

# (A) DIRECTIONAL CALIBRATION CAUSALITY — the key past-only test
print("\n(A) CALIBRATION IS PAST-ONLY (not future-leak):")
def corrupt_and_ehat(target_month):
    yc = y.copy(); yc[mon==target_month] = 0.0
    return calibrate_offtest(d, yc, mon)
# corrupt an EARLY month (2025_09) -> should NOT change its own ê, but SHOULD change a LATER month (2026_01)
ehA = corrupt_and_ehat("2025_09")
own_unchanged = np.allclose(eh[mon=="2025_09"], ehA[mon=="2025_09"])
later_changed = not np.allclose(eh[mon=="2026_01"], ehA[mon=="2026_01"])
# corrupt a LATE month (2026_04) -> should NOT change an EARLIER month (2026_01)
ehB = corrupt_and_ehat("2026_04")
earlier_unchanged = np.allclose(eh[mon=="2026_01"], ehB[mon=="2026_01"])
print(f"   corrupt 2025_09 y: own ê unchanged={own_unchanged} (want T) | LATER 2026_01 ê changed={later_changed} (want T)")
print(f"   corrupt 2026_04 y: EARLIER 2026_01 ê unchanged={earlier_unchanged} (want T)")
A_ok = own_unchanged and later_changed and earlier_unchanged
print(f"   -> {'PASS (past-only expanding, no future leak)' if A_ok else 'FAIL — calibration direction wrong!'}")

# (B) COST SIDE-COUNTING on a hand-built position path via _trans_cost
print("\n(B) COST SIDE-COUNTING (hand path 0->1->1->-1->0):")
seq=[(0,1),(1,1),(1,-1),(-1,0)]
sides=[abs(b-a) for a,b in seq]; costs=[_trans_cost(a,b,1.0,False,0,0) for a,b in seq]
exp_sides=[1,0,2,1]
B_ok = sides==exp_sides and costs==[1.0,0.0,2.0,1.0] and _trans_cost(1,1,1.0,False,0,0)==0.0
print(f"   sides={sides} (want {exp_sides}); costs={costs} (want [1,0,2,1]); hold cost={_trans_cost(1,1,1.0,False,0,0)}")
# hybrid: entry/exit=maker(0.5), flip=2*taker(1.7)
hy = [_trans_cost(0,1,1.0,True,0.5,1.7), _trans_cost(1,0,1.0,True,0.5,1.7), _trans_cost(1,-1,1.0,True,0.5,1.7)]
B_ok &= hy==[0.5,0.5,2*1.7]
print(f"   hybrid entry/exit/flip costs={hy} (want [0.5,0.5,3.4]) -> {'PASS' if B_ok else 'FAIL'}")

# (C) NON-OVERLAP independent spacing
print("\n(C) NON-OVERLAP spacing (my own check):")
day=ts//DAY; maxviol=0
for dd in np.unique(day):
    t=np.sort(ts[day==dd]);
    if len(t)>1: maxviol=max(maxviol, int((np.diff(t)<HZ).sum()))
print(f"   max within-day pairs <600s = {maxviol} -> {'PASS' if maxviol==0 else 'FAIL'}")

# (D) ORACLE independent
print("\n(D) ORACLE sign(y) (my own):")
prof={c: float(np.sum(run_strategy(np.sign(y)*1e9, y, c, 0,0,0.3,1)[0])) for c in (0.0,1.0,1.7)}
D_ok = prof[0.0]>0 and prof[0.0]>prof[1.0]>prof[1.7]
print(f"   net @0={prof[0.0]:.0f} @1={prof[1.0]:.0f} @1.7={prof[1.7]:.0f} -> {'PASS' if D_ok else 'FAIL'}")

# (E) SHUFFLE-NULL independent (different seed than 0C's rng(0))
print("\n(E) SHUFFLE-NULL (my own, seed=12345):")
rng=np.random.default_rng(12345); gs=[]
real_gross=float(np.sum(run_strategy(eh,y,1.0,1.0,0.5,0.3,1)[1]*y))
for _ in range(5):
    ps=p.copy()
    for dd in np.unique(day):
        idx=np.where(day==dd)[0]; ps[idx]=p[idx][rng.permutation(len(idx))]
    ds=ps-decision_center(ps,W); ehs=calibrate_offtest(ds,y,mon)
    gs.append(float(np.sum(run_strategy(ehs,y,1.0,1.0,0.5,0.3,1)[1]*y)))
E_ok = abs(np.mean(gs)) < abs(real_gross)*0.5+1.0
print(f"   real gross={real_gross:.1f} vs shuffled {np.mean(gs):.1f} -> {'PASS' if E_ok else 'FAIL'}")

print(f"\nINDEP AUDIT: {'ALL PASS' if (A_ok and B_ok and maxviol==0 and D_ok and E_ok) else 'REVIEW'}")
