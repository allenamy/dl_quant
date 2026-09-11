> **创建:** 2026-09-11 | **Session:** round-5 NEW-DATA-1 (book-uplift-2026-09-11) | **状态:** 预注册, 判据冻结先于任何数字 | **作废条件:** (a) 用户裁定; (b) v4 链被取代; (c) §2 的机理式被证伪

# PREREG R5/ND1 — spot-perp basis & premium index as NEW INFORMATION

**只读实盘仓, 不改任何在役件.** 全部产出在 `/workspace/uplift_2026-09-11/r5_basis/` 与本目录.

## 0. 口径钉 (v4 链, 2026-09-09)

| 项 | 值 |
|---|---|
| 装置 | `/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 `b88e35a46b93d712…` (未修改) |
| meta | `/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz` (E_ts 10182) |
| 面板 | `/workspace/data/wide_panel_4h_v2ext.npz` (ts 10039, 4h step, 829 syms) — 即 GATE P 归档件所用面板 |
| king | `SLOW_v4.npy` (sleeve) / `SLOW_v3_on_v4axis.npy` (GATE P A0 格) |
| 成本 | **拟合** `r3k/costb_PWR_G230k.json` sha `295b4e7b462373e4…` K=0.17 (GATE P 对照格用 `costb_fee_steady.json`, 因归档件如此建) |
| 统计量 | g = net_ex/gross_total, bps/锚/单位 gross; 逐锚配对; UTC 日块 bootstrap 2000, `default_rng([20260905,k])` |
| 窗 | FULL post-warm: 丢前 LOOK=900 device 锚, 截至 2026-08-10 20Z, **n=9018**, SE(Sharpe)=0.4928 |
| RANK | `scipy.stats.rankdata` (AVERAGE), 禁 `argsort(argsort())` |

**ENV 白名单 (E-0826-D, 逐个断言并写进产物 `GATE_PS.json` / `R5_ARMS.json`)**
A0 格: `LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=<umask_UPIT_CRYPTO.npz> SLOW_NPY=<SLOW_v3_on_v4axis.npy> FSEED FPRED COSTB_JSON OUT_TAG [W3FIX]`
sleeve 格: `LEGS=001 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=off PHI=0 UMASK_SCOPE=m1 UMASK_NPZ=<…> SLOW_NPY=<SLOW_v4.npy> FSEED FPRED COSTB_JSON FEMAT_NPZ OUT_TAG`
线程: `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=3`.

**GATE P (必过, 先于任何数字)**: 我的树 knobs-off **全新**跑 (先删缓存) 对四格 `w10_ablation_series_V4_A0_{dyn,fix}_s{42,2027}` 的 `d30_n2_c42_rec` 与 `_W` 全部 bitwise。
**GATE S (信号链同一性, 必过)**: 我自己的 `mk_orthlag()` + FEMAT 注入路径, 喂归档的 `AM_Q64` Amihud 矩阵, 必须逐位复现归档 sleeve `P6_AMQ64_PWR_s42`。⇒ 之后换成 basis 列时, **换的只有那一列**。

## 1. 数据来源与因果条 (THE CAUSALITY BAR)

**来源**: `data.binance.vision` **批量档案** (静态 CDN, 无鉴权, 无签名端点, 无凭据), 在 pod2 上下载 — pod2 不是任何接触交易 API 的机器。
- `futures/um/monthly/premiumIndexKlines/<SYM>/1h/` — **premium index** OHLC, 1 小时条
- `futures/um/monthly/fundingRate/<SYM>/` — 实际结算的 funding, 带真实结算时刻

**每个值在哪根条上被观测到 (逐条声明)**:
锚 E ∈ {00,04,08,12,16,20}Z。**只用 openTime ≤ E−1h 的 1h 条** (closeTime ≤ E−1ms)。即在锚 E 上可见的最后一根**已收盘**的小时条。
- `p_last(E)` = close of bar openTime = E−1h → 观测于 E−1ms, 严格早于 E。
- `p_tw8(E)` = mean close, openTime ∈ [E−8h, E−1h] (8 根)
- `p_tw24(E)` = mean close, openTime ∈ [E−24h, E−1h] (24 根)
- `p_sd8(E)` = std of those 8 closes
收益 y4 跨 [E, E+4h)。⇒ 任何值都不含 E 之后的信息。
**泄漏自检 (必做, 写进产物)**: (i) 偏移谱 — 与 y4 的秩 IC 在 k=−3..+3 上, 必须在 k=0 或更早侧无异常单峰且 backward≫forward 的形态不成立; (ii) 逐符号断言 `max(openTime used) + 3600s ≤ E`; (iii) 对 `p_last` 施 +1 锚人工超前, IC 必须显著上升 (证明装置能看见超前)。

## 2. 机理 — 问在数字之前

交易所规则: `f = clamp( P̄ + clamp(I − P̄, ±0.05%), ±cap )`, 其中 `P̄` = premium index 在结算区间上的时间平均, `I` = 利息项。
⇒ **funding 是 basis 的滞后 · 时间平均 · 双重截断 版本**。funding 结构上**装不下**的 basis 成分正是候选:
- **B1 新鲜度 (premium surprise)**: 锚上的**终值** premium 与 funding 将要支付的**区间均值**之差。basis 在窗内移动过, funding 就是陈的。
- **B2 截断**: `|P̄|` 超过 cap 时 funding 被削平, 超出部分在 funding 里不可见。
- **B3 期限结构**: 短窗 premium vs 长窗 premium 的斜率, 单个 funding 数表达不了。
- **B4 路径离散**: 区间内 premium 的波动, 不是均值。

**单位链 (E-0904-G: 换算必须脚本化, 不得手推)**: premium index 与 funding rate 同量纲 (都是价格偏离的分数, funding ≈ 区间均值 premium)。**上机前先做单位门**: 逐锚把 `f_fund_now` 对 `p_tw_iv` 做无截距 OLS, 斜率必须在 [0.7, 1.3]、R² ≥ 0.5, 否则量纲假设被证伪, `BGAP` 改用**秩差**形式并声明。

## 3. 候选列 (raw), 全部按 §1 的因果窗算

| tag | 定义 | 对应机理 |
|---|---|---|
| `BGAP` | `p_last − f_now_prem_equiv` (单位门通过则直接相减; 否则 `rank(p_last) − rank(f_fund_now)` 的秩差) | B1+B2 |
| `BSLOPE` | `p_last − p_tw24` | B3 |
| `BDISP` | `p_sd8` | B4 |
| `XVEN` | 跨场所 funding 离散度 (Binance 8h 当量 vs 其它场所同名 8h 当量), 仅在跨场所数据到位时 | 新场所信息 |

## 4. 信号链 (与已录取的 Amihud sleeve **逐字同构**, GATE S 证明)

```
B   = isfinite(f_fund_ema_v1)                      # 与在役 fund 腿同一掩码
ZF  = rank_z_rows(f_fund_ema_v1 on B)              # 在役 fund 分数
ZX  = rank_z_rows(raw column on B)
ZXL = ZX 向后错一个锚                               # LAG 臂 (PRIMARY)
b   = 逐锚无截距 OLS  Σ(ZF·ZXL)/Σ(ZF·ZF)
sig = ZXL − b·ZF                                   # 逐锚对在役 fund 分数正交化
```
注入 `FEMAT_NPZ=sig`, `LEGS=001 PHI=0 FTRIM=off` ⇒ **standalone sleeve**。
`NOLAG` 臂用 `ZX` 而非 `ZXL` (我的列因果性由构造控制), 但 **PRIMARY 是 LAG**, 因为把 Amihud sleeve 从 CI 含 0 变成 CI 排除 0 的那一个改动就是把窗提前一个锚。

## 5. K 与 Bonferroni — **看数字之前声明**

**K = 8** 个录取读数 = 4 个候选列 (`BGAP`,`BSLOPE`,`BDISP`,`XVEN`) × 2 个滞后臂 (`LAG`,`NOLAG`)。
standalone sleeve 在 `LEGS=001 PHI=0` 下**与 FSEED/FPRED 无关** (装置 `if PHI > 0` 才载 F10), 故双种子不计入 K。
Bonferroni: 双侧 α=0.05 / 8 ⇒ 每臂 α=0.00625 ⇒ z=2.734 ⇒ **Sharpe 门 = 2.734 × 0.4928 = 1.347**。
**录取条 (任务给定, 更严)**: standalone full-cycle Sharpe **≥ 1.5** 且 `|rho to A0| ≤ 0.25` 且**四个换手匹配 null 全过**。

## 6. 电池 (任何过条的臂都必须全跑)

1. standalone Sharpe + SE(0.4928) + UTC 日块 bootstrap CI95 (k=0,9), full cycle post-warm n=9018
2. 对 A0 的 g 序列相关 rho (full + frozen)
3. **carry fraction of net** — basis sleeve 极可能是伪装的 carry sleeve (round-2 ORTH_SURP 自称 45% 实测 80–106%)
4. forward vs backward rank-IC, **k = −3..+3 全谱**, 不报单一比值
5. **换手匹配 null**: `SHIFT101/SHIFT503/SHIFT1009/RELAB{1,2,3}`, 装置 `r3_attack_b9646/null.py` sha `91d4c91cb92a6440` 的构造逐字; 同时报 `pnl_ex` (毛) 与 `g` (净); 并报每个 null 的换手, 证明确实匹配 (旧逐锚置换 null 抬高换手 2.6–7.7×, 已作废)
6. **尾部集中度尺** `r3_gates/rs_conc.py` sha `3fd2f76496a593ba`: top-20 share 与 ex-top-20 Sharpe。参照: 在役 fund 腿 11.09% / +6.71; 已死的 RESID_SHARPE 130–189% / −2.40
7. 逐年符号 (2022–2026)
8. **单调剂量响应** a ∈ {0.05,0.10,0.20,0.30,0.50}: 配对 dSharpe vs A0 + CI95

## 7. 失败即公开

任一门不过 ⇒ 记 REJECTED 并写下它死在哪一门。不做门后再搜臂。不因数字难看换窗、换口径、换统计量。

---

## AMENDMENT 1 (2026-09-11, **写在任何收益数字之前** — 此刻只看过覆盖率与端点深度, 未看过任何 IC/Sharpe)

**事实**: §3 的 `XVEN` 臂**不可执行**。免费公开端点的历史深度实测 (见 `DATA_PROVENANCE_r5_basis_2026-09-11.md` §B): OKX 3 个月 / Bitget 4 个月 / Bybit 从 pod2 不可达 / Hyperliquid 起点 2023-05。要求的窗是 2022-04→2026-08 的 n=9018。**跑不了, 不是没过。**

**改动**: `XVEN` 出, `BGAPF`/`BGAPT` 拆成两条独立列入替 (§2 的单位链问题没有先验答案, 两种 gap 形式都值得单独读, 而不是由单位门"选"一个 —— 由门选就是选型污染)。

| 原 | 新 |
|---|---|
| `BGAP` (单位门通过则减 funding, 否则秩差) | `BGAPF = p_last − f_fund_now` (与**上一次已结算**的费率之差 = 新鲜度; `f_fund_now` 经查 `pod_panel_ext.py` L153 `searchsorted(ft, anchor_s, "right")−1` = **锚上最后一次已结算**的 rate, 严格因果) |
| — | `BGAPT = p_last − p_tw_iv` (与自身结算区间 TWAP 之差) |
| `XVEN × {LAG,NOLAG}` | **删除** |

**K 不变 = 8** (4 列 × 2 滞后)。Bonferroni 阈不放松: 我按更严的 **K=10** 记阈 (α=0.005, z=2.807, **Sharpe 门 1.383**), 因为 §3 本来打算读 10 个读数; 少跑两条不应该让剩下的更容易过。任务给的 **≥1.5** 条仍是主条。

**单位门降级为诊断**: 它不再选臂 (两条 gap 都跑), 只用来报告 premium 与 funding 的量纲关系。
