"""E1d —— 对 E1/E1b 最狠的反驳测试: 慢下来之后, 赚钱的还是 DL 吗?

★ 反驳假说: funding 是 carry 因子, 天然多日尺度; DL 腿预测的是 4h。把书平滑到 5 天持有,
   funding 只会更好、DL 只会更差 ⇒ **a=0.03 的 +1.26 可能几乎全部来自 funding carry,
   而 DL 腿在任何速度下都不经济。** 若成立, 结论从"慢 alpha 值钱"变成"这个策略的真实边是 carry,
   DL 是负担" —— 意义完全不同, 且对研究纲领的含义相反。
★ 判读(先写): 在 a=0.03 上, 若【去掉 funding 腿】后净夏普跌破 +0.3 ⇒ 反驳成立, DL 不经济;
   若仍 ≥ +0.8 ⇒ DL 腿在慢速下确实赚钱, 原结论稳。中间 ⇒ 按比例归因, 两条都记。
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
COSTS = [0.001, 3.63]
_ORIG = SC.SignalChain.shape_position
_ORIG_LP = SC.SignalChain.leg_positions
NMAX = 200
_ST = {"a": 1.0, "idx": None, "prev": np.zeros(NMAX), "have": False}


def patched_lp(self, t):
    out, m = _ORIG_LP(self, t)
    _ST["idx"] = m
    return out, m


def patched(self, combo):
    base = _ORIG(self, combo)
    a = _ST["a"]
    if a >= 1.0:
        return base
    m = _ST["idx"]
    if m is None or len(base) != len(m):
        return base
    prev = _ST["prev"][m]
    out = base if not _ST["have"] else (1.0 - a) * prev + a * base
    if _ST["have"]:
        out = out - out.mean()
        g0, g1 = np.abs(base).sum(), np.abs(out).sum()
        out = out * g0 / g1 if (g1 > 1e-12 and g0 > 0) else base
    _ST["prev"][:] = 0.0; _ST["prev"][m] = out; _ST["have"] = True
    return out


def run(cost, w):
    _ST.update(prev=np.zeros(NMAX), have=False)
    RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
    RF.COST_BPS = cost
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=KING, s2=S2, weights=dict(w), verbose=False)
    return {"sh": float(o["avg_net_of_cost_sharpe"]),
            "turn": float(o["netting"]["net_turn_ann"]),
            "ic": float(np.mean([o["per_year"][y]["mean_rank_ic"] for y in o["per_year"]]))}


RF._SRC, RF._SRC_KEY = None, None
RF.COST_BPS = COSTS[1]
src = RF.get_src(None, KING, S2)
SC.SignalChain.shape_position = patched
SC.SignalChain.leg_positions = patched_lp

LIVE = {"king": .5952380952380952, "s2": .20238095238095238,
        "funding": .20238095238095238, "size": 0.0}
DL_ONLY = {"king": .5952380952380952 / .7976190476190477,
           "s2": .20238095238095238 / .7976190476190477, "funding": 0.0, "size": 0.0}
FUND_ONLY = {"king": 0.0, "s2": 0.0, "funding": 1.0, "size": 0.0}
KING_ONLY = {"king": 1.0, "s2": 0.0, "funding": 0.0, "size": 0.0}

out = {}
print(" 腿配置        a      turn   毛夏普   Sh@3.63", flush=True)
for tag, w in (("线上三腿", LIVE), ("仅DL(king+s2)", DL_ONLY),
               ("仅funding", FUND_ONLY), ("仅king", KING_ONLY)):
    for a in (1.0, 0.03):
        _ST.update(a=a)
        r = {c: run(c, w) for c in COSTS}
        out[f"{tag}_a{a}"] = {"turn": r[3.63]["turn"], "gross": r[0.001]["sh"],
                              "sh363": r[3.63]["sh"], "ic": r[3.63]["ic"]}
        print(f" {tag:14s} {a:4.2f}  {r[3.63]['turn']:6.0f}  {r[0.001]['sh']:+6.3f}  "
              f"{r[3.63]['sh']:+7.3f}", flush=True)

dl = out["仅DL(king+s2)_a0.03"]["sh363"]
verdict = ("反驳成立: DL 在任何速度下都不经济" if dl < 0.3 else
           "原结论稳: DL 腿慢速下确实赚钱" if dl >= 0.8 else "中间: 按比例归因")
out["_verdict"] = verdict
print(f"\n★ 仅 DL @ a=0.03 净夏普 = {dl:+.3f} ⇒ {verdict}", flush=True)
json.dump(out, open("/tmp/RESULT_leg_attribution.json", "w"), indent=1)
