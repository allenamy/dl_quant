> **创建:** 2026-09-27 15:38 UTC | **Session:** Codex root / acting-lead-20260927 | **状态:** in-progress | **作废条件:** 用户停止、主研究员接回或 2026-10-01T00:00+08:00；引用的版本变化时重新核验

# 代理主研究员执行台账

用户已授权从现在至主研究员 9 月 30 日接回，接替推进实盘稳定、修复发布、研究和完整组合优化，不以仅提交复审件结题。工作树 `/Users/haosiyu/.codex/worktrees/acting-lead-20260927/quant_research`，分支 `codex/acting-lead-20260927`；起点 `3b4a2815ad4b8d45ee09ed8b69222e04b5885301`。生产位置仍为 `~/wide_shadow` 与 `~/dl_quant_live`，写工作树即上线；准备修改必须在隔离树。主仓别人的未跟踪/运行数据不改。

## 当前事实与边界
- 15:37Z 运行树实测为 d01e35d；代码区未发现变化，运行 state 正常变化。arm64。launchd 相关作业已加载，尚不能以此证明16Z锚正常。
- 交接记载13:01Z恢复、16Z首锚；未将交接代替独立验收。用户暂缓密钥轮换、K1只查16Z/20Z/09-28 00Z三锚，保留该约束。
- 首锚及三个恢复锚：先 inspect_anchor 和本地证据；等 anchor done 后验收。场所只读核验使用白名单装置，在静默窗 [N+1:00,N+3:40] 内。不得自动resume；未知外来订单/再跳闸立刻报告。
- CFG04/06仍盲；只读合池量。凭据值不打印。安全电池只经 offline wrapper，发布只经safe_commit；锚窗不本地重活。无名字kill。
- 资金费源、模型、目标、缓存、发布门与统计窗口逐级绑定sha；不将旧模型换名当成重训，不把IC提升当整书提升，不把UNDECIDED当不劣。
- D10三种子最新描述性重读为+0.67 bps/日(2026)、pre-2026 −0.95；需重新核收据，未批准本次自动换装。既有冷静期和门继续有效。

## 工作队列（root负责调度与发布）
1. **ONLINE，最高优先**：root + live_recovery_audit_0927。核版本、pin、路径、ARM、启动与重启；16Z/20Z/00Z完整验收。先完成恢复首锚再单独排GAP4；M3与模型换装不和GAP4同锚。
2. **GAP4**：继承DEPLOY_gap_classfix_2026-09-26.md rev3；先冻结新机16Z参照锚和实际MH缺锚列表，重跑同机C0、归因差异和完整离线电池。只有真实通过才按协议发布。A10测试修复随批准的发布顺序接入。
3. **KSR**：research_resume_0927核在跑36格与冻结读数器。发现按年回撤门疑似错误聚合，先做红控并修门，再读候选数。root核后起完成读数器，不能让完成后的任务无人消费。
4. **FUNDING**：funding_mechanism_0927核已排除机制、真值源、EMA/间隔/成员/组合各层；先冻结一个低成本机制检验，避免重跑已否决的模型或组合族。
5. **D10 / future pipeline**：接续rerun6、训练服务身份及发布准备；是否发布由现有证据与用户授权条件决定，不能为了“最新”覆盖不合格旧模型。
6. **下一实验**：先消化KSR/FRESH/资金费真值；分开固定上游的干预与整组件删除，必须同人口同费用、完整连续状态、严格时间隔离、不同regime，先写判据再看收益。保持试验次数账本，拒绝单窗/单种子择优。

## 持续执行
已创建本线程30分钟heartbeat `automation`，用于读取本台账继续实盘验收与研究执行（不是新的实盘交易调度器）。期限到9月30日接回。现存Pod唯一短期在跑任务是fresh2_ksr_book_cells；根目录INFLIGHT_REGISTRY只经registry_edit修改。所有新长作业须同时登记，终态区分DONE/FAILED/RUNNING/GONE_WITHOUT_MARKER。

## 进度追加
- 15:38Z：三项独立核验已派：线上恢复、King/FRESH/DL续跑、资金费机制；读数器问题在读候选结局前发现，待合成反例核实。未部署、未宣称盈利能力改善。
- 15:50Z 前已完成：KSR 读数器修复 `4c2512057`，root 独立复跑 6/6；按冻结判据对各历史年对应窗口独立判回撤，不再跨年抵消。KSR 36 格仍在跑；最高判词仍需 IC 与整书证据合并，不能凭此自动换装。
- 恢复验收修复：`5370d3a36` 新增纯离线逐门判词；`88e5de74f`/`80503090d` 修复 K1 的跨币 orderId/clientId 误归属及无损解析。旧工具可把 ETH 的 oid 77 与外来 BTC 的 oid 77 当同单；新工具拒绝，root 独立复跑 10+23 测试绿。只改研究侧验收，没有部署生产代码。
- GAP4 同主机参照已在16Z结果之前冻结（`93acbe3f1`）：A=1790524800，洞固定3个；下一可能发布窗17:00–19:40Z，首个补丁锚20Z=1790539200。详见 `PREREG_GAP4_recovery_release_2026-09-27.md`。原 C0 shell 的末行echo会遮掉子判官退出码，必须读真实收据与子RC。
- D10 rerun6 的三方版本核验重跑 PASS（21 个装置、4 个 common、7 个外部依赖；检查器16反例全绿），归档 `acting_lead_2026-09-27/receipts/RERUN6_CHAIN_VERIFY_before_queue.json`，SHA `fea79b5096f4ea2fd2312d2ee460a81e2b7f99a8abab9b7e051a726c0e004b6d`。尚未起跑；KSR和约26GiB的rerun6不并跑。Pod host可用内存不能代替cgroup余量。后续队列由research_resume_0927准备。

## 接续必须使用的新入口

恢复机械判词与修后的只读场所核验在 `multi_asset/exports/research/acting_lead_2026-09-27/devices/`：`recovery_acceptance.py`、`venue_readonly_symbol_bound.py`。不再接受旧裸orderId装置的PASS。正常恢复后 `watchdog/state.json` 不存在，须先确认父目录可列；不得把FileNotFoundError当故障，也不得把权限错误当空目录。

详细实际路径、17Z命令、静默窗守卫和未覆盖项在 `/Users/haosiyu/.codex/tmp/acting_lead_20260927/live_audit.md`。`inspect_anchor` 保持默认盲态；N+55报告出齐后，在17Z静默窗做K1。20Z验收到位率门0.95，16Z重建首锚0.60。新K1仍只能证明其查询窗口内、commission命中的已成交订单，不证明全局单写者。

后续修复排序：GAP4恢复首锚绿以后，继续逐项处理生产者LR缺槽/资金费未定价持久队列/HOLD止损盲区；不能因GAP4成功宣布它们关闭。训练与策略试验保持与生产发布分离，新结果未过原门不换装。

## 16:07Z 接续更新（UTC；当地已09-28）

- 16Z运行日志已出现 start、preds/arm/filter；截至本节没有锚完成验收。不得复用12Z报告，也不得在N+55报告和17Z场所门之前宣称恢复正常。
- KSR修后读数等待器实际在跑：PGID `3505287`、start_ticks `509421593`，日志 `/dev/shm/acting_lead_20260927/ksr_readout/waiter.log`。上游KSR PGID `3479615`；当前无DONE/STOP。等待器绑定36候选路径加两基线，只有准确终态后才读数，非人工口头排队。
- D10串行等待器16:05:29Z已启动：PGID `3506841`、start_ticks `509498027`，装置 `688cb50e7`、registry `b5deb4c2f`。**重任务未开始**；先等修后KSR读数DONE，再要求cgroup余量28GiB、其它进程RSS≤4GiB、shm余量4GiB及211个pin未变。root独立复跑queue与KSR waiter共12测试通过（第一次在仓根执行因模块路径错误未运行测试，切到devices后成功，不隐去失败）。D10的DONE还须单看行判词，NOT_RUN不是PASS。
- GAP4发布准备已提交 `d668ed837`，入口 `docs/PREP_GAP4_17Z_release_2026-09-27.md`；24项静态核验只证明准备无漂移，未执行C0、发布或电池。safe_commit会自动push；先查每个实际门，再在anchor.lock下FF。20Z W6已固定epoch与三MH洞。完整首次验收仍含旧标准VERSION_PROBE/M3 shadow/PARITY/B4，不能仅用新9门替代。
- F7冷静期至09-30 08:47Z约束新的停机/恢复协议；本次只推进已有批准的GAP4，再单独推进M3。新跳闸绝不自动恢复。D10最早发布窗09-30 13Z且当前候选UNDECIDED，不把演练当换装批准。
- 资金费局部梯度仪器 `48f86de0a` + 见数前单位/来源修订 `0215deef2` 已做8个冻结片段CPU测量，**不是新策略收益证据**。root随后提出执行钟反例：整点+毫秒结算先于A+24m决策，应由旧持仓负担；new(A)承担全部(A,A+4h]会把不可达的避费动作写入目标。旧P2与新ms标签约150万格差异已由代理拆到此边界及18格同秒事件，不能称为大面积数据污染。待独立确认事件钟与持仓钟后才发两臂训练；完整引擎已有funding-before-fill事件顺序，不据此撤销现有整书回放。
- 研究独立分支已推送 `origin/codex/acting-lead-20260927`（首推至当时HEAD）；本节及代理随后提交需再push。生产树本轮零修改。
- 16:08Z代码审计发现已有fixpkg-e资金费队列，而非尚待从零实现；可能仍缺“账本行持久确认后才能出队”的屏障：队列durable写出，底层funding writer仅flush未fsync。live_recovery_audit_0927正在核其它屏障，并获准仅在独立新clone准备最小修复与真实writer负控；17Z之前不运行任何执行器套件，不并入GAP4，不改停机/恢复政策。未经真实红绿验证先记源码风险，未宣称发生过丢行。
- 16:10Z heartbeat实测：KSR及两个等待器PID/start_ticks全部仍吻合，无完成/失败标记；cgroup使用46,360,465,408 / 60,999,999,488字节。生产锚日志最新为16:00:05 start，尚无本锚done；watchdog state不存在，latest_eval仍12:40，不能拿它验16Z。16:12Z combo_status仍12Z是尚未到通常16:17发布的正常等待；其真实键叫anchor，不是anchor_ts，首次轻读错键得到None后已核schema，没有据此判失败。
- 资金费诊断已归档 `941d1e81d`（`docs/RESULT_acting_funding_mechanism_2026-09-27.md`）；18个证据件和T2实际运行源码保留。root发现已有跨缺口定价的额外未知放行路径（NaN数量/步长、未知成交方向、证据读取错误吞成空），已交同一修复代理在隔离clone补合同，测试仍必须17Z后offline wrapper。资产/收入身份域另行具名，不未经论证扩大去重规则。
- 下一研究执行不只停在报告：funding_mechanism_0927获准在同钟现金控制通过后，见数前冻结两臂同初始化/一epoch实现冒烟。仅两臂、不搜参、15分钟wall上限；CPU1、RSS≤6GiB、GPU≤8GiB，cgroup余量至少预算+8GiB、其它进程RSS+预算≤30GiB、GPU空闲与真实输出quota门。资源不足就排队；不抢KSR/D10。NC输入仅作实现测试，真正候选必须最新正确共同输入；不写改D10冻结213件，不据单折冒烟判收益。
- 16:43–16:48Z资金费事件钟继续推进：找回已登记的持久镜像（不是缺数据），原认证v3六窗、505输入和332源码核同；4,930 fill与1,083 funding现金闭合。代理提交`6f14e4ef6`，root从导出的初始持仓与严格先于结算的fills独立重算，数量误差≤1.46e−11、逐窗现金误差≤9.77e−15，收据`ROOT_fixed_cash_tape_20260927.json`。只证明认证模拟路径和可达梯度，不是新策略效果，也不是独立venue价格核验。代理曾在16:43Z本机用1.04GiB跑2秒；已明确后续锚窗内也不得这样重跑，改Pod或静默窗。16:49Z Pod余量13.81GiB低于14GiB门，短训练未启动。
- 16:50–16:53Z：16Z看门狗已评估`tripped=false`，无triggers/blind/unevaluated；target214,469.60、回读gross209,240.51（到位约97.56%），321名生产快照重放逐位相等。完整锚尚待done/N+55报告/K1，不能提前验收。新增316笔资金费因停机读数缺口未定价，沿既有funding修复队列处理；不影响NAV读取但账本不完整。
- 本次验收工具自身两处错误在真验收前发现：正常watchdog评估会写`reduce_only=false,tripped_at=null,_mode=LIVE`，不能把文件存在当跳闸；RID出生时钟与anchor_ts分别读取，真实相差1.44秒，不能硬断言整数秒相等。live_recovery_audit_0927正按生产源码补同输入红绿，不改实盘/风险阈值，不删除正常state。旧验收源码及错误测试保留在提交链，修后root复核再使用。
- 16:47Z KSR与两个等待器身份仍核同、无终态，cgroup使用46.13GB/61GB。research_resume_0927接续KSR最终按年/首差/同m0交互审计，仅写独立后处理与合成控制，不读未完成候选收益、不改在飞门、不起第三个等待器。

- 17:02:55Z 恢复16Z完整验收已真实完成：9/9 PASS；VERSION_PROBE、M3 shadow、321名PARITY与合池B4分别PASS。到位率97.5618489%，K1查询窗口外来成交订单0，没有新增HIGH或再跳闸；仅证明具名查询范围，不证明全局单写者。收据归档`acting_lead_2026-09-27/receipts/RECOVERY_16Z_20260927/`。正常watchdog state以false/null/LIVE验收，不能引用上文文件不存在那句当唯一门。
- 定时报表16:55Z早于真实anchor done16:58:34Z，原件保留。17:02:55Z用生产anchor_report的gather/build_report纯读函数在独立目录形成收尾后报告，未调main、未写生产报告、未发Telegram；未放宽报告新鲜度。
- 17:06Z GAP4同机C0 PASS10/10，current归档321名逐位相等；补丁58名权重变动最大0.0001307082，均由冻结三洞MH重算解释，KC不变。W0四门通过；17:07Z四生产者服务已bootout，发布clone仅两份契约归档+A10测试文件进入safe_commit全电池。尚未安装候选，执行器仍d01e35d。
- root独立复跑KSR终态补充装置14/14通过，来源`874a8cf16`/`65ca5f65f`，只在既有reader DONE后人工单CPU读取；没有第三个等待器或未完成候选读数。

- 17:19Z **GAP4发布被safe_commit拒绝**：166套165绿/1红，唯一红为tests_disposition_matrix的稳态非自愿缺口<200U断言。具名失败RID A1790497440是今日08Z双执行器事故锚（约667U），不是16Z恢复锚；16Z仍为REBUILD且验收PASS。断言与OD源码在候选/生产逐字节相同，不能称GAP4代码回归，也不能因解释事故就豁免历史红。已派纯离线逐行定位，未放宽阈值、未删锚、未重跑碰绿。
- safe_commit未提交/推送，未FF/安装任何候选。17:19:56Z已恢复原四服务shadowloop/combolive/combosnap/comboparity，PID分别37089/37091/37093/37095；生产HEAD仍d01e35db，原生产者字节未变，未调用resume。收据GAP4_W3_REFUSED_20260927T1719Z.json及GAP4_BASELINE_SERVICES_RESTORED.json。**后续不得重复bootout或沿旧stage4直接安装；W3未过，GAP4和后续M3仍未发布。**
- 20Z恢复核验入口已准备于临时目录run_accept_20Z_after_done_report.sh（SHA383cf0bafef78a15605311b7312ed55e8dd395a468263d9636b98907a66c7f3d），只在21Z且真实done/N+55报告之后执行，到位率门0.95。GAP4 W6仅在确实发布过候选后适用，现在不适用。
- 17:28Z root独立逐行重算：08Z非自愿缺口667.0389U全部来自OPENUSDT的一条topup_taker，terminal=abandoned_max_attempts，场所-2022 ReduceOnly拒绝，confirmed成交0；maker前序-5022后重挂终态0。原始行SHA/行号与纯OD重算收据GAP4_ROOT_gap_source_20260927T1728Z.json。尚未用时间/仓位证据闭合与旧机外来平仓的因果关系；不能凭拒绝码 alone归因，更不能改成policy deferral消红。
- 17:25Z Pod轻读：KSR3479615与readout3505287、D10队列3506841的start_ticks均核同，均无DONE/FAIL/STOP，cgroup46,673,752,064/60,999,999,488字节。最终KSR后处理source075382db的14/14控制由root再次独立通过；未部署/未读候选收益。
- 研究共同输入继续核：rerun6是输入重建演练，不等于完整候选执行评估。research_resume_0927正在沿真实D10RR配置、driver、funding消费者核SHA与ms事件接口；在闭合前不把干跑DONE当新现金口径认证。资金费夹具的单一15分钟wall从17:17:09起，到17:32:09止；首轮Python/CUDA不兼容失败在首个梯度之前，无optimizer更新。重试改用已有Blackwell兼容venv但资源门不足仍不启动，失败保留、不重置预算。
- 17:31:07Z资金费durable-ack RED阶段已启动，克隆funding_durable_ack_exec_20260927 HEAD14795a1（仅新增测试，源码cea1e15），唯一入口未改的ops/run_acceptance_offline.sh，内核隔离探针通过，网络/生产/凭据均拒绝；unified session39774，完整日志state/FUNDING_DURABLE_RED_20260927T1732Z.log。**正在跑完整电池，不再并发或重复启动执行器套件，也不在跑中编辑源码。**
- 资金费子套件已完成：G1–G10、R1真实545行整行相等与schema正控全部仍绿；新增D/E故障控30格失败，精确抓到file/day/root无fsync、确认失败却pending清空、已可读重复绕过确认、NaN/读取异常/畸形队列放行。源码与日志绑定归档receipts/FUNDING_DURABLE_RED_20260927/。这是候选修复包的红能力证据，不是实盘已发生丢行的证明；完整电池终态还未出。下一步补真实损坏末行/stat权限红控，再在同克隆修确认屏障及严格证据读取，单独验证，不与GAP4混包。
- 17:35:02Z资金费六窗网络夹具终态已封存（30e2a9625）：EXPIRED_AFTER_RUNTIME_FAILURE_AND_RESOURCE_REFUSALS，原900秒预算结束，唯一child活动15.896秒，成功网络forward/optimizer更新均0，无模型产物；NO_RESCHEDULE已在Pod持久化，入口复验exit78且不启动child。不能以本次失败否定资金费学习方向。较小RSS预算仅另立工程提案，未经root核其真实上界及监控，不重置原实验预算。
- 17:36Z GAP4独立本地时序审计b6a3e70a1：OPEN在08:44:53.882659真正发出reduce-only补单，被-2022拒绝；此前08:43:43撤单是-2011 noop，不能称确认撤销；08:46:44持仓回读0。本地仍缺该名旧机F20260927083112订单/成交明细，故逐名外来平仓归因UNRESOLVED，历史send-quality真FAIL保留。入口docs/AUDIT_GAP4_OPEN_08Z_failure_2026-09-27.md。后续可准备窄Q5/Q6只读取证工具（OPEN固定历史窗、两个GET、饱和拒绝），先做源码与控制审核，尚未调用；不把它扩展为每锚K1轮询或发布豁免。
- 接续分工：live_recovery_audit_0927先完成窄取证接口静态审查，然后在full RED终态后继续资金费durable-ack修复；research_resume_0927完成D10首120输入/毫秒时钟manifest与拒绝控制；funding_mechanism_0927封存失败夹具并做独立资源上界提案。所有发布仍由root逐门验收，当前生产未换模型、未开M3、未装GAP4。

- 17:39–17:45Z，依恢复计划Q5/Q6在静默窗做了唯一一次OPEN历史窄取证：两个GET，固定08:20–08:47Z，allOrders 2行/userTrades 5行均未满页；原文私有保存，未输出凭据、未查逐臂结果。独立代理453ed3001与root从原文分别联结确认：本机maker 910475678于08:31:10.485已CANCELED、成交0；F20260927083112外来订单910476907于08:31:51.518卖出4708张，5笔成交合计4708；本机08:44:53后补减仓才被-2022拒绝。订单级归因已闭合，物理旧主机归属仍依赖事故记录，载荷本身不能认证发单主机。ROOT_OPEN_Q5Q6_20260927.json绑定原文manifest；历史send-quality真FAIL保留，GAP4仍不可发布。
- 17:42:33Z资金费完整RED终态：168套166绿/2红，wrapper exit1。两红分别为新故障控tests_funding_gap与既有08Z事故tests_disposition_matrix；日志SHA05cf69387e93764f4f84759fa09fac53bb5d106e8d3812cf8432c27f81bf9b52。root从session39774与完整退出码表独立确认后才放行代理编辑。后续补真实损坏末行、stat PermissionError、新鲜读数未知及冲突重复行红控，再实现只影响资金费调用的严格证据读者与durable-ack；不全局改变读者，不混入发布GAP4。
- D10首120身份/输入门1dbe61fa0已交：实跑特征新ms账与现金旧秒账的两条调用链确认；两账覆盖期不同，尚无共同期现金差证明，不能说旧回测资金费已错。原D10 targets已缺失，首120必须重建独立目标/适配器/配置。root审发现uint offsets回绕及FD/路径身份边界，已要求同输入红绿修后再接新消费者。checker只能签INPUT_CONTRACT_PASS_CASH_UNVALIDATED，不代表书收益通过。
- 原六窗网络夹具不再排队。独立内存工程提案fd8d70dc4只记录CPU/GPU分阶段办法，未将约1GiB失败阶段峰值当正确CUDA的3GiB硬限，未改共享cgroup。研究代理优先推进真正D10共同输入的ms现金消费者与首120，不为修正运行时重置旧900秒实验预算。

- 17:50Z root按见数前冻结3b7c7ced4做共同期资金费事件事实核对（CPU1/8.416秒、峰RSS123428KiB，无q/价格/收益读取）：一对一费率改变0，1473283格毫秒也同，1220216格仅子秒不同；18个同秒多事件；另149个old-only尚需核是否终端覆盖或合成行。原共同比较收据归档，不以样本猜总体，不以秒/ms接口不同宣布旧回测现金错。装置目录T1758Z只是预命名标签，实际执行约17:50Z；预读NPZ头探针因numpy私有API不存在而失败，未产生读数，实际装置走公开np.load通过。
- D10输入门844de1505由root再次独立13/13通过，修无符号offset回绕与打开文件身份；旧manifest不改。精确ms消费者cash方法+真实HistSim31 run/push/dispatch的小型控制由root独立10/10通过（包括同秒两结算夹fill、同刻fund先于fill）；只是固定q/price夹具，不是完整组合回放。原首120实查F10 OOF未覆盖2022-07：UNAVAILABLE，保留原拒绝；后续只能在见现金/收益前按固定完整OOF支持域另立机械修订，不能以利润/非零成交挑窗。
- 20Z与09-28 00Z验收脚本已准备，尚未执行。修正了20Z包装器先查K1后等done的次序：现在首个probe/API前必须先有唯一LIVE start与rc0 done，允许静默窗内跨小时收尾；1正/5负控制及bash语法通过。新sha为d64017da(20Z)/f69b0020(00Z)，收据RECOVERY_20Z_00Z_PREP_20260927.json；分别只在21Z/01Z静默窗执行，不创建额外K1轮询、不自动resume。
- 18:01Z前，共同期149/18差异已由research_resume独立关闭（3b72b9364）：149条全部是旧末秒后的+1ms事件，费率与原stream-D一致；18个同秒多事件名在冻结crypto/pit/production book_legal均无持仓资格。root核原JSON逐条相同。此证据不含实际持仓，不能冒称现金影响为零；也不支持大面积费率污染的归因。归档d10_boundary_population_20260928/，7项事实检查通过。
- 资金费RED2终态：168项=163套件+5审计门，166绿/2红；tests_funding_gap原30+新增20故障格为红，既有08Z历史disposition红不变。日志SHA6f63102406931b5ef625ff49569d28a0b94593345318cbbe4aced72880b50c0f，实际suite stamp174625（文件名1749只是标签）。未找到完整不可变的pre-RED状态副本，撤回“全电池同字节状态对照”的设想；R1与故障格用各自固定夹具，GREEN另钉当前360文件输入清单，不从移动生产刷新冒充原基线。
- 18:02:33Z资金费GREEN完整wrapper启动（session73846；driver文件标签1804不等于实际开始）；资金费子套件已绿，R1仍545行逐字段相同，实际file/day/root fsync正控通过，545次写入确认合计0.034186秒。全电池仍在跑、源码未提交，root与独立代理正只读审查；不能把子套件绿当发布许可。生产仍d01e35d，GAP4仍未安装。
- 18:06:28–18:06:50Z，机械支持域修订后的首120完整组合目标与现金任务已实际跑完（cfb8e5d3d；原2022首窗拒绝保留）：2023-01-01..01-21、完整King/F10/fund、固定模型s42/执行seed0，scaled仅9/120发布、111HOLD，literal0发布。原OVN roundtrip逐位通过；代理报逐事件cash误差0、逐窗约1.16e-14、equity约4.50e-10。root已要求补数量独立门、把“一分钱负控”由算术真式改为同核对器真实拒绝，再从原tape独立重算。当前只签候选现金仪器，未跑新模型优化、没有新增收益/夏普结论，不能因该窗通过宣布完整OOS评估完成。
- root独立现金核验已完成（68677f73e）：不导入引擎，从封存初始0仓和5225笔模拟成交重建全部9104事件的q(t−)，数量/现金误差均0；改现金1美分、数量1张、初始仓位或增加重复收费，四项均被同一核对函数拒绝。原模拟产物ddd8ef3b6/a1dcd597a归档未覆盖；价格与费率仍来自同一被钉引擎tape，未作独立venue真值、完整价格P&L或收益改善声明。
- 18:12Z Pod轻读：KSR与两个等待器PID/start_ticks核同，无终态；cgroup46.65GB/61GB。18:18Z生产轻读仍d01e35d、代码区diff空，watchdog LIVE/false/null、triggers空。没有新resume、API调用或部署。
- 资金费GREEN1 18:15终态exit1：168项166绿/2红，原资金费故障格103/103已绿，但tests_binance_funding[M]新增7红，另保留历史disposition红。原因追到W/M测试根同父目录导致pending队列串用；新“冲突不覆盖”把旧夹具隐蔽冲突显露。后续只修夹具隔离，不改M行为期望或真实账户冲突门。
- 独立审查e101bba96（root纯AST逐位复现）发现继承未闭合P1两条：同快照冲突后行覆盖；部分append失败后继续下一笔，后笔被ack出队却拼在坏JSONL行上。另P2日期名普通文件被忽略、条件性P2写者FD与ack路径inode未绑定；后者没有已认证生产触发证据。RED3已启动唯一offline wrapper（session85622）；在修前原实现上新增资金费17格已红。新增诊断漏import json导致M诊断NameError和静态名门红，保留原失败，不冒称完整诊断完成；不为这条输出错误额外重复整套RED。终态后同批修四类实现与隔离夹具，再跑GREEN2。尚未发布。

- 18:33Z root独立两锚共享参数反例通过：当前成交前现金对当前目标导数0，但对前锚库存/共享参数非零；总梯度−1.46，与删去早结算所得−0.72、错误提前用新仓所得+0.39均不同。源码与JSON归档ROOT_SHARED_PARAMETER_CLOCK_20260927；只验合成因果，不验神经网络或盈利。已交资金费研究代理作为独立参考。
- 已审fd045e069并仅授权一次独立固定形状CUDA探针（合成零输入120×829×171、一次forward/backward、无optimizer/模型/市场数据，60秒、RSS申报3GiB/软件止线2.5GiB、公共余量8GiB/GPU空闲门）。不是旧六窗预算续期，不据一次峰值自动降低真实训练预算；待实际终态。CPU小规模参数/硬forward控制继续准备，未授权完整训练。
- 资金费RED3终态168项164绿4红，具名包含原故障、夹具共享路径、诊断漏import和历史disposition；保留原收据。GREEN2由未改offline wrapper于18:31:30Z启动(session75860)，资金费及原binance_funding子套件已绿，完整终态未出。独立审查继续；同选集360文件SHA与GREEN1核同，不扩称完整state同字节。

- root新发现并用固定gross/net数学反例证伪G3的容量读法：null权重相关0.9441不推出F10独立敞口≤0.0559；同相关合成书的正交gross可为0.2588。FINDING_F10_capacity_not_correlation_2026-09-27.md列出原三处和可复跑源码，约束后续研究读法；不改原失败实验判词、不估计生产真实容量、不宣称发现盈利策略。
- 独立CUDA资源探针18:34:23–49Z实际完成且root复核源码/命令/终态/worker SHA：一次synthetic forward/backward、无optimizer、参数逐位未变，RSS观测峰1.389GB、GPU观测峰1.088GB、26.11秒。只证明正确Blackwell环境可运行这份固定MLP，不证明完整训练内存上界。CPU小型共享参数/一步更新控制获准固定300秒预算，未批准完整120网络训练或重开旧六窗。

- 资金费GREEN2完整终态已由root独立解析168项退出表并核源码：167通过/1红、wrapper exit1，唯一红仍为08Z历史disposition。代码冻结提交13ca2cc7533ecc4cf5ad4372b69f4b771589279e；资金费123/123及原binance_funding76/76通过，R1的545行保持逐字段相同。独立AST四类审查e886e404b也通过。driver SHA3cb259c1…，root收据ROOT_FUNDING_GREEN2_COMMIT_20260927.json。结束本批实现反复修订，不重复跑电池碰绿。
- 发布边界再次钉住：13ca2cc基于cea1e15，后者比在役d01e35d多10个尚未部署提交（fix-pkg-e/A10等），本轮另外5提交；不是直接可在d01上打四文件就算集成通过。保留全部依赖的增量Git bundle已git bundle verify通过，183694字节、SHA7b8b3712…，前提d01e35d；生产未修改/未部署，GAP4/M3门仍被真实历史FAIL挡住。
- CPU参数控制原attempt18:46:45–18:47:16Z完成，原rc0/RESULT保留：共享参数现金反例通过，10项参数FD最大误差1.47e−10；8个给定输入step前向最大误差1.74e−18，错误phi 8/8拒。**不得把它签成整项PASS**：F=0两臂torch.equal相等，但全对象SHA不等，原字段名F0_bitwise过强，严格字节身份UNRESOLVED。未知是否仅signed-zero/其它字段，原件未覆盖。只准原300秒截止前追加纯F0定位，不重置预算；给定输入step平价不等于完整连续HOLD/执行库存验收。
- 下一轮仍按原队列：KSR及D10等待器最近18:37:57Z核实仍在跑、无终态；只在reader DONE后跑既有KSR审计装置，不增加waiter。20Z恢复验收在21Z静默窗按d64017da脚本（先done后probe/K1），09-28 00Z在01Z按f69b0020；不自动resume、不额外Telegram。
- F0补充定位在原18:51:45Z硬截止被SIGALRM终止（rc−14、ORIGINAL_DEADLINE），未产出定位结果。收据d70e93e07保留；严格字节身份仍UNRESOLVED，不把数值相等改写成字节相等，不续期重试。原CPU控制已完成的FD与因果测试证据不因此撤销，但整项不可写ALL PASS。
- 18:56Z复读主仓STATE顶部仍为09-27 13Z恢复条目，无主研究员接回通知。18:57:29Z Pod独立轻读三个PID/start_ticks全部核同，KSR与D10队列无DONE/FAILED/STOP，cgroup使用43,739,254,784/60,999,999,488字节；没有新等待器或并行重训。
- 后续资金费研究只准备首120真实输入的冻结小包、标准化身份及资源预算。已读NPZ头显示两特征成员为ZIP_STORED，可按成员样本区间读取约11.43MiB的171列而不展开整面板；此为读取方案，不是重训结果。完整120网络前后向及optimizer仍未启动；不能以旧checkpoint在新输入上的实现验证冒称修复后重训。
