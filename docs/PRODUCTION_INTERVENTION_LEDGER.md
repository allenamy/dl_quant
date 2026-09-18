# 生产干预台账(追加式; 每行带首个受影响锚)— 立于 2026-09-18(FP3 J, RUNBOOK 2026-10 §0★ 修订 7)

> 语义: 生产者在 A+20m 计算锚 A、结算时(A+4h20m)落盘记录; 执行器在 N+24:00 读取。「首个受影响锚」按这个语义判定, 不按 logged_utc。每行必须带受据。

| UTC | 对象 | 变更 | 首个受影响锚 | 受据 |
|---|---|---|---|---|
| 2026-08-26 ~00Z | 在役书 | king 形态 → combo(55/45 混 V2MAIN) | 08-26 00Z | `docs/MILESTONE_2026-08-26.md` |
| 2026-09-02 ~12:xxZ | 生产者 `fea171/combo_stage.py` | ff5de5d8 → b5c698f9(加 FTRIM) | 09-02 12Z | `DESIGN_FP3_P…` §7; P-B 时间线 |
| 2026-09-04 ~04Z | 生产者 `shadow_loop_v3.py` | db326162 → e9c98374(M1 宇宙 Phase A) | 09-04 04Z(标 04Z 记录首现 M1 字段) | 同上 |
| 2026-09-05 12:47Z | 生产者状态 `state/leg_returns_live.json` | 席位播种 v3(sha bef771d6 → 4a3bfd9a) + kickstart | **09-05 16Z**(12Z 运行在 12:20Z 已完成) | `seat_seed_v3_2026-09-05/dryrun_receipt.json`; P-B v5 |
| 2026-09-12 06:05Z | 执行器树 | d040c74 → b681ca5 | 09-12 08Z | STATE 09-12 06:1xZ |
| 2026-09-13 12:0xZ | 执行器树 | 918559f → ef60f85(四包 git apply) | 09-13 12Z(复场首锚) | STATE 09-13 12:0xZ |
| 2026-09-17 02:06Z | 执行器树 | ef60f85 → 6661ea3 | 09-17 04Z | STATE 09-17 02:06Z |
| 2026-09-17 09:16Z | 执行器树 + `config/book.json` | 6661ea3 → 6e177c4(booster_sha_pin) | 09-17 12Z | STATE 09-17 09:16Z |
| 2026-09-17 12:59Z | 执行器树 | 6e177c4 → 58256ed(f10_sha_pin 读者) | 09-17 16Z | STATE 09-17 13:0xZ |
| 2026-09-17 ~16:2xZ | 生产者 `fea171/combo_stage.py` | b5c698f9 → 3520d363(写 f10_sha) | 09-17 16Z | `producer_parity…` 受据 |
| 2026-09-17 16:24Z / 17:4xZ | 执行器树 | 58256ed → d858c36(f10_sha_pin 钉值)/ 81ea654(NOSLEEP-1) | 09-17 20Z | STATE 09-17 17:46Z |
| 2026-09-18 02:46Z | 执行器树 | d858c36 → 409ea16(NOSLEEP R7-K1) | 09-18 04Z | STATE 09-18 02:5xZ |
