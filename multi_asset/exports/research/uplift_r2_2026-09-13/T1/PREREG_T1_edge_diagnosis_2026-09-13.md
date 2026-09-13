> **创建:** 2026-09-13 ~05:30Z | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T1) | **状态:** 预注册, 冻结先于任何结果数字; sha256 记入 `receipts/PREREG_FREEZE_sha.txt`, 每个装置运行前断言 | **作废条件:** 本文 §8 任一门失败且无法以定义性修正(AMENDMENT, 须先于结果数字)补救; 或 v4 链被更新的链取代; 或归档 r18 臂被替换
> **纲领:** `../PROGRAM_uplift_r2_2026-09-13.md` §2 T1 | **口径钉:** `uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md`(v4; 记账元 y4 = Π(1+r)−1 RAW; 禁从 5m 缓存 ret5 重算收益, E-0908-B / r18 §8) | **实盘零接触:** `~/dl_quant_live` 与 `~/wide_shadow` 只读, 账本与状态一律先拷只读副本到 `T1/private/`(gitignored); 不调任何交易所/Telegram/网络 API

# PREREG · T1 · 边在哪里没了 —— 分解、状态变量、估计器与每条假设的证伪读数

## §0 这份预注册冻结什么, 不冻结什么

冻结: 窗口与口径(§2)、分解与恒等式(§3)、状态变量的因果定义(§4)、估计器与多重比较族(§5)、H1–H5 每条的统计量与**能证伪它的读数**(§6)、六项交付的精确计算(§7)、结果被使用之前必须通过的门(§8)、装置与环境(§9)、事先声明的不可判项(§10)。
不冻结: 任何结果数字。本文出现的数值只有阈值、窗口端点、以及 §1 里**读代码得到的事实**(不是统计结果)。

## §1 读代码得到的事实(先于任何数字; 它们决定了 H2 要查什么)

| # | 事实 | 出处(只读) |
|---|---|---|
| F1 | **生产者 fund 腿特征**: 每次结算的间隔 `iv` = 本条与上一条 fundingTime 之差(小时), 就近取整到 {1,2,4,6,8}; `rn = rate × 8/iv`; 墙钟半衰期 3 日 EMA 作用于 `rn`。**不读任何静态 span 表。** | `~/wide_shadow/shadow_loop_v3.py` L341–349 |
| F2 | 生产者 fund 腿打分 `legz["fund"] = xz_in_base(fe_v[m], …)`, `fe_v[j] = est["acc"]`(F1 的 EMA), 新鲜度 ≤12h | 同上 L409–412, L471 |
| F3 | 生产者 carry = `sm × fn_v × 4/ivv`, `ivv` = 账本最新行记录的 iv | 同上 L527–528 |
| F4 | combo_stage FTRIM 的 rn8 = 账本最新行 `rate × 8/iv`(同一 iv) | `~/wide_shadow/fea171/combo_stage.py` L238–244 |
| F5 | **生产者模型特征**: king LGBM 第 80/81 列 = `fe_v`(F1 的 8h 归一 EMA)/ `fn_v`(原始每结算费率); V2MAIN(F10)服务端面板 `f_fund_ema` = aux EMA `acc`(8h 归一), `f_fund_now` = 原始费率 | `shadow_loop_v3.py` L418–419; `combo_stage.py` L134–146 |
| F6 | **研究面板**: `f_fund_now` = 原始费率; `f_fund_iv` = 数据 zip 的 interval 列, 缺失则时间差推导(取整到允许集, 首行默认 8); `f_fund_ema` = **v0 原始费率** EMA; `f_fund_ema_v1` = `rate×8/iv` 归一 EMA(回放 fund 腿用这个); `f_fund_ema_v2` = span=round(24/iv 中位) 的结算空间 EMA。八月 API 尾巴行的 iv 取 fetch 时的 fundingInfo 静态值 | `retrain_2026-09/pod_panel_ext.py` L63–166 |
| F7 | **模型训练特征**: king 特征构建器 `FUND = [PW["f_fund_ema"], PW["f_fund_now"]]`(注释「fund 列语义不变(v0+now)」); DL 特征构建器 `FUND = [PW["f_fund_ema"], PW["f_fund_now"]]` | `retrain_2026-09/v4_chain_2026-09-09/pod_fea_ext_clamp.py` L1, L63; `~/wide_shadow/fea171/dlw_features.py` L73 |
| F8 | **执行器 span 表**(`config/funding_span_table.json`, 建于 2026-07-25, 140 名)只被执行器自己的冻结 DL 面板读(`signal/funding_panel.py` L64–81, `signal/live_panel.py` L55); 在役书是外部书, 执行器日志记 `universe_ood: SKIPPED_EXTERNAL — the frozen DL model is not scoring this book`。15 个 stale 名(ours 8h → venue 4h)记录在 `state/live/alarm_episodes/funding_span.json`: ANKR, AXS, ENJ, FLOW, GMT, IOST, KAVA, MASK, ONT, RVN, SKL, STG, XTZ, ZIL, ZRX(均 USDT) | `~/dl_quant_live/ops/check_funding_span.py`; `state/anchor_runs.log` L36839 |

**F5 与 F6/F7 放在一起读出一个待验的不一致**(不是结论): 若训练特征文件里 `fund_ema` 列确是 v0(原始费率), 而服务端喂的是 v1(8h 归一), 则对**所有非 8h 结算的名**(不止 15 个迁移名), king 与 V2MAIN 模型在服务时看到的 `fund_ema` 是训练口径的 8/iv 倍。这与 `docs/AUDIT_full_stack_2026-08-25.md` 第 8 行「fund_ema 实盘离散度 1.96× 时间匹配对照, 待修」形状一致, 但**形状一致不是证据** —— 登记为 H2b, 以训练特征文件逐值比对判定(§6 H2b)。F1–F8 本身在 RESULT 里逐条复核引用。

## §2 数据、窗口、口径

### §2.1 回放臂(四个, 全部判读都在四个上做)
`C0_s42`(主; = 归档 A0 逐位)、`C0_s2027`、`NW_s42`、`NW_s2027` —— r18 装置 `w10_sleeve_r18.py`(sha256 `9b8a6323…c5c4`)在 pod2 的输出 `/workspace/uplift_2026-09-11/r18_foundation/arms/{C0,NW}_s{42,2027}.npz` 的 `d30_n2_c42_{rec,W}`。本轮用派生装置(§9)**重跑并逐位复现**它们(GATE P), 同时输出逐腿逐名分量。
rec 列: `ts, net, pnl, carry, cost, gross_total, …, net_ex(18), pnl_ex(19), carry_ex(20), cost_ex(21), netlong(22)`。

### §2.2 口径
回放逐锚分量 = 执行器口径列 / `gross_total`, 单位 **bps/锚/单位 gross**: price = pnl_ex/gt, carry = carry_ex/gt(正 = 付), cost = cost_ex/gt, **g = net_ex/gt = price − carry − cost**。期间值 = 期间内逐锚值的**等权均值**。比值统计(ρ, κ, π)= 分子均值 / 分母均值。

### §2.3 窗口(锚时间 E, UTC, 闭区间)
| 名 | 定义 |
|---|---|
| W_ALPHA | r18 rec 行 900..10037 = 2022-06-30 00Z..2026-08-30 20Z, n 断言 9138(08-31 00Z 行不入) |
| Y2022H2 / Y2023 / Y2024 / Y2025 | W_ALPHA ∩ 各自日历年 |
| **H1_2026(参照)** | 2026-01-01 00Z..2026-06-30 20Z |
| M2025_01..M2025_12, M2026_01..M2026_07 | 日历月 |
| M2026_08 | 2026-08-01 00Z..2026-08-30 20Z |
| LIVE_REPLAY | 2026-08-26 04Z..2026-08-30 20Z(回放 ∩ combo 在役; 08-30 00Z 一锚生产者回落为 king 形态, 已知, 不剔除) |
| **LIVE_D2** | 2026-08-26 04Z 起, 至同时满足「有 `target_live` 部署权重」「x0910 元 y4 前向收益有限」「x0910 面板行存在」的最后一锚(预期 2026-09-10 00Z) |
| **LIVE_REAL** | 2026-08-26 04Z..2026-09-11 20Z 中, 同时有 E 时刻持仓回读、E 与 E+4h 的 `mid_at_anchor_vector` 的锚 |
| W5_R6(对账用) | 2026-08-26 04Z..2026-09-10 00Z(r6 的 W5) |
| PRE_LIVE | W_ALPHA ∩ E < 2026-08-26 04Z |
| STATE_FIT | Y2024 ∪ Y2025(H1 混合效应的状态-边关系只在这里估, 与参照期和目标期都不重叠) |

### §2.4 实盘两台仪器(LIVE 窗口)
- **D2(回放口径, 部署书)**: w = `~/wide_shadow/state/target_live/<E>.json` 的 `weights`(只读副本), 映射到 829 回放符号; 映射不到的名计入 `unmapped_gross` 并报告。price_D2 = Σ w·y4x[E]·1e4 / Σ|w|, y4x = `/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz` 的 y4(NaN 名计 0, 其 |w| 计入 `unknown_gross` 报告); carry_D2 = Σ w·c4·1e4/Σ|w|, c4 = f_fund_now × 4 / IVf(x0910 面板 E 行; IVf = f_fund_iv 若有限且 >0 否则 8; f_fund_now NaN 计 0)。**D2 无成本项**, g_D2pre = price − carry。
- **REAL(账本)**: `~/dl_quant_live/state/live/pilot_log/<day>/` 只读副本。逐名: q = E 时刻持仓回读数量, p1/p2 = E/E+4h 的 mid; price_n = q(p2−p1); funding_n = Σ funding_paid(结算 ∈ (E, E+4h], 按 (symbol, settlement_ts) 去重); fee_n = −Σ commission×(commission_asset 在同锚 mid 的 USD 价)(E-0911-C 口径, 按 trade_id 去重); timing_n = 已成交带符号数量 × (p1 − 名义加权均成交价)。gross = anchors.jsonl `realized_gross`(r6 同式)。分量 bps of gross: price, carry = −funding(正 = 付), cost = −(fee + timing)。**g_REAL = (price + funding + fee + timing)/gross**(timing 计入净额的理由: 旧仓位从 E 到成交、新仓位从成交到 E+4h 的分段和恒等于 price + timing; r6 的 `net_realized` 未计 timing, 两者都报)。
- 幅度换算敏感性(P2, r6 实测斜率): REAL 价格 ÷ 0.835, REAL 资金费 ÷ 0.733。凡涉及 REAL 与回放历史比较的判读, **原值与换算值必须给出同一判决**, 否则记 NOT DECIDABLE。

### §2.5 多空与腿
- 回放: side = sign(smr_n)(执行器 reshape 后持仓); 成本按 sign(smr_n), 若 smr_n = 0(出场)按上一锚 sign(HR_n)。腿 ∈ {king, fund, f10, rev24}; rev24 在 W_ALPHA 上**断言恒 0**(LEGS=101)。
- D2: side = sign(w_n)。REAL: side = sign(q_n)。**D2/REAL 无腿拆分**(§10)。

## §3 回放的逐腿分解(派生装置内, 精确可加)

书链逐步对腿分量做与合成书相同的线性运算, 非线性步骤按合成书的掩码/比例施加于各腿, 从而逐名恒等 Σ_l 分量 = 合成量:
1. king 半书打分 z = w3_k·xz(king) + w3_r·xz(rev24) + w3_f·FZ ⇒ 分量 (w3_k·xz(king), w3_r·xz(rev24), w3_f·FZ, 0)。F10 半书 z_f = w3_k·xz(F10) + w3_r·xz(rev24) + w3_f·FZ ⇒ 分量 (0, w3_r·xz(rev24), w3_f·FZ, w3_k·xz(F10))。
2. FTRIM(`z<0 ∧ rn8≤−10bp` 置 0): 掩码按**合成** z(置 0 之前)取, 该名全部腿分量置 0。
3. sel 内去均值: 各腿分量各自减 sel 内均值。L1 归一: 各腿除以合成 g。
4. cap 截断(唯一非线性): 被截断名的各腿分量乘以 (截断后/截断前) 合成值之比; 截断前合成值为 0 的名分量不动(其和仍为 0)。再除以合成 g2。
5. 止损层屏蔽、EMA(`sm_l = H_l + SMA(tgt_l − H_l)`)、无交易带(掩码 = |合成 SMA(tgt−H)| < SBAND ⇒ 各腿保持 H_l)、强制出场(各腿置 0)、F10 半书 `_gf ≤ 1e-9` 时整体保持 HF_l —— 全部与合成书同掩码。
6. 混合 smb_l = (1−φ)·sm_l(king 半) + φ·sm_l(F10 半); 执行器 reshape: nz 集内各腿减各自均值, 乘合成比例 g0/g1。
7. 逐名分量: pnl_{l,n} = smr_{l,n}·y_n·1e4; carry_{l,n} = smr_{l,n}·fnow_n·(4/iv_n)·1e4; **cost_{l,n} = rate_n · trr_{l,n} · sign(trr_n)**(trr_l = smr_l − HR_l; Σ_l = rate_n·|trr_n|, 交易互抵的腿分得负成本, 声明)。成本只在当锚成员集上计(与装置同)。
8. 恒等门(GATE I, §8): 逐锚 Σ_{l,side} pnl/carry/cost 与 rec 的 pnl_ex/carry_ex/cost_ex 差 ≤ 1e-7 bps; 逐名 |Σ_l smr_l − smr| ≤ 1e-12; rev24 分量在 W_ALPHA 行 |·| ≤ 1e-12。

## §4 状态变量(因果: 锚 E 只用 E 之前收盘的收益与 E 时刻已结算的费率)

记元行 k(E_ts[k] = E), 面板行 j(ts[j] = E), 成员集 m = members[k] ∩ CRYPTO m1 掩码行(与装置同; x0910 九月行掩码末行前推, r6 已声明)。返回源 = **记账元 y4**(RAW 复利; 用 x0910 元以覆盖到九月; GATE X 保证与原元重叠行逐值相等)。**不从 5m 缓存、不从面板 f_rev_* 取收益**(ret5 裁剪, E-0908-B)。
- R24_n = Π_{q=1..6}(1 + y4[k−q, n]) − 1(6 行全有限, 且 E_ts[k] − E_ts[k−q] = 4h·q 断言); R72_n 同式 q=1..18。
- **DISP24** = m 上有限 R24 的总体标准差(有限数 ≥ 50, 否则 NaN)。DISP72 次要。
- **BREADTH72** = m 上有限 R72 中 > 0 的比例; BREADTH24 次要(同为 ≥50 门)。
- **BTC72** = BTCUSDT 的 R72; BTC24 次要。
- **SIGF** = 1e4 × m 上有限 RN8 的总体标准差, RN8 = f_fund_now × 8/IVf(面板 j 行; 有限数 ≥ 10)。= r8 BUILD2 的 sigma(与线上仪表 maxabs 0.0 的那个定义)。
- **MUF**(声明新增, 因 r6 §5 指向横截面均值费率) = 1e4 × m 上有限 RN8 均值。
- **PUMP72** = Σ_{n∈D10} max(R72_n,0) / Σ_n max(R72_n,0), D10 = 有限 R72 最大的 ⌈0.1N⌉ 名(N ≥ 50; 分母 0 则 NaN)。PUMPSPR72 次要 = mean(D10 的 R72) − median(R72)。
- 主状态六个: DISP24, BREADTH72, BTC72, SIGF, MUF, PUMP72。分箱 = 各变量在 PRE_LIVE 锚分布上的五分位(边界固定, 自举不重估)。
- GATE S(因果): 把 y4 第 k 行及之后全部置随机数重算, 锚 k 的六个状态逐位不变。

## §5 估计器与多重比较

- **UTC 日块自举**: 块 = floor(E/86400); 2000 次; 生成器 `numpy.random.default_rng([20260905, k])`, 每族一个 k(下表), 族内所有格/臂/期间**共用**同一组日索引抽样(公共随机数)。多期间统计: 每次复制按族内期间登记顺序, 在各期间的日集合内**各自**有放回抽满该期间日数。期间均值 = 抽中日的锚值和 / 抽中日的锚数。
- 报告: CI95 = 百分位 [2.5, 97.5]。**判决区间** = 点估计 ± z_K · SE_boot(SE = 2000 个复制值的 ddof=1 标准差), z_K = Φ⁻¹(1 − 0.025/K)。
- 生成器与族:

| k | 族 | 用途 | K(判决族大小) |
|---|---|---|---|
| 1 | LEVELS | 期间分量水平表(描述) | — |
| 2 | CELLS | 排序格表 CI(描述) | — |
| 3 | F_H1 | H1 与 H1-fuel | 10 |
| 4 | F_H3 | H3 | 8 |
| 5 | F_H4 | H4 | 3 |
| 6 | F_H5 | H5 | 4 |
| 7 | F_MONTH | 交付(2) | 10 |
| 8 | ANALOG | 交付(5b) | — |
| 10 | H2Q | H2 份额(描述) | — |

- 双种子/四臂: 判决以 C0_s42 计算, **四臂判决必须一致**, 不一致则该条记 NOT DECIDABLE 并列出各臂。

## §6 假设与证伪读数

### H1 · 离散度/广度 regime 移动解释了价格边的消失
- 目标 T_A = M2026_08(回放臂); T_L = LIVE_D2。参照 H1_2026(同一回放臂)。
- 落差 D_T = price_T − price_H1。
- 混合效应 MIX_{S,T} = Σ_b (f_{T,b} − f_{H1,b}) · μ_b, f = 期内锚落入 S 的第 b 五分位的比例, μ_b = STATE_FIT 内该五分位的平均 price(同臂)。自举: STATE_FIT、H1、T 三段日集合分层重抽。
- 单格判定(S, T): **EXPLAINS** ⇔ D_T 判决区间上界 < 0 且 MIX 判决区间上界 < 0 且 MIX/D_T ≥ 0.5; **DOES-NOT-EXPLAIN** ⇔ D_T 判决区间上界 < 0 且(MIX 判决区间含 0 或 MIX/D_T < 0.25); 其余(含 D_T 不显著为负)= UNDECIDED。
- **H1 存活** ⇔ S ∈ {DISP24, BREADTH72} 中至少一个在至少一个目标上 EXPLAINS(四臂一致)。**H1 证伪** ⇔ 两个变量在两个目标上全部 DOES-NOT-EXPLAIN。其余不可判。
- **H1-fuel(声明扩展, 同规则)**: S ∈ {SIGF, MUF}。单独给出存活/证伪/不可判, 不与 H1 合并。
- F_H1 的 K = 10 = D_TA, D_TL + MIX × {DISP24, BREADTH72, SIGF, MUF} × {T_A, T_L}。

### H2 · 资金费结算间隔 8h→4h 变更使生产者 fund 特征失真(P9)
- E2a(账本逐行, 只读副本 `private/aux_20260913.json`, 取于 2026-09-13 04:58Z): 对 15 名的 `ledger_tail` 每行 k ≥ 1, gap_k = (ft_k − ft_{k−1})/3600 就近取整到 {1,2,4,6,8}; 比较记录的 iv_k 与 gap_k。计数: LIVE 行(ft ∈ [2026-08-26 04Z, 2026-09-12 00Z])与全部存储行的不一致数; 并报告每名 LIVE 行的 gap 众数。
- E2b: 用存储行按 F1 公式(记录的 iv 与 gap 取整 iv 各一遍)重算 EMA, 与存储的 `ema[s].acc` 比较相对差 |Δ|/max(|acc|, 1e-6)。
- **H2 证伪** ⇔ 15 名的 LIVE 行不一致数全为 0, 且 E2b(记录 iv)相对差全 ≤ 1e-3。
- **H2 存活** ⇔ 任一名 LIVE 行存在「记录 iv = 8 而 gap = 4」, 或 E2b(gap 取整 iv 与存储 acc)相对差 > 5% ⇒ 按 §7(4) 量化份额。
- **不可判** ⇔ 15 名中有名不在生产者账本里、或账本尾不覆盖 LIVE。
- 另报(不参与判决): 全基名单上 iv ≠ gap 的行数(数据缺口造成的推断误差)。

### H2b · 模型特征 fund_ema 训练口径 v0 / 服务口径 v1(声明扩展, 由 §1 F5–F7 读代码发现)
- 在 pod2 上找到 king v4 训练特征矩阵与 V2MAIN(dlw_v4raw)特征矩阵中名为 `fund_ema` 的列; 在 iv = 4 的名-锚格上(面板 f_fund_iv = 4)比较该列与面板 `f_fund_ema`(v0)和 `f_fund_ema_v1`(v1)。
- **H2b 存活** ⇔ 训练列与 v0 相对差中位 ≤ 1e-5 且与 v1 相对差中位 ≥ 0.4(即训练 = v0), 而服务端按 F5 = v1。**H2b 证伪** ⇔ 训练列与 v1 相对差中位 ≤ 1e-5。其余(找不到训练矩阵、两者都不匹配)= 不可判, 并如实写出缺什么。
- 存活时量化: LIVE_D2 期部署书在非 8h 名上的 gross 份额与 D2/REAL 价格盈亏份额(书层, 描述)。**不主张该错配造成了多少亏损** —— 那需要重算模型分数, 本轮不做。

### H3 · 边的半衰期缩短(拥挤/衰减)
- 信号层滞后剖面: 腿 l ∈ {fund, king, f10}, 锚 i, 滞后 h = 0..23: 与装置 `legs()` 同式建单位 gross 秩书 z_l(i)(因果合格 = y4[i−1] 有限; fund = 829 基内秩), LR_l(i,h) = Σ_n z/g · nan→0(y4[i+h, n]) · 1e4。GATE LAG0: h=0 的 fund/king 序列在元行 ≤ 2026-08-31 上与 NW_s42 臂存档的 `legs_fund`/`legs_king` maxabs ≤ 1e-9。
- E0_T = mean_{i∈T} LR(i,0)(前 4h); E1_T = mean_{i∈T} Σ_{h=1..23} LR(i,h)(4h–96h, 覆盖 SMA=0.1 EMA 书 92% 的持仓记忆)。T 只取 i+23 行 y4 可得的锚。
- 目标: fund × {T_A = M2026_08, T_L = LIVE_D2 期}, king × T_A, f10 × T_A; 参照 H1_2026。ΔE = E_T − E_H1。
- 单格: **HALF-LIFE** ⇔ ΔE1 判决区间上界 < 0 且 E0_T ≥ 0.75·E0_H1 且 ΔE0 判决区间含 0(晚段边没了、早段边还在)。**LEVEL** ⇔ ΔE0 判决区间上界 < 0 且 (E0_T/E0_H1) ≤ (E1_T/E1_H1) + 0.25(早段跌得不比晚段少 = 整体水平下移, 不是半衰期)。**NO-DROP** ⇔ ΔE1 点估计 ≥ −0.25·|E1_H1|。其余 UNDECIDED。
- **H3 存活** ⇔ fund 腿在至少一个目标上 HALF-LIFE。**H3 证伪** ⇔ fund 腿在两个目标上都是 LEVEL 或 NO-DROP。其余不可判。king/f10 格只作补充。
- F_H3 的 K = 8(ΔE0, ΔE1 × 四个 腿×目标)。描述另报: 各期完整剖面与累积半程 t½ = min{H: Σ_{h≤H} ≥ 0.5·Σ_{h≤23}}。

### H4 · 价格对 carry 的补偿关系(P4 的 77%)在实盘窗断裂
- 队列 C = 深负费率空头: 回放 smr_n < 0 ∧ rn8_n ≤ −0.0010(装置 FTRIM 输入); D2 w_n < 0 ∧ RN8(x0910 面板 E 行) ≤ −0.0010; REAL q_n < 0 ∧ RN8(生产者账本 E 时刻最新行, 新鲜度 ≤ 12h) ≤ −0.0010。**这是 r15 的 'deep' 集, 不是 'both'(双链标记)集**, 声明。
- 队列直接比 ρ_P = mean_P(Σ_{n∈C} pnl_n / gt) / mean_P(Σ_{n∈C} carry_n / gt) = 队列每付 1 单位 carry 挣回的价格 P&L。REAL: pnl = price_n, carry = −funding_n。
- 臂基 κ_P(r15 原定义)= mean_P(pnl_F − pnl_C0)/mean_P(carry_F − carry_C0), F = r15 ARM-F(FTPOS=1)`r15_structural/receipts/arms_rec/F_s{42,2027}.npz`, 仅 C0 两种子、仅至 2026-08-30 20Z(NW 无对应臂, §10)。期间: Y2022H2, Y2023, Y2024, Y2025, H1_2026, M2026_07, M2026_08, LIVE_REPLAY。描述; W_ALPHA 上 κ 必须复现 r15 的 0.185/0.240(GATE R)。
- **H4 存活** ⇔ ρ_H1 判决下界 > 0 且 ρ_{LIVE,D2} 判决上界 < 0.5·ρ_H1 且 ρ_{LIVE,REAL} 判决上界 < 0.5·ρ_H1(REAL 原值与 ÷0.835/÷0.733 换算值都满足)。**H4 证伪** ⇔ ρ_{LIVE,D2} 与 ρ_{LIVE,REAL} 判决下界都 ≥ 0.5·ρ_H1。其余不可判。F_H4 的 K = 3。

### H5 · 2023 的亏损与 2026 实盘窗的亏损是不同机制
- c1(状态): SIGF < 4.75(P8 阈)的锚份额, Y2023 vs LIVE_D2 期。
- c2(价格/carry 比): π_P = mean_P(price)/mean_P(carry)。Y2023 取回放臂; LIVE 取 D2 与 REAL。Δπ = π_LIVE − π_2023。
- c3(空头半区单位 gross 价格边): σs_P = mean_P(Σ_{side<0} pnl / gt) / mean_P(Σ_{side<0} |pos| / gt)。Δσs 同。
- **H5 存活(不同)** ⇔ |c1 差| ≥ 0.50 且(Δπ 在 D2 与 REAL 上判决区间都不含 0, 或 Δσs 在 D2 与 REAL 上判决区间都不含 0)。**H5 证伪(相同)** ⇔ |c1 差| ≤ 0.20 且四个判决区间都含 0 且 |Δπ| ≤ 0.25|π_2023|、|Δσs| ≤ 0.25|σs_2023|(D2 与 REAL 点估计)。其余不可判。F_H5 的 K = 4。
- 腿不作 H5 判据: A0 的 king 腿 2024-01-01 前恒 0、F10 腿 2023-01-01 前恒 0(r15 §1), 2023 与 2026 的腿结构不同; 腿分解只描述。

## §7 六项交付的精确计算

**(1) 排序格表**。目标 T ∈ {M2026_07, M2026_08, LIVE_REPLAY, Y2023}(回放, 格 = 分量{price, carry, cost} × 边{long, short} × 腿{king, fund, f10}, 18 格)与 LIVE_D2(分量{price, carry} × 边)、LIVE_REAL(分量{price, carry, cost} × 边), 参照 H1_2026(回放同臂)。格对 Δg 的贡献 = +Δprice / −Δcarry / −Δcost, Δ = mean_T − mean_H1。**逐格精确可加: Σ 格 = g_T − g_H1**(断言)。状态维: 对六个主状态 S 各自, (五分位 b × 格 c) 贡献 = f_{T,b}·m_{T,b,c} − f_{H1,b}·m_{H1,b,c}(Σ_{b,c} = g_T − g_H1, 断言), 并拆 mix = Σ(f_T − f_H1)·m_H1 与 within = Σ f_T·(m_T − m_H1)。按 |贡献| 排序列前 30, 每格 CI95(k=2)。REAL 对回放参照的差是跨仪器的, 表头标注并给 ÷0.835/÷0.733 换算列。

**(2) 价格边消失而 carry 拖累照付的月份**。参照 P_ref = price_H1, C_ref = carry_H1(同臂)。月 M「价格边没了」⇔ price_M ≤ 0.25·P_ref 且 price_M 判决区间上界 < P_ref(F_MONTH, K=10: M2026_01..08 共 8 格 + LIVE_D2 + LIVE_REAL; REAL 用原值与 ×0.835 参照双判)。「carry 照付」⇔ carry_M ≥ 0.75·C_ref 且 carry_M CI95 下界 > 0。**消失月** = M2026_01..M2026_08 中最早的、同时满足两条、且其后每个月直到 M2026_08 以及 LIVE_D2、LIVE_REAL 都满足「价格边没了」的月; 若只有 LIVE 满足 ⇒ 报「只在实盘窗」; 若没有 ⇒ 报「没有这样的月份」。四臂必须给出同一个月。另附 M2025_01..M2026_08 逐月 price/carry/cost/g 与 CI95(k=1)。

**(3) H4 补偿比按期**: κ_P 与 ρ_P 的逐期表(§6 H4 期间 + LIVE_D2/LIVE_REAL 的 ρ), CI95(k=5), 以及 §6 判决。

**(4) H2 核实**: §1 F1–F8 逐条复核; E2a/E2b 表; H2 判决; 若存活则量化受影响名在 LIVE 窗 fund 腿的 gross 与 P&L 份额 —— 腿层只在 LIVE_REPLAY(回放逐腿)可精确给; LIVE_D2 期给 fund 信号层单位秩书的 gross 份额与书层 D2/REAL 的 P&L 份额(层级在表头声明)。**无论判决如何都报 15 名在 LIVE 窗书层 gross 与 P&L 份额**(描述)。H2b 同节。

**(5) 实盘窗在历史状态分布中的位置**:
- (5a) LIVE_D2 期六个主状态(及次要状态)均值在 PRE_LIVE 锚分布中的百分位; 以及在 PRE_LIVE 内全部「长 n_L 锚、步长 6 锚」连续窗均值分布中的百分位(n_L = LIVE_D2 锚数)。
- (5b) 近邻类比: 坐标 = 各主状态在 PRE_LIVE 锚分布中的经验百分位; 实盘向量 = LIVE 均值状态的百分位; 取欧氏距离最近的 1000 个 PRE_LIVE 锚; 报其 g、price、carry、cost 均值与 CI95(k=8)、年份构成。
- (5c) 反常检验: 同 (5a) 的历史窗, 每窗统计 g_net = mean(net_ex/gt) 与 g_pre = mean((pnl_ex − carry_ex)/gt), 窗均值状态向量用同一百分位变换; 条件集 = 距实盘向量最近的 10% 窗。实盘统计: REAL 的 g(原值与换算值)对 g_net, D2 的 g_pre 对 g_pre。报无条件与条件百分位。**判读**: 条件百分位 < 2.5%(REAL 原值、REAL 换算、D2 三者都满足)⇒ **ANOMALOUS**; 三者都 ≥ 10% ⇒ **WITHIN RANGE GIVEN STATE**; 其余 INTERMEDIATE。窗口重叠, 百分位是描述量, 不当作 p 值。

**(6) H5**: §6 H5 的 c1/c2/c3 表与判决, 附 Y2023 与 LIVE 的完整分量×边(×腿, 回放)描述。

## §8 结果使用前必须通过的门(任一失败 ⇒ 依赖它的读数不报, 写明失败)

| 门 | 内容 |
|---|---|
| GATE P | 派生装置 `T1_INSTR=1` 的 `d30_n2_c42_{rec,W}` 与 `S0_{rec,W}` 对 r18 arms 四个文件**逐位相等**(np.array_equal, NaN 位置相同) |
| GATE I | §3.8 恒等式, 四臂全部锚 |
| GATE X | x0910 元与原元重叠行(E ≤ 2026-08-31 20Z): members 逐锚相等, y4 逐值相等(NaN 位置相同); x0910 面板与 v2ext 重叠行 f_fund_now/f_fund_iv/f_fund_ema_v1 逐值相等 |
| GATE S | §4 因果扰动测试 |
| GATE LAG0 | §6 H3 |
| GATE R | r15 `F_s42` 所配 A0 = r18 C0_s42 rec(pnl_ex/carry_ex/cost_ex/gross_total 逐位); W_ALPHA 上 κ 的 Δpnl/Δcarry 复现 r15 表(|Δ| ≤ 5e-4) |
| GATE L | 本轮 REAL 提取在 r6 `judge1_r6/j1_realized.json` 覆盖的锚上逐锚复现其 price/fund/fee/timing(|Δ| ≤ 1e-6 USD); 不等的锚列出并给出原因(账本追加/去重), 不静默修正 |
| GATE D2 | 本轮 D2 在 W5_R6 上逐锚价格与 r6 D2-price(`j1_recon_rows.json` 或 `j1_final.json` 所存序列)相等到 1e-6, 若 r6 未存逐锚序列则复现其均值 −0.7373(W5, n=78)到 1e-4 |
| GATE H2 | 15 名在副本 aux 的 `ledger_tail` 与 `ema` 中存在 |
| GATE E | 每个装置以 `env -i` + 白名单启动并在文件内断言; 装置自报 self_sha256 与预注册 sha |

## §9 装置、环境、纪律

- 装置(`T1/devices/`): `mk_t1_device.py`(由 pod2 上 `w10_sleeve_r18.py` sha `9b8a6323…` 以只出现一次的字符串替换生成 `w10_sleeve_t1.py`, 旋钮 `T1_INSTR`, 默认 0 逐位不变)· `t1_drive.py`(pod2; GATE P/I; 四臂)· `t1_states.py`(pod2; 状态 + GATE X/S)· `t1_lags.py`(pod2; H3 + GATE LAG0)· `t1_d2.py`(pod2; D2 逐名)· `t1_realized.py`(本机; REAL 逐名 + GATE L)· `t1_h2.py`(本机; E2a/E2b)· `t1_h2b_train.py`(pod2; 训练列比对)· `t1_judge.py`(pod2; 全部统计 → `RECEIPT_T1_judge.json`)· `t1_tables.py`(本机; 从收据渲染表格)。
- pod2: 只用 CPU, 目录 `/workspace/uplift_r2_2026-09-13/T1/`; 每步前后 `nvidia-smi` 必须读 0 % / 2 MiB 并入收据; PID 333197/339489 只读状态(`ps -o pid,stat`)入收据, 不发任何信号; 负载 > 16 则排队。
- 环境白名单 `{PATH, HOME, LC_CTYPE}` + 装置子进程精确字典(同 r18); 口径旗标前缀出现在父环境即拒绝启动。本机 `/usr/bin/python3`。
- 不提交(lead 提交)。收据与装置 SHA256SUMS 写在 `T1/SHA256SUMS.txt`。

## §10 事先声明的不可判/边界(先于数字)

1. **LIVE 窗 2026-08-31 之后没有腿拆分**: 生产者只存半书(king 半 `weights/`、F10 半 `state_H_f10_*`)与合成书, 不存逐腿分量; 回放腿(king v3-on-v4 数组、F10 A0 预测)在 2026-08-30 20Z 截止。九月只有 fund **信号层**(x0910 面板)与书层 D2/REAL。
2. **D2 无成本项**; REAL 的成本 = 实付费 + timing, 与回放拟合成本模型不同口径。
3. **状态变量止于 x0910 面板的 2026-09-10 00Z**; LIVE_REAL 在 09-10 04Z..09-11 20Z 的锚没有状态, 状态条件读数只用有状态的锚。
4. 臂基 κ 只有 C0 两种子(r15 未在 NW 装置上跑 ARM-F)。
5. 回放 A0 的腿本身是 v3 谱系(king `SLOW_v3_on_v4axis`, F10 `f10_A0`; r15 §1 / CLOSEOUT A-1), 本轮照用并声明, 不修。
6. REAL 与回放的幅度差(P2 斜率 0.835 / 资金费 0.733)只做敏感性, 不校正数据。
7. H2b 若存活, 本轮**不**重算模型分数、不估计它造成的盈亏; 只核实口径与受影响份额。
8. 窗口(LIVE ≈ 90 锚 ≈ 15 日)功效低: 许多判读预期落在「不可判」, 那是结果, 不是失败。

## §11 修订规则
任何对本文的修改必须写成 `PREREG_AMENDMENT_<n>_T1_….md`, 在对应结果数字产生之前冻结 sha, 保留原失败读数于收据; 结果之后的修改一律只能进 RESULT 的「偏离」节并标 POST-HOC。
