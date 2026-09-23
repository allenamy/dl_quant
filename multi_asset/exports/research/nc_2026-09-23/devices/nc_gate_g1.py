"""NC gates G1-1 (serving legality == x0918r legal mask) and G1-3 (member screen == researcher window_stats / select_members), pod2.
G1-1: nc_contract.legal_live on the prepared crypto cache (holes NaN) at EVERY anchor vs member_mask_tradable_AND_live_W24H_cachegrid
      restricted to crypto — name-by-name differences listed.
G1-3 (DESIGN §A1-4, second correction): on >= 6 anchors, the patched King block's c7 / v7 / qvm vs feature_contract.window_stats on the
      same 40-day window (rr for channel 0, log_qv for channel 3): n7 equal, v7 / q7 equal after rounding to float32 (gate); float64
      differences reported (tolerance rel 1e-12 / abs 1e-15, diagnostic); members == select_members(n7, v7, q7, x0918r legal ∧ crypto)
      name by name. R1-4 (mutation: quicksort / max(n,1) empty window) is reported as testable or NOT TESTABLE on this anchor set.
usage: python nc_gate_g1.py <researcher devices dir> <anchor> [<anchor> ...]"""
import os, sys, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nc_hist_features as H

W = os.environ.get("NC_W", "/dev/shm/nc_2026-09-23"); TREE = os.environ.get("NC_TREE", f"{W}/tree"); CFG = os.environ.get("NC_CFG", f"{W}/inputs/bundle_config.json")
MASK = "/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"


def main():
    res_dir = sys.argv[1]; anchors = [int(a) for a in sys.argv[2:]]
    sys.path.insert(0, res_dir); import feature_contract as FC
    H.set_tree(TREE); NC, TR = H._G["NC"], H._G["TR"]; I = H.Inputs()
    cfg = json.load(open(CFG)); P = cfg["params"]; kb = H._king_block()
    MK = np.load(MASK, allow_pickle=True); assert [str(s) for s in MK["symbols"]] == I.syms
    mts = MK["ts"].astype(np.int64); mask = MK["mask"]
    out = {"device_sha256": H.sha(os.path.abspath(__file__)), "tree_receipt_sha256": H.sha(f"{TREE}/PATCH_RECEIPT.json")}
    # ---- G1-1 every anchor
    t0 = time.time(); C = I.C
    lc = C[:, :, 4]; lq = C[:, :, 3]
    L = NC.legal_live(I.ts, np.asarray(lc), np.asarray(lq), I.anchors, TR)
    mi = np.searchsorted(mts, I.anchors); assert np.array_equal(mts[mi], I.anchors)
    Mx = mask[mi][:, I.cols]
    d = L != Mx
    rows = np.flatnonzero(d.any(1))
    out["G1_1"] = {"anchors": int(len(I.anchors)), "cells": int(d.size), "differ_cells": int(d.sum()), "differ_anchors": int(len(rows)),
                   "first": [{"anchor": int(I.anchors[r]), "names": [I.syms[I.cols[c]] for c in np.flatnonzero(d[r])][:10],
                              "serving_legal": [bool(L[r, c]) for c in np.flatnonzero(d[r])][:10]} for r in rows[:10]],
                   "PASS": int(d.sum()) == 0, "seconds": round(time.time() - t0, 1)}
    print("G1-1", json.dumps({k: v for k, v in out["G1_1"].items() if k != "first"}), flush=True)
    # ---- G1-3
    g13 = []; testable_ties = testable_empty = 0
    for A in anchors:
        rts, cd, R, _ = I.window(A)
        r = H.pass1_anchor(I, A, P, cfg, kb)
        ia = len(rts) - 1
        st = FC.window_stats(R, np.array([ia]), 2016); sq = FC.window_stats(cd[:, :, 3].astype(np.float32), np.array([ia]), 2016)
        n7 = st["count"][0]; v7r = st["std"][0].astype(np.float32); q7r = sq["mean"][0].astype(np.float32)
        legal = mask[int(np.searchsorted(mts, A))] & I.crypto
        mr = FC.select_members(n7, v7r, q7r, legal, cov_min=P["cov_min"], vol_min=P["vol_min"], ntop=400)
        assert "screen" in r, f"G1-3 anchors must produce King features (>= 50 members): {A}"
        sc = r["screen"]; rr = r["members"]
        ok_n = bool(np.array_equal(sc["c7"].astype(np.int64), n7.astype(np.int64)))
        eq_v = (sc["v7"].view(np.uint32) == v7r.view(np.uint32)) | (np.isnan(sc["v7"]) & np.isnan(v7r))
        eq_q = (sc["qvm"].view(np.uint32) == q7r.view(np.uint32)) | (np.isnan(sc["qvm"]) & np.isnan(q7r))
        v64 = st["std"][0]; q64 = sq["mean"][0]
        # f64 diagnostic: producer float64 before its float32 cast is not exposed; report |f32(producer) - f64(researcher)| relative
        fin = np.isfinite(v64) & np.isfinite(sc["v7"])
        dv = np.abs(sc["v7"][fin].astype(np.float64) - v64[fin]) / np.maximum(np.abs(v64[fin]), 1e-300)
        cand = legal
        qc = q7r[cand & np.isfinite(q7r)]
        row = {"anchor": A, "utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(A)), "n_members_producer": int(len(rr)), "n_members_researcher": int(len(mr)),
               "n7_equal": ok_n, "v7_f32_differ": int((~eq_v).sum()), "q7_f32_differ": int((~eq_q).sum()),
               "v7_rel_diag_max": float(dv.max()) if len(dv) else None,
               "legal_equal_x0918r": bool(np.array_equal(sc["legal"] & I.crypto, legal)),
               "members_equal": bool(np.array_equal(np.sort(rr), np.sort(mr))),
               "producer_not_researcher": [I.syms[j] for j in sorted(set(rr.tolist()) - set(mr.tolist()))][:20],
               "researcher_not_producer": [I.syms[j] for j in sorted(set(mr.tolist()) - set(rr.tolist()))][:20],
               "R1_4_ties_in_candidate_qvm": int(len(qc) - len(np.unique(qc))),
               "R1_4_empty_7d_window_candidates": int((cand & (n7 == 0)).sum())}
        row["PASS"] = row["n7_equal"] and row["v7_f32_differ"] == 0 and row["q7_f32_differ"] == 0 and row["members_equal"]
        g13.append(row); print("G1-3", json.dumps(row)[:400], flush=True)
    out["G1_3_members"] = g13
    out["G1_3_PASS"] = all(r["PASS"] for r in g13) and len(g13) >= 6
    out["R1_4_testable"] = {"ties": sum(r["R1_4_ties_in_candidate_qvm"] for r in g13), "empty": sum(r["R1_4_empty_7d_window_candidates"] for r in g13)}
    json.dump(out, open(f"{W}/receipts/NC_GATE_G1.json", "w"), indent=1)
    print("NC_GATE_G1", "G1-1", out["G1_1"]["PASS"], "G1-3", out["G1_3_PASS"], "R1-4 testable", out["R1_4_testable"], flush=True)


if __name__ == "__main__":
    main()
