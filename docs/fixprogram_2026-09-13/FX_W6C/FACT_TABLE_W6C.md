> **创建:** 2026-09-13 14:5xZ | **Session:** FX-W6C (fix worker, EXE-01 P1) | **状态:** 事实表, 写于任何执行器代码改动之前(规程 §0-1); 数字取自只读快照与重放装置收据 | **作废条件:** 执行器基底 ≠ ef60f85, 或快照/装置 sha 改变, 或冻结门 2%/5 名被改

# FACT TABLE — EXE-01: every watchdog trip flattens 100% of the book; porting W6(c) onto ef60f85

Legend: **VERIFIED** = read in code at the cited line on ef60f85, or measured by a device whose receipt is listed; **INFERRED** = reasoning from verified facts, not measured; **NOT CHECKED** = stated so nobody reads it as checked.

## §0 Frozen objects

| Object | Value |
|---|---|
| Executor base | `ef60f85ad93e49f2e0f190bc6e8a15d04073f193` = `~/dl_quant_live` HEAD = its `origin/main` (read-only check 14:05:52Z) |
| Clone | `/Users/haosiyu/cc_tmp/fx_w6c` (cloned 14:05:57Z; HEAD ef60f85 = origin/main in clone); worktrees `fx_w6c_base` @ef60f85, `fx_w6c_918559f` @918559f (runtime of 918559f = b681ca5, the code that tripped on 09-12: 918559f and 77d9baf change only `live/tests_disposition_matrix.py`) |
| W6(c) diff | `docs/receipts/w6_proportional_response_c.diff`, 98,360 bytes, sha256 `15d29d99faad2f1ad5597a89da1c1686ca94d2d94adc24c6ab1a4e4327912d5c` (verified; the iCloud copy was dataless at first read and was materialised with `brctl download`, bytes read == st_size before hashing). `git apply --check` on ef60f85: clean (one hunk offset 28 lines in `ops/gate_coverage.py`) |
| Live state snapshot | `rsync -a --exclude acceptance/` of `~/dl_quant_live/state/` → `/Users/haosiyu/cc_tmp/fx_w6c_state_snapshot`, 14:19:50–14:19:56Z (outside 16:15–16:50Z / 20:15–20:50Z), 441 MB, 1,195 files, 44 pilot_log days; `state/live/watchdog/events.jsonl` sha256 `9db1bb6c…` (= the value DESIGN §9.1 B3 recorded), `trip_receipt.json` `76f4419a…`. No `.env` exists under `state/`; the clone has none. |
| Replay device | `devices/trip_gate_replay.py` (this directory); receipts `receipts/replay_*.json` |

## §1 What happens on a trip today (VERIFIED, ef60f85)

1. `watchdog.evaluate` builds `triggers` (14 append sites: `live/watchdog.py:1233, 1354, 1510, 1668, 1863, 1867, 1882, 1895, 1897, 1903, 1965, 2096, 2130, 2132`); `tripped = bool(triggers)` (L2156).
2. `watchdog.run` (L2444): **any** trigger ⇒ `_degradation_ladder` (L450): halt opening → cancel resting orders on **every** symbol with a resting order (L521–559) → flatten **every** position the venue reports via `broker.positions()` (L588–671) → exec recovery (L681) → ALARM.log (L698). Then `set_reduce_only(True)` (L2459), protective_flatten rows (L2483), post-flatten readback (L2512), `state.json = {reduce_only: True, degradation, tripped_at, …}` (L2531).
3. There is **no branch by trigger class**: L2451–2457 routes both the "submission impaired" and the "healthy" case to the same ladder. The trip receipt of 09-12 (`trip_receipt.json`) carries only two triggers, §4-5b on 2 names and §4-7 drift, and the whole book was flattened.
4. Readers of the trip state: `scheduler/anchor_loop.py:1008` re-applies the opening halt and the local reduce-only bit when `tripped_at or reduce_only`; `signal/legs.py:333` `harvest_reset_required` discards the EMA memory on the same predicate; `ops/resume_from_trip.sh:235` refuses while `ev["tripped"]`, and L287–303 removes `state.json` **and** `harvest_ema.json` on every resume; `scheduler/run_anchor.py:669` pages off-box only `if tripped:`; `ops/assert_anchor_artifacts.py:266` requires a delivered page only `if tripped`; `ops/unseed_rehearsal_halt.py:271` refuses only on `tripped`.

## §2 Every trip class (§4-x) — measured, source of false positives, response, cost

FP cost basis (VERIFIED on two events): a full-book flatten cost **≈ 9.1 bps of gross ≈ 0.18% NAV** on 09-09 (slippage 4.14 + taker fee 4.93 bps; memory `watchdog_trip_from_ledger_gap_e0909g_2026_09_09`) and **≈ 10.4 bps ≈ 0.21% NAV** on 09-12 (5.39 + 5.0 bps, ≈245 USDT on 235,383 USDT; ERROR_LEDGER E-0912-A). At gross = 2.0×NAV, % NAV = 2 × bps of gross. Re-entry cost and time out of the market are **NOT CHECKED** here and come on top. "LOCAL" cost bound: see §8 D4.

Scope column: **NAMES** = the trigger's evidence is a set of named symbols with a per-name size; **BOOK** = the trigger measures the whole book / account / venue.

| Class | Measures (code) | Scope | FP from our own instruments? (evidence) | Response today | FP max cost | W6(c) as written (15d29d99; switch default **OFF**) | Response after this port (§8) |
|---|---|---|---|---|---|---|---|
| §4-1 | net cost c > 9 bps, 5 consecutive priced days (L1188) | BOOK | yes: fee/slippage calibers (protocol v2 fixed a |slip| caliber) | full ladder | ≈0.18–0.21% NAV | unchanged (ladder) | unchanged (ladder) |
| §4-2 | equity day change < −4.0% (L1280) | BOOK | yes: 08-21 12:16Z double-counted unrealised (E-0821-A), flattened 108 names | full ladder | ≈0.17–0.21% NAV (08-21 measured 0.17%) | unchanged | unchanged |
| §4-3 | crash-day markout tail > 25 bps adverse (L1417) | BOOK | yes: mark coverage (floor 0.50) | full ladder | ≈0.18–0.21% NAV | unchanged | unchanged |
| §4-4 | cumulative return from starting equity < −25% (L1617) | BOOK | yes: caliber (B33 fixed a peak-relative sum) | full ladder | ≈0.18–0.21% NAV | unchanged | unchanged |
| §4-4b | target_gross/nav > 2.5× target leverage (L1945) | BOOK | yes: sizing / daily_nav rows | full ladder | ≈0.18–0.21% NAV | unchanged | unchanged |
| §4-5a | venue outage: our submissions failing + public path dead (inputs L141) | BOOK | yes: egress / probe host | full ladder | ≈0.18–0.21% NAV | unchanged | unchanged |
| **§4-5b** | reconcile: position change our orders do not explain, **latest reconciled anchor**, kinds `quantity_residual` / `execution_of_unknown_size` (L1780, reconcile L696/L784) | **NAMES** | **yes, the dominant source**: universe exits not in the ledger (08-01), a shared-account probe (08-21, E-0821-C), ledger gap after a crash (09-09, E-0909-G), identity gate vs reduce-only clamp (09-12, E-0912-A); and real venue events: delisting settlement (08-26, E-0826-F) | full ladder | ≈0.18–0.21% NAV | LOCAL only if **every** anomaly is `execution_of_unknown_size` **and** `_venue_consistency` ok **and** ≤5 names **and** Σ\|intended\| ≤ 2% target gross; anything else ladder | proportional gate (§8 D1–D3) |
| §4-5c | account restriction: ≥50% venue_reject on 2 anchors / ≥3 failed attempts / account-side anomaly (L1765) | BOOK | yes: rejects of our own malformed orders are counted as venue behaviour (V7) | full ladder | ≈0.18–0.21% NAV | unchanged | unchanged |
| **§4-5e** | position_break, three gates (position_break L806–813): `split_unauth` = unauth > 5% gross **or** any name's unauth ≥ its min_notional; `flat_intent_legacy` = dev > 1% gross on a flat-intent anchor; `legacy_undecomposable` = dev > 25% gross or a name > 10% gross | NAMES **only** for `split_unauth` fired by the per-name clause alone; BOOK otherwise | yes: unauth is reconcile's residual (its own provenance sentence says "exactly as trustworthy as B30 and no more"); fired with §4-5b on 08-21, 08-26, 09-09 | full ladder | ≈0.18–0.21% NAV | **not covered** — any §4-5e trigger beside §4-5b sends the whole set to the ladder | NAMES part through the gate; BOOK part ladder |
| §4-6 | fidelity < 0.85 for 3 eligible days **and** firing-order premise failed (L2011) | BOOK | yes: m5 coverage | full ladder | ≈0.18–0.21% NAV | unchanged | unchanged |
| §4-7 rate | rebalance fail rate > 5% for 3 days (L2109) | BOOK | yes: terminal-reason classification | full ladder | ≈0.18–0.21% NAV | unchanged | unchanged |
| **§4-7 drift** | `bool(reconcile.latest)` from `watchdog_inputs` L115 — **the same partition as §4-5b** | **NAMES** (= §4-5b names) | same as §4-5b (fired with every §4-5b trip in §3) | full ladder | ≈0.18–0.21% NAV | same partition as §4-5b under the switch (`watchdog_inputs` reads `latest_if_local_response`) | same names as §4-5b, through the same gate |

## §3 The live record: every flatten batch, and the two readings of the frozen gate

Source: `state/live/watchdog/events.jsonl` (snapshot copy; 15 events, 10 flatten batches). Replays: `devices/trip_gate_replay.py` on a copy of the snapshot truncated at each trip instant (receipts `receipts/replay_<trip>_<code>.json`). The triggers each replay reproduces are compared with the receipt's trigger text.

| Trip (UTC) | Triggers in the receipt | Flattened | Root cause (receipt) | Named scope, measured at-stake | W6(c) as written (if ON) | This port |
|---|---|---|---|---|---|---|
| 08-01 20:18:27 | §4-5b 2 names; §4-7 drift | 105 names, 4,081.51 USDT | universe exits not written to the ledger — our instrument (JOURNAL_2026-08-03 §3; fix `59f249e`) | ALT/RVN residual 9.56 + 8.62 = 18.18 USDT on a 4,297.77 target (0.42%). Replay on ef60f85 also shows §4-5e split_unauth per-name (the split gate did not exist on 08-01) | ladder (kind `quantity_residual`) | **LOCAL** |
| 08-02 04:18:21 | §4-5e legacy 26.4% > 25% | 83 names | underfill read as a break (pre-split) | BOOK | ladder | ladder |
| 08-05 00:18 / 12:18 | §4-1 | 108 / 102 names | cost persistence | BOOK | ladder | ladder |
| 08-21 12:16:30 | §4-2 −4.52% | 108 names, 31,422.84 USDT | caliber double count (E-0821-A) | BOOK | ladder | ladder |
| 08-21 20:16:00 | §4-5b 2; §4-5e split_unauth ATOM, SNX; §4-7 drift | 102 names, 30,540.86 USDT | our execution probe closed the book's ATOM/SNX on the shared account (E-0821-C) — a real position change caused by our own process | residual 369.18 + 187.11 = 556.29 USDT (= the receipt's "UNAUTHORIZED 1.84%") = **1.836%** of 30,305.50 target | ladder (kind + §4-5e co-trigger) | **LOCAL** |
| 08-26 12:47:02 | §4-5b 2; §4-5e split_unauth STORJ, SCRT; §4-7 drift | 334 names, 29,502.06 USDT | venue delisting settlement, status SETTLING (E-0826-F root-cause correction) — a real venue event on two names | 138.38 + 157.53 = 295.92 USDT = **0.996%** of 29,717.79 target | ladder (kind + §4-5e co-trigger) | **LOCAL** |
| 09-06 08:46:08 | §4-2 −4.12% | 268 names, 162,665.94 USDT | real day loss | BOOK | ladder | ladder |
| **09-09 16:45:36** | §4-5b 9; §4-5e split_unauth **52 names** (unauth 1.09%); §4-7 drift | **243 names, 232,756.97 USDT** | ledger gap: the 12Z anchor crashed before writing orders rows (E-0909-G) — our instrument | 9 `quantity_residual` names + 52 §4-5e names; doubt sum 2,525 USDT = 1.09% of gross | ladder | **LADDER (52 names > 5 — the name limit alone decides; the 2% test would have passed)** |
| **09-12 12:47:37** | §4-5b 2; §4-7 drift | **255 names, 235,382.55 USDT** | identity gate read a reduce-only clamp as a contradiction (E-0912-A) — our instrument | MEME/POPCAT `execution_of_unknown_size`, joint Σ\|intended\| 1,524.32 USDT = **0.647%** of 235,497.44 target | LOCAL (Σ\|intended\| 0.647%; venue records self-consistent) | **LOCAL** |

**VERIFIED from the table:** 5 of the 10 flatten batches came from the name-scoped classes (§4-5b / §4-5e per-name / §4-7 drift). Under the frozen 2%/5-name gate, **4 of those 5 were two-name events at 0.42–1.84% of gross** — two instrument false positives (08-01, 09-12) and two real two-name venue position changes (08-21, 08-26). W6(c) as written covers **one** of the four (09-12): the other three are `quantity_residual` and co-fired §4-5e. **09-09 is not reclassified by any reading of the frozen gate** (52 names), and that is reported, not tuned away.

## §4 The two trips the lead named, gate by gate (from receipts)

### 09-12 12:47:37Z — `receipts/replay_20260912T1247_918559f.json` (trip-time runtime) and `…_ef60f85.json`
- **Trip-time code (918559f runtime = b681ca5), ledger truncated at the trip:** tripped; triggers byte-identical to `trip_receipt.json` ("§4-5b … on 2 name(s) … (17 in this window's history)"; "§4-7 un-recovered position drift"); 5b ANOMALOUS n=2 at anchor 1789215841.923763; `reconcile.latest` = MEMEUSDT, POPCATUSDT, both `execution_of_unknown_size`; §4-5e `split_unauth` not triggered (unauth 0.0).
- **Gate:** no BOOK trigger; names {MEME, POPCAT} = 2 ≤ 5; at-stake = joint Σ|intended| 1,015.24631076 + 509.07486 = **1,524.32117076 USDT**; gross = anchors row target_gross **235,497.44337835** (readback Σ|notional| 235,397.72 reported beside); **0.6473% ≤ 2% ⇒ LOCAL**; unknown inputs: none. The named positions at the 12Z readback were 0 and 0 (both full exits had filled), so the local action has nothing to flatten; the unrelated 253 names stay.
- **ef60f85 (deployed base), same truncation:** not tripped; 5b CLEAN at the same anchor; history 15 (the two false anomalies are re-derived by W6(a)(b)). The gate is not reached. ⇒ (a)(b) removed this *cause*; the gate is about the *next* instrument false positive of any other kind.

### 09-09 16:45:36Z — `receipts/replay_20260909T1645_ef60f85.json`
- **ef60f85, ledger truncated at the trip:** tripped; triggers identical in prefix and numbers to events.jsonl line 13 ("§4-5b … 9 name(s) … (15 …)", "§4-5e position break [split_unauth]: 3951 USDT … 1.7% of a 232746 … UNAUTHORIZED 1.09% …", "§4-7 un-recovered position drift"). `reconcile.latest` = 9 × `quantity_residual` (ARKM 65.69, BLUAI 171.52, BTR 166.99, CAKE 38.44, DOGS 177.33, DYDX 48.45, ENS 32.29, FIDA 165.33, HUMA 71.06 USDT); §4-5e per-name clause fired on **52** names, portfolio clause not fired (unauth_frac 1.085%).
- **Gate:** no BOOK trigger, but names = union(9, 52) = **52 > 5 ⇒ LADDER**. The doubt sum (Σ unauth over the 52 names, ≥ each name's residual) is 2,525 USDT = 1.085% of the 232,746.08 target — the 2% test alone would have passed; the 5-name limit is what keeps 09-09 on the ladder.
- The ledger-gap mechanism does not depend on the executor version (the 52 reconstructed orders rows were never written back, LED-05), which is why the replay runs on the deployed base.

## §5 Genuinely book-level conditions still reach the full ladder — and one premise that is false

- **§4-2 daily loss line, §4-4 cumulative from starting equity, §4-4b leverage, §4-5a outage, §4-5c account restriction, §4-1, §4-3, §4-6, §4-7 rate, §4-5e portfolio / flat-intent / undecomposable gates:** BOOK scope by construction (§2). Rule D1: **any** BOOK trigger ⇒ full ladder, whatever else fired. To be proven by negative-control cells on a held book (every name flattened, reduce-only set).
- **"Positions unreadable across the book" does NOT reach the ladder today — VERIFIED, probe `receipts/probe_unreadable_book.log` on ef60f85:**
  - U1 newest anchor wrote no readback (what `anchor_loop.py:1197` does when the account read fails: HIGH "position readback failed; proceeding on cached book"): **not tripped, not blind**; §4-5b/§4-5e/§4-7 read the *previous* reconciled anchor and report CLEAN.
  - U2 no readback anywhere in the window: **not tripped**; `conditions_blind = [cond5_venue_event, cond7_ops]` ⇒ `resume_from_trip.sh` refuses; `run_anchor.py` pages HIGH "blind" once the clock has started.
  - U3 newest readback with NaN notionals: not tripped, CLEAN (quantities are compared; the notional is only a mark source).
  - This is the B30 design ("tripping on missing data is the failure mode this whole item removes"), and the ladder could not flatten an unreadable book anyway (`_degradation_ladder` sends nothing when `broker.positions()` raises, L599–605). **This port does not change that path; the same probe is re-run on the fixed clone as an equality control.** U1's stale-but-not-blind reading is registered as a detection gap outside EXE-01 (§10).

## §6 When the gate's inputs are unknown or NaN — which way it fails, and why

| Input | Source | Can it be unknown? | Direction | Why this satisfies both rules |
|---|---|---|---|---|
| name set of §4-5b | `reconcile.latest[*].symbol` | no (reconcile indexes readback by symbol; a row without one raises inside evaluate ⇒ CRITICAL "看门狗本轮无法评估", no trip) | — | — |
| name set of §4-7 drift | `ops_stats[-1]["drift_names"]` (added by this port in `watchdog_inputs`) | only for a caller that hand-builds `ops_stats` (tests); production always derives it from the same reconcile | missing ⇒ that trigger is **BOOK** ⇒ ladder | not reachable on the production path; a scope nobody stated is not a scope |
| name set of §4-5e | `split_verdict.unauth_names` when only the per-name clause fired | no (every other §4-5e gate is BOOK) | — | — |
| per-name at-stake | joint Σ\|intended\| / \|residual_usdt\| / \|unauth_usdt\| | yes: an unquantifiable row whose intended notional is unreadable | unknown ⇒ **counted as a name, excluded from the known sum, named in the page**; if the known sum alone is > 2% ⇒ ladder, otherwise **LOCAL** | ① an unknown term is by construction our own record failing to state a size — the user's 09-12 rule forbids a book-level response to instrument doubt; ② the local action does not use that number: it flattens the **whole venue position** of every named name, sized from `broker.positions()` at response time, so an unknown that hides a large exposure **on those names** is still removed; ③ exposure on other names is not implicated by this evidence and stays under the BOOK guards, which read none of these inputs; ④ opening is halted and a human is paged either way |
| gross reference | anchors row `target_gross` at/before the reconciled anchor (frozen R-14 denominator) | yes: row missing (crash before the anchors row), non-finite, ≤ 0 | fall back to Σ\|readback notional\| at the same anchor (the venue's own number); both unusable ⇒ gross **unknown** ⇒ the 2% test cannot prove "large" ⇒ **LOCAL**, named | W6(c) failed closed to the full ladder here ("no anchors row ⇒ not eligible"): a missing row of **our** ledger flattened the book — exactly the case the 09-12 rule forbids; the fallback keeps the frozen denominator whenever it exists |
| name count > 5 or known sum > 2% | — | — | ladder | the frozen thresholds; not retuned |
| config switch | `config/book.json` `watchdog_proportional_response.enabled` | yes: key missing / file unreadable | **ON** (the ruled default), source recorded | R-14 reading A is the default; an unreadable config must not silently revert to the rule the user ruled out |

## §7 W6(c) as written, against the rules and the reviews (why a verbatim port is not enough)

| # | Gap in 15d29d99 | Evidence | Rule it breaks |
|---|---|---|---|
| G1 | Scope is one anomaly kind behind a venue-self-consistency predicate; `quantity_residual` and a co-firing §4-5e always go to the ladder | §3: 08-01, 08-21, 08-26 stay ladder under W6(c) | 09-12 rule ② "全书级响应必须过比例门"; catalogue rule (cost ≥ 0.1% NAV ⇒ gate) |
| G2 | `_between` keeps only the first unknown row per name (`unknown.setdefault`), so eligibility changes with row order (C9) | DESIGN §6.5 #1; reviewer follow-up RESULT §5 | reviewer blocks enabling until closed |
| G3 | `_is_evidenced_clamp_kind` still has the C6 (joined reasons) and C7 (NaN / negative children) forms | DESIGN §6.5 #2 | same |
| G4 | No off-box page for a local response: `run_anchor.py:669` pages only `if tripped`; the design text "the anchor pages off-box from state.json's `tripped_at`" is not what the code does | code; W6(c) gate_coverage entry admits "does NOT prove … that the off-box page fires" | watchdog header: notified = left the machine |
| G5 | A local state carries `tripped_at` ⇒ `harvest_reset_required` resets the EMA at **every** halted anchor, and `resume_from_trip.sh` deletes `harvest_ema.json` — on a book that was **not** flattened (α = 0.05 in `config/book.json`, ~3.3 days of memory) | `signal/legs.py:333`, `resume_from_trip.sh:296–303` | the reset's own premise ("平仓后我们持有的是零") is false for a local response ⇒ a turnover burst the book did not earn |
| G6 | The re-check flattens only `held − expected`, where `expected` is the doubted ledger number | `_local_response` in the diff | instrument doubt deciding the size of a protective action |
| G7 | No cancel of resting orders on the named names before the reduce-only exit | `_local_response` | 07-29 ghost positions (ladder rung 1b exists for this) |
| G8 | No exec-recovery sweep for flatten legs of unknown size | `_local_response` vs ladder rung 2b | a local flatten leg of unknown size becomes the next anomaly |
| G9 | No anchors row / non-finite gross ⇒ full ladder | `unknown_size_local_eligibility` | 09-12 rule ① (§6) |
| G10 | A local response overwrites a standing trip's `state.json` (drops `degradation`) | `run()` elif branch | the trip's record must survive (B19) |
| G11 | Resume gate and unseed tool ignore `local_responses` ⇒ a resume can be certified while a local response would fire again | `resume_from_trip.sh:235`, `unseed_rehearsal_halt.py:271` | "refuse while the condition holds" |
| G12 | Artifact assertion #7 requires a delivered page only for trips | `assert_anchor_artifacts.py:266` | same as G4 |
| G13 | `watchdog.py` gains four `execution_of_unknown_size` literals and the blind-spot pin "no execution_of_unknown_size exemption" had to be restated | `tests_position_break_blindspot.py:231` | a kind-specific exemption is the shape the pin exists to stop |

## §8 Design derived from the facts (this is what the code will do)

- **D1 Scope per trigger, at the append site.** §4-5b and §4-7 drift carry the names of `reconcile.latest`; §4-5e carries `unauth_names` only when `trip_gate == split_unauth`, the per-name clause fired and the portfolio clause did not. Every other trigger — including any future one — is **BOOK** unless its append site says otherwise (fail closed for new classes).
- **D2 The gate (thresholds frozen, not retuned):** switch ON ∧ no BOOK trigger ∧ names ≤ **5** ∧ ¬(gross known ∧ Σ known at-stake > **2%** × gross) ⇒ **LOCAL**; otherwise the full ladder, byte-for-byte today's path. Inclusive at 2.00% and at 5 names, as W6(c).
- **D3 At-stake = the size of the doubt, in R-14's own measure and its analogues:** joint Σ|intended| over **all** unquantifiable rows of the name in the interval (closes G2 by construction: a sum over the set cannot depend on order), |residual_usdt|, |unauth_usdt|; per name the max of the terms that apply. The name's whole position is **not** a term (it is what the action removes, not the doubt). The venue self-consistency predicate leaves the decision path entirely (closes G1, G3; D1 makes §4-5b kind-agnostic, so `watchdog.py` needs no kind literal and the original pin holds verbatim — closes G13).
- **D4 The local action, in the ladder's order and isolation, restricted to the named names:** halt opening → cancel resting orders on the named names only → flatten the **whole** venue position of each named name, reduce-only, sized from `broker.positions()`, re-read and retried (≤3), never another symbol, never the account reduce-only bit → exec recovery → protective_flatten rows + post-flatten readback → ALARM.log. Severity HIGH when every named name reads flat; CRITICAL when a named name is still held or positions were unreadable (closes G6–G8). **Cost bound:** ≤ 5 names. Measured on the snapshot's last 12 days (58 anchors with gross ≥ 1,000 USDT, anchor readbacks only): the largest single name was **1.87%** of realized gross and the largest five names together **9.07%** (median 5.77%) — VERIFIED, `receipts/position_share_last12d.log`. So the named positions are ≤ ≈ 9.1% of gross plus their doubt (≤ 2%) ⇒ worst case ≈ 11% of gross × 10.4 bps × 2 ≈ **0.023% NAV**; typical (two names at the 12Z mean ≈0.39%) ≈ **0.002% NAV** (INFERRED arithmetic on verified inputs) — under the catalogue's 0.1% NAV line, so the local action does not itself need a proportionality gate. Plus the opening halt until a human resumes (not a flatten; its tracking cost is **NOT CHECKED**).
- **D5 State:** kind `proportional_local`, `book_flattened: false`, `tripped_at` set (every existing halt reader — anchor 0b, readiness sheet, first-anchor review — keeps reading "halted", the conservative side). A local response never replaces a standing trip's record (appended to it instead; closes G10). `harvest_reset_required` does not reset for a `proportional_local` state that did not flatten the book; `resume_from_trip.sh` keeps the EMA memory for that kind (closes G5).
- **D6 Notification:** one composition `watchdog.local_response_page` (facts from the record, evaluated_utc in the body so distinct events never dedupe; DECIDE-tier words 止损触发 / 开仓已停); `run_anchor.py` sends it off-box and persists `local_response_receipt.json`; artifact assertion #7 covers it (closes G4, G12).
- **D7 Resume / unseed:** both refuse while `local_responses` is non-empty on the copy they judge (closes G11).
- **D8 Switch:** `config/book.json` `watchdog_proportional_response.enabled`, default **true**; missing/unreadable ⇒ true with the source recorded; thresholds are module constants pinned by a test and deliberately **not** config keys (a retune must be a reviewed code change).
- **D9 Priority:** a trip outranks a local response in the same evaluation (the BOOK trigger wins; the named names are flattened by the ladder with everything else).

## §9 Catalogue checklist (`docs/CATALOGUE_venue_behaviours_positive_controls_2026-09-12.md`) for this change

"FP max cost" = cost if the behaviour is misread as an anomaly **under the new routing**: LOCAL ≤ 0.04% NAV (§8 D4) when it stays within 5 names / 2%; otherwise the ladder ≈ 0.18–0.21% NAV.

| # | Behaviour | Touches this change? | Control | FP max cost after |
|---|---|---|---|---|
| V1 | reduceOnly qty > position clamped | the local flatten sizes from `positionAmt`, so qty == position; a clamp, if it happens, is (a)(b)'s path | existing `tests_reduce_only_clamp` (unchanged); new cell: local flatten orders carry exactly the venue contracts | LOCAL ≤ 0.04% NAV |
| V2 | −5022 post-only | no (IOC reduce-only market) | n/a | — |
| V3 | −2027 max notional | no (reduce-only exit) | n/a | — |
| V4 | −2022 reduceOnly rejected (no position / wrong side) | yes: a race between re-read and send | new cell: `flatten_all` raises for the named name ⇒ error recorded, CRITICAL, other symbols untouched | LOCAL |
| V5 | −4189 account reduce-only | no (exits allowed) | n/a | — |
| V6 | −4400 quant-rules lock | possibly (exits during a lock: **NOT CHECKED** on the venue) | same failure cell as V4 (recorded, CRITICAL) | LOCAL |
| V7 | −1111/−4024/−4164/−4005 | yes (dust / cap on exits): the ladder has the same exposure | `flatten_all` splits by maxQty (unchanged); failure cell as V4 | LOCAL |
| V8 | partial fill then cancel (IOC) | yes | new cell: venue still holds after the first attempt ⇒ re-read + retry, residual reported | LOCAL |
| V9 | userTrades twin rows | exec recovery reuses `venue_fills.flatten_exec_from_trades` (unchanged) | existing | — |
| V10 | transport timeout, order may have landed | yes: leg recorded `execution_unknown` ⇒ next reconcile may flag that one name | covered by the gate itself (≤5 names ⇒ LOCAL again) | LOCAL |
| V11 | STP EXPIRE_MAKER | yes: our own resting maker vs our taker exit on the same symbol | new cell: resting orders on the named names are cancelled **before** the flatten (actions order) | — |
| V12 | positionSide BOTH (A1) | unchanged premise | existing | — |
| V13 | origQty precision | sizes are the venue's own `positionAmt` | V1 cell | — |
| V14 | price protection | market exits may be refused | failure cell as V4 | LOCAL |

## §10 Not checked / limits of this table

1. The replays truncate a **copy** of the ledger by each row's own time key; rows written after the trip for earlier anchors (none found in the two named trips) would be kept. 08-01/08-21/08-26 were replayed on **ef60f85** code, not the code that tripped then (their receipts' triggers are reproduced; 08-01 additionally shows §4-5e, which did not exist until 08-03).
2. Re-entry cost and time-out-of-market after a full flatten are not measured here; the FP cost column is the flatten alone.
3. The venue's behaviour for reduce-only market exits during −4400 / price-protection is not verified (V6, V14).
4. U1 (§5): a newest anchor with no readback leaves §4-5b/§4-5e/§4-7 reading the previous anchor as CLEAN without a blind flag. Detection gap, not the response; out of EXE-01's scope; reported for the lead.
5. Cross-anchor unexplained residuals (EXE-04 / Q6) affect **detection** (a residual can vanish from `reconcile.latest` one anchor later); they do not change which response a detected set gets. The local action removes the whole venue position of every named name, so it does not rely on the reconcile baseline being right for those names.
