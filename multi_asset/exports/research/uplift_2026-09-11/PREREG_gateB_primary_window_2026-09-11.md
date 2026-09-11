# PREREG · GATE B — the primary evaluation window, chosen on regime representativeness and sample size only

> **创建:** 2026-09-11 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 预注册; 判据冻结于 §3, **后果已在 §5 全数摊开**; 需用户裁定才能改 `judge_v4.py` | **作废条件:** regime 变量定义改变, 或 trackF `regime_labels.npz` 重建后 §2 的 L1 排序反转
> **口径 PIN:** v4 chain 2026-09-09。regime 变量与标签 = 第二轮 Track F 的原件 `trackF/{build_regime.py, label_and_arsenal.py, regime_labels.npz}`, 未改一行: `sig_fund` = 1e4 × 成员 8h 等价费率横截面 sd, `disp24` = `f_rev_24h` 横截面 sd, expanding-median 二分, BURN = 2190, 标签对未来行洗牌不变(原件自带断言, 在 i=3000/6000/9000 处 PASS)。
> **GATE P:** PASS(逐位, 见 `PREREG_gateA_offset_spectrum_2026-09-11.md` 抬头)。
> **装置:** `r3_gates/devices/regcomp.py` sha256 `30fee017…`, `r3_gates/devices/rejudge.py` sha256 `e3e87778…`。

## §1 问题
冻结窗 2025-03-01..2026-08-10 20Z 是当前唯一的判决窗(`judge_v4.py` 第 49 行 `FROZEN`)。它 **94.3% 落在单一 regime 单元**。看到这件事之后再换窗是 p-hacking; 不换就是拿单一 regime 样本判所有跨 regime 主张。

## §2 每个候选窗的 regime 成分 — VERIFIED(`r3_gates/regime_composition.json`)
标签口径 A = 第二轮的 expanding-median(轮二"94.3% vs 60.1%"两个数在此**逐数复现**: 冻结窗 HH = **0.9430**; 全史**已标注**锚中 HH = 0.587/0.977 = **0.6008**)。
标签口径 B = 全样本中位数二分, **纯描述性**(不可交易), 用来剥掉 expanding median 对趋势的偏置。

| 窗 | n | SE(Sharpe)=√(2190/n) | HH 份额 (A) | L1 vs 全史 (A) | HH 份额 (B) | **L1 vs 全史 (B)** | eff cells (B) | A0 Sharpe |
|---|---|---|---|---|---|---|---|---|
| FROZEN 2025-03-01..2026-08-10 20Z | 3168 | **0.831** | **0.943** | **0.672** | 0.833 | **0.968** | **1.419** | 3.043 |
| 2024-on..2026-08-10 | 5718 | 0.619 | 0.713 | 0.212 | 0.529 | 0.361 | 2.78 | 2.475 |
| F23 2023-01-01..2026-08-10 | 7908 | 0.526 | 0.587 | 0.012 | 0.405 | 0.114 | 3.36 | 1.628 |
| **FULLCYCLE post-warm..2026-08-10** | **9018** | **0.493** | 0.515 | **0.012** | 0.363 | **0.046** | **3.459** | 1.524 |
| 全史参照(10039 锚) | 10039 | 0.467 | 0.474 | 0 | 0.349 | 0 | 3.457 | 1.213 |

regime 变量水平(描述): 冻结窗 `sig_fund` 均 16.46 / 中位 12.91; 全史 8.53 / 4.50 ⇒ **冻结窗的费率离散是全史中位的 2.9 倍**。

**关键: 代表性与样本量没有取舍。** FULLCYCLE post-warm 同时是 n 的 argmax **和** 两种标签口径下 L1 的 argmin。把 A0 自己放进去看得更清楚: 同一条书在冻结窗读 3.04, 在全周期读 1.52 — 差的 1.5 Sharpe 是**窗口成分**, 不是书。

## §3 冻结规则 — RULE W
1. **PRIMARY = 该臂与其对照(A0)共同定义的最长跨度, post-warm**(丢 E-0911-A 的前 LOOK=900 锚), 上界 2026-08-10 20Z。判决(A)/(B)/(C) 只在 PRIMARY 上下。
2. **窗口可受理条件**(在看任何臂之前算, 只用 regime 变量与日历, 与任何臂的收益无关): (a) n ≥ 5000 锚; (b) **两种标签口径下 L1 vs 全史 ≤ 0.15**。FROZEN(0.672 / 0.968)与 2024-on(0.212 / 0.361)**不受理为判决窗**; F23(0.012 / 0.114)与 FULLCYCLE(0.012 / 0.046)受理。
3. **FROZEN 降级为稳定性诊断, 不再有否决权**: 它只能触发一条 **非矛盾要求** —— PRIMARY 上 (A) 的臂, 其 FROZEN 点估计不得反号。反号则降为 (C)。
4. **跨度缺陷罚则(对称代价)**: 不能覆盖 PRIMARY 的臂(RESID_SHARPE 按构造无 2022, walk-forward 折 2023-2026), 其最好可得判决是 **PROVISIONAL**, 且它选定的跨度计入该臂自己的 Bonferroni K。**规则不因为一个候选跑不动全周期就迁就它。**
5. **本规则不改 `judge_v4.py` / `ELIGIBILITY_CONTRACT.json`** —— 提议 diff 见 §6, 需用户裁定。

## §4 为什么这不是 p-hacking —— 以及它在哪里仍然是
- 受理判据(L1、n)是 **regime 变量与日历的函数**, 不含任何臂的收益。`regcomp.py` 在 `rejudge.py` 之前运行(会话记录可查)。
- **但我必须说出口**: 第三轮的任务书**在我动手之前就告诉我** XIB_LAG50 在全周期强、在冻结窗 (C)。所以我**没有盲性可以主张**。可用的辩护只有两条: 判据与臂无关且先于再判决冻结; 以及 §3-4 的对称罚则对另一个活口(RESID_SHARPE)确实收了钱。**用户应当把这一条当作本提议的主要风险来裁。**
- 反向检查: 若换窗只是为了放行 XIB, 那么最省事的窗是 F23(XIB 在那儿也全 PASS 且 n 更小 SE 更大)。我选的是 L1 最小、n 最大的那个, 与"挑最有利"不一致。

## §5 换窗会改哪些既有判决 — 全数摊开(VERIFIED, `r3_gates/rejudge_windows.json`)
统计量逐字复制 `judge_v4.py`: g = net_ex/gross_total, 逐锚配对 d = g_arm − g_A0, UTC 日块 bootstrap 2000, rng `default_rng([20260905,k])`。K = 4(§3-2 在看臂之前枚举的四个候选窗)。
**注:** 我的 CI 与判官的 CI 在同一臂上会有小差, 因为 rng 子流索引不同(已知性质 [judge_ci_depends_on_arm_set]); **点估计逐数相同**(冻结 dyn s42 **+0.4698**, s2027 **+0.3932** = 任务书的数)。

**XIB_LAG50 − A0:**
| 窗 | dyn s42 | dyn s2027 | fix s42 | fix s2027 | 判决 dyn / fix (CI95) | 判决 (BONF K=4) |
|---|---|---|---|---|---|---|
| FROZEN(现行) | +0.4698 [+0.096,+0.838] | +0.3932 [−0.004,+0.767] | +0.1612 [−0.334,+0.633] | +0.1833 [−0.274,+0.637] | **(C) / (C)** | (C) / (C) |
| 2024-on | +0.3764 | +0.3517 | +0.3501 [−0.026,+0.728] | +0.3745 [−0.003,+0.743] | (A) / (C) | (C) / (C) |
| F23 | +0.4589 | +0.4287 | +0.4350 | +0.4488 | (A) / (A) | (A) / (A) |
| **FULLCYCLE(提议)** | **+0.4141 [+0.180,+0.639]** | **+0.3876 [+0.151,+0.623]** | **+0.3948 [+0.118,+0.679]** | **+0.4069 [+0.139,+0.676]** | **(A) / (A)** | **(A) / (A)** |

⇒ **会改的判决 1: XIB_LAG50 从 (C) UNDECIDED 变成 (A), 四格全过, 含 Bonferroni。这就是本提议的全部收益, 也是它全部的嫌疑。** 注意 fix 席位: 在冻结窗只有 +0.16/+0.18, 在全周期 +0.39/+0.41 —— 冻结窗恰好是 XIB 最弱的地方, 而这一点是 regime 成分的结果, 不是时间的结果。
⇒ **会改的判决 2: RESID_SHARPE 无法拿到 PROMOTE。** 它按构造没有 2022, 最高只能 PROVISIONAL(§3-4)。这在它本轮被 GATE A 的 R2 判 FAIL 之前就已成立。
⇒ **不会改的判决**: 本轮之前所有在 FROZEN 上判 (B) 的臂(carry/换手/暴露/regime 四轨)——它们在全周期上点估计同号且更负, 不需重判。**未做**: 逐一重跑那四轨的 (B), 登记为 §7 的洞。

## §6 提议给 `judge_v4.py` 的 diff(**未施用**; 判官与合同是被评审的研究定义)
```diff
@@ judge_v4.py:49
-FROZEN = (T(2025, 3, 1), T(2026, 8, 10, 20) + 1); EXT = (T(2025, 3, 1), T(2026, 8, 31, 20) + 1)
+# PREREG_gateB_primary_window_2026-09-11 §3: the VERDICT window is the arm's maximal common post-warm span;
+# the 2025-03-01 window is demoted to a non-contradiction diagnostic (it is 94.3% one regime cell vs 60.1% of history).
+PRIMARY_LO = None                      # = ts[WARM_DROP] of the shared axis, computed per arm set
+WARM_DROP  = int(os.environ.get("JUDGE_WARM_DROP", "900"))   # E-0911-A: the first LOOK anchors return w3=[1/3,1/3,1/3] and bypass the LEGS mask
+PRIMARY_HI = T(2026, 8, 10, 20) + 1
+FROZEN = (T(2025, 3, 1), T(2026, 8, 10, 20) + 1)   # retained as the DIAGNOSTIC window only
+EXT    = (T(2025, 3, 1), T(2026, 8, 31, 20) + 1)
@@ the contrast block (judge_v4.py:293-302)
-        m = (ta >= FROZEN[0]) & (ta < FROZEN[1]); d = (ga - gb)[m]
+        m = (ta >= PRIMARY_LO) & (ta < PRIMARY_HI); d = (ga - gb)[m]
@@ the verdict block (judge_v4.py:318-328)
+        # non-contradiction: an (A) on PRIMARY is demoted to (C) if the FROZEN point estimate reverses sign
+        # span deficiency: an arm that does not cover PRIMARY can reach at most PROVISIONAL, and its chosen span
+        # counts in its own Bonferroni K
```
`JUDGE_N_FROZEN=3168` 的轴断言必须保留(它守的是"每臂同一时间集"), 但要为 PRIMARY 复制一份等价断言, 否则换窗会丢掉判官第三轮加的那层保护。**这一段我没有写码, 因为写了就等于改了被评审的定义。**

## §7 洞(未做的事, 明写)
1. 四条已判 (B) 的轨道没有在 PRIMARY 上逐一重判; §5 的"不会改"是按点估计同号推的, 是 **INFERRED**。
2. BURN=2190 使标签口径 A 在前 2190 锚无定义(全周期窗里 14.3% 的锚无标签)。口径 B 无此缺陷, 两口径的 L1 排序一致, 但"全史 HH=60.1%"这个参照数本身是 expanding median 趋势的产物, 不是物理常数。
3. PRIMARY 的下界(post-warm 起点 2022-06-30 00Z)由 LOOK=900 决定。若 LOOK 改, PRIMARY 改。已把 `JUDGE_WARM_DROP` 写成显式环境量而不是隐式常数。
