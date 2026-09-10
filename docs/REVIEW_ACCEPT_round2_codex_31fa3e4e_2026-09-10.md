# 独立研究员第二轮复审(31fa3e4e)· 辩证处置

> **创建:** 2026-09-10 00:4xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 处置已定, 第三轮修复待做(分支) | **作废条件:** 第三轮修复提交后本文的「待修」栏失效, 以第三轮 HANDOFF 为准
> **复审件:** 研究员 worktree `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_round2_review_2026-09-10/`(HANDOFF.md / RESULT.md / account · executor · features · pipeline 四分册; 提交 31fa3e4e, 未推送)。**被审对象:** 研究分支 5f9b8f4b→fb98a8f9, 实盘分支 e1c4c87, 运行树 d040c74。
> **研究员总判:** 部分修复成立; 实盘整包、账本补件、自动放行管线不放行。**我方总判: 同意。** 下表逐项给出接受/收窄/不接受与证据; 凡我方本地能复核的都复核了。

---

## §0 一句话

研究员抓到的最重要的东西是**我在两处把「表面完整」当成了「正确」**: 52 行补件的费用按未折叠的 fills 汇总而翻倍(1.00970 vs 0.50724, 本地复核 VERIFIED); 门与判官只核了「有没有 PASS」而没有核「是谁的 PASS、依赖全不全」。执行器方面, 我把「底层不盲重发」当成了「整个交易意图幂等」, 研究员用真实函数造出了三组反例。这些都成立。研究结论方面, G1 只能说 (a)/(b) 数值门过, (c) 轴条款没过且干预不是纯时钟单变量; G2 FAIL 维持; 我用边际 SE≈0.6 论证「反号是噪声」是错的, 撤回。

**没有任何一项让我们把「策略 alpha」或「已发表回测数字」判坏**: 研究员从原件复算 28 书 + 2 参照 6,042 项差 0, 72 个 CI 全复现, 18 格全 (C)。工程缺陷与统计结论分开, 这一点双方一致。

---

## §1 账本与收入(account 分册)

| # | 研究员发现 | 我方复核 | 判定 | 待修(第三轮) |
|---|---|---|---|---|
| A1 | 52 行 orders 补件 `fee_paid` Σ 1.00970 vs 去重 0.50724, 52/52 行偏高; note 不是程序隔离 | **VERIFIED**: 干跑文件 52 行 Σ fee 1.00970085, n_fills_joined 134 = 67×2; 根因 = `build_rows` 直接遍历 `PL.read_day` 原始 fills(含 markout supersede 行)按 (symbol, attempt) 求和 | **接受, 真实缺陷**。我 23:5xZ 的「更正 3」只修了读法, 没回头查构造器 —— 同一错误在另一层再犯 | `build_rows` 先按 (symbol, trade_id) 折叠取最新行再汇总; 加结构化列 `reconstructed_from_venue: true`; 查执行质量/处置尺子消费者并按列排除; 副本上金额/费用/数量/幂等/看门狗整链验收后才谈写回 |
| A2 | 时间游标分页: 同一毫秒 >1000 行只取 1000 且 `truncated=false`; 我的 `_TwinIncome(page=2)` 夹具 `_request` 未读 `self.page`, 「小页重叠」用例只调用 1 次 | **VERIFIED**(代码读): 满页后 `_cursor` 停在同 ms, 再请求得同批 → `fresh==0` break, `truncated` 只看 40 页; 夹具 L71 用 `params["limit"]` | **接受为逻辑缺陷(P2)**: 合成可达, 实盘可达性极低(结算扇出 ≤ 持仓名数 ≈250 ≪ 1000), 研究员也未称已发生。但 `truncated=false` 在该分支是假话 | 满页且 `fresh==0` ⇒ `truncated=True`(「不能证明排尽」); 夹具改为真分页; 不用延长页数假装解决 |
| A3 | (i) 不同 asset 直接相加非 USDT 换算; (ii) docstring `[start,end)` 但 endTime 含边界; (iii) 「只少记亏损」只能描述本窗 | (i)(ii) 既存边界, 非 e1c4 引入; 本账户手续费资产是否单一 **UNRESOLVED**(未取 symbolConfig/账户设置) | **接受为边界说明**; 措辞收窄 | docstring 改闭区间并在 reprice/相邻窗口用 `end−1`; by_type 按 asset 分桶报告(不换算); 措辞改「本窗少记亏损, 旧键吞掉的 REALIZED_PNL 也可为正」 |
| A4 | 触发机制: `unauth_frac=0.0109` 未过 **5% 整书线**(`PB_UNAUTH_PORTFOLIO_FRAC=0.05`), 实际由**逐名门**(该名 ≥ 自身 min_notional)触发; 「1.09% vs 0.05 line」把百分数与比例并排; `conditions_partial=[cond2, cond4]` ⇒ 「无盲区」只能指 blind=[] | **VERIFIED**(`position_break.py` L150/L439/L522: 整书 5% OR 任一名 ≥ 自身 min_notional) | **接受**。我的 journal/HANDOFF 写法暗示越过整书线, 错 | journal 追加更正; HANDOFF §2-7 改写为「§4-5e 由逐名未授权门触发(≥50 名各自 ≥ min_notional), 整书 1.09% 未过 5% 线」 |
| A5 | 平仓 243 orders / 0 fills / 243 null fee 是真实、已重现、未在分支闭合的家族 | 同意(我方 17:4xZ 已登记, 未修) | **接受为独立 P1 待办** | protective_flatten 路径写 fills 行(或平仓后立即 userTrades 回填); 与 12Z 补件同一副本验收 |
| A6 | 20Z 不补也 CLEAN 只说明恢复状态, 历史仍 9 异常; 恢复与历史修复分开 | 同意, 我 21:4xZ 已如此表述(52 行降为账本真值项) | **接受** | 无新增 |

## §2 执行器(executor 分册, 被审 e1c4c87)

| # | 研究员发现 | 我方复核 | 判定 | 待修 |
|---|---|---|---|---|
| P1-1 | -2013×2 ⇒ `resolved="absent", ambiguous=False` ⇒ 上层(重挂保留 from_reject → 补单)可对同一意图再发; 迟到成交 + 补单 = 双倍; 下一锚 openOrders 看不见已终态单 | 代码读一致(`_settle_order_post` absent 分支; 补单/重挂对 absent 不设防)。我 HANDOFF A1 已把 1.0s 间隔标 UNRESOLVED | **接受**。我的设计取舍是「absent 当未发, 免得一条腿整锚被锁」; 研究员反例说明代价不对称: 不重发最多少填一锚(下锚重定目标), 重发则是无上界的重复暴露 | absent ⇒ 仍 ambiguous(记 `resolved="absent"` 作证据), 本锚不再对该意图发任何单, 腿入 in-flight 列表; 下锚 sweep + 对账收口; 可恢复的未决列表落盘 |
| P1-2 | 重挂(L966)、补单(L1459)、各 chunk 共用 `A…-SYM-2`; `_resolve_ambiguous_order` 见 orderId 即认存在, 可把旧终态单认成新请求; 归属表以后 IOC 覆盖 maker | **VERIFIED**(L966/L1459 同一格式; chunk 复用 p["client_id"]) | **接受, 旧设计缺陷被新查询入口放大** | 每次真实场所请求唯一后缀(`-2`, `-2c2`, `-3r1`…), 查询只查自身身份; 归属表同 id 不同腿拒绝覆盖; 排查所有解析后缀的读者(重建工具 `rsplit("-",1)`、处置尺子、测试) |
| P1-3 | (i) chunk1 UNKNOWN 后 chunk2 VenueError 分支写 filled=0 / residual None; (ii) 已知子集手续费回填 `apply_commission_to_rows` 把整腿改成 known5, 真实 8, unknown_residual 无消费者; unattributed 只计数不报警 | 研究员用真实函数链 `submitted_order_legs → attribute_trades → apply_commission_to_rows → book_after_anchor` 复现(CONSUMER_RESULT.json); 我方第三轮先复跑其夹具 | **接受**。我修了生产端五格, 没修消费者合同 | except 分支保留 `_unknown`; 回填只抬已知下界, 任一未决请求存在时腿不得整体归 known; `_exec_qty` 把 `filled_unknown_residual` 非空视为 unquantifiable; unattributed >0 报警 |
| P1-4 | HTTP 408 / -1007 / -1006 仍走拒单 | **VERIFIED**(`_execution_unknown` 只看 ≥500 或 200 无 code) | **接受**(小) | 408 与 {-1007, -1006} 进执行未知; -1008 等明确拒绝仍拒 |
| cap | 正常有限 cap 只缩不放成立; P2: 第二名解析失败时第一名已改、日志却说未改(非原子); `nan` 字串穿过筛选; reduce_to_cap 未入 reduce_only_syms | 同意(合成) | **条件接受 → 修 P2** | 先验证 cap/target/held/margin 有限性, 临时映射完整计算后原子应用, 出错不改 + HIGH; reduce_to_cap 名入 reduce_only; 「715/897」标 INFERRED(源自代码注释, 未取 symbolConfig 原件) |

**整包判定**: 同意 e1c4c87 不放行。当前实盘跑的是 d040c74(16Z/00Z 首相位零传输异常), 分支加固待第三轮。

## §3 管线与判官(pipeline 分册)

| # | 研究员发现 | 我方复核 | 判定 | 待修 |
|---|---|---|---|---|
| R1 | `require` 只核 PASS 与调用者给的 inputs; gate 名、self_sha 不核; 可零输入放行; `chain_v4s_gpu.sh` 只传 4 依赖漏 hole_cells 且传 CLIP 目标而训练读 RAW; `chain_v4_data.sh` 两处 cp 不查退出 | **VERIFIED**(v4_gate_common L52-72; data.sh L7) | **接受**。「门=程序条件」我只做到一半 | require(expected_gate, expected_source_sha, 完整依赖清单来自声明文件); 各链传全依赖(含 hole_cells、实际 RAW 目标、fea82/legs/训练器 sha); cp 加 `|| die` |
| R2 | 判官: 任一 A0p 参照即可(L57 `any`); 3168 是计数非集合(可重复/缺锚); NaN 穿阈值; `JUDGE_ALLOW_PARTIAL=1` 下 60 锚可打 PROMOTE 且 JSON 无 exploratory 标记; 不消费 G2 资格 | **VERIFIED**(L57/L70-73) | **接受** | 双种子参照必需; 与冻结时间网格逐元素相等; 全有限性 schema 门; partial ⇒ 禁 PROMOTE + JSON `exploratory:true`; 判官读导出门收据(env 指定), 缺/FAIL ⇒ 判决上限「信息态」; L85 「126 more」改 121 |
| R3 | 生成器未发出 `BUNDLE_GUARD_LO/HI` ⇒ 再生 exporter = 23b1a5c7 ≠ 归档 b5b6cd19 ⇒ 冻结归档跑 21 套件 **20/21**; pod2 现用 23b1 故旧「ALL PASS 21」只对旧 exporter 成立 | **VERIFIED**(`make_v4_scripts.py` 0 处 BUNDLE_GUARD; exporter L162 有) | **接受**。我把 pod2 的绿灯当成了归档的绿灯 | 生成器发出 guard env 行; 再生→同步 pod2→从冻结归档重跑 21 项; 用逐文件清单自动产生计数与映射 |
| R4 | 「75/50/0/6」与原件不符: 目录 78 脚本, 清单 75 项 = 58 MATCH + 2 POD2_DIFFERS + 14 r1 + 1 r0(实际快照 r0 1 / r1 13 / r2 1); 60 非快照 pod 实读 59 等 + 1 不等(exporter, 却标 MATCH); 两处 POD2_DIFFERS 已等但字段未更新; 清单漏 3 文件; `JUDGE_v4_g3_s2027.json` 应映射到 `judge_v4.r2_17b562fd.py` | 我读了收据顶层过时计数器(n_match_pod2 50 等)就写进更正 —— **又一次「读了数字没读原件」** | **接受, 我的更正 5 撤回** | 重生成清单(78 文件, 逐文件状态, 快照按真实前缀分类); 修 receipt_to_source; 更新 pod2_sha 字段 |
| R5 | 72 个 CI 非 56(18 格 × 2 种子 × 主/扩窗); 全部复现 | 同意, 56 是 A1e 加入前计数 | **接受(措辞)** | HANDOFF/RESULT 改 72 |
| R6 | 已通过项: G2 闭包门 rc3、逐 PID 等待、显式 FAIL/marker 阻断、缺臂/短窗/A0p 偏差拒跑、3168+A0p 平价 | — | **接受(有利)** | 无 |

## §4 训练—生产一致性(features 分册)

| # | 研究员发现 | 我方复核 | 判定 | 待修 |
|---|---|---|---|---|
| F1 | G1 (a)/(b) 六锚数值门过(f16 不等格 1/13/12/3/6/15, f64 参照 0, 阳性对照 ≥4,731); 前三锚与其 live 数组 uint32 全同 | 与我方收据一致 | **接受(有利)** | — |
| F2 | G1 (c) 轴条款不满足: 新增 2022-01-07 16Z/20Z 两早锚(非「尾差 ≤1」); 门未把轴纳入 PASS; `if in_new` 跳过时 ok 保持 True(静态缺陷) | **VERIFIED**(parity L86-107 只 ok_a/ok_b) | **接受**。「G1 PASS」收窄为「(a)/(b) 过, (c) 未过」 | PREREG AMENDMENT 4: 轴规则明写(允许并列出由成员 clamp 修复产生的早锚); 门把轴与「六锚齐」折进 PASS |
| F3 | 新增早锚来自**成员统计左界 clamp**(`LO7=max(HI−2016,0)`), 四种 clock×label 组合都得同一 136 名; 未 clamp 时 r2 前缀差 ≤0 ⇒ v7=0 不可能过门; 共同轴另有 206 锚成员变化、qvk 2,029,690 格变 ⇒ 干预不是纯时钟单变量 | 逐行 diff 与代数论证成立(我方 E-0909-A 修的是 covr/VAL/vol 的 clamp, 成员 qv/m7/r2 仍用 E−2016 未 clamp; E 版一并改了) | **接受**。干预重命名为「时钟修正 + 成员窗 clamp」 | 同 AMENDMENT 4; 若要纯时钟臂需另建(本轮不训) |
| F4 | AMENDMENT 1 措辞: 「两个实现都在 float32 上排序」不普遍成立(生产 mean = f32 和 / int64 计数 → f64); (a2) 证明的是离线高精度参照与新档一致 | 同意 | **接受(收窄)** | AMD1 文字修订 |
| F5 | G4: 5/6 锚分数不变, 2024-11-15 08Z BADGERUSDT 一处 −0.00158, S=0.9999774 非精确 1; 「无影响」过度; 不得补成部署门 | 与收据一致(我早前 grep 到 0.99998) | **接受(收窄)** | 文字: 「六锚排序不变, 一锚一名分数微变; 只报不判」 |
| F6 | AMD2 六格全复现, G2 按重定基带仍 FAIL(差 0.0067); AMD2 保留后验性质 | 一致 | **接受** | — |
| F7 | R3−R5 非「纯预测效应」(成员/qvk/NaN 支持不同); R5−R2 非「机械换价」(y4 进腿权重与仓位路径); 反号 ≠ 噪声; 我的 √(2190/5839)≈0.6 边际 SE 不能替代配对方差(配对 SD 0.03–0.23) | 统计论证成立: 差的方差要减 2Cov | **接受, 撤回三句**: 「标签窗非因」「预测效应 ±0.07 反号 = 守卫噪声」「带宽 0.3 vs SE 0.6 故门不判别」。替换为: 7 日块配对 CI 全含 0(R3−R5 −0.068 [−0.418, +0.298]; R6−R2 +0.069 [−0.373, +0.526]; R5−R2 +0.023 [−0.032, +0.084]), 读法 = 在该样本与区间**未检出差异**; 「守卫带作为判别门的分辩力」改登记为待预注册问题 | AMD3 文字修订; guard_decompose 报告加配对区间(采其方法, 引其收据) |
| F8 | 新标签 [E+1,E+48] 与 DL/生产同窗成立, 但仍是 clip 过的 f16 ret5 算术和, 非 close/close−1; future-y-finite 成员筛选遗留 | 已知(E-0908-B 家族) | **接受(说明)** | 文档明写 |

## §5 我方承认的新错误(本轮新增, 供错题集)

1. **补件构造器未折叠 fills(A1)**: 「更正 3」修读法时没有回头检查用同一数据源的构造器 —— 修补的第二层再犯第一层的错。规则: 修一个读法, 必须 grep 全部使用同一源的消费者。
2. **门只核「PASS」不核身份与依赖(R1/R2)**: 把「有收据」当成「收据是对的」。
3. **把 pod2 绿灯写成归档绿灯(R3)**: 两处源码不同版本, 我只跑了一处。
4. **读收据顶层计数器不读逐项(R4)**: 与 E-0826-B「sha 推断代替复跑」同型。
5. **边际 SE 论证配对差(F7)**: 统计基本错误, 撤回。
6. **「G1 PASS」笼统宣称(F2/F3)**: 门代码实际只判 (a)/(b), 我把 PREREG 三条款都写成过了。

## §6 第三轮顺序(全部在两条既有分支, 不新开分支; 合并 ≠ 部署)

1. **实盘分支** `review/b0a573a1-executor`: P1-4(小)→ P1-1 absent 语义 → P1-2 请求身份 → P1-3 消费者合同 → cap P2 → A2 truncated 旗标 + 夹具 → A3 文字/闭区间。每项配研究员夹具复跑(`executor/fault_cases.py`、`consumer_followup.py`、`account/audit_income.py` 复制到新目录跑)+ 我方套件; 电池全绿; safe_commit。
2. **研究工具(主线)**: `reconstruct_orders_12Z.py` 折叠 + 结构化列 + 消费者排除; 平仓 fills 回填工具; 两者只干跑, 写回等字。
3. **研究分支** `review/b0a573a1-pipeline`: require 身份/依赖绑定 → 链传全依赖 + cp 检查 → 判官五门 → 生成器 guard 行 → 再生/同步/从归档跑 21 → 清单重生成与映射 → PREREG AMENDMENT 4 + AMD1/AMD3 文字修订 → HANDOFF 数字(72 CI, 121, 5% 线)。
4. 完成后出第三轮 HANDOFF, 研究员复核; 通过后分别合并; 部署另裁。

**不在本轮**: 换装(v4e 无资格不变)、重训、N+6。
