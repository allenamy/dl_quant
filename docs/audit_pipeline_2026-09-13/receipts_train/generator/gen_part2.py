# -*- coding: utf-8 -*-
# Part 2: register items TRN-01..TRN-12
C = "multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09"
T = "multi_asset/exports/research/retrain_2026-09"
R = []
def item(**k): R.append(k)

item(id="TRN-01", layer="DATA (upstream month roll)",
 title="The October month-roll stage (cache roll, hole cells, raw patch, panels, funding tail, EMA state, base json, live pins) is outside the driver, has no §0★ command, and the git builders for it overwrite September's receipt-registered inputs",
 what_is_wrong=("chain_v4_monthly.sh starts from CACHE / PANEL_SPLICE / PANEL_KING / RAW_PATCH / HOLE_CELLS / FUND_AUG / EMA_STATE_JSON / BUNDLE_BASE / LIVE_PINS. "
   "The October template leaves them as TODO paths and no document says how to produce them: RUNBOOK §0★ step 1 only says 'holefix2 正典 + 滚动补月', and §2 — the only place the upstream commands were ever written — is void. "
   "Every git script for these inputs hardcodes September or older paths. Run as-is they read the wrong lineage (holefix instead of holefix2, _fresh→_ext instead of the holefix2 roll) or overwrite files that September's gate and export receipts hash (raw_patch, holefix2_cells, fund_aug, fund_state_canoncont, wide_panel_4h_v3splice) — the E-0912-B failure class. "
   "pod_panel_ext.py ignores FUND_AUG and reads the September funding file, whose rows end 2026-09-01 02:00Z, so September anchors lose funding under its 12h staleness rule (r6 ties this to E-0911-B). "
   "The only month extension ever done (r6, to 2026-09-10) used scripts that exist only on pod2, not in git, and one of them carries the x0910 interval defect. "
   "The driver has no panel parity gate (the old gate ① was dropped), so none of this would be caught before training. "
   "Late vendor data adds a further decision the runbook does not make: the 2026-08-31 day in the September cache was synthesised by holefix2 (229,824 cells) and the vendor archive for it now exists (r6 §2)."),
 evidence=[
   f"{C}/v4_month_2026-10.env.template L9-11, L13, L27, L29, L31-32: CACHE / PANEL_SPLICE / PANEL_KING / HOLE_CELLS / BUNDLE_BASE / EMA_STATE_JSON / LIVE_PINS / FUND_AUG = TODO_ paths",
   "docs/RUNBOOK_monthly_retrain_2026-10.md L15 (step 1: no roll command); L115, L130, L148 '⛔ 作废(2026-09-12)' on §2, §3, §4",
   f"{T}/caliber_program_2026-09-09/make_raw_patch.py 7716e7d3 L5 zload(\"/workspace/data/dlnative_5m_wide829_f16_holefix.npz\"); L33 np.savez_compressed(\"/workspace/review_scratch/raw_patch.npz\", ...) = September RAW_PATCH (STEP1 input raw_patch adecf276)",
   f"{C}/v4_hole_cells.py 6afd2672 L8/L10 hardcoded holefix2 and ext caches; L38 np.savez(\"/workspace/review_scratch/holefix2_cells.npz\", ...) = September HOLE_CELLS",
   f"{T}/pod_merge_cache_ext.py de7a0661 L42 base '/workspace/data/dlnative_5m_wide829_f16_fresh.npz'; L59-61 output '..._ext.npz'",
   f"{T}/pod_panel_ext.py db7f0474 L65 AUG = json.loads(gzip.open(\"/workspace/fund_aug.json.gz\", \"rt\").read()) (no env); L160 stale = ... > 12 * 3600",
   f"{T}/pod_panel_splice.py a9c29141 L11-12 CAN = wide_panel_4h_v1.npz, EXT = wide_panel_4h_v2ext.npz; L115 json.dump(state, open(\"/workspace/fund_state_canoncont.json\", \"w\")); L116 np.savez_compressed(\"/workspace/data/wide_panel_4h_v3splice.npz\", **out)",
   f"{T}/fund_pull_pod.py fa665810 L29 gzip.open(\"/workspace/fund_aug.json.gz\", \"wt\") = September FUND_AUG (BUNDLE_export registered input fund_aug)",
   "multi_asset/exports/research/uplift_2026-09-11/RESULT_r6_coverage_extension_2026-09-11.md L109 (S5): 'pod_panel_ext.py 的 funding 只读到 fund_aug.json.gz 的 2026-09-01 02:00Z, 九月行会被它 L160 的 12h 陈旧规则判 NaN —— 那正是 E-0911-B 本身'; §2: vision had no 2026-09 monthly funding zip, '九月 funding 只能走 REST'; 08-31 day was holefix2-filled and its vendor archive now returns 200",
   "pod2 read-only 2026-09-13T13:12Z (receipts_train/pod2_readonly_receipt_2026-09-13T1312Z.txt): r6_panel_splice.py cccc5b6b, r6_merge_cache.py 3227e4f5, r6_raw_patch_ext.py 808d2f66, r6_fetch_funding.py 298927ad exist only under /workspace/uplift_2026-09-11/r6/; git ls-files has no r6_*.py",
   f"{C}/chain_v4_monthly.sh e8e688d5 L49 PF_INPUTS: existence check only; no panel parity stage in L45-303",
 ],
 status="OPEN_NOT_MEASURED", affects=["future_retrain", "future_eval"], severity="P1",
 severity_reason="October cannot be started from git without improvising this stage; the obvious improvisations either invalidate September's registered receipts (E-0912-B class) or silently blank September funding features, and no driver gate would catch either.",
 recommended_action=("Add a month-roll stage (or driver) whose inputs and outputs are month-contract keys under $R and which refuses any output path equal to a previous month's contract value; move r6_merge_cache / r6_raw_patch_ext / r6_panel_splice into git with the interval fix of TRN-07; make pod_panel_ext.py read FUND_AUG from env; "
   "decide and write down whether late vendor archives replace holefix2-filled rows; restore a panel parity gate on the common prefix before the data stage; put the commands in RUNBOOK §0★."),
 method="VERIFIED (code, pod2 read-only listing); October outcome INFERRED")

item(id="TRN-02", layer="DATA (targets)",
 title="Raw-return patch coverage is not checked, so E-0908-B can return silently on the new month's clipped bars",
 what_is_wrong=("The 5m cache stores ret5 clipped at ±0.30; DLWT_RAW_PATCH puts back the exact return for clipped bars before 4h labels are compounded (the E-0908-B fix). "
   "Nothing verifies that the patch covers every clipped bar of this month's cache, or that each patch row/col still addresses the same timestamp and symbol. "
   "STEP1 part A only checks that RAW−CLIP differences sit inside patched windows, so a bar missing from the patch (RAW == CLIP there) is invisible. "
   "The October template gives RAW_PATCH a normal path with no TODO marker (preflight only checks existence), and the git patch builder cannot target the October cache (TRN-01). "
   "The 2026-09-01..09-10 extension alone found 3 new clipped bars: AKEUSDT +42.5%, BULLAUSDT +55.8%, WOOUSDT +30.06%, all stored as +0.30."),
 evidence=[
   f"{C}/pod_dlw_targets_raw.py d7c52823 L78-81 `_rtz[_P[\"row\"], _P[\"col\"]] = _P[\"raw32\"]` (no coverage assert, no ts/symbol assert); L100 y4s = np.expm1(CS_L[hi_t] - CS_L[lo_t])",
   f"{C}/v4_gate_step1_m.py 79950786 part A: window mask X built only from patch rows (`for t, c in zip(prow, pcol): ... X[lo:hi, c] = True`); PASS uses y4s_big_outside_patch_windows == 0",
   f"{C}/v4_month_2026-10.env.template L12 RAW_PATCH=$R/raw_patch.npz (no TODO_)",
   "multi_asset/exports/research/uplift_2026-09-11/r6_RECEIPT_raw_patch.json: old_n 952, new_kept 3 (AKEUSDT 2026-09-02 21:45Z raw 0.4249; BULLAUSDT 2026-09-05 03:00Z raw 0.5581; WOOUSDT 2026-09-06 01:35Z raw 0.3006; clip16 0.30005)",
   "memory clip_compound_label_defect (E-0908-B): clip then compound writes −48% as +55%",
 ],
 status="OPEN_NOT_MEASURED", affects=["future_retrain", "future_eval"], severity="P1",
 severity_reason="Wrong training labels and wrong replay accounting on exactly the extreme-move names that drive tail losses, with no gate able to see it; the last extension already had 3 such bars in 10 days.",
 recommended_action=("Before building targets assert {(row, col): |ret5| == float16(0.30)} ⊆ patch (row, col) minus declared-unresolved, and CTS[row] == ts and symbols[col] == symbol for every patch row; give RAW_PATCH a TODO_ value and an env-located generator."),
 method="VERIFIED")

item(id="TRN-03", layer="DL (deployment artifact)",
 title="The deployable F10 numpy model is produced outside every gate; a bare export silently packages the in-service 09-01 model",
 what_is_wrong=("The live DL leg reads fea171/f10_live_s42_np.npz. The driver stops at the refit .pt and its sidecar; there is no stage for the numpy export, the V1 np==torch gate, the V3' leak check, or the >=14-day forward shadow that STATE lists as FIX7's deployment precondition. "
   "pod_f10_np_export.py still has the silent defaults the reviewer removed from the refit (R1): without explicit env it loads /workspace/f8_ext/models/f10_live_s42.pt and /workspace/dlw_ext targets, i.e. the in-service generation. "
   "It also writes trained_through = max(E_ts) of the targets (pool end), the E-0907-D mislabel (TRN-14)."),
 evidence=[
   f"{C}/chain_v4_monthly.sh e8e688d5: stages preflight..export (L45-303); grep for np_export|np_check|leakcheck|swap returns nothing",
   f"{T}/pod_f10_np_export.py 3e304c27 L13 OUT = os.environ.get(\"F10_OUT\", \"/workspace/f8_ext\"); L14 DLW = os.environ.get(\"F10_DLW\", \"/workspace/dlw_ext\"); L15 CK = f\"{{OUT}}/models/f10_live_s{{SEED}}.pt\"; L26 trained_through = int(TG[\"E_ts\"].astype(np.int64).max())",
   "docs/RUNBOOK_monthly_retrain_2026-10.md L19 (step 4 lists gates V1 / V3' in text only)",
   "STATE.md (line ~207 at 13Z): 'FIX7 / FLOOR5 = 候选, 未部署。欠: 前向影子 ≥14 天 + 用户字'",
   "~/wide_shadow/fea171/f10_live_s42_np.npz 351ae26b (read-only): trained_through 1788120000 = 2026-08-30T20:00Z",
 ],
 status="OPEN_NOT_MEASURED", affects=["future_retrain", "live_trading", "reporting"], severity="P1",
 severity_reason="The only file the live DL leg loads is made by an ungated manual step whose defaults point at the previous generation.",
 recommended_action=("Add an np_export stage after refit: F10_OUT / F10_DLW / SEED required (refuse defaults), V1 receipt through finalize bound to the sidecar pt_sha256, carry trained_through_label_utc / pool_end into the npz; add a V3' leak-check stage; put the FIX7 forward-shadow precondition (or an explicit waiver) into the swap checklist."),
 method="VERIFIED")

item(id="TRN-04", layer="KING (feature caliber)",
 title="(a) H2b is reintroduced: the October export trains king on v0 fund EMA in column 80 and ships a v1 EMA state that the producer serves in column 80",
 what_is_wrong=("Column 80 of the king features is the panel's f_fund_ema (EMA of the raw per-settlement rate, v0). The exporter fits slow2026 on those features and, in the same run, writes fund_ema_v1_state.json normalised to 8h (v1); the producer feeds that state into column 80. "
   "4h-settlement names are served at 2x and 1h names at 8x the training scale. No gate in the chain or the export gate scores the booster on the producer's feature path."),
 evidence=[
   f"{C}/pod_fea_ext_clamp.py b9f9c728 L63 FUND = [PW[\"f_fund_ema\"], PW[\"f_fund_now\"]] → cols 80/81",
   f"{T}/pod_panel_splice.py a9c29141 L94 e0 = e0 + a * (fr[i_] - e0) (raw rate) → L100 out[\"f_fund_ema\"]; L95 e1 uses rate_nf (v1)",
   f"{C}/pod_export_bundle_v4.py 42555a37 L40-41 load BUNDLE_FEA/BUNDLE_META; L46 keep drops only ret5_sum_48/288; L58 rows_X; L67-69 fit + save_model(slow2026.txt)",
   f"{C}/pod_export_bundle_v4.py L231-234 i_ derived, rn = r_ * (8.0 / i_); L242 ema_state[s] = {{\"acc\": ...}}; L245-251 EMA_STATE_JSON override then fund_ema_v1_state.json; L256 \"fund_caliber\": \"v1 normfix HL3d\"",
   "~/wide_shadow/shadow_loop_v3.py e9c98374 L147 booster = lgb.Booster(model_file=slow2026.txt); L344 rn = rate * (8.0 / iv); L412 fe_v[j] = est[\"acc\"]; L418 FE_ANCH[:, 80] = np.nan_to_num(fe_v[m], nan=0); L421-422 booster.predict(X)",
   f"{C}/v4e_gate_export_v2.py d63f4ec3 L233 and gate_signal_parity_v2.py abc45cad L59 read only f_fund_ema_v1 for the fund leg; no booster-on-producer-path parity",
   "memory king-fund-ema-feature-train-v0-serve-v1 / T4 RESULT: both in-service boosters v0-trained; split inside the exporter",
 ],
 status="VERIFIED_IMMATERIAL",
 status_resolution="T4 frozen rule (PREREG sha 0f94b754): KING_LIVE 2024+ book Δg (v1−v0) +0.0181 [−0.030, +0.063] s42, +0.0161 [−0.033, +0.065] s2027; ΔIC −0.000101 [−0.000272, +0.000070]; resolution ±0.05 bps/anchor.",
 affects=["live_trading", "future_retrain"], severity="P2",
 severity_reason="Measured below resolution, but unguarded, and its size scales with the share of gross on non-8h names (82% per T1), which moves with the settlement-interval regime.",
 recommended_action=("User ruling on the caliber (serve v0 in col 80, or build king features from f_fund_ema_v1 and retrain). Independently add an export-stage raw-score parity gate: score recent anchors with the new booster on the offline FEA and on the producer feature path and require max|Δ| within tolerance."),
 method="VERIFIED")

item(id="TRN-05", layer="DL (feature caliber)",
 title="(b) The same v0-train / v1-serve split is reintroduced for V2MAIN, and October's fold checkpoints still cannot measure it",
 what_is_wrong=("fea82 column 80 is built from the v3splice panel's f_fund_ema (v0) for training; serving builds the same column from the producer's v1 EMA state. The October chain changes neither side. "
   "Monthly fold checkpoints are saved as bare state_dicts without mu/sd, so the historical book effect (NOT MEASURED in T4b) stays unmeasurable from October's artifacts."),
 evidence=[
   f"{T}/pod_dlw_features_ext.py e86725cc (pod2 == git) L73 FUND = [PW[\"f_fund_ema\"], PW[\"f_fund_now\"]]; driver L139 F171_PANEL=$PANEL_SPLICE",
   "~/wide_shadow/fea171/combo_stage.py b5c698f9 L138-141 fe[-1, j] = float(est[\"acc\"]) (producer v1 state); L146 np.savez(xfer_panel_live.npz, f_fund_ema=fe, ...); dlw_features.py 29ae6a98 L73 reads PW[\"f_fund_ema\"]",
   f"{C}/pod_f10_train_monthly_v4.py fd5707bd L435 torch.save(best_state, f\"{{MWF_OUT}}/models/{{TAG}}_{{YM}}.pt\") (no mu/sd)",
   "T4b RESULT (memory king-fund-ema…): served mu/sd match v0 on 171 columns (col 80 rel 2.4e-7; v1 ~150% off); historical book effect NOT MEASURED; live 6 anchors combo target L1 median 0.0022; zero-filled history rows do not reach the scored row",
 ],
 status="OPEN_NOT_MEASURED", affects=["live_trading", "future_eval"], severity="P2",
 severity_reason="Unguarded unit mismatch on the DL leg (which also sets V2MAIN's seat coefficient); the fix that makes it measurable is one line.",
 recommended_action=("Save mu/sd/alpha with every fold checkpoint so the v0/v1 effect can be measured on October folds; then a user ruling on the caliber; add DL raw-score parity (numpy model on producer features vs torch on training features) to the np_export stage of TRN-03."),
 method="VERIFIED")

item(id="TRN-06", layer="DATA / KING / DL (universe)",
 title="(c) D20 is reintroduced and is wider than recorded: members are selected on a finite forward label, so king OOF and F10 OOF both exist only where future bars exist",
 what_is_wrong=("King meta and DL targets both choose each anchor's members with a condition that the forward 4h label is finite, before the top-400 volume cut. King OOF predictions are written only on finite-label members (D20). "
   "fea82/fea89 pairs are the DL members, so F10 monthly OOF scores exist only there as well (P2 recorded this as not checked). "
   "The producer and combo_stage choose members from trailing data only. So training cross-sections exclude names that stop trading within 4h, and replay/judge universes drop them before the fact."),
 evidence=[
   f"{C}/pod_fea_ext_clamp.py L37 ok = (covr[i] >= 0.95) & (v7[i] >= 1e-4) & np.isfinite(y4[i])",
   f"{C}/pod_export_bundle_v4.py L55-56 (training rows need >=50 finite labels); L80-81 and L91-92 okm = np.isfinite(y4[a, m]); PRED[a, m[okm]] = pv[sel]",
   f"{C}/pod_dlw_targets_raw.py L107 ok = (covr[i] >= 0.95) & (vstd[i] >= 1e-4) & np.isfinite(y4s[i]); L109-110 NTOP cut after the filter",
   f"{T}/pod_dlw_features_ext.py L37 MS = TG[\"members\"], L81/L95 pair_a/pair_s from MS; {C}/pod_f10_train_monthly_v4.py L398-414 PRED_f written only at pair symbols midx",
   "~/wide_shadow/fea171/combo_stage.py L121-123 ms_arr[i] = pm (current members, no future term)",
   "docs/PREREG_producer_parity_phase2_oos_2026-09-12.md L329 (D20 VERIFIED for king; 'F10 OOF 的可得性掩码未核')",
 ],
 status="OPEN_NOT_MEASURED", affects=["future_eval", "future_retrain"], severity="P2",
 severity_reason="Optimistic for levels (delisting/halting names removed ex ante) and shared by A0/A1 in paired contrasts; size unknown; L4b (forced exits) measures the related population.",
 recommended_action=("Select members from trailing data only and mask the loss/label (not membership) where the label is not finite; write OOF predictions for every trailing-eligible member; report per year the anchor×name cells removed by the forward-finite term."),
 method="VERIFIED (code); impact not measured")

item(id="TRN-07", layer="DATA (funding intervals)",
 title="(d) The x0910 interval error returns if September's funding tail carries a pull-time interval; the git splice, panel builder and exporter all apply it and no gate checks intervals",
 what_is_wrong=("The defect is one pull-time settlement interval applied to every API tail row of a symbol. r6 read fundingIntervalHours from /fapi/v1/fundingInfo once and its splice applied it to all September rows, so names whose interval changed in September got the wrong 8h normalisation (547 cells, 23 names; SKR and SOPH x1/4, IOST x8). "
   "The git pod_panel_splice.py, pod_panel_ext.py and pod_export_bundle_v4.py use the same `AUG_IV.get(s)` pattern; they are safe today only because the canonical fund_aug.json.gz has an empty intervals map, which forces timestamp-gap derivation. "
   "For October, September funding must come from REST (no monthly zip yet at month start), the puller is unspecified (TRN-01), and no gate compares intervals with settlement gaps. "
   "Scope: v0 EMA (king col 80, DL col 80) uses the raw rate and is unaffected; v1 EMA, f_fund_iv, carry and FTRIM are affected (fund leg in the exporter guard and leg_returns, legs, replay/judge). The bundle's fund_ema_v1_state.json is read by the producer only on a cold bootstrap."),
 evidence=[
   "pod2 /workspace/uplift_2026-09-11/r6/r6_fetch_funding.py 298927ad L33-34 INFO = {d[\"symbol\"]: float(d[\"fundingIntervalHours\"]) ... fundingInfo}; L69 json.dump({..., \"intervals\": {k: v ...}})",
   "pod2 r6_panel_splice.py cccc5b6b L59 SEP_IV = {...intervals...}; L82 rows.append((..., SEP_IV.get(s, np.nan))); L90 iv_full = np.where(np.isfinite(fiv), fiv, dv); L92 rate_nf = fr * (8.0 / iv_full)",
   f"{T}/pod_panel_splice.py a9c29141 L60-61 AUG_IV.get(s) on AUG rows, L71 iv_full = np.where(np.isfinite(fiv), fiv, dv); {T}/pod_panel_ext.py db7f0474 L66, L104-105; {C}/pod_export_bundle_v4.py L194, L219-220",
   "pod2 /workspace/fund_aug.json.gz: n_rates 827, n_intervals 0 (receipt); fund_pull_pod.py fa665810 L28 out = {\"rates\": rates, \"intervals\": {}}",
   "multi_asset/exports/research/uplift_r2_2026-09-13/T5d/PREREG_T5d_iv_corrected_replay_2026-09-13.md L14 (547 mismatching cells, 23 names, 60 extension rows); docs/HANDOFF_round4_review_request_2026-09-13.md L85",
   "~/wide_shadow/shadow_loop_v3.py L193-198: bundle EMA state used only when state/rolling.npz is absent",
 ],
 status="OPEN_NOT_MEASURED", affects=["future_eval", "future_retrain", "live_trading"], severity="P2",
 severity_reason="Recurrence depends on an unspecified puller; the affected quantities (fund leg, carry, FTRIM) dominate the book but only on the new month's rows; live exposure only on a cold bootstrap (INFERRED).",
 recommended_action=("Derive the interval of each settlement from the gap to the previous fundingTime (or the zip interval column) and never apply a pull-time interval to historical rows; add a gate that every recorded interval equals the rounded gap except at listed switches."),
 method="VERIFIED (mechanism in code, pod2 read-only); October recurrence INFERRED")

item(id="TRN-08", layer="DATA (feature sources)",
 title="(e) The metrics-archive label switch cannot be reintroduced today: no builder reads the metrics archive",
 what_is_wrong=("The chain's features come from the 5m kline cache (7 channels; taker-buy fraction from klines), the 4h panel and the targets. None of the builders reads data.binance.vision metrics (open interest, long/short ratios). "
   "The switch (label = window end up to 2024-03-03, window start from 2024-03-04) would matter only if OI features are added; the chain has no per-regime guard for that."),
 evidence=[
   f"grep metrics|open_interest|long_short|toptrader|premium: 0 hits in {T}/pod_dlw_features_ext.py, {T}/pod_f8_build_ext.py, {C}/pod_fea_ext_clamp.py, {C}/pod_dlw_targets_raw.py; their np.load/zload inputs are the cache, the panel, targets and fea82",
   "memory binance-metrics-archive-label-switch-2024-03-04 (L2 Stage A receipt RECEIPT_L2_A_switch.json, commit b50cef70)",
 ],
 status="VERIFIED_IMMATERIAL", status_resolution="0 metrics/OI inputs in the five chain builders; latent only.",
 affects=["future_retrain"], severity="P3", severity_reason="Latent until an OI feature is added (L2 is working on OI data).",
 recommended_action="If OI/metrics features are added: pick the label regime by date inside the builder and run an offset-spectrum check (peak at lag 0) per regime in the data stage before the STEP gates.",
 method="VERIFIED")

item(id="TRN-09", layer="DL (epoch rule)",
 title="(f) argmax is not reintroduced (FIX7 in folds and refit), but an October swap changes the live DL epoch rule without the forward shadow STATE requires",
 what_is_wrong=("Monthly folds and the refit both keep epoch 7. The live DL model was fitted with unconstrained argmax, so swapping in the October model changes the live recipe. STATE lists FIX7's deployment preconditions as a >=14-day forward shadow plus the user's word; the chain and the swap step have no shadow."),
 evidence=[
   f"{C}/launch_mwf_v4b.sh 07b2a602 L11 ... EMBARGO=1 MWF_TAG=mE1cX7 BEST_EP_FIX=7 ...; {C}/merge_mwf_v4b.py L30 assert C[\"best_epoch_rule\"] == RULE and C[\"best_epoch\"] == 7",
   f"{C}/chain_v4_monthly.sh L250 env ... BEST_EP_FIX=7 ...; L253 sidecar check best_ep_rule == 'fix7'; {C}/pod_f10_refit_v4.py L129 FIX rule",
   f"in-service {T}/pod_f10_refit_ext.py ea3675b8 L115-116 `if va > best_va:` (argmax)",
   "STATE.md (line ~207): 'FIX7 / FLOOR5 = 候选, 未部署。欠: 前向影子 ≥14 天 + 用户字'; memory live_dl_epoch_rule_is_unconstrained_argmax (FIX7 − CONST42 +0.267 [+0.083, +0.462])",
 ],
 status="PENDING_USER_DECISION", affects=["live_trading", "future_retrain"], severity="P2",
 severity_reason="Clean two-seed evidence for FIX7, but its stated deployment precondition is not part of the chain or the swap checklist.",
 recommended_action="Add the FIX7 forward shadow (or an explicit user waiver) to the swap checklist before any v4 DL model is swapped in.",
 method="VERIFIED")

item(id="TRN-10", layer="DL (gradient window)",
 title="(f) Under FIX7 the 15% validation slice selects nothing but still withholds ~260 days of the newest data from gradients",
 what_is_wrong=("The refit keeps `cut = 0.85` and trains only on tr1, while FIX7 no longer uses the validation curve. On the real September axis the refit's last loss label is 2025-12-16T20Z against a pool end of 2026-08-31T20Z (255 days). "
   "With 180 more anchors in October it would be 2026-01-09T20Z against 2026-09-30T20Z (260 days): a monthly retrain moves the DL gradient window by under a month. The monthly research folds use the same split."),
 evidence=[
   f"{C}/pod_f10_refit_v4.py 6c0666f4 L104 cut = int(len(tr_idx) * 0.85); tr1, va1 = tr_idx[:cut], tr_idx[cut:]; L111 starts = list(range(int(tr1[0]) + BURN, int(tr1[-1]) - WIN, STRIDE)); L140 _last_loss_idx",
   f"{C}/pod_f10_train_monthly_v4.py L329-330 (same split)",
   "pod2 read-only arithmetic on /workspace/dlw_v4raw/data/dlw_targets.npz (10212 anchors, 2022-01-03T00Z..2026-08-31T20Z, min 135 members): SEPT last_loss_label 2025-12-16T20:00Z; OCT(+180) 2026-01-09T20:00Z, pool end 2026-09-30T20:00Z, va1 259.8 days (receipts_train/pod2_readonly_receipt_2026-09-13T1312Z.txt)",
   "STATE.md (line ~208): X7FULL − FIX7 CI lower −0.212 vs δ 0.05 ('满窗梯度 = 不换装')",
 ],
 status="PENDING_USER_DECISION", affects=["live_trading", "future_retrain"], severity="P2",
 severity_reason="Tested alternative (full window) is undecided, so this needs a ruling rather than a code fix; but the monthly cadence does not do what its name suggests for the DL leg.",
 recommended_action="User ruling: keep 85/15 and state the lag in provenance, or preregister a fixed-length validation tail (memory: a 500-anchor tail recovers ~172 of 255 days).",
 method="VERIFIED (September arithmetic); October arithmetic assumes +180 anchors (INFERRED)")

item(id="TRN-11", layer="KING (training window)",
 title="(f/h) The king label-year cutoff is a literal `YRA < 2026`: monthly exports never advance it, now or in 2027",
 what_is_wrong=("Every export fits slow2026 on rows with label year < 2026. With an unchanged cache prefix October's training set equals September's, so October's booster is effectively September's; without a code change it will still stop at 2025 in 2027. "
   "The v4 exporter now records this honestly (king_train_end_utc)."),
 evidence=[
   f"{C}/pod_export_bundle_v4.py L63 tr = YRA < 2026; te = YRA == 2026; L64 _king_train_end; L263-266 king_train_rule / king_train_end_utc",
   "receipts/monthly_chain_2026-09-12/pod2_king_legs/export_v4.log: 'king training set: 2166009 rows / 8724 anchors, last training anchor 2025-12-31T20:00:00Z ... axis end 2026-08-31T20:00:00Z'",
   f"{T}/pod_export_bundle_v3.py c210bac6 L49 same rule (in-service booster 8d79186b)",
   "docs/PREREG_producer_parity_phase2_oos_2026-09-12.md L52 ('逐年折 SLOW_v4 的 fold Y 训练到 Y−1 年末'); memory king_retrain_cadence_axisA_2026_09_05 (UNDECIDED)",
 ],
 status="PENDING_USER_DECISION", affects=["live_trading", "future_retrain"], severity="P2",
 severity_reason="A design choice with undecided evidence, but hardcoded, so it cannot be changed by a monthly contract.",
 recommended_action="Make the king label cutoff a month-contract key (default = current value) so moving it is an explicit preregistered ruling, not a code edit.",
 method="VERIFIED")

item(id="TRN-12", layer="SWAP (seat)",
 title="(g) Seat seeding mixes calibers again: bundle king rows are v0-scored with the D20 mask while live rows are v1-served, and the seeding step is not in §0★",
 what_is_wrong=("The producer's seat is msharpe over the last 900 rows of bundle leg_returns + state rows. The seat-seed rule says every bundle swap re-seeds the king column from the new bundle's OOS rows. "
   "Those rows are scored by the exporter on v0 features with the D20 mask; rows appended live come from v1-served scores. The October bundle repeats this, and RUNBOOK §0★ step 8 does not mention seeding at all."),
 evidence=[
   "~/wide_shadow/shadow_loop_v3.py L223-226 self.LR = {leg: list(lr[leg]) + list(extra[leg])}; L237-239 n_keep = 950; L457-460 msharpe over st.LR[leg][-look:] (look 900)",
   f"{C}/pod_export_bundle_v4.py L114-127 leg returns from PRED (v0 features, D20 mask); L184 leg_returns.npz",
   "~/wide_shadow/state/leg_returns_live.json: 950 rows per leg (read-only count)",
   "memory seat_seed_v3_deployed_2026_09_05 ('每次换 bundle(月度重训)后, 状态文件的 king 列必须按同法播种'); T4b: re-scoring the 876 seeded rows with v1 moves the masked king seat +0.0078, combo target L1 0.0066",
   "docs/RUNBOOK_monthly_retrain_2026-10.md L23 (step 8: no seeding)",
 ],
 status="OPEN_NOT_MEASURED", affects=["live_trading"], severity="P3",
 severity_reason="Descriptive magnitude is small (T4b); mainly a missing procedure step.",
 recommended_action="Add seat seeding to the swap checklist; seed from rows scored on the serving caliber (or after the TRN-04 ruling) and record the seat before and after.",
 method="VERIFIED (code); book effect not measured")
