"""Score the 5 stage-2b heads vs the 2-factor book [funding_ema, M0], jointly. Multi-baseline factory.
Includes a self-check invariant: scoring M0 itself vs [funding,M0] MUST reject (corr=1, no increment)."""
import sys, numpy as np
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset"; sys.path.insert(0, MA)
from multi_asset.eval.factor_pipeline import load_panel, run_factory
from multi_asset.eval.factor_scorer import factor_corr, _perts_ic

TR = MA+"/multi_asset/exports/train"
FUND = load_panel("fund_ema_h3600", TR)
Y, CL, ts, day = FUND["Y"], FUND["CL"], FUND["ts"].astype(np.int64), FUND["day"].astype(np.int64)
funding = FUND["pred"]; M0 = load_panel("fund_resid_h3600", TR)["pred"]
BASES = [funding, M0]; NAMES = ["funding", "M0"]
T, S = Y.shape

# assemble 5 heads (merge folds: head_k[te_rows] = scores[te_rows,:,k])
import glob, os.path as op
K = 5; heads = [np.full((T, S), np.nan) for _ in range(K)]
for f in sorted(glob.glob(TR+"/stage2b_kheads/fold_*_head_scores.npz")):
    z = np.load(f); sc = z["scores"].astype(np.float64); tr = z["te_rows"]
    for k in range(K):
        heads[k][tr] = sc[tr, :, k]

def show(lbl, o):
    p = o["passes"]
    print(f"[{lbl}] a(z={o['gate_a_nullz']['z']}) b_incr(z={o['gate_b_nullz']['z']}) "
          f"c_each={o['gate_c_corr_each']} c_max={o['gate_c_corr_vs_B']} "
          f"d(dIC={o['gate_d_ridge'].get('dIC')} pf={o['gate_d_ridge'].get('per_fold_dIC')} sc={o['gate_d_ridge'].get('sign_consistent')}) "
          f"e(d_be={o['gate_e_netcost']['d_be']} dNetSh={o['gate_e_netcost']['d_netSh_c2']}) "
          f"=> passes {p} ACCEPT={o['ACCEPT']}")

print("=== SELF-CHECK: score M0 itself vs [funding,M0] (must REJECT: corr=1, no increment) ===")
show("M0_selfcheck", run_factory(M0, BASES, Y, CL, ts, day, 3600, label="M0_self", base_names=NAMES))
print("=== SELF-CHECK: score funding itself vs [funding,M0] (must REJECT) ===")
show("funding_selfcheck", run_factory(funding, BASES, Y, CL, ts, day, 3600, label="fund_self", base_names=NAMES))

print("\n=== HEAD standalone ICs + head-vs-head corr (dedup within K) ===")
for k in range(K):
    ic, _ = _perts_ic(heads[k], Y, CL); print(f"  head_{k}: standalone IC {ic.mean():+.4f} (n {len(ic)})")
print("  pairwise head corr:")
for a in range(K):
    for b in range(a+1, K):
        print(f"    corr(head_{a},head_{b}) = {factor_corr(heads[a], heads[b], CL)}")

print("\n=== 5 HEADS through the multi-baseline factory (vs [funding, M0]) ===")
for k in range(K):
    show(f"head_{k}", run_factory(heads[k], BASES, Y, CL, ts, day, 3600, label=f"head_{k}", base_names=NAMES))
print("DONE_KHEADS")
