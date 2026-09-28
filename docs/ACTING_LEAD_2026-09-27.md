> **创建:** 2026-09-27 15:38 UTC | **Session:** Codex root / acting-lead-20260927 | **状态:** in-progress | **作废条件:** 用户停止、主研究员接回或 2026-10-01T00:00+08:00；引用的版本变化时重新核验

# 代理主研究员执行台账

## 11:29Z逐层机制完成，新LQ在飞（优先读本段）

- **F10阶段与删名分解已完成，不要重跑。** 六条流各7056锚与固定生产chain档案kc/fc/raw逐位同；近期共用473/480锚、9月108/108。R180近期纯秩价格相对NC +.394/+.380 bps/锚，经fund/FTRIM后+.091/+.041，流动性选择与配平后−.0506/−.0271。近期平均400评分名仅246.49通过门；删除一步取走+.625/+.825相对价格贡献，重新配平返还一部分。但保留名IC亦提高，9月筛前价格已负，所以**人口错配不是全部根因**。报告`RESULT_F10_signal_to_book_decomposition_2026-09-28.md`，原stage/selection收据67b43fda/ea81b14f，本机独立1008+168格核对、数组8.45MB封存全验。这些不是现金NAV收益、不是解除流动性门的证据。
- 原attempt1因我把生产“先融合后稀疏序列化”顺序写反而拒绝（单格8.07e−11）；同原截止修精确顺序、未松门。失败保留，attempt2 11:03:27 rc0/33.75s；selection 11:09:12 rc0/12.27s，均CPU1无GPU，registry已关闭。
- **当前唯一新增GPU试验：f10_liquid_population_20260928**。根`/dev/shm/f10_liquid_population_20260928`，源同名_sources，PID/PGID3611346、ticks516417928，11:18:05实际启动。contract32703e72…；预注册ce277c432、实现993acabef、登记c13524c9f。只把训练效用人口改为finite(QV)且≥250k，其他原loss/EMA/抽窗/初始化不动，复用U两种子真实模型与64现金对照。23前置控制；11:26:27 s42全部23折完成，11:26:48 s2027首折完成。**训练绝对截止11:42:59Z，总截止12:12:59Z**；不得重新计时/重复起跑。自动接两完整组合与64新现金路径、配对U/NC、近期优先20门；终态前不得报收益或部署。GPU训练不是完整组合已完成。
- 11:00:45轻审LIVE/no trip、triggers/blind/unevaluated/metricerrors0；老partial2继续，S3心跳6.3秒。未新增锚验收/API/Telegram/生产写/恢复/改2倍。12Z锚附近不做本地重活。
- 最近原价/通道实物已经完成，不重复下载。09-19..27尚未接完整可交易人口、funding事件、连续状态与现金引擎；全部本批经济数仍止09-18。主仓STATE未出现接回声明。


## 10:43Z输入验收完成（优先读本段）

- channel_parity已17.73秒rc0结束，**原判DIFFERS保留**：共同有限11,832,311值7通道全部精确；08Z当前fetch519名子群无数值/缺测差异。全轴有noncrypto149与不在当前抓取名单的名字产生缺测差，不准抹成全表平价或把原始存在bar当可交易。完整837轴面板已隔离生成ac8bfa6f…，原生产不动。报告`RESULT_recent_raw_input_parity_2026-09-28.md`，原件/分组/资金费同快照绑定收据已落盘。近期funding九月归档927cac43…已冻结，不代表独立场所完备性。
- F10 score诊断补齐：两种子近期rank-IC NC→R180为.02544→.03359/.03339→.03973，逐名P/S亦升，但完整组合均亏更多。不要再写“近期训练没学到信息”；要定位信号到最终资本权重/连续仓位的哪一步损益反向。不是据此撤销CRITERION_NOT_MET，未改判据。详见同一F10报告新增表。
- 10:36:24Z本地轻审LIVE/no trip，历史partial2无变化，S3心跳2.35s。没有新锚/场所验收，不重复K1。F10/近期取数/通道验收任务都已结束，**没有须等的本批训练/GPU作业**。接旧认证原价重叠的只读小工具e5f615bde已冻结到`/dev/shm/recent_inputs_overlap_20260928`，10:46:37Z已rc0/5.49秒完成；PRICE_OVERLAP.json为描述性非精确平价：458850个5m收益差中位9.56e−8/max5.86e−5，31名×576旧有限新缺测，不拼接、不改旧源，不能当在飞训练；随后绑定逐锚fetch/合法性、资金费事件与连续状态，补09-19..27；或做F10同人口逐层价格归因，禁止再扫R180超参。

## 10:35Z调度覆盖（09-28；旧在飞记录已终结）

- **F10近期适应完整组合已结束，禁止重复起跑。** 最终根`/dev/shm/f10_recent_adapt_20260928_finish`，10:13:54Z rc0；128新路径+64NC对照。原90分钟预算10:10:18Z失败(124/128)，另立10分钟只补四条，原失败未抹去。实际总93m39s。判词**CRITERION_NOT_MET 18/28**：R180−NC近期−0.474/−1.718 bps/日，两种子九月皆更差；U亦近期变差。不换装、不网格追赢。原数组独立192文件6510核对最大差3.15e-14。报告`RESULT_F10_recent_adaptation_full_book_2026-09-28.md`。registry已b2d416ada关闭。
- **最近行情采集完成，禁止重抓。** tail10:17:01rc0；三段严格原9207请求合并8866 verified+341显式404，全部档案有288行。不能把404当退市或填0。本机ZIP91,930,085字节sha b9686fad…，17,746成员全部size/sha核过；registry2ed19daff关闭。`RECENT_PUBLIC_PRICES_20260928/MERGED.json`给完整人口。下一层是输入同源/通道/合法成员/资金费/连续状态，不是直接宣称最新回放完成。
- **当前唯一计算**：本机隔离`/Users/haosiyu/.codex/tmp/recent_channel_parity_20260928`，冻结源747ef12ab；09-17..27官方原价按生产两函数AST提取生成七通道，与08Z冻结rolling比较。9控制红→绿；只读快照/源，单线程、600秒预算，无网络/GPU/交易所。需读TERMINAL与RESULT；尚未得判词，不重复起跑。
- 自犯资源问题已纠正：首版现金归档跟随文件symlink，四次复制2.96GB相同特征，生成13.93GB冗余ZIP致/dev/shm只余0.39GiB。逐件复核160源成员/148唯一路径原件完好后，只删除此冗余ZIP；修helper跳过并钉symlink，重新压缩现金归档1.079GB，空间回到约13GiB。原数据/模型/现金路径零删除。两次错误传输明确.partial；10:35:30Z新档案本机203+144成员/128PATH全验，sha6c8eb311…，不把partial算归档。收据ARCHIVE_DUPLICATE_REMOVAL。
- 生产10:02Z所见仍d01e35d、LIVE/no trip，08Zdone验收已记；cond2/cond4老partial继续。无resume、部署、改2倍、API或Telegram。全部研究收益仍止09-18。

## 10:03Z调度追加

- 新近价格attempt2按原预算PARTIAL结束：4547 verified /181 absent /4479 unattempted。续取已独立登记f41f90b38，根`/dev/shm/recent_public_prices_20260928_continue1`、源同名_sources，09:57:00Z PID/PGID3604363 ticks515931443，deadline10:12:00Z，contract7d7e9b86…。只补4479缺口、最新优先、四线程静态CDN；不再重启原全部人口。未知与404保留。
- F10现金09:59:26Z开始最后R180_s2027格，前三格96路径已成；总截止仍10:10:15Z。若超预算必须原失败保留，不可把训练完成或部分路径当全组合完成。已准备独立raw-array核算和完整归档工具（31e148a75/17b85dcdc），还没执行，须等终态。
- 10:02:44Z轻读生产LIVE/no trip、无trigger/blind/unevaluated；历史cond2/cond4 partial仍在，无新动作。

## 09:52Z标签可观测性类缺口已取证并独立修复（09-28）

- 新发现/动作见`FINDING_F10_recent_training_admission_2026-09-28.md`。207份官方日文件180验证/27不存在；1041缺标签中852经完整49价证明可恢复。隔离overlay ea6e4b73…实建并本机验sha；所有旧有限标签逐字节不变。原训练门实跑187窗接受178→181，最新标签08-09→08-17；六旧窗仍拒。模型/收益/生产未变。证据ZIP652c5163…364成员本机全核，registry该取证作业已fe583445d关闭；不是再等在飞。
- 现金续跑仍同根/同原10:10:15Z截止。09:47已U两种子共64路径完成，R180_s42引擎09:45:45Z开始，第四格尚待；不读部分候选经济数，不重训，不改原数据。
- 新近价格静态档案采集attempt2根`/dev/shm/recent_public_prices_20260928_attempt2`，PID/PGID3601317 ticks515767131，09:29:37启动，deadline09:56:21Z；contract d9b60516…。固定837名×11日(09-17..27)9207请求，4线程、无凭据/无交易所REST。预计预算前无法全完，必须读TERMINAL/MANIFEST的partial。旧原轮因合法中文符号校验过严在网络前失败；异常原件保留，Unicode修复与9控制后换根，不能把失败算通过。

## 09:21Z GPU训练完成、现金串行续跑（09-28）

- attempt2于09:07:28Z完成两种子×23折×U/R180共92模型输出，24m7s；GPU峰值2.40GB。完整模型/预测/源已封存到本机134,970,951字节ZIP，312成员逐件size/sha已核；zip sha125041dd…，见LOCAL_TRAINING_ARCHIVE_VERIFIED。不是整书收益完成。
- 09:11:39Z现金阶段被共享资源守卫中止（两格同时各4worker）；无PATH完成，未读候选经济数。精确触发瞬时内存未记录，不能称实际OOM。原FAILED与配置/日志保留，所有旧自有PGID已退出。
- **现金唯一新在飞**：`/dev/shm/f10_recent_adapt_20260928_cash_resume1`，source同名_sources；09:20:55Z PID/PGID3600376 ticks515714950，合同6935d296…。c0244836d只改调度为逐格，U复用原目标/配置，R原码新建，不重训/不改模型、费用、判据；同原30GiB守卫、同原10:10:15Z截止。需128路径全部审计+ECONOMIC+BOOK_DECISION才算完成。入口7项真实函数控制，尚非真实续跑终态。registry原任务已关闭、新任务6a06c15ee登记。下一轮不要重训或再启动。
- 08Z本地posttrade证据已补：08:58:34Z done rc0、319名PARITY零差、生产/归档/消费目标sha052d6c7e…与两pin相符，gross完成99.6206%。LIVE/no trip；老cond2/cond4 partial两项仍在。未新增场所K1、无resume/部署/改2倍杠杆。
- 最近数据实物已保护：08Z快照10件87MB复制到本机隔离根并前后复哈希；原始价端点库存59锚、4缺槽、11,419个时戳相符端点，37锚无prev_close_ts证据。只是端点，不等于完整5m原价标签，不据此算最新收益。清单/6控制见RECENT_ENDPOINT_INVENTORY；不把rolling f16特征冒充原价。

## 08:58Z近期评价重读完成（09-28）

- 已落实用户“先改评价权重”的澄清，独立只读192候选+64原NC路径，未改旧实验门或重跑模型。下半年80天cap50/逆波动/流动性混合均改善累计收益、回撤，但优势集中8月，9月全部更差；六格下半年配对CI仍含零。故旧年均值失败不自动否决近期研究价值，亦不能把2026视为单一不可逆regime。报告`RESULT_recent_evaluation_priority_2026-09-28.md`，RESULT sha c4445a6f…。月31天相对30日块的CI不适合作确认，未引用。
- 计算21.1秒/峰值570MiB/CPU1；所有路径旧sha一致，9月全部原指标重现。新F10训练继续，08:58已进入s2027的202504（s42全部完成），尚无完整组合判词，勿改源或重复启动。
- 08:55:18轻读：生产LIVE、08:50:16评估tripped=false、无trigger/blind/unevaluated/metric_errors，历史partial2继续。S3新鲜，2登记任务（S3与F10），不是完整锚验收。第一次给工具错传仓根INFLIGHT_REGISTRY导致UNAVAILABLE；原失败件保留，改用已登记loop目录后正确读取。不是生产异常，不以错误命令结果触发风险动作。
- 数据时效缺口：所有本批收益止09-18。Pod旧daily BTC档止08-30，已有生产rolling为f16特征、boundary_raw仅越界补丁，不当作完整原始价格链。未拉场所API/未声称已补09-19以后的评估。

## 08:43Z新训练已起，评价近期优先（09-28）

- 用户再次澄清：首先是评价近期权重更高，训练近期加权只是可试方向。新目标已在71823ce73见数前冻结：2026H2主判、九月不得更差，旧年检尾部而不要求每年收益提高；旧实验原判保留。
- **实际GPU作业在跑**：`/dev/shm/f10_recent_adapt_20260928_attempt2`，源码同名`_sources`；PID/PGID3596746、start_ticks515489243，08:43:18Z起。两个种子×23原折×U/R180各96次小步warm-start更新，然后自动四格完整组合/128现金路径、双指标与近期判词。原NC模型/归一化/King/fund/席位固定；半年半衰期只改抽窗概率；非新架构/非D10政策。08:44:13首折U完成，GPU24%/2.4GB；不是收益证据。
- **硬截止未重置**：原08:40:15Z计时，训练截止09:25:15Z，整批截止10:10:15Z。新source526b333be；合同97f2cfbd…。GPU空闲预检、15控制、基线64PATH/来源复哈希通过。只监本作业精确PID，不按名称kill。下一轮勿重复起跑/改判据，先看真实TERMINAL+ECONOMIC。
- 首轮08:40:49在CUDA/optimizer前失败：我把原训练器的缺标签NaN对齐误简化成全轴相等，真实标签比特征晚12锚起。已补同形红→绿，恢复原合同；原终态/源保留。不是数据污染或策略失败，不把自动终态的GPU_training=true误读成当时已训练。
- 已预留评价历史化边界：研究轴截至09-18，尚不覆盖最近十天真实亏损；不能以本次近期筛选直接认证09-28线上表现。原生产仍d01e35d，未部署/resume/调用场所。

## 08:24Z接续与用户新方向（09-28）

- KN标签几何已完成，不是新模型收益：2023–25 / 2026价格与净额标签平均秩相关.999595/.999152、尾部10%保留约99%。高费尾部改变仍明显；不把它解释成资金费不重要。报告RESULT_KN_label_geometry_2026-09-28.md，原8收据已本地核SHA；抄写stderr哈希时重复045的错误当场核出，按实际原件纠正，未改变原件。
- 08Z08:00:05启动；08:17:13 combo rc0，08:20:18目标两pin相符，发布SHA052d6c7e…。尚未完成本锚posttrade验收。08:12轻审LIVE/no trip，但历史cond2/cond4仍partial，不能写全健康。无场所调用/部署/resume。
- 用户明确要求近期优先的新适应性研究：旧实验门不改；新比较近期收益优先、旧年份检灾难风险。原FULL与nested实验均已失败，不能照跑。拟从现有F10逐折模型继续训练，同预算均匀历史对照与180日半衰期近期样本对照，再跑完整组合；不改King/席位/实盘。GPU08:27读0%、2MiB，无外来训练。新实验必须先冻结合同与对照，实际起跑另记。

## 07:51Z增量巡检与三条研究线核对（09-28）

- 新轻量只读工具 `devices/light_local_audit.py` 固化真实字段（`_mode` / `evaluated_utc` / registry `closed`）；不导入执行器、不调网络、不碰盲态数据。缺键/类型错/非有限/时间身份错判UNAVAILABLE，优化模式关闭断言时同样拒绝。10项离线控制通过，另验`python -O`拒绝；测试先于实现写入并观测缺模块红。不是执行器电池或锚验收。
- 07:51:05Z真实收据为 **LOCAL_ATTENTION**，不能写全正常：state LIVE、reduce_only=false；最近04:49:20Z评估无跳闸/触发/盲/未评估/metric_errors，但partial两项是cond2_day_loss与cond4_drawdown。独立读原因：前者历史8个划转/起始日被排除，后者08-29缺target_gross；这不是新跳闸，也不据此修改政策。常驻S3心跳38秒，registry仅此项未关闭；任务记录不替代进程存活验证。收据`LIGHT_LOCAL_20260928T0751Z.json`，其device sha为最终加优化模式拒绝之前的版本，原件保留；改动只有优化模式拒绝。没有场所调用/部署/resume。
- 用户询问King/资金费、DL创新和融合的结论：已重读原KING_IC_KN/A1收据与完整组合报告。**KN不是KSR**：KN只改净额标签，配对ΔIC pre2026 −0.000356、2026 +0.000603，门未过，未跑其书层；A1月度ΔIC +0.007326/+0.001692，后段不足0.002幅度门，不可概称无信号。KSR是另一服务年龄政策，整书2023Q4 −4.502bps/日CI全负。残差/长持有期两组是Ridge机制基线，不可冒充新DL；T3新版只有工程单步，未完成OOS多折重训。融合流动性历史提升但九月与尾部恶化，不能换装。本轮仅核既有收据，无新训练或重复模拟。

## 用户所指最新约1读数的定位（09-28；优先于下段解释）

上一回复拿OLD约1.2解释用户所指最新约1，定位不充分。已查主仓lead 09-27 `DESIGN_nonfunding_sources_2026-09-27.md:66` 明确为**NC pre2026**；原始NEWS2_STATS的1.0205269605166336/1.1369332184419685与独立复算精确相同。因此已定位这条读数与NC全窗1.784/1.858的差是加入2026强年，不是版本差。双方sha/逐值比较已入`BASELINE_SHARPE_BRIDGE_20260928/LEAD_NC_PRE2026_MATCH.json`，报告顶部已更正；另有未提供的全窗约1文件则仍待核，不能宣称已解释。只核已有数据，未开新作业。另注意9/24旧席位继承已被9/26重播种部分更新，不可继续把初始部署手册当当前状态。

## 读数更正（09-28 07:38Z）

用户问全窗夏普为何从约1到1.8。已读取96条既有现金路径、统一1176完整日独立复算：OLD/A0=1.104900，NC42=1.784173，NC2027=1.858314；旧窗口/平均路径算法精确复现旧1.22为1.221318。共有执行配置/成本/pins相同，主差来自不同模型和递推目标，主要出现在2023H2–2025；不能归因为统计口径或宣布当前实盘具备1.8。NEW1.44是第三对象，不能与OLD混称。报告`RESULT_baseline_sharpe_bridge_2026-09-28.md`，收据sha8ecd5c25f360875962e38e141760c0383e32149d837f6f74a333245f25436101。无新模拟/训练/生产改动；本条不重开已结束流动性候选。

## 最新调度覆盖（09-28 07:21Z）

- **NC流动性混合完整组合已结束，勿重复启动/训练。** 07:13:06Z batch rc0（763.936秒），07:13:08Z postprocess rc0；64新现金路径完成，2种子×32路径与不可变NC参考配对。经济收据sha `3b1ba37e1236720c488c038759227b13735f3c5d324cded1596c0d25a4f7f916`。源/输入/目标终态后复哈希同值；原参考本轮未重跑。报告 `RESULT_NC_liquidity_blend_cash_2026-09-28.md`。
- **判词 FOLLOWUP_CRITERION_NOT_MET（7/8），不换装、不扩固定规格。** 全窗条件回放夏普s42 1.784→2.328、s2027 1.858→2.657；但9月1–18实际复合收益−3.45%→−6.19%、−3.29%→−5.10%，深尾亏损次数增加。pre2026压力格s42 −0.194bps/日不通过；不得用全窗正值替代。2026主窗CI仍跨0，历史选优不获得独立确认。
- 分解确认：九月资金费节省4.8–5.0bps/日，价格贡献却恶化15.1–21.3bps/日；不能把“省carry”当净收益，也不能把评分/席位/连续状态同时变化的结果归因到一个组件。是组合配置试验，没有新模型训练/GPU；沿用409ea16镜像、合池成本、比例历史门、秒资金费现金接口，不是当前实盘认证，不替代早先1.22/1.44读数。
- **证据持久保存完成。** 不导入原统计模块的原始数组复算：128路径/1424数值核对，最大差2.86e−14。小ZIP118成员、大ZIP68成员（含64PATH）本地逐件size/sha通过；大件431133869字节，sha `7112f38edc8152cf5e456f2ca9cfb57bf6af983f0dc1d557cf8f371557c23e6d`，本机 `.codex/tmp/pod_archive_20260928/NC_LIQUIDITY_BLEND_CASH_PATHS_20260928.zip`。原Pod产物保留；无待等的batch。
- 07:20:50Z一次本地白名单轻读：生产仍d01e35db、`_mode=LIVE`/reduce_only=false/tripped_at=null；最近实际评估04:49:20Z无triggers/blind/unevaluated。不是新场所验收；16/20/00三恢复K1已完不再做。没有API/Telegram/resume/发布/杠杆或模型修改。08Z附近不做本地重活。下一研究不得把本次历史改善当近期修复；仍需真正针对价格尾部与连续库存训练目标，不重新扫本规格剂量/发布阈值，也不重复已失败的Ridge/FD队列。

## 最新调度覆盖（09-28 07:03Z）

- **NC流动性混合目标前置已完成、已归档，勿重跑。** rc0/439秒，原fund/LR/席位与两种子×两政策四组完整目标精确同；RESULT sha c05b2962。最低qvm档：2023–25候选增加约3–4pp，09-11..18却原/新都为0，近期主要移向Q4。因此成本空桶不能一刀否决候选，历史成本外推仍不认证。席位与发布次数也变了，不能只说调权重。详见`RESULT_NC_liquidity_blend_support_2026-09-28.md`；本机137.6MB目标封存5件全验，sha b89c3d3f。
- **唯一新在飞：nc_liquidity_blend_cash_20260928**。预注册f3e3d2e06，装置c4594a4b8，合同af84616a9，登记35a2b3870。07:00:22Z启动batch PID/PGID3589098 ticks514871579、postprocess3589099同ticks；根`/dev/shm/nc_liquidity_blend_cash_20260928`，源同名`_sources`。**绝对截止07:29:30Z**，合同sha d0813efaec93c0b32923edbf1e79acb9e2c2bd51edbdedc19bea6a4cf72b3814。2×32完整执行路径，无模型训练/GPU；只消费已封存目标，适配器往返和旧控制输入/代码/路径复核，先前控制不是本轮重跑。最终64路径+会计+逐年/双期配对+候选单边额外5bps固定动作压力+BOOK_DECISION自动接续。须看TERMINAL与POSTPROCESS_TERMINAL实际rc，不能只看engine启动。当前两个engine已通过资源门并开跑。
- 即使四个主窗均值与压力全正，只允许进一步成本/前瞻检验，不是发布批准；NC固定模型、历史选优、409ea16镜像与合池成本/秒资金费接口边界保留。没有已获批的新策略、没有部署/恢复/改杠杆。前三恢复K1已完勿重做。

## 最新调度覆盖（09-28 06:49Z）

- **唯一新在飞：NC流动性混合目标/成本支持。** 预注册094a62431（时间元信息在b97c376f6更正）、装置b97c376f6/c69ccd9bc、登记5f7e1071d。只测固定50% fund排名+50%滞后Amihud排名，两固定NC F10种子；重算fund LR/动态席位/连续组合，不是换分数沿用旧席位。原信号/原组合先精确复现，未读任何候选收益；不占GPU、不训练、不调场所。
- Pod根`/dev/shm/nc_liquidity_blend_support_20260928`，源码同名`_sources`。06:46:24Z启动控制器PID/PGID3587844 ticks514787838；子PID/PGID3587855 ticks514788357。**截止07:11:24Z，1500秒，8GiB子进程RSS上限。** 06:49Z子进程身份仍同，原fund分数/LR/席位已过、s42两政策完整数组已相同，尚非全部终态。每次检查PID和TERMINAL，勿再开同任务。
- 当前研究输入特征sha3c886a2b是主研究员09-25交接明确核过的干净NC分支，不是同名a490c294污染文件。仍保留NC间隔snap规则、固定模型/旧执行镜像等边界；本件是NC移植新规格，不冒充旧XIB数值复现，也不产生可上线判词。
- 06:46–47Z本地轻读executor仍d01e35d，watchdog `_mode=LIVE`、reduce_only=false、无tripped_at；04:49:20Z评估false/triggers/blind/unevaluated空，ALARM sha未变。root又用错state键，原null另存，按真实`_mode`另发更正收据；未将null当作状态通过。无resume/额外K1/API/Telegram/杠杆或模型变更。

## 最新调度覆盖（09-28 06:25Z）

- **liquidity_cost_probe已完成，勿重跑。** 预注册24ee54677、首版装置35109d05c；只对NC的qvm与实盘合池历史成交做成本诊断，无GPU/模型训练/策略收益。144锚源特征sha3c886a2b同既有NC；36,376唯一普通调仓、1,777,769.10U全部连接。报告`RESULT_liquidity_cost_probe_2026-09-28.md`，正式收据sha2c64c27c87754a4843428831b435af8201903471707dfe2fe98e2cc9a8892c47。
- **XIB尚不能由旧正效直接晋级。** 原实现是50%资金费排名+50%滞后一锚Amihud排名，不是相乘；当前模拟器按阶段用统一合池滑点，不看流动性。NC成员qvm最低四分位仅08-26/27有76笔，其后无成交；其余档成本跨段变化。这里只证明现有成本支持范围不足，不否定XIB，也不推翻所有旧研究；qvm不等于Amihud，不能误称已修成本模型。
- root自查首版bootstrap跳过空桶重采样，真实函数红控复现后改为整项CI UNAVAILABLE；原输出保留，修后点估计不动。9/9控制；导出每日分子分母独立算术差0。无候选经济读数、没有在飞训练。下一次若推进XIB，先固定NC完整组合构造并导出最终意图的成本人口覆盖；不得再耗时重复既有失败规格或直接套统一成本宣布突破。
- 06:21本地轻读实盘HEAD仍d01e35d，state LIVE/reduce_only=false，最近真实评估04:49:20Z tripped=false、triggers/blind/unevaluated空，ALARM sha fa4805…未变。首版light probe猜ts/eval_ts/blind键得到None，已按真实schema另存更正收据，未把None判故障或通过。授权三恢复锚K1已完不重做；没有新API、Telegram、resume、部署或改杠杆。

## 最新调度覆盖（09-28 05:45Z）

- **horizon完整组合已完成，不再等、不再重跑。** I/O恢复05:32:10Z rc0，后处理05:32:38Z rc0；64现金路径全部审计。见`RESULT_holding_horizon_full_book_2026-09-28.md`。模型未重新训练，通用终态的new_model_training=true元数据不准确，以MODEL_REUSE与29件模型sha为准。
- **FOLLOWUP_CRITERION_NOT_MET，不扩此规格DL、不换装。** SLOW−FAST pre2026 +3.421、2026JanAug +0.086bps/日，两CI均含0；SLOW−NC42/2027 pre2026 −4.184/−4.720，2026 −1.734/−0.909。六正均值只过两格；2024对两NC、2025对NC2027的CI全负。九月比FAST好、比两NC差。不能把弱对照改善当现书改善。
- **证据已持久保存**：小归档156件、模型29件、大NPZ72件逐件size/sha全核。大档案本机`/Users/haosiyu/.codex/tmp/pod_archive_20260928/HORIZON_REVIEW_LARGE_ARTIFACTS_20260928.zip`，sha36eac94f955740c034273676aa60e50214009902e6d1cc9757860c8e85b2ae0e；经济sha568b2617c6c82d5f00cb52b5e2b8bd111a3bef2d03890bd317c8084deafa9341。内部会计误差≤1.43e−14，不冒充场所现金认证。
- 05:33本地轻读实盘d01e35d、04:49看门狗false/triggers空、ALARM sha未变。04Z目标与模型身份核对同前。**本次只读排查04Z的39名reconcile告警**，这是名义缓存差异，不先认定外来单；不增K1、不调场所。没有部署/自动恢复/改杠杆。
- 原residual、score_book_probe、KSR、cap50、invvol、149窗inventory、D10 dryrun均已结束，不能再起旧队列。当前无本轮在飞训练；先解决实际告警证据，不因GPU空闲重复失败规格。所有研究收益仍保留409ea16历史镜像、scaled门等限制。
- **05:52Z对账提示排查完成**：恢复后三个区间312/311/312名、329/344/437笔唯一成交，逐名张数恒等全部精确0；4个完整OBSERVED快照、998重复行按(symbol,trade_id)坍缩。04Z日志只保留39超带名中的10名，样本价格均下降，但不能声称39名金额差全部逐项归因。告警测名义缓存差，文字beyond revaluation不构成已排除价格影响。独立4控通过，报告`RESULT_reconcile_notice_2026-09-28.md`。无新增外来单证据，不增加场所请求、不修改生产告警/风控。

## 前次调度覆盖（09-28 05:19Z）

- **horizon原批次关闭为GONE_WITHOUT_MARKER**：模型已封存，但attempt2控制器与两个子进程消失；两个TARGET_RECEIPT与steps文件0字节，TERMINAL未写。05:08直接写探针errno122证实配额耗尽，df整共享盘余量无效；没有原退出栈，不能伪造rc。原05:10:52Z到点结束，不算按时完成。只轮询终态未核PID导致迟发现，是root遗漏。
- **一次单列预算的I/O恢复在跑**（cab55f4a9预登记；源码2e3f96601、合同749e5ad26；registry9f0a1dee8）。05:17:26Z启动，根`/dev/shm/horizon_book_io_recovery_20260928`，源码同名`_sources`；PID/PGID3581618、ticks514254034，后处理3581619/ticks514254035。**截止05:40:00Z，不再续跑**；合同sha213331abb24f315b2c551409c20064b2870d756596cb726ffa2ab392389320ff。仍原两模型/预测/标签/判据、无重新训练、无GPU；输出临时盘，须本机归档验sha后称持久保存。每次状态查PID/start_ticks与终态，不能只看无终态。无经济读数前的资源例外，明确偏离原45min预算，不声称原预算通过。
- **Pod清理已实做**：交接`HANDOFF_alloc_2026-09-27.md §5`已结题M输入与红控NPZ共82文件，1,365,205,284字节；全部原字节先归档本机并逐件复哈希再删除Pod副本，所有JSON与恒等基线保留。归档`/Users/haosiyu/.codex/tmp/pod_archive_20260928/ALLOC_closed_artifacts_20260928.zip`，sha9d5bb5d46b68292e69bcde88fa6e433a64f34dfc301daead6fb42fcc52377d56，必要时按manifest还原原路径。05:17:46Z workspace写+fsync已恢复；仍近配额，后续任务不可凭df放行。
- **04Z已done04:58:35Z**，无跳闸/停机拦单，模型实物两钉同、执行器d01e35d配置等HEAD；321名PARITY逐位0差，到位99.618%，合池taker21.1%、费2.63bps。7项本地检查PASS；报告04:55:05Z早于done，严格报告门PENDING；新K1未请求（授权三恢复锚已完）。不宣称9/9；未额外发Telegram。position reconcile 39名告警是现有读数，未据此推导外来单。杠杆2倍、无部署/恢复。

## 前次调度覆盖（09-28 04:41Z，优先于下文旧队列）

- **horizon试验现为attempt2，不重复训练。** 首批04:28:16Z训练两模型完成；04:28:26Z组合main缺少新完成状态白名单而FAILED，尚无现金路径。schema路由测试漏了第二个入口断言，是root自己的接口遗漏。8eef1607f修精确状态，真实main AST旧红/新绿，18测试通过；不接收泛化PASS。首根/模型/源码保持不变。
- **04:37:26Z attempt2启动**：PID/PGID3578724、ticks514014035；自动后处理3578725、ticks514014036。根`/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/horizon_book_20260928_attempt2`、源码同名`_sources`。合同sha591231f099274a70fb3ce5451875ba10d3af58b858d8aba506677a8b042a8312；**原截止05:10:52Z不延长**。所有模型/折/依赖重新复哈希、通过MODEL_REUSE指向首批封存模型，没有重新拟合；两连续组合→64现金路径→经济/预测诊断/判词/归档自动接续，须读取实际两个终态而非以MODEL_DONE宣称完成。
- 固定48h标签训练缺测剔除比例2023/24/25/26折为0.444%/0.185%/0.100%/0.061%，FAST与SLOW严格同人口；未来测试标签变异不影响训练行或值。此为训练合同证据，不是收益证据。原score_book_probe、残差整书及其他旧试验已关闭勿重复。
- 04:33轻读无新增ALARM或跳闸；04Z尚未done。04Z目标身份两钉已核同；前三恢复K1不重复、不增场所调用、无部署或改杠杆。

## 前次调度覆盖（09-28 04:28Z）

- **score_book_probe已完成勿重跑**：04:11:55Z rc0，36.39秒/929MiB；RAW/RESID/NC42/NC2027各8142锚目标全逐位一致。报告`RESULT_residual_score_to_book_probe_2026-09-28.md`（8310d4329），registry f2a74930b已关闭。2025残差新目标价格代理较高，在EMA阶段首次落后RAW；九月最终组合资金费排序载荷四组接近。仅同步原价标签诊断、非现金因果证据；不重开已判负加速交易、不撤销残差整书失败。
- **唯一新在飞horizon_book_20260928**：预注册711bc7945、装置93250c364、登记f9205e7d0。04:26:39Z启动PID/PGID3577692、ticks513949303；后处理3577693/ticks513949304。根`/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/horizon_book_20260928`，源码/日志同名`_sources`。**绝对截止05:10:52Z，不续期**；合同sha001696ca610b091eae06492fbf28bfc1078f30cb742ef8a97c97d1d0ff9db8ae。FAST下一4h与SLOW固定48h衰减价格标签，配对相同stride12不重叠训练人口、60锚标签端点隔离、同171特征/Ridge；不改alpha0.1、资金费/席位/组合/执行。CPU无GPU；自动两完整组合/64路径/经济表/双口径预测诊断/判词/封存。15测试绿、两真标签变异红；初次tar仅权限元数据返回非0，已改zip并重跑精确版本通过。模型完成不是整书终态，不重复起跑。
- 04Z目标1790568000.json现已落盘，King/F10与在役配置钉分别相等；target sha7363e4a5a417a3eb641dd551644b6acbec6522fde827120f772726d05c4c4591。仅本地身份核对，不是首锚验收。04Z已确认04:00:06Z启动。04:22本地轻读watchdog最近仍00:48:03Z false/triggers空，ALARM sha未变；未声称04Z验收。恢复三锚K1已完不重做。用户未答临时1倍提问，保持2倍；无部署、场所调用、resume或Telegram。

## 前次调度覆盖（09-28 03:54Z）

- **残差完整组合试验已终态，勿重跑或继续等它。** attempt2 03:47:27Z rc0，1014秒，训练86秒、64路径模拟约872秒；postprocess03:47:31Z rc0。封存152件逐件复哈希、82件大NPZ路径/sha已登记；归档sha `03df64894b267ec983de2dc8cf062cd19242f0b9102f53eddcf1d75400ec6417`。报告`docs/RESULT_residual_model_full_book_2026-09-28.md`。
- **FOLLOWUP_CRITERION_NOT_MET，不继续此规格的DL扩大训练/不换装。** RESID−RAW pre2026 −1.994、2026JanAug +0.816bps/日；RESID−NC42/2027 pre2026 −3.562/−4.098，2026 −1.619/−0.793；六正均值条件只过一格。2025相对NC2027 CI全负；9月三比较均恶化。排序改进未变成整书改进；2025主差价格−6.037、多付资金费−1.535，省手续费+0.076bps/日。HOLD路径也改变，不能据分解断言唯一原因；不否决全部残差/DL家族。
- 40窗会计重算最大误差5.33e−15bps/日；8诊断/判词控制Pod重跑绿。首轮数值失败保留，不能写成一次无故障通过。当前无本批运行进程须等待，不因GPU空闲重复已否决方向。后续研究仍须先冻结新机制与预算。
- 03:53:42Z仅本地轻读：实盘d01e35d，看门狗最近00:48:03Z false/triggers空，状态LIVE/reduce_only=false，ALARM sha未变；这不是04Z验收。前三恢复K1完成不重做。04Z附近不跑本地重活、不额外调场所、不部署/恢复/改杠杆。

## 前次调度覆盖（09-28 03:32Z，已被上文取代）

- **residual实际在attempt2，切勿拿旧根失败当新任务失败或重复启动。** 首轮03:27:53Z数值警告触发人工SIGINT，控制器finally清理自有子进程，终态rc1，未读任何候选书层数字。float32共线系数合成反例误差1.81%，双精度修后10/10本地及Pod通过；遇后续LinAlgWarning即拒。修复498e91ad5→10f55e8ad，不改alpha/人口/折/标签。
- **03:30:33Z attempt2已启动**：PID/PGID3572799、ticks513612713；根`/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/residual_book_20260928_attempt2`、源码同名`_sources`；合同sha872e0ff46af6b30241731515242f6f832d2dbf77289ca4572159d8e944cb560e。**截止仍04:08:45Z，不续期**。见数前计划末节记数值修订，旧失败与当前LAUNCH/CONTRACT都在RESIDUAL_BOOK_20260928/attempt1、attempt2。

## 前次调度覆盖（09-28 03:26Z，实际在飞身份以上文为准）

- **invvol已完成并关闭登记，勿重跑**。报告`0374ffb66`，registry关闭`efb88aa5b`；64路径审计通过，03:11:34Z rc0、1116秒；归档107件复哈希。全史Δ−8.764/−8.903bps/日，两CI均低于0；2026Jan–Aug回撤改善，但2024/2025与9月恶化，拒绝此规格不部署。见`docs/RESULT_inverse_risk_complete_book_2026-09-28.md`。席位还把2023–25许多HOLD改为发布，不能说纯风险权重效应。
- **唯一新作业residual_book_20260928**：预注册d89788736、源码943f3c741、登记bd6f80f06。03:23:45Z启动PID/PGID3572046、ticks513571889，绝对截止**04:08:45Z**（2700秒不可续期）；根`/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/residual_book_20260928`，同名`_sources`有CONTRACT/LAUNCH/controller.log。先核旧恒等与所有基线PATH，然后RAW和RESID两确定性Ridge→两完整组合→64执行路径→自动经济表。不是两F10种子，不是DL换装；训练仅CPU2线程，资源门24GiB。上游MODEL_DONE不是整书完成，须TERMINAL rc0和ECONOMIC_FULL_BOOK。输出见数前冻结，主对照RESID−RAW，两者分别对NC42/2027辅助；不据IC宣布获益。
- 启动前独立复核与修复见`docs/REVIEW_residual_book_prelaunch_2026-09-28.md`。当前配置绑定原成功控制12项PASS；9纯测试Pod绿。没有GPU占用，不重复原基线全跑，不再次启动相同任务。
- 03:24Z轻读生产HEAD仍d01e35d、watchdog false/无triggers/reduce_only=false；未做任何部署/自动恢复/场所请求。前三恢复K1已经完成，不重复。用户降杠杆提问未答，保持2倍。不能用新研究代替风险裁定。

## 旧调度记录（09-28 02:54Z，已被上文取代）

- **cap50已完成并关闭登记，勿重跑。** `e244faa87`报告`docs/RESULT_cap50_complete_book_2026-09-28.md`；64路径全过、两完整基线身份逐字节相等，02:45:12Z终态（1227秒），经济读数15.8秒/sha `da1ac29a837849e085e2f37d14644b98448dcfb34bf8549c91de9e7d5155addd`。两种子2024与2026Jan–Aug回撤改善，2023H2/2025均值恶化；Sep1–18多亏0.7–0.9pp、价格项变差且手续费升。风险取舍，不是近期亏损方案、不部署；主要年度CI均含0，不称非劣。完整JSON/判词在CAP50_ECONOMIC_20260928。旧现金秒接口、409ea16历史镜像局限保留，不升级当前实盘认证。
- **唯一新在飞：book_invvol_20260928**。见数前登记`9332a8a20`、代码`b341dd202`、registry `15deddf2c`；只测已有`inverse_vol(LR,look=900)/shared`，不用收益均值、不同于固定50%上限，不扫参。02:52:57Z启动PID/PGID3569357，ticks513387118；绝对截止**03:22:57Z**（1800秒，不能续期）。根`/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/book_invvol_20260928`，源码/控制器日志同名`_sources/`；终态`TERMINAL.json`，模拟先终态`SIMULATION_TERMINAL.json`，经济表`receipts/ECONOMIC_FULL_BOOK.json`自动串行生成。02:53Z源及父收据/64基线PATH复哈希通过，三个未来扰动控制true，候选组合两种子已启动；暂未有候选数字。不得另起同任务。原第一族判词不变，此为探索性风险比较。
- 02:39Z最新轻读实盘仍无新增跳闸，last_eval仍00:48:03；ALARM sha `fa4805173b18fbb79cbfdbaf0ea4c55f5adc156ac7a1b63b3e008308494d16c7`未变。不重复前三锚K1。用户暂降1倍提问尚未回复，维持2倍，不按默认选项操作。生产未部署。

- 用户明确指出工程小步循环太慢、Pod空转。暂停clock新训练代理、重复FD/F0/单步与KSR H2；不要因下一次heartbeat再启动这些旧链。KSR最终REJECT，D10演练已完成但仍UNDECIDED。恢复16Z/20Z/00Z三个K1均完成，不再重复；00Z唯一红为合池taker比例，未放宽门。02:21Z本地轻读d01e35d、watchdog false/无triggers/reduce_only=false，未部署。
- cap50历史：预注册bc3dc1127、实现652c89b7f、路径修复e3f402e13。首轮02:20:38→02:21:43在producer相对路径查找时失败，无候选数，失败原件保留。attempt2输出根为上述`book_cap50_20260928_attempt2`；经济读者`01710f19c`。已完成逐年/尾部/费用1.25倍会计敏感性，不要下一heartbeat又补跑同一件。
- 149窗inventory于02:13:31Z完成，14.84秒/249MB/无GPU：原149接受+6拒绝复现，当前149标签支持，126窗在组合原点之后、23窗在之前。状态未建，不宣布可训练；归档TRAINING_PREFIX_INVENTORY_20260928，登记已39f16936f关闭。后续不以此继续工程循环。
- 已向用户单独询问研究期间是否临时降至1倍杠杆；**尚无回复，原2倍保持**。不要把问题本身或默认选项当授权。研究不能承诺覆盖实时风险。实盘修复仍须safe_commit/全电池，历史disposition真实红不得用清账或降门绕过。

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
- 19:03Z root独立运行输入小包读取器六项合成正负控全部通过（3468f4cba，worker SHA5b9f69c6…）。另明确两项后验身份补核：复制的三个目标NPZ须消费原封存SHA，μσ来源的fold receipt须实物复哈希而非只把预期SHA写进输出。input-only运行已启动，原在飞源码不改，完整网络尚未运行。
- 19:06:58Z KSR进度按原ORDER文件SHA0e6c225d…逐个核：36个应有候选产物中23个文件存在，最新mtime19:01:23Z；这仅是落盘进度，不是23个验收通过，候选数值和判词未读。前一次按猜测前缀KSR_查到0文件不作结论，正确文件前缀是SER_且以ORDER逐项为准。上游仍无DONE，继续既有等待器，不重复起跑。

- 首120真实输入包已完成：19:02:42–19:03:08Z、CPU1、RSS/HWM峰688369664B、26.25秒；只做输入整理，未运行候选网络或optimizer。6项读取器控制通过，归档93fd499d0。root另从Pod逐文件重算22个产物的53,475,791字节，全部SHA和打开文件身份吻合（ROOT_FIRST120_INPUT_PACK_20260927.json，19:11:30Z）。三个原目标与实际fold receipt/μσ来源及7份训练源码另经postverify，终态1正6负控闭合；不把原OOF的9次发布当新checkpoint的发布次数。
- 下一件为完整120锚网络forward/backward实现验证：沿冻结202608 checkpoint、原μσ和当前ad80特征，连续组合状态、HOLD数量与事件库存现金。代码准备中、尚未启动；这仍是样本内工程检查，不是正确输入重新训练或OOS改善。F0数值相同但字节hash不同的开放项保留。主仓STATE顶部19:17Z仍未变，无主研究员接回。

- 19:30Z root复核full120最终源码8422dc61f、6项stdlib正负控与实际依赖/初始状态门，通过后批准唯一无optimizer尝试。19:31:36Z guard在0.119秒即RESOURCE_REFUSED：cgroup余量14,193,893,376B低于冻结14GiB门15,032,385,536B；UID RSS与GPU空闲门通过。worker未出生，未加载网络/反传，未生成COMMAND/PID/WORKER_RESULT；root远端独立核源与终态于ROOT_FIRST120_FORWARD_REFUSED_20260927.json。不是模型或梯度失败，不降低预算、不换目录重试、不新建等待器。
- 19:30:26Z KSR/修后读数器/D10队列三个PID与start_ticks均核同，无终态。19:31:27Z本机轻读生产仍d01e35db、代码区diff空、King/F10 pin与在役匹配、M3 shadow；watchdog最近16:49:42Z仍LIVE/false/null且trigger/blind/unevaluated均空。这是既有16Z状态，不冒称20Z验收。主仓STATE没有接回通知。

- 20:00:05Z执行器已按LIVE启动20Z锚；20:00:09Z轻读生产HEAD仍d01e35db，watchdog仍为16:49既有正常读数，不能据此验收新锚。未调场所、未做本地重活、未resume。21Z且真实done后才用既定包装器验收。
- 20:01:03Z KSR与两个等待器PID/start_ticks核同；KSR原ORDER的36候选中27个文件存在，最新mtime19:51:18，未读数、未称27个通过；D10仍等KSR。root纠正自己前两次轻探针的marker位置：实际DONE在workspace根的DONE.json，FAILED在/dev/shm marker_root的FAILED.json（不能查裸DONE/FAILED或只查workspace）；本次按源码逐一核均不存在，实时wait日志也证仍RUNNING。此纠正不改既有等待器代码。收据ROOT_HEARTBEAT_20260927T2001Z.json。

- 20:30Z轻读：20Z生产快照已于20:20:13Z PARITY，321名权重逐位相等；watchdog尚未形成20Z判词，仍为16:49Z。有限尾读未包含start行，不能把空的lifecycle筛选读为漏锚，20:00:05Z的真实start证据已在上一收据。完整验收及K1仍等21Z且done。Pod三个PID/start_ticks核同、DONE/FAILED实际路径均无终态；原ORDER中30/36文件存在，最新20:26:04，仅为落盘进度。没有重启首120被拒作业、没有额外场所读取或部署。收据ROOT_HEARTBEAT_20260927T2030Z.json。

- 21:02:35Z **恢复20Z完整验收完成**：20:58:35Z真实done rc=0之后，在21Z静默窗执行已审核包装器（最终SHA `d64017daf8fcca64774d228aa3d0d8cbd4d63c42d5b8601b3004ebf4c76019c5`，取代上文17:19的早期包装器SHA），9/9 PASS；VERSION_PROBE / M3 shadow / 321名逐位PARITY / B4合池分别PASS。目标gross212,015.23，实际212,221.27073，到位100.097182%；停机门拦单0，新HIGH0，watchdog明确false/null/LIVE，无再跳闸。King/F10实物、目标携带值、执行器pin一致，生产仍d01e35d、M3仍shadow。
- K1本轮范围RID `A1790540640` 前600秒至21:00:46.056Z，211名、329笔成交，未知外来订单0；合池taker份额27.6%，场所与账本相符。只证明commission命中的成交订单及该查询窗，**不证明全局单写者**；没有追加场所调用。按用户计划下一次且最后一次恢复K1是09-28 00Z，须等01Z静默窗与真实done。
- 20Z收据存 `acting_lead_2026-09-27/receipts/RECOVERY_20Z_20260927/`（10份+MANIFEST）；root在归档前重新核了判官所用全部原始文件sha，含当时watchdog state副本。大日志留独立临时目录且sha已绑定。定时报表早于done，保留原件；仍只用gather/build_report纯读生成收尾后报告，无生产文件写入、无Telegram。
- 21:00:48Z Pod三个PID/start_ticks核同，KSR原ORDER的32/36文件落盘、最新20:58:01Z；实际DONE/FAILED路径均无终态，D10继续等KSR读数。收据 `ROOT_POD_20260927T2100Z.json`。这是文件进度不是候选通过数；不读未完成收益、不重复启动等待器，不重开RESOURCE_REFUSED的首120作业。

- 21:30Z：KSR34/36文件落盘，最新21:22:39Z；三个PID/start_ticks均核同、正确路径无终态，D10继续等待。生产d01e35d代码区diff空，20:47:46Z看门狗false/null/LIVE，ALARM与20Z验收逐字节相同。历史条件partial仍具名：cond2八个划转日排除、cond4的08-29缺target_gross；没有把恢复锚PASS扩大为历史现金链完整。首次轻探针猜错ALARM路径，随后按已审wrapper的watchdog/ALARM.log重读核同，未把缺文件当空。无额外场所读取、无新作业或部署。收据ROOT_HEARTBEAT_20260927T2130Z.json。

- 22Z：KSR全36格及原读数器已终态DONE（21:56:09Z），root实物SHA与38/16/11输入绑定核同。后处理先因自己过宽的finite合同拒绝结构性LR预热/未闭合尾行；依据钉住的nc_legs源码与ready轴修验收器，原失败保留，15/15控制通过，实际重跑5.18秒/175MiB/rc0。8成员首差均恰2023-10-01，轴/切换点相同；没有填0、改候选或移动判据。修复提交f3cf14d2c。
- **KSR最终按冻结门REJECT，不换装**：2023四季度整书差−4.502 bps/日，95%区间[−6.373,−1.126]；三主窗合并−1.468[−3.662,+1.029]；2026-07..09-18为+1.363[+0.600,+2.796]也不能抵消历史拒绝。IC+0.012/z6.35仍成立，但不是收益转化。2023负差主要为价格−4.514而非费用；预选m0两F10种子的COMP和SEAT通道都负，不能简单归因席位或F10。详见RESULT_acting_KSR_complete_2026-09-28.md及KSR_TERMINAL_20260927归档。H2未跑、m0不代表八成员、IC/书2026端点不同、逐PATH历史身份缺独立回查，均具名。
- D10既有队列已接受KSR DONE但实际仍WAIT_RESOURCE：22:11Z cgroup余量18.13GB低于28GiB；GPU空闲不等于可开跑。查明约22GiB tmpfs历史文件占用。正在准备只迁移已完成历史单链接文件到持久盘、校验字节并保留原路径，不改D10预算/输入/等待器，不drop共享缓存，不重复起跑。生产22Z仍LIVE/false/null、ALARM与20Z逐位相同；00Z验收留01Z。

- 22:20:53–22:22:50Z Pod资源阻塞已实际处理：706个已完成历史单链接文件共13,933,310,928B迁到私有持久盘，每件复制fsync后独立复哈希、日志确认、原路径原子换成symlink并再次复哈希；原字节保留，未删训练证据。root另核706映射/大小/prepare-commit配对均正确。路径`/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/tmpfs_archive_20260927T2230Z/`，标签2230不是开始时间；日志真实时钟如前。仅新建私有副本做fadvise，未清共享cache。7/7 Linux控制通过；初次控制因无能力的其它UID nginx的/proc不可读而拒绝，随后明确只核可写主体，未声称全系统无读者。
- **D10原队列22:22:48Z已启动真实runner3548735**，先通过原28GiB/4GiB/4GiB资源门及211pin；没有调低预算或另起任务。D7名单80文件IDENTICAL、D8自检PASS，D1毫秒资金费账本重建已OPEN；仍在执行，不是全链DONE，也不是训练/换装已批准。归档资源门/进程身份与迁移原件位于`receipts/tmpfs_relocation_20260927/`，registry已逐项关闭KSR与迁移、更新D10。

- **D10原队列22:30:40Z已完成**：15项真实执行，10 IDENTICAL / 2 PASS / 3 IDENTICAL_EXCEPT_DECLARED，无NOT_RUN。root独立核215个pin、11份子收据及八个新旧NPZ共6.558GB的字节；四个新产物均与原件SHA相同。`D4b`实际子门仍为PARITY_RED/rc2，终态IDENTICAL只表示复现该红判词，不能写成生产平价通过。即时费率2742554格全同；新间隔政策的EMA334910格不同（1934格abs>0.001）、间隔39格各差1h。原UNDECIDED及冷静期不变，无新训练或换装。报告`RESULT_D10_input_dryrun_2026-09-28.md`，归档提交72bf99de4；registry已关闭，不再重复演练。
- **KSR交回机制实际重建完成**：从2023-01-01原零状态按原Python/源码重算BASE/COMP×两种子，各4740锚发布与编码gross对原存档完全相同，112.4秒/448528KiB。2025-01-01当前King分数、F10、席位和其它输入相同，但s42基线gross0.3844924017不过0.4、COMP0.4029288540发布；差落在继承的King组合状态，F10侧gross相同。s2027两边仍不过门。三次交回的完整一/二月均报告，不以2025单窗晋级；不能把HOLD目标零当空仓，也未归因全部现金差。报告`RESULT_KSR_handback_state_2026-09-28.md`；原始结果SHA bad781c0…，registry6452efd52关闭。KSR仍REJECT，未改生产或门。
- 22:47:21Z最新生产轻读：d01e35db代码区diff空；20:47:46Z看门狗false/null/LIVE，triggers、blind、unevaluated空；ALARM仍fa480517…与20Z验收相同。旧cond2/cond4历史partial照留，不把恢复PASS当全史完整。主仓STATE仍是13Z恢复记录，无接回。下一恢复K1只在09-28 00Z真实done后01Z静默窗跑既定f69b0020包装器；本轮未调用场所、未resume、未发Telegram。

### 下一步，勿重做本轮终态

1. 00Z恢复验收照原计划；16Z/20Z完成，不再重复K1。GAP4与M3仍被历史disposition FAIL挡住；资金费durable修复已封存，不能绕过发布门。
2. King机制已定位到连续状态与发布门的一条具体路径。先核已有发布门/chain实验范围，再决定最小状态干预；不重新扫0.4阈值，不把“修后当前输入相同”当作整书状态相同。
3. D10输入演练已结束。下一研究需区分D10改变的间隔政策与已干净的NC基线，先闭合训练目标的执行时钟/连续库存合同；首120资源拒绝及F0字节未决不借新名称重复。没有新的可部署更优策略。

## 23Z接续：显式追加预算及真实终态

- 23:00:25Z生产轻读与22:47Z完全同状态：d01e35d、代码diff空、LIVE/false/null、ALARM hash不变，未调用场所。主仓STATE未接回。00Z验收仍留01Z实际done后。
- root依据持续推进授权，**显式修订先前不续期的自设预算**（不是把旧失败改为通过）：3ce73a264追加90秒，仅定位原F0两控制步。23:04:23Z rc0、峰RSS830MB、无CUDA，原两whole hashes完全复现，只有未用于书的`a`梯度+0/−0不同；loss/更新参数/optimizer/分项字节相同。原全对象严格门仍false，但原因已定位；原超时原件保留。报告`RESULT_F0_byte_identity_2026-09-28.md`，完整状态亦已归档，不再重复F0定位。
- 9c7542468另批300秒无optimizer首120通路，原因是KSR/D10完成后资源已释放；原14GiB/6GiB/8GiB各门不变。**未成功**：23:07:35Z WORKER_FAILED/rc1，0.287秒/GPU0。root复制时只改guard输出、漏改worker硬编码OUTPUT，进入数值代码前被拒。原失败不覆盖，registry已关闭；不是模型或输入数值失败。
- 该配置缺陷已在独立源码修复，并在guard的源SHA验证之后加guard/worker输出一致性门。两条新测试修前1FAIL+1ERROR、修后共8/8通过；本轮不再次跑网络。下一次若执行须明确新预算、保留此次失败，且先核修后两端与实际输出合同，不能把“6项源码绿”当作整链能运行。所有候选判词与生产均未改变。

## 23:29心跳接续：首120通路完成，训练代理差异须先处理

- 23:34:30Z生产轻读仍d01e35d、代码diff空、LIVE/false/null，ALARM fa480517…未变；主仓STATE未接回。00Z完整验收仍留01Z且实际done后，未额外调场所/Telegram/resume。
- 新300秒pathrepair分配f622b78a5进入输入后于23:35:39Z拒绝：root新proxy把累计log表当绝对价。23.4秒/RSS820MB/GPU0，无模型执行；失败归档，不把负log误称市场缺价。原FullPanel已有正确转换，旧认证现金控制不受此错误影响。
- 单位修复1cd2e2d5b：复用钉住FullPanel并加类型/轴/参考/UA边界门，3个旧解释红控、新10项绿，集成18/18。真实940578价格格与独立公式相对误差≤4.14e−16；3836120未知保留，9104事件现金控制≤8.63e−12USD。本窗UA0；以后出现UA则proxy拒绝，不暗中补价。
- 显式新预算d34f6838d保留原失败、输入、窗和资源门，23:46:57–23:47:39Z完成完整120网络forward/backward；RSS2.05GB/GPU0.679GB/42.02秒/rc0，参数前后hash同，optimizer0。20输入复哈希未变，32原件root归档核同；所有registry任务已关闭，勿重跑F0/价格/已完成通路。
- **冻结梯度门仍UNRESOLVED**：eps1e−4的9分项全核过，eps1e−3全部跨producer/fill_sign分支。不能丢大步长宣称通过。硬映射对原连续实现≤3.47e−18且发布原因相同；同一固定checkpoint的缩放历史门硬发布30/120、soft-rank代理90/120。下一件先做全120锚硬/软层首差和尺度机制，不搜发布阈值，不把soft结果当整书收益。当前Jan2023+202608checkpoint仍是实现检查，不是OOS或正确输入新重训。
- 报告RESULT_first120_network_clock_2026-09-28.md；实际结果SHA88eb9cc7…；两套完整归档FIRST120_PRICE_FIX_20260928、FIRST120_NETWORK_COMPLETED_20260928。GAP4/M3历史电池阻塞及D10未决/冷静期全部照旧，本轮没有部署。

## 09-28 00Z接续与用户亏损追问

- 00:00:05Z实盘锚按时start；00:17:12Z combo ok/anchor1790553600。00:19:52轻读仍d01e35d、代码diff空、watchdog仍20Z false/LIVE、ALARM hash不变。**00Z未完成，不提前验收，K1仍等01Z静默窗且实际done。** 主仓未接回。
- 用户问核心进展及持续扩大亏损。root从同account-call的16:47:51→20:45:56读回及329唯一成交(坍缩286重复)独立拆最新损失：NAV106043.12、窗差−1019.21(−0.952%)；309共同人口数量全闭合，原多头+190.02、原空头−1195.54、原平名+1.41 USDT；155原空头129亏，期间无跨方向。覆盖起点100%、终点99.886%gross。3个不配对名字不补0；共同价格与账户价格差0.15975、NAV桥接另余1.64923具名未解释。手续费3.06、资金费13.87。**确认本窗空头篮子普遍上涨，不足以归因全月/每条模型腿；执行相对意图贡献也未重估。** 详见STATUS_core_progress_and_latest_loss_2026-09-28.md及LATEST_LOSS归档。
- rank-action机制原形完成(8447db73a)：同排序的×.1/×1/×10令soft发布113/90/41，hard全30。**交叉读旧T3源码后确认root新proxy漏了既有标准化，不能据此指认现役训练。** 已立即告知用户归属，保留原形及post-read ROOT KeyError失败。新修订fab831b78先冻结，normalized源码a97cefeb4，经修前真红、修后6/6与真120锚复跑，00:23:04Z rc0；全部正尺度/平移soft都35、hard30，30共同发布/5soft-only/85共同HOLD。硬与原continuous≤3.47e−18、frame tracing不改输出。
- normalized测试26.24秒/RSS1.355GB/GPU0.463GB，参数hash前后6cf9079f…相同、optimizer0。**原raw双eps梯度UNRESOLVED不得因修正标准化或动作更近而改PASS；新图尚未做完整参数FD。** 本窗样本内工程不报收益，不当新训练。完整旧74件/新39件归档root校验；三个registry条目均closed，无在跑研究任务。
- 下一研究：按修正后的标准化核新图梯度/完整硬动作，不重复F0/价格转换/原形尺度测量；逐笔损失已定位方向，接着核这些真实空头的因果fund状态与组合状态。GAP4/M3仍历史电池真红、durable包未部署、D10UNDECIDED/冷静期；勿把研究工具修复当成盈利或发布。

## 09-28 01Z：末次恢复验收与真实信号接线

- 00:58:35Z真实done之后，01:00:05–01:01:57Z按f69b0020包装器完成最后一次计划K1。**8/9 PASS、总体FAIL**：唯一红是合池taker49.7%超近期42%线；VERSION_PROBE/M3 shadow/320名精确PARITY/B4通过。到位99.080801%、未知外来订单0（212名344成交范围）、halt0/HIGH0、watchdog false/null/LIVE。未降门、未再resume；16/20/00三个K1均已执行，非新事故不再自动续查。原件在RECOVERY_00Z_20260928。00:46:12.682Z NAV105975.45，合池104条post-only拒绝、其它初次拒绝/限频0，费用3.49bps与合池构成相符。生产仍d01e35d代码diff空。
- 实际完成16Z事前信号桥接（固定309共同名/155原空头）：发布组合状态与源KC重算均全轴误差0。153空头fund秩负，但132最新费率正、124EMA正，末结算全在16Z；本窗不能只用极端负费率尾巴解释。King/fund同负84名亏867.45、King正fund负69名亏326.05；这是分组损失，不是独立腿因果贡献。共享fund席位61.18%，非线性前有效系数King21.35/F1017.47/fund61.18%。KC131名受带阻止更新，但当锚新目标仍有130名空头，不能据此推去带或加速盈利。F10逐名原打分缺测，未从权重反推。详见RESULT_recovery00_and_live_signal_bridge_2026-09-28.md和LATEST_LOSS_SIGNAL归档。
- 宽截phase_A曾意外看到嵌套requote字段，未转述臂内数/未用于臂比较和政策；后续白名单仅存合池，不声称执行诊断全程严格未见字段。CFG判决仍停止点原装置。读取猜键/phase错误和源码传输缺rsync已如实记录。
- normalized新图FD于01:10:18Z完成45秒、RSS2.04GB/GPU0.679GB、optimizer0；小eps9/9同分支，大eps仍跨producer/fill_sign，双eps门**UNRESOLVED保留**。30pin与17原件root复核，registry关闭。报告RESULT_normalized_network_gradient_check_2026-09-28.md。无在飞研究作业。
- 下轮只增量核实盘，无异常不重复K1或已完成FD。研究须把共享fund低秩篮子与独立模型信号分开，若继续T3先定义门内梯度/门外硬动作两类验收；不删旧UNRESOLVED。GAP4/M3历史FAIL、durable未部署、D10未决与冷静期均原样。

## 09-28 01:29心跳：完整120锚双臂一步试验

- 主仓未接回。01:45本地轻读仍d01e35d，最新评估00:48:03 false/no triggers，reduce_only=false、ALARM未变；不重复K1，不调用场所/Telegram/resume。
- 新预注册446d8a71a、源码cf6d7c51e、登记a65aa0552；01:39:54→01:41:10Z完成固定120锚4次独立单步AdamW，76.10秒/RSS2.134GB/GPU0.661GB/rc0。严格F0的loss、gradient、model、optimizer字节完全一致；每次硬映射对原continuous≤3.47e−18。29pin和32原件root独立复核。注册已8226fbdde关闭，无研究作业仍在跑。
- **新发现：A0/A1单步均令soft35→0、hard30→0发布。** 不是score常数化：KC不动、FC增大但与KC更反向，混合gross最大.45326→.37593，120/120落到.4门下。loss归0来自空仓原点一直未建仓，不能称利润或carry有效；属于本次新训练代理，不是已证明的在役F10缺陷。
- 见数后固定接缝(原点首次发布+1=index63)的独立库存核查：保留144名数量再HOLD，57锚价格−304.129/carry−2.389代理NAVbps；错误重置数量则全0。硬cash实现正确保留数量，不能把全HOLD当自动避险/平仓。非生产者隐状态一致反事实，不作策略收益。
- 报告RESULT_clock_paired_update_probe_2026-09-28.md。工程实施PASS不关闭原双epsUNRESOLVED，不放行完整训练/换装。下一项是原149训练窗的因果前缀、生产者状态和库存支持域清单/资源预算；**勿重跑F0/单步/FD去调到过**。真实学习不得每窗清空账户后以零损失假改进。GAP4/M3历史FAIL与D10未决/冷静期仍原样。
