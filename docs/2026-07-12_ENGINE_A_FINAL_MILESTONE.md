# Engine A（宽宇宙 DL 因子挖掘）— FINAL MILESTONE

> **创建:** 2026-07-12 19:20 JST | **Session:** fable multi-asset-v2 autonomous | **状态:** final | **作废条件:** 部署实现变更或新 lever 加冕时由后续 milestone 取代
> 交叉引用: 判决细节 `docs/2026-07-11_EngineA_leaderboard_RESULTS.md`; 预注册 `docs/2026-07-11_EngineA_leaderboard_prereg.md`; 范式调研 `docs/2026-07-11_v3_paradigm_research_top5.md`; server 产物 `exports/eda/{qim_final_verdict, xattn_stack_audit, xattn_5yr_coronation, xattn_g2_seeds, qim_execution_feasibility, book_assembly, xattn2_adjudication, queue_precheck}`

## 一、终态（部署卡）

**部署实现: 单 `lam_orth=0 + xattn(n=1)` 模型**（Conformer stem d=64 + 1 层跨资产注意力 + 6 无约束头诚实 ensemble，255K 参数，110 币小时面板，YR4 残差目标 = 增量-over-[funding+zoo]）。

| 指标 | 值 |
|---|---|
| 5yr 扩张 walk-forward 逐年 | 2022 +0.0483 / 2023 +0.0802 / 2024 +0.0859 / 2025 +0.1041 / 2026H1 +0.0988 |
| headline | **mean +0.0835，五年全正**（vs GO 书 QIM 0.0672，+25%）|
| 动态占比 | 0.959（非静态 tilt）|
| seeds (3-fold) | {0.0948/0.0910/0.0973} CoV 2.7%，9/9 格全正单调 |
| 净成本 | BE 8-14 bps/side；net-Sh@5bps 五年全正（含 2026 弱年 +5.28）|
| 容量 | 起步 **$4-8M** gross（x=1% maker 参与），软天花板 $40-80M |
| 组合位置 | 三腿书: funding 0.30-0.325 / **DL 0.35-0.40** / SIZE 0.30-0.325（腿 corr 近零到负，领导权轮动，2026 弱 DL 年组合 +2.07）|
| **剩余部署条件** | **(a) $2-5M live maker-fill pilot**（高换手书,实测 fill/slippage/逆选择）**(b)** ≥100 成员 regime 偏好（2024+）|

**★ 轨 1 保守回放校准 (0C 2026-07-12 PM, `exports/eda/makerfill_calibration.{json,md}`) — PILOT 值得开:** 14 mega-cap bar_1s 保守成交模拟 (join-at-back 全 L1 队列 + 仅 trade-driven 消耗 + 不记 spread-capture = 成本 floor)。发现: **fill 曲线在 f=订单/小时成交额 空间流动性无关** (f≤0.5% fill>0.95, f~2% 崩); adverse markout 极小 (−0.03~−0.38bps 全谱)。**保守下界: 全书逐年净正含弱年, 有效成本 ~1.5-1.9bps (vs 加冕用的 5bps taker, 砍到 1/3); calib-grounded 书 (≥$4M/h 31 币, 零外推) 独立净正 → 外推尾非承重**。109/140 宽币在校准底之下 (外推段显式 haircut)。**Pilot 建议书: $2-5M, 交 calib-grounded/mega+mid 核心, k=300-900s 被动+残余 taker; 成功判据 fill≥0.40@k300/成本≤2bps/markout≤2×; 止损 成本>3.5bps 持续。**

**★ 轨 1 深化 — tick 级验证 (0C, `exports/eda/makerfill_deepdive.{json,md}`, BTC Tardis µs 真 FIFO 队列 vs 1s-bar 同天同单):** **1s-bar 近似两轴皆乐观、不互相抵消** — fill 高估 ~1.5× (1s 把全部对手量算队列消耗; tick 只有价≤挂单价的成交才消耗)、markout 基本漏掉逆选择 (1s 抹平 µs 逆向移动; tick 实测 calm −0.97 / normal −1.71 / stress −3.24 / 崩盘日 −5.3 尾 −20bps = **强 regime 依赖, 压力降级 3-5×**)。fill 流动性无关性崩盘日仍成立。**tick 修正后书级影响温和: 有效成本 1.5→1.9 (normal) / 2.7-2.9 (stress) bps, 全场景逐年净正含弱年 — PILOT 判词存活**, 修订: k=900 被动 (fill 0.51)、**新增 vol-gate (BTC rvol>~18bps/min 时减参与/趋中性)**、成功判据实测 markout≤tick 值。**最大残余 (只能 pilot 实测): alt-leg 逆选择未测, 大概率差于 BTC。方法论教训: 1s-bar 不是 maker-fill 的保守代理 — 它乐观; 执行建模的 markout 必须用 tick。**

## 二、机制档案（本阶段的科学产出）

**信号 = 110 币残差空间的短期横截面反转**（买近期残差输家；forward-decay 因果签名: lag0 峰值平滑衰减 + 负 lag 反号 −0.15 = 反泄漏铁证；fill-window 安全: +1h 保留 90%）。

**机制 2×2（诚实 ensemble，同 panel，全 byte-check）:**

| | lam_orth=1.0 | lam_orth=0 |
|---|---|---|
| 无 xattn | 0.0327 | 0.0672 |
| 有 xattn (n=1) | 0.0408 | **0.0948** (3f) / 0.0835 (5yr) |

- **Lever #1 去正交惩罚**（+0.035）: stage2b `lam_orth=1.0` 逼 K 头彼此正交 = 把容量花在"彼此不同"而非"预测准"，自 Engine A 启动砍半所有臂。头类型无关（K-head vs 25-分位 pinball 五年配对打平，预测相似度 0.63 却同水平 —— 水平由去惩罚解锁）。
- **Lever #2 跨资产注意力**（clean 基线上 +0.028）: 被惩罚压制 ~3.4×（带惩罚时仅 +0.008）。两 lever 协同。
- **饱和边界**: n_xattn=2 CLOSE（增益落单层 seed 带内 + fold0 过拟合尖峰）—— **一次 message-passing 已提尽**; aux-MTL REJECT（clean 基线上反伤 −0.012）。

## 三、完整弧线（2026-07-11 → 07-12，约 36h）

范式赛马（QIM pinball 头 2× 领跑）→ 硬化电池（5yr 回放/seeds/lam_orth 消融）→ **归因修正**（0C: 2× 边际 = 去惩罚非 pinball，"范式转移"实为 loss-bug 修复）→ CONDITIONAL GO → 执行可行性 + 三腿装配（v1 123d 窗陷阱 → v2 1362d 全历史）→ 机制五年闭环 → **GO** → xattn 叠加（+41%, 审计 REAL）→ 5yr 两弱年站住 → **加冕** → G2 seeds → **CROWN SEALED** → 后加冕队列（aux REJECT / xattn2 CLOSE）→ **收敛收官**。

## 四、教训存档（防重犯）

1. **正交惩罚 loss-bug**: 多头强制正交挖多因子 = 反模式；正交性事后去重，不写进 loss。
2. **协议对标纪律**: 3-fold mean 与 5yr mean 巧合相等（0.0672==0.0672）差点误判；禁跨协议对标。
3. **stale save_tag 撞名**: 新跑覆盖前盘上是旧带惩罚 JSON；判决必须从 run config 核对关键 flag，不信文件名。
4. **pred-corr 预检条件性**: 只对共享已测 lever 的同代干净臂可靠（xattn 0.42→+0.028 命中）；带惩罚旧臂的低 corr = 伪多样性（aux 0.277→−0.012 落空）。
5. **装配窗陷阱**: 123d 联合窗（DL 强年切片）给出的权重/相关性全是假象；跨腿分析必须用全历史共享窗。
6. **诚实口径三件套**: ensemble 非 best-head；动态分解防静态灌水；headline 用 mean 非峰值年。
7. **双人验证的实际回报**（本阶段 4 次拦截）: 归因错误 / 协议错标 / stale 撞名 / blend 稀释。

## 五、可选下一阶段（未排期，等用户方向）

- **$2-5M live pilot**（部署侧头号事项，待批）；
- ARM-MIX / FinPFN 余臂（需重开 builder；EV 递减 —— FinPFN 主打 regime 漂移，而 5yr 全正说明漂移非当前绑定约束）；
- funding 主书刷新 + 组合月度再平衡工程化；
- 宽宇宙数据面扩展（funding/OI 逐币，wide 面板当前只有价量+carry 基线）。
