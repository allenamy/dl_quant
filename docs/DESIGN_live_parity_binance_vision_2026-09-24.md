> **创建:** 2026-09-24 13:1xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(集成代理 C-4,受 lead 派) | **状态:** 设计稿。未取数、未跑、没有数字 | **作废条件:** 发布树 treeNC5(PATCH_RECEIPT 3135cf8b)被替换;`nc_parity_gate.py` 或 `nc_hist_features.py` 改动;lead 改指定的独立来源

# 设计:实盘锚的独立平价(data.binance.vision 日档)

相关文档:
- `docs/DEPLOY_producer_new_contract_2026-09-23.md` §0.2 第 7 项(部署前平价门)、§B;
- `docs/DESIGN_producer_new_contract_2026-09-23.md` §A3、§A4、§A9、§A7-6;
- 部署收据 `multi_asset/exports/research/nc_2026-09-23/receipts/deploy_2026-09-24T0500Z/`。

## 0. 为什么要做,缺什么

部署后首锚验收已覆盖五项:
- 模型身份(版本探针);
- 组合平价(comboparity 由快照重放组合,08Z 304/304、12Z 306/306 逐位);
- 执行器接受新钉;
- 下单;
- 对冲字段自洽(B7(b))。

没有独立验证过的是两段:
1. **实时数据摄入**:09-19 00Z(研究轴末 1789776000)之后,rolling.npz 的 5m 行都由服务端取数写入,包括 A1 的回填包和每锚的增量。
2. **服务端特征对研究侧**:King X78、成员集、资金费 EMA / 周期。
   - 研究侧装置 `nc_hist_features.py`(`Inputs`,L85–96)只读 pod2 上 `nc_prep.py` 的产物,轴止于 09-19 00Z。
   - 认证价格表 `price_full_raw_x0918r` 也止于 2026-09-19 00:00Z(pod2 实测)。
   - 用实盘快照同时喂两侧,只能证明服务端和它自己一致,不是平价(lead 2026-09-24 裁定,不改装置)。

lead 指定的独立原始来源:data.binance.vision 的 USDⓈ-M 5m K 线日档。
- 它和我们的 fapi 取数是两条独立路径;
- 它不占 fapi 的本 IP 权重。

## 1. 第一块:取数正确性(直接验证实盘数据摄入)

**对象**:最新快照 `~/wide_shadow/state/snap/<A>/rolling.npz`(只读副本)里 ts > 1789776000 的全部行。
- 不看轴末前的行:那些来自种子包,已被部署前的平价门和 A2 的逐位核对覆盖。
- 只看加密列(`crypto_axis.json`)。

**独立值的算法**:
- 取日档 `futures/um/daily/klines/<SYM>/5m/<SYM>-5m-<YYYY-MM-DD>.zip`,并用同目录的 `.CHECKSUM` 验 sha256。路径格式在运行前用一次 HEAD 实测,不按记忆写死。
- 用生产者自己的 `bars_to_channels`(treeNC5 `shadow_loop_v3.py` L470–480)和 `clipch`(L482–486)算出 7 个通道,存 float16。只 import 函数,不另写一份。
- 日档列顺序与 fapi K 线相同:open、high、low、close、volume、quote_volume、count、taker_buy_quote_volume 在同一位置。运行前逐列断言表头。
- ret5 只用紧邻前一行的 close;前一行缺失 ⇒ NaN(NC A3 的不跨缺口规则)。
- |ret5| 超过 f16 界值的格,原始收益 c/pc − 1 另算 float32,与快照的 `boundary_raw.npz` 比。

**比对与报出**:
- 逐格、逐通道比,判为不同的情况:f16 值不同,或 NaN 位置不同。
- 快照没有的行,与日档没有的行,分别计数,不算作相同。
- 报出:
  - 每通道不同的格数、max|diff|;
  - 涉及的名单;
  - 界值表条目数与不同条数。
- close 与 quote volume 不在 rolling 里单独存储:
  - close 经 ret5、range、cpos 进入;
  - quote volume 经 log_qv、log_avgsz、tbf 进入。
  - 因此判据在通道层。另外按 lead 要求,再列一张「由日档 close / qv 反推」的对照表,只作诊断。
- 已知会出现的名:SCRTUSDT、STORJUSDT、STGUSDT 在 09-24 13:01Z 为 SETTLING(exinfo 实测)。日档里它们的 bar 会中止,快照相应的行应为 NaN;这部分单列。

**判词**:`LIVE_INGEST_PARITY PASS`,当且仅当三类计数都为 0:不同格、单边缺行、界值不同。任何非零都逐格列出,交 lead,不放宽。

## 2. 第二块:特征平价(研究侧延展到 09-24 以后,原样跑平价门)

1. **延展研究侧输入**(pod2,新装置版本,先审后跑):
   - 用第 1 块下载的日档,把 `nc_prep.py` 的五个产物从 1789776000 延展到目标锚:`axes`(ts / anchors)、`cache_crypto`、`R_crypto`、`boundary`、`fund_state`。
   - R 的构造沿用认证价格表的约定(DESIGN §A3 研究员定义 1–3):
     - 未裁剪 bar 的收益 = f16 ret5;
     - 裁剪 bar 用 close 比复原;
     - 不跨缺口。
   - 这是 `nc_prep` 的一个新版本。先写单测与对旧轴的逐位回归,即延展前的所有行必须与现有产物逐位相同;lead 审过才跑。
2. **资金费事件的独立来源**(二选一,lead 定):
   - (a) 月度档 `futures/um/monthly/fundingRate/<SYM>/<SYM>-fundingRate-2026-09.zip`。9 月的档在 10 月初才发布,因此这条路最早 10 月初可跑。
   - (b) 静默窗内 fapi `GET /fapi/v1/fundingRate` 历史查询,逐名一次,`startTime` 为轴末,`limit` 1000(1h 周期 6 天为 144 条,一页足够):
     - 约 520 名 = 约 520 个请求;
     - 该端点另有「每 IP 每 5 分钟 500 次」的共享限额(按官方文档,运行时以响应头实测为准);
     - 按不超过限额的 50% 配速,每分钟 ≤ 50 个请求,约 11 分钟;
     - 本 IP 权重另按 `used_weight_1m` 记录,超过 1200 即中止;任何 429 / 418 都中止,不重试;
     - 逐请求落 `requests.jsonl`;
     - 启动前过 `venue_quiet_window` 自检,并排在其他取数任务之后(同今日 exinfo 的做法)。
   - 周期仍按 C-2 的时差规则(`nc_contract.snap_interval`)从事件时差推出,和研究侧同一个函数。
3. **重放**:用延展后的输入跑 `nc_hist_features.py` pass1 / pass2,只跑新增锚(09-24 08Z 起),再用 `nc_export_seed.py --parity` 导出这些锚的平价包。
4. **平价门**:在 Mac 上原样运行 `nc_parity_gate.py <treeNC5> <新平价包> <out>`,不改一行。
   - 比对量不变:m、X78、fe_v、fn_v、iv_v、qvm、rev24、base_val、btcv、X82、X89;
   - 两个负控 NC-F / NC-R 仍须测出;
   - 静默窗内运行,每锚开跑时须剩 ≥ 15 分钟(装置自检)。
5. **与实盘实际输出直接对照**(第 4 步通过之后的附加一格,新增只读脚本):研究侧重放的 King 秩 z 与成员集,和每锚快照 `aux.prev_rec` 里的 `legz.king` / `members` 逐位比;资金费 EMA 与快照 `aux.ema` 比。
   - 这一格回答的是「实盘链路本身」,不是「代码同一份」。
   - 若出现不同,先按第 1 块的结果归因(数据还是计算),再报。
6. **exchangeInfo 名单**:平价门对历史锚用 w24h 代理(DESIGN §A7-6)。对实盘锚,每个快照 `aux.fetch_syms` 里有真实的逐锚名单。
   - 改用真实名单需要给装置加一个选项,属于装置改动,单独提给 lead,本设计不自行加。
   - 在那之前照旧用 w24h,并在收据里并列真实名单与 w24h 名单的差集。

**判词**:`NC_PARITY_GATE` 原判词,加上第 5 步的 `LIVE_CHAIN_PARITY PASS/FAIL`(逐量计数)。

## 3. 什么时候跑、谁跑、在哪个窗

| 块 | 最早可跑 | 谁 | 在哪 |
|---|---|---|---|
| 第 1 块(摄入) | 目标锚所在日的日档与 `.CHECKSUM` 都已存在;覆盖 09-24 的锚,最早 09-25(UTC,次日发布)。用 HEAD 实测是否已存在,不按时刻假设 | 集成代理 | 下载与比对在 Mac,本机轻活,放在 Mac 静默窗内做。日档不走 fapi,但下载仍避开 N+12…N+30 |
| 第 2 块步 1–3(延展、重放、导包) | 第 1 块 PASS 之后;资金费用 (b) 时再加一个 Mac 静默窗 | 集成代理 | pod2(计算);资金费查询在 Mac 静默窗 |
| 第 2 块步 4–5(平价门、实盘链对照) | 平价包导出后 | 集成代理 | Mac 静默窗,每锚 ≥ 15 分钟 |

- 月度资金费档路线(2-a)最早 10 月初。若要在此之前出结论,用 2-b,并由 lead 批准权重预算。
- pod2 存储:`/workspace` 配额已满(df 显示的空闲不可信),下载与中间件放 `/dev/shm`,先 `dd` 实写探针。
- 报告:三块的判词行与 rc、收据路径,交 lead;每块单独提交入库,用显式 pathspec 并核 `git show --stat`。

## 4. 不做的事

- 不改 `nc_parity_gate.py` / `nc_hist_features.py`;要改的另提。
- 不用实盘快照充当研究侧参照。
- 不在 N+12…N+30 做本机重活。
- 资金费查询与其他 fapi 取数不叠加。
