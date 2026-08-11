"""N6 —— 视界匹配, 逐字执行 PREREG_N6_horizon_match_2026-08-06.md。
h0(YR4) vs h2(YR24): 同一次训练/同一共享干/同一锚点, 唯一差别是头的目标绑定。
远端只算, 结果走 stdout。"""
import sys, glob, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
import torch; torch.backends.mkldnn.enabled = False
from engine import replay_fullhist as RF
from engine import signal_chain as SC

PH = f"{MA}/exports/train/wideA_perhead_v1"
KREF = "/tmp/king_pred_newgen.npz"                      # 只借它的形状与 ts
S2REF = "/tmp/s2_pred_newgen.npz"
COSTS = [0.001, 3.63]
SPEEDS = [1.00, 0.03]
HEADS = {"h0_YR4": 0, "h2_YR24": 2}

kref = np.load(KREF, allow_pickle=True)
NROW, NCOL = kref["king_pred"].shape
print(f"[形状] 参照 king_pred {NROW}×{NCOL}", flush=True)

# ── 拼 5 折的测试行 ──
stitched = {}
cover = None
for tag, hi in HEADS.items():
    acc = np.full((NROW, NCOL), np.nan, np.float64)
    nfill = 0
    for f in sorted(glob.glob(f"{PH}/fold_*_head_scores.npz")):
        d = np.load(f)
        sc, rows = d["scores"], d["te_rows"]
        keep = rows[rows < NROW]
        acc[keep] = sc[keep, :, hi]
        nfill += len(keep)
    fin = np.isfinite(acc).any(1)
    stitched[tag] = acc
    if cover is None:
        cover = fin
    print(f"[{tag}] 填入 {nfill} 行, 有预测的行 {int(fin.sum())} ({fin.mean():.3f})", flush=True)
    assert np.array_equal(fin, cover), "两臂锚点覆盖不同 ⇒ 对照失效"
print(f"[对照] 两臂锚点覆盖【逐位相同】✓", flush=True)

for tag, arr in stitched.items():
    np.savez(f"/tmp/n6_{tag}.npz", king_pred=arr.astype(np.float32), ts=kref["ts"])
z = np.load(S2REF, allow_pickle=True)
np.savez("/tmp/n6_s2zero.npz", s2_pred=np.zeros((NROW, NCOL), np.float32), ts=z["ts"])

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


SC.SignalChain.shape_position = patched
SC.SignalChain.leg_positions = patched_lp
W = {"king": 1.0, "s2": 0.0, "funding": 0.0, "size": 0.0}


def run(kpath, a, c):
    _ST.update(a=a, prev=np.zeros(NMAX), have=False)
    RF._SRC, RF._SRC_KEY = None, None
    RF.COST_BPS = c
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=kpath, s2="/tmp/n6_s2zero.npz", weights=dict(W), verbose=False)
    return {"sh": float(o["avg_net_of_cost_sharpe"]), "turn": float(o["netting"]["net_turn_ann"]),
            "ic": float(np.mean([o["per_year"][y]["mean_rank_ic"] for y in o["per_year"]])),
            "anchors": int(o.get("anchors", 0)),
            "per_year": {int(y): float(o["per_year"][y]["net_of_cost_sharpe"]) for y in o["per_year"]}}


res = {}
print("\n 头        a      锚数   IC       毛夏普   Sh@3.63   换手", flush=True)
for tag in HEADS:
    for a in SPEEDS:
        r = {c: run(f"/tmp/n6_{tag}.npz", a, c) for c in COSTS}
        res[f"{tag}_a{a}"] = {"ic": r[3.63]["ic"], "gross": r[0.001]["sh"], "sh363": r[3.63]["sh"],
                              "turn": r[3.63]["turn"], "anchors": r[3.63]["anchors"],
                              "per_year": r[3.63]["per_year"]}
        print(f" {tag:9s} {a:4.2f}  {r[3.63]['anchors']:5d}  {r[3.63]['ic']:.5f}  "
              f"{r[0.001]['sh']:+6.3f}  {r[3.63]['sh']:+7.3f}  {r[3.63]['turn']:6.0f}", flush=True)

for a in SPEEDS:
    d_gross = res[f"h2_YR24_a{a}"]["gross"] - res[f"h0_YR4_a{a}"]["gross"]
    d_net = res[f"h2_YR24_a{a}"]["sh363"] - res[f"h0_YR4_a{a}"]["sh363"]
    print(f"\n a={a:.2f}: Δ毛(h2−h0) = {d_gross:+.3f}   Δ净@3.63 = {d_net:+.3f}", flush=True)
    if a == 0.03:
        v = ("视界匹配是真杠杆" if d_gross >= 0.20 and d_net > 0 else
             "反向: 4h 目标更适合慢书" if d_gross <= -0.20 else "杀: 视界匹配不改变天花板")
        print(f" ★ 主判(慢书毛夏普): {v}", flush=True)
        res["verdict"] = v
print("\nJSON_BEGIN"); print(json.dumps(res)); print("JSON_END")
