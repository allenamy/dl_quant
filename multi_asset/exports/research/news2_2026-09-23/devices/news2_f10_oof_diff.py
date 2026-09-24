#!/usr/bin/env python3
"""news2_f10_oof_diff.py -- NC vs researcher-NEW, the F10 OOF SCORE array (P), compared directly.

F10 does not appear in either side's legs file: the legs file carries king / rev24 / fund, and F10
enters one level later, at the shared combo (combo_target.py d7577e82, `raw = .55*kc + .45*fc`, where
fc is built from F10). So localising the NEW <-> NC difference needs this array compared on its own.

Both sides publish the same schema (P, E_ts, symbols), so the comparison is position by position on
the shared anchors, restricted to positions finite on both sides. Positions one side has and the other
does not are counted separately and never averaged into the agreement.

READ-ONLY. No producer, no exchange, no GPU. The researcher tree is opened read-only.

NOT MEASURED (named):
  - which side's F10 is better. This device measures agreement, not skill. A score-layer IC against
    a realised return is a different device.
  - the book-layer consequence of a score difference.
"""
import argparse, datetime, hashlib, json, os, sys

import numpy as np

SELF = os.path.realpath(__file__)


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
    return corr(np.argsort(np.argsort(x)).astype(np.float64),
                np.argsort(np.argsort(y)).astype(np.float64))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--researcher", required=True)
    ap.add_argument("--nc", required=True)
    ap.add_argument("--label", default="F10_OOF",
                    help="what is being compared; goes in the receipt and the verdict line, so a\n                          King comparison is not filed under an F10 name")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__,
           "label": a.label,
           "status": "SCORE_AGREEMENT_NOT_SKILL_NOT_BOOK_LAYER",
           "inputs": {k: {"path": p, "sha256": sha(p)} for k, p in
                      ((f"researcher_{a.label}", a.researcher), (f"nc_{a.label}", a.nc))}}

    R, N = np.load(a.researcher, allow_pickle=False), np.load(a.nc, allow_pickle=False)
    rec["keys"] = {"researcher": list(R.files), "nc": list(N.files)}

    same_axis = R["symbols"].shape == N["symbols"].shape and bool((R["symbols"] == N["symbols"]).all())
    rec["symbol_axis_identical"] = same_axis
    if not same_axis:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = "symbol axes differ; a by-index comparison would compare different names"
        json.dump(rec, open(a.out, "w"), indent=2)
        print(f"{a.label}_DIFF VERDICT=UNAVAILABLE symbol axes differ"); return 2

    RP, NP = np.asarray(R["P"]), np.asarray(N["P"])
    r_ts, n_ts = R["E_ts"].astype(np.int64), N["E_ts"].astype(np.int64)
    r_pos = {int(t): i for i, t in enumerate(r_ts)}
    shared = [(r_pos[int(t)], i, int(t)) for i, t in enumerate(n_ts) if int(t) in r_pos]
    rec["n_anchors"] = {"researcher": int(r_ts.size), "nc": int(n_ts.size), "shared": len(shared)}
    if not shared:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "no shared anchors"
        json.dump(rec, open(a.out, "w"), indent=2); print(f"{a.label}_DIFF VERDICT=UNAVAILABLE"); return 2

    per_year = {}
    for y in sorted({datetime.datetime.utcfromtimestamp(t).year for _, _, t in shared}):
        idx = [(ri, ni) for ri, ni, t in shared if datetime.datetime.utcfromtimestamp(t).year == y]
        xs, ys, only_r, only_n, ident, both_nan = [], [], 0, 0, 0, 0
        for ri, ni in idx:
            rv, nv = RP[ri], NP[ni]
            rm, nm = np.isfinite(rv), np.isfinite(nv)
            only_r += int((rm & ~nm).sum()); only_n += int((nm & ~rm).sum())
            if not rm.any() and not nm.any():
                both_nan += 1
            m = rm & nm
            if m.any():
                xs.append(rv[m].astype(np.float64)); ys.append(nv[m].astype(np.float64))
                if np.array_equal(rv[m], nv[m]):
                    ident += 1
        x = np.concatenate(xs) if xs else np.zeros(0)
        yv = np.concatenate(ys) if ys else np.zeros(0)
        d = np.abs(x - yv) if x.size else np.zeros(0)
        per_year[str(y)] = {
            "anchors": len(idx), "anchors_both_all_nan": both_nan,
            "anchors_bitwise_identical": ident, "positions_both_finite": int(x.size),
            "positions_only_researcher": only_r, "positions_only_nc": only_n,
            "pearson": corr(x, yv), "spearman": spearman(x, yv),
            "mean_abs_diff": float(d.mean()) if d.size else None,
            "p99_abs_diff": float(np.percentile(d, 99)) if d.size else None,
            "std_researcher": float(x.std()) if x.size else None,
            "std_nc": float(yv.std()) if yv.size else None,
        }
    rec["per_year"] = per_year

    # RED CONTROL. self_pearson exercises the same masking path and is None (not silently 1.0) on an
    # empty mask; the mutation cell proves an injected difference is detected.
    # The control must sample anchors that CARRY DATA. Taking the first N shared anchors put the whole
    # control inside 2022, where both sides are all-NaN by construction (no F10 OOF before 2022-07),
    # so it collected nothing and the device reported UNAVAILABLE. Scan until enough anchors with a
    # non-empty overlap are found, and record how many were scanned and used.
    ctrl = {"self_pearson": None, "mutated_pearson": None, "positions_used": 0,
            "anchors_scanned": 0, "anchors_with_overlap": 0}
    xs = []
    for ri, ni, _ in shared:
        ctrl["anchors_scanned"] += 1
        m = np.isfinite(RP[ri]) & np.isfinite(NP[ni])
        if m.any():
            xs.append(NP[ni][m].astype(np.float64))
            ctrl["anchors_with_overlap"] += 1
            if ctrl["anchors_with_overlap"] >= 400:
                break
    if xs:
        v = np.concatenate(xs); ctrl["positions_used"] = int(v.size)
        ctrl["self_pearson"] = corr(v, v.copy())
        w = v.copy(); w[0] += 1.0
        ctrl["mutated_pearson"] = corr(v, w)
    sp, mp = ctrl["self_pearson"], ctrl["mutated_pearson"]
    ctrl["baseline_green"] = sp is not None and abs(sp - 1.0) < 1e-12
    ctrl["mutation_detected"] = mp is not None and sp is not None and mp < sp
    rec["red_control"] = ctrl

    if not ctrl["baseline_green"]:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "red control: self-comparison did not give pearson 1.0"
    elif not ctrl["mutation_detected"]:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "red control: injected difference not detected"
    else:
        rec["verdict"] = "MEASURED"

    json.dump(rec, open(a.out, "w"), indent=2)
    print(f"{a.label}_DIFF VERDICT={rec['verdict']} shared_anchors={len(shared)} "
          f"symbol_axis_identical={same_axis}")
    print(f"  red control: baseline_green={ctrl['baseline_green']} (self_pearson={sp}) "
          f"mutation_detected={ctrl['mutation_detected']} (mutated={mp})")
    for y, d in per_year.items():
        print(f"   {y}  anchors={d['anchors']:5d} both_all_nan={d['anchors_both_all_nan']:5d} "
              f"bitwise_ident={d['anchors_bitwise_identical']:5d}  "
              f"pearson={d['pearson'] if d['pearson'] is None else round(d['pearson'],6)}  "
              f"spearman={d['spearman'] if d['spearman'] is None else round(d['spearman'],6)}  "
              f"mean|d|={d['mean_abs_diff'] if d['mean_abs_diff'] is None else round(d['mean_abs_diff'],6)}  "
              f"onlyR={d['positions_only_researcher']} onlyNC={d['positions_only_nc']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
