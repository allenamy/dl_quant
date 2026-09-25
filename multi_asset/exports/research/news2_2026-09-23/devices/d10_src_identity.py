#!/usr/bin/env python3
"""d10_src_identity.py -- why the ledger's zip_iv is NaN on 109,070 rows. Answer: by construction.

D10 truth audit stage 1, question 1 (lead 2026-09-25, user ruling 96994c7f5): "研究员账本 zip_iv 有
109,070 行 NaN, 先查清原因".

WHAT THIS DEVICE DOES, and why it is a device rather than two numbers I noticed are equal: the claim
"the 109,070 NaN rows are the API-only rows" could be asserted by matching my count against the D5
census figure in PREREG_producer_parity_phase2_oos_2026-09-12.md. That would be a coincidence of two
numbers. Instead this device cross-tabulates zip_iv's finiteness against the ledger's own `src` column
and requires EXACT alignment: one src class holding every NaN row and no finite row.

The MEANING of the src codes is established the same way -- not from the column name, and not from a
guess. Three of the four class counts are matched against three independently committed D5 numbers
(API-only 109,070 / zip-only 158,857 / dual-source same-second 2,365,163), and the fourth is shown to
equal the row difference between this ledger and D5's cut. A label only gets attached when its count
reproduces a number that was written down before this device existed.
"""
import argparse, hashlib, json, os, sys

import numpy as np

# counts committed in docs/PREREG_producer_parity_phase2_oos_2026-09-12.md L77 (the D5 census),
# written down long before this device; a src class earns a label only by reproducing one of these.
D5 = {"api_only": 109070, "zip_only": 158857, "dual_source_same_second": 2365163, "d5_total_rows": 2633090}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable, "numpy": np.__version__,
           "task": "D10 truth audit stage 1 question 1 (user ruling 96994c7f5, lead's five questions)",
           "question": "why is the researcher ledger's zip_iv NaN on 109,070 rows",
           "method": ("cross-tabulate zip_iv finiteness against the ledger's own src column and require "
                      "EXACT alignment; attach a label to a src class only when its count reproduces a "
                      "number committed before this device (the D5 census)"),
           "d5_reference_counts": D5,
           "inputs": {"ledger": {"path": a.ledger, "sha256": sha(a.ledger)}}}

    z = np.load(a.ledger, allow_pickle=True)
    rec["ledger_keys"] = sorted(z.files)
    iv = np.asarray(z["zip_iv"], np.float64)
    src = np.asarray(z["src"], np.int8)
    assert iv.shape == src.shape, ("zip_iv and src must share the row axis", iv.shape, src.shape)
    nan = ~np.isfinite(iv)
    rec["rows_total"] = int(iv.size)
    rec["zip_iv_non_finite"] = int(nan.sum())
    rec["zip_iv_finite"] = int((~nan).sum())

    xt = {}
    for v in sorted(set(src.tolist())):
        m = src == v
        xt[str(int(v))] = {"rows": int(m.sum()), "zip_iv_nan": int((m & nan).sum()),
                           "zip_iv_finite": int((m & ~nan).sum())}
    rec["crosstab_src_x_zip_iv"] = xt
    closure = sum(v["rows"] for v in xt.values())
    rec["closure_check"] = {"sum_of_src_classes": closure, "rows_total": int(iv.size),
                            "equal": bool(closure == int(iv.size))}
    assert closure == int(iv.size), "src classes must partition the rows"

    # exact alignment: one class holds every NaN and no finite row
    aligned = [k for k, v in xt.items()
               if v["zip_iv_nan"] == rec["zip_iv_non_finite"] and v["zip_iv_finite"] == 0]
    rec["exact_alignment"] = {"src_classes_holding_every_nan_and_no_finite_row": aligned,
                              "is_exact": bool(len(aligned) == 1)}

    # labels earned by reproducing a pre-committed count, never by the column name
    labels, unmatched = {}, []
    for k, v in xt.items():
        hit = [name for name, n in D5.items() if name != "d5_total_rows" and n == v["rows"]]
        if hit:
            labels[k] = {"label": hit[0], "earned_by": f"row count {v['rows']} reproduces D5 {hit[0]}"}
        else:
            unmatched.append(k)
    for k in unmatched:
        d = xt[k]["rows"] - (rec["rows_total"] - D5["d5_total_rows"])
        labels[k] = {"label": ("rows_after_the_D5_cut" if d == 0 else "UNLABELLED"),
                     "earned_by": (f"row count {xt[k]['rows']} equals this ledger minus the D5 cut "
                                   f"({rec['rows_total']} - {D5['d5_total_rows']})" if d == 0
                                   else "no committed count reproduced; deliberately left unlabelled")}
    rec["src_labels"] = labels

    rec["distinct_finite_zip_iv_values"] = sorted(set(iv[~nan].tolist()))
    rec["note_on_3h"] = ("the declared-interval column never carries 3.0 (nor 6.0) here, so a 3-hour "
                         "value can only arise from SPACING. common/funding_interval.py's ALLOWED_IV "
                         "excludes 3.0, so an EXACT_BY_SPACING resolution of 3.0 hours would make "
                         "gate_interval RAISE rather than label the row UNRESOLVED. Reported to lead as "
                         "a reachable path, not adjudicated here.")

    ok = (rec["exact_alignment"]["is_exact"] and rec["closure_check"]["equal"]
          and all(v["label"] != "UNLABELLED" for v in labels.values()))
    rec["verdict"] = ("ZIP_IV_NAN_IS_EXACTLY_THE_API_ONLY_CLASS_BY_CONSTRUCTION" if ok
                      else "INCONCLUSIVE_ALIGNMENT_OR_LABELLING_INCOMPLETE")
    rec["reading"] = ("zip_iv is the archive's per-settlement column, so it is NaN on rows that came only "
                      "from the API. That is a definition, not a data defect and not a truth gap: the "
                      "researcher's assembly fills them from the other sources, leaving 4,663 unknown "
                      "(IV_SOURCE_CENSUS2.json).")
    rec["limits"] = ["this explains the NaN population; it does not by itself say the assembled iv is correct",
                     "the src labels are earned by count reproduction, which is strong but not a proof of semantics"]
    json.dump(rec, open(a.out, "w"), indent=2)

    print("VERDICT", rec["verdict"])
    print(f"  rows {rec['rows_total']}  zip_iv NaN {rec['zip_iv_non_finite']}  finite {rec['zip_iv_finite']}")
    for k in sorted(xt, key=int):
        v = xt[k]
        print(f"   src={k:>3}  rows={v['rows']:9d}  nan={v['zip_iv_nan']:9d}  finite={v['zip_iv_finite']:9d}"
              f"   label={labels[k]['label']}")
    print(f"  exact alignment: {rec['exact_alignment']}")
    print(f"  distinct finite zip_iv values: {rec['distinct_finite_zip_iv_values']}")
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
