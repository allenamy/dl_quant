"""E1b —— 网格外延找真优点 + 第二个持续性族(no-trade band)。

E1 的曲线在 a=0.15 仍单调上升 ⇒ 未找到最优点。本脚本 (i) 把 EMA 外延到 a∈{0.10,0.07,0.05,0.03};
(ii) 加 no-trade band 族: 只有 |Δw| 超过阈值的名字才动, 其余保持 —— 与 EMA 形状不同
(EMA 一视同仁地抹平所有名字; band 保留大信号、只压住小抖动), 可能在同换手下保住更多 IC。
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
COSTS = [0.001, 3.63, 5.8]
_ORIG = SC.SignalChain.shape_position
_ORIG_LP = SC.SignalChain.leg_positions
NMAX = 200
_ST = {"mode": "off", "p": 1.0, "t": None, "idx": None,
       "prev": np.zeros(NMAX), "have": False, "pers": []}


def patched_lp(self, t):
    out, m = _ORIG_LP(self, t)
    _ST["t"] = int(t); _ST["idx"] = m
    return out, m


def patched(self, combo):
    base = _ORIG(self, combo)
    mode, p = _ST["mode"], _ST["p"]
    if mode == "off":
        return base
    m = _ST["idx"]
    if m is None or len(base) != len(m):
        return base
    prev = _ST["prev"][m]
    if not _ST["have"]:
        out = base
    else:
        if mode == "ema":
            out = (1.0 - p) * prev + p * base
        else:                                     # no-trade band
            thr = p * np.abs(base).mean()
            move = np.abs(base - prev) > thr
            out = np.where(move, base, prev)      # 未过阈值的名字保持不动
        out = out - out.mean()
        g0, g1 = np.abs(base).sum(), np.abs(out).sum()
        out = out * g0 / g1 if (g1 > 1e-12 and g0 > 0) else base
        if prev.std() > 1e-12 and out.std() > 1e-12:
            c = np.corrcoef(prev, out)[0, 1]
            if np.isfinite(c):
                _ST["pers"].append(c)
    _ST["prev"][:] = 0.0
    _ST["prev"][m] = out
    _ST["have"] = True
    return out


def run(cost):
    _ST.update(prev=np.zeros(NMAX), have=False)
    RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
    RF.COST_BPS = cost
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=KING, s2=S2, weights=dict(LIVE_W), verbose=False)
    return {"ic": float(np.mean([o["per_year"][y]["mean_rank_ic"] for y in o["per_year"]])),
            "sh": float(o["avg_net_of_cost_sharpe"]),
            "turn": float(o["netting"]["net_turn_ann"])}


RF._SRC, RF._SRC_KEY = None, None
RF.COST_BPS = COSTS[1]
src = RF.get_src(None, KING, S2)
raw = {c: run(c) for c in COSTS}
print(f"[基线] IC {raw[3.63]['ic']:.5f} 毛 {raw[0.001]['sh']:+.3f} "
      f"@3.63 {raw[3.63]['sh']:+.3f} @5.8 {raw[5.8]['sh']:+.3f} turn {raw[3.63]['turn']:.0f}", flush=True)
SC.SignalChain.shape_position = patched
SC.SignalChain.leg_positions = patched_lp
_ST.update(mode="off")
c = run(COSTS[1])
ok = abs(c["ic"] - raw[3.63]["ic"]) < 1e-12 and abs(c["sh"] - raw[3.63]["sh"]) < 1e-12
print(f"[有效性] off 臂逐位复现: {'✓' if ok else '★FAIL'}", flush=True)
if not ok:
    sys.exit(1)

out = {"baseline": {str(k): v for k, v in raw.items()}, "arms": {}}
print("\n 族      参数   IC        ΔIC     换手   成本%/年  毛夏普  Sh@3.63  Sh@5.8  书lag1", flush=True)
for mode, ps in (("ema", [0.10, 0.07, 0.05, 0.03]), ("band", [0.25, 0.5, 0.8, 1.2, 2.0])):
    for p in ps:
        _ST.update(mode=mode, p=p, pers=[])
        r = {}
        for cc in COSTS:
            _ST.update(pers=[])
            r[cc] = run(cc)
        pers = float(np.mean(_ST["pers"])) if _ST["pers"] else float("nan")
        dic = r[3.63]["ic"] / raw[3.63]["ic"] - 1
        cp = r[3.63]["turn"] * 3.63 * 1e-4 * 100
        out["arms"][f"{mode}_{p}"] = {"mode": mode, "param": p, "ic": r[3.63]["ic"],
                                      "d_ic_pct": round(dic * 100, 2), "turn": r[3.63]["turn"],
                                      "cost_pct_yr": round(cp, 2), "gross_sh": r[0.001]["sh"],
                                      "sh363": r[3.63]["sh"], "sh58": r[5.8]["sh"],
                                      "book_lag1": round(pers, 4)}
        print(f" {mode:5s} {p:6.2f}  {r[3.63]['ic']:.5f} {dic*100:+6.1f}% {r[3.63]['turn']:6.0f} "
              f"{cp:8.2f}  {r[0.001]['sh']:+6.3f} {r[3.63]['sh']:+8.3f} {r[5.8]['sh']:+7.3f}  "
              f"{pers:.3f}", flush=True)

b = max(out["arms"].values(), key=lambda v: v["sh363"])
print(f"\n★ 全网格最优: {b['mode']} p={b['param']}  Sh@3.63 {b['sh363']:+.3f} "
      f"(基线 {raw[3.63]['sh']:+.3f}, Δ {b['sh363']-raw[3.63]['sh']:+.3f})  "
      f"Sh@5.8 {b['sh58']:+.3f}  IC {b['d_ic_pct']:+.1f}%  换手 {raw[3.63]['turn']:.0f}→{b['turn']:.0f}",
      flush=True)
json.dump(out, open("/tmp/RESULT_persistence_curve2.json", "w"), indent=1)
print("→ /tmp/RESULT_persistence_curve2.json", flush=True)
