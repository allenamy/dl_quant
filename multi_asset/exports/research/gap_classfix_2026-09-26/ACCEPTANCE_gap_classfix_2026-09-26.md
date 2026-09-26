> **创建:** 2026-09-26 17:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (integ) | **状态:** FROZEN 判据, 写于任何 gap 包读数之前(本包第一个提交; 本文件提交时 devices/ receipts/ 为空, 无任何补丁代码存在) | **作废条件:** lead 裁定改判据(只可追加 AMENDMENT 节, 不改本节字节)

# 缺锚类修复包(gap class fix)验收判据 — 冻结

验收线(lead): **下一次任意长度的缺锚, 不需要人即可被处理。**

## 0. 被修对象(读码所得, 生产 sha 12a76de8…)
`~/wide_shadow/fea171/combo_stage.py` 每个上一锚状态都按 **恰好 A−14400** 取:
L59 `state/weights/{A-14400}.npz`(king 生产者 H, 自平价 ① 与回落源)、L237–L248 `state_H_f10_{A-14400}`、L311–L318 `state_H_kc/fc_{A-14400}`。
缺锚后回落为零向量 ⇒ gross ≈ 0.07–0.1 ⇒ 飞前断言失败 ⇒ ABORT ⇒ 执行器 HOLD; 且 A 的状态在 abort 前已写 ⇒ 后续约 5 锚继续失败, 然后发布从零冷启动的书
(执行器 external_book.py L506-507 / legs.py L199 把 gross 归一回满杠杆 ⇒ 冷启动书 = 一次性全换手)。

## 1. 修法规格(实现前冻结)
- 每条状态(weights / kc / fc / f10)取 **anchor < A 的最近一份有效状态**, 与 A 的距离 d = (A−a)/14400 必须为正整数。
- 「有效」= 文件可读、npz 无 pickle、键齐、(若有 anchor 键)anchor 键 == 文件名锚、idx 为 1 维整数且 0 ≤ idx < NW 且不重复、val 有限且与 idx 等长。无效文件跳过并**具名记录原因**, 继续往更早找。
- 来源标签: d=1 且无跳过 ⇒ `own`(与现码逐字相同); 否则 `own_gap<m>`, m = d−1 = 被跳过的锚数; 有被拒文件 ⇒ 追加 `_rejected<n>`; m > MAX_GAP_ANCHORS(=6, 24h) ⇒ 追加 `_beyond_bound`。
- **越界仍承接最近有效状态并发布**(不冷启动、不 HOLD), 同时 HIGH 页报。理由: 执行器在缺目标时无限 HOLD 旧书(on_unavailable=hold), 旧状态就是执行器所持; 冷启动会被执行器放大成满杠杆一次性换手。
- 页报(HIGH, 发布后发出, 不占截止余量): 任何 `_rejected` / `_beyond_bound` / 回落(无任何有效状态)。界内缺锚不页报, 但写入 target_combo 与 combo_live_status 的 `state_lookup` 字段。
- 无缺锚时 target_combo / target_blend JSON 字节不变(新字段只在非 `own` 时出现)。

## 2. 臂与判据(沙箱重放, 设备 = lead 的 gap_arm_replay.sh 族, 生产目录只读)
重放锚: 基线臂 = 1790380800 / 1790395200 / 1790409600 三锚; 其余臂 = 1790409600(09-26 08Z)。
「权重逐位相等」= target_live_PARITY/<A>.json 的 weights 字典键集相同且每个 float 相等(==), 其余键除 `written_utc`、`weights_sha`(npz 压缩含时间戳)外全等。

| 臂 | 现码(12a76de8)判据 = 必须 RED(否则测试无分辨力, 本臂作废) | 补丁码判据 = PASS 条件 |
|---|---|---|
| C0 基线(无缺锚) ×3 锚 | 不适用; 现码必须对归档 PARITY(装置自检) | 权重逐位相等于现码同锚; state_H_{kc,fc,f10}_<A> 的 anchor/idx/val 逐位相等; target_combo/<A>.json 与 target_blend/<A>.json **字节**相等; weights_combo/<A>.npz 的 idx/val 逐位相等 |
| G1 / G2 / G6 缺 1/2/6 锚(删 A−4h…A−k·4h 的 state_H_* 与 weights) | rc≠0 或无目标, 或 kc/fc 来源非 own* | rc=0 且已发布; kc/fc/f10 来源 == `own_gap<k>`; 权重逐位相等于**现码 + 桥接参照臂**(把 A−(k+1)·4h 的三条状态以 bridge.payload 写进 A−4h 槽, 其余同 Gk) |
| X1 损坏(A−4h 的 kc 文件 = 垃圾字节) | rc≠0 / 无目标 / 来源非 own* 且无页报 | rc=0 已发布; kc 来源 `own_gap1_rejected1`、fc 来源 `own`; HIGH 页报点名该文件与原因; 权重逐位相等于现码参照臂(A−4h 的 kc 槽换成 A−8h kc 的 payload) |
| X2 错锚(A−4h 的 kc 文件内 anchor 键 = A−8h) | 同上(现码预期静默回落 warmstart_live_H 并发布 ⇒ 记 RED: 来源非 own 且无页报) | 同 X1 |
| X3 越界索引(A−4h 的 kc 文件 idx 含 NW) | 同上 | 同 X1 |
| B7 越界(缺 7 锚) | 同 G | rc=0 已发布; 来源 `own_gap7_beyond_bound`; HIGH 页报; 权重逐位相等于现码桥接参照臂(k=7) |

附加:
- U 单元测试(prev_state 的合成目录测试)全过; 且对现码的等价谓词(恰好 A−14400)跑同一组用例必须有红(证明用例有分辨力)。
- P 20260922 发布边界测试(`tests_combo_publication_boundary.py`, COMBO_PUBLICATION_SOURCE=补丁码)全过。
- T 补丁码单锚耗时 ≤ 现码 + 2 s(同锚 C0 臂)。
- 已命名的仿真伪差(不作判据): 仿真里生产者真实 H 是 A−4h 的 weights, 删除后补丁码自平价 ① 读更早的 weights ⇒ max|Δw| 非零; 实盘缺锚时生产者 st.H 就是最近一份 weights, ① 应为 0。

## 3. 不在本包判据内(设计选项, 另报)
- 生产者 LR 洞策略(shadow_loop_v3.py L752), 与 news2 的数字对齐后定。
- 成员历史缺锚 ⇒ f8 三列 24h 秩差置 0(combo_stage L167-176 → f8 L336-339), 修法与量级另冻判据。
- 其余站点(regime_dash / per_name_stop / stop_overlay / anchor_report / notary)的逐站点分类表。
