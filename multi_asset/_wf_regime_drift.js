export const meta = {
  name: 'regime-drift-feature-model-attack',
  description: 'Design + adversarially verify the best feature/model experiments to close the choppy y600 val->test concept-drift gap',
  phases: [
    { title: 'Design' },
    { title: 'Verify' },
    { title: 'Synthesize' },
  ],
}

// ---- Hard evidence injected into every agent (this session's measurements) ----
const DIAG = `
PROBLEM: single-asset BTC y_600 (10-min fwd return), ~120K-param REG_arch DL (RevIN + 64 hand LOB/flow feats via GDCN + raw 20-level book -> 2x Conformer d=32 -> FiLM(6-dim regime_prior) -> last-token -> monotonic 3-quantile head). Spot-book features (data/npz_spot). Strict time-series walk-forward.
GOAL: lift CHOPPY-regime y600 transfer IC toward 0.06. Choppy-SPECIALIZED DL gets OOS choppy-2026 IC=0.031 but choppy-2025 VAL=0.053; the val->test collapse is the problem.
*** DECISIVE BATTERY RESULT THIS SESSION (the central finding to build on) ***
On a cached multi-timescale feature representation = {last, mean, slope, std, firsthalf-minus-secondhalf} x 64 feats = 320 cols, train=choppy<=2025, test=choppy-2026 (the exact val->test gap):
- LINEAR Ridge on the 320 multi-agg cols, with HEAVY regularization, TRANSFERS at: lam30 +0.037, lam300 +0.042, lam1000 +0.044 (monotonic, clean) -- BEATS the DL's 0.031 by +0.013.
- last-ts-only (64) transfers at +0.015; multi-agg (320) is 2.4x more transferable. The transferable signal lives in the COMBINATION of many weak multi-timescale features.
- WALK-FORWARD over 19 CHOPPY months (decisive, corrects the 3-month artifact below): lin-multi-agg(lam1000) mean +0.026 / GBM(depth3) mean +0.029 / last-ts-linear mean +0.009. So NONLINEAR ~= or slightly > LINEAR across months (GBM wins 53% of months) -- nonlinearity is NOT a liability (the earlier GBM TEST +0.003 was a choppy-2026-SPECIFIC artifact). The ROBUST lever is MULTI-AGG >> last-ts (0.026/0.029 vs 0.009). All weak + high variance (std ~0.05-0.07, ~74% months positive). Choppy mean-IC ceiling ~0.026-0.029.
- linear V-REx (months as env): beta0 +0.031 -> beta5 -0.010, MONOTONICALLY destroys transfer. V-REx SCREENED OUT.
- transforms rank-gauss/sign/PCA-drop-top-k/stable-feature-subset ALL <= raw multi-agg (none beats it; magnitude matters, dropping top PCs hurts).
=> MECHANISM: the transferable choppy signal is the MULTI-TIMESCALE AGGREGATION of the features (NOT the snapshot, NOT a stable subset), it is WEAK + high-variance, and nonlinearity is fine. The DL pools by LAST-TOKEN ONLY -> it discards the very aggregations (mean/std/slope) that transfer. (DL nonlinearity ALSO pays big in TRENDING regimes 0.07-0.08 -- keep it.)
OTHER HARD DIAGNOSTICS: per-feature IC corr choppy25-vs-26 = +0.036, 0 features sign-stable across 28 months, domain-classifier AUC 0.89 (covariate shift), recency/online retraining HURTS (long all-history window best).
ADVERSARIAL CONFIRM (temper the headline): the +0.013 linear>DL edge is WITHIN noise -- choppy-2026 has only 3 months (2026-03 is -0.068), month-block bootstrap CI [-0.068,+0.113] includes 0, and the linear model ALSO collapses val->test (refit-excl-val: VAL 0.157 -> TEST 0.034). Robust parts: nonlinearity-fails-to-transfer (GBM 0.003 vs lin 0.044), heavy-reg-helps, multi-agg>>last-ts, V-REx-destroys. So treat linear-multi-agg as a TRANSFERABLE SIGNAL SOURCE to fold into the DL, NOT as a replacement.
*** USER HARD CONSTRAINT (overrides any 'use linear instead' conclusion) ***: DO NOT dismiss the DL. The DL has a LARGE, proven edge over linear/tree across MANY 2025 periods (trending regimes hit 0.07-0.08 where linear/GBM are far behind). The task is to INTEGRATE multi-agg (and other transferable-signal ideas) INTO the DL in a TARGETED way to improve the CHOPPY period, WITHOUT degrading the DL's trending-regime edge. Every proposal MUST be evaluated ALL-REGIME (trending + choppy), not choppy-only, and must show choppy-up without trending-down.
PROJECT ANTI-PATTERNS: #29 channel-addition penalty (-0.013/added channel unless >=+0.003 alpha; prefer REPLACE/skip-path over ADD); v3/v4/v6a/v8 NEG (added capacity = NEG); sigma-collapse (#20/#23/#24, sigma_yhat/sigma_y>=0.02 gate or no ckpt); regime-MoE failed 3x (so any regime mechanism must be a FIXED CAUSAL blend of frozen models, NOT a learned gate); rank-loss PRIMARY drifts. KEY DL DETAIL: REG_arch pools via LAST-TOKEN of the Conformer output (it has an encode() returning (B,32) pre-head embedding) -- last-token DISCARDS the mean/std/slope aggregations the battery showed are transferable. src/ + configs/ READ-ONLY (new files only in multi_asset/; can wrap/extend via encode()). Single RTX 3090, shared.
`

// Battery results (linear transfer screen) injected here before launch:
const BATTERY = args && args.battery ? args.battery : '(battery results not provided)'

const DESIGN_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['approach', 'mechanism', 'why_fits_this_drift', 'implementation', 'expected_dIC', 'prob_beats_baseline', 'cpu_pregate', 'risks', 'is_retread'],
  properties: {
    approach: { type: 'string', description: 'concise name of the proposed feature/model experiment' },
    mechanism: { type: 'string', description: '2-4 sentences: the causal mechanism by which it should help' },
    why_fits_this_drift: { type: 'string', description: 'why it specifically addresses THIS diagnostic (IC-corr 0.036 / AUC 0.89 / nonlinear-sequence-signal), not generic regularization' },
    implementation: { type: 'string', description: 'concrete: where in REG_arch/loss/dataset it goes, new-file-only, exact module/loss form, how to define environments if needed' },
    expected_dIC: { type: 'string', description: 'honest expected delta on choppy-2026 test IC vs 0.031 baseline, a range' },
    prob_beats_baseline: { type: 'number', description: '0-1 probability it beats the 0.031 baseline by a real margin' },
    cpu_pregate: { type: 'string', description: 'a cheap CPU/Ridge pre-gate to run BEFORE GPU, with a pass threshold' },
    risks: { type: 'string', description: 'failure modes esp. sigma-collapse / channel-penalty / retread of failed v-experiments' },
    is_retread: { type: 'boolean', description: 'true if this is substantially a re-test of something the project already falsified' },
  },
}
const VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['verdict', 'kill', 'reasoning', 'strongest_objection'],
  properties: {
    verdict: { type: 'string', enum: ['survives', 'weakened', 'killed'] },
    kill: { type: 'boolean', description: 'true if the diagnostics/anti-patterns make this dead-on-arrival' },
    reasoning: { type: 'string' },
    strongest_objection: { type: 'string', description: 'the single most damaging adversarial point' },
  },
}

const ANGLES = [
  { key: 'multiscale-pooling', mandate: 'REPLACE the DL last-token pooling with MULTI-SCALE pooling of the Conformer sequence output (concat last + mean + std + slope over time, maybe at 2-3 windows) before the head. Mechanism: last-token discards exactly the mean/std/slope aggregations the battery proved are the TRANSFERABLE choppy signal; giving the head the multi-scale pooled embedding folds that transferable signal into the DL natively. This is a REPLACE (not an added channel), respects #29. Specify exact wiring in a new multi_asset/ model that reuses the REG_arch backbone, param cost, and why it should not degrade the trending edge.' },
  { key: 'multiagg-skip-path', mandate: 'Add a heavily-regularized LINEAR skip-path: explicit multi-timescale aggregations {last,mean,slope,std,fmh}x64 of the INPUT features -> a zero-init linear residual added to the DL q50 head output. The DL keeps its nonlinear power; the skip injects the transfer-robust linear-multi-agg signal directly to the head, bypassing the Conformer. Specify: how to compute aggregations in the dataset/model (new file), strong L2 on the skip weights, zero-init so trending behavior is unchanged at start, and the all-regime eval. Contrast vs the failed v8 microprice-trajectory ADD (this is a REPLACE-of-information-path / residual, heavily regularized, with a Ridge-proven transferable signal -- v8 added unproven channels).' },
  { key: 'causal-regime-blend', mandate: 'A FIXED CAUSAL blend (NOT a learned gate -- regime-MoE failed 3x) of two FROZEN models: the existing DL (strong in trending) and a heavily-regularized linear-multi-agg model (transfer-robust in choppy). Weight = f(strictly-causal <=t trend-efficiency indicator, e.g. Kaufman ER over trailing window): DL-heavy when trending, linear-heavy when choppy. Goal: raise ALL-REGIME y600 IC. Specify the causal indicator, how to fit the blend weight without future leakage (#26), and the all-regime backtest. Address why a fixed causal blend escapes the learned-MoE failure.' },
  { key: 'choppy-robust-training', mandate: 'Keep the DL architecture but make its OWN mapping more transferable in choppy using the battery lessons (heavy reg is THE transfer lever; nonlinearity overfits the period). Propose the exact training regime: much higher weight_decay / dropout, smaller effective capacity or shorter training, possibly choppy-period upweighting in the loss, and/or a linear-dominant parameterization. It MUST preserve the trending-regime edge (eval all-regime). Give exact config deltas + the one ablation that proves choppy-up-without-trending-down.' },
]

phase('Design')
const designs = await parallel(ANGLES.map(a => () =>
  agent(
    `${DIAG}\n\nLINEAR TRANSFER BATTERY RESULTS (choppy-25 -> choppy-26 Ridge transfer screen):\n${BATTERY}\n\n` +
    `YOUR MANDATE (angle = ${a.key}): ${a.mandate}\n\n` +
    `Propose the SINGLE strongest concrete experiment in your angle to raise choppy-2026 test IC above 0.031. Be ruthlessly honest and specific; ground every claim in the diagnostics above. If your angle is mostly dead given the diagnostics, say so and propose the least-dead variant. Return the structured proposal.`,
    { label: `design:${a.key}`, phase: 'Design', schema: DESIGN_SCHEMA }
  ).then(d => ({ angle: a.key, design: d }))
))

phase('Verify')
const verified = await parallel(designs.filter(Boolean).map(d => () =>
  parallel([
    () => agent(`${DIAG}\n\nPROPOSAL (angle ${d.angle}): ${JSON.stringify(d.design)}\n\nYou are an ADVERSARIAL SKEPTIC. Try to KILL this proposal using ONLY the hard diagnostics and project anti-patterns above. Is it dead-on-arrival (e.g. relies on an invariant core that the 0-stable-features finding says does not exist; adds capacity where capacity is NEG; would sigma-collapse; re-treads a falsified v-experiment; needs predictable drift that recency-hurts refutes)? Default to skepticism. Return verdict.`, { label: `kill:${d.angle}:diag`, phase: 'Verify', schema: VERDICT_SCHEMA }),
    () => agent(`${DIAG}\n\nPROPOSAL (angle ${d.angle}): ${JSON.stringify(d.design)}\n\nYou are a skeptic focused on STATISTICAL REALITY: at R2<1% with ~89 test days, would the claimed gain survive day-block bootstrap / be distinguishable from seed variance? Is the expected_dIC honest vs the research prior (+0.000..+0.005)? Could it look good on val but drift on test? Return verdict.`, { label: `kill:${d.angle}:stat`, phase: 'Verify', schema: VERDICT_SCHEMA }),
  ]).then(vs => ({ ...d, verdicts: vs.filter(Boolean) }))
))

phase('Synthesize')
const judge = await agent(
  `${DIAG}\n\nLINEAR TRANSFER BATTERY:\n${BATTERY}\n\n` +
  `DESIGNS + ADVERSARIAL VERDICTS:\n${JSON.stringify(verified.filter(Boolean), null, 1)}\n\n` +
  `You are the final synthesizer. Given ALL evidence: (1) Rank the proposals by realistic expected value (EV = prob_beats_baseline * expected_dIC, penalized by retread/kill verdicts). (2) Pick the SINGLE next GPU experiment to run on the shared 3090, with an EXACT spec (config deltas, new-file plan, env definition if any, sigma-gate safeguard, patience, and the CPU pre-gate to run first with its pass threshold). (3) Give one fallback. (4) State the honest probability that the BEST surviving idea pushes choppy-2026 test IC from 0.031 to >=0.045, and to >=0.06. Be concrete and decisive; do not hedge into a survey. Return a structured plan.`,
  { label: 'synthesize', phase: 'Synthesize', schema: {
    type: 'object', additionalProperties: false,
    required: ['ranked', 'next_experiment', 'next_experiment_spec', 'cpu_pregate', 'fallback', 'p_reach_045', 'p_reach_060', 'bottom_line'],
    properties: {
      ranked: { type: 'array', items: { type: 'string' }, description: 'proposals ranked best->worst with one-line EV rationale each' },
      next_experiment: { type: 'string' },
      next_experiment_spec: { type: 'string', description: 'exact, runnable spec' },
      cpu_pregate: { type: 'string', description: 'the cheap pre-gate + pass threshold' },
      fallback: { type: 'string' },
      p_reach_045: { type: 'number' },
      p_reach_060: { type: 'number' },
      bottom_line: { type: 'string' },
    },
  } }
)

return { designs: designs.filter(Boolean), verified: verified.filter(Boolean), plan: judge }
