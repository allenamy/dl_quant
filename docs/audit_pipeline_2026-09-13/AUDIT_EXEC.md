> **创建:** 2026-09-13 13:3xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (auditor teammate, read-only) | **状态:** 审计登记册(只读; 未改任何实盘文件) | **作废条件:** 执行器 HEAD ≠ ef60f85、config/book.json sha256 ≠ f6fd6d0e…, 或任一登记项被修复/裁定后需差异复核

# AUDIT_EXEC — live execution, logging and reconciliation

Companion data: `AUDIT_EXEC.json` (same items, same wording).

## 0. What was audited, frozen at what

| Object | Value |
|---|---|
| Executor HEAD | `ef60f85ad93e49f2e0f190bc6e8a15d04073f193` = origin/main |
| Executor git tree | `ed2f881989e164a8d0de75fb00a698e674d011df` (equals the reviewer's independently computed four-patch tree) |
| config/book.json | sha256 `f6fd6d0e0f10039a…`, 31,904 bytes |
| Latest anchor read | 2026-09-13 12Z, `A1789302239`, `anchor done rc=0` at 12:58:30Z (rebuild from flat) |
| Audit clock | 12:39Z-13:3xZ; ledger scans only after 12:50Z |

Constraints kept: ~/dl_quant_live and ~/wide_shadow only read; no file written there; no exchange API call; .env not read; no ops script that writes state was run; no --check script run; ledger scans started after 12:50Z; during 12:39-12:50Z only small files and code were read; hashes taken with the t6_sha_guard rules (dataless flag checked, bytes read == st_size); one pure function (live/cost_buckets.bucket_fills) executed from a scratch copy with bytecode writing disabled.

Status legend: **FIXED_DEPLOYED** = fix is in the running tree and the running process loaded it; **VERIFIED_IMMATERIAL** = checked; no effect on the named layers (resolution given); **OPEN_MEASURED_MATERIAL** = defect confirmed with numbers; real effect on the named layer, even if small; **OPEN_NOT_MEASURED** = mechanism confirmed, size of effect not measured; **PENDING_USER_DECISION** = needs a user ruling (policy, experiment readout, or an operator step that touches the venue or the ledger); **DOC_STALE** = code and state are right, a document or memory note is wrong.

## 1. Result

**No P0 found. Two P1 items.** The running executor is exactly the reviewed tree and the 12Z rebuild ran it (EXE-08). The two P1s are both ways the live book can still be changed without a ruling:

| ID | Title | Status | Why P1 |
|---|---|---|---|
| EXE-01 | Any watchdog trip still flattens 100% of the book; the proportional response W6(c) is not deployed | PENDING_USER_DECISION | One false positive on a single name still flattens the whole book; this has happened twice in four days from our own instruments. |
| OPS-01 | The withdrawn σ_fund gross ladder re-arms at the next login: plist still installed, executor reader still active, STATE still says it is live | OPEN_NOT_MEASURED | A reboot can silently re-enable a withdrawn exposure rule (gross ×0.5) without a user ruling, with only an INFO notice. |

| Status | Count |
|---|---:|
| FIXED_DEPLOYED | 1 |
| VERIFIED_IMMATERIAL | 12 |
| OPEN_MEASURED_MATERIAL | 9 |
| OPEN_NOT_MEASURED | 2 |
| PENDING_USER_DECISION | 10 |
| DOC_STALE | 8 |
| **Total** | **42** |

By severity: P0 0, P1 2, P2 12, P3 28.

## 2. Short answers to the six questions

1. **Policy config vs rulings.** Gross/leverage 2.0×NAV and the per-name stop profile match the rulings (CFG-01, CFG-02). The maker window is 900 s live; STATE.md:20 and two memory notes wrongly say 180 s (CFG-03). Still experimental: chase 50/50 (hard-coded, CFG-04), requote p=0.5 (CFG-05), placement eps 0.50 whose adoption basis was half voided on 09-05 (CFG-06). Internal-book keys are inert (CFG-07); producer pins are off (CFG-08).
2. **State files and alarms.** Watchdog state is clean (STA-01). per_name_stop.json is consistent, but cooldown expiries page at HIGH (STA-02). `no_trade_band.json` and the EMA state have no reader in external mode (STA-03). The funding_span table feeds only the executor's own frozen DL panel and cannot move the traded book; the alarm's text and fingerprint are wrong (ALM-01). factor_health watches a report retired on 08-06 and its artefact assertion passes vacuously (ALM-03). Other alarm defects: hard-coded date in cond2 (ALM-02), false REGRESSION pages (ALM-04), A7 scoped to the wrong universe (ALM-05), guard_twin reference-time disagreements (ALM-06). Separately, the withdrawn σ_fund ladder can re-arm at next login (OPS-01, P1).
3. **Ledgers and readers.** fills.jsonl is exactly 2× on every day; in-repo readers collapse it (LED-01). The 09-12 flatten has 255 fee-less order rows and no fills rows: fills-based tools under-report, order-layer three-bucket readers mark all 255 unpriced (verified by running the function), and they will stay unpriced after the fee backfill (LED-02). Eight older flatten batches cannot be attributed (LED-03). daily_nav's realised-by-type split is wrong from 07-29 to 09-12 06:05Z; use NAV for totals and guard_twin's income ledger for the split (LED-04). The 52-row writeback is pending (LED-05). The notary chain has been broken since 08-31 (LED-06). anchors.jsonl needs a halted-row and era filter (LED-07). The Telegram anchor report still folds unknowns to zero (LED-08).
4. **Reviewer's open executor items.** Direct GET read path: reachable, but no caller reads the wrong field (EXE-05, P3). JSON-array event: only the battery and a manual tool parse it, and they fail closed (EXE-06, P3). flatten_only via the chase frame: real, 9 filled exit top-ups (≈5,670 USDT) since 09-01, policy pending (EXE-02, P2). Reconcile multi-reason reader: no such strings exist or can be written now (EXE-07, P3). The larger open executor risk is EXE-01 (P1): any trip still flattens the whole book.
5. **Deep-check template.** fund_updates baselines still hold (CHK-04). Stale: counterfactual rewrite level, now ≈27% (CHK-01); maker share ≥90%, now 0.56-0.89 per anchor (CHK-03). Wrong source: guard_twin AGREE lives in `~/guard_twin/state/latest.json`, not anchor_runs.log (CHK-02). Missing checks listed in CHK-05.
6. **Other live embodiments of corrected errors.** Executor neutralisation flips small producer shorts into longs and the alarm blames withheld names (EXE-03); reconcile still drops unexplained balances after one window (EXE-04); the killed probe is held only by KILL files (OPS-02); the rebuild ran at 99% of the request budget (OPS-03); STATE/CLAUDE.md executor facts (DOC-01).

## 3. Register

| ID | Layer | Title | Status | Sev | Affects |
|---|---|---|---|---|---|
| EXE-01 | executor / watchdog response | Any watchdog trip still flattens 100% of the book; the proportional response W6(c) is not deployed | PENDING_USER_DECISION | P1 | live_trading |
| OPS-01 | ops (launchd) / executor sizing | The withdrawn σ_fund gross ladder re-arms at the next login: plist still installed, executor reader still active, STATE still says it is live | OPEN_NOT_MEASURED | P1 | live_trading, reporting |
| EXE-02 | executor / stop exits | Stop and exit residuals are topped up with taker orders through the chase frame, while the stop clause says maker-only, no chase | PENDING_USER_DECISION | P2 | live_trading, future_eval |
| EXE-03 | executor / reshape | Executor neutralisation of a net-short producer book flips small shorts to longs; the 撤名残差 alarm blames withheld names for the producer's own net | PENDING_USER_DECISION | P2 | live_trading, reporting |
| EXE-04 | executor / reconcile | Reconcile compares window by window, so an unexplained balance vanishes one anchor later (Q6, not coded) | PENDING_USER_DECISION | P2 | live_trading |
| CFG-03 | config / execution window (docs) | The live maker window is 900 s, but STATE.md and the memory index say 180 s is live | DOC_STALE | P2 | future_eval, reporting |
| CFG-04 | config (code constant) / chase experiment | Chase 50/50 randomisation is live and hard-coded, before its stop point; rebuild anchors and stop exits now sit inside its population | PENDING_USER_DECISION | P2 | live_trading, future_eval |
| CFG-06 | config / placement bandit | Placement bandit eps 0.50 was adopted on a 'not toxic' finding that a later receipt voided; the config basis was not updated and no re-read is scheduled | PENDING_USER_DECISION | P2 | live_trading, future_eval |
| ALM-03 | monitor / factor_health | factor_health still polls the retired jpline report every anchor; the artefact assertion for decay monitoring passes vacuously; W5 has not landed | PENDING_USER_DECISION | P2 | live_trading, reporting |
| LED-02 | ledger / 09-12 flatten costs | 09-12 protective flatten: 255 order rows without fees and no fills rows; the backfill is an operator step that has not run | PENDING_USER_DECISION | P2 | future_eval, reporting |
| LED-04 | ledger / daily_nav realised P&L | daily_nav realised P&L by type is under-recorded from 07-29 to 09-12 06:05Z (twin income rows dropped, BNB fees summed raw); fixed going forward only | OPEN_MEASURED_MATERIAL | P2 | future_eval, reporting |
| LED-06 | ledger integrity / notary | The ledger notary has produced no valid hash chain and no third-party timestamp since 08-31 | OPEN_MEASURED_MATERIAL | P2 | reporting |
| CHK-01 | per-anchor deep check / baseline | Deep-check baseline 'counterfactual rewrite 19-20% since 09-03' is stale; the level is about 27% and rose about 6 pp in four days | DOC_STALE | P2 | live_trading, reporting |
| CHK-03 | per-anchor deep check / baseline | Deep-check baseline 'maker share ≥90%' no longer holds; the execution mix changed after 09-02 and nobody has attributed it | DOC_STALE | P2 | future_eval, reporting |
| EXE-05 | executor / broker read path (reviewer item) | Reviewer item: the broker's direct GET read path does not adopt the capacity-conflict contract, but no caller reads the affected field | VERIFIED_IMMATERIAL | P3 | reporting |
| EXE-06 | battery and ops parsers (reviewer item) | Reviewer item: a JSON-array line in watchdog events.jsonl makes the battery and an ops tool raise; the live anchor never reads that file | VERIFIED_IMMATERIAL | P3 | reporting |
| EXE-07 | executor / reconcile (reviewer item) | Reviewer item: reconcile's clamp re-derivation reads only the first origQty pair; no multi-reason strings exist or can be written now | VERIFIED_IMMATERIAL | P3 | live_trading |
| EXE-08 | executor / deployment identity | The running executor is exactly the reviewed four-patch tree, and the 12Z anchor ran it | FIXED_DEPLOYED | P3 | live_trading |
| OPS-02 | ops (launchd) / execution probe | The killed execution probe's launchd job is still loaded with RunAtLoad; only KILL files keep it from starting | VERIFIED_IMMATERIAL | P3 | live_trading |
| OPS-03 | ops / request budget at rebuild | The 12Z flat-to-full rebuild ran at 99% of the self-imposed weight budget | OPEN_NOT_MEASURED | P3 | live_trading |
| CFG-01 | config / leverage | Gross and leverage match the latest ruling (2.0 × NAV) | VERIFIED_IMMATERIAL | P3 | reporting |
| CFG-02 | config / per-name stop | per_name_stop profile matches STATE (wide d30_n2_c42, floor 5 USDT); the profile's basis text still says 20 USDT | DOC_STALE | P3 | reporting |
| CFG-05 | config / requote experiment | Requote randomisation (p_requote 0.5) is live and experimental; readout not before 09-19 00Z | PENDING_USER_DECISION | P3 | live_trading, future_eval |
| CFG-07 | config / internal-book keys | Internal-book keys are inert in external mode; the config header still says the deployed book is three legs | DOC_STALE | P3 | reporting |
| CFG-08 | config / producer identity | The executor does not pin the producer's booster or universe; today's booster matches STATE | VERIFIED_IMMATERIAL | P3 | live_trading |
| STA-01 | state / watchdog | Watchdog state is clean after the resume; the trip receipt is write-only; a transfer today would not re-trip | VERIFIED_IMMATERIAL | P3 | live_trading |
| STA-02 | state / per-name stop | per_name_stop.json is consistent after the rebuild; routine cooldown expiries page the user at HIGH | VERIFIED_IMMATERIAL | P3 | reporting |
| STA-03 | state / retired internal-book state | state/live/no_trade_band.json (last written 08-22 04:00Z) and the harvest EMA state have no reader in external mode | VERIFIED_IMMATERIAL | P3 | reporting |
| ALM-01 | alarm / funding_span | The funding_span STALE alarm is true about the executor's own frozen DL panel, cannot move the traded book, and its text and fingerprint are wrong | VERIFIED_IMMATERIAL | P3 | reporting |
| ALM-02 | alarm text / watchdog | cond2.judged_on hard-codes 2026-09-06 | OPEN_MEASURED_MATERIAL | P3 | reporting |
| ALM-04 | alarm / artefact assertion | The artefact column detector pages HIGH on clean anchors for columns that only fill on unknown fills | OPEN_MEASURED_MATERIAL | P3 | reporting |
| ALM-05 | executor arm() diagnostic | arm() A7 margin/tier-1 diagnostic is scoped to the retired internal universe (110 names), not the traded book | OPEN_MEASURED_MATERIAL | P3 | reporting |
| ALM-06 | monitor / guard_twin | guard_twin DISAGREE lines are mostly reference-time artefacts, and its wd_worst_day_pct field shows history as if current | OPEN_MEASURED_MATERIAL | P3 | reporting |
| LED-01 | ledger / fills.jsonl | fills.jsonl holds every trade exactly twice; in-repo readers collapse the copies, a naive reader double counts | VERIFIED_IMMATERIAL | P3 | future_eval |
| LED-03 | ledger / older flatten batches | Eight older flatten batches (1,210 rows, 270,076 USDT) have unmeasured fees and cannot be attributed by the current tool; the 09-09 batch is measured but mixed-asset and double-written | OPEN_MEASURED_MATERIAL | P3 | future_eval |
| LED-05 | ledger / 09-09 crash anchor | The 52 reconstructed rows for the 09-09 12Z crash anchor have not been written back | PENDING_USER_DECISION | P3 | future_eval |
| LED-07 | ledger / anchors.jsonl | Live anchors.jsonl is one row per anchor but mixes halted rows, internal-era fields and capture-time timestamps | OPEN_MEASURED_MATERIAL | P3 | future_eval |
| LED-08 | reader / anchor_report (Telegram) | The per-anchor Telegram report folds unknown fees and fills to zero and uses stale thresholds | OPEN_MEASURED_MATERIAL | P3 | reporting |
| CHK-02 | per-anchor deep check / source | 'guard_twin AGREE' is looked up in the wrong file | DOC_STALE | P3 | reporting |
| CHK-04 | per-anchor deep check / baseline | fund_updates baselines (~353 / ~453) still hold | VERIFIED_IMMATERIAL | P3 | reporting |
| CHK-05 | per-anchor deep check / coverage | The deep-check template predates several live mechanisms and misses their checks | DOC_STALE | P3 | live_trading, reporting |
| DOC-01 | docs / STATE and CLAUDE.md | STATE §1 and CLAUDE.md carry stale executor facts | DOC_STALE | P3 | reporting |

### EXE-01 — Any watchdog trip still flattens 100% of the book; the proportional response W6(c) is not deployed

- **Layer:** executor / watchdog response
- **What is wrong or unverified:** The deployed watchdog maps every trip, including a §4-5b position anomaly on one or two names and §4-7 drift (the classes that fired on our own instrument false positives on 09-09 and 09-12), to the full ladder: halt opening, cancel, flatten every read-back position. The user's 09-12 rule requires a proportionality gate before any book-level response. W6(a)(b) removed the specific E-0912-A false-positive source; W6(c) (proportional response, diff sha256 15d29d99...) is default OFF and is not in ef60f85, awaiting the R-14 ruling. The next reconciliation false positive of any other kind will flatten the whole book again.
- **Evidence:**
  - `~/dl_quant_live/live/watchdog.py:2440-2457 (sha256 7bcc7f1f...)` — ev = evaluate(root, venue_events, ops_stats) ... pos = {r["symbol"]: float(r["venue_position_notional"]) ... ladder = _degradation_ladder(broker, pos, reason, alarm, verbose=verbose)
  - `~/dl_quant_live/live/watchdog.py:478` — out = {"order": ["halt_opening", "flatten", "alert"],
  - `~/dl_quant_live/state/live/watchdog/trip_receipt.json` — "tripped_at": "2026-09-12T12:47:37Z", "triggers": ["§4-5b liquidation/position anomaly on 2 name(s) at the latest reconciled anchor (17 in this window's history)", "§4-7 un-recovered position drift"]
  - `orders.jsonl scan (this audit)` — FLATTEN-20260909T164536Z 243 rows, Σ|filled_notional| 232,756.97 USDT; FLATTEN-20260912T124737Z 255 rows, 235,382.55 USDT
  - `docs/HANDOFF_round4_review_request_2026-09-13.md:22` — W6(c) 比例响应: diff 15d29d99… 字节不变, 仍默认关、不落地
  - `grep 'proportional|W6(c)|PROPORTIONAL' live/watchdog.py` — 0 hits
  - `memory feedback_no_book_level_response_to_instrument_doubt.md` — 全书级响应(平仓/停机)必须过比例门(涉及名义占 gross 份额 + 名数; R-14 冻结 2%/5 名)
- **Status:** PENDING_USER_DECISION
- **Affects:** live_trading
- **Severity:** P1 — One false positive on a single name still flattens the whole book; this has happened twice in four days from our own instruments.
- **Recommended action:** Put R-14 / W6(c) to the user as the next executor decision. Until it lands, have the per-anchor check read §4-5b/§4-7 near-misses (latest anomaly count, unknown bands) so a person sees them before a trip.
- **Method:** VERIFIED

### OPS-01 — The withdrawn σ_fund gross ladder re-arms at the next login: plist still installed, executor reader still active, STATE still says it is live

- **Layer:** ops (launchd) / executor sizing
- **What is wrong or unverified:** The ladder was withdrawn on 09-04 09:5xZ because it hurts returns under the honest dynamic seat. The withdrawal unloaded the job and renamed its state file, but left ~/Library/LaunchAgents/com.hsy.sigma_ladder.plist in place with no disable override. launchd loads that directory at login, so after any reboot or re-login the job writes state/live/sigma_ladder.json again (HH:52 local) and anchor_loop reads it on every external anchor. After 84 consecutive low-dispersion anchors g becomes 0.5 and target gross halves, announced only at INFO. STATE.md:125 still presents the ladder as live. Whether g would flip on reactivation was not computed.
- **Evidence:**
  - `docs/PREREG_deploy_sigma_ladder_2026-09-04.md §6 (sha256 0ceef0d1...)` — 处置: launchd com.hsy.sigma_ladder 卸载; 状态文件移为 sigma_ladder.json.reserve_20260904; 执行器读取端返回 missing ⇒ g=1.0
  - `ls ~/Library/LaunchAgents; launchctl list; launchctl print-disabled gui/501` — com.hsy.sigma_ladder.plist present (sha256 239274a3..., mtime 2026-09-04) and NOT loaded; the only installed plist not loaded; no hsy/dlquant disable override; machine uptime 14 days
  - `~/regime_dash/sigma_ladder.py:6 and docstring` — OUT=os.environ.get('SIGMA_LADDER_OUT', os.path.expanduser('~/dl_quant_live/state/live/sigma_ladder.json')) ... g=1.0 且 p<0.33 连续 ≥84 锚 ⇒ 0.5
  - `~/dl_quant_live/scheduler/anchor_loop.py:1765-1776` — _g, _ginfo = _SLAD.load() ... self.alarm("INFO", f"σ_fund 阶梯低档: g={_g} ...") ... if _is_ext and _g < 1.0: ... target_leverage=external["gross_mult"] * _g
  - `STATE.md:125` — ★ 09-04 09:34Z σ_fund gross 阶梯已上线(执行器 4b8ca20 电池 124/124; 仪表盘作业 com.hsy.sigma_ladder N+52)
- **Status:** OPEN_NOT_MEASURED
- **Affects:** live_trading, reporting
- **Severity:** P1 — A reboot can silently re-enable a withdrawn exposure rule (gross ×0.5) without a user ruling, with only an INFO notice.
- **Recommended action:** User decides how to retire it: move the plist out of ~/Library/LaunchAgents or run launchctl disable gui/501/com.hsy.sigma_ladder; optionally require an explicit config key before the executor accepts a ladder file. Strike the STATE.md:125 banner.
- **Method:** VERIFIED

### EXE-02 — Stop and exit residuals are topped up with taker orders through the chase frame, while the stop clause says maker-only, no chase

- **Layer:** executor / stop exits
- **What is wrong or unverified:** per_name_stop's docstring and trigger message promise a maker-only exit without chasing (policy A). The top-up step puts every partial residual, reduce-only included, into the chase experiment; only the no_chase arm skips, while chase and chase_forced send MARKET reduce-only orders. Policy A ended on 09-01, so the clause text has been false since then; even under policy A the neutrality-forced set and the fallback branches chased. The requote and placement experiments exempt reduce-only orders; chase does not. W9 now routes held stopped longs into flatten_only, which widens this channel. Magnitude so far is small.
- **Evidence:**
  - `live/per_name_stop.py:7-8, :130 (sha256 8fb79dd8...)` — 动作 = 该名并入 untradable 且 target 置 0 ⇒ 走既有 flatten_only 通道(maker-only 出场, reduce-only 标记, 政策 A 不追, 带/EMA 经既有豁免) ... ⇒ flatten_only(maker 出场, 不追), 出场后
  - `live/binance_executor.py:1603-1612, :1863, :1891 (sha256 655839b5...)` — resid = float(p["delta_notional"]) - float(filled.get(sym, 0.0)) [note: no reduce_only filter in this loop] ... if _arm.get(p["symbol"]) == "no_chase": ... "reduce_only": bool(p.get("reduce_only"))}
  - `orders.jsonl 20260901-20260913, topup_taker rows with target_w == 0 (all full exits, not only stops; this audit)` — filled 9 (chase 4, chase_forced 4, no arm 1) ≈ 5,670 USDT; skipped_no_chase_arm 5; skipped_min_notional 54
  - `STATE.md:1 (12:1xZ entry)` — flatten_only 可沿 chase 框架补单而条款写 maker-only 不追(W9 把原被钉住的止损多头接入此通道, 政策待用户裁定)
- **Status:** PENDING_USER_DECISION
- **Affects:** live_trading, future_eval
- **Severity:** P2 — A protective clause behaves differently from its registered text; the stop layer's evaluation and the chase experiment's population both depend on which behaviour is intended.
- **Recommended action:** User chooses: (a) exempt stop/exit residuals from the experiment and always chase them, (b) never chase them, as written, or (c) keep randomising and amend both preregs. Then align the text and add a test.
- **Method:** VERIFIED

### EXE-03 — Executor neutralisation of a net-short producer book flips small shorts to longs; the 撤名残差 alarm blames withheld names for the producer's own net

- **Layer:** executor / reshape
- **What is wrong or unverified:** At 12Z the producer's target was net short 8.46% of its gross. The 11 withheld names were net long (+0.80%), so removing them left −9.26%, which is the figure the alarm attributes entirely to the withheld names. The executor then adds the same amount to every name to restore neutrality, which turned 9 of the producer's small short intents into longs; 8 of them filled long. The research replay uses the same function, so backtests already contain this behaviour; the misattribution sends diagnosis in the wrong direction.
- **Evidence:**
  - `~/wide_shadow/state/target_live/1789300800.json (read-only, this audit)` — Σw -0.069821, Σ|w| 0.825204 ⇒ net -8.46%; withheld 11 names Σw +0.0066 (+0.80%); remainder -9.26%
  - `state/notify_audit.jsonl 12:24:00Z; scheduler/anchor_loop.py:1854-1861` — 撤名残差 -21813.91 USDT = 目标 gross 的 -9.26% (>2%), 由 11 个撤下的名字造成 ... f"撤名残差 {_rs['net_before']:+.2f} USDT ..."
  - `state/live/pilot_log/20260913/anchors.jsonl 12Z reshape` — net_before -21813.91 → net_after -8.2e-12; gross_before 221,039.84 → gross_after 235,547.58
  - `producer weight vs executor target_w, orders A1789302239 (this audit)` — 9 sign flips short→long (1000CAT -0.000283→+0.000039, CFX -0.000040→+0.000358, SAGA -0.000051→+0.000343, ...); 8 filled long: 9.22+19.28+84.18+51.54+46.26+80.71+33.60+52.03 = 376.82 USDT (0.17% of realised gross)
  - `reviewer round 4 §2.5` — 保持排序不等于保持下注方向
- **Status:** PENDING_USER_DECISION
- **Affects:** live_trading, reporting
- **Severity:** P2 — Every anchor with a net-short producer book, the live book takes small positions against the producer's intent; the alarm text misdirects diagnosis.
- **Recommended action:** Fix the alarm to report producer net and withheld-name net separately. Run the reviewer's per-side scaling comparison as a registered experiment before any change.
- **Method:** VERIFIED

### EXE-04 — Reconcile compares window by window, so an unexplained balance vanishes one anchor later (Q6, not coded)

- **Layer:** executor / reconcile
- **What is wrong or unverified:** The next window takes the venue's observed position as its new baseline, so an unexplained residual in window t reads clean at t+1. The cross-window contract is accepted on paper (revision 4) but not implemented, and its priority awaits the user.
- **Evidence:**
  - `docs/PREREG_reconcile_carry_forward_unexplained_2026-09-10.md §0 and header` — 下一窗以场所观察 Q_t 为新基准, 于是窗 t 未解释的余额 ... 在窗 t+1 消失 ... 两门 CLEAN ... 数学已接受, 未落码
  - `docs/PLAN_fix_all_gaps_2026-09-12.md G7` — Q6 跨锚未解释量继承(PREREG 修订 4 未落码) ... 待用户裁定优先级
- **Status:** PENDING_USER_DECISION
- **Affects:** live_trading
- **Severity:** P2 — The reconciliation gate can lose track of a persistent unexplained position change.
- **Recommended action:** User sets priority; implement per the PREREG and validate on a 41-day ledger copy.
- **Method:** VERIFIED

### CFG-03 — The live maker window is 900 s, but STATE.md and the memory index say 180 s is live

- **Layer:** config / execution window (docs)
- **What is wrong or unverified:** k=180 was authorised on 08-10 and rolled back before any anchor ran at 180. Config and the running process use 900 s (dwell ≈ k + 46 s). STATE.md:20 (the 09-13 T3 closure) and memory k_window_180_live.md, which MEMORY.md lists under 在役适用 as 挂单窗180s, both say 180 s is live; chase_closed_at_39.md says k was changed to 180. Any simulation or cost argument built on a 226 s dwell, including T3's 'already acted on' sentence, rests on a parameter that is not deployed.
- **Evidence:**
  - `config/book.json:43 and :121` — "k_seconds": 900, ... ★★ 回滚 180→900, 2026-08-10 02:5xZ, 在任何锚点于 180 下运行【之前】
  - `scheduler/run_anchor.py:339; state/anchor_runs.log` — k = cfg.get("k_seconds", 900) ... 2026-09-13T12:25:07Z k window: sleeping 900s
  - `STATE.md:20` — 已知逆选择族(k 窗 180s 已据此上线; 机会毛额经逐笔重建可捕 ≈0, 重挂/改价族 DO-NOT-RETRY)
  - `memory k_window_180_live.md` — ★★★ 2026-08-10 上线: 挂单等待 900s→180s (commit 40c9e16)
- **Status:** DOC_STALE
- **Affects:** future_eval, reporting
- **Severity:** P2 — The declared source of truth and the session-loaded memory index misstate a live execution parameter, and a research closure has already relied on it.
- **Recommended action:** Correct STATE.md:20 and the two memory notes (180 rolled back, 900 live); re-read the T3 closure sentence that cites it.
- **Method:** VERIFIED

### CFG-04 — Chase 50/50 randomisation is live and hard-coded, before its stop point; rebuild anchors and stop exits now sit inside its population

- **Layer:** config (code constant) / chase experiment
- **What is wrong or unverified:** Policy A (never chase) was replaced on 09-01 by a 50/50 experiment that stops at 100 experimental anchors or 30 days (about 10-01). The knob is a code constant, not a config/book.json key. So far 60 anchors have both arms assigned. The preregistration has no rule for flat-book rebuild anchors: at 12Z today the arms were chase 100 / no_chase 97 / forced 4 names and the no-chase gap was 6,979 USDT (3.0% of gross), far above the registered skip-set envelope of 37-500 USDT per anchor. It also has no rule for stop/exit residuals, which W9 (deployed 12:04Z) now sends through flatten_only into the same population (see EXE-02). Memory chase_closed_at_39.md, listed as current, still describes policy A.
- **Evidence:**
  - `live/chase_policy.py:142-144 (sha256 ff33797c...)` — # 2026-09-01 重启(PREREG_chase_restart_2026-09-01, sha 1a3f433325ae, 用户裁定) ... ARM_WEIGHTS: Dict[str, float] = {ARM_CHASE: 0.5, ARM_NO_CHASE: 0.5}
  - `docs/PREREG_chase_restart_2026-09-01.md (sha256 1a3f4333...)` — 样本停点 n*₂=100 含实验锚 或 30 天先到者 ... 成本自然界: skip 集 37-500U/锚
  - `state/live/pilot_log/2026090*-20260913 anchors.jsonl chase_experiment (this audit)` — 60 anchors with both arms assigned; 12Z A1789302239 arm counts {'chase_forced': 4, 'chase': 100, 'no_chase': 97}
  - `state/anchor_report_last.json 12:55Z` — gross 227672 net -1320(-0.58%) gaps 6979U
- **Status:** PENDING_USER_DECISION
- **Affects:** live_trading, future_eval
- **Severity:** P2 — The experiment's population changed mid-run (rebuild anchors, exits); without a registered handling rule its readout can be argued either way.
- **Recommended action:** Before anyone looks at arm differences, add a prereg amendment on how rebuild anchors and target-0 exits are treated (exclude or stratify). Correct the memory entry.
- **Method:** VERIFIED

### CFG-06 — Placement bandit eps 0.50 was adopted on a 'not toxic' finding that a later receipt voided; the config basis was not updated and no re-read is scheduled

- **Layer:** config / placement bandit
- **What is wrong or unverified:** eps went 0.35 → 0.50 on 09-01 on ΔV > 0 and 'not toxic'. The 09-05 causal review found behind fills more toxic on full-coverage markout (Δ −5.28 bps, CI below zero), voided the 09-01 'not toxic' sentence, and kept 0.50 'without expanding' pending a full-coverage re-read. The config _basis still carries only the 09-01 reasoning, and CRON_TEMPLATES lists the 0.50 re-read as done on 09-04, before the voiding. Half of attempt-1 makers are still placed one tick behind.
- **Evidence:**
  - `config/book.json:129 placement_bandit` — "eps": 0.5, ... 2026-09-01 恰一次主判(RESULT_placement_bandit_read, n=2129): ΔV +1.658 ... 且不毒; 用户字采纳 eps 0.35→0.50
  - `STATE.md:158` — 全覆盖 markout60 behind −7.69 vs join −2.40, Δ −5.28 [−14.19, −0.33] ⇒ 09-01 '不毒'句作废) ⇒ 维持 eps 0.50 不扩大, 0.50 稳定性复读改用全覆盖口径
  - `docs/CRON_TEMPLATES_2026-09-04.md:9` — bandit eps0.50 稳定性复读 | 已于 09-04 13:3xZ 完成(安全线 PASS 57.5%; ...)
  - `ops/assert_anchor_artifacts.py:314` — # e-greedy ε frozen at 0.35 by PREREG f657efde —
  - `live/placement_bandit.py:8; orders.jsonl 20260910-20260912 maker attempt-1 rows (this audit)` — sha1(f"{rebalance_id}:{symbol}") 末字节 < round(eps*256) → behind ... behind 2,365 / join 2,426 / exempt 58 (behind share 0.494)
- **Status:** PENDING_USER_DECISION
- **Affects:** live_trading, future_eval
- **Severity:** P2 — A live execution setting whose adoption rationale is half withdrawn, with no dated re-read.
- **Recommended action:** Register the full-coverage re-read (date, n, criterion) or return eps to the user; update _basis and the stale 0.35 comment.
- **Method:** VERIFIED

### ALM-03 — factor_health still polls the retired jpline report every anchor; the artefact assertion for decay monitoring passes vacuously; W5 has not landed

- **Layer:** monitor / factor_health
- **What is wrong or unverified:** The consumer ssh-reads a report that stopped being published on 08-06 and records UNKNOWN at INFO each anchor. Artefact assertion #9 treats that absence as a pass. The repoint to the in-book ic_monitor ledger (W5) is designed but not in ef60f85. The in-book monitor (#55, W1 deployed today) runs daily at 01:30Z; its first post-deploy evaluation is 09-14 01:30Z.
- **Evidence:**
  - `ops/check_factor_health.py:53, :109 (sha256 f6d028fc...)` — REMOTE = ("jpline", ... subprocess.run(["ssh", "-o", "BatchMode=yes",
  - `state/factor_health_last.json; state/alarm_episodes/factor_health.json` — "reason": "report_unreachable", "decay_judged": false ... episode 68f039b2261f3dff at 2026-09-04T12:45:15Z
  - `ops/assert_anchor_artifacts.py:297-300` — _fh_absent = not fh or fh.get("reason") in ("report_unreachable",) or fh.get("as_of") is None ... add("decay monitored on the deployable caliber", bool(fh.get("decay_judged")) or _fh_absent,
  - `grep ic_monitor_evals ops/check_factor_health.py ops/assert_anchor_artifacts.py` — 0 hits (docs/DESIGN_factor_health_repoint_2026-09-12.md W5 not deployed)
  - `~/Library/LaunchAgents/com.dlquant.live.icmonitor.plist` — StartCalendarInterval Hour 9 Minute 30 (local = 01:30Z)
- **Status:** PENDING_USER_DECISION
- **Affects:** live_trading, reporting
- **Severity:** P2 — A per-anchor gate reports PASS for a monitor that has watched nothing since 08-06.
- **Recommended action:** Land W5 with its §5 corrections after W1's first ledger exists, or relabel assertion #9 as a declared gap.
- **Method:** VERIFIED

### LED-02 — 09-12 protective flatten: 255 order rows without fees and no fills rows; the backfill is an operator step that has not run

- **Layer:** ledger / 09-12 flatten costs
- **What is wrong or unverified:** The batch has no fills rows at all, so fills-based tools (for example pilot_journal/tools/inspect_anchor.py commission-by-asset, or any fill-level fee or markout study) see zero commission for it. Order-layer readers mark it correctly as not measured: m1 excludes protective_flatten from c and reports its fee as None; the three-bucket readers classify all 255 rows as unpriced (no anchor mid), so they will still not price it after the fee backfill, which writes fills rows only. Venue truth is already in the post-fix income-based daily_nav row and in guard_twin's income ledger. The backfill's report mode is not offline: it arms the broker and queries allOrders/userTrades, so it needs credentials and a user word.
- **Evidence:**
  - `state/live/pilot_log/20260912/orders.jsonl (this audit)` — rebalance_id FLATTEN-20260912T124737Z: 255 rows, fee_paid None 255, Σ|filled_notional| 235,382.55 USDT
  - `state/live/pilot_log/20260912/fills.jsonl (this audit)` — order_type counts maker 1,698, topup_taker 782, protective_flatten 0
  - `live/cost_buckets.bucket_fills (sha256 0d31d10a...) run on a scratch copy over those 255 rows` — n_unpriced 255, n_measured 0, bps_measured None, measurement_complete False
  - `live/pilot_metrics.py:100-102` — _flat = [o for o in orders if o.get("order_type") == "protective_flatten"] ... orders = [o for o in orders if o.get("order_type") in ("maker", "topup_taker")]
  - `ops/anchor_report.py:78` — if o.get("rebalance_id") == rb: O.append(o)  [note: FLATTEN-<ts> rows never match an anchor rid]
  - `state/live/pilot_log/20260912/daily_nav.jsonl 16:39Z` — realised_by_type COMMISSION -128.846 (income ledger, after the E-0909-H fix)
  - `docs/DESIGN_reduce_only_clamp_identity_2026-09-12.md §6.7` — 「只报告」模式不是离线的 —— find_gaps 一旦找到缺口, run() 就 BinanceBroker(mode).arm() 并对每个缺口调 allOrders / userTrades
- **Status:** PENDING_USER_DECISION
- **Affects:** future_eval, reporting
- **Severity:** P2 — The incident's execution cost cannot be read from the executor's own ledgers until backfilled; NAV-based P&L already includes it.
- **Recommended action:** When the user authorises: LIVE_MODE=LIVE ops/backfill_fills.py --day 20260912 report, then --apply, then confirm. Until then cost the incident from the income ledger.
- **Method:** VERIFIED

### LED-04 — daily_nav realised P&L by type is under-recorded from 07-29 to 09-12 06:05Z (twin income rows dropped, BNB fees summed raw); fixed going forward only

- **Layer:** ledger / daily_nav realised P&L
- **What is wrong or unverified:** income_since de-duplicated on tranId alone from 07-29. A trade's COMMISSION and REALIZED_PNL rows share a tranId, so one of the two was dropped. While fees were paid in BNB (08-12 to 09-04 in the fills ledger), the COMMISSION field also holds raw BNB amounts, and roughly half of them. b681ca5 (deployed 09-12 06:05Z) fixed the key and split by asset; rows written before that stay as written. Totals are unaffected: NAV and equity come from the account endpoint and cond2 judges the equity change. guard_twin's own income ledger uses a five-field key and closes to the wallet within 0.001 USDT, so it is a correct source for the split.
- **Evidence:**
  - `git show 75106a9 -- live/binance_broker.py (2026-07-29)` — k = r.get("tranId") or json.dumps(r, sort_keys=True)
  - `live/binance_broker.py:2010-2026 (ef60f85)` — ★ DEDUPE ON (tranId, incomeType, symbol, asset) — NOT on tranId alone.
  - `~/guard_twin/state/income.jsonl (this audit)` — 109,545 rows; 24,723 tranIds shared by a COMMISSION and a REALIZED_PNL row of the same symbol; FUNDING_FEE rows share none
  - `daily_nav vs fills (this audit)` — 20260911 last row COMMISSION -8.891 vs fills USDT commission 18.141 (2,025 trades, deduplicated); 20260910 -61.553 vs 67.707
  - `state/live/pilot_log/20260906` — daily_nav COMMISSION -0.00305 while all 800 fills that day paid commission in BNB
  - `state/live/pilot_log/20260830 and 20260904 (this audit)` — fills BNB commission 0.0051 vs daily_nav COMMISSION -0.00241; 0.0107 vs -0.00520 (BNB amounts, about half, labelled as USDT)
  - `~/guard_twin/state/latest.json` — "closed_account_gap_usdt": 0.0010691600909922272
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** future_eval, reporting
- **Severity:** P2 — Any fee/realised split of the live period read from daily_nav is wrong for about 45 days.
- **Recommended action:** For live-performance evaluation, take totals from NAV plus external_flow and the fee/funding/realised split from guard_twin income.jsonl (or a fresh 4-key income pull); mark daily_nav.realised_by_type before 2026-09-12T06:05Z as unreliable in the evaluation notes.
- **Method:** VERIFIED

### LED-06 — The ledger notary has produced no valid hash chain and no third-party timestamp since 08-31

- **Layer:** ledger integrity / notary
- **What is wrong or unverified:** Every automated manifest since 08-31 records prev_manifest_sha256 'GENESIS' (the glob of earlier manifests came back empty) and git add then fails with 'Operation not permitted', so none of the 13 manifests was committed or pushed. The likely cause is that the launchd job is denied access to the Desktop folder, which is where the research repo lives (inferred from the error, not tested). The script would also push multi-asset-v2 whatever branch is checked out. Separately, fills.jsonl is legitimately appended after notarisation (backfills), so manifests no longer match current files on most days.
- **Evidence:**
  - `ledger_notary/manifest_20260831.json ... manifest_20260912.json` — 13 files, all "prev_manifest_sha256": "GENESIS"; untracked in git; 0801-0830 committed in 117e9871
  - `ops/notarize_ledgers.py:19-21, :45, :50 (sha256 6a8d1769...)` — ms = sorted(glob.glob(os.path.join(NOTARY, "manifest_*.json"))) / return sha(ms[-1]) if ms else "GENESIS" ... ["git", "-C", RESEARCH, "add", "ledger_notary"] ... "push", "-q", "origin", "multi-asset-v2"
  - `~/dl_quant_live/state/notary.log` — fatal: Unable to read current working directory: Operation not permitted ... CalledProcessError: Command '['git', '-C', '/Users/haosiyu/Desktop/quant_research', 'add', 'ledger_notary']' returned non-zero exit status 128.
  - `sha256 of current ledger files vs manifests (this audit, guarded read)` — fills.jsonl differs on 20260830, 20260909, 20260911, 20260912; all 7 files match on 20260906
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** reporting
- **Severity:** P2 — The tamper-evidence claim does not hold for the live period since 08-31, and legitimate backfills would read as tampering.
- **Recommended action:** Run the notary where it can read the repo (or write manifests outside iCloud), chain from the last committed manifest, notarise after backfills settle or hash a backfill-aware digest, commit to the intended branch. User decides whether to publish late manifests for 08-31..09-12.
- **Method:** VERIFIED

### CHK-01 — Deep-check baseline 'counterfactual rewrite 19-20% since 09-03' is stale; the level is about 27% and rose about 6 pp in four days

- **Layer:** per-anchor deep check / baseline
- **What is wrong or unverified:** Measured with the same formula the journal tool uses. The escalation rule (three consecutive anchors above +0.2 pp) was met on 09-12 while the book was flat; 'up another step' is undefined.
- **Evidence:**
  - `docs/CRON_TEMPLATES_2026-09-04.md:13` — 反事实改写幅度(target_live_king vs target_live; 09-03 08Z 起新台阶 19-20%, 判据=level 再升一档或连续3锚增量>+0.2pp 才升级)
  - `Σ|w_live−w_king|/Σ|w_king| over ~/wide_shadow/state/target_live{,_king}/<A>.json (inspect_anchor.py formula; this audit)` — 09-03 08Z 17.21 · 09-05 20Z 20.50 · 09-09 12Z 21.34 · 09-11 12Z 24.60 · 09-12 12Z 25.36 · 16Z 25.99 · 20Z 26.58 · 09-13 00Z 27.10 · 04Z 27.46 · 08Z 27.20 · 12Z 27.17
- **Status:** DOC_STALE
- **Affects:** live_trading, reporting
- **Severity:** P2 — The per-anchor escalation call is anchored to a level from ten days ago.
- **Recommended action:** Replace the fixed level with a trailing 42-anchor median and band from inspect_anchor.py; define what a 'step' is.
- **Method:** VERIFIED

### CHK-03 — Deep-check baseline 'maker share ≥90%' no longer holds; the execution mix changed after 09-02 and nobody has attributed it

- **Layer:** per-anchor deep check / baseline
- **What is wrong or unverified:** Maker share by notional stayed above 0.90 through 09-02 and has run 0.56-0.89 per anchor since 09-08. Fee rates themselves are unchanged (maker 2.00, taker 5.00 bps), so each +10 pp of taker share adds 0.3 bps of fees per unit traded. Candidate causes, not measured: the chase 50/50 restart (09-01 16Z) and the requote direct arm (09-05 12Z).
- **Evidence:**
  - `docs/CRON_TEMPLATES_2026-09-04.md:13` — fills maker 占比(≥90%), 换手(稳态2-5.5%), 费用 bps(maker 1.80-2.3 带)
  - `fills.jsonl deduplicated by trade_id, maker+topup legs (this audit)` — daily maker share 08-28..09-02: 0.943, 0.914, 0.948, 0.924, 0.916, 0.902; per anchor 09-08..09-12: 0.559-0.889 except anchors without top-ups (1.0); 09-13 12Z rebuild 0.686; maker fee 2.00 bps and taker 5.00 bps (USDT) on every anchor
  - `state/anchor_report.log` — taker-share warning on 51 of 101 reports
- **Status:** DOC_STALE
- **Affects:** future_eval, reporting
- **Severity:** P2 — A stale baseline hides a real, unattributed shift toward taker execution.
- **Recommended action:** Attribute taker notional by source (from_reject direct arm, chase arm, chase_forced) for 09-02..09-12, then reset the baseline per source.
- **Method:** VERIFIED

### EXE-05 — Reviewer item: the broker's direct GET read path does not adopt the capacity-conflict contract, but no caller reads the affected field

- **Layer:** executor / broker read path (reviewer item)
- **What is wrong or unverified:** The GET fallback runs in live when a response lacks cumQuote/avgPrice (observed on flatten legs). In the reviewer's synthetic case the path returns a stale clamped.venue 8 next to the correct final executed_qty 6. Callers read only notional, price, time, order id, status and executed quantity; none reads clamped from this path. Maker settlement uses venue_fills, which does record capacity conflicts. A MARKET order's origQty changing between POST and GET is judged implausible (not verified against the venue).
- **Evidence:**
  - `live/binance_broker.py:1600, :1614` — if not float(resp.get("cumQuote") or 0.0) or not float(resp.get("avgPrice") or 0.0): ... out["clamped"] = dict(_clamp["clamped"])       # E-0912-A: the re-query showed the clamp
  - `live/venue_fills.py:1039-1041` — ONE leg per flatten comes back with `executedQty > 0` and no `cumQuote`/`avgPrice`
  - `callers: live/binance_executor.py:946-968, :1928-1968; live/binance_broker.py:1804-1822` — note_exit_fill reads filled_notional/avg_fill_px/fill_ts; top-up reads filled_notional/status/executed_qty/executed_qty_final; flatten_all reads filled_notional/avg_fill_px/fill_ts/order_id
  - `live/binance_executor.py:1572-1578` — if d.get("capacity_conflict"): ... p.pop("venue_clamped", None)  [note: settlement path, fed by venue_fills]
  - `reviewer incident/RESULT.md` — 原函数输出仍 clamped.venue=8、executed_qty=6、executed_qty_final=True、没有capacity_conflict
- **Status:** VERIFIED_IMMATERIAL — resolution: The one wrong field is unread by every caller, and the quantities callers do read are right in the reviewer's counterexample.
- **Affects:** reporting
- **Severity:** P3 — Latent for any future caller of clamped from this path.
- **Recommended action:** Add a test that no caller consumes clamped from last_fill_details, or adopt the contract the next time the file changes.
- **Method:** VERIFIED

### EXE-06 — Reviewer item: a JSON-array line in watchdog events.jsonl makes the battery and an ops tool raise; the live anchor never reads that file

- **Layer:** battery and ops parsers (reviewer item)
- **What is wrong or unverified:** Both parsers catch only ValueError/TypeError and then call .get on the parsed line. A list raises AttributeError. The watchdog only appends to events.jsonl. The failure is closed (battery red, tool aborts) and needs outside corruption of the file.
- **Evidence:**
  - `live/tests_disposition_matrix.py:672-692 (sha256 874b354a...)` — except (ValueError, TypeError): continue ... for a in (ev.get("actions") or ()):
  - `ops/rejudge_ledger_rows.py:53-56, :67-73` — return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()] ... for ev in _rows(events_path): ... for a in ev.get("actions") or ():
  - `live/watchdog.py:2538; grep events.jsonl over live/ scheduler/ ops/` — with open(os.path.join(sdir, "events.jsonl"), "a") as f:  [note: append only; the only parsers are the battery suite and the manual rejudge tool]
- **Status:** VERIFIED_IMMATERIAL — resolution: Not reachable from the live anchor; fails closed in the battery and in the manual tool.
- **Affects:** reporting
- **Severity:** P3 — Could block a deploy, cannot pass silently or affect trading.
- **Recommended action:** Catch AttributeError and name the line NOT_OBSERVABLE in both parsers.
- **Method:** VERIFIED

### EXE-07 — Reviewer item: reconcile's clamp re-derivation reads only the first origQty pair; no multi-reason strings exist or can be written now

- **Layer:** executor / reconcile (reviewer item)
- **What is wrong or unverified:** The reason check requires every part to be the origQty kind, but the numbers are taken from the first match only. No such multi-reason string exists in the ledger, and the current writer records a reduce-only clamp as a fourth state instead of a contradiction string; remaining origQty strings are non-clamp mismatches that the gates leave standing.
- **Evidence:**
  - `live/reconcile.py:148-165, :200 (sha256 df6dcf69...)` — _origqty_reasons ... if not parts or not all(_is_identity_origqty_kind(p) for p in parts): return None ... m = _ORIGQTY_PAIR.search(str(why or ""))
  - `orders.jsonl 20260801-20260912 scan (this audit)` — 2 request-level inconsistent strings (the E-0912-A rows), each with one reason; 0 with more than one origQty pair
  - `live/binance_broker.py:391-399` — _cl = reduce_only_clamp(rec, expected, reduce_only) ... if _cl is not None: ... return None ... return f"{what} {key} {v} differs from ours {expected}"
- **Status:** VERIFIED_IMMATERIAL — resolution: Unreachable from the current writer and absent from the ledger.
- **Affects:** live_trading
- **Severity:** P3 — Theoretical only.
- **Recommended action:** When reconcile.py is next touched, reject strings carrying more than one numeric pair.
- **Method:** VERIFIED

### EXE-08 — The running executor is exactly the reviewed four-patch tree, and the 12Z anchor ran it

- **Layer:** executor / deployment identity
- **What is wrong or unverified:** Deployment identity is proven by the git tree hash and by byte-identical files; the 12Z process imported the patched files (they were on disk before it started) and wrote a W9-only field. This confirms identity, not behaviour on events that have not happened yet: the held-and-stopped W9 path was not exercised by a rebuild from flat.
- **Evidence:**
  - `git -C ~/dl_quant_live rev-parse ef60f85^{tree}` — ed2f881989e164a8d0de75fb00a698e674d011df (equals the tree the reviewer computed independently); HEAD = origin/main = ef60f85; tracked code unmodified (git status shows only state/ files and untracked rollback_*/staging_* dirs, which no script references)
  - `sha256 of running files vs reviewer's frozen W6ab copies` — binance_executor.py 655839b5..., binance_broker.py 13be0871..., reconcile.py df6dcf69..., venue_fills.py 884f2238..., tests_disposition_matrix.py 874b354a... (all equal)
  - `file mtimes; state/anchor_runs.log; git log` — patched files 2026-09-13T11:46:19Z < '2026-09-13T12:00:00Z anchor start mode=LIVE' < commit 12:04:14Z; 'anchor done rc=0' 12:58:30Z
  - `scheduler/anchor_loop.py at 918559f vs ef60f85; 12Z anchors row` — reshape key forced_flat_names: 0 occurrences at 918559f, present at ef60f85 and in the 12Z row
  - `git merge-base --is-ancestor b681ca5 ef60f85; state/anchor_runs.log` — true (E-0909-D/E/H, E-0910-A fixes present); metrics_freeze: FROZEN_MATCH sha=5ac7b16d0f97f2f8 (= live/pilot_metrics.py sha256 5ac7b16d...)
- **Status:** FIXED_DEPLOYED
- **Affects:** live_trading
- **Severity:** P3 — Informational confirmation.
- **Recommended action:** None. The first anchor with a held-and-stopped name still needs the W9 disposition check.
- **Method:** VERIFIED

### OPS-02 — The killed execution probe's launchd job is still loaded with RunAtLoad; only KILL files keep it from starting

- **Layer:** ops (launchd) / execution probe
- **What is wrong or unverified:** The probe refuses to start while either KILL file exists. Removing a KILL file would revive a probe that once flattened book positions.
- **Evidence:**
  - `~/Library/LaunchAgents/com.hsy.execprobe2.plist; launchctl list` — "RunAtLoad" => true; job loaded, last exit 3
  - `~/exec_probe/v2/probe.out; ls` — KILL file present (['/Users/haosiyu/exec_probe/KILL', '/Users/haosiyu/exec_probe/v2/KILL']) — refusing to start.
  - `STATE.md §1` — 执行探针已 KILL(勿复活)
- **Status:** VERIFIED_IMMATERIAL — resolution: The KILL guard holds today.
- **Affects:** live_trading
- **Severity:** P3 — Guarded; single point of protection.
- **Recommended action:** Unload and move the plist out of ~/Library/LaunchAgents.
- **Method:** VERIFIED

### OPS-03 — The 12Z flat-to-full rebuild ran at 99% of the self-imposed weight budget

- **Layer:** ops / request budget at rebuild
- **What is wrong or unverified:** No trip occurred, but the headroom was about 1%. The 08-26 one-step 2.0× rebuild that hit 1005/1000 produced 157 null-submit rejects and a §4-5e trip. The 85 venue_reject rows of this anchor were not classified here.
- **Evidence:**
  - `state/anchor_runs.log 12:58:29Z` — rate_budget[fapi.binance.com]: weight=9665 requests=1662 orders=549 peak/min w=990 r=304 o=273
  - `live/rate_budget.py:38-39` — WEIGHT_PER_MIN = 1000 / ORDERS_PER_MIN = 300
  - `state/anchor_runs.log 12:58:30Z` — venue_rate: ... peak_used_weight_1m=1270 peak_order_count_1m=262
  - `config/book.json:172 _gross_mult_note` — §4-5e 触发根因=2.0×一步建仓的提交风暴撞速率顶(peak weight 1005/自限1000, 157张null-submit拒单)
- **Status:** OPEN_NOT_MEASURED
- **Affects:** live_trading
- **Severity:** P3 — Nothing broke; the next full rebuild has thin margin.
- **Recommended action:** In the 12Z acceptance, split the 85 rejects by code (-5022 vs null-submit/-1003); consider a staged-rebuild rule for future resumes.
- **Method:** VERIFIED

### CFG-01 — Gross and leverage match the latest ruling (2.0 × NAV)

- **Layer:** config / leverage
- **What is wrong or unverified:** No contradiction. Config and the running anchor agree on 2.0 × NAV. Two notes are out of date: the gross_mult note stops at the 1.75 step, and STATE §1 still quotes NAV ≈ 20.4k.
- **Evidence:**
  - `config/book.json:66 and :160 (sha256 f6fd6d0e...)` — "target_leverage": 2.0, ... "gross_mult": 2.0,
  - `state/anchor_runs.log, 12Z anchor A1789302239 phase_A sizing` — "nav": 117773.7916358, "target_leverage": 2.0, "leverage_source": "external_book.gross_mult"
  - `STATE.md §1` — gross = 2.0 × NAV(08-26 用户令升档; NAV ≈ 20.4k, 08-27 入金后)
  - `config/book.json:172 _gross_mult_note` — 1.75(2026-08-27 01:0xZ 爬坡第二档; ...) 1.5(2026-08-26 13:3xZ 分级爬坡恢复第一步; ...
  - `state/live/pilot_log/20260913/daily_nav.jsonl 12:45Z row` — nav 117566.70
- **Status:** VERIFIED_IMMATERIAL — resolution: Values are consistent across config, STATE and the running process; only the notes are stale.
- **Affects:** reporting
- **Severity:** P3 — Documentation only.
- **Recommended action:** Add the 2.0 step to _gross_mult_note; refresh the NAV figure in STATE §1.
- **Method:** VERIFIED

### CFG-02 — per_name_stop profile matches STATE (wide d30_n2_c42, floor 5 USDT); the profile's basis text still says 20 USDT

- **Layer:** config / per-name stop
- **What is wrong or unverified:** Active values are right. The wide profile's _basis string still says the floor stays at 20 USDT pending a ruling, while the value (and the redteam note beside it) is 5 USDT.
- **Evidence:**
  - `config/book.json:140, :144, :147` — "active_profile": "wide", ... "depth_pct": -0.3, ... "min_notional_usdt": 5.0,
  - `config/book.json:148 profiles.wide._basis` — min_notional_usdt 沿用 20(★ 待裁: L1 1×NAV/~300 名中位 ≈40 USDT, 20 以下的小仓条款看不见)
  - `STATE.md §1` — 逐名 wide 档 d30_n2_c42(depth −0.30×2锚×7d)
- **Status:** DOC_STALE
- **Affects:** reporting
- **Severity:** P3 — Text only; the executor reads the value.
- **Recommended action:** Correct the _basis string at the next config commit.
- **Method:** VERIFIED

### CFG-05 — Requote randomisation (p_requote 0.5) is live and experimental; readout not before 09-19 00Z

- **Layer:** config / requote experiment
- **What is wrong or unverified:** The readout needs 14 natural days and at least 1,500 direct-arm plans, then the first 00Z anchor, once. Halts on 09-06, 09-09 and 09-12 to 09-13 (24 h) slowed direct-arm accrual. Reduce-only orders are exempt, so the W6/W9 changes do not enter its population. The requote mechanism itself (08-06, E-0905-I) has no ruling beyond this experiment.
- **Evidence:**
  - `config/book.json:124` — "p_requote": 0.5,
  - `docs/PREREG_requote_randomised_2026-09-05.md §1-§2 (sha256 41c966f4...)` — reduce_only 一律 exempt ... 读数点: 部署满 14 个自然日 且 direct 臂累计 ≥ 1,500 个计划(两者皆满足后的首个 00Z 锚), 恰一次主判
  - `state/anchor_runs.log 12Z requote report` — "p_requote": 0.5, "n_direct": 27, "n_exempt": 0
- **Status:** PENDING_USER_DECISION
- **Affects:** live_trading, future_eval
- **Severity:** P3 — Running as registered; only the readout date moves.
- **Recommended action:** Track the direct-plan count at the daily check; at readout, state the halted days explicitly.
- **Method:** VERIFIED

### CFG-07 — Internal-book keys are inert in external mode; the config header still says the deployed book is three legs

- **Layer:** config / internal-book keys
- **What is wrong or unverified:** weights/signs, harvest_ema, no_trade_band_w, risk_budget and leg_cadence apply only to the retired internal composer. The file's first line still declares the deployed book to be the three-leg internal book.
- **Evidence:**
  - `config/book.json:2` — "_comment": "DEPLOYED BOOK = THREE LEGS (king/s2/funding); the size leg is REMOVED ..."
  - `config/book.json:153 and _book_source_note` — "book_source": "external" ... 'external' = 目标向量从 external_book.path/<anchor_ts>.json ... 读取; 不经 compose_book/风险预算/EMA/中性带
  - `scheduler/anchor_loop.py:1874-1880` — if _is_ext: ... _nb = {"applied": False, "skipped": "external_book", ...
- **Status:** DOC_STALE
- **Affects:** reporting
- **Severity:** P3 — Misleads a reader of the config, not the executor.
- **Recommended action:** Rewrite _comment to name the external combo book and mark internal-only keys.
- **Method:** VERIFIED

### CFG-08 — The executor does not pin the producer's booster or universe; today's booster matches STATE

- **Layer:** config / producer identity
- **What is wrong or unverified:** Both pins are null, so the executor would trade a target file from a different booster or universe without refusing. Today the recorded booster equals the one STATE lists.
- **Evidence:**
  - `config/book.json:162-163` — "universe_sha_pin": null, "booster_sha_pin": null,
  - `state/anchor_runs.log 12Z external_book record` — "booster_sha": "8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282"
  - `STATE.md §1` — king booster = slow2026(bundle v3 同日换装, booster_sha 8d79186b)
- **Status:** VERIFIED_IMMATERIAL — resolution: The booster in service equals the approved one today; the missing pin is defence in depth, not a present error.
- **Affects:** live_trading
- **Severity:** P3 — No mismatch today.
- **Recommended action:** Consider pinning booster/universe at the next approved bundle change (monthly retrain).
- **Method:** VERIFIED

### STA-01 — Watchdog state is clean after the resume; the trip receipt is write-only; a transfer today would not re-trip

- **Layer:** state / watchdog
- **What is wrong or unverified:** No halt or reduce-only residue remains. trip_receipt.json from 09-12 is an audit record with no reader. If today became a transfer day, cond2 would fall back to 09-12, which was a positive day.
- **Evidence:**
  - `state/live/watchdog/state.json (12:46Z)` — {"reduce_only": false, "tripped_at": null, "_mode": "LIVE"}
  - `state/live/watchdog/last_eval.json` — evaluated_utc 2026-09-13T12:46:53Z, tripped False, triggers [], cond2 recent_day 20260913 recent_day_pct -0.1807
  - `scheduler/run_anchor.py:698-704; grep trip_receipt in live/ scheduler/ ops/` — only writer is run_anchor; no reader
  - `daily_nav last rows` — 20260912 20:39Z nav 117,779.56 vs 20260911 20:45Z nav 117,515.79 ⇒ +0.22% (the day cond2 would judge if 09-13 became a flow day)
- **Status:** VERIFIED_IMMATERIAL — resolution: No residual halt state; the flow-day fallback currently points at a positive day.
- **Affects:** live_trading
- **Severity:** P3 — Checked clean.
- **Recommended action:** None beyond the standing no-transfer reminder.
- **Method:** VERIFIED

### STA-02 — per_name_stop.json is consistent after the rebuild; routine cooldown expiries page the user at HIGH

- **Layer:** state / per-name stop
- **What is wrong or unverified:** Three names remain in cooldown; counters and stopped sets are empty after the flat period. Seven expiries at 12:45Z each sent a HIGH page. The same seven names were still withheld at 12:24Z because expiry is evaluated in phase C, so they sat out one extra anchor.
- **Evidence:**
  - `state/live/per_name_stop.json (12:45Z)` — cooldown IOSTUSDT 1789835943 (09-19 16:39Z), LSKUSDT 1789821947 (09-19 12:45Z), XANUSDT 1789591142 (09-16 20:39Z); counters {}; stopped {}
  - `state/notify_audit.jsonl 12:45:49-12:45:55Z` — 7 × HIGH DELIVERED "per_name_stop: <SYM> 冷却期满, 恢复可入" (COLLECT, CYS, FLOCK, HEMI, MAGMA, RIVER, TRIA)
- **Status:** VERIFIED_IMMATERIAL — resolution: Table content follows the clause; the HIGH tier for a routine expiry is notification noise, not a trading effect.
- **Affects:** reporting
- **Severity:** P3 — Seven phone pages for a benign event.
- **Recommended action:** Route cooldown expiry to INFO or the daily summary.
- **Method:** VERIFIED

### STA-03 — state/live/no_trade_band.json (last written 08-22 04:00Z) and the harvest EMA state have no reader in external mode

- **Layer:** state / retired internal-book state
- **What is wrong or unverified:** The band file is written only inside the internal-book branch, which external mode skips, and nothing reads it. The live harvest_ema.json is absent (resume removes it). Both would matter only if book_source returned to internal, which needs a user ruling.
- **Evidence:**
  - `state/live/no_trade_band.json` — "rebalance_id": "A1787371250" (= 2026-08-22 04:00:50Z, last internal-book anchor)
  - `scheduler/anchor_loop.py:1874-1880 and :1896` — if _is_ext: ... "skipped": "external_book" ... else: ... _save(os.path.join(os.path.dirname(_hp), "no_trade_band.json"), ...
  - `grep no_trade_band.json over live/ scheduler/ ops/ ~/guard_twin ~/regime_dash` — no reader
  - `ops/resume_from_trip.sh:102, :302` — HARVEST=... harvest_ema.json ... no harvest_ema.json (EMA memory already clean)
- **Status:** VERIFIED_IMMATERIAL — resolution: Inert remnants of the retired internal book.
- **Affects:** reporting
- **Severity:** P3 — No reader.
- **Recommended action:** Archive or rename with a .retired suffix at the next state clean-up.
- **Method:** VERIFIED

### ALM-01 — The funding_span STALE alarm is true about the executor's own frozen DL panel, cannot move the traded book, and its text and fingerprint are wrong

- **Layer:** alarm / funding_span
- **What is wrong or unverified:** config/funding_span_table.json (140 names, built 07-25) feeds only the executor's internal DL panel and preds and internal-branch guards. In external mode the book comes from the producer's target file, freshness ignores preds, and the funding ledger reads venue income and the venue's own intervals, not this table. The HIGH text says the funding leg of these names is smoothed over the wrong number of settlements, which is not true of the traded funding leg. The episode fingerprint reads keys ours/venue while the record uses ours_h/venue_h, so it stores 'SYM:None->None' and only notices set changes. DEFAULT_INTERVAL_H is defined but unused, so table names missing from the venue list are not compared (possible undercount, not verified).
- **Evidence:**
  - `state/anchor_runs.log 12:47:01Z` — funding_span: STALE ours=140 venue=782 stale=15 absent_from_venue=13 built_at=2026-07-25T23:17:59+08:00
  - `ops/check_funding_span.py:73, :99, :107, :39 (sha256 2c9e5e5e...)` — "stale": [{"symbol": s, "ours_h": o, "venue_h": v} ...] ... _f = [f"{x['symbol']}:{x.get('ours')}->{x.get('venue')}" ...] ... 这些名字的 funding 腿在按错误的结算次数做 EMA ... DEFAULT_INTERVAL_H = 8.0
  - `state/live/alarm_episodes/funding_span.json` — "findings": ["ANKRUSDT:None->None", "AXSUSDT:None->None", ...]
  - `signal/live_panel.py:55; scheduler/anchor_loop.py:1206; live/binance_funding.py:354` — return sorted(FP.load_span_table().keys()) ... The preds file is not consulted for freshness ... def venue_funding_intervals(broker)
- **Status:** VERIFIED_IMMATERIAL — resolution: No path from the span table to the external target, sizing or the funding ledger; the alarm describes a panel that no longer decides trades. Text and fingerprint defects remain.
- **Affects:** reporting
- **Severity:** P3 — Wrong wording and fingerprint on a non-trading input.
- **Recommended action:** Reword as 'executor internal DL panel (not traded)', fix the key names, or retire the check with the internal book.
- **Method:** VERIFIED

### ALM-02 — cond2.judged_on hard-codes 2026-09-06

- **Layer:** alarm text / watchdog
- **What is wrong or unverified:** The watchdog record says it judges the most recent priced day '(2026-09-06)' while the judged day is 09-13. Same family as the research-side flow-day text fixed in 74b2acb5.
- **Evidence:**
  - `live/watchdog.py:1302` — "judged_on": "most recent priced day (2026-09-06); worst_day_pct is history",
  - `state/live/watchdog/last_eval.json 12:46:53Z` — recent_day 20260913; judged_on most recent priced day (2026-09-06); worst_day_pct is history
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** reporting
- **Severity:** P3 — Wrong text in the stop-loss record; the judged number is right.
- **Recommended action:** Render the date from recent_day.
- **Method:** VERIFIED

### ALM-04 — The artefact column detector pages HIGH on clean anchors for columns that only fill on unknown fills

- **Layer:** alarm / artefact assertion
- **What is wrong or unverified:** Columns added in the request-ledger rounds (filled_unknown_qty, filled_unknown_residual and others) are constant when nothing is unknown, but they are not registered as event- or fill-dependent, so the detector calls them NO_PRODUCER and pages REGRESSION. It did so on today's rebuild anchor and on both halted anchors before it.
- **Evidence:**
  - `state/notify_audit.jsonl 2026-09-13 12:46:59Z` — HIGH DELIVERED ... 锚点产物断言 REGRESSION: no orders column is constant for want of a producer [NO_PRODUCER=['filled_unknown_qty', 'filled_unknown_residual']; ...]
  - `state/notify_audit.jsonl 00:39Z and 04:39Z` — same REGRESSION on halted anchors listing 11 columns (fee_all_usdt, fee_assets, filled_known_notional, ...)
  - `ops/assert_anchor_artifacts.py:335-336, :363-366, :421 (sha256 6ee2cdde...)` — FILL_DEPENDENT = {"filled_notional", ...} ... EVENT_DEPENDENT = {"attempt_idx": ..., "order_type": ..., "cancel_ts": ..., "terminal_reason": ...} ... state = "NO_PRODUCER"
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** reporting
- **Severity:** P3 — False HIGH pages on the user's phone wear down trust in real REGRESSION pages.
- **Recommended action:** Register the event-only request-ledger columns in EVENT_DEPENDENT/FILL_DEPENDENT; fix the 0.35 comment.
- **Method:** VERIFIED

### ALM-05 — arm() A7 margin/tier-1 diagnostic is scoped to the retired internal universe (110 names), not the traded book

- **Layer:** executor arm() diagnostic
- **What is wrong or unverified:** A7 takes its universe from preds_latest.json, which in external mode is the executor's own internal DL panel. The traded 12Z book had 244 names from a 450-name universe. A7 is record-only, but its worst-case maintenance margin and thin-name list describe the wrong names.
- **Evidence:**
  - `live/binance_broker.py:1361-1373, :1451 (sha256 13be0871...)` — The universe is the one the anchor is about to SCORE: `preds_latest.json` ... _uscope = f"scoring universe from {...} ({len(_uni)} names)" ... never the reason an anchor fails to start
  - `state/anchor_runs.log 12Z arm record` — "margin_universe_scope": "scoring universe from preds_latest.json (110 names)" ... "n_margin_tier1_thin": 95
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** reporting
- **Severity:** P3 — Risk-floor reporting covers the wrong names; no gate depends on it.
- **Recommended action:** In external mode, scope A7 to the external target symbols.
- **Method:** VERIFIED

### ALM-06 — guard_twin DISAGREE lines are mostly reference-time artefacts, and its wd_worst_day_pct field shows history as if current

- **Layer:** monitor / guard_twin
- **What is wrong or unverified:** The twin's day change uses its own last snapshot before 00:00Z as the previous close; the arithmetic check uses the previous day's last daily_nav row (about 20:45Z). An evening move between those two times shows up as a DAY disagreement; CUM compares an income-ledger series with the watchdog's start-equity caliber. The field wd_worst_day_pct carries the all-history worst day (09-06), and its comment still describes pre-c800690 semantics.
- **Evidence:**
  - `~/guard_twin/state/alerts.log (84 lines)` — 2026-09-12T12:59:54Z DAY twin -0.275% vs daily_nav-arith +0.392% ... 2026-09-11T20:57:41Z DAY twin +1.563% vs daily_nav-arith +2.075% | CUM twin -0.836% vs wd -1.356%
  - `~/guard_twin/guard_twin.py:226-234 (sha256 0b299781...)` — prev_close = own_prev[-1]["equity"]; prev_src = "twin:" + own_prev[-1]["utc"] ... r = dn[pdays[-1]][-1]; prev_close = float(r.get("nav") or 0) or None
  - `~/guard_twin/state/latest.json 12:26Z` — "prev_close_src": "twin:2026-09-12T23:42:39Z" ... "wd_worst_day_pct": -4.275494048023604
  - `~/guard_twin/guard_twin.py:304, :354` — "wd_worst_day_pct": c2.get("worst_day_pct") ... # watchdog's day reading (worst over window; today if today is worst)
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** reporting
- **Severity:** P3 — Recurring non-actionable DISAGREE lines and a misleading field name in the twin's record.
- **Recommended action:** Align previous-close reference times before comparing; rename the field wd_worst_day_pct_history.
- **Method:** VERIFIED

### LED-01 — fills.jsonl holds every trade exactly twice; in-repo readers collapse the copies, a naive reader double counts

- **Layer:** ledger / fills.jsonl
- **What is wrong or unverified:** Each trade has the original row plus a backfilled_utc copy that carries the markout. Every in-repo reader found collapses supersedes. The trap is for new or ad hoc evaluation scripts: summing gives exactly 2×, keeping the first row loses every markout. The 08-10 memory note says 52.4% duplication; it is now 100% on every recent day.
- **Evidence:**
  - `state/live/pilot_log/20260910/fills.jsonl (this audit)` — 6,258 rows, 3,129 trade_ids; raw Σ|fill_notional| 555,113 vs deduplicated 277,557; same 2× on 20260906, 20260909, 20260911, 20260912
  - `live/pilot_log.py:281` — ⇒ ANY READER MUST COLLAPSE: `pilot_log.collapse_supersedes(rows)` — last row per
  - `live/watchdog.py:1382; ops/first_anchor_review.py:241; ops/first_real_anchor.py:58; live/pilot_metrics.py:265; live/reconcile.py:41-52` — PL.collapse_supersedes(...) ... def dedupe_fills(fills) ... "fills" HERE MEANS FILLED QUANTITIES FROM THE **ORDERS** LEDGER
  - `memory fills_jsonl_duplicate_trade_ids.md` — fills.jsonl 有 1334 个重复 trade_id 占金额 52.4%
- **Status:** VERIFIED_IMMATERIAL — resolution: All in-repo readers found collapse; the risk is limited to future scripts that skip collapse_supersedes.
- **Affects:** future_eval
- **Severity:** P3 — Known, documented in the schema, handled by current readers.
- **Recommended action:** Evaluation scripts must call pilot_log.collapse_supersedes; update the memory note's ratio.
- **Method:** VERIFIED

### LED-03 — Eight older flatten batches (1,210 rows, 270,076 USDT) have unmeasured fees and cannot be attributed by the current tool; the 09-09 batch is measured but mixed-asset and double-written

- **Layer:** ledger / older flatten batches
- **What is wrong or unverified:** Before 09-10 the flatten sent no client id, so the backfill tool builds zero legs and refuses to write. The 09-09 batch has fills (3,095 trades, each written twice) with USDT and BNB commissions mixed. Crisis-exit cost per incident for those days needs the venue income ledger; NAV totals are unaffected.
- **Evidence:**
  - `docs/DESIGN_reduce_only_clamp_identity_2026-09-12.md F14` — 其余 8 批 / 1,210 行 / 270,076.47 USDT(08-01 / 08-02 / 08-05×2 / 08-21×2 / 08-26 / 09-06)—— 未测, 且现工具无法归属: 09-10(d73b1b0)之前的 flatten_all 下单不发 client id
  - `state/live/pilot_log/20260906/orders.jsonl (this audit)` — FLATTEN-20260906T084608Z 268 rows, fee_paid None 268, Σ 162,665.94 USDT
  - `state/live/pilot_log/20260909 (this audit)` — FLATTEN-20260909T164536Z 243 order rows fee_paid None; fills protective_flatten 6,190 rows = 3,095 trades × 2; commission assets USDT 8,512 rows / BNB 6 rows
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** future_eval
- **Severity:** P3 — Affects per-incident cost attribution only.
- **Recommended action:** Follow-up ticket: orderId or time-window join against income COMMISSION rows, labelled as a proxy.
- **Method:** VERIFIED

### LED-05 — The 52 reconstructed rows for the 09-09 12Z crash anchor have not been written back

- **Layer:** ledger / 09-09 crash anchor
- **What is wrong or unverified:** The writeback was deferred until after deployment and needs a ruling. Until it happens, 09-09 execution metrics (M1/M4 denominators) are computed without those rows.
- **Evidence:**
  - `state/live/pilot_log/20260909/orders.jsonl (this audit)` — order types: maker 1,313, topup_taker 754, protective_flatten 243, reconstructed 0
  - `docs/RUNBOOK_deploy_executor_b681ca5_2026-09-11.md:48` — 09-09 12Z 崩溃锚(E-0909-D)的 52 行 reconstructed 写回 ... 写回改变 09-09 当日 M1/M4 的分母
- **Status:** PENDING_USER_DECISION
- **Affects:** future_eval
- **Severity:** P3 — One day's execution metrics.
- **Recommended action:** Decide: write back (ledger copy → watchdog pass → write, outside anchor windows) or record 09-09 12Z as permanently incomplete.
- **Method:** VERIFIED

### LED-07 — Live anchors.jsonl is one row per anchor but mixes halted rows, internal-era fields and capture-time timestamps

- **Layer:** ledger / anchors.jsonl
- **What is wrong or unverified:** A naive per-anchor series from this file counts targets that were never traded and mixes two book eras. In the external era anchor_ts is the capture time at about N+24, not the completion time described in the 08-06 memory note. Rebuild anchors carry turnover above 150% and dominate per-anchor cost averages.
- **Evidence:**
  - `state/live/pilot_log/20260801-20260912 anchors.jsonl (this audit)` — 253 rows; 0 duplicate nominal anchors; 127 rows without external_book.nominal_ts (internal era); 16 rows with opening_halted true that still carry target_gross (e.g. 20260912 16:24:01Z target_gross 235,335, realized_gross 0); 2 off-grid manual rows (08-01 06:29Z, 08-02 05:32Z)
  - `state/anchor_report_last.json 12Z` — 换手 162.2% 成交 228081U taker 31% fee 2.94bps
  - `memory anchors_jsonl_is_not_a_clean_series.md` — It is a COMPLETION timestamp, not the nominal anchor.
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** future_eval
- **Severity:** P3 — Avoidable with a filter, but not documented for the external era.
- **Recommended action:** Evaluation filter: external_book.nominal_ts present and opening_halted false; report rebuild anchors separately; update the memory note.
- **Method:** VERIFIED

### LED-08 — The per-anchor Telegram report folds unknown fees and fills to zero and uses stale thresholds

- **Layer:** reader / anchor_report (Telegram)
- **What is wrong or unverified:** ops/anchor_report.py was not part of the three-bucket migration. It is latent today (no maker or top-up row with an unknown or unconverted fee on 09-06..09-12), but the next such row prints as a measured fee. Its taker-share warning now fires on half of all reports, its net/gross warning sits at 5% while the check template uses 1%, and it prints 'funding.jsonl 缺' on flat settlement anchors.
- **Evidence:**
  - `ops/anchor_report.py:80, :82 (sha256 9e448836...)` — fN = sum(abs(o.get("filled_notional") or 0) for o in O) ... fee = sum(o.get("fee_paid") or 0 for o in O)
  - `ops/anchor_report.py:89, :91, :101` — if abs(ng or 0) > 0.05: ... if fN and tkN / fN > 0.10: warn.append(f"taker 占比 ...") ... warn.append("funding.jsonl 缺")
  - `state/anchor_report.log` — 101 reports, 51 carrying the taker-share warning
  - `orders.jsonl 20260906-20260912 (this audit)` — maker/topup filled rows with fee_paid None: 0; with fee_all_usdt False and no conversion: 0
- **Status:** OPEN_MEASURED_MATERIAL
- **Affects:** reporting
- **Severity:** P3 — User-facing numbers could read as measured when they are not; the taker warning is mostly noise.
- **Recommended action:** Reuse live/cost_buckets.bucket_fills; retune warnings to the current execution mix; say 'no position' instead of 'missing' on flat anchors.
- **Method:** VERIFIED

### CHK-02 — 'guard_twin AGREE' is looked up in the wrong file

- **Layer:** per-anchor deep check / source
- **What is wrong or unverified:** The template lists the check next to anchor_runs.log, where the string never appears. The verdict lives in guard_twin's own state.
- **Evidence:**
  - `docs/CRON_TEMPLATES_2026-09-04.md:13` — ④ 记账: ... `~/dl_quant_live/state/anchor_runs.log` 末行 anchor done rc=0(注意路径是 state/ 不是 state/live/), guard_twin AGREE
  - `grep -c AGREE (this audit)` — state/anchor_runs.log 0; state/launchd_out.log 0; ~/guard_twin/state/guard_twin.log 1,650 lines (84 of them DISAGREE)
  - `~/guard_twin/state/latest.json 12:26Z` — "status": "AGREE(ledger-only; nav row stale)", "comparable": false, "disagreements": []
- **Status:** DOC_STALE
- **Affects:** reporting
- **Severity:** P3 — Unverifiable as written; easy to fix.
- **Recommended action:** Read ~/guard_twin/state/latest.json (status, comparable, disagreements) and alerts.log since the last anchor; interpret DAY/CUM gaps per ALM-06.
- **Method:** VERIFIED

### CHK-04 — fund_updates baselines (~353 / ~453) still hold

- **Layer:** per-anchor deep check / baseline
- **What is wrong or unverified:** Current producer counts are within a few names of the template.
- **Evidence:**
  - `~/wide_shadow/shadow_log.jsonl (read-only, this audit)` — last 12 anchors at 04/12/20Z: 354-358; last 12 at 00/08/16Z: 454-461
  - `state/anchor_report_last.json 12Z` — fund_upd 355 cov 1.0 forced 1
- **Status:** VERIFIED_IMMATERIAL — resolution: Baseline current.
- **Affects:** reporting
- **Severity:** P3 — No change needed.
- **Recommended action:** State a tolerance (for example ±10) in the template.
- **Method:** VERIFIED

### CHK-05 — The deep-check template predates several live mechanisms and misses their checks

- **Layer:** per-anchor deep check / coverage
- **What is wrong or unverified:** No check for: executor HEAD vs origin/main (the b0a573a1 memory asks for it every anchor); W9 held-and-stopped → flatten_only disposition; alarm tiers in notify_audit (false HIGH pages, ALM-04 and STA-02); experiment safety lines (requote 30 bps × 3 days, placement behind fill rate below 15%, chase tilt abort); request budget peak (OPS-03); guard_twin disagreement content (CHK-02); regime dashboard and FTRIM (memory regime_dash_usage). The funnel step attributes orders by anchor_ts, which mixes a watchdog FLATTEN batch into the trip anchor's funnel.
- **Evidence:**
  - `docs/CRON_TEMPLATES_2026-09-04.md:1` — **更新:** 2026-09-05 14:1xZ
  - `multi_asset/exports/live/pilot_journal/tools/inspect_anchor.py:41` — orders = [r for d in days for r in jl(f"{L}/state/live/pilot_log/{d}/orders.jsonl") if A <= (r.get("anchor_ts") or 0) < A + 14400]
- **Status:** DOC_STALE
- **Affects:** live_trading, reporting
- **Severity:** P3 — Oversight gaps, each covered ad hoc today.
- **Recommended action:** Re-issue the template with these items and their current sources.
- **Method:** VERIFIED

### DOC-01 — STATE §1 and CLAUDE.md carry stale executor facts

- **Layer:** docs / STATE and CLAUDE.md
- **What is wrong or unverified:** The executor reads the target at N+24 (since 08-27), not N+23; the battery is 135 entries (130 suites + 5 audit gates), not 123; the σ_fund ladder banner is covered in OPS-01; NAV is covered in CFG-01.
- **Evidence:**
  - `CLAUDE.md (project identity)` — 执行器 `~/dl_quant_live`(git, **改动只经 `ops/safe_commit.sh` + 电池全绿**)N+23 读取交易
  - `STATE.md §1` — 执行器(`~/dl_quant_live`, external 模式)N+23 读并交易 ... 改实盘代码唯一通道: `~/dl_quant_live/ops/safe_commit.sh` + 电池 123/123
  - `config/book.json:158 and _timing` — "anchor_offset_min": 24, ... ★ 2026-08-27 05:2xZ offset 23→24
  - `state/_safe_commit_acc.log:139` — ACCEPTANCE: ALL GREEN (135/135 suites exit 0)
- **Status:** DOC_STALE
- **Affects:** reporting
- **Severity:** P3 — Documentation only.
- **Recommended action:** Refresh the STATE §1 chain and battery lines; propose the CLAUDE.md wording change to the user.
- **Method:** VERIFIED

## 4. Not checked

- Producer side (~/wide_shadow: shadow_loop_v3, combo_stage, sidecar, target_live writing, king fund_ema v0/v1 train/serve skew H2b, V2MAIN T4b) beyond reading two target files; owned by other auditors.
- The 12Z first-anchor acceptance itself (DESIGN §4.6 metrics, reject-code split, maker share by source); the lead is running it.
- Anything that needs the venue: apiTradingStatus, leverage brackets, fundingInfo (which of the 13 'absent_from_venue' names are delisted), whether the 09-12 flatten fills are still retrievable, income completeness beyond guard_twin's identity gap.
- No test suite, battery, resume_from_trip.sh --check or rejudge_ledger_rows.py --check was run; battery results are quoted from state/_safe_commit_acc.log.
- W1 ic_monitor behaviour after deployment (first evaluation 2026-09-14 01:30Z) and the ic_monitor thresholds (R-11).
- Whether the σ_fund ladder would switch g to 0.5 on reactivation (OPS-01); the ladder state was not replayed.
- Q6 replay on the 41-day ledger copy (EXE-04); the 08-01..09-12 mixed-readability back-scan (POSTMORTEM_b0a573a1 4d-ii); 'income 缺行'; -5022 reject rows lacking spread/mid (open list in POSTMORTEM_b0a573a1_15_rounds_2026-09-11.md:126).
- funding.jsonl (M6 stream) correctness and markout backfill correctness (mark_status, mark_lag_s).
- Research-side evaluation scripts other than pilot_journal/tools/inspect_anchor.py (for example analyse_requote_behind.py) for fills de-duplication and halted-row filtering.
- Other launchd jobs' logic: regime_dash, regime_weekly, c2shadow, stopoverlay, depthwatch, universe_shadow, w4liqcapture, markout_backfill, nosleep.
- notify_audit alarm policy tiers beyond the alarms quoted; Telegram delivery path.
- DRY_RUN tree under ~/dl_quant_live/state/ (root) beyond the alarm-episode scope rule; contents of untracked rollback_*/staging_* directories.
- Whether the reviewer's per-side scaling alternative (EXE-03) or chase-population amendments (CFG-04) change P&L.

## 5. Reproduction notes

- Counterfactual rewrite series (CHK-01): for each `A` in `~/wide_shadow/state/target_live/*.json`, Σ|w_live−w_king| / Σ|w_king| against `target_live_king/<A>.json` — the formula at `multi_asset/exports/live/pilot_journal/tools/inspect_anchor.py` (sha256 714792e1…).
- Ledger scans (LED-01..08, CHK-03, EXE-02, EXE-07): plain `json.loads` over `~/dl_quant_live/state/live/pilot_log/<day>/{orders,fills,anchors,daily_nav}.jsonl`; fills de-duplicated by `trade_id` keeping the last row.
- Three-bucket check (LED-02): `live/cost_buckets.py` (sha256 0d31d10a1353f4ba…) copied to the session scratchpad and loaded with bytecode writing disabled; `bucket_fills` applied to the 255 rows with `rebalance_id == FLATTEN-20260912T124737Z`.
- Notary check (LED-06): guarded sha256 of each ledger file against `ledger_notary/manifest_<day>.json` for 20260830, 20260906, 20260909, 20260911, 20260912; `prev_manifest_sha256` read from all 43 manifests.
- Deployment identity (EXE-08): `git -C ~/dl_quant_live rev-parse ef60f85^{tree}`; `stat` mtimes of patched files; `git show 918559f:scheduler/anchor_loop.py | grep -c forced_flat_names`.
