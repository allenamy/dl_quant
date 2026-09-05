"""render_results.py — turn results/*.json into markdown sections (gate table, G1 classification, G2 attribution, G3, G4, download/patch
receipts). Pure rendering: every number comes from a results file written by a gate script; nothing is computed here except formatting."""
import os, json, glob, hashlib, time
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")
def J(name):
    p = f"{ROOT}/results/{name}"; return json.load(open(p)) if os.path.exists(p) else None
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def pf(x): return "PASS" if x else "FAIL"
L = []
g1, g2a, g2bc, g3, g4a, g4b, g4v, cm, ck, dg, pin, alt = (J(n) for n in ("G1.json", "G2a.json", "G2bc.json", "G3.json", "G4a.json", "G4b.json", "G4_verdict.json", "compare_meta.json", "compare_king.json", "diag_g2a.json", "pinned_on_hist_receipt.json", "alt_meta_receipt.json"))
L.append("## Gate table (frozen rules: PREREG_second_instrument_rebuild_2026-09-05 §2)\n")
L.append("| gate | frozen rule | verdict | printed evidence |"); L.append("|---|---|---|---|")
if g1:
    L.append(f"| G1 panel bitwise | every array: NaN positions + finite values bitwise vs v1 | **{pf(g1['G1_PASS'])}** | results/G1.json: {sum(1 for c in g1['columns'].values() if c['pass'])}/{len(g1['columns'])} arrays bitwise; ts equal {g1['ts']['equal']} ({g1['ts']['n_rebuilt']} vs {g1['ts']['n_v1']}) |")
    if "G1b" in g1 and "channels" in g1["G1b"]:
        ch = g1["G1b"]["channels"]; L.append(f"| G1b cache 2022+ vs _ext | informational | — | common ts {g1['G1b']['n_common_ts']}; unequal share per channel: " + ", ".join(f"{k} {v['unequal_share']:.1e} (nan-mismatch {v['n_nan_mismatch']})" for k, v in ch.items()) + " |")
if g2a: L.append(f"| G2(a) nets bitwise | stage-6 nets vs real 08-21 nets (ref/, pod copies are 144-byte stubs) | **{pf(g2a['G2a_PASS'])}** | results/G2a.json: d30 bitwise share {g2a['arms']['nets_histv2_-30_2_42.npy']['bitwise_equal_share']:.4f}, max|Δ| {g2a['arms']['nets_histv2_-30_2_42.npy']['max_abs_diff_bps']:.3e} bps, corr {g2a['arms']['nets_histv2_-30_2_42.npy']['corr']:.4f}; ts equal {g2a['arms']['nets_histv2_-30_2_42.npy']['ts_equal']} |")
if g2bc:
    b = g2bc["G2b"]; L.append(f"| G2(b) per-gross series | ts set identical AND max|Δ| ≤ 1e-6 bps | **{pf(b['pass'])}** | ts_set_identical {b['ts_set_identical']} (step8 {b['n_step8']} vs ref {b['n_ref']}, ref⊂step8 {b['ref_ts_subset_of_step8']}); common {b['n_common']}: max|Δ| {b['max_abs_diff_bps_per_gross']:.3e}, corr {b['corr']:.4f} |")
    c = g2bc["G2c"]; L.append(f"| G2(c) device parity | log ≤1e-6 PASS and simple FAIL | **{pf(c['pass'])}** | maxabs_diff_vs_pod_backup: log S0 {c['per_caliber'].get('log', {}).get('S0', {}).get('maxabs_diff_vs_pod_backup', float('nan')):.3e} / d30 {c['per_caliber'].get('log', {}).get('d30_n2_c42', {}).get('maxabs_diff_vs_pod_backup', float('nan')):.3e}; simple S0 {c['per_caliber'].get('simple', {}).get('S0', {}).get('maxabs_diff_vs_pod_backup', float('nan')):.3e} / d30 {c['per_caliber'].get('simple', {}).get('d30_n2_c42', {}).get('maxabs_diff_vs_pod_backup', float('nan')):.3e} |")
if g3:
    L.append(f"| G3(a) static census | 0 log/expm1 hits on a return quantity in the 4 scripts | **{pf(g3['a_static']['pass'])}** | {g3['a_static']['n_return_path_hits']} return-path hits; volume-channel hits: " + "; ".join(f"{f}:{h['line']}" for f, v in g3['a_static']['census'].items() for h in v['hits']) + " |")
    L.append(f"| G3(b1) Y4 == Σ ret5 | full grid bitwise incl. NaN positions | **{pf(g3['b1_Y4_sum']['pass'])}** | both-finite {g3['b1_Y4_sum']['n_cells_both_finite']}, neq {g3['b1_Y4_sum']['n_neq']}, nan-mismatch {g3['b1_Y4_sum']['n_nan_mismatch']}; direct float64 window sum on 300 anchors neq {g3['b1_Y4_sum']['direct_float64_window_sum_sample']['n_neq']}/{g3['b1_Y4_sum']['direct_float64_window_sum_sample']['n_cells']} |")
    b2 = g3["b2_y4s_vs_raw"]; L.append(f"| G3(b2) y4s vs raw closes | ≥1000 anchors (≥300 in 2020-21), max|Δ| ≤ 2e-5 | **{pf(b2['pass'])}** | n {b2['n_sampled']} (2020-21: {b2['n_2020_21']}); max|Δ| {b2['max_abs_diff_all']:.3e}, p99 {b2['p99_abs_diff']:.2e}, median {b2['median_abs_diff']:.2e}; cells >2e-5: {b2.get('n_cells_over_2e-5')} (within 1.5× float16 bound: {b2.get('n_cells_over_2e-5_within_f16_bound')}); max |Δ|/f16_bound {b2.get('max_ratio_absdiff_over_f16_bound', float('nan')):.2f} |")
if g4v:
    it = g4v["items"]; L.append(f"| G4 leakage battery | (i)…(vi) all pass | **{pf(g4v['hist_king_admitted'])}** | (i) {pf(it['i'])} (ii) {pf(it['ii'])} (iii) {pf(it['iii'])} (iv) {pf(it['iv'])} (v) {pf(it['v'])} (vi) {pf(it['vi'])}; hist king admitted to G5: {g4v['hist_king_admitted']} |")
L.append("")
if g1 and not g1["G1_PASS"]:
    L.append("## G1 classification (per array; unequal = both finite and different; nan-mismatch = finite on one side only)\n")
    L.append("| array | pass | n both-finite | n unequal | n nan-mismatch (NaN only in rebuilt / only in v1) | max|Δ| | max rel | symbols affected | class |"); L.append("|---|---|---|---|---|---|---|---|---|")
    for k, c in g1["columns"].items():
        if c.get("kind") == "float": L.append(f"| {k} | {pf(c['pass'])} | {c['n_finite_both']} | {c['n_neq']} | {c['n_nan_mismatch']} ({c['n_nan_only_rebuilt']} / {c['n_nan_only_v1']}) | {c['max_abs_diff']:.2e} | {c['max_rel_diff']:.1e} | {c.get('n_symbols_affected', 0)} | {c.get('class', '')} |")
        else: L.append(f"| {k} | {pf(c['pass'])} | — | {c['n_neq']} | — | — | — | — | bool |")
    L.append("\nPer-year detail for failing arrays (n unequal / n nan-mismatch / max|Δ|):\n")
    for k, c in g1["columns"].items():
        if c.get("kind") == "float" and not c["pass"]: L.append(f"- `{k}`: " + " | ".join(f"{y}: {v['n_neq']}/{v['n_nan_mismatch']}/{v['max_abs_diff']:.1e}" for y, v in c["by_year"].items()) + f"; top symbols {c.get('top_symbols', [])[:6]}")
    if "Y4_hand_check" in g1: L.append("\nY4 hand check from raw zips: " + json.dumps(g1["Y4_hand_check"]))
    L.append("")
if cm: L.append(f"## Meta vs 08-21 meta (informational)\n\nE_ts equal {cm['E_ts']['equal']} ({cm['E_ts']['n_rebuilt']} vs {cm['E_ts']['n_ref']}; {cm['E_ts']['first_rebuilt']}..{cm['E_ts']['last_rebuilt']} vs {cm['E_ts']['first_ref']}..{cm['E_ts']['last_ref']}); names equal {cm['names_equal']}; members equal {cm['members']['n_equal']}/{cm['members']['n_common_anchors']}; y4 unequal {cm['y4']['n_neq']} nan-mismatch {cm['y4']['n_nan_mismatch']}; qvk unequal {cm['qvk']['n_neq']}; BITWISE_ALL {cm['bitwise_all']}\n")
if ck:
    L.append("## King rebuilt vs 08-21 king (informational)\n"); L.append("| year | n anchors | finite frac rebuilt/ref | finite mask equal | Pearson(pred) | bitwise share | IC rebuilt | IC ref |"); L.append("|---|---|---|---|---|---|---|---|")
    for y, v in ck["by_year"].items(): L.append(f"| {y} | {v['n_anchors']} | {v['finite_frac_rebuilt']:.4f}/{v['finite_frac_ref']:.4f} | {v['finite_mask_equal']} | {v['pearson_pred']:.4f} | {v['bitwise_equal_share']:.4f} | {v['ic_rebuilt']:+.4f} | {v['ic_ref']:+.4f} |")
    if "fold_ic_rebuilt" in ck: L.append(f"\nfold IC (script json): rebuilt {ck['fold_ic_rebuilt']['ic_by_year']} vs 08-21 {ck['fold_ic_ref']['ic_by_year']}\n")
if g4a and g4b:
    L.append("## G4 leakage battery detail\n")
    for f in g4a["i_causality"]["folds"]: L.append(f"- (i) fold {f['YV']}: " + (f"train {f['n_train_anchors']} anchors, max(train E_ts)+4h = {f['max_train_Ets_plus_label']} ≤ first test {f['min_test_Ets']} (gap {f['gap_s']} s), overlap {f['overlap']} → {pf(f['pass'])}" if 'gap_s' in f else f"{f.get('note')} → FAIL"))
    ii = g4a["ii_foldout"]; L.append(f"- (ii) pre-2022 anchors {ii['n_pre2022_anchors']} with finite cells {ii['n_pre2022_finite_cells']}; finite mask == member∧finite(y4) for {ii['n_anchors_checked'] - ii['n_mask_mismatch']}/{ii['n_anchors_checked']} anchors; unused anchors with values {ii['n_unused_anchors_with_values']} → {pf(ii['pass'])}")
    for nm, v in g4a["vi_feature_window"]["features"].items(): L.append(f"- (vi) {nm}: window [E-w,E-1] bitwise {v['bitwise_equal_window_[E-w,E-1]']}/{v['n']}; shifted window [E-w+1,E] differs in {v['differs_window_[E-w+1,E]']}/{v['n']}")
    L.append(f"- (vi) → {pf(g4a['vi_feature_window']['pass'])}")
    L.append("- (iii) shuffle-future null (per seed × fold): " + "; ".join(f"s{r['seed']}/{r['fold']}: " + (f"null {r['null_ic']:+.4f} vs 2·SE {2*r['se_true']:.4f} (true {r['true_ic']:+.4f}) {pf(r['pass'])}" if not r.get('skipped') else "SKIPPED") for r in g4b["iii_shuffle_null"]["runs"]) + f" → {pf(g4b['iii_shuffle_null']['pass'])}")
    if "info_not_gate" in g4b["iii_shuffle_null"]: L.append("  - information (not the gate): " + "; ".join(f"{y}: seed-mean null {v['null_ic_seed_mean']:+.4f}, 2·SE_anchor {2*v['se_anchor']:.4f}, 2·SE_dayblock {2*v['se_dayblock']:.4f}" for y, v in g4b["iii_shuffle_null"]["info_not_gate"].items()))
    sp = g4b["iv_offset_spectrum"]; L.append(f"- (iv) offset spectrum k=-6..6: " + " ".join(f"{k}:{float(v):+.4f}" for k, v in sp["spectrum"].items()) + f"; peak k={sp['peak_k']}, max|corr(k=1..3)|={sp['max_abs_k1_3']:.4f} < corr(0)={sp['corr0']:.4f} → {pf(sp['pass'])} (n anchors {sp['n_anchors']})")
    for y, v in g4b["v_embargo"]["folds"].items(): L.append(f"- (v) fold {y}: IC no-embargo refit {v['ic_no_embargo_refit']:+.5f} (stage-5 file {v['ic_stage5_file']:+.5f}, refit==file {v['refit_reproduces_stage5']}), embargo-60 {v['ic_embargo60']:+.5f}, Δ {v['delta_vs_refit']:+.5f} → {pf(v['pass'])}")
    L.append("")
if g2bc:
    a = g2bc["attribution"]; L.append("## G2 attribution\n")
    L.append(f"- ATTR(1) device form (same meta/panel/king; w10 recheck device vs pod_stop_arms_v3): common {a['1_device_form']['n_common']}, max|Δ| {a['1_device_form']['max_abs_diff_bps']:.2e} bps, mean Δ {a['1_device_form']['mean_diff_bps']:+.4f}, corr {a['1_device_form']['corr']:.4f}; by year Δ: " + ", ".join(f"{y} {v:+.3f}" for y, v in a['1_device_form']['by_year_diff'].items()))
    L.append(f"- ATTR(2) inputs (stage-6 rebuilt nets vs real 08-21 nets): common {a['2_inputs_vs_0821']['n_common']}, max|Δ| {a['2_inputs_vs_0821']['max_abs_diff_bps']:.2e}, mean Δ {a['2_inputs_vs_0821']['mean_diff_bps']:+.4f}, corr {a['2_inputs_vs_0821']['corr']:.4f}; by year (stage6/0821): " + ", ".join(f"{y} {a['2_inputs_vs_0821']['by_year_stage6'][y]:+.3f}/{a['2_inputs_vs_0821']['by_year_0821'][y]:+.3f}" for y in a['2_inputs_vs_0821']['by_year_stage6']))
    L.append(f"- ATTR(3) gross: step-8 gross_total mean {a['3_gross']['mean_gross_step8']:.4f} vs 08-21 implied {a['3_gross']['mean_gross_implied_0821']:.4f}")
    b = g2bc["G2b"]; L.append(f"- G2(b) by year (step8 per-gross / 08-21 per-gross / Δ): " + ", ".join(f"{y} {b['by_year_step8'][y]:+.3f}/{b['by_year_ref'][y]:+.3f}/{b['by_year_diff'][y]:+.3f}" for y in b['by_year_step8']) + "\n")
if dg:
    L.append("## DIAGNOSTIC for G2(a) (not a gate, not a G5 arm)\n")
    L.append(f"- v1 funding symbols {dg['v1_funding_symbols']} vs rebuilt {dg['rebuilt_funding_symbols']}; 08-21 king re-indexed: {dg['king0821_reindexed']['n_mapped']}/{dg['king0821_reindexed']['n_rebuilt_anchors']} anchors (grids identical {dg['king0821_reindexed']['identical_grid']})")
    L.append("- residual funding mismatch after masking to the 450 symbols: " + "; ".join(f"{k}: unequal {v['n_neq']}, nan-mismatch {v['n_nan_mismatch']}, max|Δ| {v['max_abs_diff']:.1e}" for k, v in dg["residual_funding_mismatch_after_mask"].items()))
    for key, lab in (("DIAG_A_masked_funding_plus_0821_king", "DIAG-A (funding masked to 08-21 coverage + real 08-21 king)"), ("DIAG_B_rebuilt_panel_plus_0821_king", "DIAG-B (rebuilt 829-symbol funding + real 08-21 king)")):
        for f, v in dg[key].items():
            L.append(f"- {lab} `{f}`: n {v['n']}/{v['n_ref']} (first {v.get('first_diag')} vs {v.get('first_ref')}), bitwise {v['bitwise_share']:.4f}, max|Δ| {v['max_abs_diff_bps']:.2e}, mean Δ {v['mean_diff_bps']:+.4f}, corr {v['corr']:.5f}; by year diag/0821 (bitwise share): " + ", ".join(f"{y} {w['diag']:+.3f}/{w['ref0821']:+.3f} ({w.get('bitwise_share', float('nan')):.2f})" for y, w in v["by_year"].items()))
    L.append("")
if g3:
    L.append("## G3 detail\n"); L.append("- (b3) Σ-simple[E,E+47] − Π(1+r)−1[E+1,E+48], cell level per year (bps): " + "; ".join(f"{y}: {v['mean_y4old_minus_y4s_bps']:+.3f} (|·| {v['mean_abs_bps']:.2f}, n {v['n_cells']})" for y, v in g3["b3_sum_vs_prod_info"].items()))
    L.append("- (b2) worst cells: " + json.dumps(g3["b2_y4s_vs_raw"]["worst"][:3]) + "\n")
if pin: L.append(f"## Adapter receipts\n\n- pinned king re-indexed onto the hist grid: src {pin['src_sha256'][:16]} shape {pin['src_shape']} → {pin['dst_shape']}, mapped {pin['n_dst_anchors_mapped']} anchors, rows bitwise equal {pin['rows_bitwise_equal_to_src']}; finite by year {pin['finite_frac_by_year']}")
if alt: L.append(f"- prod-caliber meta: oldsum vs meta y4 exact_eq {alt['parity_oldsum_vs_meta_y4']['exact_eq']}, newprod vs dlw y4s exact_eq {alt['newprod_vs_dlw_y4s']['exact_eq']} (cells {alt['newprod_vs_dlw_y4s']['cells']}), per-year Π−Σ (bps): " + ", ".join(f"{y} {v['mean_newprod_minus_oldsum']:+.3f}" for y, v in alt["by_year_bps"].items()) + "\n")
# patches + input identity
L.append("## Patches (logs/patches/*.diff) and key file hashes\n"); L.append("| file | sha256 | size |"); L.append("|---|---|---|")
for p in sorted(glob.glob(f"{ROOT}/logs/patches/*.diff")): L.append(f"| {os.path.basename(p)} | {sha(p)[:16]} | {os.path.getsize(p)} |")
for p in ["data/dlnative_5m_wide829_f16_hist.npz", "data/wide_panel_4h_hist_v2_rebuilt.npz", "data/wide_fea_hist_rebuilt.npy", "data/wide_fea_hist_meta_rebuilt.npz", "data/slow_pred_hist_oos_rebuilt.npy", "data/nets_histv2_-30_2_42.npy", "data/nets_histv2_0_0_0.npy", "data/dlw_hist/data/dlw_targets.npz", "data/meta_hist_newprod.npz", "data/slow_pred_pinned_on_hist.npy", "logs/klines5m_SHA256SUMS.txt", "logs/klines5m_404.txt"]:
    q = f"{ROOT}/{p}"
    if os.path.exists(q): L.append(f"| {p} | {sha(q)[:16]} | {os.path.getsize(q)} |")
out = "\n".join(L) + "\n"
open(f"{ROOT}/results/RESULTS_render.md", "w").write(out); print(out)
