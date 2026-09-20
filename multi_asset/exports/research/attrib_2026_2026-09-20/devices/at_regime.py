#!/usr/bin/env python3
"""at_regime.py — PREREG §2-G: the DESCRIPTIVE persistence of the anchor conditions.

It reports, for every condition of §2-D (plus RG-TREND, outside the family):
  · the empirical distribution of RUN LENGTHS of each tercile bucket (median, p90, max, n_runs), over the
    labelled axis 2022-06-30 → 2026-09-18 (the extension anchors are labelled by G0's own frozen output and
    are included HERE ONLY, for positioning; they never enter a FULL_RECIPE performance number);
  · the empirical frequency of still being in the SAME bucket +7 / +30 / +90 days later, computed from every
    historical anchor that started in that bucket;
  · the book's g and its day-block bootstrap CI in each bucket (FULL_RECIPE only — the only window with
    realised cash);
  · which bucket combination the book is in at the last anchor where that combination is fully labelled, how
    often it occurred historically and how long those episodes lasted; and the same for the modal combination
    of the 2023-06-30 → 2023-12-31 fall. Two sets are reported because the frozen upstream labels do not all
    reach the axis end: JOINT8 = the prereg's own eight §2-D conditions (its last fully labelled anchor is
    2026-08-31T00:00Z, because G0's RG-ALT stops there and TURN needs realised turnover), JOINT6 = exactly the
    subset that IS labelled through 2026-09-18T20:00Z. Neither is chosen by what it shows; the gap is a
    coverage fact and is printed as one. [This paragraph was rewritten after the first run REFUSED on
    `joint.last_anchor_fully_labelled`; no analysis definition changed, only which anchor "current" means.]
  · and, because an exact 8-way combination is almost always rare, a MATCH PROFILE: for every historical
    anchor, how many of the buckets it shares with the reference state, the number of anchors at each match
    count, and the book's realised g in FULL_RECIPE at each match count. Declared here, before the first run;
    it is a coarse non-selective summary, not a chosen cut.

THESE ARE HISTORICAL FREQUENCIES OF A FINITE SAMPLE, NOT PROBABILITIES AND NOT FORECASTS. This device makes
no statement that any state has ended, will end, will persist or will return; the prereg forbids it and the
receipt repeats the sentence next to every number.

usage: python at_regime.py <ENV_WHITELIST_CSV> <OUT_DIR>
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import at_lib as L

T0 = time.time()
ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{L.ROOT}/receipts"
os.makedirs(OUT, exist_ok=True)
chk = L.Checks(T0)
rec = L.rec_head("at_regime.py", sys.argv)
chk("env.whitelist", not sorted(set(rec["env"]) - ENV_OK), {"extra": sorted(set(rec["env"]) - ENV_OK)})
CFGP = f"{L.ROOT}/RUN_CONFIG_attrib_2026-09-20.json"
PANP = f"{L.ROOT}/work/AT_PANEL.npz"
L1P = f"{L.ROOT}/work/AT_L1_mean.npz"
rec["frozen_config"] = {"path": CFGP, "sha256": L.sha(CFGP)}
rec["upstream"] = {"panel": {"path": PANP, "sha256": L.sha(PANP)}, "L1_mean": {"path": L1P, "sha256": L.sha(L1P)}}
rec["caveat"] = ("Historical frequencies of a finite sample; not probabilities, not forecasts. No claim that a "
                 "state has ended, will end, will persist or will return.")

Z = np.load(PANP, allow_pickle=True)
L1 = np.load(L1P)
A = Z["A"].astype(np.int64)
in_run = Z["in_run"]
COND = Z["COND"]
CONDN = [str(s) for s in Z["COND_NAMES"]]
G0L = Z["G0L"]
GVARS = [str(s) for s in Z["G0_VARS"]]
NA = len(A)
chk("axis", NA == 9252 and L.utc(A[-1]) == "2026-09-18T20:00:00Z", {"n": NA, "last": L.utc(A[-1])})


def expanding_terciles(x, warm=1080):
    lab = np.full(len(x), -1, np.int8)
    for i in range(warm, len(x)):
        h = x[:i + 1]
        h = h[np.isfinite(h)]
        if h.size < warm:
            continue
        q1, q2 = np.quantile(h, [1 / 3, 2 / 3])
        if np.isfinite(x[i]):
            lab[i] = 0 if x[i] < q1 else (2 if x[i] > q2 else 1)
    return lab


CLAB = {}
for ci, cn in enumerate(CONDN):
    if cn in L.COND_FROM_G0:
        CLAB[cn] = G0L[:, GVARS.index(L.COND_FROM_G0[cn])]
    else:
        CLAB[cn] = expanding_terciles(COND[:, ci])
    chk(f"labels.present.{cn}", int((CLAB[cn] >= 0).sum()) > 4000, {"n_labelled": int((CLAB[cn] >= 0).sum())})
# TURN has no label after the certified run's window (no realised turnover there)
for cn in CONDN:
    if cn == "TURN":
        CLAB[cn] = np.where(in_run, CLAB[cn], -1).astype(np.int8)

BUCK = ("low", "mid", "high")
H_ANCH = {7: 42, 30: 180, 90: 540}


def runs_of(lab, b):
    m = (lab == b).astype(np.int8)
    d = np.diff(np.concatenate([[0], m, [0]]))
    st = np.nonzero(d == 1)[0]
    en = np.nonzero(d == -1)[0]
    return (en - st)


OUTJ = {"caveat": rec["caveat"], "axis": [L.utc(A[0]), L.utc(A[-1])], "n_anchors": int(NA),
        "labelled_from": {cn: (L.utc(A[np.nonzero(CLAB[cn] >= 0)[0][0]]) if (CLAB[cn] >= 0).any() else None) for cn in CONDN},
        "conditions": {}}
mfull = L.period_mask(A, "2023-06-30T04:00:00Z", "2026-08-31T00:00:00Z")
A_run = A[in_run]
g_run = L1["g"]
for ci, cn in enumerate(CONDN):
    lab = CLAB[cn]
    d = {"run_lengths_anchors": {}, "persistence_same_bucket": {}, "g_FULL_RECIPE": {}}
    for b, bn in enumerate(BUCK):
        r_ = runs_of(lab, b)
        d["run_lengths_anchors"][bn] = ({"n_runs": int(len(r_)), "median": float(np.median(r_)), "p90": float(np.percentile(r_, 90)),
                                         "max": int(r_.max()), "median_days": float(np.median(r_) / 6.0),
                                         "p90_days": float(np.percentile(r_, 90) / 6.0), "max_days": float(r_.max() / 6.0)}
                                        if len(r_) else {"n_runs": 0})
        pers = {}
        for hd, ha in H_ANCH.items():
            src = np.nonzero((lab == b))[0]
            src = src[src + ha < NA]
            src = src[lab[src + ha] >= 0]
            pers[f"+{hd}d"] = ({"n": int(len(src)), "share_same_bucket": float((lab[src + ha] == b).mean())}
                               if len(src) else {"n": 0})
        d["persistence_same_bucket"][bn] = pers
        mm = mfull & (lab == b)
        mm_run = mm[in_run] if len(mm) == NA else mm
        if mm_run.sum() >= 2:
            _, s, c = L.day_aggregate(A_run, g_run, mm_run)
            dr = L.boot_mean_ratio(s, c, seed_k=400 + 3 * ci + b)
            d["g_FULL_RECIPE"][bn] = L.ci_p(float(s.sum() / c.sum()), dr)
            d["g_FULL_RECIPE"][bn]["n_anchors"] = int(mm_run.sum())
        else:
            d["g_FULL_RECIPE"][bn] = {"n_anchors": int(mm_run.sum())}
    OUTJ["conditions"][cn] = d

# ── the joint combination ────────────────────────────────────────────────────────────────────────────
# Two sets are reported, because the frozen upstream labels do not all reach the last anchor:
#   JOINT8 = the eight conditions of PREREG §2-D. TURN has no label past 2026-08-31 (no realised turnover
#            beyond the certified run) and G0's RG-ALT / RG-TREND stop at 2026-08-31 as well, so JOINT8's
#            last fully labelled anchor is inside the certified window. Reported at ITS OWN last anchor.
#   JOINT6 = the six that are labelled through 2026-09-18T20:00Z (DISP, FDISP, FLEVEL, BREADTH, VOL, UBAR).
# Neither set is chosen by what it shows: JOINT8 is the prereg's own list, JOINT6 is exactly the subset that
# the upstream labels cover to the end of the axis. The mismatch is a coverage fact and is stated as one.
_episodes_cache = {}


def _episodes(m):
    d = np.diff(np.concatenate([[0], m.astype(np.int8), [0]]))
    st = np.nonzero(d == 1)[0]
    en = np.nonzero(d == -1)[0] - 1
    return list(zip(st.tolist(), en.tolist()))


SETS = {"JOINT8": list(L.COND_NAMES),
        "JOINT6": [cn for cn in ("DISP", "FDISP", "FLEVEL", "BREADTH", "VOL", "UBAR")]}
m23_win = L.period_mask(A, "2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z")
for sname, FAM in SETS.items():
    LABM = np.stack([CLAB[cn] for cn in FAM], 1)
    allok = (LABM >= 0).all(1)
    key = np.where(allok, (LABM * (3 ** np.arange(len(FAM)))[None, :]).sum(1), -1)
    li = int(np.nonzero(allok)[0][-1])
    chk(f"joint.{sname}.has_a_fully_labelled_anchor", bool(allok.any()),
        {"last_fully_labelled": L.utc(A[li]), "n_fully_labelled": int(allok.sum()),
         "unlabelled_at_axis_end": [FAM[j] for j in range(len(FAM)) if LABM[NA - 1, j] < 0]})

    def combo_stats(k, _key=key, _allok=allok):
        m = _key == k
        r_ = runs_of(m.astype(np.int8), 1)
        out = {"n_anchors": int(m.sum()), "share_of_labelled": float(m.sum() / max(_allok.sum(), 1)),
               "n_episodes": int(len(r_)),
               "median_run_anchors": (float(np.median(r_)) if len(r_) else None),
               "p90_run_anchors": (float(np.percentile(r_, 90)) if len(r_) else None),
               "max_run_anchors": (int(r_.max()) if len(r_) else None),
               "episodes": [[L.utc(A[i]), L.utc(A[j])] for i, j in _episodes(m)][:20]}
        mr = m[in_run] & mfull[in_run]
        if mr.sum() >= 2:
            _, s, c = L.day_aggregate(A_run, g_run, mr)
            dr = L.boot_mean_ratio(s, c, seed_k=900 + len(FAM))
            out["g_FULL_RECIPE"] = L.ci_p(float(s.sum() / c.sum()), dr)
            out["g_FULL_RECIPE"]["n_anchors"] = int(mr.sum())
        else:
            out["g_FULL_RECIPE"] = {"n_anchors": int(mr.sum())}
        return out

    OUTJ[f"current_state_{sname}"] = {
        "conditions": FAM, "at_anchor": L.utc(A[li]),
        "is_axis_end": bool(li == NA - 1),
        "buckets": {cn: BUCK[int(CLAB[cn][li])] for cn in FAM},
        "levels": {cn: (float(COND[li, CONDN.index(cn)]) if np.isfinite(COND[li, CONDN.index(cn)]) else None) for cn in FAM},
        "joint_stats": combo_stats(int(key[li]))}
    m23 = m23_win & allok
    if m23.any():
        vals, cnt = np.unique(key[m23], return_counts=True)
        k23 = int(vals[np.argmax(cnt)])
        OUTJ[f"2023_fall_modal_combination_{sname}"] = {
            "buckets": {FAM[j]: BUCK[(k23 // 3 ** j) % 3] for j in range(len(FAM))},
            "share_of_2023H2_labelled_anchors": float(cnt.max() / m23.sum()),
            "n_2023H2_fully_labelled": int(m23.sum()),
            "stats": combo_stats(k23)}

    def match_profile(ref_lab, tag, _LABM=LABM, _allok=allok, _FAM=FAM):
        mc = (_LABM == ref_lab[None, :]).sum(1)
        mc = np.where(_allok, mc, -1)
        out = {"conditions": _FAM, "reference": {_FAM[j]: BUCK[int(ref_lab[j])] for j in range(len(_FAM))}, "by_match_count": {}}
        for c_ in range(len(_FAM) + 1):
            m = mc == c_
            rr = {"n_anchors": int(m.sum()), "share": float(m.sum() / max(_allok.sum(), 1))}
            mr = m[in_run] & mfull[in_run]
            if mr.sum() >= 2:
                _, s, c2 = L.day_aggregate(A_run, g_run, mr)
                rr["g_FULL_RECIPE"] = float(s.sum() / c2.sum())
                rr["n_anchors_FULL_RECIPE"] = int(mr.sum())
            out["by_match_count"][str(c_)] = rr
        r_ = runs_of((mc >= len(_FAM) - 1).astype(np.int8), 1)
        out["runs_with_at_most_one_mismatch"] = ({"n_episodes": int(len(r_)), "median_anchors": float(np.median(r_)),
                                                  "p90_anchors": float(np.percentile(r_, 90)), "max_anchors": int(r_.max()),
                                                  "total_anchors": int(r_.sum())} if len(r_) else {"n_episodes": 0})
        OUTJ[tag] = out

    match_profile(LABM[li], f"match_profile_vs_current_{sname}")
    if m23.any():
        match_profile(np.array([(k23 // 3 ** j) % 3 for j in range(len(FAM))]), f"match_profile_vs_2023_fall_{sname}")
# per-condition marginal distance of the current state from the 2023H2 distribution
OUTJ["bucket_shares_by_period"] = {}
for name, lo, hi, _ in L.PERIODS:
    m = L.period_mask(A, lo, hi)
    if not m.any():
        continue
    OUTJ["bucket_shares_by_period"][name] = {
        cn: {bn: float((CLAB[cn][m] == b).mean()) for b, bn in enumerate(BUCK)} | {"unlabelled": float((CLAB[cn][m] < 0).mean())}
        for cn in CONDN}
OUTJ["extension_bucket_shares_2026-09"] = {
    cn: {bn: float((CLAB[cn][~in_run] == b).mean()) for b, bn in enumerate(BUCK)} for cn in CONDN}

p = f"{OUT}/AT_REGIME.json"
tmp = p + ".tmp"
with open(tmp, "w") as f:
    json.dump(OUTJ, f, indent=1, default=str)
os.replace(tmp, p)
rec["outputs"] = {"regime": {"path": p, "sha256": L.sha(p)}}
v = L.write_receipt(rec, chk, f"{OUT}/AT_REGIME_RECEIPT.json", {"peak_rss_gb": L.rss_gb(), "runtime_s": round(time.time() - T0, 1)})
print("AT_REGIME VERDICT=%s checks=%d failed=%s" % (v, len(chk.rows), chk.fails), flush=True)
sys.exit(0 if v == "PASS" else 3)
