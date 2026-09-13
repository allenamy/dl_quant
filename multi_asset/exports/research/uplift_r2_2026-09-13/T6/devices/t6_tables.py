#!/usr/bin/env python3
"""t6_tables.py -- render RECEIPT_T6_compute.json (frozen spec) and POSTHOC_T6_decomposition.json (post-hoc) as markdown tables.
Pure formatting; no statistic is computed. Usage: python3 t6_tables.py <receipts_dir> <out_md>"""
import json, sys, os, hashlib
RD, OUT = sys.argv[1], sys.argv[2]
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
PC = os.path.join(RD, "RECEIPT_T6_compute.json"); PP = os.path.join(RD, "POSTHOC_T6_decomposition.json")
R = json.load(open(PC)); P = json.load(open(PP)); L = []; w = L.append
f3 = lambda x: "—" if x is None else ("%+.3f" % x); f4 = lambda x: "%.4f" % x
def stem(s): return s.split(":", 1)[1] if ":" in s else s
w("# TABLES_T6 (rendered by `devices/t6_tables.py`)\n")
w("Sources: `receipts/RECEIPT_T6_compute.json` sha256 `%s` (device `t6_compute.py` sha256 `%s`); `receipts/POSTHOC_T6_decomposition.json` sha256 `%s` (device `t6_posthoc.py` sha256 `%s`, **POST-HOC**).\n" % (sha(PC), R["self_sha256"], sha(PP), P["self_sha256"]))
w("Units: SR = annualized net Sharpe of g = net_ex/gross_total (bps / 4h anchor / unit gross), ×√2190. W_FULL = 2022-01-31 00Z…2026-08-30 20Z (10,038 anchors); FROZEN = 2025-03-01 00Z…2026-08-10 20Z (3,168); W_ALPHA = W_FULL minus first 900 (9,138).\n")
w("## A. Gates\n")
w("GATE-X extraction: s42 %s, s2027 %s (every member's g re-hashes to FAMILY_T6.json).\n" % (R["GATE_X"]["42"], R["GATE_X"]["2027"]))
w("| GATE-0 item | reproduced | published | tol | pass |"); w("|---|---|---|---|---|")
for k, v in R["GATE_0"].items(): w("| %s | %.10f | %.10f | %g | %s |" % (k, v["got"], v["want"], v["tol"], v["pass_"]))
gi = R["GATE_I"]; w("\nGATE-I: splits %d, block length %d (W_FULL F1 s42, 6 oldest rows dropped), equal blocks %s, max |block-sum SR − direct SR| over 20 random splits × 125 members = %.2e ⇒ %s.\n" % (gi["n_combos"], gi["block_len"], gi["equal_blocks"], gi["max_abs_diff"], gi["pass_"]))
w("| control | rep | PBO | slope | P(OOS loss) | SEL | SEL SR | N_eff | DSR(SEL,N_eff) | nested SR | planted picks | haircut | gate checks | pass |"); w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for c in R["GATE_C"]:
    w("| %s | %d | %.4f | %+.3f | %.4f | %s | %.3f | %.1f | %.3f | %+.3f | %d/4 | %+.3f | %s | %s |" % (c["kind"], c["replicate"], c["PBO"], c["slope"], c["P_oos_loss"], c["SEL"], c["SEL_SR"], c["N_eff"], c["DSR_SEL_Neff"], c["nested_SR"], c["nested_picks_planted"], c["haircut"], ", ".join("%s=%s" % (k, v) for k, v in c["checks"].items()), "**%s**" % c["pass_"] if c["replicate"] == 0 else c["pass_"]))
w("\nGATE-C verdict (replicate 0 of each control): **%s**; ALL GATES: **%s**.\n" % (R["GATE_C_PASS"], R["ALL_GATES_PASS"]))
RES = R["RESULTS"]
w("## B. CSCV-PBO (S = 16, all 12,870 splits)\n")
w("| family · seed | window | N | T used | PBO | median logit | slope OOS~IS | intercept | corr | P(OOS loss) | mean SR_IS(n*) | mean SR_OOS(n*) | most selected (share) |"); w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for key in ("F1_s42", "F1_s2027", "F2_s42", "F3_s42", "F4_s42", "F5_s42"):
    for win in ("W_FULL", "FROZEN", "W_ALPHA"):
        if win not in RES[key]: continue
        p = RES[key][win]["PBO"]
        w("| %s | %s | %d | %d | **%.4f** | %.3f | %+.3f | %+.3f | %+.3f | %.4f | %.3f | %.3f | %s |" % (key, win, p["N"], p["T_used"], p["PBO"], p["median_logit"], p["slope"], p["intercept"], p["corr"], p["P_oos_loss"], p["mean_SR_IS_sel"], p["mean_SR_OOS_sel"], "; ".join("%s %.2f" % (stem(t["member"]), t["share"]) for t in p["top_selected"][:5])))
w("\n## C. DSR (Bailey & López de Prado 2014; N_eff = participation ratio; P(SR>3) = PSR(3/√2190 + SR0), T6 extension)\n")
for key in ("F1_s42", "F1_s2027", "F2_s42", "F3_s42", "F4_s42", "F5_s42"):
    for win in ("W_FULL", "FROZEN", "W_ALPHA"):
        if win not in RES[key]: continue
        d = RES[key][win]["DSR"]
        w("\n**%s · %s** — N_raw %d, **N_eff %.3f**, cross-member sd of SR %.4f, SR min / median / max %.3f / %.3f / %.3f\n" % (key, win, d["N_raw"], d["N_eff"], d["sd_SR_annual"], d["SR_annual_min"], d["SR_annual_median"], d["SR_annual_max"]))
        w("| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |"); w("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for t in ("SEL", "A0"):
            if t not in d: continue
            x = d[t]; first = True
            for nl in ("N_eff", "N_raw", "N_300", "N_825", "N_1221"):
                lab = {"N_eff": "N_eff %.2f%s" % (d["N_eff"], " (floored to 2)" if x["Nfloor_N_eff"] else ""), "N_raw": "N_raw %d" % d["N_raw"], "N_300": "300", "N_825": "825 (ledger low)", "N_1221": "1,221 (ledger high)"}[nl]
                if first:
                    w("| %s | %s | %.4f | %d/%d | %.3f | %.2f | %.4f | %.4f | %s | %.4f | %.4f | %.6f |" % (t, stem(x["member"]), x["SR_annual"], x["rank_in_family"], d["N_raw"], x["skew"], x["kurt"], x["PSR_0"], x["PSR_3"], lab, x["SR0_annual_" + nl], x["P_true_SR_gt_0_" + nl], x["P_true_SR_gt_3_" + nl])); first = False
                else:
                    w("| | | | | | | | | %s | %.4f | %.4f | %.6f |" % (lab, x["SR0_annual_" + nl], x["P_true_SR_gt_0_" + nl], x["P_true_SR_gt_3_" + nl]))
w("\n## D. Nested walk-forward selection (expanding training from 2022-01-31 00Z; criterion = SR on all earlier anchors)\n")
w("| family · seed | window | H* (hindsight best on window) | SR(H*, window) | **SR nested** [CI95] | SR(H*, nested span) | SR(A0, span) | span best | **haircut = nested − H*(span)** [CI95] | level haircut | span anchors / days |"); w("|---|---|---|---|---|---|---|---|---|---|---|")
for key in ("F1_s42", "F1_s2027", "F2_s42", "F3_s42", "F4_s42", "F5_s42"):
    for win in ("W_FULL", "FROZEN"):
        n = RES[key][win]["NESTED"]
        w("| %s | %s | %s | %.3f | **%.3f** [%.3f, %.3f] | %.3f | %s | %s %.3f | **%+.3f** [%+.3f, %+.3f] | %+.3f | %d / %d |" % (key, win, stem(n["Hstar"]), n["SR_Hstar_window"], n["SR_nested"], n["ci95_SR_nested"][0], n["ci95_SR_nested"][1], n["SR_Hstar_span"], ("%.3f" % n["SR_A0_span"]) if n["SR_A0_span"] is not None else "—", stem(n["span_best"]), n["SR_span_best"], n["haircut_primary"], n["ci95_haircut_primary"][0], n["ci95_haircut_primary"][1], n["haircut_level"], n["n_span"], n["n_days_span"]))
for key in ("F1_s42", "F1_s2027"):
    for win in ("W_FULL", "FROZEN"):
        n = RES[key][win]["NESTED"]
        w("\n**Per segment · %s · %s** (negative Sharpe printed as NEG)\n" % (key, win))
        w("| segment | anchors | training anchors | selected (by training SR) | SR train | SR OOS | mean g OOS | A0 SR | H* SR | best member in segment | best SR |"); w("|---|---|---|---|---|---|---|---|---|---|---|")
        if win == "W_FULL":
            y = RES[key][win]["YEAR2022"]
            w("| %s | %d | — | — | — | — | — | %s%s | %s%s | %s | %.3f |" % (y["segment"], y["n"], f3(y["A0_SR"]), " NEG" if y["A0_SR"] < 0 else "", f3(y["Hstar_SR"]), " NEG" if y["Hstar_SR"] < 0 else "", stem(y["best_member"]), y["best_SR"]))
        for s in n["segments"]:
            w("| %s | %d | %d | %s | %.3f | %s%s | %+.3f | %s%s | %s%s | %s | %.3f |" % (s["segment"], s["n"], s["train_n"], stem(s["selected"]), s["SR_train"], f3(s["SR_oos"]), " NEG" if s["selected_negative"] else "", s["mean_g_oos"], f3(s["A0_SR"]), " NEG" if s["A0_negative"] else "", f3(s["Hstar_SR"]), " NEG" if s["Hstar_negative"] else "", stem(s["best_member"]), s["best_SR"]))
w("\n## E. POST-HOC decomposition (written after reading §B–§D; descriptive, no verdict rests on it)\n")
w("**PH1 — F1 minus the XIB_LAG50 line {XIB_PWR230k, IB_LAG50_PWR230k}**\n")
w("| seed · window | N | N_eff | PBO | P(OOS loss) | slope | most selected | SEL (SR) | DSR(SEL,N_eff) | nested SR | H* (span SR) | haircut [CI95] | nested picks |"); w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for k, v in P["PH1"].items():
    w("| %s | %d | %.2f | **%.4f** | %.4f | %+.3f | %s | %s (%.3f) | %.4f | %.3f | %s (%.3f) | %+.3f [%+.3f, %+.3f] | %s |" % (k, v["N"], v["N_eff"], v["PBO"], v["P_oos_loss"], v["slope"], "; ".join("%s %.2f" % (stem(t["member"]), t["share"]) for t in v["top"]), stem(v["SEL"]), v["SEL_SR"], v["SEL_P_gt0_Neff"], v["SR_nested"], stem(v["Hstar"]), v["SR_Hstar_span"], v["haircut"], v["ci95_haircut"][0], v["ci95_haircut"][1], " → ".join(stem(x) for x in v["picks"])))
w("\n**PH2 — where the hindsight best H\\* and A0 ranked on the training data at each nested selection point (F1)**\n")
w("| seed · window | segment | selected | SR train (selected) | H* SR train | H* rank | A0 SR train | A0 rank | N |"); w("|---|---|---|---|---|---|---|---|---|")
for k, v in P["PH2"].items():
    for r in v["rows"]:
        w("| %s | %s | %s | %.3f | %.3f | %d | %+.3f | %d | %d |" % (k, r["segment"], stem(r["selected"]), r["SR_train_selected"], r["Hstar_SR_train"], r["Hstar_rank_train"], r["A0_SR_train"], r["A0_rank_train"], r["N"]))
w("\n**PH3 — nested selection minus A0 on the nested span (paired UTC-day block bootstrap, 2,000 draws)**\n")
w("| seed · window | SR nested | SR A0 | difference [CI95] | days |"); w("|---|---|---|---|---|")
for k, v in P["PH3"].items():
    w("| %s | %.3f | %.3f | %+.3f [%+.3f, %+.3f] | %d |" % (k, v["SR_nested"], v["SR_A0_span"], v["diff"], v["ci95_diff"][0], v["ci95_diff"][1], v["n_days"]))
open(OUT, "w").write("\n".join(L) + "\n")
print("SUMMARY t6_tables lines=%d out=%s" % (len(L), OUT))
