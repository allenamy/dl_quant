#!/usr/bin/env python3
"""dlarch_cell_retain.py -- shrink one engine cell to a small series, but only after proving that
everything a downstream consumer reads still reproduces from what remains.

WHY (lead ruling 2026-09-25, replacing "dbar bitwise equal => delete"): 8 engine cells x 358 MB plus
the T0 artifacts exceed the ~3 GiB /workspace headroom, so cells must shrink. But a dbar-only equality
check licenses deleting the input of every OTHER consumer:
  * the frozen judge's `load_cell` REQUIRES 32 PATH_*.npz + .json and verifies each npz sha and audits;
  * `maxdd_5m` needs `nav5_main`, and nav5 is 63% of a PATH file's bytes -- "small" and "loses maxdd_5m"
    are the same fact, not two things to trade off;
  * `dstop`/`nstop` (day_stop_flattens / per_name_stops) are not in the 9-key SER_EXT schema either.
So the delete gate covers EVERY quantity the frozen code can produce, not one statistic.

THE FOUR PRECONDITIONS (all must pass before any file is removed):
  1 judge table archived -- path_metrics + summarise for all 5 SEG segments, via the FROZEN functions
    imported (never forked), plus dbar against the control cell
  2 the small series reproduces the frozen `dbar` BITWISE (both the mean and the full daily matrix)
  3 the small series carries `dstop` and `nstop` per-anchor arrays
  4 `maxdd_5m` is precomputed per path per segment as scalars
Residual loss, named in the receipt because it is real and not detectable later: any NEW question that
needs the 5-minute NAV cannot be answered for this cell -- it can only be re-run.

NOTE on precondition 1: the frozen `news_stats.py` main() is NOT a per-cell tool -- its arms are
hardcoded (OLD/OLD_HOLD/NEWS_s42/NEWS_s2027, no T0), it needs ~15 cells at once, its P1 precondition
exits 3 unless OLD reproduces against a certified run, and its P2 requires one common axis. So this
device IMPORTS the frozen functions and initialises BT/DL exactly as main() does. The judge file is not
modified and its sha is asserted.

usage: dlarch_cell_retain.py --cell <dir> --tag <tag_dir> --control-cell <dir> --control-tag <tag>
                            --engine <engine dir> --out <dir> --env-whitelist PATH,HOME,LC_CTYPE
                            [--delete]      # without --delete nothing is removed (verify only)
"""
import argparse
import hashlib
import json
import os
import sys

import numpy as np

SMALL_KEYS = ("r", "pnl", "car", "cst", "unk", "g", "tau", "hold", "halt",   # the 9-key SER_EXT schema
              "dstop", "nstop")                                             # + precondition 3


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_frozen(engine_dir):
    """Import the frozen judge and initialise it the way its own main() does. Never fork it."""
    sys.path.insert(0, engine_dir)
    import news_stats as NS
    import bt_tables as BT
    import bt_driver_lib as DL
    NS.BT, NS.DL = BT, DL
    # replicate main()'s own device-sha guard, plus the judge's own sha
    for f, want in NS.DEV.items():
        got = sha(os.path.join(engine_dir, f))
        assert got == want, f"frozen dependency {f} moved: {got[:16]} != {want[:16]}"
    return NS, BT, DL


def small_series(paths, BT):
    """(32, n) float64 per key, plus the anchor axis. Same schema as SER_EXT_* + dstop/nstop."""
    A = paths[0]["A"]
    out = {"anchors": np.asarray(A, np.int64)}
    for k in SMALL_KEYS:
        out[f"{k}_per_path"] = np.stack([np.asarray(p[k], np.float64) for p in paths])
    return out


def paths_from_small(S):
    """Minimal path dicts that the frozen dbar can consume: it reads only 'A' and 'r'."""
    A = S["anchors"]
    R = S["r_per_path"]
    return [{"A": A, "r": R[k]} for k in range(R.shape[0])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--control-cell", required=True)
    ap.add_argument("--control-tag", required=True)
    ap.add_argument("--engine", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--delete", action="store_true")
    ap.add_argument("--env-whitelist", required=True)
    a = ap.parse_args()
    extra = sorted(set(os.environ) - set(a.env_whitelist.split(",")))
    assert not extra, f"env outside whitelist: {extra}"
    os.makedirs(a.out, exist_ok=True)

    NS, BT, DL = load_frozen(a.engine)
    rec = {"device": "dlarch_cell_retain.py", "self_sha256": sha(os.path.abspath(__file__)),
           "frozen_judge": os.path.join(a.engine, "news_stats.py"),
           "frozen_judge_sha256": sha(os.path.join(a.engine, "news_stats.py")),
           "frozen_deps": {f: s for f, s in NS.DEV.items()},
           "cell": a.cell, "tag": a.tag, "control_cell": a.control_cell, "control_tag": a.control_tag,
           "segments": {k: list(v) for k, v in NS.SEG.items()}, "checks": {}}

    print(f"frozen judge sha {rec['frozen_judge_sha256'][:16]}  segments {list(NS.SEG)}", flush=True)
    pn, facts_n = NS.load_cell(a.cell, a.tag)
    po, facts_o = NS.load_cell(a.control_cell, a.control_tag)
    A = pn[0]["A"]
    assert np.array_equal(po[0]["A"], A), "cell and control are on different axes"
    print(f"loaded {len(pn)} + {len(po)} paths, axis n={len(A)}", flush=True)

    masks = {s: NS.seg_mask(A, x, y) for s, (x, y) in NS.SEG.items()}
    days = {s: NS.full_days(A, masks[s]) for s in NS.SEG}

    # ---- precondition 1: the judge table, from the FROZEN functions ----
    table, dbars = {}, {}
    for s in NS.SEG:
        per = [NS.path_metrics(p, masks[s], days[s]) for p in pn]
        table[s] = {"paths": NS.summarise(per), "mean_path": NS.mean_path_metrics(pn, masks[s], days[s])}
        db, D = NS.dbar(pn, po, masks[s], days[s])
        dbars[s] = {"mean_bps_per_day": float(1e4 * db.mean()), "n_days": int(len(db)), "n_paths": int(D.shape[0])}
    rec["judge_table"] = table
    rec["dbar_vs_control"] = dbars
    rec["checks"]["P1_judge_table_archived"] = {"segments": list(table),
                                                "maxdd_5m_present": all("maxdd_5m" in table[s]["paths"] for s in table)}
    print("P1 judge table: " + " ".join(f"{s}:dbar={dbars[s]['mean_bps_per_day']:+.4f}" for s in NS.SEG), flush=True)

    # ---- precondition 3/4: build the small series + the scalars nav5 is needed for ----
    S = small_series(pn, BT)
    maxdd = {s: [NS.BT.maxdd_5m(p, masks[s]) for p in pn] for s in NS.SEG}
    S_scalars = {f"maxdd_5m_{s}_per_path": np.asarray([np.nan if v is None else float(v) for v in maxdd[s]], np.float64)
                 for s in NS.SEG}
    rec["checks"]["P3_dstop_nstop_present"] = {"dstop_per_path": list(S["dstop_per_path"].shape),
                                               "nstop_per_path": list(S["nstop_per_path"].shape)}
    rec["checks"]["P4_maxdd_5m_scalars"] = {s: {"n_paths": int(len(maxdd[s])),
                                                "n_defined": int(sum(v is not None for v in maxdd[s])),
                                                "path_mean": (None if any(v is None for v in maxdd[s])
                                                              else float(np.mean([float(v) for v in maxdd[s]])))}
                                            for s in NS.SEG}

    # ---- precondition 2: dbar from the small series must be BITWISE identical ----
    pn_small = paths_from_small(S)
    eq = {}
    for s in NS.SEG:
        db_a, D_a = NS.dbar(pn, po, masks[s], days[s])
        db_b, D_b = NS.dbar(pn_small, po, masks[s], days[s])
        same = (db_a.shape == db_b.shape and db_a.tobytes() == db_b.tobytes()
                and D_a.shape == D_b.shape and D_a.tobytes() == D_b.tobytes())
        eq[s] = {"BITWISE_IDENTICAL": bool(same),
                 "mean_sha_path": hashlib.sha256(db_a.tobytes()).hexdigest()[:16],
                 "mean_sha_small": hashlib.sha256(db_b.tobytes()).hexdigest()[:16]}
    rec["checks"]["P2_dbar_bitwise_from_small_series"] = eq
    p2 = all(v["BITWISE_IDENTICAL"] for v in eq.values())
    print("P2 dbar bitwise: " + " ".join(f"{s}={'OK' if eq[s]['BITWISE_IDENTICAL'] else 'DIFFERS'}" for s in NS.SEG), flush=True)

    # Red control: a one-cell perturbation MUST break P2, else P2 is decoration.
    # ★ The perturbation has to land INSIDE the population the judge actually uses. My first version
    # perturbed the first anchor of pre2026 (2023-06-30T04:00Z) -- that day has 5 windows, `full_days`
    # keeps only days with 6, so the judge DISCARDS it and the control silently had no power. A red
    # control must assert its own perturbation is inside the judged sample, not merely inside the mask.
    seg = "pre2026"
    tgt_day = int(days[seg][len(days[seg]) // 2])
    idx = np.flatnonzero(masks[seg] & (((A // NS.DAY) * NS.DAY) == tgt_day))
    assert len(idx) == 6, f"target day {tgt_day} has {len(idx)} windows, expected a full 6"
    assert tgt_day in set(int(d) for d in days[seg]), "target day is not in the judged day set"
    S_bad = {k: (v.copy() if hasattr(v, "copy") else v) for k, v in S.items()}
    S_bad["r_per_path"][0, int(idx[0])] += 1e-9
    db_c, _ = NS.dbar(paths_from_small(S_bad), po, masks[seg], days[seg])
    db_ref, _ = NS.dbar(pn, po, masks[seg], days[seg])
    red = db_c.tobytes() != db_ref.tobytes()
    rec["checks"]["P2_red_control_one_cell_perturbation_breaks_it"] = {
        "fired": bool(red), "segment": seg, "perturbed_anchor_index": int(idx[0]),
        "perturbed_day_utc": tgt_day, "windows_in_that_day": int(len(idx)), "delta": 1e-9,
        "why_this_matters": "the first version perturbed a 5-window day that full_days discards, so it had no power"}
    print(f"P2 red control (1e-9 on one cell inside a full judged day): "
          f"{'PASS' if red else 'FAIL -- P2 is decoration'}", flush=True)

    # ---- write the small series through the verified-write path ----
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import dlarch_safe_io as sio
    payload = {**S, **S_scalars}
    ser = os.path.join(a.out, f"SER_{a.tag}.npz")
    rec["small_series"] = {"path": ser, "keys": sorted(payload),
                           "sha256": sio.save_npz(ser, **payload),
                           "size_mb": round(os.path.getsize(ser) / 1e6, 2)}
    print(f"small series {ser} {rec['small_series']['size_mb']} MB sha {rec['small_series']['sha256'][:16]}", flush=True)

    ok = bool(rec["checks"]["P1_judge_table_archived"]["maxdd_5m_present"] and p2 and red
              and rec["checks"]["P3_dstop_nstop_present"]["dstop_per_path"]
              and all(v["n_defined"] == v["n_paths"] for v in rec["checks"]["P4_maxdd_5m_scalars"].values()))
    rec["ALL_PRECONDITIONS_PASS"] = ok
    rec["RESIDUAL_LOSS"] = ("PATH_*.npz removed: any NEW question needing the 5-minute NAV (nav5_main / "
                            "nav5_sim), dust, or unk_notional cannot be answered for this cell -- it can only "
                            "be re-run. The frozen judge's load_cell can no longer read this cell at all.")

    removed = []
    if a.delete:
        assert ok, "refusing to delete: a precondition failed"
        for k in range(NS.NPATH):
            p = os.path.join(a.cell, f"PATH_{a.tag}_seed_{k:02d}.npz")
            if os.path.exists(p):
                removed.append({"file": os.path.basename(p), "bytes": os.path.getsize(p)})
                os.remove(p)
        print(f"deleted {len(removed)} PATH_*.npz ({sum(x['bytes'] for x in removed)/1e6:.1f} MB); .json kept", flush=True)
    rec["deleted"] = removed
    rec["deleted_note"] = "PATH_*.json and all receipts are kept" if a.delete else "verify-only: nothing removed"

    out = os.path.join(a.out, f"RETAIN_{a.tag}.json")
    rsha = sio.write_json(out, rec)
    print(f"receipt {out} sha {rsha}", flush=True)
    print(f"DLARCH_CELL_RETAIN tag={a.tag} ALL_PRECONDITIONS_PASS={ok} deleted={len(removed)} "
          f"p2_bitwise={p2} red={red}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
