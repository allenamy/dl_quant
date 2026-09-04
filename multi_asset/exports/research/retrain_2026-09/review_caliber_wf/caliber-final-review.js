export const meta = {
  name: 'caliber-final-review',
  description: 'Independent multi-agent trace + adversarial refutation of the return-caliber truth, then a complete correct-caliber evaluation of the live strategy',
  phases: [
    { title: 'Trace', detail: 'six independent code+data tracers' },
    { title: 'Refute', detail: 'adversarial refuters per key claim' },
    { title: 'Synthesize', detail: 'complete evaluation document' },
    { title: 'Critique', detail: 'completeness critic + gap fill' },
  ],
}

const SCRATCH = '/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber'

const COMMON = `
GROUND RULES (non-negotiable):
- Live trading systems are READ-ONLY: never modify, restart, kill, or write under ~/wide_shadow, ~/dl_quant_live, or /workspace/data, /workspace/shadow_bundle_v3, /workspace/f8_* on the pod. Do not touch launchd jobs. Do not run GPU jobs.
- Write scratch files only under ${SCRATCH}/<your-label>/ on the Mac, or /workspace/review_scratch/<your-label>/ on the pod (ssh alias: pod2; python: /workspace/venv/bin/python, numpy 2.4, no scipy unless you pip install it in the venv). The research server alias 'jpline' is DOWN today: try it at most once with ConnectTimeout=8 and then do not rely on it.
- Definitions come ONLY from executed code lines and from empirical bitwise checks on data. Comments, docstrings, variable names, markdown docs, memory files, and prior conclusions are NOT evidence of a definition; you may cite them only to show what people BELIEVED.
- Every claim you make must carry a receipt: absolute file path + line number + the quoted line, or a command + its printed output. Mark each finding as VERIFIED (you executed it / read the executing line) or INFERRED.
- Prefer shell (bash, python3, grep -n, git -C <repo> log/show) with absolute paths. One repo per git command.
- Do not print secrets (API keys, tokens). If you encounter one, report only that it exists and where.
KEY LOCATIONS:
- Research repo (git, branch multi-asset-v2): /Users/haosiyu/Desktop/quant_research  — docs/ (ERROR_LEDGER_2026-08-20.md, RESULT_caliber_revalidation_2026-09-04.md, RESULT_caliber_truth_2026-09-04.md, RUNBOOK_monthly_retrain_2026-10.md, MILESTONE_2026-08-26.md, CLAUDE.md), multi_asset/exports/research/retrain_2026-09/ (w10_universe.py = replay device copy; pod_*.py, jp_*.py probes), multi_asset/exports/eda/ (older devices incl. kcurve_2026-08-15/, kcurve_2026-08-21/devices_2026-08-22/inrole_simple_return_rerun.py, RESULT_inrole_simple_return_2026-08-22.md), multi_asset/data/build_wide_dl.py, engine/panel_source.py, engine/replay_fullhist.py.
- Memory files: /Users/haosiyu/.claude/projects/-Users-haosiyu-Desktop-quant-research/memory/*.md (index MEMORY.md).
- Old session transcript (768 MB JSONL, grep-able, do NOT load whole): /Users/haosiyu/.claude/projects/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f.jsonl
- Live producer (Mac, read-only): /Users/haosiyu/wide_shadow/shadow_loop_v3.py, /Users/haosiyu/wide_shadow/fea171/combo_stage.py, cache /Users/haosiyu/wide_shadow/state/rolling.npz (keys ts, data[T,829,7] float16; channel 0 is the per-5-minute return; ~40 days), bundle /Users/haosiyu/wide_shadow/shadow_bundle/ (leg_returns.npz with ts/king/rev24/fund; config.json has symbols_panel), state /Users/haosiyu/wide_shadow/state/leg_returns_live.json, target weights /Users/haosiyu/wide_shadow/state/target_live/<anchor>.json.
- Executor (Mac, git, read-only): /Users/haosiyu/dl_quant_live (scheduler/anchor_loop.py, live/*.py), logs /Users/haosiyu/dl_quant_live/state/live/pilot_log/<YYYYMMDD>/{orders,fills,anchors,daily_nav,funding,position_readback}.jsonl
- Pod (ssh pod2): /workspace/data/wide_panel_4h_v1.npz, wide_panel_4h_v2ext.npz, wide_panel_4h_v3splice.npz (keys ts, symbols, Y4, f_*), /workspace/data/wide_fea_v2ext_meta.npz (E_ts, members, y4, qvk, names), /workspace/data/dlw_targets.npz (E_ts, E_row, members, y4s, y4old, YR4s, YRZ, symbols, meta_json), /workspace/data/dlnative_5m_wide829_f16_ext.npz (ts, symbols, ch, data[T,829,7] float16; channel 0 = 5-minute return; 2022-01-01→2026-09-01), scripts /workspace/pod_dlw_targets_ext.py, /workspace/pod_export_bundle_v3.py, /workspace/pod_f10_train_ext.py (and any /workspace/*.py that builds panels: find them), /workspace/port_w10/ (a port of the replay device with outputs in probe_artifacts/*.npz and REPORT.md).
`

const TRACE_SCHEMA = {
  type: 'object',
  properties: {
    component: { type: 'string' },
    definition: { type: 'string', description: 'The exact mathematical definition of the 4h return quantity used by this component, as established from executed code' },
    caliber: { type: 'string', enum: ['sum_of_simple_5m', 'log_return', 'compound_simple', 'other', 'unknown'] },
    evidence: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'integer' }, quote: { type: 'string' }, status: { type: 'string', enum: ['VERIFIED', 'INFERRED'] } }, required: ['file', 'quote', 'status'] } },
    empirical_checks: { type: 'array', items: { type: 'object', properties: { method: { type: 'string' }, command_or_script: { type: 'string' }, result: { type: 'string' }, passed: { type: 'boolean' } }, required: ['method', 'result', 'passed'] } },
    transforms_applied_downstream: { type: 'string', description: 'Any expm1/log1p/exp/log applied to this quantity later in this component, with file:line' },
    confidence: { type: 'number' },
    caveats: { type: 'string' },
    scratch_dir: { type: 'string' },
  },
  required: ['component', 'definition', 'caliber', 'evidence', 'empirical_checks', 'confidence'],
}

const TRACERS = [
  { key: 'pod_panels', prompt: `TASK: Determine, from the code that PRODUCES them and from bitwise empirical checks, the exact definition of the Y4 target in the pod panels /workspace/data/wide_panel_4h_v1.npz, wide_panel_4h_v2ext.npz, wide_panel_4h_v3splice.npz and of y4 in /workspace/data/wide_fea_v2ext_meta.npz. Steps: (1) find the builder scripts on the pod (search /workspace/*.py and the research repo for the script that writes these files; grep for 'Y4' assignments and np.savez calls); quote the executing lines. (2) Empirically test at least 30 anchors spread over 2022–2026 against the 5-minute data (dlnative_5m_wide829_f16_ext.npz): compute for each symbol three candidates over BOTH window conventions (rows [E, E+47] and [E+1, E+48], where E is the 5-minute row whose ts equals the anchor ts): Σ r5, Σ log1p(r5), Π(1+r5)−1; report median |Δ| and share < 1e-6 versus the panel Y4 for each candidate and window. State which candidate matches bitwise. (3) Also determine what channel 0 of the 5-minute file is (simple c/prev−1 or log) from its builder code. Do not reuse any existing probe scripts; write your own. ${COMMON}` },
  { key: 'dl_targets_and_models', prompt: `TASK: Determine from executed code which return quantity each MODEL is trained on. (a) F10 / V2MAIN DL: read /workspace/pod_dlw_targets_ext.py (how y4s and y4old are computed, which is saved) and /workspace/pod_f10_train_ext.py and any related training script (grep for dlw_targets, y4s, YR4s, YRZ, target) to establish which array is the training target / loss input; quote lines. (b) King LGBM: read /workspace/pod_export_bundle_v3.py and any king training script it calls/mirrors (grep rankdata, y4, YRZ, label) to establish the label definition; state whether a cross-sectional rank is invariant to monotone transforms of y4 and whether that matters. (c) Empirically confirm y4s == Π(1+r5)−1 and y4old == Σ r5 on ≥20 anchors using dlw E_row and the 5-minute data. Report caliber for each model's target. ${COMMON}` },
  { key: 'live_pipeline', prompt: `TASK: Trace the return caliber through the LIVE pipeline on the Mac, read-only. (1) /Users/haosiyu/wide_shadow/shadow_loop_v3.py: how channel 0 of the cache is computed from venue klines (quote the line), how the per-anchor 4h return y4v is formed, how leg returns are appended to state/leg_returns_live.json, how seats (msharpe) are computed from them, and whether any expm1/log1p/log appears on that path. (2) /Users/haosiyu/wide_shadow/fea171/combo_stage.py: does it use returns at all for decisions? (3) /Users/haosiyu/dl_quant_live: how realized P&L, stops (per_name_stop, d30 layer), and NAV are computed — from venue prices/positions (simple accounting) or from panel returns? Quote lines. (4) Empirically: pick the last completed anchor, recompute the appended leg-return row from the cache and the previous anchor's positions (state/aux.json prev_rec has legz/members; note aux.json is overwritten each anchor, so use the row that matches) OR, if the previous prev_rec is unavailable, verify on the bundle: recompute /Users/haosiyu/wide_shadow/shadow_bundle/leg_returns.npz king/fund for anchors inside the cache window from the bundle's inputs if possible; otherwise state what could not be recomputed. Report the caliber of the live seat history and of live P&L accounting. ${COMMON}` },
  { key: 'replay_device_history', prompt: `TASK: Build a dated, commit-anchored history of the return transform used by the wide-book replay devices, and identify exactly which panel each device consumed. Work in /Users/haosiyu/Desktop/quant_research with git -C. (1) For multi_asset/exports/research/retrain_2026-09/w10_universe.py: quote the CAL handling lines (env parsing, every expm1/log branch in legs() and run()), and what file it loads y4 from. (2) git log -S'expm1' --oneline (and -S'CAL') over multi_asset/exports/eda and multi_asset/exports/research to find when expm1 entered the wide-book devices; for each hit, record commit hash, date, file, and quote the added lines (git show <hash> -- <file> | grep -n expm1). (3) Identify the ancestor devices (kcurve_2026-08-15/pod_kcurve*.py, kcurve_2026-08-21/devices_2026-08-22/*.py incl. inrole_simple_return_rerun.py and conclusion_reaudit*.py, and engine/replay_fullhist.py + multi_asset/data/build_wide_dl.py + engine/panel_source.py): for each, which panel file it reads (quote the path constant) and whether its y is log or Σ-simple according to that panel's builder. (4) Produce a timeline table: date | commit | device | panel consumed | y definition in that panel | transform applied | correct? (correct = transform matches the panel's definition). Also record what the docs/ERROR_LEDGER and CLAUDE.md Metric Discipline line say and when they were written (git log for the line). ${COMMON}` },
  { key: 'exporter_and_bundle', prompt: `TASK: Establish the caliber of the seat-history series that feeds the live msharpe seats. (1) On the pod read /workspace/pod_export_bundle_v3.py: quote the lines that compute leg_returns (the LR loop) and what y4 they use; quote the training split lines (which years the production king booster is trained on, which years' predictions are in-sample vs out-of-sample); state whether the 2026 rows of slow_pred_pinned.npy are out-of-sample. (2) On the Mac compare /Users/haosiyu/wide_shadow/shadow_bundle/leg_returns.npz against an independent recomputation for anchors that overlap the local cache /Users/haosiyu/wide_shadow/state/rolling.npz (about 40 days): you will need per-anchor king/fund scores; if the bundle lacks them, instead verify the bundle's caliber indirectly by regressing/aligning the bundle fund leg with a Σ-simple vs expm1(Σ-simple) recomputation using the producer's own leg definition (xz rank → demean → unit gross) with f_fund_ema from the pod panel for the same anchors (ship a small slice). If a bitwise match is impossible, say so and give the best discriminating statistic. (3) Report: caliber of bundle leg_returns, caliber of producer-appended rows, whether they are consistent with each other, and whether the state file /Users/haosiyu/wide_shadow/state/leg_returns_live.json (sha256 prefix) currently equals the pre-2026-09-04 backup /Users/haosiyu/wide_shadow/state/leg_returns_live.json.pre_seatfix_20260904. ${COMMON}` },
  { key: 'money_truth', prompt: `TASK: Establish ground truth from exchange money and from the pod's true-compounded target, independent of any replay device. (1) On the pod, using /workspace/data/dlw_targets.npz (y4s = compounded simple by its own code — verify the line) and /workspace/shadow_bundle_v3/slow_pred_pinned.npy (production king predictions; rows aligned to /workspace/data/wide_fea_v2ext_meta.npz E_ts; 2022–2023 rows are NaN), compute the king leg return per anchor with the standard leg definition (cross-sectional rank of prediction over members → subtract mean → scale to unit gross → Σ w·y) under FOUR calibers: y4old (Σ simple), y4s (compounded simple), expm1(y4old), log1p(y4s). Report yearly means 2024/2025/2026 and the Sharpe/anchor over the last 900 anchors. Do the same for the fund leg using f_fund_ema_v1 from wide_panel_4h_v2ext.npz (align by ts). Write your own script; do not reuse existing ones. (2) On the Mac, read-only: reconcile the live book for 2026-08-26→now: for each anchor with a target_live file and the next anchor present, paper return = Σ w·R / Σ|w| where R is the compounded simple 4h return from the cache channel 0 over (anchor, anchor+4h]; venue twin = Σ position_qty·(mid_next − mid) / realized_gross using pilot_log position_readback and anchors.jsonl mid_at_anchor_vector; funding from funding.jsonl. Report means in bps/anchor, correlation paper vs twin, and daily sums vs daily_nav equity deltas net of external_flow_usdt. (3) State which caliber the exchange itself pays (positions × price change) and therefore which of the four calibers is the money caliber, and how far Σ-simple is from it (mean and std of the difference). ${COMMON}` },
]

const CLAIMS = [
  { id: 'C1', text: 'The Y4 target in ALL pod-built wide panels (wide_panel_4h_v1.npz, wide_panel_4h_v2ext.npz, wide_panel_4h_v3splice.npz) and y4 in wide_fea_v2ext_meta.npz equals the SUM of simple 5-minute returns over the old window rows [E, E+47] (bitwise), and is NOT a log return and NOT a compounded simple return.', votes: 3 },
  { id: 'C2', text: 'The replay device w10_universe.py (research repo copy) with CAL=simple applies np.expm1 to that Y4 (in legs() and run()), which adds a spurious convexity term of order σ²/2 per name; CAL=log leaves Y4 raw, which is an unbiased proxy of exchange (compounded simple) accounting to within ~0.05 bps/anchor at the leg level. Therefore every wide-book replay number produced under CAL=simple since mid-August 2026 is biased: model legs (king, F10) understated by 2–3 bps/anchor and the fund leg overstated by ~0.3–0.9 bps/anchor in 2025–26.', votes: 3 },
  { id: 'C3', text: 'The bundle exporter (/workspace/pod_export_bundle_v3.py) computes leg_returns from raw y4 (Σ-simple) and the live producer (/Users/haosiyu/wide_shadow/shadow_loop_v3.py) appends leg returns as Σ of simple 5-minute returns (c/prev−1); these two are on the same caliber, so the live king seat ≈0.21 was a legitimate msharpe output. The 2026-09-04 08:53Z replacement of state/leg_returns_live.json with an expm1-caliber OOS seed was wrong, and the 11:46Z restore of the pre-swap file was correct. The 2026 rows of the production king predictions are out-of-sample (booster trained on years < 2026).', votes: 2 },
  { id: 'C4', text: 'The F10/V2MAIN DL model is trained on y4s = Π(1+r5)−1 (compounded simple) and the king LGBM label is a cross-sectional rank of y4 (rank is invariant to monotone transforms), so neither model is affected by the caliber defect; only replay evaluation and seat-history calibers were affected.', votes: 2 },
  { id: 'C5', text: 'The 2026-08-22 re-audit (inrole_simple_return_rerun.py / RESULT_inrole_simple_return_2026-08-22.md) that established the expm1 rule was analysing a DIFFERENT panel family (wide_dl.npz built by multi_asset/data/build_wide_dl.py whose Y is a true forward log return: logc[H:]−logc[:-H]); the rule was correct for that panel and became wrong when carried by name onto the pod-built panels used by the w10 replay devices. The 08-22 receipt R3 (per-anchor correlation ≥0.99 and median |Δ| <1 bps versus an independent 1h cube) could not discriminate log-sum from Σ-simple.', votes: 2 },
  { id: 'C6', text: 'Under the correct caliber (raw Y4 = Σ-simple), the pod-ported replay (/workspace/port_w10/, arm d30_n2_c42, column net_ex in bps per anchor per unit NAV of a book whose gross is gross_total≈0.6–0.85) gives for the live form (MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero): fixed seats 0.21/0/0.79 → 2024 −0.642, 2025 +0.284, 2026(→08-30) +2.378, 2024→26 +0.457 (Sharpe 1.02, max drawdown 2614 bps); dynamic msharpe seats → 2024 +0.149, 2025 +0.359, 2026 +2.013, 2024→26 +0.691 (Sharpe 1.88); the old CAL=simple caliber gave 2024→26 +1.473 (3.14) and +1.597 (4.00) respectively; T3c (KMOD_F10=0.5) is negative vs base for both F10 seeds (2024→26 Δ −0.033 and −0.022); isolated M1+T400, FTRIM, T400 arms are within ±0.04 of canon. Converting: per-gross = net_ex/gross_total; annual % = bps/anchor × 2190 / 100; at 2× gross multiply per-gross annual % by 2.', votes: 3 },
]

const REFUTE_SCHEMA = {
  type: 'object',
  properties: {
    claim_id: { type: 'string' },
    refuted: { type: 'boolean', description: 'true if you found evidence the claim is false or materially overstated; default to true if you could not verify the key facts yourself' },
    verified_parts: { type: 'array', items: { type: 'string' } },
    refuted_or_unverified_parts: { type: 'array', items: { type: 'string' } },
    evidence: { type: 'array', items: { type: 'object', properties: { file_or_command: { type: 'string' }, line: { type: 'integer' }, quote_or_output: { type: 'string' } }, required: ['file_or_command', 'quote_or_output'] } },
    corrected_statement: { type: 'string', description: 'If refuted or overstated, the corrected statement with numbers' },
    confidence: { type: 'number' },
    scratch_dir: { type: 'string' },
  },
  required: ['claim_id', 'refuted', 'verified_parts', 'refuted_or_unverified_parts', 'evidence', 'confidence'],
}

const LENSES = [
  'CODE-READING lens: refute by reading the executing code paths line by line (not comments); find any branch, default, env flag, alignment, or normalization that would make the claim false.',
  'EMPIRICAL-DATA lens: refute by recomputing the numbers yourself from the raw arrays (panels, 5-minute data, npz outputs, pilot logs) with your own script; treat any published number you cannot reproduce within stated tolerance as refuted.',
  'HISTORY-AND-CONFOUNDER lens: refute by checking git history, file timestamps, panel versions, symbol alignment, window conventions, float16 rounding, NaN handling, and whether a different but plausible definition would also match the evidence; look for the alternative explanation.',
]

function refuterPrompt(claim, lens, idx) {
  return `You are an adversarial reviewer. Your job is to REFUTE the following claim about a live trading research pipeline. Default to refuted=true if you cannot personally verify the load-bearing facts. Do not accept any prior document, memory, or prior analysis as proof; only code you read and computations you run count. ${lens}

CLAIM ${claim.id}: ${claim.text}

Deliver: which parts you verified (with receipts), which parts you refute or could not verify (with receipts), and if refuted/overstated, the corrected statement with numbers. Keep scratch under ${SCRATCH}/refute_${claim.id}_${idx}/ (Mac) or /workspace/review_scratch/refute_${claim.id}_${idx}/ (pod). ${COMMON}`
}

phase('Trace')
log('Launching 6 independent tracers and adversarial refuters in parallel (blind to each other)')
const traceThunks = TRACERS.map(t => () => agent(t.prompt, { label: `trace:${t.key}`, phase: 'Trace', schema: TRACE_SCHEMA }))
const refuteThunks = CLAIMS.flatMap(c => Array.from({ length: c.votes }, (_, i) => () =>
  agent(refuterPrompt(c, LENSES[i % LENSES.length], i), { label: `refute:${c.id}#${i}`, phase: 'Refute', schema: REFUTE_SCHEMA })
    .then(v => ({ ...(v || { claim_id: c.id, refuted: true, verified_parts: [], refuted_or_unverified_parts: ['agent returned null'], evidence: [], confidence: 0 }), lens: i % LENSES.length }))))
const results = await parallel([...traceThunks, ...refuteThunks])
const traces = results.slice(0, TRACERS.length).filter(Boolean)
const refutes = results.slice(TRACERS.length).filter(Boolean)
const tally = CLAIMS.map(c => {
  const vs = refutes.filter(r => r.claim_id === c.id)
  const nRef = vs.filter(r => r.refuted).length
  return { id: c.id, votes: vs.length, refuted_votes: nRef, survives: vs.length > 0 && nRef * 2 < vs.length }
})
log('Tally: ' + tally.map(t => `${t.id} ${t.refuted_votes}/${t.votes} refuted → ${t.survives ? 'SURVIVES' : 'DOES NOT SURVIVE'}`).join(' | '))

phase('Synthesize')
const synthPrompt = `You are the synthesis writer. Using ONLY the JSON evidence below (tracer findings and adversarial refutation votes), write a complete, plain-language evaluation document in Chinese (technical terms may stay English), saved to ${SCRATCH}/REVIEW_caliber_final_draft.md and returned as your final text. Rules: every number carries its source (file:line or command); label each conclusion VERIFIED / INFERRED / UNRESOLVED; where refuters disagree with tracers, present both and state which receipt wins and why; never resolve a disagreement by preference. Required sections: 1) 一句话真相 (what the panel Y4 is, what is right/wrong in each component); 2) 逐组件口径表 (panel builders, DL target, king label, exporter, producer, executor, replay device: definition | caliber | transform | verdict | receipt); 3) 时间线 (dated commits: when each rule entered, which panel it applied to, whether correct there); 4) 六条论断的证伪投票结果 with the strongest refutation evidence per claim and the corrected statements; 5) 正确口径下的完整评估 (yearly 2024/2025/2026 tables for fixed-seat and dynamic-seat live forms, both calibers side by side, units chain shown explicitly: bps/anchor per NAV-book → per gross → annual % → 2× NAV; worst month; drawdown; T3c; M1/FTRIM/T400) — include ONLY numbers that were reproduced or verified by at least one refuter/tracer, and mark single-instrument numbers (pod port) as such since the second server is down; 6) 真钱对账 (live reconciliation numbers with receipts); 7) 仍未解决/单仪器/待复核 list; 8) 规则 (how to prevent recurrence, tied to concrete files). Do not invent numbers. If something was not verified by anyone, say so.

TRACERS JSON:
${JSON.stringify(traces, null, 1)}

REFUTATIONS JSON:
${JSON.stringify(refutes, null, 1)}

TALLY:
${JSON.stringify(tally)}
${COMMON}`
const synthesis = await agent(synthPrompt, { label: 'synthesis', phase: 'Synthesize' })

phase('Critique')
const critic = await agent(`You are the completeness critic. Read the draft at ${SCRATCH}/REVIEW_caliber_final_draft.md (the same text is below). Your job: find what is MISSING, UNVERIFIED, or INTERNALLY INCONSISTENT — a caliber not traced, a number without a receipt, a unit conversion error (check every bps→% and per-NAV→per-gross step numerically), a claim marked VERIFIED that rests on a comment or a doc, a conflict between sections, a component of the live pipeline (producer, combo_stage, executor stops/NAV, dashboard, tests) not covered, missing negative years, missing σ_fund-tercile breakdown, missing 2022–2023 (state why unavailable), reliance on the down server. Return a numbered list of gaps, each with severity (blocking / important / minor) and a concrete instruction for a follow-up agent to close it (what to compute or read, where). Then list the top 3 residual risks that could still flip the conclusion. Keep your own scratch under ${SCRATCH}/critic/.

DRAFT:
${synthesis}
${COMMON}`, { label: 'critic', phase: 'Critique', schema: { type: 'object', properties: { gaps: { type: 'array', items: { type: 'object', properties: { n: { type: 'integer' }, severity: { type: 'string', enum: ['blocking', 'important', 'minor'] }, description: { type: 'string' }, instruction: { type: 'string' } }, required: ['n', 'severity', 'description', 'instruction'] } }, residual_risks: { type: 'array', items: { type: 'string' } } }, required: ['gaps', 'residual_risks'] } })

const toFill = (critic?.gaps || []).filter(g => g.severity !== 'minor').slice(0, 6)
log(`Critic found ${critic?.gaps?.length || 0} gaps; filling ${toFill.length} blocking/important ones`)
const fills = await parallel(toFill.map(g => () => agent(`Close this gap in a caliber review. GAP #${g.n} (${g.severity}): ${g.description}
INSTRUCTION: ${g.instruction}
Deliver: what you computed/read, receipts (file:line or command+output), the resulting numbers or facts, and a VERIFIED/INFERRED/UNRESOLVED label. Scratch under ${SCRATCH}/gap_${g.n}/ (Mac) or /workspace/review_scratch/gap_${g.n}/ (pod). ${COMMON}`, { label: `gap:${g.n}`, phase: 'Critique' })))

const finalDoc = await agent(`Produce the FINAL version of the review document by integrating the gap-fill results into the draft. Save to ${SCRATCH}/REVIEW_caliber_final.md and return the full text. Keep every receipt; update labels (VERIFIED/INFERRED/UNRESOLVED) according to the fills; add a section "缺口审查与补证" listing each gap, its fill result, and any gap still open; add the critic's residual risks verbatim under "残余风险". Do not soften or embellish; no new numbers without receipts.

DRAFT:
${synthesis}

GAP FILLS:
${fills.filter(Boolean).map((f, i) => `--- GAP ${toFill[i]?.n} ---\n${f}`).join('\n\n')}

RESIDUAL RISKS FROM CRITIC:
${JSON.stringify(critic?.residual_risks || [])}
${COMMON}`, { label: 'final-doc', phase: 'Critique' })

return { tally, gaps: critic?.gaps || [], residual_risks: critic?.residual_risks || [], final_path: `${SCRATCH}/REVIEW_caliber_final.md`, final_len: (finalDoc || '').length }