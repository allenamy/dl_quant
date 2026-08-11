"""把"交互"打开: 风险预算拆成 ①幅度压缩 α ②按波动反向加权 λ, 与两代交叉 = 2×4。
★ 诊断实验, 非录取实验 —— 任何采纳都需另立预注册。判据不在此文, 只报数与机制。
装置 = 实盘 signal/legs.py compose_book(与 2×2 v2 同一份, G0 已过)。
"""
import json, os, sys
import numpy as np, pandas as pd
REPO = os.path.expanduser("~/dl_quant_live")
sys.path[:0] = [os.path.join(REPO, "signal"), os.path.join(REPO, "live"), REPO]
SP = os.path.dirname(os.path.abspath(__file__)); CACHE = os.path.join(SP, "panel_cache")
import legs as LG, inference as INF
NEW_DIR = os.path.join(REPO, "checkpoints")
OLD_DIR = os.path.join(REPO, "rollback_batch1_20260804T145921Z", "checkpoints")
CUT, FLOOR = 1785542400000, 887
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
COSTS = [3.115, 5.80]

P = {}
for tag, f in (("new", "panel_normfix_full.npz"), ("old", "panel_as_trained_same.npz")):
    z_ = np.load(os.path.join(CACHE, f), allow_pickle=True); P[tag] = {k: z_[k] for k in z_.files}
ts = P["new"]["ts"]; syms = [str(s) for s in P["new"]["symbols"]]
CLOSE = P["new"]["CLOSE"].astype(float); MEM = P["new"]["member"]; DV = P["new"]["DVOL30"].astype(float)
chn = [str(c) for c in P["new"]["ch_names"]]
FI, RVI = chn.index("funding_ema"), chn.index("rvol_24h")
MI = chn.index("mom_24h") if "mom_24h" in chn else None
print("mom_24h ch =", MI, "| 通道样例:", chn[:6])

G = {}
for tag, d in (("new", NEW_DIR), ("old", OLD_DIR)):
    G[tag], _ = INF.load(stats_path=os.path.join(d, "norm_stats.npz"), ckpt_dir=d)
idx = [i for i in range(FLOOR, len(ts)-4) if int(ts[i]) % (4*3600*1000) == 0 and int(ts[i]) >= CUT]
KP, S2 = {"new": [], "old": []}, {"new": [], "old": []}
FUND, DVOL, RVOL, MOM, RET, MSK = [], [], [], [], [], []
for i in idx:
    m = MEM[i].astype(bool)
    if m.sum() < 20: continue
    y = np.full(len(syms), np.nan); c0, c1 = CLOSE[i], CLOSE[i+4]
    ok = np.isfinite(c0) & np.isfinite(c1) & (c0 > 0); y[ok] = c1[ok]/c0[ok]-1.
    RET.append(y[m]); MSK.append(m)
    FUND.append(P["new"]["CH"][i, m, FI].astype(float)); DVOL.append(DV[i, m])
    RVOL.append(P["new"]["CH"][i, m, RVI].astype(float))
    MOM.append(P["new"]["CH"][i, m, MI].astype(float) if MI is not None else np.full(m.sum(), np.nan))
    for tag in ("new", "old"):
        win = P[tag]["CH"][i-INF.W+1:i+1].transpose(1, 0, 2); o = {}
        for leg in ("king", "s2"):
            c, base, _ = G[tag][leg].composite(win, m.astype(np.float32))
            v = np.full(len(syms), np.nan)
            if c is not None: v[np.asarray(base)] = c
            o[leg] = v[m]
        KP[tag].append(o["king"]); S2[tag].append(o["s2"])
n = len(RET); print(f"{n} 锚\n")

def pear(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 10: return np.nan
    x, y = a[ok]-a[ok].mean(), b[ok]-b[ok].mean()
    d = np.sqrt((x*x).sum()*(y*y).sum())
    return float((x*y).sum()/d) if d > 0 else np.nan

def run(tag, al, lm):
    prev = None; pnl = np.zeros(n); trn = np.zeros(n); ric = np.full(n, np.nan); pic = np.full(n, np.nan)
    for i in range(n):
        rb = None if (al == 1. and lm == 0.) else {"alpha": al, "lambda": lm}
        r = LG.compose_book(KP[tag][i], S2[tag][i], FUND[i], DVOL[i], weights=W,
                            rvol=RVOL[i] if rb else None, risk_budget=rb)
        w = np.asarray(r["target_w"], float); y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[ok]*y[ok]))
        cur = dict(zip(np.where(MSK[i])[0], w))
        trn[i] = 0. if prev is None else sum(abs(cur.get(x, 0.)-prev.get(x, 0.)) for x in set(cur) | set(prev))
        if ok.sum() >= 10:
            ric[i] = float(np.corrcoef(pd.Series(w[ok]).rank(), pd.Series(y[ok]).rank())[0, 1])
            pic[i] = pear(w[ok], y[ok])
        prev = cur
    return pnl, trn, ric, pic

MAP = [("M0 线性(α1 λ0)", 1., 0.), ("M1 只压幅度(α.5 λ0)", .5, 0.),
       ("M2 只除波动(α1 λ1)", 1., 1.), ("M3 在役(α.5 λ1)", .5, 1.)]
print(f"{'代':4s}{'映射':22s}{'毛bps':>9s}{'秩IC':>9s}{'值IC':>9s}{'换手':>8s}" +
      "".join(f"{'净@'+str(c):>9s}" for c in COSTS))
R = {}
for tag in ("old", "new"):
    for nm, al, lm in MAP:
        p, t, ic, pi = run(tag, al, lm); R[(tag, nm)] = (p, t, ic, pi)
        g = p.mean()*1e4; tt = t.sum()/len(t)
        print(f"{tag:4s}{nm:22s}{g:+9.3f}{np.nanmean(ic):+9.5f}{np.nanmean(pi):+9.5f}{tt:8.4f}" +
              "".join(f"{g-tt*2*c:+9.3f}" for c in COSTS), flush=True)
    print()

print("═"*86); print("★ 拆开: 每一半单独让哪一代损失多少毛额(相对 M0 线性)"); print("═"*86)
for nm, _, _ in MAP[1:]:
    do = (R[("old", nm)][0]-R[("old", MAP[0][0])][0]).mean()*1e4
    dn = (R[("new", nm)][0]-R[("new", MAP[0][0])][0]).mean()*1e4
    print(f"  {nm:22s} 旧代 {do:+7.3f}   新代 {dn:+7.3f}   差(新−旧) {dn-do:+7.3f}"
          f"   {'★新代受损更重' if dn < do else ''}")

print("\n" + "═"*86); print("★ 机制诊断: 分数与波动/动量的横截面关系(逐锚均值)"); print("═"*86)
for tag in ("old", "new"):
    cs_rv, cs_mo, cs_absrv = [], [], []
    for i in range(n):
        combo = W["king"]*LG.z(KP[tag][i]) + W["s2"]*LG.z(S2[tag][i]) + \
                W["funding"]*LG.SIGNS["funding"]*LG.rank_centered(FUND[i])
        cs_rv.append(pear(combo, RVOL[i])); cs_absrv.append(pear(np.abs(combo), RVOL[i]))
        cs_mo.append(pear(combo, MOM[i]))
    print(f"  {tag}: corr(分数, rvol)={np.nanmean(cs_rv):+.4f}   "
          f"corr(|分数|, rvol)={np.nanmean(cs_absrv):+.4f}   corr(分数, mom_24h)={np.nanmean(cs_mo):+.4f}")
print("\n  判读: |分数| 与 rvol 正相关越强 ⇒ 除以 σ 压掉的正是它最有把握的仓位")
json.dump({f"{k[0]}|{k[1]}": {"gross": float(v[0].mean()*1e4), "rank_ic": float(np.nanmean(v[2])),
                              "val_ic": float(np.nanmean(v[3])), "turn": float(v[1].sum()/len(v[1]))}
           for k, v in R.items()}, open(os.path.join(SP, "interaction.json"), "w"), indent=1)
print("\nINTERACTION_DONE")
