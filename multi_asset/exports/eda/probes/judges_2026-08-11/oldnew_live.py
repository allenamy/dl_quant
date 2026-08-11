"""辅判 A —— 实盘两段(旧脏模型 / 换装后)的差有没有判别力。
预注册 PREREG_oldnew_coincidence 7db1a08b @ 13:35:40Z
A1 日块 bootstrap CI   A2 N* 功效   A3 状态匹配(Mann-Whitney)
只用实盘一手记录; 换装点 = 2026-08-05 19:06Z (deff3bb)。
"""
import json, glob, numpy as np, pandas as pd, datetime as dt
from scipy.stats import mannwhitneyu

LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"   # ★ 只读 live 树, 非 DRY_RUN
SWAP = dt.datetime(2026, 8, 5, 19, 6, tzinfo=dt.timezone.utc).timestamp()

mids, tw = {}, {}
for f in sorted(glob.glob(f"{LIVE}/2026*/anchors.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except Exception: continue
        mv = d.get("mid_at_anchor_vector")
        if isinstance(mv, str):
            try: mv = json.loads(mv)
            except Exception: mv = None
        if d.get("anchor_ts") and mv: mids[round(float(d["anchor_ts"]))] = mv
for f in sorted(glob.glob(f"{LIVE}/2026*/orders.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except Exception: continue
        a = d.get("anchor_ts")
        if a and d.get("symbol") and d.get("target_w") is not None:
            tw.setdefault(round(float(a)), {})[d["symbol"]] = float(d["target_w"])

K = sorted(mids); rows = []
for i, a in enumerate(K[:-1]):
    if a not in tw: continue
    m0, m1 = mids[a], mids[K[i+1]]
    prev = mids[K[i-1]] if i > 0 else None
    w = tw[a]
    s = [x for x in w if x in m0 and x in m1 and m0[x] and m1[x] > 0 and abs(w[x]) > 1e-12]
    if len(s) < 20: continue
    wv = np.array([w[x] for x in s]); rv = np.array([m1[x]/m0[x]-1 for x in s])
    ic = float(pd.Series(wv).corr(pd.Series(rv), method="spearman"))
    g = np.abs(wv).sum()
    rev = np.nan
    if prev is not None:
        s2 = [x for x in s if x in prev and prev[x]]
        if len(s2) >= 20:
            rp = np.array([m0[x]/prev[x]-1 for x in s2]); rn = np.array([m1[x]/m0[x]-1 for x in s2])
            rev = float(pd.Series(rp).corr(pd.Series(rn), method="spearman"))
    rows.append({"ts": a, "t": dt.datetime.fromtimestamp(a, dt.timezone.utc),
                 "gen": "old(脏)" if a < SWAP else "new(在役)", "ic": ic,
                 "gross_bps": float((wv*rv).sum()/g*1e4),
                 "disp_bps": float(np.std(rv)*1e4), "absmkt_bps": float(abs(np.mean(rv))*1e4),
                 "self_rev": rev, "day": int(a//86400)})
d = pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)
print(f"实盘锚 n={len(d)}   跨度 {d.t.min():%m-%d %HZ} → {d.t.max():%m-%d %HZ}")
print("═"*78); print("两段对照"); print("═"*78)
g = d.groupby("gen").agg(n=("ic", "size"), ic=("ic", "mean"), ic_sd=("ic", "std"),
                         gross=("gross_bps", "mean"), disp=("disp_bps", "mean"),
                         absmkt=("absmkt_bps", "mean"), rev=("self_rev", "mean"))
print(g.round(4).to_string())

O = d[d.gen == "old(脏)"]; N = d[d.gen == "new(在役)"]
if len(O) < 5 or len(N) < 5:
    print(f"\n★ 一侧样本 <5 (old={len(O)} new={len(N)}) ⇒ 辅判 A 不出结论"); raise SystemExit

def dayboot(x, y, nb=5000):
    """日块 bootstrap: 两段独立重抽【天】, 差的分布。"""
    rng = np.random.default_rng(7)
    dx = [v.ic.values for _, v in x.groupby("day")]; dy = [v.ic.values for _, v in y.groupby("day")]
    out = np.empty(nb)
    for k in range(nb):
        a = np.concatenate([dx[i] for i in rng.integers(0, len(dx), len(dx))])
        b = np.concatenate([dy[i] for i in rng.integers(0, len(dy), len(dy))])
        out[k] = a.mean() - b.mean()
    return out

bs = dayboot(O, N)
diff = O.ic.mean() - N.ic.mean()
lo, hi = np.percentile(bs, [2.5, 97.5])
print("\n" + "═"*78); print("A1 · 差的显著性(日块 bootstrap, 两段各自重抽天)"); print("═"*78)
print(f"  ΔIC(old − new) = {diff:+.4f}   CI95 [{lo:+.4f}, {hi:+.4f}]   "
      f"p(双侧)≈{2*min((bs<=0).mean(), (bs>=0).mean()):.3f}")
cov0 = lo <= 0 <= hi
print(f"  ⇒ {'覆盖 0 ⇒ 支持 E1(巧合/样本不足), E3 在实盘证据上【不成立】' if cov0 else '排除 0 ⇒ 差是真的, 但仍需 M 判别 E2 vs E3'}")

print("\n" + "═"*78); print("A2 · 功效: 要多少锚才能判这么大的差"); print("═"*78)
sd = float(np.sqrt(O.ic.var(ddof=1)/1 + N.ic.var(ddof=1)/1))
sd_pool = float(np.sqrt((O.ic.var(ddof=1)*(len(O)-1) + N.ic.var(ddof=1)*(len(N)-1))/(len(O)+len(N)-2)))
for mde in (abs(diff), 0.05, 0.10):
    ns = int(np.ceil(7.8489*2*sd_pool**2/mde**2))
    print(f"  MDE={mde:.4f}: 每段需 N*={ns:,} 锚 (= {ns/6:.0f} 天)   现有 old={len(O)} new={len(N)}")
nstar = int(np.ceil(7.8489*2*sd_pool**2/max(abs(diff), 1e-9)**2))
print(f"  ⇒ 对【观察到的差本身】N*={nstar}, 现有最小段 n={min(len(O),len(N))}  "
      f"⇒ {'★ 样本不足 ' + str(round(nstar/min(len(O),len(N)),1)) + '× ⇒ 实盘对本命题【无判别力】' if nstar > 3*min(len(O),len(N)) else '样本够'}")

print("\n" + "═"*78); print("A3 · 两段的市场状态是不是同一个(E2 检验)"); print("═"*78)
for c, lbl in [("disp_bps", "横截面离散度"), ("absmkt_bps", "|市场收益|"), ("self_rev", "自反转强度")]:
    a = O[c].dropna().values; b = N[c].dropna().values
    if len(a) >= 5 and len(b) >= 5:
        u, p = mannwhitneyu(a, b)
        flag = "★状态不同 ⇒ 支持 E2" if p < 0.05 else "状态可比"
        print(f"  {lbl:12s} old {a.mean():+9.4f}  new {b.mean():+9.4f}   p={p:.4f}  {flag}")

print("\n" + "═"*78); print("逐锚明细(换装边界 ±6 锚)"); print("═"*78)
i0 = int((d.ts < SWAP).sum())
print(d.iloc[max(0, i0-6):i0+8][["t", "gen", "ic", "gross_bps", "disp_bps", "self_rev"]]
      .to_string(index=False, float_format=lambda x: f"{x:+.4f}"))
d.to_csv("/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/oldnew_live.csv", index=False)
