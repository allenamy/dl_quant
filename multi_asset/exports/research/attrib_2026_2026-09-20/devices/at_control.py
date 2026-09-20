#!/usr/bin/env python3
"""at_control.py — THE CONTROL REPRODUCTION, run before any new number of this stream.

It rebuilds the certified run's per-period table from the 32 raw fill-path files with an INDEPENDENT
implementation of every statistic (at_lib.daily_returns / cagr_of / sharpe_of / maxdd_of / worst30_of /
cvar5_of — written from the prereg's wording, not imported from bt_tables.py), and compares it, cell by cell,
with the PUBLISHED table `receipts/BT_MAIN_A0.json` fa3c2ce7 → `docs/RESULT_baseline_tables_A0_objB_2026-09-19.md`.

It reports max |Δ| per metric over every published period. A control that cannot reproduce the published
table is a control that has found something; the receipt reports the worst cell by name either way.

It also emits, for the downstream devices, the L1 (realised) per-anchor series of the mean path.

usage: python at_control.py <ENV_WHITELIST_CSV> <OUT_DIR>
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import at_lib as L

T0 = time.time()
ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{L.ROOT}/receipts"
os.makedirs(OUT, exist_ok=True)
chk = L.Checks(T0)
rec = L.rec_head("at_control.py", sys.argv)
chk("env.whitelist", not sorted(set(rec["env"]) - ENV_OK), {"extra": sorted(set(rec["env"]) - ENV_OK)})
CFGP = f"{L.ROOT}/RUN_CONFIG_attrib_2026-09-20.json"
chk("frozen_config.exists", os.path.exists(CFGP))
rec["frozen_config"] = {"path": CFGP, "sha256": L.sha(CFGP) if os.path.exists(CFGP) else None}
rec["inputs"] = L.verify_pins(chk, ["AGG_A0", "BT_MAIN_A0", "BT_RUN_CONFIG"])
if chk.fails:
    L.write_receipt(rec, chk, f"{OUT}/AT_CONTROL.json")
    print("AT_CONTROL VERDICT=REFUSED failed=%s" % chk.fails, flush=True)
    sys.exit(3)

GM = L.GM
paths = sorted(f for f in os.listdir(L.RUN_A0) if f.startswith("PATH_") and f.endswith(".npz"))
chk("paths.32", len(paths) == 32, {"n": len(paths)})

SER = []
t5 = None
for f in paths:
    Z = np.load(f"{L.RUN_A0}/{f}", allow_pickle=True)
    den = GM * Z["nav0"]
    s = {"A": Z["A"].astype(np.int64),
         "r": Z["navm1"] / Z["navm0"] - 1.0,
         "price": 1e4 * Z["price_trade"] / den,
         "funding_paid": -1e4 * Z["funding"] / den,
         "fee": 1e4 * Z["fee"] / den,
         "unk": 1e4 * Z["unk_excluded"] * (Z["unk_price"] + Z["unk_funding"]) / den,
         "turnover": Z["turnover"] / den,
         "dstop": Z["n_flatten_events"].astype(float),
         "nstop": Z["n_stop_events"].astype(float),
         "halt": (Z["status"] == 1).astype(float),
         "hold": (Z["status"] == 2).astype(float),
         "dust": Z["end_dust_usdt"] / den,
         "unk_notional": Z["unk_notional"] / den}
    s["g"] = 1e4 * s["r"] / GM
    nav5 = np.asarray(Z["nav5_main"], float)
    s["r5"] = nav5[1:] / nav5[:-1] - 1.0
    tt = int(Z["nav5_t0"]) + 300 * np.arange(len(nav5), dtype=np.int64)
    if t5 is None:
        t5 = tt
    else:
        assert np.array_equal(t5, tt)
    SER.append(s)

A = SER[0]["A"]
for s in SER:
    assert np.array_equal(s["A"], A)
MEAN = {"A": A}
for k in ("r", "price", "funding_paid", "fee", "unk", "turnover", "dstop", "nstop", "halt", "hold", "dust", "unk_notional", "g", "r5"):
    MEAN[k] = np.stack([s[k] for s in SER]).mean(0)
chk("g.identity", float(np.abs(MEAN["g"] - (MEAN["price"] - MEAN["funding_paid"] - MEAN["fee"] - MEAN["unk"])).max()) < 1e-9,
    {"max_abs_bps": float(np.abs(MEAN["g"] - (MEAN["price"] - MEAN["funding_paid"] - MEAN["fee"] - MEAN["unk"])).max())})


def metrics(s, m, t5=None, r5=None):
    A_ = s["A"][m]
    r = s["r"][m]
    ud, rd = L.daily_returns(A_, r)
    out = {"n_anchors": int(m.sum()), "n_days": int(len(ud)),
           "first_anchor": int(A_[0]), "last_anchor": int(A_[-1]),
           "nav_return": float(np.prod(1.0 + r) - 1.0),
           "cagr": L.cagr_of(rd), "sharpe_daily": L.sharpe_of(rd),
           "maxdd_4h": L.maxdd_from_returns(r),
           "worst_30d": L.worst30_of(rd), "cvar5_daily": L.cvar5_of(rd)}
    if t5 is not None:
        k = (t5[1:] > A_[0]) & (t5[1:] <= A_[-1] + L.H4)
        out["maxdd_5m"] = L.maxdd_from_returns(r5[k]) if k.any() else None
    for k2, nm in (("g", "g"), ("price", "price"), ("funding_paid", "funding_paid"), ("fee", "fee"), ("unk", "unknown_excluded")):
        out[nm] = float(s[k2][m].mean())
    out["turnover_over_gross"] = float(s["turnover"][m].mean())
    out["day_stop_flattens"] = float(s["dstop"][m].sum())
    out["per_name_stops"] = float(s["nstop"][m].sum())
    out["halt_anchors"] = float(s["halt"][m].sum())
    out["hold_anchors"] = float(s["hold"][m].sum())
    out["dust_over_gross_mean"] = float(s["dust"][m].mean())
    out["unknown_notional_over_gross_mean"] = float(s["unk_notional"][m].mean())
    return out


MINE = {}
for name, lo, hi, _ in L.PERIODS:
    m = L.period_mask(A, lo, hi)
    if not m.any():
        continue
    MINE[name] = {"mean_path": metrics(MEAN, m, t5, MEAN["r5"]),
                  "per_path": {k: [metrics(s, m)[k] for s in SER] for k in ("cagr", "sharpe_daily", "maxdd_4h", "worst_30d", "cvar5_daily", "g", "nav_return")}}
    for k, v in MINE[name]["per_path"].items():
        vv = [x for x in v if x is not None]
        MINE[name].setdefault("path_distribution", {})[k] = {
            "median": float(np.median(vv)), "p05": float(np.percentile(vv, 5)), "p95": float(np.percentile(vv, 95)), "n_paths": len(vv)}
    MINE[name].pop("per_path")

# ── compare with the published table ────────────────────────────────────────────────────────────────
PUB = json.load(open(L.PINS["BT_MAIN_A0"][0]))["tables"]["per_period scaled (main)"]
NAME_MAP = {"2022H2 (PARTIAL_RECIPE)": "2022H2",
            "2023 (PARTIAL_RECIPE, before full-recipe start)": "2023pre",
            "2023 (full recipe)": "2023full", "2024": "2024", "2025": "2025", "2026H1": "2026H1",
            "2026-07-01→2026-08-31": "2026JA", "FULL_RECIPE window": "FULL_RECIPE",
            "PARTIAL_RECIPE window (not the production strategy)": "PARTIAL_RECIPE"}
chk("control.every_published_period_mapped", set(PUB) == set(NAME_MAP), {"published": sorted(PUB), "unmapped": sorted(set(PUB) - set(NAME_MAP))})

diffs = {}
worst = {"metric": None, "period": None, "abs": 0.0, "mine": None, "published": None}
for pk, mk in NAME_MAP.items():
    pm_ = PUB[pk]["mean_path"]
    mm = MINE[mk]["mean_path"]
    for met, v in pm_.items():
        if v is None or mm.get(met) is None or not isinstance(v, (int, float)):
            continue
        d = abs(float(mm[met]) - float(v))
        diffs.setdefault(met, {"max_abs": 0.0, "at": None})
        if d > diffs[met]["max_abs"]:
            diffs[met] = {"max_abs": d, "at": mk, "mine": float(mm[met]), "published": float(v)}
        rel = d / max(abs(float(v)), 1e-12)
        key = d if met in ("n_anchors", "n_days") else rel
        if met not in ("first_anchor", "last_anchor") and key > worst["abs"]:
            worst = {"metric": met, "period": mk, "abs": float(key), "mine": float(mm[met]), "published": float(v)}
    # path distribution
    for met, pv in PUB[pk].get("path_distribution", {}).items():
        mv = MINE[mk]["path_distribution"].get(met, {})
        for q in ("median", "p05", "p95"):
            if pv.get(q) is None or mv.get(q) is None:
                continue
            d = abs(float(mv[q]) - float(pv[q]))
            nm2 = f"pathdist.{met}.{q}"
            diffs.setdefault(nm2, {"max_abs": 0.0, "at": None})
            if d > diffs[nm2]["max_abs"]:
                diffs[nm2] = {"max_abs": d, "at": mk, "mine": float(mv[q]), "published": float(pv[q])}

TOL = {"n_anchors": 0.0, "n_days": 0.0, "first_anchor": 0.0, "last_anchor": 0.0}
DEFAULT_TOL = 1e-9
bad = []
for met, d in diffs.items():
    base = met.split(".")[-1]
    tol = TOL.get(met, DEFAULT_TOL if met not in ("maxdd_5m",) else 1e-9)
    scale = max(abs(d.get("published") or 0.0), 1.0 if met in ("n_anchors", "n_days", "day_stop_flattens", "per_name_stops", "halt_anchors", "hold_anchors") else 1e-3)
    if d["max_abs"] > tol * 1.0 and d["max_abs"] > 1e-9 * scale:
        bad.append({met: d})
chk("control.reproduces_published_table", not bad, {"n_metrics": len(diffs), "mismatching": bad[:12]})
chk("control.worst_relative_cell", worst["abs"] < 1e-9, worst)

rec["control"] = {"published_source": {"BT_MAIN_A0.json": L.PINS["BT_MAIN_A0"][1],
                                       "doc": "docs/RESULT_baseline_tables_A0_objB_2026-09-19.md §2"},
                  "per_metric_max_abs_diff": diffs, "worst_cell": worst}
rec["table_mine"] = MINE

np.savez_compressed(f"{L.ROOT}/work/AT_L1_mean.npz", A=A,
                    **{k: MEAN[k] for k in ("r", "g", "price", "funding_paid", "fee", "unk", "turnover", "dstop", "nstop", "halt", "hold")},
                    r5=MEAN["r5"], t5=t5,
                    per_path_g=np.stack([s["g"] for s in SER]).astype(np.float32))
rec["outputs"] = {"L1_mean": {"path": f"{L.ROOT}/work/AT_L1_mean.npz", "sha256": L.sha(f"{L.ROOT}/work/AT_L1_mean.npz")}}

v = L.write_receipt(rec, chk, f"{OUT}/AT_CONTROL.json", {"peak_rss_gb": L.rss_gb(), "runtime_s": round(time.time() - T0, 1)})
print("AT_CONTROL VERDICT=%s checks=%d failed=%s" % (v, len(chk.rows), chk.fails), flush=True)
sys.exit(0 if v == "PASS" else 3)
