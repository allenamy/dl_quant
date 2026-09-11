# PREREG · r12 · 换手整形/深平滑轴重开(冻结于第一个数字之前)

> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **分支:** research/book-uplift-2026-09-11 | **状态:** 冻结 | **作废条件:** 口径钉 `CALIBER_PIN_v4_2026-09-11.md` 被更新的链取代, 或装置 `w10_sleeve.py` 换代
>
> **重开依据(形式要件):** memory `adaptive_turnover_family_closed` 自带作废条件「信号栈/成本口径换代 ⇒ 重测」。
> 成本口径已在本 programme 内换代: 平坦 1.9/3.115 bps 假设 → 拟合分档模型 `r3k/costb_PWR_G230k.json`(K=0.17 拟合值, 冲击指数 α=0.87)。该轴形式上重新打开。

## §0 在役形态(先读实盘树, 不读文档)

| 项 | 值 | 文件:行 |
|---|---|---|
| EMA α | **0.1** | `~/wide_shadow/shadow_bundle/config.json` → `params.alpha` |
| 免交易带 b | **0.00025**(权重口径) | 同上 → `params.band` |
| 消费者(king 形态生产者) | `sm = H + α(tgt−H)`; `sm = where(|Δ|<b, H, sm)` | `~/wide_shadow/shadow_loop_v3.py` **L492–L494** |
| 消费者(在役 combo 书) | 同式, 两条链各自 EMA 态 | `~/wide_shadow/fea171/combo_stage.py` **L90–L92**(`chain()`) |
| 执行器侧 | **不叠加**: 外部书路径显式跳过 harvest EMA 与中性带 | `~/dl_quant_live/scheduler/anchor_loop.py` **L1486–L1494**, **L1695–L1699** |
| 回放装置内同一常数 | `0.1` / `2.5e-4`, 两条链 | `w10_sleeve.py` **L253–254**(king), **L293–296**(F10) |

## §1 装置

`w10_r12.py` = 钉住的 `w10_sleeve.py`(sha256 `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650`)+ 三个环境旋钮 `{SMA, SBAND, AUX12}`, 逐处替换由 `mk_device.py` 断言只命中一次。
`float("0.1")==0.1` 且 `float("2.5e-4")==2.5e-4` 逐位相等 ⇒ **默认值下 rec/W 必须逐位不变**。

**GATE G1(关门条件)**: `SMA=0.1 SBAND=2.5e-4 AUX12=0`, 其余 env 与 r8 BASE 逐字同, 产出的 `d30_n2_c42_rec` 与 `d30_n2_c42_W` 必须与归档在役臂 `/workspace/uplift_2026-09-11/r8_inbook/arms/R8_A0_dyn_s42.npz` **`np.array_equal` 为真**。
**不过则停, 并如实报告** —— 此后一切都在量另一本书。
(`config_json` 允许不同: 它多了 `SMA/SBAND/AUX12/R12` 自报字段。逐位断言只对 rec/W。)

**AUX12=1 追加, 绝不参与书**: 逐锚保存未整形目标书 `_tb = (1−φ)·tgt + φ·tgt_F10`(= α=1, b=0 的瞬时书, 同样施加 `_nonsel` 强制出场与 depth 封锁), 以及逐锚标量 `{turn_ex_member, turn_ex_all, gross_target, dist_sm_tgt, n_band_king, n_band_f10, nmember, f10_degenerate}`。
**GATE G1b**: `AUX12=1` 与 `AUX12=0` 的 rec/W 亦必须逐位相等。

## §2 网格(K 先于数字声明)

| 轴 | 取值 | 个数 |
|---|---|---|
| `SMA`(EMA α) | 0.05, **0.10(在役)**, 0.15, 0.20, 0.30, 0.50, 1.00 | 7 |
| `SBAND`(带 b) | 0.0, 1.25e-4, **2.5e-4(在役)**, 5.0e-4 | 4 |

**K = 28**(全格, 无自适应, 无逐格加格)。在役角 = (0.10, 2.5e-4)。
二级格(条件, 先声明不算选型): 主格胜者 + 在役角, 换种子 `FSEED=2027 / FPRED=f10_A0_s2027.npy`, 检验符号一致性。

BASE env(与 r8 `drive.py` 逐字同, 动态席位, 臂 `d30_n2_c42`):
`LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=<hc>/masks/umask_UPIT_CRYPTO.npz SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy COSTB_JSON=/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json FSEED=42 FPRED=f10_A0_s42.npy`
全 env 逐格落盘(E-0826-D)。

## §3 统计(冻结)

- **g_t = net_ex_t / gross_total_t**, bps/锚/单位 gross(rec 列 18 / 列 5)。
- CI95 = UTC 日块自举, 2000 次, `numpy.default_rng([20260905, k])`, k=0 主 / k=9 复核。装置 `r8_inbook/fastboot.py`(已对 round-5 逐位验过)。
- Sharpe = mean/std × √2190; SE(Sharpe) = √(2190/n)。
- **换手 = 匹配口径**: 主报 `mean_t(turn_ex_all_t / gross_total_t)`(与 g 同为逐锚比值), 附报 `mean(turn)/mean(gross)`(比值的比)。**绝不把原始 Σ|dw| 与 g 并列**(常数钉: 混用是 1/0.6956 = 1.4375 倍错误)。
- **暖机**: 只在**alpha 问题**上 drop 前 900 锚(E-0911-A); **尾部/停机问题一律不 drop**(它会丢掉样本最差日 2022-06-07 −11.1714%)。两套数字分别标注。
- **成本**: 主结论在钉住的 `costb_PWR_G230k.json`; 另报「若 3.2× 重定价为真」时变化的**符号**(该 3.2× 在我方两台仪器间仍有争议, 不采信任何一方)。
- **null**: 若出现录取候选, 用换手匹配 null(`r3_attack_b9646/null.py` 的 SHIFT101/503/1009 + RELAB1-3), 不用逐锚置换 placebo(已知缺陷)。

## §4 regime 划分(自报, 若 r12_regime 代理落盘则改用其划分并注明)

由面板自身构造, 逐锚, 因果(只用 ≤t 的信息):
- `mkt_t` = 当锚成员 4h 收益中位数; `bre_t` = 成员中 24h 收益为正的比例(6 锚滚动)。
- **R1 普涨(broad rally)**: `bre_t ≥ 0.75`
- **R2 普跌(broad selloff)**: `bre_t ≤ 0.25`
- **R3 崩后反转(post-crash reversal)**: 触发日 = 滚动 24h 市场收益 ≤ 该量全样本 2% 分位; 窗口 = 触发后 1–12 锚(含), 与 R1/R2 重叠时以 R3 优先。
- **R4 其余**。
另报**年**与**用户具名的两次停机形态**(山寨暴涨后回调 / 空头深负 carry)对应的锚集。

## §5 判决规则(先于数字)

**目标函数(非 Sharpe)**: 在诚实实盘波动口径下(回放 σ × **1.4042**, r11 实测; 书 gross 2.0×NAV)
> 最大化 **1 年 CAGR 中位数**, 约束 **E[触及停机线次数] ≤ 1/年** 且 **P(1 年 maxDD ≥ 25%) ≤ 10%**。

停机线与回撤线取实盘策略常数(`~/dl_quant_live/live/watchdog.py`): `DAY_LOSS_LIMIT_PCT=-4.0`(L109, 股本 %), `DAY_LOSS_ALERT_PCT_OF_EQUITY=-2.68`(L117, 只告警), `DRAWDOWN_LIMIT_PCT=-25.0`(L131, 自起始股本)。

**「在役角仍是对的角」** ⇔ 没有任何格同时满足: (a) 在上述约束下 CAGR 中位数更高; (b) Δg 的 CI95 不含 0 **或** 约束项(停机频率/maxDD)严格改善; (c) 两个种子同号。
只要有格满足 ⇒ 报告方向与幅度与 CI, 并明说在役角不是最优角。

## §6 响应性(本轮的决定性测量, 此前从未产出)

1. **脉冲响应/有效滞后**: 对每格, 逐 lag k=0..24 求 `β_k = Σ_t ⟨sm_t, tgt_{t−k}⟩ / Σ_t ⟨tgt_{t−k}, tgt_{t−k}⟩` 的截面投影谱(在 sm 的持仓空间内), 归一后 **有效滞后 = Σ k β̂_k**(锚)。理论对照: 无带时 β_k = α(1−α)^k, 有效滞后 = (1−α)/α。
2. **带的咬合率**: `n_band_king / nmember` 逐锚, 以及死区宽度 `b/α`(权重口径)对比当锚平均 |w| = gross/nsel。
3. **滞后的代价**: 在 R1/R3 两态里, 比较在役角与 α=1,b=0 的瞬时书的 g 分解(pnl_ex / carry_ex / cost_ex), 报「滞后买来的成本节省」与「滞后放弃的毛额」谁大, 带 CI。

