> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 冻结, 先于本轮任何数字 | **作废条件:** 输入工件 sha 改变

# PREREG · r13 VERDICT STAGE (T1)

## 0 角色与可达裁决上限
本阶段**不建新臂**, 不产生新候选。它只做三件事: (a) 独立重算 build 报的头条数字; (b) 跑 build **未跑**的 6 项对抗检验; (c) 回答任务书第 4 问(停机线), 该问 build 只算了 2.0×。
**可达裁决上限 = build 自己的裁决。** 本阶段只能**维持或下调** T1 的裁决, **不能上调**。即使对抗检验全过, T1 仍是 REJECT-as-alpha, 因为主统计量 dg 的 CI 含零这一条本阶段不重测也不推翻。

## 1 K(总检验数) = 6
V1 重算奇偶(dg / CI / Sharpe / sd)· V2 去杠杆伪装 · V3 停机线判据(2.0× 与 1.40×)· V4 等停机杠杆 · V5 波动削减的逐年稳定性 · V6 换手口径三数复核(1.4375 vs 1.7821)。
**无 Bonferroni 校正**: 这 6 项不是候选臂, 没有一项能让 T1 被录取; 它们只能**杀**。杀不需要多重校正。

## 2 主统计量(承袭, 不重选)
`g = net_ex / gross_total`, bps/锚/单位 gross。`dg = mean(g_ov) − mean(g_base)`, 窗 `W_ALPHA n=9138`。
CI95 = UTC 日块自举 2000 次, `numpy.default_rng([20260905,k])`, 统计量 = `sum(Δnet)/n_anchors` 的配对差。
`Sharpe_ann = mean/sd(ddof=1)*sqrt(2190)`, `SE = sqrt(2190/n)`。
窗: `W_ALPHA` 用于全部均值/CI/Sharpe/换手; `W_TAIL n=10038` 用于全部 maxDD/最差日/停机。两窗不混。

## 3 阈值(全部先于数字)

| 检验 | 阈值 | 破了会怎样 |
|---|---|---|
| **V1 奇偶** | 重算 `dg` 与 build 报的 `+0.0077` 差 ≤ **1e-3** bps; 重算 `mean g_base` 与归档 `0.6341957` 差 ≤ **1e-6**; 重算 `Sharpe_base` 与 `1.2912234` 差 ≤ **1e-6** | 破 ⇒ build 的账本不可信, 整轮 VOID |
| **V2 去杠杆伪装** | `g_ov ≈ b·g_base` 的残差比 `sd(g_ov − b·g_base)/sd(g_base)` ≥ **0.05** 才算"不是纯去杠杆"。另: 若 `b ≤ 0.92` 且残差比 < 0.05 ⇒ **−9.1% 波动是假的**(等价于把书缩小 9%) | 破 ⇒ §8 那条"唯一活口"作废 |
| **V3 停机线** | 判据(r12 冻结): `E[halt] ≤ 1.0/yr` **且** `P(1y maxDD ≥ 25%) ≤ 10%`。两条**同时**满足才叫过。在 `W_TAIL` 上, 杠杆 **2.0×** 与 **1.40×**, base 与 overlay 各算一次。1y 窗 = 滚动 365 个连续日行 | 不设"破"——这是回答, 不是门 |
| **V4 等停机杠杆** | 找 `L*` 使 overlay 在 `W_TAIL` 上的 halt 数 = base@2.0× 的 halt 数; 报该 `L*` 下的年化。**另**找 `L_1yr` 使 overlay 的 `E[halt] ≤ 1.0/yr` 且 `P(1y maxDD≥25%) ≤ 10%` 同时成立, 报其年化 vs base 在同判据下的 `L`。**这是本阶段唯一的新数字, 明确标注为诊断, 不是部署建议** | — |
| **V5 波动逐年稳定** | `sd(g_ov) < sd(g_base)` 必须 **5/5 年**成立, 且池化 CI95 排除零, 才叫"稳"。否则标为**不稳** | 破 ⇒ 活口降级为"仅某些年" |
| **V6 换手口径** | 三数 `mean(gross_total)` / `mean(turn_raw)` / `mean(turn_raw/gross_total)` 本机重算; 比值 `mean(t/g)/mean(t)` 与任务书断言的 **1.4375** 比。若 ≠ 1.4375 ⇒ **任务书该句有误, 必须更正在案** | 破 ⇒ 更正任务书与 r12 预注册的在案表述 |

## 4 输入(逐个哈希, 装置启动时硬断言)
- `r13_B_withinhalf/receipts/r13B_series.npz` = `f1b84e2796cf59d7036f229d6a9ba432daec53632f1b1570814391259bd68aa1`
- `r13_B_withinhalf/receipts/RECEIPT_r13B_stage2.json` = `73d4db8960b7e13d2961174a03a9fb4c2766de60e1ff76ef8bd22e66df060db4`
- `r13_B_withinhalf/receipts/RECEIPT_r13B_full.json` = `c8614f7a45ad9dd9eb702fe310f1b373e93a2239a6aab0f068995194fa6f24f8`
- `r13_A_halfscale/receipts/r13A_arms.npz` = `c9a58719d57c0acffa3034bd46a2a6c80ac3c58af6184cd6117584d95c956784`
- `r13_A_halfscale/w10_sleeve.py` = `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650`(= CALIBER PIN v4)
- `r13_A_halfscale/costb_PWR_G230k.json` = `295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53`

## 5 口径禁令(CALIBER_PIN_v4)
禁 `dlw_ext` / 任何 `_ext` 缓存 · `pod_fea_ext.py` · 裁剪复利记账(E-0908-B) · `pod_legs_ext.py` · `shadow_bundle_v3` · `wide_fea_v2ext_meta` · `panel_source.py` 默认脏面板 · 对 pod 5m 谱系施 `expm1`(E-0904-F)。
本阶段**不碰面板**, 只读上述已归档的每锚序列, 所以上述谱系一个都不经过 —— 但仍逐条断言不在输入路径里。

## 6 实盘零接触
`~/dl_quant_live` / `~/wide_shadow` 本阶段**一个字节都不读也不写**。无网络。无 GPU。

## 7 ENV 白名单(E-0826-D)
`env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/Users/haosiyu` 启动; 白名单枚举并写进收据; 禁用前缀逐个断言不存在。
