> **创建:** 2026-09-12 10:4xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 预注册(判据先于数字); 依赖 Phase 1 装置(`parity_replay_2026-09-12/devices/`, king 段 41/41 ≤1e-9, combo 段最新锚精确)与 12Z 快照起步门 | **作废条件:** Phase 1 装置换代; 研究员复核推翻任一判据; AMENDMENT 记录任何修订

# PREREG — 生产者平价装置 Phase 2: 线上策略在正确口径下的折外历史水平

## §0 问题
Phase 1 证明"装置 = 线上"(生产代码路径逐锚复现线上权重)。Phase 2 回答用户的问题: **线上这套完整策略(生产代码路径: 席位 / 平滑 / FTRIM / 宇宙 / combo 混合 / 执行重塑)在正确口径下的历史水平是多少**, 与研究回放 A0 / A1x 差多少。约束(研究员 0dfc0d87 §2): ① 不能直接拿在役 booster(训练到 08-31)回放历史 —— 样本内; ② 折外预测必须模拟**月度重训节奏**, 不能把逐年折外当月度策略; ③ king 的梯度截止 = 训练数据末锚, 不以 bundle 构建日代替。

## §1 装置(只换输入, 不改代码路径)
- 代码 = Phase 1 的 `shadow_loop_v3_replay.py`(生产 sha e9c98374…)+ `combo_stage_replay.py`(生产 sha b5c698f9…), **零新替换**; 装置 sha 与 Phase 1 相同才算同一装置。
- **5m 通道缓存** = pod holefix2 正典缓存(`dlnative_5m_wide829_f16_holefix2.npz`)转成生产者格式(`ts, data[T,829,7]` f16, 通道顺序 `ret5 range cpos log_qv log_cnt log_avgsz tbf`, 生产者 `CHN_CLIPS` 裁剪)。**先过 G2-A 通道平价门**(§3)。
- **king 预测** = 折外 booster 序列: Phase 2a 用现有逐年折外 `SLOW_v4`(月度重训不可得时的**保守替代**, 明写偏差: 比线上月度重训更旧); Phase 2b(可选, 需 pod2 CPU/GPU 预算与排队)按 RUNBOOK 月度节奏逐月重训 king 得到真正的月度折外序列。每个预测锚 E 只能用训练末锚 < E − 1 月的模型(梯度截止写进收据)。
- **F10/V2MAIN 预测** = 月折 mE1cX7 FIX7 折外(20 折 202501..202608)+ 2025 前的逐年折外拼接(与研究 `merge_mwf_v4b.py` 同法, 注明拼接边界)。
- **资金费账本 / EMA** = 面板 `f_fund_now` / 结算历史重建(生产公式 HL3d, 从冷启动递推; 与 Phase 1 逆推状态在重叠窗逐位对账 → G2-B)。
- **基名单 / 宇宙** = 面板有数据的名 ∩ live_pins(exchangeInfo 历史不可得, 明写为近似); **成员筛/流动性门/席位/平滑/FTRIM/combo** = 生产代码原样。
- **执行** = 100% 成交于 E 收盘(与研究一致, 便于对照); 敏感性臂 = exec 口径(E+24m 价格执行 Δw, r21 建议)。
- **记账** = v4 钉(meta y4 原始收益, 拟合成本 `costb_PWR_G230k`, g = net_ex/gross_total, UTC 日块自举 2000, rng [20260905,k]), 与 A0/A1x 同尺。

## §2 窗口与对照
- 全史 2022-01-31 → 2026-08-30 20Z(与研究 W_FULL 同轴; 前 900 锚席位 [1/3]*3 经 combo 掩码 = [0.5,0,0.5], 与 r18 暖机修复同义, 明写)。
- 对照: A0(研究回放, 在役形态的模型放 v4 轴)、A1x(v4 原生)、NW(r18); **主读数 = 生产路径书 vs A0 的配对 Δg 与 ΔSharpe, W_ALPHA / W_FULL / 冻结窗三窗并报, 逐年表负年显式, 2.0× 真 maxDD 阶梯**。
- 重叠窗(2026-08-03 → 09-12, 生产者缓存覆盖)上: 用**线上 bundle 预测**跑 Phase 2 装置(缓存来自 pod 而非 rolling.npz)必须复现 Phase 1 的权重(G2-C) —— 这一条把"缓存换源"与"预测换源"两件事分开。

## §3 门(冻结; 门红即停, 修订以 AMENDMENT 记录)
- **G2-A 通道平价**: 重叠窗(≥ 40 天)每通道每格: 两侧同为 NaN 或 |Δ| ≤ f16 一个 ulp(相对 2⁻¹⁰); 违例格 ≤ 0.1% 且**全部有归因**(事后回填 / 裁剪 / 时间对齐), 否则停。r17 发现的 qv4h 中位 |Δlog| 0.52 必须在此门解释清楚。
- **G2-B 资金费状态平价**: 重叠窗上重建的 EMA 与 Phase 1 逆推状态 |Δacc| ≤ 1e-9(2⁻³⁰)。
- **G2-C 换缓存不换预测 = Phase 1**: 重叠窗 41 锚 king 段 L∞ ≤ 1e-6, combo 段 L∞ ≤ 1e-6(快照起步锚)。
- **G2-D 因果**: 每个锚使用的 king/F10 模型的训练末锚 < E − 30 天(king)/ < 上月末(F10), 装置逐锚断言并写收据; 任何锚违反 ⇒ 该锚不计入且 RESULT 标红。
- **G2-E 红能力**: 把 F10 折外换成在役训练到 08-31 的 booster 跑 2026 段, 2026 年 g 必须显著抬升(样本内伪影可测), 作为"折外是有效控制"的证据; 数值只报不进主表。
- 判决词只用 (A)/(B)/(C) 三种(v4 判官同规则: 双种子 CI 下界 > 0 才 (A)); 分辨率 0.23 bps/锚/gross 以下的差异一律"不可区分"。

## §4 不主张
不主张任何候选改动的效果(候选在装置过门后另立预注册); 不替代研究回放的 A0/A1x 规划数, 直到 G2-A..E 全过且研究员复核; 不改任何生产文件, 不调 API。

## 收据 1 · G2-A 通道平价(2026-09-12 10:1xZ, pod2 CPU, 只读; `parity_replay_2026-09-12/phase2/G2A_channel_parity.json`, 装置 `phase2/g2a_channel_parity.py`)
- 输入: 生产者缓存快照 `producer_state_snapshots/1789200000/rolling.npz`(11,520 行 × 829 × 7 f16)vs pod `dlnative_5m_wide829_f16_holefix2.npz`(490,753 行 × 829 × 7 f16); 符号轴 829 **同序**; 通道顺序同(`ret5 range cpos log_qv log_cnt log_avgsz tbf`)。
- 重叠 2026-08-03 08:05Z → 2026-09-01 00:00Z, **8,256 个共同 5m 时刻**(pod 正典缓存止于 09-01 00:00Z)。
- **七个通道: 两侧同为有限的格上 |Δ| 最大值全部 = 0.0(逐位相等), 超 f16 ulp 的格 0/0; 「生产者有限而 pod 为 NaN」的格 0**; 「pod 有限而生产者 NaN」= 1.06M–1.91M 格 = 生产者只抓取 450 个 live 名而 pod 覆盖 829 名(宇宙差, 不是数值差)。
- ⇒ **G2-A PASS(通道值同源同算法; 用 pod 缓存喂生产代码不引入数值差)**。r17 记的「rolling.npz qv4h vs 面板 中位 |Δlog| 0.52」因此**不是 5m 数据差**, 是 4h 量的定义差(面板 qv4h 的构造 vs 生产者 `expm1(mean log_qv)×48`), Phase 2 里按生产者定义从缓存算 qv4h 即可, 不需要面板的 qv4h。
- 未覆盖: 09-01 00:00Z 之后 pod 正典缓存无行(月度补月后再测); 非 live 名字的通道值无生产者对照(Phase 2 只用 live 名子集 + 面板宇宙, 已在 §1 明写)。

## AMENDMENT 1(2026-09-12 14:4xZ, lead; 研究员 563e3470 `parity/RESULT.md` §3 更正, 接受)
- **G2-A 原字面门(重叠 ≥40 天; 829 名每通道每格同 NaN 或差 ≤ f16 一 ulp; 违例 ≤0.1% 且全归因)= NOT PASSED AS WRITTEN**: 实际重叠 2026-08-03 08:05Z→09-01 00:00Z = 8,256 个 5m 时刻 = **28.663 天**; 829 轴上 pod 独有有限格(生产未抓的非 live 名)使每通道缺失支持差 **15.47%–27.88%**。我方「收据 1 G2-A PASS」把这些差用「pod 覆盖 829/生产只抓 450」解释后写 PASS, 未按本文规则先立 AMENDMENT ⇒ 撤回该 PASS 标签。
- **新具名子门 G2-A′「当前 live450 精确通道平价」= PASS**(研究员从 pod2 原数组独立复算): 8,256 × 450 × 7, NaN 支持差 0, 有限值差 0, 生产独有有限格 0, 无 Inf 代 NaN。此结果**保留并准确命名**; 它不推出 829 名历史成员可用同一支持。
- **G2-A 原门保留为开**(生产滚动缓存只有 ~40 日尾, ≥40 天在当前装置上不可达 ⇒ 需换用历史面板宇宙时再判); **G2-C(换数据源但同预测/同状态/同资格 ⇒ 目标相同)仍是必须门, 本轮未跑**。
- G2-E 红能力改法(研究员建议, 采纳): 用明确越界的训练截止使 G2-D 必红, 不以「泄漏模型必须显著提高 g」作红能力。

## AMENDMENT 2(2026-09-13 08:5xZ, P2 worker「p2-oos-replay」受 lead 派 S0/S1; **写于任何 S1 门数字之前**; 本节只定计划/偏差/门程序/输出规格, 不含门读数)

### A2.0 本节改了原文哪几句(先列, 再给理由)
| 原文 | 改为 | 理由(证据在 A2.1–A2.4) |
|---|---|---|
| §1「king 预测 … 每个预测锚 E 只能用训练末锚 < E − 1 月的模型」+ §3 G2-D「任何锚违反 ⇒ 该锚不计入」 | 装置**按 §1 规则供给**: 规则不成立的模型预测一律不送入(置 NaN, king 腿为空), G2-D 改为审计「无任何被送入的预测违反规则」 | 逐年折 SLOW_v4 的 fold Y 训练到 Y−1 年末 ⇒ 每年 1 月 1 日 00Z–1 月 31 日 00Z(181 锚/年, 2024/25/26 共 543 锚)违反 30 天规则; 两句原文在这 543 锚上互相矛盾。「不送入」比「送入后不计入」严格(违规模型的输出不进入任何后续状态: H/LR/席位)。原「送入+不计入」保留为敏感性臂(A2.6) |
| §1「基名单 / 宇宙 = 面板有数据的名 ∩ live_pins」 | 主臂 = **时点宇宙 PIT**(umask_UPIT_CRYPTO); live_pins 臂降为敏感性臂 | lead S0(c): 今日 pins 投到历史 = 幸存者偏差; 且按生产代码的覆盖门(exp_n = 450)pins 臂在 2025-09-19 前**结构性不可跑**(A2.3) |
| §2「前 900 锚席位 [1/3]*3 经 combo 掩码 = [0.5,0,0.5]」 | 成立于 **combo 链状态**; 但执行器读的文件在 COMBO_LIVE 飞前断言失败时是 king 文件 ⇒ 分列 **P2-CMB**(combo 链) 与 **P2-LIT**(字面被交易文件) | A2.2 D10/D11: F10 覆盖地板 380 在 2022–2024 恒失败(成员 < 380), 2025–26 因折外覆盖缺口也多失败 |
| §1「资金费账本 / EMA = 面板 f_fund_now / 结算历史重建」 | **结算历史 = data-vision 月 zip ∪ API 拉取(fund_aug)按秒并集**; iv 推断与 EMA 由生产代码自己算 | 面板是 4h 采样, 不是逐结算行; 生产公式需要逐结算时间差 |
| §1「代码 … 零新替换; 装置 sha 与 Phase 1 相同」 | **不变且已满足**: 两个装置文件逐字节 = Phase 1(sha 断言), 全部替换发生在**输入**(A2.1) | — |

### A2.1 S0(b) 注入点(生产文件行号 = `shadow_loop_v3.py` e9c98374… / `fea171/combo_stage.py` b5c698f9…; 装置文件前后 sha 不变: `shadow_loop_v3_replay.py` 4d3bc157… → 4d3bc157…, `combo_stage_replay.py` f5ba9a82… → f5ba9a82…)
| # | 生产位置 | Phase 2 输入 | 一句理由 |
|---|---|---|---|
| I1 king 分 | L421–422 `X = FE_ANCH[:, keep]; pred = booster.predict(X)` | `booster` 参数换成 OOFBooster: predict 从调用帧读 `anchor`/`m`(成员), 返回 OOF 数组 (anchor, m) 行(float64; 无值或规则不允许 ⇒ NaN); X 只核形状 | booster 本就是 run_anchor 的入参; 折外 = 换输入不换代码。**因此本臂不含 H2b 特征错配**(OOF 由研究侧 v0 特征算出; L418 的 v1 EMA 列根本不进模型) |
| I2 F10 分 | L112–118 `need`(已有 `mini/data/f8_fea89.npz` 且 `dlw_targets.E_ts[-1] ≥ A` 则跳过 171 管线); L152–167 读 F82/F89/T9 + 模型 M 前向 | 每锚写 3 个 mini 文件(每个有 OOF 分的成员一行, 第 0 列 = 该分的平均秩/128, 其余 170 列 0)+ 恒等模型文件(mu 0, sd 1, w0=e0, b0=13, w1=1, b1=0, w2=1, b2=−13) | 该段对 f10 只取 `rankdata`(L174–175); 秩/128 是 1/256 的整数倍 ≤3.2, z≥13 时 gelu(z)=z 精确(erf 饱和 1.0), (x+13)−13=x ⇒ **zf 与 OOF 秩逐位相同**; 自检 `selftest_identity_model` 每条链启动时断言 |
| I3 5m 缓存 | L262–270 扩网格/截 40 日; combo L18–25 读 `rolling.npz` | king 段 `st.cts/st.cd` = holefix2 截至 A 的 11520 行, 不在 symbols_live(A) 的名置 NaN; combo 段 `rolling.npz` = 同样的末 2016 行 | 生产者只抓 symbols_live; 管线被跳过时 combo 只读 ai 与 2016 行 qv4h 窗 |
| I4 宇宙 | L189 `self.live`; L307 覆盖门 `exp_n = len(st.live)`; L406–412 fe_v; L500 `keep = st.live_mask`; L61–91 目标文件 universe | 每锚设 `st.live / st.live_mask / cfg["symbols_live"]` = symbols_live(A) | 配置常量随时点变化是本臂定义(A2.3) |
| I5 基名单 | L313–317 exchangeInfo(≥300 名才更新 `st.base`) | `fx.base` = (A−24h, A] 内有结算的名; 锚前把 `st.base` 预置为 sorted(该集 ∪ symbols_live(A)) | **偏差 D3**(A2.2) |
| I6 资金费行 | L321–353(API `fundingRate`, startTime = last_ts+1, limit 100; iv 由相邻结算时间差推断并吸附 {1,2,4,6,8}; EMA HL 3d) | `fx.ledger[s]` = 结算史中 (last_ts, A] 的前 100 行(与全账本 ReplayFetcher 等价) | iv / EMA 仍由生产代码 L341–349 自己算 |
| I7 链状态 | L193–226 启动(rolling/aux/bundle leg_returns) | 首锚冷启动: H=0, LR=[], prev_rec=None, ema={}, ledger={}; 之后内存逐锚携带 | 历史上不存在 bundle 腿收益; 冷启动的 40 日首抓窗与 limit 100 是生产行为 |
| I8 combo 其余输入 | L13 aux.json; L29 leg_returns_live.json; L24 weights/{A−4h}; L243 FTRIM rn8 = ledger_tail 末行; L258–262 state_H; L370–379 读者自校验 import `~/dl_quant_live/live/external_book` | aux.json(ledger_tail 只写末行 —— 该段只取 `rows[-1]`)/ LR[-950:] / 链自己的 weights 与 state_H; 读者模块 = dl_quant_live@918559f `live/external_book.py` f875fe54… + `book_config.py` a724406e… 的只读副本, 放在回放 HOME 下 | 均为文件输入 |

驱动层的其它两处(非装置代码, 均受据): ① `ShadowState.save` 以子类覆盖为空(同 Phase 1, 驱动自己写 combo 需要的文件); ② combo 段在**已导入 numpy/scipy 的 fork 子进程**里 `runpy` 执行同一脚本(环境变量整体替换为 combo 环境): 与 `subprocess` 模式 **12/12 锚 king/kc/fc 向量逐位相同**(`RUN_timing12…_fork.vec.npz` 与 `RUN_timing12….vec.npz` 同 sha 75b800f7…), 每锚 4.7 s → 1.03 s。已知生产崩溃路径(chain() 在 z 全 0 时返回 None ⇒ L268 `np.abs(_sm)` TypeError, 如冷启动首锚 king 腿空且资金费未新鲜)按生产语义记录(该锚无 combo 文件, 下锚 kc/fc 暖启动), 其它任何非 0/3 返回码致命停链。

### A2.2 偏差清单(与在役生产路径的全部已知差异; 每条带数)
- **D1 king 模型** = SLOW_v4(v4 特征/配方逐年折: 2024 折 fit 年<2024、2025 折 <2025、2026 折 = v4 slow2026)≠ 在役 v3 booster(8d79186b…, v2ext 特征)。2022–2023 **无 king 预测**(全 NaN)。2026 折比「月度重训」更旧(保守, 原 §1 已写)。不含 H2b(I1)。模型匹配臂 A0pred 用 SLOW_v3_on_v4axis(= 在役 v3 bundle pinned 按 E_ts 对齐, 逐位核过)。
- **D2 F10 模型** = f10_v4RAW_s{42,2027}: 2025-01..2026-08 月折 mE1cX7 FIX7(20 折, 每折 max_train_label_end = 上月末 20:00Z)+ 2023–2024 在役逐年 V2MAIN(embargo 60, 验证片 argmax)拼接, 拼接边界 2025-01-01 00Z(逐位核过: 前段 = 逐年对齐, 后段 = 月折拼接)。≠ 在役全史重训 f10_live_s42_np(351ae26b…, 「全史重训件不参与历史评估」)。**2022 无 F10 预测**。
- **D3 基名单**: exchangeInfo 历史不可得 ⇒ (A−24h, A] 有结算的名作 TRADING 代理; 该代理 ≥300 的锚占比 2022 0% / 2023 0% / 2024 31.9% / 2025 100% / 2026 100% ⇒ 字面生产代码会把基名单冻结在链起点值, 故锚前预置 `st.base`(= 守门通过时生产代码会写的值)。
- **D4 宇宙**: PIT = umask_UPIT_CRYPTO(每月首锚: 上市 ≥30 日且 30 日成交额 >0 的名按 30 日成交额取前 449, 并 COIN 底层), 年均名数 2022 141 / 2023 179 / 2024 266 / 2025 404 / 2026 426; 缓存按**当锚** symbols_live 对全部行打 NaN(= 一直在抓这些名的生产者)。pins 臂 = 今日 450 名(幸存者偏差)。
- **D5 资金费行** = 2,633,090 行(2020-01 → 2026-09-01 02:00Z): 双源同秒 2,365,163 行且**利率冲突 0**; 仅 API 109,070; 仅 zip 158,857; 生产者自己的 API 行历史上不存在。29 对相隔 1 s 的双行(26 名, 2026-06-30..09-01, 多数为新上市股票永续, 全部**从未进入** PIT_CRYPTO 宇宙)是场所侧真实双行(18 对只在 API、11 对 API 与 zip 同有), 按生产语义保留。
- **D6 冷启动**: LR 空 ⇒ 前 900 锚 w3 = [1/3]*3(king 文件含 rev24 腿; combo 掩码后 [0.5,0,0.5]); 资金费首抓 40 日窗、每锚至多 100 行(1h 名约 10 锚追平)。
- **D7 combo 输入瘦身**: rolling.npz 只写末 2016 行; aux ledger_tail 只写末行; fork 执行(A2.1)。
- **D8 读者自校验**用 918559f 读者模块副本(A2.1 I8)。
- **D9 已知生产崩溃**按生产语义记录不停链(A2.1)。
- **D10 折外覆盖缺口(实测, 周采样 239 锚/宇宙, `S0_coverage_probe.json`)**: 生产成员中有 OOF 分的比例 —— PIT 2023 F10 100% / 2024 king·F10 100% / **2025 95.7%** / **2026 86.8%**; 有 OOF 分的生产成员 100% 属于研究 meta 成员集(缺口 = 研究侧 top-400 取自全 829 名含股票永续, 生产-PIT 取自 PIT 名)。缺分成员在模型腿为中性(NaN 不入秩)。生产上 DL 管线给**全部**成员打分, 故这是 OOF 注入的保真度缺口, 不是生产行为。
- **D11 COMBO_LIVE 飞前断言**: F10 打分 ≥380 / combo gross ∈[0.4,1.2] / 名数 ≥150 / 读者 n_in_universe ≥150 且 gross_in >0.4。历史上 F10 ≥380 的锚占比(PIT)2022–2024 **0%**、2025 17.3%、2026 5.9% ⇒ 字面路径几乎全程 fail-open 交易 king 文件; 其中 2025–26 主要由 D10 造成 ⇒ **P2-LIT 受 D10 混杂**, 只报不作主判。
- **D12 pins 臂可行域**: 覆盖门 exp_n = 450 ⇒ 结算代理下 ≥80% pins 在交易首次出现于 **2025-09-19 12Z**, 仅占 W_FULL 20.65% 锚; 周采样 pins 臂在 2025-09-15 前全部 SKIP。
- **D13 跨机**: pod2 python 3.11.10 / numpy 2.4.6 / scipy 1.17.1 / lightgbm 4.7.0 x86(AMD EPYC 9354)vs 生产 Mac 3.14.4 / 2.5.2 / 1.18.0 / 4.7.0 ARM。
- **D14 1 月 king**: 主臂不送入(A2.0); 敏感性臂 serve_all 送入并在统计上排除这 543 锚 + 标红。
- **D15 执行层**: 仍为 §1「100% 成交于 E 收盘」; 执行器 gross_in 归一/withheld/场所过滤/停机不模拟(S2 记账合同另立, A2.6)。
- **D16 G2-A**: 829×40 日原门仍开; Phase 2 历史 PIT 名的通道值无生产者对照(只有 live450 子门 G2-A′ PASS)。

### A2.3 S0(a)/(c) 盘点(全部 sha 在 `phase2/receipts/S0a_inventory.json` 9d10c22f… 与 `P2_prep_inputs.json` b0d17891…)
| 件 | 路径(pod2) | sha256 前 16 | 事实 |
|---|---|---|---|
| 5m 缓存 | `/workspace/data/dlnative_5m_wide829_f16_holefix2.npz` | 1d7f459dee434ec4 | 490,753 行 × 829 × 7 f16, **2022-01-01 00:00Z → 2026-09-01 00:00Z**, 符号 sha 381b7f01…(= 生产 symbols_panel) |
| 结算史 | `P2/work/ledger_full.npz`(由 `wide_multisrc/funding/*/*.zip` 19,609 个 + `fund_aug.json.gz` 8a9e7715… 构建) | bea6f5752772d54e | D5 |
| 宇宙 | `P2/work/universe.npz`(umask_UPIT_CRYPTO 47d87b51… + 结算代理 + live_pins fd27fe48…) | 6322b57366078ed0 | 轴 = A0 rec 轴 10,039 锚 2022-01-31 → 2026-08-31 00Z |
| king OOF | `/workspace/review_scratch/king_v4/SLOW_v4.npy` | dde19142d017c37d | 2024-01-01 → 2026-08-31 20Z 有值; = shadow_bundle_v4 pinned(该文件 09-12 被测试重写但**内容逐位相同**, MANIFEST 相符); 同目录 SLOW_v3_on_v4axis 64767318…、SLOW_v4e 83dce630… |
| 逐折 booster | 仅 `shadow_bundle_v3/v4/v4e/slow2026.txt` | — | **2024/2025 折 booster 从未落盘**(导出器 L63–65 训练后只取预测)。可行性: 同导出器训练段加一行 `save_model` 即可重出(研究脚本, 非生产); 耗时估计 ≤15 min/折(09-01 首次重训 king 全流程 15 min 的记录, 未在 pod2 CPU 实测); LightGBM 多线程重训能否逐位复现 SLOW_v4 未验证 ⇒ 未做, 仅可行性 |
| F10 OOF | `…/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s42.npy` / `_s2027` | 58d64a6ff9684589 / 47046ccd6dc7937c | D2; 月折收据 `/workspace/f8_v4/mwf_v4b/RAW_s{42,2027}/results/merge.json`(训练器 2147a7dd…, 20 折 causality_ok); A0 臂 F10 = `f10_A0_s{42,2027}` ff109711… / 98bfe779… |
| A0 | `/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s{42,2027}.npz` | 352ac36fb3195327 / aa44e18fb6bcfa7e | rec 10039×23(2022-01-31 → 2026-08-31 00Z)+ W 10039×829; 装置 w10_sleeve.py b88e35a4…, NW = r18 `arms/NW_s{42,2027}.npz` afbcd92e… / 89d28a31… |
| 记账元 | `/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz` | 0e3c09ac86c727ac | y4 RAW(Π(1+r)−1), 10,182 锚 |
| 在役 bundle | `/workspace/shadow_bundle_v3/` | config 3a8422f3… | 与 Mac 在役 bundle 逐文件 sha 相同 |

**宇宙裁定**: PIT 为主臂(数据支持: 829 轴含已退市名如 LUNAUSDT/SRMUSDT/BTCSTUSDT; umask 按月时点、严格因果)。pins 臂只作敏感性且只在可行域报(D12)。

### A2.4 S0(d) 运行时与分块计划
- **实测**(pod2 CPU, nice 10, OMP=1; `RUN_timing12_2025-03_pit_v4_s42_fork.json` 55c2c0a4…): 12 连续锚 2025-03-01 00Z 起, 稳态每锚 **1.03 s**(缓存 0.105 / king 段 0.44 / combo 输入 0.17 / combo 段 0.28), 首锚 +2.4 s 导入; 全局输入载入 18–21 s; 进程内存 ≈ 缓存 5.7 GB + 约 1 GB(估计, 未测)。另 3 条功能冒烟链(2022-02 无模型 / 2024-01 king 1 月扣留边界 / 2026-03 满规模)均 rc=0。
- **串行全史**: W_FULL 10,038 锚 × 1.05 s ≈ **2.9 h / 条链**。容器内存上限 **61 GB**(cgroup memory.max, 非 `free` 的 247 GB); /workspace 有配额(本轮 08:02Z 一次 5.7 GB 写入触顶, 已删并报 lead)⇒ **不落盘缓存副本**, 一个父进程载入缓存后 fork 各链共享页。
- **计划 P-A(推荐, 无接缝)**: 每臂一条串行链, 臂间并行(≤8 链 ≤8 核), 墙钟 ≈ 3 h, 算力 = 2.9 h × 臂数。
- **计划 P-B(分块, 需过接缝门)**: 每臂 K 块, 每块 = 暖机 W 锚 + 记录 L 锚; K=4 时每块约 4,340 锚 ≈ 76 min, 6 臂 24 块并行(≤32 核)墙钟 ≈ 76 min, 算力约为 P-A 的 1.7 倍。
- **暖机长度 W 的数值理由**(先验, 由接缝门实测验证): ① 资金费 EMA 半衰期 3 日 = 18 锚, 初值差 ≤ |rn| ≈ 0.03 衰到 1e-13 需 3·log2(0.03/1e-13) = 114 日 ≈ **686 锚**; ② 席位窗 900 锚的 LR 条目依赖 fund 腿秩(依赖 EMA) ⇒ ① 之后再 **900 锚**; ③ 平滑 H(king/f10/kc/fc)α=0.1: 差 ≤ cap ≈ 0.01 收缩到 1e-12 需 log(1e-10)/log(0.9) ≈ **219 锚**(中性带 2.5e-4 可使在带内的名更久不收敛 —— 这是接缝门要实测的风险)。合计 **W = 1,830 锚(305 日)**。
- **接缝门 G2-S(冻结)**: 链 X 自 2024-02-01 00Z 起, 链 Y 自 X 起点 + 300 锚起; 二者均 PIT / SLOW_v4 / v4RAW_s42 / withhold; 均跑到 Y 起点 + W + 300 锚。对 A ∈ [Y 起点 + W, 终点] 每锚: king H(float64 全向量)、kc、fc 状态向量 **L∞ ≤ 1e-9**, 且 w3、traded_file、combo 状态码逐锚相同 ⇒ PASS。另报 A ≥ Y 起点的逐锚 L∞ 曲线与「此后恒 ≤1e-9」的首锚(W 的实测值)。红 ⇒ S2 只用 P-A。

### A2.5 S1 门程序(冻结; 顺序执行, 红即停; 阈值不改)
- **G2-B 资金费状态平价**: 参照 = 对 41 个 Phase 1 锚 A ∈ {1788624000 + 14400k, k=0..40}, 用 `devices/replay_driver.py`(f2ced820…)中 `ema_state_before` 的**原文**(AST 抽取执行)从快照 `producer_state_snapshots/1789200000/aux.json`(5e825c2f… = Phase 1 chain_full 收据 aux_sha256)逆推。重建 = 生产公式(L341–349: iv = 与上一行时间差(h)吸附 {1,2,4,6,8}, 首行或差 ∉ (0,24] 取 8.0; rn = rate·8/iv; 首行 acc = rn, 否则 acc += a(rn − acc), a = 1 − 0.5^(max(ft − last_ts,1)/259200))从每名**最早一行**冷启动, 行集 = `ledger_full.npz` ∪ 快照 ledger_tail(按秒并集; 同秒利率冲突取快照行并计数), 取 ft ≤ A − 14400。**端口自检**(读门前必须过, 否则重建装置无效): (i) 快照 ledger_tail 中 ft > 1788624000 − 14400 的每一行(均为生产者 09-05 之后追加), 按与前一行的时间差重算的 iv == 生产者存的 iv; (ii) 从 ref(1788624000) 出发沿快照行递推到 1789200000 与快照 ema 逐名 |Δacc| ≤ 1e-15 且 last_ts 相同。**门**: 全部 (A, s) 中参照为有效状态者(非 None、非 MISMATCH)|acc_rb − acc_ref| ≤ 1e-9, 且参照有而重建无的名计为违例; 违例数 = 0 ⇒ PASS。归因(只报不改判): 违例名的 live 账本首行日期、重建与 live 的 iv 序列是否不同、差值是否随 HL 3d 衰减。
- **G2-C 换缓存不换预测 = Phase 1**: pod 正典缓存止于 09-01 00:00Z, 41 锚与 3 个快照锚都在其后 ⇒ 缓存 = **拼接**: holefix2 行(≤ 09-01 00:00Z, 非 live450 名置 NaN)+ 快照 1789243200 `rolling.npz` 的行(> 09-01 00:00Z)。king 段: 41 锚链(起点状态按 Phase 1 `build_state` 同法: 快照 aux 逆推 EMA、账本截到 ≤A0−4h、H = 生产者 weights/{A0−4h}.npz、LR = bundle + 快照 leg_returns_live 按 Phase 1 规则截断、base = aux base_syms), 真 booster(shadow_bundle_v3/slow2026.txt), 宇宙 = 在役 450; 门 = 每锚 weights 与生产者 weights/{A}.npz **L∞ ≤ 1e-6, 41/41**。combo 段: 快照起步锚 1789214400/1789228800/1789243200(状态 = 该快照前一锚的 aux/leg_returns + 生产者 fea171 state_H_{f10,kc,fc}_{A−4h} 与 weights/{A−4h} 的只读副本), 真 171 管线 + 在役 F10 模型; 门 = target_live_combo 与生产者 target_live/{A}.json **L∞ ≤ 1e-6, 3/3**。41 锚历史链 combo 残差**单列报告, 不改标签**(Phase 1 为 0/41 ≤1e-6)。
- **G2-C′ 注入管道平价(新增, 只加严〔勘误见 AMENDMENT 7 · A7.3: 指新增一门、不替换任何原门〕)**: 在 3 个快照锚上, (i) king: OOFBooster 的查表由真 booster 在同锚同成员上的输出填充 ⇒ 权重与真 booster 模式**逐位相同**; (ii) F10: 由真管线同锚产出的 f10 分(对该锚 mini 文件执行生产 L152–167 对应的装置原文)填 I2 注入文件 ⇒ state_H_{f10,kc,fc}_{A} 与真管线模式**逐位相同**。
- **G2-S 接缝门**: A2.4。
- **G2-D 因果审计**: king 规则 label_end < E − 30·86400(label_end = fold Y 训练集最后一个 ≥50 标签锚 + 4h, 由 wide_fea_v4_meta 实算); F10 规则 label_end < E 所在月首 00:00Z(月折取折配置 max_train_label_end; 逐年折取 dlw_ext 轴 E[first_te − 61] + 4h, 未扣 ≥50 行过滤 ⇒ 偏保守)。审计两层: (a) 全 W_FULL 轴按折表与 OOF 数组可得性逐锚列出「会送入的模型 / label_end / 是否合规」, 断言 withhold 策略下**无违规被送入**, 并列出被扣留锚(预期 king 543 锚 = 2024/25/26 各 1-01 00Z..1-31 00Z, F10 0 锚); (b) S1 期间每条链的逐锚记录(served 标志与规则一致)。任一违规被送入或记录不一致 ⇒ RED。
- **G2-E 红能力**(AMENDMENT 1 口径): 伪造折表 —— F10 fold 202503 的 label_end := 2025-03-15 00:00Z、king fold 2025 := 2025-02-15 00:00Z —— 以 serve_all 在 2025-03-16 00Z..20Z 6 锚上跑装置; G2-D 审计**必须**对 king 与 F10 各报 ≥1 违规(RED)⇒ 红能力 PASS。

### A2.6 S2 输出规格(本轮不跑; 记账合同在 S2 前另立 AMENDMENT 3, 冻结后才算数)
- **臂**(S2 由 lead 定跑哪些; 两种子才下判词): P2a-v4-s42/s2027(PIT, withhold, **主**)· P2a-A0pred-s42/s2027(PIT, withhold; 与 A0 模型匹配, 用于隔离「生产路径 vs 研究回放」)· P2a-v4-s42-serve_all(1 月敏感性)· P2a-v4-s42-pins(只在 D12 可行域)。研究侧匹配参照「A1-NW」= w10_sleeve_r18.py NW 旋钮 + SLOW_v4 + f10_v4RAW(未存档, S2 需先跑并过其 GATE P 类门)。
- **书**(同一条链三读): **P2-CMB** = 0.55·kc + 0.45·fc(combo 段 float64 状态; 主读数)· P2-KING = king 文件 · P2-LIT = 执行器字面会读的文件(combo 写者成功 ⇒ combo, 否则 king, 生产者跳锚 ⇒ 持有不动), 逐年报三种形态占比。层级标注: 均为**持仓书层**(目标权重), 非模型分数层/复合目标层。
- **表**: 逐年表(2022..2026, 负年显式)· W_ALPHA(A0 轴 rows ≥900 ∧ ts ≤ 2026-08-30 20Z, n = 9,138)/ W_FULL(n = 10,038)/ 冻结窗(2025-03-01 → 2026-08-10 20Z)三窗并报 · 对 A0(C0 存档)、NW、A1-NW 的配对 Δg 与 ΔSharpe(同锚; UTC 日块自举 2000 次, `default_rng([20260905, k])`, k=0 主 / k=9 复核)· 固定 2.0× 复利 NAV maxDD · G2-D 被扣留锚与 D10 覆盖缺口的逐年计数。判词只用 (A)/(B)/(C), 0.23 bps/锚/gross 以下不可区分(原 §3)。

### A2.7 本节不主张
不主张任何历史水平或 Sharpe(本轮零书层数字); 不主张 P2a 等于在役月度重训(D1/D2); 不主张 PIT 宇宙等于在役 pins; 不主张 D10 缺口对书层无影响(未测); 不注销 G2-A 原门(D16)与 Phase 1 历史 G-P2 FAIL。

## 收据 2 · G2-B 资金费状态平价 = **RED ⇒ S1 按 AMENDMENT 2 §A2.5「红即停」停止**(2026-09-13 09:0xZ, pod2 CPU, 只读; 装置 `phase2/devices/p2_g2b_funding.py` 7766c7b3…, 收据 `phase2/receipts/G2B_funding_parity.json` d654b160… / `.log` 8b000551…; 程序与阈值 = A2.5 原文, 提交 4f92fe97 先于本次运行)
- **端口自检 PASS**(读门前提): 生产者 09-05 12Z 之后追加的 19,513 行上按时间差重算 iv 与存储 iv **0 不符**; 自 ref(1788624000) 沿快照行前推到 1789200000, 525 名 |Δacc| 最大 **4.77e-18**, last_ts 全同 ⇒ 重建所用递推 = 生产公式。
- **门读数**: 41 锚 × 有效参照 = 21,520 对(参照 None 5, MISMATCH 0; 同秒利率冲突 0); **最大 |Δacc| = 2.603e-05**(PROMUSDT, 09-05 16Z); **违例 2,163 对 / 73 名**(> 1e-9); 逐锚最大值 2.6e-05 → 5.6e-06, 违例名 73 → 26 ⇒ **RED**。
- **归因(只报不改判)**: ① 41 锚全程违例的 26 名, 末/首差值比 0.21431099567–0.21431099573, 与 HL 3d 在该窗的理论衰减 0.21431099571 相同 ⇒ 差异全部来自 09-05 16Z **之前**的状态, 窗内无新增发散(VERIFIED)。② 在役 450 名中 7 名(PROMUSDT 2.60e-05 / ACEUSDT 4.80e-06 / DEXEUSDT 3.30e-06 / ERAUSDT 1.91e-06 / BANKUSDT 1.09e-06 / ESPORTSUSDT 5.9e-09 / 1000XECUSDT 1.4e-09): 其 live 账本在 09-05 之前有「存储 iv ≠ 相邻时间差 iv」的行(如 PROMUSDT 79 行, 首行 2026-08-11 05:00Z 存 4.0、时间差为 1.0), 这些存储值的来源(bundle 种子 / 更早生产者版本)**未查实**(INFERRED)。③ 其余 66 名(均不在在役 450, 属基名单扩展): live 账本首行全部为 **2026-07-26 08:00Z**, 无 iv 不符, 差 1.0e-09–1.15e-07 —— 与「live EMA 从首抓窗第一行冷启动、重建从全历史起算」一致(INFERRED; 该日期 = 2026-09-04 08:00Z 前推 40 日)。
- **含义(不是判决)**: Phase 2 用生产公式从全历史冷启动得到的资金费 EMA, 在重叠窗上与 live 状态差 ≤2.6e-05(随 HL 3d 衰减), 不满足 1e-9 冻结门。G2-C / G2-C′ / G2-S / G2-D / G2-E **均未运行**。是否以及如何修订 G2-B(例如只对账窗内递推、或模拟 live 起点历史)须由 lead 以 AMENDMENT 3 在任何新数字之前决定; 本工作者不改门。

## AMENDMENT 3(2026-09-13 09:0xZ, lead; **写于看到收据 2 的 G2-B RED 之后**, 先于 G2-C / G2-C′ / G2-S / G2-D / G2-E 任何数字)
- **G2-B 原门 = NOT PASSED AS WRITTEN(RED), 标签保留, 不改阈值、不注销。** 与 AMENDMENT 1 处理 G2-A 同法: 不把红改写成绿, 只把原门实际测到的东西拆开命名。
- **收据 2 已证明的两件事**: (i) 重建递推 = 生产公式(端口自检: 09-05 12Z 后追加的 19,513 行 iv 0 不符; 窗内前推到 1789200000 与快照 525 名 |Δacc| ≤ 4.77e-18); (ii) 违例**全部继承自 09-05 16Z 之前的状态**, 窗内无新增发散(26 名末/首差比 = HL 3d 理论衰减到第 10 位)。原门把「公式对不对」与「live 状态有没有继承历史伪迹」绑在一个阈值上, 后者不是 Phase 2 能也应该复现的东西: 历史回放的资金费 EMA 由干净的全史冷启动得到。
- **新具名子门 G2-B″「窗内递推平价」(只加严〔勘误见 AMENDMENT 7 · A7.3: 仅相对原端口自检 (ii)「只核终点」更严; 相对原 G2-B「冷启动历史状态 = live」门是不同命题, 属结果已见后透明标注的研究范围收窄, 不是全局只加严〕)**: 以 Phase 1 参照在首个重叠锚 1788624000 的状态为起点, 沿快照行前推, 在**全部 41 个锚**上与参照逐名 |Δacc| ≤ **1e-15** 且 last_ts 相同(端口自检 (ii) 只核了终点, 本子门核全部 41 锚); 红即停。
- **新偏差 D17「live 资金费 EMA 的历史伪迹」**(与 D1–D16 同列): 在役 450 中 7 名的 live 账本在 09-05 之前有「存储 iv ≠ 相邻时间差 iv」的行(PROMUSDT 79 行, 首行 2026-08-11 05:00Z 存 4.0、时间差 1.0), 来源未查实; 另 66 名基名单扩展名的 live 账本从首抓窗 2026-07-26 08:00Z 冷启动。继承残差在 09-05 16Z 最大 2.603e-05、随 HL 3d 衰减。**Phase 2 不复现该伪迹**; 因此 G2-C 的 king 段继续按 Phase 1 `build_state` 用快照 aux 逆推的 live 状态(不受 D17 影响), 而 S2 历史臂用干净重建。
- **必须附带的影响测量(描述, 不作门)**: 在 41 个重叠锚上, 用重建 EMA 与 live EMA 分别算 fund z(生产 FTRIM 前的同一 z 路径), 报逐锚 Spearman、fund 腿前/后十分位成员变动名数、以及 7 名 D17 名的 z 差; 写入 S1 收据。
- **非阻断取证(交 P2 在 S1 门之后顺带做, 只读)**: 7 名存储 iv 不符行的来源 —— bundle `funding_ledger_seed.json` 的 iv 字段 / 早期生产者版本的追加逻辑 / 其他; 影响的日期范围与行数; 在役生产者当前取数层能否再产生此类行。若结论是「在役链路仍会产生」, 立即报 lead(可能是生产缺陷)。
- G2-C / G2-C′ / G2-S / G2-D / G2-E 的程序与阈值**一字不改**(A2.5 原文), 顺序 = G2-B″ → G2-C → G2-C′ → G2-S → G2-D → G2-E, 红即停。本修订随第四轮合并审阅包交独立研究员复核。

## AMENDMENT 4(2026-09-13 09:2xZ, P2 worker; 补 AMENDMENT 2 的偏差清单与资源约束, 受 lead 09-13 两条指示 —— 指示要求写入 AMENDMENT 2, 但 AMENDMENT 2 已随 4f92fe97 提交且其后已有收据 2 的数字, 故按时间顺序另立本修订; **写于收据 2 与 AMENDMENT 3 之后、G2-B″ 及其后任何 S1 数字与任何 S2 数字之前** —— 以下三项只影响 S2 书层/尾部读数与资源纪律, 不改 A2.5 / AMENDMENT 3 的任何门程序与阈值: 资金费 EMA 状态在 FTRIM / 带 / 执行器止损的上游)
- 编号说明: A2.6 所写「记账合同在 S2 前另立 AMENDMENT 3」的编号已被 lead 的 AMENDMENT 3(G2-B″)占用, S2 记账合同改为其后的新编号修订, 内容要求不变; AMENDMENT 3 已用 D17(live 资金费 EMA 历史伪迹), 本修订的偏差顺延为 D18 / D19。

### A4.1 偏差 D18 · 执行器逐名止损(生产在 target_live **之后**生效, 本装置重放的生产者与 combo 代码看不到它)
- **源(只读)**: `~/dl_quant_live@918559f` `live/per_name_stop.py` 8fb79dd8… + `config/book.json` f6fd6d0e… 的 `per_name_stop` 块; 在役 `active_profile = "wide"` ⇒ depth_pct **−0.30** / consecutive_anchors **2** / cooloff_days **7** / min_notional_usdt **5**(基础值 −0.25/2/7/20 被覆盖)。调用点: `scheduler/anchor_loop.py` L2553 终锚读回后 `PNS.update_from_snapshot`, L1602–1604 下一锚计划时 `active_sets`。
- **语义(读码)**: 深度 = unrealizedProfit / |notional|(`/fapi/v3/account` 逐仓读回, 分母是**当前**名义 ⇒ 多头约相当于价格跌 23.1%、空头约相当于涨 42.9% 触发); 连续 2 个终锚读回均 ≤ −0.30 ⇒ 该名 stopped ⇒ 下一锚并入 untradable、target 置 0、走 flatten_only(maker-only 出场, reduce-only, 不追); |notional| < 5 USDT(已出场)起 7 天冷却禁入; 缺读回 / 回浅 / dust ⇒ 计数归零。被停名之外的书经执行器 withhold → reshape(re-demean/rescale, `apply_withhold_and_reshape` L334 起)。本地 live 状态文件 `state/live/per_name_stop.json`(读时 10 名冷却, 0 名 stopped)。
- **P2 如何建模**: 止损不回馈生产者/combo 状态 ⇒ 在 P2 目标序列上做**事后覆盖层**, 结构上与生产相同(无反馈), 不必重跑链。**S2 两臂: STOP(主; 一切尾部 / 回撤 / 停机读数只从此臂出)与 NOSTOP(对照)**, 二者配对报差。覆盖层定义在 S2 记账合同修订(见上方编号说明)冻结后才算数, 骨架先定: 按 §1「100% 成交于 E 收盘」模拟逐名持仓; 入场价按交易所均价规则(同向加仓取加权均价、减仓不变、归零或翻向重置); 标记价只用记账口径 meta y4 RAW 逐锚复利(**不从 5m 缓存 ret5 重算**); 每锚成交后读回深度; 连续 2 锚 ≤ −0.30 ⇒ 下一锚 E 收盘全额出场; 自出场锚起 42 锚冷却; min_notional 5 USDT 按该臂固定 2.0× 复利 NAV 路径换算; 停名 / 冷却名按执行器 withhold → reshape 从执行书剔除。
- **做不到的(明写, 触发时点可与实盘不同)**: 实盘入场价 = 真实 maker 成交均价(部分成交、N+23 起的执行钟), 标记价 ≠ 锚收盘, unrealizedProfit 不含资金费, 读回时点晚于 E, maker 出场可跨数锚, NAV 水平不同。T5 §6.1 的 ONGUSDT 即一例: 回放止损层 08-25 20Z 已封锁, 生产者侧止损证据采集器 08-26 20Z 才记下 −46.1% 触发(且不改书)。⇒ **P2 不主张尾部行为的生产路径保真**, 只主张「生产目标 + 该覆盖层近似」。
- 与 A0 的目标层止损 d30_n2_c42 的关系: T5 §3 构造桥中「P 止损层」占八月 carry 差 **18.5% [4.3, 32.0]**(s42, Shapley +0.220), 且与 FTRIM 有交互 ⇒ S2 对 A0 的配对差须把止损层作为单列分量报告(STOP 臂对 A0、NOSTOP 臂对 A0 的无止损版本), 不得混入「生产路径 vs 研究回放」的主差。

### A4.2 偏差 D19 · FTRIM 顺序与中性带冻结(明写复现条件)
- **代码事实(生产 `fea171/combo_stage.py` b5c698f9…)**: FTRIM 在 L239–248 把 (z<0 ∧ rn8 ≤ −0.0010) 的名的 **z 置 0**, 发生在 `chain()`(L78–102, 调用 L264–265)**之前**; 该名仍在 sel 内, 去均值(L81)后目标 = −mean 级的小值, **不是强制出场**。强制归零只经 keep 掩码(宇宙 ∧ 成员 ∧ 流动性, L93–101)。EMA α=0.1(L90), 中性带 L92 `smv = np.where(np.abs(trade) < P["band"], H, smv)`, band = 2.5e-4 ⇒ |H − tgt| < 2.5e-3 的残余仓位不再移动。rn8 = ledger_tail 末行 rate × 8 / 存储 iv(L241–243)。
- **复现条件**: P2 的 combo 段是上述文件的逐字节副本(sha f5ba9a82…, 三处 Phase 1 替换均不触及 L78–102 / L230–271), FTRIM 阈值、z 置零位置、去均值 / L1 / cap / EMA / 带的顺序与 keep 掩码全部是生产原文; kc/fc 状态由链自己逐锚携带 ⇒ **只要输入同源, 该冻结机制在 P2 中自动、逐位按生产顺序发生, 装置不做任何额外处理**。输入层唯一已知差: P2 账本的 iv 恒为时间差推断, 而收据 2 显示 live 账本有 7 名存在「存储 iv ≠ 时间差 iv」的行(如 PROMUSDT 存 4.0、差为 1.0; = AMENDMENT 3 的 D17)⇒ 这类名在那些时点的 rn8 分类(≤ −10 bp 与否)可能与 live 不同, 影响未测。
- **不主张**: 冻结机制的经济量级(T5 为推断; T5b 提交 51b93969 的标题称已按数据确认, P2 未打开其结果, 不引用其数字)。

### A4.3 资源约束(08:02Z 配额事故与 cgroup 上限的受据规则; 对 S1 余门与 S2 全部生效)
- **R1 不做多 GB 写入**: /workspace 有配额; 5m 缓存永不落盘副本, 父进程内存载入后 fork 各链共享页。
- **R2 内存**: 容器 cgroup `memory.max` = 61,000,097,792 字节(61 GB), 不是 `free` 显示的 247 GB; 每个独立载入缓存的进程约 7 GB(估计) ⇒ 同一时刻独立载入缓存的进程 ≤ 4 个; 更多链一律由共享缓存的父进程 fork, 单父进程 ≤ 8 条链。
- **R3 写前探针**: 任何单次计划写入 > 500 MB 之前, 先在 `P2/work/.ddprobe` 用 dd 写入「计划大小 × 1.1」并 fsync, 成功后立即删除再做正式写入; dd 任何报错 ⇒ 放弃该写入并上报。

## 收据 3 · G2-B″ 窗内递推平价 = **PASS** + D17 影响测量(2026-09-13 09:1xZ, pod2 CPU, 只读; 装置 `phase2/devices/p2_g2bpp_inwindow.py` e4acdb9d…(提交 3eadbdc5 先于运行), 收据 `phase2/receipts/G2Bpp_inwindow_recursion.json` 6bb771f3… / `.log` 3d9c4614…; 程序 = AMENDMENT 3 原文)
- **门**: 自 ref(1788624000) 沿快照行前推, 41 锚 × 有效参照 21,520 对, 最大 |Δacc| **8.67e-18**(阈 1e-15), last_ts 全同, 违例 **0** ⇒ **PASS**。
- **D17 影响测量(描述, 不作门)**: 41 锚上 live EMA 与全史冷启动重建 EMA 分别经装置 `xz_in_base` 算 fund z(成员 = 生产者 weights 的 members, 基 = 快照 base_syms, 新鲜度 ≤12h): 逐锚 Spearman **最小 0.9999567 / 中位 0.9999874**; 每锚 z 有变动的成员 9–11 名, 最大 |Δz| 0.023(秩单位, 全宽 1); fund 腿**前十分位成员 41 锚全不变**, 后十分位仅 1 锚换 2 名; D17 七名最大 |Δz|: PROMUSDT 0.0498 / DEXEUSDT 0.0058 / ERAUSDT 0.0038 / BANKUSDT 0.0038 / 其余 0。
- 下一门: G2-C(A2.5 原文)。

## AMENDMENT 5(2026-09-13 09:3xZ, P2 worker; **写于 G2-C 预备收据之后、任何 G2-C 门数字之前**; 不改 G2-C 程序、阈值与标签, 只加一个归因子门)
- **预备事实**(`phase2/devices/p2_g2c_prep.py` 3a7133ab…(提交 683612fa 先于运行), 收据 `phase2/receipts/G2C_prep.json`): 按 A2.5 构造的四个拼接缓存(chain 止于 1789200000; s12/s16/s20 止于各锚)与同锚生产者 `rolling.npz` 比 —— ts 全同; 双方有限格**值差 0**; 但「生产者有限而拼接为 NaN」分别 **5,560,280 / 5,462,956 / 5,364,195 / 5,265,875 格**, 反向 0 格。以 chain 为例, 这些格全部落在 **348 个不在在役 450 的名**、**2026-08-03 08:05Z – 08-13 00:00Z 的 2,784 行**上(推断: 生产者滚动缓存早段来自 bundle 引导尾, 含全部 829 名; 之后的自抓行只有 symbols_live)。G2-A′「live450 精确平价」不覆盖这些格; A2.5 的「非 live450 名置 NaN」因此不是逐格等价的换源。
- **读码推断(不作结论)**: king 段成员要求近 7 日覆盖 ≥0.95 且特征只取成员 ⇒ 这些早段格不进入 king 段; combo 段 171 管线在整条 40 日尾上算横截面特征, 可能受其影响。
- **G2-C 按 A2.5 原文运行, 标签照实报。** 另立具名子门 **G2-C-S「支持匹配拼接」(只作归因; 不改 G2-C 的标签; G2-C 若红, S1 仍按红即停)**: 缓存 = 同锚生产者缓存为有限的格取 pod holefix2 值(ts ≤ 09-01 00:00Z)、生产者为 NaN 的格保持 NaN、ts > 09-01 00:00Z 取快照 1789243200 行; 其余程序与阈值同 G2-C(king 41/41 ≤1e-6, 快照起步 combo 3/3 ≤1e-6, 历史链 combo 残差单列); 另报该缓存与生产者缓存是否逐格逐位相等及「生产者有限而 pod 为 NaN」的格数。

## 收据 4 · G2-C 换缓存不换预测 = **PASS**(2026-09-13 09:5xZ, pod2 CPU 8 核 taskset, 只读; 逐字节 Phase 1 驱动 f2ced820… + 装置 4d3bc157… / f5ba9a82…, 假 HOME 下 `~/wide_shadow/state/rolling.npz` = A2.5 拼接缓存; 判官 `p2_g2c_judge.py` 4951caf1…(提交 7b773b8b 先于运行), 收据 `phase2/receipts/G2C_verdict.json` aa108c09… 与 `phase2/receipts/g2c/`(四份驱动收据与日志, 均 rc=0))
- **king 段(41 锚链)**: 权重 npz L∞ 最大 **9.31e-10**, **41/41 ≤ 1e-6**; 链起点诊断与 Phase 1 **逐项相同**(EMA 逆推 525 名、往返 4.77e-18、LR 截掉 40 条、LR 长 11,086、base 530); 逐锚 LR 追加条目差 **0.0**; signal 字段与线上相同 37/41(另 4 锚为 Phase 1 已记的 base_n 528 vs 530)。
- **combo 段(快照起步 3 锚, 真 171 管线 + 在役 F10 模型)**: target_live L∞ **0.0 / 0.0 / 0.0**, target_combo 0.0 ×3, king 段 content sha 相同 ×3 ⇒ **3/3**。
- **历史链 combo 残差(单列, 不作门)**: 0/41 ≤1e-6, 最大 1.1255e-04 —— **与 Phase 1 收据逐锚逐位相同(41/41)**。⇒ 该残差不来自机器(pod2 vs Mac)、不来自缓存数值来源, 也不受 AMENDMENT 5 所述早段引导行支持差的影响(本链拼接缓存屏蔽了那些格, 残差仍逐位相同)。因此 AMENDMENT 5 的归因子门 G2-C-S **未运行**(无红可归因)。
- 下一门: G2-C′(A2.5 原文)。

## 收据 5 · G2-C′ 注入管道平价 = **PASS 3/3**(2026-09-13 10:0xZ, pod2 CPU; 装置 `phase2/devices/p2_g2c_prime.py` 5adf6c42…(提交 7b773b8b 先于运行), 用实际 Phase 2 代码 `p2_driver.py` dc4e6c85… 的 `OOFBooster` / `write_f10_injection` / `write_identity_model`; 收据 `phase2/receipts/G2Cprime_injection_plumbing_{s12,s16,s20}.json` 与 `.log`, 均 rc=0)
- **king**(1789214400 / 1789228800 / 1789243200): 真 booster 记录其对 (锚, 400 名成员) 的输出后, 由 Phase 2 的 OOFBooster 查表回送 ⇒ weights npz idx 与 val **逐位相同**、float64 H 向量**逐位相同**、target_live 权重相同 ×3。
- **F10**: 对 G2-C 真管线运行留下的 mini 文件执行装置原文算出 f10(400/400 名有分), 经 Phase 2 注入(秩/128 + 恒等模型)重跑逐字节 combo 段 ⇒ state_H_f10 / kc / fc **逐位相同**、target_live_combo / target_combo / target_blend 权重相同、ρ(f10,king) 相同、n_f10_scored 400/400 ×3。
- 含义: Phase 2 的两处预测注入在生产数据上与真模型路径逐位等价; 这只证明管道, 不证明折外预测等于在役预测(D1/D2)。下一门: G2-S。

## 收据 6 · G2-S 接缝门 = **PASS**(2026-09-13 10:4xZ, pod2 CPU 2 核; 链 X / Y 由 `p2_run.py` 38688a1e… + `p2_driver.py` dc4e6c85… 跑, PIT / SLOW_v4 / v4RAW_s42 / withhold; 比较器 `p2_g2s_seam.py` 189e8b1d…(首跑 542e895f… 因逐锚重读 npz 成员被 cgroup OOM 杀掉 rc=137、未写任何读数, 日志保留为 `G2S_seam_gate.attempt1_oomkilled.log`; 修正只改读取方式, 提交 480b1d3b 先于重跑); 收据 `phase2/receipts/G2S_seam_gate.json` 14861706… 与 `RUN_seamX/Y.{json,log}`(均 rc=0; `.vec.npz` sha 见 SHA256SUMS_S1))
- **门**: X 自 2024-02-01 00Z、Y 自 2024-03-22 00Z 起跑, 共同锚 2,131; 门窗 2025-01-21 00Z → 2025-03-12 00Z 共 **301 锚**: king H / kc / fc 状态向量 L∞ 最大 **1.52e-18 / 0.0 / 8.67e-19**(阈 1e-9), w3 / traded_file / combo 返回码与原因 / members / sel **逐锚全同** ⇒ **PASS**。
- **实测暖机**: 自 Y 起点起「三向量 ≤1e-9 且分类字段全同、此后保持到终点」的首锚 = **2024-11-18 16Z = Y 起点后 1,450 锚**, 低于预注册 W = 1,830(余量 380 锚)。曲线读法: 起点差 7e-3 → 06-10 衰到 3e-11 → **06-30 因 X 的 LR 满 900 条先切换 msharpe 席位而 Y 仍等权, 差回升到 1e-3 且分类字段不同** → Y 于 08-19 满 900 条后两链同用 msharpe, 差再衰减(10-28 6.6e-9, 12-27 ~1e-15, 2025-01 起 0 或 ~1e-18)。⇒ 暖机下限由席位 900 锚窗 + 其后状态收敛共同决定, 1,830 覆盖本段。**只证明本段(2024-02 → 2025-03)**, 不外推到其它时段。
- 下一门: G2-D。

## 收据 7 · G2-D 因果审计 = **PASS**; 收据 8 · G2-E 红能力 = **PASS**(2026-09-13 11:0xZ, pod2 CPU; 审计装置 `phase2/devices/p2_g2d_audit.py` 13e911d8…(提交 32b1f749 先于运行; 规则由原始折件独立重推, p2_driver 的判定函数只作交叉核对); 收据 `phase2/receipts/G2D_causality_audit.json` 168a2e97… / `G2E_red_capability.json` 4f6e078d… 与日志, 及 G2-E 链 `RUN_g2e_corrupt_2025-03-16.{json,log}`, 均 rc=0)
- **G2-D (a) 全 W_FULL 轴 10,038 锚**: king 折表 label_end = 2024-01-01 / 2025-01-01 / 2026-01-01 00Z; F10 逐年 2022-12-22 / 2023-12-22 00Z, 月折 = 上月末 20:00Z。withhold 策略下 king 被送入 5,295 锚、**扣留 543 锚(2024/2025/2026 各 181, 首 2024-01-01 00Z 末 2026-01-31 00Z)**, F10 被送入 8,028 锚、扣留 0; **被送入却不合规 0 / 0**; 与 p2_driver 判定函数逐锚交叉核对**不符 0 / 0**。**(b) S1 全部 7 条链记录**(timing12 ×2 / smoke 2022-02 / 2024-01 / 2026-03 / seamX / seamY, 共 4,364 条): 违规送入 **0**, 记录旗标与重推规则**不符 0** ⇒ **PASS**。
- **G2-E**: 伪造折表(F10 fold 202503 := 2025-03-15 00Z, king fold 2025 := 2025-02-15 00Z)+ serve_all 跑 2025-03-16 的 6 锚, 同一审计读数 = **RED**(king 违规 6、F10 违规 6)⇒ 越界截止必然被 G2-D 抓到 ⇒ **PASS**。
- **S1 汇总(AMENDMENT 3 顺序)**: G2-B 原门 NOT PASSED AS WRITTEN(RED, 标签保留) → G2-B″ PASS → G2-C PASS → G2-C′ PASS → G2-S PASS → G2-D PASS → G2-E PASS。按简报在此停止; **本轮零书层数字, 未跑全史回放, 未算任何历史 Sharpe**。

## 附 · D17 取证(AMENDMENT 3 非阻断项; 2026-09-13 11:1xZ, Mac 只读; 装置 `phase2/devices/p2_d17_forensics.py`(提交先于运行), 收据 `phase2/receipts/D17_forensics.json` 28376c8a… / `.log` 5c873e9f…, rc=0)
- **行数与日期**(快照 1789200000 账本, 09-05 12Z 之前「存储 iv ≠ 相邻时间差 iv」的行): 12 名 —— DEXEUSDT 152 行(08-01 00Z → 08-07 08Z)、ERAUSDT 137(08-01 → 08-06 16Z)、BANKUSDT 103(08-01 → 08-05 08Z)、PROMUSDT 79(08-11 05Z → 08-14 12Z)、ACEUSDT 67(08-07 09Z → 08-10 04Z), 其余 7 名各 1 行(07-09 … 07-29); 存储值全为 4.0, 时间差值 1.0(个别 2.0)。
- **来源(VERIFIED, 逐行比对)**: 每一行都**原样出现在 08-16 bundle 的 `funding_ledger_seed.json`**(备份 `shadow_bundle.aug20260816_backup/`, sha b233a072…, 存储 iv 相同), 也原样出现在 09-04 M1 前状态备份; **09-01 v3 bundle 的种子**里同一批行多数存 1.0 / 2.0(与时间差一致)或不含该行 —— 但 09-01 换装保留了既有状态, 该种子从未载入生产者。
- **在役链路会不会再产生(VERIFIED 读码)**: 磁盘上全部 5 个生产者版本(shadow_loop / _v2 / _v3 两份备份 / 在役 e9c98374…)追加结算行时 iv 都取与上一行的时间差(同一行代码); 种子只在 `state/rolling.npz` 不存在时引导载入(在役 L193–205)。⇒ **正在运行的追加路径不会产生此类行**; 唯一的再入口是「生产者状态被重置并从一个用非时间差规则写 iv 的 bundle 种子引导」(INFERRED 潜在路径, 现行导出器优先 zip 的 funding_interval_hours 列, 其次 intervals 字典, 最后时间差)。按 AMENDMENT 3 的条件, 结论不是「在役链路仍会产生」, 故不作即时告警, 在交付中列明。
- 影响面(读码): 这些行现已不是任何名的末行 ⇒ 不再进入 FTRIM 的 rn8; 只以衰减残差留在 live EMA(收据 2: 09-12 08Z 最大 5.6e-06)。

## AMENDMENT 4 补记 A4.1a · D18 更正: 在役止损对**多头**与条款不符(2026-09-13 11:3xZ, P2 worker, 受 lead 指示; **先于任何 S2 数字**; 不改 S1)
- **事实(引 T5b `51b93969` RESULT §0「事后核实的新风险」与 §5.3, git blob sha 172ac9ff…, 已打开核对)**: 执行器把已停名目标置 0 后, `apply_withhold_and_reshape` 的 reshape(`signal/legs.py` `reshape_after_withhold`: 对含已置零名在内的全部目标去均值再 L1 重标)给所有名同一平移 a(W1∪W2 为 +1.5..+62 USDT), 已停多头的目标因此变为 +a; 随后 `clamp_held_untradable`(`scheduler/anchor_loop.py` L425–449 @918559f, 本 worker 已打开读码)对「目标同号且 ≥ 持仓」判 add_blocked 钉在原仓位, 「同号但 < 持仓」判 reduced 到 ≈ a 后再被钉住; 空头因 +a 与持仓异号而 flatten_only。W1∪W2 共 125 个「已停且持仓」实例: 多头 add_blocked **94** / reduced **23**, 空头 flatten_only 5 / 未列出 3, 平移预测 **122/122** 相符; 冷却要等书级平仓后才开始。lead: 以 W9 在执行器落地包修复, **尚未部署**。⇒ **截至目前, 在役止损对多头的实际行为不同于 D18 所写的条款语义**(条款: flatten_only 出场后 7 天冷却)。
- **STOP 臂(主)重新定义 = 条款语义 = W9 修复后的预期行为**: 被停名(多空不论)下一锚全额出场, 自出场锚起 42 锚冷却; 被停 / 冷却名按执行器 withhold → reshape 从执行书剔除, 但**不经** clamp 回钉。
- **STOP-PINNED 敏感性臂(廉价, 纳入)= W9 之前的在役行为**: 覆盖层逐锚逐字执行执行器自己的纯函数(从 dl_quant_live@918559f 只读副本按 AST 抽取原文, 不改一字): `live/per_name_stop.py` 的 `evaluate`(文件 8fb79dd8…, 计数 / stopped / 冷却状态机)、`scheduler/anchor_loop.py` 的 `withhold_pop` → `apply_withhold_and_reshape`(→ `signal/legs.py` `reshape_after_withhold`, 用 anchor_loop 的 RESHAPE_REDEMEAN / RESCALE 常量)→ `clamp_held_untradable`; 持仓名义 = 覆盖层自己按 §1「E 收盘 100% 成交」模拟的仓位 × 该臂固定 2.0× 复利 NAV; 最小名义 5 USDT。钉住行为由这些函数自然产生, 不另写规则。
- **STOP-PINNED 做不到的(明写)**: 覆盖层中的 untradable 只含止损 / 冷却名(场所可交易名单等其它 withhold 不建模); 书级保护性平仓(§4-5e 停机、E-0912-A)不建模 ⇒ 历史上被钉住的多头会一直钉到其 reshape 后目标变号或降到持仓以下, 可能比实盘(遇书级平仓即解除)更久; 真实成交 / 部分成交 / 执行钟 / 读回时点同 D18 原文。
- 三臂(STOP / STOP-PINNED / NOSTOP)的精确定义随 S2 记账合同一并冻结; 本补记不产生任何数字。

## 附 · 本地哈希复核(2026-09-13 11:3xZ; 受 lead 告警: Mac 卷 97% 满, iCloud 把 Desktop 下文件驱逐为 dataless, `shasum` 可能静默记下 sha256(空)= e3b0c442…)
- 本 worker 在 SHA256SUMS_S0 / S1 记录的 **56 条哈希全部复核通过, 0 条为空串哈希**: 本地逐条先查 APFS dataless 标志且「读到字节数 = st_size」才哈希, dataless 的改读 git 已提交对象(字节数 = `git cat-file -s`); 另在 pod2 副本上独立 `sha256sum -c` **56/56 OK, rc=0**(pod2 不受 Mac 驱逐影响)。复核时已有若干本地文件为 dataless(如 `devices/p2_driver.py`、`receipts/G2B_funding_parity.json`), 其记录值由 git 对象与 pod2 副本双重核实。收据(提交 4a6e8dd3): `phase2/receipts/HASH_REVERIFY_local_2026-09-13.jsonl`(ab2b1714…)、`HASH_REVERIFY_pod2_2026-09-13.txt`(feb61c2d…)与其输入清单(dfa13506…), 装置 `phase2/devices/p2_hash_reverify.py`(b4fa12a3…); 另附 pod2 端生成的 P2 全量清单 `phase2/SHA256SUMS_pod2_P2_2026-09-13.txt`(86 条, 6aaf937a…, 以后以此为准)。G2-C 本地暂存 `g2c_stage/` 在 cc_tmp, 不在 Desktop。

## AMENDMENT 6 · S2 记账合同(2026-09-13 11:4xZ, P2 worker, 受 lead「P2 S2 go」; **写于任何 S2 数字之前**: 本节提交后才写 S2 装置、才跑任何 S2 链 / 门 / 表; 不改 S0 / S1 的任何门、阈值、标签与读数)
- 编号: A2.6 / A4.1 / A4.1a 所说「S2 记账合同另立修订」= 本节(AMENDMENT 5 之后顺延为 6)。本节与 A2.6、A4.1 骨架、A4.1a 不一致处以本节为准, 逐条列在 A6.10。
- 为定合同读过的**既有**档案属性(均非 S2 数字)列在 A6.11。

### A6.1 臂(全部预声明; 事后不选臂; 全部报告)
| 臂 tag | king OOF | F10 OOF | 宇宙 | 供给 | 读法 |
|---|---|---|---|---|---|
| `S2_v4_s42` / `S2_v4_s2027` = P2a-v4-s42 / -s2027 | `SLOW_v4` dde19142… | `f10_v4RAW_s42` 58d64a6f… / `f10_v4RAW_s2027` 47046ccd… | PIT | withhold | **主对** |
| `S2_A0pred_s42` / `S2_A0pred_s2027` = P2a-A0pred-s42 / -s2027 | `SLOW_v3_on_v4axis` 64767318… | `f10_A0_s42` ff109711… / `f10_A0_s2027` 98bfe779… | PIT | withhold | 与 A0 模型匹配: 隔离「生产路径 vs 研究回放」 |
| `S2_v4_s42_serveall` = P2a-v4-s42-serve_all | SLOW_v4 | v4RAW_s42 | PIT | serve_all | 1 月敏感性(单种子, 无判词) |
| `S2_v4_s42_pins` = P2a-v4-s42-pins | SLOW_v4 | v4RAW_s42 | pins | withhold | 只在 D12 可行域报(单种子, 无判词) |
- 每臂 = 一条串行链: 2022-01-31 00Z → 2026-08-31 00Z 共 10,039 锚(= A0 rec 轴 = `universe.npz` 轴, 严格 4h 网格), 首锚冷启动(A2.1 I7), 全部锚记录; 驱动 `p2_driver.py` dc4e6c85… 与装置 4d3bc157… / f5ba9a82… 原样(sha 断言); 臂间差别只经 `arm` 字典与折表输入。
- **A0pred 的 F10 折表**(输入折表, 不改驱动): `f10_A0_s{seed}` = `f8_ext/preds/f10_V2MAIN_s{seed}.npy` 按 E_ts 对齐(`build_dev_v4.py` L50–51), 由 `pod_f10_train_ext.py` 逐年折 YV ∈ {2023, 2024, 2025, 2026} 产出(L266–271: train i < first_te − 60 且 year < YV)⇒ **四年全按逐年规则**: label_end(Y) = E_ext[first_te(Y) − 61] + 4h(dlw_ext 轴, 31d043e8…), 可送入 ⇔ label_end < E 所在月首。启动器在 `Globals` 构造后把该臂 `ft` 换成此表(`splice_boundary` 置 2⁶², 模型名 `F10_V2MAIN_s{seed}:fold{Y}`), 折表随 RUN 收据落盘。v4 臂 = 驱动原表(月折 202501..202608 + 逐年 2023/2024)。**king 折表**: 两种 OOF 同一规则(v3 导出器 `pod_export_bundle_v3.py` L48–52 / L55–58 与 v4 导出器同构: fold Y 拟合 anchor-year < Y), label_end 由 `wide_fea_v4_meta` 实算(驱动 `king_fold_table`), 30 天规则 ⇒ 每年 1-01 00Z..1-31 00Z 扣留。
- 收据 6(G2-S)只证明 2024-02→2025-03 段暖机; P-A 无接缝, 不依赖该门。

### A6.2 书(同一条链多读; 层级一律 = 持仓书层 / 目标权重)
- **P2-CMB(主)**: W_t = c·1[|c| > 1e-9], c = 0.55·kc_t + 0.45·fc_t, kc / fc = combo 段该锚写出的 float64 状态 `state_H_{kc,fc}_A`(= COMBO_LIVE 写者 `_weights` 的公式 L319 / L339; 差别只在状态文件按 |v| > 1e-9 截存, 逐名 |Δw| ≤ 2e-9)。**不看** COMBO_LIVE 飞前断言(D11)是否通过。该锚无状态(已知生产崩溃 `none_target_all_zero_z` 或生产者跳锚)⇒ W_t = W_{t−1}(持有不动); 链上首个状态之前 W = 0。
- **P2-LIT**(只报, 一律标注「受 D10 混杂」): traded_file = combo ⇒ W_t 同 P2-CMB 式; = king ⇒ W_t = king H_t(记录的 |H| > 1e-12 向量); = none(producer_skip) ⇒ W_t = W_{t−1}。
- **P2-KING**(只报水平与对 CMB 的差): W_t = king H_t, 跳锚持有。
- 逐臂逐年报: traded_file 三形态占比、已知崩溃锚数、跳锚数、COMBO_LIVE 失败原因计数。

### A6.3 D18 覆盖层(只作用于主对 `S2_v4_s{42,2027}` 的 P2-CMB; 三读 STOP / STOP-PINNED / NOSTOP)
- **执行器原文**: 从 dl_quant_live@918559f 的只读 git 对象复制到 pod2 `P2/work/exec_ro_918559f/`(文件 sha 断言: `live/per_name_stop.py` 8fb79dd8…, `scheduler/anchor_loop.py` 3c665b4e…, `signal/legs.py` 7c0665f8…, `config/book.json` f6fd6d0e…), 按 AST 抽取函数原文执行、不改一字: `resolve_profile` L25–42, `evaluate` L77–141, `active_sets` L144–148(per_name_stop.py); `withhold_pop` L314–331, `apply_withhold_and_reshape` L334–422, `clamp_held_untradable` L425–449, 常量 `RESHAPE_REDEMEAN = RESHAPE_RESCALE = True`(anchor_loop.py); `reshape_after_withhold` L124–198(legs.py, 作为 `LG.reshape_after_withhold` 注入)。conf = `resolve_profile(book.json["per_name_stop"])`, 断言 enabled / depth_pct −0.30 / consecutive_anchors 2 / cooloff_days 7 / min_notional_usdt 5.0。
- **单位**: NAV 取常数 **NAV_REF = 117,976.93 USDT**(STATE.md 09-12 13:3xZ 条「平仓前 NAV」), 执行 gross G = 2.0 × NAV_REF; 目标名义 = (W_t / Σ|W_t|) × G, 只列 |W_t / Σ|W_t|| > 1e-12 的名(= `EXT.target_vector` + `LG.to_notional`); 记账权重 X_t = 执行名义 / G × Σ|W_t|(与研究 `_ex` 同尺度; 无止损事件时 X_t = smr(W_t) 至浮点)。
- **价格与入场价**: 每名价格指数起点 1, P_{t+1} = P_t·(1 + y4_t), y4 = meta_newprod_v4 RAW(NaN ⇒ 价格不变); **不从 5m 缓存 ret5 重算**。份额 q = 名义 / P_t; 入场均价按交易所规则(同向加仓数量加权; 减仓不变; 归零或翻向重置为 P_t), 与研究 d30 成本基 L347–357 同构。
- **时钟**: 计划与终锚读回的 now 都取 E_t(§1 / D15: E 收盘 100% 成交)。
- **逐锚顺序**:
  1. held_t = {s: q_s·P_t[s] : q_s ≠ 0}(上一锚份额按 y4 漂移到 E_t 收盘)。
  2. sets = `active_sets(state, E_t)`; U = sets.stop ∪ sets.cooldown ∪ {held_t 中不在目标名单的名}(在役 `held_not_in_target` → `_ext_held_exit` 并入 untradable 的语义)。
  3. target = 上述目标名义字典。
  4. **STOP-PINNED(W9 前在役行为)**: sets.stop 中在 target 的名置 0.0(anchor_loop L1805–1809 `_pns_zero_targets`), 再 `apply_withhold_and_reshape(target, held_t, U, G, floors_usdt=None)`。**STOP(条款语义 = W9 后预期)**: 先把 sets.stop ∪ sets.cooldown 的名从 target 中 **pop**(不进入重整集), 再同一调用 ⇒ 持有的被停名经 clamp 的 flatten_only 分支到 0, 其余名按执行器重整(去均值 + L1 复原)。**NOSTOP(对照)**: X_t = smr(W_t)(研究 `_ex` 变换 L324–330), 不经执行器函数。
  5. 执行名义 N_t = 调用后的 target(不在字典的名 = 0), 于 P_t 成交: 更新份额与入场均价。
  6. 终锚读回快照: positions_notional = {s: N_t[s] ≠ 0}, positions_unrealized = {s: q_s·(P_t[s] − avg_s)}; state = `evaluate(snapshot, state, conf, E_t)`。
  7. X_t = N_t / G × Σ|W_t|。
- **做不到的(叠加 A4.1 / A4.1a 原列)**: 执行器其余 withhold(场所可交易名单、exchangeInfo 元数据排除、2× 最小名义资格、known-gap 上限)与 floors 跨越检查; 真实时钟(读回晚于 E、计划在 N+23 ⇒ 冷却可能晚一锚结束); NAV 随时间变化; W9 最终实现若不是「从重整集 pop」, 与 STOP 的差为每个被停名 O(平移 a)。

### A6.4 记账(v4 钉; 逐式同 `w10_sleeve_r18.py` 9b8a6323… L324–339 / L362–365 / L386–389)
对任一权重序列 X_t(829 轴, 符号 sha 381b7f01…; X_{首锚−1} = 0):
- i = meta 行(`meta_newprod_v4.npz` 0e3c09ac…), j = 面板行(`wide_panel_4h_v2ext.npz` 5e67c055…)。y = nan_to_num(y4[i], 0)(**float32 RAW**, Π(1+r)−1 谱系; 禁 ret5); fnow = nan_to_num(f_fund_now[j], 0); iv = f_fund_iv[j](有限且 > 0, 否则 8.0); qv4h = expm1(clip(qvk[i], 0, 30))·48(float32); tier = 0 若 qv4h ≥ 5e6, 1 若 ≥ 1e6, 否则 2(NaN ⇒ 2); rate = fr·mk + (1 − fr)·tk, (mk, tk, fr) = `costb_PWR_G230k.json` 295b4e7b… 三档。
- pnl_ex = 1e4·Σ_S X_t·y; carry_ex = 1e4·Σ_S X_t·fnow·(4 / iv); cost_ex = Σ_S |X_t − X_{t−1}|·rate; net_ex = pnl_ex − carry_ex − cost_ex; gross_total = Σ_{全 829}|book|; **g = net_ex / gross_total**(bps / 锚 / 单位 gross)。
- **求和集 S**: 「members」= 研究成员集 m_i = members[i] ∩ UMASK_ROW[j](只用于 GATE S2-P-acc 复现研究存档); 「full」= 全 829 名(**全部 P2 书**)。理由: 生产成员集 ≠ 研究 m(D10), P2 持有研究 m 之外的名。
- **NOSTOP**: nz = |W_t| > 1e-12; smr = W_t, smr[nz] −= mean(smr[nz]), 若 Σ|smr| > 1e-9 则 smr ×= Σ|W_t| / Σ|smr|; X_t = smr; gross_total = Σ|W_t|。**覆盖层**: X_t 取 A6.3, gross_total = Σ|X_t|。
- **空书**: gross_total = 0 且 Σ|X_t − X_{t−1}| = 0 ⇒ g = 0(逐年计「空仓锚」); gross_total = 0 而有交易 ⇒ RED(停并报)。
- **研究参照**(同锚配对; g 直接取存档 rec 的 net_ex / gross_total, 不重算): **A0** = r18 C0 存档 `C0_s{seed}.npz`(d6298deb… / fa5ed19a…; 其 `d30_n2_c42_rec/W` 与 r3k A0 存档 352ac36f… / aa44e18f… 逐位相同 = RECEIPT_r18_drive_gateP 的 GATE P), 取两条: **A0_d30**(研究目标层止损 d30_n2_c42 = 发布件, s42 W_ALPHA 0.6341957)与 **A0_S0**(同装置同跑的无止损版本 = A4.1 所说「A0 的无止损版本」); **NW** = r18 `NW_s{seed}.npz`(afbcd92e… / 89d28a31…)的 S0 / d30; **A1-NW** = GATE S2-P-NW 通过后新跑的 S0 / d30。诊断(无判词): A0 存档 float32 W 按 full 口径重记账与存档之差 Δ_set, 逐窗报。
- 执行 = 100% 于 E 收盘(D15)。§1 的 exec 口径敏感性臂(E+24m)**S2 不跑**(A6.10-5)。

### A6.5 窗口
- W_FULL = A0 轴 ts ≤ 2026-08-30 20Z(n = 10,038); W_ALPHA = W_FULL ∧ 行 ≥ 900(n = 9,138, 首锚 2022-06-30 00Z); FROZEN = 2025-03-01 00Z ≤ ts ≤ 2026-08-10 20Z(n = 3,168)。各窗 n 由装置断言。
- pins 臂: 只报 D12 可行域 ts ≥ 2025-09-19 12Z 与各窗之交(n 由装置报)。serve_all 臂两读: (i) 全部锚; (ii) 剔除 `S2_v4_s42` 的 543 个 king 扣留锚(配对两侧同剔)。
- 逐年表: W_FULL 按 UTC 自然年 2022(01-31 起)… 2026(至 08-30 20Z)。

### A6.6 统计(全部冻结)
- **水平**(每 臂 × 书 × 覆盖层 与每条参照, 每窗): n, 均值 g, Sharpe = mean / sd(ddof=1)·√2190, g 的 CI95(自举同下, k = 0 与 k = 9), pnl / carry / cost 各自除 gross_total 的均值, gross_total 均值, 换手 Σ|X_t − X_{t−1}| / gross_total 均值, 年化 %/gross = 均值·2190 / 100。
- **逐年**(W_FULL): n, g, Sharpe(n > 30 才报), 年化 %/gross, **NEG = 均值 g < 0(显式标)**, 年内 2.0× 复利 maxDD(含年初起点), 最差 UTC 日(2.0× 日收益)与日期; 配对对照另报逐年 Δg(无 CI)。
- **maxDD(固定 2.0×)**: 窗内每 UTC 日(ts // 86400)r_d = Π_{t∈d}(1 + 2.0·g_t·1e-4) − 1; NAV = [1, cumprod(1 + r_d)](含窗起点, E-0909-C); maxDD = min(NAV / cummax − 1), 报峰 / 谷日期与最差日。
- **配对**(同锚): d_t = g_arm,t − g_ref,t; Δg = mean(d); ΔSharpe = SR(arm) − SR(ref); 另报 Δpnl / Δcarry / Δcost(/gross)与 d 非零锚数。
- **自举** = `judge_v4.py`(retrain_2026-09/v4_chain_2026-09-09, c2a81c48…)的 `boot()` **按 AST 抽取原文执行**: days = ts // 86400; S = bincount(v), N = bincount; idx = rng.integers(0, nd, size=(2000, nd)); mn = S[idx].sum(1) / N[idx].sum(1); CI95 = percentile 2.5 / 97.5; P>0 = mean(mn > 0)。**rng = np.random.default_rng([20260905, k])**, 每个(对照, 种子, 窗)新建生成器, **k = 0 主读、k = 9 复核**(不用 r18_judge / T6 的「每次抽样一条流」形式)。ΔSharpe CI: 以同一 (20260905, k) 重建同一 idx, 按 `t6_compute.py` `boot_sr_pair` 的式子由日和与日平方和算两侧 SR 之差, CI95 同分位。
- **DSR**(只对主臂 = `S2_v4` P2-CMB STOP, 每种子): `t6_compute.py`(103974f3…)的 `psr` / `sr0` 按 AST 抽取原文执行(γ = 0.5772156649015329; N < 2 按 2 计并标旗); T = 窗内锚数; g3 = skew(bias=False), g4 = kurtosis(fisher=False, bias=False) 取本臂窗内 g; **V_SR_pp 与 N_eff 取 `RECEIPT_T6_compute.json`(7c41281a…)RESULTS 同种子同窗的 F1 块**(W_FULL、FROZEN 两种子; W_ALPHA 只有 s42 块 ⇒ s2027 的 W_ALPHA 不报); N ∈ {N_eff, 300}; 报 SR_annual、SR0_annual、P(真 SR > 0)、P(真 SR > 3)。

### A6.7 对照清单与判词
- 判词只在双种子对照上下、且只用于 P2-CMB 对照。规则(v4 同 + 原 §3 分辨率): 对每个(对照, 窗), **任一种子 |Δg| < 0.23 bps/锚/gross ⇒「(C) 不可区分」**; 否则两种子均 Δg > 0 且 CI95(k = 0)下界 > 0 ⇒ **(A)**(Δ > 0 可分辨); 两种子 CI95 上界 < 0 ⇒ **(B)**(Δ < 0 可分辨); 其余 ⇒ **(C) UNDECIDED**。k = 9 按同规则另判; 与 k = 0 的词不同 ⇒ 列入「矛盾」, 判词仍取 k = 0。ΔSharpe 只报 CI 不下词。(A) / (B) 只表示差的符号可分辨, 不是任何改动的晋级 / 否决。

| id | 对照(同锚配对) | 判词 |
|---|---|---|
| K1 | v4 CMB-NOSTOP − A0_S0 【**「生产路径 vs 研究回放」主差**(含 v4 模型换代), 两侧均无止损层, A4.1】 | 是 |
| K2 | v4 CMB-STOP − A0_d30 【两侧各带自己的止损层; A0 = 发布件】 | 是 |
| K3 | K2 − K1 = (STOP − NOSTOP)_P2 − (d30 − S0)_A0 【止损层分量, A4.1 单列】 | 是(无 ΔSharpe) |
| K4 / K5 | v4 CMB-NOSTOP − NW_S0 / v4 CMB-STOP − NW_d30 | 是 |
| K6 / K7 | v4 CMB-NOSTOP − A1NW_S0 / v4 CMB-STOP − A1NW_d30 【同模型(v4): 生产路径 vs 研究回放】 | 是 |
| K8 | v4 CMB-STOP − v4 CMB-NOSTOP 【执行器止损覆盖层效果】 | 是 |
| K9 | v4 CMB-STOP-PINNED − v4 CMB-STOP 【钉住效应】 | 是 |
| K10 | v4 CMB-STOP-PINNED − A0_d30 | 否(只报) |
| M1 | A0pred CMB-NOSTOP − A0_S0 【**同模型(A0 模型): 生产路径 vs 研究回放**】 | 是 |
| M2 | A0pred CMB-NOSTOP − NW_S0 | 是 |
| M3 | v4 CMB-NOSTOP − A0pred CMB-NOSTOP 【生产路径内的模型换代】 | 是 |
| S1 / S2 | serve_all CMB-NOSTOP − v4_s42 CMB-NOSTOP / − A0_S0(s42), 读法 (i)(ii) | 否(单种子) |
| P1 / P2 | pins CMB-NOSTOP − v4_s42 CMB-NOSTOP / − A0_S0(s42), 只 D12 域 | 否(单种子) |
| L1–L4 | LIT(v4) − A0_S0; LIT(v4) − CMB-NOSTOP(v4); LIT(A0pred) − A0_S0; LIT(A0pred) − CMB-NOSTOP(A0pred) 【受 D10 混杂】 | 否 |
| G1 / G2 | KING(v4) − CMB-NOSTOP(v4); KING(A0pred) − CMB-NOSTOP(A0pred) | 否 |
| R1–R3 | 研究侧语境: A1NW_S0 − A0_S0; A1NW_d30 − A0_d30; NW_d30 − A0_d30 | 否 |
- 水平读数主行 = v4 CMB-STOP(A4.1: 一切尾部 / 回撤读数只从 STOP 出); NOSTOP 与 STOP-PINNED 并列。

### A6.8 门(冻结; 阻断门红 ⇒ S2 停止并上报, 不出表; 阈值不改)
| 门 | 内容 | 通过 |
|---|---|---|
| S2-FN | 执行器三个源文件与 book.json 的 sha = A6.3; AST 抽到的函数行号 = A6.3; conf 值 = A6.3 | 全等 |
| S2-P-acc | members 口径记账作用于存档 float32 W, 复现存档 rec 的 pnl_ex / carry_ex / cost_ex / net_ex 与 gross_total: r3k A0 两种子、C0 S0 / d30 两种子、NW S0 / d30 两种子(共 10 条序列, 全锚) | 逐锚 max|Δ| ≤ **1e-4 bps**(四列), |Δgross_total| ≤ 1e-6; 另 full − members = m 外名贡献的独立求和(≤ 1e-9) |
| S2-P-NW | 新 runner 在 P2 根下原样跑 r18 装置(9b8a6323…)NW 旋钮两种子 | S0_rec / S0_W / d30_n2_c42_rec / d30_n2_c42_W / cols / symbols 与 NW 存档**逐位相同**; 过后才跑 A1-NW(环境差恰为 SLOW_NPY 与 FPRED 两键, 装置断言) |
| S2-BOOT | (i) 自举函数 = judge_v4.py 抽取原文(源 sha 入收据); (ii) ΔSharpe 例程重建的 idx 所得 Δg CI 与 boot() 输出逐位相同(A0_S0 vs A0_d30, 两种子三窗, k = 0 与 9); (iv) ΔSharpe 向量式与逐次显式重抽(20 次)相等 | (i)(ii) 逐位; (iv) ≤ 1e-9 |
| S2-BOOT-iii(**非阻断**) | 复现 JUDGE_v4.json(efb51ef0…)A1−A0 dyn s42 与 s2027(k = 0)、A2−A0 dyn s42(k = 1)的 delta / ci95 / p_gt0(dev_v4 臂文件 sha 入收据) | ≤ 1e-12 且 p 相等; 不过只列入矛盾 |
| S2-DSR | 以 r3k A0 存档 g 与 T6 收据的 V_SR_pp / N_eff / T 复现 T6 收据 A0 条目(F1_s42 W_FULL / FROZEN / W_ALPHA, F1_s2027 W_FULL / FROZEN)的 SR_annual、skew、kurt、SR0_annual(N_eff / N_300)、P_true_SR_gt_0 与 gt_3(N_eff / N_300) | 每项 ≤ 1e-9 |
| S2-OVL-RED | A6.9 合成场景结果全部等于预写值 | 全等(浮点 ≤ 1e-12) |
| S2-RUN | 6 条链 rc = 0 且父进程汇总行在; 每条 RUN 收据 n_records = 10,039、锚 = A0 轴、fatal = None、驱动 / 装置 sha 同上、arm 字段 = A6.1; 非已知崩溃的 combo 非 0 / 3 返回码 = 0; 有 `combo_file_vs_states_Linf` 的锚 ≤ 1e-8 | 全满足 |
| S2-D | 新审计装置按臂独立重推规则(king: SLOW_v4 与 SLOW_v3_on_v4axis 同一 30 天规则; F10: v4RAW_s{seed} = `RAW_s{seed}` 月折配置 + 逐年 2023/24, A0_s{seed} = 四年逐年)审计全部 S2 记录: withhold 臂「送入却不合规」= 0; 记录旗标 / 模型名 = 重推; king 扣留锚集 = 2024/25/26 各 1-01 00Z..1-31 00Z(OOF 有值者); serve_all 臂送入的不合规锚 ⊆ 该集且 F10 = 0(设计内, 标红只报) | 全满足 |
| S2-OVL-ID | 真 P2-CMB 两种子: conf enabled = False 时 STOP 与 STOP-PINNED 逐锚复现 NOSTOP | |Δg| ≤ 1e-9 bps 且 ‖ΔX‖∞ ≤ 1e-12 |

### A6.9 覆盖层合成红控(S2-OVL-RED 预写结果; 6 名, 目标恒为 W = [+0.20, +0.15, +0.15, −0.20, −0.15, −0.15], 61 锚, NAV_REF / conf 同 A6.3)
- **场景 A(多头止损)**: 名 0 的 y4 在锚 2 为 −0.40, 其余全 0。预写: 锚 3、4 读回深度 −0.40(锚 3 再平衡把入场均价摊到 0.84), **锚 4 触发 stopped**。STOP: X[0] 在锚 5..46 **恰为 0**, 锚 47 再入(冷却 until = E_5 + 7 天 = E_47; `active_sets` 用 `>` ⇒ 锚 47 已不在冷却); 锚 5..46 其余五名 X = [0.25, 0.25, −4/19, −11/76, −11/76]。STOP-PINNED: 锚 5 起 X[0] = **1/24**(去均值平移 1/30 后 L1 复原, clamp 判 reduced), 此后一直钉住、从不进入冷却, 其余五名 X = [11/48, 11/48, −5/24, −7/48, −7/48]。NOSTOP: X 恒 = W。
- **场景 B(单锚越线后回升)**: 名 0 的 y4 在锚 2 为 −0.40、锚 3 为 +1.00。预写: 锚 3 计数 1, 锚 4 深度 +0.30 复位, 全程无 stopped; 三读逐锚相同。
- **场景 C(dust 不计)**: 场景 A 价格, 目标换为 W = [+1e-5, +0.35 − 1e-5, +0.15, −0.20, −0.15, −0.15](名 0 名义 ≈ 2.36 USDT < 5)。预写: 名 0 从不计数、从不 stopped; 三读逐锚相同。
- **场景 D(关闭)**: 场景 A 价格 + enabled = False ⇒ 三读逐锚相同。
- 预写值在装置里写成常数, 并由独立的逐步手算实现交叉核对; 任一不符 ⇒ 门红。

### A6.10 与此前文本的差异(逐条)
1. A4.1 骨架「min_notional 5 USDT 按该臂固定 2.0× 复利 NAV 路径换算」→ 常数 NAV_REF。理由: 该量只决定 dust 门槛; 复利路径需要任意起点 NAV, 并让门槛依赖覆盖层自身已实现路径; T5b 观察到的钉住发生在 ≈ 11.8 万 NAV 量级。
2. STOP 精确化为「被停 / 冷却名从重整集 pop, 持有者经 clamp flatten_only 到 0」(A4.1a「按执行器 withhold → reshape 剔除, 不经 clamp 回钉」的实现形式)。
3. A2.6「UTC 日块自举 2000 次, default_rng([20260905, k]), k = 0 主 / k = 9 复核」钉为 judge_v4 `boot()` 形式(每个对照一个生成器)。
4. 判词只下在 P2-CMB 的双种子对照; P2-LIT / P2-KING / 单种子臂只报数(A2.6 未限定)。
5. §1 的 exec 口径(E+24m)敏感性臂 S2 不跑。
6. P2 书的记账求和集 = 全 829 名(研究为 m)。
7. serve_all 两读 (i)(ii)(D14 原文只有 (ii))。
8. A0 的无止损版本 = C0 存档 S0(A4.1 未指明来源)。
9. P2-CMB 在崩溃 / 跳锚锚持有不动(A2.6 未定义)。
10. DSR: s2027 的 W_ALPHA 无 T6 块, 不报。

### A6.11 设计期只读事实(非 S2 数字)
- OOF 逐年有值行: SLOW_v4 与 SLOW_v3_on_v4axis 只有 2024–2026(2026: 1,458 / 1,452 行); f10_v4RAW 与 f10_A0 2023–2026(2026 A0: 1,452 行); 2022 均无。
- 829 符号轴(381b7f01…)在缓存 / 面板 / umask / r18 存档间相同; A0 轴 = universe 轴、严格 4h、⊂ meta 与面板时间轴; meta 的 y4 / qvk 为 float32。
- **新偏差 D20(读码 VERIFIED)**: king OOF 只在「该锚前向 4h 标签有限」的成员上有值(v3 导出器 L66–67 / L77–78, v4 导出器 L80–81 / L91–92: `PRED[a, m[isfinite(y4[a, m])]]`), 有限标签 < 50 的锚整行无值 —— 可得性掩码依赖未来收益是否存在; 生产 booster 给全部成员打分。A0 用同一数组(同掩码); C0 另有前向 y4 资格规则(r18 N2, NW 已修), P2 生产路径没有该规则。S2 不修正, 列为继承偏差; F10 OOF 的可得性掩码未核。
- S1 链记录: 1 月 king 扣留锚上出现 `combo_known_crash = none_target_all_zero_z`(seamX 181 锚 = 2025-01 扣留锚; 该段席位 fund 腿权重为 0 ⇒ kc 链 z 全 0 ⇒ chain() 返回 None)。S2 按 A6.2 持有不动并逐年计数; serve_all 臂即其敏感性。
- S1 seamX 2,131 锚每锚均 1.143 s(2 链并行)⇒ S2 每链估 3.2–4.5 h; r18 装置单跑 ≈ 27 s(RECEIPT_r18_drive_gateP); pod2 /workspace = MooseFS fuse。

### A6.12 执行计划 P-A 与资源(A4.3 R1–R3 继续有效)
- 装置(全部先提交再跑; 本地 `phase2/devices/` 与 pod2 `P2/devices/` sha 一致): `p2_s2_lib.py`(记账 / 覆盖层 / 抽取 / 统计)、`p2_s2_launch.py`(父进程载缓存一次, fork 6 条链, 每链 OMP = 1, nice 10)、`p2_r18_runner.py`(S2-P-NW → A1-NW)、`p2_s2_gates.py`(S2-FN / P-acc / BOOT / DSR / OVL-RED)、`p2_s2_audit.py`(S2-D)、`p2_s2_tables.py`(S2-RUN、S2-OVL-ID 之后出全部表)。
- 顺序: 提交本修订 → 提交装置 → pod2 预检(只读查看受保护 PID 333197 / 339489 状态; 有非 lead 重负载则排队; cgroup memory.current; loadavg)→ 后台启动链父进程(只写 P2 根)→ 链运行期间前台跑 runner 与 gates(rc + 汇总行入收据)→ 链完成后前台跑 S2-D → tables → 收据入库。等待一律前台 until 循环, 不用监视器。
- 资源: 6 链 + runner(≤ 2 × 3 线程)+ gates 1 核 ⇒ ≤ 13 核 ≤ 32; 内存预计 ≤ 25 GB(缓存 5.7 GB 共享页 + 每链约 1.5–2 GB, 估计), 每次加任务前读 memory.current, > 45 GB 不再加; 回放 HOME 在 `P2/work/runs/<tag>/`(每锚覆盖写 rolling.npz ≈ 23 MB 与小文件; 无多 GB 写入, 无单次 > 500 MB 写入)。不 pkill / killall, 不向受保护进程发信号。
- 收据: pod2 `sha256sum`; 取回本地的收据用 `t6_sha_guard.py` 哈希; 提交一律显式 pathspec, 提交后 `git show --stat HEAD` 核对。

### A6.13 不主张
不提出任何书行为改动; (A) / (B) 不是晋级或否决; 覆盖层读数只主张「生产目标 + A6.3 近似」, 不主张尾部行为的生产路径保真(A4.1); 水平不代表在役月度重训(D1 / D2)、不代表 pins 宇宙(D4)、不修正 D20。

## AMENDMENT 7 · G2-C-BIND 门 + S2 报告附加规定(2026-09-13 14:1xZ, P2 worker, 受 lead 三条指示: 「AMENDMENT 6 accepted; confirm maxDD + D20 bias note」「add G2-C binding gate; label S2 uncertified」「G2-C-BIND spec approved with two additions」; **写于任何 S2 书层数字之前**(此刻 S2 链仍在跑, 出表装置未运行); 不改 AMENDMENT 6 的任何臂、记账、统计、判词与门阈值)

### A7.1 独立研究员原话(第四轮复审 9dc41644, `docs/REVIEW_round4_code_and_research_2026-09-13.md`, 只读)
- §5.3「新增 P2 仪器门缺口：三个槽位未绑定三个锚」原文: 「`phase2/devices/p2_g2c_judge.py:37` 只取每份 `anchors[0]`，`:41` 的 `combo_ok` 只看 rc 和 Linf，不验预定锚、长度或三锚不同。」「对**原判官的快照折叠循环与布尔表达式**做内存变异，结果：同一 12Z 正收据放三个槽 → PASS；三个错误锚 → PASS；正确第一锚后追加失败第二锚 → PASS；正常第一锚 Linf 改坏 → RED。当前真实三份分别是 `1789214400/1789228800/1789243200`，源 SHA 和内容已独立核对，**没有发现本次用了重复收据**。」「最小补门：冻结 slot→anchor，要求每份恰一锚、集合无重漏，并核 prep/输入身份与实际执行收据一致。重跑判官正反控即可」
- §5.1 原文(措辞更正的依据): 「相对原“只核终点”的局部端口自检，新门核全 41 锚确实更严；**相对原“冷启动历史状态等于 live”的门，两者不是同一个命题，不能用更小 epsilon 宣称全局只加严。**」「所以我接受 AMENDMENT 3 作为结果已见后的、明确标注的探索性范围修订」
- §5.2 表格原文: 「combo 历史链同 41 锚 | **0/41 达 1e−6**；最大差 **1.12547e−4** | 历史状态残差仍存在，未被新模式抹掉」
- §5.3 末段原文(覆盖层时钟): 「P2 STOP 近似是 E 收盘完全成交，实际执行钟/部分成交不同；原 stop 代码在**整个读回 snapshot=None** 时保持 counter，而“有效 snapshot 内缺该名”才归零。独立例“深读→整次读回缺失→深读”仍计满两次。需选择并写清模拟的时钟/缺失规则」
- `multi_asset/exports/research/codex_round4_code_review_2026-09-13/research/RESULT.md` 中无 G2-C 专段(其 P2 字样为优先级标签), 本门以复审 §5.3 为准。

### A7.2 G2-C-BIND 门(冻结; 装置 `phase2/devices/p2_g2c_bind.py`, 运行前提交; 只读真实收据, 变异件只写 `P2/work/g2c_bind_mutants/`)
被测对象 = 收据 4 的 G2-C 束: `receipts/G2C_verdict.json`、`receipts/G2C_prep.json`、`work/g2c_{s12,s16,s20}/receipts/PARITY_G2C_snapshot_{12,16,20}Z_{A}_{A}.json`、`work/g2c_chain/receipts/PARITY_G2C_chain_1788624000_1789200000.json`, 以及它们指向的回放/生产者文件。冻结槽位: **s12 → 1789214400, s16 → 1789228800, s20 → 1789243200**; 链 = 1788624000 + 14400·k, k = 0..40。
- **B1 槽位↔锚**: 判官收据的快照槽恰为 {s12, s16, s20}; 每槽 anchor = 冻结值; 三锚互异; 每槽收据路径 = 规范路径; 记录的 receipt_sha256 = 磁盘文件 sha。
- **B2 每份恰一锚**: 每份快照收据 `anchors` 长度恰为 1, 其 anchor = 槽锚, mode = snapshot, snapshot 目录 = `work/snapshots/{A − 14400}`。
- **B3 prep / 输入身份**: `G2C_prep.json` 的 runs[g2c_{slot}]: anchors = [A]、A_end = A、snapdir = A − 4h、aux = A、mode = snapshot、root / fake_home 为规范路径; 判官记录的 prep sha = 磁盘; 快照收据 rolling_sha256 = prep hybrid_sha256 = 磁盘 fake_home `state/rolling.npz`; aux_sha256 = 磁盘 fake_home `state/aux.json` = prep 登记的 `snap_{A}_aux`; 快照收据与链收据的 device_sha256 = 4d3bc157…、production_sha256 = e9c98374…; 各 run 目录 dev 副本 sha = replay_driver f2ced820… / combo_stage_replay f5ba9a82… / shadow_loop_v3_replay 4d3bc157…; 日志末行 rc=0。
- **B4 快照起点确为 A − 4h**: `snapshots/{A−4h}/aux.json` 的 last_anchor = A − 4h, 该目录 SHA256SUMS.txt 对在场文件逐一相符; fake_home `fea171/state_H_{f10,kc,fc}_{A−4h}.npz` 在且 anchor 字段 = A − 4h; fake_home `state/weights/{A−4h}.npz` 在; hybrid rolling 的末行 ts = A 且 = prep 记录的 hybrid_ts_last。(lead 批准稿写「rolling 末 ts ≤ A」; 实物是 prep 截在 A_end = A 的拼接缓存, 故冻结为更严的「= A」。)
- **B5 文件锚**: 生产者 `state/target_live/{A}.json` 与 `state/target_combo/{A}.json`、回放 `state/target_live_combo/{A}.json` 与 `state/target_combo/{A}.json` 的 anchor_ts 均 = A。
- **B6 人口绑定(lead 补充 4)**: 每个被判记录, 实际比较的名集合 = 生产者该锚目标文件的名集合, 无静默丢名或加名, 比较计数 = 该集合大小。combo: 回放 target_live_combo 名集 = 生产者 target_live 名集, 收据 target_live_n = [n, n] 且 n = 集合大小, 在该集上重算 L∞ = 收据值(逐位); target_combo 同样。快照锚上的 king: 回放与生产者 `weights/{A}.npz` 的非零 idx 集合相同, 收据 n_nonzero_replay = n_nonzero_live = 集合大小, 稠密 L∞ 重算 = 收据值; king `target_live` JSON 名集相同且 n_names 相符。
- **B7 king 链 41 锚**: 链收据 anchors 恰为冻结 41 锚(顺序、互异); prep runs[g2c_chain].anchors 同; 每锚按 B6 的 king 规则绑定生产者 `weights/{A}` 的成员集(非零 idx 集合相同、计数相符、L∞ 重算 = 收据 = 判官 per_anchor 值), 且 ≤ 1e-6 在 41/41 上重判; 链收据 rolling_sha256 = prep hybrid_sha256 = 磁盘; 判官记录的 chain_receipt_sha256 = 磁盘。连续 combo 历史链不在本门判定内(原门不判, 仍 0/41), 只描述性报其名集是否相同。
- **B8 红能力(lead 补充 5 + 复审三例)**: 变异件只在 `P2/work/g2c_bind_mutants/` 生成, 真实收据只读; 下列 6 个变异束**每个都必须读 RED**: M1 错锚(s16 收据锚改为 1789243200, 判官记录的 sha 同步改为变异件 sha, 使只剩锚绑定可抓); M2 丢名(回放 s16 `target_live_combo/{A}.json` 删去 |w| 最小的一名, 收据不变); M3 sha 不符(s20 收据改一个无关字段, 判官记录 sha 不变); M4 同一 12Z 收据放三槽; M5 s12 收据在正确第一锚后追加一个失败的第二锚(判官 sha 同步); M6 三槽收据轮换(每槽都是别的锚)。真实束必须读 PASS(正控)。
- **判定**: G2-C-BIND = PASS ⇔ 真实束 PASS 且 M1–M6 全 RED。真实束若 RED ⇒ G2-C 标签按 lead 指示重审并上报, 不阻断 S2 出表(lead: 「S2 is not blocked」), 但 RESULT 不写任何 S2 数字直到本门已运行。收据 `receipts/G2C_BIND.json` + `.log`(rc 与汇总行)。

### A7.3 S2 报告附加规定(不改 AMENDMENT 6 的计算)
- **maxDD 澄清**: A6.3 的常数 NAV_REF = 117,976.93 USDT **只用于**覆盖层的止损尺寸(min_notional 5 USDT 的换算); A6.6 的固定 2.0× 复利 NAV maxDD 对**每个臂 × 书 × 覆盖层 × 窗(及逐年)照报**, 各自由其 g 序列算(日收益 Π(1 + 2.0·g·1e-4) − 1, NAV 前置 1.0), 与 NAV_REF 无关。
- **D20 偏向与量级(lead 指示 2)**: D20 = king OOF 只在前向 4h 标签有限的成员上有值(A0 同掩码), 是**前视的可得性掩码**: 下一期收益不存在的名(将下市、停牌、流动性断档)拿不到 king 分 ⇒ **很可能同时抬高 A0 与 P2**(把未来坏名从 king 打分人口里预先剔除); 另有继承的记账惯例: 持仓名的 y4 为 NaN 时收益记 0(未知收益敞口, 已在 A6 逐年报)。出表装置新增逐年描述量(无门): 每个 king OOF 数组(SLOW_v4 用于 v4 臂, SLOW_v3_on_v4axis 用于 A0pred 与 A0)在有折的行上, 「被掩码剔除的成员-锚格数」= Σ 该行导出器成员集(`wide_fea_v4_meta` members)中 OOF 非有限的格数(整行 < 50 个有限标签而全空的行另计), 以及成员格占比; 「书 gross 占比」= 该年 Σ_t Σ_{被剔除格} |W_t| / Σ_t Σ |W_t|, 对 P2-CMB NOSTOP(v4 两种子、A0pred 两种子)与 A0_d30 存档 W(用 SLOW_v3 掩码)各报。RESULT 的偏差表 D20 行写明偏向方向与这些量。
- **覆盖层时钟 / 缺读回规则(复审 §5.3 末段)**: 模拟中每锚恰有一次完整终锚读回快照(E 收盘成交后); **不存在「整次读回 = None」的锚**(在役此时 `evaluate` 保持计数, 覆盖层不模拟); 快照内缺名(已平或 dust < 5 USDT)按 `evaluate` 第 3–4 步归零。E 收盘完全成交是近似, 执行钟与部分成交不模拟(A4.1 / A6.3 原列)。
- **标签(lead 指示 2)**: S2 全史数字一律带标签「**生产路径历史 combo 链未被 S1 认证**: king 连续 41/41 与 3 个快照起步锚通过, 连续 combo 历史链不通过(0/41 @ 1e-6, 最大 1.12547e-4)」; 不得把 S2 描述为「生产路径平价已通过」。
- **措辞勘误**: (i) AMENDMENT 3 的「新具名子门 G2-B″ …(只加严)」应读作: **仅相对原端口自检 (ii)「只核终点」更严; 相对原 G2-B「冷启动历史状态 = live」门是不同命题, 属结果已见后透明标注的研究范围收窄, 不是全局只加严**(原 G2-B RED 保留); (ii) A2.5 的「G2-C′ 注入管道平价(新增, 只加严)」应读作「新增一门、不替换任何原门」。两处原文不删, 在原位加注指向本节。

## AMENDMENT 8 · 判词改用 K2 共享等价标签(2026-09-13 15:3xZ, P2 worker, 受 lead「adopt K2 labels before S2 tables」; FX-EVAL `docs/fixprogram_2026-09-13/REPORT_FX_EVAL.md` F22; **写于任何按新规则发出的 S2 判词之前**)
- **先披露**: `receipts/S2_TABLES.json`(2f3c67f6…)已于 15:09:49–15:11Z 按 A6.7 旧规则出过判词; K2 指示在 15:14Z 之后才送达本 worker。该表的**数**(水平、Δg、CI95 k0/k9、ΔSharpe、maxDD、逐年、DSR、D20、偏差计数)不依赖判词规则, 保留原样; 其 `verdicts` 字段与 .md 的判词表**全部作废, 不得引用**。新判词只由本节装置从该表的区间重发(不重算任何区间)。
- **缺陷(FX-EVAL 原文)**: 「PRECEDENCE(无差分支先于方向分支) | F22 P2 `p2_s2_lib.py:375`」; 「+0.20 [+0.10, +0.30] 两种子 → P2 先判「(C) indistinguishable」, 盖掉了 (A)」; 「0.23「不可区分」出自 P2 预注册 L29/A6.7 与 `p2_s2_lib.py:375`, 其中 0.23 是 r15/r18 的自举分辨率, 不是经济带」。
- **撤回**: 原 §3 末句「分辨率 0.23 bps/锚/gross 以下的差异一律"不可区分"」与 A6.7 的「任一种子 |Δg| < 0.23 ⇒ (C) 不可区分」**作废**(原文不删)。
- **新规则(替换 A6.7 判词规则; 对照集合、窗口、区间、k=0 主 / k=9 复核不变)**: 每个(对照, 窗)取两种子区间 `Interval(point=Δg_s, lo=CI95_k0 下界, hi=上界, level=0.95)`, 标签 = `equivalence_labels.v4_label(cells, margin=D1)`(`multi_asset/exports/research/common/equivalence_labels.py` sha256 ab651754…, 提交 f0cfe770; 装置在 pod2 用 sha 核过的只读副本): 方向词 (A) ⇔ 两种子点估计 > 0 且下界 > 0, (B) ⇔ 两种子上界 < 0(与 judge_v4 逐字同), **方向分支先求值**; 否则 (C) 按 TOST 细分 **(C) EQUIVALENT**(两种子均 −δ < lo 且 hi < +δ)/ **(C) NOT EQUIVALENT**(两种子均 lo ≥ δ 或 hi ≤ −δ)/ **(C) INCONCLUSIVE**(其余, 含 CI 含 0 或点估计在带内而区间出带、两种子冲突)。**δ = D1 = 0.05 bps/4h 锚/单位 gross**(`docs/fixprogram_2026-09-13/FX_EVAL/DELTA_TABLE_K2.json` sha256 ad6af207…, key D1; 单位、经济理由与来源照该表); 敏感性列 D1 ∈ {0.02, 0.25} 只报不定标签。k=9 按同规则另发, 与 k=0 不同 ⇒ 列入矛盾, 标签取 k=0。单种子与「否」列对照仍不下词。RESULT 中任何「无差 / 不重要 / 相同」措辞只能引用本模块发出的标签。
- **红测(装置 `phase2/devices/p2_s2_relabel.py` 先跑, 不符即 exit 3、不出任何标签)**: 旧谓词 = 从 `p2_s2_lib.py`(c53f5c49…)按 AST 抽取的 `verdict` 原文。R1: 两种子 +0.20 [+0.10, +0.30] ⇒ 旧必须给「(C) indistinguishable (|Δg| < 0.23)」(复现误判), 新必须给「(A)」; R2: 两种子 +0.02 [−0.40, +0.44] ⇒ 旧「(C) indistinguishable」, 新「(C) INCONCLUSIVE」; R3: 两种子 +0.01 [−0.03, +0.04] ⇒ 新「(C) EQUIVALENT」; R4: 两种子 −0.30 [−0.50, −0.10] ⇒ 旧与新都「(B)」; R5: s42 +0.01 [−0.03, +0.04]、s2027 +0.30 [+0.10, +0.50] ⇒ 新「(C) INCONCLUSIVE」且 seed_conflict = True。另核模块自带测试文件 sha 与 `tests_equivalence_labels.py` 可导入。
- **输出**: `receipts/S2_TABLES_K2.json` / `.md`(每个判词格: 两种子点估计与 k0/k9 区间、k0 标签、k9 标签、敏感性 0.02/0.25 标签; 旧词只在 JSON 的 `superseded_old_rule` 字段留档)。标签「生产路径历史 combo 链未被 S1 认证 …」照 A7.3 带在表头。

## AMENDMENT 9 — 2026-09-13 16:3xZ〔时间勘误: 实际提交 7c0b1d0d 于 16:14:35Z, 头注时刻写错, 内容未改〕(P2 worker, lead 指示第 3 项): G2-B 原门在 P6-M 迁移上线后的复判计划 —— **只写不跑**
- **状态**: G2-B 原门 = NOT PASSED AS WRITTEN(RED, 收据 2), 标签永久保留; 本计划只增补, 不改阈值、不注销、不替换 G2-B″。**P6-M 未上线前不跑任何一步**; 上线的判据 = FX-PROD 的部署收据(工具文件 sha、实际施加的类别集合 {D17} 或 {D17, P9}、施加时刻 T_M、施加前后 aux sha)。
- **依据(引收据, 非新数字)**: 收据 2 在 09-05 16Z 的 73 个违例名分三类 —— (i) D17 5 名 PROM 2.603e-05 / ACE 4.80e-06 / DEXE 3.30e-06 / ERA 1.91e-06 / BANK 1.09e-06(live 账本「存储 iv ≠ 时间差 iv」行 79/67/152/137/103); (ii) 单行切换行 2 名 ESPORTS 5.86e-09 / 1000XEC 1.36e-09(各 1 行; FACT_TABLE_PROD 6.5: 这类行 zip 申报 = 存储值, 时间差才是错的); (iii) 基名单扩展 66 名, live 账本首行 07-26 08Z 冷启动, 1.02e-09 – 1.154e-07。全部违例在窗内按 HL 3d 精确衰减(比值到第 10 位)。P6-M(`REPORT_FX_PROD.md` §P6-M; FACT M.1–M.3, 9.6): 用存储标签的独立重建逐位复现 live EMA(525/525); D17 类 533 行 / 5 名的精确修正(09-13 12Z: PROM −4.096e-06 …), 修正后 = 用修正标签的重建(1.3e-18); P9 精确类 63 行(ONG 08-25 08Z 存 2.0 申报 4; 61 个 07-26 08Z 冷启动首行与 GRVT 07-31 12Z 存 8.0 申报 4), 影响 ≤ 3.7e-9。**G2-B 的重建标签规则 = 时间差吸附(生产 L341–349)**, 与 P6-M 的「申报间隔」规则在 (ii) 类行、ONG 行和冷启动首行上不同。
- **R0 确定性(先跑, 历史输入)**: 原装置 7766c7b3… 在原输入上逐字重跑 ⇒ 必须逐项复现收据 2(max 2.6026457179762646e-05 PROMUSDT @1788624000, 违例 2,163 对 / 73 名, 21,520 对, 参照 None 5 / MISMATCH 0)。不同 ⇒ 仪器或输入漂移, **停**。
- **R1 历史反事实(离线, 不读 live)**: 把实际部署的 P6-M 工具与类别集合施加到快照 1789200000 aux 的只读副本上作参照, 其余同 R0。约定 Δ = 重建 − 参照。**应当看到**:
  - (a) 恒等式: 对每个名、每个锚, Δ_R1 − Δ_R0 = 工具对该名修正量沿记录行按 HL 3d 回推到该锚的值(绝对差 ≤ 1e-15 或相对 ≤ 1e-12)。这一条说明迁移只改了标签的贡献。
  - (b) 类 (ii) 2 名(及 FACT 6.5 其余 5 个切换行名)Δ_R1 = Δ_R0 逐位相同 —— P6-M 不得「修」本来就对的行。
  - (c) D17 5 名在每个锚 |Δ_R1| < |Δ_R0|; 剩余量逐项用该名其余标签不一致行解释, 解释不了的 > 1e-12 ⇒ 报 FX-PROD。
  - (d) 冷启动 66 名: 若部署含 P9 类, Δ 变化只来自首行标签修正(09-05 16Z 处 ≤ 3.7e-9 / 0.1637 ≈ 2.3e-8); 冷启动起点残差保留(P6-M 不重设起点)。不含 P9 类 ⇒ 逐位不变。
  - (e) 若部署含 P9 类: **ONG 与 GRVT 会新出现差异**(G2-B 重建仍按时间差 / 首行 8.0 标注, 而 live 改为申报 4), ONG 在 09-05 16Z 约 2e-7(FACT 6.7 的 6.0e-7@09-01 00Z 按 HL 3d 衰减)。这是预期结果, 不是缺陷。
  - (f) R1 在 1e-9 下**预期仍 RED**: 仅 (iii) 类起点残差最大 1.154e-07 就超门。
  - **不应当看到**: 上述集合({D17 5 名} ∪ {类 (ii) 7 名} ∪ {冷启动 66 名} ∪ 部署含 P9 时的 {ONG, GRVT})以外任何名新出现 > 1e-9 ⇒ 迁移改了声明类别以外的行 ⇒ **停**, 报 FX-PROD(可能是生产缺陷); R1 转绿 ⇒ 与 (f) 矛盾 ⇒ **停**, 查参照或重建是否被悄悄换了。
- **R2 上线后窗口(读 T_M 之后的生产者快照, 只读)**: 参照 = 首个 41 个重叠锚全在 T_M 之后的快照; 重建与阈值同原门; 另跑端口自检。**应当看到**: (a) 若 P9 追加路径未部署, T_M 之后追加行按时间差重算 iv 与存储 iv 0 不符; 若 P9 已部署, 不符行恰为「申报 ≠ 时间差」的行(切换行、冷启动首行), 逐行对上 P9 申报间隔表; 此时原 G2-B 重建已不是生产的移植, R2 读数只报不判, 需另立具名门(按申报标签重建), 另行预注册; (b) 每个名窗内末/首比 = HL 3d 理论衰减(10 位), 除逐项列出的窗内标签不一致名外无窗内发散; (c) 每个名窗首 |Δ| ≤ R1 同名 |Δ(1788624000)| × 0.5^((A − 1788624000)/259200) + 1e-12(基于同一类别集合)。**不应当看到**: 超出 (c) 投影的名(⇒ D17 / P9 / 冷启动之外还有东西, 停并报); 早于投影日期转绿 —— 最早可转绿锚 = 使 max_name |Δ_R1(1788624000)| × 0.5^((A − 1788624000)/259200) ≤ 1e-9 的首个锚(仅冷启动类即 ≥ 2026-09-26 05Z; 若 ONG 新差 ~2e-7 则 ≥ 09-28 14Z; D17 剩余量由 R1 测得后照式计算)。
- **不主张**: 衰减导致的转绿不是修复, 也不认证 live 资金费 EMA; R1 / R2 不认证 S2 历史资金费臂(S2 用干净重建, 窗内递推由 G2-B″ PASS 覆盖); 09-05 → 09-12 窗的 G2-B RED 永久保留。逐名数值投影的装置在 FX-PROD 给出部署类别集合与 T_M 之后、R1 之前提交; 本修订冻结上面的定性预言、恒等式与转绿日期公式。

## AMENDMENT 10 — 2026-09-13 16:2xZ(P2 worker, lead「dead contracts」指示): S2 偏差表增补 D21 死合约 —— 不重跑 S2
- **D21 死合约(AUDIT_DATA bb8a2806: TRD-01 / TRD-02 / TRD-03)**, 与 D1–D20 同列, 数字全部引自该审计的收据 `docs/audit_pipeline_2026-09-13/devices_data/receipts/AD_H_tradability.json`(非本 worker 新测):
  - **TRD-01**: 研究侧没有按成交的可交易性; 规范 5m 缓存里 156 个死合约写有 13,770,575 行冻结行(ret5 恰为 0), 其中 60 个仍有资金费记录(60,438 次)。S2 历史链读的就是这份缓存。
  - **TRD-02(S2 直接受影响)**: P2 的基名单代理(D3: (A−24h, A] 有结算即算 TRADING)含死名, 每锚平均 **1.4 / 6.5 / 15.8 / 17.6 / 4.4** 个(最多 5 / 8 / 26 / 41 / 10), 基名单规模 145 / 199 / 296 / 464 / 597(2022 → 2026; H5.P2_base_proxy_on_king_axis)。在役名之间相对顺序不变, 但秩位置、fund z 水平与去均值权重会移动; **书层影响未测, 方向未测**。
  - **TRD-03**: A0 轴上持有的死合约格每年 58 / 33 / 220 / 290 / 134 个, |W| 占全年份额 2.5e-4 / 8.3e-5 / 4.9e-4 / 3.6e-4 / 2.6e-4, 记账收益恰为 0, 记上的 carry 合计 +1.68 / −0.45 / +0.51 / +2.24 / +3.54 bps(s42)—— 审计标 VERIFIED_IMMATERIAL。**P2 各臂(全 829 模式)持有的死合约格未测。**
  - **处理**: 按 lead 指示**不静默重跑 S2**; S2 读数继续带「未认证」标签, D21 进偏差表。以后的认证回放消费 FX-DATA 可交易性模块 `multi_asset/exports/research/common/tradability.py`(提交 8ab0d769, 文件 sha256 a9fad82c…; 构建产物收据落地后另钉 sha)。
  - **生产窗口内(本 worker 的归因收据, `PREREG_combo_chain_residual_attribution_2026-09-13.md` Stage B / C)**: 09-05 16Z → 09-12 08Z 的 41 个生产锚上, 在役 450 名中的死名每锚 2 个(SCRTUSDT、STORJUSDT; 规则 = (A−24h, A] 无一根 5m log_cnt > 0), **41/41 锚不在 king 成员集(= F10 打分截面)里, 也不在 target_live 里**(`ATTR_stageB.json` 3eb958c1…); 三个快照锚上把这两个名整列置 NaN, king / target_combo / target_live 与 state_H 全部逐位不变(`ATTR_stageC.json` d4c4625b…)⇒ 生产窗口内死名不触及 F10 截面。这一条**不外推**到 2022–2025 历史(那里基名单代理的污染更大, 见 TRD-02)。

## 收据 9 – 14 · S2(2026-09-13 11:4xZ → 15:4xZ, pod2 CPU; 全部「未认证」, 只作信息)
**LABEL: 生产路径历史 combo 链未被 S1 认证: king 连续 41/41 与 3 个快照起步锚通过, 连续 combo 历史链不通过(0/41 @ 1e-6, 最大 1.12547e-4); S2 不是「生产路径平价已通过」。** 归因与认证见 `docs/PREREG_combo_chain_residual_attribution_2026-09-13.md`(进行中); 在其 Stage D 判定前本标签不变。
- **收据 9 · S2 门(运行前)**: `receipts/s2/S2_GATES.json` e4e07c22…: S2_FN / S2_P_acc(最坏 8.611e-06 bps)/ S2_BOOT / S2_DSR / S2_OVL_RED 全 PASS, S2_BOOT_iii 非阻断 PASS, rc=0。`S2_R18_runner.json` 0176edb7…: GATE_S2_P_NW PASS, NWrepro rc [0,0], A1NW rc [0,0], rc=0。
- **收据 10 · S2 链**: `S2_LAUNCH.json` 37486b67…: 六臂(v4 s42 / s2027, A0pred s42 / s2027, v4 s42 serveall, v4 s42 pins)全部 rc=0、各 10,039 条记录, 驱动 dc4e6c85…。首次冒烟 5/6 臂 rc=1(子进程重设 stdout 关闭 fd 1), 修为只 dup2(250f1858), 失败件留档 `*.attempt1_fdclose.*`。逐臂收据 `RUN_S2_*.json.gz` 与日志已提交; `.vec.npz` 留 pod2(sha 见 `SHA256SUMS_pod2_S2_2026-09-13.txt` 7b1310f1…, 107 条)。
- **收据 11 · S2 因果审计**: `S2_causality_audit.json` 1e086980…: 六臂 PASS, 违例 0, 失配 0, rc=0(pins 臂 king 扣留 543)。
- **收据 12 · G2-C-BIND**(AMENDMENT 7): `G2C_BIND.json` c0aca587…: 真实束 PASS(0 失败), 6/6 变异件 RED 且各自具名原因, 真实收据未改, king 链 41/41 ≤ 1e-6, rc=0。前两次运行留档: attempt1(SHA256SUMS 用仓库相对名 ⇒ 核对空转)、attempt2(该清单存 16 位前缀 ⇒ RED); 修正后第 3 次 PASS。
- **收据 13 · D20 成员探针**: `S2_D20_member_probe.json` 86e66523…: 导出器成员集中前向标签非有限的格 2022–2026 均为 0(研究侧对照 2,342 / 130 / 1,245 / 249 / 189)⇒ SLOW_v4 上 D20 丢格量 = 0, 偏向说明见 AMENDMENT 7, rc=0。
- **收据 14 · S2 表**: `S2_TABLES.json` 2f3c67f6… / `.md` 800492eb…(series 34, contrasts 50, rc=0; 15:09–15:11Z 按 A6.7 旧判词出表, 数不依赖判词)→ 判词按 AMENDMENT 8 改用 K2 标签: `S2_TABLES_K2.json` 10c98387…(模块自检 84/84, 红测 5/5, 36 格全部 **(C) INCONCLUSIVE**, k9 矛盾 0, rc=0)。书层(W_ALPHA, g = net_ex / gross_total): P2a-v4 CMB STOP s42 +0.6710(Sharpe 1.359, CI95 k0 [+0.196, +1.153]); A0_d30 s42 +0.6342; K1 W_ALPHA Δg +0.0714 [−0.1016, +0.2464] / s2027 +0.0461; M1 −0.0095 / −0.0009。W_FULL s42 CMB STOP Sharpe 1.096, DSR: N_eff 下 P(SR>0) 0.967, N=300 下 0.325(按 N 假设的插值读数, 不是校准概率)。2× 复利 maxDD W_ALPHA CMB STOP s42 −36.15%。偏差表 D1–D21(D21 见 AMENDMENT 10)。**不主张任何书行为改动; 不注销任何 FAIL / RED。**

## AMENDMENT 11 — 2026-09-13 17:1xZ(P2 worker): 连续 combo 历史链标签增补一行(原行保留)
- 原标签「生产路径历史 combo 链未被 S1 认证: king 连续 41/41 与 3 个快照起步锚通过, 连续 combo 历史链不通过(0/41 @ 1e-6, 最大 1.12547e-4)」**逐字保留**, 其后增补: **「增补门 G2-C-ASOF = PASS(2026-09-13, `phase2/receipts/ATTR_stageD.json` 10b30695…): 回放逐锚喂「11,520 行以 A 结尾」的缓存后, 41/41 锚 target_live 与 target_combo 精确 0.0、king ≤ 9.3e-10; 原 0/41 残差归因为回放装置的缓存左边界缺陷, 不是生产侧伪迹(归因预注册 `docs/PREREG_combo_chain_residual_attribution_2026-09-13.md` 结果节)。认证范围 = 09-05 16Z → 09-12 08Z 的 41 锚、pod2 拼接缓存, 07-27 16:05Z → 08-03 08:00Z 的 1,920 行未与生产文件对照。」**
- S2: H-d 不作用于 S2 的 F10 分数路径(I2 注入下 171 管线从未运行, `ATTR_s2_pipeline_skip.json`)。S2 读数的「未认证 / 只作信息」标签**本 worker 不改**, 等 lead 裁定; 任何情况下都不写「生产路径平价已通过」。
