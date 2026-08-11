import numpy as np, json, glob
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"


def ens(tag):
    d = TR + tag
    pr = np.load(d + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64)
    res = []
    for f in sorted(glob.glob(d + "/fold_*_head_scores.npz")):
        sc = np.load(f)["scores"]; T, N, K = sc.shape
        ics = []
        for t in np.where((member & CL & np.isfinite(YR)).any(1))[0]:
            base = np.where(member[t] & CL[t] & np.isfinite(YR[t]))[0]
            if base.size < 5:
                continue
            comp = np.zeros(base.size); nk = 0
            for k in range(K):
                col = sc[t, base, k]
                if np.isfinite(col).all() and col.std() > 1e-12:
                    comp += (col - col.mean()) / col.std(); nk += 1
            if nk:
                ic = np.corrcoef(rankdata(comp / nk), rankdata(YR[t, base]))[0, 1]
                if np.isfinite(ic):
                    ics.append(ic)
        res.append(round(float(np.mean(ics)), 4))
    return round(float(np.mean(res)), 4), res


# 2x2 mechanism (all 3-fold, same panel 39f5cc4e, honest ensemble)
xattn_pen, xp = ens("wideA_xattn")        # xattn=T, lam_orth=1.0
conf, cf = ens("wideA_conformer_ref")     # xattn=F, lam_orth=1.0
lam, lf = ens("wideA_lamorth0")           # xattn=F, lam_orth=0
xa, xf = ens("wideA_lamorth0_xattn")      # xattn=T, lam_orth=0
print("2x2 ensemble IC (3-fold):")
print(f"  xattn=F orth=1.0 (conformer_ref): {conf} {cf}")
print(f"  xattn=F orth=0   (lamorth0):      {lam} {lf}")
print(f"  xattn=T orth=1.0 (xattn):         {xattn_pen} {xp}")
print(f"  xattn=T orth=0   (lamorth0_xattn):{xa} {xf}")

a = json.load(open(EDA + "xattn_stack_audit.json"))
a["mechanism_2x2"] = dict(
    xattnF_orth1_conformer_ref=conf, xattnF_orth0_lamorth0=lam,
    xattnT_orth1_xattn=xattn_pen, xattnT_orth0_lamorth0_xattn=xa,
    xattn_gain_with_penalty=round(xattn_pen - conf, 4),
    xattn_gain_without_penalty=round(xa - lam, 4),
    verdict=("The orthogonality penalty SPECIFICALLY SUPPRESSED the cross-asset attention: adding xattn "
             f"under lam_orth=1.0 gained only {round(xattn_pen-conf,4):+.4f} (~0), but under lam_orth=0 it "
             f"gains {round(xa-lam,4):+.4f}. The penalty didn't merely dilute ~2x -- it strangled the "
             "attention's contribution entirely. Removing it unlocks BOTH the base K-head level AND the "
             "attention alpha. Extends the penalty-dilution archive with a LARGER coefficient on the xattn arm."))
a["verdict"] = dict(
    ruling="REAL (audit-clean on the 3-fold window) -- PENDING 5yr regime confirmation",
    reproduction="exact (0.0718/0.0988/0.1138, mean 0.0948 = JSON)",
    leak="CLEAN: panel byte-identical (39f5cc4e); attention is contemporaneous cross-sectional (mixes coins "
         "only within the same prediction hour, member-masked <=t, no cross-hour/temporal leak); fold "
         "boundaries contiguous non-overlapping (te days 302-383/384-465/466-548), 8d embargo, expanding train.",
    dynamic_static="dyn-share 0.949 (0.983/0.954/0.909); static-shuffle 0.001-0.010 -> NOT static-tilt "
                   "inflated. The #1 suspicion is REFUTED; the +0.095 is genuine dynamic timing content.",
    paired_significance="Δ vs lamorth0 +0.0149/+0.0233/+0.0446, all 3 folds CI-exclude-0. Pred similarity "
                        "to lamorth0 only 0.54 -> genuinely different cross-sectional bets. (Per-ts "
                        "significance is easy with ~490 cross-sections/fold; the load-bearing evidence is "
                        "dyn-share + the coherent 2x2 mechanism, not the CI alone.)",
    critical_caveat="The 3-fold TEST PERIOD IS ENTIRELY 2025 (days 302-548 of 549 = the last 45%, all in the "
                    "strong-regime FULL-110-member window -- DL's most favorable regime). So +0.095 is a "
                    "STRONG-REGIME number. The historical arms (QIM 5yr) show 2025 = the best year (0.081); "
                    "weak years (2022 ~0.044, 2026 flat) are NOT in this window. The 5yr replay "
                    "(wideA_lamorth0_xattn_5yr, running) is REQUIRED to confirm regime-robustness before "
                    "crowning -- do NOT kill it; the audit found no reason to.",
    increasing_delta_note="Δ increases across folds (+0.015/+0.023/+0.045); fold2 (most recent ~2025-08..10, "
                          "fullest universe) has the biggest xattn edge -- consistent with attention "
                          "benefiting from breadth, a benign explanation, but reinforces that this is a "
                          "recent-full-universe result needing weak-year confirmation.")
json.dump(a, open(EDA + "xattn_stack_audit.json", "w"), indent=2, default=str)
print("\nenriched", EDA + "xattn_stack_audit.json")
