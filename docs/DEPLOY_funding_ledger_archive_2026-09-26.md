> **创建:** 2026-09-26 17:3xZ(提交 72027a9b9 17:32:33Z;原写 17:4xZ 有误) | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** 部署包,**由 lead 执行安装**,news2 不碰任何实盘/launchd | **作废条件:** `archive_live_ledger.py` 或 `venue_quiet_window.py` 的 sha 与本文不符;或设计 `docs/DESIGN_live_funding_ledger_archive_2026-09-25.md` 被改写

# 部署包:活账本归档作业 `com.hsy.funding_ledger_archive`

批准:`docs/DECISION_RULE_D10_stage2_2026-09-26.md` §3(「fix-pkg-d 发布完成之后的下一个静默窗部署,先交 §7b 的 2 条正控、9 条红控收据」)。fix-pkg-d 已于 09-26 01:19Z 发布(d01e35d)。

## 0. 这次比 4cf4de90c 多了什么(rev 1),以及为什么

打包时我按「launchd 上下文里会怎样」重读了 rev 0,找到四处不能照原样装的地方:

| # | rev 0 的行为 | 后果 | rev 1 |
|---|---|---|---|
| 1 | 守卫路径写死在 `~/Desktop/quant_research/...`,而且**任何非 0 退出都被当作「窗口关闭」** | launchd 若读不了 Desktop(在案的 TCC 墙),守卫退出 2,作业**每天报 SKIPPED_WINDOW_CLOSED、一个字节不写,看起来完全正常**。**实测**(`REV0_VS_NEW_SHAPES.json`):守卫不可读 ⇒ `status=SKIPPED_WINDOW_CLOSED, exit=2` | 守卫改用**安装目录里的同级副本**(没有回退路径);守卫退出码只认 0 = 开、3 = 关,其它一律 FAILED(R10、R13) |
| 2 | 跳过与失败都不留收据(只有 `--out` 时才写) | 设计 §5 要求区分「跳过 / 失败 / 根本没启动」;rev 0 下三者都只剩 launchd.log 里的一行 | **每次调用都写 `runs/RUN_<utc>.json`**(OK / SKIPPED / FAILED),runs 目录在归档根之外,所以 R4「跳过时归档一字节不写」仍成立(R11) |
| 3 | 从不枚举 `~/wide_shadow/state/` | 设计 §7 写明「必须在 launchd 上下文里真跑一次 os.listdir」;rev 0 只按路径 open,**按路径能开不等于能枚举**(TCC 的形状) | 每次运行都枚举并把条目数写进收据;枚举失败即 FAILED(R12,红控用「只有 x 权限的目录」造出「能 open 不能 listdir」) |
| 4 | `--out` 用 `json.dump(x, open(p,"w"))`;`conflicts.jsonl` 用追加 | 前者是设计 §3.2 明令禁止的写法(磁盘满不抛);后者可能留下半行 | 全部改为 temp → fsync → 回读比对 → `os.replace`,sha 取自回读 |

另外两处小改:MANIFEST 字段按设计 §5 叫 `last_update_utc`(rev 0 叫 `last_utc`,尚无消费者);每次运行都把**导出的存活阈值**写进收据。

**阈值的更正**:设计 §5 写「最短覆盖 = 177 行 @ 1h ≈ 7.4 天 ⇒ 告警 3 天、硬失败 7 天」。那 177 行的名字是**新上市的名字**,它的尾巴短是因为它新,不是因为被截断。截断只发生在恰好 400 行的名字上(`shadow_loop_v3.py` L421)。rev 1 只在这些名字里取最短覆盖:**实测 674 个截断名,最短 ALPACAUSDT 399 h(16.6 天)⇒ 硬失败 399 h、告警 199.5 h**。设计原值更严,方向安全;但集成代理的存活检查应读收据里的导出值,不要写死 3/7 天。

## 1. 控制(全部在当前树上跑,收据在 `multi_asset/exports/research/news2_2026-09-23/receipts/d10_2026-09-25/archive_deploy_2026-09-26/`)

| 收据 | 内容 | 结果 |
|---|---|---|
| `7B_rev0_rerun_20260926.json` | rev 0(sha `0b2c2a43`,即 4cf4de90c)原样重跑 §7b | 12/12(2 正控 + 10 红控;R8 按设计拆成 a/b 两条,所以是 9 条编号、10 个条目) |
| `7B_rev1_20260926.json` | rev 1(sha `a71c2a22`):§7b 全部原条目不改 + R10–R13 + 正控 3 | **17/17**(3 正控 + 14 红控) |
| `REV0_VS_NEW_SHAPES.json` | 新红控的形状打在 rev 0 上 | R10 形状:rev 0 **不报错**,报 SKIPPED(即上表第 1 条);R12 形状:rev 0 **不报错**,报 OK ⇒ 两条新控制对 rev 0 有分辨力 |
| `staged_real_pass/` | 安装布局的暂存副本(scratchpad,用 `/usr/bin/python3`)对**真实** `aux.json` 连跑两次,17:31Z 静默窗内 | 第 1 次 OK,271,602 事件全部新增,43 个月分片,冲突 0,两读 sha 一致,`~/wide_shadow/state` 枚举 23 项;第 2 次 OK,**新增 0**(R2 在真实数据上成立) |

**没有测到的一项(必须在安装时测)**:以上都在会话的终端上下文里跑,**不是 launchd 上下文**。launchd 能否读守卫、能否枚举 `~/wide_shadow/state`、能否读 `~/dl_quant_live/state/anchor_runs.log`,只能在安装后用 `launchctl kickstart` 真跑一次才知道 —— 见 §2 第 5 步。

## 2. 安装步骤(lead 执行;静默窗内;每步有预期输出,不符即停并走 §3)

```bash
# 0. 前置:静默窗开着,且剩余 ≥ 20 分钟
python3 -B ~/Desktop/quant_research/multi_asset/exports/research/common/venue_quiet_window.py --json   # 期望 "open": true

# 1. 目录与文件(只在 ~/funding_ledger_archive 下;不碰 ~/wide_shadow、~/dl_quant_live)
REPO=~/Desktop/quant_research/multi_asset/exports/research
mkdir -p ~/funding_ledger_archive
cp $REPO/news2_2026-09-23/devices/archive_live_ledger.py ~/funding_ledger_archive/
cp $REPO/common/venue_quiet_window.py                     ~/funding_ledger_archive/
shasum -a 256 ~/funding_ledger_archive/*.py
#   期望(逐字):
#   a71c2a221eb59c173f346e7472c5a690c22bea98f1678c4ac4ea582323328591  archive_live_ledger.py
#   4e008f487bac4ef49f08c66eb2de44dfed4656ea63be4a398134684acb327fcc  venue_quiet_window.py

# 2. 安装前在终端上下文再跑一次自检(就在安装目录里,用 plist 里同一个解释器)
/usr/bin/python3 -B ~/funding_ledger_archive/archive_live_ledger.py --selftest --root /tmp   # 期望最后一行: 7b CONTROLS 17/17 pass (3 positive, 14 red)

# 3. plist
cp $REPO/news2_2026-09-23/devices/com.hsy.funding_ledger_archive.plist ~/Library/LaunchAgents/
plutil -lint ~/Library/LaunchAgents/com.hsy.funding_ledger_archive.plist                   # 期望: OK

# 4. 加载(RunAtLoad=false ⇒ 加载时不跑)
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.funding_ledger_archive.plist
launchctl print gui/$(id -u)/com.hsy.funding_ledger_archive | grep -E 'state|runs|last exit'  # 期望: runs = 0

# 5. ★ launchd 上下文实测(设计 §7「不能假定」那一项):触发一次真跑
launchctl kickstart gui/$(id -u)/com.hsy.funding_ledger_archive
ls -t ~/funding_ledger_archive/runs/ | head -1          # 取最新收据
#   期望该收据: status OK;window.exit 0 且 guard 指向 ~/funding_ledger_archive/venue_quiet_window.py;
#               aux.dir_enumerated_n > 0;events_new > 0(首跑);conflicts 0;liveness_thresholds.hard_fail_h 有值
cat ~/funding_ledger_archive/launchd.err               # 期望: 空
#   若 status FAILED 且 error 含 "Operation not permitted" / "cannot enumerate" ⇒ launchd 的 TCC 墙,走 §3 回滚,不要改路径硬撑

# 6. 幂等在 launchd 上下文里再验一次
launchctl kickstart gui/$(id -u)/com.hsy.funding_ledger_archive
#   期望最新收据: status OK,events_new 0,conflicts 0
```

**排程**:每天 09:30Z(本地 17:30)。每天一次就够:最短截断覆盖 399 h,日频留了 16 倍余量。

## 3. 回滚(任何一步不符;作业只读实盘,回滚对实盘零影响)

```bash
launchctl bootout gui/$(id -u)/com.hsy.funding_ledger_archive
mv ~/Library/LaunchAgents/com.hsy.funding_ledger_archive.plist ~/funding_ledger_archive/plist.rolled_back_$(date -u +%Y%m%dT%H%MZ)
# ~/funding_ledger_archive/ledger 与 runs 保留(数据与收据,不删)
launchctl print gui/$(id -u)/com.hsy.funding_ledger_archive 2>&1 | head -1   # 期望: Could not find service
```

## 4. 存活检查(交集成代理,挂每锚验收;规格来自设计 §5,阈值改读收据)

读 `~/funding_ledger_archive/runs/` 里最新一份 `RUN_*.json`:

| 情形 | 验收动作 |
|---|---|
| 最新收据 `status=OK` 且距今 < `liveness_thresholds.warn_h` | 绿 |
| `status=SKIPPED_WINDOW_CLOSED` | 不告警;**连续跳过 > 3 天**告警(门坏了,不是窗关着) |
| `status=FAILED` | 连续 2 次告警;`error` 原文进告警 |
| 最新收据距今 > `warn_h` | 告警;> `hard_fail_h` 验收红(开始真丢事件) |
| **runs 目录里没有任何收据,或最新收据超过 26 小时** | 告警 —— 作业根本没启动,与上面三类不同 |
| MANIFEST 里任一分片 sha ≠ 磁盘 | 红(作业下次启动也会自己报 R5) |

## 5. 已知限制(写明,不藏)

1. **键是秒,不是毫秒**:生产者 `ledger_tail` 本身按秒存 `ft`,同一秒两笔在上游已被合并;归档无法恢复。D10 修订 1 的毫秒规则管的是真值源 `ledger_full_ms`,本归档是线 C 的「源 1(相对事后已知账本)」,不是交易所真值。
2. 生产者停摆期间(如 09-26 11Z 起)`aux.json` 不更新,作业照跑、新增 0,这是正确行为;生产者恢复后第一次运行会补进停摆期间的结算(399 h 覆盖内不丢)。
3. 归档只覆盖安装之后仍在 `ledger_tail` 里的事件;首跑实测最早可回溯到 2020-07(旧名的稀疏行),2026-09 起才是全宇宙密集覆盖。
