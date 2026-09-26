"""dlarch_t2_pregate_2026.py -- lead's two frozen T2 pre-gate conditions, evaluated on the 2026 segment.

lead revision 5 (c), transcribed verbatim, thresholds NOT authored here (dlarch has a stake in what this
gate admits):
  1. the residual IC's 95% daily-block interval LOWER BOUND > 0
  2. in the 2026 segment, the MEDIAN per-anchor weight correlation between King's book and the
     residual-prediction's book <= 0.8
  Both must hold for T2 to run.

lead's caliber clarifications (2026-09-26), also transcribed:
  * the mean AND the interval are computed on 2026 ANCHORS ONLY. The pooled 2023-2026 value is reported
    descriptively and is NOT the gate quantity.
  * the 2026 fold's training must obey the original device's embargo -- no 2026 labels -- and that fold's
    train_label_end goes in the receipt.
  * block length comes from the frozen judge's existing value, not chosen here.
  * weight correlation = per-anchor cross-sectional, then median over anchors.

WHAT THIS DEVICE REUSES RATHER THAN REIMPLEMENTS, and why each matters:
  * the residual target and the predictions come from a PROBE COPY of the frozen dlarch_pregates.py with
    two mechanical changes (TEST_YEARS gains 2026; preds persisted). The residual construction itself was
    NOT transcribed -- re-implementing a frozen definition from its description is the single defect that
    recurred most this week.
  * ic_series is imported from the pinned readout, boot from the frozen judge, evolve from the producer.
  * the per-anchor correlation rule is dlarch_s1s3.py's Q1 rule (union of non-zero cells, >= 20 names),
    so the number is directly comparable to the existing +0.91 (2026) / +0.43 (pre-2026) readings.

POSITIVE CONTROL ON THE ASSEMBLY (before any new input is fed through it): evolve() is first called with
the ARCHIVED F10 and required to reproduce the archived combo ARRAY-FOR-ARRAY. An assembly that cannot
reproduce a known book has no business producing a new one. This mirrors s1s3's parity arm.

usage: dlarch_t2_pregate_2026.py <env-whitelist> <preds.npz> <frozen-PREGATES.json> <out.json>
"""
import os, sys, json, time, calendar, hashlib
import numpy as np

WL = set(sys.argv[1].split(","))
_x = sorted(set(os.environ) - WL)
assert not _x, f"env outside whitelist: {_x}"
PREDS, FROZEN, OUT = sys.argv[2], sys.argv[3], sys.argv[4]
W = "/dev/shm/news2_2026-09-23"
MASK_PATH = "/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"
ENGINE = f"{W}/engine"
EMBARGO, H4 = 60, 14400          # king_folds default, as the frozen device pins it
Y2026 = calendar.timegm((2026, 1, 1, 0, 0, 0))
MIN_NAMES = 20                   # dlarch_s1s3.py Q1 rule
THR_CORR = 0.8                   # lead's threshold, transcribed
sys.path.insert(0, f"{W}/devices")
sys.path.insert(0, ENGINE)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


from continuous_combo import evolve                                    # noqa: E402
from book_universe import align as align_universe, PATH as UPATH, SHA as USHA  # noqa: E402
from news2_diag1_score_ic import ic_series                             # noqa: E402
import combo_target                                                    # noqa: E402
import news_stats as NS                                               # noqa: E402
import bt_tables as BT, bt_driver_lib as DL                            # noqa: E402
NS.BT, NS.DL = BT, DL
assert sha(f"{W}/vendor_live/fea171/combo_stage.py") == combo_target.EXPECTED, "producer source moved"
assert sha(UPATH) == USHA, "universe moved"

# ── inputs, assembled the way dlarch_s1s3.py assembles them ─────────────────────────────────────────
F = np.load(f"{W}/work/NEWS_FEATURES.npz")
leg = np.load(f"{W}/work/legs.npz")
a = F["anchors"].astype(np.int64); syms = F["symbols"]
off, mm = F["off"], F["m"].astype(np.int64)
members = [mm[off[i]:off[i + 1]] for i in range(len(a))]
universe = np.load(UPATH)
mk = np.load(MASK_PATH); assert np.array_equal(mk["ts"].astype(np.int64), a), "mask axis"
crypto = np.load(f"{W}/receipts/P1_members_2025H2on.npz")["crypto"]
cand = mk["mask"] & crypto[None, :]
use = (a >= 1672531200) & (a <= universe["ts"][-1]); au = a[use]
book_legal = align_universe(au, syms, universe) & cand[use]
params = json.loads(open(f"{W}/inputs/bundle_config.json").read())["params"]
mem_u = [members[i] for i in np.flatnonzero(use)]
EV = dict(anchors=au, king=leg["KZ"][use].astype(np.float64), fund=leg["ZFD"][use].astype(np.float64),
          seats=leg["WL"][use].astype(np.float64), rn8=leg["RN8"][use].astype(np.float64),
          members=mem_u, qv=leg["QV"][use].astype(np.float64), legal=book_legal, ready=leg["ready"][use])

# ── POSITIVE CONTROL: the assembly must reproduce a KNOWN book, array for array ─────────────────────
POL = "scaled_diagnostic"
arch = np.load(f"{W}/work/combo_s42/{POL}.npz")
f10_arch = np.load(f"{W}/work/f10_s42/F10_OOF.npz")["P"][use].astype(np.float64)
P_ctl = evolve(f10=f10_arch, params=params, publication=POL, **EV)
ctl = {k: bool(np.array_equal(P_ctl[k], arch[k])) for k in ("kc", "fc", "raw", "weights", "trade_mask")}
ctl["ALL"] = all(ctl.values())
assert ctl["ALL"], (f"assembly control FAILED {ctl}: evolve() here does not reproduce the archived book, "
                    "so any book it makes from a new input is not trustworthy")

# ── the 2026 fold's embargo, proven not asserted ────────────────────────────────────────────────────
train_idx = np.flatnonzero(a + H4 <= Y2026 - EMBARGO * H4)
fold = {"fold": "2026", "test_start_utc": iso(Y2026), "embargo_anchors": EMBARGO,
        "rule": "king_folds.fold_rows: train = a + 14400 <= start - embargo*14400",
        "n_train_anchors": int(len(train_idx)),
        "max_train_anchor_utc": iso(a[train_idx].max()),
        "train_label_end_utc": iso(a[train_idx].max() + H4),
        "uses_no_2026_label": bool(a[train_idx].max() + H4 <= Y2026)}
assert fold["uses_no_2026_label"], f"the 2026 fold's training labels reach into 2026: {fold}"

# ── condition 1: residual IC on 2026 anchors only ───────────────────────────────────────────────────
Z = np.load(PREDS, allow_pickle=False)
assert np.array_equal(Z["anchors"].astype(np.int64), a), "preds axis != feature axis"
Rres = Z["residual_target"]
lab_ok_rows = np.flatnonzero(np.isfinite(Rres).any(1))
rows26 = np.array([i for i in lab_ok_rows if a[i] >= Y2026], dtype=int)
rows_all = lab_ok_rows
# The frozen judge's own block values, read from it rather than guessed. It exposes BLOCK_MAIN=30 and
# BLOCK_SENS=5 and its own main() reports BOTH (boot_30d / boot_5d), so this does the same: the gate reads
# the MAIN block, the sensitivity block is reported beside it. My first draft used getattr(NS,"BLOCK") with
# a fallback of 5 -- that name does not exist, so the fallback would have silently applied the SENSITIVITY
# block to a gate decision while the receipt claimed it came "from the frozen judge".
BLK_MAIN, BLK_SENS = NS.BLOCK_MAIN, NS.BLOCK_SENS
cond1 = {}
for mdl in ("ridge", "lgbm"):
    P = Z[mdl]
    ic26, n26, sk26 = ic_series(P, Rres, rows26, rows26)
    icall, _, _ = ic_series(P, Rres, rows_all, rows_all)
    # PER-DAY IC, computed by calling the frozen ic_series ONE DAY AT A TIME.
    # Why not group its pooled output by day: ic_series DROPS anchors (m.sum() < MIN_NAMES, or a
    # non-finite rho) and returns no index map, so len(ics) <= len(rows) with no way to say which anchor
    # each entry came from. Zipping the returned array against days derived from `rows26` would therefore
    # MISALIGN silently as soon as one anchor is skipped -- it would not raise, it would just be wrong.
    # Calling per day keeps the alignment true by construction and gives skipped anchors exactly the
    # treatment the frozen function gives them.
    days = np.unique((a[rows26] // 86400) * 86400)
    per_day, empty_days = [], 0
    for u in days:
        r = rows26[(a[rows26] // 86400) * 86400 == u]
        icd, _, _ = ic_series(P, Rres, r, r)
        if len(icd):
            per_day.append(float(np.mean(icd)))
        else:
            empty_days += 1
    per_day = np.asarray(per_day)
    b = NS.boot(per_day, BLK_MAIN)
    bs = NS.boot(per_day, BLK_SENS)
    # boot multiplies by 1e4 to report bps; the input here is an IC, so undo that to get IC units
    lo, lo_s = b["ci95_bps"][0] / 1e4, bs["ci95_bps"][0] / 1e4
    cond1[mdl] = {"ic_2026_mean": float(np.nanmean(ic26)), "n_anchors_2026": int(len(ic26)),
                  "ic_pooled_2023_2026_DESCRIPTIVE_ONLY": float(np.nanmean(icall)),
                  "n_days_2026": int(len(per_day)),
                  "n_days_dropped_all_anchors_skipped": int(empty_days),
                  "n_anchors_skipped_by_ic_series": int(sk26),
                  "block_days_main_from_frozen_judge": b["block_days"],
                  "block_days_sensitivity": bs["block_days"],
                  "ci95_lower_bound": lo, "ci95_lower_bound_sensitivity_block": lo_s,
                  "ci95_bps_raw_main": b["ci95_bps"], "ci95_bps_raw_sensitivity": bs["ci95_bps"],
                  "B_draws": b["B"], "rng": b["rng"],
                  "PASS_condition_1": bool(lo > 0),
                  "PASS_condition_1_under_sensitivity_block": bool(lo_s > 0)}

# ── condition 2: King book vs residual-prediction book, per-anchor, median over 2026 ────────────────
cond2 = {}
for mdl in ("ridge", "lgbm"):
    f10r = np.nan_to_num(Z[mdl][use], nan=0.0).astype(np.float64)
    Pr = evolve(f10=f10r, params=params, publication=POL, **EV)
    kc, fc = Pr["kc"], Pr["fc"]
    sel = np.flatnonzero(au >= Y2026)
    wp = []
    for j in sel:
        k, f = kc[j], fc[j]
        nz = (np.abs(k) > 1e-12) | (np.abs(f) > 1e-12)
        if nz.sum() >= MIN_NAMES and k[nz].std() > 0 and f[nz].std() > 0:
            wp.append(float(np.corrcoef(k[nz], f[nz])[0, 1]))
    wp = np.asarray(wp)
    cond2[mdl] = {"n_anchors_used": int(len(wp)), "n_anchors_2026": int(len(sel)),
                  "median": float(np.median(wp)) if len(wp) else None,
                  "mean": float(wp.mean()) if len(wp) else None,
                  "rule": "dlarch_s1s3 Q1: per-anchor Pearson over the union of non-zero cells, >= 20 names",
                  "threshold": THR_CORR,
                  "PASS_condition_2": bool(len(wp) and np.median(wp) <= THR_CORR)}

rec = {"device": "dlarch_t2_pregate_2026.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": iso(time.time()), "criterion_source": "lead revision 5 (c), transcribed; thresholds not authored here",
       "preds": os.path.abspath(PREDS), "preds_sha256": sha(PREDS),
       "assembly_positive_control": ctl, "fold_2026_embargo": fold,
       "condition_1_residual_ic_2026": cond1, "condition_2_weight_corr_2026": cond2,
       "frozen_receipt_controls": None, "verdict_per_model": {
           m: ("RUN_T2" if cond1[m]["PASS_condition_1"] and cond2[m]["PASS_condition_2"] else "DO_NOT_RUN_T2")
           for m in ("ridge", "lgbm")},
       "ambiguity_for_lead": ("the criterion says 'the residual IC' without naming ridge or lgbm; the "
                              "frozen PG-T2 reported both (0.06186 / 0.06216). Both are evaluated here and "
                              "neither is privileged. If the gate is meant to be one of them, or both "
                              "jointly, lead should say which -- dlarch does not choose.")}
fz = json.load(open(FROZEN))["arms"]["T2_residual"]
rec["frozen_receipt_controls"] = {
    "R2_target_on_king_per_anchor_frozen": fz["R2_target_on_king_per_anchor"],
    "finite_residual_pairs_frozen": fz["finite_residual_pairs"],
    "train_pairs_frozen_2023_2025": {y: fz["years"][y]["train_pairs"] for y in ("2023", "2024", "2025")},
    "note": ("these are TEST_YEARS-independent or per-year, so the probe copy must reproduce them exactly; "
             "the pooled ic_vs_* values are NOT comparable because adding 2026 widens the pooled window")}

tmp = OUT + ".tmp"
with open(tmp, "w") as f:
    json.dump(rec, f, indent=1)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, OUT)
assert json.load(open(OUT)) == rec, "receipt read back differs from what was written"

print("assembly control (evolve reproduces the archived book):", ctl)
print("2026 fold embargo: train_label_end %s, uses_no_2026_label=%s"
      % (fold["train_label_end_utc"], fold["uses_no_2026_label"]))
for m in ("ridge", "lgbm"):
    c1, c2 = cond1[m], cond2[m]
    print("%-6s cond1 IC(2026)=%+.5f  n_days=%d block=%s  CI95 lower=%+.6f -> %s"
          % (m, c1["ic_2026_mean"], c1["n_days_2026"], c1["block_days_main_from_frozen_judge"],
             c1["ci95_lower_bound"], c1["PASS_condition_1"]))
    print("%-6s cond2 median wcorr=%s (n=%d) threshold<=%.1f -> %s"
          % ("", c2["median"], c2["n_anchors_used"], THR_CORR, c2["PASS_condition_2"]))
    print("%-6s pooled IC 2023-2026 (descriptive only) = %+.5f" % ("", c1["ic_pooled_2023_2026_DESCRIPTIVE_ONLY"]))
print("verdict per model:", rec["verdict_per_model"])
print("T2_PREGATE_2026 OK receipt=%s sha256=%s" % (OUT, sha(OUT)[:16]))
