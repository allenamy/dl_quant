> **创建:** 2026-09-23 22:4xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(集成代理 C-4) | **状态:** 收据附注,回答 lead 22:3xZ 的问题:播种判词带 3 个未决界值格,F-2 是怎么走过 install → 回滚这一段的 | **作废条件:** `test_nc_rollback_rehearsal.py`(3acb19dd…)、`nc_install.py` 或 `test_nc_install_rehearsal.py` 改动

# F-2 正式演练的路径:它没有经过 install / preflight,3 个未决界值格不在它的路径上

## 1. 直接回答

**(a)、(b) 都不适用。F-2 演练装置 `test_nc_rollback_rehearsal.py` 根本不调用 `nc_install.py`,既不跑 preflight,也不跑 apply。它不读 `SEED_RECEIPT.json`,所以播种判词是 `SEEDED` 还是 `SEEDED_WITH_UNRESOLVED_BOUND_CELLS`,对它没有任何影响。** 我没有加旁路、没有放宽检查、也没有手工补值。

F-2 实际走的是 DESIGN §F-2 定义的路径(`--nc-state` 模式):
1. **(a)** 新生产者(treeNC4)用 `ShadowState` 加载播种出来的 NC 状态,也就是 `seeded/state/`。加载时只校验 generation 签名,不检查界值格。然后用假取数器推进 A1(1790179200)。
2. **(a2)** 新 combo_stage 在 sandbox-exec 下跑 A1。
3. **(a3)** 不开侧车,新生产者加新 combo 连推 A2。
4. **(b)** `nc_downgrade_state.py` 以子进程方式运行(与部署当晚操作员的运行方式相同),把 A1 之后的 NC 状态降级。
5. **(c)** 旧生产者(6080073b)加载降级后的状态,推进 A2。
6. **(d)** 旧 combo 跑 A2。
7. **(e1–e3)** 三个负控。

## 2. 那 3 格在 F-2 路径上的实际作用

3 个未决格是 B2USDT@1789805100、TAKEUSDT@1790147100、B2USDT@1790151900。它们的 f16 ch0 等于裁剪界值 ±0.30,而稀疏表里没有对应的 raw。生产者的 `rr = NC.rr_from_ch0(...)` 在这 3 格上因此取 f32(ch0) = ±0.30,而不是真实的 raw。

- 这只改变这 3 格的收益值,不改变任何代码路径。F-2 考的是回滚机制:加载、推进、降级、旧生产者接续、负控能否拦住。它不对这 3 格的数值做任何断言。
- 部署当晚,这 3 格(以及当时新出现的轴末后界值格)由 A1 的 `nc_deploy_fetch.py` 从交易所取真实 raw。A2 播种判词若仍带未决格就停;A3 preflight 还会独立核一遍「每个加密界值格都在稀疏表里」。两道停点手册都已写。

## 3. install → 回滚这一段在哪里演练

部署手册 R-B 的命令序列是 `nc_downgrade_state.py`,再接 `nc_install.py rollback --downgraded`。这一段由另一个装置 `test_nc_install_rehearsal.py` 演练(手册 §P2)。
- 它的 R2 格按 R-B 的原命令依次运行:在当前状态上跑 `nc_downgrade_state.py`,再跑 `nc_install.py rollback --downgraded`。最后断言:旧生产者加载成功,所有目的地回到基线,NC 专有的状态文件不存在。
- 那个装置里**确有一处旁路**,按 (b) 的要求写明如下:
  - **旁路是什么**:用一个替身实时包(`standin_live_pack.npz`)为播种工具报出的未决界值格提供 raw = ±0.35(取 ch0 的符号,在裁剪界之外)。这个包经播种工具**已支持的输入** `--live-pack` 传入,不改任何工具代码。
  - **影响哪几步**:只影响「播种状态里这些格有没有 raw」这一个判断。它让播种判词变成 `SEEDED`,于是 preflight 的界值格核对能通过。install、降级、回滚的代码路径一行没动;这个 raw 值也不参与这几步的任何断言。
  - **回滚路径是否与部署当晚逐步相同**:相同。`nc_install.py rollback` 与 `nc_downgrade_state.py` 的调用方式与手册 R-A / R-B 逐字一致。区别只在输入:替身模型,即 NEW_S 的 King / F10;机器种子包;替身 raw。
  - 已有收据是 7/7 `MACHINERY_PASS`(`receipts/install_rehearsal_machinery/`),用的是合成机器种子包。
- **本窗口补做**:用**真种子包**(600d760e)、最新快照、替身模型,再跑一次安装演练。替身 raw 只覆盖轴末后的未决格,判词前缀仍是 `MACHINERY_`,因为模型是替身。真部署包出来后按手册 §P2 用真包再跑一次,那一次才是部署前收据。
- 选项 (c) 的更干净做法不可行,原因有两条:
  - 轴末前的已知 raw 已经全部在种子包的稀疏表里(15 格),未决的 3 格都在轴末之后,种子包里没有它们的 raw。
  - 若把 A0 取在轴末(09-19T00Z)以避开轴末后的行,那时的快照早于 09-22,没有 generation 标记,安装装置无法用它搭假 HOME。
  - 在不调交易所的前提下,这 3 格的真实 raw 只能等 data.binance.vision 发布 09-23 的日档后取得。

## 4. F-2 结果(供引用)

- 判词行原文:`NC_ROLLBACK PASS {"a_new_producer_A1": true, "a2_new_combo_A1": true, "b_downgrade": true, "c_old_producer_A2": true, "d_old_combo_A2": true} a3 True {"e1_old_loader_on_nc_state": true, "e2_ema_acc_none": true, "e3_ledger_iv_none": true}`,rc = 0。
- 输入:真种子包 600d760e,在 snap/1790164800 上播种。播种判词 `SEEDED_WITH_UNRESOLVED_BOUND_CELLS`(3 格,见上)。资金费一致 174,758 行,不一致 0,覆盖期内生产缺失 0。
- (a3):`state_H_f10_<A1>` 的 sha 在 (a2) 之后、A2 开跑前、A2 跑完后三次都是 `b73f4f8a…`。h / kc / fc 的来源都是 `own`。A2 的 F10 文件已写出。
- 负控:
  - e1:旧加载器拒绝,报 `invalid generation schema`;
  - e2:旧生产者 TypeError,原因是 acc 为 None;
  - e3:旧生产者 TypeError,原因是 iv 为 None。
