> **创建:** 2026-09-13 15:2xZ | **Session:** FX-MODEL (fix worker, teammate of team-lead) | **状态:** PAUSED on lead order (account limit) | **作废条件:** superseded by the next STATE or REPORT_FX_MODEL.md

# FX-MODEL pause note

Items: FEA-01 (P1), TIM-01 (P1), UNI-01 (P2), TRD-05 (P3) + TRN-06 (coordination with fx-train), P10 (conditional).

## 1. Done (committed)

| Commit | What |
|---|---|
| `74cb2e66` | Fact devices, committed before running: `devices/fm_facts_code.py` (Mac, read-only code anchors), `devices/fm_facts_data.py` (pod2, read-only; computes no IC or return), `devices/run_pod2.sh` (sha check + env -i + nice 19 + rc line) |
| `a1c16b73` | `fm_facts_code.py` correction, committed before the rerun. C-FEA-4 narrowed from "same-family site" to "latent code path". My attempt-1 claim said the stored legs ZFD was built from the splice panel; F3 shows the stored rows are verbatim copies of the 08-23 legs file, which has full coverage. |
| `6b09524b` | Receipts:<br>• `FACTS_CODE.json` (sha 75fa15e6; device e965501e; 18 rows / 67 anchors; rc 0)<br>• `FACTS_CODE.attempt1_claim_C-FEA-4_overstated.json` (kept)<br>• `FACTS_DATA.json` (sha 9a7127d3; device 4d9df556; pod2 15:07:59–15:08:54Z; rc 0)<br>• `fm_facts_data.pod2.log` |

### Facts established (all VERIFIED, from receipts above)

**FEA-01 (funding columns)**
- **F1.** The v1 canonical panel has funding for exactly the 450 live_pins names (set equal), for f_fund_ema, f_fund_ema_v1 and f_fund_now alike. v2ext has 825 names. Splice rows up to the cut (2026-08-15 00Z) are bitwise equal to v1.
- **F2.** fea82 col 80 is exactly 0 where v2ext has a finite value on 34.15 / 33.96 / 33.63 / 24.72 / 13.94% of DL member pairs in 2022..26 (dlw_v4raw). In-service dlw_ext is the same size. Positive control: stored cols 80/81 equal f16(nan_to_num(splice)) with 0 mismatches.
- **F3.** The legs ZFD site is latent only.
  - Stored ZFD is finite wherever v2ext v1 is finite: 0 misses in 2023..25.
  - v4 legs miss 1.87% in 2022 and 1.59% in 2026. The in-service legs miss 0% and 0.15%.
  - Presumed cause, NOT yet checked: v4 members that are absent from the copied old rows.
- **F4.** On the 450 names before the cut, v1 equals v2ext exactly for f_fund_ema and f_fund_now (100% of 2,168,927 common cells); f_fund_ema_v1 matches on 99.985%, max|Δ| 0.0051. 3,740 cells are finite only in v2ext. The fill rule "splice where finite, else v2ext" therefore equals v2ext on common anchors for v0 / now.

**UNI-01**
- **U1.** Non-crypto share of member pairs is 0 / 0 / 0 / 2.8e-5 / 7.26% (2022..26), identical in the king v4 meta and dlw_v4raw; 80 non-crypto symbols appear.
- live_pins = COIN 449 + INDEX 1.

**TIM-01**
- **T1, score skew (no label).** Scoring on [E−w, E−1] vs [E−w+1, E] features, common members, 2024..2026-08:

| Booster | Spearman median | p5 | min | Top-decile overlap median | p5 | max\|Δ\|/sd median |
|---|---|---|---|---|---|---|
| v4 slow2026 | 0.9865 | 0.971 | 0.879 | 0.885 | 0.80 | 1.22 |
| in-service 8d79186b | 0.9866 | 0.971 | 0.873 | 0.889 | 0.81 | 1.25 |

- Member sets differ on 206 anchors; the new clock adds 2 early anchors.

**Code facts** (FACTS_CODE): anchors for every row of FEA-01, TIM-01, UNI-01, TRD-05/TRN-06 and P10, including two new same-family findings:
- The DL targets' member statistics use [E−2016, E−1], while DL features and producer members use [E−2015, E] (C-TIM-5).
- In the king clamp builder, the member statistics n7/qvm/m7/v7 use an unclamped E−2016 (C-TIM-2).

## 2. In progress

Nothing is running.
- No pod2 or GPU job of mine exists (checked after commit 6b09524b).
- No monitor or sleep loop.
- No uncommitted FX-MODEL file except this note.

## 3. Next steps (in order, when restarted)

1. **Render FACT_TABLE_MODEL.md/json** from the two receipts, with these additions:
   - TRD-05 dead-member counts on FX-DATA's artifact, once published.
   - P10 row: close as "no fix justified", citing aud-prod's receipt (see §4).
   - F3 check: confirm or refute the presumed cause of the 2022/2026 ZFD misses (v4 members absent from the copied rows).
2. **Red tests on the old builders**, on small real-shape fixtures:
   - fea82 zeroes funding for names outside the v1 prefix.
   - King window max row = E−1, and label [E, E+47].
   - DL targets member window excludes row E.
   - Member screens admit non-crypto names, admit a no-trade-24h name, and drop a finite-trailing name whose forward label is non-finite.
3. **New builders**, as new files with explicit knobs and no defaults. Each knob's legacy value must reproduce the old artifact bitwise (positive control).
   - `fm_king_fea_asof.py` (base pod_fea_ext_e.py): clock / members / tradability / class / col-80 caliber.
   - `fm_dlw_targets_asof.py`: member clock / as-of members.
   - `fm_dlw_features_fund.py`: fill rule / caliber.
   - King fit device: exporter section ① without export gates; OOF written for every member.
4. **Prereg, frozen before any retrain.** Draft design:
   - **Measurement without retraining:** A_train vs A_serve, i.e. old models scored on training inputs vs production-like inputs (TIM-01: v4 vs v4e features; FEA-01: saved monthly fold .pt on filled fea82, mu/sd recomputed by the trainer rule).
   - **DL retrain arms:** D0 baseline with the current trainer, D1 funding fill, D3 all fixes. Seeds s42/s2027, 20 monthly folds; about 43 min per seed per arm on GPU, based on the 09-09 logs.
   - **King retrain arms:** K0, K1 clock, K3 all.
   - **Readings:**
     - Score layer: per-asset P + xsec rank-IC, labelled by `equivalence_labels.py` with δ D4 0.003.
     - Book layer: research replay, labelled "uncertified replay", δ D1 0.05 / D2 0.10.
     - Leak checks: shuffle-future, offset peak at 0, zero out-of-fold leakage.
   - **Stated in advance:** a lower OOF IC after FEA-01 is expected, because the flag carries forward information, so it is not by itself evidence against adoption.

## 4. Coordination state

| Party | Asked (msg) | Answer |
|---|---|---|
| fx-data | 57941d9b: mask path/def/ETA; funding panel rebuild plan | **Answered.** Spec frozen 73b59ec0: tradable(A) ⇔ ≥ 1 TRADED bar (log_cnt > 0) in (A−24h, A]; W4H sensitivity only; module `common/tradability.py` (8ab0d769); `Artifact.load` requires the sha. The artifact on the king meta / dlw / panel axes is ETA 2–3 h from about 15:1xZ; fx-data will message the sha. Clock: my serve-clock members read rows through E, which closes at A, so (A−24h, A] matches; no change requested. **The funding-panel question is not answered yet.** |
| fx-train | 1632bb21: single TRN-06 prereg written by FX-MODEL; builders as new files; trainer/exporter changes; GPU schedule | No reply yet. |
| fx-prod | 2c4dc9dd: col-80 caliber (v0 or v1) for any retrain; col-81 unit; P9 effect on the fill | No reply yet. **Blocks every retrain.** |
| aud-prod | 1db22844: P10; fund-column fill at serve; clock | **Answered** (commit 428c179e). See the three findings below. |

aud-prod findings:
- **P10.** A float16 cast of served king features changes 0 deciles on 47/47 anchors (min Spearman 0.99996). Their reading: no P10 fix is justified. Receipt `receipts_prod/parity_king.json` 9dbba68b.
- **Fund columns at serve.** Names outside live_pins never reach a served V2MAIN row. Served fund_now matches training to 1e-3; served fund_ema is v1 vs v0 in training.
- **King clock on in-service booster, 32 anchors.** Spearman median 0.984, top-decile overlap median 0.90. A larger gap comes from the member universe: training rank sets over 829 names vs 450 served gives Spearman median 0.947, and the stored-vs-served total gives median 0.935 (min 0.760). V2MAIN stored-vs-served median is 0.982, mostly from the universe.
- **Implication for my design, not yet decided:** the as-of training universe vs the live list (U-PIT ∧ CRYPTO vs top-400 of 829) needs an explicit prereg choice.

## 5. Hazards noted

- Mac free disk fell from 37 to 24 GiB during this session (cause not attributed). A recursive grep of mine over `multi_asset/exports/research` may have triggered iCloud downloads before I stopped it (task byll9bpvz). I will not run recursive greps over the repo again; I will search only named files.
- pod2 cgroup memory was 49 GB used at 14:51Z while P2 S2 ran (6 × 6.5 GB). Builders that load the 5.7 GB cache must check the cgroup first.

## 6. Coordination answers received after the pause (15:3xZ; recorded only, nothing acted on)

### fx-prod

**Col 80: training stays v0 for king and V2MAIN.** Serving is being changed to match training, not the reverse. v0 = raw per-settlement rate, wall-clock HL 3d EMA, stale >12 h → 0.
- Decision record:
  - fx_prod clone commits 633d44b (P1) and 15921c0 (P2);
  - research e0e49f8e `FX_PROD/FACT_TABLE_PROD.md` §P1/§P2.
- Status: committed and tested, not deployed.
- For my retrains: col 80 = panel `f_fund_ema` (v0).

**Col 81:** raw per-settlement rate on both sides. T4 C81 gate: relative difference 0 on 10,786 cells.

**P9** changes interval labels only: f_fund_iv, and anything using rate·8/iv (f_fund_ema_v1, carry, FTRIM rn8). It does **not** change f_fund_now or v0 f_fund_ema.
- Therefore the v0 / now fill from v2ext is unaffected by P9.

### fx-data

**Mask:**
- tradable(E) ⇔ ≥ 1 traded bar (log_cnt > 0) with close in (E−24h, E], bar E included.
- Artifact: 4h grid of 10,285 anchors × 829, plus 5m bits; a flag only (no new cache, no NaN rewrite of ret5).
- Run 1 had a writer bug (rc=1, artifact invalid). Its checks passed: dual implementation 0/123,820 mismatches; T7 1h-count control 100% over 7.64M hours.
- Run 2 is pending resume. Path and sha will come by message.
- The label-bar rule "traded, not finite" fits the definition.

**Funding panels:** FND/HOL rebuilds are planned as new files.
- v1 450-name cells stay bitwise, except the FND-03 interval cells: 138 cells, 5 names, 2026-08 API rows.
- These interval cells matter for v1 only. They do not matter for the v0 / now columns that I fill.
- v2ext's August 2026 funding rows carry FND-02 spacing mislabels until the rebuild. This affects the interval / v1 only, per fx-prod's P9 scope. It does not affect the v0 / now fill.

### Remaining open questions

- fx-train: TRN-06 prereg ownership.
- fx-data: artifact sha.
