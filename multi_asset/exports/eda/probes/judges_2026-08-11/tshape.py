"""换手整形 3×5 — PREREG_turnover_shaping_2026-08-10(SHA 见同名 .sha256)
λ∈{1,.5,.3} × b∈{0,.0005,.001,.002,.004}; (1,0)=在役, 须复现 C8A ±2%。
成本双口径 主4.137/副6.23; G1-G5 冻结。"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365)
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")

# 预生成每锚 target(与臂无关, 算一次)
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
n = len(a); print(f"[build] {n} 锚", flush=True)

def run(lam, b):
    prev = np.zeros(N)
    pnl = np.zeros(n); trn = np.zeros(n); neu = np.zeros(n); gs = np.zeros(n)
    for i in range(n):
        m = MSK[i]
        tp = prev + lam*(TGT[i]-prev)              # EMA
        trade = np.abs(tp-prev) > b                # 带
        net = np.where(trade, tp, prev)
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(net[m][ok]*y[ok]))*1e4
        trn[i] = float(np.abs(net-prev).sum())
        neu[i] = abs(float(net.sum())); gs[i] = float(np.abs(net).sum())
        prev = net
    return pnl, trn, neu, gs

def boot(d, nb=3000, bl=5):
    rng = np.random.default_rng(99); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

LAMS = [1.0, 0.5, 0.3]; BS = [0.0, 0.0005, 0.001, 0.002, 0.004]
R = {}
p0, t0, _, _ = run(1.0, 0.0)
base_net1 = (p0 - t0*C1).mean()
print(f"G5 保真: (1,0) 毛 {p0.mean():+.3f} 换手 {t0.mean():.4f}  vs C8A +1.669/0.3120  "
      f"⇒ {'PASS' if abs(p0.mean()-1.669)/1.669<.02 and abs(t0.mean()-0.3120)/0.3120<.02 else '★FAIL 全部作废'}", flush=True)
print(f"\n{'λ':>5s}{'b':>8s}{'毛':>8s}{'换手':>8s}{'净@4.137':>10s}{'夏普':>7s}{'净@6.23':>9s}{'G1':>5s}{'G2':>5s}{'G3':>5s}{'G4':>5s}")
for lam in LAMS:
    for b in BS:
        p, t, neu, gs = run(lam, b)
        n1 = p - t*C1; n2 = p - t*C2
        d1 = n1 - (p0 - t0*C1)
        lo, hi = boot(d1)
        g1 = lo > 0 and n2.mean() >= (p0-t0*C2).mean()
        dfy = pd.DataFrame({"y": yr, "d": d1}).groupby("y").d.mean()
        g2 = (dfy >= 0).mean() >= 0.8
        s1 = n1.mean()/n1.std(ddof=1)*ANN; s2_ = n2.mean()/n2.std(ddof=1)*ANN
        b1 = (p0-t0*C1); b2 = (p0-t0*C2)
        g3 = s1 >= b1.mean()/b1.std(ddof=1)*ANN and s2_ >= b2.mean()/b2.std(ddof=1)*ANN
        g4 = neu.max() < 0.03
        R[(lam, b)] = {"gross": p.mean(), "turn": t.mean(), "net1": n1.mean(), "sh1": s1,
                       "net2": n2.mean(), "g": [g1, g2, g3, g4], "ci": [lo, hi],
                       "peryear": {int(k): round(float(v), 3) for k, v in dfy.items()},
                       "neu_max": float(neu.max()), "gross_sum": [float(gs.min()), float(gs.max())]}
        print(f"{lam:5.1f}{b:8.4f}{p.mean():+8.3f}{t.mean():8.4f}{n1.mean():+10.3f}{s1:+7.2f}"
              f"{n2.mean():+9.3f}" + "".join(f"{'P' if x else 'F':>5s}" for x in [g1, g2, g3, g4]), flush=True)
# 内点采纳规则
best = None
for (lam, b), v in R.items():
    if not all(v["g"]): continue
    li, bi = LAMS.index(lam), BS.index(b)
    ok = True
    for l2, b2i in ((li-1, bi), (li+1, bi), (li, bi-1), (li, bi+1)):
        if 0 <= l2 < len(LAMS) and 0 <= b2i < len(BS):
            if R[(LAMS[l2], BS[b2i])]["net1"] > v["net1"] + 0.02: ok = False
    if ok and (best is None or v["net1"] > best[1]["net1"]): best = ((lam, b), v)
print(f"\n★ 内点采纳: {best[0] if best else '无(全挂或皆边界)'}")
if best:
    v = best[1]
    print(f"  净@4.137 {v['net1']:+.3f}(基线 {base_net1:+.3f}, Δ{v['net1']-base_net1:+.3f} CI{v['ci']})  "
          f"夏普 {v['sh1']:+.2f}  逐年 {v['peryear']}  中性max {v['neu_max']:.4f}  gross∈{v['gross_sum']}")
json.dump({f"{k[0]}|{k[1]}": {kk: vv for kk, vv in v.items()} for k, v in R.items()},
          open(f"{PD}/tshape.json", "w"), indent=1, default=str)
print("TSHAPE_DONE")
