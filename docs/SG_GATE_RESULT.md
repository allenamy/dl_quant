# SG Gate 结果 (2026-04-18)

> **结论：SG 不是通往 0.12 pearson 的路径。峰值 w=21 只给 Ridge +0.008 Pearson，远低于 +0.02 gate 门槛。**

## 背景

Phase B 的假设：在输入特征上应用 Savitzky-Golay 平滑（Wang et al. 2025 在 crypto LOB 上的 proven 方法）可以将 Ridge Pearson 从 0.088 → 0.12+，打破 V4 的信号地板。

## 实验设计

- **固定设置：** 匹配 3-fold walk-forward（700d train / 30d val / 90d test），y_180，`--use-last-timestep`
- **SG 参数扫描：** window ∈ {5, 11, 21, 31, 51, 101}，polyorder 随 window 递增
- **比较基线：** 无 SG Ridge P=0.0876, S=0.1099, XGBoost P=0.0944

## 完整结果表

| SG Window | SG PolyOrder | Ridge Pearson | Δ Ridge P | Ridge Spearman | XGBoost Pearson | XGBoost Spearman |
|:-:|:-:|---:|:-:|---:|---:|---:|
| no SG | — | 0.0876 | 0 | 0.1099 | **0.0944** | 0.1086 |
| 5 | 2 | 0.0905 | +0.003 | 0.1107 | 0.0480 ❌ | 0.1085 |
| 11 | 2 | 0.0897 | +0.002 | 0.1095 | 0.0719 | 0.1106 |
| **21** | **3** | **0.0956** | **+0.008** ⭐ | 0.1101 | 0.0797 | 0.1095 |
| 31 | 3 | 0.0916 | +0.004 | 0.1095 | 0.0614 ❌ | 0.1103 |
| 51 | 3 | 0.0820 ⬇ | **−0.006** | 0.1083 | 0.0873 | 0.1098 |
| 101 | 5 | ⏳ pending | ? | ? | ? | ? |

## Ridge Pearson 曲线（以 window 为 x 轴）

```
0.100 |              
0.098 |         
0.096 |         *    (w=21 peak)
0.094 |                   
0.092 |              *
0.090 |   *           
0.088 |      *     baseline---|
0.086 |                             
0.084 |                             *
0.082 |                          (w=51 跌破 baseline)
```

## 核心观察

### 1. 曲线呈倒 U 形，w=21 是 Ridge 最优点

从 w=5 → w=21 单调上升，从 w=21 → w=51 单调下降。这说明：
- **过少平滑（w=5, 11）**：对 1-second 采样的噪声抑制不够
- **适度平滑（w=21）**：噪声抑制最优
- **过度平滑（w=51+）**：把真实信号也磨平了，净效果变负

### 2. XGBoost 对 SG 非常敏感，且非单调

```
no SG: 0.0944  →  w=5:  0.0480 (砍半!)
                  w=11: 0.0719  →  w=21: 0.0797
                  w=31: 0.0614  →  w=51: 0.0873
```

Tree models 依赖原始高频特征的局部信号做分裂。SG 小窗口杀伤最大（破坏最有用的细节），大窗口反而部分恢复（因为整体信号被保留）。但 **没有任何 SG 配置让 XGBoost 接近 baseline 0.0944**。

### 3. Spearman 几乎不动

所有 SG 配置的 Ridge Spearman 在 0.109-0.111 之间 —— **SG 没有改善 rank 质量**，只影响幅度预测。

### 4. DirAcc 也不动（54.9% ± 0.2%）

## Gate 裁决

| 标准 | 阈值 | 实际 | 结果 |
|---|:-:|:-:|:-:|
| Pass（Pearson ≥ 0.11） | +0.02 提升 | +0.008 | ❌ 未达 |
| Fail（Pearson < 0.09） | 明确失败 | 0.0956 | ❌ 未达 |
| **Marginal（0.09-0.11）** | 中间区 | **0.0956** | ✅ 符合中间区 |

**Gate 结论：Marginal 胜出 —— SG 有微弱正面效应，但不够打破 V4 的 Pearson 地板。**

## 战略建议

### ❌ 不推荐 Phase B 完整版

理由：
- 即使将 Ridge 从 0.088 提升到 0.096（仅 +0.008），V4 的 DL 放大效应大概率只有 +0.005-0.015 Pearson
- 预计 V4 最终 Pearson 在 0.10-0.11，**仍未达 spec 0.12**
- 投入 3-4 天工程（NPZ regen + V4 retrain）获得 ~+0.01 Pearson 的 ROI 太低
- XGBoost 明显受损，说明 SG 不是 "all-horizon 的免费午餐"

### ✅ 推荐 Option C（V4 y_300 训练）

理由：
- Ridge 在 y_300 上有微弱的每笔边际优势（0.69 bps vs y_180 的 0.61 bps）
- 需要测试这一点能否在 V4 上复现
- 成本固定（12-15 小时 pod），信息回报明确
- 如果 y_300 V4 也不显著好于 y_180 V4，那我们就知道**信号天花板来自数据本身**，需要更激进的动作（新数据源、新特征、完全不同的模型）

### 未来可选探索（不紧急）

1. **其他平滑方法**：Kalman filter, EWMA 在某些金融场景比 SG 更好
2. **特征选择**：Ridge 64 特征可能有冗余，用 Lasso 或 Ridge β-权重剔除低贡献特征
3. **非线性特征交互**：Ridge-informed polynomial interactions（spec 已有模块但未使用）
4. **新数据源**：扩展到 ETH、其他交易所的 LOB

## 保留工件

- 实验数据：`experiments/baselines_sg_sweep/sg_w{5,11,21,31,51,101}_p{2,2,3,3,3,5}/`
- 每个目录含 `baseline_results.json` + `preds/fold_{0,1,2}_{Ridge,TemporalRidge,XGBoost}_preds.npz`
- 复现命令：
  ```bash
  python3 -m src.baselines.evaluate_baselines \
    --npz-dir data/npz_v4 \
    --output-dir experiments/baselines_sg_sweep/sg_w21_p3 \
    --device cpu --train-days 700 --val-days 30 --test-days 90 --fold-stride 60 \
    --horizon-key y_180 --mask-key y_mask_180 --use-last-timestep \
    --sg-window 21 --sg-polyorder 3
  ```
