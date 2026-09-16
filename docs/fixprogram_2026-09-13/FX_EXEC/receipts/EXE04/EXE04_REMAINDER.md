> **创建:** 2026-09-16 | **Session:** FX-EXEC | **状态:** 具名余项(lead 裁定方案 (a): 只建核, 停在接线与回放之前) | **作废条件:** 下列任一项落码并过独立复审后, 对应行作废

# EXE-04 / Q6 具名余项 — 本轮**没有**做的部分

本轮交付 = 纯联合可行性核 `live/reconcile_carry.py` + 验收套件 `live/tests_reconcile_carry.py`(35 格, 绑研究员网格)。
**在役缺陷一行未动**: `live/reconcile.py:693-720, 848` 仍逐窗以场所观察量为新基准, §4-5b/5e 仍读 |e_t|。
红证据(真 reconcile(), 非新核): `EXE04_red_on_live_reconcile.log` —— 窗 1 残差 30 报 anomaly, 窗 2
`expected_qty = 80.0`(= 上一窗的**观察**值)⇒ 残差 0、0 anomaly。那 30 既未被解释也未被结清, 只是被吸收进基准。

## 1. 执行器接线(书行为改动; 需用户字 + 41 天回放 + 独立复审)
| # | 项 | 出处 | 说明 |
|---|---|---|---|
| R1 | `reconcile()` 输出 `carry_by_symbol`(E_s 轨迹)与 `pending_requests`(P_s) | PREREG §2 | 新键; 既有键不动 |
| R2 | `position_break` §4-5b/5e 改读 \|E_s\| 而非 \|e_t\| | PREREG §2 | **这一条改变风控接受域** |
| R3 | `state/live/pending_requests.jsonl` 写出器(非终态请求, 追加) | PREREG §2 | 执行器行写出时 |
| R4 | 下锚阶段 B 按 client id 查终态(`GET /fapi/v1/order`), 终态 ⇒ 追加 `reconstructed` + `supersedes_client_id` 修正行 | PREREG §2 | 消费者按 supersedes 折叠, 不得双计 |
| R5 | 双时钟(事件时间 / 观察时间)与迟到证据的前缀重建 | PREREG §1.1, §1d.3 | 本轮核按「当前证据集」重算, 已具备顺序无关性; **但「当时在线收据保留、不改写」未实现** |
| R6 | 联合 checkpoint 落盘与恢复(硬约束集 + 已准入 + 被排除 + 政策身份), 重放逐位相同 | PREREG §1d.5 | 核的 `carry_state()` 返回该对象; **落盘与跨进程恢复未做** |

## 2. 回放与既有期望
| # | 项 | 出处 |
|---|---|---|
| R7 | **41 天账本副本回放**: 列出全部 E_s ≠ 0 的历史事件, 与 journal 已知事故(E-0909-D/G, E-0910-A)逐一对上; 出现未登记事件 ⇒ 先查因再部署 | PREREG §2, §3.5 |
| R8 | **既有期望逐条重新论证**: 旧 reconcile / position_break / watchdog 套件的每一条 CLEAN/BREAK 期望复核, 任何翻转必须指出解释它的合同条款 | PREREG §3.6 |
| R9 | 部署当锚若存在历史 E_s 会触发 §4-5e ⇒ 先由用户裁定「清零起点(记账起点行)」还是「先解释」 | PREREG §2 |

## 3. 核自身的已知边界(已写进模块与套件文档, 并进 gate_coverage 边界自述)
| # | 项 |
|---|---|
| R10 | 枚举随 请求数 × 锚数 指数增长; `feasible_exact` 超界**拒绝**(不回退到 unsound 边际法), 但该上界未按真实逐名请求数标定 |
| R11 | 证据下界 C_i(t) 在核里简化为**常量**(当前已知值), 而合同允许它随时间单调上升; 迟到证据通过重算整段体现, 未建模「每锚各自的 C」 |
| R12 | `feasible_marginal_UNSOUND` 留在树内作对照; 任何调用它做判决的改动都必须被视为回到修订 3 已撤回的对象 |

## 4. 与相邻项的边界(避免被读成同一件事)
- **与 W6C B13 不同**: B13 是「缺最新截面 ⇒ 读旧状态判」; Q6 是「有最新截面, 但旧未解释量不作为债项延续」。复审明确二者是两件事, 且**比例响应不能代替 Q6**。
- **与 NEW-02 不同**: NEW-02 是 fills 行的 attempt_idx 标识符错; Q6 是跨窗数量恒等式。二者都出现在平仓批上纯属巧合。

## 5. 取用外部夹具的谱系(复审可验)
`live/tests_fixtures/exe04_q6/GRID_SOLUTION_SETS.json`
- 来源(只读复制, 未 fetch / checkout / merge 该分支, 未改一字节):
  `/Users/haosiyu/Desktop/quant_research/.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_round7_review_2026-09-10/design/attempt01/GRID_SOLUTION_SETS.json`
- 分支: `agent/codex/QNT-2026-0907/onboarding-audit`(该 worktree head `d0d82862960f30ddc49bd0f29c5793530b63ebd7`)
- 该文件在来源分支上的提交: `82cbe018ba14d7aaaa29c17a352255badc097552`「Audit round7 request evidence paths and Q6 joint-state contract」(2026-09-10)
- 复制时刻: 2026-09-16T03:2xZ
- sha256: `8a2b7c9b7e309c381f7115d91d0695c37af1a1098f5e6dbd489a56b34f128926`(夹具与来源逐位相同; 套件 [G0] 格把该 sha 钉死)
