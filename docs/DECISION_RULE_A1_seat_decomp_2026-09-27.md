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

## 修订 1(lead,05:5xZ,写于任何读数之前;起因:fresh 读装置后指出 4 处冲突)
正文是我没先读装置就写的,有 4 处与装置冲突。以本修订为准:
1. **块长**:判定用 **30**,与 3b 一致,因为本读数要检验的正是 3b 的结论,换块长会让两者不可比。7 日块另报一列作参考,不作判。读数装置 `rc_read_a1.py` = rc_read.py(3dd2d635)加一份最小 DIFF,只把臂名、成员、根目录、块长参数化。恒等控制:用 3b 的配置(RED、m0、块 30)运行,必须逐位复现 RC_READ_hybrid 2e75f1b3 的全部段数;复现不了就不读。rc_hybrid_legs.py(1b8d9643)逐字复用,sha 按字面量断言。
2. **成员**:只做 **m0,两种子**,与 3b 同形,共 6 格。m1–m7 不跑(约 15 小时,相对 3b 已有的证据形状只是重复)。局限写明:单成员;但 A1 的 IC 在 8/8 成员上为正,m0 不是挑出来的。
3. **泄漏门**:A1LEAK_DONE rc=0,加上 lead 读完审计后写的 `/workspace/a1seat_2026-09-27/LEAK_CLEARED` 标记文件(内容为 lead 判语 + 审计收据 sha)。没有标记就不跑。执行者不参与「算不算泄漏」的判断。
4. **口径**:正文写的「RAW v4 口径」改为「与 3b 同判官:news_stats 7141ba42 的 dbar,单位 NAV bps/日 × GM」。
- 归属:只读 fresh2 的 /dev/shm/mretrain_2026-09-26;产物全部写到 /workspace/a1seat_2026-09-27。
