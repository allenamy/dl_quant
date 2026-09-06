> **创建:** 2026-09-06 04:4xZ | **Session:** b9646a9e | **状态:** 预注册(判据冻结; 沙箱验证进行中; 换装需三锚全绿 + 首锚验收) | **用户字:** 09-06 "如果拉数据延迟确实是对效果造成影响, 那深入思考并按最佳路径执行, 确保效果最优" | **受据:** `PREREG_deploy_exec_n6_2026-09-06.md` 读数 #1(04Z): 数据在 N+53 s 内 100% 到位(P1 GREEN); 沙箱 = 实盘逐位(P2 恒等 GREEN); 但 runtime 243.5 s 由逐请求延迟主导(预算 480 未缩短), 落盘 N+5.05 ⇒ 时点被生产者拉数据的方式卡住, 不是被数据卡住 | **作废条件:** 任一冻结门红; 验证期间实盘任何异常; 生产者 v2 与实盘任一锚不逐位相同

# PREREG · 执行时点 Phase 2: 生产者取数层重构(并行 K 线 + 批量资金费)⇒ 落盘 ≤ N+2:30, 执行器 N+3

## 0. 事实(VERIFIED 09-06 04:3x–04:4xZ)
- 04Z 沙箱(offset 1, 预算 480): runtime 243.5 s, 实盘同锚(预算 240)235.5 s ⇒ 预算不是瓶颈; 请求 ≈ 450 K 线 + 354/457 资金费 + 1 exchangeInfo, 顺序 urlopen, 逐请求 ≈0.3 s。
- 资金费历史接口 `GET /fapi/v1/fundingRate` 不带 symbol 时返回全市场行(时间窗内), 4h 窗 465 行 / 459 名, 8h 窗需分页(>1000 行); 与逐名查询逐行相等(3 名 + 15 探针名核对, 12 个 8h 名两侧都无 04Z 行 = 一致)。**该接口与 fundingInfo 共用独立的 500 次/5 分钟/IP 配额**(交易所文档), 现行逐名 354–457 次/锚贴着上限; 批量 1–2 次。
- 在役生产者 `urlopen` 无超时(挂死风险, 靠 launchd 无法自愈单锚); v2 加 HTTP_TIMEOUT。

## 1. 改动(锁死; 生产者 v2 = 逐字原件 + 取数层旋钮, 旋钮缺省 = 逐字现行为)
- `shadow_loop_v3.py` v2(sha 见 §4 收据; diff 133 行): 环境旋钮 `FETCH_WORKERS`(K 线并行线程, 缺省 1)、`FETCH_BUDGET`(60 s 滑窗权重预算, 缺省 240)、`FUND_BULK`(批量资金费 + 逐名回退, 缺省 0)、`HTTP_TIMEOUT`(缺省 0 = 无)。**处理代码逐字不变**: K 线并行只预取响应, 仍按原顺序逐名处理; 批量资金费按每名 `fundingTime ∈ [(last_ts+1)·1000, anchor·1000+999]` 升序筛选 = 逐名查询同语义, 跳过规则(未到期不查)原样保留, 批量窗 = 锚前 8h, 更旧的名逐名回退, 批量失败整锚逐名。信号行新增 `fetch_v2` 字段(模式、页数、行数、回退数、请求/错误数、K 线/资金费耗时)。
- 部署旋钮: `FETCH_WORKERS=6 FETCH_BUDGET=720 FUND_BULK=1 HTTP_TIMEOUT=10 SHADOW_OFFSET_MIN=1`(plist env)。预算 720 = 交易所 2400/分钟的 30%; K 线 450 权重在 ≈25 s 内完成, 仍 < 720/分钟窗; 生产者在 N+3 前结束, 与执行器(N+3 起)无 API 重叠。
- 执行器(`~/dl_quant_live`, safe_commit + 电池): `external_book.anchor_offset_min` 24 → **3**, `require_producer_prefix` "combo_stage", `producer_grace_min` **4**(硬截止 N+7 = 与 Phase 1 相同的最晚时点; 宽限期满按现行语义接受文件 + HIGH 页报)。执行器代码不变(0ae54cc 已含前缀门)。
- 不改: 信号/combo/k 窗/其它作业/重挂与赌博机实验(记环境变更)。

## 2. 验证门(冻结; 沙箱 v2 与实盘生产者并行, 三锚 08Z / 12Z / 16Z, 含两个 8h 结算锚)
- **P1**(探针, 同 Phase 1): 三锚 klines@N+10 s 10/10、应结算名首查即在且 ≤ N+60 s、无抖动。
- **P2 恒等**: 三锚 sandbox 与 live 的 members/sel/coverage/fund_updates/fund_updates_base/forced_exit/fetched/missing 全同, w3 同, king 形态 target max|Δw|/gross ≤ 1e-4, universe_sha 同; 沙箱 `fetch_v2.bulk_ok` = true 三锚, `fund_fallback_n` ≤ 5, `n_err` = 0, 无 anchor_error/anchor_skip, 无 429/−1003。
- **P2 时序**: 沙箱 runtime ≤ **90 s** 三锚(含 8h 锚); `t_klines_s` ≤ 45, `t_fund_s` ≤ 5。
- **P4**: 投影 combo 落盘 = 沙箱 target 时刻 + 实盘 combo 延迟 ≤ **N+2:30** 三锚(执行器 N+3 留 ≥30 s; 硬截止 N+7)。
- **P3**: 执行器电池全绿(config offset 3 / prefix / grace 4 校验通过; 前缀门测试 P0–P7 已在 0ae54cc)。
- **取数层独立收据(换装前)**: 标准化测试 `fetch_layer_test.py`: 450 名 K 线顺序 vs 6 线程 行 sha 相等、错误 0; 批量资金费 8h 窗分页 vs 逐名 60 名逐行相等。

## 3. 换装(静默窗 17:05–17:40Z, 16Z 锚收尾后; 三锚全绿; 旧件保留)
1. 生产者: `swap_n6_producer.sh --apply` 升级版(备份 plist + 原件 → 换入 v2 文件 → plist env 五项 → bootout/bootstrap → 验 pid/lock/loop.out `next …:01:00`); 收据行原样入本文与 journal。
2. 执行器: config 三键经 safe_commit + 电池全绿; 生效于 20Z 锚进程。
3. **首锚(20Z)验收(冻结)**: 生产者 N+1 起跑, runtime ≤ 90 s, `fetch_v2.bulk_ok` true, fund_updates 同量级(4h 锚 ~354), n_err 0, 无 `_err`; target ≤ N+2; combo rc=0 ≤ N+2:45; 执行器 wake N+3 且读到 producer=combo_stage 无回退告警; 无 429/−1003; fills maker 占比 ≥ 0.75, 换手带内, 拒单率 < 40%; phase C 三件齐 ≤ N+28; sidecar 自平价 PASS; guard_twin 无新 DISAGREE 家族。任一不成立 ⇒ 回滚。
4. **回滚**: `rollback_n6_producer.sh <TS>`(原件 + plist)+ 执行器 config offset 回 24(前缀门可留); 下一锚生效。
5. 连续 6 锚验收后写 RESULT; 30 锚后报 maker 占比/费用/拒单率/markout 与换装前对照(只报不判增益; 增益上界 +0.08 bps/锚/gross 不可实盘测出)。

## 4. 收据
- v2 文件与 diff: `multi_asset/exports/live/exec_n6_2026-09-06/v2/`(shadow_loop_v3_v2.py, v2.diff, fetch_layer_test.py + json)。
- Phase 3(另立, 不在本文): 资金费跳过规则改为全名应用(批量后免费; 可提前捕获结算间隔变更), 需与在役差异的预注册。
