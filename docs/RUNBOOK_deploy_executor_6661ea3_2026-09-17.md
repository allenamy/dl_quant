# RUNBOOK · 把执行器 6661ea3 部署到运行树 `~/dl_quant_live`(用户裁定 2026-09-17 ~01:5xZ「再次 double check, 确保无误, 可以更新执行侧到最新的版本, 并推送到远端分支, 实盘生效」)

> **创建:** 2026-09-17 02:0xZ | **Session:** 0134cBjSFjjurUhAz95RNuWk | **状态:** 执行中(每步实测值就地回填) | **作废条件:** 运行树 HEAD 不再是 6661ea3(回滚或后继部署), 本文降为历史 | **前一份:** `RUNBOOK_deploy_executor_b681ca5_2026-09-11.md`(格式与纪律沿用)

## §0 前提(五条全部为真才动手; 任一为假 ⇒ 停, 写 STATE)
| # | 前提 | 核法 | 实测(02:0xZ) |
|---|---|---|---|
| 1 | 用户裁定部署 | 本轮用户字 | ✅ 「可以更新执行侧到最新的版本, 并推送到远端分支, 实盘生效」 |
| 2 | 时间窗: 非锚小时 HH:00–HH:59; 推荐 HH+1:00→HH+3:30Z; 上一锚已收尾 | `tail -1 state/anchor_runs.log` | ✅ 00Z 锚 `00:57:30Z anchor done rc=0`; 窗 01:00–03:30Z; 下一锚 04:00Z(run_anchor 整点起, 04:24Z 读书交易) |
| 3 | 运行树干净且可 FF | `git status --short \| grep -v "state/\|rollback\|staging\|BATTERY.lock"` 为空; 6661ea3 是 ef60f85 后裔 | ✅ 脏文件 23 个**全在 state/**(账本, 跟踪但两版本零差异 ⇒ FF 不触碰); 新增 130 文件零撞路径; 修改集∩脏文件 = 0; 后裔 yes(60 提交) |
| 4 | 远端 = 复审通过的提交 | `git ls-remote origin main` | 部署前 origin/main = ef60f85(= 运行树); **本步骤把 6661ea3 推成 origin/main, 再 `pull --ff-only`** —— 与 09-11/09-13 同法, 运行树始终 = origin/main |
| 5 | 无电池 / safe_commit 在运行目录跑 | `pgrep -fl "[r]un_acceptance\|[s]afe_commit"`; `BATTERY.lock` | ⏳ 叠加树电池(head 6661ea3, 01:47:59Z 起)收工并释放锁后再动 |

**复审状态**: 独立研究员五轮(28c1f208 / 47061580 / 7a05b4f4 / 1004d6d6)——六件原始反例 + 四条边界 + 恢复路径全部翻转并独立验证(27 断言 / 23/23 / 60/60 / 两次电池 161 套一致), 「未发现新的阻断性执行器问题, 可以收口」; 同时明言「代码收口 ≠ 部署条件满足: 真漂移 / 防休眠 / 凭据加载仍需验收」—— 三项在本 runbook §2/§5 逐一处理, **由用户裁定推进部署**。

**三红在生产语境的读法(部署决策依据)**:
- `drift_gate` / `tests_drift_gate`: `pilot_metrics.py` 方向 **production→research**(执行器是上游, 研究仓 `multi_asset/engine/live/pilot_metrics.py` 5ac7b16d 落后于 6661ea3 的 cd508c3f)。**不是执行器缺陷**; 修法 = 部署后把执行器文件 re-vendor 到研究仓(§5), 不改门。
- `tests_entrypoint_wiring`(nosleep): `ok=False … power=AC log_verified=False guard_age_h=58` —— 守卫 `caffeinate -ims`(launchd `com.dlquant.live.nosleep`, pid 815)**在**且 AC, 红的是「睡眠日志没读到」(NOSLEEP-1, `pmset -g log` 超时), 是证据层而非守卫失效。部署不改变这一项; 修复另列(R16R §5)。
- `tests_env_loading` UNAVAILABLE: 叠加树按规矩无 `.env`; 生产树有(`.env` 存在且 gitignored) ⇒ **§2 的生产电池会真跑这一套**。

## §1 动作(两条命令, 顺序固定)
```
# (a) 复审通过的提交推成远端 main(FF: 远端 main=ef60f85 是其祖先)
git -C <叠加树> push https://github.com/allenamy/dl_quant_live.git 6661ea3:refs/heads/main
# (b) 运行树只 fast-forward 到 origin/main(与 09-11 runbook §1 同一条命令)
git -C /Users/haosiyu/dl_quant_live pull --ff-only origin main
```
禁 `reset --hard` / force push / 在运行目录跑 `safe_commit.sh`(它会 rebase)。

## §2 部署后立刻核(锚前, 只读)
| # | 核 | 命令 | 期望 |
|---|---|---|---|
| 1 | 树到位 | `git -C ~/dl_quant_live rev-parse --short HEAD origin/main` | 两行 6661ea3 |
| 2 | 差集就是那 185 文件, state/ 未动 | `git diff --stat ef60f85 HEAD \| tail -1`; `git status --short \| grep -v "^??"` 仍只有 state/ | 185 files; 脏文件集合与部署前逐字相同 |
| 3 | 关键文件字节 = 叠加树 | `shasum` live/binance_broker.py scheduler/anchor_loop.py scheduler/run_anchor.py live/watchdog.py ops/daily_summary.py | 与叠加树 6661ea3 相同 |
| 4 | `.env` 未动、可读 | `git check-ignore .env`; `tests_env_loading` 在 §2.6 | ignored; 套件绿 |
| 5 | launchd 入口未变 | `com.dlquant.live.anchor` ProgramArguments | `python3 ~/dl_quant_live/scheduler/run_anchor.py`, cal 00/04/…:00 |
| 6 | **生产电池作为部署收据** | `cd ~/dl_quant_live && ACCEPT_PY=/usr/bin/python3 bash run_acceptance.sh`(读真 state, 只读; 避开锚小时) | 相对叠加树 157/3/1: `tests_env_loading` 应转绿; 其余逐套件同; **任何新红 ⇒ 立即按 §4 回滚** |
| 7 | 漂移门 | §5 re-vendor 后 `python3 ops/check_upstream_drift.py` | exit 0 |

## §3 首锚验收(04:00Z run / 04:24Z 交易; 深查模板 ①–⑦ 之外加)
1. `state/anchor_runs.log` 末行 `anchor done rc=0`, 且该锚的 anchors 行 / readback / orders 正常写入(比例响应开关 ON 下无误触发)。
2. 看门狗 `last_eval.json`: tripped=False(除非真有事), `cond2_day_loss` 非 blind。
3. 深查模板固定新增一项: `git -C ~/dl_quant_live rev-parse --short HEAD` == `origin/main` == **6661ea3**; 不同 = 落后/被改, 照常报不动作。
4. 新代码首次实盘路径: `submit_refused_nonfinite_quantity` / `derisk_unknown` 等新动作**预期为 0 条**(没有 NaN 就不该出现); 出现 = 真有未知仓位, 按已知处置规则报。

## §4 回滚(已排演 02:0xZ, 临时克隆: 树差 0 文件, 可 FF, state/ 零触碰; 不 revert —— 链里有 merge 提交)
```
RB=$(git -C ~/dl_quant_live commit-tree "$(git -C ~/dl_quant_live rev-parse ef60f85^{tree})" -p 6661ea3 \
     -m "rollback: executor tree back to ef60f85 (tree swap on top of 6661ea3; forward commit, no force push)")
git -C ~/dl_quant_live merge --ff-only "$RB" && git -C ~/dl_quant_live push origin main
```
回滚后 `git diff ef60f85 HEAD --name-only` 必为空。旧码读者对新码写的行: 新键按 `dict.get` 忽略(与 09-11 同判断, INFERRED 未测)。

## §5 漂移 re-vendor(方向 production→research; 门的规则「do NOT fix the local copy」)
```
cp ~/dl_quant_live/live/pilot_metrics.py ~/Desktop/quant_research/multi_asset/engine/live/pilot_metrics.py
# 研究仓提交(显式路径); 然后 ~/dl_quant_live: python3 ops/check_upstream_drift.py ⇒ exit 0
```

## §6 记录(部署后同步, 防版本混乱与「灾难性遗忘到有问题的版本」)
STATE.md 顶部新条(运行树 6661ea3, 时刻, 链, 电池, 回滚命令) · FIXPROGRAM §45 · HANDOFF_R16RF §7.6 · 记忆: `offschedule_run_flattens_the_whole_book_i6`(「修复在克隆未部署」→ 已部署)· `review_b0a573a1_closure…`(运行树 → 6661ea3)· `derisk_late_reference_rule`(未部署 → 已部署)· `independent_review_no_evidence_chain…` · MEMORY.md 索引行 · 每锚深查模板附注「本纲领无任何代码修复已部署(仍 ef60f85)」**需用户更新 cron 文本**(那是用户侧的模板, 不在仓库里)。

## §7 实测回填
(待 §1–§2 执行后逐行写: 推送时刻 / FF 时刻 / HEAD / 电池计数 / 漂移门 / 首锚)

### §7.0 叠加树终验(02:03:54Z 收工, head 6661ea3): 156/5/1 — 相对 01:05Z 多一红 tests_alarm_digest [E] 'only 7 readable alarms in 24h — NOT OBSERVABLE'; 定因 = 叠加树 state/notify_audit.jsonl 是 09-16 08:24Z 静态快照(最新行 04:45Z), 近 24h 仅 7 行 < 阈值 8, 随钟衰减(ENVRED-2); 生产实时文件近 24h 46 行。d580eb5→6661ea3 只改 docstring + 一个测试出口, 与 alarm_digest 无关。判定: 非代码红, 由 §2.6 生产电池在真实文件上复核。
- 02:06:18Z §1(a) push 完成: origin main ef60f85 → 6661ea3 (远端确认: 6661ea3)
- 02:06:20Z §1(b) 运行树 FF 完成: HEAD=6661ea3 origin/main=6661ea3
- 02:06:20Z §2.1 ✓ HEAD=origin/main=6661ea3
- 02:06:21Z §2.2 diff ef60f85..HEAD: 185 files changed, 21653 insertions(+), 389 deletions(-); 脏文件(非 state/rollback/staging/lock): 1(期望 0); 脏 state 文件数 22(部署前 23)
- 02:06:21Z §2.3 ✓ 六个关键文件字节 == 叠加树 6661ea3
- 02:06:21Z §2.4 ✓ .env 在且 ignored, 未被 FF 触碰(mtime 2026-08-01T10:20)
- 02:06:21Z §2.5 ✓ launchd 入口不变: /usr/bin/python3 /Users/haosiyu/dl_quant_live/scheduler/run_anchor.py (整点 00/04/08/12/16/20Z)
- 02:08:29Z §2.2 补核: 那 1 个非 ' M state/' 条目 = ' D state/alarm_episodes/artifacts.json'(state 文件, D 状态码, 部署前即如此); 部署后脏文件 23 个全在 state/ ✓ 与部署前集合一致
