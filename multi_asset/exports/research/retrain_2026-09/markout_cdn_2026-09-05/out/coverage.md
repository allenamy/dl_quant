# CDN markout backfill -- coverage and preliminary markout read
> **创建:** 2026-09-05 | **Session:** review_caliber / markout_cdn (pod2, CPU only) | **状态:** data receipt, preliminary read | **作废条件:** archives for 2026-09-05 published (rerun `--resume`), or the executor's own API-path backfill supersedes these marks

## Device
- script `scripts/markout_cdn.py` self_sha256 `542f98a67da3f0d826c9ac01af38fc8f948924f98abbfbaa0f2f32a3d87426f3`; input `pending_fills.json` sha256 `e37a035324f69fd0cd445d4be6048ea7551378a277d8561aed92a524140af596` (17660 rows, 407 symbols, ledger days 2026-08-01 .. 2026-09-05)
- rule: target = fill_ts + 60 s; mark = FIRST aggTrade with T >= target and T <= target + 60 s; strict variant recorded when lag <= 5 s; none -> `no_trade_within_60s`; 404 -> `archive_missing`
- source: data.binance.vision daily aggTrades (futures/um), file chosen by the UTC day of target (0 rows cross midnight); 4697 archives requested, 6.59 GB fetched in memory, elapsed 6.9 min; unsorted archives: 0; header-less archives: 0
- archive status: {"ok": 4479, "archive_missing": 218}; generated 2026-09-05T09:12:06Z

## Row status by ledger day
| day | ok | no_trade_60s | archive_missing | dl_err | parse_err | total | ok% | lag p50 s | lag p90 s | lag max s | strict(<=5s) n |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20260801 | 111 | 2 | 0 | 0 | 0 | 113 | 98.2 | 15.466 | 33.577 | 59.611 | 0 |
| 20260802 | 262 | 7 | 0 | 0 | 0 | 269 | 97.4 | 8.224 | 22.846 | 59.324 | 68 |
| 20260803 | 519 | 1 | 0 | 0 | 0 | 520 | 99.8 | 4.868 | 18.901 | 59.502 | 266 |
| 20260804 | 516 | 4 | 0 | 0 | 0 | 520 | 99.2 | 4.342 | 19.961 | 54.133 | 273 |
| 20260805 | 379 | 3 | 0 | 0 | 0 | 382 | 99.2 | 3.928 | 17.233 | 52.941 | 209 |
| 20260806 | 334 | 4 | 0 | 0 | 0 | 338 | 98.8 | 3.905 | 20.538 | 56.037 | 187 |
| 20260807 | 412 | 8 | 0 | 0 | 0 | 420 | 98.1 | 2.874 | 14.686 | 58.561 | 253 |
| 20260808 | 544 | 1 | 0 | 0 | 0 | 545 | 99.8 | 2.635 | 15.832 | 49.096 | 350 |
| 20260809 | 474 | 0 | 0 | 0 | 0 | 474 | 100.0 | 2.440 | 16.134 | 56.828 | 304 |
| 20260810 | 276 | 0 | 0 | 0 | 0 | 276 | 100.0 | 2.144 | 12.725 | 56.074 | 176 |
| 20260811 | 61 | 0 | 0 | 0 | 0 | 61 | 100.0 | 5.874 | 18.889 | 44.024 | 27 |
| 20260812 | 17 | 0 | 0 | 0 | 0 | 17 | 100.0 | 9.236 | 21.231 | 39.326 | 0 |
| 20260813 | 17 | 1 | 0 | 0 | 0 | 18 | 94.4 | 10.113 | 12.551 | 13.575 | 0 |
| 20260814 | 19 | 0 | 0 | 0 | 0 | 19 | 100.0 | 12.994 | 22.403 | 38.396 | 2 |
| 20260815 | 33 | 0 | 0 | 0 | 0 | 33 | 100.0 | 7.727 | 31.755 | 39.297 | 6 |
| 20260816 | 31 | 1 | 0 | 0 | 0 | 32 | 96.9 | 7.605 | 22.827 | 52.116 | 11 |
| 20260817 | 19 | 1 | 0 | 0 | 0 | 20 | 95.0 | 9.659 | 22.674 | 30.128 | 4 |
| 20260818 | 392 | 1 | 0 | 0 | 0 | 393 | 99.7 | 1.315 | 9.088 | 48.056 | 313 |
| 20260819 | 47 | 0 | 0 | 0 | 0 | 47 | 100.0 | 4.442 | 23.740 | 35.192 | 24 |
| 20260820 | 105 | 0 | 0 | 0 | 0 | 105 | 100.0 | 2.176 | 10.248 | 57.240 | 72 |
| 20260821 | 273 | 0 | 0 | 0 | 0 | 273 | 100.0 | 0.692 | 8.658 | 44.096 | 230 |
| 20260822 | 1513 | 3 | 0 | 0 | 0 | 1516 | 99.8 | 0.782 | 3.337 | 48.534 | 1417 |
| 20260823 | 389 | 1 | 0 | 0 | 0 | 390 | 99.7 | 0.977 | 11.016 | 46.059 | 303 |
| 20260824 | 393 | 0 | 0 | 0 | 0 | 393 | 100.0 | 1.160 | 9.644 | 47.970 | 307 |
| 20260825 | 575 | 3 | 0 | 0 | 0 | 578 | 99.5 | 2.442 | 13.854 | 48.812 | 398 |
| 20260826 | 910 | 3 | 0 | 0 | 0 | 913 | 99.7 | 1.521 | 13.803 | 57.824 | 658 |
| 20260827 | 1302 | 11 | 0 | 0 | 0 | 1313 | 99.2 | 2.242 | 18.331 | 55.211 | 877 |
| 20260828 | 626 | 2 | 0 | 0 | 0 | 628 | 99.7 | 1.518 | 14.976 | 55.427 | 445 |
| 20260829 | 683 | 4 | 0 | 0 | 0 | 687 | 99.4 | 2.821 | 20.879 | 58.945 | 417 |
| 20260830 | 1006 | 4 | 0 | 0 | 0 | 1010 | 99.6 | 2.792 | 17.114 | 59.432 | 641 |
| 20260831 | 722 | 1 | 0 | 0 | 0 | 723 | 99.9 | 2.079 | 13.280 | 47.290 | 516 |
| 20260901 | 655 | 0 | 0 | 0 | 0 | 655 | 100.0 | 1.804 | 12.038 | 37.374 | 459 |
| 20260902 | 548 | 7 | 0 | 0 | 0 | 555 | 98.7 | 2.296 | 12.706 | 59.233 | 373 |
| 20260903 | 1568 | 0 | 0 | 0 | 0 | 1568 | 100.0 | 1.517 | 10.339 | 47.222 | 1219 |
| 20260904 | 1151 | 2 | 0 | 0 | 0 | 1153 | 99.8 | 1.735 | 11.240 | 54.055 | 861 |
| 20260905 | 0 | 0 | 703 | 0 | 0 | 703 | 0.0 | - | - | - | 0 |
| **total** | 16882 | 75 | 703 | 0 | 0 | 17660 | 95.6 | 1.890 | 14.549 | 59.611 | 11666 |

Status totals: ok=16882, archive_missing=703, no_trade_within_60s=75
Status by order_type: maker: ok=13854, archive_missing=556, no_trade_within_60s=64; topup_taker: ok=3028, archive_missing=147, no_trade_within_60s=11

## mark_lag_s distribution (ok rows)
| slice | n | p50 | p90 | p99 | max | share lag<=5s | share lag<=1s |
|---|---:|---:|---:|---:|---:|---:|---:|
| all | 16882 | 1.890 | 14.549 | 40.457 | 59.611 | 0.691 | 0.365 |
| order_type=maker | 13854 | 1.877 | 14.048 | 40.479 | 59.611 | 0.695 | 0.365 |
| order_type=topup_taker | 3028 | 1.920 | 16.821 | 39.726 | 59.502 | 0.672 | 0.368 |

`no_trade_within_60s` rows by symbol (top 15): BUSDT=9, KASUSDT=4, BASUSDT=4, XTZUSDT=3, SUSHIUSDT=3, STXUSDT=3, RVNUSDT=3, NEOUSDT=3, WUSDT=3, ANKRUSDT=2, THETAUSDT=2, COMPUSDT=2, ARUSDT=2, YFIUSDT=2, MAVUSDT=2

## Cross-check
The venue API cannot be called from here and the pending set contains no executor-marked fills by construction, so the check is on the parser: 20 random ok rows (seed 20260905) re-derived by an independent pure-`csv` streaming implementation (no pandas/numpy) that re-downloads the archive, re-verifies its sha256, and prints the 2 trades before the mark, the mark, and the 2 after.  Full printout: `out/validation_20rows.txt`.
- result: **20/20 agree** on (mark_ts, mark_px, archive sha256); mismatches: []

- `no_trade_within_60s` rows: 10 random ones (seed 20260905) re-scanned by the same pure-`csv` path, printing the last trade before target and the first trade after the window (`out/validation_no_trade_10rows.txt`): **10/10 no_trade rows confirmed (zero trades inside the 60 s window)**

## PRELIMINARY markout read (information only)
Sign: buy => (mark_px - fill_px)/fill_px, sell => (fill_px - mark_px)/fill_px, in bps; **positive = price moved in our favour after the fill, negative = adverse selection**.  Weights: **equal per fill** -- the export has no quantity column, so the notional-weighted number the brief asked for cannot be formed from this input (re-weight after joining the ledger on trade_id).  Uncertainty: day-block bootstrap of the mean only (blocks = ledger day, 2000 resamples, numpy default_rng(20260905)); no other CI, no cost netting, no fee/rebate, not a book-level number.

| slice | n marks | mean bps | median bps | day-block 95% CI | days | mean 5s-variant bps (n) |
|---|---:|---:|---:|---:|---:|---:|
| all | 16882 | -1.23 | +0.00 | [-2.08, -0.50] | 35 | -1.44 (11666) |
| order_type=maker | 13854 | -1.40 | +0.00 | [-2.29, -0.65] | 35 | -1.75 (9632) |
| order_type=topup_taker | 3028 | -0.46 | +0.00 | [-2.73, +1.25] | 31 | +0.07 (2034) |
| maker / buy | 7464 | -0.80 | +0.00 | [-2.74, +0.85] | 35 | -1.26 (5177) |
| maker / sell | 6390 | -2.10 | +0.00 | [-3.63, -0.99] | 35 | -2.32 (4455) |
| topup_taker / buy | 1568 | -0.60 | -1.10 | [-4.19, +1.97] | 29 | -0.18 (1017) |
| topup_taker / sell | 1460 | -0.30 | +0.00 | [-3.44, +2.35] | 30 | +0.32 (1017) |

### by ledger day (equal-weighted, no CI)
| day | n all | mean bps all | n maker | mean bps maker | n topup_taker | mean bps topup_taker | share of marks with markout<0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 20260801 | 111 | -0.84 | 72 | +0.41 | 39 | -3.15 | 0.405 |
| 20260802 | 262 | -0.79 | 180 | -0.84 | 82 | -0.67 | 0.439 |
| 20260803 | 519 | -1.60 | 247 | -1.93 | 272 | -1.31 | 0.420 |
| 20260804 | 516 | +0.18 | 307 | -0.36 | 209 | +0.98 | 0.370 |
| 20260805 | 379 | -0.59 | 230 | -0.23 | 149 | -1.14 | 0.430 |
| 20260806 | 334 | -0.07 | 243 | +0.86 | 91 | -2.56 | 0.431 |
| 20260807 | 412 | -0.68 | 334 | -0.12 | 78 | -3.05 | 0.468 |
| 20260808 | 544 | -1.18 | 473 | -1.21 | 71 | -0.96 | 0.445 |
| 20260809 | 474 | -0.55 | 395 | -0.44 | 79 | -1.06 | 0.420 |
| 20260810 | 276 | -0.47 | 253 | -0.38 | 23 | -1.45 | 0.457 |
| 20260811 | 61 | -0.27 | 59 | -0.49 | 2 | +6.13 | 0.344 |
| 20260812 | 17 | -1.12 | 17 | -1.12 | 0 | - | 0.529 |
| 20260813 | 17 | +1.47 | 17 | +1.47 | 0 | - | 0.412 |
| 20260814 | 19 | -2.80 | 19 | -2.80 | 0 | - | 0.526 |
| 20260815 | 33 | -0.19 | 30 | +1.14 | 3 | -13.56 | 0.303 |
| 20260816 | 31 | -0.98 | 31 | -0.98 | 0 | - | 0.323 |
| 20260817 | 19 | -1.17 | 18 | -1.10 | 1 | -2.42 | 0.421 |
| 20260818 | 392 | +0.33 | 315 | -1.44 | 77 | +7.58 | 0.352 |
| 20260819 | 47 | -2.19 | 43 | -1.70 | 4 | -7.44 | 0.404 |
| 20260820 | 105 | +3.39 | 89 | +3.34 | 16 | +3.62 | 0.276 |
| 20260821 | 273 | -1.34 | 187 | +0.09 | 86 | -4.44 | 0.509 |
| 20260822 | 1513 | -0.01 | 1262 | -0.27 | 251 | +1.27 | 0.467 |
| 20260823 | 389 | -0.06 | 368 | +0.32 | 21 | -6.65 | 0.447 |
| 20260824 | 393 | -0.15 | 362 | +1.22 | 31 | -16.13 | 0.463 |
| 20260825 | 575 | -1.63 | 482 | -2.03 | 93 | +0.45 | 0.522 |
| 20260826 | 910 | -3.40 | 795 | -2.98 | 115 | -6.27 | 0.557 |
| 20260827 | 1302 | -1.17 | 1114 | -1.16 | 188 | -1.23 | 0.473 |
| 20260828 | 626 | -6.02 | 585 | -5.53 | 41 | -13.10 | 0.524 |
| 20260829 | 683 | -1.00 | 615 | -1.72 | 68 | +5.47 | 0.473 |
| 20260830 | 1006 | -2.21 | 937 | -2.55 | 69 | +2.41 | 0.446 |
| 20260831 | 722 | -0.70 | 673 | -0.16 | 49 | -8.18 | 0.416 |
| 20260901 | 655 | -2.28 | 589 | -0.60 | 66 | -17.31 | 0.479 |
| 20260902 | 548 | -0.45 | 486 | +0.16 | 62 | -5.22 | 0.464 |
| 20260903 | 1568 | +1.19 | 995 | -0.29 | 573 | +3.75 | 0.461 |
| 20260904 | 1151 | -4.66 | 1032 | -5.71 | 119 | +4.40 | 0.464 |

### robustness of the equal-weighted mean (same marks, information only)
- all: mean -1.23 | winsorised 1/99 -1.14 | mean of daily means -0.97 (sd across days 1.65, n days 35) | std per fill 22.6 | share<0 0.459
- maker: mean -1.40 | winsorised 1/99 -1.16 | mean of daily means -0.83 (sd across days 1.74, n days 35) | std per fill 22.3 | share<0 0.455
- topup_taker: mean -0.46 | winsorised 1/99 -1.01 | mean of daily means -2.62 (sd across days 6.26, n days 31) | std per fill 24.1 | share<0 0.478

## Files
- `out/marks.json` (trade_id -> record, every pending row), `out/archives.json` (per-archive status/sha256/rows), `out/run_meta.json` (device config + counts), `out/validation_20rows.txt`, `logs/run.log`, `logs/commands.txt`, `logs/SHA256SUMS.txt`
- rerun for the missing 2026-09-05 archives once published: `/workspace/venv/bin/python scripts/markout_cdn.py --resume` (keeps ok/no_trade rows, refetches the rest)
