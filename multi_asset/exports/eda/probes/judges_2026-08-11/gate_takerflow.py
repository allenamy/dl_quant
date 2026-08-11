"""taker flow 五因子过冻结三关 — PREREG_takerflow_family 43a76ddb。
装置 = 实盘 compose_book(正典), 9821 锚。候选腿权重槽 w=0.10 固定不搜索
★ 该权重不在冻结文本里, 明标为本次实现选择。
P2 对齐断言先于一切; P3 与面板 32 通道 max|rho|<0.7; 关三与在役三腿 max|rho|<0.3;
关一 秩+值双报; 关二 净额双档; 安慰剂 5 固定种子同槽位; 逐年 >=80%。
"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF

W0 = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
WC = 0.10                                   # 候选槽位, 固定
RB = {"alpha": .5, "lambda": 1.}; COSTS = [3.115, 5.80]; ANN = np.sqrt(6*365)
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
psyms = [str(s) for s in src.symbols]

z = np.load(f"{PD}/takerflow_factors_panel.npz", allow_pickle=True)
fsyms = [str(s) for s in z["symbols"]]; fts = z["ts"]
FK = [k for k in z.files if k.startswith("F")]
print("因子:", FK)

# ── P2 对齐(断言先于一切)
col = {s: i for i, s in enumerate(fsyms)}
sidx = np.array([col.get(s, -1) for s in psyms])
row = {int(t): i for i, t in enumerate(fts)}
ridx = np.array([row.get(int(src.ts[t]), -1) for t in a])
cov_s = (sidx >= 0).mean(); cov_t = (ridx >= 0).mean()
print(f"P2 对齐: 面板 {len(psyms)} 币中 {int((sidx>=0).sum())} 个有因子 ({cov_s:.3f}); "
      f"{len(a)} 锚中 {int((ridx>=0).sum())} 个有时戳 ({cov_t:.3f})")
assert cov_t > 0.5, "★时间轴对不上, 停"
FAC = {}
for k in FK:
    A = z[k]; out = np.full((len(a), N), np.nan)
    ok = ridx >= 0
    for j, si in enumerate(sidx):
        if si >= 0: out[ok, j] = A[ridx[ok], si]
    FAC[k] = out
    print(f"  {k:12s} 对齐后有限占比 {np.isfinite(out).mean():.4f}")

# ── 预取
M, KK, SS, FF, RV, RET = [], [], [], [], [], []
for t in a:
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    M.append(m); KK.append(src.king[ti, m].astype(float)); SS.append(src.s2[ti, m].astype(float))
    FF.append(src.CH[ti, m, FI].astype(float)); RV.append(src.CH[ti, m, RVI].astype(float))
    RET.append(src.Y4[ti, m].astype(float))
n = len(a)

def pear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 10: return np.nan
    u, v = x[ok]-x[ok].mean(), y[ok]-y[ok].mean()
    d = np.sqrt((u*u).sum()*(v*v).sum())
    return float((u*v).sum()/d) if d > 0 else np.nan

# ── P3 与面板 32 通道
print("\nP3 与面板 32 通道的逐锚横截面 max|rho| (<0.7 才留):")
step = max(1, n//400)
P3 = {}
for k in FK:
    mx, arg = 0.0, ""
    for ci, cn_ in enumerate(src.ch):
        rs = [pear(FAC[k][i][M[i]], src.CH[int(a[i]), M[i], ci].astype(float)) for i in range(0, n, step)]
        r = np.nanmean(np.abs(rs))
        if r > mx: mx, arg = r, cn_
    P3[k] = (mx, arg)
    print(f"  {k:12s} max|rho| {mx:.3f} vs {arg:18s} {'PASS' if mx < 0.7 else '★剔除'}")
KEEP = [k for k in FK if P3[k][0] < 0.7]
print(f"  ⇒ 进入后续: {KEEP}")

def run(extra=None, w_extra=0.0):
    prev = None; pnl = np.zeros(n); trn = np.zeros(n); ric = np.full(n, np.nan); pic = np.full(n, np.nan)
    sc = 1.0 - w_extra
    W = {k: v*sc for k, v in W0.items()}
    for i in range(n):
        m = M[i]
        r = LG.compose_book(KK[i], SS[i], FF[i], np.ones(len(m)), weights=W,
                            rvol=RV[i], risk_budget=RB)
        w = np.asarray(r["target_w"], float)
        if extra is not None:
            e = extra[i][m]
            w = w + w_extra*LG.l1(LG.rank_centered(e))
            w = LG.l1(w - w.mean())
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[ok]*y[ok]))*1e4
        cur = dict(zip(m, w))
        trn[i] = 0. if prev is None else sum(abs(cur.get(x, 0.)-prev.get(x, 0.)) for x in set(cur)|set(prev))
        if ok.sum() >= 10:
            ric[i] = float(np.corrcoef(pd.Series(w[ok]).rank(), pd.Series(y[ok]).rank())[0, 1])
            pic[i] = pear(w[ok], y[ok])
        prev = cur
    return pnl, trn, ric, pic

def boot(d, nb=3000, bl=5):
    rng = np.random.default_rng(99); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

p0, t0_, r0, i0 = run()
print(f"\n基线: 毛 {p0.mean():+.3f}  秩IC {np.nanmean(r0):+.5f}  值IC {np.nanmean(i0):+.5f}  换手 {t0_.mean():.4f}  "
      + "  ".join(f"净@{c} {(p0-t0_*2*c).mean():+.3f}" for c in COSTS))

# 安慰剂: 同槽位随机因子 5 固定种子
PL = []
for sd in range(5):
    rg = np.random.default_rng(sd)
    ex = [rg.standard_normal(N) for _ in range(n)]
    PL.append(run(ex, WC)[0])
plm = np.mean(PL, axis=0)
print(f"安慰剂(5种子均): 毛 {plm.mean():+.3f}")

print("\n" + "═"*96)
print(f"{'因子':12s}{'毛bps':>8s}{'秩IC':>9s}{'值IC':>9s}{'换手':>8s}{'净@3.115':>10s}{'净@5.8':>9s}"
      f"{'关三max|r|':>11s}{'关一':>6s}{'关二':>6s}{'安慰剂':>7s}{'逐年':>6s}")
print("═"*96)
res = {}
for k in KEEP:
    p, t, r, ip = run(FAC[k], WC)
    # 关三: 与在役三腿的正交性
    mx = 0.0
    for i in range(0, n, step):
        m = M[i]
        for leg, v in (("king", KK[i]), ("s2", SS[i]), ("funding", FF[i])):
            mx = max(mx, abs(pear(FAC[k][i][m], np.asarray(v, float)) or 0))
    d = p - p0
    lo, hi = boot(d)
    g1 = lo > 0
    g2 = all(((p-t*2*c).mean() - (p0-t0_*2*c).mean()) > 0 for c in COSTS)
    lo2, _ = boot(p - plm); pl_ok = lo2 > 0
    dfy = pd.DataFrame({"y": yr, "d": (p-t*2*3.115)-(p0-t0_*2*3.115)}).groupby("y").d.mean()
    g4 = (dfy >= 0).mean() >= 0.8
    print(f"{k:12s}{p.mean():+8.3f}{np.nanmean(r):+9.5f}{np.nanmean(ip):+9.5f}{t.mean():8.4f}"
          f"{(p-t*2*3.115).mean():+10.3f}{(p-t*2*5.8).mean():+9.3f}{mx:11.3f}"
          f"{'PASS' if g1 else 'FAIL':>6s}{'PASS' if g2 else 'FAIL':>6s}"
          f"{'PASS' if pl_ok else 'FAIL':>7s}{int((dfy>=0).sum())}/{len(dfy):<4d}", flush=True)
    res[k] = {"gross": float(p.mean()), "rank_ic": float(np.nanmean(r)), "val_ic": float(np.nanmean(ip)),
              "turn": float(t.mean()), "d_gross": float(d.mean()), "ci": [lo, hi],
              "orth_max": mx, "G1": bool(g1), "G2": bool(g2), "placebo": bool(pl_ok),
              "per_year": {int(x): round(float(v), 4) for x, v in dfy.items()}, "G4": bool(g4)}
print("═"*96)
adm = [k for k, v in res.items() if v["G1"] and v["G2"] and v["placebo"] and v["G4"] and v["orth_max"] < 0.3]
print(f"\n★ 录取: {adm if adm else '零 —— 无因子过全部关'}")
res["P3"] = {k: [float(v[0]), v[1]] for k, v in P3.items()}
res["baseline"] = {"gross": float(p0.mean()), "turn": float(t0_.mean())}
json.dump(res, open(f"{PD}/takerflow_gate.json", "w"), indent=1)
print("TAKERFLOW_GATE_DONE")
