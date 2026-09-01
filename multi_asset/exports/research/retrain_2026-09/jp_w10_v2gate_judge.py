"""门V2 判官 @jpline(PREREG addendum §A, 判据冻结先于数字):
ΔNet(new − old, 2023+)逐锚, 双种子各报 95%CI; 判据 = 两种子 CI 下界均 ≥ −0.10 bps/锚;
好于 +0.30 ⇒ SUSPECT(好得反常先查仪器)。主读 = 装置 net_ex(执行器口径, 设备头注主读), 文件口径并报。
用法: python3 jp_w10_v2gate_judge.py
"""
import json
import numpy as np

PD = "/mnt/storage/private/work_hsy/probe_artifacts"
Z = {run: np.load(f"{PD}/w10_v2gate_{run}.npz", allow_pickle=True) for run in
     ("s42_OLD9", "s42_NEW9", "s2027_OLD9", "s2027_NEW9")}
k0 = sorted(Z["s42_OLD9"].files)
print("series keys:", k0[:24], flush=True)

COLS = None
def series(z):
    global COLS
    COLS = [str(c) for c in z["cols"]]
    rec = z["d30_n2_c42_rec"]
    return rec[:, COLS.index("net_ex")].astype(np.float64), "d30.net_ex", rec[:, COLS.index("ts")].astype(np.int64), rec[:, COLS.index("net")].astype(np.float64)

import time
_, _, ts, _ = series(Z["s42_OLD9"])
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts])
sel = yrs >= 2023
verdicts = {}
for S in ("s42", "s2027"):
    old_ex, kn, ts_o, old_f = series(Z[f"{S}_OLD9"])
    new_ex, _, ts_n, new_f = series(Z[f"{S}_NEW9"])
    assert np.array_equal(ts_o, ts_n)
    for cal, o, n_ in (("net_ex", old_ex, new_ex), ("net_file", old_f, new_f)):
        d = (n_ - o)[sel]
        m = d.mean(); se = d.std(ddof=1) / np.sqrt(len(d))
        lo, hi = m - 1.96 * se, m + 1.96 * se
        if cal == "net_ex": verdicts[S] = (m, lo, hi)
        print(f"[{S}][{cal}] n {len(d)} ΔNet {m:+.4f} bps/锚 95%CI [{lo:+.4f}, {hi:+.4f}]", flush=True)
ok = all(lo >= -0.10 for _, lo, _ in verdicts.values())
suspect = any(m > 0.30 for m, _, _ in verdicts.values())
print("V2_GATE", "SUSPECT_TOO_GOOD" if suspect else ("PASS" if ok else "FAIL"),
      {k: round(v[1], 4) for k, v in verdicts.items()}, flush=True)
