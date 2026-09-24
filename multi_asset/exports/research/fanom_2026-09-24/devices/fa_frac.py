"""fa_frac.py — PREREG docs/PREREG_seat_window_fraction_2026-09-24.md (54748c683). Read-only, no engine, no GPU.
SECOND test of the same mechanism; the prereg's §0 discloses that the first was UNDECIDED and that its direction
was already seen, which is why the criterion here is stricter (rank correlation AND a bootstrap interval).
Sign convention frozen in §2: intensity is SIGNED bps/anchor, so the mechanism predicts Spearman > 0.
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT = sys.argv[2]
F = "/dev/shm/fresh_2026-09-23"; N = "/dev/shm/news_2026-09-23"
SER = "/dev/shm/fanom_2026-09-24/receipts/FA_ANCHOR_SERIES.npz"
LOOK = 900; MINN = 100; MINCELL = 50; NB = 5; B = 10000; RNG = (20260923, 1); BLOCK_DAYS = 30
DEN_PHASE2 = -3116.454543230235; DAY = 86400; H4 = 14400
Q33, Q67 = 0.5725596881282329, 0.7810047984528542

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()

def fold_id_series(root, axis):
    R = json.load(open(f"{root}/work/king/TRAIN_RECEIPT.json"))
    fid = np.full(len(axis), -1, np.int64)
    for j, f in enumerate(R["folds"]):
        fid[(axis >= int(f["score_start"])) & (axis <= int(f["score_end"]))] = j
    return fid

def frac_series(fid, look):
    """fraction of the preceding `look` anchors belonging to the fold that scores anchor i; -1 if window short"""
    out = np.full(len(fid), -1.0)
    for i in range(look, len(fid)):
        cur = fid[i]
        if cur < 0: continue
        out[i] = float((fid[i - look:i] == cur).sum()) / look
    return out

def spearman(x, y):
    rx = np.argsort(np.argsort(x)).astype(float); ry = np.argsort(np.argsort(y)).astype(float)
    if rx.std() == 0 or ry.std() == 0: return None
    return float(np.corrcoef(rx, ry)[0, 1])

def main():
    rec = {"device": "fa_frac.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "prereg": {"path": "docs/PREREG_seat_window_fraction_2026-09-24.md", "commit": "54748c683"},
           "disclosure": "SECOND test; the first (0da6d4ae6) was UNDECIDED and its direction was already seen. "
                         "Criterion here is stricter: rank correlation over 5 bins AND a bootstrap interval excluding 0.",
           "sign_convention": "intensity = SIGNED bps/anchor (more negative = worse for FRESH); mechanism predicts Spearman > 0"}
    S = np.load(SER); rec["series"] = {"path": SER, "sha256": sha(SER)}
    ax = S["anchors"].astype(np.int64); d = S["price_diff_D_minus_A_bps"]; seat = S["seat_king_FRESH"]; pre = S["in_pre2026"].astype(bool)
    leg = np.load(f"{F}/work/legs.npz"); le = leg["E_ts"].astype(np.int64)
    fidF = fold_id_series(F, le); fidA = fold_id_series(N, le)
    fF_full = frac_series(fidF, LOOK); fA_full = frac_series(fidA, LOOK)
    pos = {int(t): i for i, t in enumerate(le)}; idx = np.array([pos[int(t)] for t in ax])
    fF = fF_full[idx]; fA = fA_full[idx]
    # ---- §4 zero control / device self-check: NEW_S annual frac must concentrate high ----
    za = fA[pre & (fA >= 0)]
    zc = {"NEWS_frac_mean": float(za.mean()), "NEWS_frac_median": float(np.median(za)),
          "NEWS_frac_p10": float(np.percentile(za, 10)), "NEWS_share_ge_0.5": float((za >= 0.5).mean()),
          "FRESH_frac_mean": float(fF[pre & (fF >= 0)].mean()),
          "FRESH_frac_min": float(fF[pre & (fF >= 0)].min()), "FRESH_frac_max": float(fF[pre & (fF >= 0)].max())}
    zc["DEVICE_CHECK_PASS"] = bool(zc["NEWS_share_ge_0.5"] >= 0.5)
    zc["rule"] = "prereg §4: if NEW_S's frac is NOT concentrated high, frac is miscomputed; STOP with no verdict"
    rec["zero_control"] = zc
    if not zc["DEVICE_CHECK_PASS"]:
        rec["VERDICT"] = "STOPPED: zero control failed"
        json.dump(rec, open(OUT, "w"), indent=1, default=float)
        print("FA_FRAC VERDICT=STOPPED NEWS_share_ge_0.5=%.3f" % zc["NEWS_share_ge_0.5"], flush=True); sys.exit(3)
    pop = pre & (fF >= 0)
    excluded = int((pre & (fF < 0)).sum()); den_pop = float(np.nansum(d[pop]))
    rec["population"] = {"phase2_denominator_bps": DEN_PHASE2, "excluded_incomplete_window": excluded,
                         "anchors_after_exclusion": int(pop.sum()), "sum_after_exclusion_bps": den_pop,
                         "fraction_of_phase2_denominator": den_pop / DEN_PHASE2}
    # ---- quintile bins on FRESH frac over the pre-2026 population (rule, not a number) ----
    cuts = [float(np.percentile(fF[pop], q)) for q in (20, 40, 60, 80)]
    binid = np.digitize(fF, cuts, right=True)
    rows = {}; tot = 0.0; n = 0
    for b in range(NB):
        m = pop & (binid == b); s = float(np.nansum(d[m])); tot += s; n += int(m.sum())
        rows[b] = {"n_anchors": int(m.sum()), "frac_range": [float(fF[m].min()), float(fF[m].max())] if m.any() else None,
                   "sum_bps": s, "bps_per_anchor": float(np.nanmean(d[m])) if m.any() else None,
                   "share": float(s / den_pop) if den_pop else None, "effective": bool(int(m.sum()) >= MINN)}
    closes = abs(tot - den_pop) <= 1e-9 * max(1.0, abs(den_pop)) and n == int(pop.sum())
    assert closes, f"bins do not close: {tot} vs {den_pop}, {n}/{int(pop.sum())}"
    rec["bins"] = {"quintile_cuts": cuts, "rows": rows, "sum_of_shares": float(tot / den_pop), "CLOSES": bool(closes)}
    eff = [b for b in range(NB) if rows[b]["effective"]]
    vals = [rows[b]["bps_per_anchor"] for b in eff]
    rho = spearman(np.array(eff, float), np.array(vals, float)) if len(eff) >= 2 else None
    # ---- 30-day moving-block bootstrap on the Spearman ----
    lo = hi = None
    if len(eff) == NB:
        rs = np.random.default_rng(RNG)
        days = ax[pop] // DAY; ud = np.unique(days); blk = BLOCK_DAYS
        starts = np.arange(len(ud) - blk + 1)
        dd = d[pop]; bb = binid[pop]; dayarr = days
        draws = []
        nblocks = int(np.ceil(len(ud) / blk))
        for _ in range(B):
            pick = rs.choice(starts, size=nblocks, replace=True)
            sel_days = np.concatenate([ud[s:s + blk] for s in pick])
            mask = np.isin(dayarr, sel_days)
            if not mask.any(): continue
            v = []
            ok = True
            for b in range(NB):
                mm = mask & (bb == b)
                if mm.sum() < 10: ok = False; break
                v.append(float(np.nanmean(dd[mm])))
            if not ok: continue
            r = spearman(np.arange(NB, dtype=float), np.array(v))
            if r is not None: draws.append(r)
        draws = np.array(draws)
        if len(draws) > 100:
            lo, hi = float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))
        rec["bootstrap"] = {"B": B, "rng": list(RNG), "block_days": BLOCK_DAYS, "draws_used": int(len(draws)),
                            "ci95": [lo, hi], "excludes_zero": bool(lo is not None and lo > 0)}
    if len(eff) < NB:
        verdict = "UNDECIDED"
    else:
        verdict = "SUPPORTED" if (rho is not None and rho > 0 and lo is not None and lo > 0) else "REFUTED"
    rec["criterion"] = {"effective_bins": eff, "bps_per_anchor_in_order": vals, "spearman": rho,
                        "ci95_lower": lo, "cond_rho_gt_0": bool(rho is not None and rho > 0),
                        "cond_ci_excludes_zero": bool(lo is not None and lo > 0), "VERDICT": verdict,
                        "frozen_in": "PREREG 54748c683 §3"}
    rec["VERDICT"] = verdict
    # ---- §5 separability ----
    terc = np.where(seat <= Q33, 0, np.where(seat <= Q67, 1, 2))
    rho_seat = spearman(fF[pop], terc[pop].astype(float))
    ct = {b: {int(t): int(((binid == b) & (terc == t) & pop).sum()) for t in (0, 1, 2)} for b in range(NB)}
    strat = {}
    for t in (0, 1, 2):
        strat[t] = {b: {"n": int((pop & (terc == t) & (binid == b)).sum()),
                        "bps_per_anchor": float(np.nanmean(d[pop & (terc == t) & (binid == b)]))}
                    for b in range(NB) if int((pop & (terc == t) & (binid == b)).sum()) >= MINCELL}
    rec["separability"] = {"spearman_frac_vs_seat_tercile": rho_seat, "contingency": ct, "stratified": strat}
    # ---- zero control relation: same intensity binned by the CONTROL arm's frac ----
    ca = [float(np.percentile(fA[pop], q)) for q in (20, 40, 60, 80)]
    bA = np.digitize(fA, ca, right=True)
    rowsA = {b: {"n": int((pop & (bA == b)).sum()),
                 "bps_per_anchor": float(np.nanmean(d[pop & (bA == b)])) if (pop & (bA == b)).any() else None}
             for b in range(NB)}
    effA = [b for b in range(NB) if rowsA[b]["n"] >= MINN]
    rec["zero_control"]["binned_by_NEWS_frac"] = {"cuts": ca, "rows": rowsA,
        "spearman": spearman(np.array(effA, float), np.array([rowsA[b]["bps_per_anchor"] for b in effA], float)) if len(effA) >= 2 else None,
        "note": "the mechanism is about the MONTHLY arm's diluted seat memory; binning by the ANNUAL arm's own frac should NOT show it"}
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    print("FA_FRAC VERDICT=%s bins_n=%s bps_per_anchor=%s spearman=%s ci95=[%s, %s] | NEWS_frac mean=%.4f share>=0.5=%.3f | "
          "FRESH_frac range=[%.4f, %.4f] | excluded=%d closes=%s | spearman_frac_vs_seat=%s | zero_control_spearman=%s | receipt=%s"
          % (verdict, [rows[b]["n_anchors"] for b in range(NB)], [round(v, 4) for v in vals],
             ("%.4f" % rho) if rho is not None else "None", ("%.4f" % lo) if lo is not None else "None",
             ("%.4f" % hi) if hi is not None else "None", zc["NEWS_frac_mean"], zc["NEWS_share_ge_0.5"],
             zc["FRESH_frac_min"], zc["FRESH_frac_max"], excluded, closes,
             ("%.4f" % rho_seat) if rho_seat is not None else "None",
             ("%.4f" % rec["zero_control"]["binned_by_NEWS_frac"]["spearman"]) if rec["zero_control"]["binned_by_NEWS_frac"]["spearman"] is not None else "None",
             sha(OUT)), flush=True)

if __name__ == "__main__":
    main()
    assert os.path.exists(OUT), f"device finished without writing {OUT}"
