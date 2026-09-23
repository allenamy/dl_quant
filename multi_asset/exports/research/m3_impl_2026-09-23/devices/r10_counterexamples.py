#!/usr/bin/env python3
"""r10_counterexamples — the round-10 review's two M3 counterexamples (R10-A01 leverage, R10-A02 frozen-BTC net), run on ONE
version of live/beta_overlay.py (a pure module: no file, network or clock; loaded by path, nothing else of the executor runs).
usage: /usr/bin/python3 r10_counterexamples.py <path/to/beta_overlay.py> <label>
Prints one JSON line and a verdict line. Exit 0 = the version DEFENDS against both (post-fix expectation); exit 1 = at least one
counterexample goes through (the pre-fix expectation). The inputs are the reviewer's, verbatim
(REVIEW_round10_core_release_2026-09-23.md §3; its m3/repro_runtime.py)."""
import hashlib, importlib.util, inspect, json, sys
path, label = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location(f"bo_{label}", path)
BO = importlib.util.module_from_spec(spec); spec.loader.exec_module(BO)
has_budget = "max_combined_leverage" in inspect.signature(BO.stage).parameters
G, NAV = 10000.0, 5000.0
target = {f"L{i}USDT": 100.0 for i in range(50)}
target.update({f"S{i}USDT": -100.0 for i in range(50)})
betas = {s: (-1.0 if s.startswith("L") else 4.0) for s in target}
betas["BTCUSDT"] = 1.0
field = dict(version="m3_beta_v1", anchor_ts=14400, data_cutoff_ts=14400, n_win=180, n_min=120, clip=[-1.0, 4.0], fallback=1.0,
             btc="BTCUSDT", betas=betas, n_obs={s: 180 for s in betas})
out = {"label": label, "beta_overlay_sha256": hashlib.sha256(open(path, "rb").read()).hexdigest(), "stage_has_budget": has_budget}
# A01: leverage. Post-fix the leg needs an explicit budget; the fixture uses 3.0 x NAV (the alert line) and also "unset".
runs = {"no_budget_arg": {}} if not has_budget else {"budget_3.0": {"max_combined_leverage": 3.0, "nav": NAV},
                                                     "budget_unset": {"max_combined_leverage": None, "nav": NAV}}
out["A01"] = {}
a01_defended = has_budget
for k, kw in runs.items():
    t = dict(target)
    r = BO.stage("on", t, {}, {"anchor_ts": 14400, "beta_overlay": field}, G, [], btc_floor=100.0, dust_mult=2.0,
                 btc_dust_only=True, **kw)
    lev = sum(abs(v) for v in t.values()) / NAV
    out["A01"][k] = {"status": r["record"].get("status"), "reason": r["record"].get("reason"),
                     "btc_target": t.get("BTCUSDT"), "combined_leverage": lev, "watchdog_old_reads": G / NAV,
                     "above_halt_5x": lev > 5.0}
    if lev > 5.0:
        a01_defended = False
# A02: frozen BTC (field missing): base BTC +500 / ETH -500, held BTC 1,500 ⇒ the ex-overlay net must be 0
frozen = {"BTCUSDT": 500.0, "ETHUSDT": -500.0}
kw = {"max_combined_leverage": 3.0, "nav": NAV} if has_budget else {}
ref = BO.stage("on", frozen, {"BTCUSDT": 1500.0}, {"anchor_ts": 14400}, 10000.0, [], **kw)
row = dict(venue_net_usdt=sum(frozen.values()), venue_gross_usdt=sum(abs(x) for x in frozen.values()), net_over_gross=0.5,
           net_over_equity=0.2)
view = BO.neutrality_view(dict(row), ref["record"])
out["A02"] = {"status": ref["record"].get("status"), "overlay_net_usdt": ref["overlay_net_usdt"],
              "venue_net_usdt": row["venue_net_usdt"], "ex_overlay_net_usdt": view["venue_net_usdt"], "correct": 0.0}
a02_defended = view["venue_net_usdt"] == 0.0
print(json.dumps(out, sort_keys=True))
print(f"R10_COUNTEREXAMPLES label={label} A01={'DEFENDED' if a01_defended else 'GOES_THROUGH'} "
      f"A02={'DEFENDED' if a02_defended else 'GOES_THROUGH'}")
sys.exit(0 if (a01_defended and a02_defended) else 1)
