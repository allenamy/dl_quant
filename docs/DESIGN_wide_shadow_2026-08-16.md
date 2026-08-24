# DESIGN: 宽书影子管道(只算不下单)——建设方案与漏洞清单

> **创建:** 2026-08-16 | **Session:** 宽书战役 | **状态:** 用户已批"立即开建, 高质量严谨" | **作废条件:** 影子结束或宽书方案作废

## 0. 目的与一句话

每 4h 锚+6min, 用与离线判官同构的代码计算宽书目标仓位与模型净额, **只落盘不下单**, 逐锚与 (a) 离线回放 (b) 交易所真实费率 对账——把"实盘预期 1.3-1.6"从推算变为实测, 并充当规格类错误(如今日 carry bug)的终极检测器。PASS 判据已预冻结于 `PREREG_wide_book_assembly §4`。

## 1. 结构安全(零实盘接触的实现方式)

1. **无钥匙运行**: 只用公开端点(klines/fundingRate/fundingInfo/premiumIndex/exchangeInfo), 启动时**断言环境无 BINANCE_API_KEY, 有则拒启**——结构上不可能下单, 而非承诺不下单。
2. **独立目录** `~/wide_shadow/`(平行于 ~/exec_probe/), 不 import 实盘仓任何代码, 不读写实盘 state; 与 dl_quant_live 仓库零交集(不进 safe_commit/电池)。
3. **时间错峰**: 锚+6min 起跑(实盘书 +0~4min, 探针 +20min), 取数节流 ≤150 weight/min(IP 限 2400/min, 留 >90% 余量)。
4. **锁文件防双开**: lock 带 PID, 启动时按 PID 验尸(pgrep 文本匹配陷阱家族: 只认 PID 不认进程名)。

## 2. 数据面(每锚增量, 全因果)

- **5m 滚动缓存**(本地 npz, f16 与 pod 同 dtype 路径防漂移): 450 币 × 40 天窗(特征最长 30d+缓冲); 每锚增量拉 `limit=50` klines/币(weight 1×450, 摊 3-4 分钟); **因果断言: 只收 close_time ≤ 锚的 bar, 违者丢弃并计数**。
- **funding 账本**(jsonl 只追加): 已结算费率 (ts, rate, interval); 每锚增量拉 fundingRate(startTime=上次); interval 从 fundingInfo 周刷; **只取 fundingTime ≤ 锚**。fund_ema 用 **v1 normfix 口径**(rate×8/iv, 墙钟 HL3d)从账本滚动; carry 建模用 **rate×4/iv**(§21 修正口径)。
- **宇宙**: 钉死 450 币单(随 bundle 带 SHA); 新上币不静默加入(周刷事件显式记录); 退市币由覆盖率筛自动出局并记名。

## 3. 模型面(全部钉死, 版本化)

- slow-LGBM **2026 折 booster 文本导出自 pod 今日重训版**(IC 平价门已过), SHA 钉死; 09-01 月度重训 = 显式版本事件, 不静默换。
- 78 慢特征 keep-list、成员筛(覆盖95%/波动1e-4/量能 top400/qv≥2.5e5)、秩+帽 sizing(cap 2.5/n)、α0.1/带2.5e-4、msharpe 900 锚回看(**纯价格毛额腿收益**——carry-aware 已判负 §22-bis)——全部与 extweek 判官逐字同参。
- **bootstrap bundle** 从 pod 导出: 35d 缓存尾 + funding 账本种子 + 900 锚腿收益序列 + EMA 状态 + booster + 名单 + 全件 SHA256。

## 4. 每锚输出(shadow_log.jsonl, 只追加)

`{anchor_ts, universe_n, coverage, degraded?, weights_sha, top_holdings, gross_target, turnover_vs_prev, modeled: {gross_bps(下锚补), carry_bps, cost_bps, net_bps}, data_max_ts, fetch_weight_used, runtime_s}` + 心跳文件(deadman 用)。t+1 锚回填 t 锚的 y4 实现值。

## 5. 漏洞清单与对策(逐条设防, 验收电池逐条对应)

| # | 漏洞 | 对策 |
|---|---|---|
| V1 | 未来 bar 泄漏(取数晚于锚) | close_time≤锚 硬断言+丢弃计数; 验收: 注入未来 bar 必须被拒 |
| V2 | 半宇宙静默成书 | 覆盖门: <95% 记 DEGRADED, <80% 跳锚记因; 绝不静默 |
| V3 | 守护进程无声死亡 | 心跳文件+session Monitor(>5h 无输出告警)+下锚自检测 gap 不假装回填 |
| V4 | 双开/幽灵进程 | PID 锁+验尸; kill 只按 PID |
| V5 | 取数挂死 | socket 15s 超时×3 重试→标缺失继续, 永不阻塞整锚 |
| V6 | f16/f32 特征漂移 | 与 pod 同 dtype 路径; 验收: 冻结窗(08-10..15)特征逐因子 corr≥0.999 vs pod 面板 |
| V7 | 状态文件写坏(truncate 陷阱) | 全部 tmp+os.replace 原子写 |
| V8 | 无钥匙失效 | 启动断言无 key; 验收: 带 key 环境启动必须拒绝 |
| V9 | 限速冲突伤实盘 | 错峰+节流+逐锚 weight 用量入日志; 验收: 单锚实测 <900 weight |
| V10 | 静默换模型/名单 | 全 artifact SHA 入每锚日志; SHA 变则拒跑 |
| V11 | 断电/重启断档 | 状态原子化+重启续跑; gap 如实记录(不回填=诚实缺口) |
| V12 | funding 时点(取到未结算) | fundingTime≤锚 过滤; nextFundingTime 仅作调度提示 |

## 6. 验收电池(上线前全绿, 顺序固定)

A1 无钥匙断言双向(无 key 跑通/有 key 拒启); A2 冻结窗平价(特征 corr≥0.999+信号 corr≥0.99 vs pod extweek 同锚); A3 因果注入测试(未来 bar 拒收); A4 覆盖门三档触发正确; A5 原子写断电模拟(kill -9 中途, 状态可续); A6 限速实测 <900/锚; A7 干跑一个真锚全链路(fetch→特征→信号→落盘→心跳)。

## 7. 工期

B 段 pod 导出 bundle ~30min → C 段本地 runner ~3h → D 段验收电池 ~1h → **今日 20:20Z 或明日 00:20Z 锚正式开跑**; 影子 PASS 最早 09-01(2 周), 现实 09-08~15(4 周档)。
