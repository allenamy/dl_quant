> **创建:** 2026-09-27 16:12 UTC | **Session:** Codex acting-lead/live_recovery_audit_0927 | **状态:** final（候选及本批验证已交付；完整发布门仍FAIL，未部署） | **作废条件:** fixpkg_e基线或funding写者/读者合同改变；root裁定变更

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

## 18:23 UTC 追加：实测取代以上窗前状态

保留上段作为16:12的历史状态；“当前未运行”已不适用于本段时间。唯一入口仍为 `bash ops/run_acceptance_offline.sh`，运行于本件独立clone。RED1/RED2分别观察到 funding_gap 30/50 FAIL，所有原R1的545行逐字段正控均通过。完整电池每轮168项（163套件、5审计门），RED2为166过、funding_gap及历史disposition两项失败。

首实现 `eea02b2` 的 GREEN1 已真实终态exit1：funding_gap 103/103通过，完整电池166/168；失败为 tests_binance_funding 的M段7断言，以及08Z OPENUSDT历史667.0389真实拒单的 tests_disposition_matrix。后者不因16Z恢复通过而归零，也不豁免或上调200门。首实现尚不能发布。

R1真实545次writer+ack累计耗时：RED2 0.003132624秒，GREEN1 0.034186251秒；对应整次pull为0.412355917/0.595148375秒。该夹具逐字段结果相同，真实macOS文件、day目录、root目录fsync正控通过。这些是离线本机成本测量，不是生产耗时上界。全电池的state副本被套件改写，未留不可变的最早副本；不声称整套RED/GREEN输入逐字节同一。`FUNDING_GREEN_input_manifest_20260927.json`记录RED2之后、GREEN1之前实际输入，历史disposition订单SHA保持一致。

本批最后四类承重审查已冻结范围，并在RED3新增红控后再修：

1. strict funding snapshot应以精确有效read_ts取完整快照；同symbol冲突行拒绝，完全相同行可去重；邻近但不同浮点时刻不能用epsilon混合。普通读者默认合同不改。
2. strict日期目录扫描遇到YYYYMMDD普通文件必须具名失败，不能当缺失日。
3. writer首次异常后停止本次pull其余append，失败及未尝试的原income全部留pending。真实partial write的残行不自动修复，重试须严格拒绝损坏文件。
4. ack须绑定写入/严格读取证据的dev/inode，不能给替换后的同名文件背书。未发现正常已认证流程替换该路径，故此为潜在保护，不能声称现场发生。

M段另属夹具根目录串用：W与M把各自temp目录直接作为pilot_log，`pending_path`均落到公共父目录；同DOGE结算旧-0.05与新+0.40冲突被新身份保护正确拒绝。RED3路径不等断言已证实两者路径相同；新增白名单诊断漏`json`导入引发NameError，不能说完整dump通过。root认可结合GREEN1原M7失败、RED3路径真红及源码，不为这个诊断错误单独再跑整套RED；终态后修测试诊断与夹具独立父目录，M原收入与行为断言保持。

未闭合：旧funding schema没有asset/tranId完整身份。R1原income545条全部显式USDT，但历史55,395 funding行均缺asset，旧W/M夹具income也缺asset；不能泛称它们已证明USDT。本补丁仅保留旧省略asset行为并明确计数，显式非USDT或同旧key多income留pending+HIGH。不得称跨资产/完整tranId域已闭合。

## 18:35 UTC 追加：RED3终态及实现冻结

RED3真实exit1，168项中164过；funding_gap的17条真实失败、binance_funding的共享队列真红与诊断NameError、static_names的同一json遗漏、历史disposition。完整列表见 `multi_asset/exports/research/acting_lead_2026-09-27/receipts/FUNDING_RED3_terminal_20260927.json`，driver SHA256 `0f9d1c45a8dbe22e634fef542488838fe00eb721c33cd6416822687b56d3d75d`。

四类修复与M夹具隔离已在clone落码并冻结。仅4个code-zone文件变更：`live/pilot_log.py`、`live/binance_funding.py`、`live/tests_funding_gap.py`、`live/tests_binance_funding.py`；运行入口未改。调用者普查只有binance_funding一个真实资金费写者。首错break之外，PilotLogger也将自身资金费句柄标记失败，后续资金费调用拒绝（其它表不受影响）。新pull的严格账本读取拒绝损坏尾行，不自动截断、猜测或补造账。

GREEN2由原offline wrapper于18:31:31Z启动。相关两套已完整exit0：funding_gap 123/123、binance_funding 76/76；M诊断显示独立pending路径、原income未改、无身份失败。R1仍545行逐字段一致；真实writer+ack累计0.034770872秒、整pull0.628367875秒。此处尚未取得全电池终态，不能称完整绿色。

`FUNDING_GREEN2_input_manifest_20260927.json`记录GREEN2开始前360个已选输入及完整源码SHA；该选集与GREEN1输入manifest逐项相同，历史disposition订单SHA亦相同。这是选集比较，不是整个state不可变声明。所有full battery都在可变隔离副本上执行，未从生产刷新状态。

## 继承的跨缺口证明边界（本补口不扩大）

原算法以两个持仓读数A/B包围结算t，检查本地账本中(A,t)没有该symbol成交，并以(A,B)的本地成交净量和既有step容差核对前后数量。本补口使读取失败、损坏、冲突和非法数字不能冒充这些条件成立，并保证确认的funding行在出队前持久化。它没有新建一套独立venue历史路径完整性证明。两个端点加本地成交账本不能独立排除未入账的往返交易或外部执行者；这仍依赖既有成交完整性、单写者和恢复取证合同。不能将本批通过解释为全链无风险或任意停机间隔均可安全定价。

候选仍独立于GAP4；现有历史disposition门的真实FAIL阻断发布。没有改门、改200阈值、改历史订单/锚类别或把事故视为已自动豁免。后续发布处理须由root依据既有协议审议，不能用本件资金费正控替代完整发布门。

## 最终交付：18:44 UTC

clone最终提交 `13ca2cc7533ecc4cf5ad4372b69f4b771589279e`（分支 `codex/funding-durable-ack`，路径 `/Users/haosiyu/cc_tmp/funding_durable_ack_exec_20260927`）。相对cea1e15的候选仅改上述4个文件，code-zone工作区干净；state测试副本和日志保留但未提交，未推送或部署。测试提交顺序14795a1→841e771→首实现eea02b2→RED3测试0568773→最终13ca2cc。

GREEN2由 `/Users/haosiyu/cc_tmp/funding_durable_ack_exec_20260927/ops/run_acceptance_offline.sh` 完整执行，实际进程exit1及wrapper末行EXIT1一致。完整168个唯一条目中167项exit0，唯一非零为 `tests_disposition_matrix`。两套资金费结果123/123和76/76不变，root已独立核完整表及源码SHA。没有重跑碰绿、改历史门或调整阈值。

最终driver：`state/FUNDING_DURABLE_GREEN2_20260927T1832Z.log`（实际suite时间戳183131Z），SHA256 `3cb259c1d3c600af42923d964ae60c2b72e8fe37931049e32e53b2c8303ad7ca`。完整表、源码和输入边界见 `multi_asset/exports/research/acting_lead_2026-09-27/receipts/FUNDING_GREEN2_terminal_20260927.json`。RED1/RED2/GREEN1/RED3/GREEN2的完整退出表及资金费stdout均归档于同目录 `FUNDING_DURABLE_RUNS_20260927/`，并由BINDING逐文件绑定SHA。

最终commit重新导出的4文件源码diff，与开跑冻结版本逐字节一致：

| 基线 | 归档文件（FUNDING_DURABLE_RUNS_20260927内） | SHA256 |
|---|---|---|
| cea1e15 | PATCH_from_cea1e15.diff | c4aec111db77c496b68dfc5c906c0126577c0f11361cdd21c7eb41af8df65b1b |
| eea02b2 | PATCH_from_eea02b2.diff | d40dc4986a54f00e6ab1962ac8aad43b1867b79a363d8b8186ca822f7b135832 |

未验证/未闭合点保持：候选未在生产运行；离线545行成本不是生产耗时上界；跨缺口本地账本证明不独立替代完整venue路径取证；旧schema的缺asset/tranId身份域未扩大。发布仍被08Z OPENUSDT真实667.0389 involuntary gap阻断。此件是可审候选交付，不是发布PASS收据。

## 基线依赖：不能当作d01e35d上的独立发布整包

只读Git元数据确认：`merge-base(d01e35d, cea1e15)=d01e35d`，生产d01是候选基线的祖先，cea基线领先10个尚未部署提交；`merge-base(cea1e15, 13ca2cc)=cea1e15`，本轮再加5个提交。因此生产至本候选共15个提交，而本件4文件diff仅相对cea基线。**本次结果不是生产d01上的集成PASS；不能把最后一个提交或4文件patch当成可直接发布的完整包。**

直接资金费前置：4ce03f5（G/R夹具）、ef3c9d6（持久pending与跨缺口类修复及suite注册）、99bac95（告警修正）、8102559（funding schema）、7ff6968（step来源冲突与545行完整对照）。其余继承基线提交仍须在后续包组装中交代：ceb582d（producer publication边界测试）、2c19df9（anchor_report前锚选择）、20a4748/4e3fc6c（per-name-stop缺锚记录及测试）、cea1e15（A10主机无关红控）。这些是提交元数据及依赖边界，不借旧commit message中的测试声称代替新验收。

完整SHA、父提交、Git tree与祖先关系见 `multi_asset/exports/research/acting_lead_2026-09-27/receipts/FUNDING_CANDIDATE_dependencies_20260927.json`。后续须依据已批准包依赖组装准确集成树，并在该树上运行原offline wrapper；本次没有另开clone、没有新电池、没有遍历或提交state内容diff。
