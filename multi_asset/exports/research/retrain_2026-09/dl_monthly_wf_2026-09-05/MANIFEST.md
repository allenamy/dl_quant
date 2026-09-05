# dl_monthly_wf_2026-09-05 · MANIFEST(pod2 `/workspace/review_scratch/dl_monthly_wf/`; 大件不入 git, 只登记路径 + sha256)

> **创建:** 2026-09-05 09:47Z(FINAL DONE 收据 `logs/commands.txt`)| **Session:** b9646a9e, teammate `dl-monthly-wf` | 全部 sha256 由 pod 上 `final_chain.sh` 的 `sha256sum` 写入 `SHA256SUMS.txt`(本目录副本 `POD_SHA256SUMS_all_artifacts.txt`, 含 40 个折模型 .pt / 40 个折预测 .npz / 40 个折 config)。

## 大件(pod 路径, 不入 git)

| 文件(pod `/workspace/review_scratch/dl_monthly_wf/`) | 内容 | sha256 |
|---|---|---|
| `preds/f10_V2MAIN_mE60_s42.npy` | 月折拼接预测, ext 网格 (10206×829), 截止 −60 锚, 2025-01-01 前 NaN | `2c6e9756feabd0447e79fc93eaf65e0a14967eb1b3072789b48e37b6e60915cf` |
| `preds/f10_V2MAIN_mE1_s42.npy` | 同上, 截止 −1 锚 | `54bd748d2f1553774ebb5a72de61e417cbac9b7298f4e47775dbd546464b6bb0` |
| `replay/dev_alt/f8_2026-08-22/preds/f10_V2MAIN_mE60_s42.npy` | 0822 网格投影(前 10086 行), pure | `4d354bf2eac84b9121234d9a229008084d8ffb20aef5b72c69d0130caee52085` |
| `replay/dev_alt/f8_2026-08-22/preds/f10_V2MAIN_mE60spl_s42.npy` | 0822 网格, spliced(2025-01-01 前 = 年折文件) | `2970948dc90e76e113bce2ad7285b2474c61d79bcff90de93674d5f21982c39e` |
| `replay/dev_alt/f8_2026-08-22/preds/f10_V2MAIN_mE1_s42.npy` | 0822 网格, pure | `2ad9b6ea3071590bf3d4a3bc458828942192a80e38b4613ec7747fd8378a05af` |
| `replay/dev_alt/f8_2026-08-22/preds/f10_V2MAIN_mE1spl_s42.npy` | 0822 网格, spliced | `7ae3f8227077d5b958b7a62345c7de91903d4b8cb5d6df0c6e8c272d003e5ae2` |
| `replay/dev_alt/f8_2026-08-22/preds/f10_V2MAIN_s42.npy` → `/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy` | 年折基线文件(symlink) | `baf747ceb31f10d614ffac79b9c969c499e1c3e9f82edfec246d7cfb0f353ace` |
| `replay/dev_alt/probe_artifacts/w10_ablation_series_BASE_M1_UPIT_prod_s42_ccal.npz` | 基线臂(= health_check `M1_UPIT_prod_s42_ccal` 逐位) | `32bfecb9cf9c0e5caebd4d77ad3ee5cf8334be3e75bf04b2cd66cb8550d9d12a` |
| `replay/dev_alt/probe_artifacts/w10_ablation_series_M1_mE60spl_prod_s42_ccal.npz` | 主臂 mE60(spliced) | `7037b8ab81833c204181e1bcf70f0530ab37684fb3fd1146de510e9b512f6ffe` |
| `replay/dev_alt/probe_artifacts/w10_ablation_series_M1_mE60pure_prod_s42_ccal.npz` | 敏感臂 mE60(pure) | `5e433f7bdd664dd1758cccbe470559821cd2c63c1f2147d2c25346bc08a032b2` |
| `replay/dev_alt/probe_artifacts/w10_ablation_series_M1_mE1spl_prod_s42_ccal.npz` | 主臂 mE1(spliced) | `ef4d5265fbde60461c8b523a3e7384d54c8c5dae9cf12b207cdcecd3ab6d21de` |
| `replay/dev_alt/probe_artifacts/w10_ablation_series_M1_mE1pure_prod_s42_ccal.npz` | 敏感臂 mE1(pure) | `44ae27bb684eb793c79c4c64999b01302f8027129f0dbc25ae7ca9d14daa3b75` |
| `replay/dev_alt/probe_artifacts/w10_ablation_series_PHI1_BASE_prod_s42_ccal.npz` | 辅臂 PHI=1.0 基线(F10 书单独) | `bfc27a250f81d1a6bfa2057ef194530a03d2d9a6a87aeea02a4bf5a93d2b982a` |
| `replay/dev_alt/probe_artifacts/w10_ablation_series_PHI1_mE60spl_prod_s42_ccal.npz` | 辅臂 PHI=1.0 mE60 | `529c1ec9b3f074048d172fa57d8d8e43ad6a6ccad75499bbf1a4d58e642192ca` |
| `replay/dev_alt/probe_artifacts/w10_ablation_series_PHI1_mE1spl_prod_s42_ccal.npz` | 辅臂 PHI=1.0 mE1 | `c8e16f2e984be425f7bcc4c0a4cb874df5ba27126c2dc6472a90c5c758806090` |
| `models/mE{60,1}_{202501..202608}.pt`(40 件, 19 MB) | 每折模型 state_dict | 见 `POD_SHA256SUMS_all_artifacts.txt` |
| `preds_fold/mE{60,1}_{202501..202608}.npz`(40 件, 132 MB) | 每折模型对 ≥ first_te 全部锚的原始分数(模型年龄曲线输入) | 见 `POD_SHA256SUMS_all_artifacts.txt` |
| `replay_check/`(47 MB) | RNG 复现收据: E60 2025-01 折在新进程重训, 分数/权重与 07:27Z 原件逐位相等(`logs/replay_check_compare.log`) | `preds_fold/mE60_202501.npz` 原件/复跑 sha 前 16 位均 `050552b66db36188` |

## 输入(只读, sha256)

| 输入 | sha256 |
|---|---|
| `/workspace/pod_f10_train_ext.py`(逐字训练器, 本装置前 260 行逐字节同) | `93cc2cdf925a1dada9190a5d86664d28c811d9ba0ecf3eaf377d54fc554f2598` |
| `/workspace/dlw_ext/data/dlw_targets.npz` | `31d043e8f160a1d4475d5992a069c4b602419d78c7916f710d1e56ae8915caf9` |
| `/workspace/dlw_ext/data/dlw_fea82.npz` | `9bc111a47cee54fc26193165258a83eb11f59df79bebcd69452532bb4c59678e` |
| `/workspace/f8_ext/data/f8_fea89.npz` | `bebf2720315499707e54b53c26d889cbf6f2d2d3184a42455284636c0c5e4d67` |
| `/workspace/f8_ext/data/f10v2_legs.npz` | `facf53f7355da98fa2b92d95e0989882fb33523ce0237bcd1d6af77641a8e416` |
| `/workspace/review_scratch/health_check/w10_health.py`(回放装置, 逐位复制) | `8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d` |
| `/workspace/review_scratch/health_check/masks/umask_UPIT.npz` | `ccb7a0805be2a106898467b5ffef3a8fd4813a659e044492c0a437b0e5d7aece` |
| `/workspace/review_scratch/health_check/calib/costb_fee_steady.json` | `9349ca634747772dcfc9adfb7a42a5c7b5b34f60bc7f31bc6fd95c4ae5d0fc42` |
| `/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz`(prod 口径 meta) | `831857dd6a2035235647158d26d0155d17c7e77d85fa248b2ae9a617658ddf13` |
| `/workspace/shadow_bundle_v3/slow_pred_pinned.npy`(pinned king) | `158cd4ac8f8f30f7f41a5a6cba0bd19a450ce756727e4aeae3d4e4b0b67d0054` |
| `/workspace/data/dlw_targets.npz`(0822 网格) | `dd4ed2dfb5fa426f8b8f49c0a20f39bcf077280025ed03ebb19b2ece66fc68a3` |

## 本目录(git)

脚本: `pod_f10_train_monthly.py`(sha `7bb39f8d93f2daf749535f8a6d91aecd15e8e3361de80138a29c6fbb6270b51e`)= 逐字训练器前 260 行 + `monthly_section.py`; `trainer.diff`; `stitch.py` `ic_monthly.py` `leakcheck_monthly.py` `judge_dl.py` `render_report.py` `verify_artifacts.py`; 启动/链: `run_train.sh` `run_train_E1.sh` `run_train_E60_tail.sh` `launch_variant.sh` `setup_replay.sh` `run_replay.sh` `replay_check.sh` `final_chain.sh` `status.sh`。
收据: `REPORT_tables.md`(T1–T9); `results/`(两变体折表 json); `replay_results/judge_dl.json`; `logs/`(ic/leakcheck json, judge/leakcheck/ic/verify/stitch 终版日志, `commands.txt` 全程命令与事故记录, `replay_check_compare.log`); `replay_logs/`(装置命令、等价收据); `fold_configs/`(40 折 config)。`SHA256SUMS` = 本目录全部文件。
