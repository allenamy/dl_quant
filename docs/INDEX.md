> **创建:** 2026-08-03 14:1x UTC | **Session:** team-lead (6737834a) | **状态:** living — 每次新增里程碑文档时追加一行 | **作废条件:** 无(索引不作废, 只补充)

# docs/ 索引 —— 脉络地图

**为什么存在:** 44 份文档横跨 2026-04 → 08 四个阶段。**一份都没有被删除 —— 它们是脉络本身。** 但没有索引的时候, 一个新会话无法区分"当前有效"与"历史记录", 于是要么全读(读不完), 要么读到过期的当成当前(今天发生过两次)。

**读法: 先读 `STATE.md`(当前快照) → 再按需从本索引取历史。**

---

## 0. 常读(与阶段无关)

| 文档 | 是什么 |
|---|---|
| `../STATE.md` | **当前状态唯一真相源** —— 任何判断之前先读 |
| **`MILESTONE_2026-08-11.md`** | **★阶段总账(在版里程碑锚)**: 在役栈 / 13 条已关闭轴索引 / 活口 / 地雷路由 / 基建地图 —— **恢复任何研究轴先查它** |
| `TEAM_PROTOCOL.md` | 协作规则(完成必须声明 / 具名 owner / 交错处置 / 引用前打开看) |
| `../CLAUDE.md` | 项目宪法(2026-08-12 已路由化): 硬约束 + 任务类型→文档路由表 |
| `2026-07-06_SINGLE_ASSET_PERP_Y600_CLOSEOUT.md` | **单资产权威终版**(Run1 双盘口 REG_arch, 诚实 P≈0.049, maker-only); 05-20 milestone 为历史基线(其 0.0646/4.4 已更正) |
| `PROJECT_PRINCIPLES.md` · `METRIC_DISCIPLINE.md` | 七条操作原则 · 双口径指标纪律 |
| `DATA_RESTORE.md` | 本机数据治理与恢复手册(含"绝对不得清理"反向清单) |

## 1. 当前阶段 — 实盘试点 P0 (2026-07-25 →)

| 文档 | 是什么 |
|---|---|
| `2026-07-25_live_deployment_feasibility.md` | 上线可行性评估 |
| `2026-07-27_FACTOR_MINING_COMPLETE_SPEC.md` | 因子挖掘阶段的完整规格与结题 |
| `server_verdicts_shadow_launch_review.md` | 影子期上线前的裁定汇总 |
| `crypto_4h_long_short_strategy_optimization.md` | **外部评审框架**(2026-08-03 用户提供), 逐项裁定见 journal |
| **每日历史** | `../multi_asset/exports/live/pilot_journal/JOURNAL_<date>_*.md` —— **只追加**, 事实/裁定/在飞/门 四类分开 |
| **审计交接** | `../multi_asset/exports/eda/HANDOFF_lookahead_audit_2026-08-03.md` |

## 2. 多资产 v2 / 因子挖掘 (2026-07)

`2026-07-06_MULTI_ASSET_V2_KICKOFF` · `2026-07-07_midfreq_factor_research_catalog` · `2026-07-08_multi_asset_v2_portfolio_scorecard` · `2026-07-09_DLv2_acceptance_protocol_prereg` · `2026-07-09_DLv2_design_review` · `2026-07-09_M0_fullhistory_replay_prereg` · `2026-07-11_EngineA_leaderboard_prereg` / `_RESULTS` · `2026-07-11_v3_paradigm_research_top5` · `2026-07-12_ENGINE_A_FINAL_MILESTONE` · `2026-07-14_crossasset_dualarm_technical_design` · `2026-07-14_frontier_v4_research_and_dualarm_design` · `2026-07-15_PROJECT_COMPLETE_PRIMER` · `2026-07-25_SG_self_research_guide` · `2026-07-12_disk_cleanup_manifest`(上一次磁盘治理的先例)

## 3. Regime / 双源永续 (2026-06 → 07)

`2026-07-02_fable_regime_breakthrough` · `2026-07-02_phase1_findings_appendix` · `2026-07-02_phase2_design_appendix` · `2026-07-04_causal_router_spec` · `2026-07-05_FINAL_deliverable_regime_breakthrough` · `2026-07-06_run1_production_export_metrics` · `dual_source_perp_REFERENCE_2026_06_24` · `v2_autonomous_overnight_2026_06_24` · `PERP_SINGLE_TARGET_PARADIGM_2026-06-24`

## 4. 多资产 v1 / 单资产结题 (2026-05 → 06)

`MULTI_ASSET_Y180_CONCLUDED_MILESTONE_2026_06_15` · `2026-06-28_FINAL_y600_deliverable` · `2026-07-06_SINGLE_ASSET_PERP_Y600_CLOSEOUT` · **`SINGLE_ASSET_Y600_FINAL_MILESTONE_2026_05_20`**(★ 反模式清单的出处, CLAUDE.md 引它)

## 5. 单资产 V4/V5 时代 (2026-04 → 05)

`V4_MODEL_AUDIT` · `V5_BACKBONE_AUDIT` · `V5_TO_PRODUCTION_ITERATION_2026_05_15` · `Y600_V5_SINGH_ALPHA0_HUBER_DESIGN` · `PHASE_A_FINDINGS` · `PHASE_B_OVERNIGHT_REPORT_2026_05_06` · `HORIZON_DECISION` · `PROJECT_OVERVIEW`

---

## ★ 使用这份索引的一条纪律

**这份索引会过期, 而它自己看不出来。** 引用其中任何一份为"当前有效"之前, **打开它读首行的状态与作废条件** —— 2026-08-03 两次事故都源于把一份过期文档当权威(一次是交接指向停在 2 小时前的 journal, 一次是把首行写着 `SUPERSEDED` 的复现指南派给了执行会话)。**索引给的是位置, 不是时效。**
