# DL Quant — Multi-Asset Track — Project Guidance

> **Phase:** 宽宇宙实盘阶段(真钱, 2026-08-26 起在役书 = **combo**: 去rev24 ∧ king 55/45 混 V2MAIN)。**阶段总账: `docs/MILESTONE_2026-08-26.md`**(上期 `docs/MILESTONE_2026-08-11.md`; 单资产终版 `docs/2026-07-06_SINGLE_ASSET_PERP_Y600_CLOSEOUT.md`)。
> **重启任何任务先读它对应小节; 引用"已关闭/DO-NOT-RETRY"必须带受据文档。**

## ★ 会话起步必读(顺序固定)
1. **`STATE.md`(仓库根)** — 当前状态唯一真相源(在役链路/在飞/待裁定/口径纪律)。**先读它, 不信任何更早轮次的摘要, 包括自己的。**
2. **`docs/TEAM_PROTOCOL.md`** — 协作规则(完成必须声明+收据/具名 owner/引用前打开看/落盘即上线)。
3. **`docs/MILESTONE_2026-08-26.md`** — 关闭轴/翻转对账/活口/基建地图。
4. 历史脉络: `multi_asset/exports/live/pilot_journal/`(只追加)+ `docs/ERROR_LEDGER_2026-08-20.md`。

## 项目身份
**Binance USDT-perp 宽宇宙中频市场中性**: 宇宙 450 币, 4h 锚(00/04/08/12/16/20Z), maker-only, gross 1.5×NAV。
**在役书 = combo**(构成 ≈77% funding 动量 + 13% king LGBM + 10% V2MAIN 书损失 DL): 生产者 `~/wide_shadow`(非 git, 快照入研究仓)写 king 文件 → combo_stage 重写 target_live(五层安全, 失败自动回滚 king 形态)→ 执行器 `~/dl_quant_live`(git, **改动只经 `ops/safe_commit.sh` + 电池全绿**)N+23 读取交易。
**数据**: share 面板 READ-ONLY(mode="r"); 宽面板/判官在 jpline `/mnt/storage/private/work_hsy/`; GPU/LOB 在 pod2 `/workspace/`。**★ 面板默认值陷阱: `engine/panel_source.py` 默认=as-trained 脏面板 — 特征类实验必须显式传因果面板。**

## 不可违反约束 (Core Constraints)
1. **信号极弱 (R²<1%)** — 容量匹配信号; 有效样本是一切; 任何聚焦/加权/复杂化先过样本算术。
2. **非平稳性** — 结论必须多年 walk-forward + 跨 regime + 最坏五分位(Q4)。
3. **预处理 > 架构; 机制 > 堆叠(用户硬约束)** — 组件必有机理 + 定量 gate。
4. **单资产代码只读**(`src/` `configs/` 只 import); **share data 只读**。
5. **书行为改动 = 预注册 + 用户裁定**; 判据冻结先于看数字; 完成体动词必须有收据; 判决装置与结论同寿命(判官脚本当日入库, 训练脚本随产物存档)。
6. **复现纪律**(E-0826 族): 枚举 env 白名单断言; 装置自报 config 且写进产物; **复跑命令逐字抄转录**; 多种子先断言 self_sha256 同; 服务端与训练逐算子同序; 工件当输入前开产它的代码。

**决策检查清单**(架构/特征/loss 改动必答): 机制? 前置门(Ridge/LGBM)? 复杂度预算? 泄漏(shuffle-future + 偏移谱峰@0 + 折外泄出=0)? OOS 逐折同号? σŷ/σy≥0.02?

## Metric Discipline(全文 MILESTONE_2026-08-11 §2)
- **一律简单收益口径**(expm1); 对数口径只作诊断并显式标注。双口径必报(per-asset P + xsec rank-IC), net-of-fee, clean+dense。
- **IC 是 alpha, β 是量纲**: β 禁作质量门; 塌缩守卫=σŷ/σy。**口径三层**(模型分数/复合目标/持仓书, 逐层差 20-25%)引用必须声明层。
- **排序≠净额**(五例在案): 分数层录取必要非充分, 必须过书层净额 CI。

## Anti-Patterns(最咬人的; 全谱见两期 milestone + ERROR_LEDGER)
#29 通道税(每加 channel −0.013P 除非 ≥+0.003 alpha); 单日/单折结论; stride<horizon; 多种子集成/训后技巧(用户禁); **CAL/口径旗标凭记忆**(E-0826-C); **复跑漏 env**(E-0826-D); **sha 推断代替复跑实测**(E-0826-B); 按文件名/目录名推断语义(E-0825-H/G); 声明"上线"须验运行中进程(E-0825-F); 新结论与既有受据反向先对账。

## Documentation Discipline
docs 首行元信息 `> **创建:** … | **Session:** … | **状态:** … | **作废条件:** …`; 禁 `_v2/_final` 后缀替代日期; 同主题 cross-reference; 预注册 SHA 先于数字。

## 路由表(重启任务 → 先读什么)
| 任务 | 参考 |
|---|---|
| 实盘状态/链路/回滚/在飞 | `STATE.md` |
| 在役书证据/杠杆/局限 | `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md` |
| 换装工程/组件/校验 | `docs/CHECKLIST_combo_switch_2026-08-26.md` |
| 恢复研究某条轴 / DNR | `docs/MILESTONE_2026-08-26.md` §2/§5(08-11 前的查上期) |
| 判决翻转案例/装置纪律 | `docs/PREREG_leg_ablation_2026-08-26.md` RECONCILIATION + `docs/ERROR_LEDGER_2026-08-20.md` |
| 部署/回滚/电池 | `~/dl_quant_live/ops/safe_commit.sh` + `run_acceptance.sh` |
| 月度重训 | `docs/RUNBOOK_monthly_retrain_2026-09.md` |
| 长期记忆索引 | `~/.claude/projects/...quant-research/memory/MEMORY.md` |

## 当前进度
本节不滚动。当前状态=`STATE.md`; 总账=`docs/MILESTONE_2026-08-26.md`; tag: `milestone-2026-08-26`(双仓)。
