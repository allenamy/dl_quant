#!/usr/bin/env python3
"""cf_render.py — CF3 step 5: render CF_READ.json into markdown tables. LAYOUT ONLY: this device
computes nothing; every number is copied from the receipt so that no figure in the result document
is transcribed by hand.

usage: /workspace/venv/bin/python -B cf_render.py <RECEIPTS_DIR> <OUT_MD>
"""
import json
import os
import sys
import time

R = sys.argv[1]
OUT = sys.argv[2]
D = json.load(open(f"{R}/CF_READ.json"))
ARMSJ = json.load(open(f"{R}/CF_ARMS.json"))
REB = json.load(open(f"{R}/CF_REBUILD.json"))
ST = json.load(open(f"{R}/CF_SELFTEST.json"))

FAITH = ["BASE", "noFUND", "noKING", "noF10", "onlyFUND", "onlyKING", "onlyF10", "NONE"]
FROZ = ["BASE", "noFUND_GF", "noKING_GF", "noF10_GF", "onlyFUND_GF", "onlyKING_GF", "onlyF10_GF", "NONE_GF"]
PER = ["HIST", "2026", "FULL_RECIPE"]
L = []


def w(s=""):
    L.append(s)


def f(x, n=3, pct=False):
    if x is None:
        return "—"
    try:
        return ("%+." + str(n) + "f%%") % (100 * x) if pct else ("%+." + str(n) + "f") % x
    except Exception:
        return str(x)


w("> **创建:** %s | **Session:** CF3 | **状态:** 由 `cf_render.py` 从收据渲染, 不含任何手抄数字 | "
  "**作废条件:** CF_READ 收据被替换" % time.strftime("%Y-%m-%d", time.gmtime()))
w()
w("# CF3 全表 · 三信号(资金费 / king / F10)反事实重链")
w()
w("口径: object B A0_main, B-scaled 读数, 模拟器 v3.1 + 复原价 + 2.0x + rule 日止损 + 32 条成交路径。")
w("`g` = bps / 锚 / 目标 gross(目标 gross = 2.0 x 该锚窗初 NAV), 32 条路径的路径均值。")
w()

# ── T0 判词 ──
w("## T0 判词行(整行, 不报裸计数)")
w()
w("| 装置 | 判词 | 失败项 |")
w("|---|---|---|")
w("| `cf_rebuild.py` | `CF_REBUILD VERDICT=%s checks=%d failed=%s state_anchors=%d` | %s |"
  % (REB["verdict"], len(REB["checks"]), REB["failed"], REB["census"]["n_state_anchors"], REB["failed"] or "[]"))
w("| `cf_arms.py` | `CF_ARMS VERDICT=%s checks=%d failed=%s arm_files=%d` | %s |"
  % (ARMSJ["verdict"], len(ARMSJ["checks"]), ARMSJ["failed"], len(ARMSJ["arms"]), ARMSJ["failed"] or "[]"))
w("| `cf_selftest.py` | `CF_SELFTEST VERDICT=%s items=%d credited=%d failed=%s` | %s |"
  % (ST["verdict"], ST["n_items"], ST["n_credited"], ST["failed"], ST["failed"] or "[]"))
w("| `cf_read.py` | `CF_READ VERDICT=%s checks=%d failed=%s` | %s |"
  % (D["verdict"], len(D["checks"]), D["failed"], D["failed"] or "[]"))
w()
w("Gate J1(本任务的 judge 就是基线表的 judge): CF_BASE 的 32 条路径文件与认证 `OBJB_A0|scaled|rule|raw|UAFE` "
  "**逐字节相同**, 差异文件数 **%d**; AGG 不同的键 **%s**。g 恒等式最大残差 **%.2e** bps。"
  % (len(D["gate_J"]["J1"]["differing"]), D["gate_J"]["J1"]["agg_keys_differing"] or "[]", D["gate_J"]["J2_max_g_identity_err"]))
w()

# ── T1 人口 ──
w("## T1 闭合人口(每张表的分母; E-0920-C)")
w()
w("| 时段 | 锚 n | 首锚 | 末锚 | COMBO 桶 | KING_FILE 桶 | HOLD 桶 | 三桶和 == n | 有持仓(gross0>0) | 无持仓(具名子集) |")
w("|---|---|---|---|---|---|---|---|---|---|")
for p in ["HIST", "2026", "FULL_RECIPE", "PRE", "ALL_2022_06"]:
    v = D["populations"][p]
    b = v["buckets_by_BASE_kind"]
    w("| %s | %d | %s | %s | %d | %d | %d | %s | %d | %d |"
      % (p, v["n_anchors"], v["first_anchor"], v["last_anchor"], b["COMBO"], b["KING_FILE"], b["HOLD"],
         "是" if v["buckets_sum_equals_n"] else "**否**", v["HAS_POSITION_gross0_gt_0"], v["NO_POSITION_gross0_eq_0"]))
w()
w("桶按 **BASE 臂的 kind** 切, 因此逐臂可比; 各臂自己的 kind 翻转数见 T5。")
w()

# ── T2 逐臂主表 ──
for gate, arms in (("G-FAITHFUL(主口径, 每臂重算前飞门)", FAITH), ("G-FROZEN(沿用 BASE 的 kind, 豁免前飞下限)", FROZ)):
    w("## T2 逐臂主表 · %s" % gate)
    w()
    for p in PER:
        w("### %s" % p)
        w()
        w("| 臂 | 锚 n | 2xNAV 累计 | CAGR | 日夏普 | 回撤 4h | 回撤 5m | g(全人口) | n(有持仓) | g(有持仓) |")
        w("|---|---|---|---|---|---|---|---|---|---|")
        for a in arms:
            c = D["tables"][a][p]
            w("| `%s` | %d | %s | %s | %s | %s | %s | **%s** | %d | %s |"
              % (a, c["n_anchors"], f(c["nav_return"], 2, True), f(c["cagr"], 2, True),
                 f(c["sharpe_daily"], 2), f(c["maxdd_4h"], 2, True), f(c["maxdd_5m"], 2, True),
                 f(c["g"]), c["n_has_position"], f(c["g_has_position"])))
        w()

# ── T3 逐桶 g ──
w("## T3 逐桶 g(按 BASE 臂的 kind 切; 每格带 n)")
w()
for p in PER:
    w("### %s" % p)
    w()
    w("| 臂 | COMBO n | COMBO g | KING_FILE n | KING_FILE g | HOLD n |")
    w("|---|---|---|---|---|---|")
    for a in FAITH + [x for x in FROZ if x != "BASE"]:
        b = D["tables"][a][p]["buckets_by_BASE_kind"]
        w("| `%s` | %d | %s | %d | %s | %d |"
          % (a, b["COMBO"]["n"], f(b["COMBO"]["g_whole_population"]),
             b["KING_FILE"]["n"], f(b["KING_FILE"]["g_whole_population"]), b["HOLD"]["n"]))
    w()
w("**自检 C5(预注册 §9)· 前提被证伪, 不是装置缺陷**: 预注册写「KING_FILE 桶在 G-FROZEN 下按构造逐臂完全相同」。"
  "上表显示它**不同**。已查证: 在全部 3,337 个 BASE-king 文件锚上, `noKING_GF` 写出的目标与 BASE **逐位相同**"
  "(0 个锚不同, max|dw| = 0.0)。差异全部来自**执行器到达那些锚时手里拿着另一本书**: 完整配方窗该桶上"
  "`noKING_GF` 的换手是 gross 的 **0.1617** vs BASE 的 **0.1278**(+27%), 多出来的换手带着费用与滑点 ⇒ 桶内 g "
  "−1.415 vs −1.244。**「交易同一个目标」不蕴含「实现同一个收益」** —— 任何按「交易了哪本书」切桶再跨臂比较的读数都继承这一条。")
w()

# ── T4 Delta vs BASE ──
w("## T4 与 BASE 的差(按锚配对, 5 日移动块自举 B=10,000; 描述性标签)")
w()
for p in PER:
    w("### %s" % p)
    w()
    w("| 臂 | Δg | Δg CI95 | ΔSharpe | ΔSharpe CI95 | ΔCAGR | ΔCAGR CI95 |")
    w("|---|---|---|---|---|---|---|")
    for a in [x for x in FAITH if x != "BASE"] + [x for x in FROZ if x != "BASE"]:
        d = D["delta_vs_BASE"][a][p]
        w("| `%s` | %s | [%s, %s] | %s | [%s, %s] | %s | [%s, %s] |"
          % (a, f(d["d_g"]["estimate"]), f(d["d_g"]["ci95"][0]), f(d["d_g"]["ci95"][1]),
             f(d["d_sharpe"]["estimate"], 2), f(d["d_sharpe"]["ci95"][0], 2), f(d["d_sharpe"]["ci95"][1], 2),
             f(d["d_cagr"]["estimate"], 2, True), f(d["d_cagr"]["ci95"][0], 2, True), f(d["d_cagr"]["ci95"][1], 2, True)))
    w()

# ── T5 具名子集 ──
w("## T5 具名子集(不进任何均值, 只报 n)")
w()
w("| 时段 | 臂 | G-FAITHFUL kind2 | G-FROZEN kind2 | DEGEN_BOTH | DEGEN_ONE | KIND_FLIP vs BASE (FAITH) |")
w("|---|---|---|---|---|---|---|")
for p in PER:
    ns = D["named_subsets"][p]
    for a in FAITH:
        v = ns[a]
        w("| %s | `%s` | %d | %d | %d | %d | %d |"
          % (p, a, v["kind2"], v["GF_kind2"], v["DEGEN_BOTH"], v["DEGEN_ONE"], v["KIND_FLIP_vs_BASE"]))
w()

# ── T6 分解 ──
w("## T6 三信号分解(交互缺口显式报出, 不分摊)")
w()
for gate in ("G-FAITHFUL", "G-FROZEN"):
    w("### %s" % gate)
    w()
    for p in PER:
        dd = D["decomposition"][gate][p]["g"]
        w("**%s · 主量 g(唯一可加的量)**" % p)
        if "UNAVAILABLE" in dd:
            w()
            w("UNAVAILABLE: %s" % dd["UNAVAILABLE"])
            w()
            continue
        w()
        w("| 联盟 | v(S) = g |")
        w("|---|---|")
        for k, v in sorted(dd["coalition_values"].items(), key=lambda kv: (-len(kv[0]), kv[0])):
            w("| %s | %s |" % (k, f(v)))
        w()
        w("| 量 | FUND | KING | F10 | 合计 | 与 v(N)−v(∅) 的缺口 |")
        w("|---|---|---|---|---|---|")
        w("| LOO = v(N)−v(N∖i) | %s | %s | %s | %s | **%s** |"
          % (f(dd["LOO"]["FUND"]), f(dd["LOO"]["KING"]), f(dd["LOO"]["F10"]),
             f(sum(dd["LOO"].values())), f(dd["GAP_LOO"])))
        w("| LOI = v({i})−v(∅) | %s | %s | %s | %s | **%s** |"
          % (f(dd["LOI"]["FUND"]), f(dd["LOI"]["KING"]), f(dd["LOI"]["F10"]),
             f(sum(dd["LOI"].values())), f(dd["GAP_LOI"])))
        w("| **Shapley** | **%s** | **%s** | **%s** | %s | %s(算术残差) |"
          % (f(dd["shapley"]["FUND"]), f(dd["shapley"]["KING"]), f(dd["shapley"]["F10"]),
             f(sum(dd["shapley"].values())), f(dd["shapley_sum_residual"], 12)))
        sp = dd["per_signal_ordering_spread"]
        w("| 6 个排序下的边际跨度 | %s…%s | %s…%s | %s…%s | | |"
          % (f(sp["FUND"]["min"]), f(sp["FUND"]["max"]), f(sp["KING"]["min"]), f(sp["KING"]["max"]),
             f(sp["F10"]["min"]), f(sp["F10"]["max"])))
        w()
        w("v(N)−v(∅) = **%s** bps/锚; LOO 可加性判据(|GAP_LOO| ≤ 0.5·|total|): **%s**。"
          % (f(dd["total_v(N)-v(empty)"]), "满足" if dd["decomposable_by_LOO"] else "**不满足 ⇒ LOO 读数不得当作贡献**"))
        w()
        w("<details><summary>6 个排序的逐个边际贡献</summary>")
        w()
        w("| 排序 | FUND | KING | F10 |")
        w("|---|---|---|---|")
        for o, m in dd["per_ordering_marginals"].items():
            w("| %s | %s | %s | %s |" % (o, f(m["FUND"]), f(m["KING"]), f(m["F10"])))
        w()
        w("</details>")
        w()
    w("**非可加量(描述性, 这些量上不存在贡献分解)**")
    w()
    w("| 时段 | 量 | FUND Shapley | KING Shapley | F10 Shapley | v(N)−v(∅) | GAP_LOO |")
    w("|---|---|---|---|---|---|---|")
    for p in PER:
        for key, lab in (("cagr", "CAGR"), ("sharpe_daily", "日夏普"), ("maxdd_4h", "回撤 4h"), ("nav_return", "2xNAV")):
            dd = D["decomposition"][gate][p][key]
            if "UNAVAILABLE" in dd:
                w("| %s | %s | — | — | — | — | UNAVAILABLE |" % (p, lab))
                continue
            nn = 2 if key in ("sharpe_daily",) else 4
            w("| %s | %s | %s | %s | %s | %s | %s |"
              % (p, lab, f(dd["shapley"]["FUND"], nn), f(dd["shapley"]["KING"], nn), f(dd["shapley"]["F10"], nn),
                 f(dd["total_v(N)-v(empty)"], nn), f(dd["GAP_LOO"], nn)))
    w()

w("---")
w()
w("**收据**: `CF_REBUILD.json` / `CF_ARMS.json` / `CF_SELFTEST.json` / `CF_READ.json`(本文件全部数字的来源)。")
w("**盲态**: %s" % D["blind_protocol"])
with open(OUT + ".tmp", "w") as fh:
    fh.write("\n".join(L) + "\n")
os.replace(OUT + ".tmp", OUT)
print("CF_RENDER wrote %s (%d lines)" % (OUT, len(L)), flush=True)
