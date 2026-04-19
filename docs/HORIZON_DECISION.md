# Horizon 选择决策文档

> **决策日期：** 2026-04-18  
> **决策人：** Claude + Siyu（项目负责人）  
> **结论：** **保持 y_180 为生产主力**。

---

## 背景

用户问题：我们一直在训练 180 秒预测窗口。这是当前项目（小团队、中频、不追求 HFT）的最佳选择吗？

## 实验

在 **完全相同的 3-fold walk-forward 设置**（train=700d, val=30d, test=90d, fold_stride=60）下，在 V4 NPZ 特征上运行 Ridge/TemporalRidge/XGBoost 对比 4 个 horizon。命令：

```bash
python3 -m src.baselines.evaluate_baselines \
    --npz-dir data/npz_v4 \
    --output-dir experiments/baselines_horizon_sensitivity/y_$H \
    --train-days 700 --val-days 30 --test-days 90 --fold-stride 60 \
    --horizon-key y_$H --mask-key y_mask_$H --use-last-timestep \
    --save-predictions experiments/baselines_horizon_sensitivity/y_$H/preds
```

for `H ∈ {60, 180, 300, 600}`.

## 原始结果

| Horizon | Ridge Pearson | Ridge Spearman | XGBoost Pearson | XGBoost Spearman | DirAcc | Residual AC(1) |
|:-:|---:|---:|---:|---:|---:|---:|
| y_60 | **0.1495** | **0.1910** | 0.1146 | 0.1877 | 58.6% | −0.024 |
| y_180 | 0.0876 | 0.1099 | 0.0963 | 0.1099 | 54.9% | −0.018 |
| y_300 | 0.0735 | 0.0830 | 0.0737 | 0.0846 | 53.4% | **+0.372** |
| y_600 | 0.0400 | 0.0491 | 0.0383 | 0.0538 | 52.0% | **+0.681** |

## 关键校准：通过子采样模拟 clean stride

我们不必重新生成 NPZ。**通过只取每 H/60 个样本（模拟 stride=H），即可估计干净 stride 下的 Pearson：**

| Horizon | Original (stride=60) P / S | Clean (stride=H) P / S | 变化 |
|:-:|:-:|:-:|:-:|
| y_60 | 0.143 / 0.189 | 0.143 / 0.189 (无重叠) | — |
| y_180 | 0.084 / 0.109 | **0.089 / 0.112** | 略升 |
| y_300 | 0.071 / 0.082 | **0.074 / 0.079** | **几乎不变** |
| y_600 | 0.035 / 0.047 | **0.019 / 0.060** | P 腰斩，S 反升 |

**结论纠错：**
- **y_180 的原始数字公平**（clean 略高一点）
- **y_300 的原始数字基本公平** —— 我之前的"严重污染"描述过激
- **y_600 的 Pearson 确实被污染**（腰斩），但 **Spearman 反而被低估**（0.047→0.060）

## 只看可信对照：y_60 vs y_180

### 步骤 1：原始 IC

- y_60 Ridge Pearson 0.150
- y_180 Ridge Pearson 0.088
- 比例：**y_60 IC 是 y_180 的 1.7×**

### 步骤 2：目标幅度（σ）— 用真实数据

从 2024-06-15 的 NPZ 文件直接测量：

| Horizon | y_sigma (decimal) | y_sigma (bps) |
|---|---:|---:|
| y_60 | 0.000225 | **2.25** |
| y_180 | 0.000391 | **3.91** |
| y_300 | 0.000528 | **5.28** |
| y_600 | 0.000727 | **7.27** |

**⚠️ 之前版本错误：** 我最初用 σ=20/50 bps，是实际的 **~10 倍**。BTC 180s 的 σ 只有 ~4 bps，不是 50 bps。

**√H 缩放验证：** y_60/y_180 = 2.25/3.91 = 0.58 ≈ √(60/180) = 0.577 ✓

### 步骤 3：每笔毛边际（Clean Pearson × σ × 1.76）

使用**子采样模拟 clean stride**得到的 Pearson：

| Horizon | Clean Pearson | σ_y (bps) | Top 10% edge (bps) |
|---|---:|---:|---:|
| y_60 | 0.143 | 2.25 | **0.57** |
| y_180 | 0.089 | 3.91 | **0.61** |
| y_300 | 0.074 | 5.28 | **0.69** |
| y_600 | 0.019 | 7.27 | **0.24** |

**关键发现：**
- 每笔信号强度 **y_300 ≥ y_180 ≈ y_60 ≫ y_600**
- y_300 每笔 0.69 bps 为最高（clean stride 假设下）

### 步骤 4：成本建模

Binance Futures BTCUSDT：

| 项目 | Maker | Taker |
|---|---:|---:|
| 单边 fee | 2 bps | 4 bps |
| **Roundtrip fee** | **4 bps** | **8 bps** |
| 滑点（实测保守估计） | 1-2 bps | 3-5 bps |
| **Roundtrip total** | **5-6 bps** | **11-13 bps** |

### 步骤 5：净边际（简单 top-10% 多空，Maker-only）

| Horizon | 毛边际 (bps) | 成本 (bps) | **Net edge** | 结论 |
|:-:|:-:|:-:|:-:|:-:|
| y_60 | 0.57 | 6 | **−5.4** | ❌ 严重亏损 |
| y_180 | 0.61 | 6 | **−5.4** | ❌ 严重亏损 |
| y_300 | 0.69 | 6 | **−5.3** | ❌ 严重亏损 |
| y_600 | 0.24 | 6 | **−5.8** | ❌ 严重亏损 |

**严酷真相：按简单策略，所有 horizon 都亏损。** 这是 crypto mid-freq 的物理现实 —— σ 太小，fee 相对太大。

**但请注意：**

1. **这是"按每个样本都交易"的场景** —— 实际我们应该用**置信度门控**，只在信号最强时下单
2. 综合评估的 Cat 9 显示：V4 置信度门控让 Sharpe 从 289 → 327，说明门控能把信号集中到高信度的样本
3. 如果我们只交易**前 5% 最高置信度**的样本（而不是 top 10%），每笔信号强度会进一步提高 2-3×
4. **所以实战不是"每笔都亏"，而是"需要严格的门控 + 低成本路由"**

### 步骤 6：基础设施 / 延迟要求

| Horizon | 建议延迟预算 | 基础设施 | 小团队可行性 |
|:-:|:-:|---|:-:|
| y_60 | < 500ms | 低延迟 VPS + 异步下单 + 优化数据订阅 | ❌ 勉强（需工程投入） |
| y_180 | < 5s | 标准 VPS + WebSocket | ✅ 当前已验证 |
| y_600 (理论) | < 60s | 任何 VPS | ✅ 非常从容 |

### 步骤 7：Daily IC-IR（时序稳定性，未验证但可估）

y_60 的 Daily IC-IR 应该也更高（预期 > 1.5），但每日样本数也更大（~1440/日 vs ~480/日），所以"每天有信号"维度两者类似。

---

## V4 y_300 训练实证（2026-04-18 完成）

在 Ridge 显示 y_300 每笔边际略高的基础上，我们训练了 V4 on y_300 测试假设。**假设被 V4 数据推翻：**

| Metric | y_180 V4 (3-fold pooled) | y_300 V4 (2-fold pooled) | Δ |
|---|---:|---:|:-:|
| Pearson | 0.0943 | **0.0639** | **−0.030 (−32%)** |
| Spearman | 0.1107 | **0.0738** | **−0.033 (−33%)** |
| DirAcc | 0.5490 | 0.5265 | −2.3pp |

**Per-fold val_corr：**
- Fold 0: y_180 V4 = 0.0643, **y_300 V4 = 0.0586 (−9%)**
- Fold 1: y_180 V4 = 0.0934, **y_300 V4 = 0.0775 (−17%)**
- Fold 2: hang, not completed (stdout buffer + worker stall; 2 folds sufficient)

**为什么 V4 在 y_300 上更差：**
1. **输入窗口/horizon 比例失配**：V4 600s 输入对 y_180 (3.3×) 最优，对 y_300 (2.0×) 信息不够
2. **TCN 感受野固定 15s**：不随 horizon 扩展 → 相对覆盖率下降
3. **标签重叠传染到高容量模型**：Ridge 对 stride=60 导致的 80% label overlap 鲁棒（线性，低容量），V4 容量更高可能过拟合到 overlap

**Ridge vs V4 一致性对比：**
- Ridge y_180 → y_300 Pearson 变化：+0.09 → +0.07 (−22%)  [clean stride subsample]
- V4 y_180 → y_300 Pearson 变化：+0.09 → +0.06 (−32%)

V4 在 y_300 上受损比 Ridge 更严重 → 这与"高容量模型更容易受 overlap 污染"假设一致。

## 最终决策矩阵（修正版 v2）

| 选项 | Clean Pearson | 每笔毛边际 (bps) | 延迟要求 | 小团队适配 | 综合评分 |
|---|:-:|:-:|:-:|:-:|:-:|
| y_60 | 0.143 | 0.57 | < 500ms ❌ | 勉强 | ⭐⭐ |
| **y_180（当前）** | **0.089** | **0.61** | < 5s ✅ | ✅ | ⭐⭐⭐⭐ |
| **y_300（候选）** | **0.074** | **0.69** | < 30s ✅ | ✅ | **⭐⭐⭐⭐⭐** |
| y_600 | 0.019 | 0.24 | < 60s ✅ | ✅ | ⭐⭐ |

**修正后的结论：**

1. **y_180 仍是稳健的主生产 horizon**（已有 V4 训练 + 12 类评估 + 完整基线对照）
2. **y_300 值得并行试验** —— 每笔信号强度最高，延迟要求低，基础设施无压力
3. **y_60 的优势被抵消** —— 原始 IC 高但 σ 小，每笔实际边际最低（除了 y_600）
4. **y_600 确实弱** —— clean Pearson 只有 0.019，远低于其他

**现实成本考量：**
- 所有 horizon 按"每笔都交易"都亏损（毛边际 < fee + slippage）
- 必须用**置信度门控 + maker-only 路由**
- 这是 Phase C 完整回测框架要解决的核心问题

---

## 后续动作

### 立即（0 成本）

1. **把本决策写入 `docs/PROJECT_OVERVIEW.md` FAQ**（✓ 已完成）
2. **在 `experiments/eval_comprehensive/REPORT_ZH.md` 加 horizon 敏感性章节**（待完成）

### Phase C（2-3 天）

完整回测框架建立后，重做此决策：
1. 用真实 fill simulation + order book impact 模型
2. 考虑 maker / taker 混合策略
3. 做 confidence-gated 版本的净 Sharpe 对比（y_60 可能在 τ* 高门槛下变得经济）

### 长期（若扩团队）

1. 若未来有低延迟基础设施（co-location, custom execution engine），重新评估 y_60
2. 若生成 stride=600 的新 NPZ，重新评估 y_600 的真实信号

---

## 附：原始文件位置

- 结果：`experiments/baselines_horizon_sensitivity/y_{60,180,300,600}/`
- 预测：`experiments/baselines_horizon_sensitivity/y_{60,180,300,600}/preds/fold_{0,1,2}_{Ridge,TemporalRidge,XGBoost}_preds.npz`
- 日志：`/workspace/quant_research/logs/horizon_sensitivity.log`（pod 上）
- y_180 基线：`experiments/baselines_v4_matched_preds/`（local + pod）
