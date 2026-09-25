> **Created:** 2026-09-26 00:0xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4) | **Status:** release notes for executor branch fix-pkg-d 96acfdd..ee455fa (9 commits, NOT pushed, not deployed; awaiting user ruling + window) | **Invalidated by:** any new commit on fix-pkg-d

# fix-pkg-d — release notes
Commits: FIXPKG_D_commits_96acfdd_to_ee455fa.txt. Battery: run 3 (18:41Z, tree ee455fa, /usr/bin/python3) 164/166. The 2 reds are drift_gate and tests_drift_gate on durable_io.py only: R25-10 is held upstream (HELD_UPSTREAM_durable_io_R25_10.diff); upstream goes first inside the window (E-0925-D).

## Behaviour changes (production code)
1. **Dust pop (D)**, 1e70316: withhold_pop pops a held residual strictly below the name's venue min notional. A flatten_only row stays at 0.0 (no orphan). A NaN held value or an unknown floor is not dust.
2. **H1 finiteness gate**, b1df4f5.
3. **durable_io split**, b9daa11 (R25-10): DurableWriteNotReplaced vs DurableWriteReplacedNotDurable.
4. **Drift guard**, 67f5ec8 (R25-12): a production->research file that is MISSING on the research side is named, not passed.
5. **Unknown is not zero on the money path**, 19c7ae1 (R25-01 tier 1: 2 medium + 5 low-medium):
   - position_break.decide: absent bucket gross ⇒ cannot speak.
   - reconcile._qty_of: no qty and no usable notional ⇒ unknown, not flat.
   - external_book.below_min_notional: no floor ⇒ unchecked, listed.
   - anchor_loop floors: unknown min_notional ⇒ no entry, and not dust.
   - child fills / userTrades: any malformed row ⇒ unknown / symbol not measured.
   - watchdog NAV flow: absent or None ⇒ unknown ⇒ priced as a flow day.

## Production data shape that the watchdog fix now reads differently (lead ruling: stated here)
**The only daily_nav writer (scheduler/anchor_loop.py L3305) writes `external_flow_usdt=None` when the income read fails** (`None if inc is None else inc["external_flow"]`).
- Before this package, watchdog.evaluate read that None as a measured 0 flow (`float(x or 0.0)`), so a deposit/withdrawal day whose income read failed was priced from its NAV jump.
- After it, such a day is UNKNOWN: flow-day pricing at L~1888, and UNKNOWN on the equity caliber at L~1368.
- 331 production rows at check time: 305 zero, 26 non-zero, 0 None ⇒ no day changes reading today.

## Test-side changes that are not new tests
- ee455fa: 5 suites' daily_nav fixtures now state `external_flow_usdt=0.0`, the shape the production writer emits on a successful income read. No assertion changed; lead accepted.
- tests_guard_calibers mutant re-anchored, same mutation.
- The pre-fix copies are stored as `*.py.prefix`, so the production-path scanner does not judge frozen old code.

## Deferred (next package, owners named)
- r25_01_2026-09-25/triage/NEXT_PACKAGE_low_defects.jsonl: 20 low defects (tier 1: 11, tier 2: 9), owner C-4, lead approval.
