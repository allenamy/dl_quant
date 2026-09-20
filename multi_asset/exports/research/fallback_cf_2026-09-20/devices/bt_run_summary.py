#!/usr/bin/env python3
"""bt_run_summary.py — per run (AMENDMENT 1 item 5: trigger counts and notional per run): the UNAVAILABLE-policy counters (UA-FREEZE-EXCLUDE: frozen anchors / plans dropped / fills cancelled /
UNKNOWN cells held, their notional and the excluded P&L; LEGACY-ZERO-RETURN: the same exposure REPORTED — priced through, not excluded), event
counts, audits, and the compute used (wall time from the launch receipt; core-seconds = Σ single-threaded path runtimes). Reads only the launch
receipt and the path files it lists (sha-checked). Blind protocol: arm assignment COUNTS only.
usage: python bt_run_summary.py <BT_LAUNCH_full.json> <runs_root> <out.json>
"""
import json, os, sys, hashlib, collections

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


LR = json.load(open(sys.argv[1])); ROOT = sys.argv[2]; OUT = sys.argv[3]
assert LR.get("VERDICT") == "PASS", LR.get("VERDICT")
out = {"launch_receipt_sha256": sha(sys.argv[1]), "launch_wall_s": LR["runtime_s"], "runs": {}}
core_s = 0.0
for tag, rr in LR["runs"].items():
    d = os.path.join(ROOT, tag.replace("|", "_")); o = {"seeds": len(rr["seeds"])}
    ua = collections.Counter(); ev = collections.Counter(); rt = []; unk = collections.defaultdict(list); flat_dates = collections.Counter()
    for s, v in sorted(rr["seeds"].items(), key=lambda kv: int(kv[0])):
        st = os.path.join(d, f"PATH_{tag.replace('|', '_')}_seed_{int(s):02d}")
        assert sha(st + ".npz") == v["npz_sha256"], st
        J = json.load(open(st + ".json")); Z = np.load(st + ".npz")
        ua.update({k: float(x) for k, x in J["ua_counters"].items()}); ev.update(J["events_fired_counts"]); rt.append(J["runtime_s"])
        for t_, why in J["flatten_log"]: flat_dates[t_[:10]] += 1
        unk["windows_with_held_unknown_names"].append(int((Z["unk_held"] > 0).sum()))
        unk["held_unknown_name_windows"].append(float(Z["unk_held"].sum()))
        unk["notional_at_risk_usdt_sum"].append(float(Z["unk_notional"].sum()))
        unk["notional_at_risk_over_gross_max"].append(float((Z["unk_notional"] / np.maximum(Z["gross0"], 1e-9)).max()))
        unk["unknown_price_pnl_usdt"].append(float(Z["unk_price"].sum())); unk["unknown_funding_usdt"].append(float(Z["unk_funding"].sum()))
        unk["excluded_from_main"].append(int(Z["unk_excluded"].max()))
        unk["frozen_anchors"].append(int((Z["rec_n_frozen"] > 0).sum()))
        unk["frozen_name_anchors"].append(float(np.nansum(Z["rec_n_frozen"])))
        unk["frozen_held_notional_usdt_sum"].append(float(np.nansum(Z["rec_frozen_held_notional"])))
        unk["frozen_plan_notional_dropped_usdt_sum"].append(float(np.nansum(Z["rec_frozen_plan_notional"])))
        unk["fills_cancelled_in_ua_bars"].append(float(J["ua_counters"].get("fills_cancelled_ua_bar", 0.0)))
        unk["fill_notional_cancelled_usdt"].append(float(J["ua_counters"].get("fill_notional_cancelled_ua_bar", 0.0)))
    core_s += sum(rt)
    o["path_runtime_s"] = {"sum": round(sum(rt), 1), "median": float(np.median(rt)), "max": float(max(rt))}
    o["policy"] = rr["seeds"][next(iter(rr["seeds"]))].get("ua") is not None and json.load(open(os.path.join(d, f"PATH_{tag.replace('|', '_')}_seed_00.json")))["policy"]
    o["ua_counters_sum_over_paths"] = dict(ua)
    o["unknown_cells_per_path"] = {k: {"min": float(np.min(v)), "median": float(np.median(v)), "max": float(np.max(v))} for k, v in unk.items()}
    o["events_sum_over_paths"] = dict(ev); o["day_stop_flatten_dates_paths"] = dict(sorted(flat_dates.items()))
    o["audits_all_clean"] = all(v["audits"]["max_fee_err"] == 0.0 and v["audits"]["window_identity_max_abs_err"] <= 1e-6 for v in rr["seeds"].values())
    out["runs"][tag] = o
out["core_seconds_paths"] = round(core_s, 1); out["core_hours_paths"] = round(core_s / 3600.0, 2)
json.dump(out, open(OUT, "w"), indent=1)
print("BT_RUN_SUMMARY written", OUT, "core_hours", out["core_hours_paths"], "wall_s", out["launch_wall_s"])
