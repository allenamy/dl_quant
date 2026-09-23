#!/usr/bin/env python3
"""news_vs_new.py — REPORT ONLY (not a rule; the SWAP verdict is news_stats.py / NEWS_STATS.json): how much NEW_S gives up relative to the
researcher's NEW (Stage 1 OVN_NEW_s42 / OVN_NEW_s2027, same seeds, same certified engine, same 32 paths with common random numbers).
d̄(NEW_S_s − NEW_s) per segment on the base cell and the three cost cells, with the same full-UTC-day convention, the same dbar / boot
functions (imported from news_stats.py, which copies them verbatim from Stage 1 ovn_stats.py) and the same 30-day MBB (B=10,000, rng
[20260923,1]). NEW path files are re-checked against their own json sha (load_cell). Levels for NEW are read from Stage 1 OVN_STATS.json.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B news_vs_new.py PATH,HOME,LC_CTYPE <stage1_runs> <news_runs>
         <stage1 OVN_STATS.json> <NEWS_STATS.json> <out.json>"""
import os, sys, json, time, hashlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
    for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
    S1R, NR, OVN, NST, OUT = sys.argv[2:7]
    sys.path.insert(0, HERE)
    import news_stats as NS
    import bt_tables as BT
    import bt_driver_lib as DL
    NS.BT, NS.DL = BT, DL
    for k, h in NS.DEV.items(): assert sha(os.path.join(HERE, k)) == h, f"{k} sha"
    ovn = json.load(open(OVN)); nst = json.load(open(NST))
    cells = ("base", "fee_x1.25", "slip_x1.5", "fill_x0.9")
    rec = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "news_stats_sha256": sha(os.path.join(HERE, "news_stats.py")),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "status": "REPORT_ONLY_NOT_A_RULE",
           "inputs": {"stage1_runs": S1R, "news_runs": NR, "OVN_STATS": {"path": OVN, "sha256": sha(OVN)}, "NEWS_STATS": {"path": NST, "sha256": sha(NST)}},
           "segments": NS.SEG, "seeds": {}}
    A0 = None
    for seed in ("42", "2027"):
        new = {c: NS.load_cell(os.path.join(S1R, f"OVN_NEW_s{seed}_{NS.CELLS[c]}"), f"OVN_NEW_s{seed}_{NS.CELLS[c]}")[0] for c in cells}
        nws = {c: NS.load_cell(os.path.join(NR, f"NEWS_s{seed}_{NS.CELLS[c]}"), f"NEWS_s{seed}_{NS.CELLS[c]}")[0] for c in cells}
        A = new["base"][0]["A"]
        for c in cells:
            assert np.array_equal(new[c][0]["A"], A) and np.array_equal(nws[c][0]["A"], A), f"axis {c}"
        if A0 is None: A0 = A
        assert np.array_equal(A, A0)
        masks = {s: NS.seg_mask(A, a, b) for s, (a, b) in NS.SEG.items()}; days = {s: NS.full_days(A, masks[s]) for s in NS.SEG}
        out = {}
        for s in NS.SEG:
            db, D = NS.dbar(nws["base"], new["base"], masks[s], days[s])
            row = {"mean_bps_per_day": float(1e4 * db.mean()), "n_days": int(len(db)), "n_paths": int(D.shape[0])}
            if s == "pre2026": row["intervals_report_only"] = {"boot_30d": NS.boot(db, NS.BLOCK_MAIN), "boot_5d": NS.boot(db, NS.BLOCK_SENS)}
            if s in ("pre2026", "2026"):
                row["cost_cells_bps_per_day"] = {c: float(1e4 * NS.dbar(nws[c], new[c], masks[s], days[s])[0].mean()) for c in cells if c != "base"}
            out[s] = row
        # linearity cross-check: d̄(NEWS−OLD) − d̄(NEW−OLD) from the two receipts must equal d̄(NEWS−NEW) (same days, same paths, same OLD)
        chk = {}
        for ctrl in ("OLD",):
            a = nst["rules"][f"NEWS_s{seed}"]["S1"][ctrl]["estimate_bps_per_day"]
            b = ovn["criteria"][f"NEW_s{seed}"][ctrl]["G1"]["estimate_bps_per_day"]
            chk[ctrl] = {"NEWS_minus_OLD": a, "NEW_minus_OLD": b, "difference": (a - b) if b is not None else None, "direct": out["pre2026"]["mean_bps_per_day"]}
        levels = {}
        for s in NS.SEG:
            L = {}
            for tag, T in (("NEW", ovn["tables"][f"NEW_s{seed}"]["base"][s]["paths"]), ("NEW_S", nst["tables"][f"NEWS_s{seed}"]["base"][s]["paths"])):
                L[tag] = {k: T[k]["path_mean"] for k in ("sharpe", "total_return", "cagr", "maxdd_5m", "worst_day", "g", "turnover_over_gross", "hold_anchors", "day_stop_flattens")}
            levels[s] = L
        rec["seeds"][f"s{seed}"] = {"dbar_NEWS_minus_NEW": out, "linearity_check_vs_receipts": chk, "levels_path_mean": levels}
        segs = ", ".join("%s %+.3f" % (s, out[s]["mean_bps_per_day"]) for s in ("2023H2", "2024", "2025", "2026"))
        ci = [round(x, 3) for x in out["pre2026"]["intervals_report_only"]["boot_30d"]["ci97.5_two_sided_bps"]]
        print("NEWS_VS_NEW s%s: pre2026 d(NEW_S-NEW) %+.3f bps/d 30d97.5 %s segs %s linearity diff %s" % (seed, out["pre2026"]["mean_bps_per_day"], ci, segs, chk["OLD"]["difference"]), flush=True)
    json.dump(rec, open(OUT, "w"), indent=1)
    print("NEWS_VS_NEW written", OUT, sha(OUT), flush=True)


if __name__ == "__main__":
    main()
