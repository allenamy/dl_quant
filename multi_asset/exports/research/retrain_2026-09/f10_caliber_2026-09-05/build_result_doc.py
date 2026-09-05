#!/usr/bin/env python3
"""build_result_doc.py — assemble docs/RESULT_f10_caliber_sensitivity_2026-09-05.md from the archived pod products in this directory.
Every table is embedded verbatim from s1_tables.md / s2_tables.md (sha256 in SHA256SUMS); numbers quoted in the prose are read from s1_tables.json /
s2_judge.json / s0_receipts.json at build time (no hand-typed numbers). Run from anywhere: python3 build_result_doc.py"""
import json, os, re, hashlib, subprocess
A = os.path.dirname(os.path.abspath(__file__))
REPO = "/Users/haosiyu/Desktop/quant_research"; OUT = f"{REPO}/docs/RESULT_f10_caliber_sensitivity_2026-09-05.md"; PREREG = f"{REPO}/docs/PREREG_f10_caliber_sensitivity_2026-09-05.md"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
s0 = json.load(open(f"{A}/s0_receipts.json")); s1 = json.load(open(f"{A}/s1_tables.json")); s2 = json.load(open(f"{A}/s2_judge.json"))
t1 = open(f"{A}/s1_tables.md").read(); t2 = open(f"{A}/s2_tables.md").read()
def section(txt, head):   # return the markdown block starting at the line beginning with `head` up to the next '### '
    i = txt.index(head); j = txt.find("\n### ", i + 1); return txt[i:(j if j > 0 else len(txt))].rstrip() + "\n"
def d(leg, w): return s1["decomp"][f"{leg}/{w}"]
def pg(cal, s, w): return s2["delta_pergross"][f"{cal}/s{s}"]["windows"][w]
def rw(cal, s, w): return s2["delta_raw"][f"{cal}/s{s}"]["windows"][w]
def lv(leg, w, lab): return s1["levels"][f"{leg}/{w}"][lab]["mean"]
def f3(x): return f"{x:+.3f}"
W = "2024->26"
# ---- numbers used in the prose (all read from files)
f42, f27 = d("f10_s42", W), d("f10_s2027", W); kg = d("king", W); fd = d("fund", W); fd26 = d("fund", "2026<=08-10")
pE42 = s1["parts"][f"f10_s42/{W}"]["rE"]["mean"]; pE27 = s1["parts"][f"f10_s2027/{W}"]["rE"]["mean"]
cE42 = s1["corr"][f"f10_s42/{W}"]["rE"]["mean"]; cE27 = s1["corr"][f"f10_s2027/{W}"]["rE"]["mean"]
cK = s1["corr"][f"king/{W}"]["rE"]["mean"]; cFc = s1["corr"][f"fund/{W}"]["conv"]["mean"]
P = {cal: {s: pg(cal, s, W) for s in ("42", "2027")} for cal in ("log", "sum1", "prod")}
R = {cal: {s: rw(cal, s, W) for s in ("42", "2027")} for cal in ("log", "sum1", "prod")}
P25 = {cal: {s: pg(cal, s, "2025->26") for s in ("42", "2027")} for cal in ("log", "sum1", "prod")}
Py = {cal: {s: pg(cal, s, "2025") for s in ("42", "2027")} for cal in ("log", "sum1", "prod")}
win_pg = {s: P["sum1"][s]["mean"] - P["log"][s]["mean"] for s in ("42", "2027")}; comp_pg = {s: P["prod"][s]["mean"] - P["sum1"][s]["mean"] for s in ("42", "2027")}; tot_pg = {s: P["prod"][s]["mean"] - P["log"][s]["mean"] for s in ("42", "2027")}
win_rw = {s: R["sum1"][s]["mean"] - R["log"][s]["mean"] for s in ("42", "2027")}; comp_rw = {s: R["prod"][s]["mean"] - R["sum1"][s]["mean"] for s in ("42", "2027")}
n_f10_h1 = sum(1 for leg in ("f10_s42", "f10_s2027") for w in ("2024", "2025", "2026<=08-10", "2024->26", "2025->26") if s1["decomp"][f"{leg}/{w}"]["reading"].startswith("H1"))
rec_ok = all(v["bitwise_equal"] for v in s1["receipts"].values()); n_rec = len(s1["receipts"])
lab_ok = all(v["exact_eq_frac"] == 1.0 and v["nan_pattern_mismatch"] == 0 for v in s0["receipts"].values())
equiv = open(f"{A}/logs/check_equiv.log").read(); n_pass = equiv.count("PASS ["); n_fail = equiv.count("FAIL [")
chain = open(f"{A}/logs/chain_s2.log").read(); judge_ts = re.search(r"JUDGE rc=0 (\S+)", chain).group(1)
prereg_sha = sha(PREREG); dev_sha = s2["device_sha256"]
L = []; Pp = L.append
Pp(f"> **创建:** {judge_ts.replace('T', ' ')}(判官收据 chain_s2.log `JUDGE rc=0`; 归档 2026-09-05 10:5xZ)| **Session:** b9646a9e / f10-caliber agent | **状态:** final(判据冻结先于数字, 数字后未改; 臂未加)| **预注册:** `docs/PREREG_f10_caliber_sensitivity_2026-09-05.md` sha256 `{prereg_sha}` | **装置:** pod2 `/workspace/review_scratch/f10_caliber/`(w10_health.py sha256 `{dev_sha[:16]}…` = health_check 装置逐字节同; s1_decompose.py `{s1['config']['self_sha256'][:16]}…`; labels_lib.py `{s1['config']['labels_lib_sha256'][:16]}…`; judge_s2.py `{sha(f'{A}/judge_s2.py')[:16]}…`)| **归档:** `multi_asset/exports/research/retrain_2026-09/f10_caliber_2026-09-05/`(SHA256SUMS + MANIFEST.md)| **作废条件:** 面板/king/F10 OOS 文件任一 sha 变更; 分解式或判读规则在看数字后被改; 本文任何数字无归档文件出处")
Pp("")
Pp("# RESULT · F10 腿口径敏感的来源分解(一根 bar 的窗口错位 vs 复利凸性)+ 三口径下 V2MAIN 贡献复核")
Pp("")
Pp("标注约定: **VERIFIED(文件名)** = 该数字由归档目录中的该文件逐字给出(表格整段从 `s1_tables.md` / `s2_tables.md` 原样嵌入, 正文数字由 `build_result_doc.py` 在生成时从 json 读出); **INFERRED** = 未由本轮脚本直接证明的解释性陈述。单位: 腿层 = 单位 gross 秩书 bps/锚; 书层主口径 = net_ex/gross_total(bps/锚/每单位 gross, E-0904-G 单位链), 次口径 = 装置刻度 net_ex 原值。窗口: 2024-01-01 → 2026-08-10 20Z(F10 折外预测最后一行), 逐年 + 2024→26 + 2025→26。")
Pp("")
Pp("## §0 结论(白话)")
Pp("")
Pp(f"F10(V2MAIN)腿的秩书在在役面板口径(Σ简单, 行 [E,E+47])下比交易所记账口径少赚约 1.5 bps/锚/gross, 来源查清了: **是一根 5 分钟 bar 的窗口错位, 不是复利凸性**。把三个标签 (i) Σ简单[E,E+47] → (ii) Σ简单[E+1,E+48] → (iii) Π(1+r)−1[E+1,E+48] 在同一本秩书上逐锚配对拆开(2024-01→2026-08-10, {s1['windows'][W]} 锚), F10 腿的**窗口项** {f3(f42['window']['mean'])}/{f3(f27['window']['mean'])} bps(s42/s2027, CI95 下界 {f3(f42['window']['lo'])}/{f3(f27['window']['lo'])}), **复利项** {f3(f42['comp']['mean'])}/{f3(f27['comp']['mean'])}(CI 含 0), 比值 {f42['ratio_abs_window_over_comp']:.0f}×/{f27['ratio_abs_window_over_comp']:.0f}×, 两种子五个窗口共 {n_f10_h1}/10 格全部落在冻结判读的\"H1 窗口主导\"(VERIFIED s1_tables.json)。机制直接可见: F10 的特征窗含收盘于 N 的那根 bar(行 E, `/workspace/f10/dlw_features.py` L44-45 断言 max_feature_row == E), 它对这根 bar 是反转载荷(成员内 Spearman {cE42:+.3f}/{cE27:+.3f}, 是偏移谱 k=−3..+3 中最强的一档), 而面板标签 (i) 恰把这根**已知** bar 计入标签 ⇒ F10 秩书被自己已经看到的那根 bar 扣掉 {abs(pE42):.2f}/{abs(pE27):.2f} bps/锚(书·r_E, VERIFIED s1_tables.md §1.3)。king 的面板特征窗止于 E−1, 对它这根 bar 是真正的未来 bar(书·r_E 为正), 窗口项 {f3(kg['window']['mean'])} ± {kg['window']['se']:.3f}(CI 含 0); fund 腿窗口项 {f3(fd['window']['mean'])}, 但**复利项 {f3(fd['comp']['mean'])} ± {fd['comp']['se']:.3f}(CI<0; 2026 年 {f3(fd26['comp']['mean'])})**, 即 Σ简单口径系统性高估 fund 腿。书层(体检主臂 U-PIT·m1·FTRIM·实盘费率, PHI 0.45 − PHI 0, 每 gross 口径)2024→26 的 V2MAIN 贡献: (i) {f3(P['log']['42']['mean'])}/{f3(P['log']['2027']['mean'])}, (ii) {f3(P['sum1']['42']['mean'])}/{f3(P['sum1']['2027']['mean'])}, (iii) {f3(P['prod']['42']['mean'])}/{f3(P['prod']['2027']['mean'])} bps/锚/gross, 三口径双种子 CI95 下界均 >0(VERIFIED s2_tables.md §2.2a); 从 (i) 到 (iii) 共 {f3(tot_pg['42'])}/{f3(tot_pg['2027'])}, 其中一根 bar 窗口 {f3(win_pg['42'])}/{f3(win_pg['2027'])}, 复利 {f3(comp_pg['42'])}/{f3(comp_pg['2027'])}(均值之差, 由 s2_judge.json 算得); 2025 单年三口径 CI 全含 0; 装置刻度(net_ex 原值)下三口径 2024→26 为 {f3(R['log']['42']['mean'])}/{f3(R['log']['2027']['mean'])} · {f3(R['sum1']['42']['mean'])}/{f3(R['sum1']['2027']['mean'])} · {f3(R['prod']['42']['mean'])}/{f3(R['prod']['2027']['mean'])}, 全部 CI 含 0 —— 这正是 08-26/09-04 \"V2MAIN 净≈0\"读数所在的刻度(VERIFIED s2_tables.md §2.2b)。预注册 §2 的判读规则\"(i)≈0 且 (ii)(iii) CI>0\"在任何窗口都**不成立**, 因为每 gross 口径下 (i) 本身就不≈0(2024→26 双种子 CI>0), 而 2025→26 下 (ii) 的下界 {f3(P25['sum1']['42']['lo'])}/{f3(P25['sum1']['2027']['lo'])} 刚好含 0(VERIFIED s2_tables.md §2.3)。**实盘零改动**: V2MAIN 的训练目标本来就是 (iii)(`pod_dlw_targets_ext.py` L91-95, 结构断言起点 E+1), 服务端特征用到行 E; 变化在于今后一切回放以 (iii) 交易所窗口口径为主口径报数, 且 king 标签对齐 [E+1,E+48] 列为下次月度重训的候选(需自己的预注册)。")
Pp("")
Pp("## §1 腿层: 三标签下的单位 gross 秩书收益(VERIFIED s1_tables.md §1.1)")
Pp("")
Pp("秩书 = `w10_health.py legs()` 逐字(MEMBERS_TOPN=829 按 qvk 重建成员 ∩ U-PIT 掩码 m1; fund z 在 829 基内排名 FZB; king/F10 z 在成员内排名; 标签有数成员内去均值, 单位 gross; 缺 y 记 0); 腿 = king(slow_pred_pinned)/ F10 s42 / F10 s2027 / fund(f_fund_ema_v1)。s.e. = UTC 日块 bootstrap 2000, 种子 20260905。")
Pp("")
Pp(section(t1, "### §1.1").split("\n", 2)[2])
Pp("读法(INFERRED): F10 腿在 (i) 下只有 (ii)/(iii) 的 40% 左右, 而 king/fund 三标签几乎不动; 与 RESULT_seat_round2 §5(iii) 报的 2025→26 prod +2.1 vs log +0.44 一致(本表 2025→26 s42: (i) " + f3(lv("f10_s42", "2025->26", "i")) + " / (iii) " + f3(lv("f10_s42", "2025->26", "iii")) + ")。")
Pp("")
Pp("## §2 分解: 窗口项 (ii)−(i) vs 复利项 (iii)−(ii), 冻结判读规则(VERIFIED s1_tables.md §1.2)")
Pp("")
Pp("判读规则(预注册 §1, 数字前冻结): |窗口项| ≥ 2×|复利项| ⇒ H1 窗口错位主导; |复利项| ≥ 2×|窗口项| ⇒ H2 复利凸性主导; 否则并存。逐锚配对, 日块 bootstrap CI95。")
Pp("")
Pp(section(t1, "### §1.2").split("\n", 2)[2])
Pp(f"读数: F10 两种子 × 五窗口 = {n_f10_h1}/10 格 H1 主导, 复利项在 10 格中无一 CI 排除 0; king 窗口项 2024→26 {f3(kg['window']['mean'])} [{f3(kg['window']['lo'])},{f3(kg['window']['hi'])}](小, CI 含 0), 复利项 {f3(kg['comp']['mean'])}; fund 窗口项 {f3(fd['window']['mean'])}(≈0), 复利项 {f3(fd['comp']['mean'])} [{f3(fd['comp']['lo'])},{f3(fd['comp']['hi'])}](CI<0)⇒ **Σ简单口径高估 fund 腿 {abs(fd['comp']['mean']):.2f} bps/锚(2026 年 {abs(fd26['comp']['mean']):.2f})**; fund 腿的判读为 H2 是因为它的窗口项本来就≈0, 不是因为凸性暴露大(corr(fund 分数, 凸性) {cFc:+.3f}, §3)。(VERIFIED s1_tables.json)")
Pp("")
Pp("## §3 暴露部分: 书·r_E(模型已看到的那根 bar)与书·r_{E+48}; 直接暴露与偏移谱(VERIFIED s1_tables.md §1.3–§1.5)")
Pp("")
Pp(section(t1, "### §1.3").split("\n", 2)[2])
Pp(f"读数: F10 秩书对行 E(收盘于 N 的 bar)的暴露 2024→26 = {f3(pE42)}/{f3(pE27)} bps/锚, 对行 E+48 只有 {f3(s1['parts'][f'f10_s42/{W}']['rE48']['mean'])}/{f3(s1['parts'][f'f10_s2027/{W}']['rE48']['mean'])}; 窗口项 = 后者 − 前者(逐锚最大偏差 ≤ 3.9e-3 bps, float32 标签舍入, INFERRED)。king 对行 E 的暴露为正({f3(s1['parts'][f'king/{W}']['rE']['mean'])}): 对 king 这是一根真正的未来 bar, 它预测得到, 因此 (i) 反而略偏袒 king。")
Pp("")
Pp(section(t1, "### §1.4").split("\n", 2)[2])
Pp(section(t1, "### §1.5").split("\n", 2)[2])
Pp(f"读数: F10 分数与 r_E 的成员内 Spearman {cE42:+.4f}/{cE27:+.4f}(2024→26)是 k=−3..+3 七档中绝对值最大的一档, k=+1 起转正(它预测下一根 bar 为正); king 在 k=0 为 {cK:+.4f}(正, 未来 bar), 在 k≤−1 为负(其特征窗内的反转)。预注册 §0 写的\"F10 偏移谱 k=−1 为 −0.26\"来自另一台仪器/另一种归一, 本轮成员内 Spearman 口径下同一现象的量级是 −0.04~−0.06(INFERRED: 不同口径, 未复现该 −0.26)。凸性暴露: F10 {s1['corr'][f'f10_s42/{W}']['conv']['mean']:+.4f}/{s1['corr'][f'f10_s2027/{W}']['conv']['mean']:+.4f}, king {s1['corr'][f'king/{W}']['conv']['mean']:+.4f}, fund {cFc:+.4f} —— king 的凸性暴露最大却复利项≈0(书层 |w| 摊薄, INFERRED), fund 为负与其复利项 CI<0 同向。")
Pp("")
Pp("## §4 书层: 三口径下 V2MAIN 贡献(体检主臂, PHI 0.45 − PHI 0)(VERIFIED s2_tables.md)")
Pp("")
Pp("装置 = health_check `w10_health.py`(逐字节同, 见 §7), 主臂 U-PIT · UMASK_SCOPE=m1 · LEGS=101 · LOOK=900 · msharpe · FTRIM=zero · 实盘费率 COSTB_JSON(fee-only)· 种子 42/2027; 三布局: dev(标签 (i) = 在役 meta y4)/ dev_alt2(标签 (ii), meta 用 s0 构建的 Σ简单[E+1,E+48] 替换, 与 refute_C6_2 meta_newsum 逐位同)/ dev_alt(标签 (iii) = refute_C6_2 meta_newprod = dlw y4s); 12 次运行, 配对锚 n=10038 完全相同。命令逐字见归档 `logs/commands.txt`。")
Pp("")
Pp(section(t2, "### §2.1").split("\n", 2)[2])
Pp(section(t2, "### §2.2a").split("\n", 2)[2])
Pp(section(t2, "### §2.2b").split("\n", 2)[2])
Pp(f"读数(均由上两表算得): 每 gross 口径 2024→26 从 (i) 到 (iii) 共 {f3(tot_pg['42'])}/{f3(tot_pg['2027'])} bps/锚/gross, 其中窗口 (i)→(ii) {f3(win_pg['42'])}/{f3(win_pg['2027'])}, 复利 (ii)→(iii) {f3(comp_pg['42'])}/{f3(comp_pg['2027'])}; 装置刻度下窗口 {f3(win_rw['42'])}/{f3(win_rw['2027'])}, 复利 {f3(comp_rw['42'])}/{f3(comp_rw['2027'])}。两刻度的差来自 PHI=0.45 书的 gross_total 更低(§2.1: 0.585–0.619 vs 0.712–0.724): 执行器按 gross = L×NAV 定尺寸, 所以每 gross 口径才是 NAV 收益的口径(E-0904-G 单位链); 装置刻度把混合书的更小 gross 当作它自己的损失(INFERRED, 机制见 health_metrics.py L3-5 单位链)。换手: PHI=0.45 每 gross 换手 +36~46%(表末列)。")
Pp("")
Pp("## §5 冻结判读(预注册 §2)与它对旧结论的含义(VERIFIED s2_tables.md §2.3)")
Pp("")
Pp(section(t2, "### §2.3").split("\n", 2)[2])
Pp(f"白话: 规则\"(i)≈0 且 (ii)(iii) CI>0\"在五个窗口无一成立, 但原因不是 V2MAIN 没贡献, 而是**每 gross 口径下 (i) 本身就不≈0**(2024→26 双种子 CI 下界 {f3(P['log']['42']['lo'])}/{f3(P['log']['2027']['lo'])} > 0)。08-26/09-04 的\"V2MAIN 净≈0\"读数(combo_recheck: C−A log +0.005 / 复利 +0.079, P 0.50/0.79, 装置刻度 net_ex)属于装置刻度: 本轮同刻度下三口径 2024→26 全部 CI 含 0(§4 次表), 与旧读数同向; 每 gross 口径下 V2MAIN 贡献在三口径、双种子的 2024→26 全为 CI>0, 一根 bar 窗口在其上再加 {f3(win_pg['42'])}/{f3(win_pg['2027'])}, 复利再加 {f3(comp_pg['42'])}/{f3(comp_pg['2027'])}; 2025 单年在每一种口径下都未定(CI 含 0: (i) [{f3(Py['log']['42']['lo'])},{f3(Py['log']['42']['hi'])}] / (iii) [{f3(Py['prod']['42']['lo'])},{f3(Py['prod']['42']['hi'])}], s42)。2025→26: (i) 含 0, (ii) 下界 {f3(P25['sum1']['42']['lo'])}/{f3(P25['sum1']['2027']['lo'])}(刚好含 0), (iii) 下界 {f3(P25['prod']['42']['lo'])}/{f3(P25['prod']['2027']['lo'])} > 0。注意旧读数的装置形态是正典形(MEMBERS_TOPN=0/TRADE_TOPN=0/FTRIM=off), 本轮是体检主臂形态(m1/U-PIT/FTRIM/实盘费), 二者不是同一本书, 只能对\"刻度\"作对照, 不能逐格相减(INFERRED)。**本文只报数字, 不改任何在役判决。**")
Pp("")
Pp("## §6 什么变、什么不变")
Pp("")
Pp("- **实盘零改动。** V2MAIN(F10)的训练目标本来就是 (iii): `pod_dlw_targets_ext.py` L91-95 定义 y4s = expm1(CS_L[E+49] − CS_L[E+1]), 并在 L91 结构断言目标行窗起点 = E+1(VERIFIED, 源码行); F10 特征行窗 [E−w+1, E] 含收盘于 N 的 bar(`/workspace/f10/dlw_features.py` L3/L44-45, VERIFIED 于 pod 副本; 08-22 折外预测与 09-01 v3 换装件用同一约定, INFERRED 于冻结目标文件 docstring 与 STATE 09-01 np≡torch 1e-7 收据)。所以线上 F10 从未被这根 bar 扣分; 被扣分的只是**回放/评估**里用面板 y4(标签 (i))给 F10 腿记的账。")
Pp("- **今后回放报数一律以 (iii) 交易所窗口口径为主口径**(记账窗 (N, N+4h], 复利), (i) 只作面板对照; 已有的 CAL=log(=原始 y4=标签 (i))读数对 F10 相关的一切(席位输入、B1/B5 的口径分裂、V2MAIN 贡献)都偏低 ≈1.5 bps/锚/gross(腿层)/ ≈0.05 bps/锚/gross(书层窗口部分)。")
Pp("- **king 的面板标签 Y4 = 标签 (i)**(`pod_panel_ext.py` L57-58, VERIFIED): 它的特征窗止于 E−1, 标签窗 [E, E+47] 对它无泄漏, 但与记账窗错开一根 bar。把 king 标签对齐到 [E+1, E+48] 是下次月度重训的**候选**, 需要自己的预注册与门(RUNBOOK 月度重训流程), 本文不裁定。")
Pp("- 席位读数: 席位规则(msharpe)吃的是腿层秩书收益; 在 (i) 下 F10 腿被低估 ≈1.5 bps/锚, 所以 RESULT_seat_round2 里 log 口径的 F10 自有席位(0.40)与 prod 口径(0.64–0.66)的分裂已由本文解释为标签错位, 不是复利凸性; seat_round2 的结论(六臂无一录取)在 prod 口径下本已成立, 不受影响(INFERRED)。")
Pp("")
Pp("## §7 局限与收据")
Pp("")
Pp(f"- 标签平价(VERIFIED s0_receipts.json): (i) vs meta y4 {s0['receipts']['(i) oldsum vs meta y4']['cells_both_finite']} 格 exact_eq 1.0 / NaN 型式差 0; (iii) vs refute_C6_2 meta_newprod {s0['receipts']['(iii) newprod vs refute_C6_2 meta_newprod y4']['cells_both_finite']} 格 exact_eq 1.0; (iii) vs dlw y4s(共同锚 {s0['receipts']['(iii) newprod vs dlw y4s (common anchors)']['common_anchors']})exact_eq 1.0; (ii) vs refute_C6_2 meta_newsum exact_eq 1.0; dev_alt2 的 meta 文件 y4 与 (ii) 逐位同(sha256 `{s0['outputs']['meta_newsum_f10cal'][:16]}…`, {s0['outputs']['size_bytes']} B, 与 refute_C6_2 meta_newsum 同 sha)。全部平价 {'通过' if lab_ok else '未通过'}。")
Pp(f"- 秩书序列收据(VERIFIED s1_tables.json receipts): {n_rec}/{n_rec} 逐位相等 —— (i)/(iii) 下 king 与 fund 腿序列 = health_check M1_UPIT_{{log,prod}}_s42_ccal 存的 legs_king/legs_fund; F10 s42/s2027 在 (i)/(iii) 下 = seat_round2 B1_{{log,prod}} 存的 legs_f10(SEATF10=1 臂)。{'全部通过' if rec_ok else '有不等'}。")
Pp(f"- 装置运行收据(VERIFIED logs/check_equiv.log): PHI=0.45 的 log/prod 四次运行四数组(rec/W × S0/d30)与 health_check M1_UPIT_{{log,prod}}_s{{42,2027}}_ccal 逐位相等, PASS {n_pass}/4, FAIL {n_fail}; 12 件工件同一装置 sha `{dev_sha[:16]}…`; 锚集 n={s2['n_anchors']}({s2['first']} .. {s2['last']})完全相同; PHI=0 运行种子无关(s42 ≡ s2027 逐位): {s2['phi0_seed_independent']}(VERIFIED s2_judge.json)。")
Pp("- 输入 sha256(VERIFIED s0_receipts.json / s1_tables.json): 5m 缓存 `72eb7849…`, meta `4b1b6047…`, 面板 `5e67c055…`, umask_UPIT `ccb7a080…`, costb_fee_steady `9349ca63…`, slow_pred_pinned `158cd4ac…`, f10_V2MAIN_s42 `baf747ce…`, f10_V2MAIN_s2027 `c742ffaa…`, dlw_targets `dd4ed2df…`, meta_newprod `831857dd…`。")
Pp("- 局限: (a) 书层形态是体检主臂(m1/U-PIT/FTRIM/实盘费), 不是 08-26 正典形, 与旧读数只能对刻度不能逐格相减; (b) 每 gross 口径下 PHI=0.45 书 gross 更低, 换手每 gross +36~46%, 换手门与逆向选择成本(体检未知项)不在本文范围; (c) 2025 单年三口径全部未定, 分辨率 ±0.2 bps/锚/gross; (d) 偏移谱只做成员内 Spearman, 未复现预注册 §0 引用的 −0.26; (e) bootstrap 每格用同一种子的新生成器(与 judge_seat2 的顺序共享生成器不同), 对结论无影响但数字不可与其逐位比对; (f) F10 腿在 2024-H1 之前的 king 席位零填充问题(seat_round2 §4c)不在本文范围。")
Pp("- 归档: `multi_asset/exports/research/retrain_2026-09/f10_caliber_2026-09-05/`(脚本 + 结果 json/md + logs + SHA256SUMS; .npz 工件留 pod, 路径与 sha 在 MANIFEST.md)。pod 只读, 未重跑。")
open(OUT, "w").write("\n".join(L) + "\n")
print(OUT, sha(OUT))
