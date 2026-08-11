"""PROPOSAL 00 §9 的决定性实验 —— alpha 在非主导方向上有信息吗?

对书的最终权重做 top-k 主成分中性化(协方差【逐 epoch 因果滚动】估计), 在同一 replay 装置上测
IC / 净夏普 / N_eff^book。判读规则已封于 §9, 本脚本只执行。

★ 有效性: k=0 臂必须与【未打补丁】的 replay 逐位相同。不同 ⇒ 补丁改变了基线, 全表作废。
★ 伙伴检查: k=3 随机正交方向臂。若随机方向产生同样效果 ⇒ 效应是"扰动这本书"而非"移除因子押注"。
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
COSTS = [3.63, 5.8]
KS = [1, 2, 3, 5]
WIN_ROWS = 120 * 24          # 120 天因果窗(面板逐小时)
EPOCH = 168                  # 每 7 天重估一次主成分(top-k 在日尺度上稳定)
NPC_KEEP = 5

# ── 因果主成分预计算 ────────────────────────────────────────────────────────────
z = np.load(f"{MA}/exports/wide_dl_full_corrfund_causal_0731.npz", allow_pickle=True)
Y4 = z["Y4"].astype(np.float64); CL4 = z["CL4"].astype(bool); MEM = z["MEMBER110"].astype(bool)
T, N = Y4.shape
Rm = np.where(MEM & CL4, Y4, np.nan)
Rd = Rm - np.nanmean(Rm, axis=1, keepdims=True)      # xsec-demean = 市场中性书的真实暴露

EPOCHS = list(range(WIN_ROWS, T, EPOCH))
VP = {}                                              # epoch -> (V(N,k), lam(k'), full_lam)
t0 = time.time()
for e in EPOCHS:
    W = Rd[max(0, e - WIN_ROWS):e]                   # ★ 严格 < e, 因果
    W = W[np.isfinite(W).sum(1) >= 20]
    if W.shape[0] < 100:
        continue
    cov_ok = np.isfinite(W).mean(0) > 0.8
    Wc = W[:, cov_ok]
    Wc = Wc[np.isfinite(Wc).all(1)]
    if Wc.shape[0] < 60 or cov_ok.sum() < 20:
        continue
    C = np.cov(Wc, rowvar=False)
    lam, V = np.linalg.eigh(C)
    order = np.argsort(lam)[::-1]
    lam, V = lam[order], V[:, order]
    Vfull = np.zeros((N, NPC_KEEP))
    Vfull[np.where(cov_ok)[0][:, None], np.arange(NPC_KEEP)[None, :]] = V[:, :NPC_KEEP]
    VP[e] = (Vfull, lam[:NPC_KEEP], lam, np.where(cov_ok)[0])
print(f"[因果主成分] {len(VP)}/{len(EPOCHS)} epoch 可用 (窗 {WIN_ROWS}h, 每 {EPOCH}h 重估), "
      f"{time.time()-t0:.0f}s", flush=True)
EK = np.array(sorted(VP))

_ORIG = SC.SignalChain.shape_position
_ORIG_LP = SC.SignalChain.leg_positions
_ST = {"k": 0, "mode": "pc", "t": None, "idx": None, "n_treated": 0, "n_skipped": 0,
       "rng": None, "samples": []}


def patched_lp(self, t):
    out, m = _ORIG_LP(self, t)
    _ST["t"] = int(t); _ST["idx"] = m
    return out, m


def patched(self, combo):
    base = _ORIG(self, combo)
    k = _ST["k"]
    if k == 0:
        return base                                   # ★ 逐位回落 = 有效性判据靠它
    t, m = _ST["t"], _ST["idx"]
    if t is None or m is None or len(base) != len(m):
        _ST["n_skipped"] += 1
        return base
    j = np.searchsorted(EK, t, side="right") - 1      # 最近的【已过去】epoch
    if j < 0:
        _ST["n_skipped"] += 1
        return base
    Vfull, _lamk, _lamall, _cols = VP[EK[j]]
    B = Vfull[m][:, :k]                               # (n_member, k)
    if _ST["mode"] == "rand":                         # 伙伴检查: 随机正交方向
        B = _ST["rng"].normal(size=B.shape)
    q, _ = np.linalg.qr(B)
    if not np.isfinite(q).all():
        _ST["n_skipped"] += 1
        return base
    out = base - q @ (q.T @ base)                     # 投影掉 top-k 方向
    out = out - out.mean()                            # 中性化破坏 demean ⇒ 二次 demean
    g0, g1 = np.abs(base).sum(), np.abs(out).sum()
    if g1 <= 1e-12 or g0 <= 0:
        _ST["n_skipped"] += 1
        return base
    out = out * g0 / g1                               # 归一到同毛敞口 ⇒ 同口径比较
    _ST["n_treated"] += 1
    if _ST["n_treated"] % 40 == 0:
        _ST["samples"].append((t, out.copy(), m.copy()))
    return out


def neff_book(samples):
    vals = []
    for t, w, m in samples:
        j = np.searchsorted(EK, t, side="right") - 1
        if j < 0:
            continue
        _V, _lk, lam_all, cols = VP[EK[j]]
        pos = {c: i for i, c in enumerate(cols)}
        sel = [(i, pos[c]) for i, c in enumerate(m) if c in pos]
        if len(sel) < 20:
            continue
        wi = np.array([w[i] for i, _ in sel]); ci = np.array([p for _, p in sel])
        Wc = Rd[max(0, t - WIN_ROWS):t][:, cols]
        Wc = Wc[np.isfinite(Wc).all(1)]
        if Wc.shape[0] < 60:
            continue
        C = np.cov(Wc, rowvar=False)[np.ix_(ci, ci)]
        lam, V = np.linalg.eigh(C)
        lam = np.clip(lam, 0, None)
        r = np.square(V.T @ wi) * lam
        if r.sum() > 0:
            vals.append(r.sum() ** 2 / np.square(r).sum())
    return float(np.mean(vals)) if vals else float("nan")


def run(cost):
    RF.COST_BPS = cost
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=KING, s2=S2, weights=dict(LIVE_W), verbose=False)
    return {"ic": float(np.mean([o["per_year"][y]["mean_rank_ic"] for y in o["per_year"]])),
            "sh": float(o["avg_net_of_cost_sharpe"]),
            "turn": float(o["netting"]["net_turn_ann"]),
            "per_year_ic": {int(y): float(o["per_year"][y]["mean_rank_ic"]) for y in o["per_year"]},
            "per_year_sh": {int(y): float(o["per_year"][y]["net_of_cost_sharpe"]) for y in o["per_year"]}}


RF._SRC, RF._SRC_KEY = None, None
RF.COST_BPS = COSTS[0]
src = RF.get_src(None, KING, S2)

# ══ 有效性: 先跑【完全未打补丁】的基线 ══
base_raw = {}
for c in COSTS:
    RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
    base_raw[c] = run(c)
print(f"[未打补丁基线] IC={base_raw[COSTS[0]]['ic']:.5f}  Sh@3.63={base_raw[COSTS[0]]['sh']:+.3f}  "
      f"Sh@5.8={base_raw[COSTS[1]]['sh']:+.3f}  turn={base_raw[COSTS[0]]['turn']:.0f}", flush=True)

SC.SignalChain.shape_position = patched
SC.SignalChain.leg_positions = patched_lp

res = {"baseline_unpatched": {str(c): base_raw[c] for c in COSTS}, "arms": {}}
_ST.update(k=0, mode="pc")
k0 = {}
for c in COSTS:
    RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
    k0[c] = run(c)
ok = (abs(k0[COSTS[0]]["ic"] - base_raw[COSTS[0]]["ic"]) < 1e-12
      and abs(k0[COSTS[0]]["sh"] - base_raw[COSTS[0]]["sh"]) < 1e-12
      and abs(k0[COSTS[1]]["sh"] - base_raw[COSTS[1]]["sh"]) < 1e-12)
res["validity_k0_bitwise"] = bool(ok)
print(f"[有效性] k=0 臂 vs 未打补丁: {'逐位相同 ✓' if ok else '★不同 ⇒ 全表作废'}", flush=True)
if not ok:
    sys.exit(1)

for k in KS:
    _ST.update(k=k, mode="pc", n_treated=0, n_skipped=0, samples=[])
    r = {}
    for c in COSTS:
        RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
        r[c] = run(c)
    ne = neff_book(_ST["samples"])
    dic = r[COSTS[0]]["ic"] / base_raw[COSTS[0]]["ic"] - 1
    res["arms"][f"pc_k{k}"] = {"ic": r[COSTS[0]]["ic"], "d_ic_pct": round(dic * 100, 2),
                               "sh363": r[COSTS[0]]["sh"], "sh58": r[COSTS[1]]["sh"],
                               "d_sh363": round(r[COSTS[0]]["sh"] - base_raw[COSTS[0]]["sh"], 3),
                               "d_sh58": round(r[COSTS[1]]["sh"] - base_raw[COSTS[1]]["sh"], 3),
                               "turn": r[COSTS[0]]["turn"], "n_eff_book": round(ne, 2),
                               "n_treated": _ST["n_treated"], "n_skipped": _ST["n_skipped"],
                               "per_year_ic": r[COSTS[0]]["per_year_ic"]}
    print(f"  PC-k={k}: IC {r[COSTS[0]]['ic']:.5f} ({dic*100:+.1f}%)  "
          f"Sh@3.63 {r[COSTS[0]]['sh']:+.3f} ({r[COSTS[0]]['sh']-base_raw[COSTS[0]]['sh']:+.3f})  "
          f"Sh@5.8 {r[COSTS[1]]['sh']:+.3f} ({r[COSTS[1]]['sh']-base_raw[COSTS[1]]['sh']:+.3f})  "
          f"N_eff^book {ne:5.2f}  turn {r[COSTS[0]]['turn']:.0f}  "
          f"[治疗 {_ST['n_treated']} 跳过 {_ST['n_skipped']}]", flush=True)

# ══ 伙伴检查: 随机正交方向 (k=3) ══
_ST.update(k=3, mode="rand", n_treated=0, n_skipped=0, samples=[],
           rng=np.random.default_rng(20260806))
r = {}
for c in COSTS:
    RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
    r[c] = run(c)
ne = neff_book(_ST["samples"])
dic = r[COSTS[0]]["ic"] / base_raw[COSTS[0]]["ic"] - 1
res["arms"]["rand_k3_PARTNER"] = {"ic": r[COSTS[0]]["ic"], "d_ic_pct": round(dic * 100, 2),
                                  "sh363": r[COSTS[0]]["sh"], "sh58": r[COSTS[1]]["sh"],
                                  "d_sh363": round(r[COSTS[0]]["sh"] - base_raw[COSTS[0]]["sh"], 3),
                                  "n_eff_book": round(ne, 2), "turn": r[COSTS[0]]["turn"]}
print(f"  [伙伴]随机 k=3: IC {r[COSTS[0]]['ic']:.5f} ({dic*100:+.1f}%)  "
      f"Sh@3.63 {r[COSTS[0]]['sh']:+.3f}  N_eff^book {ne:5.2f}", flush=True)

json.dump(res, open("/tmp/RESULT_pc_neutralize.json", "w"), indent=1)
print("\n→ /tmp/RESULT_pc_neutralize.json", flush=True)
