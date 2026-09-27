> **创建:** 2026-09-27 05:4xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(integ 入库, lead 裁定原文) | **状态:** 第 5 轮判据, 写于 08Z(1790496000)任何读数之前 | **作废条件:** lead 另行裁定

# lead 裁定原文(逐字转录, 2026-09-27)

裁定:选 B,不加 mhfill 臂。
先说明:我的 P5 原意就是「只重跑 C0 里的 current_vs_archived 这一子项」,不是重跑整个 C0,措辞不够清楚是我的问题。
第 5 轮判据如下,写于 08Z 读数之前:
(i) 在 08Z(1790496000)上,新机的 current 回放对新机的生产存档,权重、beta_overlay 全部逐位相同。取值来自冻结 C0 段里的 current_vs_archived 字段,你的等价性控制已经证过它与冻结判官逐字段相同。
(ii) patched == current:引用 run 4 在 arm64 上对 3 个无洞锚的逐位结果,不重做。
(iii) 必报且必须成立:08Z 上 patched ≠ current 的部分,逐项点名,全部来自 MH_RECOMPUTED 的 3 个锚 [1790424000, 1790438400, 1790481600];current 那一侧日志显示缺的正是这 3 个锚。有任何一处解释不了 ⇒ 停下来交给我。
理由:(ii) 在同主机上已经有逐位收据;mhfill 是窗前新造的装置,加它会引入新的出错面,换来的却只是重复证明。
请把这段裁定原文和你 05:33Z 的控制运行一起入库,之后再读 08Z。

# integ 执行注记(不改判据)
- 装置:`devices/run_c0_round5.sh`(EXPECT_MH=1790424000,1790438400,1790481600)→ `gap_fix_judge_c0.py`(冻结 C0 段原文, 判官 sha 01760c37 / 段 sha a6c46dac 断言)→ `c0_round5_attrib.py`(判 (i) 与 (iii); (ii) 引 `receipts/GAPFIX_JUDGE_run4_arm64.json`)。
- (iii) 中「current 那一侧日志显示缺的正是这 3 个锚」:current 的日志只打印缺锚**个数**(`NC A2 member history: …(missing k)`),不打印锚名。装置用两件事合起来证:日志里 missing == 3;current 读的是同一份快照 members_hist.npz,在 A 之前的 4h 网格上它的洞 == 字面量这 3 个锚。锚名由文件推出,不是从日志里读出来的。这一点在此具名。
- 05:33Z 控制运行(`round5_control_0533Z/`, 09-27 00Z 1790467200, 存档为 x86 所产):冻结 C0 段判 FAIL:
  - current_vs_archived = `other keys differ: ['beta_overlay']`(跨主机);
  - current 与 patched 之间 64 个权重不同(max |dw| 8.167e-07),fc / f10 状态不同;
  - 日志:current 为 `237/239 … (missing 2)`,patched 为 `239/239 … (missing 0)` 加 `MH_RECOMPUTED (gap class fix) 2 anchors [1790424000, 1790438400] errors {}`。
  这次运行就是促成本裁定的那次读数。其后在 option B 装置上的控制见 `round5_controls/`(提交 ab8f2a814 之后的两个提交)。
