"""0C reproduction on acceptance_battery v2 — the rows the built-in self-test does NOT cover:
T2b archived rejects (N1b/S1) + T2a degraded retrain (conformer lam_orth=1) vs the CORRECT
3-fold champion (wideA_lamorth0_xattn). Confirms the v2 verdict taxonomy reproduces 0C's
human ARCHIVE judgments. Writes /tmp/0c_repro_v2.json.
"""
import os
import json, sys, numpy as np
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA + "/handoff")
import acceptance_battery as ab
M = MA + "/exports/train"
THR = ab.THRESHOLDS


def summ(rep):
    g = {x["name"]: x for x in rep["gates"]}
    return dict(verdict=rep["verdict"], hard_failed=rep["hard_failed"], soft_failed=rep["soft_failed"],
                b_ic_resid=g["b_honest_ensemble_ic"]["ic_pooled_resid"],
                b_ic_raw=g["b_honest_ensemble_ic"]["ic_pooled_raw"],
                b_champ=g["b_honest_ensemble_ic"]["champion_ic"], b_thresh=g["b_honest_ensemble_ic"]["threshold"],
                f_ts_match=g["f_index_alignment"].get("ts_md5_match"),
                f_passed=g["f_index_alignment"]["passed"],
                e_peak0=g["e_forward_causal"]["peak_at_lag0"], e_pass=g["e_forward_causal"]["passed"],
                e_prof=g["e_forward_causal"]["profile_fullH"],
                g_headcorr=g["g_cov_headdiv"].get("head_pairwise_corr_max"))


OUT = {}
print("loading champions ...", flush=True)
champ5 = ab.load_any(f"{M}/wideA_lamorth0_xattn_5yr", THR)
champ3 = ab.load_any(f"{M}/wideA_lamorth0_xattn", THR)      # TRUE 3-fold champion (lam_orth=0)
ic3, _, _ = ab.ic_series(champ3, champ3.pred, champ3.oos_rows, "YR")
OUT["_champ3_true_ic"] = round(float(np.mean(ic3)), 4)
print("  champ3 (lamorth0_xattn) IC =", OUT["_champ3_true_ic"], flush=True)

# T2a — degraded retrain (lam_orth re-enabled) vs TRUE champion, same 3-fold panel
print("T2a conformer(lam_orth=1) vs lamorth0_xattn ...", flush=True)
conf = ab.load_any(f"{M}/wideA_conformer_ref", THR)
OUT["T2a_conformer_degraded"] = summ(ab.run_battery(conf, champ=champ3, thr=THR))

# G — champion head-diversity (champ3 alone: 6 distinct heads should pass)
print("G head-diversity on champ3 ...", flush=True)
OUT["G_champ3_headdiv"] = summ(ab.run_battery(champ3, champ=champ3, thr=THR))

# T2b — archived rejects (5-fold, residual-target panels)
for tag, d in [("T2b_N1b", "wideA_n1b_multirel_c1"), ("T2b_S1", "wideA_s1_yr4k_c1")]:
    print(f"{tag} ...", flush=True)
    cand = ab.load_any(f"{M}/{d}", THR)
    OUT[tag] = summ(ab.run_battery(cand, champ=champ5, thr=THR))

json.dump(OUT, open("/tmp/0c_repro_v2.json", "w"), indent=1, default=str)
print("\n==== REPRO v2 ====", flush=True)
for k, v in OUT.items():
    if isinstance(v, dict):
        print(f"{k:26s} {v['verdict']:22s} hard={v['hard_failed']} soft={v['soft_failed']}", flush=True)
print("SAVED /tmp/0c_repro_v2.json", flush=True)
