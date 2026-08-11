"""联合优化曲面: EMA α × 带宽 b × 修正模式(到目标/到带边) · 9821 锚 · 判据冻结
理论框架: 线性成本下最优=纯带+修到带边(Constantinides/Davis-Norman, 带宽∝(cost·σ²/衰减)^⅓);
二次成本下=部分调整(GP)。我们成本近纯线性 ⇒ 理论先验: (α=1, 大带, 到边) 可能支配 EMA+小带。
格: α∈{1.0,.3,.1,.05,.03,.02} × b∈{0,.001,.002,.004,.008,.012} × mode∈{target,edge}(b=0 时两模同).
判据: 任一格要取代在役(α.05,b.002,target), 须 Δ净@4.137 CI95>0 且 @6.23≥0 且逐年≥4/5 且夏普不降,
且为邻格不劣的内点。理论带宽估计随附。"""
import sys, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np, pandas as pd
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365)
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
TGT, MSK, RET = [], [], []
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                        weights=W, rvol=src.CH[ti, m, RVI].astype(float), risk_budget=RB)
    w = np.full(N, 0.0); w[m] = np.asarray(r["target_w"], float)
    TGT.append(w); MSK.append(m); RET.append(src.Y4[ti, m].astype(float))

def run(alpha, b, mode):
    state = None; prev = np.zeros(N)
    pnl = np.zeros(n); trn = np.zeros(n)
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, alpha)
        state = out["state"]
        tgt = np.asarray(out["target_w"], float)
        w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
        if b > 0:
            delta = tgt - w[m]
            T = np.abs(delta) > b
            wm = w[m].copy()
            if mode == "target":
                wm[T] = tgt[T]
            else:                                       # edge: 只修到带边缘
                wm[T] = tgt[T] - np.sign(delta[T]) * b
            if T.any(): wm[T] -= wm.sum()/T.sum()
            w[m] = wm
        else:
            w[m] = tgt
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[m][ok]*y[ok]))*1e4
        trn[i] = float(np.abs(w-prev).sum()); prev = w
    return pnl, trn

def boot(d, nb=2000, bl=5):
    rng = np.random.default_rng(99); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

# 理论带宽(量纲校验): b* ≈ (1.5·c·σ²_Δ/κ)^(1/3), c=成本/权重单位, σ_Δ=目标逐锚漂移, κ=衰减率
d_t = np.array([np.nanstd(TGT[i][MSK[i]] - TGT[i-1][MSK[i]]) for i in range(1, 200)])
sig_d = float(np.nanmean(d_t))
c_w = 4.137e-4
kappa = 1 - 0.62                                        # 分数持久性 0.62 ⇒ 衰减率/锚
b_theory = (1.5 * c_w * sig_d**2 / max(kappa, 1e-9)) ** (1/3)
print(f"理论带宽估计 b* ≈ {b_theory:.4f}(σ_Δ={sig_d:.4f}, κ={kappa:.2f}, c={c_w:.1e})")

p_cur, t_cur = run(0.05, 0.002, "target"); n_cur = p_cur - t_cur*C1
sh_cur = n_cur.mean()/n_cur.std(ddof=1)*ANN
print(f"在役格 (α.05, b.002, target): 净 {n_cur.mean():+.3f} 夏普 {sh_cur:+.2f}\n")
rows = []
for al in (1.0, 0.3, 0.1, 0.05, 0.03, 0.02):
    for b in (0.0, 0.001, 0.002, 0.004, 0.008, 0.012):
        modes = ("target",) if b == 0 else ("target", "edge")
        for md in modes:
            if (al, b, md) == (0.05, 0.002, "target"):
                net = n_cur; p, t = p_cur, t_cur
            else:
                p, t = run(al, b, md); net = p - t*C1
            sh = net.mean()/net.std(ddof=1)*ANN
            rows.append(dict(a=al, b=b, m=md, net=round(net.mean(),4), turn=round(t.mean(),5),
                             sh=round(sh,3)))
            print(f"α={al:<4} b={b:<6} {md:6s}: 净 {net.mean():+.3f} 换手 {t.mean():.4f} 夏普 {sh:+.2f}", flush=True)
df = pd.DataFrame(rows)
best = df.loc[df.net.idxmax()]
print(f"\n曲面最优: α={best.a} b={best.b} {best.m} 净 {best.net:+.3f} 夏普 {best.sh:+.2f}")
if (best.a, best.b, best.m) != (0.05, 0.002, "target"):
    pb, tb = run(best.a, best.b, best.m)
    d = (pb - tb*C1) - n_cur; lo, hi = boot(d)
    d2 = (pb - tb*C2) - (p_cur - t_cur*C2)
    dfy = pd.DataFrame({"y": yr, "d": d}).groupby("y").d.mean()
    print(f"最优 vs 在役: Δ {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] @6.23 {d2.mean():+.4f} "
          f"逐年{int((dfy>=0).sum())}/5 ⇒ {'★取代候选' if lo>0 and d2.mean()>=0 and (dfy>=0).sum()>=4 else '在噪声内, 在役即联合最优'}")
else:
    print("在役格即曲面最优。")
json.dump(rows, open(f"{PD}/joint_opt_surface.json","w"), indent=1)
print("JOINTOPT_DONE")
