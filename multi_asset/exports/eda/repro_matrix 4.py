"""0C reproduction matrix for acceptance_battery.py (Task 2 audit).
Runs the pre-registered adversarial tests (handoff/acceptance_battery_SPEC.md §12) with 0C
FROZEN thresholds (handoff/acceptance_thresholds_0C_frozen.json). Verifies the battery's
verdicts reproduce 0C's human judgments (S1/N1b archived; broken products rejected).
Writes /tmp/0c_repro.json. Imports the battery as a module (no re-implementation).
"""
import os
import json, sys, numpy as np
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA + "/handoff")
import acceptance_battery as ab

M = MA + "/exports/train"
THR = json.load(open(MA + "/handoff/acceptance_thresholds_0C_frozen.json"))
THR = {k: v for k, v in THR.items() if not k.startswith("_")}


def summ(rep):
    g = {x["name"]: x for x in rep["gates"]}
    return dict(verdict=rep["verdict"], failed=rep["failed_gates"],
                b_ic=g["b_honest_ensemble_ic"].get("pooled_ic"),
                b_champ=g["b_honest_ensemble_ic"].get("champion_ic"),
                b_thresh=g["b_honest_ensemble_ic"].get("threshold"),
                c_folds=g["c_sign_consistency"].get("per_fold_ic"),
                d_dyn=g["d_dynamic_share"].get("dyn_share"),
                e_decay=g["e_forward_window_causal"].get("decay"),
                e_peak0=g["e_forward_window_causal"].get("peak_at_lag0"),
                f_md5c=g["f_panel_byte_check"].get("candidate_panel_md5"),
                f_md5champ=g["f_panel_byte_check"].get("champion_panel_md5"),
                f_match=g["f_panel_byte_check"].get("matches_champion"),
                g_cov=g["g_multiseed_cov"].get("cov"), g_ran=g["g_multiseed_cov"].get("ran"))


def corrupt_lookahead(prod):
    """Inject forward-window leak: prediction at t := realized raw return of the NEXT window
    (Yraw[t+H]). A causal model cannot see this; gate (e) must catch it (peak displaces to +1)."""
    H, T = prod["horizon"], prod["T"]
    Yraw, member, CL, YR = prod["Yraw"], prod["member"], prod["CL"], prod["YR"]
    bad = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in prod.items()}
    S = np.full((T, prod["N"]), np.nan); P = np.full((T, prod["N"]), np.nan)
    bad_folds = []
    for f in prod["folds"]:
        C = np.full((T, prod["N"]), np.nan)
        for t in f["te_rows"]:
            tt = t + H
            if tt >= T:
                continue
            base = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(Yraw[tt]))[0]
            if base.size >= THR["min_base"]:
                C[t, base] = Yraw[tt, base]
        m = np.isfinite(C); S[m] = C[m]; P[m] = C[m]
        bad_folds.append(dict(year=f["year"], te_rows=f["te_rows"], C=C))
    bad["S"], bad["P"], bad["folds"] = S, P, bad_folds
    return bad


def corrupt_duphead_ensemble(prod):
    """Simulate a 'K identical heads' delivery. The honest ensemble of K copies of one head
    == that head, so the STITCHED composite is unchanged. This probes whether ANY gate reads
    head diversity (0B currently has none -> expected: PASS == the documented gap)."""
    # identical: composite already IS a valid single-head-equivalent; battery has no head-corr gate.
    return {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in prod.items()}


OUT = {}
print("loading products ...", flush=True)
champ5 = ab.load_products(f"{M}/wideA_lamorth0_xattn_5yr", THR["min_base"])
champ3 = ab.load_products(f"{M}/wideA_xattn", THR["min_base"])              # seed42 3-fold champion
conf = ab.load_products(f"{M}/wideA_conformer_ref", THR["min_base"])        # lam_orth=1 degraded
print("  champ5/champ3/conformer loaded", flush=True)

# T2a — degraded retrain (lam_orth re-enabled), same 3-fold panel => apples-to-apples
print("T2a conformer_ref vs champion-3fold ...", flush=True)
OUT["T2a_conformer_lamorth1"] = summ(ab.run_battery(conf, champ=champ3, thr=THR))

# G — champion 3-seed CoV
print("G seeds 42/43/44 ...", flush=True)
seedp = {t: ab.load_products(f"{M}/{d}", THR["min_base"]) for t, d in
         [("s42", "wideA_xattn"), ("s43", "wideA_xattn_seed43"), ("s44", "wideA_xattn_seed44")]}
OUT["G_seed_cov"] = summ(ab.run_battery(champ3, champ=champ3, seed_prods=seedp, thr=THR))

# T3c — inject forward-window lookahead (build on champ3)
print("T3c lookahead ...", flush=True)
OUT["T3c_lookahead"] = summ(ab.run_battery(corrupt_lookahead(champ3), champ=champ3, thr=THR))

# T3b — duplicate single head (gap probe)
print("T3b duphead ...", flush=True)
OUT["T3b_duphead_gap"] = summ(ab.run_battery(corrupt_duphead_ensemble(champ3), champ=champ3, thr=THR))

# T2b — archived rejects (5-fold; residual-target panels, different md5)
for tag, d in [("T2b_N1b", "wideA_n1b_multirel_c1"), ("T2b_S1", "wideA_s1_yr4k_c1")]:
    print(f"{tag} ...", flush=True)
    cand = ab.load_products(f"{M}/{d}", THR["min_base"])
    OUT[tag] = summ(ab.run_battery(cand, champ=champ5, thr=THR))

json.dump(OUT, open("/tmp/0c_repro.json", "w"), indent=1, default=str)
print("\n==== REPRO MATRIX ====", flush=True)
for k, v in OUT.items():
    print(f"{k:26s} {v['verdict']:5s} failed={v['failed']}", flush=True)
print("SAVED /tmp/0c_repro.json", flush=True)
