> **创建:** 2026-09-23 09:5xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(换装包执行代理,受 lead 派) | **状态:** **BLOCKED(停在第 1 步差异清单)** —— 未改生产者副本、未做平价、未导出模型、未写部署手册 | **作废条件:** NEW 训练构造(`build_combo_inputs.py` eb708c5a / `feature_contract.py` e4338749 / `f8_candidate.py` 4d495d06)、NEW 模型文件、或生产者 `shadow_loop_v3.py` 6080073b / `combo_stage.py` fb5a9407 / `dlw_features.py` 29ae6a98 / `f8_higher_order_features.py` 2c500c7a 任一改变

# 换装包(NEW King + F10 s42):第 1 步差异清单 —— 发现服务时无法短时安全改掉的差异,按令停下

相关:Stage 1 结果 `docs/RESULT_old_vs_new_models_same_engine_2026-09-23.md`(判词 UNDECIDED);研究员输入复审 `REVIEW_model_inputs_2026-09-23.md`(研究员工作树 `codex_combo_20260923/`)。

## §0 结论(白话)

**NEW 两个模型(King、F10)的训练特征是在一个比生产者能服务的更大的名单上算的。** NEW 每个锚的"成员"(截面秩、J/H 状态、F89 秩化都在这个名单上算)是从合法掩码(可交易 W24H ∧ 判活,829 名轴上约 669 名)里按流动性取前 400;生产者只抓 `symbols_live` 那 450 名的 K 线,其余名在滚动缓存里整列为空。

实测(收据 `multi_asset/exports/research/swap_new_2026-09-23/receipts/pop_check_pod.json`):

- 在研究员 NEW 轴与生产快照重叠的全部 10 个锚(2026-09-17 12Z → 09-19 00Z)上,NEW 400 名成员里有 **100 名在生产滚动缓存中近 7 天没有任何一根 bar**;生产当锚服务的 400 名里只有 300 名与 NEW 相同。
- 这 100 名包括股票永续(AAPL/NVDA/TSLA…)、商品(XAU/XAG/NATGAS/COPPER)、杠杆 ETF(SOXL/TQQQ/SQQQ)、pre-IPO(ANTHROPIC/OPENAI)以及不在 live 名单里的加密名(ALCH/ANIME/ASTR/KNC/MASK…)。全名单在收据 `last_axis_anchor`。
- 不是近期偶然:NEW 成员中不在 `symbols_live` 的名,逐年平均 46.5(2022)/ 63.6(2023)/ 91.6(2024)/ 95.6(2025)/ 57.8(2026)个/锚,占成员格 34% / 34% / 34% / 25% / 14%;2026-09 平均 90.0(81–100)。

**为什么这是硬阻断:** King 78 列里 38 列、F10 82 列里 40 列是"成员内截面秩";F89 的 A–G、J 共 69 列在成员行上再秩化(`f8_higher_order_features.py:87-97,345`),H、I 共 20 列由 82 列成员秩与成员截面状态构成(H 的截面离散度按成员集算、180 锚因果 z,`:348-360`;J 的 24h 前秩按当时成员集,`:329-336`)。成员集不同 ⇒ **即使对两边都有的 300 个名字,每一个秩特征的值都不同**。要让服务时特征等于 NEW 训练构造,生产者必须:(1)把 K 线/资金费抓取扩到约 669 名(改 King 管线 `shadow_loop_v3.py:406` 的抓取宇宙,增加场所请求权重,与实盘共用 IP 权重,见 E-0919-V);(2)为新增约 220 名回补 40 天 5m 历史(大量 REST 拉取);(3)在服务时实现可交易 W24H(SPEC_TRADABILITY)与判活掩码,并为 J/H 所需的过去 ≥180 个锚持久化逐锚 as-of 成员。这不是"最小改动",也不能在今天的静默窗内安全完成。任何"在 450 名上按 NEW 规则选成员"的做法都是近似,按令不做。

因此第 2–6 步(副本改动、平价证明、模型导出、钉变更、部署手册)**均未开始**。本文只交付第 1 步差异清单与阻断证据。另有两项服务时必须改、同样不能短时安全改掉的差异(D3 收益通道精度/裁剪、D10 资金费区间来源),即使 D1 解决也要一起处理,列在 §1。

## §1 差异清单(NEW 训练构造 vs 生产服务构造)

NEW 源码路径均在研究员工作树 `.claude/worktrees/codex-strategy-uplift-20260920/multi_asset/experiments/codex_combo_20260923/devices/`;生产源码在 `~/wide_shadow/`(与研究员 `vendor_live/` 副本逐字节同 sha,已核)。"必须改"= 服务时必须改才能让特征/目标等于 NEW 训练构造;"只历史"= 只影响历史重建,当前锚服务无关。

| # | 项 | NEW 训练构造 | 生产服务构造 | 服务时 | 能否短时安全改 |
|---|---|---|---|---|---|
| **D1** | **成员人口** | 合法掩码 `member_mask_tradable_AND_live_W24H_cachegrid.npz`(`build_combo_inputs.py:27,61`)∧ 覆盖 ≥0.95 ∧ 波动 ≥1e-4 ∧ 流动性有限,按流动性稳定排序取前 400(`feature_contract.py:50-55`;调用 `build_combo_inputs.py:123`) | 只抓 `symbols_live` 450 名(`shadow_loop_v3.py:406`);成员 = 覆盖 ∧ 波动,无合法掩码,前 400(`shadow_loop_v3.py:497-509`) | 必须改 | **否 —— 阻断**(见 §0) |
| **D2** | J/H 历史成员 | 逐锚 as-of 成员(`build_combo_inputs.py:123-125,158` 写入 `members`;F89 读它) | 所有历史锚都填当前 pm(`combo_stage.py:147-150`);J 用 24h 前锚(i−6)的成员秩(`f8_higher_order_features.py:329-336`),H 用 180 个先前锚的成员截面离散度(`:348-360`) | 必须改 | **否**(依赖 D1:需要全人口数据与逐锚合法掩码) |
| **D3** | 收益通道口径 | 由原始对数价差 `expm1(Δlog p)` 得到的 float32 收益,不裁剪;补洞格与未观测区间置 NaN(`build_combo_inputs.py:85-88,96-105`;F89 经 `patched_market.py:13,17,23` 同源) | K 线 close 比值,存 float16 并裁剪到 ±0.30(`shadow_loop_v3.py:422,426`;裁剪表 `:173`,`clipch` `:350`) | 必须改 | **否**:缓存只存 f16 收益,没有 close 价历史;要么生产者改存 float64 close 并回补 40 天,要么改训练口径。量级参考:研究员收据 `raw_feature_returns_changed_gt_1e5 = 960`(全史只有 960 格两者差 >1e-5;其余格差在 f16 舍入级,本代理未逐格测) |
| D4 | F10 82 列存储精度 | float32(`build_combo_inputs.py:147`) | float16(`dlw_features.py:78`),推理前再转 f32(`combo_stage.py:184`) | 必须改 | 能(改 dtype) |
| D5 | King/F10 窗口累加精度 | float64 累加(`feature_contract.py:37-48`;docstring 明写"服务必须用同一核") | King:float32 直接求和(`shadow_loop_v3.py:487-495`);F10:float32 值 → float64 cumsum(`dlw_features.py:49-65`) | 必须改 | 能 |
| D6 | 空窗编码 | 窗内无有限值 ⇒ 均值/标准差为 NaN ⇒ 值 0、不入秩(`feature_contract.py:47`;`build_combo_inputs.py:149-152`) | 分母取 max(n,1) ⇒ 均值 0、标准差 0 且**参与排秩**(`shadow_loop_v3.py:489-495,532-535`;`dlw_features.py:55,59,63-65,84-89`) | 必须改 | 能 |
| D7 | F89 趋势块 | 稳定局部趋势 `stable_trend_block`(`stable_trend_reference.py:4-20`,经 `derive_f8_candidate.py:20-28` 替换) | 全局累积价格/时间矩(`f8_higher_order_features.py:204-216`) | 必须改 | 能(换成 `f8_candidate.py` 的补丁代码) |
| D8 | F89 缺失支撑集 | 14 处补丁:分块和不完整 ⇒ NaN、dhi/dlo/ppct/SR30/RVj/jp/ac 完整窗门、bv 下界 lo+1、Amihud/Kyle/成交流共同人口(`derive_f8_candidate.py:29-46`) | 原阈值(<12、<72、w//4 等) | 必须改 | 能 |
| D9 | btcv(H 块输入) | BTC 2016 窗 [E−2015,E] 收益标准差,覆盖 <95% ⇒ NaN(`build_combo_inputs.py:156`) | `nanstd(r5[i−2016:i])` 即 [E−2016,E−1] 不含当根,f16 收益,早期回填首个满窗值(`combo_stage.py:77-103`,窗 `:87`,回填 `:90`) | 必须改 | 能(但输入受 D3 影响) |
| **D10** | 资金费 EMA 区间来源 | 官方区间优先(`build_combo_inputs.py:129-141` 调 `official_intervals`),未知区间使 EMA 中断重置(`feature_contract.py:82-83`),衰减 2^(−Δt/3d)(`:87`) | 区间由相邻结算时差四舍五入到 {1,2,4,6,8}(`shadow_loop_v3.py:473`),EMA 不重置、Δt 下限 1s(`:477-479`),初值来自部署时 bundle `fund_ema_v1_state.json`(`:288`) | 必须改 | **否(需设计)**:服务时要官方区间需新增场所调用;现有 EMA 状态是按推断区间累出来的,要么重播种要么接受差。`official_intervals` 在 `uplift_20260922/devices/corrected_inputs.py`,本代理**未打开**,细节以其源码为准 |
| D11 | F10 的 fund_ema/fund_now 新鲜度 | 事件 ≤ 锚且 ≤12h 新鲜,否则 NaN→0(`feature_contract.py:89-92`;`build_combo_inputs.py:153`) | 直接取 `aux.ema.acc` 与账本末行费率,**无新鲜度**(`combo_stage.py:161-173`) | 必须改 | 能(King 侧已有 12h:`shadow_loop_v3.py:538-545`) |
| D12 | 资金费腿秩基 | 合法掩码 ∧ 有新鲜 EMA 的名(829 名轴内)(`combo_legs.py:37-39`) | exchangeInfo TRADING USDT 永续 ∪ live,且 ≤12h 有结算(`shadow_loop_v3.py:448,546-549`,`xz_in_base` `:100-111`) | 必须改(影响 combo 目标,不影响模型特征) | 否(依赖 D1 的合法掩码);研究员自己把它声明为"候选政策差异"(`combo_legs.py:5-6`) |
| D13 | FTRIM 的 rn8 | 最近结算 ≤12h 新鲜、官方区间(`feature_contract.py:90-92`;用于 `combo_target.py:33-34`) | 账本末行,无新鲜度,区间缺省 8(`combo_stage.py:266-273`) | 必须改 | 新鲜度能;区间部分随 D10 |
| D14 | 流动性排序并列 | `argsort(kind='stable')`(`feature_contract.py:54`) | 默认快速排序(`shadow_loop_v3.py:509`) | 必须改 | 能 |
| D15 | 席位 w3 | 由 NEW King z 的腿收益历史算(`combo_legs.py:22-44`) | 由 bundle `leg_returns.npz` + live 账本(OLD King z)算(写者 `shadow_loop_v3.py:309-311,572,594`;combo 读 `leg_returns_live.json` 末 950 条,`combo_stage.py:57-64`) | 状态量,需裁定是否用 NEW 历史播种 | 能(播种),但属书行为,需用户字 |
| D16 | kc/fc 连续状态 | 研究链自 2023-01-01 零起、各自推进(`continuous_combo.py:29`) | 生产状态由 OLD 模型推进(`combo_stage.py:290-298`) | 状态量;换装后按 α=0.1 收敛(半衰期约 7 锚) | 需裁定(研究链止于 09-19,无法用它播种当前状态) |
| D17 | 成员选择是否依赖未来标签 | 不依赖:标签只作训练掩码(`feature_contract.py:57-70`;`build_combo_inputs.py:122-123`) | 服务时本就没有标签 | 只历史 | — |
| D18 | King 特征时钟 | [E−w+1,E](`feature_contract.py:41`,hi=rows+1) | [E−w+1,E](`shadow_loop_v3.py:490`) | 无差异 | — |
| D19 | King 标签 | 原始复利 (E,E+48] 且全部收盘可观测(`feature_contract.py:57-70`) | 服务时无关 | 只历史 | — |
| D20 | F10 推理的 NaN 顺序 | 训练断言 171 列全有限(`train_f10.py:74`),`clamp((x−mu)/sd,−5,5)`(`:83`) | `nan_to_num(clip((X−mu)/sd,−5,5))`(`combo_stage.py:194`) | 输入全有限时等价 | —(数值平价未做) |

## §2 已核的身份(备后续使用;**未导出、未改任何钉**)

| 对象 | 文件 | sha256 | 训练标签截止 |
|---|---|---|---|
| NEW King 最新折 | `artifacts/king/king_2026.txt`(pod2 `corrected_combo_v1d/king/king_2026.txt` 同 sha) | `0585aad1e50493720a77b8df1ae77b877cf66797f3c4e6a1118653be20a8d182`(= `artifacts/king/TRAIN_RECEIPT.json` fold 2026) | `max_train_label_end` 1766361600 = 2025-12-22T00Z |
| NEW F10 s42 最新月折 | `artifacts/f10_completed/f10_s42/202609/model.pt`(pod2 `/tmp/codex_combo_20260923/f10_s42/202609/model.pt` 同 sha;`/tmp` 仍在) | `1d533ac1abcf05c0b2992de87246f2170313d1b07f6e59d9042064e919deb1e6`(= FOLD_RECEIPT `model_sha256`) | `ADMISSION.json`:`max_train_label_end` 1767744000 = 2026-01-07T00Z(`cutoff` 字段 2026-08-22T00Z,`test_start` 2026-09-01T00Z;训练器只取合格训练锚的前 85%,`train_f10.py:101-103,109`,所以实际标签末远早于 cutoff) |
| 在役 King 钉 | `~/dl_quant_live/config/book.json` `external_book.booster_sha_pin`(执行器 @ b66257b) | `8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282`(= `shadow_bundle/MANIFEST.json` 的 `slow2026.txt`) | — |
| 在役 F10 钉 | 同上 `external_book.f10_sha_pin` | `351ae26bd6b4a203431a280427fc0bbc968c66e903532168765d654e7e57b3a4`(= `fea171/f10_live_s42_np.npz`) | — |

`model.pt` 带 `state_dict/mu/sd/input_dim=171`(`train_f10.py:129`),将来可导出为生产的 numpy 格式;本轮因阻断未导出。

## §3 给 lead 的选项(不是建议,只列代价)

1. **服务侧扩人口**:生产者抓取宇宙扩到合法人口(约 669 名)+ 40 天回补 + 服务时可交易/判活掩码 + 逐锚成员持久化,再加 D3、D10 的数据口径改造。涉及 King 管线与场所请求权重,工程量以天计,需要新的预注册与复审。
2. **训练侧收人口**:按生产者能服务的人口(及其收益/资金费口径)重建输入并重训 NEW King/F10,之后平价可以做到逐位;但模型变了,Stage 1 的对照要重做。
3. 不换装。

## §4 本轮做了什么 / 没做什么

- 做了:通读 Stage 1 结果、研究员复审/输入验证/工作记录、NEW 构建与训练源码、生产者四个源码与执行器钉;在 10 个重叠锚上实测成员人口差异(两段装置 `pop_check_local.py`(本机,只读 `~/wide_shadow/state/snap/*` 与 bundle config)+ `pop_check_pod.py`(pod2 `/dev/shm`,只读研究员根),收据逐文件带 sha256)。
- 没做:副本改动、平价(a)(b)(c)、正控、模型导出、钉/配置变更清单、部署手册。没有写 `~/wide_shadow`、`~/dl_quant_live`,没有重载任何 launchd 服务,没有调用交易所,没有读 CFG-04/06。本机只跑了约 5 秒的只读提取(09:43Z,位于 08Z 锚静默窗内)。pod2 只在自己的 `/dev/shm/cc_swap_20260923` 写。
