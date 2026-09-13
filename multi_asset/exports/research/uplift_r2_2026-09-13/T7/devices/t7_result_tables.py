#!/usr/bin/env python3
"""t7_result_tables.py — renders every numeric table of RESULT_T7_feasibility.md from the receipts (no hand-copied numbers). Output receipts/TABLES_T7.md."""
import os, json
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R = T7 + "/receipts"
J = lambda f: json.load(open(os.path.join(R, f)))
A = J("PROBE_A_conventions.json"); A2 = J("PROBE_A2_tsfield.json"); B = J("PROBE_B_depth.json"); Cc = J("PROBE_C_survivorship.json")
CEN = J("CENSUS_krw_markets.json"); M1 = J("MAPPING_guard.json"); M2 = J("MAPPING_guard_r2.json"); COV = J("COVERAGE_T7.json"); G = J("GUARDS_sample.json")
PL = J("PLAN_full_pull.json"); AR = J("ARCHIVE_listings.json"); SM = json.load(open(T7 + "/sample/SAMPLE_MANIFEST.json")); U = J("pod2/RECEIPT_T7_universe_pod2.json")
L = []
def pct(x): return "%.1f%%" % (100 * x)
L.append("## T-1 时间戳与 `to` 语义(PROBE_A / A2)\n| 项 | Upbit | Bithumb |\n|---|---|---|")
for k in ("A1_m60", "A1_m1", "A1_m240"):
    u, b = A["venues"]["upbit"][k], A["venues"]["bithumb"][k]
    L.append(f"| {k} 最新 bar 标签 = 请求时刻向下取整 | {u['newest_is_request_floor']} | {b['newest_is_request_floor']} |")
    L.append(f"| {k} 标签对齐到单位整点(UTC) | {u['open_aligned_to_unit']} | {b['open_aligned_to_unit']} |")
    L.append(f"| {k} KST−UTC 标签差(秒) | {u['kst_minus_utc_label_seconds']} | {b['kst_minus_utc_label_seconds']} |")
for k in ("iso_Z", "naive_T", "naive_space", "kst_offset", "iso_Z_plus1s"):
    u, b = A["venues"]["upbit"]["A2_to_" + k], A["venues"]["bithumb"]["A2_to_" + k]
    L.append(f"| `to={u['to']}` ⇒ 最新 bar open(UTC) | {u['newest_open_utc']} | {b['newest_open_utc'] or '**空列表 (HTTP ' + str(b['status']) + ')**'} |")
L.append(f"| 日 K 标签(UTC) | {A['venues']['upbit']['A3_days']['rows'][0]['candle_date_time_utc']} | {A['venues']['bithumb']['A3_days']['rows'][0]['candle_date_time_utc']} |")
for c in (200, 201, 1000):
    L.append(f"| count={c} 实得行数 | {A['venues']['upbit']['A4_count_%d' % c]['n']} | {A['venues']['bithumb']['A4_count_%d' % c]['n']} |")
L.append(f"| 限速响应头(首个 60m 请求) | `{A['venues']['upbit']['A1_m60']['rate_header']}` | `x-ratelimit-remaining: {A['venues']['bithumb']['A1_m60']['rate_header']}` |")
for mk in ("KRW-BTC", "KRW-XRP", "KRW-USDT"):
    u, b = A2["A2_ts_field"][f"upbit_{mk}_m60"], A2["A2_ts_field"][f"bithumb_{mk}_m60"]
    L.append(f"| {mk} 60m: `timestamp` 落在 [open, open+1h) 外的 bar 数 / 最大 (timestamp−open) 秒 | {u['n_outside']}/200, {u['max_ts_minus_open_s']} | {b['n_outside']}/200, {b['max_ts_minus_open_s']} |")
L.append(f"| 已收盘 bar 70 秒后重读改变数 | {A2['A2_revision_70s']['upbit']['n_changed']}/{A2['A2_revision_70s']['upbit']['n_closed_common']} | {A2['A2_revision_70s']['bithumb']['n_changed']}/{A2['A2_revision_70s']['bithumb']['n_closed_common']} |")
L.append("\n## T-2 历史深度 / USDT 起点 / 下市可查性(PROBE_B / C)\n| 项 | Upbit | Bithumb |\n|---|---|---|")
for k, lab in (("B1_KRW-BTC_days", "KRW-BTC 最早日 K"), ("B1_KRW-BTC_60", "KRW-BTC 最早 60m"), ("B1_KRW-BTC_1", "KRW-BTC 最早 1m"), ("B2_KRW-USDT_days", "KRW-USDT 最早日 K"), ("B2_KRW-USDT_60", "KRW-USDT 最早 60m")):
    L.append(f"| {lab} | {B['venues']['upbit'][k]['earliest']} | {B['venues']['bithumb'][k]['earliest']} |")
for v in ("upbit", "bithumb"):
    c = B["venues"][v]["B3_delisted_candidates"]
    n404 = sum(1 for mk, r in c.items() if not r["in_market_all_now"] and (r["status"] != 200 or r["n"] is None))
    L.append(f"| {v}: 不在今日列表的候选代码中「Code not found」数 | {n404 if v == 'upbit' else ''} | {n404 if v == 'bithumb' else ''} |")
arch_conf = {}
for v in ("upbit", "bithumb"):
    c = B["venues"][v]["B3_delisted_candidates"]
    arch_conf[v] = sorted(mk for mk, r in c.items() if not r["in_market_all_now"] and any(mk in s.get("krw_codes", []) for s in AR["snapshots"][v].values()))
L.append(f"| 其中经网页存档确认「曾在该所 KRW 上市」的代码 | {', '.join(arch_conf['upbit'])} | {', '.join(arch_conf['bithumb'])} |")
nb = {v: B["venues"][v]["B3_delisted_candidates"]["KRW-ZZZNOTACOIN"] for v in ("upbit", "bithumb")}
L.append(f"| 从未存在代码 KRW-ZZZNOTACOIN | HTTP {nb['upbit']['status']} `{nb['upbit']['body_head']}` | HTTP {nb['bithumb']['status']} (body 同 Upbit, 见日志) |")
L.append(f"| 兜底源: Upbit 网页 CDN crix(KRW-LUNA/WEMIX) | HTTP {Cc['C1_upbit_crix']['KRW-WEMIX latest']['status']} Code not found | — |")
L.append(f"| 兜底源: CryptoCompare 免 key | HTTP {Cc['C2_cryptocompare']['Upbit:LUNA/KRW histoday to 2022-06-01']['status']} API key required | HTTP {Cc['C2_cryptocompare']['Bithumb:LUNA/KRW histoday to 2022-06-01']['status']} |")
for v in ("upbit", "bithumb"):
    g = B["venues"][v]["B4_gaps"]; mk = g["thinnest3"][0]
    L.append(f"| {v} 最薄市场 {mk} 60m: 200 根 bar 跨 {g[mk + '_m60']['span_units']} 小时, 零成交量 bar {g[mk + '_m60']['zero_volume_candles']} | ⇒ 无成交的小时不出 bar | |")
L.append("\n## T-3 KRW 市场普查(CENSUS, 当前在市)\n| 所 | KRW 市场数 | 错误 | 无 bar | 有缺月 | 首日年份分布 |\n|---|---|---|---|---|---|")
for v in ("upbit", "bithumb"):
    Rv = CEN["venues"][v]; fy = [r["first_day_utc_label"][:4] for r in Rv["markets"].values() if "first_day_utc_label" in r]
    L.append(f"| {v} | {Rv['n_krw']} | {Rv['n_error_final']} | {Rv['n_no_candles']} | {sum(1 for r in Rv['markets'].values() if r.get('gap_months_kst'))} | {', '.join(f'{y}:{fy.count(y)}' for y in sorted(set(fy)))} |")
L.append("\n## T-4 映射与价格同一性守卫(MAPPING r1 + r2)\n| 所 | 有候选的合格名 | PASS 选用 | 按规则×判决 |\n|---|---|---|---|")
from collections import Counter
for v in ("upbit", "bithumb"):
    cnt = Counter(); ch = 0; n = 0
    for s, d in M2["pairs"].items():
        if v in d:
            n += 1; ch += bool(d[v]["chosen"])
            for r in d[v]["candidates"]: cnt[(r["rule"], r["verdict"])] += 1
    L.append(f"| {v} | {n} | {ch} | {'; '.join(f'{a}/{b}={c}' for (a, b), c in sorted(cnt.items()))} |")
L.append("\n### 非 exact 规则或非 PASS 的全部对\n| 所 | 币安符号 | KRW 市场(名称) | 规则 | 判决 | R | 检查时刻 T | KRW 首日 |\n|---|---|---|---|---|---|---|---|")
for s, d in sorted(M2["pairs"].items()):
    for v in ("upbit", "bithumb"):
        for r in d.get(v, {}).get("candidates", []):
            if r["rule"] != "exact" or r["verdict"] != "PASS":
                L.append(f"| {v} | {s} | {r['krw_market']} ({r['english_name']}) | {r['rule']} | {r['verdict']} | {r.get('R', '')} | {r['T_utc']} | {r['krw_first_day_utc']} |")
L.append(f"\n预检(币安归档格式): `{M1['preflight']['BTCUSDT_T_CAP']['url']}` 表头 {M1['preflight']['BTCUSDT_T_CAP']['header'][:6]}…, open_time 单位 {M1['preflight']['BTCUSDT_T_CAP']['open_time_unit']}")
L.append("\n## T-5 合格宇宙覆盖率(按名计, 池化锚×名格; 映射 PASS 且 KRW 首日 ≤ 锚 − 1 日)\n| 年 | 回放锚 | 平均合格名 | Upbit | Bithumb | 并集 | 两所都有 | 逐锚并集 [最小, 最大] |\n|---|---|---|---|---|---|---|---|")
for y, r in COV["per_year_count"].items():
    L.append(f"| {y} | {r['n_anchors']} | {r['mean_n_eligible']} | {pct(r['upbit']['pooled_cell_frac'])} | {pct(r['bithumb']['pooled_cell_frac'])} | {pct(r['union']['pooled_cell_frac'])} | {pct(r['both']['pooled_cell_frac'])} | [{pct(r['union']['min_anchor_frac'])}, {pct(r['union']['max_anchor_frac'])}] |")
a = COV["all_years_count"]
L.append(f"| 全部 | {COV['n_replay_anchors']} | — | {pct(a['upbit']['pooled_cell_frac'])} | {pct(a['bithumb']['pooled_cell_frac'])} | {pct(a['union']['pooled_cell_frac'])} | {pct(a['both']['pooled_cell_frac'])} | |")
lw = COV["live_weight_coverage"]
L.append(f"\n**实盘书按权重**({lw['n_used']} 个 target_live 副本, {lw['first_anchor_utc']} .. {lw['last_anchor_utc']}; 生产者 {', '.join(lw['producers'])}):\n| 所 | 毛权重覆盖均值 [最小, 最大] | 持仓名数覆盖均值 |\n|---|---|---|")
for k in ("upbit", "bithumb", "union"):
    L.append(f"| {k} | {pct(lw[k]['gross_weight_frac_mean'])} [{pct(lw[k]['min'])}, {pct(lw[k]['max'])}] | {pct(lw[k]['held_name_count_frac_mean'])} |")
xc = U["crosscheck_vs_archived_arms"]
L.append("\n**分母复核**(装置对存档 r18 臂逐锚): " + "; ".join(f"{k}: rows {v['n_rec_rows']}, n_sel 差 {v['n_sel_mismatch']}, len(m) 差 {v['len_m_mismatch']}, PASS={v['PASS']}" for k, v in xc.items()))
L.append("\n## T-6 幸存者偏差(网页存档快照 vs 今日可查)\n| 所 | 半年 | 快照 | 当时 KRW 市场 | 今日查不到 上界/下界 | 快照锚合格名 | 可查且 PASS 覆盖 | 当时按 ticker 在市 | 因下市而丢失(占合格名) |\n|---|---|---|---|---|---|---|---|---|")
for v in ("upbit", "bithumb"):
    for h, r in COV["survivorship_archive"][v].items():
        e = r.get("eligible_impact")
        L.append(f"| {v} | {h} | {r['snapshot_ts']} | {r['n_listed']} | {pct(r['frac_not_queryable_UPPER'])} / {pct(r['frac_not_queryable_LOWER'])} | "
                 + (f"{e['n_eligible']} | {pct(e['frac_covered_queryable'])} | {pct(e['frac_ticker_listed_then'])} | {pct(e['frac_lost_to_survivorship'])} |" if e else "— | — | — | — |"))
L.append("\n## T-7 样本守卫(GUARDS_sample; 360 锚)\n| 所 | G1 因果(违例/格) | G1 负控 bar=N(违例/格) | G2 命中率 def A (新鲜率) | G2 命中率 def B (新鲜率) | BTC pB 水平 [最小, 中位, 最大] |\n|---|---|---|---|---|---|")
for v, r in G["venues"].items():
    g1 = r["G1_causality"]; nc = g1["negative_control_leaky"]; a_ = r["G2_hit_rate_defA"]; b_ = r["G2_hit_rate_defB"]; bt = r["SANITY_btc_pB"]
    L.append(f"| {v} | {g1['violations']}/{g1['cells_checked']} | {nc['violations']}/{nc['cells_with_bar_open_eq_N']} | {a_['hit_rate']} ({a_['fresh_frac_of_valid']}) | {b_['hit_rate']} ({b_['fresh_frac_of_valid']}) | [{bt['min']}, {bt['median']}, {bt['max']}] |")
L.append("\n| 所 | 市场 | G3 argmax ρ | ρ(−1) / ρ(0) / ρ(+1) | 离散度 argmin | D(0)/min D(±1) | 负控 KST 当 UTC argmax | 负控 收盘标签 argmax | PASS |\n|---|---|---|---|---|---|---|---|---|")
for v, r in G["venues"].items():
    for mk, sp in r["G3_offset_spectrum"].items():
        L.append(f"| {v} | {mk} | {sp['argmax_rho']} | {sp['rho_m1']} / {sp['rho0']} / {sp['rho_p1']} | {sp['argmin_dispersion']} | {sp['disp0_over_disp1_min']} | {sp['NEG_kst_as_utc']['argmax_rho']} | {sp['NEG_close_time_label']['argmax_rho']} | {sp['PASS']} |")
L.append(f"\nXRP 两所 def B 之差: 中位 {G['SANITY_cross_venue_XRP_pB_abs_diff']['median']}, p95 {G['SANITY_cross_venue_XRP_pB_abs_diff']['p95']}(n={G['SANITY_cross_venue_XRP_pB_abs_diff']['n']})")
L.append("\n## T-8 样本拉取清单(SAMPLE_MANIFEST)\n| 市场 | bar 数/小时数 | 页数 | V2 整点 | V3 页缝 | V4 日量恒等(天/不等/仅舍入) | 60m 文件 sha256 |\n|---|---|---|---|---|---|---|")
for k, r in SM["krw"].items():
    v4 = r["V4_volume_identity"]
    L.append(f"| {k} | {r['n_bars_in_window']}/{r['hours_in_window']} | {r['n_pages']} | {r['V2_hour_aligned']} | {r['V3_seams_ok']} | {v4['n_days_checked']}/{v4['n_mismatch']}/{v4['n_rounding_only']} | `{r['sha256_60m'][:16]}…` |")
for s, r in SM["binance"].items():
    L.append(f"| binance {s} | {r['n_rows_in_window']}/1440 | {len(r['source_files'])} zip | ms={r['V5']['ms_units']} | 连续={r['V5']['contiguous']} | 行数 {r['V5']['n_rows']}={r['V5']['expected_rows']}, close_time=open+3599999: {r['V5']['close_time_is_open_plus_3599999']} | `{r['sha256'][:16]}…` |")
L.append(f"\n样本请求数 {SM['n_requests']}; 窗口 {SM['window_utc']}")
L.append("\n## T-9 全量拉取预算(PLAN_full_pull; 上界 = ceil(小时/200))\n| 所 | 范围 | 市场数 | 60m 请求 | 日 K 请求 | 合计 | 5 req/s 小时 | 4 req/s 小时 | gz CSV MB |\n|---|---|---|---|---|---|---|---|---|")
for v, r in PL["venues"].items():
    for sc in ("S-MAP/H-REPLAY", "S-MAP/H-FULL", "S-ALL/H-REPLAY", "S-ALL/H-FULL"):
        x = r[sc]; nmk = r["n_markets_" + sc.split("/")[0]]
        L.append(f"| {v} | {sc} | {nmk} | {x['req_60m']} | {x['req_days']} | {x['req_total']} | {x['hours_at_5rps']} | {x['hours_at_4rps']} | {x['gzcsv_MB_upper']} |")
L.append(f"| binance vision | indexPriceKlines 1h 月 zip | {PL['binance']['n_symbols']} 符号 | — | — | {PL['binance']['monthly_zips_indexPriceKlines']} | {PL['binance']['hours_at_5rps']} | {round(PL['binance']['monthly_zips_indexPriceKlines'] / 4 / 3600, 2)} | — |")
open(R + "/TABLES_T7.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
