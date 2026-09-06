# MANIFEST · cadence_seats_2026-09-05/axisA_incremental(king 增量重训两臂 KR 叶值 refit / KC 续训 vs K1 rollm60; PREREG_incremental_retrain_2026-09-06 §2)
> **创建:** 2026-09-06 03:5xZ | **Session:** b9646a9e / Track C agent | **预注册:** docs/PREREG_incremental_retrain_2026-09-06.md §2(commit a63fcc6, sha16 1463d7244c5b39db)| **结果文档:** docs/RESULT_king_incremental_2026-09-06.md | **pod 源目录:** pod2 /workspace/review_scratch/cadence_seats/axisA_incremental/(留 pod: models_KR/ models_KC/ 各 32 个 booster, slow_pred_KR.npy 879ab60b…, slow_pred_KC.npy ce24ce7f…, ic_KR.npz, ic_KC.npz, dev/ dev_alt/ 的 18 个回放 npz; sha 见 logs/chain_train.log 与 folds_*.json)

| 文件 | 内容 |
|---|---|
| train_incremental.py | 训练装置(sha256 37cd5881…): 数据准备与 K1 折规则逐字 = 轴 A pod_king_cadence.py D1; MODE=ident 恒等收据 / KR refit(decay 0.9) / KC 续训(+40 棵, init_model); 每折 train_rows==K1 断言; IC–年龄矩阵与相邻月一致性 |
| identity_receipt.json / logs/train_ident.log | 起点模型折 0 预测 == K1 逐位; KR decay 1.0 叶值 25,200 个逐位不变; KC 截断到继承树预测逐位 == 起点(0 轮被 lightgbm 4.7.0 拒绝, 如实记) |
| folds_KR.json / folds_KC.json / logs/train_KR.log / logs/train_KC.log | 每折收据(train_rows、IC vs K1、树数、字节、一致性、KR 叶值变化)、IC–年龄曲线、输出 sha、有限掩码 == pinned |
| consistency_k1.py / results/consistency_k1.json | K1 相邻月一致性(轴 A d1_pred_age1/age2; 含每折换种子) |
| setup_inc.sh / run_train.sh / chain_train.sh / run_arms_inc.sh | 布局(14 SAME + df/du/nproc/load)/ 单训练包装(12 线程)/ 恒等门控链 + 心跳 / 18 回放(3 并行 × 4 线程) |
| w10_universe_recheck.py | 轴 A 回放装置逐字节副本(5424aceb…) |
| check_equiv_inc.py / logs/check_equiv_inc.log | K1 重跑 6 格 vs 轴 A 归档逐位相等(ALL_EQUIV_INC True n 6) |
| judge_inc.py / results/judge_dyn.{json} results/tables_dyn.md / results/judge_fix.json results/tables_fix.md / logs/judge_{dyn,fix}.log | 冻结判官(轴 A judge_dyn/judge 改 ROOT/臂/配对 vs K1): 水平、配对 Δ、席位、判决; 日志首行单位链 |
| logs/commands.txt / logs/heartbeat.log / logs/setup_inc.log | 逐字命令(3 训练 + 18 回放, rc=0)/ 心跳(60 s, 训练 PID 存活)/ 资源与 sha |
| logs/*attempt1_segfault* / logs/heartbeat_attempt1.log | 首次启动段错误(Booster.reset_parameter)记录 |
| SHA256SUMS | 本目录全文件 sha(不含本文件与自身) |
