> **创建:** 2026-09-27 03:1xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(fresh) | **状态:** 设计 + 装置(已入库、已在两个真实锚上干跑);**判据形状为提议,由 lead 冻结**;**未安装**,安装步骤见 §6,由 lead 执行 | **作废条件:** 在役 `combo_stage.py`(12a76de8)或在役 `combo_parity_replay.sh`(7fa0881a)改变 ⇒ 装置按设计 fail-closed 停止,需重审

# 设计:组合层改动的前瞻影子 A/B

## 0. 为什么要前瞻

回测对组合层改动基本没有功效:NC 相关读数 pre-2026 的 t 只有 1.6–1.9;King 月度重训族在红控就停了(打乱 King 在 2026 反而 +4.29,`33abbad32`)。前瞻影子用的是**实盘当锚的真实输入**(生产者快照),不经过任何历史重放假设。它的代价是样本增长慢:每天只有 6 个锚。

## 1. 机制:每锚在沙箱里重放一次 combo_stage,在同一进程里多算三本影子书

- **隔离方式与在役平价回放完全相同**:`shadow_ab_replay.sh` 就是在役 `combo_parity_replay.sh`(7fa0881a)加上 22 行差异(`shadow_ab_replay.DIFF.txt`)。仍在 `sandbox-exec` 下运行:断网、不许写沙箱外、凭据不可读、实盘目录不可读写(用内核探针自证,`ISOLATION_OK`)。只读 `~/wide_shadow` 与 `~/dl_quant_live`,只写 `~/shadow_ab` 与 `~/cc_tmp/shadow_ab`。
- **挂钩而不是重写**:把 `ab_hook_block.py` 插进**沙箱副本**的 combo_stage,位置在 ④ 那一行日志之后。影子书直接调用 stage 自己的 `chain` / `exec_reshape` / FTRIM 规则 / 席位 `w3m`,**不重实现任何算术**。
  插入点必须唯一,所需的 18 个名字都必须在插入点之前已绑定(用 AST 检查);否则 UNAVAILABLE,agent 写 STOP。这样在役代码一变就会停下来,不会静默算错。
- **每一臂自带 kc / fc 两个 EMA 状态**,逐锚接力。首锚从实盘状态暖启动(来源写进每锚元数据);EMA α = 0.1,暖启动差异的半衰期约 7 锚。
- **席位对所有臂相同**:席位来自三条腿的纸面收益,而腿收益与书怎么混合无关。

| 臂 | 做什么 | 机理(它回答的问题) |
|---|---|---|
| `LIVE_REPLAY` | 在役 combo 原样重算 | **恒等控制**:必须与实盘 `state/target_combo/<A>.json` 逐位相同(8 位小数、名字集合相同、w3m 6 位相同)。不等 ⇒ 该锚 VOID;连续两锚 VOID ⇒ STOP |
| `NOKING` | King 书里去掉 King 分数,只留资金费;F10 书不动 | King 这个 LGBM 模型在资金费与 F10 之外还有没有增量。回测侧:三信号留一与 King 红控都指向「2026 去掉 King 书更好」 |
| `KHALF` | 模型席位减半(King 与 F10 都经这个席位),重新归一 | 2026 席位已经翻向资金费。问题是:把模型的剂量再减一半,是更好还是更差 |
| `FUNDONLY` | 两本书都只用资金费腿 | 两个模型合起来有没有增量(CF3:资金费扛 86–95%) |

臂数有意克制在 3 个:每多一臂,多重比较就要付代价,见 §4。

## 2. 纸面收益(`shadow_ab_pnl.py`,每锚一行,只追加)

- **价格**:锚 A 的书,用 **A+4h 快照**里生产者自己的 5 分钟收益通道(`nc_contract.rr_from_ch0` + boundary 表),取 (A, A+4h] 的 48 行,逐名按 Π(1+r)−1 复利(生产者口径的求和一并报)。有限行少于 46 的名记 **UNPRICED**,单报其权重份额,**不按 0 处理**。
- **权重**:每一臂 reshape 之后的 combo,按执行器的恒定杠杆缩放:`w_nav = 2.0 · w / Σ|w|`。
- **资金费**:取同一快照里生产者账本 `ledger_tail` 中 A < ft ≤ A+4h 的结算,P&L = −w_nav · Σrate。账本里没有该名,或该名 tail 的最早一行已在 A 之后 ⇒ 记 **FUNDING_UNKNOWN**,单报。
- **成本代理**:3.52 bps × Σ|w_nav(A) − w_nav(A−4h)|(训练器的成本系数,同 dlarch `aab04e8b9`)。没有上一锚的书 ⇒ 成本与净额记「未知」,不记 0。
- **不建模**:入场滞后(执行器约在 N+24 分钟交易)、钳位 / 剔除 / 场所上限、成交、M3 beta 覆盖(M3 仍是 shadow)。
- **账本**:`~/shadow_ab/ledger.jsonl`,每行带 `prev_line_sha256` 形成链,锚严格递增。每轮先跑 `shadow_ab_verify_ledger.py`,链断 ⇒ STOP。

## 3. 已做的验证

| 项 | 结果 |
|---|---|
| 单元 / 红测 `tests_shadow_ab.py` | **18/18**:价格复利已知答案(float32 通道;第一跑是我的期望值用了 0.001 而红,改正的是期望值)、46/45 行门、资金费窗 (A, A+4h] 两端、覆盖与缺失标记、成本、无上一锚 ⇒ 未知、杠杆缩放、账本链(篡改一行 ⇒ BROKEN)、挂钩插入的唯一性与缺名拒绝、恒等控制差 1e-8 ⇒ VOID |
| **真实锚干跑**(只读实盘,写 `~/shadow_ab_dryrun`) | 04Z(1790452800)与 08Z(1790467200)两锚:**恒等控制 PASS**(318 / 319 名,0 值不符,w3m 相同);08Z 各臂状态来源为 `own`(接力成功);04Z 用 08Z 快照定价,48 行、0 未定价、0 资金费未知。每锚约 41 秒 CPU。收据在 `receipts/dryrun_2026-09-27/` |

## 4. 判据形状(提议;**由 lead 冻结**,冻结前我不读任何影子读数)

- **统计量**:每臂对 `LIVE_REPLAY` 的逐锚净额差 d = net_arm − net_live(NAV 口径)。按日汇总为 bps/日,D̄ = 日均值。
- **SE**:7 日块 MBB(B = 10,000),块长覆盖周内结构。
- **判定**:三臂各自与在役比,按 Bonferroni 把双侧 α 设为 0.05/3(z = 2.39)。
  - `BETTER`:D̄ − 2.39·SE > 0,且前后两半同号;
  - `WORSE`:D̄ + 2.39·SE < 0;
  - 其余为 `NO_DETECTABLE_DIFFERENCE`。
  - 任一臂 VOID / UNDEFINED 锚超过 10% ⇒ 该臂 `UNDECIDED`。
- **固定时长,不偷看**:
  - 前 18 个锚(3 天)是暖启动收敛期,不计入。
  - 运行期间只报**合池的离散度与覆盖**(盲态,同记忆 `blind_state…`),不报各臂均值。唯一的中途动作是恒等控制失败时停机。
- **最少运行时长**:12 周(504 锚),另加一个**只按离散度**的延长规则:第 2 周末用实测的配对 σ_d 重算 12 周的 MDE;若 MDE > 10 bps/日,延长到 26 周。这一步只看 σ,不看均值。
- **必报,不作门**:税前、κ ∈ {0, 3.52, 7.04} 的成本敏感性、价格与资金费拆分、换手、差值累计曲线的最大回撤、未定价与资金费未知的份额、状态来源。
- **从这里到换装**:BETTER 只是「可以呈给用户」;换装仍须用户裁定并走部署协议。

## 5. 样本算术(能分辨多大的效应)

σ 的唯一在案来源是 R25-04 的实盘反事实:`cf_legs.py` 的逐锚书 P&L,两段共 40 锚,都在 09-17..09-24 的主回撤期,波动偏高。

| 臂(近似对应) | 逐锚 σ(USDT) | 换成 NAV bps(NAV ≈ 109,300,`42b30528b`:2,405 USDT = 2.20%) | 滞后 1 自相关 |
|---|---|---|---|
| no_king ≈ `NOKING` | 92.6 | 8.5 / 锚 | +0.10 |
| no_f10 | 53.8 | 4.9 / 锚 | −0.22 |
| no_fund(与 `FUNDONLY` 方向相反,只作上界参考) | 601.2 | 55 / 锚 | −0.13 |

`NOKING`:σ_日 ≈ 8.5 × √6 × 1.08 ≈ **22.5 bps/日**。MDE(双侧 α = 0.05/3,功效 80%,系数 2.39 + 0.84 = 3.23)= 3.23 · σ_日 / √天数:

| 运行 | 4 周 | 8 周 | **12 周** | 26 周 | 52 周 |
|---|---|---|---|---|---|
| MDE(bps/日,`NOKING`) | 13.7 | 9.7 | **7.9** | 5.4 | 3.8 |

**直说**:12 周只能分辨约 8 bps/日的效应。在案最大的相关回测读数是打乱 King 的 2026 段 +4.29,大约只有它的一半(引擎 dbar 与这里的 NAV 口径杠杆不完全相同,只能作量级比较)。所以:
- 12 周多半得到 `NO_DETECTABLE_DIFFERENCE`,除非效应比回测大得多;
- 26 周约 5.4,52 周约 3.8;
- 这个 σ 取自回撤期,平常时期可能更小,第 2 周的离散度检查就是为这个设的。
`KHALF` 与 `FUNDONLY` 没有在案的 σ,第 2 周实测后按同一公式补表。`FUNDONLY` 的 σ 很可能远大于 `NOKING`(它移走的是两个模型),可分辨的效应也会相应变大。

## 6. 执行者与安装(**由 lead 安装**,我不装)

执行者:launchd agent `com.hsy.shadowab`,每 300 秒一次,放在 `~/shadow_ab`(**不在 Desktop**,避开 launchd 的 TCC 墙)。
- 心跳:`~/shadow_ab/HEARTBEAT.json`,每轮原子写,含 utc / pid / 状态 / 最后重放锚 / 最后定价锚。
- 终态标记:`~/shadow_ab/STOP`(fail-closed,带原因)与 `~/shadow_ab/DONE`(到 END_ANCHOR)。两者 agent 都不会删。
- 只在 [N+1:00, N+3:40] 窗内工作;只处理在役平价 agent 已出 `PARITY.json` 的快照,所以不会与它同时占用沙箱。
- STOP 条件:在役 combo_stage 变了(挂钩点或名字找不到)/ 恒等控制连续两锚失败 / 账本链断 / 磁盘剩余 < 2 GB / P&L 装置异常。

**安装步骤**(lead 执行):
1. `mkdir -p ~/shadow_ab/devices ~/shadow_ab/logs`
2. 从仓库 `multi_asset/exports/research/shadow_ab_2026-09-27/devices/` 拷入:`shadow_ab_agent.sh shadow_ab_replay.sh shadow_ab_insert_hook.py ab_hook_block.py shadow_ab_collect.py shadow_ab_pnl.py shadow_ab_verify_ledger.py`,并对照本提交里的 sha 逐一核对。
3. 写 `~/shadow_ab/config.sh`(模板 `config.sh.template`):`START_ANCHOR` = 安装后的第一个 4h 锚;`END_ANCHOR` = START + 12 周 × 7 × 6 × 14400(按 §4 冻结的时长)。
4. 先手动跑一次:`bash ~/shadow_ab/devices/shadow_ab_agent.sh`,确认 `HEARTBEAT.json` 出现;窗外时状态应为 `IDLE_OUTSIDE_WINDOW`。
5. 安装 launchd:`cp com.hsy.shadowab.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.hsy.shadowab.plist`。
6. 登记 `INFLIGHT_REGISTRY`,建议条目:`{"id":"fresh_shadow_ab","executor":"launchd com.hsy.shadowab","heartbeat":"~/shadow_ab/HEARTBEAT.json","terminal":["~/shadow_ab/STOP","~/shadow_ab/DONE"],"log":"~/shadow_ab/logs/agent.log","ledger":"~/shadow_ab/ledger.jsonl","owner":"fresh"}`。巡检每轮看:心跳年龄 < 15 分钟;不存在 STOP;窗内每锚一行账本。
7. 回滚:`launchctl unload …/com.hsy.shadowab.plist`。影子不写任何实盘文件,所以无需别的回滚。

## 7. 限定

- 纸面书没有执行层(钳位、上限、成交、滞后);三臂与在役共享这一偏差,差值里会部分抵消,但不会全部抵消,因为非线性。
- 在役一旦发布新版 combo_stage,挂钩会 fail-closed 停止。继续就意味着对新版本重新冻结,之前的读数不能与之后的拼接。
- 快照有保留期:agent 停得太久,中间的锚会永久缺失,臂状态会重新暖启动(写进来源字段,并计入 §4 的 VOID/UNDEFINED 比例)。
