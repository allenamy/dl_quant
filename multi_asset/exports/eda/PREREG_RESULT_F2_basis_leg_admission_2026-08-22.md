> **创建:** 2026-08-22 07:0xZ | **Session:** 6737834a-F2 | **状态:** 预注册冻结(§P 段 SHA 见侧车 `.prereg.sha256`, 先于数字)→ 结果待回填 | **作废条件:** 主线对"去 funding 主导"研究总线(`docs/DESIGN_optimization_path_2026-08-21.md` §3.7)作出裁定后由新日期文件取代并互链; 09-01 重训后以新权重重跑; STATE.md §3 永远优先

# F-2 · basis/溢价载体腿的正式录取(简单口径 · 实盘相位 · 400 宇宙)—— 预注册 + 结果

**动机受据(引用前已打开):** `docs/DESIGN_optimization_path_2026-08-21.md` §3.7(用户 08-22 "全力研究如何摆脱 funding 的主导"; F-2 = 08-09 预注册的 basis⟂funding 在简单口径 S1/S2 于 400 宇宙; 过 ⇒ 以预注册腿进影子)· FF `RESULT_funding_factor_deepdive_2026-08-22.md` §2.1(U140: basis 原始 4h IC −0.0194 (t −15.9) / ⟂funding −0.0210 (t −16.9), **5/5 年同号**; 双排序: 价格反应属于 basis 不属于 funding 水平; "400 宇宙需 premiumIndexKlines 扩面")· RC `RESULT_conclusion_reaudit_simple_caliber_2026-08-22.md` §3.1(在役管线 S2 预读: C2 w.05 **LOG S1 Δ+0.048 过 G 族, SIM 仅 +0.005 fail** ⇒ "08-26 正式 S2 必须按简单口径, 预读 = 不过")· WA `kcurve_2026-08-21/RESULT_wide_full_caliber_audit_2026-08-22.md` §2.1(宽书 W-b d30 简单口径 净@2 1.785 bps/锚 / 夏普 1.668 [0.726, 2.608]; **去 fund 腿 0.803 / 0.664 [−0.275, 1.599]**; fund 腿 2024-26 占净额 62%)· `PREREG_breadth_round2_basis_2026-08-09.md`(C1/C2 定义、sign −1 由机制定、无自由参数)· `PREREG_leg_admission_v2_2026-08-09.md` §3(G0 尺子/G1/G2/G3/G4; 同槽位同权重安慰剂 5 种子)· 记忆 `breadth_round2_basis_orthogonalised`(关三 0.126 vs 0.403; 内部最优 w≈0.15 是事后读数, 部署前须另立预注册 —— 本文即是)· `difference_is_not_residual`(正交 = 逐锚 LSQ 残差, 不是相减)。

---

<!-- PREREG-BEGIN -->
## P. 预注册(冻结段; 本段 SHA256 先于任何数字入库)

### P.0 一句话机制
Binance 永续的 **premium index = (永续标记价 − 现货指数价)/现货指数价**(`premiumIndexKlines` 1h close), 是"合约 vs 现货"溢价的连续读数; funding 只是它的 8h/4h **离散化 + 封顶**版本(费率 = clamp(平均溢价 + clamp(利率−溢价), ±cap))。溢价 > 0 ⇒ 多头付费 ⇒ 拥挤做多 ⇒ 短期反转 ⇒ **sign = −1(机制定, 不搜)**。把溢价对 funding 水平 **与 king 分数**做逐锚 LSQ 残差, 剩下的 = funding 机制在结构上表达不了(越顶/盘中/结算间)且 king 没学到的"合约−现货"价格反应; 本文问它能不能在 400 宇宙、简单口径、实盘相位上**作为第四腿**录取, 以及它能否**补足/替代 fund 腿**。

### P.1 对象、数据、口径(全部继承 WA, 零改动; 只加第四槽)
- **对象**: 宽书 **W-b 链**(WA 装置 `kcurve_2026-08-21/devices_2026-08-22/wide_full_caliber_audit.py` `run_chain` 语义, 本装置 import 其函数并写一个 K 腿推广 `run_chain_k`; **收据 R1**: 第四腿权重=0 时 `run_chain_k` 权重 ≡ WA `probe_artifacts/wa/wa_weights_Wb_d30.npz` 逐锚逐名 max|Δw| < 1e-6, 且基线净@2 锚级夏普(2022-01..2026-06)= WA 的 **1.668**; 对不上照实报、不调和、不出结论): 三腿 king = slow LGBM OOS(`pod_backup_2026-08-21/slow_pred_hist_oos.npy`)/ rev24 = −`f_rev_24h` / fund = `f_fund_ema_v1`(`wide_panel_4h_hist_v2.npz`); 截面秩 z ∈ [−0.5, 0.5] → 走前 msharpe(900 锚, Sharpe 负截 0)→ 逐腿 over-sel 去均值 / L1 / cap 2.5/n / 再归一 → 止损 d30_n2_c42(EMA 前置零)→ EMA α0.1 → 带 2.5e-4; 宇宙 = 宽成员 ∩ qv4h ≥ 2.5e5("400 宇宙", 逐锚均 ~251 名); 无目标锚(sel<80)持仓不动。
- **数据**: WA 自建 1h 收盘网格 `probe_artifacts/wa/close1h_829.npz` 与逐结算资金费 `funding_829.npz`; 4h 简单收益 RET = C(T+4h)/C(T) − 1; 锚 T ∈ {00,04,…,20}Z, 持仓窗 (T, T+4h](**实盘相位**)。**basis 数据(新)**: `data.binance.vision` `futures/um/monthly/premiumIndexKlines/<sym>/1h` 月度 zip(2021-01→2026-07, 829 名按各自上市跨度拉取; 下载器 `devices_2026-08-22/f2_pull_premium_829.py`)汇成 `probe_artifacts/f2/premium_1h_829.npz`(ts_hour = bar open ms, 与 `basis_premium_1h.npz` 同约定); **收据 R2**: 与 08-06 fapi 拉的 140 名 `basis_premium_1h.npz` 在重叠格上 Pearson ≥ 0.999 且 |Δ| 中位 < 1e-6(对不上 ⇒ 报, 并以 fapi 140 为准复核 140 子集)。不拉现货 K 线: premium index 本身就是 perp−spot 指数差, 现货腿已在其中。
- **记账**: WA `account()` 语义 —— 价格 pnl = Σw·RET(简单); carry = 逐结算实现(结算时刻 ∈ (T,T+4h] 作用于 w(T)); 成本 = c × Σ|Δw|(单向意图换手, NAV 份额), **主臂 c = 3.52**, G 族用 **4.137 / 6.23**(本装置在 WA COST_ARMS 上追加 6.23); **净@2** = 每锚按 2/Σ|w| 缩放(恒定 gross 2, 主口径), 权重原样并报。
- **统计**: 锚级夏普 = 均/σ×√2190(主), 日聚合 ×√365 并报; 夏普 CI = 42 锚块自助 2000 次, 臂间 ΔSharpe = 配对块自助; G 族 Δ净 CI = RC `gfam` 逐字(5 锚块, 2000 次, 种子 41)。
- **跨度**: 主 = 2022-01-01 00Z → 2026-06-30 20Z(WA "2022-01..2026-06", 9,852 锚; 2021 只作 msharpe 暖机); 并报 FULL(→2026-08-15)、2022-23、2024-26、逐年。

### P.2 候选(事前列死; 只此 6 个形态, 主臂 1 个)
- **取值时点**: 锚 T 用 open = T−1h 的 1h bar close(该 bar 于 T 收盘, ≤N; FF/RC 同约定 "PREM 行 N−1h")。
- **变量族**(逐名, 严格 ≤T): `B0` = 溢价水平 PREM(T); `Bema24` = PREM 小时序列 EMA(α = 2/25, 跨度 24h); `Bchg24` = PREM(T) − PREM(T−24h); `Bz168` = (PREM(T) − mean_168h)/sd_168h(≥84 个有限小时, 否则 NaN)。
- **正交化**(逐锚, 在当锚 sel 成员且各量有限的名上; 记忆 `difference_is_not_residual`: 估计的投影, 不是系数=1 的相减): y = rank-center(B*), X = [1, rank-center(`f_fund_ema_v1`[T]), rank-center(`f_fund_now`[T]), rank-center(SLOW[T])] ⇒ LSQ 残差 r ⇒ 候选 = **−rank-center(r)**(sign −1 固定; `+1` 臂只作机制诊断, 永不用于录取)。
- **六形态**: **`BASIS_OK`**(B0 ⟂ {fund_ema, fund_now, king}; **主臂**)· `BASIS_OF`(B0 ⟂ fund_ema 仅; = 08-09 C2 在宽面板上的同构)· `BASIS_RAW`(−rank B0; = 08-09 C1, 诊断)· `BASIS_OK_ema24` / `BASIS_OK_chg24` / `BASIS_OK_z168`(变量族, 同正交化)。
- **刷新节奏**: 主 = 4h(与宽书三腿同, 平滑由 EMA α0.1 承担; 宽书组装 `PREREG_wide_book_assembly` 已否 8h 节奏); 并报 8h 保持臂(04/12/20Z 复用上锚候选, 08-09 预注册口径)仅作连续性对照。
- **缺失处理**: 某名当锚无 basis ⇒ 候选 NaN ⇒ 经 xz→nan_to_num 记 0(中性, 不持仓), 与三腿 NaN 处理同; 报 basis 对 400 宇宙的逐锚覆盖率(名数份额与 gross 份额)与无数据名单。

### P.3 S1 · 排序门(FF `s1_gate` 逐字; 400 宇宙; 主跨度)
逐锚 m = sel ∩ 有限{K, cand, RET}(≥30 名): dIC = Spearman(0.7·z(K) + 0.3·z(cand), RET) − Spearman(z(K), RET); 年份取 ≥100 个有效锚; **PASS ⇔ 逐年 dIC 均值之均值 ≥ +0.003 且每年 ≥ 0**。并报: cand 自身 IC、cand 对 king 残差(RET 秩对 K 秩单回归残差)的 IC、king IC、2022-23 / 2024-26 拆分; 6 形态 + `+1` 诊断 + 8h 臂全部报, **录取只看主臂**。

### P.4 S2 · 净额门(同管线第四腿; G 族 RC `gfam` 逐字; 净@2 序列; 主跨度)
- **臂**: (F) 固定权重 w4 ∈ {0.10, **0.15 (主)**, 0.20}: 三腿权重 = (1−w4)×走前 msharpe 三腿份额, basis = w4; (M) 四腿走前 msharpe(900 锚, 负截 0, basis 腿纯价格收益序列与三腿同法); 止损 **d30_n2_c42(主)** 与 S0 并报; 底座 = WA W-b 同形态(`base`)。
- **去 fund 腿情景**(用户核心问题): 底座 `nofund` = king+rev24(msharpe 份额重归一, WA 同式, 夏普 0.664); 臂 `nofund+basis`: w4 ∈ {0.10, 0.15 (主), 0.20} 与 M(三腿 msharpe over {king, rev24, basis}); 止损 d30/S0。
- **G 族**(每臂 vs 各自底座): Δ = 净@2_臂 − 净@2_底座 逐锚; **PASS ⇔ Δ@4.137 的 5 锚块自助 CI95 下界 > 0 且 Δ@6.23 均值 ≥ 0 且逐年 Δ@4.137 ≥ 0 的年数 ≥ 4/5 且 夏普@4.137 臂 ≥ 底座**; 并报 Δ@3.52、ΔSharpe(42 锚块配对自助 CI)、换手、腿级归因(WA 腿级可加分解推广到 4 腿)、Q4(等权市场五分位最差档 / |市场| 最高档)、2022-23 / 2024-26 / 逐年。
- **尺子(腿录取门 v2 G0/G1)**: 同槽位同权重安慰剂 = 主臂候选逐锚横截面随机置换(种子 0–4 固定), 走同一条链(d30, w4=0.15, full 与 nofund 各 5 条): **G0** 安慰剂 ΔSharpe 均值 |·| < 0.10 ⇒ 尺子可用(不过则不出具录取判定, 只报); **G1** ΔSharpe(真) − mean ΔSharpe(安慰剂) > 0 且真臂 ΔSharpe 的 42 锚块配对自助 CI 下界 > 0; 全部 5 种子逐个报。
- **换手归因(G4 必报)**: 增益若来自降换手而非升毛额, 分开陈述。

### P.5 录取与判读规则(先写)
1. **录取**(= "过 ⇒ 以预注册腿进影子"): 主臂 `BASIS_OK` · 固定 w4 = 0.15 · d30 · 全书 同时过 **S1 PASS + G 族 PASS + G0 可用 + G1 > 0**; 任一不过 ⇒ 不录取。w4 0.10/0.20、M 臂、S0、其他形态**只报不录**; 若某非主臂过而主臂不过 ⇒ 记"候选形态, 须另立预注册", 不得当场改主臂。
2. **去 fund 腿问题**(独立读数, 不影响录取): 报 `nofund+basis`(主臂 w4 0.15 d30)净@2 夏普与 `nofund` 0.664 的 Δ 及 CI; 对照 §3.7 阶段判据 "去 fund 腿书夏普 ≥ 1.0 且逐年 ≥4/5 非负" 逐字读; 并报 `nofund+basis` vs `base`(三腿含 fund)—— 回答 "basis 能替代 fund 腿吗"。
3. **三选一措辞**: G 族与 G1 都过 = "录取(进影子)"; S1 过而 S2 不过 = "排序有、净额无(第五例)"; 都不过 = "判负"。数字对不上收据(R1/R2)⇒ 只报不判。

### P.6 四问(逐条留痕)
- **口径**: 简单持有收益 [T,T+4h] / 逐结算 carry / 3.52 主 + 4.137/6.23 G 族 / 净@2; basis 来源 vision(R2 对 fapi 140); 退市名只要在成员且有收盘就参与(与三腿同); 无 basis 名在 basis 腿记中性, 覆盖率单列。
- **泄漏**: basis 取 open T−1h 的 bar(T 收盘); 诊断臂: (i) 取 open=T 的 bar(T+1h 才收盘, 未来 1h)的 S1 IC —— 若显著大于主臂则本族对时点敏感(报警, 非门); (ii) 取 T−4h 的陈旧值 —— 衰减画像; 正交化只用 ≤T 的 fund/king。
- **选择效应**: 变量族/正交化集/权重网格/主臂/止损/节奏全部在本段定死; 同槽位安慰剂 5 种子; 不搜 sign/EMA 跨度/cadence。
- **regime**: 逐年 5 年 + 2022-23 vs 2024-26 + Q4(等权市场五分位/|市场|最高档)+ 去 fund 腿情景逐年。

### P.7 预期方向(先写, 会红的方向)
- S1: 依 FF U140 IC −0.02 (t −16, 5/5 年), **预期主臂 S1 PASS**; 若 400 宇宙稀释到 <+0.003 ⇒ "载体只在大币有排序"。
- S2 全书: 依 RC(在役管线 SIM S2 w.05 仅 +0.005)与记忆"排序≠净额"四例, **预期 G 族边缘或 fail**(basis 是"空高溢价名"sleeve, 简单口径凸性在空头侧); 若 PASS 则是简单口径下第一条新腿。
- 去 fund 腿: 预期 `nofund+basis` > 0.664 但 **< 1.0**(basis 与 fund 腿 ρ 低, 增量真实但量级小); 若 ≥1.0 则阶段性达标, 须红队(w4 网格内单调性 + 安慰剂)。
<!-- PREREG-END -->

---

## R. 结果(待回填; 本段在 §P 冻结并入库之后写)
