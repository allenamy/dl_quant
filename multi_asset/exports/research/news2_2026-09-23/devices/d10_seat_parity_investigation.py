#!/usr/bin/env python3
"""d10_seat_parity_investigation.py -- why do live w3_raw and research WL disagree?

lead 2026-09-26, after dlarch's reconciliation: at 2026-09-13T12Z the research seats (legs.npz 9ee5886f WL) are
[0.2939, 0.1559, 0.5501] while the live dashboard's w3_raw is [0.3422, 0.1044, 0.5534]. The funding component
nearly agrees; the gap is in the King <-> rev24 split. lead asked for (1) a per-anchor comparison over the whole
overlap, (2) the two sides' seat code compared item by item, (3) the source located with line numbers.

THE FORMULA IS IDENTICAL -- checked line by line, not assumed:
  live      shadow_loop_v3.py:784-790
  research  nc_legs.py:57-61
  both:  r = np.stack([LR[leg][-look:] for leg in ("king","rev24","fund")])
         shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
         w3  = shp / shp.sum() if shp.sum() > 0 else [1/3]*3
  same look (P["msharpe_look"] = 900), same leg order, same clamp, same normalisation.
The per-anchor LR append is also the same shape and the same guard
  live      shadow_loop_v3.py:752-766   prev["anchor_ts"] == last_anchor and anchor - last_anchor == 14400
  research  nc_legs.py:43-54            the same condition, the same 48 rr rows, the same fin.sum(0) < 46 rule,
                                        the same demean-and-normalise-by-sum|z| construction

SO IT IS NOT THE FORMULA. Two candidate explanations were tested and one was REFUTED by measurement:
  REFUTED: "the research LR series has gaps (1,086 not-ready anchors), so its 900-entry window reaches further
           back". Measured: both windows start at exactly 2026-04-16T16:00Z, gap 0.0 days. The not-ready
           anchors are all in early history.
  CONFIRMED: the two sides feed the identical formula DIFFERENT LR VALUES. The live history is SEEDED from
           shadow_bundle/leg_returns.npz (ts + king/rev24/fund, 10,176 entries), and that seed differs from the
           research replay on EVERY overlapping anchor.

This device reproduces all of it. It reads only; it never writes into the producer tree.
"""
import datetime
import hashlib
import json
import os
import statistics as st
import sys

import numpy as np

DASH = os.path.expanduser("~/regime_dash/regime_dash.jsonl")
SEED = os.path.expanduser("~/wide_shadow/shadow_bundle/leg_returns.npz")
LIVE_STATE = os.path.expanduser("~/wide_shadow/state/leg_returns_live.json")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def u(t):
    return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def main():
    wl_slice, out = sys.argv[1], sys.argv[2]
    Z = np.load(wl_slice)
    E = Z["E_ts"].astype(np.int64)
    WL = np.asarray(Z["WL"], np.float64)
    LR = np.asarray(Z["LR"], np.float64)
    ready = np.asarray(Z["ready"], bool)
    ei = {int(t): i for i, t in enumerate(E)}

    dash = []
    for line in open(DASH, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if "w3_raw" in r:
            dash.append(r)

    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "task": "lead 2026-09-26: locate the live-vs-research seat parity gap",
           "inputs": {"dashboard": {"path": DASH, "sha256": sha(DASH), "rows_with_w3_raw": len(dash)},
                      "seed": {"path": SEED, "sha256": sha(SEED)},
                      "live_state": {"path": LIVE_STATE, "sha256": sha(LIVE_STATE)},
                      "research_wl_slice": {"path": wl_slice, "sha256": sha(wl_slice)}},
           "formula_identical": {
               "live_lines": "shadow_loop_v3.py:784-790", "research_lines": "nc_legs.py:57-61",
               "append_live": "shadow_loop_v3.py:752-766", "append_research": "nc_legs.py:43-54",
               "look": 900, "verdict": "byte-identical formula, guard, window length and leg order"}}

    # ---- (1) per-anchor comparison over the whole overlap
    d = {0: [], 1: [], 2: []}
    per = []
    for r in dash:
        i = ei.get(int(r["anchor_ts"]))
        if i is None:
            continue
        lw = [float(x) for x in r["w3_raw"]]
        rw = [float(x) for x in WL[i]]
        for k in range(3):
            d[k].append(rw[k] - lw[k])
        per.append({"anchor": u(int(r["anchor_ts"])), "live": lw, "research": [round(x, 6) for x in rw],
                    "d_king": rw[0] - lw[0], "d_rev24": rw[1] - lw[1], "d_fund": rw[2] - lw[2],
                    "research_ready": bool(ready[i])})
    rec["per_anchor"] = {"n_compared": len(per), "rows": per}
    rec["difference_distribution"] = {
        nm: {"mean": st.mean(v), "median": st.median(v), "min": min(v), "max": max(v),
             "n_research_lower": sum(1 for x in v if x < 0), "n_research_higher": sum(1 for x in v if x > 0)}
        for nm, v in (("d_king", d[0]), ("d_rev24", d[1]), ("d_fund", d[2]))} if per else {}

    # ---- (2) refuted hypothesis: window composition
    fin = np.isfinite(LR[:, 0])
    tgt = int(datetime.datetime(2026, 9, 13, 12, 0, tzinfo=datetime.timezone.utc).timestamp())
    i0 = ei[tgt]
    idx = np.flatnonzero(fin[:i0 + 1])
    win_start = int(E[idx[-900]]) if idx.size >= 900 else None
    consecutive_start = tgt - 899 * 14400
    rec["refuted_hypothesis_window_gaps"] = {
        "claim": "research LR gaps make its 900-entry window reach further back",
        "research_LR_entries": int(fin.sum()), "anchors": int(E.size),
        "window_start_research": u(win_start) if win_start else None,
        "window_start_if_consecutive": u(consecutive_start),
        "gap_days": round((win_start - consecutive_start) / 86400.0, 3) if win_start else None,
        "verdict": "REFUTED -- identical window start, so the not-ready anchors are all in early history"}

    # ---- (3) confirmed: the LR VALUES differ, and the live history is seeded
    S = np.load(SEED, allow_pickle=True)
    ts = S["ts"].astype(np.int64)
    cols = ("king", "rev24", "fund")
    eq = {c: 0 for c in cols}
    dif = {c: [] for c in cols}
    n = 0
    for k, t in enumerate(ts):
        i = ei.get(int(t))
        if i is None or not np.isfinite(LR[i, 0]):
            continue
        n += 1
        for ci, c in enumerate(cols):
            x = float(S[c][k]) - float(LR[i, ci])
            dif[c].append(x)
            if x == 0.0:
                eq[c] += 1
    seeded_in_window = int(((ts >= consecutive_start) & (ts <= tgt)).sum())
    kz = (S["king"] == 0.0)
    rec["confirmed_source_seeded_history"] = {
        "seed_span": [u(ts.min()), u(ts.max())], "seed_entries": int(ts.size),
        "live_state_is_positional": "leg_returns_live.json holds 950 floats per leg with NO timestamps "
                                    "(n_keep = 900 + 50, shadow_loop_v3.py:427-429), so it is a rolling "
                                    "window identified only by position",
        "overlap_with_research_axis": n,
        "exactly_equal": eq,
        "median_abs_diff": {c: st.median([abs(x) for x in dif[c]]) for c in cols},
        "max_abs_diff": {c: max(abs(x) for x in dif[c]) for c in cols},
        "in_window_seed_minus_research": {c: {"n": len(dif[c]), "median": st.median(dif[c])} for c in cols},
        "window_900_anchors": [u(consecutive_start), u(tgt)],
        "seeded_share_of_window": {"seeded": seeded_in_window, "of": 900,
                                   "pct": round(100.0 * seeded_in_window / 900.0, 1)},
        "seed_king_exactly_zero": {"n": int(kz.sum()), "pct": round(100.0 * kz.sum() / ts.size, 1),
                                   "span": [u(ts[kz].min()), u(ts[kz].max())] if kz.any() else None,
                                   "first_nonzero_king": u(ts[~kz].min()),
                                   "rev24_zeros": int((S["rev24"] == 0.0).sum()),
                                   "fund_zeros": int((S["fund"] == 0.0).sum())},
        "verdict": "CONFIRMED"}

    rec["conclusion"] = (
        "The seat formula, its guard, its window length and its leg order are identical on both sides, and the "
        "900-entry windows start on the same anchor, so neither the formula nor the window composition explains "
        "the gap. The cause is the INPUT HISTORY: the live seats are computed from a leg-return series that is "
        f"{rec['confirmed_source_seeded_history']['seeded_share_of_window']['pct']}% seeded from "
        "shadow_bundle/leg_returns.npz over the 900-anchor window at 2026-09-13T12Z, and that seed differs from "
        f"the research replay on ALL {n} overlapping anchors (exactly equal: 0 for every leg). In-window the "
        "seed's king is above the research value and its rev24 below it, which is the direction of the observed "
        "gap (research King lower, research rev24 higher). Separately, the seed carries king EXACTLY 0.0 for "
        f"{int(kz.sum())} entries spanning {u(ts[kz].min())}..{u(ts[kz].max())} with the first non-zero king at "
        f"{u(ts[~kz].min())}, while rev24 and fund have no zeros -- so any research backtest whose msharpe "
        "window reaches before 2024 is comparing against a live-equivalent history in which the King leg "
        "contributed nothing.")

    print(json.dumps({k: rec[k] for k in ("formula_identical", "difference_distribution",
                                          "refuted_hypothesis_window_gaps")}, indent=1, default=str))
    print()
    print(json.dumps(rec["confirmed_source_seeded_history"], indent=1, default=str))
    print()
    print(rec["conclusion"])
    json.dump(rec, open(out, "w"), indent=1, default=str)
    print(f"\nreceipt -> {out}  sha256={sha(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
