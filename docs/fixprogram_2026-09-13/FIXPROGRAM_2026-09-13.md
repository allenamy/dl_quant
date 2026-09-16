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
  - **★ 更正 2026-09-16(FX-DATA 自查; 原字节保留)**: **HEAD 上是 54 个文件, 不是 33 也不是 21**。审计的 21 在**它自己的范围内是对的**(限定为 2026-09-09 当天或之后首次提交的文件, 逐文件复现得 21); **我此前记录的 33 是错的, 作废**。另: 全仓 `"CAL": "log"` 出现 988 次 · `"prod"` 12 次 · **`"simple"` 27 次分布在 14 个文件, 全部首次提交于 2026-09-04/05**, 且全在 `pod_port_2026-09-04/` · `review_caliber_wf/` · `second_instrument_rebuild_2026-09-05/pod_logs/` 内 —— 即那次以口径选择本身为对象的复审(E-0904-F)⇒「09-09 之后没有新增」成立。那些 09-04/05 的 `simple` 数字是否仍在当作当前结果流通, 是 **K4** 问题, 数据层不裁。
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
| **PROD-42**(原登记为 PROD-31, 与 AUDIT_PROD 撞号, 2026-09-16 改号; 原号标 SUPERSEDED-ID) | **08-29 20Z: 生产者根本没出 king 文件**(16:21Z 打印 `next 20:16:00Z in 14061s` 后无输出, 至 23:28:01Z 重启)。守护的守卫是 `[ -f "$TL" ]` ⇒ 循环体从不执行: **无页报、无日志行、`combo_live_last_anchor` 都不推进**; 执行器 N+24:00→N+29:00 轮询 21 次全 `{ok:false,"missing"}`, **整锚 HOLD、持仓冻结、`anchors_row: false`**。比 PROD-27 命名的「静默跳过」更严重。FX-W6C 在同一锚上独立测到同一事实(§5 洞的实例) | **P1** | FX-PROD |
| **PROD-43**(原登记为 PROD-32, 与 AUDIT_PROD 撞号, 2026-09-16 改号; 原号标 SUPERSEDED-ID) | **该守护的全部告警路径在生产中从未被执行过**: 125 锚 `combo_live.log` 0 条 PAGE / 0 条 `skip aux-not-settled` / 0 条 `COMBO_LIVE ABORT`; 唯一投递证明是 08-26 手工跑的 4 行, **第一行 `status: NOT_CONFIGURED`**。且 `_page` 把异常吞成 `PAGE_FAIL` 后 `_bail` 照退 3, 守护又因看见 `COMBO_LIVE ABORT` **故意不页报** ⇒ **bail + 通道坏 = 端到端静默**。告警通道正控已裁定为 PROD-27 修复的一部分 | **P1** | FX-PROD |
| **PROD-41**(原登记为 PROD-30, 与 AUDIT_PROD 撞号, 2026-09-16 改号; 原号标 SUPERSEDED-ID) | G1(守护跳过 `NOW-A>1355`)与 G2(`combo_stage` bail `A+1360`)**仍按已退役的 N+23:00 标定**; 执行器 08-27 05:2xZ 起读 **N+24:00**(`anchor_offset_min=24` / `poll_grace_min=5`, 重试到 N+29:00)⇒ **G1 比首读早 85 s 关门, G2 早 80 s** ⇒ 本可按时写出的 combo 形态被主动放弃、改交 king 形态 | P2(**书行为, 待用户裁定**) | lead → 用户 |
| **PROD-28-STALE** | AUDIT_PROD PROD-28(「运行中进程执行盘上代码/bundle/F10 模型」)是对 PID 10900 / 30944 / 30943 验的; **09-14 15:43:56Z 重启后三守护为 797/801/812, 15:45:14Z 起** ⇒ 该验证记录**已过期**, 复审包中引用它处一律标 STALE 直到重取 | P2 | FX-PROD(重取) |
| **OPS-04** | `ops/daily_summary.py` **既无 launchd 作业也不在 `docs/CRON_TEMPLATES_2026-09-04.md`** ⇒ 今天没有任何东西调度它 ⇒ LED-08 的每日漂移告警落地后也不会响(「已声明的盲区≠已关闭」同族; 一个没人调度的告警不是告警) | P1(投递) | lead(部署 runbook) |
| **PROD-44**(原登记为 PROD-33, 与 AUDIT_PROD 撞号, 2026-09-16 改号; 原号标 SUPERSEDED-ID) | `combo_live_status.json` 是**单槽可变文件**, 两条静默分支上都保留上一锚的 `{"ok": true}` ⇒ 读者不比对 `status["anchor"]` 就会读到上一次成功(与 P2 AMENDMENT 12 同一对象) | P2 | FX-PROD |
| **PROD-45**(原登记为 PROD-34, 与 AUDIT_PROD 撞号, 2026-09-16 改号; 原号标 SUPERSEDED-ID) | 排练模式用 `WS` 而非 `_outdir` 备份(`combo_stage.py` L340)⇒ **写进实盘状态树**; 08-26 00Z 因此有 king 备份却无 combo 运行 ⇒「有备份 ⇒ 跑过 combo」的朴素判据误计(装置污染被测对象同族) | P2 | FX-PROD |
| **DATA-COR-1** | 交接 §4.5 与 FX_DATA/STATE_PAUSE 写「run 1 在 writer 处失败」**不准确**: traceback 是**重载回环**被拒 —— `Artifact.load` 比 spec sha `['99ae35e01ec3dd`(shape-(1,) 数组的打印)与模块的 `99ae35e01ec3dd06`; 根因同(`np.ascontiguousarray` 提升 0-d 标量), 但抓住它的是**工件自身的守卫**, 这才是收据里该留的部分 | 记录 | FX-DATA(已自报) |

### 13.2 裁定
1. **PROD-27 严重度按「因 × 果」两维**: `late_producer` ⇒ HIGH; `late_daemon_start` ⇒ 默认 INFO/计数, 但同锚出现 (i) 执行器无可用外部书(HOLD / `ok:false` / 无 LIVE phase_A 行) 或 (ii) 连续 ≥2 锚落静默分支 ⇒ 升 HIGH; **PROD-31(无文件)不进该分裂, 一律 HIGH**。三者都必须具名 + 计数 + 进逐锚记录。

> ⚠ **更正 KB-72 · P2 · AUD-KB K4 2026-09-16**(原句字节保留, 不改写): 本条裁定里的 **PROD-31 应为 PROD-42** —— 「无文件」项已按 §17.5 由 PROD-31 改号为 **PROD-42**(原号标 SUPERSEDED-ID), 而 `AUDIT_PROD`(ee2a8c4d)的 PROD-31 是「`fea171/f10_live_s42.pt` 是八月模型」, 与本裁定无关。实施 PROD-27 严重度分裂者按 **PROD-42(无文件)不进该分裂, 一律 HIGH** 读。§17.5 的改号只改了 §13.1/§14.2 的登记表与 `STATE.md`, 本条是残留引用。

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
| **PROD-47**(原登记为 PROD-36b, 与 AUDIT_PROD 撞号, 2026-09-16 改号; 原号标 SUPERSEDED-ID) | **08-29 20Z 无文件 ⇒ 无 `state_H_f10_1788033600.npz` ⇒ 08-30 00Z 唯一一次 `h_source: king_fallback`, `self_parity_maxdw` 6.58e-3 vs 其余锚 ~2.3–3.2e-10(差七个数量级), 且 `h_source` 上无任何页报**; 同锚 combo 又静默跳过 ⇒ 该链状态只由侧车写成。**两个静默缺陷是同一次事故的两截** | **P1** | FX-PROD(并进 PROD-27) |
| **PROD-46**(原登记为 PROD-35, 与 AUDIT_PROD 撞号, 2026-09-16 改号; 原号标 SUPERSEDED-ID) | 侧车的 `LAST` 是内存 shell 变量(`sidecar_daemon.sh` L4)⇒ 重启后按 `ls -t | head -1` 重处理**过去的锚**并在数小时后覆写其链状态。四次实例: 08-24 08Z(+2.84h)· 08-29 16Z(+7.50h)· 08-30 04Z(+1.09h)· 09-14 12Z(+3.79h); 其中 **08-30 04Z → 08-30 08Z 与 09-14 12Z → 09-14 16Z 两次确实把事后重写的状态喂给了随后的实盘锚**。四次都未拉入锚后市场数据(0.8–2.4 s, 无 171 管线重建, 复用各自锚的 `mini/cache.npz`), **但该否定是有条件的**(缓存检查只按锚) | P2 | FX-PROD(排 PROD-27 之后) |
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
| **TRN-30**(原登记为 TRN-28, 与 AUDIT_TRAIN 撞号, 2026-09-16 改号; 原号标 SUPERSEDED-ID) | `pod_f10_np_export.py` 在**自己的 V1 门判词之前**就写出可部署 npz(`np.savez` L56, `sys.exit(0 if ok else 3)` 在其后), 且默认 `F10_OUT` **就是在役工件路径** ⇒ **失败的门仍在实盘路径留下完整可加载模型并覆盖原件**。比审计的「产生在所有门之外」更锋利: **门存在, 只是判词不控制写入**。与 FXR-PROD-1(修正态先于控制落盘)同族 | **P1** | FX-TRAIN(并进 TRN-03) |
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


### 17.5 ★ 编号冲突更正(AUD-KB 发现, lead 自身错误; 2026-09-16 05:0xZ)
**事实**: §13.1 与 §14.2 开出的 **PROD-30/31/32/33/34/35** 以及 **PROD-36b** 所用的号, **AUDIT_PROD(ee2a8c4d)已经占用且指的是别的发现**。两个登记**证明是同一个命名空间** —— §13.1 自己那张表就用号码交叉引用了「AUDIT_PROD PROD-28」。
**为何是 P1 而不是记账**: `STATE.md:144`(唯一现状源)当时写着「登记为 PROD-30, 待用户裁定, 属书行为」, 而该号在同一个包交给复审的登记里解析为 **exec_n6 沙箱生产者**; 谁打开 PROD-30 去裁定, 读到的是**错的证据**。

| 号 | AUDIT_PROD ee2a8c4d 的原主 | 我方 §13/§14 的新项 | 改为 |
|---|---|---|---|
| PROD-30 | exec_n6 沙箱生产者自 09-06 起在 N+1 对着实盘 bundle 运行 | G1/G2 仍按已退役的 N+23 标定 | **PROD-41** |
| PROD-31 | `fea171/f10_live_s42.pt` 是八月模型, 不是 351ae26b 背后的 checkpoint | 08-29 20Z 生产者根本没写 king 文件 | **PROD-42** |
| PROD-32 | `stop_overlay.py` 是 king 形态权重上的报告影子 | 守护的告警路径在生产中从未执行(125 锚 0 页报) | **PROD-43** |
| PROD-33 | CLAUDE.md 写 N+23 而执行器读 N+24 | `combo_live_status.json` 是单槽可变文件 | **PROD-44** |
| PROD-34 | 在役 booster 8d79186b 训练在未 clamp 的构建器上(E-0909-A) | 排练模式用 `WS` 备份 ⇒ 写进实盘状态树 | **PROD-45** |
| PROD-35 | 在役 V2MAIN 训练时 fund 列对非 live450 名置 0, 且在 pre-holefix 缓存上 | 侧车 `LAST` 是内存变量 ⇒ 重启后重处理过去的锚 | **PROD-46** |
| PROD-36(b) | 回放缓存短于约 37 天把 btcv 回填放进 180 锚 z 窗 | 08-29 20Z 无文件 ⇒ 08-30 00Z 唯一一次 `h_source: king_fallback` | **PROD-47** |
**处置**: AUDIT_PROD 的最高号是 **PROD-40**, 故 **PROD-41 起为空号**。上表七项已在 §13.1 / §14.2 就地改号并注明「原登记为 PROD-3x, 与 AUDIT_PROD 撞号, 原号标 SUPERSEDED-ID」; `STATE.md` 的引用同步改为 PROD-41 并在括号里保留原号。**原字节保留, 以本节为准。**
**规矩(新)**: 本纲领新开的登记号**必须先对四份审计登记(AUDIT_EXEC 842bbffa / AUDIT_TRAIN 7e1ecf9a / AUDIT_DATA bb8a2806 / AUDIT_PROD ee2a8c4d)查重**再使用; 四份审计与本纲领**共用一个命名空间**。AUD-KB 已把本条登记为 **KB-69 / KB-70**, 并新增 **KB-71** 记录 KB-03 / KB-11(N+23→N+24)已由 lead 于 09-16 应用。

## §18 第六轮交付与裁定(2026-09-16 05:0xZ, lead)

### 18.1 ★ PROD-41 的反事实 = 零 —— lead 先前的推断被实测推翻
我在 §13.1 登记 PROD-41(原 PROD-30)时写的后果是「**本可以按时写出的 combo 形态被主动放弃、改交易 king 形态**」。FX-PROD 按裁定做了**只计数、不改码不改配置**的反事实:

| G1 移到 | 生产者落地 ∈ (1355, G] 的锚数 | 其中 combo 仍能在 N+24:00 前落地 |
|---|---:|---:|
| N+23:00(1380 s) | 0 | 0 |
| N+23:35(1415 s) | 0 | 0 |
| N+24:00(1440 s) | 0 | 0 |
| N+24:30(1470 s) | 1 | **0** |
| N+25:00(1500 s) | 1 | **0** |

**combo 时代唯一一个生产者落地越过门的锚是 2026-08-30 00Z, 1467.8 s —— 它本身已经比执行器首读晚 27.8 s**; combo 还需要再约 52 s(settle + stage 运行的 p90), 所以**无论门放在哪里都来不及**。而**处在当前门之内的最高落地是 1305.9 s** ⇒ **该门从未截断过一次本可以完成的运行**。
⇒ **裁定**: 我原先那句后果陈述**作废**。85 s 的空余是真的, 但**在已观察历史上没有代价**。PROD-41 上交用户时**只能立论于未来余量, 不得说成「我们在丢掉 combo 锚」** —— 后者不成立。(FX-PROD 主动指出这一点并说「我会照直说」, 记为正例。)

### 18.2 PROD-27 修复交付(克隆 7c4e79f; 研究仓 327c0c26; 未部署)
- **红**(对**实盘**守护 sha `72f78d1e`): 15 格, **9 失败**(RED 4 / NEW 5), **KEEP 0 失败, CRASH 0** ⇒ 红是机制缺席而非夹具坏。**绿**(修复后守护 `2d57cc21`): 15 格 0 失败。`combo_live_daemon.sh` 的 diff **0 删除行** —— 两处既有页报文案与整个原控制流逐字保留, 记录在旁新增, 并补上那条**从未存在过的分支**(`[ -f "$TL" ]` 为假)。
- 裁定项全部落地: 严重度**因 × 果**(`no_producer_file` 恒 HIGH; `late_producer` HIGH; `late_daemon_start` INFO/计数, 在「执行器无可用书」或「连续 ≥2 个静默锚」时升 HIGH), 且 `late_daemon_start` 由守护**自己的启动时刻经 `ps` 读出**, 是事实不是猜测。**后果 (i) 在守护动作时不可观测** ⇒ 每条记录在下一锚由**幂等的复访**重新评定, 该复访同时记录「被宣告缺席之后才落地的生产者文件」= 08-30 00Z 那种 N+24:27.8 的形状。
- **`form_written`, 永不 `form_traded`**, 带 join key(anchor, `json_sha256`, `written_utc`); 格 P27-N1 断言字符串 `form_traded` 在记录里**不出现**。**P12 已并入记录**: `h_source` · `self_parity_maxdw` · **上一锚的 `state_H_f10` 是否存在** · `target_blend` 与 `state_H_f10` **两者的写者身份**(各自从候选者自己的守护日志归因)。**`h_source != "own"` 是它自己的具名计数 HIGH 事件** ⇒ 08-30 00Z 那种形状不再是哑的。
- **告警通道正控通过(3 项 0 失败)**, 且测的正是裁定要求的两件: **一次投递** + **一次被具名(而非被吞)的失败**并带原因。不发真页报(沙箱 sink + 故意坏掉的 notifier)。`page()` 现在返回发生了什么, 记录保留 `page_delivery_unverified`; **真通道自检归 lead**。
- **工作者自报两个自身仪器缺陷**(均属我们反复撞的族, 已修而非绕过): ① 沙箱把文件 mtime 留在真实挂钟时刻 ⇒ 每个余量都是夹具噪声, 水平规则响在假象上; ② `h_source_of()` 在 `target_blend` 缺席时返回**短字典** ⇒ 读者的 `if "state_H_f10_writer" in chain` 会静默跳过 —— **与一小时前 PROD-28 装置里 `MANIFEST` vs `MANIFEST.json` 是同一个「缺键即跳过」族**。现在所有键恒存在, 源缺席时为 `None`。(事实 27.25 / F28.4)
- 叠加: `docs/receipts/fx_prod_stack.diff` = `b891748..7c4e79f`, **0 删除行**, sha `4bc25f8b`。

### 18.3 ALM-06 (ii) 交付(guard_twin 包 0f59252b; 未部署; `~/guard_twin/guard_twin.py` 仍 sha 0b299781 且从未被触碰)
- **两条告警并存**: (i) 算术孪生 vs 看门狗(`TOL["cum_pct"]` 0.50 不变)抓代码缺陷; (ii) **独立的收入账本 TWR** vs 看门狗链, 判在**减去已测口径成因之后的残差**上 —— **只有它能看见输入偏差**。
- **成因是算出来的不是假定的**(装置 `alm06_cum_decomposition.py`): 只有孪生**段**可能不同(孪生首快照之前的日子两条链都按 daily_nav 定价)。同一批日上跑四条链 —— T(孪生收盘 + 自己的收入划转)· C1(收盘取自 daily_nav)· C2a(划转日按看门狗公式, realised 取自孪生**自己的收入**)· C2b(同上但 realised 取 daily_nav 记录值)⇒ **T−C1 = 日收盘时点 · C1−C2a = 划转日公式 · C2a−C2b = 输入偏差**。**C2b 必须复现 `wd_chain_arith_pct`; 做不到时 (ii) 拒绝判决而不是照判。**
- **保真先于结论**: T 在 **1,655/1,655** 行上精确复现记录的 `cum_pct_twin`(最大差 0.0), C2b 复现 `wd_chain_arith_pct` 到 **4.95e-05 pp**。**记录在案的八条 CUM 线全部由「日收盘时点」单独解释**(孪生收盘 = 它自己当日最后快照; 看门狗收盘 = daily_nav 当日最后一行 ~20:45Z), 残差 ≤ **0.017 pp** —— **是被解释, 不是被消音**。
- **LED-04 允许量冻结且只覆盖孪生段**: 冻结是因为「每次运行都从收入重算」会吸收**任何**输入偏差(换个马甲的同一种盲); 只覆盖孪生段是因为四个大的修前划转日(08-02 / 08-05 / 08-10 / 08-18, 几乎是全部 0.2613 pp)在两条链上**定价相同因而从差里抵消**, 段内只有 08-27 / 09-03 / 09-08 且都是第四位小数。**把整张 7 天表都套上会让残差停在中位 0.246 pp —— 几乎正好是那个根本不可能出现在差里的前缀效应, 作者就是这样抓到自己的错的。**
- **修订状态取自看门狗的声明而非猜测**: cond4 声明 `realised_source: "amendment_records"` ⇒ 允许量 0; 声明 `recorded_rows` ⇒ 冻结值; **字段缺席 ⇒ 冻结值并标 `inferred_recorded`**。从「盘上有没有记录文件」去推断是错的 —— 文件可能先于 fx-w6c 的代码落地。
- **阈值 `RESIDUAL_TOL` = 0.25 pp = 已部署常数 `TOL["cum_pct"]` 的一半**(是对既有常数的折半, 不是对着记录行挑的数); 比实测噪声底(181 个可判行上最大残差 **0.017307 pp**)高 **14×**, 比要抓的 0.5 pp 偏差低 **2×**。
- **两道属于机制而非调参的门**: **未收盘的划转日不可判并说明理由**(当日未收盘时孪生的收入账本按构造只持有一部分 ⇒ 09-03T20:36Z 入金日 +0.3232 pp, 收盘后回到第四位小数); **(i) 那条腿不记在 (ii) 头上**((i) 按自己的容差报; 最差可判裸残差 09-13 12:46Z −0.1858 中 −0.1696 是该腿, 其余只有 −0.0162)。**注入的偏差藏不进这个减法** —— 它同时移动记录值与算术孪生 ⇒ (i) 腿保持 ~0 而偏差落在输入腿; **I3 格是证明而不是断言**。
- **测试** `tests_guard_twin_alignment.py`(离线, 从不调 `main()`; 92.5 s, rc 0, **20/20**): 六个原有格不变且仍过; I1 复现自身输入(8/8 与 8/8); I2 **1,655 行漂移 0**(ok 1,507 / 不可判 148, 每个不可判都点名理由); **I3 在一个划转日(09-08 realised_pnl)注入 0.5 pp 偏差 ⇒ (ii) 触发(残差 −0.5132)而 (i) 不触发(其腿恰为 0.0)**, 且孪生自身数字前后逐位相同 —— **这就是独立性的含义**; I4/I5/I6 允许量随声明状态走、前缀日贡献为零、在最后一个划转日上评估为不可判并具名。
- **两个顺带的真实修复**: `day_of` 按 UTC 日索引记忆化(原先每次查找对每条收入行调一次 `strftime`, 仅旧链每次运行约 **4.8M 次**), 键的精确性逐日核过 2026-07-01..10-01; `twin_cum_chains` 对收入账本**只过一遍**而不是每天过一遍 ⇒ 多加两条链不会让每次运行的成本变三倍。
- **工作者自报的错误**: 装置最初在 **0/1,654** 行上复现孪生 —— 两个都是自己的缺陷(用 `time.mktime(strptime(...)) − time.timezone` 解析 UTC, 只在 `tm_isdst == 0` 且 `strptime` 不设它时才对; 修好后仍**落后一个快照**, 因为比较行上唯一的时间戳被按秒取整, 而它所依据的快照带毫秒且孪生在计算前先追加它)。**前四次运行的任何数字都未被使用。** 另: 修正后的测试第一次跑返回 rc 0 而汇总与 `sys.exit` 还停在文件中部 ⇒ **退出码尚未绑定新格**; 把它们移到末尾后重跑, 而不是留着那份收据。
- **未证明**: 新文件从未在 launchd 下运行过; 重建锚上的 LEV 行未动; 在 daily_nav 参照 ±900 s 内的移动落在快照时点容差内; **一条潜伏项**: 孪生前缀只读当日**最后一行**的 `external_flow_usdt` 而 `wd_chain_arith_pct` 读当日**任意行** —— 1,655 次评估上分歧 0 天, 故**潜伏而非现存**。
- **部署(lead)**: ① 备份 `~/guard_twin/guard_twin.py` 并确认 0b299781…; ② 拷入 `guard_twin_ALM06/guard_twin.py`, sha256 `526bf1d2…`; ③ 下一次 launchd 运行(每 1,200 s 全新进程)即加载。包 diff sha256 `31c96572…`; 测试 sha256 `7e09a6a2…`。

### 18.4 TIM-01 事实表(FX-MODEL, 提交 fc262f79)
- **时钟按前缀和语义读出**(`cs_pair` 带前导零行 ⇒ `CS[b]−CS[a]` = 行 **[a, b−1]**): 训练特征 [E−w, **E−1**] / 服务 [E−w+1, **E**]; 成员统计 [E−2016, E−1] / [E−2015, E]; 标签**训练 [E, E+47]** / 记账 [E+1, E+48]。**bar E 恰在锚收盘**(生产者 `endTime = anchor*1000 − 1` 且拒绝 `close_s > anchor`)⇒ 含它是因果的。
- **必须照此措辞**: 训练拟合的是 *(数据 ≤ E−1) → (自 E 起的收益)*, 生产施加的是 *(数据 ≤ E) → (自 E+1 起的收益)*; **每一半各自连续且因果, 两者相差一根 bar**。脉冲测试的结果之所以成立, 是因为 **行 E 是标签的第一个加数**。分数会动是因为这是**两个不同的条件关系**(只要 5 分钟收益有任何短程自相关), **不是因为泄漏** —— 禁用措辞已在文档中显式标出。
- **标签成熟与 embargo**(原先薄的那一行): king 标签 [E, E+47] 在 **A+3h55m** 完成; 对齐构建器与 DL 的 [E+1, E+48] 在 A+4h 完成。**king 折是年度且 embargo 为零**(`tr_ = YRA < YV; te_ = YRA == YV`): 最后一个训练锚的标签止于 12-31 23:55Z, 第一个测试锚是 01-01 00:00Z —— **无重叠, 也无 embargo**(今天 5 分钟间隔, 对齐后 0 分钟)。DL 侧不同: 月度训练器带 `EMBARGO ∈ {60,1}` 与打印出来的因果断言 `max_label_end = E_ts + 48*300` = A+4h(**对 DL 精确, 对 king 保守**)。
- **导出器的 provenance 把 king 标签末端写错 5 分钟**: 记 `king_train_last_label_end_utc = _king_train_end + 4*3600` = A+4h, 而 clamp 构建器的标签实际止于 A+3h55m ⇒ **把 DL 的时钟写进了 king 的字段**, 与缺陷本身是同一个「登记携带错误时钟」的形态。king 的梯度止于 label-year < 2026。
- **★ king 的 arm B 与 DL 的 arm B 是不同的问题**: **king 根本没有特征归一化**(LightGBM 直接拟合原始特征)⇒ 复审「冻结训练时 mu/sd」这条约束**对 king 是空的**; 要冻结的是**特征顺序与支持**, 而且已有一条现成断言可钉: 导出断言 `[names[k] for k in keep] == PINS["keep_names"]`。**只有出厂的那个 booster 被保存过** —— `slow2026.txt`(label-year < 2026)在, 而 **2024 与 2025 的折 booster 是局部变量 `g2`, 从未写盘** ⇒ king 的历史 OOF 与 DL 月折有同一个缺陷: **产出它的 checkpoint 不存在**。LightGBM 在同数据同参数下确定 ⇒ 同样走「重建 + 用复现存储 `PRED` 的正控认证 + 失败即如实报告, 不替换」。**king 的 OOF 只在前向标签有限处存在**(训练行那一行与预测写入那一行各门一次)= AUDIT_DATA D3 与 TRN-06 轴, 现已钉到精确行号。
- **同族站点以测量关闭: 恰好 30 个锚**。`n7/qvm/m7/v7` 索引**未 clamp** 的 `E − 2016` 而 `covr` 已 clamp; 网格过滤为 `E ≥ 576` ⇒ `E < 2016` 的锚索引为负并绕到缓存尾部。pod2 只读(只取 `ts` 成员, 先查 cgroup 40.9/56.8 GB): 轴 2022-01-01 00Z..2026-09-01 00Z, 490,753 根 bar, 网格间距一致为 48 **无缺口**, `E ≥ 576` 的锚 10,213 个, 其中 **`E < 2016` 恰好 30 个 = 2022-01-03 00Z..2022-01-07 20Z**。**用自己已有的收据交叉佐证而不是新跑**: T1 记录对齐(会 clamp 的)构建器**恰好多出两个锚 2022-01-07 16Z 与 20Z**(E = 1920, 1968), 且一个都不少 —— 正是「clamp 修好统计量后, 又有两个早期锚通过筛」应有的签名。影响半径 **0.29%**, 全在轴的第一周。
  - **★ 更正 2026-09-16(FX-MODEL 自更正, 原文保留并标 SUPERSEDED)**: ① **绑定的门不是 `len(m) ≥ 50`, 是 `covr`** —— 在只有 `E+1` 行的 clamp 窗上, `covr` 仍按**常数 2016** 相除, 故 `covr ≥ 0.95` 要求 `E ≥ 1915.2`, 而 [1915, 2016) 内的网格值只有 **1920 与 1968** —— 算术上恰是 T1 观察到的那两个锚; D 保住全部 30 个是因为它按**真实窗长**相除。**三个构建器的行为由同一个除数完全解释。** ② **更重要: 绕回并没有污染那 30 个锚, 而是把它们从 king 训练轴上整个移除了** —— king meta 10,182 个锚, **首锚 2022-01-08 00:00Z = E 2016 恰好**, `E < 2016` 的锚 **0 个**; DL targets 10,212 个锚, 首锚 2022-01-03 00:00Z = E 576, `E < 2016` 的 **30 个**。在 DL 而不在 king 的恰好是这 **30** 个(E = 576…1968), 在 king 而不在 DL 的 **0** 个 ⇒ **king 缺了它的头五天, 且 king 与 DL 的训练轴在那里按构造就不一致**。这正是 AUDIT_DATA TRD-05 记的 `anchors_off_king_axis: 30`, 现在有了机制。
- **两件让队列第 3 项更便宜的事**: `pod_fea_ext_e.py` 是 `pod_fea_ext_clamp.py` **逐行相同、只改了时钟**(`HI = E+1`, `LO7 = max(HI−2016, 0)`, 标签 [E+1, E+48], `grid + 49 <= TT`)⇒ 已经是第 3 项要的「单旋钮」形状, 只需把它变成带 legacy 设置的旋钮, 不必从头写。**它旧的判决不是对时钟的判决**: 它过了平价门, 却按规则**栽在导出守卫上, Sharpe 2.260 对 2.27** —— 而**该守卫的抽样误差约 ±0.6**; **±0.6 噪声的守卫分辨不了 0.01 的差**。预注册改用冻结 δ 下基于 CI 的书层判官, 不用那个守卫。
- **对比纪律**: 47/47 逐位 · 总体 0.9353434309(最小 0.7601561963)· 仅时钟 0.98434 · 仅排名宇宙 0.94700 是**不同的对比**, 不可相加也不可分解为逐因 alpha 损失, **没有一个是收益 IC**。工作者自己的仅时钟 T1: 5,844 个锚上中位 0.9865(v4)/ 0.9866(在役), 逐年 0.9905 / 0.9856 / 0.9827 —— **偏斜在近年更大**, 因为成员更多。

### 18.5 EXE-04 在**真实** `reconcile()` 上的红(FX-EXEC)
窗 1 报残差 **30**; 窗 2 报 `expected_qty = 80.0` —— **上一次的观察值** —— 于是残差 0、零异常。**那个 30 既没有被解释也没有被结清, 只是被吸收了。** 收据 `EXE04_red_on_live_reconcile.log`, 钉 `reconcile.py` 的 sha。具名余项 R1–R12 已写(接线 / 41 天回放 / §3.6 逐条重新论证 / 核自身的限制, **含一条工作者主动上记录的**: 证据下界 `C_i(t)` 在合同允许其单调上升处被简化为常数)。网格出处按裁定钉住: 源路径 · 分支 `agent/codex/QNT-2026-0907/onboarding-audit` · worktree 头 `d0d82862` · 文件自身提交 `82cbe018` · sha `8a2b7c9b…`, 只读拷入; **未 fetch / checkout / merge, 也未进入那棵 worktree 工作**。

## §19 第七轮裁定(2026-09-16 05:2xZ, lead)

### 19.1 PROD-46(原 PROD-35)· `>=` 留作具名潜伏 + 守卫在前
**FX-PROD 的实测**: 三个被重跑的锚**重跑输出与首跑完全一致**(08-29 16Z / 08-30 04Z / 09-14 12Z; n·gross·net·ρ·self-parity·成员数 400·锚标签全同)⇒ **该机制从未改变过一个数字** —— 这比原先「没有锚后数据进入」的论证强, 因为它是**直接的输出比对**而非关于输入的论证。
**它自己保留的界**: 只在**日志精度**上一致(gross 4 位有效数字 / net 5 位小数 / ρ 3 位小数 / self-parity 3 位有效数字), **不是逐位**; 而逐位核**已不再可得**, 因为重跑正是原地覆写了 `state_H_f10_<A>.npz` 与 `target_blend/<A>.json` —— **即被检查的那个行为本身销毁了检查它的证据**。
**它对自己 P12 措辞的更正(我已同步到纲领与记忆)**: 原写「重处理**过去的**锚」过头了。`sidecar_blend.py` L13 取 `A = aux["prev_rec"]["anchor_ts"]` = 生产者**最后完成的锚**, 与 `combo_stage.py` L16 相同; 守护里的 `ls -t | head -1` **只是触发器, 不是锚的来源** ⇒ 侧车**不可能在存在更新锚时挑一个陈旧的**。四次都是「该锚仍是生产者当前锚, 而生产者此后没再跑过」。
**裁定 (a)**: 缓存复用判据 `if int(T9["E_ts"][-1]) >= A: need = False` 的 **`>=` 保持不动, 登记为具名潜伏 PROD-48**, 理由: ① 该行与 `combo_stage.py` L119 **逐字节相同**, 即**实盘 combo 书自己的路径**, 改它会在「当前就是错的那种情形」上改变书产出的数字 ⇒ **书行为**; ② 无任何观察到的实例, 到达它需要生产者在侧车读 `aux.json` 与查缓存之间完成一个锚(亚秒), 而该进程此时距下一锚尚有数小时; ③ **35.7 的守卫把它从静默变成响亮**, 覆盖其大部分风险。`>=` → `==` 作为**独立的配对回放项**随换装计划上交用户, 不在本轮实施。
**裁定 (b)**: **35.7 就是 PROD-46 的全部范围** —— 覆写前先比对: 相同 ⇒ 计数事件 `rerun_noop`; **不同 ⇒ 拒绝覆写并页报 HIGH**。它**恰好断言 35.2 测到的那条不变量**, 不变量成立时什么都不改, 并把一次未被观察的原地重写变成一次被检查的重写。**侧车的写入行为(谁赢)仍是保留给用户的那件事, 不得触碰。**

### 19.2 EVL-01 · 裁定 (a)+(c), 不走 (b)
**FX-DATA 量出了后果**(此前无人写下来): 把权重固定在 CAL=log 臂, 一次被遗忘的 `CAL` 使价格通道平移 **+0.327 bps/锚/单位 gross(种子 42)与 +0.359(种子 2027)**, 覆盖 W_ALPHA ⇒ **是 D1 δ(0.05)的 6.5–7.2 倍**, 且 **91.2% 的单锚超过 δ**。**不是均匀偏置**: 逐年均值 −1.13 / +0.02 / −0.32 / −0.02 / **+2.66**(2022–26), 除 2026 外逐年中位为负, 因为 `expm1(y)−y ≈ y²/2` 恒正 ⇒ 书的符号取决于**最大 |y| 上的权重符号**, 通常是空头侧; 最差锚 **−1778 bps**(2022-06-07 20Z)与 **+760**(2026-07-01 16Z)。**这只是记账通道且是下界**: `CAL` 还进 `legs()` 并因此决定席位权重, 真正的 CAL=simple 运行会连 `W` 都不同。
**冲突**: 「把 CAL 设为必填或缺省 log」与两件冻结物相撞 —— **SPEC §7 把 `w10_sleeve.py` 钉在 sha `b88e35a4` 且要求不得修改**(A0 参照臂), 且 **54 个已提交装置把 self-sha 写在收据里** ⇒ 改缺省会破坏一份冻结规范, 并使这 54 个的「按路径复现」全部失效。
**裁定**: 走 **(a) + (c)**, **不走 (b)**。
- **(a)** 存档**逐字节不动** —— 复现-按-路径必须继续可用, SPEC §7 的钉是承重的。
- **(c)** **发射侧守卫**: 任何运行这 54 个装置之一的入口, 必须在**枚举 env 白名单**里显式带 `CAL`, 否则**拒绝启动**(这正是 E-0826-D「复跑漏 env」的正面形式)。守卫在装置**之外**, 不改装置一个字节, 因此不动任何 sha。
- **新装置**一律把 `CAL` 设为必填、无缺省。
- **不走 (b)** 的理由: 把一份冻结规范重新钉到一个被编辑过的装置上, 是为一个守卫已能覆盖的危险而破坏「先于数字冻结」的纪律。
**同时接受 FX-DATA 的自我披露**: 正控第 9 次假设 `pnl_ex = Σ_j W[k,j]·y4[i,j]` 被以相对误差 **3.17** 拒绝(存储的 `W` 是**重整前**的 `sm`, 两个通道都已是 bps, 且都只在**成员集**上求和); 第 10 次用的相对判据在记录 pnl 接近零处爆炸; 最终判据是**推导出来的** float32 存储界(`8·eps32·Σ|w[m]·yv|·1e4`)而非调出来的, 实跑落在其 **0.018**。**「看到残差之后改了通过判据」已被主动声明**, 且理由是机械事实(W 以 float32 存储), 而第 9 次的误读比被放宽后的界还高 **7 个数量级**, 仍会被拒 ⇒ **接受**。

### 19.3 PROD-11 · 不得把训练对齐到 live 450
**FX-MODEL 指出的陷阱**: PROD-11 读起来像「差别全在宇宙: 训练取 829 的 top 400, 生产取 live 450 的 top 400」, 于是自然推论是「把训练对齐到生产」。**该推论是错的** —— `live_pins.json` 是一个 **2026-08 的对象**; 把 2022–2025 的训练行限制到那 450 个名, 会使**成员资格成为一份更晚名单的函数**, 那**正是 FEA-01, 只是从资金费列搬到了成员筛**。
| 选项 | 是否前视 |
|---|---|
| (a) 保持 829 的 top 400 | 否, 但带着死合约(TRD-02/05)与非 crypto(UNI-01) |
| (b) `U-PIT ∧ CRYPTO` 的 top 400 | 否 —— 回放与判官已经在用的掩码 |
| (c) (b) 再用钉住的 `tradability_v1.npz` 门一次 | 否 —— 但 FXR-DATA-1 适用: 过去活跃度代理是**可接受的具名筛**, 不是结算真值 |
| (d) live 450 的 top 400 | **是 —— 不要做** |
**裁定**: **(b) 为预注册的默认候选, (c) 作具名敏感性臂**(其标签必须写明它是活跃度代理而非结算真值); **(d) 明令禁止**; (a) 保留为旧基线臂。**这是一项与资金费重建分开的干预**, 不得捆在一起报效果。
**另记**: 三条成员规则的差异在**七个轴**上(窗口 · clamp · `covr` 除数(P 与 K 用常数 2016, D 用真实窗长) · `qvm` 除数 · `v7` 除数 · 前向标签项 · 宇宙 · dtype), 其中六个在 aud-prod 的窗上量得 0 —— **那是实质性结果, 不是「规则一致」的陈述**; 而那些「0」里的一个, 正是移除 king 头五天的那个。**aud-prod 的数字可用, 其范围不可搬运**(「在 2026-08-17..09-10 的 147 个锚上、无下架」)。

### 19.4 引用必须钉提交 blob, 不是可变工作树(新规矩)
FX-MODEL 在重审自己引用的每个 sha 时抓到**两个被引文件在它写作期间被 FX-TRAIN 改动**: `chain_v4_monthly.sh` `c80303b5…` → `b1dcf771…`(+4 −1, 所引 L139/L148 逐字重读后仍成立)· `pod_legs_v4b.py` `8c33a230…` → `ff6dccad…`(+36 −2, **L22 已经移位**, 现读 `if MAX_NO_PANEL < 0:`)⇒ 其 §1.4(c) 的 `pod_legs_v4b.py:22` **只对它所引的那个 blob 有效**, 用作输入前必须重新定位。
**裁定(全体)**: 研究仓内的事实表/报告**一律引用提交 blob**(`git show <commit>:<path>`), **不引可变工作树**; 多人同时在同一个 checkout 上工作时, 行号只在 blob 上有意义。FX-MODEL 已按此重审全部 21 个被引文件, 0 不符、无驱逐桩。
**调度**: FX-MODEL 的事实表与 FX-TRAIN 的十月链正在动同一批文件。**裁定**: FX-MODEL 的新构建器**以 FX-TRAIN 的 TRN-17 版本为继承对象**(TRN-17 把那条只打印的条件变成了**在 `np.savez` 之前拒绝**的声明界, 并单独拒绝面板内部空洞, 恰好关掉 FX-MODEL §1.5 的顾虑); FX-TRAIN 在动这批文件前先知会 FX-MODEL。**TRN-17 的机制同时佐证 FX-MODEL §1.4(b) 的分解**: 面板按构造比 king/DL 轴短五个锚(面板要 `E+288 <= TT`, 轴只要 `E+48`; 240 行 = 20 h = 5 个四小时锚)⇒ **5 × 400 = 2,000**, 恰是它从收据计数里分解出来的那一项。

### 19.5 LIN-01 / RET-02 交付确认
- **LIN-01 关闭**: 全部 **20** 个 r6 x0910 构建器与链脚本入库 `multi_asset/exports/research/uplift_2026-09-11/r6_devices/`, 逐字节自 pod2 拷贝, **20/20 sha256 与 `AD_A_inventory.json` 相符**; 清单 `MANIFEST_r6_devices.json` 逐文件带 sha / 字节数 / 审计值并列, 并**单独列出(为空)审计从未盘点过的文件**。**FX-TRAIN 的 TRN-01 可以指向该提交**。
  - **输出路径行为分三类**(TRN-01 与 HOL-01 都要): env 可覆盖且带 r6 缺省(`r6_merge_cache` / `r6_raw_patch_ext` / `r6_king_pred`)· **env 必填, 裸跑不了**(`r6_panel_splice` / `r6_legs_x0910`)· 真正硬编码(`r6_dev_tree` OUT6 与其收据 · `r6_xking` OUT · `r6_fetch_funding` OUT; `r6_raw_patch_ext` 只硬编码它的**收据**)。**这更正了 FX-DATA 自己的 STATE_PAUSE**(原说 raw_patch 与 dev_tree「硬编码输出与收据路径」—— raw_patch 的输出可覆盖, 而 `r6_panel_splice` 根本没有硬编码路径)。
  - **FND-01 的站点现在可对着已提交文件引用**: `r6_panel_splice.py` L59 用**每个符号一个间隔**构建 `SEP_IV`, L82 把它施加到该符号**九月每一条 API 结算行**。该文件自己的头注写明这段是「自 `pod_panel_splice.py` L83-L102 **逐字复制**」⇒ 同样的缺陷在那里**是预期的, 但必须被检查而不是被推断** —— 已具名标记而未计入。
- **RET-02**: 裁剪 bar 索引入库 `common/data/bound_bars_ret5_x0910.npz`(sha `94e8e8c1…`, 即已提交 `r6_RECEIPT_raw_patch.json` 里的 `out_sha256`)+ `common/bound_bars.py` + 测试。**955 个被裁格, 440 个符号**, 2022-05-11..2026-09-06; 逐年 **33 / 6 / 13 / 832 / 71**(2025 占 **87%**); 两个方向都有(460 正 / 495 负); 原值 **−0.951 .. +3.678** 对存储的 ±0.300048828125。模块**拒绝该缺陷回来的两条路**: **无缺省窗口、无缺省 sha**; 且窗口末端越过 2026-09-11T00:00Z 时**抛异常**而不是对索引从未见过的 bar 回答「干净」。电池 20/20, 外加**突变检查 5/5**(窗口缺省 / sha 缺省 / 覆盖检查 / `assert_clean` 抛出 / sha 比较各删一次, 每次恰好预期那一格变红, 还原后全绿)—— **只有绿电池只能说明旧缺陷不在**。**RET-02 仍开**: 八个具名装置仍读裁剪通道, 逐装置暴露仍未测。

## §20 第八轮: 通用条目 + 用户提问引出的一项缺口(2026-09-16 05:4xZ, lead)

### 20.1 ★ 三条通用条目(已由 FX-PROD 单格化提交 6684895e, 全体适用)
1. **G-1(整类设计否决)**: `ShadowState.save()` 写**固定键集** ⇒ 任何写进 `aux.json` 的额外键都会在**下一个锚**被丢掉 ⇒ **「把『本状态已吸收到哪一版 / 哪些行』记录在生产者状态内部」这一整类设计都不成立** —— 不是标记、不是版本字段、不是已应用修正清单。**对任何未来的迁移工具都适用**, 不只 FXR-PROD-1。**由读 `save()` 得到, 不由行为推断。**
2. **G-2(检查表规则)**: **返回 dict 的函数必须返回恒定键集**, 源缺席处给 `None`。短字典会把 `if key in d` 变成**对「该函数存在的意义」那一项检查的静默跳过**。来源: 同一小时内的两个实例 —— PROD-28 装置找 `MANIFEST` 而文件名是 `MANIFEST.json`(⇒ `bundle_mismatch=None`); `h_source_of()` 在 `target_blend` 缺席时返回短字典。
3. **G-3(新)**: **凡失败模式是返回码的调度, 该返回码必须被读取并写进记录。** shell: `rc=$?` 不得与被测命令之间隔管道或 `tail`(有管道用 `PIPESTATUS` / `pipestatus`)。Python: **`subprocess.run` 在非零退出时不抛异常** ⇒ 不读 `returncode` 等于没发。FX-PROD 今天第三次撞到同一形态(PROD-46 的页报调度), **是从测试 stderr 看到子进程失败而格子仍绿才发现的** —— 即「装置绿 ≠ 被测动作发生」。

### 20.2 PROD-46 交付确认(在裁定送达之前已完成, 与裁定一致)
克隆 `f70397b`, 收据 `83a197dc`, 通用条目 `6684895e`。**实盘文件 2 格 2 失败(机制缺席)→ 修复后 8 格 0 失败。** 行为: 覆写前比对 —— 相同 ⇒ 计数 `rerun_noop` 且**不重写**; 不同 ⇒ **拒绝覆写并页报 HIGH**, 保留首个工件、把新的存到旁边作 `.rerun_<ts>.npz` 证据; **不可读 ⇒ 按「不同」处理**(不覆写我们无法核验的东西)。`sidecar_blend.py` 与 `combo_stage.py` 同法(共享写路径)。**`>=` 前后都未触碰**, PROD-48 是它的记录。**「谁赢」一步未实施**: 守卫改的是**是否允许覆写**, 从不改**谁写**。
**红的诚实界(35.10, 工作者主动写下)**: 该红**只证明机制缺席, 不证明旧码会覆写**; 覆写的证据是 P12 普查与 mtime 归因(128/129 锚由侧车最后写, 在其完成 ±1.0 s 内), 不是这一格。
**未接受**: PROD-46 改了 `combo_stage.py`, 其原链邻居是 **P2-R0**; 全电池 + `tests_target_live_output.py` 在 N+50(04:50Z)之后一次跑, **报了才算**。P9 生成器的逐字节身份检查同批。
**换装计划 §2 步骤 3 现已写全 `--allow-out-of-tail` 的四条**, 含我点出缺的第四条: **该旗标不使控制失效** —— 被传时正控仍闸住发布(由重跑那条唯一的尾外残差 ONG dacc −3.40e-08 未过 `positive_control_within_1e12` 而被拒所实测)。并明写: **四条缺一, 合同不成立。**

### 20.3 BNXUSDT 的读法更正(FX-PROD 核, 更正 FX-DATA TRD-04 F6 的一半)
**−205.7 bps 是真实的场所费率**: zip 申报 `iv 8.0`, 两侧 8 小时间距干净 ⇒ **「间距被标错」这一假设对该格被证伪**; 它是**可交易性 / 成员资格**问题, **不是资金费间隔问题**。TRD-04 F6 的另一半仍然成立(该锚 NODATA 而 qvk 有限故过成员筛, 且审计的两个旗标都看不见它)。**不得把这个数当成间隔缺陷的例子。**

### 20.4 ★ 用户提问引出的一项缺口: 独立研究员的平行研究我们一行未读
用户 05:3xZ 问:「过去两天独立研究员推动了好几轮的调研和修复, 是否有必要先全面了解?」—— **有必要, 而这是 lead 的缺口。** 我此前只读了他们对**我们纲领**的复审(9f6384fb / `REVIEW_fixprogram_progress_2026-09-14.md`), 而他们在**十条分支**上跑了一整套平行研究, 我们**一行未读**:
| 分支 | 最后提交 |
|---|---|
| `codex/fullchain-continuation-20260914` | **09-15 23:57(最新)** |
| `codex/public-funding-evidence-20260915` | 09-15 23:54 |
| `codex/f10-fullaxis-readback-20260915` | 09-15 20:35 |
| `codex/f10-assessment-review-20260915` | 09-15 02:34 |
| `codex/f10-fullaxis-conditional-20260915` | 09-15 02:18 |
| `codex/f10-fullaxis-provider-controls-20260915` | 09-15 00:58 |
| `codex/raw-month-repair-20260915` | 09-15 00:44 |
| `codex/f10-lifecycle-four-stage-20260915` | 09-15 00:30 |
| `codex/causal-producer-generation-20260914` | 09-14 23:17 |
| `codex/known89-data-20260914` | 09-14 22:28 |
(全部 600–673 提交领先 main, 共享长历史 ⇒ 须两两相差而非只对 main 相差。另有 worktree `agent/codex/QNT-2026-0907/onboarding-audit` 头 d0d82862。)
**从分支名即可见与我方登记的重叠面**: f10 全轴 / 生命周期四阶段 / 因果生产者生成 / 原始月修复 / 公开资金费证据, 正压在 **FEA-01 · TIM-01 · TRD-01/05 · PROD-11 · F10 导出链(TRN-03/14) · 生产者 col-80 v0/v1 · 资金费间隔表 · P2 连续 combo 认证** 上。
**处置**: 已派只读通读线 **CODEX-SURVEY**, 交付物 = 分支→主题映射 · 逐项「问了什么 / 测了什么 / 结论 / **他们自己声明没有确立的东西** / 依据的收据 sha」· 与我方登记的**重叠与冲突**两张表 · **对我们全新的发现**。**裁定: 在该通读回来之前, 不得基于「我方自己的结论」去动模型输入族的任何代码**(FX-MODEL 的红测试与新构建器一律等它)。事实表与测量可以继续。

### 20.5 §20.4 的拓扑更正(CODEX-SURVEY 早期映射, 2026-09-16 05:5xZ)
「十条分支」这个说法**是我的框架错误**。实测拓扑: 十条分支与我们的 `research/book-uplift-2026-09-11` 共同分叉于 **`0c65883b`(09-07 18:05)**; 自那以后**他们 243–244 提交, 我们 728 提交** —— 所谓「600–673 领先 main」里绝大部分是**我们共享的历史**(`main` = 9ffe0082, 落后双方很多)。他们的真实独立产出 = **244 提交 / 09-07..09-15**。
他们自己的线在 **`1fd02c7f`(09-14 23:03「Bind isolated cash capsule paths and verify actual subprocess completion gates」)** 汇合, 然后分成**三个活头 + 两条停滞侧枝**(祖先关系以 `git merge-base --is-ancestor` 验过):
| 头 | sha / 时间 | 角色 | 主干之外的 md |
|---|---|---|---|
| **A `codex/fullchain-continuation-20260914`** | 8990ebd3 · 09-15 23:57 | **回放 / 经济学**: 当前模型的 **608 天条件回放**; 费用与部署模型分离 | 54, 含唯一的新顶层文档 `docs/RESULT_current_strategy_replay_2026-09-15.md` |
| **B `codex/public-funding-evidence-20260915`** | 6e6f5dc6 · 09-15 23:54 | **现金 / 资金费证据**: 按标记估值的回放 + 独立记账(含 raw-month-repair) | 72(cash capsule · settlement box · canonical month repair · Dec-2024 恢复) |
| **C `codex/f10-fullaxis-readback-20260915`** | 4dca09cf · 09-15 20:35 | **F10 生命周期 / 全轴**: 四阶段适配器 · provider controls · King0 seed42 预测桥 | 78(整棵 `f10/`) |
- 五条 `f10-*` 构成单链止于头 C; `raw-month-repair` 是头 B 的祖先 ⇒ **只有三个 tip 要读**。
- 停滞侧枝: `known89-data-20260914`(离主干 1 提交)· `causal-producer-generation-20260914`(离 `ec16cbb0` 12 提交: 生产者生成修复 · Mac↔Pod NumPy 服务交叉核 · AERGO 七月资金费/存档缺口审计)。
- **规模: 自 0c65883b 起新增 1,079 个 markdown, 分布在 68 个 `multi_asset/exports/research/codex_*` 目录**; 09-14/09-15 的工作几乎全在 `codex_causal_fullchain_2026-09-14/{book,data,f10,integration,plans}/` 下。
- **仅凭文件名即已看出压在我方登记上的件**(尚未读, 只作标记): `data/canonical_month_repair_20260914/ORIGINAL_FULL_AXIS_AUDIT_20260915.md` · `integration/root_missing_four_funding_months_20260915/REVIEW.md`(**缺四个资金费月** → 我方 FND-01/02/03 与 P9 表)· `integration/current_fee_model_clarification_20260915/REPORT.md`(→ X-COST 与 FXR-DOC-2)· `plans/FINDING_executor_sizing_boundary_2026-09-15.md`(→ 执行器三条线)· `f10/strict_production_identity_audit_20260915/REVIEW.md`(→ PROD-28 与训练/服务平价)· `f10/current_rules_oos_candidate_20260915/REPORT.md` 与 `f10/formal_known89_lifecycle_20260914/RESULT.md`(→ TRD-01/05 与 FX-MODEL 成员规则选项表)。
**读序裁定**: **`docs/RESULT_current_strategy_replay_2026-09-15.md` 先读且单独回报** —— 它是当前模型的 608 天条件回放, 是任何人做出来的、最接近正面回答「为什么回测 3.0+ 而实盘差」的东西。对它要逐项问: 估计量(模型 / 输入 / 宇宙 / 成本面 / 记账口径 / 窗与锚数)· **它自己声明没有确立的东西** · **它的输入是否带着我们已登记的缺陷**(FEA-01 / TIM-01 / UNI-01 / PROD-11)—— 若带着, 则它回放的是「**带缺陷的当前模型**」, 结论须照此限定 · 任何 Sharpe 必须连窗、锚数、成本面、CI 方法一起抄(FXR-DOC-3)。


### 20.6 编号第二轮扫除(AUD-KB 410555c8, lead 裁定)
**再一处活撞号: TRN-28 → TRN-30。** AUDIT_TRAIN 的 **TRN-28** = 「CLAUDE.md 把月度重训路由到已被取代的九月 runbook」; 我在 §15.2 开的 TRN-28 = P1「`pod_f10_np_export.py` 在自己的 V1 门判词之前写出可部署 npz, 且默认 `F10_OUT` 就是在役工件路径」。**比 PROD 那次更糟: 同一份文件的 §3.2 第 100 行早已把 `TRN-28` 按 AUDIT_TRAIN 的原义路由给 K4** —— 一个号、两个主、两个严重度, 在同一个文件里。AUDIT_TRAIN 最高号 TRN-29 ⇒ **改 TRN-30**, 原号标 SUPERSEDED-ID, §15.2/§15.3 引用已同步。
**其余 32 个新号全部干净**(逐一对五份登记查过): OPS-04(AUDIT_EXEC 止于 OPS-03)· LED-09 · RES-01 · TEST-01 · BAT-01 · EXEC-RACE-01 · DATA-COR-1 · W6C-I6 · MON-1..4 · 全部 15 个 FXR-\*。
**`PROD-28-STALE` 保留**: 它是对 AUDIT_PROD 的 PROD-28 **记录本身的状态标注**, 不是把一个**新发现**挂到既有号上 —— 与 PROD-36b 恰好相反, 我给 PROD-36b 改号的理由对它不适用。
**两处撞号早于本纲领, 裁定不改号**: `LED-01` 与 `DOC-01` **各被 AUDIT_EXEC 与 AUDIT_DATA 定义两次, 所指不同**(LED-01: fills 每笔成交存两份 / 研究读者从 daily_nav 打印错费列; DOC-01: STATE+CLAUDE 携带陈旧执行器事实 / 口径文档与记忆条目误述数据谱系)。**不改号**, 因为那是另外两位审计者已提交的登记, 改号会让**每一条既有引用悬空** —— 那正是我给自己的新号改号所避开的代价。**一律加前缀引用: `EXEC:LED-01` / `DATA:LED-01` / `EXEC:DOC-01` / `DATA:DOC-01`。**
**§17.5 的规矩补一条**: 查重范围**包括四份审计彼此之间**, 不只是纲领对审计。

### 20.7 ★ KB-73: 绿电池认证的是「钉写在文件里」, 不是「钉被用了」
AUD-KB 实测四条边(比我先前转述的锋利):
1. `run_acceptance.sh` 在**仓库根**, 不在 `ops/`(`safe_commit.sh` 才在 `ops/`); **CLAUDE.md:46 读起来像两个都在** —— 该行由 lead 更正。
2. L28 是 `PY="${ACCEPT_PY:-/usr/bin/python3}"` —— **可覆盖的缺省, 不是硬钉**。文件自己 L20-22 列出三个解释器: `/usr/bin/python3` 3.9.6(torch 2.2.2 + numpy 1.26.4 + pandas 2.3.3, **唯一能跑推理的**)· `/usr/local/bin/python3` 3.14.4(裸 `python3` 解析到它, **无 torch**)· `/opt/anaconda3` 3.7.6。
3. **守卫查的是文本不是行为**: `live/tests_acceptance_entrypoints.py:55` 断言 `"ACCEPT_PY:-/usr/bin/python3" in open(ROOT_SH).read()` —— **源文件的一个子串**。把 `ACCEPT_PY` 指向 3.14 跑, `tests_inference_parity` / `tests_panel_build` 因无 torch 而红, **而该套件照样打印 OK「ACCEPT_PY pinned」**。同族: 「守卫查的是文本不是行为」。
4. **没有任何收据记录解释器**: `state/acceptance/` 38,177 个工件中 **0 个**记 Python 版本(465 个匹配该路径的全是 gate_coverage 的字节码缓存盲区注记, 非运行收据); L278 逐套件调 `"$PY"` 却从不回显解析后的路径。
**历史证明风险非假想**: `live/run_acceptance.sh` L15 自记 2026-07-27 之前的双门分裂「制造了两个假的 known failures」—— 正是那两个套件, 在裸 `python3` 下红、在钉住的解释器下**双双通过**。
⇒ **任何 2026-07-27 之前的「逐套件 N/M」与之后的不可比, 且没有任何日期的计数说明它是由哪个解释器产生的。** 已标注引用此类计数的五行 KB(KB-12 123/123 · KB-13 124/124 · KB-35 135/135 · M3-35 132/132 · M5-02 135/135)。
**lead 裁定**: ① **本轮每次电池的收据必须记下解释器**(`ACCEPT_PY` 是否被设 / 解析后 `$PY` 绝对路径 / 该解释器 `sys.version` 与 `torch.__version__`, 无则具名), 跑前跑后各一次 —— 已下发 FX-EXEC 与 FX-PROD, **不改 `run_acceptance.sh`, 在各自外层记**; ② **运行器改造与守卫改造(从源码子串改为断言有效解释器)由 FX-EXEC 落地, 且必须在三分支叠加电池之前** —— 否则叠加电池同样什么都没认证; 红测试 = 旧码上把 `ACCEPT_PY` 指向 3.14 跑该套件仍打印 OK。

### 20.8 PROD-44 归属与修法裁定
**唯一实盘消费者 = `~/dl_quant_live/ops/anchor_report.py:49-50`**(`S.get("ok") and S.get("reader_ok")`, **不比 `S["anchor"]` 与本报告的 `A`**), 由 FX-PROD 全仓 grep 三棵树复核, 并与早于本纲领的独立记录相符(`PREREG_ship1_amihud_4th_leg_2026-09-11.md:159`「唯一消费者」)。**同一文件在别处都比锚**(L40 `d.get("anchor_ts") == A`; 按锚读 `target_combo/{A}.json`)—— **只有状态文件这一处忘了**, 这把它从风格疏忽钉成干净缺陷。
**归属**: 文件属 **FX-EXEC2**(它刚为 LED-08 改过 `anchor_report.py`)⇒ 派给 FX-EXEC2, FX-PROD 交出事实表 `0c3f6a4e`, FX-EXEC 只需在 gate_coverage 为新读者留具名边界。
**修法按 FX-PROD 的提法, 不按 lead 原框架**: **不是「加一个 `status["anchor"]` 比较」**, 而是让读者改读 **`state/combo_anchor_record/<A>.json`**(PROD-27 新增, 按构造逐锚, 带 `form_written` / join key / 三个余量 / `h_source`), 把单槽对象**从消费者路径里拿掉**; 旧槽继续写以保持兼容。判据: **把一个陈旧也能满足的活性检查, 换成一个陈旧无法满足的。**
**两处克制保留**: ① 两个静默锚上危害是**部分的** —— 槽里是另一个锚的成功, 但 `target_combo/<A>.json` 对两者**确实缺失**, 姊妹检查会报警 ⇒ 报告不会全绿; 缺陷精确地是「『combo 写者**在本锚**成功了吗』被另一个锚回答了」。② **当天报告实际说了什么不可复原**(`anchor_report_last.json` 只存最近一份)⇒ 标 NOT ESTABLISHED, 不从代码倒推。

### 20.9 UNI-03 交付(FX-DATA `7a761621`, 装置 `e14df41a`)
run 14 rc=0, **5/5**; 收据 `RECEIPT_fx_uni03_sep_mask.json`(`08bf49d4`)。**不需要新缓存谱系**: `dlnative_5m_wide829_f16_ext.npz` 恰好止于 2026-09-01T00:00Z, 而那**就是**九月首锚, 规则的窗是其前 8640 根 bar ⇒ 同规则同缓存, 往前一个月。
**正控双掩码逐位**: `umask_UPIT.npz` 全部 56 个已提交月行零差异格重建, `umask_UPIT_CRYPTO.npz` 过类过滤后同样; 任一失败即拒写九月行。
**2026-09 行**: 挂牌 826 · 合格 676 · top 449 · 第 449 名尾随 30 日成交额 57.53 M USD(八月 53.19 M)· **CRYPTO 放行 375**(八月 373)。
**对照被结转的八月行: 加 60 / 减 58 = 373 中的 118 个名格 = 31.6%。** **但工作者自己先量了基准而不是让 31.6% 裸奔**: 过去 12 个月 CRYPTO 放行集的月度换手中位是 **40 加 / 41 减**(2026-03→08: 39/41 · 41/50 · 54/59 · 43/55 · 34/54 · 49/76)⇒ **九月约为常态的 1.5 倍, 其中大部分是任何结转都会有的普通换手, 九月偏重但不是九月特异的异常**。**不得脱离这个基准引用 31.6%。** 60 个新进者**没有一个**经由 `build_crypto_mask.py` 的「未知类别 ⇒ 保留」兜底进来。
**自报两次做错月界**: x0910 面板轴比已提交掩码多 60 个锚, 但**其中 5 个(2026-08-31 04:00Z..20:00Z)仍属八月**, 而月度规则按**日历月**赋行 ⇒ run 12/13 把九月行写到了那五个上; 真实九月锚数是 **55 不是 60**。现按日历月赋行并加了覆盖八月尾巴的断言。**被取代的工件 sha `023adc09` 不得使用。**
**工件**(x0910 轴 10,099 锚, 前缀与已提交掩码逐位相同): `umask_UPIT_x0910_sep.npz` → `66e21c89…` · `umask_UPIT_CRYPTO_x0910_sep.npz` → `de7c34d7…`。
**UNI-03 未关闭**: 没有任何既有九月读数在真实行上重跑过 —— 那属于 T2 d4 · T5c/T5d · `t1_states.py:78-81`(它同样是结转)。**十月的滚动应调用该装置而不是再结转一次** ⇒ 已转 FX-TRAIN 并入 TRN-01。

## §21 ★ 独立研究员平行研究的辩证复核 · 第一批(2026-09-16 06:0xZ, lead 亲测)

用户 05:5xZ 字:「一定要深入辩证地分析是否有道理、是否真实存在…确保整个策略所有 pipeline 无懈可击…之后给完整结论、提交、代码, 交独立研究员复审。」本节只写 **lead 亲自在我们自己的实盘记录上量过的**结论; 通读线的转述另见 §22。

### 21.1 ★★★ EXE-05(新, P1, lead 亲测): 10% 杠杆死区**从未在生产上生效过一次**
独立研究员 `CF/plans/FINDING_executor_sizing_boundary_2026-09-15.md` 断言我们的 `scheduler/run_anchor.py:314` 每锚以 gross=0 建对象, 因此跨锚 10% 死区在标准调度路径上不可能成立。**我没有转引, 我自己查了代码并在实盘日志上用算术恒等式验证。**

**代码链(执行器运行树 `ef60f85`, 与实盘 HEAD 相同)**:
1. `com.dlquant.live.anchor` 是 **`StartCalendarInterval`** 作业 ⇒ **每个锚是一个全新进程**。
2. `scheduler/run_anchor.py:314`: `loop = AL.AnchorLoop(b, ex, gross_usdt=0.0, ...)` —— 其上方注释明写这是**有意**的:「A zero seed means 'no previous gross', which is exactly true at process start and forces the first anchor to size from equity」。
3. `scheduler/anchor_loop.py:1343` `prev = float(self.gross or 0.0)` ⇒ **0.0**
4. `:1360` `actual = (prev / nav) if prev else None` ⇒ **None**
5. `:1362` `resize = (actual is None) or (drift is not None and drift > dead)` ⇒ **恒 True**
⇒ `config/book.json` 的 **`leverage_deadzone_frac = 0.10` 在生产路径上是一个永远不可能生效的政策数**。注释对「进程的第一个锚」的说法是对的 —— **但每一个锚都是它自己进程的第一个锚。**

**在实盘记录上的算术验证(lead, 只读 `~/dl_quant_live/state/anchor_runs.log`, 2026-07-29T08:55Z..2026-09-16T00:24Z)**:
- 携带定量块的行共 **562**; 其中 `"gross_previous": 0.0` **562/562** · `"actual_leverage": null` **562/562** · `"leverage_drift_frac": null` **562/562**。
- 只取 **mode=LIVE** 的 **272** 行, 逐行解析定量子字典并检验恒等式 **`gross == round(nav × target_leverage, 2)`** ⇒ **272/272 成立, 0 例外**(容差 0.011)。
⇒ **死区一次都没有抑制过重定规模。每一个 LIVE 锚都把整本书按权益重新定规模。**
(用恒等式而不是 `"resized"` 旗标, 是因为同一行日志里别处也有 `blind` / `resized` 同名键, 正则会串行 —— 这一点我第一次就踩到了, 改用逐字典解析 + 算术恒等式。)

**后果, 要测不要断言**: ① **换手**: 每锚都付了死区本应避免的那部分「按 NAV 漂移重新缩放整本书」的换手, 量 ≈ 每锚 |ΔNAV/NAV| × gross —— **必须实测**, 不得由我估。② **研究/生产背离**: 凡是把死区建模为**生效**的回放或换手整形研究(EMA+带 / 深平滑带 / 自适应换手族), 其换手系统性地低于生产 —— 与「部署 carry 是回放 2 倍」同一族的背离来源。③ **政策选择本身是书行为**: 「跨锚持久化 gross 使死区真正生效」会改变书每锚的目标, **须用户裁定**; 「删掉这条永不生效的配置并在文档里写明书每锚按权益重定规模」只是文档。
**定级**: P1 —— 不是因为它当下在亏钱(未测), 而是因为**一个被写进配置、被研究引用、却在生产上从不可能生效的控制**属于「已声明的盲区 ≠ 已关闭」与「门存在但判词不控制写入」同族的最硬形态。

### 21.2 ★ EXE-06(新, P2, lead 亲测): 单位 gross 归一 —— **对实盘是纯尺度, 对回放才是形状**
独立研究员测得(全 3,648 锚, 六本 STRICT 书): 回放侧 `combo_stage.py::exec_reshape` **去均值后把输入 gross 还原**(实测 `g0 = |w|.sum()` / `g1 = |o|.sum()` 两行确在 `combo_stage.py:203-204`), 其平均 gross = **0.766448(King 参照书) / 0.709066(F10 seed42 combo) / 0.715757(seed2027)**; 而实盘 `live/external_book.py:483-490 target_vector` 返回 **`w_in / gross_in`, 按构造 sum|·| ≡ 1**, 再由 `to_notional(·, gross)` 乘 `NAV × gross_mult`。
**lead 的补充测量(只读 145 个带 `external_book` 的实盘锚)**: `gross_outside_frac` **min=median=mean=max = 0.000000**, `n_outside_universe` **恒 0**。
⇒ **在实盘上, 生产者的名全部落在执行器宇宙内, 故 `gross_in` = 文件总 gross, 除它是一个纯标量 ⇒ 形状被精确保留, 差异只在尺度; 而实盘的尺度本来就由 `NAV × gross_mult` 决定。**
⇒ **该背离咬的是回放, 不是实盘**: 任何直接拿 `exec_reshape` 输出当实盘书、不经 `target_vector` 的回放, 其 gross 是实盘的 **0.71–0.77 倍**(即**少 23–29% 杠杆**)。**这直接压在我方 P2 连续 combo 认证链上** —— 该链若在 `exec_reshape` 之后未过 `target_vector`, 其书层读数按构造与实盘不同尺度。独立研究员自己的 608 天主结果**不受此影响**(它用的是动态 NAV 引擎, 全期日界平均 gross/NAV = 1.9876)。
**注意他们自己的警告, 采纳**:「**不能把原现金收益乘一个常数冒充修正结果**」—— 该乘子逐锚不同且经 NAV 反馈复利。

### 21.3 lead 对 608 天回放的辩证判读(证据见 §22 通读转述, 结论为 lead 所下)
1. **头条 2.52 的成立前提是关掉了实盘正在跑的那条停机政策。** 同窗同数据同模型, 保留永久停机 ⇒ **+6.9308% / 夏普 ≈0.606**。两个数都不是与实盘可比的数(保留停机那个没有人工复场规则, 且停机前 335 次发布全为 King 回退)。**与实盘可比的那个数——「停机 + 我们实际执行的人工复场」——没有人做过。** 这是最重要且最便宜可补的缺口。
2. **回放没有与实盘矛盾, 它复现了实盘的坏。** 2026 年 8 月单月 **−5.9586% / 夏普 −1.82 / 回撤 15.53%**; 实盘 08-26 开跑。⇒ **「实盘差」不能全部归因于实现缺陷**, 该月对这本书自身就是坏的。分辨率有限(重叠仅 6 天 = 36 锚), 已派 VER-OVERLAP 用我们自己的账本做逐日四桶分解。
3. **「夏普显著 >3」在修复前后都没有被支持。** 他们: 608 天 **[0.858, 4.185]**(30 日块, **未校正选择偏差**, 且「重采样没有重新执行止损」)。我们: T6 的 N_eff ≈ 1.57, 在役冻结窗 2.94 自身 CI95 [1.306, 4.565]。**两台互不相干的仪器给出同一个结论。** 分状态表进一步说明: 低波动下跌 148 天夏普 **1.361**, 且 **2025 的该格仍为负**; 高波动下跌那格 4.420 只有 **43 天**, 他们明写不可外推。
4. **「修了很多根本性问题 ⇒ 策略变好了」这一步没有证据, 而且他们自己先说了。** §5 标题即「**严格因果后的差距: 没有可报告的配对估计**」, 并明写「**不能从旧全周期 1.29 与本次 2.52 相减声称提升**」。更硬的是他们自己的介入式对照(OLD/REPAIRED/ZERO King, 预注册 `7fbb57ab`, 18 个模型 3 臂 × 3 折 × 2 种子): **修复资金费列买不到稳定排序增益**(6 行里 5 行 CI 跨零), 而且**把两列整个置零只损失约 0.002 IC**。⇒ **FEA-01 作为覆盖/前视事实成立, 但不得再按「可回收的 alpha」给它记账。**
5. **他们确实修到了我们根本没去找的东西**(以下为其文档所述, 我方未复现): 三个整符号月**从未被下载进正典缓存**(1000000BOB 2026-02 · BMT 2026-02 · MTL 2026-04, 24,768 根 5m bar), 造成 **−16.87% / −15.53% / +9.34% 的幽灵首根 bar**, 修后 −1.83% / +0.65% / +0.17%; **EOS 于 2025-05-21 09:00Z 正式下架而旧日历漏了这次关闭** ⇒ **1,402 次未定价资金费事件持续 15 个月**; 以及 **2024-11-11 起币安的下架结算价规则 = 收盘前 30 分钟 1,800 个逐秒指数值的均值**(我们此前只有 0.5/0.9/1/1.1/1.5 的情景因子)。**这三条对我们是新的**, 且前两条与我们的 TRD-01 是**互补而非重复**: 我们查的是「死后还在写行」, 他们查的是「当时根本没采进来」。
6. **一处与我方发现互相独立地撞到同一堵墙**: 他们记「旧月 fold checkpoint 没有保存 mu/sd」, 与我方 FX-MODEL 今日独立测得的「20 个月折 checkpoint 只有裸 state_dict, `has_mu False has_sd False`」**完全一致**。两条线互不通气而结论相同, 这是本轮最强的一处交叉佐证。
7. **UNI-01 是我们独有的**: 通读线在其全部已读文档中**未发现任何一处涉及代币化股票 / 非 crypto 永续 / 3× 反向杠杆对**; 他们全程把 829 轴当作给定。⇒ **那两对 3× 反向杠杆(SOXL/SOXS · TQQQ/SQQQ)若在 829 轴上, 就在这次回放的训练人口与宇宙里, 未被处理也未被测量。**
8. **TIM-01 未被测试**(他们的折合同是「cutoff = 测试月首 E−4h」且特征含 E, 但**没有回答我们 E−1/E 的问题**), 且他们自己把「建模观察时钟与真实数据到达差异」列为范围外未决。
9. **表示层缺陷被明确保留**:「资金费只在基础列 80/81; `fresh=False` 先转 NaN, 随后 **NaN→0 并存 float16**; 额外 89 列**没有 availability 通道** … **模型输入仍可能混淆未观测、中性零值和量化零**」—— 与我方 FX-MODEL 今日就 FEA-01 写下的「必须带独立可得性位, 换填充值只是把二义性搬个地方」**是同一条**。他们刻意本轮不加通道以免把修复与特征干预混为一个实验 —— **这个克制是对的**。

### 21.4 lead 的裁定
1. **EXE-05 登记 P1**, 归 **FX-EXEC**: 只做 ① 代码链与实盘恒等式的事实表(我已给出全部读数, 它复核并补齐 `config/book.json` 的 `leverage_deadzone_frac` 出处与历史)· ② **换手后果的实测**(每锚 |ΔNAV/NAV| × gross 的历史分布, 以及它占已测换手 2–5.5%/锚 的比例)· ③ **不改代码**。「跨锚持久化 gross 让死区生效」是**书行为, 上交用户**。
2. **EXE-06 登记 P2**, 归 **lead + P2 链**: 立刻核 P2 连续 combo 认证链是否在 `exec_reshape` 之后经过 `target_vector`; 若否, 其书层读数的尺度口径必须重写。**禁止**用一个常数乘子去「修正」历史现金收益。
3. **补做那个与实盘可比的数**: 请独立研究员(或我方)跑一个**保留全书经济停机 + 明确声明的人工复场规则**(按我们实盘实际做法: 停机后人工检查通过再复场)的同窗情景。**在它出来之前, 2.52 与 0.606 都不可用于回答「实盘应该长什么样」。**
4. **FEA-01 的 alpha 预算撤销**: 保留其覆盖/前视事实与我方的「可得性位」要求, 但**不再把它列为可回收 alpha 的来源**; 我方 FX-MODEL 的三臂预注册照做, 目的改为**测量而非回收**。
5. **新增一类数据缺陷进纲领: 采集缺月(acquisition omission)** —— 与 TRD-01(死后仍写行)、E-0908-B(裁剪)都不同。**要求 FX-DATA 增加一项月度清单完整性检查**(逐符号逐月的存档存在性与行数), 并**独立复现**他们点名的三个符号月与那三根幽灵 bar。
6. **UNI-01 的测量优先级不变且更高了**: 既然他们的回放把这些名带在训练人口里而未处理, 那两对 3× 反向杠杆对**这次 2.52 的结果同样有效**。FX-MODEL 的 ①–⑤ 测量照做。

### 21.5 ★★★ EXE-05 追加(lead 亲测, 五环链条闭合): **一个绿套件在认证生产路径永远到不了的状态**
承 §21.1。我继续查「为什么这条从来没被发现」, 链条闭合如下, 每一环我都自己读过:

| 环 | 事实 | 证据 |
|---|---|---|
| 1 | **配置声明了它** | `~/dl_quant_live/config/book.json` `leverage_deadzone_frac = 0.10` |
| 2 | **代码正确实现了它** | `scheduler/anchor_loop.py:1340-1363`: `dead` 取自配置; `drift = abs(actual/tgt − 1)`; `resize = (actual is None) or (drift > dead)` |
| 3 | **测试套件正确认证了它 —— 靠自己注入一个上锚 gross** | `live/tests_sizing_policy.py`: `_in = _L(9216.0, 4700.0)._size_book()` 断言 drift ≤ DEAD 不重定规模; `_out = _L(9216.0, 3686.0)` 断言 drift > DEAD 重定规模; `_edge = _L(4608.0*TGT, 4608.0*TGT/(TGT*(1+DEAD)))` 断言边界恰在 `TGT*(1+DEAD)`; L58 还断言 `DEAD == 0.10` |
| 4 | **生产入口从不注入那个状态** | `scheduler/run_anchor.py:314` `AnchorLoop(b, ex, gross_usdt=0.0, ...)`; `com.dlquant.live.anchor` 是 `StartCalendarInterval` ⇒ **每锚一个全新进程** |
| 5 | **实盘记录的算术恒等式** | LIVE **272/272** 锚 `gross == round(nav × target_leverage, 2)`; `gross_previous` 562/562 为 0.0 |

**该套件里唯一在生产上真实发生的那一格, 是 L67-68 的 `_first = _L(0.0, 4608.0)` 「★★ first anchor (no previous gross) sizes from equity」—— 它被当作众多情形之一, 而它是唯一的情形。**

⇒ **通用规矩(新, 全体)**: **一个自己构造被测状态的套件, 必须同时证明「生产入口能够构造出那个状态」。** 否则它认证的是一条生产永远走不到的分支。这与 KB-73(守卫断言源码子串而非有效解释器)、G-1/G-3、以及「门存在但判词不控制写入」是同一族的**第四种形态**: **测试通过构造一个生产构造不出的状态来认证行为。**
**gate_coverage 必须为此新增一类具名边界**: 凡断言依赖注入状态的格, 需声明「生产可达性」由谁证明。

**对我方既有结论的影响面(要查, 不要假设)**: 研究仓内引用死区的文件 —— `REDTEAM_wide_live_prelaunch_2026-08-22` · `RUNBOOK_wide_live_2026-08-22` · `SURVEY_arch_modules_2026-08-24` · `DESIGN_wide_replay_P3_2026-08-16` · `DESIGN_differentiable_book_loss_2026-08-22`, 以及记忆条目 `deepsmooth_band_deployed` / `turnover_shaping_ema_revalidated` / `adaptive_turnover_family_closed`。**凡把死区当作生效前提的换手整形结论, 其换手基数与生产不同, 须逐条重判**(归 FX-EXEC 出清单, 归 AUD-KB 进 KB 登记)。

### 21.6 另两条对我方生产代码的断言, lead 亦已亲验
- **`RebalanceExecutor.plan` 在计划 mids 上形成固定张数 —— 成立。** `live/binance_executor.py:760-800` 的 docstring 与代码: 取 `mids`, 走 `delta → band → min-notional → lot rounding`, 逐名 `qty` 由 `delta / mid` 得出并记 `qty_source = "notional_over_mid"`; **全退出优先 `-held_qty`** 并记 `qty_source = "venue_position_qty"`(这正是 E-0912-A (b) 的修复)。⇒ **被控制的量是张数不是名义**; 成交价偏离计划 mid 时, **实际成交名义随之漂移**。**凡假设「名义是被控量」的执行器改动一律按此收窄** —— 已下发三条执行器线。
- **`gross_outside_frac ≡ 0`(实盘 145 锚)** ⇒ 见 §21.2: 归一在实盘是纯标量, 形状不变。**但独立研究员测得的 ΔL1 由 0.0313 升到 0.0447(≈ +43%)正是这个标量的倒数效应**(1/0.709 ≈ 1.41): **任何不经 `target_vector` 的回放, 其书比实盘小 0.71–0.77 倍, 换手需求相应低约 29–43%。** 这给了我方「部署 carry 是回放 2 倍」一个**可检验的、构造性的**候选来源, 须逐项核 P2 链与换手整形研究是否走了归一步。

## §22 ★★★ 2026 到底是不是样本外 —— 两侧证据合并后的精确答案(2026-09-16 06:3xZ, lead)

**起因**: 独立研究员 `CF/f10/current_rules_oos_candidate_20260915/REPORT.md` 的对照表里有一行说在役 F10 是**「当前固定权重全历史 refit」**, 因而**「固定在役权重不能在训练历史上当 OOS」**; 又说在役 King **「seed0 / 年度 / 无 60 锚 embargo」**。通读线同时指出**该行没有给在役侧的收据 sha, 是全文最弱的一行**。若照字面读, 我们所有 2026 的水平读数(含 2026 年内 Sharpe 4.53、regime 3.0+)都会变成样本内 —— 那将直接回答用户「为什么回测好实盘差」。**所以我没有转述, 我回到我们自己已受据的事实。**

**我们自己的受据(E-0907-D, 2026-09-07 由独立研究员发现、我方复算确认, 记忆条目 `live_model_legs_stopped_learning_end_2025`)**:
- `pod_f10_refit_ext.py`(sha `ea3675b8012ea266`)**L90** `cut = int(len(tr_idx)*0.85); tr1, va1 = tr_idx[:cut], tr_idx[cut:]` —— **梯度只用 `tr1`**, 而 `tr_idx` 是**按时间排序**的 ⇒ 被留出的最后 15% 恰是**最近的一段**。**L122** `"trained_through": int(E_ts[tr_idx[-1]])` 记的是**索引终点(含验证段)**。在 dlw_targets(n=10,086)上复算: **梯度最后一个锚 = 2025-12-01 16:00Z**, 而 `trained_through` = 2026-08-10 20:00Z —— **两者相差 252 天**。
- King: `tr = YRA < 2026` ⇒ **止于同一处**。

**⇒ 精确结论(两侧合并)**:
1. **2026 对两条腿的梯度而言是真正的样本外** —— **没有任何一段 2026 进入过梯度**。独立研究员那一行**方向对, 但对我们这件在役工件过强**: 它把「索引跨到 2026-08」读成了「权重拟合到 2026-08」, 而 L90 恰恰把最近 15% 划为验证段。
2. **但 2026 对「选轮」而言是样本内**: 被留出的 15% 验证段就是 **2025-12 → 2026-08** 那一段, 而我方另一条受据(`live_dl_epoch_rule_is_unconstrained_argmax`)记明在役 epoch 规则是**无约束 argmax**。⇒ **DL 腿的 epoch 是在一个包含整个 2026 的窗口上按效用最大挑出来的。**
3. ⇒ **2026 的水平读数既不是干净样本外, 也不是样本内 —— 污染通道是具名且可测的: 「在含 2026 的验证窗上做无约束 argmax 选轮」对该窗测得水平的抬升。**

**新登记 EVAL-01(P1, 可测且便宜)**: 用**只到 2025 的验证段**重选 epoch(其余一切不变), 再读 2026。**差就是选轮通道的量。** 这是直接瞄准用户原始问题的实验, 而**两侧至今都没有人做过**。归 FX-MODEL, 排在 GATE B-REPRO 之后、跑臂之前; 判据先于数字冻结, 用书层 δ = 0.05 bps/锚/gross。
**同时登记 EVAL-02(P2)**: 独立研究员那行「在役 King **无 60 锚 embargo**」与我方 FX-MODEL 今日实测「king 折是年度且 **embargo 为零**(`tr_ = YRA < YV; te_ = YRA == YV`, 最后训练锚标签止 12-31 23:55Z, 首个测试锚 01-01 00:00Z, **无重叠亦无 embargo**)**互相独立地得到同一结论** —— 两侧一致, 采纳为事实; 其对跨年边界读数的影响未测。

**给复审包的措辞(冻结)**: 「**在役两条腿的梯度止于 2025-12-01 16:00Z(DL)与 2025 年末(King); 2026 未进入任何梯度, 但 2026 位于 DL 的 15% 时序验证段内, 而 epoch 规则是无约束 argmax ⇒ 2026 的水平读数带有『选轮』通道的选择效应, 其量未测(EVAL-01)。**」**任何引用 2026 年内水平(含 4.53、regime 3.0+)必须带这句。**

**方法学一笔**: 这条正是「**引用前回到自己的受据, 不转述**」的价值 —— 若照转那一行, 我会告诉用户「我们的 2026 全是样本内」, 那是**错的**; 若完全无视它, 我们会漏掉**选轮通道**这个真实的、可测的选择效应。两边都错, 中间那句才对。

## §23 第九轮: 一个 100% 失败率的控制, 与三条构建器认证(2026-09-16 06:5xZ, lead)

### 23.1 ★ BAT-02(P1): 电池窗口规则被测试四次, 四次全失败 —— 缺陷在控制不在人
| 次 | 时间 | 谁 | 经由 |
|---|---|---|---|
| 1–2 | 2026-09-13 16:51Z / 17:01:50Z | FX-W6C | 直接起电池(一次被 lead 中止, 一次早 3 分钟且未取锁) |
| 3 | 2026-09-16 03:16:25Z | FX-EXEC | **传递到达**: `tests_acceptance_entrypoints` 第 85–90 行两次 `bash run_acceptance.sh`; 窗后 **85 秒** |
| 4 | 2026-09-16 04:28:43Z | FX-W6C | 手敲的邻格循环里含 `tests_entrypoint_wiring`(驱动 DRY_RUN `run_anchor`); **N+28min**, 在 04Z 锚窗内 |
**四次没有一次是「工作者不守规矩」 —— 四次都是「套件的网络性质从名字上看不出来」。** FX-W6C 自己的判词: 「**规则需要的是机械守卫, 不是我的注意力**」。**一个被测试四次、失败四次的控制, 缺陷在控制。**
**裁定(派 FX-EXEC)**: ① `run_acceptance.sh` / `gate_coverage` 携带**机器可读的 `NETWORK_TOUCHING` 集合** —— 直接发场所请求者 + **传递到达者**(已知: `tests_acceptance_entrypoints`、`tests_entrypoint_wiring`); ② 提供**共用守卫助手**: 输入一组套件名, 窗外即拒绝并**点名是哪一个、为什么**; ③ **手敲循环也必须走它**(四次里有两次正是绕过了自己已有的守卫); ④ 该集合的**完备性由构造证明**(扫全部套件的 `subprocess`/`bash`/`os.system`/`requests`/venue 调用生成, 而不是人工维护一张名单)。
**第四次的一个副产品, 按其自报方式处理**: 那次违规的 DRY 运行打印了 `book_observability_gate: {halt:false, state:NOT_EVALUATED}` 与带 `book_observation` 的 phase_C ⇒ **B13 的门与生产者判词在真实锚上接线正确**。**证据不因来路不正而作废, 但来路必须写在证据旁边** —— 工作者主动声明而非静默使用, 记为正例。

### 23.2 W6C 部署前判词检查: 修改后的代码对今天这本书**说同样的话**
用 `derive_ops_stats`(生产自己的)在 02:53Z 的只读实盘状态副本上跑修复后的看门狗:
| | 修复后 | 实盘 `last_eval`(00:45:38Z) |
|---|---|---|
| tripped | False | False |
| conditions_blind | `[]` | `[]` |
| §4-5b | CLEAN, 不 blind | CLEAN |
| cond4 `cum_return_from_start` | **1.1704**(限 −25.0) | **1.1704** |
新事实全部是**追加的**: `book_observability = OBSERVED` · **`halt_opening = False`(B13 的门今天不会停任何东西)** · 最新计划锚回读 249 行(上一锚 249)。cond4 加载 0 条修订记录并把**七个修前划转日全部命名 `unamended_prefix_day`** —— **那正是裁定 (a) 在 FX-EXEC2 的 apply 步骤跑之前规定的行为**。
⇒ **一个安全修复在部署当天应当什么都不改变, 只是多说几句话。** 这条作为部署前的标准检查项写进复审包。
**基线对照的写法也记一笔**: 139 个套件在 base 与 fixed 两棵树各跑一遍, **base 7 红 / fixed 7 红, 同样的七个, 无新增红**。**「无新增红」比「全绿」是更强的陈述** —— 它把环境红与代码红分开了。

### 23.3 FX-MODEL 三条构建器全部认证(14a20ab1)
| 构建器 | 基线 | 控制 | 结果 |
|---|---|---|---|
| `fm_dlw_features_fund.py`(FEA-01) | `pod_dlw_features_ext.py` `e86725cc` | C2 | **PASS** X 1,308,638 格 0 差异 |
| `fm_king_fea_asof.py`(TIM-01) | `pod_fea_ext_clamp.py` `b9f9c728` | K2 | **PASS** FEA 1,134,880 格 + 5 个 meta 数组 0 差异 |
| `fm_dlw_targets_asof.py`(TIM-01 + TRN-06) | `pod_dlw_targets_raw.py` `d7c52823` | T2 | **PASS** 基线所写全部 12 个数组 0 差异 |
**浮点一律经整数视图比较** —— `FEA` / `y4s` / `YR4s` / `YRZ` 按构造 NaN 密集, 带 NaN 宽容的浮点比较几乎不算测试。
**一个落出来的真实测量**: 在一个合约中途死亡的夹具上, 它作为训练成员**恰好再活 42 个锚 = 2016/48** —— **正是 7 日波动窗**, 之后被 `v7` 丢弃。这把 AUDIT_DATA TRD-05 的「约一周」变成了**精确数**。
**T3 三臂全读 +0, 且工作者把理由写在数字之前**: 夹具按构造是健康的(每根 bar 有限、每个名波动、80 个真实名**正因为在每个夹具锚上都 TRADABLE 才被选中**)⇒ 前向有限项排除不了任何人、可交易性筛排除不了任何人、一根 bar 的时钟位移翻不动任何阈值。「**那里的 0 意味着夹具无法展现该效应, 不是效应为零**」—— 该字段被命名为会先于数字被读到。**这是本轮最好的一次「先说这个数不能说明什么」。**
**第三个构建器基于已提交 blob 而非工作树**: `pod_dlw_targets_raw.py` 在其会话中途被 FX-TRAIN 改动(`d7c52823` → `4568bea6`), 是第三个如此的文件 ⇒ 取 `git show HEAD:<path>` 并把**对账要求写进自己工件的元数据**而不是留给记忆。**§19.4 的正确应用。**
**记录不修的一条**: 成员筛若清空, `keep = np.array([])` 是 float64, 下一行抛**裸 `IndexError`** 而不是具名拒绝。工作者是用真实符号构夹具时撞到的(那些名 2022-01 仍 NODATA, **筛拒绝它们是对的**), 于是**改自己的夹具、不动基线**(改基线是其项目之外的行为变更), 并登记以免被重新发现。

## §24 通读线合并重叠判定(CODEX-SURVEY, lead 采纳并加裁定; 2026-09-16 07:0xZ)

### 24.1 ★ FEA-01: 规模被独立复现到 0.01%, 而我们声明「未测」的那个效应他们已经测了
**格数两侧独立复现**(我们: 比对两份已存面板; 他们: 从 19,611 个钉住的原始档案、2,633,108 条原始费率事实**重建** 829 列):
| 年 | 我方(v2ext 有限 ∧ v3splice NaN) | 他们(旧缺失 → 新有限) | Δ | Δ% |
|---|---:|---:|---:|---:|
| 2022 | 104,374 | 113,921 | **+9,547** | **+9.15%** |
| 2023 | 160,652 | 160,636 | −16 | −0.010% |
| 2024 | 245,209 | 245,195 | −14 | −0.006% |
| 2025 | 316,990 | 316,965 | −25 | −0.008% |
| 2026 | 202,688 | 202,530 | −158 | −0.078% |
**两台方向相反的仪器, 在 10⁵–10⁶ 量级上合到 6–158 格。** 唯一分歧是 **2022 的 9,547 格(9.15%)**, 已派查(轴起点 2020 vs 2022 的暖启/边界 · 成员对 vs 全面板格的人口差 · 真实分歧, 三选一即可)。
**我方 FEA-01 的收尾句是「对 F10 预测与书的效应大小未被测量」—— 他们测了**: 预注册 `7fbb57ab` 先于数字, 18 个模型 = OLD/REPAIRED/ZERO × 3 年折 × 2 种子, 400 树 78 输入 **60 锚 embargo**, **738,595 / 2,712,889 对**从两列皆零变为真实值(与我方 2024+2025+2026 的 764,887 合到 3.4%)。结果: REPAIRED − OLD 六行在 −0.001324 到 +0.000553 之间, **五行 CI 跨零**; **ZERO 臂只比 OLD 低约 0.002 IC**。逐字:「**修复前后没有稳定、明显的排序增益, 也没有预测能力崩塌的证据。**」
**三条限制使它不能关闭 FEA-01**: ① 用的是 **King 结构**(400 树 78 特征), 不是 F10, 而我方 FEA-01 是关于 F10 输入与所有用于评判候选的 F10 OOF; ② 用的是 **DLW 含 E 的特征 + E+4h 目标**, 他们自己说「**不是原 exporter 时钟/标签的原样重放**」; ③ 测的是**秩 IC 不是书层净额** —— 我方「排序≠净额」五例与 `score_level_magnitude_is_not_book_level` 对它同样适用。
**lead 裁定**: **FEA-01 的前视半边保持 P1, 对 F10 与书层净额保持 OPEN; 但十月重训不得再为「回收资金费 alpha」编列预算** —— 在 King 秩层面那个量已被独立测为约零。(与 §21.3-4 一致, 此处加上两侧格数复现作为第二根支柱。)

### 24.2 ★ X-COST 的 5→2 bps 假设已被实测兑现(FXR-DOC-2 的该条 caveat 可销)
他们在 **9,419 条按 `(symbol, trade_id)` 去重**(与 X-COST 同键)的成交上逐类测得: **maker 2.000000 / 1.999999 / 2.000000 bps · taker 4.999999 / 5.000000 / 5.000000 bps**(09-08/09/10)。⇒ FXR-DOC-2 里「5.14U/日只在 5→2 bps 假设下成立」的该假设**在该人口上精确成立**; 收据 `OBSERVED_FEES.json` sha `9ce2d8f2…`。
**通读线的算术(明确标注为其本人所做, 非任一方主张)**: 把他们的逐类费率配我方 X-COST 的**名义加权**份额 ⇒ S1a(maker 93.1%)混合纯费 **2.207 bps**, S3(maker 73.9%)**2.783 bps** ⇒ **−19.22 pp 的 maker 份额位移值约 +0.58 bps 纯费**; 3.52 bps 里纯费占 2.2–2.8, **余 ~0.7–1.3 bps 给滑点/拒单/机会成本**。**三条健康警告随数字同报**: 他们三天窗只部分重叠 S3 · **09-09 是我方事故日**(他们标「异常平仓」, 按计数 81% taker; 我方 E-0909-G 的逐名门平仓正是该日)· 把他们的逐类费率配我方的名义份额**假定费率在两窗间稳定**。
**三种 maker 份额口径从此不得互引**(进 FX-EXEC2 的 D4 清单): X-COST = fill 级 `venue_maker_flag` 的 M/(M+T), 按名义合并(93.1%→73.9%) · FX-EXEC2 = `topup_taker` 订单行的 |成交名义| 占比, 逐锚(taker 中位 5.010%) · 他们 = **按成交笔数**分类(09-08/09/10 maker 64.9% / 19.0% / 73.1%)。
**未被任何一方解释的仍然是: 首拒 −5022 由 14.3% 升到 23.0%。**

### 24.3 ★ 待查的决定性一条: 他们的现金宇宙屏不屏蔽非 crypto
通读线在其读过的全部文档里**未找到任何一处说明他们的现金宇宙对非 crypto 做掩码**; 他们全程在 829 轴上训练**并记账**。而**我方 A0 是掩到 373 个 crypto 名的**(PROD-10, 与 400 重叠 332)。
⇒ **若他们不掩码, 则 UNI-01 就在那 608 天头条里面**, 规模约我方测得的 **7.3%(2026 训练成员对)**, 且**两对 3× 反向杠杆按构造占据截面秩两端** ⇒ **Sharpe 2.523 部分由交易代币化股票永续产生**。这不是风格批评, 是对**估计量本身**的质疑。已派查, 判据: 在其逐名产物里直接找 `SOXLUSDT` / `SOXSUSDT` / `TQQQUSDT` / `SQQQUSDT` / `QQQUSDT` / `SPYUSDT`。**「找不到 ≠ 不在」** —— 只能给出「文档缺席」时必须照实说是文档的缺席而非事实的否定。
**同时这条把我方 UNI-01 也说得更准了**: **我们的训练包含这些名, 我们的评估掩掉它们** ⇒ **模型被训练在书从不交易的名上**, 这是宇宙层的训练/服务背离, 比「训练宇宙里有脏东西」更具体。

### 24.4 其余逐项判定(采纳)
- **TIM-01 两侧皆未测**; 他们把「建模观察时钟与真实数据到达差异」列为范围外未决。**归我们独有。**
- **PROD-11 收敛而非冲突**: 他们的回放在 829 上训练 —— 正是 §19.3 所规定的; 残余不对称(研究在 829 上打分、实盘服务 450)他们自己也登记了。
- **TRD-01 与他们的注册表缺失是同一批名字上的两个不同失效面**: 我们是面板侧(冻结行通过每一条资格规则), 他们是注册表侧(日历从未记录关闭 ⇒ **现金书持着真实仓位并吃真实资金费**)。**EOS 是已定价的实例**: 我们的面板会让它看起来静止, 他们的书持 **−118.997 到 −253.101 张 / 3,273 行 / 24 个网格**, 吃 **1,402 次未定价资金费**(2025-05-21 16:00:00.004 → 2026-08-31 16:00:00.001)。**修面板修不掉他们那个。** 其普查: **629 个持仓名里 570 个未注册**; 生命周期已知态 **0/1506 → 48/1506, 仍 1458 未知**, 并**为此把正式 40 折暂停**。
- **FND-02 的前提被从第二个方向佐证**(同一个 `fund_aug.json.gz`, 同样的两字段形状), 且他们独立采用了我方 FND-02 指出我们违反的那条纪律:「**不把时间间距当声明周期**」; 与我方 P9 表「**LIKELY 是猜测, 永不是更正**」同规。**缺陷本身两侧都未修。**
- **P9 表**: 他们对 2,063 个此前未列的币月做了更大规模的独立核验(2,050 个相等、**0 处修改**、13 个仍 UNKNOWN 且拒绝置零), 与我方 August 拉取 **152/680 = 22% 的 404 率**所描绘的存档可得性图景一致。其硬规矩:「**不得把新 public 月档用于历史训练可见性认证。**」
- **F10 numpy 导出链**: 端到端跑通(294 件逐件下载 + fsync + sha 核, exit 0), **但跨 runtime 有 106 行秩变化**(286 万预测, 最大绝对差 1.3411e-7)⇒ **书是秩驱动的, 要紧的是那 106 行秩**。他们以「组合用 NumPy 服务侧结果」解决而**不宣称跨 runtime 逐位一致** —— 处理正确。
- **生产者 col-80/81 迁移在全人口上是红的**: 四臂**全部拒绝发布**, 因为六个名(DOLO / HAEDAL / ICP / RIF / TLM / TUSDT)缺 **2,235** 条必需历史标签; **519 名子集**四臂全过。他们**没有把六名删掉、没有用零补标签、没有缩短控制窗**, 并明写「**519 名结果是机制/回归正控, 不能用作线上整书状态**」。其 D17 的 **533 格**与我方 P9 表「逐一确认 533 个旧 D17 行」**是同一个 533**。
- **PROD-28 两侧都没有重启后的进程指纹**; 他们最强的身份证据是 git HEAD + 十个文件字节相符(09-15 取, **在我们 09-14 重启之后**), 并四次明写「**Git HEAD 不能证明运行进程加载身份**」。另两条身份事实: **部署 bundle 的 MANIFEST 里没有 F10 条目**(他们称「已确认的身份追踪缺口」); **两个冻结 `pilot_metrics.py` 身份在流通**(`cd508c3f…` vs `5ac7b16d…`, 分叉源自我方 `ec88424` 的 LED-01 重封存)⇒ **对其一为绿的组件电池不可迁移到携带另一个的树上**。
- **无任何一条与我方已登记发现构成「两边都测了同一个量而结论相反」的矛盾。** 三处张力(回放残差的符号与量级 · 同期实盘损益的两个数 · 581 vs 618 次 King 回退)均为**不同仪器测不同量**, 且他们各自标了限制。

## §25 ★★★ 重叠期实测 + A0 被高估 + 一条 25 天前就写下来的缺陷(2026-09-16 07:2xZ, lead)

### 25.1 ★ lead 更正: 「回放复现了实盘八月的坏」这句是错的
我在 §21.3-2 与两次给用户的汇报里写过「回放没有与实盘矛盾, 它复现了实盘的坏」。**VER-OVERLAP 实测把它推翻了**(装置先于运行提交 2c34b325 / 8f5ec821 / c6c15982, 收据 71354275; 正控逐位复现该文档四项总量 +363,572.31 / −114,015.21 / −24,738.04 / −26.09 / 净 +224,792.97474255):
| 段 | 回放净收益 |
|---|---:|
| 2026-08 整月 | **−5.9586%**(价格 −0.16 · **资金费 −5.21** · 费 −0.59 ⇒ **该月 87% 的亏损是资金费不是价格**) |
| 2026-08-01..08-25(**实盘开跑之前**) | **−8.6444%** |
| 2026-08-26..08-31(**实盘实际交易的 6 天**) | **+2.9399%** |
⇒ **回放亏的那个月不是实盘交易的那个月。** 用「回放八月 −5.96%」去解释「实盘 08-26 以来差」是**期间错配**。**在回放里, 实盘真正交易的那 6 天是盈利的。** 原句作废, 以本条为准。

### 25.2 第三个混淆项: 两侧不共享模型
回放文档 §4 自己写明在役磁盘件 King `8d79186b…` / F10 `351ae26b…` **「不是本次收益的模型」** —— 回放用的是**在修复数据上重训**的 King/F10。加上它**关闭了全账户停机**、按**模拟成交名义**扣 3.52 bps。⇒ **混淆项有三个而非两个: (A) 实现 · (B) 期间 · (C) 模型身份。** 本窗无法移除 (C) ⇒ **任何「差值 = 实现问题的大小」的读法在移除 (C) 之前都不成立。**

### 25.3 ★ 净额不可判, 资金费可判 —— 而资金费正是两本书真正不同的地方
**净额**: 逐日差(实盘−回放)均值 全 6 天 **−0.481 pp/日, CI95 [−1.437, +0.475]**; 干净 3 天 **−0.231, [−0.741, +0.279]**; **换一个日界约定, 符号翻正(+0.247, [−1.198, +1.692])**。**被争论的效应本身约 +0.19 pp/日, 而半宽是它的 2.7–5.0 倍** ⇒ **此处小于约 1 pp/日的东西一概测不出来**; 且 6 个日差里有 3 天被实盘专有事件污染, **其中包括最大的两个**。
**资金费(可判)**: 先对账两台仪器再下结论 —— `funding.jsonl` 相对场所收入账本**逐日少报 16–26%**(`skipped_no_position=0` ⇒ 是**逐行重建误差**: `funding_paid = 陈旧回读仓位 × 费率`, 仓位读龄最高约 73 分钟), 故取**场所收入账本为准**, 并把实盘窗保持在 [00:00Z, 当日最后一行 daily_nav ~20:45Z] = **一个 UTC 日的 86%**(对回放整日)⇒ **实盘侧按构造被低估**。
按各自 gross/NAV 的单位计, 干净日: 08-28 **1.57×** · 08-30 **1.68×** · 08-31 **1.66×**; 差 **−0.0499 pp/日/单位 gross, CI95 [−0.0840, −0.0158] —— 排除 0**(全 6 天 −0.0387 [−0.0607, −0.0167] 亦排除 0)。**在部署的 2.0× gross 下 ≈ −0.0998 pp/日 NAV ≈ −36 pp/年。**
**资金费之所以在 6 天里可判, 正因为它逐日近乎确定而价格是噪声。** 与 T5 的「部署 carry = 回放 carry 的 2.19 倍」同号同量级, **但那是另一个回放(旧模型)在另一个窗上** ⇒ **这是独立的第二次测量, 不是复述。**
**费用方向相反**: 实盘佣金 **1.966 bps**(去重成交, 100% BNB, 按同锚 BNBUSDT 中价换算)对回放按构造的 **3.520** ⇒ **回放在费用侧是保守的一方(1.79×)**, 费用解释不了回放跑赢。

### 25.4 两条实盘记账缺陷(顺带发现, 与比较无关)
1. **`funding.jsonl` 相对场所收入账本逐日少报 16–26%**(比值 0.744/0.879/0.814/0.867/0.847/0.817; 6 天缺口 +41.17 USDT 对已收取的 −252.80)。成因**未确立**, 只知是「按陈旧仓位读数逐行重建」。⇒ **凡过去对 `funding.jsonl` 求和得出的结论, 都低估了资金费成本。** 登记 **LED-10, P1**。
2. `daily_nav.realised_by_type["COMMISSION"]` **既不是 USDT 也不是完整的 BNB 总额**: 该字段 ÷ 同窗去重成交的 BNB 原生和, 六天漂移 **0.950 / 0.919 / 0.627 / 0.494 / 0.473 / 0.495**。量级 ≤5.3 USDT/日(≤0.026 pp NAV), 不动结论, 但**是错的**。登记 **LED-11, P2**。
3. 附带: 成交去重把 **20,069 行折成 6,781**(**66.2% 是重复**), 每个 `(symbol, trade_id)` 键都被重复(08-26 有 913/943 个键重复度为 3)。重复来自 markout 回填重写, **经济字段逐份相同**, 故去重安全且必须 —— **未去重的名义是真值的 2.96 倍**。

### 25.5 ★ A0 被死合约「抬高」了 —— 修好的书反而赚得少
FX-DATA 的 SPEC §7 A0 效应测量(装置未修改, 跑在 `w10_sleeve.py` sha `b88e35a4` 上; 估计量未重实现, 用 `ast.get_source_segment` 抽 `r18_judge.py` 的节点并执行其源文本; **正控双种子逐位相等**且复现 r18 的 W_ALPHA `g` = 0.6341957 / Sharpe 1.2912):
| 臂 | 改什么 | Δg W_ALPHA s42 / s2027 | 标签 |
|---|---|---|---|
| **TB** | 仅资金费秩基 | −0.0105 / +0.0107 | **EQUIVALENT** |
| TU | 宇宙 ∧ tradable | −0.0599 / −0.0459 | INCONCLUSIVE |
| **TF** | 两者(修好的书) | **−0.0603 / −0.0519** | **INCONCLUSIVE** |
| TF4 | 两者, W=4h | −0.0948 / −0.0862 | SENSITIVITY_ONLY(**双种子 CI 均排除 0**) |
- **TB 回答了 §TRD-02 拒绝回答的问题**: 原始 z 层 |Δz| 均值 0.027 在书层**几乎被完全吸收**(`legs()` 去均值 + 按 Σ|z| 归一), Δg 符号甚至在两种子间翻转。**若当初把原始 z 数字报成效应, 会错一个数量级。**
- **符号本身是发现**: **去掉死合约使书变差** ⇒ 它们原本在贡献。TF 分解(s42, W_ALPHA): **Δ价格 −0.1028 · Δcarry −0.0274 · Δ成本 −0.0151 · 换手 −8.6%** ⇒ 它们在贡献 **+0.103 bps 价格 P&L** 与 **+0.027 bps carry**; **价格那半几乎是 carry 的四倍**, 来自冻结收盘与下架前异动(ALPACAUSDT 那一类)。
- **几乎全在 2026**: TF Δg 逐年 −0.022 / −0.003 / −0.001 / −0.024 / **−0.3215** —— 与 §TRD-02 的「2026 污染几乎全是 NODATA 类(两个审计旗标都看不见)」对上。
- **按 SPEC §7 冻结在先的读法规则: 非 EQUIVALENT ⇒ A0 参照登记给 lead 重新定基, FX-DATA 不编辑任何 RESULT。** ⇒ **TRD-03 不关闭**; **A0 登记重新定基**。实务含义: **纲领内每一条引用 A0 的读数, 其基准高约 0.06 bps/锚/单位 gross(A0 自身 W_ALPHA 净额 0.634 的 ~9.5%), 而 2026 高约 0.32。**
- **两条限制上记录**: 修好的书**并不消除暴露**(`w10_sleeve` 不强制退出离开 `m` 的名, 其 `sm` 按 EMA 衰减)—— TF 书仍有 **0.70 / 2.09 / 5.02 / 10.83 / 9.37 %** 的 gross 落在固定宇宙掩码之外; 且工作者主动指出**自己收据里那个字段名把它说过头了**(`absW_on_non_tradable_outside_member_set` 实际计的是「在掩码之外**或**不可交易」)。

### 25.6 ★★ EXE-05 与 NEW-03 都不是本周的发现 —— 25 天前就写下来了, 死在「复合行」里
`docs/REDTEAM_wide_live_prelaunch_2026-08-22.md` 行 **R16 ③** 逐字: 「RUNBOOK §3『gross_mult 变化由 ±10% 死区自然重定尺寸』—— **死区在生产中从不生效**: `run_anchor.py:277 gross_usdt=0.0` ⇒ 每锚新进程 `prev=0` ⇒ 每锚重算(在役 anchors 行 target_gross 30,715→30,526 逐锚变化即证)」。**缺陷、机制、行号、实盘证据, 全都在, 日期 2026-08-22。补救栏写「逐条改句」, 状态栏 **否**。** 同一行的 **R16 ④** 正是今早作为 NEW-03 修掉的 `gate_coverage` 重复键。
**机制比这两项本身更值钱(FX-EXEC 的判断, 我采纳)**: **R16 把六个互不相关的缺陷捆在一个标题「声明≠观测」下, 并作为一整行被评为 P3** ⇒ **严重度由行决定而不是由其最差成员决定**, 而其中一个成员是**实盘定量行为**不是文档不符; 补救栏「改句」把一个行为缺陷框成了文案卫生。**一个复合行是发现去被低估的地方。**
⇒ **新规矩(全体)**: **登记行必须一项一行**; 若必须并列, **严重度取其最差成员**, 且**每个成员各有 owner 与复访**。AUD-KB 把该规则写进 KB, 并**扫查其余复合行**。
**换手后果实测(FX-EXEC)**: 292 对连续 LIVE 定量中 **278 对(95.2%)落在 10% 带内**; 被抑制的重定规模名义占 gross **0.3721% 未加权 / 0.4493% 按 gross 加权**(89,115 USDT 对 19,832,437 USDT gross)⇒ 占已测每锚换手(2.0–5.5%)的 **18.6%–6.8%**(未加权)/ **22.5%–8.2%**(加权), **且是下界**(只算重定规模腿, 不含它在下游引发的逐名重挂)。
**两条比我的简报更锋利的读数**: ① **`leverage_drift_frac` 在 563 个锚里非空 0 次** —— 漂移**从未被计算过**, 遑论比较, 这比 gross 恒等式更干净, 因为它不需要算术; ② **`resized: False` 在记录里从不表示死区生效** —— 它出现 270 次, **270 次全是 `blind` 分支**(nav 不可读, 同字段不同理由), 非 blind 行是 **293/293 resized True**。**按 `resized` 去 grep 审计的人会得出「死区在 48% 的锚上生效」的结论。**
**影响面(FX-EXEC 出表)**: `RUNBOOK_wide_live_2026-08-22.md:105` **必须重判**(它在指导操作员依赖一个从不发生的行为); 三份文档的「软死区」是**另一个对象**(训练侧无交易带)不受影响; 三条记忆条目**零提及**不受影响; `DESIGN_wide_replay_P3_2026-08-16.md:113` 说「死区语义一项即 ±1.0 Sharpe」—— **若任何回放变体建模了生产从不施加的杠杆死区, 那是回放-实盘背离**, 归 P2 链(lead)。
