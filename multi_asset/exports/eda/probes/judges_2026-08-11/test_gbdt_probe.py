"""Validate gbdt_probe on synthetic panels: JUICE (nonlinear interaction beyond funding) vs NULL (funding+noise)."""
import sys, numpy as np
sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.eval.gbdt_probe import run_probe
LP=dict(objective="regression",n_estimators=300,learning_rate=0.05,num_leaves=15,max_depth=4,min_child_samples=40,feature_fraction=0.7,bagging_fraction=0.8,bagging_freq=1,lambda_l1=0.5,lambda_l2=2.0,verbosity=-1,n_jobs=4)

def make_panel(juice, seed=0):
    rng=np.random.default_rng(seed)
    S=12; DAYS=90; TPD=8; T=DAYS*TPD; F=20
    ts=np.repeat(np.arange(T), S); day=ts//TPD; N=len(ts)
    X=rng.standard_normal((N,F)).astype(np.float32)
    fund=rng.standard_normal(N)                              # the funding factor (per row)
    # nonlinear interaction signal GBDT can find, linear cannot: sign(X0)*X1 + relu(X2)*X3
    nonlin = np.sign(X[:,0])*X[:,1] + np.maximum(X[:,2],0)*X[:,3]
    nonlin = (nonlin-nonlin.mean())/nonlin.std()
    y = 0.45*fund + (0.35*nonlin if juice else 0.0) + rng.standard_normal(N)   # returns
    y=(y*20e-4).astype(np.float64)                          # ~bps scale
    return dict(X=X.astype(np.float64), y=y, fund=fund, ts=ts.astype(np.int64), day=day.astype(np.int64))

print("========== CASE 1: JUICE (nonlinear interaction beyond funding) ==========")
r1=run_probe(make_panel(True), label="JUICE", params=LP)
print("\n========== CASE 2: NULL (funding + noise only, no nonlinear) ==========")
r2=run_probe(make_panel(False), label="NULL", params=LP)

print("\n=== INVARIANT CHECKS ===")
chk=[
 ("JUICE detected (z>=2.5 sign-consistent)", abs(r1["z"])>=2.5 and r1["sign_consistent"]),
 ("JUICE leak-guard clean (~0)", r1["leak_ok"]),
 ("NULL not detected (z<2.5 or not sign-consistent)", not(abs(r2["z"])>=2.5 and r2["sign_consistent"])),
 ("NULL leak-guard clean", r2["leak_ok"]),
]
ok=True
for nm,c in chk: print(f"  {'PASS' if c else 'FAIL'}  {nm}"); ok&=c
print("ALL PROBE INVARIANTS PASS" if ok else "SOME FAIL")
print("DONE_TEST")
