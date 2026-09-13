> **创建:** 2026-09-13 15:3xZ | **Session:** FX-EXEC2 (teammate of team-lead) | **状态:** 暂停(lead 令: 账号额度; 无实盘安全紧急项) | **作废条件:** 恢复工作后由 REPORT_FX_EXEC2.md 取代

# FX-EXEC2 · pause state

## Where the work lives
- Executor clone `/Users/haosiyu/cc_tmp/fx_exec2`, branch main, base `ef60f85`, head **`c2e9bdc`** (tree `8becaf4b`). No `.env`. Its `state/` is a copy of live state taken 14:27:00–06Z without `acceptance/`; guarded SHA256SUMS are in the session scratchpad. Nothing was written to `~/dl_quant_live`, `~/wide_shadow` or `~/guard_twin`.
- Old-code worktree for red runs: `/Users/haosiyu/cc_tmp/fx_exec2_old` (detached at ef60f85, `state` symlinked to the clone's state; the new test files are copied in, untracked).
- guard_twin copy: `/Users/haosiyu/cc_tmp/fx_exec2_guard_twin` (guard_twin.py `0b299781`, income.jsonl `ffbb1102`, 109,545 rows).
- Partial stacked diff: `receipts/fx_exec2_partial_ef60f85_c2e9bdc.diff`, sha256 `a8354619cfd3b923f547c32b7c25d77c68e7a9c83e5f37fbc27bdcc8dbdb71c6`, 30 files, +2529/−89. Checked with `git apply --cached` on an ef60f85 index, which reproduces tree `8becaf4b` exactly.
- Fact table: `FACT_TABLE_EXEC2.md`. Fixture builders: `devices/build_fixture_led0{2,7,8}.py`.

## Done (committed in the clone, each with red on old code and green on new, no crash)
| Item | Commit | New suite: green on c2e9bdc | Red on ef60f85 |
|---|---|---|---|
| LED-02 flatten exit cost (vs mid_at_submit, fee from fills ledger) + score_post_fix key + daily_summary section | `c46fb83` | tests_flatten_exit_cost 29/29 | 9/28, 19 FAIL (`LED02_red_old_ef60f85.log`) |
| LED-07 `pilot_log.anchor_series` | `7ca52ac` | tests_anchor_series 17/17 | 3/10, 7 FAIL |
| LED-08 anchor_report pure builder, cost_buckets, trailing-band warnings | `469c3f3` | tests_anchor_report_builder 17/17 | 5/12, 7 FAIL |
| STA-02 cooldown expiry is tier B (alarm_policy rule) + tests_alarm_digest later-demotion exemption | `8354c5a` | tests_pns_expiry_tier 8/8 | 6/8, 2 FAIL |
| ALM-01 funding_span fingerprint, text and tier by book_source, absent non-default names | `c2e9bdc` | tests_funding_span_alarm 14/14 | 5/14, 9 FAIL |

- Neighbour suites green at c2e9bdc (receipts `receipts/HEAD_c2e9bdc_tree_8becaf4_*.log`): tests_rehearsal_anchor (59 checks), tests_alarm_digest 34, tests_readers_three_bucket 75, tests_daily_summary 107 + 1 SKIP. tests_imports, tests_static_names, tests_pilot_log, tests_frozen_inputs, tests_universe_tripwire and gate_coverage (ok) were also green when run on their own.
- **The full battery has NOT been run** on any commit of this chain.
- Receipts are in `receipts/`: `*_red_old_ef60f85.log`, `*_green_tree_*.log` and `HEAD_c2e9bdc_*`. The LED02 green log named `2ba293c` predates the rehearsal-census amendment; the HEAD receipts supersede it.

## Not started / next steps (in order)
1. **LED-01**, lead ruling option B with six requirements (see the lead message 15:2xZ):
   - (symbol, trade_id) key in `collapse_supersedes` and the FROZEN `pilot_metrics.dedupe_fills`, with a 44-day bitwise identity proof of M2 and the watchdog cond3 inputs, before and after.
   - A non-raising write-time guard with a quarantine ledger, one alarm, and a test where the anchor completes.
   - Legal supersede chains: the 3-row pattern and the E1 singles; collapse picks the last row in write order.
   - Validator positive control over 44 days, expecting 0 violations.
   - A canonical `read_fills` plus a static census; a research-repo commit fixing `pilot_journal/tools/inspect_anchor.py`, and a list of the other research readers.
   - Coordinate the notary test with fx-exec (E10), and tell fx-w6c when the key change lands.
2. **LED-04**: a daily_nav realised-split amendment device (offline, from the guard_twin income ledger; 250 pre-fix rows through 09-12 04:46:05Z, discriminated by the absence of `realised_by_type_asset`), and a reader change in `daily_summary.realised_facts`. The live apply goes to the lead after a rehearsal on a copy.
3. **LED-05**: an offline write-back device for the 52 round-3 `reconstructed` rows (`pilot_journal/e0909g_reconstructed_orders_12Z_DRYRUN.jsonl`; do NOT use the older cc_tmp version, which has doubled fees). Cross-check against the collapsed fills; rehearse with watchdog before and after plus an idempotency check; live apply by the lead.
4. **LED-03**: an offline proxy of the 8 older batches' fees from guard_twin COMMISSION rows by (symbol, fill window), with a positive control on the exact 09-09 and 09-12 fees. The credentialed exact path is for the lead.
5. **ALM-05**: A7 scope = the latest verified external target plus held positions (binance_broker.py ~L1353-1378; fx-exec's hunks there are L379-481 and L1652-1686, so this is disjoint).
6. **ALM-06**: guard_twin DAY/CUM reference-time alignment and the `wd_worst_day_pct` rename. Develop on the copy; the lead deploys by copying the file.
7. **OPS-03**: design only; flag it to the lead before any code. The fact table §OPS-03 has already measured it:
   - the weight shaper uses a fixed window;
   - sliding-window emission reached 1,289 at 09-13 12Z and 1,941 at 08-26 12Z;
   - venue header peaks ≤1,620 of 2,400;
   - all rejects are -5022.
   Proposed red test: no sliding 60 s window above WEIGHT_PER_MIN. A replay of the recorded timelines through a sliding shaper would measure the added delay.
8. **Doc-only items**: STA-03, CFG-02, CFG-07, DOC-01 (executor README and config strings).
9. Full battery in the clone (disk rule: check `df` first). Then the final stacked diff at `docs/receipts/fx_exec2.diff`, `REPORT_FX_EXEC2.md`, and cleaning up the old worktree.

## Coordination items still open
- **fx-exec** (reply received 15:2xZ, branch fix/known-issues-2026-09-13, head a21797d):
  - They do not touch cost_buckets.py or score_post_fix.py.
  - Their daily_summary hunk is account_facts ~L191-193 and their first_anchor_review hunk ~L395-405; my daily_summary hunks (a new function before account_facts, a block after the per-anchor table) are disjoint.
  - They own the per_name_stop.py L6-9 and L130 text (E4/E6); I did not touch per_name_stop.py.
  - Both sides edit pilot_log.py: theirs is L105-116, mine is anchor_series after collapse_supersedes plus the anchors SCHEMA comment.
  - Both sides edit gate_coverage.py: they change entry texts, I append new entries.
  - Whoever commits second rebases.
  - Still to agree: the E10 notary test for supersede appends (LED-01 req. 6).
- **fx-w6c**: notify them when the LED-01 collapse key change lands (watchdog consumes collapse_supersedes).
- New findings to hand off, not edited by me:
  - NEW-01: flatten rows' `submit_ts`/`anchor_ts` are the row-write time (watchdog.py, fx-w6c).
  - NEW-02: flatten fills rows carry `attempt_idx 2` (venue_fills.py:1179).
  - NEW-03: gate_coverage SUITE_SCOPE has a duplicate key `tests_external_book`.

---

## Resume progress (appended 2026-09-13 16:2xZ; this section supersedes "Not started" above)

**Branch and state.** The clone branch `main` was renamed at c2e9bdc to `fix/ledger-alarms-2026-09-13`, and clone-local `main` was reset to ef60f85. The ledger copy moved to `/Users/haosiyu/cc_tmp/fx_exec2_state_20260913T1427Z`, and the clone's `state/` was restored with `git checkout -- state`. The old worktree's `state` symlink points at the moved copy.

**Executor chain** (ef60f85..e808697):

| Item | Commit(s) |
|---|---|
| LED-02 | c46fb83 |
| LED-07 | 7ca52ac |
| LED-08 | 469c3f3 |
| STA-02 | 8354c5a |
| ALM-01 | c2e9bdc |
| LED-01 | ec88424 (1/3), d3d16ea (2/3), 0d27a52 (3/3), df57077 (drift manifest follow-up) |
| LED-04 | e05c45a |
| ALM-05 | 63e116c |
| STA-03 | 2f66d77 |
| CFG-02 | 15c31a5 |
| CFG-07 | 4b81443 |
| DOC-01 | e808697 |

Latest partial diff: `receipts/fx_exec2_partial_ef60f85_e808697.diff`.

**Research repo:**
- inspect_anchor.py fix: 5a866f0c.
- ALM-06 guard_twin package: 24b6e083, under `guard_twin_ALM06/`. Deploy is a lead file copy.
- OPS-03 design: 9add9bd5. It is NOT coded and waits for a lead ruling.
- Devices committed before running:
  - LED-04 apply/rehearsal: da1a9389.
  - LED-03 proxy: two commits.
  - LED-05 write-back: two commits.

**Waiting on the lead:**
- Whether the full battery may make public GETs (tests_entrypoint_wiring).
- Timing of the research-copy re-vendor of pilot_metrics (deploy coupling).
- LED-04: the watchdog cond4 transfer-day bias (0.26 pp).
- OPS-03: option A, B or C.

**Waiting on fx-exec:** the E10 notary test proposal (LED-01 req. 6).

**Still to do after 16:50Z:**
- LED-04 rehearsal (devices/led04_apply_amendments.py --rehearse).
- LED-05 rehearsal (devices/led05_writeback_reconstructed.py --rehearse).
- LED-03 proxy run and positive control.
- The full battery, if allowed.
- The final `docs/receipts/fx_exec2.diff`.
