#!/usr/bin/env python3
"""alloc_causality.py — DECISION_RULE_combination_layer §2-0 causality probe, every seat rule.

For each rule and each probe anchor i: poison every LR row >= i (+1e3 on finite entries) and require the rule's seat at i to be unchanged
(alloc_rules.causality_probe). PASS for a deployable rule = unchanged at every probe anchor.
POSITIVE CONTROL: the oracle (look-ahead by construction) MUST be flagged (changed at >= 1 probe anchor); if the probe cannot see the
oracle's look-ahead it cannot certify anything, and the verdict is PROBE_BLIND.
Probe anchors: 8 fixed indices spread over the axis where every rule is data-driven (after the 1800-row warmup), chosen by position,
not by value: quantiles 0.2 .. 0.9 of the ready rows.
usage: /workspace/venv/bin/python -B alloc_causality.py <out.json>
"""
import os, sys, json, hashlib, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import alloc_rules as R

LEGS = "/dev/shm/news2_2026-09-23/work/legs.npz"
RULES = ("inservice", "cap050", "look1800", "invvol")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    L = np.load(LEGS); LR = L["LR"]; WL = L["WL"]; ready = np.flatnonzero(L["ready"])
    idx = [int(ready[int(q * (len(ready) - 1))]) for q in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)]
    out = {"device": "alloc_causality.py", "self_sha256": sha(os.path.abspath(__file__)), "alloc_rules_sha256": sha(os.path.join(HERE, "alloc_rules.py")),
           "legs_sha256": sha(LEGS), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "probe_anchor_index": idx,
           "probe_anchor_utc": [time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(L["E_ts"][i]))) for i in idx], "rules": {}}
    for r in RULES + ("oracle",):
        t0 = time.time(); res = R.causality_probe(r, LR, WL, idx)
        out["rules"][r] = {"unchanged_at": res, "n_unchanged": sum(res.values()), "n": len(res), "seconds": round(time.time() - t0, 1)}
        print(f"CAUSALITY {r:10s} unchanged {sum(res.values())}/{len(res)}", flush=True)
    ctl = out["rules"]["oracle"]["n_unchanged"] < len(idx)
    ok = all(out["rules"][r]["n_unchanged"] == len(idx) for r in RULES)
    out["positive_control_oracle_flagged"] = bool(ctl)
    out["VERDICT"] = "PROBE_BLIND" if not ctl else ("PASS" if ok else "FAIL")
    json.dump(out, open(sys.argv[1] + ".tmp", "w"), indent=1); os.replace(sys.argv[1] + ".tmp", sys.argv[1])
    assert json.load(open(sys.argv[1]))["self_sha256"] == out["self_sha256"]
    print(f"ALLOC_CAUSALITY VERDICT={out['VERDICT']} oracle_flagged={ctl}", flush=True)


if __name__ == "__main__":
    main()
