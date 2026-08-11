"""波动缩放 sizing 的三通道分离 —— 执行 PREREG_volscaling_three_channel_2026-08-04.md
(FROZEN v2, sha 806d6b1c9aa33ae7f14b5106af45e5d5f17f2c31b2e6bc4384564b9244195ba3)
v1 的有效性判据方向搞反: 用夏普检验方差效应而对照臂均值不为零。Sharpe=mean/std,
臂B 的 mean 按构造为负 ⇒ std 下降必然让夏普更负 ⇒ v1 把成功读成了失败。
v2 直接测方差, 并把夏普拆成 mean 与 std 两部分报。

不改引擎: 用 monkey-patch 覆盖 SignalChain.shape_position, 原实现保留并在 λ=0 时逐位回落到它。
σ 的因果约定【照抄】 panel_source 第 32-33 行:
    "causal realized 1h return by time t = Y1[t-1]"
  ⇒ r[t] = Y1[t-1] 是 t−1→t 的收益, 在 t 已实现 ⇒ 窗口 [t-w+1, t] 是因果的。
  (我一度怀疑 btc_rvol 的 [lo:t+1] 切片吃了未来 —— 查了源码, 引擎已经处理过, 我错了。)
"""
import sys, json, time
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
import torch; torch.backends.mkldnn.enabled = False
from engine import replay_fullhist as RF
from engine import signal_chain as SC

_DS = []
_ORIG_DS = RF._dsharpe


def _ds_rec(x):
    a = np.asarray(x, float); a = a[np.isfinite(a)]
    if len(a) > 2:
        _DS.append((float(np.mean(a)), float(np.std(a))))
    return _ORIG_DS(x)


RF._dsharpe = _ds_rec       # ★ 每年调用两次: 先 pnl(gross) 后 pnl_net ⇒ 奇数索引是 net

KING = "/tmp/king_pred_newgen.npz"
S2 = "/tmp/s2_pred_newgen.npz"
LAMBDAS = [0.0, 0.25, 0.5, 0.75, 1.0]        # 预注册 §1; λ=0 = 现行(嵌套)
COSTS = [3.63, 5.8]
WIN_H = 24
SEED = 20260804

_ORIG_SHAPE = SC.SignalChain.shape_position
_STATE = {"lam": 0.0, "sigma": None, "src": None, "t": None, "idx": None, "undone": []}


def build_sigma(src, win=WIN_H):
    """逐名因果已实现波动 (T,N)。约定照抄 panel_source:32-33。"""
    Y1 = src.Y1
    T, N = Y1.shape
    r = np.empty((T, N)); r[0] = np.nan; r[1:] = Y1[:-1]      # r[t] = t−1→t, 在 t 已实现
    sig = np.full((T, N), np.nan)
    csum = np.nancumsum(np.nan_to_num(r), axis=0)
    csq = np.nancumsum(np.nan_to_num(r) ** 2, axis=0)
    cnt = np.cumsum(np.isfinite(r), axis=0)
    for t in range(1, T):
        lo = max(1, t - win + 1)
        n = cnt[t] - cnt[lo - 1]
        s1 = csum[t] - csum[lo - 1]
        s2_ = csq[t] - csq[lo - 1]
        with np.errstate(invalid="ignore", divide="ignore"):
            v = s2_ / np.maximum(n, 1) - (s1 / np.maximum(n, 1)) ** 2
        sig[t] = np.where(n >= 4, np.sqrt(np.maximum(v, 0.0)), np.nan)
    return sig


def patched_shape(self, combo):
    """cap → demean → ÷σ^λ → 二次 demean → (L1 由下游做)。λ=0 时逐位等于原实现。"""
    base = _ORIG_SHAPE(self, combo)                     # cap → demean, 原样
    lam = _STATE["lam"]
    if lam == 0.0:
        return base
    t, sig = _STATE["t"], _STATE["sigma"]
    m = _STATE["idx"]
    # ★ 索引集对不上 = 把 σ 对到错的名字上, 而且不会有任何东西报警。响亮失败, 不静默。
    if len(base) != len(m):
        raise RuntimeError(f"index-set mismatch: combo has {len(base)} entries, "
                           f"tradeable(t={t}) has {len(m)} — sigma would be applied to the wrong names")
    s = sig[t, m] if (sig is not None and t is not None) else None
    if s is None or not np.isfinite(s).any():
        return base
    med = np.nanmedian(s[np.isfinite(s) & (s > 0)])
    s = np.where(np.isfinite(s) & (s > 0), s, med)
    scaled = base / np.power(s / med, lam)              # 以中位数归一, 避免整体尺度漂移
    out = scaled - scaled.mean()                        # ★ 二次 demean(缩放破坏了中性)
    # 记录二次 demean 抵消了多少缩放(预注册 §1 要求必报)
    a, b = scaled - scaled.mean(), scaled
    denom = np.sum(np.abs(b - base))
    if denom > 1e-18:
        _STATE["undone"].append(float(np.sum(np.abs(a - b)) / denom))
    return out


# ★ shape_position 有【两个】调用者, 其 docstring 早就写着:
#     "The shared tail used by BOTH target_position() and the netting P&L path."
#   我读过那句话却按"只有 target_position"写了钩子, 第一次运行就 KeyError('idx') 炸了。
#   正确的挂钩点是 leg_positions —— 两条路径都必经它, 且它就返回那个索引集 m:
#     netting.py:49   legpos, m = chain.leg_positions(ti)   ... active = combo_full[m]
#     signal_chain    combined_signal -> leg_signals -> leg_positions
_ORIG_LEGPOS = SC.SignalChain.leg_positions


def patched_legpos(self, t):
    out, m = _ORIG_LEGPOS(self, t)
    _STATE["t"] = int(t); _STATE["idx"] = m
    return out, m


SC.SignalChain.shape_position = patched_shape
SC.SignalChain.leg_positions = patched_legpos


def permute_alpha(src, seed=SEED):
    """臂 B: alpha 逐锚【在成员内】横截面随机置换; σ 与掩码不变, 信息置零。"""
    rng = np.random.default_rng(seed)
    for arr in (src.king, src.s2):
        for t in range(arr.shape[0]):
            m = np.where(src.member[t])[0]
            if m.size > 1:
                arr[t, m] = arr[t, rng.permutation(m)]
    return src


def run(lam, cost, permuted):
    RF._SRC, RF._SRC_KEY = None, None
    RF.COST_BPS = cost
    src = RF.get_src(None, KING, S2)
    if permuted:
        before = src.king.copy()
        permute_alpha(src)
        moved = float((src.king != before)[np.isfinite(before)].mean())
        # 臂 B 的全部意义在于 alpha 被打散。若置换没发生, 臂 B 就是又一个臂 A,
        # 而有效性判据会"通过"得毫无意义。断言它, 不假设它。
        if moved < 0.5:
            raise RuntimeError(f"permutation did not take: only {moved:.1%} of king entries moved")
        print(f"    [arm B] permutation verified: {moved:.1%} of king entries moved", flush=True)
    _STATE["sigma"] = build_sigma(src)
    _STATE["lam"] = lam
    _STATE["undone"] = []
    _DS.clear()
    # ★ get_src 的缓存 key = (panel, king, s2), 且不匹配会 RAISE。必须用它会算出的那个 key,
    #   否则本脚本一调用就抛。副作用: 那道门看不见"同路径但内容被置换"——所以下面自己断言。
    RF._SRC, RF._SRC_KEY = src, (None, KING, S2)
    o = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                      king=KING, s2=S2, verbose=False)
    und = float(np.mean(_STATE["undone"])) if _STATE["undone"] else 0.0
    # ★ gross_turn_ann 在 out["netting"] 下, 不在顶层。第一轮我取错了 key, 整列成了 nan ——
    #   而换手正是【无 alpha 的臂为何变差】唯一可能的解释(它的盈亏≈0毛额−换手成本)。
    #   取不到就抛, 不要再让一个必报项静默变成 nan。
    _net = o.get("netting") or {}
    if "gross_turn_ann" not in _net:
        raise RuntimeError(f"gross_turn_ann missing; netting keys = {sorted(_net)}")
    net_pairs = _DS[1::2]                       # 奇数索引 = pnl_net
    return {"mean_net": float(np.mean([m for m, s in net_pairs])) if net_pairs else float("nan"),
            "std_net": float(np.mean([s for m, s in net_pairs])) if net_pairs else float("nan"),
            "avg": float(o["avg_net_of_cost_sharpe"]),
            "turn": float(_net["gross_turn_ann"]),
            "net_turn": float(_net.get("net_turn_ann", float("nan"))),
            "undone_frac": und,
            "per_year": {int(y): float(o["per_year"][y]["net_of_cost_sharpe"]) for y in o["per_year"]}}


t0 = time.time()
res = {}
for permuted in (False, True):
    arm = "B_permuted" if permuted else "A_real"
    for lam in LAMBDAS:
        for cost in COSTS:
            res[(arm, lam, cost)] = run(lam, cost, permuted)
            r = res[(arm, lam, cost)]
            print(f"  {arm:11s} λ={lam:<5} c={cost:<5} Sh={r['avg']:+7.3f} "
                  f"mean={r['mean_net']:+.5f} std={r['std_net']:.5f} "
                  f"netturn={r['net_turn']:7.0f} undone={r['undone_frac']:.3f}", flush=True)
print(f"\nelapsed {time.time()-t0:.0f}s")

# ── 预注册 v2 §2 有效性判据(测方差) → §3 三通道 → §4 判读 ────────────────────
print("\n" + "=" * 78)
und_max = max(v["undone_frac"] for k, v in res.items() if k[1] > 0)
print(f"[中性度代价] 二次 demean 抵消掉的缩放比例 (max over λ>0) = {und_max:.3f}")

for cost in COSTS:
    sB = [res[("B_permuted", l, cost)]["std_net"] for l in LAMBDAS]
    mono = all(sB[i + 1] <= sB[i] + 1e-12 for i in range(len(sB) - 1))
    drop = (sB[0] - sB[-1]) / sB[0] if sB[0] > 0 else 0.0
    ok = mono and drop > 0.01
    print(f"\n[cost {cost}] [§2 有效性判据] 臂B std(pnl_net) 随 λ: "
          + " → ".join(f"{s:.5f}" for s in sB)
          + f"  单调={mono} 降幅={drop:+.2%} ⇒ {'PASS' if ok else 'FAIL'}")
    if not ok:
        print("  ⇒ 全表作废: 本书 σ 离散度不足以让风险平价起作用(不是『vol scaling 无效』)")
        continue
    a0 = res[("A_real", 0.0, cost)]; b0 = res[("B_permuted", 0.0, cost)]
    print(f"  {'λ':>5} {'①Δstd(B)':>11} {'Δmean(A)':>11} {'Δmean(B)':>11} "
          f"{'③交互':>11} {'②Δnetturn':>11} {'参考ΔSh(A)':>11}")
    for lam in LAMBDAS[1:]:
        a = res[("A_real", lam, cost)]; b = res[("B_permuted", lam, cost)]
        dsB = (b["std_net"] - b0["std_net"]) / b0["std_net"]
        dmA = a["mean_net"] - a0["mean_net"]; dmB = b["mean_net"] - b0["mean_net"]
        print(f"  {lam:>5} {dsB:>+11.2%} {dmA:>+11.6f} {dmB:>+11.6f} {dmA-dmB:>+11.6f} "
              f"{a['net_turn']-a0['net_turn']:>+11.0f} {a['avg']-a0['avg']:>+11.3f}")
    best = max(LAMBDAS[1:], key=lambda l: res[("A_real", l, cost)]["mean_net"])
    dmA = res[("A_real", best, cost)]["mean_net"] - a0["mean_net"]
    dmB = res[("B_permuted", best, cost)]["mean_net"] - b0["mean_net"]
    if dmA - dmB < 0:
        print(f"  [§4] λ*={best}: 交互为负 ⇒ 停, 回查装置(与任何已知机制矛盾)")
    elif dmA > 0:
        print(f"  [§4] λ*={best}: Δmean(A)={dmA:+.6f} > 0 ⇒ 待 day-block CI 判(下一步)")
    else:
        print(f"  [§4] λ*={best}: Δmean(A)={dmA:+.6f} ≤ 0 ⇒ 不上; 三通道拆解见上表")

json.dump({"prereg": "PREREG_volscaling_three_channel_v2_2026-08-04.md",
           "prereg_sha256": "806d6b1c9aa33ae7f14b5106af45e5d5f17f2c31b2e6bc4384564b9244195ba3",
           "lambdas": LAMBDAS, "costs": COSTS, "win_h": WIN_H, "seed": SEED,
           "rows": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in res.items()}},
          open(MA + "/exports/eda/RESULT_volscaling_v2_2026-08-04.json", "w"), indent=1)
print("\nrecord -> exports/eda/RESULT_volscaling_v2_2026-08-04.json")
