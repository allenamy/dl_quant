# DL Quant — Multi-Asset Track — Project Guidance

> **Phase:** Multi-asset cross-sectional y_600 (launched 2026-05-20). Single-asset BTCUSDT concluded — see `docs/SINGLE_ASSET_Y600_FINAL_MILESTONE_2026_05_20.md` (REG_arch P=0.0646, retail-maker Sharpe 4.4). This file governs the MULTI-ASSET work.

## Project Identity

**Goal:** Binance USDT-perp 多资产中频预测。给定 14 个 symbol 的同步 1s bar 序列，预测每个 symbol 未来 10 min 收益率 y_600。目标 **avg per-asset Pearson 0.10** (单资产 BTC 0.065)，β≈1，单调校准，near-zero long-short bias。

**Universe:** 14 USDT-perp: BTC ETH SOL BNB XRP DOGE ADA LINK BCH TRX LTC DOT FIL ETC (5 USDC dups 仅作 robustness check)。Data: `/mnt/storage/share/bar_data` (READ-ONLY), 1s bars, 85800/day, 2022-01→2025-11 (~3.9yr), 5-level LOB + 9-bucket cumu depth + trade flow + book add/del。

**Plan:** `docs/superpowers/plans/2026-05-20-multi-asset-y600.md` (10-phase, GO/NO-GO gated)。

### 核心 reframing (实测, 是整个方法论的支点)

- 同期 BTC→alt beta **巨大** (ETH corr 0.84, avg alt ~0.70)。Lagged BTC→alt 在 600s **很弱** (~0.02)。
- ⇒ **beta-projection** (β·ŷ_BTC) 白送 **~0.045 Pearson/alt**。模型真正要做的是 **residual alpha** (0.045 → 0.10)。
- Risk ladder: **C** (beta-projection floor) → **A** (shared-backbone universal REG_arch + cross-asset attention，主力) → **B** (BTC 25-level LOB enrich leader，conditional)。

---

## 不可违反约束 (Core Constraints)

1. **信号极弱 (R² < 1%)** — 容量必须匹配信号，不能用复杂度强行拟合噪声。Multi-asset 的优势是 **parameter pooling** 把 params:sample 从 18:1 翻到 ~1:1000，这是核心杠杆，不是堆容量的借口。
2. **非平稳性** — 分布/lead-lag/corr 持续漂移。任何结论必须多日时序 walk-forward CV 验证，跨 regime 检查 (A5)。
3. **预处理 > 架构** — 特征工程优先级永远高于模型创新。
4. **机制 > 堆叠 (用户硬约束 2026-05-20)** — 每个 feature / module 必须有**清晰的作用机理 (为什么应该带来信号)** + 通过**定量 gate**。禁止生硬堆叠。
5. **单资产代码只读** — 所有新代码在 `multi_asset/`。`src/` `configs/` 等只 import 不改。`reg-arch-final` branch 是冻结参考。
6. **Share data 只读** — `/mnt/storage/share` 一律 mode="r"。本地开发，rsync 推送 server 训练 (`multi_asset/sync_to_server.sh` → `work_hsy/quant_research_multi_asset`，单 RTX 3090)。

### 决策检查清单 (每次架构/特征/loss 改动必答)

- [ ] **机制**：这个组件的作用机理是什么？为什么在 low-SNR 多资产上应该带来信号？(不是"试试看")
- [ ] **信号验证**：用 cross-sectional Ridge/XGBoost walk-forward 对比了吗？ΔP ≥ +0.005 (feature) / +0.003 (model channel)？
- [ ] **复杂度预算**：新增多少参数？pooling 后 params:sample 是否健康？
- [ ] **泄漏**：cross-asset / lead-lag feature 是否严格 ≤t？shuffle-future null test 过了吗？
- [ ] **OOS**：多日 walk-forward 严格时序隔离？per-fold sign-consistent (无 fold 反号)？
- [ ] **σ 检查**：σŷ/σy ≥ 0.02？(低于直接 reject)

### 禁止事项

- 禁止单日/单 fold 声称有效；禁止 `stride < horizon`；禁止不经 Ridge baseline 就上 DL；禁止盲目堆 channel/module；禁止改单资产代码；禁止动 share data。

---

## Metric Discipline (dual-caliber)

**所有实验同时报告 Pearson + Spearman。** 多资产额外要求 **dual-caliber**:

1. **avg per-asset Pearson** — headline (目标 0.10)。每个 symbol 各算 P，再平均。
2. **cross-sectional rank-IC** — 每个 timestamp 横截面 rank corr，mean + IR。交易侧首选 (long-short portfolio)。
3. **per-asset Spearman** — 重尾稳健。
4. **β (y on ŷ) + σŷ/σy** — 校准 + collapse 检查。
5. **long-short bias** — 预测 cross-sectional demean 后应 near-zero。
6. **Clean vs Dense** — clean = stride≥600 非重叠；报告必须双给，clean 才 honest。
7. **net-of-fee** — 回测必须扣 per-asset cost (A7 tiering)。

**P/S 分歧** = 危险信号，记录 + 诊断。不可为单指标牺牲另一个。不可单指标 early-stop / checkpoint。

---

## Anti-Patterns (单资产血泪，全部 inherit；详见 milestone doc)

**Loss/target:** #10 multi-horizon UNIT 机制错配；#12 tail-focal REPLACE → P/S 分歧 (AUX 安全)；#15 direct rank-loss REPLACE → val→test drift (AUX w≤0.1 安全)；#20 dir_huber w_wrong>0 / L2 primary → σ collapse (用 plain Huber + pinball L1 primary)；#21 utility_rank α=1 + softplus head → q50 偏负 (α=0 修复)；#25 mag/tail-focal 作 AUX≤0.30 安全。

**架构:** #2 stride<horizon 标签重叠；#5 params:sample >1:2 过拟合 (pooling 反转此项)；#22 MRP replace last-token NULL；#23 decoupled (2σ−1)×softplus head σ collapse (保留 tanh×softplus DAQH)；#24 σ-gate BEST checkpoint (TV channel init-noise → illusory high-P broken ckpt，必须 σŷ/σy≥0.02 gate)；**#29 channel-addition penalty (每加 channel −0.013 P，除非 ≥+0.003 alpha)** — multi-asset 最相关。

**评估:** #1 单日验证 (regime 差异)；#14 单 fold/seed 不可靠；#16 rank-blend β crash (用 value-blend)；#18 label engineering 必须 raw y eval；#19 eval methodology 一致 (raw + dense + per-fold-aware for production；raw + stride10 + block-bootstrap for stats)；#26 regime-aware 必须 causal indicator (future-|y| stratification 不可交易)。

**新增 multi-asset 候选:** lead-lag feature 必须 leakage-safe (shuffle-future null)；cross-sectional 必须 per-asset MAD-σ 归一才可比；beta 必须 causal rolling (非 stationary)。

---

## Documentation Discipline

所有 Claude 生成的 docs/notes 首行附元信息: `> **创建:** YYYY-MM-DD HH:MM TZ | **Session:** ... | **状态:** draft|in-progress|final|superseded | **作废条件:** ...`。禁止无元信息的 status/interim 文档；禁止 `_v2`/`_final` 后缀替代日期；同主题多份必须 cross-reference。

---

## 当前进度 (滚动更新)

**Phase 0 (infra) — done:** branch `multi-asset`, `multi_asset/` skeleton, server sync, bar_loader (cross-validated bit-for-bit vs share loader), this CLAUDE.md。
**下一步:** Phase 1 EDA GO/NO-GO funnel (A1 universe / **A2 per-asset Ridge SNR ← 项目定生死的 gate** / A4 lead-lag / A6 target dist / A7 cost tiering) → Phase 2 panel pipeline → Phase 3 baselines (beta-projection floor ~0.045 + xsec Ridge ceiling)。

**关键工具 (单资产可复用):** `src/model/dual_path_model_v3.py::DualPathLOBModelV3` (= REG_arch backbone, 见 `multi_asset/NAMING.md`)；`src/model/cross_asset.py::CrossAssetAttention` (已 scaffold，待 wire)；`src/losses/cross_sectional_ic_loss.py`；`src/training/trainer_v2.py` (σ-gate BEST + EMA)。
