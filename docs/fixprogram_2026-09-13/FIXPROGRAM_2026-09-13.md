> **创建:** 2026-09-13 12:5xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 执行中(第一优先) | **作废条件:** 无; 只追加

# 已知问题修复纲领(用户字 2026-09-13 20:5x SGT: 「所有已知问题的修复不用等我裁定, 既然是问题, 就要最严谨的修复, 每一项修复完之后产出完整的提交链和报告, 独立研究员复审。这是第一优先。」)

## §0 规程(每一项都走, 不缩水)
1. **事实表先于代码**: 逐版本读码 + 真数据定位缺陷与所有同族位点; 事实表入库。
2. **红先**: 用真实形状(真账本行 / 真锚)写能在旧码上变红的测试; 旧码红日志留档, 且须是「因对的理由红」(不是缺夹具、不是崩溃)。
3. **修**: 最小正确改动; 同族位点一并; 旧断言逐字保留(AST 核); 每修一格测三个邻格 + 原链。
4. **全电池 / 回放**: 执行器改动在干净克隆 + 真 state 副本跑全电池; 生产者 / 书行为改动在生产路径回放装置上配对比较(同输入同执行钟), 并过平价正控。
5. **提交链 + 报告**: 克隆内逐项提交; diff 入研究仓 `docs/receipts/`(sha); 报告 `docs/fixprogram_2026-09-13/REPORT_<id>.md`(问题 / 事实表 / 红证据 / 修法 / 测试 / 电池或回放 / 未证边界)。
6. **独立研究员复审**; 复审通过后按既定落地规程部署(执行器: 非锚窗 safe_commit; 生产者: 换装事件 + 首锚验收)。
7. **声明纪律**: 收据先于宣称; 前台运行留 rc 与汇总行; 提交显式 pathspec 并核 `git show --name-only`; 哈希按 T6 guard(Mac 盘满 iCloud 驱逐)。

## §1 登记表(已知项; 五路审计交付后并入)
| id | 层 | 问题 | 来源 | 修复负责 |
|---|---|---|---|---|
| E1 | 执行器账本 | 09-12 保护性平仓 255 笔手续费未回填(按订单行统计成本的读者低估) | W6 §4.6 / STATE | lead(先副本演练 + 看门狗核) |
| E2 | 执行器 | broker 直接 GET 读路未采用容量冲突合同(POST cap8/C4 → GET cap6/C6 仍输出旧 clamped8 与 C6 final) | 复审 R4 §2.2 | FX-EXEC |
| E3 | 执行器 | 损坏事件为 JSON 数组时异常退出, 未形成具名不可观测 | 复审 R4 §2.2 | FX-EXEC |
| E4 | 执行器 | flatten_only 补单沿用 chase 框架, 与逐名止损条款「maker-only 出场、政策 A 不追」不符(W9 把原钉住的止损多头接入此通道) | 复审 R4 §2.4 / W9 | FX-EXEC |
| E5 | 执行器 | reconcile 多 origQty 原因串只取首条 | 复审 R3/R4 | FX-EXEC |
| E6 | 执行器 | 钳制告警把止损 / 冷却名称作「被场所扣留」(文案 ≠ 来源) | W9 | FX-EXEC |
| E7 | 执行器读者 | 窗内无 NAV 行回退到窗外最新行未声明; target_w 为 None 时 intent 块跳过 | X2 登记 | FX-EXEC |
| E8 | 执行器 | funding_span STALE 告警(ours=140 venue=782, 表建于 07-25)—— 消费者与影响待审计 | 08Z 深查 | 待 aud-exec |
| P1 | 生产者 | king 第 80 列训练 v0 / 服务 v1 | T4 | FX-PROD |
| P2 | 生产者 | V2MAIN 第 80 列训练 v0 / 服务 v1 | T4b | FX-PROD |
| P3 | 生产者 | 面板 qv4h 与生产者 qv4h 定义差(中位 |Δlog| 0.52)—— 成员 / 流动性门 / 特征 | G2-A 收据 1 | 待 aud-prod 事实表 |
| P4 | 生产者 | 其余 76 + 169 个模型特征训练 / 服务逐列平价从未核 | 审计 | 待 aud-prod |
| P5 | 生产者 | 09-05 席位播种 876 行为 v0 打分 | T4b | FX-PROD(随 P1 口径) |
| P6 | 生产者 | 08-16 bundle 种子账本存储 iv ≠ 时间差 iv(D17), 状态重置时会再现 | P2 D17 取证 | FX-PROD |
| P7 | 生产者 | FTRIM 置零不强平, 残余在带内冻结 | T5b | FX-PROD(书行为: 回放配对) |
| P8 | 生产者 | 撤名缺口按名等额再分配翻转小仓符号(1000CAT −80.88 → +3.28) | W9 / 复审 R4 §2.5 | FX-PROD(书行为: 回放配对) |
| D1 | 数据 | x0910 面板结算间隔错(SKR/SOPH ¼、IOST 8×)| T5b | 待 aud-data 定位构建器 |
| D2 | 数据 | metrics 归档 2024-03-04 标签切换, 统一处理有 5 分钟时钟错 | L2 | 待 aud-data 列消费者 |
| D3 | 数据 | 研究 king OOF 预测只在前向 y4 有限处有值(D20 前视可得性掩码) | P2 D20 | 待 aud-data |
| R1 | 重训 | 导出器在 v0 上训练却导出 v1 状态(H2b 分叉之源) | T4 | FX-PROD / 待 aud-train |
| R2 | 重训 | 十月链真实业务段从未跑通; P3 裸 R 输出负控缺失; r20 出口门 v2 仅提议未应用 | 复审 R4 §3 / 记忆 | 待 aud-train |
| K1 | 评估 | T5c 标签谓词在全盈利输入上仍打「策略自身亏损」 | 复审 R4 §4.1 | T5d |
| K2 | 评估 | 「NOT MATERIAL」类标签只由显著性门生成, 无经济等价带 | 复审 R4 §4.3 | FX-EVAL |
| K3 | 评估 | P2 G2-C 快照判官未绑定三个预定锚与记录人口 | 复审 R4 §5 | P2(G2-C-BIND) |
| K4 | 知识库 | CLAUDE.md / MILESTONE / CANDIDATE / 记忆中被推翻或待复验的结论仍像现行事实 | 复审 / T8 / T6 | 待 aud-kb, lead 应用 |
| K5 | 运维 | 每锚深查模板基准与检查项过时(guard_twin 字样不存在、改写率台阶、fund_updates 基线) | 08Z 深查 | 待 aud-exec |

| E9 | 执行器装置 | 锚点产物断言把只在未知成交事件时才写的 `filled_unknown_qty/residual` 判 NO_PRODUCER(HIGH 误报; 09-13 空仓日更把全部成交列误判), 去重会吞掉真回归 | 12Z 首锚验收 | FX-EXEC |
| E10 | 账本公证 | `ops/notarize_ledgers.py` 以整文件 sha 公证「昨日」, 但执行器 markout 回填与 fills 回填会合法追加历史日 ⇒ 链上看起来像篡改(09-12: 公证后 +12 行 markout 回填, 再 +3,656 行 E1); 且 manifest 自 08-31 起全部未提交未推送(第三方时间戳缺失), 提交时推 multi-asset-v2 而研究仓在别的分支 | E1 核查 | FX-EXEC(需: 前缀一致性校验 + 追加修订记录 + 修提交/推送) |
| P9 | 生产者(实盘缺陷) | 资金费追加规则按「与上一行时间差」定结算间隔(`shadow_loop_v3.py` L341–342): 短→长间隔切换时, 新制度首次结算按长间隔申报而时间差是短, 被标成短 ⇒ rn = rate×8/iv 放大 2–4×(v1 EMA / fund 腿), FTRIM rn8 在该行为最新行时放大(至多一锚); 08-16 以来在役名 6 例(ONG 08-25 08Z / COTI 08-31 20Z / ZKC 09-02 20Z / T 09-06 00Z / SKR 09-07 20Z / SOPH 09-11 12Z) | FX-PROD 13:3xZ(data.binance.vision 资金费包 `funding_interval_hours` 列为申报值) | FX-PROD(三规则对归档列测误标率, 执行器 fundingInfo 记录作正控) |
| P6′ | 生产者 | P6 前提更正: D17 存储 iv 与时间差不一致的行分两类 —— (a) fund_aug 当前间隔字典造的多行串(存储错、时间差对)、(b) 单行切换行(存储对、时间差错); 盲按时间差重推会改坏正确行 ⇒ 种子加载器按申报证据分类; 另 v3 bundle EMA 状态(08-31 00Z)与种子(至 09-01 00Z)错位, 状态重置会跳行; 实盘 v1 EMA 今日 D17 残差 PROM 相对 5.1% / ERA 0.89% / BANK 0.43% / DEXE 0.10% ⇒ 迁移 P6-M 精确修正 | FX-PROD | FX-PROD |
| P10 | 生产者/训练 | king 训练特征以 float16 存储(`pod_fea_ext.py` L66), 服务端 78 列为 float32 —— 精度层训练/服务差, 影响待测 | FX-PROD | aud-prod 测, FX-PROD 修 |

## §2 审计并入第一批(2026-09-13 14:0xZ, lead; aud-exec 842bbffa 42 项 / aud-train 7e1ecf9a 29 项; 其余三路续跑中)
**顺序原则**: 先实盘安全(会整书平仓 / 会改 gross / 实盘信号错)→ 其余已知缺陷(按严重度)→ 书行为改动(须生产路径回放配对, 等 P2 S2 与 G2-C-BIND)→ 十月重训链(期限 ≈10-01 之前)。「PENDING_USER_DECISION」按用户字不等裁定, 但性质性裁定(杠杆、BNB 抵扣等策略选择)仍单列给用户。

| id | 层 | 问题(摘要; 全文见审计 md) | 严重度 | 负责 / 状态 |
|---|---|---|---|---|
| EXE-01 | 执行器看门狗 | 任何触发仍整书平仓; W6(c) 比例响应 diff 15d29d99 默认关未落地; 09-09(243 名 232.8k)与 09-12(255 名 235.4k)两次均为自家仪器假阳性 | P1 | **FX-W6C**(新克隆 cc_tmp/fx_w6c; R-14 读作 A 默认 ON, 冻结 2%/5 名不调; 事实表 + 红先 + 真书级触发负控 + 电池; 复审后部署) |
| OPS-01 | 运维 launchd | 已撤回的 σ_fund gross 阶梯 plist 仍在 LaunchAgents 且无 disable 覆盖, 重启 / 重登后复活, 连续 84 低离散锚 ⇒ gross 减半仅 INFO | P1 | **lead 已应用 14:00:50Z**: `launchctl disable gui/501/com.hsy.sigma_ladder`(print-disabled 显示 disabled)+ plist 移至 `~/Library/LaunchAgents_retired/`(sha 239274a3 不变, 副本入 receipts); 在役三守护 PID 不变; 收据 `receipts/OPS01_disable_sigma_ladder_20260913T140050Z.log`; 待复审 |
| OPS-01b | 执行器 | 读取端仍在(`scheduler/anchor_loop.py` ~L1762–1780), 任何人手写一个新鲜 g=0.5 文件即减半 gross | P2 | FX-EXEC(红测: 旧码上新鲜可接受 g=0.5 文件降 gross) |
| E4 ⊕ EXE-02 | 执行器 | 追加事实: 自 09-01 起止损 / 全退出残差经 chase 臂发 MARKET reduce-only(9 笔成交约 5,670 USDT); W9 扩大该通道 | P2 | FX-EXEC(R2′ 裁定照旧) |
| E10 ⊕ LED-06 | 账本公证 | 追加事实: launchd 下 git add 报 Operation not permitted(推断 Desktop TCC); 08-31 起全部 manifest prev=GENESIS; 推送分支写死 | P2 | FX-EXEC |
| EXE-03 ⊕ P8 | 执行器 reshape / 生产者 | 12Z 生产者目标本身净空 −8.46%, 撤下 11 名净多 +0.80%; 等额平移把 9 个小空头翻多(8 笔成交 376.82 USDT); 「撤名残差 −9.26% 由撤下名造成」告警归因错; 研究回放同函数 ⇒ 回测已含此行为 | P2 | 并入 P8(书行为, 回放配对); 告警文案归因并入 E6 |
| EXE-04 | 执行器 reconcile | Q6 跨窗未解释余额继承(PREREG 修订 4 数学已接受未落码) ⇒ 窗 t 未解释量在 t+1 读作干净 | P2 | FX-EXEC(队列末) |
| ALM-03 | 执行器告警 | factor_health 仍 ssh 读 08-06 已停发的 jpline 报告; 产物断言 #9 对缺席空过 | P2 | FX-EXEC(W5 设计: 改读在书 ic_monitor 账本) |
| LED-02 | 账本 | 09-12 平仓批 255 行无费无 fills; 三桶读者全判未定价, 回填后仍未定价(无锚中价) | P2 | FX-EXEC(读者从收入账本定价或具名永久未定价) |
| LED-04 | 账本 | daily_nav 按类型已实现 / 费用 07-29..09-12 06:05Z 错(tranId 单键去重吞孪生行 + BNB 费按 USDT 加) | P2 | FX-EXEC(历史行修订记录 + 读者改用 guard_twin income); aud-data 查研究消费者 |
| CFG-04 | 执行实验 | chase 50/50 实验人口无重建锚与退出残差规则(12Z 重建 no_chase 缺口 6,979 USDT = gross 3.0%, 远超登记 37–500U/锚) | P2 | lead: PREREG_chase_restart 修订(实验人口定义), 先于看任何臂差 |
| CFG-06 | 执行实验 | placement eps 0.50 的「不毒」依据 09-05 已作废, config _basis 未改; 模板把 09-04 复读记为完成 | P2 | lead: 全覆盖口径复读预注册 |
| CHK-03 | 成本 | maker 成交占比 08-28..09-02 ≥0.90 → 09-08 起逐锚 0.56–0.89(费率不变 2.00/5.00 bps; 每 +10pp taker ≈ +0.3 bps/单位成交); 原因未测(候选 chase 09-01 重启 / requote direct 臂 09-05) | P2 | 新登记 X-COST: 归因测量(只读), 排在书行为波次 |
| CHK-01/02 · CFG-03 · TRN-27/28/29 | 文档 / 模板 / 记忆 | 改写率台阶 27% 非 19–20%; guard_twin 结论在 ~/guard_twin/state/latest.json; k 窗在役 900s(180 未上线); RUNBOOK_2026-10 引旧 sha; CLAUDE.md 月度重训指向旧 RUNBOOK; r20 出口门 v2 已应用 | P2/P3 | K4 / K5(aud-kb 登记, lead 应用) |
| TRN-01 | 重训链 | 月滚输入(滚动缓存 / 洞格 / RAW 补丁 / 面板 / 资金费尾 / EMA 状态 / base json / pins)在驱动之外且 git 构建器写死九月路径, 照跑会覆盖九月收据所哈希的文件; 驱动无面板平价门 | P1 | 第二波 FX-TRAIN(期限: 十月重训前) |
| TRN-02 | 重训链 | 无门核新月被裁剪 bar 是否全部进 RAW 补丁(E-0908-B 可静默复发; 09-01..10 已有 AKE/BULLA/WOO 三例) | P1 | 第二波 FX-TRAIN; aud-data 先核现面板 |
| TRN-03 | 重训链 | 可部署 F10 numpy 模型在所有门之外导出; 裸调默认打包 09-01 模型; trained_through 写池终点 | P1 | 第二波 FX-TRAIN |
| TRN-15 | 重训链 | 出口门 E2b 钉九月 BUNDLE_BASE dce6a228 / LIVE_PINS fd27fe48, 十月模板要求新值 ⇒ 十月导出必败 | P2 | 第二波 FX-TRAIN(按月合同参数化, 不放宽) |

## §3 用户优先级裁定 + 全审计项归属映射(2026-09-13 14:2xZ, lead)
**用户字(2026-09-13T14:13:19Z)**: 「等main全部完成了再开始secondary,sencdonary看起来最高优的应该是P2和L2.P2其实都不算是secondary,是关键的错误的修复」
- **main** = 本纲领全部登记项(§1 + §2 + 本节)+ **P2 生产路径回放认证**(G2-C-BIND; 连续 combo 历史链 0/41 @1e-6、最大 1.12547e-4 的机理闭合 —— Phase 1 §3 自 09-12 未闭合, 残差只在 DL 腿 f10/fc; G2-B 原门在 P6-M 迁移后的复判计划; S2 读数一律带「未认证」标签, 只作信息)。
- **secondary 全部挂起至 main 完成**: L2(首位)→ T7 → L3→L4 家族 3 → T5d-R(消费 FX-PROD P9 真值表)→ T6 §11 录取规程重设计 → T1 LIVE_D2 九月 carry 更正。已在跑的拉数进程(T7 永续 1h K 线 Mac PID 91801; L2 metrics pod2 PID 611886)让其自然结束, 不做分析、不派代理。
- **main 完成的定义**: 下表每一行要么(a)修复 + 独立复审 + 按规程部署(适用时)且有收据, 要么(b)已核实无缺陷并有收据, 要么(c)转为具名预注册实验 / 批准对象并列给用户(只限真正的配方或人口选择, 不得用来停放缺陷)。
- **并发上限**: 约 12 个工作者(13:34Z 账号额度在约 20 个代理并发时用尽, 全体停摆约 20 分钟)。

### §3.1 AUDIT_EXEC(842bbffa)42 项
| 负责 | 项 |
|---|---|
| FX-W6C | EXE-01(W6(c) 比例响应, R-14 读作 A 默认 ON)· ALM-02(cond2.judged_on 写死) |
| FX-EXEC | EXE-02(= E4)· EXE-04(Q6)· EXE-05(= E2, 克隆 6294534 已提交)· EXE-06(= E3)· EXE-07(= E5)· ALM-03 · ALM-04(= E9)· LED-06(= E10)· OPS-01b · E6(含 EXE-03 告警归因文案)· E7 |
| FX-EXEC2 | LED-01 · LED-02 · LED-03 · LED-04 · LED-05 · LED-07 · LED-08 · ALM-01(= E8 文案/指纹)· ALM-05 · ALM-06 · STA-02 · STA-03 · OPS-03(先设计后编码)· CFG-02 · CFG-07 · DOC-01(执行器侧) |
| FX-BOOK(待派) | EXE-03 ⊕ P8(撤名 / 净空等额平移翻号; 按侧比例分配对照实验)· P7(FTRIM 残余) |
| lead 已应用(待复审) | OPS-01 σ_fund 阶梯 disable + 退役 14:00:50Z(6cc95943)· **OPS-02 已 KILL 执行探针 launchd bootout + disable + plist 退役 14:20:08Z**(sha 58a776ec 不变; KILL 文件保留; 在役三守护 PID 不变; 收据 `receipts/OPS02_retire_execprobe2_20260913T142008Z.log`) |
| lead 预注册修订 | CFG-04(chase 实验人口: 重建锚与退出残差)· CFG-06(placement eps 0.50 全覆盖口径复读) |
| X-COST(待派, aud-exec 只读) | CHK-03 归因(maker 占比 ≥0.90 → 0.56–0.89) |
| K5(lead 深查模板) | CHK-01 · CHK-02 · CHK-03 基线 · CHK-05 · CFG-05 读数跟踪(requote 实验 ≥09-19 00Z 恰一次主判, 停机日须明列) |
| K4(lead, aud-kb 登记后) | CFG-03 · DOC-01(STATE/CLAUDE.md 侧) |
| 关闭(核实无缺陷, 收据 = AUDIT_EXEC 行) | EXE-08 · CFG-01 · CFG-08 · STA-01 · CHK-04 |

### §3.2 AUDIT_TRAIN(7e1ecf9a)29 项
| 负责 | 项 |
|---|---|
| FX-TRAIN | TRN-01 · 02 · 03 · 06(D20 人口 ⇒ 预注册实验设计)· 07 · 09 · 10(15% 验证切片 ⇒ 预注册实验设计)· 11 · 12 · 14 · 15 · 16 · 17 · 18 · 19 · 20 · 21 · 22 · 23 · 24 · 25 · 26(批准对象备齐, 用户一行批准)· 27(RUNBOOK 草稿)· R1 · R2 |
| FX-PROD ⇄ FX-TRAIN(同一口径决定) | TRN-04(= P1 导出侧; 效应不重要但缺陷会随十月导出复发, 不关闭)· TRN-05(= P2) |
| K4(lead) | TRN-13 · TRN-28 · TRN-29 |
| 关闭(核实今日不可复发; 收据 = AUDIT_TRAIN 行) | TRN-08(无构建器读 metrics 归档; D2 仍由 aud-data 列消费者) |

### §3.3 其余登记项
- P2(critical): K3 = G2-C-BIND; G-P2 链残差闭合; G2-B 迁移后复判计划。
- aud-prod / aud-data / aud-kb 交付后: P3 · P4 · P10 · D1 · D2 · D3 · K4 并入本表, 各派负责。
- E1(已应用, 待复审)· K1(T5d 已修谓词, 待复审)· K2(FX-EVAL)。

## §4 第二批并入与裁定(2026-09-13 14:5xZ, lead)
### §4.1 规程增补(FX-EVAL K2 交付, 99a6cd27; lead 复跑: legacy rc=1 红集 == 声明 19 格 / module 84/84 rc=0 / AST 保留 PASS; 变异与重标门复跑在后台)
- **§0 第 8 条(采纳)**: 无差类判词(NOT MATERIAL / 不可区分 / SAME LEVEL / EQUIVALENT)**只由等价带发出** —— 共享模块 `multi_asset/exports/research/common/equivalence_labels.py` + 预冻结 δ(单位 / 理由 / 出处); CI∋0、点估计在带内但区间出带、或门失败 ⇒ INCONCLUSIVE / NOT ESTABLISHED; LOSS 标签只在该书实现均值 < 0 时发; (A)/(B) 方向判不变且无差分支永不先于它们求值; 须在 P2 S2 出表、L2 判官、T5d OWN-LOSS 门之前采纳。
- **δ 裁定**: 同一纲领内同一单位只一个 δ。书层 Δg(bps/锚/gross)= **0.05**(D1; 最早预声明 = PROGRAM L155 / SPEC_T5b「≥0.05 = material」, 更严); T5d 自设 0.25 只作敏感性列(FX-EVAL 核: T5d 标签在 0.25 下亦不变)。ΔIC δ = 0.003 仅分数层, 不作书层经济判据。
- **重标 347 行 = 提案**(撤回 126 / 细化 36 / 不变 180), 待独立复审后由 K4 应用于 RESULT / STATE / 记忆; 要点: T4 NOT MATERIAL → INCONCLUSIVE; T5c/T5d 价格与净额「策略自身亏损」→「共同亏损, 差异不可判」; T8「不能预测」→「未检出; 多空腿有用性未排除」; v4 决策文档六处「(C) 不可区分」→「(C) INCONCLUSIVE」。

### §4.2 裁定
- **E4(FX-EXEC)R2′ 前提更正**: from_reject 转换是 MARKET reduce-only(非「原限价 IOC」)。裁定 **(a) 保留**: 止损于 08-20 批准的动作是「走既有 flatten_only 通道 — 零新执行形态」, 该通道在政策 A 下已有 from_reject MARKET 转换(PROMUSDT 08-26 00Z / BTRUSDT 08-31 16Z); 09-01 改变的是 from_partial 随机入追单臂, R2′(1) 把止损名移出全部追单路径即恢复所批准通道。(c) 原限价 IOC = 新执行形态, 另立执行设计候选(需预注册 + 场所正控, 证据来自 X-COST 转换滑点分布); (b) 为止损特例延迟一锚且六例普查符号混杂(均值 ≈ −1 bps)无据。止损 docstring / 告警文案按真实通道改写(E6 族)。原句逐字保留并标假。
- **P9(FX-PROD)**: 批准 pod2 拉 data.binance.vision 八月资金费月 zip(用户 09-05 静态 CDN 豁免); 方向 = (a) 挂账时精确签名 + 下锚前向缺口精确规则回溯重解 + 精确 EMA 追溯修正(先在同一评估装置上量残差再写码)+ (c) 月 zip 对账离线迁移; (b) 结算前 fundingInfo 记录器仅候选, 须对八/九月 zip 正控; 首行默认 8.0(07-26 08Z 22 名)并入 P6′/P9; AUG_IV.get 三处构建器归 FX-TRAIN(TRN-07)。
- **回滚动词(aud-kb P0, 确认)**: STATE §1 与深查模板 ⑥ 的 `kill $(cat combo_live_daemon.pid)` 在 launchd KeepAlive 下不是回滚。lead 哑任务正控(同 plist 形态, 在役任务零接触, combolive PID 30944 前后不变): 第 1 次演练 3 s 读「未重生」**结论错误**(launchd 对运行 <10 s 的任务节流, 状态为 spawn scheduled; 收据保留 `receipts/OPS_rollback_verb_drill_20260913T144523Z.attempt1_insufficient_wait_WRONG_CONCLUSION.log`); 第 2 次(运行 15 s 后 kill, 轮询 15 s): **kill ⇒ 1 s 内重生; bootout ⇒ 卸载、无进程、15 s 无重生; bootstrap ⇒ 恢复**(`receipts/OPS_rollback_verb_drill2_20260913T144746Z.log`)。STATE §1 已更正; 深查模板 ⑥ 待 K5 重发; 深查 cron 41df7caa 会话级、约 09-16 00:24Z 自动过期 ⇒ K5 须在此前以更正模板重建。
- **基建**: 盘 98% 满 ⇒ iCloud 驱逐 .git 对象 ⇒ 提交需数分钟且与他人提交撞 ref 锁; 删除已部署轮次 23 个陈旧克隆(`receipts/INFRA_disk_cleanup_20260913T143228Z.log`, 逐目录 HEAD / 脏计数 / 开句柄检查), 空闲 12 → 39 GiB; 工作者磁盘守则(复制前 df、剩余 ≥20 GiB、电池后删副本、<15 GiB 停写)。

### §4.3 AUDIT_DATA(bb8a2806)29 项归属
| 负责 | 项 |
|---|---|
| **FX-DATA**(新, 14:4xZ) | TRD-01(P1 按成交定义可交易: 156 个死合约冻结行 / 60 个死后资金费记录)· TRD-02 · TRD-04 · TRD-03(随 TRD-01 关闭)· FND-01(= D1)· FND-02 · FND-03 · HOL-01 · LIN-01 · RET-02 · UNI-03 · EVL-01(CAL 默认值陷阱) |
| **FX-MODEL**(新, 14:4xZ) | FEA-01(P1 DL 训练资金费输入 = 前视名单)· TIM-01(P1 king 训练/服务时钟错位 E-0909-F 仍在役)· UNI-01 · TRD-05 · TRN-06 协调 · P10(视 aud-prod 测量) |
| P2 | OOF-01(全史数字 ≠ 在役书: S2 标签)· TRD-02 回放偏差列 |
| K4 | DOC-01(数据谱系)· LED-01(研究工具打印错费列, 结论未用) |
| 关闭(收据 = AUDIT_DATA 行) | RET-01 · HOL-02(已修)· LBL-01 · FWD-02 · UNI-02 · TIM-02(= D2 关闭)· TIM-03 · LIN-02 · LIN-03 · FWD-01(= D3; TRD-01 修后复测) |
- 追加: M2-33(aud-kb 记忆扫描, 在役核实)实盘看门狗 flow-day 缺陷仍在(`watchdog.py` L1110–1111 / L1252; 74b2acb5 只改研究侧)⇒ FX-W6C 增补 2(先与 AUDIT_EXEC STA-01 对账)。
- 待派: FX-BOOK(P7 / P8⊕EXE-03)于审计工作者交付腾出并发后。

## §5 复审交付方式(用户字 2026-09-13 15:0xZ)
「整体修复完之后,发我完整文档和提交链,我交独立研究员复审,确保整个实盘,包括所有pipeline,数据采集,评估,模型训练,未来的调研,口径都是准确无误的.」
- 复审 = **main 全部完成后一次性合并包**, 由用户转交独立研究员; 不再逐项交接。
- 包内容(机械组装, 以 §3/§4 映射表为索引): 总交接文档(按层: 实盘执行 / 生产者 / 数据采集 / 评估口径 / 模型训练 / 重训链 / 未来研究装置)· 每项的问题 / 事实表 / 旧码红 / 修法 / 测试 / 电池或回放 / 未证边界 · 全部提交链(研究仓、执行器克隆分支、生产者快照分支, 含 diff sha)· lead 复跑收据 · 偏差与更正记录(含 lead 自身错误)· 复核指南(逐项复跑命令)。
- 部署仍在复审之后; lead 未部署任何修复(OPS-01/OPS-02 为已裁定撤回任务的 launchd 持久关闭, 已含收据, 列入包内复审)。
