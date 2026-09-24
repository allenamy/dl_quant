"""fa_c1.py — PREREG docs/PREREG_fresh_rootcause_C1_2026-09-24.md (619173e0f). Read-only, NO engine, NO GPU.
Both seeds. hold age == book age (prereg §1), computed once per arm.
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x
OUT = sys.argv[2]
F = "/dev/shm/fresh_2026-09-23"; N = "/dev/shm/news_2026-09-23"; R = "/dev/shm/fanom_2026-09-24/receipts"
LAB = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz"
PRE = ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"); Q33, Q67 = 0.5725596881282329, 0.7810047984528542
BINS = [(1, 2), (3, 6), (7, 20), (21, 10**9)]; BLAB = ["1-2", "3-6", "7-20", "21+"]
B = 10000; RNG = (20260923, 1); BLOCK_DAYS = 30; DAY = 86400
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def q(v, m):
    vv = v[m]; vv = vv[np.isfinite(vv)]
    return {"median": float(np.median(vv)), "q25": float(np.percentile(vv, 25)), "q75": float(np.percentile(vv, 75))} if len(vv) else None

def hold_age(pub):
    """anchors since this arm's last publish; 0 while publishing, >=1 while holding"""
    age = np.zeros(len(pub), np.int64); last = -1
    for i in range(len(pub)):
        if pub[i]: last = i; age[i] = 0
        else: age[i] = (i - last) if last >= 0 else -1
    return age

def boot_diff(x_long, x_short, days_long, days_short, rs):
    ud = np.unique(np.concatenate([days_long, days_short])); blk = BLOCK_DAYS
    starts = np.arange(max(1, len(ud) - blk + 1)); nb = int(np.ceil(len(ud) / blk)); out = []
    for _ in range(B):
        pick = rs.choice(starts, size=nb, replace=True)
        sel = np.concatenate([ud[s:s + blk] for s in pick])
        a = x_long[np.isin(days_long, sel)]; b = x_short[np.isin(days_short, sel)]
        if len(a) < 5 or len(b) < 5: continue
        out.append(float(np.nanmean(a) - np.nanmean(b)))
    o = np.array(out)
    return ([float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))], int(len(o))) if len(o) > 100 else ([None, None], int(len(o)))

def main():
    rec = {"device": "fa_c1.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "prereg": {"path": "docs/PREREG_fresh_rootcause_C1_2026-09-24.md", "commit": "619173e0f"},
           "note": "hold age and book age are the same quantity (prereg §1); computed once per arm",
           "proxy_calibration_from_A2": {"spearman_vs_engine": 0.6260, "magnitude_ratio_approx": 11,
                                         "use": "per-arm absolute intensity is DESCRIPTIVE only; the criterion uses exact D-A"},
           "seeds": {}}
    T = np.load(LAB, allow_pickle=True); te = T["E_ts"].astype(np.int64); y = T["y4s"]
    lpos = {int(v): i for i, v in enumerate(te)}
    for seed, serp in (("s42", f"{R}/FA_ANCHOR_SERIES.npz"), ("s2027", f"{R}/FA_ANCHOR_SERIES_s2027.npz")):
        S = np.load(serp); ax = S["anchors"].astype(np.int64); d = S["price_diff_D_minus_A_bps"]
        seat = S["seat_king_FRESH"].astype(np.float64); pre = S["in_pre2026"].astype(bool)
        sub = seed[1:]
        CF = np.load(f"{F}/work/combo_s{sub}/scaled_diagnostic.npz", allow_pickle=True)
        CN = np.load(f"{N}/work/combo_s{sub}/scaled_diagnostic.npz", allow_pickle=True)
        ce = CF["E_ts"].astype(np.int64); cpos = {int(t): i for i, t in enumerate(ce)}
        ci = np.array([cpos.get(int(t), -1) for t in ax]); cok = ci >= 0
        # hold age on the COMBO axis (contiguous), then mapped to the engine axis
        ageF_c = hold_age(np.asarray(CF["trade_mask"]).astype(bool))
        ageN_c = hold_age(np.asarray(CN["trade_mask"]).astype(bool))
        ageF = np.full(len(ax), -1, np.int64); ageN = np.full(len(ax), -1, np.int64)
        ageF[cok] = ageF_c[ci[cok]]; ageN[cok] = ageN_c[ci[cok]]
        terc = np.where(seat <= Q33, 0, np.where(seat <= Q67, 1, 2))
        g4 = pre & cok & (terc == 2) & (ageF >= 1) & (ageN >= 1)
        den = float(np.nansum(d[g4]))
        days = ax // DAY
        rows = {}; tot = 0.0; n = 0
        for (lo, hi), lab in zip(BINS, BLAB):
            m = g4 & (ageF >= lo) & (ageF <= hi); s = float(np.nansum(d[m])); tot += s; n += int(m.sum())
            rows[lab] = {"n_anchors": int(m.sum()), "sum_bps": s,
                         "bps_per_anchor": float(np.nanmean(d[m])) if m.any() else None,
                         "share_of_G4": (s / den if den else None)}
        closes = abs(tot - den) <= 1e-9 * max(1.0, abs(den)) and n == int(g4.sum())
        assert closes, f"{seed}: hold-age bins do not close ({tot} vs {den}, {n}/{int(g4.sum())})"
        vals = [rows[l]["bps_per_anchor"] for l in BLAB]
        mono = all(vals[i + 1] <= vals[i] for i in range(3) if vals[i] is not None and vals[i + 1] is not None)
        mlong = g4 & (ageF >= 21); mshort = g4 & (ageF >= 1) & (ageF <= 2)
        ci_d, nd = boot_diff(d[mlong], d[mshort], days[mlong], days[mshort], np.random.default_rng(RNG))
        point = (float(np.nanmean(d[mlong])) - float(np.nanmean(d[mshort]))) if (mlong.any() and mshort.any()) else None
        sup = bool(mono and point is not None and point < 0 and ci_d[1] is not None and ci_d[1] < 0)
        # ---- G4 book-age anatomy ----
        anat = {"book_age": {"FRESH": q(ageF.astype(float), g4), "NEWS": q(ageN.astype(float), g4)}}
        same = g4 & (ageF == ageN)
        anat["same_book_age"] = {"n_anchors": int(same.sum()),
                                 "bps_per_anchor": float(np.nanmean(d[same])) if same.any() else None,
                                 "share_of_G4": (float(np.nansum(d[same])) / den if den else None)}
        if same.any():
            ci_s, ns = boot_diff(d[same], np.zeros(1), days[same], np.array([days[same][0]]), np.random.default_rng(RNG))
            sm = d[same]; ud = np.unique(days[same]); rs2 = np.random.default_rng(RNG); dr = []
            for _ in range(B):
                pick = rs2.choice(np.arange(max(1, len(ud) - BLOCK_DAYS + 1)), size=int(np.ceil(len(ud) / BLOCK_DAYS)), replace=True)
                sel = np.concatenate([ud[s:s + BLOCK_DAYS] for s in pick]); mm = np.isin(days[same], sel)
                if mm.sum() >= 5: dr.append(float(np.nanmean(sm[mm])))
            dr = np.array(dr)
            anat["same_book_age"]["ci95"] = [float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))] if len(dr) > 100 else [None, None]
        anat["distributions_differ"] = bool(anat["book_age"]["FRESH"] and anat["book_age"]["NEWS"] and
                                            anat["book_age"]["FRESH"]["median"] != anat["book_age"]["NEWS"]["median"])
        rec["seeds"][seed] = {"G4_n": int(g4.sum()), "G4_sum_bps": den, "by_hold_age": rows, "CLOSES": bool(closes),
                              "monotone_nonincreasing": bool(mono), "long_minus_short_point": point,
                              "long_minus_short_ci95": ci_d, "boot_draws": nd, "seed_supported": sup, "G4_anatomy": anat}
    a, b = rec["seeds"]["s42"], rec["seeds"]["s2027"]
    if a["seed_supported"] and b["seed_supported"]: v = "SUPPORTED"
    elif (a["monotone_nonincreasing"] and (a["long_minus_short_point"] or 0) < 0) != (b["monotone_nonincreasing"] and (b["long_minus_short_point"] or 0) < 0): v = "UNDECIDED"
    elif not a["monotone_nonincreasing"] or not b["monotone_nonincreasing"]: v = "REFUTED"
    else: v = "UNDECIDED"
    flip = bool(a["seed_supported"] != b["seed_supported"])
    rec["VERDICT"] = v; rec["seed_flip"] = flip
    rec["criterion"] = {"frozen_in": "PREREG 619173e0f §4", "requires_both_seeds": True,
                        "note_if_flip": "another seed reversal" if flip else None}
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    print("FA_C1 VERDICT=%s seed_flip=%s" % (v, flip), flush=True)
    for s in ("s42", "s2027"):
        r = rec["seeds"][s]
        print("  %-6s G4_n=%-5d mono=%-5s long-short=%s ci95=%s supported=%s | %s"
              % (s, r["G4_n"], r["monotone_nonincreasing"],
                 ("%+.4f" % r["long_minus_short_point"]) if r["long_minus_short_point"] is not None else "None",
                 [round(c, 3) if c is not None else None for c in r["long_minus_short_ci95"]], r["seed_supported"],
                 {l: (r["by_hold_age"][l]["n_anchors"], round(r["by_hold_age"][l]["bps_per_anchor"], 4) if r["by_hold_age"][l]["bps_per_anchor"] is not None else None) for l in BLAB}), flush=True)
        an = r["G4_anatomy"]
        print("         book_age med F=%s N=%s differ=%s | same_age n=%d bps/anchor=%s ci95=%s"
              % (an["book_age"]["FRESH"]["median"] if an["book_age"]["FRESH"] else None,
                 an["book_age"]["NEWS"]["median"] if an["book_age"]["NEWS"] else None, an["distributions_differ"],
                 an["same_book_age"]["n_anchors"],
                 ("%+.4f" % an["same_book_age"]["bps_per_anchor"]) if an["same_book_age"]["bps_per_anchor"] is not None else None,
                 [round(c, 3) if c is not None else None for c in an["same_book_age"].get("ci95", [None, None])]), flush=True)

if __name__ == "__main__":
    main()
    assert os.path.exists(OUT), f"device finished without writing {OUT}"
