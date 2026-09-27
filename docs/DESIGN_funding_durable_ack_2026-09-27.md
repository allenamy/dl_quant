> **创建:** 2026-09-27 16:12 UTC | **Session:** Codex acting-lead/live_recovery_audit_0927 | **状态:** in-progress（root已批准最小设计；红控待17Z后调度） | **作废条件:** fixpkg_e基线或funding写者/读者合同改变；root裁定变更

# funding 现有类修复的 durable ack 补口

本件续接 `multi_asset/exports/research/fixpkg_e_2026-09-27/CRITERIA_funding_class_fix.md` 与 news2 `funding_backfill_2026-09-26/RELEASE_AND_CLASS_FIX.md`。现有实现首提交 ef3c9d6、schema补充8102559、news2复审末修7ff6968；候选clone HEAD为cea1e15fa4051df1fb506a5989a3e582291ce95b。真实生产d01e35d未包含队列。旧545行回填已安装，不能当类修复部署。

独立clone `/Users/haosiyu/cc_tmp/funding_durable_ack_exec_20260927`，分支`codex/funding-durable-ack`，基线cea1e15；未改`fixpkg_e_exec`或运行树。此项不并入17Z GAP4，不增停机/恢复机制，不碰F7冷静期政策。

## 根因与边界

1. `live/binance_funding.py:806–844`先durable写候选队列，然后`log.funding`成功即从最终队列移除；但真实`live/pilot_log.py:464–469`只有write+flush，`:548–550`的close也无fsync。进程退出通常仍可读，不等于机器崩溃持久性。新队列可已落盘、funding页仍未落盘；若较新行存活，max-settlement cursor越过丢行。
2. 已盘上去重`:700–708`也必须取得durable ack：上一轮append可见但fsync失败，下一轮不能仅凭可读而出队。
3. 跨缺口证据的未知放行：`_GapEvidence._day_rows:515–519`把读错吞成空表；`carried_position:578–619`没有对qa/qb/na/step/时间/净量完整有限性检查，NaN可令`abs(diff)>tol`为False；缺失side默认SELL、NaN fill_ts被跳过。若早于首待定价日的历史日不可读，前面的on_disk日扫描未必触及，不能以它替代fail-closed。这些都使“零成交/数量不变”失去证据。
4. 队列载入仅验顶层list，`_load_pending:488`的exists也不能把权限错当不存在。新增入口应区分ENOENT与其它I/O错误，并验证待处理行的必要结构；异常保留原队列并具名失败，不重置为空。

## 最小设计（root已认可）

- 只改变funding表的ack：实际append/flush后fsync funding文件，再fsync day目录、pilot_log根目录，最后允许调用返回成功。其它表保持原写者。
- pilot_log根及其父链须预先存在；本补口不默默建立未知父链。当天新目录由既有logger建立，ack day目录内容及root中的day目录项。真实macOS文件与目录fsync必须由离线套件证明，不能只mock。
- 对可读的既存funding行，出队前也ack相同文件及目录。ack失败保留pending、HIGH及明确失败字段，不将其计作rows_written。append后最终队列写失败，复跑先ack再去重，不重复追加。
- 跨缺口证据读失败/非法数值/非法side/未知时间，统一具名拒绝并保留原income于pending，不声明NO_TRADES。合法G9/R1/R2正控逐字段不变；不增加资产换算或更改历史单位。
- 写入/读取失败不自动停止或恢复交易，沿既有funding告警路径交root处理。

## 先写最小红控，窗口后真实红绿

只允许root于17Z之后调度独立clone的`bash ops/run_acceptance_offline.sh`。窗前只构造测试及compile，不执行任何执行器套件。遵守TDD：先在未修改实现的cea1e15上观察新增红控，再落实现、复跑同一入口；没有红控实测不得声称修好。

| 验收 | 最小证明 |
|---|---|
| D1 | 真实PilotLogger.funding在macOS上完成文件、day目录、root目录fsync；只给资金费增加屏障 |
| D2 | 文件/day/root任一fsync失败，income仍在pending，HIGH/明确失败；再次读取可见行也不能绕过失败ack |
| D3 | append成功后最终队列写失败，重试只ack/出队，账本不双计 |
| D4 | 根父链不存在时funding拒绝，不靠递归mkdir声称持久化 |
| E1 | 历史日read_day PermissionError/损坏不得返回空成交集合，所有未能证明的行留队、HIGH/具名FAIL |
| E2 | qa/qb/na/step、fill_ts/fill_px/fill_notional中的NaN/Inf；非法side：逐名拒绝，正常名不受影响 |
| E3 | 合法JSON但队列行缺字段、队列权限错误：原文件不覆盖，失败可见 |
| 原正控 | G1–G10、R1全545行逐字段、R2及已有funding/ledger套件仍过 |

## 单独保留的身份语义合同

fetch_income按tranId去重（`:121–125`）；pending按(symbol,time,tranId)（`:482–483`）；on_disk按(symbol,settlement_ms)（`:706–708`）；build_rows不保存asset/tranId（`:193–199`）。同symbol/time多income、不同asset与重复tranId语义未闭合。现R1原始545行的asset全USDT，合成测试也全USDT，不提供跨asset证明。root裁定当前不扩大身份域/资产换算；本补口不能宣称关闭该项。

## 当前证据与未验证

已存在的红控收据证明d01e35d有19 FAIL；历史cea1e15 arm64 wrapper收据EXIT0。它们不覆盖本件新增崩溃/未知证据路径，也不替代修改后的验收。当前未运行新红控、未跑套件、未碰API/凭据、未读取臂结局、未部署。新的测试是否能分辨每个缺口与真实macOS fsync能否完成，均待root调度验证。
