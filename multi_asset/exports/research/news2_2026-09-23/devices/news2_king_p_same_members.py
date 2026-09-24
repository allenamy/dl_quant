#!/usr/bin/env python3
"""news2_king_p_same_members.py -- does the KZ leg difference come from P, or from members / xz?

Lead's item A, plus the numeric upper bound that replaces a retracted claim.

RETRACTED AND REPLACED. I earlier reported "the legs code contributes <=0.02" by subtracting the
King-OOF spearman from the KZ spearman. That subtraction was invalid: the two were computed on
DIFFERENT position sets (KZ on member positions, King OOF on all finite positions). Two numbers from
different populations cannot be differenced. This device puts BOTH on the SAME positions -- the same
anchors and the same members -- and differences them per anchor, which is a valid paired contrast and
yields a real upper bound.

POSITION SET, per anchor: positions where both sides' KZ is finite and non-zero (i.e. both put a member
there) AND both sides' P is finite. Identical set for the P contrast and the KZ contrast, so the
per-anchor difference isolates what xz + the member/base handling do on top of P.

READ-ONLY. No producer, no exchange, no GPU. The researcher tree is opened read-only.

NOT MEASURED (named):
  - which King is better. Agreement is not skill; that is KING_IC_HEADTOHEAD.
  - why the two P arrays differ (features vs training recipe). That is the next step.
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


def sp(x, y):
    """within-anchor spearman on the given positions"""
    if x.size < 5:
        return None
    a = np.argsort(np.argsort(x)).astype(np.float64)
    b = np.argsort(np.argsort(y)).astype(np.float64)
    sa, sb = a.std(), b.std()
    if sa < 1e-15 or sb < 1e-15:
        return None
    return float(((a - a.mean()) * (b - b.mean())).mean() / (sa * sb))


def q(v, p):
    v = np.array([x for x in v if x is not None], np.float64)
    return float(np.percentile(v, p)) if v.size else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--researcher-king", required=True)
    ap.add_argument("--nc-king", required=True)
    ap.add_argument("--researcher-legs", required=True)
    ap.add_argument("--nc-legs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__,
           "status": "AGREEMENT_ON_ONE_POSITION_SET_NOT_SKILL",
           "replaces": ("the retracted '<=0.02' claim, which differenced two spearmans computed on "
                        "different position sets"),
           "inputs": {k: {"path": p, "sha256": sha(p)} for k, p in
                      (("researcher_king", a.researcher_king), ("nc_king", a.nc_king),
                       ("researcher_legs", a.researcher_legs), ("nc_legs", a.nc_legs))}}

    RK, NK = np.load(a.researcher_king, allow_pickle=False), np.load(a.nc_king, allow_pickle=False)
    RG, NG = np.load(a.researcher_legs, allow_pickle=False), np.load(a.nc_legs, allow_pickle=False)

    axes = [RK["symbols"], NK["symbols"], RG["symbols"], NG["symbols"]]
    same = all(axes[0].shape == v.shape and bool((axes[0] == v).all()) for v in axes)
    rec["symbol_axis_identical"] = same
    if not same:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "symbol axes differ across the four inputs"
        json.dump(rec, open(a.out, "w"), indent=2); print("KING_P_SAME_MEMBERS VERDICT=UNAVAILABLE"); return 2

    RP, NP = np.asarray(RK["P"]), np.asarray(NK["P"])
    RZ, NZ = np.asarray(RG["KZ"]), np.asarray(NG["KZ"])
    rr, nn = np.asarray(RG["ready"]), np.asarray(NG["ready"])
    rkt, nkt = RK["E_ts"].astype(np.int64), NK["E_ts"].astype(np.int64)
    rgt, ngt = RG["E_ts"].astype(np.int64), NG["E_ts"].astype(np.int64)
    rk = {int(t): i for i, t in enumerate(rkt)}
    nk = {int(t): i for i, t in enumerate(nkt)}
    rg = {int(t): i for i, t in enumerate(rgt)}
    shared = [(int(t), rk[int(t)], nk[int(t)], rg[int(t)], i)
              for i, t in enumerate(ngt) if int(t) in rk and int(t) in nk and int(t) in rg]
    rec["n_shared_anchors"] = len(shared)

    per_year, ctrl_self, ctrl_mut = {}, [], []
    for t, rki, nki, rgi, ngi in shared:
        if not (rr[rgi] and nn[ngi]):
            continue
        mz = (np.isfinite(RZ[rgi]) & (RZ[rgi] != 0) & np.isfinite(NZ[ngi]) & (NZ[ngi] != 0)
              & np.isfinite(RP[rki]) & np.isfinite(NP[nki]))
        if mz.sum() < 5:
            continue
        y = str(datetime.datetime.utcfromtimestamp(t).year)
        d = per_year.setdefault(y, {"anchors": 0, "n_pos": [], "sp_P": [], "sp_KZ": [], "delta": [],
                                    "bitwise_P": 0, "bitwise_KZ": 0})
        xp, yp = RP[rki][mz].astype(np.float64), NP[nki][mz].astype(np.float64)
        xz_, yz_ = RZ[rgi][mz].astype(np.float64), NZ[ngi][mz].astype(np.float64)
        s_p, s_z = sp(xp, yp), sp(xz_, yz_)
        d["anchors"] += 1
        d["n_pos"].append(int(mz.sum()))
        d["sp_P"].append(s_p); d["sp_KZ"].append(s_z)
        if s_p is not None and s_z is not None:
            d["delta"].append(s_p - s_z)
        d["bitwise_P"] += int(np.array_equal(xp, yp))
        d["bitwise_KZ"] += int(np.array_equal(xz_, yz_))
        if len(ctrl_self) < 300:
            ctrl_self.append(sp(xp, xp.copy()))
            w = xp.copy(); w[0], w[-1] = w[-1], w[0]
            ctrl_mut.append(sp(xp, w))

    out = {}
    for y, d in sorted(per_year.items()):
        out[y] = {
            "anchors": d["anchors"],
            "mean_positions_same_members": float(np.mean(d["n_pos"])) if d["n_pos"] else None,
            "P_bitwise_identical_anchors": d["bitwise_P"],
            "P_bitwise_identical_pct": 100.0 * d["bitwise_P"] / d["anchors"] if d["anchors"] else None,
            "KZ_bitwise_identical_anchors": d["bitwise_KZ"],
            "KZ_bitwise_identical_pct": 100.0 * d["bitwise_KZ"] / d["anchors"] if d["anchors"] else None,
            "P_within_anchor_spearman": {"median": q(d["sp_P"], 50), "p10": q(d["sp_P"], 10),
                                         "p90": q(d["sp_P"], 90)},
            "KZ_within_anchor_spearman": {"median": q(d["sp_KZ"], 50), "p10": q(d["sp_KZ"], 10),
                                          "p90": q(d["sp_KZ"], 90)},
            "paired_delta_P_minus_KZ": {"median": q(d["delta"], 50), "p10": q(d["delta"], 10),
                                        "p90": q(d["delta"], 90),
                                        "mean": float(np.mean(d["delta"])) if d["delta"] else None,
                                        "max_abs": float(np.max(np.abs(d["delta"]))) if d["delta"] else None},
        }
    rec["per_year"] = out

    # RED CONTROL: within-anchor self-spearman must be exactly 1.0 (it exercises the same masking and
    # ranking path, and returns None on a degenerate set rather than silently passing); swapping two
    # elements must push it below 1.0.
    cs = np.array([x for x in ctrl_self if x is not None], np.float64)
    cm = np.array([x for x in ctrl_mut if x is not None], np.float64)
    ctrl = {"n_cells": int(cs.size), "self_spearman_min": float(cs.min()) if cs.size else None,
            "self_spearman_max": float(cs.max()) if cs.size else None,
            "mutated_spearman_max": float(cm.max()) if cm.size else None}
    ctrl["baseline_green"] = cs.size > 0 and bool(np.all(np.abs(cs - 1.0) < 1e-12))
    ctrl["mutation_detected"] = cm.size > 0 and bool(np.all(cm < 1.0))
    rec["red_control"] = ctrl

    if not ctrl["baseline_green"]:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "red control: self-spearman was not exactly 1.0"
    elif not ctrl["mutation_detected"]:
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "red control: a swap was not detected"
    else:
        rec["verdict"] = "MEASURED"

    json.dump(rec, open(a.out, "w"), indent=2)
    print(f"KING_P_SAME_MEMBERS VERDICT={rec['verdict']} shared_anchors={len(shared)}")
    print(f"  red control: baseline_green={ctrl['baseline_green']} "
          f"(self spearman in [{ctrl['self_spearman_min']},{ctrl['self_spearman_max']}]) "
          f"mutation_detected={ctrl['mutation_detected']} (max mutated {ctrl['mutated_spearman_max']})")
    print("  same anchors, SAME MEMBERS -- within-anchor spearman (median / p10):")
    for y, d in out.items():
        p_, z_, dl = d["P_within_anchor_spearman"], d["KZ_within_anchor_spearman"], d["paired_delta_P_minus_KZ"]
        print(f"   {y}  n={d['anchors']:5d} pos={d['mean_positions_same_members']:.0f}  "
              f"P: {p_['median']:.4f} / {p_['p10']:.4f}   KZ: {z_['median']:.4f} / {z_['p10']:.4f}   "
              f"Δ(P−KZ) med={dl['median']:+.5f} p90={dl['p90']:+.5f} max|Δ|={dl['max_abs']:.5f}")
    print("  bitwise-identical anchors (P / KZ):")
    for y, d in out.items():
        print(f"   {y}  P {d['P_bitwise_identical_anchors']:5d} ({d['P_bitwise_identical_pct']:5.2f}%)   "
              f"KZ {d['KZ_bitwise_identical_anchors']:5d} ({d['KZ_bitwise_identical_pct']:5.2f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
