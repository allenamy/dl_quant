import glob, json, sys
import numpy as np
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
from engine.panel_source import PanelSource
from engine.ic_monitor import ICMonitor

WINDOW, DECAY_FRAC, BASE = 60, 0.5, 0.062
src = PanelSource(panel=MA + "/exports/live/wide_dl_live.npz",
                  king=MA + "/exports/live/king_pred_live.npz",
                  s2=MA + "/exports/live/s2_pred_live.npz")
tj = {int(t): i for i, t in enumerate(src.ts)}
sym2j = {s: j for j, s in enumerate(src.symbols)}

def series(files, getpos, label):
    mon = ICMonitor(window=WINDOW, baseline_ic=BASE, decay_frac=DECAY_FRAC)
    ics, rolls = [], []
    for f in sorted(files):
        rec = json.load(open(f))
        ti = tj.get(int(rec["anchor_ts_ms"]))
        if ti is None:
            continue
        ret = src.Y4[ti]
        if not np.isfinite(ret).any():
            continue
        w = np.zeros(src.N)
        for s, wt in getpos(rec).items():
            if s in sym2j:
                w[sym2j[s]] = wt
        r = mon.update(rec["anchor_ts_ms"], w, ret)
        if r["ic"] is not None and np.isfinite(r["ic"]):
            ics.append(r["ic"]); rolls.append(r["rolling_ic"])
    return dict(label=label, ic=ics, roll=rolls, alerts=len(mon.alerts), now=mon.rolling_ic())

CH = glob.glob(MA + "/exports/live/positions/positions_*.json")
FX = glob.glob(MA + "/exports/live/fixfunding/positions/positions_*.json")
S = [series(CH, lambda r: r["curve"]["A_provisional_3leg"]["positions"], "champion A_3leg  <- 部署告警读的就是这条"),
     series(CH, lambda r: r["curve"]["B_backfilled_4leg"]["positions"],  "champion B_4leg   as-trained, 四腿"),
     series(FX, lambda r: r["positions"],                                "fixfunding 4leg   normfix 修正, 四腿")]

thr = DECAY_FRAC * BASE
print("阈值 = %.1f x %.3f = %.4f   window=%d" % (DECAY_FRAC, BASE, thr, WINDOW))
print()
for s in S:
    ic = np.array(s["ic"]); roll = np.array(s["roll"]); n = len(ic)
    se = ic.std(ddof=1) / np.sqrt(n); h = n // 2
    x = ic - ic.mean()
    rho = [float((x[:-k] * x[k:]).sum() / (x * x).sum()) for k in range(1, 13)]
    infl = 1 + 2 * sum(max(r, 0.0) for r in rho)
    full = roll[WINDOW - 1:] if n >= WINDOW else roll
    print(s["label"])
    print("   n=%d  全窗 IC %+.4f (t=%.2f)   前半 %+.4f -> 后半 %+.4f" % (n, ic.mean(), ic.mean()/se, ic[:h].mean(), ic[h:].mean()))
    print("   rolling 现值 %.4f   越阈值: %s   告警次数 %d" % (s["now"], "是 ***" if s["now"] < thr else "否", s["alerts"]))
    print("   满窗 rolling 峰 %.4f  谷 %.4f   末5 %s" % (full.max(), full.min(), np.round(roll[-5:], 4).tolist()))
    print("   IC 自相关 lag1..6 %s" % np.round(rho[:6], 3).tolist())
    print("   膨胀因子 %.2f  =>  n_eff %.0f   t_eff %.2f" % (infl, n/infl, ic.mean()/se/np.sqrt(infl)))
    print()
a = np.array(S[1]["ic"]); b = np.array(S[2]["ic"]); m = min(len(a), len(b))
d = b[:m] - a[:m]; sd = d.std(ddof=1)/np.sqrt(m)
print("配对(修正 - as-trained, 同为四腿, n=%d): dIC %+.5f   t %+.2f" % (m, d.mean(), d.mean()/sd))
