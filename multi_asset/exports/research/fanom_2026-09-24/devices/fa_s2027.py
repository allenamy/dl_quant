"""fa_s2027.py — PREREG docs/PREREG_fresh_rootcause_s2027_2026-09-24.md (328985964).
G0b for s2027, then reproduce A2 and C0 on s2027. Saves the small per-anchor series so the cell can be freed.
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x
OUT = sys.argv[2]
ENG = "/dev/shm/fresh_2026-09-23/engine"; sys.path.insert(0, ENG)
import bt_tables as BT, bt_driver_lib as DL
F = "/dev/shm/fresh_2026-09-23"; N = "/dev/shm/news_2026-09-23"
MAN = "/dev/shm/fanom_2026-09-24/FRESH_RUNS_MANIFEST.json"
CELL_D = f"{F}/runs/FRESH_s2027_scaled_rule_raw_UAFE"; CELL_A = f"{N}/runs/NEWS_s2027_scaled_rule_raw_UAFE"
PRE = ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"); Q33, Q67 = 0.5725596881282329, 0.7810047984528542
NP = 32; S42_SHARE_G2 = 0.4203
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def q(v, m):
    vv = v[m]; vv = vv[np.isfinite(vv)]
    return {"median": float(np.median(vv)), "q25": float(np.percentile(vv, 25)), "q75": float(np.percentile(vv, 75))} if len(vv) else None
def load(cell):
    tag = os.path.basename(cell); out = []
    for k in range(NP):
        s = f"{cell}/PATH_{tag}_seed_{k:02d}"
        J = json.load(open(s + ".json")); assert J["npz_sha256"] == sha(s + ".npz")
        assert DL.audits_clean(J["audits"]) and int(J["seed"]) == k
        out.append(BT.series_from_path(np.load(s + ".npz")))
    return out

def main():
    rec = {"device": "fa_s2027.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seed": 2027,
           "prereg": {"path": "docs/PREREG_fresh_rootcause_s2027_2026-09-24.md", "commit": "328985964"}}
    # ---- G0b ----
    M = json.load(open(MAN)); want = M["cells"]["FRESH_s2027_scaled_rule_raw_UAFE"]["paths"]
    per = {}; ok = True; nchk = 0
    for fn, wsha in sorted(want.items()):
        p = os.path.join(CELL_D, fn)
        a = sha(p) if os.path.exists(p) else None; same = (a == wsha); nchk += 1
        per[fn] = {"match": bool(same)}
        if not same: per[fn].update({"want": wsha, "got": a})
        ok = ok and same
    rec["G0b"] = {"n_checked": nchk, "all_match": bool(ok), "manifest_sha256": sha(MAN)}
    assert nchk == 32, f"G0b vacuous or wrong count: {nchk}"
    if not ok:
        rec["VERDICT"] = "STOPPED: G0b failed for s2027"
        rec["G0b"]["mismatches"] = {k: v for k, v in per.items() if not v["match"]}
        json.dump(rec, open(OUT, "w"), indent=1, default=float)
        print("FA_S2027 VERDICT=STOPPED G0b_FAILED n_checked=%d" % nchk, flush=True); sys.exit(3)
    # ---- per-anchor series ----
    D = load(CELL_D); A = load(CELL_A); ax = D[0]["A"]
    for p in D + A: assert np.array_equal(p["A"], ax)
    d = np.mean([p["pnl"] for p in D], axis=0) - np.mean([p["pnl"] for p in A], axis=0)
    LF = np.load(f"{F}/work/legs.npz"); LN = np.load(f"{N}/work/legs.npz"); le = LF["E_ts"].astype(np.int64)
    # prereg §0: assert the seat is the SAME object s42 used (legs is per-arm, not per-seed)
    S42 = np.load("/dev/shm/fanom_2026-09-24/receipts/FA_ANCHOR_SERIES.npz")
    sp = {int(t): i for i, t in enumerate(le)}; si = np.array([sp[int(t)] for t in ax])
    seat = LF["WL"][si, 0].astype(np.float64)
    assert np.array_equal(S42["anchors"].astype(np.int64), ax), "engine axis differs from s42's"
    assert np.array_equal(np.nan_to_num(S42["seat_king_FRESH"], nan=-9e9), np.nan_to_num(seat, nan=-9e9)), \
        "seat differs between seeds -- prereg §0's structural claim is wrong"
    rec["seat_identical_to_s42"] = True
    pre = (ax >= ts(PRE[0])) & (ax <= ts(PRE[1]))
    terc = np.where(seat <= Q33, 0, np.where(seat <= Q67, 1, 2))
    np.savez_compressed("/dev/shm/fanom_2026-09-24/receipts/FA_ANCHOR_SERIES_s2027.npz",
                        anchors=ax, price_diff_D_minus_A_bps=d, seat_king_FRESH=seat, in_pre2026=pre)
    rec["derived_series"] = {"path": "/dev/shm/fanom_2026-09-24/receipts/FA_ANCHOR_SERIES_s2027.npz",
                            "sha256": sha("/dev/shm/fanom_2026-09-24/receipts/FA_ANCHOR_SERIES_s2027.npz")}
    # ---- A2 reproduction ----
    CF = np.load(f"{F}/work/combo_s2027/scaled_diagnostic.npz", allow_pickle=True)
    CN = np.load(f"{N}/work/combo_s2027/scaled_diagnostic.npz", allow_pickle=True)
    ce = CF["E_ts"].astype(np.int64); cpos = {int(t): i for i, t in enumerate(ce)}
    ci = np.array([cpos.get(int(t), -1) for t in ax]); cok = ci >= 0
    pop = pre & (terc == 2) & cok
    assert int(pop.sum()) == 1832, f"high-seat population {int(pop.sum())} != 1832"
    a2 = {"gross_floor": 0.4, "arms": {}}
    for arm, C in (("FRESH", CF), ("NEWS", CN)):
        g = np.full(len(ax), np.nan); hd = np.zeros(len(ax), bool)
        g[cok] = np.abs(C["raw"])[ci[cok]].sum(1); hd[cok] = ~np.asarray(C["trade_mask"])[ci[cok]].astype(bool)
        a2["arms"][arm] = {}
        for nm, m in (("high_seat", pop), ("rest", pre & (terc != 2) & cok)):
            a2["arms"][arm][nm] = {"n": int(m.sum()), "raw_gross": q(g, m), "hold_fraction": float(hd[m].mean()),
                                   "frac_gross_below_0.4": float((g[m] < 0.4).mean())}
    hf = a2["arms"]["FRESH"]["high_seat"]; hn = a2["arms"]["NEWS"]["high_seat"]
    straddle = bool(hf["raw_gross"]["median"] < 0.4 <= hn["raw_gross"]["median"])
    more_hold = bool(hf["hold_fraction"] > hn["hold_fraction"])
    a2["VERDICT"] = ("REPRODUCED" if (more_hold and straddle) else ("PARTIAL" if more_hold else "NOT REPRODUCED"))
    a2["more_hold"] = more_hold; a2["straddles_floor"] = straddle
    rec["A2_s2027"] = a2
    # ---- C0 reproduction ----
    pubF = np.zeros(len(ax), bool); pubN = np.zeros(len(ax), bool)
    pubF[cok] = np.asarray(CF["trade_mask"])[ci[cok]].astype(bool)
    pubN[cok] = np.asarray(CN["trade_mask"])[ci[cok]].astype(bool)
    den = float(np.nansum(d[pop]))
    groups = {"G1_both_publish": pop & pubF & pubN, "G2_FRESH_hold_NEWS_publish": pop & ~pubF & pubN,
              "G3_FRESH_publish_NEWS_hold": pop & pubF & ~pubN, "G4_both_hold": pop & ~pubF & ~pubN}
    rows = {}; tot = 0.0; n = 0
    for gname, m in groups.items():
        s = float(np.nansum(d[m])); tot += s; n += int(m.sum()); fr = int(m.sum()) / int(pop.sum())
        rows[gname] = {"n_anchors": int(m.sum()), "anchor_fraction": fr, "sum_bps": s,
                       "bps_per_anchor": float(np.nanmean(d[m])) if m.any() else None,
                       "share": (s / den if den else None), "over_representation": ((s / den) / fr if den and fr else None)}
    closes = abs(tot - den) <= 1e-9 * max(1.0, abs(den)) and n == int(pop.sum())
    assert closes, "C0 groups do not close"
    shg2 = rows["G2_FRESH_hold_NEWS_publish"]["share"]
    c0v = "SUPPORTED" if shg2 >= 0.50 else ("UNDECIDED" if shg2 >= 0.25 else "REFUTED")
    biggest = max(rows.items(), key=lambda kv: kv[1]["share"])
    rec["C0_s2027"] = {"denominator_bps": den, "rows": rows, "CLOSES": bool(closes), "share_G2": shg2,
                       "VERDICT": c0v, "largest_share_group": biggest[0], "largest_share": biggest[1]["share"]}
    # ---- cross-seed consistency (frozen) ----
    same_band = bool((shg2 >= 0.25) == (S42_SHARE_G2 >= 0.25) and (shg2 >= 0.50) == (S42_SHARE_G2 >= 0.50))
    g1_low_both = bool(rows["G1_both_publish"]["share"] < 0.10 and 0.0333 < 0.10)
    cons = bool(a2["VERDICT"] == "REPRODUCED" and same_band and g1_low_both)
    rec["cross_seed"] = {"s42_share_G2": S42_SHARE_G2, "s2027_share_G2": shg2, "same_band": same_band,
                         "G1_share_s2027": rows["G1_both_publish"]["share"], "G1_share_s42": 0.0333,
                         "G1_below_0.10_both": g1_low_both, "A2_verdict": a2["VERDICT"],
                         "VERDICT": "CONSISTENT" if cons else "INCONSISTENT",
                         "if_inconsistent": "the s42 structure does not carry across seeds; the October decision must not rest on s42 alone",
                         "frozen_in": "PREREG 328985964 §2"}
    rec["VERDICT"] = rec["cross_seed"]["VERDICT"]
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    print("FA_S2027 G0b=PASS(32/32) seat_identical=%s | A2=%s (hold F=%.3f N=%.3f, gross med F=%.4f N=%.4f, straddle=%s) | "
          "C0=%s share_G2=%.4f largest=%s(%.4f) | CROSS_SEED=%s"
          % (rec["seat_identical_to_s42"], a2["VERDICT"], hf["hold_fraction"], hn["hold_fraction"],
             hf["raw_gross"]["median"], hn["raw_gross"]["median"], straddle, c0v, shg2, biggest[0], biggest[1]["share"],
             rec["cross_seed"]["VERDICT"]), flush=True)
    for gname, v in rows.items():
        print("   %-28s n=%-5d frac=%.3f bps/anchor=%+8.4f share=%+.4f over_rep=%+.2f"
              % (gname, v["n_anchors"], v["anchor_fraction"], v["bps_per_anchor"], v["share"], v["over_representation"]), flush=True)

if __name__ == "__main__":
    main()
    assert os.path.exists(OUT), f"device finished without writing {OUT}"
