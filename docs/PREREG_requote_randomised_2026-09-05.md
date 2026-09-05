> **创建:** 2026-09-05 11:3xZ | **Session:** b9646a9e | **状态:** 预注册(判据冻结; 实施同批提交实盘仓, 读数点前不看臂间差) | **用户字:** 09-05 "重挂可以随机实验, 但是一定不要引入任何错误, 精准实施" | **作废条件:** 读数点前改 p_requote 或动作集; 判据在看数字后被改; 任何数字无脚本收据

# PREREG · −5022 重挂的实盘随机实验(requote vs direct)

## 0. 为什么随机化
- 重挂(phase 1.5)08-06 上线, 从未在真实账本上判决; 前后对比前期仅 4 天, 双重差分 CI ±13 bps(`RESULT_requote_and_behind_live_causal_2026-09-05` §2)。再观察不会缩小区间。
- 反事实只能由同锚随机化取得: 同一锚内, 被拒名一部分照旧重挂, 一部分直接走 08-06 前路径。

## 1. 干预定义(全部锁死, 与实盘仓提交同批)
- 单位: attempt-1 被 −5022 拒的计划 (rebalance_id, symbol)。动作集 {requote, direct}; reduce_only 一律 exempt(照旧重挂)。
- 分配: sha1(f"requote:{rebalance_id}:{symbol}") 末字节 < round(p×256) ⇒ requote, 否则 direct; p = `config/book.json` 的 `requote_experiment.p_requote` = **0.5**。盐与挂单赌博机不同 ⇒ 两实验分配独立(测试 T3b 断言一致率 ≈50%)。
- direct 臂 = 跳过该名的重挂调用; 该名留在 `benign_rejected`, `_topup_source=from_reject` 不变, 在 k 窗末按既有政策 IOC 补单 —— 与"二次拒"和"重报价无新鲜盘口"两种既有情形**同一条代码路径**, 不新增任何路径; 唯一候选全为 direct 时连 bookTicker 都不读(零场所调用, 测试 T7)。
- 恒等陷阱反向: 实验"关" = 现行为 = 全部重挂; p=1.0、键缺失、形状错、任何异常 ⇒ 全部重挂(测试 T1/T2/T10), 绝不落到"不重挂"。
- 记账: 订单行新增 `requote_arm`(requote/direct/exempt; attempt-1 拒单行写于分臂之前为 null, 由 attempt-2 行/补单行/终态 maker 行携带)与 `requote_p`; 执行器 requote 报告新增 `n_direct / n_exempt / p_requote`(落 launchd 日志)。
- 回滚: `p_requote` 置 1.0(或删除键), 下一锚生效; 无代码改动。
- 生效: 实盘仓 safe_commit 全电池绿后首个新起的锚进程(执行器按锚起新进程)。MC-3 验收: 首锚日志 requote 报告出现 `p_requote: 0.5` 与 `n_direct > 0`, 订单行出现 `requote_arm`。

## 2. 判据(冻结, 先于数字)
- **主指标**: 计划级意向处理全包成本 = 该计划全部成交(首挂/重挂/补单)的 Σ|名义|×(相对 `mid_at_anchor` 的价差 bps + 费 bps) ÷ |意向名义|; **锚内配对**(逐锚按名义加权的臂均值之差, 再按锚名义加权汇总), UTC 日块 bootstrap 2000, 种子 20260905。装置 = `multi_asset/exports/live/exec_requote_behind_2026-09-05/analyse_requote_behind.py` 的口径, 臂由行上 `requote_arm` 读取(exempt 剔除)。
- 次指标(只报不判): 实现名义/意向、maker 腿成交占比、补单 from_reject/from_partial 名义占比与成本、markout60(覆盖率先报)、每锚场所请求数差。
- **读数点**: 部署满 14 个自然日 **且** direct 臂累计 ≥ 1,500 个计划(两者皆满足后的首个 00Z 锚), **恰一次主判**; 读数前不看臂间差(每锚巡检只报两臂计数与安全线)。
- **判读**: 重挂有帮助 ⇔ Δ(requote − direct) < 0 且 CI95 不含 0 ⇒ p 置 1.0 并补追认(现状合法化)。重挂有害 ⇔ Δ > 0 且 CI95 不含 0 ⇒ 建议 p 置 0.0(= 撤回重挂), 需用户字。其余 UNDECIDED ⇒ p 置 1.0(恢复现行为), 实验关闭入档, 不延期不加臂。
- **安全线**(每日锚后人工复查): 连续 3 日 direct 臂日均成本高于 requote 臂 30 bps 以上(各日 n ≥ 100)⇒ p 置 1.0 排查; 实验列缺失或 requote 报告缺 `p_requote` ⇒ 同上。
- 禁: 中途改 p 或阈值; 用观测数据先看臂间差; 多次读数。

## 3. 实施与验证收据(填于提交后)
- 实盘仓提交: **`12aa2a1`**(2026-09-05 11:48Z, safe_commit, 128/128 套件绿, 已推送; 首跑因普查未声明新模块被 `tests_rehearsal_anchor` 拒, 加豁免声明后复跑绿); 新模块 `live/requote_experiment.py`; 套件 `live/tests_requote_experiment.py`(30 断言: 恒等/失效安全/确定性/份额/exempt/direct 零新路径与零场所调用/requote 臂逐位现行为/记账列/配置在位/静态钉); `tests_binance_executor` 的旧 RQ 夹具钉 p=1.0(其断言语义不变)。
- 首锚 MC-3 验收 ✓(12Z 锚 A1788611039, 巡检 13:4xZ): launchd requote 报告 {n_candidates 18, n_requoted 18, n_rested 18, n_refused_again 0, p_requote 0.5, n_direct 19, n_exempt 0}; 订单行 requote_arm: requote 36 / direct 19; direct 臂 19 名走既有 from_reject 补单(告警文案同旧路径); 首次 −5022 37/171 = 21.6%。运行代码 = 12aa2a1(新口径日志行同锚出现)。
