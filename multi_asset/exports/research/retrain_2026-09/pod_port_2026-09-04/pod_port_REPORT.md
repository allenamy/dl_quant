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

## 9. Follow-up runs (2026-09-04, second batch): fixed live seats (W3FIX), isolated component arms, decomposition columns

> **状态:** 6 跟进跑全部 DONE(2026-09-04T12:36:22Z, 85–104 s each, 6 in parallel); 无断言触发; 只报数字。作废条件同首行。

### 9.0 Setup, commands, code-path facts

Same setup as §1–§4 (cwd `/workspace/port_w10`, patched-path device, symlinked v2ext inputs, `SLOW_NPY` pointer, `LEGS=101 LOOK=900 WRULE=msharpe FSEED=42`). Exact commands (`logs/commands_followup.txt`, launcher `run_followup.sh`):

```
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 CAL=log W3FIX=0.21,0,0.79 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=pod_live_w3fix_callog_s42 /workspace/venv/bin/python w10_universe.py
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 CAL=simple W3FIX=0.21,0,0.79 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=pod_live_w3fix_calsimple_s42 /workspace/venv/bin/python w10_universe.py
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 CAL=log W3FIX=0.21,0,0.79 OUT_TAG=pod_canon_w3fix_callog_s42 /workspace/venv/bin/python w10_universe.py
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 CAL=log MEMBERS_TOPN=829 TRADE_TOPN=400 OUT_TAG=pod_m1t400_callog_s42 /workspace/venv/bin/python w10_universe.py
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 CAL=log FTRIM=zero OUT_TAG=pod_ftrim_callog_s42 /workspace/venv/bin/python w10_universe.py
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 CAL=log TRADE_TOPN=400 OUT_TAG=pod_t400_callog_s42 /workspace/venv/bin/python w10_universe.py
```

Tables: `/workspace/venv/bin/python summarize2.py` → `probe_artifacts/pod_port_followup_tables.md`, `probe_artifacts/pod_port_followup_stats.json`.

**W3FIX code path (verified, not assumed).** Device line 28: `if W3FIX is not None: assert W3FIX == "0.21,0,0.79"` — the value used is the single whitelisted one, so the assertion passed (no Traceback in any log). With W3FIX set, `w3_at(i)` (line 146) returns `[0.21, 0.0, 0.79]` before any msharpe / LEGS / `p < LOOK` logic, for every anchor; `legs()` still runs but its output is unused. `SEATF10=0` ⇒ `W3FC is None` ⇒ the F10 sub-book uses the same fixed vector with F10 in the king slot (line 227). §9.13 confirms the stored `w3_king / w3_rev24 / w3_fund` columns take exactly one value each (0.21 / 0.0 / 0.79) on all 10038 anchors of the three W3FIX runs. Consequence: in W3FIX runs the first-900-anchor equal-weight quirk (§2) does not apply, and the king seat is 0.21 already in 2024 while the king predictions are present from 2024-01 only.

**Every follow-up log** shows `F10 OOS preds aligned: rows 10056/10176, cols 829/829, finite 0.2838`, the expected dummy-receipt `NOTE` lines only, and `DONE`; the live-form runs also show `MEMBERS_TOPN=829: members rebuilt from qvk ranking`. `config_json` of the six runs is in §9.12.

**Decomposition columns and sign convention (item C).** `cols` = `ts, net, pnl, carry, cost, gross_total, gross_member, gross_sel, nsel, nmember, fires, leg_king, leg_rev24, leg_fund, w3_king, w3_rev24, w3_fund, turnover, net_ex, pnl_ex, carry_ex, cost_ex, netlong`. There are two cost columns: `cost` (file-caliber path, from `trade = sm − HB`, device line 275) and `cost_ex` (executor path, from `trr = smr − HR`, line 307). The device stores `net_ex = pnl_ex − carry_ex − cost_ex` (line 312) and `net = pnl − carry − cost` (line 310); §9.1 checks this numerically on every run: max abs residual **0.00e+00** for both identities on all 13 runs, so the decomposition to read is `net_ex = pnl_ex − carry_ex − cost_ex` (using `cost` instead of `cost_ex` leaves a residual of up to 0.05–0.12 bps on single anchors; yearly means of the two cost columns differ by 0.002–0.008). Sign convention: `carry_ex = Σ sm·f_fund_now·(4h/interval) × 1e4` is **positive when the book pays funding** and is subtracted; it is positive on 90–99.6 % of anchors in every run (§9.1 last column). `cost_ex ≥ 0` always (maker/taker mix from `COST_B`). `turnover` (col 17) is `Σ|sm − HB|` of the blended book against the previous blended book on the file-caliber path (line 311); the executor-path turnover is not stored as a column (only its cost, `cost_ex`, is). In the device's own `RECEIPT_EX`, `turnover_ex_mean` is `mean(|cost_ex|)`, not a turnover.

**TRADE_TOPN binding (§9.11, explains the zero 2024 delta of B3).** On the canon member set (meta `members`), no member is ranked ≥ 400 by qvk at any anchor in 2022–2024, so `TRADE_TOPN=400` cannot change `sel` there and B3 is bit-identical to `pod_canon_callog_s42` on every 2024 anchor by construction (the first differing anchor is in 2025; 2858 of 10038 anchors differ in total, all in 2025–2026, where 1469 (2025) and 1452 (2026) anchors have 1–98 members outside the qvk top-400). This is a no-op-by-construction, not a switch that failed to wire.

### 9.1 Residual check of the decomposition (all runs, arm d30_n2_c42, all 10038 anchors)

| run | max abs net_ex − (pnl_ex − carry_ex − cost_ex) | max abs net − (pnl − carry − cost) | max abs net_ex − (pnl_ex − carry_ex − cost) | frac anchors carry_ex > 0 |
|---|---|---|---|---|
| pod_canon_callog_s42 | 0.00e+00 | 0.00e+00 | 0.078 | 0.978 |
| pod_canon_calsimple_s42 | 0.00e+00 | 0.00e+00 | 0.047 | 0.983 |
| pod_live_callog_s42 | 0.00e+00 | 0.00e+00 | 0.101 | 0.897 |
| pod_live_calsimple_s42 | 0.00e+00 | 0.00e+00 | 0.051 | 0.908 |
| pod_live_t3c_callog_s42 | 0.00e+00 | 0.00e+00 | 0.116 | 0.899 |
| pod_live_t3c_callog_s2027 | 0.00e+00 | 0.00e+00 | 0.109 | 0.909 |
| pod_live_callog_s2027 | 0.00e+00 | 0.00e+00 | 0.099 | 0.904 |
| pod_live_w3fix_callog_s42 | 0.00e+00 | 0.00e+00 | 0.081 | 0.978 |
| pod_live_w3fix_calsimple_s42 | 0.00e+00 | 0.00e+00 | 0.080 | 0.977 |
| pod_canon_w3fix_callog_s42 | 0.00e+00 | 0.00e+00 | 0.077 | 0.996 |
| pod_m1t400_callog_s42 | 0.00e+00 | 0.00e+00 | 0.076 | 0.970 |
| pod_ftrim_callog_s42 | 0.00e+00 | 0.00e+00 | 0.079 | 0.907 |
| pod_t400_callog_s42 | 0.00e+00 | 0.00e+00 | 0.079 | 0.978 |

### 9.2 Decomposition by year, all runs (arm d30_n2_c42; yearly MEANS, bps of gross per anchor; net_ex = pnl_ex − carry_ex − cost_ex)

| run | year | n | pnl_ex | carry_ex | cost_ex | cost (file path) | net_ex | turnover (file path Σ\|Δw\|) | w3_king | nsel |
|---|---|---|---|---|---|---|---|---|---|---|
| pod_canon_callog_s42 | 2024 | 2196 | +0.574 | +0.238 | 0.081 | 0.079 | +0.255 | 0.0367 | 0.629 | 270 |
| pod_canon_callog_s42 | 2025 | 2190 | +1.339 | +0.808 | 0.094 | 0.092 | +0.436 | 0.0329 | 0.692 | 372 |
| pod_canon_callog_s42 | 2026 | 1452 | +3.976 | +2.008 | 0.075 | 0.069 | +1.893 | 0.0188 | 0.368 | 318 |
| pod_canon_callog_s42 | 2026<=08-10 | 1332 | +4.492 | +2.043 | 0.075 | 0.070 | +2.373 | 0.0190 | 0.374 | 324 |
| pod_canon_calsimple_s42 | 2024 | 2196 | +0.649 | +0.265 | 0.062 | 0.060 | +0.322 | 0.0271 | 0.420 | 270 |
| pod_canon_calsimple_s42 | 2025 | 2190 | +1.646 | +0.736 | 0.067 | 0.064 | +0.843 | 0.0234 | 0.460 | 372 |
| pod_canon_calsimple_s42 | 2026 | 1452 | +4.784 | +1.609 | 0.044 | 0.038 | +3.132 | 0.0099 | 0.053 | 318 |
| pod_canon_calsimple_s42 | 2026<=08-10 | 1332 | +5.309 | +1.636 | 0.043 | 0.037 | +3.629 | 0.0097 | 0.058 | 324 |
| pod_live_callog_s42 | 2024 | 2196 | +0.398 | +0.167 | 0.083 | 0.081 | +0.149 | 0.0375 | 0.639 | 272 |
| pod_live_callog_s42 | 2025 | 2190 | +0.910 | +0.447 | 0.104 | 0.101 | +0.359 | 0.0357 | 0.673 | 375 |
| pod_live_callog_s42 | 2026 | 1452 | +3.020 | +0.916 | 0.090 | 0.083 | +2.013 | 0.0236 | 0.361 | 324 |
| pod_live_callog_s42 | 2026<=08-10 | 1332 | +3.518 | +0.916 | 0.090 | 0.083 | +2.512 | 0.0238 | 0.368 | 328 |
| pod_live_calsimple_s42 | 2024 | 2196 | +0.479 | +0.195 | 0.065 | 0.062 | +0.220 | 0.0282 | 0.436 | 272 |
| pod_live_calsimple_s42 | 2025 | 2190 | +1.750 | +0.450 | 0.078 | 0.074 | +1.223 | 0.0268 | 0.475 | 375 |
| pod_live_calsimple_s42 | 2026 | 1452 | +5.146 | +0.842 | 0.057 | 0.049 | +4.247 | 0.0138 | 0.052 | 324 |
| pod_live_calsimple_s42 | 2026<=08-10 | 1332 | +5.718 | +0.840 | 0.056 | 0.048 | +4.823 | 0.0136 | 0.057 | 328 |
| pod_live_t3c_callog_s42 | 2024 | 2196 | +0.367 | +0.171 | 0.087 | 0.086 | +0.109 | 0.0383 | 0.639 | 272 |
| pod_live_t3c_callog_s42 | 2025 | 2190 | +0.895 | +0.463 | 0.104 | 0.101 | +0.328 | 0.0357 | 0.673 | 375 |
| pod_live_t3c_callog_s42 | 2026 | 1452 | +3.024 | +0.944 | 0.091 | 0.084 | +1.989 | 0.0240 | 0.361 | 324 |
| pod_live_t3c_callog_s42 | 2026<=08-10 | 1332 | +3.541 | +0.944 | 0.091 | 0.085 | +2.505 | 0.0243 | 0.368 | 328 |
| pod_live_t3c_callog_s2027 | 2024 | 2196 | +0.433 | +0.171 | 0.084 | 0.083 | +0.178 | 0.0375 | 0.639 | 272 |
| pod_live_t3c_callog_s2027 | 2025 | 2190 | +0.987 | +0.477 | 0.099 | 0.095 | +0.411 | 0.0335 | 0.673 | 375 |
| pod_live_t3c_callog_s2027 | 2026 | 1452 | +3.050 | +0.949 | 0.095 | 0.088 | +2.006 | 0.0252 | 0.361 | 324 |
| pod_live_t3c_callog_s2027 | 2026<=08-10 | 1332 | +3.564 | +0.950 | 0.096 | 0.090 | +2.519 | 0.0255 | 0.368 | 328 |
| pod_live_callog_s2027 | 2024 | 2196 | +0.465 | +0.167 | 0.081 | 0.080 | +0.217 | 0.0369 | 0.639 | 272 |
| pod_live_callog_s2027 | 2025 | 2190 | +0.994 | +0.460 | 0.097 | 0.093 | +0.438 | 0.0336 | 0.673 | 375 |
| pod_live_callog_s2027 | 2026 | 1452 | +3.007 | +0.920 | 0.094 | 0.087 | +1.994 | 0.0247 | 0.361 | 324 |
| pod_live_callog_s2027 | 2026<=08-10 | 1332 | +3.500 | +0.920 | 0.094 | 0.088 | +2.486 | 0.0250 | 0.368 | 328 |
| pod_live_w3fix_callog_s42 | 2024 | 2196 | -0.268 | +0.340 | 0.034 | 0.031 | -0.642 | 0.0143 | 0.210 | 272 |
| pod_live_w3fix_callog_s42 | 2025 | 2190 | +1.005 | +0.678 | 0.042 | 0.037 | +0.284 | 0.0126 | 0.210 | 375 |
| pod_live_w3fix_callog_s42 | 2026 | 1452 | +3.363 | +0.916 | 0.069 | 0.061 | +2.378 | 0.0171 | 0.210 | 324 |
| pod_live_w3fix_callog_s42 | 2026<=08-10 | 1332 | +3.894 | +0.916 | 0.068 | 0.060 | +2.911 | 0.0168 | 0.210 | 328 |
| pod_live_w3fix_calsimple_s42 | 2024 | 2196 | +0.016 | +0.341 | 0.034 | 0.031 | -0.358 | 0.0143 | 0.210 | 272 |
| pod_live_w3fix_calsimple_s42 | 2025 | 2190 | +2.125 | +0.677 | 0.042 | 0.036 | +1.406 | 0.0125 | 0.210 | 375 |
| pod_live_w3fix_calsimple_s42 | 2026 | 1452 | +5.321 | +0.908 | 0.069 | 0.060 | +4.344 | 0.0170 | 0.210 | 324 |
| pod_live_w3fix_calsimple_s42 | 2026<=08-10 | 1332 | +5.920 | +0.905 | 0.068 | 0.060 | +4.948 | 0.0168 | 0.210 | 328 |
| pod_canon_w3fix_callog_s42 | 2024 | 2196 | -0.113 | +0.429 | 0.032 | 0.029 | -0.574 | 0.0129 | 0.210 | 270 |
| pod_canon_w3fix_callog_s42 | 2025 | 2190 | +1.354 | +1.107 | 0.030 | 0.026 | +0.218 | 0.0086 | 0.210 | 372 |
| pod_canon_w3fix_callog_s42 | 2026 | 1452 | +4.121 | +1.908 | 0.054 | 0.047 | +2.158 | 0.0124 | 0.210 | 318 |
| pod_canon_w3fix_callog_s42 | 2026<=08-10 | 1332 | +4.644 | +1.941 | 0.053 | 0.047 | +2.649 | 0.0123 | 0.210 | 324 |
| pod_m1t400_callog_s42 | 2024 | 2196 | +0.509 | +0.230 | 0.081 | 0.080 | +0.197 | 0.0368 | 0.639 | 272 |
| pod_m1t400_callog_s42 | 2025 | 2190 | +1.250 | +0.803 | 0.097 | 0.094 | +0.350 | 0.0330 | 0.673 | 375 |
| pod_m1t400_callog_s42 | 2026 | 1452 | +4.051 | +1.903 | 0.074 | 0.066 | +2.074 | 0.0182 | 0.361 | 324 |
| pod_m1t400_callog_s42 | 2026<=08-10 | 1332 | +4.544 | +1.931 | 0.074 | 0.067 | +2.539 | 0.0183 | 0.368 | 328 |
| pod_ftrim_callog_s42 | 2024 | 2196 | +0.466 | +0.173 | 0.082 | 0.081 | +0.211 | 0.0374 | 0.629 | 270 |
| pod_ftrim_callog_s42 | 2025 | 2190 | +1.061 | +0.482 | 0.100 | 0.098 | +0.479 | 0.0352 | 0.692 | 372 |
| pod_ftrim_callog_s42 | 2026 | 1452 | +2.953 | +1.039 | 0.091 | 0.086 | +1.823 | 0.0244 | 0.368 | 318 |
| pod_ftrim_callog_s42 | 2026<=08-10 | 1332 | +3.421 | +1.052 | 0.092 | 0.087 | +2.277 | 0.0247 | 0.374 | 324 |
| pod_t400_callog_s42 | 2024 | 2196 | +0.574 | +0.238 | 0.081 | 0.079 | +0.255 | 0.0367 | 0.629 | 270 |
| pod_t400_callog_s42 | 2025 | 2190 | +1.229 | +0.790 | 0.097 | 0.095 | +0.341 | 0.0334 | 0.692 | 370 |
| pod_t400_callog_s42 | 2026 | 1452 | +3.960 | +1.991 | 0.075 | 0.069 | +1.894 | 0.0188 | 0.368 | 318 |
| pod_t400_callog_s42 | 2026<=08-10 | 1332 | +4.473 | +2.025 | 0.075 | 0.070 | +2.373 | 0.0190 | 0.374 | 324 |

### 9.3 A1 vs A2 — live form with fixed seats W3FIX=0.21,0,0.79: CAL=log vs CAL=simple

| year | log mean | simple mean | log Sharpe | simple Sharpe | log worst mo | simple worst mo | log maxDD | simple maxDD | log w3_king | simple w3_king | log turnover | simple turnover | n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | -0.642 | -0.358 | -1.68 | -0.92 | -717 (2024-11) | -576 (2024-11) | 1815 | 1514 | 0.210 | 0.210 | 0.0143 | 0.0143 | 2196 |
| 2025 | +0.284 | +1.406 | 0.67 | 3.08 | -635 (2025-01) | -464 (2025-01) | 902 | 717 | 0.210 | 0.210 | 0.0126 | 0.0125 | 2190 |
| 2026 | +2.378 | +4.344 | 4.21 | 7.49 | -252 (2026-08) | +42 (2026-08) | 774 | 694 | 0.210 | 0.210 | 0.0171 | 0.0170 | 1452 |
| 2026<=08-10 | +2.911 | +4.948 | 5.16 | 8.55 | +171 (2026-02) | +324 (2026-08) | 458 | 264 | 0.210 | 0.210 | 0.0168 | 0.0168 | 1332 |
| 2024on | +0.457 | +1.473 | 1.02 | 3.14 | -717 (2024-11) | -576 (2024-11) | 2614 | 2126 | 0.210 | 0.210 | 0.0143 | 0.0143 | 5838 |

### 9.4 A1 (fixed seats) vs pod_live_callog_s42 (msharpe seats), live form, CAL=log

| year | base mean | arm mean | Δ mean | base Sharpe | arm Sharpe | Δ Sharpe | base worst mo | arm worst mo | base maxDD | arm maxDD | base w3_king | arm w3_king | base turnover | arm turnover | base nsel | arm nsel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.149 | -0.642 | -0.791 | 0.53 | -1.68 | -2.21 | -363 | -717 | 795 | 1815 | 0.639 | 0.210 | 0.0375 | 0.0143 | 272 | 272 |
| 2025 | +0.359 | +0.284 | -0.075 | 1.15 | 0.67 | -0.47 | -294 | -635 | 418 | 902 | 0.673 | 0.210 | 0.0357 | 0.0126 | 375 | 375 |
| 2026 | +2.013 | +2.378 | +0.365 | 3.84 | 4.21 | +0.37 | -294 | -252 | 771 | 774 | 0.361 | 0.210 | 0.0236 | 0.0171 | 324 | 324 |
| 2026<=08-10 | +2.512 | +2.911 | +0.399 | 4.83 | 5.16 | +0.33 | +104 | +171 | 452 | 458 | 0.368 | 0.210 | 0.0238 | 0.0168 | 328 | 328 |
| 2024on | +0.691 | +0.457 | -0.235 | 1.88 | 1.02 | -0.87 | -363 | -717 | 795 | 2614 | 0.583 | 0.210 | 0.0334 | 0.0143 | 324 | 324 |

### 9.5 A2 (fixed seats) vs pod_live_calsimple_s42 (msharpe seats), live form, CAL=simple

| year | base mean | arm mean | Δ mean | base Sharpe | arm Sharpe | Δ Sharpe | base worst mo | arm worst mo | base maxDD | arm maxDD | base w3_king | arm w3_king | base turnover | arm turnover | base nsel | arm nsel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.220 | -0.358 | -0.578 | 0.75 | -0.92 | -1.67 | -343 | -576 | 586 | 1514 | 0.436 | 0.210 | 0.0282 | 0.0143 | 272 | 272 |
| 2025 | +1.223 | +1.406 | +0.183 | 3.37 | 3.08 | -0.30 | -370 | -464 | 647 | 717 | 0.475 | 0.210 | 0.0268 | 0.0125 | 375 | 375 |
| 2026 | +4.247 | +4.344 | +0.097 | 7.63 | 7.49 | -0.14 | +85 | +42 | 689 | 694 | 0.052 | 0.210 | 0.0138 | 0.0170 | 324 | 324 |
| 2026<=08-10 | +4.823 | +4.948 | +0.125 | 8.70 | 8.55 | -0.14 | +343 | +324 | 252 | 264 | 0.057 | 0.210 | 0.0136 | 0.0168 | 328 | 328 |
| 2024on | +1.597 | +1.473 | -0.124 | 4.00 | 3.14 | -0.86 | -370 | -576 | 689 | 2126 | 0.355 | 0.210 | 0.0241 | 0.0143 | 324 | 324 |

### 9.6 A3 (canon form, fixed seats) vs pod_canon_callog_s42 (canon, msharpe seats), CAL=log

| year | base mean | arm mean | Δ mean | base Sharpe | arm Sharpe | Δ Sharpe | base worst mo | arm worst mo | base maxDD | arm maxDD | base w3_king | arm w3_king | base turnover | arm turnover | base nsel | arm nsel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.255 | -0.574 | -0.829 | 0.86 | -1.43 | -2.29 | -380 | -635 | 719 | 1835 | 0.629 | 0.210 | 0.0367 | 0.0129 | 270 | 270 |
| 2025 | +0.436 | +0.218 | -0.219 | 1.25 | 0.50 | -0.74 | -367 | -616 | 503 | 1040 | 0.692 | 0.210 | 0.0329 | 0.0086 | 372 | 372 |
| 2026 | +1.893 | +2.158 | +0.265 | 3.64 | 3.98 | +0.34 | -280 | -245 | 727 | 709 | 0.368 | 0.210 | 0.0188 | 0.0124 | 318 | 318 |
| 2026<=08-10 | +2.373 | +2.649 | +0.276 | 4.61 | 4.93 | +0.31 | +34 | +75 | 395 | 394 | 0.374 | 0.210 | 0.0190 | 0.0123 | 324 | 324 |
| 2024on | +0.730 | +0.403 | -0.328 | 1.91 | 0.89 | -1.02 | -380 | -635 | 727 | 2742 | 0.588 | 0.210 | 0.0308 | 0.0112 | 320 | 320 |

### 9.7 B1 MEMBERS_TOPN=829 TRADE_TOPN=400 (no FTRIM) vs pod_canon_callog_s42

| year | base mean | arm mean | Δ mean | base Sharpe | arm Sharpe | Δ Sharpe | base worst mo | arm worst mo | base maxDD | arm maxDD | base w3_king | arm w3_king | base turnover | arm turnover | base nsel | arm nsel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.255 | +0.197 | -0.057 | 0.86 | 0.70 | -0.16 | -380 | -378 | 719 | 787 | 0.629 | 0.639 | 0.0367 | 0.0368 | 270 | 272 |
| 2025 | +0.436 | +0.350 | -0.086 | 1.25 | 1.18 | -0.07 | -367 | -320 | 503 | 518 | 0.692 | 0.673 | 0.0329 | 0.0330 | 372 | 375 |
| 2026 | +1.893 | +2.074 | +0.181 | 3.64 | 3.97 | +0.34 | -280 | -200 | 727 | 640 | 0.368 | 0.361 | 0.0188 | 0.0182 | 318 | 324 |
| 2026<=08-10 | +2.373 | +2.539 | +0.166 | 4.61 | 4.90 | +0.28 | +34 | +83 | 395 | 426 | 0.374 | 0.368 | 0.0190 | 0.0183 | 324 | 328 |
| 2024on | +0.730 | +0.721 | -0.009 | 1.91 | 1.99 | +0.09 | -380 | -378 | 727 | 787 | 0.588 | 0.583 | 0.0308 | 0.0307 | 320 | 324 |

### 9.8 B2 FTRIM=zero vs pod_canon_callog_s42

| year | base mean | arm mean | Δ mean | base Sharpe | arm Sharpe | Δ Sharpe | base worst mo | arm worst mo | base maxDD | arm maxDD | base w3_king | arm w3_king | base turnover | arm turnover | base nsel | arm nsel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.255 | +0.211 | -0.044 | 0.86 | 0.73 | -0.13 | -380 | -366 | 719 | 725 | 0.629 | 0.629 | 0.0367 | 0.0374 | 270 | 270 |
| 2025 | +0.436 | +0.479 | +0.042 | 1.25 | 1.28 | +0.04 | -367 | -303 | 503 | 430 | 0.692 | 0.692 | 0.0329 | 0.0352 | 372 | 372 |
| 2026 | +1.893 | +1.823 | -0.070 | 3.64 | 3.49 | -0.15 | -280 | -299 | 727 | 798 | 0.368 | 0.368 | 0.0188 | 0.0244 | 318 | 318 |
| 2026<=08-10 | +2.373 | +2.277 | -0.097 | 4.61 | 4.41 | -0.20 | +34 | +22 | 395 | 417 | 0.374 | 0.374 | 0.0190 | 0.0247 | 324 | 324 |
| 2024on | +0.730 | +0.712 | -0.018 | 1.91 | 1.83 | -0.08 | -380 | -366 | 727 | 798 | 0.588 | 0.588 | 0.0308 | 0.0333 | 320 | 320 |

### 9.9 B3 TRADE_TOPN=400 vs pod_canon_callog_s42

| year | base mean | arm mean | Δ mean | base Sharpe | arm Sharpe | Δ Sharpe | base worst mo | arm worst mo | base maxDD | arm maxDD | base w3_king | arm w3_king | base turnover | arm turnover | base nsel | arm nsel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.255 | +0.255 | +0.000 | 0.86 | 0.86 | +0.00 | -380 | -380 | 719 | 719 | 0.629 | 0.629 | 0.0367 | 0.0367 | 270 | 270 |
| 2025 | +0.436 | +0.341 | -0.095 | 1.25 | 1.15 | -0.09 | -367 | -429 | 503 | 602 | 0.692 | 0.692 | 0.0329 | 0.0334 | 372 | 370 |
| 2026 | +1.893 | +1.894 | +0.001 | 3.64 | 3.71 | +0.07 | -280 | -271 | 727 | 720 | 0.368 | 0.368 | 0.0188 | 0.0188 | 318 | 318 |
| 2026<=08-10 | +2.373 | +2.373 | -0.001 | 4.61 | 4.71 | +0.10 | +34 | +23 | 395 | 392 | 0.374 | 0.374 | 0.0190 | 0.0190 | 324 | 324 |
| 2024on | +0.730 | +0.695 | -0.036 | 1.91 | 1.92 | +0.01 | -380 | -429 | 727 | 720 | 0.588 | 0.588 | 0.0308 | 0.0310 | 320 | 319 |

### 9.10 Series identity checks (max abs difference of the per-anchor net_ex series; 0 = bit-identical books)

| A | B | max abs Δ net_ex | anchors with Δ≠0 | max abs Δ nsel |
|---|---|---|---|---|
| pod_canon_callog_s42 | pod_t400_callog_s42 | 5.775e+01 | 2858 | 12 |
| pod_canon_callog_s42 | pod_ftrim_callog_s42 | 4.292e+01 | 10038 | 0 |
| pod_canon_callog_s42 | pod_m1t400_callog_s42 | 7.339e+01 | 10038 | 90 |
| pod_live_callog_s42 | pod_m1t400_callog_s42 | 5.991e+01 | 10038 | 0 |
| pod_live_callog_s42 | pod_live_w3fix_callog_s42 | 1.692e+02 | 10038 | 0 |
| pod_canon_callog_s42 | pod_canon_w3fix_callog_s42 | 2.291e+02 | 10038 | 0 |

### 9.11 TRADE_TOPN=400 binding diagnostic on meta members (canon form): members ranked ≥400 by qvk at the anchor

| year | anchors | mean #members | anchors with ≥1 member outside qvk top-400 | mean #outside | max #outside |
|---|---|---|---|---|---|
| 2022 | 2148 | 139.2 | 0 | 0.00 | 0 |
| 2023 | 2190 | 187.4 | 0 | 0.00 | 0 |
| 2024 | 2196 | 273.9 | 0 | 0.00 | 0 |
| 2025 | 2190 | 388.0 | 1469 | 3.64 | 13 |
| 2026 | 1452 | 400.0 | 1452 | 8.46 | 98 |

### 9.12 config_json of the six follow-up runs

- `pod_live_w3fix_callog_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": "0.21,0,0.79", "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_live_w3fix_calsimple_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": "0.21,0,0.79", "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "simple", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_canon_w3fix_callog_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": "0.21,0,0.79", "MEMBERS_TOPN": 0, "TRADE_TOPN": 0, "FTRIM": "off", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_m1t400_callog_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "off", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_ftrim_callog_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 0, "TRADE_TOPN": 0, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_t400_callog_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 0, "TRADE_TOPN": 400, "FTRIM": "off", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`

### 9.13 W3FIX code-path check (w3_king / w3_fund columns must be constant 0.21 / 0.79 on every anchor)

- `pod_live_w3fix_callog_s42`: w3_king unique = [0.21], w3_rev24 unique = [0.0], w3_fund unique = [0.79], anchors 10038
- `pod_live_w3fix_calsimple_s42`: w3_king unique = [0.21], w3_rev24 unique = [0.0], w3_fund unique = [0.79], anchors 10038
- `pod_canon_w3fix_callog_s42`: w3_king unique = [0.21], w3_rev24 unique = [0.0], w3_fund unique = [0.79], anchors 10038

### 9.14 RECEIPT_EX lines verbatim, follow-up runs (both arms per run)

```
logs/pod_live_w3fix_callog_s42.log:RECEIPT_EX S0 {"net_ex_all": 0.1409, "net_ex_2024on": 0.4114, "sharpe_ex_2024on": 0.831, "by_year_ex": {"2022": -0.15, "2023": -0.313, "2024": -0.674, "2025": 0.154, "2026": 2.441}, "carry_ex_mean": 0.5597, "cost_ex_mean": 0.0392, "turnover_ex_mean": 0.0392, "netlong_mean": -0.0366, "netlong_by_year": {"2022": -0.0258, "2023": -0.0188, "2024": -0.0215, "2025": -0.0704, "2026": -0.0506}}
logs/pod_live_w3fix_callog_s42.log:RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.1584, "net_ex_2024on": 0.4566, "sharpe_ex_2024on": 1.017, "by_year_ex": {"2022": -0.12, "2023": -0.381, "2024": -0.642, "2025": 0.284, "2026": 2.378}, "carry_ex_mean": 0.5053, "cost_ex_mean": 0.0401, "turnover_ex_mean": 0.0401, "netlong_mean": -0.0466, "netlong_by_year": {"2022": -0.0382, "2023": -0.0113, "2024": -0.0244, "2025": -0.0978, "2026": -0.0676}}
logs/pod_live_w3fix_calsimple_s42.log:RECEIPT_EX S0 {"net_ex_all": 0.6552, "net_ex_2024on": 1.4029, "sharpe_ex_2024on": 2.751, "by_year_ex": {"2022": -0.481, "2023": -0.296, "2024": -0.398, "2025": 1.315, "2026": 4.259}, "carry_ex_mean": 0.5597, "cost_ex_mean": 0.0392, "turnover_ex_mean": 0.0392, "netlong_mean": -0.0366, "netlong_by_year": {"2022": -0.0258, "2023": -0.0188, "2024": -0.0215, "2025": -0.0704, "2026": -0.0506}}
logs/pod_live_w3fix_calsimple_s42.log:RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.7087, "net_ex_2024on": 1.4731, "sharpe_ex_2024on": 3.139, "by_year_ex": {"2022": -0.43, "2023": -0.284, "2024": -0.358, "2025": 1.406, "2026": 4.344}, "carry_ex_mean": 0.5038, "cost_ex_mean": 0.04, "turnover_ex_mean": 0.03998, "netlong_mean": -0.0401, "netlong_by_year": {"2022": -0.0306, "2023": -0.0105, "2024": -0.0183, "2025": -0.0871, "2026": -0.0601}}
logs/pod_canon_w3fix_callog_s42.log:RECEIPT_EX S0 {"net_ex_all": 0.1085, "net_ex_2024on": 0.3872, "sharpe_ex_2024on": 0.763, "by_year_ex": {"2022": -0.209, "2023": -0.343, "2024": -0.601, "2025": 0.102, "2026": 2.311}, "carry_ex_mean": 0.9535, "cost_ex_mean": 0.0326, "turnover_ex_mean": 0.0326, "netlong_mean": -0.0324, "netlong_by_year": {"2022": -0.0324, "2023": -0.0301, "2024": -0.0376, "2025": -0.044, "2026": -0.0105}}
logs/pod_canon_w3fix_callog_s42.log:RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.1423, "net_ex_2024on": 0.4025, "sharpe_ex_2024on": 0.891, "by_year_ex": {"2022": -0.166, "2023": -0.269, "2024": -0.574, "2025": 0.218, "2026": 2.158}, "carry_ex_mean": 0.827, "cost_ex_mean": 0.0337, "turnover_ex_mean": 0.03375, "netlong_mean": -0.0413, "netlong_by_year": {"2022": -0.0447, "2023": -0.0219, "2024": -0.0395, "2025": -0.0657, "2026": -0.0316}}
logs/pod_m1t400_callog_s42.log:RECEIPT_EX S0 {"net_ex_all": 0.3262, "net_ex_2024on": 0.718, "sharpe_ex_2024on": 1.818, "by_year_ex": {"2022": 0.047, "2023": -0.462, "2024": 0.149, "2025": 0.347, "2026": 2.138}, "carry_ex_mean": 0.8168, "cost_ex_mean": 0.0661, "turnover_ex_mean": 0.0661, "netlong_mean": -0.0151, "netlong_by_year": {"2022": -0.008, "2023": -0.0197, "2024": -0.0009, "2025": -0.0165, "2026": -0.0376}}
logs/pod_m1t400_callog_s42.log:RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.3372, "net_ex_2024on": 0.7214, "sharpe_ex_2024on": 1.995, "by_year_ex": {"2022": 0.06, "2023": -0.432, "2024": 0.197, "2025": 0.35, "2026": 2.074}, "carry_ex_mean": 0.7149, "cost_ex_mean": 0.0662, "turnover_ex_mean": 0.0662, "netlong_mean": -0.0163, "netlong_by_year": {"2022": -0.0166, "2023": -0.011, "2024": 0.0002, "2025": -0.0198, "2026": -0.0435}}
logs/pod_ftrim_callog_s42.log:RECEIPT_EX S0 {"net_ex_all": 0.3986, "net_ex_2024on": 0.747, "sharpe_ex_2024on": 1.797, "by_year_ex": {"2022": 0.103, "2023": -0.259, "2024": 0.178, "2025": 0.519, "2026": 1.951}, "carry_ex_mean": 0.472, "cost_ex_mean": 0.0716, "turnover_ex_mean": 0.07161, "netlong_mean": -0.0247, "netlong_by_year": {"2022": -0.0248, "2023": -0.0399, "2024": -0.0309, "2025": -0.0131, "2026": -0.01}}
logs/pod_ftrim_callog_s42.log:RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.3749, "net_ex_2024on": 0.7124, "sharpe_ex_2024on": 1.829, "by_year_ex": {"2022": 0.059, "2023": -0.234, "2024": 0.211, "2025": 0.479, "2026": 1.823}, "carry_ex_mean": 0.4344, "cost_ex_mean": 0.0714, "turnover_ex_mean": 0.0714, "netlong_mean": -0.0235, "netlong_by_year": {"2022": -0.0296, "2023": -0.031, "2024": -0.0253, "2025": -0.0115, "2026": -0.0192}}
logs/pod_t400_callog_s42.log:RECEIPT_EX S0 {"net_ex_all": 0.3081, "net_ex_2024on": 0.71, "sharpe_ex_2024on": 1.789, "by_year_ex": {"2022": -0.12, "2023": -0.37, "2024": 0.178, "2025": 0.387, "2026": 2.002}, "carry_ex_mean": 0.8106, "cost_ex_mean": 0.0672, "turnover_ex_mean": 0.06723, "netlong_mean": -0.0289, "netlong_by_year": {"2022": -0.0206, "2023": -0.0365, "2024": -0.0279, "2025": -0.0345, "2026": -0.0217}}
logs/pod_t400_callog_s42.log:RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.3084, "net_ex_2024on": 0.6948, "sharpe_ex_2024on": 1.92, "by_year_ex": {"2022": -0.149, "2023": -0.302, "2024": 0.255, "2025": 0.341, "2026": 1.894}, "carry_ex_mean": 0.7154, "cost_ex_mean": 0.0673, "turnover_ex_mean": 0.06726, "netlong_mean": -0.0313, "netlong_by_year": {"2022": -0.0274, "2023": -0.0293, "2024": -0.0277, "2025": -0.0405, "2026": -0.0314}}
```

### 9.15 Files added by the follow-up

Pod `/workspace/port_w10/`: `run_followup.sh`, `summarize2.py`, `logs/commands_followup.txt`, `logs/pod_<tag>.log` ×6, `logs/summarize2.out`; `probe_artifacts/w10_ablation_series_<tag>.npz` ×6 and `w10_ablation_summary_<tag>.json` ×6 for tags `pod_live_w3fix_callog_s42`, `pod_live_w3fix_calsimple_s42`, `pod_canon_w3fix_callog_s42`, `pod_m1t400_callog_s42`, `pod_ftrim_callog_s42`, `pod_t400_callog_s42`; `probe_artifacts/pod_port_followup_tables.md`, `pod_port_followup_stats.json`, `pod_port_receipts_ex_followup.txt`. Mac scratchpad: `pod_port_REPORT.md` (this file, re-copied), the six new `w10_ablation_summary_<tag>.json`, `pod_port_followup_tables.md`, `pod_port_followup_stats.json`, `pod_port_receipts_ex_followup.txt`, `commands_followup.txt`, `summarize2.py`, `run_followup.sh`. Read-only outside `/workspace/port_w10/`; no GPU job.
