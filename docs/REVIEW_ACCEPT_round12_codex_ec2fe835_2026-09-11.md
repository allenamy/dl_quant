# 独立研究员第十二轮复审(ec2fe835)· 辩证处置 + 第十三轮修复

> **创建:** 2026-09-11 16:0xZ(09-10 UTC 晚间开始, 跨日) | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 处置已定; 第十三轮修复在实盘复审分支落码(未合并未部署), 待研究员第十三轮复核 | **作废条件:** 研究员第十三轮复核出具后以其为准
> **复审件:** `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_round12_review_2026-09-10/`(HANDOFF / executor · risk · root · design 分册; 提交 ec2fe835; 研究员自报 23 个入口 + 2,081 项核验)。**被审对象:** 实盘 84a3b51, 研究 fd386578, 主线 61a57bd9; 运行树 d040c74。
> **研究员总判:** 上一轮两项 P1 修复成立, 本轮**未确认新的 P1**; 四项 P2 需收口(金额下界遗漏 / 非有限金额漏检 / 身份字段规则不一致 / 成本报表覆盖不足); 接受 [0,Q] 为合法请求的保守数量范围(非价格/金额精确可行集, 非 Q6 完成); 132 套件本轮未独立重跑。**我方总判: 四项全真全修, 外加研究员点名的三处措辞与 §5 全表补项。**

---

## §0 一句话

第十二轮之后承重缺口清零; 剩下的是同一模型里没对称的边: 数量有的规则(下界比较、坏值必查、字段四态、未测≠零)金额和成本报表还没有。第十三轮补齐: 子成交金额**下界**(Σ 有 quote 的孩子)参与「不超终值 N」比较, 不等全集; `ledger_inconsistencies` 先查 N 有限性再看 C; 身份字段四态(缺键/None = 无证据, 空串/不可解析/非有限 = 畸形 ⇒ 矛盾, 有值 = 比对)由一个 `identity_field` 贯穿三处门; 两个成本诊断(`neutrality_price` / `chase_readout.collect`)的 bps 只按已定价成交, 未定价的 count / notional / fee 同报, 无已定价 ⇒ None 而不是 0。

没有任何一项影响策略 alpha 或回测数字; 研究员本轮亦未产生新收益结论。

---

## §1 四项 P2 + 措辞(全部接受, 全部修)

| # | 研究员发现(隔离合成) | 真因(读码 VERIFIED) | 第十三轮修复(实盘分支 5f2dd75) | 证据(`tests_request_identity_unknown.py` 325/325; 旧码上红) |
|---|---|---|---|---|
| R12-PARTIAL-N | 终值 C20/N40 + 孩子 5/N50 + 孩子 5/N 缺 ⇒ 下界 50 > 40 但 n_child 含 None 变 None ⇒ 检查跳过, 行 N90 读 70 CLEAN | `n_child` 只在所有孩子有 quote 时存在, 「不超」比较用它 | `n_lower = Σ 有 quote 的孩子` 参与「不超终值 N」; 全集等式判断才用 `n_child` | [72] 3 格(旧码 2/3 红) |
| R12-N-FINITE | 账本 C None / N NaN|Inf ⇒ `ledger_inconsistencies` 因 C 缺提前 continue, N 未查, 按数量带通过 RC | N 检查写在 C 检查之后 | N 有限性先查 | [73] 3 格(旧码 2/3 红) |
| R12-ID-SHAPE | 提交门对 origQty=NaN/Infinity/文本「不可解析 ⇒ 跳过」⇒ 精确补 6; 结算门拒; 空 side 两门方向相反 | 三处门各自实现, 「可读性」没有定义 | `identity_field(rec, key)` 四态: absent / malformed / value; `_ident_check` 一个实现贯穿提交回包门、补查门、结算的提交记录门(完整记录门 `_valid` 仍要求字段齐全) | [74] 12 格(旧码 7 红: NaN / Infinity / 文本 origQty 三处门; 空 side / 空 cid 旧门已拦 ⇒ 绿) |
| R12-COST-COVERAGE | N6 / C 与 avg 未知 ⇒ `neutrality_price` 0 bps、n_fills_priced 0; `chase_readout.collect` 0 bps; 正控 N6/C3/avg2 应 10000 bps | 分母含未定价成交, 分子按 0 adverse | bps 只按已定价成交(fee + adverse); 报 `n_fills_unpriced` / `unpriced_notional_usdt` / `fee_unpriced_usdt` / `coverage_priced`; 无已定价 ⇒ None; `chase_readout` 同 + 汇总用已定价名义 | [75] 5 格(旧码 1 红 + 崩: 旧 collect 无新键) |
| 措辞 | DESIGN §3f.1「按 A 补查」; `request_remaining` 旧 R5-QC 注释; API_SEMANTICS POST 回包字段; §5 avg 读者过窄 | — | 「先拒不补查(0 GET)」; 注释改为区间读法; POST 回包三分开(官方承诺 / 我方政策 / 实际观测: testnet 07-26 带 executedQty 缺 cumQuote/avgPrice, 其余未单独观测); §5 补 M4/M5、`neutrality_price`、`chase_readout`、`score_post_fix`、RC 残差计价与 `_unknown_interval` 后备 | — |

**边界(接受研究员裁)**: [0, Q] 是合法请求的保守数量范围, 不是价格 / 金额事实的精确可行集(正金额排除精确 0、限价可给更高下界 —— 当前合同未用), 不代表 Q6 完成; 10000 bps 是夹具尺度正控, 不是实盘成本。

## §2 Q6 / 管线
数学接受不变(字节相同); 实现与回放另排。管线参考态不变。

## §3 我方承认的新错误
1. 数量与金额的规则集不对称(第十二轮记忆里写了「少一条就是下一格」, 这一轮就是那一格: 下界比较 / 坏值必查)。
2. 「可读性」在三处门各写各的, 没有先定义四态再实现。
3. 「未测」在成本报表里被当作 0 —— 与「filled_amount_unknown ≠ 0」是同一条原则, 没有推到报表层。

## §4 状态

| 件 | 提交 | 电池 | 状态 |
|---|---|---|---|
| 实盘分支 第十三轮 | `review/b0a573a1-executor` **5f2dd75** | 132/132 全绿(notify_audit 副本 16:08Z 刷新) | 已推送, 待复核 |
| 研究分支 | fd386578 → HANDOFF §EXECUTOR 第十三轮 | — | — |
| 研究主线 | 本文 + DESIGN §3g / §5 补项 / §3f.1 措辞 + journal/STATE | — | — |

**版本配对(上一轮期望被改的格)**: [65] 身份门措辞统一(「another client id」→「clientOrderId … is not ours」, 断言接受两者)。其余 301 项原样保留。

**未闭合(明写)**: R6-MARK 动作合同; 同快照内 C×avg 与 N 一致性; 时窗核对; Q6 实现与回放; 无场所事实 maker 行走旧读法(来源前提); `_seen_syms > 1` 与 settle 整体异常出口; −2013 终局性(假设); 跨进程同秒平仓 id; M5 再封存; income 缺行/币种换算; 物理 BUNDLE_export 门; 52 行写回等部署。协议不变: 第十三轮复核 → 分别合并 → 部署另裁; 运行树 d040c74 零接触(VERIFIED)。

## §5 数字标签
研究员列数字(50/40, 6/3/2 ⇒ 10000 bps, 23 入口 / 2,081 核验)= 其复算(VERIFIED by them); 套件/电池计数与旧码红格计数 VERIFIED(本机); 其余为规则。
