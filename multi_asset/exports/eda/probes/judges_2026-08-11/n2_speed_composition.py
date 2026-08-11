"""N2 —— 腿权重 × 收割速度 的交互, 逐字执行 PREREG_N2_speed_composition_2026-08-06.md。
报整张面 + holdout, 不报 argmax 作为建议。远端只计算, 结果走 stdout 回传(主线新守卫的正确模式)。
"""
import sys, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
import torch; torch.backends.mkldnn.enabled = False
from engine import replay_fullhist as RF
from engine import signal_chain as SC

KING = "/tmp/king_pred_newgen.npz"; S2 = "/tmp/s2_pred_newgen.npz"
COSTS = [2.5, 3.63]
SPEEDS = [1.00, 0.15, 0.03]
WSET = {
    "live":       {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238},
    "dl_only":    {"king": .7462686567164178, "s2": .2537313432835821, "funding": 0.0},
    "king_only":  {"king": 1.0, "s2": 0.0, "funding": 0.0},
    "king_heavy": {"king": .80, "s2": .10, "funding": .10},
    "fund_heavy": {"king": .40, "s2": .20, "funding": .40},
    "s2_heavy":   {"king": .40, "s2": .40, "funding": .20},
    "equal":      {"king": 1/3, "s2": 1/3, "funding": 1/3},
}
_ORIG = SC.SignalChain.shape_position
_ORIG_LP = SC.SignalChain.leg_positions
NMAX = 200
_ST = {"a": 1.0, "idx": None, "prev": np.zeros(NMAX), "have": False}


def patched_lp(self, t):
    o, m = _ORIG_LP(self, t); _ST["idx"] = m; return o, m


def patched(self, combo):
    base = _ORIG(self, combo); a = _ST["a"]
    if a >= 1.0:
        return base
    m = _ST["idx"]
    if m is None or len(base) != len(m):
        return base
    prev = _ST["prev"][m]; out = base
    if _ST["have"]:
        out = (1.0 - a) * prev + a * base
        out = out - out.mean()
        g0, g1 = np.abs(base).sum(), np.abs(out).sum()
        out = out * g0 / g1 if (g1 > 1e-12 and g0 > 0) else base
    _ST["prev"][:] = 0.0; _ST["prev"][m] = out; _ST["have"] = True
    return out


def run(c, w):
    _ST.update(prev=np.zeros(NMAX), have=False)
    RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
    RF.COST_BPS = c
    ww = dict(w); ww["size"] = 0.0
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=KING, s2=S2, weights=ww, verbose=False)
    py = {int(y): float(o["per_year"][y]["net_of_cost_sharpe"]) for y in o["per_year"]}
    return {"sh": float(o["avg_net_of_cost_sharpe"]), "turn": float(o["netting"]["net_turn_ann"]),
            "per_year": py,
            "fit": float(np.mean([py[y] for y in py if y <= 2024])),
            "hold": float(np.mean([py[y] for y in py if y >= 2025]))}


RF._SRC, RF._SRC_KEY = None, None
RF.COST_BPS = 3.63
src = RF.get_src(None, KING, S2)
b = run(3.63, WSET["live"])
SC.SignalChain.shape_position = patched
SC.SignalChain.leg_positions = patched_lp
_ST.update(a=1.0)
c0 = run(3.63, WSET["live"])
ok = abs(c0["sh"] - b["sh"]) < 1e-12
print(f"[有效性] a=1 逐位复现: {'OK' if ok else 'FAIL'} (live@3.63 = {b['sh']:+.3f})", flush=True)
if not ok:
    sys.exit(1)

res = {}
for a in SPEEDS:
    _ST.update(a=a)
    print(f"\n[speed a={a:.2f}]  权重        turn   Sh@2.5   Sh@3.63  | 拟合22-24  保留25-26", flush=True)
    for tag, w in WSET.items():
        r = {c: run(c, w) for c in COSTS}
        res[f"a{a}_{tag}"] = {"a": a, "w": tag, "turn": r[3.63]["turn"],
                              "sh25": r[2.5]["sh"], "sh363": r[3.63]["sh"],
                              "fit363": r[3.63]["fit"], "hold363": r[3.63]["hold"],
                              "per_year": r[3.63]["per_year"]}
        print(f"            {tag:11s} {r[3.63]['turn']:6.0f}  {r[2.5]['sh']:+7.3f}  "
              f"{r[3.63]['sh']:+7.3f}  |  {r[3.63]['fit']:+7.3f}  {r[3.63]['hold']:+7.3f}", flush=True)

print("\n★ 判读所需三件:", flush=True)
out = {"rows": res, "argmax": {}}
for a in SPEEDS:
    sub = {k: v for k, v in res.items() if v["a"] == a}
    rank363 = sorted(sub.values(), key=lambda v: -v["sh363"])
    rankfit = sorted(sub.values(), key=lambda v: -v["fit363"])
    rankhold = sorted(sub.values(), key=lambda v: -v["hold363"])
    live = sub[f"a{a}_live"]
    cost_of_live = rank363[0]["sh363"] - live["sh363"]
    out["argmax"][str(a)] = {"top2_full": [rank363[0]["w"], rank363[1]["w"]],
                             "top2_fit": [rankfit[0]["w"], rankfit[1]["w"]],
                             "top2_hold": [rankhold[0]["w"], rankhold[1]["w"]],
                             "cost_of_live_weights": round(cost_of_live, 3)}
    print(f"  a={a:.2f}: 全期top2 {rank363[0]['w']}/{rank363[1]['w']} | "
          f"拟合top2 {rankfit[0]['w']}/{rankfit[1]['w']} | 保留top2 {rankhold[0]['w']}/{rankhold[1]['w']} "
          f"| 用线上权重的代价 {cost_of_live:+.3f}", flush=True)
print("\nJSON_BEGIN")
print(json.dumps(out, ensure_ascii=False))
print("JSON_END")
