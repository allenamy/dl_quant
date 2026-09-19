> **创建:** 2026-09-19 09:0xZ | **Session:** session_01KW6frfphbFmFzx7wUtGhLb (sub-agent, exec clone only) | **状态:** IMPLEMENTED IN A CLONE, NOT DEPLOYED — deployment deferred until BOTH CFG-04 and CFG-06 reach their stopping points | **作废条件:** the user rules otherwise on RULINGS #2; or AMENDMENT 1 X-A3 is replaced (then ρ_pre here must be re-derived from the new text)

# REBUILD as the fourth `excluded_because` reason in the chase experiment — design note

Ruling: `docs/RULINGS_best_recommendation_2026-09-19.md` #2 = CFG-04 `docs/AMENDMENT_1_chase_restart_population_2026-09-16.md` §C option (a); `docs/AMENDMENT_2_blind_breach_CFG04_CFG06_2026-09-19.md` §3 and §4-3.
Criterion: X-A3 of the adopted draft `docs/fixprogram_2026-09-13/X_COST/DRAFT_AMENDMENT_chase_restart_population_2026-09-13.md` §1, word for word.
Code base: executor `~/dl_quant_live` HEAD **409ea16** (read-only), changed only in the clone `scratchpad/exec_clone_rebuild` (working tree, **uncommitted** — the diff in this folder is the whole change).

## 0. Deployment status (read this first)
- **Not deployed, and not to be deployed before both stopping points**: CFG-04 (100 pairable anchors or 2026-10-01 16Z, whichever first) **and** CFG-06 (W1 ≈ 2026-10-14). With that, both experiments run their whole window under one chase policy (AMENDMENT 2 §4-3).
- **This change is NOT claimed to leave the CFG-04 estimator unaffected.** Rebuild anchors are outside the analysis (X-A3), but chasing on them changes later anchors (§5). Deferring the deploy is what keeps those paths out of both experiments.
- The deploy (after both stop points, via `ops/safe_commit.sh` + a green battery + a quiet window between anchors + checking the first anchor after deploy) must record in its receipt **the effective anchor (first `rebalance_id`) and time, and the executor commit sha**. The per-anchor record carries the rule version on its own (§4), but not the executor sha.

## 1. The change: files and functions
| file | function / symbol | change |
|---|---|---|
| `live/chase_policy.py` | new constants `REBUILD_RHO_THRESHOLD = 0.50`, `REBUILD_RULE = "rebuild_v1: …"` | the criterion and a version string |
| `live/chase_policy.py` | new `emits_attempt1_maker_row(plan_row)` | a copy of the predicate at the top of `submit_maker`'s loop that decides whether a plan row gets an attempt-1 maker row (checked against real behaviour by test H-1) |
| `live/chase_policy.py` | new `rho_pre_from_plans(plans)` | X-A3's ρ_pre from the plan rows (pure) |
| `live/chase_policy.py` | `plan_experiment(…, rho_pre=None, rho_pre_detail=None)` | step 4: after the three older reasons, if ρ_pre < 0.50, add `"REBUILD: …"` and move every non-forced name to `chase` (the same override the tilt-abort uses). Five new record keys: `rebuild_rule`, `rebuild_rho_threshold`, `rho_pre`, `rebuild`, `rho_pre_detail` |
| `live/binance_executor.py` | `RebalanceExecutor._plan_chase_experiment` | computes `CP.rho_pre_from_plans(self._last_plans)` (an exception is caught and gives ρ None) and passes `rho_pre`, `rho_pre_detail` |
| tests | `tests_chase_policy.py` §12 (+19 checks: 37 → 56), `tests_chase_experiment_wiring.py` [G][H][I] (+11 checks: 22 → 33) | new behavioural tests |
| tests (fixtures) | `tests_chase_experiment_wiring.py` `weighted()`, `tests_per_name_stop.py` `_BOOK12` | fixture `prev_w` corrected to what `plan()` writes (§6) |

**Not changed:** `ARM_WEIGHTS`, the salt/`ASSIGN_RULE`, `assign_arms`, `neutral_only_decision`, the three older reasons (their text, order and inputs), the tilt-abort, the E4 stop exclusion, `recompute_check`, `anchor_loop`, `ops/check_chase_first_anchor.py`, `ops/chase_readout.py`, the estimator.

## 2. How ρ_pre is computed and why it is X-A3's quantity
X-A3: ρ_pre(a) = Σ over distinct symbols of |`prev_w`|, each taken from the **first** `orders.jsonl` row with `rebalance_id == a`, `order_type == "maker"`, `attempt_idx == 1`.

1. **The same value.** Every attempt-1 maker row is written by `_order_row(p, …)` from one plan row `p`, with `"prev_w": p.get("prev_w")`. `prev_w = current_notional / Σ|target_notional|` is set by `plan()` from the phase-A readback **before any order of this rebalance**. So `rho_pre_from_plans` sums `|p["prev_w"]|` for the **same** plan dicts (`self._last_plans`, set by `anchor_loop` L2159 right after `plan()`). It does not re-derive the value from `prev_notional`/`target_notional`: the two agree in production, but a re-derivation would be a second definition that could drift from the one the readout uses.
2. **The same set of rows.** `emits_attempt1_maker_row` copies `submit_maker`'s own test: a row is written iff `skip` is a label, or `skip is None` and the row has a `qty` (sent/refused makers get their attempt-1 row in `submit_maker` or in `topup`: filled / partial_expired / unknown). The only plan row with no maker row is the `band_bps` no-trade row, which is off in production (`DEFAULT_BAND_BPS = 0.0`). A symbol that appears twice is counted once. Sums use `math.fsum`, so the result does not depend on row order.
3. **Decision time only.** The function's only input is the list of plan rows. Maker fills, top-ups, the post-anchor readback and rows already written are never passed to it, and stamping all of those fields onto the rows leaves the result bit-identical (test 12e-6). A mutant that reads the book after the maker leg (prev + fills) goes red (I-2).
4. **Checked end to end.** Test H-2 builds plans with the real `plan()`, runs the real `submit_maker()` + `topup()`, then computes X-A3 **literally from the executor's own `rows_orders`**. That value equals the `rho_pre` recorded at decision time, to the bit (0.25150715900527504 in the fixture). H-1 checks that the names that got an attempt-1 maker row are exactly the rows `emits_attempt1_maker_row` selects (band row excluded).
5. **Matches the amendment's numbers.** X-A3 recomputed read-only from the live ledger (`evidence/xa3_from_ledger.py`; reads only `rebalance_id/order_type/attempt_idx/symbol/prev_w`) gives exactly the lead's four rebuild anchors: 09-03 16Z **0.2570**, 09-07 04Z **0**, 09-10 00Z **0**, 09-13 12Z **0**. The other ten anchors below 0.50 since 09-01 16Z are the ten halted anchors (ρ 0). Steady anchors sit at 0.96–1.05. The closest non-rebuild anchors are 0.6203 (09-07 08Z), 0.6673 (09-10 04Z) and 0.7104 (09-08 12Z), so nothing sits near the boundary.

**Unknown is not zero.** If the executor has no plan rows at all (`_last_plans` absent or empty), or an emitting row has a `prev_w` that is not finite, ρ_pre is `None`. The offending rows are named, and no partial sum is used, because a lower bound could fake a rebuild. With ρ None the criterion is not established, so the anchor is decided **exactly as before**, and the record shows `rho_pre: null` with the state. The top-up's `live` list is never used as a stand-in, because it is a subset of the book and would read flatter than it is (test I-3). This case cannot occur in production: `plan()` always writes a float `prev_w`, and `anchor_loop` always sets `_last_plans`.

## 3. Semantics
- **Boundary:** strictly `ρ_pre < 0.50`. Exactly 0.50 is not a rebuild; `nextafter(0.5, 0)` is (12c-1/12c-2). The threshold is a module constant, not a parameter; S-ρ25/S-ρ75 remain readout sensitivities.
- **Precedence:** REBUILD is applied **after** no-book-net, min_eligible and the tilt-abort. Those three are computed on the same inputs, in the same order, with the same text as before. On a rebuild anchor they still fire where they fired before, and REBUILD is appended last (12d-1/12d-2). REBUILD never pre-empts them.
- **Treatment:** identical to any excluded anchor today. C's fill set stays `chase_forced` and every other population name goes to `chase`. Names under a per-name stop stay outside the population (E4/R2′) and are **not** chased. `no_chase_arm_net_usdt = 0`; `no_chase_arm_tilt_frac` keeps the coin's would-be tilt, as the abort does. `recompute_check` passes through its existing excluded-anchor branch.
- **Normal anchors (ρ ≥ 0.50 or None):** the record minus the five new keys is byte-identical to 409ea16 (§7).

## 4. Record fields: how a readout identifies post-change exposure
Every `chase_experiment` record written by the new code carries:
- `rebuild_rule` (`"rebuild_v1: …"`). Its **presence** marks an anchor decided under this rule, and its absence marks an anchor decided before it. This is the policy version.
- `rho_pre` (float or null), `rebuild` (bool), `rebuild_rho_threshold` (0.5), and `rho_pre_detail` (`n_rows`, `n_without_maker_row`, `unreadable_prev_w`, `state`).
- The reason text `"REBUILD: rho_pre <exact value> < 0.5 …"` in `excluded_because`, with `in_sample: false`.

Together with the deploy receipt (effective `rebalance_id`/time + executor sha), the stopping-point analysis can:
1. **Assert** that no anchor inside the CFG-04 window (09-01 16Z → stop point) or the CFG-06 window carries `rebuild_rule`. Deployment waits for both stop points, so the expected count is 0, and any hit is listed by name.
2. If a hit ever appeared, mark the **exposed** anchors: those at or after the first record carrying `rebuild_rule`. Within them, the names with `rebuild: true` and `arm_assigned == chase` are the directly treated names. The cross-anchor paths in §5 then extend the exposure to later anchors of those names, and the analysis would need to report them separately rather than pool them.

## 5. Cross-anchor influence paths (independent review, round 5)
Rebuild anchors themselves are excluded from the analysis (X-A3). Changing their chase policy still reaches later anchors through:
1. **Next-anchor holdings / residuals.** Chasing fills gross that no_chase would have left unbuilt (09-13 12Z: 6,979 USDT = 3.0% of gross). The next anchor's `prev_notional`, deltas and from_partial residual sizes differ, so do C's book tilt and fill/skip split, and so do **which names enter the next randomised population**, and at what size.
2. **Per-name stop state and cooldowns.** Holdings that exist earlier change per-name P&L paths, stop counters and triggers, stop sets and cooldown timing. Those feed the E4 population exclusion and the stop exits at later anchors.
3. **Turnover and cost.** Fewer residuals are carried forward, so the next anchors' maker/top-up mix and fees change, as do the no_chase arm's measured tilt and the abort's input.
4. **CFG-06 populations.** Maker orders at later anchors (placement `join`/`behind` arms, requote attempt 2) are sized from those deltas, so CFG-06's order population shifts too.
5. **The next anchor's X-A3 status.** ρ_pre of the following anchor depends on how much was built. It is not affected in practice (steady ≈ 1), but it is a path.

Because of these paths the change is **deferred until both stop points**. The record fields in §4 make "no exposure inside the windows" a checkable assertion, not an assumption.

## 6. Existing fixtures that changed, and why
Before this change `prev_w` was not read by the chase path, so fixtures carried placeholders. Under the rule, a placeholder `prev_w: 0.0` claims "this book is flat", i.e. a rebuild anchor:
- `tests_chase_experiment_wiring.py`: PLANS / `_p` / `_p3` had `prev_w 0.0` beside a held book of 3,700 USDT. They now carry `prev_notional / Σ|target_notional|` (ρ 1.0176 for PLANS) via `weighted()`. Old-code behaviour is unchanged, because old code does not read `prev_w`.
- `tests_per_name_stop.py` E4-3a/E4-4 (real 09-12 12Z anchor, 192 names): the held book sits in two aggregate rows `BOOK±` with no `prev_w`. They now carry `prev_w = prev_notional / gross` and a `skipped_min_notional` label (the row a held, untraded name writes), giving ρ 1.0. The real anchor's ledger value is 1.0044. Without this, E4-3a goes red, and E4-4 silently becomes a comparison of two runs in which everyone is chased. The suite passes on the old code with the corrected fixture (exit 0).
- **Census** (`evidence/census.jsonl`: every `plan_experiment` call in the 15 suites that drive `topup()`/`plan_experiment`). REBUILD changed the arm map only in the two E4-3 runs above, which are now fixed. It also fires, **without changing any arm**, in 8 calls of `tests_signal_and_loop` and 5 of `tests_per_name_stop`. In those calls the population is empty, or the no_chase weight is 0 in that cell. No assertion there reads `in_sample`/`excluded_because`. Suites that reach `topup()` only through a subprocess are outside the census, and the full battery covers them.

## 7. Evidence
- **Red against old code:** the new test files run against a pristine `git archive 409ea16`: `tests_chase_policy` exit 1 (14 FAIL: 12a-1×2, 12a-3, 12c-2/3/4, 12d-1/2, 12e-1…6); `tests_chase_experiment_wiring` exit 1 (7 FAIL: G-1, G-2, H-1, H-2, I-1, I-2, I-3). The bit-for-bit identity cells 12b-1/12b-2/12c-1 and every pre-existing cell stay green on old code (`evidence/redold_*.log`; new-code runs = `evidence/after_battery_tests_*.log`; `tests_per_name_stop` with the corrected fixture: exit 0 on old and new, verdicts only in `evidence/tests_per_name_stop_verdicts.txt` — its full log is withheld because an existing check name quotes a realised per-name chase cost inside the CFG-04 window).
- **Bit-for-bit (in the battery):** 12b-1 pins sha256 digests of 7 golden records computed by the **unmodified** module at 409ea16 (`evidence/golden_gen.py`, `golden_409ea16.json`). The new records at ρ ∈ {None, 0.5, 0.5000000001, 0.62, 1.0, 1.0044, 7.3}, minus the five new keys, reproduce all of them.
- **Differential fuzz (outside the battery):** `evidence/fuzz_old_vs_new.py`, 20,000 random anchors, old module vs new: 11,089 cases with ρ ≥ 0.5 or None are byte-identical; 8,911 cases with ρ < 0.5 follow the override contract exactly (1,157 of them actually moved names off no_chase); **0 mismatches**.
- **Battery:** see §8.

## 8. Battery (clone, tree state `.env=false`, `notify_audit` stale; interpreter `/usr/bin/python3` 3.9.6, torch 2.2.2, `ACCEPT_PY` unset)
Both runs were in the same tree state. The clone was clean at 409ea16 before the baseline. Before the after-run, `state/` was restored to HEAD (`git checkout -- state/ && git clean -fd state/`) because the baseline had itself rewritten tracked caches. `.env=false` both times; notify_audit 1047 lines, newest 582.1 h / 582.4 h old. The exit codes below were read from files written by the runner line, not through a pipe.

| run | start (UTC) | verdict line (verbatim) | exit | suites exit 0 |
|---|---|---|---|---|
| baseline, unmodified 409ea16 | 08:28:02Z | `ACCEPTANCE: NOT GREEN — at least one suite failed (see table above)` | **1** | 154/161 |
| after, this diff (sha256 of `git diff -- live/` = `ffd93638…` = `rebuild_chase_409ea16.diff`) | 08:48:44Z | `ACCEPTANCE: NOT GREEN — at least one suite failed (see table above)` | **1** | 155/161 |

Suite by suite (`battery_compare.txt`, FAIL-line sets compared per suite):
- **6 suites are red in both runs with identical FAIL sets.** All are clone tree-state effects, and none touches the chase path: `tests_env_loading` (no `.env`, exit 3 UNAVAILABLE), `tests_alarm_digest` (notify_audit 24 days stale), `tests_reject_topup` / `tests_disposition_matrix` / `tests_break_split_wiring` / `tests_unseal_rehearsal_halt` (they read real ledger, watchdog or live-tree state that a clone does not have).
- **1 suite changed red→green, not because of this diff:** `tests_entrypoint_wiring`. Its off-schedule cell branches on wall-clock time against the producer's target file. At 08:30Z the 08:00Z target was fresh, so the run took the TRADE/off-schedule branch with `planned=0` and went red. At 08:50Z the file was 28.8 min old (more than `max_age_min=10`), so the run took the HOLD branch and went green.
- **The three touched suites:** `tests_chase_policy` `ALL PASS (37 checks)` → `ALL PASS (56 checks)`; `tests_chase_experiment_wiring` `ALL PASS (22 checks)` → `ALL PASS (33 checks)`; `tests_per_name_stop` `ALL PASS` → `ALL PASS`.
- So the only differences attributable to this change are the +19 and +11 new checks, all passing, and the corrected per-name-stop fixture, which still passes. The battery is **not** green in a clone, and that was already true before the change.

## 9. What worried me / open items for the lead
1. **The battery makes public venue requests, and my after-run landed in production's busiest minute.** The DRY_RUN entry-point cell runs a real anchor against public `fapi.binance.com` endpoints (klines / fundingRate / exchangeInfo / bookTicker). It made 568 GETs (weight 863) at 08:29:00–08:30:01Z in the baseline and 566 GETs (weight 858) at 08:49:29–08:50:34Z in the after-run. None was order-flagged, and no keys were available (the clone has no `.env`). This shares the production IP's weight budget. The baseline burst fell in production's 900 s k-window, when it sends nothing. **The after-run burst did not avoid production:** its 08:00Z anchor ran post-anchor steps until 08:55:09Z. Its telemetry shows the anchor's peak venue-reported IP weight, **1316/2400 (54.8%), in minute 08:49Z**, while its own spend that minute was 600. The logged `gap_vs_this_process=716` is consistent with my burst. There were no waits and no ban (the backstop waits at 80%). If anyone investigates that gap line, it is this clone battery. **A deploy-time or review battery should run only when no anchor process is running** (roughly N+0:24 → N+0:55 today, where N is the 4-hourly anchor), i.e. between about N+1:00 and N+4:15. Check that the previous anchor has logged `anchor done` before starting.
2. **Unknown ρ keeps randomising.** I chose "criterion not established ⇒ old behaviour" (named in the record, no alarm) over "unknown ⇒ everyone chases". This is unreachable in production today. If phase A and phase B are ever split across processes, `_last_plans` would be absent, ρ would be None, and REBUILD would silently stop applying. A page on `rho_pre is None` with a non-empty population would close that gap. I did not add it (it would be an alarm-policy change).
3. **The copied predicate** `emits_attempt1_maker_row` must stay in step with `submit_maker`. H-1 checks it by behaviour on three row kinds, but a new row-emission path in `submit_maker`/`topup` would need a new H-1 case.
4. **`recompute_check` is not extended** to assert "ρ_pre < 0.5 ⇒ out of sample". I left it unchanged to keep the change minimal. It is an optional follow-up.
5. **AMENDMENT 2 §3's first bullet** still says the main estimator is not affected (「所以主估计量不受影响」). §4-3 adds the deferral, but the §3 sentence itself is not annotated where it stands. The lead may want an in-place marker there, per the rule that a retraction must reach every copy of the claim.
6. **The readout must compute X-A3 the same way.** Use fsum, or at least state the summation. At 0.50 exactly, float summation order could matter in principle. Historically the nearest anchor is 0.62, so it does not matter in practice.
