"""Pre-flight for fresh_stats' control-side loading: for every NEW_S cell fresh_stats will load, check that the
32 path files exist and carry the fields the device reads. Field presence and the window axis only — no returns."""
import os, json, sys
sys.path.insert(0, "/dev/shm/fresh_2026-09-23/engine")
import numpy as np
import bt_driver_lib as DL
N = "/dev/shm/news_2026-09-23/runs"
CELLS = {"base": "scaled_rule_raw_UAFE", "fee_x1.25": "scaled_rule_raw_UAFE_fee_x1.25", "slip_x1.5": "scaled_rule_raw_UAFE_slip_x1.5",
         "fill_x0.9": "scaled_rule_raw_UAFE_fill_x0.9", "lit": "lit_rule_raw_UAFE"}
NEED = ("npz_sha256", "audits", "seed", "device_sha256", "calibration_sha256", "price_pin", "config_sha256",
        "status_counts", "events_fired_counts", "target_stats")
pins = {}
for arm in ("NEWS_s42", "NEWS_s2027"):
    for cell, suf in CELLS.items():
        d = os.path.join(N, f"{arm}_{suf}"); tag = f"{arm}_{suf}"
        stems = [os.path.join(d, f"PATH_{tag}_seed_{k:02d}") for k in range(32)]
        miss = [s for s in stems if not (os.path.exists(s + ".npz") and os.path.exists(s + ".json"))]
        J0 = json.load(open(stems[0] + ".json"))
        missing_fields = [f for f in NEED if f not in J0]
        clean = all(DL.audits_clean(json.load(open(s + ".json"))["audits"]) for s in stems)
        seeds_ok = all(int(json.load(open(s + ".json"))["seed"]) == k for k, s in enumerate(stems))
        pins[(arm, cell)] = {w: json.dumps(J0[w], sort_keys=True) for w in ("device_sha256", "calibration_sha256", "price_pin", "config_sha256")}
        print(f"{tag:46s} missing_files={len(miss)} missing_fields={missing_fields} audits_clean={clean} seeds_0_31={seeds_ok}")
for w in ("device_sha256", "calibration_sha256", "price_pin"):
    vals = {v[w] for v in pins.values()}
    print(f"{w:22s}: {len(vals)} distinct across the 10 control cells -> {'IDENTICAL' if len(vals)==1 else 'DIFFER'}")
for arm in ("NEWS_s42", "NEWS_s2027"):
    cfgs = {pins[(arm, c)]["config_sha256"] for c in CELLS}
    print(f"{arm}: config_sha256 distinct across its 5 cells = {len(cfgs)}")
