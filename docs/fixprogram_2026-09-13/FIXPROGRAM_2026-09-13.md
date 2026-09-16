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

## §6 第三批事实与裁定(2026-09-13 15:3xZ, lead)
- **P10(king f16 训练 / f32 服务)**: aud-prod parity_king 收据(428c179e, 装置 3e71e0de, rc=0): 把服务端 king 特征往返 float16 后 **47/47 锚十分位不变** ⇒ 精度层无可测差; 以该收据**关闭**(VERIFIED_IMMATERIAL), 不改代码; 列入复审包。
- **新登记 P11(训练 / 服务宇宙不一致)**: aud-prod 与 FX-MODEL 读数 —— king 训练成员取自 829 名轴, 生产只对在役 450 名打分; 训练宇宙对服务宇宙的分数 Spearman 中位 **0.947**, 大于时钟错位 TIM-01(0.9865)。负责 FX-MODEL(预注册须显式定义「as-of 训练宇宙」), aud-prod 在 AUDIT_PROD 登记证据。
- **TIM-01 同族两处(FX-MODEL 读码)**: DL 成员统计不含锚 bar 而生产含; king 成员统计在 2022 首周负索引回绕。并入 TIM-01。
- **FEA-01 事实细化(FX-MODEL)**: 08-15 前 v1 面板资金费恰为 live_pins 450 名, v2ext 825 名; 在 450 名上 v1 与 v2ext 的 raw EMA(v0)与 fund_now 逐位相同 ⇒ 用 v2ext 补齐缺失名不改任何既有格。已存 DL 训练腿的 ZFD 是 08-23 旧文件逐字拷贝(全名有资金费)⇒ 该处为潜在代码路径而非在役缺陷(FX-MODEL a1c16b73 自更正)。
- **第 80 列口径裁定(FX-MODEL 阻塞问题)**: 在役修复 = **P1 服务端改用训练定义 v0**(633d44b)—— 恢复与现有 booster 的训练 / 服务一致, 不需重训, 属缺陷修复。**十月及以后的重训**是否改为按间隔归一的 v1(v0 为原始费率 EMA, 对 1h/4h 结算名尺度不同 ⇒ 训练特征本身有经济尺度问题)属配方选择, 不在缺陷修复内单方定: FX-MODEL 预注册须含 **v0 一致臂 / v1 一致臂** 配对(训练与服务同口径), 按 K2 等价带判; 未判之前十月导出维持 v0 一致(与 P1 服务口径相同)。FX-PROD 的 P2(V2MAIN 第 80 列 v0)同此。
- **EVL-01 范围**: FX-DATA 普查 HEAD 中 33 个文件 CAL 缺省为 "simple"(审计记 21)。
- **构建器写死输出路径**(FX-DATA 读码): `pod_panel_ext.py` 未传输出路径时覆写 `wide_panel_4h_v2ext.npz`, `pod_panel_splice.py` 恒写固定路径, 两个 r6 构建器写死 r6 目录 ⇒ 并入 TRN-01(十月链)与 HOL-01(面板重建一律沙箱副本)。
- **G2-C-BIND lead 核验**: `receipts/s2/G2C_BIND.json` sha c0aca587, verdict PASS(真实束 0 失败 · 突变 6/6 按名红 · 真实收据前后不变 · king 链 41/41 ≤1e-6)· 预注册 sha 35ea8761 · 日志 rc=0 ⇒ **接受**(ecd45655)。附记: 三槽 B4 均报 `combo_live_status.json` 在清单中但不在场, 按冻结 B4 只核在场文件 PASS 成立, RESULT 须说明缺失原因与是否被任何回放步骤读取。
- **S2_TABLES 旧判词作废**: 15:09–15:11Z 按旧 A6.7 规则出表(K2 指令送达前); 书层数字不受判词规则影响, 判词须按 K2 AMENDMENT 重出; 12 个双种子对照无一 CI95 排零。
- **D20(P2 探针)**: king 导出器成员集自身已不含前向标签非有限格(各年 0)⇒ 前视条件内嵌于成员集构造; 研究成员规则(有限 qvk ∩ umask)含非有限标签格 2342/130/1245/249/189(2022–26)。生产路径上 D20 的诚实量 = 生产成员与 OOF 打分集之差。

## §7 AUDIT_PROD 并入 + 第四批裁定(2026-09-13 15:4xZ, lead)
### §7.1 AUDIT_PROD(57f7e2be)31 项归属(无 P0/P1; 11 项 P2; 分数层度量, 书层未测)
| 负责 | 项 |
|---|---|
| FX-MODEL(暂停中, 恢复后读本节) | PROD-01 king 训练时钟 E−1 vs 服务 E(Spearman 中位 0.984, 400 名中约 95 名跨十分位)· PROD-02 king 秩宇宙 829 vs 450(0.947; = P11)· PROD-03 研究 king 特征 vs 服务(0.935, 最小 0.760; A0 与 P2 S2 注入 king 同此差)· PROD-06 V2MAIN 训练行 vs 服务(0.982, 几乎全是成员宇宙)· PROD-07 · PROD-11 成员 Jaccard 0.660(差异全在宇宙)· PROD-34 / PROD-35(E-0909-A 行数与 V2MAIN 训练零资金费列的模型效应, 未测) |
| FX-PROD | **PROD-27 combo 重写最坏余量 9 s, 生产者迟到时静默跳过 ⇒ 该锚按 king 形态交易且无页报**(P6-M 之后、P9 编码之前)· PROD-40(= P9 交叉引用) |
| P2 | **PROD-36 = G-P2 连续链残差的候选机理(H-d)**: 回放缓存短于生产者 40 日窗时 `_btcv_series` 前 7 日回填进入 180 锚 z 窗, 只动 H:btcv_z 与其 4 个乘积列, 且只在缓存 ≤213 锚行时(分数至多 3.3e-4), ≥221 行后为 0; 与「残差只在 DL 腿、早锚大、向最新锚衰减、快照起步 3/3 精确」一致; 与 combo 目标的链接为推断, 须 P2 冻结判别检验 · PROD-03 入 S2 偏差表 |
| FX-TRAIN | PROD-21 十月换装无席位重播种步骤(与 TRN-12 同族) |
| FX-DATA / FX-TRAIN | PROD-23 构建器对 API 尾部资金费行套用单一申报间隔(= FND-01 同族; 消费 P9 真值表) |
| FX-BOOK(待派) | PROD-24 FTRIM 为去均值前排除而非强平, 残余随带冻结(= P7)· PROD-25 = EXE-03 确认: 12Z 撤名残差的 91% 是生产者自身净空 −8.46%, 再去均值在 109 个 combo 锚中 99 个翻转小空头(= P8) |
| K5 | PROD-26 = CHK-01 确认: 11 个改写率读数全对, 上升来自 V2MAIN 链与 king 书分离(corr(R, R_fc) 0.93, R_kc 平 0.163) |
| 关闭(收据 = AUDIT_PROD 行) | PROD-05 = P10(f16 往返 47/47 十分位不变)· PROD-12 = P3 qv4h(生产与 A0 中位 |Δlog| 5.7e-4 ⇒ 原登记的 0.52 属面板与生产者不同定义, 生产路径一致)· 其余 VERIFIED_IMMATERIAL 行 |
- **逐位门全过**: 服务 king 输入 booster(X) = 记录分数 47/47 · 生产代码在实盘缓存上复现服务 X 47/47 · 训练构建公式复现存储 x0910 特征 1,056,000/1,056,000 格 · 服务 V2MAIN 输入 6/6 · 成员规则 161/161、148/148 · pod 缓存 = 生产者缓存(在役 450, 08-04..09-11)。
- **列级**: king 78 个服务列 77 DIFFERENT(K 线列差在时钟与 f16 存储, 秩列另差宇宙, 第 80 列差在单位)/ 1 EQUIVALENT_FORMULA; V2MAIN 40 IDENTICAL_CODE / 2 EQUIVALENT_FORMULA / 129 DIFFERENT; 逐列表 `AUDIT_PROD_columns.csv`。

### §7.2 裁定
- **FX-TRAIN TRN-02 请示(九月合同数据段将因缺覆盖清单拒跑; 写清单须写入九月运行目录 `/workspace/review_scratch/`)**: **暂不写入九月目录**。恢复后先: (a) 枚举所有引用该目录的九月收据, 证明无收据对目录列表(而非逐文件)取哈希; (b) 清单由已提交的门装置从补丁与缓存只读生成; (c) 目录内全部既有文件 sha 前后逐一不变。三条都成立 ⇒ 可作为纯追加文件写入, 收据入库; 任一不成立 ⇒ 清单放同级新目录并把九月合同标为「历史运行, 门之前完成」的具名例外(不改九月冻结文件)。
- **TRN-06 预注册归 FX-MODEL**(FX-TRAIN 同意); FX-TRAIN 保留 TRN-10 / TRN-11 与十月链接线。
- **r6 构建器入 git 归 FX-DATA(LIN-01)**; FX-TRAIN 月滚阶段消费 FX-DATA 的副本(提交与逐文件 sha)。
- **REPORT_FX_EXEC**: 子代理工具约定「以文本交回、不写报告文件」⇒ lead 逐字转录落盘(dce59600), 非权限绕行。

## §8 第五批(2026-09-13 16:1xZ, lead)
- **EXE-01 交付(FX-W6C, 未部署)**: 克隆 `fix/exe01-proportional-response` f0d4eac → f99dc80 → b3c5fc2; diff `docs/receipts/fx_w6c.diff` sha d4a6d103; 研究仓 49fea5f2 / b750a5d4 / ff77d8ed; 报告 `REPORT_FX_W6C.md`(lead 逐字转录 22708e83)。最终电池(树 057449db)136 套件 135 rc 0, 唯一红 tests_env_loading(克隆无 .env)。**范围宽于 R-14 文字**(按触发器作用域而非只 W6(c) 自洽类; 实盘 10 次整书平仓中 5 次为具名作用域, 4 次为两名事件 0.42–1.84% gross)—— 交复审确认。
- **新登记 W6C-B13(P1, 在役)**: 全书读回缺失不进入全阶梯 —— ef60f85 上无最新读回 ⇒ 不触发且不判盲(基于陈旧状态判); lead 早前「全书不可读回会走全阶梯」的表述**错误**(记入 lead 错误清单)。修复方向: 最新读回缺失 / 陈旧 ⇒ 具名盲态 ⇒ 停开仓 + 页报, **不整书平仓**(仪器疑问不得触发全书级响应)。负责 FX-W6C, 排在 ALM-02 之前。
- **新登记 W6C-I6(P1 待测)**: 非计划时刻运行 + 持仓书 + 无下单 ⇒ §4-5e 平意图暴露可能整书平仓; 先测可达性。负责 FX-W6C。
- **新登记 W6C-I5 / NEW-01**: 平仓行 anchor_ts / submit_ts 为写行时刻(晚于全部成交), 与平仓后读回 anchor_ts 不同 ⇒ §4-5e 永不评判平仓锚; 负责 FX-W6C(watchdog.py)。**NEW-02** `venue_fills.py:1179` 平仓 fills attempt_idx 2 对订单行 1 · `ops/gate_coverage.py` 重复登记 tests_external_book(首条被静默忽略)—— 负责 FX-EXEC。
- **电池公开行情 GET 裁定**: `run_acceptance.sh` 含 tests_entrypoint_wiring(DRY_RUN run_anchor ⇒ 对 fapi 的无凭据公开行情 GET), 部署门 safe_commit 同此 ⇒ **允许**, 条件: 仅在 N+65min..N+3h15m 启动; 三个执行器工作者共用 `/Users/haosiyu/cc_tmp/BATTERY.lock` 一次一个; 断言无 .env 与 DRY_RUN; 收据记请求权重; 事后还原 state; 不对证据账本副本运行。FX-EXEC2 15:52Z / 15:57Z 邻格运行已发生此类 GET 并追加其 14:27Z 账本副本的 anchor_runs.log(账本文件不变), 记入其报告。
- **LED-08 设计缺口(已退回 FX-EXEC2)**: 自校准带(滚动 ≤42 锚 中位 + 3×1.4826×MAD)会在约 7 天内吸收阶跃漂移(X-COST 的 93.1% → 73.9% 正是此形态)⇒ 须加冻结参照窗漂移检查(配置命名、日报一次、红测合成阶跃)。
- **pod2 配额(基建)**: /workspace 配额 15:51Z 用尽 ⇒ P2 Stage C 第 1 跑被杀(零数字)、P9 八月 zip 拉取与 L2 metrics 拉取停止。lead 16:07Z 删除 `uplift_2026-09-11/r2_sleeve/feat/*.npy` 7 个原始特征缓存(约 11.4 GB, 09-11 08:36Z, 第一轮已关闭线; 引用扫描: 该目录外无引用; r2_new_feats.npz 与全部装置 / 收据保留; 可由 holefix 缓存重建), 2 GiB 探针通过; 收据 `receipts/INFRA_pod2_quota_relief_*.log`。未触碰 bookdepth_raw(188 GB)/ lob_npz / review_scratch / data / 另一研究员目录。P2 与 FX-PROD 恢复, 一次一条、先探针。

## §9 第六批裁定(2026-09-13 16:2xZ, lead)
- **LED-04 更正审计 + 新在役缺陷 W6C-C4(P2)**: AUDIT_EXEC 称「无触发决策依赖修前 daily_nav 已实现值」不完全对 —— 看门狗 cond4 `cum_return_from_start_pct`(§4-4, watchdog.py:1533-1600)在转账日用当日末行 realised_pnl 定价; 修前行低记 ⇒ 14:27Z 账本副本上判断量 −1.3136%(与实盘 last_eval 逐位同)对修正后 −1.5749%, **低估 0.2613 pp**(主要 08-02 / 08-05); FX-EXEC2 装置与收据 44cbcfc6。**裁定 (a)**: cond4 对修前转账日优先用修订记录的 USDT 已实现值; 记录缺失 / sha 不符 / 解析失败 ⇒ 用记录值并在 last_eval 具名 `unamended_prefix_day`, 不判盲、不静默跳过。负责: 记录格式 / 读取合同 / 演练 / 应用装置 = FX-EXEC2(da1a9389); watchdog.py 改动 = FX-W6C(B13 / I6 之后)。修订账本的实盘应用等复审包(看门狗改动部署前无读者)。
- **ALM-03 方案 A**: 新消费者 `run_ledger()` / `evaluate_ledger()`(监控输入健康检查, 不发衰减判词)接入第 9 步; 旧 `run()` / `evaluate()` / `fetch()` 逐字节保留并标 RETIRED(保 §0 旧断言逐字), 静态格证明运行时无调用; 新消费者须以真实 W1 行形状做正控并有 W1 行键变更即红的格; 「删除 RETIRED 代码并改指四个套件」登记为需复审给 §0 例外的后续项。
- **E10 公证器**: FX-EXEC 克隆 6523440 已提交(报告待收据入库后); FX-EXEC2 提议的前缀一致 + 追加后缀零合同违例 ⇒ LEGITIMATE_APPEND + 修订记录 与之对齐。
- **P9 八月 zip 新表**: `cc_tmp/fx_prod/work/p9/P9_declared_interval_table_2026-07-01_2026-09-13T12Z_zipszips_2026-08.csv.gz` sha 366763a4…(2,008,476 字节; FX-DATA 本地核过); 八月 zip 否定 4 个存储标签、逐一确认 533 个旧 D17 行; T / SKR 待九月 zip; FX-DATA 恢复后以此表替代 b797c85f。

## §10 P2 回放装置认证闭合 + 新登记(2026-09-13 17:0xZ, lead)
- **G-P2 连续 combo 链残差 = 回放装置缺陷, 已修并过新门 G2-C-ASOF(41/41 恰 0.0)**: 生产 combo 段每锚在截至 A 的完整 11,520 行缓存上重跑 171 特征管线; Phase 1 链喂截到 A 的 09-12 08Z 缓存, 早锚少 1,920 行 ⇒ 只改 DL 腿早段样本统计并经 EMA / 带冻结传递。修正链装置 p2_attr_chain_asof.py c333b0e5(Phase 1 驱动本身不变); 原 G-P2 FAIL 标签逐字保留。认证范围 = 41 锚 pod2 混合缓存(其 07-27..08-03 的 1,920 行从未与生产文件逐位对比, 只证明其对输出无可测影响)。K3 / P2 main 项中「回放装置保真」部分关闭(待复审); S2 历史书读数「未认证 / 仅信息」标签**维持**(D1/D2 / PROD-03 / D20 / D21 仍在)。
- **新登记 P12(待测)**: 生产者 `state_H_f10_{A}.npz` 在每锚 kc/fc 写出后约 2 分钟被再写, 09-12 08Z 与 combo 段自身计算差 2.63e-8(96 名)—— 疑似第二写者(sidecar?); 负责 FX-PROD(读码 + 逐锚 mtime 与内容普查, 只读)。
- **LED-03 BNB 换算口径裁定**: `bnb_spot_1m_close_at_fill` = BNBUSDT 现货 1m K 线(data.binance.vision 静态存档)含成交时刻那根的收盘; 逐行记换算价 / 来源 zip / sha / 口径名; 永续 BNB 标记价只作敏感性; 缺分钟 ⇒ fee_unknown 具名不插补。
- **实盘写回类操作(LED-03 精确回填 / LED-04 修订记录 / LED-05 52 行重建订单)**: 装置与演练均已提交; 本会话交接期一律不执行, 随复审包由接手者执行(先 --rehearse 于实盘根再 --apply, 锚窗外)。

## §11 引用更正(2026-09-13 17:1xZ, lead)
- **AUDIT_PROD 的提交是 `ee2a8c4d`, 不是 `57f7e2be`**(P2 指出, lead `git show` 核实: 57f7e2be = P2 装置 p2_s2_relabel.py; ee2a8c4d = AUDIT_PROD.json / .md / _columns.csv)。§7 标题与 §7.1 表头及交接文档中的「57f7e2be」均指 ee2a8c4d; 原文不改, 以本条为准。审计工作者自报的提交号与实际不符, 属「完成体动词须有收据」同族 —— 我方转引时未 `git show` 核对。
- **P2 最终**: AMENDMENT 12 cfc38847(combo_live_status.json 只在仓内快照目录、从未进入 pod2 副本; 无回放步骤读取生产者副本, 读者验收读的是回放自己刚写的 target_live_combo ⇒ B4 PASS 按冻结成立)· D22 = PROD-03 入 S2 偏差表 · 最新 a4173c84 · 指针 `docs/PREREG_combo_chain_residual_attribution_2026-09-13.md` 结果段 + P2 预注册 AMENDMENT 9–12 与收据 9–14。仍开: G2-B R0/R1/R2(P6-M 部署后)· FX-DATA 可交易性掩码 sha 钉入(对方暂停)· pod2 attr_D 删除(lead 已准, 收据核实后)· S2 标签维持「未认证 / 仅信息」(lead 已裁)。

## §12 独立复审(Codex QNT-2026-0907)结论并入 + 裁定(2026-09-16 03:2xZ, lead)

**受据**: `docs/REVIEW_fixprogram_progress_2026-09-14.md`(分支 `agent/codex/QNT-2026-0907/onboarding-audit`, 提交 **9f6384fb**, blob dce26d3e, 文件 sha256 `cd3bdb88ac0e759edabacec9faf1b754405206330cf427095e81d7bb64bd08fe`, 定稿 2026-09-14 00:58 SGT)。被复审对象钉在研究提交 **3eb901ee**, 分支头 FX_EXEC a21797dc · FX_W6C 3f85c0e · FX_EXEC2 e05c45ae · FX_PROD dfd3b0bc。复审后我方继续提交的内容**不在**其复审范围, 须另做差异复核。

**复审给用户的总判**(逐字要点): 输入不一致 / 未来名单污染 / 长期僵尸行情 / 连续 combo 未平价四条核心警报**有依据**;「所有流程已修正确」不成立;「因此实盘完全无效」也推不出。最准确表述 = **尚无一条同时满足 当时可见数据 · 训练/服务同定义 · 逐折样本外 · 生产整书连续平价 · 真实持仓退出会计闭合 的证据链, 来证明在役策略的历史水平与 Sharpe>3**。

### 12.1 新登记项(FXR-*, 全部进入本纲领 owner 队列)
| 编号 | 事实(复审复算) | 级别 | owner |
|---|---|---|---|
| FXR-PROD-1 | `migrations/fund_label_ema_correction.py:74-78,117-127`(sha256 1cbeca90…): `setdefault` 钉住旧标签、当前输入的标签冲突**只收集不拒绝**; 把上次修正态再作输入 ⇒ EMA 0.00022238→0.00020784, 控制残差 1.4540e−5, 标签冲突 1, **仍正常返回且状态文件已写出**; `--control` 只报不阻断, 且修正态先于控制落盘 | **P1** | FX-PROD |
| FXR-DATA-1 | `SPEC_TRADABILITY_2026-09-13.md` §5–7 以「不交易」代替「不欠账」: §5 payable iff tradable · §6 出成员后不再计价格/carry/cost · §7 TF≈C0 关缺陷。反例: 最后成交在 D, D+23h55m 仍 TRADABLE、D+24h 不再; 两个市场成交标记相同而结算价 100 / 50 ⇒ 退出损益 0 / −50, 代理无法区分。另: `AUDIT_DATA TRD-03` 的 `VERIFIED_IMMATERIAL` 过头, 应降为「已记录幽灵 carry 很小, **退出损益未识别**」 | **P1(设计)** | FX-DATA |
| FXR-PROD-2 | `shadow_loop_v3.py:293-327 resolve_appended_intervals` 只遍历「刚得到下一行」的行 ⇒ 冷启动首行到达批次不同结果不同: 一次到齐 `[4,4,4]` EMA 0.00026 · 逐次到齐 `[8,4,4]` EMA 0.00013964 | P2 | FX-PROD |
| FXR-PROD-3 | `shadow_loop_v3.py:186 ema_v0_problems` 对 `{'S': None}` / acc=NaN / 同 last_ts 均返回空问题表 ⇒ `ShadowState` 判通过 | P2 | FX-PROD |
| MON-1 | 未知成交比例显示**下界算错**: 已知 taker10+maker10、未知 maker100 时报 ≥50%, 实际相容 8.33%; 09-12 12Z 真实 4 未知行应显示 ≥15.62% | P2 | FX-EXEC2 |
| MON-2 | funding-span 由 external INFO 升 internal HIGH 时, 旧 episode 不含 book_source / 后果等级 ⇒ **第一次 HIGH 被去重抑制** | P2 | FX-EXEC2 |
| MON-3 | 修前收入被标 unreliable, 但 `account_facts` / 同日落袋段只看 observable/complete ⇒ 缺修订仍判可算(可靠性标签未贯穿读者) | P2 | FX-EXEC2 |
| MON-4 | 日报残差 `ΔNAV−Δrealised−Δflow` **漏 ΔUPL** 却称「非交易原因本应为 0」。Sep-11 实例: 差额 1,708.427360U 中 ΔUPL=1,694.16638087U, 余 ~14.26U 未归因; 正控(钱包 1,000 不变, 浮盈 0→10)新旧读者都报 +10 | P2 | FX-EXEC2 |
| FXR-W6C-1 | 比例响应**默认 ON 且配置缺失/不可读/非布尔都 ON**, 只有布尔 false 关 ⇒ 应进入**显式配置故障**; 且 300U 疑额可触发平该名 1,300U 整仓 ⇒ 「2%」不是平仓额/成本上界, 范围条款须先裁 | P2 | FX-W6C |
| FXR-TRN-1 | swap dryrun 允许词法 `root/..` 逃出空 root ⇒ 路径须**规范化后**再检查 | P2 | FX-PROD / FX-TRAIN |
| FXR-DOC-1 | 交接措辞更正: producer 基名单实际是 `exchangeInfo TRADING ∪ st.live`, 失败回退旧基名单 —— **不是严格只保留 TRADING**;「实盘天然完全排除退役币」推不出 | P2 | lead(已并入本条) |
| FXR-DOC-2 | X-COST 摘要须更正: requote 的 11.3831pp 依赖「历史转单率可搬到当前人口」的可交换性假设, 不作该假设时原模型自报 **[−0.4178, +15.5642]pp**, 摘要把下界写 0 是错的; chase/forced 的 4.3531/2.4401pp 是**已成交桶份额**, 不是关实验后的反事实; 5.14U/日只在固定成交额且 5bps→2bps 假设下成立。**不接受「执行成本侧没有隐藏缺陷」**: 首拒 −5022 14.3%→23.0% 原因未测 | P2 | lead |
| FXR-DOC-3 | Sharpe 1.29 引用必须带窗: **W_ALPHA 2022-06-30 00Z→2026-08-30 20Z, 9,138 锚, 1.29122344 [0.3207, 2.2822]**(探索性 2,000 次 UTC 日块自举, 保留日内不保留跨日); T6 的 **W_FULL 2022-01-31 起 10,038 锚 = 1.1062**; 原表另含 08-31 00Z 一锚的 9,139/1.2947 **不可混用**。N_eff≈1.57 不是有效独立试验数, `.30` 不是「真 Sharpe>3」的后验概率 | P2 | lead / aud-kb |
| FXR-ALM-1 | Telegram #55 `ic_monitor` 的对象 = 场所实持仓名义排序 vs 下一锚隐含价格收益排序(**非模型分数 IC, 非净收益 IC**); 阈值仍 alpha 0.05 / band 0.002, 实际 0.1 / 0.00025 **未重标**; `check_factor_health` 仍读退役 jpline daily_report(ALM-03 迁移未完成) | P2 | FX-EXEC2 |
| FXR-KB-1 | 替换版深查提示词内含**未获批准的新监控/解盲政策**(42 锚阈值 · placement 分臂读数), 且须与 CFG-06「没有看过分臂结果」声明对齐 | P2 | aud-kb / lead |

### 12.2 复审确认的既有缺口(不重复计数, 仍归原 owner)
- **Q6 / EXE-04 未落码**: `live/reconcile.py:693-720,848` 每窗以上一次场所观察量起算, 旧未解释量不作债项延续 —— 与 B13「缺最新截面读旧状态」是两件事, 比例响应不能代替。→ FX-EXEC。
- **B13 / I6 未完成**; 划转日 BLIND 目前不自动停新开仓, 动作合同待裁。→ FX-W6C。
- **W6C 整套电池绑的是 `b3c5fc2`, 不是最终 `3f85c0e`**; 三分支 `merge-tree` 两两无文本冲突 ≠ 共同版本运行正确; 冻结包内**没有最终合并 head 的整套收据**。→ lead(叠加树 + 叠加电池)。
- **reshape docstring「no alpha is given up」须更正**(排序不变推不出 alpha 不变); 生产者与执行器重塑后是**不同意图**。→ FX-EXEC。
- 09-09 全书平仓: 新比例规则**对 09-09 仍因 52 名触发整书阶梯**, 不保证避免两次; 且未从交易所原始成交独立重建当时全账户 ⇒ 证据等级低于 09-12。→ FX-W6C(范围条款) / lead(措辞)。
- E10 / M5 / LED-06 未完成; 平仓 `mid_at_submit` 实为批前一次报价, 10.3911bps = 该批报价到成交的不利价差+手续费, **不能叫「从触发开始的所有损失」**。→ FX-EXEC2。

### 12.3 lead 裁定
1. **FXR-PROD-1 与 FXR-DATA-1 提到各自 owner 队列最前**(P1, 优先于本轮其余排队项)。其余 FXR-* 并入对应 owner 的现有队列, 不另开分支。
2. **复审的措辞更正一律采纳**(FXR-DOC-1/2/3, TRD-03 降级, reshape docstring, 10.3911bps 口径, Sharpe 窗绑定)。凡我方文档中的原句**保留原字节**并就地标注更正, 不静默改写 —— 与 §11 同规。
3. **CFG-06「无人看过分臂结果」的声明不成立**(lead 09-16 自查 + 复审 §7.4 同指): 见 §12.4。
4. **复审第 8 节五项建议**并入交接文档 §5 待用户裁定, 复审的建议作为默认推荐值随包上交, 不代用户决定。
5. 复审第 9 节的「下一轮最小可核交付」表**作为本纲领的出口门**: 安全包须**单一合并 head + 同版本叠加电池**; 数据须**支持覆盖与原始值分开 · PIT 生命周期 · 退出结算未知保持显式**; 平价须**逐列时钟/单位/dtype/mask/成员/归一化 + 实际消费 SHA**; 生产平价须**连续逐锚逐名**; 修复后模型验证须**旧输入旧模型 / 新输入旧模型固定归一化 / 新输入重训 三臂 + King/DL 拆臂与组合臂**。

### 12.4 CFG-06 分臂读数自查(lead, 09-16 03:1xZ, 只读)
草案 `DRAFT_PREREG_placement_eps050_reread_2026-09-13.md` §0 要求 lead 在冻结时声明「2026-09-05 12:00Z 之后无人计算过按臂 placement 结果」, 否则 **W0 移到冻结时刻**。自查结论: **该声明不成立**, 09-05 之后至少三处读过分臂量 ——
- **r14(09-12, 独立研究员轮次)** `r14_intent.py:234-236` `by_placement_arm_ERA2`: join **−7.7574** [−18.1223, −0.1554] n=19,513 · behind **+3.3603** [+0.2337, +5.9691] n=13,476 · exempt +7.5752 · None +2.622。**但该读数是零控制**: r14 RESULT §「臂在目标形成之后分配, 只动一个 tick 的挂单价, 不可能改动 [E,E+25m] 的价格路径 ⇒ join 与 behind 的 drift 之差**恒为零**」。故观测到的 ≈11.1 bps 臂间差 = **该估计量上分臂读数的噪声实测**, 与 r14 自己的「一个锚内诚实分辨率 5.25 bps · 日块 CI 偏窄」一致。
- **r17(09-12)** `r17_fillmodel.py:195` `by_placement_arm`: join f_w **0.8424** (n=9,652) · behind **0.8279** (n=7,080) · None 0.9410; maker 成交份额 join 0.8388 / behind 0.8462。**这是成交率结果读数**。
- **T3(09-13, 我方)** `RESULT_T3_markout_curve_2026-09-13.md` 行 206/207: R1 join **−3.96** [−25.80, +13.66] n=4,299 · R1 behind **+5.09** [−16.94, +39.67] n=3,306(两条 CI 都含 0)。**这是 markout 结果读数, 与 CFG-06 的 E 同族**。
**裁定**: (a) 按草案自身条款 **W0 移到冻结时刻**(≥ 09-16 冻结后的第一个名义锚), W1 = W0+28 日历天; (b) §0 增「已读数声明」逐项记上表数值与装置 sha, 冻结版不得删; (c) 装置**必须带零控制**: 同一估计量施于「臂不可能影响」的量(drift over [E,E+25m]) 与 **锚内臂标签置换零分布**, 零控制的 |Δ| 若超出判据带 ⇒ 本次读数**作废**(判据带按零分布重标, 不按日块 CI); (d) 精度表按 r14 实测(锚内 5.25 bps、日块 CI 偏窄)重估, 原「±11.5 / ±7.0 bps」按 INFERRED 保留并标注偏窄风险; (e) 复审 §8-2 的建议(保留在役已批准配置, 不把修 bug 的许可当作三个参数择优的许可)随包上交用户。

### 12.5 CFG-04 / CFG-06 冻结完成 + 深查盲态收紧(lead, 2026-09-16 04:1xZ)
| 件 | 冻结物 | sha256 | 提交 |
|---|---|---|---|
| CFG-06 | `docs/fixprogram_2026-09-13/X_COST/PREREG_placement_eps050_reread_2026-09-16.md`(含 AMENDMENT 1) | `ca2df32b…`(冻结初版 `b4c03b17…`) | 2b94d71f → e51fbf2f |
| CFG-04 | `docs/AMENDMENT_1_chase_restart_population_2026-09-16.md` | `edf789a1…` | 86c0227b |
- **CFG-06**: 已读数声明**不成立**(r14 零控制 / r17 成交率 / T3 markout / 深查日志逐臂拒单率四处)⇒ **W0 = 冻结后第一个名义锚(≥09-16 04:00Z), W1 = +28 日历天(≈10-14)**; 主推断改为**随机化检验**(同机制换 salt 重抽 2,000 次, 判据带 = 置换零分布 2.5/97.5 分位), 日块自举降为并报; **零控制 N1(drift over [E,E+25m], 真差恒零)+ N2(零分布须以 0 为中心)不过即读数作废**; **D1 裁定: UNDECIDED ⇒ 维持在役 eps 0.50**(不自动回退 0.35; 书行为须用户裁定 + 复审 §8-2), D3 停 behind = eps 0; 三项(0.35 与否 / eps 0 或 0.10 / 28 或 14 天)随包上交用户。
- **CFG-04**: 逐字采纳草案 `acdadd87…` 的 §1–§4/§6; **lead 复核已读数声明成立**(09-01 16Z 后只见臂平衡计数、治疗集行数与残差名义、X-COST 成本侧 pp, 无任何 H−X 读数)⇒ 停止规则与窗不动; §5 三选项 (a)/(b)/(c) 连同复审 §8-1 建议随包上交; 补充事实: 符合 X-A3 的非停机重建锚共 4 个, 对 n*₂ 进度影响小, 差别只在那 4 个锚是否继续付未成交毛额。
- **深查 cron 已替换**(旧 46dd536b 删除, 新 **a84f2bd4**, 同排程 `9 1,5,9,13,17,21`): 附注新增**盲态条**——「到 CFG-06 读数产出前, 分臂**只报臂平衡**(各臂计数 / behind 占比 / 逐臂残差名义作成本上界), **不报任何逐臂结果量**(拒单率 / 成交率 / markout / 成本 / 价差)」。历史越界的 6 条逐臂拒单率(09-10、09-11 各 3 锚)保留原字节, 已在 CFG-06 §0.5 + AMENDMENT 1 声明。

## §13 复工首轮工作者回报的新登记 + 裁定(2026-09-16 04:3xZ, lead)

### 13.1 新登记
| 编号 | 事实(工作者实测) | 级别 | owner |
|---|---|---|---|
| **PROD-31** | **08-29 20Z: 生产者根本没出 king 文件**(16:21Z 打印 `next 20:16:00Z in 14061s` 后无输出, 至 23:28:01Z 重启)。守护的守卫是 `[ -f "$TL" ]` ⇒ 循环体从不执行: **无页报、无日志行、`combo_live_last_anchor` 都不推进**; 执行器 N+24:00→N+29:00 轮询 21 次全 `{ok:false,"missing"}`, **整锚 HOLD、持仓冻结、`anchors_row: false`**。比 PROD-27 命名的「静默跳过」更严重。FX-W6C 在同一锚上独立测到同一事实(§5 洞的实例) | **P1** | FX-PROD |
| **PROD-32** | **该守护的全部告警路径在生产中从未被执行过**: 125 锚 `combo_live.log` 0 条 PAGE / 0 条 `skip aux-not-settled` / 0 条 `COMBO_LIVE ABORT`; 唯一投递证明是 08-26 手工跑的 4 行, **第一行 `status: NOT_CONFIGURED`**。且 `_page` 把异常吞成 `PAGE_FAIL` 后 `_bail` 照退 3, 守护又因看见 `COMBO_LIVE ABORT` **故意不页报** ⇒ **bail + 通道坏 = 端到端静默**。告警通道正控已裁定为 PROD-27 修复的一部分 | **P1** | FX-PROD |
| **PROD-30** | G1(守护跳过 `NOW-A>1355`)与 G2(`combo_stage` bail `A+1360`)**仍按已退役的 N+23:00 标定**; 执行器 08-27 05:2xZ 起读 **N+24:00**(`anchor_offset_min=24` / `poll_grace_min=5`, 重试到 N+29:00)⇒ **G1 比首读早 85 s 关门, G2 早 80 s** ⇒ 本可按时写出的 combo 形态被主动放弃、改交 king 形态 | P2(**书行为, 待用户裁定**) | lead → 用户 |
| **PROD-28-STALE** | AUDIT_PROD PROD-28(「运行中进程执行盘上代码/bundle/F10 模型」)是对 PID 10900 / 30944 / 30943 验的; **09-14 15:43:56Z 重启后三守护为 797/801/812, 15:45:14Z 起** ⇒ 该验证记录**已过期**, 复审包中引用它处一律标 STALE 直到重取 | P2 | FX-PROD(重取) |
| **OPS-04** | `ops/daily_summary.py` **既无 launchd 作业也不在 `docs/CRON_TEMPLATES_2026-09-04.md`** ⇒ 今天没有任何东西调度它 ⇒ LED-08 的每日漂移告警落地后也不会响(「已声明的盲区≠已关闭」同族; 一个没人调度的告警不是告警) | P1(投递) | lead(部署 runbook) |
| **PROD-33** | `combo_live_status.json` 是**单槽可变文件**, 两条静默分支上都保留上一锚的 `{"ok": true}` ⇒ 读者不比对 `status["anchor"]` 就会读到上一次成功(与 P2 AMENDMENT 12 同一对象) | P2 | FX-PROD |
| **PROD-34** | 排练模式用 `WS` 而非 `_outdir` 备份(`combo_stage.py` L340)⇒ **写进实盘状态树**; 08-26 00Z 因此有 king 备份却无 combo 运行 ⇒「有备份 ⇒ 跑过 combo」的朴素判据误计(装置污染被测对象同族) | P2 | FX-PROD |
| **DATA-COR-1** | 交接 §4.5 与 FX_DATA/STATE_PAUSE 写「run 1 在 writer 处失败」**不准确**: traceback 是**重载回环**被拒 —— `Artifact.load` 比 spec sha `['99ae35e01ec3dd`(shape-(1,) 数组的打印)与模块的 `99ae35e01ec3dd06`; 根因同(`np.ascontiguousarray` 提升 0-d 标量), 但抓住它的是**工件自身的守卫**, 这才是收据里该留的部分 | 记录 | FX-DATA(已自报) |

### 13.2 裁定
1. **PROD-27 严重度按「因 × 果」两维**: `late_producer` ⇒ HIGH; `late_daemon_start` ⇒ 默认 INFO/计数, 但同锚出现 (i) 执行器无可用外部书(HOLD / `ok:false` / 无 LIVE phase_A 行) 或 (ii) 连续 ≥2 锚落静默分支 ⇒ 升 HIGH; **PROD-31(无文件)不进该分裂, 一律 HIGH**。三者都必须具名 + 计数 + 进逐锚记录。
2. **「哪个形态被交易」不归生产者**: 生产者只记 `form_written` + join key(anchor / json_sha / written_utc); **traded 是执行器的词**(`phase_A.external_book.producer`)。受据: 09-02 00Z 与 09-09 12Z 有 combo 文件却无 LIVE phase_A 行。对账由读者做并给出定义。
3. **LED-08 不把 δ 折进触发条件**: 检测(离开被刻画的 regime)与实质性(K2 书层 δ 0.05 bps/锚/gross)分层; 经济换算(+0.026 bps/锚/gross)照印不照判。**一个真实的水平位移可以落在书层实质带以下** —— 这句本身是给 K5 的输入。
4. **B13 参照锚 = 最新 `anchors` 行 + 具名排除**(按 `live/rebalance_id.py:26-30` 的性质判别, 禁按 `FLATTEN-` 名字判); 动作**只停开仓, 不平书, 不写 `tripped_at`, 不 `set_reduce_only`**; `last_eval.json` 的五种缺失态各自具名(缺失/不可读/非法/mode 戳不符/比本锚旧), 默认动作 = 与「书未被观察到」同义; **DRY_RUN 必须是显式负控**; **每次打印用了哪个参照**。队列重排: B13 → 平仓行时间戳 → FXR-W6C-1 → I6 → cond4。
5. **B13 的基率照实写**: 47 天 293 个锚键里该形态 **0 次** ⇒ 预防性修复, 论证重心是假阳性代价(最坏一锚不开新仓)对真阳性代价(三守卫印 CLEAN 地对看不见的书开仓)。
6. **十月决策单(D1–D5)转用户**, lead 全部同意 FX-TRAIN 的推荐; **TRN-27 的 runbook 文本更正必须先落地再要裁定**(runbook 写 `0fe5ec55`/`b2f9cfd4`, 当前对象是 `d99a9109`; 批准 b2f9cfd4 等于批准「放行导出器会崩的输入」的门)。TRN-07 并进 TRN-01、TRN-11 只接线不改值、LIN-01 回退(pod2 只读 + 断言 sha + 具名未闭合边界)三条确认。若 09-25 前未裁, **批准准备仅供排练用的豁免门副本**(明确标注, 不得进真跑路径, sha 与真门并列登记)。

## §14 电池窗口事故 + 第二轮登记与裁定(2026-09-16 03:2xZ, lead)

### 14.1 ★ 电池规则按传递闭包重述(全体工作者, 立即生效)
**事故**: FX-EXEC 于 **03:16:25Z 起跑 `live/tests_acceptance_entrypoints.py`**, 该套件第 85–90 行**两次 `bash run_acceptance.sh`**(做入口逐字节对比)⇒ 整套电池连同 `tests_entrypoint_wiring` 一起跑了; 窗口 01:05Z–03:15Z 已于 **85 秒前关闭**(原写「70 秒」是估计; FX-EXEC 自行重算: 03:16:25Z 距锚 11,785 s, 限 11,700 s ⇒ **85 s**), 且**未取 `BATTERY.lock`**。03:18:49Z 由工作者自行 kill。
- **出去的是什么**: 只有未签名的公共行情 GET(证据 = 克隆内 DRY_RUN run_anchor 写出的 `exchange_info_cache.json` 03:17:59Z / `funding_last_pull.json` 03:18:00Z / `panel_cache/funding.npz` 03:17:47Z / `panel_cache/klines_1h.npz` 03:17:11Z ⇒ 端点为 exchangeInfo、funding/premiumIndex、klines)。**权重数不可得**(套件日志 0 字节, kill 时 stdout 仍在缓冲)——**工作者如实写「给不出」, 这是对的**。
- **没有发生的**(按树断言, 非假设): 克隆无 `.env`; `BINANCE_API_KEY` 未设; `LIVE_MODE` 未设 ⇒ 默认 DRY_RUN; `state/pilot_log/20260916/` 只有 `_schema.json`, **无 orders.jsonl / fills.jsonl** ⇒ 未下单未撤单; `~/dl_quant_live` 与 `~/wide_shadow` 未被触碰。
- **lead 风险核(03:21Z, 只读)**: 04Z 锚**尚未开始**, GET 距锚起点 42 分钟, 场所权重窗为 1 分钟 ⇒ 已完全衰减; 00Z 锚峰值 847/2400, 远离上限 ⇒ **对下一锚无实际影响**。不改变违规性质。04Z 锚跑完后由 lead 核 `rate_budget` 与 −1003/−4400 计数并补进收据。
- **规则重述(取代原文按名字判的写法)**: > **任何会直接或间接执行 `run_acceptance.sh`、或发出任何场所请求的套件, 一律受同一窗口(N+65min..N+3h15m)+ `BATTERY.lock` 约束。跑任何套件前先 grep 其 `subprocess` / `bash` / `os.system` / `requests` 调用; 判不准即当作受约束。** 已知传递到达者: **`live/tests_acceptance_entrypoints.py`**。新写的 gate_coverage 类格一律放进**不 shell-out 的套件**。
- **连带发现(单独一格)**: FX-EXEC 继承克隆时 `state/` **本就不干净** —— 约 20 个被修改的跟踪文件 + 大量未跟踪件, 时间戳 2026-09-13T18:01Z, 即上一轮电池结束时**没有按规则还原 `state/`**。要求 FX-EXEC 逐项给出: 被改文件清单、是否影响其已交付的任何红/绿判定、还原后的树 sha; 任何依赖该残留的格必须重跑。
- **处置纪律记录**: 工作者 ① 立即上报且在继续工作之前上报; ② **故意不跑 `git clean -- state`**(那会删掉套件要读的既有未跟踪真实状态副本)—— 两条都对, 留作先例。事故日志 `INCIDENT_battery_outside_window_20260916T0316Z.log` 随收据入库, 不得抹除。

### 14.2 新登记
| 编号 | 事实 | 级别 | owner |
|---|---|---|---|
| **PROD-29 重定级** | VERIFIED_IMMATERIAL/P3 → **DISPUTED/P2**(见 AUDIT_PROD 就地标注, 提交 4f86635a): 侧车在 **128/129 锚**上是 `state_H_f10_<A>.npz` 的**最后写者**(±1.0 s), `combo_stage` 的链状态每锚被丢弃 ⇒ 用 `combo_stage` 代码重算该状态的回放**按构造**与实盘不同(= P2 的 96 名 2.63e-8); **79/129 次写入落在执行器首读 N+24:00 之后**; 「0 次碰撞」是错的检验 —— 没有碰撞是因为侧车每锚都赢 | P2 | lead(已改) |
| **PROD-36b** | **08-29 20Z 无文件 ⇒ 无 `state_H_f10_1788033600.npz` ⇒ 08-30 00Z 唯一一次 `h_source: king_fallback`, `self_parity_maxdw` 6.58e-3 vs 其余锚 ~2.3–3.2e-10(差七个数量级), 且 `h_source` 上无任何页报**; 同锚 combo 又静默跳过 ⇒ 该链状态只由侧车写成。**两个静默缺陷是同一次事故的两截** | **P1** | FX-PROD(并进 PROD-27) |
| **PROD-35** | 侧车的 `LAST` 是内存 shell 变量(`sidecar_daemon.sh` L4)⇒ 重启后按 `ls -t | head -1` 重处理**过去的锚**并在数小时后覆写其链状态。四次实例: 08-24 08Z(+2.84h)· 08-29 16Z(+7.50h)· 08-30 04Z(+1.09h)· 09-14 12Z(+3.79h); 其中 **08-30 04Z → 08-30 08Z 与 09-14 12Z → 09-14 16Z 两次确实把事后重写的状态喂给了随后的实盘锚**。四次都未拉入锚后市场数据(0.8–2.4 s, 无 171 管线重建, 复用各自锚的 `mini/cache.npz`), **但该否定是有条件的**(缓存检查只按锚) | P2 | FX-PROD(排 PROD-27 之后) |
| **LED-08 交付缺口** | = OPS-04, 由 FX-EXEC2 独立测到并具名(D9): 无 plist 引用 `ops/daily_summary.py`, 亦不在 cron 模板 ⇒ 判词今天无人调度; **levels 仍每锚经报告基线行到 Telegram** | P1(投递) | lead |

### 14.3 裁定
1. **P12 的可观测性并入 PROD-27 修复**(不另开对同批文件的改动); 逐锚记录必须带 **`h_source`** 与**写者身份**, 且 `h_source != own` ⇒ 具名事件 + 计数(否则对 08-30 00Z 那类情况仍是哑的)。**侧车的写入行为本身(谁赢)另案**, 属书行为, 需配对回放 + 用户裁定, 由 lead 上交。
2. **可交易性工件 sha 钉定**: FX-DATA run 2 产出 `tradability_v1.npz` **sha256 `54d409d0ddf695f497d8b27fb5bdee960deda763250d530a16bd7cf506205302`**(2,501,576 字节, 10,285 锚 × 829 名, `reload_roundtrip: true`, 装置 066c3d74 / 模块 a9fad82c / spec 99ae35e0, numpy 2.4.6)。P2、FX-MODEL、FX-TRAIN 一律钉这个 sha。**核对无残差**: 工件并集轴 14,142,095 冻结行 − 审计 13,770,575 = **371,520 = `AD_H.H1_x0910_tail.untraded_rows_of_those` 精确相等**(129 个已死名 × 2,880 尾行); 156 死名两轴**逐名相同**(对称差为空); 60 名死后资金费按**工件自己的 `last_traded_ts`** 复现(60,438 事件)。定义差 841 格全部是「无紧邻前一根 bar」(826 首根 + 15 NODATA 缺口后首根), `last_traded` 行 **0/829 改变**。**run 1 的字面命令从未被记录** ⇒ run 2 的 `receipts/run2_fx_trd_build.sh`(a63e2935)是本工件的权威命令, 不回填看似合理的行。
3. **LED-08 判据按 FX-EXEC2 交付版**: `|median_now − median_ref| > 3 × 1.4826 × MAD_ref` 且两侧 ≥12 锚; taker 漂移 **+16.570 pp** vs 线 10.431 pp ⇒ 报警; |net/gross| **+0.664 pp** vs 1.021 pp ⇒ 不报; 费侧换算 **+0.0235 bps/锚/gross** vs K2 δ 0.05 **照印不照判**。**口径声明必须留**: 报告口径(`topup_taker` 订单行的成交名义占比)与 X-COST 口径(fill 级 `venue_maker_flag` 的 M/(M+T))**此处相差约 2 pp 是算术巧合, 不是构造上的一致**; config 里 X-COST 口径标 `NOT_this_caliber`。MAD_ref = 0 的退化参照**拒绝给判词**并说明理由, 两个 level 与 Δ 仍照印。

## §15 第三轮登记与裁定(2026-09-16 04:0xZ, lead)

### 15.1 ★ 提交纪律: `.gitignore` 静默吞文件(全体, 立即生效)
**事实(FX-DATA 自查发现并自报)**: 研究仓 `.gitignore` 含全局 **`*.npz` / `*.csv` / `*.csv.gz`** 与**目录名 `logs/`**。`git add <目录>` 对目录内被忽略的文件**不报错** ⇒ 提交静默少带文件。`d32465c7` 因此只带了收据与日志而**没带工件本身**, 尽管 `git show --name-only` 被读过 —— **读的人只核对了「我期望的文件在不在」, 没核对「我声称的东西有没有缺席」**。已由 `b4d60d73` 用 `git add -f` 修复, 两个 npz 的入库 blob 内容哈希与收据相符(`54d409d0…` / `1e85aaf6…`)。
- **规则**: 收据类 `.npz` / `.csv` / **任何路径含 `logs/` 段的文件**一律 `git add -f`; **`git show --name-only` 要读「缺席」而非只读「在场」**; 关键收据用 `git ls-files --error-unmatch <path>` 逐条验。
- **lead 全仓核(04:0xZ)**: 纲领与审计两目录下全部 `.csv` / `.npz` / `.csv.gz` **现已 TRACKED**(`AUDIT_PROD_columns.csv` · `receipts_prod/parity_f10_columns.csv` · `receipts_prod/parity_king_columns.csv` · 两个 FX_DATA npz)⇒ 暴露只此一处且已修。`logs/` 段匹配无法一次扫完, 已要求各线自验并写进报告。

### 15.2 新登记
| 编号 | 事实 | 级别 | owner |
|---|---|---|---|
| **TRN-28** | `pod_f10_np_export.py` 在**自己的 V1 门判词之前**就写出可部署 npz(`np.savez` L56, `sys.exit(0 if ok else 3)` 在其后), 且默认 `F10_OUT` **就是在役工件路径** ⇒ **失败的门仍在实盘路径留下完整可加载模型并覆盖原件**。比审计的「产生在所有门之外」更锋利: **门存在, 只是判词不控制写入**。与 FXR-PROD-1(修正态先于控制落盘)同族 | **P1** | FX-TRAIN(并进 TRN-03) |
| **LED-09** | NEW-02 修复之后, 实盘 `fills.jsonl` 里**已落盘的 7,312 行**(09-12 平仓批)仍带 `attempt_idx 2` 而其订单行是 1 ⇒ 按 (rebalance_id, symbol, order_type, attempt_idx) 连接的读者仍漏这 7,312 行。账本只追加 ⇒ 走 **LED-04 修订记录同族**, 与 LED-03/04/05 一同由 lead 在复审时执行(先 `--rehearse` 于实盘根, 再 `--apply`, 锚窗外) | P2(实盘写回) | lead |
| **RES-01** | 两个研究装置按该缺陷键连接 orders→fills, **受影响**: `retrain_2026-09/health_check_2026-09-05/calib/markout_diag.py:16,24`(平仓成交丢 `spread_at_submit_bps`)与 `calib/cost_calib.py:118,120`(平仓成交的 BNB 费变得不可归属, 计入 `nofee`)。**限定句必须保留**: markout_diag 的已发布窗 08-26..09-05 不含整书平仓 ⇒ **没有已发布数字会动, 缺陷在代码里**。`export_fills_for_markout.py` 与 `survey_keys.py` 传播该列 | P2 | 待派(非 FX-EXEC 分支) |
| **TRD-02 更正** | AUDIT_DATA「秩基 0.7–5.3%」用的是描述性旗标; 因果条件 `¬tradable = UNTRADED ∪ NODATA` 实测 **2.34–6.68%**, 且 **2026 年几乎全是 NODATA**(Z24 看不见)⇒ 原行对 2026 **低估约 7 倍**。已就地标注(bf809ed6) | P2 | lead(已改) |

### 15.3 裁定
1. **EXE-04 走「核 + 断言, 停在接线之前」**: FX-EXEC 建纯联合可行性核 + 复审的 40 条断言(驱动自 `GRID_SOLUTION_SETS.json`), **停在执行器接线与 41 天回放之前**, 交具名余项(接线四处 · 41 天回放 · PREREG §3.6 要求的逐条重新论证)。理由: 「今天可合并」并不存在(被复审/部署的是三分支叠加树, 另两条未完); 相关性风险几乎全在精确联合可行集里且自包含; 接线那半改书行为, 本来就要先过 41 天回放与独立复审。**`GRID_SOLUTION_SETS.json` 只读取用**: 复制进克隆当外部夹具并记来源路径 + sha256 + 其所在提交号; **禁 fetch / checkout / merge 那条分支**。
2. **电池锁本轮优先序: FX-EXEC → FX-EXEC2 → FX-W6C**(FX-EXEC 的链已完整)。锁文件写名字 / PID / 树 sha / 起始时间, 跑完即删; 跑套件前按 §14.1 grep 传递调用。
3. **NEW-02 的做法记为正例**: 「attempt 随腿走」; 并记下那个坑 —— FLATTEN client id 结尾是进程级计数器 `_FLATTEN_SEQ`, 真实 12Z 批上是 **255 个互异值 1..255** 对 255 条全 attempt 1 的订单行 ⇒ **解析后缀比缺陷本身更糟**(已成为对着真实夹具的断言格)。两个写者都硬编码却一直「看起来对」, 是因为**实盘历史上每次阶梯都在第一次尝试成功**(8 个平仓日 1,708/1,708 全在 attempt 1)—— 这解释了此类缺陷为何没有行为签名。
4. **gate_coverage 重复键的断言必须在源码层**: 重复键由**解析器**消解 ⇒ `len()` 对、键在、`verify()` 过、`tests_external_book` 自己的 S7 也过, **损失没有运行期签名**。故用 ast 扫每个 dict 字面量报出重复常量键的全部行号, 并用 `verify(self_path=)` 指向植入夹具来断言**接线**(改名不能让它失效)。写检查时发现检查自身的 bug(`sorted()` 混合 int/str 键抛 TypeError ⇒ 本该报告问题的东西反而崩掉门)= 「患处再过一行」正例。
5. **TRN-27 的两条方法论收进纲领**: ① **读 diff 而非修订说明**(因此发现 `b2f9cfd4` 先转 int64 再校验, `[False,True]`→`[0,1]` 过门而导出器用持久化数组下标会 IndexError); ② **删掉按构造就会过期且已被自我免责的冻结 sha 表**, 换成测量命令 + 已提交清单; ③ 新门拒绝**截断 sha**, 判其为「标签而非身份」。

## §16 第四轮: FXR-PROD-1 实测规模 + 交付确认(2026-09-16 04:2xZ, lead)

### 16.1 FXR-PROD-1 的红比复审的夹具大一个量级(FX-PROD 实测)
对复审点名的同一份文件(sha `1cbeca90…`, 逐字节确认相同), **把工具喂它自己的修正输出**(= 每月常规对账对状态副本所做的事):
| | 首次运行 | 修复前重跑 |
|---|---|---|
| 修正被应用 | 534 + 65 | **599 条全部重做** |
| 存储标签冲突 | 0 | **598**(复审夹具只显 1) |
| 控制 `max_abs` | 6.94e-18 | **4.0958e-06**, `n_gt_1e12` **70**, `n_gt_1e9` 17 |
| 退出码 / 状态文件 | 0 / 发布 | **0 / 照常发布, 5.1 MB** |
⇒ **三个独立探测器都响了, 它仍以成功码发布。**
**修复三项按合同**: (a) 输入状态自己的账本尾部对它持有的行**具权威**(在源头杀掉重复计数; 原先冻结源先加载 + `setdefault` 钉住陈旧标签); (b) 冲突逐类分型 —— `frozen_vs_frozen` 与 `rate_differs` 拒绝, 输入标签只在**有出处**时接受(等于声明值, 或来自另一冻结源), 否则拒绝; (c) 控制**总是**运行且**闸住发布** —— 输出先写 `.tmp`, 六道门全过后才经 `os.replace` 露出可用文件名, 否则删除临时文件并 **rc 2**。
**绿**: **K1/K2 回归** —— 修复后的工具在原输入上发布出与**修复前逐字节相同**的状态(`fc3125ad282584bf`), 同样 599 条修正、同样控制 `6.938893903907228e-18`, 六门全绿 ⇒ 一次性迁移未被触碰; **R1/R1b** —— 重新进入已修正状态时 **598 条尾内修正 0 条被重做**, 唯一残留是**尾外**行(ONG, dacc −3.4e-08), 被正控抓住 ⇒ `rc 2, 不写文件`; **N3** 598 条带出处解决, **0 条不可解释**; **N1** 尾外修正在无显式旗标时被拒, `rc 2`, 无文件。**移除的 9 行全部是语义被替换的那几行**, 对 diff 的移除侧 grep `assert|need(|gate` 为空。
**结构性限制(接受, 并按合同四条同时成立)**: 离开账本尾部的结算在状态里不带标签, 而**修订标记救不了 —— `shadow_loop_v3.py::save()` 写固定键集, 下一个锚就会丢掉它**。故 `--allow-out-of-tail` **默认关**; 一次性换装迁移传它(恰好 1 行); **每月常规作业永不传**; 控制在被传时仍是兜底。四条缺一不成立, 写进 swap plan §2 步骤 3 与 §7。
> **由此得到一条通用否决理由(新)**: 任何把「我已吸收到哪一版 / 哪些行」写进生产者状态的方案, 都会被 `save()` 的固定键集**静默抹掉** —— 不只是本项, 是一整类设计的否决。

### 16.2 其他交付确认
- **PROD-28 重取完成**: **10/10 文件 `DISK_IS_RUNNING_CODE`, 0 unknown**; bundle `MANIFEST.json` `af61d597` **8/8 相符**。方法学按裁定写明: **「mtime 早于进程启动」是全部主张, `lsof` 只作佐证, `git HEAD` 故意不用**。**该装置自己犯了它存在就是为了抓的那类缺陷**(找 `MANIFEST` 而文件名是 `MANIFEST.json` ⇒ 报 `bundle_mismatch=None`)—— 「缺字段就跳过」同族; 现改为缺失或 0 条目即硬退出。F28.5 记录对 b891748 的比对**连同其取证方法**。
- **P5 通过门**: 81/81 已记录行**逐位复现**, `max_abs_diff 0.0`; 席位 w3m king 0.382095 → 0.384765。**P1 迁移** 525 名 0 冲突。**装载测试经验性确认部署条件**: 新码遇未迁移状态 ⇒ `REFUSE_TO_START: FUND_COL80_V0 but state has no ema_v0`(实测拒启字符串, 钉进 swap plan)。
- **换装 dry run 完成**: 各步 rc=0, `LIVE_RO unchanged`, 5m29s, **占用 24 MB**(p5 9M / corr 5M / compose 5M / p1 4.9M)。
- **zsh 不分词第二形态**: `$PY` 从未执行而 `rc=$?` 读到的是 `tail` 的状态 ⇒ 失败的验证报 `RC=0`; 靠**读输出**抓住。**追加规则: `rc=$?` 必须紧跟被测命令, 中间不得隔管道或 `tail`; 有管道用 `PIPESTATUS` / `pipestatus`。**

### 16.3 裁定
1. **顺序冲突是 lead 的错**: §12.3-1 的裁定(FXR-PROD-1 提到最前)为准, 后一条消息里「现在写 PROD-27 修复」作废。FX-PROD 取的顺序正确。
2. **P9「UNRESOLVED 即拒绝」的门需要 zip 可得性前置条件**(FX-PROD 实测非 exact 行: 八月 0 / 七月 1 / 九月 **305** ⇒ 原门每月必挂)。**裁定**: 两种 UNRESOLVED 必须分开 —— ① **证据尚不可得**(zip 未发布 / 拉取失败)⇒ 具名 `EVIDENCE_NOT_AVAILABLE` + 记录待重试, **只在受影响行真正进入本月训练输入时**才阻断; ② **来源彼此矛盾** ⇒ 真拒绝并阻断。**任何情况下不得把 LIKELY 静默升成 EXACT。** owner: FX-TRAIN(门) + FX-PROD(表), 两方直接对。
3. **FX-MODEL 的自更正确认**: 其暂停note 第五项是 **P10(float16)不是 P11**, 名下无 P11 事实; P11 按纲领定义走。**复现 aud-prod 的 `members_audit.json` 而非照单引用、且不搬运其 `VERIFIED_IMMATERIAL` 标签**(该标签只覆盖 147 个近期锚且无下架)—— 批准且记为正例。
4. **FEA-01 的交付物本体是「归一化那一行」**: cols 80/81 的 mu/sd 在训练器**哪一行**算、存进**哪个工件**、其 **sha**、服务路径**实际读哪一个** —— 四项缺一不可, **读训练器代码得到, 不从工件反推**。臂 B 若重算 mu/sd 即**另一种干预**, 必须改名。
5. **dtype 二义性的推论写成要求**: `nan_to_num(…,0.0)` 后存 float16 ⇒「缺失」与「真零」成同一 token ⇒ **重建必须带独立的可得性位**, 而不是换填充值(换填充值只是把二义性搬个地方)。

## §17 ★ W6C-I6 = 已存在的全书平仓路径 + 第五轮登记(2026-09-16 04:4xZ, lead)

### 17.1 I6: 非计划运行持有书时会平掉整本书 —— 真实行上实测 96.39% of gross
**这不是假设, 也不小。** FX-W6C 按裁定**先测可达性**: `devices/probe_i6_offschedule.py` 扫实盘 `state/anchor_runs.log`(37,611 行, 999 次运行, 2026-07-25…09-16), 把每条 `anchor start mode=` 与其 phase_A 记录配对 ⇒ DRY_RUN 570 次非计划, TESTNET 2 次, **LIVE 3 次**: 2026-08-01 06:29:29Z(−90.06 min)· 2026-08-01 10:03:18Z(−116.36 min)· 2026-08-02 05:31:47Z(+92.02 min)。**可达, 而且已经达到过。**

**机制**: gate 0c 拒绝开仓单**且刻意不返回**(reduce-only 路径必须继续работать)。该锚随后仍然规划、定价、写出一条带**正 `target_gross`** 的 `anchors` 行、**不提交任何单**、且**不带 `halt_kind`**。于是 `position_break._intended_by_anchor` 落到最后一个分支: 意图 **ZERO**, `halted_intent_flat` ⇒ 限额变成 `PB_HALTED_FLAT_PORTFOLIO_FRAC = gross 的 1%`, 且**分边不被允许对平意图发言**(设计如此, 否则会赦免 2026-07-29 的幽灵书), `frac = Σ|readback| / target_gross`。

**三次为何无害 —— 是运气不是设计**: 两次到达 phase_C 的 LIVE 运行都被判 `halted_intent_flat` / `flat_intent_legacy` 并 CLEAN, **唯一原因是书是空的**。08-01 06:29Z 那条记录 `target_gross 4234.690812343863`, **109 条订单行 0 条提交**, 回读 `Σ|venue_position_notional| = 0.00` —— 那是部署的第一个锚; 08-02 05:32Z 紧跟 04:18Z 的保护性平仓。`dev_frac 0.0` 对 `0.01`: **压线靠的是时机, 不是设计**。

**带着书会怎样 —— 实测, 非论证**: 用**同一个锚自己的行**(它的 `anchors` 行, 它那 109 条从未提交的订单行, `target_w` 与 `mid_at_anchor` 原样)重键到该日 20:00Z 锚之后一小时并持有该锚的真实书(回读逐字拷贝, 因为期间没有成交)。在 ef60f85 与修前头上: `halted_intent_flat`, 门 `flat_intent_legacy`, **`dev_frac` 0.9639 对限 0.01**, `triggered=True`, `tripped=True`, **`flatten_all` 105 单 `reduce_only=True`**。平意图的 break **不带名字范围** ⇒ EXE-01 的比例门把它路由为书级, 阶梯拿走整本书, **而且就在同一次运行里**(看门狗紧跟 phase C)。
> **在任何一个普通交易日, 一次 LIVE 非计划运行都会平掉整本书。至今没发生, 只因为三次都落在空书上。**
> 这是「我方仪器的假阳性造成全书平仓」这一族的**第三例**(前两例: E-0912-A reduce-only 截量 × 身份核对; 09-09 账本缺行触发逐名门)。

**修复**(与 EXE-01 的比例局部响应、B13 的未观察书同形): `anchors` 行带 `halt_kind=off_schedule`, 该 kind 加入 `position_break.BOOK_HELD_HALT_KINDS`(B13 已把它做成判官里唯一那张表)⇒ 该锚按**持有的书**对目标向量判定, 残差 ≈0(什么都没成交), 分边可以发言, 缺口读作**欠填** —— 它会告警并由下一锚重新瞄准, 这才是正确读法。**清空书的 kind 绝不能进那张表**: 写者带 `and outA.get("action") != "FLATTEN"` —— 阶梯的 FLATTEN 是**故意**在平书, 而看门狗 trip 之后书已经被平; 两者都保持意图 ZERO 与抓幽灵书的 1% 规则。
**红→绿**: 新套件 `live/tests_offschedule_held_book.py`, ef60f85 **9/13 rc=1**(到达汇总行; 头条红就是上面那次 105 名平仓), 修后 **13/13 rc=0**。反事实自成一格: 在同一棵树上剥掉标记, 同一本被持有的书又被按意图 ZERO 判定并 trip, 书级, 105 名。四个突变体各自红在拥有该性质的格上。
**未证明**: 非计划运行**是否本就不该可能** —— 那是 gate 0c 的裁定, 未触碰; 1% 是否是平意图的正确限额 —— 政策, 未触碰; 第三次 LIVE 非计划运行(08-01 10:03Z)**没有留下 phase_C 记录**, 其锚如何被判定 NOT CHECKED。

**lead 追查的触发机制(只读)**: `com.dlquant.live.anchor` 的 plist 用 **`StartCalendarInterval`** 六个固定时刻(本地 8/12/16/20/0/4 = 00/04/08/12/16/20Z), **无 `RunAtLoad`**。launchd 对日历作业的语义是**机器在计划时刻睡眠或关机则醒来后补跑** ⇒ **只要 Mac 跨过一个锚分钟睡着或关机, 醒来后就会产生一次迟到的 LIVE 非计划运行**。今天唯一的防线是 `com.dlquant.live.nosleep`(caffeinate, PID 815)—— **单点**。已令 FX-W6C 把三次逐一定性(人手跑 vs launchd 补跑), 判据取 `launchd_out/err.log` 启动行、`pmset -g log` 睡眠-唤醒、`kern.boottime`、以及该次运行的 `mode=` 与父进程线索。**能区分两者才算测完**: 前者可用操作纪律避免, 后者不能。

### 17.2 W6C-B13 交付(同一提交链, 头 5a04f64; B13 = 1483e41, I6 = 5a04f64; 研究仓 f5047ac0)
- **缺陷在真实 08-01 行上被证明有后果**: 该日最后一个计划锚以一次真正的 §4-5e BREAK 结束(同文件里 20:18Z 的 FLATTEN 批就是对它的响应)。**删掉那一个锚的回读行, 评估就报 CLEAN**, 判在前一个锚上, 什么都不 blind —— **守卫自己的 trip 随回读一起消失, 而且没有任何东西说明原因。**
- **参照 = 最新 `anchors` 行, 且判在「AT 那个锚」而不是「at-or-after」**: 阶梯自己的平仓后回读是**一本刚被关掉的书**在 18 分钟后的回读, 把它算作覆盖正是那个锚的 BREAK 未被检视的原因。已验证该参照排除全部 10 个 flatten 批, 并在 272 个健康锚上等于被判锚。
- **生产者陈述原因**: 四个不同事实都会写出零回读行(读抛异常 / DRY_RUN 无账户 / 回读宇宙为空 / 被拒的行截断写循环), 在日志里是**同一个可观测量**。`finalize_anchor` 现返回 `book_observation`(OBSERVED / OBSERVED_EMPTY / READ_FAILED / NO_ACCOUNT / WRITE_TRUNCATED / NO_LOGGER)。**`fin` 现在在其 `try` 之前绑定** —— 否则一次 phase_C 失败会以 NameError 带走整个看门狗块。
- **响应**: `ev["book_observability"]` **刻意不放在 `conditions` 下**(新条件需要自己的 trip 路由, 而这件事永不得到达阶梯); 5b 增 `UNOBSERVED` 态; 5b/5e/cond7 继承 `blind` ⇒ 经 `conditions_blind` 页报并拒绝 resume, 无需新接线。开仓停用 `anchor_loop.book_unobserved_halt`, 经 mode 戳读者读 `last_eval.json`: **不写状态、不设 `tripped_at`、不碰账户级开关、不关闭任何东西**; **按事实自愈**(下一锚在开仓被停期间仍写回读 ⇒ 下一次评估即 OBSERVED, 门自行停止触发, 无计时器无计数器无需人工清理)。**部署边界**: 本次构建之前写的评估没有该键 ⇒ 返回 halt=False, 具名 `NOT_EVALUATED`, **且不页报**(对它页报会打破 `tests_signal_and_loop` 的「半夜不叫醒任何人做无事」那一格 —— 作者抓到并**去掉页报而不是去掉那一格**)。`anchors` 行带 `halt_kind=book_unobserved`, 使 §4-5e 不把被停的锚按意图 ZERO 判定而在下一锚触发阶梯。
- **红→绿**: 新套件 `live/tests_book_observability.py`, 夹具建自**真实**已提交日 `state/live/pilot_log/20260801` + 持有该锚真实书的 MockBroker。ef60f85 上 **15/48 rc=1**(到达汇总行; 15 个绿是两棵树都绿的格 = 正控); 修后 **48/48 rc=0**。**六个突变体**各自红在拥有该性质的格上。负控在两棵树都绿: 未动的真实日仍检出 BREAK 并动作; 真实 20:19Z FLATTEN 批不使任何东西 blind; 真实 2026-08-29 HOLD 锚形态不 blind; 从不观察书的树(DRY_RUN)是 `NEVER_OBSERVED` 且不停开仓; 对**正在 blind 的那棵树**做 §4-5a 断供仍然 trip 且仍以 reduce-only 平仓。
- **AST**: 恰好一格既有断言被改(57 → 57), 即 `tests_proportional_response` 的 B13 等价控制格, 原本钉 U1 的 `blind: []` 为「本移植不改变该路径」并已由 `FACT_TABLE_W6C §10` 登记为 EXE-01 之外的检测缺口; 现断言 `[cond5, cond7]`, 改动与理由写在该格之上。其余每个套件的每条断言逐字节不变。
- **未证明(不得读作覆盖)**: 一次在写任何行之前就死掉的运行不留任何行, 此处抓不到(2026-09-09 12Z 锚完全不在记录里 —— 那是场外 deadman ping 的问题); HOLD 锚(无 `anchors` 行)且账户读也失败时只对生产者的判词可见; **被截断的回读具名 PARTIAL 且不停开仓** —— 短写是否该停, **无人做过裁定**; EXE-01 比例门的分母仍取自被判锚(`watchdog.py:2346`), 陈旧的被判锚会用更旧的 gross 给 2% 检验定价 —— 已报告, 未重基, 数值 NOT CHECKED。

### 17.3 新登记
| 编号 | 事实 | 级别 | owner |
|---|---|---|---|
| **W6C-I6** | 见 §17.1: 非计划 LIVE 运行 + 有书 ⇒ 全书平仓(真实行实测 dev_frac 0.9639, 105 单); LIVE 已发生 3 次, 全落空书 | **P0 级实盘风险(修复在克隆, 未部署)** | FX-W6C(已交)+ lead(止血与部署优先级) |
| **TEST-01** | `live/tests_reduce_only_clamp.py` 往仓库真实 state 树写 `state/venue_ban.json`(FX-W6C 在 17 个套件中 bisect 出唯一一个); 而 `live/tests_cancel_ban_resilience.py:69` 自己就把这件事记为缺陷并为自己 scope 到临时目录(「测试不得有能力封禁」)。**lead 核实: 实盘树 `~/dl_quant_live/state/venue_ban.json` 现存**, mtime 09-13 11:58Z, 含 `testnet.binancefuture.com` / `"Too many requests"` / `until_epoch: null` / `observed_utc 2026-09-13T11:58:21Z` —— 时刻落在 09-13 落地时在**运行树**上跑的验收电池窗口内。**当前内容惰性**(fapi 条已过期; testnet 条无 deadline ⇒ `banned` 假; 读者取磁盘与内存 MAX 只会更保守), **文件不得删除**(08-27 那条是真实封禁证据) | **P1** | FX-EXEC |
| **BAT-01** | `tests_disposition_matrix` 在已提交 state 上**每棵树都 9 红**, 其绿依赖于「有人把实盘账本拷进来」⇒ 合并电池必须显式声明**哪些套件的绿依赖未入库的数据副本** | P2 | lead(合并电池) |
| **EXEC-RACE-01** | 研究仓是单 worktree ⇒ 三个工作者共享一个 git **索引**。FX-PROD 于 ~03:40:0xZ 暂存 17 份收据, FX-EXEC 于 03:40:51Z **无显式 pathspec** 执行 `git commit` 把它们扫进 `71c80e1d`, FX-PROD 自己的提交随后以 `no changes added to commit` rc 1 失败。**无丢失**(17/17 在索引中已验), 但提交链把 FXR-PROD-1 / PROD-28 / dry-run 的收据记在一条讲电池时间的提交下 —— **复审包正是按该链组装**。两侧各自留更正记录(FX-EXEC `f15e2466` / FX-PROD `7b8963a2`)。**不重写**(共享分支上 `71c80e1d` 已是祖先, reset 会改 SHA 并可能丢掉期间他人提交) | P2 | 双方(已记录) |

### 17.4 裁定
1. **§0.7 升级为硬规矩(全体)**: **`git commit -F - -- <显式路径>`, 无条件** —— 它完全绕过索引状态; `git add -- <path>` 只对 add 生效, `git commit` 无 pathspec 会提交整个索引。`git show --name-only` **读缺席**。
2. **电池窗口越界的迟到量按实测更正**: 「70 秒」是估计, 实测 **85 秒**(11,785 s 对限 11,700 s); §14.1 已就地更正。**此类数一律算出来, 不估。**
3. **`tests_proportional_response` B14 归 FX-W6C, 修的是断言不是行为**: 该格断言 `ev3_5e_state == 'BREAK'` 而实际路由是 LOCAL 且保护成立 ⇒ 它断言的是**状态标签**而非它要保护的性质。改为断言**路由与行为**, 原状态标签断言保留为**数据存在时才生效**的附加格(缺数据具名 SKIP, 不红)。必须在合并电池之前落地。**附带事实**: `run_acceptance.sh:28` 钉 `/usr/bin/python3`(3.9.6), 而裸 `python3` 是 3.14.4 —— 此前所有逐套件数字的可比性都取决于此, 进报告。
4. **EXE-04 停在核, 不进接线**(重申); 被撤回的区间传播法留在文件里标 UNSOUND 且不被任何做决定的东西调用 —— **否则测试只能查「与解集一致」, 查不了「不是那个被撤回的宽对象」**; 比**集合**不比计数(PREREG 自证: 正确合同与错误合同在单 BUY100 上都恰好接受 5,151 对)。
