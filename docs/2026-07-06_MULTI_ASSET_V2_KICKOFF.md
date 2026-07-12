# 多资产 v2 — 中频横截面 long-short 创新因子 · 启动计划

> **创建:** 2026-07-06 | **分支:** multi-asset-v2 | **状态:** ★阶段完成 (2026-07-08 收口, 交付=docs/2026-07-08_multi_asset_v2_portfolio_scorecard.md) | **作废条件:** 被后续里程碑取代
> **最终交付: 两本审计过的净成本可交易 book — Book-1(大币 funding_ema+M0 DL 混合, net-Sh@2bps 4.56, BE 41) + Book-2(宽 SIZE sleeve); 跨book corr +0.08 分散实证; ~160 候选因子空间权威地图。**
> **前置:** 单资产 y_600 已收口(`docs/2026-07-06_SINGLE_ASSET_PERP_Y600_CLOSEOUT.md`);方法论/工具/Run1 底盘复用(`run1_reference_package`)。

## 0. 北极星（与用户 brainstorm 明确）

**做 14 币 USDT-perp 的中频(1h 起)横截面 long-short,以"净成本可交易"为北极星。走杂交路线: DL/ML + 跨领域知识构建创新因子(edge 所在) + 稳健横截面组合 + 显式成本控制。**

- **路线判定**：因子为核 + DL 增强 > 纯端到端 DL（单资产实测端到端撞天花板+难交易；中频横截面因子范式更可靠/主流/可归因/可控成本）。
- **edge 定义（可量化）**：**创新因子在"商品化因子基线"之上的 增量正交 IC + 净成本组合贡献。** 传统因子无壁垒;我们只投资"正交增量"。
- **北极星指标**：横截面 long-short 净成本 Sharpe / IC-IR(主) + 增量正交 IC(因子验收)。
- **horizon**：1h 起(+2h 稳健性)。

## 1. 因子弹药（按 差异化×可行性）
1. **1s 微结构 → 中频因子**(最硬数据 edge;复用单资产时序编码器作因子构造器): OBI 持续性/成交尺寸漂移/盘口补充速度/Kyle-λ 趋势/1s 实现波动期限结构。
2. **跨资产网络/关系**: lead-lag、订单流溢出、横截面背离、BTC-beta 残差。**★BTC 高精度 Tardis 25 档作 alt 的领先驱动**(诚实: 单资产 lagged BTC→alt 600s 弱~0.02,需 guard-first 早测 1h+微结构状态版)。
3. **自监督表示学习**(3 年无标签 1s 预训练 → embedding 即因子;门槛高别人少做)。
4. **跨领域**: 信息论(熵/互信息)、Hawkes 点过程、频域/小波(因果)、变点/regime。
5. **funding/OI**(y180 唯一未测 IC 杠杆): funding 差分、OI 动量、funding×微结构交互、分粒度。

## 2. 因子研究流水线（每个候选过五关，防低 SNR 过拟合）
1. 横截面 IC + IC-IR;
2. **增量正交 IC**(基线残差上,横截面,OOS —— 同事残差思路,但组合用联合重拟合非裸加);
3. 正交性/相关矩阵(去冗余);
4. walk-forward 门(Ridge/浅模型,ΔIC≥阈值才入库);
5. 净成本组合贡献(day-1 判)。
**创新因子先过 Ridge 门再上 DL;gated + 双人验证。**

## 3. 复用的方法论铁律（单资产带来）
- IC 是 alpha / β 是量纲;口径纪律(clean/dense/clip/raw-y);净成本回测判可交易;guard-first + 预注册 kill 门 + 双人验证 + gated flag;容量匹配信号 + 加通道惩罚 + Ridge-before-DL。

## 4. Phase-0（地基,多 CPU/Ridge 不烧 GPU）
- **★ GO/NO-GO 门**: 1h 横截面 long-short 商品化基线,净成本可交易吗?(y180 说 180s 不可交易;1h 待实测;不可交易→换更长 horizon)。
- 步骤: ① 盘点复用现有 infra ② 14 币 1s→1h 面板(as-of 无泄漏)+ BTC Tardis 25 档接入 ③ 商品化因子基线 + 横截面 Ridge → 基线净成本 Sharpe + 残差 ④ 因子工厂评分器(五关) ⑤ beta-projection 底板 + BTC→alt lead-lag 早探。

## ★ Phase-0a 结果 (2026-07-07): NO-GO on 快微结构基线 —— 但诊断重定向方向

**1h 横截面 long-short 快微结构基线 NOT 净成本可交易**: break-even **0.408 bps/side**, 每档水下(连 maker~1)。1h xsec rank-IC +0.0066 / IR 1.15(真实但薄, ~10× 低于 10min 的 0.0744)。

**三诊断(决定性)**:
1. 6× 换手摊薄救不了: 1h IC 小 ~10× 抵消 6× 成本节省有余 → 成本主导(同 y180);
2. EMA 平滑反更差: 1h 信号无可平滑持续性(一周期,混陈旧权重反号)→ 逼满换手;
3. **★ "1h→延迟容忍"假设证伪: 1h alpha 3min 衰减 50%/6min 80%, 同 y600. 延迟容忍是"特征"属性非"目标 horizon"属性 —— 慢目标配快特征照样延迟敏感.**

**战略重定向(诊断指向)**: 问题不在 horizon 在"特征太快"。**可交易中频横截面 alpha 更可能在 慢/持续因子(多小时动量、funding/OI 差分、basis、regime),非快微结构。** 张力: 我们数据 edge 是快微结构,但可交易信号要慢持续因子(相对更商品化)。→ edge 三候选: ① 微结构累积成慢信号(慢 positioning/liquidity regime, DL 学慢 state) ② **funding/OI 差分(y180 唯一未测 IC 杠杆, 天然慢/持续/延迟容忍 —— 可能最对)** ③ 微结构作执行择时叠慢 alpha 之上。**下一测(待用户方向确认): 慢持续因子基线(多小时动量/反转/波动 + funding/OI)1h 净成本 GO/NO-GO.**

## ★ Phase-0b 结果 (2026-07-07): B 慢价格因子 = NULL(印证研究), A 无数据阻塞

**B(慢价格因子基线) = NULL/NEGATIVE**: pooled xsec ridge rank-IC −0.005 / IR −0.80(n=2760, 因果验证 leak-free, 真 null 非泄漏)。逐因子: 动量全负(mom_4h −0.010→72h −0.024, **1h 大币是横截面反转非动量**), rev_1h/3h 弱正(+0.013/+0.014), vol/beta/等 max|standalone|~0.028, **符号跨 fold 不稳→组合 anti-generalize**。→ 印证研究预警(慢价格因子 14 大币消失/微市值驱动)。**B 残差≈0 → A 因子的增量正交 IC ≈ standalone IC(干净基线)。B 是打靶对象非赌注。**
**A 前置 = 无数据阻塞(good)**: funding/OI/positioning 数据全历史可得(data.binance.vision BULK 归档, 非 30 天 REST 限)。BTC metrics 2023-02→2026-06(覆盖面板): OI/top-trader 持仓比/账户比/global 账户比/taker vol 比; funding 全历史。→ funding-carry + positioning-divergence 在 2024-06..2025-09 可建。0B 自主推进: 扩 2 dump 脚本到 14 币 → 对齐(funding 8h/metrics 5m ffill≤t)→ 建 2 因子(因果+shuffle-null)→ 报 standalone IC。**A = 真赌注,决定性数字在路上。**

## ★ Phase-0b/A 结果 (2026-07-08): funding 杠杆 REAL, positioning NULL —— 净成本 gate 待定

**A funding 因子(leak-clean: ffill≤t sentinel PASS, 覆盖~1.00, shuffle-null done):**
- ★ **funding_ema(24h 平滑 funding): standalone IC −0.0186, z=−2.50, 3 fold 符号一致(−0.0035/−0.0373/−0.0150)** —— 负=crowding-reversion(高 funding→低未来收益)= 论点成立每 fold。**赢家。**
- funding_carry(raw): −0.0173, z=−2.89, 噪(fold0≈0); EMA 平滑帮(8h 高自相关)。
- toptrader_pos: −0.0156, z=−1.97(边缘), 符号一致。
- **NULL: global_account(z=−0.74 bias 调后 null); pos_divergence(−0.0043, z=−0.27, 符号翻→NULL, 大币上失败-catalog 已预警自验); oi_mom/taker_ratio NULL。** 组合 7 因子 ridge +0.005/IR 0.87。
**诚实 caveat: ① shuffle-null 均值非零(14 资产持续因子小样本横截面 bias)→ z vs 经验 null 才是诚实显著性(funding_ema/carry 过, global/pos_div 不过); ② regime 依赖(fold1-heavy −0.04 vs fold0≈0)。**
**关键洞察: |IC|~0.017 幅度温和(似 fast-micro 0.0066, ~4× 干净于 B 的符号不稳噪声), 但 funding 的差异化在 净成本-via-低换手(8h stamp+24h EMA→延迟容忍)。**

## ★★ GO (2026-07-08): funding_ema 净成本可交易 —— 第一个真信号, 五关全过

**funding_ema L/S 净成本 gate(纯低换手, honest raw-y): ★ BREAK-EVEN = 18.83 bps/side(α=0.02, turnover 0.027)—— 每档 GO(maker~1/2, taker~2.5/5), 清 taker~5 约 4×。** EMA 帮(break-even 随换手降而升 α0.5→10.2/α0.02→18.8, gross 正=真持续性, 反 fast-micro)。**LATENCY-FLAT: decay 1.00→1.05(180s)→1.05(360s) 不衰减(vs fast-micro 0.49/0.21)。** rank-IC +0.0186 IC-IR 3.16 gross Sharpe 2.33 mono +0.60(信号在极值: 多最低-funding/空最高-funding=crowding-reversion 经济自洽)。
**★ 五关工厂全 ACCEPT(基线 B=slow null): (a) xsec IC +0.0186 z=3.7; (b) 增量正交 IC over B +0.014 z=3.28(BEYOND 商品化基线=edge); (c) 正交 corr −0.029; (d) walk-forward Ridge ΔIC +0.0171 3-fold 符号一致; (e) 净成本贡献 加 funding 使 book BE −0.76→+3.87, net-Sharpe@2bps −12.2→+0.82。**
**诚实 caveat: ① regime-依赖幅度(fold1-heavy dIC 0.030 vs 0.008/0.013)但符号每 fold 一致(方向稳强度变); ② 信号集中 funding 极值(中间噪,交易尾部); ③ 7 因子组合也名义 GO(BE 34)但噪(null 因子快换手污染)——纯 funding_ema 是干净杠杆+推荐。**
**★★ 里程碑: 单资产 y600 non-taker + fast-micro 1h NO-GO + 慢价格 NULL → 但 funding_ema 差异化杠杆 IS 净成本可交易(BE 18.8, latency-flat, 持续性友好)。因子工厂 work, 第一个真因子清关。GO on funding 方向 → 建因子书(funding 为 base 叠正交因子)。**
**★ 全-fold 稳健(加固 GO, 解 regime caveat): 逐 fold 净成本@2bps BE = 9.04/46.74/8.07 bps/side, net-Sharpe +0.75/+7.74/+0.72 —— 三 fold 全净成本正、全清 taker~5。fold1 最强(dislocation 大)但非单-regime 海市蜃楼: funding_ema 每个 regime 都可交易, 只是强度变。诚实解: regime-依赖幅度但全-fold 净成本正。**

## 因子书增长 (2026-07-08): funding-family REJECT, signed-flow NULL, funding 2h 更强

**funding-family(vs funding_ema base): 全 REJECT。** fund_carry(corr 0.81 near-dup, 无增量, 伤 OOS, 降净成本); toptrader_pos(corr 0.36 正交但 gate-b 增量 z=0.92<2.5 + gate-d ΔIC −0.0056 伤 OOS = 正交但非增量)。工厂抓两种失败模式(重复 + 正交非增量); net-cost 单独不可靠(toptrader d_be +50.6 是噪声, b/d 正确否决)。**positioning 轴穷尽于单个干净杠杆。book 暂单因子。**
**★ 累积签名订单流(微结构轴) = NULL(leak-clean, coverage 1.00)。** 窗扫: ofi_cum_8h best raw IC +0.0068 但 z=+0.41(在持续因子 null 带 null_mu +0.0047 内, NOT 显著); 2h/4h/24h 全 flip。**null-mean-bias landmine: IC-vs-0 会误看真, 经验-null z 正确 kill。** 对比 funding_ema z=−2.50(真) vs signed-flow z=+0.41(null)。印证 catalog"累积签名流=边际, 成本敏感"。微结构在 1h 不加正交 alpha(印证快微结构衰减主题)。
**★ 2h 稳健确认 funding_ema(good): 2h standalone IC −0.0249(强于 1h −0.0186), 组合 ridge +0.0099/IR 1.15(vs 1h +0.005/0.87)。8h-stamp 慢 funding 预测 2h 更好 —— funding_ema 非 1h artifact, 是真慢信号, 且 2h 可能是更好 horizon。**
**★ 2h 净成本 gate(双人): fund_ema_h7200 BE = 33.82 bps/side(vs 1h 18.83), 清 taker~5 约 7×, net-Sharpe 每档正(含 c=10), mono +0.70(净于 1h 0.60), latency-flat。→ funding book 在 2h 明显更强, 2h 可能是首选 horizon。** order-flow 五关双人 REJECT(gate-a z1.1/gate-b 增量 z0.62/gate-c corr −0.034 正交但 gate-d ΔIC −0.0104 伤/gate-e d_be −18): **正交但无信号(正交必要非充分, gate-b/d 抓 null)。微结构-flow 轴 14 大币 1h 死。**
**★ 已 REJECT 全表: slow-price(null)/fund_carry(冗余 0.81)/toptrader(非增量)/order-flow(正交但 null)/combined(污染)。工厂 work: 一个真因子, 其余全正确 kill。BOOK = 单因子 funding_ema, horizon-robust(1h BE 18.8/2h BE 33.8, 全-fold 正)。**
**诚实读: funding_ema 可能是此 universe 唯一干净净成本杠杆 —— 强单因子 book(BE 18-34, 2h 更优)而非多因子栈。**
**semivar/signed-jump 判决(2026-07-08): 基本 NULL**(skew_4h/8h flip z<1.4; rv_24h null)。唯一边缘 skew_24h(z=−2.30 <2.5 门槛, 反转味大概率叠 B 反转轴, 0C 增量确认中)。**微结构轴接近穷尽确认。**
**semivar_skew24 终判 REJECT(2026-07-08): 过 a/b/c(真正交, 非反转重复)但 gate-d walk-forward FAIL(−0.008)+gate-e FAIL —— pooled 增量 IC 不迁移 OOS。方法论: gate-b pooled 乐观, gate-d 才是真门。**
**★ GBDT 交互探针(DL 轨道 stage-1) = NULL(2026-07-08): LightGBM 吃全部 94 特征(44快+20F2+15慢+7funding+4oflow+4semivar), funding-残差目标, 双跑(含/不含 funding 交互)全 null(z −0.37/−0.55, fold 不一致), 泄漏守卫干净。→ 表格特征无非线性增量; DL stage-2 只剩原始序列赌注(待用户 sign-off)。**
**★ Alpha-101+GTJA-191 库扫完成(2026-07-08): 96 公式, 预注册门(|z|≥3+fold一致)→ 3 边缘幸存者: a101_044(价量背离, z4.70, 全fold正, 唯一有戏), gtja_046(MA反转, z4.43, fold0≈0 watch-d), a101_045(价量corr, z3.63, fold0 弱)。044/045 likely 同簇(~2 个信号非 3)。★主导 pattern: 多个价格公式 pooled-z≥3 但 fold 翻号(价格-量轴在大币上的签名: pooled 显著 fold 不稳)。工厂终审(gate-d+换手陷阱)进行中; 全拒→价格-量轴权威关闭。**
**★★ 价格-量轴权威关闭(2026-07-08): 库扫 3 幸存者工厂全 REJECT。** 全部过 a/b/c(standalone 显著+pooled 增量显著 z2.8-3.7+对 funding 正交)但**全部 fail gate-d walk-forward(ΔIC≤+0.001 多为负)+gate-e(d_be 全负)** —— pooled 增量不迁移 OOS, semivar 教训 4× 确认。96-way 选择虚推 standalone z(4.7>funding 2.5), gate-d 每次抓住。3 个两两 corr 0.22-0.28(非马甲, 独立地各自失败)。
**★★ 最终图景: funding_ema = 此 universe 唯一净成本杠杆(1h BE 18.8/2h BE 33.8, 全fold正, latency-flat)。表格/库因子空间穷尽**(positioning/order-flow/semivar/慢价格/GBDT-非线性/96库扫 全 null-或-不泛化)。**强单因子 book, 真实/差异化/horizon-稳健。**
**剩余两赌注(自主 mandate 推进): ① 扩 universe 60+ 币(No-regret, √N 放大唯一真因子, 全 CPU, 数据可得 —— 最高 EV) ② DL stage-2 原始序列(用户 edge 主张, 单次纪律实验, 预注册 kill 门, GPU 闲置)。funding book(2h primary)收口交付无论如何做。**

## ★★ 双重突破 (2026-07-08 PM): 宽 universe 复活证实 + DL 原始序列有信号

**① 宽 universe 复活(N=110 point-in-time, 140/140 dump, 13176 小时 bar): 14/20 因子复活**(|z|≥2.5 经验null + 3fold 符号一致; vs 14 大币全 null)。**N=14 确是结构性约束。** 簇(~5 个独立): ★短期反转最强(mom 全族反转 z −8.9~−14.5, rev_1h/3h +11); 价量(gtja_046 z+15 顶因子, a101_044 +6.6 复活); MAX/lottery +5.0; 低波 +3.5/2.8; 换手/size +3.9/+2.7。**★意外: funding_ema 宽上不复活(z+1.7 fold 翻)—— 两个 universe 携带不同 alpha: 大币=funding 拥挤(集中度效应), 宽=价量因子动物园(文献小币因子主场)。**
**诚实 caveat: ① 复活的是商品化因子(基线非 edge; edge=在其上的增量) ② 净成本张力: 最强簇(反转)=最快换手(1-3h)+最小币(最宽 spread)=快微结构成本陷阱风险; 慢复活者(168h 反转/低波/size)才是净成本友好。0C tercile gate 判生死(gate 需适配宽面板变动成员)。**
**② M0 DL 探针 fold-0 PASS 预注册 gate: test xsec rank-IC +0.0298, IC-IR 2.84, σ 0.023 健康, kill 未触发(val ~0.04 ≫ 0.005)。→ 原始序列携带 funding 之外的横截面信号。fold1/2 继续; 0C 工厂=验收。stage-2b(多头正交因子挖掘器: 双路径+小时粗上下文+K 正交头+因子级验收)构建中, M0 完成后 GPU-serial 启动。**

## ★ Book-2 存在 (2026-07-08): 宽 universe 慢溢价净成本可交易; 反转簇成本陷阱

**宽净成本 tercile gate(per-coin 成本 top/mid/bottom DVOL=2/5/10 bps/side, commit c46cf2f):**
- **可交易(慢溢价): max_ret_24h(lottery) NET Sh +0.97/BE 9.4/换手 0.09; rvol_24h(低波) +1.02/9.9/0.09; size_dvol +2.11/BE 219(!)/换手 0.002(防弹)。**
- **成本陷阱(最强 IC 但快换手×小币): rev_1h NET −17.7(BE 0.57); gtja_046 −6.0; mom_168h −0.97 边缘。** 同快微结构逻辑的宽版重演: gross IC 最大的簇被换手杀。
**→ Book-2 = {低波+lottery+size} 慢溢价组合书, N=110, 与大币 funding book 不相交、可叠加。** Caveat: ① 单因子 net-Sh +1~2 温和, 3 因子较正交(vol/lottery/size)等风险合并应抬升 ② illiquid 假设 10bps 或低估(真小币 spread 20-50)→ 压力重跑中(max/rvol BE 9-10 边际薄; size 防弹) ③ size 换手 0.002 但小币容量有限。
**★ Book-2 定版(2026-07-08, commit 8907040, 0C 复核中): 合并书(低波+MAX+size 等风险) gross Sh 2.62(分散抬升), NET-Sh 1.41 @base(illiq 10bps), 换手 0.078, BE 12bps/side, ★per-fold [3.17,1.91,1.92] 全正 walk-forward 稳健。**
**成本压力(illiq 10/20/30/50): 低波破 ~25bps; MAX 破 ~22; ★size 防弹(1.96@50bps, 换手 0.0018); 合并破 ~30bps。→ 诚实定性: Book-2 真实/稳健/可交易, 但 ① 成本敏感(真 spread 20-30bps 则 net-Sh 0-0.7) ② 压力下 size-锚定(低波/MAX 脆) ③ 容量受限(信号在 illiquid tercile ~$2.5M 日均量, 5-10% ADV cap → 单位数 $M 小 sleeve)。**
**格局: 两本诚实的小书 > 一本 —— Book-1(大币 funding, 差异化, 容量较深) ⊥ Book-2(宽慢溢价 size-锚定小 sleeve), 组合天然分散。**
**0C 双人复核 CLEAR(2026-07-08): 0B 方法干净(分层成本+压力+per-fold+因果成员 mask, 算术一致)。两条解释性 caveat: ① 合并书 headline 1.41 在乐观成本端(illiq 10bps 轻; 真实 20-30bps 往返 → 合并 0.71/0.02 边缘化) —— **book-2 ≈ SIZE-主导慢书**(size 任何成本档都过, 其余脆); ② 容量: 信号住 illiquid tercile($2.5M ADV)→ 小 sleeve。**净读: Book-1 funding = 主书(差异化+horizon-稳健+容量可扩), Book-2 = 真实但容量受限的 size-溢价分散 sleeve。**

## ★★★ M0 DL 因子真 ACCEPT (2026-07-08 audit-clean): DL edge 验证, funding book → 2 因子

**M0(Conformer, 原始 44ch 序列, funding-残差目标)五关全过 + 6 项泄漏审计全 PASS(证据制):** 窗口 [t-599,t] 无未来; y_3600 前向零重叠+funding 因果 ffill; train-only 归一(seq_panel_dataset:135-167); 训测 22 天 gap+EMBARGO; **★口径 parity 独立复算: 新鲜 ≥3600 非重叠网格 IC=+0.0355/n_ts 2640 与 0C 精确一致(z 非重叠虚推)**; 日内窗口无跨日。
**⚠ 排掉一个 landmine: M0 导出的 panel_ref.CL 是 ~720s 密网格(继承 seq_cache), 在其上 naive z 5.3→11.2 虚高 —— 0C 用了 funding 的 ≥3600 CL 避开(ACCEPT 有效); 0B 修正标注, stage-2b 导出 CL 用 ≥3600。**
**判决: +0.0355 真实/口径正确/walk-forward 稳健/无泄漏。数字: standalone z7.03, 增量 over funding +0.0334(z6.64), corr 0.107, gate-d 3fold 一致, book BE 32.4→44.2 net-Sh@2bps 4.14→4.61; M0 standalone BE 33.6, mono 1.000, EMA-持续, 延迟保留81%@3-6min。★GBDT-null 指对: 表格无非线性, 时序/路径结构里有 —— Conformer 挖到了。stage-2b(K 头正交挖掘器)启动。**

## stage-2b 判决 (2026-07-08): 5 头全 REJECT vs [funding+M0] —— book 定格 2 因子, 转收口

**K=5 正交头逐个过多基线工厂(0C 扩展至 joint-baseline, 自验证: M0/funding 自身 vs book 正确 REJECT corr=1.0):** 全 REJECT。head_1 standalone 显著(z2.84)但与 M0 冗余(corr 0.181, 增量 z1.27); **head_2 近失手(过 a/c/d/e, gate-d +0.0032 符号一致, 但 gate-b 增量-over-book z −1.89)→ 记 watch(coarse-context 变体可能推过, 按预注册规则 park 不自动跑)。** 头间正交(−0.26..+0.29)但不转化为增量价值 —— 正交必要非充分, 全程一致的教训。
**解读: M0(单头)已吃掉 DL 原始序列 edge; 多头挖不出更多。大币因子空间 mined out @2 因子。**
**★ 收口(CONSOLIDATE): 最终组合 = Book-1(funding_ema+M0, 2h primary, net-Sh@2bps 4.61 BE 44) + Book-2(宽 SIZE sleeve, 小容量分散)。0C 出生产 scorecard(组合构造/净成本/逐月稳定/回撤/book 间相关验证/诚实边界), 0B 出生产因子管线。coarse/raw 变体 park 存档。**

## 5. 约束（继承）
src/ 单资产代码只读;新代码 multi_asset/;share data + btcusdt_copy 只读(mode="r");本地改码 rsync server 训练;无泄漏;单 GPU 串行 GPU exclusivity;kill-gate 不放松;推理零 regime 后验切换。
