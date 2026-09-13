## P-1 配置
| 项 | 值 |
|---|---|
| 冻结计划 sha256 | `88f8e42478c135dff31a8db39ff97f8c1cfa8e5a0bd0d9754eee2a27588b1b1c` |
| 修订 1(传输) sha256 | `6bb5de9193871fb6107de0c0ece406837bc4e8ce0973afe16ec29beb70a2dead` |
| PULL_END(排他) / CUTOFF | 2026-09-13T09:00:00Z / 2021-12-01T00:00:00Z |
| KRW 市场数 Upbit / Bithumb | 234 / 352(映射 PASS 市场 + KRW-BTC + KRW-USDT) |
| 映射对 / 币安符号 / 符号-月 | 595 / 362 / 10937 |
| 限速 | 每主机任意 1 s 内 ≤ 5 次且间隔 ≥ 0.21 s, 三主机并行 |

## P-2 运行记录(controls / exits)
| 主机 | 运行 | 控制通过 | 退出码 | 本次数据请求 | 本次完成单元 | 本次错误 | 备注 |
|---|---|---|---|---|---|---|---|
| upbit | `20260913T091818Z_85081` | True | — | — | — | — | SIGTERM (修订 1 换传输, 无 exit 记录) |
| upbit | `20260913T093833Z_91893` | True | 0 | 22174 | 436 | 0 |  |
| bithumb | `20260913T091818Z_85083` | True | — | — | — | — | SIGTERM (修订 1 换传输, 无 exit 记录) |
| bithumb | `20260913T093833Z_91895` | True | 0 | 36991 | 680 | 0 |  |
| binance | `20260913T091818Z_85085` | True | — | — | — | — | SIGTERM (修订 1 换传输, 无 exit 记录) |
| binance | `20260913T093833Z_91897` | True | 0 | 8988 | 0 | 0 |  |

## P-3 文件数与体积(PULL_SUMMARY)
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

## P-4 完整性检查(CHECKS_T7_pull; 规则见冻结计划 checks)
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

## P-5 币安指数价月 zip(C6)
| 项 | 值 |
|---|---|
| 计划符号-月 | 10937 |
| 状态计数 | {'NOT_FOUND': 251, 'OK': 10686} |
| 旗标计数 | {'PARTIAL_MONTH': 902, 'FORMAT_FAIL': 961, 'FLAG_MISSING_INDEX': 5} |
| 尝试按状态 / 任意 1 s 最大 / 错误记录 | {'200': 10688, '404': 253} / 5 / 0 {} |

PARTIAL_MONTH(902): 0GUSDT 2025-09 rows 206/720, 0GUSDT 2026-06 rows 696/720, 1000BONKUSDT 2023-11 rows 204/720, 1000BONKUSDT 2026-06 rows 696/720, 1000BTTCUSDT 2022-01 rows 159/744, 1000BTTCUSDT 2022-04 rows 696/720, 1000BTTCUSDT 2022-05 rows 720/744, 1000FLOKIUSDT 2023-05 rows 612/744, 1000FLOKIUSDT 2026-06 rows 696/720, 1000PEPEUSDT 2023-05 rows 637/744, 1000PEPEUSDT 2026-06 rows 696/720, 1000SHIBUSDT 2022-07 rows 720/744, 1000SHIBUSDT 2022-10 rows 720/744, 1000SHIBUSDT 2023-02 rows 648/672, 1000SHIBUSDT 2026-06 rows 696/720, 1000XECUSDT 2022-04 rows 696/720, 1000XECUSDT 2022-05 rows 720/744, 1000XECUSDT 2022-07 rows 672/744, 1000XECUSDT 2022-10 rows 720/744, 1000XECUSDT 2023-02 rows 624/672, 1000XECUSDT 2023-04 rows 672/720, 1000XECUSDT 2026-06 rows 696/720, 1INCHUSDT 2022-07 rows 720/744, 1INCHUSDT 2022-10 rows 720/744, 1INCHUSDT 2023-02 rows 648/672, 1INCHUSDT 2026-06 rows 696/720, 2ZUSDT 2025-10 rows 708/744, 2ZUSDT 2026-06 rows 696/720, AAVEUSDT 2022-07 rows 720/744, AAVEUSDT 2022-10 rows 720/744, AAVEUSDT 2023-02 rows 648/672, AAVEUSDT 2026-06 rows 696/720, ACEUSDT 2023-12 rows 328/744, ACEUSDT 2026-06 rows 696/720, ACHUSDT 2023-02 rows 624/672, ACHUSDT 2023-04 rows 672/720, ACHUSDT 2026-06 rows 696/720, ACXUSDT 2024-12 rows 613/744, ADAUSDT 2022-07 rows 720/744, ADAUSDT 2022-10 rows 720/744, ADAUSDT 2023-02 rows 648/672, ADAUSDT 2026-06 rows 696/720, AEROUSDT 2024-12 rows 659/744, AEROUSDT 2026-06 rows 696/720, AGLDUSDT 2023-07 rows 96/744, AGLDUSDT 2026-06 rows 696/720, AKTUSDT 2024-11 rows 302/720, AKTUSDT 2026-06 rows 696/720, ALGOUSDT 2022-07 rows 720/744, ALGOUSDT 2022-10 rows 720/744, ALGOUSDT 2023-02 rows 648/672, ALGOUSDT 2026-06 rows 696/720, ALICEUSDT 2022-07 rows 720/744, ALICEUSDT 2022-10 rows 720/744, ALICEUSDT 2023-02 rows 648/672, ALICEUSDT 2026-06 rows 696/720, ALLOUSDT 2025-11 rows 466/720, ALLOUSDT 2026-06 rows 696/720, ALTUSDT 2024-01 rows 157/744, ALTUSDT 2026-06 rows 696/720, ANIMEUSDT 2025-01 rows 200/744, ANIMEUSDT 2026-06 rows 696/720, ANKRUSDT 2022-04 rows 672/720, ANKRUSDT 2022-05 rows 720/744, ANKRUSDT 2022-07 rows 600/744, ANKRUSDT 2022-10 rows 720/744, ANKRUSDT 2023-02 rows 624/672, ANKRUSDT 2023-04 rows 672/720, ANKRUSDT 2026-06 rows 696/720, APEUSDT 2022-03 rows 348/744, APEUSDT 2022-07 rows 720/744, APEUSDT 2022-10 rows 720/744, APEUSDT 2023-02 rows 648/672, APEUSDT 2026-06 rows 696/720, API3USDT 2022-02 rows 182/672, API3USDT 2022-04 rows 672/720, API3USDT 2022-07 rows 600/744, API3USDT 2022-10 rows 720/744, API3USDT 2023-02 rows 624/672, API3USDT 2023-04 rows 672/720 …

FORMAT_FAIL(961): 0GUSDT 2026-06, 1000BONKUSDT 2026-06, 1000BTTCUSDT 2022-01, 1000BTTCUSDT 2022-03, 1000BTTCUSDT 2022-04, 1000BTTCUSDT 2022-05, 1000FLOKIUSDT 2026-06, 1000PEPEUSDT 2026-06, 1000SHIBUSDT 2021-12, 1000SHIBUSDT 2022-01, 1000SHIBUSDT 2022-03, 1000SHIBUSDT 2022-05, 1000SHIBUSDT 2022-10, 1000SHIBUSDT 2023-02, 1000SHIBUSDT 2026-06, 1000XECUSDT 2021-12, 1000XECUSDT 2022-01, 1000XECUSDT 2022-03, 1000XECUSDT 2022-04, 1000XECUSDT 2022-05, 1000XECUSDT 2022-07, 1000XECUSDT 2022-10, 1000XECUSDT 2023-02, 1000XECUSDT 2023-04, 1000XECUSDT 2026-06, 1INCHUSDT 2021-12, 1INCHUSDT 2022-01, 1INCHUSDT 2022-03, 1INCHUSDT 2022-05, 1INCHUSDT 2022-10, 1INCHUSDT 2023-02, 1INCHUSDT 2026-06, 2ZUSDT 2026-06, AAVEUSDT 2021-12, AAVEUSDT 2022-01, AAVEUSDT 2022-03, AAVEUSDT 2022-05, AAVEUSDT 2022-10, AAVEUSDT 2023-02, AAVEUSDT 2026-06, ACEUSDT 2026-06, ACHUSDT 2023-02, ACHUSDT 2023-04, ACHUSDT 2026-06, ADAUSDT 2021-12, ADAUSDT 2022-01, ADAUSDT 2022-03, ADAUSDT 2022-05, ADAUSDT 2022-10, ADAUSDT 2023-02, ADAUSDT 2026-06, AEROUSDT 2026-06, AGLDUSDT 2026-06, AKTUSDT 2026-06, ALGOUSDT 2021-12, ALGOUSDT 2022-01, ALGOUSDT 2022-03, ALGOUSDT 2022-05, ALGOUSDT 2022-10, ALGOUSDT 2023-02, ALGOUSDT 2026-06, ALICEUSDT 2021-12, ALICEUSDT 2022-01, ALICEUSDT 2022-03, ALICEUSDT 2022-05, ALICEUSDT 2022-10, ALICEUSDT 2023-02, ALICEUSDT 2026-06, ALLOUSDT 2026-06, ALTUSDT 2026-06, ANIMEUSDT 2026-06, ANKRUSDT 2021-12, ANKRUSDT 2022-01, ANKRUSDT 2022-03, ANKRUSDT 2022-04, ANKRUSDT 2022-05, ANKRUSDT 2022-07, ANKRUSDT 2022-10, ANKRUSDT 2023-02, ANKRUSDT 2023-04 …

FLAG_MISSING_INDEX(5): LITUSDT 2025-08, LITUSDT 2025-09, LITUSDT 2025-10, LITUSDT 2025-11, LITUSDT 2025-12

## P-6 逐对价格同一性守卫(IDENTITY_GUARD_T7_pull)
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

## P-7 偏移谱时间戳守卫(逐年; OFFSET_SPECTRUM_T7_pull)
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

## P-9 C3 日量不等的明细与重拉核验(C3_MISMATCH_DETAIL / C3_REPULL_*)
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

## P-10 币安月 zip 内缺失的整日(BINANCE_ARCHIVE_GAPS; 未做任何补填)
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

## P-11 C6 旗标拆因(BINANCE_FORMAT_BREAKDOWN)
| 项 | 值 |
|---|---|
| OK zip / FORMAT_FAIL(任一子项) | 10686 / 961 |
| 子项失败计数 | {'not_contiguous': 594, 'no_header': 370} |
| 子项按年 | {'not_contiguous': {'2026': 303, '2022': 156, '2023': 132, '2025': 3}, 'no_header': {'2022': 281, '2021': 89}} |
| 既无表头又不连续 | 3 |
| PARTIAL_MONTH: 上市/下市边界月 vs 内部月 | {'boundary_month': 271, 'internal_month': 631} |

## P-12 币安指数价日 zip 补填(FILL_DAILY_RECEIPT; lead 决定, 12:50Z 后开始, ≤ 2 req/s)
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

## P-13 G2 命中率全史(G2_HITRATE; 锚 2021-12-01T04:00Z .. 2026-08-30T20:00Z, 10403 个; 小时粒度)
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

## P-8 入库的小件(COLLECT_RECEIPT)
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
