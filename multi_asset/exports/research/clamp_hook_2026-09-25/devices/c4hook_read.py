#!/usr/bin/env python3
"""Read the hooked cell: (0) PREREQUISITE CONTROL — the hooked seed-00 path's series (bt_tables.series_from_path, the fa_ladsave recipe)
equals row 0 of the filed SER_EXT_NEWS2_s42X.npz bitwise for r / pnl / car / cst / unk / g / tau / hold / halt; any difference ⇒ the hook
had a behavioural effect (or the run is not the filed configuration) ⇒ every hook reading is VOID. (1) hook completeness: one row per
decided anchor, hook errors 0. (2) the post-clamp net / NAV (NAV = sizing_gross / gross_mult 2.0) per anchor: distribution by year
(5/25/50/75/95 %, mean, share of anchors with any clamped name), and |net|/NAV.
usage: /workspace/venv/bin/python -B c4hook_read.py <cell dir> <hook dir> <filed SER npz> <out json>"""
import glob, json, os, sys, time, collections
import numpy as np
sys.path.insert(0, "/dev/shm/news_2026-09-23/engine")
import bt_tables as BT                      # noqa: E402
CELL, HOOK, SER, OUT = sys.argv[1:5]
tag = os.path.basename(CELL.rstrip("/"))
p = BT.series_from_path(np.load(f"{CELL}/PATH_{tag}_seed_00.npz")); S = np.load(SER)
ctrl = {}
for k in ("r", "pnl", "car", "cst", "unk", "g", "tau", "hold", "halt"):
    a = np.asarray(p[k], np.float64); b = S[k + "_per_path"][0]
    ctrl[k] = bool(a.shape == b.shape and np.ascontiguousarray(a).tobytes() == np.ascontiguousarray(b).tobytes())
ctrl["anchors"] = bool(np.array_equal(np.asarray(p["A"], np.int64), S["anchors"].astype(np.int64)))
ok = all(ctrl.values())
rows = [json.loads(l) for f in sorted(glob.glob(f"{HOOK}/HOOK_*.jsonl")) for l in open(f) if l.strip()]
errs = sum(sum(1 for _ in open(f)) for f in glob.glob(f"{HOOK}/HOOK_ERRORS_*.txt"))
by = collections.defaultdict(list); anyc = collections.Counter(); n = collections.Counter()
for r in rows:
    if r.get("A") is None or r.get("book_net_usdt") is None or not r.get("sizing_gross"): continue
    y = time.strftime("%Y", time.gmtime(r["A"])); y = y + ("H2" if y == "2023" else "")
    nav = r["sizing_gross"] / 2.0; v = r["book_net_usdt"] / nav
    for key in (y, "ALL"):
        by[key].append(v); n[key] += 1; anyc[key] += bool(r.get("clamped_names"))
dist = {k: {"n": len(v), "mean_pct": float(np.mean(v) * 100), "pct": {str(q): float(np.percentile(v, q) * 100) for q in (5, 25, 50, 75, 95)},
            "median_abs_pct": float(np.median(np.abs(v)) * 100), "share_with_clamp": anyc[k] / max(n[k], 1)} for k, v in sorted(by.items())}
rec = {"control_bitwise_vs_filed": ctrl, "CONTROL": "PASS" if ok else "FAIL (hook readings VOID)", "hook_rows": len(rows), "hook_errors": errs,
       "distinct_A": len({r.get("A") for r in rows}), "post_clamp_net_over_nav": dist if ok else "VOID"}
json.dump(rec, open(OUT, "w"), indent=1)
print("C4HOOK CONTROL", rec["CONTROL"], ctrl); print("hook rows", len(rows), "errors", errs, "distinct A", rec["distinct_A"])
if ok:
    for k, v in dist.items(): print(f"  {k}: n {v['n']} mean {v['mean_pct']:+.3f}% pct {json.dumps({q: round(x, 3) for q, x in v['pct'].items()})} median|.| {v['median_abs_pct']:.3f}% share_with_clamp {v['share_with_clamp']:.3f}")
