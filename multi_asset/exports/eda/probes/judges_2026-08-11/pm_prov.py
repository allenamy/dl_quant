"""Each number is printed WITH the file that produced it. No label is trusted."""
import sys, subprocess, json, os
LIVE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/engine/live"
ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/live/pilot_log"
FROZ = "/tmp/frozen_pm"

CHILD = r'''
import sys, json
LIVE = %r; ROOT = %r; FROZ = %r; WHICH = %r; CONV = %r
sys.path.insert(0, LIVE)
if WHICH == "frozen":
    sys.path.insert(0, FROZ)
import pilot_log as PL, pilot_metrics as PM
data = PL.read_range(ROOT, PL.available_days(ROOT))
o = data["orders"]
if CONV:
    c = []
    for r in o:
        r2 = dict(r); f = r2.get("filled_notional")
        if f is not None:
            r2["filled_notional"] = (1 if r2.get("side") == "buy" else -1) * abs(float(f))
        c.append(r2)
    o = c
m5 = PM.m5_weight_fidelity(o, data["anchors"], data["position_readback"])
full = PM.compute(ROOT, verbose=False)
print(json.dumps({
    "module_file": PM.__file__,
    "self_hash": PM.self_hash()[:16],
    "m5_direct_drift": m5["venue_vs_inferred_drift_usd_max"],
    "m5_via_compute_drift": full["M5_weight_fidelity"]["venue_vs_inferred_drift_usd_max"],
    "m1_c_bps": full["M1_effective_cost"]["c_bps_overall"],
    "m1_n_filled": full["M1_effective_cost"]["n_filled_orders"],
}))
'''

for which in ("server", "frozen"):
    for conv in (False, True):
        src = CHILD % (LIVE, ROOT, FROZ, which, conv)
        out = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True)
        if out.returncode:
            print(which, conv, "FAILED", out.stderr[-300:]); continue
        d = json.loads(out.stdout)
        tag = "%s rows=%s" % (which, "SIGNED(converted)" if conv else "as-written")
        print("%-28s file=%-52s sha=%s" % (tag, d["module_file"].replace("/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/engine/live", "<server>"), d["self_hash"]))
        print("%-28s m5 drift: direct=%14.2f  via compute=%14.2f | M1 c=%s bps n=%s"
              % ("", d["m5_direct_drift"], d["m5_via_compute_drift"], d["m1_c_bps"], d["m1_n_filled"]))
