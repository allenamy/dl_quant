> **创建:** 2026-09-28 02:00 SGT | **Session:** acting-lead/research_resume_0927 | **状态:** final | **作废条件:** 输入、冻结 eligibility 轴/掩码、生成器或比较区间发生变化；本收据不能用作现金影响或候选通过证明。

149 条末端差异已全部解释，18 个同秒双事件标的全部不具备本 D10 冻结书层目标资格。未读取 q、targets、价格、收益或盲实验臂，未调用执行器/交易所。

- **149/149 末端行**：旧 `ft=1789776000`；新账 `ft_ms=1789776000001`，全部仅 +1 ms；各行费率完全相同，且 stream-D 原 `ts_ms/rate` 与新账逐值一致。根收据的精确共同上界是 `1789776000000` inclusive，因而裁掉全部 149 个新事件。完整末秒 `[1789776000000,1789776000999]` 则能逐一对应；没有把后续 8 天新增 horizon 混入此判断。
- **非人造终止行的代码证据**：`ax04_funding_ledger.py` L92–97 把 REST `fundingTime` floor 到秒，用 `t_s<=HI` 收录，并保留原 `ms`；L140–142 将它存为 `ts_ms`。`bt_funding_overlap.py` L95–108 只复制 P2≤CUT 和 stream-D>CUT，未添加末端占位事件。实际源 SHA 与生成时收据 `self_sha256` 相等；stream-D 输出 SHA→splice 输入 SHA→旧账 SHA 链一致。未重新解析原 REST gzip，故结论是已存储账本生成链事实，不是独立交易所历史认证。
- **18/18 资格**：`AAPL AVGO BABA CRM GOOGL HD HPE META MSFT NVDA QCOM QQQ SAMSUNG SPY STXX TSM WDC XLE`（均 USDT 后缀）在共同 829 symbol 轴上 `crypto=False`，且冻结 universe `pit` 全 10,152 行均 False。生产 8,142 锚区间 `1672531200..1789761600` 中 `book_legal = pit & member_mask & crypto` 均 False；事件落点 4h 锚都实际存在。member mask 本身有 True，因此不能把可交易 mask 或名字当书层合法性。未查看实际 q，不声称真实账户零持仓，也不把 ledger 粒度差异称为现金 bug。

完整逐行证据在 `BOUNDARY_POPULATION_FACTS.json`（149 条全量，不是前 24 条样本），源 `read_boundary_population.py`。`PROVENANCE.json` 绑定原 identity manifest、root 对比收据、生成器/书层源的当前 SHA 与既有生成收据。各大输入仅消费列清单中的字段：旧/新 ledger symbols/off/time/rate、stream-D symbols/sym/time/rate、feature symbols/anchors、冻结成员及 universe mask。未重 hash 3 GB feature/price。大输入 SHA 沿用先前 identity manifest，当前重新核 path/realpath/size 一致及打开 FD/路径 stat 在读取期间稳定；这不是当前全字节重认证。

`AX04` 源 SHA `f6417720ffdffac203dd32de88b589720c4de30c9162bb82bb0c0c8a566692e2`；splice 源 SHA `184670af1d38b3fc3102ef99f247eb03b6d1264d282bf1a7cda0737bfb0d98e8`；实际 `news2_combo.py` `81e2d274f2202755103a0dc3ab2fa31f8ff42c0da5000a3752708e34990d3201`，`book_universe.py` `90e332cc27cf8f34aabcac13f9829f84e463ffa900efbe554e17c07436e8dcca`。

执行于 Pod2，单线程、硬 `RLIMIT_AS=512 MiB`；exit=0，7 个事实检查全部成立，1.19 s，peak RSS 137,560 KiB。源码 SHA `3736c12c1206be5483363c5078992d2a4fc207959462f63feb824fddad4c0fb2`；结果 SHA `09c3ee9af7711fa1d902d852646e57c4416427c9290f8745d3117eee69960de6`。这是一项有完整枚举的只读事实核查，未新增模拟器测试。

复核命令（从此目录调用，只写调用者指定的新本地文件）：

```sh
ssh pod2 'env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -c '\''import sys,hashlib; raw=sys.stdin.buffer.read(); AUDIT_SOURCE_SHA=hashlib.sha256(raw).hexdigest(); exec(compile(raw,"read_boundary_population.py","exec"))'\''' < read_boundary_population.py > /tmp/d10_boundary_population_new.json
```

后续仍按独立 ms consumer/config/targets 与逐事件现金控制验收；本收据没有解除那些前置。现有 213 pins、D10/KSR 运行装置、root 台账及旧收据均未修改。
