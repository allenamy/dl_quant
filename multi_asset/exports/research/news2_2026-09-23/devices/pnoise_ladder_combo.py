#!/usr/bin/env python3
"""pnoise_ladder_combo.py -- step 3 combo-layer substitution: one array swapped, combo code untouched.

Pre-registration: docs/PREREG_gap_carrier_ladder_2026-09-25.md (be4a013a8), step 3. Criteria are LEAD'S.

WHY A SEPARATE DRIVER (and why that is still "combo code unchanged"):
news2_combo.py is the DRIVER; the combo CODE is continuous_combo.evolve + combo_target (1501c9f6 /
d7577e82). The driver asserts that F10's TRAIN_RECEIPT input shas still match on disk, and F10's
recorded inputs include legs.npz -- so substituting any leg array through that driver trips
'training input drift'. Rewriting that receipt to match would be fabricating a receipt, which is not
on the table. So this device is a NEW DRIVER that calls the SAME UNCHANGED evolve with substituted
arrays. Lead's wording is satisfied: "只在组合层替换数组, combo 代码 d7577e82 不改".

The RED CONTROL is what licenses this driver: arm `none` substitutes nothing, and its targets must come
out bitwise identical to the archived TARGETS_NEWS2_s42. If they do not, this driver is not equivalent
to the production one and the whole ladder is UNAVAILABLE.

ARMS (lead's list):
  none      red control     -- nothing substituted
  all_new   positive control-- every array from NEW; must reproduce NEW's archived targets (<=1e-6)
  kz_neg    mutation        -- KZ negated; publish decisions must change
  KZ_res / WL_res / F10_res / FUND_res(ZFD+ready+QV+RN8) / KZWL_res
Each arm is a PIPELINE-UNPRODUCIBLE COMBINATION and only a measuring instrument; never a deployable
version. That sentence belongs beside every number this produces.
"""
import argparse, collections, datetime, hashlib, json, os, pathlib, sys

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--devices", required=True)
    ap.add_argument("--nc-legs", required=True)
    ap.add_argument("--nc-f10", required=True)
    ap.add_argument("--new-legs", required=True)
    ap.add_argument("--new-f10", required=True)
    ap.add_argument("--new-funding", required=True,
                    help="funding_state.npz -- NEW's rn8 AND legal live here (continuous_combo.py:69,78)")
    ap.add_argument("--new-targets", required=True,
                    help="dlw_targets.npz -- NEW's qvk and members live here (continuous_combo.py:78)")
    ap.add_argument("--features", required=True)
    ap.add_argument("--mask", required=True)
    ap.add_argument("--crypto-axis", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--receipt", required=True)
    a = ap.parse_args()

    sys.path.insert(0, a.devices)
    from continuous_combo import evolve                     # UNCHANGED
    from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA
    import continuous_combo as _cc, combo_target as _ct

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable, "numpy": np.__version__,
           "prereg": "docs/PREREG_gap_carrier_ladder_2026-09-25.md @ be4a013a8 (step 3)",
           "criterion_author": "team-lead (not news2)",
           "arm": a.arm,
           "status": "PIPELINE_UNPRODUCIBLE_COMBINATION_MEASURING_INSTRUMENT_ONLY",
           "combo_code": {"continuous_combo": sha(_cc.__file__), "combo_target": sha(_ct.__file__),
                          "modified_by_this_device": False},
           "inputs": {k: {"path": p, "sha256": sha(p)} for k, p in
                      (("nc_legs", a.nc_legs), ("nc_f10", a.nc_f10), ("new_legs", a.new_legs),
                       ("new_f10", a.new_f10), ("new_funding", a.new_funding),
                       ("new_targets", a.new_targets),
                       ("mask", a.mask), ("crypto_axis", a.crypto_axis))}}
    rec["new_input_provenance"] = {
        "read_off": "continuous_combo.py:49 (paths), :61 (handles), :69 (book_legal), :78 (evolve call)",
        "KZ/ZFD/WL/ready": "data/f10v2_legs.npz",
        "P": "f10_s42/F10_OOF.npz",
        "rn8": "data/funding_state.npz[rn8]",
        "legal": "data/funding_state.npz[legal]  -- NEW book_legal = align_universe & fund[legal]",
        "qv": "data/dlw_targets.npz[qvk]",
        "members": "data/dlw_targets.npz[members]",
        "not_in_the_legs_file": ["rn8", "legal", "qv", "members"],
        "caliber_note": ("NC book_legal = align_universe & tradable_mask & crypto (production); NEW = "
                         "align_universe & funding_state[legal]. legal and members are NEW-vs-NC input "
                         "differences that none of lead's five single-swap arms covers; lead's arm list "
                         "is not edited here, the coverage hole is reported to lead.")}

    F = np.load(a.features, allow_pickle=False)
    ncl = np.load(a.nc_legs, allow_pickle=False)
    ncf = np.load(a.nc_f10, allow_pickle=False)
    nwl = np.load(a.new_legs, allow_pickle=False)
    nwf = np.load(a.new_f10, allow_pickle=False)
    nwfund = np.load(a.new_funding, allow_pickle=False)
    nwt = np.load(a.new_targets, allow_pickle=True)

    anchors = F["anchors"].astype(np.int64); syms = F["symbols"]
    assert np.array_equal(ncl["E_ts"].astype(np.int64), anchors)
    assert np.array_equal(ncf["E_ts"].astype(np.int64), anchors)

    # NEW is on its own (shorter) anchor axis -> align onto NC's by TIMESTAMP, never by position
    new_pos = {int(t): i for i, t in enumerate(nwl["E_ts"].astype(np.int64))}
    newf_pos = {int(t): i for i, t in enumerate(nwf["E_ts"].astype(np.int64))}
    rows_new = np.array([new_pos.get(int(t), -1) for t in anchors])
    rows_newf = np.array([newf_pos.get(int(t), -1) for t in anchors])
    for _nm, _z in (("new_funding", nwfund), ("new_targets", nwt), ("new_f10", nwf)):
        assert np.array_equal(_z["E_ts"].astype(np.int64), nwl["E_ts"].astype(np.int64)), \
            ("NEW files not on one anchor axis", _nm)
        assert np.array_equal(_z["symbols"], syms), ("NEW symbol axis differs", _nm)
    assert np.array_equal(rows_newf, rows_new), "NEW F10 axis must equal NEW legs axis"
    rec["new_axis"] = {"nc_anchors": int(anchors.size), "new_anchors": len(new_pos),
                       "nc_anchors_absent_from_new": int((rows_new < 0).sum())}

    def take(nc_arr, new_arr, rows):
        """NEW's array on NC's axis; anchors NEW lacks keep NC's values (counted)."""
        out = np.asarray(nc_arr, np.float64).copy()
        ok = rows >= 0
        out[ok] = np.asarray(new_arr, np.float64)[rows[ok]]
        return out, int((~ok).sum())

    base = {"KZ": np.asarray(ncl["KZ"], np.float64), "ZFD": np.asarray(ncl["ZFD"], np.float64),
            "WL": np.asarray(ncl["WL"], np.float64), "RN8": np.asarray(ncl["RN8"], np.float64),
            "QV": np.asarray(ncl["QV"], np.float64), "ready": np.asarray(ncl["ready"], bool),
            "P": np.asarray(ncf["P"], np.float64)}
    off = F["off"]; members = [F["m"][off[i]:off[i + 1]].astype(np.int64) for i in range(len(anchors))]

    swapped, kept_nc, NEW_LEGAL = [], {}, [False]
    def sub(name, new_arr, rows):
        v, n_kept = take(base[name], new_arr, rows)
        base[name] = v; swapped.append(name); kept_nc[name] = n_kept

    ARM = a.arm
    if ARM == "none":
        pass
    elif ARM == "kz_neg":
        base["KZ"] = -base["KZ"]; swapped.append("KZ(negated)")
    elif ARM == "KZ_res":
        sub("KZ", nwl["KZ"], rows_new)
    elif ARM == "WL_res":
        sub("WL", nwl["WL"], rows_new)
    elif ARM == "F10_res":
        sub("P", nwf["P"], rows_newf)
    elif ARM == "FUND_res":
        # lead's arm is written "FUND_res(ZFD+ready+QV+RN8)" -- copied verbatim, legal deliberately NOT here
        sub("ZFD", nwl["ZFD"], rows_new)
        sub("RN8", nwfund["rn8"], rows_new)
        sub("QV", nwt["qvk"], rows_new)
        rd, nk = take(base["ready"].astype(np.float64), nwl["ready"].astype(np.float64), rows_new)
        base["ready"] = rd > 0.5; swapped.append("ready"); kept_nc["ready"] = nk
    elif ARM == "KZWL_res":
        sub("KZ", nwl["KZ"], rows_new); sub("WL", nwl["WL"], rows_new)
    elif ARM == "all_new":
        for nm in ("KZ", "ZFD", "WL"):
            sub(nm, nwl[nm], rows_new)
        sub("RN8", nwfund["rn8"], rows_new)
        sub("QV", nwt["qvk"], rows_new)
        sub("P", nwf["P"], rows_new)
        # members and legal too: "全部数组换成 NEW 的" means both ends of the ladder really are NC and NEW
        nm_new = list(nwt["members"]); n_sw = 0
        for i in range(len(anchors)):
            if rows_new[i] >= 0:
                members[i] = np.asarray(nm_new[rows_new[i]], np.int64); n_sw += 1
        swapped.append("members"); kept_nc["members"] = int(len(anchors) - n_sw)
        NEW_LEGAL[0] = True
        rd, nk = take(base["ready"].astype(np.float64), nwl["ready"].astype(np.float64), rows_new)
        base["ready"] = rd > 0.5; swapped.append("ready"); kept_nc["ready"] = nk
    else:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = f"unknown arm {ARM}"
        json.dump(rec, open(a.receipt, "w"), indent=2); print("LADDER UNAVAILABLE arm"); return 2
    rec["substituted"] = swapped
    rec["anchors_keeping_nc_values_because_new_lacks_them"] = kept_nc

    # book_legal, built exactly as news2_combo.py does
    mk = np.load(a.mask, allow_pickle=False)
    assert np.array_equal(mk["ts"].astype(np.int64), anchors)
    crypto = np.load(a.crypto_axis, allow_pickle=False)["crypto"]
    cand = mk["mask"] & crypto[None, :]
    rec["legal_source"] = "NC: align_universe & tradable_mask & crypto"
    if NEW_LEGAL[0]:
        nwlegal = np.asarray(nwfund["legal"], bool)
        c2 = cand.copy(); ok = rows_new >= 0
        c2[ok] = nwlegal[rows_new[ok]]
        rec["legal_swap"] = {"nc_true_cells": int(cand.sum()), "new_true_cells": int(c2.sum()),
                             "disagreeing_cells": int((cand != c2).sum()),
                             "anchors_with_any_disagreement": int((cand != c2).any(1).sum())}
        cand = c2
        swapped.append("legal(funding_state)"); kept_nc["legal"] = int((~ok).sum())
        rec["legal_source"] = "NEW: align_universe & funding_state[legal]"
    assert sha(UNIVERSE_PATH) == UNIVERSE_SHA, "universe content identity"
    universe = np.load(UNIVERSE_PATH)
    use = (anchors >= 1672531200) & (anchors <= universe["ts"][-1]); au = anchors[use]
    book_legal = align_universe(au, syms, universe) & cand[use]
    config = json.loads(pathlib.Path(a.config).read_text())
    mem_u = [members[i] for i in np.flatnonzero(use)]
    rec["window"] = {"n_anchors_used": int(use.sum()), "first": int(au[0]), "last": int(au[-1])}

    out = pathlib.Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for policy in ("literal", "scaled_diagnostic"):
        result = evolve(au, base["KZ"][use], base["P"][use], base["ZFD"][use], base["WL"][use],
                        base["RN8"][use], mem_u, base["QV"][use], book_legal, base["ready"][use],
                        config["params"], policy)
        p = out / (policy + ".npz")
        np.savez_compressed(p, E_ts=au, symbols=syms, **result)
        yr = np.array([datetime.datetime.fromtimestamp(int(x), datetime.timezone.utc).year for x in au])
        years = {}
        for y in np.unique(yr):
            m = yr == y
            years[str(int(y))] = {"anchors": int(m.sum()), "publish": int(result["trade_mask"][m].sum()),
                                  "mean_producer_gross": float(np.abs(result["raw"][m]).sum(1).mean())}
        summary[policy] = {"path": str(p), "sha": sha(p),
                           "reasons": dict(collections.Counter(result["reason"])),
                           "publish_total": int(result["trade_mask"].sum()), "years": years}
    rec["policies"] = summary
    rec["verdict"] = "MEASURED"
    rec["limits"] = ["pipeline-unproducible combination; a measuring instrument, never a deployable version",
                     "arms are NOT additive",
                     "this is a NEW DRIVER calling the UNCHANGED evolve; the red control (arm none) is what licenses it"]
    json.dump(rec, open(a.receipt, "w"), indent=2)

    print(f"LADDER arm={ARM} VERDICT={rec['verdict']}  substituted={swapped}")
    print(f"  combo code sha: continuous_combo {rec['combo_code']['continuous_combo'][:12]}  "
          f"combo_target {rec['combo_code']['combo_target'][:12]} (unchanged)")
    for pol, s in summary.items():
        print(f"  {pol:18s} publish={s['publish_total']:5d}  sha={s['sha'][:16]}  reasons={s['reasons']}")
    if kept_nc:
        print(f"  anchors keeping NC values (NEW lacks them): {kept_nc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
