> **创建:** 2026-09-12 | **状态:** FROZEN BEFORE ANY NULL NUMBER EXISTS | **修订对象:** prereg `bbedfdaa…` + AMENDMENT 1 `6207572a…` + AMENDMENT 2 `abfcc850…`

# PREREG AMENDMENT 3 — TWO NULLS, DECLARED BEFORE THEY ARE RUN. THEY MAY ONLY WIDEN THE
# UNCERTAINTY OF THE RULING, NEVER NARROW IT.

## Why

The AMENDMENT-2 run produced, on the **randomised** placement arm (`placement_bandit.assign`,
sha1(rebalance_id:symbol) last byte < 128, eps=0.50), `drift_intent` of **join −7.7574
CI95 [−18.1223, −0.1554]** vs **behind +3.3603 CI95 [+0.2337, +5.9691]**.

The arm is assigned AFTER the target is formed and changes only the limit price. It cannot move the
price path over `[E, E+25m]`, which is the entirety of `drift_intent`. **The true difference between
those two arms is zero by construction.** An 11.1 bps split with both CIs excluding zero is therefore
either chance or evidence that the UTC-day block bootstrap understates the true sampling variation of
this statistic. That must be settled before any ruling quotes a CI.

## N1 — RANDOMISED-ARM NULL (zero by construction)

Statistic: `D = wmean(drift_intent | join) − wmean(drift_intent | behind)` on ERA2, attempt-1,
non-exempt rows. Null distribution: **2000 re-randomisations using the venue's own assignment
function**, `sha1(f"{salt}:{rebalance_id}:{symbol}")` last byte < 128, salt = 0..1999. This is the
exact randomisation scheme, so the null is exact, not approximate.
Reported: observed `D`, the null's sd and its [2.5, 97.5] percentiles, and the two-sided percentile
of `|D|` in the null. **If |D| sits inside the null's central 95%, the split is chance and the
day-block CI on each arm alone is not to be read as a significance statement for a difference.**
Independently, the null's sd IS the honest resolution of a within-anchor contrast on this statistic
and will be quoted as such.

## N2 — RELAB NULL FOR THE LEVEL (the desk's own null family)

`SHIFT` is the wrong family here: `drift` is a within-anchor cross-sectional quantity and the
disputed object is the matching between a name's trade sign and that same name's next-25-minute
return — a NAME-IDENTITY object. The desk's own rule (BACKTEST_METHOD §4, r13b) is that for
name-identity objects the informative family is **RELAB**, not SHIFT.

RELAB_d: one fixed permutation of the 829-name axis per draw, `default_rng([4242, d])`, applied to
every anchor identically; each order row keeps its sign and notional but is paired with the drift of
the permuted name AT THE SAME ANCHOR. This destroys name matching while preserving (a) the sign and
notional structure exactly, (b) the anchor's cross-sectional return distribution exactly, and
(c) all time-series structure. d = 1..200.
Reported: the null's mean, sd and [2.5,97.5] percentiles of the notional-weighted drift, and the
percentile of the observed value.

## N3 — FILL-RATE ACCOUNTING (declared here, arithmetic only, no inference)

Total filled notional by attempt and order_type divided by attempt-1 intended notional, ERA2,
excluding `protective_flatten` from the numerator's steady-state reading (it is stop-loss/watchdog
traffic, per `mk_costb.py` `maker_share_excludes`). This is reported because the replay books 100%
of `Δw` while the desk books this share, and because the cheapness of the maker fill price and the
incompleteness of the fill are two halves of the same selection.

## Binding constraint on the ruling

Neither null may be used to strengthen a claim. If N1 shows the day-block CI is too narrow, the
ruling's uncertainty widens to the null's scale. If N2 shows the observed level sits inside the
RELAB null, the level is reported as **not distinguishable from no name-matching at all**.
K rises to 13 + 3 = **16**.
