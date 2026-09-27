> **创建:** 2026-09-27 05:5xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(lead) | **状态:** 冻结判据,写于任何 A1 书层或拆分读数之前 | **作废条件:** dlarch 的 A1 泄漏审计报出泄漏(那样本读数不跑);rc_hybrid_legs.py / rc_read.py 与 3b 所用版本不同

# 判据:A1 相对 A0 的席位 / 构成拆分(描述性,只回答 G4 终版第 3 条)

目的:把 G4 终版(bf503aa66)第 3 条「King 进书主要走席位通道,所以排序变好没变成书变好」,从「相容」升为「已测」或「未被支持」。作者是 lead,对结论无利害;fresh 是这条假说的提出者,只负责执行,不参与判定。

## 1. 运行
- 装置:fresh2 的 `mretrain_2026-09-26/devices/rc_hybrid_legs.py` 与 `rc_read.py`,版本与 3b 相同(sha 在收据里断言为字面量)。
- 对比对象:A1(按月重训)m0–m7 对 A0 m0–m7,成员逐一配对;其余设置与 3b 相同。
- 产出 FULL、SEAT_ONLY、COMP_ONLY 三格,以及交互项 INT = FULL − SEAT_ONLY − COMP_ONLY。按段(pre-2026 / 2026)分别报,均为逐日书层净额(RAW v4 口径),CI 用 7 日块 MBB。
- 时机:dlarch 的 A1 泄漏审计到达终态且未报泄漏之后;只在 pod2 上跑,过资源门,登记进 INFLIGHT_REGISTRY。

## 2. 判定(按段,机械套用)
- **不可判**:|INT| > 0.5·|FULL|。三个信号有交互、不可相加(STY-03),拆分在这种情况下不可解释。
- **已测:席位通道承载**:同时满足三条:SEAT_ONLY 与 FULL 同号;|SEAT_ONLY| ≥ 0.5·|FULL|;|COMP_ONLY| < |SEAT_ONLY|。
- 其余情况:**未被支持**。
- FULL 本身就是用户问的「A1 书层格」,只作描述。A1 的 IC 层判词(FAIL,d585e1792)维持不变,本读数不构成任何上线依据。
