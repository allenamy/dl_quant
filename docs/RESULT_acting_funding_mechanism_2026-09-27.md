> **创建:** 2026-09-27 16:06:26 UTC | **Session:** acting_lead/funding_mechanism_0927 | **状态:** final | **作废条件:** 冻结输入SHA改变；同人口/执行钟闭合被反证；不能把本文的描述性或局部梯度读数升级为策略许可

# 资金费腿机制：独立测量与可执行下一步

冻结研究仓为 `3b4a2815ad4b8d45ee09ed8b69222e04b5885301`。只读生产snapshot/现金簿、pod2既有产物；独立CPU单线程，峰值约1.0GiB；没有交易所请求、凭证读取、生产写、GPU、模型训练或新候选回测。三个独立测量先后冻结在 `PREREG_acting_funding_diagnostic_2026-09-27.md`、`PREREG_acting_funding_recent_2026-09-27.md`、`PREREG_acting_funding_gradient_2026-09-27.md`。本报告交代理主研究员 `/root`，不写共享STATE/registry。

**结论：近期亏损不能据此诊断为重大模型bug。** 对“资金费特征EMA三天迟滞”已有否定证据的说法过强：原no_ema干预的是仓位EMA。我们新测的窄迟滞群在已知12区间内负担很小，不能解释主要空头亏损；历史条件效应不确定，MDE尚不能排除小贡献。反动量负载变号/共同残差暴露更值得继续量化，但相关性不是归因干预。F10损失确实不含实际carry，其连续梯度不能被King KN秩IC失败自动否定；本次计算同时发现执行钟未闭合，因此**经济训练仍不启动**。

## 1. 三类机制的排除范围

| 机制 | 已经排除/确认的范围 | 尚未排除的范围 |
|---|---|---|
| 特征EMA三天迟滞 | 主研究员Q1是`fe_v`；旧no_ema实际去仓位EMA+deadband，不是Q1干预。新12区间窄定义迟滞组只占gross 4.006%，价格−65.85美元，不能承担该窗全部短侧−7197.46美元 | EMA的经济失效、其他恢复状态、其他月份、前向窗口；历史条件IC无法排除0.005级别效应 |
| 共同行情暴露 | 资金费源不是始终反动量：k7载荷Jan–Jul +.020、Aug +.007、Sep1–18 −.013、live Sep19–26 −.04097；King−.09435，F10−.00981。最近执行差额约−20.2美元，主要损失在目标书，不是成交质量 | 共同残差因子、动量反转与持仓漂移的因果份额；原始目标净短已被执行中性化，不能再用“净短偏置”解释 |
| 训练/服务或账本错配 | NC EMA在同规则、同事件账2,742,554成员格bitwise；第二机制30,242实质EMA差异全来自间隔规则，非笼统污染。D10 cut后伪影修正使联合臂2026 +2.24降至+.67 bps/day | 同规则一致≠经济有效。F10价格标签/效用窗口与真实约A+24m决策、各笔t_dec+tau填单不同；新carry训练若忽略该时钟将引入反事实避费 |

来源：`RESULT_ema_channel_attribution_and_truth_2026-09-26.md`、`RESULT_ema_second_mechanism_2026-09-26.md`、`RESULT_dlarch_momentum_loading_2026-09-27.md`、`RESULT_drawdown_attribution_0916_0926_2026-09-26.md`、`VERDICT_D10_joint_arm_book_gate_2026-09-27.md`。

RN8去夹子2026两个种子价格提高约.857/.922 bps/锚，同时多付1.104/1.106 bps资金费，净额负；保留夹子。S1低IC和sigma失败不等于零信息：0.005–.010正残差IC仍可能是真弱信号，只未过既定门。D10联合臂仍UNDECIDED、s42前段回撤加深3.33pp；只换资金费特征的line D也没有提供换装许可。

## 2. 独立历史同人口测量（不是EMA干预）

读干净L2N s42/s2027已有数据；限定持有NC空头、fund席位>0、fund_z<0、W24H可交易。每锚用 `rank(RN8)-rank(FZ)` 的条件残差，控制FZ/King/过去3日收益排名；分别对后4小时原收益/收益rank作部分Pearson。日内锚等权、日等权；30日循环块2000次，种子20260927；两年代，双种子共享行情，不能视作独立四次重复。

| 人口 | partial Pearson [95%] | partial rank-Pearson [95%] |
|---|---:|---:|
| s42 pre2026 | −.00059 [−.00660,.00569] | .00183 [−.00455,.00889] |
| s42 2026 | .00278 [−.00406,.01036] | .00164 [−.00571,.01029] |
| s2027 pre2026 | .00059 [−.00546,.00671] | .00269 [−.00369,.00982] |
| s2027 2026 | .00253 [−.00439,.01039] | .00153 [−.00596,.01020] |

没有丢弃锚；约69万名锚/种子。见数前正控植入+.015、负控0都被仪器识别，但这只是统计装置校准。**实际MDE约.009–.011，不足排除.005，也完全没有九月样本**（末人口2026-08-30 20Z）。判词NOT_ESTABLISHED。运行8.016秒，RSS249,408KB。首跑numpy.bool序列化失败、计算已发生；只修输出转换后复跑，披露在预注册；不伪称后一次是首次见计算。

## 3. 近期生产人口闭合（已知窗，严格描述性）

固定NAMES `4e84c8dd…`全部12个priced区间，Sep24 12Z→Sep26 08Z。以实际L5 notional<0出发，加入同锚aux的fund_z、feature EMA、RN8、King、rev24，以及同源BTC收益和beta。真实funding现金按结算时持有方向单列，不把静态价格归因与动态资金费硬拼NAV。

L组定义：EMA<0、fund_z≤−.25、当前RN8<0，且RN8≥EMA/2；C组为同一极端群但RN8<EMA/2。全部1957名锚，负RN8方向188名锚；L49、C69、其他1839，无未知。L gross 52,403.80 / 全短侧1,308,035.28=4.006%；L price−65.85、BTC项−8.30、残差−57.55美元；实际资金费净现金−9.84美元（付10.54、收.70）。C price−170.79、残差−136.24、资金费现金−82.67美元。其他组承担price−6960.83、残差−6491.76美元。

固定同锚caliper匹配20对/11区间，覆盖L gross 42.98%；L相对C的名义加权空头残差差 **+5.684bps**（L更好）。这只是小样本描述，不是因果估计、OOS、策略优化或整月归因，不能据此取消EMA研究。

闭合按实际来源精度：SIDE_SPLIT金额round2、BTC收益round5；同NAMES未舍入BTC用于计算，整书L5对LAYERED_BOOK仍1e-6；+0.01美元红控必须失败。失败两次锚键格式、一次把rounded receipt当全精度比较，日志保留；修订发生在首锚整体价格已见、分组/匹配未见。没有放宽人口/caliper/窗口或匹配门。

## 4. F10 carry：数学梯度存在，经济时钟未闭合

现役loss为 `net=1e4 Σnew*y4s−3.52 Σsqrt((new-held)^2+1e-12)`，再取 `−mean(net)+.25*ES5%(−net)`。实际carry不在loss内；资金费特征进utility并不等于支付成本被惩罚。King KN失败只针对rank目标，不能替连续净效用/尾部梯度作判词。

本次原utility、原WL、tau=.3、已有s42 OOF分数，固定pre2026/2026各4个120锚span，burn24，alpha为对应fold最终值，保留held递推与ES完整计算图。读取D10延长毫秒账 `76b777bf…`，逐事件求F(A,A+4h]，单CPU7.77秒、RSS1,027,284KB。carry/price的score梯度norm中位 **9.89%**，carry/turnover **12.38倍**；加入carry后总loss梯度变化/L0为 **1.37%–42.96%**。八组F=0逐位恒等、F反号精确、同率中性、负carry方向有限差分全部通过（最大相对误差1.84%）。它证明当前分数附近的**抽象效用图**有非零方向，不是网络参数梯度，更不是可泛化收益。单位是utility名义归一化bps，不含GM=2，不能叫NAV bps。

**这个读数不能发经济训练。** 主审指出真实决策约A+24m，填单在各自t_dec+tau（旧历史适配器才使用A+25m网格近似）。new(A)承担A+1ms刚结算的资金费，是让模型事后避开它来不及避开的付款。正确量是结算事件当时的 `q(t−)*P(t)*rate`；不能直接把目标权重w乘F当作等价。原JSON的LOCAL_DIRECTION_WORTH_TWO_ARM_TEST保存为数学原始读数，当前经济解释为 **UNAVAILABLE_TIMING_NOT_CLOSED**。

独立第二装置将1,497,091变化格完整拆成：

- 同轴10212锚×829名称。旧T_NET与旧P2原始费率和**逐位相同**，不是RN8比例化或符号映射错误。
- A端(0,1s)的新纳入与A+4h端(0,1s)的移出引起1,497,097格变化；左端非零1,018,513、右端1,018,960、两端均非零350,573。
- 同秒额外18笔导致18格事件集差异，与边界项部分抵消后总差1,497,091；恒等误差4.27e−16。新增九月事件不进冻结covered窗。
- BTC 2022-01-03 00:00:00.010的1bp：旧秒账把它归前锚20Z；朴素ms片段把它归00Z。两种表示不能决定当时持有数量；00Z新目标的约24m决策及之后逐笔交易尚未发生。这不是“149万格数据污染”。

原边界JSON中的 `prefix_collapsed_error:0` 是初始化未更新字段，**不是测量**，不得引用；有效闭合是old_label_error=0和decomposition_error=4.27e−16。保留原件而不回写假装不存在。

需严格区分三层：旧P2秒级F（旧目标近似）、D10毫秒朴素F（事件分片真但目标承担可错）、真实持仓事件钟cash（可交易、需q与结算价）。旧`r_hist_sim.py`历史适配器描述决策24m→25m网格，但当前`exec_sim.py` v3.1按记录t_dec及各笔tau调度fill，PRI funding=2、fill=3，on_funding用当时self.q和floor_b价格。下一步绑定当前版本与实际cfg，不能改成“24分钟或25分钟统一换仓”。

## 5. 最便宜的可证伪两臂协议（交/root复核，未启动）

先CPU同钟门，再短训练；不由本次梯度门直接放行。

1. 固定上述8个span和已有分数/King/资金费席位、NC chain、执行参数。从既有engine导出事件序列/持有数量/settlement px/cash，不重写费率或执行时间。单核≤2GiB，MB输出；每一资金费事件必须能追到前一持有数量。明确实现当前span起点held来自burn路径，不凭空清空真实book。分清fill前/后、同刻优先级和5m价格插值。
2. 可微替身只在已经过独立同钟核验的范围参与训练。对同一target路径逐事件现金与全书引擎校准；F=0时两臂loss/梯度/参数逐位相同。负控把A+1ms收费错误归给new，必须在合成例和真实BTC例报红；正控在可达fill后植入一笔费，梯度必须抵达相应持有而非前一段；金额控制用q*settlement price，不能只验证ΣF。
3. 两臂共用同一合法price窗口/换手/held递推/King混合、同初始化、同shuffle、同tau、同epoch和输入：A0为现有无carry损失形式；A1仅加上述**事件时持有**实际carry。若为同钟必须改变原price标签，则两臂共同改变，并明确A0不再是原NC逐位复现；保留NC全书参照才能解释差异。不能偷偷把“price时钟+carry”两变量称仅加carry。
4. 首轮固定s42、一个202608 fold、一epoch，仅作实现/网络参数可达性冒烟，不据一折P/S或收益判有效。不变的验证窗、模型和数据；至少报告参数梯度carry/price/turn比例、Δloss、alpha、σ比、原收益P/S与rankIC，检查无可达干预时两臂应同。通过后由/root冻结多fold、多seed验证，不搜carry系数或截止窗。
5. 必须保留完整King+F10+fund book通过既有chain与32路径执行账，报告price/carry/cost/unknown闭合、对NC及共同A0的日差，历史多regime和既定MDE；不拿独立F10腿净额代替整书。当前F10书层MDE约1.87bps/day说明小额收益仍可能不可判。

成本：现有202608 fold八epoch180.4秒，单epoch22.2–23.2秒；两臂一epoch计算量约45–60 GPU秒，再加恒等/负控预计<3 GPU分钟（**外推，尚未测同钟算子**）。原NEWS_FEATURES压缩2.96GB、训练全量特征拼接约GB级，当前≤2GiB预算不能直接调用原trainer；先做小包/实测内存，具体GPU/RSS预算由/root安排。CPU同钟小窗探针先预算单核5分钟/2GiB/≤10MB；完整32路径整书与轻量Ridge/LGBM重建需先实测输入展开内存和一窗口耗时，当前不报未经验证的全量CPU时数，资源门后排且让KSR/D10优先。全23折3seed约2.8–3.0GPU小时仅是后续上限参考，本次不申请或启动。

## 6. T2既有输出的零GPU复用审计

`/workspace/dlarch_2026-09-24/out_pgret/T2_RESIDUAL_PREDS.npz`实测存在36,377,336字节，SHA `bcc7a9bd3b58b648bfaa4c5b055c5c4aa5e558d4b0f37e67586a5bcbbd7318c5`；ridge/lgbm/residual_target均10333×829，有anchors/symbols。对应PREGATES.json `b883068f…`绑定NC NEWS_FEATURES `3c886a2b…`、target `ca479fcc…`、KING_OOF `a10b8725…`，不是已弃用旧news树，也不是D10新特征。

年折2023/24/25/26；2026所有月沿同一个2026年折模型，60锚embargo，训练label最晚2025-12-22 00Z，训练2,134,630对、测试626,800对。不能误称月度更新或用2026见数选择Ridge/LGBM。已有`dlarch_t2_pregate_2026.py`复用continuous_combo.evolve，并以归档F10正控验证kc/fc/raw/weights/trade_mask五数组全bitwise；所以从已有预测接整书原则上无GPU需求。但原装置把预测NaN直接补0，新桥必须具名审计覆盖/hold规则，不能继承静默补0。

收益单位版2026 IC是Ridge .01838 [下界.01278]、LGBM .01188 [下界.00666]，不可混用秩残差 .051/.055。原T2“混合书损失”与这里CPU残差标签也不是同一机制。执行source SHA `9185482b…`与仓中一般版不同，现已从实际probe路径独立归档且哈希逐位核同，附逐月source/finite-score审计；正式候选判词前需钉实际probe源码、逐月输入身份/训练隔离和全书同钟，不能仅凭旧门宣称所有来源已闭合。NC服务一致输入仍可能含D10拟修的间隔近似，不能称最新正确资金费数据；纯桥接正控可复用这些预测，但新增候选收益必须以纠正后的共同输入重建轻量Ridge/LGBM及其完整书基线。

## 7. 交付与局限

独立证据在 `multi_asset/exports/research/acting_lead_20260927/funding/`：历史/近期/梯度结果、失败日志、毫秒差异分解、手读事件、T2复用审计与源装置；原tmp保留。报告源在 `/Users/haosiyu/.codex/tmp/acting_lead_20260927/funding_mechanism.md`。

未测：9月OOS特征EMA干预、真实网络参数梯度、事件时持有的可微cash与全书平价、新训练或候选完整净收益。主审已独立纠正执行钟，故最值钱的新结论不是“该训F10-N”，而是**不能因KN秩门拒绝它，也不能用错误归属的carry去训练它**。

## 8. 主审追加后的最小同钟探针（2026-09-27 16:13:10 UTC，尚未运行）

旧P2秒级(A,B]可能把B+几毫秒的整点结算归给前锚，这恰可能接近A约24m→B约24m真实持有期，不能定性为“旧秒错误、新ms正确”。**事件真值×执行可达时钟**共同定义现金目标。当前exec_sim.on_funding按`int(t)`查率，旧HistFunding/RateMap也使用整数秒；直接接ms事件会使同秒不同笔覆盖/混同，因此适配器本身还需额外门。

资源最小的第一包只做输入与时钟合同，预算1核、≤2GiB、≤5分钟、≤10MB，先不跑模型也不读2.96GB特征：

- 固定原八span、同scores与alpha，不增加样本选择自由度；读取当前exec_sim实际cfg.t_dec、各笔校准tau与既有价格表，只切需要的floor5m价、原始rate及固定目标。price表若不包含实际决策/逐fill所需bar则UNAVAILABLE，不沿用旧A+25m样本表或补未来价。
- 第一小门用合成A+10ms结算、t_dec前后两次partial fill、同刻fund-before-fill，以及真实BTC例；分别用旧canonical秒队列和独立毫秒事件手账计算q(t−)*P(floor_b(t))*rate。旧源必须逐笔复现canonical，新源必须每个(symbol,ft_ms)恰记一次。故意令new回溯承担A+10ms、按秒覆盖18笔之一，两个负控都应红。
- 同一权重路径并列报告三者：旧P2(A,B]、朴素ms(A,B]、可达事件时持有现金。**同钟price亦由同一数量/成交/标价序列重导**，不得拿y4s和延后F拼合。若仅做理想化(A+24m,B+24m]片段，单列为第四个“延迟瞬时换仓代理”，绝不命名actual；主量仍是逐fill执行钟。
- 通过金额闭合后才对同clock损失作同score局部导数/有限差分。原八span的price梯度、carry梯度和ES尾部都重新计算，不复用旧梯度分母。若源码adapter、price覆盖、q路径或输入身份任何一项不闭合，停在测量不可得，不用原始9.9%推进。

以上包只量仪器，完整书验证仍保留King、fund席位、F10、链、GM、执行费用、保护逻辑；不能用独立F10证明候选。CPU扩窗和两臂GPU烟测在资源门后排，由/root核协议后执行，不抢KSR/D10。

## 9. 最小控制已执行、条件训练未启动（2026-09-27 16:19:24 UTC起；输入缺失判断已被§10作废）

预注册及装置提交a19e3a725。直接提取当前v3 `on_funding/push/step_until/PRI`，只用固定fill夹具：三笔现金−.10,+.48,−.495美元，合计−.115；new-fill幅度导数−.09美元/单位幅度，有限差分误差<1e−9。F=0和反号通过，回溯给new、同刻fill先于funding、ms两笔强接int键均报红。收据`funding_cash_clock_result.json`，只判IMPLEMENTATION_CONTROL_PASS。按秒字典的风险只是**本次ms接入风险**；未查明现役消费者有真实重复扣费，不能由旧文件推翻已有引擎结论。

**当时报告的数据阻塞（定位不充分，已解除，见§10）**：仓内v3 seed02完整window金额在，但INPUT_MANIFEST原镜像`.../scratchpad/replay_exec_mirror`本地不存在；pod2`/workspace/replay_exec_2026-09-19`也不存在。pod2 R/work/exec_mirror只有filters和executor tree，没有pilot_log或producer，不能据它复现v3逐fill路径。实际live funding记录的position_notional来自旧position_read_ts，首条示例读数落后838秒，所以现成notional×rate不能当独立实时q×P真值校验。所需最小恢复物是**某个已经认证的固定路径初始state、trade_log、fund_log、结算price来源及其源码/calibration SHA**；或者找回同版本mirror，再由原引擎只读导出。无需重写模拟器，亦无需可微替身复现全部非线性撮合。

16:15资源预检：GPU约32GiB总量、仅2MiB使用、util0；cgroup max60,999,999,488/current45,907,533,824字节，余量刚超过6GiB+8GiB；同UID RSS约15.69GiB，加6GiB小于30GiB。这只是当刻快照，真实启动必须重检。已授权两臂CPU1/RSS6GiB/GPU8GiB，但实际现金输入门未闭合，**没有启动GPU或训练**。预测两臂一epoch45–60GPU秒、端到端≤8分钟；本轮最多15分钟wall，不以余量逼近而绕过缺失输入。NC旧输入若用只可标实现测试；候选需D10正确共同输入。

## 10. 持久镜像找到，认证模拟路径真实cash门已完成（16:43:38–40Z）

前轮只核原scratchpad即判缺失，定位不完整；本轮按主审要求继续搜索，找到仓内`MIRROR_DURABLE_COPIES_2026-09-19.json`，明确原镜像已持久化到本地`/Users/haosiyu/quant_mirrors/replay_exec_mirror_59875e5a`与pod2`/workspace/replay_exec_mirror_59875e5a`，现时两处均存在。本次实际用本地副本，不读取实时生产树，也不重新拼历史镜像。§9缺失判断作废，失败过程保留。

预注册及装置先提交4ff3f9a7c，定点核验manifest505/505输入（257,175,687字节）、332个executor源码；v3.1 `29679672…`、calibration `fda34243…`、seed02、live模式全固定。只重跑原认证CAL路径前6窗，初始sealed SHA一致，窗口所有数字对已存参考最大差1.46e−11美元。不是新窗口或新策略，也没有复跑全史。

独立现金：从initial_state数量出发，按严格先于结算的4,930笔原引擎实际fill增减重建q；以固定价格panel与FundingBook费率重算1,083笔结算。最大q差1.46e−11、现金差1.67e−16美元，6窗各自闭合≤1e−8美元。六窗现金为−4.2290228482、−4.4467628684、−2.8079652984、0、0、−4.3521065793。源码/镜像/独立数量路径与原认证参考共同闭合，不是仅将fund_log的q乘其自报rate作同式自证。价格来源仍是canonical panel，**不是另一个独立price oracle**；这里的“真实路径”指已认证执行模拟的事件路径，不冒称逐笔venue成交真值。

同钟线性通路：按时间第一笔具有后续结算的真实fill是1000BONK，t=1787718198.759，334.8单位；对这笔增量q、保持后续已执行成交不变，carry导数−8.4650768783e−8美元/数量，独立现金有限差分−8.4652285182e−8，fill前导数0。相同fill price到窗尾的价格导数1.8146030902e−6美元/数量。它证明**可达后的old-held/new-fill线性carry通路**，不包含未来止损/重规划反馈，不推成171维网络参数梯度或收益。另附原事件流里“同锚先fund、后fill”的可读例，展示把当前fill回溯收费的红控。

耗时2.009秒、CPU1、Mac ru_maxrss=1,119,830,016字节（约1.043GiB）。完整初始state、trade_log、fund_log、独立cash导出1.14MB，均留在独立证据根；零GPU、零远端写。最新授权已明确旧GPU额度不延长，因此本轮以**FIXED_CANONICAL_PATH_CASH_PASS**交付，不自启训练。下一步可在此事件钟基础上冻结因果可达carry代理与同钟价格两臂；无需再恢复镜像或重写模拟器。


## 11. 新授权的网络夹具与完整fold方案（17:06:30Z资源门仍红）

主审在§10交付后重新授权两臂同初始化、一epoch，并同意收窄为认证六窗网络夹具。预注册53b61495f、实现1e0d18276及后续身份/守卫加强6c1f9e8f3。原§10“不自启”是当时旧授权过期的记录，不代表拒绝本次新授权。

六窗属于原202608 OOF时段，因此在其上优化只测网络参数通路；不得输出候选/OOS结论。以实际fill的名义份额把网络目标相对同初始化目标的差映射到数量扰动；初始held与保护flatten冻结。价格从真实fill到各窗边界标价，fee在fill所属窗、cash只在严格晚于fill的结算收取。共同A0/A1均改变旧y4s时钟，只有reachable carry项在两臂之间不同。F=0的参数及AdamW状态逐位恒等、提前收费红控、fill前梯度0和完整现金FD均列硬门。不能声称新目标在模拟器会产生固定tape的同样成交。

**代码复查补充（未见新读数）**：§10现金逐笔/逐窗基准闭合仍成立，但其局部导数只枚举fund_log；baseline q=0时引擎可能省略结算，新增数量的导数不能据此也省略。新装置枚举原FundingBook全部事件（包含q=0）并独立有限差分；旧−8.465e−8导数暂限定为“已记录fund事件上的扰动”，不可当完整后续现金导数。待资源门通过后报告补齐差异，保留原读数。

Pod部署根为`/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding/network_fixture_20260927`，stored-NPZ只读mmap目标row，不复制全量特征。17:06:30Z门：cgroup max60,999,999,488/current46,052,999,168，余量14,947,000,320 bytes，仍低于14GiB的15,032,385,536；同UID RSS13,717,983,232 bytes，GPU2MiB/util0。没有因为差85MB降门；未启动GPU或训练、未开始15分钟额度。每轮失败门已归档，停止60秒轮询，等待现有作业/主审释放资源后5–10分钟级重查。守卫只停止自己的PGID，首次通过后单一15分钟预算跨重试保持。

完整fold最小方案另见`PLAN_acting_funding_fold_clock_2026-09-27.md`（8b5fe0f58）：已定位原始价全网格23af32bd…、meta d1e49cc9…、历史CfgMap31/逐fill offset、D10真实ledger76b777…与已归档共同特征ad80d50d…，先120锚mmap小包校准，不需要重新寻找历史实盘全tape。新候选必须等待D10共同输入验收，保留NC参照，通过完整King+F10+fund书、32执行路径和UNKNOWN人口评价。第一span预算CPU1/2GiB/5分钟；整fold两臂一epoch预计45–120 GPU秒但尚未实测，完整训练/整书资源另排；未自动延长本轮范围。

17:11:54Z按约5分钟重查仍红：余量14,897,160,192 bytes<14GiB，同UID RSS16,806,248,448 bytes，GPU2MiB/util0；仍未启动任何GPU/训练。代码、预注册、实际失败资源收据和单次续跑命令均已归档，等待资源释放，无后台高频轮询。
