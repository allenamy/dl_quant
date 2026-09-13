> **创建:** 2026-09-13 15:3xZ | **Session:** FX-DATA (fix worker) | **状态:** PAUSED by team-lead (account usage limit); resume by lead message | **作废条件:** superseded by the next STATE note or REPORT_FX_DATA.md

# FX-DATA — state at pause

## Done (committed)
| What | Commit | sha256 (16) |
|---|---|---|
| SPEC_TRADABILITY_2026-09-13.md: trades-based tradability, frozen before any number. W24H primary, W4H sensitivity; A0 effect plan with D1 δ=0.05 | 73b59ec0 | 99ae35e0 |
| `multi_asset/exports/research/common/tradability.py` (shared module) + `FX_DATA/devices/fx_trd_build.py` (builder) | 8ab0d769 | module a9fad82c · builder run-1 ab02564f |
| FACT_TABLE_DATA.md §TRD (A1–A11 legacy rule sites, B1–B7 A0 recipe, C1–C5 data facts, D run-1 provisional readings); builder writer fix; run-1 log | this pause commit | — |

## Run 1 of the builder (pod2), rc=1: no receipt, artifact INVALID
- All pre-write checks passed in the log (`receipts/fx_trd_build_run1_rc1_writer_bug.log`):
  - axis and x0910-prefix parity;
  - no grid gaps;
  - every untraded bar is a frozen close;
  - 5m rolling flag == anchor state;
  - independent dual implementation: 0 of 123,820 mismatches;
  - **T7 1h count third-party control: 100% agreement over 7.64M hours, 0 disagreements**.
- Failure: the deterministic writer turned 0-d scalars into shape (1,), and the reload roundtrip caught it.
- pod2 `/workspace/fx_data_2026-09-13/out/trd/tradability_v1.npz` (b84f324d) is INVALID; `Artifact.load` refuses it. The writer is fixed in the pause commit, not re-run.
- No pod2 job of mine is running.

## Next steps, in order, on resume
1. Re-run `fx_trd_build.py` (the fixed version in the pause commit). The command is in `logs/fx_trd_build.log` of run 1: `env -i PATH HOME OMP=1 PYTHONPATH=/workspace/fx_data_2026-09-13/common nice 19 python -B devices/fx_trd_build.py out/trd t7_klines_1h PERP_KLINES_RECEIPT.json`. Sync the builder first, then fetch the receipt and the artifact sha, and fill FACT_TABLE §TRD-D.
2. Red tests: legacy rules A1–A8 extracted verbatim (AST, sha-pinned) run on a real-contract fixture (dead: FTT/RAY/SC/STRAX/DGB/SNT + 2026 deaths; neighbours: BTC, a thin live name, a resumed-halt name, a pre-listing name, and a lag case < 24 h). Legacy must be red for the stated reason; the module-based rules green.
3. Injection artifacts (umask_UPIT_CRYPTO ∧ tradable; f_fund_ema_v1 masked). Then the A0 arms C0 (GATE P bitwise vs A0_PWR230k) / TU / TB / TF / TF4 on the unmodified w10_sleeve b88e35a4, then the r18_judge estimator and the equivalence label (D1).
4. TRD-02: per-anchor `base_proxy ∧ ¬tradable` on the 10,039 A0 axis for P2 (requested by p2-oos-replay). TRD-04: T1 states recomputed with m ∩ tradable (positive control: reproduce stored states bitwise). TRD-05 counts for FX-MODEL.
5. HOL-01 + FND-01/02/03 panels, published side by side as staged artifacts (hf2 only / hf2 + P9 intervals).
   - Builders run as sandboxed copies: `pod_panel_ext.py` defaults its output to `/workspace/data/wide_panel_4h_v2ext.npz`, and `pod_panel_splice.py` writes fixed paths. Never run either one bare.
   - Positive control first: the rebuild on `_ext` must equal v2ext bitwise.
   - Then the holefix2 rebuild: parity on non-hole cells, with every non-bitwise cell explained (the float64 cumsum roundoff class is a candidate, not yet measured).
6. LIN-01: r6 builders into git (copies already pulled to the session scratchpad; not yet committed). The reproduction runs use the run_sandboxed pattern, because `r6_raw_patch_ext.py` and `r6_dev_tree.py` hard-code output and receipt paths inside `/workspace/uplift_2026-09-11/r6`.
7. RET-02 scan; UNI-03 September mask row (T1 `t1_states.py:78-81` carries the mask forward too); EVL-01: 33 HEAD files carry `os.environ.get("CAL", "simple")` (list at pause, `git grep` over HEAD). Then the D2/D3 closures, and the report.

## Coordination state
- **fx-prod (replied after the pause, received 15:4xZ):**
  - **New table.** A version with the August monthly zips folded in arrives after 18Z (roughly 2.5-3h). Same columns, iv_zip filled for 08-01..08-31, same directory under a new filename; sha to follow. ⇒ Build the FND panels on it, not on b797c85f.
  - **EXACT tiers:** `zip`, `structure_steady` (2 exchange anomalies: XAG/XAU 2026-01-30 16Z), `interest_signature`, `cap_signature_4h_to_1h`, `cap_signature_8h_to_1h`, `structure_last_1h_before_gap2`, `structure_last_1h_before_gap3`, and any '+' combination of these.
  - **LIKELY only (not truth):** the `iv_likely` column (`structure_gap3_into_longer` 40/41, `structure_gap2_into_longer` 52/62).
  - **Unresolved:** `unresolved_transition`, `unresolved_edge` (also marks each symbol's last row at the window end), `conflicting_rules:*`. My plan (keep incumbent value, flag, bound columns) is confirmed.
  - **Coverage:** pod2 ledger_full (zip ∪ fund_aug to 2026-09-01 02Z) ∪ frozen producer ledgers (live 450 + base, to 09-13 12Z) ∪ executor records, 687 symbols. It does **not** read r6_fund_sep. ⇒ For non-producer symbols, 09-01 02Z..09-10 settlement rows are absent from the table and will be counted as `not_in_P9` (flagged, not guessed).
- **fx-prod: August-zip P9 table delivered (2026-09-14; verified locally, bytes 2,008,476):**
  - **Pinned FND input:** `/Users/haosiyu/cc_tmp/fx_prod/work/p9/P9_declared_interval_table_2026-07-01_2026-09-13T12Z_zipszips_2026-08.csv.gz`, sha256 **366763a4aae854b2415fb461334efe95c1a74f93fc9e81c112c6138b16ec3197**. Receipts: `FX_PROD/receipts/p9/RECEIPT_P9_declared_interval_table_zips_2026-08.json` and `MANIFEST_zips_2026-08.json`. Same columns as b797c85f.
  - **Zip pull:** 680 zips at HTTP 200, 152 at 404; 0 source conflicts.
  - **Producer labels contradicted by the zip:** COTI 08-31 20Z (1→4) and ONG 08-25 08Z (2→4). ERA 08-06 16Z (4→1) is a seed row. DOS 08-11 16Z (8→4) is **not** a seed row; fx-prod corrected this in commit 3012a6af. It is DOS's first settlement, which the producer cold-started at M1 (09-04) with the first-row default label 8. That places it in the cold-start first-row family, with 07-26 08Z ×61 and ILV 09-04. The values and the table sha are unchanged. The other 533 D17 rows (ACE, BANK, DEXE, ERA, PROM; 08-01..08-14) are confirmed row by row.
  - **Caveat:** 16 August TradFi rows have calc_time 1 s past the hour; they are keyed to the nearest settlement hour (tolerance 60 s). T and SKR stay unresolved until the September zip exists.
  - **Still true:** the table does not read r6_fund_sep. ⇒ FND panels on resume use this table: 366763a4 replaces b797c85f.
- **p2-oos-replay (replied):**
  - Sites: `p2_driver.py:153-154, 293`; `p2_prep_inputs.py:99/103` (universe.npz 6322b573); `p2_s2_lib.py:99-106`.
  - Historical S2 keeps the proxy, with the deviation sized from my per-anchor `base_proxy ∧ ¬tradable` on the 10,039 axis (owed by me).
  - The certified replay will consume the module, with base = settled ∧ tradable.
- **fx-model (asked):**
  - (1) The mask. Answer: the artifact is on the 4h grid (10,285 anchors × 829) plus 5m bits, defined per the SPEC with the window (E−24h, E] inclusive of bar E. Flag only: no new cache and no NaN rewrite of ret5. The path and sha come after run 2.
  - (2) Funding panels. Answer: yes, FND/HOL rebuilds are planned as new files, and the v1 450-name cells stay bitwise unless an interval fix touches them (only 2026-08 API rows, which were 138 cells for 5 names in the v1 prefix, FND-03). No objection to its fill-from-v2ext plan in principle, but the v2ext August funding rows carry the FND-02 spacing mislabels until my rebuild lands.
  - fx-model follow-up (15:4xZ): the W24H flag (A−24h, A] lines up with its serve-clock member stats; no window change needed. Its funding-panel question crossed with my answer (msg 09b4dc82).
- **fx-train (replied, paused; its note is FX_TRAIN/STATE_PAUSE.md, commit 31305140):**
  - It has copied no r6 builder. LIN-01 is mine, and its TRN-01 month-roll stage will consume my git copies. ⇒ Send it the commit and per-file shas when they land.
  - The October template `v4_month_2026-10.env.template` still holds TODO_ values: CACHE / PANEL_SPLICE / PANEL_KING / HOLE_CELLS / BUNDLE_BASE / EXPORT_PANEL / EMA_STATE_JSON / LIVE_PINS / FUND_AUG / LEGS_PANEL. It will point them at roll outputs built from my rebuilt panels after review. It won't edit the template or the 46-key contract before then.
  - TRN-02: patched RAW targets will require a coverage manifest beside RAW_PATCH (its WIP). Relevant to RET-02 and to r6_raw_patch_ext.py reproduction.
