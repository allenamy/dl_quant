"""反解 betaadj_ret24 用的市场窗: 中心(含11h未来,脏) vs 因果(干净)。"""
import numpy as np, sys
for p in sys.argv[1:]:
    z = np.load(p, allow_pickle=True)
    n = [str(x) for x in z["ch_names"]]
    if "betaadj_ret24" not in n:
        print("%-42s 无该通道" % p.split("/")[-1]); continue
    CH = z["CH"]; MEM = z["MEMBER110"]
    r1 = CH[:, :, n.index("ret_1h")].astype(np.float64)
    r24 = CH[:, :, n.index("ret_24h")].astype(np.float64)
    bt = CH[:, :, n.index("beta_24h")].astype(np.float64)
    bj = CH[:, :, n.index("betaadj_ret24")].astype(np.float64)
    T, N = r1.shape
    mk = np.nan_to_num(np.nanmean(np.where(r1 != 0, r1, np.nan), axis=1))
    cent = np.convolve(mk, np.ones(24), "same")
    caus = np.convolve(mk, np.ones(24), "full")[:T]
    ok = MEM & (np.abs(bt) > 0.3) & (r24 != 0) & (bj != 0)
    imp = np.full(T, np.nan)
    for t in range(T):
        m = ok[t]
        if m.sum() >= 15: imp[t] = np.nanmedian((r24[t, m] - bj[t, m]) / bt[t, m])
    v = np.isfinite(imp) & (np.arange(T) > 200) & (np.arange(T) < T - 200)
    cc = np.corrcoef(imp[v], cent[v])[0, 1]; ca = np.corrcoef(imp[v], caus[v])[0, 1]
    print("%-42s 中心%+.4f 因果%+.4f  ⇒ %s" % (
        p.split("/")[-1], cc, ca, "★★★ 脏(含11h未来)" if cc > ca else "干净"))
