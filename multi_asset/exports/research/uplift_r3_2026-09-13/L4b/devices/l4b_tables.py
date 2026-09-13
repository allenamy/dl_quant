#!/usr/bin/env python3
"""l4b_tables.py -- L4b step 3 (local). Renders <receipts>/TABLES_L4b.md from RECEIPT_L4b_pull.json and RECEIPT_L4b_marks.json only (formatting, no computation
beyond sums of receipt values). Usage: python3 l4b_tables.py <receipts_dir>"""
import os, sys, json, math
RD = sys.argv[1]
PR = json.load(open(os.path.join(RD, "RECEIPT_L4b_pull.json"))); R = json.load(open(os.path.join(RD, "RECEIPT_L4b_marks.json")))
L = []; P = L.append
def f(x, d=2, sign=False):
    if x is None: return "—"
    if isinstance(x, bool): return "yes" if x else "no"
    if isinstance(x, str): return x
    if not math.isfinite(x): return "nan"
    return ("%+.*f" if sign else "%.*f") % (d, x)
V = ("X1s1", "X1s0", "X2s1", "X3s1")
P("# TABLES · L4b · executable exit marks from raw 1m archives (rendered from receipts; P&L in bps per unit sleeve capital unless stated)")
P("")
P("Pull device `%s`, marks device `%s`, PREREG `%s`, F2 series `%s`." % (PR["device_sha256"], R["device_sha256"], R["prereg_sha256"], R.get("series_sha256")))
P(""); P("## T0 Gates")
P("| gate | pass | readings |"); P("|---|---|---|")
g = PR["gates"]["G-ARCHIVE"]; by = PR["by_family"]
P("| G-ARCHIVE | %s | %s; premium covers P_F months %s; dd probes %s |" % (f(g["pass_"]), "; ".join("%s %d/%d ok, checksum %d, empty %d, µs files %d, dup minutes %d, %.2f GB" % (k, v["ok"], v["required"], v["checksum_ok"], v["empty_rows"], v["us_files"], v["dup_minutes"], v["bytes"] / 1e9) for k, v in by.items()),
      f(PR["premium_covers_pop_months"]), [(d["tag"], d["ok"]) for d in PR["dd_probes"]]))
for k in ("G-L4REPRO", "G-SYN2", "G-B1REPRO", "G-PREMPARSE", "G-HARNESS"):
    v = R["gates"][k]; det = {kk: vv for kk, vv in v.items() if kk not in ("pass_", "cases", "examples", "series_equal")}
    if k == "G-SYN2": det = dict(cases=len(v["cases"]), failing=[c for c in v["cases"] if not (c["telescoped_ok"] and c["total_ok"] and c["stopped_ok"])])
    P("| %s | %s | %s |" % (k, f(v["pass_"]), json.dumps(det)))
P(""); P("Population: P_F %d arm-holds (%d unique events), P_C %d arm-holds." % (R["population"]["P_F"], R["population"]["unique_events"], R["population"]["P_C"]))
P(""); P("## T1 Per event (unique symbol / entry / exit). Hold P&L columns are per arm-hold, bps per unit sleeve capital; income and cost are L4's.")
P("| symbol (spot) | reason | entry → exit | τ spot / τ perp | stopped (gap h) | blowout / peak |P/S−1| bps | B2 / B1 at exit (bps) | 1m premium longest identical run, last 7 d (min) | discontinuities | arm: M-PREM / M-CLOSE / EXEC X1σ1 / X1σ0 / X2σ1 / X3σ1 · income · cost |")
P("|---|---|---|---|---|---|---|---|---|---|")
for e in sorted(R["events"], key=lambda x: (x["exit"], x["sym"], x["entry"])):
    arms = "<br>".join("%s: %s / %s / %s / %s / %s / %s · %s · %s" % (a, f(v["M_PREM"], 1, True), f(v["M_CLOSE"], 1, True), f(v["M_EXEC_X1s1"], 1, True), f(v["M_EXEC_X1s0"], 1, True), f(v["M_EXEC_X2s1"], 1, True),
                                                          f(v["M_EXEC_X3s1"], 1, True), f(v["income_L4"], 1, True), f(v["cost_L4"], 2)) for a, v in sorted(e["arms"].items()))
    disc = ", ".join("%s %s ×%.3g" % (d["leg"], d["t"], d["ratio"]) for d in (e["discontinuities"] or [])) or "none"
    P("| %s (%s) | %s | %s → %s | %s / %s | %s (%s) | %s / %s | %s / %s | %s | %s | %s |" % (e["sym"], e["spot"], e["reason"], e["entry"], e["exit"], e["tau_spot"], e["tau_perp"],
      ("NO-STOP" if e["nostop"] else e["stopped"]), f(e["gap_h"], 1), e["blowout"] or "none", f(e["peak_abs_basis_bps"], 0), f(e["b2_exit_bps"], 1), f(e["b1_exit_bps"], 1),
      e["prem_1m_longest_identical_run_last7d"], disc, arms))
P(""); P("### Exit prices (pre-stress) by variant, per event")
P("| symbol | entry → exit | X1: spot (time) / perp (time) · P/S−1 | X2 | X3 |"); P("|---|---|---|---|---|")
def exs(x):
    if not x: return "—"
    s_, p_ = x["spot"], x["perp"]
    try: ps = "%+.0f bps" % ((p_[0] / s_[0] - 1) * 1e4)
    except Exception: ps = "—"
    import time as _t
    t = lambda z: _t.strftime("%m-%d %H:%MZ", _t.gmtime(z)) if z and z > 0 else "—"
    return "%.6g (%s) / %.6g (%s) · %s" % (s_[0], t(s_[1]), p_[0], t(p_[1]), ps)
for e in sorted(R["events"], key=lambda x: (x["exit"], x["sym"], x["entry"])):
    P("| %s | %s → %s | %s | %s | %s |" % (e["sym"], e["entry"], e["exit"], exs(e["exec_exit"]["X1s1"]), exs(e["exec_exit"]["X2s1"]), exs(e["exec_exit"]["X3s1"])))
P(""); P("## T2 Instrument agreement (per arm-hold P&L): controls (normal exits) vs forced exits")
P("| population | pair | n | median |Δ| | Spearman | sum a / sum b |"); P("|---|---|---|---|---|---|")
for pop in ("controls", "forced"):
    for pair, v in R["R2"][pop].items():
        if v: P("| %s | %s | %d | %s | %s | %s / %s |" % (pop, pair, v["n"], f(v["median_abs_diff"], 2), f(v["spearman"], 3), f(v["sum_a"], 1, True), f(v["sum_b"], 1, True)))
P(""); P("Sums over P_F arm-holds: " + "; ".join("%s %s" % (k, f(sum((vv[k] or 0) for e in R["events"] for vv in e["arms"].values()), 1, True)) for k in ("M_PREM", "M_CLOSE", "M_EXEC_X1s1", "M_EXEC_X1s0", "M_EXEC_X2s1", "M_EXEC_X3s1")))
P(""); P("## T3 POST-HOC-FAMILY-2: A01–A08 under M-EXEC (per anchor, bps per unit capital; CI95 = 30-day circular block bootstrap; Bonf-8 = 0.3125 % quantile; cum-20 = 0.125 %)")
P("| arm | span | X1σ1 net [CI95] · Bonf-8 · cum-20 | SR | basis | income | cost | pos share | X1σ0 net | X2σ1 net | X3σ1 net |"); P("|---|---|---|---|---|---|---|---|---|---|---|")
for a in sorted(R["R3"]):
    for sp in ("Y22", "Y23", "Y24", "Y25", "Y26", "S2426", "FULL"):
        t = R["R3"][a]["X1s1"]["table"][sp]; ci = t.get("ci", {})
        P("| %s | %s | %s [%s, %s] · %s · %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (a, sp, f(t["net_mean"], 4, True), f(ci.get("q2.5000"), 4, True), f(ci.get("q97.5000"), 4, True), f(ci.get("q0.3125"), 4, True), f(ci.get("q0.1250"), 4, True),
          f(t["sharpe"], 2), f(t["bas_mean"], 4, True), f(t["inc_mean"], 4, True), f(t["cost_mean"], 4), f(t["position_share"], 3),
          f(R["R3"][a]["X1s0"]["table"][sp]["net_mean"], 4, True), f(R["R3"][a]["X2s1"]["table"][sp]["net_mean"], 4, True), f(R["R3"][a]["X3s1"]["table"][sp]["net_mean"], 4, True)))
P(""); P("### F2 survival (PREREG §7)")
P("| arm | P0 | P1 | P2 Bonf-8 | P2 unadj | P2 cum-20 | P3 | sensitivities S2426 > 0 | **survives** | survives unadj | survives cum-20 | ρ W anchor/day s42 · s2027 | unpriceable holds X1σ1 |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for a, v in sorted(R["F2_survival"].items()):
    rho = R["R3"][a]["X1s1"]["rho"]
    P("| %s | %s | %s | %s | %s | %s | %s | %s | **%s** | %s | %s | %s/%s · %s/%s | %d |" % (a, f(v["P0"]), f(v["P1"]), f(v["P2_bonf8"]), f(v["P2_unadj"]), f(v["P2_cum20"]), f(v["P3"]), f(v["sensitivities_S2426_positive"]),
      f(v["survives"]), f(v["survives_unadj"]), f(v["survives_cum20"]), f(rho["42"]["per_anchor"], 3, True), f(rho["42"]["per_day"], 3, True), f(rho["2027"]["per_anchor"], 3, True), f(rho["2027"]["per_day"], 3, True),
      R["R3"][a]["X1s1"]["unpriceable_holds"]))
P(""); P("**F2 statement: %s** (N_F2 = %d; cumulative ledger %d)." % (R["F2_statement"], R["N_F2"], R["cumulative_ledger"]))
if R.get("R3_flagged_zeroed"): P(""); P("Descriptive (primary with discontinuity-flagged P_F holds zeroed): " + "; ".join("%s S2426 %s · W %s" % (a, f(v["S2426"], 4, True), f(v["FULL"], 4, True)) for a, v in sorted(R["R3_flagged_zeroed"].items())))
P(""); P("F3: %s" % R["F3"])
open(os.path.join(RD, "TABLES_L4b.md"), "w").write("\n".join(L) + "\n")
print("SUMMARY l4b_tables lines=%d statement=%s" % (len(L), R["F2_statement"]))
