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
