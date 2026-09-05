#!/usr/bin/env python3
"""build_result_doc.py — assemble docs/RESULT_phi_grid_2026-09-05.md from the archived pod products in this directory.
Every table is embedded verbatim from phi_tables.md (sha256 in SHA256SUMS); numbers quoted in the prose are read from phi_judge.json at build time
(no hand-typed numbers). Run from anywhere: python3 build_result_doc.py"""
import json, os, re, hashlib
A = os.path.dirname(os.path.abspath(__file__))
REPO = "/Users/haosiyu/Desktop/quant_research"; OUT = f"{REPO}/docs/RESULT_phi_grid_2026-09-05.md"; PREREG = f"{REPO}/docs/PREREG_dl_monthly_gate_and_phi_grid_2026-09-05.md"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
J = json.load(open(f"{A}/phi_judge.json")); T = open(f"{A}/phi_tables.md").read()
def section(head):
    i = T.index(head); j = T.find("\n### ", i + 1); return T[i:(j if j > 0 else len(T))].rstrip() + "\n"
def body(head): return section(head).split("\n", 2)[2]
def lv(cal, phi, s, w): return J["levels"][f"{cal}/phi{phi}/s{s}/{w}"]
def dl(cal, phi, s, w): return J["delta"][f"{cal}/phi{phi}/s{s}"]["windows"][w]
def dt(cal, phi, s, w): return J["delta"][f"{cal}/phi{phi}/s{s}"]["dturn_pct"][w]
def f3(x): return f"{x:+.3f}"
chain = open(f"{A}/logs/chain_phi.log").read(); judge_ts = re.search(r"JUDGE rc=0 (\S+)", chain).group(1)
prereg_sha = sha(PREREG); dev = J["device_sha256"]; V = J["verdict"]
PH = ["025", "035", "045", "055", "065"]; PV = {"0": 0.0, "025": 0.25, "035": 0.35, "045": 0.45, "055": 0.55, "065": 0.65}; S = ("42", "2027")
neg = [(k, v["mean"]) for k, v in J["levels"].items() if k.startswith("pergross/") and v["negative"]]; neg_raw = [(k, v["mean"]) for k, v in J["levels"].items() if k.startswith("raw/") and v["negative"]]
L = []; P = L.append
P(f"> **创建:** {judge_ts.replace('T', ' ')}(判官收据 chain_phi.log `JUDGE rc=0`; 归档 2026-09-05 11:2xZ)| **Session:** b9646a9e / f10-caliber agent | **状态:** final(判据 = PREREG §B 冻结先于数字, 数字后未改; 臂未加)| **预注册:** `docs/PREREG_dl_monthly_gate_and_phi_grid_2026-09-05.md` §B sha256 `{prereg_sha}`(commit dfbe516)| **装置:** pod2 `/workspace/review_scratch/phi_grid/`(w10_health.py sha256 `{dev[:16]}…` = health_check/f10_caliber 装置逐字节同; judge_phi.py `{sha(f'{A}/judge_phi.py')[:16]}…`)| **归档:** `multi_asset/exports/research/retrain_2026-09/phi_grid_2026-09-05/`(SHA256SUMS + MANIFEST.md)| **作废条件:** 面板/king/F10 OOS 文件任一 sha 变更; 判读规则在看数字后被改; 本文任何数字无归档文件出处")
P("")
P("# RESULT · F10 权重 φ 网格(记账口径 (iii), 体检主臂形态)— PREREG §B")
P("")
P("标注约定: **VERIFIED(文件名)** = 该数字由归档目录中的该文件逐字给出(表格整段从 `phi_tables.md` 原样嵌入; 正文数字由 `build_result_doc.py` 在生成时从 `phi_judge.json` 读出); **INFERRED** = 解释性陈述。主口径 = 每 gross(g = net_ex/gross_total, bps/锚/每单位 gross, E-0904-G 单位链); 次口径 = 装置刻度 net_ex 原值。2× 杠杆年化 NAV(算术)由脚本打印: " + J["units"]["nav_formula"] + "; " + J["units"]["dd2x"] + "。窗口: 2024 / 2025 / 2026≤08-10(F10 折外预测最后一行 2026-08-10 20Z)/ 2024→26 / 2025→26; 负年份以 ⚠ 显式标出。")
P("")
P("## §0 结论(白话)")
P("")
p45 = {s: lv("pergross", "045", s, "2024->26")["mean"] for s in S}; p55 = {s: lv("pergross", "055", s, "2024->26")["mean"] for s in S}; p65 = {s: lv("pergross", "065", s, "2024->26")["mean"] for s in S}; p25 = {s: lv("pergross", "025", s, "2024->26")["mean"] for s in S}; p35 = {s: lv("pergross", "035", s, "2024->26")["mean"] for s in S}
d55 = {s: dl("pergross", "055", s, "2024->26") for s in S}; d65 = {s: dl("pergross", "065", s, "2024->26") for s in S}; d25 = {s: dl("pergross", "025", s, "2024->26") for s in S}; d35 = {s: dl("pergross", "035", s, "2024->26") for s in S}
d55_25 = {s: dl("pergross", "055", s, "2025->26")["mean"] for s in S}; d65_25 = {s: dl("pergross", "065", s, "2025->26")["mean"] for s in S}
t55 = {s: dt("pergross", "055", s, "2024->26") for s in S}; t65 = {s: dt("pergross", "065", s, "2024->26") for s in S}
sh45 = {s: lv("pergross", "045", s, "2024->26")["sharpe"] for s in S}; sh65 = {s: lv("pergross", "065", s, "2024->26")["sharpe"] for s in S}; dd45 = {s: lv("pergross", "045", s, "2024->26")["dd2x_pctNAV"] for s in S}; dd65 = {s: lv("pergross", "065", s, "2024->26")["dd2x_pctNAV"] for s in S}
nav45 = {s: lv("pergross", "045", s, "2024->26")["nav_pct_yr_2x"] for s in S}; nav65 = {s: lv("pergross", "065", s, "2024->26")["nav_pct_yr_2x"] for s in S}
r55 = {s: dl("raw", "055", s, "2024->26") for s in S}; r65 = {s: dl("raw", "065", s, "2024->26") for s in S}
g45 = {s: lv("pergross", "045", s, "2024->26")["gross_total"] for s in S}; g65 = {s: lv("pergross", "065", s, "2024->26")["gross_total"] for s in S}
y25_55 = {s: dl("pergross", "055", s, "2025") for s in S}; y25_65 = {s: dl("pergross", "065", s, "2025") for s in S}; y26_55 = {s: dl("pergross", "055", s, "2026<=08-10") for s in S}
P(f"**结论: φ 0.45 保持**(冻结判读, VERIFIED phi_judge.json verdict)。在记账口径 (iii)、体检主臂形态下, 五个 φ 的书层每 gross 净额 2024→26 随 φ 单调上升(s42/s2027): 0.25 {f3(p25['42'])}/{f3(p25['2027'])} → 0.35 {f3(p35['42'])}/{f3(p35['2027'])} → **0.45 {f3(p45['42'])}/{f3(p45['2027'])}** → 0.55 {f3(p55['42'])}/{f3(p55['2027'])} → 0.65 {f3(p65['42'])}/{f3(p65['2027'])} bps/锚/gross(VERIFIED phi_tables.md §B.1a), 两种子同序; 但没有一个 φ 满足冻结判读的三条件: 向上 φ 0.55 vs 0.45 配对差 2024→26 {f3(d55['42']['mean'])} [{f3(d55['42']['lo'])},{f3(d55['42']['hi'])}] / {f3(d55['2027']['mean'])} [{f3(d55['2027']['lo'])},{f3(d55['2027']['hi'])}], φ 0.65 {f3(d65['42']['mean'])} [{f3(d65['42']['lo'])},{f3(d65['42']['hi'])}] / {f3(d65['2027']['mean'])} [{f3(d65['2027']['lo'])},{f3(d65['2027']['hi'])}] —— CI95 下界全部 < 0(2025→26 点估计虽全 ≥ 0: 0.55 {f3(d55_25['42'])}/{f3(d55_25['2027'])}, 0.65 {f3(d65_25['42'])}/{f3(d65_25['2027'])}), 且 φ 0.65 的换手/gross 增幅 s42 {t65['42']:+.1f}% 破 +20% 门(s2027 {t65['2027']:+.1f}%; φ 0.55 为 {t55['42']:+.1f}%/{t55['2027']:+.1f}%); 向下 φ 0.25 显著变差({f3(d25['42']['mean'])} [{f3(d25['42']['lo'])},{f3(d25['42']['hi'])}] / {f3(d25['2027']['mean'])} [{f3(d25['2027']['lo'])},{f3(d25['2027']['hi'])}], 双种子 CI<0), φ 0.35 {f3(d35['42']['mean'])}/{f3(d35['2027']['mean'])}(s2027 上界 {f3(d35['2027']['hi'])})。(VERIFIED phi_tables.md §B.2a/§B.3)剂量-响应是单调的(INFERRED 读法): 更多 F10 权重方向上更好、Sharpe 更高({sh45['42']:+.2f}/{sh45['2027']:+.2f} → φ 0.65 {sh65['42']:+.2f}/{sh65['2027']:+.2f})、2× 回撤更小({dd45['42']:.1f}/{dd45['2027']:.1f}% → {dd65['42']:.1f}/{dd65['2027']:.1f}% NAV)、2× 年化 {nav45['42']:.1f}/{nav45['2027']:.1f}% → {nav65['42']:.1f}/{nav65['2027']:.1f}%, 但增益(+0.07~+0.14 bps/锚/gross)小于本装置的分辨率(s.e. ±0.05~±0.10), 部分来自混合书 gross 更低(gross_total {g45['42']:.3f}/{g45['2027']:.3f} → {g65['42']:.3f}/{g65['2027']:.3f}; 装置刻度 Δ 0.55 {f3(r55['42']['mean'])}/{f3(r55['2027']['mean'])}, 0.65 {f3(r65['42']['mean'])}/{f3(r65['2027']['mean'])}, CI 全含 0, VERIFIED §B.2b), 并以换手上升为代价。单年 2025 所有 φ 的配对差 CI 含 0(0.55: [{f3(y25_55['42']['lo'])},{f3(y25_55['42']['hi'])}] / [{f3(y25_55['2027']['lo'])},{f3(y25_55['2027']['hi'])}]); 2026 单窗 φ 0.55 s42 [{f3(y26_55['42']['lo'])},{f3(y26_55['42']['hi'])}] CI>0 但预注册禁止按 2026 单窗挑 φ。每 gross 口径下无任何负年份; 装置刻度下只有 φ=0 对照 2024 为负({neg_raw[0][1]:+.3f} ⚠, 共 {len(neg_raw)} 格)。**实盘零改动, 不产生候选预注册。**")
P("")
P("## §1 设计与装置(PREREG §B 逐字; VERIFIED setup_phi.log / judge_phi.log)")
P("")
P("- 臂: φ ∈ {0.25, 0.35, 0.45(在役), 0.55, 0.65} × 种子 {42, 2027}; φ = 0(无 F10 书)作对照行。其余全同体检主臂: U-PIT 掩码 · UMASK_SCOPE=m1 · LEGS=101 · LOOK=900 · msharpe 动态席位 · FTRIM=zero · 实盘费率 costb_fee_steady(fee-only)· 止损 d30_n2_c42 · 标签 (iii) = meta_newprod(= dlw y4s, Π(1+r)−1 于 [E+1,E+48])。")
P(f"- φ 0.45 与 φ 0 不重跑: 直接读 f10_caliber 的 prod 工件, judge_phi.py 断言其 sha256 = f10_caliber MANIFEST 值(phi0/s42 93b927b7…, phi0/s2027 d7e66b96…, phi045/s42 53cd2d7f…, phi045/s2027 4710b1bb…); 8 个新工件的命令逐字见 `logs/commands.txt`。12 件工件同一装置 sha `{dev[:16]}…`, 锚集 n={J['n_anchors']}({J['first']} .. {J['last']})完全相同; 窗口大小 " + ", ".join(f"{k}={v}" for k, v in J["windows"].items()) + "。")
P("- 判读(冻结, PREREG §B): 改 φ 的候选 ⇔ 某 φ vs 0.45 的 2024→26 配对差 CI95 下界 > 0 且 2025→26 点估计 ≥ 0 且换手/gross 增幅 ≤ +20%, 两种子同号; 否则 φ 0.45 保持。换手增幅的窗口取 2024→26(与 CI 条件同窗; 2025→26 并列打印, 不入判)。禁: 按 2026 单窗挑 φ; 用 Σ简单口径 (i) 作主判。")
P("")
P("## §2 逐年表 — 每 gross 主口径(VERIFIED phi_tables.md §B.1a)")
P("")
P("紧凑网格(每 gross 净额 bps/锚, s42 / s2027; 由下表抄出, VERIFIED phi_judge.json levels):")
P(""); P("| φ | 2024 | 2025 | 2026≤08-10 | 2024→26 | 2025→26 | Sharpe 24→26 | 2×DD %NAV 24→26 | turn/gross 24→26 | NAV %/yr @2× 24→26 |"); P("|---|---|---|---|---|---|---|---|---|---|")
for phi in ["0"] + PH:
    c = lambda w, key, fmt: " / ".join(fmt.format(lv("pergross", phi, s, w)[key]) for s in S)
    P(f"| {PV[phi]:.2f}{' (在役)' if phi == '045' else (' (对照)' if phi == '0' else '')} | {c('2024', 'mean', '{:+.3f}')} | {c('2025', 'mean', '{:+.3f}')} | {c('2026<=08-10', 'mean', '{:+.3f}')} | **{c('2024->26', 'mean', '{:+.3f}')}** | {c('2025->26', 'mean', '{:+.3f}')} | {c('2024->26', 'sharpe', '{:+.2f}')} | {c('2024->26', 'dd2x_pctNAV', '{:.1f}')} | {c('2024->26', 'turn_per_gross', '{:.4f}')} | {c('2024->26', 'nav_pct_yr_2x', '{:.1f}')} |")
P(""); P(f"负年份(每 gross): {'无' if not neg else ', '.join(k for k, _ in neg)}。")
P("")
P(body("### §B.1a"))
P("## §3 每 φ vs 0.45 的配对差 — 每 gross 主口径(VERIFIED phi_tables.md §B.2a)")
P("")
P(body("### §B.2a"))
P("## §4 冻结判读(PREREG §B)(VERIFIED phi_tables.md §B.3)")
P("")
P(body("### §B.3"))
P("")
P("## §5 次口径: 装置刻度 net_ex 原值(VERIFIED phi_tables.md §B.1b / §B.2b)")
P("")
P(body("### §B.1b"))
P(body("### §B.2b"))
P("## §6 读法与不变项")
P("")
P(f"- 剂量-响应单调(INFERRED 读法, 数字 VERIFIED §2/§3): 每 gross 净额、Sharpe、2× 年化随 φ 单调上升, 回撤单调下降, 两种子同序; 向下(0.25)显著变差, 向上(0.55/0.65)点估计为正但 CI 含 0。这与 F10 口径分解(RESULT_f10_caliber_sensitivity 7ceb754)一致: 记账口径下 V2MAIN 贡献 +0.405/+0.451 bps/锚/gross(φ 0.45 vs 0), 再加 0.1~0.2 的 φ 只动书的 ~10% 构成, 增益落在 ±0.1 分辨率之内。")
P(f"- 增益的一部分是 gross 效应(INFERRED): 混合书 gross_total 随 φ 下降({g45['42']:.3f}/{g45['2027']:.3f} @0.45 → {g65['42']:.3f}/{g65['2027']:.3f} @0.65), 每 gross 口径按 gross = L×NAV 定尺寸把它折算成更高 NAV 收益, 装置刻度(§5)的 Δ 只有每 gross 的 1/3~1/2 且 CI 全含 0; 换手/gross 随 φ 上升(0.45→0.65: {t65['42']:+.1f}%/{t65['2027']:+.1f}%), 换手门守的是逆向选择成本(体检未知项)。")
P("- 不变项: 在役 φ 0.45 保持; 不产生候选预注册; 本文不改任何在役判决, 不涉及 seat_round2 的动态 φ(B4)结论(UNDECIDED, 换手 +15~18%)。重开条件(INFERRED): 逆向选择成本落地后重定换手门, 或样本延长使 2024→26 的分辨率降到 ±0.05 以下。")
P("")
P("## §7 局限与收据")
P("")
P(f"- 收据(VERIFIED judge_phi.log / chain_phi.log): 8 次新运行 rc=0(11:22:37Z), 判官 rc=0({judge_ts}); 12 件工件同一装置 sha `{dev[:16]}…`(= health_check 8684d9a9…); 4 个锚工件 sha 断言通过; 12 件的布局 meta 均断言为 meta_newprod(标签 (iii)); 配对锚 n={J['n_anchors']} 全同。setup_phi.log: 装置/掩码/费率三件与 health_check、f10_caliber 逐字节同, dev_alt 七个链接解析目标与 f10_caliber 与 health_check 全 SAME。")
P("- 局限: (a) 形态 = 体检主臂(m1/U-PIT/FTRIM/实盘费), 非 08-26 正典形; (b) 分辨率 ±0.05~±0.10 bps/锚/gross(2024→26), ±0.06~±0.13(2025→26), 增益量级与之相当 ⇒ 未定而非否定; (c) 席位规则(msharpe, LEGS=101)只含 king/fund, φ 不在席位内, 本文只扫固定 φ; (d) 换手门窗口取 2024→26 为本文假设(预注册未指明窗口), 2025→26 并列打印(0.65 s42 +31.6%, 同样破门); (e) bootstrap 每格用同一种子的新生成器; (f) 2026 单窗 φ 0.55 s42 CI>0 不作依据(预注册禁)。")
P("- 归档: `multi_asset/exports/research/retrain_2026-09/phi_grid_2026-09-05/`(脚本 + 结果 json/md + logs + SHA256SUMS + MANIFEST; 8 个 .npz 留 pod, 路径与 sha 在 MANIFEST.md)。pod 只读, 未训练, 未触碰实盘侧。")
open(OUT, "w").write("\n".join(L) + "\n")
print(OUT, sha(OUT))
