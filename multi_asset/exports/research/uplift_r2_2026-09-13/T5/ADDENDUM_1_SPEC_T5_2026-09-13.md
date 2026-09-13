> **创建:** 2026-09-13 ~07:23Z | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T5) | **状态:** 结果后追加的描述性读数规格, 冻结先于本附录任何数字(sha 记 `receipts/PREREG_FREEZE_sha.txt`) | **作废条件:** 同主预注册; T4 的 `K1_v4axis.npy` 被替换
> **地位:** **不是预注册判据。** 主预注册 §4.4 的 K 组纳入规则要求「窗内 30 锚的实盘服务 king 预测(booster 29ffaf58)v1/v0 两版且 T4 实盘平价门 PASS」; 主运行时该条件不满足(T4 的实盘平价窗是 09-05 16Z..09-12 08Z, 用 booster 8d79186b), 故主表 (e) = NOT MEASURED, 一字不改。本附录用 T4 已产出的**回放模型**变体给 (e) 一个代理读数。
> **写本规格前已看过的 T5 数字(申报):** 主运行全部结果(`receipts/pod2/RECEIPT_T5_bridge.json`), 含 REM 均值 −0.011(s42)/ −0.013(s2027)与 B_N 对 D 的权重相关 0.999; T4 `RECEIPT_T4_kings.json`(GATE AL/K26/KF 全过)与 `RECEIPT_T4_judge.json` 判词 NOT MATERIAL。

# ADDENDUM 1 规格 · H2b 的 carry 代理(回放 king 模型, 第 80 列 v0 → v1)

- **输入**: T4 `kings/K0_v4axis.npy`(sha `64767318…9009`, = 回放所用 `SLOW_v3_on_v4axis.npy`)与 `kings/K1_v4axis.npy`(同一批 booster, 第 80 列喂 v1)。门 **G-A1**: 窗内 31 行 K0 与 T5 装置 dump 的 SLOW 行逐位相等(NaN 同位)。
- **估计量**: 在主桥的全部 1024 个节点 S(10 组)上各跑一次「king 分数 = K1」: `Δ_K1(S)(A) = v(S; K1)(A) − v(S; K0)(A)`。报告: (i) 全 R 节点 `Δ_K1(∅)`; (ii) 全 D 节点 `Δ_K1(G)`; (iii) 把 K1 当第 11 组的 Shapley 值 `φ_K1 = Σ_S |S|!(10−|S|)!/11! · Δ_K1(S)`; 各自 A_T5 均值、占主表 Δ 的比例, 日块 CI 用 `default_rng([20260905, 58])`; 两个种子。
- **读法(描述)**: |φ_K1 占比| ≤ 0.05 ⇒「H2b 对本窗建模 carry 差的代理贡献可忽略」; ≥ 0.20 ⇒「不可忽略」; 其余「小」。**限定**: 这是回放 king 模型(2026 年 = 8d79186b)在 v1 馈入下的变化, 不是窗内实际服务的 29ffaf58; 不能替代主表 (e)。
- 装置 `devices/t5_addendum_h2b.py`(pod2): 按语法树从 `t5_bridge.py`(sha 断言)逐字取出 `xz` 与 `simulate`, 数据装载与主桥相同; 收据 `receipts/pod2/RECEIPT_T5_addendum1_h2b.json`。
