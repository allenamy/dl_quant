"""E1c 验证 —— 三个能推翻 E1/E1b 结论的检查, 全部先写判读再看数。

★ 检查①【静态组合】: a→0 的极限若只是一个几乎不变的组合(永远多低波/空高波), 那它是风险溢价
   而非慢 alpha —— 容量、稳健性、可复制性全然不同, 且"世界模型能提供持续性"的推论作废。
   判读: 若 lag-180 锚(≈1 月)权重相关 > 0.95 且年内符号翻转名字 < 5% ⇒ 静态组合, 结论降级。
★ 检查②【逐年稳健】: +1.63 是不是一年撑起来的。判读: 若任一年 ΔSharpe < 0 ⇒ 降为"regime 依赖"。
★ 检查③【网格是否真的到边】: 继续外延 a∈{0.02,0.01}。
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
_ST = {"a": 1.0, "idx": None, "prev": np.zeros(NMAX), "have": False, "hist": [], "keep": False}


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
    if not _ST["have"]:
        out = base
    else:
        out = (1.0 - a) * prev + a * base
        out = out - out.mean()
        g0, g1 = np.abs(base).sum(), np.abs(out).sum()
        out = out * g0 / g1 if (g1 > 1e-12 and g0 > 0) else base
    _ST["prev"][:] = 0.0
    _ST["prev"][m] = out
    _ST["have"] = True
    if _ST["keep"]:
        full = np.zeros(NMAX); full[m] = out
        _ST["hist"].append(full)
    return out


def run(cost, keep=False):
    _ST.update(prev=np.zeros(NMAX), have=False, keep=keep, hist=[])
    RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
    RF.COST_BPS = cost
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=KING, s2=S2, weights=dict(LIVE_W), verbose=False)
    return {"sh": float(o["avg_net_of_cost_sharpe"]),
            "turn": float(o["netting"]["net_turn_ann"]),
            "ic": float(np.mean([o["per_year"][y]["mean_rank_ic"] for y in o["per_year"]])),
            "per_year_sh": {int(y): float(o["per_year"][y]["net_of_cost_sharpe"]) for y in o["per_year"]}}


RF._SRC, RF._SRC_KEY = None, None
RF.COST_BPS = COSTS[1]
src = RF.get_src(None, KING, S2)
base = {c: run(c) for c in COSTS}
print(f"[基线] @3.63 {base[3.63]['sh']:+.3f}  逐年 {base[3.63]['per_year_sh']}", flush=True)
SC.SignalChain.shape_position = patched
SC.SignalChain.leg_positions = patched_lp
_ST.update(a=1.0)
chk = run(COSTS[1])
ok = abs(chk["sh"] - base[3.63]["sh"]) < 1e-12
print(f"[有效性] a=1 逐位复现: {'✓' if ok else '★FAIL'}", flush=True)
if not ok:
    sys.exit(1)

out = {"baseline": {str(c): base[c] for c in COSTS}}
print("\n【检查③ 网格外延 + 检查② 逐年】", flush=True)
rows = {}
for a in [0.03, 0.02, 0.01]:
    _ST.update(a=a)
    r = {c: run(c) for c in COSTS}
    d = {y: round(r[3.63]["per_year_sh"][y] - base[3.63]["per_year_sh"][y], 2)
         for y in r[3.63]["per_year_sh"]}
    neg = [y for y, v in d.items() if v < 0]
    rows[a] = {"sh363": r[3.63]["sh"], "sh58": r[5.8]["sh"], "gross": r[0.001]["sh"],
               "turn": r[3.63]["turn"], "ic": r[3.63]["ic"],
               "per_year_sh": r[3.63]["per_year_sh"], "d_per_year": d,
               "years_worse": neg}
    print(f"  a={a:.2f} turn {r[3.63]['turn']:5.0f} 毛 {r[0.001]['sh']:+.3f} "
          f"@3.63 {r[3.63]['sh']:+.3f} @5.8 {r[5.8]['sh']:+.3f} | 逐年Δ {d} "
          f"{'★有年份变差: ' + str(neg) if neg else '全年份改善 ✓'}", flush=True)
out["arms"] = {str(k): v for k, v in rows.items()}

print("\n【检查① 静态组合?】(a=0.03 的书, 权重序列)", flush=True)
_ST.update(a=0.03)
run(3.63, keep=True)
H = np.array(_ST["hist"])
print(f"  采到 {H.shape[0]} 个锚的权重", flush=True)
res1 = {}
for lag in (1, 30, 90, 180, 360):
    if H.shape[0] <= lag:
        continue
    cs = []
    for i in range(0, H.shape[0] - lag, max(1, (H.shape[0] - lag) // 400)):
        a_, b_ = H[i], H[i + lag]
        m = (np.abs(a_) > 1e-12) | (np.abs(b_) > 1e-12)
        if m.sum() > 20 and a_[m].std() > 1e-12 and b_[m].std() > 1e-12:
            c = np.corrcoef(a_[m], b_[m])[0, 1]
            if np.isfinite(c):
                cs.append(c)
    res1[f"lag_{lag}"] = round(float(np.mean(cs)), 4) if cs else None
    print(f"  lag-{lag:3d} 锚 (≈{lag*4/24:5.1f} 天): 权重相关 {res1[f'lag_{lag}']}", flush=True)
# 年内符号翻转比例
flip = []
step = 2190 // 6                       # 约 1 年的锚数(替代: 用 H 的 1/4 跨度)
L = min(H.shape[0] // 3, 1500)
for i in range(0, H.shape[0] - L, max(1, (H.shape[0] - L) // 200)):
    a_, b_ = H[i], H[i + L]
    m = (np.abs(a_) > 1e-10) & (np.abs(b_) > 1e-10)
    if m.sum() > 20:
        flip.append(float((np.sign(a_[m]) != np.sign(b_[m])).mean()))
res1["sign_flip_frac_over_long_span"] = round(float(np.mean(flip)), 4) if flip else None
res1["span_anchors"] = int(L)
print(f"  跨 {L} 锚 (≈{L*4/24:.0f} 天) 的符号翻转比例: {res1['sign_flip_frac_over_long_span']}", flush=True)
static = (res1.get("lag_180") or 0) > 0.95 and (res1.get("sign_flip_frac_over_long_span") or 1) < 0.05
res1["verdict_static_portfolio"] = bool(static)
print(f"  ⇒ {'★★ 静态组合 —— 结论降级为风险溢价' if static else '不是静态组合 ✓ 权重确在演化'}", flush=True)
out["static_check"] = res1
json.dump(out, open("/tmp/RESULT_persistence_verify.json", "w"), indent=1)
print("\n→ /tmp/RESULT_persistence_verify.json", flush=True)
