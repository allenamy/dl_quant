"""持续性–成本 交换曲线 —— 给"世界模型"范式定价的最便宜实验。

★ 推理链: 实测成本 34.9%/年 vs 毛 alpha 29%/年, 成本是唯一 3-夏普量级的项。而世界模型/状态建模
   若真有优势, 其在【本项目】的兑现形式不是更高 IC(兑换率仅 +0.27 夏普/10%IC), 而是**更持续的
   信号**(状态缓变, 观测抖动) —— 持续性直接打在成本项上。
★ 本实验不训练任何模型: 对【现有预测】施加不同强度的时间平滑, 机械地买入持续性、卖出 IC,
   把整条交换曲线测出来。若曲线的净夏普最大值显著高于当前点 ⇒ 持续性值得买 ⇒ 任何能提高持续性的
   建模范式(SSM/状态/Koopman)就有了【被定价过的】上限。若曲线在当前点已近最优 ⇒ 整条范式在本项目
   的价值上限被封死, 省下数月。

w_t = (1-a)·w_{t-1} + a·w_t^raw  → 二次 demean → 归一到同毛敞口
a=1 ⇒ 逐位回落(有效性判据)
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
COSTS = [0.001, 3.63, 5.8]           # 毛 / 点估计 / CI 上界
ALPHAS = [1.0, 0.7, 0.5, 0.35, 0.25, 0.15]

_ORIG = SC.SignalChain.shape_position
_ORIG_LP = SC.SignalChain.leg_positions
NMAX = 200
_ST = {"a": 1.0, "t": None, "idx": None, "prev": np.zeros(NMAX), "have": False,
       "last_t": -1, "pers": [], "n": 0}


def patched_lp(self, t):
    out, m = _ORIG_LP(self, t)
    _ST["t"] = int(t); _ST["idx"] = m
    return out, m


def patched(self, combo):
    base = _ORIG(self, combo)
    a = _ST["a"]
    if a >= 1.0:
        return base                                   # ★ 逐位回落
    t, m = _ST["t"], _ST["idx"]
    if t is None or m is None or len(base) != len(m):
        return base
    prev = _ST["prev"][m]
    if not _ST["have"]:
        out = base
    else:
        out = (1.0 - a) * prev + a * base
        out = out - out.mean()
        g0, g1 = np.abs(base).sum(), np.abs(out).sum()
        if g1 > 1e-12 and g0 > 0:
            out = out * g0 / g1
        else:
            out = base
        # 机制回执: 实现出来的权重 lag-1 相关(不是信号的, 是【书的】)
        if prev.std() > 1e-12 and out.std() > 1e-12:
            c = np.corrcoef(prev, out)[0, 1]
            if np.isfinite(c):
                _ST["pers"].append(c)
    _ST["prev"][:] = 0.0
    _ST["prev"][m] = out
    _ST["have"] = True
    _ST["n"] += 1
    return out


def run(cost):
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
print(f"[未打补丁基线] IC {raw[COSTS[1]]['ic']:.5f}  毛夏普 {raw[0.001]['sh']:+.3f}  "
      f"Sh@3.63 {raw[3.63]['sh']:+.3f}  Sh@5.8 {raw[5.8]['sh']:+.3f}  turn {raw[3.63]['turn']:.0f}",
      flush=True)

SC.SignalChain.shape_position = patched
SC.SignalChain.leg_positions = patched_lp
out = {"baseline_unpatched": {str(c): raw[c] for c in COSTS}, "arms": {}}

_ST.update(a=1.0)
c1 = run(COSTS[1])
ok = abs(c1["ic"] - raw[COSTS[1]]["ic"]) < 1e-12 and abs(c1["sh"] - raw[COSTS[1]]["sh"]) < 1e-12
out["validity_a1_bitwise"] = bool(ok)
print(f"[有效性] a=1 逐位复现: {'✓' if ok else '★FAIL 全表作废'}", flush=True)
if not ok:
    sys.exit(1)

print("\n  a     半衰期   IC        ΔIC     换手     成本%/年  毛夏普   Sh@3.63   Sh@5.8   书lag1", flush=True)
for a in ALPHAS:
    _ST.update(a=a, prev=np.zeros(NMAX), have=False, pers=[], n=0)
    r = {}
    for c in COSTS:
        _ST.update(prev=np.zeros(NMAX), have=False, pers=[])
        r[c] = run(c)
    pers = float(np.mean(_ST["pers"])) if _ST["pers"] else float("nan")
    hl = (np.log(0.5) / np.log(1 - a)) if a < 1 else 0.0
    dic = r[COSTS[1]]["ic"] / raw[COSTS[1]]["ic"] - 1
    costpct = r[COSTS[1]]["turn"] * 3.63 * 1e-4 * 100
    out["arms"][f"a{a}"] = {"alpha": a, "half_life_anchors": round(float(hl), 2),
                            "ic": r[COSTS[1]]["ic"], "d_ic_pct": round(dic * 100, 2),
                            "turn": r[COSTS[1]]["turn"], "cost_pct_yr": round(costpct, 2),
                            "gross_sh": r[0.001]["sh"], "sh363": r[3.63]["sh"], "sh58": r[5.8]["sh"],
                            "book_lag1_persistence": round(pers, 4)}
    print(f" {a:4.2f}  {hl:6.2f}  {r[COSTS[1]]['ic']:.5f} {dic*100:+6.1f}%  "
          f"{r[COSTS[1]]['turn']:7.0f}  {costpct:7.2f}   {r[0.001]['sh']:+6.3f}  "
          f"{r[3.63]['sh']:+7.3f}  {r[5.8]['sh']:+7.3f}   {pers:.3f}", flush=True)

best = max(out["arms"].values(), key=lambda v: v["sh363"])
print(f"\n★ Sh@3.63 最优臂: a={best['alpha']} (半衰期 {best['half_life_anchors']:.1f} 锚 = "
      f"{best['half_life_anchors']*4:.0f}h)  净夏普 {best['sh363']:+.3f} "
      f"(基线 {raw[3.63]['sh']:+.3f}, Δ {best['sh363']-raw[3.63]['sh']:+.3f})  "
      f"IC 代价 {best['d_ic_pct']:+.1f}%  换手 {raw[3.63]['turn']:.0f}→{best['turn']:.0f}", flush=True)
json.dump(out, open("/tmp/RESULT_persistence_curve.json", "w"), indent=1)
print("→ /tmp/RESULT_persistence_curve.json", flush=True)
