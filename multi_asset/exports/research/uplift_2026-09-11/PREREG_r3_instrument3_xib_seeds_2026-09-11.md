> **创建:** 2026-09-11 | **Session:** b9646a9e (round 3, INSTRUMENT 3) | **状态:** 预注册 — 冻结于任何新数字之前 | **作废条件:** 判据被用户裁定改写, 或 v4 口径被换掉

# PREREG — INSTRUMENT 3: settle XIB_LAG50 with more seeds

## 0. Why this exists
XIB_LAG50 是 (C) UNDECIDED: 在预注册的 frozen window 上 dyn 席位 s42 配对差 **+0.4698 [+0.0586,+0.8467]**,
s2027 **+0.3932 [−0.0151,+0.7744]** —— 下界差 0.015 bps/锚。两颗种子回答不了"这是噪声还是信号"。
本预注册在看任何新数字之前冻结: 种子集 / 配对规则 / 窗 / 统计量 / 判决规则(以计数表述)。

## 1. What "seed" is in this device (读码所得, 不是推断)
`w10_sleeve.py` 的 `FSEED`/`FPRED` 只喂 **F10(DL, V2MAIN)腿**: `PHI=0.45` ⇒ king 链 = 0.55·king + 0.45·F10。
fund 腿(= XIB_LAG50 唯一改动的对象)**不含种子**。种子因此通过两条通道进入配对差:
(a) msharpe 席位权重 w3(LOOK=900 的腿收益窗, 三腿联立), (b) 书层 gross 归一。
⇒ 配对差对种子的敏感性是**席位层交互**, 不是信号本身的随机性。这一点在解释结果时必须带着。

## 2. Seed set (FROZEN, N = 6)
| seed | 来源 | 状态 |
|---|---|---|
| 42 | `/workspace/f8_ext/preds/f10_V2MAIN_s42.npy` → align → `f10_A0_s42.npy` (在役) | 已存在 |
| 2027 | 同上 s2027 | 已存在 |
| 7, 101, 1234, 31337 | **本轮新训**: `/workspace/pod_f10_train_ext.py` sha256 `93cc2cdf925a1dada9190a5d86664d28c811d9ba0ecf3eaf377d54fc554f2598` | 新建 |

新训配方**逐字抄自** `f8_ext/results/f10_V2MAIN_s42.json`:
`ARM=V2MAIN COST=3.52 LDD=0.25 AFIX=0 EPOCHS=15 LR=3e-4` (win 96 / burn 24 / stride 48 / embargo 60 为脚本常量),
`F10_DLW=/workspace/dlw_ext` (targets sha `31d043e8…`, fea82 sha `9bc111a4…`, fea89 sha `bebf2720…` —— 三者已逐位核对与收据同),
`F10_OUT=/workspace/uplift_2026-09-11/r3_xib/f8` (**不写 f8_ext**)。
对齐到 v4 DL 轴用 `build_dev_v4.py` 的 `align()` 逐字同函数。

> **口径例外声明**: 本条用 `/workspace/dlw_ext` —— 它在 CALIBER PIN 的 FORBIDDEN 列表里。理由: A0 的 DL 腿**本身**
> 就是 `f8_ext/preds/f10_V2MAIN_s{42,2027}.npy` 对齐到 v4 轴(`build_dev_v4.py` 末段)。"同一个对象的第二颗种子"
> 必须用**同一配方**; 换成 v4raw 训出来的是**另一个对象**, 不是第二颗种子。禁令针对的是用 _ext 重算面板/特征去做新测量,
> 不是复制 A0 自己的输入。书层面板/meta/成本/掩码全部仍是 v4 pin 件。

### 2b. 第 7 次抽样 REP42(诊断, **不计入判决**)
再跑一次 seed=42。用途: 把"种子方差"和"同种子重跑方差"分开。若二者同量级, 则 nuisance 的正确名字是
**训练运行**而不是**种子**, 判决表的自由度要按运行数而不是种子数算。预注册: REP42 只进 §6 的方差分解, 不进 §5 的计数。

## 3. Pairing rule (FROZEN)
臂 at seed s **vs A0 at THE SAME seed s**, 同席位, 同装置二进制, 同 span, 锚集取交集 (`np.intersect1d(ts_arm, ts_A0)`)。
**禁止跨种子配对** —— round 1 的致命错误正是把 FSEED=42 的单臂对上两个不同种子的 A0。

## 4. Window / statistic (FROZEN, 不改窗 —— 改窗是 INSTRUMENT 2 的活)
- 窗: **frozen 2025-03-01 00:00Z → 2026-08-10 20:00Z 含端** (= `measure_xib.py` 的 PRIMARY), 预期 n = 3168。
  E-0911-A 暖机 900 锚落在 2022 上半年, 与本窗不相交 —— **本预注册要求逐位验证该不相交性**并落收据。
- 统计量: `g = net_ex / gross_total` (bps/锚/单位 gross, net-of-fee, RAW 记账, CAL=log, 部署态成本 `costb_fee_steady.json`)。
  逐锚配对差 `d = g_arm − g_A0`; 读数 = `mean(d)`。
- CI95: UTC-day block bootstrap, 2000 resamples, `numpy.default_rng([20260905, k])`, **k ∈ {0, 9} 两条子流都跑**。
- **cell PASS 的定义**: 该 cell 的 CI95 下界 > 0 **在 k=0 与 k=9 下同时成立**。任一条含 0 即不算 PASS(对称、不可挑)。

## 5. Decision rule, stated as a count (FROZEN before any number)
每个席位 (dyn / fix) 独立计数 6 颗种子里的 PASS 数:

| 计数 | 该席位判决 |
|---|---|
| **≥ 5 / 6** | **ADMIT** |
| 3–4 / 6 | UNDECIDED |
| **≤ 2 / 6** | **REJECT** |

**晋升判决 = 两个席位都 ADMIT 才 ADMIT**(与 judge_v4 的双席位要求同构)。任一席位 REJECT ⇒ 整体 REJECT。

### 为什么 X = 5(在看数字之前写)
1. **这不是显著性检验, 是稳定性检验。** 六颗种子共享同一个窗、同一块面板、同一条 fund 信号; 零假设下它们
   **高度相关**, 不是 Binomial(6, 0.025)。所以"6 选 5"不能当成 p 值来读, 只能当成"结论不由抽到哪颗种子决定"的门。
   (记忆件 `judge_ci_depends_on_arm_set` / `noninferiority_rule_is_not_noninferiority_proof`: 计数规则必须自报它证明的是什么。)
2. **允许恰好一次失手**是给已测到的种子弥散留的余量: round 2 测到两颗真种子之间臂自身水平 mean|Δg| = 1.567,
   相对 +0.47 的效应是大的。要求 6/6 会让一次不走运的 DL 抽样否掉一条真效应。
3. **4/6 或更少 = round 1 的病**: 结论的正负由你抽到哪颗种子决定。那正是本 instrument 要消灭的失败形态。
4. 5/6 对应"至多一颗种子的 CI 下界落到 0 以下", 而 A0 与臂在同一 cell 里共享绝大部分方差 —— 若效应是真的且
   幅度 ~+0.4 而每 cell SE ~0.20, 真实下界应普遍为正, 6/6 才是期望值, 5/6 已经是让步。

### 多重检验
K 声明 = **1 个假设**(XIB_LAG50 优于 A0), 用 12 个 cell(2 席位 × 6 种子)一起裁, **不选最好 cell**。
因此计数规则上**不做 Bonferroni**。另报 round-2 口径的 BONF68 下界**仅作可比栏**, 不参与判决。

## 6. Seed dispersion → how many seeds would resolve it (方法先冻)
- 报: 臂自身水平的种子间弥散 `mean|Δg|` 与跨种子 sd(用于和 round 2 的 1.567 对账);
  以及**配对差**的跨种子 sd `s_seed = sd_s(mean(d_s))`。
- t=2 所需种子数: `N* = ceil( (2 · s_seed / mean_s(d))^2 )`。
- **必须同时报天花板**: 六颗种子看的是**同一批锚**, 所以加种子**不能**缩小共同的窗内抽样误差。
  定义 `SE_common` = 跨种子平均差序列 `d̄_t = mean_s(d_{s,t})` 的 block-bootstrap SE。
  则 `t` 的上限 = `mean(d̄) / SE_common`(N→∞)。若该上限 < 2, **再多种子也解决不了**, 必须换窗或换统计量。

## 7. Item 3 — the standalone orthogonalised Amihud sleeve
**读码得到的预测(在跑之前写下)**: `infra1_cost/reprice.py` 里 `kind="SL"` 的 `common()` 返回
`LEGS=001 PHI=0 SLOW_NPY=SLOW_v4`, **完全不传 FSEED/FPRED**; 装置里 F10 只在 `if PHI > 0:` 分支加载。
⇒ **该 sleeve 是面板的确定性函数, 种子弥散恒等于 0**, 文件名里的 `_s42` 只是标签。
预注册验证: 用 FSEED=42 与 FSEED=31337 各跑一次, 断言 `d30_n2_c42_rec` **逐位相等**。若相等, 计数规则对它**空转**,
诚实结论是"无需更多种子", 而不是"通过了 6/6"。

**另一条必须报的洞**: `reprice.py` 的 `rz()` 用的是 `np.argsort(np.argsort(.))` = **ORDINAL 秩** —— 正是 INFRA-2
在 XIB 上修掉的那个缺陷(`f_fund_ema_v1` 在 10039 行里 9031 行有并列)。而 sleeve 的正交化基 `ZF` 正是由它建的。
预注册: 用装置自己的 `rankdata` 重建同一条 sleeve(ORTHLAG_AVG), 与 ORDINAL 版逐锚对比, 报 Δ 与结论是否翻转。

## 8. GATE P (先于任何数字)
本轮装置 = `w10_sleeve.py` sha256 `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650`(knobs 全关)。
必须在 `{dyn,fix} × {42,2027}` 四个 cell 上, 对 `d30_n2_c42_rec` **和** `d30_n2_c42_W` 逐位复现归档
`/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_{seat}_s{seed}.npz`。
不过就不报任何数字。

## 9. 落盘
pod: `/workspace/uplift_2026-09-11/r3_xib/`; 本地: 本目录。不 commit。实盘仓只读。
