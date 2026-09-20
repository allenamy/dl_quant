> **创建:** 2026-09-20 | **Session:** CF3 | **状态:** 对 `at_legs2.py` 冻结字节的**外部**更正条 | **作废条件:** CF3 结果件被撤回

# `at_legs2.py` / `at_render.py` 里「三信号书层拆分不可识别」一段已被 CF3 取代 —— 装置字节不改

`at_legs2.py`(装置 sha 见 `receipts/AT_LEGS2_RECEIPT.json`)的 docstring 有一节
**"WHAT IS *NOT* IDENTIFIABLE, STATED RATHER THAN MANUFACTURED"**, 其中写:

> "The archive stores only sm_kc, sm_fc, the king book and the combo — never z_king, z_f10 or z_fund.
> Recovering the three-signal split therefore needs a producer re-run that dumps those three z vectors
> per anchor; this device does not guess one, and the result document says so."

**这一句的前半对、后半错, 原字节保留不改**(装置必须与它自己的收据 `self_sha256` 对得上):

- **对的**: `chain` 非线性(±cap 截断 + 死区 + 逐组件 EMA), 所以**线性**的三信号书层拆分确实不存在。
- **错的**: 「三个 z 从未落盘 ⇒ 需要生产者重跑」。三者**都在研究侧档案里**:
  `object_b_2026-09-19/work/A0_main/P1.vec.npz` 的 `legz` 存 king / rev24 / fund 三条腿 z(全 10,039 锚);
  `P2_SCORES.npz` 存 F10 分数, 而组合阶段只通过 `rankdata(f10_pm[okf])` 用它(`b_lib.py` L135)⇒ 由分数重建的 `zf` 与生产 `zf` **逐位相同**。
- **正解不是线性拆分, 也不是生产者重跑**, 而是**反事实重链**: 把某个信号整体置零, 让整窗从同一播种起点重跑一遍 `chain`。
  零生产接触、零 GPU。装置 `cf_rebuild.py` / `cf_arms.py`, 结构断言逐位全绿
  (`CF_REBUILD VERDICT=PASS checks=22 failed=[] state_anchors=10038`)。

**同一句话的其它落点(一并在此更正, 原字节全部保留)**:
- `devices/at_render.py` 里渲染该句的模板, 以及它的产物 `receipts/ATTRIB_TABLES.md` 第 366 行;
- `docs/RESULT_attribution_2026_vs_history_2026-09-20.md` 第 13 / 60 / 129 / 301–311 / 583 行(已在该文件内就地追加更正)。
- 另一处**同族但不同题**: `multi_asset/exports/research/uplift_2026-09-11/ANALYSIS_independent_report_2026-09-12.md` L237 的「非线性混合下腿贡献不可识别」—— 那是 SB 席位构造, 不是本题; 但它属于同一类判断, **现在这一类有方法了**(反事实重链), 需要时可重开。

**去哪看**: `docs/PREREG_three_signal_counterfactual_2026-09-20.md` 与 `docs/RESULT_three_signal_counterfactual_2026-09-20.md`。
`at_legs2.py` 的**其余部分(结构断言 A0a–A0d、组件层分解、席位极值子样本)不受影响**, 只有 §3.4 的人口口径另有一条更正, 写在结果件里。
