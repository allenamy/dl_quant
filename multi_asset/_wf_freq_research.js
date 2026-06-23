export const meta = {
  name: 'freq-domain-nonstationary-research',
  description: 'Deep research on frequency-domain / spectral-decomposition + latest 2024-2026 non-stationary TS forecasting methods for the choppy-regime y600 bottleneck',
  phases: [{ title: 'Survey' }, { title: 'Assess' }, { title: 'Synthesize' }],
}

const DIAG = `
SETTING: single-asset BTC y_600 (10-min fwd return), ~120K-param REG_arch DL (RevIN + 64 hand LOB/flow feats via GDCN + raw 20-level book -> 2x Conformer d=32 -> FiLM(regime_prior) -> last-token -> monotonic 3-quantile head). Spot-book features, 1s bars, 600-step windows. Strict time-series walk-forward. R^2<1%, Pearson IC 0.03-0.08.
PROBLEM: choppy-regime IC (~0.03) << trending-regime IC (0.07-0.08). The choppy val->test gap is the bottleneck.
HARD DIAGNOSTICS THIS SESSION (do NOT contradict; assess every method against these):
- The drift is CONCEPT DRIFT: per-feature->return linear IC structure between two choppy periods has corr only +0.036, 18 top features SIGN-FLIP, 0 features sign-stable across 28 months, month-to-month IC-vector corr mean +0.04..+0.18 (min -0.4..-0.7). P(y|X) itself reorganizes month to month. There is ALSO covariate shift (domain-classifier AUC 0.89).
- Oracle (fresh fit on the choppy-2026 test period) reaches ~0.087, but transfer from prior data gives only 0.032 => the signal EXISTS on test; the barrier is non-transferability of the MAPPING, not signal absence.
- EMPIRICALLY TESTED + SUBSUMED BY THE DL (each tested as: standalone walk-forward transfer AND residual-on-frozen-DL): multi-timescale aggregation (helps weak linear 0.009->0.026 but DL already captures it, residual on DL = -0.016); adaptive/causal normalization = SAN/Dish-TS essence (helps weak models a LOT: linear 0.002->0.025, GBM 0.013->0.026, variance halved -- BUT head-to-head DL 0.033 > causal-GBM 0.026 > causal-linear 0.022; DL SUBSUMES it, residual on DL = -0.009). NONLINEAR GBM ~= linear over 19 choppy months. V-REx invariant-training MONOTONICALLY DESTROYS transfer. recency/online retraining HURTS.
- CRYPTO PERIODICITY CAVEAT: BTC 1s/10-min returns have weak/no stable dominant frequency; project already found session/time2vec features NET-NEGATIVE (24/7 market). So any method whose gain relies on STABLE SEASONALITY/PERIODICITY is suspect here.
- PROJECT ANTI-PATTERNS: #29 channel-addition penalty (-0.013/added channel unless >=+0.003 alpha; prefer REPLACE/plug-in over ADD); added capacity has been NEG (v3/v4/v6a/v8); sigma-collapse if output-shrinking/L2-like loss dominates (sigma_yhat/sigma_y>=0.02 gate); src/ + configs/ READ-ONLY (new files only). Single RTX 3090.
KEY QUESTION for every method: does it address CONCEPT DRIFT (P(y|X) reorganizing) -- the actual barrier -- or only periodic-structure / covariate-shift, which crypto may lack and the DL already subsumes? Be brutally honest; the prior from this session is that input-side transforms get subsumed by the DL.
`

const SURVEY = [
  { key: 'fft-decomposition', q: 'FFT / frequency-domain time-series forecasting that DECOMPOSES into trend + periodic + noise via spectral transform: FreTS, FEDformer, FiLM(freq), Autoformer, FITS, FilterNet, frequency-enhanced MLPs, time-frequency dual-domain architectures, residual frequency-band reconstruction for abrupt-signal sensitivity, FFT-based spectral sparsification for efficiency. Find the strongest 2-3 (2023-2026, ICLR/NeurIPS), exact mechanism, and whether the trend/noise spectral separation could help SEPARATE the transferable trend signal from the non-stationary noise in choppy crypto y600.' },
  { key: 'iclr26-spectral-routing', q: 'Find the ICLR 2026 paper on "Routing Channel-Patch Dependencies in Time Series Forecasting with Spectral Decomposition" (channel-patch modeling unit, graph spectral decomposition, SHARED GRAPH FOURIER BASIS mapping signal to frequency domain, spectral-energy response auto-distinguishing low/mid/high frequency = period-trend / random-volatility / abrupt-anomaly, plug-in to DLinear/TimesNet/etc WITHOUT changing backbone, minimal compute). Extract the EXACT mechanism (the graph Fourier basis, the energy-routing), and assess: as a no-backbone-change plug-in that auto-separates regime frequency content, could it help the choppy/trending regime discrimination? Use web/OpenReview search.' },
  { key: 'timepre-sin-mcl', q: 'Find the TimePre paper: Stabilized Instance Normalization (SIN) + Multiple Choice Learning (MCL) combining linear-model efficiency with distribution flexibility for efficient/accurate/STABLE forecasting. Extract exactly how SIN differs from RevIN and how MCL (multiple hypotheses) provides distributional flexibility. Assess: does SIN address the covariate shift better than RevIN, and does MCL multi-hypothesis help when P(y|X) is multimodal/regime-switching? Use web search.' },
  { key: 'latest-nonstat-2024-2026', q: 'Latest 2024-2026 ICLR/NeurIPS/ICML papers on NON-STATIONARY / regime-switching / distribution-shift time-series forecasting NOT in {RevIN, SAN, Dish-TS, FAN, Non-stationary Transformer, V-REx, IRM} (already covered). Specifically methods that target P(y|X) CONCEPT DRIFT (not just P(x) covariate shift): e.g. learned decomposition, koopman/spectral operators, frequency-domain regime detection, test-time spectral adaptation, mixture-of-frequency-experts. Find the 2-3 most relevant, mechanism, and honest applicability to R^2<1% crypto with concept drift.' },
  { key: 'spectral-for-regime-concept-drift', q: 'Conceptual + literature: can FREQUENCY-DOMAIN / spectral analysis address CONCEPT DRIFT specifically (a feature->target relationship that reorganizes over time), or is spectral decomposition fundamentally a tool for COVARIATE/periodic structure? Is there evidence that spectral energy distribution is a more STATIONARY regime descriptor than time-domain stats (so a model conditioned on spectral-regime transfers better across choppy periods)? Find any papers using spectral features for regime classification / concept-drift detection in finance, and judge whether spectral-regime-conditioning would survive the IC-corr-0.036 / DL-subsumes findings.' },
]

const SURVEY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['methods', 'addresses_concept_drift', 'periodicity_dependence', 'expected_dIC', 'cpu_pregate', 'retread_risk', 'verdict', 'sources'],
  properties: {
    methods: { type: 'string', description: 'the 1-3 concrete methods/papers found, each with its EXACT mechanism in 2-3 sentences' },
    addresses_concept_drift: { type: 'string', description: 'honest: does it attack P(y|X) reorganization (the barrier), or only periodic/covariate structure? why' },
    periodicity_dependence: { type: 'string', description: 'does its gain depend on stable seasonality/periodicity (which crypto lacks)? how much' },
    expected_dIC: { type: 'string', description: 'honest expected delta on choppy-2026 test IC vs 0.033 DL baseline, a range' },
    cpu_pregate: { type: 'string', description: 'a cheap CPU/Ridge spectral-feature pre-gate to run BEFORE GPU, with pass threshold, analogous to the multi-agg/causal-norm residual-on-DL tests' },
    retread_risk: { type: 'string', description: 'is this likely subsumed by the DL like multi-agg/adaptive-norm were? why or why not' },
    verdict: { type: 'string', enum: ['worth-pregate', 'low-priority', 'dead-on-arrival'] },
    sources: { type: 'string', description: 'inline source URLs' },
  },
}
const ASSESS_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['survives', 'kill_reason', 'strongest_point', 'would_DL_subsume'],
  properties: {
    survives: { type: 'boolean' },
    kill_reason: { type: 'string', description: 'the most damaging objection from the diagnostics (concept-drift / crypto-no-periodicity / DL-subsumes / channel-penalty / sigma-collapse)' },
    strongest_point: { type: 'string', description: 'the strongest reason it might genuinely help despite the diagnostics' },
    would_DL_subsume: { type: 'string', description: 'specifically: would the existing RevIN+Conformer+GDCN already capture this signal (like it did multi-agg + adaptive-norm)? evidence-based judgment' },
  },
}

phase('Survey')
const surveyed = await parallel(SURVEY.map(s => () =>
  agent(`${DIAG}\n\nRESEARCH TASK (${s.key}): ${s.q}\n\nUse web search / OpenReview to ground this in REAL current papers (2023-2026). Be specific and honest; the session prior is that input-side transforms get subsumed by the DL, so the bar is high. Return the structured survey.`,
    { label: `survey:${s.key}`, phase: 'Survey', schema: SURVEY_SCHEMA }
  ).then(r => ({ key: s.key, survey: r }))
))

phase('Assess')
const assessed = await parallel(surveyed.filter(Boolean).map(s => () =>
  agent(`${DIAG}\n\nSURVEY RESULT (${s.key}): ${JSON.stringify(s.survey)}\n\nYou are an ADVERSARIAL SKEPTIC grounded in the hard diagnostics. The session has ALREADY shown the DL subsumes multi-agg AND adaptive/causal normalization (both helped weak models but the DL beat them and residual-on-DL was negative). Judge whether THIS spectral/frequency method would meet the same fate, or whether it genuinely attacks concept drift / provides a more-stationary regime descriptor the DL lacks. Default to skepticism; require a concrete mechanism for why the DL would NOT already capture it. Return verdict.`,
    { label: `assess:${s.key}`, phase: 'Assess', schema: ASSESS_SCHEMA }
  ).then(v => ({ ...s, assess: v }))
))

phase('Synthesize')
const fft = args && args.fft_result ? args.fft_result : '(empirical FFT/spectral pre-gate result not yet provided)'
const plan = await agent(
  `${DIAG}\n\nEMPIRICAL FFT/SPECTRAL PRE-GATE (my own test this session, spectral band-energy/entropy/centropy features):\n${fft}\n\nSURVEYS + ADVERSARIAL ASSESSMENTS:\n${JSON.stringify(assessed.filter(Boolean), null, 1)}\n\n` +
  `Synthesize. Integrate the EMPIRICAL spectral pre-gate result with the literature. (1) Rank the spectral/frequency methods by realistic EV for the choppy concept-drift bottleneck. (2) State plainly whether ANY frequency-domain method is likely to beat the DL's 0.033 choppy ceiling, given (a) the empirical pre-gate, (b) crypto's weak periodicity, (c) the DL-subsumes pattern, (d) that the barrier is concept drift not covariate/periodic. (3) If something IS worth trying, give the single best with exact CPU pre-gate + GPU spec + honest probability. (4) If not, say so decisively and explain why frequency-domain doesn't fix concept drift. Honest p(any spectral method -> choppy-2026 >= 0.045) and (>= 0.06).`,
  { label: 'synthesize', phase: 'Synthesize', schema: {
    type: 'object', additionalProperties: false,
    required: ['ranked', 'will_freq_beat_DL', 'best_to_try', 'best_spec', 'p_reach_045', 'p_reach_060', 'bottom_line'],
    properties: {
      ranked: { type: 'array', items: { type: 'string' } },
      will_freq_beat_DL: { type: 'string', description: 'plain yes/no/unlikely + why' },
      best_to_try: { type: 'string' },
      best_spec: { type: 'string', description: 'exact CPU pre-gate + GPU spec if worth it, else "none"' },
      p_reach_045: { type: 'number' },
      p_reach_060: { type: 'number' },
      bottom_line: { type: 'string' },
    },
  } }
)
return { surveyed: surveyed.filter(Boolean), assessed: assessed.filter(Boolean), plan }
