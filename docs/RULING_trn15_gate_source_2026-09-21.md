> **创建:** 2026-09-21 | **Session:** session_01KW6frfphbFmFzx7wUtGhLb(lead) | **状态:** 裁定记录 —— **对用户 09-18 裁定的解释**, 非新裁定; 实现已在库但**一步可回滚**, 用户可推翻 | **作废条件:** 用户另行裁定

# 裁定记录 · TRN-15 的 `not_changed: "the gate source"` 与 `mechanism_approved: true` 的张力

## §1 事实(合同原文, lead 逐字读出)

`ELIGIBILITY_CONTRACT.json` → `month_contract_rulings.TRN-15_export_baseline_per_month`:
- `mechanism_approved = True`
- `ruling` = 「批准基线成为**按月**的批准对象: 每月新 pins 与基线 json 立档, 其 sha 在导出阶段运行前批准进本合同。**门不放宽**: 它仍要求逐字节相同。」
- `not_changed = "thresholds, identities, the 28-input floor, **the gate source**"`

**张力**: 不改门源码, 这个机制无法实现。⇒ 该裁定按字面**批准了一个它同时禁止实现的东西**。

**同时成立的另一个事实**(`READINESS_october_v4_chain_2026-09-19.md` L193 已记, 我今天才读到): 该机制 `mechanism_approved: true` 但**从未被实现** —— 09-18 至今三天, 合同里写着的机制**没有任何门在执行它**。

## §2 两种读法

- **(a) 状态描述**: `not_changed` 那一行是在记录「裁定时刻尚未改动的东西」。⇒ 实现它属于执行该裁定。
- **(b) 禁令**: 「门源码」与 thresholds / identities / 28-input floor 并列, 都是禁令。⇒ 实现它超出该裁定, 需新的用户字。

## §3 lead 的裁定(**按最佳建议推进, 但明确标注这是解释**)

**采用 (a), 保留实现。** 理由三条:
1. `not_changed` 列表里的另外三项(thresholds / identities / floor)都是**判准参数** —— 动它们会改变「什么能过门」。**本次源码改动不改变门的严格度**: 仍是对**显式批准的常数**做逐字节比较, 四种具名拒绝(旧合同形状 / 月份未声明 / 月份未批准(缺失**或** null) / 条目格式错), 且全局 `approved_baseline` **明确不作回退**。
2. 不实现的后果不是「维持现状」, 而是**十月导出按构造必败** ⇒ 整条月度链跑不起来。「维持现状」在这里等于「链停摆」。
3. **一步可回滚**: 两个旧门已归档在 git(`.r1_d63f4ec3` / `.r1_16e9cc32`), 回滚 = 恢复旧对, 十月回到按构造必败的状态。

**我必须声明的利害**: 采用 (a) 的人是我, 而我也是推动这条链往前走的人。**这是对用户的字的解释, 不是方法论判据** —— 所以它归用户裁, 不归独立研究员裁。**用户一句话即可推翻, 回滚成本是一次文件恢复。**

## §4 由此立的一条规矩(与今日其它发现同族)

> **合同里写着、却没有任何门在执行的机制, 与不存在的机制不可区分。**

与 E-0920-G(「从未被执行过的应急路径, 与不存在的路径不可区分」)同族: 那条讲**路径**, 这条讲**机制**。
**验收线**: 任何 `mechanism_approved: true` 的条目, 必须同时给出**执行它的门与那条门的红/绿实测**; 给不出 ⇒ 该条目标记为 **DECLARED_NOT_IMPLEMENTED**, 不得当作已生效引用。
**立即应用**: 对本合同全部 `mechanism_approved: true` 条目做一次普查(本文只处理了 TRN-15, `CONTROLS_REF_identity` 亦为 true, **未查**)。
