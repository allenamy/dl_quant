"""dlarch_t3_verdict.py -- the T3 verdict under BOTH criteria, side by side, per section 10.

Section 10 of DECISION_RULE_dl_program_book_gate_2026-09-25.md (lead, after dlarch's provenance alert
6a6d48df9): revision 4 is NOT a blind criterion for T3, because the readings existed and had been
delivered 5.5 h before it was committed. So T3 is judged under BOTH and the user sees both:

  A = original section 3 + revision 1   -> BLIND for T3 (written before any T3 reading existed)
  B = revision 4                        -> NOT BLIND for T3 (section 10); applies normally to later arms

This device implements the FROZEN TEXT of each, clause by clause, and does not summarise. That matters:
lead's own section 10 characterises A's outcome as "cannot resolve, not recommended", but A's REJECT
clause is literally `mean(d) <= 0`, which fires here independently of resolution. Paraphrase and text
disagree, so the text is what gets coded and the difference is reported.

dlarch has a stake in what this gate admits and therefore writes NO criterion here -- every threshold,
comparison and verdict word below is transcribed from the frozen document, with the section it came from
recorded next to it.

usage: dlarch_t3_verdict.py <env-whitelist> <sigma-receipt> <receipts-dir> <out.json>
"""
import os, sys, json, glob, math, time, hashlib

WL = set(sys.argv[1].split(","))
_x = sorted(set(os.environ) - WL)
assert not _x, f"env outside whitelist: {_x}"
SIGR, RDIR, OUT = sys.argv[2], sys.argv[3], sys.argv[4]
KAPPA = 1.3533          # revision 1: sigma_ref = 1.3533 * sigma_hat (80% one-sided, chi2 df=7)
N1 = 3                  # stage 1 seeds 42/2027/7, frozen in section 3
DD_TOL_PP = 3.0         # section 3 condition 4: not worse than T0 by more than 3 percentage points


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


S = json.load(open(SIGR))
sd_d, sig = S["sd_d"], S["sigma_hat_F10_per_segment"]
assert "status" not in sd_d, f"sd(d) not available: {sd_d.get('status')}"
for g in ("pre2026", "2026"):
    assert sd_d[g].get("routes_agree"), f"{g}: the two sd(d) routes do not agree; refusing to judge"


def seg(g):
    """mean(d), sd(d), per-seed d, and the SE both criteria share the formula for."""
    r = sd_d[g]
    per = r["d_per_seed_route_i"]
    sref = KAPPA * sig[g]["sigma_hat_F10"]
    se_meas = r["sd_d"] / math.sqrt(N1)
    se_back = sref * math.sqrt(2) / math.sqrt(N1)
    return {"segment": g, "mean_d": r["mean_d"], "sd_d": r["sd_d"], "d_per_seed": per,
            "n_positive": sum(1 for v in per.values() if v > 0), "n": len(per),
            "sigma_hat_F10": sig[g]["sigma_hat_F10"], "sigma_ref": sref,
            "SE_measured_branch": se_meas, "SE_backstop_branch": se_back,
            "SE": max(se_meas, se_back), "branch_taken": "backstop" if se_back > se_meas else "measured",
            "three_SE": 3 * max(se_meas, se_back), "threshold": max(1.0, 3 * max(se_meas, se_back))}


PRE, Y26 = seg("pre2026"), seg("2026")

# ── drawdown guardrail (section 3 condition 4, unchanged by revision 4) ──────────────────────────────
def maxdd(pattern, arm, segment):
    out = {}
    for d in sorted(glob.glob(os.path.join(RDIR, pattern))):
        fs = glob.glob(os.path.join(d, "RETAIN_*.json"))
        if not fs:
            continue
        r = json.load(open(fs[0]))
        tag = r["tag"]
        sd_ = int(tag.split(f"DLARCH_{arm}_s")[1].split("_")[0])
        out[sd_] = r["judge_table"][segment]["paths"]["maxdd_5m"]["path_mean"]
    return out


dd_t0, dd_t3 = maxdd("RETAIN_s*_2026-09-25.json", "T0", "pre2026"), maxdd("RETAIN_T3_s*_2026-09-25.json", "T3_clamp", "pre2026")
pair = sorted(set(dd_t3) & set(dd_t0))
assert pair, "no seed has both a T0 and a T3 cell; cannot evaluate the drawdown guardrail"
# maxdd is recorded as a NEGATIVE fraction; "worse" = more negative. Compare in percentage points.
dd = {"seeds": pair,
      "T3_mean_pp": 100.0 * sum(dd_t3[s] for s in pair) / len(pair),
      "T0_mean_pp": 100.0 * sum(dd_t0[s] for s in pair) / len(pair)}
dd["T3_minus_T0_pp"] = dd["T3_mean_pp"] - dd["T0_mean_pp"]
dd["passes"] = dd["T3_minus_T0_pp"] >= -DD_TOL_PP      # not worse by more than 3pp
dd["note"] = ("maxdd_5m path_mean over the pre-2026 segment, averaged across the seeds that have BOTH "
              "cells. Negative is worse; the guardrail allows T3 to be at most %.1f pp worse." % DD_TOL_PP)

# ── criterion A: section 3 + revision 1 (BLIND for T3) ──────────────────────────────────────────────
A = {"criterion": "section 3 (stage 1) with revision 1's sigma_ref", "main_window": "pre2026",
     "blind_for_T3": True,
     "why_blind": "written before any T3 book-layer reading existed (revision 1 timestamped 02:2xZ)",
     "clauses": {
        "1_mean_ge_threshold": {"text": "mean(d) >= max(1.0, 3*SE)", "lhs": PRE["mean_d"],
                                "rhs": PRE["threshold"], "pass": PRE["mean_d"] >= PRE["threshold"]},
        "2_all_three_seeds_positive": {"text": "3/3 seeds d > 0", "n_positive": PRE["n_positive"],
                                       "pass": PRE["n_positive"] == N1},
        "3_2026_point_estimate_ge_0": {"text": "mean(d_2026) >= 0", "lhs": Y26["mean_d"],
                                       "pass": Y26["mean_d"] >= 0},
        "4_drawdown_guardrail": {"text": "pre-2026 maxdd not worse than T0 by > 3pp", **dd}}}
if A["clauses"]["1_mean_ge_threshold"]["pass"] and A["clauses"]["2_all_three_seeds_positive"]["pass"] \
        and A["clauses"]["3_2026_point_estimate_ge_0"]["pass"] and dd["passes"]:
    A["verdict"] = "RECOMMEND_TO_USER"
elif PRE["mean_d"] <= 0 or PRE["n_positive"] <= 1:
    A["verdict"] = "REJECT"
    A["reject_clause_fired"] = ([] + (["mean(d) <= 0"] if PRE["mean_d"] <= 0 else [])
                                + (["<=1 seed d > 0"] if PRE["n_positive"] <= 1 else []))
elif 1.0 <= PRE["mean_d"] < PRE["three_SE"] and PRE["n_positive"] == N1 \
        and A["clauses"]["3_2026_point_estimate_ge_0"]["pass"] and dd["passes"]:
    A["verdict"] = "EXTEND"
else:
    A["verdict"] = "UNDECIDED"

# ── criterion B: revision 4 (NOT blind for T3, per section 10) ──────────────────────────────────────
B = {"criterion": "revision 4 (user's dual main criteria)", "main_window": "2026",
     "blind_for_T3": False,
     "why_not_blind": ("section 10: the T3 readings existed at 18:22Z and were delivered ~18:3xZ; "
                       "revision 4 was committed 23:57Z. Applies normally to LATER arms."),
     "clauses": {
        "1_2026_mean_ge_threshold": {"text": "mean(d_2026) >= max(1.0, 3*SE_2026)", "lhs": Y26["mean_d"],
                                     "rhs": Y26["threshold"], "pass": Y26["mean_d"] >= Y26["threshold"]},
        "2_2026_all_three_positive": {"text": "2026: 3/3 seeds d > 0", "n_positive": Y26["n_positive"],
                                      "pass": Y26["n_positive"] == N1},
        "3_pre2026_not_worse": {"text": "mean(d_pre) >= 0", "lhs": PRE["mean_d"],
                                "pass": PRE["mean_d"] >= 0},
        "4_drawdown_guardrail": {"text": "per section 3", **dd}}}
if all(B["clauses"][k].get("pass") for k in ("1_2026_mean_ge_threshold", "2_2026_all_three_positive",
                                             "3_pre2026_not_worse")) and dd["passes"]:
    B["verdict"] = "RECOMMEND_TO_USER"
elif Y26["mean_d"] <= 0 or Y26["n_positive"] <= 1 or PRE["mean_d"] < -PRE["three_SE"]:
    B["verdict"] = "REJECT"
    B["reject_clause_fired"] = ([] + (["mean(d_2026) <= 0"] if Y26["mean_d"] <= 0 else [])
                                + (["<=1 seed positive in 2026"] if Y26["n_positive"] <= 1 else [])
                                + (["mean(d_pre) < -3*SE_pre"] if PRE["mean_d"] < -PRE["three_SE"] else []))
elif 1.0 <= Y26["mean_d"] < Y26["three_SE"] and Y26["n_positive"] == N1 \
        and B["clauses"]["3_pre2026_not_worse"]["pass"] and dd["passes"]:
    B["verdict"] = "EXTEND"
else:
    B["verdict"] = "UNDECIDED"

# ── the mandatory NC column (revision 4 clause 5) ───────────────────────────────────────────────────
def vs_nc(pattern, arm):
    out = {}
    for d in sorted(glob.glob(os.path.join(RDIR, pattern))):
        fs = glob.glob(os.path.join(d, "RETAIN_*.json"))
        if fs:
            r = json.load(open(fs[0]))
            s_ = int(r["tag"].split(f"DLARCH_{arm}_s")[1].split("_")[0])
            out[s_] = {k: v["mean_bps_per_day"] for k, v in r["dbar_vs_control"].items()}
    return out


t3nc = vs_nc("RETAIN_T3_s*_2026-09-25.json", "T3_clamp")
nc_col = {g: {"per_seed": {f"s{s}": t3nc[s][g] for s in sorted(t3nc)},
              "mean": sum(t3nc[s][g] for s in t3nc) / len(t3nc)} for g in ("pre2026", "2026")}
nc_wording_required = nc_col["2026"]["mean"] < 0

rec = {"device": "dlarch_t3_verdict.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "sigma_receipt": os.path.abspath(SIGR), "sigma_receipt_sha256": sha(SIGR),
       "measurements": {"pre2026": PRE, "2026": Y26},
       "criterion_A_section3_rev1_BLIND": A, "criterion_B_rev4_NOT_BLIND": B,
       "vs_in_service_NC": nc_col,
       "nc_wording_required_by_rev4_clause5": nc_wording_required,
       "nc_wording": ("2026 段对在役 NC 仍为负" if nc_wording_required else None),
       "both_criteria_agree": A["verdict"] == B["verdict"],
       "paraphrase_discrepancy": ("section 10 describes A's outcome as 'cannot resolve, not recommended'. "
                                  "A's frozen REJECT clause is literally `mean(d) <= 0`, which fires here "
                                  "(mean(d_pre) = %.3f), so the frozen text yields REJECT, a stronger "
                                  "verdict word than the paraphrase. Reported, not reconciled -- the text "
                                  "is what this device implements." % PRE["mean_d"]),
       "authorship": ("dlarch wrote no criterion here. Every threshold and verdict word is transcribed "
                      "from the frozen document; dlarch has a stake in what this gate admits.")}
tmp = OUT + ".tmp"
with open(tmp, "w") as f:
    json.dump(rec, f, indent=1)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, OUT)
assert json.load(open(OUT)) == rec, "receipt read back differs from what was written"

for nm, C, M in (("A  section3+rev1 (BLIND for T3)", A, PRE), ("B  revision 4 (NOT blind for T3)", B, Y26)):
    print("%-34s main=%-8s mean(d)=%+7.3f  threshold=%6.3f  positive=%d/%d  ->  %s"
          % (nm, C["main_window"], M["mean_d"], M["threshold"], M["n_positive"], M["n"], C["verdict"]))
    if "reject_clause_fired" in C:
        print("%-34s   reject clauses: %s" % ("", ", ".join(C["reject_clause_fired"])))
print()
print("SE branch taken: pre2026 %s (measured %.4f vs backstop %.4f) | 2026 %s (%.4f vs %.4f)"
      % (PRE["branch_taken"], PRE["SE_measured_branch"], PRE["SE_backstop_branch"],
         Y26["branch_taken"], Y26["SE_measured_branch"], Y26["SE_backstop_branch"]))
print("drawdown guardrail: T3 %.2f pp vs T0 %.2f pp -> diff %+.2f pp, passes=%s"
      % (dd["T3_mean_pp"], dd["T0_mean_pp"], dd["T3_minus_T0_pp"], dd["passes"]))
print("vs in-service NC: pre2026 mean %+.3f | 2026 mean %+.3f  (rev4 wording required: %s)"
      % (nc_col["pre2026"]["mean"], nc_col["2026"]["mean"], nc_wording_required))
print("both criteria agree:", rec["both_criteria_agree"])
print("T3_VERDICT OK receipt=%s sha256=%s" % (OUT, sha(OUT)[:16]))
