# PREREG — r10 screen: COINT_PAIR (pair-local cointegration, state-dependent holding)

> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 冻结于任何结果数字之前 | **作废条件:** 判据在看到数字后被改动

## 0. 口径锁
v4 chain 2026-09-09 (`CALIBER_PIN_v4_2026-09-11.md`). 统计量 `g = net_ex/gross_total`, bps/4h锚/单位gross.
Post-warm 丢前 900 个 device 锚 (E-0911-A); 截止 2026-08-30 20Z (E-0911-D). n=9138 轴.
成本 = 固定 `costb_PWR_G230k.json` (sha16 295b4e7b462373e4) 三档 blended.
UTC 日块自举 2000 次, `numpy.default_rng([20260905,k])`.
**E-0826-D ENV 白名单 = 空集**, 所有装置 import 后即封 `os.environ.get`.

## 1. 候选定义 (冻结)
- **价格代理 (因果)**: `p[t,i] = Σ_{s<t} y4[s,i]`。y4[t] 覆盖 [E_t+5m, E_t+4h+5m); 在 E_t+5m 建仓时 y4[..t-1] 已实现 ⇒ 严格因果, stride = horizon = 1 锚。**不施 expm1** (E-0904-F)。
- **宇宙**: `meta.members[t]` ∩ CRYPTO m1 umask — 与在役 device 同一成员合同。
- **配对形成 (因果, 滚动)**: 每 `REBAL=180` 锚 (30天) 一次, 形成窗 = 之前 `L=1080` 锚 (180天), **严格早于**交易窗。合格名 = 形成窗内 y4 有限率 ≥95% 且在 t0 为成员。
- **配对打分**: Engle–Granger 两步。去均值 p 上 OLS `b = <p_i,p_j>/<p_j,p_j>`, 残差 `r = p_i − b·p_j`, 对 r 做无截距 DF 回归 `Δr_t = ρ·r_{t−1}+e`, 报 t 统计量。全部 N×N 向量化, **全部合格对都搜, 搜索数逐次记录**。
- **录取约束 (冻结)**: `b ∈ [0.2, 5.0]`; 半衰期 `−ln2/ln(1+ρ) ∈ [2, 60]` 锚; DF t ≤ −3.5; `sd(r) ≥ 0.005`; 每个名字最多进 2 对; 按 t 统计量取前 `K=40` 对。
- **状态相关持有规则 (冻结)**: `z[t] = (r[t] − μ_form)/σ_form` (μ,σ **只来自形成窗**)。
  空仓 → `z ≤ −2.0` 做多价差 / `z ≥ +2.0` 做空价差。持仓 → 满足任一即平: `|z| ≤ 0.5`; z 反号过 0; `|z| ≥ 4.0` (止损); 持有 ≥ 42 锚 (7天); 交易窗结束。
- **权重**: 每对占一个 slot, `w_i += s/(1+b)`, `w_j += −s·b/(1+b)`; 除以 `KMAX=40` ⇒ 分配资本 = 1, `gross_total[t] = n_active[t]/40 ≤ 1`。
- **记账**: 与 device 逐行同式 — `pnl = Σ w_i·y4_i·1e4`; `carry = Σ w_i·f_fund_now_i·(4/f_fund_iv_i)·1e4`; `cost = Σ |Δw_i|·rate(tier_i)`, tier 由 `qv4h = expm1(clip(qvk,0,30))*48` 分档; `net = pnl − carry − cost`。**该式已由 r9_screen/s2_cohort.py 对 A0 逐项复现 (carry maxabs 1.5e-7, cost 2.5e-8, gross 7.4e-9)**, 本轮自行复跑同一恒等式。

## 2. 主序列
`g_alloc[t] = net[t] / 1` (每单位**分配**资本), 空仓锚 = 0 —— 这是一笔资本配置真正拿到的东西。
副报 `g_book[t] = net[t]/gross_total[t]` (只在 active 锚) 与部署率。Sharpe 对两者相同 (常数缩放不变)。

## 3. 判据 (冻结, 先于数字)
| 门 | 阈 | 杀 |
|---|---|---|
| **G1 因果** | 偏移谱 peak 必须在 lag 0, 且 lag<0 侧无峰 | 任一负 lag 的 mean g 高于 lag 0 ⇒ 泄漏, 停 |
| **G2 独立性 (主筛)** | \|rho(g, gA0)\| < 0.30 **且** A0 最差五分位锚内 \|rho\| < 0.30 | 任一 ≥0.30 ⇒ 不是分散源 |
| **G3 净额** | net mean g 的 CI95 下界 > 0 | ≤0 ⇒ DEAD |
| **G4 零假设** | net mean g 高于全部 6 个 turnover-matched null (SHIFT101/503/1009, RELAB1-3) | 否 ⇒ DEAD |
| **G5 集中度** | top-20 share 报数 (活 fund-leg 对照 11.09%) | 只报数, 不单独杀 |
| **G6 下行** | net beta, 最差 UTC 日, maxDD 对比 A0 | 若 Sharpe 升而最差日更深 ⇒ 对本台无用 |
| **G7 算术** | 与 A0 在方差最优二书配置下的合并 Sharpe vs 3.966 | 只报数 |

## 4. 稳健性网格 (全格都报, 不取 max — 反 p-hacking)
`ENTRY ∈ {1.5, 2.0, 2.5}` × `K ∈ {20, 40, 80}` × `L ∈ {540, 1080}`。主格 = `(2.0, 40, 1080)`, 在看任何数字前指定。

## 5. 已知的、会偏向候选的偏差 (必须在结论里声明)
- 固定成本档是在 **450 名、G=$230k** 的书上拟合的; 对书(80名)下每名名义额 ~5.7×, impact 指数 0.87 ⇒ 真 impact ~4.6×。主格用书平均档 (**低估成本**), 另报 concentration-adjusted 档。
- 选对是对 ~N²/2 个对的搜索 ⇒ 多重比较机器; 逐次搜索数必须写进收据。
