# HANDOFF round 2 · 复审 b0a573a1 的收口件(给独立研究员复核「是否真正关闭」)

> **创建:** 2026-09-09 16:0xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 交付复核(合并 ≠ 部署) | **作废条件:** 任一分支被改写或合入后本文只作历史

## §0 复核对象(两条分支, 分别复审, 分别合并; 实盘主树与生产者未动)

| 仓 | 分支 | 提交 | 基底 | 内容 |
|---|---|---|---|---|
| 实盘 `~/dl_quant_live`(origin allenamy/dl_quant_live) | `review/b0a573a1-executor` | **961a858** | main @ d040c74 | 执行器 UNKNOWN/重发协议 + 补单/重挂歧义 + 收尾逐计划 + E-0909-E 有限上限截断 |
| 研究 `quant_research`(multi-asset-v2) | `review/b0a573a1-pipeline` | **620db83c**(+ 本文提交) | multi-asset-v2 @ 77802646 | 门=程序条件 / 链失败阻断 / 判官必需输入 / 生成器修复 / E-0909-F king 时钟装置 + PREREG |

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

<E0909F_RESULTS>

## §4 复核清单(建议)

1. 执行器: 用你的 `audit_transport.py` 夹具对 961a858 重跑六场景(期望全部变为「已处理」而非「复现缺陷」); 特别看 §1 末的 absent 处理边界。
2. 流水线: 运行 `tests_pipeline_gates.py`(21 项); 在 pod2 上核对同步后的脚本 sha 与 `receipts/v4_scripts_sha_full.json`; 检查 `chain_lib.sh` 的 `run_shards` 对 4 个分片的 PID 等待是否覆盖你复现的「子进程失败未传到父链」。
3. 一致性: `v4e_gate_parity.py` 的六锚结果(你的三锚 + 预定三锚)与你 `clamp_clock/FEATURES.npz` 的 live 数组对照; G4 量化报告是否支持「送 booster 前 float16 往返」作为生产候选。
4. 数字: `JUDGE_v4e.json` 的 A1e−A1 / A1e−A0 四格与 56 个 CI 复算。
