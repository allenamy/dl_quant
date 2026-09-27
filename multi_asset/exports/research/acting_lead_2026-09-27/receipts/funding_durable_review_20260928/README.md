> **创建:** 2026-09-28 02:12 SGT | **Session:** acting-lead/research_resume_0927 | **状态:** final（审查反例，待实现修复） | **作废条件:** 两审阅源 SHA 或根设计合同改变；不能作为完整执行器验收结果。

仅只读审查独立 clone 相对 `841e771` 的两文件；设计见 `docs/DESIGN_funding_durable_ack_2026-09-27.md`。`ast_counterexamples.py` 只抽出指定 AST 定义，在内存中替换 I/O；没有 import 执行器模块、读生产状态、联网、跑 wrapper/suite 或修改 clone。源码、stdout、完整被审 diff 和 SHA/行号映射均落本目录。

1. **P1，继承的证据冲突仍未闭合** — `binance_funding.py:353–357,588–590`。同一精确 read_ts、同名两行 A=(qty10,notional200) 与 A=(qty5,notional100)，B=(qty5,notional100)，无 fills。后行覆盖使 gap 成功返回100；仅反转 A 行顺序就拒绝。fresh strict 同样在100/200间随行序变化，却都返回成功。必须在 snapshot 聚合前拒绝同键事实冲突；完全一致的重复可单列去重，不能由顺序裁决。这不是此次新增回归，也不是历史 disposition 红。
2. **P2，strict 日目录普查仍可漏掉损坏日** — `pilot_log.py:869–872`。`YYYYMMDD` 条目存在但为 regular file 时，stat成功后被 `S_ISDIR` 静默滤掉；AST 输入24目录/25文件/26目录得到仅24/26。`_GapEvidence` 用这个日列表搜 fills，故错误类型会变成未读取的零成交日。遇到合法日名的非目录条目应明确拒绝。当前权限/JSON损坏测试没有覆盖这个入口。
3. **P1，继承的部分追加失败后继续写仍能错误出队** — `pilot_log.py:469–474,552–553` 与 `binance_funding.py:971–995`。AST mock先给X写出10字符后抛I/O异常；调用方保留X但继续Y。Y的 `funding` 正常返回并ack，调用方将Y出队，但账本仅有一行“X截断前缀+Y完整JSON”，不能JSON解析。现D2注入fsync失败时之前的JSON已完整，未覆盖此类部分append。建议失败后隔离该写者/停止该批后续append并保留所有未确认行，或另有能证明完整记录的拒绝门；不要自动修剪历史坏尾。
4. **P2，条件性 FD 身份缺口，未证实生产触发** — `_w` 写长期fh，ack重新open路径，未绑定 dev/inode。AST模拟原写FD101、当前路径FD202，实际ack依次fsync202/目录303/root404并返回成功，101未确认。建议本轮将成功ack绑定写入FD及仍被路径引用的inode；检测到替换应拒绝并留队。**实际相关性有限**：scheduler:125单实例flock、:307每轮logger、:385 funding、:1097关闭；现行545回填装置:202–207为copy2备份+同目标append，没有replace。未找到正常已认证路径会在本次写者存活时换目标，故不声称发生过线上丢账；其成立条件是未经编码的路径不可替换假设。

反例均有断言，脚本exit0表示缺口被复现，不是修复通过。两源 SHA：funding `7e92718e3af06c729c38ca7dd38b865cd5cd9b6d1a1d6d3081e6780f7c650ec1`；pilot `73a69a4f14e833ea3a598ffa31fa8b482e787219ba466c0c9a7be68df898bda7`。脚本拒绝在源SHA改变后套用旧结论。root现有wrapper仍独立负责，未重复运行。
