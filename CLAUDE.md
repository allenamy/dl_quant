# DL Quant — Multi-Asset Track — Project Guidance

> **Phase:** 多资产实盘阶段(2026-08 起, 真钱 pilot 运行中)。**阶段总账: `docs/MILESTONE_2026-08-11.md`** —— 重启任何任务先读它的对应小节。
> **单资产 BTCUSDT 已收口, 权威终版 = `docs/2026-07-06_SINGLE_ASSET_PERP_Y600_CLOSEOUT.md`**(Run1 双盘口 REG_arch @修正后 spot+perp 数据, 诚实口径 P≈0.049, maker-only ≤0.76bps/side, 非 taker)。05-20 milestone 为其历史基线(anti-patterns #1-#29 出处; 其 0.0646/Sharpe 4.4 系 clip+demean+强月口径构造, 更正见 07-06 文档 §2.3 与 memory `single_asset_record_caliber_correction`)。

## ★ 会话起步必读(顺序固定)

1. **`STATE.md`(仓库根)** —— 当前状态唯一真相源(线上配置/在飞任务/冻结项/口径纪律)。**先读它, 不信任何更早轮次的摘要, 包括自己的。**
2. **`docs/TEAM_PROTOCOL.md`** —— 协作规则(完成必须声明+收据/具名 owner/引用前打开看/落盘即上线)。
3. **`docs/MILESTONE_2026-08-11.md`** —— 已关闭轴总索引 + 活口 + 地雷路由 + 基建地图。**引用任何"已关闭/DO-NOT-RETRY"必须带它指向的受据文档。**
4. 历史脉络: `multi_asset/exports/live/pilot_journal/`(只追加)。

## 项目身份

**Binance USDT-perp 多资产中频市场中性**: ~110 币, 4h 锚(00/04/08/12/16/20Z), 三腿书(king DL 8h + s2 慢反转 24h + funding 8h), maker-only 执行。**实盘仓 `~/dl_quant_live`**(落盘即上线; 改动只经 `ops/safe_commit.sh`; 电池 `run_acceptance.sh` 必须全绿; mode 判别式唯一写法见 `live/tests_deadman_ping.py`)。

**数据**: `/mnt/storage/share/bar_data`(READ-ONLY, mode="r"); BTC Tardis 高精度 `/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/`(READ-ONLY; **旧 `23-25-BTCUSDT` 已弃用** —— 其 book 是现货, 现货-永续口径 bug 是 B25-FAIL 根因); 宽宇宙面板与判官在 jpline `/mnt/storage/private/work_hsy/`(路径详表: MILESTONE §5)。**★ 面板默认值陷阱: `engine/panel_source.py` 默认=as-trained 脏面板(betaadj_ret24 含 11h 前视, 故意保留供归因复现)—— 特征类实验必须显式传因果面板。**

## 不可违反约束 (Core Constraints)

1. **信号极弱 (R² < 1%)** — 容量必须匹配信号; 有效样本是一切, 任何"聚焦/加权/复杂化"先过样本算术。
2. **非平稳性** — 任何结论必须多日时序 walk-forward + 跨 regime 检查; 判据必须带最坏五分位(Q4)。
3. **预处理 > 架构; 机制 > 堆叠(用户硬约束)** — 每个组件必须有清晰作用机理 + 定量 gate; 禁止生硬堆叠。
4. **单资产代码只读** — 新代码在 `multi_asset/`; `src/` `configs/` 只 import 不改; `reg-arch-final` 冻结参考。
5. **Share data 只读** — 一律 mode="r", 绝不改/删。
6. **书行为改动 = 预注册 + 用户裁定**; 判据冻结先于看数字; 完成体动词必须有收据; 判决装置与结论同寿命(判官脚本当日入库)。

**决策检查清单**(每次架构/特征/loss 改动必答): 机制? Ridge/LGBM 前置门(ΔP≥+0.005 特征/+0.003 腿)? 复杂度预算? 泄漏(shuffle-future null + 偏移谱对齐)? OOS 逐折同号? σŷ/σy≥0.02?

**禁止**: 单日/单折结论; stride<horizon; 不过 Ridge 就上 DL; 多种子集成/训后技巧; 动单资产代码; 动 share data; 把 β 水平当质量门。

## Metric Discipline(全文见 MILESTONE §2 与旧版存档)

- **双口径必报**: avg per-asset Pearson + xsec rank-IC(+ Spearman); clean(stride≥600)与 dense 双给; **net-of-fee**。P/S 分歧=危险信号。
- **★ IC 是 alpha, β 是量纲**(β=r·σy/σŷ): alpha 判定唯一以 IC/rank-IC; β 水平可任意 rescale, 禁作质量门; β 合法角色仅 (a) 塌缩监视(真守卫是 σŷ/σy≥0.02) (b) 跨-regime 稳定性(看方差不看均值); 幅度靠事后校准, 不训进模型。
- **★ 口径三层**(2026-08-11 实测): 模型分数 IC / 复合新鲜目标 IC / 持仓书 IC 逐层差 20-25%, 引用必须声明层; 实盘 ic_monitor 测的是持仓书层。
- **★ 排序≠净额**(四例在案): 腿录取 S1 +0.003 是必要非充分, 必须过 S2 净额 G 族(Δ净@4.137 CI>0 且 @6.23≥0 且逐年≥4/5 且夏普不降)。

## Anti-Patterns

全谱见 `docs/SINGLE_ASSET_Y600_FINAL_MILESTONE_2026_05_20.md`(单资产 #1-#29)+ MILESTONE_2026-08-11 §2/§4(多资产)。**多资产日常最咬人的**: #29 通道税(每加 channel −0.013P, 除非 ≥+0.003 alpha); #24 σ-gate BEST checkpoint; 单日/单折验证; 泄漏安全(lead-lag ≤t + shuffle-future null + **锚→面板行偏移谱峰@0**); 单资产先验不整体迁移(引用失败必须带范围)。

## Documentation Discipline

所有 docs/notes 首行元信息: `> **创建:** … | **Session:** … | **状态:** … | **作废条件:** …`; 禁止 `_v2`/`_final` 后缀替代日期; 同主题多份必须 cross-reference; 预注册 SHA 先于数字入库。

## 路由表(重启任务 → 先读什么)

| 任务类型 | 参考 |
|---|---|
| 实盘状态/配置/在飞 | `STATE.md` §2/§3 |
| 恢复研究某条轴 | `docs/MILESTONE_2026-08-11.md` §2(关闭)§3(活口)§4(地雷) |
| 部署/回滚/电池 | `~/dl_quant_live/ops/safe_commit.sh` + `run_acceptance.sh` + `docs/RUNBOOK_deploy_batch1_2026-08-04.md` |
| 训练复现 | memory `champion_baseline_repro` + `eda/PREREG_retrain_causal_panel_2026-08-03.md` |
| 因子挖掘规范 | `docs/FACTOR_MINING_COMPLETE_SPEC.md` + 腿录取门 v2(#71) |
| 路线/日历 | `docs/ROADMAP_2026-08-06.md` |
| 长期记忆索引 | `~/.claude/projects/...quant-research/memory/MEMORY.md` |

## 当前进度

**本节不再滚动更新**(历史上它总是过期)。当前状态 = `STATE.md`; 阶段总账 = `docs/MILESTONE_2026-08-11.md`; 里程碑 tag: `milestone-2026-08-11`(双仓)。
