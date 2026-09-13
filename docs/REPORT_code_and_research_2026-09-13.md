> **创建:** 2026-09-13 00:2xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 交独立研究员复审(用户字 09-13「这三件完整代码提交报告给我, 包括优化实验方向的改动」)| **作废条件:** 表中任一 diff sha / 提交 sha 改变须做差异复核; W8 尺子第七次重标定落定后本文 §1.5 与 W6 (a)(b) 的 diff sha 必须更新

# 完整代码提交报告 —— 执行器三件修复 + 研究侧(优化实验方向)改动

**读法**: 每件给「为什么改 / 改了哪几行 / 怎么证明它对 / 旧码在新测试下红 / 收据路径 / 复跑命令」。**全部未部署**: 实盘运行树 `~/dl_quant_live` HEAD 仍 `918559f`, 代码与之逐字节相同; 生产者 `~/wide_shadow` 自 09-05 未触。研究仓分支 `research/book-uplift-2026-09-11`。时间 UTC。

---

## §0 一页纸

| # | 件 | 产物 | 状态 | 阻塞 |
|---|---|---|---|---|
| 1 | **W6 (a)(b)** 事故 E-0912-A 根因修复 | `docs/receipts/w6_reduce_only_clamp_ab.diff` sha `cdf37046…` | 复审通过, **待尺子第七次重标定后落地** | 用户字 |
| 2 | **W6 (c)** 看门狗比例响应 | `docs/receipts/w6_proportional_response_c.diff` sha `9f137598…` | 代码在, **默认 OFF**(研究员 C1 反例) | 裁定 R-14 |
| 3 | **W2** 读者三桶 + 完整性 | `docs/receipts/w2_readers_three_bucket.diff` sha `3794ecfd…` | 复审通过, 待落地 | 用户字 |
| 4 | **W1** #55 告警合同 | `docs/receipts/w1_ic_monitor_contract.diff` sha `86324465…` | 复审通过, 待落地 | 用户字 |
| 5 | 研究链装置(W3/W4/W7/F9/B-R1..R5) | 研究仓 `15941da7` + `942b3e73` | 已入库, 自检 328+19 全绿 | 十月合同批准 = 用户字 |
| 6 | 平价装置(线上代码历史回放) | `parity_replay_2026-09-12/` | 前向 3/3 逐位精确; 历史 41 锚 FAIL 保留 | 材料性测量中(R22) |
| 7 | 口径/统计勘误 | 逐年表 + G2-A + AMENDMENT 3 | 已改正入库 | — |

---

## §1 执行器第一件: W6 (a)(b) —— 事故 E-0912-A 的根因修复

### 1.1 为什么改(事实链, 每环有收据)
2026-09-12 12:47:37Z 看门狗触发, 255 张 IOC reduce-only 平掉整本书(Σ 235,382.55 USDT, 滑点 5.39 bps = 126.90 USDT, 另 5 bps 假设费 117.69 USDT **未实测**)。链条:
1. 12Z 锚 MEMEUSDT / POPCATUSDT `target_w=0`(全退出)⇒ 按设计发 **reduceOnly** GTX 卖单。
2. 数量 = `round_qty(delta_notional/mid)`, delta 的持仓部分来自 **mark** ⇒ MEME 1,933,986 张 vs 实际持仓 **1,933,692**(多 294 = 0.015%); POPCAT 10,435 vs 10,434。
3. 交易所把 reduceOnly 单**截到持仓量**: 回执 `origQty` = 持仓, 随后全部成交(子成交之和 == origQty), 读回 0。
4. b681ca5 第 12 轮的 `submit_identity_mismatch`(容差 1e-6)把「回执 origQty ≠ 我方数量」判为 `inconsistent` ⇒ `filled_amount_unknown` ⇒ `reconcile` 「矛盾不可当已知」⇒ `execution_of_unknown_size` ×2 ⇒ 看门狗 §4-5b(状态门 M=1)+ §4-7(读同一次对账)⇒ 阶梯 停开仓 → 全平 → 告警。
5. 两名合计 Σ|intended| **1,524 USDT = gross 0.65%**, 响应是平 **100%** 的书。历史 `differs from ours` 今天之前 **0 行**。

**独立研究员复核结论(563e3470 `incident/RESULT.md` §1)**: 事实链成立, 是合法场所缩量被记成不可测导致的保护性平仓, 不是两名真有未平余额。

### 1.2 改了什么(12 个代码/测试文件, +1400 / −40; 另 13 个 12Z 真日夹具文件)
| 文件 | 改动 | 行 |
|---|---|---|
| `live/binance_broker.py` | 身份核对加**第四态 `clamped`**: `order.reduce_only ∧ resp.reduceOnly ∧ 0 < origQty < 我方数量 ∧ 同侧` ⇒ 不是矛盾, 记 `clamped{ours, venue, why}`, `orig_qty` 取回执值(= 场所接受的请求容量 **Qv**)。**不放宽**: origQty > 我方、方向错、非 reduceOnly 的差 仍是矛盾; 1e-6 容差**未动** | +84 / −12 |
| `live/binance_executor.py` | `plan()`: `target==0 ∧ 持仓≠0` ⇒ 数量 = **读回的持仓张数**(`venue_position_qty`), 不再走 notional/mid; 无 qty 列时退回旧路径并记 `qty_source` | +83 / −8 |
| `live/reconcile.py` | 从**账本条目内容**重推持久化的「矛盾」(仅当满足 clamp 规则: 身份-origQty 型 ∧ 同侧 ∧ \|C\| ≤ \|Q\| ∧ Σ 子成交 == \|C\|), 其余矛盾种类照旧不可量化 | +115 / −1 |
| `scheduler/anchor_loop.py` | 把读回的持仓张数交给 `plan`(与 notional 同一次 account snapshot) | +23 / −2 |
| `live/venue_fills.py`, `ops/backfill_fills.py` | **平仓费根因**: 平仓单 client id `F<utc>-SYM-n` 无 `<rid>-` 前缀 ⇒ B26b 重建 0 腿 ⇒ 255 行费全 None。改为按 client id 精确 join, 平仓腿单列, fills 行带 commission(只追加, 不改订单行) | +71 / −17 |
| `ops/rejudge_ledger_rows.py` **新** | **只读**重判工具: 读 12Z 两行, 用原始证据(POST 回执 origQty、子成交、前后读回)套 clamp 规则, 写收据; **不改账本、不翻 state** | +236 |
| `live/tests_reduce_only_clamp.py` **新** | 75 格(真 12Z 行正控 + 8 负控 + T7 端到端 + T9 看门狗) | +554 |
| `live/tests_flatten_fee_backfill.py` **新** | 13 格 | +223 |
| `live/tests_rehearsal_anchor.py`, `ops/gate_coverage.py`, `run_acceptance.sh` | 登记新套件与新工具 | +11 |

### 1.3 怎么证明它对
- **真实身份记录正控**: 用两份**原始 POST 回执**重跑冻结的新旧 `submit_identity_mismatch`: 旧版两条拒绝, 新版两条接受并记 clamped; 8 个负控(超量/错 side/非 reduceOnly/外来 cid)仍拒绝。
- **计划正控**: 用冻结 `plan` 与确定性 lot 桩, 全退出变成 MEME −1,933,692 / POPCAT −10,434, 来源 `venue_position_qty`。
- **端到端 T7**: 12Z 真账本三文件经 `reconcile` ⇒ 新码两名 `known`、异常 **0**; 旧码 **2 条 `execution_of_unknown_size`**(= 事故复现)。
- **T9 看门狗**: 真 12Z 日, 新码 **cond5b CLEAN / §4-7 CLEAN**; 旧码 **ANOMALOUS 2 + DRIFT**(收据 `w6_resume_gate_replica_{new,old}.log`, 43 日复现)。
- **只读重判收据** `docs/receipts/w6_rejudge_20260912_receipt.json`: 两行, 每行 6/6 交叉核对为真(回执 origQty 字符串相等、reduceOnly、Qv<Qs、子成交在 fills 中、Σ == C、读回后 == 读回前 + C)。
- **旧码红**: `w6_oldcode_red.log`(918559f 上 32/70 rc=1)、`w6_oldcode_red_backfill.log`(4/11 rc=1), 各自以 Traceback 指名旧树缺什么。
- **电池 #7**(最终链 + 真账本副本): **132/135**, 红三套 `tests_env_loading` / `tests_disposition_matrix` / `tests_alarm_digest` 与**纯 918559f 同账本对照**逐字相同; 对照多出的 `tests_break_split_wiring` 红被本次重判修好(非偶发)。
- **研究员探针重跑** exit 0(`w6_review_probe_rerun.log`)。

### 1.4 命名纪律(研究员要求, 已落)
Qs 发送容量 / **Qv 场所接受的请求容量** / L 已成交下界 / F 已证最终量 四者分开; 代码与收据**不**把 Qv 叫「当前持仓真值」(两次恰等只是观察)。T7 里由 POST + 子成交重建的 allOrders 终态行标注为 **SYNTHETIC**。

### 1.5 仍开(诚实)
1. **尺子第七次重标定进行中(W8)**: 叠加落地电池里 `tests_disposition_matrix` 因**今日账本事实**红 —— 12Z 锚的两行被尺子计为稳态锚的非自愿缺口(1,524U), 且 12Z 既非稳态锚也非停机锚(区间内含一次全平)。按用户规则**按事实新增类, 不放宽**: 有据重判行不计非自愿缺口 + 新类 TRIP-FLATTENED(承重断言 255 行 / Σ 235,382.55U)+ 新类 HALTED-NO-SUBMIT(16Z/20Z: 243 blocked_by_halt + 2 小额, 零提交零成交)。**完成后 W6 (a)(b) 的 diff sha 会变**, 届时补发。
2. **平仓费真回填未跑**(需凭据, 运维步): `LIVE_MODE=LIVE python3 ops/backfill_fills.py --day 20260912 [--apply]`。当前 255 行费仍诚实显示未测。
3. 恢复交易前的 `resume_from_trip.sh` 自检项与剩余阻塞见 DESIGN §4.5。

---

## §2 执行器第二件: W6 (c) —— 看门狗比例响应(**默认 OFF, 不随本批落地**)

**内容**: 最新对账锚的「未知大小」异常若 场所记录自洽 ∧ Σ\|intended\| ≤ gross 2% ∧ ≤5 名 ⇒ 停开仓 + HIGH + 只处置那几名; 否则现行全书阶梯。7 文件 +859 / −6, 测试 50 格。
**为什么不开**: 研究员 C1 用**完整 reconcile 生产路径**给出反例 —— 原「自洽」谓词不核 `request.inconsistent` / `row.ledger_inconsistent`, 不核 `row.known == Σ 有符号请求 C`, 不核 gross 有限, 于是带身份矛盾的账本也能被判自洽并降级为局部响应。**已按 C1 重写谓词并加三格红→绿**, C2 符号边界(held>0 而差为负会构造 BUY reduceOnly)加单测, C3 措辞改为「事故后制定的政策阈值」(不再声称先于看数冻结)。**但默认仍 False**, 等 R-14 裁定。

---

## §3 执行器第三件: W2 —— 三桶读者与完整性

### 3.1 为什么改
三个读者(日报 / 首锚屏 / 评分器)把「场所锁住的量」「费未知的行」混进滑点与成本统计; `None` 被当 0; 非 USDT 费被当 USDT 加总。研究员前轮(0dfc0d87)与本轮(563e3470 W2-R1/R2)各给了可复现反例。

### 3.2 改了什么(8 文件 +1298 / −89)
- `live/cost_buckets.py` **新** (+194): 单一规则来源, 逐字抄 `anchor_loop.neutrality_price` 的 `_pos`/`_fee` 并逐键钉住; 三桶 = 已测 / 费未知 / 未定价; `known_fee` 对 None、非有限、非 USDT 未换算一律判未知; 新增**桶派生的 `measurement_complete`**。
- `ops/score_post_fix.py` (+55/−5): **E6 判据改用桶派生的完整性**, 同时保留 m1 自己的位为 `m1_measurement_complete` 并标 `completeness_disagrees_with_m1`; 平仓块另记 `protective_flatten_buckets` / `fee_known_by_buckets`。
- `ops/daily_summary.py` (+208/−32): 残差与轮换增量**要求收入读取两端 complete**(截断 ⇒ None + 「已读部分」); 「下界」措辞全删(收入是带符号的, 局部和不保证是下界); `realised_pnl` NaN/inf ⇒ 不可观测; 覆盖率保持精确比, 只在显示时向下取整。
- `ops/first_anchor_review.py` (+69/−38): 走新桶, 打印「measurement complete: yes/NO」。
- 两个测试文件 +765: 64 格 + 42 格; 真账本依赖格改**显式 SKIP**(克隆无账本时 58+6 SKIP / 39+3 SKIP), 表格格改按工具自报 `covered: N` **精确断言**(比原来的 ≥3 代理更强)。

### 3.3 证明与仍开
旧读者在新测试下红(`prereview_readers_tests_*_RED.log`, 8 条 FAIL 后 rc 1); 克隆电池 **133 套 132 绿**(红 = 无 `.env`)。**仍开(记为裁定项 R-12b)**: `live/pilot_metrics.py` 在 `check_metrics_freeze` 冻结窗内(sha `5ac7b16d`), 它自身的两个「已测」缺陷(fee=NaN ⇒ complete=True; 平仓行未换算费被计为已测)**未改**, 只被记录并由消费者绕开 —— 改冻结文件 = 重新认证冻结窗 + 预注册。

---

## §4 执行器第四件: W1 —— #55 Telegram IC 告警合同

### 4.1 为什么改
该告警测的是**书级实现 rank-IC**(场所实持仓名义排序 vs 下锚场所隐含价收益排序), 但页面从不说明对象, 也不说阈值是在 **α=0.05 / band=0.002 的离线书**上标定的(在役是 α=0.1 / band=0.00025); 恢复无通知; 窗被平仓掏空时照常判级。

### 4.2 改了什么(3 文件 +1164 / −75; 统计量/阈值/WINDOW_START **逐字未动**)
- 每页与持久化 state 带 **OBJECT 行**(明示不是模型分数 IC、不是扣费净收益)与**标定身份行**。
- **恢复按触发窗口与事件**: 越线页开一个 event 并记下是哪个窗触发; RECOVERED 仅当**每个触发窗都重新可判且脱线**; partial-OK 既不恢复也不降级, 页面只说「可判窗口未越线, 其余窗口未判」。
- **冷却限在同一事件内**: 恢复后同级复发 = 新事件, 立即推送(这比把 24h 改 23h 更对症)。
- **新鲜度门**: 前沿 = floor((now−5h)/4h)·4h, 缺 >2(r24) / >4(r48) ⇒ 该窗 INCOMPLETE 不判, 每 24h 一次 INFO 列缺失锚; <24 行也做普查(空/冻结账本不再静默 OK)。
- **只读入口**: `allow_abbrev=False` 且**先解析 argv 再 import 任何凭据模块**(研究员发现 `--che` 缩写会先触发 envfile import)。
- 新增只追加账本 `state/live/ic_monitor_evals.jsonl`, 并输出 observed latest anchor 与 expected frontier 两个字段(供 W5)。
- `LEGACY_TRIGGER_WINDOWS = ["r48"]`: 依据 09-09 与 09-10 两次 DECIDE 的实测值(r24 −0.03483 / −0.02705 都在 DECIDE 线 −0.04425 之上; r48 −0.02373 / −0.02667 都在 R48_P1 −0.01656 之下)。

### 4.3 证明与后果
76 格全绿; **两个旧基线都红**(918559f 与研究员冻结的中间版 8b2c218c); 陷阱测试证明 `--check` / `--dry` / `--backfill --check` 零 envfile/Telegram import、零 socket、零写盘, `--che` 现在 exit 2。**行为后果(必须让用户知道)**: 按新鲜度门, 09-07..09-12 五次判级**全部 INCOMPLETE**(窗被 09-06/09-09 平仓掏空), 且以真实 state 投影, 最早可能的 RECOVERED 是 **09-16 01:30Z** 那次运行(此前 r48 缺失 >4)。**INCOMPLETE 不是 alpha 恢复的证据**。阈值按在役形态重标**不在本次范围**(等平价 Phase 2)。

---

## §5 研究侧改动(优化实验方向)

### 5.1 十月重训链: 从「不可照抄」到「一条驱动 + 一份月合同」
- `chain_v4_monthly.sh`(11 阶段单驱动)+ **46 键月合同**(全部必填且**必须是文件里的 KEY= 行**, 先 unset 再 source, 父环境不可污染)+ 空根负控。
- 每阶段 **dispatch 前**检验前置票据(绑本月合同 sha 与本月根): refit ← STEP1 + legs + MERGE_DONE×seed + deps 身份; arms ← STEP2 + BUNDLE_DONE + refit 侧车(fix7); judge ← DEV_V4_DONE + ARMS_DONE + END rc=0; export ← JUDGE_V4_DONE。**依赖图, 不是文件顺序**(研究员 B-R1)。
- 数据阶段五个子进程 `env -i` + 白名单, CLIP 显式清空 RAW 补丁(B-R3)。
- 五个旧链脚本加 `V4_LEGACY_OK=1` 物理门, 裸调 rc 64(R5: 不再只靠横幅)。
- **十月数据门源码** `v4_gate_step1_m.py` / `v4_gate_step2_m.py`: 由冻结门经白名单行生成(只改路径定位与滚动参照), **预注册先于任何运行**; pod2 九月正控 STEP1 **78 判决字段全等**(字面 FAIL 与归档一致)、STEP2 **31 全等** + 唯一预注册新字段 `tail_quality`。`NONE` 模式绑 builder 身份三方相等; 新尾质量门(成员 ≥1、有限比 ≥0.90, 地板先入 AMENDMENT)。
- **需要用户一句话**: 把两个新门的 sha 加进资格合同的 approved 列表, 否则 preflight 按设计拒绝。

### 5.2 资格与判官
- 出口门底 **11 → 28 名**(= v2 出口门真收据逐名), 漏任一项即不合格。
- **F9**: 判官自绑 `eligibility_contract` = 它自己读的那份合同(此前由调用方给路径, 只验「那文件没变」)。
- **B-R2**: 判官现在把收据**记录过**的条件依赖(femat / signal_receipt 等)也自行定位并验证 —— 调用方漏报不再可以蒙混。前身快照 `judge_v4.r5_f6850dc3.py` 留档并在新套件里被证明会接受反例(旧码红)。
- 链自检 151 → **328**(+ 新套件 19), 我本人复跑全绿。

### 5.3 平价装置: 第一台能回放「部署书」的仪器
- 装置由**生产者源码经一次性字符串替换**派生(研究员逐字节复现了派生关系)。
- **前向(新)**: 以真实生产者状态快照为种子前推一锚, 12Z / 16Z / 20Z **三次全部逐位精确**(king L∞ 0.0, `target_combo` / `target_live` L∞ 0.0)。
- **缓存回填探针**: 三对快照(08Z→12Z / 12Z→16Z / 16Z→20Z)**全部 0/0/0**(11,472 行 × 829 名)。
- **历史**: 自 09-05 链式 41 锚 **0/41** 过 1e-6 门(中位 1.05e-5, 最大 1.13e-4, 14 名)—— **FAIL 保留, 不被近期成功注销**。
- **机理裁定(按研究员措辞更正)**: 支持「链起点状态差 / 历史输入差」候选, **未排除** 09-05→09-11 窗内的回填、当前 rolling 左边界、mini 特征历史长度、辅助文件代际。
- **已完成(R22, 2026-09-13 00:3xZ, 判据冻结先于数字; `docs/PREREG_parity_materiality_2026-09-13.md` + `RESULT_materiality_2026-09-13.md`)**: **经济材料性裁定 = FIT**。41 锚上 replay 与在役书的 Δg(同一真实收益向量, 单位 gross): **`target_live`(执行器真读的那本) mean −0.000334 bps/锚, CI95 [−0.00212, +0.00120], U_mean = |mean|+半宽 = **0.00199**; `target_combo` U_mean **0.00331**。冻结规则是「U_mean ≤ 目标效应/3」⇒ 装置对 **≥0.006 bps/锚** 的效应可用, **覆盖候选关心的 0.02–0.6 全区间**(低端仍有 3.3× 余量), 系统偏差比判官自身分辨率 0.23 bps 小 **115×**; 加 3.52 / 6.64 bps 每单位换手的成本通道后裁定不变。**正控**: 三个快照种子锚 Δw 与 Δg **逐位 0.0**, 并加**红能力门**(注入扰动与闭式解对到 2e-12 —— 「Δg=0」也可能只是点积坏了)。残差是**截面**的不是尺度的(β−1 ≤ 1.3e-4, Spearman ρ ≥ 0.99998, 逐锚名集合相同)。**更正一处我先前的说法**: 「14 名」属 `target_combo` 对; **部署文件 `target_live` 只有 4 名**(BULLA/GPS/POL/PROM)—— 两文件按设计本就不同: `combo_stage.py` 把 `combo_raw` **全精度**写 `target_live`(中性化由执行器 `verify_reshape_anchor` 做), 把 `exec_reshape(combo_raw)` 四舍五入到 8dp 写 `target_combo`(归档/诊断)。**未验证**: 正典 y4s = Π(1+r)−1 的未裁剪版在 pod2(本轮只读约束未取; 差已界住: 885,600 格 1 格触裁剪且该名 Δw=0 未持仓, Σ-vs-Π ≤ 3.6e-4 bps)、跨 regime(只有一周一 regime)、单锚适用性(41 锚里 1 锚超 0.02)。**意义: 这是第一次有证据表明研究侧回放可以替部署书度量策略改动** —— 此前所有候选判决都缺这把尺子。**不推出**: 历史链逐位、机理识别、任何候选获准。
- **原计划(已被上条取代)**: 经济材料性 —— 判据先冻结再算数: 该残差换算成 g(bps/锚)后, 与我们关心的 0.02–0.6 bps 量级效应相比是否可忽略。这直接决定**后续所有策略实验是否有可信的尺子**; 若判「不适用」, 则必须先把历史链做到逐位, 再谈任何候选。

### 5.4 口径与统计勘误(全部由研究员指出, 全部接受)
| 项 | 原 | 正 |
|---|---|---|
| 逐年表窗口 | 「至 08-30」(n=9139) | 实际读到 **08-31 00Z**; v4 原钉 W_ALPHA 上界 08-30 20Z(n=**9138**, Sharpe **1.29122**) |
| 2023 年回撤 | 算术 gross DD ×2 ≈ 33.5% NAV | 固定 2 倍**复利** NAV maxDD **28.92%**(误差 4.61pp) |
| 全史回撤 | 「≥44%(下界)」 | **撤回**: 43.97% 是**点读数**, 不是统计下界 |
| SE 表述 | 「收据用 block bootstrap SE, 我用 std」 | **错误对立, 撤回**: Sharpe 点估计都是 mean/std; 收据的 `sharpe_se` 是 √(2190/n), `se_boot` 是 **g 均值**的日块自举 |
| 区间 | — | 新增探索性 UTC 日块自举 Sharpe CI95: 全窗 **[0.32, 2.28]**, 2026 **[2.21, 6.79]** ⇒ **2026 的 4.53 也不能说 CI 下界显著 >3** |
| G2-A | 「PASS」 | **原门(829 名 / ≥40 天)NOT PASSED AS WRITTEN**(实 28.66 天, 829 轴支持差 15.5–27.9%); 保留具名子门 **G2-A′「当前 live450 精确通道平价」PASS** |
| 候选表述 | 「零录取 = 无一过 (A)」 | **「零获准换装」**: 历史某窗显著 / 确认性证据 / 风险成本接受域 / 正式资格是四件事 |
| 正控目录 | V1/V8/V11/V9 四处 | 逐条更正(V8、V11 我写错; V1 过度概括; V9 混了三种身份), 并改为「官方承诺 / 真实观察 / 我方政策」三列分列 |

### 5.5 事故 E-0912-B(研究基建, 无实盘影响)
我方自检里一格突变测试在 pod2 上以**默认路径**跑了真导出器, 改写了研究 bundle 的 `slow2026.txt`(本机因缺依赖早死所以盲)。已: 从未动过的 09-09 归档包按 sha 先验后恢复、8 文件逐一对清单、**在恢复后的 bundle 上重跑 v2 出口门 PASS + REQUIRE_OK**(资格由新收据重建, 不是「字节恢复」); 导出器改为**无 `BUNDLE_OUT` 即拒**; 自检加 `run_sandboxed()` 与**静态格禁止裸调真写者**。入错题册 E-0912-B。

---

## §6 请研究员复核什么(按优先级)

1. **W6 (a)(b) 的 clamp 规则边界**: 是否还有第三种「场所改数量」的文档化行为会再次触发身份核对(见 `docs/CATALOGUE_venue_behaviours_positive_controls_2026-09-12.md` V1–V14, 尤其 V11 自成交防护的完整竞争链)。
2. **reconcile 的重判谓词**: 「仅限有据 clamp 型」的判定是否可被构造绕过(你上一轮的 C1 三格已并入测试, 请找第四格)。
3. **尺子第七次重标定**(W8, 进行中): 新增两类是否属于「按事实分类」而非放宽; 承重断言是否真能红。
4. **W1 的事件/触发窗语义**: 恢复、冷却、升级三者的状态机是否还有你能构造的漏报/误报序列。
5. **W2 的 R-12b**: 冻结的 `pilot_metrics` 与消费者完整性分叉, 是否接受「消费者绕开 + 记录分歧」作为过渡。
6. **十月门**: `tail_quality` 地板 0.90 与 `NONE` 的 builder 绑定是否足够; 合同批准对象是 `v4_gate_step2_m.py` **0fe5ec55**(不是早先的 455e3df4)。
7. **平价材料性(R22, 已出数)**: 判据「U_mean = \|mean Δg\| + CI 半宽 ≤ 目标效应/3」在 `PREREG_parity_materiality_2026-09-13.md`(sha `eb9f5e41…`)里**先于数字冻结**, 装置自身断言该 sha。请审: (i) 规则本身(/3 的理由: 三分之一的偏差翻不了效应的号; 判官分辨率 0.23 bps); (ii) r 用生产者结算式(±0.30 裁剪的 Σ)而非 pod2 上的正典 y4s —— 我界住了差(≤3.6e-4 bps)但没取正典, 是否接受; (iii) 正控的红能力门设计; (iv) 「单锚不适用」这一限制是否应写进后续任何用该装置的预注册。

## §7 复跑(全部只读)

```bash
# 执行器: 在隔离克隆上叠加三件并跑全电池(真 state 只读拷入, 永不拷 .env)
git clone ~/dl_quant_live /tmp/land && cd /tmp/land && git checkout 918559f
git apply docs/receipts/w6_reduce_only_clamp_ab.diff    # 再 w2_…diff, w1_…diff
cp -R ~/dl_quant_live/state ./state && bash run_acceptance.sh
# 研究链自检(约 6 分钟)
cd multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09
/usr/bin/python3 tests_pipeline_gates.py && /usr/bin/python3 tests_judge_dynamic_deps.py
/usr/bin/python3 make_sha_manifest.py
# 平价收据自校验
cd multi_asset/exports/research/parity_replay_2026-09-12/receipts && shasum -c SHA256SUMS.txt
```

**本报告未声称**: 任何候选获准换装; 十月全链在真数据上跑通; 平仓费已实测; 恢复交易的安全性由本文建立(那要 W8 落定 + 用户字 + 首锚验收 + `resume_from_trip.sh`)。
