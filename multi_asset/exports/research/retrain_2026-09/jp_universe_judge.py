"""宇宙 A/B 判官 @jpline(PREREG addendum §B 判据逐字): U1/U2 vs U0 — ΔNet CI>0 双种子 / ES5 不劣化>10% / 负档空头暴露增幅<=50%; 另报最坏五分位与 U∞ 参照。"""
import numpy as np, time
PD = "/mnt/storage/private/work_hsy/probe_artifacts"
B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
PW = np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pw_ts = PW["ts"].astype(np.int64); prow = {int(t): j for j, t in enumerate(pw_ts)}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
rng = np.random.default_rng(0)
def load(run):
    z = np.load(f"{PD}/{run}.npz", allow_pickle=True)
    cols = [str(c) for c in z["cols"]]; rec = z["d30_n2_c42_rec"]
    return (rec[:, cols.index("ts")].astype(np.int64), rec[:, cols.index("net_ex")].astype(np.float64), z["d30_n2_c42_W"])
def expo(ts, W):
    out = np.full(len(ts), np.nan)
    for p, t in enumerate(ts):
        j = prow.get(int(t))
        if j is None: continue
        w = W[p]
        iv = IV[j]; iv = np.where(np.isfinite(iv) & (iv > 0), iv, 8.0)
        fn = np.nan_to_num(FN[j]) * (8.0 / iv)
        sh = w < -1e-9
        g = np.abs(w).sum()
        if g > 1e-9: out[p] = np.abs(w[sh & (fn < -0.0010)]).sum() / g
    return out
stats = {}
for arm in ("U0", "U1", "U2", "Uinf"):
    runs = {}
    for S in ("s42", "s2027"):
        name = f"w10_v2gate_{S}_NEW9" if arm == "Uinf" else f"w10_uni_{arm}_{S}"
        runs[S] = load(name)
    stats[arm] = runs
ts0 = stats["U0"]["s42"][0]
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts0]); sel = yrs >= 2023
for arm in ("U0", "U1", "U2", "Uinf"):
    for S in ("s42",):
        ts, ne, W = stats[arm][S]
        r = ne[sel]
        es5 = np.sort(r)[: max(1, int(len(r) * 0.05))].mean()
        wq = np.sort(r)[: max(1, int(len(r) * 0.20))].mean()
        ex = np.nanmean(expo(ts[sel][::6], W[sel][::6]))
        print(f"[{arm}][{S}] 净 {r.mean():+.3f} ES5 {es5:+.1f} 最坏五分位 {wq:+.2f} 负档空头暴露 {ex*100:.1f}%", flush=True)
for arm in ("U1", "U2"):
    verd = []
    for S in ("s42", "s2027"):
        _, n0, _ = stats["U0"][S]; _, na, _ = stats[arm][S]
        d = (na - n0)[sel]
        nb6 = len(d) // 6; blocks = d[:nb6 * 6].reshape(nb6, 6).sum(1)
        boots = np.array([blocks[rng.integers(0, nb6, nb6)].mean() for _ in range(4000)]) / 6
        lo, hi = np.quantile(boots, [0.025, 0.975])
        r0 = n0[sel]; ra = na[sel]
        es0 = np.sort(r0)[: max(1, int(len(r0) * 0.05))].mean(); esa = np.sort(ra)[: max(1, int(len(ra) * 0.05))].mean()
        es_ok = esa >= es0 * 1.10 if es0 < 0 else esa >= es0 * 0.90
        _, _, W0 = stats["U0"][S]; _, _, Wa = stats[arm][S]
        e0 = np.nanmean(expo(stats["U0"][S][0][sel][::6], W0[sel][::6]))
        ea = np.nanmean(expo(stats[arm][S][0][sel][::6], Wa[sel][::6]))
        ex_ok = ea <= e0 * 1.5
        ok = lo > 0 and es_ok and ex_ok
        verd.append(ok)
        print(f"[{arm} vs U0][{S}] ΔNet {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] ES5 {es0:+.1f}->{esa:+.1f}({'OK' if es_ok else 'FAIL'}) 暴露 {e0*100:.1f}%->{ea*100:.1f}%({'OK' if ex_ok else 'FAIL'}) -> {'过' if ok else '不过'}", flush=True)
    print(f"== {arm}: {'ADMIT' if all(verd) else 'REJECT'}", flush=True)
print("UNIVERSE_JUDGE_DONE", flush=True)
