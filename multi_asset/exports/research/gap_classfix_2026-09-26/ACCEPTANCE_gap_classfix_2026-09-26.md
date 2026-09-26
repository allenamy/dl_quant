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

## AMENDMENT 1(2026-09-26 17:4xZ, 写于任何重放读数之前; 只加细则, 不改上文)
- 「HIGH 页报」在沙箱重放中的判法: 沙箱一律是演练分支(`COMBO_LIVE_DIR` ≠ target_live ⇒ `_rehearsal=True`), 补丁码与 M3 同样**演练不发只记**,
  所以判据读 run.log 的 `GAP_PAGE` 行(即实盘会发出的同一段文字): X1–X3 该行须含 `state_H_kc_<A-4h>.npz` 与 `rejected`; B7 须含 `beyond_bound`;
  G1/G2/G6 与 C0 **不得**出现该行。实盘发送路径 = 发布成功后 `_page("HIGH", …)`, 包在 try 里(页报失败不把已发布的书变成中止)。
- 「现码 RED」的判法固定为: rc≠0, 或无目标, 或 target_combo 的 kc/fc 来源不以 `own` 开头(现码无任何缺锚页报机制, 故 X2 的静默回落记为 RED)。
- C0 另查: 现码重放的权重与生产归档 target_live/<A>.json 逐位相等(装置自检; 除 written_utc / weights_sha)。
- 装置提交 `1ffd…` 之前的 HEAD 为本修订的前提; 判官 = devices/gap_fix_judge.py(已提交)。
- 更正(同日): 上一条「装置提交 `1ffd…`」是占位笔误; 实际装置提交 = `2d54e2622`(判官/钩子/运行器/补丁树生成器), 早于本修订与任何重放读数。

## AMENDMENT 2(2026-09-26 17:4xZ, 成员历史组件; 写于该组件任何代码与读数之前)
lead 派单(PROGRAM_loop §2-1b): 缺锚 ⇒ members_hist 无 12Z/16Z ⇒ 09-27 12Z/16Z 的 f8 三列 drank_*_1d 全 0(另: H:disp 序列在 180 锚窗里少 2 点)。
**修法(类形状, 不改状态文件)**: combo_stage 在构造 ms_arr 时, 对窗口内缺成员历史的锚, 用生产者成员规则(shadow_loop_v3.py L676–L701 逐字抽成
`fea171/members_rule.py`)在同一份滚动缓存上现算(fetch 名单 = aux.fetch_syms 减 nc_backfill_residual, 即 A 时刻名单), 具名计数
`MH_RECOMPUTED`; 历史齐全时一行不执行(⇒ C0 字节同一仍须成立)。备选 = 用 T−4h 成员承接(carry-forward)。
判据(冻结):
- **V1 规则复现**: 8 个快照锚 S 各用 S 自己的输入重算 members(S) == members_hist[S] 逐元素相等, 须 8/8; 否则抽出的规则不是生产规则, 本组件作废。
- **V2 事后重算精度**(描述 + 选择规则): 对每个 S 与 T = S−4h…S−24h(6 个滞后), 用 **S 的**输入重算 members(T) 对 members_hist[T];
  报逐元素全等率与平均 Jaccard; 同时报 carry-forward(members_hist[T−4h] 当作 T)对 members_hist[T] 的同两量。
  **选择规则**: 重算的平均 Jaccard ≥ carry-forward ⇒ 用重算; 否则用 carry-forward(并改实现)。
- **M 影响量级**(描述, 不设门): 沙箱重放 A=1790409600, 臂 `mhdrop` = 删 members_hist 中 A−24h 一条(生成标记同步改 sha):
  现码 vs 基线: F10 分数(有限名)Spearman、drank 三列在 A 行是否全 0、发布权重 L1 差与 max|dw|;
  补丁码(含本组件) vs 基线: 同上; 若 V2 在 24h 滞后上逐元素全等, 则补丁码 mhdrop 的发布权重须与基线**逐位相等**(这是一条门)。

## AMENDMENT 3(2026-09-26 19:0xZ, lead 裁定后; 写于 GAP4 任何重放读数之前)
lead 裁定(1)越界 = 承接最近有效状态 + 发布 + HIGH(采纳本包原设计);(2)设计原则写成:**承接最近一份有效状态;一份都没有且回落为零 = 冷启动,冷启动的书绝不发布**,并补测试。
读码+读数发现(本修订的动因,只读): 历史上 08-29 20Z 缺锚后 f10 状态从零爬升(08-30 00Z gross 0.0896 → 04Z 0.170…),combo 在 08-30 04Z 以 gross 0.515 发布 —— 一本部分从零爬升的书已上过实盘。
修法(tree GAP4): prev_state 增 `MIN_STATE_GROSS = 0.4`,gross 低于它的状态判「degenerate」具名拒绝(不作前驱);combo_stage 在 kc/fc 找不到任何有效状态且回落向量 gross < 0.4 时判冷启动:**不写该锚任何 kc/fc 状态、COMBO_LIVE 下 _bail(HIGH 页报)不发布**;f10 单独冷启动只不写 f10 状态(它不进发布的书)。
新增臂(A=1790409600)与判据:
| 臂 | 构造 | 现码 RED 判法 | 补丁码 PASS |
|---|---|---|---|
| cold | 删沙箱内全部 state_H_{kc,fc,f10}_* 与 state/weights/*.npz | 现码写出了 state_H_kc_<A> 或 state_H_fc_<A>(毒化后续锚),或发布了目标 | rc≠0 且无目标;state_H_kc_<A>、state_H_fc_<A>、state_H_f10_<A> 均不存在;run.log 的 COMBO_LIVE ABORT 行含「冷启动拒绝发布」 |
| poison | A−4h 的 kc/fc/f10 状态换成自身 val×0.1(anchor 键正确,模拟从零爬升的状态) | 现码 kc/fc 来源为 own(承接了退化状态)或无目标 | rc 0 已发布;kc/fc/f10 来源 == `own_gap1_rejected1`;GAP_PAGE 行含 `degenerate`;权重与现码 bridge1 参照臂逐位相等 |
另: GAP4 上**全部既有臂按原判据重跑**(C0×3 / T / G1 G2 G6 / gap7 / X1–X3 / M),判官只加上两臂; U 为 16 例(新增 degenerate 例,旧谓词须 RED)。
首锚验收(手册 W6)补一条: 正常锚 kc/fc/f10 来源必须为 `own`;与现码字节相同的性质由 C0 负责。
