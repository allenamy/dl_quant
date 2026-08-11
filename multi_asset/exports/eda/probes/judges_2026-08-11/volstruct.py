"""#32/#26 波动结构测量 + 干预臂 · 9821 锚 · 即将在役的完整栈(EMA α0.3 + 中性带 b.002)之上
==== 冻结判据(先于任何数字) ====
测量(诊断, 无门): M1 按 rvol_24h 逐锚三分位的 书内技能 corr(w, y) 与盈亏份额;
干预臂(采纳线, 继承 G 族): Δ净@4.137 日块CI95 下界>0 且 Δ净@6.23≥0 且 逐年≥4/5 且 夏普不降。
臂: cap_sym c∈{2,3,5}×中位贡献 | cap_long(只封多侧, 空尾信息在案)c∈{2,3} | shrink_long
(king/s2 分数横截面多侧 top10% × γ∈{0.5,0.7}, #26 探针B 的分数空间形态)。
==== 边界声明 ====
· α/λ 映射 DO-NOT-RETRY —— cap=尾部截断, 非幂律重标定, 不同族; 不测任何 λ 变体。
· cap 在生产中应整合进 compose_book(cap→re-demean→L1); 本装置在 compose 输出后模拟, 口径差已记。
· Q4 健康分层(sha 981d6768)不在本装置, 稳定性读逐年 + 2026 切片。
会红方向: (a) RB λ=1 已在栈内 ⇒ cap 增量可能≈0(这本身是 #32 的答案之一);
(b) shrink_long 若砍掉的是真信号, 2022/2025 强年先红; (c) cap 触发率过低 ⇒ 无统计力, 报告触发率。"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365); BW = 0.002
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]

def shrink_long(x, gamma):
    x = x.copy(); f = np.isfinite(x)
    if f.sum() < 20: return x
    thr = np.nanpercentile(x[f], 90)
    hi = f & (x > thr) & (x > 0)
    x[hi] = thr + (x[hi]-thr)*gamma
    return x

def build_tgt(cap_c=None, cap_side="both", shr=None):
    TGT, MSK, RET, RV = [], [], [], []
    held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
    for i, t in enumerate(a):
        ti = int(t); m = np.asarray(src.tradeable(ti))
        if m.dtype == bool: m = np.where(m)[0]
        if i == 0 or ti % 8 == 0:
            kk = src.king[ti, m].astype(float)
            if shr is not None: kk = shrink_long(kk, shr)
            v = np.full(N, np.nan); v[m] = kk; held["k"] = v
        if i == 0 or ti % 24 == 0:
            ss = src.s2[ti, m].astype(float)
            if shr is not None: ss = shrink_long(ss, shr)
            v = np.full(N, np.nan); v[m] = ss; held["s"] = v
        if i == 0 or ti % 8 == 0:
            v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
        rv = src.CH[ti, m, RVI].astype(float)
        r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                            weights=W, rvol=rv, risk_budget=RB)
        w = np.asarray(r["target_w"], float)
        if cap_c is not None:
            sig = np.where(np.isfinite(rv) & (rv > 0), rv, np.nanmedian(rv))
            contrib = np.abs(w)*sig
            med = np.nanmedian(contrib[contrib > 0]) if (contrib > 0).any() else 0.0
            if med > 0:
                lim = cap_c*med/sig
                over = np.abs(w) > lim
                if cap_side == "long": over &= (w > 0)
                w = np.where(over, np.sign(w)*lim, w)
                w = w - np.nanmean(w)
                s1 = np.abs(w).sum()
                if s1 > 0: w = w/s1
        wf = np.full(N, 0.0); wf[m] = w
        TGT.append(wf); MSK.append(m); RET.append(src.Y4[ti, m].astype(float)); RV.append(rv)
    return TGT, MSK, RET, RV

def run(TGT, MSK, RET):
    state = None; prev = np.zeros(N); n = len(a)
    pnl = np.zeros(n); trn = np.zeros(n); WH = []
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, 0.3)
        state = out["state"]
        tgt = np.asarray(out["target_w"], float)
        w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
        delta = tgt - w[m]
        T = np.abs(delta) > BW
        wm = w[m].copy(); wm[T] = tgt[T]
        if T.any(): wm[T] -= wm.sum()/T.sum()
        w[m] = wm
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[m][ok]*y[ok]))*1e4
        trn[i] = float(np.abs(w-prev).sum())
        prev = w; WH.append(w[m].copy())
    return pnl, trn, WH

def boot(d, nb=3000, bl=5):
    rng = np.random.default_rng(99); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

T0, M0, R0, V0 = build_tgt()
p0, t0, WH0 = run(T0, M0, R0)
n0 = p0-t0*C1
print(f"基线(EMA.3+带.002): 毛 {p0.mean():+.3f} 换手 {t0.mean():.4f} 净 {n0.mean():+.3f} "
      f"夏普 {n0.mean()/n0.std(ddof=1)*ANN:+.2f}")

# M1 按波动三分位的书内技能与盈亏(基线书, 逐锚)
ic3 = {0: [], 1: [], 2: []}; pnl3 = {0: 0.0, 1: 0.0, 2: 0.0}; gz3 = {0: 0.0, 1: 0.0, 2: 0.0}
for i in range(len(a)):
    w = WH0[i]; y = R0[i]; rv = V0[i]
    ok = np.isfinite(y) & np.isfinite(rv) & (np.abs(w) > 0)
    if ok.sum() < 30: continue
    q = np.nanpercentile(rv[ok], [33.3, 66.7])
    for b_ in range(3):
        if b_ == 0: sel = ok & (rv <= q[0])
        elif b_ == 1: sel = ok & (rv > q[0]) & (rv <= q[1])
        else: sel = ok & (rv > q[1])
        if sel.sum() >= 8 and np.std(w[sel]) > 0 and np.std(y[sel]) > 0:
            ic3[b_].append(float(np.corrcoef(w[sel], y[sel])[0, 1]))
        pnl3[b_] += float(np.nansum(w[sel]*y[sel]))*1e4
        gz3[b_] += float(np.abs(w[sel]).sum())
print("\nM1 按 rvol 三分位(全史 9821 锚, 基线书):")
for b_, nm in ((0, "低波"), (1, "中波"), (2, "高波")):
    v = np.array(ic3[b_]); se = v.std(ddof=1)/np.sqrt(len(v))
    print(f"  {nm}: 逐锚 corr(w,y) 均值 {v.mean():+.4f} (t={v.mean()/se:+.1f}, n={len(v)}) "
          f"累计盈亏 {pnl3[b_]:+.0f} bps·gross份额 {gz3[b_]/sum(gz3.values()):.3f} "
          f"盈亏/风险 {pnl3[b_]/max(gz3[b_],1e-9):+.4f}")

res = {}
ARMS = ([(f"cap_sym{c}", dict(cap_c=c)) for c in (2, 3, 5)]
        + [(f"cap_long{c}", dict(cap_c=c, cap_side="long")) for c in (2, 3)]
        + [(f"shrink_long{g}", dict(shr=g)) for g in (0.5, 0.7)])
for nm, kw in ARMS:
    Ti, Mi, Ri, Vi = build_tgt(**kw)
    p, t, _ = run(Ti, Mi, Ri)
    d = (p-t*C1)-n0; lo, hi = boot(d)
    d2 = (p-t*C2)-(p0-t0*C2)
    dfy = pd.DataFrame({"y": yr, "d": d}).groupby("y").d.mean()
    sh = (p-t*C1).mean()/(p-t*C1).std(ddof=1)*ANN; sh0 = n0.mean()/n0.std(ddof=1)*ANN
    ok_ = "★PASS" if (lo > 0 and d2.mean() >= 0 and (dfy >= 0).sum() >= 4 and sh >= sh0) else "fail"
    res[nm] = dict(dnet=round(d.mean(), 4), ci=[round(lo, 4), round(hi, 4)],
                   dnet_c2=round(d2.mean(), 4), yrs=int((dfy >= 0).sum()),
                   by_year={str(k): round(v, 3) for k, v in dfy.items()}, sharpe=round(sh, 3))
    print(f"{nm}: Δ净 {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] @6.23 {d2.mean():+.4f} "
          f"逐年{int((dfy>=0).sum())}/5 夏普 {sh:+.2f} 2026 {dfy.get(2026, float('nan')):+.3f} {ok_}")
json.dump(res, open(f"{PD}/volstruct_result.json", "w"), indent=1)
print("VOLSTRUCT_DONE")
