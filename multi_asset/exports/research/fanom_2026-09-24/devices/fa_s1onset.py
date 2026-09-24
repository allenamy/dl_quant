"""fa_s1onset.py — PREREG docs/PREREG_fresh_rootcause_B_onset_2026-09-24.md (3ce252cc7). Read-only, NO engine."""
import os, sys, json, time, hashlib, calendar
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x
OUT = sys.argv[2]
F = "/dev/shm/fresh_2026-09-23"; N = "/dev/shm/news_2026-09-23"; R = "/dev/shm/fanom_2026-09-24/receipts"
Q33, Q67 = 0.5725596881282329, 0.7810047984528542
B = 10000; RNG = (20260923, 1); BLOCK_DAYS = 30; DAY = 86400; MINB = 30
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def q(v, m):
    vv = v[m]; vv = vv[np.isfinite(vv)]
    return {"median": float(np.median(vv)), "q25": float(np.percentile(vv, 25)), "q75": float(np.percentile(vv, 75)), "n": int(len(vv))} if len(vv) else None
def hold_age(pub):
    age = np.zeros(len(pub), np.int64); last = -1
    for i in range(len(pub)):
        if pub[i]: last = i; age[i] = 0
        else: age[i] = (i - last) if last >= 0 else -1
    return age
def last_pub_idx(pub):
    out = np.full(len(pub), -1, np.int64); last = -1
    for i in range(len(pub)):
        if pub[i]: last = i
        out[i] = last
    return out
def boot_diff(a, b, da, db, rs):
    ud = np.unique(np.concatenate([da, db])); blk = BLOCK_DAYS
    st = np.arange(max(1, len(ud) - blk + 1)); nb = int(np.ceil(len(ud) / blk)); o = []
    for _ in range(B):
        sel = np.concatenate([ud[s:s + blk] for s in rs.choice(st, size=nb, replace=True)])
        x = a[np.isin(da, sel)]; y = b[np.isin(db, sel)]
        if len(x) < 5 or len(y) < 5: continue
        o.append(float(np.nanmean(x) - np.nanmean(y)))
    o = np.array(o)
    return ([float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))], int(len(o))) if len(o) > 100 else ([None, None], int(len(o)))
def spear(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    ra = np.argsort(np.argsort(a[ok])).astype(float); rb = np.argsort(np.argsort(b[ok])).astype(float)
    if ra.std() == 0 or rb.std() == 0: return np.nan
    return float(np.corrcoef(ra, rb)[0, 1])

def main():
    rec = {"device": "fa_s1onset.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "prereg": {"path": "docs/PREREG_fresh_rootcause_B_onset_2026-09-24.md", "commit": "3ce252cc7"},
           "S1": {}, "onset": {}}
    SER = {"s42": f"{R}/FA_ANCHOR_SERIES.npz", "s2027": f"{R}/FA_ANCHOR_SERIES_s2027.npz"}
    # ---- S1: seat-tercile loss shares, s2027 (and s42 restated for comparison) ----
    for seed, p in SER.items():
        S = np.load(p); ax = S["anchors"].astype(np.int64); d = S["price_diff_D_minus_A_bps"]
        seat = S["seat_king_FRESH"].astype(np.float64); pre = S["in_pre2026"].astype(bool)
        terc = np.where(seat <= Q33, 0, np.where(seat <= Q67, 1, 2))
        den = float(np.nansum(d[pre])); rows = {}; tot = 0.0; n = 0
        for t, lab in ((0, "low"), (1, "mid"), (2, "high")):
            m = pre & (terc == t); s = float(np.nansum(d[m])); tot += s; n += int(m.sum())
            rows[lab] = {"n_anchors": int(m.sum()), "sum_bps": s,
                         "bps_per_anchor": float(np.nanmean(d[m])), "share": (s / den if den else None)}
        closes = abs(tot - den) <= 1e-9 * max(1.0, abs(den)) and n == int(pre.sum())
        assert closes, f"S1 {seed} does not close"
        rec["S1"][seed] = {"denominator_bps": den, "rows": rows, "CLOSES": bool(closes), "high_share": rows["high"]["share"]}
    hs = rec["S1"]["s2027"]["high_share"]
    rec["S1"]["B2_decision"] = {"rule": "prereg §1: high-seat share >= 0.50 keeps B2, else B2 and B6 are both dropped",
                                "s2027_high_share": hs, "s42_high_share": rec["S1"]["s42"]["high_share"],
                                "KEEP_B2": bool(hs >= 0.50)}
    # ---- onset anatomy ----
    for seed in ("s42", "s2027"):
        sub = seed[1:]
        S = np.load(SER[seed]); ax = S["anchors"].astype(np.int64); d = S["price_diff_D_minus_A_bps"]; pre = S["in_pre2026"].astype(bool)
        days = ax // DAY
        out = {}
        CF = np.load(f"{F}/work/combo_s{sub}/scaled_diagnostic.npz", allow_pickle=True)
        CN = np.load(f"{N}/work/combo_s{sub}/scaled_diagnostic.npz", allow_pickle=True)
        ce = CF["E_ts"].astype(np.int64); cpos = {int(t): i for i, t in enumerate(ce)}
        ci = np.array([cpos.get(int(t), -1) for t in ax]); cok = ci >= 0
        for arm, C in (("FRESH", CF), ("NEWS", CN)):
            pub = np.asarray(C["trade_mask"]).astype(bool)
            age_c = hold_age(pub); lp_c = last_pub_idx(pub); raw = C["raw"]
            dis_c = np.full(len(ce), np.nan)
            for j in range(len(ce)):
                if age_c[j] >= 1 and lp_c[j] >= 0:
                    dis_c[j] = spear(raw[lp_c[j]], raw[j])
            age = np.full(len(ax), -1, np.int64); dis = np.full(len(ax), np.nan)
            age[cok] = age_c[ci[cok]]; dis[cok] = dis_c[ci[cok]]
            onset = pre & cok & (age >= 1) & (age <= 2); later = pre & cok & (age >= 3)
            out[arm] = {"disagreement_onset": q(dis, onset), "disagreement_later": q(dis, later),
                        "n_onset": int(onset.sum()), "n_later": int(later.sum())}
            if arm == "FRESH":
                fo = onset; fdis = dis
        # long/short split of D-A on FRESH's onset anchors
        rawF = CF["raw"]; rprev = np.zeros_like(rawF)
        pubF = np.asarray(CF["trade_mask"]).astype(bool); lpF = last_pub_idx(pubF)
        tot = float(np.nansum(d[fo]))
        # disagreement terciles on FRESH onset anchors
        dv = fdis[fo]; ok = np.isfinite(dv)
        tinfo = {"n_onset": int(fo.sum()), "n_with_disagreement": int(ok.sum()), "total_bps": tot}
        if ok.sum() >= 3 * MINB:
            c1, c2 = np.percentile(dv[ok], [33.333, 66.667])
            idx = np.flatnonzero(fo)
            grp = {"low": idx[np.isfinite(fdis[idx]) & (fdis[idx] <= c1)],
                   "mid": idx[np.isfinite(fdis[idx]) & (fdis[idx] > c1) & (fdis[idx] <= c2)],
                   "high": idx[np.isfinite(fdis[idx]) & (fdis[idx] > c2)]}
            rows = {}; s_tot = 0.0
            for k, ii in grp.items():
                s = float(np.nansum(d[ii])); s_tot += s
                rows[k] = {"n": int(len(ii)), "sum_bps": s, "bps_per_anchor": float(np.nanmean(d[ii])) if len(ii) else None,
                           "share_of_onset": (s / tot if tot else None)}
            ci_d, nd = boot_diff(d[grp["low"]], d[grp["high"]], days[grp["low"]], days[grp["high"]], np.random.default_rng(RNG))
            pt = (rows["low"]["bps_per_anchor"] - rows["high"]["bps_per_anchor"]) if rows["low"]["bps_per_anchor"] is not None else None
            tinfo.update({"cuts": [float(c1), float(c2)], "rows": rows, "low_minus_high_point": pt,
                          "low_minus_high_ci95": ci_d, "boot_draws": nd,
                          "seed_supported": bool(pt is not None and pt < 0 and ci_d[1] is not None and ci_d[1] < 0)})
        else:
            tinfo["UNAVAILABLE"] = f"fewer than {3*MINB} onset anchors with a defined disagreement; terciles not formed"
            tinfo["seed_supported"] = False
        out["FRESH_onset_by_disagreement"] = tinfo
        rec["onset"][seed] = out
    a = rec["onset"]["s42"]["FRESH_onset_by_disagreement"]; b = rec["onset"]["s2027"]["FRESH_onset_by_disagreement"]
    if a.get("seed_supported") and b.get("seed_supported"): v = "SUPPORTED"
    elif (a.get("low_minus_high_point") or 0) > 0 or (b.get("low_minus_high_point") or 0) > 0: v = "REFUTED"
    else: v = "UNDECIDED"
    rec["onset_VERDICT"] = v
    rec["onset_seed_flip"] = bool(a.get("seed_supported") != b.get("seed_supported"))
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    print("FA_S1 s2027 high_share=%.4f (s42 %.4f) KEEP_B2=%s | shares s2027=%s"
          % (hs, rec["S1"]["s42"]["high_share"], rec["S1"]["B2_decision"]["KEEP_B2"],
             {k: round(v["share"], 4) for k, v in rec["S1"]["s2027"]["rows"].items()}), flush=True)
    print("FA_ONSET VERDICT=%s seed_flip=%s" % (v, rec["onset_seed_flip"]), flush=True)
    for s in ("s42", "s2027"):
        o = rec["onset"][s]; t = o["FRESH_onset_by_disagreement"]
        print("  %-6s disagree med FRESH onset=%s later=%s | NEWS onset=%s later=%s | n_onset=%d"
              % (s, o["FRESH"]["disagreement_onset"]["median"] if o["FRESH"]["disagreement_onset"] else None,
                 o["FRESH"]["disagreement_later"]["median"] if o["FRESH"]["disagreement_later"] else None,
                 o["NEWS"]["disagreement_onset"]["median"] if o["NEWS"]["disagreement_onset"] else None,
                 o["NEWS"]["disagreement_later"]["median"] if o["NEWS"]["disagreement_later"] else None, t["n_onset"]), flush=True)
        if "rows" in t:
            print("         terciles=%s low-high=%s ci95=%s supported=%s"
                  % ({k: (v["n"], round(v["bps_per_anchor"], 4)) for k, v in t["rows"].items()},
                     ("%+.4f" % t["low_minus_high_point"]), [round(c, 3) if c is not None else None for c in t["low_minus_high_ci95"]], t["seed_supported"]), flush=True)
        else:
            print("         %s" % t.get("UNAVAILABLE"), flush=True)

if __name__ == "__main__":
    main()
    assert os.path.exists(OUT), f"device finished without writing {OUT}"
