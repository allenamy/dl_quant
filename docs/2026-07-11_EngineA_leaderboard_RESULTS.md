# Engine A — paradigm-race LEADERBOARD (live results)

> **创建:** 2026-07-11 · **Session:** fable-regime-breakthrough (agent stage0C-d3-factors) · **状态:** final (0C 终判 2026-07-12 落地, 见 §终判) · **交叉引用:** pre-registration `docs/2026-07-11_EngineA_leaderboard_prereg.md` · 终判 `exports/eda/qim_final_verdict.{json,md}` (server) · tools `wideA_score.py` (5-col + dynamic split), `wideA_leakaudit.py`, `wide_null_calib.py`, `wide_fillcost.py`.

## ★★ 终判 (0C, 2026-07-12): CONDITIONAL GO — 王冠重贴标签

**信号真实、审计六查全清、可净成本交易；但 headline 归因修正: ~2× 边际来自去掉正交惩罚 (lam_orth 1.0→0)，pinball 头本身中性。** 机制配对 (3-fold, 同 panel md5): conformer_ref(K6, lam_orth=1.0)=0.0327 → **lamorth0(K6, lam_orth=0)=0.0672 (+105%, 每 fold 翻倍)** → qim(pinball)=0.0689 (vs lamorth0 +0.0017 = seed 噪声内)。⇒ stage2b 的 `lam_orth=1.0` 自 Engine A 启动以来把每个 K-head 臂的 IC 砍半；本表 xattn/aux-MTL/Conformer 行全部被系统性低估 ~2×。

**QIM 5 年扩张 walk-forward (airtight wide_dl_full):** 2022 +0.0443 / 2023 +0.0640 / 2024 +0.0697 / 2025 +0.0807 / 2026H1 +0.0774 — **五年全正, mean +0.0672, 动态占比 0.86-0.95 (mean 0.92, 无持久 tilt 灌水)**。IC-IR 16-29 = 每横截面 t-stat (~2000 ts/年), 不是 Sharpe。

**逐年净成本 (4h 再平衡 dollar-neutral rank-L/S, raw 收益, full-turnover):** break-even 4.9-16 bps/side; **maker/2.3bps 五年全 GO**; 5bps 4/5 (2026H1 打平); 9.5bps 仅 2024/25 存活。账面 Sharpe 8-19 是频率×breadth 无摩擦产物 — 诚实门是 BE per-side。重 EMA 抬 BE 至 15-27 但 Sharpe 塌到 2-3 (快信号不耐持有)。

**Seeds (同 3-fold 协议) {0.0689, 0.0652, 0.0781} CoV 7.5% — G2 PASS。** 六查: fold embargo 9d 零重叠 / member point-in-time 无幸存者 / YR⊥funding / honest ensemble / panel 字节一致 / "好得惊人"由扩张窗+breadth+口径解释。

**全 GO 条件:** (1) 5 年协议 lamorth0 确认跑 (已发, `--year_folds`; **fold0/2022 = +0.0423 vs QIM +0.0443, seed 噪声内咬合**); (2) 真实执行验证 → **✅ 完成 (0C, `exports/eda/qim_execution_feasibility.{json,md}`)**; (3) 偏好 ≥100 成员 regime (2024+), 薄宇宙年 (2022/2026) 是弱尾。

**执行可行性 (0C, 2026-07-12, 真实 QVOL: BTC $435M/h, 中位币 $1.5M/h, 底档 $0.63M/h):** 换手 1.66/4h (~41% gross/次), 平均持仓 6.4h。**容量是硬约束但只稀释不翻负** (小币欠配丢其 alpha, 大/中盘腿撑 Sharpe): maker 参与 x=1% 下 **起步 $5-10M gross** (保留 85-90% 无摩擦边际, net-Sh 7.8-8.8 @5bps), $25M 保留 ~63%, **$50-100M 软天花板**。容量杀手 = 小盘档拿 ~25% gross 但底档仅 $0.63M/h。小盘腿 fill 砍半几乎不动 Sharpe (执行鲁棒); maker 假设失败翻负阈值: 5bps 下需 ~100% 失败 (仅 2026 边缘), 9.5bps 下薄年容忍 52-69%。**硬 caveat: 未建模市场冲击/挂单逆选择/队列位置, 所有 AUM 按上界读 — 建议 $2-5M live maker-fill pilot 实测 fill-rate+slippage 再放大。**
**Tasking 教训 (0C flag):** battery 的 lamorth0/seed 步骤是 3-fold 非 5 年协议 — 3-fold mean 0.0672 与 5 年 mean 0.0672 相等纯属巧合; 严禁跨协议对标。

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
