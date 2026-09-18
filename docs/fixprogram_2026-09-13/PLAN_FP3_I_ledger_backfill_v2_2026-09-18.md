# FP3 I 计划 v2: 历史账本回填 —— 独立真值与本地推导分列, 只读专用凭证, 补 08-02 OTHER — 2026-09-18

> **创建:** 2026-09-18 02:2xZ | **Session:** b9646a9e(主研究员) | **状态:** 计划(未取数、未改账本、未持有任何凭证) | **作废条件:** D v4 收据被更正; 用户否决回填范围或凭证方式
> **取代:** `PLAN_FP3_I_ledger_backfill_2026-09-17.md`(v1, sha 7b81d871…)——v1 有三处独立复审(R7-C3)指出的缺陷: ① I-3 用本地 fills 重算 COMMISSION 再当「场所真值」验收 = 循环验证; ② 要求生产 `.env` 交易权限密钥; ③ 漏 08-02 08Z OTHER 缺口(22 名 / 1,009.30 USD)。v1 保留原字节, 顶部已加作废横幅。
> **来源:** `RESULT_FP3_D_cash_reconciliation_v3_2026-09-18.md` §1–§2, `FP3_receipts/CASH_RECON_20260801_20260917_v3.json`; 复审 `REVIEW_FP3_ROUND7_codex_independent_2026-09-18.md` §4 R7-C3。

## 0. 原则(先于清单)
1. **两列分开, 永不互相生成**: 「场所真值」列只能来自场所自己的记录(income / userTrades / 账户快照导出); 「本地推导」列来自 fills/orders/readback 重算。D 引擎的判词只比较两列, **不允许用本地推导改写场所真值列**(v1 的 I-3 作废)。
2. **凭证**: 只用**只读 API key**(场所侧权限勾选只有「读取」, 无交易/划转), 或账户持有人自行导出的 CSV(交易历史 / 资金流水 / 资金费历史)。**不得用带交易权限的生产密钥替代, GET 也不行**(用户字, 09-18)。没有只读凭证之前, 本计划只能停在「清单已列」。
3. 取数在锚外窗口(避开 N+24…N+47 分钟), 请求计权与响应 sha 入收据; 原始响应原样落盘, 派生表另存。
4. 改账本只在**副本**上做, 副本过看门狗 + `assert_anchor_artifacts` 全绿后才谈替换; 原文件按日备份 `*.pre_backfill_<sha8>`; 每条回填行带 `source`、`backfilled_utc`、真实 `trade_id`/`tranId`。
5. 不改任何策略/执行行为。

## 1. 清单(逐项; 全部来自 D v3 收据)
| # | 缺口 | 范围 | 场所真值来源 | 本地推导 | 关闭判据(D v4 引擎在副本上重跑) |
|---|---|---|---|---|---|
| I-1 | 整书平仓成交不在 fills.jsonl | 8 桶: 08-01 20:19Z, 08-02 04:19Z, 08-05 00:20Z, 08-05 12:19Z, 08-21 12:17Z, 08-21 20:17Z, 08-26 12:49Z, 09-06 08:49Z(09-09/09-12 已记账) | `GET /fapi/v1/userTrades` 逐名, 窗口 [事件−15 min, 事件+10 min]; 名单 = 该桶回读 `ladder_flatten@post_flatten` 中 qty→0 的名 | 回读 qty 差 × 平仓时中价(只作对照) | 仓位重建 vs 回读 281/281 一致; 平仓桶已实现盈亏与场所 income REALIZED_PNL 同窗一致 |
| I-2 | 单名止损成交未记 | 18 锚(08-03…08-19, 各 1 名, 20–374 USD) | 同上, 逐名逐锚窗口 | 同上 | 单名不一致 → 0 |
| **I-2b(新)** | **08-02 08Z OTHER 缺口** | 22 名 / 1,009.30 USD, 不属平仓桶也不属单名止损(v3 分类 OTHER) | 先取证: 该锚 `orders.jsonl` / `anchors.jsonl` 的 rc、`known_gaps`、执行日志; 再按 userTrades 同窗核 | — | 归类到既有类或立新类, 带受据; 不允许留 OTHER 关闭 |
| I-3(改) | daily_nav COMMISSION 少计(09-12 前 BNB 数量当 USDT) | 08-03…09-11 共 31 天, 估 283 USDT | **`GET /fapi/v1/income?incomeType=COMMISSION`(逐笔, 含 asset)** 与 BNB 当时价 | fills commission × 资产 × 当日收盘(现 v3 的做法) | 两列逐日差 ≤ 1 USDT; daily_nav 原行**不改写**, 以 `ledger_amendments.py` 追加修订行且修订值来自场所列 |
| I-4 | 资金费 read_age 偏差 | 3 天 > 2 USDT(08-25, 09-02, 09-09) | `income?incomeType=FUNDING_FEE` 逐结算行(3 个月内可取) | funding.jsonl | 只作注记; 不改 funding.jsonl |
| **I-5(新, D v4 需要)** | NAV 窗口的**同时刻**持仓/标记快照 | 09-07 起 10 个日窗的 22 USDT 残差 | 账户快照导出(若有)或 `GET /fapi/v3/account` 在 NAV 时刻的历史不可回取 ⇒ 只能对**今后**窗口做: 在 daily_nav 落盘同一调用里记 read_ts | — | 今后窗口 |rt − nav_ts| ≤ 60 s; 历史窗口标 UNAVAILABLE_TIMING 而不是猜 |

## 2. 执行顺序与 ETA
1. 用户提供只读凭证或导出(阻塞项; 我不能自造)。2. 取数脚本(只读, 原始响应落盘)0.25 d。3. 副本回填 + 看门狗 0.25 d。4. D v4 引擎重跑两份收据(回填前/后), 独立复审。
