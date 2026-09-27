#!/usr/bin/env python3
"""Evaluate explicitly supplied recovery evidence, without production imports or API calls.

PASS covers these recovery checks only, not VERSION_PROBE/M3/PARITY or global
single-writer exclusivity. Output contains no raw source rows or arm outcomes.
Missing/not-yet-current evidence is PENDING; malformed/unreadable is UNKNOWN;
positive adverse evidence is FAIL. Precedence: FAIL > UNKNOWN > PENDING > PASS.
The watchdog-state path must be explicitly supplied; an enumerable parent plus
an absent entry is normal after resume. CLI writes one new output file (no overwrite).
"""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re

INPUTS = ("inspect", "anchors", "anchor_log", "ledger_receipt", "alarm_log",
          "watchdog_eval", "watchdog_state", "anchor_report", "venue_receipt")
EXIT = {"PASS": 0, "FAIL": 1, "UNKNOWN": 2, "PENDING": 3}


class EvidenceError(Exception):
    def __init__(self, status, reason):
        self.status, self.reason = status, reason


def require(condition, reason, status="FAIL"):
    if not condition:
        raise EvidenceError(status, reason)


def number(value):
    require(type(value) in (float, int) and math.isfinite(value),
            "missing or nonfinite numeric field", "UNKNOWN")
    return value


def epoch(value):
    require(isinstance(value, str), "missing UTC timestamp", "UNKNOWN")
    try:
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()
    except ValueError:
        raise EvidenceError("UNKNOWN", "invalid UTC timestamp")


def evaluate(inputs, anchor, observed_at, minimum_fill_ratio=0.60):
    checks, provenance, loaded = {}, {}, {}
    now = epoch(observed_at)
    require(type(anchor) is int and anchor > 0 and anchor % 14400 == 0,
            "anchor must be positive UTC 4-hour grid", "UNKNOWN")
    require(0 < number(minimum_fill_ratio) <= 1, "invalid minimum fill ratio", "UNKNOWN")

    def read(key, kind="json"):
        if key in loaded:
            return loaded[key]
        require(key in inputs, "input path not supplied", "UNKNOWN")
        path = Path(inputs[key])
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            raise EvidenceError("PENDING", "input not present")
        except OSError:
            raise EvidenceError("UNKNOWN", "input unreadable")
        provenance[key] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        try:
            text = raw.decode("utf-8")
            val = text if kind == "text" else ([json.loads(s) for s in text.splitlines() if s.strip()]
                                               if kind == "jsonl" else json.loads(text))
        except (UnicodeError, ValueError):
            raise EvidenceError("UNKNOWN", "input encoding/JSON invalid")
        loaded[key] = val
        return val

    def gate(name, fn):
        try:
            detail = fn()
            checks[name] = {"status": "PASS", "reason": "evidence agrees", **(detail or {})}
        except EvidenceError as e:
            checks[name] = {"status": e.status, "reason": e.reason}
        except (KeyError, TypeError, ValueError, AttributeError, IndexError, OSError):
            checks[name] = {"status": "UNKNOWN", "reason": "required field missing, invalid, or unreadable"}

    def fresh(t, floor=anchor):
        require(t <= now, "timestamp is in the future")
        require(t >= floor, "evidence predates this anchor", "PENDING")

    row = {}
    done = {}

    def inspect_check():
        text = read("inspect", "text")
        identities = re.findall(r"^### anchor (\d+) =", text, re.M)
        require(identities == [str(anchor)], "inspect anchor identity wrong or ambiguous")
        require("[BLIND:" in text and "[UNBLINDED:" not in text, "inspect is not explicitly blind")
        require(bool(re.search(r"^DONE(?:\s|$)", text, re.M)), "inspect incomplete", "PENDING")
        require("Traceback (most recent call last)" not in text, "inspect contains execution error", "UNKNOWN")

    def anchor_check():
        rows = read("anchors", "jsonl")
        candidates = []
        for r in rows:
            ats = number(r.get("anchor_ts"))
            nominal = (r.get("external_book") or {}).get("nominal_ts")
            if anchor <= ats < anchor + 14400 or nominal == anchor:
                candidates.append(r)
        require(bool(candidates), "anchor row not yet present", "PENDING")
        require(len(candidates) == 1, "duplicate or ambiguous anchor rows")
        r = candidates[0]
        ats = number(r.get("anchor_ts")); eb = r.get("external_book") or {}
        require(anchor <= ats < anchor + 14400 and eb.get("nominal_ts") == anchor,
                "nominal anchor and wall time disagree")
        require(r.get("rebalance_id") == "A" + str(int(ats)), "RID and wall time disagree")
        fresh(ats)
        require(type(r.get("opening_halted")) is bool, "opening_halted missing", "UNKNOWN")
        require(r["opening_halted"] is False, "opening is halted")
        require(eb.get("ok") is True and eb.get("sha_ok") is True and eb.get("reason") is None,
                "external book is not accepted with valid pins")
        target, realized = number(r.get("target_gross")), number(r.get("realized_gross"))
        require(target > 0 and realized >= 0, "invalid gross values")
        row.update(rid=r["rebalance_id"], ats=ats, ratio=realized / target)
        require(row["ratio"] >= minimum_fill_ratio, "fill ratio below required threshold")
        return {"rebalance_id": row["rid"], "fill_ratio": row["ratio"], "minimum": minimum_fill_ratio}

    def done_check():
        text = read("anchor_log", "text")
        events = []
        for line in text.splitlines():
            m = re.match(r"^(\S+) anchor (start|done)(?: mode=(\S+)| rc=(-?\d+))", line)
            if m:
                t = epoch(m[1])
                if anchor <= t < anchor + 14400:
                    fresh(t)
                    events.append((t, m[2], m[3], m[4]))
        starts = [e for e in events if e[1] == "start"]
        require(bool(starts), "anchor start not yet present", "PENDING")
        require(len(starts) == 1 and starts[0][2] == "LIVE", "start is repeated or not LIVE")
        ends = [e for e in events if e[1] == "done" and e[0] >= starts[0][0]]
        require(bool(ends), "anchor done not yet present", "PENDING")
        require(len(ends) == 1 and ends[0][3] == "0", "anchor completion failed or ambiguous")
        done["ts"] = ends[0][0]

    def ledger_check():
        r = read("ledger_receipt")
        require(r.get("A") == anchor, "ledger receipt anchor mismatch")
        require(bool(row), "valid anchor identity unavailable", "UNKNOWN")
        require(r.get("rebalance_id") == row["rid"], "ledger receipt RID mismatch")
        fresh(epoch(r.get("utc")), done.get("ts", row["ats"]))
        require(type(r.get("K4_blocked_by_halt_rows")) is int, "blocked count missing", "UNKNOWN")
        require(r["K4_blocked_by_halt_rows"] == 0, "blocked_by_halt rows present")
        require(r.get("K5_watchdog_state_json_exists") is False, "ledger receipt reports watchdog state or omits it")
        ratio = number(r.get("K2_fill_ratio"))
        require(abs(ratio - row["ratio"]) <= 0.00011, "ledger fill ratio disagrees with anchor")
        require(ratio >= minimum_fill_ratio, "ledger fill ratio below required threshold")

    def state_check():
        path = Path(inputs["watchdog_state"])
        try:
            names = [p.name for p in path.parent.iterdir()]
        except OSError:
            raise EvidenceError("UNKNOWN", "watchdog-state parent cannot be enumerated")
        require(path.name not in names, "watchdog state entry exists")
        provenance["watchdog_state"] = {"path": str(path), "parent_enumerated": True, "absent": True}

    def watchdog_check():
        r = read("watchdog_eval")
        fresh(epoch(r.get("evaluated_utc")), row.get("ats", anchor))
        require(type(r.get("tripped")) is bool, "tripped field must be boolean", "UNKNOWN")
        require(not r["tripped"], "watchdog tripped")
        for key in ("triggers", "conditions_blind", "conditions_unevaluated"):
            require(isinstance(r.get(key), list), key + " missing", "UNKNOWN")
            require(not r[key], key + " is nonempty", "FAIL" if key == "triggers" else "UNKNOWN")

    def alarm_check():
        rows = read("alarm_log", "jsonl")
        new_high = 0
        for r in rows:
            ts = epoch(r.get("ts"))
            require(ts <= now, "alarm timestamp in the future")
            require(isinstance(r.get("severity"), str), "alarm severity missing", "UNKNOWN")
            if ts >= anchor and r["severity"].upper() in ("HIGH", "CRITICAL"):
                new_high += 1
        require(new_high == 0, "new HIGH/CRITICAL alarm since nominal anchor")
        return {"new_high_count": new_high}

    def report_check():
        r = read("anchor_report")
        ra = number(r.get("anchor_ts"))
        require(ra >= anchor, "anchor report not yet for this anchor", "PENDING")
        require(ra == anchor, "anchor report identity mismatch")
        fresh(epoch(r.get("utc")), max(anchor + 3300, done.get("ts", anchor)))
        require(r.get("status") == "green", "anchor report is not green")

    def venue_check():
        r = read("venue_receipt")
        require(r.get("anchor") == anchor, "venue receipt anchor mismatch")
        require(bool(row), "valid anchor identity unavailable", "UNKNOWN")
        require(r.get("rebalance_id") == row["rid"], "venue receipt RID mismatch")
        require(r.get("device") == "venue_readonly_symbol_bound.py" and r.get("identity_key") == "symbol_orderId_v1",
                "venue receipt lacks the required symbol-bound identity contract", "UNKNOWN")
        receipt_ts = epoch(r.get("utc")); fresh(receipt_ts, anchor + 3600)
        require(r.get("VERDICT") in ("PASS", "FAIL", "UNKNOWN"), "venue verdict missing", "UNKNOWN")
        require(r["VERDICT"] != "UNKNOWN", "venue observation UNKNOWN", "UNKNOWN")
        require(r["VERDICT"] == "PASS" and r.get("bad") == [], "venue device reports failure")
        start, end = [number(v) for v in r["window_ms"]]
        require(start == (int(row["rid"][1:]) - 600) * 1000, "venue window starts at unexpected time")
        require(start < end <= receipt_ts * 1000, "venue window end invalid or after receipt")
        require(end >= max(anchor + 3600, done.get("ts", row["ats"])) * 1000,
                "venue query did not cover completed anchor and quiet window", "PENDING")
        for k in ("n_commission_rows", "n_symbols", "n_venue_trades", "n_foreign_order_ids", "blocked_by_halt_rows"):
            require(type(r.get(k)) is int and r[k] >= 0, "venue count missing/invalid: " + k, "UNKNOWN")
        require(r["n_foreign_order_ids"] == 0, "foreign order IDs present")
        require(r["blocked_by_halt_rows"] == 0, "venue receipt has blocked_by_halt rows")
        require(all(r[k] > 0 for k in ("n_commission_rows", "n_symbols", "n_venue_trades")),
                "empty venue coverage cannot verify a rebuilt book", "UNKNOWN")
        ratio = number(r.get("fill_ratio_realized_over_target"))
        require(abs(ratio - row["ratio"]) <= 0.00011 and ratio >= minimum_fill_ratio,
                "venue receipt fill ratio disagrees or below threshold")
        return {"window_ms": [start, end], "foreign_order_ids": 0}

    for name, fn in (("inspect", inspect_check), ("anchor", anchor_check), ("anchor_done", done_check),
                     ("ledger_receipt", ledger_check), ("watchdog_state", state_check),
                     ("watchdog_eval", watchdog_check), ("alarms", alarm_check),
                     ("anchor_report", report_check), ("venue_receipt", venue_check)):
        gate(name, fn)
    statuses = {v["status"] for v in checks.values()}
    verdict = next(s for s in ("FAIL", "UNKNOWN", "PENDING", "PASS") if s in statuses)
    return {"schema": "recovery_acceptance_v1", "anchor": anchor, "observed_at": observed_at,
            "minimum_fill_ratio": minimum_fill_ratio, "verdict": verdict, "checks": checks,
            "inputs": provenance, "coverage": {"scope": "recovery evidence only; VERSION_PROBE/M3/PARITY remain separate",
                "global_single_writer_proven": False,
                "venue_limits": ["only rid-minus-600s to receipt window end", "only commission-listed symbols and filled orders",
                    "symbol/orderId identity; symbol/clientOrderId fallback for no-orderId local rows",
                    "no coverage of gaps between monitored windows or future activity"]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchor", type=int, required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--minimum-fill-ratio", type=float, default=0.60)
    for name in INPUTS:
        parser.add_argument("--" + name.replace("_", "-"), required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    inputs = {k: getattr(args, k) for k in INPUTS}
    out = Path(args.out)
    require(out.resolve() not in [Path(p).resolve() for p in inputs.values()], "output must not alias an input", "UNKNOWN")
    try:
        result = evaluate(inputs, args.anchor, args.observed_at, args.minimum_fill_ratio)
    except EvidenceError as e:
        result = {"verdict": e.status, "checks": {"arguments": {"status": e.status, "reason": e.reason}}}
    result["self_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with out.open("x") as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write("\n")
    for name, check in result["checks"].items():
        print(name, check["status"], check["reason"])
    print("RECOVERY_ACCEPTANCE", result["verdict"])
    return EXIT[result["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
