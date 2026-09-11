> **创建:** 2026-09-12 | **Session:** session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 冻结, 写在本轮任何新数字之前 | **作废条件:** 轴/成本/装置 sha 与 §2 不符

# PREREG · r10 screen · SLOW_CLOCK_SECOND_BOOK

## §0 候选是什么
把 `r2_horizon` 已归档的 horizon 臂**当作自带 gross 的独立书**(装置 `w10_sleeve.py`
`LEGS=001 PHI=0 FTRIM=off` 本来就是这个形态: `g = net_ex/gross_total` 已经是"每单位自己的 gross"),
在**书层**与 A0 合并。不重新推导信号, 只复用归档臂。

## §1 污染声明(必须写在最前)
我在冻结本规则之前**已经读过** `r2_horizon/RESULT_abcd.json` 与 `r9_horizon/REOPEN_CHECK_r9.json`,
因此**已经看过这 38 条臂的 Sharpe**。所以"事前只看 rho"这句话对我**不成立**。
处置 = 同时做 (a) 与 (b), 并且把 (a) 做成**不可能挑赢家**的形式:

- **(a) 只按 rho 选, 且选中就全要。** 不取"低 rho 里 Sharpe 最高的那条", 取**全部**合格臂的等权组合。
  等权组合的读数不随我事后知道哪条 Sharpe 高而变化 ⇒ 挑选自由度 = 0。
- **(b) 留出期。** 号(±)这一个自由度用 TRAIN 拟合, 主判在 HOLDOUT。

**仍然无法消除的污染, 明写**: 这 19 个基础特征本身是 r2_horizon 的调研者在看过读数后选/扩的
(该轮 AMENDMENT 2/3 明说是"基于已看到的东西扩展候选集")。任何本轮的留出期都在**同一个样本**里,
所以留出期控制的是我的号/成员选择, **控制不了特征集的选择**。这条必须跟数字一起引用。

## §2 轴 / 口径 / 成本(逐字, 冻结)
- 统计 `g = net_ex / gross_total`, bps / 4h 锚 / 单位 gross。
- 轴: 装置 rec 全长 10039 锚(2022-01-31 00Z .. 2026-08-31 00Z) → **丢前 900**(E-0911-A) → `ts <= 2026-08-30 20Z`(E-0911-D) ⇒ **n = 9138**。
  (已实测: A0 与 r2_horizon 臂的 `ts` 向量**逐位相同**, 见 RECEIPT `axis`。)
- 自举: UTC 日块, **2000** 次, `numpy.default_rng([20260905, k])`。
- SE(年化 Sharpe) = `sqrt(2190/n)`。
- 成本: 主报 **`r3k_impact/costb_PWR_G230k.json`** sha256 `295b4e7b4623...`(K 档 G=$230k, POWER book-walk),
  由**重跑装置**得到, 不用比例外推。对照报归档的 `costb_fee_steady`(部署档, book_avg 2.0673 bps/单位换手)。
- 装置: `/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 `b88e35a46b93d712...`(与 r2_horizon GATE P 同一条), **不改一行**。

## §3 候选池(冻结)
`RESULT_abcd.json` 的 40 个键里去掉 2 条安慰剂 `PL_ORTHPERM__{p,m}` ⇒ **19 个基础特征 × ±2 号 = 38 臂**:
A_{AMI1H,CPOS1H,QVS1H,REV1H,TBF1H,VOL1H} · B_{AMI12H,REV12H,TBF12H} ·
C_{AMI3D,AMI7D,QVTR3D,TBF3D,TBF7D,TBF14D,TBF30D} · D_{FCHG12H,FCHG3D,FSLOPE}。
(r9 说的"40 臂"含 2 条安慰剂 ⇒ 本轮按 38 计。A3_* 的 MA 持有变体在 `out/` 里但不在该 JSON 的候选集内,
只作补充诊断, 不入池。)

## §4 选择规则 S(冻结, 先于任何新 Sharpe)
1. TRAIN = 后暖轴 ∩ `ts <= 2024-12-31 20Z`; HOLDOUT = 后暖轴 ∩ `2025-01-01 00Z <= ts <= 2026-08-30 20Z`。
2. 对每个**基础特征** f, 算 `rho_train(f) = corr(g_{f__p}, g_A0)` 在 TRAIN 上(±两号的 |rho| 相同)。
3. **录取集 Q = { f : |rho_train(f)| <= 0.10 }**。只用 rho, 不看 Sharpe, 不看 g。
4. 号: 特征 f 取 `__p` 若 `mean(g_{f__p})` 在 **TRAIN** 上为正, 否则取 `__m`。只用 TRAIN。
5. **SLOW_CLOCK 书 = Q 中全部签名臂的等 gross 平均**(书层合并, 每本自付自己的成本)。
   等权 = 每本一份 gross; 组合的 g 序列 = 各臂 g 序列的算术平均; 组合换手 = 各臂换手的算术平均。
6. 另报**纯 rho 单条**: `argmin_f |rho_train(f)|` 的签名臂(选择输入里完全没有 Sharpe)。
7. 另报**污染对照**(明确标 CONTAMINATED): 低 rho 里 Sharpe 最高的那条。它**不是**本轮结论。

## §5 判据(冻结, 先于数字)
- **G1 独立性**(主筛): 全轴 `|rho(SLOW_CLOCK, A0)| <= 0.30`, 且 **A0 最差五分位锚上的条件 rho 同样 <= 0.30**。
  条件 rho 超 0.30 ⇒ 与 Amihud sleeve 同一形态, 判 **NOT A DIVERSIFIER**。
- **G2 净额**: HOLDOUT 上 `mean g > 0` 且 CI95 下界 > 0, 在 **PWR_G230k** 成本下。
- **G3 零假设**: 超过 6 条换手匹配 null(SHIFT101/503/1009 + RELAB1/2/3)的最大值。
  **不使用逐锚置换安慰剂**(已知有缺陷)。
- **G4 前视**: 偏移谱 `corr(signal_rank@i, y4@i+k)` 峰在 k=0 且 `IC(k=0) >= IC(k=-1)`。
  这是 r2_horizon §5 的 S5, **本轮沿用, 不豁免**。
- **G5 下行**: 组合书(A0 + SLOW_CLOCK 在合理配比)的**最差 UTC 日**不得比 A0 更差, maxDD 不得更深。
- **ALIVE** = G1..G5 全过且 §6 算术有意义; 任何一条硬失 ⇒ **DEAD**。

## §6 目标算术(冻结公式)
`SE = sqrt(2190/9138) = 0.4895`。CI95 下界 > 3.0 需要点估计 `3.0 + 1.96*SE = 3.9595`(简报写 3.966, 用简报值报距离)。
两本书 w / (1-w): `SR_c = (w*mu1 + (1-w)*mu2) / sqrt(w^2 s1^2 + (1-w)^2 s2^2 + 2 w(1-w) rho s1 s2)`,
mu/s 用同一轴上的逐锚 g 的均值/标准差, 年化因子 sqrt(2190) 对分子分母同样施加 ⇒ 直接用年化 Sharpe 合成。

## §7 ENV 白名单(E-0826-D)
本轮全部脚本断言**以下变量不在 os.environ**:
`CAL, LEGS, PHI, FTRIM, WRULE, LOOK, MEMBERS_TOPN, UMASK_SCOPE, UMASK_NPZ, COSTB_JSON, SLOW_NPY,
FSEED, FPRED, FEMAT_NPZ, OUT_TAG, EXPORT_PANEL, EMA_STATE_JSON, PANEL_IN, JUDGE_HC, TILT, TILT_TAU, TILT_K`。
装置调用时这些**逐个显式传**在 `env` 前缀里, 且**写进产物**(`config_json` 回读比对)。
线程: `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=3`。
