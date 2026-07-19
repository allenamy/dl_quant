# Engine (shadow pipeline v1) — READ THIS BEFORE THE SHARPE TABLE

> **创建:** 2026-07-15 JST | **Session:** fable multi-asset-v2 (0B) | **状态:** v1 final | **作废条件:** 引擎组件/腿构成/权重变更, 或叠入 maker-fill 执行栈后重估
> 复核: 0C `exports/eda/engine_replay_review.md`. 输出: `exports/eda/engine_fullhist_replay.json` (canonical) + `_calibrated.json` (变体).

## ⚠️ 定位判词 (0C, 2026-07-15) — 结构口径 ≠ 部署净值

任何人看到本引擎的 Sharpe 表, **必须先读这一段**:

> **"引擎全历史 Sharpe 是结构口径 (frictionless — 除 1.9bps 显性成本, 日频×√365, 市场中性), 是信号质量的上界, 不是部署净值 Sharpe。部署口径需叠 maker-fill 执行栈 (tick-验证的逆选择 markout: 平静 −1 / 压力 −3.2 / 崩盘 −5.3 bps、fill-rate<1、排队、冲击、容量), 会实质折损。对标业界时对标研究/信号级 Sharpe, 不对标扣全成本的基金净值 Sharpe。"**

**这张表不含**: maker-fill 滑点、逆选择、排队、市场冲击、容量约束。它是 **信号质量上界**, 部署净 Sharpe 会显著更低。

> **v1 更新 (2026-07-15):** 0C 原判词有一句 "该 Sharpe 重度依赖 C5 对 funding 腿的方差控制" —— **v1 已解除该依赖**: funding 腿改 **rank 加权** (天然有界, 单名 ≤0.05), C5 在 rank 下 **完全冗余** (on/off 逐格 bit-identical)。结构口径警告本身不变。

## 当前出货表 (canonical = rank-funding + C6 4h-sync + shaping='cap')

| 年 | 交易日 | gross Sharpe | net-of-cost Sharpe | rank-IC |
|---|---|---|---|---|
| 2022 | 365 | 11.82 | 9.64 | 0.0616 |
| 2023 | 365 | 14.18 | 11.77 | 0.0859 |
| 2024 | 366 | 14.44 | 12.55 | 0.0805 |
| 2025 | 365 | 18.70 | 16.04 | 0.0764 |
| 2026H1 | 180 | 13.74 | 11.05 | 0.0622 |
| **avg net** | | | **12.21** | |

netting: hedge 12.4% / gross-turn 857 / net-turn 751 / **savings 202.3 bps/yr**. funding 单名集中 max 0.049, FTX funding-leg max-abs 1.0 (rank 天然有界). **再次强调: 结构口径上界, 非部署净值。**

**部署-已校准变体 (rank + shaping='calibrated', isotonic C3 on):** avg net **10.84** ([9.64/9.98/10.93/15.57/8.07]), hedge 17.4% / savings 283.9 bps/yr → `engine_fullhist_replay_calibrated.json`。isotonic 的**合法角色 = 部署 Kelly / 净成本门需要真实 E[bps]**; 代价 **−1.3 avg Sharpe** (0C: isotonic 在此稀疏尾信号是**净负重塑** —— 尾饱和压平高信念仓位, 砍均值不砍波动, 连前视 oracle 版都低于 cap-only)。**结构 headline 用 cap-only; 需要标定幅度时用此变体, 代价明示。**

## 组件图 (C1–C6)

| | 文件 | 作用 |
|---|---|---|
| C1 | `signal_chain.py` | 4 腿 L1 子组合 → 组合 → (可选 C3 校准) → 尾 cap → 市场中性目标仓位 |
| C2 | `vol_gate.py` | **执行战术 only** (exposure_mult 钉死 1.0 — 书是危机受益者, 不去杠杆); 高 rvol → 加宽报价/减小切片/更耐心 |
| C3 | `isotonic_calib.py` | 单调 isotonic 校准到 E[bps]; **非 canonical** (net-negative), 仅部署-已校准变体用 (Kelly/净成本门) |
| C4 | `ic_monitor.py` | 滚动 rank-IC 衰减告警 + champion/challenger 切换桩 (retrain hook, 未实装重训) |
| C5 | `funding_risk.py` | funding 腿风控。**rank 加权下三者皆 no-op → 当前 inert; z-mode 下为保险** (见下) |
| C6 | `netting.py` | 4h-sync 跨腿净额, 只交易 Δnet。**4h-sync = 部署规格** (口径出处见 netting.py docstring) |

驱动: `panel_source.py` → `replay_fullhist.py` (`run_replay(funding_mode, use_c5, shaping)`, 可 import).

## v1 三项校正 (0C 复核队列, 2026-07-15)

**1. shaping 接入 P&L 路径 + isotonic 误归因更正.** 0C 发现 `netting.run` 直接用 `leg_signals`, 从不过 `target_position` → C3/尾cap 对回放零影响。v1: netting 每个净额 book 现走 `chain.shape_position()`, 并 **renorm 回未校准 book gross** (恒定敞口, 契合 vol-gate 不调 exposure; no-shaping 极限精确复现基线, rank-IC bit-identical)。
- **★ 误归因更正 (0C):** 我先前报的 "+1.3 来自 isotonic" 是错的 —— 那实际是 **z-mode 的 99% pos-cap 在削离群** (干 C5 的活)。**isotonic 本身是 −1.3** (稀疏尾饱和, 砍均值不砍波动, oracle 前视版亦低于 cap-only = 重塑本身净负, 非漂移)。rank 下离群已消 → **cap 近免费, isotonic 只剩代价**。
- **⇒ canonical 只留 cap, isotonic 单列部署-已校准变体** (见上)。cap-only 下 rank-IC 反而更高 (2023 0.0859 vs iso 版 0.0756), 佐证 isotonic 在压信号。

**2. funding 腿 z → rank 加权 (canonical).** z+L1 无界 → 单名集中 0.49。2×2 (z/rank × C5 on/off, cap 口径, `exp_funding_weighting.py` → `engine_funding_weighting_2x2.json`):

| cell | 单名集中 max | FTX \|max\| | hedge% | avg net Sharpe |
|---|---|---|---|---|
| z + C5on | 0.176 | 4.00 | 12.2 | 8.82 |
| z + C5off | **0.490** | 6.70 | 10.3 | 8.52 |
| rank + C5on | **0.049** | 1.00 | 12.4 | **12.21** |
| rank + C5off | 0.049 | 1.00 | 12.4 | 12.21 |

- **★ rank + C5on ≡ rank + C5off (逐格 bit-identical).** rank 天然有界 → winsor(±4)/name-cap(0.15) 皆 no-op; 分散度门 shrink 被腿内 L1 **抵消** → **C5 在 rank 下完全冗余**。
- rank 单名 0.049 (z 的 ~1/10)、FTX 尾天然 1.0、avg Sharpe 更高 (12.21 vs z 8.82, 主升在 2022 分散度尖峰年: z 过押单名, rank 摊平)、rank-IC 亦升。**与 book_assembly 的 raw-funding 因子 corr 仅 0.213 = 不同因子 (对 funding_ema 腿的真实改进, 非 revert), 尾部共险 rank 版保留 (0C 加冕)。**
- **C5 判词: rank 下 inert (bit-identical, 保留接线); z-mode 下为保险** (无界 z 需 winsor/name-cap 才可交易 —— 但 canonical 是 rank, 故 C5 当前不激活)。若 funding 改回无界 z, C5 自动复活为必需卫生。

**3. C6 口径 = 部署规格 (无代码改动).** 0C 裁定 4h-sync cadence-hold 为部署规格, supersede 代理面板估计 (86–179 bps/yr / 5–8%, 不同的非出货 funding/size 构造)。**出货数 (canonical rank+cap) = 12.4% hedge / 202.3 bps/yr** (校准变体 17.4% / 283.9)。口径出处见 `netting.py` 顶部 docstring。

## C5-owner 待办 (归档, 未实装)

**分散度门 (C5-iii) 在 rank 加权下被腿内 L1 抵消 → 零风控作用** (shrink 常数被归一消掉)。若要它在 rank 下真起效, 作用点须从 **腿内标量** 改到 **book 权重层** (高 funding 分散日降 `w[funding]` 在书中的占比, 而非缩放腿内)。属 C5-owner 设计决策, **v1 不实装**。

## 复现

```
python engine/replay_fullhist.py --funding_mode rank --shaping cap          # canonical 出货表 (12.21)
python engine/replay_fullhist.py --funding_mode rank --shaping calibrated   # 部署-已校准变体 (10.84)
python engine/replay_fullhist.py --funding_mode z --shaping none            # 校准: 复现 0C z 基线 (rank-IC bit-identical)
python engine/exp_funding_weighting.py                                      # funding 加权 2×2 (cap 口径)
python engine/tests/test_c2c3.py && python engine/tests/test_c1c4.py        # C1–C4 组件测试
```

产物: `engine_fullhist_replay.json` (canonical rank+cap), `engine_fullhist_replay_calibrated.json` (isotonic 变体), `engine_fullhist_replay_zbaseline_prev.json` (0C 复核的旧 z 表), `engine_funding_weighting_2x2.json`.

## 诚实边界 (再述)

结构口径上界。部署需叠 maker-fill 执行栈 (逆选择/fill-rate/排队/冲击/容量) → 净 Sharpe 实质折损。C4 retrain 未实装 (仅 hook)。real-time 模式为 stub。**对标研究/信号级 Sharpe, 不对标扣全成本基金净值。**
