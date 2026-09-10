"""Shared gate discipline for the v4 chain (review b0a573a1 P1-PIPE, 2026-09-09; round 3 after review 31fa3e4e, 2026-09-10).

★ THE RULE: a gate is a PROGRAM CONDITION, not a printed word. Every gate (a) writes ONE structured
  verdict JSON {gate, PASS, inputs_sha256, utc, argv, self_sha256, ...}, (b) exits 0 iff PASS, else
  3; and every chain stage that depends on a gate REQUIRES its receipt through `require` — PASS
  true AND the receipt's input SHAs equal to the files the stage is about to consume. "The file
  exists" (the old STEP1_PASS marker) and "the child printed PASS" are not evidence of either.

★ ROUND 3 (review 31fa3e4e §2): a receipt is an IDENTITY, not a boolean. `require` now also demands
  (1) the receipt's `gate` equals the gate the caller expected — a PASS from an unrelated gate, or a
      stale receipt left by an older stage under the same file name, is not this stage's permission;
  (2) the receipt's `self_sha256` exists, is a real sha256 (64 hex, not all-zero) and, when the
      caller pins one, equals the gate source the caller trusts;
  (3) the caller DECLARES at least one dependency — `require` with an empty input list verified
      nothing and read as a pass, which is a gate with no door.
  A caller that cannot name its gate or its inputs is refused; that is the point.

CLI:
  python v4_gate_common.py require <receipt.json> gate=<expected_gate> [self_sha=<sha256>] name=path [name=path ...]
                                                                       # exit 0 iff PASS & identity & fresh
  python v4_gate_common.py sha <path> [...]                            # print sha256 per file
"""
import hashlib
import json
import os
import re
import sys
import time

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(p, chunk=16 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def finalize(gate, res, out_path, inputs=None, exit_code_fail=3):
    """Write the verdict and EXIT. `inputs` = {name: path} hashed into the receipt.
    The receipt carries the gate's NAME, its own source sha and every input's sha — the three
    things `require` checks — so a receipt is bound to (which gate, which code, which data)."""
    res = dict(res)
    res["gate"] = gate
    res["PASS"] = bool(res.get("PASS"))
    res["inputs_sha256"] = {k: (sha256_file(v) if v and os.path.exists(v) else None) for k, v in (inputs or {}).items()}
    res["inputs_path"] = dict(inputs or {})
    res["utc"] = utc()
    res["argv"] = list(sys.argv)
    try:
        res["self_sha256"] = sha256_file(os.path.abspath(sys.argv[0]))
    except Exception:                                   # noqa: BLE001 — receipt still written
        res["self_sha256"] = None
    res["receipt_schema"] = "v4_gate_common/2 (gate, PASS, self_sha256, inputs_sha256 bound)"
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(f"{gate} {'PASS' if res['PASS'] else 'FAIL'} -> {out_path}", flush=True)
    sys.exit(0 if res["PASS"] else exit_code_fail)


def require(receipt_path, inputs=None, expected_gate=None, expected_self_sha=None):
    """Return (ok, reason). ok iff the receipt exists, names the expected gate, carries a real
    self sha (equal to `expected_self_sha` when given), says PASS, the caller declared at least
    one input, and every declared input's sha equals the sha recorded in the receipt (a stale
    receipt is not a receipt)."""
    if not os.path.exists(receipt_path):
        return False, f"receipt missing: {receipt_path}"
    try:
        r = json.load(open(receipt_path))
    except Exception as e:                              # noqa: BLE001
        return False, f"receipt unreadable: {type(e).__name__}: {e}"
    if not expected_gate:
        return False, "caller did not declare the gate it expects (gate=<name>); a receipt cannot be required anonymously"
    if r.get("gate") != expected_gate:
        return False, f"receipt is from gate {r.get('gate')!r}, caller expected {expected_gate!r}"
    ss = r.get("self_sha256")
    if not isinstance(ss, str) or not _HEX64.match(ss) or set(ss) == {"0"}:
        return False, f"receipt carries no usable self_sha256 ({ss!r}): the gate's own code is unidentified"
    if expected_self_sha and ss != expected_self_sha:
        return False, f"receipt was written by gate source {ss[:12]}, caller trusts {expected_self_sha[:12]}"
    if r.get("PASS") is not True:
        return False, f"receipt says PASS={r.get('PASS')!r} (gate {r.get('gate')}, {r.get('utc')})"
    if not inputs:
        return False, "caller declared no inputs: nothing would be verified, so nothing is permitted"
    rec = r.get("inputs_sha256") or {}
    for k, p in inputs.items():
        if k not in rec:
            return False, f"receipt has no sha for input {k!r}"
        if not rec[k]:
            return False, f"receipt recorded no sha for input {k!r} (the gate did not see that file)"
        if not os.path.exists(p):
            return False, f"input {k!r} missing on disk: {p}"
        cur = sha256_file(p)
        if cur != rec[k]:
            return False, f"input {k!r} changed since the receipt: {cur[:12]} != {str(rec[k])[:12]}"
    return True, (f"PASS ({r.get('gate')}, {r.get('utc')}, self {ss[:12]}, "
                  f"{len(inputs)} inputs verified)")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "require":
        kv = dict(a.split("=", 1) for a in sys.argv[3:])
        gate = kv.pop("gate", None)
        self_sha = kv.pop("self_sha", None)
        ok, why = require(sys.argv[2], kv, expected_gate=gate, expected_self_sha=self_sha)
        print(("REQUIRE_OK " if ok else "REQUIRE_FAIL ") + why, flush=True)
        sys.exit(0 if ok else 3)
    if len(sys.argv) >= 3 and sys.argv[1] == "sha":
        for p in sys.argv[2:]:
            print(sha256_file(p), p)
        sys.exit(0)
    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    main()
