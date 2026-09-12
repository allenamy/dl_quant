> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME(子代理 r17-fill-pricing)| **状态:** 冻结 — 本文在拟合任何成交模型、计算任何臂收益之前写定; sha256 写入 `receipts/PREREG_FREEZE_sha.txt`, 每台装置运行前断言 | **作废条件:** 出现比 v4 更新且逐门验过的链; 或 GATE P 失败(那时本轮无结果); 或 `~/dl_quant_live` 账本 schema v2 被改 | **口径:** `CALIBER_PIN_v4_2026-09-11.md`(v4 链; 禁 dlw_ext/_ext、pod_fea_ext.py、裁剪复利、pod_legs_ext.py、shadow_bundle_v3、wide_fea_v2ext_meta、panel_source.py 默认面板、对 5m 谱系施 expm1)

# PREREG r17 · 给漏单定价: 回放只执行实盘会成交的那部分, 书值多少; 哪些既有判决因此移动

## §0 问题与三条独立仪器的指向
回放(`w10_sleeve.py`)假设**每笔意图交易 100% 成交、按模型价收费**。实盘是 maker-only, 政策 A(flatten_only 不追单)。
(1) r14 §6: 模型过度收费 2.20 bps/单位成交里 1.6457 是 maker 价格优惠, 而优惠的另一半就是 45.48% 的成交率 —— 「便宜价与漏单必须同时定价, 否则两边都错」。
(2) r16 + 组长账本核实: 已发腿按类成交/意图 ZERO_TARGET 65.6% / FLIP 64.6% / DERISK 64.8% / ADD 34.0%; 零目标 maker 腿 814 条里 740 条 `skipped_min_notional`(灰尘发不出)。
(3) r6 judge1: 回放 vs 实盘最大差异项 = 书的构造 **+2.6982 bps/锚**(CI 排 0), 漏单是它的一个未检验候选解释。
**本轮 = 对回放仪器的一次测量, 不是书行为改动, 无部署件。**

## §1 仪器与钉(跑前逐个重算 sha, 任一不符即中止)
| 项 | 值 |
|---|---|
| 判决装置(不改) | `trackA/w10_sleeve.py` = pod2 `/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 **b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650**(两处本轮已重算 VERIFIED) |
| 派生装置 | `devices/w10_sleeve_r17.py` = 判决装置 + `{R17_FILL, R17_TABLE, R17_MODE, R17_SEED, R17_GROSS_USDT, R17_X1, R17_INSTR}`; 由 `devices/mk_r17_device.py` 字符串替换生成(每处断言恰命中一次), diff 存 `devices/w10_sleeve_r17.diff`; 自报 self_sha256 与 R17 全部旋钮 |
| A0 归档臂 | pod2 `r3k/arms/A0_PWR230k_s42.npz` **352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339**; `_s2027.npz` **aa44e18fb6bcfa7ef54f1708d070b0a2a7d5333f6cea63dfca94fecf59be1c7b** |
| r16 X1 归档臂(100% 成交参照) | pod2 `r16_asym_band/arms/A_X1_s42.npz` **cdec63ed669265ad8255c02af09a583947a6c271ddf8ebf1eb439a67476fbafa**; `A_X1_s2027.npz` **baecf30e384ffcdc875319a086ab39277663ee0f23abd8d54cb01dd35a0c0ff9**; 产它的装置 `w10_r16.py` **caf7ffdb3bde581bc34438d5e9df695546564c0669bbaa5812e5c9b62e4a87a0** |
| r15 F / S 归档臂(100% 成交参照) | pod2 `r15_structural/arms/{F,S}_s{42,2027}.npz`(sha 在跑前重算并写入收据; 与 `r15_structural/receipts/RECEIPT_r15_drive_gateP.json` 记录的 out_sha256 逐个比对) |
| 成本 | `r3k/costb_PWR_G230k.json` **295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53**(λ=1.0 模型墙 2.9537 bps/单位; 手续费底 λ=0.8096 = 2.3914) |
| A0 环境(逐字) | `LEGS=101 PHI=0.45 WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FTRIM_TH=-0.0010 UMASK_SCOPE=m1 CAL=log FTPOS=0 SEATNET=0 UMASK_NPZ=…/masks/umask_UPIT_CRYPTO.npz SLOW_NPY=…/king_v4/SLOW_v3_on_v4axis.npy FPRED=f10_A0_s{FSEED}.npy COSTB_JSON=r3k/costb_PWR_G230k.json`, FSEED∈{42,2027}, W3FIX 不设; 运行树 = r15 同构符号链接树(pod_backup_2026-08-21/{wide_fea_hist_meta→meta_newprod_v4.npz, wide_panel_4h_hist_v2→wide_panel_4h_v2ext.npz, slow_pred_hist_oos→SLOW_v4.npy, nets_histv2_*}, dlw_2026-08-22→/workspace/dlw_v4raw, f8_2026-08-22→health_check/dev_v4/f8_2026-08-22) |
| regime | `r12_regime/receipts/causal_primitives_r12_v2.npz` **0510f456f63f4963cae757a0fd86251477089de1d266b8b8859092f9f73cf08f** + 分区 `PREREG_r12_regime_partition_2026-09-12.md` **e239f8dfd5645bf867a50950377d6d6e4b4e4fd276395e35aa2e3481a699ce3c**; 34 格构造逐字复用 `r15_structural/devices/r15_judge.py` L?? 的 CELLS, 切点断言等于 `RECEIPT_r12_regime_table.json` |
| r6 对账行 | 仓内 `judge1_r6/j1_recon_rows.json`(D2 = 部署权重 × 回放 y4s; A0 = 归档臂 pnl_ex/gt), `j1_decomp.py` 的 BOOK 项定义与自举(`default_rng([20260911,k])`, k=107 / 110) |
| 实盘账本(只读) | `~/dl_quant_live/state/live/pilot_log/{YYYYMMDD}/{orders,fills,anchors}.jsonl`, 2026-08-01 起全部日文件(读取时刻与日清单写入收据; 账本仍在追加); `~/dl_quant_live/state/live/exchange_info_cache.json`(逐名 min_notional; sha 写入收据); `~/wide_shadow/state/rolling.npz`(LIVE-CACHE 谱系, 只用于 09-10 00Z 之后锚的 qv4h, 见 §2.3) |
| 统计核 | UTC 日块自举 2000, `numpy.default_rng([20260905, k])`; Sharpe = mean/sd(ddof=1)·√2190, SE = √(2190/n); 分辨率 0.23 bps/锚 |

### §1.1 必须写进 RESULT 头部的基线事实(承 r15/r16, VERIFIED)
归档 A0 带 **v3 谱系模型腿**(`SLOW_v3_on_v4axis.npy`, `f10_A0_s*.npy`)与**死前缀**: king 腿 W_ALPHA 前 3300 锚 ≡ 0(至 2023-12-31), F10 前 1110 锚 ≡ 0(至 2022-12-31)。每个 headline 另在 KING_LIVE(ts ≥ 2024-01-01, W_ALPHA∩ n=5838)上报。

## §2 STEP 1 · 成交模型(先于拟合冻结; 全部从实盘账本, 只读)
### §2.1 分析单元与量
- 单元 = `orders.jsonl` 的 **(rebalance_id, symbol) 组**(一名一锚)。跨全部日文件。
- **意图** `I` = 该组 **maker attempt_idx=1 行**的 `|intended_full|`(缺该字段的早期行用 `|intended_notional|`)。若组内有多条 a1 maker 行(−5022 拒后重挂, 账本记为第二条 a1 行), 断言各行意图相等(相对差 < 1e-6), 取第一条; 不等 ⇒ 该组剔除并计数。无 a1 maker 行的组(`protective_flatten` / `exit_only`)剔除并计数(结构性排除, 与 r14 一致)。
- **发出** = a1 `terminal_reason ∉ {skipped_min_notional, blocked_by_halt, skipped_no_mid}`。`skipped_min_notional` = **灰尘**(单独计数, 见 §2.4); `blocked_by_halt` = **停机封锁**(单独计数; **主表剔除** —— 它是风险层状态, 不是成交失败; 副表把它记 f=0 只作报告)。
- **成交** `F` = 组内 `order_type ∈ {maker, topup_taker}` 全部行 `|filled_notional|` 之和(`None` 记 0 并计数「成交额未知」行); **f = min(F/I, 1)**。F > 1.02·I 的组计数并报(from_reject 转 taker 按手数上取整可超意图, 已见 73 例); 成交符号与意图符号相反的组计数并剔除。
- 只报 a1 与 topup 的成交拆分(maker 份额 / taker 份额), 作机制描述; **不**把 order_type 当分层变量(回放建模的是一名一锚的**总**成交)。
### §2.2 特征(只用提交前可观测量; 禁 markout / 成交时刻 / terminal_reason)
- **方向类** 由 a1 行 (prev_w, target_w): `ZERO_TARGET`: target=0 ∧ prev≠0; `FLIP`: prev·target<0; `DERISK`: 同号 ∧ |target|<|prev|; `ADD`: 其余(含 prev=0)。
- **流动性档** = 装置 `tier_of(qv4h)` 同式: qv4h ≥ 5e6 → 0; ≥ 1e6 → 1; 其余 2; qv4h = expm1(clip(qvk,0,30))·48, qvk 取 v4 谱系(§2.3)。
- **参与率** p = I / qv4h; 在「发出」总体上切三分位(切点写入表)。
- 另报(只作边际检查, 不入表): anchor-of-day(6)、side、placement_arm(join/behind, 随机化 ε=0.5)、纪元。
### §2.3 qv4h 的来源(v4 谱系优先)
锚 ≤ 2026-09-10 00Z: 仓内 `judge1_r6/j1_slice.npz` 的 `qvk`(来自 `meta_newprod_v4_x0910.npz`, 同一构建器的延展)。锚 > 09-10 00Z: 由 `rolling.npz` 通道 3(log1p 报价额, `shadow_loop_v3.py` L246 逐字)按 `log1p(mean_{48 bar 止于 E} expm1(lqv))` 重建; **先在重叠锚上验**: 与 j1_slice qvk 的 |Δlog| 中位 < 0.02 且 tier 一致率 ≥ 0.98 才用, 否则 09-10 后的锚只用 j1_slice 覆盖范围内的(缩窗并报)。账本 `anchor_ts` 是**墙钟浮点**(如 1789158241.472 = 20:24:01Z), 锚对齐 = round(anchor_ts/14400)·14400, 断言 |anchor_ts − E| < 3600。
### §2.4 灰尘规则
逐名 `min_notional` 取 `exchange_info_cache.json`(缺名 → 5.0 USDT)。实盘: |Δ| < floor ⇒ 不发。回放同规则: |dw|·G_USDT < floor(sym) ⇒ 不发, **G_USDT = 232,000**(NAV 116k × 2.0, 常数, 预先声明; 敏感性 G=116,000(1×)只报不判)。报: 灰尘组数与其意图额占比(实盘)、回放每锚触灰尘名数与意图额占比。
### §2.5 表与用途(先声明谁进回放)
- **T1**(主报表): 方向类 × 档 = 12 格; 每格 n、ΣI、**f̄_w = ΣF/ΣI**(名义加权, 回放用的量)、f̄_u(等权)、f 的分布(P(f=0), P(0<f<1), P(f=1))。
- **T2**(回放用): 方向类 × 档 × 参与率三分位 = 36 格, 同量。**回放 f_hat 查 T2 格, n_格 < 30 ⇒ 回退 T1 格, T1 n < 30 ⇒ 回退方向类边际。** 理由: 参与率是把 8 月小 gross(4–25k)时代与 9 月 232k 时代放到同一尺度的唯一变量, 回放在 232k 尺度上运行。
- **稀疏检查**: 一个带 L2 罚的分数 logistic 回归(响应 f∈[0,1], 权 I, 特征 = 类哑变量 + 档哑变量 + log p + anchor-of-day 哑变量 + side, 罚 λ_L2 = 1.0, IRLS ≤ 50 步), 报系数与它对 T2 格的预测; **不进回放**。
- **校准**: T2 预测 vs 实现 f̄_w 按预测十分位(全样本, 与**按 UTC 日奇偶两折**留出); 报斜率、逐十分位 MAE。**GATE F-i(报, 不停)**: 留出斜率 ∈ [0.8, 1.2]。
- **纪元稳定性**: T1 分 ERA_A(08-01..08-25, 旧书/小 gross)/ ERA_B(08-26..09-02, combo 爬坡)/ ERA_C(09-03 起, 入金后 2.0×)三报。
- **逆选择条件**: adv = sgn(意图) × (mid_next − mid_now)/mid_now × 1e4, mid_now = a1 行 `mid_at_anchor`, mid_next = **下一锚** `anchors.jsonl` `mid_at_anchor_vector[symbol]`(下一锚 = anchor_ts 之后 3h..5h 内最近的一行; 无 ⇒ 跳过); 正 = 价格朝意图方向走(不成交则错失)。按 f=1 / 0<f<1 / f=0 三组与四类报均值与日块 CI95; **在役配置的「成交 +3.66 vs 未成交 +5.48」须在方向上复现**(未成交组 adv > 成交组 adv); 若反向, 如实报并在 §8 限度里说明成交模型可能低估漏单代价。
### §2.6 随机臂参数
随机臂逐名 f 从其 T2 格(同回退)的**经验分布**抽取, 权 I(与 f̄_w 同均值), `default_rng([20260912, R17_SEED])`, 抽样顺序 = 锚序 × 名序; 种子 R17_SEED ∈ {1,2,3,4,5}。**跨名独立抽取 —— 已知失真**: r14/chase_policy 记录未成交残差在锚内**同向**, 独立抽取低估方向缺口方差; §8 必写。

## §3 STEP 2 · 带漏单的回放(派生装置; 关掉时逐位同)
插入点: 判决装置 L312 `sm = smb` 之后、L313 `trade = sm - HB` 之前。新增状态 `HX`(执行后持仓, 初值 0)。
```
intent  = sm - HX                                   # 与实盘 delta = tgt - cur 同构(cur 含上锚未成交残差)
class   = 由 (HX, sm) 逐名按 §2.2 规则
tier    = tier_of(expm1(clip(qvk[i,:],0,30))*48)   # 全 829 名; qvk NaN ⇒ 档 2
p       = |intent|·G_USDT / qv4h                    # qv4h NaN ⇒ 最高参与率三分位
f       = T2[class,tier,p三分位](回退规则) | 随机臂: 经验抽取
dust    = |intent|·G_USDT < floor(sym)  ⇒ f = 0   (不发; 残差留到下锚 —— 政策 A)
exec    = f · intent
sm_exec = HX + exec
```
此后**全部记账用 sm_exec**: `trade = sm_exec − HB`(= exec), 成本 Σ_tier |trade|·rate(λ=1 记 cost_ex; λ 平面在判官里按标量施于 cost_ex), pnl/carry 用 sm_exec, 执行器去均值 smr 从 sm_exec, 止损层(Pi/sh/cb/dep)用 sm_exec, `gross_total = Σ|sm_exec|`, `WS` 存 sm_exec; `HB ← sm_exec`, `HX ← sm_exec`。**链态 H(king)/HF(F10)不变** —— 它们是生产者的平滑态, 不是持仓(与 `combo_stage.py chain()` / 执行器 `delta = tgt − cur` 的分工同构)。
`R17_FILL=0` ⇒ `sm_exec` 即 `sm` 同一对象, 无新浮点运算触及主路径 ⇒ rec/W 逐位同(GATE P 证)。
`R17_X1=1` = r16 `_x16_apply` 的 X1 算子逐字(去风险名两链跳到目标), 不带 XNULL/AUX16。
`R17_INSTR=1` 逐锚仪表(加性, 书不读): tau_intent=Σ|intent|, tau_exec=Σ|exec|, gross_target=Σ|sm|, gross_prev_held=Σ|HX 前|, resid=Σ|sm−sm_exec|, n_resid(>1e-12 且在 m), n_dust, dust_notional, 四类的 Σ|intent| 与 Σ|exec|, 残差年龄直方图(逐名 age: |sm−sm_exec| > 5e-5 权重时 +1 否则清零; 桶 {1,2,3-5,6-12,>12})。

## §4 GATE P(先于一切; 任一失败 ⇒ STOP, 只报 GATE P)
- **P1**: 派生装置 `R17_FILL=0 R17_X1=0`, A0 环境, 两种子 ⇒ `d30_n2_c42_rec`/`_W` 与归档 A0 **逐位相等**(shape 同、NaN 位同、maxabs 0.0)。
- **P2**: 派生装置 `R17_FILL=0 R17_X1=1` 两种子 ⇒ 与 r16 归档 `A_X1_s*` 的 rec/W 逐位相等(证 X1 算子搬运无误)。
- **P3**: 派生装置 `R17_FILL=0 FTPOS=1` 与 `R17_FILL=0 SEATNET=1` 两种子 ⇒ 与 r15 归档 `F_s*` / `S_s*` 逐位相等。
- **P4**: `R17_FILL=0 R17_INSTR=1` ⇒ 与 P1 逐位相等(仪表不改主路径)。
- **GATE F-ii(报, 不停; 成交模型的稳态校准)**: 实盘 `anchors.jsonl` 的 `realized_gross/target_gross` 在 2026-08-03 起非重建锚上的中位数(本轮已初读 ≈ 1.00, 248 锚; 正式值写入收据)与 **A0_DET 在 2026 年 W_ALPHA 锚上 Σ|HX_{i−1}|/Σ|sm_i| 的中位数**之差 ≤ 0.05 ⇒ 成交模型的不对称(ADD 低 / DERISK 高)在回放稳态下与实盘持仓 gross 一致; 否则**标 FAIL 并在判决里说明成交模型未复现实盘稳态**(不改模型, 不重拟合)。

## §5 臂(全部预先声明; 不加臂)
| 臂 | 装置旋钮 | 用途 |
|---|---|---|
| **A0_DET** | `R17_FILL=1 R17_MODE=det` | 主: 期望成交 |
| **A0_STO_k**, k=1..5 | `R17_FILL=1 R17_MODE=stoch R17_SEED=k` | 桌子面对的方差 |
| **X1_DET** | `R17_FILL=1 R17_MODE=det R17_X1=1` | r16 X1 重基 |
| **F_DET** | `R17_FILL=1 R17_MODE=det FTPOS=1` | r15 F 重基 |
| **S_DET** | `R17_FILL=1 R17_MODE=det SEATNET=1` | r15 S 重基 |
两种子 s42 / s2027 都跑。成本平面 λ ∈ {0.8096(**主**), 1.0(次)} 为判官里对 `cost_ex` 的标量, 不另跑。**理由(§0 (1))**: 显式建模成交后, maker 价格优惠不再是白拿的贷记, 手续费底才是与「按实际成交额收费」自洽的一对; λ=1.0 平面同时报, 供与既有 λ=1 判决直接比。
K(Bonferroni)= 4: 主对比 1(A0_DET vs A0)+ 重基对比 3(X1/F/S)⇒ α_K = 0.0125, 报 CI95 与 CI99-K(分位 0.625% / 99.375%)。

## §6 窗口(★ 不混用)
`W_ALPHA` = 丢前 900 ∩ ts ≤ 2026-08-30 20Z ⇒ **n=9138**(断言): mean/CI/Sharpe/换手/残差/腿/分解。`W_TAIL` = ts ≤ 2026-08-30 20Z 不丢暖机 ⇒ **n=10038**(断言): maxDD/最差日/HALT。`KING_LIVE` = ts ≥ 2024-01-01(W_ALPHA∩ **n=5838** 断言)。

## §7 统计量与读法(冻结)
- `g = net_ex/gross_total`(bps/锚/单位 gross), 恒等式 `net_ex = pnl_ex − carry_ex − cost_ex` 逐锚断言(1e-9)。λ 平面: `g_λ = (pnl_ex − carry_ex − λ·cost_ex)/gt`。
- **主统计量** `Δ_fill = mean_WA[ g_pf(λ=0.8096) − g_100(λ=1.0) ]`(同种子配对; A0_DET vs 归档 A0); 次: `Δ_fill^(1.0) = mean_WA[ g_pf(1.0) − g_100(1.0) ]`。分解 Δpnl / Δcarry / Δcost(各 /gt, 加总核对 1e-9)。CI: 配对日块自举(§1)。
- **读法 (b)**: 两种子 `|Δ_fill| ≥ 0.23` **且** CI95 排 0 ⇒ **MOVES**(报方向; 规划数、成本争议、r15/r16 臂须按 §7.5 重基); 两种子 `|Δ_fill| < 0.23` ⇒ **CLOSES**(100% 成交回放作为规划仪器在分辨率内被证实); 其余 ⇒ **UNDECIDED**。λ=1.0 平面同规则另判, 两平面结论并列报。
- 随机臂: 5 种子 g 的均值与跨种子 sd(W_ALPHA 均值的 sd = 桌子的执行方差); A0_DET 须落在 5 种子 [min, max] 内(构造检查); 每种子 W_TAIL 尾部另报。
- 换手(匹配口径, 逐锚比的均值): `tau_intent/gt` 与 `tau_exec/gt` 分别报; A0 归档 `turnover/gt` = 0.0540270 断言; RAW 0.03032 同印; **不用任何因子换算**。
- 残差: mean_WA resid/gross_target; n_resid/锚; 年龄直方图(W_ALPHA 合计与 2026 子窗); Σ|HX|/Σ|sm| 逐年中位; 灰尘触发名数/锚与意图额占比。
- carry: carry_ex/gt 对照(持仓不同 ⇒ carry 不同), 报 Δcarry 及其符号解释(去风险慢 ⇒ 陈旧仓位多付)。
- 逐年 g 表(2022..2026, 负年显式); KING_LIVE 全套 headline。
- **BOOK 缺口(§0 (3))**: 先**逐位复现** r6 的 BOOK 项: 26 锚(W5 ∩ 归档臂有值 = 2026-08-26 04Z..08-30 20Z), d = D2.price_y4s − A0.price_bps, 均值须 = 2.6981652(s42)/ 2.8709079(s2027), 自举 `default_rng([20260911,107])`/`[20260911,110]` 复现 CI [0.5777,4.3220]/[0.8082,4.5785]; 再以 A0_DET 的 `pnl_ex/gt` 替换 A0.price_bps 得 BOOK_pf; 报 BOOK_100 − BOOK_pf = 漏单解释掉的份额(配对 CI, 同种子)。同时报随机 5 种子的 BOOK_pf 区间。**读法**: BOOK_pf 的 CI95 仍排 0 ⇒ 漏单不是 BOOK 项的主因; BOOK_pf CI 含 0 ⇒ 漏单可解释该项(描述性, n=26 无判决权, 与 r6 预注册一致)。
- 34 格 regime: 每格 n、g_A0、g_pf(两平面)、Δ、CI95、Sharpe 前后、Sharpe>3 计数前后(r12: 2/34, 0/34)。描述性。
- 尾部(W_TAIL, 2.0× NAV): maxDD(prepend 1.0)、最差日、HALT(≤−4%)、ALERT(≤−2.68%)、日 sd; A0 vs A0_DET vs 5 随机种子; 两平面; KING_LIVE∩W_TAIL 另报。**(c) 停机频率**在此回答。
### §7.5 重基臂(X1 / F / S)
`dg_pf = mean_WA[g_arm_pf − g_A0_DET]`(同种子, 两平面)vs `dg_100 = mean_WA[g_arm_100 − g_A0_100]`(归档臂, λ=1)。报 Δτ_intent 与 Δτ_exec(匹配口径)及**增量意图的成交率** = Δτ_exec/Δτ_intent; 符号翻转 ⇒ 该臂既有判决须标「在漏单口径下反号」; 不翻 ⇒ 维持。r16 X1 的既有判决 REJECT(−0.564/−0.528), r15 F UNDECIDED(+0.018/+0.019), r15 S REJECT(REJECT −0.37 v3 / v4 见 r15 RESULT)。

## §8 限度(RESULT 必抄)
1. 成交模型拟合于 2026-08-01..09-12 的 ~43 个实盘日, 一个 regime(HH 格 ≥ 94%), 前 25 天 gross 4–25k; 参与率分层是唯一的尺度迁移装置; **不得把它当作 2022–2025 的成交率事实**。
2. 跨名独立抽取低估同向残差的方向缺口方差。
3. 无冲击反馈: 成交概率不随回放 gross 变化。
4. 回放止于 2026-08-30 20Z(E-0911-D); 九月不入。
5. 停机/最差日/maxDD 为单路径统计, 无 CI。
6. 灰尘规则按 232k 常数 gross; 实盘 gross 随 NAV 逐锚变。

## §9 ENV 白名单(E-0826-D)
- 本机账本装置(`devices/r17_fillmodel.py`): 读取 0 个环境变量; 跑前断言 r14 的 23 个口径旗标无一在 `os.environ`; numpy 导入后把 `os.environ.get` 换成抛异常桩; 收据写 `env_whitelist: []` 显式空集。
- pod2 装置运行: 驱动器 `devices/r17_drive.py` 以**精确 env 字典**(不继承)启动 = `PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=3 OPENBLAS_NUM_THREADS=3 MKL_NUM_THREADS=3` ∪ §1 A0 旋钮 ∪ 臂旋钮 ∪ `OUT_TAG`; 驱动器与判官自身以 `env -i … python <dev> <whitelist>` 启动, 断言 `os.environ` 键集 == 白名单且无口径旗标前缀; 每份收据 `env_whitelist` 非空、`self_sha256`、`prereg_sha256`、输入 realpath+sha、`gpu_before/after`(期望 `0 %, 2 MiB`)、受保护 PID 333197/339489 状态(期望 T, 不触碰)。

## §10 实盘零接触
`~/dl_quant_live` / `~/wide_shadow` 只读(账本、`exchange_info_cache.json`、`rolling.npz`、源码 grep); 未写、未重启、未下单、未调交易端点; 零网络。pod2 只 CPU; 不 SIGCONT; 负载 > 6 等待。

## §11 数字标签
§1 sha 与 §1.1 的 3300/1110/5838 为本轮/前轮 pod2 实测 **VERIFIED**; §0 引用的 45.48% / 65.6% / 34.0% / +2.6982 为前轮文档转述 ⇒ 对本轮 **INFERRED**(本轮在同一账本上重测其中可重测者); 本文写定前只看过账本的**计数**(组数、类×终态计数、|Δw| 分位)与 `realized_gross/target_gross` 序列, **未看任何成交比例**。
