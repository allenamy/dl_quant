> **创建:** 2026-08-22 07:0xZ | **Session:** 6737834a-F7(子代理, 路径文档 §3.7 F-7) | **状态:** §P 预注册 FROZEN(候选清单 + 门 + 收据写于任何 IC 读数之前; 冻结 SHA = 本文首个 git commit, 见 §0.1); 结果节 §1-§5 待回填 | **作废条件:** 同一候选在全宇宙数据(§A 可得性 B 级项拉齐)上重测后, 本文的"子集预读"一律失效, 以全宇宙读数为准
> **上游:** `docs/DESIGN_optimization_path_2026-08-21.md` §3.5(FF 地基审计)/§3.7(研究总线 F-1…F-6); 同口径姊妹装置 `devices_2026-08-22/funding_factor_deepdive.py`(FF, S1 定义出处); 用户原话 "从合约, 现货以及其他多种角度更深入地针对性地思考和挖掘"(目标: 摆脱宽书对 funding 动量腿的依赖)
> **边界:** 只读数据, 只写研究仓; 不碰 `~/dl_quant_live`; 不调交易 API(公共行情/归档端点可用: data.binance.vision, api.binance.com exchangeInfo); 简单收益口径 + 实盘相位 + 400 宇宙; **只报秩 IC 预筛, 不选臂不堆叠, 不做 S2**

# F-7 · 多角度非 funding 价格反应来源: 候选清单 · 可得性 · S1 预筛(PREREG + RESULT)

## 0. 白话三句(结果回填后写; 预注册阶段留空)

(待回填)

### 0.1 冻结凭证
- 本文 §P(候选清单 + 门 + 收据)在读任何 IC 之前入库: **commit `<回填>`**(`git log --format=%H -1 -- 本文` 首个); 任何 §P 改动必须以新日期文件增补, 不得原地改。
- 判官脚本: `multi_asset/exports/eda/kcurve_2026-08-21/devices_2026-08-22/f7_multiangle_prescreen.py`(SHA256 入结果 JSON `devices_2026-08-22/results/f7_multiangle_prescreen_2026-08-22.json`); 数据构建器 `f7_build_1h_panels.py`(永续/现货 1h 面板)、拉数器 `jp_spot1h_pull.py`/`local_spot1h_pull.py`(同目录)。
- 数据快照: jpline `/mnt/storage/private/work_hsy/probe_artifacts/f7/`(现货映射表 `f7_spot_map.json`、U400 并集 `u400_union_symbols.json`、1h 面板 npz); 原始 zip `w3lane/{wide1h_csv,spot1h_csv}`。

---

## §P PREREG(判据先冻结, 2026-08-22 07:0xZ, 写于任何读数之前)

### P0 口径(与 FF §P0 逐字同源, 不另立)
- **收益**: 简单持有收益 `expm1(R_wide)`; `R_wide` = `probe_artifacts/w2b_ret_cube.npz::R_wide` = log(close[N+4h]/close[N]), 1h K 线, **实盘相位 [N, N+4h]**, 名义锚 N ∈ {00,04,…,20}Z。
- **锚集**: 9,821 锚 2022-01-01 → 2026-06-29(W2/PH/SR/FF 同锚族); 逐年 = 2022/23/24/25/26(2026 为 1-6 月)。
- **宇宙 400**: `wide_fea_hist_meta::members[E_ts==N]` ∩ `qv4h ≥ 2.5e5`(FF/pod_stop_arms_v3 同式; 实测逐锚均 ≈251 名, 并集 727 名)。
- **king 基线**: `pod_backup_2026-08-21/slow_pred_hist_oos.npy`(宽 slow-LGBM king, 逐年扩张 OOS, 行 E_ts==N)—— 与 FF 的 400 宇宙 S1 同一基线(FF 读数: king 4h 价格 IC +0.0617)。
- **信息集**: 候选全部只用 ≤N 的信息; 1h K 线只用 open_time ≤ N−1h 的 bar(收盘 ≤ N); Binance metrics 通道取行 **N−1h**(与 FF `DOI24[rowT]` 同约定, 比必要多陈旧 1h, 宁保守); 现货/永续 quote volume 不受 1000×乘数影响(量纲 USDT)。
- **S1 门(冻结, = FF P3 / 路径文档 §3.7 F-2 原文)**: ΔIC = IC(0.7·z(king) + 0.3·z(cand)) − IC(z(king)), 逐锚横截面 Spearman 对 4h 简单价格收益, 在 U400 ∩ {cand 有限} ∩ {king 有限}; **过 = 评估年(≥100 有效锚)逐年均值 ≥ +0.003 且每年 ≥ 0**。附: cand 对 king 秩残差(逐锚 rank-OLS 残差)的 IC; cand 单独 IC(按预声明符号); 同子集上的 king IC(使 ΔIC 可比)。
- **子集规则(冻结)**: 若候选在 U400 内逐锚覆盖率均值 < 80%(按名计), 该读数标 **"子集预读"**: 过/不过都**不构成 400 宇宙判决**(宇宙依赖正是宽度复活的教训, `ma_v2_wide_universe_revival`); 正式 S1 必须覆盖 ≥80%。
- **相关(冻结报表)**: 逐锚横截面 Spearman 均值: cand vs {king, f_fund_ema_v1(宽腿变量), f_fund_ema_v2(在役腿变量), fund_now_nf, f_rev_24h(rev24 腿), f_amihud_24h, f_volq_ratio, f_mom_7d}。**|ρ| ≥ 0.5 对 funding 族 ⇒ 标"funding 渗透"**(即使过 S1 也不算"非 funding 来源")。
- **噪声底(冻结)**: 每候选 5 个固定种子(0-4)的锚内随机置换安慰剂, 报其 ΔIC 均值(0.7/0.3 掺噪声会**稀释** king ⇒ 安慰剂 ΔIC 预期为负; 它标定"ΔIC=0 已含真信息, +0.003 是严门"); 安慰剂只作参照, 不改门。
- **反号诊断(冻结)**: 同时报 −cand 的 ΔIC; **反号过线不算过**(符号事前声明; 反号若过只能作为下一轮新预注册的假说)。
- **不做**: S2(净额/换手), 臂选择, 堆叠, 权重搜索, 任何阈值事后调整。

### P1 今日 S1 预筛的 8 个候选(冻结; 符号 = 腿方向, + 表示高值做多)

| # | 角度 | 候选 | 构造(因果, ≤N) | 数据源 | 覆盖 | 预声明符号/机理 | 与已判负的关系 |
|---|---|---|---|---|---|---|---|
| P1 | 合约/持仓 | `d_oi_24h` OI 24h 变化 | `wide_metrics_ch.npz::d_oi_24h` 行 N−1h(含 MASK) | Binance 5-min metrics 归档, 143 币已在库 | U400∩140 ⇒ **子集** | **+**: OI 堆积 = 新仓位/注意力流入 ⇒ 短期延续(110 宇宙 Ridge 曾见 d_oi_1h 弱正一致) | 110 宇宙·1h/YR4·对 DL 书双门 FAIL(`ma_v3_track2_oi_positioning_closed` 2026-07-13); 本次 = 400∩143·4h 简单·实盘相位·对宽 king |
| P2 | 合约/持仓 | `doi_x_ret` OI 变化 × 收益交互 | 同上通道 | 同上 | 子集 | **+**: 价涨+OI 增 = 新多(趋势确认), 价涨+OI 减 = 空头回补(反转) | 同上 |
| P3 | 合约/持仓 | `top_vs_global_divergence` 大户 vs 散户多空比分歧 | 同上通道 | 同上 | 子集 | **+**: 跟大户、逆散户 | 同上(110 读数 −0.0012, 方向与假说相反; 本次按机理 + 号, 反号只作诊断) |
| P4 | 合约/持仓 | `oi_level_norm` OI/成交额(杠杆强度) | 同上通道 | 同上 | 子集 | **−**: 高 OI/量 = 仓位拥挤、难退出 ⇒ 反转/均值回归 | 同上(110 无增量) |
| P5 | 合约/结构 | 结算时点后首小时反应 `r_settle` | s = 满足 s+1h ≤ N 的最近结算时点(按该币 `f_fund_iv` 周期, 自 00Z 起整周期); r = close_bar(s)/close_bar(s−1h) − 1(bar open_time=s, 即 [s,s+1h) 价格变动), 减当锚横截面中位数 | `w3lane/wide1h_csv`(829 名 1h)+ `f_fund_iv` | 全宇宙 | **−**: 结算后首小时是费率收割者解仓的流量驱动移动 ⇒ 4h 内回吐 | 未测; funding-**相邻**(时点由费率周期定, 值是价格反应不是费率); king 含 ret5_sum_48(最近 4h 和)但不含该小时单独项; FF 的费率变化反转(−0.006)被换手吃光 ⇒ 预期弱 |
| S1 | 现货 | 现货成交占比 `sshare24` | Σ24h spot quoteVol / (Σ24h spot qv + Σ24h perp qv), bar open_time ≤ N−1h | 现货 1h K 线(data.binance.vision, 今日拉; 映射表 `f7_spot_map.json`: exchangeInfo 命中 469 + 手工 10 + CDN 试拉 248)+ 永续 1h | 有现货对的名(预期 ≈60-70% 并集名, 按锚计更高) | **+**: 现货主导 = 真实需求/非杠杆 ⇒ 漂移为正且少反转; 合约主导 = 杠杆投机 ⇒ 拥挤回吐 | 未测(现货成交量 = 新信息源, 不在 78 列/82 特征内; `ammunition_campaign_night1` 的饱和结论只覆盖永续 bar/书) |
| S2 | 现货 | 现货主动买入失衡 `stbi24` | (Σ24h takerBuyQuote − Σ24h (qv − takerBuyQuote)) / Σ24h qv, 现货 | 同上 | 同上 | **+**: 现货净主动买入 = 真实需求, 4h 内持续 | 永续成交流族 110 宇宙 DNR-as-leg(`takerflow_family_zero_admissions`; F3 反转有排序被换手吃光); 现货参与者群体不同, 未测; king 含永续 tbf 五窗口 |
| S3 | 现货 | 现货占比变化 `dsshare` | sshare24 − sshare168(7d) | 同上 | 同上 | **+**: 相对自身常态现货买盘抬头 = 需求转移 | 同上 |

**宇宙外/覆盖外处理**: 无现货对的名 S1-S3 = NaN(不记 0; 避免把"有无现货上市"这个特征冒充成交占比); "有无现货"只作诊断列(§P4 事件/状态项), 不入 8 候选。

### P2 完整候选清单(§A, 按角度; 可得性分级 = 今日可跑 / 1-2 天可拉 / 需采购 / 不立项)

见 §A(写于 §P 同一 commit; 清单本身是预注册的一部分, 事后不得增删以改结论; 可追加"下一轮"项但须标注追加时间)。

### P3 读法(冻结)
- 过 S1(全宇宙覆盖)⇒ 列为 F-2/F-3 之后的正式录取候选(S1 正式 + S2 净额 G 族 `PREREG_leg_admission_v2`), **不是结论**。
- 过 S1 但"子集预读"⇒ "候选, 待全宇宙数据"(§A 的 B 级拉数进日历), 不得引用为 400 宇宙结论。
- 不过 S1 ⇒ 该构造在该口径关闭(范围标注: 400/子集 · 4h 简单 · 实盘相位 · 对宽 king 0.7/0.3 blend); 不外推到其它视界/口径。
- 预写死法: 若某候选与 funding 族 |ρ| ≥ 0.5 且过 S1 ⇒ 记"funding 渗透的排序", 不计入"非 funding 来源"。
- 预写死法 2: 若 P1-P4 子集预读全部 ≤ 0 ⇒ 与 110 宇宙关闭同向, 400 全宇宙拉数(~1M 日文件)降为低优先级(仍可拉, 但排在 bookDepth 之后)。

### P4 四问(事前作答框架, 结果节逐条回填)
- 口径: 简单收益/实盘相位/400 宇宙/对宽 king; 与 FF 同源同锚同基线 ⇒ 读数可与 FF §4 C 表直接并排。
- 泄漏: 全部输入 ≤N(1h bar open_time ≤ N−1h; metrics 行 N−1h; 现货映射不含未来信息); 收据 R5 断言。
- 选择效应: 8 候选事前冻结, 无事后挑选; 反号不算过; 安慰剂报噪声底; 无任何阈值/窗口搜索(24h/168h 窗口事前定, 与宽面板 f_*_24h 习惯一致)。
- regime: 逐年 ≥0 是门的一部分; 另报 2022-24 vs 2025-26 两段。

### P5 收据(脚本断言, 非口头)
- R1 面板/立方体 829 符号逐位对齐。
- R2 自建永续 1h 面板的 close 推出的 log(close[N+4h]/close[N]) 与 `w2b_ret_cube::R_wide` 在 2,000 随机有效格 maxabs < 1e−6(验证我方 1h 解析与小时对齐)。
- R3 metrics 网格 == 训练面板网格(ms, 与 FF 同断言), 行 N−1h 存在率 100%。
- R4 结算时点推断: 140 名 `xvenue_funding_binance.npz` 逐笔结算时间戳 vs 由 `f_fund_iv` 推出的 s 序列: 推断 s 命中真实结算时间 ≥ 95%(iv 变更期容许差)。
- R5 因果: 每个候选记录其用到的最大 bar open_time / metrics 行时间, 断言 ≤ N−1h。
- R6 现货映射: 每个映射名在重叠小时上 现货 vs 永续 1h 对数收益相关中位 ≥ 0.95(抓错映射/错乘数), 不过的名从 S1-S3 剔除并列表。
- R7 安慰剂 5 种子 ΔIC 均值 < 0(稀释方向; 若为正 ⇒ 装置有误, 停)。

### P6 输入(只读)与输出
输入: jpline `pod_backup_2026-08-21/{wide_panel_4h_hist_v2.npz, wide_fea_hist_meta.npz, slow_pred_hist_oos.npy}`, `probe_artifacts/w2b_ret_cube.npz`, `quant_research_multi_asset/multi_asset/exports/wide_metrics_ch.npz`, `w3lane/wide1h_csv`(829 名永续 1h 月度 zip), `w3lane/spot1h_csv`(现货 1h, 今日拉), `w3lane/xvenue_funding_binance.npz`(收据 R4)。全部 SHA256 入 JSON。
输出: 本文 §1-§5; `devices_2026-08-22/results/f7_multiangle_prescreen_2026-08-22.{json,log}`; 脚本三件入 `devices_2026-08-22/`。

---

## §A 候选清单(全谱; 冻结于 §P 同 commit)

可得性分级: **A 今日可跑**(数据已在库或今日拉齐) / **B 1-2 天可拉**(公共归档, 需拉数+构面板) / **C 需采购或等采集** / **D 不立项**(已判负同形态或属择时/状态变量)。

### A-1 合约角度

| 候选 | 机理 | 构造 | 数据 / 可得性 | 与已判负的关系 / 处置 |
|---|---|---|---|---|
| 永续溢价 basis(F-2, 不重复) | 期限结构中 funding 表达不了的部分 | basis⟂funding | premiumIndexKlines 1h(140 在库, 400 可拉) | F-2 在做; 本文只作相关参照 |
| 基差期限结构(季度 vs 永续) | 远期曲线斜率 = 杠杆需求 | 季度合约 K 线(`BTCUSDT_YYMMDD`) | 仅 BTC/ETH 有季度交割 ⇒ **非横截面量** | **D**: 只能作市场状态变量 ⇒ 择时五形态已封(HEALTHCHECK §4/§6), 不立项 |
| OI 变化 × 价格(P1/P2/P4) | 持仓流入/拥挤 | d_oi_1h/24h, oi/量, doi×ret | metrics 143 币在库; 其余 ~580 并集名 = data.binance.vision `futures/um/daily/metrics`(日文件, 5-min; ~1M 文件, 本地并行约 1 天) | **A(子集)/B(全宇宙)**; 110 宇宙 1h/YR4 双门 FAIL 在案, 400 重测按 P3 读法 |
| 清算/强平密度 | 强平瀑布 = 流动性事件; W4 方向性发现: 4h 延续 | 逐名强平额 1h/4h 归一 | 真值: data.binance.vision **无** liquidationSnapshot(实测 8 日期 404, S3 前缀列表无此项); `allForceOrders` REST 已停; 自建 ws 采集 `com.hsy.w4liqcapture` 08-11 起(样本太短); Tardis/Coinglass 付费 | **C**: 真值需采购(W4 Tardis-C ~$700-1200)或等采集 ≥6 月; 5m 代理(140)0/7 已判负 |
| 多空持仓比(P3) | 大户/散户定位 | top_ls_ratio_z, global LS, 分歧 | 同 metrics | **A(子集)/B** |
| taker 买卖比(metrics) | 主动流 | taker_ratio_ema | 同 metrics | **D**: 成交流族 DNR-as-leg(110), king 已含 tbf 五窗口 |
| 标记价偏离 | mark−last = 短期错位 | markPriceKlines 1h close vs 最后价 | `futures/um/monthly/markPriceKlines`(829×57 月文件, ~1h 拉) | **B(低先验)**: 与 basis 同族(mark 含指数+基差 MA), F-2 之后再议 |
| 结算时点价格跳(P5) | 费率收割流 | r_settle | 1h 在库 | **A**(funding-相邻, 标注) |
| 资金费周期切换(4h↔8h) | 交易所对极端费率币改 4h | 周期状态 | f_fund_iv 在库 | **D**: 这是 funding 族的量纲伪影来源(FF §3), 不算新源 |

### A-2 现货角度

| 候选 | 机理 | 构造 | 数据 / 可得性 | 关系 / 处置 |
|---|---|---|---|---|
| 现货成交占比(S1)/变化(S3) | 现货主导 vs 合约主导 | 见 P1 表 | 现货 1h K 线 data.binance.vision(今日拉; 映射 469+10+试拉 248) | **A**; 新信息源 |
| 现货主动买入失衡(S2) | 现货净需求 | 见 P1 表 | 同上 | **A**; 现货群体 ≠ 永续成交流族 |
| 现货 Amihud/波动 | 现货流动性 | 同永续 f_amihud_24h 公式 | 同上 | **D(冗余先验)**: 与永续 Amihud 同构, 先看 S1-S3 与 f_amihud 的 ρ 再议 |
| 现货−永续领先滞后 | 谁先动 | r_spot(1h) − r_perp(1h) = Δbasis | 同上 + 永续 | **D → F-2**: 数学上 = 溢价变化, 属 basis 族(FF: 费率变化反转被换手吃光) |
| 现货上架/下架事件 | 上市效应 | has_spot / 距上市天数 | 现货首月文件日期(免费, 拉数副产品) | **诊断列**(状态/事件, 不作腿); 事件研究可列 R4 事件流 |
| 现货订单流 | 微观 | Tardis(仅 BTC) | 付费 | **C → F-6** |
| 现货成交笔数/均笔(参与者结构) | 散户 vs 大户 | count/qv | 同一拉数 | **B(低先验)**: 永续版 ≈ 慢动量(ρ 0.776); 下一轮 |

### A-3 跨所 / 市场结构

| 候选 | 机理 | 构造 | 数据 / 可得性 | 关系 / 处置 |
|---|---|---|---|---|
| 跨所价格溢价 Binance vs Hyperliquid | 场所定位差/套利流 | prem_div, hl_prem_ema | `hl_hourly.npz`(140 名, 2023-07 起) | **D**: `RESULT_w1_hl_family_2026-08-10` 收益预测全族 \|IC\| ≤ 0.006(84 币·标准 IC 门)已关; 400 上无新覆盖 |
| Binance vs OKX/Bybit 价格溢价 | 同上 | (P_bybit − P_binance)/P | Bybit REST kline(公共, 深度至 2020, ~17k 次调用)/OKX history-candles(深度不确定) | **B(低先验)**: 跨所 funding 全史判负(`orthogonal_mining_round1` ②)且 HL 溢价判负 ⇒ 排在 bookDepth/metrics 之后 |
| BTC 主导率 / 山寨相对强弱 | 横截面条件变量 | 状态 | 在库 | **D**: 择时五形态封卷; 在役书的保费本身就是主导率 β(`book_is_dominance_premium`), 这正是要摆脱的 |
| 截面离散度 | 全局状态 | 状态 | 在库 | **D**: L2 全局书状态 +0.0007 已关(弹药战役) |
| 稳定币供应 / ETF 流 / 链上流(日频) | 宏观流动性 | 状态 | DefiLlama(免费)/Farside(爬)/Glassnode(付费) | **D(状态变量, 频率失配)**; 逐币交易所净流入(横截面)= Glassnode/CryptoQuant/Nansen 付费且覆盖 ~100-200 资产 < 400 ⇒ **C** |
| 板块/叙事归属(显式分类) | 板块领先-滞后/板块内反转 | 板块龙头 24h 收益 → 滞后者; 板块相对反转 | CoinGecko categories(免费 API, ~700 次查询, 限速) | **B(中先验)**: 新信息 = 分类表本身(F4 截面结构族用的是统计 β/相关, 已关; 这是显式分类, 未测); 下一轮 |
| 解锁/事件流 | 供给冲击 | 事件日历 | tokenomist/cryptorank(部分免费) | R4 事件流轨(MILESTONE §3 活口 4), 本文不立项 |

### A-4 微观结构(LOB)

| 候选 | 机理 | 构造 | 数据 / 可得性 | 关系 / 处置 |
|---|---|---|---|---|
| **Binance 永续 bookDepth(±1..5% 档名义深度, ~30s 快照)** | 挂单不对称 = 流动性供给失衡; 深度/成交额 = 可吸收性 | 锚 N 的 (bid−ask)/(bid+ask) @±1%/±2%; 24h 均值; 深度÷24h 成交额; 斜率(±5%/±1%) | `futures/um/daily/bookDepth/<sym>/`(**免费, 全部永续, 2023-01-01 起**; 实测 BTC/ZK/1000PEPE 200, 2022 404; 每日文件 ~440KB ⇒ U400 2023→2026-06 ≈50 万文件 ~200GB 压缩; **jpline 仅余 101GB ⇒ 必须流式处理**: 下载→取锚时刻/小时均值→删) | **B(高先验, 1-2 天)**: 这就是 F-6 "400 宇宙 LOB 需采购"的**免费粗粒度替代**; L0 BTC 25 档单资产 +0.0007 已关(单资产时序口径), 400 横截面深度失衡**未测** |
| bookTicker(最优买卖) | 点差 | — | 仅部分主流名有日文件(ZK 404) | **D**: 覆盖不足; 点差代理 = Amihud 已在库 |
| 全档 L2 / 逐笔(Tardis) | 完整微观 | — | 付费 | **C → F-6**(用户裁定) |

**为什么 BTC Tardis 微观装置不在此跑**: 单资产时序口径与 400 横截面口径不是一个问题(弹药战役 L0 判的是前者); 400 宇宙横截面第一遍应先用免费 bookDepth 证伪/证实, 再决定是否买全档(#29 铁律: 先证伪再花钱)。

---

## 1. 装置、数据、收据(回填)

(待回填)

## 2. S1 预筛结果表(回填)

(待回填)

## 3. 相关与渗透(回填)

(待回填)

## 4. 四问(回填)

(待回填)

## 5. 排序后的候选清单 + 下一步(回填)

(待回填)
