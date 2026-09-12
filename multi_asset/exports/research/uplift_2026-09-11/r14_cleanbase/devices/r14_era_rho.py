"""r14 CONTROL — is the FULL->CLEAN rho move the DEFECT or the ERA?

On this artifact the two are perfectly confounded: there is no king prediction before 2024-01-01 in
EITHER the v3 or the v4 file (r14_pod_deadmask receipt), so no baseline with a live king leg exists on
the dead prefix.  The best available control is to ask whether rho is era-stable INSIDE the clean sample.
If rho wanders as much between 2024 / 2025 / 2026 as it does between FULL and CLEAN, the FULL->CLEAN move
is not evidence about the defect at all.

PREREG 89ba6e7d... + AMENDMENT 1 asserted.  ENV WHITELIST (E-0826-D) = EMPTY SET, asserted in-file.
"""
import os, sys, json, hashlib, calendar, time
_FORBID = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
           "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","TILT",
           "TILT_TAU","TILT_K","KMOD","KMOD_F10","KMOD_L","KMOD_AGREE","KTAIL","SEATF10","SEATNET",
           "FUNDSCALE","REF_SKIP","SLEEVE","CDAMP","LTRIM_TH","FTRIM_TH","RNSM","FTPOS","PANEL",
           "PANEL_IN","EXPORT_PANEL","EMA_STATE_JSON","JUDGE_HC","JUDGE_REQUIRE_W")
_v = [k for k in _FORBID if k in os.environ]
assert not _v, "E-0826-D env violation: %r" % _v
ENV_SEEN = sorted(os.environ.keys()); ENV_WHITELIST = []
assert ENV_WHITELIST == []
import numpy as np
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def T(*a): return calendar.timegm(a + (0,)*(6-len(a)))
ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
OUT = ROOT + "/r14_cleanbase"
assert sha(OUT + "/PREREG_r14_clean_baseline_2026-09-12.md") == "89ba6e7d87d79866d78f7a95400ee13b21b7d0d511dfc82f6ce7b509ca956fe7"
assert sha(OUT + "/PREREG_AMENDMENT_1_2026-09-12.md") == "e1caddf028b5148403da28527b6cb27ab152652d413c5f8bdf4bd04e4b74012f"
R = {"step": "R14_ERA_RHO", "self_sha256": sha(os.path.abspath(__file__)),
     "env_whitelist": ENV_WHITELIST, "env_seen_at_runtime": ENV_SEEN,
     "numpy": np.__version__, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
SP = reg_p = OUT + "/series/r14_clean_series.npz"
R["inputs"] = {"r14_clean_series": {"path": SP, "sha256": sha(SP)}}
z = np.load(SP, allow_pickle=True)
ts = z["ts"]; gA0 = z["g_A0"]; CLEAN = z["clean"]; names = [str(x) for x in z["names"]]; G = z["G"]
SETA = ["TSMOM","VRP","CMUM","SLOW","COINT","REVS","TSMOM_best","CMUM_static","CMUM_best",
        "SLOW_best","REVS_best","XIB_LAG50","AMIHUD_SLEEVE","T1_FORMB"]
def rho(a, b):
    return float(np.corrcoef(a, b)[0, 1]) if (np.std(a) > 0 and np.std(b) > 0) else float("nan")
ERAS = {str(y): (ts >= T(y,1,1)) & (ts < T(y+1,1,1)) for y in range(2022, 2027)}
TAB = {}
print("%-16s %8s %8s | %8s %8s %8s %8s %8s | %9s %9s"%("arm","FULL","CLEAN","2022","2023","2024","2025","2026","clean_rng","dFULLCL"))
for k in SETA:
    y = G[:, names.index(k)]
    rf = rho(y, gA0); rc = rho(y[CLEAN], gA0[CLEAN])
    per = {e: round(rho(y[m], gA0[m]), 4) for e, m in ERAS.items()}
    clean_years = [per[e] for e in ("2024","2025","2026")]
    rngc = round(max(clean_years) - min(clean_years), 4)
    TAB[k] = {"rho_FULL": round(rf,4), "rho_CLEAN": round(rc,4), "per_year": per,
              "within_clean_year_range": rngc, "abs_d_FULL_to_CLEAN": round(abs(rc-rf), 4),
              "era_noise_exceeds_defect_move": bool(rngc > abs(rc-rf))}
    print("%-16s %+8.4f %+8.4f | %+8.4f %+8.4f %+8.4f %+8.4f %+8.4f | %9.4f %9.4f"%(
        k, rf, rc, per["2022"], per["2023"], per["2024"], per["2025"], per["2026"], rngc, abs(rc-rf)))
R["per_arm"] = TAB
n_exceed = sum(1 for v in TAB.values() if v["era_noise_exceeds_defect_move"])
R["summary"] = {"n_arms": len(SETA), "n_with_era_noise_exceeding_the_FULL_to_CLEAN_move": n_exceed,
    "median_within_clean_year_range": round(float(np.median([v["within_clean_year_range"] for v in TAB.values()])), 4),
    "median_abs_d_FULL_to_CLEAN": round(float(np.median([v["abs_d_FULL_to_CLEAN"] for v in TAB.values()])), 4),
    "reading": "if the within-clean-era spread of rho is larger than the FULL->CLEAN move for most arms, "
               "the FULL->CLEAN move carries no information about the dead-leg defect specifically"}
print("\n%d/%d arms: rho wanders MORE between 2024/2025/2026 than it moves FULL->CLEAN" % (n_exceed, len(SETA)))
print("median within-clean-era range %.4f vs median |FULL->CLEAN move| %.4f"
      % (R["summary"]["median_within_clean_year_range"], R["summary"]["median_abs_d_FULL_to_CLEAN"]))
json.dump(R, open(OUT + "/receipts/RECEIPT_r14_era_rho.json", "w"), indent=1)
print("ERA_RHO_DONE")
