> **创建:** 2026-09-13 15:1xZ | **Session:** aud-exec | **状态:** PAUSED(lead 令: 账号额度) | **作废条件:** lead 重启消息

# X-COST / CFG-04 / CFG-06 — pause state

## Done (all committed, explicit pathspec)
| sha | what |
|---|---|
| 3eea1906 | device 0 `devices/x_cost_schema_census.py` (committed before run) |
| 55aa2d3b | device 1 `devices/x_cost_decompose.py` (sha256 bf41270f…, frozen decomposition) + census receipt |
| bcb3c0d5 | run-1 receipts + amendment A1 `devices/x_cost_amend_a1.py` (committed before run; fixes halted-anchor denominators in D9 ratios) |
| fdee4894 | A1 receipts, `devices/x_cost_render.py`, `receipts/x_cost_tables.md`, **`RESULT_X_COST.md`** (part A complete, reported to lead) |
| 977962a4 | **`DRAFT_AMENDMENT_chase_restart_population_2026-09-13.md`** (part B) and **`DRAFT_PREREG_placement_eps050_reread_2026-09-13.md`** (part C); both DRAFT, reported to lead |

## In progress
Nothing. No monitors, sleeps or background jobs are running. There is no uncommitted work in `X_COST/`.

## Next step (on restart)
1. Wait for the lead's review of both drafts. The lead needs to decide:
   - **B §5:** rebuild-anchor randomisation (options a/b/c).
   - **B gap G1:** X-N2b stopgap via the anchor_runs.log `untradable_held.reduced` field, plus a request to E4/R2′.
   - **C D1/D2/D3:** the undecided default (0.35 vs 0.50), window 28 vs 14 days, and whether "stop behind" means eps 0 or 0.10.
   - **C §0:** freeze-time attestation that no placement arm outcome after 09-05 12Z has been computed.
2. Apply the lead's edits, if any. The lead freezes.
3. Part A carries no open action. Optional follow-up if the lead wants it: attribute the rise in the first-attempt −5022 rate (14.3% → 23.0% of plans), cost-side and pooled only.
