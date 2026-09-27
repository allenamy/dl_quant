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
