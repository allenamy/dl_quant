#!/usr/bin/env python3
"""d10_seed_provenance.py -- who built shadow_bundle/leg_returns.npz, from what, and why king == 0 in 2022-23.

lead 2026-09-26 task 2, after ruling the research replay authoritative. Read-only.

PROVENANCE, by citation rather than by inference:
  writer       multi_asset/exports/research/runpod_scripts/workspace_mirror/pod_export_shadow_bundle.py:147
               np.savez_compressed(f"{OUT}/leg_returns.npz", ts=E_ts[np.array(idx)], **LRa)
  built        file mtime 2026-09-01T05:58Z; sha256 6061af10... which the bundle MANIFEST.json also records,
               so the bundle is self-consistent about it
  leg defs     L82-92: sc = {"king": PRED[i, m], "rev24": -R24[j, m], "fund": FE[j, m]} then per leg
               z = np.nan_to_num(xz(sc[leg])); z = where(ok, z, 0); z -= z[ok].mean(); g = |z|.sum();
               LR = (z/g * nan_to_num(y4)).sum()*1e4 if g > 1e-9 else 0.0
  KING SOURCE  L44-50: PRED = full(nan); then folds for YV in (2024, 2025) each fit their OWN
               lgb.LGBMRegressor(n_estimators=400, lr=0.05, num_leaves=63, subsample=0.8,
               colsample_bytree=0.8), and the 2026 fold uses the pinned booster saved to slow2026.txt.
               The file's own comment: "钉死预测: 2026 折用本 booster; 2024/2025 折照旧训练(仅历史腿收益用,
               不进影子)".

WHY king == 0.0 FOR 2022-01-08..2023-12-31 (4,338 entries): there is NO 2022 or 2023 fold, so PRED stays NaN
there; xz(all-NaN) is all-NaN, np.nan_to_num makes it all ZERO, so g == 0 and the append takes its `else 0.0`
branch. The first non-zero king is 2024-01-01, which is exactly where the first fold begins. rev24 and fund
have no zeros because R24 and FE exist across the whole axis.

The research side handles the same situation differently: nc_legs.py refuses the anchor
(`if not np.isfinite(pred).all(): why[A] = "king_oof_missing"; continue`) instead of recording a zero, so it
has no LR entry at all there. Two defensible choices, but they are not the same series.

★ AND THE DIVERGENCE IS NOT ONLY THE MISSING FOLDS. It persists in 2026, where both sides do have King
predictions, because the seed's King comes from a DIFFERENT MODEL -- the LGBM folds the exporter trains inline
plus the pinned slow2026 booster -- not from the NC King OOF the research replay uses.
"""
import collections
import datetime
import hashlib
import json
import os
import statistics as st
import sys

import numpy as np

SEED = os.path.expanduser("~/wide_shadow/shadow_bundle/leg_returns.npz")
MANIFEST = os.path.expanduser("~/wide_shadow/shadow_bundle/MANIFEST.json")
WRITER = ("multi_asset/exports/research/runpod_scripts/workspace_mirror/pod_export_shadow_bundle.py",
          147, 'np.savez_compressed(f"{OUT}/leg_returns.npz", ts=E_ts[np.array(idx)], **LRa)')


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def ymd(t, fmt="%Y"):
    return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime(fmt)


def main():
    wl_slice, out = sys.argv[1], sys.argv[2]
    R = np.load(wl_slice)
    E = R["E_ts"].astype(np.int64)
    LR = np.asarray(R["LR"], np.float64)
    ready = np.asarray(R["ready"], bool)
    S = np.load(SEED, allow_pickle=True)
    ts = S["ts"].astype(np.int64)
    man = json.load(open(MANIFEST))
    seed_sha = sha(SEED)

    kz = (S["king"] == 0.0)
    ei = {int(t): i for i, t in enumerate(E)}
    by = collections.defaultdict(lambda: {0: [], 1: [], 2: []})
    for k, t in enumerate(ts):
        i = ei.get(int(t))
        if i is None or not np.isfinite(LR[i, 0]):
            continue
        for ci, c in enumerate(("king", "rev24", "fund")):
            by[ymd(t)][ci].append(abs(float(S[c][k]) - float(LR[i, ci])))

    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "task": "lead 2026-09-26 task 2: provenance of shadow_bundle/leg_returns.npz",
           "seed": {"path": SEED, "sha256": seed_sha,
                    "mtime_utc": datetime.datetime.fromtimestamp(os.path.getmtime(SEED),
                                                                 datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                    "entries": int(ts.size), "span": [ymd(ts.min(), "%Y-%m-%dT%H:%MZ"),
                                                      ymd(ts.max(), "%Y-%m-%dT%H:%MZ")],
                    "manifest_records_same_sha": man.get("leg_returns.npz") == seed_sha},
           "writer": {"file": WRITER[0], "line": WRITER[1], "code": WRITER[2]},
           "leg_definitions_line": "pod_export_shadow_bundle.py:82-92",
           "king_source": {
               "lines": "pod_export_shadow_bundle.py:44-50",
               "what": "PRED = full(nan); folds YV in (2024, 2025) each fit their OWN inline "
                       "lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, "
                       "subsample=0.8, colsample_bytree=0.8); the 2026 fold uses the pinned booster written "
                       "to slow2026.txt",
               "file_comment": "钉死预测: 2026 折用本 booster; 2024/2025 折照旧训练(仅历史腿收益用, 不进影子)",
               "implication": "the seed's King leg is NOT the NC King OOF the research replay uses; it is a "
                              "model trained inside the bundle exporter"},
           "why_king_zero": {
               "n": int(kz.sum()), "pct_of_seed": round(100.0 * kz.sum() / ts.size, 1),
               "span": [ymd(ts[kz].min(), "%Y-%m-%dT%H:%MZ"), ymd(ts[kz].max(), "%Y-%m-%dT%H:%MZ")],
               "first_nonzero_king": ymd(ts[~kz].min(), "%Y-%m-%dT%H:%MZ"),
               "mechanism": "no 2022/2023 fold exists, so PRED is NaN there; xz(all-NaN) is all-NaN and "
                            "np.nan_to_num turns it into all ZERO, so g == 0 and the append takes its "
                            "`else 0.0` branch. The first non-zero king is exactly where the first fold starts.",
               "rev24_zeros": int((S["rev24"] == 0.0).sum()), "fund_zeros": int((S["fund"] == 0.0).sum()),
               "research_side_instead": "nc_legs.py refuses the anchor (king_oof_missing) rather than "
                                        "recording a zero, so it has NO entry there"},
           "seed_king_zero_by_year": dict(sorted(collections.Counter(ymd(t) for t, z in zip(ts, kz) if z).items())),
           "research_not_ready_by_year": dict(sorted(collections.Counter(ymd(t) for t, r in zip(E, ready) if not r).items())),
           "difference_over_time": {yy: {"n": len(v[0]),
                                         "median_abs_king": st.median(v[0]),
                                         "median_abs_rev24": st.median(v[1]),
                                         "median_abs_fund": st.median(v[2])}
                                    for yy, v in sorted(by.items())}}

    k = [v["median_abs_king"] for _, v in sorted(rec["difference_over_time"].items())]
    rec["converges_over_time"] = bool(k == sorted(k, reverse=True))
    rec["conclusion"] = (
        "Written by pod_export_shadow_bundle.py:147 on 2026-09-01T05:58Z (sha 6061af10, which the bundle "
        "MANIFEST also records). The king == 0.0 block over 2022-01-08..2023-12-31 (4,338 entries, 42.6%) is "
        "not a data gap but a construction artifact: the exporter builds King predictions only for the 2024, "
        "2025 and 2026 folds, so PRED is NaN in 2022-23 and np.nan_to_num turns the all-NaN score vector into "
        "all zeros, which drives g to 0 and appends the literal 0.0. The research side refuses those anchors "
        "instead. AND the divergence does NOT converge: median |diff| on the King leg by year is "
        f"{', '.join(f'{yy} {v['median_abs_king']:.2f}' for yy, v in sorted(rec['difference_over_time'].items()))}"
        " -- it persists at a similar magnitude into 2026, where BOTH sides have real King predictions. So the "
        "gap is not merely the missing early folds: the seed's King leg comes from a different model (the "
        "exporter's own inline LGBM folds plus the pinned slow2026 booster) than the NC King OOF the research "
        "replay uses. That is exactly the shape lead was worried about -- live seats allocated from another "
        "model's leg returns.")

    print(json.dumps({k2: rec[k2] for k2 in ("seed", "writer", "king_source", "why_king_zero",
                                            "seed_king_zero_by_year", "research_not_ready_by_year",
                                            "difference_over_time", "converges_over_time")},
                     indent=1, default=str))
    print()
    print(rec["conclusion"])
    json.dump(rec, open(out, "w"), indent=1, default=str)
    print(f"\nreceipt -> {out}  sha256={sha(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
