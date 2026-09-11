> **创建:** 2026-09-12 | **Session:** round-8 BUILD-1 (basis in-book, netted) | **状态:** 预注册 — 判据冻结先于任何数字 | **作废条件:** (a) 用户裁定; (b) v4 链被取代; (c) §6 的任一门被证明写错

# PREREG R8/BUILD-1 — 把 basis 表达在书内, 与已有交易对冲, 并为成本优化表达式

**只读实盘仓**(`~/dl_quant_live` / `~/wide_shadow` 全程不写不读不重启)。产出只在
`/workspace/uplift_2026-09-11/r8_inbook/` 与本目录 `r8_inbook/`。**不改 `w10_sleeve.py`**(装置 sha 不变 ⇒ GATE P 可比)。

## 0. 口径钉 (v4 链, 与 CALIBER_PIN_v4_2026-09-11 一致)

| 项 | 值 |
|---|---|
| 装置 | `/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 `b88e35a46b93d712…` **未修改** |
| meta | `/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz` (E_ts 10182) |
| 面板 | `/workspace/data/wide_panel_4h_v2ext.npz` (ts 10039 × 829) |
| king | `SLOW_v3_on_v4axis.npy` (A0 格; 本轮全部臂都是 A0 格) |
| 成本 | **拟合** `r3k/costb_PWR_G230k.json` sha `295b4e7b462373e4…` K=0.17 |
| basis 面板 | `r5_basis/basis_panel.npz` (round-5 建, 本轮**重验**其因果断言与一个符号的逐条重建) |
| 统计量 | g = net_ex/gross_total, bps/锚/单位 gross; 逐锚配对; UTC 日块 bootstrap, `default_rng([20260905,k])`, k∈{0,9} |

**ENV 白名单 (E-0826-D, 逐个断言并写进产物 `R8_RUN_ENV.json`)** — 全部臂同一格, 只有 `FEMAT_NPZ` / `OUT_TAG` / `FSEED` / `FPRED` / `W3FIX` 变:
`LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1
UMASK_NPZ=<umask_UPIT_CRYPTO.npz> SLOW_NPY=<SLOW_v3_on_v4axis.npy> COSTB_JSON=<costb_PWR_G230k.json>
FSEED∈{42,2027} FPRED=f10_A0_s{FSEED}.npy [W3FIX=0.21,0,0.79 仅 fix 席位] FEMAT_NPZ OUT_TAG
OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=3`
未列出的装置旋钮一律保持默认(RNSM=0 FTPOS=0 LTRIM_TH=unset CDAMP=0 FTRIM_TH=-0.0010 SLEEVE=0 REF_SKIP=0
KMOD=KMOD_AGREE=KMOD_F10=0 KMOD_L=0.5 SEATF10=0 SEATNET=0 KTAIL=0 FUNDSCALE=0 TRADE_TOPN=0), 并由装置自报 `config_json` 存进每个产物。

**GATE P (必过, 先于任何数字)**: 我的树 knobs-off **全新**跑(先删产物)对四格
`w10_ablation_series_V4_A0_{dyn,fix}_s{42,2027}` 的 `d30_n2_c42_rec` **与** `_W` **全部 bitwise**。

**E-0911-D 覆盖天花板(本轮自验)**: `f10_A0_s42.npy` 最后有限行 = **2026-08-30 20:00Z**;
任何 PHI>0 的臂在其后的锚上 F10 腿被 `nan_to_num` 置零 ⇒ **一切读数在 2026-08-30 20Z 截断**, 并声明。

**窗(全部臂同跨度, 逐锚配对)**
- **FULLCYCLE(主判)**: 丢前 LOOK=900 个 device 锚, ts ≤ **2026-08-10 20:00Z** ⇒ 目标 n=**9018**(实测写进产物)。
- **EXT**: 2026-08-11 00Z .. 2026-08-30 20Z (覆盖天花板内的全部延展锚)。
- **★ GIVEBACK(用户最关心)**: 2026-08-19 00Z .. 2026-08-21 20Z **含两端 = 18 锚**(与 `r6j1_regime.py` L62 逐字同窗)。
- FROZEN: 2025-03-01 .. 2026-08-10 20Z。

## 1. R5_FBSLOPE_NOLAG 是什么 — 先把定义和符号说死

原始列 `BSLOPE(E,n) = p_last(E,n) − p_tw24(E,n)`, 其中 `p_last` = openTime=E−1h 的 1h premium-index 条的收盘,
`p_tw24` = openTime∈[E−24h, E−1h] 的 24 根条收盘的均值(要求满窗)。**只用 closeTime ≤ E−1ms 的条**。
信号链(与已录取的 Amihud sleeve 逐字同构, round-5 GATE S 已证):
```
BM  = isfinite(f_fund_ema_v1)                # 在役 fund 腿掩码 = 秩基
ZF  = rank_z(f_fund_ema_v1 on BM)            # 在役 fund 分数 (rankdata AVERAGE, /(n-1)-0.5)
ZB  = rank_z(BSLOPE on BM)
b_E = 逐锚无截距 OLS  Σ(ZF·ZB)/Σ(ZF·ZF)
ORTH= ZB − b_E·ZF                            # NOLAG(不错锚)
FBSLOPE_NOLAG = −ORTH                        # ★ 反号
```
**符号是 POST-HOC 的。** round-5 预注册声明的方向是"像 funding 一样的动量"(高分做多), 十条声明臂**全部读负**;
反号是**看过结果之后**才提出的假设(round-5 `flip.py` 的头注自述)。因此:
- 可以claim的: |IC| 的大小、与 A0 的正交性、换手匹配 null 的胜负 —— 这些不依赖符号。
- **不可**claim的: "均值回复方向"这 1 bit **没有独立于数据的先验**。本轮继承这个 post-hoc 符号, 所有结论都带这个折扣, 并在结果文里重复声明。
- 本轮**不**再挑符号: 符号固定为 `−ORTH`, 写在这里, 不看数字。

## 2. 三种"书内"表达 — 全部通过 `FEMAT_NPZ` 注入, **不加第四条腿**

装置 L~200 的 `FEMAT_NPZ` 把 `f_fund_ema_v1` 整张矩阵替换掉, 之后 `FZB(j,m)=xz(FE[j,:])[m]` 在 829 基上重排秩。
⇒ **改 fund 腿分数 = 改整本书的目标持仓 = 换手在书内自然对冲**(这正是本轮的全部论点),
且**同时**解决了 round-7 DOCKET C-7 记的 **G0 空洞**("合成书从未作为一本书跑过"): 本轮每一条臂都是**一条真书的逐锚序列**。

缺列回退(**先于数字声明**): basis 缺失的格一律回退到"零倾斜"(`ZB_eff := ZF`, 等价 `ORTH := 0`),
使有 basis 的名与没 basis 的名**同尺度**, 不产生"被收缩的名被推到秩两端"的伪效应。

| form | 注入矩阵 M(行 = 锚, 列 = 829; 有限性与 BM 逐位相同) | 说明 |
|---|---|---|
| **A · BLEND** | `M = (1−a)·ZF + a·ZBF`, `ZBF := −ZB`(缺则 `:= ZF`) | 任务 2(a): 秩层混合 |
| **B · ORTH OVERLAY** | `M = ZF + c·ORTHF`, `ORTHF := −ORTH`(缺则 0) | 任务 2(b): 正交化叠加 |
| **C · COSTGATE-TRADE** | `M = ZF + c·ORTHF·G_T` | 任务 2(c): **只在书本来就在同向交易的名上动** |
| **C2 · COSTGATE-HOLD** | `M = ZF + c·ORTHF·G_H` | 变体: 只在已持有同向仓位的名上动(只改大小, 不翻向) |

**门 G_T / G_H 的定义与因果性**(先于数字声明):
参照书 = 同 env 的 **A0**(`r3k/arms/A0_PWR230k_s42.npz` 的 `W`, 即装置内的逐锚权重 `sm`, 形状 10039×829)。
`trade_i = W[i] − W[i−1]`(装置内 `sm = H + 0.1·(tgt−H)` ⇒ `sign(trade)=sign(tgt−H)`), `hold_i = W[i−1]`。
`G_T[i,n] = 1` 当且仅当 `sign(ORTHF[i,n]) == sign(trade_i[n])` 且 `|trade_i[n]| > 0`, 否则 0。
`G_H[i,n] = 1` 当且仅当 `sign(ORTHF[i,n]) == sign(hold_i[n])` 且 `|hold_i[n]| > 0`, 否则 0。
**因果**: `trade_i` / `hold_i` 只由锚 i 及之前的信息决定(装置在锚 i 上先算 tgt 再算 trade), 无未来信息。
**可部署性**: 这是"先算未倾斜的书, 再按它的交易方向决定在哪些名上加 basis 倾斜"的规则 —— 生产者可以逐字实现。
**已声明的近似**: 门用的是**未倾斜书**的路径, 不是臂自己的路径(自洽定义会是隐式方程)。这是**规则的一部分**, 不是估计误差; 但它意味着 C/C2 不是"A0 + 倾斜"的不动点, 结果文里必须重复这句。

## 3. 网格与 **K**(看数字之前声明)

| form | 剂量 | 读数 |
|---|---|---|
| A BLEND | a ∈ {0.05, 0.10, 0.20, 0.35, 0.50} | 5 |
| B ORTH OVERLAY | c ∈ {0.10, 0.25, 0.50, 1.00} | 4 |
| C COSTGATE-TRADE | c ∈ {0.25, 0.50, 1.00} | 3 |
| C2 COSTGATE-HOLD | c = 0.50 | 1 |
| | **K = 13** | |

**主格**: 席位 **dyn**, 种子 **s42**, 窗 **FULLCYCLE**, 成本 **拟合 PWR230k**。其余(fix 席位 / s2027 / EXT / GIVEBACK / 其它成本模型)是**次级读数**, 不计入 K, 只在主格过门后跑。
**Bonferroni**: 双侧 α = 0.05/13 = **0.0038462** ⇒ bootstrap 分位 **0.1923% / 99.8077%**, B = **4000**, 两条流 k∈{0,9}。
同时报 CI95(与 round-5 incumbent 可比)。

## 4. 必须先复现的 incumbent(**不计入 K**, 是装置自校准)

round-5 §5.4 的 **收益序列混合** `A0 + 0.10·basis`: ΔSharpe **+0.1171**, CI95 **[0.0121, 0.2186] / [0.0067, 0.2202]**。
**注意这不是"书内"**: round-5 `battery.py` 的 `dose` 是 `C = (1−a)·g_A0 + a·g_sleeve`, 即**两本书在 g 层线性组合**,
每本各付自己的全额换手。本轮先逐位重跑它(同 `battery.py` 数学), 复现到 ±0.001, 作为"我的尺 = round-5 的尺"的收据;
**它就是本轮要打败的对照**(标称 35.2% 毛 alpha 存活)。
另两个自校准数: A0 FULLCYCLE Sharpe **1.4150**(s42) / **1.4370**(s2027); GIVEBACK 18 锚上 A0 Sharpe **−29.6**(s42) / **−32.0**(s2027), g **−20.75**。

## 5. 成本口径 — 本轮的主命题, 先写清怎么算

对每条臂 X(与 A0 同跨度逐锚配对):
- **边际换手** `Δturn = mean(turn_X) − mean(turn_A0)`, 报 `Δturn / mean(turn_A0)`。
- **边际毛 alpha** `Δpnl = mean(pnl_ex_X) − mean(pnl_ex_A0)`(bps/锚/单位 gross)。
- **边际成本** `Δcost = mean(cost_ex_X) − mean(cost_ex_A0)`。
- **边际 carry** `Δcarry`。
- **存活率** `surv = 1 − Δcost/Δpnl`(仅当 `Δpnl > 0` 有意义; 否则报 N/A 并说明)。
  **对照**: 独立 sleeve 的 `surv = 1 − 1.1746/1.8131 = 35.2%`。**本轮假设: 书内表达把它从 35.2% 抬高。**
- `Δg = Δpnl − Δcarry − Δcost`(恒等式, 逐项报, 并断言与直接算的 `mean(g_X)−mean(g_A0)` 在 1e-9 内相等)。

## 6. 录取门(任一不过 ⇒ 记 REJECTED 并写死在哪一门)

1. **G-P** GATE P 四格 bitwise。
2. **G1 主格显著**: 配对 `ΔSharpe` **与** `Δg` 的 **Bonferroni(K=13) bootstrap CI 下界 > 0**, **两条流 k=0/9 都过**。
3. **G2 双种子 × 双席位**: s42/s2027 × dyn/fix 四格 `ΔSharpe` 与 `Δg` **同号为正**(四格 Bonferroni 下界不要求全过, 但 CI95 下界须 ≥ 0 的格 ≥ 3/4)。
4. **G3 换手匹配 null**: `SHIFT101 / SHIFT503 / SHIFT1009 / RELAB1 / RELAB2 / RELAB3`(装置 `r3_attack_b9646/null.py` sha `91d4c91cb92a6440` 的构造逐字), **毛 `Δpnl_ex` 与净 `Δg` 两个口径都必须击败全部 6 条**, 并报每条 null 的换手比(必须 0.9–1.1 才算匹配)。
5. **G4 尾部集中度**(`r3_gates/rs_conc.py` sha `3fd2f76496a593ba`): 对**边际 pnl 序列**报 top-20 占比与 ex-top-20 Sharpe。参照: 在役 fund 腿 11.09% / +6.71; 已死的 RESID_SHARPE 130–189% / −2.40/−5.60。门: top-20 占比 < 100% 且 ex-top-20 的边际效应同号。
6. **G5 偏移谱**: 注入列 `M` 对 y4 的逐锚 xsec 秩 IC, k = −3..+3; 不得出现 backward 单峰(k<0 显著大于 k=0 且 k=0 附近无结构)。
7. **G6 逐年符号**: 2022–2026 逐年 `Δg` 同号(允许 1 年反号, 须声明)。
8. **G7 单调剂量响应**: form 内部随剂量单调(至少在 0→最优剂量段)。
9. **G8 条件 rho**: 对 A0 的 g 序列 rho, **按 regime 四格分别报**(不是只报无条件 —— XIB 的失败正是被无条件 rho 藏住的)。**说明**: 书内倾斜与 A0 的 rho 必然接近 1(它就是 A0 加一个小倾斜), 所以 rho 在本轮**不是门**, 是**诚实披露项**; "是不是新赌注"由 basis 自身与 A0 的 rho(standalone 0.0026)回答。
10. **★ G9 GIVEBACK 披露**(不是门, 是决策项): 18 锚上的 `ΔSharpe` / `Δg` + CI, 与 XIB 的 `Δg −5.690 CI95 [−12.589,−1.466]` 并列。

## 7. 失败即公开
任一门不过 ⇒ REJECTED + 死在哪一门。不做门后再搜臂。不因数字难看换窗/换口径/换统计量/换符号/加剂量格。
若全部 13 条不过 ⇒ 本 BUILD 判 REJECTED, 并写明"basis 的成本问题不能靠书内对冲解决"。
