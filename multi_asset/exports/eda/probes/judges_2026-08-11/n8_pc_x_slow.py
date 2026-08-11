"""N8 —— 去集中 × 慢书: 唯一没测过的组合。

★ 为什么它可能成立(而 PC 单独失败): PC 中性化在【快书】上失败, 是因为投影把换手从 961 推到 1030
   (+7%), 而快书每单位换手要付 3.63bps ⇒ 机械代价 −0.27~−0.51 吃掉了 +0.33 的毛增益。
   **慢书的换手基数只有 59–71 ⇒ 同样比例的换手增加, 绝对成本小一个数量级。**
   ⇒ 两个干预在快书上互相打架, 在慢书上可能【互补】。这是我自己两个实验的交叉引用, 没人测过。

★ 判读预写:
   净夏普(3.63) 相对"仅慢书"提升 ≥ +0.15 且毛夏普同向上升 ⇒ 互补成立, 出提案;
   |Δ| < 0.15 ⇒ 杀(去集中在任何速度下都不值);
   净额下降 ⇒ 反向, 记录并关闭该组合。
★ 伙伴检查: 随机方向 k=3 臂必须给出显著更小的增益, 否则增益来自"任何投影"而非去集中。
"""
import sys, json, time
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
WIN_ROWS, EPOCH, NPC = 120 * 24, 168, 5

z = np.load(f"{MA}/exports/wide_dl_full_corrfund_causal_0731.npz", allow_pickle=True)
Y4 = z["Y4"].astype(np.float64); CL4 = z["CL4"].astype(bool); MEM = z["MEMBER110"].astype(bool)
T, N = Y4.shape
Rm = np.where(MEM & CL4, Y4, np.nan)
Rd = Rm - np.nanmean(Rm, axis=1, keepdims=True)
VP, t0 = {}, time.time()
for e in range(WIN_ROWS, T, EPOCH):
    W = Rd[max(0, e - WIN_ROWS):e]
    W = W[np.isfinite(W).sum(1) >= 20]
    if W.shape[0] < 100:
        continue
    ok = np.isfinite(W).mean(0) > 0.8
    Wc = W[:, ok]; Wc = Wc[np.isfinite(Wc).all(1)]
    if Wc.shape[0] < 60 or ok.sum() < 20:
        continue
    lam, V = np.linalg.eigh(np.cov(Wc, rowvar=False))
    o = np.argsort(lam)[::-1]; V = V[:, o]
    Vf = np.zeros((N, NPC))
    Vf[np.where(ok)[0][:, None], np.arange(NPC)[None, :]] = V[:, :NPC]
    VP[e] = Vf
EK = np.array(sorted(VP))
print(f"[因果主成分] {len(VP)} epoch, {time.time()-t0:.0f}s", flush=True)

_ORIG = SC.SignalChain.shape_position
_ORIG_LP = SC.SignalChain.leg_positions
NMAX = 200
_ST = {"a": 1.0, "k": 0, "rand": False, "t": None, "idx": None,
       "prev": np.zeros(NMAX), "have": False, "rng": None}


def patched_lp(self, t):
    o, m = _ORIG_LP(self, t); _ST["t"] = int(t); _ST["idx"] = m; return o, m


def patched(self, combo):
    base = _ORIG(self, combo)
    t, m, a, k = _ST["t"], _ST["idx"], _ST["a"], _ST["k"]
    if m is None or len(base) != len(m):
        return base
    out = base
    # ① 去集中(先做: 它是对"当期目标"的修正)
    if k > 0 and t is not None:
        j = np.searchsorted(EK, t, side="right") - 1
        if j >= 0:
            B = VP[EK[j]][m][:, :k]
            if _ST["rand"]:
                B = _ST["rng"].normal(size=B.shape)
            q, _ = np.linalg.qr(B)
            if np.isfinite(q).all():
                o2 = out - q @ (q.T @ out)
                o2 = o2 - o2.mean()
                g0, g1 = np.abs(out).sum(), np.abs(o2).sum()
                if g1 > 1e-12 and g0 > 0:
                    out = o2 * g0 / g1
    # ② EMA(后做: 它是对"仓位路径"的平滑)
    if a < 1.0:
        prev = _ST["prev"][m]
        if _ST["have"]:
            o3 = (1.0 - a) * prev + a * out
            o3 = o3 - o3.mean()
            g0, g1 = np.abs(out).sum(), np.abs(o3).sum()
            out = o3 * g0 / g1 if (g1 > 1e-12 and g0 > 0) else out
        _ST["prev"][:] = 0.0; _ST["prev"][m] = out; _ST["have"] = True
    return out


SC.SignalChain.shape_position = patched
SC.SignalChain.leg_positions = patched_lp


def run(a, k, rand, c):
    _ST.update(a=a, k=k, rand=rand, prev=np.zeros(NMAX), have=False,
               rng=np.random.default_rng(20260806))
    RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
    RF.COST_BPS = c
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=KING, s2=S2, weights=dict(LIVE_W), verbose=False)
    return {"sh": float(o["avg_net_of_cost_sharpe"]), "turn": float(o["netting"]["net_turn_ann"])}


RF._SRC, RF._SRC_KEY = None, None
RF.COST_BPS = 3.63
src = RF.get_src(None, KING, S2)
chk = run(1.0, 0, False, 3.63)
print(f"[有效性] a=1,k=0 逐位复现: {'OK' if abs(chk['sh']+0.370)<1e-9 else 'FAIL '+str(chk['sh'])}",
      flush=True)

res = {}
print("\n  a     k   臂        换手   毛夏普   Sh@3.63  Sh@5.8", flush=True)
for a in (0.03, 0.15):
    for k, rnd, tag in ((0, False, "仅慢书"), (1, False, "PC k=1"), (3, False, "PC k=3"),
                        (5, False, "PC k=5"), (3, True, "★随机 k=3")):
        r = {c: run(a, k, rnd, c) for c in COSTS}
        res[f"a{a}_k{k}_{'rand' if rnd else 'pc'}"] = {
            "a": a, "k": k, "rand": rnd, "turn": r[3.63]["turn"], "gross": r[0.001]["sh"],
            "sh363": r[3.63]["sh"], "sh58": r[5.8]["sh"]}
        print(f" {a:5.2f} {k:3d}  {tag:10s} {r[3.63]['turn']:6.0f}  {r[0.001]['sh']:+6.3f}  "
              f"{r[3.63]['sh']:+7.3f}  {r[5.8]['sh']:+7.3f}", flush=True)

for a in (0.03, 0.15):
    b = res[f"a{a}_k0_pc"]
    best = max((res[f"a{a}_k{k}_pc"] for k in (1, 3, 5)), key=lambda v: v["sh363"])
    rnd = res[f"a{a}_k3_rand"]
    d, dg = best["sh363"] - b["sh363"], best["gross"] - b["gross"]
    dr = rnd["sh363"] - b["sh363"]
    v = ("互补成立" if d >= 0.15 and dg > 0 else "反向" if d <= -0.15 else "杀: 去集中在慢书上也不值")
    if abs(dr) >= abs(d) - 0.02:
        v = "★全表作废: 随机方向同样好"
    print(f"\n a={a}: 最优 PC(k={best['k']}) Δ净={d:+.3f} Δ毛={dg:+.3f} | 随机 Δ净={dr:+.3f} ⇒ {v}",
          flush=True)
    res[f"verdict_a{a}"] = v
print("\nJSON_BEGIN"); print(json.dumps(res)); print("JSON_END")
