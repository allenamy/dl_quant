
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
{{P-1}}

{{P-2}}

{{P-3}}

{{P-4}}

{{P-5}}

{{P-11}}

{{P-6}}

{{P-7}}

{{P-9}}

{{P-10}}

{{P-12}}

{{P-13}}

{{P-8}}
