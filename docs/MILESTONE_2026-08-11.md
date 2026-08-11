> **创建:** 2026-08-11 15:0xZ | **Session:** multi-asset-v2 主线 (6737834a) | **状态:** final(阶段里程碑) | **作废条件:** 下一里程碑发布
> **性质:** 阶段总账 + 全部关闭轴索引 + 活口清单 + 地雷路由。重启任何任务先读本文相应小节, 再进对应受据文档。

# MILESTONE 2026-08-11 — 多资产实盘第一阶段: 参数封卷 · 天花板三重证明 · 新源第一轮

## 1. 在役栈(实盘, 真钱)

- **仓库**: `~/dl_quant_live`(落盘即上线, 改动只经 `ops/safe_commit.sh`, 电池 `run_acceptance.sh` 118/118); 研究仓 `~/Desktop/quant_research`(本仓)。
- **配置**: king 8h 刷新(00/08/16Z) + s2 24h + funding 8h, 权重 .5952/.2024/.2024; RB α=.5 λ=1; **EMA α=0.05 + 中性带 b=0.002**(to-target); k=900 maker-only GTX; 政策A 不追价; 2× 杠杆; 场外死人开关 hc-ping(每锚 LIVE ping)。commits: `87123cb`(三连部署)→`3f28d1f`(死人开关)。
- **离线口径**: 净 +1.154 bps/锚, 夏普 1.46, 换手 0.026/锚, 无亏损年(2022 +2.18 … 2026 +0.699)。
- **实盘验证(08-11)**: 52 锚书级 rank-IC **+0.0504 (t=2.62)** = 离线滚动分布第 **72 分位**; ic_monitor 每日 09:30 SGT 自检, R24/R48 远离阈值。→ `eda/RESULT_ic_caliber_ladder_voltarget_2026-08-11.md` §1(口径楼梯: king 0.0546 / 复合新鲜 0.0493 / 持仓书 0.0368 —— 每层 IC 折价都在买净额)。
- **在飞裁定**: 84 锚窗(~10/84, PASS ⇒ 3×+停机线−50% 预授权包, PREREG_deposit `30d1a53f`); CRV/BOME 仓储观察线 |15%|。

## 2. 已关闭轴总索引(引用关闭必须带受据文档)

| 轴 | 判决 | 受据 |
|---|---|---|
| **模型侧 rank-IC 整域** | 天花板 ~0.047 是数据属性(构造证明: 冻结SSL表征+浅头 0.0465=全监督 0.0463) DO-NOT-RETRY | RESULT_gpu_night_campaign_2026-08-10 |
| 目标视界(y4/8/12/24) | 全灭(y24 六种子终审; 判决装置同寿命规则出处) | RESULT_gate1_y24_seed2 §5 |
| regime/择时/顺势 | 五形态全死(无因果指标); 复活件=W4清算强度真值 | HEALTHCHECK_full §4/§6 |
| 整形层(α×b×模式×腿权×RB) | 66格联合曲面在役即最优(理论双验: b*=0.0035+带边定理) | RESULT_jointopt_surface_2026-08-11 |
| 自适应换手 | 感知门三条件量全fail(能感知风险不能感知回报) DO-NOT-RETRY | RESULT_adaptive_turnover_2026-08-11 |
| 书级波动目标化 | 保险形态(夏普+0.14/最差年+74%)逐年3/5不过门; 具名复活=弱年优先时代 | RESULT_ic_caliber_ladder_voltarget §2 |
| 幅度/尺寸六尸 | isotonic/γ收缩/w_mag/QIM/映射αλ/vol目标化 — 幅度技能在此SNR不存在 | 同上 §3 |
| 跨领域范式 14 筛 | 顶部加权损失/段位混合/R5双形态/元标注/基础模型/GNN/保形 全关; 三线合流"上限=信息集" | SURVEY_crossdomain_paradigms_2026-08-11 |
| 新源第一轮 | W4清算代理 0/7(方向性发现: 瀑布4h延续非反转); RM1过S1死S2; OI/taker流/解锁 前判 | RESULT_w4_gate1 / RESULT_rm_channels |
| 执行微干预 | chase(n=39)/requote两代/重挂 全被自身装置否决; maker滑点为负−2.23bps | RESULT_live_forensics §6 / chase_closed |
| 树 vs DL | DL优势=时序深度+池化≈+45-50%(浅面板0.033→冠军0.047); "树在DL上加成"实验因默认脏面板作废待重跑 | 本文 §4 地雷#1 + SURVEY |
| RL 执行 | 分层否定: 锚级(无感知状态+解析最优已知)/微级(奖池几毛每天+模拟器鸿沟)/离线RL(动作空间退化); 梯子低层=R1 | 会话记录 2026-08-11(树/RL评估) |

## 3. 活口(按期望值排序)

1. **84 锚窗 → 3×**(整书 +50%, 只需时间; 读数 ≈08-24);
2. **R1 成交概率**(执行侧唯一真杠杆: p=0.839, from_partial −40bps; 标签 6k+ 日增 250; 首拟合门 AUC +0.02);
3. **W4 真值裁定**: 采集器 24h 心跳(`~/w4_liq_capture`)判端点生死 → 死则 Tardis C叉(~$700-1200 一次性, 用户钱裁定; 同时解 Q4-regime 因果指标);
4. **R4 LLM 事件流**(#36, 最后一条未动正交源, 设计未起);
5. **#29 已付费 BTC 25档书**(执行侧价值, 零新钱)。
6. 数据购买总判: 无刚需; 当前 NAV 下入金期望回报高于买数据一个量级(会话记录 08-11)。

## 4. 地雷路由(重启任务前查此表, 详情在 memory/)

1. **默认面板=脏面板**: `engine/panel_source.py` PANEL=wide_dl_full.npz(betaadj_ret24 含11h前视, 故意保留供归因复现); 特征实验必须显式传因果面板 —— LGBM 曾 30 分钟"打穿"天花板全靠它。现已加横幅。
2. **面板行=K线开盘索引**: 锚→墙钟 +1h(anchor_ts 名义−1h 家族); 特征面接面板必须双守卫(命中率 + 偏移谱峰@0)→ w4_gate1.py v3 是模板。
3. **口径三层**: 模型分数/新鲜目标/持仓书 IC 各差 20-25%, 引用必须带层(§1 楼梯)。
4. **排序≠净额**(四例): S1 +0.003 是必要非充分; "段内 spearman"不得单独立项。
5. mode 树/DRY 污染: 判据数字必须带绝对路径; LIVE_MODE 判别式全仓唯一写法(tests_deadman_ping)。
6. 实盘状态只从 STATE.md 读; 完成体动词必须有收据; 判决装置与结论同寿命(判官脚本当日入 probe_artifacts/ 或仓)。
7. jpline = 容器化训练机(#67: 断连=容器/端口变更非限流); pod 易失层(EXPORT 符号链接每容器重建)。

## 5. 基建地图

- **jpline**(ssh jpline, env hsy_v5push): 面板/预测npz/判官在 `/mnt/storage/private/work_hsy/probe_artifacts/`(joint_opt/adaptive_turn/vol_target/tail_pregate/segblend/w4_gate1/rm_build_gate/r5_pregate/lgbm_vs_dl + logs); 数据 `…/quant_research_multi_asset/multi_asset/exports/`(wide_metrics_raw 143币至08-09 / w4_klines5m 2.0GB / w4_liq_proxy_v1.npz / rm_channels_v1.npz)。
- **本机常驻**(launchd): com.dlquant.live.{anchor,nosleep,icmonitor} + com.hsy.{c2shadow,w4liqcapture}; FileVault 开(无人重启不可自愈=设计使然, 死人开关补探测)。
- **正典复现**: docs/…champion_baseline_repro(记忆) + `eda/PREREG_retrain_causal_panel_2026-08-03.md`; 训练显式 `--xattn --lam_orth 0 --wide_dl_path <因果面板>`。
