# STATE — 当前状态唯一真相源

> **重置于 2026-08-26 milestone(combo 换装)。** 此前全部历史横幅 → git 历史 + `docs/MILESTONE_2026-08-26.md`(08-11→08-26 总账)+ `docs/MILESTONE_2026-08-11.md`(更早)。
> 重启任务: 先读本文件 → `docs/TEAM_PROTOCOL.md` → 按 CLAUDE.md 路由表取正典文档。**不信任何更早轮次的摘要, 包括自己的。**

## §1 在役实盘(live, 真钱)
- **书**: 宽宇宙 combo(**去 rev24 腿 ∧ king 腿 55/45 混 V2MAIN** φ0.45), 2026-08-26 04:00Z 锚起。构成 ≈ 77% fund + 13% king(LGBM) + 10% V2MAIN(可微书损失 DL, 171 列)。宇宙 450, 4h 锚, maker-only, **gross = 1.5 × NAV**(NAV ≈ 15k)。
- **链路**(每锚): `~/wide_shadow/shadow_loop_v3.py`(N+16 起跑, 写 king 三腿文件 = **自动回滚缺省**)→ `combo_live_daemon`(fea171/, PID 见 `combo_live_daemon.pid`)等 aux/rolling 落定 → `combo_stage.py` 重写 `state/target_live/{anchor}.json`(五层安全: 硬截止 N+22:40 / king 备份 target_live_king/ / 飞前断言 / **写后用执行器 parse_target 自验收, 失败自动回滚** / 全路径 HIGH 页报)→ 执行器(`~/dl_quant_live`, external 模式)N+23 读并交易。
- **模型**: `fea171/f10_live_s42_np.npz`(V2 配方全史重训至 2026-08-06/07; np≡torch 3.6e-8)。king booster = slow2026。
- **止损/风控**: 逐名 wide 档 d30_n2_c42(depth −0.30×2锚×7d)⟺ book_source=external 耦合; 看门狗 cond2 日亏 −4% flatten(口径 0aa6586)/ cond4 −25% 起始权益口径(57cb180); ArmingRefused 自带 CRITICAL(10063a6)。
- **守护/采集**: guard_twin(20min, 账本孪生+**锚任务存活哨**·坏态 HIGH 恢复 INFO 均实测)· sidecar_blend(独立第二实现交叉核对, 每锚 king 自平价 2e-10)· depth_watch · stop_overlay · ic_monitor · nosleep · chase 随机实验 · pilot_log 全套。执行探针已 KILL(勿复活)。
- **回滚**: `kill $(cat ~/wide_shadow/fea171/combo_live_daemon.pid)` ⇒ 下一锚起 king 三腿形态; 全停 = `~/dl_quant_live/ops/KILL.sh`。
- **改实盘代码唯一通道**: `~/dl_quant_live/ops/safe_commit.sh` + 电池 122/122; mac 生产者栈改动须同步快照入研究仓。

## §2 在飞
- **combo 首周前向判据**(CANDIDATE §6): ≥42 锚后首读, 影子记分净额 ≥0 且方向与回放一致; 逐锚 kc/fc 状态断链或自复算 >1e-6 当日排查。
- **V2L38**(LOB 价带弹药, f11 811 币特征已建)双种子训练 @pod, 判据冻结 `docs/PREREG_v2l38_2026-08-26.md`(泄漏仪器先行/同座替换门/换手+25%即负/2023折降权)。
- V2K78 s2027 预测已出待书层判(2×2 第二种子)。
- 09-01 月度重训: `docs/RUNBOOK_monthly_retrain_2026-09.md`。

## §3 待裁定(书行为改动, 归用户)
- 宇宙冻结刷新(450 vs 场所 527); fund 集中 77% 的回应; 杠杆升级(候选 2.0× 历史不触 −25% 线); 备用逐名停机条款 STANDBY(cf40ea21); FOMC 16Z 预缩候选; rev24 恢复与 φ 升档 = DNR 无新证据不动。
- 已知未修(非 08-26 引入): 告警去重吞同级复发; daily_summary/redeliver 无调度; markout 回填积压(预算限速)。

## §4 口径纪律(违者结论作废)
- **收益一律简单口径**(expm1; 对数口径系统性乐观, SR 57038bd); 判官 `CAL` 只认 simple|log(白名单断言, E-0826-C)。
- **V2MAIN 训练必带 `V2=1`**; 复跑命令逐字抄转录/正典, 不凭记忆(E-0826-D)。
- 多种子声明先断言 self_sha256 相同; sha 异=待证, 等价性由复跑证明(E-0826-B)。
- 服务端数值链与训练逐算子同序(标准化/截断/缺失值, E-0826-E); 工件当输入前开产它的代码(E-0825-H)。
- 面板默认值陷阱 / IC-β 纪律 / 口径三层 / 排序≠净额: 见 CLAUDE.md(不变)。

## §5 基建
milestone §6 的机器/路径表为准: mac(生产+执行)/ jpline(面板+判官)/ pod2(GPU+LOB)/ 151MB 旧 pod 档不入 git。
