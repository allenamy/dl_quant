#!/usr/bin/env python3
"""d10_reseed_expected_impact.py -- expected seat impact of re-seeding the live leg-return history.

lead 2026-09-26, design docs/DESIGN_reseed_live_leg_returns_2026-09-26.md, rulings:
  (A) whole-file rebuild
  (2) replay values wherever the replay covers -- INCLUDING the post-2026-09-01 live-accumulated entries;
      anchors beyond the replay axis end keep the live-accumulated entries; assert timestamp continuity at the
      seam and print 3 entries either side
  (3) no 2022-23 handling needed, but ASSERT all 950 positions are covered by timestamped entries and STOP if
      any is missing -- never fall back to equal weights

READ-ONLY. This device computes what WOULD happen; it writes nothing into the producer tree.

★ POSITION -> ANCHOR IS MEASURED, NOT ASSUMED. leg_returns_live.json holds 950 floats per leg with no
timestamps (shadow_loop_v3.py:427-429). The per-anchor copies under state/snap/<anchor>/ are diffed to find how
many entries each anchor actually appended. Measured over the 50 available steps: 49 appended exactly 1 and ONE
appended 2 (2026-09-21T12:00Z -> 20:00Z, because the 16:00Z snapshot is absent, so two anchors elapsed). So
"the k-th from the end is k anchors back" is false, and anything built on it would be off by one for every
position older than that step. That is the same class of error as the gap being repaired: the live file dropped
its timestamps, which is what let a seeded series and a replayed series be mixed unnoticed.

THE APPEND'S OWN TIMESTAMP CONVENTION, cited: the append at shadow_loop_v3.py:752-766 runs while processing
anchor B and scores the PREVIOUS anchor A over (A, B], so the entry belongs to anchor A = B - 14400. The
research side attributes it the same way (nc_legs.py: LRm[i-1] = ...), which is what makes the two series
comparable at all.

The seat formula is NOT reimplemented differently: it is the frozen one, shadow_loop_v3.py:784-790 ==
nc_legs.py:57-61, with look = 900 from the bundle config.
"""
import collections
import datetime
import hashlib
import json
import os
import statistics as st
import sys

import numpy as np

SNAP = os.path.expanduser("~/wide_shadow/state/snap")
LIVE = os.path.expanduser("~/wide_shadow/state/leg_returns_live.json")
DASH = os.path.expanduser("~/regime_dash/regime_dash.jsonl")
CFG = os.path.expanduser("~/wide_shadow/shadow_bundle/config.json")
LEGS = ("king", "rev24", "fund")
STEP = 14400


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def u(t):
    return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def seats(window):
    """The frozen msharpe seat formula. window = list of (king, rev24, fund) oldest->newest, len == look."""
    r = np.stack([np.array([w[i] for w in window], float) for i in range(3)])
    shp = r.mean(1) / (r.std(1) + 1e-9)
    shp = np.maximum(shp, 0.0)
    # plain floats, not np.float64: with json default=str a numpy scalar would be stored as the STRING
    # "np.float64(0.287)" and a reader could not tell it from a number
    return tuple(float(x) for x in (shp / shp.sum())) if shp.sum() > 0 else (1 / 3, 1 / 3, 1 / 3)


def measure_live_tail():
    """Walk the per-anchor snapshots and assign each appended entry to its anchor (B - 14400)."""
    ts = sorted(int(x) for x in os.listdir(SNAP) if x.isdigit())
    prev = None
    prev_t = None
    assigned = []        # (anchor_of_entry, (king, rev24, fund))
    steps = []
    for t in ts:
        p = os.path.join(SNAP, str(t), "leg_returns_live.json")
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        cur = {lg: [float(x) for x in d[lg]] for lg in LEGS}
        if prev is not None:
            n_new = None
            for k in range(0, 8):
                if k == 0:
                    if cur["king"] == prev["king"]:
                        n_new = 0
                        break
                elif cur["king"][:-k] == prev["king"][k:]:
                    n_new = k
                    break
            if n_new is None:
                raise AssertionError(f"cannot determine the append count for {u(prev_t)} -> {u(t)}; refusing")
            steps.append({"from": u(prev_t), "to": u(t), "appended": n_new})
            # the j-th of n_new appends made while running anchor t belongs to anchor t - (n_new - j) * STEP
            for j in range(n_new):
                a = t - (n_new - 1 - j) * STEP - STEP
                pos = len(cur["king"]) - n_new + j
                assigned.append((a, tuple(cur[lg][pos] for lg in LEGS)))
        prev, prev_t = cur, t
    return assigned, steps, ts


def main():
    wl_slice, out = sys.argv[1], sys.argv[2]
    look = int(json.load(open(CFG))["params"]["msharpe_look"])
    Z = np.load(wl_slice)
    E = Z["E_ts"].astype(np.int64)
    LR = np.asarray(Z["LR"], np.float64)

    replay = [(int(E[i]), tuple(float(LR[i, k]) for k in range(3)))
              for i in range(len(E)) if np.isfinite(LR[i, 0])]
    replay_end = replay[-1][0]

    assigned, steps, snap_ts = measure_live_tail()
    live_after = sorted([(a, v) for a, v in assigned if a > replay_end])
    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "design": "docs/DESIGN_reseed_live_leg_returns_2026-09-26.md",
           "rulings": "lead 2026-09-26: path (A) whole-file rebuild; replay wherever it covers; assert all 950 "
                      "positions timestamped; never fall back to equal weights",
           "read_only": True, "look": look,
           "inputs": {"live": {"path": LIVE, "sha256": sha(LIVE)},
                      "dash": {"path": DASH, "sha256": sha(DASH)},
                      "replay_wl_slice": {"path": wl_slice, "sha256": sha(wl_slice)}},
           "position_to_anchor": {"method": "diff of per-anchor state/snap copies -- MEASURED",
                                 "snapshots": len(snap_ts), "steps": steps,
                                 "append_histogram": dict(collections.Counter(s["appended"] for s in steps)),
                                 "note": "one step appended 2 entries, so a positional assumption would be "
                                         "off by one for every older position"},
           "replay": {"entries": len(replay), "span": [u(replay[0][0]), u(replay_end)]},
           "live_entries_after_replay_end": [{"anchor": u(a), "king": v[0], "rev24": v[1], "fund": v[2]}
                                            for a, v in live_after]}

    # ---- assemble the new series: replay up to its end, then the live tail beyond it
    new = [(a, v) for a, v in replay] + live_after
    new.sort()
    # ruling (3): every one of the last `look + 50` positions must be a timestamped entry
    need = look + 50
    rec["assembled"] = {"total_entries": len(new), "need": need,
                        "all_positions_timestamped": len(new) >= need}
    if len(new) < need:
        rec["verdict"] = "STOP_INSUFFICIENT_TIMESTAMPED_ENTRIES"
        json.dump(rec, open(out, "w"), indent=1, default=str)
        print(json.dumps(rec["assembled"], indent=1))
        sys.stderr.write("STOP per lead ruling (3): fewer than 950 timestamped entries; NOT falling back "
                         "to equal weights.\n")
        return 2
    # seam continuity
    seam_i = next(i for i, (a, _) in enumerate(new) if a > replay_end)
    before = new[max(0, seam_i - 3):seam_i]
    after = new[seam_i:seam_i + 3]
    gaps = [new[i + 1][0] - new[i][0] for i in range(seam_i - 1, min(seam_i + 2, len(new) - 1))]
    rec["seam"] = {"replay_end": u(replay_end),
                   "three_before": [{"anchor": u(a), "vals": v} for a, v in before],
                   "three_after": [{"anchor": u(a), "vals": v} for a, v in after],
                   "gaps_s": gaps, "continuous_4h": all(g == STEP for g in gaps)}
    assert rec["seam"]["continuous_4h"], ("seam is not 4h-continuous", rec["seam"])

    # ---- (1) new seats vs the recorded w3_raw, anchors from 09-24
    dash = {}
    for line in open(DASH, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if "w3_raw" in r:
            dash[int(r["anchor_ts"])] = [float(x) for x in r["w3_raw"]]
    lo = int(datetime.datetime(2026, 9, 24, 0, 0, tzinfo=datetime.timezone.utc).timestamp())
    rows = []
    for A in sorted(a for a in dash if a >= lo):
        win = [v for a, v in new if a < A][-look:]
        if len(win) < look:
            rows.append({"anchor": u(A), "skipped": f"only {len(win)} entries before this anchor"})
            continue
        nw = seats(win)
        lw = dash[A]
        rows.append({"anchor": u(A), "live_w3_raw": lw, "new_w3": [round(x, 6) for x in nw],
                     "d_king": float(nw[0] - lw[0]), "d_rev24": float(nw[1] - lw[1]),
                     "d_fund": float(nw[2] - lw[2])})
    ok = [r for r in rows if "d_king" in r]
    rec["seat_impact_from_2026_09_24"] = {
        "anchors": len(ok), "rows": rows,
        "distribution": {nm: {"mean": st.mean([r[nm] for r in ok]), "median": st.median([r[nm] for r in ok]),
                              "min": min(r[nm] for r in ok), "max": max(r[nm] for r in ok)}
                         for nm in ("d_king", "d_rev24", "d_fund")} if ok else {}}

    print(f"position->anchor MEASURED from {len(snap_ts)} snapshots; appends {rec['position_to_anchor']['append_histogram']}")
    print(f"replay entries {len(replay)} ending {u(replay_end)}; live entries kept beyond it: {len(live_after)}")
    print(f"assembled {len(new)} timestamped entries (need {need}) -> all_positions_timestamped="
          f"{rec['assembled']['all_positions_timestamped']}")
    print(f"seam 4h-continuous: {rec['seam']['continuous_4h']}  gaps {gaps}")
    print("  three before:", [(x['anchor'], [round(y,3) for y in x['vals']]) for x in rec['seam']['three_before']])
    print("  three after :", [(x['anchor'], [round(y,3) for y in x['vals']]) for x in rec['seam']['three_after']])
    print()
    print(f"{'anchor':18s} {'live w3_raw':26s} {'new w3':26s} {'dKing':>8s} {'drev24':>8s} {'dfund':>8s}")
    for r in rows:
        if "d_king" not in r:
            print(f"{r['anchor']:18s} {r['skipped']}")
            continue
        print(f"{r['anchor']:18s} {str([round(x,4) for x in r['live_w3_raw']]):26s} "
              f"{str([round(x,4) for x in r['new_w3']]):26s} "
              f"{r['d_king']:+8.4f} {r['d_rev24']:+8.4f} {r['d_fund']:+8.4f}")
    if ok:
        print()
        for nm in ("d_king", "d_rev24", "d_fund"):
            d = rec["seat_impact_from_2026_09_24"]["distribution"][nm]
            print(f"  {nm:8s} mean {d['mean']:+.4f}  median {d['median']:+.4f}  "
                  f"min {d['min']:+.4f}  max {d['max']:+.4f}")
    rec["verdict"] = "EXPECTED_IMPACT_MEASURED"
    def _no_numpy(o):
        raise TypeError(f"refusing to serialise {type(o).__name__}: convert to a plain float first, or the "
                        f"receipt stores a string that reads like a number ({o!r})")
    json.dump(rec, open(out, "w"), indent=1, default=_no_numpy)
    print(f"\nreceipt -> {out}  sha256={sha(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
