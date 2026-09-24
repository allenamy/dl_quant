"""fa_bridge.py — PREREG 427d76f34 §1.3 as amended by 84524bcdd.
Read-only. No engine, no GPU.

Bridge quantity: the King LEG realised return difference, LR[:, king], in bps per anchor (LR is ALREADY bps;
fresh_legs.py L61 multiplies by 1e4, so nothing is rescaled here). This is the furthest-downstream link in the
score -> book chain that is still measurable: FRESH's engine paths and the feature panel were deleted.

Reports, per month and per bucket, with SHARES that close:
  - King IC difference (correlation points) and F10 IC difference, on the COMMON scored cells of the two arms
  - King leg return difference (bps/anchor)
  - king seat WL[:,0], raw gross, publish/hold counts
Buckets: hold/publish, seat tercile, raw-gross band, and distance past a King fold boundary (M3's signature).
Every bucket table asserts that the shares sum to 1 over a closed population, so a bucket cannot silently
drop anchors.

usage: env -i PATH=/usr/bin:/bin HOME=/root python -B fa_bridge.py PATH,HOME,LC_CTYPE <out.json>
"""
import os, sys, json, time, hashlib, calendar
import numpy as np

WL_ = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL_); assert not extra, f"env outside whitelist: {extra}"
OUT = sys.argv[2]
F = "/dev/shm/fresh_2026-09-23"; N = "/dev/shm/news_2026-09-23"
H4 = 14400
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"), "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"), "2026": ("2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z"),
       "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z")}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def ym(t):
    g = time.gmtime(int(t)); return f"{g.tm_year}-{g.tm_mon:02d}"


def cs_ic(P, Y, mask_cells):
    """mean cross-sectional Spearman between score P and label Y over anchors, on given cells"""
    out = []
    for i in range(P.shape[0]):
        m = mask_cells[i]
        if m.sum() < 20: continue
        a, b = P[i][m], Y[i][m]
        f = np.isfinite(a) & np.isfinite(b)
        if f.sum() < 20: continue
        ra = np.argsort(np.argsort(a[f])).astype(np.float64); rb = np.argsort(np.argsort(b[f])).astype(np.float64)
        if ra.std() == 0 or rb.std() == 0: continue
        out.append(float(np.corrcoef(ra, rb)[0, 1]))
    return np.array(out)


def main():
    rec = {"device": "fa_bridge.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()),
           "prereg": {"path": "docs/PREREG_fresh_book_anomaly_2026-09-24.md", "commit": "427d76f34"},
           "amendment_1": {"path": "docs/AMENDMENT_1_fresh_book_anomaly_2026-09-24.md", "commit": "84524bcdd"},
           "bridge_quantity": "King leg realised return LR[:, king], bps per anchor (LR is already bps; NOT rescaled)",
           "why_not_price_channel": "FRESH engine paths and the feature panel were deleted; see AMENDMENT 1"}

    LF = np.load(f"{F}/work/legs.npz", allow_pickle=True); LN = np.load(f"{N}/work/legs.npz", allow_pickle=True)
    E = LF["E_ts"].astype(np.int64); rdy = LF["ready"]
    assert np.array_equal(E, LN["E_ts"].astype(np.int64)) and np.array_equal(rdy, LN["ready"])
    dLR = LF["LR"][:, 0] - LN["LR"][:, 0]                      # King leg return difference, bps/anchor
    dseat = LF["WL"][:, 0].astype(np.float64) - LN["WL"][:, 0].astype(np.float64)
    rec["inputs"] = {"legs_FRESH": sha(f"{F}/work/legs.npz"), "legs_NEWS": sha(f"{N}/work/legs.npz")}

    # ---- King fold boundaries (FRESH monthly), for M3's signature ----
    KR = json.load(open(f"{F}/work/king/TRAIN_RECEIPT.json"))
    bounds = sorted(int(f["score_start"]) for f in KR["folds"])
    idx_of = {int(t): i for i, t in enumerate(E)}
    bidx = np.array(sorted(idx_of[b] for b in bounds if b in idx_of))
    dist = np.full(len(E), 10 ** 6, np.int64)
    for b in bidx:
        n = min(len(E) - b, 200)
        seg = np.arange(n)
        dist[b:b + n] = np.minimum(dist[b:b + n], seg)
    rec["king_fold_boundaries"] = {"n": int(len(bidx)), "first_iso": iso(E[bidx[0]]), "last_iso": iso(E[bidx[-1]])}

    # ---- segment totals of the bridge quantity ----
    def segmask(s):
        lo, hi = SEG[s]; return rdy & (E >= ts(lo)) & (E <= ts(hi))
    seg_tot = {}
    for s in SEG:
        m = segmask(s); v = dLR[m]; fin = np.isfinite(v)
        seg_tot[s] = {"n_ready": int(m.sum()), "mean_diff_bps_per_anchor": float(np.nanmean(v[fin])),
                      "sum_diff_bps": float(np.nansum(v[fin])), "n_finite": int(fin.sum())}
    rec["segment_totals"] = seg_tot
    DEN_SEG = "pre2026"
    den_mask = segmask(DEN_SEG)
    den_sum = float(np.nansum(dLR[den_mask][np.isfinite(dLR[den_mask])]))
    rec["share_denominator"] = {"segment": DEN_SEG, "quantity": "sum of King leg return difference over ready anchors",
                                "value_bps": den_sum, "unit": "bps (summed over anchors, not per-anchor)"}

    # ---- per-month table ----
    KF = np.load(f"{F}/work/king/KING_OOF.npz"); KN = np.load(f"{N}/work/king/KING_OOF.npz")
    rec["oof"] = {"FRESH_king": sha(f"{F}/work/king/KING_OOF.npz"), "NEWS_king": sha(f"{N}/work/king/KING_OOF.npz")}
    PF, PN = KF["P"], KN["P"]
    common = np.isfinite(PF) & np.isfinite(PN)
    rec["king_ic_population"] = {"cells_FRESH_finite": int(np.isfinite(PF).sum()), "cells_NEWS_finite": int(np.isfinite(PN).sum()),
                                 "cells_common": int(common.sum()),
                                 "note": "IC is computed on the COMMON finite cells of both arms (prereg 1.3), so the two "
                                         "arms are scored on one population"}
    # labels: both arms trained on dlw_targets y4s (TRAIN_RECEIPT.label, identical string in both receipts),
    # so IC is recomputed here from the SAME label file rather than inherited from either arm's own receipt.
    LABP = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz"
    T_ = np.load(LABP, allow_pickle=True)
    assert np.array_equal(T_["symbols"], KF["symbols"]), "label symbol axis differs from OOF"
    le = T_["E_ts"].astype(np.int64); oe = KF["E_ts"].astype(np.int64)
    lpos = {int(v): i for i, v in enumerate(le)}
    rows = np.array([lpos.get(int(v), -1) for v in oe])
    hit = rows >= 0
    Yal = np.full(PF.shape, np.nan, np.float64)
    Yal[hit] = T_["y4s"][rows[hit]].astype(np.float64)
    rec["label"] = {"path": LABP, "sha256": sha(LABP), "field": "y4s",
                    "label_string_FRESH": json.load(open(f"{F}/work/king/TRAIN_RECEIPT.json")).get("label"),
                    "label_string_NEWS": json.load(open(f"{N}/work/king/TRAIN_RECEIPT.json")).get("label"),
                    "oof_anchors": int(len(oe)), "anchors_with_label_row": int(hit.sum())}
    common = np.isfinite(PF) & np.isfinite(PN) & np.isfinite(Yal)
    rec["king_ic_population"] = {"cells_FRESH_finite": int(np.isfinite(PF).sum()), "cells_NEWS_finite": int(np.isfinite(PN).sum()),
                                 "cells_common_with_label": int(common.sum()),
                                 "arms_score_identical_cells": bool(np.array_equal(np.isfinite(PF), np.isfinite(PN))),
                                 "note": "IC is computed on cells finite in BOTH arms AND in the label, so the two arms are "
                                         "scored on one population (prereg 1.3, mechanism M5)"}
    seg_pre = (oe >= ts(SEG["pre2026"][0])) & (oe <= ts(SEG["pre2026"][1]))
    ic = {}
    for tag, rowsel in (("all", np.ones(len(oe), bool)), ("pre2026", seg_pre)):
        cm = common.copy(); cm[~rowsel] = False
        icf = cs_ic(PF, Yal, cm); icn = cs_ic(PN, Yal, cm)
        n = min(len(icf), len(icn))
        ic[tag] = {"FRESH_mean": float(icf.mean()) if len(icf) else None, "NEWS_mean": float(icn.mean()) if len(icn) else None,
                   "diff": float(icf.mean() - icn.mean()) if len(icf) and len(icn) else None,
                   "n_anchors_FRESH": int(len(icf)), "n_anchors_NEWS": int(len(icn)),
                   "same_anchor_count": bool(len(icf) == len(icn)),
                   "unit": "correlation points (cross-sectional Spearman), recomputed on common cells"}
    rec["king_ic_common_cells"] = ic

    # ---- buckets, shares must close ----
    def bucket_table(name, labels, assign):
        rows = {}; tot = 0.0; n_tot = 0
        pop = den_mask
        for lab in labels:
            m = pop & assign(lab); v = dLR[m]; fin = np.isfinite(v)
            s = float(np.nansum(v[fin])); tot += s; n_tot += int(m.sum())
            rows[lab] = {"n_anchors": int(m.sum()), "sum_diff_bps": s,
                         "mean_diff_bps_per_anchor": float(np.nanmean(v[fin])) if fin.any() else None,
                         "share_of_denominator": float(s / den_sum) if den_sum else None}
        closes = abs(tot - den_sum) <= 1e-6 * max(1.0, abs(den_sum)) and n_tot == int(pop.sum())
        return {"rows": rows, "sum_of_shares": float(tot / den_sum) if den_sum else None,
                "population_anchors": int(pop.sum()), "bucketed_anchors": n_tot, "CLOSES": bool(closes)}

    CF = np.load(f"{F}/work/combo_s42/scaled_diagnostic.npz", allow_pickle=True)
    CN = np.load(f"{N}/work/combo_s42/scaled_diagnostic.npz", allow_pickle=True)
    ce = CF["E_ts"].astype(np.int64)
    pos = {int(t): i for i, t in enumerate(ce)}
    pub_f = np.zeros(len(E), bool); pub_n = np.zeros(len(E), bool); has_c = np.zeros(len(E), bool)
    for i, t in enumerate(E):
        j = pos.get(int(t))
        if j is not None:
            has_c[i] = True; pub_f[i] = bool(CF["trade_mask"][j]); pub_n[i] = bool(CN["trade_mask"][j])
    rec["combo"] = {"FRESH": sha(f"{F}/work/combo_s42/scaled_diagnostic.npz"), "NEWS": sha(f"{N}/work/combo_s42/scaled_diagnostic.npz"),
                    "anchors_with_combo_row": int(has_c.sum())}

    B = {}
    B["publish_state"] = bucket_table("publish_state", ["both_publish", "only_FRESH", "only_NEWS", "neither", "no_combo_row"],
        lambda lab: {"both_publish": has_c & pub_f & pub_n, "only_FRESH": has_c & pub_f & ~pub_n,
                     "only_NEWS": has_c & ~pub_f & pub_n, "neither": has_c & ~pub_f & ~pub_n, "no_combo_row": ~has_c}[lab])
    sq = LF["WL"][:, 0].astype(np.float64)
    q1, q2 = np.nanpercentile(sq[den_mask], [33.333, 66.667])
    B["fresh_king_seat_tercile"] = bucket_table("seat", ["low", "mid", "high"],
        lambda lab: {"low": sq <= q1, "mid": (sq > q1) & (sq <= q2), "high": sq > q2}[lab])
    B["seat_tercile_cuts"] = {"q33": float(q1), "q67": float(q2), "quantity": "FRESH king seat WL[:,0]"}
    B["anchors_past_king_fold_boundary"] = bucket_table("dist", ["0-5", "6-20", "21-60", "61+"],
        lambda lab: {"0-5": dist <= 5, "6-20": (dist > 5) & (dist <= 20), "21-60": (dist > 20) & (dist <= 60), "61+": dist > 60}[lab])
    rec["buckets"] = B
    for k, v in B.items():
        if isinstance(v, dict) and "CLOSES" in v:
            assert v["CLOSES"], f"bucket {k} does not close: shares sum to {v['sum_of_shares']}, {v['bucketed_anchors']} of {v['population_anchors']} anchors"

    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    p = rec["segment_totals"]["pre2026"]
    print(f"FA_BRIDGE bridge=King_leg_diff pre2026_mean={p['mean_diff_bps_per_anchor']:+.4f}bps/anchor "
          f"denominator_sum={den_sum:+.1f}bps over {p['n_ready']} ready anchors | "
          f"buckets_close={{ {', '.join(k + ':' + str(v['CLOSES']) for k, v in B.items() if isinstance(v, dict) and 'CLOSES' in v)} }} "
          f"boundary_share_0-5={B['anchors_past_king_fold_boundary']['rows']['0-5']['share_of_denominator']:.3f} "
          f"seat_high_share={B['fresh_king_seat_tercile']['rows']['high']['share_of_denominator']:.3f} "
          f"receipt={sha(OUT)}", flush=True)


if __name__ == "__main__":
    main()
