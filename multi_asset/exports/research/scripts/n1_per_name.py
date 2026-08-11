"""N1 —— 逐名自适应平滑, 逐字执行 PREREG_N1_per_name_smoothing_2026-08-06.md。

a_i = clip(a_base × (dvol_i/median dvol)^γ, 0.001, 1.0)
判据: 两条【前沿】在同换手处比, 不是两个点比。随机代理对照臂若同样好 ⇒ 全表作废。
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
BASES = [0.30, 0.15, 0.07, 0.03, 0.01]
_ORIG = SC.SignalChain.shape_position
_ORIG_LP = SC.SignalChain.leg_positions
NMAX = 200
_ST = {"base": 1.0, "gamma": 0.0, "rand": False, "t": None, "idx": None,
       "prev": np.zeros(NMAX), "have": False, "rng": None}


def patched_lp(self, t):
    o, m = _ORIG_LP(self, t); _ST["t"] = int(t); _ST["idx"] = m; return o, m


def patched(self, combo):
    base = _ORIG(self, combo)
    ab = _ST["base"]
    if ab >= 1.0:
        return base                                   # ★ 逐位回落
    t, m = _ST["t"], _ST["idx"]
    if t is None or m is None or len(base) != len(m):
        return base
    g = _ST["gamma"]
    if g == 0.0:
        a = np.full(len(m), ab)
    else:
        d = DVOL[t, m].astype(np.float64)
        fin = np.isfinite(d) & (d > 0)
        if fin.sum() < 10:
            a = np.full(len(m), ab)
        else:
            med = np.median(d[fin])
            d = np.where(fin, d, med)
            if _ST["rand"]:
                d = d[_ST["rng"].permutation(len(d))]   # ★ 伙伴检查: 打乱成本代理
            a = np.clip(ab * np.power(d / med, g), 0.001, 1.0)
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
    _ST.update(prev=np.zeros(NMAX), have=False, rng=np.random.default_rng(20260806))
    RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
    RF.COST_BPS = c
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=KING, s2=S2, weights=dict(LIVE_W), verbose=False)
    return float(o["avg_net_of_cost_sharpe"]), float(o["netting"]["net_turn_ann"])


RF._SRC, RF._SRC_KEY = None, None
RF.COST_BPS = 3.63
src = RF.get_src(None, KING, S2)
DVOL = src.CH[:, :, src.ch.index("dvol_24h")]
print(f"[代理] dvol_24h 有限率 {np.isfinite(DVOL).mean():.3f}", flush=True)
b0 = run(3.63)
SC.SignalChain.shape_position = patched
SC.SignalChain.leg_positions = patched_lp
_ST.update(base=1.0)
c0 = run(3.63)
ok = abs(c0[0] - b0[0]) < 1e-12
print(f"[有效性] a_base=1 逐位复现: {'✓' if ok else '★FAIL'} (基线 {b0[0]:+.3f} turn {b0[1]:.0f})",
      flush=True)
if not ok:
    sys.exit(1)

res = {}
for tag, gam, rnd in (("均匀 γ=0", 0.0, False), ("成本感知 γ=0.5", 0.5, False),
                      ("成本感知 γ=1.0", 1.0, False), ("★随机代理 γ=1.0", 1.0, True)):
    print(f"\n[{tag}]  a_base   换手   毛夏普   Sh@3.63   Sh@5.8", flush=True)
    rows = []
    for ab in BASES:
        _ST.update(base=ab, gamma=gam, rand=rnd)
        r = {c: run(c) for c in COSTS}
        rows.append({"a_base": ab, "turn": r[3.63][1], "gross": r[0.001][0],
                     "sh363": r[3.63][0], "sh58": r[5.8][0]})
        print(f"           {ab:5.2f}  {r[3.63][1]:6.0f}  {r[0.001][0]:+6.3f}  "
              f"{r[3.63][0]:+7.3f}  {r[5.8][0]:+7.3f}", flush=True)
    res[tag] = rows

# ★ 同换手比较: 对每个自适应点, 在均匀族上线性内插出同换手的净夏普
uni = sorted(res["均匀 γ=0"], key=lambda r: r["turn"])
ut = [r["turn"] for r in uni]; us = [r["sh363"] for r in uni]
print("\n★ 同换手比较(判据所在): 自适应 − 均匀(同换手内插)", flush=True)
summary = {}
for tag in ("成本感知 γ=0.5", "成本感知 γ=1.0", "★随机代理 γ=1.0"):
    ds = []
    for r in res[tag]:
        if ut[0] <= r["turn"] <= ut[-1]:
            u = float(np.interp(r["turn"], ut, us))
            ds.append((r["turn"], round(r["sh363"] - u, 3)))
    summary[tag] = ds
    best = max([d for _, d in ds]) if ds else float("nan")
    print(f"  {tag:16s}: " + "  ".join(f"turn{t:.0f}:{d:+.3f}" for t, d in ds) +
          f"   最大 {best:+.3f}", flush=True)

adapt = max([d for _, d in summary.get("成本感知 γ=1.0", [])] +
            [d for _, d in summary.get("成本感知 γ=0.5", [])], default=float("nan"))
rand = max([d for _, d in summary.get("★随机代理 γ=1.0", [])], default=float("nan"))
verdict = ("全表作废: 随机代理同样好" if np.isfinite(rand) and rand >= adapt - 0.02 else
           "有效" if adapt >= 0.10 else "杀: 均匀 EMA 已够")
print(f"\n★ 判决: 自适应最大增益 {adapt:+.3f} | 随机代理最大 {rand:+.3f} ⇒ {verdict}", flush=True)
json.dump({"arms": res, "matched_turnover_delta": summary, "verdict": verdict},
          open("/tmp/RESULT_n1_per_name.json", "w"), indent=1, ensure_ascii=False)
