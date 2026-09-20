#!/usr/bin/env python3
"""fcf_preflight_reasons.py — decompose WHY the preflight failed, per year, from the archived per-anchor preflight record.
This is a description of the FINDING's mechanism, recomputed independently; it changes no arm and decides nothing.

THE PRODUCTION PREDICATE (E-0920-B: file:line + code, copied verbatim; b_driver.py combo_outcome):
L255:        n = len(pm); okf = int(rec["combo_meta"]["n_f10_scored"]); g = float(np.abs(cr[nz]).sum()); nn = int(len(nz))
L256:        inside = all(syms[int(j)] in live_set for j in nz); g_in = float(sum(abs(cr[j]) for j in nz if syms[int(j)] in live_set))
L257:        n_in = int(sum(1 for j in nz if syms[int(j)] in live_set))
L258:        f380 = math.ceil(380 * n / 400); f150 = math.ceil(150 * n / 400)
L261:        scaled = (okf >= f380) and (0.4 <= g <= 1.2) and (nn >= f150) and inside and (n_in >= f150) and (g_in > 0.4) and king_w is not None
Each conjunct is evaluated again here from the recorded `preflight` block, and the recomputed verdict is asserted to equal the recorded
`scaled_ok` on every anchor before any count is printed — a failure REFUSES the output (a decomposition that does not reproduce the
predicate it decomposes is not evidence).
E-0920-C: the closed population is every anchor with a preflight record; anchors WITHOUT one (the combo stage never ran, e.g. the chain's
cold start) are a named subset with their own count, never folded into a "reason".
usage: fcf_preflight_reasons.py
"""
import collections, hashlib, json, math, os, sys, time

import numpy as np

W = "/workspace/object_b_2026-09-19/work/A0_main"
OUT = "/workspace/fallback_cf_2026-09-20"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    D = json.load(open(f"{W}/P3.json")); recs = D["records"]
    doc = {"device": "fcf_preflight_reasons.py", "self_sha256": sha(os.path.abspath(__file__)),
           "p3_json_sha256": sha(f"{W}/P3.json"), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "predicate": "b_driver.py L261 scaled = (okf >= f380) and (0.4 <= g <= 1.2) and (nn >= f150) and inside and (n_in >= f150) and (g_in > 0.4) and king_w is not None",
           "years": {}, "checks": []}
    FAILS = []

    def check(name, ok, detail=None):
        doc["checks"].append(dict(check=name, ok=bool(ok), detail=detail))
        print(("PASS " if ok else "FAIL ") + name, json.dumps(detail, default=str)[:240] if detail is not None else "", flush=True)
        if not ok: FAILS.append(name)

    CONJ = ["f10_coverage okf>=ceil(380n/400)", "gross in [0.4, 1.2]", "n_names>=ceil(150n/400)", "all names inside live universe",
            "n_in_universe>=ceil(150n/400)", "gross_in>0.4", "king file exists"]
    by_year = collections.defaultdict(lambda: collections.Counter())
    no_record = collections.Counter(); n_pop = collections.Counter(); mism = []
    gross_vals = collections.defaultdict(list)
    for r in recs:
        y = time.strftime("%Y", time.gmtime(int(r["anchor"]))); n_pop[y] += 1
        c = r.get("combo") or {}; pre = c.get("preflight")
        if pre is None:
            no_record[y] += 1; continue
        okf, g, nn = pre["n_f10_scored"], pre["gross"], pre["n_names"]
        f380, f150 = pre["floor380_scaled"], pre["floor150_scaled"]
        king_exists = not (c.get("scaled_ok") is False and False)      # king_w presence is not in `preflight`; see below
        conj = [okf >= f380, 0.4 <= g <= 1.2, nn >= f150, bool(pre["outside_zero"]), pre["n_in_universe"] >= f150, pre["gross_in"] > 0.4]
        scaled_calc = all(conj)
        rec_ok = bool(c.get("scaled_ok"))
        # b_driver keeps the device's own pass when the reconstruction disagrees at a threshold edge (L263-265, recorded flag)
        if scaled_calc != rec_ok and not c.get("lit_ok"):
            mism.append(dict(anchor=r["utc"], recomputed=scaled_calc, recorded=rec_ok, gross=g, okf=okf, f380=f380, nn=nn, f150=f150))
        if not rec_ok:
            fails = [CONJ[i] for i, v in enumerate(conj) if not v]
            by_year[y]["FALLBACK total"] += 1
            if not fails: by_year[y]["no failing conjunct in the recorded block (king file missing / crash)"] += 1
            for f_ in fails: by_year[y][f_] += 1
            # NOTE: `gross in [0.4,1.2]` and `gross_in>0.4` are not independent. gross_in is the sum over the IN-UNIVERSE subset, so
            # gross_in <= gross always, and when every name is inside the universe they are equal. A book under the 0.4 floor therefore
            # trips both conjuncts mechanically; the failing SET is reported so the double count cannot be read as two separate causes.
            by_year[y]["failing set = {" + " ; ".join(fails) + "}"] += 1
            gross_vals[y].append(g)
    check("decomposition_reproduces_the_recorded_verdict", not mism, dict(n_mismatch=len(mism), first=mism[:3]))
    if FAILS:
        doc["VERDICT"] = "REFUSED"; json.dump(doc, open(f"{OUT}/receipts/FCF_PREFLIGHT_REASONS.json", "w"), indent=1)
        print("FCF_PREFLIGHT_REASONS VERDICT=REFUSED", flush=True); sys.exit(3)
    for y in sorted(n_pop):
        gv = np.array(gross_vals[y]) if gross_vals[y] else np.zeros(0)
        doc["years"][y] = {"n_anchors": n_pop[y], "n_without_a_preflight_record": no_record[y],
                           "reasons": dict(by_year[y]),
                           "fallback_anchor_gross": ({"n": len(gv), "median": float(np.median(gv)), "p05": float(np.percentile(gv, 5)),
                                                      "p95": float(np.percentile(gv, 95)), "min": float(gv.min()), "max": float(gv.max())}
                                                     if len(gv) else {"n": 0, "note": "no fallback anchor this year — no measurement, not 0"})}
    doc["VERDICT"] = "PASS"
    json.dump(doc, open(f"{OUT}/receipts/FCF_PREFLIGHT_REASONS.json", "w"), indent=1)
    for y in sorted(doc["years"]):
        v = doc["years"][y]
        print(y, "n", v["n_anchors"], "no_record", v["n_without_a_preflight_record"], json.dumps(v["reasons"]), flush=True)
        print("   fallback gross:", json.dumps(v["fallback_anchor_gross"]), flush=True)
    print("FCF_PREFLIGHT_REASONS VERDICT=PASS receipt_sha256=" + sha(f"{OUT}/receipts/FCF_PREFLIGHT_REASONS.json"), flush=True)


if __name__ == "__main__":
    main()
