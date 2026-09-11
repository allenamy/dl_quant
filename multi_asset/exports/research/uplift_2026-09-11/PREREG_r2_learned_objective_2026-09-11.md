> **创建:** 2026-09-11 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 预注册, 数字之前落盘 | **作废条件:** GATE P 不逐位过; 或 v4 口径被推翻
> **口径:** 严格 v4 (CALIBER_PIN_v4_2026-09-11.md)。装置 = /workspace/uplift_2026-09-11/w10_sleeve.py sha256 b88e35a4…

# PREREG · Round 2 · Sleeve family = A DIFFERENT LEARNED OBJECTIVE (GPU)

## §1 机制假设 (mechanism first)
在役 DL 腿 V2MAIN 的损失(`pod_f10_train_ext.py` / `pod_f10_refit_v4.py` 逐字):
`u = cap(L1(demean(softrank(z))))`, `w_t = (1-α)w_{t-1} + α·u_t`,
`net_t = 1e4·(w_t·y4_t) − 3.52·|w_t − w_{t-1}|`, `loss = −mean(net) + 0.25·ES5(net)`,
其中秩在进 book 前先与**两条固定腿**混合: `r = wl0·r_DL + wl1·Z24 + wl2·ZFD`。

**它没有优化的东西(这是本轮的机制入口):**
1. **书里没有 king 腿。** 训练时的同伴腿是 rev24 + fund;**部署时的书是 king + fund(LEGS=101, PHI=0.45)**。
   ⇒ DL 腿从未对"king 已经吃掉了什么"取过梯度。这是一个真实的、可写下的目标缺口。
2. **没有 A0 书的既有仓位。** 它优化的是自己那本书的净额, 不是"在 A0 之上再加一笔"的增量净额。
3. **优化 mean − 0.25·ES5, 不优化 Sharpe**(方差不在损失里)。
4. 成本是**平的 3.52 bps**, 与流动性无关。

⇒ 本轮改的是**目标**, 不是数据: 把**冻结的 A0 书仓位 W_A0 放进损失**, 让梯度只看 A0 漏掉的部分
(boosting 第二级, 结构上与 A0 低相关), 以及把 Sharpe / 纯尾部 / 书自身实现误差分别当目标。

## §2 K 声明 (先于任何数字)
**K = 8**, 即本轮一共测 8 个"目标族"臂, 每臂产出一个分数矩阵 → 一条站立 sleeve:

| # | 臂 | 目标 |
|---|---|---|
| G1 | `PG_RIDGE` | 前置门: Ridge on 82 列, 目标 = 残差化收益秩 ỹ |
| G2 | `PG_LGBM` | 前置门: LGBM on 82 列, 同目标 |
| O1 | `RESID` | 可微书损失, 但 **w = W_A0(冻结) + λ·u_model**, loss = −mean(net)+0.25·ES5 |
| O2 | `RESID_ORTH` | O1 + 逐锚对**在役 fund 腿秩**的可微截面正交化(层, 不是事后) |
| O3 | `SHARPE` | 站立书, loss = −mean(net)/std(net)(直接打我们被评的量) |
| O4 | `CVAR` | 站立书, loss = ES5(net) 为主(0.1·−mean), 纯尾部目标 |
| O5 | `BOOKERR` | 目标 = 书自身实现误差 ỹ = y4 − β_i·W_A0(逐锚截面回归残差), 秩损失 |
| O6 | `RESID_SHARPE` | O1 的书 + O3 的损失(增量 Sharpe) |

Bonferroni 用 **K=8**。λ、符号、混合比例一律**不**当额外自由度: λ 固定 = 使 sleeve 的 L1 gross 等于 W_A0 行 L1 均值的 0.30;
分数符号固定为"分高=做多"; 不做事后翻号(若某臂反号为正, 记 REJECTED 并写明)。

## §3 走前验证协议 (walk-forward), 与在役 F10 逐字相同
逐年折 `YV ∈ {2023,2024,2025,2026}`, 训练集 = `yrs<YV 且 i < first_te − 60`(embargo 60 锚),
85/15 时序切 train/val, 15 epoch, argmax 早停(在役规则), AdamW lr 3e-4 wd 1e-4, cosine。
2022 无预测(与在役 F10 一致, 留 NaN)。**只用 v4 原生 `dlw_fea82`(82 列)** —— `f8_fea89` 属 `_ext` 谱系, FORBIDDEN。
种子: 筛选用 s42; **任何进入结论表的臂必须在 s2027 上复跑同一对照**。

## §4 判据 (冻结先于数字)
一条 sleeve 被 **ADMITTED** 必须全过:
- **S1 水平**: 站立全周期(2022-01-31→2026-08-31, n=10039 或 2022-01-01→2026-08-10, n=9918, 声明用哪个)
  `g = net_ex/gross_total` 均值 > 0 且**全周期 Sharpe ≥ 1.50**
- **S2 逐年**: 有预测的 4 年(2023-2026)全部同号为正
- **S3 相关**: `|corr(sleeve g 序列, A0 g 序列)|` 全周期 ≤ 0.25
- **S4 安慰剂×2**: (a) 逐锚打乱特征 → 重训/重打分; (b) 正交化算子作用在打乱秩上。两者 Sharpe 必须 ≤ 0
- **S5 carry**: `net_ex = pnl_ex − carry_ex − cost_ex` 恒等式成立, 且 **carry_ex/net_ex ≤ 0.40**
- **S6 泄漏**: 偏移谱 `corr(score_i, y4_{i+k})`, k=−2..+2, **峰在 k=0**; 且 k=−1 读数不得 > k=0
- **S7 Bonferroni(K=8)**: 全周期 g 的自举 BONF 区间排除 0
- **S8 双种子**: s42/s2027 同号且都过 S1
未过 S1 或 S3 ⇒ **REJECTED**(不移动目标)。过 S1/S3 但 S7 或 S8 失手 ⇒ **NEAR_MISS**。

## §5 装置与只读纪律
- GATE P: 六个 knob 全关时 `w10_sleeve.py` 必须**逐位**复现归档 `V4_A0_{dyn,fix}_s{42,2027}` 的
  `d30_n2_c42_rec` 与 `d30_n2_c42_W`。**不过就不测任何东西。**
- 站立 sleeve 臂 = `LEGS=001 PHI=0 FTRIM=off FEMAT_NPZ=<分数矩阵>`, 其余 env 逐字抄 `run_v4_arms.sh` COMMON。
- 只写 `/workspace/uplift_2026-09-11/r2_learned/`; v4 冻结工件零改动。
