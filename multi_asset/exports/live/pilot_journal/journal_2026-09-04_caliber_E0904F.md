# journal 2026-09-04 · 口径事故 E-0904-F(只追加)

- 08:53Z 按"席位种子样本内/对数口径"的错误结论, 把 `~/wide_shadow/state/leg_returns_live.json` 换成回放装置口径(expm1)的 OOS 种子(de0aa38b), king 席位 0.211→0.000; 生产者 kickstart PID 4833→39548。08Z 锚(原种子)w3 = [0.197, 0.122, 0.681]。
- 11:2xZ 用户"严谨确认, 如果无误进行修正": 逐字核对生产者 ret5 = c/pc − 1(简单), y4v = Σ ret5 ⇒ 生产者不是对数口径, 我拟加的 expm1 会把它改错 ⇒ 候选撤回(`.WITHDRAWN_wrong_caliber_20260904`)。
- 11:3xZ 实证: 缓存 Σ ret5(旧窗 [E,E+47])与面板 y4 逐位相等(median|Δ| 0.00); Σlog1p 与 Π(1+r)−1 都不等 ⇒ 面板 y4 = Σ 简单。
- 11:4xZ pod 真简单收益 y4s 判定: 生产 king 末 900 窗 Sharpe/锚 Σ简单 +0.100 / 真简单 +0.098 / expm1(Σ简单) −0.020; mean(expm1(Σ简单)−真简单) = −2.03 bps/锚 ⇒ 装置 CAL=simple 是伪凸性; bundle/生产者口径正确。
- 11:46:00Z 回滚: `leg_returns_live.json` ← `.pre_seatfix_20260904`(172715cea9f5, 950 行), 被撤种子存 `.oos_expm1_seed_withdrawn_20260904`; `launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop` PID 39548→58281; loop.out "next 12:16Z in 1796s"。12Z 生产者运行前完成, 12Z 为恢复后首锚(巡检 cron 6b5f8773)。
- 同时: T3c 换装 cron 删除(候选未安装, combo_stage.py b5c698f9 未改); 12Z 验收 cron 258c1372 删除(其 w3≤0.05 判据基于错前提); KC 五臂结果作废(其"凸性"即伪项); 无偏口径(CAL=log)复验批在 jpline(callog_*), jpline 11:47Z 起短暂不可达。
- 文档: ERROR_LEDGER E-0904-F(+E-0904-C 作废横幅), RUNBOOK_2026-10 §9 第三版(导出器/生产者都不改), PREREG_deploy_seat_seed_oos §8 回滚收据, PREREG_king_convexity 作废横幅, PREREG_deploy_modulation §6 暂缓, 记忆 live_seat_seed_is_in_sample 终版, 生产者测试 [10] 改口径一致性。
- 12:31Z jpline 第 6 次超时(自 11:47Z 不可达); CAL=log 复验批结果未读; 已排 21:03 本地(13:03Z)重连 cron; pod 移植子代理与全史 alpha 衰减(brm6bdb2e)在跑。12Z 锚 w3 = [0.193, 0.118, 0.689](恢复生效), 换手 0.0137。实盘对账 51 锚: 纸面真简单 +2.93 / 后移 25 分 +0.59 / 孪生 +1.72 / 资金费 −1.92 / 孪生+资金费 −0.20 bps/锚; 日 NAV 与孪生一致(±130 USDT, 4× 后首两日 −220/−280); 08-26 起真实 ΔNAV 扣入金 −879 USDT。
- 12:58Z 12Z 锚巡检(cron 6b5f8773): ① signal w3 [0.193,0.118,0.689] masked king 0.219 ∈[0.15,0.40] 恢复生效 ② Σ|Δw|/gross 0.020 ③ M1 验收 PASS(5/5, n_names 233, dw_AB 0.0062) ⑤ 口径收据: 用锚前 aux 快照 prev_rec + 缓存 Σ ret5 逐字重算三腿 = state 末行(Δ 0.00e+00 三腿), expm1 口径值不同(−29.03 vs −27.04) ⇒ 运行中的生产者口径 = Σ 简单; state 行数 950(设计上限)。
- 21:2xZ 基建两笔(非书行为): ① `~/.claude/settings.json` 增 `cleanupPeriodDays: 365`(默认 30 天会在约 30 天后清掉 768.8 MB 的 6737834a 转录与检查点快照; 其余 12 个键逐项未变, jq 校验通过)。② 会话转录卫生审计: 转录明文不加密; 发现 `AWS_SECRET_ACCESS_KEY=<50 字符>` 同一取值 17 次(指纹 45aa3919, 最早 04-17), Binance 密钥只有变量名无值 ⇒ 入 STATE §3 待用户确认/轮换。
- 21:2xZ 会话调度器提醒: 定时任务是会话内存态, `/model` 切换或终端退出即清空(今日已发生一次, jpline 重连与 bandit 复读两条到点未触发)。已重建 4 条(每锚深查 9e253683 / jpline 重连 a493188b / bandit 复读 c7a333f5 / 84 锚二读 291b2f81), 并在每锚深查模板里修正两处: 执行漏斗按 anchor_ts 归属(rebalance_id 会因 UTC 日切漏), anchor_runs.log 在 `~/dl_quant_live/state/` 而非 `state/live/`。
