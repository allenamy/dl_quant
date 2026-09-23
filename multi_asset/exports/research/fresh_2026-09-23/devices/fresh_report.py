#!/usr/bin/env python3
"""fresh_report.py — the PREREG_fresh_models_newS_2026-09-23.md §3/§4 REPORT-ONLY items (no gate, no verdict):
  1. King score-layer IC by model age in months, both arms (curve + OLS slope with a 30-day block interval).
  2. F10 score-layer IC by model age in months, both arms (same).
  3. Share of anchors whose book target differs from NEW_S, and the L1 distribution of the difference (§4 delivery line).
  4. Chain turnover (target-level L1 turnover per year), both arms.
  5. Seat shares (king / rev24 / fund) per year, both arms.
  6. F10 per-fold admission windows and rejection ratio, both arms; King per-fold training-label cutoff and age span.
Populations are closed: every anchor is accounted for in exactly one bucket, and "no measurement" is counted as such —
never averaged in as a value (E-0920-C).
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B fresh_report.py PATH,HOME,LC_CTYPE <fresh_root> <news_root> <out.json>
"""
import os, sys, json, time, hashlib, datetime
import numpy as np
from scipy.stats import rankdata

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
FW, NW, OUT = sys.argv[2:5]
NEWT = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz"
NEWT_SHA = "ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62"
MONTH = 86400 * 30.4375; H4 = 14400; SEEDS = ("42", "2027")
BOOT_B = 2000; BOOT_RNG = 20260923


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def year_of(t): return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).year


def spearman_rows(P, Y, members, off, min_names=30):
    """per-anchor cross-sectional Spearman over the anchor's members with BOTH score and label finite.
    Returns (ic array over measured anchors, index array of those anchors, dict of why the others were not measured)."""
    ic = []; ix = []; skipped = {"fewer_than_min_names": 0, "no_score": 0, "zero_variance": 0}
    n = P.shape[0]
    for i in range(n):
        m = members[off[i]:off[i + 1]]
        if len(m) == 0: skipped["no_score"] += 1; continue
        s = P[i, m]; y = Y[i, m]; g = np.isfinite(s) & np.isfinite(y)
        if not np.isfinite(s).any(): skipped["no_score"] += 1; continue
        if g.sum() < min_names: skipped["fewer_than_min_names"] += 1; continue
        a = rankdata(s[g]); b = rankdata(y[g])
        if a.std() == 0 or b.std() == 0: skipped["zero_variance"] += 1; continue
        ic.append(float(np.corrcoef(a, b)[0, 1])); ix.append(i)
    return np.array(ic), np.array(ix, int), skipped


def block_slope_ci(age, ic, anchors, block_days=30):
    """OLS slope of IC on model age (per month) + a moving-block-bootstrap interval over 30-day blocks of anchors."""
    if len(ic) < 50 or np.ptp(age) < 1e-9: return {"UNMEASURABLE": f"n={len(ic)}, age span={float(np.ptp(age)):.4f} months"}
    A = np.polyfit(age, ic, 1); slope = float(A[0])
    blk = (anchors - anchors.min()) // (block_days * 86400)
    ub = np.unique(blk); rng = np.random.default_rng(BOOT_RNG); draws = []
    for _ in range(BOOT_B):
        pick = rng.choice(ub, size=len(ub), replace=True)
        sel = np.concatenate([np.flatnonzero(blk == b) for b in pick])
        if len(sel) < 20 or np.ptp(age[sel]) < 1e-9: continue
        draws.append(np.polyfit(age[sel], ic[sel], 1)[0])
    d = np.array(draws)
    return {"slope_ic_per_month": slope, "intercept": float(A[1]), "n_anchors_measured": int(len(ic)),
            "block_days": block_days, "B_effective": int(len(d)), "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))] if len(d) > 100 else "UNAVAILABLE"}


def age_curve(age, ic):
    out = {}
    b = np.floor(age).astype(int)
    for k in np.unique(b):
        m = b == k
        out[str(int(k))] = {"age_months_floor": int(k), "n_anchors": int(m.sum()), "mean_ic": float(ic[m].mean()), "median_ic": float(np.median(ic[m]))}
    return out


rec = {"device": "fresh_report.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()),
       "prereg": {"path": "docs/PREREG_fresh_models_newS_2026-09-23.md", "commit": "b6e682e0a"},
       "status": "REPORT ONLY — no gate, no verdict", "roots": {"fresh": FW, "news": NW}, "inputs": {}}

F = np.load(f"{NW}/work/NEWS_FEATURES.npz"); a = F["anchors"].astype(np.int64); off = F["off"]; mem = F["m"].astype(np.int64); syms = F["symbols"]
assert sha(NEWT) == NEWT_SHA
T = np.load(NEWT, allow_pickle=True); ya = T["E_ts"].astype(np.int64)
Y = np.full((len(a), len(syms)), np.nan, np.float32); ixm = np.searchsorted(ya, a); okm = (ixm < len(ya)) & (ya[np.minimum(ixm, len(ya) - 1)] == a); Y[okm] = T["y4s"][ixm[okm]]
rec["inputs"]["features"] = {"path": f"{NW}/work/NEWS_FEATURES.npz", "sha256": sha(f"{NW}/work/NEWS_FEATURES.npz")}
rec["inputs"]["labels"] = {"path": NEWT, "sha256": NEWT_SHA}
rec["inputs"]["axis"] = {"first": iso(a[0]), "last": iso(a[-1]), "n": int(len(a))}

# ───── 1. King IC by model age ─────
rec["king_ic_by_model_age"] = {}
king_age = {}
for arm, root in (("FRESH", FW), ("NEWS", NW)):
    K = np.load(f"{root}/work/king/KING_OOF.npz"); kr = json.load(open(f"{root}/work/king/TRAIN_RECEIPT.json"))
    assert np.array_equal(K["E_ts"].astype(np.int64), a)
    cut = np.full(len(a), -1, np.int64)
    for f in kr["folds"]:
        m = (a >= f["score_start"]) & (a <= f["score_end"]); cut[m] = f["max_train_label_end"]
    scored = np.isfinite(K["P"]).any(1)
    assert (cut[scored] > 0).all(), "a scored anchor with no fold cutoff"
    ic, ix, skip = spearman_rows(K["P"], Y, mem, off)
    age = (a[ix] - cut[ix]) / MONTH
    king_age[arm] = {"cut": cut, "P": K["P"], "ic": ic, "ix": ix, "age": age}
    rec["king_ic_by_model_age"][arm] = {"n_anchors_total": int(len(a)), "n_scored_anchors": int(scored.sum()), "n_measured": int(len(ic)),
                                        "not_measured": skip, "population_closed": bool(len(ic) + sum(skip.values()) == len(a)),
                                        "mean_ic_all_measured": float(ic.mean()), "age_months": {"min": float(age.min()), "max": float(age.max()), "mean": float(age.mean())},
                                        "curve": age_curve(age, ic), "slope": block_slope_ci(age, ic, a[ix]),
                                        "folds": [{"fold": f["fold"], "max_train_label_end": iso(f["max_train_label_end"]), "score_start": iso(f["score_start"]),
                                                   "score_end": iso(f["score_end"]), "train_pairs": f["train_pairs"], "embargo_anchors": f["embargo_anchors"],
                                                   "mean_cs_spearman": f["mean_cs_spearman"]} for f in kr["folds"]],
                                        "receipt_sha256": sha(f"{root}/work/king/TRAIN_RECEIPT.json")}
rec["king_ic_same_population_note"] = ("Both arms are measured on the same anchors and the same members; anchors where either arm has no score are "
                                       "counted in not_measured for that arm and never coded as a value.")

# ───── 2. F10 IC by model age + admission ─────
rec["f10_ic_by_model_age"] = {}; rec["f10_admission"] = {}
for seed in SEEDS:
    for arm, root in (("FRESH", FW), ("NEWS", NW)):
        fr = f"{root}/work/f10_s{seed}"
        tr = json.load(open(f"{fr}/TRAIN_RECEIPT.json")); P = np.load(f"{fr}/F10_OOF.npz")["P"]
        cut = np.full(len(a), -1, np.int64); adm = []
        ads = [(tag, json.load(open(f"{fr}/{tag}/ADMISSION.json"))) for tag in tr["expected_folds"]]
        starts = sorted(int(ad["test_start"]) for _, ad in ads)
        for tag, ad in ads:
            rej = int(sum(ad["rejected"].values())); tot = ad["accepted_windows"] + rej
            adm.append({"fold": tag, "accepted_windows": ad["accepted_windows"], "rejected": ad["rejected"], "considered_windows": tot,
                        "rejected_fraction": (rej / tot) if tot else None, "train_anchors": ad["train_anchors"],
                        "max_train_label_end": iso(ad["max_train_label_end"]), "test_start": iso(ad["test_start"]), "cutoff": iso(ad["cutoff"])})
            st = int(ad["test_start"]); later = [q for q in starts if q > st]
            end = min(later) if later else int(a[-1]) + H4
            cut[(a >= st) & (a < end)] = ad["max_train_label_end"]
        ic, ix, skip = spearman_rows(P, Y, mem, off)
        keep = cut[ix] > 0
        rec["f10_admission"][f"{arm}_s{seed}"] = {"n_folds": len(adm), "folds": adm,
                                                  "totals": {"accepted_windows": int(sum(x["accepted_windows"] for x in adm)),
                                                             "considered_windows": int(sum(x["considered_windows"] for x in adm)),
                                                             "rejected_windows": int(sum(x["considered_windows"] - x["accepted_windows"] for x in adm))}}
        if keep.sum() < 50:
            rec["f10_ic_by_model_age"][f"{arm}_s{seed}"] = {"UNMEASURABLE": f"only {int(keep.sum())} measured anchors with a fold cutoff"}
            continue
        age = (a[ix][keep] - cut[ix][keep]) / MONTH
        rec["f10_ic_by_model_age"][f"{arm}_s{seed}"] = {"n_measured": int(keep.sum()), "not_measured": skip,
                                                        "measured_without_fold_cutoff": int((~keep).sum()),
                                                        "mean_ic_all_measured": float(ic[keep].mean()),
                                                        "age_months": {"min": float(age.min()), "max": float(age.max()), "mean": float(age.mean())},
                                                        "curve": age_curve(age, ic[keep]), "slope": block_slope_ci(age, ic[keep], a[ix][keep]),
                                                        "receipt_sha256": sha(f"{fr}/TRAIN_RECEIPT.json")}

# ───── 3. target difference vs NEW_S + 4. chain turnover ─────
def dense(z, pre, i, width):
    """the adapter's sparse target row as a dense vector over ITS OWN index space (int16 idx into the run universe,
    the same for both arms because both adapter specs carry the same universe file/sha)."""
    v = np.zeros(width); s, e = z[pre + "_off"][i], z[pre + "_off"][i + 1]
    v[z[pre + "_idx"][s:e].astype(int)] = z[pre + "_val"][s:e]; return v


rec["target_difference_vs_news"] = {}; rec["chain_turnover"] = {}
for seed in SEEDS:
    zf = np.load(f"{FW}/targets/TARGETS_FRESH_s{seed}.npz"); zn = np.load(f"{NW}/targets/TARGETS_NEWS_s{seed}.npz")
    assert np.array_equal(zf["anchor"], zn["anchor"]), "target axes differ"
    an = zf["anchor"].astype(np.int64); n = len(an)
    width = int(max(zf["scaled_idx"].max(), zn["scaled_idx"].max())) + 1
    l1 = np.zeros(n); gf = np.zeros(n); gn = np.zeros(n); kf = zf["scaled_kind"]; kn = zn["scaled_kind"]
    prev_f = np.zeros(width); prev_n = np.zeros(width); tof = np.zeros(n); ton = np.zeros(n)
    for i in range(n):
        wf = dense(zf, "scaled", i, width); wn = dense(zn, "scaled", i, width)
        l1[i] = np.abs(wf - wn).sum(); gf[i] = np.abs(wf).sum(); gn[i] = np.abs(wn).sum()
        tof[i] = np.abs(wf - prev_f).sum(); ton[i] = np.abs(wn - prev_n).sum(); prev_f, prev_n = wf, wn
    diff = l1 > 0
    rec["target_difference_vs_news"][f"s{seed}"] = {
        "n_anchors": int(n), "anchors_with_any_difference": int(diff.sum()), "share_anchors_different": float(diff.mean()),
        "kind_decision_differs": int((kf != kn).sum()),
        "l1_over_all_anchors": {"mean": float(l1.mean()), "p50": float(np.percentile(l1, 50)), "p90": float(np.percentile(l1, 90)), "p99": float(np.percentile(l1, 99)), "max": float(l1.max())},
        "l1_over_differing_anchors": ({"n": int(diff.sum()), "mean": float(l1[diff].mean()), "p50": float(np.percentile(l1[diff], 50)),
                                       "p90": float(np.percentile(l1[diff], 90)), "max": float(l1[diff].max())} if diff.any() else {"n": 0, "note": "no differing anchor"}),
        "mean_gross": {"FRESH": float(gf.mean()), "NEWS": float(gn.mean())},
        "l1_relative_to_mean_gross": float(l1.mean() / gn.mean()) if gn.mean() > 0 else None,
        "delivery_line": ("<50% of anchors differ: the change barely reaches the book" if diff.mean() < 0.5 else ">=50% of anchors differ"),
        "sources": {"FRESH": sha(f"{FW}/targets/TARGETS_FRESH_s{seed}.npz"), "NEWS": sha(f"{NW}/targets/TARGETS_NEWS_s{seed}.npz")}}
    yr = np.array([year_of(x) for x in an]); ty = {}
    for y in np.unique(yr):
        m = yr == y
        ty[str(int(y))] = {"anchors": int(m.sum()), "FRESH_mean_L1_turnover": float(tof[m].mean()), "NEWS_mean_L1_turnover": float(ton[m].mean()),
                           "ratio": float(tof[m].mean() / ton[m].mean()) if ton[m].mean() > 0 else None}
    rec["chain_turnover"][f"s{seed}"] = {"definition": "mean over anchors of sum|w_t - w_{t-1}| on the adapter's scaled target rows (target layer, before execution)",
                                         "by_year": ty, "whole_axis": {"FRESH": float(tof.mean()), "NEWS": float(ton.mean())}}

# ───── 5. seat shares ─────
rec["seat_shares"] = {}
for arm, root in (("FRESH", FW), ("NEWS", NW)):
    L = np.load(f"{root}/work/legs.npz"); WLm = L["WL"]; rdy = L["ready"]; at = L["E_ts"].astype(np.int64)
    yr = np.array([year_of(x) for x in at]); by = {}
    for y in np.unique(yr):
        m = (yr == y) & rdy
        by[str(int(y))] = ({"ready_anchors": int(m.sum()), "king": float(WLm[m, 0].mean()), "rev24": float(WLm[m, 1].mean()), "fund": float(WLm[m, 2].mean())}
                           if m.sum() else {"ready_anchors": 0, "note": "no ready anchor in this year — no seat measured"})
    rec["seat_shares"][arm] = {"by_year": by, "ready_total": int(rdy.sum()), "not_ready_total": int((~rdy).sum()),
                               "legs_sha256": sha(f"{root}/work/legs.npz")}

json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
print("FRESH_REPORT written", OUT, sha(OUT), flush=True)
for arm in ("FRESH", "NEWS"):
    k = rec["king_ic_by_model_age"][arm]
    print(f"  King {arm}: mean IC {k['mean_ic_all_measured']:+.5f} over {k['n_measured']} anchors, age {k['age_months']['min']:.2f}–{k['age_months']['max']:.2f} months, slope {k['slope'].get('slope_ic_per_month')}", flush=True)
for seed in SEEDS:
    d = rec["target_difference_vs_news"][f"s{seed}"]
    print(f"  targets s{seed}: {d['share_anchors_different']:.4f} of anchors differ, mean L1 {d['l1_over_all_anchors']['mean']:.5f} (mean gross NEWS {d['mean_gross']['NEWS']:.4f})", flush=True)
