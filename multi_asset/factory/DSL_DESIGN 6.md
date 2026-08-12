# Factory step 1 — formula-DSL operator set + evaluation pipeline (DESIGN)

> **创建:** 2026-07-20 JST | **Session:** fable multi-asset-v2 (0B) | **状态:** design (review before build) | **作废条件:** 算子集/操作数/评估口径变更; 或 0C 预注册协议修订
> **审阅:** team-lead + 0C (泄漏面逐算子审 + 阈值预注册)

Design-only. Proposes the operator set, operands, formula representation, causal/leakage rules, and
the vectorized evaluation → ledger pipeline for systematic factor mining. **Nothing is built until this
is reviewed.** The goal is to discover factors that are **incremental over the shipped four-leg book**
(scored on the king+S2-orthogonalized residual target), under an anti-p-hacking, append-only,
pre-registered protocol — not to re-mine what the book already captures.

## 1. Scope & the anti-p-hacking frame

A formula is a small trailing-only expression tree over the panel. The factory batch-proposes formulas,
evaluates each with **walk-forward incremental rank-IC over YR4B/YR24B**, and appends every result
(pass or fail) to an immutable ledger. The multiple-testing exposure is controlled by (a) a
**pre-registered** operator set + acceptance thresholds frozen before any mining, (b) a **two-stage
multiple-testing gate** — Stage-0 batch Benjamini-Hochberg q=0.10 as pure compute-saving *triage* (not a
discovery claim), then Stage-1 survivors face a Reality-Check / Romano-Wolf step-down max-null **and** a
Bonferroni z=4.42 campaign gate whose denominator is the **cumulative ledger count M** (see
`factory_prereg.md §2.3`), so BH can never launder a discovery — (c) the **≤6 depth / ≤12 operator**
complexity cap (already in the 0C protocol) to bound the hypothesis space, and (d) the existing
**acceptance battery** gating any DL model built on discovered factors. A discovered factor is a candidate, not a result, until it clears the same
five-gate discipline (incremental IC + day-block CI + per-year sign + dyn-share + net-cost) the four
legs cleared.

## 2. Operands

**A. Wide-panel channels (32, causal ≤t)** — `wide_dl_full.npz` `CH`:
`funding_ema, mom_{4,8,24,72,168}h, rev_{1,3}h, rvol_{24,72,6}h, dvol_{24,72}h, beta_{24,72}h,
lturnover_24h, illiq_72h, size_dvol, max_ret_24h, gtja_046, a101_044, ret_{1,4,12,24}h, logqvol,
xsr_{rvol,ret24,fund,turn,mom72}, betaadj_ret24`.
Note: several channels are **already derived** (the `xsr_*` are cross-sectional pct-ranks; `mom/rev/rvol`
are window reductions). The factory earns credit only for **novel composition** on top of these — 0C
should treat e.g. `xsec_rank(rvol_24h)` as redundant with the existing `xsr_rvol`.

**B. Leg score columns (4) — the factory's unique expression space:**
`king` (4h residual-reversal OOS prediction), `s2` (24h slow), `funding_leg = rank(funding_ema)·(−1)`,
`size_leg = z(size_dvol)`. Formulas may **condition and combine on top of the legs** (e.g. "king where
BTC-vol is low, else S2", "funding-reversion gated by turnover") — an expression space the raw channels
alone cannot reach. Leakage caveat (0C): king/S2 are **OOS** predictions, so using them as operands is
leak-safe by construction; but any factor built on them is by nature **book-correlated**, so it must be
scored on the **king+S2-orthogonalized target** (§4) to earn incremental credit, not on raw YR.

**C. Constants:** small integer windows `{1,3,4,6,12,24,72}` (bars), scalar literals for thresholds.

## 3. Operator set (~20) — the audit table

All operators are **trailing-only** (no operator can reference `t+k`). Grouped by kind; each row is what
0C audits. Complexity cost feeds the ≤12-operator budget (temporal reductions cost more than pointwise).

| # | operator | signature | semantics | causal window | cost | leakage surface (0C audit) |
|---|---|---|---|---|---|---|
| **temporal (trailing reductions)** |
| 1 | `ts_delta` | (x, n) | x_t − x_{t−n} | [t−n, t] | 1 | must use x_{t−n}, never x_{t+n}; n≥1 |
| 2 | `ts_mean` | (x, n) | trailing mean over n | [t−n+1, t] | 1 | window ends at t inclusive; min-periods guard |
| 3 | `ts_std` | (x, n) | trailing std over n | [t−n+1, t] | 1 | same; std of a constant → 0 (guard div) |
| 4 | `ts_zscore` | (x, n) | (x_t − ts_mean)/ts_std | [t−n+1, t] | 2 | div-by-0 when trailing std=0 |
| 5 | `ema` | (x, span) | causal EMA (adjust=False) | (−∞, t] | 1 | recursive, strictly causal; NaN-propagation guard |
| 6 | `ts_rank` | (x, n) | rank of x_t within its trailing n | [t−n+1, t] | 2 | rank includes t but only over past-window values |
| 7 | `ts_corr` | (x, y, n) | trailing Pearson corr(x,y) over n | [t−n+1, t] | 3 | both series trailing; degenerate-variance → NaN |
| 8 | `ts_min`/`ts_max` | (x, n) | trailing extremum | [t−n+1, t] | 1 | trailing only |
| 9 | `decay_linear` | (x, n) | linearly-weighted trailing mean | [t−n+1, t] | 1 | weights on past only |
| **cross-sectional (per-anchor, same t)** |
| 10 | `xsec_rank` | (x) | pct-rank across coins at t | {t} | 1 | uses only same-anchor cross-section (member set) |
| 11 | `xsec_z` | (x) | (x − mean)/std across coins at t | {t} | 1 | same-anchor; std=0 guard |
| 12 | `xsec_demean` | (x) | x − cross-sectional mean at t | {t} | 1 | same-anchor |
| **pointwise (elementwise, at t)** |
| 13 | `add/sub/mul` | (a, b) | elementwise arithmetic | {t} | 1 | none (pointwise) |
| 14 | `div` | (a, b) | a / b with |b|<eps → NaN | {t} | 1 | div-by-0 guard (returns NaN, not inf) |
| 15 | `neg/abs/sign` | (x) | −x / \|x\| / sign(x) | {t} | 1 | none |
| 16 | `log1p_safe` | (x) | sign(x)·log(1+\|x\|) | {t} | 1 | domain-safe (no log of ≤0) |
| 17 | `power` | (x, p) | sign-preserving \|x\|^p | {t} | 1 | p∈{0.5,1,2}; overflow guard |
| **conditional (the leg-combination space)** |
| 18 | `where` | (cond, a, b) | a where cond>0 else b | {t} | 2 | cond must be trailing/pointwise (no future) |
| 19 | `gt`/`lt` | (a, b) | boolean mask a≷b | {t} | 1 | pointwise |
| 20 | `clip` | (x, lo, hi) | winsorize to [lo,hi] | {t} | 1 | pointwise |

**Deliberately excluded** (leakage-prone or redundant): any forward/centered window, any operator taking
`t+k`, group-by-future, and raw `log`/`div` without the domain/zero guards above.

## 4. Formula representation, caps, and target

- **Expression tree**: operator nodes + operand leaves (channel / leg column / constant). **Depth ≤ 6,
  operator count ≤ 12** (0C protocol). Trailing-only is enforced structurally — no node can index the
  future — so the tree is causal by construction.
- **Output** of a formula = a `(T, N)` factor array, causal ≤t.
- **Scoring target**: the **king+S2-orthogonalized residual** `YR4B` (4h) / `YR24B` (24h)
  (`yr4b_target.npz` / `yr24b_target.npz`). A factor's rank-IC vs YR4B **is** its incremental content
  over the shipped book — the deployment gate, measured directly. (Raw `YR` and `Yraw` are reported too,
  per the dual-caliber rule, but acceptance is on the orthogonalized target.)

## 5. Evaluation pipeline (vectorized batch)

```
formula (string / tree)
  └─ parse  ->  validate (depth≤6, ops≤12, trailing-only, operand whitelist)
  └─ vectorized eval over CH/legs  ->  factor (T,N)  [each operator = one numpy/pandas vector op]
  └─ score on the CLEAN CL{H} non-overlap grid, member-masked:
       per-anchor rank-IC(factor_t, YR{H}B_t)  ->  pooled + per-year
       + day-block bootstrap CI (3000x, block=day)
       + per-year sign consistency
       + shuffle-future dynamic share (static-tilt guard)
       + turnover / net-cost break-even (is it tradeable?)
       + pred-corr vs the four legs (novelty, not redundancy)
  └─ leakage screen: shuffle-future null (IC→0) + forward-window-decay signature (peak lag0)
  └─ ledger append (immutable)
```
Fully vectorized: a batch of formulas is evaluated over the same `(T,N)` arrays; the per-anchor rank-IC
and bootstrap reuse the acceptance-battery primitives already written (`comp_panel`/`ricorr`/dayblock).
CPU-bound, no GPU. Walk-forward = the same expanding-year folds the book uses.

## 6. Ledger (append-only) schema

One row per evaluated formula (**pass or fail — failures are the p-hacking audit trail**):
`id · timestamp · formula_str · tree_depth · op_count · operands_used · target(YR4B|YR24B) ·
ic_pooled · ic_ci95 · ic_by_year · sign_consistent · dyn_share · turnover · be_bps · predcorr_king ·
predcorr_s2 · predcorr_funding · predcorr_size · leak_shuffle_null · leak_fwd_decay · fdr_q ·
verdict(REJECT|CANDIDATE|ACCEPT) · reject_reason`. Immutable + content-hashed; the batch's FDR is
computed over all rows in the batch (not cherry-picked survivors).

## 7. Proposal loop protocol

```
propose (batch of K formulas, agent-generated within the operator/operand/cap grammar)
   -> evaluate (§5, vectorized) -> ledger (§6, all K rows) -> FDR over the batch
   -> failure archive re-feed: the ledger's REJECT rows (and their reasons) are fed back so the
      proposer does not re-propose failed forms / known-redundant compositions (pred-corr≈1 to a leg
      or to an existing channel). Survivors that clear FDR + the five gates -> CANDIDATE -> the
      acceptance battery (if promoted into a DL model) -> ACCEPT only if it clears the same battery.
```
Pre-registration (0C, before mining): freeze the operator set (this table), the caps, the scoring
target, the acceptance thresholds, and the FDR level. Any change to those = a new pre-registration doc.

## Open questions for review

1. **Leg-operand novelty gate**: what pred-corr-to-a-leg ceiling marks a formula "redundant" (I propose
   the same 0.7 book-corr rule the arms used)?
2. **FDR level** for a batch of K (I propose Benjamini-Hochberg q=0.10; 0C to freeze)?
3. **Batch size K** per round (affects the FDR denominator — larger K = stricter correction)?
4. Whether the `xsr_*` channels should be **removed from the operand set** (they are already
   cross-sectional ranks) to force the DSL to express cross-section explicitly via `xsec_rank`, or
   kept as convenient primitives (I lean: keep raw factors, drop the pre-ranked `xsr_*` to avoid
   trivially-redundant proposals).
