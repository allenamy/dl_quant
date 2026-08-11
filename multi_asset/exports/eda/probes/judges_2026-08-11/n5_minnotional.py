"""N5 —— minNotional × 账户规模 × 收割速度, 逐字执行 PREREG_N5_minnotional_scale_2026-08-06.md。
远端只算, 结果走 stdout。"""
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
COST = 3.63
GROSSES = [4400, 10000, 20000, 44000]      # NAV 2200/5000/10000/22000 × 2x
MINNOTS = [5.0, 20.0]
SPEEDS = [1.00, 0.03]
_ORIG = SC.SignalChain.shape_position
_ORIG_LP = SC.SignalChain.leg_positions
NMAX = 200
_ST = {"a": 1.0, "idx": None, "prev": np.zeros(NMAX), "have": False,
       "gross": None, "mn": None, "ndrop": [], "gdrop": []}


def patched_lp(self, t):
    o, m = _ORIG_LP(self, t); _ST["idx"] = m; return o, m


def patched(self, combo):
    base = _ORIG(self, combo)
    m = _ST["idx"]
    a = _ST["a"]
    out = base
    if a < 1.0 and m is not None and len(base) == len(m):
        prev = _ST["prev"][m]
        if _ST["have"]:
            out = (1.0 - a) * prev + a * base
            out = out - out.mean()
            g0, g1 = np.abs(base).sum(), np.abs(out).sum()
            out = out * g0 / g1 if (g1 > 1e-12 and g0 > 0) else base
    # ── minNotional: |w|×GROSS < MIN ⇒ 该腿不存在, 剩余名字承接敞口 ──
    if _ST["gross"] is not None and m is not None and len(out) == len(m):
        g_before = np.abs(out).sum()
        small = np.abs(out) * _ST["gross"] < _ST["mn"]
        if small.any() and (~small).sum() >= 5:
            _ST["ndrop"].append(int(small.sum()))
            _ST["gdrop"].append(float(np.abs(out[small]).sum() / max(g_before, 1e-12)))
            out = np.where(small, 0.0, out)
            out = out - out[~small].mean() * (~small)          # 只在存活名字上再中性化
            out = np.where(small, 0.0, out)
            g1 = np.abs(out).sum()
            if g1 > 1e-12:
                out = out * g_before / g1                       # ★ 归一【回原毛敞口】
            else:
                out = base
    if a < 1.0 and m is not None and len(out) == len(m):
        _ST["prev"][:] = 0.0; _ST["prev"][m] = out; _ST["have"] = True
    return out


def run(a, gross, mn):
    _ST.update(a=a, gross=gross, mn=mn, prev=np.zeros(NMAX), have=False, ndrop=[], gdrop=[])
    RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
    RF.COST_BPS = COST
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=KING, s2=S2, weights=dict(LIVE_W), verbose=False)
    return {"sh": float(o["avg_net_of_cost_sharpe"]), "turn": float(o["netting"]["net_turn_ann"]),
            "n_drop": float(np.mean(_ST["ndrop"])) if _ST["ndrop"] else 0.0,
            "g_drop_pct": float(np.mean(_ST["gdrop"]) * 100) if _ST["gdrop"] else 0.0}


RF._SRC, RF._SRC_KEY = None, None
RF.COST_BPS = COST
src = RF.get_src(None, KING, S2)
SC.SignalChain.shape_position = patched
SC.SignalChain.leg_positions = patched_lp
ref = {}
for a in SPEEDS:
    r = run(a, None, None)                                     # 无 minNotional = 既有口径
    ref[a] = r["sh"]
    print(f"[无 minNotional] a={a:.2f}: Sh {r['sh']:+.3f} turn {r['turn']:.0f}", flush=True)
ok = abs(ref[1.00] - (-0.370)) < 1e-9
print(f"[有效性] a=1 无约束复现 −0.370: {'OK' if ok else 'FAIL ' + str(ref[1.00])}", flush=True)

out = {"ref": {str(k): v for k, v in ref.items()}, "grid": {}}
for mn in MINNOTS:
    print(f"\n[MIN_NOTIONAL = {mn:.0f} USDT]  GROSS   a=1.00 Sh(Δ)   掉名/锚  掉毛%  |  "
          f"a=0.03 Sh(Δ)   掉名/锚  掉毛%", flush=True)
    for g in GROSSES:
        row = {}
        for a in SPEEDS:
            row[a] = run(a, g, mn)
        out["grid"][f"mn{mn:.0f}_g{g}"] = {str(a): row[a] for a in SPEEDS}
        print(f"                        {g:6d}  {row[1.00]['sh']:+7.3f}"
              f"({row[1.00]['sh']-ref[1.00]:+.3f})  {row[1.00]['n_drop']:6.1f}  "
              f"{row[1.00]['g_drop_pct']:5.2f}  |  {row[0.03]['sh']:+7.3f}"
              f"({row[0.03]['sh']-ref[0.03]:+.3f})  {row[0.03]['n_drop']:6.1f}  "
              f"{row[0.03]['g_drop_pct']:5.2f}", flush=True)
print("\nJSON_BEGIN"); print(json.dumps(out)); print("JSON_END")
