"""ksr_targets_stats.py -- per-anchor book-change series for the KSR guardrail (DECISION_RULE_king_serving_refresh_2026-09-27 §3,
dlarch's interface 2026-09-27: "anchors, Σ|Δw| (L1 change of the target weights vs the previous anchor) and the WL seat vector";
the switch anchors and the non-switch p99 are computed by dlarch's reader, not here). fresh2 2026-09-27. DESCRIPTIVE, no gate.
For each seed: the engine's scaled targets TARGETS_NEWS2_s{seed}.npz (CSR: scaled_off / scaled_idx / scaled_val per anchor -- the
'scaled' side is the one the engine trades, run tag NEWS2_s{seed}X|scaled|rule|raw|UAFE) densified; sum_abs_dw[t] = Σ_i |w_t,i −
w_t−1,i| (NaN at t = 0), gross[t] = Σ_i |w_t,i|; scaled_kind and pad_before_new_axis copied through. WL comes from the cell's legs on the
legs axis (legs E_ts), stored as-is: the two axes differ (legs 10333 anchors, targets 9252) and are NOT aligned here.
Writes <outdir>/<label>_s<seed>.npz + <label>_s<seed>.json (source shas, as the verified writes returned them).
usage: python ksr_targets_stats.py <arm dir W> <legs.npz> <label> <outdir>
"""
import os, sys, json, hashlib
import numpy as np

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def main():
    W, legs_p, label, outd = sys.argv[1:5]
    os.makedirs(outd, exist_ok=True)
    L = np.load(legs_p)
    for s in ("42", "2027"):
        tp = os.path.join(W, "targets", "TARGETS_NEWS2_s%s.npz" % s)
        T = np.load(tp, allow_pickle=False)
        a = T["anchor"].astype(np.int64); off = T["scaled_off"]; idx = T["scaled_idx"].astype(np.int64); val = T["scaled_val"]
        assert len(off) == len(a) + 1 and off[-1] == len(idx) == len(val)
        n = int(idx.max()) + 1 if len(idx) else 1
        dense = np.zeros((len(a), n), np.float64)
        for t in range(len(a)):
            ii = idx[off[t]:off[t + 1]]
            assert len(np.unique(ii)) == len(ii), "duplicate name within anchor %d" % t
            dense[t, ii] = val[off[t]:off[t + 1]]
        dw = np.full(len(a), np.nan); dw[1:] = np.abs(np.diff(dense, axis=0)).sum(1)
        out = os.path.join(outd, "%s_s%s.npz" % (label, s))
        osha = DW.write_npz(out, anchors=a, sum_abs_dw=dw, gross=np.abs(dense).sum(1), scaled_kind=T["scaled_kind"],
                            pad_before_new_axis=T["pad_before_new_axis"], legs_E_ts=L["E_ts"], WL=L["WL"])
        rec = {"device": "ksr_targets_stats.py", "self_sha256": sha(os.path.realpath(__file__)), "label": label, "seed": s,
               "targets": tp, "targets_sha256": sha(tp), "legs": legs_p, "legs_sha256": sha(legs_p), "out": out, "out_sha256": osha,
               "n_anchors": int(len(a)), "n_legs_anchors": int(len(L["E_ts"]))}
        DW.write_json(out[:-4] + ".json", rec, indent=1)
        print("KSR_TSTATS %s s%s n=%d out_sha=%s" % (label, s, len(a), osha[:16]), flush=True)
    print("KSR_TSTATS_DONE %s" % label, flush=True)


if __name__ == "__main__":
    main()
