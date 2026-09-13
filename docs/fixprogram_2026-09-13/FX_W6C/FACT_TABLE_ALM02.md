> **创建:** 2026-09-13 16:0xZ | **Session:** FX-W6C (https://claude.ai/code/session_01HLaR7r1Tyg5CoEsNgnNFkY) | **状态:** 事实表(ALM-02), 代码提交 933e7c5 于克隆 fix/exe01-proportional-response; 未部署 | **作废条件:** watchdog.py cond2 块改动

# FACT TABLE — ALM-02: §4-2 `judged_on` hard-codes 2026-09-06

| # | Fact | Where | Consequence |
|---|---|---|---|
| A1 | `detail["cond2_day_loss"]["judged_on"] = "most recent priced day (2026-09-06); worst_day_pct is history"` — a literal | ef60f85 `live/watchdog.py:1302` | the record names a day that was not judged |
| A2 | Live `state/live/watchdog/last_eval.json` at 2026-09-13T12:46:53Z: `recent_day 20260913`, `recent_day_pct −0.1807`, `worst_day_pct −4.2755`, `judged_on "…(2026-09-06)…"` | snapshot copy (14:19:50Z) | VERIFIED stale on the running tree |
| A3 | Twin, same block: `triggers.append(f"§4-2 single-day loss {worst:.2f}% …")` while `hit = recent < DAY_LOSS_LIMIT_PCT` | ef60f85 `live/watchdog.py:1354` vs L1280 | when an older worse day stays in the window, the trigger prints another day's number; with A2's live window a new −4.05% trip would print −4.28% (09-06) into the trigger, `trip_page`, ALARM.log, `state.json` reason and every protective_flatten row's `note` |
| A4 | Readers: `grep "single-day loss|judged_on"` over live/ ops/ scheduler/ — only watchdog.py itself and a print in tests_watchdog; `run_anchor.py:613–618` builds its own line from `recent_day_pct` | grep | no parser in this repo depends on the text; `~/guard_twin` (outside the repo) NOT CHECKED |
| A5 | Same family as research commit 74b2acb5 (a written date/fact that expires) | ERROR/audit text | — |

**Fix (933e7c5):** `_recent_day_txt` rendered from `recent_day` (YYYY-MM-DD; None ⇒ "no priced day in the window (blind)");
`judged_on` uses it; the trigger prints `recent` and names its day. Thresholds, judged quantity and blind logic unchanged.

**Red → green:** `live/tests_cond2_judged_text.py` — ef60f85 **0/6 rc=1** (cell 1 trigger "−5.00%" for a −4.105% trip; judged_on
literal; cells 2–4 no day named; cell 5 source) → 933e7c5 **6/6 rc=0**. Neighbours: worst == recent; quiet window; no priced day.
Adjacent suites rc 0: tests_watchdog, tests_threshold_roles, tests_trip_page, tests_proportional_response; `ops/gate_coverage.py`
rc 0 (137 suites). Receipts `receipts/alm02_*`. Battery: with the flow-day item (next), after 16:50Z.
