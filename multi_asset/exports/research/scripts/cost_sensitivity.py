"""E1e —— 把发现表达成【成本的函数】, 并实测交叉点。

动机: 实盘实测成本不确定(真费 2.33-2.60bps, 净成本日读数 0.15-8.82bps), 而我的 +1.73 是在
3.63bps 上测的。若真实成本是引擎默认 1.9, Δ 会缩到 ~+0.37。⇒ 一个点没有决策价值,
【曲线 + 交叉点】才有。

线性外推给出交叉点 c* = 1.43 bps(基线斜率 0.8433/bps vs a=0.01 的 0.0461/bps)。
本脚本【实测】多个成本档验证该外推 —— 外推与实测偏差 >10% ⇒ 线性假设作废, 以实测为准。
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
LIVE_W = {"king": .5952380952380952, "s2": .20238095238095238,
          "funding": .20238095238095238, "size": 0.0}
GRID = [0.001, 1.0, 1.43, 1.9, 2.5, 3.63, 4.5, 5.8]
ARMS = [1.0, 0.15, 0.03, 0.01]
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
    prev = _ST["prev"][m]
    out = base
    if _ST["have"]:
        out = (1.0 - a) * prev + a * base
        out = out - out.mean()
        g0, g1 = np.abs(base).sum(), np.abs(out).sum()
        out = out * g0 / g1 if (g1 > 1e-12 and g0 > 0) else base
    _ST["prev"][:] = 0.0; _ST["prev"][m] = out; _ST["have"] = True
    return out


def run(c):
    _ST.update(prev=np.zeros(NMAX), have=False)
    RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
    RF.COST_BPS = c
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=KING, s2=S2, weights=dict(LIVE_W), verbose=False)
    return float(o["avg_net_of_cost_sharpe"]), float(o["netting"]["net_turn_ann"])


RF._SRC, RF._SRC_KEY = None, None
RF.COST_BPS = 3.63
src = RF.get_src(None, KING, S2)
SC.SignalChain.shape_position = patched
SC.SignalChain.leg_positions = patched_lp

res = {}
print("成本bps →   " + "  ".join(f"{c:6.2f}" for c in GRID), flush=True)
for a in ARMS:
    _ST.update(a=a)
    row, turn = [], None
    for c in GRID:
        s, t = run(c)
        row.append(s); turn = t
    res[str(a)] = {"turn": turn, "net_by_cost": {str(c): round(v, 3) for c, v in zip(GRID, row)}}
    print(f" a={a:4.2f} turn{turn:5.0f}: " + "  ".join(f"{v:+6.3f}" for v in row), flush=True)

b = res["1.0"]["net_by_cost"]
print("\nΔ(平滑 − 基线) 逐成本档:", flush=True)
for a in ARMS[1:]:
    d = [res[str(a)]["net_by_cost"][str(c)] - b[str(c)] for c in GRID]
    res[str(a)]["delta_by_cost"] = {str(c): round(x, 3) for c, x in zip(GRID, d)}
    # 交叉点: Δ 变号处线性内插
    xo = None
    for i in range(len(GRID) - 1):
        if d[i] < 0 <= d[i + 1]:
            xo = GRID[i] + (GRID[i + 1] - GRID[i]) * (-d[i]) / (d[i + 1] - d[i])
            break
    if xo is None and d[0] >= 0:
        xo = 0.0
    res[str(a)]["crossover_bps"] = round(xo, 3) if xo is not None else None
    print(f" a={a:4.2f}: " + "  ".join(f"{x:+6.3f}" for x in d) +
          f"   ★交叉点 {res[str(a)]['crossover_bps']} bps", flush=True)

print("\n外推预测的交叉点 1.43 bps(a=0.01) vs 实测 "
      f"{res['0.01']['crossover_bps']} bps ⇒ "
      f"{'线性外推成立 ✓' if res['0.01']['crossover_bps'] and abs(res['0.01']['crossover_bps']-1.43)<0.15 else '★外推偏差大, 以实测为准'}",
      flush=True)
json.dump(res, open("/tmp/RESULT_cost_sensitivity.json", "w"), indent=1)
