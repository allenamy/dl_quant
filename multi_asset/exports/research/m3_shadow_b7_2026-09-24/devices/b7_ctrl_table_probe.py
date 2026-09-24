#!/usr/bin/env python3
"""b7_ctrl_table_probe.py — POST-HOC, DESCRIPTIVE, NON-GATING (written AFTER the B7 verdict). Why did the positive control miss its frozen
1e-6 gate? The gate assumed the certified price table price_full_raw_x0918r holds log(close) at each 4h boundary exactly, so that 4h log
returns from the table and from the venue's 4h kline closes agree to float64 rounding. This probe measures that assumption directly: for
every name of the control (all names in the kline subset that exist in the certified table), over the control window [ACTRL − 180×4h, ACTRL],
it compares the table's 4h log returns (differences of the table at the 181 boundaries) with log(close_k / close_{k−1}) from the klines.
Only finite pairs are compared. Also reports the table's dtype. pod2, read-only inputs (mmap).
usage: /workspace/venv/bin/python -B b7_ctrl_table_probe.py <closes_json> <out_json>
  closes_json: {symbol: {boundary_ts: close_string}} built on the Mac from KLINES_RAW.jsonl.gz (b7 fetch, sha in FETCH_MANIFEST.json)
"""
import sys, json, hashlib, time
import numpy as np

A = 1789761600; H4 = 14400; ROW = 300
TAB = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r.npy"
META = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r_meta.npz"; META_SHA = "d1e49cc9f0a7ddc4104feb52a42da3024ba1e66ad5891a26c96f00cff7ce5d90"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def qs(x):
    x = np.asarray(x, float)
    if x.size == 0: raise ValueError("empty sequence")
    return {"n": int(x.size), "p50": float(np.quantile(x, .5)), "p90": float(np.quantile(x, .9)), "p99": float(np.quantile(x, .99)), "max": float(x.max())}


cp, outp = sys.argv[1:3]
assert sha(META) == META_SHA, "pinned meta"
T = np.load(TAB, mmap_mode="r"); PM = np.load(META, allow_pickle=True)
g = PM["grid"].astype(np.int64); sy = {str(s): j for j, s in enumerate(PM["symbols"])}
K = json.load(open(cp))
bnd = list(range(A - 180 * H4, A + 1, H4)); rows = [(t - int(g[0])) // ROW for t in bnd]
assert all(int(g[r]) == t for r, t in zip(rows, bnd))
per_bar, per_name, n_names, skipped = [], [], 0, 0
for s, cl in sorted(K.items()):
    if s not in sy: skipped += 1; continue
    j = sy[s]
    p = np.array([float(T[r, j]) for r in rows])
    c = np.array([np.log(float(cl[str(t)])) if str(t) in cl else np.nan for t in bnd])
    e = np.diff(p) - np.diff(c); e = e[np.isfinite(e)]
    if e.size == 0: continue
    n_names += 1; per_bar.extend(np.abs(e).tolist()); per_name.append([s, float(np.abs(e).max()), float(np.median(np.abs(e))), int(e.size)])
rec = {"device": "b7_ctrl_table_probe.py", "self_sha256": sha(sys.argv[0]), "status": "POST-HOC DESCRIPTIVE, NON-GATING",
       "table": TAB, "table_dtype": str(T.dtype), "table_shape": list(T.shape), "meta_sha256": META_SHA, "closes_json_sha256": sha(cp),
       "anchor": A, "n_names_compared": n_names, "n_names_not_in_table": skipped,
       "abs_diff_4h_logret_per_bar": qs(per_bar), "n_bars_over_1e-9": int(sum(1 for v in per_bar if v > 1e-9)), "n_bars_total": len(per_bar),
       "per_name_max_abs_diff": qs([r[1] for r in per_name]),
       "top8_names_by_max": sorted(per_name, key=lambda r: -r[1])[:8],
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(rec, open(outp, "w"), indent=1)
print("B7_CTRL_TABLE_PROBE DONE", json.dumps({k: rec[k] for k in ("table_dtype", "n_names_compared", "abs_diff_4h_logret_per_bar", "n_bars_over_1e-9", "n_bars_total")}))
