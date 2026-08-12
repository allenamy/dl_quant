> **创建:** 2026-07-13 | **Session:** 0C independent scorer/auditor — supplementary-factor phase | **状态:** final (pre-registration, locked before any candidate scored) | **作废条件:** king 部署实现变更(base 列失效),或 wide panel/target 重建

# 补充因子验收门 — 预注册 (0C)

**目的:** DL 挖王座(lam_orth=0 + xattn, book ~0.084)之外的**正交增量**因子。核心纪律: **功劳只按增量算** —— 一个因子进书的价值 = 它在 [funding+zoo+king] 之上新增的、可交易的、稳健的 alpha,不是它自己的原始 IC。弱因子进书是**负贡献**(三腿 3-way blend 稀释案的教训: xattn 太强时掺 QIM/lamorth0 反降 0.0812<0.0835)。

**所有候选在同一协议评分,门在见任何候选结果前锁定。**

---

## 0. 基准列(正交化基础)—— 已就绪

- **king-pred 面板**: `exports/eda/king_pred_panel.npz`(0C 2026-07-13 建, `king_pred_panel_report.json`)。逐 ts×N 的**严格 OOS** king honest-ensemble 预测(每 ts 只用其所属 test-fold 的预测,**跨 fold 重叠 = 0 cell**)。覆盖 **2022→2026H1**(9851 clean-ts, 4h CL 网格, 中位 109 币/ts)。**gap: 2021 无 OOS king-pred**(2021 只当训练年)→ 候选评分窗 = 2022→2026H1。
- **[funding+zoo] 8 列 baseline**: `wide_dl_full.npz` 的 `baseline_cols` = [funding_ema, mom_24h, mom_72h, rev_1h, rvol_24h, size_dvol, max_ret_24h, beta_24h](逐 ts causal ≤t)。
- **正交化 base = 这 9 列**(8 baseline + king-pred)。逐 ts 横截面 ridge-OLS 残差化,**列先标准化**(避免 funding-leak landmine: 未标准化时重尾 funding_ema 欠 shrink 会留残差 loading)。

---

## 1. 验收判据(全部满足才 ACCEPT;任一不过 = REJECT/存档)

### (a) ★ king-正交增量 rank-IC(核心门)
- 候选 OOS 预测逐 ts 横截面对 base(9 列)残差化 → `cand_orth`;算 `cand_orth` vs YR(残差目标)的横截面 rank-IC。等价于控制 [funding+zoo+king] 后的偏相关(YR 已 ⊥[funding+zoo],故 ≈ 控 king 的偏相关)。
- **门: 增量 rank-IC ≥ +0.003(honest ensemble 口径),且逐 fold/逐年符号一致(无反号年)。** 5 年 walk-forward,pooled + 逐年都报。
- **显著性: day-block bootstrap(3000×)增量-IC 的 mean CI 排除 0。** (per-ts 显著易达成,承重是符号一致 + book 边际。)

### (b) pred-corr vs king < 0.7(厂规 c,冗余门)
- 候选与 king-pred 的逐 ts 横截面 rank-corr 均值 < 0.7。≥0.7 = 同信号,低先验,REJECT。(注: 此为**必要非充分** —— corr 低但增量 IC 不过仍 REJECT。pred-corr 预检的条件性教训: 只对同代干净臂可靠。)

### (c) ★ 书级边际(防稀释门,最硬)
- 构 value-blend [king + 新因子](各 per-ts z-score 后加权,#16: value 非 rank;权重先固定 50/50 与 best-of-grid 都报,但**判据用固定 50/50 防 val-fit**)。
- **门: blend 的净 rank-IC vs king 单独,逐年配对 day-block bootstrap 显著为正,且无年显著变差。** 弱因子即便增量-IC 微正,进书若稀释 king → REJECT。这是终判门(a 是必要,c 是充分)。

### (d) 动态占比 ≥ 0.5 + 泄漏审计
- 增量信号 shuffle-future 动态分解: dynamic share ≥ 0.5(防静态 tilt 灌水,尤其 metrics/positioning 通道)。
- 泄漏审计照旧: 输入通道严格 ≤t;fold 边界 embargo 无重叠;panel byte-check(md5 == king panel 185d3b65);honest ensemble 非 best-head;若含 cross-asset attention → mask 同期 member-only ≤t(经典泄漏位)。metrics/positioning 通道额外: 发布延迟对齐(funding/OI 有结算延迟,须用 ≤t 的已发布值,非未来结算值)。

### (e) 净成本贡献
- 新因子换手画像单独测(4h 或其 horizon 再平衡 rank-L/S: turnover、BE、net-Sh)。
- **门: blend 相对 king 的净成本不恶化到抹掉增量** —— 报 blend 换手 vs king 换手,net-Sh@{2.3/5.0} 逐年 vs king。慢换手因子(如 24h horizon)天然占优。

---

## 2. 评分协议(所有候选同口径)

- **5 年扩张 walk-forward**(year_folds, wide_dl_full, embargo 8d),test 年 2022-2026H1(与 king-pred 覆盖对齐)。
- **honest ensemble**(z-score 后平均 K 头/预测,非 per-fold best-head)。
- **同 panel byte-check**(md5 185d3b65)。
- **YR{H} 残差目标**(候选 horizon 的 YR: YR4 / YR24 等);增量-IC 与 book-边际都在候选 horizon 的 YR + Yraw 双报。
- **σ/kill gate**: rank-IC checkpoint(σ 对任意尺度头无意义);fold0 floor kill 可选。
- **诚实口径**: raw 与残差 IC 都报;发现异常宁 flag 不粉饰;"好得惊人"必审计(dyn 分解 + 泄漏 + byte-check + 逐年配对)。

## 3. 候选臂(团队 EV 序,0B 建 target/通道后我评分)

1. **ARM-S2 24h-horizon 补充因子**(YR24 目标, 慢换手天然补 4h king; **输入含 7 metrics 通道 —— positioning/OI 在长 horizon 是未测用法**, 保留数据资产的复用点)。**评分注意: metrics 通道的 ≤t 发布对齐 + 长-horizon 的 dyn-share(慢因子易静态灌水,(d) 门吃紧)。**
2. **ARM-S1 同 horizon king-残差再挖**(4h, 测 1h/4h 是否还有 king 之外剩余 alpha)。**评分注意: 与 king pred-corr 大概率高((b) 门吃紧);(c) book-边际是真判据。**
3. **ARM-MIX 架构多样性**(与 king 0.54 已知不同下注,但架构本身非新信号源;(c) 门 + dyn 决定)。

## 4. 判词模板

每候选出: 增量-IC(pooled + 逐年 + bootstrap CI)/ pred-corr vs king / **book-边际(blend vs king 配对显著性)** / dyn-share / 泄漏审计 / 净成本 → **ACCEPT(进书)/ 条件 ACCEPT / REJECT(存档)** + 一句依据。**默认怀疑: 多数补充因子会死在 (a) 增量不足 或 (c) 稀释;真进书的稀。**

---
**基准产物:** `king_pred_panel.npz` + `king_pred_panel_report.json`(0C 已建)· base = 8 baseline + king-pred · 评分窗 2022→2026H1。


---

> **追加:** 2026-07-14 | **状态:** final (pre-registration v2, locked before any frontier candidate scored) | **作废条件:** 四腿书部署实现变更 / YR{H}B target 重建 / king 或 S2 OOS 面板重建

# 补充因子验收门 v2 — 前沿双臂 (25-26 范式, base=四腿书)

**背景:** 补充因子阶段第一轮收官 —— S2(24h)=1 ACCEPT 进书, S1(4h 再挖)+S3(168h 周级)+metrics-input 轴全存档. 现书 = **四腿** (funding / DL-king=xattn 4h / SIZE / S2-24h). 用户令: 在此残差上用 25-26 前沿范式 (默认候选 FinPFN in-context / StockMixer-MASTER, 调研 agent 定稿中) 再挖 2 臂. 本段沿用 v1 五门, base 更新为四腿书, 加**架构三专项** + **horizon 入门约束**. 门在见任何候选结果前锁定; 评分协议继承 v1 §2 (5 年扩张 walk-forward / honest ensemble / panel byte-check / day-block bootstrap / raw+残差双报 / 好得惊人必审).

## v2.0 基准列更新 — 四腿书 (0B 建 target, 我 verify)

- 正交化 base = **10 列**: 8 baseline (funding_ema, mom_24h, mom_72h, rev_1h, rvol_24h, size_dvol, max_ret_24h, beta_24h) + **king-pred** + **S2-pred** (S2 24h OOS honest-ensemble 面板; 我评分前 verify 其 md5 + ts 逐字节对齐 king_pred_panel).
- 目标 **YR{H}B** (0B 建): 候选 horizon H 的 Yraw 逐 ts xsec-demean → ridge-OLS 残差化 on [10 列], **列先标准化** (funding-leak landmine). ⇒ **IC vs YR{H}B 直接 = 书-正交增量** (承 S1 的 YR4K 逻辑: 目标已 ⊥ 四腿书 → 对残差目标的 rank-IC 就是控四腿后的偏相关).
- ★ **必报 corr(YR{H}B, YR{H})** —— 量化 king+S2 吃掉的维度. S1 先例 corr(YR4K,YR4)=0.989 (king 只吃 ~2%, 近满维, 增量无残差空间折损). 若此值明显 <0.99 = king+S2 已吃相当维度, 增量的"满维换算"须相应折; 直接影响 (a) 门解读. 双 target (YR{H}B 主 + 候选 horizon 的 YR{H} 交叉验证) + Yraw 都报.

## v2.1 五门 (base 更新为四腿书)

- **(a) ★ 书-正交增量 rank-IC** ≥ **+0.003**, 逐年符号一致 (无反号年), day-block bootstrap(3000×) mean CI **排除 0**. 口径 = IC vs YR{H}B (honest ensemble); 交叉验证 = 候选逐 ts 残差化 on 10 列 vs YR{H} 应吻合. pooled + 逐年都报.
- **(b) pred-corr 对 king 和 S2 都 < 0.7 (理想 < 0.4)** —— 冗余门. **任一腿 ≥0.7 = REJECT.** 慢因子的 S2-冗余是新增风险 (S3 教训: S3↔S2 pred-corr 0.152 才够格; 若前沿臂落 24h 带, S2-冗余吃紧). 必要非充分.
- **(c) ★ 书级边际 (最硬, 五腿装配非 pairwise)**: improve-rule Ss > ρ·S(4leg) + 五腿 value-blend. **过门 = 二选一: (i) pooled 五腿 Sharpe 提升 day-block bootstrap 显著为正; 或 (ii) S2-doctrine —— 对四腿全部低 corr + worst-year floor 抬升 + 小权重(0.05-0.15)单调改善 + 无年显著变差 (worst-year 保护).** S3 反例锁死: 独立周频 Sharpe 0.79 净 / 1.16 gross « book 5.90 → 混合 +0.06 CI 含 0 + w>0.10 转负 → FAIL. **附 breadth check (S3 lesson): 报独立 Sharpe(gross+net) + bets/年; breadth 饥饿 (bets/年 太少 → Sharpe 天花板 ~IC×√breadth) 须 flag —— 便宜执行 ≠ book 价值.**
- **(d) dyn-share ≥ 0.5 + 泄漏审计** (in-context 见 v2.2-iii). 输入 ≤t / fold embargo 无重叠 / panel byte-check / honest ensemble 非 best-head / cross-asset attn mask 同期 member-only ≤t.
- **(e) 净成本贡献** 不抹增量: blend 换手 vs 四腿书, net-Sh@{2.3/5.0} 逐年 vs 四腿.

## v2.2 ★ 架构三专项 (新范式臂必过, v2 新增)

- **(i) 归纳偏置差异实证** —— pred-corr vs king **≤ 0.36** (S1 同-arch 再挖测得的数, 作硬上界). 机理: 目标 YR{H}B 已移除 king; 一个**真正不同归纳偏置**的范式, 其残差预测对 king 应显著 < 0.36; 若仍 >0.36 = 在重学 king 结构 = "换皮再挖" (S1 教训, 存档). **低 corr 必要非充分** (aux 教训: 低 corr 不保证增量), 但高 corr 直接判死. [与 (b) 的 0.7 门叠加: (b) 是冗余底线, (i) 是"新范式"资格线, 更严]
- **(ii) 复杂度预算** —— 报 n_params + 有效训练样本 (clean 锚 × 均 N × folds) + params:sample + **相对 Conformer-ref(255,238 params) 的参数比**. 门: pooling 后 params:sample 仍在健康区 (Conformer 基线 = 已验证健康的参照点); 若 >5× Conformer 参数, 须证增量随容量 scale (非拟合噪声, 即容量↑而增量↑且 dyn-share 不掉). **Kill 信号 (过拟合签名): fold0 σ-collapse / 加容量后 dyn-share 掉 / fold jitter 放大 / val-test gap 扩.** (低-SNR 硬约束 #1: 容量须匹配信号, pooling 是杠杆非堆容量的借口.)
- **(iii) in-context 泄漏专项** (FinPFN / in-context-learning 类) —— 若"上下文 = 近期 (特征, 收益) 对": **(1)** 上下文每对的**收益必须在 t 前完全实现** (上下文锚时刻 + 其 horizon ≤ t), 上下文集**不含 test 点本身 / 同-horizon 重叠邻居** (in-context 经典事故位). 审上下文组装代码 + 边界. **(2) ★ 预注册 forward-window-decay 因果测** (QIM 用过的决定性 lookahead 判别, shuffle-future 抓不住 in-context 泄漏): 增量-IC 必须 **lag=0 峰 + 前向平滑衰减**; 若 IC flat 跨 lag 或负-lag 上升 = 上下文偷看未来 → 判死. 对任何带"检索近期样本"结构的臂**强制**跑此测.

## v2.3 horizon 入门约束

- 新臂 horizon **限 [4h, 24h] 带**. 阶梯已证 sweet band: **<4h → king 已饱和** (S1: 4h 再挖 pred-corr 0.36 book-hurt); **>24h → breadth 饥饿** (S3: 168h gross Sharpe 仅 1.16, 混合不显著). **不接受 168h+ 提案; <4h 拒.** 24h = 已知甜点 (S2 进书); 4h-12h 带在新范式下未测, 可接受. 每臂 intake 先报 horizon, 越界直接不评.

## v2.4 阶段判据 + 诚实先验

- **两臂各判 ACCEPT(进书, 五腿书) / ARCHIVE.** 判词模板同 v1 §4 + 架构三专项行.
- **★ 诚实先验 (预注册, 防凑数): S1/S3 先例 → 大概率 ≤1 臂进书; 0 臂进书是合法且有价值的科学结论** —— 证明四腿书在**现数据轴 + 现 horizon 带已 alpha-完备**, 前沿架构 (更强归纳偏置/in-context) 在此残差上无可交易增量, 剩余 EV 只在**新数据轴** (funding/OI 之外的正交信息源), 非架构/horizon. **不为"用户要 2 臂"接受边际臂**: (c) 书级边际是终判, (a) 增量是必要非充分, 架构三专项是"新范式"资格.
- 若某臂 (a)+(b)+架构三专项全过但 (c) 不显著 → 只有 S2-doctrine 成立 (低 corr + worst-year 保护) 才 conditional-accept; 否则存档 (S1/S3 均此路).

---
**v2 基准产物 (0B 建, 0C verify 后评分):** S2-pred OOS 面板 + YR{H}B target (H∈{4,24}) · base = 8 baseline + king-pred + S2-pred (10 列) · 评分窗 2022→2026H1 · 候选默认 FinPFN in-context / StockMixer-MASTER (待调研定稿).
