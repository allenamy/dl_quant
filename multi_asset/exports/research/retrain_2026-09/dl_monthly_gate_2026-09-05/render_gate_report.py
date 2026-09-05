"""render_gate_report.py — dl_monthly_gate: REPORT_tables.md from the json artifacts (manifest/inference receipts, decisions, score tables, replay levels, deltas, judge, commands)."""
import os, json, hashlib, time
G = "/workspace/review_scratch/dl_monthly_gate"
def J(p): return json.load(open(p)) if os.path.exists(p) else None
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else "MISSING"
def f4(v): return "n/a" if v is None else f"{v:+.4f}"
def f3(v): return "n/a" if v is None else f"{v:+.3f}"
L = []; P = L.append
MAN = J(f"{G}/preds_model_manifest.json"); JD = J(f"{G}/results/judge_gate.json"); DEC = {t: J(f"{G}/results/decisions_{t}.json") for t in ("mE1", "mE60")}; SC = {t: J(f"{G}/results/score_{t}.json") for t in ("mE1", "mE60")}
P("## T1 · Inference receipts (VERIFIED `preds_model_manifest.json`; GPU inference only, no training)")
if MAN:
    P(f"inputs: targets `{MAN['inputs']['targets'][:16]}` fea82 `{MAN['inputs']['fea82'][:16]}` fea89 `{MAN['inputs']['fea89'][:16]}`; torch {MAN['torch']} on {MAN['device']}; created {MAN['created_utc']}")
    P("| model | train cutoff | first scored anchor | n_train | re-infer vs preds_fold: bitwise / max abs Δ / cells | months packaged (age→month) | .pt sha |"); P("|---|---|---|---|---|---|---|")
    for k, v in MAN["models"].items():
        r = v["reinfer_vs_preds_fold"]; P(f"| {k} | {v['train_cutoff']} | {v['first_test']} | {v['n_train']} | {r['bitwise_equal']} / {r['max_abs_diff']:.1e} / {r['n_cells']} | " + ", ".join(f"{m['age']}→{mo}" for mo, m in v["months"].items()) + f" | `{v['pt_sha256'][:12]}` |")
    P(f"\nall bitwise: {all(v['reinfer_vs_preds_fold']['bitwise_equal'] for v in MAN['models'].values())}; per-month npz files: {sum(len(v['months']) for v in MAN['models'].values())} (sha256 in the manifest)")
for t in ("mE1", "mE60"):
    d = DEC[t]
    if not d: continue
    P(f"\n## T2 · Decision table {t} (VERIFIED `results/decisions_{t}.json`; candidate = F(t−1) evaluated on month t−1 vs the incumbent at its age; R1 IC ≥ −0.002 / R2 leg ≥ −0.10 bps / R3 both / R4 IC > 0)")
    P("| month | R0 dep/age | R1 dep/age/swap | R2 dep/age/swap | R3 dep/age/swap | R4 dep/age/swap | IC cand / inc (t−1) | leg cand / inc (t−1) | IC of R1's model this month | IC newest this month |"); P("|---|---|---|---|---|---|---|---|---|---|")
    for k in range(len(d["months"])):
        r0, r1, r2, r3, r4 = (d["rules"][r][k] for r in ("R0", "R1", "R2", "R3", "R4"))
        ic = f"{r1['ic_cand_tm1']:+.4f} / {r1['ic_inc_tm1']:+.4f}" if r1.get("ic_cand_tm1") is not None else "n/a"; lg = f"{r1['leg_cand_tm1']:+.3f} / {r1['leg_inc_tm1']:+.3f}" if r1.get("leg_cand_tm1") is not None else "n/a"
        P(f"| {r0['month']} | {r0['deployed']}/{r0['age']} | {r1['deployed']}/{r1['age']}/{r1['swap']} | {r2['deployed']}/{r2['age']}/{r2['swap']} | {r3['deployed']}/{r3['age']}/{r3['swap']} | {r4['deployed']}/{r4['age']}/{r4['swap']} | {ic} | {lg} | {r1['ic_month']:+.4f} | {r1['ic_newest_month']:+.4f} |")
    P("\nIC matrix (model test-month × scored month; VERIFIED `ic_matrix_model_x_month`):"); M = d["months"]; IM = d["ic_matrix_model_x_month"]
    P("| model \\ month | " + " | ".join(str(m)[2:] for m in M) + " |"); P("|---|" + "---|" * len(M))
    for i, m in enumerate(M): P(f"| {m} | " + " | ".join((f"{IM[i][j]:+.3f}" if IM[i][j] == IM[i][j] else "") for j in range(len(M))) + " |")
    s = SC[t]
    if s:
        P(f"\n## T3 · Score level {t} (VERIFIED `results/score_{t}.json`; per-anchor rank IC, same anchor set; day-block bootstrap)")
        P("| window / arm | n | IC mean | anchor s.e. |"); P("|---|---|---|---|")
        for k, v in s["ic_levels"].items(): P(f"| {k} | {v['n']} | {v['mean']:+.4f} | {v['se_anchor']:.4f} |")
        P("\n| ΔIC pair (window) | n | Δ | CI95 | P(Δ>0) |"); P("|---|---|---|---|---|")
        for k, v in s["ic_delta"].items():
            if "mean" in v: P(f"| {k} | {v['n']} | {v['mean']:+.4f} | [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] | {v['p_gt0']:.3f} |")
        P("\n| month | " + " | ".join(s["monthly_ic"][next(iter(s["monthly_ic"]))].keys()) + " |"); P("|---|" + "---|" * len(s["monthly_ic"][next(iter(s["monthly_ic"]))]))
        for m, row in s["monthly_ic"].items(): P(f"| {m} | " + " | ".join(f4(row[k]) for k in row) + " |")
        P("\n| arm | swaps | decisions | mean age (all) | mean age (2025-03→) | max age | deployed models |"); P("|---|---|---|---|---|---|---|")
        for r, a in s["arms"].items(): P(f"| {r} | {a['swaps']} | {a['decisions']} | {a['mean_age']:.2f} | {a['mean_age_from_2025-03']:.2f} | {a['max_age']} | {', '.join(str(x) for x in a['deployed_models'])} |")
if JD:
    PW = "2025-03->26<=cut"
    P(f"\n## T4 · Replay levels (VERIFIED `results/judge_gate.json`; n={JD['n_anchors']} anchors {JD['first']}→{JD['last']}; cut {JD['cut']}; windows {JD['windows']}; {JD['units']}; bootstrap {JD['bootstrap']})")
    P("| arm | FPRED | seed | φ clip | 2025-03→26≤cut mean S DD %/yr [CI95] | 2026≤cut | 2025-03→12 | gross | w_king | turn/gross | cost/gross | carry/gross | swaps | mean age | max age | IC primary |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k, row in JD["levels"].items():
        m = JD["arms"][k]; p = row[PW]; b = p.get("boot", {}); q = row["2026<=cut"]; r12 = row["2025-03->12"]; ic = row.get("ic_primary")
        s_age = f"{row['mean_age']:.2f}" if isinstance(row["mean_age"], float) else "-"; s_ic = f"{ic['mean']:+.4f}" if ic else "-"; s_sw = str(row["swaps"]) if row["swaps"] is not None else "-"; s_mx = str(row["max_age"]) if row["max_age"] is not None else "-"
        P(f"| {k} | {m['FPRED']} | {m['FSEED']} | {m['PHIDYN_CLIP']} | {p['mean']:+.3f} S{p['sharpe']:+.2f} DD{p['maxDD_bps']:.0f} {p['pct_gross_yr']:+.1f}% [{b.get('lo', float('nan')):+.3f},{b.get('hi', float('nan')):+.3f}] | {q['mean']:+.3f} S{q['sharpe']:+.2f} DD{q['maxDD_bps']:.0f} | {r12['mean']:+.3f} S{r12['sharpe']:+.2f} | {p['gross']:.3f} | {p['w_king']:.3f} | {p['turn_per_gross']:.5f} | {p['cost_per_gross']:.3f} | {p['carry_per_gross']:+.3f} | {s_sw} | {s_age} | {s_mx} | {s_ic} |")
    P("\n## T5 · Paired deltas per gross (VERIFIED `results/judge_gate.json`; Δ [CI95] P(Δ>0); months +/n = calendar months with positive Δ sum in the primary window)")
    P("| pair | pre-2025 | 2025-01/02 | 2025-03→12 | 2026≤cut | **2025-03→26≤cut** | ΔSharpe | Δturn% | maxDD ref→x | months + | best month (share) | Δ w/o best month |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name, d in JD["deltas"].items():
        w = d["windows"]; c = lambda k: (f"{w[k]['mean']:+.4f} [{w[k]['lo']:+.4f},{w[k]['hi']:+.4f}] P{w[k]['P>0']:.2f}" + (" (=0)" if w[k]["exact_zero"] else "")) if k in w else "n/a"
        bs = d["best_month_share"]; s_bs = f"{bs*100:+.0f}%" if bs is not None else "n/a"; bm = d["monthly_contrib"][d["best_month"]]["sum_bps"]; db = d["drop_best_month"]
        P(f"| {name} | {c('pre-2025')} | {c('2025-01/02')} | {c('2025-03->12')} | {c('2026<=cut')} | **{c(PW)}** | {d['dSharpe'][PW]:+.3f} | {d['dturn_pct_primary']:+.1f}% | {d['maxDD_ref']:.0f}→{d['maxDD_x']:.0f} | {d['n_months_pos']}/{d['n_months']} | {d['best_month']} {bm:+.0f} bps ({s_bs}) | {db['mean']:+.4f} [{db['lo']:+.4f},{db['hi']:+.4f}] |")
    P("\n## T6 · Per-month Δ contribution (sum of Δg per calendar month, bps gross; primary window) for the gate arms vs R0(mE1)")
    names = [n for n in JD["deltas"] if n.endswith("− R0(mE1)")]
    if names:
        mos = list(JD["deltas"][names[0]]["monthly_contrib"].keys()); P("| month | " + " | ".join(n.replace(" − R0(mE1)", "") for n in names) + " |"); P("|---|" + "---|" * len(names))
        for mo in mos: P(f"| {mo} | " + " | ".join(f"{JD['deltas'][n]['monthly_contrib'][mo]['sum_bps']:+.1f}" for n in names) + " |")
        P("| **total** | " + " | ".join(f"**{JD['deltas'][n]['total_bps']:+.1f}**" for n in names) + " |")
    if JD["phidyn"]:
        P("\n## T7 · φdyn (PHIDYN, clip [0.30, 0.60], look 900; VERIFIED `results/judge_gate.json` phidyn)"); P("| arm | φ mean | min | max | share at 0.30 | share at 0.60 | share = 0.45 (warm-up/fallback) | crossings of 0.45 | jumps ≥0.05 | φ 2025 | φ 2026 |"); P("|---|---|---|---|---|---|---|---|---|---|---|")
        for k, v in JD["phidyn"].items(): P(f"| {k} | {v['phi_mean']:.3f} | {v['phi_min']:.3f} | {v['phi_max']:.3f} | {v['share_at_lower_clip']:.3f} | {v['share_at_upper_clip']:.3f} | {v['share_eq_0.45']:.3f} | {v['n_cross_0.45']} | {v['n_jumps_ge_0.05']} | {v['phi_by_year'].get('2025', float('nan')):.3f} | {v['phi_by_year'].get('2026', float('nan')):.3f} |")
    P("\n## T8 · Frozen judge §A4 (VERIFIED `results/judge_gate.json` judge)"); P("```"); P(json.dumps(JD["judge"], indent=1, ensure_ascii=False)); P("```")
P("\n## T9 · Commands (verbatim)")
for p in (f"{G}/logs/commands.txt", f"{G}/replay/logs/commands.txt", f"{G}/replay/logs/eq_chain.log", f"{G}/replay/logs/check_equiv.log"):
    if os.path.exists(p):
        P(f"\n`{p}`:"); P("```")
        for ln in open(p): P(ln.rstrip()[:500])
        P("```")
open(f"{G}/REPORT_tables.md", "w").write("\n".join(L) + "\n"); print(f"wrote {G}/REPORT_tables.md ({len(L)} lines)")
