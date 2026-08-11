"""2×2 因子: 把"换装变差"拆成 模型效应 / 装置效应 / 交互
预注册 PREREG_2x2_swap_attribution_2026-08-09 FROZEN ec9c2917… @ 14:34:29Z
A 旧分数×旧装置 | B 新分数×新装置 | C 旧分数×新装置 | D 新分数×旧装置
G0 与实盘一致性(corr≥0.5, 会红) → G1 总差 → G2 分解(≥50%且CI排0才算主因) → G3 净额 → G4 功效
★ funding 腿是【重建】(面板 funding_ema rank-center), 四臂逐位相同 ⇒ 不偏 2×2 的对比, 但会影响 G0。
"""
import json, os, sys, glob, datetime as dt
import numpy as np, pandas as pd
REPO = os.path.expanduser("~/dl_quant_live")
sys.path[:0] = [os.path.join(REPO, "signal"), os.path.join(REPO, "live"), REPO]
SP = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(SP, "panel_cache")
NEW_DIR = os.path.join(REPO, "checkpoints")
OLD_DIR = os.path.join(REPO, "rollback_batch1_20260804T145921Z", "checkpoints")
CUT, FLOOR = 1785542400000, 887
W = {"king": 0.5952380952380952, "s2": 0.20238095238095238, "funding": 0.20238095238095238}
COSTS = [3.115, 5.80]

P = {}
for tag, f in (("new", "panel_normfix_full.npz"), ("old", "panel_as_trained_same.npz")):
    z = np.load(os.path.join(CACHE, f), allow_pickle=True)
    P[tag] = {k: z[k] for k in z.files}
    print(f"[{tag}] {f}  CH{P[tag]['CH'].shape}")
ts = P["new"]["ts"]; syms = [str(s) for s in P["new"]["symbols"]]
CLOSE = P["new"]["CLOSE"].astype(float); MEM = P["new"]["member"]
chn = [str(c) for c in P["new"]["ch_names"]]
FI = chn.index("funding_ema")
assert np.array_equal(ts, P["old"]["ts"]), "两面板时间轴不同"
assert not np.array_equal(P["new"]["CH"][:, :, 31], P["old"]["CH"][:, :, 31]), "★ch31 相同 ⇒ 口径没切"

import inference as INF
G = {}
for tag, d in (("new", NEW_DIR), ("old", OLD_DIR)):
    G[tag], _ = INF.load(stats_path=os.path.join(d, "norm_stats.npz"), ckpt_dir=d)

idx = [i for i in range(FLOOR, len(ts)-4) if int(ts[i]) % (4*3600*1000) == 0 and int(ts[i]) >= CUT]
print(f"{len(idx)} 锚\n")

def zc(v):
    s = np.nanstd(v); return (v-np.nanmean(v))/s if s > 0 else v*np.nan

def shape99(s):
    a = np.abs(s); c = np.percentile(a[np.isfinite(a)], 99) if np.isfinite(a).any() else 0
    s = np.clip(s, -c, c); s = s - s.mean()
    return np.sign(s)*np.abs(s)**0.5

SC, FUND, RVOL, RET, MASK = {"new": [], "old": []}, [], [], [], []
RVI = chn.index("rvol_24h")
for i in idx:
    m = MEM[i].astype(bool)
    if m.sum() < 20: continue
    MASK.append(m)
    y = np.full(len(syms), np.nan)
    c0, c1 = CLOSE[i], CLOSE[i+4]
    ok = np.isfinite(c0) & np.isfinite(c1) & (c0 > 0)
    y[ok] = c1[ok]/c0[ok]-1.0; y[~m] = np.nan
    RET.append(y[m])
    RVOL.append(P["new"]["CH"][i, m, RVI].astype(float))
    f = P["new"]["CH"][i, m, FI].astype(float)               # ★ 四臂共用
    r = pd.Series(f).rank(pct=True).values
    FUND.append(-(r - r.mean()))                              # funding 高 ⇒ 做空
    for tag in ("new", "old"):
        win = P[tag]["CH"][i-INF.W+1:i+1].transpose(1, 0, 2)
        legs = {}
        for leg in ("king", "s2"):
            c, base, _ = G[tag][leg].composite(win, m.astype(np.float32))
            v = np.full(len(syms), np.nan)
            if c is not None: v[np.asarray(base)] = c
            legs[leg] = v[m]
        SC[tag].append((zc(legs["king"]), zc(legs["s2"])))

n = len(RET); print(f"可打分 {n} 锚")

def run(score_tag, rb_on):
    prev = None; pnl = np.zeros(n); trn = np.zeros(n); ric = np.full(n, np.nan)
    for i in range(n):
        k, s2 = SC[score_tag][i]
        raw = W["king"]*np.nan_to_num(k) + W["s2"]*np.nan_to_num(s2) + W["funding"]*FUND[i]
        sh = shape99(raw)
        if rb_on:
            v = RVOL[i]; fin = np.isfinite(v) & (v > 0)
            med = float(np.median(v[fin])) if fin.any() else 0.0
            if med > 0:
                v = np.where(fin, v, med)
                sh = np.sign(sh)*np.abs(sh)**0.5/(v/med)
                sh = sh - sh.mean()
        g = np.abs(sh).sum()
        if g > 1e-12: sh = sh/g
        r = RET[i]; ok = np.isfinite(r)
        pnl[i] = float(np.nansum(sh[ok]*r[ok]))
        cur = dict(zip(np.where(MASK[i])[0], sh))
        trn[i] = 0.0 if prev is None else sum(abs(cur.get(x, 0.)-prev.get(x, 0.))
                                              for x in set(cur) | set(prev))
        if ok.sum() >= 10:
            ric[i] = float(np.corrcoef(pd.Series(sh[ok]).rank(), pd.Series(r[ok]).rank())[0, 1])
        prev = cur
    return pnl, trn, ric

ARM = {"A 旧分数×旧装置": ("old", False), "B 新分数×新装置": ("new", True),
       "C 旧分数×新装置": ("old", True),  "D 新分数×旧装置": ("new", False)}
R = {}
print(f"\n{'臂':18s} {'毛bps':>9s} {'秩IC':>9s} {'换手':>8s} " + " ".join(f"{'净@'+str(c):>9s}" for c in COSTS))
for nm, (st, rb) in ARM.items():
    p, t, ic = run(st, rb); R[nm] = (p, t, ic)
    g = p.mean()*1e4; tt = t.sum()/len(t)
    print(f"{nm:18s} {g:+9.3f} {np.nanmean(ic):+9.5f} {tt:8.4f} " +
          " ".join(f"{g-tt*2*c:+9.3f}" for c in COSTS))

# ─── G0 与实盘一致性 ───
L = pd.read_csv(os.path.join(SP, "oldnew_live_v2.csv")); L["k"] = (L.ts//14400).astype(int)
kk = [int(ts[i])//1000//14400 for i in idx][:n]
mine = pd.DataFrame({"k": kk, "A": R["A 旧分数×旧装置"][2], "B": R["B 新分数×新装置"][2]})
mg = mine.merge(L[["k", "gen", "ic"]], on="k", how="inner")
o = mg[mg.gen == "as_trained_broken_v1"]; nw = mg[mg.gen == "corrfund_causal_ac"]
c_o = o.A.corr(o.ic); c_n = nw.B.corr(nw.ic)
print(f"\nG0 一致性: A vs 实盘换装前 corr={c_o:+.4f} (n={len(o)})   B vs 实盘换装后 corr={c_n:+.4f} (n={len(nw)})")
g0 = (c_o >= 0.5) and (c_n >= 0.5)
print(f"   ⇒ G0 {'PASS' if g0 else '★FAIL —— 按预注册, 整门作废, 不调参数'}")

def boot(d, nb=5000, bl=3):
    rng = np.random.default_rng(11); N = len(d); k = int(np.ceil(N/bl)); o_ = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(N-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:N]; ix = ix[ix < N]
        o_[q] = d[ix].mean()*1e4
    return float(np.percentile(o_, 2.5)), float(np.percentile(o_, 97.5))

A, B, C, D = (R[k][0] for k in ["A 旧分数×旧装置", "B 新分数×新装置", "C 旧分数×新装置", "D 新分数×旧装置"])
tot = B - A; lo, hi = boot(tot)
print(f"\nG1 总差 B−A = {tot.mean()*1e4:+.3f} bps  CI95[{lo:+.3f},{hi:+.3f}]  "
      f"{'⇒ 覆盖0: 总差不显著' if lo <= 0 <= hi else ('⇒ 新书更差' if hi < 0 else '⇒ 新书更好')}")
sd = tot.std(ddof=1)*1e4
print(f"G4 功效: N* = {int(np.ceil(7.8489*sd**2/max(abs(tot.mean()*1e4),1e-9)**2))}  现有 n={n}")
if tot.mean() >= 0:
    print("\n⇒ G1 判: 新书在同锚上【不差】 ⇒ 实盘那个差不在模型也不在装置, 归于锚点/市场。G2 按预注册不读。")
else:
    print("\nG2 分解(仅因 B−A<0 才读):")
    for nm, d_ in [("装置效应 C−A", C-A), ("模型效应 D−A", D-A),
                   ("交互", (B-A)-(C-A)-(D-A))]:
        l2, h2 = boot(d_)
        share = abs(d_.mean()/tot.mean()) if abs(tot.mean()) > 0 else 0
        print(f"   {nm:12s} {d_.mean()*1e4:+7.3f} bps  CI95[{l2:+.3f},{h2:+.3f}]  占总差 {share:.0%}  "
              f"{'★主因' if share >= 0.5 and not (l2 <= 0 <= h2) else ''}")
json.dump({"arms": {k: {"gross": float(v[0].mean()*1e4), "ic": float(np.nanmean(v[2])),
                        "turn": float(v[1].sum()/len(v[1]))} for k, v in R.items()},
           "G0": {"corr_A_live": float(c_o), "corr_B_live": float(c_n), "pass": bool(g0)},
           "G1": {"delta": float(tot.mean()*1e4), "ci": [lo, hi]}, "n": n,
           "prereg": "ec9c291740fcba6934f0b7d38a8a4b9f8c46e7f42b93ce7fd89a50d9fece140e"},
          open(os.path.join(SP, "attr2x2.json"), "w"), indent=1)
print("\nATTR2X2_DONE")
