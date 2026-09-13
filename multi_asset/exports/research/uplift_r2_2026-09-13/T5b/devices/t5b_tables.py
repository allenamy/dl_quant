#!/usr/bin/env python3
"""t5b_tables.py — renders receipts/TABLES_T5b.md from T5b receipts only (no new measurement except arithmetic summaries of receipt series).
Launch: env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_tables.py <T5b dir> CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING
"""
import os, sys, json, collections
T5B = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
sys.path.insert(0, T5B + "/devices")
import numpy as np
import t5b_common as TC
R = lambda n: json.load(open(f"{T5B}/receipts/{n}"))
Q1 = R("RECEIPT_T5b_q1.json"); Q1P = R("RECEIPT_T5b_q1_posthoc.json"); DG = R("RECEIPT_T5b_diag_cd2.json"); EX = R("RECEIPT_T5b_exec.json"); EXP = R("RECEIPT_T5b_exec_posthoc.json"); CP = R("RECEIPT_T5b_copy.json")
ROWS = json.load(open(f"{T5B}/receipts/T5b_exec_rows.json")); assert TC.sha(f"{T5B}/receipts/T5b_exec_rows.json") == EX["rows_sha256"]
f = lambda x, d=4: ("—" if x is None else (f"{x:+.{d}f}" if isinstance(x, (int, float)) else str(x)))
L = []; P = L.append
P("> 由 `devices/t5b_tables.py` 从 `receipts/*.json` 渲染; 每张表注明来源收据。单位: carry = bps / 4h 锚 / 单位 gross(正 = 付); USDT 为名义。")
P(""); P("# TABLES · T5b"); P("")
# T0 gates
g = Q1["gates"]; ge = EX["gates"]
P("## T0 门(RECEIPT_T5b_q1.json / RECEIPT_T5b_exec.json / RECEIPT_T5b_copy.json)"); P("| 门 | 结果 | 读数 |"); P("|---|---|---|")
P(f"| COPY | rc 0 | 拷贝 {CP['n_copied']} 文件, 缺 {CP['n_missing']}(均为预期缺席), 凭据命中 {CP['n_skipped_secret']}, 源在拷贝期间不变 {CP['integrity_counts']['UNCHANGED']}, git 导出 {sum(1 for x in CP['git_exports'] if x.get('present'))}; 执行器 HEAD {CP['exec_head'][:9]}; 拷贝时刻 {CP['copy_utc']} |")
P(f"| 首个 FTRIM 锚 | {'PASS' if g['FIRST_FTRIM']['PASS'] else 'FAIL'} | target_combo 09-02 12Z 首含 ftrim 键; combo_live.log 块头 L{g['FIRST_FTRIM']['block_line']}, 首行 L{g['FIRST_FTRIM']['first_ftrim_line']} |")
P(f"| G-ARCH | {'PASS' if g['G_ARCH']['PASS'] else 'FAIL'} | {g['G_ARCH']['n']} 锚 max|w_tl − (0.55 kc + 0.45 fc)| = {g['G_ARCH']['max_abs']} |")
P(f"| G-LEDGER | {'PASS' if g['G_LEDGER']['PASS'] else 'FAIL'} | 重叠行冲突 {g['G_LEDGER']['n_conflicts']}; 截断尾 W1 {g['G_LEDGER']['n_truncated_W1']} / CT5 {g['G_LEDGER']['n_truncated_CT5']} |")
P(f"| G-RN8(诊断) | — | MATCH {g['G_RN8']['classes']['MATCH']} / 前一结算 {g['G_RN8']['classes']['MATCH_PREV_SETTLEMENT']} / MISMATCH {g['G_RN8']['classes']['MISMATCH']} / 无行 {g['G_RN8']['classes']['NO_ROW']} |")
P(f"| G-MECH | {'PASS' if g['G_MECH']['PASS'] else 'FAIL'} | 可识别链-锚 {g['G_MECH']['identifiable_chain_anchors']}(不可识别 {g['G_MECH']['unidentifiable_chain_anchors']}); t* 极差 max {g['G_MECH']['tstar_spread_max']:.2e}; (b) 失败 {g['G_MECH']['n_b_fail']}; (c) 逐名核对 {g['G_MECH']['n_c_checked']} 不符 {g['G_MECH']['n_c_mismatch']}; 从 0 新开 {len(g['G_MECH']['opened_from_zero'])} |")
cd = g["G_CARRY_CD2"]; ct = g["G_CARRY_CT5"]
P(f"| G-CARRY-CD2 | {'PASS' if cd['PASS'] else '**FAIL**'} | {cd['n']} 锚; max|Δcarry| {cd['max_abs_d_carry']:.4f}, max|Δcoh| {cd['max_abs_d_coh']:.4f}; 同文件 sha {cd['all_same_file']} ⇒ Q1 读法 PROVISIONAL |")
P(f"| G-CARRY-CT5 | {'PASS' if ct['PASS'] else 'FAIL'} | 27 锚 max|Δ C_D| {ct['max_abs_d']:.1e}; TC1 两格 Δ {ct['cells']['short|<=-30bp']['d']:.1e} / {ct['cells']['short|-30..-10bp']['d']:.1e} |")
P(f"| G-DET | {'PASS' if g['G_DET']['PASS'] else 'FAIL'} | " + "; ".join(f"{k} {'PASS' if v['PASS'] else 'FAIL'}" for k, v in g["G_DET"]["cells"].items()) + " |")
P(f"| G-FILE | {'PASS' if ge['G_FILE']['n_fail'] == 0 else 'FAIL'} | {ge['G_FILE']['n']} 锚 执行器 json_sha == 副本 sha 且 gross_in 重算一致; 失败 {ge['G_FILE']['n_fail']} |")
P(f"| G-PLAN | {'PASS' if ge['G_PLAN']['n_fail'] == 0 else 'FAIL'} | {ge['G_PLAN']['n']} maker 行; 失败 {ge['G_PLAN']['n_fail']} |")
P(f"| G-S | — | 比对 {ge['G_S']['n_compared']} 锚失败 {ge['G_S']['n_fail']}; reshape 字段缺 {len(ge['G_S']['missing'])} 锚({ge['G_S']['missing'][0]}..{ge['G_S']['missing'][-1]}, E-0908-A 段) |")
gc = ge["G_CODE"]
P(f"| G-CODE | {'PASS' if gc['PASS'] else 'FAIL'} | {gc['n_versions']} 个代码版本(C_code 提交 + 工作树)全部含: 外部书跳过中性带 / 跳过 harvest EMA / DEFAULT_BAND_BPS = 0.0 / plan 最小名义额跳过 / 2×minNotional 撤下 / withhold+reshape; 非测试 band_bps= 赋值 {len(gc['band_bps_non_test_assignments'])} |")
P("")
# T1 Q1 readings
P("## T1 Q1 读法(RECEIPT_T5b_q1.json readings; 日块自举 11 块)"); P("| 量 | 角色 | 锚数 | 均值 | CI95 | 累计 | 读法 |"); P("|---|---|---|---|---|---|---|")
for k, v in Q1["readings"].items():
    if "reading" not in v: continue
    P(f"| {k} | {v['role']} | {v['n_anchors']} | {f(v['mean'])} | [{f(v['ci95'][0])}, {f(v['ci95'][1])}] | {f(v['cumulative'], 3)} | {v['reading']} |")
for k in ("share_tl_FROZ", "share_tl_RES"):
    v = Q1["readings"][k]; P(f"| {k}(gross 份额) | 描述 | {v['n_anchors']} | {v['mean']:.5f} | [{v['ci95'][0]:.5f}, {v['ci95'][1]:.5f}] | — | max {v['max']:.5f} |")
P("")
P("## T2 Q1 计数与年龄(RECEIPT_T5b_q1.json summary)"); P("| 书 | 纳入锚 | 残余名 均/最大 | 冻结名 均/最大 | 冻结实例 | 冻结实例中空头占比 | 年龄 p50 / p90 / max(锚) | 年龄分箱 | 曾冻结名数 | 冻结段数(末锚仍冻结) | 离开 F 后仍不变 |"); P("|---|---|---|---|---|---|---|---|---|---|---|")
for b, s in Q1["summary"].items():
    aq = s["age_quantiles"] or {}
    P(f"| {b} | {s['n_anchors_included']} | {s['n_RES_mean']:.2f} / {s['n_RES_max']} | {s['n_FROZ_mean']:.2f} / {s['n_FROZ_max']} | {s['n_FROZ_total_instances']} | {s['short_share_of_FROZ_instances']:.3f} | {aq.get('p50')} / {aq.get('p90')} / {aq.get('max')} | {s['age_bins']} | {s['distinct_names_ever_frozen']} | {s['n_runs']}({s['n_runs_right_censored']}) | {s['n_post_F_unchanged_total']} |")
P(""); P("tl 最长冻结段(前 10): " + "; ".join(f"{x['symbol']} 起 {x['start']} 长 {x['length']}{' 右删失' if x['right_censored'] else ''}" for x in Q1["summary"]["tl"]["runs_longest"][:10])); P("")
# T3 posthoc split
P("## T3 Q1 事后描述: 按残余方向拆分(RECEIPT_T5b_q1_posthoc.json; POST-HOC, 不改读法)"); P("| 量 | 均值 | CI95 | 累计 |"); P("|---|---|---|---|")
for k in ("FROZ_short", "FROZ_long", "RES_short", "RES_long"):
    v = Q1P[k]; P(f"| tl {k} | {f(v['mean'])} | [{f(v['ci95'][0])}, {f(v['ci95'][1])}] | {f(v['cumulative'], 3)} |")
P(f"| tl FROZ 去掉 |C_FROZ| 最大 3 锚后均值 | {f(Q1P['mean_C_FROZ_without_top3_abs_anchors'])} | — | — |"); P("")
P("| 名 | 冻结 carry 均贡献 | 全残余 carry 均贡献 | 冻结锚数 | 残余锚数 | 方向 |"); P("|---|---|---|---|---|---|")
for x in Q1P["per_name_froz_top"][:12]: P(f"| {x['symbol']} | {f(x['froz_mean_contrib'])} | {f(x['res_mean_contrib'])} | {x['n_froz']} | {x['n_res']} | {'/'.join(x['sides'])} |")
P(""); P("|C_tl^FROZ| 最大的锚: " + "; ".join(f"{x['utc']} {f(x['C_FROZ'], 3)}(" + ", ".join(f"{n['symbol']} w {n['w_tl']:+.5f} c4 {n['c4_bps']:+.1f}" for n in x['names'] if abs(n['w_tl'] * n['c4_bps']) > 0.2) + ")" for x in Q1P["top_anchors_abs_C_FROZ"][:4])); P("")
# T4 CD2 diag
P("## T4 G-CARRY-CD2 红的定位(RECEIPT_T5b_diag_cd2.json; POST-HOC 诊断)"); rows = DG["per_anchor"]
dm = np.array([r["d_mine"] for r in rows]); P(f"- 46 锚 Δ(本装置 − T1 D2)均值 {dm.mean():+.4f}, 中位 {np.median(dm):+.4f}, |Δ| > 1e-3 的锚 {int((np.abs(dm) > 1e-3).sum())}; 账本 iv 字段与其相邻两次结算间隔不符的持仓名: {sum(r['n_interval_flags'] for r in rows)}。")
def _implied(anchor, sym, part):
    rr = next(r for r in rows if r["utc"] == anchor); wl = DG["worst"][anchor]; x = next(v for v in wl if v["symbol"] == sym)
    mine = x["w_unit"] * x["c4_bps"]; d = rr["d_components"][part]; t1 = mine - d
    return mine, d, t1, (t1 / mine if mine else None)
for anc, sym, part, note in (("2026-09-02 20:00Z", "SKRUSDT", "carry_S", "账本与执行器结算行 iv=1(逐小时)"), ("2026-09-08 16:00Z", "SOPHUSDT", "carry_L", "账本与执行器 16:00Z 行 iv=1"), ("2026-09-10 00:00Z", "IOSTUSDT", "carry_L", "账本 00:00Z 行 iv=8, 执行器结算行 09-10 01:00Z 起才为 iv=1")):
    mine, d, t1, ratio = _implied(anc, sym, part)
    P(f"- {anc} {sym}: 本装置贡献 {mine:+.4f}; 该侧 Δ {d:+.4f} 若全归此名 ⇒ D2 口径贡献 {t1:+.4f}, 比值 {ratio:.3f}({note})。")
P("- 09-09 16Z..09-10 00Z 与 09-06 16Z..09-09 12Z: D2 的非 8h gross 份额比本装置大 0.0004..0.0037, Δ 同时出现在 st15 名组, 与 D2 把 IOSTUSDT 计为非 8h 同向(执行器与账本在 09-10 00Z 前均为 8h)。")
P("| 锚 | Δ carry | Δ 空头 | Δ 多头 | Δ 非8h | Δ st15 |"); P("|---|---|---|---|---|---|")
for r in rows:
    if abs(r["d_mine"]) > 0.2: dc = r["d_components"]; P(f"| {r['utc']} | {f(r['d_mine'])} | {f(dc['carry_S'])} | {f(dc['carry_L'])} | {f(dc['non8h_carry'])} | {f(dc['st15_carry'])} |")
P("")
# T5 Q2 cohort
Q2 = EX["Q2"]; P("## T5 Q2 八月队列 × 执行器逐名止损(RECEIPT_T5b_exec.json Q2)")
cfgs = EX["config"]["versions"]; P(f"- 配置(C_cfg {len(cfgs) - 1} 个提交 + 工作树): enabled {cfgs[0]['enabled']}, profile {cfgs[0]['_profile']}, depth {cfgs[0]['depth_pct']}, 连续 {cfgs[0]['consecutive_anchors']} 锚, 冷却 {cfgs[0]['cooloff_days']} 天, min_notional {cfgs[0]['min_notional_usdt']} USDT; 键不恒定只因 37186e6(08-22 04:58Z)min_notional 20.0 → 82476ad(05:58Z)5.0, 均在 W2 之前; gross_mult(按提交时刻)W2 起点 1.5 → 2.0(08-26 09:10Z ccdd1bb)→ 1.5(08-26 13:10Z 0ef08d2)→ 1.75(08-27 01:24Z 5c1f677)→ 2.0(08-27 05:06Z e3e8685)。")
P("- W2 执行器锚类: " + json.dumps(dict(collections.Counter(v["cls"] for v in Q2["classes"].values())), ensure_ascii=False) + "; 非 NORMAL: " + "; ".join(f"{k} {v['cls']}" for k, v in Q2["classes"].items() if v["cls"] != "NORMAL"))
P("| 名 | 回答 | 条款被评估锚数 | counter≥1 锚 | W2 事件 | 窗外事件 | NORMAL 锚 | H_post/T_file 中位 [p10, p90] | |H_post|>|T_file| 占比 | 队列 carry 差均值 | 重建深度最小 | 重建状态 |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|")
for s, v in Q2["answers"].items():
    rt = v["ratio_Hpost_over_Tfile"] or {}
    P(f"| {s} | **{v['answer']}** | {v['n_anchors_pns_evaluated']}/31 | {len(v['anchors_counter_ge1'])} | {len(v['all_events_W2'])} | {len(v['events_W2plus_OUTSIDE_WINDOW'])} | {v['n_normal_anchors']} | {rt.get('median', float('nan')):.3f} [{rt.get('p10', float('nan')):.3f}, {rt.get('p90', float('nan')):.3f}] | {f(v['frac_abs_Hpost_gt_abs_Tfile'], 3)} | {f(v['mean_carry_gap_bps'], 4)} | {f(v['depth_rec_min'], 3)} | {v['depth_rec_status_counts']} |")
cg = Q2["cohort_carry_gap_normal"]
P(f"- 队列 8 名在 {len(cg)} 个 NORMAL 锚上: 目标文件 carry {np.mean([x['C_file'] for x in cg]):+.4f}, 执行器持仓 carry {np.mean([x['C_held'] for x in cg]):+.4f}, 差 {np.mean([x['gap'] for x in cg]):+.4f}(单位 gross 口径 /S)。重建深度 vs 计数器: {Q2['depth_vs_counter']}; G-QTY: " + "; ".join(f"{k} 读回 {v['n_readbacks']} 失配 {v['n_mismatch_events']} 重同步 {v['n_resync']}" for k, v in Q2["G_QTY"].items()))
P(f"- W2 内(08-26 00:00Z ≤ ts < 08-31 04:00Z)全部 per_name_stop 触发(任何名): " + "; ".join(f"{e['utc']} {e['symbol']} {e['depth_pct']}%" for e in Q2["all_fire_events"] if 1787702400 <= e["ts"] < 1788134400 + 14400) + f"; notify_audit 全部 {len(Q2['all_fire_events'])} 次触发(08-20..09-12), 其中队列名 " + str(sum(1 for e in Q2["all_fire_events"] if e["symbol"] in Q2["answers"])) + " 次。")
P("")
P("### T5a ONGUSDT 逐锚(T5b_exec_rows.json)"); P("| 锚 | 执行器锚类 | tl_w | T_file | T_exec | H_pre | H_post | counter | 深度(重建) | entry | mid |"); P("|---|---|---|---|---|---|---|---|---|---|---|")
for e in ROWS["Q2rows"]:
    if e["symbol"] != "ONGUSDT": continue
    d = e["depth_rec"] or {}
    P(f"| {e['utc']} | {e['anchor_class']} | {f(e['tl_w'], 5)} | {f(e['T_file'], 1)} | {f(e['T_exec'], 1)} | {f(e['H_pre'], 1)} | {f(e['H_post'], 1)} | {e['pns_counter']} | {d.get('status')} {f(d.get('depth'), 3)} | {f(d.get('entry'), 5)} | {f(d.get('mark_mid'), 5)} |")
P("")
# T6 Q3
Q3 = EX["Q3"]; s3 = Q3["summary"]
P("## T6 Q3 执行器层 F_A 名(RECEIPT_T5b_exec.json Q3)")
P("- W1 执行器锚类: " + json.dumps(s3["classes_W1"], ensure_ascii=False) + "; 非 NORMAL: " + "; ".join(f"{k} {v}" for k, v in s3["class_by_anchor"].items() if v != "NORMAL"))
P("| 量 | 角色 | 锚数 | 均值 | CI95 | 累计 | 读法 |"); P("|---|---|---|---|---|---|---|")
for k, v in Q3["readings"].items(): P(f"| {k} | {v.get('role', '描述')} | {v['n_anchors']} | {f(v['mean'])} | [{f(v['ci95'][0])}, {f(v['ci95'][1])}] | {f(v['cumulative'], 3)} | {v.get('reading', '—')} |")
P(f"- (A, i∈F_A) 实例 {s3['n_instances']}; 执行器冻结 {s3['n_exec_frozen']}(其中生产者同时冻结 {s3['n_exec_frozen_and_prod_frozen']}); **执行器加冻 {s3['n_exec_added_freeze']}**, 原因 {s3['exec_added_freeze_causes']}, |H_post − T_file| 合计 USDT " + json.dumps({k: round(v, 1) for k, v in s3['exec_added_abs_gap_usdt_by_cause'].items()}) + f"; 连续段长度分布 {s3['exec_added_run_lengths']}; 生产者冻结而执行器仍交易 {s3['n_prod_frozen_not_exec_frozen_normal']}; NORMAL 实例 |H_post − T_file| 中位 {s3['held_vs_file_normal']['median_abs_Hpost_minus_Tfile_usdt']:.1f} USDT, 权重差均值 {s3['held_vs_file_normal']['mean_Hpost_over_S_minus_tfile']:+.2e}。")
P("| 锚 | 名 | 原因 | T_file | T_exec | H_pre | H_post | c4 bps |"); P("|---|---|---|---|---|---|---|---|")
for e in s3["examples_exec_added"]:
    c4 = next((x["c4"] for x in ROWS["Q3rows"] if x["utc"] == e["utc"] and x["symbol"] == e["symbol"]), None)
    P(f"| {e['utc']} | {e['symbol']} | {e['exec_added_freeze_cause']} | {f(e['T_file'], 1)} | {f(e['T_exec'], 1)} | {f(e['H_pre'], 1)} | {f(e['H_post'], 1)} | {f(c4 * 1e4 if c4 is not None else None, 2)} |")
nt = EX["no_trade_band"]; P(f"- no_trade_band: `state/live/no_trade_band.json` 最后写入 {nt['state_live']['rebalance_id']} = {nt['state_live_written_utc']}; `state/no_trade_band.json` {nt['state_root']['rebalance_id']} = {nt['state_root_written_utc']}; W1/W2 LIVE phase_A 中带 no_trade_band 键的锚 {len(nt['phase_A_records_with_no_trade_band_key_W1W2'])}。")
P("")
# T7 posthoc stop pinning
P("## T7 事后核查: 已停名在执行器 reshape + clamp 下的处置(RECEIPT_T5b_exec_posthoc.json; POST-HOC)")
inst = EXP["all_instances"]; side = lambda o: "long" if o["held_prev_readback"] > 0 else "short"
tab = collections.Counter((side(o), ",".join(o["recorded_buckets"]) or "UNLISTED") for o in inst)
P(f"- 已停且持仓的 (锚, 名) 实例 {EXP['n_stopped_held_instances']}; 记录桶已知 {EXP['n_recorded_bucket_known']}; 用统一平移 a 预测的桶与记录相符 {EXP['n_pred_matches_record']}/{EXP['n_recorded_bucket_known']}。")
P("| 方向 | 记录桶 | 实例数 |"); P("|---|---|---|")
for (sd, bk), n in sorted(tab.items()): P(f"| {sd} | {bk} | {n} |")
a_vals = [o["fitted_shift_a_usdt"] for o in inst]; pinned = [o for o in inst if "add_blocked" in o["recorded_buckets"]]
P(f"- 拟合平移 a 范围 [{min(a_vals):+.1f}, {max(a_vals):+.1f}] USDT(= reshape 去均值对每个名的统一平移; 当撤名残差 net_before < 0 时 a > 0)。add_blocked 已停多头持仓 {min(o['held_prev_readback'] for o in pinned):.1f}..{max(o['held_prev_readback'] for o in pinned):.1f} USDT。")
byname = collections.defaultdict(list)
for o in pinned: byname[o["symbol"]].append(o["utc"])
P("- 被钉住的已停名(首末锚, 锚数): " + "; ".join(f"{k} {v[0]}..{v[-1]} ({len(v)})" for k, v in sorted(byname.items(), key=lambda kv: kv[1][0])))
P("")
open(T5B + "/receipts/TABLES_T5b.md", "w").write("\n".join(L) + "\n")
print("DONE_t5b_tables lines", len(L))
