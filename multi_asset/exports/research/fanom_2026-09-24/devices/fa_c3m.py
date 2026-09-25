"""fa_c3m.py — build the C3m combo: C3's weights under the BASE publish decision.

PREREG: docs/PREREG_C3m_exposure_vs_gate_2026-09-25.md (ebba4ece7), lead-approved as a DIAGNOSTIC arm
(no admit/reject verdict, does not enter the family wording).

    trade_mask_C3m = trade_mask_base                    # bitwise the base's
    weights_C3m    = C3_weights where trade_mask_base   # C3's weights on the anchors the base published
                     0          otherwise

Licence for expressing this as post-processing is the same as B4/B5: continuous_combo.evolve L36-42 writes
kc/fc/raw UNCONDITIONALLY; only trade_mask/weights depend on `accepted`.

The arm isolates (1) cutting exposure + (2) paying less funding, WITHOUT (3) the preflight gate biting less.
⚠ The decomposition is ORDER-DEPENDENT, not additive (prereg §2): d(C3) != d(C3m) + d(pure gate effect).

usage: ... fa_c3m.py WL <seed> <base_dir> <c3_dir> <out_dir>
"""
import os, sys, json, hashlib, time
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
SEED, BASE, C3, OUT = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
MODES = ["scaled_diagnostic", "literal"]
# `reason` and `trade_mask` describe the PUBLISH decision, so both come from the base; kc/fc/raw come from C3.
FROM_BASE = ["trade_mask", "reason"]
FROM_C3 = ["E_ts", "symbols", "kc", "fc", "raw"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


os.makedirs(OUT, exist_ok=True)
rec = {"device": "fa_c3m.py", "self_sha256": sha(os.path.abspath(__file__)), "seed": SEED,
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "prereg": "docs/PREREG_C3m_exposure_vs_gate_2026-09-25.md (ebba4ece7)",
       "role": "DIAGNOSTIC — no verdict, not a family candidate (lead 2026-09-25)",
       "order_warning": "d(C3) != d(C3m) + d(pure gate effect); the split is order-dependent (prereg S2)",
       "base_dir": BASE, "c3_dir": C3, "modes": {}}

for m in MODES:
    pb, pc = os.path.join(BASE, m + ".npz"), os.path.join(C3, m + ".npz")
    zb, zc = np.load(pb, allow_pickle=False), np.load(pc, allow_pickle=False)
    assert sorted(zb.files) == sorted(zc.files), f"{m}: schema differs between base and C3"
    # axis identity: the arm is only meaningful if both are on the same anchors and the same names
    assert np.array_equal(zb["E_ts"], zc["E_ts"]), f"{m}: anchor axis differs"
    assert np.array_equal(zb["symbols"], zc["symbols"]), f"{m}: symbol axis differs"

    tm_b, tm_c = zb["trade_mask"].copy(), zc["trade_mask"].copy()
    w_b, w_c = zb["weights"], zc["weights"]
    w_new = np.where(tm_b[:, None], w_c, 0.0)

    out = {k: zc[k] for k in FROM_C3}
    for k in FROM_BASE: out[k] = zb[k]
    out["weights"] = w_new

    # ---- prereg S3 controls: any failure stops the arm ----
    c = {}
    c["1_mask_bitwise_equals_base"] = bool(np.array_equal(out["trade_mask"], tm_b))
    pub = tm_b
    c["2_weights_bitwise_equal_C3_on_published"] = bool(np.array_equal(out["weights"][pub], w_c[pub]))
    # np.all over an empty selection is True, which is the right degenerate answer; written flat so that no
    # reader has to resolve `and`/`or` precedence to know what the control asserts
    c["2b_zero_off_published"] = bool(np.all(out["weights"][~pub] == 0.0))
    c["3_state_chain_bitwise_equals_C3"] = bool(all(np.array_equal(out[k], zc[k]) for k in FROM_C3))
    # S3.4 non-degeneracy: must differ from BOTH parents, else the arm collapsed into one of them
    d_vs_c3_publish = int((out["trade_mask"] != tm_c).sum())
    fin = np.isfinite(w_b) & np.isfinite(out["weights"])
    d_vs_base_w = int((np.where(fin, out["weights"], 0.0) != np.where(fin, w_b, 0.0)).sum())
    d_vs_base_anch = int((np.where(fin, out["weights"], 0.0) != np.where(fin, w_b, 0.0)).any(1).sum())
    c["4_differs_from_C3_in_publish_set"] = d_vs_c3_publish > 0
    c["4_differs_from_base_in_weights"] = d_vs_base_w > 0
    failed = [k for k, v in c.items() if not v]

    p_out = os.path.join(OUT, m + ".npz")
    np.savez(p_out + ".tmp.npz", **out); os.replace(p_out + ".tmp.npz", p_out)
    # the receipt's sha is the one the verifying READ-BACK returns, not an independent later re-read (E-0925-A)
    zr = np.load(p_out, allow_pickle=False)
    assert all(np.array_equal(zr[k], out[k]) for k in out), f"{m}: written npz does not read back bitwise"
    rec["modes"][m] = {"npz": p_out, "npz_sha256": sha(p_out), "controls": c, "controls_failed": failed,
                       "base_published": int(tm_b.sum()), "c3_published": int(tm_c.sum()),
                       "anchors_c3_publishes_and_base_does_not": int((tm_c & ~tm_b).sum()),
                       "anchors_base_publishes_and_c3_does_not": int((tm_b & ~tm_c).sum()),
                       "cells_differing_from_base_weights": d_vs_base_w,
                       "anchors_differing_from_base_weights": d_vs_base_anch}
    print("FA_C3M %-18s published base=%d c3=%d  c3_extra=%d  wcells_vs_base=%d  controls=%s"
          % (m, tm_b.sum(), tm_c.sum(), (tm_c & ~tm_b).sum(), d_vs_base_w,
             "ALL_OK" if not failed else "FAILED:" + ",".join(failed)), flush=True)

rec["all_controls_ok"] = all(not v["controls_failed"] for v in rec["modes"].values())
p_rec = os.path.join(OUT, "FA_C3M_RECEIPT.json")
json.dump(rec, open(p_rec + ".tmp", "w"), indent=1); os.replace(p_rec + ".tmp", p_rec)
print("FA_C3M all_controls_ok=%s receipt=%s" % (rec["all_controls_ok"], p_rec), flush=True)
bad = {m: v["controls_failed"] for m, v in rec["modes"].items() if v["controls_failed"]}
assert not bad, f"prereg S3 controls failed, arm not implemented as defined: {bad}"
