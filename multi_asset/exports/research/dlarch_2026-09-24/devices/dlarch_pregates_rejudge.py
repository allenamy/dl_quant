#!/usr/bin/env python3
"""dlarch_pregates_rejudge.py — re-issue the pre-gate verdicts from the ALREADY-MEASURED per-year deltas.

lead ruled (2026-09-24): the pre-registered WORDS are the criterion and the code is their implementation;
where they disagree the code is the defect (E-0924-DLARCH-E). The reverse-direction arm A4a was judged
against `delta_year > 0` while its frozen wording says `逐年 >= 2/3 不劣` = `delta_year >= -0.001`.

This device RE-JUDGES ONLY. It does not retrain, refit, or recompute a single IC: it reads the stored
PREGATES.json and applies `dlarch_pregates.gate_verdict` (the single corrected implementation, imported,
not copied). The original verdict line stands in the result document with a correction note.

Load-bearing assertions (the fix must be SURGICAL):
  * every FORWARD arm's verdict must be UNCHANGED -- the direction fix may not touch them;
  * the reverse arm A4a's verdict MUST change (otherwise the fix is not wired to anything);
  * every re-judged delta must equal the stored delta bit-for-bit (proves nothing was recomputed).

READ-ONLY apart from its own output. No GPU.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B dlarch_pregates_rejudge.py \
         PATH,HOME,LC_CTYPE <pregates.json> <out.json>
"""
import os, sys, json, hashlib, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dlarch_pregates import gate_verdict, TEST_YEARS, PL_SEEDS, GATE_A4A, GATE_DELTA, REVERSE_ARMS


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def main():
    assert not sorted(set(os.environ) - set(sys.argv[1].split(","))), "env outside whitelist"
    src, out = sys.argv[2], sys.argv[3]
    R = json.load(open(src))
    rec = {"device": "dlarch_pregates_rejudge.py", "self_sha256": sha(os.path.abspath(__file__)),
           "gate_impl_from": "dlarch_pregates.gate_verdict (imported, single implementation)",
           "gate_impl_sha256": sha(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dlarch_pregates.py")),
           "source_receipt": {"path": src, "sha256": sha(src)},
           "ruling": "lead 2026-09-24: the frozen pre-registration wording is the criterion; the code was the defect (E-0924-DLARCH-E)",
           "recomputed_any_ic": False, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "thresholds": {"forward": GATE_DELTA, "reverse": GATE_A4A, "reverse_arms": list(REVERSE_ARMS)},
           "old_verdicts": {}, "new_verdicts": {}, "gates": {}}
    b = R["arms"]["BASE"]
    pl = [R["arms"][f"PL{s}"] for s in range(PL_SEEDS) if f"PL{s}" in R["arms"]]
    changed, unchanged, delta_mismatch = [], [], []
    for arm in [x for x in ("A4a", "A4b", "A1", "A2", "T6a") if x in R["gates"]]:
        old = R["gates"][arm]["VERDICT"]
        g = gate_verdict(arm, R["arms"][arm], b, pl, TEST_YEARS)
        for mdl in ("ridge", "lgbm"):                      # proves nothing was recomputed
            if g[mdl]["delta_ic_all"] != R["gates"][arm][mdl]["delta_ic_all"]: delta_mismatch.append(f"{arm}/{mdl}/all")
            if list(g[mdl]["delta_by_year"]) != list(R["gates"][arm][mdl]["delta_by_year"]): delta_mismatch.append(f"{arm}/{mdl}/years")
        rec["old_verdicts"][arm] = old; rec["new_verdicts"][arm] = g["VERDICT"]; rec["gates"][arm] = g
        (changed if g["VERDICT"] != old else unchanged).append(arm)
    rec["changed"] = changed; rec["unchanged"] = unchanged; rec["delta_mismatch"] = delta_mismatch
    fwd = [a for a in ("A4b", "A1", "A2", "T6a") if a in rec["new_verdicts"]]
    rec["surgical"] = {"forward_arms": fwd,
                       "forward_arms_unchanged": all(a in unchanged for a in fwd),
                       "reverse_arm_changed": all(a in changed for a in REVERSE_ARMS if a in rec["new_verdicts"]),
                       "deltas_bit_identical": not delta_mismatch}
    assert not delta_mismatch, f"re-judge recomputed a delta: {delta_mismatch}"
    assert rec["surgical"]["forward_arms_unchanged"], f"the direction fix moved a forward arm: {changed}"
    assert rec["surgical"]["reverse_arm_changed"], "the direction fix changed nothing -- not wired"
    tmp = out + ".tmp"; open(tmp, "w").write(json.dumps(rec, indent=1, allow_nan=False)); os.replace(tmp, out)
    print(f"PREGATES_REJUDGE verdicts={json.dumps(rec['new_verdicts'])} changed={changed} "
          f"forward_unchanged={rec['surgical']['forward_arms_unchanged']} "
          f"deltas_bit_identical={rec['surgical']['deltas_bit_identical']} json={sha(out)[:16]}", flush=True)


if __name__ == "__main__":
    main()
