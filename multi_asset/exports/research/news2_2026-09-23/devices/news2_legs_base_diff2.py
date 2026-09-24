#!/usr/bin/env python3
"""news2_legs_base_diff2.py -- NC vs researcher-NEW: the FUNDING RANK BASE, compared on both sides' own recorded arrays.

WHY v2: v1 tried to rebuild the researcher's `funding` argument from NC's own funding state
(`R.I.funding(A)`), and crashed because `ema.get(s)` returns a dict, not a scalar. Rebuilding it was
the wrong move anyway: it would have compared NC's base against an object I constructed, not against
the researcher's. The researcher delivered the array itself -- funding_state.npz carries `ema` and the
full-width `legal` -- and that file's sha is the one recorded as an INPUT in TARGET_RECEIPT_s42.json,
so it is the exact array that fed their combo.

DEFINITIONS, each taken verbatim from the side that owns it:
  researcher base at anchor A : np.flatnonzero(legal[A] & np.isfinite(ema[A]))   (combo_legs.py L37)
  NC base at anchor A         : np.flatnonzero(np.isfinite(base_val[A]))         (nc_legs.py L65)

READ-ONLY. Touches no producer, no exchange, no GPU. The researcher tree is opened read-only.

NOT MEASURED (named, not silently omitted):
  - whether a differing base CHANGES the leg values. This device compares SET MEMBERSHIP only.
    xz_in_base ranks within the base, so a base difference is necessary-not-sufficient for a leg
    difference; the leg comparison is a separate device.
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


def year(ts):
    return datetime.datetime.utcfromtimestamp(int(ts)).year


def base_sets(legal, ema, base_val, ri, ni):
    res = np.flatnonzero(legal[ri] & np.isfinite(ema[ri]))
    nc = np.flatnonzero(np.isfinite(base_val[ni]))
    return set(res.tolist()), set(nc.tolist())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--researcher", required=True)
    ap.add_argument("--nc-features", required=True)
    ap.add_argument("--nc-legs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {
        "device": os.path.basename(SELF),
        "self_sha256": sha(SELF),
        "argv": sys.argv[1:],
        "cwd": os.getcwd(),
        "python": sys.executable,
        "numpy": np.__version__,
        "inputs": {},
        "status": "BASE_SET_MEMBERSHIP_ONLY_NOT_LEG_VALUES",
    }
    for k, p in (("researcher_funding_state", a.researcher), ("nc_features", a.nc_features), ("nc_legs", a.nc_legs)):
        rec["inputs"][k] = {"path": p, "sha256": sha(p)}

    R = np.load(a.researcher, allow_pickle=False)
    F = np.load(a.nc_features, allow_pickle=False)
    L = np.load(a.nc_legs, allow_pickle=False)

    r_sym, n_sym = R["symbols"], F["symbols"]
    # The whole comparison is by COLUMN INDEX, so a differing symbol axis would silently compare
    # different names. Assert it rather than trust the shared length 829.
    same_axis = r_sym.shape == n_sym.shape and bool((r_sym == n_sym).all())
    rec["symbol_axis_identical"] = same_axis
    rec["n_symbols"] = {"researcher": int(r_sym.shape[0]), "nc": int(n_sym.shape[0])}
    if not same_axis:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = "symbol axes differ; a by-index comparison would compare different names"
        if r_sym.shape == n_sym.shape:
            d = np.flatnonzero(r_sym != n_sym)
            rec["first_differing_columns"] = [
                {"col": int(j), "researcher": str(r_sym[j]), "nc": str(n_sym[j])} for j in d[:10]
            ]
        json.dump(rec, open(a.out, "w"), indent=2)
        print("BASE_DIFF VERDICT=UNAVAILABLE symbol axes differ")
        return 2

    r_ts, n_ts = R["E_ts"].astype(np.int64), L["E_ts"].astype(np.int64)
    ema, legal, base_val = R["ema"], R["legal"], F["base_val"]
    rec["n_anchors"] = {"researcher": int(r_ts.size), "nc": int(n_ts.size)}

    r_pos = {int(t): i for i, t in enumerate(r_ts)}
    shared = [(r_pos[int(t)], i, int(t)) for i, t in enumerate(n_ts) if int(t) in r_pos]
    rec["n_shared_anchors"] = len(shared)
    rec["n_nc_only"] = int(n_ts.size) - len(shared)
    rec["n_researcher_only"] = int(r_ts.size) - len(shared)
    if not shared:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = "no shared anchors"
        json.dump(rec, open(a.out, "w"), indent=2)
        print("BASE_DIFF VERDICT=UNAVAILABLE no shared anchors")
        return 2

    per_year, rows = {}, []
    for ri, ni, t in shared:
        sres, snc = base_sets(legal, ema, base_val, ri, ni)
        only_r, only_n = len(sres - snc), len(snc - sres)
        y = str(year(t))
        d = per_year.setdefault(y, {"anchors": 0, "identical": 0, "sym_diff_total": 0,
                                    "only_researcher_total": 0, "only_nc_total": 0,
                                    "n_res_total": 0, "n_nc_total": 0, "max_sym_diff": 0})
        d["anchors"] += 1
        d["identical"] += int(only_r == 0 and only_n == 0)
        d["sym_diff_total"] += only_r + only_n
        d["only_researcher_total"] += only_r
        d["only_nc_total"] += only_n
        d["n_res_total"] += len(sres)
        d["n_nc_total"] += len(snc)
        d["max_sym_diff"] = max(d["max_sym_diff"], only_r + only_n)
        rows.append((t, len(sres), len(snc), only_r, only_n))

    for y, d in per_year.items():
        d["mean_sym_diff"] = d["sym_diff_total"] / d["anchors"]
        d["mean_n_researcher_base"] = d["n_res_total"] / d["anchors"]
        d["mean_n_nc_base"] = d["n_nc_total"] / d["anchors"]
        d["pct_anchors_identical"] = 100.0 * d["identical"] / d["anchors"]
    rec["per_year"] = dict(sorted(per_year.items()))

    tot = sum(d["anchors"] for d in per_year.values())
    ident = sum(d["identical"] for d in per_year.values())
    rec["overall"] = {
        "anchors": tot,
        "identical": ident,
        "pct_identical": 100.0 * ident / tot,
        "mean_sym_diff": sum(d["sym_diff_total"] for d in per_year.values()) / tot,
        "only_researcher_total": sum(d["only_researcher_total"] for d in per_year.values()),
        "only_nc_total": sum(d["only_nc_total"] for d in per_year.values()),
    }

    # RED CONTROL. A zero symmetric difference is only informative if this comparison can produce a
    # non-zero one, so "compare a set to itself" is not a control -- it is 0 by construction and
    # cannot fail. The three cells below can each fail:
    #   mutation : drop one element from NC's base; the SAME expression must then report exactly 1.
    #   shifted  : NC base vs the NEXT anchor's NC base must be > 0 on real data (resolution).
    #   nonempty : bases must not be empty, or every difference is 0 for an uninteresting reason.
    ctrl = {"mutation_detected": 0, "mutation_wrong_count": 0, "shifted_nonzero_anchors": 0,
            "empty_base_anchors": 0, "checked": 0}
    for ri, ni, t in shared[: min(200, len(shared))]:
        _, snc = base_sets(legal, ema, base_val, ri, ni)
        ctrl["checked"] += 1
        if not snc:
            ctrl["empty_base_anchors"] += 1
            continue
        mut = set(snc)
        mut.discard(next(iter(snc)))
        d = len(snc - mut) + len(mut - snc)
        if d:
            ctrl["mutation_detected"] += 1
        if d != 1:
            ctrl["mutation_wrong_count"] += 1
        if ni + 1 < base_val.shape[0]:
            nxt = set(np.flatnonzero(np.isfinite(base_val[ni + 1])).tolist())
            if len(snc - nxt) + len(nxt - snc):
                ctrl["shifted_nonzero_anchors"] += 1
    n_ok = ctrl["checked"] - ctrl["empty_base_anchors"]
    ctrl["baseline_green"] = n_ok > 0 and ctrl["mutation_detected"] == n_ok and ctrl["mutation_wrong_count"] == 0
    ctrl["can_detect_a_difference"] = ctrl["shifted_nonzero_anchors"] > 0
    rec["red_control"] = ctrl

    if not ctrl["baseline_green"]:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = "red control: a set compared against itself differed; the comparison is broken"
    elif not ctrl["can_detect_a_difference"]:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = "red control: adjacent anchors also showed zero difference; no resolution"
    else:
        rec["verdict"] = "MEASURED"

    rows.sort(key=lambda r: -(r[3] + r[4]))
    rec["worst_20_anchors"] = [
        {"anchor": int(t), "utc": datetime.datetime.utcfromtimestamp(int(t)).strftime("%Y-%m-%dT%H:%MZ"),
         "n_researcher_base": nr, "n_nc_base": nn, "only_researcher": orr, "only_nc": onc}
        for t, nr, nn, orr, onc in rows[:20]
    ]
    json.dump(rec, open(a.out, "w"), indent=2)

    o = rec["overall"]
    print(f"BASE_DIFF VERDICT={rec['verdict']} shared={o['anchors']} identical={o['identical']} "
          f"({o['pct_identical']:.2f}%) mean_sym_diff={o['mean_sym_diff']:.3f} "
          f"only_researcher={o['only_researcher_total']} only_nc={o['only_nc_total']}")
    print(f"  red control: baseline_green={ctrl['baseline_green']} "
          f"can_detect={ctrl['can_detect_a_difference']} (checked {ctrl['checked']})")
    for y, d in rec["per_year"].items():
        print(f"   {y}  anchors={d['anchors']:5d}  identical={d['identical']:5d} "
              f"({d['pct_anchors_identical']:5.1f}%)  mean_sym_diff={d['mean_sym_diff']:7.3f}  "
              f"mean_base res={d['mean_n_researcher_base']:6.1f} nc={d['mean_n_nc_base']:6.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
