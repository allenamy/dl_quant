> **创建:** 2026-09-13 ~05:40Z | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T1) | **状态:** 定义性修订, 由门失败触发, 冻结先于任何结果数字 | **修订对象:** `PREREG_T1_edge_diagnosis_2026-09-13.md` sha256 `95482142…77f6`(+ AMENDMENT 1 `a7628a72…a374`) | **作废条件:** 同主文

# AMENDMENT 2 · 成员集 m 的定义写错了: 装置用的不是 meta members

**触发**: GATE LAG0 首跑失败(`receipts/RECEIPT_T1_lags.json` 首版: h=0 king maxabs 20.80, fund maxabs 61.63 bps, 对 NW_s42 存档 `legs_king`/`legs_fund`)。查因: 装置在 `MEMBERS_TOPN=829` 时**重建**成员集(`w10_sleeve_r18.py` L77–83): 每锚取 `qvk` 有限的全部名(`nan_to_num(qvk, −1) > −0.5`), **不用** meta 的 `members`; 之后 `legs()`/`run()` 再与 CRYPTO m1 掩码相交。主文 §4 写的是「m = members[k] ∩ CRYPTO m1 掩码行(与装置同)」—— 括号里的意图(与装置同)是对的, 字面(members[k])是我对装置的错误认识。
**同时**: `t1_states.py` 首跑用的是错误的成员集, 已在输出任何内容之前停掉(stdout 0 字节, 无收据), 没有产生、也没有看到任何状态数字。GATE LAG0 的失败读数只是装置保真度诊断, 不是结果。

**修订(定义性)**:
1. §4 与 §6 H3 的成员集改为 **m_k = { n : qvk[k, n] 有限 } ∩ CRYPTO m1 掩码行**(= 装置 MEMBERS_TOPN=829 语义; 掩码行缺失时装置不施掩码, 仅 x0910 在掩码末行之后前推, 同主文)。这也正是 r8 BUILD2 的 sigma(与线上仪表 maxabs 0.0)所用的「the same masked member set the book ranks at anchor i」。
2. GATE X 增加: x0910 元与原元重叠行的 `qvk` 逐值相等(NaN 位置相同)。
3. GATE LAG0 阈值与判读不变(≤ 1e-9); 若修正后仍失败, 依赖 H3 的读数不报。
4. 其余定义不变。trackF `build_regime.py` 用的是 meta members(与本修订不同), 本轮状态值因此**不应**与 r6 §5 / trackF 的 sig_fund 逐值比较; RESULT 中若并列引用须注明成员集差异。
