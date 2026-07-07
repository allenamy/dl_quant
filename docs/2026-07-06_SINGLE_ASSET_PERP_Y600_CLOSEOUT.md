# 单资产 BTCUSDT 永续 y_600 — 阶段性收口里程碑

> **创建:** 2026-07-06 | **状态:** final (阶段性完成,收口) | **作废条件:** 被盘外数据/事件时间采样的新突破取代
> **交叉引用:** `docs/2026-07-05_FINAL_deliverable_regime_breakthrough.md`(最终交付) · `docs/2026-07-02_fable_regime_breakthrough.md`(滚动全记录) · `docs/2026-07-06_run1_production_export_metrics.md`(指标成绩单) · memory: `taker_tradeability_y600_2026_07_05` / `arch_iter_concat_tailw_killed` · `CLAUDE.md`(IC/β 铁律)

## 0. 一句话收口

**单资产 BTC 永续 y_600 阶段性完成。最佳可部署模型 = Run1(双盘口 REG_arch + 修 bug),真实、强显著、经济上明显胜生产,但是 maker-only 弱信号(≤0.76 bps/side);目标 per-month Pearson ≥0.08 全 regime 在盘上数据里证明不可达。全程无泄漏,关键结论双人独立验证。on-disk 杠杆穷尽。**

## 1. 成果（可交付、已冻结保留）

| 项 | 内容 | 路径 |
|---|---|---|
| **最佳模型** | Run1 bugfix, 10 月 walk-forward OOS | `configs/d1gate/d1_*_run1.json` · `multi_asset/model/dual_lob_regarch.py` |
| **生产预测** | 130,698 行, 2025-08→2026-05, raw-y | `exports/run1_production_preds_from_2025_08.csv` (+README) |
| **指标成绩单** | Pearson/Spearman/R²/DirAcc/bin-mono, 双人验证 | `docs/2026-07-06_run1_production_export_metrics.md` |
| **净成本回测** | taker/maker + 尾部扫描, 双人审计 CLEAN | `multi_asset/eval/taker_backtest.py` |
| **诚实评分器** | raw-y per-day-CLEAN, gate 纪律 | `multi_asset/eval/guard_fold_scorer.py` |
| **日内自评部署层** | 上午命中→下午仓位, 正交增益 | `multi_asset/eval/intraday_scaler.py` |
| **参考包** | 核心代码+架构+方法论, 供多资产 | `run1_reference_package.tar.gz`(已交付) |

## 2. 核心结论（全部经得起推敲、双人验证）

1. **模型**: Run1 是稳态最优单模型。路由/state/LoRA/combo/rank/basis 全部样本外不稳健胜它。**Run1 pooled cd-CLEAN raw-y ≈ +0.049**(Pearson +0.0487 / Spearman +0.0572), 决定性胜生产。
2. **目标**: **0.08-全 regime 盘上不可达** —— 穷尽架构/特征/损失/融合/路由/basis + DL 测过。大多月 cd 0.02-0.06, 只强月近 0.08。R²~0(信息在 rank/sign)。
3. **可交易**: **maker-only(盈亏平衡 ≤0.76 bps/side, 好费率档), 非 taker(尾部扫描 + bootstrap 定死), 非零售 maker**。强月最肥、drift 死。milestone 旧数(retail-maker 4.4/taker 2.8)是强月+clip+低费灌水构造, 已修正。
4. **架构/损失迭代(2026-07-06)**: concat 融合 + 尾部加权损失两个候选都 KILL 强月(−0.029) → **Run1 的加法残差 + 均衡损失是弱信号稳态最优**。共同签名: dense/幅度升但 per-day-CLEAN(交易口径)退。
5. **方法论(固化 CLAUDE.md)**: **IC 是 alpha / β 是量纲**(别追 β 别当质量门); **deploy-demean 低估持续方向 alpha**(用净成本回测判可交易); **口径纪律**(clean vs dense, clip 陷阱, raw-y 成绩单)。

## 3. 已穷尽的杠杆（避免重测）

架构容量(深/宽/长上下文/multi-scale)、永续 concat 融合、尾部/幅度损失重加权、rank 输入归一、basis-dynamics+RevIN旁路(DL)、因果 regime 路由、state/gain FiLM、LoRA 换弹法、目标 demean 对齐/aux、选择器 —— **全部样本外证伪或伤强月**。

## 4. 未验证的真杠杆（下一阶段候选,均需盘外/重建）

1. **事件时间采样**(volume/event bars) —— 机理对症(信号住成交爆发处), 需重建缓存管线。
2. **盘外正交数据**(更细 funding/OI/liquidations) —— 历史多次指向"0.06+ 需盘外数据"。

## 5. 收口决定

**单资产阶段性完成、冻结保留。** 转多资产工作(新分支)。单资产的**方法论 + 评估工具 + Run1 底盘**可复用于多资产(见 `run1_reference_package`)。
