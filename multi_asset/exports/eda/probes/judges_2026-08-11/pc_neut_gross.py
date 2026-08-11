"""PROPOSAL 00 §9 附测 —— 把【机械成本】与【alpha 效应】分开。

主实验在 3.63/5.8 两档上判, 基线本身已是净负(−0.370) ⇒ 全部读数是"比谁亏得少", 且
伙伴臂证明投影操作自带 ~−0.27 夏普的机械代价。**框架的可证伪预测在毛口径上**:
N_eff^book 2.79 → 11.94(4.3×) ⇒ 基本法则预测毛夏普 ~2.1 → ~3.9。
本脚本在 cost≈0 上直接测这条预测。predicted-vs-measured 不符 ⇒ 框架的 breadth 项不适用, 我错。
"""
import sys, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
import torch; torch.backends.mkldnn.enabled = False
exec(open("/tmp/pc_neutralize.py").read().split("RF._SRC, RF._SRC_KEY = None, None")[0])  # 复用装置

RF._SRC, RF._SRC_KEY = None, None
RF.COST_BPS = 0.001
src = RF.get_src(None, KING, S2)


def run0():
    RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
    RF.COST_BPS = 0.001                      # ≈ 零成本(不设 0 以免除零)
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=KING, s2=S2, weights=dict(LIVE_W), verbose=False)
    return (float(np.mean([o["per_year"][y]["mean_rank_ic"] for y in o["per_year"]])),
            float(o["avg_net_of_cost_sharpe"]), float(o["netting"]["net_turn_ann"]))

ic_b, sh_b, tu_b = run0()
print(f"[毛口径 cost≈0] 基线(未打补丁): IC {ic_b:.5f}  毛夏普 {sh_b:+.3f}  turn {tu_b:.0f}", flush=True)

SC.SignalChain.shape_position = patched
SC.SignalChain.leg_positions = patched_lp
out = {"gross_baseline": {"ic": ic_b, "sharpe": sh_b, "turn": tu_b}, "arms": {}}

_ST.update(k=0, mode="pc")
ic0, sh0, _ = run0()
ok = abs(sh0 - sh_b) < 1e-12 and abs(ic0 - ic_b) < 1e-12
print(f"[有效性] k=0 逐位复现: {'✓' if ok else '★FAIL'}", flush=True)
out["validity_k0_bitwise"] = bool(ok)

for tag, k, mode, seed in (("pc_k1", 1, "pc", None), ("pc_k3", 3, "pc", None),
                           ("pc_k5", 5, "pc", None), ("rand_k3_PARTNER", 3, "rand", 20260806)):
    _ST.update(k=k, mode=mode, n_treated=0, n_skipped=0, samples=[],
               rng=np.random.default_rng(seed) if seed else None)
    ic, sh, tu = run0()
    ne = neff_book(_ST["samples"])
    # 基本法则的预测: IR = IC × √(514 × N_eff)
    pred = ic * np.sqrt(514 * ne) if np.isfinite(ne) else float("nan")
    out["arms"][tag] = {"ic": ic, "gross_sharpe": sh, "turn": tu, "n_eff_book": round(ne, 2),
                        "d_gross_sharpe": round(sh - sh_b, 3),
                        "fundamental_law_pred": round(pred, 2)}
    print(f"  {tag:16s}: IC {ic:.5f}  毛夏普 {sh:+.3f} ({sh-sh_b:+.3f})  N_eff {ne:5.2f}  "
          f"turn {tu:.0f}  |  基本法则预测 IR={pred:.2f}", flush=True)

pb = ic_b * np.sqrt(514 * 2.79)
out["gross_baseline"]["fundamental_law_pred"] = round(pb, 2)
print(f"\n基线的基本法则预测 IR = {pb:.2f}  vs 实测毛夏普 {sh_b:+.3f}", flush=True)
json.dump(out, open("/tmp/RESULT_pc_gross.json", "w"), indent=1)
print("→ /tmp/RESULT_pc_gross.json", flush=True)
