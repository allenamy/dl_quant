> **创建:** 2026-09-23 08:0xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(lead) | **状态:** 冻结 —— 写于 Stage 1 **任何 NAV 或 NAV 导出数字之前**(当时 OLD / NEW_s42 运行中,尚无输出被读) | **作废条件:** 预注册 `PREREG_old_vs_new_models_same_engine_2026-09-23.md`(8530d2b7f)或本修订改动

# 修订 1:加入与现役发布语义一致的旧模型对照臂 OLD_HOLD;判据改为"两个旧臂都要赢"

## 起因(来自运行前身份披露,不是来自任何结果)

Stage 1 代理的 `IDENTITY_DISCLOSURE.json`(e6d8f6680,`written_before_any_nav: true`)列出具名混淆 **C1**:scaled 门失败时,**OLD 交易生产者的 King 形态回退书(kind 1),NEW 则 HOLD**。OLD scaled 的回退锚占比:2023H2 223/1109(20%)、2024 294/2196(13%)、**2025 806/2190(37%)**、2026 0。

在册受据(F 族,`fallback_counterfactual_F_family_2026_09_20`):回退形态本身是亏损载体(F0 −1.2438 bps/锚),HOLD(F2)优于任何重建 king 书。而**现役生产自 2026-09-18(f10_sha_pin)起,发布失败即 HOLD**(09-21 16Z 首次生产触发)。

⇒ 原预注册的 OLD 臂带着一个**现役已不存在的、已知亏钱的发布语义**。它回答的是"旧模型 + 旧发布语义 vs 新模型 + 新语义",而换装决策要问的是"**在现役语义下**,旧模型 vs 新模型"。

## 修订内容

1. **新增臂 OLD_HOLD**:OLD 目标中 scaled kind = 1(King 回退)的锚改为 HOLD(维持上一锚合约数量,与 NEW 的 HOLD 语义同一实现),其余逐位不变。其它设置、32 路径、随机数、窗口与 OLD 完全相同。改写须有往返测试:把 HOLD 锚换回原 kind-1 目标后与原 OLD 逐位相等;逐段 HOLD 锚数须等于披露中的 king_fallback 数。
2. **判据**:G1–G5 **原样**,但 PASS 需要 NEW(两种子各自)**同时**对 OLD **和** OLD_HOLD 两个对照都满足 G1–G5。只对其一满足 ⇒ UNDECIDED,并写明是哪一个。
3. REVERSE 的定义同步:两种子对 OLD_HOLD 的 G1 区间上界都 < 0。
4. OLD vs OLD_HOLD 的差(同一模型、只差回退语义)**单列报告**,作为 C1 的量化 —— 它不是判据,但解释"新旧差距里有多少是发布语义"。
5. 其余具名混淆 C2–C5 不修订,照原样报告;C4 的运行前补记(NEW F10 折间缺口 ≥217 锚,年初比 OLD 更陈旧)一并写入结果。

## 这条修订的方向

**只会让 NEW 更难通过**(多一个对照、且去掉了 OLD 身上一个已知亏损源),不放宽任何门。写于任何 NAV 之前。
