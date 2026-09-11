> **创建:** 2026-09-12 | **Session:** b9646a9e / r9_screen slot 3 | **状态:** CLOSED — INFEASIBLE as an uplift candidate; the DEFECT is VERIFIED and larger than reported; one instrument-misreading trap disarmed | **作废条件:** 币安恢复发布市场级强平历史 / 买入第三方清算聚合(Tardis 等, 用户钱) / 修复后的采集器积累 ≥12 个月并跨 regime

# SCREEN — LIQ_CAPTURE_REPAIR (r9 candidate 3)

**Screen owner:** research subagent, branch `research/book-uplift-2026-09-11`.
**Caliber pin:** v4 chain 2026-09-09 (`CALIBER_PIN_v4_2026-09-11.md`) — read, but **no measurement on the
v4 axis was possible** (see §2), so no v4 artifact was loaded and no device was run.
**ENV WHITELIST (E-0826-D): EMPTY SET.** No environment variable was set or read by any step of this
screen. Every command was read-only: `ls find cat head tail wc grep shasum python3(stdlib json/math)
lsof ps sysctl launchctl-list launchctl-print last mkdir(output dir only)`. No device
(`w10_universe.py` / `w10_sleeve.py` / `judge_v4.py`) was run, no GPU job launched, no exchange
endpoint called, no process started / stopped / restarted, nothing written to `~/dl_quant_live`,
`~/wide_shadow` or `~/w4_liq_capture`.

## 0. ONE-LINE VERDICT
**INFEASIBLE as an uplift candidate, and the underlying mechanism it would feed is already bounded
below the cost line by a standing receipt.** The candidate has **n = 0 rows of data**: rho to A0 and
standalone edge are NOT_REACHED, not "not yet run". The defect the surveyor found is **real and worse
than reported**. Its most valuable content is not an alpha at all — it is that **a standing
$700–1200 spending rule keyed on this instrument would have fired on a client-side bug.**

## 1. STEP 1 — FEASIBILITY: the surveyor's data claim is CORRECT, and incomplete
All of the following was measured first-hand today, read-only.

| # | Fact | Status |
|---|---|---|
| F1 | **No `forceorder_*.jsonl` exists anywhere** under `~/w4_liq_capture` (`find ~/w4_liq_capture -name 'forceorder*'` → empty). The directory holds only `heartbeat.jsonl`, `recorder.err`, `recorder.py`, `run.err`, `run.log` (0 bytes). | VERIFIED |
| F2 | `heartbeat.jsonl` = **4080 lines, and `n_events` is 0 in EVERY ONE of them** — not merely in the first and last. `grep -c '"n_events": 0'` = 4080 = total lines; the max non-`ts` numeric value over the whole file is **0**. | VERIFIED (stronger than the survey claim) |
| F3 | **The 31.57-day span is NOT 31.57 days of capture.** It contains exactly one gap > 400 s, of **1,504,690.5 s = 17.415 days**, from **2026-08-12T08:17:35Z to 2026-08-29T18:15:46Z**. Median inter-beat interval 300.012 s ⇒ real heartbeat coverage = 4080 × 300 s = **14.17 days = 44.9 % of the claimed span**. | VERIFIED — **NEW, the survey missed this** |
| F4 | Cause of the hole is host downtime, not the recorder: `last reboot` → shutdown Sun Aug 30 01:58 local, reboot Sun Aug 30 02:06 local; `sysctl kern.boottime` = Sun Aug 30 02:06:37 2026 local; `ps -p 1225` START = Sun Aug 30 02:15:24 local = **2026-08-29T18:15:24Z** (host is UTC+8), **22 s before the first post-gap heartbeat**. `KeepAlive` cannot cover a powered-off host. | VERIFIED |
| F5 | The process is alive **and genuinely connected**: `launchctl print gui/501/com.hsy.w4liqcapture` → `state = running`, `pid = 1225`, `runs = 1`; `ps` elapsed `13-01:04:36`; `lsof -p 1225 -i` shows exactly one socket, **`TCP 192.168.0.43:61075->57.182.85.6:443 (ESTABLISHED)`**. | VERIFIED |
| F6 | `recorder.err` holds **5 lines total**: four `WebSocketTimeoutException` inside the first 111 s of the very first start (2026-08-11T05:30:11 / :30:42 / :31:14 / :32:11Z) and one `WebSocketConnectionClosedException` at **2026-09-02T23:20:00Z**. **Zero errors in the 8.8 days since.** | VERIFIED |
| F7 | Interpreter identity checked, not inferred: plist `ProgramArguments` = `/usr/bin/python3 recorder.py`; `ps` shows the resolved binary = Xcode Python **3.9.6**; `websocket-client **1.9.0**` at `~/Library/Python/3.9/lib/python/site-packages/websocket`. The 7 `ModuleNotFoundError: No module named 'websocket'` tracebacks in `run.err` are **stale** — from the pre-install launches of 2026-08-11 13:29 local, before `recorder.py` reached its current mtime 13:32; the import succeeds today. | VERIFIED |

**So the failure mode is precisely localised:** it is **not** a dead process, **not** a missing module,
**not** a missing connection, and **not** an error-channel event. It is **a live, ESTABLISHED TLS
socket that has delivered zero application messages in 13 days**, with the error channel silent for
8.8 of them. That excludes exactly the two conditions the `KeepAlive` + heartbeat design was built to
detect, which is why it ran unnoticed.

**Root cause: NOT ESTABLISHED.** Three candidates remain — (a) a half-open / black-holed socket that
`ping_interval=180, ping_timeout=20` failed to tear down; (b) the raw-stream path subscription not in
effect server-side; (c) venue-side suppression for this client/region. **I did not discriminate
between them, deliberately: the discriminating test is opening a websocket to `fstream.binance.com`,
and hard constraint 1 forbids calling an exchange API.** Anyone claiming a root cause without that
test is inferring. (The premise that the venue publishes liquidations continuously, so that zero over
13 days is impossible if the subscription worked, is **INFERRED** domain knowledge — not measured here.)

### 1b. Six design defects, each of which alone would have hidden this
- **D1 — liveness ≠ capture.** `heartbeat.jsonl` records `n_events`, and **nothing reads it**. No flat-counter alarm. This is the `silent_watcher_death` / `handback_dies_silently` family, exactly as the surveyor labelled it.
- **D2 — `KeepAlive` is the wrong guard** for a failure in which the process never exits.
- **D3 — no output-existence check**: a never-created output file is invisible for 31 days.
- **D4 — wrong host.** A laptop that shuts down gives 17.4-day holes no in-process guard can fix. A 12-month forward capture must live on an always-on box (jpline / pod2).
- **D5 — `on_error` writes to a file nobody reads**; an 8.8-day error silence is indistinguishable from health.
- **D6 — no expected-rate assertion.** There is no "≥ N events per UTC day or alarm" rule, so a 100 % shortfall and a quiet market read identically.

### 1c. Lookahead review (moot, recorded for the repair spec)
With `n = 0` there is nothing to leak. **If repaired**, the construction is naturally causal — each
record carries `recv_ts` (local receipt) alongside the venue event — and the guards it must still pass
are the ones r5 already used on the OI lineage: only 5m rows with `create_time ≤ t − 300 s`, plus the
offset-spectrum peak@0 check and a zero-lag leakage twin. **Untested here.** Note also the
pre-registered honesty clause in `PREREG_w4_liquidation_2026-08-11.md` L22: since 2021-04 the venue
pushes **at most one forceOrder per symbol per second** — the "truth" this capture would collect is a
**censored lower bound**, so ratio/imbalance features are biased small even when it works.

## 2. STEP 2 — rho TO A0: **NOT_REACHED**, and not for want of effort
The candidate's per-anchor series cannot be built, at any caliber, because **the candidate has zero
observations**. This is not a screen I declined to run; it is a screen with an empty input.
Independently, the historical substitute does not exist either — `RESULT_r5_newdata2_liq_oi_2026-09-11.md`
§1 verified that `data.binance.vision` has **no `liquidationSnapshot` prefix**, `fapi/v1/allForceOrders`
returns **404 (removed)**, and `fapi/v1/forceOrders` returns **401 (signed, own orders only)**.
**rho = NOT_REACHED. Conditional rho in A0's loss cells = NOT_REACHED.**

## 3. STEP 3 — STANDALONE EDGE: **NOT_REACHED** (and pre-bounded by two standing receipts)
No series ⇒ no mean g, no CI, no Sharpe, no turnover, no null comparison. What *is* on the record for
the mechanism this capture would serve — cited, not re-run:
- **Gate G1 has already failed twice, on two independent lineages.** Round 1: W4 liquidation proxy **0/7** (`RESULT_w4_gate1`, 2026-08-11; memory `new_info_campaign_round1_2026_08_11.md` — best cell F1_4h +0.0026, 87 % off target). Round 5 on the v4 829-name lineage at the book layer: **0 admissions from 8 arms** (`RESULT_r5_newdata2_liq_oi_2026-09-11.md` §10).
- **The capture exists to serve gate G0**, whose own prereg (`PREREG_w4_liquidation_2026-08-11.md` L39) states: *"任何部署提案必须 G0+G1 双过"* — any deployment proposal must pass **both**. **G1 is already failed.** Repairing the capture therefore cannot unblock a deployment; it can at most retire a proxy that is already retired.
- **The mechanism's own ceiling**: the tightest event cell (OI-drop ≥1 % with a down move, n = 494,629) reads **+0.46 bps [−0.17, +1.12]**, i.e. bounded at ~1.1 bps, against a book cost of **2.9537 bps per unit turnover** (`r3k_impact/costb_PWR_G230k.json`, field `book_avg_bps_per_unit_turnover`, read today). Every one of the 16 threshold cells contains zero.

## 4. STEP 4 — THE ARITHMETIC, NOT ROUNDED IN OUR FAVOUR
Identity check first, so the decomposition can be trusted: `g = pnl_ex − carry − cost` reproduces A0's
own row exactly — 1.3266 − 0.4694 − 0.1682 = **0.6890** ✓ (VERIFIED arithmetic on the r5 §6 table).

**a) What the desk needs.** Target 3.966. At rho = 0 a single new source must carry standalone Sharpe
`sqrt(3.966² − S_A0²)` = **3.7050** against the full-cycle A0 1.4150 (reproduces the brief's 3.705
exactly) or **3.7499** against the cross-regime A0 1.2912.

**b) What the best liquidation-adjacent sleeve ever measured delivers.** `SA_LIQPC`: Sharpe **0.4464**,
rho to A0 **0.099**. Combined with the cross-regime A0 at the optimal 2-asset allocation:
`sqrt((S1²+S2²−2ρS1S2)/(1−ρ²))` = **1.3303**, i.e. **+0.0391** Sharpe, leaving the gap at **2.6357**.
(Against the full-cycle A0: 1.4481, +0.0331, gap 2.5179.) And `SA_LIQPC` is disqualified on its own
terms — **168 % of its +1.07 bps net is funding carry** (carry −1.8072), i.e. it is a re-weighting of
the book's own bet wearing an event's clothes. `SA_OIV` (rho 0.293) buys **+0.0035**.

**c) The fantasy upper bound, stated as a fantasy.** A0's implied per-anchor sd of g is
0.6890 / (1.4150/√2190) = **22.787 bps**. A book earning the event study's *upper CI* of +1.12 bps per
anchor **at zero cost and zero turnover** would read Sharpe **2.300** — still 1.67 below target, and
that is the most generous number the data permits. Charge it the measured turnover of the only real
expression (0.0902, 2.97× A0) at 2.9537 bps/unit: 1.12 − 0.2664 = +0.8536 bps ⇒ Sharpe **1.7530**; at the
event study's **point** estimate (+0.46) the same arithmetic gives **+0.1936 bps ⇒ Sharpe 0.3975**. The
measured expression actually delivered gross +0.4462 (own CI95 [−0.0475, +0.9396], contains zero) and
net **−1.0301**.

**d) The inversion trap, closed.** "Just flip the −2.15 Sharpe book" does not work: inverting flips
`pnl_ex` and `carry` but **not** `cost`, so `g_inv = −0.4462 + 0.1724 − 1.3039 = **−1.5777**` — worse,
not better.

**e) The clock, which no repair shortens.** A forward-only capture repaired today yields its first
12 months in **2027-09**, one regime, no walk-forward, no Q4 worst-quintile. A cross-regime Sharpe
claim cannot be built on it inside this program. `RESULT_r5_newdata2` §10 already said the quiet part:
even a **perfect** one-name-per-anchor expression of this mechanism does not pay.

## 5. THE PART THAT IS ACTUALLY WORTH THE SCREEN: an instrument-misreading trap, disarmed
`docs/MILESTONE_2026-08-11.md` §3 item 3 records a standing decision rule:
> **W4 真值裁定**: 采集器 24h 心跳(`~/w4_liq_capture`)判端点生死 → 死则 Tardis C叉(~$700-1200 一次性, 用户钱裁定)

**Read literally, 4080 consecutive zero-event heartbeats is the "endpoint dead" branch, and the next
step is spending $700–1200 of the user's money on a third-party aggregator.** That inference would be
**wrong-by-instrument**: F5 shows a live ESTABLISHED socket and F6 shows a silent error channel, so the
zero is **not yet attributable to the venue** — a client-side defect is entirely unexcluded, and the one
test that would discriminate is forbidden to me here. This is the
`my_own_instruments_fail_at_the_extremes` / `measuring_a_misunderstood_quantity` /
`declared_blind_spot_is_not_closed` family: the heartbeat was built to adjudicate **endpoint liveness**
and it actually measures **端点 ∧ 客户端 ∧ 主机开机** jointly. **Do not fire the Tardis branch on this
evidence.**

## 6. RECOMMENDATION
1. **Do not fund, do not schedule, do not plan a book on this.** As an uplift candidate: INFEASIBLE (n=0 today) and pre-bounded (G1 failed 0/7 and 0/8; mechanism ceiling ~1.1 bps vs a 2.95 bps cost line).
2. **Repair it anyway — as hygiene, it is cheap** — but on an always-on host (jpline/pod2), with (i) an alarm on a **flat counter** and on a **missing daily output file**, not on process death; (ii) an assert of `n_events > 0` within one hour of start; (iii) a per-UTC-day minimum-count rule; (iv) the counter persisted next to the data, not only in a heartbeat nobody reads. **The repair is an engineering change to a non-live asset and is outside this screen's zero-touch mandate — I did not perform it.**
3. **Amend the MILESTONE decision rule** so that "採集器心跳" cannot be read as an endpoint verdict until a client-side self-test (a loopback/known-chatty stream, or a first-party liveness probe) has passed.

## 7. RECEIPTS
`RECEIPT_LIQ_CAPTURE_REPAIR_2026-09-12.json` in this directory carries every command, every sha256 I
computed myself, and the VERIFIED/INFERRED label on every number above.
**Output-path note (E-0825-G/H, no inference from names):** the mandated output directory string in my
brief is **523 bytes and contains `/` characters**, so it is not a legal path component on this
filesystem (255-byte limit). I substituted
`.../uplift_2026-09-11/r9_screen/LIQ_CAPTURE_REPAIR_3/` and recorded the substitution here and in the
receipt rather than silently renaming.
