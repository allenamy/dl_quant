"""W2b 口径发现二(宽 meta y4 vs 1h K 线收益源)的检查脚本 @jpline; 数字见 RESULT_two_book_second_read_2026-08-22.md §3。只读。"""
import numpy as np, time, json
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
Z = np.load(f"{PD}/w2b_ret_cube.npz", allow_pickle=True); ts = Z["ts"].astype(np.int64); sym = [str(s) for s in Z["symbols"]]; RW = Z["R_wide"]; RL = Z["R_live"]
MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True); E = MT["E_ts"].astype(np.int64); y4 = MT["y4"]; members = MT["members"]
wp = {int(t): j for j, t in enumerate(E)}; wj = np.array([wp[int(t)] for t in ts])
Y = y4[wj]                                   # meta y4 aligned to common anchors (wide clock)
D = (Y - RW) * 1e4
for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "1000PEPEUSDT", "ARBUSDT"]:
    j = sym.index(s); ok = np.isfinite(Y[:, j]) & np.isfinite(RW[:, j]); d = D[ok, j]
    print(s, "n", ok.sum(), "corr %.5f" % np.corrcoef(Y[ok, j], RW[ok, j])[0, 1], "mean diff %.3f bps" % d.mean(), "mean|diff| %.2f" % np.abs(d).mean(), "p99|diff| %.1f" % np.percentile(np.abs(d), 99), "max %.1f" % np.abs(d).max())
ok = np.isfinite(Y) & np.isfinite(RW); d = D[ok]
print("ALL pairs", ok.sum(), "mean diff %.3f" % d.mean(), "median %.3f" % np.median(d), "mean|diff| %.2f" % np.abs(d).mean(), "p50 %.2f p90 %.2f p99 %.2f" % tuple(np.percentile(np.abs(d), [50, 90, 99])), "frac>100bps %.4f" % (np.abs(d) > 100).mean())
# is the diff a 5-min shift? compare meta y4 with R_live (T+1h) and R_wide (T): already known 0.98 vs ?; check sign structure: regress y4 on RW
ok2 = ok.copy(); a = np.polyfit(RW[ok2], Y[ok2], 1); print("y4 ≈ %.4f * RW + %.6f" % (a[0], a[1]))
# per-year mean diff in book-relevant names: weight by |wide target|? use wide W from W2 series
Wd = np.load(f"{PD}/w2_wide_series.npz", allow_pickle=True); cols = [str(c) for c in Wd["cols"]]; R = Wd["d30_n2_c42_rec"]; WW = Wd["d30_n2_c42_W"]; wts = R[:, 0].astype(np.int64); wpp = {int(t): j for j, t in enumerate(wts)}
yr = np.array([time.gmtime(int(t)).tm_year for t in ts]); out = {}
for y in sorted(set(yr.tolist())):
    rows = np.where(yr == y)[0]; pn_meta = []; pn_rw = []
    for i in rows:
        w = WW[wpp[int(ts[i])]].astype(float); ym = np.nan_to_num(Y[i]); rw = np.nan_to_num(RW[i])
        pn_meta.append((w * ym).sum() * 1e4); pn_rw.append((w * rw).sum() * 1e4)
    pn_meta = np.array(pn_meta); pn_rw = np.array(pn_rw)
    out[y] = {"book pnl meta y4": round(pn_meta.mean(), 4), "book pnl 1h-kline wide clock": round(pn_rw.mean(), 4), "corr": round(float(np.corrcoef(pn_meta, pn_rw)[0, 1]), 4)}
print("W2 wide positions × returns, by year:", json.dumps(out))
# check the sign of diff for long vs short legs
wL = []; wS = []
for i in range(0, len(ts), 3):
    w = WW[wpp[int(ts[i])]].astype(float); dd = np.nan_to_num(D[i]) / 1e4
    wL.append((np.clip(w, 0, None) * dd).sum() * 1e4); wS.append((np.clip(w, None, 0) * dd).sum() * 1e4)
print("book-weighted (meta − 1h) long side %.4f bps/anchor, short side %.4f" % (np.mean(wL), np.mean(wS)))
