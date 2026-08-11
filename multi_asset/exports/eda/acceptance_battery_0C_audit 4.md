> **创建:** 2026-07-19 JST | **Session:** fable multi-asset-v2 (0C 独立审计) | **状态:** final | **作废条件:** acceptance_battery.py 门集/口径变更 或冠军产物重建

# 交接验收电池 acceptance_battery.py — 0C 独立审计 verdict

**审计对象:** `handoff/acceptance_battery.py` (0B 建, v2 @ 10:35)。规格 = `handoff/acceptance_battery_SPEC.md` (0C 预注册)。阈值 = `handoff/acceptance_thresholds_0C_frozen.json` (0C 冻结, 被 v2 auto-load)。
**方法:** 独立重跑 (不信 0B 自测): 冠军产物 + 存档 N1b/S1 + 人为破坏产物, 用 0C 冻结阈值跑 v2, 核验判决与 0C 当年人工判决方向一致。产物: `exports/eda/repro_v2.py`, `repro_matrix.py`, `e_check2.py`, `/tmp/0c_repro_v2.json`。

## 判词: **PASS — v2 SPEC-合规, 复现 0C 全部人工判决, 可交付。** 一个自测破坏产物 scale bug (0B 已自查修复), 一个非阻断 gate_a 标签精度建议。

## 时间线 (协作收敛)
0B v1 (10:03, 机制完整+占位阈值) → 0C 审 v1 + 出 SPEC (10:05) + 冻结阈值 (10:14) → **0B v2 (10:23→10:35) 逐门实现到 SPEC**。v1 我发现的 4 个 gap (无升级门 i / 无 bootstrap CI / 无 head-多样性 / hard-soft 未接线) **v2 全部关闭**。v2 还实现了 SPEC §5 的 forward-decay 三判据 (sub-H razor≥0.6 / full-H flat<0.9 / neg-lag 反转豁免) 与验证四态 (REJECT-untrustworthy | REJECT-degraded | REJECT-quality | ACCEPT-clone/upgrade)。

## 复现矩阵 (0C 独立重跑, v2 + 冻结阈值)

| 测试 | 候选 (IC) | 冠军 (IC) | 电池判决 | 触发门 | 0C 人工判决 | 一致 |
|---|---|---|---|---|---|---|
| T1 clone | champ5 vs self | — | **ACCEPT-clone** | 全 PASS; (i) 不升级 | 冠军干净 | ✓ |
| T3a shuffle-ts | champ5 打乱 ts | champ5 | **REJECT-untrustworthy** | f_index (ts md5≠) | 错位泄漏 | ✓ |
| T3b dup-head | champ5 复制单头 | champ5 | **REJECT-quality** | g (head-corr 1.0) | 伪 ensemble | ✓ (v1 gap 已闭) |
| T3c lookahead | champ5 注入未来 (w0.85) | champ5 | **REJECT** | e (峰移+1, IC 0.965) | 未来泄漏 | ✓ (注入修复后) |
| T2a 退化重训 | conformer lam_orth=1 (0.033) | lamorth0_xattn (**0.095**) | **REJECT** | b(0.033«0.090)[+a] | 退化 (惩罚砍半 IC) | ✓ |
| T2b N1b | N1b resid 0.016 / raw 0.068 | champ5 (0.082) | **REJECT-untrustworthy** | f + b | ARCHIVE (换皮) | ✓ |
| T2b S1 | S1 resid 0.018 / raw 0.067 | champ5 (0.082) | **REJECT-untrustworthy** | f + b | ARCHIVE (冗余) | ✓ |

## ★ 关键正确性确认
1. **门 (e) 反转豁免 WORKS (最要紧):** N1b/S1/冠军 三者 neg-lag 都是**反号大** (−0.15/−0.28/−0.25), 门 (e) **全 PASS 不误杀**。N1b forward-decay 实测 {−4h −0.277 / 0 +0.068 / +4h +0.031} 与 0C 当年 `arm_n1b_verdict.md` **逐值吻合**。团队 lead 提示的"负滞后反号是反转机制不是泄漏"被电池正确处理。
2. **门 (b) 容差 0.005 校准正确:** 冠军自比 0.0949 过; 最差 seed 0.0910 (=mean−0.0034<0.005) 会过; conformer 0.033 挂。**0B v1 占位 0.003 会误杀冠军自己的 seed-43** —— 我冻结为 0.005 (=2σ_seed)。
3. **门 (b) 抓交接第一风险:** conformer (误重启 lam_orth 惩罚) IC 从 0.095 砍到 0.033 → REJECT。若合作方重训误引入我们踩过的正交惩罚 bug, 电池一眼判死。
4. **head-多样性阈 0.999 校准正确:** 冠军 6 头两两 corr **0.993** (PASS, 真异质); dup-head 1.0 (FAIL)。
5. **门 (e) 本身 sound (自测 T3c BROKEN 是破坏产物 bug, 非门缺陷):** pred σ≈1.0 vs Yraw σ≈0.023 差 43× → 0B v1 自测的加性注入 α=3 只搅 ~7% → profile 仍健康 → 门 (e) 正确不触发。实测 α=50 / w=0.85 / 纯替换 → 门 (e) FAIL (峰移 +1)。**0B 已自查并把注入改为尺度匹配 z(Yraw)·w0.85 (v2 @10:35), 我复核修复后门 (e) 触发 (peak +1 = 0.965)。** SPEC §12 已补 scale-matched 注入的预注册要求。

## 非阻断建议 (标签精度) — #1 已被 0B 采纳并 0C 复核
1. **门 (a) 的 champion-relative 死锚地板对尺度敏感 → ★已修 (0B 采纳, 0C 终版复核).** 原: conformer 触发 (a) 全靠 **dead_anchor_frac=0.345** 而尺度不变量全说"没塌" (per-asset σŷ/σy=0.31, degenerate_ts=0, head-degen=0) → 被误标 untrustworthy。**0B 已把 (a) pass/fail 改为只由尺度不变信号驱动** (σŷ/σy≥0.02 floor + degenerate_ts≤0.01 + head-degen≤0.01), champion-relative 死锚降为诊断项 `dead_anchor_frac_vs_champ`。**0C 终版复核: conformer 现落 REJECT-degraded** (gate_a passed=True, gate_b 0.0327«0.0949 FAIL) —— 子标签正确。0B 四合成候选单测 (weak-x1/100 PASS(a)→degraded / near-collapse x1/1000 FAIL / constant FAIL) 覆盖到位。
2. **panel 不同 YR 时的跨-target IC.** N1b/S1 是按 own residual-YR 打分 (0.016/0.018)。冠军在场时**建议同时报 cand.pred vs CHAMP.YR** (同 index) 做严格 apples-to-apples。canonical 同板重训 (require_match=True) 下无关。判决不受影响 (都 REJECT)。
3. **embargo 从 fold 产物不可核验** (只有 te_rows)。门 (f) 核 OOS-disjoint + index 对齐, 不核 train/val embargo。建议给产物契约加 tr_rows, 或维持为 §11 人工审边界。
4. **REJECT-degraded 路径 (hard 全过、仅 b 挂) 未被现存档臂触发** (它们先触 hard 门, 正确)。同板更弱候选可触发; 验证逻辑由 verdict 合成码确认。

## 0B 三点转达 — 0C 裁定

1. **T3c BROKEN (自测注入尺度 bug):** 复核确认 —— 门 (e) sound, 是破坏器注入尺度不匹配, 0B 已修 (z(Yraw)·w0.85)。**current 版全自测 = SELF-TEST OK** (T1 ACCEPT-clone / T3a f / T3b g / T3c e 全对)。收口。

2. **门 (g) head-corr 阈值 → 裁定: 收紧到 0.9999 (非放宽)。** 冠军 lam_orth=0 六头**天生近冗余 corr 0.9957 = +IC 杠杆本身** (lam_orth=1 正交惩罚 DILUTIVE 砍半 IC)。门 (g) 要抓**复制** (corr→1.0 机器精度), 不抓**设计冗余**。0.999 只留 0.0033 余量会误杀合法重训 → **0.9999** 只对数值复制触发。**承重判据 = ensemble ≠ 任一单 head** (抓 best-head 替换 + 复制填充)。已改冻结 config `head_corr_max: 0.9999`。

3. **T2 口径 → 裁定: 以 Yraw (原始前向收益) 为 apples-to-apples 基, 不用候选自己的残差-YR。** 实测: **Yraw 三者逐字节相同** (md5 02c03849, 目标无关), **member 相同**, 但 **CL 真不同** (冠军 1.13M clean cells vs N1b 987K / S1 990K —— N1b/S1 在**更稀的 clean 网格**上评)。
   - **Yraw 口径 (承重):** 冠军 **0.1212** / N1b **0.068** / S1 **0.0669** → 都 ~0.05 低于门 → **REJECT (b)**。复现我 ARCHIVE, 无残差混淆。
   - **残差-YR 是训练目标依赖的** (N1b=YR4B/S1=YR4K/冠军=YR4), 跨臂不可比 —— N1b/S1 own-resid 0.016/0.018 是**补充因子增量 caliber** (book-marginal 门的事, 非替换门)。
   - **untrustworthy vs degraded:** N1b/S1 落 REJECT-**untrustworthy** 因门 (f) 硬失 —— 它们 **CL 网格真不同** (更稀), 对替换候选这本身是红旗, 标 untrustworthy **正确**。若要看纯 degraded 路径, 把 pred 放冠军网格 + Yraw 打分 (0.068«0.116 门) → b 失 = degraded。**两路都 REJECT。** 建议: 冠军在场时 gate (b) 的比较 key 在 ic_raw (Yraw), 使即便 (f) 触发, 报告也显出 raw-IC 差 (0.068 vs 0.121) 让 degraded 可见。

## 一句话给汇报
acceptance_battery v2 逐门实现到 0C SPEC, 独立复现 0C 全部人工判决 (S1/N1b ARCHIVE + 破坏产物 REJECT + 冠军 ACCEPT-clone), 门 (e) 反转豁免不误杀真反转, 门 (b) 抓退化重训; 唯一 bug 是自测注入尺度不匹配 (0B 已修, 我复核触发); 一个 gate_a 标签精度建议 (非阻断)。**可交付。**

---
**产物:** `exports/eda/repro_v2.py` · `repro_matrix.py` · `e_check2.py` · `/tmp/0c_repro_v2.json` · `handoff/acceptance_battery_SPEC.md` (§12 补 scale-match) · `handoff/acceptance_thresholds_0C_frozen.json`
