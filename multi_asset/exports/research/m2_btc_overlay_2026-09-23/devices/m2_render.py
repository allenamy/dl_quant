#!/usr/bin/env python3
"""m2_render.py — renders m2_readout.py JSON receipts into markdown tables (no computation beyond formatting and the ratios printed).
usage: /usr/bin/python3 m2_render.py <readout.json> [<readout.json> …] > out.md"""
import json, sys


def f(x, p=3, pct=False):
    if x is None: return "n/a"
    return (f"{100 * x:+.{p - 1}f}%" if pct else f"{x:+.{p}f}")


for fp in sys.argv[1:]:
    R = json.load(open(fp))
    print(f"### {R['label']} — VERDICT **{R['VERDICT']}**" + (f" (failing: {', '.join(R['failing'])})" if R["failing"] else "") + "\n")
    print(f"receipt `{fp.split('/')[-1]}` · device m2_readout.py {R['self_sha256'][:12]} · UTC {R['utc']}\n")
    C = R["criteria"]
    print("| criterion | measured | gate | result |\n|---|---|---|---|")
    h1 = C["H2.1"]; print(f"| H2.1 realised daily beta vs BTC, PRE2026 (M2 arm) | {h1['beta_m2']:+.3f} (base {h1['beta_base']:+.3f}) | [−0.10, +0.10] | {'PASS' if h1['pass'] else 'FAIL'} |")
    h2 = C["H2.2"]; segs = ", ".join(f"{k} {f(v)}" for k, v in h2["dS_segments"].items())
    print(f"| H2.2 ΔSharpe PRE2026; segments | {f(h2['dS_pre2026'])}; {segs} ({h2['n_segments_positive']}/3 > 0) | > 0 and ≥ 2/3 | {'PASS' if h2['pass'] else 'FAIL'} |")
    h3 = C["H2.3"]["[m2, base, m2>=base]"]
    s3 = "; ".join(f"{k} {f(v[0], pct=True)} vs {f(v[1], pct=True)}" for k, v in h3.items())
    print(f"| H2.3 maxDD 5m and worst day not worse (mean path and path average) | {s3} | M2 ≥ base, all four | {'PASS' if C['H2.3']['pass'] else 'FAIL'} |")
    h4 = C["H2.4"]["cells"]; s4 = "; ".join(f"{k} ΔS {f(v['dS'])}" for k, v in h4.items())
    print(f"| H2.4 cost cells: sign of ΔSharpe unchanged | {s4} | same sign as {f(h2['dS_pre2026'])} | {'PASS' if C['H2.4']['pass'] else 'FAIL'} |\n")
    D = R["decomposition_PRE2026"]
    print("**Drift / variance decomposition (PRE2026, mean paths, complete UTC days, n = %d)**\n" % D["n_days"])
    print("| quantity | value |\n|---|---|")
    for k, lab in (("mu_base", "μ base (daily)"), ("mu_m2", "μ M2 (daily)"), ("d_mu", "Δμ"), ("sd_base", "σ base (daily)"), ("sd_m2", "σ M2 (daily)"), ("d_sd", "Δσ"),
                   ("mu_btc_daily", "μ BTC (daily)"), ("beta_book_gross_units_mean", "mean β_book / Σ|w| (published anchors)"),
                   ("drift_term_daily", "drift term −gm·β̄_book·μ_BTC (daily)"), ("drift_share_of_d_mu", "drift / Δμ"),
                   ("sharpe_split_mean_only", "Sharpe change from the mean only"), ("sharpe_split_variance_only", "Sharpe change from the variance only")):
        v = D[k]; print(f"| {lab} | {'n/a' if v is None else (f'{v * 1e4:+.2f} bps' if k.startswith(('mu', 'd_mu', 'sd', 'd_sd', 'drift_term')) else f'{v:+.4f}')} |")
    print(f"| DRIFT-DEPENDENT rule fires | {D['drift_dependent_rule']['fires']} ({', '.join(f'{k}={v}' for k, v in D['drift_dependent_rule'].items() if k != 'fires')}) |\n")
    print("**Per segment, two arms (mean path; per-path [2.5 %, 97.5 %] in brackets)**\n")
    print("| window | arm | days | Sharpe | total ret | CAGR | maxDD 5m | worst day | β daily vs BTC | g bps/anchor | fee bps | day stops | name stops |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for w, T in R["table"].items():
        for arm in ("base", "m2"):
            m = T[arm]["mean_path"]; p = T[arm]["paths"]
            print(f"| {w} | {arm} | {m['n_days']} | {m['sharpe']:.2f} [{p['sharpe']['p2.5']:.2f}, {p['sharpe']['p97.5']:.2f}] | {100 * m['total_return']:+.1f}% | "
                  f"{100 * m['cagr']:+.1f}% | {100 * m['maxdd_5m']:.1f}% [{100 * p['maxdd_5m']['p2.5']:.1f}, {100 * p['maxdd_5m']['p97.5']:.1f}] | {100 * m['worst_day']:.2f}% | "
                  f"{m['beta_daily_vs_btc']:+.3f} | {m['g_bps_per_anchor']:+.3f} | {m['fee_bps']:.3f} | {m['day_stop_flattens']:.1f} | {m['per_name_stops']:.0f} |")
    print()
    print("**β_book in gross units (β_book / Σ|w|, published anchors)**\n")
    print("| window | n | mean | p5 | p25 | p50 | p75 | p95 | share < 0 |\n|---|---|---|---|---|---|---|---|---|")
    for w, b in R["beta_book_gross_units"].items():
        print(f"| {w} | {b['n_published_anchors']} | {b['mean']:+.4f} | {b['p5']:+.4f} | {b['p25']:+.4f} | {b['p50']:+.4f} | {b['p75']:+.4f} | {b['p95']:+.4f} | {100 * b['share_negative']:.1f}% |")
    print()
