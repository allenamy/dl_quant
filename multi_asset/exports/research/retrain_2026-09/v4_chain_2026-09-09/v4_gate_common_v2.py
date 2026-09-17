#!/usr/bin/env python3
"""v4_gate_common_v2 — the THREE-STATE successor of the frozen `v4_gate_common.finalize` (24e813f1…, untouched).

Why a successor and not an edit (FP2-4, 2026-09-17; R16-T1 / R16R / PENDING_DECISIONS): the frozen `finalize` knows two
states. A gate that could NOT evaluate (its evidence was never supplied) had to choose between lying PASS and printing
"FAIL" for something that did not fail. `v4_gate_roll_paths.py` already computes a VERDICT ∈ {PASS, FAIL, UNAVAILABLE}
but its exit went through the two-state printer. Readers were censused 2026-09-17: every consumer of a gate receipt reads
the JSON `PASS` field (chain_lib.sh L228, chain_v4_monthly.sh preflight L88–90, compare_gate_receipts.py); nobody
parses the printed label; `check_marker REQUIRE_OK` is `require`'s marker, not `finalize`'s. So the contract here is:

  PASS         → PASS=True,  VERDICT="PASS",        exit 0
  FAIL         → PASS=False, VERDICT="FAIL",        exit 3   (reasons in `failed_checks` / `why`)
  UNAVAILABLE  → PASS=False, VERDICT="UNAVAILABLE", exit 3   (reasons in `unevaluated_checks` / `why_unavailable`)

`PASS=False` for UNAVAILABLE is deliberate: an old reader that only knows PASS must refuse it (an unevaluated check is not
a passed check). A reader that knows VERDICT can tell the two apart. The exit code is the same non-zero for both so the
chain stops either way; the receipt and the printed line say which. The receipt schema is bumped so a receipt written by
this function is distinguishable from a two-state one. The frozen module is imported for its hashing helpers and for
`require`, which are unchanged.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from v4_gate_common import sha256_file, utc                      # frozen helpers, unchanged

VERDICTS = ("PASS", "FAIL", "UNAVAILABLE")
RECEIPT_SCHEMA = "v4_gate_common_v2/3 (gate, PASS, VERDICT ∈ PASS|FAIL|UNAVAILABLE, self_sha256, inputs_sha256 bound)"

def verdict_of(res):
    """Derive the three-state verdict from a result dict that may carry VERDICT, or PASS + unevaluated_checks."""
    v = res.get("VERDICT")
    if v in VERDICTS:
        return v
    if res.get("PASS") is True:
        return "PASS"
    if res.get("unevaluated_checks") and not res.get("failed_checks"):
        return "UNAVAILABLE"
    return "FAIL"

def finalize3(gate, res, out_path, inputs=None, exit_code_fail=3, exit_code_unavailable=3):
    """Write the receipt with a three-state VERDICT and EXIT. Same binding as the frozen finalize (gate name, self sha,
    every input's sha) plus VERDICT. PASS=True iff VERDICT == PASS."""
    res = dict(res)
    v = verdict_of(res)
    res["gate"] = gate
    res["VERDICT"] = v
    res["PASS"] = (v == "PASS")
    res["inputs_sha256"] = {k: (sha256_file(p) if p and os.path.exists(p) else None) for k, p in (inputs or {}).items()}
    res["inputs_path"] = dict(inputs or {})
    res["utc"] = utc()
    res["argv"] = list(sys.argv)
    try:
        res["self_sha256"] = sha256_file(os.path.abspath(sys.argv[0]))
    except Exception:                                   # noqa: BLE001 — receipt still written
        res["self_sha256"] = None
    res["receipt_schema"] = RECEIPT_SCHEMA
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(f"{gate} {v} -> {out_path}", flush=True)
    sys.exit(0 if v == "PASS" else (exit_code_unavailable if v == "UNAVAILABLE" else exit_code_fail))
