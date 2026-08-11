import sys, json
LIVE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/engine/live"
ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/live/pilot_log"
sys.path.insert(0, LIVE)
import pilot_log as PL
data = PL.read_range(ROOT, PL.available_days(ROOT))

sys.path.insert(0, "/tmp/frozen_pm")
import pilot_metrics as NEW          # frozen 9a033684

o, a, rb = data["orders"], data["anchors"], data["position_readback"]

raw = NEW.m5_weight_fidelity(o, a, rb)

# same rows, sign convention converted to the venue-real one the frozen impl documents
conv = []
for r in o:
    r2 = dict(r)
    f = r2.get("filled_notional")
    if f is not None:
        r2["filled_notional"] = (1 if r2.get("side") == "buy" else -1) * abs(float(f))
    conv.append(r2)
fixed = NEW.m5_weight_fidelity(conv, a, rb)

sys.modules.pop("pilot_metrics")
sys.path.remove("/tmp/frozen_pm")
import importlib
OLD = importlib.import_module("pilot_metrics")   # server cfd1de1b
old = OLD.m5_weight_fidelity(o, a, rb)

k = "venue_vs_inferred_drift_usd_max"
print("M5 %s:" % k)
print("  OLD impl (cfd1de1b) on the shadow's UNSIGNED rows          : %14.2f" % old[k])
print("  FROZEN impl (9a033684) on the same UNSIGNED rows (drop-in) : %14.2f   <-- vendoring as-is" % raw[k])
print("  FROZEN impl after converting the rows to SIGNED            : %14.2f" % fixed[k])
print()
print("agreement OLD vs FROZEN-on-converted-rows: %s" % ("YES" if abs(old[k]-fixed[k]) < 1e-6 else
      "NO  (delta %.6f)" % (fixed[k]-old[k])))
for kk in ("mean_abs_weight_error", "max_abs_weight_error", "n_comparisons"):
    print("  %-28s old=%-14s frozen_dropin=%-14s frozen_converted=%s" % (kk, old.get(kk), raw.get(kk), fixed.get(kk)))
