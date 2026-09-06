> **创建:** 2026-09-06 01:0xZ | **Session:** b9646a9e | **状态:** 预注册(判据冻结; 验证阶段进行中; 换装需全部门绿) | **用户字:** 09-06 "确保提前到n+6执行能获取最新数据, 且没有任何风险和策略, 进行实施, 并严谨验证, 通过可换装" | **受据:** RESULT_trackA_newinfo 附录 002f326(前 25 分钟换手部分 +0.08 [+0.05, +0.11] / +0.075 [+0.05, +0.10] bps/锚/gross = 提前执行的价值上限); 体检 §7(时点衰减 5–9%) | **作废条件:** 任一冻结门红; 验证期间实盘任何异常

# PREREG · 执行时点从 N+24 提前到 N+6: 时序链改造、数据到位验证、冻结门与回滚

## 0. 现状时序链(VERIFIED 09-06 读码/读 plist)
| 环节 | 现在 | 依据 |
|---|---|---|
| 生产者 shadow_loop_v3 启动 | N+16(launchd env `SHADOW_OFFSET_MIN=16` 覆盖 bundle config 的 6) | plist; `next_slot()` |
| 生产者数据拉取 | 每锚 ~450 次 5m K 线(至收盘于 N 的 bar)+ 357/457 次资金费(`fundingRate` 逐名, endTime=N+999ms); 自限 240 权重/分钟 ⇒ 运行 230–316 s | L110–135, L268–300, L319–352 |
| target_live 落盘 | ≈ N+20–21(king 形态, producer="shadow_loop_v3") | L544 |
| combo 守护 | 轮询到新文件且 aux/rolling 落定后重写为 combo 形态(≈30 s; N+22:35 硬截止) | combo_live_daemon.sh |
| 执行器 | launchd N+0 启动, `external_book.anchor_offset_min=24` ⇒ 睡到 N+24 读文件(校验 schema/锚/宇宙, **不校验 producer 字段**); k 窗 900 s; phase C ≈ N+44 | external_book.py L213–226; book.json |
| 其它作业 | c2shadow N+25; regime_dash N+50; sigma_ladder N+52; universe_shadow N+54; anchor_report N+55; sidecar 见新文件后 120 s 起; guard_twin/stopoverlay/depthwatch 每 20 min | plists |
- **N+16 不是数据约束**: 收盘于 N 的 bar 在 N 即定; 结算费率在结算后短时可查(待本文 §2 探针量化)。它是"自限 4 req/s × 逐名拉取"的工程选择。
- **价值上限(VERIFIED)**: 回放里记给尚未成交换手的前 25 分钟收益 +0.08~+0.10 bps/锚/gross(2× ≈ +3.5~4.4% NAV/年); 实盘 N+23 的 maker 成交已拿到其中未知的一部分(maker 成交价优于锚中价 +3.9 bps)。**实盘测不出这个量级**(每锚 shortfall 噪声 ±20 bps/单位换手, 42 锚 SE ≈ 3 bps vs 效应 ≈ 1.6 bps/单位换手)⇒ 换装依据 = 回放上限 + **无害性验证全绿**, 不承诺可测的实盘增益。

## 1. 改动(锁死)
1. 生产者: `SHADOW_OFFSET_MIN` 16 → **1**(plist env; 需 bootout/bootstrap 重载, 非 kickstart); 自限 240 → **480 权重/分钟**(`shadow_loop_v3.py` L123 常量, 仍 ≤ 交易所 2400/分钟的 20%; 备份原件, 与 FTRIM 同法); 预期落盘 ≤ N+3:30, combo ≤ N+4:30。
2. 执行器(`~/dl_quant_live`, safe_commit + 电池): `external_book.anchor_offset_min` 24 → **6**; **新增 producer 前缀门**: config `require_producer_prefix: "combo_stage"` + `producer_grace_min: 5` —— 文件 producer 字段不匹配时视为可重试(继续轮询), 宽限期满仍不匹配则按现行语义接受该文件(king 形态回退)并 HIGH 页报; 默认(键缺失)= 现行为(不校验)。恒等: 键缺失时全部套件逐位现行为。
3. 不改: 信号、combo_stage、k 窗、其它作业时点、重挂/赌博机实验(两臂同受时点变化, 在其预注册记环境变更)。

## 2. 验证(先于换装; 全部只读或沙箱)
- **P1 数据到位探针(公开接口, ≤1 req/s, 27 名: 4h 12 / 8h 12 / 1h 3)**: 在 04Z/08Z/12Z 三个锚, 于 N+0:10 查 klines(endTime=N−1ms, 收盘于 N 的 bar 是否在), 于 N+0:20/+0:45/+1:15/+2:00/+4:00 查 `fundingRate`(N 结算行是否在)。**门 P1**: 三锚 × 全部应结算名, 在 **N+1:00** 前 100% 到位(否则生产者 offset 取"100% 到位时刻 + 30 s")。
- **P2 沙箱生产者并行**(`WIDE_SHADOW_HOME=~/cc_tmp/.../exec_n6_sandbox`, 复制 state 99 MB, bundle 只读, offset 1, 预算 480; 独立 lock/log/target; 不写实盘任何文件): 04Z 起每锚与实盘生产者(N+16)的 target_live 逐名比对。**门 P2**: ≥3 锚(含 ≥1 个 8h 结算锚 08Z)`fund_updates`/`sel`/`w3`/成员集相同, 权重 max|Δw|/gross ≤ 1e-4(因果随机性允许 f16 抖动); 沙箱运行时间 ≤ 210 s; 沙箱 API 窗口权重峰值 ≤ 480/分钟且无 −1003/429。
- **P3 执行器电池**: 前缀门 + offset 6 的测试(恒等/前缀等待/宽限回退+告警/超时预算); safe_commit 全绿; DRY_RUN 彩排锚验证等待逻辑在 N+6 读到 combo 文件。
  - **P3 收据(01:02Z)**: 实盘仓 `0ae54cc`(safe_commit, 128/128 绿, 已推送): `external_book.py` 新键 require_producer_prefix/producer_grace_min(缺省 None/0 = 逐位现行为), `anchor_loop.py` 回退 HIGH 页报, `tests_external_book.py` +7 项(P0 恒等 / P1 关 / P2 配置 / P3 等重写 / P4 宽限回退 / P5 非轮询不阻塞 / P6 缺文件不变 / P7 页报静态钉)。config 未启用(换装时与 offset 同批)。
- **P4 时序冲突表**: 沙箱落盘时刻 vs combo 守护 120–150 s 落定等待 vs 执行器 N+6 —— 逐锚打印; 若 combo 落盘 > N+5:30 任一锚 ⇒ offset 改 7。

## 3. 换装(静默窗, 全门绿后; 旧件保留)
1. 备份 plist 与 shadow_loop_v3.py; 改 env/常量; `launchctl bootout gui/$(id -u)/com.hsy.shadowloop` → `bootstrap`; 验 PID/lock/loop.out `next …:01:00`。
2. 执行器: 已提交的前缀门 + config offset 6 生效于下一锚进程。
3. **首锚验收(冻结)**: 生产者日志 N+1 起跑、runtime ≤ 210 s、fund_updates 与前几锚同量级(4h 锚 ~357 / 结算锚 ~457)、无 `_err`; target 落盘 ≤ N+4; combo rc=0 ≤ N+5; 执行器 wake N+6, 文件 producer=combo_stage, 无前缀门回退告警; 无 −1003/429; fills maker 占比 ≥ 0.75(实验期基线 0.61–0.83)、换手带内、拒单率 < 40%; phase C 三件齐 ≤ N+30; sidecar 自平价 PASS; guard_twin AGREE。任一不成立 ⇒ 回滚。
4. **回滚**: plist env 回 16 + 常量回 240 + bootout/bootstrap; 执行器 config offset 回 24(前缀门可留, 缺省即现行为); 下一锚生效。
5. 连续 6 锚验收后写 RESULT; 30 锚后报 maker 占比/费用/拒单率/markout 与换装前对照(只报不判增益)。
