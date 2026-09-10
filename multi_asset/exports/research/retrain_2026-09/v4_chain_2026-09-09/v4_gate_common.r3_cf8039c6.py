"""Shared gate discipline for the v4 chain (review b0a573a1 P1-PIPE, 2026-09-09).

★ THE RULE: a gate is a PROGRAM CONDITION, not a printed word. Every gate (a) writes ONE structured
  verdict JSON {gate, PASS, inputs_sha256, utc, argv, self_sha256, ...}, (b) exits 0 iff PASS, else
  3; and every chain stage that depends on a gate REQUIRES its receipt through `require` — PASS
  true AND the receipt's input SHAs equal to the files the stage is about to consume. "The file
  exists" (the old STEP1_PASS marker) and "the child printed PASS" are not evidence of either.

CLI:
  python v4_gate_common.py require <receipt.json> [name=path ...]     # exit 0 iff PASS & fresh
  python v4_gate_common.py sha <path> [...]                            # print sha256 per file
"""
import hashlib
import json
import os
import sys
import time


def sha256_file(p, chunk=16 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def finalize(gate, res, out_path, inputs=None, exit_code_fail=3):
    """Write the verdict and EXIT. `inputs` = {name: path} hashed into the receipt."""
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
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(f"{gate} {'PASS' if res['PASS'] else 'FAIL'} -> {out_path}", flush=True)
    sys.exit(0 if res["PASS"] else exit_code_fail)


def require(receipt_path, inputs=None):
    """Return (ok, reason). ok iff the receipt exists, PASS is true, and every given input's sha
    equals the sha recorded in the receipt (stale receipt = not a receipt)."""
    if not os.path.exists(receipt_path):
        return False, f"receipt missing: {receipt_path}"
    try:
        r = json.load(open(receipt_path))
    except Exception as e:                              # noqa: BLE001
        return False, f"receipt unreadable: {type(e).__name__}: {e}"
    if r.get("PASS") is not True:
        return False, f"receipt says PASS={r.get('PASS')!r} (gate {r.get('gate')}, {r.get('utc')})"
    rec = r.get("inputs_sha256") or {}
    for k, p in (inputs or {}).items():
        if k not in rec:
            return False, f"receipt has no sha for input {k!r}"
        if not os.path.exists(p):
            return False, f"input {k!r} missing on disk: {p}"
        cur = sha256_file(p)
        if cur != rec[k]:
            return False, f"input {k!r} changed since the receipt: {cur[:12]} != {str(rec[k])[:12]}"
    return True, f"PASS ({r.get('gate')}, {r.get('utc')}, {len(inputs or {})} inputs verified)"


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "require":
        inputs = dict(a.split("=", 1) for a in sys.argv[3:])
        ok, why = require(sys.argv[2], inputs)
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
