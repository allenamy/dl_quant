#!/usr/bin/env python3
"""s2_event_study.py — S2 step 2 (DECISION_RULE_nonfunding_sources_2026-09-27 §2), committed before it is run.

Events: census_events_f991bc80.jsonl, types D_upbit_krw_listing and B_binance_monitoring_tag_ADD (judged separately, m = 2), with a USDT
perp symbol that is a column of the engine's RAW 5-minute price table. t0 = the first anchor >= publish_s ("the first complete anchor after
publication"). Events whose effective time is before the next anchor (census field effective_before_next_anchor == true) are reported in a
separate row and are NOT in the main reading.
Returns: engine RAW log-price table (price_full_raw_x0918r.npy), r_i(h) = exp(lp[t0 + h] - lp[t0]) - 1 for h in {4h, 24h, 72h}.
Excess: e_i = (r_i - med) - beta_i * (r_BTC - med), med = the cross-sectional median over all names with a finite r at that (t0, h);
beta_i = OLS slope of (x_i - med_x) on (x_BTC - med_x) over the 180 trailing 4h returns ending at t0 (causal; >= 120 finite pairs,
else beta_i = 1). An event whose r_i(h) is not finite is dropped for that h (counted).
Statistic per type and horizon: mean excess over events; SE by an event block bootstrap (blocks = ISO calendar week of publication,
B = 10,000, rng (20260927, 1)); t = mean / sd_boot. Segments: pre-2026 (publish < 2026-01-01) and 2026.
Placebo: for each event, 20 anchors of the SAME name drawn from anchors that are >= 30 days from every census event of that name (any
type), inside the price grid, with finite r; same excess definition; per-event placebo value = mean of its draws; same bootstrap.
Rule §2 (per type): PASS iff pre-2026 24h |t| >= 3 AND the 2026 24h mean has the same sign AND the pre-2026 24h placebo |t| < 2.
+4h and +72h are descriptive.
usage: /workspace/venv/bin/python -B s2_event_study.py <census.jsonl> <out.json>
"""
import os, sys, json, hashlib, time, calendar, datetime
import numpy as np
CENSUS_SHA = "f991bc80966ad0b6"
PX = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r.npy"; PXM = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r_meta.npz"
TYPES = ("D_upbit_krw_listing", "B_binance_monitoring_tag_ADD")
H = {"4h": 4 * 3600, "24h": 24 * 3600, "72h": 72 * 3600}
Y26 = calendar.timegm((2026, 1, 1, 0, 0, 0)); B = 10000; RNG = (20260927, 1); NPLACEBO = 20; GAP = 30 * 86400


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    cp, out = sys.argv[1], sys.argv[2]
    assert sha(cp).startswith(CENSUS_SHA)
    ev = [json.loads(l) for l in open(cp)]
    m = np.load(PXM); grid = m["grid"].astype(np.int64); syms = [str(x) for x in m["symbols"]]; col = {s: j for j, s in enumerate(syms)}
    lp = np.load(PX, mmap_mode="r"); jb = col["BTCUSDT"]
    assert np.all(np.diff(grid) == 300), "price grid must be regular 5-minute"
    # every horizon is a multiple of 4h and every t0 is an anchor => work on the anchor rows only (loaded once)
    arow = np.flatnonzero(grid % 14400 == 0); anchors = grid[arow]
    LA = np.asarray(lp[arow], dtype=np.float64)                          # (n_anchor, 829) log prices at anchors
    R4 = np.expm1(LA[1:] - LA[:-1]); med4 = np.nanmedian(R4, axis=1)       # 4h returns (k -> k+1) and their cross-sectional median
    kpos = {int(a): k for k, a in enumerate(anchors)}
    beta_cache = {}

    def beta_of(j, k0):
        key = (j, k0)
        if key not in beta_cache:
            lo = max(0, k0 - 180); x = R4[lo:k0, jb] - med4[lo:k0]; y = R4[lo:k0, j] - med4[lo:k0]; ok = np.isfinite(x) & np.isfinite(y)
            beta_cache[key] = float(np.polyfit(x[ok], y[ok], 1)[0]) if ok.sum() >= 120 else 1.0
        return beta_cache[key]

    def excess(j, t0, h):
        k0 = kpos.get(int(t0)); q = h // 14400
        if k0 is None or k0 + q >= len(anchors): return None
        r = np.expm1(LA[k0 + q] - LA[k0]); med = np.nanmedian(r)
        if not np.isfinite(r[j]) or not np.isfinite(r[jb]): return None
        be = beta_of(j, k0)
        return float((r[j] - med) - be * (r[jb] - med)), be

    def boot_t(vals, weeks):
        vals = np.asarray(vals, float); wk = np.asarray(weeks); u = np.unique(wk)
        if len(vals) < 3: return None
        idx = {w: np.flatnonzero(wk == w) for w in u}; rng = np.random.default_rng(list(RNG)); bm = np.empty(B)
        for b_ in range(B):
            pick = rng.choice(u, size=len(u), replace=True); ii = np.concatenate([idx[w] for w in pick]); bm[b_] = vals[ii].mean()
        sd = bm.std(ddof=1)
        return {"n": int(len(vals)), "mean_bps": float(1e4 * vals.mean()), "sd_boot_bps": float(1e4 * sd), "t": float(vals.mean() / sd) if sd > 0 else None,
                "ci95_bps": [float(1e4 * np.percentile(bm, 2.5)), float(1e4 * np.percentile(bm, 97.5))]}

    ev_times = {}
    for e in ev:
        if e.get("symbol"): ev_times.setdefault(e["symbol"], []).append(int(e["publish_s"]))
    rng_p = np.random.default_rng([20260927, 2])
    rec = {"device": "s2_event_study.py", "self_sha256": sha(os.path.abspath(__file__)), "census_sha256": sha(cp), "price_meta_sha256": sha(PXM),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "types": {}}
    for t in TYPES:
        E = [e for e in ev if e["type"] == t and e.get("symbol") in col]
        rows = []; dropped = {k: 0 for k in H}
        for e in E:
            ps = int(e["publish_s"]); t0 = int(((ps + 14399) // 14400) * 14400); j = col[e["symbol"]]
            wk = datetime.datetime.utcfromtimestamp(ps).isocalendar(); wkid = f"{wk[0]}-{wk[1]:02d}"
            r = {"symbol": e["symbol"], "publish_utc": e["publish_utc"], "t0": t0, "week": wkid, "segment": "2026" if ps >= Y26 else "pre2026",
                 "effective_before_next_anchor": bool(e.get("effective_before_next_anchor")), "x": {}, "placebo": {}}
            for hk, h in H.items():
                v = excess(j, t0, h)
                if v is None: dropped[hk] += 1; continue
                r["x"][hk] = v[0]; r["beta"] = v[1]
            others = np.array(ev_times.get(e["symbol"], []))
            cand = anchors[(anchors >= anchors[0] + 180 * 14400) & (anchors <= anchors[-1] - H["72h"])]
            if len(others): cand = cand[np.min(np.abs(cand[:, None] - others[None, :]), 1) >= GAP]
            draws = rng_p.choice(cand, size=min(NPLACEBO, len(cand)), replace=False) if len(cand) else []
            for hk in ("24h",):
                vv = [excess(j, int(a), H[hk]) for a in draws]; vv = [x[0] for x in vv if x is not None]
                if vv: r["placebo"][hk] = float(np.mean(vv))
            rows.append(r)
        res = {"n_events_with_symbol_in_price_table": len(E), "dropped_nonfinite": dropped, "cells": {}}
        for grp, sel in (("main", lambda r: not r["effective_before_next_anchor"]), ("effective_before_next_anchor", lambda r: r["effective_before_next_anchor"])):
            for seg in ("pre2026", "2026"):
                rr = [r for r in rows if sel(r) and r["segment"] == seg]
                for hk in H:
                    vals = [r["x"][hk] for r in rr if hk in r["x"]]; wks = [r["week"] for r in rr if hk in r["x"]]
                    res["cells"][f"{grp}|{seg}|{hk}"] = boot_t(vals, wks)
                pv = [r["placebo"]["24h"] for r in rr if "24h" in r["placebo"]]; pw = [r["week"] for r in rr if "24h" in r["placebo"]]
                res["cells"][f"{grp}|{seg}|placebo24h"] = boot_t(pv, pw)
        c_pre = res["cells"]["main|pre2026|24h"]; c_26 = res["cells"]["main|2026|24h"]; c_pl = res["cells"]["main|pre2026|placebo24h"]
        ok = (c_pre is not None and c_pre["t"] is not None and abs(c_pre["t"]) >= 3 and c_26 is not None and np.sign(c_26["mean_bps"]) == np.sign(c_pre["mean_bps"])
              and c_pl is not None and c_pl["t"] is not None and abs(c_pl["t"]) < 2)
        res["VERDICT"] = "PASS" if ok else "FAIL"
        res["events"] = rows
        rec["types"][t] = res
        print(f"S2_EVENT {t}: pre2026 24h {c_pre} | 2026 24h {c_26} | placebo {c_pl} -> {res['VERDICT']}", flush=True)
    json.dump(rec, open(out + ".tmp", "w"), indent=1, default=float); os.replace(out + ".tmp", out)
    assert json.load(open(out))["self_sha256"] == rec["self_sha256"]
    print("S2_EVENT DONE", sha(out)[:16], flush=True)


if __name__ == "__main__":
    main()
