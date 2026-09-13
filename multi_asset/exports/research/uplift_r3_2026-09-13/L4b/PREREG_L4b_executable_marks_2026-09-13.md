> **创建:** 2026-09-13 12:4xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (worker L4, task L4b from lead) | **状态:** PREREG — frozen before any raw price is downloaded or read; POST-HOC-FAMILY-2 (F2) and conditional FAMILY-3 (F3) are both defined here; research only, proposes nothing (a spot leg needs the user's word) | **作废条件:** L4 frozen inputs (`l4_inputs.npz` 3d9d3466…, `L4_SERIES.npz` 8ba4ba1f…, `l4_run.py` cfa25171…) change; feasibility receipt `receipts/pod2/FEAS_L4b.json` replaced; any change to §2–§8 after the first mark is computed (only a dated AMENDMENT written before marks may change them)

# PREREG · L4b · Executable exit marks for L4's forced-exit holds, rebuilt from raw 1m archives

Upstream: `../L4/RESULT_L4.md` §10–§11 (commit ad7c2b5b). Lead's task L4b (2026-09-13): rebuild marks from raw data; report per-event marks and hold P&L; re-run A01–A08 as POST-HOC-FAMILY-2 with its own N; conditional exit-rule family. Facts carried in: on identical positions, the frozen premium-index marking (B2) and the Binance close marking (B1) disagree in sign, and the whole disagreement sits in holds closed by forced exits. In those events raw B2 repeats one value for 6–24+ anchors. Neither instrument was validated there.

## §0 Questions
- **Q1** For every A01–A08 hold closed by forced exit (a) spot not tradable for 6 anchors or (b) no funding event in 24h (population P_F), and a matched control of normal-exit holds (P_C): what are the hold P&Ls under M-PREM (L4 B2), M-CLOSE (L4 B1) and M-EXEC (buy-and-hold hedged P&L on raw 1m last-traded prices with the exit rules of §4)?
- **Q2** Did a Binance delisting announcement precede each event's blowout? (Join to L3's committed census; §6.)
- **Q3 (F2)** Under M-EXEC, what are A01–A08's S2426 and full-window net? Does any arm survive (§7)?
- **Q4 (F3, conditional)** Does an exit within N anchors of a delisting announcement or a funding stop change that (§8)?

## §1 Looked at before this freeze (disclosure)
- All of L4 (PREREG, AMENDMENT 1, RESULT, TABLES, POST-HOC receipts).
- `receipts/pod2/FEAS_L4b.json` (device `devices/l4b_feasibility.py`, b9013403…, commit 1653b222, rc=0).
  - Re-simulating A01–A08 reproduces the L4 net series bitwise (8/8).
  - 1,747 holds: normal / forced_a / forced_b / forced_c / open = A01 200/11/10/19/7, A02 261/12/10/22/7, A03 195/12/10/19/7, A04 256/13/10/22/7, A05 119/8/7/2/0, A06 168/8/7/2/0, A07 116/8/7/2/0, A08 166/8/7/2/0.
  - **P_F = 148 arm-holds, 35 unique (symbol, entry, exit), 23 symbols:** 1000BTTC, BNX, XEM, BOND, LOOM, AMB, LINA, MDT, ALPHA, BSW, LOKA, MKR, BAKE, HIFI, KDA, FLM, PERP, FIS, FIO, DEGO, DENT, TON, SCRT.
  - Archive coverage of required (symbol, month) monthly 1m zips, all complete: spot 654/654 (0.88 GB), perp 654/654 (0.96 GB), markPrice 654/654 (0.51 GB), indexPrice 654/654 (0.56 GB), premiumIndex 39/39 for P_F symbols (0.02 GB).
- No raw price, mark, index or premium value from the archive has been read. Symbol names and dates of P_F were seen (they are L4 outputs).

## §2 Population
- Holds come from L4's frozen state machine: A01–A08, committed core, bitwise-equal series. Unit n = 1/(K·1.5) per unit sleeve capital; positions and their timing are L4's.
- **P_F**: holds with L4 exit reason forced_a or forced_b (148 arm-holds).
- **P_C**: matched controls. Process P_F holds in order (exit time, symbol, entry). For each P_F hold h in arm a, take the **2** normal-exit holds of arm a with a different symbol that are not yet used as controls in arm a. Rank by smallest |exit − h.exit|, then smallest |length − h.length|, then lower symbol index, then earlier entry. Up to 296 arm-holds.
- forced_c holds (premium missing for 6 anchors) are not in P_F. In F2 they are marked like normal exits and counted separately.
- Per-event tables deduplicate by (symbol, entry, exit); P&L sums are per arm-hold.

## §3 Raw data and derived prices (pod2; data.binance.vision static CDN only)
- **Families** (monthly zips; archive `.CHECKSUM` sha256 verified per zip):
  - every F2 (symbol, month) of FEAS_L4b: `spot/monthly/klines/<SPOT>/1m`, `futures/um/monthly/klines/<PERP>/1m`, `futures/um/monthly/markPriceKlines/<PERP>/1m`, `futures/um/monthly/indexPriceKlines/<PERP>/1m`;
  - P_F symbols only: `futures/um/monthly/premiumIndexKlines/<PERP>/1m`.
  - Spot symbol and price_mult come from trackA `perp_to_spot_map.json` (b17eb0ba…), as in L4; spot prices are multiplied by price_mult.
- **Handling**: zips are held in memory, verified, parsed and never written to disk (raw on disk ≈ 0, always < 1 GB). A dd probe of 600 MB (written and deleted) runs before the pull and after each 100 symbols; ≤ 8 worker processes, CPU only. A host allowlist admits only data.binance.vision; fapi/api hosts are asserted absent. Every request is logged.
- **Timestamps**: open_time > 1e14 ⇒ microseconds, else milliseconds; minute bar = [open, open + 60 s).
- **Traded minute** = number_of_trades > 0. **Last traded price at time t** = close of the latest traded minute whose bar end ≤ t; its staleness = t − bar end.
- **Anchor values** for every grid anchor E in each symbol's contiguous required months (carrying the last trade across month boundaries; reset across gaps):
  - S(E), P(E) = last traded spot / perp price at E, with staleness;
  - MARK(E), INDEX(E), PREM(E) = close of the latest bar with end ≤ E, with staleness;
  - S5(E), P5(E) = last traded prices at E − 5 min (for the B1 reproduction gate).
- **Minute store** for P_F symbols over their required months: spot close / quote volume / trades, perp close / quote volume / trades, mark, index, premium.

## §4 Marks and exit rules
- **M-PREM** and **M-CLOSE**: exactly L4 (n·1e4·(b̃_in − b̃_out), frozen inputs).
- **M-EXEC (buy-and-hold hedged)**:
  - Entry at anchor E_in: S0 = S(E_in), P0 = P(E_in) if staleness ≤ 60 min. Otherwise use the first traded close after E_in within 60 min (counted). If still none, the hold is ENTRY-UNPRICEABLE: excluded from M-EXEC sums, counted, and its L4 B2 basis kept in F2 (declared).
  - Units u_S = n/S0 (long spot), u_P = n/P0 (short perp).
  - Value path V(t) = u_S·S(t) − u_P·P(t). Per-anchor basis increment on window i = (V(E_{i+1}) − V(E_i))·1e4 bps per unit capital; a hold telescopes to u_S(S_x − S0) − u_P(P_x − P0).
  - **Normal, forced_c and open holds**: exit prices S(E_out), P(E_out) (open holds marked at 2026-08-31 00Z). No extra stress; L4 costs apply.
  - **P_F holds**:
    - τ_S, τ_P = last traded minute (bar end) of spot and perp within (E_in, E_out].
    - A leg has **stopped** if E_out − τ ≥ 20 h (no trade in the final 20 h). If both legs stopped, the earlier τ is the stopped leg and the other is "continuing". If neither stopped, the hold is **NO-STOP**: exit both legs at E_out marks with no stress, in every variant; labelled.
    - Stress (adverse): stopped leg 1,000 bps (spot sold at ×0.90, perp bought back at ×1.10); continuing leg 50 bps.
    - **PRIMARY X1σ1 (last traded closes, synchronised)**: exit time t_x = τ_stop. Stopped leg at its close at τ_stop. Continuing leg at its last traded close with bar end ≤ τ_stop if staleness ≤ 60 min, else its first traded close after τ_stop within 60 min, else its last traded close ≤ τ_stop (staleness counted). Stress applied.
    - **X1σ0**: X1 without stress.
    - **X2σ1 (state-machine timing)**: stopped leg at its last print at τ_stop; continuing leg at S(E_out) or P(E_out). The continuing leg is unhedged from τ_stop to E_out. Stress applied.
    - **X3σ1 (detection time, stopped leg off-Binance)**: stopped spot leg at INDEX(E_out) × 0.90; stopped perp leg settles at the mean of indexPrice 1m closes over the 30 minutes ending at τ_P, ×1.005; continuing leg at its E_out price with 50 bps stress.
  - **When one leg stops first**: X1 closes the other leg at the same time (optimistic, hindsight). X2 and X3 leave it open until the sleeve detects the stop at the forced-exit anchor, as L4's state machine would. X1 and X2 use the stopped leg's last print, which a real trader cannot know in advance; X3 is the only variant that values the stranded leg at the moment of detection.
  - **Income under M-EXEC**: L4 income (n × Σ settled rates) for events S ≤ exit time of the perp leg (X1: S ≤ τ_stop; X2/X3: S ≤ E_out; normal: as L4).
  - **Costs**: L4 turnover cost unchanged (13.92 × n per entry and exit). A P_F exit cost is booked in the window containing its exit time.
  - After a P_F exit the slot stays empty until L4's E_out (no refill; L4 positions unchanged).
- **Flags** (descriptive only):
  - SPOT-DISCONTINUITY / PERP-DISCONTINUITY: one-minute close ratio outside [0.2, 5] for one leg while the other leg's ratio over the same minute is inside [0.8, 1.25] (possible redenomination).
  - **Blowout** = first anchor in (E_in, t_exit] where both legs traded within 60 min and |P/S − 1| ≥ 500 bps. Report its time and the peak |P/S − 1|.

## §5 Gates (all must pass before any mark or reading is printed; failure ⇒ stop, AMENDMENT)
| gate | rule |
|---|---|
| G-L4REPRO | A01–A08 re-simulation equals `L4_SERIES.npz` net bitwise; hold list equals FEAS_L4b |
| G-ARCHIVE | every required zip: HTTP 200, sha256 = archive `.CHECKSUM`, CSV parsed, row count > 0 (or, if empty, the month is recorded as no trades); manifest complete (654 × 4 + 39) |
| G-HARNESS | the F2 accounting harness driven by L4's B2 increments reproduces L4's per-anchor net for A01–A08 to ≤ 1e-9 |
| G-B1REPRO | on held anchors of P_F ∪ P_C where L4 B1 is finite and both reconstructed legs at E − 5 min are ≤ 60 min stale: \|(P5/S5 − 1) − L4 b1\| ≤ 1e-6 in ≥ 99 % of cells (mismatches listed) |
| G-PREMPARSE | on P_F held anchors where L4 B2 changes from the previous anchor: \|PREM(E) − B2(E)\| ≤ 1e-7 in ≥ 95 % (checks parsing and alignment; agreement on frozen stretches is a reading, not a gate) |
| G-SYN2 | synthetic minute worlds vs an independent pure-Python reference of §4 (both legs trade; spot stops first; perp stops first; both stop; NO-STOP; stale entry; μs timestamps; stress; income cut at τ): hold P&L and per-anchor increments exact to 1e-9 in every variant |

## §6 Readings
- **R1 per event** (unique symbol/entry/exit, with every arm-hold it covers):
  - reason; τ_S, τ_P; which leg stopped and the gap in hours; NO-STOP flag;
  - exit-time marks: B2 and B1 at E_out, plus M-EXEC exit prices and implied P/S − 1 under each variant;
  - hold P&L (bps per unit sleeve capital, per arm) under M-PREM, M-CLOSE, M-EXEC X1σ1 / X1σ0 / X2σ1 / X3σ1, plus L4 income and cost;
  - blowout time and peak; the longest run of identical 1m premium closes in the final 7 days; mark/index availability; discontinuity flags;
  - announcement precedence: PRECEDED if a Binance delisting announcement for the base asset was published in [blowout − 60 d, blowout] (or [E_in − 60 d, t_exit] if no blowout); AFTER if only after; NONE FOUND; or PENDING L3 if L3 has no committed census when R1 is computed.
- **R2 controls**: the same three marks for P_C; agreement of M-EXEC with M-CLOSE and M-PREM on P_C vs P_F (median \|Δ\|, Spearman).
- **R3 F2 re-run** (A01–A08; X1σ1 primary; the three sensitivities alongside):
  - per arm × {Y22…Y26, S2426, FULL}: net mean with CI95 (L4's 30-day circular block bootstrap, B = 20,000, rng [20260913, 42, arm, span, purpose]), Sharpe, position share (= L4), basis mean, income, cost;
  - ρ to A0 per anchor and per day (both seeds); the L4 rule flags;
  - descriptive: primary with discontinuity-flagged holds' basis set to 0.
- **R4 announcement join** summary; **R5 F3** (conditional).

## §7 POST-HOC-FAMILY-2: N and survival rule (frozen)
- **N_F2 = 8** (A01–A08 under the primary marks). The three sensitivities select nothing: they only enter the survival conjunction below, which can only make survival harder.
- Cumulative ledger: 12 (L4) + 8 = 20, reported.
- An arm **survives F2** iff:
  - under X1σ1, L4's P0 ∧ P1 ∧ P3 hold **and** the S2426 net CI lower bound at the 0.025/8 quantile (0.3125 %) is > 0; **and**
  - the S2426 net mean is > 0 under each of X1σ0, X2σ1 and X3σ1.
- Also reported: survival with the unadjusted CI and with the cumulative-20 bound (0.125 %).
- Statement: "no arm survives" or the list of surviving arms.

## §8 FAMILY-3 (pre-declared exit rule; conditional)
- **RUN condition**: at the time the F2 re-run is complete, L3 has committed a census of Binance delisting announcements (spot and USDⓈ-M futures) with UTC publish timestamps and base assets, and its own receipt states coverage of 2022-01-01…2026-08-31. Otherwise **NOT RUN**, stated as such. A thin adapter mapping L3's fields to (base asset, segment, publish time) is written after L3 commits and before any F3 number, and is committed before it runs.
- **Triggers** for a held name:
  - (i) a delisting announcement for its base asset (the perp symbol without USDT and without a 1000/1000000 prefix, or the spot base) published at T_a ∈ [E_in − 30 d, E_out] and, if L3 gives an effective delisting time, with that time after E_in; trigger time = max(T_a, E_in);
  - (ii) a funding stop: the first anchor E_i in the hold where E_i − (last funding event) > (true spacing of that event) + 4 h.
- **Exit** at the anchor N anchors after the first anchor at or after the earlier trigger, capped at L4's E_out; N ∈ {0, 3}.
  - If that exit anchor is before the stopped leg's τ: both legs exit at S/P(E_exit) with 50 bps stress each.
  - Otherwise the §4 PRIMARY rule applies.
  - Income stops at the F3 exit; no refill.
- **N_F3 = 16** (8 arms × 2). An arm survives F3 iff L4's P0 ∧ P1 ∧ P3 and S2426 CI lower bound at the 0.025/16 quantile > 0 under F3 marks (M-EXEC primary); cumulative ledger 12 + 8 + 16 = 36 reported.

## §9 Devices, runs, limits
- Devices, each committed before it runs:
  - `devices/l4b_pull.py` (pod2): pull, verify, derive; gate G-ARCHIVE; writes anchor values, minute store, manifest.
  - `devices/l4b_marks.py` (pod2): G-L4REPRO, G-HARNESS, G-B1REPRO, G-PREMPARSE, G-SYN2; marks, R1–R3, F2 verdict.
  - `devices/l4b_ann_join.py` and `devices/l4b_f3.py`: only if L3 commits in time.
  - `devices/l4b_tables.py` (local).
- Receipts under `receipts/pod2/`; `SHA256SUMS` via the T6 guard; foreground runs with rc and a SUMMARY line; pod2 PIDs 333197 / 339489 untouched; memory ≤ 61 GB.
- **Limits declared in advance**:
  - X1 and X2 exits at the stopped leg's last print are hindsight bounds.
  - The index is only a proxy for an off-Binance price.
  - 1m closes are not order-book depth; the stress levels are given numbers.
  - Income keeps L4's constant-notional definition while marks are buy-and-hold.
  - Redenominations are flagged, not adjusted.
  - The no-refill convention understates deployment after early exits.
  - Announcement precedence depends entirely on L3's census.
