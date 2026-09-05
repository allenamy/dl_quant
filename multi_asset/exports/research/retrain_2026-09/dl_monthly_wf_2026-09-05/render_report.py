"""render_report.py — dl_monthly_wf: render REPORT_tables.md from the json artifacts (fold tables, IC/agreement/age/leakage, replay judge, receipts, commands).
Reads only; writes REPORT_tables.md. The narrative head (REPORT_head.md) is written by hand after the numbers; REPORT.md = head + tables."""
import os, json, glob, hashlib, time
R = "/workspace/review_scratch/dl_monthly_wf"
def J(p):
    return json.load(open(p)) if os.path.exists(p) else None
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else "MISSING"
def f4(v): return "n/a" if v is None else f"{v:+.4f}"
def f3(v): return "n/a" if v is None else f"{v:+.3f}"
L = []; P = L.append
TAGS = [t for t in ("mE60", "mE1") if os.path.exists(f"{R}/results/f10_V2MAIN_{t}_s42.json")]
RES = {t: J(f"{R}/results/f10_V2MAIN_{t}_s42.json") for t in TAGS}
IC = J(f"{R}/logs/ic_{'_'.join(TAGS)}.json"); LK = J(f"{R}/logs/leakcheck_{'_'.join(TAGS)}.json"); JD = J(f"{R}/replay/results/judge_dl.json")
ST = {t: J(f"{R}/logs/stitch_{t}.json") for t in TAGS}
# ───────── T1 receipts ─────────
P("## T1 · Devices, inputs, receipts (VERIFIED = printed by the scripts named)")
P("| item | value |"); P("|---|---|")
P(f"| verbatim trainer | `/workspace/pod_f10_train_ext.py` sha256 `{sha('/workspace/pod_f10_train_ext.py')}` |")
P(f"| monthly trainer | `{R}/pod_f10_train_monthly.py` sha256 `{sha(f'{R}/pod_f10_train_monthly.py')}` = verbatim lines 1–260 (byte-identical, `cmp` receipt in run log) + `monthly_section.py` sha256 `{sha(f'{R}/monthly_section.py')}`; `trainer.diff` {sum(1 for _ in open(f'{R}/trainer.diff')) if os.path.exists(f'{R}/trainer.diff') else 'n/a'} lines |")
for t in TAGS:
    r = RES[t]
    P(f"| {t} run self-report | arm {r['arm']} seed {r['seed']} cost {r['cost']} ldd {r['ldd']} afix {r['afix']} epochs {r['epochs']} lr {r['lr']} win/burn/stride {r['win']}/{r['burn']}/{r['stride']} embargo **{r['embargo']}**; torch {r.get('torch')} cuda {r.get('cuda')} gpu {r.get('gpu')}; self_sha {r['self_sha256'][:16]} base_sha {r.get('base_sha256', '')[:16]} |")
    P(f"| {t} inputs | targets `{r['targets_sha256'][:16]}` fea82 `{r['fea82_sha256'][:16]}` fea89 `{r['fea89_sha256'][:16]}` legs `{r.get('legs_sha256', '')[:16]}` (targets/fea82/fea89 asserted == 09-01 gate run `f8_ext/results/f10_V2MAIN_s42.json`) |")
    P(f"| {t} env given | `{json.dumps(r.get('env_given', {}), ensure_ascii=False)}` |")
    P(f"| {t} fold rule | `{json.dumps(r.get('fold_rule', {}), ensure_ascii=False)}` |")
P(f"| replay device | `{R}/replay/w10_health.py` sha256 `{sha(f'{R}/replay/w10_health.py')}` (= health_check w10_health.py) |")
P(f"| replay masks/cost | umask_UPIT `{sha('/workspace/review_scratch/health_check/masks/umask_UPIT.npz')[:16]}` costb_fee_steady `{sha('/workspace/review_scratch/health_check/calib/costb_fee_steady.json')[:16]}` meta_newprod `{sha('/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz')[:16]}` pinned king `{sha('/workspace/shadow_bundle_v3/slow_pred_pinned.npy')[:16]}` |")
P(f"| yearly-fold file (baseline) | `/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy` sha256 `{sha('/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy')}` |")
for t in TAGS:
    P(f"| stitched {t} (ext grid, pure) | `{R}/preds/f10_V2MAIN_{t}_s42.npy` sha256 `{sha(f'{R}/preds/f10_V2MAIN_{t}_s42.npy')}` |")
    if ST.get(t):
        o = ST[t][t]["outputs"]["dev_alt"]; P(f"| replay inputs {t} (0822 grid) | " + "; ".join(f"`{k}` {v[:16]}" for k, v in o.items()) + f"; coverage {ST[t][t]['coverage_by_month']}; overlap finite-mask == yearly {ST[t][t]['overlap_2025_to_0810_finite_mask_equal_to_yearly']} (rows diff {ST[t][t]['overlap_rows_with_mask_diff']}, cells {ST[t][t]['overlap_cells_with_mask_diff']}) |")
ce = f"{R}/replay/logs/check_equiv.log"
if os.path.exists(ce):
    for ln in open(ce): P(f"| equivalence receipt | {ln.strip()[:400]} |")
# ───────── T2 fold tables ─────────
for t in TAGS:
    r = RES[t]; P(f"\n## T2 · Fold table {t} (embargo {r['embargo']} anchors; VERIFIED `results/f10_V2MAIN_{t}_s42.json`; wall-clock per fit on the RTX PRO 4500)")
    P("| test month | n_test | n_train | max train label end | cutoff | causal | windows/epoch | best ep | best va | α* | net bps/anchor (train frame) | ES5 | turnover | wall s | s/epoch | test-month IC |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    walls = []
    for m, f in sorted(r["folds"].items()):
        ic = IC["monthly_ic"].get(m, {}).get(t, {}).get("ic") if IC else None
        walls.append(f["wall_clock_s"])
        P(f"| {m} | {f['n_test']} | {f['n_train']} | {f['max_train_label_end']} | {f['cutoff']} | {'OK' if f['causality_ok'] else 'FAIL'} | {f['n_windows_per_epoch']} | {f['best_epoch']} | {f['best_va']:+.3f} | {f['alpha_final']:.4f} | {f['net_mean_bps']:+.3f} | {f['es5_bps']:.1f} | {f['turnover_mean']:.4f} | {f['wall_clock_s']:.0f} | {sum(f['epoch_s'])/len(f['epoch_s']):.1f} | {f4(ic)} |")
    if walls: P(f"\nwall-clock: {len(walls)} fits, mean {sum(walls)/len(walls):.0f} s, min {min(walls):.0f} s, max {max(walls):.0f} s, total {sum(walls)/3600:.2f} h")
# ───────── T3 IC ─────────
if IC:
    P("\n## T3 · Score-level: IC levels, paired ΔIC vs yearly, overlap agreement (VERIFIED `logs/ic_*.json`; ext-grid dlw targets y4s = Π(1+r5)−1; rank IC per anchor over members)")
    P("| window / file | n | IC mean | anchor s.e. | share>0 |"); P("|---|---|---|---|---|")
    for k, v in IC["ic_levels"].items(): P(f"| {k} | {v['n']} | {v['mean']:+.4f} | {v['se_anchor']:.4f} | {v['share_pos']:.3f} |")
    P("\n| ΔIC pair (window) | n | Δ mean | anchor s.e. | CI95 day-block | P(Δ>0) |"); P("|---|---|---|---|---|---|")
    for k, v in IC["ic_delta_vs_yearly"].items():
        if "mean" in v: P(f"| {k} | {v['n']} | {v['mean']:+.4f} | {v['se_anchor']:.4f} | [{v['ci95_dayblock'][0]:+.4f}, {v['ci95_dayblock'][1]:+.4f}] | {v['p_gt0']:.3f} |")
    P("\n| overlap agreement (per-anchor Spearman monthly vs yearly) | n | mean | median | p5 | p95 | min |"); P("|---|---|---|---|---|---|---|")
    for k, v in IC["agreement"].items(): P(f"| {k} | {v['n']} | {v['mean']:.4f} | {v['median']:.4f} | {v['p5']:.4f} | {v['p95']:.4f} | {v['min']:.4f} |")
    P("\n| test month | " + " | ".join(IC["monthly_ic"][next(iter(IC["monthly_ic"]))].keys()) + " |"); P("|---|" + "---|" * len(IC["monthly_ic"][next(iter(IC["monthly_ic"]))]))
    for m, row in IC["monthly_ic"].items(): P(f"| {m} | " + " | ".join(f4(row[k]["ic"]) for k in row) + " |")
    P("\n## T4 · IC by model age (each fold model scores its month and the following five; paired on anchors where all six ages exist; VERIFIED `logs/ic_*.json` age_curve)")
    P("| variant | n anchors | span | age1 | age2 | age3 | age4 | age5 | age6 | Δ(1−2) | Δ(1−3) | Δ(1−4) | Δ(1−5) | Δ(1−6) [CI95] | age1 == stitched (max abs) |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for t, c in IC["age_curve"].items():
        ib = c["ic_by_age"]; d = c["delta_age1_minus"]
        P(f"| {t} | {c['n_anchors_all6']} | {c.get('first')} → {c.get('last')} | " + " | ".join(f4(ib.get(str(a))) for a in range(1, 7)) + " | " + " | ".join(f"{d[str(a)]['mean']:+.4f}" for a in range(2, 6) if str(a) in d)
          + (f" | {d['6']['mean']:+.4f} [{d['6']['ci95_dayblock'][0]:+.4f},{d['6']['ci95_dayblock'][1]:+.4f}]" if "6" in d else " | n/a") + f" | {c.get('age1_equals_stitched_maxabs')} |")
    P("\n## T5 · F10 score-leg return by window (rank-leg on dlw members, bps/anchor per unit gross; VERIFIED `logs/ic_*.json` leg_levels)")
    P("| window / file | n | mean bps | Sharpe(anchor) | %/gross/yr |"); P("|---|---|---|---|---|")
    for k, v in IC["leg_levels"].items(): P(f"| {k} | {v['n']} | {v['mean_bps']:+.3f} | {v['sharpe_anchor']:+.2f} | {v['pct_gross_yr']:+.1f} |")
    P("\n| Δ leg vs yearly (window/variant) | n | Δ mean | CI95 day-block | P(Δ>0) |"); P("|---|---|---|---|---|")
    for k, v in IC["leg_delta_vs_yearly"].items():
        if "mean" in v: P(f"| {k} | {v['n']} | {v['mean']:+.3f} | [{v['ci95_dayblock'][0]:+.3f}, {v['ci95_dayblock'][1]:+.3f}] | {v['p_gt0']:.3f} |")
# ───────── T6 leakage ─────────
if LK:
    P("\n## T6 · Leakage gate V3′ on the stitched files (VERIFIED `logs/leakcheck_*.json`)")
    P(f"yearly spectrum on the common window ({LK['common_window']}): " + " ".join(f"k{int(k):+d}:{v:+.4f}" for k, v in LK["yearly_spectrum_common"].items()))
    P("| file | n test anchors | own spectrum k−3..+3 (full) | common-window spectrum | ① future no peak (full / stride) | ② max|Δ| vs yearly (common) | ③ pre-fold finite | verdict |"); P("|---|---|---|---|---|---|---|---|")
    for t, v in LK["files"].items():
        P(f"| {t} | {v['n_test_anchors']} | " + " ".join(f"{x:+.4f}" for x in v["spectrum_own_full"].values()) + " | " + " ".join(f"{x:+.4f}" for x in v["spectrum_common"].values())
          + f" | {'OK' if v['c1_future_no_peak_full'] else 'FAIL'} / {'OK' if v['c1_future_no_peak_stride'] else 'FAIL'} (max future {v['max_abs_future_full']:.4f}) | {v['c2_shape_vs_yearly_maxabs']:.4f} {'OK' if v['c2_pass'] else 'FAIL'} | {v['c3_prefold_finite']} {'OK' if v['c3_pass'] else 'FAIL'} | {'PASS' if (v['c1_future_no_peak_full'] and v['c2_pass'] and v['c3_pass']) else 'FAIL'} |")
    P(f"\nV3P_GATE_MONTHLY {LK['verdict']}")
# ───────── T7 replay ─────────
if JD:
    P(f"\n## T7 · Replay (device w10_health.py, arm d30_n2_c42, U-PIT · m1 · prod · fee-only · LEGS=101 · LOOK=900 · msharpe · FTRIM zero; n={JD['n_anchors']} anchors {JD['first']}→{JD['last']}; cut {JD['cut']}; VERIFIED `replay/results/judge_dl.json`)")
    P(f"units: {JD['units']}; bootstrap {JD['bootstrap']}")
    P("| arm | FPRED | PHI | 2025 mean S DD %/yr | 2026≤cut | 2025→26≤cut [CI95] | 2024→26≤cut | gross | w_king | turn/gross | cost/gross | carry/gross | fires |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k, row in JD["levels"].items():
        m = JD["arms"][k]; c = lambda w: f"{row[w]['mean']:+.3f} S{row[w]['sharpe']:+.2f} DD{row[w]['maxDD_bps']:.0f} {row[w]['pct_gross_yr']:+.1f}%" if w in row else "n/a"
        r25 = row.get("2025->26<=cut", {}); b = r25.get("boot", {})
        P(f"| {k} | {m['FPRED']} | {m['PHI']} | {c('2025')} | {c('2026<=cut')} | {c('2025->26<=cut')} [{b.get('lo', float('nan')):+.3f},{b.get('hi', float('nan')):+.3f}] | {c('2024->26<=cut')} | {r25.get('gross', float('nan')):.3f} | {r25.get('w_king', float('nan')):.3f} | {r25.get('turn_per_gross', float('nan')):.5f} | {r25.get('cost_per_gross', float('nan')):.3f} | {r25.get('carry_per_gross', float('nan')):+.3f} | {r25.get('fires', 0)} |")
    P("\n| Δ pair | pre-2025 | 2025 | 2026≤cut | **2025→26≤cut** | postcut | ΔSharpe 25on | Δturn% | maxDD ref→x (bps gross) |"); P("|---|---|---|---|---|---|---|---|---|")
    for name, d in JD["deltas"].items():
        w = d["windows"]; c = lambda k: (f"{w[k]['mean']:+.4f} [{w[k]['lo']:+.4f},{w[k]['hi']:+.4f}] P{w[k]['P>0']:.2f}" + (" (=0)" if w[k]["exact_zero"] else "")) if k in w else "n/a"
        P(f"| {name} | {c('pre-2025')} | {c('2025')} | {c('2026<=cut')} | **{c('2025->26<=cut')}** | {c('2026-postcut')} | {d['dSharpe']['2025->26<=cut']:+.3f} | {d['dturn_pct']:+.1f}% | {d['maxDD_ref_25on']:.0f}→{d['maxDD_x_25on']:.0f} |")
    P("\n## T8 · Frozen comparison (lead's rule: 'monthly not worse than yearly' ⇔ 2025→26 CI95 upper of Δ(net_ex per gross) > 0 AND ΔIC ≥ 0; no admission decision)")
    P("| variant | book Δg 2025→26 [CI95] (spliced, primary) | upper>0 | pure-file sensitivity Δg [CI95] | ΔIC 2025→26 ± s.e. [CI95] | ΔIC≥0 | not worse |"); P("|---|---|---|---|---|---|---|")
    for t, c in JD["frozen_comparison"].items():
        d = c["book_delta_per_gross_2025->26"]; dp = c["book_delta_pure_sensitivity"]; ic = c["ic_delta_2025->26"]
        sd = f"{d['mean']:+.4f} [{d['lo']:+.4f},{d['hi']:+.4f}]" if d else "n/a"
        sdp = f"{dp['mean']:+.4f} [{dp['lo']:+.4f},{dp['hi']:+.4f}]" if dp else "n/a"
        sic = f"{ic['mean']:+.4f} ± {ic['se_anchor']:.4f} [{ic['ci95_dayblock'][0]:+.4f},{ic['ci95_dayblock'][1]:+.4f}]" if ic else "n/a"
        P(f"| {t} | {sd} | {c['book_CI95_upper>0']} | {sdp} | {sic} | {c['ic_delta>=0']} | **{c['monthly_not_worse_than_yearly']}** |")
# ───────── T9 commands ─────────
P("\n## T9 · Commands (verbatim from the command logs)")
for p in (f"{R}/logs/commands.txt", f"{R}/replay/logs/commands.txt", f"{R}/replay/logs/replay_chain.log", f"{R}/replay/logs/eq_chain.log"):
    if os.path.exists(p):
        P(f"\n`{p}`:"); P("```")
        for ln in open(p): P(ln.rstrip()[:600])
        P("```")
open(f"{R}/REPORT_tables.md", "w").write("\n".join(L) + "\n")
print(f"wrote {R}/REPORT_tables.md ({len(L)} lines)")
