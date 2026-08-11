"""候选4 段位条件腿混合 · 判据冻结(先于数字)
前置证据(tail_pregate 实测): 复合底段内 spearman +0.0089 vs king 底段 +0.0384 (5/5 年一致)
—— 混合稀释了 king 最强的短端, 而 D1 档 |均值| 全表最大(−3.6bps)。
臂: 底段(复合自身排名 q≤1/3, 因果同锚)换用 king 加重书的权重, 其余名不动; 混合后重去均值+
毛额归一 → EMA+带照旧。剂量: kingheavy(k.85/s.075/f.075) 与 kingpure(1/0/0)。
对照臂: 同法作用于顶段(若顶段臂同样"改善", 机制不是短端技能而是"到处加 king", 全族存疑 ——
且 D2 已证全局加 king 是平的)。
判(冻结): 底段臂 Δ净@4.137 CI95>0 且 @6.23≥0 且逐年≥4/5 且夏普不降, 且顶段对照不显著为正
⇒ 才立项(之后仍需 prereg + 用户裁定才可上书)。"""
import sys
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import numpy as np, pandas as pd
import legs as LG
import engine.replay_fullhist as RF
WB = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
WH = {"king": .85, "s2": .075, "funding": .075, "size": 0.}
WP = {"king": 1.0, "s2": 0.0, "funding": 0.0, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365)
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
BASE, ALT_H, ALT_P, MSK, RET = [], [], [], [], []
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
    rv = src.CH[ti, m, RVI].astype(float)
    args = (held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)))
    b = np.asarray(LG.compose_book(*args, weights=WB, rvol=rv, risk_budget=RB)["target_w"], float)
    h = np.asarray(LG.compose_book(*args, weights=WH, rvol=rv, risk_budget=RB)["target_w"], float)
    p = np.asarray(LG.compose_book(*args, weights=WP, rvol=rv, risk_budget=RB)["target_w"], float)
    wb = np.full(N, 0.0); wb[m] = b; BASE.append(wb)
    wh = np.full(N, 0.0); wh[m] = h; ALT_H.append(wh)
    wp = np.full(N, 0.0); wp[m] = p; ALT_P.append(wp)
    MSK.append(m); RET.append(src.Y4[ti, m].astype(float))
def mix(base_w, alt_w, m, seg):
    b = base_w[m]
    q = np.argsort(np.argsort(b)) / max(len(m) - 1, 1)
    sel = q <= 1/3 if seg == "bot" else q >= 2/3
    out = b.copy(); out[sel] = alt_w[m][sel]
    out -= out.mean()
    g0, g1 = np.abs(b).sum(), np.abs(out).sum()
    if g1 > 0: out *= g0 / g1
    return out
def run(mode=None, alt=None, seg=None):
    state = None; prev = np.zeros(N)
    pnl = np.zeros(n); trn = np.zeros(n)
    for i in range(n):
        m = MSK[i]
        tgt0 = BASE[i][m] if mode is None else mix(BASE[i], alt[i], m, seg)
        out = LG.apply_harvest_ema(tgt0, [SYMS[j] for j in m], state, 0.05)
        state = out["state"]; tgt = np.asarray(out["target_w"], float)
        w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
        delta = tgt - w[m]; T = np.abs(delta) > 0.002
        wm = w[m].copy(); wm[T] = tgt[T]
        if T.any(): wm[T] -= wm.sum()/T.sum()
        w[m] = wm
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[m][ok]*y[ok]))*1e4
        trn[i] = float(np.abs(w-prev).sum()); prev = w
    return pnl, trn
def boot(d, nb=2000, bl=5):
    rng = np.random.default_rng(21); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q_ in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q_] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))
p0, t0 = run(); n0 = p0-t0*C1; sh0 = n0.mean()/n0.std(ddof=1)*ANN
print(f"基线: 净 {n0.mean():+.3f} 夏普 {sh0:+.2f} 换手 {t0.mean():.4f}")
yrs = np.array(yr)
for nm, alt, seg in (("底段 kingheavy85", ALT_H, "bot"), ("底段 kingpure", ALT_P, "bot"),
                     ("顶段对照 kingheavy85", ALT_H, "top")):
    p, t = run("mix", alt, seg)
    net = p-t*C1; d = net-n0; lo, hi = boot(d)
    d2 = (p-t*C2).mean()-(p0-t0*C2).mean()
    dfy = pd.DataFrame({"y": yrs, "d": d}).groupby("y").d.mean()
    sh = net.mean()/net.std(ddof=1)*ANN
    ok_ = "★PASS" if (lo > 0 and d2 >= 0 and (dfy >= 0).sum() >= 4 and sh >= sh0) else "fail"
    print(f"{nm}: Δ净 {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] @6.23 {d2:+.4f} "
          f"逐年{int((dfy>=0).sum())}/5 换手 {t.mean():.4f} 夏普 {sh:+.2f} {ok_}", flush=True)
print("SEGBLEND_DONE")
