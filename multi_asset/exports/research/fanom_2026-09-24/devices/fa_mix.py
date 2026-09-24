"""fa_mix.py — PREREG docs/PREREG_seat_window_mixing_2026-09-24.md (0da6d4ae6). Read-only, no engine, no GPU.
Tests: does the book-layer loss intensity rise with the number of distinct King fold models inside the
900-anchor seat window? Criteria frozen in the prereg before any of these numbers existed.
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT = sys.argv[2]
ENG = "/dev/shm/fresh_2026-09-23/engine"; sys.path.insert(0, ENG)
import bt_tables as BT, bt_driver_lib as DL
F = "/dev/shm/fresh_2026-09-23"; N = "/dev/shm/news_2026-09-23"
CELL_D = f"{F}/runs/FRESH_s42_scaled_rule_raw_UAFE"; CELL_A = f"{N}/runs/NEWS_s42_scaled_rule_raw_UAFE"
Q33, Q67 = 0.5725596881282329, 0.7810047984528542
PRE = ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"); LOOK = 900; NP = 32; MINN = 100; MINCELL = 50
DEN_PHASE2 = -3116.454543230235

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))

def load(cell):
    tag = os.path.basename(cell); out = []
    for k in range(NP):
        s = f"{cell}/PATH_{tag}_seed_{k:02d}"
        J = json.load(open(s + ".json")); assert J["npz_sha256"] == sha(s + ".npz")
        assert DL.audits_clean(J["audits"]) and int(J["seed"]) == k
        out.append(BT.series_from_path(np.load(s + ".npz")))
    return out

def fold_id_series(root, axis):
    """for each anchor on `axis`, which King fold scored it (index into the receipt's fold list); -1 if none"""
    R = json.load(open(f"{root}/work/king/TRAIN_RECEIPT.json"))
    fid = np.full(len(axis), -1, np.int64)
    for j, f in enumerate(R["folds"]):
        m = (axis >= int(f["score_start"])) & (axis <= int(f["score_end"]))
        fid[m] = j
    return fid, [f["fold"] for f in R["folds"]]

def mixing(fid_full, n_look):
    """distinct fold ids in the preceding n_look anchors; -1 where the window is not full"""
    out = np.full(len(fid_full), -1, np.int64)
    for i in range(n_look, len(fid_full)):
        w = fid_full[i - n_look:i]
        w = w[w >= 0]
        out[i] = len(np.unique(w)) if len(w) else -1
    return out

def main():
    rec = {"device": "fa_mix.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "prereg": {"path": "docs/PREREG_seat_window_mixing_2026-09-24.md", "commit": "0da6d4ae6"},
           "look": LOOK, "primary_statistic": "bps per anchor (intensity); share reported but NOT the criterion"}
    D = load(CELL_D); A = load(CELL_A)
    ax = D[0]["A"]
    for p in D + A: assert np.array_equal(p["A"], ax)
    d = np.mean([p["pnl"] for p in D], axis=0) - np.mean([p["pnl"] for p in A], axis=0)
    # mixing is computed on the FULL legs axis (the seat window reaches back before the engine axis starts)
    leg = np.load(f"{F}/work/legs.npz"); le = leg["E_ts"].astype(np.int64)
    fidF, foldsF = fold_id_series(F, le); fidA, foldsA = fold_id_series(N, le)
    mixF_full = mixing(fidF, LOOK); mixA_full = mixing(fidA, LOOK)
    pos = {int(t): i for i, t in enumerate(le)}
    idx = np.array([pos[int(t)] for t in ax])
    mixF = mixF_full[idx]; mixA = mixA_full[idx]; seat = leg["WL"][idx, 0].astype(np.float64)
    pre = (ax >= ts(PRE[0])) & (ax <= ts(PRE[1]))
    rec["fold_counts"] = {"FRESH": len(foldsF), "NEWS": len(foldsA)}
    # ---- §4 zero control: NEW_S annual-fold mixing distribution; device check ----
    va, ca = np.unique(mixA[pre & (mixA >= 0)], return_counts=True)
    vf, cf = np.unique(mixF[pre & (mixF >= 0)], return_counts=True)
    zc = {"NEWS_annual_mix_distribution": {int(k): int(v) for k, v in zip(va, ca)},
          "FRESH_monthly_mix_distribution": {int(k): int(v) for k, v in zip(vf, cf)}}
    news_mostly_low = float(sum(int(v) for k, v in zip(va, ca) if int(k) <= 2)) / max(1, int(ca.sum()))
    zc["NEWS_share_mix_le_2"] = news_mostly_low
    zc["DEVICE_CHECK_PASS"] = bool(news_mostly_low >= 0.5)
    zc["rule"] = "prereg §4: if NEW_S's mixing is also mostly >=3 the mix computation is wrong; STOP, no verdict"
    rec["zero_control"] = zc
    if not zc["DEVICE_CHECK_PASS"]:
        rec["VERDICT"] = "STOPPED: zero control failed, mix likely miscomputed"
        json.dump(rec, open(OUT, "w"), indent=1, default=float)
        print("FA_MIX VERDICT=STOPPED zero_control_failed NEWS_share_mix_le_2=%.3f" % news_mostly_low, flush=True)
        sys.exit(3)
    # ---- population: prereg §6 excludes anchors whose seat window is not full ----
    pop = pre & (mixF >= 0)
    excluded = int((pre & (mixF < 0)).sum())
    den_pop = float(np.nansum(d[pop]))
    rec["population"] = {"phase2_denominator_bps": DEN_PHASE2, "phase2_anchors": int(pre.sum()),
                         "excluded_incomplete_window": excluded, "anchors_after_exclusion": int(pop.sum()),
                         "sum_after_exclusion_bps": den_pop, "difference_vs_phase2_bps": den_pop - DEN_PHASE2,
                         "fraction_of_phase2_denominator": den_pop / DEN_PHASE2 if DEN_PHASE2 else None,
                         "note": "shares below close to 1 over the POST-EXCLUSION sum, per prereg §6"}
    # ---- main table ----
    levels = sorted(int(v) for v in np.unique(mixF[pop]))
    rows = {}; tot = 0.0; n = 0
    for L in levels:
        m = pop & (mixF == L); s = float(np.nansum(d[m])); tot += s; n += int(m.sum())
        rows[L] = {"n_anchors": int(m.sum()), "sum_bps": s,
                   "bps_per_anchor": float(np.nanmean(d[m])) if m.any() else None,
                   "share_of_post_exclusion_sum": float(s / den_pop) if den_pop else None,
                   "effective": bool(int(m.sum()) >= MINN)}
    closes = abs(tot - den_pop) <= 1e-9 * max(1.0, abs(den_pop)) and n == int(pop.sum())
    assert closes, f"mixing buckets do not close: {tot} vs {den_pop}, {n}/{int(pop.sum())}"
    rec["by_mixing"] = {"rows": rows, "sum_of_shares": float(tot / den_pop), "CLOSES": bool(closes), "min_n_effective": MINN}
    # ---- frozen criterion ----
    eff = [L for L in levels if rows[L]["effective"]]
    v = [rows[L]["bps_per_anchor"] for L in eff]
    best_run = 0
    if len(v) >= 2:
        run = 1
        for i in range(1, len(v)):
            run = run + 1 if v[i] <= v[i - 1] else 1
            best_run = max(best_run, run)
    cond1 = best_run >= 3
    cond2 = bool(len(eff) >= 2 and v[-1] < v[0])
    if len(eff) < 3:
        verdict = "UNDECIDED"
    else:
        verdict = "SUPPORTED" if (cond1 and cond2) else "REFUTED"
    rec["criterion"] = {"effective_levels": eff, "bps_per_anchor_in_order": v,
                        "longest_monotone_nonincreasing_run": best_run, "cond1_run_ge_3": bool(cond1),
                        "cond2_highest_more_negative_than_lowest": cond2, "VERDICT": verdict,
                        "frozen_in": "PREREG 0da6d4ae6 §3"}
    rec["VERDICT"] = verdict
    # ---- §5 separability ----
    tercile = np.where(seat <= Q33, 0, np.where(seat <= Q67, 1, 2))
    mp = mixF[pop].astype(np.float64); tp = tercile[pop].astype(np.float64)
    rm = np.argsort(np.argsort(mp)).astype(np.float64); rt = np.argsort(np.argsort(tp)).astype(np.float64)
    rho = float(np.corrcoef(rm, rt)[0, 1]) if rm.std() > 0 and rt.std() > 0 else None
    ct = {}
    for L in levels:
        ct[L] = {int(t): int(((mixF == L) & (tercile == t) & pop).sum()) for t in (0, 1, 2)}
    strat = {}
    for t in (0, 1, 2):
        strat[t] = {}
        for L in levels:
            m = pop & (tercile == t) & (mixF == L)
            if int(m.sum()) >= MINCELL:
                strat[t][L] = {"n": int(m.sum()), "bps_per_anchor": float(np.nanmean(d[m]))}
    rec["separability"] = {"spearman_mix_vs_seat_tercile": rho, "contingency_mix_by_tercile": ct,
                           "stratified_bps_per_anchor_min_n": MINCELL, "stratified": strat,
                           "rule": "prereg §5: if mix and seat are highly correlated they are not separable in this data; "
                                   "say so and do not claim the loss is attributed to mixing rather than seat"}
    # Save the small DERIVED per-anchor series so no future follow-up ever needs the 346 MiB engine cell again.
    # This is the artifact I should have kept instead of the cell: 4 arrays over 8,142 anchors, about 260 KB.
    ser = os.path.join(os.path.dirname(OUT), "FA_ANCHOR_SERIES.npz")
    np.savez_compressed(ser, anchors=ax, price_diff_D_minus_A_bps=d, mix_FRESH=mixF, mix_NEWS=mixA,
                        seat_king_FRESH=seat, in_pre2026=pre)
    rec["derived_series"] = {"path": ser, "sha256": sha(ser),
                             "arrays": ["anchors", "price_diff_D_minus_A_bps", "mix_FRESH", "mix_NEWS",
                                        "seat_king_FRESH", "in_pre2026"],
                             "why": "keeps every per-anchor quantity this line of work has needed, so the engine cell "
                                    "is disposable; regenerating the cell costs ~10 min and 350 MiB, this file is ~260 KB"}
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    print("FA_MIX VERDICT=%s levels=%s bps_per_anchor=%s run=%d cond1=%s cond2=%s | NEWS_mix<=2 share=%.3f | "
          "excluded=%d post_excl_sum=%.2fbps (%.3f of phase2) | closes=%s | spearman_mix_vs_seat=%s | receipt=%s"
          % (verdict, eff, [round(x, 4) for x in v], best_run, cond1, cond2, news_mostly_low, excluded, den_pop,
             den_pop / DEN_PHASE2, closes, ("%.4f" % rho) if rho is not None else "None", sha(OUT)), flush=True)


if __name__ == "__main__":
    main()
    assert os.path.exists(OUT), f"device finished without writing {OUT}"
