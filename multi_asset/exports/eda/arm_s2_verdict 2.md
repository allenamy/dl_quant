> **创建:** 2026-07-13 | **Session:** 0C suppl-factor scoring | **状态:** final (3-fold screen) | **作废条件:** metrics leak-audit / 32ch ablation 落地后重判;或 king 部署实现变更

# ARM-S2(24h 补充因子)验收判词 (0C)

**裁决: CONDITIONAL REJECT(不进书 as-is)。过 4/5 门,但 FAIL 决定性的书级边际门 (c)。+0.0277 king-正交增量是真的/大/动态,但 king 太强,ARM-S2 不抬书。两个必做前置(leak + 32ch)。**

arm = wideA_s2_y24_c1(lam_orth=0 + xattn + 39ch 含 7 metrics, YR24, 3-fold, test 2024-2026)。base = king_pred_panel(5yr, ts 行对齐, king-pred 覆盖 902/902 test 行)。

## 五门

| 门 | 判 | 值 | 说明 |
|--|--|--|--|
| **(a) king-正交增量 IC** | **PASS** | **+0.0277**(CI[.020,.035])| raw 0.0515 去 4h king 后**存活 54%**;逐 fold 2024+.024/2025+.046/2026+.013 全正;CI 排除 0。**强过。** |
| (b) pred-corr vs king | PASS | 0.24 | 24h vs 4h = 实质不同下注,远 <0.7。|
| (d) dyn-share | PASS | 0.944 | 增量是动态 timing 非静态 tilt。★但 dyn-share **不能**捕获 metrics 通道的**动态 publish-lag 泄漏**(见前置)。|
| **(c) 书级边际** | **★FAIL** | 见下 | **决定门。任何权重/成本都不显著抬书。** |
| (e) 净成本 | PASS | netSh 3.45@5bps, BE 16.8 | 24h 慢腿,日换手 ~king 的 1/6,标独立正。|

## (c) 书级边际 FAIL —— 3-way 稀释教训重演

daily corr king↔S2 = 0.20(低)。king (paper) Sharpe: gross 20.3 / maker 17.2 / taker5 12.0。S2 sleeve Sharpe: 4.9/4.4/3.4。**权重扫(maker,combined vs king-alone 改善):** w0.1 −0.01 / w0.2 −0.25 / w0.3 −0.84 / w0.5 −3.3;taker5 最好 w0.1 **+0.04(不显著)**。**⇒ 无权重显著抬书。** king (paper)Sharpe 12-20 太压 S2 的 3.4-4.9,4× 更弱的低相关(0.20)正交腿也抬不动书 = 弱因子进书=负贡献的教训。

## ★两个必做前置(接受前 blocking)

1. **★metrics 泄漏审计(blocking):** 7 个 metrics 通道(funding/OI/positioning)有**结算/发布延迟**。+0.0277 增量**只在这些通道用 ≤t 已发布值(非未来结算值)时才成立**。**dyn-share(0.944)catch 不到动态 publish-lag 泄漏。** 需 0B 的通道 build 脚本 + lag 敏感性 / shuffle-future-on-metrics 测试才能信这个增量。
2. **32ch ablation(归因):** +0.0277 增量来自 24h **价格**horizon(干净——24h 动量/反转正交于 4h king 是预期)还是 **metrics** 通道?同协议 32ch(去 metrics)跑隔离: 32ch≈39ch → metrics 无贡献(无泄漏风险也无数据价值);39ch≫32ch → metrics 驱动(泄漏审计变关键)。需 GPU。

## 部署 nuance(诚实)

(c) FAIL 被 king 的**频率膨胀 paper Sharpe(20)** 放大。若走**独立慢/便宜容量 sleeve**(三腿书逻辑: funding+DL+SIZE 接受了比 DL 腿弱得多的腿,靠分散/容量/成本)—— ARM-S2 有**窄价值**(低 corr 0.20、便宜慢换手、加容量)。但那要 king 的**可部署(非 paper)Sharpe** + 多-sleeve 部署决策,不是 signal-blend。

## bottom line

**不要把 ARM-S2 blend 进 king 信号(稀释)。** 增量真实但书级无关(king 太强)。**先解决 metrics 泄漏审计 + 32ch ablation;** 若干净且部署走多-sleeve,ARM-S2 是小权重慢 sleeve 候选,非书级提升。

---
**产物:** `arm_s2_verdict.json` · `arm_s2_core.json`(a/b/d)· `arm_s2_book.json`(c/e)· `score_arm_s2_core.py`/`score_arm_s2_book.py`(可复算)


---

# v2 段 — 32ch 终定性 (0C, 2026-07-13)

**触发: 32ch 消融 mean 0.0620 全面 > 39ch 0.0515 → metrics 通道净拖累(#29 于 24h)。泄漏审计 CLEAN(0B)。32ch 才是 S2 正身,五门重跑。**

**裁决: CONDITIONAL SLEEVE CANDIDATE → 值 5yr+seeds(升级 39ch 的 CONDITIONAL REJECT)。**

| 门 | 判 | 32ch 值 | vs 39ch |
|--|--|--|--|
| (a) king-正交增量 | PASS 强 | **+0.0285**(CI[.021,.036], 逐 fold .030/.036/.020 全正)| ~同(+.0277);32ch raw 更强但更 king-相关(0.335)故增量持平 |
| (b) pred-corr | PASS | 0.335 <0.7 | 高于 39ch 0.24(价格-only 更像 king)|
| (d) dyn-share | PASS | 0.895 | 略低于 .944 |
| **(c) 书级边际** | **★FLIP** | improve-rule Ss>ρSk **全 tier 成立**(5.56>3.78/4.93>3.26/3.91>2.33);best-blend w0.1 **+0.077/+0.084/+0.103 正但未 bootstrap-显著** | 39ch 是 ~0/负;32ch 更强 sleeve 翻正 |
| (e) 净成本 | PASS | 24h 慢 sleeve netSh 5.56/4.93/3.91,换手 ~king 的 1/6 | 同 |

**★(c) 翻案关键 —— 部署 caliber 口径:** improve-rule Ss>ρSk **对 Sharpe 均匀缩放不变**(比值判据),故无论 king 基准是 paper-20 还是可部署 -10M 档都成立。且 king 快换手在真实成本下压 Sk 更多(taker 比值 Ss/Sk 0.33 > gross 0.27)→ 可部署口径下 ARM-S2 改善**更大**。**多-sleeve 决策不系于膨胀的 paper Sharpe —— ARM-S2 是小权重(~0.1)慢正交 sleeve 的合格加项。**

**★metrics 归因(输入轴关闭 = 第 3 个 null):** 32ch 0.0620 > 39ch 0.0515 → 7 metrics 通道是 **−0.010 净拖累**(#29 于 24h,容量稀释>alpha)。继 1h-线性 + 1h-非线性后,**24h-DL-输入是 positioning/OI 数据资产经此用法的第 3 个 null**。泄漏干净但无预测价值。**数据资产保留;无新机制勿再挖 metrics-as-input。**

## 终定性

**32ch S2 = CONDITIONAL SLEEVE CANDIDATE。** 真·泄漏干净 +0.0285 king-正交增量,作慢/便宜正交 sleeve 全 tier 过 improve-rule(不像 39ch)。经验书改善(+0.08-0.10)正但 3-fold 未 bootstrap-显著 → **排 5yr+seeds** 确认增量 regime-wide 保持 + 书边际达显著。5yr 过 → 部署为小权重(~0.1)慢 sleeve(**非 signal-blend,非书变革**);5yr 褪 → 存档。


---

# v3 段 — 5yr 终判 (0C, 2026-07-14)

**裁决: QUALIFIED PASS —— S2(32ch)作小权重(~0.1)慢分散 sleeve 进书,seeds 电池确认后正式。价值 = 真·regime-robust 增量 + 最差年保护,非 headline Sharpe 提升。**

**(a)king-正交增量 逐年(2022-2026H1):** 2022 +.018 / 2023 +.037 / 2024 +.034 / 2025 +.020 / **2026 +.042** —— pooled **+0.0289**(CI[.023,.034]),**五年全正,符号一致**。★2026 增量最大 = 王座弱书年 → 分散在增量层确认。(b)pred-corr 0.31<0.7。(d)dyn 0.895。(e)慢 sleeve netSh 5.14/4.16(maker/taker)。

**★(c)书级边际:** improve-rule Ss>ρSk **全 cost-tier 成立**(ρ0.22);best-blend Sharpe 改善 +0.11(maker w0.1)/+0.19(taker w0.2)**正但 5yr 仍未 bootstrap 显著**(Sharpe-差估计噪)。**★但逐年: 组合 ~每年 ≥ king(无年变差)且抬 king 最差书年 —— taker5 下 king 最差年 2026(+5.26)→组合 +5.75,最差年地板 5.26→5.39。真·最差年/下行保护 = pooled-Sharpe bootstrap 低估的分散价值(同三腿书 funding/SIZE 腿画像: 独立弱、低相关、护最差年)。**

**抽查全清:** panel md5 1c8ad451 ts-对齐 king;24h clean(king 逐年覆盖满 n=365/365/366/365/180);2022 短训练 fold 增量 +0.018 正非退化 = σ 健康;32ch(metrics 输入轴已关,v2)。

## 终判

**QUALIFIED PASS → S2 作 ~0.1 权重慢 24h sleeve 进四腿书(funding/DL-king/SIZE/S2-24h),seeds 电池(seed43/44)确认 seed-稳健后正式。** 诚实定位: **S2 是分散/最差年保护 sleeve(真 regime-robust 增量,护王座弱年 2022/2026),非 headline Sharpe 提升器**(边际提升正但未统计确认)。seeds 过后 0C 重算四腿风险权重。剩余等 seeds。
