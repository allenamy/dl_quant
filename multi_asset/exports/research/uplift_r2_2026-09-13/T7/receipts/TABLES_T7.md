## T-1 时间戳与 `to` 语义(PROBE_A / A2)
| 项 | Upbit | Bithumb |
|---|---|---|
| A1_m60 最新 bar 标签 = 请求时刻向下取整 | True | True |
| A1_m60 标签对齐到单位整点(UTC) | True | True |
| A1_m60 KST−UTC 标签差(秒) | [32400] | [32400] |
| A1_m1 最新 bar 标签 = 请求时刻向下取整 | True | True |
| A1_m1 标签对齐到单位整点(UTC) | True | True |
| A1_m1 KST−UTC 标签差(秒) | [32400] | [32400] |
| A1_m240 最新 bar 标签 = 请求时刻向下取整 | True | False |
| A1_m240 标签对齐到单位整点(UTC) | True | False |
| A1_m240 KST−UTC 标签差(秒) | [32400] | [32400] |
| `to=2026-09-01T00:00:00Z` ⇒ 最新 bar open(UTC) | 2026-08-31T23:00:00 | **空列表 (HTTP 200)** |
| `to=2026-09-01T00:00:00` ⇒ 最新 bar open(UTC) | 2026-08-31T23:00:00 | 2026-08-31T14:00:00 |
| `to=2026-09-01 00:00:00` ⇒ 最新 bar open(UTC) | 2026-08-31T23:00:00 | 2026-08-31T14:00:00 |
| `to=2026-09-01T09:00:00+09:00` ⇒ 最新 bar open(UTC) | 2026-08-31T23:00:00 | **空列表 (HTTP 200)** |
| `to=2026-09-01T00:00:01Z` ⇒ 最新 bar open(UTC) | 2026-09-01T00:00:00 | **空列表 (HTTP 200)** |
| 日 K 标签(UTC) | 2026-09-13T00:00:00 | 2026-09-12T15:00:00 |
| count=200 实得行数 | 200 | 200 |
| count=201 实得行数 | 200 | 200 |
| count=1000 实得行数 | 200 | 200 |
| 限速响应头(首个 60m 请求) | `group=candles; min=600; sec=9` | `x-ratelimit-remaining: 149` |
| KRW-BTC 60m: `timestamp` 落在 [open, open+1h) 外的 bar 数 / 最大 (timestamp−open) 秒 | 6/200, 3600.048 | 0/200, 3599.978 |
| KRW-XRP 60m: `timestamp` 落在 [open, open+1h) 外的 bar 数 / 最大 (timestamp−open) 秒 | 3/200, 3600.054 | 0/200, 3599.996 |
| KRW-USDT 60m: `timestamp` 落在 [open, open+1h) 外的 bar 数 / 最大 (timestamp−open) 秒 | 3/200, 3600.022 | 0/200, 3599.993 |
| 已收盘 bar 70 秒后重读改变数 | 0/198 | 0/198 |

## T-2 历史深度 / USDT 起点 / 下市可查性(PROBE_B / C)
| 项 | Upbit | Bithumb |
|---|---|---|
| KRW-BTC 最早日 K | 2017-09-25T00:00:00 | 2013-12-26T15:00:00 |
| KRW-BTC 最早 60m | 2017-09-25T03:00:00 | 2013-12-27T09:00:00 |
| KRW-BTC 最早 1m | 2017-09-25T03:00:00 | 2013-12-27T09:10:00 |
| KRW-USDT 最早日 K | 2024-06-07T00:00:00 | 2023-12-06T15:00:00 |
| KRW-USDT 最早 60m | 2024-06-07T09:00:00 | 2023-12-07T03:00:00 |
| upbit: 不在今日列表的候选代码中「Code not found」数 | 18 |  |
| bithumb: 不在今日列表的候选代码中「Code not found」数 |  | 17 |
| 其中经网页存档确认「曾在该所 KRW 上市」的代码 | KRW-BTG, KRW-DAWN, KRW-EMC2, KRW-IGNIS, KRW-LOOM, KRW-MFT, KRW-NU, KRW-OMG, KRW-PCI, KRW-SRM, KRW-STPT, KRW-WEMIX, KRW-XEM | KRW-BTG, KRW-LOOM, KRW-LUNA, KRW-NU, KRW-OMG, KRW-SRM, KRW-STPT, KRW-WEMIX, KRW-XEM |
| 从未存在代码 KRW-ZZZNOTACOIN | HTTP 404 `{"error":{"name":404,"message":"Code not found"}}` | HTTP 200 (body 同 Upbit, 见日志) |
| 兜底源: Upbit 网页 CDN crix(KRW-LUNA/WEMIX) | HTTP 404 Code not found | — |
| 兜底源: CryptoCompare 免 key | HTTP 401 API key required | HTTP 401 |
| upbit 最薄市场 KRW-USDG 60m: 200 根 bar 跨 449 小时, 零成交量 bar 0 | ⇒ 无成交的小时不出 bar | |
| bithumb 最薄市场 KRW-USDE 60m: 200 根 bar 跨 605 小时, 零成交量 bar 0 | ⇒ 无成交的小时不出 bar | |

## T-3 KRW 市场普查(CENSUS, 当前在市)
| 所 | KRW 市场数 | 错误 | 无 bar | 有缺月 | 首日年份分布 |
|---|---|---|---|---|---|
| upbit | 288 | 0 | 0 | 0 | 2017:19, 2018:23, 2019:11, 2020:22, 2021:11, 2022:5, 2023:12, 2024:33, 2025:85, 2026:67 |
| bithumb | 482 | 0 | 0 | 0 | 2013:1, 2016:1, 2017:5, 2018:21, 2019:8, 2020:24, 2021:42, 2022:27, 2023:69, 2024:78, 2025:140, 2026:66 |

## T-4 映射与价格同一性守卫(MAPPING r1 + r2)
| 所 | 有候选的合格名 | PASS 选用 | 按规则×判决 |
|---|---|---|---|
| upbit | 245 | 236 | exact/FAIL=2; exact/NO_OVERLAP_AT_T=5; exact/PASS=230; manual/NO_OVERLAP_AT_T=1; manual/PASS=4; manual_r2/FAIL=1; manual_r2/PASS=1; suffix2/PASS=1 |
| bithumb | 370 | 359 | exact/FAIL=1; exact/NO_OVERLAP_AT_T=7; exact/PASS=348; exact/REVIEW=2; manual/PASS=8; manual_r2/NO_OVERLAP_AT_T=1; manual_r2/PASS=3 |

### 非 exact 规则或非 PASS 的全部对
| 所 | 币安符号 | KRW 市场(名称) | 规则 | 判决 | R | 检查时刻 T | KRW 首日 |
|---|---|---|---|---|---|---|---|
| bithumb | 1000000BOBUSDT | KRW-BOB (BOB) | exact | NO_OVERLAP_AT_T |  | 2025-10-16T03:00:00 | 2025-12-02T15:00:00 |
| upbit | 1000BTTCUSDT | KRW-BTT (BitTorrent) | manual | PASS | 1.046085 | 2022-04-11T03:00:00 | 2019-01-31T00:00:00 |
| bithumb | 1000BTTCUSDT | KRW-BTT (BitTorrent) | manual | PASS | 1.046821 | 2022-04-11T03:00:00 | 2022-01-04T15:00:00 |
| upbit | AIUSDT | KRW-AI (Gensyn) | exact | NO_OVERLAP_AT_T |  | 2025-11-30T11:00:00 | 2026-06-30T00:00:00 |
| bithumb | AIUSDT | KRW-AI (Gensyn) | exact | NO_OVERLAP_AT_T |  | 2025-11-30T11:00:00 | 2026-05-17T15:00:00 |
| bithumb | AXLUSDT | KRW-WAXL (Axelar) | manual | PASS | 1.00311 | 2026-06-21T11:00:00 | 2024-01-07T15:00:00 |
| upbit | B3USDT | KRW-B3 (B3) | exact | NO_OVERLAP_AT_T |  | 2026-04-04T03:00:00 | 2026-05-07T00:00:00 |
| upbit | BEAMXUSDT | KRW-BEAM (Beam) | manual | PASS | 1.002019 | 2026-03-14T15:00:00 | 2024-05-31T00:00:00 |
| bithumb | BEAMXUSDT | KRW-BEAM (Beam) | manual | PASS | 0.997172 | 2026-03-14T15:00:00 | 2024-10-23T15:00:00 |
| bithumb | DARUSDT | KRW-D (DAR Open Network) | manual_r2 | PASS | 1.000539 | 2024-12-27T11:00:00 | 2023-01-26T15:00:00 |
| upbit | EDGEUSDT | KRW-EDGE (Definitive) | exact | FAIL | 0.194903 | 2026-08-30T23:00:00 | 2026-03-04T00:00:00 |
| bithumb | EDGEUSDT | KRW-EDGE (Definitive) | exact | FAIL | 0.194824 | 2026-08-30T23:00:00 | 2026-03-03T15:00:00 |
| upbit | EOSUSDT | KRW-A (Vaulta) | manual | PASS | 1.001282 | 2025-05-21T03:00:00 | 2018-03-22T00:00:00 |
| bithumb | EOSUSDT | KRW-A (Vaulta) | manual | PASS | 1.000685 | 2025-05-21T03:00:00 | 2017-12-11T15:00:00 |
| bithumb | FTMUSDT | KRW-S (Sonic) | manual | PASS | 1.002451 | 2025-01-08T11:00:00 | 2023-07-17T15:00:00 |
| bithumb | FXSUSDT | KRW-FRAX (Frax) | manual_r2 | PASS | 0.995005 | 2025-11-26T19:00:00 | 2023-08-23T15:00:00 |
| bithumb | HNTUSDT | KRW-HNT (Helium) | exact | NO_OVERLAP_AT_T |  | 2023-03-22T03:00:00 | 2026-05-31T15:00:00 |
| bithumb | KLAYUSDT | KRW-KAIA (Kaia) | manual | PASS | 1.000006 | 2024-10-23T03:00:00 | 2021-05-13T15:00:00 |
| upbit | KMNOUSDT | KRW-KMNO (Kamino Finance) | exact | NO_OVERLAP_AT_T |  | 2026-06-26T11:00:00 | 2026-08-07T00:00:00 |
| bithumb | MANTRAUSDT | KRW-MANTRA (MANTRA) | exact | REVIEW | 1.389096 | 2026-08-30T23:00:00 | 2026-03-02T15:00:00 |
| upbit | MATICUSDT | KRW-POL (Polygon Ecosystem Token) | manual | PASS | 1.002912 | 2024-09-06T11:00:00 | 2021-10-15T00:00:00 |
| bithumb | MATICUSDT | KRW-POL (Polygon Ecosystem Token) | manual | PASS | 1.000944 | 2024-09-06T11:00:00 | 2021-06-06T15:00:00 |
| upbit | METUSDT | KRW-MET2 (Meteora) | suffix2 | PASS | 0.999627 | 2026-08-30T23:00:00 | 2025-11-18T00:00:00 |
| upbit | OMUSDT | KRW-MANTRA (MANTRA) | manual_r2 | FAIL | 0.254277 | 2026-02-24T23:00:00 | 2025-05-21T00:00:00 |
| bithumb | OMUSDT | KRW-MANTRA (MANTRA) | manual_r2 | NO_OVERLAP_AT_T |  | 2026-02-24T23:00:00 | 2026-03-02T15:00:00 |
| upbit | RAYUSDT | KRW-RAY (Raydium) | exact | NO_OVERLAP_AT_T |  | 2022-11-16T15:00:00 | 2025-06-19T00:00:00 |
| bithumb | RAYUSDT | KRW-RAY (Raydium) | exact | NO_OVERLAP_AT_T |  | 2022-11-16T15:00:00 | 2024-11-18T15:00:00 |
| upbit | RNDRUSDT | KRW-RENDER (Render Token) | manual | NO_OVERLAP_AT_T |  | 2024-07-18T11:00:00 | 2024-12-05T00:00:00 |
| bithumb | RNDRUSDT | KRW-RENDER (Render Token) | manual | PASS | 1.00193 | 2024-07-18T11:00:00 | 2023-07-17T15:00:00 |
| bithumb | SCUSDT | KRW-SC (Siacoin) | exact | NO_OVERLAP_AT_T |  | 2022-06-18T19:00:00 | 2024-03-26T15:00:00 |
| bithumb | STORJUSDT | KRW-STORJ (Storj) | exact | REVIEW | 1.269055 | 2026-08-27T11:00:00 | 2023-11-13T15:00:00 |
| upbit | STPTUSDT | KRW-AWE (AWE Network) | manual_r2 | PASS | 1.003505 | 2024-05-13T15:00:00 | 2020-03-24T00:00:00 |
| bithumb | STPTUSDT | KRW-AWE (AWE Network) | manual_r2 | PASS | 1.003242 | 2024-05-13T15:00:00 | 2023-04-05T15:00:00 |
| upbit | STRAXUSDT | KRW-STRAX (Xertra) | exact | FAIL | 0.099877 | 2024-03-16T23:00:00 | 2017-09-25T00:00:00 |
| bithumb | STRAXUSDT | KRW-STRAX (Xertra) | exact | NO_OVERLAP_AT_T |  | 2024-03-16T23:00:00 | 2024-03-26T15:00:00 |
| bithumb | USELESSUSDT | KRW-USELESS (Useless Coin) | exact | NO_OVERLAP_AT_T |  | 2026-08-30T23:00:00 | 2026-09-07T15:00:00 |
| upbit | XCNUSDT | KRW-XCN (Onyxcoin) | exact | NO_OVERLAP_AT_T |  | 2025-11-15T07:00:00 | 2026-04-27T00:00:00 |

预检(币安归档格式): `https://data.binance.vision/data/futures/um/daily/indexPriceKlines/BTCUSDT/1h/BTCUSDT-1h-2026-08-30.zip` 表头 ['open_time', 'open', 'high', 'low', 'close', 'volume']…, open_time 单位 ms

## T-5 合格宇宙覆盖率(按名计, 池化锚×名格; 映射 PASS 且 KRW 首日 ≤ 锚 − 1 日)
| 年 | 回放锚 | 平均合格名 | Upbit | Bithumb | 并集 | 两所都有 | 逐锚并集 [最小, 最大] |
|---|---|---|---|---|---|---|---|
| 2022 | 2010 | 138.8 | 33.9% | 46.6% | 52.6% | 27.9% | [50.3%, 54.4%] |
| 2023 | 2190 | 176.3 | 31.1% | 51.3% | 55.5% | 26.9% | [50.3%, 61.8%] |
| 2024 | 2196 | 258.0 | 30.4% | 57.4% | 59.0% | 28.7% | [56.5%, 62.0%] |
| 2025 | 2190 | 354.3 | 32.9% | 58.3% | 58.6% | 32.6% | [55.6%, 64.9%] |
| 2026 | 1453 | 280.4 | 45.0% | 64.1% | 64.5% | 44.6% | [58.2%, 71.6%] |
| 全部 | 10039 | — | 34.2% | 56.6% | 58.5% | 32.3% | |

**实盘书按权重**(132 个 target_live 副本, 2026-08-22T04:00Z .. 2026-09-13T04:00Z; 生产者 combo_stage_v1(kingLGBM 0.55 + V2MAIN 0., shadow_loop_v2, shadow_loop_v3):
| 所 | 毛权重覆盖均值 [最小, 最大] | 持仓名数覆盖均值 |
|---|---|---|
| upbit | 42.1% [31.8%, 46.5%] | 49.4% |
| bithumb | 58.5% [48.1%, 62.0%] | 67.9% |
| union | 59.2% [49.3%, 62.7%] | 68.3% |

**分母复核**(装置对存档 r18 臂逐锚): C0:S0_rec: rows 10039, n_sel 差 0, len(m) 差 0, PASS=True; C0:d30_n2_c42_rec: rows 10039, n_sel 差 0, len(m) 差 0, PASS=True; NW:S0_rec: rows 10039, n_sel 差 0, len(m) 差 0, PASS=True; NW:d30_n2_c42_rec: rows 10039, n_sel 差 0, len(m) 差 0, PASS=True

## T-6 幸存者偏差(网页存档快照 vs 今日可查)
| 所 | 半年 | 快照 | 当时 KRW 市场 | 今日查不到 上界/下界 | 快照锚合格名 | 可查且 PASS 覆盖 | 当时按 ticker 在市 | 因下市而丢失(占合格名) |
|---|---|---|---|---|---|---|---|---|
| upbit | 2021H1 | 20210422084616 | 117 | 36.8% / 31.6% | — | — | — | — |
| upbit | 2021H2 | 20210711185901 | 102 | 27.5% / 21.6% | — | — | — | — |
| upbit | 2022H1 | 20220102134840 | 109 | 25.7% / 21.1% | — | — | — | — |
| upbit | 2022H2 | 20220808164939 | 113 | 24.8% / 20.3% | 139 | 33.8% | 38.9% | 5.0% |
| upbit | 2023H1 | 20230202120905 | 114 | 22.8% / 19.3% | 145 | 33.1% | 37.2% | 4.1% |
| upbit | 2023H2 | 20230904183132 | 118 | 18.6% / 15.2% | 189 | 30.2% | 32.8% | 2.6% |
| upbit | 2024H1 | 20240115181517 | 118 | 16.1% / 12.7% | 235 | 30.6% | 33.6% | 2.5% |
| upbit | 2024H2 | 20240815142939 | 134 | 11.9% / 10.4% | 257 | 31.1% | 34.2% | 2.7% |
| upbit | 2025H2 | 20250908215759 | 193 | 6.2% / 5.7% | 349 | 33.0% | 35.2% | 2.3% |
| upbit | 2026H1 | 20260120092338 | 234 | 4.3% / 3.9% | 325 | 40.9% | 42.1% | 1.5% |
| upbit | 2026H2 | 20260819081004 | 283 | 0.7% / 0.7% | 202 | 48.0% | 49.0% | 0.5% |
| bithumb | 2018H1 | 20180625110814 | 37 | 54.0% / 48.6% | — | — | — | — |
| bithumb | 2018H2 | 20180721061041 | 37 | 54.0% / 48.6% | — | — | — | — |
| bithumb | 2019H1 | 20190115003953 | 70 | 60.0% / 57.1% | — | — | — | — |
| bithumb | 2019H2 | 20190701024433 | 86 | 62.8% / 60.5% | — | — | — | — |
| bithumb | 2020H1 | 20200106014655 | 103 | 64.1% / 62.1% | — | — | — | — |
| bithumb | 2020H2 | 20200707122516 | 104 | 58.7% / 55.8% | — | — | — | — |
| bithumb | 2021H1 | 20210204003824 | 137 | 53.3% / 51.8% | — | — | — | — |
| bithumb | 2021H2 | 20210817072611 | 177 | 46.9% / 44.6% | — | — | — | — |
| bithumb | 2022H1 | 20220112051255 | 184 | 44.0% / 41.9% | — | — | — | — |
| bithumb | 2022H2 | 20220808063656 | 191 | 34.5% / 33.0% | 139 | 47.5% | 54.0% | 6.5% |
| bithumb | 2023H1 | 20230523145637 | 216 | 29.6% / 27.3% | 171 | 47.4% | 52.6% | 4.7% |
| bithumb | 2023H2 | 20230823132706 | 235 | 27.7% / 25.5% | 187 | 52.9% | 58.8% | 5.9% |
| bithumb | 2024H1 | 20240306235540 | 272 | 22.4% / 20.6% | 250 | 56.8% | 64.8% | 6.8% |
| bithumb | 2024H2 | 20240823154758 | 292 | 17.8% / 16.8% | 255 | 58.4% | 63.9% | 5.1% |
| bithumb | 2025H1 | 20250226022245 | 355 | 14.9% / 13.5% | 327 | 56.9% | 62.4% | 5.2% |
| bithumb | 2026H1 | 20260222114506 | 449 | 6.5% / 5.6% | 267 | 65.2% | 70.0% | 4.5% |

## T-7 样本守卫(GUARDS_sample; 360 锚)
| 所 | G1 因果(违例/格) | G1 负控 bar=N(违例/格) | G2 命中率 def A (新鲜率) | G2 命中率 def B (新鲜率) | BTC pB 水平 [最小, 中位, 最大] |
|---|---|---|---|---|---|
| upbit | 0/1800 | 1790/1790 | 1.0 (0.996528) | 1.0 (0.996667) | [-0.00191, -3e-05, 0.00255] |
| bithumb | 0/1080 | 1077/1077 | 1.0 (1.0) | 1.0 (1.0) | [-0.00188, -0.00015, 0.00235] |

| 所 | 市场 | G3 argmax ρ | ρ(−1) / ρ(0) / ρ(+1) | 离散度 argmin | D(0)/min D(±1) | 负控 KST 当 UTC argmax | 负控 收盘标签 argmax | PASS |
|---|---|---|---|---|---|---|---|---|
| upbit | KRW-BTC | 0 | 0.820628 / 0.962131 / 0.835337 | 0 | 0.4297 | 9 | 1 | True |
| upbit | KRW-ETH | 0 | 0.860355 / 0.983375 / 0.874387 | 0 | 0.3338 | 9 | 1 | True |
| upbit | KRW-XRP | 0 | 0.811969 / 0.984573 / 0.812174 | 0 | 0.2562 | 9 | 1 | True |
| bithumb | KRW-BTC | 0 | 0.821932 / 0.963901 / 0.839791 | 0 | 0.4162 | 9 | 1 | True |
| bithumb | KRW-XRP | 0 | 0.812926 / 0.985303 / 0.811917 | 0 | 0.243 | 9 | 1 | True |

XRP 两所 def B 之差: 中位 0.00064, p95 0.00147(n=360)

## T-8 样本拉取清单(SAMPLE_MANIFEST)
| 市场 | bar 数/小时数 | 页数 | V2 整点 | V3 页缝 | V4 日量恒等(天/不等/仅舍入) | 60m 文件 sha256 |
|---|---|---|---|---|---|---|
| upbit:KRW-BTC | 1437/1440 | 8 | True | True | 60/0/0 | `e425abb6d83e8850…` |
| upbit:KRW-USDT | 1436/1440 | 8 | True | True | 60/0/0 | `f998004615c772dd…` |
| upbit:KRW-ETH | 1437/1440 | 8 | True | True | 60/0/0 | `b144ff55997defe9…` |
| upbit:KRW-XRP | 1437/1440 | 8 | True | True | 60/0/0 | `2d2192f14cd6eba8…` |
| upbit:KRW-PEPE | 1436/1440 | 8 | True | True | 60/0/0 | `37d9445dc8c20b19…` |
| upbit:KRW-POL | 1433/1440 | 8 | True | True | 60/0/0 | `07ac2974283981f1…` |
| bithumb:KRW-BTC | 1440/1440 | 8 | True | True | 59/0/0 | `f4a992a9dbc64d7d…` |
| bithumb:KRW-USDT | 1440/1440 | 8 | True | True | 59/0/0 | `4c90b5948541f653…` |
| bithumb:KRW-XRP | 1440/1440 | 8 | True | True | 59/0/0 | `21ca7d14c258c63f…` |
| bithumb:KRW-SHIB | 1440/1440 | 8 | True | True | 59/0/0 | `e005c23b7e7e95db…` |
| binance BTCUSDT | 1440/1440 | 2 zip | ms=True | 连续=True | 行数 1488=1488, close_time=open+3599999: True | `d667da91b9ae2921…` |
| binance ETHUSDT | 1440/1440 | 2 zip | ms=True | 连续=True | 行数 1488=1488, close_time=open+3599999: True | `0840bc8b05508597…` |
| binance XRPUSDT | 1440/1440 | 2 zip | ms=True | 连续=True | 行数 1488=1488, close_time=open+3599999: True | `a78662af1f1210ee…` |
| binance 1000PEPEUSDT | 1440/1440 | 2 zip | ms=True | 连续=True | 行数 1488=1488, close_time=open+3599999: True | `591244182a5be044…` |
| binance POLUSDT | 1440/1440 | 2 zip | ms=True | 连续=True | 行数 1488=1488, close_time=open+3599999: True | `f2c355837b1e6972…` |
| binance 1000SHIBUSDT | 1440/1440 | 2 zip | ms=True | 连续=True | 行数 1488=1488, close_time=open+3599999: True | `f2eb8d15f801737e…` |

样本请求数 102; 窗口 ['2026-07-01T00:00:00', '2026-08-30T00:00:00']

## T-9 全量拉取预算(PLAN_full_pull; 上界 = ceil(小时/200))
| 所 | 范围 | 市场数 | 60m 请求 | 日 K 请求 | 合计 | 5 req/s 小时 | 4 req/s 小时 | gz CSV MB |
|---|---|---|---|---|---|---|---|---|
| upbit | S-MAP/H-REPLAY | 234 | 23536 | 1074 | 24610 | 1.37 | 1.71 | 174.0 |
| upbit | S-MAP/H-FULL | 234 | 31082 | 1404 | 32486 | 1.8 | 2.26 | 230.0 |
| upbit | S-ALL/H-REPLAY | 288 | 28970 | 1326 | 30296 | 1.68 | 2.1 | 214.1 |
| upbit | S-ALL/H-FULL | 288 | 38554 | 1746 | 40300 | 2.24 | 2.8 | 285.3 |
| bithumb | S-MAP/H-REPLAY | 352 | 38363 | 1754 | 40117 | 2.23 | 2.79 | 283.6 |
| bithumb | S-MAP/H-FULL | 352 | 44834 | 2042 | 46876 | 2.6 | 3.26 | 331.6 |
| bithumb | S-ALL/H-REPLAY | 482 | 52154 | 2391 | 54545 | 3.03 | 3.79 | 385.6 |
| bithumb | S-ALL/H-FULL | 482 | 59902 | 2737 | 62639 | 3.48 | 4.35 | 443.0 |
| binance vision | indexPriceKlines 1h 月 zip | 363 符号 | — | — | 11330 | 0.63 | 0.79 | — |
