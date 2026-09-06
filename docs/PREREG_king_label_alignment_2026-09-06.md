> **创建:** 2026-09-06 02:3xZ | **Session:** b9646a9e | **状态:** 预注册(判据冻结先于数字; 单变量; 研究仪器 = pod 第二仪器 king 管线; 实盘零接触; owner: track-a-newinfo 执行 / lead 判读) | **用户字:** 09-06 "king 换标签确认代码都没有问题可以推进测试" | **受据:** E-0905-J(面板/族门标签起点 E−5m, 早记账窗一根 bar); RESULT_f10_caliber_sensitivity(king 窗口项 −0.05 CI 含 0 = 现有 king 在记账窗上几乎不靠那根 bar); RESULT_trackA_newinfo(S1/S2 装置与恒等收据) | **作废条件:** 判据在看数字后被改; 任何数字无脚本收据; 触碰实盘文件或 bundle

# PREREG · king(LGBM)标签对齐: 训练目标从面板 y4(Σ ret5 行 [E, E+47], 起点 E−5m)换成记账窗目标(行 [E+1, E+48], 起点 E)

## 0. 事实与问题(VERIFIED 来源标注)
- 面板 meta y4 = Σ ret5 行 E..E+47, 行 E = 收盘于锚 E 的 5 分钟 bar ⇒ 目标从 E−5m 收盘起算, 与最后一根特征 bar(行 E−1, 收盘于 E−5m)同一价格时点(`build_y4_alt.py` FACT 段; E-0905-J)。记账口径 = Π(1+r)−1 行 [E+1, E+48](`pod_dlw_targets_ext.py` L93 y4s), 起点 = E 收盘; 实盘换手在 N+23(N+6 换装后为 N+6)之后才发生。
- 在役 king booster 由 bundle 管线训练, 目标 = 面板 y4(同一谱系)。第二仪器 king 管线(`trackA_gate_s1.py`: LGBM 400 树 / lr .05 / 63 叶 / subsample .8 / colsample .8, 目标 = 锚内成员的 y4 秩, 折 = 测试年 2024/2025/2026, 训 < 测试年, 78 面板列)已带 `Y4_ALT` 入口: 设置后 **训练目标矩阵整体替换**(L38–41, 在秩目标构造之前), 现成 `features/y4_startE.npz` = Σ ret5 行 E+1..E+48。
- 已知量级: 现有 king 预测在记账窗 vs 面板窗的书层差 −0.05 bps/锚/gross(CI 含 0)⇒ 预期本次改动效应小; 因此判读是**非劣 + 可执行窗不差**, 不是"必须更好"。

## 1. 臂(锁死; 只换目标, 其余逐字节同)
- **BASE**: 现行, 目标 = 面板 y4(已有 `results/preds/pred_BASE_s{42,2027}.npy` 与 S2 回放工件)。
- **ALT_SUM**(主臂): `Y4_ALT=features/y4_startE.npz`(Σ ret5 行 E+1..E+48; 对秩目标而言与 Π 形式几乎同)。
- **ALT_ACC**(副臂): 目标 = Π(1+r)−1 行 E+1..E+48(meta_newprod y4 谱系; 由 `build_y4_alt.py` 同法导出 npz), 只报, 不单独判。
- 种子 42 / 2027; NJOBS/OMP 线程数固定并写进 config。

## 2. 代码核对(先于任何数字; 全部落收据 `results/code_check.json`)
1. **恒等**: 不设 Y4_ALT 复跑 BASE 一次(同种子同线程数), 预测数组与 `pred_BASE_s42.npy` 逐位相同(sha 相等); 不相同则先查线程/版本, 不得进入臂。
2. **标签收据**: 随机 ≥1000 个 (锚, 名) 格, y4_startE 值 = 用 5m cache 重算的 Σ ret5[E+1..E+48](max|Δ| ≤ 1e-6); ALT_ACC 值 = Π(1+r)−1 同行(max|Δ| ≤ 1e-6); 起点行 = 收盘于 E+5m 的 bar(E_ts 断言)。
3. **因果**: 特征最右 bar 收盘 ≤ E−300 s(装置断言, 与 RESULT_trackA §时移 同); 目标最左 bar 开盘 = E。
4. **折/禁运**: 训 < 测试年逐字; 标签末端 = E+4h 不跨年边界泄入(断言 max label end < 测试年首锚)。

## 3. 读数与装置
- 分数层(`trackA_gate_s1.py` 输出 + `horizon_profile.py`): 每折 rank-IC 对三种目标(面板 y4 / y4_startE / 可执行窗 meta_exec25 = 行 E+6..E+48)各一; 视界谱 n1/n3/n12/n48/exec。
- 书层(`s2_chain.sh` 同形态, RULE=s2 装置 `s2_paired_delta.py`; w10_health_spotsup.py SPOTSUP_B=0 ≡ w10_health.py, 体检主臂形态 U-PIT·m1·FTRIM·动态席位·实盘费率·记账口径 dev_alt): ALT − BASE 同种子配对 Δ 每 gross, 2024→26 主判, 逐年 2024/2025/2026≤cut 辅, UTC 日块 bootstrap 2000 种子 20260905; 换手变化; 席位轨迹(2026-08-10 席位)。

## 4. 冻结读法
- **(A) 采纳候选(非劣且可执行窗不差)**: 双种子 Δ_book(2024→26)点估计 ≥ −0.02 且 CI95 下界 > −0.05; 双种子可执行窗 IC Δ ≥ 0; 换手 ≤ +10%。
- **(B) 否决**: 任一种子 Δ_book CI95 上界 < 0, 或任一种子可执行窗 IC Δ CI95 上界 < 0。
- **(C) UNDECIDED**: 其余。
- 比较家族: 主臂 1(ALT_SUM)× 2 种子; ALT_ACC 只报。
- **部署含义(先写后看)**: (A) ⇒ 立部署预注册: bundle 管线 king 目标改为记账窗(RUNBOOK 改动; booster IC 门 |Δ| ≤ 0.006 需按新目标重设基线), 换 bundle 须同法播种席位(seat_seed_v3 教训), 需用户字; (B) ⇒ 面板目标保留, E-0905-J 规则只约束族门; (C) ⇒ 报用户, 不动。任何情况实盘不动。

## 5. 归档
`multi_asset/exports/research/allweather_2026-09-05/trackA/label_alignment/`(code_check.json、preds sha、S1/S2 结果 json、logs/commands.txt 逐字、SHA256SUMS、MANIFEST 段); RESULT = `docs/RESULT_king_label_alignment_2026-09-06.md`。CPU 任务(LightGBM), 与 GPU 早停臂并行无冲突; 线程数 ≤ 24。
