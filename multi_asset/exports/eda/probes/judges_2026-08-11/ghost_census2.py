#!/usr/bin/python3
"""READ-ONLY census, second pass — fixes two flaws in the first pass:

 1. Consumers that WRITE (WD.run, score_post_fix -> defect D1) polluted the very trees under
    test, so later consumers saw rows the earlier ones had created. Each (consumer, tree) pair
    now gets its OWN fresh copy.
 2. Volatile fields (network latency `ms`, capture timestamps, the tree's own path) made three
    consumers look non-immune when nothing about them had changed. Those are stripped before
    comparison, and the stripping is listed so it cannot hide a real difference.

Nothing under dl_quant_live is written.
"""
import json, os, re, shutil, sys, tempfile, collections

REPO = "/Users/haosiyu/dl_quant_live"
for d in ("live", "ops", "signal"):
    sys.path.insert(0, os.path.join(REPO, d))
SCRATCH = tempfile.mkdtemp(prefix="census2_")
SRC = os.path.join(REPO, "state/testnet/pilot_log")
SCORER_IDS = {"FLATTEN-20260726T130451Z", "FLATTEN-20260726T130511Z"}

VOLATILE = {"ms", "captured_utc", "pilot_log_root", "root", "evaluated_utc", "elapsed_s",
            "built_at", "ts", "written_utc", "state_dir"}


def is_signature(o):
    return (str(o.get("rebalance_id", "")).startswith("FLATTEN-")
            and o.get("submit_ts") is None
            and o.get("filled_notional") is None
            and o.get("terminal_reason") == "venue_reject")


ARMS = {"all": lambda o: False,
        "noscorer": lambda o: o.get("rebalance_id") in SCORER_IDS,
        "nosig": is_signature}
_seq = [0]


def fresh(arm):
    _seq[0] += 1
    dst = os.path.join(SCRATCH, f"t{_seq[0]}_{arm}")
    shutil.copytree(SRC, dst)
    drop = ARMS[arm]
    for day in sorted(os.listdir(dst)):
        p = os.path.join(dst, day, "orders.jsonl")
        if not os.path.exists(p):
            continue
        keep = [l.strip() for l in open(p) if l.strip() and not drop(json.loads(l))]
        with open(p, "w") as f:
            f.write("\n".join(keep) + ("\n" if keep else ""))
    return dst


def scrub(x, treepath):
    if isinstance(x, dict):
        return {k: scrub(v, treepath) for k, v in sorted(x.items()) if k not in VOLATILE}
    if isinstance(x, list):
        return [scrub(v, treepath) for v in x]
    if isinstance(x, str):
        s = x.replace(treepath, "<TREE>")
        return re.sub(r"/(var|tmp|Users)/[^\s\"]*", "<PATH>", s)
    return x


def norm(x, treepath):
    return json.dumps(scrub(x, treepath), sort_keys=True, default=str)


import pilot_log as PL, pilot_metrics as PM, reconcile as RC
import watchdog as WD, watchdog_inputs as WI
import score_post_fix as SPF, capture_halt_evidence as CHE


def rows(root, table):
    out = []
    for d in PL.available_days(root):
        out.extend(PL.read_day(root, d).get(table, []))
    return out


def regimes(root):
    return {a["anchor_ts"]: a["regime_at_anchor"] for a in rows(root, "anchors")}


CONSUMERS = collections.OrderedDict([
    ("PM.m1_effective_cost", lambda r: PM.m1_effective_cost(rows(r, "orders"), regimes(r))),
    ("PM.m3_fill_rate", lambda r: PM.m3_fill_rate(rows(r, "orders"))),
    ("PM.m4_turnover", lambda r: PM.m4_turnover(rows(r, "orders"), rows(r, "anchors"))),
    ("PM.m5_weight_fidelity", lambda r: PM.m5_weight_fidelity(
        rows(r, "orders"), rows(r, "anchors"), rows(r, "position_readback"))),
    ("PM.compute (M1-M6)", lambda r: PM.compute(r, verbose=False)),
    ("RC.reconcile", lambda r: RC.reconcile([(d, PL.read_day(r, d)) for d in PL.available_days(r)])),
    ("RC.signed_fills_by_anchor", lambda r: RC.signed_fills_by_anchor(rows(r, "orders"))),
    ("WI.derive_ops_stats", lambda r: WI.derive_ops_stats(r)),
    ("WI.collect", lambda r: WI.collect(r)),
    ("WD.run (7 conditions)", lambda r: (lambda o, v, _: WD.run(
        r, broker=WD.MockBroker(), venue_events=v, ops_stats=o, verbose=False,
        state_dir=tempfile.mkdtemp())[0])(*WI.collect(r))),
    ("score_post_fix.score E1-E6", lambda r: SPF.score(root=r, day="20260726",
                                                       rebalance_id="A1785067246")),
    ("capture_halt_evidence.capture", lambda r: CHE.capture(day="20260726", root=r)),
])

print(f"src={SRC}\nscratch={SCRATCH}\nvolatile keys stripped: {sorted(VOLATILE)}\n")
print(f"{'consumer':32s} {'206 scorer rows':>16s} {'all 208 sig rows':>17s}   note")
print("-" * 96)
bad = []
for name, fn in CONSUMERS.items():
    outs = {}
    for arm in ("all", "noscorer", "nosig"):
        t = fresh(arm)
        try:
            outs[arm] = norm(fn(t), t)
        except Exception as e:
            outs[arm] = f"__ERROR__ {type(e).__name__}: {e}"
    a, b, c = outs["all"], outs["noscorer"], outs["nosig"]
    im_s, im_g = (a == b), (a == c)
    note = ""
    if a.startswith("__ERROR__"):
        note = "RAISES on the production tree"
    if not im_g and not a.startswith("__ERROR__"):
        note = "output changes"
    if not (im_s and im_g):
        bad.append((name, outs))
    print(f"{name:32s} {'IMMUNE' if im_s else 'AFFECTED':>16s} {'IMMUNE' if im_g else 'AFFECTED':>17s}   {note}")

print("\n" + "=" * 96)
print("DIFFERENCES, FIELD BY FIELD")
for name, outs in bad:
    print(f"\n-- {name}")
    a, c = outs["all"], outs["nosig"]
    if a.startswith("__ERROR__") or c.startswith("__ERROR__"):
        print(f"   with ghosts    : {a[:200]}")
        print(f"   without ghosts : {c[:200]}")
        continue
    da, dc = json.loads(a), json.loads(c)

    def walk(x, y, path=""):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in sorted(set(x) | set(y)):
                walk(x.get(k), y.get(k), f"{path}.{k}")
        elif x != y:
            print(f"   {path:52s} with={x!s:>22s}   without={y!s}")
    walk(da, dc)
