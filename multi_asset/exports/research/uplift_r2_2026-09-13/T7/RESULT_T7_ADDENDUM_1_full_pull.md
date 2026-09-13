> **创建:** 2026-09-13 ~12:3xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T7) | **状态:** RESULT_T7_feasibility 的**附录 1**: 全量拉取完成记录与完整性/守卫收据(**不含任何收益相关数字**) | **作废条件:** `pull/plan/PULL_PLAN_FROZEN.json` sha 与 `.sha256` 不符; 或 cc_tmp 数据被改写(逐页 body sha 见清单); 或任一检查装置被发现有缺陷
> **上游:** `RESULT_T7_feasibility.md`(§9 拉取计划, 更正 1 = §13-9); lead 派工(09:0xZ): 映射市场 · 自 2021-12 · 两所 · 币安 futures/um 指数价 1h 月 zip · 位置 `/Users/haosiyu/cc_tmp/krw_pull/` · 每主机 ≤ 5 req/s · 逐页原子写 + JSONL 清单 · 最老游标续拉 · 每次运行正负 `to` 控制 · 完整性检查 · 逐对滚动同一性守卫 · 逐年偏移谱 · 前台 until 循环等待 · 只提交小件 · 不动 S1 草案

# RESULT T7 · 附录 1 · 全量拉取

## §0 结论(先读)
1. **拉完且无未解决错误**: 三个主机进程均 exit 0、错误记录 0、未解决 0。KRW 市场单元 Upbit 468/468、Bithumb 704/704(60m + 日 K); 页文件 Upbit 24,522 / Bithumb 38,662; 币安月 zip 10,686 个 OK + 251 个 NOT_FOUND = 计划 10,937。拉数根目录在拉取完成时合计 **1,049,925,762 字节(0.978 GiB)**(补填与 G2 之后为 1,126,143,845 字节 / 1.049 GiB, 见 P-3), 拉取完成时其中数据页与 zip 约 760 MB(Upbit 220.9 + Bithumb 354.5 + 币安 184.8)、清单 34 MB、HTTP 日志 41 MB、守卫用派生数组 213 MB(见 P-3)。
2. **完整性**: C0 页完整性、C1 最早 bar 对普查首日、C2 页缝、重复 bar、C4 新鲜度**全部 0 失败**(C4: Upbit 234 FRESH; Bithumb 341 FRESH + 11 THIN_OK)。C3 逐市场日量恒等: Upbit 195,244 天中 EXACT 195,180 / ROUNDING 32 / **MISMATCH 32**(25 个市场); Bithumb 318,148 天中 EXACT 317,439 / ROUNDING 7 / **MISMATCH 702**(107 个市场)。**734 个不等市场日今天逐字段重拉, 全部与存档 IDENTICAL** ⇒ 这是场所自身「日 K 成交量 ≠ 小时 K 之和」的不一致(Bithumb 696/702 为小时和偏小, 比值中位 0.9994、最小 0.657; 集中在 2021-12–2023 与少数日期, 如 2024-08-24 同日 27 个市场), **不是拉数丢页**; 未改动、未剔除任何数据。
3. **限速**: 429 = 0。按日志墙钟计算的「任意 1 秒最大请求数」Upbit 与 Bithumb 均为 **6**(各恰好 1 个窗口), 币安 5。这两个窗口都由 **10:20:48Z 同一时刻** 的一次 0.087 / 0.088 秒间隔造成, 出现在两个独立进程里且短缺量相同(约 0.12 秒); 限速器用单调时钟强制间隔 ≥ 0.21 秒 ⇒ **推断**为系统墙钟回拨约 0.12 秒, 而非真实超速; timed 日志中未找到佐证(可能已滚动), 故只作推断, 照实列出。
4. **逐对价格同一性守卫**(595 对, 冻结阈值): PASS 584 / FLAG_DIVERGE 10 / FLAG_SCALE_SUSPECT 1。**只标不删**。
   - 改名对(EOS→A 两所、FTM→S、KLAY→KAIA、DAR→D)的分歧区间**全部在币安旧符号最后一个合格锚之后**(退市尾段, 位于 ±62 天月份填充内), 不触及合格窗。
   - 合格窗内的旗标: Upbit KAVA 2022-12-25..2023-06-06; Bithumb CRV 2023-08-04..09-12(唯一尺度嫌疑, 旗标区间内 |m30| 最大 1.319, 约 5 周后回复); Bithumb ENJ 2023-10-27..11-12; Bithumb SOLV 2026-04-04..05-13; Bithumb TAIKO 2026-07-13..08-06(与合格窗末端部分重叠)。XVS 2026-04 在其合格窗之后。
   - **读法(推断)**: 这些都是持续数周后回复的分歧, 形态上更像充提暂停期的真实韩国溢价, 而不是 STRAX 那种持久的面额改动; 是否在 S1 中剔除这些对×月由冻结的 G4 规则决定, 本步不决定。
5. **逐年偏移谱**: 24/24 个年份格 PASS(两所 × KRW-BTC/BTCUSDT 与 KRW-XRP/XRPUSDT × 2021-12 与 2022–2026), 负控(KST 当 UTC ⇒ +9; 收盘标签 ⇒ +1)24/24 红 ⇒ 全史时间戳约定未见漂移。
6. **币安归档缺口**(未补填): 月 zip 内缺整日的「符号-日」在合格窗内 **896** 个(窗外 83), 涉及 330/362 个符号、207 个日期, 最多的是 2026-06-29(303 个符号)、2023-02-24(112)、2022-10-02(98)、2022-07-31(97)。抽查 3 个缺失日期的**日 zip 均存在**(HTTP 200, 约 800 字节; **内容未检视**)⇒ 按日补填可行, 但派工范围是月 zip, **本步未补, 交 lead 决定**。另: 370 个 2021–2022 月 zip 无表头(格式差异, 加载器已处理, 数据可用); LITUSDT 2025-08..12 在其合格窗内 5 个月 NOT_FOUND。
7. 过程中有两份修订性收据: **修订 1**(传输换 keep-alive, 规则不变)与**更正 1**(可行性结果把 Bithumb `Z` 字面误写为「空列表」, 已 d41f0b1b 更正)。


## §1 做了什么(与计划的对应)
- **范围**(冻结于 `pull/plan/PULL_PLAN_FROZEN.json`, 先于任何数据请求): 映射 PASS 的 KRW 市场 + 每所 KRW-BTC / KRW-USDT; 60m 与日 K, 自 max(普查首日, 2021-12-01T00Z) 至 PULL_END(冻结时刻取整点, 排他); 币安 futures/um indexPriceKlines 1h **月** zip, 每个映射符号取 [max(2021-12, 首个 C0 合格锚 − 62 天), min(2026-08, 末个合格锚 + 62 天)] 覆盖的月份(2026-09 尚无月 zip, 不在范围内), BTCUSDT 与 XRPUSDT 取全段。
- **机制**: 每主机一个进程并行; 每页 gzip 后写临时文件 → fsync → 原子改名, 然后 fsync 追加 JSONL 清单(含 body sha256); 续拉游标 = 已接受页的最老 bar 开盘; 每次运行开头三项控制(正控固定窗口 body sha 与首跑一致 / 负 `to` / 不存在代码), 任一不过即在任何数据请求前以 exit 2 中止; 非 200 或非列表 body = 错误, 从不写页, 市场留作未完成并在第二轮重试。
- **检查与守卫**的全部阈值写在冻结计划的 `checks` / `identity_guard` / `offset_spectrum` 段, 先于数据。
- **拉数位置**: `/Users/haosiyu/cc_tmp/krw_pull/`(非 iCloud 同步目录; 已核 `ls -lO` 无 dataless 标志)。数据与 HTTP 日志留在该处, 只把计划、控制、退出、完成/错误清单、检查与守卫收据、清单摘要复制入库(`pull/`)。

## §2 过程记录(照实)
1. **测试先行**(3 个测试根, 收据在 `pull/tests/`): 测试计划含一个**不存在的市场**(两所)与一个**不存在的币安符号-月**作为负夹具。v1 测试首跑时 Bithumb 负 `to` 控制不过(期望 `[]`, 实得 error 体)——**这暴露了可行性结果里的一个错误事实, 已作为更正 1 提交(d41f0b1b), 见 RESULT §13-9**; 控制规格改为「error 体」后: 中断(`--max-requests`)→ 续拉, 夹具市场以错误告终(never DONE)、夹具月为 NOT_FOUND 且被 C6 标 FLAG_MISSING_INDEX(红), 真实市场 C3 逐日恒等 EXACT、C4 FRESH; 单元中途中断 + 人为删掉最后一条清单行(模拟改名后崩溃)→ 续拉重取该游标、body sha 相同、无 REVISION、游标链完整。
2. **修订 1(传输, 09:38Z; `pull/plan/AMENDMENT_1_transport.json`)**: v1 进程受延迟约束而非限速约束(请求中位 378 ms Upbit / 504 ms Bithumb, 本地开销 7–9 ms, 每请求新建 TLS), Bithumb 预计 6.3 小时。keep-alive 基准(≤ 1 req/s, 与在跑进程合计 < 5 req/s)85–87 ms vs 新连接 376–385 ms。以 SIGTERM 按精确 PID 停 v1(停时全部清单文件以换行结尾, 无撕裂行), 在空闲主机上用新传输重跑测试(含注入撕裂行 → 启动时修复并记录), 写修订记录(新旧装置 sha), 再续拉。**范围、停止规则、控制、检查阈值、守卫判据均未改**。
3. 等待方式: 前台 until 循环(每次 ≤ 9.5 分钟, 检查进程存活、退出记录与进度), 未用监视器。

## §2b 补 A · lead 裁定之后(2026-09-13 12:4xZ 起)
**lead 裁定(派工原文要点)**: ① K3 与两所合并权重的 KRW 成交额**钉为小时和**(溢价本身由 4h 锚的小时 bar 构造), 日 K 不等清单保留为旗标收据; ② 币安指数价缺日**用日 zip 补**(约 979 请求), **12:50Z 之后**开始(实盘执行器 12Z 锚在本机网络上), **≤ 2 req/s**, 在接缝处用相邻月 zip 行核验内容(格式与首末小时连续), 然后在全史上**重算 G2**; ③ **G4 被采纳**为事前声明的数据质量剔除(KAVA / CRV / ENJ / SOLV / TAIKO 的 pair×month 格), 名单由 lead 写入冻结预注册; ④ **S1 止于 2026-08-30 20Z**(W_FULL 终点), 2026-09 未检查的 bar 不在范围内。**S1 预注册由 lead 冻结, 本步未改动。**
**hash 纪律(lead 同日另函)**: 本步所有新的 sha256 都从写入的内存字节计算(不事后重读); sha256(empty) 出现在非空 body 上即中止; 入库收据用 dataless 旗标 + 读取字节数 == st_size 的守卫(与 `T6/devices/t6_sha_guard.py` 同规则; 入库 `SHA256SUMS` 由该装置 `write` 生成并 `check` 通过)。**既往收据复核**: 仓库 T7 全部 180 个已提交文件经 t6_sha_guard `check` 0 不符、无 dataless; 收据中出现的全部 sha256(empty) 均为真实空内容(3 个 0 字节 stdout 日志、13 条 body_len = 0 的传输失败日志行), git 中无其他空 blob。**如实披露**: 已完成拉取的停止阈值是 3 GiB(lead 本次要求 5 GB, 补填步已按 5 GiB 执行; 已完成拉取期间两次 df 快照为 12 GiB(09:07Z)与 15 GiB(10:28Z), 进程内逐请求的 3 GiB 检查从未触发); 已完成拉取页清单里的 `file_sha256` 是写入后立即在 cc_tmp(非 iCloud 同步卷)重读计算的, `body_sha256` 来自内存字节; 两者均无 sha256(empty)。

- **补填结果**(P-12): 979 个目标 → 785 OK + 194 NOT_FOUND(LITUSDT 188 个 = 其 5 个月停摆; PUMP 4, ACH 1, CKB 1), 未解决 0; 979 次请求, 任意 1 s 最多 2 次, 最小间隔 0.500 s。780 个日 zip 格式全合格; 5 个为非整日边界日(7–15 行, 连续、close_time 正确): CTK 2025-04-30、CVC 2025-05-16、LIT 2025-07-10 与 2026-01-15、PUMP 2025-07-14。**内容核验**: 日 zip 与月 zip 同时存在的 56 个小时 OHLC 字符串**逐字相同 56/56**; 接缝 前 782/785、后 784/785 通过; 1 个价格跳变(CTK 2025-04-30 前接缝, 该日前 11 小时指数本身缺失, 跨停摆比较, 其 13 行与月 zip 重叠且逐字相同)、3 个邻接小时缺失(LIT 两端、PUMP 上市日)。
- **G2 全史命中率**(P-13; 锚 2021-12-01T04Z .. 2026-08-30T20Z, 10,403 个): **视图 U(草案 G2 格集)补后 38/38 个 所×年×定义 ≥ 0.99, 全过**; 补前 Upbit 2022 A 0.977 / 2023 A 0.989、Bithumb 2022 A 0.974 / 2023 A 0.987 不过。补后最低: Bithumb 2023 A 0.99543、2026 A 0.99613、2022 A 0.99687; Upbit 全部 ≥ 0.99928。视图 E(S1 宇宙)补后最低 Bithumb 2023 A 0.99539。剩余无效格以 **NO_KRW_BAR**(薄市场 4 小时窗内无成交)为主, 指数缺失已基本清零(剩 NO_INDEX_BAR ≤ 12/年、NO_BTC_BAR ≤ 46/年)。**G4 剔除后命中率变化 ≤ 0.00002**; 剔除格(视图 U): KAVA 1,272 A; CRV 366 A; ENJ 366 A; SOLV 366 A + 366 B; TAIKO 186 A + 186 B(G4 月份由冻结的同一性守卫收据算出, 恰为 lead 点名的五对)。

## §3 对后续(S1 草案冻结时)需要 lead 决定的数据问题(本步不改草案)
1. **KRW 成交量两种粒度不自洽**(C3 734 个市场日): 草案 K3 与两所合并权重用到 KRW 成交额, 冻结时须写死用 60m 求和还是日 K, 并声明不等日的处理(本步只标)。
2. **币安指数价缺日**(896 个符号-日): 这些日溢价无效, 会降低命中率; 是否用日 zip 补(约 979 个请求)须 lead 决定; G2 命中率须在最终面板上按全史复算。
3. **同一性旗标**(11 对): 草案 G4「越界对×月剔除」若被采纳, KAVA / CRV / ENJ / SOLV / TAIKO 等对应月份将被剔除, 须在冻结时确认。
4. 2026-09-01..09-13 的 KRW bar 已拉, 但无对应币安月 zip, **未做同一性检查**。

## §4 未验证与风险
- 墙钟回拨解释是推断(见 §0-3); 日 zip 内容未检视; 已下市韩国市场仍不在数据里(幸存者, RESULT §6)。
- 数据只在 `/Users/haosiyu/cc_tmp/krw_pull/`(不在 git); 若被清理, 须按入库的页清单(逐页 body sha256)复拉并逐字节核对。派生数组可由 `t7_pull_checks.py` 重建。
- 磁盘剩余约 12–15 GiB(使用率 97–98%)。

## §5 装置与复跑命令(逐字)
全部装置在 `devices/`, 运行副本在 `/Users/haosiyu/cc_tmp/krw_pull/devices/`(sha 记录于冻结计划与修订 1)。
```
cd /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T7/devices
python3 t7_pull_plan_freeze.py --root /Users/haosiyu/cc_tmp/krw_pull
bash t7_pull_launch.sh /Users/haosiyu/cc_tmp/krw_pull
# (修订 1: 停 v1 后以同一命令重启, 续拉)
cd /Users/haosiyu/cc_tmp/krw_pull/devices
python3 t7_pull_checks.py --root /Users/haosiyu/cc_tmp/krw_pull
python3 t7_pull_identity_guard.py --root /Users/haosiyu/cc_tmp/krw_pull
python3 t7_pull_offset_spectrum.py --root /Users/haosiyu/cc_tmp/krw_pull
python3 t7_pull_c3_detail.py --root /Users/haosiyu/cc_tmp/krw_pull
python3 t7_pull_c3_repull.py --root /Users/haosiyu/cc_tmp/krw_pull --venue upbit
python3 t7_pull_c3_repull.py --root /Users/haosiyu/cc_tmp/krw_pull --venue bithumb
python3 t7_pull_binance_gaps.py --root /Users/haosiyu/cc_tmp/krw_pull --probe 3
python3 t7_pull_binance_format_breakdown.py --root /Users/haosiyu/cc_tmp/krw_pull
python3 t7_pull_summarize.py --root /Users/haosiyu/cc_tmp/krw_pull
python3 t7_pull_fill_daily.py --root /Users/haosiyu/cc_tmp/krw_pull   # 12:50Z 之后
python3 t7_pull_g2_hitrate.py --root /Users/haosiyu/cc_tmp/krw_pull --elig <T7>/receipts/pod2/T7_universe_elig.npz
cd /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T7/devices
python3 t7_pull_collect.py --root /Users/haosiyu/cc_tmp/krw_pull --tests /Users/haosiyu/cc_tmp/krw_pull_test /Users/haosiyu/cc_tmp/krw_pull_test2 /Users/haosiyu/cc_tmp/krw_pull_test3
python3 t7_pull_addendum_tables.py
python3 t7_pull_assemble_addendum.py
```
测试根(`krw_pull_test`、`_test2`、`_test3`)的计划、控制、退出与检查收据复制在 `pull/tests/`。

## §6 数表(全部由 `devices/t7_pull_addendum_tables.py` 从 `pull/` 收据生成)
### P-1 配置
| 项 | 值 |
|---|---|
| 冻结计划 sha256 | `88f8e42478c135dff31a8db39ff97f8c1cfa8e5a0bd0d9754eee2a27588b1b1c` |
| 修订 1(传输) sha256 | `6bb5de9193871fb6107de0c0ece406837bc4e8ce0973afe16ec29beb70a2dead` |
| PULL_END(排他) / CUTOFF | 2026-09-13T09:00:00Z / 2021-12-01T00:00:00Z |
| KRW 市场数 Upbit / Bithumb | 234 / 352(映射 PASS 市场 + KRW-BTC + KRW-USDT) |
| 映射对 / 币安符号 / 符号-月 | 595 / 362 / 10937 |
| 限速 | 每主机任意 1 s 内 ≤ 5 次且间隔 ≥ 0.21 s, 三主机并行 |

### P-2 运行记录(controls / exits)
| 主机 | 运行 | 控制通过 | 退出码 | 本次数据请求 | 本次完成单元 | 本次错误 | 备注 |
|---|---|---|---|---|---|---|---|
| upbit | `20260913T091818Z_85081` | True | — | — | — | — | SIGTERM (修订 1 换传输, 无 exit 记录) |
| upbit | `20260913T093833Z_91893` | True | 0 | 22174 | 436 | 0 |  |
| bithumb | `20260913T091818Z_85083` | True | — | — | — | — | SIGTERM (修订 1 换传输, 无 exit 记录) |
| bithumb | `20260913T093833Z_91895` | True | 0 | 36991 | 680 | 0 |  |
| binance | `20260913T091818Z_85085` | True | — | — | — | — | SIGTERM (修订 1 换传输, 无 exit 记录) |
| binance | `20260913T093833Z_91897` | True | 0 | 8988 | 0 | 0 |  |

### P-3 文件数与体积(PULL_SUMMARY)
| 目录 | 文件数 | 字节 |
|---|---|---|
| binance | 10686 | 184759187 |
| binance_daily | 785 | 677956 |
| bithumb | 38662 | 354538802 |
| checks | 15 | 1632506 |
| derived | 1310 | 286577021 |
| devices | 15 | 103821 |
| logs | 7 | 41632249 |
| manifest | 6 | 34758792 |
| plan | 11 | 533468 |
| run | 22 | 19213 |
| upbit | 24522 | 220910830 |
| **合计** | 76041 | 1126143845(1.049 GiB) |

| 页文件 | 数 |
|---|---|
| bithumb/60m | 36908 |
| bithumb/days | 1754 |
| upbit/60m | 23445 |
| upbit/days | 1077 |

### P-4 完整性检查(CHECKS_T7_pull; 规则见冻结计划 checks)
| 项 | Upbit | Bithumb |
|---|---|---|
| 市场单元 完成/计划 | 468 / 468 | 704 / 704 |
| 完成原因 | {'FIRST_TRADE': 340, 'CUTOFF': 126, 'EMPTY_AT_FIRST_TRADE_OR_CUTOFF': 2} | {'FIRST_TRADE': 547, 'CUTOFF': 152, 'EMPTY_AT_FIRST_TRADE_OR_CUTOFF': 5} |
| 清单页数 / 撕裂行 / 孤儿文件 | 24522 / 0 / 0 | 38662 / 0 / 0 |
| 未完成单元 | 0 | 0 |
| C0 页完整性失败单元 | 0 | 0 |
| 重复 bar 单元 | 0 | 0 |
| C2 页缝断裂单元 | 0 | 0 |
| C1 最早 bar 不符单元 | 0 | 0 |
| C3 日量不等市场 | 25 | 107 |
| C4 新鲜度失败市场 | 0 | 0 |
| C3 检查的市场日 | 195244 | 318148 |
| C3 EXACT / ROUNDING / MISMATCH | 195180 / 32 / 32 | 317439 / 7 / 702 |
| C4 FRESH / THIN_OK / STALE_MISSING / NO_BARS | 234 / 0 / 0 / 0 | 341 / 11 / 0 / 0 |
| C5 尝试按状态 | {'200': 24528, '404': 2} | {'200': 38673} |
| C5 429 次数 / 任意 1 s 最大请求数 | 0 / 6 | 0 / 6 |
| C5 错误记录(类型) / 未解决 | 0 {} / 0 | 0 {} / 0 |

upbit C3 失败清单: KRW-ALGO, KRW-AWE, KRW-BTC, KRW-BTT, KRW-CHZ, KRW-DOGE, KRW-ETH, KRW-GLM, KRW-HBAR, KRW-HIVE, KRW-KNC, KRW-LINK, KRW-LSK, KRW-MANA, KRW-MTL, KRW-ONG, KRW-ONT, KRW-POL, KRW-POLYX, KRW-SAND, KRW-SNT, KRW-THETA, KRW-WAVES, KRW-XRP, KRW-ZIL

bithumb C3 失败清单: KRW-A, KRW-AAVE, KRW-ACE, KRW-ACH, KRW-ADA, KRW-ALGO, KRW-ALICE, KRW-ANKR, KRW-ARKM, KRW-ARPA, KRW-ATH, KRW-AVAX, KRW-AWE, KRW-AXS, KRW-BAT, KRW-BCH, KRW-BEL, KRW-BLUR, KRW-BNT, KRW-BONK, KRW-BRETT, KRW-BSV, KRW-BTC, KRW-CAKE, KRW-CELR, KRW-CHR, KRW-COS, KRW-COTI, KRW-CRV, KRW-CTSI, KRW-D, KRW-DOGE, KRW-DOT, KRW-DYDX, KRW-EIGEN, KRW-ENJ, KRW-ETC, KRW-ETH, KRW-FLOKI, KRW-FLUX, KRW-GAS, KRW-GLM, KRW-GMT, KRW-GRT, KRW-HIVE, KRW-HOOK, KRW-HYPER, KRW-ICX, KRW-ID, KRW-IN, KRW-IO, KRW-IOST, KRW-IOTA, KRW-JOE, KRW-JST, KRW-KAIA, KRW-KNC, KRW-KSM, KRW-LDO, KRW-LINK …

### P-5 币安指数价月 zip(C6)
| 项 | 值 |
|---|---|
| 计划符号-月 | 10937 |
| 状态计数 | {'NOT_FOUND': 251, 'OK': 10686} |
| 旗标计数 | {'PARTIAL_MONTH': 902, 'FORMAT_FAIL': 961, 'FLAG_MISSING_INDEX': 5} |
| 尝试按状态 / 任意 1 s 最大 / 错误记录 | {'200': 10688, '404': 253} / 5 / 0 {} |

PARTIAL_MONTH(902): 0GUSDT 2025-09 rows 206/720, 0GUSDT 2026-06 rows 696/720, 1000BONKUSDT 2023-11 rows 204/720, 1000BONKUSDT 2026-06 rows 696/720, 1000BTTCUSDT 2022-01 rows 159/744, 1000BTTCUSDT 2022-04 rows 696/720, 1000BTTCUSDT 2022-05 rows 720/744, 1000FLOKIUSDT 2023-05 rows 612/744, 1000FLOKIUSDT 2026-06 rows 696/720, 1000PEPEUSDT 2023-05 rows 637/744, 1000PEPEUSDT 2026-06 rows 696/720, 1000SHIBUSDT 2022-07 rows 720/744, 1000SHIBUSDT 2022-10 rows 720/744, 1000SHIBUSDT 2023-02 rows 648/672, 1000SHIBUSDT 2026-06 rows 696/720, 1000XECUSDT 2022-04 rows 696/720, 1000XECUSDT 2022-05 rows 720/744, 1000XECUSDT 2022-07 rows 672/744, 1000XECUSDT 2022-10 rows 720/744, 1000XECUSDT 2023-02 rows 624/672, 1000XECUSDT 2023-04 rows 672/720, 1000XECUSDT 2026-06 rows 696/720, 1INCHUSDT 2022-07 rows 720/744, 1INCHUSDT 2022-10 rows 720/744, 1INCHUSDT 2023-02 rows 648/672, 1INCHUSDT 2026-06 rows 696/720, 2ZUSDT 2025-10 rows 708/744, 2ZUSDT 2026-06 rows 696/720, AAVEUSDT 2022-07 rows 720/744, AAVEUSDT 2022-10 rows 720/744, AAVEUSDT 2023-02 rows 648/672, AAVEUSDT 2026-06 rows 696/720, ACEUSDT 2023-12 rows 328/744, ACEUSDT 2026-06 rows 696/720, ACHUSDT 2023-02 rows 624/672, ACHUSDT 2023-04 rows 672/720, ACHUSDT 2026-06 rows 696/720, ACXUSDT 2024-12 rows 613/744, ADAUSDT 2022-07 rows 720/744, ADAUSDT 2022-10 rows 720/744, ADAUSDT 2023-02 rows 648/672, ADAUSDT 2026-06 rows 696/720, AEROUSDT 2024-12 rows 659/744, AEROUSDT 2026-06 rows 696/720, AGLDUSDT 2023-07 rows 96/744, AGLDUSDT 2026-06 rows 696/720, AKTUSDT 2024-11 rows 302/720, AKTUSDT 2026-06 rows 696/720, ALGOUSDT 2022-07 rows 720/744, ALGOUSDT 2022-10 rows 720/744, ALGOUSDT 2023-02 rows 648/672, ALGOUSDT 2026-06 rows 696/720, ALICEUSDT 2022-07 rows 720/744, ALICEUSDT 2022-10 rows 720/744, ALICEUSDT 2023-02 rows 648/672, ALICEUSDT 2026-06 rows 696/720, ALLOUSDT 2025-11 rows 466/720, ALLOUSDT 2026-06 rows 696/720, ALTUSDT 2024-01 rows 157/744, ALTUSDT 2026-06 rows 696/720, ANIMEUSDT 2025-01 rows 200/744, ANIMEUSDT 2026-06 rows 696/720, ANKRUSDT 2022-04 rows 672/720, ANKRUSDT 2022-05 rows 720/744, ANKRUSDT 2022-07 rows 600/744, ANKRUSDT 2022-10 rows 720/744, ANKRUSDT 2023-02 rows 624/672, ANKRUSDT 2023-04 rows 672/720, ANKRUSDT 2026-06 rows 696/720, APEUSDT 2022-03 rows 348/744, APEUSDT 2022-07 rows 720/744, APEUSDT 2022-10 rows 720/744, APEUSDT 2023-02 rows 648/672, APEUSDT 2026-06 rows 696/720, API3USDT 2022-02 rows 182/672, API3USDT 2022-04 rows 672/720, API3USDT 2022-07 rows 600/744, API3USDT 2022-10 rows 720/744, API3USDT 2023-02 rows 624/672, API3USDT 2023-04 rows 672/720 …

FORMAT_FAIL(961): 0GUSDT 2026-06, 1000BONKUSDT 2026-06, 1000BTTCUSDT 2022-01, 1000BTTCUSDT 2022-03, 1000BTTCUSDT 2022-04, 1000BTTCUSDT 2022-05, 1000FLOKIUSDT 2026-06, 1000PEPEUSDT 2026-06, 1000SHIBUSDT 2021-12, 1000SHIBUSDT 2022-01, 1000SHIBUSDT 2022-03, 1000SHIBUSDT 2022-05, 1000SHIBUSDT 2022-10, 1000SHIBUSDT 2023-02, 1000SHIBUSDT 2026-06, 1000XECUSDT 2021-12, 1000XECUSDT 2022-01, 1000XECUSDT 2022-03, 1000XECUSDT 2022-04, 1000XECUSDT 2022-05, 1000XECUSDT 2022-07, 1000XECUSDT 2022-10, 1000XECUSDT 2023-02, 1000XECUSDT 2023-04, 1000XECUSDT 2026-06, 1INCHUSDT 2021-12, 1INCHUSDT 2022-01, 1INCHUSDT 2022-03, 1INCHUSDT 2022-05, 1INCHUSDT 2022-10, 1INCHUSDT 2023-02, 1INCHUSDT 2026-06, 2ZUSDT 2026-06, AAVEUSDT 2021-12, AAVEUSDT 2022-01, AAVEUSDT 2022-03, AAVEUSDT 2022-05, AAVEUSDT 2022-10, AAVEUSDT 2023-02, AAVEUSDT 2026-06, ACEUSDT 2026-06, ACHUSDT 2023-02, ACHUSDT 2023-04, ACHUSDT 2026-06, ADAUSDT 2021-12, ADAUSDT 2022-01, ADAUSDT 2022-03, ADAUSDT 2022-05, ADAUSDT 2022-10, ADAUSDT 2023-02, ADAUSDT 2026-06, AEROUSDT 2026-06, AGLDUSDT 2026-06, AKTUSDT 2026-06, ALGOUSDT 2021-12, ALGOUSDT 2022-01, ALGOUSDT 2022-03, ALGOUSDT 2022-05, ALGOUSDT 2022-10, ALGOUSDT 2023-02, ALGOUSDT 2026-06, ALICEUSDT 2021-12, ALICEUSDT 2022-01, ALICEUSDT 2022-03, ALICEUSDT 2022-05, ALICEUSDT 2022-10, ALICEUSDT 2023-02, ALICEUSDT 2026-06, ALLOUSDT 2026-06, ALTUSDT 2026-06, ANIMEUSDT 2026-06, ANKRUSDT 2021-12, ANKRUSDT 2022-01, ANKRUSDT 2022-03, ANKRUSDT 2022-04, ANKRUSDT 2022-05, ANKRUSDT 2022-07, ANKRUSDT 2022-10, ANKRUSDT 2023-02, ANKRUSDT 2023-04 …

FLAG_MISSING_INDEX(5): LITUSDT 2025-08, LITUSDT 2025-09, LITUSDT 2025-10, LITUSDT 2025-11, LITUSDT 2025-12

### P-11 C6 旗标拆因(BINANCE_FORMAT_BREAKDOWN)
| 项 | 值 |
|---|---|
| OK zip / FORMAT_FAIL(任一子项) | 10686 / 961 |
| 子项失败计数 | {'not_contiguous': 594, 'no_header': 370} |
| 子项按年 | {'not_contiguous': {'2026': 303, '2022': 156, '2023': 132, '2025': 3}, 'no_header': {'2022': 281, '2021': 89}} |
| 既无表头又不连续 | 3 |
| PARTIAL_MONTH: 上市/下市边界月 vs 内部月 | {'boundary_month': 271, 'internal_month': 631} |

### P-6 逐对价格同一性守卫(IDENTITY_GUARD_T7_pull)
| 项 | 值 |
|---|---|
| 对数 | 595 |
| 按状态 | {'PASS': 584, 'FLAG_DIVERGE': 10, 'FLAG_SCALE_SUSPECT': 1} |
| 检查小时数合计 / 每对中位 | 10379057 / 13246 |

| 所 | 币安符号 | KRW 市场 | 状态 | 检查天数 | 检查区间 | 分歧区间(起, 止, 天) | 尺度嫌疑区间 | 旗标区间内最大 \|m30\| |
|---|---|---|---|---|---|---|---|---|
| upbit | EOSUSDT | KRW-A | FLAG_DIVERGE | 1306 | ['2021-12-01', '2025-07-10'] | [['2025-06-20', '2025-07-10', 21]] |  | 0.442 |
| upbit | KAVAUSDT | KRW-KAVA | FLAG_DIVERGE | 1691 | ['2021-12-01', '2026-07-31'] | [['2022-12-25', '2023-02-12', 50], ['2023-02-14', '2023-02-23', 10], ['2023-02-25', '2023-04-06', 41], ['2023-04-09', '2023-06-06', 59]] |  | 0.53 |
| bithumb | CRVUSDT | KRW-CRV | FLAG_SCALE_SUSPECT | 1173 | ['2023-06-15', '2026-08-31'] | [['2023-08-14', '2023-09-12', 30]] | [['2023-08-04', '2023-08-09', 6], ['2023-09-10', '2023-09-12', 3]] | 1.319 |
| bithumb | DARUSDT | KRW-D | FLAG_DIVERGE | 760 | ['2023-01-27', '2025-02-28'] | [['2025-01-25', '2025-02-28', 35]] |  | 0.954 |
| bithumb | ENJUSDT | KRW-ENJ | FLAG_DIVERGE | 1722 | ['2021-12-01', '2026-08-31'] | [['2023-10-27', '2023-11-12', 17]] |  | 0.246 |
| bithumb | EOSUSDT | KRW-A | FLAG_DIVERGE | 1306 | ['2021-12-01', '2025-07-10'] | [['2025-06-20', '2025-07-10', 21]] |  | 0.442 |
| bithumb | FTMUSDT | KRW-S | FLAG_DIVERGE | 623 | ['2023-07-18', '2025-03-31'] | [['2025-02-08', '2025-03-02', 23], ['2025-03-20', '2025-03-31', 12]] |  | 0.301 |
| bithumb | KLAYUSDT | KRW-KAIA | FLAG_DIVERGE | 1115 | ['2021-12-01', '2024-12-31'] | [['2024-12-11', '2024-12-31', 21]] |  | 0.542 |
| bithumb | SOLVUSDT | KRW-SOLV | FLAG_DIVERGE | 553 | ['2025-01-24', '2026-07-31'] | [['2026-04-04', '2026-05-13', 40]] |  | 0.622 |
| bithumb | TAIKOUSDT | KRW-TAIKO | FLAG_DIVERGE | 446 | ['2025-06-11', '2026-08-31'] | [['2026-07-13', '2026-08-06', 25]] |  | 0.321 |
| bithumb | XVSUSDT | KRW-XVS | FLAG_DIVERGE | 1124 | ['2023-04-01', '2026-04-30'] | [['2026-04-14', '2026-04-30', 17]] |  | 0.346 |

### P-7 偏移谱时间戳守卫(逐年; OFFSET_SPECTRUM_T7_pull)
| 所 | 市场 | 年 | 小时 | KRW bar | 指数 bar | argmax ρ | ρ(−1)/ρ(0)/ρ(+1) | 离散度 argmin | 负控 KST(+9) | 负控 收盘标签(+1) | PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| upbit | KRW-BTC | 2021 | 744 | 742 | 744 | 0 | 0.85271 / 0.96249 / 0.89308 | 0 | 9 红 | 1 红 | True |
| upbit | KRW-BTC | 2022 | 8760 | 8751 | 8568 | 0 | 0.84987 / 0.9733 / 0.86049 | 0 | 9 红 | 1 红 | True |
| upbit | KRW-BTC | 2023 | 8760 | 8739 | 8664 | 0 | 0.838 / 0.95969 / 0.85004 | 0 | 9 红 | 1 红 | True |
| upbit | KRW-BTC | 2024 | 8784 | 8771 | 8784 | 0 | 0.82366 / 0.9469 / 0.83269 | 0 | 9 红 | 1 红 | True |
| upbit | KRW-BTC | 2025 | 8760 | 8743 | 8760 | 0 | 0.84072 / 0.95306 / 0.83609 | 0 | 9 红 | 1 红 | True |
| upbit | KRW-BTC | 2026 | 5832 | 5825 | 5808 | 0 | 0.84463 / 0.97163 / 0.84358 | 0 | 9 红 | 1 红 | True |
| upbit | KRW-XRP | 2021 | 744 | 742 | 744 | 0 | 0.85018 / 0.97286 / 0.89125 | 0 | 9 红 | 1 红 | True |
| upbit | KRW-XRP | 2022 | 8760 | 8751 | 8712 | 0 | 0.86358 / 0.98183 / 0.87032 | 0 | 9 红 | 1 红 | True |
| upbit | KRW-XRP | 2023 | 8760 | 8738 | 8736 | 0 | 0.88553 / 0.98748 / 0.89484 | 0 | 9 红 | 1 红 | True |
| upbit | KRW-XRP | 2024 | 8784 | 8769 | 8784 | 0 | 0.83016 / 0.97436 / 0.83232 | 0 | 9 红 | 1 红 | True |
| upbit | KRW-XRP | 2025 | 8760 | 8743 | 8760 | 0 | 0.86469 / 0.98531 / 0.86929 | 0 | 9 红 | 1 红 | True |
| upbit | KRW-XRP | 2026 | 5832 | 5825 | 5808 | 0 | 0.86841 / 0.98619 / 0.86702 | 0 | 9 红 | 1 红 | True |
| bithumb | KRW-BTC | 2021 | 744 | 736 | 744 | 0 | 0.84578 / 0.95706 / 0.89043 | 0 | 9 红 | 1 红 | True |
| bithumb | KRW-BTC | 2022 | 8760 | 8727 | 8568 | 0 | 0.84938 / 0.97375 / 0.85974 | 0 | 9 红 | 1 红 | True |
| bithumb | KRW-BTC | 2023 | 8760 | 8739 | 8664 | 0 | 0.83911 / 0.95963 / 0.85135 | 0 | 9 红 | 1 红 | True |
| bithumb | KRW-BTC | 2024 | 8784 | 8765 | 8784 | 0 | 0.82399 / 0.94763 / 0.83284 | 0 | 9 红 | 1 红 | True |
| bithumb | KRW-BTC | 2025 | 8760 | 8730 | 8760 | 0 | 0.84326 / 0.95528 / 0.84013 | 0 | 9 红 | 1 红 | True |
| bithumb | KRW-BTC | 2026 | 5832 | 5824 | 5808 | 0 | 0.84554 / 0.97373 / 0.84841 | 0 | 9 红 | 1 红 | True |
| bithumb | KRW-XRP | 2021 | 744 | 734 | 744 | 0 | 0.84357 / 0.97346 / 0.8948 | 0 | 9 红 | 1 红 | True |
| bithumb | KRW-XRP | 2022 | 8760 | 8727 | 8712 | 0 | 0.86369 / 0.98582 / 0.86855 | 0 | 9 红 | 1 红 | True |
| bithumb | KRW-XRP | 2023 | 8760 | 8743 | 8736 | 0 | 0.8871 / 0.98947 / 0.89727 | 0 | 9 红 | 1 红 | True |
| bithumb | KRW-XRP | 2024 | 8784 | 8764 | 8784 | 0 | 0.83193 / 0.97534 / 0.83276 | 0 | 9 红 | 1 红 | True |
| bithumb | KRW-XRP | 2025 | 8760 | 8731 | 8760 | 0 | 0.86561 / 0.98549 / 0.86945 | 0 | 9 红 | 1 红 | True |
| bithumb | KRW-XRP | 2026 | 5832 | 5823 | 5808 | 0 | 0.86885 / 0.9872 / 0.86821 | 0 | 9 红 | 1 红 | True |

汇总: {'n_cells': 24, 'n_pass': 24, 'n_neg_kst_red': 24, 'n_neg_close_red': 24, 'non_pass': [], 'no_data': []}

### P-9 C3 日量不等的明细与重拉核验(C3_MISMATCH_DETAIL / C3_REPULL_*)
| 项 | Upbit | Bithumb |
|---|---|---|
| 不等市场日 | 32 | 702 |
| 小时和 < 日量 / 小时和 > 日量 / 无小时 bar / 无日 bar | 17 / 15 / 0 / 0 | 696 / 6 / 0 / 0 |
| 是该市场首个检查日 | 0 | 10 |
| 按年 | {'2022': 32} | {'2021': 89, '2022': 393, '2024': 35, '2025': 22, '2023': 162, '2026': 1} |
| upbit 小时和/日量 [最小, p10, 中位, p90, 最大] | [0.9992, 1.0, 1.0, 1.0, 1.0005] | |
| bithumb 小时和/日量 [最小, p10, 中位, p90, 最大] | [0.6566, 0.9957, 0.9994, 1.0, 1.0006] | |
| 最集中的日期 | [['2022-02-11', 3], ['2022-01-27', 2], ['2022-01-14', 2], ['2022-02-10', 2], ['2022-02-09', 1]] | [['2024-08-24', 27], ['2025-10-21', 18], ['2022-12-09', 18], ['2022-01-14', 11], ['2022-04-25', 10]] |
| **重拉核验判决**(同一天 60m + 日 K 今天再取, 与存档逐字段比) | {'IDENTICAL': 32} / 32 | {'IDENTICAL': 702} / 702 |

### P-10 币安月 zip 内缺失的整日(BINANCE_ARCHIVE_GAPS; 未做任何补填)
| 项 | 值 |
|---|---|
| n_symbols | 362 |
| n_symbols_with_missing_hours | 330 |
| symbol_days_missing_inside_elig | 896 |
| symbol_days_missing_outside_elig | 83 |
| distinct_missing_dates | 207 |
| top_missing_dates | [['2026-06-29', 303], ['2023-02-24', 112], ['2022-10-02', 98], ['2022-07-31', 97], ['2022-07-25', 36], ['2023-04-08', 20], ['2023-04-07', 18], ['2022-07-24', 17], ['2022-04-27', 17], ['2022-07-27', 16], ['2022-07-28', 16], ['2022-07-30', 11], ['2023-02-13', 10], ['2022-04-17', 8], ['2022-05-10', 3], ['2025-07-10', 2], ['2025-07-11', 2], ['2025-07-12', 2], ['2025-07-13', 2], ['2025-07-14', 2]] |

| 日 zip 探针 | 状态 | 字节 |
|---|---|---|
| 0GUSDT 2026-06-29 | 200 | 800 |
| 1000SHIBUSDT 2023-02-24 | 200 | 828 |
| 1000SHIBUSDT 2022-10-02 | 200 | 824 |

### P-12 币安指数价日 zip 补填(FILL_DAILY_RECEIPT; lead 决定, 12:50Z 后开始, ≤ 2 req/s)
| 项 | 值 |
|---|---|
| 目标(符号, UTC 日) / 冻结目标 sha256 | 979 / `97eb9fe864a9c32dce801e9659ce54398aeb646afc14128a45fd42add95cf22d` |
| 装置 sha256 / 运行 | `98b7e0b10c1afc6f53fcc31cb352820311e638ddf4dac1e7933a35898f78b15f` / `20260913T125027Z_76132` |
| 状态计数 / 未解决 | {'OK': 785, 'NOT_FOUND': 194} / [] |
| 格式计数 | {'format_ok': 780, 'header': 564, 'no_header': 221, 'format_fail': 5} |
| 格式不过(均为非整日边界) | ['CTKUSDT 2025-04-30', 'CVCUSDT 2025-05-16', 'LITUSDT 2025-07-10', 'LITUSDT 2026-01-15', 'PUMPUSDT 2025-07-14'] |
| 接缝与重叠计数 | {'seam_prev_OK': 782, 'seam_next_OK': 784, 'days_with_overlap_mismatch': 0, 'overlap_hours': 56, 'seam_prev_PRICE_JUMP': 1, 'seam_next_NEIGHBOUR_MISSING': 1, 'seam_prev_NEIGHBOUR_MISSING': 2} |
| 价格跳变接缝 | [('CTKUSDT', '2025-04-30', 'PRICE_JUMP', 'OK', 13, 0)] |
| 邻接小时缺失 | [('LITUSDT', '2025-07-10', 'OK', 'NEIGHBOUR_MISSING'), ('LITUSDT', '2026-01-15', 'NEIGHBOUR_MISSING', 'OK'), ('PUMPUSDT', '2025-07-14', 'NEIGHBOUR_MISSING', 'OK')] |
| 限速设置 / 结束时剩余磁盘 | {'max_in_window': 2, 'min_gap_s': 0.5} / 27.86 GiB |

### P-13 G2 命中率全史(G2_HITRATE; 锚 2021-12-01T04:00Z .. 2026-08-30T20:00Z, 10403 个; 小时粒度)
| 视图 | 所 | 年 | 定义 | 格数(补后) | 命中率 补前 → 补后 | 补后且 G4 剔除 | 新鲜率(补后) | 补后无效原因 | ≥0.99 |
|---|---|---|---|---|---|---|---|---|---|
| U | upbit | 2021 | A | 8051 | 1.0 → 1.0 | 1.0 | 0.994535 | {} | 是 |
| U | upbit | 2022 | A | 102142 | 0.977365 → 0.999863 | 0.999863 | 0.998688 | {'NO_BTC_BAR': 14} | 是 |
| U | upbit | 2023 | A | 124858 | 0.989476 → 0.999279 | 0.999273 | 0.997596 | {'NO_KRW_BAR': 71, 'NO_BTC_BAR': 19} | 是 |
| U | upbit | 2024 | A | 178888 | 1.0 → 1.0 | 1.0 | 0.997948 | {} | 是 |
| U | upbit | 2025 | A | 296218 | 0.99999 → 0.99999 | 0.99999 | 0.997215 | {'NO_KRW_BAR': 1, 'NO_INDEX_BAR': 2} | 是 |
| U | upbit | 2026 | A | 281005 | 0.995626 → 0.999897 | 0.999897 | 0.990519 | {'NO_KRW_BAR': 29} | 是 |
| U | upbit | 2024 | B | 108354 | 1.0 → 1.0 | 1.0 | 0.997333 | {} | 是 |
| U | upbit | 2025 | B | 298408 | 0.99999 → 0.99999 | 0.99999 | 0.997222 | {'NO_KRW_BAR': 1, 'NO_INDEX_BAR': 2} | 是 |
| U | upbit | 2026 | B | 282457 | 0.995628 → 0.999897 | 0.999897 | 0.99056 | {'NO_KRW_BAR': 29} | 是 |
| U | bithumb | 2021 | A | 10233 | 1.0 → 1.0 | 1.0 | 0.982703 | {} | 是 |
| U | bithumb | 2022 | A | 139462 | 0.974215 → 0.996867 | 0.996867 | 0.985298 | {'NO_KRW_BAR': 433, 'NO_BTC_BAR': 4} | 是 |
| U | bithumb | 2023 | A | 204234 | 0.986912 → 0.995427 | 0.995415 | 0.951131 | {'NO_KRW_BAR': 887, 'NO_INDEX_BAR': 12, 'NO_BTC_BAR': 35} | 是 |
| U | bithumb | 2024 | A | 341717 | 0.998452 → 0.998452 | 0.998452 | 0.981731 | {'NO_KRW_BAR': 527, 'NO_BTC_BAR': 2} | 是 |
| U | bithumb | 2025 | A | 531688 | 0.997149 → 0.997149 | 0.997149 | 0.974088 | {'NO_KRW_BAR': 1511, 'NO_INDEX_BAR': 4, 'NO_BTC_BAR': 1} | 是 |
| U | bithumb | 2026 | A | 423416 | 0.99202 → 0.996134 | 0.996131 | 0.951337 | {'NO_KRW_BAR': 1591, 'NO_BTC_BAR': 46} | 是 |
| U | bithumb | 2023 | B | 19048 | 1.0 → 1.0 | 1.0 | 0.997008 | {} | 是 |
| U | bithumb | 2024 | B | 343913 | 0.998462 → 0.998462 | 0.998462 | 0.981837 | {'NO_KRW_BAR': 529} | 是 |
| U | bithumb | 2025 | B | 533878 | 0.997159 → 0.997159 | 0.997159 | 0.974185 | {'NO_KRW_BAR': 1513, 'NO_INDEX_BAR': 4} | 是 |
| U | bithumb | 2026 | B | 424868 | 0.992139 → 0.996253 | 0.99625 | 0.951401 | {'NO_KRW_BAR': 1592} | 是 |
| E | upbit | 2022 | A | 92645 | 0.975627 → 0.999849 | 0.999849 | 0.998597 | {'NO_BTC_BAR': 14} | 是 |
| E | upbit | 2023 | A | 118014 | 0.989425 → 0.999288 | 0.999282 | 0.997617 | {'NO_KRW_BAR': 66, 'NO_BTC_BAR': 18} | 是 |
| E | upbit | 2024 | A | 169834 | 1.0 → 1.0 | 1.0 | 0.99801 | {} | 是 |
| E | upbit | 2025 | A | 253165 | 0.999996 → 0.999996 | 0.999996 | 0.997745 | {'NO_KRW_BAR': 1} | 是 |
| E | upbit | 2026 | A | 181632 | 0.996069 → 0.999961 | 0.999961 | 0.995182 | {'NO_KRW_BAR': 7} | 是 |
| E | upbit | 2024 | B | 101618 | 1.0 → 1.0 | 1.0 | 0.997402 | {} | 是 |
| E | upbit | 2025 | B | 255355 | 0.999996 → 0.999996 | 0.999996 | 0.997748 | {'NO_KRW_BAR': 1} | 是 |
| E | upbit | 2026 | B | 183084 | 0.996067 → 0.999962 | 0.999962 | 0.99521 | {'NO_KRW_BAR': 7} | 是 |
| E | bithumb | 2022 | A | 128016 | 0.972113 → 0.996602 | 0.996602 | 0.984222 | {'NO_KRW_BAR': 431, 'NO_BTC_BAR': 4} | 是 |
| E | bithumb | 2023 | A | 195914 | 0.986754 → 0.995386 | 0.995374 | 0.95009 | {'NO_KRW_BAR': 871, 'NO_BTC_BAR': 33} | 是 |
| E | bithumb | 2024 | A | 322906 | 0.998483 → 0.998483 | 0.998483 | 0.982278 | {'NO_KRW_BAR': 488, 'NO_BTC_BAR': 2} | 是 |
| E | bithumb | 2025 | A | 450397 | 0.997318 → 0.997318 | 0.997318 | 0.979138 | {'NO_KRW_BAR': 1207, 'NO_BTC_BAR': 1} | 是 |
| E | bithumb | 2026 | A | 259707 | 0.994116 → 0.997851 | 0.997851 | 0.97165 | {'NO_KRW_BAR': 523, 'NO_BTC_BAR': 35} | 是 |
| E | bithumb | 2023 | B | 17958 | 1.0 → 1.0 | 1.0 | 0.996937 | {} | 是 |
| E | bithumb | 2024 | B | 325102 | 0.998493 → 0.998493 | 0.998493 | 0.982385 | {'NO_KRW_BAR': 490} | 是 |
| E | bithumb | 2025 | B | 452587 | 0.997329 → 0.997329 | 0.997329 | 0.979228 | {'NO_KRW_BAR': 1209} | 是 |
| E | bithumb | 2026 | B | 261159 | 0.994256 → 0.997994 | 0.997994 | 0.971677 | {'NO_KRW_BAR': 524} | 是 |

判据表(视图 U, 补后): 38 格, 不过 []

G4 剔除月份: [{'venue': 'bithumb', 'symbol': 'CRVUSDT', 'market': 'KRW-CRV', 'months': ['2023-08', '2023-09']}, {'venue': 'bithumb', 'symbol': 'ENJUSDT', 'market': 'KRW-ENJ', 'months': ['2023-10', '2023-11']}, {'venue': 'bithumb', 'symbol': 'SOLVUSDT', 'market': 'KRW-SOLV', 'months': ['2026-04', '2026-05']}, {'venue': 'bithumb', 'symbol': 'TAIKOUSDT', 'market': 'KRW-TAIKO', 'months': ['2026-07']}, {'venue': 'upbit', 'symbol': 'KAVAUSDT', 'market': 'KRW-KAVA', 'months': ['2022-12', '2023-01', '2023-02', '2023-03', '2023-04', '2023-05', '2023-06']}]

G4 剔除格数(视图 U, 补后): {'upbit KAVAUSDT': {'cellsA': 1272, 'cellsB': 0}, 'bithumb CRVUSDT': {'cellsA': 366, 'cellsB': 0}, 'bithumb ENJUSDT': {'cellsA': 366, 'cellsB': 0}, 'bithumb SOLVUSDT': {'cellsA': 366, 'cellsB': 366}, 'bithumb TAIKOUSDT': {'cellsA': 186, 'cellsB': 186}}

### P-8 入库的小件(COLLECT_RECEIPT)
| 项 | 值 |
|---|---|
| 复制文件数 / 字节 | 73 / 9858972 |
| 页清单 | committed as gzip (decompression asserted byte-identical to source)(gz 合计 7454141 字节) |

| 清单文件(数据在 cc_tmp) | sha256 | 字节 | 行 |
|---|---|---|---|
| done_bithumb.jsonl | `ebe93311c866f2ed…` | 108011 | 704 |
| done_upbit.jsonl | `d46d390a52040102…` | 70664 | 468 |
| pages_binance.jsonl | `3112e5cef70726e4…` | 6651861 | 10937 |
| pages_binance_daily.jsonl | `49c60b9be629f4dc…` | 527892 | 979 |
| pages_bithumb.jsonl | `df6a68ecf696e7d6…` | 16825986 | 38662 |
| pages_upbit.jsonl | `1846ef08f62e0f46…` | 10574378 | 24522 |
