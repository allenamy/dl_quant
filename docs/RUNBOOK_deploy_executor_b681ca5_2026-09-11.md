# RUNBOOK · 把执行器 b681ca5 部署到运行树 `~/dl_quant_live`(部署 = 用户裁定后才执行)

> **创建:** 2026-09-11 02:2xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 远端 `origin/main` = **b681ca5** 已合并(收据 `docs/POSTMORTEM_b0a573a1_15_rounds_2026-09-11.md` §1); 运行树 **d040c74 未部署**; 本文 = 部署那一刻要做的全部动作, 谁执行都一样 | **作废条件:** 运行树 HEAD = b681ca5 且首锚验收(§3)写进 journal 后, 本文只作回滚参考
> **协议来源:** 用户 09-09 令「合并 ≠ 部署」; 研究员第十五轮 limits「Merge recommendation requires no production checkout update or automatic deployment」。**没有用户明字「部署」, 不做 §1。**

## §0 前提(五条全部为真才动手; 任一为假 ⇒ 停, 写 STATE)

| # | 条件 | 命令 / 判据 |
|---|---|---|
| 1 | 用户明字「部署」(本轮 09-11 02Z 尚未给) | STATE.md 最新一行有「用户字: 部署 b681ca5」 |
| 2 | 时间窗: **不在锚小时(00/04/08/12/16/20Z)的 HH:00–HH:59**; 推荐 HH+1:00 → HH+3:30Z(例 01:00–03:30Z / 05:00–07:30Z); 且上一锚已收尾 | `tail -1 ~/dl_quant_live/state/anchor_runs.log` 末行含 `anchor done rc=0`; `pgrep -fl "[r]un_anchor.py"` 为空 |
| 3 | 运行树干净且可 fast-forward | `git -C ~/dl_quant_live rev-parse HEAD main` 两行都是 d040c74; `git -C ~/dl_quant_live status --short \| grep -v "state/\|rollback\|staging"` 为空; `git -C ~/dl_quant_live fetch origin main && git -C ~/dl_quant_live merge-base --is-ancestor HEAD origin/main && echo FF_OK` 打印 FF_OK |
| 4 | 远端就是复审通过的那个提交 | `git -C ~/dl_quant_live rev-parse origin/main` = `b681ca5285e9620cb6d9158d72dc2d50b2d21109` |
| 5 | 没有电池 / safe_commit 在运行目录跑 | `pgrep -fl "[r]un_acceptance\|[s]afe_commit"` 为空 |

⚠ **隐式部署陷阱(VERIFIED 读 `ops/safe_commit.sh` L23–28)**: safe_commit 在运行目录被调用时先 `git fetch origin main`, 落后就 `git rebase origin/main` ⇒ **下一次在 `~/dl_quant_live` 跑 safe_commit 会把 b681ca5 一并带入并推送 = 没人裁定的部署**。所以: 部署未裁定期间, **禁止**在运行目录跑 safe_commit(任何改动先在 worktree 分支上做, 或先裁定部署)。

## §1 动作(一条命令)

```bash
git -C /Users/haosiyu/dl_quant_live pull --ff-only origin main
```

不需要重启任何进程: 执行器由 launchd `com.dlquant.live.anchor` 每锚新起 `/usr/bin/python3 /Users/haosiyu/dl_quant_live/scheduler/run_anchor.py`, 下一锚自动加载盘上新代码; 生产者 `~/wide_shadow`(`com.hsy.shadowloop`)不在本仓, 不动。同树的其它 launchd 作业(`ops/anchor_report.py` / `ops/backfill_markout.py` / `ops/notarize_ledgers.py` / `ops/ic_monitor.py`)入口文件都不在本次 27 文件里, 各自下次运行时加载新的 `live/` 模块。

## §2 部署后立刻核(锚前, 全部离线 / 只读)

| # | 核什么 | 命令 | 期望 |
|---|---|---|---|
| 1 | 树到位 | `git -C ~/dl_quant_live rev-parse HEAD` | `b681ca5285e9620cb6d9158d72dc2d50b2d21109` |
| 2 | 代码干净, 差集就是那 27 文件 | `git -C ~/dl_quant_live status --short \| grep -v "state/\|rollback\|staging"`; `git -C ~/dl_quant_live diff --stat d040c74 HEAD \| tail -1` | 空; `27 files changed, 5098 insertions(+), 280 deletions(-)` |
| 3 | 字节冻结件未动 | `cd ~/dl_quant_live && /usr/bin/python3 ops/check_upstream_drift.py; echo rc=$?`(只读; 清单格式非 `shasum -c`) | `rc=0`(五个 A-set 文件 = 清单指纹; 电池里同一门 `tests_drift_gate`) |
| 4 | 可编译 | `cd ~/dl_quant_live && /usr/bin/python3 -m compileall -q live scheduler ops signal` | 退出 0 |
| 5 | 烟测(无网络) | `cd ~/dl_quant_live/live && /usr/bin/python3 tests_request_identity_unknown.py \| tail -2`; 同法 `tests_static_names.py`, `tests_transport_resilience.py` | 378 / 全过 |
| 6 | (可选, 推荐)全电池作为部署收据 | `cd ~/dl_quant_live && bash run_acceptance.sh`(读真 state, 只读; **避开锚小时 HH:20–HH:35**, `tests_entrypoint_wiring` 读墙钟) | 132/132; 研究员 limits 明写「无独立 132 电池」, 这一次就是补那一件 |

## §3 首锚验收(部署后第一个锚; 深查模板 ①–⑦ 之外加这些; 写进当日 journal)

1. `state/anchor_runs.log` 末行 `anchor done rc=0`; `state/live/watchdog/last_eval.json` `tripped=False`, `metric_errors=[]`。
2. 当锚 `orders.jsonl`(rid 过滤): 带 `request_ledger` 的 maker 行数 **> 0**(有场所事实的 maker 行带账本 = 第 11 轮合同); `inconsistent` / `venue_inconsistent` / `filled_amount_unknown` 行数(期望 0; **非 0 不是缺陷, 是场所事实不可读被如实记下 —— 看那一行, 不看总数**); 补单行带 `avg_fill_px_children`。
3. 当锚 `anchors.jsonl` 的 `neutrality_price`: 有 `n_fills_measured` / `coverage_measured_notional` / `measured_over` 键; bps 为 None 时三桶(unpriced / fee_unknown / measured)能解释。
4. `ops/verify_reshape_anchor.py` 输出的 neutrality 行引用「已测」口径(第 15 轮改的读者)。
5. guard_twin / anchor_report 照常出报(同树代码, 入口未改)。
6. **深查模板固定新增一项**: `git -C ~/dl_quant_live rev-parse --short HEAD` 与 `git -C ~/dl_quant_live rev-parse --short origin/main` 相同; 不同 = 运行树落后 = 有未部署改动, 照常报, 不动作。

## §4 部署后的第二件事(另裁, 不与部署同锚)

09-09 12Z 崩溃锚(E-0909-D)的 52 行 `reconstructed` 写回: 现网 d040c74 的 `pilot_log.ORDER_TYPES` 不含该类型, b681ca5 含。写回按 E-0909-G 规则: **先在账本副本上过看门狗**(`watchdog.evaluate(副本根)` tripped=False)再写真账本, 且在锚窗外。写回改变 09-09 当日 M1/M4 的分母(§POSTMORTEM 4d)。

## §5 回滚(已排演 02:1xZ, scratch 共享克隆; 排演收据: revert 19 提交 ⇒ 27 文件 +280/−5,098, `git diff d040c74` = 0 文件)

```bash
git -C /Users/haosiyu/dl_quant_live revert --no-commit d040c74..b681ca5 \
 && git -C /Users/haosiyu/dl_quant_live commit -m "rollback: executor tree back to d040c74 (revert d040c74..b681ca5)" \
 && git -C /Users/haosiyu/dl_quant_live push origin main
```

- 结果: 盘上代码逐字节 = d040c74, 历史线性, safe_commit 不受影响; 下一锚自动用旧代码。
- **禁** `reset --hard` / force push: 与 origin 分叉后, 下次 safe_commit 的 rebase 会把 b681ca5 再拉回来。
- 回滚后账本兼容: 新码写的行多出的键(`request_ledger` 等)旧码读者按 `dict.get` 忽略(旧读法 = 第 11 轮前的行读法, 无异常); **若 §4 的 52 行已写回再回滚, 旧码读者对 `reconstructed` 行的行为未测(UNRESOLVED)⇒ §4 只在确认不回滚后做**。

## §6 部署前验收三件(研究员第十五轮要求; 02:07–02:12Z 已做, 细表 `docs/POSTMORTEM_b0a573a1_15_rounds_2026-09-11.md` §4a)

| 件 | 做法 | 结果 |
|---|---|---|
| 账本副本旧 / 新对照 | 09-09→09-11 三日 12 锚账本副本(02:07:54Z), 旧树 d040c74 与新树 b681ca5 各自 `anchor_loop.neutrality_price` + `ops/chase_readout.collect` | bps 12/12 逐锚相等(含两个 None); collect 共有键 0 差, 新版只多三桶/覆盖率键 |
| 历史行兼容 | 全量 42 日账本副本(08-01→09-11, 02:08:24Z)跑两树 `watchdog.evaluate()` | 输出逐键 0 差(`evaluated_utc` 除外); tripped False; `cond7_ops` 两侧同为 blind = 离线未注入 ops_stats 的装置效应 |
| 回滚排演 | 共享克隆里 `revert --no-commit d040c74..b681ca5` | 树 = d040c74(0 文件差) |

## §7 数字标签
提交号 / 文件数 / 行数 / 12 锚 bps / 42 日 0 差 / 排演数字 = VERIFIED(本机 02:04–02:12Z); 「其它 launchd 作业入口不在 27 文件内」= VERIFIED(plist `ProgramArguments` 逐个读); 「旧码读者忽略新键」= 按码读 INFERRED(未逐读者跑); `reconstructed` 行回滚兼容 UNRESOLVED。
