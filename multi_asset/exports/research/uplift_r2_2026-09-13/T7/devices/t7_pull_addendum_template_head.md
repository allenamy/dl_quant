> **创建:** 2026-09-13 {{CREATED}} | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T7) | **状态:** RESULT_T7_feasibility 的**附录 1**: 全量拉取完成记录与完整性/守卫收据(**不含任何收益相关数字**) | **作废条件:** `pull/plan/PULL_PLAN_FROZEN.json` sha 与 `.sha256` 不符; 或 cc_tmp 数据被改写(逐页 body sha 见清单); 或任一检查装置被发现有缺陷
> **上游:** `RESULT_T7_feasibility.md`(§9 拉取计划, 更正 1 = §13-9); lead 派工(09:0xZ): 映射市场 · 自 2021-12 · 两所 · 币安 futures/um 指数价 1h 月 zip · 位置 `/Users/haosiyu/cc_tmp/krw_pull/` · 每主机 ≤ 5 req/s · 逐页原子写 + JSONL 清单 · 最老游标续拉 · 每次运行正负 `to` 控制 · 完整性检查 · 逐对滚动同一性守卫 · 逐年偏移谱 · 前台 until 循环等待 · 只提交小件 · 不动 S1 草案

# RESULT T7 · 附录 1 · 全量拉取

{{RESULTS_SUMMARY}}

## §1 做了什么(与计划的对应)
- **范围**(冻结于 `pull/plan/PULL_PLAN_FROZEN.json`, 先于任何数据请求): 映射 PASS 的 KRW 市场 + 每所 KRW-BTC / KRW-USDT; 60m 与日 K, 自 max(普查首日, 2021-12-01T00Z) 至 PULL_END(冻结时刻取整点, 排他); 币安 futures/um indexPriceKlines 1h **月** zip, 每个映射符号取 [max(2021-12, 首个 C0 合格锚 − 62 天), min(2026-08, 末个合格锚 + 62 天)] 覆盖的月份(2026-09 尚无月 zip, 不在范围内), BTCUSDT 与 XRPUSDT 取全段。
- **机制**: 每主机一个进程并行; 每页 gzip 后写临时文件 → fsync → 原子改名, 然后 fsync 追加 JSONL 清单(含 body sha256); 续拉游标 = 已接受页的最老 bar 开盘; 每次运行开头三项控制(正控固定窗口 body sha 与首跑一致 / 负 `to` / 不存在代码), 任一不过即在任何数据请求前以 exit 2 中止; 非 200 或非列表 body = 错误, 从不写页, 市场留作未完成并在第二轮重试。
- **检查与守卫**的全部阈值写在冻结计划的 `checks` / `identity_guard` / `offset_spectrum` 段, 先于数据。
- **拉数位置**: `/Users/haosiyu/cc_tmp/krw_pull/`(非 iCloud 同步目录; 已核 `ls -lO` 无 dataless 标志)。数据与 HTTP 日志留在该处, 只把计划、控制、退出、完成/错误清单、检查与守卫收据、清单摘要复制入库(`pull/`)。

## §2 过程记录(照实)
1. **测试先行**(3 个测试根, 收据在 `pull/tests/`): 测试计划含一个**不存在的市场**(两所)与一个**不存在的币安符号-月**作为负夹具。v1 测试首跑时 Bithumb 负 `to` 控制不过(期望 `[]`, 实得 error 体)——**这暴露了可行性结果里的一个错误事实, 已作为更正 1 提交(d41f0b1b), 见 RESULT §13-9**; 控制规格改为「error 体」后: 中断(`--max-requests`)→ 续拉, 夹具市场以错误告终(never DONE)、夹具月为 NOT_FOUND 且被 C6 标 FLAG_MISSING_INDEX(红), 真实市场 C3 逐日恒等 EXACT、C4 FRESH; 单元中途中断 + 人为删掉最后一条清单行(模拟改名后崩溃)→ 续拉重取该游标、body sha 相同、无 REVISION、游标链完整。
2. **修订 1(传输, 09:38Z; `pull/plan/AMENDMENT_1_transport.json`)**: v1 进程受延迟约束而非限速约束(请求中位 378 ms Upbit / 504 ms Bithumb, 本地开销 7–9 ms, 每请求新建 TLS), Bithumb 预计 6.3 小时。keep-alive 基准(≤ 1 req/s, 与在跑进程合计 < 5 req/s)85–87 ms vs 新连接 376–385 ms。以 SIGTERM 按精确 PID 停 v1(停时全部清单文件以换行结尾, 无撕裂行), 在空闲主机上用新传输重跑测试(含注入撕裂行 → 启动时修复并记录), 写修订记录(新旧装置 sha), 再续拉。**范围、停止规则、控制、检查阈值、守卫判据均未改**。
3. 等待方式: 前台 until 循环(每次 ≤ 9.5 分钟, 检查进程存活、退出记录与进度), 未用监视器。
