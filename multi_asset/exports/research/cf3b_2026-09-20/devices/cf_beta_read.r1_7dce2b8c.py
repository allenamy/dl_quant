#!/usr/bin/env python3
"""cf_beta_read.py — CF3-B step 3: collect the four at_beta runs and APPLY THE PRE-REGISTERED
FALSIFIERS IN CODE, so the verdict is computed rather than eyeballed.

PREREG docs/PREREG_style_beta_on_counterfactual_worlds_2026-09-20.md §5 (+B-A1):
  s = d_common_style / (d_common_style + d_name_specific)      (share of the HIST->2026 improvement)
  5.1 lead's stated-more-likely reading ("a common/style tailwind lifts any book of this family"),
      operationalised BEFORE the numbers as: |s_NONE - s_BASE| <= 15pp AND d_common p < 0.05
  5.2 the alternative ("both books improved through name selection"): 1 - s_NONE >= 65% AND p < 0.05
  5.3 neither cleanly satisfied  =>  UNDECIDED, print the numbers, do not pick the nearer one
  5.4 unattributed bound > half of |d_common|  =>  the common term is unreadable => UNDECIDED
      and: |s_noFUND - s_noFUND_GF| > 15pp => that contrast is gate-convention-dominated, description only

usage: /workspace/venv/bin/python -B cf_beta_read.py <RECEIPTS_DIR> <OUT_JSON> <OUT_MD>
"""
import json
import os
import sys

R = sys.argv[1]
OUTJ = sys.argv[2]
OUTM = sys.argv[3]
ARMS = ["BASE", "NONE", "noFUND", "noFUND_GF"]
D = {a: json.load(open(f"{R}/{a}/AT_BETA.json")) for a in ARMS}
CERT = json.load(open("/workspace/attrib_2026_2026-09-20/receipts/AT_BETA.json"))
UNREAD = json.load(open(f"{R}/unread/CF_BETA_UNREAD_TEST.json"))
GATES = {a: json.load(open(f"{R}/CF_BETA_{a}.json")) for a in ARMS}

out = {"prereg": "docs/PREREG_style_beta_on_counterfactual_worlds_2026-09-20.md (+B-A1)"}


def share(a):
    c = D[a]["ci_2026_vs_HIST"]
    dc, dr = c["style_common"]["point"], c["style_residual"]["point"]
    tot = dc + dr
    return dc, dr, (dc / tot if tot != 0 else None), c["style_common"]["p"], c["style_residual"]["p"], c["price"]["point"]


S = {}
for a in ARMS:
    dc, dr, s, pc, pr, dp = share(a)
    S[a] = {"d_price": dp, "d_common_style": dc, "d_name_specific": dr,
            "s_common_share": (None if s is None else 100 * s),
            "p_common": pc, "p_name": pr,
            "denominator_near_zero": abs(dc + dr) < 0.25,
            "per_period": {p: {k: D[a]["per_period"][p][k] for k in
                               ("n_anchors", "price", "style_common_risk_and_style", "style_residual_selection",
                                "unattributed_no_beta", "unattributed_bound_abs", "gross_share_without_beta",
                                "book_ex_ante_net_beta_mean")}
                           for p in ("HIST", "2026", "FULL_RECIPE")}}
out["arms"] = S

# ── B5 control ─────────────────────────────────────────────────────────────
b5 = {}
for p in ("HIST", "2026", "FULL_RECIPE"):
    for k in ("price", "style_common_risk_and_style", "style_residual_selection"):
        b5[f"{p}/{k}"] = {"mine": D["BASE"]["per_period"][p][k], "published": CERT["per_period"][p][k],
                          "identical": D["BASE"]["per_period"][p][k] == CERT["per_period"][p][k]}
for k in CERT["ci_2026_vs_HIST"]:
    for f in ("point", "p"):
        b5[f"ci/{k}/{f}"] = {"mine": D["BASE"]["ci_2026_vs_HIST"][k][f],
                             "published": CERT["ci_2026_vs_HIST"][k][f],
                             "identical": D["BASE"]["ci_2026_vs_HIST"][k][f] == CERT["ci_2026_vs_HIST"][k][f]}
out["B5_control"] = {"n_cells": len(b5), "n_identical": sum(1 for v in b5.values() if v["identical"]),
                     "all_identical": all(v["identical"] for v in b5.values()), "cells": b5}

# ── the pre-registered falsifiers, applied ─────────────────────────────────
sB, sN = S["BASE"]["s_common_share"], S["NONE"]["s_common_share"]
bound_ok = all(max(S[a]["per_period"]["HIST"]["unattributed_bound_abs"],
                   S[a]["per_period"]["2026"]["unattributed_bound_abs"]) <= abs(S[a]["d_common_style"]) / 2
               for a in ARMS)
c51_similar = abs(sN - sB) <= 15.0
c51_sig = S["NONE"]["p_common"] < 0.05
c52 = (100 - sN) >= 65.0 and S["NONE"]["p_name"] < 0.05
gf_gap = abs(S["noFUND"]["s_common_share"] - S["noFUND_GF"]["s_common_share"])
out["verdicts"] = {
    "5.4_unattributed_bound_leaves_common_readable": bound_ok,
    "5.4_noFUND_contrast_convention_dominated": gf_gap > 15.0,
    "5.1_lead_reading_tailwind_lifts_any_book": {
        "criterion": "|s_NONE - s_BASE| <= 15pp AND p_common < 0.05",
        "s_BASE": sB, "s_NONE": sN, "gap_pp": abs(sN - sB), "similar_within_15pp": c51_similar,
        "p_common_NONE": S["NONE"]["p_common"], "significant": c51_sig,
        "SUPPORTED": bool(c51_similar and c51_sig)},
    "5.2_alternative_mostly_name_specific": {
        "criterion": "1 - s_NONE >= 65% AND p_name < 0.05",
        "name_specific_share": 100 - sN, "p_name_NONE": S["NONE"]["p_name"], "SUPPORTED": bool(c52)},
}
sup51 = out["verdicts"]["5.1_lead_reading_tailwind_lifts_any_book"]["SUPPORTED"]
sup52 = out["verdicts"]["5.2_alternative_mostly_name_specific"]["SUPPORTED"]
out["verdicts"]["FINAL"] = ("5.1" if (sup51 and not sup52) else
                            "5.2" if (sup52 and not sup51) else "UNDECIDED (PREREG 5.3)")
out["verdicts"]["direction_note"] = (
    "NOT part of the pre-registered test, stated because it is what the numbers show: NONE's improvement "
    "is MORE common/style-driven than BASE's (%.1f%% vs %.1f%%), not less, and its d_common is the most "
    "significant of any arm (p = %.4f). My 5.1 criterion tested SIMILARITY to BASE; the coordinator's "
    "substantive wording was a DIRECTIONAL claim. See the result document: the gap between the two is a "
    "defect in my own operationalisation, not a property of the data."
    % (sN, sB, S["NONE"]["p_common"]))
out["unread_test"] = UNREAD
out["gate_receipts"] = {a: {"verdict": GATES[a]["verdict"], "failed": GATES[a]["failed"]} for a in ARMS}
json.dump(out, open(OUTJ, "w"), indent=1, default=float)

# ── markdown ───────────────────────────────────────────────────────────────
L = []
def w(x=""):
    L.append(x)
def f(x, n=4):
    return "—" if x is None else ("%+." + str(n) + "f") % x

w("# CF3-B 全表 · 反事实世界上的风格/β 分解(由 `cf_beta_read.py` 从收据渲染)")
w()
w("仪器 = **未改一个字节的** `at_beta.py`; 层 = **L2 纸面书**(price = 1e4·ΣW·RET), **不是** L1 已实现 g。")
w()
w("## 门")
w()
w("| 门 | 结果 |")
w("|---|---|")
w("| B5 控制复现(我的 BASE vs 已发布 §5) | **%d / %d 格逐位相同** |" % (out["B5_control"]["n_identical"], out["B5_control"]["n_cells"]))
w("| B-A1 延展 113 行不可读(变异实测) | 毒化后变动 **%d** 个数(要 0); 零对照: 单个 in_run 行 ×1.001 变动 **%d** 个数(要 >0) |"
  % (UNREAD["mutation_ext_rows"]["n_numbers_changed"], UNREAD["control_one_in_run_row"]["n_numbers_changed"]))
w("| §5.4 UNATTRIBUTED 上界 ≤ |Δ共同|/2 | **%s**(实测无 β 的 gross 份额 = %.5f, 上界 = %.4f) |"
  % ("满足" if bound_ok else "**不满足**", S["BASE"]["per_period"]["2026"]["gross_share_without_beta"],
     S["BASE"]["per_period"]["2026"]["unattributed_bound_abs"]))
w()
w("## 逐臂 · 逐时段(L2 纸面价格, bps/锚/目标 gross)")
w()
w("| 臂 | 时段 | n | 价格 | 共同风险+风格 | 逐名 | 事前净 β |")
w("|---|---|---|---|---|---|---|")
for a in ARMS:
    for p in ("HIST", "2026"):
        d = S[a]["per_period"][p]
        w("| `%s` | %s | %d | %s | **%s** | **%s** | %s |"
          % (a, p, d["n_anchors"], f(d["price"]), f(d["style_common_risk_and_style"]),
             f(d["style_residual_selection"]), f(d["book_ex_ante_net_beta_mean"])))
w()
w("## HIST → 2026 的改善, 按成分(自举 p 来自 `at_beta.py` 自己的检验)")
w()
w("| 臂 | Δ价格 | Δ共同+风格 | p | Δ逐名 | p | 共同份额 s |")
w("|---|---|---|---|---|---|---|")
for a in ARMS:
    v = S[a]
    w("| `%s` | %s | **%s** | %.4f | **%s** | %.4f | %s |"
      % (a, f(v["d_price"]), f(v["d_common_style"]), v["p_common"], f(v["d_name_specific"]), v["p_name"],
         ("%.1f%%" % v["s_common_share"]) + (" ⚠分母近零" if v["denominator_near_zero"] else "")))
w()
w("## 预注册判据(在装置里算的, 不是看出来的)")
w()
for k in ("5.1_lead_reading_tailwind_lifts_any_book", "5.2_alternative_mostly_name_specific"):
    v = out["verdicts"][k]
    w("- **%s** — 判据 `%s` ⇒ **%s**" % (k, v["criterion"], "支持" if v["SUPPORTED"] else "**不支持**"))
    w("  - " + json.dumps({kk: vv for kk, vv in v.items() if kk not in ("criterion", "SUPPORTED")}, ensure_ascii=False))
w("- **最终判决: %s**" % out["verdicts"]["FINAL"])
w("- `noFUND` 与 `noFUND_GF` 的 s 相差 **%.1f** 个百分点 ⇒ 该对照 **%s**(§5.4)"
  % (gf_gap, "受门口径支配, 只作描述" if gf_gap > 15 else "两口径一致"))
w()
w("> " + out["verdicts"]["direction_note"])
open(OUTM, "w").write("\n".join(L) + "\n")
print("CF_BETA_READ wrote %s and %s | FINAL=%s | B5 %d/%d identical"
      % (OUTJ, OUTM, out["verdicts"]["FINAL"], out["B5_control"]["n_identical"], out["B5_control"]["n_cells"]), flush=True)
