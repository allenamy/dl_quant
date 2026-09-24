> **创建:** 2026-09-24 | **Session:** dlarch(第 0 步量尺,受 lead 任务书) | **状态:** 预注册,判据冻结,先于任何数字 | **作废条件:** 若 NC s42/s2027 的 `work/legs.npz`、`work/king/KING_OOF.npz`、`work/f10_s*/F10_OOF.npz`、`work/combo_s*/*.npz`、`runs/NEWS2_s*` 任一 sha 与本文所钉不同,本文全部数字作废重跑

# PREREG:NC 部署版的「分数 → 腿 → 组合 → 书」逐层量尺(pre-2026)

**owner** dlarch · **只读**:不写 `~/wide_shadow`、不写 `~/dl_quant_live`、不调交易所、不占 GPU、不写 `/dev/shm`。
输出目录 `pod2:/workspace/dlarch_2026-09-24/`(已用 8 MiB `dd` 实写探针确认可写,见记忆 `pod2_workspace_quota_df_lies_2026_09_23`)。

## 0. 这份预注册要回答的问题

lead 任务书第 0 步:**「F10 的 IC 在哪一层没有变成书的收益」**。
本文在**看任何数字之前**钉住:窗口、口径、每一层测什么量、哪些步骤是**恒等式(必须闭合)**、哪些只是
**并列测量(不构成分解)**、零控制、以及我的事前预测(便于被证伪)。

⚠ **本文不是一个分解。** 项目已受据的结论是:链上有非线性算子(`chain` 的 FTRIM/裁剪/掩码/归一、
`exec_reshape`、发布门、EMA),**线性拆分在这些算子下不可识别**(记忆 `counterfactual_rechain_beats_not_identifiable_2026_09_20`)。
正确的做法是**反事实重链**,那是 CF3 的装置,本轮不做(任务书:第 0 步只读量尺)。
因此本文只做两件事:① 在**每一层用同一个标签、同一种归一**把该层的钱量出来;② 只在**真的是恒等式**的两处
(L3 的线性组合、L5 的 0.55/0.45)断言闭合。其余层与层之间的差**只报「差多少」,不报「因为什么」**。

## 1. 冻结的输入(sha 在运行时逐一断言,不符即 rc≠0)

| 角色 | 路径 | 说明 |
|---|---|---|
| 标签 | `/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz` | `y4s`;sha 必须 == `news2_train_f10.py` L17 的 `NEWT_SHA` = `ca479fcc…6924d62`。**这就是 F10 训练用的那个标签**,口径声明见 §2 |
| 特征/成员 | `/dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz` | 只取 `anchors/symbols/m/off/count`;sha 必须 == `receipts/P2B_FEATURES.json` 的 `sha256` |
| 腿/席位 | `/dev/shm/news2_2026-09-23/work/legs.npz` | `KZ/Z24/ZFD/WL/ready/LR`;sha 必须 == `receipts/P3_LEGS.json` 的 `sha256` |
| King 分数 | `.../work/king/KING_OOF.npz` | `P`;sha 记入收据 |
| F10 分数 | `.../work/f10_s42/F10_OOF.npz`、`.../f10_s2027/F10_OOF.npz` | `P`;sha 必须 == 各自 `TRAIN_RECEIPT.json` 的 `pred_sha256` |
| 组合 | `.../work/combo_s42/{literal,scaled_diagnostic}.npz`、`combo_s2027/…` | `kc/fc/raw/weights/trade_mask/reason`;sha 必须 == 各自 `TARGET_RECEIPT.json` 的 `policies[policy].sha` |
| 书层路径 | `/dev/shm/news2_2026-09-23/runs/NEWS2_s{42,2027}_{scaled,lit}_rule_raw_UAFE/` | 32 条 `PATH_*.npz`,经 `news_stats.load_cell`(import,不重写) |

**装置**:`news2_layer_ladder.py`(新写)+ **import** 两个已钉住的模块,不重写它们的统计口径:
- `news2_diag1_score_ic.py` 的 `ic_series`(逐锚截面 Spearman + 锚内打乱零控制,`MIN_NAMES=20`,`RNG_SEED=20260924`);
- `news_stats.py` 的 `SEG / seg_mask / full_days / path_metrics / summarise`(以及它 import 的 `bt_tables`),
  用于 L7 的书层读数与窗口约定。

## 2. 口径声明(绑定文件,不绑定变量名 —— E-0904-F)

- **标签 = `dlw_targets.npz` 的 `y4s`**,即 **F10 训练损失里那一个**(`news2_train_f10.py` L72、L79、L90)。
  按 CLAUDE.md 更正 KB-05,**记账正典口径是 v4 RAW `Π(1+r)−1`**(`meta_newprod_v4.npz`),
  而 `y4s` 属于「`pod_dlw_targets_ext.py` L93 的 ±0.30 裁剪缓存复利」谱系(E-0908-B),**只作对照**。
  ⇒ **本文 L1–L6 的所有数字一律标注「y4s 口径,只作对照,不得当记账收益引用」**。
  之所以仍用 `y4s`:本文问的是「**训练损失看见的那个钱**在各层剩下多少」,换成别的标签就答不了这个问题。
  **L7(书层)用的是引擎路径,那是记账口径**,所以 L6 与 L7 之间**不可比,只能并列报**,这条写在结果里。
- **不许**从 5m 缓存 `ret5` 重算收益(CLAUDE.md 更正 KB-05)。本文不读 5m 缓存。
- 单位:L2–L6 一律 **bps / 锚 / 单位 gross**(即 `Σ|z| = 1` 的书);L7 是 **每窗(4h)净收益**,由 `path_metrics` 给出。
- 窗口 `pre2026` = `2023-06-30T04:00:00Z … 2025-12-31T20:00:00Z`(**逐字取 `news_stats.py` 的 `SEG`**)。
  分段 `2023H2 / 2024 / 2025` 同样照 `SEG`,一并报(判据纪律:不许单段结论)。
- **两种发布策略都报**:`literal`(= 生产门,固定 380 / 150,记忆 `production_publish_gate_is_literal_380`)
  与 `scaled_diagnostic`(= 判词基准格 `scaled_rule_raw_UAFE` 用的那个)。只报一种就会把
  「门把锚全毙了」和「信号没钱」混在一起。
- 两个种子 s42 / s2027 **都报,分开报**,任何跨种子不同号的读数标注「不同号」。

## 3. 层与量(逐层定义,先于数字)

记 `m_i` = 锚 `i` 的成员索引(`NEWS_FEATURES` 的 `m[off_i:off_{i+1}]`,即 `news_legs.py` 用的同一个集合),
`y_i` = `y4s` 在锚 `i` 的那一行。

**L1 分数层**:逐锚截面 Spearman(`ic_series`,import)。受测对象 4 个:
King `P`、F10 `P`、fund 腿 `ZFD`、rev24 腿 `Z24`。报均值、标准误、逐锚 t、分段值。
**加上 fund/rev24 不是凑数** —— 没有它们,F10 的 IC 是个没有尺子的数。

**L2 腿层(单位 gross 纸面 bps/锚)**:对每个信号 `z`,**逐字照 `news_legs.py` L51–57 的算术**:
`zz = where(y finite, z, 0)`;`zz -= mean(zz[y finite])`;`g = Σ|zz|`;`leg = (Σ zz/g · y)·1e4`(`g ≤ 1e-9` ⇒ 0)。
F10 的 `z` 取**生产口径**`rankdata(P[finite])/max(n_finite−1,1) − 0.5`(`combo_target.py` L28–29),不是原始分数。
- **R1 对账(必报)**:king/rev24/fund 三条我算出来的 leg 与 `legs.npz` 的 `LR` 三列比:逐锚相关、均值差、
  符号一致率。`LR` 用的是 5m 缓存的 `y4v`,我用的是 `y4s` ⇒ **两者本就不同口径**,这一格量的是
  「换标签带来多大偏差」。**若逐锚相关 < 0.95,我把 L2 全部降级为「y4s 代理,偏差已量化」并在结果里点名。**

**L3 组合前的线性合成(恒等式,必须闭合)**:`w = [WL0, 0, WL2]` 归一(`combo_target.py` L30),
`u(z) ≡ Σ_j z_j y_{i,j}`(未归一的纸面钱)。断言(逐锚,容差 `1e-9 · max|项|`):
```
u(zkc_preclamp) == w0·u(king_rank) + w2·u(fund_rank)
u(zfc_preclamp) == w0·u(f10_rank)  + w2·u(fund_rank)
```
再报 **rn8 夹子**(L33–34,把资金费为负且信号为负的名置零)的残差 `u(zkc) − u(zkc_preclamp)`,**具名,不归因**。
这一层回答:**在合成的那一刻,纸面上的钱有多少份是 F10 的、多少份是 King 的、多少份是 fund 的。**
⚠ 这是 CLAUDE.md「口径三层」里的**复合目标层**,不是书层;引用必须带层名。

**L4 链层(`chain`:FTRIM / 裁剪 / `sel` / `LIVE_MASK` / 归一 / EMA)**:
报 `u(kc)/Σ|kc|·1e4` 与 `u(zkc)/Σ|zkc|·1e4`(同理 fc)。
**这一步不是恒等式,`chain` 非线性且带状态** ⇒ 只报两个数和它们的比,**不报「链吃掉了 x%」之外的任何因果**。

**L5 发布目标(恒等式,必须闭合)**:`raw = .55·kc + .45·fc`(`combo_target.py` L38)⇒
`u(raw) == .55·u(kc) + .45·u(fc)`,逐锚断言。报两项各自的窗口均值与占比。
这一层回答:**发布出去的那本书的纸面钱,有多少是 F10 链贡献的。**

**L6 发布门层**:`trade_mask` 为真的锚占比、`reason` 计数;并分别报
「发布锚上 raw 的单位 gross 纸面 bps」与「被门挡下的锚上 raw 的同一个量」。
⚠ 被挡下的锚上,书**不是空的,是上一本**(`continuous_combo.py` docstring + `bt_hist_sim31.py` L195–199,
附录 C.3 已受据)。所以 L6 只能说「这些锚上新算的书没被交易」,**不能**说「这些锚没赚钱」。

**L7 书层(记账口径,并列不可比)**:`news_stats.load_cell` + `path_metrics`,32 条路径的路径均值:
`g / price(pnl) / funding_paid(car) / fee(cst) / unknown_excluded(unk) / turnover / hold_anchors / halt_anchors`。
`g == pnl − car − cst − unk` 由 `path_metrics` 自带断言(`g_identity_max_err ≤ 1e-9`),我照抄不放宽。

## 4. 零控制与承重断言(先红后绿)

- **N1 锚内打乱**:L1、L2 全部重算一遍,标签在锚内打乱(固定 RNG)。
  判据:打乱后 L1 各 |mean IC| < 0.005 且 L2 各 |mean leg| < 0.30 bps/锚。**不过则本文全部读数作废。**
- **N2 恒等式**:L3 两条、L5 一条,逐锚容差内闭合;任一锚不过即 rc≠0,不放宽容差。
  ⚠ 依记忆 `brittle_check_welds_identity_to_population_expectation_2026_09_20`:恒等式容差**不与人口完整性焊在一起** ——
  人口计数(锚数、非零格数)单独报,不作门。
- **N3 非零格计数**(记忆 `rank_transform_turns_all_nan_into_all_zero_2026_09_23`):
  每个 `z` 报**非零格数**而不是有限格数;若某个信号在某段非零格为 0,标注「该段无测量」而不是算出 0。
- **N4 未知收益不得当 0**(记忆 `aggregate_must_not_encode_no_measurement_as_a_value_2026_09_20`):
  L3–L5 里 `kc/fc/raw` 非零而 `y4s` 非有限的格,**单独计数并报其权重质量占比**;主数字按「排除这些格」算,
  同时报「这些格占 gross 的多少」。若质量占比 > 2%,主数字标注 UNRELIABLE。
- **N5 红能力**(记忆 `red_capability_check_is_vacuous_when_baseline_is_red`):
  先断言基线全绿并**逐条打印实测值**,再做一次变异(把 `raw` 的 0.45 改成 0.40)确认 N2 的 L5 断言会变红;
  两行判词都进收据。

## 5. 事前预测(便于被证伪;写在数字之前)

1. L1:King 的 IC > 0(已有受据:0.0617 年折);**F10 的 IC 也 > 0 但显著更小**,因为 F10 的损失不是 IC 而是
   带成本的书层效用。若 F10 的 IC ≤ 0 而书层仍有价值,那就是「排序≠净额」的第六例,要单列。
2. L2:fund 腿的单位 gross bps **最大**;F10 腿 > 0 但小于 fund;rev24 腿在 pre-2026 为负或接近 0。
3. L3:F10 在合成那一刻的份额 ≈ `w0`,而 `w0 = WL0/(WL0+WL2)` 在 pre-2026 大概 0.2–0.4 ⇒
   **F10 的纸面份额 ≈ 0.45 × w0 ≈ 0.09–0.18**。这个数如果成立,那么「F10 的 IC 变不成书的收益」
   **第一大原因就是权重,不是模型** —— 这是本轮最可能的答案。
4. L6:pre-2026 在 `literal` 门下发布锚**极少**(受据:记忆 `production_publish_gate_is_literal_380` 说 2023/24 全现金);
   在 `scaled` 门下被挡下的锚约 20–30%,且**全部**因 `gross`。
5. 最可能的结论形状:**不是某一层「丢掉了」IC,而是 F10 的分数在设计上只买到了约十分之一的书**,
   外加约四分之一的锚根本没换书。**若预测 3 与 4 成立,第 1/2/3 步的设计就应该先动权重与门,再动架构。**

## 6. 决策规则(本文只量尺,不录取任何改动)

本文**不产生任何录取/否决**。它只产出一把尺子。任何后续改动(第 1/2/3 步)的录取判据由 lead 冻结,
且必须是**书层 `dbar`**、以 news2 扰动噪声实验测出的 σ 为尺、**至少 3 个种子作测量**(用户禁多种子生产集成,
只许用于测量 —— 记忆 `feedback_no_multi_seed_2026_05_15`)。

## 7. 已知局限(写在前面,不等结果)

1. `y4s` 不是记账口径(§2),L1–L6 与 L7 **不可比**。
2. 只有 **2 个种子**的 F10;跨种子不同号的任何读数一律标注,不取均值当结论。
3. `chain` 带状态,L4 的比值**不是**「链的代价」的因果度量。
4. pre-2026 与 2026 的选型样本重合问题照旧存在(受据:`certified_path_a0_history_is_all_2026_2026_09_20`);
   本文只报 pre-2026,不拿 2026 作论据。
5. NC 的组合轴 8,142 锚(2023-01-01 起)短于腿轴 10,333 锚(2022 起),引擎窗又是第三个轴 ——
   所有对齐按**时间戳**做并报三个轴的交集大小,不按行号。
