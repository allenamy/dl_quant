"""fa_c0.py — PREREG docs/PREREG_fresh_rootcause_C0_2026-09-24.md (424a00d79). Read-only, no engine.
Does the threshold mechanism carry the loss AT THE BOOK LAYER? Split the high-seat tercile by both arms'
publication state. Criterion frozen before the numbers: share(G2) >= 0.50 for SUPPORTED, and if G2's
bps/anchor is POSITIVE the mechanism cannot be called a loss carrier regardless of share.
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x
OUT = sys.argv[2]
F = "/dev/shm/fresh_2026-09-23"; N = "/dev/shm/news_2026-09-23"
SER = "/dev/shm/fanom_2026-09-24/receipts/FA_ANCHOR_SERIES.npz"
PRE = ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"); Q33, Q67 = 0.5725596881282329, 0.7810047984528542
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))

def main():
    rec = {"device": "fa_c0.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "prereg": {"path": "docs/PREREG_fresh_rootcause_C0_2026-09-24.md", "commit": "424a00d79"},
           "related_finding": "seat_pushes_book_through_its_own_preflight_2026_09_20 (same class of mechanism)",
           "lead_caveat": "news2 measured on NEW vs NC that on hold anchors the stale book earned MORE and the hold "
                          "population was only 2.1% of the gap; so 'more holding' is not 'holding caused the loss'"}
    S = np.load(SER); ax = S["anchors"].astype(np.int64); d = S["price_diff_D_minus_A_bps"]
    seat = S["seat_king_FRESH"].astype(np.float64); pre = S["in_pre2026"].astype(bool)
    CF = np.load(f"{F}/work/combo_s42/scaled_diagnostic.npz", allow_pickle=True)
    CN = np.load(f"{N}/work/combo_s42/scaled_diagnostic.npz", allow_pickle=True)
    ce = CF["E_ts"].astype(np.int64); assert np.array_equal(ce, CN["E_ts"].astype(np.int64))
    cpos = {int(t): i for i, t in enumerate(ce)}
    ci = np.array([cpos.get(int(t), -1) for t in ax]); ok = ci >= 0
    pubF = np.zeros(len(ax), bool); pubN = np.zeros(len(ax), bool)
    pubF[ok] = np.asarray(CF["trade_mask"])[ci[ok]].astype(bool)
    pubN[ok] = np.asarray(CN["trade_mask"])[ci[ok]].astype(bool)
    terc = np.where(seat <= Q33, 0, np.where(seat <= Q67, 1, 2))
    pop = pre & (terc == 2) & ok
    den = float(np.nansum(d[pop]))
    rec["population"] = {"n_anchors": int(pop.sum()), "expected_from_A2": 1832,
                         "sum_bps": den, "mean_bps_per_anchor": float(np.nanmean(d[pop])),
                         "anchors_without_combo_row": int((pre & (terc == 2) & ~ok).sum())}
    assert int(pop.sum()) == 1832, f"population is {int(pop.sum())}, expected 1832 (A2's high-seat tercile)"
    groups = {"G1_both_publish": pop & pubF & pubN, "G2_FRESH_hold_NEWS_publish": pop & ~pubF & pubN,
              "G3_FRESH_publish_NEWS_hold": pop & pubF & ~pubN, "G4_both_hold": pop & ~pubF & ~pubN}
    rows = {}; tot = 0.0; n = 0
    for g, m in groups.items():
        s = float(np.nansum(d[m])); tot += s; n += int(m.sum())
        frac_n = int(m.sum()) / int(pop.sum())
        rows[g] = {"n_anchors": int(m.sum()), "anchor_fraction": frac_n, "sum_bps": s,
                   "bps_per_anchor": float(np.nanmean(d[m])) if m.any() else None,
                   "share_of_high_seat_loss": (s / den if den else None),
                   "over_representation": ((s / den) / frac_n if den and frac_n else None)}
    closes = abs(tot - den) <= 1e-9 * max(1.0, abs(den)) and n == int(pop.sum())
    assert closes, f"groups do not close: {tot} vs {den}, {n}/{int(pop.sum())}"
    rec["groups"] = {"rows": rows, "sum_of_shares": float(tot / den), "CLOSES": bool(closes)}
    g2 = rows["G2_FRESH_hold_NEWS_publish"]
    sh = g2["share_of_high_seat_loss"]; ip = g2["bps_per_anchor"]
    verdict = "SUPPORTED" if sh >= 0.50 else ("UNDECIDED" if sh >= 0.25 else "REFUTED")
    biggest = max(rows.items(), key=lambda kv: kv[1]["share_of_high_seat_loss"])
    rec["criterion"] = {"share_G2": sh, "G2_bps_per_anchor": ip,
                        "G2_intensity_positive_means_not_a_loss_carrier": bool(ip is not None and ip > 0),
                        "VERDICT": verdict, "largest_share_group": biggest[0],
                        "largest_share_value": biggest[1]["share_of_high_seat_loss"],
                        "frozen_in": "PREREG 424a00d79 §3"}
    rec["VERDICT"] = verdict
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    print("FA_C0 VERDICT=%s share_G2=%.4f G2_bps_per_anchor=%+.4f G2_positive=%s | largest=%s (%.4f) | den=%.2fbps n=%d closes=%s"
          % (verdict, sh, ip, rec["criterion"]["G2_intensity_positive_means_not_a_loss_carrier"],
             biggest[0], biggest[1]["share_of_high_seat_loss"], den, int(pop.sum()), closes), flush=True)
    for g, v in rows.items():
        print("   %-28s n=%-5d frac=%.3f bps/anchor=%+8.4f share=%+.4f over_rep=%+.2f"
              % (g, v["n_anchors"], v["anchor_fraction"], v["bps_per_anchor"], v["share_of_high_seat_loss"], v["over_representation"]), flush=True)

if __name__ == "__main__":
    main()
    assert os.path.exists(OUT), f"device finished without writing {OUT}"
