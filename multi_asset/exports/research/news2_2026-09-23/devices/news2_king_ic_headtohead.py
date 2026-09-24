#!/usr/bin/env python3
"""news2_king_ic_headtohead.py -- whose score has more skill: NC's or the researcher-NEW's?

The leg comparison established WHICH input differs (the king leg: pearson 0.76-0.90, zero anchors
bitwise identical). It cannot say which side is better, because agreement is not skill. This device
scores both sides against the SAME realised return and reports the cross-sectional rank-IC per anchor.

CALIBER, bound to the file rather than to a variable name (E-0904-F / KB-05):
  the target is the researcher's dlw_targets.npz `y4s`, whose meta records
  target_window = "(E,E+48] raw compounded; all closes observed", built from
  price_full_raw_x0918r.npy -- the RAW price panel, NOT the +-0.30-clipped 5m return cache.
  The identical array scores both sides, so the head-to-head is internally caliber-consistent.
  This device does NOT re-derive the v4 accounting meta and does not claim to be the book-layer caliber.

TWO POSITION SETS, both reported, because they answer different questions:
  intersection : positions both sides scored. The fair head-to-head -- no member-set confound.
  own          : each side's own positions. What each side actually ranked.

RED CONTROL: a within-anchor shuffle of the score must collapse the IC towards 0. If it does not, the
IC is not measuring what it claims and the device reports UNAVAILABLE rather than a number.

NOT MEASURED (named):
  - the book-layer consequence. Rank-IC is a score-layer statistic; this project has five filed cases
    of score-layer admission not surviving the book layer ("排序 != 净额").
  - fees, slippage, capacity, turnover.
  - why one side ranks better.
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


def rank(v):
    return np.argsort(np.argsort(v)).astype(np.float64)


def rank_ic(s, r):
    if s.size < 5:
        return None
    a, b = rank(s), rank(r)
    sa, sb = a.std(), b.std()
    if sa < 1e-15 or sb < 1e-15:
        return None
    return float(((a - a.mean()) * (b - b.mean())).mean() / (sa * sb))


def summarise(vals):
    v = np.array([x for x in vals if x is not None], np.float64)
    if v.size == 0:
        return {"anchors": 0, "mean_ic": None, "note": "no anchor produced an IC"}
    se = v.std(ddof=1) / np.sqrt(v.size) if v.size > 1 else float("nan")
    return {"anchors": int(v.size), "mean_ic": float(v.mean()),
            "std_ic": float(v.std(ddof=1)) if v.size > 1 else None,
            "se_mean": float(se) if v.size > 1 else None,
            "t_stat": float(v.mean() / se) if v.size > 1 and se > 0 else None,
            "frac_positive": float((v > 0).mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--researcher-legs", required=True)
    ap.add_argument("--nc-legs", required=True)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--leg", default="KZ")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__, "leg": a.leg,
           "status": "SCORE_LAYER_RANK_IC_NOT_BOOK_LAYER",
           "inputs": {k: {"path": p, "sha256": sha(p)} for k, p in
                      (("researcher_legs", a.researcher_legs), ("nc_legs", a.nc_legs),
                       ("targets", a.targets))}}

    R, N, T = (np.load(p, allow_pickle=False) for p in (a.researcher_legs, a.nc_legs, a.targets))
    Tm = np.load(a.targets, allow_pickle=True)
    try:
        meta = json.loads(str(Tm["meta_json"]))
        rec["caliber"] = {"target_array": "y4s", "target_window": meta.get("target_window"),
                          "price_source": meta.get("input_paths", {}).get("price")}
    except Exception as e:
        rec["caliber"] = {"target_array": "y4s", "why_unread": f"{type(e).__name__}: {e}"}

    axes = {"researcher_legs": R["symbols"], "nc_legs": N["symbols"], "targets": T["symbols"]}
    same = all(axes["researcher_legs"].shape == v.shape and bool((axes["researcher_legs"] == v).all())
               for v in axes.values())
    rec["symbol_axis_identical"] = same
    if not same:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "symbol axes differ across the three inputs"
        json.dump(rec, open(a.out, "w"), indent=2); print("KING_IC VERDICT=UNAVAILABLE axes"); return 2

    RL, NL, Y = np.asarray(R[a.leg]), np.asarray(N[a.leg]), np.asarray(T["y4s"])
    rr, nn = np.asarray(R["ready"]), np.asarray(N["ready"])
    r_ts, n_ts, t_ts = (x["E_ts"].astype(np.int64) for x in (R, N, T))
    rp = {int(t): i for i, t in enumerate(r_ts)}
    tp = {int(t): i for i, t in enumerate(t_ts)}
    shared = [(rp[int(t)], i, tp[int(t)], int(t)) for i, t in enumerate(n_ts)
              if int(t) in rp and int(t) in tp]
    rec["n_anchors"] = {"researcher": int(r_ts.size), "nc": int(n_ts.size),
                        "targets": int(t_ts.size), "shared": len(shared)}
    if not shared:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "no anchor shared by all three inputs"
        json.dump(rec, open(a.out, "w"), indent=2); print("KING_IC VERDICT=UNAVAILABLE"); return 2

    rng = np.random.default_rng(12345)
    by_year, shuf_all = {}, []
    for ri, ni, ti, t in shared:
        if not (rr[ri] and nn[ni]):
            continue
        y = str(datetime.datetime.utcfromtimestamp(t).year)
        d = by_year.setdefault(y, {"res_inter": [], "nc_inter": [], "res_own": [], "nc_own": [],
                                   "n_inter": [], "n_res_own": [], "n_nc_own": []})
        rv, nv, yv = RL[ri], NL[ni], Y[ti].astype(np.float64)
        fy = np.isfinite(yv)
        rm = np.isfinite(rv) & (rv != 0) & fy
        nm = np.isfinite(nv) & (nv != 0) & fy
        it = rm & nm
        if it.sum() >= 5:
            d["res_inter"].append(rank_ic(rv[it].astype(np.float64), yv[it]))
            d["nc_inter"].append(rank_ic(nv[it].astype(np.float64), yv[it]))
            d["n_inter"].append(int(it.sum()))
            sh = rv[it].astype(np.float64).copy(); rng.shuffle(sh)
            shuf_all.append(rank_ic(sh, yv[it]))
        if rm.sum() >= 5:
            d["res_own"].append(rank_ic(rv[rm].astype(np.float64), yv[rm])); d["n_res_own"].append(int(rm.sum()))
        if nm.sum() >= 5:
            d["nc_own"].append(rank_ic(nv[nm].astype(np.float64), yv[nm])); d["n_nc_own"].append(int(nm.sum()))

    out = {}
    for y, d in sorted(by_year.items()):
        ri_, ni_ = summarise(d["res_inter"]), summarise(d["nc_inter"])
        pair = [x - z for x, z in zip(d["res_inter"], d["nc_inter"]) if x is not None and z is not None]
        out[y] = {
            "intersection": {"researcher": ri_, "nc": ni_, "paired_res_minus_nc": summarise(pair),
                             "mean_positions": float(np.mean(d["n_inter"])) if d["n_inter"] else None},
            "own_positions": {"researcher": summarise(d["res_own"]), "nc": summarise(d["nc_own"]),
                              "mean_positions_researcher": float(np.mean(d["n_res_own"])) if d["n_res_own"] else None,
                              "mean_positions_nc": float(np.mean(d["n_nc_own"])) if d["n_nc_own"] else None},
        }
    rec["per_year"] = out

    sh = summarise(shuf_all)
    real = summarise([v for y in by_year.values() for v in y["res_inter"]])
    ctrl = {"shuffled": sh, "unshuffled_researcher": real}
    ctrl["baseline_green"] = (real["mean_ic"] is not None and real.get("t_stat") is not None
                              and abs(real["t_stat"]) > 3)
    ctrl["shuffle_collapses_ic"] = (sh["mean_ic"] is not None and real["mean_ic"] is not None
                                    and abs(sh["mean_ic"]) < 0.25 * abs(real["mean_ic"]))
    rec["red_control"] = ctrl

    if not ctrl["baseline_green"]:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = ("red control: the unshuffled score has no detectable IC (|t|<=3), so this "
                      "instrument cannot tell the two sides apart on this population")
    elif not ctrl["shuffle_collapses_ic"]:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = "red control: a within-anchor shuffle did not collapse the IC"
    else:
        rec["verdict"] = "MEASURED"

    json.dump(rec, open(a.out, "w"), indent=2)
    print(f"KING_IC VERDICT={rec['verdict']} leg={a.leg} shared={len(shared)}")
    print(f"  caliber: {rec['caliber'].get('target_window')} | price={rec['caliber'].get('price_source')}")
    print(f"  red control: baseline_green={ctrl['baseline_green']} "
          f"(unshuffled mean_ic={real['mean_ic']}, t={real.get('t_stat')})")
    print(f"               shuffle_collapses={ctrl['shuffle_collapses_ic']} "
          f"(shuffled mean_ic={sh['mean_ic']})")
    print("  INTERSECTION positions (fair head-to-head):")
    for y, d in out.items():
        i = d["intersection"]; p = i["paired_res_minus_nc"]
        print(f"   {y}  n={i['researcher']['anchors']:5d}  res={i['researcher']['mean_ic']:+.5f}  "
              f"nc={i['nc']['mean_ic']:+.5f}  paired Δ={p['mean_ic']:+.5f} "
              f"(t={p['t_stat'] if p['t_stat'] is None else round(p['t_stat'],2)})  "
              f"pos={i['mean_positions']:.0f}")
    print("  OWN positions:")
    for y, d in out.items():
        o = d["own_positions"]
        print(f"   {y}  res={o['researcher']['mean_ic']:+.5f} (pos {o['mean_positions_researcher']:.0f})  "
              f"nc={o['nc']['mean_ic']:+.5f} (pos {o['mean_positions_nc']:.0f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
