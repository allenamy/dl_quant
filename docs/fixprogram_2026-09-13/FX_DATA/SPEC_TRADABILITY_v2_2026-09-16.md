> **创建:** 2026-09-16 | **Session:** FX-DATA (fix worker) | **状态:** DESIGN, frozen before any v2 number; supersedes SPEC_TRADABILITY_2026-09-13 §2 (naming), §5, §6 and §7 | **作废条件:** an amendment file `SPEC_TRADABILITY_v2_AMENDMENT_<n>.md` committed with its reason stated before the numbers it affects; or the canonical cache sha changes (holefix2 `1d7f459dee434ec4` / x0910 `8115299410cd5e8d`)

# SPEC v2 — activity, obligation and price integrity are three objects, not one

**Supersedes.** `SPEC_TRADABILITY_2026-09-13.md` (sha256 `99ae35e01ec3dd06ba7bf69ea62de8f36cfd2695492ccf53757d985b8a0946b2`, commit `73b59ec0`) in four places: **§2's naming** of the flag, and **§5, §6, §7 entirely**. §1 (the 5m row fact), §3 (5m granularity), §4 (descriptive-only fields) and §8 survive unchanged and are re-stated here by reference, not re-frozen. The v1 file's bytes are not edited; it stays in the repository as the object this document supersedes, and every v1 number already produced keeps its receipt and its v1 label.

**Why there is a v2.** The independent review (`docs/REVIEW_fixprogram_progress_2026-09-14.md`, sha256 `cd3bdb88ac0e759edabacec9faf1b754405206330cf427095e81d7bb64bd08fe`, commit `9f6384fb`, §4, registered as **FXR-DATA-1, P1**) found that v1 §5–§7 cannot pass as written. The finding is correct and I accept it in full. In v1's own words the defect is visible: §8 declares "It does not define the exit price of a delisted contract. The data do not contain it", and §7 nevertheless closes TRD-03 on a label computed under that treatment. That is this project's own registered anti-pattern — **a declared blind spot is not a closed one** — and I walked into it.

**The governing rule the review invoked**, from the review branch's `AGENTS.md` (sha256 `7d5a40d57e45789d80ec14e8155515803212d1162e175e55189d3f1751fc1a6d`), dated 2026-09-08:

> **档案覆盖不是交易资格。** 月ZIP或日ZIP的404不能推导整月/整日不可交易；平直或有限价格也不能证明仍可新开仓。… **未知有仓出场价必须停在显式不可定价状态，不能用未来finite筛池、零补偿或事后提前退场通过门**；只掌握部分终止公告时不能称全历史PIT已认证。

Recorded precisely, because it changes who it binds: this rule is in the **review branch's** `AGENTS.md`. The research repository's own `AGENTS.md` (86 lines, single-asset-era header) contains no such clause — `grep -ciE "资格|退市|不可定价"` returns 0. So the rule reaches this work through the review, and the lead has adopted it as the design baseline.

---

## 0. What v1 got wrong, stated as a defect and not as a nuance

v1 defined one predicate, `tradable(A, s) ⇔ ≥1 traded bar in (A − 24 h, A]`, and then used it for three different jobs:

| v1 section | what it decided with the predicate | why that is not what the predicate knows |
|---|---|---|
| §2 / §6 | who may be **admitted** to a member set or rank base | acceptable — this is a recent-activity question, and activity is what a traded bar is evidence of |
| §5 | whether a settlement is **payable** | a traded bar in the previous 24 h is not evidence that the venue settled, nor that we were owed it |
| §6 / §7 | what happens to a **position already held** when the name stops qualifying | nothing at all was booked — no price, no carry, no cost. That is **zero compensation**, which the AGENTS rule forbids by name |

The three counter-examples, which v2's red tests reproduce rather than paraphrase:

1. **The 24 h tail is an artefact of the window, not of the venue.** A contract whose last trade is at D is `TRADABLE` at D+5 min and still `TRADABLE` at D+23 h 55 min, and only stops at D+24 h. A coin halted immediately after its last trade passes the gate for almost a day. The converse also holds: a normally-trading coin whose data feed breaks fails the gate.
2. **The proxy cannot see the number that matters.** Construct two markets with identical traded-bar marks and identical frozen quotes whose final legitimate settlement prices are 100 and 50. A position of 1 contract entered at 100 exits at P&L 0 in the first and −50 in the second. `tradable()` is bit-identical in both. Under v1's treatment both book **0**, so the error is 0 and −50 and the backtests differ by nothing. **Two backtests that both refuse to price the exit can agree exactly and still say nothing about whether the historical loss mattered.**
3. **Archive coverage is not eligibility, in either direction.** v1 §2 said "`NODATA` is never treated as tradable", which reads an absence of rows as proof of inability to trade. The AGENTS rule forbids that inference. It also forbids the opposite one: a flat or finite price does not prove a new position could still be opened.

**Consequence for numbers already produced.** Everything measured under v1 remains a valid measurement *of what it measured*, and every receipt stands. What changes is what those numbers may be called. §5 below re-labels them.

---

## 1. Object A — ACTIVITY (an admission proxy, named as a proxy)

**Definition.** `activity(A, s)` over a declared window W, from the 5m cache's `log_cnt` channel exactly as v1 §1 defines a bar's state:

- `ACTIVE` ⇔ ≥ 1 `TRADED` bar with close time in (A − W, A]
- `QUIET` ⇔ no `TRADED` bar but ≥ 1 `UNTRADED` bar in the window
- `ACTIVITY_UNKNOWN` ⇔ every bar in the window is `NODATA`

W = 24 h is primary; W = 4 h is a sensitivity that never sets a label. Causality, refusals and the truncation flag are unchanged from v1 §2.

**What changed from v1, and it is not only a rename.**

- The name. `tradable` asserted a venue permission the data cannot support. `activity` asserts what a traded bar is actually evidence of. **Every consumer must read it as a proxy**, and any document that calls it tradability is wrong.
- v1's `NODATA` became **`ACTIVITY_UNKNOWN`, not `INACTIVE`.** An absent row is missing evidence, not proof of inability.
- **The declared lag is a property of the proxy, not a tolerance.** `activity` stays `ACTIVE` for up to W after the last trade — at most 6 anchors at W = 24 h. v1 called this a bounded lag to be counted. v2 keeps the counting and adds: this window is the reason the proxy may not decide payability or exit.

**Permitted use — exactly one.** Admission screening: whether a name may **enter or remain in** a member set, a rank base, or a trade set at anchor A. `ACTIVE` admits; `QUIET` and `ACTIVITY_UNKNOWN` do not.

**Forbidden uses, and these are the v1 defects:**
- deciding whether a funding settlement is payable (v1 §5),
- deciding what happens to a position already held (v1 §6),
- being called a fix for delisting risk, or a book "fixed" with respect to it (v1 §7).

**A mask built from Object A is a population sensitivity.** It answers "what if this population had been admitted instead". It is not an economic-truth correction and may not be named one until Object B is resolved for the affected positions.

---

## 2. Object B — OBLIGATION (a held position does not vanish when admission ends)

A position held at the anchor where admission ends enters the **unresolved-holdings register** and stays there until evidence closes it. Nothing is booked at 0 by default, ever.

### 2.1 States

| state | meaning | how it is entered |
|---|---|---|
| `OPEN` | admitted and priced from real trades | normal operation |
| `HELD_QUIET` | admission ended, position still held, last price still has a trade behind it | `activity` leaves `ACTIVE` while the position is non-zero |
| `HELD_UNPRICEABLE` | no reliable price is available for the exit | no trade-backed price within the declared reliability window |
| `CLOSED_BY_TRADE` | exited at a real traded price | an actual fill |
| `CLOSED_BY_EVIDENCE` | closed at a settlement or announced termination price | a settlement record or venue announcement naming a price and a time |

### 2.2 Transition rules

1. **Only evidence closes a position.** `CLOSED_BY_TRADE` requires a fill; `CLOSED_BY_EVIDENCE` requires a settlement record or announcement carrying a price and a timestamp. **A timer may not close a position. An absence of rows may not close a position. Zero may not close a position.**
2. **No future information may enter a state transition.** `last_traded_ts` and `dead_after` (v1 §4) use the future by construction and stay descriptive: they may choose fixtures and count contamination, never drive a transition. v1 already held this line; v2 keeps it and tests it (RT-5).
3. **`HELD_UNPRICEABLE` is a terminal reporting state, not a gap.** While a position is in it, every reading that includes that book **must** report the register's bounded interval beside the point estimate, or state that unresolved positions were present and unquantified. A net number quoted without that statement is not admissible.
4. **`ACTIVITY_UNKNOWN` does not by itself set `HELD_UNPRICEABLE`.** Missing rows are missing evidence; the position stays `HELD_QUIET` with its last reliable price and its evidence class recorded, and only the absence of any trade-backed price within the declared reliability window moves it.

### 2.3 The unresolved-holdings register — field definition

One row per (symbol, position episode). Frozen here before any v2 number.

| field | type | rule |
|---|---|---|
| `symbol` | str | contract |
| `episode_id` | str | `symbol` + the anchor the position was opened at |
| `entry_anchor_ts` | int | anchor of the first non-zero holding of this episode |
| `qty` | float | signed size still held, in the book's own weight unit; **never coerced to 0** |
| `last_reliable_price` | float or null | last price with identified evidence behind it |
| `last_reliable_price_ts` | int or null | its timestamp |
| `price_evidence` | enum | `TRADE` · `MARK_ONLY` · `FROZEN_CLOSE` · `NONE` — `FROZEN_CLOSE` and `NONE` are **not** reliable prices |
| `state` | enum | §2.1 |
| `exit_price` | float or null | **null until evidence**; a null may never be read as 0 |
| `exit_evidence` | enum | `TRADE` · `SETTLEMENT_RECORD` · `ANNOUNCEMENT` · `NONE` |
| `unknown_flag` | bool | `exit_price is None` |
| `stress_basis` | enum | `TO_ZERO` · `OBSERVED_RANGE_k` · `VOL_MULTIPLE_k` · `ANNOUNCED` — named, never implicit |
| `stress_px_lo` / `stress_px_hi` | float | bounded exit-price scenario, both from `stress_basis` |
| `pnl_lo` / `pnl_hi` | float | the implied bounded P&L in the book's unit |
| `opened_at` / `resolved_at` | int or null | |
| `resolution_source` | str or null | the file and row of the closing evidence |

**Registered stress pair**, frozen now so it cannot be chosen after seeing a result. For an unresolved episode with a `last_reliable_price` P:

- **downside** `TO_ZERO`: a long exits at **0** (the contract is worthless); a short exits at **P** (a short cannot lose from a fall).
- **upside** `VOL_MULTIPLE_k`: exit at `P · (1 ± k·σ)` with **k = 3** and σ the name's own realised 24 h volatility over its last window with trades; a short's bad side is the up move, a long's good side likewise.

The pair is deliberately wide and deliberately asymmetric, because the honest statement about an unpriceable exit is an interval, not a point. `ANNOUNCED` replaces both bounds with the announced price once evidence exists.

**What the register is not.** It is not a claim that these are the true exit prices. It is the explicit not-priceable state the AGENTS rule requires, carried forward with enough structure that a later announcement closes it instead of reopening the whole question.

---

## 3. Object C — PRICE AND SETTLEMENT INTEGRITY

1. **Original price, not robustified price.** Exit and settlement P&L use unclipped close ratios. The 5m cache's `ret5` is hard-clipped at ±0.30 and may never be compounded into an exit price; the committed index of the 955 clipped cells is `common/data/bound_bars_ret5_x0910.npz` (`94e8e8c1…`) and the guard is `common/bound_bars.py`.
2. **A 404 is not an ineligibility.** Archive absence maps to `ACTIVITY_UNKNOWN` and to missing evidence, never to a decision.
3. **Three clocks are recorded separately**, never merged: the event/announcement time, the time new positions were forbidden, and the automatic settlement time. Spot announcements and perpetual terms are separate sources.
4. **Partial coverage may not be called certified.** Holding termination announcements for some names does not license a claim that the full history is PIT-certified.

---

## 4. Red tests — frozen before any v2 number

Each cell names the object it tests and the exact assertion. RT-1 and RT-2 are the review's own counter-examples, reproduced rather than paraphrased.

| id | object | assertion |
|---|---|---|
| **RT-1** | A | On a synthetic contract whose last trade is at D: `activity(D+5min) == ACTIVE`, `activity(D+23h55min) == ACTIVE`, `activity(D+24h) != ACTIVE`. **And**: v1's `payable` rule applied at D+23h55min returns `True`, while v2 returns `PAYABLE_UNKNOWN` absent settlement evidence. The v1 branch going `True` is the red. |
| **RT-2** | A, B | Two synthetic markets with **identical** traded-bar patterns and frozen quotes, true settlement 100 and 50. Assert `activity()` is bit-identical in both (the proxy is blind — asserted as a fact, not hidden). Assert v1's treatment books **0 in both**, so its error is 0 and −50. Assert v2 puts both in `HELD_UNPRICEABLE` with **identical** bounded intervals before evidence, and **different** closed P&L after evidence. |
| **RT-3** | A | A window of pure `NODATA` maps to `ACTIVITY_UNKNOWN`, **not** to a claim of ineligibility; and no code path derives "untradable" from archive absence. |
| **RT-4** | B | No path can write `exit_price = 0` or `pnl = 0` for a position in `HELD_UNPRICEABLE`. Only `CLOSED_BY_TRADE` or `CLOSED_BY_EVIDENCE` may set a price. A mutation that reintroduces the zero default must turn this cell red. |
| **RT-5** | B | Every state at anchor A is computable from information available at A. A mutation that lets `last_traded_ts` or `dead_after` drive a transition must turn this cell red. |
| **RT-6** | B | A reading that includes an unresolved episode and quotes a net number without the register's interval, or without stating that unresolved positions were present, fails. |
| **RT-7** | C | An exit price recomputed from the clipped `ret5` channel on a window containing a bound bar fails, via `bound_bars.assert_clean`. |

---

## 5. Re-labelling of the numbers already produced under v1

No receipt is withdrawn and no number is recomputed here. What changes is the name each one is allowed to carry.

| produced under v1 | v1 label | v2 label |
|---|---|---|
| `tradability_v1.npz` `54d409d0…` | the tradability flag | **the activity proxy**, W = 24 h; a valid admission input, not a tradability truth. The artifact's bytes and sha are unchanged and it stays pinned |
| SPEC §7 arm `TF` | "the fixed book" | **`PU24` — the population sensitivity at W = 24 h.** It changes who is admitted; it does not price any exit |
| SPEC §7 arm `TF4` | 4 h sensitivity | `PU4`, unchanged in role |
| §TRD-D3 Δg = **−0.0603 / −0.0519** bps/anchor/unit gross | "the cost of the fix" / grounds to close TRD-03 | **the book effect of an admission-population change, measured under a common exit convention that books nothing on either side.** It is not the economic effect of a delisting fix |
| §TRD-D3 verdict | TRD-03 closes on EQUIVALENT | **TRD-03 cannot close on this arm at all**, whatever the label — because the arm does not measure the quantity TRD-03 is about |

**The direction of the A0 conclusion survives and may be understated, not overstated.** Both C0 and `PU24` omit exit P&L, so the paired Δg is a difference of two numbers that share the same omission. The re-basing conclusion — A0's base is too high — is unaffected by the shared omission. What is now unavailable is any claim about *how much of the dead-contract problem has been dealt with*: the price channel Δ of **−0.1028** measures the P&L the frozen rows contributed while the names were still admitted, and says nothing about the exit that was never priced.

**AUDIT_DATA TRD-03's `VERIFIED_IMMATERIAL` is overreach and must be downgraded** to *"recorded phantom carry is small; exit P&L unidentified"*. The share-of-gross figure (max 4.9e−4) and the small booked carry are not an upper bound on exit exposure. Per the §11 discipline the original bytes stay and the correction is annotated; and as with the TRD-02 register correction, **the AUDIT_DATA edit itself is the lead's to apply** — this document is the evidence for it, not the edit.

**The census is not a lifecycle.** 156 dead contracts and 13,770,575 frozen rows are a true archive count with a receipt, reproduced as sets and not merely as counts. They are **not** a substitute for 156 per-name lifecycles with termination and settlement evidence. Object B exists because that evidence has not been gathered.

---

## 6. Wording corrections carried in from the review and from FX-PROD

1. **The producer's base list is `exchangeInfo TRADING ∪ st.live`, with a fallback to the previous base list on failure** — not strictly TRADING-only. So "live naturally excludes delisted names, therefore research only has to catch up with live" does not follow from that line, and v2 makes no such argument. (v1 §6's fix-site table cited `shadow_loop_v3.py:315-317` for the production base; the citation stands, the inference drawn from it does not.)
2. **`state_H_f10_<A>.npz`'s last writer is the sidecar `sidecar_blend.py` on 128 of 129 anchors, not `combo_stage`**, whose own chain state is discarded each anchor. v2 therefore makes no "replay runs the same code as production" claim anywhere, and any such phrasing in my earlier documents is withdrawn.
3. **BNXUSDT 2023-02-11 08:00Z is a genuine exchange rate, not an interval mislabel** (FX-PROD, from `ledger_full.npz`): raw rate −0.02056789, the zip declares `funding_interval_hours = 8.0`, and every neighbour for ±3 days is a clean 8 h gap, so `rn8 = −205.68 bps` is the rate, correctly labelled. My FND-adjacent reading of that cell is withdrawn. What survives is the membership finding, and it belongs to Object A: **a correctly-labelled rate for a name with no market data at that anchor was allowed into a cross-sectional dispersion state**, moving T1's SIGF from 17.62 to 4.78 at that anchor on its own.
4. **Citations are to commit blobs**, `git show <commit>:<path>`, not to the mutable working tree (lead's §19.4).

---

## 7. What v2 does not decide

- It does not gather the termination evidence. Object B is a structure for carrying the unknown, and the 156 lifecycles are a separate, named piece of work.
- It does not re-run any reading. Re-basing A0, and re-running T1 D2 or the September carry readings, are the lead's and the suspended secondary axis's.
- It does not change `tradability_v1.npz`. The artifact is unchanged and still pinned at `54d409d0…`; only its name and its permitted use change.
