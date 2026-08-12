"""0C independent adversarial verification of the factory pipeline (do NOT trust smoke). Uses a TEMP
ledger (never the real campaign ledger). Tests: Lock(i) verdict-path, Lock(ii) tamper-detect + M-denom,
holdout exclusion, null calibration, closure (ii) NaN-not-0 + (iii) sparse-leg ban. Writes /tmp/0c_factory_adv.json."""
import sys, json, numpy as np
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/factory")
import dsl
from ledger import Ledger, STAGE0_VERDICTS
import pipeline as P
R = {}

# ---- Lock (i): Stage-0 path cannot write a discovery verdict ----
tl = "/tmp/0c_test_ledger.jsonl"
import os
if os.path.exists(tl): os.remove(tl)
lg = Ledger(tl)
try:
    lg._append(dict(stage="stage0", verdict="CANDIDATE", formula_str="x"), STAGE0_VERDICTS)
    R["lock_i_stage0_candidate"] = "FAIL (accepted CANDIDATE on stage0 path)"
except PermissionError:
    R["lock_i_stage0_candidate"] = "PASS (PermissionError)"
# fdr_q cannot drive a CANDIDATE without stage1_stats
try:
    lg._append(dict(stage="x", verdict="CANDIDATE", fdr_q=0.01, formula_str="x"), {"CANDIDATE"})
    R["lock_i_fdrq_drives_verdict"] = "FAIL (fdr_q drove CANDIDATE w/o stage1_stats)"
except PermissionError:
    R["lock_i_fdrq_drives_verdict"] = "PASS (PermissionError)"

# ---- Lock (ii): tamper a row -> verify() False; M counts all rows ----
lg2 = Ledger(tl := "/tmp/0c_test_ledger2.jsonl") if not os.path.exists("/tmp/0c_test_ledger2.jsonl") else Ledger("/tmp/0c_test_ledger2.jsonl")
if os.path.exists("/tmp/0c_test_ledger2.jsonl"): os.remove("/tmp/0c_test_ledger2.jsonl")
lg2 = Ledger("/tmp/0c_test_ledger2.jsonl")
for i in range(3):
    lg2.append_stage0(f"f{i}", "md5", 1, 1, inc_ic=0.01*i, fdr_q=0.5, survived=False)
R["lock_ii_verify_clean"] = "PASS" if lg2.verify() else "FAIL"
R["lock_ii_M_counts_all"] = "PASS" if lg2.M() == 3 else f"FAIL (M={lg2.M()})"
lg2._rows[1]["inc_ic"] = 0.999            # tamper
R["lock_ii_tamper_detected"] = "PASS (verify False)" if not lg2.verify() else "FAIL (tamper undetected)"

# ---- Closure (iii): sparse leg banned from temporal ops ----
R["closure_iii_ts_on_leg"] = "PASS (rejected)" if not dsl.validate("ts_mean(king, 6)")["ok"] else "FAIL (accepted)"
R["closure_iii_ts_on_dense"] = "PASS (accepted)" if dsl.validate("ts_mean(mom_4h, 6)")["ok"] else "FAIL"
R["closure_iii_leg_pointwise_ok"] = "PASS" if dsl.validate("where(gt(rvol_24h, 0), king, s2)")["ok"] else "FAIL"
R["closure_iii_ts_on_xsec_leg"] = "PASS (SPARSE taint propagates)" if not dsl.validate("ts_mean(xsec_rank(king), 6)")["ok"] else "FAIL"

# ---- Closure (ii): NaN not 0/inf ----
T, N = 30, 12
A = np.random.default_rng(0).normal(size=(T, N)); ctx = {c: A.copy() for c in dsl.DENSE_CHANNELS}
# div by exact zero -> NaN (not inf, not 0)
divz = dsl.evaluate(dsl.parse("div(mom_4h, sub(mom_4h, mom_4h))"), ctx)
R["closure_ii_div0_is_nan"] = "PASS (NaN)" if np.all(np.isnan(divz)) else f"FAIL (got {divz.flat[0]})"
# xsec_z on a constant cross-section -> SHOULD be NaN; check current behavior
const_ctx = {c: np.ones((T, N)) for c in dsl.DENSE_CHANNELS}
xz = dsl.evaluate(dsl.parse("xsec_z(mom_4h)"), const_ctx)
R["closure_ii_xsecz_degenerate"] = ("PASS (NaN)" if np.all(np.isnan(xz)) else
                                    f"VIOLATION (zero-fill, sample={float(xz.flat[0])}) — should be NaN not 0")

# ---- Holdout exclusion + null calibration (needs the real panel) ----
try:
    C = P.load_context(horizon=4, subsample=8)   # subsample for speed
    yrs = C["year"][C["rows"]]
    R["holdout_2026_excluded"] = "PASS (no 2026)" if (2026 not in set(yrs.tolist())) else "FAIL (2026 present)"
    R["holdout_year_range"] = f"{int(yrs.min())}-{int(yrs.max())}"
    # null calibration: shuffle-eval per-factor IC should center ~0
    rng = np.random.default_rng(1)
    f0 = dsl.evaluate(dsl.parse("xsec_rank(mom_24h)"), C["ctx"])
    day_of = {int(t): int(C["day"][t]) for t in C["rows"]}
    tmask = {int(t): (C["member"][t] & C["CL"][t] & np.isfinite(C["target"][t])) for t in C["rows"]}
    day2rep = {}
    for t in C["rows"]: day2rep.setdefault(int(C["day"][t]), int(t))
    udays = np.array(sorted(day2rep)); nullics = []
    for _ in range(40):
        dmap = dict(zip(udays, rng.permutation(udays))); ics = []
        for t in C["rows"]:
            ti = int(t); tt = day2rep[dmap[day_of[ti]]]
            cb = np.where(tmask[ti] & tmask[tt] & np.isfinite(f0[ti]))[0]
            if cb.size >= 8: ics.append(P._ric(f0[ti, cb], C["target"][tt, cb]))
        if ics: nullics.append(float(np.nanmean(ics)))
    # real (unshuffled) IC of same factor
    real_ic = P.stats(*P.score_series(f0, C), rng)["inc_ic"]
    R["null_shuffle_mean"] = round(float(np.mean(nullics)), 5)
    R["null_shuffle_std"] = round(float(np.std(nullics)), 5)
    R["null_calibrated_~0"] = "PASS" if abs(np.mean(nullics)) < 3 * np.std(nullics) / np.sqrt(len(nullics)) + 0.01 else "CHECK"
    R["null_real_vs_null"] = f"real_ic {real_ic} vs null_mean {round(float(np.mean(nullics)),5)}"
except Exception as e:
    R["holdout_null_error"] = f"{type(e).__name__}: {e}"

print(json.dumps(R, indent=1))
json.dump(R, open("/tmp/0c_factory_adv.json", "w"), indent=1)
