#!/usr/bin/env python3
"""FP3 item F (K3 refinement, 2026-09-17): which NaN funding cells in the rebuilt panel's tail are LEGITIMATE and which MUST FAIL. Read-only.
Rule (proposed as the K3 criterion): a NaN in any of the five funding columns at (name, t) in the tail is legitimate iff the declared-interval
table (P9) has NO settlement row for that name in the tail window (the name has no settlements there: delisted before / listed after); it must
fail iff P9 has rows for the name in the window (a known settlement stream exists but the panel carries NaN). Also measured: names that the
panel's `elig` column keeps eligible in the tail although they have no settlement at all in the window (eligibility lagging delisting), and
what the FP2 evaluation mask (tradable-by-trades W24H) says for the same cells. Inputs sha-bound; output one receipt.
usage: fx_k3_nan_legitimacy.py <panel.npz> <P9.csv.gz> <umask.npz> <out.json>"""
import csv, gzip, hashlib, json, sys, time, collections
import numpy as np
PAN, P9, UM, OUT = sys.argv[1:5]; sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
Z = np.load(PAN, allow_pickle=True); ts = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; CUT = 1787961600; tail = np.where(ts >= CUT)[0]
FUND = ["f_fund_now", "f_fund_iv", "f_fund_ema", "f_fund_ema_v1", "f_fund_ema_v2"]
p9_rows = collections.defaultdict(list)
with gzip.open(P9, "rt") as f:
    for x in csv.DictReader(f):
        if int(x["ft"]) >= CUT: p9_rows[x["symbol"]].append(int(x["ft"]))
U = np.load(UM, allow_pickle=True); uts = U["ts"].astype(np.int64); usyms = [str(s) for s in U["symbols"]]; um = U["mask"]; upos = {int(t): i for i, t in enumerate(uts)}
out = {"device": "fx_k3_nan_legitimacy.py", "self_sha256": sha(__file__), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "inputs": {PAN: sha(PAN), P9: sha(P9), UM: sha(UM)}, "tail_rows": len(tail), "names": len(syms), "columns": {}, "names_all_nan_tail": [], "must_fail": [], "elig_but_no_settlement": []}
for c in FUND:
    a = Z[c][tail]; nan = np.isnan(a); per_name = nan.all(0); n_must = 0; must = []
    for j in np.where(nan.any(0))[0]:
        s = syms[j]; rows_nan = tail[nan[:, j]]
        if p9_rows.get(s):
            # a settlement stream exists in the window: NaN cells AFTER the first settlement row are not legitimate
            first = min(p9_rows[s]); bad = [int(ts[r]) for r in rows_nan if ts[r] >= first]
            if bad: n_must += len(bad); must.append({"name": s, "n_cells": len(bad), "first_settlement": time.strftime("%Y-%m-%dT%HZ", time.gmtime(first)), "first_bad": time.strftime("%Y-%m-%dT%HZ", time.gmtime(bad[0]))})
    out["columns"][c] = {"nan_cells_tail": int(nan.sum()), "names_all_nan": int(per_name.sum()), "names_partial_nan": int((nan.any(0) & ~per_name).sum()), "must_fail_cells": n_must, "must_fail_names": must[:20]}
nan_all = [j for j in range(len(syms)) if np.isnan(Z["f_fund_iv"][tail, j]).all()]
out["names_all_nan_tail"] = [{"name": syms[j], "p9_rows_in_window": len(p9_rows.get(syms[j], [])), "last_finite_iv": (time.strftime("%Y-%m-%d", time.gmtime(int(ts[np.where(~np.isnan(Z['f_fund_iv'][:, j]))[0][-1]]))) if (~np.isnan(Z["f_fund_iv"][:, j])).any() else None)} for j in nan_all]
out["n_names_all_nan_with_p9_rows"] = sum(1 for r in out["names_all_nan_tail"] if r["p9_rows_in_window"])
el = Z["elig"]
for j in nan_all:
    rows = tail[el[tail, j]]
    if len(rows):
        s = syms[j]; ui = usyms.index(s) if s in usyms else None
        um_true = int(sum(1 for r in rows if ui is not None and int(ts[r]) in upos and um[upos[int(ts[r])], ui])) if ui is not None else None
        fin = np.where(~np.isnan(Z["f_fund_iv"][:, j]))[0]
        out["elig_but_no_settlement"].append({"name": s, "elig_tail_rows": int(len(rows)), "elig_from": time.strftime("%m-%d %HZ", time.gmtime(int(ts[rows[0]]))), "elig_to": time.strftime("%m-%d %HZ", time.gmtime(int(ts[rows[-1]]))), "last_settlement_in_panel": time.strftime("%m-%d %HZ", time.gmtime(int(ts[fin[-1]]))) if len(fin) else None, "eval_umask_true_on_those_rows": um_true, "Y4_finite_tail": int(np.isfinite(Z["Y4"][tail, j]).sum())})
out["VERDICT"] = "LEGITIMATE_ALL" if all(v["must_fail_cells"] == 0 for v in out["columns"].values()) else "MUST_FAIL_PRESENT"
json.dump(out, open(OUT, "w"), indent=1)
print("VERDICT", out["VERDICT"], {c: (v["nan_cells_tail"], v["must_fail_cells"]) for c, v in out["columns"].items()}, "| all-NaN names", len(nan_all), "with p9 rows", out["n_names_all_nan_with_p9_rows"], "| elig-but-no-settlement:", [(r["name"], r["elig_tail_rows"], r["eval_umask_true_on_those_rows"]) for r in out["elig_but_no_settlement"]])
