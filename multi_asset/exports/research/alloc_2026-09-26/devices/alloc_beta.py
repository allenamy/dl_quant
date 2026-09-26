#!/usr/bin/env python3
"""alloc_beta.py — DECISION_RULE_combination_layer §5 required report (not a gate): the book's daily beta to BTC, arm vs same-seed NC.
Committed before it is run on any arm.
Book daily return: the frozen judge's convention (news_stats.load_cell -> bt_tables.series_mean -> bt_tables.daily over UTC full days,
i.e. the 32-path mean path, prod(1 + r) over the six 4h windows). BTC daily return: the engine's own 5-minute RAW log-price table
(price_full_raw_x0918r.npy, the certified run's price source), exp(lp[D+1 00:00Z] - lp[D 00:00Z]) - 1 for BTCUSDT.
beta = cov(book, btc) / var(btc) per segment (pre2026; 2026 extended to 09-18T20Z), per seed, arm and NC, and the difference.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B alloc_beta.py PATH,HOME,LC_CTYPE <arm> <seed,seed,...> <out.json>
"""
import os, sys, json, hashlib, time
import numpy as np
ENG = "/dev/shm/news2_2026-09-23/engine"; NS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
PX = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r.npy"; PXM = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r_meta.npz"
CELLS = "/workspace/alloc_2026-09-26/cells"
REF = "/workspace/dlarch_2026-09-24/chain/ref_nc_s{s}X/runs/DLARCH_REF_NC_s{s}X_scaled_rule_raw_UAFE"; REF_TAG = "DLARCH_REF_NC_s{s}X_scaled_rule_raw_UAFE"
sys.path.insert(0, ENG)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra
    arm, seeds, out = sys.argv[2], [int(x) for x in sys.argv[3].split(",")], sys.argv[4]
    assert sha(f"{ENG}/news_stats.py") == NS_SHA
    import news_stats as S, bt_tables as BT, bt_driver_lib as DL
    S.BT, S.DL = BT, DL
    m = np.load(PXM); grid = m["grid"].astype(np.int64); j = int(np.flatnonzero(m["symbols"] == "BTCUSDT")[0])
    lp = np.load(PX, mmap_mode="r")[:, j].astype(np.float64)
    seg = {"pre2026": S.SEG["pre2026"], "2026": ("2026-01-01T00:00:00Z", "2026-09-18T20:00:00Z")}
    res = {}
    for s in seeds:
        tag = f"ALLOC_{arm}_s{s}X_scaled_rule_raw_UAFE"
        pa, _ = S.load_cell(f"{CELLS}/{arm}_s{s}/runs/{tag}", tag); pr, _ = S.load_cell(REF.format(s=s), REF_TAG.format(s=s))
        ma, mr = BT.series_mean(pa), BT.series_mean(pr); A = ma["A"]
        res[str(s)] = {}
        for k, (a, b) in seg.items():
            msk = S.seg_mask(A, a, b); days = S.full_days(A, msk)
            ra = S.daily_on(A[msk], ma["r"][msk], days); rr = S.daily_on(A[msk], mr["r"][msk], days)
            i0 = np.searchsorted(grid, days); i1 = np.searchsorted(grid, days + 86400)
            ok = (i1 < len(grid)) & (grid[np.minimum(i0, len(grid) - 1)] == days) & (grid[np.minimum(i1, len(grid) - 1)] == days + 86400)
            ok &= np.isfinite(lp[np.minimum(i0, len(grid) - 1)]) & np.isfinite(lp[np.minimum(i1, len(grid) - 1)])
            rb = np.expm1(lp[i1[ok]] - lp[i0[ok]]); x, y = ra[ok], rr[ok]
            v = rb.var(ddof=1); ba = float(np.cov(x, rb)[0, 1] / v); bn = float(np.cov(y, rb)[0, 1] / v)
            res[str(s)][k] = {"n_days": int(ok.sum()), "n_days_dropped": int((~ok).sum()), "beta_arm": ba, "beta_NC": bn, "delta": ba - bn}
            print(f"BETA {arm} s{s} {k}: arm {ba:+.4f} NC {bn:+.4f} delta {ba - bn:+.4f} (n={int(ok.sum())})", flush=True)
    rec = {"device": "alloc_beta.py", "self_sha256": sha(os.path.abspath(__file__)), "price_table": PX, "price_meta_sha256": sha(PXM),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "arm": arm, "segments": seg, "per_seed": res,
           "mean_over_seeds": {k: {q: float(np.mean([res[str(s)][k][q] for s in seeds])) for q in ("beta_arm", "beta_NC", "delta")} for k in seg}}
    json.dump(rec, open(out + ".tmp", "w"), indent=1); os.replace(out + ".tmp", out)
    assert json.load(open(out))["self_sha256"] == rec["self_sha256"]
    print("ALLOC_BETA DONE", out, sha(out)[:16], flush=True)


if __name__ == "__main__":
    main()
