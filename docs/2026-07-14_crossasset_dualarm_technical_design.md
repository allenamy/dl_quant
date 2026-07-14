# 跨资产结构双臂 — 技术设计 (N1b 多关系注意力 + N1a 共动对比预训练)

> **创建:** 2026-07-14 深夜 JST | **Session:** fable multi-asset-v4 frontier | **状态:** draft (待 main 过目) | **作废条件:** main 否决设计 / 实施后由 arm 判词 milestone 取代
> 交叉引用: 调研判决 `docs/2026-07-14_frontier_v4_research_and_dualarm_design.md`; 基建 `exports/eda/{s2_pred_panel_cl4,yr4b_yr24b}_report.json`; 王座 `docs/2026-07-12_ENGINE_A_FINAL_MILESTONE.md`

## 0. 共主题与归纳偏置对照

**核心论点 (调研):** 方向 (alpha) 低 SNR，但**共动 (co-movement) 高 SNR**。王座的单层跨资产注意力 (CrossAssetAttnLayer, nhead=4, n_xattn=1) 用低-SNR 的 alpha 梯度**隐式**学跨资产结构 —— 学不满。两条**显式**把结构信号变密的路，归纳偏置不同、预期互补：

| | N1b 多关系注意力 | N1a 共动对比预训练 |
|---|---|---|
| 偏置 | 架构 (关系通道展宽) | 表征 (自监督预训练 encoder) |
| 结构来源 | 显式滚动相关先验 (多时标) | 未来共动自监督目标 |
| 推理参数 | 王座 +≤50k | 王座 (255k, 不变) |
| 工程量 | 便宜 (~1-2d) | 重 (~4-6d) |
| 实施序 | 先 | 后 |

**共用:** YR4B(CL4) 目标 (987k cells, 1:3.9) + `--year_folds_from 2023` + v2 验收门 + 0C forward-decay 因果测。互补假设: 两臂 pred-corr < 0.36 (v2 多样性门) → 都过 = 互补书腿; corr 高 = 一方主导 (亦 informative)。

---

## 1. ARM N1b — 多关系跨资产注意力 (先实施)

### 1.1 机制
王座的单层 xattn 之上，**加**一条门控的多关系 delta 通路，使 gate=0 时**恒等于王座** (天然 ablation)：

```
h_base = SingleXAttn(h, mask)                 # 王座原路 (不动)
h_out  = h_base + alpha * sum_k g_k * RelAttn_k(h, mask, B_k)
                  └─ alpha: 标量 gate, 零初始化 (off=王座)
                  └─ g_k = softmax(GateMLP(meanpool_member(h)))_k   # 输入相关的边混合权重
```

### 1.2 ★ K 关系边诱导方案 — 推荐: 滚动相关分桶 @ 多时标

**推荐 primary = 滚动相关分桶** (对比另两候选)：
- 边 k 的注意力加性偏置 `B_k[i,j] = zscore_ij( rollcorr(ret_i, ret_j; lookback L_k) )`，L = **{24h, 72h, 168h}** (K=3 边: 日内-中期-周)。相关用滞后收益 (≤t) 的 Pearson，逐 ts 截面 z 标准化。
- `logits_k[i,j] = (Q_k h_i)·(K_k h_j)/√d + lambda_k * B_k[i,j]` (lambda_k 可学标量)。
- **理由 (vs 备选):**
  - **(选中) 滚动相关分桶**: 直接编码高-SNR 的共动结构 (论点支点)，多时标覆盖不同 regime；因果、无需学图 (低-SNR 下学图=过拟合噪声)；机制可解释 ("谁在时标 k 上共动")；调研 A 级 crypto OOS (多关系注意力 IC 0.071) 的最数据-grounded、参数-最省实现。
  - **(备选1) 特征子空间边**: 各边不同 Q/K 投影 = 本质就是多头 self-attn，无显式关系先验，归纳偏置弱 —— 留作 primary 弱时的消融，不作首选。
  - **(备选2) 可学习软分组**: 学出的簇分配，参数多、在低-SNR alpha 上过拟合 —— 整个论点就是**避免**从噪声 alpha 学结构，所以否。
- 消融挂钩: `--n1b_edge_kind {rollcorr, subspace, group}`，默认 rollcorr。

### 1.3 门控混合
两级：(i) **边混合** `g_k = softmax(GateMLP(meanpool over members of h))_k` (输入相关，选"当前哪个时标重要")；(ii) **总门** `alpha` 标量，**零初始化**。delta = alpha · Σ_k g_k · RelAttn_k。

### 1.4 ★ 零初始化门 (天然 ablation)
`alpha` 初值 0 → 训练起点 `h_out = h_base` **逐字节等于王座单-xattn**。→ N1b(alpha=0) = 王座, 是内建 ablation；训练学着开门。若 alpha 训不起来 (留 ~0) = 多关系无增量的干净负结论。(同 DAQH q50 零初始化范式。)

### 1.5 参数预算 (≤50k 硬顶)
d=64。delta 通路：
- 每边 Q_k, K_k 投影: 若**跨边共享 V+out** 且每边独立 Q,K → 3×(2·d²)=3×8192=**24,576**；
- 若更省: 跨边共享 K-proj, 每边独立 Q → 3·d²(Q)+1·d²(K)+ (V,out 复用王座) = 4·4096=**16,384**；
- GateMLP (d→K): 64×3+3≈**195**; lambda_k: 3; alpha: 1。
- **合计 ~17-25k << 50k** ✓ (取共享 K-proj 版 ~17k, 留裕度)。

### 1.6 config
王座家族 (Conformer stem d=64 + 此多关系注意力替换/包裹单 xattn) + YR4B(CL4) + `--target_horizon 4` + `--dense_train` + `--year_folds_from 2023` + `--embargo_days 10` + seed 42。save_tag `wideA_n1b_multirel_c1`。损失=王座 stage2b (LambdaRankIC primary + mag Huber + lam_orth=0)。

### 1.7 因果 & 泄漏
`B_k` 来自滞后收益 (≤t 滚动相关)，无未来。0C forward-decay 因果测强制 (预测须现因果衰减签名, 负 lag 反号)。

---

## 2. ARM N1a — 未来共动 soft-contrastive 预训练 (后实施)

### 2.1 两阶段流程
**Phase 1 (预训练):** encoder + 临时投影头，在 fold-i 训练窗上以未来共动自监督目标训 encoder 的跨资产结构。
**Phase 2 (fine-tune):** encoder 用预训练权重初始化 + 接因子头 + xattn，全模型 fine-tune 到 YR4B(CL4)，王座损失。投影头丢弃。

### 2.2 ★ 共动标签定义
- **未来窗** H_f = **64 个 4h-bar ≈ 10.7 天** (够长得稳定相关估计, 够短保留多数训练锚点)。
- **相关度量**: 逐对 `C_fut[i,j] = Pearson( ret4h_i[t+1:t+H_f], ret4h_j[t+1:t+H_f] )` ∈ [-1,1] (member 对)。
- **soft-contrastive 损失 (推荐 primary = 相关匹配):**
  ```
  z_i = normalize(encoder(x_i))            # L2-归一 embedding
  S[i,j] = z_i · z_j                        # 余弦相似
  L_pre = mean_{i,j in member pair} ( S[i,j] - C_fut[i,j] )^2    # soft-target MSE
  ```
  直接把 embedding 几何对齐到未来共动 = 学出低-SNR alpha 学不出的结构。
- **备选**: InfoNCE-soft (目标分布 softmax(C_fut[i,:]/τ) 的交叉熵) —— 留作消融；primary 用 MSE 相关匹配 (稳、直接回归结构)。

### 2.3 ★ 逐 fold 预训练边界 (泄漏纪律, 最重)
- **逐 fold**: fold-i 的预训练**只用 fold-i 训练窗**数据。
- **未来窗完全落训练窗内**: 预训练锚点 t 须满足 `t + H_f ≤ train_end_i`；否则丢弃 → **边界丢弃量 = 训练窗末尾 H_f=64 bar ≈ 10.7 天/fold** (相对多年训练窗可忽略)。
- **因果论证 (0C 会审):** 未来收益**只作训练期自监督目标** (完全类比 fine-tune 标签 YR4B 本身也用未来收益)；**推理时 encoder 只吃 ≤t 输入窗** → 因果。预训练未来窗永不触 val/test (边界丢弃保证)。→ 推理管线严格 ≤t，0C forward-decay 因果测是最终强制验收。

### 2.4 冻结/解冻策略
Phase 2 推荐: **判别式学习率全解冻** —— encoder LR = 0.3× 头 LR (标准迁移: 保护预训练结构, 头快速适配 alpha)。备选: 头先热身 N_warm epoch (encoder 冻) 再全解冻。默认判别式 LR。

### 2.5 ★ 规避 aux-MTL 关轴
aux-MTL 轴 (alpha 主损失 + aux 头**联合**训) 已关 (共享 trunk 上 aux 头在 alpha 训练期反伤)。N1a 走**顺序**预训练 (预训练 → 再 fine-tune 到 alpha 单目标)，**非联合多任务** → encoder 在见 alpha 目标**之前**被结构信号塑形，然后只对 alpha fine-tune → 规避 aux-MTL 失败模式。共动目标从不与 alpha 损失同批出现。

### 2.6 预训练哪个 encoder (开放, 我推荐)
**推荐: 预训练王座单-xattn encoder** (非 N1b 多关系)，保两臂归因干净 (N1a=表征偏置单变量, N1b=架构偏置单变量)。若两者都过再考虑组合。

### 2.7 config
推理架构=王座 (255k, 预训练不加推理参数)。fine-tune: YR4B(CL4) + dense_train + year_folds_from 2023 + embargo 10 + seed 42。save_tag `wideA_n1a_comovepre_c1`。

---

## 3. 共享验收 & 实施序

- **目标**: YR4B(CL4) 987k (`yr4b_target.npz`, hook 格式)。24h 变体 `yr24b_target.npz` 备用。
- **v2 门 (0C):** 四腿书基准增量 + 归纳偏置差异 pred-corr ≤ 0.36 + horizon 4-24h + "0 进书合法"诚实先验 + forward-decay 因果测。
- **实施序**: N1b (便宜, 零初始化门=内建 ablation) → 判 → N1a (重, 预训练). 逐项报 main。
- **σ/kill 守卫**: 沿用 trainer 的 σŷ/σy≥0.02 gate + 可选 --kill_gates fold0 floor。

## 4. 开放问题 (待 main 裁定)
1. N1b 关系边: 滚动相关分桶 (推荐) 确认? K=3 @ {24,72,168}h?
2. N1b 参数: 共享 K-proj 版 (~17k) vs 独立 Q,K 版 (~25k)? (都 <50k; 我倾向共享省参)
3. N1a 未来窗 H_f=64 bar(~10.7d)? 损失=相关匹配 MSE (推荐) vs InfoNCE-soft?
4. N1a 预训练 encoder: 王座单-xattn (推荐, 归因干净) 确认?
5. 冻结策略: 判别式 LR 全解冻 (推荐) vs 头热身?
