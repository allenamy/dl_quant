> **创建:** 2026-08-22 07:1xZ | **Session:** 6737834a-F1 | **状态:** 预注册冻结(§P 段 SHA 见 git commit 信息, 先于任何数字); 结果段待回填 | **作废条件:** 主线对"摆脱 funding 主导"研究总线(路径文档 §3.7)作出裁定后由新日期文件取代并互链; 09-01 重训换代后以新 king 重跑; STATE.md §3 永远优先

# F-1 · 宽书 king 剥离 funding 输入(ablation)+ 三腿配权归因 —— "去 fund 腿"书 0.66 的缺口有多少来自 king 自己吃了 funding、多少来自 msharpe 把权重推向 fund 腿

**任务来源:** `docs/DESIGN_optimization_path_2026-08-21.md` §3.7 F-1(用户 08-22 06:4xZ "全力研究如何摆脱 funding 的主导"); 阶段判据(总): "去 fund 腿"书夏普 0.66 → ≥1.0(简单口径, 逐年 ≥4/5 非负)。
**受据(引用前已打开):** WA `kcurve_2026-08-21/RESULT_wide_full_caliber_audit_2026-08-22.md`(§2.1 去 fund 腿 0.664 [−0.28, 1.60] / 减半 1.336; §2.4 腿级归因 fund 腿 2024-26 占净额 62%; 装置 `devices_2026-08-22/wide_full_caliber_audit.py` SHA `9792ecd0…808b`, 权重链 W-b)· FF `RESULT_funding_factor_deepdive_2026-08-22.md`(地基没歪腿歪了; 宽 fund 腿证书半伪影)· king 训练协议 `kcurve_2026-08-15/devices_2026-08-21/pod_slow_hist_folds.py`(逐年扩张 OOS 折, 2020 起)+ 特征构造 `pod_fea_wide_hist.py`(5m 7 通道 × 5 窗 × {值, 秩} + fund_ema/fund_now)+ 缓存构造 `runpod_scripts/workspace_mirror/pod_build_wide_ext.py`(通道定义)· CX `PREREG_RESULT_convexity_aware_construction_2026-08-22.md`(同一条 W-b 链上加钩子的先例与收据 R1 形式)。记忆: [[wide_book_final_form_verdict]] [[wide_book_carry_correction]] [[leak_taught_momentum_crutch]](输入里的"拐杖"要用 ablation 实测, 不用推断)[[judge_device_must_outlive_verdict]]。

**★ 先澄清一个前提(团队口径):** 宽书 king(slow-LGBM)的输入**不是**宽 4h 因子面板的 zoo 列(f_rev_4h/24h/3d, f_mom_7d/30d, …)—— 那是 rev24/fund 腿与 zoo 的面板; king 的输入是 `wide_fea_hist`: 5m 缓存 7 通道(ret5/range/cpos/log_qv/log_cnt/log_avgsz/tbf)× 5 窗(48/288/864/2016/8640 bar = 4h/1d/3d/7d/30d)的滚动统计各取 {值, 逐锚秩} 共 80 列 + vol 5 窗 ×2(含在 80 内)+ **fund_ema、fund_now 两列**(来自 `wide_panel_4h_hist.npz`), 去掉 ret5_sum_48/288(v,r)后 **78 列**。funding 进入 king 的通道**只有这两列**。

---

<!-- PREREG-BEGIN -->
## P. 预注册(冻结段; 本段 SHA256 先于任何数字入库)

### P.0 三个问题与阶段判据
1. **king 去 funding 输入后还剩多少**: 同协议重训的"去 f_fund_* king"的 OOS IC(两口径)与三腿书/去 fund 腿书夏普, 相对同协议重训的基线 king 与 WA 的参考 king。
2. **去 fund 腿书多少**: 用去 funding 输入的 king + rev24(走前 msharpe 两腿重归一)+ 止损层 d30 的书, 简单口径净@2 夏普、逐年。
3. **配权是不是主因**: 走前 msharpe w3 vs 固定等权 vs 固定 (0.45/0.45/0.10) 下 fund 腿对净额的贡献占比与"去 fund 腿"的夏普损失。
**阶段判据(冻结, 来自路径文档 §3.7)**: 去 fund 腿书 = **K2(去 funding 输入 king)+ rev24, 走前 msharpe 两腿, 止损 d30_n2_c42, 净@2, 2022-01-01 → 2026-06-30**: 锚级夏普 **≥ 1.0 且 逐年夏普 ≥ 0 的年数 ≥ 4/5**(2022/23/24/25/26H1)⇒ "阶段达标"; 否则报缺口 (1.0 − S) 及来源分解(P.5)。

### P.1 对象、数据、口径(全部继承 WA, 零改动)
- **链**: WA 装置 `wide_full_caliber_audit.py`(SHA `9792ecd0…808b`)的 `run_chain` 语义 —— 三腿 king / rev24 = −`f_rev_24h` / fund = `f_fund_ema_v1`(`wide_panel_4h_hist_v2.npz`); 截面秩 z ∈ [−0.5, 0.5] → 走前 msharpe(900 锚腿纯价格收益, 负夏普截 0, 归一)配三腿权重 w3 → 逐腿去均值(over sel)/ L1 / cap 2.5/n / 再归一 → 止损 d30_n2_c42(EMA 前置零)→ EMA α0.1 → 带 2.5e-4; sel = 收益有数 ∧ qv4h ≥ 2.5e5; 2021-01 暖机, 2022-01 起记录。本装置以**带 w3 钩子的逐语句副本**实现(新增 w3_mode: `equal` / `fixed_45_45_10` / `king_only` / `rev24_only` / `fund_only`; 原有 `base`/`no_fund`/`half_fund` 逐位不动), 其余记账/读数函数(`account`/`summarize`/`series_block`/块自助/五分位)直接 import WA 模块。
- **收据 R1(先于一切)**: 本装置在 king = K0(WA 参考 king)、w3_mode=base、d30 下的权重 ≡ `probe_artifacts/wa/wa_weights_Wb_d30.npz`(逐锚逐名 max|Δw| < 1e-6)且净@2 锚级夏普(2022-01..2026-06)= WA 的 **1.668**; no_fund 臂 = WA 的 **0.664**(`Wb_d30_nofund`)。对不上照实报、不调和, 且不得出任何结论。
- **数据**: WA 自建 1h 收盘网格 `probe_artifacts/wa/close1h_829.npz`(829 名)与逐结算资金费 `funding_829.npz`; 4h 简单收益 RET = C(T+4h)/C(T) − 1(= expm1 对数), 锚 T ∈ {00,04,…,20}Z, 持仓窗 (T, T+4h](实盘相位); 记账 = WA `account()`: 价格 Σw·RET − 逐结算实现 carry − 3.52 bps × Σ|Δw|(敏感 4.137/6.64 并报); **净@2**(恒定 gross 2)主口径, 权重原样并报; 锚级夏普 √2190 主, 日聚合 √365 并报; CI = 42 锚块自助 2000 次(seed 11), 臂间 Δ = 配对块自助(seed 7)。
- **跨度**: 主 = 2022-01-01 → 2026-06-30 23:00(WA "2022-01..2026-06"块); 并报 2022-23、2024-26、FULL(→ 本装置缓存末 2026-08-10 20:00)。

### P.2 king 重训协议(继承 `pod_slow_hist_folds.py`, 唯一改动 = 特征列表与固定种子)
- **5m 缓存(hist, 2020 起)**: pod 的 hist 缓存(2020-01 起)只存在于已不可达的 pod 上, 本装置重建: [2020-01-01 00:05 → 2021-12-31 23:55 从 data.binance.vision 月度 5m zip 重建, 通道定义 = `pod_build_wide_ext.py` 逐字(ret5 = clip(pct_change, ±0.3); range = clip((h−l)/c, 0, .5); cpos = clip((c−l)/(h−l), 0, 1); log_qv = clip(log1p(qv), 0, 25); log_cnt = clip(log1p(cnt), 0, 20); log_avgsz = clip(log(qv/cnt), −5, 15); tbf = clip(tbqv/qv, 0, 1); 行 ts = open_time + 5min), 名单 = WA 1h 网格 2020/2021 有数的 139 名(其余 690 名 2020-21 不存在)] ⊕ [jpline `w3lane/kcurve/data/dlnative_5m_wide829_f16.npz` 2022-01-01 00:00 → 2026-08-11 00:00(= pod 同代码同源缓存)], 边界行 2022-01-01 00:00 的 ret5 用 2021-12-31 23:55 / 2022-01-01 00:00 收盘重算(jpline 缓存首行 pct_change 为 NaN), 其余通道不动。
- **锚/成员/目标/qvk = pod hist meta 原样**(`pod_backup_2026-08-21/wide_fea_hist_meta.npz`: E_ts 12,985 锚 2020-09-11 → 2026-08-15, members K400 同筛, y4 = Σ ret5 48 bar(≥46 有数), qvk), **截到 E_ts ≤ 2026-08-10 20:00**(本装置缓存可完整覆盖的最后锚); 特征值按 `pod_fea_wide_hist.py` 逐字在本装置缓存上重算(40 值列 × {v, 逐锚成员内秩 r} + fund_ema/fund_now ← `wide_panel_4h_hist.npz` 行 T, nan→0), 去 ret5_sum_48/288 ⇒ **78 列**。
- **收据 R0(缓存/特征同源性)**: (a) 用本装置缓存按 pod 代码重算的 y4 vs pod meta y4, 全部共同锚·名: max|Δ|、|Δ|<1e-6 占比(2020-21 段单列); (b) 按 pod 代码重算成员 vs pod members: 逐年完全相同锚占比; (c) 2022+ 段缓存与 jpline 缓存逐位同(同一文件)。R0(a) 2020-21 段 |Δ|<1e-6 占比 < 99% ⇒ 重建缓存与 pod 不同源, 结论全部标"传闻级"。
- **模型**: `LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=24, verbose=-1, random_state=0)`(pod 未设种子; 本装置两臂同种子 0); 目标 = 锚内 y4 秩 rankdata/(n−1) − 0.5; **折** YV ∈ {2022, 2023, 2024, 2025, 2026}, train = 年 < YV(≥20,000 行), test = 年 = YV; OOS 预测矩阵 (nA × 829), 成员外/训练年 NaN。
- **臂**: **K0** = pod 参考 `slow_pred_hist_oos.npy`(WA 的 king, 只读); **K1** = 基线重训(78 列); **K2** = 去 funding 输入重训(76 列: 去 fund_ema、fund_now); 预注册"臂二 = 去 f_fund_* 及任何费率派生列": 本特征集里**不存在**其他费率派生列(7 通道全是价量), 故臂二 ≡ K2, 照实声明, 以 **K3** 代之 = K2 分数逐锚对 funding 族 [xz(f_fund_ema_v1), xz(f_fund_now × 8/f_fund_iv)] 截面 OLS 残差(成员内, ≤T 信息)—— 度量"去列后 king 经相关价量列对 funding 的残余渗透"。
- **收据 R2(复现)**: K1 vs K0 逐锚 Spearman 均值 ≥ 0.90 且 K1 的逐年 IC(y4 口径)与 `slow_hist_folds.json` 各年差 ≤ 0.006 ⇒ "同协议复现成立"; 否则 K1/K2 的绝对水平标传闻, 只读 K2 − K1 的差。
- **IC 口径**: (i) 逐锚 Spearman(pred, meta y4) 年均(协议平价); (ii) 逐锚 Spearman(pred, RET 1h 简单 (T,T+4h]) 年均(交易口径, 实盘相位); (iii) 臂间逐锚 Spearman 均值 K1–K0 / K2–K1 / K3–K2 与书级净额序列 Pearson。

### P.3 特征族重要性(A · king 内部)
- **族**: FUND = {fund_ema, fund_now}; RET = {ret5_sum_{864,2016,8640}_{v,r}}; VOL = {vol_{48,288,864,2016,8640}_{v,r}}; RANGE = {range_mean_*}; CPOS = {cpos_mean_*}; LIQ = {log_qv_mean_*, log_cnt_mean_*, log_avgsz_mean_*}; TBF = {tbf_mean_*}。
- **SHAP**: LightGBM 原生 `pred_contrib` 在每折 OOS 行随机子样本(≤200k 行, seed 0)上; 族份额 = Σ_{f∈族} mean|φ_f| / Σ_all mean|φ|; 逐折与合并; K1 与 K2 各报。
- **置换重要性**: 对每族, 每折 OOS 锚内把该族全部列**联合同序置换**(同一锚内同一置换作用于族内各列; 保留截面边际分布, 切断与名的对应), 重打分, ΔIC_族 = IC(原) − IC(置换)(y4 口径, 锚均; 逐年与合并; seeds 0/1/2 平均); K1 全族, K2 非 FUND 族。读法: ΔIC_族 ≥ 基线 IC 的 25% ⇒ "主要族"。

### P.4 腿级独立书(A · 腿层)
- 通过同一条链以 w3 one-hot(`king_only` / `rev24_only` / `fund_only`; 即同一管线: xz → 去均值/L1/cap/再归一 → 止损 d30 → EMA → 带)生成三条单腿书(d30 主, S0 并报); king 用 K0(主)与 K2(副)。报净@2 均值/夏普/CI/逐年/maxDD。与 WA §2.4 的三腿书内可加分解(另一个量: 腿在三腿书内的份额)并列, 不混用。

### P.5 书级臂(B)
- 对 K ∈ {K0, K1, K2, K3}: (a) 三腿 msharpe d30(base); (b) **去 fund 腿** = w3_mode no_fund(king+rev24 msharpe 重归一)d30; (c) half_fund d30; (d) (a)(b) 的 S0 版。Δ(vs K0 同形态)= 配对块自助。
- **阶段判据**见 P.0(K2 (b))。K3 (b) 同两门并报, **不替代判据**。
- **次读**: 三腿(K2) vs 三腿(K0) Δ夏普: CI 上界 < 0 ⇒ funding 输入实质承载 king alpha; |Δ| ≤ 0.10 且 CI 含 0 ⇒ king 一阶上不依赖 funding 输入。
- **缺口来源分解**(若判据不过): 去 fund 腿书 S(K2) 相对 1.0 的缺口拆为 [king 去 funding 的代价: S_nofund(K0) − S_nofund(K2)] / [rev24 腿弱: rev24_only 单腿夏普与 king_only 之差的贡献] / [fund 腿缺席: S_base(K0) − S_nofund(K0) = WA 0.97]; 三项按定义可加到基线, 只报各项数值, 不排序为"应做什么"。

### P.6 配权归因(C)
- king = K0(主)/ K2(副); w3 方案: 走前 msharpe(base)/ 等权 1/3 / 固定 (0.45, 0.45, 0.10); 止损 d30(S0 并报)。
- 读数: 夏普/逐年; **fund 腿贡献占比** = Σ 腿 fund 净 / Σ 书净(WA 可加分解), 2022-26 与 2024-26; w3_fund 逐年均值; 各方案下 Δ夏普(去 fund 腿 − 本方案)(等权/固定的去 fund 腿 = (0.5, 0.5, 0))。
- **冻结读法**: "msharpe 推高 fund 权重是依赖度主因" 当且仅当 (i) msharpe 的 w3_fund 2025-26 均值 ≥ 0.40(等权 = 0.333)**且** (ii) 等权方案下 |Δ夏普(去 fund 腿)| ≤ 0.5 × msharpe 方案下 |Δ夏普(去 fund 腿)|。(ii) 不成立 ⇒ 依赖度是 fund 腿自身 2025-26 regime 的性质, 不是配权造成。

### P.7 四问(结果段逐条回答)
口径(简单/相位/成本/净@2/两 IC 口径)· 泄漏(特征 ≤T; 折 = 年 < YV; 置换/SHAP 只在 OOS 行; K3 正交化只用 ≤T 的 funding 列)· 选择效应(止损参数 d30 样本内 ⇒ S0 并报; 族定义与判据先冻结; 不挑种子)· regime(逐年 + Q4 市场五分位 + 2022-23/2024-26 分段)。
<!-- PREREG-END -->

---

## 1. 装置与收据(回填)

(待回填: 装置 SHA、输入 SHA、R0/R1/R2 读数)

## 2. 结果(回填)

(待回填)

## 3. 四问与白话(回填)

(待回填)
