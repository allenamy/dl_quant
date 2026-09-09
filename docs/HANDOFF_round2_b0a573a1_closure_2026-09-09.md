# HANDOFF round 2 · 复审 b0a573a1 的收口件(给独立研究员复核「是否真正关闭」)

> **创建:** 2026-09-09 16:0xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 交付复核(合并 ≠ 部署) | **作废条件:** 任一分支被改写或合入后本文只作历史

## §0 复核对象(两条分支, 分别复审, 分别合并; 实盘主树与生产者未动)

| 仓 | 分支 | 提交 | 基底 | 内容 |
|---|---|---|---|---|
| 实盘 `~/dl_quant_live`(origin allenamy/dl_quant_live) | `review/b0a573a1-executor` | **961a858** | main @ d040c74 | 执行器 UNKNOWN/重发协议 + 补单/重挂歧义 + 收尾逐计划 + E-0909-E 有限上限截断 |
| 研究 `quant_research`(multi-asset-v2) | `review/b0a573a1-pipeline` | **见 git log(本文所在提交)** | multi-asset-v2 @ 77802646 | 门=程序条件 / 链失败阻断 / 判官必需输入 / 生成器修复 / E-0909-F king 时钟装置 + PREREG |

用户令(09-09): 通过复核后分别合入研究仓主开发线(multi-asset-v2)与实盘仓对应分支(main); 合并与实盘部署分开; 是否重训、换装 bundle、重启执行器, 另按验收结果裁定。

## §1 执行器 UNKNOWN(复审 P1-EXEC #1–#3, P2)→ 分支 961a858

**协议(`live/binance_broker.py` `_request` / `_settle_order_post`)**: 下单 POST 只尝试一次; 任何非定论结果 — 传输请求相(URLError)、传输应答相(裸 OSError/HTTPException)、**HTTP 5xx、200 非 JSON**(币安文档: execution status UNKNOWN)— 都不重发, 只按我们自己的 `newClientOrderId` 查场所记录: 存在→把场所记录当应答返回(`_resolved_by_query`, `last_fill_details` 读它的 status/executedQty/cumQuote); -2013 两次(各停 `ORDER_QUERY_PAUSE_S`=1s)→ `VenueTransportError(resolved="absent")`, 调用方记「未发」, **不重发**; 查不到→`ambiguous=True`。定论拒单(4xx 含码、429/418)逐字不变。GET/DELETE 保留有界重发。

**调用点(`live/binance_executor.py`)**: maker(`submit_maker`): absent→`transport_error` 行; 歧义→留 `live`(阶段 B 撤单+读成交)。重挂(`_requote_benign_rejects`): 歧义→`rested`(attempt_idx 2, cancel_resting 撤 -2 id)并退出补单人口; absent→`transport_error` 行(attempt 2), 仍欠补单。补单(`topup`): 已确认块 `_acc`/`_n_sent` 在 try 之外; 歧义或某块成交不可读→`filled_amount_unknown`(filled_notional None, **`filled_known_notional`=已确认, `filled_unknown_residual`=未知余量**, 新列); absent 且已有块→`abandoned_max_attempts` 且 filled=已确认; 普通拒单在已确认块后→filled=已确认(旧行为写 0); 无块 absent→`transport_error`。收尾(`scheduler/anchor_loop.submit_with_cleanup`): 逐计划 try, 失败行具名 `rows_failed` 并入页。

**测试**: `live/tests_transport_resilience.py` **89 检查**(原 69 改写 [C]/[E] 为新协议 + 新 [P1]–[P6]): 复审六场景逐一 — 真 `do_open` 接受后抛(**POST→GET, 接受 1 次**); 503→查→存在采纳 / 503→-2013×2→`transport_error` 非 `venue_reject` / 503+查失败→歧义入 live / 200 非 JSON→查 / 429 仍定论; 重挂歧义→rested、absent→行; 补单 单歧义 / 5+歧义 / 5+拒单 / 5+absent / 单 absent 五格; 收尾一行故障其余照写; 布线断言(无重发分支、`_settle_order_post` 恰两处、三处调用点顺序)。`live/tests_venue_cap_clamp.py` 22 检查。工作树全电池 129 套: 127 绿 + `tests_env_loading`/`tests_alarm_digest` 在补齐 `.env` 符号链接与 `notify_audit.jsonl` 快照后绿(环境夹具, 非代码)。

**未证/边界(请复核)**: `_resolve_ambiguous_order` 的 -2013 仍不是远端一致性证明 — 本轮的处理是**不再据此重发**, 只记「未发」; 若该锚后来出现该 clientOrderId 的成交, 下一锚 `sweep_stale_orders` 与对账是兜底, 账本会有一行 `transport_error` 与一笔无行成交并存(可从 orderId 归属回填)。请判断这是否可接受, 或要求 absent 也进 live。

## §2 失败阻断(复审 P1-PIPE / R4 / R7 / P1-REGEN)→ 分支 620db83c

| 项 | 修复 | 证据 |
|---|---|---|
| 门 FAIL 仍 rc0 | `v4_gate_common.finalize`: 写收据 {gate, PASS, inputs_sha256, self_sha256, argv, utc}, **FAIL exit 3**; step1/step2/G2/G1 全部改用 | `tests_pipeline_gates.py` [B][G] |
| 只核 E_row(R7) | 闭包门加轴检查: E_ts 相等、symbols 相等同序、E_row 严格递增且 48 行网格、E_ts↔E_row 一致、pair 唯一且在范围、列数=期望、X 行数=pair 数 | [C][D]: E_ts+300 & 反转 symbols ⇒ FAIL(旧版 PASS) |
| 父链不阻断 / STEP1_PASS 只看文件 | `chain_lib.sh`: `require_gate`(PASS + 输入 sha 新鲜)、`run_shards`(按 PID 等待收 rc, 任一非零 die 不合并不 DONE)、`check_marker`; 四个驱动重写; post_export 用 `require step1.json` 轮询代替标记文件 | [E][I]: 分片 rc 7 ⇒ 驱动 rc 1、无 merge、无 DONE; FAIL 收据 ⇒ require 退 3 不派发; 输入变了 ⇒ 收据过期 |
| 判官缺输入 rc0 / 部分窗 | 缺任一对照所需臂 ⇒ exit 2; 冻结窗覆盖 ≠ 3168 ⇒ exit 2; A0p 复现 max|Δ| > 1e-6 或缺失 ⇒ exit 3(`JUDGE_ALLOW_PARTIAL=1` 只作探索且写进收据) | [F] |
| 生成器覆盖 BUNDLE_BASE | `make_v4_scripts.py` 发出 `BASE = json.load(open(os.environ.get("BUNDLE_BASE", …)))` 行; 输入基底/输出目录参数化 | [H]: 三个 v4 脚本自归档真基底(55ee8382 / ea3675b8 / c210bac6)**逐位再生** |
| 历史映射(R5) | 真首轮泄漏门 `v4_leakcheck.r0_bb7f14ac.py` 补回; 清单 `receipt_to_source`; 所有产收据旧版本 `.r1_/.r2_` 快照 | `receipts/v4_scripts_sha_full.json`(75 脚本) |
| 文档(R6) | RUNBOOK §v4 第 3 步撤回 AMD3 例外与「RAW/CLIP 无差」; CONST2027 进度更正 | 42eecc09(主线) |

**尚未做(明写)**: 加固脚本的 pod2 副本在 E-0909-F 链跑完后同步并重跑 G2(稳定)/判官出合规收据(旧收据无 inputs_sha256, `require` 会正确拒绝它们); 旧 `STEP1_PASS` 标记文件保留为历史。

## §3 训练—生产特征一致性(复审 P1-CONTRACT)→ E-0909-F

**缺陷范围(PREREG_king_clock_E_2026-09-09 §1, 已读码核对)**: 只有 king 腿: 离线特征窗 [E−w, E−1] vs 生产 [E−w+1, E](差一根 bar); king 训练标签 [E, E+47] vs DL/生产记账 [E+1, E+48]。DL 特征(`pod_dlw_features_ext.py` = 生产 `fea171/dlw_features.py`, hi=E+1)、fea89 构建器(hi=E+1)、DL 目标([E+1,E+48])与生产同源, 无偏差; 生产者自身记账 `CDf[pi+1:ai+1]` = [E+1, E+48]。

**G4 量化报告(只报不判; `receipts/G4_king_quant.json`, v4 booster `slow2026.txt`, 六锚同成员)**: 送 booster 前 float16 往返 vs float32 直送 — Spearman **1.0000**, 十分位重叠 **100%**, max|Δpred| 0(一锚 0.0016) ⇒ 存储量化对分数无实质影响, **不需要生产改动**。而**时钟差一 bar**(训练表示 A vs 生产时钟 C)— Spearman 0.976–0.990, 顶十分位重叠 78–93%, max|Δpred| 0.02–0.046 vs 分数 σ 0.018–0.027 ⇒ 服务时 10–20% 的顶十分位成员与训练表示不同, 时钟对齐是实质纠正。自检: 离线 E−1 时钟 float64 重算 → float16 与归档逐位 0 格差(六锚), 平价装置本身正确。

| 锚 | 成员 | Spearman A(训练表示)~B(生产) | C(量化)~B | 十分位重叠 top/bot | max\|Δpred\| / σ |
|---|---|---|---|---|---|
| 2022-01-08T00:00 | 136 | 0.9846 | 1.0000 | 0.92 / 0.85 | 0.0325 / 0.0273 |
| 2025-04-05T04:00 | 379 | 0.9847 | 1.0000 | 0.92 / 0.97 | 0.0218 / 0.0205 |
| 2026-08-20T00:00 | 400 | 0.9760 | 1.0000 | 0.93 / 0.85 | 0.0373 / 0.0234 |
| 2023-06-01T00:00 | 184 | 0.9888 | 1.0000 | 0.89 / 0.83 | 0.0217 / 0.0179 |
| 2024-11-15T08:00 | 308 | 0.9896 | 1.0000 | 0.87 / 0.93 | 0.0384 / 0.0244 |
| 2025-12-01T16:00 | 400 | 0.9765 | 1.0000 | 0.78 / 0.88 | 0.0460 / 0.0249 |

**干预与门(PREREG ca7c5816 + AMENDMENT 1–3)**: `pod_fea_ext_e.py`(只改时钟: 窗 [E−w+1, E], 标签 [E+1, E+48]); 新轴 10184 锚(比 v4 多 2022-01-07 16Z/20Z 两锚, 成员窗后移一 bar 的边界效应, 旧锚零丢失); 六锚成员与 v4 逐位同。

**G1 平价门 = PASS(run 2; run 1 因参照实现对 float64 和排序而在两锚各 2 个秩格判红, AMENDMENT 1 明写更正, 收据 `G1_king_clock_parity_run1_FAIL.json` 保留)**: 新构建器存档 vs 生产算子 float32(六锚, 80 列 float16 位比):

| 锚 | 成员 | 新 vs 生产(float32) 不等格 | 旧 v4 vs 生产(阳性对照) |
|---|---|---|---|
| 2022-01-08T00:00 | 136 | 1/10880 (0.009%) | 4731 (43.5%) |
| 2025-04-05T04:00 | 379 | 13/30320 (0.043%) | 14666 (48.4%) |
| 2026-08-20T00:00 | 400 | 12/32000 (0.037%) | 15850 (49.5%) |
| 2023-06-01T00:00 | 184 | 3/14720 (0.020%) | 6037 (41.0%) |
| 2024-11-15T08:00 | 308 | 6/24640 (0.024%) | 10765 (43.7%) |
| 2025-12-01T16:00 | 400 | 15/32000 (0.047%) | 16875 (52.7%) |

float64 归约参照(和先转 float32 再排序)vs 新存档: 六锚 **0 格**。⇒ 训练特征与生产算子在同时钟下逐位一致到浮点归约精度; 旧构建器 41–53% 格不等 = 门看得见缺陷。

**G2 导出门 = FAIL(如实)**: 门② fold 2024 Δ+0.0000 / 2025 Δ−0.0024(≤0.004 ✓), 门③ 2026 IC +0.0559 vs 0.0571 ✓, **守卫 Sharpe 2.260 < 2.27**。六格分解(`guard_decompose_v4e.json`, v3splice 面板, R1 2.284 / R2 2.304 复现): 标签窗效应 v3 −0.003、v4 +0.023 ⇒ 不是标签窗; 预测效应 v4e−v4 在旧标签 **+0.071**、在 E 标签 **−0.067**, 符号相反, 量级 ≈ 守卫单次读数的抽样误差(年化 Sharpe SE ≈ √(2190/5839) ≈ 0.6, 带宽 0.3)。AMENDMENT 2 重定基带 [2.267, 2.567] 仍外 0.007 ⇒ **按规则 G2 FAIL, v4e 无换装候选资格**。登记(不改判): 守卫带是复现门, 作新模型录取门时分辨率不足, 请你判断是否该在 RUNBOOK 里改成带 CI 的书层判官。

**G4 量化**: 见上表 — float16 存储无影响; 时钟差一 bar 改变 10–20% 顶十分位成员 ⇒ 对齐是实质纠正(与 G2 无关)。

**G3 书层(信息读数, AMENDMENT 3; 不是候选路径; `receipts/JUDGE_v4e_informational.json`, 判官冻结 §4 原样, 28 臂全在, 冻结窗 3168 锚, bps/锚/gross)**:

| 对照 | 席位 | s42 Δ [CI95] | s2027 Δ [CI95] | 判读 |
|---|---|---|---|---|
| A1e-A1 | 动态 | -0.041 [-0.331, +0.245] | -0.055 [-0.348, +0.225] | (C) UNDECIDED |
| A1e-A1 | 固定 0.21 | +0.050 [-0.030, +0.124] | +0.052 [-0.018, +0.122] | (C) UNDECIDED |
| A1e-A0 | 动态 | +0.019 [-0.255, +0.291] | -0.007 [-0.276, +0.243] | (C) UNDECIDED |
| A1e-A0 | 固定 0.21 | +0.055 [-0.041, +0.144] | +0.042 [-0.044, +0.127] | (C) UNDECIDED |

水平(冻结窗 均值 / Sharpe / maxDD bps): A1e 动态 s42 +1.913 / 3.14 / 835, s2027 +1.891 / 3.09 / 917; A1 动态 s42 +1.954 / 3.02 / 851; A1e 固定 s42 +1.881 / 2.94 / 728。逐年: A1e 动态 2023 −0.63/−0.59(NEG), 2024 +0.68, 2025 +0.81/+0.87, 2026→08-10 +3.64。
读法: 时钟纠正在书层**未检出差异**(四格 (C); 动态席位 CI 比 A1s−A1 宽一个量级, 因为 king 预测本身变了 10–20% 顶十分位), 与 G4「分数层实质变化」并存 — 分数层变化没有在书层转成可测净额, 这与本轮其它十四格一致。**结论**: 训练/生产合同现在可以同定义(G1 PASS 的构建器), 但 v4e 因 G2 守卫红不具备换装资格; 若要把纠正带上线, 需 (a) 用户裁定守卫带的定性(复现门 vs 录取门), (b) 按 RUNBOOK §v4 全链(含 DL legs)重跑。

## §4 复核清单(建议)

1. 执行器: 用你的 `audit_transport.py` 夹具对 961a858 重跑六场景(期望全部变为「已处理」而非「复现缺陷」); 特别看 §1 末的 absent 处理边界。
2. 流水线: 运行 `tests_pipeline_gates.py`(21 项); 在 pod2 上核对同步后的脚本 sha 与 `receipts/v4_scripts_sha_full.json`; 检查 `chain_lib.sh` 的 `run_shards` 对 4 个分片的 PID 等待是否覆盖你复现的「子进程失败未传到父链」。
3. 一致性: `v4e_gate_parity.py` 的六锚结果(你的三锚 + 预定三锚)与你 `clamp_clock/FEATURES.npz` 的 live 数组对照; G4 量化报告是否支持「送 booster 前 float16 往返」作为生产候选。
4. 数字: `JUDGE_v4e.json` 的 A1e−A1 / A1e−A0 四格与 56 个 CI 复算。
