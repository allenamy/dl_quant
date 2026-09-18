# 复审请求 FP3 第十轮: 六组缺口本轮推进的全部交付(一并排查)— 2026-09-18

> **创建:** 2026-09-18 08:4xZ | **Session:** b9646a9e(主研究员) | **提交范围:** 28305881 之后至本轮末(见 git log; 全部在 `research/book-uplift-2026-09-11` 分支) | **无部署**(执行器仍 409ea16)

## 按六组
| 组 | 交付 | 请重点核 |
|---|---|---|
| 1 完整生产策略回放 | **P-C1** 三新锚精确(`RESULT_FP3_PC1…` §2)+ 历史 74 锚(§6; 装置 `pc/pc1_intent_replay.py` v9, 运行器 `pc1_history.py`, 收据 `PC1_HISTORY_0906_0918`); **P-C2** 五天层分解(`RESULT_FP3_PC2…`; `pc2_layer_decomposition.py` v2; `PC2_<day>.json`); **P-C3**(`RESULT_FP3_PC3…`; 覆盖四成) | ① v8 的两处输入解析修正(phase_A `untradable_names` 是 dict; 止损集 = 上一锚 phase_C `stopped`)是否还有遗漏; ② 09-06→09-12 16Z 书层段不精确归因为老执行器树版本差——是否应按锚检出旧树复现; ③ P-C2 用生产者面板收盘定价(与场所标记在极端锚差 0.2–0.55)是否可接受; ④ 「执行层不是放大器」这一结论的边界 |
| 2 现金与账本 | 无新取数(等只读凭证); 现金 v5 不变 | — |
| 3 Q6 | **影子 v2** `q6/q6_shadow.py` + `RESULT_FP3_Q6_shadow…` + `Q6_SHADOW_0808_0918.json` | ① LP 连续松弛替代精确枚举(精确版在真实请求量上 unmeasurable)——「距离>0 可靠、=0 不证明」的口径是否可作影子合同; ② 分段起点 = 整书平仓后回读、非请求流未建模的边界; ③ 三名持续未解释(RVN/ARKM/IMX)是否就是 Q6 设计里的「被吞掉的差额」 |
| 4 数据与成员资格 | 判活规则 **PROPOSED6** 入 `ELIGIBILITY_CONTRACT.json`(未 APPLIED, 前身 `r2_753f9752` 保留; `proposed_gates.MEMBER_LIVENESS`) | 规则措辞与边界(零成交真实条通过; 非场所资格真值)是否可入合同 |
| 5 未来重训交付 | RUNBOOK 2026-10 **§0★ 修订 7**(唯一执行清单; 负控实跑收据 `FP3_receipts/chain_negctl_2026-09-18/negctl.log`); 新立 `docs/PRODUCTION_INTERVENTION_LEDGER.md` | ① 负控「在正确的地方停」是否足够作版本绑定的端到端验收; ② 干预台账九月回填的锚位是否正确 |
| 6 最终评估 | 未动 | — |
| 附 | 只读实盘一页 `page/live_page.py`(`LIVE_PAGE_20260918.md`) | 真实分母的表述(空头 +42.9%)与「三句话分开说」是否达到反转归因件 D 项的要求 |

## 本轮我自己的更正
P-C1 v7 曾靠冷却集重建与 held_exit 碰巧对上三新锚, v8 修了 dict 解析; Q6 影子 v1 用请求账本当已知成交把整本书报成未解释, v2 改 fills.jsonl; 页面「相对起始资金」误用首行小额余额, 改总入金。
