# PREREG · E-0910-A 场所量化规则锁(-4400)熔断 + 复场重建的两个候选

> **创建:** 2026-09-10 02:1xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 候选 1 已在实盘复审分支落码(未部署, 等复核 + 用户字); 候选 2 只登记 | **作废条件:** 场所改变 -4400 语义, 或用户裁定不采纳

## 0. 事实(VERIFIED, 2026-09-10 00Z 复场锚)
- 补单相 71 张 IOC 全部 -4400「Futures Trading Quantitative Rules violated, only reduceOnly order is allowed, please try again later」(Σ|意图| 72,813U); 首挂相 191 张 GTX 未受影响(锁在两相之间落下)。
- `GET /fapi/v1/apiTradingStatus`: ACCOUNT 级指标 TMV isLocked=true, value 10, triggerValue 59, plannedRecoverTime 02:34:10Z; 无单名锁。
- 结果: realized_gross 154,910 / 232,259(67%), net/gross +5.23%(卖侧 59 单未成交), 方向暴露 ≈8.1k ≈ 7% NAV 至 04Z。
- 机制(INFERRED): 平仓(243 市价)→ 从零重建(191 GTX + 72 -5022 拒 + 36 复挂 + 33 撤)的密集下单/撤单形态把账户级违规计数推过线。

## 1. 候选 1 · 执行器熔断(已落码, 分支 `review/b0a573a1-executor`)
**规则(冻结)**: 在同一提交循环(首挂相或补单相)内, 第一张被 -4400 拒绝的单照旧记 `venue_reject`(首挂)/ `abandoned_max_attempts`(补单); 其后所有**开仓**单不再发送, 记新终态 **`skipped_venue_lock`**(GAP, 不可恢复于本锚, 下锚补齐); **reduce-only 单不受影响照发**(场所允许)。锚内发 HIGH 页, 含 `apiTradingStatus` 的锁指标与 plannedRecoverTime(只读一次, 仅供页面, 不参与决策)。
**为什么是这个形状**: (i) 场所已明说后续开仓单必拒, 继续发只增加违规计数、可能延长锁; (ii) 不用 `venue_reject` 记未发的单 —— 否则 §4-7 失败率分子分母都被我们自己灌满(2026-09-10 00Z 若锁落在首挂相, 191 张全拒 = 拒单率 100% ⇒ §4-5c/§4-7 可触发平仓, 这才是真正的风险); (iii) 与 E-0909-D 的传输熔断同构。
**不改什么**: 不读 apiTradingStatus 来决定发不发(避免新依赖进入决策路径); 不跨相传递锁状态(15 分钟后重新学一次, 代价一张被拒单)。
**验收**: 新套件 [13](首挂相 / 补单相 / reduce-only 例外 / 报告 / 矩阵一致 / -5022 不触发); 电池全绿; 研究员复核。
**部署后的观测门**: 首次触发时 `skipped_venue_lock` 行数 = 锁后剩余开仓单数; 无 `venue_reject` 膨胀。

## 2. 候选 2 · 复场/大重建分两锚建仓(只登记, 不落码)
从零重建全书时, 首锚按目标 50% 建(gross 1.0×), 次锚补齐 —— 把下单/撤单密度对半, 也把重建首锚的方向暴露对半。**这是书行为改动**, 影响回放不可比(重建锚极少), 需用户字; 若采纳, 实现点在 `resume_from_trip.sh` 后的首锚 sizing(`target_leverage` 临时 1.0)而非策略层。

## 3. 每锚深查新增项
`abandoned_max_attempts` / `venue_reject` 的码分布中出现 -4400 即报; 复场前先读 `apiTradingStatus`。
