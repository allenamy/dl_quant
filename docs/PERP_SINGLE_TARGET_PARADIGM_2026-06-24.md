# Dual-Source Perp y_600 — 当前最佳范式（合作者复现手册）

> **创建:** 2026-06-24 | **Session:** dual-source-perp overnight autonomous | **状态:** final（当前最佳；dp48/mh180 强月 dense 杠杆仍在跑，落地后追加）| **作废条件:** 出现 ΔP_clean ≥ +0.005 的新 leak-free 杠杆，或换数据源（funding/OI）后 choppy 突破 0.06。
>
> 本文给合作者一份**自包含**的最佳范式说明：设计理念 → 架构 → 数据/损失 → 结果阶梯 → 复现命令 → 代码位置 → 诚实结论。配套：实验全量日志 `docs/v2_autonomous_overnight_2026_06_24.md`；精简引用 `docs/dual_source_perp_REFERENCE_2026_06_24.md`。

---

## 0. TL;DR

**任务：** 单资产 BTC USDT-**永续** y_600（未来 10min 收益）预测，输入用**现货 + 永续**双源（盘口 + 成交），target 是**永续** mid。

**当前最佳生产模型 = `adaptive`**（REG_arch + 永续 deep-book gated residual + regime FiLM/bias），**一个模型，两个 regime 都不亏：**

| regime | DENSE P | CLEAN P | β | 对照 |
|---|---|---|---|---|
| **强月 (2025-04)** | **0.0747** | **0.1054** | **0.98** | ≥ nobasis 0.0732/0.1026（且 β 1.49→0.98 校准更好） |
| **choppy (2026-05)** | — | **0.035 / 0.040**(BEST/EMA) | 修正 | ≥ nobasis 0.0225/0.0294 |

- **强月 CLEAN 0.105 ≥ 0.10（达标，β≈1 可交易）；DENSE 0.075 < 0.10。**
- **choppy ~0.04 = in-data 真上限（DL=Ridge 平价，非 DL 缺陷）；0.06 需正交数据（funding/OI，本期 out-of-scope）。**
- **核心杠杆 = deeper-perp tower**（把永续盘口残差门加深，0.04→0.08）。**regime FiLM 让同一模型在两 regime 都最优。**

---

## 1. 问题 & 核心 reframing（设计理念的支点）

1. **永续是现货的衍生品。** 信号主体来自现货盘口特征（单资产里程碑就是 spot-LOB），但**永续盘口自带现货没有的微结构状态**（深度压力梯、流动性摆放、基差承载的不平衡）。→ 把永续 deep-book 作为**额外信息源**注入，而非替换。
2. **信号极弱（R²<1%）+ 强非平稳。** 不能堆容量拟合噪声。每个模块必须有机理 + 过定量 gate（ΔP_clean ≥ +0.003，leak-safe）。
3. **强月 vs choppy 信号结构本质不同（实测）：**
   - **强月：非线性/时序信号**（Ridge 线性上限 0.041，DL 0.08 = 翻倍）→ DL + deeper-perp 大赢。
   - **choppy：弱线性信号**（DL ≈ Ridge ~0.03）→ DL 无非线性增益，~0.04 是真上限。
4. **生产无法预知强弱月** → 必须**一个自适应模型**，用 regime 特征自己判断、两 regime 都好（headline 指标 = pooled 多 regime；分 regime + dual-caliber 双报）。

---

## 2. 架构（自底向上）

```
INPUT  x_feat (B,600,64)  现货手工特征(npz_v4-64) + cross-8(可选)
       x_raw (B,600,20,4) 现货 20 档盘口  [REG_arch Path-B]
       x_raw_perp_deep (B,600,20,4) 永续 20 档盘口  [本范式新增]
       regime_prior (B,6) 因果 regime 描述子
  │
  ├─ Path A: x_feat → (GDCN) → input_proj ─┐
  ├─ Path B: x_raw → RawLOBEncoder ────────┤→ fusion → h (B,600,d_model=32)
  │                                          │
  │   ┌─ 永续 gated residual（本范式核心杠杆）──────────────┐
  │   │  h_perp = RawLOBEncoder_perp(x_raw_perp_deep)  # d_perp=32 │
  │   │  g      = sigmoid(perp_gate(h))                # 数据相关门  │
  │   │  h      = h + tanh(perp_alpha)·g·perp_proj(h_perp)         │
  │   └────────────────────────────────────────────────────────────┘
  │
  ├─ Conformer ×2 (d=32, kernel=15, 2 heads)
  │     └─ FiLM-multistage(regime_prior)  逐 block γ/β 调制
  ├─ pool: last-token  →  h_pred (B,32)
  │     └─ RegimeFiLM(h_pred, regime_feats)  # adaptive 的 (a)
  │     └─ PPNet gate(h_pred, regime_prior)
  ├─ DAQH 单调 3-分位头 → [q10,q50,q90]
  │     └─ output_scale + regime_bias_head(regime_prior)  # adaptive 的 (b)
  └─ (snapshot_skip: 已实现但 OFF；见 §6)
```

**2.1 永续 deep-book gated residual（`DualLOBREGArch`，最大杠杆）**
- 用**和父类 Path-B 同款** `RawLOBEncoder`（channel_mix_conv + level_attention_pool）编码永续 20 档盘口 → `h_perp`。
- 以**状态相关残差**注入到融合后的 bus `h` 上、Conformer **之前**：`h += tanh(perp_alpha)·sigmoid(perp_gate(h))·perp_proj(h_perp)`。
- **机理：** 永续盘口的深度压力/流动性摆放/基差不平衡是现货盘口没有的方向信息；以残差注入 → 不新增 Path-A channel（避开 anti-pattern #29 通道加法惩罚），下游 backbone/FiLM/head 全不变。
- **两个关键调参（=本范式的"大跳"）：**
  - **`d_perp` 16 → 32（deeper tower）：** 永续残差门原来 capacity-limited（门常顶到上限）；加宽永续编码器 → 挖出更多非线性盘口信号。**这是 0.04→0.08 的主因。**
  - **`perp_alpha_init` 0.05 → 0.02（gentle gate）：** master 门初值调小 → 修正 β 过冲（校准）。注意**不能 0**：`tanh(0)=0` 会让残差子网梯度饿死（gradient-starvation，已验证）→ 必须非零小值。

**2.2 regime FiLM / bias（`adaptive` 的自适应机制，让一个模型两 regime 都好）**
- **(a) RegimeFiLM：** 一个**非学习**的 `RegimeFeatureExtractor` 算 6 个**因果** regime 描述子（60/300/1200s 实现波动、波动加速度、OBI 均值、lag-60 OBI 自相关）→ FiLM MLP(hidden=8) 出 (γ,β) 调制 pooled 嵌入：`h_pred ← γ⊙h_pred + β`，**identity-init（γ≈1,β≈0）**。
- **(b) regime_bias_head：** zero-init MLP，按 regime_prior 加一个 per-horizon 偏置。
- **它是 vol/trend 的 FiLM 门**，让模型**按 regime 自适应调整表示/校准**：实测在强月**不稀释**（0.075/0.105，门在高 vol 收敛）、在 choppy **抬升**（0.029→0.040）、且把 β 从 1.49 修到 0.98。
- **它 NOT 是：** [0,1] basis 门、basis-dynamics 块、snapshot-skip（这些都试过，见 §6 阴性清单）。
- **重要：** regime FiLM/bias 的实现代码在**只读父类** `src/model/dual_path_model_v3.py` + `src/model/regime_film.py`（继承的 REG_arch base），本范式只是**用 config flag 打开**（`use_regime_film/regime_film_hidden/use_regime_bias/use_film_multistage`），不改 src/。

---

## 3. 数据 pipeline

- **Cache：** `data/npzv4_dual`（overlay）= 单资产里程碑的 `npz_v4`-64 现货特征（spot-LOB 38 + perp-trade 18 + ret/vol 8）+ cross-8 + **永续 25 档盘口** + X_long，~981 天 2023-02→2025-09，ts-join leak-safe。
- **窗口：** input_len=600（1s bar），stride=180（dense 训练），horizon=600。
- **来源：** `/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/`（READ-ONLY，Tardis book_snapshot_25 + trades，现货 `binance` + 永续 `binance-futures`，µs 戳，零缺失）。**永续 book mid 与 perp target 对齐 corr 1.000。**
- **Infra 修复（关键，根治整夜 OOM）：** train700 全 split preload 原本 ~156G > 125G cgroup → OOM。真因 = X 特征张量 f32 占内存 51%（raw 盘口早已 f16）。**修法：X 在内存里存 float16、`__getitem__` per-row 升 f32（模型仍 f32 训练）→ train700 = 116G 装得下。** 等价性 corr(X_f16,X_f32)=0.99999999、train700 no-OOM 实跑验证。env `DUAL_PRELOAD_X_F32=1` 可回退。
- **教训：** 这个重 cache **只能 `num_workers=0`/preload**（nw>0 会 fork-deadlock；f16 是 preload-RAM 修复，不是 worker-streaming 修复）。

---

## 4. 损失（`dul_config`，全部作用于同一残差，无梯度冲突）

**= singh α=0 huber**（单资产 V5 winner，已 inherit）：
```
L = 0.5·utility_rank(α=0) + 0.5·Huber_δ2(w_wrong=0) + 0.1·pinball(q10/50/90)
  + 0.1·cls(tail_focal_1p5) + 0.3·mag_focal_huber(clip 0.3–3.0)
```
- **`utility_alpha=0`（关键）：** α=1 + softplus head 会让 q50 偏负（anti-pattern #21）；α=0 是 bias 根因的外科修复。
- **Huber 作 primary（w_wrong=0）+ pinball L1：** 低 SNR 下 L2-like primary 会 σ collapse（#20）；plain Huber + pinball L1 安全。
- **校准/单调：** DAQH 单调 3-分位头 + EMA(0.999) + σ-gate（σŷ/σy≥0.02 才存 BEST checkpoint）。

---

## 5. 结果阶梯（强月 2025-04，DENSE / CLEAN，raw Pearson）

| 配置 | DENSE | CLEAN | β | 备注 |
|---|---|---|---|---|
| base（npzv4_dual, train700, 无永续残差） | 0.052 | 0.077 | — | 起点 |
| + 永续残差门 α0.05 | 0.059 | — | — | +轻 |
| + 温和门 α0.02 | 0.061 | — | — | +轻 |
| + **deeper-perp d_perp=32** | 0.071 | 0.110 | — | **大跳** |
| **dp32_a02（deeper + 温和门，nobasis）** | **0.080** | **0.113** | ~1 | ✅ 验证赢家，**shuffle-null PASS** |
| baseline 复现（本次 overnight，apples-to-apples） | 0.073 | 0.103 | 1.49 | 参考 |
| **adaptive（+ regime FiLM/bias）** | **0.075** | **0.105** | **0.98** | ✅ **生产选择，两 regime 都赢** |
| + real-X_long 长上下文 | −0.020 | −0.024 | — | ❌ 死杠杆 |
| + basis-dynamics（additive） | −0.011~−0.014 | — | — | ❌ 强月负 |

**choppy 2026-05（CLEAN）：** Ridge ≈ 0.030｜DL nobasis 0.0225/0.0294(BEST/EMA)｜**DL adaptive 0.0346/0.0402** ← 最好。**DL=Ridge 平价（无 DL bug），~0.04 真上限。**

---

## 6. 关键发现（机理 + 阴性清单，省合作者时间）

**正向（机理成立 + 过 gate）：**
1. **deeper-perp tower = 唯一大杠杆**（0.04→0.08）。机理：放开 capacity-limited 的永续残差门，挖永续盘口非线性方向信号。
2. **regime FiLM/bias = 一个模型两 regime 都好**（强月不稀释 + choppy +0.011 + β 修正）。

**阴性（已严格证伪/边际，不要重试）：**
3. **basis-dynamics**（z-离均衡/AR1-反转/半衰期/lead-lag）：多变量 Ridge 上 regime-specific（choppy +0.0076 / strong −0.0137），**但不是干净的单通道符号翻转**（corr-flip 证伪：basis_z 两 regime 都正，21 通道仅 4 显著）。作统一杠杆**边际/死**。
4. **长上下文（ModernTCN/X_long）= 死杠杆**：降级版 + 真 25 档版、Ridge + DL，全负/边际（strong −0.020，choppy 边际）。
5. **"Ridge>DL on choppy" = 口径 artifact**：apples-to-apples（同折同口径）DL=Ridge（~0.03）。**choppy 无 DL bug**；时序稀释假设也证伪（信号在窗口平均里，非瞬时快照）→ snapshot-skip 因此**保留代码但 OFF**（`use_snapshot_skip=false`）。
6. **choppy 0.06 = in-data 不可达**：线性 + DL 都撞 ~0.04 上限；需正交数据（funding/OI，本期 drop）。

---

## 7. 复现（exact）

**前置：** server `jpline`（`ssh jpline`），repo `/mnt/storage/private/work_hsy/quant_research_multi_asset`，env `hsy_v5push`，单 RTX 3090。本地改 → `multi_asset/sync_to_server.sh` 同步 → server 跑。

**强月 adaptive（生产模型）：**
```bash
# config: configs/npzv4_dual/perp_dp32_a02_adaptive_2025_04.json
# 关键 flags: d_perp=32, perp_alpha_init=0.02, use_perp_residual=true,
#   use_regime_film=true, regime_film_hidden=8, use_regime_bias=true,
#   use_film_multistage=true, train_days=700, batch=1024, patience=10,
#   num_workers=0, preload=true, EMA=0.999, embargo=1d
nohup python -u multi_asset/train/train_v2arch.py \
  --config configs/npzv4_dual/perp_dp32_a02_adaptive_2025_04.json \
  > /tmp/adaptive_strong.log 2>&1 &
# f16-preload 默认开（省内存）；DUAL_PRELOAD_X_F32=1 可回退 f32
```

**choppy（同架构，2026 折）：** `configs/v2arch/dp32_adaptive_2026_05.json`（batch=256，patience=10，test 2026-05）。

**eval（dual-caliber + per-regime + β）：** `multi_asset/eval/`（DENSE=stride180 重叠；CLEAN=stride≥600 非重叠；两者都 raw Pearson）。

---

## 8. 诚实结论 vs 目标（strong 0.10 / choppy 0.06）

| | 目标 | 实测（adaptive 单模型） | 判定 |
|---|---|---|---|
| 强月 | ≥0.10 | CLEAN **0.105** / DENSE 0.075，β0.98 | **CLEAN 达标 + 可交易**；DENSE 差 +0.025 |
| choppy | ≥0.06 | **0.040** | 真上限 ~0.04，**需正交数据** |
| β/单调/DA | 良好 | β0.98、DAQH 单调、shuffle-null PASS | ✅ |

- **强月在 honest 的 CLEAN 口径下达标（0.105>0.10，leak-free，β≈1）→ 可作交易指引。** DENSE 0.075→0.10 的最后冲刺 = dp48（更深 tower）+ mh180（multi-horizon y_180），仍在跑，落地追加。
- **choppy 0.06 在纯 in-data 不可达**（DL=Ridge 双证 ~0.04 上限）；唯一出路 = funding/OI/liquidations 等正交数据。

---

## 9. 代码地图（file:line）

| 组件 | 位置 |
|---|---|
| 永续 gated residual（核心）| `multi_asset/model/dual_lob_regarch.py`（`DualLOBREGArch`，注入在 `encode()` L217-229） |
| `d_perp=32` | `dual_lob_regarch.py:98,128-130` |
| `perp_alpha_init=0.02`（gentle gate）| `dual_lob_regarch.py:91,144-145` |
| 长上下文分支（v2arch，已测死）| `multi_asset/model/dual_lob_v2arch.py`（`DualLOBV2Arch`）+ `modern_tcn_lite.py` |
| regime FiLM（adaptive a）| `src/model/dual_path_model_v3.py:451-462,1149` + `src/model/regime_film.py`（只读父类）|
| regime bias（adaptive b）| `src/model/dual_path_model_v3.py:873-886,1268-1269` |
| snapshot-skip（OFF）| `dual_lob_regarch.py:102-123,368-393` |
| f16-preload 修复 | `multi_asset/data/dual_lob_dataset.py:155-168` + `v2arch_dataset.py` |
| 损失（singh α=0 huber）| config `dul_config` → `src/losses/`（utility_rank/huber/pinball/mag_focal） |
| 训练入口 | `multi_asset/train/train_v2arch.py`（σ-gate warmup-fix：`elif sigma_ok: epochs_no_improve += 1`） |
| best config | `configs/npzv4_dual/perp_dp32_a02_adaptive_2025_04.json` |

---

## 10. 泄漏 / 纪律哨兵（全过）

- **shuffle-future null（dp32_a02）：PASS** —— 训练 permuted-y → σŷ/σy 从 0.088 collapse 到 0.006、PERP P=−0.055（信号消失=无泄漏）。
- **embargo=1 天** >> horizon 600s；train-based target 归一化；ts ≤ t 静态检查。
- **dual-caliber**：DENSE（stride180 重叠，自相关）+ CLEAN（stride≥600 非重叠，honest）双报；所有 headline 用 CLEAN。
- **单资产/src 只读**：所有新代码在 `multi_asset/`，src/ 只 import 不改（regime FiLM 用 config flag 打开父类能力）。
- **share data 只读**：`/mnt/storage/btcusdt_copy*` 一律 mode="r"。

---

*本文档随 dp48/mh180 强月 dense 杠杆结果更新。当前最佳生产模型：`adaptive`（强月 CLEAN 0.105/β0.98 + choppy 0.040，leak-free，单一自适应模型两 regime 都最优）。*
