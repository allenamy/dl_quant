#!/usr/bin/env python3
"""c0_report.py — renders the summary tables quoted in docs/RESULT_c0_attribution_2026-09-19.md from the two JSON receipts
(C0_ATTRIB.json from c0_attrib.py ec8de310 = frozen §1; C0_SUPP.json from c0_supp.py = post-freeze market/selection split). Pure JSON →
Markdown, no computation beyond ratios and sums of receipt numbers; runs anywhere (local python3).
usage: python3 c0_report.py <receipts_dir> > C0_DOC_TABLES.md"""
import hashlib, json, sys
D = sys.argv[1]
A = json.load(open(f"{D}/C0_ATTRIB.json")); S = json.load(open(f"{D}/C0_SUPP.json"))
sh = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
f2 = lambda x: "—" if x is None else f"{x:+.2f}"
SK = ["A0_s42", "A0_s2027"]
out = [f"<!-- rendered by c0_report.py from C0_ATTRIB.json {sh(D + '/C0_ATTRIB.json')} + C0_SUPP.json {sh(D + '/C0_SUPP.json')} -->", ""]

def comp(sk, w):
    a = A["seeds"][sk]["windows"][w]; s = S["seeds"][sk]["windows"][w]
    sl, ss = s["sides"]["long"], s["sides"]["short"]
    return dict(N=a["N"], g=a["components"]["net"], price=a["components"]["price"], mkt=sl["market"] + ss["market"], sel=sl["selection"] + ss["selection"], selL=sl["selection"], selS=ss["selection"],
                car=a["components"]["carry"], carL=a["by_side"]["long"]["carry"], carS=a["by_side"]["short"]["carry"], fee=a["components"]["fee"], ybar=s["ybar_bps_per_4h"],
                rL=s["r_long_minus_ybar"], rS=s["r_short_minus_ybar"], net=s["net_exposure_over_gross"], pL=a["by_side"]["long"]["price"], pS=a["by_side"]["short"]["price"])

# T1 windows
out += ["### T1 窗口分解(两种子; bps / 锚 / 单位 gross)", "",
        "| 窗口 | 锚 | g | 价格 | = 市场 | + 选股 | 选股 多 / 空 (s2027) | 资金费 付出 (多 / 空) | 手续费 | 宇宙 ȳ bps/4h | 多头篮 − ȳ | 空头篮 − ȳ | 冻结表 多 / 空 价格 (s2027) |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
mxd = 0.0
for w in ["2025", "2026H1", "2026-04", "2026-06", "2026-07", "2026-08", "ALL"]:
    c = [comp(sk, w) for sk in SK]
    j = lambda k: " / ".join(f2(x[k]) for x in c)
    out.append(f"| {w} | {c[0]['N']} | {j('g')} | {j('price')} | {j('mkt')} | {j('sel')} | {f2(c[0]['selL'])} / {f2(c[0]['selS'])} ({f2(c[1]['selL'])} / {f2(c[1]['selS'])}) | "
               f"{f2(c[0]['car'])} ({f2(c[0]['carL'])} / {f2(c[0]['carS'])}) | {f2(c[0]['fee'])} | {f2(c[0]['ybar'])} | {j('rL')} | {j('rS')} | {f2(c[0]['pL'])} / {f2(c[0]['pS'])} ({f2(c[1]['pL'])} / {f2(c[1]['pS'])}) |")
    mxd = max(mxd, max(abs(c[0][k] - c[1][k]) for k in ("car", "carL", "carS", "fee", "ybar")))
out += ["", f"两种子的格写作「s42 / s2027」, 括号里是 s2027; 只写一个数的列(资金费、手续费、ȳ)是 s42 —— 这些列两种子在本表各窗的最大差实测为 {mxd:.3f}。「冻结表 多 / 空 价格」= §2 按方向拆的价格(含市场)。", ""]

# T2 monthly
out += ["### T2 逐月(s42 / s2027)", "", "| 月 | g | 选股 | 选股 多 | 选股 空 | 市场 | 资金费付出 | 宇宙 ȳ |", "|---|---|---|---|---|---|---|---|"]
for m in A["months"]:
    c = [comp(sk, m) for sk in SK]; j = lambda k: " / ".join(f2(x[k]) for x in c)
    out.append(f"| {m} | {j('g')} | {j('sel')} | {j('selL')} | {j('selS')} | {j('mkt')} | {j('car')} | {f2(c[0]['ybar'])} |")
out.append("")

# T3 cohorts H1 vs Jul vs Aug
out += ["### T3 逐格: 2026H1 → 2026-07 → 2026-08(净贡献 = 冻结 §1; 选股 = §3 追加拆分)", "",
        "格 = 方向:分组。数字为 s42 / s2027。gross = 该格占 gross_total 的平均份额(s42)。选股/gross = 该格自身资金相对宇宙的收益(bps / 锚)。全部格照列, 不择优(gross 在 H1 与 8 月都 < 0.001 的格略去, 其数字在 JSON)。", ""]
for cn in ["FSIG", "FUND", "AGE", "MOM7", "MOM30", "LIQ", "TBF"]:
    codes = A["seeds"]["A0_s42"]["windows"]["ALL"]["chars"][cn]["codes"]
    out += [f"**{cn}**", "", "| 格 | 净 H1 | 净 7 月 | 净 8 月 | 选股 H1 | 选股 7 月 | 选股 8 月 | 资金费 H1 → 8 月 (s42) | gross H1 → 8 月 | 选股/gross H1 → 8 月 (s42) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for sd in ("long", "short"):
        for i, c in enumerate(codes):
            gH = A["seeds"]["A0_s42"]["windows"]["2026H1"]["chars"][cn]["gross"][sd][i]; gA = A["seeds"]["A0_s42"]["windows"]["2026-08"]["chars"][cn]["gross"][sd][i]
            if max(gH, gA) < 1e-3: continue
            nv = lambda w: " / ".join(f2(A["seeds"][sk]["windows"][w]["chars"][cn]["net"][sd][i]) for sk in SK)
            sv = lambda w: " / ".join(f2(S["seeds"][sk]["windows"][w]["chars"][cn]["selection"][sd][i]) for sk in SK)
            cv = lambda w: A["seeds"]["A0_s42"]["windows"][w]["chars"][cn]["carry"][sd][i]
            sH = S["seeds"]["A0_s42"]["windows"]["2026H1"]["chars"][cn]["selection"][sd][i]; sA = S["seeds"]["A0_s42"]["windows"]["2026-08"]["chars"][cn]["selection"][sd][i]
            rg = lambda s_, g_: "—" if g_ < 0.002 else f"{s_ / g_:+.1f}"
            out.append(f"| {'多' if sd == 'long' else '空'}:{c} | {nv('2026H1')} | {nv('2026-07')} | {nv('2026-08')} | {sv('2026H1')} | {sv('2026-07')} | {sv('2026-08')} | {f2(cv('2026H1'))} → {f2(cv('2026-08'))} | {gH:.3f} → {gA:.3f} | {rg(sH, gH)} → {rg(sA, gA)} |")
    out.append("")

# T4 selection concentration
out += ["### T4 选股的名字集中度(逐名对月均的贡献; s42, 括号 s2027)", "", "| 月.方向 | 合计 | 最差 10 名 | 最好 10 名 | 其余(主体) | 名字数 <0 / >0 |", "|---|---|---|---|---|---|"]
for w in ["2026-04", "2026-06", "2026-07", "2026-08"]:
    for sd in ("long", "short"):
        c = [S["seeds"][sk]["windows"][w][f"{sd}_selection_per_name"] for sk in SK]
        out.append(f"| {w}.{'多' if sd == 'long' else '空'} | {f2(c[0]['total'])} ({f2(c[1]['total'])}) | {f2(c[0]['worst10'])} ({f2(c[1]['worst10'])}) | {f2(c[0]['best10'])} ({f2(c[1]['best10'])}) | "
                   f"{f2(c[0]['body_ex_worst10_best10'])} ({f2(c[1]['body_ex_worst10_best10'])}) | {c[0]['n_neg']} / {c[0]['n_pos']} |")
out.append("")
out += ["### T4b 冻结表的净集中度(§1 D3; s42 / s2027)", "", "| 月 | 净合计 | 最差 10 | 最好 10 | 去掉最差 10 名 | 净<0 名字的 gross 份额 | 有效名字数 | 净<0 的日数 | 最差 5 日 | 最好 5 日 |", "|---|---|---|---|---|---|---|---|---|---|"]
for w in ["2026-04", "2026-06", "2026-07", "2026-08"]:
    c = [A["seeds"][sk]["concentration"][w] for sk in SK]; d = [A["seeds"][sk]["days"][w] for sk in SK]
    j = lambda k, src=c: " / ".join(f2(x[k]) for x in src)
    out.append(f"| {w} | {j('total_net')} | {j('worst10_net_sum')} | {j('best10_net_sum')} | {j('leave_worst10_out_net')} | {c[0]['gross_share_in_net_neg_names']:.2f} / {c[1]['gross_share_in_net_neg_names']:.2f} | "
               f"{c[0]['effective_n_abs_net']:.0f} / {c[1]['effective_n_abs_net']:.0f} | {d[0]['n_days_net_neg']} / {d[1]['n_days_net_neg']} of {d[0]['n_days']} | {j('worst5_days_net_sum', d)} | {j('best5_days_net_sum', d)} |")
out.append("")

# T5 rally-week split
out += ["### T5 8 月按日: 事后切分 RALLY6(08-19 … 08-24)vs 其余 24 天(对 8 月均值的贡献; s42 / s2027)", ""]
for sk in SK:
    ap = S["seeds"][sk]["aug_split_posthoc"]
    dd = S["seeds"][sk]["days"]["2026-08"]
    agg = {p: {k: sum(v[k] for d_, v in dd.items() if (("2026-08-19" <= d_ <= "2026-08-24") == (p == "RALLY6"))) for k in ("market_long", "market_short", "selection_long", "selection_short", "carry", "fee", "net")} for p in ("RALLY6", "REST")}
    out += [f"**{sk}**: ȳ RALLY6 {f2(ap['RALLY6']['ybar_bps_per_4h'])} bps/4h ({ap['n_anchors']['RALLY6']} 锚) · 其余 {f2(ap['REST']['ybar_bps_per_4h'])} ({ap['n_anchors']['REST']} 锚)", "",
            "| 段 | 市场 多 | 市场 空 | 选股 多 | 选股 空 | 资金费付出 | 手续费 | 净 |", "|---|---|---|---|---|---|---|---|"]
    for p in ("RALLY6", "REST"):
        v = agg[p]; out.append(f"| {p} | {f2(v['market_long'])} | {f2(v['market_short'])} | {f2(v['selection_long'])} | {f2(v['selection_short'])} | {f2(v['carry'])} | {f2(v['fee'])} | {f2(v['net'])} |")
    out.append("")
out += ["全部格(8 月 gross ≥ 0.001 的格; 其余在 C0_SUPP.json)。选股, 对 8 月均值的贡献; RALLY6 + 其余 = §3 T3 的「选股 8 月」。", "",
        "| 格(选股) | RALLY6 s42 / s2027 | 其余 s42 / s2027 |", "|---|---|---|"]
for cn in ["FSIG", "FUND", "AGE", "MOM7", "MOM30", "LIQ", "TBF"]:
    codes = S["seeds"]["A0_s42"]["aug_split_posthoc"]["RALLY6"]["chars"][cn]["codes"]
    for sd in ("long", "short"):
        for i, cd in enumerate(codes):
            if A["seeds"]["A0_s42"]["windows"]["2026-08"]["chars"][cn]["gross"][sd][i] < 1e-3: continue
            vals = {p: " / ".join(f2(S["seeds"][sk]["aug_split_posthoc"][p]["chars"][cn][sd][i]) for sk in SK) for p in ("RALLY6", "REST")}
            out.append(f"| {cn} {'多' if sd == 'long' else '空'}:{cd} | {vals['RALLY6']} | {vals['REST']} |")
out.append("")
for sk in SK:
    ap = S["seeds"][sk]["aug_split_posthoc"]["RALLY6"]
    out.append(f"- {sk} RALLY6 多头选股最差 10 名 {f2(ap['long_worst10_sum'])}: " + ", ".join(f"{n.replace('USDT', '')} {v:+.2f}" for n, v in ap["long_worst10"]) + f"; 最好 10 名 {f2(ap['long_best10_sum'])}")
    out.append(f"- {sk} RALLY6 空头选股最差 10 名 {f2(ap['short_worst10_sum'])}: " + ", ".join(f"{n.replace('USDT', '')} {v:+.2f}" for n, v in ap["short_worst10"]) + f"; 最好 10 名 {f2(ap['short_best10_sum'])}")
out.append("")

# T6 top-20
for w in ["2026-08", "2026-07", "2026-06", "2026-04"]:
    lst = A["seeds"]["A0_s42"]["top20"][w]; l2 = {x["symbol"] for x in A["seeds"]["A0_s2027"]["top20"][w]}
    out += [f"### T6 {w} 按 |净| 前 20 名(s42; 与 s2027 前 20 重合 {len({x['symbol'] for x in lst} & l2)} / 20)", "",
            "| # | 名字 | 净 | 价格 | 资金费 | gross | 多头占比 | AGE 天 | RN8 bp | MOM30 | 众数分组 AGE/FUND/MOM7/MOM30/LIQ/TBF/FSIG |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r, x in enumerate(lst, 1):
        mc = x["median_chars"]; ml = x["modal_cohort"]
        fm = lambda k, s=1.0, fmt="{:.0f}": "—" if (mc[k] is None or mc[k] != mc[k]) else fmt.format(mc[k] * s)
        out.append(f"| {r} | {x['symbol'].replace('USDT', '')} | {f2(x['net'])} | {f2(x['price'])} | {f2(x['carry'])} | {x['gross']:.4f} | {'—' if x['long_share'] is None else format(x['long_share'], '.2f')} | "
                   f"{fm('AGE')} | {fm('RN8', 1e4, '{:.2f}')} | {fm('MOM30', 1.0, '{:+.2f}')} | " + "/".join(ml[c] for c in ["AGE", "FUND", "MOM7", "MOM30", "LIQ", "TBF", "FSIG"]) + " |")
    out.append("")

# T7 legs
out += ["### T7 腿的逐月收益(bps / 锚 / 单位**腿** gross; EMA 之前的目标腿; 两种子逐位相同, 因为腿与席位不依赖 F10 种子)", "",
        "| 月 | 席位 fund | fund 席位加权(rec `leg_fund`) | **fund 原始 = leg_fund / 席位(席位 > 0.05)[锚数]** | fund 原始重算(全部锚) | fund 席位输入(去均值 `legs_fund`) | 席位 king | king 原始 = leg_king / 席位 [锚数] | king 席位输入 |", "|---|---|---|---|---|---|---|---|---|"]

for w, v in A["seeds"]["A0_s42"]["legs"].items():
    v2 = A["seeds"]["A0_s2027"]["legs"][w]
    same = all((v[k] == v2[k]) for k in v)
    out.append(f"| {w}{'' if same else ' (s2027 不同!)'} | {v['w3_fund_mean']:.3f} | {f2(v['leg_fund_seatweighted_mean'])} | **{f2(v['fund_raw_by_division_mean'])}** [{v['fund_division_n_used']}] | {f2(v['fund_raw_recomputed_mean'])} | {f2(v['fund_seat_input_mean'])} | "
               f"{v['w3_king_mean']:.3f} | {f2(v['king_raw_by_division_mean'])} [{v['king_division_n_used']}] | {f2(v['king_seat_input_mean'])} |")
out.append("")
print("\n".join(out))
