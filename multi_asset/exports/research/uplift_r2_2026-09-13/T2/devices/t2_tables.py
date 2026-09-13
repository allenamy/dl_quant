#!/usr/bin/env python3
"""t2_tables.py — render receipts/TABLES_T2.md from RECEIPT_T2_kappa_main.json, RECEIPT_T2_drive.json, RECEIPT_T2_judge.json
(and RECEIPT_T2_tripwire.json if present). Pure formatting: every number comes from a receipt. Local:
  env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t2_tables.py <T2 dir>
"""
import json, os, sys, hashlib
T2 = sys.argv[1]; RC = T2 + "/receipts"
K = json.load(open(RC + "/RECEIPT_T2_kappa_main.json")); D = json.load(open(RC + "/RECEIPT_T2_drive.json")); J = json.load(open(RC + "/RECEIPT_T2_judge.json"))
KG = json.load(open(RC + "/RECEIPT_T2_kappa_garbled.json")) if os.path.exists(RC + "/RECEIPT_T2_kappa_garbled.json") else None
TR = json.load(open(RC + "/RECEIPT_T2_tripwire.json")) if os.path.exists(RC + "/RECEIPT_T2_tripwire.json") else None
L = []; P = L.append
f = lambda x, n=4: ("%+.*f" % (n, x)) if isinstance(x, (int, float)) and x is not None else str(x)
u = lambda x, n=4: ("%.*f" % (n, x)) if isinstance(x, (int, float)) and x is not None else str(x)
ci = lambda c, n=4: "[%s, %s]" % (f(c[0], n), f(c[1], n))
P("# TABLES_T2 (rendered from receipts by devices/t2_tables.py; do not edit by hand)\n")
P("Receipt sha256: kappa_main %s · drive %s · judge %s\n" % tuple(hashlib.sha256(open(RC + x, "rb").read()).hexdigest()[:16] for x in ("/RECEIPT_T2_kappa_main.json", "/RECEIPT_T2_drive.json", "/RECEIPT_T2_judge.json")))
# ---------------------------------------------------------------- T1 gates
P("## T1 · Gates (PREREG §4)\n")
P("| gate | run | reference | rec bitwise | W bitwise | extra |"); P("|---|---|---|---|---|---|")
for k, v in D["gate"]["P"].items():
    if k == "PASS": continue
    P("| GATE P | %s | %s | %s | %s | cols equal %s, T2_MODE %s |" % (k, v["ref"], v["rec"]["bitwise"], v["W"]["bitwise"], v["cols_equal"], v["cfg_T2_mode"]))
for k, v in D["gate"]["PC0"].items():
    if k == "PASS": continue
    ex = ("anchors through the rank path %s" % v["anchors_through_rank_path"]) if v["anchors_through_rank_path"] is not None else ("seat kappa values used %s" % v["seat_kappa_unique"])
    P("| PC-0 | %s | %s | %s | %s | %s |" % (k, v["ref"], v["rec"]["bitwise"], v["W"]["bitwise"], ex))
for k, v in D["gate"]["PC1"].items():
    if k == "PASS": continue
    P("| PC-1 | %s | %s | %s | %s | Δg vs A0 W_ALPHA %s → %s (target %s, match %s) |" % (k, v["ref"], v["rec"]["bitwise"], v["W"]["bitwise"], f(v["dg_vs_A0_W_ALPHA"], 7), v["dg_4dp"], v["target"], v["dg_matches_target"]))
for k, v in D["gate"]["WIRE"].items():
    if k == "PASS": continue
    nb = sum(1 for r in v["b_rows"] if r["bitwise"])
    P("| WIRE | %s | independent re-implementation | — | — | (a) g differs on %.1f%% of W_ALPHA anchors (pass %s); (b) FZ_book bitwise %d/12 (pass %s) |" % (k, 100 * v["frac_W_ALPHA_anchors_g_differs"], v["a_pass"], nb, v["b_pass"]))
P("\nPASS: GATE P %s · PC-0 %s · PC-1 %s · WIRE %s · C1 %s · C2 path %s · C2 baseline %s · C2 arms %s\n" % (D["gate"]["P"]["PASS"], D["gate"]["PC0"]["PASS"], D["gate"]["PC1"]["PASS"], D["gate"]["WIRE"]["PASS"], K["C1"]["PASS"], D["C2"]["path"]["PASS"], D["C2"]["baseline_PASS"], D["C2"]["arm_PASS"]))
P("C1 checks (estimate at T bitwise after garbling every y4 row with E_ts > T−8h and every panel funding row with ts > T−8h):\n")
P("| refit T | garbled y4 rows | garbled panel rows | scalar | σ bins | diagnostics |"); P("|---|---|---|---|---|---|")
for c in K["C1"]["checks"]: P("| %s | %d | %d | %s | %s | %s |" % (c["T_iso"], c["garbled_y4_rows"], c["garbled_panel_rows"], c["bitwise_scalar"], c["bitwise_sigma"], c["bitwise_diagnostics"]))
G = D["C2"]["garbled_tree"]
P("\nC2 garbled tree (T* %s): y4 rows permuted %d (past bitwise %s, NaN pattern kept %s, future cells changed %d); panel rows permuted %d (past bitwise %s, future cells changed %d). Path bitwise for E_ts ≤ T*: %s; future path cells that differ: %d.\n" % (
    G["TSTAR"], G["y4_rows_permuted"], G["past_y4_bitwise"], G["future_y4_nan_pattern_kept"], G["future_y4_changed_cells"], G["panel_rows_permuted"], G["past_panel_bitwise"], G["future_panel_changed_cells"],
    {k: v for k, v in D["C2"]["path"].items() if k not in ("PASS", "future_path_differs_cells")}, D["C2"]["path"]["future_path_differs_cells"]))
P("| garbled run | real run | rows ≤ T* | W ≤ T* bitwise | rec non-y4 cols ≤ T* | rec all cols < T* | PASS |"); P("|---|---|---|---|---|---|---|")
for k, v in D["C2"]["runs"].items():
    P("| %s | %s | %d | %s | %s | %s | %s |" % (k, v["real"], v["n_rows_le_TSTAR"], v.get("W_le_TSTAR", {}).get("bitwise"), v.get("rec_non_y4_cols_le_TSTAR", {}).get("bitwise"), v.get("rec_all_cols_lt_TSTAR", {}).get("bitwise"), v["PASS"]))
# ---------------------------------------------------------------- T2 kappa path
P("\n## T2 · κ* path (monthly refit, expanding window, estimate at T uses E_ts ≤ T−8h; y winsorised ±0.20 for estimation only)\n")
P("| refit T | anchors | obs | λ̂ (return/rank) | SE_day λ̂ | b̂ | κ*_raw | SE_day b̂ | κ* used | active | σ-bin κ_raw (low/mid/high) | per-side κ⁺ / κ⁻ raw (SE b⁺ / b⁻) | unwinsorised κ_raw |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for e in K["refits"]:
    if not e.get("ok"): P("| %s | %d | — | — | — | — | — | — | — | False | — | — | — |" % (e["T_iso"], e["n_anchors"])); continue
    sg = e["sigma"]; sb = " / ".join("%.2f" % b["kappa_raw"] for b in sg["bins"]) if sg.get("ok") else "—"
    sd = e.get("d2_side") or {}; d1 = e.get("d1_raw") or {}
    P("| %s | %d | %d | %.2e | %.2e | %.3f | %.3f | %.3f | %.3f | %s | %s | %.2f / %.2f (%.2f / %.2f) | %.3f |" % (e["T_iso"], e["n_anchors"], e["n_obs"], e["lam"], e["se_day_lam"], e["b"], e["kappa_raw"], e["se_day_b"], e["kappa"], e["active"], sb,
      sd.get("kappa_plus_raw", float("nan")), sd.get("kappa_minus_raw", float("nan")), sd.get("se_day_b_plus", float("nan")), sd.get("se_day_b_minus", float("nan")), d1.get("kappa_raw", float("nan"))))
S = K["W_ALPHA_summary"]; M1 = K["M1_final_refit"]
P("\n**W_ALPHA path summary:** scalar active %d/%d anchors; κ* mean %.3f (min %.3f, max %.3f); first half %.3f, second half %.3f; anchors where κ*_raw > 1 was clipped to 1: %d; κ*_raw < 0 clipped to 0: %d; λ̂ floored at 0 (fund score ranked on −κ*·carry alone): %d; refits used %d. σ variant active %d anchors; κ* mean by bin (low/mid/high σ) %s; anchors by bin %s.\n" % (
    S["scalar_active"], S["n_mask"], S["scalar_kappa_mean"], S["scalar_kappa_min"], S["scalar_kappa_max"], S["scalar_kappa_mean_first_half"], S["scalar_kappa_mean_second_half"], S["anchors_clip_hi"], S["anchors_clip_lo"], S["anchors_lam_floor"], S["n_refits_used"], S["sigma_active"], S["sigma_kappa_mean_by_bin"], S["sigma_anchors_by_bin"]))
P("**M1 (final refit %s):** κ*_raw %.3f, CI95 (day clusters) %s, SE_day b̂ %.3f / SE_week %.3f; λ̂ %.2e (SE %.2e). Inside (0,1): %s; excludes 0: %s; excludes 1: %s. Per side: κ⁺_raw %.2f (SE b⁺ %.2f), κ⁻_raw %.2f (SE b⁻ %.2f). Unwinsorised κ_raw %.3f (SE %.3f).\n" % (
    M1["T_iso"], M1["kappa_raw"], ci(M1["ci95_day"], 3), M1["se_day_b"], M1["se_week_b"], M1["lam"], M1["se_day_lam"], M1["ci_inside_0_1"], M1["ci_excludes_0"], M1["ci_excludes_1"], M1["d2_side"]["kappa_plus_raw"], M1["d2_side"]["se_day_b_plus"], M1["d2_side"]["kappa_minus_raw"], M1["d2_side"]["se_day_b_minus"], M1["d1_raw"]["kappa_raw"], M1["d1_raw"]["se_day_b"]))
P("**d3 yearly refit (diagnostic):** " + "; ".join("%s κ_raw %.3f (SE %.3f, λ̂ %.1e)" % (e["T_iso"], e["kappa_raw"], e["se_day_b"], e["lam"]) for e in K["d3_yearly"]) + "; W_ALPHA mean κ* %.3f (%d anchors in 2022 have no yearly estimate).\n" % (K["d3_yearly_W_ALPHA"]["kappa_mean"], K["d3_yearly_W_ALPHA"]["anchors_without_yearly_estimate"]))
d4 = K["d4_live_window"]; e4 = d4["estimate"]
P("**d4 live window %s (r6 extension tree, prefix bitwise %s, umask carried forward on %d panel rows; %d anchors, %d obs, %d day clusters):** b̂ %.3f, κ_raw %.3f, CI95 %s (SE_day %.3f, SE_week %.3f); λ̂ %.2e (SE %.2e); per side κ⁺_raw %.2f (SE b⁺ %.2f), κ⁻_raw %.2f (SE b⁻ %.2f). %s\n" % (
    d4["window"], d4["prefix_all_equal"], d4["umask_carry_forward_panel_rows"], e4["n_anchors"], e4["n_obs"], e4["n_days"], e4["b"], e4["kappa_raw"], ci(e4["kappa_raw_ci95_day"], 3), e4["se_day_b"], e4["se_week_b"], e4["lam"], e4["se_day_lam"],
    e4["d2_side"]["kappa_plus_raw"], e4["d2_side"]["se_day_b_plus"], e4["d2_side"]["kappa_minus_raw"], e4["d2_side"]["se_day_b_minus"], d4["caveat"]))
# ---------------------------------------------------------------- T3.. results
R = J["results"]; DEC = J["decisions"]
def headline(base, win, title):
    P("\n## %s\n" % title)
    P("| arm | seed | reference | Δg | CI95 | CI99-K (K=3) | Δpnl | Δcarry | Δcost | Δpnl/Δcarry | carry arm / base | τ matched arm / base | Δτ %% | Sharpe arm / base | ΔSharpe |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for a, v in R.items():
        for s in ("42", "2027"):
            o = v["bases"][base][s][win]
            P("| %s | s%s | %s | **%s** | %s | %s | %s | %s | %s | %s | %s / %s | %s / %s | %+.1f%% | %s / %s | %s |" % (v["label"], s, o["reference"], f(o["dg"]), ci(o["ci95"]), ci(o["ci99K"]), f(o["dpnl"]), f(o["dcarry"]), f(o["dcost"]),
              u(o["price_given_up_per_unit_carry_saved"], 2) if o["price_given_up_per_unit_carry_saved"] is not None else "—", u(o["carry_arm"]), u(o["carry_base"]), u(o["tau_matched_arm"], 5), u(o["tau_matched_base"], 5), o["dtau_pct"],
              u(o["sharpe_arm"], 3), u(o["sharpe_base"], 3), f(o["dsharpe"], 3) if o["dsharpe"] is not None else "—"))
headline("A0", "W_ALPHA", "T3 · Headline — A0 base, W_ALPHA n=9138 (verdict window)")
headline("A0", "KING_LIVE", "T4 · KING_LIVE (W_ALPHA ∩ ts ≥ 2024-01-01, n=5838) — A0 base")
headline("NW", "W_ALPHA", "T5 · NW base (candidate new baseline), W_ALPHA — robustness reading, not a verdict")
P("\n## T6 · Tail — W_TAIL n=10038, fixed 2.0× NAV, UTC-day compounding, NAV prepend 1.0\n")
P("| arm | base | seed | maxDD arm / base | peak→trough arm | worst day arm (ret) | worst day base (ret) | HALT arm / base | ALERT arm / base | sd_day arm / base | ann ret arm / base |"); P("|---|---|---|---|---|---|---|---|---|---|---|")
for a, v in R.items():
    for b in ("A0", "NW"):
        for s in ("42", "2027"):
            ta, tb = v["bases"][b][s]["tail_arm"], v["bases"][b][s]["tail_base"]
            P("| %s | %s | s%s | %.4f / %.4f | %s→%s | %s (%.4f) | %s (%.4f) | %d / %d | %d / %d | %.4f / %.4f | %.4f / %.4f |" % (v["label"], b, s, ta["maxdd"], tb["maxdd"], ta["maxdd_peak"], ta["maxdd_trough"], ta["worst_day"], ta["worst_day_ret"], tb["worst_day"], tb["worst_day_ret"], ta["halt"], tb["halt"], ta["alert"], tb["alert"], ta["sd_day"], tb["sd_day"], ta["ann_ret"], tb["ann_ret"]))
P("\n## T7 · Per calendar year on W_ALPHA (g and Sharpe; bps/anchor/unit gross)\n")
P("| arm | base | seed | year | n | g arm | g base | Δg | Sharpe arm | Sharpe base | Δcarry | Δpnl |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|")
for a, v in R.items():
    for b in ("A0", "NW"):
        for s in ("42", "2027"):
            for y, o in v["bases"][b][s]["per_year"].items():
                P("| %s | %s | s%s | %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (v["label"], b, s, y, o["n"], f(o["g_arm"]), f(o["g_base"]), f(o["dg"]), u(o["sharpe_arm"], 3), u(o["sharpe_base"], 3), f(o["dcarry"]), f(o["dpnl"])))
P("\n## T8 · Live window on the replay (2026-08-26 00Z → 2026-08-30 20Z, n=30, 5 UTC days; CI uninformative by construction)\n")
P("| arm | base | seed | g arm | g base | Δg | CI95 (5 days) | Δpnl | Δcarry | Δcost |"); P("|---|---|---|---|---|---|---|---|---|---|")
for a, v in R.items():
    for b in ("A0", "NW"):
        for s in ("42", "2027"):
            o = v["bases"][b][s]["W_LIVE_REPLAY"]
            P("| %s | %s | s%s | %s | %s | %s | %s | %s | %s | %s |" % (v["label"], b, s, f(o["g_arm"]), f(o["g_base"]), f(o["dg"]), ci(o["ci95"]), f(o["dpnl"]), f(o["dcarry"]), f(o["dcost"])))
P("\n## T9 · Δg by the anchor's causal σ_fund tercile (bins of the ARM-Nσ path), A0 base, W_ALPHA — descriptive\n")
P("| arm | seed | low σ: n / Δg [CI95] | mid σ | high σ |"); P("|---|---|---|---|---|")
for a, v in R.items():
    for s in ("42", "2027"):
        bb = v["bases"]["A0"][s]["sigma_bins"]
        cell = lambda o: ("%d / %s %s" % (o["n"], f(o["dg"]), ci(o["ci95"]))) if "dg" in o else ("n %d" % o["n"])
        P("| %s | s%s | %s | %s | %s |" % (v["label"], s, cell(bb["0"] if "0" in bb else bb[0]), cell(bb["1"] if "1" in bb else bb[1]), cell(bb["2"] if "2" in bb else bb[2])))
P("\n## T10 · What the arms did to the book (A0 base, W_ALPHA)\n")
for a, v in R.items():
    for s in ("42", "2027"):
        o = v["bases"]["A0"][s]
        if o["name_aux"]:
            n = o["name_aux"]; P("- %s s%s: rank path used on %.1f%% of anchors; fund score ranked on −κ*·carry alone (λ̂ floored) on %.1f%%; names whose fund score changed per anchor %.1f; mean |ΔFZ| %.4f; mean corr(FZ_book, FZ) %.3f; mean κ* %.3f." % (
                v["label"], s, 100 * n["frac_anchors_path_used"], 100 * n["frac_anchors_lam_zero_pure_carry_rank"], n["mean_n_fz_changed"], n["mean_abs_dfz_used"] or float("nan"), n["mean_corr_fz_book_vs_fz_used"] or float("nan"), n["kappa_mean_used"] or float("nan")))
        if o["seat_path"]:
            sp = o["seat_path"]; P("- %s s%s: w3_king arm %.3f vs base %.3f (p10/p50/p90 arm %s, base %s); mean |Δw3_king| %.3f; mean κ used %.3f; by year %s." % (
                v["label"], s, sp["w3_king_arm"], sp["w3_king_base"], [round(x, 2) for x in sp["pct_arm"]], [round(x, 2) for x in sp["pct_base"]], sp["mean_abs_dw3_king"], sp["kappa_seat_mean"] if sp["kappa_seat_mean"] is not None else float("nan"), {y: (round(z["arm"], 2), round(z["base"], 2)) for y, z in sp["by_year"].items()}))
P("\n## T11 · Decisions (PREREG §6.2; verdict = A0 base; NW = robustness reading)\n")
P("| arm | A0 verdict | flags | clauses (s42 / s2027) | M2 carry reduced | tripwire | NW reading | deployability |"); P("|---|---|---|---|---|---|---|---|")
for a, v in DEC.items():
    c = v["A0_verdict"]["clauses"]
    cl = "CI95 lo>0 %s/%s; maxDD not worse %s/%s; HALT not worse %s/%s; C2 %s" % (c["ci95_lo_gt0"]["42"], c["ci95_lo_gt0"]["2027"], c["maxdd_not_worse_point"]["42"], c["maxdd_not_worse_point"]["2027"], c["halt_not_worse_point"]["42"], c["halt_not_worse_point"]["2027"], c["c2_pass"])
    P("| %s | **%s** | %s | %s | %s | %s | %s | %s |" % (R[a]["label"], v["A0_verdict"]["verdict"], ", ".join(v["A0_verdict"]["flags"]) or "—", cl, v["A0_verdict"]["mechanism_M2_carry_reduced_both_seeds"], v["tripwire_state"], v["NW_reading"]["verdict"], v["deployability"]))
P("\nBaselines (W_ALPHA): " + "; ".join("%s g %.4f Sharpe %.4f τ %.5f carry %.4f" % (k, x["W_ALPHA"]["g"], x["W_ALPHA"]["sharpe"], x["W_ALPHA"]["tau"], x["W_ALPHA"]["carry"]) for k, x in J["baselines"].items()) + ". PC-1 judge-recomputed: %s.\n" % J["PC1_judge_recomputed"])
if TR: P("\n## T12 · Ceiling tripwire (§7)\n\n```\n%s\n```\n" % json.dumps(TR.get("arms"), indent=1))
open(RC + "/TABLES_T2.md", "w").write("\n".join(L) + "\n"); print("wrote", RC + "/TABLES_T2.md", len(L), "lines")
