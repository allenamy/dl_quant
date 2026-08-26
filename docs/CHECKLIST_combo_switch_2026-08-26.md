# 换装检查清单 · combo(去rev24∧混V2MAIN φ0.45)→ target_live

> **创建:** 2026-08-26 02:4xZ | **Session:** 6737834a 主线 | **状态:** 已上闸, 首个实盘锚 = 04:00Z | **作废条件:** 换装稳定一周后并入 STATE.md 常规段
> 用户令: "现在切…最严格最细致谨慎地逐环节校验所有细节, 并标记检查清单。立即切"(2026-08-26 02:1xZ)

## A. 逐环节校验(每项带收据)

| # | 环节 | 检查 | 结果 | 收据 |
|---|---|---|---|---|
| A1 | **符号轴一致(币换位置)** | producer symbols_panel vs xfer_ref vs xfer_syms vs mini targets, 四方 829 列逐位比较 | ✅ 全部逐位相同; universe 450 全 ⊂ panel | 本日核验输出 |
| A2 | **特征管线跨机平价** | mac 迷你管线 vs 离线正史, 119 锚 47,600 行逐列 | ✅ 唯一坏列 C:vr48_8640 系当时缓存不足 30 天; 现缓存 40 天, 8640 族全部 400/400 有限 | xmachine_parity.json + 本日复核 |
| A3 | **模型管线平价(np vs torch)** | numpy 推理 vs torch 原模型在 200 样本 fixture | ✅ max\|Δ\|=3.6e-8, Spearman=1.000000(首测"FAIL"系我对已标准化 fixture 二次标准化, 已澄清) | f10_np_check.npz |
| A4 | **NaN 处理次序** | 训练=标准化→截断→NaN置0; 服务端原为 NaN置0→标准化(NaN 会变 −mu/sd) | ✅ 已修 sidecar_blend+combo_stage 两处; 当前锚 X171 实测 **0 个 NaN** ⇒ 今日行为不变, 修的是未来(新上市/数据缺口) | E-0826-E |
| A5 | **所有特征完整使用** | X171 = fea82(82)+fea89(89) 逐列拼接, 列序=训练序(同一构建脚本 env 重定向); n_cols=171 断言 | ✅ shape 断言 + 打分覆盖 400/400 | 三锚 n_f10_scored=400 |
| A6 | **funding 时效** | E-0825-G 修复在产(fund_updates 803/353/453 近三锚); aux fund-EMA 450 名非零; fund_ema 配方=训练同款 v1 normfix HL3d | ✅ | shadow_log 近三锚 |
| A7 | **币退市/宇宙** | 权重只落 universe∧members∧sel; 读者拒宇宙外目标; 离宇宙/不合格名强制出场在链内 | ✅(既有开放项不变: 宇宙冻结于 08-16, 450 vs 场所 527 —— 新旧形态同承, 非本次引入) | external_book §44 |
| A8 | **书链语义与判官同构** | 侧车 king 书复算对生产者逐位 2.27e-10; combo 用同一 chain(); 判官装置(w10 LEGS=101)与部署构造逐式同构 | ✅ | 侧车①自平价三锚 |
| A9 | **combo 计算正确性** | 幂等(两次运行逐字段同)+ **独立复算 max\|Δw\|=5e-9** | ✅ | 00:00Z 沙箱 |
| A10 | **执行器合同** | 写完立刻用实盘 external_book.verify_file+parse_target 验收自己(schema/sha/宇宙sha/gross一致/年龄/锚匹配) | ✅ 彩排 ok, age=60s, 宇宙外=0 | 彩排① |
| A11 | **时序** | 生产者落盘 N+21:12–21:51(实测 8 锚), combo ≈1s(管线已热)/≈40s(冷), 执行器读 N+23:00; **硬截止 N+22:40** 拒绝迟写 | ✅ 截止实测触发(rc=3) | 彩排② |
| A12 | **告警链路** | 中止/异常/跳过三条路径全部 HIGH 页报; 凭据只从 .env 解析 TELEGRAM 两项(不装 BINANCE 键入环境) | ✅ HIGH 与 INFO 自检均 DELIVERED | notify_audit 末条 |
| A13 | **回滚** | ① 每锚自动备份 king 原件到 target_live_king/; ② 读者验收不过 ⇒ 当锚自动拷回; ③ 整体回滚 = kill 守护 PID(下一锚起自动 king 形态), 不动任何其他组件 | ✅ 机制在码, 回滚路径彩排未破坏原件 | 彩排②后原件核验 |
| A14 | **失败缺省形态** | 任何失败 ⇒ 执行器读到生产者 king 文件(3 腿在役书)= 已验证的旧形态; 绝无"读不到文件"风险(原文件先在) | ✅ 设计+彩排 | — |
| A15 | **切换代价** | 首锚一次性换手 ≈2.4% gross(EMA 暖启动使 combo 锚定现仓) | ✅ 实测 | 00:00Z 对比 |
| A16 | **执行器/实盘仓零改动** | 本次换装 dl_quant_live 零提交; 电池维持 122/122(10063a6 起未动) | ✅ | git log |

## B. 组件清单(切换后在跑的)
| 组件 | 角色 | 状态 |
|---|---|---|
| shadow_loop_v3(PID 18998) | 数据+king 三腿书生产者, 先写 target_live(=自动回滚缺省) | 未动 |
| **combo_live_daemon(PID 72287)** | 生产者落盘后等 aux/rolling 落定 → combo_stage COMBO_LIVE=1 重写 target_live | **新** |
| combo_stage.py | 候选书计算+五层安全+读者自验收; 亦写 target_combo/(研究记录)与双书状态 | 新(NaN 序修复含) |
| sidecar_daemon(PID 11380)+sidecar_blend | 独立第二实现: king 自平价+含 rev24 的 blend 记录(交叉核对器) | 未动(NaN 序修复含) |
| 执行器/看门狗/止损/守护双子 | 全部零改动 | 未动 |

## C. 已知残留(如实, 非本次引入)
1. 宇宙冻结 08-16(450 vs 527)— 新旧同承, 待单独裁定刷新机制。
2. 实盘模型 f10_live_s42 训练至 2026-08-06/07 ⇒ 09-01 月度重训适用(RUNBOOK_monthly_retrain_2026-09)。
3. fund 构成升至 ~77%(候选结构属性, 已在正典文档 §3 局限声明)。
4. 前向证据从今日起积累; 首周判据见正典 §6。

## D. 首锚(04:00Z)验证项(锚后执行)
- [ ] combo_live.log: ⑤ 写者完成 + 读者验收 ok + 未触截止
- [ ] 执行器 anchor_runs.log: external_book.producer = "combo_stage_v1(…)", n_names≈300, sha_ok, age<10min
- [ ] phase_C: anchors_row true / position_readback 正常 / per_name_stop 正常
- [ ] reshape: net_after≈0 / gross≈NAV×1.5
- [ ] guard_twin 下一轮 AGREE + anchor_rc=0
