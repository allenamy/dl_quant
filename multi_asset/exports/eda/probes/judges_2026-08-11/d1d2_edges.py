"""D1 倾斜/选择双袖风险配置 + D2 腿权重新成本重测 · 诊断口径声明:
D1: 基书按 rvol 三分位分解为 倾斜序列(档均值书) 与 选择序列(基−倾斜), 各自夏普/相关/最优混合前沿
    vs 内嵌混合 —— 差值=免费夏普(若≈0 ⇒ 关闭)。
D2: 腿权重简面网格 @新栈(EMA.05+带.002, 成本4.137) 全史净读数【声明: 全史挑格=样本内, 只作
    "面是否平"诊断; 面若强斜 ⇒ 另做 WF 版才可采纳】。"""
import sys, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np, pandas as pd
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
RB = {"alpha": .5, "lambda": 1.}; C1 = 4.137; ANN = np.sqrt(6*365); BW = 0.002
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]

def build(W):
    TGT, MSK, RET, RV = [], [], [], []
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
        rv = src.CH[ti, m, RVI].astype(float)
        r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                            weights=W, rvol=rv, risk_budget=RB)
        w = np.full(N, 0.0); w[m] = np.asarray(r["target_w"], float)
        TGT.append(w); MSK.append(m); RET.append(src.Y4[ti, m].astype(float)); RV.append(rv)
    return TGT, MSK, RET, RV

def run(TGT, MSK, RET, split_tilt=None):
    state = None; prev = np.zeros(N)
    pnl = np.zeros(n); trn = np.zeros(n)
    p_tilt = np.zeros(n)
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, 0.05)
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
        if split_tilt is not None:
            rv = split_tilt[i]
            f = np.isfinite(rv)
            if f.sum() > 30:
                q = np.nanpercentile(rv[f], [33.3, 66.7])
                b_ = np.where(~f, 1, np.where(rv <= q[0], 0, np.where(rv <= q[1], 1, 2)))
                wt = np.zeros_like(w[m])
                for k_ in range(3):
                    sel = b_ == k_
                    if sel.sum() > 3: wt[sel] = w[m][sel].mean()
                p_tilt[i] = float(np.nansum(wt[ok]*y[ok]))*1e4
        prev = w
    return pnl, trn, p_tilt

W0 = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
TGT, MSK, RET, RV = build(W0)
p, t, ptilt = run(TGT, MSK, RET, split_tilt=RV)
net = p - t*C1
psel = p - ptilt                       # 选择分量(毛口径; 成本全记在总书, 分量按毛分析)
sT = ptilt.mean()/ptilt.std(ddof=1)*ANN
sS = psel.mean()/psel.std(ddof=1)*ANN
rho = float(np.corrcoef(ptilt, psel)[0, 1])
print(f"D1 分量: 倾斜 毛{ptilt.mean():+.3f} 夏普{sT:+.2f} | 选择 毛{psel.mean():+.3f} 夏普{sS:+.2f} | ρ={rho:+.3f}")
# 最优混合(毛口径, 两资产 MV): w* ∝ Σ^{-1}μ
mu = np.array([ptilt.mean(), psel.mean()])
S = np.cov(np.stack([ptilt, psel]))
wopt = np.linalg.solve(S, mu); wopt = wopt/np.abs(wopt).sum()
mix = wopt[0]*ptilt + wopt[1]*psel
s_mix = mix.mean()/mix.std(ddof=1)*ANN
s_base_gross = p.mean()/p.std(ddof=1)*ANN
print(f"D1 前沿: 内嵌混合(=基书毛)夏普 {s_base_gross:+.2f} vs 最优混合 {s_mix:+.2f} "
      f"(w*=倾斜{wopt[0]:.2f}/选择{wopt[1]:.2f}) ⇒ 免费夏普 {s_mix-s_base_gross:+.2f}")

# D2 腿权重简面 @新栈(全史诊断)
print("\nD2 腿权重面(全史净@4.137, 诊断口径):")
res2 = {}
for wk, ws, wf in ((.60,.20,.20),(.45,.35,.20),(.45,.20,.35),(.30,.50,.20),(.30,.20,.50),
                   (.20,.60,.20),(.20,.40,.40),(.75,.125,.125),(.33,.34,.33),(.50,.10,.40)):
    Wx = {"king": wk, "s2": ws, "funding": wf, "size": 0.}
    Ti, Mi, Ri, _ = build(Wx)
    pi, ti_, _ = run(Ti, Mi, Ri)
    neti = pi - ti_*C1
    sh = neti.mean()/neti.std(ddof=1)*ANN
    res2[f"{wk}/{ws}/{wf}"] = dict(net=round(neti.mean(),4), sharpe=round(sh,3))
    tag = " ★在役" if abs(wk-.5952)<0.02 else ""
    print(f"  k{wk:.2f}/s{ws:.2f}/f{wf:.2f}: 净 {neti.mean():+.3f} 夏普 {sh:+.2f}{tag}")
json.dump({"d1": dict(tilt_sh=round(sT,3), sel_sh=round(sS,3), rho=round(rho,3),
                      mix_sh=round(s_mix,3), base_gross_sh=round(s_base_gross,3),
                      wopt=[round(float(x),3) for x in wopt]), "d2": res2},
          open(f"{PD}/d1d2_edges.json", "w"), indent=1)
print("D1D2_DONE")
