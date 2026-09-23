#!/usr/bin/env python3
"""fresh_ext.py (= news_ext.py with the controls replaced by the NEW_S same-seed X arms) — DESCRIBE-ONLY extension segment
2026-08-31T04Z → 2026-09-18T20Z (PREREG_fresh_models_newS_2026-09-23.md §2: "2026-08-31 → 09-18 延伸段只描述"; no criterion).
FRESH = FRESH_s{42,2027}X_scaled_rule_raw_UAFE; control = NEWS_s{42,2027}X_scaled_rule_raw_UAFE (same seed).
Same per-path metric definitions as news_stats.py / ovn_stats.py, path mean + 2.5/97.5 percentiles, and the point estimate of
d̄ (no bootstrap: 18 full days). Control: on the shared anchors up to 2026-08-30T20Z each X path is compared with the same
seed's main-run path; max |Δr| is reported, not gated.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B fresh_ext.py PATH,HOME,LC_CTYPE <fresh_runs> <news_runs> <out.json>
"""
import os, sys, json, time, hashlib, calendar

import numpy as np

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_tables as BT
import bt_driver_lib as DL

RUNS_F, RUNS_N, OUT = sys.argv[2:5]; DAY = 86400; NPATH = 32


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(iso): return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def load(d, tag_dir):
    P = []
    for k in range(NPATH):
        s = os.path.join(d, f"PATH_{tag_dir}_seed_{k:02d}"); J = json.load(open(s + ".json"))
        if J["npz_sha256"] != sha(s + ".npz"): raise ValueError(f"{tag_dir} seed {k}: sha")
        if not DL.audits_clean(J["audits"]): raise ValueError(f"{tag_dir} seed {k}: audits")
        P.append(BT.series_from_path(np.load(s + ".npz")))
    return P


a0, a1 = ts("2026-08-31T04:00:00Z"), ts("2026-09-18T20:00:00Z")
rec = {"device": "fresh_ext.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()), "segment": ["2026-08-31T04:00:00Z", "2026-09-18T20:00:00Z"],
       "status": "DESCRIBE ONLY (PREREG §2); overlaps the live period", "arms": {}, "control_vs_main_run": {}}
S = {}
for s in ("42", "2027"):
    S[f"NEWS_s{s}"] = load(os.path.join(RUNS_N, f"NEWS_s{s}X_scaled_rule_raw_UAFE"), f"NEWS_s{s}X_scaled_rule_raw_UAFE")
    S[f"FRESH_s{s}"] = load(os.path.join(RUNS_F, f"FRESH_s{s}X_scaled_rule_raw_UAFE"), f"FRESH_s{s}X_scaled_rule_raw_UAFE")
A = S["NEWS_s42"][0]["A"]
for k, P in S.items(): assert all(np.array_equal(p["A"], A) for p in P), k
m = (A >= a0) & (A <= a1); d = (A[m] // DAY) * DAY; ud, c = np.unique(d, return_counts=True); days = ud[c == 6]
assert m.any() and len(days) > 0


def daily_on(p):
    u, rd = BT.daily(p["A"][m], p["r"][m]); pos = np.searchsorted(u, days); assert np.all(u[pos] == days); return rd[pos]


for arm, P in S.items():
    per = []
    for p in P:
        rd = daily_on(p); r = p["r"][m]
        per.append({"total_return": float(np.prod(1 + r) - 1), "sharpe": BT.sharpe(rd), "worst_day": float(rd.min()), "maxdd_5m": BT.maxdd_5m(p, m),
                    "g": float(p["g"][m].mean()), "price": float(p["pnl"][m].mean()), "funding_paid": float(p["car"][m].mean()), "fee": float(p["cst"][m].mean()),
                    "turnover_over_gross": float(p["tau"][m].mean()), "day_stop_flattens": float(p["dstop"][m].sum()), "per_name_stops": float(p["nstop"][m].sum())})
    rec["arms"][arm] = {"n_paths": len(per), "n_windows": int(m.sum()), "n_full_days": int(len(days))}
    for k in per[0]:
        v = [x[k] for x in per]
        if any(x is None for x in v): rec["arms"][arm][k] = "UNAVAILABLE"; continue
        v = np.array(v); rec["arms"][arm][k] = {"path_mean": float(v.mean()), "p2.5": float(np.percentile(v, 2.5)), "p97.5": float(np.percentile(v, 97.5))}
for s in ("42", "2027"):
    D = np.stack([daily_on(a) - daily_on(b) for a, b in zip(S[f"FRESH_s{s}"], S[f"NEWS_s{s}"])]).mean(0)
    rec["arms"][f"FRESH_s{s}"]["dbar_vs_NEWS_same_seed_bps_per_day_point"] = float(1e4 * D.mean()); rec["arms"][f"FRESH_s{s}"]["dbar_n_days"] = int(len(D))
    mr = os.path.join(RUNS_F, f"FRESH_s{s}_scaled_rule_raw_UAFE")
    if os.path.isdir(mr):
        M = load(mr, f"FRESH_s{s}_scaled_rule_raw_UAFE"); AM = M[0]["A"]; shared = AM[AM <= ts("2026-08-30T20:00:00Z")]
        ix = np.searchsorted(A, shared); jx = np.searchsorted(AM, shared)
        dm = max(float(np.max(np.abs(x["r"][ix] - y["r"][jx]))) for x, y in zip(S[f"FRESH_s{s}"], M))
        rec["control_vs_main_run"][f"FRESH_s{s}"] = {"shared_anchors": int(len(shared)), "max_abs_diff_window_return": dm, "bitwise_equal": dm == 0.0}
json.dump(rec, open(OUT, "w"), indent=1, default=float)
print("FRESH_EXT written", OUT, sha(OUT), {k: rec["arms"][k].get("dbar_vs_NEWS_same_seed_bps_per_day_point") for k in rec["arms"]}, rec["control_vs_main_run"], flush=True)
