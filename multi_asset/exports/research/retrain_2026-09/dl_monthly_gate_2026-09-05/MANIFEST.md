# MANIFEST — dl_monthly_gate_2026-09-05 (PREREG_dl_monthly_gate_and_phi_grid_2026-09-05 §A, sha256 05801bb2…, commit dfbe516)

> **创建:** 2026-09-05 14:3xZ(归档; 计算 pod2 2026-09-05 11:27:48Z–11:29:57Z, `logs/commands.txt` CHAIN START → JUDGE rc=0; SHA256SUMS.txt 11:30:01Z)| **Session:** b9646a9e, teammate Track B(allweather)| **状态:** 归档 final; pod 原件只读 | **作废条件:** pod 原件任一 sha 与本目录 `POD_SHA256SUMS_*.txt` 不符

pod2 root: `/workspace/review_scratch/dl_monthly_gate/`(987 MB, 329 文件, 其中 260 个 .npy/.npz 不入 git)。本目录 = 全部脚本 / 结果 json / REPORT / 日志 / 回放装置脚本 / 摘要 json 的逐字节拷贝(`SHA256SUMS` = 本地 sha256; 与 pod 端逐一相等, 校验收据见下)。数组文件只留 pod 路径 + sha256。

## 1. 校验收据(2026-09-05 14:2xZ, 本机 shasum -a 256 vs pod 端 sha256sum)
- `POD_SHA256SUMS_all_artifacts.txt`(= pod `SHA256SUMS.txt`, 263 行, pod-side sha `dc2af5f6…`): 已归档的 17 个非数组文件 **17/17 相等**; 其余 246 行 = 数组(210 preds_model/*.npz + 10 series/*.npy + 10 replay/dev_alt/f8_2026-08-22/preds/*.npy + 16 replay/dev_alt/probe_artifacts/*.npz)未归档。
- `POD_SHA256SUMS_logs_and_replay.txt`(pod 端 sha256sum, 68 行: logs/ 9 + replay/logs/ 22 + replay/dev_alt/logs/ 16 + probe_artifacts 摘要 json 16 + replay 脚本 5): **68/68 相等**。
- `verify_rerun/`: 判官在 pod 上以**同一脚本(仅输出路径改为环境变量, diff 一行, `judge_verify.diff`)**重跑到 `/workspace/review_scratch/allweather_trackB/part0_verify/judge_gate_rerun.json`, 与原 `results/judge_gate.json` **`cmp` 逐字节相等**(sha256 `1f0385e19a9619be8458443343e84be18de48cffd40c86fa70ca69e2a019bc1f` 两侧同; `verify_rerun/commands.txt` 逐字, rc=0, 2026-09-05T14:21:32Z)。原件未被写入(mtime 仍 11:29:57Z)。
- `series/mE1_R0.npy` sha `54bd748d2f155377…` = RESULT_dl_monthly_walkforward(f311321)记录的 mE1 拼接文件 sha(`simulate_mE1.log`: "R0 series == dl_monthly_wf stitched file: True"; "R0 spliced == earlier mE1spl replay input: True")。

## 2. 目录内容
| 文件 | 作用 |
|---|---|
| `setup_gate.sh` / `chain_gate.sh` / `run_gate_replay.sh` | 装置搭建(w10_health.py / w10_seat2g.py 拷贝与 sha 断言)、全链、回放批 |
| `infer_fold_models.py` | GPU 只推断: 40 个折模型(dl_monthly_wf/models/*.pt)对其 test 月后 1..6 月龄重推, 与 preds_fold 逐位比对(40/40 bitwise, max\|Δ\| 0) → `preds_model/*.npz`(210 件, pod) + `preds_model_manifest.json`(含每模型 .pt sha 前 12 位、训练截止、首评分锚、n_train) |
| `simulate_gates.py` | §A2 规则臂 R0/R1/R2/R3/R4 因果模拟(IC / 秩腿净额定义在文件头), 输出 `results/decisions_{mE1,mE60}.json`, `results/score_{mE1,mE60}.json`, `series/*.npy`(ext 网格)与 `replay/dev_alt/f8_2026-08-22/preds/f10_gate_*_s42.npy`(0822 网格拼接: 2025-01-01 前取年折 s42 行) |
| `judge_gate.py` | 冻结判官 §A4(数字前写就): 每 gross 配对差, UTC 日块自举 2000 种子 20260905, 主窗 2025-03-01→2026-08-10 20Z; 单月条款; keepable 条款; §A3 φdyn → `results/judge_gate.json` |
| `render_gate_report.py` → `REPORT_tables.md` | T1–T9 表(推断收据 / 决策表 / IC 矩阵 / 回放水平 / 配对差 / 逐月贡献 / φdyn / 判官 / 命令) |
| `build_result_gate_doc.py` → `gate_tables.md` | **本归档新增**: 只读 `results/*.json` 渲染 RESULT 文档嵌入的表 A–H(单位链脚本打印, E-0904-G); 日志 `logs/build_result_gate_doc.log` |
| `results/` | `judge_gate.json`(215 KB)· `decisions_mE1.json` · `decisions_mE60.json` · `score_mE1.json` · `score_mE60.json` |
| `logs/` | `commands.txt`(逐字命令 + rc)· `setup_gate.log` · `infer_fold_models.log` · `simulate_mE1.log` · `simulate_mE60.log` · `run_gate_replay.log` · `judge_gate.log` · `render.log` · `chain_gate.out`(空) |
| `replay/` | `w10_health.py`(sha `8684d9a9f43a8d15…` = health_check 原件)· `w10_seat2g.py`(`13d0c849…` = seat_round2 `w10_seat2.py` 仅 PHIDYN_CLIP 改读环境变量, diff 见 setup_gate.log)· `w10_seat2_orig.py`(`5285f004…`)· `check_equiv.py` · `run_arm.sh` · `logs/`(每臂 .out、`commands.txt` 逐字、`check_equiv.log` 4 PASS、`eq_chain.log`、`setup_sha256.txt`、`replay_sha256.txt`)· `dev_alt/logs/`(每臂装置日志)· `dev_alt/probe_artifacts/*_summary_*.json`(16 件摘要) |
| `verify_rerun/` | 判官复跑收据(`commands.txt`, `judge_verify.diff`, `judge_verify.log`, `POD_SHA256SUMS.txt`) |

## 3. 未归档的数组(pod 路径 + sha256 见 `POD_SHA256SUMS_all_artifacts.txt`)
- `preds_model/{mE1,mE60}_{YYYYMM}_age{1..6}_{YYYYMM}.npz`(210 件): 每模型每月龄的预测。
- `series/{mE1,mE60}_{R0..R4}.npy`(10 件, ext 网格 nA×829, 2025-01 前 NaN)。
- `replay/dev_alt/f8_2026-08-22/preds/f10_gate_{mE1,mE60}_{R0..R4}_s42.npy`(10 件, 回放输入; mE60_R1 与 mE60_R3 同 sha `6b843b51…`, 因 E60 下 R3 决策序列 = R1)。
- `replay/dev_alt/probe_artifacts/w10_ablation_series_{BASE_s42,BASE_s2027,G_*,SEAT2DEF_s42}.npz`(16 件, 判官输入; 每件 sha 前 16 位亦记在 `results/judge_gate.json["arms"]`)。
- 折模型与折预测原件在 `/workspace/review_scratch/dl_monthly_wf/{models,preds_fold}/`(sha 见 `../dl_monthly_wf_2026-09-05/POD_SHA256SUMS_all_artifacts.txt`; 每模型 .pt sha 前 12 位亦在 `preds_model_manifest.json`)。

## 4. 固定输入(sha256, `replay/logs/setup_sha256.txt` / `preds_model_manifest.json`)
```
31d043e8f160a1d4475d5992a069c4b602419d78c7916f710d1e56ae8915caf9  targets (dlw_ext)
9bc111a47cee54fc26193165258a83eb11f59df79bebcd69452532bb4c59678e  fea82
bebf2720315499707e54b53c26d889cbf6f2d2d3184a42455284636c0c5e4d67  fea89
baf747ceb31f10d614ffac79b9c969c499e1c3e9f82edfec246d7cfb0f353ace  /workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy   (R-yearly s42 = 09-01 门跑)
c742ffaa1f4397aee55a31a5486aabfd89ae28624123bbda535a7d41851b2a0b  /workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy (R-yearly s2027)
8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d  replay/w10_health.py (= /workspace/review_scratch/health_check/w10_health.py)
13d0c849fc472fb1b1cbe1d37855aff481fe6fe048a61225fef2a74f520fda57  replay/w10_seat2g.py
ccb7a0805be2a106898467b5ffef3a8fd4813a659e044492c0a437b0e5d7aece  /workspace/review_scratch/health_check/masks/umask_UPIT.npz
9349ca634747772dcfc9adfb7a42a5c7b5b34f60bc7f31bc6fd95c4ae5d0fc42  /workspace/review_scratch/health_check/calib/costb_fee_steady.json
158cd4ac8f8f30f7f41a5a6cba0bd19a450ce756727e4aeae3d4e4b0b67d0054  /workspace/shadow_bundle_v3/slow_pred_pinned.npy (pinned king)
```
回放臂环境(逐字, `replay/logs/commands.txt`): `LEGS=101 CAL=log SLOW_NPY=… WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=… COSTB_JSON=… FSEED=42 FPRED=f10_gate_<TAG>_<ARM>_s42.npy`; φdyn 臂加 `PHIDYN=1 PHIDYN_CLIP=0.3,0.6` 走 `w10_seat2g.py`。等价收据(`replay/logs/check_equiv.log`): BASE_s42/BASE_s2027 四数组 `array_equal` = health_check `M1_UPIT_prod_s{42,2027}_ccal`; w10_seat2g PHIDYN=0 = w10_health(BASE 与 R1 两组)。

## 5. 附录 addendum_mE1_s2027/(2026-09-05 17:4xZ; RESULT §10)
mE1 月折以种子 2027 重训(dl_monthly_wf 逐字月折训练器 + 一行种子白名单补丁, 4 分片, 15:08Z 配额事故后 resume 重启, 20/20 折)→ 拼接 → 拼行(spl27/spl42)→ 同装置回放 → `judge_gate_addendum.py`(冻结主窗 + 全窗)。pod 根 `/workspace/review_scratch/allweather_trackB/mwf_s2027/` + `…/replay/dev_alt/`; 数组 sha `addendum_mE1_s2027/POD_SHA256SUMS_arrays_and_devices.txt`; 归档文件 pod 端 sha `POD_SHA256SUMS_archived_files.txt`(63/63 相等)。
