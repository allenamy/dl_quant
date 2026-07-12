# Engine A — paradigm-race LEADERBOARD (live results)

> **创建:** 2026-07-11 · **Session:** fable-regime-breakthrough (agent stage0C-d3-factors) · **状态:** final (0C 终判 2026-07-12 落地, 见 §终判) · **交叉引用:** pre-registration `docs/2026-07-11_EngineA_leaderboard_prereg.md` · 终判 `exports/eda/qim_final_verdict.{json,md}` (server) · tools `wideA_score.py` (5-col + dynamic split), `wideA_leakaudit.py`, `wide_null_calib.py`, `wide_fillcost.py`.

## ★★★ 终判升级 (0C, 2026-07-12 二审): **GO (部署条件版)** — 机制五年闭环

**lamorth0_5yr 确认跑全表 + 逐年配对判 (per-ts 配对 + day-block bootstrap 3000×, 同 panel md5):** lamorth0 五年 +0.0423/+0.0637/+0.0737/+0.0639/+0.0775 (mean 0.0642) vs QIM 0.0672 — 4/5 年 seed 噪声内咬合; 两个 per-ts 显著年**方向相反** (2024 lamorth0 赢 / 2025 QIM 赢) = 年级拟合波动非系统架构边际。**★预测相似度仅 0.63: 两架构做实质不同的横截面下注却都到 ~0.065 ⇒ 水平由"去惩罚"解锁, 不系于头类型 — 机制 CLOSED。** 部署注: QIM 头 mean 微领先+已全审计=合理默认, 但机制等价, 勿包装"pinball 赢强 regime"叙事 (2024 反证)。**剩余条件 (部署级非研究阻断): (a) $2-5M live maker-fill pilot 实测参与率/slippage/逆选择; (b) ≥100 成员 regime 偏好。研究侧全闭环: GO。** 下一臂: lam_orth=0 + xattn 叠加 (已上 GPU, save_tag wideA_lamorth0_xattn)。

**★★ xattn 叠加臂 (lam_orth=0 + M3, 2026-07-12): 3-fold mean +0.0948 [.0718/.0988/.1138] = +41% over lamorth0 基线 — 0C 审计判词 REAL (待 5yr regime 确认)** (`exports/eda/xattn_stack_audit.{json,md}`): dyn-share 0.949 (非静态 tilt 灌水); 泄漏干净 (panel byte-identical + attention 同期跨币 member-mask ≤t 无跨时泄漏 + fold 边界 8d embargo); 配对 Δ +0.015/+0.023/+0.045 三 fold CI 全排除 0 且递增; pred 相似度 0.54 (实质不同下注)。**机制 2×2 (诚实 ensemble, 同 panel): orth=1/xattn=F 0.0327, orth=1/xattn=T 0.0408, orth=0/xattn=F 0.0672, orth=0/xattn=T 0.0948 — 正交惩罚把 xattn 贡献压制 ~3.4× (+0.008 带惩罚 vs +0.0276 去惩罚), 两 lever 协同。** ★caveat: 3-fold 测试期全在 2025 强 regime + 满 110 宇宙; +0.095 是强年数; **5yr replay (跑中, wideA_lamorth0_xattn_5yr) 确认弱年 (2022/2026) 不塌 = 加冕必需**; 弱年塌则降级为强-regime-only 杠杆。

**双实现 blend 评分卡 (0C, `exports/eda/qim_blend_score.{json,md}`, 预注册判据 PASS — 供用户部署决策, 非自动进部署):** QIM+lamorth0 各 per-ts z-score 后 50/50 value-blend (#16: value 非 rank): 逐年 .0458/.0693/.0787/.0793/.0810, **mean .0708 vs QIM .0672 (+.0036)**, 3/5 年配对显著优、无年显著变差, 动态占比 ~0.92。blend 在劈叉年吃两者之 best (经典 diversity-pair, 相关 0.63)。换手不升 (1.35-1.91 vs 1.5-1.83); **2026 (DL 最弱年) net@5bps 从 −0.13 救到 +1.65 = 薄年净成本转正**。政策定位: 理论有据 (diversity-pair) + 非 val-fit (固定 50/50) = 符合"生产期可考虑"; 代价 = 2× 推理。不采纳则单 QIM 已 GO, blend 存档备用。

## 终判一审存档 (0C, 2026-07-12): CONDITIONAL GO — 王冠重贴标签

**信号真实、审计六查全清、可净成本交易；但 headline 归因修正: ~2× 边际来自去掉正交惩罚 (lam_orth 1.0→0)，pinball 头本身中性。** 机制配对 (3-fold, 同 panel md5): conformer_ref(K6, lam_orth=1.0)=0.0327 → **lamorth0(K6, lam_orth=0)=0.0672 (+105%, 每 fold 翻倍)** → qim(pinball)=0.0689 (vs lamorth0 +0.0017 = seed 噪声内)。⇒ stage2b 的 `lam_orth=1.0` 自 Engine A 启动以来把每个 K-head 臂的 IC 砍半；本表 xattn/aux-MTL/Conformer 行全部被系统性低估 ~2×。

**QIM 5 年扩张 walk-forward (airtight wide_dl_full):** 2022 +0.0443 / 2023 +0.0640 / 2024 +0.0697 / 2025 +0.0807 / 2026H1 +0.0774 — **五年全正, mean +0.0672, 动态占比 0.86-0.95 (mean 0.92, 无持久 tilt 灌水)**。IC-IR 16-29 = 每横截面 t-stat (~2000 ts/年), 不是 Sharpe。

**逐年净成本 (4h 再平衡 dollar-neutral rank-L/S, raw 收益, full-turnover):** break-even 4.9-16 bps/side; **maker/2.3bps 五年全 GO**; 5bps 4/5 (2026H1 打平); 9.5bps 仅 2024/25 存活。账面 Sharpe 8-19 是频率×breadth 无摩擦产物 — 诚实门是 BE per-side。重 EMA 抬 BE 至 15-27 但 Sharpe 塌到 2-3 (快信号不耐持有)。

**Seeds (同 3-fold 协议) {0.0689, 0.0652, 0.0781} CoV 7.5% — G2 PASS。** 六查: fold embargo 9d 零重叠 / member point-in-time 无幸存者 / YR⊥funding / honest ensemble / panel 字节一致 / "好得惊人"由扩张窗+breadth+口径解释。

**全 GO 条件:** (1) 5 年协议 lamorth0 确认跑 (已发, `--year_folds`; **fold0/2022 = +0.0423 vs QIM +0.0443, seed 噪声内咬合**); (2) 真实执行验证 → **✅ 完成 (0C, `exports/eda/qim_execution_feasibility.{json,md}`)**; (3) 偏好 ≥100 成员 regime (2024+), 薄宇宙年 (2022/2026) 是弱尾。

**执行可行性 (0C, 2026-07-12, 真实 QVOL: BTC $435M/h, 中位币 $1.5M/h, 底档 $0.63M/h):** 换手 1.66/4h (~41% gross/次), 平均持仓 6.4h。**容量是硬约束但只稀释不翻负** (小币欠配丢其 alpha, 大/中盘腿撑 Sharpe): maker 参与 x=1% 下 **起步 $5-10M gross** (保留 85-90% 无摩擦边际, net-Sh 7.8-8.8 @5bps), $25M 保留 ~63%, **$50-100M 软天花板**。容量杀手 = 小盘档拿 ~25% gross 但底档仅 $0.63M/h。小盘腿 fill 砍半几乎不动 Sharpe (执行鲁棒); maker 假设失败翻负阈值: 5bps 下需 ~100% 失败 (仅 2026 边缘), 9.5bps 下薄年容忍 52-69%。**硬 caveat: 未建模市场冲击/挂单逆选择/队列位置, 所有 AUM 按上界读 — 建议 $2-5M live maker-fill pilot 实测 fill-rate+slippage 再放大。**
**Tasking 教训 (0C flag):** battery 的 lamorth0/seed 步骤是 3-fold 非 5 年协议 — 3-fold mean 0.0672 与 5 年 mean 0.0672 相等纯属巧合; 严禁跨协议对标。

**三腿组合装配 (0C, 2026-07-12, `exports/eda/book_assembly.{json,md}`, v2 全历史扩窗为准):** deployed 级 funding 书 (2020-2026) + SIZE 重建到 2026H1 → **多年联合窗 1362d (2022-08→2026-06, 含 DL 弱年)**。两两日 corr **近零到负**: funding↔DL 0.075 / funding↔SIZE −0.031 / **DL↔SIZE −0.152** (v1 的 +0.262 是 123d 假象) — 分散优秀。**领导权轮动**: 2022 SIZE 撑 / 2024 DL 撑 / 2025 DL+funding 撑 / **2026 funding+SIZE 撑弱 DL (DL 该年 −0.11, 组合仍 +2.07 = narrative 窗外确认)**。等风险组合 Sharpe 5.28 (信号级), 逐全年全正: 2023 +5.35 / 2024 +6.60 / 2025 +8.29 / 2026 +2.07。**终版权重 (v2 部分推翻 v1): DL 风险预算 0.35-0.40 (多年窗解除 regime 过拟合忧虑; 上限来自容量+2026 覆盖, 勿超 0.45; 冲击考虑偏下沿 0.35), funding/SIZE 各 ~0.30-0.325; 等风险 0.33 = 保守默认。** caveat: 全腿 Sharpe 信号级无摩擦; 2022 是 partial 联合年。**xattn 叠加预检: xattn↔QIM 逐年 xsec rank corr 均值 ~0.42 (0.28-0.51) — 非冗余, attention 做实质不同的横截面下注 ⇒ "lam_orth=0 + xattn" 臂值一个 GPU 槽, 确认跑后排。**

**Race metric = shuffle-future-adjusted DYNAMIC IC** (excludes static cross-sectional tilt so paradigms compete on genuine timing skill). Headline = the 6-head equal-risk ENSEMBLE (no per-fold-best selection bias). Net-cost at REALISTIC wide-book cost {2.3 mega / 5.0 mega+mid-capped / 9.5 full-book} bps, EMA-hold operating point (the wide book is mid+small-cap, not mega). All on ≥4h-CL × MEMBER110, target YR4 (=incremental-over-[funding+zoo] by construction).

## Standings

| rank | arm | naive IC | **DYNAMIC IC** (z) | static tilt | gate-d per-fold (sign) | net-Sh @2.3/5.0/9.5 | persist | verdict |
|---|---|---|---|---|---|---|---|---|
| **1** | **★ QIM q50** (single pinball head) | +0.0704 | **+0.0601** (24.4) | +0.0103 | [.054/.069/**.088**]↑ ✓ | **+8.32 / +5.08 / +2.60** | 0.66 | ★★ **PARADIGM-SHIFT LEADER** — 2× the field, leak-free, folds *increasing*; pending lam_orth=0 confirm + 3-seed |
| 2 | xattn (cross-asset attn) | +0.0408 | +0.0313 (13.6) | +0.0094 | [.035/.040/.048] ✓ | +2.04 / +1.81 / +1.42 | 0.77 | strong (best K-head arm) |
| 3 | aux-MTL (1h/24h aux) | +0.0348 | +0.0271 (12.1) | +0.0077 | [.027/.037/.041] ✓ | +2.36 / +2.15 / +1.81 | 0.73 | above bar (aux supervision helps) |
| 4 | Conformer (M0 paradigm) | +0.0312 | +0.0245 (11.1) | +0.0068 | [.033/.031/.030] ✓ | +1.66 / +1.39 / +0.95 | 0.66 | REFERENCE BAR |
| — | pred-smooth λ0.3 | +0.0151 | +0.0130 (4.9) | +0.0021 | [.005/.006/.034] ✓ | +0.46 / −0.36 / −0.99 | 0.75 | REJECT (below bar + net-negative) |
| — | IPCA resmom_24h (K=3 best) | +0.0059 | n/a (factor) z3.0 | — | [.008/.009/**.001**] | (tiny IC) | — | REJECT — DECAYING (fold-2→~0) + residual-only fragile |

★★ **QIM = the finding of the race.** A single unconstrained 25-quantile pinball head (q50) scores DYNAMIC +0.0601 — **~2× the best K-head orthogonality arm (xattn +0.0313)** — leak-free (shuffle-future z24.4), net-cost ~3× the field (+5.08 @5bps), and per-fold *increasing* (not decaying). Both QIM heads beat the field (imean +0.0573 dyn), so it's the **single-distributional-head-on-residual approach** that's the lever, not q50 specifically. **Mechanism (0B's hypothesis): the K-head `lam_orth=1.0` orthogonality penalty dilutes the signal ~2×** — forcing 6 heads apart costs alpha; an unconstrained head captures it. ★ DECISIVE CONFIRM PENDING: a K-head run with `lam_orth=0` — if it recovers ~+0.06, the orthogonality-dilution mechanism is proven and the paradigm is "drop K-head orthogonality, use a distributional point head"; if it stays ~+0.03, QIM's edge is the pinball loss itself. Plus 3-seed robustness before crowning.

## Read

- ★ **The wide-universe multi-head DL is a real positive** — not the paradigm-null. Both Conformer and xattn add leak-free, net-cost-tradeable (at realistic wide-book cost, EMA-held, mega+mid-capped) incremental timing alpha over [funding+zoo].
- ★ **xattn (cross-asset attention) leads** — dynamic +0.0313, 28% over the Conformer bar, net-cost better at every tier, gate-d clean and *increasing* across folds. Cross-sectional structure across the 140-coin universe is exploitable signal beyond a per-asset temporal backbone.
- **pred-smooth λ0.3 validates the dynamic metric:** its naive +0.0151 hides a weak dynamic (+0.0130, below the bar) and it's net-NEGATIVE at realistic cost. The pred-smoothing dispersed the 6 heads (2 went negative), dragging the ensemble — not a timing lever (0B predicted this). Its static tilt is tiny, so the failure is dispersion, not static-inflation.
- **Selection-bias note:** per-fold-best-head numbers (e.g. pred-smooth 0.0338) overstate; the ENSEMBLE is the honest, deployable, comparable metric.

## Gates (pre-registered, all arms scored identically)

null-z ≥ 2.5 (IC ≥ 0.0047 at N≈110; FWER z ≥ 3.0 for the winner) · gate-d walk-forward ΔIC ≥ +0.003 + per-fold sign-consistent · no-temporal-leak (shuffle-future dyn-z ≥ 5) · fill-window (4h ≫ 5min; persistence-confirmed slow) · net-cost > 0 at realistic wide-book cost. Winner also gets: full independent leak-audit + 3-seed confirm before any deploy claim.

## Next

Remaining arms (IPCA / QIM / aux-MTL) must beat **xattn's dynamic +0.0313** to lead. If none does, xattn is the paradigm winner (pending its leak-audit + 3-seed). If no arm beat the Conformer, the read would have been "Conformer sufficient" — but xattn already cleared it, so cross-asset attention is the paradigm lever so far.
