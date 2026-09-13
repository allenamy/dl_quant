#!/usr/bin/env python3
"""t7_pull_addendum_tables.py — renders every number of ADDENDUM_1_full_pull from the collected receipts in T7/pull/ (no hand-copied numbers).
Output T7/pull/TABLES_PULL.md."""
import os, json, collections
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); P = T7 + "/pull"
J = lambda rel: json.load(open(os.path.join(P, rel)))
def jl(rel):
    p = os.path.join(P, rel)
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
PLAN = J("plan/PULL_PLAN_FROZEN.json"); AM = J("plan/AMENDMENT_1_transport.json"); CH = J("checks/CHECKS_T7_pull.json"); IG = J("checks/IDENTITY_GUARD_T7_pull.json")
SP = J("checks/OFFSET_SPECTRUM_T7_pull.json"); SU = J("checks/PULL_SUMMARY.json"); DG = J("checks/MANIFEST_DIGEST.json"); CO = J("COLLECT_RECEIPT.json")
L = []
L.append("## P-1 配置\n| 项 | 值 |\n|---|---|")
L.append(f"| 冻结计划 sha256 | `{open(P + '/plan/PULL_PLAN_FROZEN.json.sha256').read().split()[0]}` |")
L.append(f"| 修订 1(传输) sha256 | `{open(P + '/plan/AMENDMENT_1_transport.json.sha256').read().split()[0]}` |")
L.append(f"| PULL_END(排他) / CUTOFF | {PLAN['pull_end_utc']} / {PLAN['cutoff_utc']} |")
L.append(f"| KRW 市场数 Upbit / Bithumb | {PLAN['n_krw_markets']['upbit']} / {PLAN['n_krw_markets']['bithumb']}(映射 PASS 市场 + KRW-BTC + KRW-USDT) |")
L.append(f"| 映射对 / 币安符号 / 符号-月 | {PLAN['n_pairs']} / {len(PLAN['binance'])} / {PLAN['n_binance_symbol_months']} |")
L.append(f"| 限速 | 每主机任意 1 s 内 ≤ {PLAN['rate']['max_requests_in_any_1s_per_host']} 次且间隔 ≥ {PLAN['rate']['min_gap_s']} s, 三主机并行 |")
L.append("\n## P-2 运行记录(controls / exits)\n| 主机 | 运行 | 控制通过 | 退出码 | 本次数据请求 | 本次完成单元 | 本次错误 | 备注 |\n|---|---|---|---|---|---|---|---|")
for v in ("upbit", "bithumb", "binance"):
    ctl = {c["run_id"]: c for c in jl("run/controls_%s.jsonl" % v)}
    ex = {e["run_id"]: e for e in jl("run/exits_%s.jsonl" % v)}
    for rid in sorted(set(ctl) | set(ex)):
        c = ctl.get(rid, {}); e = ex.get(rid, {})
        note = e.get("stopped") or ("unresolved: %s" % e.get("unresolved") if e.get("unresolved") else "") or ("SIGTERM (修订 1 换传输, 无 exit 记录)" if not e else "")
        L.append(f"| {v} | `{rid}` | {c.get('ok')} | {e.get('exit_code', '—')} | {e.get('n_data_requests', '—')} | {e.get('units_done_this_run', '—')} | {e.get('errors_this_run', '—')} | {note} |")
L.append("\n## P-3 文件数与体积(PULL_SUMMARY)\n| 目录 | 文件数 | 字节 |\n|---|---|---|")
for k in sorted(SU["file_counts"]):
    L.append(f"| {k} | {SU['file_counts'][k]} | {SU['bytes'].get(k, '')} |")
L.append(f"| **合计** | {sum(v for k, v in SU['file_counts'].items() if not k.endswith('_TMP_LEFTOVER'))} | {SU['total_bytes']}({SU['total_GiB']} GiB) |")
L.append("\n| 页文件 | 数 |\n|---|---|")
for k in sorted(SU["page_file_counts_by_venue_unit"]): L.append(f"| {k} | {SU['page_file_counts_by_venue_unit'][k]} |")
L.append("\n## P-4 完整性检查(CHECKS_T7_pull; 规则见冻结计划 checks)\n| 项 | Upbit | Bithumb |\n|---|---|---|")
U, B = CH["venues"]["upbit"], CH["venues"]["bithumb"]
def row(lab, fu, fb): L.append(f"| {lab} | {fu} | {fb} |")
row("市场单元 完成/计划", "%d / %d" % (U["n_done"], U["n_market_units"]), "%d / %d" % (B["n_done"], B["n_market_units"]))
row("完成原因", U["done_reasons"], B["done_reasons"])
row("清单页数 / 撕裂行 / 孤儿文件", "%d / %d / %d" % (U["n_manifest_pages"], U.get("n_manifest_torn_lines", 0), U["n_orphan_files"]), "%d / %d / %d" % (B["n_manifest_pages"], B.get("n_manifest_torn_lines", 0), B["n_orphan_files"]))
for key, lab in (("NOT_DONE", "未完成单元"), ("C0", "C0 页完整性失败单元"), ("DUP", "重复 bar 单元"), ("C2", "C2 页缝断裂单元"), ("C1", "C1 最早 bar 不符单元"), ("C3", "C3 日量不等市场"), ("C4", "C4 新鲜度失败市场")):
    row(lab, U["fail_counts"].get(key, 0), B["fail_counts"].get(key, 0))
row("C3 检查的市场日", U["C3_C4"].get("days_checked", 0), B["C3_C4"].get("days_checked", 0))
row("C3 EXACT / ROUNDING / MISMATCH", "%d / %d / %d" % (U["C3_C4"].get("EXACT", 0), U["C3_C4"].get("ROUNDING", 0), U["C3_C4"].get("MISMATCH", 0)), "%d / %d / %d" % (B["C3_C4"].get("EXACT", 0), B["C3_C4"].get("ROUNDING", 0), B["C3_C4"].get("MISMATCH", 0)))
row("C4 FRESH / THIN_OK / STALE_MISSING / NO_BARS", "%d / %d / %d / %d" % tuple(U["C3_C4"].get("C4_" + k, 0) for k in ("FRESH", "THIN_OK", "STALE_MISSING", "NO_BARS")), "%d / %d / %d / %d" % tuple(B["C3_C4"].get("C4_" + k, 0) for k in ("FRESH", "THIN_OK", "STALE_MISSING", "NO_BARS")))
row("C5 尝试按状态", U["C5"]["attempts_by_status"], B["C5"]["attempts_by_status"])
row("C5 429 次数 / 任意 1 s 最大请求数", "%d / %d" % (U["C5"]["n_429"], U["C5"]["max_sends_in_any_1s"]), "%d / %d" % (B["C5"]["n_429"], B["C5"]["max_sends_in_any_1s"]))
row("C5 错误记录(类型) / 未解决", "%d %s / %d" % (U["C5"]["n_error_records"], U["C5"]["error_kinds"], U["C5"]["n_unresolved_error_records"]), "%d %s / %d" % (B["C5"]["n_error_records"], B["C5"]["error_kinds"], B["C5"]["n_unresolved_error_records"]))
for V, X in (("upbit", U), ("bithumb", B)):
    for key in ("NOT_DONE", "C0", "DUP", "C2", "C1", "C3", "C4"):
        if X["fail_lists"].get(key): L.append(f"\n{V} {key} 失败清单: {', '.join(X['fail_lists'][key][:60])}{' …' if len(X['fail_lists'][key]) > 60 else ''}")
BN = CH["binance"]
L.append("\n## P-5 币安指数价月 zip(C6)\n| 项 | 值 |\n|---|---|")
L.append(f"| 计划符号-月 | {BN['n_symbol_months_planned']} |"); L.append(f"| 状态计数 | {BN['status_counts']} |"); L.append(f"| 旗标计数 | {BN['flag_counts']} |")
L.append(f"| 尝试按状态 / 任意 1 s 最大 / 错误记录 | {BN['C5']['attempts_by_status']} / {BN['C5']['max_sends_in_any_1s']} / {BN['C5']['n_error_records']} {BN['C5']['error_kinds']} |")
for k, v in BN["flags"].items():
    L.append(f"\n{k}({len(v)}): {', '.join(v[:80])}{' …' if len(v) > 80 else ''}")
L.append("\n## P-6 逐对价格同一性守卫(IDENTITY_GUARD_T7_pull)\n| 项 | 值 |\n|---|---|")
L.append(f"| 对数 | {IG['summary']['n_pairs']} |"); L.append(f"| 按状态 | {IG['summary']['by_status']} |")
hrs = [q.get("n_hours_checked", 0) for q in IG["pairs"]]
L.append(f"| 检查小时数合计 / 每对中位 | {sum(hrs)} / {sorted(hrs)[len(hrs) // 2] if hrs else 0} |")
L.append("\n| 所 | 币安符号 | KRW 市场 | 状态 | 检查天数 | 检查区间 | 分歧区间(起, 止, 天) | 尺度嫌疑区间 | 旗标区间内最大 \\|m30\\| |\n|---|---|---|---|---|---|---|---|---|")
for q in IG["pairs"]:
    if q["status"] != "PASS":
        L.append(f"| {q['venue']} | {q['symbol']} | {q['market']} | {q['status']} | {q.get('checked_days', '')} | {q.get('checked_range', '')} | {q.get('diverge_ranges', '')} | {q.get('scale_suspect_ranges', '')} | {q.get('extreme_abs_m30_in_flagged', '')} |")
L.append("\n## P-7 偏移谱时间戳守卫(逐年; OFFSET_SPECTRUM_T7_pull)\n| 所 | 市场 | 年 | 小时 | KRW bar | 指数 bar | argmax ρ | ρ(−1)/ρ(0)/ρ(+1) | 离散度 argmin | 负控 KST(+9) | 负控 收盘标签(+1) | PASS |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
for c in SP["cells"]:
    if "PASS" in c:
        L.append(f"| {c['venue']} | {c['market']} | {c['year']} | {c['hours']} | {c['krw_bars']} | {c['index_bars']} | {c['argmax_rho']} | {c['rho_m1']} / {c['rho0']} / {c['rho_p1']} | {c['argmin_disp']} | {c['NEG_kst']['argmax_rho']} {'红' if c['NEG_kst']['RED'] else '未红'} | {c['NEG_close']['argmax_rho']} {'红' if c['NEG_close']['RED'] else '未红'} | {c['PASS']} |")
L.append(f"\n汇总: {SP['summary']}")
C3D = J("checks/C3_MISMATCH_DETAIL.json"); RPU = J("checks/C3_REPULL_upbit.json"); RPB = J("checks/C3_REPULL_bithumb.json"); BG = J("checks/BINANCE_ARCHIVE_GAPS.json")
L.append("\n## P-9 C3 日量不等的明细与重拉核验(C3_MISMATCH_DETAIL / C3_REPULL_*)\n| 项 | Upbit | Bithumb |\n|---|---|---|")
su, sb = C3D["summary"].get("upbit", {}), C3D["summary"].get("bithumb", {})
L.append(f"| 不等市场日 | {su.get('days', 0)} | {sb.get('days', 0)} |")
L.append(f"| 小时和 < 日量 / 小时和 > 日量 / 无小时 bar / 无日 bar | {su.get('hourly_lt_day', 0)} / {su.get('hourly_gt_day', 0)} / {su.get('no_hourly', 0)} / {su.get('no_day_bar', 0)} | {sb.get('hourly_lt_day', 0)} / {sb.get('hourly_gt_day', 0)} / {sb.get('no_hourly', 0)} / {sb.get('no_day_bar', 0)} |")
L.append(f"| 是该市场首个检查日 | {su.get('first_day', 0)} | {sb.get('first_day', 0)} |")
L.append(f"| 按年 | {C3D['by_year'].get('upbit')} | {C3D['by_year'].get('bithumb')} |")
import statistics
for V in ("upbit", "bithumb"):
    rs = sorted(x["ratio_h_over_d"] for x in C3D["days"] if x["venue"] == V and x["ratio_h_over_d"] is not None)
    if rs: L.append(f"| {V} 小时和/日量 [最小, p10, 中位, p90, 最大] | {[round(rs[0], 4), round(rs[len(rs) // 10], 4), round(statistics.median(rs), 4), round(rs[9 * len(rs) // 10], 4), round(rs[-1], 4)]} | |")
L.append(f"| 最集中的日期 | {C3D['top_dates'].get('upbit', [])[:5]} | {C3D['top_dates'].get('bithumb', [])[:5]} |")
L.append(f"| **重拉核验判决**(同一天 60m + 日 K 今天再取, 与存档逐字段比) | {RPU['verdicts']} / {RPU['n_days']} | {RPB['verdicts']} / {RPB['n_days']} |")
L.append("\n## P-10 币安月 zip 内缺失的整日(BINANCE_ARCHIVE_GAPS; 未做任何补填)\n| 项 | 值 |\n|---|---|")
for k, v in BG["summary"].items(): L.append(f"| {k} | {v} |")
if BG.get("daily_zip_probe"):
    L.append("\n| 日 zip 探针 | 状态 | 字节 |\n|---|---|---|")
    for x in BG["daily_zip_probe"]: L.append(f"| {x['symbol']} {x['date']} | {x['status']} | {x['bytes']} |")
BF = J("checks/BINANCE_FORMAT_BREAKDOWN.json")
L.append("\n## P-11 C6 旗标拆因(BINANCE_FORMAT_BREAKDOWN)\n| 项 | 值 |\n|---|---|")
L.append(f"| OK zip / FORMAT_FAIL(任一子项) | {BF['n_ok_zips']} / {BF['format_fail_any']} |")
L.append(f"| 子项失败计数 | {BF['sub_check_failures']} |"); L.append(f"| 子项按年 | {BF['sub_check_failures_by_year']} |")
L.append(f"| 既无表头又不连续 | {BF['both_no_header_and_not_contiguous']} |"); L.append(f"| PARTIAL_MONTH: 上市/下市边界月 vs 内部月 | {BF['partial_months']} |")
L.append("\n## P-8 入库的小件(COLLECT_RECEIPT)\n| 项 | 值 |\n|---|---|")
L.append(f"| 复制文件数 / 字节 | {len(CO['files'])} / {sum(x['bytes'] for x in CO['files'])} |"); L.append(f"| 页清单 | {CO['page_manifests']}(gz 合计 {CO['page_manifest_gz_total_bytes']} 字节) |")
L.append("\n| 清单文件(数据在 cc_tmp) | sha256 | 字节 | 行 |\n|---|---|---|---|")
for f, x in DG["manifest_files_sha256"].items(): L.append(f"| {f} | `{x['sha256'][:16]}…` | {x['bytes']} | {x['lines']} |")
open(P + "/TABLES_PULL.md", "w").write("\n".join(L) + "\n"); print("\n".join(L)[:3000])
