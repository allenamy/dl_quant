> **创建:** 2026-09-28 13:31 UTC | **Session:** Codex root / acting-lead-20260927 | **状态:** in-progress | **作废条件:** 源、输入、公式或评价窗变更；非发布批准

# Causal peer linkage implementation plan

> **For agentic workers:** Implement inline with superpowers:executing-plans. No new agents. User authorized independent research; no new live behavior.

**Goal:** Test whether peer price/flow/funding context contributes information beyond the NC model inputs.
**Architecture:** Pure time-indexed relationship estimator, then eight causal features, then a separately versioned data adapter/Ridge screen. Real cash continuation/readout remains the immediate priority. Do not train a large network without signal evidence.
**Tech Stack:** Python/NumPy, no new dependencies, one CPU thread.
**Spec:** docs/DESIGN_cross_section_linkage_features_2026-09-28.md

## Global constraints

60 calendar days / 360 completed 4h observations strictly before the daily graph time; minimum240 pairwise valid rows; positive residual-correlation top16 peers, minimum8; same-date legal population, no self. Daily graph frozen until next midnight. Missing observations remain unknown. Existing frozen NC source/data identities, raw unclipped price and real funding intervals. No venue API, live write, blind arm outcomes or automatic resume.

## Review focus

Future mutation must not change the graph/features. Missing/young names cannot silently become zero. Reordered names yield equivalent named peers. Current population changes must remove stale peers without selecting future replacements. Regression normalization and coefficients may use only prior completed training labels.

## Task 1: pure peer graph and eight-column transformation

Files: multi_asset/exports/research/acting_lead_2026-09-27/devices/linkage_20260928/peer_features.py and test_peer_features.py.

- [x] Tests first: time cutoff/future poison, duplicate/time gaps, unknowns, constant returns, self-exclusion, permutation, stale graph, missing peers.
- [x] Implement fit_graph(ts, returns, legal, symbols, graph_ts) with causal leave-one-out market beta/residual covariance. Do not claim correlation is lag causation.
- [x] Implement transform(graph, anchor_ts, current vectors). Columns: standardized peer residual4h/24h, own-minus-peer residual24h, peer positive breadth, peer flow-change minus own, peer volume anomaly minus own, negativefund8h×peer residual4h, currentfund8h-minus-EMA8h. Feature-specific peer coverage>=8; report coverage. No post-hoc feature clipping.
- [x] Run tests; commit source and results. No economic claim from synthetic tests.

## Task 2: versioned real-panel adapter and incremental screen

- [ ] Bind original+extended price metadata, member axes, legal states, funding units and NC prediction identity. Strict 49 endpoint observability; do not use UA held valuation as a genuine return.
- [ ] Materialize features on historical legal members. Graph fitting excludes current bar; raw current signals use only closed bars. Save sources/parameters/axis hashes and missing counts.
- [ ] Freeze ridge monthly-fold contract before labels/metrics; baseline existing scores plus own price/flow/funding controls, candidate adds peer columns. RecentH2 primary descriptive, September explicit; already viewed windows are exploratory. Separate train cutoff/purge, use train-only normalization; include raw Pearson/Spearman and existing-model conditional residual metrics.
- [ ] No grid. Null future shuffle, graph scrambling/own-feature controls, coverage equality. Cross-regime/year results required before whole-book candidate. Price and carry labels separate; fees and stateful final portfolio must still be evaluated for promotion.

Task2 is not started by this plan; its runtime/data contract must be written after input inventory. Do not claim a new model exists until predictions and whole-book readout exist.

## Ruling and progress 2026-09-28 14:03 UTC

Price-family first: four of eight columns materialized with actual historical data; flow/funding unit adapters remain pending. This is an implementation order change before any peer signal number, not dropping a losing feature family. Contract PREREG_peer_price_incremental_screen_2026-09-28.md freezes monthly Ridge; first family running under 16-minute cap. Task2 overall incomplete until outcomes, input archive, controls and coverage are reviewed. No new strategy release.

## First family completion and next brief (2026-09-28 14:12 UTC)

Panel and 39-month Ridge complete. Source 512612a04/2cebd2edd; independent 83741 checks (30b7b89fd). Weak positive incremental rank-IC across all periods, recent +.001911; failed frozen .005 and calibrated sigma .02 gates. No GPU expansion of this family or retuning its graph parameters. Full archive verified177members/156models b0b23c72. Core8-column design remains partially implemented.

Next: funding/flow interaction adapter. Before any metric, verify clean NC funding `acc` unit from actual update code and actual interval fields; do not infer EMA unit from a name or multiply EMA by current interval. Baseline must include individual normalized funding (`fund8`, `ema8`), individual buy-flow and volume states, so a plain difference of existing columns is not mislabeled peer alpha. Test only predeclared peer interactions beyond these own-name controls. Old/current funding snapshots and symbol/member axes must bind. Flow comes from actual channel definitions, unknown volume/buy-flow never zero. Preserve price-family result; new variant needs own contract and matched all-population fallback. Do not spend GPU on a direct implementation of the known HOLD escape or a failed same-feature grid.

## Flow/funding family completion (2026-09-28 14:43 UTC)

Three new interaction columns materialized under D10 data and as-of policy. Fund-now minus EMA is an existing own-name linear combination, so it is a control, not a purported ninth signal. Before outcomes, added own negativefund×own return interaction to isolate peer contribution. 42 engineering controls, 96 direct-window checks; 39×4 Ridge complete, independent83559 arithmetic/fold checks. Three of seven gates pass; recent rankIC −.000284, no GPU escalation or deployment. All184 archive members verified locally b663156a.

Task2 adapter/population/train screen/missing fallback/period reporting complete for this bounded price-label diagnostic. Still NOT completed: distinct carry/net label screen, incremental comparison conditional on actual King/F10 frozen scores, cash cost coverage or a whole-book candidate. Do not claim the whole multi-stage design is certified. Previous weak price-family increment unchanged. Next permitted independent diagnosis: align already stored baselines to distinguish changed population/cutoff/input/control count before claiming an own-control effect; freeze any new experiment before fitting. No graph/window tuning of failed families.
