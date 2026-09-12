> **created:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **status:** caliber audit of the 13-round uplift programme, written for the independent reviewer | **invalidated by:** any recomputation below failing to reproduce, or a chain newer than v4 passing every gate
> **scope:** which numbers the reviewer MAY quote, which they MAY NOT, which window each sits on, and which unit.
> **my own device:** `handoff_audit/caliber/caliber_audit_recompute.py` → `RECEIPT_caliber_audit_2026-09-12.json` (env whitelist = empty set, asserted in-file; no GPU; no network; `~/dl_quant_live` and `~/wide_shadow` not read or written by this audit).
> **label key:** `[V-me]` = I verified it this session and I name the file · `[V-blk]` = verified by the named block auditor in `handoff_audit/{r1_r3,r4_r6,r7_r9,r10_r11,r12_r13}/`, NOT re-checked by me · `[UNRECEIPTED]` = exists only in prose · `[INFERRED]` = my reasoning.

# CALIBER AUDIT — the canonical number table

> **★ 修订(2026-09-12, 第十四轮 + 独立研究员平行报告对照, 全文见 `ANALYSIS_independent_report_2026-09-12.md`):**
> ① **"~300 条候选全是同一下注的重新加权"这句话撤回** —— 门二实测: 污染与干净基线上都只有 **2/14** 候选 |ρ|≥0.60(中位 |ρ| 0.025 / 0.037), 那两条(XIB_LAG50 / T1_FORMB)本就是按修改 A0 构造的; 凡从独立数据源建的候选与书**正交但无净额**。判决 CLAIM NEVER HELD。
> ② **成本争议符号已定: 模型过度收费**(成交后 markout 100% 在 y4 内); 量级只给区间 [−0.4752, +8.2538]。**但不得单独重定价**(便宜成交价与 45.48% 成交率是一次选择的两半; r14 §6)。规划数 A1x **0.6602 / 1.2857 保持**。两个已发表估计量共用的参照价 `mid_at_anchor` 采集于 **E+24 分**, 非 E。
> ③ **Amihud +0.2458 是方差削减不是 alpha**: a=0.20 时组合 mean g 下降(干净样本 −0.0900); 干净样本 ΔSharpe +0.2181 CI95 [−0.0278,+0.4664] 含零。审计所说"2023 单年修复"理由不对(剔 2023 仍 +0.1927)。
> ④ **在役构成 77/13/10 过时**: 09-11 00Z 名义系数 **fund 65.4% / king 19.0% / DL 15.6%**(研究员自 `target_combo` 读出; 我方 09-12 00Z 掩码席位 king 0.3557 同向)。
> ⑤ **新增两条结构性缺陷(源码坐实, 实盘工件复现)**: 席位纯价格看不见 carry(09-05 的 SEATNET REJECT 坐在 v3 作废口径上); FTRIM 是分数级 pre_zero, 经 demean 泄漏为小空头, 58 锚均值 68% 标记名仍为负目标、付 A0 carry_ex 的 59.8%(毛节省)。**验证臂 r15(FTPOS=1 / SEATNET=1)与 r16(减风险免带)在飞。**
> ⑥ **r15 / r16 已出(2026-09-12, 全 v4 钉住, GATE P 逐位, 无录取)**: 仓位级 FTRIM 净 **+0.018**(省下 carry 的 77% 以放弃的价格还回; 2026 −0.20; 换手 +24%)⇒ **泄漏是真的, 修它是零和**, 我方"年化 12.6% NAV"为毛口径, **净 +0.8%/年 CI 跨零**; 腿层净额席位 **REJECT**(v4 上 fund 腿秩书 carry = 书的 **2.60×**, 过罚; DEEPNEG_SHORT 格 −1.87 CI<0); 书路径净额席位 UNDECIDED 但停机更差; 非对称带无录取(退出毛值 +0.44 被 ×7 换手吃掉, **带在进场侧净赚**); 实盘"零目标仍有仓"= **maker 退出 35% 未成交 + 灰尘低于 min_notional**, 不是带 ⇒ 与"给漏单定价"同轴。**换手因子更正**: 1.7819 是两均值之比, E[1/g]=1.5868, 1/E[g]=1.4375, 匹配口径只能逐锚算。
> ⑦ **成交率口径更正(r17 模型收据)**: "退出腿只成交 65%"撤回(按行、混腿、含停机拦截, 定义有缺陷)。正确单位 = (名字,锚) 意图组: 已发组意图加权成交 **0.848**(ZERO_TARGET 0.911); **零目标意图 84% 是低于 min_notional 的灰尘从未发出**, 已发部分 ~9% 完全未成交; 停机拦截占意图名义 **38.5%**。**未成交组价格朝交易方向跑 +29.2 bps [13.7,44.7]**(已成交 −4.1)—— 挂不到的恰是信号最对的那一半。"零目标仍有仓 ≠ 带"成立。
> ⑧ **独立复审(codex 8fb5c8d1)回应, 全文 `RESPONSE_to_independent_review_2026-09-12.md`。撤回八处**: ①"真因是波动率/2.81×"(同期配对比 **0.656 [0.467,1.008]**, 因果不成立); ②"最优平滑 +9.2%"(未过自身门 p=0.1005; 真 maxDD 门下 L=0.88 收 8.18%); ③"+5.29% 立即入账"(仅 BNB 接近可取); ④"数学上关不上"→"已测候选尚未弥补缺口"; ⑤"TrackF 未失效"(掩码零命中, 687 标签变); ⑥ W_TAIL 口径(前 900 锚跑的是含 rev24 的另一本书, 最差锚 rev24 腿 −139); ⑦ **不再建议批准门 sha f814c728**(六负例里五个仍 PASS, 不可证伪); ⑧ CEM 零假设"匹配 <1%"(实为 11–18%)。**DOCKET #5 → 不批准; #6 → 不晋级(supersedes)。** 新增两处回放缺陷待修: 成员资格用未来 y4 有限性(L160/L234); 暖机在 LEGS 掩码前返回等权三腿(L182)。**五路复测在飞(E1–E5), b681ca5 进入部署验收(钉 exact commit)。**
> ⑨ **r17 漏单定价已出: 成交轴 CLOSES。** 只执行实盘会成交的部分, A0 移动 **|Δ| ≤ 0.03 bps/锚**(费下界 +0.025/+0.011; λ=1 −0.005/−0.019; 两种子; 全部 CI 含零), 远低于 0.23 分辨率 ⇒ 100%-fill 回放作为规划仪器成立; 规划数 / r14 成本争议 / r15 F,S / r16 X1 **无需重定**。**"45% 成交率"是停机不是执行**: `blocked_by_halt` 意图占全部意图名义 **38.5%**(1.00M USDT), 计入才得 ADD 0.451; 真实已发意图组成交 0.848(ADD 0.822 / DERISK 0.943)。逆选择通道**有界未关**: 未成交超额 +17.4 bps/单位 ⇒ 惩罚 0.084 bps/锚 CI [0.008, 0.30], 不能翻任何 ≥0.3 的判决。成交不解释 r6 的 BOOK 缺口(2.70 → 3.33, 反向宽 CI)。★ 新疑点: `rolling.npz` qv4h 与面板重叠门 FAIL(中位 |Δlog| 0.52), 09-10 后 2,975 组被剔 —— 需查实盘 rolling.npz 的 qv4h 是否漂移。
> ⑩ **r19 TrackF 重索引已出**: 掩码 0→10039 命中, **687/7849 标签变**, 但 trackF 六候选**零翻号零越门**(R1 的有害判决反而加强); 三条发现存活, 数字作废字母不变。**找到 7 个外部消费者**(r3 GATE B / r4p3 / r6 judge1 / r7 fuel 与 final / r8 regime_gb; 我方 r12 审计说"无消费者"**是错的**), 其中四个逐字复制了错行。全部重跑: GATE B 可采集不变(FROZEN HH .9426→.9208); **Amihud 亏损格 ρ 更正为 +0.374/+0.369**(原 +0.343/+0.438; 机制成立, HL 数字错); **r4-vs-r7 "独立复现"实为两台仪器共享同一缺陷**; r7 唯一越 95% 的项是 KING 腿 T0 gap(P .040→.011)。缺陷限于 trackF 谱系; r12 v2 原语(被 r13/r15/r16/r17 消费)索引正确。研究员的第二项更正(829-qvk 成员规则, 733 标签变)**未做**。


---

## §0 READ THIS FIRST — eleven facts before you open any document

1. **The pinned statistic is `g = net_ex / gross_total`, bps per 4h anchor PER UNIT GROSS, and the book's weights are NOT normalised to gross 1.** Mean `gross_total` = **0.6956440** on W_ALPHA `[V-me]`. Any quantity you compare with `g` must be divided by `gross_total` per anchor first. The archived receipts store BOTH normalisations in adjacent fields with similar names. §4 is the map.

2. **The accounting identity is `net_ex = pnl_ex − carry_ex − cost_ex`, EXACTLY (maxabs 0.0, n=9138)** `[V-me]`. Carry is **PAID**, not received; it is subtracted. Two devices in the programme got this sign wrong and stored a broken identity residual (`r8_inbook/battery.py` L59, residuals up to 0.5118; `r10_r11` audit §B5 reported the identity as an open defect). It is not a defect — it is a sign convention. Per unit gross on W_ALPHA: `pnl_ex 1.281337 − carry_ex 0.479661 − cost_ex 0.167481 = 0.634196` `[V-me]`.

3. **There are two cost planes in circulation and they are never labelled in the prose.** The *fitted* plane (`costb_PWR_G230k.json`, sha `295b4e7b462373e4` `[V-me]`) and the *deployed fee-only* plane (`costb_fee_steady`, what the live book actually pays). The same A0 book reads **0.6342 / SR 1.2912** on the fitted plane and **0.688853 / SR 1.4025** on the cheap plane. The trap: the cheap-plane number **0.6889** is numerically almost identical to the fitted-plane number at a *different window* (n=9018: **0.689021 / SR 1.4150**) `[V-me]`. Seeing "0.689" tells you nothing; you must read the window AND the cost plane.

4. **`Sharpe 3.04` and `Sharpe 2.9357` are the same book on the same window, on different cost planes** — 3.043 is the deployed-fee arm (`r3_gates/regime_composition.json`) `[V-me]`, 2.9357 is the fitted arm (`p6_receipts/P6_COMBO.json`, `r3k_impact/analyze3.out:25`) `[V-me]`. **Its own CI95 is [1.306, 4.565]** — analytic, from the pin's own rule SE = √(2190/3168) = 0.8314 `[V-me]`. The programme's target ("cross-regime Sharpe significantly above 3.0") was set from a point estimate that is not itself significantly above 3.0. This is the single most important corrective in the programme.

5. **Two windows, never mixed.** `W_ALPHA` n=**9138** (drop first 900 warm anchors, E-0911-A; ceiling 2026-08-30 20Z, E-0911-D) for every mean/CI/Sharpe/turnover/leg number. `W_TAIL` n=**10038** (no warm drop, same ceiling) for every maxDD/worst-day/halt number, because the warm drop discards **2022-06-07, the worst day in the sample (−11.1714% at 2.0×)** `[V-me]`. Rounds 1–8 predate both definitions; §3 tells you what each round actually used.

6. **The leverage ladder in the handoff is on the WRONG window and it is optimistic in the direction that matters.** `r11_tail`'s entire `part2_leverage_ladder` (all three cost planes, 1.00×…2.50×) is computed on n_days **1523 = W_ALPHA** `[V-me]`. On W_ALPHA the book shows **zero** days ≤ −4% at any leverage ≤1.50×. On W_TAIL it shows **1 halt already at 1.00×** and the worst day at 1.00× is **−5.63%** `[V-me, this audit's own recomputation — no document contains this table]`. §1.7 publishes the missing W_TAIL ladder.

7. **A0 — the baseline of the entire programme — is itself on the FORBIDDEN v3 lineage.** `f10_A0` comes from `f8_ext/preds/f10_V2MAIN_s{42,2027}.npy` produced by `pod_f10_train_ext.py` off `dlw_ext`; the king leg is `SLOW_v3_on_v4axis.npy` `[V-blk r7_r9 §7, from `build_dev_v4.py` L42-45]`. The v4-native equivalent is A1/A1x, and A1−A0 is **UNDECIDED** (Δ +0.0562, CI95 [−0.0778,+0.1894]) `[V-me, r9_coverage/SUMMARY_r9.json]`. Everything in the programme is therefore measured against a baseline the pin forbids, and the pin does not say so.

8. **A0's legs are dead on a large contiguous prefix and nothing flags it.** `w10_sleeve.py` L267 `np.nan_to_num` silently zeroes the F10 leg on **1110/9138 = 12.15%** of W_ALPHA `[V-me in source; receipt `r9_coverage/SUMMARY_r9.json`]`, and L219 does the same for the **king** leg on **3300/9138 = 36.11%** `[V-blk r7_r9 §1, first-hand on pod2]`. Mean g on king-dead anchors −0.3770 vs king-live +1.2058. Any "cross-regime Sharpe 1.29" is measured on a book that is not the book for a third of its sample; the clean subsample (SR 2.15) is era-selected and is not a clean estimate either.

9. **The cost model is disputed by this desk's own instruments by a factor between 1.71× and 3.22×, and the sign of the correction is NOT settled** — one instrument says CHARGE −0.3625 bps/anchor (g 0.6342→0.2717, SR→0.5532), the other says CREDIT +0.1441 (the model OVER-charges), a 0.5066 bps/anchor spread. Both are receipted (§1.9). The deciding question — whether the post-fill markout is already inside the replay's y4 — is named and unanswered. Every cost-sensitive verdict in the programme inherits this.

10. **Nothing in this programme has been formally admitted, and nothing CAN be.** `retrain_2026-09/v4_chain_2026-09-09/ELIGIBILITY_CONTRACT.json` registers four gates; **`BUNDLE_export` has `source: null` and `approved_source_sha256: []`** `[V-me]`, and the contract's own rule text says an empty approved list makes every arm ineligible. `RESULT_uplift_program_2026-09-11.md` L4 states this itself: the whole round is **EXPLORATORY, not promotable, not deployable** `[V-me]`. It is DOCKET hole #1/#5 and RULINGS item #3, still unruled. Read every verdict in the programme as research measurement, never as an admission.

11. **sha hygiene is the strongest part of the programme: across all five audit blocks, ~150 manifest entries were recomputed and ZERO mismatched** `[V-blk, all five blocks]`. I re-recomputed the three load-bearing ones myself: device `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650`, cost book `295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53`, pinned arm `352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339` `[V-me]`. What is NOT verifiable from this machine is every `/workspace/...` input (panels, meta, preds, probe npz) — the repo can verify the judges, not the inputs.

---

## §1 THE CANONICAL NUMBER TABLE

### 1.1 The book's level and the planning number — four circulating variants, all "correct", none interchangeable

| # | quantity | value | caliber string | receipt | status |
|---|---|---|---|---|---|
| P1 | **A0, archived arm, FITTED cost, W_ALPHA** | mean g **+0.6341957** bps/anchor/gross · SR **1.2912234** · SE(SR) 0.4895 | `g=net_ex/gross_total`; A0 = LEGS=101 PHI=0.45 WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero UMASK m1 CAL=log W3FIX=None; cost `costb_PWR_G230k.json`; post-warm 900 + ts≤2026-08-30 20Z; n=9138 | `r11_tail/receipts/RECEIPT_r11_tail_2026-09-12.json::A0_reproduction`; reproduced to 2.6e-08 by `r13_B_withinhalf` and again by me `[V-me]` | **CURRENT — quote this as "the book's level"** |
| P1-CI | its CI95 on mean g | **[+0.1774, +1.1136]** (pinned B=2000) · **[+0.1653, +1.1071]** (B=4000) · [+0.15865,+1.11826] (r11_tail's own stream) | UTC-day block bootstrap, `default_rng([20260905,k])`; B=2000 is the PIN, B=4000 is not | `r9_coverage/SUMMARY_r9.json::RESULTS` carries BOTH labelled `CI95_TASK_B2000` / `CI95_R8_B4000` `[V-me]` | **use the B=2000 pair.** CLOSEOUT §7 and DOCKET quote the B=4000 pair without saying so |
| P2 | **A1x, v4-NATIVE arm, extended window** | mean g **+0.6602** · CI95 **[+0.1673,+1.1472]** · SR **1.2857** · SE 0.4879 · n **9199** (s2027: 0.6828 / 1.3288) | same statistic, v4-native F10 (`f10_v4RAWx_s42.npy`) + v4 king; ceiling 2026-09-10 00Z after GATE X-P closed E-0911-D | `r9_coverage/SUMMARY_r9.json::RESULTS.A1x_ext_s42_NEW_WINDOW` `[V-me]`; repeated in `r11_verdict/receipts/RECEIPT_r11_cost_estimand_reconciliation.json::planning_number` `[V-me]` | **CURRENT and the only lineage-clean one.** It is the honest planning number; P1 is the one every document quotes |
| P3 | **A0, DEPLOYED fee-only cost, n=9139** | mean g **0.688853** · SR **1.4025** (s2027 0.713714 / 1.4426) | cheap/`fee_steady` cost plane; post-warm to the axis end, i.e. **one anchor past the E-0911-D ceiling** | `ship1_receipts/SHIP1_A0_accounting.json` `[V-me]` | **legitimate but a different cost plane.** Never compare with P1 without saying so |
| P4 | NAV translation at 2.00× gross | P1 → **+27.78 %NAV/yr**, CI95 **[+7.77%, +48.78%]** (B=2000) or [+7.24%,+48.49%] (B=4000) · P2 → **+28.92%**, CI95 [+7.33%,+50.25%] | `bps/anchor × 2190 × L / 1e4`; 2190 anchors/yr | arithmetic in my receipt `NAV_ARITHMETIC` `[V-me]`; P2's pair in the r11 reconciliation receipt | CURRENT. **CLOSEOUT §7 pairs the B=4000 bps CI with a NAV CI that neither CI generates** (its [7.1%,48.6%] comes from [0.161,1.110], DOCKET's rounding) |

**Why they differ, in one line each:** P1 vs P2 = v3-lineage baseline vs v4-native baseline plus 61 extra anchors. P1 vs P3 = fitted impact cost vs deployed fee-only cost (raw cost_ex 0.094756 vs 0.064799 bps/anchor, i.e. the fitted model is **1.46×** the deployed one) `[V-me]`. P1 vs the n=9018 figure 0.689/1.4150 = 120 anchors of 2026-08-11…08-30, which are bad ones.

**The one thing no receipt contains:** an A0 reading on the DEPLOYED cost plane over W_ALPHA. The closest is P3 at n=9139 `[V-me, searched]`.

### 1.2 Full-cycle Sharpe and its SE — every published pair

| window | Sharpe | n | SE=√(2190/n) | cost plane | receipt |
|---|---|---|---|---|---|
| **W_ALPHA (CURRENT)** | **1.2912** | 9138 | **0.4895** | fitted | `RECEIPT_r11_tail…json`, `RECEIPT_r13B_full.json::sharpe_base` `[V-me]` |
| n=9018 | 1.4150 (s2027 1.4370) | 9018 | 0.4928 | fitted | `r3k_impact/analyze3.out:25` `[V-me]` |
| n=9139 | 1.2947 | 9139 | 0.4895 | fitted | `r5_newdata3/A0_headline_check.json` `[V-blk r4_r6 §6]`; reproduced by me `[V-me]` |
| n=9139 | 1.4025 | 9139 | 0.4895 | deployed fee | `ship1_receipts/SHIP1_A0_accounting.json` `[V-me]` |
| n=9918 | 1.2112 (mine, fitted) / **1.32 (published, deployed fee)** | 9918 | 0.4700 | see cell | `RESULT_uplift_program_2026-09-11.md` L24/L33 `[V-me]`; my fitted value `[V-me]` |
| n=10039 full axis | 1.1092 (fitted) / 1.213 (deployed fee) | 10039 | 0.4671 | see cell | mine `[V-me]` / `r3_gates/regime_composition.json` `[V-me]` |
| **W_TAIL** | **1.1062** | 10038 | 0.4671 | fitted | `RECEIPT_r11_tail…json::part1_companion_NOWARM` `[V-me]` |
| n=7835 (LOB subset) | 1.6039 | 7835 | 0.5287 | fitted | `r5_lob/RESULT_SUMMARY.json` `[V-blk r4_r6]` |

### 1.3 The frozen window and its CI — the programme's most important corrective

| quantity | value | caliber | receipt |
|---|---|---|---|
| A0 frozen, **fitted** cost | g **+1.8266823** · SR **2.9357130** | 2025-03-01…2026-08-10 20Z, n=3168 | `p6_receipts/P6_COMBO.json::SR_A0_frozen`, `r8_inbook/BATTERY_dyn_s42.json`; reproduced by me `[V-me]` |
| A0 frozen, **deployed fee** cost | g **+1.8937** · SR **3.043** · SE 0.831 | same window | `r3_gates/regime_composition.json` `[V-me]`; this is the pin §4 "+1.894 / 3.04" |
| **CI95 of the frozen Sharpe** | **[1.3061, 4.5653]** | analytic, SE=√(2190/3168)=0.83144, ±1.96σ, on the FITTED 2.9357 | my receipt `FROZEN_SHARPE_CI` `[V-me]`; the interval appears in CLOSEOUT L11/L38/L154 only `[V-me]` — **no bootstrap receipt exists for it** |
| composition of that window | HH regime share **0.9426**, effective cells **1.124**, L1 distance to full-history mix **0.6722** | round-2 expanding-median labelling | `r3_gates/regime_composition.json` `[V-me]` |
| bootstrap resolution on that window | **±0.23 bps/anchor** | pin §4 | `CALIBER_PIN_v4` L51 `[V-me]` |
| "regime rent 2.075×" | = 2.9357 / 1.4150 | **ratio to the SUPERSEDED n=9018 Sharpe** | `RULINGS_OUTSTANDING` L25 states the derivation `[V-me]`; CLOSEOUT §0 repeats "2.075×" with no derivation ⇒ **[UNRECEIPTED as stated]**. On W_ALPHA the ratio is **2.2737** `[V-me]` |

### 1.4 Per-year, corrected caliber (W_ALPHA, fitted cost)

| year | mean g bps/anchor | Sharpe | annualised % of gross |
|---|---|---|---|
| 2022 | +0.15859 | 0.4797 | +3.47% |
| 2023 | **−0.64852** | −1.9355 | −14.2% |
| 2024 | +0.48648 | 1.0875 | +10.65% |
| 2025 | +0.67701 | 1.1867 | +14.83% |
| 2026 (→08-30) | **+3.09129** | 4.5165 | +67.7% |

`r12_regime/receipts/RECEIPT_r12_cost_repricing.json::a_YEAR` `[V-me]`. **Supersedes the pin §4 per-year row** (+0.8 / −13.7 / +12.3 / +16.7 / +81.7 %), which is the deployed-fee plane cut at 2026-08-10. Note 2022 is 100% king-dead (fact 8) and 2026 is 5.6× the full-sample mean.

### 1.5 The cost model — what is and is not in the pinned file

| quantity | value | receipt |
|---|---|---|
| **book average** | **2.9537** bps per unit turnover; my blend recomputation of `Σ blended×share` = **2.95375** (shares sum to 1.0) | `r3k_impact/costb_PWR_G230k.json` `[V-me]` |
| tier impacts (excess of half-spread) | [0.01954, 0.07144, 0.85794]; turnover shares [0.3092, 0.4041, 0.2867] | same file `[V-me]` |
| **K = 0.17** | `FITK_v3_shape.json::POWER.K_excess = 0.17`, CI95 [0.1522, 0.1883], bootsd 0.0091 — and its `per_tier.excess` equals the pinned `impact_bps_by_tier` **exactly** | `FITK_v3_shape.json` sha `0f682c91c29725c3…` `[V-me]` |
| K is a **ratio, not a coefficient** | K_excess = book_excess / infra1_K1, i.e. "the measured book-walk is 0.17× what a K=1 square-root law charges". `costb_PWR_G230k.json` contains **no K field and no exponent field** (top-level keys: tiers, model, impact_bps_by_tier, blended…, book_avg…, turnover_share…, calibration) | `r3k_fitK3.py` `[V-blk r1_r3 §1]`; key list `[V-me]` |
| **"impact exponent 0.87" is the wrong file** | the POWER shape that produced the pinned tiers implies **0.7826** (`implied_impact_exponent_alpha_1_over_p`, p=1.2777). **0.8739** is `FITK_v2.json::FINE2026_G230k.powerlaw_vwap_vs_participation.pooled.alpha` — a *pooled-across-tiers* OLS slope whose within-tier values are 1.2661 / 1.2076 / 0.9884, i.e. a Simpson artifact | both files `[V-me]` | 
| ⇒ **the CALIBER PIN and the task brief both mis-state the model's own parameter.** Fee tiers are unaffected (the book prices off rates, not the exponent), but any argument extrapolating "α=0.87" rests on a different fit. `r13_deploy` §9.4 additionally read the **UNIF** branch (K 0.1165) and called K=0.17 unreproducible — it is reproducible, in the POWER branch `[V-blk r12_r13 §11]`. |
| **fit support** | the ±0.2% LOB band exists **only in 2026**: `mean_names_by_year` 2022-2025 = 0.0, 2026 = 525.1. Tier impacts measured on 1331 2026 anchors, applied 2022-2026 | `LOBCUBE_COV.json` `[V-me]` |
| blending mismatch | 2.9537 blends 2026-measured impacts with **full-history** turnover shares; with the measurement sample's own shares it is **3.3002** (+11.7%) | `[V-blk r1_r3 §1]` |
| **effective rate the book actually pays** | **3.0999** bps per unit MATCHED turnover on W_ALPHA = **1.0495×** the quoted book average | my receipt `COST_MODEL` `[V-me]` |
| no adverse-selection term at all | maker legs are charged the full aggressive walk; 81–85% of live fills are maker | `mk_costb.py` `[V-blk r1_r3 §1]` |

### 1.6 Turnover — the number with three receipted values (see §4 for the full trap)

| series | RAW | MATCHED (mean of per-anchor t/g) | what it is |
|---|---|---|---|
| archived `turnover` column (**the cost-consistent one**) | **0.0303158** | **0.0540270** | `sum|Δw|` over the member set — the same set `cost_ex` is charged on |
| r13A/r13B recomputation `base_turn` | 0.0314943 | **0.0556336** | `sum|Δw|` over the **full** vector, including off-member names; cost is unchanged (maxabs diff 2.5e-08) so this series does **not** match the cost caliber |
| "implied by cost" | — | 0.0567020 | `mean(cost_ex/gross)/2.9537` — not a turnover at all; it is turnover × (effective rate / book average) |

All three `[V-me]` (my receipt `TURNOVER_TWO_SERIES`; third from `RECEIPT_r11_tail…json::unit_reconciliation_of_the_cost_gap`). **Use 0.0540270** for anything that touches cost. The 3.0% spread propagates linearly into every repricing.

### 1.7 Tail, drawdown and halt frequency — W_TAIL, published here for the first time

**`W_TAIL` (n=10038 anchors = 1673 UTC days, no warm drop, ≤2026-08-30 20Z), fitted cost, A0 dyn s42** `[V-me, this audit's own device]`:

| gross | CAGR | ann vol | **maxDD** | **worst day** | **halts ≤−4%** | alerts ≤−2% | P(rolling-1y maxDD ≥25%), empirical |
|---|---|---|---|---|---|---|---|
| 1.00× | 12.37% | 11.29% | 25.79% | **−5.63%** | **1** (0.218/yr) | 6 (1.31/yr) | 0.0% |
| 1.25× | 15.47% | 14.11% | 31.33% | −7.02% | 1 (0.218/yr) | 10 | 0.0% |
| **1.40×** | 17.33% | 15.80% | 34.49% | −7.85% | **2** (0.436/yr) | 18 | **4.13%** |
| 1.50× | 18.57% | 16.93% | 36.53% | −8.41% | 2 (0.436/yr) | 25 | 4.97% |
| 1.75× | 21.65% | 19.76% | 41.41% | −9.79% | 3 (0.655/yr) | 42 | 22.46% |
| **2.00× (in service)** | 24.72% | 22.58% | **45.99%** | **−11.1714%** | **6** (1.309/yr) | 62 (13.53/yr) | **26.97%** |
| 2.50× | 30.78% | 28.22% | 54.26% | −13.91% | 10 (2.182/yr) | 98 | 49.81% |

Cross-checks: my 1.40× and 2.00× rows reproduce `r13_verdict/receipts/RECEIPT_r13_verdict.json::V3_halt_criterion` **to every printed digit** (halt 2/6, halt_per_yr 0.4363/1.3090, worst −0.0785382/−0.1117140, maxDD 0.3448836/0.4598580, P25 0.0412529/0.2696715) `[V-me]`. The anchor-level maxDD at 2.0× is 46.418% (`maxDD_anchor`), the daily-close one is 45.986%.

**The same ladder on W_ALPHA (what `r11_tail` published), for contrast** `[V-me]`: 1.00× maxDD 23.44% / worst −2.31% / **0 halts**; 1.50× 33.27% / −3.44% / **0 halts**; 2.00× **41.99%** / **−4.57%** / 4 halts (0.959/yr); 2.50× 49.69% / −5.69% / 8 halts. **Dropping 900 warm anchors removes the entire tail below 1.75×.**

**P(1-year maxDD ≥ 25%) at 2.00× has two receipted values and they differ by 3.6×** `[V-me]`:
- **7.40%** — `r11_tail…json::part1…PINNED.2.00x.bootstrap_1y.P_maxDD_ge_25pct`, an **iid-day resample** (2000 draws) on **W_ALPHA**;
- **12.25%** — the same estimator on **W_TAIL** (`part1_companion_NOWARM`);
- **26.97%** — `RECEIPT_r13_verdict::V3` and my recomputation: the **empirical share of the 1309 overlapping rolling 1-year windows** on the realised W_TAIL path (on W_ALPHA the same estimator gives **30.46%**).
A drawdown is a path statistic; iid-day resampling destroys the serial correlation that produces drawdowns, so the bootstrap value is a lower bound `[INFERRED]`. **The leverage recommendation rests on which of these you quote.** `RESULT_r11_cost_tail_income` §6 quotes the 7.40% family throughout.

**Live-vs-replay volatility (the sizing input)** `[V-me, `RECEIPT_r11_live_vs_replay_vol_2026-09-12.json`]`: live daily σ (2× equivalent) **1.5917%**, **n=33 days**, CI95 **[1.2800, 2.1053]**; replay 1.1335% (n=1523); F=1.9717, p=0.00102; decomposition 1.2352 (per-anchor) × 1.1368 (within-day serial corr) = 1.4042; **vol-equivalent gross 2.8083, CI95 [2.2584, 3.7145]**; E[halt]/yr at that gross 3.385. **The CI95 lower bound implies a ratio of only ~1.13, not 1.40, and all 33 days sit inside one 2026-08/09 regime while the replay spans 2022-2026** — the whole sizing case rests on this one ratio.

### 1.8 Live-book reconciliation (replay vs realized)

| quantity | value | caliber | receipt |
|---|---|---|---|
| per-anchor correlation replay↔realized | ρ **+0.8263** CI95 [+0.7104,+0.8986] (W5, n=78) | **holdings-book layer `g = pnl/gross`, NOT `net_ex/gross_total`** | `RESULT_r6_judge1…md` + `judge1_r6` receipts `[V-blk r4_r6]` |
| slope | **0.8348** [0.7068,0.9627]; all four tests' CI upper bound < 1 | same | same |
| reading | the replay **amplifies magnitude 15–27% in BOTH directions** | — | CLOSEOUT L24 retracts the earlier "replay is pessimistic" `[V-me]`; **the retraction was never back-annotated into `RESULT_r6_judge1`, whose planning sentence "1.42 is conservative" is the one place the error is load-bearing** `[V-blk r4_r6 §10]` |
| largest replay-vs-live term | the **book construction** itself, +2.6982 bps/anchor, CI excludes zero | — | `RESULT_r6_judge1` L11/L20-29 `[V-blk]` |
| live combo-era decomposition | price alpha −0.022 (SE 4.018, t −0.01) · **funding −1.371 (SE 0.113, t −12.09)** | ledger components | `PREREG_r6…md` L187 `[V-blk r1_r3/r4_r6]` |
| E-0911-C fee correction | corrected fee **2.7847** bps vs naive 1.9629 ⇒ the naive sum understates by 29.5% of the corrected bill | live ledger, 2026-08-01…09-11, 34921 fills, $1.538M | `r11_costtruth/RECEIPT…json::fee_side` `[V-me]`; VIP0, maker 2.0000 / taker 5.0000 bps |

### 1.9 The unresolved cost dispute — both sides, receipted

| instrument | measurement | effect on the planning number | receipt |
|---|---|---|---|
| **B — markout term structure** (r11_costtruth) | fee 2.7847 + adverse selection **6.7164** (steady plateau) = **9.5012** bps/unit traded one side vs model **2.9537** ⇒ **ratio 3.2167**, gap 6.5475 | Δg **−0.3625** ⇒ g 0.6342 → **0.2717**, SR → **0.5532** (1.13 SE from zero) | `r11_costtruth/RECEIPT…json::reconciliation, ::repricing` `[V-me]`. Term structure: −3.20 (60s) → −6.64 (5m) → −6.30 (15m) → −7.78 (1h) → −6.14 (4h, CI crosses zero) |
| **A — versus the decision price** (trackB/judge1) | fill vs anchor mid + fee = **0.286** bps/unit traded ⇒ the model **over-charges** by 2.6677 | Δg **+0.1441** ⇒ g **RISES** | `r11_verdict/receipts/RECEIPT_r11_cost_estimand_reconciliation.json` `[V-me]` |
| triangulation | 2.6677 × **live** turnover 0.2898 = 0.2767 reproduces judge1's measured +0.2767 [+0.075,+0.653] to 4.74%; with **replay** turnover it gives half, the factor being the recorded 2.01× live/replay turnover gap | — | same `[V-me]` |
| third and fourth readings | r9 critic **1.7071×** (fee 2.3848 + adverse 2.6573 = 5.0421, 229 rows) · `costb_honest_X1` **1.87×** (5.517 bps) | — | `r9_critic/RECEIPT…json`, `r9_horizon/REOPEN_CHECK_r9.json` `[V-blk r7_r9 §5]` |
| **spread between A and B** | **0.5066 bps/anchor**, opposite signs | `cost_repricing_applied = false` in the planning number | `[V-me]` |
| a pre-registered gate was self-exempted | `gate.clause1 = FAIL` (96.213% exact price equality vs the pre-set >98%); device set `decision = PROCEED` on its own argument | — | `r11_costtruth/RECEIPT…json::gate` `[V-me]`. **Report as "gate not fully passed + self-granted exemption", never as "gate passed"** |

**Signs under a 3.2167× repricing, per block** `[V-blk, each block's own arithmetic]`: A0 planning number −55.8%; every turnover-ADDING arm gets worse (r13_B PRIMARY +0.0077 → **−0.0139**, sign flip; r12 ICO +0.0162 → −0.0850, flip; r12 CEM_99 +0.0380 → +0.0369, survives); the one turnover-REDUCING family (R8 BUILD-1 basis-in-book, marginal turnover −5.13%) gets **better**; every already-rejected high-turnover arm (REV_SHORT, r5 basis, r5 LOB) is killed harder.

### 1.10 The two headline in-flight verdicts (so the reviewer reads the right cells)

| arm | reading | caliber | receipt |
|---|---|---|---|
| **r13 FORM B** (within-half beta re-allocation), PRIMARY K=1.00 W250 | dg **+0.0077303**, CI95 **[−0.1638638, +0.1794332]**, Bonf-12 [−0.2274,+0.2491], cost survival 0.4416, dturn +5.81%, **repriced −0.0139**, SR 1.2912→1.4378 | W_ALPHA n=9138, fitted cost, B-block bootstrap | `r13_B_withinhalf/receipts/RECEIPT_r13B_full.json::grid.K1.00_W250` `[V-me]` — **REJECT as alpha**; the mechanism works (beta gap −91.9%, CI excludes zero) |
| its amendment | AMENDMENT 1 moved this very cell from −0.0118 to +0.0077, **the largest delta in the 12-cell grid**, and moved the gate figure 50.33% → 91.90% | — | `RECEIPT_r13B_v1_vs_v2_disclosure.json` `[V-blk r12_r13 §12 FINDING K]`; verdict unchanged either way |
| **r12 CEM_99_neutral** | dg +0.0379739, CI95 [−0.0045,+0.0851], Bonf-29 [−0.0210,+0.1158], fire 141/9199 = 1.53% | **n=9199**, A1x baseline — *not* the r12_regime window | `r12_intervene/receipts/BATTERY_r12.json` `[V-blk r12_r13 §6/§7]` |
| programme-level | **zero admissions across ~300 candidates** | — | count itself is `[UNRECEIPTED]` `[V-blk r10_r11 §E]` |

---

## §2 THE DO-NOT-QUOTE LIST

Ordered by how likely a reviewer is to pick it up.

| # | archived number | where it is | why it must not be quoted | quote instead |
|---|---|---|---|---|
| D1 | **A0 Sharpe 1.32, mean g +0.663, n=9918** | `RESULT_uplift_program_2026-09-11.md` L8/L24/L33/L44/L48 (a top-level document) | no warm drop AND cut at 2026-08-10 `[V-me]`. The document names no cost plane; the fitted plane at n=9918 reads **0.6097 / 1.2112** `[V-me]`, so 0.663/1.32 is a different (cheaper) plane `[INFERRED]`. `RULINGS_OUTSTANDING` L70 already flags the pair as stale `[V-me]` | P1: **0.6342 / 1.2912 / n=9138** |
| D2 | **"cross-regime Sharpe 1.32 → 2.28–2.39" (the Amihud sleeve headline)** | `RESULT_uplift_program` L8/L17/L33 | baseline is D1; the *gain* is diversification against a baseline that is **fund-leg-only in 2022–2023** (king OOS non-finite), so it is not a gain against the deployed three-source book `[V-blk r1_r3 §5 cross-round kill shot]`; and the placebo used to admit it was the defective per-anchor permutation | the sleeve's own gated reading: **ΔSharpe +0.2458** at a=0.20, CI95 [+0.0336,+0.4587] (4/4 lower bounds >0) `P6_COMBO_PAIRED.json` `[V-blk r1_r3 §5]` |
| D3 | **"1.42 → about 1.90" (sleeve at a=0.50)** | `PREREG_p6`, `PREREG_ship1` | holds only at a=0.50, whose paired ΔSharpe CI **contains zero** (P(Δ>0)=0.93); the allocation that passes the gates gives +0.246 | +0.246 at a=0.20 |
| D4 | **A0 = 1.4150 [0.449, 2.381], "primary window n=9018"** | `RULINGS_OUTSTANDING_2026-09-11.md` header + L24 (never amended) | superseded window; the doc's own hole #5 warns about exactly this failure mode `[V-blk r7_r9 §6.4]` | 1.2912 [0.332, 2.251] on n=9138 |
| D5 | **frozen-window Sharpe 3.04 / +1.894 as "the thing to beat"** | `CALIBER_PIN_v4` §4, and by inheritance the deployed `constant_leverage_2.00` sizing | it is a **one-regime-cell** reading (HH share 94.26%, effective cells 1.124) on the **deployed-fee** plane; its own CI95 is [1.306,4.565] on the fitted plane | quote the frozen number **with** its CI and its composition, and use P1/P2 for planning |
| D6 | **any tail/maxDD/halt number computed post-warm** — maxDD **41.99%**, worst day −4.574%, E[halt]/yr **0.974**, P(1y DD≥25%) **7.40%**, and the whole `part2_leverage_ladder` | `RESULT_r11_cost_tail_income_2026-09-12.md` §1 and §6 | W_ALPHA drops 2022-06-07 (−11.1714%) and 2022-05-11 (−6.28%); bias is **toward higher leverage** | §1.7 of this document (W_TAIL): maxDD **45.99%**, worst **−11.1714%**, halts **1.309/yr**, P(1y DD≥25%) 12.25% (bootstrap) / **26.97%** (empirical) |
| D7 | **"the replay is pessimistic" / "1.42 is conservative"** | `RESULT_r6_judge1…md` §0/§3/§4 (5 places) + `PREREG_r6` §4.3 | retracted by CLOSEOUT L24: slope CI upper <1 in all four tests ⇒ the replay **amplifies** magnitude both ways. The retraction was never back-annotated `[V-blk r4_r6 §10]` | "the replay over-states magnitude by 15–27% in both directions" |
| D8 | **"placebo overstatement 53–448% with turnover 2.6–7.7×"** | CLOSEOUT §4-4, `PREREG_r3_resid_deployable` L66, `PREREG_r5_basis` L89, `RESULT_r5_basis` L104, `RESULT_r5_newdata2` L157 | the 53–448% is receipted; the **"2.6–7.7×" is not** — receipted turnover ratios run **1.686–16.360** and cost ratios **1.861–46.211**; the stated range mixes one turnover ratio with cost ratios and understates the max by 2.1×/6× `[V-blk r1_r3 §2]` | "turnover ratios 1.69–16.36×, cost ratios 1.86–46.2×" |
| D9 | **"REV_SHORT turnover ≈ 39× the book"** | CLOSEOUT A-8 | mixes calibers. Matched: **1.3178 / 0.0540270 = 24.39×** (this is what the receipt says); mixed: 43.47×. **39× appears in no receipt** `[V-blk r10_r11 §B3]` | **24.4×** |
| D10 | **"REV_SHORT's gross alpha is 87% of the whole book"** | `klass…/RECEIPT_klass_screen…json` prose field only | denominator `A0 pnl_ex 1.3266` is in no machine field; recomputation gives pnl_ex/gross 1.28134 (⇒90.4%) or pnl/gross 1.33843 (⇒86.6%) `[V-blk r10_r11 §B4]` `[UNRECEIPTED]` | state the ratio with the denominator you used |
| D11 | **"K=0.17, impact exponent 0.87"** | `CALIBER_PIN_v4` §head, CLOSEOUT L2, `PREREG_r6` L204, `RESULT_r10` L2, and the task brief | K=0.17 is right (POWER branch) but is a **ratio to a K=1 sqrt law**, not a coefficient in the file; **0.87 belongs to a different fit** (FITK_v2 pooled α, a Simpson artifact); the shape that produced the pinned tiers implies **0.7826** `[V-me]` | "fitted POWER shape, K_excess 0.17 [0.1522,0.1883]; the pinned file stores rates, not an exponent" |
| D12 | **"K=0.17/α=0.87 are unreproducible"** | `r13_deploy` RESULT §9.4 | it read the **UNIF** branch (K_excess 0.1165). The POWER branch reproduces the pinned tiers exactly `[V-me]` | D11's phrasing |
| D13 | **the frozen-window XIB verdict letter** — "(C) UNDECIDED" vs "(A) PASS" on `dyn_s2027` | `r3_gates/rejudge_windows.json` rows "as-judged" and "post-warm" | the two rows are the **same sample**; `rejudge.py` passes a running counter as the bootstrap sub-stream, so the CI differs (−0.0038 vs +0.0048 lower bound) purely by Monte-Carlo noise at B=2000 `[V-blk r1_r3 §3]` | quote the effect (+0.3932) and say the verdict letter is inside the bootstrap's own MC error |
| D14 | **"2.075× regime rent"** | CLOSEOUT §0 | = 2.9357/1.4150, i.e. ratio to the superseded n=9018 Sharpe; `[UNRECEIPTED]` in CLOSEOUT | **2.2737×** (2.9357/1.2912) `[V-me]`, or state the derivation |
| D15 | **"today's funding dispersion σ = 9.0565 (masked)"** and "8.20 = 69.5th percentile of post-warm history" | `RESULT_r7_fuel2` §1, `RECEIPT_r7_fuel1_viability.headline_findings.2`, `DOCKET_r7` L315 | the "masked" gauge was never masked (`r7_fuel.py` L26-29 looks a row index up in a timestamp-keyed dict; `carried_mask_rows = {incumbent: 0}` proves it); the true masked reading is **8.1995**. And 69.5/median 4.09 is the **no-warm-drop n=10038** sample while labelled "post-warm"; the same receipt contradicts itself (66.98 elsewhere) `[V-blk r7_r9 §2/§3]` | masked LIVE gauge **8.1995**, W_ALPHA percentile **66.98**, median 4.5447 |
| D16 | **r9 critic's C2 repricing** — "extra cost 0.0633 bps, A0 → 0.5709, haircut 9.98%" | `r9_critic/critic_arith.py`, and CLOSEOUT A-3 repeats 0.5709/1.1623 | multiplied a per-unit-traded gap by the **RAW** turnover 0.03032 and subtracted it from a per-unit-gross quantity | corrected ×1.7822: extra cost **0.1128**, A0 → **0.5214**, SR → **1.0615**, haircut **17.79%** `[V-blk r7_r9 §4]` |
| D17 | **`RECEIPT_r11_M1_fee.json::lever_BNB_restore.valuation.at_A0_replay_turnover_0.03032`** | that field | same raw-vs-matched error, still sitting in an archived receipt. It did **not** propagate (TOTALS uses live turnover) `[V-blk r10_r11 §F2]` | recompute on 0.0540270 |
| D18 | **"BNB discount restoration ≈ +1.5% NAV/yr"** | `RESULT_r11_cost_tail_income` §3 | the receipt has only three regime values: +1.188 / +1.756 / +2.332 `[V-blk r10_r11 §E3]` `[UNRECEIPTED]` | quote a regime and its value |
| D19 | **"idle margin +1.18% NAV/yr"** quoted without its blocker | `RESULT_r11_cost_tail_income` §4 | `RECEIPT_r11_M2_financing.json::STRUCTURAL_BLOCKER`: under `constant_leverage_2.00`, every $1 moved out shrinks next anchor's gross by $2 — under current policy it is **not extractable**; M2 self-reports status INFERRED `[V-blk r10_r11 §B12]` | quote it with the blocker attached |
| D20 | **the watchdog's own comment "fires 3 times in 4.5 years, all three in 2024 (02-28, 03-08, 11-13)"** | `~/dl_quant_live/live/watchdog.py` L109 (live tree, read-only) | on the corrected caliber **2024 contains none**. Breaches are W_ALPHA: 2022-11-10, 2025-04-30, 2025-05-13, 2026-08-22; W_TAIL adds 2022-05-11 and **2022-06-07** `[V-blk r10_r11 §B7, recomputed]` | the six W_TAIL dates |
| D21 | **"the same 34 regime cells, cell-by-cell comparable"** | `r12_verdict` §1.2 | r12_regime's 34 cells contain a 6-bin R72 **ladder**; r12_verdict's contain a 5-**quantile** partition — different partitions, and the shared cell DEEPNEG_SHORT has different n and Sharpe `[V-blk r12_r13 §10]` | compare only within one partition |
| D22 | **r12_regime's halt frequencies (prose)** — DEEPNEG_MKT 6.12, BREADTH_T1 3.49 | `RESULT_r12_regime_table` §8 | the round's own verdict device recorded receipt values **5.887** and **2.632** (33% off) and flagged the discrepancy `[V-blk r12_r13 §9]` | the receipt values |
| D23 | **"rolling 500-anchor beta slides monotonically"** | `RESULT_r12…` §5.3 | 14 of 34 steps go **up**, with three sign flips to positive; the quoted 7-window subsequence omits every positive window `[V-blk r12_r13 §2 FINDING A]` | "beta drifts negative with substantial reversals" |
| D24 | **"effective lag deconvolution R² = 0.9949"** | `r12_smoothing` RESULT | that R² is the **b=0 control**; the deployed corner (α=0.1, b=2.5e-4) is **0.9759**, and the band is a threshold operator so the linear deconvolution is misspecified exactly where the "+3.10 anchors from the band" comes from `[V-blk r12_r13 §4 FINDING C]` | report both R² and flag the misspecification |
| D25 | **any level comparison across r12 tracks** (A0 mean_g 0.6602 vs 0.6342; maxDD 41.81% vs 45.99% vs 46.42%) | r12_intervene vs r12_regime vs r13_A | different windows (9199 vs 9138), different baselines (A1x v4-native vs A0 v3-lineage), different day counts (1683 vs 1673) `[V-blk r12_r13 §7/§14]` | compare only paired Δ within one track |
| D26 | **"maxDD improves and worst-day worsens in every combination configuration"** | `RESULT_r10` §4 prose | 6 counter-examples in the receipt, incl. POOL_A equal-risk d_maxDD **+4443.5 bps** `[V-blk r10_r11 §B13]` | "…in the 19/24 configurations where A0 keeps the dominant risk share" |
| D27 | **`r10_screen/TSMOM_DIR`'s "FROZEN 2025-03-01..2026-08-10" cells** | that device, L22 | the mask ends at **1786737600 = 2026-08-14 20Z**, 24 anchors past the frozen ceiling; n=3192, not 3168 `[V-blk r10_r11 §B2]` | the true frozen-window recomputation (ρ −0.0322, n=3168) |
| D28 | **the 7 arms marked `UNRESOLVED_null_not_matched`** (RESID_SHARPE ×2, LOBDEPTH_RAW, LOBDEPTH_ORTH, TBF_ema08, ORTH_LISTEVT, ORTH_RESSKEW) | `r3_placebo/REPORT_FULL.txt` | their old margins are known-biased and their new margins are inadmissible (pooled cost ratio outside [0.75,1.25]). **Neither number may be quoted** `[V-blk r1_r3 §2]` | "no admissible margin exists for these arms" |
| D29 | **any `REPORT_FULL.txt` level column compared with a margin column** | `r3_placebo/REPORT_FULL.txt` | paired arms print arm-minus-baseline in `real`/NL rows but raw levels in the pooled ALL row; the table cannot be recomputed from its own columns `[V-blk r1_r3 §2]` | read `JUDGE_r3_placebo.json` instead |
| D30 | **`BATTERY_*.json::identity_resid` (values up to 0.5118)** | `r8_inbook/battery.py` L59 | sign error against the pin's convention (fact 2). With the correct sign the max residual over all arms and windows is **1.0159e-14** `[V-blk r7_r9 §6.1]` | the prose value 1.02e-14 |

---

## §3 THE WINDOW TABLE

### 3.1 The windows, defined

| name | rule | n anchors | n UTC days | first / last anchor |
|---|---|---|---|---|
| **W_ALPHA** | drop first 900 (E-0911-A) ∧ ts ≤ 2026-08-30 20Z (E-0911-D) | **9138** | 1523 | 2022-06-30 00Z / 2026-08-30 20Z |
| **W_TAIL** | ts ≤ 2026-08-30 20Z, no warm drop | **10038** | 1673 | 2022-01-31 00Z / 2026-08-30 20Z |
| **EXTENDED** | post-warm ∧ ts ≤ 2026-09-10 00Z (after GATE X-P closed the ceiling) | **9199** | — | 2022-06-30 00Z / 2026-09-10 00Z |
| **FROZEN** | 2025-03-01 00Z … 2026-08-10 20Z | **3168** | 528 | — |
| n9018 | post-warm ∧ ts ≤ 2026-08-10 20Z ("FULLCYCLE" in rounds 1–5) | 9018 | 1503 | 2022-06-30 00Z / 2026-08-10 20Z |
| n9139 | post-warm, whole archived axis (incl. 2026-08-31 00Z) | 9139 | — | — |
| n9918 | no warm drop ∧ ts ≤ 2026-08-10 20Z | 9918 | 1653 | — |
| n10039 | the whole device axis | 10039 | — | 2022-01-31 00Z / 2026-08-31 00Z |
All n values `[V-me]` from my receipt `LEVELS`.

### 3.2 Which round is on which window

| round / track | window(s) actually used | on W_ALPHA? | note |
|---|---|---|---|
| R1–R3 (trackA–F, r2_*, r3_*, p6, infra1, r3k) | 3168 · 5718 · 7849/7908 · 9018 · 9139 · 9918 · 10039 | **NO — W_ALPHA did not exist** | `[V-blk r1_r3 §8]`. Every tail number here that is post-warm drops 2022-06-07 ⇒ optimistic |
| R4 (nondet), R4-P3, R5 (angles 1-3, ND1-4) | **9018** primary; also 9139, 10033, 9918, 7835/7850 (LOB) | NO — 120 anchors short | `[V-blk r4_r6 §1/§6]`. `r5_newdata3`'s receipt also carries a 9139 row that the document never quotes |
| R6 EXTEND / JUDGE-1 | extended x0910 products; live ledger | n/a | JUDGE-1 is on the **holdings-book layer `g = pnl/gross`** — different statistic, do not compare bps |
| **R6 JUDGE-2** | **9138 — this is the round that DEFINES W_ALPHA**; also 3288 (EXT), 9018 | **YES** | effect sizes reproduce bitwise across windows; only SE changes |
| R7 fuel-1 / fuel-2 | **9138** (but the "69.5th percentile" statement is on 10038) | YES | bootstrap B=4000, base seed 20260912 — off-pin |
| R8 BUILD-1 | headline **9018** (`battery.py` L12-14 `FULL_HI`); a W_ALPHA row exists (`FULL_TO_CEIL`, dg +0.01732) but **has no CI** | partly | `[V-blk r7_r9 §6.3]` |
| R8 BUILD-2, R9 | **9138** | YES | R9 closes the ceiling ⇒ 9199 |
| R10 screens / combine | **9138** (`books_on_pinned_axis.npz` verified) except TSMOM's mislabelled 3192 | YES | two A0 cost planes on one page (`RESULT_r10` §1 PWR, §2 fee_steady) |
| R11 cost truth / income | live-ledger windows (2026-08-01…09-11) | n/a | |
| **R11 tail / sizing** | receipts carry **both** 9138 and 10038; **the top-level document and the whole leverage ladder use 9138 only** | **mis-used** | D6 |
| R12 regime / smoothing | 9138 (alpha) + 10038 (tail) — correct | YES | |
| **R12 intervene** | **9199**, baseline A1x, tail window to 2026-09-09 (1683 days) | NO | pre-registered and disclosed, but never reconciled against E-0911-D `[V-blk r12_r13 §7]` |
| R13 deploy / A / B / verdict / r13b | alpha on **9138**, tail on **10038 (1673 d)** — the cleanest window discipline in the programme | YES | my own recomputation reproduces `V3_halt_criterion` digit for digit `[V-me]` |

### 3.3 Windows that are mixed illegally, or silently

1. **`RESULT_r5_angle1`** quotes a ladder on n=9018 and a per-year table on n=9139 **in the same document, unlabelled** `[V-blk r4_r6 §7]`.
2. **`DOCKET_r7_ship` §B-4** is internally inconsistent: its composition table says 9018, its prose two paragraphs later says 9138 `[V-blk r7_r9 §6.5]`.
3. **`DOCKET_r7` L315** quotes three σ percentiles in one sentence from three different (gauge, window) pairs `[V-blk r7_r9 §3]`.
4. **`ship1_receipts`** mixes two cost planes inside one directory (`SHIP1_A0_accounting.json` cheap, `…_PWR.json` fitted) and adds a third window (n=9277) in its offset spectrum with no explanation `[V-blk r4_r6]`.
5. **The n=9139 row is one anchor past the ceiling** — that anchor (2026-08-31 00Z) has a NaN F10 leg silently zeroed by L267, so it replays a *different book* `[V-me in source]`.
6. **`r3_attack`'s RESID_SHARPE arm has n=7908 where A0 has 9018** — any "full cycle" comparison for that arm is 7908-vs-9018 unless explicitly intersected `[V-blk r1_r3 §2]`.
7. **Bootstrap caliber drifts**: the pin says B=2000 / `default_rng([20260905,k])`. Actual: r7 B=4000 seed 20260912; r8_inbook B=4000 seed 20260905; r8b2 B=4000 seed 20260912; r12/r13 B=2000 as pinned; r13B B=2000. **CI widths in rounds 7–8 are not on the pinned caliber and the documents do not say so** `[V-blk r7_r9 §6.6]`.

---

## §4 THE UNIT TABLE

### 4.1 Turnover: raw vs matched

| | value on W_ALPHA | definition |
|---|---|---|
| `turnover` (the stored column) | **0.0303158** | Σ|Δw| over the member set, **not** divided by gross |
| matched = mean(`turnover`/`gross_total`) | **0.0540270** | the caliber that matches `g`; **ratio to raw = 1.782141** (mean of ratios) |
| mean(`turnover`)/mean(`gross_total`) | 0.0435784 | ratio of means; **= raw × 1.437517 = 1/mean(gross)** |

**The task brief's own statement is wrong and the desk already caught it.** 1.4375 is `1/mean(gross_total)`, which converts raw into a *ratio-of-means*, not into the matched caliber. Applying 1.4375 to 0.0303158 gives 0.0436, **not** 0.0540270 — a 24% error. The correct converter is **1.782141** `[V-me]`; `r13_verdict/receipts/RECEIPT_r13_verdict.json::V6_turnover_caliber` states this explicitly with `brief_claim_correct = false` `[V-me]`, and `r12_regime` §7 / `r12_smoothing` §83 print both `[V-blk r12_r13 §14]`.

**Where each caliber is used** (all `[V-blk]` unless marked):

| document / receipt | caliber | says so? |
|---|---|---|
| `RESULT_r5_angle1` §3 (dyn 0.05402 / fix 0.01926) | MATCHED | no |
| `RESULT_r5_angle3` §8, `RESULT_r5_newdata2` §6, all `r5_newdata3` tables (0.03084 / 0.03037 / 0.01607) | RAW | no |
| `SHIP1_A0_accounting.json::turnover` (0.030315) | RAW | no |
| `r9_critic/critic_arith.py` C2 | RAW, subtracted from a per-gross quantity ⇒ **wrong** (D16) | no |
| `r9` REV_SHORT receipt (24.4×) | MATCHED ⇒ right | yes |
| CLOSEOUT A-8 (39×) | mixed ⇒ **wrong** (D9) | no |
| `RECEIPT_r11_M1_fee.json::at_A0_replay_turnover_0.03032` | RAW ⇒ **wrong** (D17) | no |
| `r11_tail`, `r12_*`, `r13_*` | MATCHED, with an explicit unit-reconciliation block | yes |
| `r13A`/`r13B` `base_turn` (0.0556336 matched) | MATCHED but a **different series** (full-vector Σ|Δw|, not cost-consistent) `[V-me]` | the gate field records the file caliber separately |

### 4.2 bps per unit gross vs bps per anchor (the second half of the same trap)

- `g`, `pnl_ex/gross_total`, `carry_ex/gross_total`, `cost_ex/gross_total` are **per unit gross**: on W_ALPHA 0.634196 = 1.281337 − 0.479661 − 0.167481 `[V-me]`.
- The **raw columns** `pnl_ex`, `carry_ex`, `cost_ex`, `net_ex` are per anchor **at the book's actual gross** (mean 0.6956): raw `cost_ex` mean = **0.094756** vs per-gross **0.167481**, a factor 1.768 `[V-me]`.
- **`SHIP1_A0_accounting.json` prints raw component bps (0.808813 / 0.364018 / 0.064799 / 0.379996) next to `mean_g 0.688853`, which is a mean of ratios.** The components subtract correctly among themselves but **cannot** be compared with any per-unit-gross figure `[V-me]`.
- **Cost per unit turnover:** mean(`cost_ex`)/mean(`turnover`) = **3.1256** bps (this is the "3.1252 bps" in `RESULT_r11_nonforecast_income`); mean-of-ratios per gross = **3.0999** bps; the cost book's quoted average is **2.9537**. The 4.95% excess is the realised tier mix `[V-me]`.
- **Three layers of caliber** (model score / composite target / position book) differ by 20–25% per the desk's standing discipline — every quotation must name its layer. `RESULT_r6_judge1` is on the **holdings-book layer** `g = pnl/gross`; its bps are not comparable with rounds 4/5/7-13 `[V-blk r4_r6]`.

### 4.3 Two ledger traps that bit this programme (carried from the brief, confirmed in-programme)

- **`anchor_ts` in the executor ledger is a wall-clock float** (e.g. 1789158241.472 = 20:24:01Z), not the canonical anchor epoch 1789156800. Joining on the canonical value returns zero rows `[brief; handled correctly in `judge1_r6`]`.
- **`fills.jsonl` has duplicate `trade_id` BY DESIGN** — `ops/backfill_markout.py` appends a NEW row when the +60s mark becomes observable, and the canonical collapse is **LAST-WINS**. `infra1_cost/extract_fill_costs.py` L45-51 does it right (upgrades only when the incumbent lacks the mark; n_raw 81161 → n_dedup 33886, dup_diff 0) `[V-blk r1_r3 §1]`. **`judge1_r6/j1_realized.py` L78-81 and `refute_r6/r6_fee_dedupe.py` dedupe FIRST-WINS** — harmless for fee/turnover/timing (the backfilled row is a verbatim copy plus mark fields) but those devices would silently discard **every** backfilled mark if reused for markout work — i.e. exactly the instrument at the centre of the cost dispute `[V-blk r4_r6 §4]`.

---

## §5 WHAT THIS AUDIT COMPUTED ITSELF, AND HOW TO RE-RUN IT

Device: `handoff_audit/caliber/caliber_audit_recompute.py` (self sha256 recorded inside its own receipt).
Receipt: `handoff_audit/caliber/RECEIPT_caliber_audit_2026-09-12.json`.
Re-run, verbatim:

```
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=$HOME \
  python3 <repo>/multi_asset/exports/research/uplift_2026-09-11/handoff_audit/caliber/caliber_audit_recompute.py
```

It asserts an **empty** env whitelist, re-hashes all six inputs, asserts the device sha and the arm's `config_json` before touching a number, and writes: levels on all seven windows, the accounting-identity test, the two turnover series, the full tail ladder on **both** windows (7 leverage points each), the analytic frozen CI, the cost-book blend and effective rate, and the NAV arithmetic for every circulating planning pair.

**What I could NOT verify from this machine** (and neither can the reviewer, without pod2): every `/workspace/...` input — `meta_newprod_v4.npz`, `wide_fea_v4_meta.npz`, `dlw_v4raw`, `shadow_bundle_v4`, the `dev_v4` probe npz, every `preds/*.npy`, the LOB cube. All GATE-P "bitwise, maxabs 0.0" claims are self-reports of a remote comparison. The repo verifies the **judges**, not the **inputs**. Several rounds' devices exist **only** on pod2 (all of `r7f1/`, `r7f2/`, `r8b2/w10_sleeve_tilt{,2}.py`); if pod2 is lost, those verdicts have no device `[V-blk r7_r9 §0]`.
