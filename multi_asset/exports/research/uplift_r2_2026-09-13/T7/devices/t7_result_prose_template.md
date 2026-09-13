> **创建:** 2026-09-13 ~09:3xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T7) | **状态:** 可行性结果(数据工程; **不含任何收益相关数字**); 全量拉取**未启动**(本文写成时); **更正 1**(09:2xZ, Bithumb `Z` 字面的返回, 见 §13-9) | **作废条件:** 任一场所改变 K 线 API 行为(`to` 语义 / count 上限 / 下市可查性 / 错误体格式); 回放合格规则(A0 C0)或 `receipts/pod2/T7_universe_elig.npz`(sha256 `a530e123…`)被替换; 映射守卫收据 `MAPPING_guard_r2.json` 被推翻
> **上游:** `../PROGRAM_uplift_r2_2026-09-13.md` AMENDMENT 5(T7 定义)| 数据地雷来源(记忆): `ma_v3_track2_oi_positioning_closed`(吞掉的列表失败 / 分页静默截断)、`new_info_campaign_round1_2026_08_11`(命中率 + 偏移谱双守卫)、`f7_multiangle_sources_and_free_bookdepth`、`f2_basis_leg_judged_negative`、`young_listings_carry_fund_alpha` | **S1 草案:** `PREREG_T7_S1_DRAFT.md`(DRAFT, lead 冻结)

# T7 · 韩元市场溢价 · 数据可行性

## §0 结论(先读)
1. **可行, 但带三道硬约束。** (a) 两所官方 K 线 API 公开免 key, 当前在市市场的 60m 与 1m 历史完整回到开市(Upbit 2017-09-25, Bithumb 2013-12-27)。(b) **已下市市场查不到**: 两所官方 API 与 Upbit 网页 CDN 都返回与「从未存在的代码」逐字相同的 `Code not found`; CryptoCompare 免 key 通道已关(401)⇒ 历史样本是**幸存者子集**。(c) 对回放合格宇宙的覆盖**结构性低于 80%**: 两所并集按名 52.6%(2022)→ 64.5%(2026), 全期 58.5%; 实盘书按毛权重 59.2%。
2. **幸存者偏差已量化**(27 个网页存档快照): 快照时点「当时在该所 KRW 上市、今天查不到」的合格名占合格集: Upbit 0.5–5.0%, Bithumb 4.5–6.8%。市场层面: 2022H2 快照里 Upbit 20–25%、Bithumb 33–35% 的 KRW 市场今天查不到。
3. **对齐守卫在样本上全绿, 负控全红**: 因果断言 0 违例(负控 bar=N 全部违例); 命中率 1.000(两定义、两所); 偏移谱峰在 lag 0(BTC/ETH/XRP、两所; 负控 KST 当 UTC ⇒ +9、收盘时刻标签 ⇒ +1)。
4. **会静默造假的场所地雷**(全部有收据, 见 §2): Bithumb `to` 只认无时区的 KST 字面, 带 `Z`/`+09:00` 返回 **HTTP 200 + error 体 `Invalid parameter`**(**更正 1**: 原文误写为「空列表」, §13-9); Bithumb 的错误一律是 **HTTP 200 + error 体**; `count>200` 静默截成 200; 无成交小时不出 bar; Bithumb 240m/日 K 按 KST 对齐(Upbit 按 UTC); 场所改名后换代码且**保留历史**(MATIC→POL、EOS→A、FTM→S、STPT→AWE 等, 价格同一性 R≈1.00 已验); **Upbit KRW-STRAX(现名 Xertra)历史价被整体改了约 10 倍面额**(R = 0.0999); 场所停机(2026-07-05 17–20Z Upbit 全市场无 bar); 研究仓位于 iCloud 同步桌面, 文件会被驱逐成 dataless(读一次数秒)。
5. **全量拉取计划**(未启动): 全部在市 KRW 市场全史 + 币安指数价参照, 每主机 5 req/s、主机并行约 **3.5 小时墙钟**(Bithumb 62,639 / Upbit 40,300 / vision 11,330 请求, 均为上界), gz CSV ≤ 约 730 MB。
6. **S1 预注册草案** `PREREG_T7_S1_DRAFT.md`: 家族 N = 4(K1 溢价水平 / K2 24h 变化 / K3 KRW 成交集中度 / K4 溢价 × 高费率), 增量秩 IC 对 king+fund 复合、对 rev24 残差化、逐年同号; S2 以 ρ-to-A0 为主筛选; 覆盖冲突(80% 规则)给出三选一待 lead 冻结。

## §1 纪律与边界(执行记录)
- **未产生任何收益相关数字**: 无 IC、无与过去/未来收益的相关、无书 P&L。溢价只在样本上以守卫汇总出现(BTC 水平范围、XRP 两所之差), 用途是数据体检。偏移谱用的是**去趋势对数价格水平**的跨场所对齐, 不是收益。
- **只调公共行情**: api.upbit.com / api.bithumb.com 的 `/v1/market/all`、`/v1/candles/*`、`/v1/ticker`、`/public/candlestick`; data.binance.vision 归档; 幸存者兜底探针 crix-api-cdn.upbit.com(8 次)与 min-api.cryptocompare.com(4 次, 均 401); web.archive.org(71 次尝试: CDX 4 + 快照两轮各 27 + 传输错误重试 13)。**HTTP 客户端的主机白名单里没有任何币安 REST 主机**; 负控: `fapi.binance.com`、`api.binance.com/api/v3/account`、Upbit `/v1/orders`、Bithumb `/v1/accounts`、vision 路径穿越全部被断言拦截(§13-5)。无凭据。
- **限速**: 每主机最小间隔 0.25 s(约 4 req/s, 上限 5), 429 退避(Retry-After 或 2^n 秒), 418 立即致命停; 每次请求落 HTTP 日志(时刻、URL、状态、限速头、body sha256)。全部日志合计 4,472 次尝试: 200×4,413、404×42(下市/不存在代码探针, 含首跑中止的重复)、401×4(CryptoCompare)、传输错误×13(均重试成功); **429、418、5xx 均为 0**。
- **实盘树** `~/wide_shadow`、`~/dl_quant_live` **未触碰**。实盘书权重只读 T1 已拷进研究仓的 `T1/private/target_live/*.json`(132 份)。
- **pod2**: 只 CPU(nice 10、2 线程), 运行前后 GPU 0 % / 2 MiB, 研究员 PID 333197 / 339489 前后均为 Tl; 只写 `/workspace/uplift_r2_2026-09-13/T7/`。
- **他人目录**: T4/T5/T6/P2 未写; 只读过 T1 装置源码与 target_live 副本、T5 预注册首段(确认 target_live 语义)。

## §2 来源事实表(每条有现场探针收据)
| # | 事实 | Upbit | Bithumb | 收据 |
|---|---|---|---|---|
| F1 | K 线端点(已实测的单位) | `GET https://api.upbit.com/v1/candles/minutes/{1,60,240}`、`/days`、`/months`; 参数 `market`、`to`、`count` | `GET https://api.bithumb.com/v1/candles/minutes/{1,60,240}`、`/days`、`/months`(字段与 Upbit 同构) | `receipts/http_log_explore.jsonl`、`PROBE_A_conventions.json` |
| F2 | 字段 | market, candle_date_time_utc, candle_date_time_kst, opening/high/low/trade_price, timestamp, candle_acc_trade_price(KRW 成交额), candle_acc_trade_volume | 同 | explore |
| F3 | 每请求上限 | 200(201/1000 静默截成 200, HTTP 200) | 同 | T-1 |
| F4 | `to` 语义 | 按 bar 开盘时刻**排他**; 无时区字面按 **UTC**; `Z`、`+09:00` 均被正确解析 | 排他; 无时区字面按 **KST**; **`Z` / `+09:00` 字面返回 HTTP 200 + error 体 `Invalid parameter`**(更正 1, 原误写为空列表) | T-1、`receipts/CORRECTION_1_bithumb_to_spelling.json` |
| F5 | bar 标签 | **开盘时刻**; 返回进行中的 bar(最新标签 = 请求时刻向下取整) | 同 | T-1 |
| F6 | KST 标签 | = UTC + 9h(每根) | 同 | T-1 |
| F7 | `timestamp` 字段 | 最后更新毫秒; 1.5–3% 的 60m bar 超出收盘 ≤ 0.054 s(推断为处理延迟, 见 §11) | 始终在 [open, open+unit) 内 | T-1、`PROBE_A2_tsfield.json` |
| F8 | 已收盘 bar 事后改写 | 70 s 后重读 198 根 0 改变 | 同(0/198) | T-1 |
| F9 | 240m 对齐 | UTC 00/04/08/12/16/20(= 书的锚) | **KST** 00/04/…(= UTC 15/19/23/03/07/11, 与锚不齐) | T-1 |
| F10 | 日 K | UTC 日(00:00Z) | **KST 日**(15:00Z) | T-1 |
| F11 | 无成交区间 | **不出 bar**(从未见零量 bar) | 同 | T-2 |
| F12 | 限速(响应头) | `Remaining-Req: group=candles; min=600; sec=9` ⇒ 推断每 IP 每组 10/s、600/min | `x-ratelimit-remaining: 149` ⇒ 推断窗口上限 150 | T-1(**推断**: 头里是剩余数, 上限值由首请求剩余数 +1 推出; 未做压力测试, 按任务上限 5 req/s 执行) |
| F13 | 60m / 1m 历史深度 | KRW-BTC 60m 与 1m 均自 2017-09-25T03:00Z(开市) | 60m 自 2013-12-27T09:00Z, 1m 自 09:10Z(开市) | T-2 |
| F14 | 已下市市场 | **查不到**: HTTP 404 `Code not found`, 与从未存在的代码逐字相同; 13 个代码经网页存档确认曾在 Upbit KRW 上市(其中 STPT 为改名, 历史在 KRW-AWE 下) | **查不到**: **HTTP 200** + `{"error":{"name":404,"message":"Code not found"}}`, 与从未存在相同; 9 个代码经存档确认曾上市(含 LUNA 2020H1..2022H1、WEMIX 2021H1..2025H1; STPT 为改名) | T-2、`PROBE_B_depth.json`、`ARCHIVE_listings.json` |
| F15 | 幸存者兜底源 | 网页 CDN crix 对 WEMIX/LUNA 同样 404; CryptoCompare 免 key ⇒ 401 API key required | CryptoCompare 401 | `PROBE_C_survivorship.json` |
| F16 | KRW-USDT 市场起点 | 首根 60m 2024-06-07T09:00Z | 首根 60m 2023-12-07T03:00Z | T-2 |
| F17 | 改名 | 换代码并保留历史: KRW-POL 首日 2021-10-15(MATIC)、KRW-A 2018-03-22(EOS)、KRW-AWE 2020-03-24(STPT); 名称配对 KRW-TON → KRW-TOKAMAK; 旧代码查不到 | KRW-POL 2021-06-06、KRW-A 2017-12-11、KRW-S 2023-07-17(FTM)、KRW-KAIA 2021-05-13(KLAY)、KRW-RENDER、KRW-D(DAR)、KRW-FRAX(FXS)、KRW-AWE | `CENSUS_krw_markets.json` + T-4(R 在币安旧符号最后合格时刻验证) |
| F18 | 历史改面额 | **KRW-STRAX(Xertra)R = 0.0999**(2024-03-16 对币安 STRAXUSDT)⇒ 历史价被按约 10× 重标; OM→MANTRA R = 0.254(1:4 类互换) | — | T-4 |
| F19 | 场所停机 | 样本内 2026-07-05 17/18–20Z 六个 Upbit 市场同时无 bar, 日量恒等式仍成立 ⇒ 停机不是丢数 | 样本内无 | `sample/SAMPLE_MANIFEST.json` |
| F20 | 在市规模 | 288 个 KRW 市场(2026-09-13 普查, 0 错误) | 482(0 错误) | T-3 |
| F21 | 历史上市清单 | 网页存档 11 个半年快照 2021H1–2026H2(117 → 283 个 KRW 市场) | 16 个快照 2018H1–2026H1(37 → 449) | `ARCHIVE_listings.json`、`PROBE_D_archive_cdx.json` |
| F22 | 币安参照 | data.binance.vision `futures/um/{daily,monthly}/indexPriceKlines/<SYM>/1h/`: 有表头、open_time 毫秒、逐小时连续、close_time = open + 3599999; 1000 前缀符号的指数价按 1000 单位报价(映射守卫中 1000PEPE / 1000SHIB / 1000BONK / 1000FLOKI / 1000XEC 以乘数 1000 PASS, R 0.993–1.006) | — | T-8、`MAPPING_guard.json` 预检 |
| F23 | 场所自带标记 | `market/all?isDetails=true` 的 `market_event.caution` 含 `GLOBAL_PRICE_DIFFERENCES`、`CONCENTRATION_OF_SMALL_ACCOUNTS`(**只有当下快照, 无历史**) | `market_warning`(同, 仅当下) | `receipts/raw/*market_all*.json.gz` |

## §3 时间戳约定与 `to` 语义
{{T-1}}

## §4 历史深度、下市可查性、在市普查
{{T-2}}

{{T-3}}

## §5 映射与覆盖
### §5.1 回放「合格名」的定义(引用源码, 已逐锚复核)
- A0 旋钮: `uplift_2026-09-11/r18_foundation/devices/r18_drive.py` L53–55(`MEMBERS_TOPN=829`, `UMASK_SCOPE=m1`, `UMASK_NPZ=…/masks/umask_UPIT_CRYPTO.npz`)。
- 规则: `T1/devices/w10_sleeve_t1.py` L81–86(成员 = 该锚 qvk 有限的全部名)、L229–232(∩ UPIT_CRYPTO 掩码)、L255–256(`sel = isfinite(y4[i,m]) & qv4h ≥ 2.5e5`, `qv4h = expm1(clip(qvk,0,30))·48`)、L262(`sel.sum() < 80` 跳锚)。NW 臂(R18_ELIG=1)为因果版 `isfinite(y4[i-1,m])`。
- 装置 `devices/t7_universe_pod2.py`(sha256 `f4bf8723…`)在 pod2 上按上式重建逐锚合格集, **y4 只经 isfinite() 使用**; 与存档 r18 臂 `C0_s42.npz` / `NW_s42.npz` 的 `rec` 第 8 列(sel.sum())与第 9 列(len(m))逐锚比对: **10,039 锚, 两臂 × 两个 rec 数组, 差异 0**(见 T-5 分母复核)。
- 注意: 面板里 `qvk` 对 829 名在全窗都是有限值, **不能用来判断币安上市时间**; 映射检查时刻改用各名「最后一个 C0 合格锚」。
### §5.2 映射规则(先于任何价格写死, 装置 docstring)
- 去 `USDT`; 乘数前缀 `1000000`→1e6、`1000`→1e3、`1M`→1e6(仅当后接字母)。
- 候选 = [基名] + 手工表 + [基名+`2`](韩所消歧后缀, 仅在守卫 PASS 时接受)。手工表 r1: BEAMX→BEAM, DODOX→DODO, LUNA2→LUNA, BTTC→BTT, MATIC→POL, FTM→S, EOS→A, RNDR→RENDER, KLAY→KAIA, AXL→WAXL; r2(存档揭示的改名): STPT→AWE, DAR→D, FXS→FRAX, OM→MANTRA。**故意不映射**(非 1:1 互换破坏价格水平): GAL→G, MKR→SKY, AGIX/OCEAN→FET, NU/KEEP→T。
- **价格同一性守卫**(阈值先于运行冻结): 检查时刻 T = min(2026-08-30T23Z, 该名最后 C0 合格锚 − 1h); `R = (P_krw(币)/P_krw(BTC)) / ((P_idx(符号)/乘数)/P_idx(BTCUSDT))`, 同所同 T; |ln R| ≤ ln 1.25 PASS, ≤ ln 2 REVIEW, 其余 FAIL; KRW bar 陈旧 > 24h 记 STALE; KRW 首日 > T − 2d 记 NO_OVERLAP_AT_T。**只有 PASS 计入覆盖**。

{{T-4}}

### §5.3 覆盖率
{{T-5}}

**读法**: Bithumb 贡献了并集的绝大部分(并集只比 Bithumb 高 0.3–6.0 个百分点); 两所都有的名 26.9–44.6%。覆盖在 2026 年最高, 与「新上市名在韩国上得快」一致(推断, 未测)。**按 F7 §P0 的 80% 规则, 任何在这个子集上的 S1 都只能算「子集预读」**(草案 §5 给出三选一)。

## §6 幸存者偏差
{{T-6}}

**读法**: (1) 市场层面「今天查不到」的比例随时间单调上升: 越早的快照, 越多 KRW 市场已下市。**上界**把所有消失的代码都算作下市; **下界**扣掉「今天在市、首日早于快照、却不在快照里」的代码数(它们可能是改名目标)。(2) 对合格宇宙的冲击小于市场层面(因为很多已下市韩国币根本不在币安合格集里), 但方向不可知: 韩国下市前常先有「投资警示」与极端散户交易, 正是本假说要找的事件 ⇒ **缺的恰可能是信号最强的样本**。(3) 「当时按 ticker 在市」列未经价格验证(下市代码无价可验), 三列来自不同映射路径, 相加不严格闭合(差 ≤ 0.5 个百分点)。(4) Bithumb 2018–2021 快照早于回放窗, 只作市场层面参考。

## §7 溢价定义与对齐守卫(样本 2026-07-01..08-29, 360 锚)
- **取数**: 锚 N 取币 i 的 60m bar `o = max{open : N−4h ≤ open ≤ N−1h}`(收盘 ≤ N); 币安指数价取同一根 `o`; 缺则无效。
- **def A(经 BTC 消去汇率)**: `pA = [ln P_krw,i(o) − ln(P_idx,i(o)/m_i)] − [ln P_krw,BTC(o) − ln P_idx,BTC(o)]`(同所、同 bar)。
- **def B(所内 KRW-USDT)**: `pB = ln P_krw,i(o) − ln(P_idx,i(o)/m_i) − ln P_krw,USDT(u)`, `u` = [o−3h, o] 内最近的 USDT bar。
- **一条水平事实(非收益)**: 样本内 BTC 的 pB 在 [−0.19%, +0.26%], 中位 ≈ 0 ⇒ **KRW-USDT 市场价本身带着国家级溢价**, def A 与 def B 都是「币相对」溢价, 都不测国家级溢价(若要国家级溢价须另接官方汇率, 但它在横截面秩里被消掉)。
- 守卫判据写在 `devices/t7_sample_guards.py` docstring, 先于运行。

{{T-7}}

## §8 样本拉取(≤ 10 个 KRW 市场、60 天)
- 市场: Upbit KRW-BTC / USDT / ETH / XRP / PEPE(×1000 → 1000PEPEUSDT)/ POL(改名市场); Bithumb KRW-BTC / USDT / XRP / SHIB(×1000)。参照: 6 个币安符号 indexPriceKlines 1h 月 zip。
- 机制与全量拉取相同: 60m 按页倒翻(count=200, `to` = 上一页最老 bar 开盘, 排他; Bithumb 用无时区 KST 字面); 页只在「HTTP 200 且 body 是 JSON 列表」时接受; 停止规则: 最老 bar 早于窗口起点, 或短页且已到普查首日, 否则 ABORT(防分页静默截断)。
- 验证: V1 bar 唯一递减; V2 整点; V3 页缝; **V4 日量恒等式**(窗口内每个场所日, 小时量之和 = 日 K 量; Upbit UTC 日 / Bithumb KST 日; 相对差 ≤ 1e-9 精确、≤ 1e-6 仅舍入、否则不等); V5 币安 zip 行数 = 月小时数、毫秒、连续、close_time = open + 3599999。
- **60 天上限**: 日 K 文件起初写入了整页 200 天, 已由 `devices/t7_sample_trim_days.py` 裁到与窗口相交的场所日(Upbit 60 行 / Bithumb 61 行; 修改前后 sha 记入清单; V4 只用窗口内完整日, 结果不变; 裁剪后守卫重跑输出 `receipts/guards_stdout_after_trim.txt`)。「≤ 10 个市场」按 KRW 市场计(10 个), 另有 6 个币安参照序列。
- **样本数据在盘, 但不在 git**: 仓库根 `.gitignore` 忽略 `*.csv.gz` 与 `*.npz`(与 T1/T5 的 npz 收据同样处理), sha256 全部列在 `SHA256SUMS` 与 `sample/SAMPLE_MANIFEST.json`(后者入库, 含每页 body sha256)。

{{T-8}}

## §9 全量拉取计划(未启动)
{{T-9}}

- **范围建议**: S-ALL/H-FULL(全部在市 KRW 市场, 全史)。理由: K3(KRW 成交集中度)的分母需要全所成交额; 全史给 2022-01-31 首锚之前足够暖机。墙钟 = 各主机并行 ≈ max(Bithumb 3.48 h, Upbit 2.24 h, vision 0.63 h) ≈ **3.5 h @ 5 req/s**(4 req/s 下 4.35 h)。请求数是上界(无成交小时不出 bar, 实际页数更少)。
- **断点续拉**: 每市场一个目录, 每页一个文件(文件名含游标 `to`), 写临时文件后原子改名; 追加式清单 JSONL(url、游标、行数、最新/最老 bar、body sha256); 重启时从清单里该市场最老游标继续; 同一页重复拉取须 body sha 相同, 否则记「事后改写」并停。
- **文件 = 应有范围的核验**(针对 OI 拉数的「列表与文件同时被截断」地雷, 不能只比文件数): (1) 该市场最老 bar 的开盘日 = 普查首日(普查是独立的月 K/日 K 路径); (2) 页缝: 每页最新 bar < 上一页最老 bar; (3) **V4 日量恒等式逐市场逐日**(独立的日 K 路径), 不等 ⇒ 该日重拉; (4) 最新 bar ≥ 拉取开始时刻 − 1h(在市市场); (5) 普查 `n_months_present` 与小时数据覆盖的月份集合一致。
- **HTTP 错误 ≠ 真空结果**: 非 200 或 body 非列表(含 Bithumb 的 200 + error 体)= 错误 ⇒ 退避重试, 超限记入错误清单, **从不写空文件**; 空列表只在「游标已早于普查首日」时被接受为真空, 其余空列表 = 错误(防任何未预期的空列表; Bithumb 时区字面实为 200 + error 体, 本就按错误处理, 更正 1)。每次运行开头: 正控(已知窗口必须非空)+ 负控(Upbit: 开市前的 `to` 必须是空列表; Bithumb: `Z` 字面必须是 error 体; 两所: 不存在的代码必须是 Code not found), 任一变化 ⇒ API 行为变了 ⇒ 停。
- **同一性与改面额**: 全史逐对 30 日滚动 |pB| 中位 ≤ ln 1.25, 越界的对×月剔除并列表(STRAX/Xertra 类)。
- **存储位置**: **不要放在 iCloud 同步目录**(本研究仓在 `~/Desktop`, 本轮已观察到 `T1/private/target_live` 文件被驱逐成 `compressed,dataless`, Python 读每文件数秒); 建议本机非同步目录或 jpline, 完成后清单 sha 入研究仓。币安 vision 大批量从本机拉(记忆: jpline 到 vision 慢 35×)。
- **前向采集(建议, 非本步)**: `market_event.caution.GLOBAL_PRICE_DIFFERENCES` 等场所标记只有当下快照, 若将来要用须从现在起每锚存档。

## §10 开放风险
1. **幸存者偏差(最大)**: 下市韩国币不可查; 丢失的正是「投资警示 → 下市」这类可能信号最强的名; 方向不可知(§6)。任何 S1 结论必须带「幸存者子集」范围, 草案要求 2025–26 子期同号。
2. **覆盖 < 80%**: 与 F7 规则冲突, 须 lead 事前选 O1/O2/O3(草案 §5)。
3. **改名/改面额**: 存档里「今天在市、首日早于某快照却不在该快照」的改名候选代码 Upbit 11 个、Bithumb 21 个; 其中经价格同一性验证的 1:1 改名 8 对(MATIC→POL、EOS→A、FTM→S、KLAY→KAIA、RNDR→RENDER、STPT→AWE、DAR→D、FXS→FRAX), 名称配对 TON→TOKAMAK 与 OM→MANTRA(后者非 1:1, 映射 FAIL), 其余只进上下界。历史改面额已见 1 例(STRAX/Xertra), 未见的须靠全史滚动同一性守卫捕获。BTT 2022 年改面额(新 BTT 1:1000)应落在 Upbit KRW-BTT 的历史内 —— **这是依公开事件的推断, 本轮检查时刻在其之后, 未用数据看到断点**。
4. **时间戳**: 本轮只在 2026-07/08 两个月上验证; 历史年份(尤其 Upbit 2017–2019)的标签约定未验证 ⇒ 偏移谱必须逐年复跑。Upbit `timestamp` 超出收盘 ≤ 54 ms 的解释(处理延迟)是**推断**。
5. **场所停机与薄市场**: 停机时段无 bar(回退规则最多 3 根); 薄市场的「最近 bar」可能陈旧 3 小时, 溢价与参照价同 bar 对齐但与锚不同步。
6. **API 行为漂移**: Bithumb v1 端点在网页存档中最早的 `v1/market/all` 快照是 2025-01-19(上线日期未查), `to` 语义或错误体格式可能变; 每次运行开头的正/负控可以抓到。
7. **限速上限是推断**(F12); 按 5 req/s 执行不依赖该推断。
8. **两所合并与 KRW-USDT**: def B 不含国家级溢价(§7 水平事实); 若假说需要国家级溢价, 须另立数据源。
9. **iCloud dataless**: 研究仓文件会被驱逐, 读取变慢但不丢数; 拉数不得写在同步目录。
10. **样本与合格集数据不在 git**(根 `.gitignore`), 只有 sha 入库; 他机复核须复拉或另行拷贝。

## §11 已验证 vs 推断
**已验证(本轮现场收据)**: F1–F11、F13–F22 全部; 合格宇宙分母与存档 r18 臂逐锚 0 差; 映射 PASS/FAIL/REVIEW 全表; 覆盖率与幸存者表; 样本 V1–V5; 守卫 G1–G3 及其负控; 客户端拦截负控。
**推断(未直接证实)**: F12 限速上限数值(由剩余数 +1 推出); Upbit `timestamp` 超出收盘是处理延迟; BTT 2022 改面额落在 Upbit KRW-BTT 历史内; STRAX/Xertra 是场所对历史价的改面额(另一解释: 当时 Upbit 与币安不是同一资产; 两种解释下该对都不可用); 「新上市名在韩国上得快」; 幸存者偏差的方向; 改名下界(把未解释的新代码都当作改名目标)。

## §12 装置、收据与复跑命令(逐字; 均在 `T7/` 目录下运行)
| 装置 | 作用 | 输出 |
|---|---|---|
| `devices/t7_http.py` | 公共行情客户端(白名单、限速、退避、日志) | — |
| `devices/t7_explore.py` | 首次接触形态探针 | `receipts/http_log_explore.jsonl` |
| `devices/t7_probe_a_conventions.py` | 时间戳 / `to` / count | `receipts/PROBE_A_conventions.json` |
| `devices/t7_probe_a2_tsfield.py` | `timestamp` 字段位置 + 70 s 重读 | `receipts/PROBE_A2_tsfield.json` |
| `devices/t7_probe_b_depth.py` | 历史深度二分 / USDT 起点 / 下市可查 / 缺口 | `receipts/PROBE_B_depth.json` |
| `devices/t7_probe_c_survivorship.py` | 幸存者兜底源 | `receipts/PROBE_C_survivorship.json` |
| `devices/t7_probe_d_archive_cdx.py` | 存档 CDX 索引 | `receipts/PROBE_D_archive_cdx.json` |
| `devices/t7_census_krw.py` | 在市 KRW 普查 | `receipts/CENSUS_krw_markets.json`、`receipts/raw/*market_all*.json.gz` |
| `devices/t7_archive_listings.py` | 存档快照上市集合 | `receipts/ARCHIVE_listings.json`(原始体在 `private/archive_raw/`, gitignored) |
| `devices/t7_universe_pod2.py` | pod2: 合格宇宙 + 存档臂复核 | `receipts/pod2/RECEIPT_T7_universe_pod2.json`、`T7_universe_elig.npz` |
| `devices/t7_mapping_guard.py` / `t7_mapping_guard_r2.py` | 映射 + 价格同一性守卫 r1 / r2 | `receipts/MAPPING_guard.json` / `MAPPING_guard_r2.json` |
| `devices/t7_coverage.py` | 覆盖率 / 实盘权重覆盖 / 幸存者 | `receipts/COVERAGE_T7.json` |
| `devices/t7_sample_pull.py` | 样本拉取 + V1–V5 | `sample/*`、`sample/SAMPLE_MANIFEST.json` |
| `devices/t7_sample_trim_days.py` | 日 K 文件裁到 60 天窗口 | `sample/*_days.csv.gz`、清单 `days_trim` |
| `devices/t7_sample_guards.py` | 溢价定义 + G1–G3 + 负控 | `receipts/GUARDS_sample.json` |
| `devices/t7_pull_plan.py` | 全量预算 | `receipts/PLAN_full_pull.json` |
| `devices/t7_result_tables.py` | 从收据生成本文全部数表 | `receipts/TABLES_T7.md` |
| `devices/t7_assemble_result.py` + `devices/t7_result_prose_template.md` | 模板 + 数表 ⇒ 本文(逐字节可复现) | `RESULT_T7_feasibility.md` |

复跑命令(逐字):
```
cd /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T7
python3 devices/t7_explore.py
python3 devices/t7_probe_a_conventions.py
python3 devices/t7_probe_a2_tsfield.py
python3 devices/t7_probe_b_depth.py > receipts/probe_b_stdout.txt 2>&1
python3 devices/t7_probe_c_survivorship.py
python3 devices/t7_probe_d_archive_cdx.py
python3 devices/t7_census_krw.py > receipts/census_stdout.txt 2>&1
python3 devices/t7_archive_listings.py
# pod2, 目录 /workspace/uplift_r2_2026-09-13/T7:
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 nice -n 10 /workspace/venv/bin/python devices/t7_universe_pod2.py PATH,HOME,OMP_NUM_THREADS,OPENBLAS_NUM_THREADS,MKL_NUM_THREADS,LC_CTYPE > receipts/t7_universe_pod2_stdout.log 2>&1
python3 devices/t7_mapping_guard.py > receipts/mapping_stdout.txt 2>&1
python3 devices/t7_mapping_guard_r2.py
python3 devices/t7_coverage.py > receipts/coverage_stdout.txt 2>&1
python3 devices/t7_sample_pull.py > receipts/sample_pull_stdout.txt 2>&1
python3 devices/t7_sample_trim_days.py
python3 devices/t7_sample_guards.py
python3 devices/t7_pull_plan.py
python3 devices/t7_result_tables.py
python3 devices/t7_assemble_result.py
```
环境: 本机 Python 3.14.4 / numpy 2.4.4(无 requests, 只用标准库 urllib); pod2 `/workspace/venv/bin/python`。网络探针**不可逐位复现**(实时数据、场所每天上新/下市); 可复现的是装置与判据, 每个响应的 body sha256 在 HTTP 日志里。

## §13 过程中我方的错误与修正(照实记)
1. **路径守卫误伤**(两次): 禁词检查先后命中 `KRW-ORDER`(查询串)与 `ORDERUSDT`(vision 路径)。第一次让 PROBE_B 首跑中止(日志保留为 `http_log_probe_b_run1_aborted.jsonl`); 修为「禁词只查交易所 REST 路径 + 各主机正向路径白名单」。
2. **线程崩溃却退出码 0**: 映射首跑时一个场所线程因上条断言崩溃, 进程仍 rc=0 并打印了部分计数(`http_log_mapping_run1_crashed.jsonl`)。**该部分计数作废未用**; 修为线程异常收集后 `sys.exit(3)`, 重跑完整。
3. **存档快照 gzip**: `id_` 模式返回原始编码, 11 个快照首跑解析失败(`http_log_archive_run1_nogunzip.jsonl`); 加 gzip 识别后重跑全部成功。
4. **pod2 白名单**: 首跑被 `LC_CTYPE`(Python 本地化强制)拦; 二跑发现存档臂有两个 rec 数组(`S0_rec`、`d30_n2_c42_rec`), 改为全部复核。两次均在任何输出前停。
5. **客户端负控**(修正后): `fapi.binance.com/fapi/v1/klines`、`api.binance.com/api/v3/account` → HOST NOT ALLOWED; `api.upbit.com/v1/orders`、`api.bithumb.com/v1/accounts` → BANNED PATH WORD; `data.binance.vision/../api/v3/order` → ONLY ARCHIVE DATA PATHS。
6. **我自己的记忆错了一处**: 我以为 Upbit 有过 KRW-LUNA, 存档 2021-04 起所有快照里都没有; 幸存者事实只引用存档确认过的代码。
7. **装置在运行之间被修改**: `t7_http.py` 在 PROBE_A/A2/B 之后改过(白名单扩充、禁词范围、限速实现从持锁睡眠改为按主机预约时隙), 请求语义未变; 覆盖率首版(r1 映射)输出保留为 `COVERAGE_T7_r1mapping_superseded.json`, 本文只用 r2 版。
8. **qvk 不能当上市时间**: 首版映射检查时刻计划用 qvk 首末有限行, 发现 829 名全窗有限后改为「最后 C0 合格锚」, 在任何价格读取之前。
9. **更正 1 —— 我把 Bithumb `Z` / `+09:00` 字面的返回写成了「空列表」**(本文 fbf36ffd 版 §0.4、F4、T-1、§9 均如此)。事实: **HTTP 200 + `{"error":{"name":400,"message":"Invalid parameter. Check the given value!"}}`**(76 字节)。原因: PROBE_A 装置在 status 200 时不存 body, 把「非列表 body」与「空列表」都记成 `newest_open_utc = None`; 我在数表生成器里把 None 渲染成「空列表」, 没有打开同一请求的 HTTP 日志(日志里 76 字节的 error 体一直在)——「字段缺了就当某个值」缺陷族。发现者: 全量拉取的负 `to` 控制在测试运行中期望 `[]` 得到 error 体, 测试进程在任何数据请求前以 exit 2 中止。证据: `receipts/CORRECTION_1_bithumb_to_spelling.json`(原探针 3 条 + 拉取运行开头控制 1 条, body sha256 同为 `2fa56dff…`)。影响: 该地雷比原文说的**轻**(列表类型检查即可识别, 不与真空结果混淆); 其余事实不受影响; 数表 T-1 改为从 HTTP 日志读 body 类型。
