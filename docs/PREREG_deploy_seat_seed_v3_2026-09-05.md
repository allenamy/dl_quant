> **创建:** 2026-09-05 12:4xZ | **Session:** b9646a9e | **状态:** 预注册(干跑已做, 换文件待执行于锚静默窗 12:4x–16:10Z) | **用户字:** 09-05 "king权重按装置规则更新, 确保更新无误, 所有pipeline链路正常" | **作废条件:** 换入文件与本文干跑 sha 不符; 16Z 锚席位读数落在预期带之外而未回滚

# PREREG · king 席位历史按装置规则播种(v3 bundle 样本外行替换 08-16 旧 bundle 行)

## 0. 事实(VERIFIED, 干跑脚本 `multi_asset/exports/live/seat_seed_v3_2026-09-05/dryrun_seat_seed.py`, 输出 `out_dryrun.txt`, 收据 `dryrun_receipt.json`)
- 生产者(`shadow_loop_v3.py`)每锚 LR = bundle `leg_returns.npz` 全部行 + 状态文件 `~/wide_shadow/state/leg_returns_live.json`(保留末 950 行); 席位 = 末 900 行的 msharpe(mean/(std+1e-9), 截 ≥0, 归一), combo_stage 掩掉 rev24 ⇒ king 席位 = w_king/(w_king+w_fund)。状态文件 950 ≥ 900 ⇒ bundle 行不进席位窗(09-01 换 v3 bundle 时其样本外行从未生效, 这是 STATE 里"线上 0.19 vs 装置 0.33"的缝)。
- 状态文件(sha bef771d68d94, 950 行/腿)逐位对账: 前 834 行三腿全部逐位等于 **08-16 旧 bundle** 尾部(锚 2026-03-29 04:00Z .. 08-15 00:00Z); 后 116 行 = 生产者实盘追加行, 与 score 日志锚一一对应(08-16 12:00Z .. 09-05 08:00Z, 两处非 4h 间隔系当时停跑)。
- v3 bundle `leg_returns.npz`(sha 6061af108e45, 2022-01-08 .. 2026-08-30 20:00Z, 10,176 行): 与旧 bundle 在 834 行上 fund/rev24 **逐位相等**, king 行 **0/834 相等**(两代 booster 的样本外行)。
- 装置规则 = 席位窗内每个锚用**当前模型**的样本外行(体检装置形态)。

## 1. 改动(锁死)
- 只改状态文件的 `king` 列: v3 bundle 覆盖的锚(≤ 2026-08-30 20:00Z, 共 917 行 = 834 旧 bundle 行 + 83 实盘行)← v3 样本外 king 行(按锚 ts 对齐); 其余 33 行(08-31 00:00Z .. 09-05 08:00Z 实盘行, 含 09-01 08Z 起 v3 booster 的实盘行)不动。`fund`/`rev24` 列逐位不动(断言)。行数/结构/浮点格式不变(dict 三列表, 950 行, `json.dumps`)。
- 不改: bundle、booster、导出器、生产者代码、combo_stage、执行器、任何配置。
- 干跑读数(生产者同法, 末 900 行): 现 w3 [0.1623, 0.1361, 0.7017] ⇒ 掩码 king **0.1878**; 播种后 w3 [0.2640, 0.1195, 0.6164] ⇒ 掩码 king **0.2999**(king 行均值 1.28 → 2.41 bps/锚, shp/锚 0.045 → 0.083); 对照: 只换 834 行 0.2946; v3 bundle 末 900 行单独 0.3228。
- 换入文件 = 干跑产物 `leg_returns_live.seeded_v3.json`, **sha 4a3bfd9a9353**; 换入后现场重算 sha 必须相等。

## 2. 执行步骤(锚静默窗; 生产者下次运行 16:16Z)
1. 备份: `leg_returns_live.json` → `leg_returns_live.json.pre_seatseed_v3_20260905`(sha 必须 = bef771d68d94; 旧件保留)。
2. 原子换入: 写 `.tmp` 后 `os.replace`; 读回 sha = 4a3bfd9a9353, 行数 950×3, fund/rev24 逐位等于备份。
3. 重启生产者(唯一动词, E-0904-A): `launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop`; 验: `launchctl list` 新 PID, `shadow.lock` = 新 PID, `loop.out` 出现 `next 2026-09-05T16:16:00+00:00`, 日志无 Traceback。
4. 16Z 锚验收(巡检 cron): 生产者 w3 掩码 king ∈ [0.28, 0.32](= 0.2999 ± 一行追加的影响), 状态文件 950 行且末行为 12Z 锚新行; combo_stage 正常重写 target_live(五层安全通过); 执行器 16:23Z 正常, position_readback 核对; sidecar 自平价 PASS; FTRIM/M1 PASS。任一不成立 ⇒ 回滚。
5. 回滚: `leg_returns_live.json` ← 备份文件, 再 kickstart; 下一锚生效。
- 禁: 改 bundle 或生产者代码"顺手"一起换; 在 16:00–16:30Z 之间做任何改动。

## 3. 收据(执行后填)
- 换入: 2026-09-05 12:47:3xZ; 备份 `leg_returns_live.json.pre_seatseed_v3_20260905` sha bef771d68d94; 换入后 live sha 4a3bfd9a9353(= 干跑产物); king 行改 917, fund/rev24 逐位不变; 现场重算掩码 king 席位 0.2999, w3 [0.264, 0.1195, 0.6164]; 生产者 kickstart PID 58281 → 10900, shadow.lock = 10900, loop.out `next 2026-09-05T16:16:00+00:00`, 无 Traceback。研究仓预注册提交 2040662(sha fed8faa4)。
- 16Z 验收: <填>
