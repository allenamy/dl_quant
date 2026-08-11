"""仓位映射四臂 · 9821 锚 · 用【实盘的书】compose_book
预注册 PREREG_mapping_4arm_fullhist_2026-08-09  (SHA 见同名 .sha256)
P1 legs.py 同码断言 · P2 M3 vs 引擎 S0(+1.832/0.4707) ±15% · G1 净额双档 · G2 逐年 · G3 净夏普 · G4 一致性
"""
import sys, os, json, time, hashlib
import numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"
sys.path.insert(0, PD)                       # legs.py 传到这里
import legs as LG
print("P1 jpline legs.py SHA256 =", hashlib.sha256(open(LG.__file__, "rb").read()).hexdigest()[:16])
print("   FUNDING_MODE=%s SIGNS=%s POS_CAP=%s" % (LG.FUNDING_MODE, LG.SIGNS, LG.POS_CAP_PCT))
import engine.replay_fullhist as RF
from engine.signal_chain import SignalChain
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate

W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
COSTS = [3.115, 5.80]; ANN = np.sqrt(6*365)
t0 = time.time()
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N
RVI = src.ch.index("rvol_24h"); FI = src.fund_idx
DVI = src.ch.index("dvol_30d") if "dvol_30d" in src.ch else None
print(f"[build] {len(a)} 锚  dvol ch={DVI}  {time.time()-t0:.0f}s", flush=True)

M, KK, SS, FF, RV, DVv, RET = [], [], [], [], [], [], []
for t in a:
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]          # ★ 统一成索引数组
    M.append(m); KK.append(src.king[ti, m].astype(float)); SS.append(src.s2[ti, m].astype(float))
    FF.append(src.CH[ti, m, FI].astype(float)); RV.append(src.CH[ti, m, RVI].astype(float))
    DVv.append(np.exp(-src.CH[ti, m, DVI].astype(float)) if DVI is not None else np.ones(len(m)))
    RET.append(src.Y4[ti, m].astype(float))
n = len(a)

def run(al, lm):
    prev = None; pnl = np.zeros(n); trn = np.zeros(n); ric = np.full(n, np.nan)
    for i in range(n):
        rb = None if (al == 1. and lm == 0.) else {"alpha": al, "lambda": lm}
        r = LG.compose_book(KK[i], SS[i], FF[i], DVv[i], weights=W,
                            rvol=RV[i] if rb else None, risk_budget=rb)
        w = np.asarray(r["target_w"], float); y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[ok]*y[ok]))
        cur = dict(zip(M[i], w))
        trn[i] = 0. if prev is None else sum(abs(cur.get(x, 0.)-prev.get(x, 0.)) for x in set(cur) | set(prev))
        if ok.sum() >= 10:
            ric[i] = float(np.corrcoef(pd.Series(w[ok]).rank(), pd.Series(y[ok]).rank())[0, 1])
        prev = cur
    return pnl, trn, ric

def boot(d, nb=3000, bl=5):
    rng = np.random.default_rng(99); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()*1e4
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

ARMS = [("M0 线性", 1., 0.), ("M1 只压幅度", .5, 0.), ("M2 只除波动", 1., 1.), ("M3 在役", .5, 1.)]
R = {}
print(f"\n{'臂':14s}{'毛bps':>9s}{'秩IC':>9s}{'换手':>8s}" +
      "".join(f"{'净@'+str(c):>9s}{'夏普':>8s}" for c in COSTS))
for nm, al, lm in ARMS:
    p, t, ic = run(al, lm); R[nm] = (p, t, ic)
    g = p.mean()*1e4; tt = t.sum()/len(t); row = f"{nm:14s}{g:+9.3f}{np.nanmean(ic):+9.5f}{tt:8.4f}"
    for c in COSTS:
        np_ = p*1e4 - t*2*c
        row += f"{np_.mean():+9.3f}{np_.mean()/np_.std(ddof=1)*ANN:+8.2f}"
    print(row, flush=True)

m3g = R["M3 在役"][0].mean()*1e4; m3t = R["M3 在役"][1].sum()/n
p2 = abs(m3g-1.832)/1.832 <= .15 and abs(m3t-0.4707)/0.4707 <= .15
print(f"\nP2 M3 vs 引擎S0(+1.832/0.4707): 毛 {m3g:+.3f}({(m3g/1.832-1)*100:+.1f}%) "
      f"换手 {m3t:.4f}({(m3t/0.4707-1)*100:+.1f}%) ⇒ {'在±15%内' if p2 else '★超出 ⇒ 两装置差异不止风险预算, 数字不得混用'}")

print("\n" + "═"*80); print("判据(对 M3 在役)"); print("═"*80)
out = {}
for nm, _, _ in ARMS[:3]:
    p, t, _ = R[nm]; p3, t3, _ = R["M3 在役"]
    g1 = True; line = f"  {nm:12s}"
    for c in COSTS:
        dn = (p*1e4 - t*2*c) - (p3*1e4 - t3*2*c)
        lo, hi = boot(dn/1e4)
        g1 = g1 and lo > 0
        line += f"  Δ净@{c}={dn.mean():+7.3f} CI[{lo:+.3f},{hi:+.3f}]"
    dfy = pd.DataFrame({"y": yr, "d": ((p*1e4-t*2*3.115)-(p3*1e4-t3*2*3.115))}).groupby("y").d.mean()
    npos = int((dfy >= 0).sum()); g2 = npos/len(dfy) >= .8
    s_ = {c: float((p*1e4-t*2*c).mean()/(p*1e4-t*2*c).std(ddof=1)*ANN) for c in COSTS}
    s3 = {c: float((p3*1e4-t3*2*c).mean()/(p3*1e4-t3*2*c).std(ddof=1)*ANN) for c in COSTS}
    g3 = all(s_[c] > s3[c] for c in COSTS)
    print(line)
    print(f"        G1={'PASS' if g1 else 'FAIL'}  G2 逐年 {npos}/{len(dfy)}={'PASS' if g2 else 'FAIL'}  "
          f"G3 净夏普 {[round(s_[c],2) for c in COSTS]} vs 在役 {[round(s3[c],2) for c in COSTS]}"
          f"={'PASS' if g3 else 'FAIL'}   逐年 {dict(dfy.round(3))}")
    out[nm] = {"G1": bool(g1), "G2": bool(g2), "G3": bool(g3),
               "per_year": {int(k): round(float(v), 4) for k, v in dfy.items()}}
out["P2"] = bool(p2); out["arms"] = {k: {"gross": float(v[0].mean()*1e4),
                                          "turn": float(v[1].sum()/n),
                                          "rank_ic": float(np.nanmean(v[2]))} for k, v in R.items()}
print("\nG4 与 50 锚一致性: 50 锚排序 M0>M1≈M2>M3 (净@3.115 +4.311/+2.873/+1.512/+1.158)")
print(f"   9821 锚排序: " + " > ".join(sorted(R, key=lambda k: -(R[k][0].mean()*1e4 - R[k][1].sum()/n*2*3.115))))
json.dump(out, open(f"{PD}/map4.json", "w"), indent=1)
print(f"\n[done] {time.time()-t0:.0f}s\nMAP4_DONE")
