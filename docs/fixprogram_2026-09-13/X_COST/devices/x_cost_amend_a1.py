#!/usr/bin/env python3
"""X-COST AMENDMENT A1 — committed after run 1 of x_cost_decompose.py and BEFORE this script is run.

WHY (found reading run 1, recorded as a device defect, not a result):
  A1.1 Run 1's D9 driver ratios (pooled maker fill ratio, residual pool / maker intent, first-attempt -5022 rate) put
       HALTED anchors' blocked maker rows into maker intent and plan counts. Halted anchors trade nothing (D = 0) but
       carry a full book of intent (164k-235k USDT each; 4 in S2b, 6 in S3), so those ratios are diluted there and
       are VOID as printed. The taker-share identity, component shares and Δ-by-component are unaffected (halted
       anchors contribute 0 to M and T). A1 recomputes the D9 ratios over non-halted anchors only.
  A1.2 Run 1 did not separate the two ways the from_reject taker share can grow: more first-attempt post-only rejects
       (a bigger reject pool) versus more of that pool converted to IOC (the requote experiment's direct arm skips the
       re-quote by design). A1 adds a factorisation and a counterfactual for the direct arm that uses only
       PRE-TREATMENT quantities of the experiment and a PRE-EXPERIMENT conversion baseline:
         share_FR = (RI / MI) x (IOC_FR / RI) x (MI / D)
           MI     = Σ|intended_full| over attempt-1 maker plans (non-halted)
           RI     = Σ|intended_full| over first-attempt -5022 plans (pooled over arms; rejection precedes assignment)
           IOC_FR = K2d + K2q + K2e + K2n taker notional (run 1 components)
         c0     = IOC_FR / RI in S2a excluding REBUILD anchors (post-deposit scale, before the experiment: every
                  rejected plan was re-quoted); sensitivity c0' from S1a
         RI_dir = Σ|intended_residual| over from_reject top-up rows with requote_arm == direct (all terminal reasons).
                  A direct plan always ends in such a row and its residual is the unfilled maker delta, fixed before
                  assignment => pre-treatment. No requote-arm quantity other than run 1's K2q notional is used.
         attributable_direct(S) = K2d(S) - c0 x RI_dir(S)     (INFERRED counterfactual; bounds: [K2d - RI_dir, K2d])
  Barrier unchanged: same allow-lists (imported), no price/mid/markout/placement field; self-check extended to this file.

Usage: python3 x_cost_amend_a1.py <receipts_dir>      (reads receipts/x_cost_per_anchor.json from run 1)
Exit: 0 ok; 4 inputs changed during run; 5 barrier; 6 run-1 receipt missing or its device sha differs.
"""
import json
import os
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import x_cost_decompose as XC   # noqa: E402

RUN1_DEVICE_SHA = "bf41270fcef9f1d5"


def barrier_self():
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    bad = [t for t in XC.FORBIDDEN if ('"' + t + '"') in src or ("'" + t + "'") in src]
    if bad:
        print(f"BARRIER VIOLATION in amendment: {bad}")
        sys.exit(5)
    XC._barrier_selfcheck()
    return {"amendment_forbidden_tokens_found": 0}


def main(outdir):
    barrier = barrier_self()
    p1 = json.load(open(os.path.join(outdir, "x_cost_periods.json")))
    if not p1.get("self_sha256", "").startswith(RUN1_DEVICE_SHA):
        print("RUN-1 RECEIPT DEVICE SHA MISMATCH"); sys.exit(6)
    recs = json.load(open(os.path.join(outdir, "x_cost_per_anchor.json")))
    by_rid = {r["rid"]: r for r in recs if r.get("rid")}
    inputs = [os.path.join(XC.ROOT, d, "orders.jsonl") for d in XC.DAYS if os.path.exists(os.path.join(XC.ROOT, d, "orders.jsonl"))]
    sha0 = {p: XC.guarded_sha(p) for p in inputs}
    self_sha, _ = XC.guarded_sha(os.path.abspath(__file__))
    anomalies = []
    RI = defaultdict(float); RI_dir = defaultdict(float)
    seen_plan = set()
    for d in XC.DAYS:
        for r in XC.read_rows(os.path.join(XC.ROOT, d, "orders.jsonl"), XC.ALLOW_ORDERS, anomalies, f"orders:{d}"):
            rid, sym, ot = r.get("rebalance_id"), r.get("symbol"), r.get("order_type")
            if rid not in by_rid:
                continue
            if ot == "maker" and r.get("attempt_idx") == 1:
                if r.get("terminal_reason") == "venue_reject" and "[-5022]" in str(r.get("note") or "") and (rid, sym) not in seen_plan:
                    seen_plan.add((rid, sym))
                    fi = XC.fnum(r.get("intended_full"))
                    if fi is None:
                        fi = XC.fnum(r.get("intended_notional"))
                    RI[rid] += abs(fi or 0.0)
            elif ot == "topup_taker" and r.get("topup_source") == "from_reject" and r.get("requote_arm") == "direct":
                ir = XC.fnum(r.get("intended_residual"))
                if ir is None:
                    ir = XC.fnum(r.get("intended_notional"))
                RI_dir[rid] += abs(ir or 0.0)

    FR = ("K2d", "K2q", "K2e", "K2n")

    def agg(rows):
        rows = [r for r in rows if not r["halted"]]
        MI = sum(r["maker_intent"] for r in rows); D = sum(r["D"] for r in rows)
        M_maker = sum(r["M_maker"] for r in rows)
        npl = sum(r["n_plans"] for r in rows); nrj = sum(r["n_first_5022"] for r in rows)
        ri = sum(RI.get(r["rid"], 0.0) for r in rows); rid_ = sum(RI_dir.get(r["rid"], 0.0) for r in rows)
        ioc = {k: sum(r["components"][k] for r in rows) for k in FR}
        ioc_fr = sum(ioc.values())
        pool = defaultdict(float)
        for r in rows:
            for k, v in r["resid_pool"].items():
                pool[k] += v
        return {"n_non_halted": len(rows), "D": round(D, 4), "MI": round(MI, 4),
                "pooled_maker_fill_ratio": (round(M_maker / MI, 6) if MI else None),
                "first_attempt_5022_rate": (round(nrj / npl, 6) if npl else None),
                "RI": round(ri, 4), "RI_over_MI": (round(ri / MI, 6) if MI else None),
                "IOC_FR": round(ioc_fr, 4), "IOC_FR_over_RI": (round(ioc_fr / ri, 6) if ri else None),
                "MI_over_D": (round(MI / D, 6) if D else None),
                "share_FR": (round(ioc_fr / D, 6) if D else None),
                "share_FR_check_product": (round((ri / MI) * (ioc_fr / ri) * (MI / D), 6) if (MI and ri and D) else None),
                "K2d": round(ioc["K2d"], 4), "RI_direct": round(rid_, 4),
                "resid_pool_over_MI": {k: (round(v / MI, 6) if MI else None) for k, v in sorted(pool.items())}}

    out = {"device": os.path.basename(__file__), "self_sha256": self_sha, "run1_device_sha256_prefix": RUN1_DEVICE_SHA,
           "barrier": barrier, "run_started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "subperiods_non_halted": {}, "subperiods_non_halted_ex_rebuild": {}}
    for lab in XC.SUB:
        rows = [r for r in recs if r["sub"] == lab]
        out["subperiods_non_halted"][lab] = agg(rows)
        out["subperiods_non_halted_ex_rebuild"][lab] = agg([r for r in rows if not r["rebuild"]])
    for lab in XC.BOUNDS:
        rows = [r for r in recs if r["period"] == lab]
        out["subperiods_non_halted"][lab] = agg(rows)
        out["subperiods_non_halted_ex_rebuild"][lab] = agg([r for r in rows if not r["rebuild"]])
    exr = out["subperiods_non_halted_ex_rebuild"]
    c0 = exr["S2a"]["IOC_FR_over_RI"]; c0s = exr["S1a"]["IOC_FR_over_RI"]
    cf = {}
    for lab in ("S2b", "S3", "P3"):
        for tag, tbl in (("all", out["subperiods_non_halted"]), ("ex_rebuild", exr)):
            o = tbl[lab]
            if not o["D"]:
                continue
            k2d, rd, D = o["K2d"], o["RI_direct"], o["D"]
            cf[f"{lab}:{tag}"] = {
                "K2d_share": round(k2d / D, 6),
                "attributable_direct_share_c0_S2a": (round((k2d - c0 * rd) / D, 6) if c0 is not None else None),
                "attributable_direct_share_c0_S1a": (round((k2d - c0s * rd) / D, 6) if c0s is not None else None),
                "bounds_share": [round((k2d - rd) / D, 6), round(k2d / D, 6)],
                "c0_S2a": c0, "c0_S1a": c0s, "RI_direct_over_D": round(rd / D, 6)}
    out["counterfactual_direct_arm"] = cf
    sha1 = {p: XC.guarded_sha(p) for p in inputs}
    changed = [p for p in inputs if sha0[p] != sha1[p]]
    out["inputs_orders_sha256"] = {p: sha0[p][0] for p in inputs}
    out["inputs_changed_during_run"] = changed
    json.dump(out, open(os.path.join(outdir, "x_cost_a1.json"), "w"), indent=1, ensure_ascii=False)
    if changed:
        print(f"INPUTS CHANGED {changed}"); sys.exit(4)
    print(f"SUMMARY x_cost_amend_a1 self_sha256={self_sha[:16]} anomalies={len(anomalies)} rc=0")


if __name__ == "__main__":
    main(sys.argv[1])
