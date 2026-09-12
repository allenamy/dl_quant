> **创建:** 2026-09-12 13:3xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 交独立研究员复审(用户字 13:3xZ「把所有的更新和待实验全部总结…一定要严谨」); 本文随 W6/W7 交付**原地更新**(同路径, 新增 §11 追记) | **作废条件:** 研究员复审结论入 STATE 后转历史

# HANDOFF: 2026-09-12 全部更新与待实验(含事故 E-0912-A)—— 请独立研究员复审

**读法**: 每条给「落在哪(commit/sha)/收据/请复核什么/我方已知的弱点」。所有 commit 在研究仓分支 `research/book-uplift-2026-09-11`(本文写时 HEAD `490e3398`)或执行器仓 `~/dl_quant_live`(origin/main = 运行树 = **918559f**, 运行时代码 = b681ca5)。时间全部 UTC。**我方今日错误清单在 §9, 请优先看。**

## §0 一页纸(按复审优先级)
| 优先 | 件 | 状态 | 关键收据 |
|---|---|---|---|
| 1 | **E-0912-A 假阳性全书平仓**(12:47:37Z) | 事实链七条已入库; 修复 W6 克隆中; 用户裁定 R-13=A(彻底修复不回滚) | `docs/ERROR_LEDGER_2026-08-20.md` E-0912-A; `docs/DESIGN_reduce_only_clamp_identity_2026-09-12.md`; journal 12Z 两节 |
| 2 | 执行器今日三次落地(b681ca5 部署 / 77d9baf / 918559f) | 已部署; 918559f = 运行树 | `docs/ACCEPTANCE_b681ca5_2026-09-12.{md,json}`; `docs/receipts/safe_commit_*.log`; journal 08Z §3 |
| 3 | 执行器待落地: W1 #55 合同 / W2 读者三桶 / W6 修复 / W5 factor_health | W1/W2 在克隆已过电池, **事故后暂停**, 与 W6 同批 | `docs/receipts/w1_*`, `w2_*`; DESIGN 三份 |
| 4 | 研究链装置 15941da7(W3 十月驱动 / W4 判官底 28 / F9 判官自绑合同) | 入库; 链自检 228 ALL PASS(lead 复跑) | `v4_chain_2026-09-09/receipts/{monthly_chain,judge_floor}_2026-09-12/`; 三份 DESIGN |
| 5 | W7 十月门源码(STEP1/STEP2 月度通用) | 进行中 | 交付后追记 §11 |
| 6 | 平价装置(线上代码历史回放) Phase 1 + 前向 + Phase 2 PREREG | Phase 1 RESULT; 前向 1/3; G2-A PASS | `parity_replay_2026-09-12/RESULT_parity_phase1_2026-09-12.md`; PREREG 两份 + AMENDMENT 1–3 |
| 7 | 正确口径回测数字(逐年表) | 收据 | `r18_foundation/receipts/TABLE_per_year_v4_caliber_2026-09-12.md` |
| 8 | 待裁定 R-1..R-14 | 用户 | `docs/RULINGS_requested_2026-09-12.md` |
| 9 | 待实验清单 | §7 | — |

## §1 事故 E-0912-A(请最先复核; 每条事实带收据路径)
**链**: ① 12Z 锚(rid A1789215839)MEMEUSDT / POPCATUSDT `target_w=0` ⇒ 执行器按设计发 **reduceOnly=true** GTX 卖单(`anchor_loop.py` L1630 / L1930–1932; 回执 `"reduceOnly": true` 见 `state/live/watchdog/events.jsonl` 末行 actions.submit)。② 数量 = `round_qty(delta/mid)`(`binance_executor.plan` L774): MEME 1,933,986 张 vs 08Z 读回持仓 **1,933,692**(多 294 = 0.015%); POPCAT 10,435 vs 10,434(`pilot_log/20260912/position_readback.jsonl`)。③ 交易所把 reduce-only 单截到持仓: 回执 origQty **1933692 / 10434**(与持仓逐张相等), 全部成交(子成交 560266+782806+590620 / 8433+2001), 12Z 读回两名 **0**。④ 今晨 b681ca5 第 12 轮 `submit_identity_mismatch`(`binance_broker.py` L343 `_ident_check`, 相对容差 1e-6; L1487 调用)⇒ 「submit response origQty 1933692.0 differs from ours 1933986.0」⇒ `venue_inconsistent` ⇒ 请求账本 `inconsistent` ⇒ `terminal_reason=filled_amount_unknown`(orders.jsonl 两行), 两条 topup 腿 `skipped_unknown_fill`。⑤ `reconcile.py` L200–203 「矛盾最先 ⇒ unquantifiable」; L455–473 D2 「未知大小 = 异常」⇒ `execution_of_unknown_size` ×2。⑥ 看门狗 §4-5b 状态门(`watchdog.py` L1770–1867, M=1)触发; §4-7 漂移 = `bool(_rec["latest"])`(`watchdog_inputs.py` L115)同一对账 ⇒ 同因两条(`watchdog/last_eval.json` cond5_venue_event / cond7_ops)。⑦ 12:47:38Z 停开仓 → 12:47:39–12:50:01Z **255 张 IOC reduce-only 全成交, Σ 235,383 USDT**(events.jsonl flatten_all; executedQty==origQty 255/255, 0 错), 滑点 vs mid_at_submit **+5.39 bps = 126.90 USDT**, taker 费 ≈ 117.7 USDT(推断: 5.0 bps × 名义; 账本无读数)→ 读回 Σ|名义| 0 → Telegram HIGH 12:50:04Z(id 1403)。`anchor done rc=0` 12:58:29Z。
**为什么是假阳性**: 场所记录自洽(origQty == Σ 子成交 == 持仓, 读回 0); 「不符」唯一来源是我方数量比持仓多 0.015%; reduce-only 截量是交易所文档化行为。历史 `differs from ours` 今天前 **0 行**(pilot_log 全日扫描)。异常两名 Σ|intended| 1,524 USDT = gross **0.65%**, 响应 = 平 100%。
**修复(W6, 克隆 `/Users/haosiyu/cc_tmp/exec_w6`, 起点 918559f, 进行中)**: (a) 身份核对加第四态 `clamped`(reduceOnly ∧ resp.reduceOnly ∧ 0<origQty<ours 同侧 ⇒ 数量已知=origQty, 记录不判矛盾; origQty>ours / 方向错 / 非 reduceOnly 差 仍矛盾; 1e-6 容差不动); (b) 全退出数量 = 持仓张数(读回 `venue_position_qty`), 无 qty 列时退回旧路径并记 `qty_source`; (c) 比例响应(**书行为改动**, 用户 13:19Z「彻底修复」读作 R-14=A, **默认 ON**; 若研究员认为应先关默认请提): 最新对账锚的未知大小异常若 场所记录自洽 ∧ Σ|intended| ≤ gross 2% ∧ ≤5 名 ⇒ 停开仓 + HIGH + 只处置那几名; 否则现行全书阶梯。加派: reconcile 须从账本内容**重判**已持久化的 12Z 行(否则 `ops/resume_from_trip.sh` 因 cond5b 仍 ANOMALOUS 拒绝恢复); 告警文案「满页或查询失败」≠ 行内原因(身份/origQty)一并修。测试 T1–T9 含 12Z 真行正控 + 旧码红。
**请复核**: (i) 事实链每环的行号与收据是否如述; (ii) 是否还有第三种「场所改数量」的文档化行为会再次触发身份核对(见 `docs/CATALOGUE_venue_behaviours_positive_controls_2026-09-12.md` V1–V14, 尤其 V11 STP `EXPIRE_MAKER` 无处置无测试); (iii) (c) 的 2%/5 名阈值是否合理、默认 ON 是否应等你复核后; (iv) 我方**过程错误**: 12:59:19Z 我在锚 done 后 50 s 启动 W2 落地, 12 分钟后才从深查代理得知 12:47Z 已触发 —— 落地启动早于深查读数, 违反「先查再动」; 已 13:04Z 停止并复原运行树(`docs/receipts/safe_commit_w2_readers_three_bucket_20260912T125919Z.log` 尾行)。
**恢复**: 书空仓, 开仓停; 16Z/20Z 锚只报告不下单; 恢复 = W6 复审 → 用户字部署 → `resume_from_trip.sh`(用户手动)。

## §2 执行器: 今日已部署与待落地
| 提交 | 时间 | 内容 | 验证 | 请复核 |
|---|---|---|---|---|
| **b681ca5** 部署 | 06:05:30Z `fetch`+`merge --ff-only <sha>` | 15 轮复审(b0a573a1)全部运行时修复: 请求账本、E-0909-D/E 传输韧性、E-0909-E 有限上限截断、费用换算读者等 | `ACCEPTANCE_b681ca5`(隔离克隆 + 05:43Z 真状态: 新旧读者 19/19 锚逐位; 看门狗 43 日 0 差; 回滚排演 0 文件); 运行目录电池 132 套 131 绿(唯一红 = 账本事实, 旧树同 sha 复现 ⇒ 树无关); 08Z 首锚验收 §3 六条 PASS(request_ledger 159 行, 四类标记 0, −2027 残差 2,102→0) | **第 12 轮身份核对无 reduce-only 截量正控 ⇒ E-0912-A**。请审: 15 轮里还有哪些「新分类」缺文档化行为正控 |
| 77d9baf | 07:49Z safe_commit | `tests_disposition_matrix` 尺子第六次重标定(仅测试文件): VENUE-LOCKED 类 / −2027 分母 target / 自愿从行求和 / 承重断言 | 电池 132/132; DESIGN F1–F15; 三种突变红 | 是否有「放宽」(我方: 结构重分类, 非放宽) |
| 918559f | 09:51Z safe_commit | `_CAP_CLAMP_DEPLOYED_TS=1789201439.0`(仅测试文件) | 电池 132/132 | −2027 上线后为零断言从空集变实测(你 §3 指出项) |
| W2(待) | 克隆 exec_w2 | 三桶读者: `cost_buckets.py` 新, daily_summary / first_anchor_review / score_post_fix 三桶 + 非 USDT 单列 + None≠0; 53+31 检查 | 克隆电池 132/133(红 = 无 .env); `w2_readers_three_bucket.diff`(8 文件, sha fded2c21…) | 规则是否逐字抄 `anchor_loop.neutrality_price` 且逐键钉住; **事故后暂停落地** |
| W1(待) | 克隆 exec_w1 | #55 `ic_monitor.py` 告警合同: 对象/标定身份逐页; RECOVERED 一次; 新鲜度门 MAX_MISSING r24:2/r48:4; `--check/--dry` 严格只读; 52 检查 | 克隆电池 131/132; `w1_ic_monitor_contract.diff`(3 文件, sha ad2f6dba…) | 统计量/阈值/WINDOW_START 是否逐字不变; 新鲜度门后果: 09-07..12 五次判级全 INCOMPLETE(R-11); 冷却 24h 抖动(R-10) |
| W6(进行中) | 克隆 exec_w6 | §1 | 交付后追记 | — |
| W5(设计) | — | factor_health 消费者改指 #55 本地账本(上游 08-06 退役, 对象是退役 3 腿曲线, 产物断言 #9 空过) | `DESIGN_factor_health_repoint_2026-09-12.md` F1–F7 | 是否同意退役 ssh 源 |
运行树状态: `git status` 无代码改动, HEAD 918559f = origin/main(W2 diff 已 13:04Z 复原)。生产者 `~/wide_shadow` 09-05 后未动(正确: 09-05 后无研究结果够格改生产者)。

## §3 研究链装置 15941da7(+ 文档提交 c44065c8 等)
| 件 | 内容 | 收据 | 请复核 |
|---|---|---|---|
| W3 | `chain_v4_monthly.sh` 单驱动 11 阶段; 41 键月合同 `v4_month_2026-09.env`(九月正控)/ `v4_month_2026-10.env.template`; `chain_v4_monthly_dryrun.sh` 空根负控; refit 四键必填(裸调 rc 2); `BUNDLE_GENERATION` 必填; provenance `king_train_end_utc=2025-12-31T20Z`(月度导出不推进); MONTHS_ALL 由合同声明并对目标轴断言; 四片轮转(九月常量逐位同手写); `run_v4_arms` 逐 PID rc; 三生成脚本从基底逐位再生 | `receipts/monthly_chain_2026-09-12/`: pod2_root(preflight PASS, STEP1 FAIL/STEP2 PASS 判决字段 78/31 全等 09-09 归档), pod2_king_legs(bundle 6/8 文件逐位, fold_ic 0.0544/0.0609 相等, legs 旧行 10206/10212 逐位, 2023 席位 0.5865), pod2_dryrun(DRYRUN_PASS, 33 项点名缺失); GPU 0%/2MiB 前后; PID 333197/339489 未动 | 你的 R1–R5 是否各有会红测试([P] 41 格含 8 突变红); DESIGN §7 (i)(ii) 未验证面(mwf/refit/arms/judge/export 五阶段**未真跑**)是否如实; R2 两项(训练器 `_done` 复用不核身份; merge 只断言三 sha)明写未处理 |
| W4 | `v4_gate_common.REQUIRED_INPUTS[BUNDLE_export]` 11→28(= v2 门真收据 registered_inputs 逐名); 夹具扩到真形状 | `receipts/judge_floor_2026-09-12/`: pod2 真 A1 全 28 ⇒ ELIGIBLE; 漏 slow_pred / 漏 contract ⇒ 不合格 | 28 名清单 vs 真收据 |
| F9(lead 第七轮) | `judge_v4.py` 自绑 `inputs["eligibility_contract"]=CONTRACT_PATH`(此前调用方给路径只验「文件未变」); 前身 `judge_v4.r4_7f1aa5d6.py`; 自检 [Q] 6 格(他合同拒 / 逐字节副本过 / 出厂合同 + v2 签名拒 / **旧判官接受 = 旧码红** / 静态) | 链自检 151 → 222 → **228 ALL PASS**(`tests_pipeline_gates_lead_{merged,r7_first_227of228,r7}.log`) | **[O] 一格改标**: 「漏报 eligibility_contract ⇒ 拒」在第七轮反转为「判官自补 ⇒ 仍合格」; 首跑 227/228 正是它。我方判「非放宽」(指错仍拒), 请独立判 |
| 合同 | `ELIGIBILITY_CONTRACT.json` 1188267a(09:2xZ 应用; 前身 .r0_3299dc97); 文本第 8 句 (e) 落后代码一句(R-9) | `receipts/pod2_applied/` 正负控 | — |
| RUNBOOK_2026-10 | §0★ 唯一步骤单 + 修订 2/3: **十月只经驱动**; 仍开 = STEP1/STEP2 门九月专用(W7) | — | — |
复跑: `cd multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09 && /usr/bin/python3 tests_pipeline_gates.py`(≈6 min, 期望 `ALL PASS (228 checks)`); `python3 make_sha_manifest.py`(rc 0, 94 文件)。

## §4 平价装置(线上代码历史回放 —— 你 §2 指出的缺口)
- Phase 1(PREREG 0806c5e7 + AMENDMENT 1/2; RESULT b9c1f3c4): 装置 = 生产者代码经**一次性字符串替换**派生(`mk_replay_device.py` 2 处 / `mk_combo_replay_device.py`), EMA 逆推 roundtrip 4.8e-18, LR 截断规则(丢 anchor_ts ≥ 锚的分数行), `REPLAY_TRUNCATE_CACHE=1`。**G-P1 king 段 41/41 ≤ 9.3e-10(LR 40/40 差 0.0)**, G-P4 红能力 3/3, G-P3 内容 sha 0/41(机理 = H float32 存档, 定义性), **G-P2 combo 段自 09-05 16Z 链式 0/41 ≤1e-6(中位 1.05e-5, 最大 1.13e-4, 14 名)但从 09-11 20Z 在役状态起 3/3 精确 0.0**。
- 机理(AMENDMENT 3, 98a42feb): 08Z→12Z 缓存回填探针 **0/0/0**(11,472 行 × 829 名)⇒ 4h 尺度回填假说不成立; 12Z 快照种子平价(08Z 快照为种子)king L∞ 0.0 / combo 0.0 **精确**(前向 1/3); 预注册: 3 对快照 probe 全 0 且 3 次快照种子平价精确 ⇒ 判「链起点状态差」(09-05 起点的 EMA/mini-cache 历史), 任一 probe>0 ⇒ 回填假说复活。下两对 12Z→16Z(16:59Z)、16Z→20Z。
- Phase 2(PREREG 52bd410f): 只换输入不改代码路径; G2-A 通道平价 **PASS**(生产者缓存 vs pod holefix2 缓存 8,256 时刻 × 829 × 7 通道 |Δ| 0.0)。
- 请复核: 替换处是否只有两处且语义不变(`devices/*.py` diff); LR 截断规则是否等价于线上「本锚 LR 只见过去」; G-P2 的机理裁定序列是否合理。

## §5 正确口径(v4 pin)回测数字与实盘诊断
收据 `TABLE_per_year_v4_caliber_2026-09-12.md`(9123f38d; 从 r18 `arms_rec/C0_s42.npz` 重算, 全窗 n=9139 g +0.6359 Sharpe 1.2947 vs 收据 9138 / +0.6342 / 1.2912 边界一锚之差)。g = net_ex/gross_total(bps/锚, 单位 gross), 年化 = mean/std·√2190。
| 年 | n | g | Sharpe(s42 / s2027 / NW) | 年内 maxDD(单位 gross) |
|---|---|---|---|---|
| 2022(06-30 起) | 1110 | +0.159 | +0.48 / +0.48 / +0.36 | 5.6% |
| 2023 | 2190 | −0.649 | −1.94 / −1.82 / −1.93 | 16.8% |
| 2024 | 2196 | +0.487 | +1.09 / +1.03 / +1.09 | 13.1% |
| 2025 | 2190 | +0.677 | +1.19 / +1.31 / +1.20 | 8.3% |
| 2026 至 08-30 | 1453 | +3.100 | +4.53 / +4.54 / +4.53 | 8.6% |
| 全窗 | 9139 | +0.636 | 1.29 [0.33, 2.25] / 1.33 / 1.29 | 全史 ≥44%(下界) |
- 「2026 regime 3.0+」出处 = 2026 年内格; 冻结窗 2025-03..2026-08-10 的 2.9357 自身 CI95 [1.306, 4.565]。三条模型谱系全窗夏普同到一位小数 ⇒ 重训模型腿不改此表。未决扣减: 60 s markout 若不回复, 全窗 ≈1.16(CLOSEOUT L142)。
- 实盘 08-26→09-11 同口径: 价格 alpha −0.022 bps/锚(t −0.01), 资金费 −1.371(t −12.09); 回放 vs 实现 ρ 0.83 斜率 0.835; 最大差项 = 书构造 +2.6982 [+0.578,+4.322](**26 锚 08-26 04Z→08-31 00Z combo 期**, 我方此前「08-26 前形态差主导」的说法已按你 §5 更正)。
- 请复核: 逐年表的年化与 r18 收据口径是否一致(receipt Sharpe 用 block bootstrap SE, 我用 std); maxDD 换算「×2.0 ≈ NAV」的近似是否可接受。

## §6 今日其他入库(次要, 供索引)
PLAN `docs/PLAN_fix_all_gaps_2026-09-12.md`(11 项 G1–G11 + §3 状态 + §4 事故改序); STATUS 三问 `docs/STATUS_three_questions_2026-09-12.md`(+追问 +更正); 每锚深查 04Z/08Z/12Z 三节(journal); parabolic_onset 每日一跑 f6e48d4a(θ8 P 41/200, 未达复判); r18/r19/r20/r21 入档(见 CLOSEOUT); 记忆五条(E-0912-A / 用户硬反馈 / 月度链 / 尺子重标定 / 等)。

## §7 待实验与未测格(全部按预注册判据; **「零获准换装」**: 历史某窗显著、确认性证据、风险/成本接受域、正式资格是四件事 —— 研究员 563e3470 §7 更正, 原「零录取 = 无一过 (A)」与同表 XIB 全周期 (A) 矛盾)
| 项 | 状态 | 下一步 | 阻塞 |
|---|---|---|---|
| ~300 候选 + r8–r21 | **零获准换装**(CLOSEOUT); 其中 XIB_LAG50 全周期 (A) 是历史显著结果, 非录取 | — | — |
| 席位只看价格(你的第 1 点) | 腿层净额席位 ARM-S REJECT(−0.093/−0.089, 换手 +27%); 书路径净额 ARM-SB UNDECIDED(+0.084/+0.100 CI 含零, 停机 6→9) | **未测一格: 按比例缩放的 carry 罚 κ∈(0,1)**(便宜) | 无 |
| 仓位级 FTRIM(r15) | UNDECIDED +0.018 含零; 2026 −0.20; 换手 +24% | 不推进 | — |
| 慢滤波/免交易带 | 非对称带判负(带在进场侧净赚); 更慢角落(0.05, 2.5e-4)中位 1 年 +8.2% vs +0.3% 点估计, Δg CI 含零 | 影子臂候选 | 出口门 + 用户字 |
| CEM_99 carry 紧急处置 | +0.038 [−0.005, +0.085], 零假设重匹配后胜 6/6, Bonf-29 含零 | 预注册影子臂 | R-3 型裁定 |
| XIB_LAG50 | 全周期 Δg +0.41 [+0.18,+0.64] (A); 冻结窗 (C); 回吐窗 −5.69; ρ 0.91; 换手 +12.8% | 影子臂(R-3) | 用户裁定 |
| 平价 Phase 2(线上策略折外历史水平) | PREREG + G2-A PASS | G-P2 前向 3/3 后执行 | 16Z/20Z 快照对 |
| #55 阈值重标(在役 α/band) | 未做 | 平价 Phase 2 后 | — |
| 60 s markout 是否回复(成本重定价) | 未决(影响规划数 ~10%) | 4h lag 采样 | 数据积累 |
| Q6 跨锚未解释量继承政策落码 | 数学接受未落码 | R-5 | 用户 |
| 十月重训 | W7 门源码进行中 | 合同批准 | 用户字 |
| 逐年表按 block-bootstrap SE 复算 | 未做(本表用 std) | 便宜 | — |

## §8 待裁定(R-1..R-14, 详见 RULINGS 文件)
R-1 BNB 抵扣(建议恢复) · R-2 杠杆 2.0×(无建议) · R-3 XIB 影子 · R-4 换钉 w10_sleeve_r18 + NW 基线 · R-5 Q6 落码 · R-6 R6-MARK · R-7 paper 计分器 · R-8 十月重训 · R-9 合同文本落后一句 · R-10 #55 冷却 23h · R-11 新鲜度门维持 · R-12 m1 分母 · **R-13 恢复路径 = A 已裁定** · **R-14 比例响应(读作 A, 默认 ON, 可翻)**。

## §9 我方今日错误与更正(请重点核)
1. **E-0912-A 本身**: 我复核/部署的 b681ca5 第 12 轮身份核对缺 reduce-only 截量态; 15 轮复审无此正控。
2. **过程**: W2 落地 12:59:19Z 启动早于 12Z 深查读数(计划窗 13:00Z, 提前 41 s; 且看门狗 12:47Z 已触发未被我察觉 12 分钟); 13:04Z 停止复原。
3. 早间: 电池计数 132/130 误写 128/126(漏 4 个 ops 入口套件); A1788999840 时间误写 09-09 20Z(实 09-10 00:24Z); 「BOOK +2.70 主因 08-26 前形态差」错(实 combo 期 26 锚); 「监控读错书」过宽(#55 读实盘, 只有 paper 计分器读退役书)—— 均已更正入 STATE/STATUS。
4. 链自检: 应用合同后 r5 用例过时(改 r6); v4_gate_common 11→27 一度破 8 格(回退, W4 重做); [Q] 首跑 227/228([O] 语义反转, 改标)。
5. 平价驱动六处修(LR 截断差一锚 / lightgbm 解释器 / zsh 分词 / combo 参照文件 / mini-data 复用 / rmtree 删前锚 H); `git add` 扫进 216MB replay_home(已 amend + .gitignore)。
6. 12Z 派工说「12Z 非结算锚」不准确: 188 个 4h 间隔名在 12Z 结算(funding −9.25U)。
7. 平仓代价首算错(signed 求和 969.6), 复算 |名义| 235,383 后才报。
8. 锚监视器首版匹配串错(`anchor done rc=` 才是真实结束行), 12Z 前修正。

## §10 复核方法建议(可复跑)
- 链: `tests_pipeline_gates.py`(228), `make_sha_manifest.py`; pod2 收据目录 sha 自校验。
- 执行器: 在隔离克隆 `git checkout 918559f && git apply <w2.diff> && git apply <w1.diff> && bash run_acceptance.sh`(期望 132/133 与 131/132, 红 = 无 .env); W6 交付后同法。
- 平价: `parity_replay_2026-09-12/receipts/*.json` + `SHA256SUMS.txt`; 复跑命令逐字在 RESULT 与 AMENDMENT。
- 逐年表: 收据内含重算脚本口径; `arms_rec/C0_s42.npz` sha 在 `SHA256_arms_rec.json`。
- 事故: `state/live/watchdog/{state,last_eval,trip_receipt}.json`, `events.jsonl` 末行, `pilot_log/20260912/{orders,fills,position_readback}.jsonl` 两名行(只读)。

## §11 追记 1(2026-09-12 14:4xZ)—— 独立研究员复审 563e3470 已收, 逐项处置
入口 `.claude/worktrees/codex-independent-20260907/docs/HANDOFF_batch_incident_independent_review_2026-09-12.md`; 总评 `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_batch_incident_review_2026-09-12/``REVIEW.md` + 四份分审。**总判: 事故主因成立, W6(a)(b) 成立; 不签「全部闭环」; W6(c) 保持 OFF。** 我方处置(全部接受, 无一条不成立):
| 研究员发现 | 处置 | 派给 |
|---|---|---|
| C1 (P1) W6(c) 「自洽」不核 request.inconsistent / row.known=Σ请求 C / gross 有限 ⇒ 身份矛盾可被降级为局部响应 | (c) 默认改回 **OFF**; 自洽谓词按 C1 三格重写为红→绿; C2 `_local_response` 符号边界单测; C3 措辞改「事故后制定的政策阈值」 | W6 |
| 旧 12Z 两行交新 reconcile 仍 2 异常; 恢复动词受 cond5b 阻 | 历史重判 = **只读收据**(不改账本、不翻 state), T9 用真账本证 CLEAN | W6 |
| 255 笔保护性平仓 0 fills / 费 255 None | 平仓路径自写 fills / 触发 userTrades 回填, 费实测而非 5 bps 估 | W6 |
| 正控目录 V1/F3/F8 过度概括、V8 错、V11 不成立、V9 混三身份 | 目录 §更正 已写 | lead(本提交) |
| B-R1 (P1) `V4_STAGES=refit` 越过上游门 | 每阶段 dispatch 前 require 前置票据(依赖图非文件顺序) | W7 |
| B-R2 (P1 有条件) 判官不验收据记录的条件依赖(femat/signal_receipt) | 判官按收据 inputs_sha256 全部记录项自行定位并验; 新套件 `tests_judge_dynamic_deps.py`; 前身 `judge_v4.r5_f6850dc3.py` | W4 |
| B-R3 (P2) 配置继承父环境; CLIP 可继承 RAW 补丁 | loader 要求键**在文件中**且先 unset; CLIP 命令显式清空 `DLWT_RAW_PATCH` | W7 |
| B-R4 (P2) W7 `NONE` 不核 builder 身份; 新尾全 NaN 仍过 | NONE 绑 `pod_fea_ext_clamp.py` 钉 sha; 新尾质量门(先入 PREREG 修订) | W7 |
| R5 旧脚本只有横幅 | 五个旧链脚本加 `V4_LEGACY_OK=1` 物理门 + 测试 | W7 |
| W1-R1/R2/R3 恢复语义 / 冷却吞复发 / `--che` 缩写 | 恢复按触发窗口与事件; 冷却限同一事件; `allow_abbrev=False` 先解析后 import | W1 |
| W2-R1/R2 m1 完整性位错(冻结文件)/ 截断收入仍算残差 / 「下界」措辞 / 覆盖率先 round | 消费者改用 cost_buckets 完整性, 不改冻结 `pilot_metrics.py`(冲突记 R-12b); 残差要求 complete; 「已读部分」 | W2 |
| G2-A 原 829 名/≥40 天门未满足却写 PASS(实 28.66 天, 829 轴支持差 15.47–27.88%) | PREREG Phase 2 AMENDMENT: 原门 **NOT PASSED AS WRITTEN**, 新具名子门 G2-A′「当前 live450 精确通道平价」PASS; G2-C 仍必须 | lead(本提交) |
| AMENDMENT 3 机理措辞「只能来自起点状态差」不唯一 | 改为「候选解释, 未排除历史缓存/辅助文件/左边界差」; 七通道 08Z→12Z 0/0 由研究员独立加强 | lead(本提交) |
| 逐年表: 多读一锚(至 08-31 00Z, n9139 vs 钉 9138)、2024 g 0.486、算术 gross DD×2 ≠ 复利 NAV DD(2023 33.5% vs **28.92%**)、SE 表述错(Sharpe=mean/std; 收据 sharpe_se=√(2190/n); bootstrap 是均值的)、「全史 ≥44% 下界」是点读数非下界 | 收据勘误节已写; 日块 bootstrap Sharpe CI 全窗 [0.32, 2.28]、2026 [2.21, 6.79] 采纳为探索性诊断 | lead(本提交) |
| W5 设计: 字段 `eval_at` 非 `at`; 期望 frontier ≠ 实际 frontier; 命名不得叫「因子健康」; 三态; 通知职责重叠 | DESIGN §5 更正已写, 落码前再审 | lead(本提交) |
| 「零录取」措辞 | 改「零获准换装」(§7) | lead(本提交) |
| 过程: W2 落地启动早于深查 | 已认; 顺序改为「事故事实冻结 → 待部署 diff 冻结 → 恢复证据齐备」 | lead |
**未接受/无**。研究员保留的正面结论(F9 自绑正确、W6 按合约量退出正确、近期 combo 三锚连续精确、live450 七通道精确)与本方一致。W6/W7/W4/W1/W2 交付后追记 2。

## §11 追记 2(2026-09-12 15:1xZ)—— 研究链装置第二批入库 `942b3e73`(lead 复跑 328/328 + 19/19 后一次提交)
| 件 | 落地 | 收据 | 请复核 |
|---|---|---|---|
| W7 十月门 | `v4_gate_step1_m.py` 79950786 / `v4_gate_step2_m.py` **0fe5ec55**(B-R4 后), 由冻结源经白名单行生成; PREREG 2290f191 先冻结, AMENDMENT 1 4a407f2b 先于 r2 运行 | pod2 `w7_gates/`: STEP1 78/0(字面 FAIL 同归档), STEP2 r2 31 等 + 唯一预注册新字段 `tail_quality`; 真合同 REQUIRE_FAIL(预期) | 合同批准对象 = **0fe5ec55**(非 455e3df4); §3.3 NONE 条件; tail 豁免规则 |
| B-R1 | `chain_v4_monthly.sh` c6ea34fa: 每阶段 prereq_* 先于 dispatch(绑本合同 sha + 本月根) | [S] 45 格; 研究员探针 `W3_refit_subset_dispatches_without_upstream_receipts` True→False | 依赖图是否完整(arms/judge/export 的前置) |
| B-R3 | `chain_lib.sh` 3cd82956: 46 键须为文件内 KEY= 行, 先 unset; 数据阶段五子进程 `env -i` + 白名单, CLIP `DLWT_RAW_PATCH=` | 探针 `omitted_SEEDS_inherited` 0→4 拒; CLIP 环境格 | **未做**: GPU 阶段未 env -i(W7 明写) |
| B-R4 | NONE 须 合同钉 == preflight 钉 == 盘上 builder sha(`PREV_CLAMP_BUILDER_SHA256`); `tail_quality` 成员 ≥1 ∧ 有限比 ≥0.90 | 探针 `NONE_positive_without_identity` PASS→REFUSED; `new_tail_NaN` PASS→FAIL | 0.90 地板来自九月标定(min 0.9756) —— 是否合理 |
| R5 | 五个旧链脚本 `V4_LEGACY_OK` 物理门, 裸调 rc 64 | [S] 各一格 | — |
| B-R2(W4) | `v4_gate_common.py` 24e813f1 `require(recorded_extras)`; `judge_v4.py` **c2a81c48** 按收据 inputs_sha256 全部记录项自行定位并验; 前身 `judge_v4.r5_f6850dc3.py`; `make_sha_manifest` r0–r9 | `tests_judge_dynamic_deps.py` 19/19(含旧判官红); 探针 `changed_receipt_extra_omitted` True→False; `receipts/judge_floor_2026-09-12/r8/` | 收据无 inputs_path 时的拒绝语义 |
| E-0912-B(W3) | `pod_export_bundle_v4.py` 42555a37 无 BUNDLE_OUT 即拒; 自检 `run_sandboxed()` + 静态禁裸调格 | `e0912b/`: tar 恢复 sha 先验, 8/8 对清单, **恢复后 v2 门 PASS + REQUIRE_OK 15:01:44Z**; ERROR_LEDGER E-0912-B | 自检沙箱规则是否覆盖全部真写者 |
| 自检 | 151 → 228 → 278 → **328**(lead 复跑 ALL PASS; `tests_pipeline_gates_lead_final.log`), 新套件 19 | manifest rc 0 | 三人同文件并发编辑(W3/W7)—— 最终文件 sha 7181045d 在 lead 运行前后不变 |
**仍开(诚实)**: mwf/refit/arms/judge/export 真数据未跑到底(GPU 禁); 十月合同批准 = 用户字(两门 sha); GPU 阶段 env 未清; r20 A1 收据以 e0912b 新收据替代(旧收据留档为过期)。**未入库**: W6(执行器)/ W1 / W2 仍在克隆, 待其电池与红集证明。

## §11 追记 3(2026-09-12 17:0xZ)—— 执行器三件最终交付 + 叠加落地电池
| 件 | 最终 diff(sha256 前 8) | 内容 | 自证 | 研究员复审项闭合 |
|---|---|---|---|---|
| **W6 (a)(b)** | `w6_reduce_only_clamp_ab.diff` **cdf37046**(= 918559f→fe97e46, 25 文件含 12Z 真日夹具 4.3MB) | clamped 第四态; 全退出 = 持仓张数; reconcile 从账本内容重判持久化的「矛盾」(仅限有据 clamp 型); 告警文案 = 行内原因; 平仓路径 fills/费回填修(F<utc>-SYM-n 无 rid 前缀 ⇒ B26b 重建 0 腿 = 根因); Qs/Qv/L/F 命名; T7 合成标注 | 新套件 75/75 + 回填 13/13; 旧码 918559f 红(32/70); **只读重判收据** `w6_rejudge_20260912_receipt.json`(两行 6/6 交叉核对真); **T9 真 12Z 日: 新码 cond5b CLEAN / §4-7 CLEAN, 旧码 ANOMALOUS 2 + DRIFT**; 43 日复现 `w6_resume_gate_replica_{new,old}.log`; 研究员探针重跑 exit 0 | C1 谓词(三格)、C2 符号边界(5 格)、C3 措辞、历史重判=只读收据、255 平仓费人口(代码修好, **真跑需凭据: `LIVE_MODE=LIVE python3 ops/backfill_fills.py --day 20260912 [--apply]` = 运维步**) |
| W6 (c) | `w6_proportional_response_c.diff`(fe97e46→3308cbc, 7 文件) | 比例响应, **默认 OFF**(`UNKNOWN_SIZE_LOCAL_RESPONSE=False`) | 50/50, 旧码 T8 红 | 不随 (a)(b) 落地; 翻开 = R-14 用户字 |
| **W2** | `w2_readers_three_bucket.diff` **3794ecfd** | E6 完整性由 cost_buckets 派生(m1 位保留并标不一致; 冻结 `pilot_metrics.py` 不动 = R-12b); 残差要求 realised.complete; 「已读部分」; NaN 不可观测; 覆盖率精确比; 真账本格显式 SKIP | 64+42(有账本)/ 58+6 SKIP + 39+3 SKIP(无账本); 旧读者红; 克隆电池 133 套 132 绿 | W2-R1/R2 |
| **W1** | `w1_ic_monitor_contract.diff` **86324465** | 恢复按触发窗/事件(RECOVERED 仅当触发窗可判且脱线); 冷却限同一事件; `allow_abbrev=False` 先解析后 import; OBJECT 措辞; <24 行普查; `LEGACY_TRIGGER_WINDOWS=["r48"]`(事实: 09-09/09-10 DECIDE 皆 r48 门); T9g 无账本 SKIP | 76/76; 旧码 918559f 与复审冻结版 8b2c218c 均红; 克隆电池 132 套 131 绿 | W1-R1/R2/R3; 最早 RECOVERED 仍 09-16(更正 09-14 说法) |
**叠加落地电池**(fresh clone 918559f + W6ab → W2 → W1 顺序应用, 真 state 副本只读拷入, `stacked_landing_battery_20260912T164355Z.log`): 三 diff 干净应用(21 文件), compile ok, 四新套件全绿(reduce_only_clamp / ic_monitor / readers 42 / daily_summary 64+1 SKIP); **130 套, 红 2**: `tests_env_loading`(克隆无 .env, 预期)与 **`tests_disposition_matrix`**(今日账本事实: 12Z 锚两行被尺子计为稳态锚 1,524U 非自愿缺口, 且 12Z 既非稳态也非停机锚)。后者会在运行树 safe_commit 电池同样红 ⇒ **落地前需第七次尺子重标定(事实分类, 不放宽)**: 有据重判的行不计非自愿缺口 + 新类 TRIP-FLATTENED(承重断言: 255 张 protective_flatten Σ 235,383U), 已派 W6, 仅测试文件。
**落地顺序(待用户字)**: 非锚窗 safe_commit ×3(W6ab → W2 → W1; 各自电池全绿)→ 首锚验收(RUNBOOK §3 + W6 新条目: 全退出名 origQty == 持仓、clamped 记录数、四类标记 0)→ 用户手动 `resume_from_trip.sh`(其自检: LIVE_MODE、公共路径探针、看门狗复评; W6 §4.5)→ 运维步: 平仓费真回填 `--apply`。
**未入库/未做**: (c) 不落地; 平仓费真回填未跑(凭据); 16Z 前向平价 2/3, 20Z 后 3/3。

