#!/usr/bin/env python3
"""build_audit_data.py -- renders docs/audit_pipeline_2026-09-13/AUDIT_DATA.json and AUDIT_DATA.md (AUDIT_EXEC register format).
Reads only the committed device receipts in devices_data/receipts/ (AD_A..AD_H, AD_E) and fills every number from them; the register
wording is written here. No dataset is opened. Usage (repo root): python3 docs/audit_pipeline_2026-09-13/devices_data/build_audit_data.py
"""
import json, os, hashlib, collections

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); RC = os.path.join(HERE, "receipts")
def J(n): return json.load(open(os.path.join(RC, n)))
A, B, C, D, E, F, G, H = (J(x) for x in ("AD_A_inventory.json", "AD_B_funding_iv.json", "AD_C_cache_members.json", "AD_D_panel_holes.json",
                                           "AD_E_consumers_matrix.json", "AD_F_batch2.json", "AD_G_batch3.json", "AD_H_tradability.json"))
YRS = ["2022", "2023", "2024", "2025", "2026"]
def f(x, n=2): return f"{x:,.{n}f}"
def i(x): return f"{int(x):,}"
def pct(x, n=1): return f"{100.0 * x:.{n}f}%"
FA = {r["path"].replace("/workspace/", ""): r for r in A["files"]}
def S(p): return (FA[p].get("sha256") or "")[:16]

# ------------------------------------------------------------------ numbers pulled from receipts
c1 = C["C1_clip_bound_vs_patch"]; c1x = c1["x0910"]; c2 = C["C2_axis_survivorship"]; c3k = C["C3_forward_predicate"]["king_meta_rule"]; c3d = C["C3_forward_predicate"]["dl_targets_rule"]
c4 = C["C4_A0_forward_nonfinite_exits"]["42"]["by_year"]; c5 = C["C5_oof_masks"]; c6 = C["C6_universe_class_in_training_members"]
d2 = D["comparisons"]["v2ext"]; d3 = D["comparisons"]["v3splice"]; dk = d2["keys"]
bx = B["panels"]["v2ext_x0910"]; bx3 = B["panels"]["v3splice_x0910"]; b2 = B["panels"]["v2ext"]; b3 = B["panels"]["v3splice"]; tc = bx["tail_correction"]
f1 = F["F1_splice_vs_v2ext_funding_coverage"]; f2 = F["F2_fea82_fund_columns"]["by_year"]; f4 = F["F4_patch_bars_by_month"]
g1 = G["G1_v1_funding_symbols_vs_live_pins"]; g2 = G["G2_availability_flag_information"]
h1 = H["H1_cache"]; h1t = H["H1_x0910_tail"]; h2 = H["H2_A0_population"]["42"]["by_year"]; h2b = H["H2_A0_population"]["2027"]["by_year"]
h3 = H["H3_fund_rank_base_v2ext_f_fund_ema_v1"]; h4k = H["H4_training_rows"]["king_meta"]; h4d = H["H4_training_rows"]["dl_targets"]; h5 = H["H5_funding_after_death"]; h6 = H["H6_panel_elig_and_funding_on_dead"]
p2b = h5["P2_base_proxy_on_king_axis"]
mx = E["matrix"]

def yline(d, key, fmt=i): return " / ".join(fmt(d[y][key]) for y in YRS if y in d)
BASE_SH = [h3[y]["base_DEAD_mean"] / h3[y]["base_mean"] for y in YRS]; U_SH = [h2[y]["U_DEAD"] / h2[y]["U_pairs"] for y in YRS]
BASE_RNG = f"{100*min(BASE_SH):.1f}-{100*max(BASE_SH):.1f}%"; U_RNG = f"{100*min(U_SH):.1f}-{100*max(U_SH):.1f}%"

# ------------------------------------------------------------------ register
items = []
def add(**kw): items.append(kw)

add(id="TRD-01", layer="data layer / tradability definition (all panels, caches, metas, masks)",
    title="Dead perpetuals keep writing untraded rows with a frozen close and keep funding records; every eligibility rule in research reads them as live",
    what=("No research panel, cache, meta, mask or replay defines tradability by trades. After a perp stops trading the archive keeps writing 5m rows with zero trades and one frozen close; "
          f"in the canonical 5m cache {i(h1['symbols_dead_inside_cache'])} contracts stopped trading inside the cache and still carry {i(h1['post_death_signature']['post_death_untraded_rows'])} such rows, "
          f"every one with ret5 exactly 0, log_qv exactly 0 and cpos/tbf NaN ({h1t['symbols_dead_before_2026-09-01_still_writing_untraded_rows']} of them still write frozen rows through the x0910 tail to 2026-09-11). "
          f"Per year: {yline(h1['post_death_rows_by_year'], 'rows')} rows over {yline(h1['post_death_rows_by_year'], 'symbols')} symbols (2022..2026). "
          f"Zero-trade runs of 24 h or longer: {h1['zero_trade_runs_ge_24h']['n_runs_ge_288']}, of which {h1['zero_trade_runs_ge_24h']['runs_never_resumed']} never resume. "
          "The eligibility rules all pass such rows: panel elig and king/DL member screens use the share of finite ret5 bars (coverage) plus 7-day volatility and a finite forward return (a frozen close gives a finite 0); "
          "the replay universe is 'finite qvk' (the 7-day mean of log1p(quote volume), which is a finite 0 on frozen rows) intersected with U-PIT, whose monthly rule keeps any name with positive 30-day volume, i.e. up to about two months after death; "
          "the replay trade set uses a 7-day log-volume mean that decays only gradually after the stop (TRD-03 counts the dead pairs it still admits); P2 uses 'a settlement in the last 24 h' as its TRADING proxy. "
          f"Funding archives keep records for dead contracts: {h5['symbols_with_events_after_death']} of the {h5['symbols_dead_inside_cache']} dead contracts have {i(h5['totals']['events'])} settlement events after their last trade "
          f"(zips {i(h5['totals']['zip'])}, fund_aug {i(h5['totals']['aug'])}, r6 September pull {h5['totals']['sep']}), e.g. RAYUSDT last trade 2022-11-15, funding until 2025-06-19. "
          "My own survivorship reading C2 (28 names with last finite bar before 2026-08-01) was fooled by the same rows; by trades the number is 156. "
          "The book-level size on A0 is small (TRD-03) and the rank-base and statistics contamination is systematic (TRD-02, TRD-04); L4 already had its verdict decided by this failure (L4b)."),
    evidence=[
        {"source": "retrain_2026-09/pod_merge_cache_ext.py:24,27-32 (git HEAD; = pod2 /workspace copy de7a0661)", "quote": "k['ts'] = pd.to_datetime(k.open_time...) + pd.Timedelta('5min') ... A[:,0] = np.clip(k.c.pct_change(fill_method=None), -0.3, 0.3) ... A[:,4] = np.log1p(k.cnt).clip(0, 20)"},
        {"source": "devices_data/receipts/AD_H_tradability.json H1_cache (ad_tradability.py 4c065c17, commit 60461e1a before run)", "quote": json.dumps(h1["post_death_signature"]) + "; top: " + ", ".join(f"{k} last trade {v['last_traded_bar_close']} ({v['days']} d frozen)" for k, v in list(h1["top_symbols_post_death_rows"].items())[:6])},
        {"source": "AD_H_tradability.json H1_x0910_tail", "quote": json.dumps({k: v for k, v in h1t.items() if k != "names"})},
        {"source": "retrain_2026-09/pod_panel_ext.py:40; v4_chain_2026-09-09/pod_fea_ext_clamp.py:37; pod_dlw_targets_raw.py:107", "quote": "elig = (covr >= 0.95) & (v7 >= 1e-4) | ok = (covr[i] >= 0.95) & (v7[i] >= 1e-4) & np.isfinite(y4[i]) | ok = (covr[i] >= 0.95) & (vstd[i] >= 1e-4) & np.isfinite(y4s[i])"},
        {"source": "uplift_2026-09-11/r18_foundation/devices/w10_sleeve_r18.py:81,244,267 (A0 config MEMBERS_TOPN=829)", "quote": "_mem2[_i] = np.sort(_ord[:MEMBERS_TOPN]) (all finite qvk) ... ok = ... np.isfinite(y4[i, m]); qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48 ... _nonsel[m[~sel]] = True"},
        {"source": "retrain_2026-09/health_check_2026-09-05/build_umask.py:46 (U-PIT, monthly refresh)", "quote": "elig = has & (age >= 30) & (vol30 > 0)"},
        {"source": "docs/PREREG_producer_parity_phase2_oos_2026-09-12.md:75 (P2 D3)", "quote": "exchangeInfo 历史不可得 ⇒ (A−24h, A] 有结算的名作 TRADING 代理"},
        {"source": "AD_H_tradability.json H5_funding_after_death", "quote": json.dumps(h5["totals"]) + "; " + ", ".join(f"{k} {v['events_after']} events after last trade {v['last_traded_bar_close'][:10]} (last {v['last_after'][:10]})" for k, v in list(h5["per_symbol"].items())[:5])},
        {"source": "uplift_r3_2026-09-13/L4b/RESULT_L4b.md:46-47 (commit 30dc6eb2)", "quote": "After a perp stops trading, the archive keeps writing untraded 1m rows with one frozen close ... fund_aug keeps recording funding for some stopped perps (MDT 1,197 events ...)"},
        {"source": "AD_C_cache_members.json C2_axis_survivorship (my earlier close-based reading)", "quote": f"last_bar_before_2026-08-01_n {c2['last_bar_before_2026-08-01_n']} vs AD_H symbols_dead_inside_cache {h1['symbols_dead_inside_cache']}"}],
    status="OPEN_MEASURED_MATERIAL", affects=["future_eval", "future_retrain", "reporting"], severity="P1",
    severity_reason="A verified, systematic defect with no guard anywhere in research: dead contracts enter universes, rank bases and statistics with zero returns and phantom funding; it already decided one research verdict (L4) and sits directly under the next ones (L3 delisting events, carry sleeves).",
    action=("Add a trades-based flag to the data layer (for each name and 5m row: traded = number_of_trades > 0 from log_cnt; untradable_since = first row after the last trade) and a causal version for decisions "
            "(no trade in the trailing 24 h). Apply it to U-PIT, the replay universe and trade set, the fund rank base, P2's base proxy, the king/DL member screens and state-variable member sets; "
            "set post-death returns to NaN, not 0, and treat funding records after the last trade as not paid. Re-run A0/NW and P2 S2 once, paired, to size the change."),
    method="VERIFIED",
    dependents=["uplift_r3 L4 carry sleeve (corrected by L4b)", "P2 S2 historical replay (running; base proxy = settlement presence)", "every w10_sleeve arm with MEMBERS_TOPN=829 / UMASK m1 (A0, NW, C0, T1 C0, T2, T5, T5c)",
                "T1 H3 / T8 state variables over finite-qvk ∩ m1", "r12 / r19 sig_fund and dispersion labels", "my own C2 survivorship reading (corrected here)"])

add(id="FEA-01", layer="DL training features / funding columns (fea82 via wide_panel_4h_v3splice)",
    title="DL training features carry funding only for the 450 names of the 2026-08 live list; for every other name the funding inputs are 0.0 back to 2022, and that flag carries forward-return information",
    what=("The DL feature builder takes fund_ema and fund_now from the splice panel (F171_PANEL = PANEL_SPLICE in the chain) and writes nan_to_num(value, 0.0). The splice panel's prefix up to 2026-08-15 is the v1 canonical panel, "
          f"whose funding covers exactly the {g1['v1_funding_symbols']} symbols of live_pins symbols_live (identical sets), while the 829-name panel the replay reads has funding for {f1['v2ext_symbols_with_any_finite_f_fund_ema']}. "
          f"So among DL member pairs that do have funding in the 829-name panel, the training feature is 0.0 on {' / '.join(pct(f2[y]['share_fund_ema_zero_while_v2ext_finite']) for y in YRS)} of pairs (2022..2026). "
          "Membership of a 2026-08 list is future information for 2022-2025 rows. The flag 'funding feature present' is informative about the next 4 h: restricted to pairs with real funding, "
          f"the demeaned forward return of flagged minus unflagged names is {' / '.join('+' + f(g2[y]['mean_gap_bps_A1_minus_A0']) if g2[y]['mean_gap_bps_A1_minus_A0'] >= 0 else f(g2[y]['mean_gap_bps_A1_minus_A0']) for y in YRS)} bps per 4 h "
          f"(naive t {' / '.join(f(g2[y]['t_gap'], 1) for y in YRS)}; autocorrelated, descriptive). The in-service F10 (dlw_ext / f8_ext, built from the same splice), the v4 F10 and every F10 OOF used in replays "
          "(f10_A0, f10_v4RAW, P2's injection) were trained on this. Production scores only live names; how its own funding inputs are filled is a production-path question (T4b found historical-anchor fund rows back-filled with 0; AUDIT_PROD), so train and serve distributions of these two columns differ in an unmeasured way. "
          "The October template keeps PANEL_SPLICE, so the zero prefix persists. The size of the effect on F10 predictions and books was not measured."),
    evidence=[
        {"source": "retrain_2026-09/pod_dlw_features_ext.py:73,94", "quote": "FUND = [PW[\"f_fund_ema\"]..., PW[\"f_fund_now\"]...] ... X[sl, col] = 0.0 if j is None else np.nan_to_num(fv[j, m], nan=0.0)"},
        {"source": "pod2 dlw_ext/results/dlw_features_report.json and dlw_v4raw/results/dlw_features_report.json (read-only)", "quote": "panel_sha256 c5d10f6ae31fa3f9... (= wide_panel_4h_v3splice.npz) in both; cache 72eb7849 (in-service, _ext) and 1d7f459d (v4, holefix2)"},
        {"source": "retrain_2026-09/v4_chain_2026-09-09/chain_v4_monthly.sh:139", "quote": "env -i ... F171_CACHE=$CACHE F171_PANEL=$PANEL_SPLICE F171_OUT=$DLW_CLIP \"$PY\" \"$BUILDER_FEA82\""},
        {"source": "retrain_2026-09/pod_panel_splice.py:11-12 (CAN = v1 canonical, EXT = v2ext)", "quote": "CAN = np.load(\"/workspace/data/wide_panel_4h_v1.npz\") ... EXT = np.load(\"/workspace/data/wide_panel_4h_v2ext.npz\")"},
        {"source": "devices_data/receipts/AD_G_batch3.json G1 (ad_batch3.py f1e9b714, commit 36633520 before run)", "quote": json.dumps(g1)},
        {"source": "AD_F_batch2.json F1 (ad_batch2.py 941ba723, commit deb8a47b)", "quote": f"v1_symbols_with_any_finite_f_fund_ema {f1['v1_symbols_with_any_finite_f_fund_ema']}; v2ext {f1['v2ext_symbols_with_any_finite_f_fund_ema']}; f_fund_ema finite in v2ext but NaN in v3splice by year: " + yline(f1['keys']['f_fund_ema']['by_year'], 'finite_v2ext_nan_v3splice')},
        {"source": "AD_F_batch2.json F2 (dlw_v4raw dlw_fea82.npz 40608701, 2,753,289 member pairs)", "quote": "; ".join(f"{y}: {i(f2[y]['fund_ema_zero_while_v2ext_finite'])} of {i(f2[y]['pairs_with_v2ext_row'])} pairs zero while v2ext finite" for y in YRS)},
        {"source": "AD_G_batch3.json G2", "quote": "; ".join(f"{y}: anchors {g2[y]['anchors_both_groups_ge20']}, gap {g2[y]['mean_gap_bps_A1_minus_A0']:+.2f} bps (t {g2[y]['t_gap']:.1f}), spearman {g2[y]['mean_spearman']:+.4f}" for y in YRS)},
        {"source": "retrain_2026-09/second_instrument_rebuild_2026-09-05/REPORT.md:59", "quote": "the 08-21 instrument (v1 = wide_panel_4h_hist_v2.npz) used 450-symbol funding coverage ... The two instrument families therefore differed in funding coverage"},
        {"source": "v4_chain_2026-09-09/v4_month_2026-10.env.template:10", "quote": "PANEL_SPLICE=/workspace/data/TODO_wide_panel_4h_v3splice_2026-10.npz"}],
    status="OPEN_NOT_MEASURED", affects=["live_trading", "future_eval", "future_retrain"], severity="P1",
    severity_reason="A future-derived availability flag sits in the training inputs of a live model leg and of every F10 out-of-fold series used to judge candidates; the October retrain would re-bake it, and no document records it as a defect.",
    action=("Rebuild fea82 funding columns from the 829-name panel (or from the settlement stream with the declared interval) and keep NaN semantics explicit (a separate availability bit built from trades, TRD-01); "
            "measure on one monthly fold pair (current vs rebuilt features, same seed and recipe) the F10 OOF IC and the A1 book difference before October; until then label F10 OOF readings as carrying this flag."),
    method="VERIFIED",
    dependents=["in-service F10 f10_live_s42_np (dlw_ext / f8_ext)", "RESULT_v4_chain_retrain_quantify_2026-09-09 (A1 vs A0, both affected)", "every replay F10 leg: f10_A0_s*, f10_v4RAW_s*", "P2 F10 OOF injection (D2)", "none re-run"])

add(id="TIM-01", layer="king features and labels / clock (train vs serve)",
    title="King training uses windows ending one bar before the anchor and labels starting one bar before it; the live producer serves windows that include the anchor bar; the October chain rebuilds the same way and no register carries it",
    what=("pod_fea_ext_clamp.py builds every window as rows [E-w, E-1] and the label as the sum over rows [E, E+47]; shadow_loop_v3.py serves rows [ai+1-w, ai] where ai is the bar closing at the anchor; the accounting return is rows [E+1, E+48]. "
          "E-0909-F measured the skew on six anchors: prediction Spearman 0.976-0.990 between the training clock and the serving clock, top-decile overlap 78-93%, largest |Δpred| 1.2-1.9 times the score's sd. "
          "The clock-aligned builder (v4e) passed its parity gate but failed the export guard by rule (Sharpe 2.260 < 2.27, a guard whose sampling error is about ±0.6); book-level readings were (C). "
          "The in-service booster and the v4 candidate both carry the skew; the October chain calls pod_fea_ext_clamp.py again. RUNBOOK_2026-10, CALIBER_STATUS and FIXPROGRAM do not list it."),
    evidence=[
        {"source": "~/wide_shadow/shadow_loop_v3.py:280,285-286,356,358 (sha256 e9c98374...)", "quote": "\"endTime\": anchor * 1000 - 1 ... close_s = (int(k[0]) + 300000) // 1000 ... if close_s > anchor ... ai = row_of[anchor] ... seg = CDf[max(ai + 1 - w, 0):ai + 1, :, ch]"},
        {"source": "v4_chain_2026-09-09/pod_fea_ext_clamp.py:33-34,48,51 (sha b9f9c728, = pod2 review_scratch copy)", "quote": "y4 = (CS[\"ret5\"][0][E + 48] - CS[\"ret5\"][0][E]) ... Ew = np.maximum(E - w, 0) ... VAL.append(((s_[E] - s_[Ew])))"},
        {"source": "devices_data/receipts/AD_C_cache_members.json C3_positive_control.king", "quote": f"member lists unequal {C['C3_positive_control']['king']['member_lists_unequal']}; y4 maxabs vs Σ rows [E, E+47] = {C['C3_positive_control']['king']['y4_maxabs_window_rows_E_to_E+47']}"},
        {"source": "docs/HANDOFF_round2_b0a573a1_closure_2026-09-09.md:40,42,68", "quote": "离线特征窗 [E−w, E−1] vs 生产 [E−w+1, E] ... Spearman 0.976–0.990, 顶十分位重叠 78–93% ... G2 导出门 = FAIL ... 守卫 Sharpe 2.260 < 2.27"},
        {"source": "v4_chain_2026-09-09/chain_v4_monthly.sh:148", "quote": "env -i ... CACHE_IN=$CACHE PANEL_IN=$PANEL_KING FEA_OUT=$KING_FEA META_OUT=$KING_META \"$PY\" \"$D/pod_fea_ext_clamp.py\""},
        {"source": "grep 'E-0909-F|v4e|king_clock|时钟' RUNBOOK_monthly_retrain_2026-10.md, CALIBER_STATUS_2026-09-09.md, git show HEAD:docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md", "quote": "no entry for the king clock; RUNBOOK mentions v4e only as the export gate file v4e_gate_export_v2.py; FIXPROGRAM's only 时钟 hit is D2 (metrics archive)"}],
    status="OPEN_MEASURED_MATERIAL", affects=["live_trading", "future_retrain", "future_eval"], severity="P1",
    severity_reason="A measured train/serve skew in a live model leg (7-22% of the top decile changes), with a ready fix blocked by a low-resolution guard, silently re-baked by the next retrain because it fell out of every register.",
    action="Add E-0909-F to FIXPROGRAM; decide the clock-aligned builder with a CI-based book judge instead of the ±0.6-noise guard band; until decided, state in RUNBOOK_2026-10 that October keeps the old clock.",
    method="VERIFIED", dependents=["in-service king booster 8d79186b", "v4 king SLOW_v4 (A1x, P2 king OOF)", "RESULT_king_clip_label_ablation / guard band 2.27-2.57 (computed on the same early-window label)", "none re-run"])

add(id="TRD-02", layer="fund leg rank base (replay FZB and P2 base proxy)",
    title="The fund leg's rank base in research includes dead contracts that still have funding records; production's base (exchangeInfo TRADING) does not",
    what=("w10 m1 scope ranks each member's funding EMA among every finite value on the panel row; dead contracts with continuing funding records sit in that base. "
          f"Dead names in the base, mean per anchor {' / '.join(f(h3[y]['base_DEAD_mean'], 1) for y in YRS)} (max {' / '.join(str(h3[y]['base_DEAD_max']) for y in YRS)}) of a base of {' / '.join(f(h3[y]['base_mean'], 0) for y in YRS)} names (2022..2026). "
          f"P2's settlement-based TRADING proxy has the same contamination: {' / '.join(f(p2b[y]['base_proxy_DEAD_mean'], 1) for y in YRS)} dead names per anchor (max {' / '.join(str(p2b[y]['base_proxy_DEAD_max']) for y in YRS)}). "
          "Relative order among live names is unchanged, but rank positions and therefore z levels and demeaned weights shift. Production's base is exchangeInfo TRADING perpetuals plus the pinned live list, so it excludes dead contracts unless they are still pinned. The book-level effect was not measured."),
    evidence=[
        {"source": "uplift_2026-09-11/r18_foundation/devices/w10_sleeve_r18.py:149", "quote": "def FZB(j, m): # ... fund z = rank position of each member among ALL finite fund-EMA values of the 829 base on panel row j"},
        {"source": "devices_data/receipts/AD_H_tradability.json H3", "quote": json.dumps({y: {k: h3[y][k] for k in ("base_mean", "base_DEAD_mean", "base_DEAD_max", "base_Z24_mean")} for y in YRS})},
        {"source": "AD_H_tradability.json H5.P2_base_proxy_on_king_axis", "quote": json.dumps({y: {k: p2b[y][k] for k in ("base_proxy_mean", "base_proxy_DEAD_mean", "base_proxy_DEAD_max")} for y in YRS})},
        {"source": "AD_H_tradability.json H6 fund_now_finite_on_DEAD (v2ext cells)", "quote": yline(h6, "fund_now_finite_on_DEAD")},
        {"source": "docs/PREREG_producer_parity_phase2_oos_2026-09-12.md:75", "quote": "D3 基名单: exchangeInfo 历史不可得 ⇒ (A−24h, A] 有结算的名作 TRADING 代理"},
        {"source": "~/wide_shadow/shadow_loop_v3.py:315-317 (e9c98374)", "quote": "_b = [x[\"symbol\"] for x in _xi[\"symbols\"] if x.get(\"contractType\") == \"PERPETUAL\" and x.get(\"quoteAsset\") == \"USDT\" and x.get(\"status\") == \"TRADING\"] ... st.base = sorted(set(_b) | set(st.live))"}],
    status="OPEN_NOT_MEASURED", affects=["future_eval"], severity="P2",
    severity_reason=f"Systematic {BASE_RNG} contamination of the rank base (yearly mean) behind the book's dominant leg in every replay and in P2's production-path claim; effect on levels not measured but paired contrasts mostly cancel.",
    action="Drop from the base any name with no trade in the trailing 24 h (TRD-01 flag) in w10 FZB and in P2's base proxy; report the paired A0 and P2 differences.",
    method="VERIFIED", dependents=["A0/NW/C0 and all m1-scope arms", "P2 S2 (running)", "none re-run"])

add(id="TRD-03", layer="replay book (A0) / positions in dead contracts",
    title="A0 holds dead contracts in the days right after their last trade, books a 0 return on them and charges carry from records that were not paid; the size is small",
    what=("On the A0 axis the replay universe contains dead member-anchors "
          f"{yline(h2, 'U_DEAD')} per year (2022..2026, {yline({y: {'s': h2[y]['U_DEAD'] / h2[y]['U_pairs']} for y in YRS}, 's', lambda x: pct(x, 2))} of universe pairs); "
          f"the trade set keeps {yline(h2, 'U_DEAD_sel')} of them and all of those are held (|W| sum {yline(h2, 'absW_DEAD', lambda x: f(x, 3))}, share of annual |W| {yline(h2, 'absW_DEAD_share', lambda x: f'{x:.1e}')}). "
          f"Every held dead cell has accounting return exactly 0; the carry booked on them is {yline(h2, 'carry_bps_booked_on_DEAD', lambda x: f'{x:+.2f}')} bps summed over each year (s42; s2027 {yline(h2b, 'carry_bps_booked_on_DEAD', lambda x: f'{x:+.2f}')}). "
          "The exit loss of a dead contract is not in the data. At this size the replay's level and Sharpe do not change within resolution; the separate forward-return exit (FWD-02) is smaller still."),
    evidence=[
        {"source": "devices_data/receipts/AD_H_tradability.json H2_A0_population (A0_PWR230k_s42 352ac36f, s2027 aa44e18f)", "quote": json.dumps({y: {k: h2[y][k] for k in ("U_pairs", "U_DEAD", "U_DEAD_sel", "held_DEAD", "absW_DEAD", "absW_DEAD_share", "held_DEAD_y4_exactly0", "carry_bps_booked_on_DEAD")} for y in YRS})},
        {"source": "AD_H_tradability.json H2 positive-control field held_outside_U (smoothing carry-over outside the universe)", "quote": yline(h2, "held_outside_U")}],
    status="VERIFIED_IMMATERIAL", affects=["future_eval"], severity="P3",
    severity_reason="Held dead exposure is at most 4.9e-4 of annual gross and the booked carry about 0.002 bps per anchor; far below the 0.23 bps resolution.",
    action="None for A0; include the trades flag (TRD-01) before any sleeve that holds illiquid or deeply negative-funding names is judged.", method="VERIFIED", dependents=["A0 / NW (immaterial)"])

add(id="TRD-04", layer="state variables and member-set statistics",
    title="Cross-sectional statistics over 'finite qvk ∩ CRYPTO mask' include dead contracts with zero returns and phantom funding",
    what=("T1 (AMENDMENT 2) and the w10 state instruments define the member set as finite qvk ∩ m1 mask, which is exactly the universe that contains the dead member-anchors counted in TRD-03 "
          f"({yline({y: {'s': h2[y]['U_DEAD'] / h2[y]['U_pairs']} for y in YRS}, 's', lambda x: pct(x, 2))} of pairs per year) and, for funding statistics, the base contamination of TRD-02. "
          "Breadth (share of positive returns), return dispersion and funding dispersion (sig_fund) are therefore computed with zero-return rows and stale default funding rates; the direction is toward lower breadth and lower dispersion. Size on T1/T8/r12/r19 readings not measured."),
    evidence=[
        {"source": "uplift_r2_2026-09-13/T1/PREREG_AMENDMENT_2_T1_2026-09-13.md:9", "quote": "成员集改为 m_k = { n : qvk[k, n] 有限 } ∩ CRYPTO m1 掩码行(= 装置 MEMBERS_TOPN=829 语义"},
        {"source": "devices_data/receipts/AD_H_tradability.json H2 U_pairs / U_DEAD / U_Z24", "quote": json.dumps({y: {k: h2[y][k] for k in ("U_pairs", "U_DEAD", "U_Z24")} for y in YRS})},
        {"source": "uplift_2026-09-11/r19_trackF_reindex/RESULT_r19_trackF_reindex_2026-09-12.md:14", "quote": "更正后 sig_fund 对 ... R6M 臂(meta 成员 ∩ m1, x0910 轴)共同 10039 锚 maxabs 3.78e-6"}],
    status="OPEN_NOT_MEASURED", affects=["future_eval", "reporting"], severity="P2",
    severity_reason=f"{U_RNG} of member pairs per year are dead; state-conditioned readings (all nulls so far) are unlikely to flip but the bias is one-directional and undocumented.",
    action="Recompute the T1/T8 state columns and r19 sig_fund with the trades flag once; if nothing moves beyond resolution, record VERIFIED_IMMATERIAL.", method="VERIFIED",
    dependents=["T1 H3 states", "T8 24 state columns", "r12 REGIME12 / causal primitives", "r19 sig_fund / disp24 labels", "none re-run"])

add(id="TRD-05", layer="training rows (king meta, DL targets)",
    title="King and DL training members include dead contracts with labels exactly 0 in the first days after death",
    what=(f"King meta members that are dead: {yline(h4k, 'DEAD')} pairs per year (2022..2026), all with accounting y4 exactly 0; DL members {yline(h4d, 'DEAD')}, all y4s exactly 0 "
          f"(largest share {max(h4k[y]['DEAD'] / h4k[y]['king_member_pairs'] for y in YRS):.2%}). The 7-day volatility screen removes them after about a week; before that they are training rows with a zero label."),
    evidence=[{"source": "devices_data/receipts/AD_H_tradability.json H4_training_rows", "quote": json.dumps({"king_meta": {y: h4k[y] for y in YRS}, "dl_targets": {y: h4d[y] for y in YRS}})}],
    status="VERIFIED_IMMATERIAL", affects=["future_retrain"], severity="P3", severity_reason="At most 0.21% of member pairs; rank labels place them mid-distribution.",
    action="Exclude with the trades flag when the member screens are next edited; not worth a retrain by itself.", method="VERIFIED", dependents=["king v3/v4 boosters, F10 v3/v4 (immaterial)"])

add(id="FND-01", layer="4h panel / x0910 funding tail",
    title="x0910 panels apply one pull-time settlement interval to every September API row of a symbol (builder located and reproduced)",
    what=("r6_fetch_funding.py read fundingIntervalHours from /fapi/v1/fundingInfo once at 2026-09-11 and stored it as intervals; r6_panel_splice.py appends every September row with that value and prefers it to the settlement spacing. "
          f"Re-deriving the r6 rule reproduces the panel tail exactly (iv cells not reproduced {tc['PC2_builder_rule_reproduces_panel_tail']['tail_iv_cells_not_reproduced']}, EMA maxabs {tc['PC2_builder_rule_reproduces_panel_tail']['tail_ema_v1_maxabs_replica_vs_panel']}). "
          f"Against settlement truth the tail has {bx['iv_mismatch_cells']['tail']} wrong interval cells over {bx['symbols_with_mismatch']} symbols (IOST 1h for true 8h; SKR, T, SOPH, ZKC, COTI 4h for true 1h; six tokenized stock perps 4h for 8h). "
          f"Corrected f_fund_ema_v1 differs by up to {tc['ema_v1_maxabs_corrected_vs_panel']:.4f} (IOST), {tc['ema_v1_cells_absdiff_gt_1e-6']} cells above 1e-6, per-anchor Spearman ≥ {tc['per_anchor_spearman_min']:.4f}, "
          f"{tc['ftrim_class_flips_total']} FTRIM class flips on {tc['ftrim_class_flips_anchors_with_any']} anchors. The incumbent prefix is correct (0 mismatches). "
          "Caveat: settlement spacing itself mislabels the first long-interval settlement after a short-to-long switch (FIXPROGRAM P9); four of the counted cells fall exactly on the switch rows P9 lists (COTI 08-31 20Z, ZKC 09-02 20Z, T 09-06 00Z, SKR 09-07 20Z), where the pull-time value is probably the declared one and spacing is wrong, so the true count is 543-547. "
          "T5d re-ran T5c with corrected intervals (not yet re-run by the lead); T1 D2 September carry and the other September readings were not re-run. Recurrence in October is AUDIT_TRAIN TRN-07."),
    evidence=[
        {"source": "pod2 /workspace/uplift_2026-09-11/r6/r6_fetch_funding.py:33-34,69 (sha 298927ad, not in git)", "quote": "INFO = {d[\"symbol\"]: float(d[\"fundingIntervalHours\"]) for d in get(\".../fapi/v1/fundingInfo\") ...} ... \"intervals\": {k: v for k, v in INFO.items() if k in rates}"},
        {"source": "pod2 /workspace/uplift_2026-09-11/r6/r6_panel_splice.py:82,90 (sha cccc5b6b, not in git)", "quote": "rows.append((int(t_ms)//1000, float(rate), SEP_IV.get(s, np.nan))) ... iv_full = np.where(np.isfinite(fiv), fiv, dv)"},
        {"source": "devices_data/receipts/AD_B_funding_iv.json panels.v2ext_x0910 (ad_funding_iv.py f6d58b2b, commit feb7747e before run)", "quote": json.dumps({"iv_mismatch_cells": bx["iv_mismatch_cells"], "symbols": bx["symbols_with_mismatch"], "PC2": tc["PC2_builder_rule_reproduces_panel_tail"], "flips": tc["ftrim_class_flips_total"]})},
        {"source": "AD_B_funding_iv.json top_symbols", "quote": "; ".join(f"{k} panel {v['panel_iv_values']} true {v['true_iv_values']} last {v['last']}" for k, v in list(bx["top_symbols"].items())[:12])},
        {"source": "docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md:46 (P9)", "quote": "短→长间隔切换时, 新制度首次结算按长间隔申报而时间差是短, 被标成短 ... COTI 08-31 20Z / ZKC 09-02 20Z / T 09-06 00Z / SKR 09-07 20Z"},
        {"source": "git e73f50e6 (T5d)", "quote": "研究 T5d 入库(结算间隔真值修正后重生成仓位复算 T5c; 未经 lead 复跑) ... 部署 king 链九月 carry 被低估 +0.253"}],
    status="OPEN_MEASURED_MATERIAL", affects=["future_eval", "reporting"], severity="P2",
    severity_reason="Confined to 60 September anchors and 23 names, already flagged PROVISIONAL and partly re-run; it can still move September carry and FTRIM readings by up to 2.4 bps per anchor for single names.",
    action="Rebuild the x0910 funding tail with the declared interval where available and spacing otherwise (P9-aware), then re-run T1 D2 and any September carry reading; retire the r6 splice for future extensions (TRN-07).",
    method="VERIFIED", dependents=["T1 D2 September carry (PROVISIONAL, not re-run)", "T5c (re-run as T5d e73f50e6, lead re-run pending)", "T2 live addendum d4", "r6 JUDGE-1/2 September anchors", "r9 x0910 replays", "r12/r19 September sig_fund"])

add(id="FND-02", layer="funding source (fund_aug) / interval rule for API rows",
    title="API funding rows get their interval from settlement spacing; the canonical panels match that rule exactly, but spacing mislabels switch rows and nobody has measured them in the research panels",
    what=(f"fund_aug.json.gz was written with an empty intervals map, so pod_panel_ext.py, pod_panel_splice.py and the bundle exporter derive API-row intervals from spacing; zip rows use the archive's own column. "
          f"On the canonical v2ext panel the interval matches (zip column, else spacing) on all {i(b2['compared_cells']['prefix'])} compared cells. "
          f"Spacing agrees with the archive column on {i(B['PC1_zip_column_vs_spacing']['both_defined'] - B['PC1_zip_column_vs_spacing']['col_ne_spacing'])} of {i(B['PC1_zip_column_vs_spacing']['both_defined'])} zip rows; the {B['PC1_zip_column_vs_spacing']['col_ne_spacing']} disagreements are consistent with the switch rows FIXPROGRAM P9 describes (not classified row by row). "
          "The same mislabel therefore exists, unmeasured, wherever panel rows came from the API instead of a zip: 2026-08 rows of v2ext/v3splice (the August zip was not published at build time) and all x0910 September rows. "
          "The precedence rule (explicit interval over spacing) is a latent trap for any fund pull that fills intervals (TRN-07)."),
    evidence=[
        {"source": "retrain_2026-09/fund_pull_pod.py:28 (= pod2 copy fa665810)", "quote": "out = {\"rates\": rates, \"intervals\": {}}"},
        {"source": "retrain_2026-09/pod_panel_ext.py:66,105,120", "quote": "AUG_IV = {k: float(v) for k, v in (AUG.get(\"intervals\") or {}).items() if v} ... AUG_IV.get(s, np.nan) ... iv_full = np.where(np.isfinite(fiv), fiv, dv)"},
        {"source": "devices_data/receipts/AD_A_inventory.json fund_aug.json.gz (8a9e7715)", "quote": json.dumps(FA["fund_aug.json.gz"]["funding_pull"])},
        {"source": "devices_data/receipts/AD_B_funding_iv.json PC1 and panels.v2ext", "quote": json.dumps({"PC1": {k: B["PC1_zip_column_vs_spacing"][k] for k in ("zip_rows_with_col", "both_defined", "col_ne_spacing", "rate_conflicts_between_sources")}, "v2ext": {"compared": b2["compared_cells"], "mismatch": b2["iv_mismatch_cells"]}})},
        {"source": "pod2 /workspace/wide_multisrc/funding (AD_A dirs)", "quote": json.dumps(A["dirs"][0]["latest_zip_month_histogram"]) + " (latest zip month per symbol; 2026-08 zips are .404 placeholders)"}],
    status="OPEN_NOT_MEASURED", affects=["future_eval", "future_retrain"], severity="P2",
    severity_reason="Switch rows scale one settlement by 2-4x in the normalised EMA and can flip FTRIM for one anchor; rare (646 rows in the whole zip history) but concentrated in the live window where intervals changed.",
    action="Download the now-published 2026-08 (and later 2026-09) fundingRate zips read-only and rebuild the August/September intervals from the declared column; make every builder use declared > spacing and never a pull-time map.", method="VERIFIED",
    dependents=["v2ext/v3splice August 2026 funding cells", "x0910 September funding cells", "bundle funding_ledger_seed / EMA state for October"])

add(id="HOL-01", layer="4h panels / hole residuals",
    title="The panels every replay and the v4 chain read were built on the pre-holefix cache and still carry the filled holes in their kline columns",
    what=(f"Same builder, same code, pre-fix cache versus hole-fixed cache: {i(d2['kline_diff_cells_near_hole_total'])} kline cells differ on {d2['anchors_near_hole']} anchors near the four fill runs and 0 cells elsewhere (the positive control). "
          f"Examples: elig {i(dk['elig']['diff_cells_near_hole'])} cells, Y4 {i(dk['Y4']['diff_cells_near_hole'])}, f_mom_30d {i(dk['f_mom_30d']['diff_cells_near_hole'])}, f_amihud_24h up to {dk['f_amihud_24h']['max_abs_value_diff']:.1f}; funding keys identical. "
          "v3splice carries the same cells (its v1 prefix has the 2022 holes too) and the x0910 panels copy both prefixes verbatim. Consumers: rev24 z in the F10 legs (old rows verbatim), the pinned 2022 warm-up seat of A0, amihud/XIB candidates, and state variables on anchors within 30 days after a fill run (2022-02-25..2022-05-03 and 2026-08-11 to the panel end). "
          "October: a fresh PANEL_KING build on the rolled cache would be clean, but PANEL_SPLICE rolls the prefix and LEGS_OLD rows are copied verbatim, so the residual persists there. Book-level effect not measured."),
    evidence=[
        {"source": "devices_data/receipts/AD_D_panel_holes.json comparisons.v2ext (ad_panel_holes.py a62a9d48, commit feb7747e before run)", "quote": json.dumps({k: d2[k] for k in ("common_anchors", "anchors_near_hole", "kline_diff_cells_near_hole_total", "kline_diff_cells_away_from_hole_total", "positive_control_kline_equal_away_from_holes")})},
        {"source": "AD_D_panel_holes.json holes.fill_runs_utc (holefix2_cells.npz 6156f97a)", "quote": json.dumps(D["holes"]["fill_runs_utc"])},
        {"source": "AD_A_inventory.json", "quote": f"wide_panel_4h_v2ext.npz {S('data/wide_panel_4h_v2ext.npz')} mtime {FA['data/wide_panel_4h_v2ext.npz']['mtime_utc']} (holefix2 cache mtime {FA['data/dlnative_5m_wide829_f16_holefix2.npz']['mtime_utc']}); reference rawbuild_x0910 {S('uplift_2026-09-11/r6/out/wide_panel_4h_rawbuild_x0910.npz')}"},
        {"source": "uplift_2026-09-11/RESULT_r6_coverage_extension_2026-09-11.md:249,254", "quote": "incumbent 面板里最大 302.9 ... 回放装置消费的面板就是 wide_panel_4h_v2ext.npz"}],
    status="OPEN_NOT_MEASURED", affects=["future_eval", "future_retrain"], severity="P2",
    severity_reason="Confined to about 5% of anchors, but those include the 2026-08 live window that current diagnostics study and the legs every F10 retrain copies forward.",
    action="Rebuild v2ext-type and splice panels (and the legs Z24/ZFD old rows) on holefix2; re-run the diagnostics that use panel kline columns near 2026-08.", method="VERIFIED",
    dependents=["XIB/amihud candidates (r5, r6 X3)", "T1/T8 states near 2026-08", "F10 legs Z24", "A0 warm-up 2022 rev24", "none re-run"])

add(id="UNI-01", layer="universe / training member sets",
    title="Tokenized stock and commodity perps are 7.3% of 2026 training member pairs; evaluation masks them, training does not",
    what=(f"Using the venue class snapshot, non-crypto names are {c6['king_meta_members']['2026']['noncrypto_pairs']:,} of {c6['king_meta_members']['2026']['pairs']:,} king-meta member pairs in 2026 "
          f"({pct(c6['king_meta_members']['2026']['noncrypto_share'], 2)}, present at all {c6['king_meta_members']['2026']['anchors_with_noncrypto']} anchors), and identical in the DL targets; 2025 has {c6['king_meta_members']['2025']['noncrypto_pairs']} pairs. "
          "The replay and judge use the CRYPTO mask, but the F10 2026 folds, the F10 refit and the king fold-2026 gates (ic26, guard) include these names, and October adds September rows. Effect on models not measured."),
    evidence=[{"source": "devices_data/receipts/AD_C_cache_members.json C6 (venue_class_20260908.json fa9196a3)", "quote": json.dumps({"king": c6["king_meta_members"], "noncrypto_symbols_on_axis": c6["noncrypto_symbols_on_axis"]})},
              {"source": "docs/PREREG_producer_parity_phase2_oos_2026-09-12.md D10", "quote": "缺口 = 研究侧 top-400 取自全 829 名含股票永续, 生产-PIT 取自 PIT 名"}],
    status="OPEN_NOT_MEASURED", affects=["future_retrain", "live_trading"], severity="P2",
    severity_reason="A growing share of the newest training rows are names production never scores; it shifts the rank labels and the monthly folds that decide the swap.",
    action="Apply the CRYPTO class filter to the king/DL member screens (or report the fold gates on both member sets) before the October folds.", method="VERIFIED",
    dependents=["F10 monthly folds 202601-202608 and refit", "king ic26 gate", "P2 D10 coverage gap"])

add(id="OOF-01", layer="OOF predictions / reference book coverage",
    title="Replay model legs exist only from 2023 (F10) and 2024 (king), and A0's legs are on v3-lineage member lists; full-history numbers are not the in-service book",
    what=(f"King OOF SLOW_v4 starts {c5['SLOW_v4']['first_pred_anchor']} ({c5['SLOW_v4']['anchors_with_any_pred']} anchors), F10 OOF starts {c5['f10_v4RAW_s42']['first_pred_anchor']}; "
          f"A0's legs (SLOW_v3_on_v4axis, f10_A0) sit on member lists that differ from the v4 meta in {c5['SLOW_v3_on_v4axis']['pred_cells_outside_members']:,} cells. "
          "So 2022 rows run without the F10 leg and 2022-2023 rows without the king leg, and A0 is built from the v3 lineage; the uplift error ledger (★1/★3) records that the cross-regime Sharpe used as a planning number is measured on a book that is not the in-service form for 36% of the sample."),
    evidence=[{"source": "devices_data/receipts/AD_C_cache_members.json C5_oof_masks", "quote": json.dumps({k: {kk: v[kk] for kk in v if kk != 'axis'} for k, v in c5.items()})},
              {"source": "uplift_2026-09-11/handoff_audit/errors/ERROR_LEDGER_uplift_2026-09-12.md:18,132,161", "quote": "归档基线 A0 的 2022 与 2023 两行, 是缺腿的书 ... ★1 归档基线 A0 本身建在被 PIN 明令禁止的 v3 谱系上 ... ★3 1110 锚 F10 死前缀 + 3300 锚 king 死前缀"}],
    status="OPEN_MEASURED_MATERIAL", affects=["future_eval", "reporting"], severity="P2",
    severity_reason="Any full-history or 2022-2023 level quoted for the in-service form measures a different book; reference choice (A0 vs A1x) is still open.",
    action="Quote the in-service form only on windows where both legs exist; decide the reference (A1x v4-native vs A0) and restate the yearly table with SE.", method="VERIFIED",
    dependents=["CALIBER_PIN_v4 yearly table", "CLOSEOUT uplift", "~300 paired verdicts against A0"])

add(id="LIN-01", layer="lineage hygiene / x0910 builders",
    title="The x0910 extension builders exist only on pod2, while committed devices consume their products",
    what=(f"None of the {sum(1 for r in A['files'] if '/uplift_2026-09-11/r6/' in r['path'] and r['path'].endswith(('.py', '.sh')))} r6 builders and chain scripts (merge cache, panel splice, funding fetch, raw patch extension, king prediction, legs, dev tree, gates) is in git; the RESULT cites them by name only. "
          f"Committed devices since 09-09 that read x0910 products: accounting meta {mx['acct_meta_v4_x0910']['n_devices']}, panel {mx['panel_v2ext_x0910']['n_devices']}, cache {mx['cache_holefix2_x0910']['n_devices']}, DL {mx['dl_x0910']['n_devices']}, king OOF {mx['oof_king_x0910']['n_devices']} (overlapping). "
          "One of the unarchived builders carries FND-01."),
    evidence=[{"source": "devices_data/receipts/AD_A_inventory.json (pod2 r6 scripts)", "quote": "; ".join(f"{r['path'].split('/')[-1]} {r['sha256'][:16]}" for r in A["files"] if "/uplift_2026-09-11/r6/" in r["path"] and r["path"].endswith((".py", ".sh")))},
              {"source": "git ls-files | grep r6_", "quote": "receipts and RESULT only; no r6_*.py or r6_*.sh"},
              {"source": "devices_data/receipts/AD_E_consumers_matrix.json (ad_consumers_scan.py e6d9a686, HEAD deb8a47b)", "quote": json.dumps({k: mx[k]["by_research_line"] for k in ("acct_meta_v4_x0910", "panel_v2ext_x0910")})}],
    status="OPEN_MEASURED_MATERIAL", affects=["reporting", "future_eval"], severity="P2",
    severity_reason="Conclusions outlive their devices (project rule 5); a pod loss would make every September reading irreproducible, and the defective splice would be re-used from memory.",
    action="Copy the r6 builders with their shas into the research repo next to r6_MANIFEST; mark r6_panel_splice.py as defective (FND-01).", method="VERIFIED", dependents=["all x0910 consumers"])

add(id="DOC-01", layer="docs and memory",
    title="Caliber documents and memory notes miss or misstate several data-lineage facts",
    what=("CALIBER_STATUS_2026-09-09 still lists E-0908-C as 'full-history size not measured' (measured here, FWD-01) and has no rows for the king clock (TIM-01), DL funding coverage (FEA-01), dead contracts (TRD-01), hole residuals in panels (HOL-01) or non-crypto training members (UNI-01). "
          "RUNBOOK_2026-10 says the raw patch 'travels with the cache' with no extension step. The P2 prereg says F10 OOF availability is 'not checked' (C5 shows it has the same mask). "
          "crypto_mask_note.json says underlyingType=='COIN' while the builder keeps {COIN, INDEX}. The clip-compound memory note calls E-0908-C 'mild survivorship' without numbers."),
    evidence=[{"source": "docs/CALIBER_STATUS_2026-09-09.md:15", "quote": "E-0908-C | 成员集含未来标签谓词 | 研究员 C 臂: 单窗每锚 +0.0025/+0.0009 | 我方回放同样继承; 全史量级未测"},
              {"source": "docs/RUNBOOK_monthly_retrain_2026-10.md:15,193", "quote": "原始收益补丁 raw_patch.npz 随缓存走 ... 原始收益补丁 raw_patch.npz(952 bar)随缓存走"},
              {"source": "docs/PREREG_producer_parity_phase2_oos_2026-09-12.md:329", "quote": "S2 不修正, 列为继承偏差; F10 OOF 的可得性掩码未核"},
              {"source": "universe_crypto_2026-09-08/scripts/build_crypto_mask.py:11,44", "quote": "(CLS[s][\"underlyingType\"] in (\"COIN\",\"INDEX\")) ... \"definition\":\"UPIT & underlyingType=='COIN' (unknown -> kept)\""}],
    status="DOC_STALE", affects=["reporting", "future_retrain"], severity="P2",
    severity_reason="The October runbook and the caliber ledger are what an operator will read; three P1 facts are absent from both.",
    action="Add rows for TIM-01, FEA-01, TRD-01, HOL-01, UNI-01 to CALIBER_STATUS; add the patch-extension and trades-flag steps to RUNBOOK_2026-10; update the P2 prereg D20 note and the mask note string.", method="VERIFIED", dependents=[])

add(id="RET-01", layer="accounting returns / clip patch (data-side TRN-02 check)",
    title="Every clipped bar in the research caches through 2026-09-11 00:00Z has a patch entry; no research cache or panel exists after that",
    what=(f"Canonical cache: {c1['bound_cells']} cells sit exactly on the float16 ±0.30 bound, {c1['cells_beyond_bound']} beyond it; {c1['bound_cells_in_patch']} are in raw_patch.npz and the remaining one "
          f"({c1['not_in_patch_list'][0]['symbol']} {c1['not_in_patch_list'][0]['ts']}) is a true return inside ±0.30 that float16 rounds onto the bound (make_raw_patch 'not clipped'), so no clipped bar is unpatched. "
          f"x0910 tail: {c1x['tail_bound_cells']} bound cells ({', '.join(x['symbol'] + ' ' + x['ts'] for x in c1x['tail_bound_list'])}), all in raw_patch_x0910; its first 952 rows equal raw_patch.npz. "
          f"Clipped bars per month in 2026: {', '.join(k[5:] + ' ' + str(v) for k, v in f4['raw_patch_x0910']['by_month'].items() if k.startswith('2026'))}. "
          "No research cache, panel or meta has rows after 2026-09-11 00:00Z, so September 11-30 is not present and must be checked when the month is rolled (the gate itself is AUDIT_TRAIN TRN-02, P1)."),
    evidence=[{"source": "devices_data/receipts/AD_C_cache_members.json C1_clip_bound_vs_patch (ad_cache_members.py 0e8bc8fd, commit feb7747e before run)", "quote": json.dumps({k: c1[k] for k in ("bound_value", "bound_cells", "cells_beyond_bound", "patch_rows", "bound_cells_in_patch", "bound_cells_NOT_in_patch", "not_in_patch_list", "bound_cells_by_year")})},
              {"source": "AD_C_cache_members.json C1.x0910", "quote": json.dumps({k: c1x[k] for k in ("tail_first", "tail_last", "tail_bound_cells", "tail_bound_cells_in_patch", "patch_x0910_prefix_equals_incumbent_patch")})},
              {"source": "retrain_2026-09/caliber_program_2026-09-09/make_raw_patch.py:30", "quote": "if abs(rv) <= 0.3: notclip += 1; continue"},
              {"source": "AD_A_inventory.json", "quote": f"holefix2_x0910 cache last row {FA['data/dlnative_5m_wide829_f16_holefix2_x0910.npz']['ts_axis']['last_utc']}; meta_newprod_v4_x0910 last anchor {FA['uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz']['E_ts_axis']['last_utc']}"}],
    status="FIXED_DEPLOYED", affects=["future_eval"], severity="P3",
    severity_reason="The evaluation data in use are correct; the open risk is the October roll, registered as TRN-02.", action="None for current data; implement TRN-02's coverage assertion in the roll.", method="VERIFIED",
    dependents=["meta_newprod_v4 / x0910 accounting y4", "dlw_v4raw RAW targets"])

add(id="RET-02", layer="devices / returns recomputed from the clipped cache channel",
    title="Several devices written after the 09-12 rule still compound or sum returns from the clipped ret5 channel",
    what=("r14 (estimand drift), r21 (cost bridge), r12_mon (y4 monitors), event_state build_sett_v4 (settlement-window drift), s12 (target direction), smooth_latency_core (latency P&L), materiality_probe_v2 (rolling.npz, acknowledged) and r13/beta estimation read ret5 for returns. "
          "Only windows containing a bound bar are wrong; 2026 had 68 such bars before September and the live window 3. Per-device exposure was not measured; T3 uses the channel only to back-project up to 5 bars and is guarded."),
    evidence=[{"source": "uplift_2026-09-11/r14_estimand/devices/r14_gap.py:68,93", "quote": "RET = np.asarray(CD[:, :, 0], np.float64) ... CL = np.concatenate([...np.cumsum(np.where(fin, np.log1p(np.clip(RET, -0.99, None)), 0.0), 0)])"},
              {"source": "uplift_2026-09-11/r12_intervene/devices/r12_mon.py:36,51", "quote": "y4 = prod(1+ret5[E+1 .. E+48]) - 1 ... cp=np.cumprod(1.0+blk,0)-1.0"},
              {"source": "uplift_2026-09-11/event_state/devices/build_sett_v4.py:48", "quote": "dr=float(np.prod(1.0+w[ok])-1.0) if ok.any() else np.nan"},
              {"source": "memory cache_ret5_channel_clipped_at_0p30_2026_09_12", "quote": "never rebuild 4h/24h returns, price-available flags, or regime primitives from the cache ret5 on extreme bars"}],
    status="OPEN_NOT_MEASURED", affects=["future_eval"], severity="P3", severity_reason="Diagnostics over short windows; wrong only where a bound bar falls inside the window.",
    action="Swap to raw_patch-corrected returns or assert no bound bar in the window, per device, when each is next reused.", method="VERIFIED", dependents=["r12 monitors", "r14", "r21", "event_state", "r10 s12"])

add(id="LBL-01", layer="king labels",
    title="King labels are ranks of the clipped 5m sum over rows [E, E+47]; the export guard books P&L on the same label",
    what=("The king meta y4 is Σ clipped ret5 over rows [E, E+47] (reproduced exactly, maxabs 0.0), i.e. from the close before the anchor to five minutes before the accounting window ends; the exporter ranks it for training and uses it for the guard band P&L. "
          "Both parts were measured at book level: the clip part on an upper-bound arm (four cells undecided) and the window part (-0.051 [-0.115, +0.016] bps per anchor per gross, 2024-26). October keeps both."),
    evidence=[{"source": "v4_chain_2026-09-09/pod_export_bundle_v4.py:42,55-59,166", "quote": "y4 = MT[\"y4\"] ... rr = rankdata(yv[ok]) ... rows_y.append(rr) ... yv = np.nan_to_num(y4[i, m], nan=0.0)"},
              {"source": "docs/RESULT_king_clip_label_ablation_2026-09-08.md:52", "quote": "裁剪不构成 king 的重训理由(上界臂实测, 四格 UNDECIDED)"},
              {"source": "docs/RESULT_f10_caliber_sensitivity_2026-09-05.md:28", "quote": "king 窗口项 2024→26 -0.051 [-0.115,+0.016](小, CI 含 0)"}],
    status="VERIFIED_IMMATERIAL", affects=["future_retrain"], severity="P3", severity_reason="Both parts measured inside resolution; the window part is fixed together with TIM-01.",
    action="Fold into the TIM-01 decision (the clock-aligned builder also moves the label to [E+1, E+48]).", method="VERIFIED", dependents=["king boosters", "export guard band"])

add(id="FWD-01", layer="member screens / OOF availability (D20, E-0908-C)",
    title="The forward-return member predicate removes almost nothing, because dead contracts keep finite frozen returns; king and F10 OOF carry the same mask",
    what=(f"Rebuilding both member rules exactly (positive control: axes and every member list equal) and dropping only the forward predicate: king rule removes {yline(c3k, 'pairs_removed_forward_nonfinite')} pairs per year (2022..2026), DL rule {yline(c3d, 'pairs_removed_forward_nonfinite')}; "
          f"no anchor exists only without it; 24 of the 33 2022 removals never trade again. King OOF (SLOW_v4) and F10 OOF (f10_v4RAW) are written exactly on those member lists (0 predictions outside, 0 members without prediction, 0 predictions on non-finite forward returns). "
          "The predicate cannot see most deaths because the archive's frozen rows keep the forward return finite at 0 (TRD-01); the real survivorship channel is inclusion, not exclusion. AUDIT_TRAIN TRN-06's 'wider than recorded' reading should be read with these counts."),
    evidence=[{"source": "devices_data/receipts/AD_C_cache_members.json C3_positive_control", "quote": json.dumps(C["C3_positive_control"])},
              {"source": "AD_C_cache_members.json C3_forward_predicate.king_meta_rule", "quote": json.dumps(c3k)},
              {"source": "AD_C_cache_members.json C5_oof_masks (SLOW_v4, f10_v4RAW_s42)", "quote": json.dumps({k: c5[k] for k in ("SLOW_v4", "f10_v4RAW_s42")})}],
    status="VERIFIED_IMMATERIAL", affects=["future_eval", "future_retrain"], severity="P3", severity_reason="At most 1.1e-4 of member pairs per year.",
    action="None beyond TRD-01; replace the predicate by the causal trades flag when the screens are edited.", method="VERIFIED", dependents=["P2 D20", "FIXPROGRAM D3", "AUDIT_TRAIN TRN-06"])

add(id="FWD-02", layer="replay accounting / non-finite forward returns",
    title="The replay exits positions whose next accounting return is non-finite and books 0 for them; 13 pairs in the whole A0 history",
    what=(f"A0 positions dumped because the next 4 h accounting return is non-finite: {yline(c4, 'dumped_pairs')} pairs per year (2022..2026), |W| {yline(c4, 'dumped_abs_weight_prev', lambda x: f(x, 4))}, "
          "9 of 13 in contracts that never trade again (KEEP, NU, 1000BTTC, YFII, ANC, LUNA, DODO, AKRO, EOS). The exit P&L at those delistings is not in the data (L4b measured such exits for the carry sleeve)."),
    evidence=[{"source": "devices_data/receipts/AD_C_cache_members.json C4_A0_forward_nonfinite_exits.42", "quote": json.dumps(C["C4_A0_forward_nonfinite_exits"]["42"]["by_year"])}],
    status="VERIFIED_IMMATERIAL", affects=["future_eval"], severity="P3", severity_reason="Largest yearly share 2.5e-5 of gross.", action="None.", method="VERIFIED", dependents=["r18 N2 (consistent: 15 cells)"])

add(id="FND-03", layer="v1 canonical panel / API tail intervals",
    title="The v1 canonical panel's August 2026 API tail stored one interval per symbol; 138 cells for five names, the same rows as the 08-16 bundle seed",
    what=(f"On the splice prefix (v1 canonical) {b3['iv_mismatch_cells']['prefix']} cells differ from settlement truth, all in 2026-08-01..08-14 for DEXE, ERA, BANK, PROM and ACE (stored 4 h, true 1-2 h); nothing earlier differs. "
          "These are the D17 rows P2 traced to the 08-16 bundle seed; their residual in live EMA is decaying and was measured small. Builder on jpline (unverifiable)."),
    evidence=[{"source": "devices_data/receipts/AD_B_funding_iv.json panels.v3splice", "quote": json.dumps({"mismatch": b3["iv_mismatch_cells"], "by_month": b3["mismatch_by_month"], "symbols": list(b3["top_symbols"].keys())})},
              {"source": "retrain_2026-09/second_instrument_rebuild_2026-09-05/REPORT.md:55", "quote": "rebuilt interval 1 h / 2 h (per-settlement column of the 2026-08 monthly zip) vs v1 4 h (the 08-21 API tail's single per-symbol interval)"}],
    status="VERIFIED_IMMATERIAL", affects=["future_retrain"], severity="P3", severity_reason="138 cells in two weeks for five names; live residual measured by P2 D17 and FIXPROGRAM P6'.",
    action="Covered by FIXPROGRAM P6'; rebuild the splice prefix funding from zips when HOL-01/FEA-01 are rebuilt.", method="VERIFIED", dependents=["legs ZFD for five names in 2026-08", "fund_state_canoncont seeds"])

add(id="UNI-02", layer="universe / symbol axis",
    title="The 829-name axis is an S3 listing from 2026-08-21 that keeps delisted names; it is frozen at that date",
    what=(f"The axis includes contracts that died before and inside the window (by trades {h1['symbols_dead_inside_cache']} died inside the cache; {len(c2['no_finite_bar'])} names have no bar at all). "
          "No 2022+ survivorship is visible in the axis. The CRYPTO mask keeps the 31 names absent from today's exchangeInfo. Names listed after 2026-08-21 never enter research data; production pins are also frozen, so the two agree."),
    evidence=[{"source": "retrain_2026-09/jpline_lineage_2026-09-05.md:26", "quote": "宇宙符号轴 ... S3 列 data/futures/um/monthly/klines/ 前缀 ... panel_symbols_wide.txt ... 829"},
              {"source": "devices_data/receipts/AD_C_cache_members.json C2 + AD_H H1", "quote": f"no_finite_bar {c2['no_finite_bar']}; dead inside cache by trades {h1['symbols_dead_inside_cache']}"},
              {"source": "universe_crypto_2026-09-08/scripts/build_crypto_mask.py:11", "quote": "if s in CLS else True for s in syms])  # 未知 ⇒ 保留"}],
    status="VERIFIED_IMMATERIAL", affects=["future_eval"], severity="P3", severity_reason="No survivorship in the axis for the evaluation window.", action="Refresh the axis when the universe is refreshed (separate event).", method="VERIFIED", dependents=[])

add(id="TIM-02", layer="metrics archive label switch (2024-03-04)",
    title="Only L2 reads the metrics archive and it applies the label regime by date",
    what="The 2024-03-04 switch (window END labels before, START after) matters only to consumers of data.binance.vision metrics; since 09-09 those are the L2 devices, which encode the regime explicitly. No panel, cache or retrain builder reads the archive (AUDIT_TRAIN TRN-08).",
    evidence=[{"source": "uplift_r3_2026-09-13/L2/devices/l2_a_archive.py:12-14,225", "quote": "archive labels = window END up to 2024-03-03 and window START from 2024-03-04 ... REG = (\"END_pre_2024-03-04\", \"START_from_2024-03-04\")"},
              {"source": "devices_data/receipts/AD_E_consumers_matrix.json metrics_archive", "quote": json.dumps(mx["metrics_archive"]["by_research_line"])}],
    status="VERIFIED_IMMATERIAL", affects=["future_eval"], severity="P3", severity_reason="Handled at the only consumer.", action="None.", method="VERIFIED", dependents=["FIXPROGRAM D2"])

add(id="TIM-03", layer="5m cache timestamps",
    title="The cache labels bars by close time; panel features end one bar before the anchor, DL features include the anchor bar",
    what="ts = open_time + 5 min in the cache builder and the producer; panel windows are rows [E-w, E-1] (one bar staler than production), DL windows [E-w+1, E] with targets from E+1. The rev24 panel factor is out of the combo book; research factors from the panel are one bar stale, which is conservative.",
    evidence=[{"source": "retrain_2026-09/pod_merge_cache_ext.py:24", "quote": "k['ts'] = pd.to_datetime(k.open_time.astype(np.int64), unit='ms') + pd.Timedelta('5min')"},
              {"source": "retrain_2026-09/pod_dlw_features_ext.py:3", "quote": "窗端点对齐为 rows [E−w+1, E+1)(含收盘于 N 的那根 bar; 目标从 E+1 起 ⇒ 零重叠零间隙)"}],
    status="VERIFIED_IMMATERIAL", affects=["future_eval"], severity="P3", severity_reason="Consistent within each lineage; the king case is TIM-01.", action="None.", method="VERIFIED", dependents=[])

add(id="HOL-02", layer="5m cache / holes",
    title="Cache holes E-0908-D and E-0909-B are filled in holefix2 and in its extension",
    what="holefix2 filled 1,422,720 cells in four runs; the coverage gate passes on holefix2 and on the x0910 extension, and the r6 extension is bitwise equal to holefix2 on the common prefix. The residual lives in the panels built earlier (HOL-01).",
    evidence=[{"source": "AD_D_panel_holes.json holes", "quote": json.dumps(D["holes"]["fill_runs_utc"])},
              {"source": "uplift_2026-09-11/RESULT_r6_coverage_extension_2026-09-11.md (X1, BW-1)", "quote": "COVERAGE_GATE_V2 PASS (hole symbol-days 0 in multi-symbol runs; wide-gap days 0) ... bitwise_diff 0"}],
    status="FIXED_DEPLOYED", affects=["future_eval", "future_retrain"], severity="P3", severity_reason="Fixed at the cache.", action="None.", method="VERIFIED", dependents=[])

add(id="LIN-02", layer="lineage / write incident",
    title="A 09-12 test run rewrote dlw_v4raw/data/dlw_targets.npz on pod2; the bytes are identical",
    what="tests_pipeline_gates [S] R5 ran the untranslated legacy chain_v4_data.sh on pod2 at 15:12Z; the 60 s timeout killed bash but the python child finished at 15:17:54Z and rewrote the RAW targets, their report and chain_v4_data.log. The file's sha is still d1976cf6 (the 09-09 value) and the test was switched to a translated copy in 942b3e73.",
    evidence=[{"source": "retrain_2026-09/v4_chain_2026-09-09/receipts/monthly_chain_2026-09-12/tests_pipeline_gates_pod2_final3.log:380-381", "quote": "subprocess.TimeoutExpired: Command '['bash', '/workspace/w3_monthly_chain_2026-09-12/device/chain_v4_data.sh']' timed out after 60 seconds"},
              {"source": "devices_data/receipts/AD_A_inventory.json dlw_v4raw/data/dlw_targets.npz", "quote": f"sha {FA['dlw_v4raw/data/dlw_targets.npz']['sha256'][:16]} mtime {FA['dlw_v4raw/data/dlw_targets.npz']['mtime_utc']}"}],
    status="VERIFIED_IMMATERIAL", affects=["reporting"], severity="P3", severity_reason="No content change; same family as E-0912-B.", action="Record the incident next to E-0912-B.", method="VERIFIED", dependents=[])

add(id="LIN-03", layer="lineage / builder identity",
    title="Builder copies on pod2 match git; all audit receipts are bound to the committed devices",
    what="16 builder copies on pod2 equal git HEAD byte for byte; build_dev_v4.py, pod_legs_v4b.py and pod_export_bundle_v4.py on pod2 equal earlier commits (5749a821, 3f058a7c, 5d214260). Every AD receipt's self_sha256 equals the committed device.",
    evidence=[{"source": "devices_data/receipts/AD_A_inventory.json (pod2 builder shas) vs git show HEAD:<path> | shasum", "quote": "fund_pull_pod fa665810, pod_panel_ext db7f0474, pod_panel_splice a9c29141, pod_fea_ext_clamp b9f9c728, pod_dlw_targets_raw d7c52823, make_raw_patch 7716e7d3 ... equal"}],
    status="VERIFIED_IMMATERIAL", affects=["reporting"], severity="P3", severity_reason="Traceable lineage.", action="None.", method="VERIFIED", dependents=[])

add(id="EVL-01", layer="replay device default",
    title="w10 sleeve devices still default CAL to 'simple' (expm1 on an already simple return); every committed run since 09-09 sets CAL=log",
    what="21 sleeve device files committed since 09-09 read os.environ.get(\"CAL\", \"simple\"); among receipt/log files committed since then, 39 record \"CAL\": \"log\" and none \"CAL\": \"simple\". A run that forgets the variable would apply expm1 to RAW y4.",
    evidence=[{"source": "uplift_2026-09-11/r18_foundation/devices/w10_sleeve_r18.py:17", "quote": "CAL = os.environ.get(\"CAL\", \"simple\")                 # simple = 交易所记账(y -> expm1)"}],
    status="VERIFIED_IMMATERIAL", affects=["future_eval"], severity="P3", severity_reason="Latent trap (E-0826-C family); no affected run found.", action="Make CAL required or default to log.", method="VERIFIED", dependents=[])

add(id="LED-01", layer="research readers of daily_nav (AUDIT_EXEC LED-04)",
    title="Research tools that read daily_nav.realised_by_type COMMISSION/REALIZED_PNL inside 07-29..09-12 print wrong fee columns; their conclusions do not use them",
    what=("live_root_cause_2026-09-09.py and live_root_cause_part3_flatten_funding.py print COMMISSION next to NAV, TRANSFER and FUNDING_FEE; three August probes (attr_2day, inrole_simple_return_rerun, phase_alignment_audit) and build_viz.py read COMMISSION/REALIZED_PNL. "
          "LED-04 affects COMMISSION and REALIZED_PNL (shared tranIds, BNB amounts); FUNDING_FEE and TRANSFER rows share no tranId. The 09-09 root cause rests on the position-times-mid decomposition, not on the fee column."),
    evidence=[{"source": "multi_asset/exports/live/pilot_journal/tools/live_root_cause_2026-09-09.py:80,82", "quote": "cm = float(bt.get(\"COMMISSION\") or 0) ... print(f\"... funding {ff:+7,.0f} comm {cm:+6,.0f} | pos×mid {pm:+8,.0f}\")"},
              {"source": "multi_asset/exports/live/pilot_journal/tools/live_root_cause_part3_flatten_funding.py:43,47", "quote": "cm=float(bt.get(\"COMMISSION\") or 0) ... tot_cm = sum(v[\"cm\"] for d, v in daily.items() if d >= \"20260827\")"},
              {"source": "docs/audit_pipeline_2026-09-13/AUDIT_EXEC.json LED-04", "quote": "24,723 tranIds shared by a COMMISSION and a REALIZED_PNL row of the same symbol; FUNDING_FEE rows share none"}],
    status="VERIFIED_IMMATERIAL", affects=["reporting"], severity="P3", severity_reason="Printed columns only; no decision depends on them.", action="Annotate those outputs; take fees from guard_twin income.jsonl if they are reused.", method="VERIFIED",
    dependents=["journal tables printed by the two 09-09 tools", "build_viz daily split chart"])

add(id="UNI-03", layer="universe mask frontier",
    title="September anchors use the last August mask row carried forward",
    what="umask_UPIT_CRYPTO ends 2026-08-31 00Z; x0910 September readings carry that row forward (declared in T2/T5c). A September listing, delisting or monthly refresh is therefore not reflected; not measured.",
    evidence=[{"source": "devices_data/receipts/AD_A_inventory.json", "quote": f"umask_UPIT_CRYPTO last {FA['review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz']['ts_axis']['last_utc']}; T5c umask_UPIT_CRYPTO_cf_x0910 last {FA['uplift_r2_2026-09-13/T5c/masks/umask_UPIT_CRYPTO_cf_x0910.npz']['ts_axis']['last_utc']}"},
              {"source": "uplift_r2_2026-09-13/T2/PREREG_T2_carry_net_sizing_2026-09-13.md:73", "quote": "the incumbent umask ends 2026-08-31 00Z, so its last row is carried forward for September — an approximation, labelled"}],
    status="OPEN_NOT_MEASURED", affects=["future_eval"], severity="P3", severity_reason="Declared approximation over 60 anchors.", action="Build a September mask row with the same monthly rule when September is rolled.", method="VERIFIED", dependents=["T2 d4", "T5c/T5d"])

# ------------------------------------------------------------------ counts
ST = ["FIXED_DEPLOYED", "VERIFIED_IMMATERIAL", "OPEN_MEASURED_MATERIAL", "OPEN_NOT_MEASURED", "PENDING_USER_DECISION", "DOC_STALE"]
by_status = {s: sum(1 for it in items if it["status"] == s) for s in ST}
by_sev = {p: sum(1 for it in items if it["severity"] == p) for p in ("P0", "P1", "P2", "P3")}
ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
POS = {it["id"]: k for k, it in enumerate(items)}
items.sort(key=lambda it: (ORDER[it["severity"]], POS[it["id"]]))

# ------------------------------------------------------------------ inventory rows
INV = [("5m cache (canonical)", "data/dlnative_5m_wide829_f16_holefix2.npz", "holefix2 chain (caliber_program holefix2_daily.py) on _ext", "v4 chain, P2, A0/NW, r12, r14, r21, audits"),
       ("5m cache (Sept extension)", "data/dlnative_5m_wide829_f16_holefix2_x0910.npz", "r6_merge_cache.py 3227e4f5 (pod2 only)", "T3, r12, r21"),
       ("5m cache (pre-fix)", "data/dlnative_5m_wide829_f16_ext.npz", "pod_merge_cache_ext.py de7a0661", "L2 alignment spectra, L4 symbol axis, gates"),
       ("raw-return patch", "review_scratch/raw_patch.npz", "make_raw_patch.py 7716e7d3", "dlw_v4raw RAW targets, STEP1 gate"),
       ("raw-return patch (Sept)", "uplift_2026-09-11/r6/out/raw_patch_x0910.npz", "r6_raw_patch_ext.py 808d2f66 (pod2 only)", "dlw_v4raw_x0910"),
       ("hole cells", "review_scratch/holefix2_cells.npz", "v4_hole_cells.py / holefix2 chain", "STEP1, build_dev_v4"),
       ("4h panel v1 canonical", "data/wide_panel_4h_v1.npz", "jpline (UNVERIFIABLE)", "splice prefix, panel_ext self-check"),
       ("4h panel v2ext", "data/wide_panel_4h_v2ext.npz", "pod_panel_ext.py db7f0474 on _ext", "every w10 replay (alias hist_v2), king PANEL_IN, T-series"),
       ("4h panel v3splice", "data/wide_panel_4h_v3splice.npz", "pod_panel_splice.py a9c29141", "DL targets/fea82, legs, bundle export"),
       ("4h panel v2ext x0910", "uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz", "r6_panel_splice.py cccc5b6b (pod2 only)", "T1, T2, T5, T5c, T5d, r12"),
       ("4h panel v3splice x0910", "uplift_2026-09-11/r6/out/wide_panel_4h_v3splice_x0910.npz", "r6_panel_splice.py cccc5b6b (pod2 only)", "none since 09-09"),
       ("EMA state", "fund_state_canoncont.json", "pod_panel_splice.py a9c29141", "bundle export EMA_STATE_JSON"),
       ("funding API pull", "fund_aug.json.gz", "fund_pull_pod.py fa665810", "panels, exporter, P2 ledger, L4/L4b"),
       ("funding Sept pull", "uplift_2026-09-11/r6/dl/r6_fund_sep.json.gz", "r6_fetch_funding.py 298927ad (pod2 only)", "x0910 panels, T5d"),
       ("P2 settlement ledger", "uplift_r2_2026-09-13/P2/work/ledger_full.npz", "p2_prep_inputs.py", "P2 S1/S2"),
       ("king features v4", "data/wide_fea_v4.npy", "pod_fea_ext_clamp.py b9f9c728", "v4 king export, STEP2"),
       ("king meta v4", "data/wide_fea_v4_meta.npz", "pod_fea_ext_clamp.py b9f9c728", "exporter, legs, build_dev_v4"),
       ("king features v2ext (in-service)", "data/wide_fea_v2ext.npy", "pod_fea_ext.py 02157bda", "in-service booster lineage, STEP2 reference"),
       ("accounting meta v4", "review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "build_dev_v4.py 0dbc2f60 (git 5749a821)", "every w10 replay (alias wide_fea_hist_meta), P2 accounting"),
       ("accounting meta x0910", "uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz", "r6_dev_tree.py faffd726 (pod2 only)", "T1, T2, T3, T5c, r12"),
       ("DL targets RAW", "dlw_v4raw/data/dlw_targets.npz", "pod_dlw_targets_raw.py d7c52823", "F10 v4 training, legs, F10 alignment in replays"),
       ("DL targets CLIP", "dlw_hf3/data/dlw_targets.npz", "pod_dlw_targets_raw.py d7c52823 (no patch)", "STEP1 reference"),
       ("DL targets in-service", "dlw_ext/data/dlw_targets.npz", "pod_dlw_targets_ext.py c21683ee", "in-service F10, A0 F10 alignment, P2"),
       ("DL fea82", "dlw_v4raw/data/dlw_fea82.npz", "pod_dlw_features_ext.py e86725cc", "F10 v4"),
       ("DL fea89", "f8_v4/data/f8_fea89.npz", "pod_f8_build_ext.py f606bffa", "F10 v4"),
       ("F10 legs v4", "f8_v4/data/f10v2_legs.npz", "pod_legs_v4b.py 6f0f0095 (git 3f058a7c)", "F10 v4 trainer (V2)"),
       ("king OOF v4", "review_scratch/king_v4/SLOW_v4.npy", "pod_export_bundle_v4.py 23b1a5c7 (bundle v4)", "A1x, P2 king OOF, r-series"),
       ("king OOF v3 on v4 axis", "review_scratch/king_v4/SLOW_v3_on_v4axis.npy", "build_dev_v4.py 0dbc2f60", "A0 king leg"),
       ("F10 OOF A0", "review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy", "build_dev_v4.py (align f8_ext yearly OOF)", "A0 F10 leg"),
       ("F10 OOF v4RAW", "review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s42.npy", "merge_mwf_v4b.py", "A1x, P2 F10 injection"),
       ("universe mask CRYPTO", "review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz", "build_crypto_mask.py 43ebca0d on build_umask.py (U-PIT)", "every m1 replay, P2 PIT universe"),
       ("A0 reference book", "uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz", "w10_sleeve.py b88e35a4", "~300 paired verdicts, T-series, P2")]
inv_rows = []
for nm, p, bld, cons in INV:
    r = FA[p]; ax = r.get("ts_axis") or r.get("E_ts_axis") or {}
    shape = r.get("shape") or next((v["shape"] for k, v in (r.get("members") or {}).items() if k in ("data", "y4", "y4s", "Y4", "mask", "W", "X", "row", "ft")), None)
    inv_rows.append({"dataset": nm, "path": "/workspace/" + p, "sha256_16": (r.get("sha256") or "")[:16], "bytes": r.get("bytes"), "mtime_utc": r.get("mtime_utc"),
                     "axis": ({"n": ax.get("n"), "first": ax.get("first_utc"), "last": ax.get("last_utc")} if ax else None), "shape": shape, "builder": bld, "consumers": cons})

# ------------------------------------------------------------------ october inheritance
OCT = [("Clip-compound on new clipped bars (E-0908-B)", "Yes unless the roll extends the patch; current data clean through 2026-09-11", "RET-01, AUDIT_TRAIN TRN-02"),
       ("Month-roll inputs without a committed builder", "Yes", "AUDIT_TRAIN TRN-01, LIN-01, FND-01"),
       ("King clock / label window (E-0909-F)", "Yes (pod_fea_ext_clamp.py again)", "TIM-01, LBL-01"),
       ("DL funding features from the 2026-08 live list", "Yes (PANEL_SPLICE keeps the v1 prefix)", "FEA-01"),
       ("Dead contracts with frozen rows / funding records", "Yes (no trades flag anywhere)", "TRD-01, TRD-02, TRD-05"),
       ("Non-crypto names in training members", "Yes, larger (September rows)", "UNI-01"),
       ("Hole residuals in panels and legs", "Partly: a fresh PANEL_KING is clean, PANEL_SPLICE prefix and LEGS_OLD rows are not", "HOL-01"),
       ("Pull-time funding interval", "Only if the September pull fills intervals", "FND-01, FND-02, AUDIT_TRAIN TRN-07"),
       ("Switch-row interval mislabels (spacing rule)", "Yes for API-only rows (September, and August if not rebuilt from zips)", "FND-02, FIXPROGRAM P9"),
       ("Fund EMA v0 train / v1 serve (H2b)", "Yes", "AUDIT_TRAIN TRN-04/TRN-05, FIXPROGRAM P1/R1"),
       ("Frontier truncation (E-0911-B)", "Yes (tail gate floor calibrated at 0.9756 admits it)", "AUDIT_TRAIN TRN-17"),
       ("Forward member predicate (D20)", "Yes, but it removes almost nothing", "FWD-01, AUDIT_TRAIN TRN-06"),
       ("Cache holes", "No (coverage gate in the driver)", "HOL-02"),
       ("King window wrap (E-0909-A)", "No (clamp builder)", "CALIBER_STATUS"),
       ("Metrics label switch", "No (no builder reads metrics)", "TIM-02, AUDIT_TRAIN TRN-08")]

NOT_CHECKED = [
    "Anything that exists only on jpline (unreachable since 09-04): the v1 canonical panel builder and its 2020-2021 caches, w3lane funding (UNVERIFIABLE); v1 is used here only as data.",
    "Declared settlement intervals for 2026-08 and 2026-09 API rows (FND-02): the 2026-08 fundingRate zips were not on pod2 and no download was made.",
    "The size of FEA-01, TRD-02, TRD-04, HOL-01 and UNI-01 on F10 predictions, books or state readings; no model was retrained and no arm re-run.",
    "fea89 (f8_fea89) column-level lineage, its funding-derived columns and its trend_288 global cumulative sum; legs Z24/ZFD beyond the ZFD finiteness count.",
    "Production-side live state (rolling.npz, aux ledger, seat seeds, F10 fea171 inputs) beyond reading shadow_loop_v3.py for the clock; owned by AUDIT_PROD.",
    "Frozen-close rows in the 1m premium index and spot archives used by r5 basis and L4 (only the 5m perp cache was measured).",
    "September 11-30 data: no research cache or panel contains it.",
    "Per-device exposure of RET-02 consumers to bound bars.",
    "Other OOF arrays (v4CLIP, v4sRAW, A0p, SLOW_v4e) for masks and coverage; NW/C0 inputs beyond A0's.",
    "Whether any committed RESULT quotes numbers built on superseded metas (meta_newprod.npz, _ext-based panels) after 09-09 beyond the device grep; only device references were classified.",
    "LOB, OI/metrics (L2), KRW (T7) and event (L3) datasets beyond confirming the metrics label handling."]

CONSUMER_TABLE = {k: {"n_devices": v["n_devices"], "by_research_line": v["by_research_line"]} for k, v in mx.items()}

meta = {"created_utc": "2026-09-13T14:3xZ", "session": "https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (auditor teammate aud-data of team-lead; read-only)",
        "scope": "data lineage and return / funding / timestamp / universe / tradability calibers of every panel, cache, meta, target, OOF and mask read by research, evaluation and retrain devices committed since 2026-09-09",
        "frozen": {"research_repo_branch": "research/book-uplift-2026-09-11", "device_commits_before_runs": ["feb7747e (A-E)", "deb8a47b (F, E v2)", "36633520 (G)", "60461e1a (H)"],
                   "consumer_scan_head": E["repo_head"], "pod2_data": {r["dataset"]: r["sha256_16"] for r in inv_rows},
                   "receipts": {n: J(n)["self_sha256"][:16] for n in sorted(os.listdir(RC)) if n.endswith(".json")}},
        "constraints_kept": ["every dataset opened read-only (np.load / zipfile streaming); no dataset written, moved or rewritten", "pod2 CPU only, nice 19, env -i with OMP=1; at most 6 worker processes; no GPU; PIDs 333197/339489 and P2 S2 processes untouched",
                             "no exchange or venue API call; no network download", "hashes guarded (bytes read == st_size)", "every device committed before it ran; every receipt's self_sha256 equals the committed device"],
        "status_legend": {"FIXED_DEPLOYED": "fixed in the data or code that current consumers read", "VERIFIED_IMMATERIAL": "checked; no effect on the named layers (resolution given)",
                          "OPEN_MEASURED_MATERIAL": "defect confirmed with numbers; real effect on the named layer, even if small", "OPEN_NOT_MEASURED": "mechanism confirmed, size of effect not measured",
                          "PENDING_USER_DECISION": "needs a user ruling", "DOC_STALE": "data and code are right, a document or memory note is wrong"}}
out = {"meta": meta, "counts": {"by_status": by_status, "by_severity": by_sev, "n_items": len(items)}, "items": items, "inventory": inv_rows,
       "october_inheritance": [{"defect": a, "carried_into_october": b, "items": c} for a, b, c in OCT], "dependency_matrix": CONSUMER_TABLE, "not_checked": NOT_CHECKED}
json.dump(out, open(os.path.join(ROOT, "AUDIT_DATA.json"), "w"), indent=1, ensure_ascii=False)

# ------------------------------------------------------------------ markdown
L = []
w = L.append
w("> **创建:** 2026-09-13 14:3xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (auditor teammate aud-data, read-only) | **状态:** 审计登记册(只读; 未改任何数据) | **作废条件:** 任一登记数据件 sha 变化(见 §0), 或任一登记项被修复/裁定后需差异复核")
w("")
w("# AUDIT_DATA — data lineage and calibers for research, evaluation and retraining")
w("")
w("Companion data: `AUDIT_DATA.json` (same items, same wording, plus the full inventory and dependency matrix). Every number below is rendered from the device receipts in `devices_data/receipts/` by `devices_data/build_audit_data.py`.")
w("")
w("## 0. What was audited, frozen at what")
w("")
w("| Object | Value |"); w("|---|---|")
w(f"| Research repo branch | `research/book-uplift-2026-09-11`; consumer scan at `{E['repo_head'][:10]}` over {E['n_devices_scanned']} devices committed since 2026-09-09 |")
w("| Devices (committed before each run) | `feb7747e` ad_inventory / ad_funding_iv / ad_cache_members / ad_panel_holes / ad_consumers_scan; `deb8a47b` ad_batch2 (+ scan v2); `36633520` ad_batch3; `60461e1a` ad_tradability |")
w("| Receipts | " + "; ".join(f"`{n}` self {J(n)['self_sha256'][:8]}" for n in sorted(os.listdir(RC)) if n.endswith(".json")) + " — each equals its committed device |")
w(f"| Canonical cache | `dlnative_5m_wide829_f16_holefix2.npz` sha {S('data/dlnative_5m_wide829_f16_holefix2.npz')}, {FA['data/dlnative_5m_wide829_f16_holefix2.npz']['ts_axis']['first_utc'][:10]} → {FA['data/dlnative_5m_wide829_f16_holefix2.npz']['ts_axis']['last_utc'][:16]} |")
w(f"| Accounting meta | `meta_newprod_v4.npz` sha {S('review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz')}; x0910 {S('uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz')} |")
w(f"| Replay panel | `wide_panel_4h_v2ext.npz` sha {S('data/wide_panel_4h_v2ext.npz')}; splice {S('data/wide_panel_4h_v3splice.npz')}; v1 canonical {S('data/wide_panel_4h_v1.npz')} |")
w("| Audit clock | pod2 receipts written D 13:17:43Z, A 13:18:15Z, B 13:20:56Z, C 13:21:35Z, F 13:25:23Z, G 13:33:23Z (all rc=0 before the 13:34Z session stop, none repeated), H 14:12:20Z; P2 S2 running throughout |")
w("")
w("Constraints kept: " + "; ".join(meta["constraints_kept"]) + ".")
w("")
w("Status legend: " + "; ".join(f"**{k}** = {v}" for k, v in meta["status_legend"].items()) + ".")
w("")
w("## 1. Result")
w("")
p1 = [it for it in items if it["severity"] in ("P0", "P1")]
w(f"**No P0 found. {len(p1)} P1 items.** All three are data facts that current evaluation and the October retrain inherit without any gate or register entry:")
w(""); w("| ID | Title | Status | Why P1 |"); w("|---|---|---|---|")
for it in p1: w(f"| {it['id']} | {it['title']} | {it['status']} | {it['severity_reason']} |")
w(""); w("| Status | Count |"); w("|---|---:|")
for s in ST: w(f"| {s} | {by_status[s]} |")
w(f"| **Total** | **{len(items)}** |")
w(""); w("By severity: " + ", ".join(f"{p} {by_sev[p]}" for p in ("P0", "P1", "P2", "P3")) + ".")
w("")
w("## 2. Short answers to the audit questions")
w("")
w("1. **Inventory.** Current devices read one canonical 5m cache (holefix2) plus its September extension, the pre-fix `_ext` cache only for axes/alignment, two raw-return patches, the v1/v2ext/v3splice panels and their x0910 extensions, the v4 king feature/meta pair, the v4 accounting meta, three DL target sets, fea82/fea89/legs, four OOF families, the CRYPTO mask, two funding pulls, the zip archive and P2's ledger. Paths, shas, builders, axes and consumers are in §6 and the JSON inventory; builders on pod2 equal git (LIN-03) except the x0910 builders, which are only on pod2 (LIN-01).")
w("2. **Known defects per dataset.** (a) Return caliber: accounting returns are RAW and every clipped bar through 2026-09-11 is patched (RET-01); king labels stay clipped sums over an early window (LBL-01); some diagnostics still recompute returns from the clipped channel (RET-02). (b) Funding interval: the x0910 builder is located and reproduced exactly (FND-01); the canonical panels match settlement truth, but the spacing rule mislabels switch rows in API-only months (FND-02); the v1 prefix has 138 wrong cells (FND-03). (c) Timestamps: close-time labelling is consistent (TIM-03), the king clock is not (TIM-01), the metrics switch is handled (TIM-02). (d) Universe: tokenized stocks are 7.3% of 2026 training members (UNI-01); the September mask is carried forward (UNI-03). (e) Forward masks: the predicate removes almost nothing and the OOF arrays carry it exactly (FWD-01, FWD-02). (f) Survivorship: the axis keeps delisted names (UNI-02); the DL funding inputs exist only for the 2026-08 live list (FEA-01).")
w(f"3. **Tradability by trades (L4b lesson).** No research layer defines tradability by trades. {h1['symbols_dead_inside_cache']} dead contracts write {h1['post_death_signature']['post_death_untraded_rows']/1e6:.1f}M frozen rows with return exactly 0 in the canonical cache and {h5['symbols_with_events_after_death']} of them keep funding records; universes, rank bases and statistics admit them (TRD-01..05). On A0 the held exposure is at most {max(h2[y]['absW_DEAD_share'] for y in YRS):.1e} of gross; the fund rank base carries {BASE_RNG} dead names (yearly mean); member sets carry {U_RNG}.")
w("4. **Dependent results.** Each item lists its dependents; only FND-01's T5c reading was re-run (T5d, not yet re-run by the lead). Nothing else has been re-run.")
w(f"5. **October chain.** See §4: of {len(OCT)} checked defects, {sum(1 for _, b_, _c in OCT if b_.startswith('Yes') and not b_.startswith('Yes unless'))} would be carried into the next retrain as the chain stands, {sum(1 for _, b_, _c in OCT if b_.startswith(('Yes unless', 'Partly', 'Only if')))} conditionally, and {sum(1 for _, b_, _c in OCT if b_.startswith('No'))} not.")
w("6. **Inputs folded in.** AUDIT_TRAIN TRN-02: data side confirmed clean through 2026-09-11 00:00Z, nothing later exists (RET-01). AUDIT_EXEC LED-04: research readers of the daily_nav fee split listed; no conclusion depends on them (LED-01).")
w("")
w("## 3. Register")
w("")
w("| ID | Layer | Title | Status | Sev | Affects |"); w("|---|---|---|---|---|---|")
for it in items: w(f"| {it['id']} | {it['layer']} | {it['title']} | {it['status']} | {it['severity']} | {', '.join(it['affects'])} |")
w("")
for it in items:
    w(f"### {it['id']} — {it['title']}"); w("")
    w(f"- **Layer:** {it['layer']}")
    w(f"- **What is wrong or unverified:** {it['what']}")
    w("- **Evidence:**")
    for ev in it["evidence"]: w(f"  - `{ev['source']}` — {ev['quote']}")
    w(f"- **Status:** {it['status']}"); w(f"- **Affects:** {', '.join(it['affects'])}")
    w(f"- **Severity:** {it['severity']} — {it['severity_reason']}"); w(f"- **Recommended action:** {it['action']}")
    if it.get("dependents"): w(f"- **Dependents (re-run status):** {'; '.join(it['dependents'])}")
    w(f"- **Method:** {it['method']}"); w("")
w("## 4. Would the next retrain still carry them? (October chain inputs)")
w(""); w("| Defect | Carried into October | Items |"); w("|---|---|---|")
for a, b, c in OCT: w(f"| {a} | {b} | {c} |")
w("")
w("## 5. Not checked"); w("")
for x in NOT_CHECKED: w(f"- {x}")
w("")
w("## 6. Appendix A — inventory (pod2, measured by ad_inventory.py)")
w(""); w("| Dataset | Path | sha256[:16] | Axis | Builder | Consumers |"); w("|---|---|---|---|---|---|")
for r in inv_rows:
    ax = r["axis"]; axs = f"{ax['n']:,} · {ax['first'][:10]} → {ax['last'][:16]}" if ax else (str(r["shape"]) if r["shape"] else "")
    w(f"| {r['dataset']} | `{r['path']}` | {r['sha256_16']} | {axs} | {r['builder']} | {r['consumers']} |")
w("")
w("## 7. Appendix B — dependency matrix (dataset token × research line; number of devices committed since 09-09, audit devices excluded)")
w("")
lines = sorted({g for v in mx.values() for g in v["by_research_line"]})
def short(g): return g.replace("multi_asset/exports/research/", "").replace("uplift_2026-09-11", "r1").replace("uplift_r2_2026-09-13", "r2").replace("uplift_r3_2026-09-13", "r3").replace("retrain_2026-09", "rt09").replace("parity_replay_2026-09-12", "parity")
agg = collections.OrderedDict()
for k, v in mx.items():
    row = collections.Counter()
    for g, n in v["by_research_line"].items():
        s = short(g); key = "r1 (uplift round 1)" if s.startswith("r1") else ("v4 chain" if s.startswith("rt09/v4_chain") else ("rt09 other" if s.startswith("rt09") else s))
        row[key] += n
    agg[k] = row
cols = [c for c in ["v4 chain", "rt09 other", "parity/phase2", "parity/devices", "r1 (uplift round 1)", "r2/T1", "r2/T2", "r2/T3", "r2/T4", "r2/T4b", "r2/T5", "r2/T5c", "r2/T5d", "r2/T6", "r2/T7", "r2/T8", "r3/L2", "r3/L4", "r3/L4b"] if any(c in r for r in agg.values())]
others = sorted({c for r in agg.values() for c in r} - set(cols))
cols += others
w("| Token | total | " + " | ".join(cols) + " |"); w("|---|---:|" + "---:|" * len(cols))
for k, row in agg.items(): w(f"| {k} | {mx[k]['n_devices']} | " + " | ".join(str(row.get(c, '')) for c in cols) + " |")
w("")
w("## 8. Reproduction notes")
w("")
w("- Devices A-D, F-H: `bash docs/audit_pipeline_2026-09-13/devices_data/run_pod2.sh sync` then `run_pod2.sh <A|B|C|D|F|G|H>` (pod2, `env -i`, nice 19); E: `run_pod2.sh E` (Mac, git objects); receipts via `run_pod2.sh fetch`.")
w("- Positive controls read before any finding: C3 member lists and king label window reproduced bitwise; B PC2 r6 funding rule reproduced the x0910 tail exactly; D kline columns equal away from hole neighbourhoods; H frozen-row signature 100%.")
w("- Render: `python3 docs/audit_pipeline_2026-09-13/devices_data/build_audit_data.py` (reads receipts only).")
open(os.path.join(ROOT, "AUDIT_DATA.md"), "w").write("\n".join(L) + "\n")
print("AUDIT_DATA written:", len(items), "items", by_status, by_sev)
