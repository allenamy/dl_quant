#!/usr/bin/env python3
"""r15_tables.py — render RESULT tables verbatim from the receipts (no new statistics). Local, read-only.
Usage: python3 r15_tables.py <r15_structural dir>  -> writes receipts/TABLES_r15.md and prints it."""
import json, sys, os
R = sys.argv[1]; J = json.load(open(f"{R}/receipts/RECEIPT_r15_judge.json")); N = json.load(open(f"{R}/receipts/RECEIPT_r15_nulls.json")); M = json.load(open(f"{R}/receipts/RECEIPT_r15_mechgate.json")); G = json.load(open(f"{R}/receipts/RECEIPT_r15_drive_gateP.json"))
L = []; P = L.append
ARMS = ["F", "S", "SB", "F05", "F20"]; SEEDS = ["42", "2027"]
NAME = {"F": "ARM-F FTPOS=1", "S": "ARM-S SEATNET=1", "SB": "ARM-SB book-path-net seat", "F05": "ARM-F05 FTPOS=1 TH=-5bp", "F20": "ARM-F20 FTPOS=1 TH=-20bp"}
P("## T1 · Headline (W_ALPHA n=9138; Δ = arm − A0, same seed; bps/anchor/unit gross)\n")
P("| arm | seed | Δg | CI95 | CI99-K(K=5) | Δpnl | Δcarry | Δcost | τ_matched arm / A0 | Δτ % | Sharpe arm / A0 | verdict |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|")
for a in ARMS:
    for s in SEEDS:
        w = J["arms"][a][s]["W_ALPHA"]
        P("| %s | s%s | **%+.4f** | [%+.4f, %+.4f] | [%+.4f, %+.4f] | %+.4f | %+.4f | %+.4f | %.5f / %.5f | **%+.2f%%** | %.3f / %.3f | %s |" % (NAME[a], s, w["dg"], *w["ci95"], *w["ci99K"], w["dpnl"], w["dcarry"], w["dcost"], w["tau_matched_arm"], w["tau_matched_A0"], w["dtau_pct"], w["sharpe_arm"], w["sharpe_A0"], J["verdicts"][a]["verdict"]))
P("\n## T2 · KING_LIVE sub-sample (W_ALPHA ∩ ts ≥ 2024-01-01, n=5838)\n")
P("| arm | seed | Δg | CI95 | CI99-K | Δpnl | Δcarry | Δcost | Δτ % | Sharpe arm / A0 |"); P("|---|---|---|---|---|---|---|---|---|---|")
for a in ARMS:
    for s in SEEDS:
        w = J["arms"][a][s]["KING_LIVE"]
        P("| %s | s%s | %+.4f | [%+.4f, %+.4f] | [%+.4f, %+.4f] | %+.4f | %+.4f | %+.4f | %+.2f%% | %.3f / %.3f |" % (NAME[a], s, w["dg"], *w["ci95"], *w["ci99K"], w["dpnl"], w["dcarry"], w["dcost"], w["dtau_pct"], w["sharpe_arm"], w["sharpe_A0"]))
P("\n## T3 · Cost survival: Δg at λ ∈ {1.0, 0.8096, 0.2545} (W_ALPHA; λ=1.0 is the only verdict number)\n")
P("| arm | seed | Δg λ=1.0 | Δg λ=0.8096 | Δg λ=0.2545 | sign stable | g_A0 λ=1 / 0.8096 / 0.2545 | surv_A0(λ=1) → surv_arm(λ=1) |"); P("|---|---|---|---|---|---|---|---|")
for a in ARMS:
    for s in SEEDS:
        w = J["arms"][a][s]["W_ALPHA"]; sv = w["survival"]
        P("| %s | s%s | %+.4f | %+.4f | %+.4f | %s | %.4f / %.4f / %.4f | %.3f → %.3f |" % (NAME[a], s, sv["1.0000"]["dg"], sv["0.8096"]["dg"], sv["0.2545"]["dg"], w["dg_sign_stable_over_lambda"], sv["1.0000"]["g_A0"], sv["0.8096"]["g_A0"], sv["0.2545"]["g_A0"], sv["1.0000"]["surv_A0"], sv["1.0000"]["surv_arm"]))
P("\n## T4 · By year Δg (W_ALPHA; 2022 starts 2022-06-30 after the 900-anchor warm drop)\n")
yrs = sorted(J["arms"]["F"]["42"]["W_ALPHA"]["by_year"].keys(), key=int)
P("| arm | seed | " + " | ".join(yrs) + " | A0 g by year |"); P("|---|---|" + "---|" * len(yrs) + "---|")
for a in ARMS:
    for s in SEEDS:
        by = J["arms"][a][s]["W_ALPHA"]["by_year"]
        P("| %s | s%s | " % (NAME[a], s) + " | ".join("%+.3f" % by[y]["dg"] for y in yrs) + " | " + " / ".join("%+.3f" % by[y]["g_A0"] for y in yrs) + " |")
P("\n## T5 · Tail (W_TAIL n=10038, 2.0× NAV; anchor-compounded maxDD with prepended start)\n")
P("| arm | seed | maxDD arm / A0 | worst day arm | worst day A0 | HALT(≤−4%) arm / A0 | ALERT(≤−2.68%) arm / A0 | sd_day arm / A0 | KING_LIVE maxDD arm / A0 | KL HALT arm / A0 |"); P("|---|---|---|---|---|---|---|---|---|---|")
for a in ARMS:
    for s in SEEDS:
        t = J["arms"][a][s]["tail_WT"]; b = J["A0"][s]["tail_WT"]; tk = J["arms"][a][s]["tail_KL"]; bk = J["A0"][s]["tail_KL"]
        P("| %s | s%s | %.4f / %.4f | %s %.4f | %s %.4f | %d / %d | %d / %d | %.4f / %.4f | %.4f / %.4f | %d / %d |" % (NAME[a], s, t["maxDD"], b["maxDD"], t["worst_day"], t["worst_day_ret"], b["worst_day"], b["worst_day_ret"], t["halt4"], b["halt4"], t["alert268"], b["alert268"], t["sd_day"], b["sd_day"], tk["maxDD"], bk["maxDD"], tk["halt4"], bk["halt4"]))
P("\n## T6 · Nulls (turnover-matched by bisection; target = arm's marginal matched turnover Δτ; RELAB informative, SHIFT weak)\n")
P("| arm | seed | family | dose (F: kill th / S: carry scale) | Δτ null / target | rel err | matched | steps | fire null / arm | Δg null | Δg arm | n_missing anchors |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|")
for a in ("F", "S"):
    for s in SEEDS:
        for fam in ("RELAB1", "RELAB2", "RELAB3", "SHIFT101", "SHIFT503", "SHIFT1009"):
            n = N["nulls"]["%s_s%s_%s" % (a, s, fam)]
            fire = ("%d / %d" % (n["fire_total_WA"], n["fire_target_WA"]) if a == "F" else "|Δw3k| %.4f / %.4f" % (n["fire_S_mean_abs_dw3k"], n["fire_S_target"]))
            P("| %s | s%s | %s%s | %.6f | %+.6f / %+.6f | %+.4f | %s | %d | %s | %+.4f | %+.4f | %d |" % (a, s, fam, " (weak)" if n["weak_family"] else "", n["dose_matched"], n["dtau"], n["dtau_target"], n["dtau_rel_err"], "MATCHED" if n["MATCHED"] else "**UNMATCHED**", n["n_steps"], fire, n["dg"], n["dg_arm"], n.get("n_missing_anchors", 0)))
P("\n| arm | seed | Δg arm | RELAB Δg (3) | beats all RELAB | rank among RELAB | z vs RELAB | all RELAB matched | SHIFT Δg (3) |"); P("|---|---|---|---|---|---|---|---|---|")
for a in ("F", "S"):
    for s in SEEDS:
        u = J["arms"][a][s]["nulls"]["summary"]
        P("| %s | s%s | %+.4f | %s | %s | %d / 4 | %s | %s | %s |" % (a, s, u["dg_arm"], ", ".join("%+.4f" % v for v in u["relab_dg"]), u["beats_all_relab"], u["rank_of_arm_among_relab"], ("%+.2f" % u["z_vs_relab"]) if u["z_vs_relab"] is not None else "n/a", u["all_relab_matched"], ", ".join("%+.4f" % v for v in u["shift_dg"])))
P("\n## T7 · Seat path (ARM-S, ARM-SB) — W_ALPHA means; KL = KING_LIVE\n")
P("| arm | seed | w3_king arm / A0 | w3_king KL arm / A0 | w3_king p10/p50/p90 arm | A0 p10/p50/p90 | P(w3_king≥0.85) arm / A0 | mean\\|Δw3_king\\| | frac anchors seat changed |"); P("|---|---|---|---|---|---|---|---|---|")
for a in ("S", "SB"):
    for s in SEEDS:
        o = J["arms"][a][s]["seat"]; k = o["w3_king"]
        P("| %s | s%s | %.3f / %.3f | %.3f / %.3f | %s | %s | %.3f / %.3f | %.4f | %.3f |" % (NAME[a], s, k["arm_mean"], k["A0_mean"], k["arm_king_live_mean"], k["A0_king_live_mean"], "/".join("%.2f" % v for v in k["arm_p10_p50_p90"]), "/".join("%.2f" % v for v in k["A0_p10_p50_p90"]), o["P_w3_king_ge_085_arm"], o["P_w3_king_ge_085_A0"], o["mean_abs_dw3_king"], o["frac_anchors_w3_changed"]))
P("\n| arm | seed | w3_king by year arm | w3_king by year A0 |"); P("|---|---|---|---|")
for a in ("S", "SB"):
    for s in SEEDS:
        k = J["arms"][a][s]["seat"]["w3_king"]
        P("| %s | s%s | %s | %s |" % (NAME[a], s, ", ".join("%s:%.2f" % (y, v) for y, v in k["arm_by_year"].items()), ", ".join("%s:%.2f" % (y, v) for y, v in k["A0_by_year"].items())))
P("\n## T8 · σ_fund (SIGF) terciles — Δg with CI95 (cuts = r12's, on A0 s42 W_ALPHA)\n")
P("| arm | seed | T1 lowest n / Δg [CI95] / w3k arm vs A0 | T2 | T3 highest |"); P("|---|---|---|---|---|")
for a in ("S", "SB"):
    for s in SEEDS:
        t = J["arms"][a][s]["seat"]["sigf_terciles"]
        P("| %s | s%s | " % (NAME[a], s) + " | ".join("%d / %+.3f [%+.3f, %+.3f] / %.2f vs %.2f" % (t[k]["n"], t[k]["dg"], *t[k]["ci95"], t[k]["w3_king_arm"], t[k]["w3_king_A0"]) for k in ("T1 lowest", "T2", "T3 highest")) + " |")
P("\n## T9 · Leg-level vs book-level carry on v4 (W_ALPHA; bps/anchor/unit gross; positive = paid)\n")
P("| seed | fund rank-book carry | A0 executed book carry_ex | ratio | king rank-book carry | KL fund rank-book / book carry | fund leg price LR mean / Sharpe | fund leg net LR (price − rank-book carry) mean / Sharpe | king leg price LR / net LR Sharpe |"); P("|---|---|---|---|---|---|---|---|---|")
for s in SEEDS:
    c = J["leg_vs_book_carry"][s]
    P("| s%s | %.4f | %.4f | **%.2f×** | %.4f | %.4f / %.4f | %+.3f / %.2f | %+.3f / %.2f | %.2f / %.2f |" % (s, c["leg_rankbook_carry_pug_fund"], c["book_carry_ex_pug_A0"], c["ratio_leg_over_book_fund"], c["leg_rankbook_carry_pug_king"], c["fund_rankbook_carry_king_live"], c["book_carry_ex_pug_A0_king_live"], c["leg_price_LR_mean_fund"], c["leg_price_LR_sharpe_fund"], c["leg_net_LR_mean_fund"], c["leg_net_LR_sharpe_fund"], c["leg_price_LR_sharpe_king"], c["leg_net_LR_sharpe_king"]))
P("\n## T9b · ARM-SB seat inputs (per-leg EMA-chain book net vs rank-book price LR; W_ALPHA)\n")
P("| seed | leg | SB net mean / Sharpe | rank-book price LR mean / Sharpe |"); P("|---|---|---|---|")
for s in SEEDS:
    q = J["arms"]["SB"][s].get("sb_seat_inputs") or {}
    for l in ("king", "rev24", "fund"):
        if l in q: P("| s%s | %s | %+.3f / %.2f | %+.3f / %.2f |" % (s, l, q[l]["sb_net_mean"], q[l]["sb_net_sharpe"], q[l]["price_LR_mean"], q[l]["price_LR_sharpe"]))
P("\n## T10 · Regime cells (r12's 34 cells): summary per arm\n")
P("| arm | seed | cells | Sharpe>3.0 before → after | CI95-lo>3.0 before → after | cells with Δg CI95 excluding 0 | which |"); P("|---|---|---|---|---|---|---|")
for a in ARMS:
    for s in SEEDS:
        r = J["arms"][a][s]["regime"]; wh = ["%s/%s (%+.2f)" % (c["family"].split("_")[0], c["cell"], c["dg"]) for c in r["cells"] if not c.get("note") and (c["ci95"][0] > 0 or c["ci95"][1] < 0)]
        P("| %s | s%s | %d | %d → %d | %d → %d | %d | %s |" % (NAME[a], s, r["n_cells"], r["sharpe_gt3_before"], r["sharpe_gt3_after"], r["sharpe_lo_gt3_before"], r["sharpe_lo_gt3_after"], r["cells_dg_ci95_excl0"], "; ".join(wh) or "—"))
for a in ("F", "S", "SB"):
    P("\n### T10.%s · full 34-cell table, %s, s42 (Sharpe A0 → arm; Δg [CI95]; Δcarry / Δpnl / Δcost)\n" % (a, NAME[a]))
    P("| family | cell | n | Sharpe A0 | Sharpe arm | SE | Δg | CI95 | Δcarry | Δpnl | Δcost |"); P("|---|---|---|---|---|---|---|---|---|---|---|")
    for c in J["arms"][a]["42"]["regime"]["cells"]:
        if c.get("note"): P("| %s | %s | %d | too few | | | | | | | |" % (c["family"], c["cell"], c["n"])); continue
        P("| %s | %s | %d | %.3f | %.3f | %.3f | %+.4f | [%+.4f, %+.4f] | %+.4f | %+.4f | %+.4f |" % (c["family"], c["cell"], c["n"], c["sharpe_A0"], c["sharpe_arm"], c["sharpe_se"], c["dg"], *c["ci95"], c["dcarry"], c["dpnl"], c["dcost"]))
P("\n## T11 · Mechanism gate (ARM-F), replay, three windows; 'both' = flagged in both chains (production dual-arm analogue)\n")
P("| run | window | n | flagged/anchor (both) | leaked/anchor | frac still short | leaked gross mean / p90 / max | carry paid by leaked shorts | book carry_ex/gt | leaked share of book carry | FTPOS kills/anchor |"); P("|---|---|---|---|---|---|---|---|---|---|---|")
for tag in ("D_A0I_s42", "D_FI_s42", "D_A0I_s2027", "D_FI_s2027"):
    for wn in ("W_ALPHA", "KING_LIVE", "Y2026"):
        w = M["arms"][tag][wn]; b = w["both_chains"]
        P("| %s | %s | %d | %.2f | %.2f | %.1f%% | %.3f%% / %.3f%% / %.3f%% | %.4f | %.4f | %s | %.3f |" % (tag, wn, b["n_anchors"], b["flagged_per_anchor"], b["leaked_per_anchor"], 100 * b["frac_flagged_negative"], 100 * b["leaked_gross_share_mean"], 100 * b["leaked_gross_share_p90"], 100 * b["leaked_gross_share_max"], b["leaked_carry_paid_bps_mean"], w["carry_ex_pug_mean"], ("%.1f%%" % (100 * w["leaked_carry_share_of_book_carry"])) if w["leaked_carry_share_of_book_carry"] is not None else "n/a", w["kills_per_anchor"]))
P("\n## T12 · A0 reference (this round's GATE-P run = archived arm, bitwise)\n")
P("| seed | g W_ALPHA | Sharpe | τ matched | τ raw | matched/raw (mean of per-anchor ratios) | carry_ex/gt | cost_ex/gt | pnl_ex/gt | g KL | Sharpe KL | maxDD 2× | HALT | worst day |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for s in SEEDS:
    a = J["A0"][s]; t = a["tail_WT"]
    P("| s%s | %.7f | %.7f | %.7f | %.5f | %.5f | %.4f | %.4f | %.4f | %.4f | %.4f | %.4f | %d | %s %.4f |" % (s, a["g_WA"], a["sharpe_WA"], a["tau_matched_WA"], a["tau_raw_WA"], a["tau_ratio_matched_over_raw"], a["carry_WA"], a["cost_WA"], a["pnl_WA"], a["g_KL"], a["sharpe_KL"], t["maxDD"], t["halt4"], t["worst_day"], t["worst_day_ret"]))
P("\n## T13 · Arm artifacts on pod2 (`/workspace/uplift_2026-09-11/r15_structural/arms/`), sha256\n")
P("| tag | device | rc | secs | out sha256 |"); P("|---|---|---|---|---|")
for k, v in G["runs"].items(): P("| %s | %s | %s | %s | %s |" % (k, "pinned" if v["device_sha256"] == G["pinned_device_sha256"] else "derived", v["rc"], v["secs"], v["out_sha256"]))
txt = "\n".join(L); open(f"{R}/receipts/TABLES_r15.md", "w").write(txt); print(txt)
