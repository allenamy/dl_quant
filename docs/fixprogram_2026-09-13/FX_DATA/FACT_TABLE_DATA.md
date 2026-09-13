> **创建:** 2026-09-13 15:4xZ | **Session:** FX-DATA (fix worker, teammate of team-lead) | **状态:** 事实表, append-only by section; each section is committed before the red tests and before the fix code of its item | **作废条件:** a cited file sha changes (each row carries its sha16)

# FACT_TABLE_DATA — FX-DATA items (AUDIT_DATA bb8a2806 → FIXPROGRAM §4.3)

Conventions:
- `sha16` is the first 16 hex characters of the sha256 of the git HEAD blob (research repo), or of the pod2 file for `pod2:` rows.
- "Receipt" means an AUDIT_DATA receipt row (`docs/audit_pipeline_2026-09-13/devices_data/receipts/…`) or one of this program's receipts under `FX_DATA/receipts/`.
- Order disclosure for TRD-01: the SPEC was frozen at 73b59ec0 and the shared module plus builder were committed at 8ab0d769, both before this table. The module is a new definition; no existing eligibility code has been changed. The red tests and every rule fix come after this section's commit.

## §TRD — dead contracts admitted by research eligibility rules (TRD-01..05)

### TRD-A. Where each rule admits a contract (legacy code, the object the red tests must hit)

| # | Rule | File:line (sha16) | Code | Why a dead contract passes |
|---|---|---|---|---|
| A1 | Replay member set, `MEMBERS_TOPN=829` | `uplift_2026-09-11/r18_foundation/devices/w10_sleeve_r18.py:77-81` (9b8a6323); pod2 runtime `w10_sleeve.py` (b88e35a4) same lines | `_q = nan_to_num(qvk[_i], nan=-1.0) … _ord[_q[_ord] > -0.5]` | On frozen rows qvk (7-day mean log1p quote volume) is a finite 0, and 0 > −0.5 |
| A2 | Universe mask applied to members (`UMASK_SCOPE=m1`) | same file `:163-165` (legs), `:222-224` (run) | `m = m[_mk[m]]` | The mask row is U-PIT ∧ CRYPTO (A5/A6), which keeps a name for up to 2 months after death |
| A3 | Fund-leg rank base `FZB` | same file `:149-150` | `return xz(FE[j, :])[m]`: rank among every finite `f_fund_ema_v1` on the panel row | Funding records continue after death (AUDIT H5: 60,438 events), so the EMA stays finite |
| A4 | Trade set `sel` | same file `:244-245` | `ok = isfinite(y4[i, m]); sel = ok & (qv4h >= 2.5e5)` | Frozen close ⇒ y4 finite at 0. qv4h decays over 7 days (AUDIT TRD-03: 58/33/220/290/134 dead pairs selected per year) |
| A5 | U-PIT monthly row | `retrain_2026-09/health_check_2026-09-05/build_umask.py:46` (746700fd) | `elig = has & (age >= 30) & (vol30 > 0)` | vol30 over the 30 days before the month start is > 0 for the month after death |
| A6 | CRYPTO class filter | `retrain_2026-09/universe_crypto_2026-09-08/scripts/build_crypto_mask.py:11` (43ebca0d) | `underlyingType in ("COIN","INDEX") if s in CLS else True` | Delisted names are absent from today's exchangeInfo ⇒ unknown ⇒ kept |
| A7 | P2 TRADING proxy | `parity_replay_2026-09-12/phase2/devices/p2_prep_inputs.py:94-99` (a9216641); consumed at `p2_driver.py:153-154, 293` (dc4e6c85) | `TR24[:, j] = hi > lo` (≥ 1 settlement in (A−24h, A]); `st.base = sorted(set(tr) \| set(live))` | Settlements continue after death (AUDIT H5 P2 base proxy: 1.4/6.5/15.8/17.6/4.4 dead per anchor) |
| A8 | Panel `elig` | `retrain_2026-09/pod_panel_ext.py:40` (db7f0474) | `elig = (covr >= 0.95) & (v7 >= 1e-4)` | Frozen ret5 = 0 is finite ⇒ covr = 1; v7 stays ≥ 1e-4 until the 7-day window is mostly zeros |
| A9 | King member screen | `retrain_2026-09/v4_chain_2026-09-09/pod_fea_ext_clamp.py:37` (b9f9c728) | `ok = (covr >= 0.95) & (v7 >= 1e-4) & isfinite(y4)` | Same as A8; owner FX-MODEL (TRD-05) |
| A10 | DL member screen | `retrain_2026-09/v4_chain_2026-09-09/pod_dlw_targets_raw.py:107` (d7c52823) | `ok = (covr >= 0.95) & (vstd >= 1e-4) & isfinite(y4s)` | Same as A8; owner FX-MODEL (TRD-05) |
| A11 | T1 state member set | `uplift_r2_2026-09-13/T1/devices/t1_states.py:77-82` (d1dd994f) | `m = where(nan_to_num(QVK) > -0.5)`; `m = m[umask[u][m]]`; the umask row is carried forward if missing (UNI-03) | A1 + A2 |

### TRD-B. The A0 reference recipe (what the effect measurement must reproduce)

| # | Fact | Source (sha16) |
|---|---|---|
| B1 | A0 device = pod2 `/workspace/uplift_2026-09-11/w10_sleeve.py` b88e35a4, run with cwd `r3k/dev` | `uplift_2026-09-11/r3k_impact/r3k_reprice3.py:13,41-48,55` (c069cf8a) |
| B2 | A0 env = `LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=…/masks/umask_UPIT_CRYPTO.npz SLOW_NPY=…/king_v4/SLOW_v3_on_v4axis.npy FSEED=s FPRED=f10_A0_s{s}.npy COSTB_JSON=r3k/costb_PWR_G230k.json OUT_TAG=A0_PWR230k_s{s}` | `r3k_reprice3.py:41-48,55` |
| B3 | Tree links: `pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz → /workspace/data/wide_panel_4h_v2ext.npz` (5e67c055); `wide_fea_hist_meta.npz → refute_C6_2/altrun/meta_newprod_v4.npz` (0e3c09ac); `dlw_2026-08-22 → /workspace/dlw_v4raw`; `f8_2026-08-22 → health_check/dev_v4/f8_2026-08-22` | pod2 `ls -la r3k/dev` (15:0xZ today) |
| B4 | Archived arms: `r3k/arms/A0_PWR230k_s42.npz` 352ac36f, `_s2027.npz` aa44e18f; keys cols/rec/W/config_json | pod2 |
| B5 | Mask `umask_UPIT_CRYPTO.npz` 47d87b51, axis = the v2ext panel ts (10,039 anchors, 2022-01-31 → 2026-08-31 00Z) | AUDIT_DATA §6 |
| B6 | Judge estimator: g = net_ex / gross_total; W_FULL n = 10038, W_ALPHA n = 9138 (skip 900), KING_LIVE (2024+) n = 5838; UTC-day block bootstrap 2000 `default_rng([20260905,k])`; A0 W_ALPHA mean g = 0.6341957 | `uplift_2026-09-11/r18_foundation/devices/r18_judge.py:32-52,63-72,83-96` |
| B7 | Names that leave `m` are **not** force-exited: `_nonsel` covers only `m[~sel]`. Their `sm` decays by EMA with the band; price, carry and cost are booked only on `m` | `w10_sleeve_r18.py:258-268, 320-331` |

### TRD-C. Data facts behind the definition

| # | Fact | Source |
|---|---|---|
| C1 | Cache channel 4 is `log_cnt = log1p(kline count).clip(0, 20)`, float16; bars are labelled by close time (`open_time + 5 min`) | `retrain_2026-09/pod_merge_cache_ext.py:24,32`; `caliber_program_2026-09-09/holefix2_daily.py:43,46` |
| C2 | holefix2 filled holes from official daily archives with the same channel math (pre-existing cells bitwise unchanged), so filled bars carry true counts | `holefix2_daily.py:36-58`; `holefix2_daily.log` (390910/390910 bitwise, 487,969 fills) |
| C3 | After death: 13,770,575 untraded rows with ret5 == 0, log_qv == 0, cpos/tbf NaN; 156 contracts; 129 still writing in the x0910 tail | AUDIT `AD_H_tradability.json` H1 |
| C4 | Third-party count source: T7 1h perp klines (`count` column), 362 symbols, receipt `PERP_KLINES_RECEIPT.json` (device 1b1a07a3), 72,468 zero-count hours | `/Users/haosiyu/cc_tmp/krw_pull/checks/PERP_KLINES_RECEIPT.json` |
| C5 | Production base = exchangeInfo TRADING perpetual USDT ∪ pinned live names | `~/wide_shadow/shadow_loop_v3.py:315-317` (e9c98374) via AUDIT TRD-02 |

### TRD-D. Built-artifact receipts (appended after `fx_trd_build.py` ran; see FX_DATA/receipts/RECEIPT_fx_trd_build.json)

**Run 1 (15:13–15:15Z, device ab02564f, module a9fad82c) ended rc=1 at its last step.** Log: `receipts/fx_trd_build_run1_rc1_writer_bug.log`.
- Cause: the deterministic npz writer passed 0-d scalars through `np.ascontiguousarray`, which returns shape (1,). The `Artifact.load` reload roundtrip then refused the file with a spec mismatch.
- The written `out/trd/tradability_v1.npz` (pod2, sha16 b84f324d) is **INVALID** and must not be consumed. The module itself refuses it.
- No receipt JSON was written. The writer is fixed in the same commit as this row. Run 2 is pending (paused by lead, 15:2xZ).
- The checks below were printed by run 1 **before** the write. They are PROVISIONAL until run 2 reproduces them into a receipt.

| # | Reading (run 1 log, provisional) |
|---|---|
| D1 | P: axes equal; x0910 prefix == holefix2 on log_cnt **and** ret5 (bitwise); spacing census {300 s: 493,632}, no gaps; min positive log_cnt 0.69336 (= float16 log1p(1)), max 13.99 |
| D2 | Cells: TRADED 153,569,514 · UNTRADED 15,881,719 · NODATA 239,770,524. TRADED with NaN ret5: 840 (first bars). UNTRADED with ret5 == 0 exactly: 15,881,718 of 15,881,719; the remaining 1 has NaN ret5; 0 non-zero ⇒ every untraded bar is a frozen close |
| D3 | 4h grid 10,285 anchors × 829. TRADABLE cells W24H 3,208,920 · W4H 3,208,062 |
| D4 | R: 5m rolling flag == anchor state at every on-grid anchor (W24H, W4H) |
| D5 | D: independent bisect implementation, 123,820 cells, 0 mismatches (both windows) |
| D6 | T7 third-party control: 362 symbols, 7,638,831 hours compared. Traded-in-hour agreement is **100%** (7,566,867 both traded + 71,964 both zero; 0 disagreements either way); 504 hours where the cache has no data but T7 has a row |
| D7 | Census 2022 (W24H): dead_after name-anchors 17,380; lag (TRADABLE ∧ dead) 84; UNTRADED ∧ dead 2,893; UNTRADED but trades again later 1,911. W4H lag 14. Other years are in the log line truncated at 600 chars; the full table goes into the run 2 receipt |
