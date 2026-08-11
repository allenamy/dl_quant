> **创建:** 2026-07-12 | **Session:** 0C independent scorer/auditor | **状态:** final — 5yr 加冕确认 (见文末 v2 段) | **作废条件:** 5yr replay (wideA_lamorth0_xattn_5yr) 落地后重判 regime 稳健性;或 panel 重建

# lamorth0 + xattn 叠加臂审计 (0C) — "好得惊人"档

**判词: REAL(3-fold 窗审计全清)—— 待 5yr regime 确认。** #1 怀疑(xattn 静态 tilt 灌水)**已 REFUTE**(dyn-share 0.949)。唯一实质限制: **3-fold 测试期全在 2025 强/满宇宙窗**,+0.095 是强 regime 数,须 5yr replay 确认弱年(2022/2026)不塌。**GPU 5yr 跑继续,别 kill。**

3-fold ensemble(诚实口径,同 panel md5=39f5cc4e): xattn 叠加 **+0.0718 / +0.0988 / +0.1138 = mean +0.0948** vs lamorth0 +0.0672(**Δ +0.0276, +41%**)。

## 1. 动态/静态分解(shuffle-future)— 决定性,#1 怀疑被否

| fold | total | static(shuffle) | static(mean) | dynamic | **dyn-share** |
|--|--|--|--|--|--|
|0|0.0718|0.0012|0.0013|0.0706|**0.983**|
|1|0.0988|0.0046|0.0193|0.0942|**0.954**|
|2|0.1138|0.0104|0.0258|0.1034|**0.909**|
| mean | | | | | **0.949** |

**判词:** +0.095 **几乎纯 dynamic timing**(dyn-share 0.949,甚至高于 lamorth0/QIM 的 ~0.92),static-shuffle 微不足道(0.001-0.010)。**xattn 的横截面结构没有变成静态 tilt 灌水 —— 你和我的第一怀疑点被数据否决。** cross-asset attention 加的是真时变信息。

## 2. 泄漏审计 — 干净

- **panel byte-identical**(md5=39f5cc4e == lamorth0 == qim 3-fold)。
- **attention 结构安全**(读了 `cross_asset_panel.py::CrossAssetAttnLayer`):只在**同一预测小时内跨币** mix(batch_first,跨 S 不跨 B),`key_padding_mask = mask<0.5` = member-only,member 是 point-in-time ≤t。⇒ **同期横截面 mixing,无跨时/时间泄漏**(attention 是经典泄漏事故位,此处 mask 正确)。输入 CH 全 causal ≤t。
- **fold 边界**:连续不重叠测试块(te 天 302-383 / 384-465 / 466-548,各 ~82 天),8d embargo,扩张 train。无 train/test 重叠。

## 3. 配对显著性 vs lamorth0(同 fold per-ts + day-block bootstrap 3000×)

| fold | xattn | lamorth0 | Δ | CI95 | 显著 | pred相似 |
|--|--|--|--|--|--|--|
|0|0.0718|0.0569|+0.0149|[+0.006,+0.024]|是|0.49|
|1|0.0988|0.0755|+0.0233|[+0.016,+0.031]|是|0.69|
|2|0.1138|0.0693|+0.0446|[+0.033,+0.057]|是|0.44|

三 fold Δ 全 CI 排除 0(显著),且**递增**(+0.015→+0.045)。**pred 相似度仅 ~0.54**(比 QIM↔lamorth0 的 0.63 更低)= xattn 做**实质不同的横截面下注**。注: per-ts 显著在 ~490 横截面/fold 下易达成,承重证据是 dyn-share + 2×2 机制,非 CI 本身。

## 4. 机制(你的 #4 成立,系数更大)— 2×2

| | lam_orth=1.0 | lam_orth=0 |
|--|--|--|
| **xattn=F** | 0.0327 (conformer_ref) | 0.0672 (lamorth0) |
| **xattn=T** | 0.0408 (xattn) | **0.0948 (lamorth0_xattn)** |

- 去惩罚: no-xattn +0.0345(2.05×);with-xattn +0.0540(2.32×)。
- 加 xattn: 带惩罚 **+0.0081**;去惩罚 **+0.0276**。
- **★判词:** 正交惩罚**压制了 cross-asset attention ~3.4×**(xattn 带惩罚只贡献 +0.008 vs 去惩罚 +0.028)—— 不是完全掐死但重度压制;**两个 lever 协同**(去惩罚在有 xattn 时增益更大,xattn 在去惩罚时增益更大)。这修正了我口头初判的"惩罚时几乎+0"(那用了 best-head 0.034;诚实 ensemble 是 0.0408,xattn 带惩罚仍 +0.008)。惩罚-稀释档扩充:xattn 臂系数更大。

## ★ 关键 caveat — 为什么 5yr 必须跑

**3-fold 测试期全在 2025**(天 302-548/549 = 末 45%,全落强 regime + 满 110 成员宇宙 = DL 最 favorable 窗)。历史臂(QIM 5yr)显示 **2025 = 最强年(0.081)**,弱年(2022 ~0.044、2026 flat)**不在本窗**。fold2(最近 ~2025-08→10,宇宙最满)xattn 边际最大(+0.045)—— 与"attention 受益于 breadth"一致(良性),但也强调这是**近期-满宇宙**结果。**+0.095 是强 regime 数;5yr replay(wideA_lamorth0_xattn_5yr,跑中)是确认弱年不塌的必需实验 —— 审计没发现任何 kill 理由,继续跑。**

## 结论

**REAL(3-fold 审计全清:复现精确 / 泄漏干净 / dyn-share 0.949 非静态灌水 / 配对显著 / 机制 2×2 coherent)。判据待 5yr:** 若 xattn 边际在 2022/2026 弱年保持 → 真 paradigm 升级(cross-asset attention 是继"去惩罚"后的下一个真 lever);若弱年塌 → 强-regime-only 杠杆(仍有条件价值但非全 regime 冠军)。**不 kill 5yr。**

---
**产物:** `xattn_stack_audit.json` · `xattn_stack_audit.py`(可复算)


---

# v2 段 — 5yr 加冕终判 (0C, 2026-07-12): cross-asset attention = 第二 lever

**判词: 加冕确认。cross-asset attention 是继"去惩罚"后的第二个真 lever,regime-robust。书升到 ~0.084 级。我上一 doc 的"强-regime-only"降级假设 REFUTED。** 三 panel byte-identical(md5=185d3b65)。

5yr ensemble(诚实口径): xattn **+0.0483/+0.0802/+0.0859/+0.1041/+0.0988 = mean +0.0835** vs lamorth0 0.0642 / QIM 0.0672(**+0.0193 mean, +30% vs QIM, +41% 峰值窗口对 lamorth0**)。

## 1. 逐年配对(per-ts + day-block bootstrap 3000×,重点弱年)

| 年 | xattn | lam | qim | Δvs_lam | CI95 | 显著 | dyn-share |
|--|--|--|--|--|--|--|--|
|**2022 弱#1**|.0483|.0423|.0443|**+.0060**|[.0015,.0107]|**是**|0.932|
|2023|.0802|.0637|.0640|+.0165|[.0123,.0204]|是|0.945|
|2024|.0859|.0737|.0697|+.0122|[.0079,.0163]|是|0.993|
|2025|.1041|.0639|.0807|+.0402|[.0348,.0453]|是|0.971|
|**2026 弱#2**|.0988|.0775|.0774|**+.0213**|[.0156,.0269]|**是**|0.955|

**★ xattn 边际对 lamorth0 五年全正全显著,两个预注册弱年(2022/2026)都站住,2026 边际反而最大之一(+.021)。降级假设 REFUTED —— cross-asset attention 跨 crash-recovery/chop/strong/drift 全 regime 加真边际。** 对 QIM 亦每年显著。

## 2. 逐年动态/静态 — dyn-share 0.959,2025 峰值不是灌水

dyn-share 均值 **0.959**,每年 ≥0.93(0.932/0.945/**0.993**/**0.971**/0.955)。**"好得惊人"的 2025 +0.104 = dyn-share 0.971 = 几乎纯 dynamic timing,非静态 tilt 灌水。** static-shuffle 微不足道。+0.084 是五年真 dynamic 内容。

## 3. 净成本(xattn 书重跑,不沿用 QIM 画像)

| 年 | 换手 x/q | BE x/q | nSh@0 x | nSh@2.3 x | nSh@5 x/q | nSh@9.5 x |
|--|--|--|--|--|--|--|
|2022|1.85/1.70|8.35/6.51| |—|**5.33/2.12**| |
|2023|1.99/1.75|10.1/9.21| | |10.1/6.70| |
|2024|2.05/1.63|14.2/15.9| | |14.5/12.4| |
|2025|2.27/1.51|11.8/16.0| | |14.0/12.9| |
|2026|2.00/1.83|7.96/4.92| | |**5.28/−0.13**| |

- **换手确实变了**(你的 #3 担心成立):xattn ~2.0 vs QIM ~1.7(+15-40%,attention 下注不同→churn 更多)。
- **但净 Sharpe@5bps 五年全高于 QIM**;★**2026(弱年)xattn @5bps net-正 +5.28,QIM 是水下 −0.13** —— 高 IC 完全盖过多出的换手。BE 8-14 健康(2024/25 略低于 QIM 因换手高,但净 Sharpe 仍更高)。

## 4. 执行画像增量 — 容量档需小修

换手 ~2.0 vs 1.66 → 容量收紧 ~15-20%(小币参与约束早 ~20% 触顶)。**xattn 书起步修为 ~$4-8M gross(QIM 是 $5-10M),软天花板 ~$40-80M。** net-Sharpe-per-AUM 仍优于 QIM。**高换手书 → live maker-fill pilot 更关键。** 全容量 re-sim 可选(线性换手缩放足够)。

## 5. 三实现 blend — 不推荐(xattn 已太强,blend 反稀释)

3-way(QIM+lamorth0+xattn 等权)mean **0.0812 < 单 xattn 0.0835**。仅 2022 弱年 blend 微胜(0.0509 vs 0.0483);4/5 年单 xattn 胜。**⇒ 3-way blend 不推荐;之前 QIM+lamorth0 blend(那时两者co-equal)已被 supersede。** xattn 现在太 dominant,掺弱实现只掉 ~0.002。**部署 = 单 xattn(lamorth0+xattn)。**

## 6. 部署判词

**换部署实现为 lamorth0+xattn(xattn 叠加)** —— 每年 dominate QIM 和 lamorth0(对两者皆显著)。书从 ~0.067(QIM)升到 ~0.084(xattn),+25%。**单实现,非 blend。**

## 7. 加冕前建议:seed 确认

**建议发 seed43/44(G2 gate)再最终加冕。** +0.0193 mean 边际 > 3-fold 单 fold seed spread(±0.01-0.015),大概率 seed-robust,但加冕第二 lever + 2025 +0.104 峰值值得一个 3-seed 检查。相对 claim 很便宜。

## Leaderboard 影响

重排:无惩罚 xattn(0.0835)现 #1,高于 QIM(0.0672)、lamorth0(0.0642)。**惩罚-稀释修正 + cross-asset attention 合起来把原带惩罚臂 leaderboard 数大致 ×3。**

---
**v2 产物:** `xattn_5yr_coronation.json` · `coronation_xattn_5yr.py`(可复算)
