"""Minimal replay test for engine C1 (signal chain) + C4 (IC monitor / retrain trigger), 2026-06.

v1: exercises the CURRENT API (target_position / shape_position; C3 on the P&L path)."""
import sys, numpy as np
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
from engine.panel_source import PanelSource
from engine.isotonic_calib import IsotonicCalibrator
from engine.vol_gate import VolGate
from engine.signal_chain import SignalChain
from engine.ic_monitor import ICMonitor, RetrainTrigger, xsec_rank_ic

src = PanelSource()

# ---- C1 signal chain: fit C3 on 2026-05, replay 2026-06 via target_position ----
chain = SignalChain(src, vol_gate=VolGate(src))
chain.fit_calibrator("2026-05", IsotonicCalibrator())
rp = [chain.target_position(int(t)) for t in src.month_anchors("2026-06")]
neutral = np.mean([abs(r["position"].sum()) for r in rp])
ics = np.array([ic for ic in (xsec_rank_ic(r["position"], src.realized_fwd_bps(r["t"])) for r in rp)
                if np.isfinite(ic)])
print("[C1] anchors=%d dollar-neutral(mean|sum pos|)=%.2e | book pos-rankIC=%.4f (IR %.2f) | pos range[%.3f,%.3f]" % (
    len(rp), neutral, ics.mean(), ics.mean() / (ics.std() + 1e-9) * np.sqrt(len(ics)),
    float(np.min([r["position"].min() for r in rp])), float(np.max([r["position"].max() for r in rp]))))
assert neutral < 1e-9, "C1 FAIL: not dollar-neutral"
assert all(r["exec_tactic"]["exposure_mult"] == 1.0 for r in rp), "C1 FAIL: exposure modulated"
print("[C1] PASS (dollar-neutral + exposure pinned 1.0)")

# ---- C4 IC monitor + retrain trigger stub ----
baseline = float(ics.mean())
mon = ICMonitor(window=30, baseline_ic=baseline, decay_frac=0.5)
trig = RetrainTrigger(margin=0.0, persist=10)
rng = np.random.default_rng(0); switched = 0
for r in rp:
    real = src.realized_fwd_bps(r["t"])
    mon.update(r["t"], r["position"], real)
    chall = r["position"] + rng.normal(0, 3, size=r["position"].shape)   # noisier challenger -> worse
    ci = xsec_rank_ic(r["position"], real); li = xsec_rank_ic(chall, real)
    if trig.step(r["t"], ci, li):
        switched += 1
print("[C4] rolling_ic(final)=%.4f baseline=%.4f decay_alerts=%d | noisy-challenger switches=%d (expect ~0)" % (
    mon.rolling_ic(), baseline, len(mon.alerts), switched))
trig2 = RetrainTrigger(margin=-0.01, persist=5); fired = 0
for r in rp[:15]:
    real = src.realized_fwd_bps(r["t"]); ic = xsec_rank_ic(r["position"], real)
    if trig2.step(r["t"], ic, ic):
        fired += 1
print("[C4] switch-stub fires on winning challenger:", fired > 0)
assert np.isfinite(mon.rolling_ic()) and fired > 0, "C4 FAIL"
print("[C4] PASS")
