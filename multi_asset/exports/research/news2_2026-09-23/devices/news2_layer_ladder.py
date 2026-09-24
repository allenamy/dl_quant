#!/usr/bin/env python3
"""news2_layer_ladder.py — dlarch step 0 ruler for PREREG docs/PREREG_dl_layer_ladder_2026-09-24.md (06f571a41).

Measures, on the SAME pre-2026 window and with the SAME label, how much money sits at each layer of the
deployed NC book: score (IC) -> leg (unit-gross paper bps) -> pre-chain combination -> chain -> published
target -> publication gate -> engine book. Only two steps are identities and they are asserted per anchor:
  L3  u(zkc_pre) == w0*u(king_rank) + w2*u(fund_rank)     and the f10 twin
  L5  u(raw)     == .55*u(kc) + .45*u(fc)
Everything else is reported SIDE BY SIDE, never as a decomposition: chain/exec_reshape/gate are nonlinear
and stateful, so a linear split there is not identified (受据 counterfactual_rechain_beats_not_identifiable).

Label = dlw_targets.npz y4s, i.e. the label F10's own loss reads (news2_train_f10.py L72/L79/L90). That is
NOT the v4 RAW accounting caliber (CLAUDE.md 更正 KB-05), so L1-L6 are labelled y4s-caliber and are NOT
comparable with L7 (engine paths, accounting caliber). Both are printed; no ratio across that boundary.

READ-ONLY. No GPU, no venue calls, no writes under /dev/shm, no writes to the live trees.

usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B news2_layer_ladder.py \
         PATH,HOME,LC_CTYPE <outdir>
"""
import os, sys, json, time, hashlib, calendar

import numpy as np

W = "/dev/shm/news2_2026-09-23"
NEWSD = "/dev/shm/news_2026-09-23/devices"           # news_stats.py lives here (pinned statistics device)
LAB = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz"
LAB_SHA = "ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62"   # news2_train_f10.py L17
BT_SHA = "892ba66b9e8040ff04caede02272556dec5a71eb4632cbe7a2a13f46bd35f389"
DL_SHA = "ba3bc2610b12a3f0280ff8f03c039ff5c2e81b8c05789183fd2b1acab661bddb"
SEEDS = (42, 2027)
POLICIES = ("literal", "scaled_diagnostic")
MIN_NAMES = 20           # from news2_diag1_score_ic.py
RNG_SEED = 20260924      # from news2_diag1_score_ic.py
H4 = 14400
# verbatim from news_stats.py SEG
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"),
       "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"),
       "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z")}
MAIN = "pre2026"
# N1 thresholds, frozen by the prereg §4
NULL_IC_MAX = 0.005
NULL_LEG_MAX = 0.30
# N4 threshold, frozen by the prereg §4
UNKNOWN_MASS_MAX = 0.02
BT = DL = None


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def log(*a): print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def f10_rank(p):
    """Production caliber F10 score -> rank, combo_target.py L28-29, on ONE anchor's member vector."""
    from scipy.stats import rankdata
    n = len(p); ok = np.isfinite(p); z = np.full(n, np.nan)
    if ok.sum(): z[ok] = rankdata(p[ok]) / max(ok.sum() - 1, 1) - .5
    return z


def leg_return(z, y, rng=None):
    """news_legs.py L51-57 verbatim arithmetic. z, y are one anchor's member vectors. -> bps at unit gross."""
    yy = np.asarray(y, float)
    if rng is not None:                       # N1: destroy the pairing, keep the marginal
        yy = yy.copy(); rng.shuffle(yy)
    okl = np.isfinite(yy)
    zz = np.where(okl, np.nan_to_num(np.asarray(z, float)), 0.0)
    zz = zz - (zz[okl].mean() if okl.sum() else 0.0)
    g = float(np.abs(zz).sum())
    if g <= 1e-9: return 0.0, 0
    return float((zz / g * np.nan_to_num(yy, nan=0.0)).sum() * 1e4), int((np.abs(zz) > 0).sum())


def stats1(v):
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    if not len(v): return {"NO_MEASUREMENT": "0 finite anchors"}
    se = float(v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 1 else float("nan")
    return {"n": int(len(v)), "mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else None,
            "se": se, "t": float(v.mean() / se) if se and np.isfinite(se) and se > 0 else None,
            "median": float(np.median(v)), "frac_positive": float((v > 0).mean())}


def main():
    global BT, DL
    WLIST = set(sys.argv[1].split(","))
    extra = sorted(set(os.environ) - WLIST)
    assert not extra, f"env outside whitelist: {extra}"
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[k] = "2"
    sys.path.insert(0, f"{W}/devices"); sys.path.insert(0, f"{W}/engine"); sys.path.insert(0, NEWSD)
    assert sha(f"{W}/engine/bt_tables.py") == BT_SHA, "bt_tables sha"
    assert sha(f"{W}/engine/bt_driver_lib.py") == DL_SHA, "bt_driver_lib sha"
    import bt_tables as _BT, bt_driver_lib as _DL
    BT, DL = _BT, _DL
    import news_stats as NS
    NS.BT, NS.DL = BT, DL                       # main() would do this; we import the functions only
    from news2_diag1_score_ic import ic_series  # pinned score-layer readout (import, not rewritten)

    rec = {"device": "news2_layer_ladder.py", "self_sha256": sha(os.path.abspath(__file__)),
           "prereg": {"path": "docs/PREREG_dl_layer_ladder_2026-09-24.md", "commit": "06f571a41"},
           "utc_start": iso(time.time()), "caliber": {
               "L1_L6_label": "dlw_targets.npz y4s — the label F10's loss reads; NOT the v4 RAW accounting caliber (KB-05)",
               "L7_label": "engine PATH files, accounting caliber",
               "comparability": "L1-L6 and L7 are NOT comparable; printed side by side, no ratio across the boundary",
               "unit_L2_L6": "bps per anchor per unit gross (sum|z| = 1)", "unit_L7": "mean per-4h-window net return"},
           "imported_devices": {"news2_diag1_score_ic.py": sha(f"{W}/devices/news2_diag1_score_ic.py"),
                                "news_stats.py": sha(f"{NEWSD}/news_stats.py"),
                                "bt_tables.py": BT_SHA, "bt_driver_lib.py": DL_SHA},
           "segments": SEG, "min_names": MIN_NAMES, "rng_seed": RNG_SEED,
           "inputs": {}, "assertions": {}, "seeds": {}, "unavailable": []}

    # ───────────────────────── inputs, sha-asserted ─────────────────────────
    log("hashing inputs (NEWS_FEATURES is 2.9 GB)")
    fpath = f"{W}/work/NEWS_FEATURES.npz"; lpath = f"{W}/work/legs.npz"; kpath = f"{W}/work/king/KING_OOF.npz"
    fsha = sha(fpath); lsha = sha(lpath)
    assert json.load(open(f"{W}/receipts/P2B_FEATURES.json"))["sha256"] == fsha, "features sha != P2B receipt"
    assert json.load(open(f"{W}/receipts/P3_LEGS.json"))["sha256"] == lsha, "legs sha != P3 receipt"
    assert sha(LAB) == LAB_SHA, "label sha != news2_train_f10.py NEWT_SHA"
    rec["inputs"].update({fpath: fsha, lpath: lsha, LAB: LAB_SHA, kpath: sha(kpath)})

    F = np.load(fpath); leg = np.load(lpath); K = np.load(kpath); lab = np.load(LAB, allow_pickle=True)
    a = F["anchors"].astype(np.int64); syms = F["symbols"]
    assert np.array_equal(leg["E_ts"].astype(np.int64), a) and np.array_equal(leg["symbols"], syms)
    assert np.array_equal(K["E_ts"].astype(np.int64), a) and np.array_equal(K["symbols"], syms)
    assert np.all(np.diff(a) == H4), "leg axis not a continuous 4h grid"
    ya = lab["E_ts"].astype(np.int64); Y = lab["y4s"]; assert np.array_equal(lab["symbols"], syms), "label symbol axis"
    off = F["off"]; mm = F["m"].astype(np.int64)
    members = [mm[off[i]:off[i + 1]] for i in range(len(a))]
    KZ = leg["KZ"]; Z24 = leg["Z24"]; ZFD = leg["ZFD"]; WL = leg["WL"]; RN8 = leg["RN8"]; ready = leg["ready"]; LR = leg["LR"]
    iy = np.searchsorted(ya, a); lab_ok = (iy < len(ya)) & (ya[np.minimum(iy, len(ya) - 1)] == a)
    rec["assertions"]["axes"] = {"leg_anchors": int(len(a)), "first": iso(a[0]), "last": iso(a[-1]),
                                 "label_anchors": int(len(ya)), "leg_anchors_with_label": int(lab_ok.sum()),
                                 "ready": int(ready.sum()), "symbols": int(len(syms))}
    log("axes", json.dumps(rec["assertions"]["axes"]))

    masks = {}
    for s, (lo, hi) in SEG.items():
        m = (a >= ts(lo)) & (a <= ts(hi)); assert m.any(), f"empty segment {s}"
        masks[s] = m
    rec["assertions"]["segment_anchor_counts"] = {s: {"anchors": int(masks[s].sum()),
                                                     "ready_and_labelled": int((masks[s] & ready & lab_ok).sum())} for s in SEG}

    # ───────────────────────── L1 score layer (imported readout) ─────────────────────────
    log("L1 score IC")
    SCORES = {"king": K["P"], "f10_s42": None, "f10_s2027": None, "fund_z": ZFD, "rev24_z": Z24}
    f10P = {}
    for sd in SEEDS:
        p = f"{W}/work/f10_s{sd}/F10_OOF.npz"; tr = json.load(open(f"{W}/work/f10_s{sd}/TRAIN_RECEIPT.json"))
        h = sha(p); assert tr["pred_sha256"] == h, f"f10 s{sd} sha != TRAIN_RECEIPT pred_sha256"
        assert set(tr["folds"]) == set(tr["expected_folds"]), f"f10 s{sd} folds incomplete"
        rec["inputs"][p] = h
        z = np.load(p); assert np.array_equal(z["E_ts"].astype(np.int64), a) and np.array_equal(z["symbols"], syms)
        f10P[sd] = z["P"]; SCORES[f"f10_s{sd}"] = z["P"]
    L1 = {}
    for s in SEG:
        rows = np.flatnonzero(masks[s] & ready & lab_ok)
        L1[s] = {"n_anchors_offered": int(len(rows))}
        for name, P in SCORES.items():
            ics, nn, skipped = ic_series(P, Y, rows, iy[rows])
            rng = np.random.default_rng(RNG_SEED)
            nics, _, nskip = ic_series(P, Y, rows, iy[rows], rng=rng)
            L1[s][name] = {"ic": stats1(ics), "n_skipped": int(skipped), "mean_names": float(nn.mean()) if len(nn) else None,
                           "null_ic": stats1(nics), "null_n_skipped": int(nskip)}
        log("L1", s, {k: round(v["ic"]["mean"], 5) for k, v in L1[s].items() if isinstance(v, dict) and "ic" in v})
    rec["L1_score_layer"] = L1

    # ───────────────────────── L2 leg layer + R1 reconciliation ─────────────────────────
    log("L2 leg layer")
    legnames = ("king", "rev24", "fund", "f10_s42", "f10_s2027")
    acc = {s: {k: [] for k in legnames} for s in SEG}
    accnull = {s: {k: [] for k in legnames} for s in SEG}
    nonzero = {s: {k: 0 for k in legnames} for s in SEG}
    repro = {s: {k: [] for k in ("king", "rev24", "fund")} for s in SEG}   # my leg vs archived LR, same anchors
    archived = {s: {k: [] for k in ("king", "rev24", "fund")} for s in SEG}
    rng_null = np.random.default_rng(RNG_SEED)
    rows_all = np.flatnonzero(ready & lab_ok & (masks[MAIN] | masks["2023H2"] | masks["2024"] | masks["2025"]))
    zf_cache = {}
    for i in rows_all:
        m = members[i]; yv = Y[iy[i]][m]
        zs = {"king": KZ[i][m], "rev24": Z24[i][m], "fund": ZFD[i][m]}
        for sd in SEEDS:
            zf = f10_rank(f10P[sd][i][m]); zf_cache[(i, sd)] = zf; zs[f"f10_s{sd}"] = zf
        segs = [s for s in SEG if masks[s][i]]
        for name, z in zs.items():
            v, nz = leg_return(z, yv)
            vn, _ = leg_return(z, yv, rng=rng_null)
            for s in segs:
                acc[s][name].append(v); accnull[s][name].append(vn); nonzero[s][name] += nz
        for li, name in enumerate(("king", "rev24", "fund")):
            if np.isfinite(LR[i, li]):
                for s in segs: repro[s][name].append(acc[s][name][-1]); archived[s][name].append(float(LR[i, li]))
    L2 = {}
    for s in SEG:
        L2[s] = {"n_anchors": len(acc[s]["king"])}
        for name in legnames:
            L2[s][name] = {"leg_bps_per_anchor_unit_gross": stats1(acc[s][name]),
                           "null_control": stats1(accnull[s][name]),
                           "nonzero_cells": nonzero[s][name]}
        R1 = {}
        for name in ("king", "rev24", "fund"):
            x = np.asarray(repro[s][name], float); z = np.asarray(archived[s][name], float)
            ok = np.isfinite(x) & np.isfinite(z)
            R1[name] = {"n": int(ok.sum()),
                        "corr": float(np.corrcoef(x[ok], z[ok])[0, 1]) if ok.sum() > 2 else None,
                        "mean_mine_y4s": float(x[ok].mean()) if ok.sum() else None,
                        "mean_archived_y4v": float(z[ok].mean()) if ok.sum() else None,
                        "sign_agreement": float((np.sign(x[ok]) == np.sign(z[ok])).mean()) if ok.sum() else None}
        L2[s]["R1_reconciliation_vs_archived_LR"] = R1
        log("L2", s, {k: round(L2[s][k]["leg_bps_per_anchor_unit_gross"].get("mean", float("nan")), 4) for k in legnames})
    rec["L2_leg_layer"] = L2

    # ───────────────────────── L3..L6, per seed per policy ─────────────────────────
    for sd in SEEDS:
        tr = json.load(open(f"{W}/work/combo_s{sd}/TARGET_RECEIPT.json"))
        assert tr["seed"] == sd
        srec = {"L3_L5_identities": {}, "policies": {}}
        for pol in POLICIES:
            cp = f"{W}/work/combo_s{sd}/{pol}.npz"; h = sha(cp)
            assert tr["policies"][pol]["sha"] == h, f"combo s{sd} {pol} sha != TARGET_RECEIPT"
            rec["inputs"][cp] = h
            C = np.load(cp); ca = C["E_ts"].astype(np.int64); assert np.array_equal(C["symbols"], syms)
            kc = C["kc"]; fc = C["fc"]; raw = C["raw"]; tm = C["trade_mask"]; reason = C["reason"]
            # map combo rows -> leg rows by TIMESTAMP (three different axes, prereg §7.5)
            ci = np.searchsorted(a, ca); assert np.all(a[ci] == ca), "combo anchor not on leg axis"
            log(f"L3-L6 s{sd} {pol}: combo anchors {len(ca)}")
            out = {"n_combo_anchors": int(len(ca)), "segments": {}}
            worst = {"L3k": 0.0, "L3f": 0.0, "L5": 0.0}
            for s in SEG:
                sel = np.flatnonzero(masks[s][ci] & ready[ci] & lab_ok[ci])
                if not len(sel):
                    out["segments"][s] = {"NO_ANCHORS": True}; continue
                rows = {k: [] for k in ("L3k", "L3k_king", "L3k_fund", "L3k_clamp", "L3f", "L3f_f10", "L3f_fund",
                                        "L3f_clamp", "L4kc", "L4fc", "L5raw", "L5_from_kc", "L5_from_fc",
                                        "gross_raw", "gross_kc", "gross_fc", "gross_zkc", "gross_zfc")}
                unk = {"cells": 0, "mass": 0.0, "gross": 0.0, "anchors": 0}; pubflag = []
                for j in sel:
                    i = ci[j]; m = members[i]; yrow = Y[iy[i]]; yv = np.nan_to_num(yrow, nan=0.0)
                    yfin = np.isfinite(yrow)
                    w = np.array([WL[i, 0], 0.0, WL[i, 2]], float)
                    w = w / w.sum() if w.sum() > 1e-12 else np.array([.5, 0., .5])
                    kr = np.nan_to_num(KZ[i][m].astype(np.float64)); fr = np.nan_to_num(ZFD[i][m].astype(np.float64))
                    zf = np.nan_to_num(zf_cache[(i, sd)].astype(np.float64))
                    ym = yv[m]
                    u_king = float((kr * ym).sum()); u_fund = float((fr * ym).sum()); u_f10 = float((zf * ym).sum())
                    zkc_pre = w[0] * kr + w[2] * fr; zfc_pre = w[0] * zf + w[2] * fr
                    rn = RN8[i][m].astype(np.float64); bad = np.isfinite(rn) & (rn <= -.001)
                    zkc = np.where((zkc_pre < 0) & bad, 0.0, zkc_pre); zfc = np.where((zfc_pre < 0) & bad, 0.0, zfc_pre)
                    u_zkc_pre = float((zkc_pre * ym).sum()); u_zfc_pre = float((zfc_pre * ym).sum())
                    # ---- N2: L3 identities, per anchor ----
                    sk = max(abs(w[0] * u_king), abs(w[2] * u_fund), abs(u_zkc_pre), 1.0)
                    sf = max(abs(w[0] * u_f10), abs(w[2] * u_fund), abs(u_zfc_pre), 1.0)
                    ek = abs(u_zkc_pre - (w[0] * u_king + w[2] * u_fund)) / sk
                    ef = abs(u_zfc_pre - (w[0] * u_f10 + w[2] * u_fund)) / sf
                    worst["L3k"] = max(worst["L3k"], ek); worst["L3f"] = max(worst["L3f"], ef)
                    Dk = float(np.abs(zkc).sum()); Df = float(np.abs(zfc).sum())
                    if Dk > 1e-9:
                        rows["L3k"].append(1e4 * float((zkc * ym).sum()) / Dk)
                        rows["L3k_king"].append(1e4 * w[0] * u_king / Dk); rows["L3k_fund"].append(1e4 * w[2] * u_fund / Dk)
                        rows["L3k_clamp"].append(1e4 * (float((zkc * ym).sum()) - u_zkc_pre) / Dk)
                        rows["gross_zkc"].append(Dk)
                    if Df > 1e-9:
                        rows["L3f"].append(1e4 * float((zfc * ym).sum()) / Df)
                        rows["L3f_f10"].append(1e4 * w[0] * u_f10 / Df); rows["L3f_fund"].append(1e4 * w[2] * u_fund / Df)
                        rows["L3f_clamp"].append(1e4 * (float((zfc * ym).sum()) - u_zfc_pre) / Df)
                        rows["gross_zfc"].append(Df)
                    # ---- L4 / L5 on the stored chain output ----
                    kcv = kc[j]; fcv = fc[j]; rawv = raw[j]
                    bad_cells = (np.abs(rawv) > 1e-9) & ~yfin           # N4: unknown return is not zero
                    if bad_cells.any():
                        unk["anchors"] += 1; unk["cells"] += int(bad_cells.sum())
                        unk["mass"] += float(np.abs(rawv[bad_cells]).sum()); unk["gross"] += float(np.abs(rawv).sum())
                    u_kc = float((kcv * yv).sum()); u_fc = float((fcv * yv).sum()); u_raw = float((rawv * yv).sum())
                    sr = max(abs(.55 * u_kc), abs(.45 * u_fc), abs(u_raw), 1.0)
                    worst["L5"] = max(worst["L5"], abs(u_raw - (.55 * u_kc + .45 * u_fc)) / sr)
                    gk = float(np.abs(kcv).sum()); gf = float(np.abs(fcv).sum()); gr = float(np.abs(rawv).sum())
                    if gk > 1e-9: rows["L4kc"].append(1e4 * u_kc / gk); rows["gross_kc"].append(gk)
                    if gf > 1e-9: rows["L4fc"].append(1e4 * u_fc / gf); rows["gross_fc"].append(gf)
                    if gr > 1e-9:
                        rows["L5raw"].append(1e4 * u_raw / gr); rows["gross_raw"].append(gr)
                        rows["L5_from_kc"].append(1e4 * .55 * u_kc / gr); rows["L5_from_fc"].append(1e4 * .45 * u_fc / gr)
                        pubflag.append(bool(tm[j]))
                sm = masks[s][ci] & ready[ci] & lab_ok[ci]
                pub = tm & sm
                seg = {"n_anchors": int(sm.sum()), "n_published": int(pub.sum()),
                       "publish_rate": float(pub.sum() / max(sm.sum(), 1)),
                       "reason_counts": {str(k): int(v) for k, v in zip(*np.unique(reason[sm], return_counts=True))},
                       "unknown_return_cells": {"anchors": unk["anchors"], "cells": unk["cells"],
                                                "mass_share_of_gross": (unk["mass"] / unk["gross"]) if unk["gross"] > 0 else 0.0}}
                for k, v in rows.items(): seg[k] = stats1(v)
                # L6: the published book's unit-gross paper bps, split by whether the gate let it through.
                # Anchors whose raw gross is 0 carry no book at all and are counted, never folded in as a 0.
                pj = np.asarray(pubflag, bool); rr = np.asarray(rows["L5raw"], float)
                assert len(rr) == len(pj), "L6 split population mismatch"
                seg["L6_zero_gross_anchors_excluded"] = int(sm.sum()) - len(rr)
                seg["L6_L5raw_on_published"] = stats1(rr[pj]) if pj.any() else {"NO_MEASUREMENT": "0 published anchors"}
                seg["L6_L5raw_on_gated_out"] = stats1(rr[~pj]) if (~pj).any() else {"NO_MEASUREMENT": "0 gated-out anchors"}
                out["segments"][s] = seg
            out["identity_worst_rel_err"] = worst
            assert worst["L3k"] <= 1e-9 and worst["L3f"] <= 1e-9, f"L3 identity failed: {worst}"
            assert worst["L5"] <= 1e-9, f"L5 identity failed: {worst}"
            srec["policies"][pol] = out
            srec["L3_L5_identities"][pol] = {"worst_rel_err": worst, "tolerance": 1e-9, "PASS": True}
            # ---- N5 red-capability: the same identity with .40 in place of .45 must go red ----
            j0 = int(np.flatnonzero(masks[MAIN][ci] & ready[ci] & lab_ok[ci] & tm)[0])
            yv0 = np.nan_to_num(Y[iy[ci[j0]]], nan=0.0)
            u_kc0 = float((kc[j0] * yv0).sum()); u_fc0 = float((fc[j0] * yv0).sum()); u_raw0 = float((raw[j0] * yv0).sum())
            s0 = max(abs(.55 * u_kc0), abs(.45 * u_fc0), abs(u_raw0), 1.0)
            base_err = abs(u_raw0 - (.55 * u_kc0 + .45 * u_fc0)) / s0
            mut_err = abs(u_raw0 - (.55 * u_kc0 + .40 * u_fc0)) / s0
            srec["L3_L5_identities"][pol]["N5_red_capability"] = {
                "anchor": iso(ca[j0]), "baseline_rel_err": base_err, "baseline_green": bool(base_err <= 1e-9),
                "mutated_045_to_040_rel_err": mut_err, "mutation_goes_red": bool(mut_err > 1e-9)}
            assert base_err <= 1e-9 and mut_err > 1e-9, "N5 red-capability check vacuous"
            del C, kc, fc, raw
        rec["seeds"][str(sd)] = srec
        log(f"L3-L6 s{sd} done")

    # ───────────────────────── L7 engine book layer (imported readout) ─────────────────────────
    log("L7 engine book layer")
    L7 = {}
    for sd in SEEDS:
        for cell, suf in (("base_scaled", "scaled_rule_raw_UAFE"), ("lit", "lit_rule_raw_UAFE")):
            tag = f"NEWS2_s{sd}_{suf}"; d = f"{W}/runs/{tag}"
            try:
                paths, facts = NS.load_cell(d, tag)
            except Exception as e:
                rec["unavailable"].append({"L7": tag, "why": f"{type(e).__name__}: {e}"}); log("UNAVAILABLE", tag, e); continue
            A = paths[0]["A"]
            per_seg = {}
            for s in SEG:
                m = NS.seg_mask(A, *SEG[s]); days = NS.full_days(A, m)
                per = [NS.path_metrics(p, m, days) for p in paths]
                per_seg[s] = NS.summarise(per)
            L7[f"s{sd}_{cell}"] = {"runs_dir": d, "n_paths": len(paths), "axis": {"first": iso(A[0]), "last": iso(A[-1]), "n": int(len(A))},
                                   "segments": per_seg}
            log("L7", tag, "g pre2026 path_mean", per_seg[MAIN]["g"]["path_mean"])
    rec["L7_book_layer"] = L7

    # ───────────────────────── N1 verdict ─────────────────────────
    n1 = {"IC": [], "LEG": []}
    for s in SEG:
        for name in SCORES:
            v = L1[s][name]["null_ic"].get("mean")
            if v is not None and abs(v) > NULL_IC_MAX: n1["IC"].append(f"{s}/{name}={v:+.5f}")
        for name in legnames:
            v = L2[s][name]["null_control"].get("mean")
            if v is not None and abs(v) > NULL_LEG_MAX: n1["LEG"].append(f"{s}/{name}={v:+.4f}")
    rec["N1_null_control"] = {"ic_threshold": NULL_IC_MAX, "leg_threshold": NULL_LEG_MAX,
                              "ic_breaches": n1["IC"], "leg_breaches": n1["LEG"],
                              "PASS": not n1["IC"] and not n1["LEG"]}
    # ───────────────────────── N4 verdict ─────────────────────────
    n4 = []
    for sd in SEEDS:
        for pol in POLICIES:
            for s in SEG:
                seg = rec["seeds"][str(sd)]["policies"][pol]["segments"][s]
                if "unknown_return_cells" not in seg: continue
                ms = seg["unknown_return_cells"]["mass_share_of_gross"]
                if ms > UNKNOWN_MASS_MAX: n4.append(f"s{sd}/{pol}/{s}={ms:.4f}")
    rec["N4_unknown_return_mass"] = {"threshold": UNKNOWN_MASS_MAX, "breaches": n4,
                                     "note": "breach ⇒ that cell's L4/L5 numbers are UNRELIABLE, not wrong-and-fixed",
                                     "PASS": not n4}
    rec["utc_end"] = iso(time.time())
    verdict = "MEASURED" if rec["N1_null_control"]["PASS"] else "VOID_NULL_CONTROL_FAILED"
    rec["VERDICT"] = verdict
    op = os.path.join(outdir, "LADDER.json")
    tmp = op + ".tmp"; open(tmp, "w").write(json.dumps(rec, indent=1, allow_nan=False)); os.replace(tmp, op)
    print(f"LADDER VERDICT={verdict} null_pass={rec['N1_null_control']['PASS']} n4_pass={rec['N4_unknown_return_mass']['PASS']} "
          f"json={sha(op)[:16]} unavailable={len(rec['unavailable'])}", flush=True)
    sys.exit(0 if verdict == "MEASURED" else 4)


if __name__ == "__main__":
    main()
