# PROPOSED5 · 出口门 fp2dyn 变体(只折算在役席位)— 2026-09-17

> **创建:** 2026-09-17 13:1xZ | **修订:** 14:4xZ rev2(复审四轮) | **Session:** b9646a9e | **状态:** 已写入合同(scope 2026-09 @ /workspace/fp2_2026-09)并在真实数据上跑过, **待独立研究员复审**; 未审批前不作换装许可。**性质: 事后出口判定范围变更(接受域扩大: 同一批旧书 v2 FAIL / 变体 PASS), 不是单纯身份更正**; 旧 FAIL 收据保留 | **作废条件:** 复审否决; 或回放动态席位再次被证明不跟踪实盘

## 1. 用户字与性质
「没道理用 fix 席位回测吧, 线上的策略都是动态席位, 那回测应该也是动态的, 用历史当时同样策略得出的最佳权重来才能反映真实自动化策略的表现」(2026-09-17)。性质 = 评估对象是在役的动态席位策略。

## 2. 为什么 fix 席位曾在出口门里
九月 2 日 E-0902-D: 旧回放装置的 msharpe 动态席位 2026 年 king ≈0.01 而实盘 0.21(回放 king 腿用陈旧逐年折外预测)⇒ 规定席位敏感臂附一本固定实盘席位(W3FIX 0.21/0/0.79)的书作部署等价读数, 出口门 v2 因而检查四本书。

## 3. 现在为什么可以只看 dyn
- v4 链回放 king 腿 = 正确折外序列; 回放动态席位 2026 年均值 king 0.362/0.374(A0/A1), 最近 30 天 0.315/0.345; 实盘 09-16 12Z–09-17 08Z 0.359–0.379(`regime_dash.jsonl w3_masked_king`)。九月病灶不在。
- tradable 掩码下 fix 席位两书 gross_total > 1.000001(A0 28/34 锚, A1 33/41 锚, 最大 1.03), 九月 m1 掩码下无一超 ⇒ 评估机制性质, A0/A1 相同, 与新模型无关(受据 `OUTSIDE_MASK_PNL_2026-09-17.json`, AMENDMENT 11)。
- 决策装置的 formal profile 本来只用 dyn 席位四格。

## 4. 变体内容(对冻结 v2 d63f4ec3 的最小补丁, 5 处, 52 行 diff)
`v4e_gate_export_fp2dyn.py` 9a61420c: `CHECK_SEATS = {"dyn"}`; E8/E9 对每本书照算, `informational_seat = seat ∉ CHECK_SEATS`, 门判词只折算 `ok or informational_seat`; 版本串与 `seats_checked/seats_informational` 入收据。**不变**: E5/E6/E7、28 名输入底线、所有哈希、所有阈值(gross_max 1.000001 等)。原 v2 文件未动(仍是 do-not-touch, 仍在批准表)。

## 5. 接线
- 合同: `gates.BUNDLE_export.approved_source_sha256 += 9a61420c…`, `approved_variants["v4e_gate_export_fp2dyn.py"]`(scope V4_MONTH 2026-09, R /workspace/fp2_2026-09; 后续链需各自批准); 前身 `ELIGIBILITY_CONTRACT.pre_PROPOSED5_b996e1d7.json` 保留; pipeline 套件 helper 剥离 PROPOSED5 重建 r1。
- 驱动: 可选键 `GATE_EXPORT`(默认 `v4e_gate_export_v2.py`), DEV_FILES 含所选门; 本月合同 env 加 `GATE_EXPORT=v4e_gate_export_fp2dyn.py`(env sha b7d0afa7 → f008eb38, 前身 `.pre_PROPOSED5_b7d0afa7`)。
- 决策: `EXPORT_GATE` 参数记入收据, `require` 验其为合同批准源。

## 6. 真实数据
冒烟(12:5xZ, 收据写到 scratch): PASS, E8 dyn ok / fix informational, E9 median 0.9995 / 1.0025(dyn), 带外 0。正式重跑(preflight → export → decision)结果见 AMENDMENT 12 附记与 `FP2_receipts/*_p5.*`。

## 7. 不改变的结论
G1′ UNDECIDED ⇒ 本轮不换装。PROPOSED5 只让 G3 反映在役席位的书, 不是换装许可。

## 8. rev2(复审四轮, 2026-09-17 14:4xZ)— 只豁免机制真正打破的两条
复审指出 rev1 把 fix 席位的 K1–K4/K7 记账恒等式与 E9 基线身份一并降为信息, 宽于「处理 gross 超限」。rev2(e55875d0, 58 行 diff): 对 CHECK_SEATS 之外的席位, **只有 K6(gross ≤ 1.000001)与 E9 带宽**是信息项; K1–K4/K7 恒等式与 E9 基线身份(批准 sha、冻结窗覆盖)**照旧折算进判词**——诊断书也必须是诚实的书。套件 `tests_v4e_gate_export_fp2dyn.py` 6/6: 同一合成书上 v2 与变体并排, fix K4 破坏 / fix 基线 sha 错 ⇒ 两门皆红; fix gross 1.03 / fix 带外 ⇒ v2 红、变体绿且标 informational; dyn 任何破坏 ⇒ 两门皆红。
**限定**: 回放动态席位与实盘的**水平**一致(2026 均值 0.36–0.37 vs 0.36–0.38)不是逐锚生产平价; fix 对照的旧角色被重新定义, 不是被「认证消失」。真实数据(本轮): fix 两书恒等式与基线身份全过, 只有 K6 红 ⇒ rev2 与 rev1 的真实判词相同(PASS), 决策仍 NO_SWAP。
