#!/usr/bin/env python3
"""ovn_render.py — renders the OVN Stage 1 receipts into markdown tables (no computation beyond formatting and unit conversion; every number is
read from a receipt whose sha256 is printed in the output). Mac: /usr/bin/python3 ovn_render.py <STATS.json> <EXT.json|-> <P_dir|-> <out.md>
P_dir holds BT_P_READING_OVN_{OLD,NEW_s42,NEW_s2027}.json and BT_P2_READING_OVN_{...}.json (any missing file is rendered as UNAVAILABLE)."""
import sys, json, hashlib, os, time

STATS, EXT, PDIR, OUT = sys.argv[1:5]
ARMS = ("OLD", "OLD_HOLD", "NEW_s42", "NEW_s2027")
CTRLS = ("OLD", "OLD_HOLD")
SEGS = ("2023H2", "2024", "2025", "pre2026", "2026")


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


S = json.load(open(STATS)); L = []
w = L.append
w(f"<!-- rendered by ovn_render.py from {os.path.basename(STATS)} sha256 {sha(STATS)}" + (f"; {os.path.basename(EXT)} sha256 {sha(EXT)}" if EXT != "-" else "") + " -->")
if S.get("DRYRUN_device_test_on_published_runs"): w("**DRY RUN ON PUBLISHED RUNS - NOT AN OVN RESULT**")


def pct(x, d=1): return "n/a" if x is None else f"{100 * x:+.{d}f}%"
def num(x, d=2): return "n/a" if x is None else f"{x:+.{d}f}"
def cell(t, k, f, d):
    v = t["paths"].get(k)
    if not isinstance(v, dict) or "path_mean" not in v: return "UNAVAILABLE"
    return f"{f(v['path_mean'], d)} [{f(v['p2.5'], d)}, {f(v['p97.5'], d)}]"


w("\n### Verdict lines (AMENDMENT 1: each NEW seed must pass G1–G5 against BOTH OLD and OLD_HOLD)\n")
def vline(v):
    g1 = v["G1"]; b = g1["boot_30d"]["ci97.5_two_sided_bps"]
    return (f"G1={'PASS' if g1['PASS'] else 'FAIL'} ({g1['estimate_bps_per_day']:+.3f} bps/day, 97.5% CI 30d [{b[0]:+.3f}, {b[1]:+.3f}]) · G2={'PASS' if v['G2']['PASS'] else 'FAIL'} ({v['G2']['segments_positive']}/3) · "
            f"G3={'PASS' if v['G3']['PASS'] else 'FAIL'} · G4={'PASS' if v['G4']['PASS'] else 'FAIL'} · G5={'PASS' if v['G5']['PASS'] else 'FAIL'} · all={'PASS' if v['ALL_G_PASS'] else 'FAIL'}")
for s in ("NEW_s42", "NEW_s2027"):
    for c in CTRLS:
        v = S["criteria"][s][c]
        w(f"- {s} vs {c}: " + ("UNAVAILABLE" if "G1" not in v else vline(v)))
w(f"- **VERDICT = {S['VERDICT']}** — {S['verdict_rule']}")
w(f"- which control each seed passed: {json.dumps(S['which_control_passed'])}; original prereg verdict vs OLD only (superseded, transparency): {S[[k for k in S if k.startswith('original_prereg_verdict')][0]]}")
gates = {"G1": "pre-2026 d̄ mean > 0 and 97.5% two-sided lower bound (30-day blocks) > 0", "G2": "≥ 2 of 3 segments with mean d̄ > 0",
         "G3": "NEW worst-segment Sharpe ≥ control worst − 0.10; pre-2026 maxDD (path mean) not worse than control by > 2 pp", "G4": "G1 point estimate keeps sign under fee×1.25 / slip×1.5 / fill×0.9",
         "G5": "pre-2026 §4-2 day-stop events (path mean) NEW ≤ 1.25 × control"}
def gcell(v, g):
    if g == "G1":
        g1 = v["G1"]; b30 = g1["boot_30d"]; b5 = g1["boot_5d_sensitivity"]
        return (f"{g1['estimate_bps_per_day']:+.3f} bps/day; 97.5% [{b30['ci97.5_two_sided_bps'][0]:+.3f}, {b30['ci97.5_two_sided_bps'][1]:+.3f}] (30d); 95% [{b30['ci95_bps'][0]:+.3f}, {b30['ci95_bps'][1]:+.3f}]; "
                f"5d-block 97.5% [{b5['ci97.5_two_sided_bps'][0]:+.3f}, {b5['ci97.5_two_sided_bps'][1]:+.3f}]; {g1['n_days']} d × {g1['n_paths']} paths → **{'PASS' if g1['PASS'] else 'FAIL'}**")
    if g == "G2":
        sm = v["G2"]["segment_means"]; return " / ".join(f"{k} {sm[k]['mean_bps_per_day']:+.3f}" for k in ("2023H2", "2024", "2025")) + f" → {v['G2']['segments_positive']}/3 → **{'PASS' if v['G2']['PASS'] else 'FAIL'}**"
    if g == "G3":
        g3 = v["G3"]; ws = g3["worst_segment_sharpe"]; dd = g3["maxdd_5m_pre2026_path_mean"]
        return (f"worst-seg Sharpe NEW {ws['NEW']:+.3f} vs ctrl {ws['CTRL']:+.3f} (need ≥ {ws['CTRL'] - 0.10:+.3f}) {'ok' if g3['sharpe_part_PASS'] else 'FAIL'}; "
                f"maxDD5m NEW {pct(dd['NEW'])} vs ctrl {pct(dd['CTRL'])} (need ≥ {pct(dd['CTRL'] - 0.02)}) {'ok' if g3['maxdd_part_PASS'] else 'FAIL'} → **{'PASS' if g3['PASS'] else 'FAIL'}**")
    if g == "G4":
        return "; ".join(f"{c} {x['estimate_bps_per_day']:+.3f}" if "estimate_bps_per_day" in x else f"{c} UNAVAILABLE" for c, x in v["G4"]["cells"].items()) + f" (base {v['G4']['base_estimate_bps_per_day']:+.3f}) → **{'PASS' if v['G4']['PASS'] else 'FAIL'}**"
    g5 = v["G5"]["day_stop_flattens_pre2026_path_mean"]
    return f"NEW {g5['NEW']:.2f} vs limit {g5['limit_1.25x_CTRL']:.2f} (ctrl {g5['CTRL']:.2f}) → **{'PASS' if v['G5']['PASS'] else 'FAIL'}**"
for s in ("NEW_s42", "NEW_s2027"):
    w(f"\n### G1–G5 for {s}: measured vs gate, against each control\n")
    w("| # | gate | vs OLD | vs OLD_HOLD |"); w("|---|---|---|---|")
    for g in ("G1", "G2", "G3", "G4", "G5"):
        w(f"| {g} | {gates[g]} | " + " | ".join(("UNAVAILABLE" if "G1" not in S["criteria"][s][c] else gcell(S["criteria"][s][c], g)) for c in CTRLS) + " |")
    w("\nG1 with the partial first day included (sensitivity): " + "; ".join(f"vs {c}: {S['criteria'][s][c]['G1']['sensitivity_partial_first_day_included']['estimate_bps_per_day']:+.3f} bps/day, changes G1: {S['criteria'][s][c]['G1']['sensitivity_partial_first_day_included']['changes_G1']}" for c in CTRLS)
      + ". 2026 segment mean d̄ (report only): " + "; ".join(f"vs {c} {S['criteria'][s][c]['G2']['segment_means']['2026']['mean_bps_per_day']:+.3f} bps/day" for c in CTRLS))
c1 = S[[k for k in S if k.startswith("C1_quantified")][0]]
w("\n### C1 quantified: OLD_HOLD − OLD (same model, only the failure action differs; NOT a criterion)\n")
w("| quantity | value |"); w("|---|---|")
for g in ("G1", "G2", "G3", "G5"): w(f"| {g}-form | {gcell(c1, g).replace('**', '')} |")
w("\n### Per segment, R-main (base cost cell, scaled reading): 32-path mean [2.5%, 97.5%]\n")
w("| segment | arm | Sharpe (full UTC days) | total return | CAGR | maxDD 5m | worst day | §4-2 day stops | per-name stops | turnover/gross per anchor | n windows / full days |")
w("|---|---|---|---|---|---|---|---|---|---|---|")
T = S["tables"]
for sg in SEGS:
    for a in ARMS:
        if a not in T or "base" not in T[a]: w(f"| {sg} | {a} | UNAVAILABLE |||||||||"); continue
        t = T[a]["base"][sg]
        w(f"| {sg} | {a} | {cell(t, 'sharpe', num, 2)} | {cell(t, 'total_return', pct, 1)} | {cell(t, 'cagr', pct, 1)} | {cell(t, 'maxdd_5m', pct, 1)} | {cell(t, 'worst_day', pct, 2)} | "
          f"{cell(t, 'day_stop_flattens', num, 1)} | {cell(t, 'per_name_stops', num, 0)} | {t['paths']['turnover_over_gross']['path_mean']:.4f} | {t['paths']['n_windows']} / {t['paths']['n_full_days']} |")
w("\n### Cash decomposition, R-main: bps per anchor per unit target gross, 32-path mean (identity g = price − funding paid − fee − unknown, max err printed)\n")
w("| segment | arm | g | price & trading | funding paid | fee | unknown excluded | identity max err |")
w("|---|---|---|---|---|---|---|---|")
for sg in SEGS:
    for a in ARMS:
        if a not in T or "base" not in T[a]: continue
        p = T[a]["base"][sg]["paths"]
        w(f"| {sg} | {a} | {p['g']['path_mean']:+.3f} | {p['price']['path_mean']:+.3f} | {p['funding_paid']['path_mean']:+.3f} | {p['fee']['path_mean']:+.3f} | {p['unknown_excluded']['path_mean']:+.3f} | {p['g_identity_max_err']:.1e} |")
w("\n### Certified MEAN PATH (descriptive; the published headline convention)\n")
w("| segment | arm | Sharpe | total return | maxDD 5m |")
w("|---|---|---|---|---|")
for sg in SEGS:
    for a in ARMS:
        if a not in T or "base" not in T[a]: continue
        m = T[a]["base"][sg]["mean_path"]; w(f"| {sg} | {a} | {num(m['sharpe'])} | {pct(m['total_return'])} | {pct(m['maxdd_5m'])} |")
w("\n### Cost cells and the literal (fixed-380) reading: path-mean Sharpe / total return (report only)\n")
w("| cell | segment | " + " | ".join(ARMS) + " |")
w("|---|---|" + "---|" * len(ARMS))
for c in ("fee_x1.25", "slip_x1.5", "fill_x0.9", "lit"):
    for sg in ("pre2026", "2026"):
        vals = []
        for a in ARMS:
            if a in T and c in T[a]:
                p = T[a][c][sg]["paths"]; vals.append(f"S {p['sharpe']['path_mean']:+.2f} / {pct(p['total_return']['path_mean'])}")
            else: vals.append("not run (by design)" if (a == "OLD_HOLD" and c == "lit") else "UNAVAILABLE")
        w(f"| {c} | {sg} | " + " | ".join(vals) + " |")
if EXT != "-":
    E = json.load(open(EXT))
    w("\n### 2026-08-31T04Z → 2026-09-18T20Z (DESCRIBE ONLY; OLD = certified OBJB_A0X run)\n")
    w("| arm | total return | Sharpe (full days) | maxDD 5m | worst day | g | day stops | d̄ vs OLD (point, bps/day) |")
    w("|---|---|---|---|---|---|---|---|")
    for a in [a_ for a_ in ARMS if a_ in E["arms"]]:
        x = E["arms"][a]
        w(f"| {a} | {pct(x['total_return']['path_mean'])} | {num(x['sharpe']['path_mean'])} | {pct(x['maxdd_5m']['path_mean'])} | {pct(x['worst_day']['path_mean'], 2)} | {x['g']['path_mean']:+.3f} | {x['day_stop_flattens']['path_mean']:.2f} | "
          + (f"{x['dbar_vs_OLD_bps_per_day_point']:+.2f} ({x['dbar_n_days']} d)" if "dbar_vs_OLD_bps_per_day_point" in x else "—") + " |")
    w(f"\nControl, NEW X run vs NEW main run on shared anchors ≤ 2026-08-30T20Z: {json.dumps(E['control_vs_main_run'])}")
if PDIR != "-":
    w("\n### R-P (§4-4 −25 % from the base's starting equity, permanent halt) and R-P2 (day stop + named resume delay), FULL_RECIPE base 2023-06-30T04Z — report only\n")
    w("| arm | R-P halted paths | R-P median halt anchor | R-P end return (P-halt / no-halt) | R-P2 H=12h W_ENTRY: paths hit −25 % | median −25 % anchor | end return P2 / no halt |")
    w("|---|---|---|---|---|---|---|")
    for a in ARMS:
        pf = os.path.join(PDIR, f"BT_P_READING_OVN_{a}.json"); p2f = os.path.join(PDIR, f"BT_P2_READING_OVN_{a}.json"); cells = []
        if os.path.exists(pf):
            P = json.load(open(pf)); run = next(v for k, v in P["runs"].items() if "scaled" in k); base = next(v for k, v in run["bases"].items() if k.startswith("FULL_RECIPE"))
            sm = base["summary"]; hi = sm["halt_index"]
            cells += [f"{sm['fired_paths']}/{sm['n_paths']}", (next((pp["halt_anchor"] for pp in base["per_path"] if pp.get("halt_index") == hi.get("median_element")), f"index {hi.get('median_element')}") if sm["fired_paths"] else "none"),
                      f"{pct(sm['end_return_phalt']['mean'])} / {pct(sm['end_return_nohalt']['mean'])}"]
        else: cells += ["UNAVAILABLE"] * 3
        if os.path.exists(p2f):
            P2 = json.load(open(p2f)); run = next(v for k, v in P2["runs"].items() if "scaled" in k); base = next(v for k, v in run["bases"].items() if k.startswith("FULL_RECIPE"))
            sm = base["12"]["W_ENTRY"]["summary"]
            hit = sm["paths_that_hit_cum25"]; e2 = sm["end_return_P2"]["measured"]; e0 = sm["end_return_no_halt"]["measured"]
            cells += [f"{hit['n_true']}/{hit['population']['n']}", str(sm["cum25_anchor_median_utc"].get("value")),
                      f"{pct(e2['mean'])} / {pct(e0['mean'])} (n_eff {e2['n_eff']})"]
        else: cells += ["UNAVAILABLE"] * 3
        w(f"| {a} | " + " | ".join(cells) + " |")
open(OUT, "w").write("\n".join(L) + "\n"); print("rendered", OUT, sha(OUT))
