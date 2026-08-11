"""2×2 因子 v2 —— 直接 import 实盘 signal/legs.py 的 compose_book, 不手搓书。
预注册 PREREG_2x2_swap_attribution_2026-08-09 FROZEN ec9c2917… 判据一字未改。
v1 的 G0 FAIL(A corr 0.4931) 归因: 手搓书漏了 per-leg l1 归一 + rank_centered 平均秩 + 无 |.|^0.5。
"""
import json, os, sys
import numpy as np, pandas as pd
REPO = os.path.expanduser("~/dl_quant_live")
sys.path[:0] = [os.path.join(REPO, "signal"), os.path.join(REPO, "live"), REPO]
SP = os.path.dirname(os.path.abspath(__file__)); CACHE = os.path.join(SP, "panel_cache")
import legs as LG, inference as INF
print(f"legs.FUNDING_MODE={LG.FUNDING_MODE}  SIGNS={LG.SIGNS}  POS_CAP_PCT={LG.POS_CAP_PCT}")

NEW_DIR = os.path.join(REPO, "checkpoints")
OLD_DIR = os.path.join(REPO, "rollback_batch1_20260804T145921Z", "checkpoints")
CUT, FLOOR = 1785542400000, 887
W = {"king": 0.5952380952380952, "s2": 0.20238095238095238,
     "funding": 0.20238095238095238, "size": 0.0}
RB = {"alpha": 0.5, "lambda": 1.0}
COSTS = [3.115, 5.80]

P = {}
for tag, f in (("new", "panel_normfix_full.npz"), ("old", "panel_as_trained_same.npz")):
    z_ = np.load(os.path.join(CACHE, f), allow_pickle=True)
    P[tag] = {k: z_[k] for k in z_.files}
ts = P["new"]["ts"]; syms = [str(s) for s in P["new"]["symbols"]]
CLOSE = P["new"]["CLOSE"].astype(float); MEM = P["new"]["member"]
DV = P["new"]["DVOL30"].astype(float)
chn = [str(c) for c in P["new"]["ch_names"]]
FI, RVI = chn.index("funding_ema"), chn.index("rvol_24h")
assert not np.array_equal(P["new"]["CH"][:, :, 31], P["old"]["CH"][:, :, 31]), "★ch31 相同"

G = {}
for tag, d in (("new", NEW_DIR), ("old", OLD_DIR)):
    G[tag], _ = INF.load(stats_path=os.path.join(d, "norm_stats.npz"), ckpt_dir=d)

idx = [i for i in range(FLOOR, len(ts)-4) if int(ts[i]) % (4*3600*1000) == 0 and int(ts[i]) >= CUT]
KP = {"new": [], "old": []}; SP_ = {"new": [], "old": []}
FUND, DVOL, RVOL, RET, MSK, TSK = [], [], [], [], [], []
for i in idx:
    m = MEM[i].astype(bool)
    if m.sum() < 20: continue
    y = np.full(len(syms), np.nan); c0, c1 = CLOSE[i], CLOSE[i+4]
    ok = np.isfinite(c0) & np.isfinite(c1) & (c0 > 0); y[ok] = c1[ok]/c0[ok]-1.0
    RET.append(y[m]); MSK.append(m); TSK.append(int(ts[i]))
    # ★ funding 腿: 面板 normfix 通道(与 compute_preds 的 build_funding_grid(NORMFIX) 同源)
    FUND.append(P["new"]["CH"][i, m, FI].astype(float))
    DVOL.append(DV[i, m]); RVOL.append(P["new"]["CH"][i, m, RVI].astype(float))
    for tag in ("new", "old"):
        win = P[tag]["CH"][i-INF.W+1:i+1].transpose(1, 0, 2)
        out = {}
        for leg in ("king", "s2"):
            c, base, _ = G[tag][leg].composite(win, m.astype(np.float32))
            v = np.full(len(syms), np.nan)
            if c is not None: v[np.asarray(base)] = c
            out[leg] = v[m]
        KP[tag].append(out["king"]); SP_[tag].append(out["s2"])
n = len(RET); print(f"可打分 {n} 锚")


def run(score_tag, rb_on):
    prev = None; pnl = np.zeros(n); trn = np.zeros(n); ric = np.full(n, np.nan)
    for i in range(n):
        r = LG.compose_book(KP[score_tag][i], SP_[score_tag][i], FUND[i], DVOL[i],
                            weights=W, rvol=RVOL[i] if rb_on else None,
                            risk_budget=RB if rb_on else None)
        w = np.asarray(r["target_w"], float)
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[ok]*y[ok]))
        cur = dict(zip(np.where(MSK[i])[0], w))
        trn[i] = 0.0 if prev is None else sum(abs(cur.get(x, 0.)-prev.get(x, 0.))
                                             for x in set(cur) | set(prev))
        if ok.sum() >= 10:
            ric[i] = float(np.corrcoef(pd.Series(w[ok]).rank(), pd.Series(y[ok]).rank())[0, 1])
        prev = cur
    return pnl, trn, ric


ARM = {"A 旧分数×旧装置": ("old", False), "B 新分数×新装置": ("new", True),
       "C 旧分数×新装置": ("old", True), "D 新分数×旧装置": ("new", False)}
R = {k: run(*v) for k, v in ARM.items()}
print(f"\n{'臂':18s} {'毛bps':>9s} {'秩IC':>9s} {'换手':>8s} " + " ".join(f"{'净@'+str(c):>9s}" for c in COSTS))
for k, (p, t, ic) in R.items():
    g = p.mean()*1e4; tt = t.sum()/len(t)
    print(f"{k:18s} {g:+9.3f} {np.nanmean(ic):+9.5f} {tt:8.4f} " +
          " ".join(f"{g-tt*2*c:+9.3f}" for c in COSTS))

L = pd.read_csv(os.path.join(SP, "oldnew_live_v2.csv")); L["k"] = (L.ts//14400).astype(int)
mine = pd.DataFrame({"k": [t//1000//14400 for t in TSK],
                     "A": R["A 旧分数×旧装置"][2], "B": R["B 新分数×新装置"][2],
                     "gA": R["A 旧分数×旧装置"][0]*1e4, "gB": R["B 新分数×新装置"][0]*1e4})
mg = mine.merge(L[["k", "gen", "ic", "gross_bps"]], on="k", how="inner")
o = mg[mg.gen == "as_trained_broken_v1"]; nw = mg[mg.gen == "corrfund_causal_ac"]
cA, cB = o.A.corr(o.ic), nw.B.corr(nw.ic)
print(f"\nG0: A vs 实盘前 corr={cA:+.4f}(n={len(o)}, 毛额 我{o.gA.mean():+.2f} vs 实盘{o.gross_bps.mean():+.2f})")
print(f"    B vs 实盘后 corr={cB:+.4f}(n={len(nw)}, 毛额 我{nw.gB.mean():+.2f} vs 实盘{nw.gross_bps.mean():+.2f})")
g0 = cA >= 0.5 and cB >= 0.5
print(f"    ⇒ G0 {'PASS' if g0 else '★FAIL —— 按预注册作废, 不调门槛'}")


def boot(d, nb=5000, bl=3):
    rng = np.random.default_rng(11); N = len(d); k = int(np.ceil(N/bl)); o_ = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(N-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:N]; ix = ix[ix < N]
        o_[q] = d[ix].mean()*1e4
    return float(np.percentile(o_, 2.5)), float(np.percentile(o_, 97.5))


A, B, C, D = (R[k][0] for k in ARM)
tot = B - A; lo, hi = boot(tot)
print(f"\nG1 总差 B−A = {tot.mean()*1e4:+.3f} bps  CI95[{lo:+.3f},{hi:+.3f}]  "
      f"{'覆盖0' if lo <= 0 <= hi else ('新书更差' if hi < 0 else '新书更好')}")
sd = tot.std(ddof=1)*1e4
print(f"G4 N* = {int(np.ceil(7.8489*sd**2/max(abs(tot.mean()*1e4),1e-9)**2))}   n={n}")
if not g0:
    print("\n⇒ G0 未过, G2 按预注册不读。")
elif tot.mean() >= 0:
    print("\n⇒ G1: 新书同锚上不差 ⇒ 差归于锚点/市场, G2 不读。")
else:
    print("\nG2 分解:")
    for nm, d_ in [("装置效应 C−A", C-A), ("模型效应 D−A", D-A), ("交互", (B-A)-(C-A)-(D-A))]:
        l2, h2 = boot(d_); sh = abs(d_.mean()/tot.mean())
        print(f"   {nm:12s} {d_.mean()*1e4:+7.3f} CI95[{l2:+.3f},{h2:+.3f}] 占 {sh:.0%} "
              f"{'★主因' if sh >= 0.5 and not (l2 <= 0 <= h2) else ''}")
json.dump({"arms": {k: {"gross": float(v[0].mean()*1e4), "ic": float(np.nanmean(v[2])),
                        "turn": float(v[1].sum()/len(v[1]))} for k, v in R.items()},
           "G0": {"cA": float(cA), "cB": float(cB), "pass": bool(g0)},
           "G1": {"delta": float(tot.mean()*1e4), "ci": [lo, hi]}, "n": n},
          open(os.path.join(SP, "attr2x2_real.json"), "w"), indent=1)
print("\nATTR2X2R_DONE")
