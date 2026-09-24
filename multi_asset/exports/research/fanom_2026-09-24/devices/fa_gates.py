"""fa_gates.py — PREREG docs/PREREG_fresh_book_anomaly_2026-09-24.md (427d76f34) phase 1, items 1.1 and 1.2.
Read-only. No engine, no GPU, no disk beyond one json.

1.1 FOLD-MAPPING AUDIT, re-derived from the receipts rather than trusting the assertions the trainers made:
    - every fold's max_train_label_end <= score_start - embargo*4h
    - every fold trained only on data before the month it scores (max_train_label_end < score_start)
    - the score windows tile the axis with no gap and no overlap, and each fold's name matches the month it scores
    - F10: where mu/sd come from, read out of the TRAINER SOURCE (compiled, not paraphrased), plus the
      train_frac effect (max_train_label_end vs cutoff)
    - label look-ahead span vs the embargo
    Run over BOTH arms with the same code, so the comparison is instrument-free.

1.2 LEGS ZERO-CONTROL + LEG LEDGER:
    legs.npz depends on King only. So Z24 / ZFD / RN8 / QV / WL / ready / E_ts / symbols MUST be bitwise
    identical across the two arms. If they are not, legs is not King-only and the phase-2 design is void:
    the device says STOP rather than continuing. KZ and LR[:, king] are expected to differ.

usage: env -i PATH=/usr/bin:/bin HOME=/root python -B fa_gates.py PATH,HOME,LC_CTYPE <out.json>
"""
import os, sys, json, time, ast, hashlib, calendar, inspect
import numpy as np

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
OUT = sys.argv[2]
ARM = {"FRESH": "/dev/shm/fresh_2026-09-23", "NEWS": "/dev/shm/news_2026-09-23"}
H4 = 14400
LABEL_SPAN_ANCHORS = 1     # y4 = 4h forward return = exactly one anchor of look-ahead


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def month_of(t):
    g = time.gmtime(int(t)); return f"{g.tm_year}{g.tm_mon:02d}"


def audit_king(root, arm):
    R = json.load(open(f"{root}/work/king/TRAIN_RECEIPT.json"))
    folds = R["folds"]; rows = []
    for f in folds:
        emb = int(f["embargo_anchors"]); ss = int(f["score_start"]); mtle = int(f["max_train_label_end"])
        need = ss - emb * H4
        rows.append({"fold": f["fold"], "score_start": ss, "score_start_iso": iso(ss), "score_end": int(f["score_end"]),
                     "max_train_label_end": mtle, "max_train_label_end_iso": iso(mtle), "embargo_anchors": emb,
                     "required_max_train_label_end": need, "slack_anchors": (need - mtle) / H4,
                     "embargo_respected": bool(mtle <= need),
                     "trained_only_before_scored_window": bool(mtle < ss),
                     "fold_name_matches_scored_month": bool(f["fold"].startswith(month_of(ss)) or not f["fold"][:6].isdigit()),
                     "train_pairs": f.get("train_pairs"), "model_sha256": f.get("model_sha256")})
    srt = sorted(rows, key=lambda r: r["score_start"])
    # score_end is the LAST scored anchor of the fold, so contiguity means next.score_start == prev.score_end + one anchor.
    # (The earlier form compared against score_end itself and therefore fired on every boundary in both arms — a check
    #  that fails 100% of the time is the check, not the data.)
    gaps = [{"after": srt[i]["fold"], "before": srt[i + 1]["fold"],
             "gap_anchors": (srt[i + 1]["score_start"] - srt[i]["score_end"]) / H4 - 1}
            for i in range(len(srt) - 1) if srt[i + 1]["score_start"] != srt[i]["score_end"] + H4]
    return {"arm": arm, "receipt": f"{root}/work/king/TRAIN_RECEIPT.json", "receipt_sha256": sha(f"{root}/work/king/TRAIN_RECEIPT.json"),
            "n_folds": len(rows), "embargo_values": sorted({r["embargo_anchors"] for r in rows}),
            "violations_embargo": [r["fold"] for r in rows if not r["embargo_respected"]],
            "violations_future_train": [r["fold"] for r in rows if not r["trained_only_before_scored_window"]],
            "min_slack_anchors": min(r["slack_anchors"] for r in rows),
            "window_gaps_or_overlaps": gaps, "folds": rows}


def audit_f10(root, arm, seed):
    base = f"{root}/work/f10_{seed}"
    R = json.load(open(f"{base}/TRAIN_RECEIPT.json"))
    ds = sorted(d for d in os.listdir(base) if d[0].isdigit())
    rows = []
    for d in ds:
        A = json.load(open(f"{base}/{d}/ADMISSION.json"))
        emb = int(A.get("embargo_anchors", 0)); ts_ = int(A["test_start"]); mtle = int(A["max_train_label_end"]); cut = int(A["cutoff"])
        need = ts_ - emb * H4 if emb else None
        rows.append({"fold": A["fold"], "test_start": ts_, "test_start_iso": iso(ts_), "cutoff": cut, "cutoff_iso": iso(cut),
                     "max_train_label_end": mtle, "max_train_label_end_iso": iso(mtle),
                     "embargo_anchors_declared": emb or None,
                     "gap_test_start_minus_mtle_anchors": (ts_ - mtle) / H4,
                     "gap_test_start_minus_cutoff_anchors": (ts_ - cut) / H4,
                     "train_frac": A.get("train_frac"),
                     "mtle_equals_cutoff": bool(mtle == cut),
                     "gradient_stops_before_cutoff_anchors": (cut - mtle) / H4,
                     "embargo_respected": bool(mtle <= need) if need is not None else None,
                     "accepted_windows": A.get("accepted_windows"), "rejected": A.get("rejected"), "train_anchors": A.get("train_anchors")})
    srt = sorted(rows, key=lambda r: r["test_start"])
    return {"arm": arm, "seed": seed, "n_folds": len(rows), "receipt_sha256": sha(f"{base}/TRAIN_RECEIPT.json"),
            "declared_folds": R.get("folds"),
            "min_gap_test_start_minus_mtle_anchors": min(r["gap_test_start_minus_mtle_anchors"] for r in rows),
            "any_mtle_after_test_start": [r["fold"] for r in rows if r["max_train_label_end"] >= r["test_start"]],
            "folds_where_gradient_stops_before_cutoff": [{"fold": r["fold"], "anchors": r["gradient_stops_before_cutoff_anchors"]}
                                                         for r in srt if r["gradient_stops_before_cutoff_anchors"] > 0],
            "folds": srt}


def mu_sd_provenance(dev_path):
    """read out of the TRAINER SOURCE where mu/sd are computed from -- compiled from the file, not paraphrased,
    so this cannot drift from the code that actually produced the models."""
    src = open(dev_path).read()
    tree = ast.parse(src)
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            tgt = ", ".join(t.id for t in n.targets if isinstance(t, ast.Name))
            if tgt and ("mu" in tgt.split(", ") or "sd" in tgt.split(", ")):
                hits.append({"line": n.lineno, "source": ast.get_source_segment(src, n)})
    return {"device": dev_path, "device_sha256": sha(dev_path), "mu_sd_assignments": hits}


def main():
    rec = {"device": "fa_gates.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()),
           "prereg": {"path": "docs/PREREG_fresh_book_anomaly_2026-09-24.md", "commit": "427d76f34"},
           "label_span_anchors": LABEL_SPAN_ANCHORS,
           "label_note": "y4 = 4h forward simple return = 1 anchor of look-ahead; an embargo of E anchors leaves E-1 anchors of true slack"}

    # ---- 1.1 fold mapping ----
    king = {a: audit_king(r, a) for a, r in ARM.items()}
    f10 = {a: {s: audit_f10(r, a, s) for s in ("s42", "s2027")} for a, r in ARM.items()}
    rec["king_audit"] = king
    rec["f10_audit"] = f10
    rec["mu_sd_provenance"] = {"FRESH": mu_sd_provenance("/dev/shm/fresh_2026-09-23/devices/fresh_train_f10.py")}
    viol = {"king": {a: {"embargo": king[a]["violations_embargo"], "future_train": king[a]["violations_future_train"],
                         "gaps": king[a]["window_gaps_or_overlaps"]} for a in ARM},
            "f10": {a: {s: f10[a][s]["any_mtle_after_test_start"] for s in ("s42", "s2027")} for a in ARM}}
    rec["violations"] = viol
    rec["FOLD_AUDIT_CLEAN"] = bool(
        all(not king[a]["violations_embargo"] and not king[a]["violations_future_train"] and not king[a]["window_gaps_or_overlaps"] for a in ARM)
        and all(not f10[a][s]["any_mtle_after_test_start"] for a in ARM for s in ("s42", "s2027")))

    # ---- 1.2 legs zero-control ----
    LF = np.load(f"{ARM['FRESH']}/work/legs.npz", allow_pickle=True)
    LN = np.load(f"{ARM['NEWS']}/work/legs.npz", allow_pickle=True)
    MUST_MATCH = ("E_ts", "symbols", "Z24", "ZFD", "RN8", "QV", "ready")
    MAY_DIFFER = ("KZ", "LR", "WL")   # WL = msharpe seats, computed from the leg-return history incl. the king leg
    LR_COLS = ("king", "rev24", "fund")          # fresh_legs.py L44/L62, read from source not inferred
    LR_MUST_MATCH_COLS = (1, 2)                  # rev24 and fund depend on no King input
    zc = {"legs_sha": {"FRESH": sha(f"{ARM['FRESH']}/work/legs.npz"), "NEWS": sha(f"{ARM['NEWS']}/work/legs.npz")}, "per_key": {}}
    for k in LF.files:
        a, b = LF[k], LN[k]
        same = bool(a.shape == b.shape and np.array_equal(a, b, equal_nan=True) if a.dtype.kind == "f" else a.shape == b.shape and np.array_equal(a, b))
        zc["per_key"][k] = {"shape": list(a.shape), "identical": same, "expected": "identical" if k in MUST_MATCH else "may differ"}
    # per-COLUMN zero control on LR: only the king column is allowed to differ
    zc["LR_per_column"] = {}
    for j, nm in enumerate(LR_COLS):
        a, b = LF["LR"][:, j], LN["LR"][:, j]
        zc["LR_per_column"][nm] = {"identical": bool(np.array_equal(a, b, equal_nan=True)),
                                   "expected": "identical" if j in LR_MUST_MATCH_COLS else "may differ"}
    zc["LR_zero_control_holds"] = bool(all(zc["LR_per_column"][LR_COLS[j]]["identical"] for j in LR_MUST_MATCH_COLS))
    # falsifiable timing test: WL is claimed to differ only BECAUSE LR's king column differs. If that claim is true,
    # WL cannot first differ strictly before LR's king column first differs. If it does, the claim is wrong.
    dk = np.flatnonzero(~np.isclose(LF["LR"][:, 0], LN["LR"][:, 0], equal_nan=True))
    dw = np.flatnonzero(~np.isclose(np.nan_to_num(LF["WL"], nan=-9e9), np.nan_to_num(LN["WL"], nan=-9e9)).all(axis=1) == False) \
        if False else np.flatnonzero((~np.isclose(LF["WL"], LN["WL"], equal_nan=True)).any(axis=1))
    first_lr = int(dk[0]) if len(dk) else None
    first_wl = int(dw[0]) if len(dw) else None
    zc["WL_explained_by_LR_king"] = {"first_anchor_index_LR_king_differs": first_lr,
                                     "first_anchor_index_WL_differs": first_wl,
                                     "WL_never_precedes_LR": bool(first_wl is None or (first_lr is not None and first_wl >= first_lr)),
                                     "test": "WL is computed from the leg-return history (fresh_legs.py L64-82), so if the only "
                                             "King dependence is via LR's king column then WL cannot first differ before LR does"}
    zc["zero_control_holds"] = bool(all(zc["per_key"][k]["identical"] for k in MUST_MATCH)
                                    and zc["LR_zero_control_holds"]
                                    and zc["WL_explained_by_LR_king"]["WL_never_precedes_LR"])
    zc["king_dependent_keys_differ_as_expected"] = bool(all(not zc["per_key"][k]["identical"] for k in MAY_DIFFER))
    zc["source_evidence"] = {"WL": "fresh_legs.py L64-82: w3 = msharpe over r = stack(LR[leg][-look:]) for (king, rev24, fund); WL[i] = w3",
                             "LR": "fresh_legs.py L44/L61-62: LR dict keyed (king, rev24, fund), LRm[i-1] = last of each"}
    zc["VERDICT"] = ("LEGS_IS_KING_ONLY" if zc["zero_control_holds"] and zc["king_dependent_keys_differ_as_expected"]
                     else "STOP: legs is NOT King-only, phase-2 swap design is void")
    rec["legs_zero_control"] = zc

    # ---- 1.2 leg ledger: does the higher-IC leg actually earn more at leg level ----
    if zc["zero_control_holds"]:
        E = LF["E_ts"].astype(np.int64); rdy = LF["ready"]
        SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"), "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
               "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"), "2026": ("2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z"),
               "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z")}
        def t(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
        led = {"unit": "bps per anchor -- LR is ALREADY in bps (fresh_legs.py L61 multiplies by 1e4), so this is the plain "
                       "mean of LR over the segment's ready anchors with NO further scaling",
               "LR_columns_note": "LR has 3 columns; column identity is taken from the legs device order (king, rev24, fund)",
               "segments": {}}
        names = ["king", "rev24", "fund"]
        for s, (lo, hi) in SEG.items():
            m = rdy & (E >= t(lo)) & (E <= t(hi))
            row = {"n_ready_anchors": int(m.sum())}
            for j, nm in enumerate(names):
                fv = LF["LR"][m, j]; nv = LN["LR"][m, j]
                fin = np.isfinite(fv) & np.isfinite(nv)
                row[nm] = {"FRESH_bps_per_anchor": float(np.nanmean(fv[fin])) if fin.any() else None,
                           "NEWS_bps_per_anchor": float(np.nanmean(nv[fin])) if fin.any() else None,
                           "diff_bps_per_anchor": float(np.nanmean(fv[fin]) - np.nanmean(nv[fin])) if fin.any() else None,
                           "n_finite_both": int(fin.sum()),
                           "bitwise_identical_on_segment": bool(np.array_equal(fv, nv, equal_nan=True))}
            led["segments"][s] = row
        rec["leg_ledger"] = led

    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    k = rec["king_audit"]; f = rec["f10_audit"]
    print(f"FA_GATES FOLD_AUDIT_CLEAN={rec['FOLD_AUDIT_CLEAN']} "
          f"king_folds={{FRESH:{k['FRESH']['n_folds']}(emb {k['FRESH']['embargo_values']}, min_slack {k['FRESH']['min_slack_anchors']:.1f}a), "
          f"NEWS:{k['NEWS']['n_folds']}(emb {k['NEWS']['embargo_values']}, min_slack {k['NEWS']['min_slack_anchors']:.1f}a)}} "
          f"f10_min_gap_anchors={{FRESH:{f['FRESH']['s42']['min_gap_test_start_minus_mtle_anchors']:.1f}, NEWS:{f['NEWS']['s42']['min_gap_test_start_minus_mtle_anchors']:.1f}}} "
          f"NEWS_folds_gradient_stops_early={len(f['NEWS']['s42']['folds_where_gradient_stops_before_cutoff'])}/{f['NEWS']['s42']['n_folds']} "
          f"FRESH_same={len(f['FRESH']['s42']['folds_where_gradient_stops_before_cutoff'])}/{f['FRESH']['s42']['n_folds']} "
          f"LEGS={rec['legs_zero_control']['VERDICT']} "
          f"LR_cols_identical={{rev24:{zc['LR_per_column']['rev24']['identical']}, fund:{zc['LR_per_column']['fund']['identical']}, king:{zc['LR_per_column']['king']['identical']}}} "
          f"WL_first_diff={zc['WL_explained_by_LR_king']['first_anchor_index_WL_differs']} LR_king_first_diff={zc['WL_explained_by_LR_king']['first_anchor_index_LR_king_differs']} "
          f"receipt={sha(OUT)}", flush=True)
    sys.exit(0 if rec["FOLD_AUDIT_CLEAN"] and zc["zero_control_holds"] else 3)


if __name__ == "__main__":
    main()
