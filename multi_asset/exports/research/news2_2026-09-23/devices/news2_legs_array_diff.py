#!/usr/bin/env python3
"""news2_legs_array_diff.py -- NC vs researcher-NEW, LEG ARRAYS compared directly, leg for leg.

The researcher's f10v2_legs.npz carries the same schema as NC's legs.npz (E_ts, symbols, KZ, Z24, ZFD,
WL, ready, LR), so the three legs and the seat weights can be compared position by position instead of
being inferred from the models that produced them. That is the point of this device: it replaces
"compare the F10 model" and "compare the seats" with "compare the arrays both sides actually fed to the
same shared combo code" (combo_target.py d7577e82, identical on both sides).

Legs are cross-sectional z-scores over the member set, so a position is only comparable where BOTH
sides put a member. Positions are selected as finite-and-nonzero on both sides; the count of positions
each side has that the other does not is reported separately and never averaged into the agreement.

READ-ONLY. No producer, no exchange, no GPU. The researcher tree is opened read-only.

NOT MEASURED (named):
  - WHY a leg differs. This device localises which leg, which year, how much. It does not attribute.
  - the book-layer consequence. A leg difference is necessary-not-sufficient for a return difference.
  - LR (leg return ledger) is reported as a level comparison only; it is a cumulative state, so a
    difference at anchor i carries forward and successive rows are not independent.
"""
import argparse, datetime, hashlib, json, os, sys

import numpy as np

SELF = os.path.realpath(__file__)
LEGS = ("KZ", "Z24", "ZFD")
SEATS = ("king", "rev24", "fund")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def corr(x, y):
    if x.size < 2:
        return None
    sx, sy = x.std(), y.std()
    if sx < 1e-15 or sy < 1e-15:
        return None
    return float(((x - x.mean()) * (y - y.mean())).mean() / (sx * sy))


def spearman(x, y):
    if x.size < 2:
        return None
    rx = np.argsort(np.argsort(x)).astype(np.float64)
    ry = np.argsort(np.argsort(y)).astype(np.float64)
    return corr(rx, ry)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--researcher", required=True)
    ap.add_argument("--nc", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {
        "device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
        "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__,
        "status": "LEG_ARRAY_COMPARISON_NOT_BOOK_LAYER",
        "inputs": {k: {"path": p, "sha256": sha(p)} for k, p in
                   (("researcher_legs", a.researcher), ("nc_legs", a.nc))},
    }

    R = np.load(a.researcher, allow_pickle=False)
    N = np.load(a.nc, allow_pickle=False)

    same_axis = R["symbols"].shape == N["symbols"].shape and bool((R["symbols"] == N["symbols"]).all())
    rec["symbol_axis_identical"] = same_axis
    if not same_axis:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = "symbol axes differ; a by-index comparison would compare different names"
        json.dump(rec, open(a.out, "w"), indent=2)
        print("LEG_ARRAY_DIFF VERDICT=UNAVAILABLE symbol axes differ")
        return 2

    r_ts, n_ts = R["E_ts"].astype(np.int64), N["E_ts"].astype(np.int64)
    r_pos = {int(t): i for i, t in enumerate(r_ts)}
    shared = [(r_pos[int(t)], i, int(t)) for i, t in enumerate(n_ts) if int(t) in r_pos]
    rec["n_anchors"] = {"researcher": int(r_ts.size), "nc": int(n_ts.size), "shared": len(shared)}
    if not shared:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "no shared anchors"
        json.dump(rec, open(a.out, "w"), indent=2); print("LEG_ARRAY_DIFF VERDICT=UNAVAILABLE"); return 2

    rr, nn = R["ready"], N["ready"]
    # Hoist every array out of the loops. np.load on an npz returns a lazy member: `R[leg][ri]`
    # inside a loop re-reads and re-decompresses the WHOLE (n_anchor, n_sym) array on every single
    # access. With ~9k anchors x 3 legs that is ~31k full decompressions and the device never
    # finishes. Each array is read exactly once here.
    RL = {leg: np.asarray(R[leg]) for leg in LEGS}
    NL = {leg: np.asarray(N[leg]) for leg in LEGS}
    RW, NW = np.asarray(R["WL"]), np.asarray(N["WL"])
    years = sorted({datetime.datetime.utcfromtimestamp(t).year for _, _, t in shared})

    # ---- ready agreement ----
    ready_tab = {}
    for y in years:
        sel = [(ri, ni) for ri, ni, t in shared if datetime.datetime.utcfromtimestamp(t).year == y]
        b = sum(1 for ri, ni in sel if rr[ri] and nn[ni])
        ro = sum(1 for ri, ni in sel if rr[ri] and not nn[ni])
        no = sum(1 for ri, ni in sel if nn[ni] and not rr[ri])
        ne = sum(1 for ri, ni in sel if not rr[ri] and not nn[ni])
        ready_tab[str(y)] = {"anchors": len(sel), "both_ready": b, "only_researcher_ready": ro,
                             "only_nc_ready": no, "neither": ne}
    rec["ready_agreement"] = ready_tab

    # ---- per-leg, per-year comparison on anchors where BOTH are ready ----
    legtab = {leg: {} for leg in LEGS}
    for y in years:
        idx = [(ri, ni) for ri, ni, t in shared
               if datetime.datetime.utcfromtimestamp(t).year == y and rr[ri] and nn[ni]]
        for leg in LEGS:
            if not idx:
                legtab[leg][str(y)] = {"anchors": 0, "note": "no anchor with both sides ready"}
                continue
            xs, ys, only_r, only_n, both, ident_anchors = [], [], 0, 0, 0, 0
            for ri, ni in idx:
                rv, nv = RL[leg][ri], NL[leg][ni]
                rm = np.isfinite(rv) & (rv != 0)
                nm = np.isfinite(nv) & (nv != 0)
                only_r += int((rm & ~nm).sum()); only_n += int((nm & ~rm).sum())
                m = rm & nm
                both += int(m.sum())
                if m.any():
                    xs.append(rv[m].astype(np.float64)); ys.append(nv[m].astype(np.float64))
                    if np.array_equal(rv[m], nv[m]):
                        ident_anchors += 1
            x = np.concatenate(xs) if xs else np.zeros(0)
            yv = np.concatenate(ys) if ys else np.zeros(0)
            d = np.abs(x - yv) if x.size else np.zeros(0)
            legtab[leg][str(y)] = {
                "anchors": len(idx), "anchors_bitwise_identical": ident_anchors,
                "positions_both": both, "positions_only_researcher": only_r, "positions_only_nc": only_n,
                "pearson": corr(x, yv), "spearman": spearman(x, yv),
                "mean_abs_diff": float(d.mean()) if d.size else None,
                "p99_abs_diff": float(np.percentile(d, 99)) if d.size else None,
                "max_abs_diff": float(d.max()) if d.size else None,
            }
    rec["per_leg"] = legtab

    # ---- seat weights ----
    seattab = {}
    for y in years:
        idx = [(ri, ni) for ri, ni, t in shared
               if datetime.datetime.utcfromtimestamp(t).year == y and rr[ri] and nn[ni]]
        if not idx:
            seattab[str(y)] = {"anchors": 0}; continue
        rw = np.array([RW[ri] for ri, _ in idx], np.float64)
        nw = np.array([NW[ni] for _, ni in idx], np.float64)
        seattab[str(y)] = {"anchors": len(idx)}
        for j, nm in enumerate(SEATS):
            seattab[str(y)][nm] = {
                "mean_researcher": float(rw[:, j].mean()), "mean_nc": float(nw[:, j].mean()),
                "mean_abs_diff": float(np.abs(rw[:, j] - nw[:, j]).mean()),
                "max_abs_diff": float(np.abs(rw[:, j] - nw[:, j]).max()),
            }
    rec["seat_weights"] = seattab

    # ---- RED CONTROL ----
    # Cell 1 (baseline green): NC's own leg against itself must give pearson exactly 1.0. This is NOT
    #   trivially true here -- it exercises the mask, and returns None on an empty mask, so a broken
    #   mask shows up as None rather than as a silent pass.
    # Cell 2 (mutation): add 1.0 to one selected position; pearson must then be < 1.0 strictly.
    ctrl = {"self_pearson": None, "mutated_pearson": None, "cells": 0, "positions_used": 0}
    probe = [(ri, ni) for ri, ni, t in shared if rr[ri] and nn[ni]][:300]
    if probe:
        xs = []
        for ri, ni in probe:
            nv = NL["KZ"][ni]; rv = RL["KZ"][ri]
            m = np.isfinite(nv) & (nv != 0) & np.isfinite(rv) & (rv != 0)
            if m.any():
                xs.append(nv[m].astype(np.float64))
        if xs:
            v = np.concatenate(xs)
            ctrl["positions_used"] = int(v.size)
            ctrl["self_pearson"] = corr(v, v.copy())
            w = v.copy(); w[0] += 1.0
            ctrl["mutated_pearson"] = corr(v, w)
            ctrl["cells"] = 2
    sp, mp = ctrl["self_pearson"], ctrl["mutated_pearson"]
    ctrl["baseline_green"] = sp is not None and abs(sp - 1.0) < 1e-12
    ctrl["mutation_detected"] = mp is not None and sp is not None and mp < sp
    rec["red_control"] = ctrl

    if not ctrl["baseline_green"]:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "red control: self-comparison did not give pearson 1.0"
    elif not ctrl["mutation_detected"]:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "red control: an injected difference was not detected"
    else:
        rec["verdict"] = "MEASURED"

    json.dump(rec, open(a.out, "w"), indent=2)

    print(f"LEG_ARRAY_DIFF VERDICT={rec['verdict']} shared_anchors={len(shared)} "
          f"symbol_axis_identical={same_axis}")
    print(f"  red control: baseline_green={ctrl['baseline_green']} (self_pearson={sp}) "
          f"mutation_detected={ctrl['mutation_detected']} (mutated={mp})")
    print("  ready agreement (both / only-res / only-nc / neither):")
    for y, d in rec["ready_agreement"].items():
        print(f"   {y}  n={d['anchors']:5d}  {d['both_ready']:5d} / {d['only_researcher_ready']:4d} / "
              f"{d['only_nc_ready']:4d} / {d['neither']:5d}")
    for leg in LEGS:
        print(f"  leg {leg}:")
        for y, d in rec["per_leg"][leg].items():
            if not d.get("anchors"):
                print(f"   {y}  -- {d.get('note','')}"); continue
            print(f"   {y}  anchors={d['anchors']:5d} bitwise_ident={d['anchors_bitwise_identical']:5d}  "
                  f"pearson={d['pearson'] if d['pearson'] is None else round(d['pearson'],6)}  "
                  f"spearman={d['spearman'] if d['spearman'] is None else round(d['spearman'],6)}  "
                  f"mean|d|={d['mean_abs_diff'] if d['mean_abs_diff'] is None else round(d['mean_abs_diff'],5)}  "
                  f"onlyR={d['positions_only_researcher']} onlyNC={d['positions_only_nc']}")
    print("  seat weights (mean researcher -> mean nc, mean|d|):")
    for y, d in rec["seat_weights"].items():
        if not d.get("anchors"):
            continue
        s = "  ".join(f"{nm}: {d[nm]['mean_researcher']:.4f}->{d[nm]['mean_nc']:.4f} "
                      f"(|d|{d[nm]['mean_abs_diff']:.4f})" for nm in SEATS)
        print(f"   {y}  {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
