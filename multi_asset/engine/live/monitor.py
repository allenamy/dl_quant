"""Live shadow — item 4: C4 monitoring daily report.

Rolling cross-sectional rank-IC of the emitted positions vs the realized 4h return (backfilled as
anchors mature), a decay alarm vs the historical baseline, and a daily-report json. Wraps the engine
C4 (engine/ic_monitor.py). Outputs exports/live/monitor/daily_report.json (+ ic_history.csv).
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, MA)
from engine.ic_monitor import ICMonitor, xsec_rank_ic

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
POS_DIR = MA + "/exports/live/positions"
OUT = MA + "/exports/live/monitor"
# REGIME-AWARE baseline: use the CURRENT-regime engine rank-IC, not the full-history average (0.076).
# 2026 is a weaker regime (~0.062), so a live rolling IC near 0.059 is 2026-NORMAL, not degraded —
# comparing it to the 0.076 full-history level would read a healthy signal as decaying. Keyed by year;
# update as new regimes are entered (values = engine canonical per-year rank-IC).
BASELINE_BY_YEAR = {2022: 0.062, 2023: 0.086, 2024: 0.081, 2025: 0.076, 2026: 0.062}
WINDOW = 60                # rolling anchors
DECAY_FRAC = 0.5           # alarm if rolling IC < DECAY_FRAC * baseline


def _src():
    from engine.panel_source import PanelSource
    return PanelSource(panel=MA + "/exports/live/wide_dl_live.npz",
                       king=MA + "/exports/live/king_pred_live.npz",
                       s2=MA + "/exports/live/s2_pred_live.npz")


def run(verbose=True):
    os.makedirs(OUT, exist_ok=True)
    src = _src()
    tj = {int(t): i for i, t in enumerate(src.ts)}
    sym2j = {s: j for j, s in enumerate(src.symbols)}
    # regime-aware baseline: the year of the most recent scored anchor
    files_all = sorted(glob.glob(POS_DIR + "/positions_*.json"))
    cur_year = pd.Timestamp.utcnow().year
    if files_all:
        cur_year = pd.to_datetime(json.load(open(files_all[-1]))["anchor_ts_ms"], unit="ms", utc=True).year
    baseline_ic = BASELINE_BY_YEAR.get(int(cur_year), 0.062)
    mon = ICMonitor(window=WINDOW, baseline_ic=baseline_ic, decay_frac=DECAY_FRAC)
    hist = []
    for f in sorted(glob.glob(POS_DIR + "/positions_*.json")):
        rec = json.load(open(f))
        ti = tj.get(int(rec["anchor_ts_ms"]))
        if ti is None:
            continue
        ret = src.Y4[ti]
        if not np.isfinite(ret).any():        # label not matured yet -> backfill on a later run
            continue
        w = np.zeros(src.N)
        for s, wt in rec["curve"]["A_provisional_3leg"]["positions"].items():
            if s in sym2j:
                w[sym2j[s]] = wt
        r = mon.update(rec["anchor_ts_ms"], w, ret)
        hist.append({"anchor_utc": rec["anchor_utc"], "ic": r["ic"], "rolling_ic": r["rolling_ic"],
                     "n": r["n"], "alert": r["alert"]})
    scored = [h for h in hist if h["ic"] is not None and np.isfinite(h["ic"])]
    report = {
        "as_of": pd.Timestamp.utcnow().isoformat(),
        "n_anchors_scored": len(scored),
        "rolling_rank_ic": round(mon.rolling_ic(), 4) if scored else None,
        "baseline_ic": baseline_ic, "baseline_regime_year": int(cur_year),
        "decay_alarm_threshold": round(DECAY_FRAC * baseline_ic, 4),
        "decay_alarm": bool(mon.alerts), "n_alerts": len(mon.alerts),
        "latest_alert": mon.alerts[-1] if mon.alerts else None,
        "note": "rolling rank-IC of live positions vs realized 4h return; backfilled as labels mature. "
                "structural-caliber signal-health monitor (not a P&L). Baseline is REGIME-AWARE (current-"
                "year engine level), so a reading near the current regime's IC is healthy, not decayed.",
    }
    json.dump(report, open(OUT + "/daily_report.json", "w"), indent=1)
    if hist:
        pd.DataFrame(hist).to_csv(OUT + "/ic_history.csv", index=False)
    if verbose:
        print(f"[monitor] scored {report['n_anchors_scored']} anchors | rolling rank-IC "
              f"{report['rolling_rank_ic']} (regime-{cur_year} baseline {baseline_ic}) | decay_alarm {report['decay_alarm']}", flush=True)
        print(f"[monitor] -> {OUT}/daily_report.json + ic_history.csv", flush=True)
    return report


if __name__ == "__main__":
    run()
