# PREREG · reconcile 跨读数联合约束: 未解释余额与未决请求跨窗延续(研究员第四轮 Q6 / 合同 §2.4)

> **创建:** 2026-09-10 05:4xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 预注册(设计 + 验收判据), **未落码**; 是书行为(风控接受域)改动, 需用户字 + 账本副本回放 | **作废条件:** 研究员对合同的复核给出不同形状, 或用户裁定不采纳

## 0. 问题(研究员第四轮实证, 我方接受)
现役 `reconcile` 逐窗比较: 窗 t 的残差 = (Q_t − Q_{t−1}) − K_t − clip(·, L_t, U_t)。**下一窗以场所观察 Q_t 为新基准**, 于是窗 t 未解释的余额(例: 已解释 50, 观察 80, 残差 30)在窗 t+1 消失: 若 t+1 无成交且观察仍 80, 残差 0, §4-5b/5e 两门 CLEAN, 历史残差 30 只留在 `residual_by_anchor` 里。研究员用真实 topup(两请求各 EXPIRED 成交 25)→ 回读 80 → 下锚零成交 → 回读 80 复现: 最新一格 CLEAN 不等于数量恒等式已闭合。**这是旧 latest-only 消费方式的盲点, 不是第四/五轮引入。** 同时, 第四/五轮的授权带只在含该行时间戳的窗口生效(不会重复花掉, 已由研究员穷举 20,301 对证实), 但晚到的成交在下一窗读成未解释(误报方向), 旧 UNKNOWN 行不自动关(第五轮后子成交可跨次抬 C, 但没有「下锚按 id 查终态」)。

## 1. 合同(冻结先于任何数字)
对每个 symbol s 维护两条跨窗状态, 直到被**可核对证据**解决:
1. **未解释余额 E_s**(合约数, 带号): 窗 t 结束时 E_s ← E_s(t−1) + e_t, 其中 e_t = (ΔQ_t − K_t) − clip(ΔQ_t − K_t, L_t, U_t)。判门读的是 |E_s|·mark(而非 |e_t|·mark): 一次未解释的 +30 在被解释前每窗都算。
2. **未决请求集 P_s**: 第五轮账本里 `terminal=False` 或 `state=unknown` 的请求, 跨窗保留其 [L, U] 直到终态(场所 status / C 达 Q / 显式授权更正); 每窗的 U_t 只计 P_s 里仍未决的部分, 已在前窗解释的数量不能再解释新增量(联合约束 = 对累计 ΔQ 与累计 K 核对, 不是逐窗重发额度)。
3. **解决 E_s 的证据**(仅三类): (a) 后到的可归属成交(userTrades 按 (symbol, orderId) 联接到 P_s 里的请求)抬 K; (b) 划转/结算等非交易类的显式记账; (c) 用户签字的授权更正行(orders 追加, 类型 `reconstructed`, 带来源 sha)。**没有第四类**: 尤其不允许「下一窗观察没变」自动清零。
4. 坏值规则同第四/五轮: 非有限 / side 缺失 / 矛盾 ⇒ 不可测(异常), 不入 E_s 的算术。

## 2. 实现点(登记, 未做)
- `reconcile.reconcile()`: 输出增加 `carry_by_symbol`(E_s 轨迹)与 `pending_requests`(P_s); `position_break` 的 §4-5b/5e 读 |E_s| 而非 |e_t|。
- 未决请求落盘: 执行器在行写出时把 `request_ledger` 中非终态请求写入 `state/live/pending_requests.jsonl`(追加); 下锚阶段 B 开始时按 client id 查终态(`GET /fapi/v1/order`), 终态 ⇒ 追加修正行(orders 只追加: `reconstructed` 类型 + `supersedes_client_id`), 消费者(reconcile/m1/m3)对被替代的原 UNKNOWN 行按 `supersedes` 折叠, **不得双计**。
- 首次部署前在账本副本上回放 41 天: 报告 E_s 非零的 (symbol, 首现锚, 幅度, 解决锚); 若存在历史 E_s 会在部署当锚触发 §4-5e, 必须先由用户裁定是清零起点(记账起点行)还是先解释。

## 3. 验收判据(先于数字)
1. 研究员 Q6 夹具(两请求 EXPIRED 各 25 / 回读 80 / 下锚零成交 / 回读 80): 窗 2 仍报 |E|=30 ⇒ 5b ANOMALOUS(不再 CLEAN)。
2. 晚到成交夹具(窗 1 回读 0, 窗 2 回读 80, 请求带 [0,100] 在 P_s 跨窗): 窗 2 残差 0(不再误报), 且窗 3 不再有带可用。
3. 研究员穷举(first 0..100, second 0..200): 联合约束下「两窗残差皆 0」的解集只含 first+second ≤ 100 且 second 由 P_s 剩余解释。
4. 41 天账本副本回放: 列出全部 E_s ≠ 0 的历史事件并与 journal 的已知事故(E-0909-D/G, E-0910-A)逐一对上; 出现未登记事件 ⇒ 先查因再部署。
5. 电池: 新套件三件套; 旧 reconcile/position_break/watchdog 套件的 CLEAN/BREAK 期望逐条复核, 任何翻转必须能指出解释它的合同条款。

## 4. 数字标签
§0 的 50/80/30 与 20,301 对来自研究员 risk/REVIEW.md §7(其复算, VERIFIED by them); 本文其余是规则不是数字。
