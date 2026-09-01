"""V2L38 同座替换判官 @jpline(判据冻结 08-26 + L1): ΔNet(V2L38−V2MAIN 同种子同网格 w10)块自举(块=6锚, 4000次, 成对同锚)95%CI 下界>0 双种子同向; 逐年≥−0.5; 换手+25%即负。"""
import numpy as np, time
PD = "/mnt/storage/private/work_hsy/probe_artifacts"
rng = np.random.default_rng(0)
def series(run):
    z = np.load(f"{PD}/{run}.npz", allow_pickle=True)
    cols = [str(c) for c in z["cols"]]; rec = z["d30_n2_c42_rec"]
    return (rec[:, cols.index("ts")].astype(np.int64), rec[:, cols.index("net_ex")].astype(np.float64),
            rec[:, cols.index("turnover")].astype(np.float64))
verd = []
for S in ("s42", "s2027"):
    tb, nb, tob = series(f"w10_v2gate_{S}_OLD9")
    tl, nl, tol = series(f"w10_l38_{S}")
    assert np.array_equal(tb, tl)
    yrs = np.array([time.gmtime(int(t)).tm_year for t in tb])
    sel = yrs >= 2023
    d = (nl - nb)[sel]
    nb6 = len(d) // 6
    blocks = d[:nb6 * 6].reshape(nb6, 6).sum(1)
    boots = np.array([blocks[rng.integers(0, nb6, nb6)].mean() for _ in range(4000)]) / 6
    lo, hi = np.quantile(boots, [0.025, 0.975])
    yr_ok = True
    yl = {}
    for y in (2023, 2024, 2025, 2026):
        sy = yrs == y
        dy = (nl - nb)[sy].mean(); yl[y] = round(dy, 3)
        if dy < -0.5: yr_ok = False
    to_chg = (tol[sel].mean() / max(tob[sel].mean(), 1e-9) - 1)
    ok = lo > 0 and yr_ok and to_chg <= 0.25
    verd.append(ok)
    print(f"[{S}] ΔNet {d.mean():+.4f} 块自举95%CI [{lo:+.4f},{hi:+.4f}] 逐年Δ {yl} 换手变化 {to_chg*100:+.1f}% -> {'过' if ok else '不过'}", flush=True)
print("L38_SEAT_GATE", "PASS" if all(verd) else "FAIL", flush=True)
