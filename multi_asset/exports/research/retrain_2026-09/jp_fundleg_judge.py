"""fund腿工程判官 @jpline(PREREG e888007fd6ae 五判据逐字)。基线 = 同种子 OLD9。"""
import numpy as np, time
PD = "/mnt/storage/private/work_hsy/probe_artifacts"
rng = np.random.default_rng(0)
def series(run):
    z = np.load(f"{PD}/{run}.npz", allow_pickle=True)
    cols = [str(c) for c in z["cols"]]; rec = z["d30_n2_c42_rec"]
    return (rec[:, cols.index("ts")].astype(np.int64), rec[:, cols.index("net_ex")].astype(np.float64),
            rec[:, cols.index("turnover")].astype(np.float64))
base = {S: series(f"w10_v2gate_{S}_OLD9") for S in ("s42", "s2027")}
for ARM in ("A1_v2cal", "A2_hl15", "A3_hl7d", "A4_dmom", "A5_gap"):
    verd = []
    for S in ("s42", "s2027"):
        tb, nb, tob = base[S]
        ta, na, toa = series(f"w10_fund_{ARM}_{S}")
        assert np.array_equal(tb, ta)
        yrs = np.array([time.gmtime(int(t)).tm_year for t in tb]); sel = yrs >= 2023
        d = (na - nb)[sel]
        nb6 = len(d) // 6; blocks = d[:nb6 * 6].reshape(nb6, 6).sum(1)
        boots = np.array([blocks[rng.integers(0, nb6, nb6)].mean() for _ in range(4000)]) / 6
        lo, hi = np.quantile(boots, [0.025, 0.975])
        yl = {y: round((na - nb)[yrs == y].mean(), 3) for y in (2023, 2024, 2025, 2026)}
        to_chg = toa[sel].mean() / max(tob[sel].mean(), 1e-9) - 1
        sg_chg = na[sel].std() / max(nb[sel].std(), 1e-9) - 1
        ok = lo > 0 and all(v >= -0.5 for v in yl.values()) and yl[2026] >= -1.0 and to_chg <= 0.25 and sg_chg <= 0.10
        verd.append(ok)
        print(f"[{ARM}][{S}] Δ {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] 年{yl} 换手{to_chg*100:+.1f}% σ{sg_chg*100:+.1f}% {'过' if ok else '不过'}", flush=True)
    print(f"== {ARM}: {'ADMIT' if all(verd) else 'REJECT'}", flush=True)
print("FUNDLEG_JUDGE_DONE", flush=True)
