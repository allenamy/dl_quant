"""Validate factor_pipeline gates d/e (+ a/b/c) on a synthetic panel with known ground truth."""
import sys, numpy as np
sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.eval.factor_pipeline import run_factory, gate_d_ridge_dic, gate_e_netcost

rng=np.random.default_rng(0)
T,S=3000,10
truth=rng.standard_normal((T,S))                       # latent cross-sectional alpha
Y=(0.35*truth + rng.standard_normal((T,S)))*20e-4      # returns (return units, ~20bps noise)
B=0.5*truth + 0.8*rng.standard_normal((T,S))           # commoditized baseline: partial view of truth
ts=(np.arange(T)*3600*1_000_000_000).astype(np.int64)  # ns grid, 3600s spacing
day=(ts//(86400*1_000_000_000)).astype(np.int64)
CL=np.ones((T,S),bool)

def shuf(F):
    Fs=F.copy()
    for t in range(T): Fs[t]=F[t][rng.permutation(S)]
    return Fs

factors={
 "ZERO":      np.zeros((T,S)),
 "BASE(=B)":  B.copy(),
 "SHUFFLED":  shuf(B),
 "SYNTH_orth":truth + 0.7*rng.standard_normal((T,S)),   # predicts truth (⊂Y) partly beyond B
}
print(f"synthetic panel T={T} S={S}, horizon=3600")
for name,F in factors.items():
    o=run_factory(F.astype(float),B,Y,CL,ts,day,3600,label=name)
    ga,gb,gd,ge=o["gate_a"],o["gate_b_incremental"],o["gate_d_ridge"],o["gate_e_netcost"]
    print(f"\n[{name}]")
    print(f"  a: meanIC={ga['mean_ic']} IR={ga['ic_ir']}")
    print(f"  b(incr): meanIC={gb['mean_ic']} IR={gb['ic_ir']}")
    print(f"  c(corr vs B): {o['gate_c_corr_vs_B']}")
    print(f"  d(ridge): ic_B={gd.get('ic_B')} ic_BF={gd.get('ic_BF')} dIC={gd.get('dIC')} sign_consistent={gd.get('sign_consistent')} per_fold={gd.get('per_fold_dIC')}")
    print(f"  e(netcost): be_B={ge['be_baseline']} be_comb={ge['be_combined']} d_be={ge['d_be']} d_netSh={ge['d_netSh_c2']}")
    print(f"  passes={o['passes']} ACCEPT={o['ACCEPT']}")
    print(f"  nullz_a={o['gate_a_nullz']} nullz_b={o['gate_b_nullz']}")

print("\n=== INVARIANT CHECKS ===")
def g(name,F): return run_factory(F.astype(float),B,Y,CL,ts,day,3600,label=name)
z=g("ZERO",factors["ZERO"]); bb=g("BASE",factors["BASE(=B)"]); sh=g("SHUFFLED",factors["SHUFFLED"]); sy=g("SYNTH",factors["SYNTH_orth"])
chk=[
 ("ZERO gate_b≈0", abs(z["gate_b_incremental"]["mean_ic"])<0.01),
 ("ZERO dIC≈0", abs(z["gate_d_ridge"]["dIC"])<0.005),
 ("BASE corr≈1", abs(bb["gate_c_corr_vs_B"]-1.0)<0.01),
 ("BASE dIC≈0 (collinear)", abs(bb["gate_d_ridge"]["dIC"])<0.005),
 ("BASE incr≈0", abs(bb["gate_b_incremental"]["mean_ic"])<0.01),
 ("SHUF a≈0", abs(sh["gate_a"]["mean_ic"])<0.02),
 ("SHUF dIC≈0", abs(sh["gate_d_ridge"]["dIC"])<0.005),
 ("SYNTH incr>0", sy["gate_b_incremental"]["mean_ic"]>0.02),
 ("SYNTH dIC>0", sy["gate_d_ridge"]["dIC"]>0.003),
 ("SYNTH ACCEPT", sy["ACCEPT"]),
 ("SHUF fails gate_a (z-gated)", not sh["passes"]["a"]),
 ("SYNTH passes gate_a (z-gated)", sy["passes"]["a"]),
]
allok=True
for nm,ok in chk:
    print(f"  {'PASS' if ok else 'FAIL'}  {nm}"); allok&=ok
print("ALL INVARIANTS PASS" if allok else "SOME INVARIANTS FAIL")
print("DONE_TEST")
