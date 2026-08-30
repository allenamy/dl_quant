# MILESTONE 2026-08-26 · 宽书 combo 换装(阶段总账 2026-08-11 → 08-26)

> **创建:** 2026-08-26 03:3xZ | **Session:** 6737834a 主线 | **状态:** 阶段总账(不滚动; 当前状态唯一真相源=STATE.md) | **作废条件:** 下一次 milestone
> 上一期总账 = `docs/MILESTONE_2026-08-11.md`(单资产收口与多资产 110 名时代的关闭轴/地雷在那里, 本文不重复)。

## §0 一句话
实盘书自 2026-08-26 04:00Z 锚起 = **宽宇宙 combo 书**: 去掉 rev24 腿, king 腿 55/45 混入 V2MAIN(可微书损失 DL);
构成 ≈ 77% funding 动量 + 13% king LGBM + 10% V2MAIN, gross 1.5×NAV, maker-only, 4h 锚。
回放证据: 三种子 Δnet +0.29~+0.43 bps/锚 全显著(基线夏普 2.18 → 2.7-3.0)。

## §1 在役形态与证据链(正典指针, 引用先读这些)
| 主题 | 正典文档 |
|---|---|
| 候选定义/全量指标/杠杆表/局限/前向判据 | `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md` |
| 判决全链(腿消融/2×2/剂量-反应/**三次翻转对账 RECONCILIATION**) | `docs/PREREG_leg_ablation_2026-08-26.md` |
| 换装工程 16 项校验清单 + 组件表 + 回滚 | `docs/CHECKLIST_combo_switch_2026-08-26.md` |
| 错题集(E-0820-A … E-0826-E) | `docs/ERROR_LEDGER_2026-08-20.md` |
| 生产者栈代码快照(mac ~/wide_shadow 非 git) | `multi_asset/exports/live/wide_shadow_snapshot_2026-08-26/` |
| 判官装置存档(sha 入名) | `eda/w10_ablation_replay_hardened_9f15dea0131f_2026-08-26.py` + `eda/f10_train_pod_3fac6689d3f3c60f_2026-08-25.py` |

## §2 本期关闭的轴(判据受据在括号内; DO-NOT-RETRY 除非新证据)
**书构造**
- **fund 腿 = 书本体**(去掉 4/4 年由盈转亏 −3.04 CI[−3.86,−2.20]); **king = 组合内方差压制者**(仅king 单腿书 −2.74 亏钱; 去king ΔSharpe CI 全负); **rev24 非正向贡献者**且与 V2MAIN 冗余(组合去除三种子全显著)。(PREREG_leg_ablation §R1/§T5)
- **LGBM-171 换 king 判负**: IC 高 4 倍书层 −0.026/−0.184; 机制=其 IC 部分重复既有腿(投影掉两腿 IC 掉 10-14%)。**特征去重救不了树**(窄/宽/正交化三路全无增益, Q3 判定)⇒ 升级 king 的路 = 书损失目标。(§T8 + CANDIDATE §4)
- 2×2 终版: 目标效应 +0.488 / 弹药效应 +0.267 / 交互 +0.451; **换目标单独≈0, 换弹药单独判负, 合并才 +0.305**。
- F10 阶梯家族(R1/R1CTX/RECB/T/PLE/V3FULL/L3.2 conformer)全部不敌朴素 V2MAIN(REVIEW_f10_blend_deployment)。
**执行/风控(08-11 后新增受据)**
- 压力战役: N_eff 6-30 / 尾部预算 −25~30%@3.5× / 深V定律(stress_campaign)。渐进止损 OOS 判负 DNR; 书自带隐式止损(在役止损≈免费保险); OI 象限双口径判负; vol 可预测但按它行动亏(−22%)。
- 空头β=有报酬保费(34% 利润), 书=主导率保费(78%)+残差 alpha —— 对冲毁书。保费 sleeve 预算判负 DNR。
- 换手成本全审: 3.52 bps/单位意图 [0.32,6.64]; cad8/α/带维持。
**口径(必须内化)**
- **对数→简单收益总更正**(SR 57038bd): 9821 锚族绝对数全部重表; 可交易口径=简单持有收益。
- 执行器口径 / demean 修复 / 不合格名强制出场 / const-gross 触线 —— 全史判官已重建并逐位平价(w10 加固版)。

## §3 本期的三次结论翻转(P0 级教训, 全链对账在 PREREG_leg_ablation RECONCILIATION)
1. **E-0825-H**: 按文件名假设工件语义 → 错误 FAIL → 修正为 PASS。规则: 工件当输入前开产它的代码。
2. **E-0826-C/D**: `CAL=exec` 被静默当对数口径(13 臂污染)+ 复跑漏 `V2=1`(复跑了另一个实验)→ 错误 RETRACTION → 全环境复跑+逐位平价拉回。规则: 枚举 env 白名单断言 / 装置自报 config 且写进产物 / 复跑命令逐字抄转录 / 种子距离先标定(0.82)再谈判据。
3. **E-0826-B**: "多种子稳健"必须先断言 self_sha256 相同; sha 不同=待证不同, 等价性由复跑证明(V2TRU 中位 Spearman 1.0000 平反四个 sha)。
另: **E-0826-E** NaN 处理次序服务端与训练相反(换装前逐行审计抓获, 当前 0 NaN 零影响, 已修)。

## §4 换装工程(2026-08-26 02:4xZ 上闸)
生产者(shadow_loop_v3, 未动)先写 king 文件=**自动回滚缺省** → combo_live_daemon 等 aux/rolling 落定 → combo_stage 重写 target_live(五层安全: 硬截止 N+22:40 / king 备份 / 飞前断言 / **写后用执行器自己的 parse_target 验收失败即回滚** / 全路径 HIGH 页报, 均彩排实测)。执行器与实盘仓**零代码改动**。切换代价实测 2.4% gross。侧车(sidecar_blend)保留为独立第二实现交叉核对器。

## §5 活口(在飞/待裁定)
- ~~V2L38~~ **已判负 DNR**(2026-08-26 04:0xZ, 双种子同座替换门 FAIL, 泄漏仪器 PASS; 只封"价带38列进V2弹药"形态, LOB 执行侧/短视界轨道不受约束)⇒ 弹药结论强化: **新信息源的第一形态也未过书层**。受据 PREREG_v2l38 RESULT。
- combo 前向首周判据(CANDIDATE §6); 09-01 月度重训(RUNBOOK_monthly_retrain_2026-09)。
- 待裁定: 宇宙冻结(450 vs 场所 527)刷新机制; fund 集中 77% 的结构性风险回应; 杠杆升级(2.0× 历史不触线, 归用户); 备用逐名停机条款 STANDBY; FOMC pre-shrink 候选。
- 已知未修(非本次引入): 告警去重吞同级复发; daily_summary/redeliver 无调度器; markout 回填积压(预算限速)。
- ~~Q3 活口: 树分数作输入列~~ **已关**(V2TREE 双种子 Δ≈0 判 DNR, PREREG_v2tree RESULT)⇒ 树 raw 层优势四路全部不可变现, 该框架封卷。
- 混合书 φ 升级(0.45→0.6+)与 rev24 恢复条件: 均 DNR-无新证据不动。
- **扩容/执行队列(2026-08-27 立, 目标 NAV=30-50万, 受据 `PLAN_deposit_2026-09-10.md` §7-8; owner=Claude)**:
  ① T1 入金爬坡预注册(9-10 前交付: 分锚建仓表+逐档 markout/拒单/成交率门);
  ② 逐名流动性帽(持仓≤~1.5-2%·qv4h)预注册 + w10 回放剂量-反应(T2→300k 前置; 书行为改动=用户字);
  ③ flatten 按流动性排序退出设计(实盘仓, 电池+用户字, 平静期);
  ④ placement bandit 逐臂 markout 报告(深度轴首份正式读数);
  ⑤ 回撤阶梯定稿(2.5× 前置, 已在案); E3 脆弱性 pre-shrink 规则设计+假阳性定价(平静期)。
  ⑥ guard_twin 阈值改相对口径(bps of gross): 2.0×后绝对阈~0.86U 每锚后被正常盯市漂移触发1-2周期(08-27 实测5次, 均自愈; 形态=twin实时盯市 vs arith锚时冻结); 入金后将更频. 装置改动, 动前用户字。
  纪律: 禁五维执行优化器(样本算术); 尺寸/盘口态只作 contextual bandit 上下文, 逐步预注册。
  ~~⑦ funding极端空头处理~~ **已判 DNR**(2026-08-30 当日完整预注册流程: 平价门逐位0.0, 三臂无一过CI门; A3剔≤−10bp为差一口气近失 +0.08bps/锚双种子一致; 重开=前向~1年样本或荒年子样本重审)。受据 PREREG_funding_extreme_short RESULT。
- **总纲领裁定(2026-08-28, 48h 筛选后的分层最可行方案; 受据 PLAN_deposit §7-8 + DESIGN_lob_risk_layer §4-5)**:
  第一层(本周, Claude 直做): T1 爬坡预注册定稿 → 9-10 前交付; **月度 regime 监控三件套**(合格名数/funding分位/书尾随净vs带)入 09-01 runbook — 全队列期望值最高项(年化第一决定因素=regime); 42锚门 09-02 首读。
  第二层: 9-10 入金 @2.0×(线性容量受据)。第三层: 门绿后 2.5× 裁定=用户风险偏好(工程无障碍, 3× 不可)。
  第四层(过门才上): E3c 极端尾 pre-shrink 定价预注册(教训焊入: 极端稀有触发+小动作+富集期机会成本入表) · B3 一小时普涨信号→执行时序上下文(本轮新受据, lift 2.6-3.0× 对分复现)。
  筛掉并标价: 阶梯 −13~−26pp / 脆弱度分档 −34pp起 / 锚间逐名微调 −15bps/次 / 深模型4h方向不立项。

## §6 基建地图(2026-08-26)
| 机器 | 角色 | 关键路径 |
|---|---|---|
| mac(本机) | 生产者+执行器+全部守护 | `~/wide_shadow`(生产者栈, 非 git, 快照入库) / `~/dl_quant_live`(实盘仓 git) / `~/guard_twin` |
| jpline | 面板/判官/回放 | `/mnt/storage/private/work_hsy/{pod_backup_2026-08-21, probe_artifacts, f8_2026-08-22, dlw_2026-08-22}` |
| pod2(RTX PRO 4500) | GPU 训练 + LOB | `/workspace/{f10, f8_2026-08-22, lob_npz(811), dlw_2026-08-22}`; 重启自愈=BOOTSTRAP.sh |
| 磁盘档 | 旧 pod 撤离 | `multi_asset/exports/pod_archive_2026-08-15/`(151MB, 不入 git, 有 SHA256SUMS) |

## §7 首锚验证(04:00Z)— 五项全绿, 换装确认生效
| 项 | 收据 |
|---|---|
| combo 写者 | 04:21:56Z ⑤完成, rc=0, 36.3s(截止04:22:40), reader_ok, n=301, gross 0.8671, **kc/fc 状态=own(无断链)**, w3m=[0.238,0,0.762] |
| 执行器读取 | 04:23:30Z `producer="combo_stage_v1(kingLGBM 0.55 + V2MAIN 0.45, rev24 leg removed)"`, sha_ok, age 64s, 301 名, 锚匹配 |
| phase_C | anchors_row ✓, position_readback 329 行, per_name_stop 正常(stopped 空/cooldown 8) |
| reshape | net_after −5.9e-13 ≈ 0, gross_after 22,601 ≈ NAV×1.5 |
| 收尾 | watchdog tripped=False, **anchor done rc=0**(04:46:37Z) |
