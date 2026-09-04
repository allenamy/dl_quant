# Pod port of `w10_universe.py` — CAL=log vs CAL=simple replay (read-only, CPU)

> **创建:** 2026-09-04 | **Session:** 6737834a (teammate: pod port) | **状态:** 完成, 7 跑全部 DONE, 自检 (a)(b)(c) 通过(见 §3 的 2026 锚域说明) | **作废条件:** jpline 恢复后用原路径 `/mnt/storage/private/work_hsy/pod_backup_2026-08-21` 复跑并逐元素对账; 或 `/workspace/data/*v2ext*` / `shadow_bundle_v3/slow_pred_pinned.npy` 被替换。
> 只报数字, 不作解释, 不含部署建议。

## 1. Port layout (`/workspace/port_w10/`; everything new lives here, nothing outside was written)

| Path on pod | What |
|---|---|
| `w10_universe_orig.py` | byte-identical scp of the Mac device `multi_asset/exports/research/retrain_2026-09/w10_universe.py`; sha256 `43578158a90e7067fe10fcbb0a36cf4b2ca1acc8e6d7d0fd277be7f96fb2281b` (same on Mac and pod) |
| `w10_universe.py` | the run copy; sha256 `64c70a44ee88b79547a444ccb969c58d17d3a25f2f02af9cc77055b767bfe430`. **Only three path constants changed** (the device hard-codes absolute jpline paths; it is *not* working-directory relative). Full `diff orig patched` below. |

```
26c26
< B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; PD = "/mnt/storage/private/work_hsy/probe_artifacts"
---
> B = "pod_backup_2026-08-21"; PD = "probe_artifacts"
93c93
<     _R2 = "/mnt/storage/private/work_hsy"
---
>     _R2 = "."
```

(`/mnt/storage` does not exist on the pod; creating it would have written outside `/workspace/port_w10/`, so the constants were patched instead. No other line differs; the docstring still mentions the jpline path, which is text only.)

Symlinks (names exactly as the device expects → pod source, all read-only):

| Device-expected file | → pod file (sha256) |
|---|---|
| `pod_backup_2026-08-21/wide_fea_hist_meta.npz` | `/workspace/data/wide_fea_v2ext_meta.npz` (`4b1b6047107d25573244a84df69d45bc987ada89b6731e826c867a230e247082`) — keys E_ts/members/y4/qvk/names; E_ts 10176 anchors 2022-01-08 00:00 → 2026-08-30 20:00; y4 (10176, 829) float32 |
| `pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz` | `/workspace/data/wide_panel_4h_v2ext.npz` (`5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116`) — ts 10039 rows 2022-01-31 00:00 → 2026-08-31 00:00; 829 symbols; has `f_fund_ema_v1` (device takes the `UMASK_ROW=None` branch), `f_fund_now`, `f_fund_iv`, `f_rev_24h` |
| `pod_backup_2026-08-21/slow_pred_hist_oos.npy` | `/workspace/shadow_bundle_v3/slow_pred_pinned.npy` (`158cd4ac8f8f30f7f41a5a6cba0bd19a450ce756727e4aeae3d4e4b0b67d0054`, matches `shadow_bundle_v3/MANIFEST.json`) — (10176, 829) float32 |
| `pod_backup_2026-08-21/nets_histv2_0_0_0.npy`, `nets_histv2_-30_2_42.npy` | **dummy** `np.zeros((1,2))` files (no such receipts exist on the pod). With `LEGS=101` the device only prints `NOTE <arm>: arm anchors 10038 vs ref 1 …` and sets `maxabs_diff_vs_pod_backup = NaN`; the hard `assert ref.shape[0]==R.shape[0]` is gated on `LEGS=="111"` (device line 325) and was not reached. No other assertion touches these files. |
| `f8_2026-08-22/preds/f10_V2MAIN_s42.npy` | `/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy` (`baf747ceb31f10d614ffac79b9c969c499e1c3e9f82edfec246d7cfb0f353ace`) — (10086, 829) float32, mtime Sep 1 07:30 |
| `f8_2026-08-22/preds/f10_V2MAIN_s2027.npy` | `/workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy` (`c742ffaa1f4397aee55a31a5486aabfd89ae28624123bbda535a7d41851b2a0b`) — (10086, 829) float32 |
| `dlw_2026-08-22/data/dlw_targets.npz` | `/workspace/data/dlw_targets.npz` (`dd4ed2dfb5fa426f8b8f49c0a20f39bcf077280025ed03ebb19b2ece66fc68a3`) — E_ts 10086 anchors 2022-01-03 00:00 → 2026-08-10 20:00; symbols == panel symbols (order-identical). `/workspace/dlw_2026-08-22/data` on the pod is itself a symlink to `/workspace/data`, so this is the same file the device would find under the original `_R2` layout. |
| `probe_artifacts/` | outputs |

**King source and `SLOW_NPY`.** `SLOW_NPY` does *not* replace the canonical load: the device still opens `{B}/slow_pred_hist_oos.npy` (mmap) as the shape reference (device line 88), so the symlink above is required in any case. `SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy` was additionally set on every run so that `config_json` self-reports the king source (E-0826-C); both paths resolve to the same file, the shape assertion is trivially satisfied, and the numbers are unaffected. Log line on every run: `SLOW override: /workspace/shadow_bundle_v3/slow_pred_pinned.npy finite 0.241`. The lead's run list said run 1 has "no other switches"; `SLOW_NPY` is the only extra env var and it is an input pointer, not a behaviour switch.

## 2. Input coverage facts that shape the numbers (data facts, not interpretation)

- **meta ↔ panel column alignment verified**: meta `names` has length 82 (feature names, not symbols), so alignment was checked by comparing meta `y4` with panel `Y4` at the 10038 common timestamps: 3,427,554 both-finite cells, max abs diff 0.000e+00, finite pattern identical. Columns are the same 829 symbols in the same order.
- **138 meta anchors (2022-01-08 → 2022-01-30) have no panel row** and are skipped by the device; every run therefore has 10038 anchors, 2022-01-31 00:00 → 2026-08-30 20:00 (S0 and d30_n2_c42 alike).
- **King predictions are entirely NaN before 2024**: finite fraction of `slow_pred_pinned.npy` by anchor year = 2022 0.0000, 2023 0.0000, 2024 0.3304, 2025 0.4681, 2026 0.4825 (2024–2026 = all members). In the device this makes the king leg return identically 0 for 2022–2023 and gives king a zero msharpe seat until real king returns enter the 900-anchor lookback during 2024. (The brief described 2022–2023 as in-sample; on this file they are absent. Either way they are excluded below.)
- **F10 alignment source ends 2026-08-10 20:00** (dlw_targets E_ts) while the meta runs to 2026-08-30 20:00. `F10 OOS preds aligned: rows 10056/10176, cols 829/829, finite 0.2838` on every run. For the last 120 anchors of 2026 (08-11 → 08-30) `F10P` is NaN → `xz` → 0, so on those anchors the F10 sub-book carries no DL leg (only the fund leg under LEGS=101) and `KMOD_F10` has no effect. A supplementary row `2026<=08-10` (1332 anchors) is therefore given in every table.
- F10 finite fraction by dlw year: 2022 0.0000, 2023 0.2260, 2024 0.3304, 2025 0.4681, 2026 0.4825 (identical for s42 and s2027).
- Device behaviour retained as-is (identical on jpline): for the first 900 processed anchors (`p < LOOK`, all in 2022) `w3_at` returns `[1/3,1/3,1/3]` without applying the `LEGS` mask; `COST_B`, EMA 0.1, band 2.5e-4, cap 2.5/nsel, `sel.sum()<80` skip, all unchanged.

## 3. Self-checks

### (a) Leg-level equality (`/workspace/port_w10/selfcheck_legs.py`, log `logs/selfcheck_legs.log`)

Device leg definition replicated verbatim from `legs()` with CAL=log (raw y4): `xz` rank → 0 where y4 not finite → demean over finite-y → unit gross → `Σ z/g·y4 × 1e4`; meta `members`; all meta anchors that have a panel row (10038). Means by anchor year, bps/anchor:

| leg | 2024 | 2025 | 2026 (all 1452 anchors, to 08-30) | 2026 ≤ 2026-08-10 20:00 (1332 anchors) |
|---|---|---|---|---|
| king (pinned) | **+1.5326** (exp +1.53 OK) | **+2.3813** (exp +2.38 OK) | +3.1298 (exp +3.20, Δ −0.07) | **+3.1975** OK |
| fund (f_fund_ema_v1) | **−0.3608** (exp −0.36 OK) | **+1.7118** (exp +1.71 OK) | +5.5200 (exp +6.34, Δ −0.82) | **+6.3436** OK |
| rev24 (−f_rev_24h, reference only) | +0.2959 | +0.3356 | +1.7111 | +1.9542 |

2024 and 2025 match the expected values to within 0.003. For 2026 the full-range means differ, and the difference is entirely the anchor range: a prefix scan over 2026 finds the best match to (+3.20, +6.34) at exactly n=1332 anchors, last anchor 2026-08-10 20:00 (|err| sum 0.006), the last anchor of the dlw_targets range. Monthly means (king / fund / rev24; n): 2026-01 +4.235/+2.640/+0.344 (186); 02 +3.996/+5.913/+4.964 (168); 03 +3.493/+4.627/+3.302 (186); 04 +4.148/+10.292/−0.103 (180); 05 +2.773/+5.194/+1.257 (186); 06 −0.479/+10.049/−2.996 (180); 07 +4.042/+5.864/+5.283 (186); 08 (to 08-30) +2.821/−0.268/+1.743 (180). Input mapping verified; the reference numbers were computed on a 2026 range ending 2026-08-10.

### (b) F10 alignment and config_json

Every run's log contains `F10 leg source: f10_V2MAIN_s42.npy` (or `_s2027`) and `F10 OOS preds aligned: rows 10056/10176, cols 829/829, finite 0.2838`. The `config_json` stored in each npz is reproduced verbatim in §6; MEMBERS_TOPN / TRADE_TOPN / FTRIM / KMOD_F10 / FSEED / LEGS / LOOK / WRULE match the intended switches for every run. Live-form runs also log `MEMBERS_TOPN=829: members rebuilt from qvk ranking`.

### (c) CAL

`"CAL": "log"` in the five CAL=log npz files and `"CAL": "simple"` in the two CAL=simple npz files, exactly as set (see §6).

## 4. Exact commands (`/workspace/port_w10/logs/commands.txt`; launched by `run_all.sh`, all seven in parallel, cwd `/workspace/port_w10`, `OMP_NUM_THREADS=4`; wall time 60–95 s each; all finished 2026-09-04T12:24:43Z)

```
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy CAL=log FSEED=42 OUT_TAG=pod_canon_callog_s42 /workspace/venv/bin/python w10_universe.py
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy CAL=simple FSEED=42 OUT_TAG=pod_canon_calsimple_s42 /workspace/venv/bin/python w10_universe.py
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy CAL=log FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=pod_live_callog_s42 /workspace/venv/bin/python w10_universe.py
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy CAL=simple FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=pod_live_calsimple_s42 /workspace/venv/bin/python w10_universe.py
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy CAL=log FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero KMOD_F10=0.5 OUT_TAG=pod_live_t3c_callog_s42 /workspace/venv/bin/python w10_universe.py
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy CAL=log FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero KMOD_F10=0.5 OUT_TAG=pod_live_t3c_callog_s2027 /workspace/venv/bin/python w10_universe.py
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy CAL=log FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=pod_live_callog_s2027 /workspace/venv/bin/python w10_universe.py
```

Self-check: `cd /workspace/port_w10 && /workspace/venv/bin/python selfcheck_legs.py`. Tables: `/workspace/venv/bin/python summarize.py` (writes `probe_artifacts/pod_port_tables.md` and `probe_artifacts/pod_port_peryear_stats.json`).

## 5. `RECEIPT_EX` lines verbatim (both arms per run; `grep -H RECEIPT_EX logs/pod_*.log`)

Device receipt fields: `by_year_ex` / `net_ex_2024on` group by anchor year over all 10038 anchors (2026 = through 08-30); `turnover_ex_mean` in the device is `mean(|cost_ex|)` (device line 349), not the turnover column.

```
logs/pod_canon_callog_s42.log:RECEIPT_EX S0 {"net_ex_all": 0.3261, "net_ex_2024on": 0.7409, "sharpe_ex_2024on": 1.778, "by_year_ex": {"2022": -0.12, "2023": -0.37, "2024": 0.178, "2025": 0.468, "2026": 2.003}, "carry_ex_mean": 0.8182, "cost_ex_mean": 0.0665, "turnover_ex_mean": 0.06652, "netlong_mean": -0.0175, "netlong_by_year": {"2022": -0.0206, "2023": -0.0365, "2024": -0.0279, "2025": 0.0043, "2026": -0.0019}}
logs/pod_canon_callog_s42.log:RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.329, "net_ex_2024on": 0.7304, "sharpe_ex_2024on": 1.908, "by_year_ex": {"2022": -0.149, "2023": -0.302, "2024": 0.255, "2025": 0.436, "2026": 1.893}, "carry_ex_mean": 0.7217, "cost_ex_mean": 0.0665, "turnover_ex_mean": 0.06654, "netlong_mean": -0.0199, "netlong_by_year": {"2022": -0.0274, "2023": -0.0293, "2024": -0.0277, "2025": 0.0008, "2026": -0.0151}}
logs/pod_canon_calsimple_s42.log:RECEIPT_EX S0 {"net_ex_all": 0.4782, "net_ex_2024on": 1.1457, "sharpe_ex_2024on": 2.786, "by_year_ex": {"2022": -0.495, "2023": -0.408, "2024": 0.322, "2025": 0.776, "2026": 2.949}, "carry_ex_mean": 0.7518, "cost_ex_mean": 0.054, "turnover_ex_mean": 0.05403, "netlong_mean": -0.0295, "netlong_by_year": {"2022": -0.0206, "2023": -0.0379, "2024": -0.0263, "2025": -0.039, "2026": -0.0193}}
logs/pod_canon_calsimple_s42.log:RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.5422, "net_ex_2024on": 1.2163, "sharpe_ex_2024on": 3.179, "by_year_ex": {"2022": -0.499, "2023": -0.299, "2024": 0.322, "2025": 0.843, "2026": 3.132}, "carry_ex_mean": 0.6523, "cost_ex_mean": 0.0542, "turnover_ex_mean": 0.0542, "netlong_mean": -0.0255, "netlong_by_year": {"2022": -0.0207, "2023": -0.0257, "2024": -0.0172, "2025": -0.0344, "2026": -0.0308}}
logs/pod_live_callog_s2027.log:RECEIPT_EX S0 {"net_ex_all": 0.4539, "net_ex_2024on": 0.7853, "sharpe_ex_2024on": 1.983, "by_year_ex": {"2022": 0.348, "2023": -0.332, "2024": 0.219, "2025": 0.488, "2026": 2.09}, "carry_ex_mean": 0.4466, "cost_ex_mean": 0.0698, "turnover_ex_mean": 0.06979, "netlong_mean": -0.0247, "netlong_by_year": {"2022": -0.0129, "2023": -0.0244, "2024": -0.0042, "2025": -0.0397, "2026": -0.0497}}
logs/pod_live_callog_s2027.log:RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.4202, "net_ex_2024on": 0.7416, "sharpe_ex_2024on": 2.005, "by_year_ex": {"2022": 0.313, "2023": -0.338, "2024": 0.217, "2025": 0.438, "2026": 1.994}, "carry_ex_mean": 0.4117, "cost_ex_mean": 0.0697, "turnover_ex_mean": 0.06971, "netlong_mean": -0.0277, "netlong_by_year": {"2022": -0.0223, "2023": -0.0185, "2024": -0.0043, "2025": -0.0455, "2026": -0.0574}}
logs/pod_live_callog_s42.log:RECEIPT_EX S0 {"net_ex_all": 0.4177, "net_ex_2024on": 0.7341, "sharpe_ex_2024on": 1.869, "by_year_ex": {"2022": 0.348, "2023": -0.362, "2024": 0.149, "2025": 0.41, "2026": 2.108}, "carry_ex_mean": 0.4414, "cost_ex_mean": 0.0713, "turnover_ex_mean": 0.07134, "netlong_mean": -0.024, "netlong_by_year": {"2022": -0.0129, "2023": -0.0239, "2024": -0.0037, "2025": -0.0358, "2026": -0.0522}}
logs/pod_live_callog_s42.log:RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.3833, "net_ex_2024on": 0.6914, "sharpe_ex_2024on": 1.884, "by_year_ex": {"2022": 0.313, "2023": -0.373, "2024": 0.149, "2025": 0.359, "2026": 2.013}, "carry_ex_mean": 0.4082, "cost_ex_mean": 0.0713, "turnover_ex_mean": 0.07127, "netlong_mean": -0.0267, "netlong_by_year": {"2022": -0.0223, "2023": -0.0182, "2024": -0.0028, "2025": -0.0407, "2026": -0.0605}}
logs/pod_live_calsimple_s42.log:RECEIPT_EX S0 {"net_ex_all": 0.8499, "net_ex_2024on": 1.5866, "sharpe_ex_2024on": 3.777, "by_year_ex": {"2022": -0.018, "2023": -0.317, "2024": 0.295, "2025": 1.216, "2026": 4.098}, "carry_ex_mean": 0.4409, "cost_ex_mean": 0.0599, "turnover_ex_mean": 0.05995, "netlong_mean": -0.0293, "netlong_by_year": {"2022": -0.0129, "2023": -0.0217, "2024": -0.0055, "2025": -0.0579, "2026": -0.0566}}
logs/pod_live_calsimple_s42.log:RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.8448, "net_ex_2024on": 1.5975, "sharpe_ex_2024on": 3.998, "by_year_ex": {"2022": -0.1, "2023": -0.295, "2024": 0.22, "2025": 1.223, "2026": 4.247}, "carry_ex_mean": 0.404, "cost_ex_mean": 0.06, "turnover_ex_mean": 0.06, "netlong_mean": -0.03, "netlong_by_year": {"2022": -0.0162, "2023": -0.0137, "2024": -0.0025, "2025": -0.0614, "2026": -0.0679}}
logs/pod_live_t3c_callog_s2027.log:RECEIPT_EX S0 {"net_ex_all": 0.4316, "net_ex_2024on": 0.7524, "sharpe_ex_2024on": 1.916, "by_year_ex": {"2022": 0.348, "2023": -0.347, "2024": 0.169, "2025": 0.479, "2026": 2.046}, "carry_ex_mean": 0.4619, "cost_ex_mean": 0.0723, "turnover_ex_mean": 0.07227, "netlong_mean": -0.0031, "netlong_by_year": {"2022": -0.0129, "2023": -0.0179, "2024": 0.0186, "2025": 0.0107, "2026": -0.021}}
logs/pod_live_t3c_callog_s2027.log:RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.4046, "net_ex_2024on": 0.72, "sharpe_ex_2024on": 1.959, "by_year_ex": {"2022": 0.313, "2023": -0.352, "2024": 0.178, "2025": 0.411, "2026": 2.006}, "carry_ex_mean": 0.4244, "cost_ex_mean": 0.0721, "turnover_ex_mean": 0.07208, "netlong_mean": -0.0055, "netlong_by_year": {"2022": -0.0223, "2023": -0.0119, "2024": 0.0186, "2025": 0.0061, "2026": -0.0268}}
logs/pod_live_t3c_callog_s42.log:RECEIPT_EX S0 {"net_ex_all": 0.4017, "net_ex_2024on": 0.7005, "sharpe_ex_2024on": 1.793, "by_year_ex": {"2022": 0.348, "2023": -0.346, "2024": 0.104, "2025": 0.379, "2026": 2.086}, "carry_ex_mean": 0.4564, "cost_ex_mean": 0.0737, "turnover_ex_mean": 0.07369, "netlong_mean": -0.0032, "netlong_by_year": {"2022": -0.0129, "2023": -0.017, "2024": 0.0183, "2025": 0.0116, "2026": -0.024}}
logs/pod_live_t3c_callog_s42.log:RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.3669, "net_ex_2024on": 0.6586, "sharpe_ex_2024on": 1.802, "by_year_ex": {"2022": 0.313, "2023": -0.361, "2024": 0.109, "2025": 0.328, "2026": 1.989}, "carry_ex_mean": 0.4212, "cost_ex_mean": 0.0735, "turnover_ex_mean": 0.07353, "netlong_mean": -0.0057, "netlong_by_year": {"2022": -0.0223, "2023": -0.011, "2024": 0.0185, "2025": 0.0074, "2026": -0.0311}}
```

## 6. Per-year tables (arm d30_n2_c42, column net_ex; years 2024/2025/2026 only)

### Canon form (MEMBERS_TOPN=0, TRADE_TOPN=0, FTRIM=off), FSEED=42: CAL=log vs CAL=simple

| year | log mean | simple mean | log Sharpe | simple Sharpe | log worst mo | simple worst mo | log maxDD | simple maxDD | log w3_king | simple w3_king | log turnover | simple turnover | n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.255 | +0.322 | 0.86 | 1.06 | -380 (2024-04) | -372 (2024-07) | 719 | 694 | 0.629 | 0.420 | 0.0367 | 0.0271 | 2196 |
| 2025 | +0.436 | +0.843 | 1.25 | 2.41 | -367 (2025-12) | -404 (2025-04) | 503 | 671 | 0.692 | 0.460 | 0.0329 | 0.0234 | 2190 |
| 2026 | +1.893 | +3.132 | 3.64 | 6.10 | -280 (2026-08) | +10 (2026-08) | 727 | 682 | 0.368 | 0.053 | 0.0188 | 0.0099 | 1452 |
| 2026<=08-10 | +2.373 | +3.629 | 4.61 | 7.14 | +34 (2026-02) | +161 (2026-01) | 395 | 258 | 0.374 | 0.058 | 0.0190 | 0.0097 | 1332 |
| 2024on | +0.730 | +1.216 | 1.91 | 3.18 | -380 (2024-04) | -404 (2025-04) | 727 | 694 | 0.588 | 0.344 | 0.0308 | 0.0214 | 5838 |

### Live form (MEMBERS_TOPN=829, TRADE_TOPN=400, FTRIM=zero), FSEED=42: CAL=log vs CAL=simple

| year | log mean | simple mean | log Sharpe | simple Sharpe | log worst mo | simple worst mo | log maxDD | simple maxDD | log w3_king | simple w3_king | log turnover | simple turnover | n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.149 | +0.220 | 0.53 | 0.75 | -363 (2024-04) | -343 (2024-07) | 795 | 586 | 0.639 | 0.436 | 0.0375 | 0.0282 | 2196 |
| 2025 | +0.359 | +1.223 | 1.15 | 3.37 | -294 (2025-12) | -370 (2025-04) | 418 | 647 | 0.673 | 0.475 | 0.0357 | 0.0268 | 2190 |
| 2026 | +2.013 | +4.247 | 3.84 | 7.63 | -294 (2026-08) | +85 (2026-08) | 771 | 689 | 0.361 | 0.052 | 0.0236 | 0.0138 | 1452 |
| 2026<=08-10 | +2.512 | +4.823 | 4.83 | 8.70 | +104 (2026-02) | +343 (2026-08) | 452 | 252 | 0.368 | 0.057 | 0.0238 | 0.0136 | 1332 |
| 2024on | +0.691 | +1.597 | 1.88 | 4.00 | -363 (2024-04) | -370 (2025-04) | 795 | 689 | 0.583 | 0.355 | 0.0334 | 0.0241 | 5838 |

### T3c (KMOD_F10=0.5) vs base, live form, CAL=log, FSEED=42

| year | base mean | arm mean | Δ mean | base Sharpe | arm Sharpe | Δ Sharpe | base w3_king | arm w3_king | base turnover | arm turnover | base maxDD | arm maxDD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.149 | +0.109 | -0.040 | 0.53 | 0.38 | -0.15 | 0.639 | 0.639 | 0.0375 | 0.0383 | 795 | 881 |
| 2025 | +0.359 | +0.328 | -0.031 | 1.15 | 1.05 | -0.10 | 0.673 | 0.673 | 0.0357 | 0.0357 | 418 | 457 |
| 2026 | +2.013 | +1.989 | -0.024 | 3.84 | 3.86 | +0.02 | 0.361 | 0.361 | 0.0236 | 0.0240 | 771 | 779 |
| 2026<=08-10 | +2.512 | +2.505 | -0.007 | 4.83 | 4.93 | +0.10 | 0.368 | 0.368 | 0.0238 | 0.0243 | 452 | 454 |
| 2024on | +0.691 | +0.659 | -0.033 | 1.88 | 1.80 | -0.08 | 0.583 | 0.583 | 0.0334 | 0.0337 | 795 | 881 |

### T3c (KMOD_F10=0.5) vs base, live form, CAL=log, FSEED=2027

| year | base mean | arm mean | Δ mean | base Sharpe | arm Sharpe | Δ Sharpe | base w3_king | arm w3_king | base turnover | arm turnover | base maxDD | arm maxDD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.217 | +0.178 | -0.039 | 0.78 | 0.63 | -0.15 | 0.639 | 0.639 | 0.0369 | 0.0375 | 740 | 816 |
| 2025 | +0.438 | +0.411 | -0.027 | 1.36 | 1.28 | -0.07 | 0.673 | 0.673 | 0.0336 | 0.0335 | 430 | 476 |
| 2026 | +1.994 | +2.006 | +0.013 | 3.80 | 3.88 | +0.08 | 0.361 | 0.361 | 0.0247 | 0.0252 | 757 | 763 |
| 2026<=08-10 | +2.486 | +2.519 | +0.033 | 4.78 | 4.94 | +0.15 | 0.368 | 0.368 | 0.0250 | 0.0255 | 460 | 479 |
| 2024on | +0.742 | +0.720 | -0.022 | 2.01 | 1.96 | -0.05 | 0.583 | 0.583 | 0.0326 | 0.0329 | 757 | 816 |

### Additional per-year means (all runs; d30_n2_c42; executor caliber columns)

| run | year | pnl_ex | carry_ex | cost_ex | net_ex | netlong | nsel | gross_total | fires | w3_fund |
|---|---|---|---|---|---|---|---|---|---|---|
| pod_canon_callog_s42 | 2024 | +0.574 | +0.238 | 0.081 | +0.255 | -0.0277 | 270 | 0.621 | 362 | 0.371 |
| pod_canon_callog_s42 | 2025 | +1.339 | +0.808 | 0.094 | +0.436 | +0.0008 | 372 | 0.593 | 679 | 0.308 |
| pod_canon_callog_s42 | 2026 | +3.976 | +2.008 | 0.075 | +1.893 | -0.0151 | 318 | 0.865 | 713 | 0.632 |
| pod_canon_calsimple_s42 | 2024 | +0.649 | +0.265 | 0.062 | +0.322 | -0.0172 | 270 | 0.648 | 441 | 0.580 |
| pod_canon_calsimple_s42 | 2025 | +1.646 | +0.736 | 0.067 | +0.843 | -0.0344 | 372 | 0.606 | 735 | 0.540 |
| pod_canon_calsimple_s42 | 2026 | +4.784 | +1.609 | 0.044 | +3.132 | -0.0308 | 318 | 0.740 | 729 | 0.947 |
| pod_live_callog_s42 | 2024 | +0.398 | +0.167 | 0.083 | +0.149 | -0.0028 | 272 | 0.602 | 358 | 0.361 |
| pod_live_callog_s42 | 2025 | +0.910 | +0.447 | 0.104 | +0.359 | -0.0407 | 375 | 0.531 | 584 | 0.327 |
| pod_live_callog_s42 | 2026 | +3.020 | +0.916 | 0.090 | +2.013 | -0.0605 | 324 | 0.779 | 453 | 0.639 |
| pod_live_calsimple_s42 | 2024 | +0.479 | +0.195 | 0.065 | +0.220 | -0.0025 | 272 | 0.636 | 444 | 0.564 |
| pod_live_calsimple_s42 | 2025 | +1.750 | +0.450 | 0.078 | +1.223 | -0.0614 | 375 | 0.549 | 661 | 0.525 |
| pod_live_calsimple_s42 | 2026 | +5.146 | +0.842 | 0.057 | +4.247 | -0.0679 | 324 | 0.689 | 467 | 0.948 |
| pod_live_t3c_callog_s42 | 2024 | +0.367 | +0.171 | 0.087 | +0.109 | +0.0185 | 272 | 0.614 | 365 | 0.361 |
| pod_live_t3c_callog_s42 | 2025 | +0.895 | +0.463 | 0.104 | +0.328 | +0.0074 | 375 | 0.542 | 593 | 0.327 |
| pod_live_t3c_callog_s42 | 2026 | +3.024 | +0.944 | 0.091 | +1.989 | -0.0311 | 324 | 0.781 | 459 | 0.639 |
| pod_live_t3c_callog_s2027 | 2024 | +0.433 | +0.171 | 0.084 | +0.178 | +0.0186 | 272 | 0.612 | 371 | 0.361 |
| pod_live_t3c_callog_s2027 | 2025 | +0.987 | +0.477 | 0.099 | +0.411 | +0.0061 | 375 | 0.556 | 641 | 0.327 |
| pod_live_t3c_callog_s2027 | 2026 | +3.050 | +0.949 | 0.095 | +2.006 | -0.0268 | 324 | 0.786 | 462 | 0.639 |
| pod_live_callog_s2027 | 2024 | +0.465 | +0.167 | 0.081 | +0.217 | -0.0043 | 272 | 0.602 | 374 | 0.361 |
| pod_live_callog_s2027 | 2025 | +0.994 | +0.460 | 0.097 | +0.438 | -0.0455 | 375 | 0.549 | 610 | 0.327 |
| pod_live_callog_s2027 | 2026 | +3.007 | +0.920 | 0.094 | +1.994 | -0.0574 | 324 | 0.782 | 459 | 0.639 |

### config_json as stored in each npz

- `pod_canon_callog_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 0, "TRADE_TOPN": 0, "FTRIM": "off", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_canon_calsimple_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 0, "TRADE_TOPN": 0, "FTRIM": "off", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "simple", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_live_callog_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_live_calsimple_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "simple", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_live_t3c_callog_s42`: `{"KMOD_F10": 0.5, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_live_t3c_callog_s2027`: `{"KMOD_F10": 0.5, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "2027", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_live_callog_s2027`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "2027", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`

### Series coverage

- `pod_canon_callog_s42`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]
- `pod_canon_calsimple_s42`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]
- `pod_live_callog_s42`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]
- `pod_live_calsimple_s42`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]
- `pod_live_t3c_callog_s42`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]
- `pod_live_t3c_callog_s2027`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]
- `pod_live_callog_s2027`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]

## 7. Definitions used in §6 (script `summarize.py`)

Arm `d30_n2_c42` (stop layer), column `net_ex` = executor-caliber net (bps of gross per anchor), grouped by anchor year (UTC). `mean` = mean net_ex; `Sharpe` = mean / std(ddof=1) × √2190; `worst mo` = minimum over calendar months of the monthly sum of net_ex (month shown); `maxDD` = maximum drawdown of the within-year cumulative sum of net_ex (bps of gross); `w3_king`, `turnover` = means of those columns (turnover = Σ|trade| of the blended book vs the previous blended book). `2024on` = all anchors from 2024-01-01. 2022 and 2023 are excluded everywhere (king predictions absent). `2026<=08-10` = 2026 anchors through 2026-08-10 20:00, the last anchor with F10 coverage.

## 8. Files

Pod (`/workspace/port_w10/`): `REPORT.md` (this file), `w10_universe_orig.py`, `w10_universe.py`, `run_all.sh`, `selfcheck_legs.py`, `summarize.py`, `logs/` (`commands.txt`, `selfcheck_legs.log`, `pod_<tag>.log` ×7, `summarize.out`), `probe_artifacts/` (`w10_ablation_series_<tag>.npz` ×7 with keys cols/symbols/config_json/S0_rec/S0_W/d30_n2_c42_rec/d30_n2_c42_W, `w10_ablation_summary_<tag>.json` ×7, `pod_port_tables.md`, `pod_port_peryear_stats.json`, `pod_port_receipts_ex.txt`).

sha256 of the seven series npz:

```
e80c957d949e3247df9d87da360e0f2794559fb60aaeb1a6d5195fc6efe242d9  w10_ablation_series_pod_canon_callog_s42.npz
5d601e1adeb195aba4776b6132a94128abf8573816eac58e0b4019e0acc77eec  w10_ablation_series_pod_canon_calsimple_s42.npz
634ea0dcd7c3ac7a2b1b7a063859fed1896b08a97c27b2a5d57fa06c03af5611  w10_ablation_series_pod_live_callog_s2027.npz
dd85ded80c7af05855780ef237e5fc128492450bda034522fd8726f2f9ea7083  w10_ablation_series_pod_live_callog_s42.npz
e0917815955a5f3b4d2d931a2beb5320b377cbecb58a0228d46f369ab2ce304a  w10_ablation_series_pod_live_calsimple_s42.npz
d69cd5e0e72a6a3d70257fcb80ef2f0631dd424163b6b8b924e5ae8d4639974f  w10_ablation_series_pod_live_t3c_callog_s2027.npz
3e30af6aa1faedf0dd103a506ccf68e5b2dbbae2a839eb58e7c1b905027cea2f  w10_ablation_series_pod_live_t3c_callog_s42.npz
```

Mac scratchpad copies (`/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/`): `pod_port_REPORT.md`, the seven `w10_ablation_summary_<tag>.json`, `pod_port_tables.md`, `pod_port_peryear_stats.json`, `pod_port_receipts_ex.txt`, `selfcheck_legs.log`, `commands.txt`, and the scripts `selfcheck_legs.py`, `summarize.py`, `run_all.sh`.

Nothing under `/workspace/shadow_bundle_v3/`, `/workspace/data/`, `/workspace/f8_*` was modified (reads only; all symlinks live under `/workspace/port_w10/`). No GPU job was started.
