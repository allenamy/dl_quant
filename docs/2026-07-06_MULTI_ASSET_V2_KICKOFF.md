# 多资产 v2 — 中频横截面 long-short 创新因子 · 启动计划

> **创建:** 2026-07-06 | **分支:** multi-asset-v2 | **状态:** in-progress (Phase-0) | **作废条件:** 被后续里程碑取代
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

## 5. 约束（继承）
src/ 单资产代码只读;新代码 multi_asset/;share data + btcusdt_copy 只读(mode="r");本地改码 rsync server 训练;无泄漏;单 GPU 串行 GPU exclusivity;kill-gate 不放松;推理零 regime 后验切换。
