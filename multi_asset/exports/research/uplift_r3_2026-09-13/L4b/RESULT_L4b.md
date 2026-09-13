> **创建:** 2026-09-13 ~13:1xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (worker L4, task L4b from lead) | **状态:** RESULT — POST-HOC-FAMILY-2 statement **no arm survives** under `PREREG_L4b_executable_marks_2026-09-13.md` (sha256 bd7ad1e4…, frozen 2026-09-13T12:28:31Z, commit ff41b981); FAMILY-3 **NOT RUN** (L3 census not committed when F2 completed, 12:57Z); announcement precedence **PENDING L3**; §4 is descriptive (device written after reading the tables, changes nothing); not re-run by lead; research only, proposes nothing | **作废条件:** L4 inputs or `L4_SERIES.npz` change; `RECEIPT_L4b_marks.json` (439519a7…) or `L4b_F2_SERIES.npz` (825936ee…) replaced; a Binance settlement record shows perp positions in the stopped-perp events were closed at prices other than those assumed in §3

# RESULT · L4b · Executable exit marks for L4's forced-exit holds, from raw 1m archives

Units: hold P&L in **bps per unit of sleeve capital** for one arm-hold (n = 1/(K·1.5) notional per name); F2 series in bps per 4h anchor per unit capital. Every number is in `receipts/pod2/TABLES_L4b.md` (rendered by `devices/l4b_tables.py` from `RECEIPT_L4b_pull.json` and `RECEIPT_L4b_marks.json`) or, for §4, `receipts/pod2/DESC_L4b_stops.json`. Marks: **M-PREM** = L4's premium index (B2); **M-CLOSE** = L4's Binance perp/spot 5m closes (B1, first-order basis); **M-EXEC** = buy-and-hold hedged P&L on raw 1m last-traded prices with the frozen exit rules (primary X1σ1 = both legs at the stopped leg's last print, stopped leg −10 %, continuing leg −50 bps; sensitivities X1σ0 no stress, X2σ1 continuing leg at the forced-exit anchor, X3σ1 stranded leg valued off-Binance at detection).

## §0 One page

**VERIFIED (frozen devices, all gates green):**
1. **No arm survives POST-HOC-FAMILY-2** (N_F2 = 8; cumulative ledger 12 + 8 = 20). Every arm fails **P1**, because 2025 is negative under the primary marks (−0.17…−0.38 bps/anchor). Every arm also fails the S2426 CI rule at every level (Bonferroni-8, unadjusted, cumulative-20) and the sensitivity conjunction (X2σ1 S2426 net < 0 in all arms). P0 and P3 still pass; ρ to A0 stays ≈ 0.
2. **S2426 net per arm**, as L4 premium marks → M-EXEC X1σ1 [CI95] / X1σ0 / X2σ1 / X3σ1:

   | arm | L4 M-PREM | X1σ1 [CI95] | X1σ0 | X2σ1 | X3σ1 |
   |---|---|---|---|---|---|
   | A01 | +0.2660 | −0.0215 [−0.2505, +0.2217] | +0.1929 | −0.3051 | −0.1312 |
   | A02 | +0.2127 | +0.0709 [−0.0848, +0.2557] | +0.1781 | −0.0710 | +0.0160 |
   | A03 | +0.2496 | −0.0485 | +0.1659 | −0.3322 | −0.1583 |
   | A04 | +0.2050 | +0.0577 | +0.1649 | −0.0842 | +0.0028 |
   | A05 | +0.1256 | −0.0794 | +0.0950 | −0.2460 | −0.1447 |
   | A06 | +0.1107 | +0.0085 | +0.0958 | −0.0747 | −0.0241 |
   | A07 | +0.1099 | −0.1003 | +0.0741 | −0.2669 | −0.1656 |
   | A08 | +0.1029 | −0.0019 | +0.0853 | −0.0852 | −0.0345 |

3. **What the forced exits are**:
   - **148 arm-holds on 35 unique entries and 23 symbols; every one is a delisting-type stop except LOOM.** The stopped leg is identified from raw trades.
   - **Perp stopped first:** 20 entries, 14 symbols (1000BTTC, BNX, AMB, LINA, MDT, LOKA, MKR, KDA, FIS, FIO, DEGO, DENT, TON, SCRT). Perp trading ends around 09:00 UTC; L4's forced exit fires about 23 h later (AMB 91 h, LINA 43 h, **MDT 9,599 h**).
   - **Spot stopped first:** 14 entries, 8 symbols (XEM, BOND, ALPHA, BSW, BAKE, HIFI, FLM, PERP). Spot trading ends around 03:00 UTC; the forced exit fires 25 h later.
   - **Unpriceable:** LOOM, with no trade in either leg during its 1-day hold.
4. **Hold P&L summed over the 148 arm-holds** (a sum across arms, not a portfolio figure):

   | mark | perp-stopped (90) | spot-stopped (56) | all |
   |---|---|---|---|
   | M-PREM | −1,731 | +43 | −1,685 |
   | M-CLOSE | −24,606 | −1,857 | −26,462 |
   | X1σ1 | −5,990 | −2,860 | −8,849 |
   | X1σ0 | −1,622 | −138 | −1,761 |
   | X2σ1 | −13,232 | −3,639 | −16,870 |
   | X3σ1 | −9,008 | −2,781 | −11,789 |

   L4 income on these holds: +1,164 (perp-stopped), +332 (spot-stopped).
   - Frictionless exits at the last print (X1σ0) cost about what the frozen premium marks said in aggregate.
   - The close-based basis mark overstated losses about 15×, because a first-order basis change is not the hedged P&L when prices diverge 3–4×.
   - Any friction flips the sleeve: 10 % slippage on the stopped leg, or holding the other leg until the state machine notices.
5. **Instruments agree on normal exits** (296 matched controls): median \|EXEC − CLOSE\| 0.71 and \|EXEC − PREM\| 0.83 bps·capital; Spearman 0.58 / 0.38; sums EXEC +977, CLOSE +318, PREM +730. On forced exits the medians are 49 / 43. The L4 disagreement is a delisting phenomenon, not general mark noise.
6. **Why L4 held dead hedges (descriptive, VERIFIED on raw data)**:
   - After a perp stops trading, the archive keeps writing untraded 1m rows with **one frozen close**, which passes L4's close-based tradability flag. MDT had 575,939 such minutes over 400 days; AMB 5,460; LINA 2,578; the other perp-stopped events about 1,380, i.e. 23 h.
   - fund_aug keeps recording funding for some stopped perps (MDT 1,197 events after its last trade; AMB 23; LINA 5; BTTC 3; BNX 3), so the no-funding exit never fired.
   - The 1m premium index sits on one value from the perp stop onward (longest identical run in the last 7 days: MDT 10,080 min, AMB 5,460, LINA 2,579, most others about 1,380). L4's frozen B2 values are therefore archive content, not a panel artifact; G-PREMPARSE matched the 1h values 2,430/2,430.
7. **FAMILY-3 NOT RUN; announcement precedence PENDING L3.** L3 had no commit when F2 completed (12:57Z); the frozen run condition was not met. N_F3 = 16 was not spent.

**INFERRED:**
- On premium marks the sleeve looked alive, but its economics depend on how a few dozen delisting events are exited.
- It survives only with frictionless exits at the last traded print (X1σ0 keeps every arm positive, S2426 +0.07…+0.19). That is a hindsight bound nobody can execute without knowing the stop in advance.
- With the pre-declared slippage, or with the state machine's detection lag, it is gone.
- The one open route is to exit **before** the stop on the delisting announcement, which Binance typically publishes days ahead. That is exactly F3, which needs L3's census.
- Nothing about a spot leg should go to the user on current evidence.

## §1 Gates (all passed before any mark was printed; `TABLES_L4b.md` T0)
| gate | reading |
|---|---|
| G-ARCHIVE | spot/perp/mark/index 1m 654/654 each and premium 39/39: HTTP 200, archive CHECKSUM sha256 equal on all 2,655 zips, 0 empty, 0 duplicate minutes, 160 spot files in µs timestamps; dd probes (600 MB) at start, after 100 symbols and at end OK; raw zips never written to disk; 0.88 + 0.96 + 0.51 + 0.56 + 0.02 GB streamed |
| G-L4REPRO | A01–A08 re-simulation equals `L4_SERIES.npz` bitwise; 1,747 holds equal to FEAS_L4b |
| G-SYN2 | 17 synthetic cases (both legs trade / spot stops / perp stops / both stop × 4 variants + stale-entry fallback) equal to an independent closed-form reference |
| G-B1REPRO | 21,618 held anchor cells: reconstructed perp/spot − 1 at E − 5 min equals L4 B1 within 1e-6 in **100 %** (max \|Δ\| 1.09e-7). The extreme B1 values in L4 are genuine archive closes |
| G-PREMPARSE | 2,430 P_F anchors where B2 moves: 1m premium close at E equals B2 within 1e-7 in 100 % |
| G-HARNESS | the F2 accounting driven by L4's B2 increments reproduces L4's per-anchor net for A01–A08 to ≤ 7.1e-15 |

## §2 Per-event marks and hold P&L (arm A01 shown where it holds the event, else A05/A02/A03; all arms in `TABLES_L4b.md` T1)

| symbol · entry → exit | stopped leg · gap h | peak \|P/S−1\| bps (blowout) | M-PREM | M-CLOSE | X1σ1 | X1σ0 | X2σ1 | X3σ1 | L4 income |
|---|---|---|---|---|---|---|---|---|---|
| 1000BTTC 22-04-11→04-12 | perp · 23 | 0 | +0.0 | +0.0 | −70.4 | −0.3 | −98.2 | −31.6 | +1.3 |
| BNX 23-01-28→02-02 (A02) | perp · 24 | 24 | +0.3 | +0.1 | −34.3 | +0.3 | −33.5 | −2.5 | +0.8 |
| XEM 24-06-14→06-18 | spot · 25 | 89 | +0.7 | −0.7 | −56.2 | −0.3 | +17.5 | −49.1 | +4.9 |
| BOND 24-07-18→07-23 | spot · 25 | 121 | −1.5 | +11.1 | −88.5 | +1.4 | +45.3 | −76.4 | +5.1 |
| LOOM 24-08-26→08-27 (A03) | — (no trades) | — | +1.7 | +0.0 | unpriceable | | | | −0.2 |
| AMB 25-02-19→02-25 | perp · 91 | 259 | −175.1 | −1,807.5 | −190.6 | −136.5 | −435.0 | −367.6 | +76.1 |
| LINA 25-03-26→03-29 | perp · 43 | 99 | −64.1 | −799.1 | −169.0 | −87.4 | −505.9 | −416.6 | +23.2 |
| MDT 24-05-15→25-06-20 | perp · **9,599** | 43 | −2.8 | −2,138.6 | −101.1 | −30.2 | −583.4 | −505.3 | +81.8 |
| ALPHA 25-07-04→07-05 | spot · 25 | 1,412 (07-04 04Z) | −0.9 | −99.0 | −72.1 | −9.2 | −165.9 | −74.8 | +0.5 |
| BSW 25-07-02→07-05 | spot · 25 | 2,500 (07-04 04Z) | +1.2 | −170.1 | −58.8 | −12.9 | −182.2 | −57.9 | +3.7 |
| LOKA 25-07-19→07-22 | perp · 23 | 60 | −2.5 | −39.0 | −83.1 | −5.4 | −124.1 | −52.0 | +3.3 |
| MKR 25-09-06→09-09 | perp · 23 | 35 | −0.4 | +64.2 | −66.9 | −2.9 | −1.7 | +56.3 | +1.0 |
| BAKE 25-09-08→09-18 | spot · 25 | 829 (09-17 04Z) | −0.2 | −52.2 | −103.9 | −7.7 | −214.1 | −113.8 | +9.9 |
| HIFI 25-09-15→09-18 | spot · 25 | 1,750 (09-17 04Z) | +5.2 | −81.8 | −22.7 | +1.1 | −196.9 | −39.0 | +1.8 |
| KDA 25-11-01→11-07 | perp · 23 | 140 | +15.3 | +65.6 | −13.4 | +20.9 | +2.3 | +33.7 | +13.6 |
| FLM 25-11-01→11-13 | spot · 25 | 185 | +2.3 | +9.4 | −49.3 | −1.7 | −33.0 | −42.3 | +31.2 |
| PERP 25-11-10→11-13 | spot · 25 | 248 | +0.6 | −10.6 | −59.5 | −1.0 | −45.7 | −55.2 | +4.8 |
| FIS 25-12-09→12-11 | perp · 23 | 130 | +0.8 | −32.4 | −65.6 | +5.7 | −103.6 | −38.2 | +2.0 |
| FIO 26-04-11→04-16 | perp · 23 | 102 | −37.4 | −57.9 | −67.4 | −22.1 | −73.7 | −31.7 | +13.8 |
| DEGO 26-04-18→04-22 | perp · 23 | 167 | −4.2 | −100.8 | −81.9 | −18.7 | −143.7 | −86.0 | +9.2 |
| DENT 26-04-19→04-22 | perp · 23 | 429 | −21.9 | −291.1 | −112.6 | −14.2 | −384.4 | −298.3 | +3.6 |
| TON 26-06-22→06-24 | perp · 23 | 43 | +0.2 | −3.0 | −66.8 | +1.6 | −70.1 | −7.1 | +7.6 |
| SCRT 26-08-20→08-27 | perp · 23 | 123 | +1.1 | +7.6 | −38.5 | +3.1 | −35.4 | +2.5 | +7.5 |

- Blowouts (|P/S−1| ≥ 5 % with both legs traded within 60 min) occur only at spot delistings, in the hour after the final spot prints (ALPHA, BSW, BAKE, HIFI).
- Exit prices for each variant are in `TABLES_L4b.md` T1 (exit-prices sub-table).
- No discontinuity flag (possible redenomination) fired.
- **Announcement precedence: PENDING L3 for all 35 entries.**

## §3 POST-HOC-FAMILY-2 by year (`TABLES_L4b.md` T3; X1σ1 net [CI95], position share = L4)

| arm | Y22 | Y23 | Y24 | **Y25** | Y26 | FULL [CI95] |
|---|---|---|---|---|---|---|
| A01 | −0.0390 | +0.2645 [+0.1047, +0.4483] | +0.2654 | **−0.3437 [−0.6465, −0.0750]** | +0.0308 | +0.0374 [−0.1068, +0.1892] |
| A02 | −0.0195 | +0.2061 | +0.3432 [+0.0314, +0.7355] | **−0.1654 [−0.3162, −0.0276]** | +0.0154 | +0.0823 [−0.0166, +0.1963] |
| A04 | −0.0215 | +0.2071 | +0.3379 | **−0.1682** | −0.0255 | +0.0744 |
| A05 | −0.0033 | +0.1125 | +0.2007 | **−0.3649** | −0.0725 | −0.0223 |
| A06 | −0.0016 | +0.0827 | +0.2286 | **−0.1824** | −0.0363 | +0.0227 |
| A08 | −0.0016 | +0.0825 | +0.2315 | **−0.1877** | −0.0746 | +0.0166 |

2023 is untouched by forced exits and stays positive; 2025 carries 13 of the 23 stopped symbols. Survival table (`TABLES_L4b.md` T3, "F2 survival"): all arms P0 yes, P1 no, P2 (Bonf-8 / unadj / cum-20) no, P3 yes, sensitivities no ⇒ **no arm survives**, under the adjusted, unadjusted and cumulative-20 rules alike.

## §4 Mechanism (descriptive device `l4b_desc_stops.py`, committed before running; `DESC_L4b_stops.json`)
- **Perp-stopped events:**
  - after τ_perp, every minute until L4's exit has an archive row with zero trades and a single distinct close (MDT 575,939 rows / 1 close; AMB 5,460 / 1; LINA 2,578 / 1; the other 11 symbols 1,378–1,380 / 1);
  - funding events after τ_perp: MDT 1,197 (2024-05-16 16:00Z…2025-06-19 08:00Z), AMB 23, LINA 5, 1000BTTC 3, BNX 3, all others 0.
- **Spot-stopped events:** no spot rows at all after τ_spot (0 of 1,500 minutes), so L4's spot flag drops and the forced exit follows 6 anchors later.
- **Reading:** L4's tradability flag is built from 5m closes (trackA a1 basis), and its funding-stop exit assumes funding records imply trading. Both hold on normal names and both fail at perp delistings. The frozen state machine kept marking a perp that had not traded for 400 days (MDT) and kept booking its funding. This is an input-semantics defect of L4's paper sleeve, not of the executor.

## §5 FAMILY-3 and announcements
- FAMILY-3 (exit N ∈ {0, 3} anchors after a delisting announcement or a funding stop; N_F3 = 16) is **NOT RUN**. At F2 completion (2026-09-13 12:57Z), `uplift_r3_2026-09-13/L3` had no commit, which fails the frozen RUN condition (PREREG §8). The definition stays frozen and can run as a dated step once L3 commits a census with UTC publish times and a stated 2022–2026 coverage. It needs no new raw data: the F2 pull covers every held name-month.
- Announcement precedence for the 35 entries is **PENDING L3**. L3 was told the join fields and the symbol list (message 2026-09-13 ~12:3xZ).

## §6 Verified vs inferred
- **Verified (receipts):**
  - all gates;
  - the stopped-leg classification and τ times from raw trades;
  - every hold P&L under the three marks and four executable variants;
  - the F2 per-arm, per-year series and the survival flags;
  - control-vs-forced agreement;
  - the archive behaviour after stops (frozen untraded rows, funding records, frozen premium);
  - that L4's extreme B1 values reproduce exactly from raw closes.
- **Inferred:**
  - that an announcement-based exit could restore the sleeve;
  - that 10 % stopped-leg slippage is a fair stress (it is a given number; X1σ0 and X3σ1 bracket it);
  - that Binance settled the stopped perps near the index (X3 assumes an index TWAP; no settlement record was read);
  - that the MDT funding after its perp stopped was never actually paid.

## §7 Limits and deviations
- X1 and X2 use the stopped leg's last print, which is hindsight. X3 uses the index as an off-Binance proxy.
- 1m closes are not depth. Income keeps L4's constant-notional definition while marks are buy-and-hold.
- 1–2 holds per arm are unpriceable (including LOOM in A03/A04; counts per arm in `TABLES_L4b.md` T3) and keep their B2 basis. The entry fallback (first trade within 60 min) was used for 32 legs, counted across all arm × variant builds.
- F2 keeps L4's positions (no refill after early exits), so capital freed by an X1 exit stays idle until L4's exit anchor.
- Deviations from the PREREG device list:
  - `l4b_ann_join.py` / `l4b_f3.py` were not written (F3 not run).
  - `l4b_desc_stops.py` was added as a descriptive device after reading the tables.
  - The marks device was re-committed twice before its run: a crash-proofing `.get` and the fallback counter (`4c716e28`).
  - pod2 was unreachable from the Mac for about 10 minutes before the pull; no run was affected.

## §8 Reproduction (commands as run) and files
pod2, `/workspace/uplift_r3_2026-09-13/L4b` (CPU only, `taskset -c 40-47`, `nice -n 10`; `nvidia-smi` 0 % / 2 MiB before and after; PIDs 333197 / 339489 `Tl` throughout; launched as `nohup bash work/<name>_cmd.sh`, scripts in `receipts/pod2/*_cmd.sh`):
```
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 taskset -c 40-47 /workspace/venv/bin/python devices/l4b_feasibility.py PATH,HOME,LC_CTYPE /workspace/uplift_r3_2026-09-13/L4/work /workspace/uplift_r3_2026-09-13/L4/devices/l4_run.py /workspace/review_scratch/allweather_trackA/spot/perp_to_spot_map.json work > work/l4b_feasibility_stdout.log 2>&1; echo rc=$? > work/l4b_feasibility_rc.txt
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 taskset -c 40-47 /workspace/venv/bin/python devices/l4b_pull.py PATH,HOME,LC_CTYPE work/FEAS_L4b.json work 8 > work/l4b_pull_stdout.log 2>&1; echo rc=$? > work/l4b_pull_rc.txt
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 taskset -c 40-47 /workspace/venv/bin/python devices/l4b_marks.py PATH,HOME,LC_CTYPE /workspace/uplift_r3_2026-09-13/L4/work /workspace/uplift_r3_2026-09-13/L4/devices/l4_run.py work > work/l4b_marks_stdout.log 2>&1; echo rc=$? > work/l4b_marks_rc.txt
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 taskset -c 40-47 /workspace/venv/bin/python devices/l4b_desc_stops.py PATH,HOME,LC_CTYPE work > work/l4b_desc_stops_stdout.log 2>&1; echo rc=$? > work/l4b_desc_stops_rc.txt
```
local, `multi_asset/exports/research/uplift_r3_2026-09-13/L4b`:
```
python3 devices/l4b_tables.py receipts/pod2 > receipts/pod2/l4b_tables_stdout.log 2>&1; echo "rc=$?" > receipts/pod2/l4b_tables_rc.txt
```
Summary lines, all rc=0:
- `SUMMARY l4b_feasibility series_equal=8/8 holds=1747 forced_ab_holds=148 unique_events=35 f2 sym=177 name-months=654 pop sym=23 name-months=39 | spot_1m 654/654 0.88GB perp_1m 654/654 0.96GB mark_1m 654/654 0.51GB index_1m 654/654 0.56GB premium_1m 39/39 0.02GB | listing 310s self_sha256=b9013403fa1241ab`
- `SUMMARY l4b_pull G-ARCHIVE=True spot_1m 654/654 ck654 0.88GB perp_1m 654/654 ck654 0.96GB mark_1m 654/654 ck654 0.51GB index_1m 654/654 ck654 0.56GB premium_1m 39/39 ck39 0.02GB symbols=177 elapsed=792s self_sha256=ed1195350752aded`
- `SUMMARY l4b_marks gates={'G-L4REPRO': True, 'G-SYN2': True, 'G-B1REPRO': True, 'G-PREMPARSE': True, 'G-HARNESS': True} | P_F=148 P_C=296 events=35 | F2 no arm survives | S2426 net X1s1 {'A01': -0.0215, 'A02': 0.0709, 'A03': -0.0485, 'A04': 0.0577, 'A05': -0.0794, 'A06': 0.0085, 'A07': -0.1003, 'A08': -0.0019} | elapsed=25s self_sha256=19b8595d3be927a8`
- `SUMMARY l4b_desc_stops events=35 self_sha256=f782242e47c3b623`
- `SUMMARY l4b_tables lines=181 statement=no arm survives`

Commits: 1653b222 (feasibility device), ff41b981 (PREREG + feasibility receipts), d7efe276 (pull + marks devices), 6236f737 (tables device), 4c716e28 (marks re-commit before run), a76d3347 (descriptive device), plus this RESULT commit. Hashes are in `SHA256SUMS` (T6 guard). `*.npz` are git-ignored: `receipts/pod2/L4b_F2_SERIES.npz` is local, and per-symbol stores (151 MB) stay on pod2 `work/sym/`, hashed in `RECEIPT_L4b_pull.json`.
