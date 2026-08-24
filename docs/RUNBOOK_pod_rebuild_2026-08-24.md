> **创建:** 2026-08-24 | **Session:** 6737834a | **状态:** 现势盘点+复现手册 | **作废条件:** 新 pod 实际重建后以其验收记录为准

# RUNBOOK · Pod 报废盘点与新 pod 快速复现

## §1 直答: 能否快速复现 —— **能, 而且当前运营根本不依赖 pod**
过去 72 小时的全部工作(F-4→F-10 全战役、部署工件、影子工程、数据扩军)是**零 pod** 完成的: 训练在 jpline 3090, 实时在 Mac 影子, 实盘在本机。新开 pod 属**可选加速**(更大 GPU 跑 V3 级/更长史训练), 不是恢复依赖。

## §2 三处镜像盘点(2026-08-24 实测)
| 资产 | 位置 | 状态 |
|---|---|---|
| **pod 全部代码**(300 文件含 BOOTSTRAP.sh/champion_run/训练与判官全套) | 本仓 `runpod_scripts/workspace_mirror/` | ✓ 完整 |
| 5m 宽缓存(829 币) | jpline `dlnative_5m_wide829_f16.npz` + **fresh 拼接版到 08-24**(影子回灌管线, 可持续) | ✓ 且更新 |
| fea82/fea89/targets/legs/171 管线 | jpline dlw/f8 目录 + 本仓 devices 镜像 | ✓ |
| king booster + 影子 bundle(含 MANIFEST/状态种子) | Mac `~/wide_shadow/shadow_bundle/` | ✓ 自足 |
| F-10 部署工件(双种子 pt + numpy 权重) | jpline models/ + Mac fea171/ | ✓ |
| 历史臂 nets/止损判官产物 | jpline `pod_backup_2026-08-21`(568M)+ `pod_archive_2026-08-15` | ✓ |
| 判据/预注册/RESULT 全部文档 | 本仓 docs/ + eda/(SHA 链) | ✓ |

## §3 永久损失清单(如实)
1. **2020–2021 年 5m 原始史**(pod 独有; share bar_1s 起点 2022-01)⇒ 2020 起全史回测不可再生 —— **结论无损**(受据文档+当年 nets 序列在 pod_backup), 但不能出新臂; 未来若需, data.binance.vision 可按币重下(免费, ~2 天工程)。
2. pod 卷上未导出的中间 scratch(无已知承重物 —— 承重产物均经 shadow_bundle/backup 导出)。
3. wide_fea_v2ext 1.6G 特征矩阵原件 ⇒ **可再生**(dlw_features 即其逐字移植, 对新缓存重跑即可)。

## §4 新 pod 复现手册(估时 ~2-3 小时 + 数据传输)
1. 起容器(CUDA 12.x + PyTorch) → `rsync workspace_mirror/ pod:/workspace/` → `bash /workspace/BOOTSTRAP.sh`(钥匙+科学栈+体检, 脚本在镜像内);
2. 数据回种(按需): jpline → pod rsync `dlnative_*_fresh.npz`(~1.5G)+ dlw/f8 data 目录(~8G)——只在跑大训练时需要;
3. 验收 = champion_run.sh 复现基线(0.0475/0.067 双种子, memory `champion_baseline_repro` 配方)+ 任一 RESULT 判官重放对表;
4. 纪律不变: 判官脚本当日入库(判决装置与结论同寿命 —— y24 遗失装置的教训正是 pod 单副本机器)。

## §5 决策建议
当前队列 jpline 足够(单卡串行是节奏瓶颈非能力瓶颈)。**值得开新 pod 的触发条件**: V3 级多臂并行需求 / 2020-21 史重下后的全史重训 / L3 快模型上 400 币全宇宙。触发前不必花这笔钱。
