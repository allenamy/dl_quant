# MANIFEST — allweather_2026-09-05/trackB (PREREG_allweather_programme_2026-09-05 §3 Track B, sha256 8a02895c…, commit 5075b36)

> **创建:** 2026-09-05 19:0xZ(归档; 计算 pod2 14:37:11Z–18:52:08Z; 判官 JUDGE_DONE 18:5xZ)| **Session:** b9646a9e, teammate Track B | **状态:** 归档 final; pod 原件只读 | **作废条件:** pod 原件任一 sha 与 `POD_SHA256SUMS_*.txt` 不符

pod2 root: `/workspace/review_scratch/allweather_trackB/`(fits `f8_out/`, 回放 `replay/dev_alt/`, 结果 `results/`, 月折附录 `mwf_s2027/` → 归档在 `retrain_2026-09/dl_monthly_gate_2026-09-05/addendum_mE1_s2027/`)。本目录 = 全部脚本 / 结果 json+md / fit 自报 json / 日志 / 回放日志与摘要 的逐字节拷贝(`SHA256SUMS` = 本地; `POD_SHA256SUMS_archived_files.txt` = pod 端, **123/123 相等**)。数组只留 pod 路径 + sha256(`POD_SHA256SUMS_arrays_and_devices.txt`: 8 个 fit 预测 + 2 个事故部分文件 + 9 个回放输入 + 13 个回放工件 + 4 个年折基线 + 训练器/装置)。

## 1. 目录内容
| 路径 | 作用 |
|---|---|
| `scripts/pod_f10_train_ext.py` | 逐字训练器副本(sha `93cc2cdf…` = `/workspace/pod_f10_train_ext.py`) |
| `scripts/pod_f10_train_dro.py` / `pod_f10_train_dro.rebuilt.py` / `make_patch.py` / `patch.diff` | 补丁训练器(sha `d5df2f1c…`; pod 上从在役原件重建 `cmp` 相等)、生成器(精确串替换, 锚点恰一次断言)、diff(110 行, +34/−6) |
| `scripts/launch_train.sh` | 单 fit 启动(CMD/PID/END rc/wall 逐字入 `logs/commands.txt`; F10_OUT=f8_out, data → /workspace/f8_ext/data 符号链接) |
| `scripts/setup_replay.sh` / `run_arm.sh` / `w10_health.py` / `check_equiv.py` | 回放布局(= health_check dev_alt, prod 口径)+ 等价收据 |
| `scripts/stage_preds.py` / `run_replay_arms.sh` | ext 网格 → 0822 网格(前 nB 行, 前缀断言)+ 回放批 |
| `scripts/identity_check.py` / `leakcheck_yearly.py` / `score_trackB.py` / `judge_trackB.py` / `build_result_trackB_doc.py` | 恒等断言 / 泄漏门 / 分数层 / 冻结判官 / RESULT 补充表 |
| `scripts/check_shard_artifacts.py` / `pull_trackB_archive.sh` | 事故后产物完整性检查 / 归档拉取 |
| `fits/f10_V2MAIN_{IDENT,B1,B2,B3}_s{42,2027}.json` | 训练器自报(config/输入 sha/逐折指标/DRO 逐 epoch 权重) |
| `results/` | `judge_trackB.json` · `trackB_tables.md`(表 L/D/J)· `score_trackB.json` · `identity_check.json` · `leakcheck_IDENT_s42_B1_s42.json` · `leakcheck_B2_s42_B3_s42.json` · `leakcheck_B1_s2027_B2_s2027_B3_s2027.json` |
| `trackB_supp_tables.md` | 表 S1–S5(由 `build_result_trackB_doc.py` 从归档 json 打印; 日志 `logs/build_result_trackB_doc.log`) |
| `logs/` | `commands.txt`(清洗版; `commands.txt.raw_20260905T1640` 原始含 NUL)· `train_*.log`(8 fit + 事故前 `partial_20260905T1508/*.part1`)· `identity_check.log` · `leakcheck_*.log` · `score_*.log` · `judge_trackB*.log` · `stage.log` · `patch_sha256.txt` · `launch_*.out` |
| `replay/logs/` · `replay/dev_alt/logs/` · `replay/dev_alt/probe_summary/` | 回放命令逐字(16 臂 env 全文)、每臂 .out/.log、摘要 json、`setup_sha256.txt`、`check_equiv.log`(EQ1/EQ2 PASS) |
| `part0_verify/` | Part 0 判官复跑收据(dl_monthly_gate) |

## 2. 关键 sha256(pod 端, `POD_SHA256SUMS_arrays_and_devices.txt` 全文归档)
- fit 预测(ext 网格 10206×829): IDENT_s42 `42666fc75aa68b44…`(= `/workspace/f8_ext/preds/f10_V2MAIN_s42.npy`, 恒等), B1_s42 `3b0191ac5f18a085…`, B2_s42 `7f1581b47b9cb317…`, B3_s42 `ea07fdfcbe5b8e82…`, B1_s2027 `b1b92677b46ba871…`, B2_s2027 `26eb973b0b900f8b…`, B3_s2027 `af6ab178b19b89c2…`。
- 年折基线: ext `f8_ext/preds/f10_V2MAIN_s42.npy` `42666fc7…` / `_s2027` `57c3625c…`; 装置默认 0822 `f8_2026-08-22/preds/f10_V2MAIN_s42.npy` `baf747ce…` / `_s2027` `c742ffaa…`。
- 装置: `w10_health.py` `8684d9a9f43a8d15…`; 掩码 `ccb7a080…`; 费率 `9349ca63…`; pinned king `158cd4ac…`(`replay/logs/setup_sha256.txt`)。

## 3. 事故记录
2026-09-05 15:08–15:10Z /workspace 配额顶: B2_s42 / B3_s42(2025 折 ep9–10)与 4 个 mE1 s2027 分片被杀, 无 traceback、无 END 行; 16:36Z 相同命令重跑(B2/B3 从头; 逐折指标与被杀运行逐位同), 部分文件隔离在 `f8_out/partial_20260905T1508/`(pod)与 `logs/partial_20260905T1508/`; B1/B2 s2027 曾以 SIGSTOP 暂停(14:50:12Z)并于 17:31:41Z SIGCONT(记录在 commands.txt)。

## 4. 复跑(逐字, 见 `logs/commands.txt` CMD 行)
`bash launch_train.sh IDENT 42 inf 0` · `B1 42 0.5 0` · `B2 42 inf 1.0` · `B3 42 0.5 1.0` · 同 SEED=2027 → `python identity_check.py` → `bash run_replay_arms.sh IDENT:42 B1:42 B2:42 B3:42 B1:2027 B2:2027 B3:2027` → `python leakcheck_yearly.py …` → `python score_trackB.py B1:42 B2:42 B3:42 B1:2027 B2:2027 B3:2027` → `python judge_trackB.py`。
