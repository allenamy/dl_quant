#!/usr/bin/env python3
"""d10_prefix_identity.py {fund_state|legs} REF NEW CUT_EPOCH OUT.json -- the pre-cut identity controls of the descriptive re-read
(docs/PLAN_d10_reread_past_cut_2026-09-27.md, R4 and R7). Extending the ledger past the cut may change ONLY what lies after the cut.

  fund_state : per crypto column, the events with ft <= CUT (arrays ft, rate, iv, ema, prev) must equal REF's bitwise, and kidx at
               every anchor <= CUT must equal REF's. anchors / cols must be identical. (Layout: nc_prep.py L108-L122.)
  legs       : every row with E_ts < CUT, in every per-anchor key (KZ, Z24, ZFD, RN8, QV, ready, LR, WL, E_ts), must equal REF's
               bitwise; symbols identical. Rows after the cut are counted per key (descriptive).
Floats are compared through their same-width integer view (NaN == NaN). One anchored line: `PREFIX_IDENTITY PASS|FAIL <kind> ...`.
"""
import hashlib, json, os, sys

import numpy as np

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW  # every file this device writes goes through it (news2 class fix 2026-09-27)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def neq(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape or a.dtype != b.dtype:
        return -1
    if a.dtype.kind == "f":
        u = {4: np.uint32, 8: np.uint64}[a.itemsize]
        return int((~((a.view(u) == b.view(u)) | (np.isnan(a) & np.isnan(b)))).sum())
    return int((a != b).sum())


def fund_state(R, N, cut):
    res = {"anchors_equal": neq(R["anchors"], N["anchors"]) == 0, "cols_equal": neq(R["cols"], N["cols"]) == 0}
    ro, no = R["ev_off"].astype(np.int64), N["ev_off"].astype(np.int64)
    bad_cols, per_field = [], {k: 0 for k in ("ft", "rate", "iv", "ema", "prev")}
    added_after = 0
    for j in range(len(ro) - 1):
        rf, nf = R["ft"][ro[j]:ro[j + 1]], N["ft"][no[j]:no[j + 1]]
        rm, nm = rf <= cut, nf <= cut
        added_after += int((~nm).sum()) - int((~rm).sum())
        if rm.sum() != nm.sum():
            bad_cols.append(j); continue
        for k in per_field:
            d = neq(R[k][ro[j]:ro[j + 1]][rm], N[k][no[j]:no[j + 1]][nm])
            if d:
                per_field[k] += max(d, 1); bad_cols.append(j)
    am = R["anchors"].astype(np.int64) <= cut
    kd = neq(R["kidx"][am], N["kidx"][am])
    res.update({"columns_with_pre_cut_difference": sorted(set(bad_cols))[:20], "n_columns_bad": len(set(bad_cols)),
                "pre_cut_field_differences": per_field, "kidx_pre_cut_differences": kd,
                "anchors_le_cut": int(am.sum()), "events_added_after_cut_net": added_after})
    ok = res["anchors_equal"] and res["cols_equal"] and not bad_cols and kd == 0
    return ok, res


def legs(R, N, cut):
    ok = neq(R["symbols"], N["symbols"]) == 0 and neq(R["E_ts"], N["E_ts"]) == 0
    pre = R["E_ts"].astype(np.int64) < cut
    per = {}
    for k in sorted(set(R) & set(N)):
        if k == "symbols":
            continue
        a, b = R[k], N[k]
        if a.shape[:1] != R["E_ts"].shape:
            continue
        per[k] = {"pre_cut_differ": neq(a[pre], b[pre]), "post_cut_differ": neq(a[~pre], b[~pre])}
    ok = ok and all(v["pre_cut_differ"] == 0 for v in per.values())
    return ok, {"rows_pre_cut": int(pre.sum()), "rows_post_cut": int((~pre).sum()), "per_key": per,
                "keys_only_ref": sorted(set(R) - set(N)), "keys_only_new": sorted(set(N) - set(R))}


def main():
    kind, ref, new, cut, outp = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
    # load every array ONCE: indexing an NpzFile re-reads the member on every access (680 columns x 5 fields would re-read 2.6M-row
    # arrays thousands of times -- the first pod2 run of this device was stopped for exactly that, before it produced any reading)
    R = {k: v for k, v in np.load(ref, allow_pickle=True).items()}
    N = {k: v for k, v in np.load(new, allow_pickle=True).items()}
    ok, res = (fund_state if kind == "fund_state" else legs)(R, N, cut)
    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)), "kind": kind, "cut": cut,
           "ref": [ref, sha(ref)], "new": [new, sha(new)], "result": res, "verdict": "PASS" if ok else "FAIL"}
    s = DW.write_json(outp, rec, indent=1, allow_nan=True, default=str)
    print(f"PREFIX_IDENTITY {rec['verdict']} {kind} receipt_sha256={s} {json.dumps(res, default=str)[:400]}")


if __name__ == "__main__":
    main()
