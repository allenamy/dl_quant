"""NEW_S2 global gate (PREREG §6.2 ii + iii): on real archived anchors, run the producer feature code
with one fix enabled at a time and check that ONLY the declared columns move.

Arms:
  base_raw   6080073b, no fixes            -- for gate (ii), the base swap
  base       ed11d731, no fixes            -- the reference every other arm is diffed against
  D4 D5 D6 D7 D8 D9 D11 D13 D14            -- one fix each
  all        every fix

Gates:
  (ii)  base_raw vs base: bitwise identical on every output. Proves the measured deltas below come
        from the nine fixes and not from swapping the base file.
  (iii) for each single-fix arm, on anchors whose MEMBER SET is identical to base, every column
        OUTSIDE that fix's declared reach is bitwise identical. Two ways this gate can be empty are
        reported, never silently passed:
          n_same == 0        -> UNAVAILABLE (no anchor could be compared at all)
          n_changed == 0     -> NO-MEASUREMENT, unless the arm is declared expected_zero

Also emits the numbers PREREG §5 needs before the chain: member-set deltas, per-column change counts,
f8 finite_share_raw per arm (how much of F89 the D8 full-window gates actually remove on REAL data),
btcv NaN counts, and per-anchor wall clock (the §7 P0 timing).

Inputs are the NEW_S parity slices under ~/cc_tmp/news_20260923/parity (read-only).
usage: python news2_global_gate.py <work_dir> <out.json> [n_anchors]
"""
import json, os, subprocess, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import news2_hist_features as H

PAR = os.environ.get("NEWS2_PAR", os.path.expanduser("~/cc_tmp/news_20260923/parity"))
CRYPTO = os.environ.get("NEWS2_CRYPTO", os.path.join(HERE, "../../news_2026-09-23/receipts/P1_members_2025H2on.npz"))
CFG = os.environ.get("NEWS2_CFG", os.path.expanduser("~/cc_tmp/news_20260923/producer_copy/shadow_bundle/config.json"))
ANCH_ALL = [1789660800 + 14400 * k for k in range(9)]

ARMS = ["base_raw", "base", "D4", "D5", "D6", "D7", "D8", "D9", "D11", "D13", "D14", "all"]
REACH_CORRECTIONS = [{"utc": "2026-09-23T16:4xZ", "arm": "D8", "added": ["C:vr12_2016", "C:vr48_2016", "C:vr48_8640"],
                      "why": "BS (f8 L196) feeds the whole vr loop L194-L203, not only upblk; my first reach table under-read the source",
                      "seen_before_correction": "gate run 1 reported 1197 out-of-reach cells, all in C:vr48_8640"}]

# CORRECTION (2026-09-23 16:4xZ, after gate run 1 reported C:vr48_8640 out of reach): the D8:BS_support
# patch rewrites BS at f8_higher_order_features.py L196, and BS feeds EVERY column of the vr loop
# (L194-L203): C:vr12_2016, C:vr48_2016, C:vr48_8640 and C:upblk_2016. The first three were missing from
# this table. This is a correction to a DESCRIPTION OF THE SOURCE'S DEPENDENCY GRAPH (re-derived by
# reading L188-L204), not a loosening of a judging criterion; it is recorded here and in the receipt.
D8_COLS = ["A:jump_288", "A:jump_2016", "B:vov_7d", "C:ac1_288", "C:ac1_2016",
           "C:vr12_2016", "C:vr48_2016", "C:vr48_8640", "C:upblk_2016",
           "D:dhi_48", "D:dhi_288", "D:dhi_2016", "D:dhi_8640", "D:dlo_288", "D:dlo_2016", "D:dlo_8640",
           "D:ppct_288", "D:ppct_2016", "E:spr_7", "E:spr_30", "E:spr_30_t",
           "F:amihud_288", "F:amihud_2016", "F:damihud", "F:kyle_288", "F:kyle_2016",
           "G:tbvw_48", "G:tbvw_288", "G:tbvw_2016", "G:tbac1_288",
           "J:r4_lag_2", "J:r4_lag_3", "J:r4_lag_4", "J:r4_lag_5", "J:r4_lag_6", "J:r24_lag1"]
D9_COLS = ["H:btcv_z", "H:r4xbtcv", "H:r24xbtcv", "H:m7xbtcv", "H:v7xbtcv"]
D7_COLS = ["C:trend_288", "C:trend_2016"]


def f89_reach(arm, names):
    """Columns of F89 this arm is ALLOWED to move. Everything else must be bitwise identical."""
    HI = [n for n in names if n.startswith("H:") or n.startswith("I:")]
    DR = [n for n in names if n.startswith("J:drank_")]
    if arm == "D4":
        return set(HI) | set(DR)                  # via the stored X82 the H/I/drank blocks read
    if arm == "D6":
        return set(HI) | set(DR)
    if arm == "D7":
        return set(D7_COLS)
    if arm == "D8":
        return set(D8_COLS)
    if arm == "D9":
        return set(D9_COLS)
    if arm in ("D5", "D11", "D13", "D14"):
        return set()
    return set(names)                              # "all"


def x82_reach(arm, n_cols=82):
    if arm == "D5":
        return set()            # D5 is King-side only; F10's kernel is untouched (D5' in the PREREG)
    if arm == "D4":
        return set(range(n_cols))
    if arm == "D6":
        # the 30 mean columns and the 5 vol columns, value AND rank; the 5 ret5_sum value columns must not move
        keep = set()
        for blk in range(40):
            nm_is_ret5_sum = blk < 5
            if not nm_is_ret5_sum:
                keep.add(2 * blk)
            keep.add(2 * blk + 1)                  # a rank can move even for ret5_sum: the denominator changes
        return keep
    if arm == "D11":
        return {80, 81}
    if arm in ("D5", "D7", "D8", "D9", "D13", "D14"):
        return set()
    return set(range(n_cols))


def king_reach(arm):
    return arm in ("D5", "D6", "all")


EXPECTED_ZERO = {"D13": "rn8 is not a feature column; D13 is measured in the legs/combo layer",
                 "D14": "on anchors whose member set is identical, D14 changes nothing by construction"}


def build_tree(work, arm):
    out = f"{work}/tree_{arm}"
    if os.path.exists(f"{out}/PATCH_RECEIPT.json"):
        return out
    cmd = [sys.executable, f"{HERE}/news2_derive_producer.py", out]
    if arm == "base_raw":
        cmd += ["--only", "NONE", "--shadow-base", "raw"]
    elif arm == "base":
        cmd += ["--only", "NONE"]
    elif arm != "all":
        cmd += ["--only", arm]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return out


def main():
    work = os.path.abspath(sys.argv[1])
    out_path = os.path.abspath(sys.argv[2])
    nanch = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    anchors = ANCH_ALL[:nanch]
    os.makedirs(f"{work}/mini", exist_ok=True)
    t0 = time.time()

    C = np.load(f"{PAR}/parity_cache_slice.npz", allow_pickle=True)
    ts = C["ts"].astype(np.int64); D = C["data"]; row0 = int(C["row0"])
    syms = [str(s) for s in C["symbols"]]; chn = [str(c) for c in C["ch"]]
    with np.load(f"{PAR}/parity_holes_slice.npz") as z: hz = {"row": z["row"], "col": z["col"]}
    o = np.lexsort((hz["col"], hz["row"]))
    holes = (hz["row"][o].astype(np.int64) - row0, hz["col"][o].astype(np.int64))
    # Materialise every array ONCE (an NpzFile decompresses on every __getitem__, and these are read per anchor).
    with np.load(f"{PAR}/parity_mask_slice.npz") as z: mk = {"ts": z["ts"].astype(np.int64), "mask": z["mask"]}
    mts = mk["ts"]
    with np.load(f"{PAR}/parity_fund_slice.npz") as z: fr = {k: z[k] for k in ("anchors", "ema_acc", "last_ft", "last_rate", "last_iv")}
    fa = fr["anchors"].astype(np.int64)
    with np.load(os.path.abspath(CRYPTO)) as z: crypto = z["crypto"]
    cfg = json.load(open(CFG))

    res = {}
    timing = {}
    for arm in ARMS:
        tree = build_tree(work, arm)
        H.set_tree(tree)
        res[arm] = {}
        timing[arm] = []
        for A in anchors:
            i = int(np.searchsorted(fa, A)); assert fa[i] == A
            cand = mk["mask"][int(np.searchsorted(mts, A))] & crypto
            ema = {syms[j]: {"acc": float(fr["ema_acc"][i, j])} for j in np.flatnonzero(np.isfinite(fr["ema_acc"][i]))}
            led = {syms[j]: [[int(fr["last_ft"][i, j]), float(fr["last_rate"][i, j]), float(fr["last_iv"][i, j])]]
                   for j in np.flatnonzero(fr["last_ft"][i] >= 0)}
            t1 = time.time()
            r = H.replay_anchor(A, D, ts, syms, chn, cand, ema, led, cfg["params"], cfg, f"{work}/mini", holes=holes, cols="members")
            dt = round(time.time() - t1, 2)
            timing[arm].append(dt)
            assert "skip" not in r, (arm, A, r)
            res[arm][A] = r
            print(f"{time.strftime('%H:%M:%S', time.gmtime())} {arm:9s} {A} members={len(r['m'])} {dt}s", flush=True)

    names = res["base"][anchors[0]]["f89_names"]
    cells = []

    def bitwise(a, b):
        a = np.asarray(a); b = np.asarray(b)
        if a.shape != b.shape:
            return False, a.size
        d = ~((a == b) | (np.isnan(a) & np.isnan(b)))
        return (not d.any()), int(d.sum())

    # ---- gate (ii): the base swap is a no-op
    diffs = 0
    for A in anchors:
        a, b = res["base_raw"][A], res["base"][A]
        for k in ("m", "king_X78", "X82", "X89", "fe_v", "fn_v", "qvm", "rev24"):
            ok, n = bitwise(a[k].astype(np.float64) if k != "m" else a[k], b[k].astype(np.float64) if k != "m" else b[k])
            diffs += 0 if ok else n
    cells.append({"gate": "ii.base_swap_is_a_noop", "verdict": "PASS" if diffs == 0 else "FAIL",
                  "n_anchors": len(anchors), "n_differing_cells": diffs,
                  "note": "6080073b vs ed11d731, no fixes applied"})

    # ---- gate (iii): per-fix reach
    for arm in ARMS:
        if arm in ("base", "base_raw"):
            continue
        same = [A for A in anchors if np.array_equal(res["base"][A]["m"], res[arm][A]["m"])]
        memdiff = {str(A): int(len(set(res["base"][A]["m"].tolist()) ^ set(res[arm][A]["m"].tolist()))) for A in anchors}
        allowed89 = f89_reach(arm, names)
        allowed82 = x82_reach(arm)
        out_of_reach = 0
        in_reach = 0
        king_changed = 0
        per_col = {}
        for A in same:
            b, x = res["base"][A], res[arm][A]
            _, nk = bitwise(b["king_X78"].astype(np.float64), x["king_X78"].astype(np.float64))
            king_changed += nk
            b82 = np.asarray(b["X82"], np.float64); x82 = np.asarray(x["X82"], np.float64)
            for c in range(b82.shape[1]):
                _, n = bitwise(b82[:, c], x82[:, c])
                if n:
                    (per_col.setdefault("X82", {})).setdefault(str(c), 0)
                    per_col["X82"][str(c)] += n
                    if c in allowed82:
                        in_reach += n
                    else:
                        out_of_reach += n
            b89 = np.asarray(b["X89"], np.float64); x89 = np.asarray(x["X89"], np.float64)
            for c, nm in enumerate(names):
                _, n = bitwise(b89[:, c], x89[:, c])
                if n:
                    (per_col.setdefault("F89", {})).setdefault(nm, 0)
                    per_col["F89"][nm] += n
                    if nm in allowed89:
                        in_reach += n
                    else:
                        out_of_reach += n
        if king_changed and not king_reach(arm):
            out_of_reach += king_changed
        elif king_changed:
            in_reach += king_changed
        n_changed = in_reach + out_of_reach
        if not same:
            v = "UNAVAILABLE(no comparable anchor)"
        elif out_of_reach:
            v = "FAIL(out of declared reach)"
        elif n_changed == 0 and arm not in EXPECTED_ZERO:
            v = "NO-MEASUREMENT"
        else:
            v = "PASS"
        cells.append({"gate": f"iii.{arm}", "verdict": v, "n_same_member_anchors": len(same),
                      "member_symmetric_difference": memdiff, "cells_in_reach": in_reach,
                      "cells_out_of_reach": out_of_reach, "king_X78_cells_changed": king_changed,
                      "expected_zero": EXPECTED_ZERO.get(arm), "changed_columns": per_col})

    # ---- PREREG §5 diagnostics
    fin = {arm: res[arm][anchors[-1]]["f89_finite_share_raw"] for arm in ("base", "D8", "all")}
    d8_drop = sorted(((nm, round(fin["base"][nm], 4), round(fin["D8"][nm], 4)) for nm in D8_COLS if nm in fin["base"]),
                     key=lambda t: t[2] - t[1])
    diag = {
        "anchors": anchors,
        "members_per_anchor": {arm: {str(A): int(len(res[arm][A]["m"])) for A in anchors} for arm in ARMS},
        "btcv_at_anchor": {arm: {str(A): res[arm][A]["btcv_anchor"] for A in anchors} for arm in ("base", "D9", "all")},
        "btcv_nan_rows_in_mini": {arm: {str(A): res[arm][A]["btcv_nan_rows"] for A in anchors} for arm in ("base", "D9", "all")},
        "f89_finite_share_raw_D8_columns_last_anchor": [{"col": c, "base": b, "D8": d} for c, b, d in d8_drop],
        "f89_finite_share_raw_mean": {arm: round(float(np.mean(list(fin[arm].values()))), 4) for arm in fin},
        "seconds_per_anchor": timing,
        "king_span": res["all"][anchors[0]]["king_span"],
        "fund_panel_span": res["all"][anchors[0]]["fund_span"],
    }

    bad = [c for c in cells if c["verdict"] != "PASS"]
    rec = {"device": "news2_global_gate.py", "self_sha256": H.sha(os.path.abspath(__file__)),
           "news2_hist_features_sha256": H.sha(os.path.join(HERE, "news2_hist_features.py")),
           "news2_derive_producer_sha256": H.sha(os.path.join(HERE, "news2_derive_producer.py")),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "python": sys.version.split()[0], "numpy": np.__version__,
           "inputs": {p: H.sha(p) for p in [f"{PAR}/parity_cache_slice.npz", f"{PAR}/parity_holes_slice.npz",
                                            f"{PAR}/parity_mask_slice.npz", f"{PAR}/parity_fund_slice.npz",
                                            os.path.abspath(CRYPTO), CFG]},
           "tree_shas": {arm: json.load(open(f"{work}/tree_{arm}/PATCH_RECEIPT.json"))["outputs"] for arm in ARMS},
           "gates": cells, "diagnostics": diag, "reach_corrections": REACH_CORRECTIONS,
           "VERDICT": "PASS" if not bad else "FAIL", "n_gates": len(cells), "n_not_pass": len(bad),
           "seconds": round(time.time() - t0, 1)}
    with open(out_path, "w") as f:
        json.dump(rec, f, indent=1)
    for c in cells:
        print(f"  {c['gate']:26s} {c['verdict']}", flush=True)
    print(f"NEWS2_GLOBAL_GATE VERDICT={rec['VERDICT']} gates={rec['n_gates']} not_pass={rec['n_not_pass']} receipt_sha256={H.sha(out_path)}", flush=True)
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()
