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

★ ROUND 4 (researcher round-3 extra cases require_valid_wrong_source_unpinned / chain_valid_wrong_gate_source, 2026-09-10):
  `self_sha=` is MANDATORY. A receipt whose self_sha256 is a real sha of the WRONG program (the judge's, say) passed round 3
  whenever the caller did not pin — and no chain pinned. Now every caller must say which gate source it trusts (the chains
  compute it at run time from the gate script they invoke: chain_lib.sh gate_sha), and `require` refuses an unpinned call.

★ ROUND 5 (independent review cfaf1bbe §2-4, 2026-09-10): the STANDARD is a frozen file, not the caller's word.
  ELIGIBILITY_CONTRACT.json beside this module lists, per governed gate, the APPROVED gate source sha256s, and per candidate arm the
  gate it must pass. `require` refuses a pinned source that is not approved for a gate listed there — the reviewer showed that a
  locally edited gate, re-run, writes a receipt whose self sha equals its own runtime sha (the round-4 pin passed it): "receipt matches
  the program on disk" is not "the program is the reviewed one". The judge derives every arm's standard from the contract and treats
  JUDGE_ELIGIBILITY as a receipt LOCATOR only; the contract is read from the judge's own directory and no environment variable can
  replace it. BUNDLE_export additionally requires the four judged book files of the arm (book_binding) in the receipt.

★ ROUND 4 (researcher require_correct_identity_dependency_subset): the FULL-DEPENDENCY CONTRACT is code. REQUIRED_INPUTS below registers,
  per gate (and per stage profile where stages legitimately consume different parts of a receipt), the input names a caller MUST declare;
  `require` refuses a caller that omits a registered name (extras are allowed). Round 3 verified whatever subset the caller chose to name —
  a chain that forgot hole_cells was silently unbound from the holes.

CLI:
  python v4_gate_common.py require <receipt.json> gate=<expected_gate> self_sha=<sha256> [profile=<stage>] name=path [name=path ...]
                                                                       # exit 0 iff PASS & identity & fresh & full registered dependency set
  python v4_gate_common.py sha <path> [...]                            # print sha256 per file
"""
import hashlib
import json
import os
import re
import sys
import time

_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# ★ ROUND 4: the input names a caller MUST declare when it requires a receipt of this gate (extras allowed). Key = gate, or gate@profile for a
#   stage that consumes a registered subset; a caller naming an unregistered profile is refused. Populated from what the chains ACTUALLY consume.
REQUIRED_INPUTS = {
    "G2_closure": ["fea_A", "fea_B", "targets_A", "targets_B", "hole_cells"],            # chain_v4s_gpu.sh: both feature builds, both target sets, the hole cells
    "STEP1": ["dlw_v4raw_targets", "fea82_v4raw"],                                        # floor: RAW targets + fea82 every F10 chain reads
    "STEP1@v4s": ["dlw_v4raw_targets", "fea82_v4raw"],                                    # chain_v4s_gpu.sh (RAW only; its fea89 is bound through G2_closure fea_A)
    "STEP1@v4": ["dlw_v4raw_targets", "dlw_hf3_targets", "fea82_v4raw", "fea89_f8v4"],    # chain_v4_gpu3.sh / chain_v4_post_export.sh (RAW + CLIP chains, fea89)
    "STEP2": ["wide_fea_v4", "wide_fea_v4_meta"],                                          # chain_v4_gpu3.sh king side
    "BUNDLE_export": ["wide_fea_v4", "wide_fea_v4_meta", "bundle_base", "export_panel", "bundle_cache", "fund_aug", "live_pins",
                      "book_dyn_s42", "book_dyn_s2027", "book_fix_s42", "book_fix_s2027"],   # pod_export_bundle_v4.py inputs + the arm's four judged books (round 5)
    #   BUNDLE_FEA / BUNDLE_META / BUNDLE_BASE / EXPORT_PANEL / BUNDLE_CACHE / fund_aug.json.gz / live_pins.json — the judge's per-arm eligibility (JUDGE_ELIGIBILITY)
}


def required_inputs(gate, profile=None):
    """(names, key, registered): the registered floor for gate[@profile]. Unknown profile -> registered False with the bad key."""
    key = f"{gate}@{profile}" if profile else gate
    if key in REQUIRED_INPUTS:
        return list(REQUIRED_INPUTS[key]), key, True
    if profile:
        return [], key, False
    return [], key, None          # bare gate with no registry entry: no floor (the caller's non-empty declaration still binds)


CONTRACT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ELIGIBILITY_CONTRACT.json")
BOOK_INPUTS = ("book_dyn_s42", "book_dyn_s2027", "book_fix_s42", "book_fix_s2027")


def load_contract(path=None):
    """(contract dict or None, error). Round 5: the frozen research definition beside this module — never an env-supplied path."""
    p = path or CONTRACT_PATH
    if not os.path.exists(p):
        return None, f"frozen contract missing: {p}"
    try:
        c = json.load(open(p))
    except Exception as e:                              # noqa: BLE001
        return None, f"frozen contract unreadable ({p}): {type(e).__name__}: {e}"
    if not isinstance(c, dict) or not isinstance(c.get("gates"), dict) or not isinstance(c.get("arms"), dict) \
            or str(c.get("contract_schema", "")).split("/")[0] != "v4_eligibility_contract":
        return None, f"frozen contract malformed ({p}): expected contract_schema v4_eligibility_contract/N with 'gates' and 'arms'"
    return c, None


def approved_sources(gate, contract=None):
    """(approved list or None if the gate is not governed by the contract, error)."""
    c, err = (contract, None) if contract is not None else load_contract()
    if c is None:
        return None, err
    g = c["gates"].get(gate)
    if not isinstance(g, dict):
        return None, None
    lst = g.get("approved_source_sha256") or []
    return [str(x) for x in lst if isinstance(x, str) and _HEX64.match(x)], None


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


def require(receipt_path, inputs=None, expected_gate=None, expected_self_sha=None, profile=None):
    """Return (ok, reason). ok iff the receipt exists, names the expected gate, the caller PINNED the
    gate source it trusts (`expected_self_sha`, mandatory since round 4) and the receipt's real self sha
    equals it, says PASS, the caller declared at least one input AND every input registered for
    gate[@profile] in REQUIRED_INPUTS (round 4), and every declared input's sha equals the sha recorded
    in the receipt (a stale receipt is not a receipt)."""
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
    if not expected_self_sha:
        return False, "caller did not pin the gate source (self_sha=<sha256 of the gate script it trusts>); a receipt from an unidentified program is not permission"
    if not isinstance(expected_self_sha, str) or not _HEX64.match(expected_self_sha) or set(expected_self_sha) == {"0"}:
        return False, f"self_sha={expected_self_sha!r} is not a sha256 (64 hex, not all-zero)"
    ss = r.get("self_sha256")
    if not isinstance(ss, str) or not _HEX64.match(ss) or set(ss) == {"0"}:
        return False, f"receipt carries no usable self_sha256 ({ss!r}): the gate's own code is unidentified"
    if ss != expected_self_sha:
        return False, f"receipt was written by gate source {ss[:12]}, caller trusts {expected_self_sha[:12]}"
    # ★ round 5: the pinned source must be an APPROVED source of the gate in the frozen contract (a governed gate with no contract, or
    #   a contract that does not list it, is refused; an ungoverned gate — neither registered nor listed — carries no approval)
    governed = expected_gate in REQUIRED_INPUTS or any(k.startswith(expected_gate + "@") for k in REQUIRED_INPUTS)
    contract, cerr = load_contract()
    if contract is None and governed:
        return False, f"gate {expected_gate!r} is governed but the {cerr}: nothing can be required without the frozen research definition"
    if contract is not None:
        approved, _ = approved_sources(expected_gate, contract)
        if approved is None and governed:
            return False, f"gate {expected_gate!r} is registered in REQUIRED_INPUTS but absent from the frozen contract's gates: refused"
        if approved is not None and expected_self_sha not in approved:
            return False, (f"gate source {expected_self_sha[:12]} is not an APPROVED source of gate {expected_gate!r} in the frozen contract "
                           f"(approved: {[a[:12] for a in approved] or 'none — the physical gate is not built'}); a program that re-ran and "
                           f"signed its own receipt is not the reviewed program")
    if r.get("PASS") is not True:
        return False, f"receipt says PASS={r.get('PASS')!r} (gate {r.get('gate')}, {r.get('utc')})"
    if not inputs:
        return False, "caller declared no inputs: nothing would be verified, so nothing is permitted"
    need, key, registered = required_inputs(expected_gate, profile)
    if registered is False:
        return False, f"profile {profile!r} is not registered for gate {expected_gate!r} (known: {sorted(k for k in REQUIRED_INPUTS if k.startswith(expected_gate + '@'))})"
    missing = [k for k in need if k not in inputs]
    if missing:
        return False, f"caller omitted registered input(s) {missing} for {key}: the stage would run unbound from them (REQUIRED_INPUTS[{key!r}] = {need})"
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
    return True, (f"PASS ({r.get('gate')}, {r.get('utc')}, self {ss[:12]} approved, "
                  f"{len(inputs)} inputs verified, registered floor {key}={len(need) if registered else 'none'})")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "require":
        kv = dict(a.split("=", 1) for a in sys.argv[3:])
        gate = kv.pop("gate", None)
        self_sha = kv.pop("self_sha", None)
        profile = kv.pop("profile", None)
        ok, why = require(sys.argv[2], kv, expected_gate=gate, expected_self_sha=self_sha, profile=profile)
        print(("REQUIRE_OK " if ok else "REQUIRE_FAIL ") + why, flush=True)
        sys.exit(0 if ok else 3)
    if len(sys.argv) >= 3 and sys.argv[1] == "approved":       # approved <gate> <sha256> -> rc 0 iff approved in the frozen contract
        lst, err = approved_sources(sys.argv[2])
        ok = bool(lst) and len(sys.argv) > 3 and sys.argv[3] in lst
        print(("APPROVED " if ok else "NOT_APPROVED ") + (err or f"{sys.argv[2]}: {lst}"), flush=True)
        sys.exit(0 if ok else 3)
    if len(sys.argv) >= 3 and sys.argv[1] == "sha":
        for p in sys.argv[2:]:
            print(sha256_file(p), p)
        sys.exit(0)
    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    main()
