> **创建:** 2026-09-13 16:1xZ | **Session:** FX-W6C (https://claude.ai/code/session_01HLaR7r1Tyg5CoEsNgnNFkY) | **状态:** 事实表(M2-33 flow-day), 代码提交 3f85c0e 于克隆 fix/exe01-proportional-response; 未部署 | **作废条件:** watchdog.py cond2 块改动, 或 B32 划转日口径被裁定改变

# FACT TABLE — M2-33: a transfer on a resume day re-trips §4-2 on a stale day

## Q1 How does the watchdog decide a flow day? (VERIFIED, ef60f85)
Measured, not text or date: `live/watchdog.py:1103–1105` `_flow_day = any(abs(float(r.get("external_flow_usdt") or 0.0)) > 1e-9 for r in nav)`
over the day's `daily_nav` rows. A flow day (and a `realised_truncated` day, L1106) appends `None` to `per_day_loss`
(L1110–1112, named in `flow_days` / `truncated_days`) — the B32 caliber ("nav delta is not P&L on a transfer day"). The
hard-coded text fixed in research commit 74b2acb5 was in `pilot_journal/tools/flowday_daylossguard.py`, not the executor.

## Q2 What does a transfer on a resume day do today? (VERIFIED by test on ef60f85)
L1252 `_recent_i` = the most recent day with a non-None loss, no staleness bound. `live/tests_cond2_stale_day.py` [1] on
ef60f85: day 2 at −4.20% (the trip day), day 3 a +5,000 transfer ⇒ `recent_day 20260912`, `recent_day_pct −4.2`,
**`triggered True`** — §4-2 trips again on the old day. [2] the same with a truncated income ledger instead: tripped.
Consequences (HEALTHCHECK_pre_resume_2026-09-06 §8.2, read in code then; measured now): before a resume the gate refuses;
after a resume the next anchor's watchdog runs the whole-book ladder again.

## Q3 STA-01 vs M2-33
STA-01 (AUDIT_EXEC): "a transfer today would not re-trip" — its fallback day was 09-12 at +0.22% (`daily_nav` 117,779.56 vs
117,515.79). Same mechanism, a window whose fallback day was positive: **no contradiction**; STA-01 is true for 09-13 and
false after any losing trip day. Cell [3] reproduces STA-01's window.

## Ledger facts (snapshot copy 14:19:50Z, measured)
- 8 transfer days in 44 pilot_log days (08-01, 08-02, 08-05, 08-10, 08-18, 08-27, 09-03, 09-08).
- `external_flow_usdt` on a row is cumulative since 00:00Z (09-03: two flow rows sum 125,995.62; last row ≈ 62,998 fits the nav change); summing rows double counts.
- Candidate transfer-day calibers, both computable and **not implemented** (a caliber decision): §4-4's P&L rule (realised + Δunrealised)/nav_prev gives 09-03 −0.51%, 09-08 −0.72%, 08-27 −0.42%; (nav − nav_prev − last-row flow)/nav_prev gives 09-03 ≈ −0.65%. On ordinary days the P&L rule differs from the nav change by ≈0.1 pp (09-06: −4.175% vs −4.275%).

## Fix (3f85c0e) and why this direction
cond2 judges the **latest day that carries equity rows**; if it is unpriced (transfer / truncated / terms missing) `recent`
is None ⇒ **BLIND**, with `latest_equity_day`, `latest_equity_day_unpriced_reason`, `last_priced_day(_pct)` named and
`judged_on` saying so. A day with no equity rows is skipped as before. The B32 caliber is unchanged.
- Rule 09-12 (instrument doubt never triggers a book-level response): today's day cannot be priced by our own record ⇒ no
  verdict from an older day. Blind is not a trigger.
- Safety: blind is loud (run_anchor pages blind once the clock has started) and the resume gate refuses on blind, so a
  transfer day cannot be a resume day — the operating rule becomes a gate.
- Cost: on every transfer day cond2 is blind for that day (and resume waits a day). Pricing transfer days would remove that;
  it is a caliber choice for the user (two candidates above).

## Red → green
`live/tests_cond2_stale_day.py` 7 cells — ef60f85 **3/7 rc=1** (cells 1, 1-why, 2, 3 red for the defect; controls 4–6 green) →
3f85c0e **7/7 rc=0**. Neighbours: truncated instead of transfer; STA-01's positive window; ordinary −0.5% / −4.5% latest day;
a newer day without equity rows. Adjacent suites rc 0 on 3f85c0e: tests_cond2_judged_text 6/6, tests_watchdog,
tests_threshold_roles 16 (pinned lines kept verbatim), tests_guard_calibers (B32 naming cells), tests_numerator_honesty 18,
tests_trip_page, tests_proportional_response; `ops/gate_coverage.py` rc 0 (138 suites). Battery: after 16:50Z on the tip.
