"""风险预算扫描 —— 执行 PREREG_risk_budget_2026-08-05.md
(FROZEN v1, sha 69dba0ad73c6899a9c50b85b658795942b6d82ff3afe1cc7025b8031ff13de3e)

判据由【用户】所定, 逐字执行, 顺序 A→C→B。本脚本不解释判据, 只执行。
"""
import sys, json, time
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
import torch; torch.backends.mkldnn.enabled = False
from engine import replay_fullhist as RF
from engine import signal_chain as SC

KING = "/tmp/king_pred_newgen.npz"; S2 = "/tmp/s2_pred_newgen.npz"
LIVE_W = {"king": .5952380952380952, "s2": .20238095238095238,
          "funding": .20238095238095238, "size": 0.0}
ALPHAS = [1.0, 0.75, 0.5]
LAMBDAS = [0.0, 0.25, 0.5, 0.75, 1.0]
KAPPAS = [None, 4.0, 3.0, 2.0]
COSTS = [3.63, 5.8]

_ORIG = SC.SignalChain.shape_position
_ST = {"a": 1.0, "l": 0.0, "k": None, "sig": None, "t": None, "idx": None, "hhi": []}


def build_sigma(src, win=24):
    """逐名因果已实现波动。★ 用面板通道 `rvol_24h` 的同源构造:
    面板的 rvol_24h 来自 wide_factory 的 _roll(ret1, 24, 'std'), 这里在 replay 的 source 上
    以同一定义重建 —— replay 的 PanelSource 只暴露 CH, 而 rvol_24h 就在 CH 里, 直接取。"""
    j = src.ch.index("rvol_24h")
    return np.asarray(src.CH[:, :, j], np.float64)


def patched(self, combo):
    base = _ORIG(self, combo)                    # C3 + cap99 + demean, 原样
    a, l, k = _ST["a"], _ST["l"], _ST["k"]
    if a == 1.0 and l == 0.0 and k is None:
        return base                              # ★ 逐位回落到现行(有效性判据靠它)
    m = _ST["idx"]; sig = _ST["sig"]; t = _ST["t"]
    if m is None or sig is None or t is None or len(base) != len(m):
        return base
    s = sig[t, m]
    fin = np.isfinite(s) & (s > 0)
    if not fin.any():
        return base
    med = np.median(s[fin])
    s = np.where(fin, s, med)
    w = np.sign(base) * np.abs(base) ** a / np.power(s / med, l)
    if k is not None:
        g = np.abs(w).sum()
        if g > 0:
            cap = k * g / max(len(w), 1)
            w = np.clip(w, -cap, cap)
            g2 = np.abs(w).sum()
            if g2 > 0:
                w = w * g / g2
    out = w - w.mean()                           # 缩放破坏中性 ⇒ 二次 demean
    g0, g1 = np.abs(base).sum(), np.abs(out).sum()
    if g1 > 0 and g0 > 0:
        out = out * g0 / g1                      # 归一到同毛敞口, 保证同口径
    rc = np.abs(out) * s
    if rc.sum() > 0:
        _ST["hhi"].append(float((rc ** 2).sum() / rc.sum() ** 2 * len(rc)))
    return out


_ORIG_LP = SC.SignalChain.leg_positions


def patched_lp(self, t):
    out, m = _ORIG_LP(self, t)
    _ST["t"] = int(t); _ST["idx"] = m
    return out, m


SC.SignalChain.shape_position = patched
SC.SignalChain.leg_positions = patched_lp


def run(a, l, k, cost, sig):
    _ST.update(a=a, l=l, k=k, sig=sig, hhi=[])
    RF.COST_BPS = cost
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=KING, s2=S2, weights=dict(LIVE_W), verbose=False)
    ic = float(np.mean([o["per_year"][y]["mean_rank_ic"] for y in o["per_year"]]))
    return {"sh": float(o["avg_net_of_cost_sharpe"]), "ic": ic,
            "hhi": float(np.mean(_ST["hhi"])) if _ST["hhi"] else float("nan"),
            "turn": float(o["netting"]["net_turn_ann"]),
            "per_year_ic": {int(y): float(o["per_year"][y]["mean_rank_ic"]) for y in o["per_year"]},
            "per_year_sh": {int(y): float(o["per_year"][y]["net_of_cost_sharpe"]) for y in o["per_year"]}}


RF._SRC, RF._SRC_KEY = None, None
RF.COST_BPS = COSTS[0]
src = RF.get_src(None, KING, S2)
SIG = build_sigma(src)
print(f"sigma from CH['rvol_24h'] shape={SIG.shape} finite={np.isfinite(SIG).mean():.3f}", flush=True)

res = {}
t0 = time.time()
n = 0
for a in ALPHAS:
    for l in LAMBDAS:
        for k in KAPPAS:
            for c in COSTS:
                RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
                res[(a, l, k, c)] = run(a, l, k, c, SIG)
                n += 1
            if n % 16 == 0:
                print(f"  {n}/{len(ALPHAS)*len(LAMBDAS)*len(KAPPAS)*len(COSTS)}  "
                      f"({time.time()-t0:.0f}s)", flush=True)

base = {c: res[(1.0, 0.0, None, c)] for c in COSTS}
print(f"\n[有效性判据] 现行格 (α=1, λ=0, κ=∞): "
      f"IC {base[3.63]['ic']:.5f}  Sh@3.63 {base[3.63]['sh']:+.3f}  HHI {base[3.63]['hhi']:.3f}")

rows = []
for (a, l, k, c), v in res.items():
    if c != COSTS[0]:
        continue
    v2 = res[(a, l, k, COSTS[1])]
    dic = v["ic"] / base[3.63]["ic"] - 1
    A = dic >= -0.10
    C = (v["sh"] >= base[3.63]["sh"] - 1e-9) and (v2["sh"] >= base[5.8]["sh"] - 1e-9)
    rows.append({"a": a, "l": l, "k": k, "ic": v["ic"], "dic": dic, "hhi": v["hhi"],
                 "dhhi": v["hhi"] / base[3.63]["hhi"] - 1, "sh363": v["sh"], "sh58": v2["sh"],
                 "turn": v["turn"], "A": A, "C": C,
                 "per_year_ic": v["per_year_ic"]})

surv = [r for r in rows if r["A"] and r["C"]]
print(f"\n[A] IC 降 ≤10%: {sum(r['A'] for r in rows)}/{len(rows)}   "
      f"[A∧C] 且两档净夏普不劣: {len(surv)}/{len(rows)}")
if not surv:
    print("\n★ 判据 §2 的空结果条款触发: 【IC 预算 10% 内买不到风险下降】。不放宽 A, 不去掉 C。")
else:
    surv.sort(key=lambda r: r["dhhi"])
    print(f"\n幸存者按 HHI 降幅排序(前 10):")
    print(f"  {'α':>4} {'λ':>5} {'κ':>5} {'IC':>8} {'ΔIC':>7} {'HHI':>7} {'ΔHHI':>8} "
          f"{'Sh@3.63':>8} {'Sh@5.8':>8} {'turn':>7}")
    for r in surv[:10]:
        print(f"  {r['a']:>4} {r['l']:>5} {str(r['k']):>5} {r['ic']:>8.5f} {r['dic']*100:>+6.1f}% "
              f"{r['hhi']:>7.3f} {r['dhhi']*100:>+7.1f}% {r['sh363']:>+8.3f} {r['sh58']:>+8.3f} "
              f"{r['turn']:>7.0f}")
    w = surv[0]
    print(f"\n[B] 胜者: α={w['a']} λ={w['l']} κ={w['k']}  "
          f"ΔIC {w['dic']*100:+.1f}%  ΔHHI {w['dhhi']*100:+.1f}%  "
          f"Sh {w['sh363']:+.3f}/{w['sh58']:+.3f}")

json.dump({"prereg": "PREREG_risk_budget_2026-08-05.md",
           "prereg_sha256": "69dba0ad73c6899a9c50b85b658795942b6d82ff3afe1cc7025b8031ff13de3e",
           "criteria_author": "user",
           "baseline": {str(c): base[c] for c in COSTS},
           "rows": [{k: (v if not isinstance(v, dict) else {str(x): y for x, y in v.items()})
                     for k, v in r.items()} for r in rows]},
          open(MA + "/exports/eda/RESULT_risk_budget_2026-08-05.json", "w"), indent=1)
print("\nrecord -> exports/eda/RESULT_risk_budget_2026-08-05.json")
