"""ROLL_PATHS gate (FX-TRAIN TRN-01, 2026-09-16; AUDIT_TRAIN 7e1ecf9a TRN-01; FACT_TABLE_TRN §TRN-01).

WHY: every git builder for the month-roll inputs writes a SEPTEMBER path by default (make_raw_patch.py, v4_hole_cells.py,
pod_merge_cache_ext.py, pod_panel_splice.py, fund_pull_pod.py, and pod_panel_ext.py's PANEL_OUT default). Run as-is for a new
month they overwrite files that September's gate and export receipts hash — the E-0912-B class — and nothing in the chain would
notice, because preflight only checks that each contract path EXISTS. A path that exists because last month put it there passes.

WHAT THIS DECIDES, and only this: that this month's contract cannot be pointed at any previous month's artifacts.
  P1 rolled_keys_differ    for every ROLLED key, this month's value differs from the previous month's value for the SAME key
  P2 no_cross_key_reuse    no ROLLED value of this month equals ANY value of the previous contract under any key — the dangerous
                           improvisation is not only "same key, same path" but "this month's CACHE is last month's PANEL"
  P3 rolled_under_root     every ROLLED value lies under this month's $R, so the month's products are inside the month's root
                           (exceptions must be declared in ROLL_ALLOW_OUTSIDE_ROOT, and each one is named in the receipt)
  P4 previous_untouched    every previous-month value that still exists on disk has the sha it had when the previous contract's
                           own receipt was written, when ROLL_PREV_SHA_JSON supplies that record; without it the check is
                           reported NOT_EVALUABLE with its reason, never silently skipped
  P5 no_parent_escape      no value contains a '..' component (the lexical-containment escape of FXR-TRN-1, same family)
The ROLLED set is the eight keys the October template leaves as TODO_ plus RAW_PATCH, which the template gives a real path with
no TODO_ marker and which is therefore the easiest one to leave pointing at September.

This gate does NOT decide whether the roll produced correct data; that is the parity gate and the coverage gate. It decides
whether the month is allowed to write where it is about to write.

Receipt through v4_gate_common.finalize (gate ROLL_PATHS; inputs month_env / prev_month_env): rc 0 iff PASS, else 3.
env (all REQUIRED, no defaults): V4_MONTH_ENV, ROLL_PREV_MONTH_ENV, ROLL_OUT.
optional: ROLL_ALLOW_OUTSIDE_ROOT (comma list of ROLLED keys allowed outside $R, each named in the receipt),
          ROLL_PREV_SHA_JSON (a {path: sha256} record of the previous month's artifacts, for P4).
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4_gate_common import finalize, sha256_file

# The keys a month roll PRODUCES. RAW_PATCH is here although the October template gives it a real path: that is exactly why it
# is the easiest one to leave pointing at September (AUDIT_TRAIN TRN-02 evidence line).
ROLLED = ("CACHE", "PANEL_SPLICE", "PANEL_KING", "RAW_PATCH", "HOLE_CELLS", "FUND_AUG", "EMA_STATE_JSON", "EXPORT_PANEL")
_KEYRE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")

_OUT = os.environ.get("ROLL_OUT")
if not _OUT:
    print("ROLL_PATHS_REFUSED missing ROLL_OUT (no receipt path: nothing written)", flush=True)
    sys.exit(3)
_KEYS = ("V4_MONTH_ENV", "ROLL_PREV_MONTH_ENV")
E = {k: os.environ.get(k, "") for k in _KEYS}
INPUTS = {"month_env": E["V4_MONTH_ENV"] or None, "prev_month_env": E["ROLL_PREV_MONTH_ENV"] or None}
_ref = {}
if [k for k in _KEYS if not E[k]]:
    _ref["missing_env"] = [k for k in _KEYS if not E[k]]
_miss = {k: v for k, v in INPUTS.items() if not v or not os.path.isfile(v)}
if _miss:
    _ref["missing_files"] = _miss
if _ref:
    print("ROLL_PATHS_REFUSED", json.dumps(_ref), flush=True)
    finalize("ROLL_PATHS", {"PASS": False, "REFUSED": _ref}, _OUT, INPUTS)

ALLOW = [k for k in os.environ.get("ROLL_ALLOW_OUTSIDE_ROOT", "").split(",") if k]
PREV_SHA = os.environ.get("ROLL_PREV_SHA_JSON", "")
t0 = time.time()


def read_env(path):
    """{KEY: raw value} from a month contract, read as DATA — never sourced, never executed (chain_lib's D3 rule). Values are
    returned with $R / ${R} expanded from the file's own R, because that is how the driver will see them."""
    kv = {}
    for line in open(path, encoding="utf-8").read().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _KEYRE.match(s)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if "R" in kv:
            v = v.replace("${R}", kv["R"]).replace("$R", kv["R"])
        kv[k] = v
    return kv


cur, prev = read_env(E["V4_MONTH_ENV"]), read_env(E["ROLL_PREV_MONTH_ENV"])
checks, fails = {}, []


def chk(name, ok, detail):
    checks[name] = dict(detail, ok=bool(ok))
    if not ok:
        fails.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + " " + json.dumps(detail, default=str)[:400], flush=True)


missing_keys = [k for k in ROLLED if k not in cur]
prev_missing = [k for k in ROLLED if k not in prev]
if missing_keys or prev_missing:
    chk("P0_rolled_keys_present", False,
        {"absent_in_month_contract": missing_keys, "absent_in_previous_contract": prev_missing,
         "why": "a rolled key that is not in the contract cannot be checked, and an unchecked key is the one that gets reused"})
else:
    chk("P0_rolled_keys_present", True, {"n_rolled": len(ROLLED)})

# P1 — same key, same path
p1 = [{"key": k, "value": cur[k], "previous_month_value": prev[k]}
      for k in ROLLED if k in cur and k in prev and cur[k] == prev[k]]
chk("P1_rolled_keys_differ", not p1,
    {"violations": p1, "why": "a rolled key still pointing at the previous month's artifact means this month either reads stale "
                              "data or overwrites a file the previous month's receipts hash (E-0912-B)"})

# P2 — this month's rolled value is some OTHER key of the previous contract
prev_by_value = {}
for k, v in prev.items():
    prev_by_value.setdefault(v, []).append(k)
p2 = [{"key": k, "value": cur[k], "is_previous_month": sorted(prev_by_value[cur[k]])}
      for k in ROLLED if k in cur and cur[k] in prev_by_value and cur[k] != cur.get("R", object())]
p2 = [v for v in p2 if v["is_previous_month"] != [v["key"]]]        # the same-key case is P1's to report, not P2's
chk("P2_no_cross_key_reuse", not p2,
    {"violations": p2, "why": "the improvisation is not only 'same key, same path': a month whose CACHE is the previous month's "
                              "PANEL, or whose FUND_AUG is the previous month's EMA_STATE_JSON, is the same failure"})

# P3 — rolled products live under this month's root
root = cur.get("R", "")
p3 = []
for k in ROLLED:
    if k not in cur or k in ALLOW:
        continue
    if not root or not (cur[k] == root or cur[k].startswith(root.rstrip("/") + "/")):
        p3.append({"key": k, "value": cur[k], "R": root or None})
chk("P3_rolled_under_root", not p3 and bool(root),
    {"violations": p3, "R": root or None, "declared_exceptions": ALLOW,
     "why": "the month's products belong inside the month's root; an exception has to be declared by key, and is named here"})

# P4 — the previous month's artifacts are still what its receipts say they are
if not PREV_SHA:
    chk("P4_previous_untouched", True,
        {"NOT_EVALUABLE": "ROLL_PREV_SHA_JSON not supplied: this gate can compare paths, but proving the PREVIOUS month's files "
                          "are unchanged needs the record of what they hashed to. Supply it to turn this into a real check.",
         "evaluated": False})
elif not os.path.isfile(PREV_SHA):
    chk("P4_previous_untouched", False, {"why": f"ROLL_PREV_SHA_JSON={PREV_SHA} does not exist", "evaluated": False})
else:
    try:
        rec = json.load(open(PREV_SHA))
        rec = rec if isinstance(rec, dict) else {}
        moved, checked, absent = [], 0, []
        for p, want in sorted(rec.items()):
            if not isinstance(want, str):
                continue
            if not os.path.isfile(p):
                absent.append(p)
                continue
            got = sha256_file(p)
            checked += 1
            if got != want:
                moved.append({"path": p, "recorded": want[:16], "now": got[:16]})
        chk("P4_previous_untouched", not moved,
            {"n_checked": checked, "n_absent_now": len(absent), "absent": absent[:20], "moved": moved, "evaluated": True,
             "why": "a previous-month artifact whose sha moved means something already overwrote it"})
    except Exception as e:                                        # noqa: BLE001
        chk("P4_previous_untouched", False, {"why": f"ROLL_PREV_SHA_JSON unreadable: {type(e).__name__}: {e}", "evaluated": False})

# P5 — no '..' component anywhere in the month contract (FXR-TRN-1 family)
p5 = [{"key": k, "value": v} for k, v in sorted(cur.items()) if "/../" in f"/{v}/"]
chk("P5_no_parent_escape", not p5,
    {"violations": p5, "why": "a '..' component makes every containment test above lexical-only (FXR-TRN-1)"})

res = {"PASS": not fails, "failed_checks": fails, "checks": checks,
       "month_env": E["V4_MONTH_ENV"], "prev_month_env": E["ROLL_PREV_MONTH_ENV"],
       "v4_month": cur.get("V4_MONTH"), "previous_v4_month": prev.get("V4_MONTH"), "R": root or None,
       "rolled_keys": list(ROLLED), "rolled_values": {k: cur.get(k) for k in ROLLED},
       "declared_exceptions_outside_root": ALLOW, "prev_sha_record": PREV_SHA or None,
       "wall_s": round(time.time() - t0, 1), "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
print("ROLL_PATHS", "PASS" if res["PASS"] else "FAIL",
      json.dumps({"month": res["v4_month"], "previous": res["previous_v4_month"], "failed": fails}), flush=True)
finalize("ROLL_PATHS", res, _OUT, INPUTS)
