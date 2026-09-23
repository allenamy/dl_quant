> **创建:** 2026-09-23 10:3xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(NEW_S 执行代理,受 lead 派) | **状态:** 冻结 —— 写于 NEW_S 任何模型、分数、收益数字之前(本文与 P1 可行性收据同一提交;P1 只含成员人口计数与算力估计,不含任何 NEW_S 模型或书层数字) | **作废条件:** 预注册 `PREREG_new_servable_models_2026-09-23.md`(db0123df7)§2/§3/§4 改动,或生产者特征源码(`shadow_loop_v3.py` 6080073b / `combo_stage.py` fb5a9407 / `dlw_features.py` 29ae6a98 / `f8_higher_order_features.py` 2c500c7a)任一改变

# 预注册 db0123df7 修订 1:范围调整 —— 生产者现行特征代码原样重放历史,只换模型

## 1. 来源(lead 转达用户裁定,2026-09-23 10:2xZ,原文要点逐条)

用户裁定:先做「既有策略在正确口径重训 + 重组装 + 评估」,最快;新模型/新策略之后再议。据此:

1. **本轮不修生产者服务时的特征缺陷**(D4–D9、D11、D13、D14 全部保持原样)。训练特征 = **生产者今天线上实际运行的特征代码**(`~/wide_shadow` 现版本,记录各文件 sha)原样在历史上逐锚运行产生 —— 「一份实现、训练向服务对齐」,上线时生产者特征代码**零改动**,只换模型文件与 `booster_sha_pin` / `f10_sha_pin`。D2(J/H 用「当锚的 pm」回看历史)、D3(f16 裁剪缓存通道)、D10(由结算间隔推断的资金费间隔)也都按生产者现行做法在历史上复现,不另修。
2. **训练侧必须改正的保留**:标签用未裁剪的原始价格收益、缺失标签不填 0(拒绝/掩掉);成员选择不得以未来标签是否有限为条件;King 用生产时钟;资金费 EMA 用服务时版本。
3. **成员集**:历史各锚的候选 = 当时的合法掩码 ∧ 加密币类(不能用今天的 450 名单倒填);在候选上**套用生产者自己的成员选择规则**。P1 实测服务时按此规则会选中、但不在生产者 450 拉取名单里的名字数与名单。若为 0 或很少,生产者只需扩拉取名单(配置/数据层,不改特征代码);若很多,停下交回。
4. 其余(King/F10 配方、两个种子、组合生成、认证引擎评估、S1–S5 决策规则、平价硬门、部署手册)不变。平价在这个设计下应当**逐位**成立(同一份代码),以逐位为门,做不到要定位原因。

## 2. 对预注册 §1 的改动(§2 评估、§3 决策规则 S1–S5、§4 两道硬门 **一字不改**)

| 预注册 §1 条目 | 原文 | 修订 1 |
|---|---|---|
| 1.1 成员规则 | 合法 ∧ 加密币类,按流动性取前 400 | 候选 = 合法 ∧ 加密币类;在候选上跑**生产者自己的成员筛**(`shadow_loop_v3.py` L497–509:7 天覆盖 ≥ 0.95、7 天波动 ≥ 1e-4、按 7 天 log_qv 均值取前 400,默认快排 argsort)。流动性度量、覆盖/波动门、排序实现都是生产者的,不是 NEW 的 `select_members` |
| 1.2 一份实现 | 生产者特征代码修 D2、D4–D9、D11、D13、D14 后训练与服务共用;D3/D10 训练向服务对齐 | 生产者特征代码**零改动**,原样逐锚重放历史;D2/D3/D10 与其余全部差异按生产者现行做法复现 |
| 1.3 生产者供数 | 拉取名单覆盖成员规则可能选中的名字 | 不变;另须满足「服务时按生产者规则在拉取名单上选出的成员 = 训练规则在候选上选出的成员」,P1 实测 |
| 1.4 模型与配方 | 同 NEW,只换输入;两种子;部署种子 42 | 不变 |
| §4.1 平价 | 逐值相等或写明理由的浮点容差 | **逐位为门**;不逐位处必须定位原因 |

## 3. 执行口径(本代理落盘,先于任何 NEW_S 数字;不属判据)

1. **加密币类字段**:lead 指定的本地文件 `~/dl_quant_live/state/exchange_info_cache.json`(660 名)**没有标的类型字段**(只有 tick/step/min_qty/max_qty/mkt_max_qty/mkt_step/min_notional 七个过滤器字段)。改用仓库内已入库的本地场所快照 `multi_asset/exports/research/retrain_2026-09/universe_crypto_2026-09-08/venue_class_20260908.json`(sha256 `fa9196a34ce92028…`,2026-09-08 一次公开 exchangeInfo 落盘,897 名,字段 `underlyingType` / `contractType`)。**不调交易所。**
2. **加密币类规则(冻结)**:`crypto ⇔ underlyingType ∈ {COIN, INDEX} ∧ contractType == PERPETUAL`;快照里没有的名(09-08 前已下架,31 名)按加密币保留,**仅当**其缓存首根 bar 早于快照内任一 `TRADIFI_PERPETUAL` 名的最早首根 bar(实测 `XAUUSDT` 2025-12-11),否则拒绝构建。**更正留痕**:我第一版写的是「最后一根 bar 早于 2025-01-01」,P1 首跑据此对 5 名(AERGO / BDXN / BTCST / EOS / SXP,首根 bar 2022-01 至 2025-06,均为加密币)报 `REFUSE_UNCLASSIFIABLE`;该条件用错了量(品种类别由**上市**时点决定,不由下架时点决定),改为首根 bar 判据后 31 名全部早于 2025-12-11,判为加密币(收据 `P1B_FETCHLIST.json` `unknown_names_rule_check`)。这次改动发生在 P1 人口计数之后、任何 NEW_S 模型数字之前。`INDEX` 保留的理由:该类在场所里只有 `DEFIUSDT` / `BTCDOMUSDT` / `ALLUSDT` 三个**加密指数**(contractType 为 PERPETUAL 而非 TRADIFI_PERPETUAL),`BTCDOMUSDT` 就在生产 450 名单里;同一定义是用户 09-08 裁定的 CRYPTO 口径(`REVIEW_codex_early_batch_2026-09-08.md` ADDENDUM 3/4)。预注册 1.1 的「指数」按其上下文「非加密合约」读作非加密指数 —— **此读法请 lead 确认**;若 lead 要求连加密指数一并排除,影响至多 3 名,成员与特征须重算。
3. **合法掩码**:`/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz`(sha256 `f752d8ae…`,可交易 W24H ∧ 判活,与 NEW 同一文件)。
4. **历史滚动窗**:锚 A 的输入 = 生产者在 A 时持有的滚动缓存 = 历史缓存 `dlnative_5m_wide829_f16_holefix2_x0918r.npz`(sha256 `08bb2957…`)中以 A 行结尾的最后 11520 行(`CACHE_ROWS`,40 天;缓存开头不足 40 天的锚取从缓存首行起的全部行,等同于生产者从缓存首日起运行)。非候选列整列置 NaN(= 生产者拉取名单 = 候选)。
5. **补洞格**:`holefix2r_cells_x0918r.npz` 所列格(无官方来源的合成 bar,判活规则同样不认)七通道一律置 NaN —— 实盘生产者从不摄入合成 bar。其余格按缓存存值原样(f16、ret5 裁剪 ±0.30,即 D3 的生产口径)。
6. **King 特征**:`shadow_loop_v3.py` L486–L553 的源码行原样编译为函数体执行(行号与首末行文本、文件 sha 均断言),包括成员筛、82 列、King 的 fund_ema/fund_now(12 小时新鲜度,只对拉取名单)。
7. **F10 特征**:`combo_stage.py` L147–L185 的迷你管线原样:同一 11520 行窗写成迷你缓存,targets 的每个历史锚成员 = 当锚 pm(D2),`_btcv_series` 由 AST 原样抽出,资金费面板只填最后一行(全体有 EMA 状态的名的 acc 与账本末行费率,无新鲜度),然后以子进程运行生产的 `dlw_features.py` 与 `f8_higher_order_features.build()`(F171_* 环境变量同 L159–160),取当锚行。若为算力只保留 pm ∪ {BTCUSDT} 列,必须先在声明的样本锚上与 829 列原样运行**逐位**相等,否则不用。
8. **资金费状态**:生产者的资金费增量循环(`shadow_loop_v3.py` L451–L484:0.9×间隔跳过、`startTime=last_ts+1`、`endTime=A·1000+999`、`limit=100`、相邻结算时差取整到 {1,2,4,6,8} 小时、EMA 半衰期 3 天、Δt 下限 1 秒)原样在历史账本上重放;回放取数器只返回账本里 fundingTime ∈ [start, end] 的前 100 条。秩基名单 = 当锚候选(场所 TRADING 加密永续的历史代理)。状态从首个回放锚的空状态起步(生产者冷启动语义:首锚回看 40 天)。
9. **标签**:NEW 的 `dlw_targets.npz` `y4s`(原始价格 (E, E+48] 复利,区间内所有收盘可观测,否则 NaN);King 目标 = 当锚 pm 内有限标签 ≥ 50 时的截面秩;F10 损失用同一 y 与有效位,NaN 不作 0。
10. **腿与席位**(F10 训练的 Z24/ZFD/WL 与组合目标):生产口径 —— rev24 = King 块里 `wstat(0,288,"sum")` 的成员值取负后秩、fund = `xz_in_base(fe_v[m], base_vals)`、席位 = 生产者 L556–L596 的腿收益递推(f16 缓存 (A, A+4h] 求和、≥ 46 根有限、msharpe 900)。
11. **组合目标**:研究员 `combo_target.py`(d7577e82,核 `combo_stage.py` fb5a9407 的 `chain` / `exec_reshape` 原文)`publication='scaled_diagnostic'`,门失败 HOLD;输入换成上述生产口径(LIVE_MASK = 当锚候选、rn8 = 账本末行 rate×8/iv 无新鲜度、qv = 生产 qv4h)。状态自 2023-01-01 零起步,与 Stage 1 C5 相同。
12. **评估与统计**:Stage 1 装置原样(认证运行器主设置、32 路径、`ovn_stats.py` 判据窗/分段/自举);对照 OLD 与 OLD_HOLD 复用 Stage 1 已跑 NAV,配置逐字节对比。
13. **平价(P5,仅 SWAP 时)**:同一生产代码在实盘归档输入(`~/wide_shadow/state/snap/<A>/`,09-17 16Z 起)上与训练构建逐位比较 X78、X171、分数、组合目标;数据层差异(实盘拉取的 bar / 资金费事件 vs 历史缓存与账本、扩名前后成员集、补洞窗)单列定位,不以容差掩盖。
14. **环境**:历史重放在 pod2 上用与生产 venv 同版本的解释器与库(Python 3.14.4、numpy 2.5.2、scipy 1.18.0、pandas 3.0.5、lightgbm 4.7.0)运行,并以 `NPY_DISABLE_CPU_FEATURES` 关掉 AVX-512 分派(生产机 i7-9750H 只有 X86_V3);做不到时如实记录,不作为逐位失败的借口。

## 4. P1 可行性实测(人口计数与算力;不含任何 NEW_S 模型或书层数字)

收据目录 `multi_asset/exports/research/news_2026-09-23/receipts/`(装置在 `devices/`,pod2 日志在 `logs/`)。

1. **加密币类**(`P1_MEMBERS.json` `crypto_rule` + `P1B_FETCHLIST.json`):829 名轴上 COIN/PERPETUAL 646、INDEX/PERPETUAL 3、快照外已下架 31(首根 bar 全部早于 2025-12-11 ⇒ 判加密)⇒ **加密币类 680 名;排除 149 名**(EQUITY 130、COMMODITY 8、HK_EQUITY 6、KR_EQUITY 3、PREMARKET 2,全部 contractType = TRADIFI_PERPETUAL)。生产 450 名单里非加密 = 0;执行器缓存 658 名全部可分类。排除名单全文见收据 `excluded`。
2. **生产者需扩的名字**(2026-09-01 00Z → 09-19 00Z,109 锚;候选 = 合法 ∧ 加密,恒为 520 名,其中 519 过覆盖/波动门):
   - 训练规则选出的 400 名成员里**不在 450 名单**的:每锚 23–41 名(均值 31.7),9 月并集 **50 名**:ALCH ANIME ARK ARX ASTR AVA AXL AZTEC BAND BEAMX BTW CAP CKB CLANKER COW CTR CVC CYBER FLUX GLM GOAT GRAM GRVT HIVE ILV INIT KNC MASK MELANIA METIS MEW MTL NMR OG O POLYX PUMPBTC PUNDIX RAYSOL RED RE SLX SOMI STEEM SUN SUPER VTHO WCT ZEST ZRX。
   - 但生产者的成员筛是在**拉取名单上按流动性排前 400**,要与训练规则在候选上排出的 400 名逐名相同,拉取名单必须覆盖**整个候选池**(否则池内流动性更高的名不在名单里,排序结果就不同)。候选池不在 450 里的有 **72 名**(上面 50 名 + 1000000BOB 1000000MOG 1000CHEEMS ALL ALPINE ASR BNT CELR CTK DATAIP ETHW FRAX MAVIA MOCA RPL SANTOS SFP SLP SONIC SPORTFUN USTC XVS)。
   - **服务模拟**(生产者原码成员筛、无合法掩码、拉取名单 = 450 ∪ 这 72 名 = 522 名):9 月 **109/109 锚与训练规则逐名相同**。同一份名单放回 2025-07 → 2026-08 则几乎每锚都不同 —— 候选池逐月漂移(2025-07 成员里不在 450 的每锚约 105 名,2026-08 约 12 名),所以扩出去的名单要随候选池维护,这是数据层维护,不改特征代码。
   - **残余机制**(拉取全部 680 个加密名、同一模拟,2025-07 → 2026-09 共 2,671 锚):181 锚有差异,其中 74 锚在 2026-08 补洞期(合成 bar 使不合法的名仍过覆盖/波动门,属历史数据人工品);其余月份每月 0–27 锚、几乎都是 1 名之差,全部由「当锚不合法(24 小时无成交或无真实 bar)但缓存里有冻结行、仍过生产者覆盖/波动门」的名造成 —— 生产者的成员筛没有合法掩码,这类名在服务时会被选入而训练规则不会。要消除只能在生产者成员筛里加合法掩码(= 改特征代码,本轮禁止)。9 月 0 锚。(P1 的成员计数在缓存原值上算,未把补洞格置 NaN;P2 构建按 §3.5 置 NaN,补洞期成员可能与 P1 略有不同。)
3. **列裁剪逐位检查**(`P1_COLRESTRICT_BITWISE.json`):F10 迷你管线只保留 pm ∪ {BTCUSDT} 列,与 829 列原样运行在 5 个锚(2022-03-15、2023-06-30T04Z、2024-06-01、2025-09-01、2026-09-18T20Z)上 X82 与 X89 **逐位相等**(0 格不同),耗时约减半 ⇒ 历史构建用裁剪版。
4. **算力**:pod2 在他人负载(load 6–12)下,单锚原样重放(King 块 + F10 迷你管线,裁剪版)5.1 s(2022,139 名成员)/ 5.9 s(2023)/ 7.3 s(2024)/ 9.8 s(2025–26,400 名);全史 10,333 锚约 7.8 万工人·秒,10 个工人约 2–3 小时。资金费回放(顺序)约 10–20 分钟,先于特征。
