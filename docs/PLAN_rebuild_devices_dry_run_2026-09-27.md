> **创建:** 2026-09-27 05:2xZ(原写 06:0xZ,时间写错,以提交 89c33ed86 05:27Z 为准) | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** **计划草稿,未跑;判据待 lead 冻结**(冻结前不起任何作业) | **作废条件:** `d3a7f013d` 之后本文点名的任一装置再被改动(须重写 §2 对应行);或参照产物(§2 的 sha)在 pod2 上被清掉而无法复核

# 计划:十月前对「只做过静态检查」的重建装置做一次真实端到端干跑(pod2,静默窗)

**为什么**:拉取器类修复(`d3a7f013d`)把 10 个链上装置的写文件改成走 `common/durable_write.py`。这些装置只做过解析、`--help`、import 检查,**没有实跑**。十月重建时它们第一次真跑,出错就出在关键路径上。lead 09-27 要求十月之前排一次真实干跑,先写计划。

**干跑的问题只有一个**:在**与上次交付完全相同的输入**上重跑修改后的装置,产物是否与上次交付的产物一致?
- 数组层逐位相等(含 NaN 模式);
- 收据 JSON 除「易变键」以外逐键相等。
- 这是**恒等控制**,不是新读数:不产生任何书层或模型层数字,不改变任何已有结论。

---

## 1. 判据(草案,冻结权在 lead;写于任何干跑读数之前)

1. **npz 产物**:逐键比较,键集合相同,每个数组 dtype、shape 相同,且按位相等。浮点按自身宽度的整数视图比较,NaN 与 NaN 视为相等。**npz 文件本身的 sha 不作判据**:zip 条目带写入时刻,同一装置两次运行的文件 sha 从来就不相同,例如上次 `ledger_full_ms.npz` 的 sha 就无法由重跑复现。
2. **JSON 收据**:去掉易变键之后逐键相等。易变键只允许以下几类,按装置在 §2 中逐一列出:运行耗时(`seconds`、`elapsed_s`)、时间戳(`utc`、`started_utc`、`finished_utc`)、装置自身 sha(`self_sha256`、`device_sha256`,这正是被改动的部分)、npz 输出的文件 sha(理由见第 1 条),以及输出路径(干跑写到新目录)。**判据冻结之后,不许为了让某一行变绿再往易变键里加东西。**
3. **文本产物**(symlists、manifest 的 files 段):逐字节相等。
4. **结果分三类**:
   - IDENTICAL:全部相等。
   - DIFFERS:按字段具名列出,并按 |diff| 分桶;不许只报一个总数。
   - NOT_RUN:输入缺失或装置在跑之前就停了,具名写原因。

   任何 DIFFERS 都先停下来查原因,不许重跑到变绿。
5. **基线先行**:先对参照产物跑一次比较器自比(参照对参照),必须 IDENTICAL;再对参照注入 1 个 ULP 的扰动,必须被检出。两条都过,比较器才算有分辨力;否则整轮作废。

## 2. 装置、参照与 argv

**输出**一律写到新目录 `/workspace/d10_dryrun_<日期>/`,不覆盖任何已有文件。`/dev/shm` 余量只有约 6.1G,而 NEWS_FEATURES_D10 有 2.96 GB,所以大件不放 `/dev/shm`。
**装置同步**:从仓库 HEAD 同步到 `/workspace/d10_dryrun_<日期>/{devices,common}`,三方比 sha(HEAD blob = 工作树 = pod2)。
**解释器**:与上次交付时的运行相同(下表列出)。

| # | 装置 | 参照(上次交付) | argv 来源 | 易变键(在 §1 第 2 条范围内具名) | 估时 |
|---|---|---|---|---|---|
| D1 | `d10_build_ledger_ms.py --out <新>` | `ms/ledger_full_ms.npz`(`e179071d`,数组层)+ `D10_LEDGER_MS_BUILD.json`(RECONCILED) | 装置只有 `--out`,输入写死为 OLD、FUND_DIR、FUND_AUG(L44–47)。**先核这三个输入**:OLD 的 sha 由装置自己断言;FUND_DIR 与 FUND_AUG 的 sha 和 mtime 要与上次一致,不一致就是 NOT_RUN,不能算 DIFFERS | self_sha256, seconds, new_ledger.path, new_ledger.sha256 | 约 155 s(上次收据) |
| D2a | `d10_build_fund_state.py --mode snap --ledger-ms …/ledger_full_ms.npz --ledger-ms-sha e179071d… --axes /dev/shm/nc_2026-09-23/work/axes.npz --out <新>/fund_state_snap.npz --compare <NC fund_state> --compare-sha a12a8ed3` | `fund_state_snap.npz`(`35cc8f30`,数组)+ 收据,其中 identity_verdict 上次为 DIFFERS,须原样复现 | **收据没有 argv**,要从收据的 inputs/mode/output 与 fs_snap.log 重建。`--compare` 的路径需要核实 | self_sha256, seconds, output.path, output.sha256 | 约 6 s |
| D2b | 同上,`--mode d10`,不带 `--compare` | `fund_state_d10.npz`(`f07e4ebd`)+ 收据(tier 计数 672/2582884/9/10) | 同上 | 同上 | 约 7 s |
| D3 | `d10_stage2_assemble.py`,argv **逐字**取自 `NEWS_FEATURES_D10_RECEIPT.json` 的 argv 字段,只换 `--out`;cwd 必须是 `/dev/shm/d10_2026-09-25`,因为 `--rebuilt ms/…` 是相对路径 | `NEWS_FEATURES_D10.npz`(`f1cd3fa2`,2.96 GB,数组层)+ 收据的 G1/G2/profile/crosscheck | 收据 | utc, device_sha256, output.path, output.sha256 | 分钟级;峰值内存约 2 份 3 GB |
| D4 | `d10_parity_gate.py --a ms/rebuilt_features_d10.npz --b /dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz --features <同 b> --columns … --out <新>`;另跑一遍带 `--positive-control` | `D10_PARITY_REBUILT_VS_NC.json`(PARITY_RED,各列 DIFFER 与分桶)、`D10_PARITY_POSITIVE_CONTROL.json`(CONTROL_PASS) | **收据没有 argv**,从 sides/columns/mode 重建;`--anchor-max-utc` 是否用过要查 `3e9d72c10` | self_sha256 | 分钟级 |
| D5 | `d10_p2_ledger_vs_archive.py`(新旧两本账本)与 `d10_legs_rn8_vs_archive.py`,argv **逐字**取自 `d10_reaudit_jan_to_aug_pod2.sh` 的 run 行,只换 `--out` | `reaudit_jan_aug/` 下 3 份 `_JAN_AUG.json` | 驱动脚本 | self_sha256(若有), seconds | 各分钟级 |
| D6 | `d10_live_ledger_vs_archive.py --live … --zips … --month 2026-08 --mask … --crypto-axis … --out <新>` | `D10_LIVE_LEDGER_VS_ARCHIVE_2026-08_RESIGNED.json` | **argv 需从 `a2254f930` 恢复**;若 `--live` 的快照已不在,就是 NOT_RUN(具名) | self_sha256(若有) | 分钟级 |
| D7 | `d10_make_symlists.py <D10_S1_ARCHIVE_INVENTORY.json> <新>/symlists` | pod2 `/dev/shm/d10_2026-09-25/symlists/*.txt` | 用法行 | 无(逐字节) | 秒级 |
| D8 | `d10_manifest_gate.py --selftest $EXP/zips/2026-08 2026-08` | 该装置自带的基线加 6 个变异,全部按类命中 | 用法行 | — | 秒级 |
| D9 | `d10_archive_inventory.py --symbols <3 名的文件> --ledger <P2> --out <新> --progress <新>`,真实网络请求,只列目录(3 次请求,公共 CDN,用户 09-05 豁免) | 上次盘点里这 3 个名的 months 字段 | 用法 | elapsed_s, requests_made 以外逐键 | 秒级 |
| D10 | `EXP=<新> bash d10_pull_months_pod2.sh 2026-08`,symlist 只放 3 名,真实拉取(6 次 GET) | `$EXP/zips/2026-08/` 里同名 zip 的字节,以及 manifest 中这 3 名的 sha256 | 本装置 | manifest 的 run_nonce、时间戳、self_sha256、durable_write_sha256 | 秒级 |

**不在干跑范围内**(具名):
- `d10_stage2_pass1.sh` 与 `d10_stage2_legs.sh` 调用的 `nc_p2_build.py`、`nc_legs.py` 是生产派生的「代码不改」复制件,本次没有改动;它们上次各自的恒等控制(`7fe5b3473`、`dacd303af`)仍然有效。
- 训练器、生产者树、执行器不在范围内。

## 3. 顺序与资源门

1. 同步装置并三方比 sha。然后跑 §1 第 5 条:比较器自比,加 ULP 正控。
2. D7、D8 → D1 → D2a/D2b → D3 → D4 → D5 → D6 → D9、D10。一行红就停,后面的行不跑;前后有依赖的只有 D1 → D2(D2 读上次交付的 `e179071d`,不读 D1 的新产物,所以 D1 红并不妨碍 D2 有意义,但仍按「红即停」处理)。
3. 每个作业:pod2 `setsid nohup`,`nice 10`,PGID 写入 `INFLIGHT_REGISTRY.json`,terminal/success 正则锚定行首。
4. 起跑门:按团队门检查他人 `bt_launch`(按不同 PGID 计 ≤ 2)、cgroup 余量 ≥ 24 GiB、`/dev/shm` ≥ 4 GiB;只读进程表,绝不发信号。不用 GPU。
5. 本机不跑重活。驱动在 pod2 上;本机只有一个只读等待器。

## 4. 产物与收据

- `DRYRUN_RESULT.json`:每行一条,含 IDENTICAL/DIFFERS/NOT_RUN、参照 sha、新产物 sha、逐字段差异分桶、所用 argv(逐字)、解释器。
- 比较器 `d10_dryrun_compare.py`(待写,先于运行入库):按 §1 实现,自带基线与 ULP 正控。它本身也受 `tests_october_chain_contract.py` 约束,须在本计划冻结版里点名。
- 入库路径:`news2_2026-09-23/receipts/dryrun_<日期>/`。

## 5. 顺带要修的一个缺口(提议;是否先做由 lead 定)

D1、D2、D4 的收据**没有记录 argv**,本次只能从 inputs 字段和日志重建。这正是 CLAUDE.md 约束 6(装置自报 config 并写进产物)要防的情况。提议在干跑之前给这三个装置的收据补上 `argv` 与 `python` 两个字段,这样干跑同时验证了这处小改动。收据里新增的这两个键列为「干跑新增键」,参照中没有它们,比较时只作单向忽略。

## 6. 这份计划没有覆盖的风险

- D6 依赖的实盘 aux 快照可能已不在,只能 NOT_RUN。
- 参照产物都在 `/dev/shm` 或 `/workspace`,前者可能被清掉。HANDOFF §1 说大件已经用符号链接指向 `/workspace`;真跑之前要先核参照 sha。
- 干跑只证明「同输入同输出」,不证明十月的新输入(九月 zip、新轴)能走通。那部分由 runbook §1–§2 的恒等控制在十月当时负责。

## 冻结(lead,2026-09-27 05:3xZ;写于任何干跑读数之前)
- §1 判据草案原样冻结:npz 逐数组逐位比较、NaN 模式一致;JSON 去掉 §2 列出的易变键后逐键相等(清单就此冻结,不许为了变绿再加键);文本逐字节相等;比较器先过「参照对参照自比」与「1 ULP 扰动必须检出」两道;出现任何差异就停下查原因,不许重跑到变绿。
- 决定 1:**先补**。给 ledger_ms、fund_state、平价门三个装置的收据加上 argv 与解释器版本。argv 由 `vars(args)` 派生,不许手写清单。补完后,干跑本身就是这处小改动的验证。
- 决定 2:D6 当时用的实盘快照若已不在,记为 `NOT_RUN (input absent)`,并具名写明原因。不算通过,也不许拿别的快照代替。
- 执行只在 pod2 上做,过资源门;作业登记进 INFLIGHT_REGISTRY。

## 冻结补遗 1(lead,2026-09-27;对 news2 起跑前 4 处澄清的答复,写于任何干跑读数之前,入库后才可起跑)
可,附 3 个条件。
1. D4 同意,改用 521c6a28 的两份收据(SNAP_CONTROL GREEN、COMMON_WINDOW RED)做恒等对照。RED 那份也必须逐键复现,仍然是 RED,内容相同。正控只作功能检查,判据按你写的。
2. argv 里的 --out 同意,但不许只凭下标:比较器对每个豁免下标 i 断言 argv[i-1] == "--out"。断言不成立 ⇒ 这一行判 DIFFERS,不静默跳过。argv 的长度也必须相等。
3. gate_sha256 同意归「被改动装置自身 sha」一类,前提是先证明 793c5eb2 → 6a8b16ca 只改了注释:取两版源码做 ast.dump 比较,相等才豁免,并把两个 ast 的 sha 写进收据;不相等 ⇒ 该键判 DIFFERS。
补充:output.sha256 只在输出是 npz 时算易变(因为数组另外逐位比)。输出若是 JSON、文本或 parquet,sha 必须相等。请逐行标明 D1、D2、D3 的输出属于哪种。
4. 解释器照你说的办。D1–D3 若出现 DIFFERS,就如实记为 DIFFERS,并附原因调查;不许因为「只是解释器不同」改判为通过。

**news2 逐行标注(按补遗 1 第 3 条补充要求)**:
- D1 `new_ledger.sha256` 指 `ledger_full_ms.npz`,是 npz,算易变;D1 的收据 JSON 本身逐键比较。
- D2a/D2b `output.sha256` 指 `fund_state_*.npz`,是 npz,算易变。
- D3 `output.sha256` 指 `NEWS_FEATURES_D10.npz`,是 npz,算易变。
- 这三行都没有 JSON、文本或 parquet 的输出 sha 被列为易变。
