"""Minimal replay test for engine C2 (vol-gate) + C3 (isotonic calibration), 2026-05 fit / 2026-06 test.

v1: C2 asserts the execution-tactic ramp (exposure pinned 1.0; crisis beneficiary)."""
import sys, numpy as np
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
from engine.panel_source import PanelSource
from engine.isotonic_calib import IsotonicCalibrator, ic_invariance_check
from engine.vol_gate import VolGate

src = PanelSource()


def pairs(ym):
    S, Y = [], []
    for t in src.month_anchors(ym):
        legs, m = src.legs_raw(t)
        S.append(legs["king"]); Y.append(src.realized_fwd_bps(t))
    return np.concatenate(S), np.concatenate(Y)


# ---- C3 isotonic ----
s_fit, y_fit = pairs("2026-05"); s_te, y_te = pairs("2026-06")
cal = IsotonicCalibrator().fit(s_fit, y_fit)
inv = ic_invariance_check(s_te, y_te, cal)
xs = np.linspace(np.nanpercentile(s_te, 1), np.nanpercentile(s_te, 99), 50); ys = cal.transform(xs)
print("[C3] fit_pairs=%d test_pairs=%d | IC_raw=%.4f IC_cal=%.4f INVARIANT=%s | monotone=%s | cal_bps=[%.2f,%.2f]" % (
    len(s_fit), len(s_te), inv["ic_raw"], inv["ic_calibrated"], inv["invariant"],
    bool(np.all(np.diff(ys) >= -1e-9)), float(np.nanmin(ys)), float(np.nanmax(ys))))
assert inv["invariant"], "C3 FAIL: IC not invariant under isotonic"
print("[C3] PASS")

# ---- C2 vol-gate (execution-tactic ramp; exposure pinned) ----
anchors = src.month_anchors("2026-06")
rv = np.array([src.btc_rvol_bps_min(int(t)) for t in anchors]); rv = rv[np.isfinite(rv)]
print("[C2] BTC rvol bps/min 2026-06: min/med/max = %.2f/%.2f/%.2f" % (rv.min(), np.median(rv), rv.max()))
# (a) production default 18 bps/min -> calm month, expect ~no stress triggers, exposure pinned
vg = VolGate(src, thresh_bps_min=18.0)
tacs = [vg.execution_tactic(int(t)) for t in anchors]
exp_pinned = all(t["exposure_mult"] == 1.0 for t in tacs)
print("[C2a] thresh=18: stress_triggers=%d exposure_mult all==1.0 = %s" % (len(vg.gate_log()), exp_pinned))
assert exp_pinned, "C2 FAIL: exposure modulated (must be pinned -- crisis beneficiary)"
# (b) threshold at median rvol -> exercise the ramp (wider quotes / smaller slices), exposure STILL pinned
vg2 = VolGate(src, thresh_bps_min=float(np.median(rv)))
t2 = [vg2.execution_tactic(int(t)) for t in anchors]
qw = np.array([x["quote_width_mult"] for x in t2]); sl = np.array([x["slice_frac"] for x in t2])
exp2 = all(x["exposure_mult"] == 1.0 for x in t2)
print("[C2b] thresh=median: quote_width[max]=%.2f slice_frac[min]=%.2f stress=%d exposure_pinned=%s ramp=%s" % (
    qw.max(), sl.min(), len(vg2.gate_log()), exp2, bool(qw.max() > 1.0 and sl.min() < 1.0)))
assert exp2 and qw.max() > 1.0 and sl.min() >= vg2.min_slice - 1e-9 and sl.min() < 1.0, "C2 FAIL: ramp/pin broken"
print("[C2] PASS (tactic ramp works, exposure pinned)")
