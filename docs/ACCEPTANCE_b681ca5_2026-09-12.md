# ACCEPTANCE · 执行器 b681ca5 部署前验收(隔离克隆; 本代理不部署)

> **创建:** 2026-09-12 05:5xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME(team-lead 派发的验收子任务)| **状态:** 全部验收动作在 scratch 克隆完成; 运行树 `~/dl_quant_live` 本代理零写入零 git 动词(本代理最后复核 06:04Z 时 HEAD 仍 d040c74); **DEPLOY: NOT EXECUTED BY THIS AGENT** —— lead 报告已于 06:0xZ 按 §0 五前提复核后执行 ff-merge(本代理未复核), §2 核与 08Z 首锚由 lead 做 | **作废条件:** 运行树 HEAD = b681ca5 且 08Z 首锚验收写进 journal 后, 本文只作部署收据 / 回滚参考
> **上游:** `docs/RUNBOOK_deploy_executor_b681ca5_2026-09-11.md`(§0 前提 / §2 部署后核 / §3 首锚 / §5 回滚 / §6 三件)· `docs/POSTMORTEM_b0a573a1_15_rounds_2026-09-11.md` §4a · 研究员 `docs/HANDOFF_uplift_independent_review_2026-09-12.md` §5 #1(在副本跑电池 + 回滚排演 + 新旧行读者; 钉死提交, 禁浮动 pull; 避锚窗; 下一锚验收; 52 行重建另裁)。
> **机器收据:** 同名 `docs/ACCEPTANCE_b681ca5_2026-09-12.json`; 中间产物 scratch `…/scratchpad/{cmp_final/,readers/,battery_stdout.log}`(session 生命期)。

## §0 一句话

在与运行树同源的两个 scratch 克隆(旧 d040c74 / 新 b681ca5)上, 用 **05:43:50Z 刷新的真 state 快照**跑完: 前提 5/5 真; 字节冻结件 rc=0; **神经价新旧读者 19/19 锚逐位相等(09-09 00Z → 09-12 04Z, 含 3 个 None)**; **看门狗 43 日全量副本新旧输出 0 差(`evaluated_utc` 除外), tripped False**; 回滚排演 revert 19 提交 ⇒ `git diff d040c74` **0 文件**; 新行读者 `chase_readout` rc=0 打印已测口径列, `verify_reshape_anchor` 两树判据段逐字相同(rc=1 是锚的性质, 见 §6)。电池结果见 §4。

## §1 前提(RUNBOOK §0; 全部只读; 04:45:52Z 首核, 05:43:20Z 复核)

| # | 条件 | 命令 | 结果 | 真/假 |
|---|---|---|---|---|
| 1 | 运行树 HEAD = main = d040c74 | `git -C ~/dl_quant_live rev-parse HEAD main origin/main` | `d040c7444c24f945d14b14803143771146886c4b` ×2; origin/main `b681ca5285e9620cb6d9158d72dc2d50b2d21109` | 真 |
| 2 | 代码干净 | `git -C ~/dl_quant_live status --short \| grep -v "state/\|rollback\|staging"` | 空 | 真 |
| 3 | 可 fast-forward | `git -C ~/dl_quant_live merge-base --is-ancestor d040c74 b681ca5` → FF_OK; `merge-base --is-ancestor b681ca5 origin/main` → 可达; `rev-list --left-right --count HEAD...origin/main` = `0 19` | 落后 19, 领先 0 | 真 |
| 4 | 无电池 / safe_commit 在跑 | `pgrep -fl "[r]un_acceptance\|[s]afe_commit"` | 空(04:45Z, 05:43Z 两次) | 真 |
| 5 | launchd 作业与入口未变 | `launchctl list \| grep -i "dlquant\|hsy"`; 每个 plist `PlistBuddy -c "Print :ProgramArguments"` | 本仓 5 作业入口逐个读出: `com.dlquant.live.anchor`→`scheduler/run_anchor.py`, `com.hsy.anchor_report`→`ops/anchor_report.py`, `com.hsy.markout_backfill`→`ops/backfill_markout.py`, `com.hsy.notary`→`ops/notarize_ledgers.py`, `com.dlquant.live.icmonitor`→`ops/ic_monitor.py`; 均 `/usr/bin/python3`; 无一含 `git pull`(与 RUNBOOK §1 表一致); 生产者 `com.hsy.shadowloop` 等在 `~/wide_shadow`, 不在本仓 | 真 |
| — | 锚状态 | `anchor_runs.log` | 04:00Z 锚 **04:57:28Z anchor done rc=0**; `pgrep "[r]un_anchor.py"` 空(05:43Z); `state/live/watchdog/last_eval.json` tripped=False, triggers=[], metric_errors=[], 04:47:50Z, `_mode=LIVE` | 已收尾 |

RUNBOOK §0-1「用户明字部署」不在本代理判定范围(lead 持有)。

## §2 克隆(B)

| 克隆 | 路径 | HEAD(完整 sha) | 校验 |
|---|---|---|---|
| 新 | `/Users/haosiyu/cc_tmp/exec_b681_acceptance` | `b681ca5285e9620cb6d9158d72dc2d50b2d21109`(detached) | `git clone ~/dl_quant_live` → `checkout b681ca5…`; `git diff --stat d040c74 HEAD \| tail -1` = **`27 files changed, 5098 insertions(+), 280 deletions(-)`** |
| 旧 | `/Users/haosiyu/cc_tmp/exec_d040c74_old` | `d040c7444c24f945d14b14803143771146886c4b`(detached) | 同法 |
| 账本副本 | `/Users/haosiyu/cc_tmp/exec_b681_acceptance_ledger/pilot_log` | — | `rsync -a ~/dl_quant_live/state/live/pilot_log/`; `diff -rq` 与实盘 **逐字节相同**(05:43:50Z); 43 日 20260801→20260912 |

19 提交 = `961a858 … b681ca5`(`git log --oneline d040c74..b681ca5`); 27 文件 = `docs/API_SEMANTICS.md`, `live/{binance_broker,binance_executor,order_disposition,pilot_log,reconcile,venue_fills,watchdog}.py`, `live/tests_{avgpx_backfill,daily_summary,disposition_matrix,fee_asset_detection,fill_backfill,income_twin_rows,notional_backfill,numerator_honesty,reprice_day,request_identity_unknown,signal_and_loop,transport_resilience,venue_cap_clamp}.py`, `ops/{chase_readout,gate_coverage,reprice_day,verify_reshape_anchor}.py`, `run_acceptance.sh`, `scheduler/anchor_loop.py`。**无 `state/` 文件**。

## §3 state 快照(C)

- 初次: `rsync -a ~/dl_quant_live/state/ <新克隆>/state/` 04:49:51→04:50:16Z(657 MB, 含 `acceptance/` 37,606 份旧日志); 旧克隆同法 04:55:05→04:55:28Z。
- **电池前刷新**(04Z 锚收尾后): 三份同时 **05:43:34→05:43:50Z** rc=0; `notify_audit.jsonl` 行数 实盘 1818 = 克隆 1818; 账本副本 `diff -rq` = 相同。
- 为什么旧克隆也要拷 state: 首轮对照(04:52Z 副本)看门狗出现 **1 处叶差** `conditions.cond5_venue_event.5b_liquidation_anomaly.dust_floor.n_symbols_with_own_minimum: 654 → 658` —— 溯源 `live/reconcile.py:120` `len(table)`, 表来自**各树自己的** `state/live/exchange_info_cache.json`(旧克隆当时只有 git 追踪的 656 币旧版, 新克隆已拷入实盘 660 币版)。两树 state 拉平后差消失(§5-2)。**装置效应, 不是代码差**; 记在此处免得下次再当缺陷追。
- 克隆里 `live/state_root.py` 以 `REPO/state` 定根(读码 L97), 所以电池 / 读者全在克隆自己的 state 上跑, 不触实盘; 唯二读实盘绝对路径的套件 `tests_notional_backfill`(L125)/ `tests_position_break_blindspot`(L47)读的是 `~/dl_quant_live/state/testnet/pilot_log`, 只读。未拷 `.env`(凭据; `tests_env_loading` / `tests_live_install_ritual` 两分支皆自造夹具, 不需要真文件)。

## §4 电池(D)

命令: `cd /Users/haosiyu/cc_tmp/exec_b681_acceptance && bash run_acceptance.sh`(state = 05:43:50Z 快照; `ACCEPT_PY` 缺省 `/usr/bin/python3`; `ops/pyenv.sh` 私有 pycache)。**05:44:11Z → 05:59:37Z**(15 分 26 秒; 前 2 分钟与 §5 两树对照并行, 历史独跑 ≈ 11 分); 全程在 05Z 小时内, **未跨任何 HH:20–35 墙钟窗, 亦不在锚小时**(`tests_entrypoint_wiring` 第 9 套, ≈05:45Z 跑)。全文 stdout `scratchpad/battery_stdout.log`, 逐套日志 `<新克隆>/state/acceptance/20260912T054411Z_*.log`。

**结果: 130 / 132 exit 0; 2 红; 收尾行 `ACCEPTANCE: NOT GREEN — at least one suite failed`, rc=1。** 两红逐一归类(lead 三分法 (i) 产品缺陷 / (ii) state 制品 / (iii) 墙钟; 此处再分出 (iv) 克隆环境):

| 红 | 失败项 | 归类 | 证据(全部本机实测) |
|---|---|---|---|
| `tests_env_loading`(10/14) | [B] 四条「`ops/ic_monitor.py` / `ops/redeliver_alarms.py` / `ops/unseed_rehearsal_halt.py` / `scheduler/run_anchor.py` populates TELEGRAM_* on import — []」 | **(iv) 克隆环境: 克隆无 `.env`** | ① `live/envfile.py` L34–35 `ENV_PATH = REPO/.env`, [B] 在清空 TELEGRAM_* 的子进程里 import 各模块再读环境 —— 克隆根目录**没有 `.env`**(凭据文件, gitignored, 本代理刻意不拷; 运行树有, 变量名 `TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID / BINANCE_*`, 只读了名不读值)⇒ 按构造必红; ② **旧树 d040c74 同一 state 上同套件同样 10/14 红**(同四条); ③ 干预: 第三个一次性克隆(b681ca5, 同 state)放入只含同名变量、占位值的哑 `.env` ⇒ **14/14 rc=0**。运行目录跑(RUNBOOK §2-6)会绿。 |
| `tests_disposition_matrix`(38/41) | [E] 三条读**真账本**的世界性质断言: ① 「EVERY steady trading anchor's INVOLUNTARY gap is small(< 200U)」— 违例 `A1789115039`(09-11 08Z)involuntary 4504; ② 「-2027 VENUE-CAPPED residual ≤ 1% of anchor's OWN realized gross」— 违例 `A1788999840`(09-10 00Z)PIEVERSEUSDT 2239 vs 1% × 154,910; ③ 「halted / trading SEPARATION on INVOLUNTARY total」— max steady 4504 ≥ min halted 4169 | **(ii) 数据制品(不是「过期」, 是「更新」): 账本里 E-0910-A 两个场所锁锚违反了套件钉住的世界性质** | ① 三个违例锚都是 STATE 已登记的 E-0910-A 事件: 09-10 00Z(-4400 锁, 书只建 67%, gross 154,910)与 09-11 08Z(第二次锁, 73 张补单全 -4400, Σ意图 4,014U, 补单腿零成交)—— 当时跑的是 d040c74, 逐张重试写下的拒单行被读者归为 involuntary gap; ② **旧树 d040c74 的同名套件在同一 state 上同样红, 同三条**(本轮对该文件 +13 行未改这三条的判定); ③ 干预: 第三克隆把 `state/live/pilot_log/2026091{0,1,2}` 移除(≤ 09-09)⇒ **41/41 rc=0**; ④ 09-11 00:5xZ 的 132/132 是在复审工作树的 state **副本**上跑的(提交记录只写「刷新 notify_audit 副本」), 那份账本副本早于这两个锁锚 —— 所以这不是新红, 是账本长到了断言之外。 |

**Lead 独立对照(06:0xZ, 旧树克隆 `/Users/haosiyu/cc_tmp/exec_d040c74_old`, 同一 05:43Z 快照, 直接跑两套)**: 同样 rc=1, 3 + 4 条 FAIL; 三条 disposition 断言的 payload 与新树**逐字节相同**(sha256 前 12 位: `d19da6693f71` / `bea0dd249993` / `78a55480d2cc`, 两树一致)⇒ 两处红**树无关**。归因(lead 与本代理一致): (i) `tests_env_loading` — `.env` 在 `.gitignore`, 运行目录有(668 B), 克隆没有, 子进程 import 后 TELEGRAM_* 为空; 运行目录会过。(ii) `tests_disposition_matrix` — 生产账本事实: 稳态锚 `A1789115039`(09-11 08:23Z, E-0910-A −4400 锁复发, 补单腿零成交)involuntary 4,504 U > 200 U 且 > 最小停机锚整书缺口 4,169; PIEVERSEUSDT −2027 场所上限残差 ≈2,2xx U 在 `A1788999840`(账本 anchor_ts = 09-10 00:24Z, 套件归入 REBUILD 类, 实现 gross 154,910)超过自身 gross 1% 界。这些是 09-09 / 09-11 之后的真实事件打破了预注册不变量, 与树无关; 运行目录电池今后也会红, 直到该套件的分类被裁定更新(另立项)。

**两红都不在 27 文件的行为里, 与部署对象无关。** 但有一条**运维后果必须写进去**: 部署后若在运行目录跑全电池(RUNBOOK §2-6 可选项), `tests_disposition_matrix` **照样红**(真账本就含这两个锚, d040c74 同红)⇒ 预期 **131/132**; 而 `ops/safe_commit.sh` 要求电池全绿 ⇒ **下一次 safe_commit 会被这条红挡住, 直到该套件的世界性质断言按 E-0910-A 修订**(一件独立的小工程, 不属本次部署; 修法方向 = 把 `skipped_venue_lock` / -4400 拒单归入自己的类, 同 -2027 的处理)。

## §5 三件验收 + 漂移门(E / F; 今日账本, 不是 09-11 那份副本)

装置: scratch `np_tree_dump.py`(每树一个子进程, `sys.path` 只插该树的 `live/ scheduler/ signal/ ops/`, **断言 `anchor_loop / watchdog / pilot_log / pilot_metrics / chase_readout` 五模块 `__file__` 都在该树内**, 私有 `PYTHONPYCACHEPREFIX`)+ `cmp_old_new.py`(逐锚 / 逐叶比对)。同一账本副本 05:43:50Z; 两树 dump 05:44:53Z / 05:45:36Z。收据 `scratchpad/cmp_final/{dump_old,dump_new,cmp_old_new}.json`, 关键数字抄入同名 `.json`。

**E. 漂移门** `cd <新克隆> && /usr/bin/python3 ops/check_upstream_drift.py; echo rc=$?` → `no drift across 5 vendored modules (declared A-set 5, all covered)`, **rc=0**(04:48:40Z)。电池里 `drift_gate` / `tests_drift_gate` 两套件为同一门(见 §4)。

**F-1. `neutrality_price` 旧树 vs 新树, 逐锚(09-09 → 09-12 04Z, 4 日 19 锚, orders 9,105 行)**: **19/19 相等**(比对键 `deficient_side / taker_notional_needed_usdt / measured_taker_bps_same_side / n_fills_basis / n_fills_priced / notional_basis_usdt / price_usdt / price_is_lower_bound`; None==None 算相等); 且两树重算值 = 账本里 d040c74 当时写下的 `stored` 值(19/19)。

| 锚(UTC) | rid | 旧 bps | 新 bps | 基数 n | 未定价 / 费未知 | 覆盖率(已测名义) |
|---|---|---|---|---|---|---|
| 09-09 00Z | A1788913440 | 6.6121 | 6.6121 | 36 | 0 / 0 | 1.0 |
| 09-09 04Z | A1788927840 | −11.6884 | −11.6884 | 20 | 0 / 0 | 1.0 |
| 09-09 08Z | A1788942240 | 3.5548 | 3.5548 | 30 | 0 / 0 | 1.0 |
| 09-09 16Z | A1788971040 | 74.4142 | 74.4142 | 28 | 0 / 0 | 1.0 |
| 09-09 20Z | A1788985440 | None | None | 0 | — | None |
| 09-10 00Z | A1788999840 | None | None | 0 | — | None |
| 09-10 04Z | A1789014240 | −3.4919 | −3.4919 | 29 | 0 / 0 | 1.0 |
| 09-10 08Z | A1789028640 | 107.2102 | 107.2102 | 9 | 0 / 0 | 1.0 |
| 09-10 12Z | A1789043040 | −40.905 | −40.905 | 50 | 0 / 0 | 1.0 |
| 09-10 16Z | A1789057440 | −69.8349 | −69.8349 | 16 | 0 / 0 | 1.0 |
| 09-10 20Z | A1789071839 | −6.2798 | −6.2798 | 49 | 0 / 0 | 1.0 |
| 09-11 00Z | A1789086240 | −15.5005 | −15.5005 | 31 | 0 / 0 | 1.0 |
| 09-11 04Z | A1789100640 | 27.3620 | 27.3620 | 16 | 0 / 0 | 1.0 |
| 09-11 08Z | A1789115039 | None | None | 0 | — | None |
| 09-11 12Z | A1789129439 | 235.4608 | 235.4608 | 36 | 0 / 0 | 1.0 |
| 09-11 16Z | A1789143840 | 70.7170 | 70.7170 | 49 | 0 / 0 | 1.0 |
| 09-11 20Z | A1789158240 | −7.7646 | −7.7646 | 13 | 0 / 0 | 1.0 |
| 09-12 00Z | A1789172639 | 17.3848 | 17.3848 | 15 | 0 / 0 | 1.0 |
| 09-12 04Z | A1789187040 | 98.6721 | 98.6721 | 33 | 0 / 0 | 1.0 |

前 12 行与 POSTMORTEM §4a 表逐位一致; 09-11 04Z 起 7 锚为本次新增。新版只多 11 键: `n_fills_unpriced / n_fills_fee_unknown / n_fills_measured / notional_priced_usdt / notional_measured_usdt / unpriced_notional_usdt / fee_unknown_notional_usdt / coverage_priced / coverage_measured_notional / coverage_measured_count / measured_over`; 19 锚 467+ 笔补单 taker 无一未定价 / 费未知 ⇒ 新分母 = 旧分母。三个 None 锚两侧都无该侧补单 taker 成交(09-11 08Z = E-0910-A 第二次 -4400 锁, 补单腿零成交, 与 STATE 09-11 09:4xZ 记录一致)。

**F-2. `watchdog.evaluate(账本副本根)` 全量 43 日(20260801 → 20260912), 两树**: 叶级递归比对 **0 差**(`evaluated_utc` 除外; 含它 1 差); `tripped` False / False; `triggers` [] / []; `metric_errors` [] / []。(首轮 1 差 = §3 说的 exchange_info 表大小装置效应, 已拉平。)

**F-2b. `ops/chase_readout.collect(账本副本根)`, 两树**: 记录 239 / 239; **窗内(09-09 起, 19 锚)共有键 0 差**; 新版只多 14 键(`chase_{n_measured,n_unpriced,n_fee_unknown,notional_priced,notional_measured,unpriced_notional,fee_unknown_notional}` + `chase_forced_*` 同名七个)。**全账本回扫(POSTMORTEM §4d-ii 待查项, 本次顺手做了)**: 共有键差 **3 处**, 全部集中在两个 2026-08-05 锚 —— `A1785931245`(12:00Z) `chase_bps` 10.1212 → **None**; `A1785945696`(16:01Z) `chase_bps` 26.2383 → None, `chase_forced_bps` 26.6209 → None。原因按行读出: 这些补单成交 `fee_paid=0.0, fee_all_usdt=False, fee_conversion=None`(费非 USDT 且未换算), 第十四轮 b 规则「原币种混合和不是已知 USDT 费」⇒ 全部落「费未知」桶(2 笔 / $91.18; 4 + 15 笔 / $62.24 + $703.64), 已测 0 笔 ⇒ bps None 而非把 0.0 当免费。**这是文档写明的口径变化(POSTMORTEM §4b 第一行), 不是缺陷**; 全账本点估计随之 旧 +260.37 USDT / +69.01 bps → 新 +260.11 USDT / +69.22 bps(已测名义 37,576.83, 未定价 / 费未知 153.42 明写不计)。08-01 起除这两锚外无其它混合可读性锚。

**F-3. 回滚排演(新克隆, 04:49Z)**: `git revert --no-commit d040c74..b681ca5` rc=0 ⇒ 暂存区 `27 files changed, 280 insertions(+), 5098 deletions(-)`; **`git diff d040c74 --name-only | wc -l` = 0**; `git revert --abort` rc=0 ⇒ `status --short` 0 行, HEAD 仍 `b681ca5285e9620cb6d9158d72dc2d50b2d21109`。

## §6 新行读者(在新克隆的 05:43Z state 快照上, 最近 3 锚; 旧树同法对照)

| 读者 | 命令(克隆 `ops/` 内, `/usr/bin/python3`, `PYTHONDONTWRITEBYTECODE=1`) | 新树 rc | 旧树 rc | 观察 |
|---|---|---|---|---|
| `chase_readout.py` | `python3 chase_readout.py`(root = 克隆 `state/live/pilot_log`, 无 override, 不写审计) | **0** | 0 | 239 锚 / 227 in-sample; 逐锚表新增 `measured$` 列(09-11 20Z 162.75 / 09-12 00Z 206.75 / 09-12 04Z 1011.42 = 全部已测); 点估计行按第十五轮文案「已测 37,576.83; 未定价/费未知 153.42 不计入成本, 不是零成本」 |
| `verify_reshape_anchor.py A1789158240` | 09-11 20Z | **1** | 1 | 判据段两树 `diff` **逐字相同**; FAIL 在【判据 1】`\|INTENT net\| = 7033.00 USDT (门槛 < 1.00)`, 判据 2 / 3 PASS |
| `verify_reshape_anchor.py A1789172639` | 09-12 00Z | **1** | 1 | 同; 判据 1 `12810.60 USDT` FAIL |
| `verify_reshape_anchor.py A1789187040` | 09-12 04Z | **1** | 1 | 同; 判据 1 `1706.83 USDT` FAIL(`sum(target_w)=−0.00728`, `sum\|target_w\|=1.06996`, 10 名被撤) |

- **rc=1 是锚的性质不是读者的**: 旧树 d040c74 对同三锚给出逐字相同的判据段与同样 rc=1 —— 【判据 1】按 maker 行 `target_w` 求和判 INTENT 中性, 外部书(combo)锚上 `sum|target_w|` ≈ 1.07 且撤名后 net 非零, 该判据是为内部 DL 书写的; 本轮 27 文件未改判据段(`diff` 证)。**不在本次验收范围, 照报不动作。**
- 【附】中性价格段是第十五轮改的读者: 对 d040c74 写的行(无 `n_fills_measured`)正确走「旧记录」分支: `该侧实测 taker 98.67bps (旧记录: 基于 33 笔 / $1422.17, 无三桶)` + `(下界, 只按已测成交)`; 旧树打印 `(基于 33 笔 / $1422.17)` + `(下界)`。数字相同。部署后 08Z 锚的行将带三桶 ⇒ 走非旧记录分支(RUNBOOK §3-4 当锚验)。
- **观察到一处文案重复(P3, 非阻断)**: 新版【附】段把 `欠缺侧 BUY 需要 taker 名义 …` 打印两次 —— `main()` L207–208 自己打一行, `neutrality_lines()` L76 又以它作首行。旧树只打一次。不改数字, 不改 rc; 记下留后修。

## §7 部署命令(G; 由 lead 亲手执行; 钉死完整 sha, 不用浮动 `pull origin main`; 窗口 05:00–08:15Z, 避 08:00 起锚小时)

```bash
# 0. 前提复核(全部只读; 任一不符 ⇒ 停)
git -C /Users/haosiyu/dl_quant_live rev-parse HEAD main                       # 两行 d040c7444c24f945d14b14803143771146886c4b
git -C /Users/haosiyu/dl_quant_live status --short | grep -v "state/\|rollback\|staging"   # 空
tail -1 /Users/haosiyu/dl_quant_live/state/anchor_runs.log                    # 含 "anchor done rc=0"
pgrep -fl "[r]un_anchor.py\|[r]un_acceptance\|[s]afe_commit"                  # 空

# 1. 部署 = 钉死提交的 fast-forward(RUNBOOK §1 的浮动 pull 由此三行替代)
git -C /Users/haosiyu/dl_quant_live fetch origin
git -C /Users/haosiyu/dl_quant_live rev-parse origin/main                     # 必须 = b681ca5285e9620cb6d9158d72dc2d50b2d21109; 远端已动 ⇒ 停, 不部署别的对象
git -C /Users/haosiyu/dl_quant_live merge --ff-only b681ca5285e9620cb6d9158d72dc2d50b2d21109
git -C /Users/haosiyu/dl_quant_live rev-parse HEAD                            # 期望 b681ca5285e9620cb6d9158d72dc2d50b2d21109

# 2. 部署后立刻核(RUNBOOK §2, 只读 / 离线)
git -C /Users/haosiyu/dl_quant_live status --short | grep -v "state/\|rollback\|staging"          # 空
git -C /Users/haosiyu/dl_quant_live diff --stat d040c74 HEAD | tail -1                            # 27 files changed, 5098 insertions(+), 280 deletions(-)
cd /Users/haosiyu/dl_quant_live && /usr/bin/python3 ops/check_upstream_drift.py; echo rc=$?       # rc=0
cd /Users/haosiyu/dl_quant_live && /usr/bin/python3 -m compileall -q live scheduler ops signal; echo rc=$?   # rc=0
cd /Users/haosiyu/dl_quant_live/live && /usr/bin/python3 tests_request_identity_unknown.py | tail -2   # 378 全过
cd /Users/haosiyu/dl_quant_live/live && /usr/bin/python3 tests_static_names.py | tail -2
cd /Users/haosiyu/dl_quant_live/live && /usr/bin/python3 tests_transport_resilience.py | tail -2
# (可选, RUNBOOK §2-6) 运行目录全电池作部署收据: cd /Users/haosiyu/dl_quant_live && bash run_acceptance.sh   # ≈11 分钟; 必须在 08:05Z 前结束(避开 08:20–08:35Z 墙钟)
```

不重启任何进程(launchd `com.dlquant.live.anchor` 每锚新起 `run_anchor.py`, 08Z 锚自动加载盘上新代码; 其余 4 个本仓作业入口文件不在 27 文件内)。

**§3 首锚验收(08Z 锚, 08:23Z 起跑, ~08:55Z 收尾; 写进当日 journal)**:
1. `tail -1 state/anchor_runs.log` 含 `anchor done rc=0`; `state/live/watchdog/last_eval.json` `tripped=False`, `metric_errors=[]`。
2. 当锚 `orders.jsonl`(rid `A1789201440` 预期; 以实际为准): 带 `request_ledger` 的 maker 行数 **> 0**; `inconsistent` / `venue_inconsistent` / `filled_amount_unknown` 行数(期望 0; 非 0 看那一行, 不看总数); 补单行带 `avg_fill_px_children`。
3. 当锚 `anchors.jsonl` 的 `neutrality_price` 有 `n_fills_measured / coverage_measured_notional / measured_over` 键; bps 为 None 时三桶能解释。
4. `ops/verify_reshape_anchor.py <rid>` 的【附】段走非「旧记录」分支(打印 `已测 N 笔 / $…; 覆盖 名义 … / 计数 …`)。
5. guard_twin / anchor_report 照常出报。
6. `git -C ~/dl_quant_live rev-parse --short HEAD` = `rev-parse --short origin/main`(深查模板固定项)。

**§5 回滚(RUNBOOK 原文逐字; 已在克隆排演 = 0 文件差)**:

```bash
git -C /Users/haosiyu/dl_quant_live revert --no-commit d040c74..b681ca5 \
 && git -C /Users/haosiyu/dl_quant_live commit -m "rollback: executor tree back to d040c74 (revert d040c74..b681ca5)" \
 && git -C /Users/haosiyu/dl_quant_live push origin main
```

禁 `reset --hard` / force push(与 origin 分叉后 safe_commit 的 rebase 会把 b681ca5 再拉回来)。回滚后新码写的多余键旧读者按 `dict.get` 忽略(按码读 INFERRED); `reconstructed` 行回滚兼容 UNRESOLVED ⇒ 52 行写回(RUNBOOK §4)只在确认不回滚后另裁。

## §8 未做 / 边界(明写)

- 未部署, 未在运行目录跑任何东西(含电池), 未碰 pod2, 未调场所 API, 未跑 safe_commit。
- 电池在克隆的 state **快照**上跑, DRY_RUN 根 = 克隆 `state/`; 与运行目录电池(RUNBOOK §2-6, 可选)不是同一件收据 —— 研究员 limits「无独立 132 电池」由本次补上一半(独立树), 运行目录那一半留给部署后。
- `verify_reshape_anchor` 判据 1 在外部书锚上恒 FAIL(旧新同)= 既有问题, 登记不处置; 文案重复 P3 登记不处置。
- 全账本回扫只做了 `chase_readout.collect`(两 08-05 锚费未知); `neutrality_price` 全账本回扫未做(只做 09-09 起 19 锚)。
- 数字标签: 前提 / sha / 文件数行数 / 19 锚 bps / 43 日 0 差 / 排演 0 文件 / 读者 rc = **VERIFIED**(本机 04:45–05:5xZ 直接计算); 三个 None 锚的原因 = INFERRED(时间线); 判据 1 为「内部书判据」的解释 = 按码读 INFERRED。

## §9 判定

**GO(电池红两处均为树无关, 见 §4)**(部署 b681ca5 到运行树, 由 lead 按 §7 钉死 sha 执行)。理由: 前提 5/5; 今日账本 19/19 锚神经价新旧逐位相等 + 43 日看门狗 0 差 = **正常态零差在今日账本上再次成立**; 回滚排演 0 文件差, 一条命令可退; 漂移门 rc=0; 电池 130/132 且两红都被证明是克隆环境(无 `.env`)与账本里的 E-0910-A 事件(旧树同红, 干预后全绿), 不是 27 文件的行为; 新读者可跑。**GO 附两条不阻断的登记**: (a) 部署后运行目录电池会因 `tests_disposition_matrix` 停在 131/132, 下一次 safe_commit 被挡, 需另修该套件; (b) `verify_reshape_anchor` 判据 1 在外部书锚上恒 FAIL(旧新同)+ 【附】段重复一行(P3)。

**DEPLOY: NOT EXECUTED BY THIS AGENT.**
