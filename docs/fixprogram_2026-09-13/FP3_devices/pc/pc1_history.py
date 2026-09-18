#!/usr/bin/env python3
"""P-C1 historical runner v3 (for pc1_intent_replay.py v11; R12-P1): every anchor from <from_ts> to <to_ts> that has a phase_A record is replayed in a
subprocess against the executor tree that was DEPLOYED at its run time (the device's reflog timeline). Per anchor the runner records the device's
status (OK / REFUSED with the named refusal), the tree label, the book-layer exact count, the reshape verdicts (bitwise / within 1e-9) and the
request-population summary. Nothing is folded across anchors into a single "parity" number: the summary counts anchors per outcome class.
Since v11 the summary also carries the PLAN POPULATION (MEASURED_EQUAL / MEASURED_DIFFERENT / MISSING_REQUEST / UNMEASURABLE:<reason> / SKIP_*),
the number of quantity comparisons, and how many anchors had ZERO of them — the class `OK_zero_quantity_measurement` is the shape the reviewer
caught in round 12 (four halted anchors, 966 plans, no comparison, reported as "exact" by v10).
usage: pc1_history.py <from_ts> <to_ts> <out.json>"""
import sys, os, json, time, subprocess, collections
F, T, OUT = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]; HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.environ.get("PC1_REPO") or os.path.expanduser("~/dl_quant_live")
SCR = os.environ.get("PC1_HISTORY_SCRATCH") or "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/pc1_history"
os.makedirs(SCR, exist_ok=True)
U = lambda t: time.strftime("%m-%d %HZ", time.gmtime(t)); pa = {}
for l in open(f"{REPO}/state/anchor_runs.log"):
    if " phase_A: " in l:
        try: d = json.loads(l.split(" phase_A: ", 1)[1])
        except Exception: continue
        a = (d.get("external_wait") or {}).get("nominal_anchor_ts") or d.get("anchor_ts")
        if a: pa[int(a)] = d
res = []
for A in range(F, T + 1, 14400):
    row = {"anchor": A, "utc": U(A)}
    if A not in pa: row["status"] = "NO_PHASE_A"; res.append(row); continue
    out = f"{SCR}/pc1_{A}.json"; r = subprocess.run([sys.executable, f"{HERE}/pc1_intent_replay.py", str(A), out], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out): row["status"] = "DEVICE_FAILED"; row["error"] = (r.stderr.strip().splitlines() or ["?"])[-1][:200]; res.append(row); continue
    j = json.load(open(out)); row["status"] = j.get("status"); row["tree"] = (j.get("executor_tree") or {}).get("label")
    if j.get("status") != "OK": row["refusals"] = j.get("refusals"); res.append(row); continue
    sa = j["stage_A_book_layer"]; sb = j["summary"]; rc = j["reshape_compare"]
    row.update(rid=j["rebalance_id"], eq_pre=j["inputs"]["eq_pre_from_phase_A"], book_exact=f"{sa['exact']}/{sa['n']}", book_max_diff=sa["max_abs_diff_usdt"],
               n_qty_comparisons=sb.get("n_quantity_comparisons"), n_qty_equal=sb.get("n_quantity_equal"), n_unmeasurable=sb.get("n_unmeasurable"),
               plan_population=sb.get("plan_population"), request_population=sb.get("request_population"), population_identity=sb.get("population_identity"),
               reshape_bitwise=f"{len(rc['equal'])}/{rc['n_recorded_keys']}", reshape_within_1e9=rc["all_recorded_keys_within_1e-9"],
               R1_exact=sb["R1_exact"], R1_reject_no_qty=sb["R1_reject_no_qty_evidence"], R1_intent_consistent=sb["R1_intent_consistent_among_rejects"], R1_mismatch=sb["R1_mismatch_or_missing"],
               R2_exact=sb["R2_exact"], R3_consistent=sb["R3_consistent"], n_plan_sent=sb["n_plan_sent"], unexplained=sb["n_unexplained_or_mismatch"],
               all_measurable_exact=sb["all_measurable_exact"], complete_parity=sb["complete_parity"], filters_assumed_current=j["inputs"]["filters_assumed_current"],
               unexplained_categories={k: v for k, v in sb["categories"].items() if "unexplained" in k or "MISMATCH" in k or "MISSING" in k})
    res.append(row)
ok = [r for r in res if r.get("status") == "OK"]
cls = collections.Counter()
for r in res:
    if r.get("status") != "OK": cls[f"{r['status']}:{','.join(r.get('refusals') or [])}" if r.get("refusals") else r["status"]] += 1
    else: cls["OK_book_exact_and_all_measurable_exact" if (r["book_exact"].split("/")[0] == r["book_exact"].split("/")[1] and r["all_measurable_exact"]) else ("OK_zero_quantity_measurement" if (r.get("n_qty_comparisons") or 0) == 0 else "OK_book_exact_requests_unexplained" if r["book_exact"].split("/")[0] == r["book_exact"].split("/")[1] else "OK_book_layer_not_exact")] += 1
import collections as _c
_pp = _c.Counter()
for r in ok:
    for k, v in (r.get("plan_population") or {}).items(): _pp[k] += v
summ = {"n_anchors": len(res), "n_ok": len(ok), "classes": dict(cls), "n_complete_parity": sum(1 for r in ok if r["complete_parity"]),
        "n_zero_measurement_anchors": sum(1 for r in ok if (r.get("n_qty_comparisons") or 0) == 0),
        "n_quantity_comparisons_total": sum(r.get("n_qty_comparisons") or 0 for r in ok), "n_quantity_equal_total": sum(r.get("n_qty_equal") or 0 for r in ok),
        "plan_population_total": dict(_pp), "n_anchors_identity_balanced": sum(1 for r in ok if (r.get("population_identity") or {}).get("plans_balance") and (r.get("population_identity") or {}).get("requests_balance")),
        "n_all_measurable_exact": sum(1 for r in ok if r["all_measurable_exact"]), "n_reshape_within_1e9": sum(1 for r in ok if r["reshape_within_1e9"]),
        "trees": dict(collections.Counter((r.get("tree") or "?")[:7] for r in res if r.get("tree"))),
        "R1_totals": {"exact": sum(r["R1_exact"] for r in ok), "reject_no_qty": sum(r["R1_reject_no_qty"] for r in ok), "mismatch": sum(r["R1_mismatch"] for r in ok)},
        "note": "complete_parity requires zero rejects-without-quantity-evidence; a −5022 post-only reject leaves no request ledger by construction, so anchors with rejects can be all_measurable_exact but never complete_parity"}
json.dump({"device": "pc1_history.py", "version": "v3 (for pc1_intent_replay v11)", "utc": time.strftime("%FT%TZ", time.gmtime()), "from": U(F), "to": U(T), "summary": summ, "rows": res}, open(OUT, "w"), indent=1)
print("summary", json.dumps(summ, ensure_ascii=False)[:900])
for r in res:
    if r.get("status") == "OK": print(f"  {r['utc']} {str(r.get('tree'))[:7]} book {r['book_exact']} (max {r['book_max_diff']:.4f}) reshape {r['reshape_bitwise']} within1e-9 {r['reshape_within_1e9']} R1 {r['R1_exact']}+{r['R1_reject_no_qty']}rej R2 {r['R2_exact']} R3 {r['R3_consistent']}/{r['n_plan_sent']} unexpl {r['unexplained']} {'' if not r['unexplained'] else r['unexplained_categories']}")
    else: print(f"  {r['utc']} {str(r.get('tree'))[:7]} {r['status']} {r.get('refusals') or r.get('error','')}")
