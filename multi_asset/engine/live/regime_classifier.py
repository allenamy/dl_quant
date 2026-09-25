"""Regime classifier — machine-decided, persisted daily, BEFORE any markout is observable (§9-F8).

WHY: §3b's gate is a "normal regime mean". If a human decides which days count as normal, then
"that day was stress" becomes the most natural rationalisation available exactly when the numbers
disappoint. So the label is computed by machine from a causal input and written down at anchor
time -- before the markout it will later be used to filter even exists.

Thresholds (pre-registered, reusing the makerfill_deepdive gates, NOT re-tuned here):
    calm    BTC realised vol  < 7   bps/min
    normal                    7-18  bps/min
    stress                   >= 18  bps/min
Input is `PanelSource.btc_rvol_bps_min()` -- a CAUSAL trailing 24h window (std of trailing 1h
returns / sqrt(60)), so the label at anchor t uses only data <= t.

The v2 log additionally stamps `regime_at_anchor` on every anchor row, which makes "classified
before markout" auditable FROM THE LOG ITSELF rather than from this file's mtime -- a stronger
property, and the reason both exist.

Out: exports/live/regime/<YYYYMMDD>.json  (idempotent; re-running a day reproduces it exactly)
"""
from __future__ import annotations
import argparse, json, os, sys
import numpy as np
import pandas as pd

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA)
OUT = os.environ.get("PILOT_REGIME_OUT", MA + "/exports/live/regime")
# overridable so tests can point the chain at a synthetic fixture (see tests_fixture.py)
PANEL = os.environ.get("PILOT_LIVE_PANEL", MA + "/exports/live/wide_dl_live.npz")
KING = os.environ.get("PILOT_KING_PANEL", MA + "/exports/live/king_pred_live.npz")
S2 = os.environ.get("PILOT_S2_PANEL", MA + "/exports/live/s2_pred_live.npz")
CALM_MAX, STRESS_MIN = 7.0, 18.0


def label(rvol_bps_min: float | None) -> str:
    if rvol_bps_min is None or not np.isfinite(rvol_bps_min):
        return "unknown"
    if rvol_bps_min < CALM_MAX:
        return "calm"
    if rvol_bps_min >= STRESS_MIN:
        return "stress"
    return "normal"


def classify(src, anchors):
    """[{anchor_ts, anchor_utc, btc_rvol_bps_min, regime}] for the given anchor row indices."""
    rows = []
    for t in anchors:
        ti = int(t)
        rv = src.btc_rvol_bps_min(ti)
        rows.append({"anchor_ts": int(src.ts[ti]),
                     "anchor_utc": pd.to_datetime(src.ts[ti], unit="ms", utc=True).isoformat(),
                     "btc_rvol_bps_min": (round(float(rv), 4) if np.isfinite(rv) else None),
                     "regime": label(rv)})
    return rows


def run(panel=None, days_back=None, verbose=True):
    from engine.panel_source import PanelSource
    src = PanelSource(panel=panel or PANEL, king=KING, s2=S2)
    os.makedirs(OUT, exist_ok=True)
    anchors = np.sort(np.where((src.member & src.CL4).any(1))[0])
    if days_back:
        last = int(anchors[-1])
        anchors = anchors[anchors >= last - days_back * 24]
    rows = classify(src, anchors)
    by_day = {}
    for r in rows:
        by_day.setdefault(r["anchor_utc"][:10].replace("-", ""), []).append(r)
    written = []
    for day, rr in sorted(by_day.items()):
        payload = {"day": day, "thresholds_bps_min": {"calm_lt": CALM_MAX, "stress_gte": STRESS_MIN},
                   "input": "PanelSource.btc_rvol_bps_min() — causal trailing 24h window",
                   "note": ("labels are determined at anchor time and never revised; the v2 pilot "
                            "log stamps the same label on each anchor row so the ordering is "
                            "auditable from the log itself"),
                   "anchors": rr,
                   "counts": {k: sum(1 for x in rr if x["regime"] == k)
                              for k in ("calm", "normal", "stress", "unknown")}}
        json.dump(payload, open(f"{OUT}/{day}.json", "w"), indent=1)
        written.append(day)
    if verbose:
        allc = {k: sum(1 for r in rows if r["regime"] == k)
                for k in ("calm", "normal", "stress", "unknown")}
        print(f"[regime] wrote {len(written)} day files ({written[0] if written else '-'} .. "
              f"{written[-1] if written else '-'}) | anchor counts {allc}", flush=True)
    return written


def regime_for_anchor(anchor_ts_ms: int):
    """Lookup used by the logger; returns 'unknown' if the day file is absent."""
    day = pd.to_datetime(anchor_ts_ms, unit="ms", utc=True).strftime("%Y%m%d")
    p = f"{OUT}/{day}.json"
    if not os.path.exists(p):
        return "unknown"
    for r in json.load(open(p))["anchors"]:
        if int(r["anchor_ts"]) == int(anchor_ts_ms):
            return r["regime"]
    return "unknown"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=None)
    ap.add_argument("--days_back", type=int, default=None)
    a = ap.parse_args()
    run(panel=a.panel, days_back=a.days_back)
