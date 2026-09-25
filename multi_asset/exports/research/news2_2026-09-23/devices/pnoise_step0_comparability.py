#!/usr/bin/env python3
"""pnoise_step0_comparability.py -- is the rs-perturbation family's change to King as large as NEW's?

Pre-registration: docs/PREREG_gap_carrier_ladder_2026-09-25.md (be4a013a8), step 0.
The criterion is LEAD'S, copied verbatim there; this device only measures what it asks for.

WHY IT MATTERS (lead): tier 2 says "NEW lies outside the random_state family". That only means
something if the family's change to King is at least as large as NEW's change to NC. If rs only nudges
King's P, the family is narrow because the perturbation is small, not because NEW has a mechanism.

ONE POSITION SET FOR EVERY COMPARISON. Lead: "同一位置集!... 不许跨位置集相减". So a single set is
built once and used for all panels:
  per anchor: NC legs KZ finite AND non-zero (the member set)  AND  P finite in EVERY compared panel
Panels compared against rs_0: rs_1..rs_7, NEW (researcher King), refit arm (a), refit arm (b).
NC == rs_0 (verified bitwise), so "NEW vs NC" and "NEW vs rs_0" are the same comparison.

Anchor axes differ (NC/rs 10333 vs researcher 10321) -- aligned by TIMESTAMP, never by position.

NOT MEASURED: whether a larger/smaller King change causes a larger/smaller book difference. This
device sizes the INPUT perturbation only.
"""
import argparse, datetime, hashlib, json, os, sys

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def spearman(x, y):
    if x.size < 5:
        return None
    rx = np.argsort(np.argsort(x)).astype(np.float64)
    ry = np.argsort(np.argsort(y)).astype(np.float64)
    sx, sy = rx.std(), ry.std()
    if sx < 1e-15 or sy < 1e-15:
        return None
    return float(((rx - rx.mean()) * (ry - ry.mean())).mean() / (sx * sy))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--king-oofs-dir", required=True)
    ap.add_argument("--nc-legs", required=True)
    ap.add_argument("--researcher-king", required=True)
    ap.add_argument("--refit-p-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable, "numpy": np.__version__,
           "prereg": "docs/PREREG_gap_carrier_ladder_2026-09-25.md @ be4a013a8 (step 0)",
           "criterion_author": "team-lead (not news2)",
           "status": "SIZES_THE_INPUT_PERTURBATION_NOT_ITS_BOOK_EFFECT",
           "position_set_rule": ("one set for every comparison: NC legs KZ finite AND non-zero, "
                                 "AND P finite in every compared panel"),
           "inputs": {}}

    panels = {}
    for r in range(8):
        p = os.path.join(a.king_oofs_dir, f"KING_OOF_rs{r}.npz")
        panels[f"rs{r}"] = p
    panels["NEW"] = a.researcher_king
    for arm in ("a", "b"):
        panels[f"refit_{arm}"] = os.path.join(a.refit_p_dir, f"REFIT_P_{arm}.npz")
    for k, p in panels.items():
        rec["inputs"][k] = {"path": p, "sha256": sha(p)}
    rec["inputs"]["nc_legs"] = {"path": a.nc_legs, "sha256": sha(a.nc_legs)}

    L = np.load(a.nc_legs, allow_pickle=False)
    KZ = np.asarray(L["KZ"])
    leg_ts = L["E_ts"].astype(np.int64)
    leg_pos = {int(t): i for i, t in enumerate(leg_ts)}
    syms_ref = L["symbols"]

    loaded = {}
    for k, p in panels.items():
        z = np.load(p, allow_pickle=False)
        if not (z["symbols"].shape == syms_ref.shape and bool((z["symbols"] == syms_ref).all())):
            rec["verdict"] = "UNAVAILABLE"
            rec["why"] = f"symbol axis of {k} differs from the legs axis"
            json.dump(rec, open(a.out, "w"), indent=2); print("STEP0 UNAVAILABLE axes"); return 2
        loaded[k] = (np.asarray(z["P"]), {int(t): i for i, t in enumerate(z["E_ts"].astype(np.int64))})

    # anchors present in the legs axis and in EVERY panel
    common_ts = [t for t in leg_ts.tolist()
                 if all(int(t) in loaded[k][1] for k in loaded)]
    rec["n_anchors_common_to_all_panels"] = len(common_ts)

    others = [k for k in loaded if k != "rs0"]
    per_year = {k: {} for k in others}
    npos_year = {}
    for t in common_ts:
        li = leg_pos[int(t)]
        kz = KZ[li]
        m = np.isfinite(kz) & (kz != 0)
        if not m.any():
            continue
        # intersect with finiteness in EVERY panel -> one set
        for k in loaded:
            P, pos = loaded[k]
            m = m & np.isfinite(P[pos[int(t)]])
        if m.sum() < 5:
            continue
        yr = datetime.datetime.utcfromtimestamp(int(t)).year
        npos_year.setdefault(yr, []).append(int(m.sum()))
        base = loaded["rs0"][0][loaded["rs0"][1][int(t)]][m].astype(np.float64)
        for k in others:
            P, pos = loaded[k]
            s = spearman(base, P[pos[int(t)]][m].astype(np.float64))
            if s is not None:
                per_year[k].setdefault(yr, []).append(s)

    years = sorted(npos_year)
    rec["positions_per_year"] = {str(y): {"n_anchors": len(npos_year[y]),
                                          "mean_positions": float(np.mean(npos_year[y]))}
                                 for y in years}
    table = {}
    for k in others:
        table[k] = {str(y): (float(np.median(per_year[k][y])) if per_year[k].get(y) else None)
                    for y in years}
    rec["median_within_anchor_spearman_vs_rs0"] = table

    # ---- lead's frozen reading ----
    PRE = [y for y in years if y in (2023, 2024, 2025)]
    checks = {}
    all_years_hold = True
    for y in PRE:
        new_c = table["NEW"].get(str(y))
        rs_c = [table[f"rs{r}"].get(str(y)) for r in range(1, 8)]
        if new_c is None or any(v is None for v in rs_c):
            checks[str(y)] = {"note": "a correlation is missing; cannot evaluate"}
            all_years_hold = False
            continue
        thr = new_c + 0.05
        holds = all(v >= thr for v in rs_c)
        checks[str(y)] = {"NEW_vs_rs0": new_c, "threshold_NEW_plus_0.05": thr,
                          "rs1_to_rs7": rs_c, "min_rs": min(rs_c),
                          "all_seven_ge_threshold": holds}
        all_years_hold = all_years_hold and holds
    rec["frozen_check"] = {
        "rule": ("lead, verbatim: 若 pre-2026 三年里, 七个 rs_k 的相关全部 >= NEW 对 NC 的相关 + 0.05 "
                 "=> 判「扰动幅度不可比」, 第 2 档降级为「族未覆盖 NEW 的改动量级」, 必须在 RESULT 里加横幅; "
                 "否则第 2 档照立。"),
        "per_year": checks,
        "holds_in_all_three_pre2026_years": all_years_hold,
        "VERDICT": ("PERTURBATION_MAGNITUDE_NOT_COMPARABLE_tier2_downgraded" if all_years_hold
                    else "TIER_2_STANDS")}

    # ---- red control ----
    ctrl = {}
    probe = common_ts[len(common_ts) // 2] if common_ts else None
    if probe is not None:
        li = leg_pos[int(probe)]
        kz = KZ[li]; m = np.isfinite(kz) & (kz != 0)
        for k in loaded:
            P, pos = loaded[k]
            m = m & np.isfinite(P[pos[int(probe)]])
        b = loaded["rs0"][0][loaded["rs0"][1][int(probe)]][m].astype(np.float64)
        ctrl["self_spearman_is_1"] = (abs((spearman(b, b.copy()) or 0) - 1.0) < 1e-12)
        w = b.copy()
        if w.size > 1:
            w[0], w[-1] = w[-1], w[0]
        ctrl["swap_moves_spearman_below_1"] = (spearman(b, w) or 1.0) < 1.0
        ctrl["probe_positions"] = int(m.sum())
    ctrl["position_set_nonempty"] = bool(npos_year)
    ctrl["baseline_green"] = bool(ctrl.get("self_spearman_is_1") and ctrl.get("swap_moves_spearman_below_1")
                                 and ctrl["position_set_nonempty"])
    rec["red_control"] = ctrl
    rec["verdict"] = "MEASURED" if ctrl["baseline_green"] else "UNAVAILABLE"

    json.dump(rec, open(a.out, "w"), indent=2)

    print(f"STEP0_COMPARABILITY VERDICT={rec['verdict']}  anchors_common={len(common_ts)}")
    print(f"  red control: {ctrl}")
    print("  median within-anchor spearman vs rs0 (ONE common position set):")
    hdr = "    panel      " + "".join(f"{y:>9d}" for y in years)
    print(hdr)
    for k in [f"rs{r}" for r in range(1, 8)] + ["refit_a", "refit_b", "NEW"]:
        row = "".join((f"{table[k][str(y)]:9.4f}" if table[k].get(str(y)) is not None else "      n/a")
                      for y in years)
        print(f"    {k:<11s}{row}")
    print("  positions/anchor: " + "  ".join(
        f"{y}:{rec['positions_per_year'][str(y)]['mean_positions']:.0f}" for y in years))
    print(f"\n  FROZEN CHECK -> {rec['frozen_check']['VERDICT']}")
    for y, c in rec["frozen_check"]["per_year"].items():
        if "note" in c:
            print(f"   {y}: {c['note']}"); continue
        print(f"   {y}: NEW={c['NEW_vs_rs0']:.4f}  thr={c['threshold_NEW_plus_0.05']:.4f}  "
              f"min(rs1..7)={c['min_rs']:.4f}  all_seven_ge={c['all_seven_ge_threshold']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
