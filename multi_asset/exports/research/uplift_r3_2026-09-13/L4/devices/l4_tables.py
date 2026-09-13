#!/usr/bin/env python3
"""l4_tables.py -- L4 step 3 (local). Renders receipts/TABLES_L4.md from receipts/RECEIPT_L4_build.json and receipts/RECEIPT_L4_run.json only
(no computation beyond formatting). Usage: python3 l4_tables.py <receipts_dir>
"""
import os, sys, json, math
RD = sys.argv[1]
B = json.load(open(os.path.join(RD, "RECEIPT_L4_build.json"))); R = json.load(open(os.path.join(RD, "RECEIPT_L4_run.json")))
L = []; P = L.append
def f(x, d=3, sign=False):
    if x is None: return "—"
    if isinstance(x, str): return x
    if isinstance(x, bool): return "yes" if x else "no"
    if not math.isfinite(x): return "nan"
    return ("%+.*f" if sign else "%.*f") % (d, x)
SP = ("Y22", "Y23", "Y24", "Y25", "Y26", "S2426", "FULL")
ARMS = R["constants"]["arms"]; PA = R["readings"]["per_arm"]
P("# TABLES · L4 · low-turnover delta-neutral funding carry sleeve (rendered from receipts; units: bps per 4h anchor per unit sleeve capital, m = 0.5)")
P("")
P("Build device sha256 `%s`, run device sha256 `%s`, inputs sha256 `%s`, series sha256 `%s`, PREREG sha256 `%s` (+ AMENDMENT 1)." % (
    B["device_sha256"], R["device_sha256"], R["inputs_sha256"], R.get("series_sha256"), R["prereg_sha256"]))
P("")
P("## T0 Gates")
P("| gate | pass | key readings |"); P("|---|---|---|")
g = B["gates"]
P("| G-IN | %s | %d inputs hashed, all known values equal |" % (f(g["G-IN"]["pass_"]), len(g["G-IN"]["detail"])))
P("| G-ALIGN | %s | %s |" % (f(g["G-ALIGN"]["pass_"]), ", ".join("%s=%s" % (k, v) for k, v in g["G-ALIGN"]["detail"].items() if k not in ("fund_missing",))))
P("| G-A0 | %s | %s |" % (f(g["G-A0"]["pass_"]), "; ".join("%s got %.10f want %s" % (k, v["got"], v["want"]) for k, v in g["G-A0"]["detail"].items())))
d = g["G-FUND"]["detail"]
P("| G-FUND | %s | zips %d (404 %d); fund_aug events in zip months %d, matched %d (%.4f), rate \\|Δ\\| ≤ 1e-9 %.4f of matched (max \\|Δ\\| %.2e); api unmatched %d, vision unmatched %d; spacing = interval column %.4f of %d |" % (
    f(g["G-FUND"]["pass_"]), d["zips"], d["zip_404"], d["api_events_in_zip_months"], d["matched"], d["matched_share_of_api"], d["rate_eq_share_of_matched"], d["max_abs_drate"],
    d["api_unmatched"], d["vision_unmatched"], d["interval_agree_share"], d["interval_compared"]))
d = g["G-SETT"]["detail"]
P("| G-SETT | %s | %d shared anchors %s..%s; compared cells %d, max \\|Δ\\| %.2e, presence mismatches %d (excluded cells %d, of which presence-mismatched %d) |" % (
    f(g["G-SETT"]["pass_"]), d["shared_anchors"], d["first"], d["last"], d["cells_compared"], d["max_abs_diff"], d["presence_mismatch"], d["excluded_cells"], d["presence_mismatch_in_excluded"]))
d = g["G-UNITS"]["detail"]
P("| G-UNITS | %s | (i) 8h events \\|rate\\| ≥ 10 bps: sign agreement with p_tw8 +: %.4f (n %d), −: %.4f (n %d); (ii) Spearman(b1, p_last) %.3f (n %d, \\|p\\| ≥ 10 bps), median b1/p_last %.3f (n %d, \\|p\\| ≥ 20 bps) |" % (
    f(g["G-UNITS"]["pass_"]), d["i_funding_sign_vs_p_tw8"]["agree_pos"], d["i_funding_sign_vs_p_tw8"]["n_pos"], d["i_funding_sign_vs_p_tw8"]["agree_neg"], d["i_funding_sign_vs_p_tw8"]["n_neg"],
    d["ii_b1_vs_b2"]["spearman_b1_p_last"], d["ii_b1_vs_b2"]["n_cells_p10"], d["ii_b1_vs_b2"]["median_ratio_b1_over_p_last"], d["ii_b1_vs_b2"]["n_cells_p20"]))
rg = R["gates"]
P("| G-SYN | %s | %d world×arm cases vs independent reference, all positions equal %s, max acct diff %.1e; explicit %s |" % (
    f(rg["G-SYN"]["pass_"]), len(rg["G-SYN"]["detail"]["cases"]), all(c["positions_equal"] for c in rg["G-SYN"]["detail"]["cases"]),
    max(c["max_abs_acct_diff"] for c in rg["G-SYN"]["detail"]["cases"]), json.dumps(rg["G-SYN"]["detail"]["explicit"])))
gc = rg["G-CAUSAL"]["detail"]
P("| G-CAUSAL | %s | 20 cuts: future-perturbed positions identical %d/20; negative control changed positions at the cut in %d/20 draws (arms changed per draw: %s) |" % (
    f(rg["G-CAUSAL"]["pass_"]), sum(x["future_perturbed_positions_identical"] for x in gc["draws"]), gc["neg_changed_draws"], [x["neg_control_arms_changed_at_cut"] for x in gc["draws"]]))
ga = rg["G-ACCT"]["detail"]
P("| G-ACCT | %s | max identity %.1e, turnover-vs-holds %.1e, telescope %.1e, basis total vs holds %.1e, NaN marks %d |" % (
    f(rg["G-ACCT"]["pass_"]), max(v["identity"] for v in ga.values()), max(v["turnover_vs_holds"] for v in ga.values()), max(v["telescope_max"] for v in ga.values()),
    max(v["basis_total_vs_holds"] for v in ga.values()), sum(v["basis_nan_marks"] for v in ga.values())))
c = B["counts"]
P(""); P("Funding records %d (dropped outside grid %d, same-hour duplicate records %d, second-of-hour-1 %d); spot/eligibility cells in W: %s." % (
    c["funding"]["records"], c["funding"]["dropped_outside_grid"], c["funding"]["same_hour_dup_records"], c["funding"]["sec1_records"], json.dumps(c["spot_elig_basis"])))
V = R["verdict"]
P(""); P("## T1 Verdict under the frozen rule (PREREG §5, base cost c_spot = 10, B2 marking)")
P("**Study verdict: %s** — arms PASS_adj %s; arms PASS_unadj %s; nested PASS %s." % (V["study"], V["arms_PASS_adj"] or "none", V["arms_PASS_unadj"] or "none", f(V["nested_PASS"])))
P(""); P("| arm | h_in | h_out | min_hold | K | S2426 net [CI95] · Bonf-12 lower | S2426 SR | S2426 pos share | P0 | P1 (years applying: net) | P2a | P2b | ρ FULL anchor/day s42 · s2027 | P3 | PASS_adj | PASS_unadj |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for a in ARMS:
    r = PA[a["id"]]; t = r["R1"]["S2426"]; ru = r["rule"]; rh = r["R4"]
    yrs = ", ".join("%s %s" % (y, f(v["net_mean"], 3, True)) for y, v in ru["P1_years"].items() if v["applies"]) or "none"
    P("| %s | %g | %g | %d | %d | %s [%s, %s] · %s | %s | %s | %s | %s (%s) | %s | %s | %s/%s · %s/%s | %s | **%s** | %s |" % (
        a["id"], a["h_in"], a["h_out"], a["min_hold"], a["K"], f(t["net_mean"], 4, True), f(t["ci"]["q2.5000"], 4, True), f(t["ci"]["q97.5000"], 4, True), f(t["ci"]["q0.2083"], 4, True),
        f(t["sharpe"], 2), f(t["position_share"], 3), f(ru["P0"]), f(ru["P1"]), yrs, f(ru["P2a"]), f(ru["P2b"]),
        f(rh["42"]["FULL"]["per_anchor"], 3, True), f(rh["42"]["FULL"]["per_day"], 3, True), f(rh["2027"]["FULL"]["per_anchor"], 3, True), f(rh["2027"]["FULL"]["per_day"], 3, True),
        f(ru["P3"]), f(ru["PASS_adj"]), f(ru["PASS_unadj"])))
P(""); P("## T2 Per-year table (per arm; CI95 = 30-day circular block bootstrap of the mean)")
P("| arm | span | n | net mean [CI95] | income | basis | cost | turnover | deployed | position share | empty share | no-candidate share | Sharpe | σ | maxDD % | APR % | completed holds | median hold (anchors) | forced a/b/c |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for a in ARMS:
    for s in SP:
        t = PA[a["id"]]["R1"][s]; ci = t.get("ci", {})
        P("| %s | %s | %d | %s [%s, %s] | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %d | %s | %d/%d/%d |" % (
            a["id"], s, t["n"], f(t["net_mean"], 4, True), f(ci.get("q2.5000"), 4, True), f(ci.get("q97.5000"), 4, True), f(t["inc_mean"], 4, True), f(t["bas_mean"], 4, True), f(t["cost_mean"], 4),
            f(t["turnover_mean"], 5), f(t["deployed_share"], 3), f(t["position_share"], 3), f(t["empty_share"], 3), f(t["no_candidate_share"], 3), f(t["sharpe"], 2), f(t["sigma"], 3),
            f(t["maxdd_pct"], 2), f(t["apr_pct"], 2, True), t["completed_holds"], f(t["median_hold_anchors"], 1), t["forced_exits"]["forced_a"], t["forced_exits"]["forced_b"], t["forced_exits"]["forced_c"]))
P(""); P("## T3 Break-even per unit notional turnover (bps; assumed all-in 13.92 = 3.92 perp + 10 spot)")
P("| arm | " + " | ".join("%s all-in / spot / income-only" % s for s in SP) + " |"); P("|---|" + "---|" * len(SP))
for a in ARMS:
    P("| %s | " % a["id"] + " | ".join("%s / %s / %s" % (f(PA[a["id"]]["R1"][s]["breakeven_allin"], 1), f(PA[a["id"]]["R1"][s]["breakeven_spot"], 1), f(PA[a["id"]]["R1"][s]["breakeven_income_only"], 1)) for s in SP) + " |")
P(""); P("## T4 Correlation with A0 (Pearson; per anchor / per UTC day)")
P("| arm | seed | " + " | ".join(SP) + " |"); P("|---|---|" + "---|" * len(SP))
for a in ARMS:
    for sd in ("42", "2027"):
        P("| %s | s%s | " % (a["id"], sd) + " | ".join("%s / %s" % (f(PA[a["id"]]["R4"][sd][s]["per_anchor"], 3, True), f(PA[a["id"]]["R4"][sd][s]["per_day"], 3, True)) for s in SP) + " |")
P(""); P("## T5 Combination with A0 (A0 per capital = 2.0 × g). EC = 0.5·A0 + 0.5·sleeve (equal capital). EV = equal vol, feasible only if λ_needed ≤ k_max = 1.8 (spot leg ≤ 3×)")
P("| arm | seed | span | A0 SR | EC SR | ΔSR [CI95] | EC mean / A0 mean | EC maxDD / A0 maxDD % | λ_needed | EV SR |")
P("|---|---|---|---|---|---|---|---|---|---|")
for a in ARMS:
    for sd in ("42", "2027"):
        for s in SP:
            v = PA[a["id"]]["R5"][sd][s]; pr = v.get("paired", {})
            P("| %s | s%s | %s | %s | %s | %s [%s, %s] | %s / %s | %s / %s | %s | %s |" % (
                a["id"], sd, s, f(v["A0_sharpe"], 2), f(v["EC_sharpe"], 2), f(v["dSR"], 2, True), f((pr.get("dSR_ci95") or [None, None])[0], 2, True), f((pr.get("dSR_ci95") or [None, None])[1], 2, True),
                f(v["EC_mean"], 3, True), f(v["A0_mean"], 3, True), f(v["EC_maxdd_pct"], 1), f(v["A0_maxdd_pct"], 1), f(v["EV_lambda_needed"], 2), f(v["EV_sharpe"], 2) if not isinstance(v["EV_sharpe"], str) else v["EV_sharpe"]))
N = R["readings"]["nested"]
P(""); P("## T6 T6 framing: nested walk-forward selection over the 12 arms, DSR, EC increment")
P("| segment | train n | selected | OOS net mean | OOS SR | OOS position share | training SR by arm A01..A12 |"); P("|---|---|---|---|---|---|---|")
for s_ in N["segments"]:
    P("| %s | %d | %s | %s | %s | %s | %s |" % (s_["segment"], s_["train_n"], s_["selected"], f(s_["oos_net_mean"], 4, True), f(s_["oos_sharpe"], 2), f(s_["oos_position_share"], 3), " ".join(f(x, 2) for x in s_["train_sharpe"])))
P(""); P("Nested years: " + "; ".join("%s net %s SR %s pos %s" % (y, f(v["net_mean"], 4, True), f(v["sharpe"], 2), f(v["position_share"], 3)) for y, v in N["years"].items()))
P("Nested S2426: net %s [%s, %s], SR %s, position share %s; ρ nested span s42 %s/%s, s2027 %s/%s; P0 %s P1 %s P2a %s P3 %s ⇒ **Nested PASS %s**" % (
    f(N["S2426"]["net_mean"], 4, True), f(N["S2426"]["ci"]["q2.5000"], 4, True), f(N["S2426"]["ci"]["q97.5000"], 4, True), f(N["S2426"]["sharpe"], 2), f(N["S2426"]["position_share"], 3),
    f(N["rho_nested_span"]["42"]["per_anchor"], 3, True), f(N["rho_nested_span"]["42"]["per_day"], 3, True), f(N["rho_nested_span"]["2027"]["per_anchor"], 3, True), f(N["rho_nested_span"]["2027"]["per_day"], 3, True),
    f(N["P0"]), f(N["P1"]), f(N["P2a"]), f(N["P3"]), f(N["PASS"])))
for sd, v in N["EC_increment_nested_span"].items():
    P("EC increment (nested sleeve + A0 s%s vs A0, nested span): EC SR %s vs A0 SR %s, ΔSR %s [%s, %s], Δmean CI95 [%s, %s]" % (
        sd, f(v["EC_sharpe"], 2), f(v["A0_sharpe"], 2), f(v["dSR"], 2, True), f(v["dSR_ci95"][0], 2, True), f(v["dSR_ci95"][1], 2, True), f(v["dmean_ci95"][0], 3, True), f(v["dmean_ci95"][1], 3, True)))
Dd = R["readings"]["dsr"]
P("DSR (best S2426 arm %s, SR %s, T %d, skew %s, kurt %s, arms with variance %d): PSR(0) %s; P(true SR > 0) at N_eff %s (%s) / N 12 %s / N 18 %s; SR0 annual %s / %s / %s" % (
    Dd["best_arm"], f(Dd["SR_annual"], 2), Dd["T"], f(Dd["skew"], 2), f(Dd["kurt"], 1), Dd["arms_with_variance"], f(Dd["PSR_0"], 4), f(Dd["P_true_SR_gt_0_N_eff"], 4), f(Dd["N_eff"], 2),
    f(Dd["P_true_SR_gt_0_N_12"], 4), f(Dd["P_true_SR_gt_0_N_18"], 4), f(Dd["SR0_annual_N_eff"], 2), f(Dd["SR0_annual_N_12"], 2), f(Dd["SR0_annual_N_18"], 2)))
P(""); P("## T7 2023 reading (descriptive; 'adds' = Y23 net > 0 and Y23 ΔSR(EC − A0) > 0 for both seeds)")
P("| arm | Y23 net | Y23 position share | ΔSR s42 | ΔSR s2027 | adds in 2023 |"); P("|---|---|---|---|---|---|")
for a in ARMS:
    r7 = PA[a["id"]]["R7"]
    P("| %s | %s | %s | %s | %s | %s |" % (a["id"], f(r7["Y23_net_mean"], 4, True), f(r7["Y23_position_share"], 3), f(r7["Y23_dSR_EC_minus_A0"]["42"], 2, True), f(r7["Y23_dSR_EC_minus_A0"]["2027"], 2, True), f(r7["adds_in_2023"])))
P(""); P("## T8 Sensitivities (descriptive; same positions)")
P("| arm | c_spot 5: S2426 net [CI95] SR · PASS_adj/unadj | c_spot 15: S2426 net [CI95] SR · PASS_adj/unadj | basis excluded S2426 net / SR · FULL net | B1 marking S2426 net / SR · FULL net (NaN marks) · corr(B1,B2 basis) | m=1.0 EC SR S2426 s42 | S2426 CI95 iid-day · 7-day |")
P("|---|---|---|---|---|---|---|")
for a in ARMS:
    s8 = PA[a["id"]]["R8"]; c5 = s8["c_spot_5"]; c15 = s8["c_spot_15"]; bx = s8["basis_excluded"]; b1 = s8["B1_marking"]
    P("| %s | %s [%s, %s] %s · %s/%s | %s [%s, %s] %s · %s/%s | %s / %s · %s | %s / %s · %s (%d) · %s | %s | [%s, %s] · [%s, %s] |" % (
        a["id"], f(c5["table"]["S2426"]["net_mean"], 4, True), f(c5["table"]["S2426"]["ci"]["q2.5000"], 4, True), f(c5["table"]["S2426"]["ci"]["q97.5000"], 4, True), f(c5["table"]["S2426"]["sharpe"], 2), f(c5["rule"]["PASS_adj"]), f(c5["rule"]["PASS_unadj"]),
        f(c15["table"]["S2426"]["net_mean"], 4, True), f(c15["table"]["S2426"]["ci"]["q2.5000"], 4, True), f(c15["table"]["S2426"]["ci"]["q97.5000"], 4, True), f(c15["table"]["S2426"]["sharpe"], 2), f(c15["rule"]["PASS_adj"]), f(c15["rule"]["PASS_unadj"]),
        f(bx["S2426"]["net_mean"], 4, True), f(bx["S2426"]["sharpe"], 2), f(bx["FULL"]["net_mean"], 4, True), f(b1["spans"]["S2426"]["net_mean"], 4, True), f(b1["spans"]["S2426"]["sharpe"], 2), f(b1["spans"]["FULL"]["net_mean"], 4, True),
        b1["nan_marks"], f(b1["corr_basis_B1_B2_invested"], 3, True), f(s8["m_1.0"]["combo"]["42"]["S2426"]["EC_sharpe"], 2),
        f(s8["ci_S2426_iid_day"]["q2.5000"], 4, True), f(s8["ci_S2426_iid_day"]["q97.5000"], 4, True), f(s8["ci_S2426_7day"]["q2.5000"], 4, True), f(s8["ci_S2426_7day"]["q97.5000"], 4, True)))
P(""); P("## T9 Descriptives")
P("| arm | distinct names held | held name-anchor cells | interval mix by true spacing 1h/2h/4h/8h | median log(spot/perp 24h qv) | duplicate-event cells held | exits with stale B2 |"); P("|---|---|---|---|---|---|---|")
for a in ARMS:
    d = PA[a["id"]]["desc"]; im = d["interval_mix_by_spacing"] or {}
    P("| %s | %d | %d | %s/%s/%s/%s | %s | %d | %d |" % (a["id"], d["distinct_names_held"], d["held_name_anchor_cells"], f(im.get("1.0"), 3), f(im.get("2.0"), 3), f(im.get("4.0"), 3), f(im.get("8.0"), 3),
                                                     f(d["median_qvr24_held"], 2, True), d["dup_event_cells_held"], d["exits_with_stale_b2"]))
P(""); P("No-candidate share by h_in: " + "; ".join("h_in %s: %s" % (h, ", ".join("%s %s" % (s, f(v, 3)) for s, v in d_.items())) for h, d_ in R["readings"]["no_candidate_share"].items()))
open(os.path.join(RD, "TABLES_L4.md"), "w").write("\n".join(L) + "\n")
print("SUMMARY l4_tables lines=%d verdict=%s" % (len(L), V["study"]))
