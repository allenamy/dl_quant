#!/usr/bin/python3
"""READ-ONLY census: does any consumer of orders.jsonl change its output because of the
208 never-submitted FLATTEN rows?

Method is BEHAVIOURAL, not a code read: build two copies of the pilot_log tree (verbatim /
ghosts removed), run every consumer against both, diff the outputs. A consumer that is immune
by luck and one that is immune by construction both show "no diff" — so each no-diff is then
attributed to the specific guard that produced it, by reading the code.

Nothing under /Users/haosiyu/dl_quant_live is written: the copies live in the scratchpad, and
the one consumer that writes (WD.run -> _write_flatten_rows, defect D1) is pointed at a copy.
"""
import json, os, shutil, sys, tempfile, collections

REPO = "/Users/haosiyu/dl_quant_live"
for d in ("live", "ops", "signal"):
    sys.path.insert(0, os.path.join(REPO, d))
SCRATCH = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(REPO, "state/testnet/pilot_log")

SCORER_IDS = {"FLATTEN-20260726T130451Z", "FLATTEN-20260726T130511Z"}


def is_signature(o):
    """The row class the ruling is about: an order that never left this process."""
    return (str(o.get("rebalance_id", "")).startswith("FLATTEN-")
            and o.get("submit_ts") is None
            and o.get("filled_notional") is None
            and o.get("terminal_reason") == "venue_reject")


def build(tag, drop):
    dst = os.path.join(SCRATCH, "tree_" + tag)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(SRC, dst)
    n_drop = 0
    for day in sorted(os.listdir(dst)):
        p = os.path.join(dst, day, "orders.jsonl")
        if not os.path.exists(p):
            continue
        keep = []
        for line in open(p):
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            if drop(o):
                n_drop += 1
                continue
            keep.append(line)
        with open(p, "w") as f:
            f.write("\n".join(keep) + ("\n" if keep else ""))
    return dst, n_drop


T_ALL, _ = build("all", lambda o: False)
T_NOSCORER, n1 = build("noscorer", lambda o: o.get("rebalance_id") in SCORER_IDS)
T_NOSIG, n2 = build("nosig", is_signature)
print(f"trees built:  all=verbatim   noscorer(-{n1} rows)   nosig(-{n2} rows)")

import pilot_log as PL, pilot_metrics as PM, reconcile as RC
import watchdog as WD, watchdog_inputs as WI


def norm(x):
    return json.dumps(x, sort_keys=True, default=str)


RESULTS = collections.OrderedDict()


def run_consumer(name, fn):
    outs = {}
    for tag, root in (("all", T_ALL), ("noscorer", T_NOSCORER), ("nosig", T_NOSIG)):
        try:
            outs[tag] = norm(fn(root))
        except Exception as e:
            outs[tag] = f"__ERROR__ {type(e).__name__}: {e}"
    same_scorer = outs["all"] == outs["noscorer"]
    same_sig = outs["all"] == outs["nosig"]
    RESULTS[name] = {"immune_to_206_scorer_rows": same_scorer,
                     "immune_to_all_208_signature_rows": same_sig,
                     "out_all": outs["all"], "out_nosig": outs["nosig"]}
    flag = "OK " if (same_scorer and same_sig) else "DIFF"
    print(f"  [{flag}] {name:38s} scorer-immune={same_scorer}  signature-immune={same_sig}")


def _day_rows(root, table):
    days = PL.available_days(root)
    agg = []
    for d in days:
        agg.extend(PL.read_day(root, d).get(table, []))
    return agg


def _regimes(root):
    return {a["anchor_ts"]: a["regime_at_anchor"] for a in _day_rows(root, "anchors")}


print("\n=== CONSUMER-BY-CONSUMER (behavioural diff) ===")
run_consumer("PM.m1_effective_cost",
             lambda r: PM.m1_effective_cost(_day_rows(r, "orders"), _regimes(r)))
run_consumer("PM.m3_fill_rate", lambda r: PM.m3_fill_rate(_day_rows(r, "orders")))
run_consumer("PM.m4_turnover",
             lambda r: PM.m4_turnover(_day_rows(r, "orders"), _day_rows(r, "anchors")))
run_consumer("PM.m5_weight_fidelity",
             lambda r: PM.m5_weight_fidelity(_day_rows(r, "orders"), _day_rows(r, "anchors"),
                                             _day_rows(r, "position_readback")))
run_consumer("PM.compute (M1-M6 driver)", lambda r: PM.compute(r, verbose=False))
run_consumer("RC.reconcile",
             lambda r: RC.reconcile([(d, PL.read_day(r, d)) for d in PL.available_days(r)]))
run_consumer("RC.signed_fills_by_anchor",
             lambda r: RC.signed_fills_by_anchor(_day_rows(r, "orders")))
run_consumer("WI.derive_ops_stats", lambda r: WI.derive_ops_stats(r))
run_consumer("WI.collect", lambda r: WI.collect(r))


def _wd(root):
    ops_s, ve, _ = WI.collect(root)
    ev, _, _ = WD.run(root, broker=WD.MockBroker(), venue_events=ve, ops_stats=ops_s,
                      verbose=False, state_dir=tempfile.mkdtemp())
    ev.pop("evaluated_utc", None)
    return ev


run_consumer("WD.run (all 7 conditions)", _wd)

import score_post_fix as SPF
run_consumer("score_post_fix.score (E1-E6)",
             lambda r: SPF.score(root=r, day="20260726", rebalance_id="A1785067246"))

import capture_halt_evidence as CHE
run_consumer("capture_halt_evidence.capture",
             lambda r: CHE.capture(day="20260726", root=r))

print("\n=== WHERE THE GHOSTS DO LAND (reported, not gated) ===")
m1_all = PM.m1_effective_cost(_day_rows(T_ALL, "orders"), _regimes(T_ALL))
m1_sig = PM.m1_effective_cost(_day_rows(T_NOSIG, "orders"), _regimes(T_NOSIG))
print("  m1.protective_flatten_cost  WITH ghosts :", norm(m1_all.get("protective_flatten_cost")))
print("  m1.protective_flatten_cost  WITHOUT     :", norm(m1_sig.get("protective_flatten_cost")))
print("  m1.c_bps_overall            with/without:",
      m1_all.get("c_bps_overall"), "/", m1_sig.get("c_bps_overall"))

print("\n=== DIFF DETAIL for any consumer that changed ===")
for k, v in RESULTS.items():
    if not (v["immune_to_206_scorer_rows"] and v["immune_to_all_208_signature_rows"]):
        print(f"  -- {k}")
        a, b = v["out_all"], v["out_nosig"]
        print("     ALL  :", a[:600])
        print("     NOSIG:", b[:600])

print("\n=== SUMMARY ===")
bad = [k for k, v in RESULTS.items()
       if not (v["immune_to_206_scorer_rows"] and v["immune_to_all_208_signature_rows"])]
print(f"  consumers tested : {len(RESULTS)}")
print(f"  not immune       : {len(bad)}  {bad}")
