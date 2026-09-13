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
