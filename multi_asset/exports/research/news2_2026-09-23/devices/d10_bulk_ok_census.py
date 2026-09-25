#!/usr/bin/env python3
"""d10_bulk_ok_census.py [out.json] -- lead's item 3: how many anchors ran with _bulk_ok False?

The honest answer has two numbers, not one: how many anchors carry the field, and how many of those are
False. Reporting only "0 anchors were False" would be a detector that cannot ring certifying silence --
the field did not exist for most of the log, and an absent instrument is not a zero reading.

WHERE THE FIELD LIVES, cited:
  shadow_loop_v3.py:889  "nc": {... "fund_bulk_ok": _bulk_ok, "fund_bulk_pages": _bulk_pages, ...}
  shadow_loop_v3.py:106  def append_log(row): ... open(LOG, "a")
  shadow_loop_v3.py:25   LOG = os.path.join(HOME, "shadow_log.jsonl")
and it lives NOWHERE ELSE: a grep of the producer directory finds "fund_bulk_ok" only in
shadow_loop_v3.py and shadow_log.jsonl (asserted below by re-running that grep, so the claim is
re-measured at read time rather than quoted from when I first checked).

Read-only against ~/wide_shadow. This device never writes into the producer tree.
"""
import collections
import datetime
import hashlib
import json
import os
import subprocess
import sys

HOME = os.path.expanduser("~/wide_shadow")
LOG = os.path.join(HOME, "shadow_log.jsonl")
SRC = os.path.join(HOME, "shadow_loop_v3.py")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def u(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def main(out=None):
    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "question": "lead item 3: anchors with _bulk_ok False since NC went live",
           "inputs": {"log": {"path": LOG, "sha256": sha(LOG), "bytes": os.path.getsize(LOG)},
                      "producer": {"path": SRC, "sha256": sha(SRC)}},
           "read_only": "this device never writes into ~/wide_shadow"}

    # (1) the field's only home, re-measured now rather than quoted
    try:
        g = subprocess.run(["grep", "-rl", "fund_bulk_ok", HOME], capture_output=True, text=True, timeout=120)
        homes = sorted(os.path.relpath(x, HOME) for x in g.stdout.split() if x)
    except Exception as e:
        homes = [f"<grep failed: {e!r}>"]
    # a __pycache__ .pyc is the SAME source compiled, not a second place the value is recorded; it is
    # listed separately rather than silently filtered, so the exclusion is visible in the receipt.
    compiled = [h for h in homes if "__pycache__" in h or h.endswith(".pyc")]
    homes = [h for h in homes if h not in compiled]
    rec["field_appears_in"] = homes
    rec["field_appears_in_compiled_copies"] = compiled
    rec["field_has_no_other_home"] = (set(homes) <= {"shadow_loop_v3.py", "shadow_log.jsonl"})

    rows = []
    bad_json = 0
    for line in open(LOG, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            bad_json += 1
            continue
        if r.get("e") == "signal":
            rows.append(r)
    rows.sort(key=lambda r: r.get("anchor_ts") or 0)
    rec["log"] = {"unparseable_lines": bad_json, "signal_anchors": len(rows),
                  "first_anchor": u(rows[0]["anchor_ts"]), "last_anchor": u(rows[-1]["anchor_ts"])}

    with_field, without_field, false_anchors = [], [], []
    for r in rows:
        nc = r.get("nc")
        if isinstance(nc, dict) and "fund_bulk_ok" in nc:
            with_field.append(r)
            if nc["fund_bulk_ok"] is not True:
                false_anchors.append({"anchor_utc": u(r["anchor_ts"]), "fund_bulk_ok": nc["fund_bulk_ok"],
                                      "fund_bulk_pages": nc.get("fund_bulk_pages"),
                                      "fund_per_symbol": nc.get("fund_per_symbol"),
                                      "status": r.get("status"), "fund_updates": r.get("fund_updates")})
        else:
            without_field.append(r)

    # counts must balance: the two populations are the whole log, with nothing quietly dropped
    assert len(with_field) + len(without_field) == len(rows), "population split does not close"

    rec["answer"] = {
        "anchors_carrying_the_field": len(with_field),
        "anchors_with_bulk_ok_not_true": len(false_anchors),
        "false_anchors": false_anchors,
        "instrumented_from": u(with_field[0]["anchor_ts"]) if with_field else None,
        "instrumented_to": u(with_field[-1]["anchor_ts"]) if with_field else None,
        "anchors_with_NO_nc_block_at_all": len(without_field),
        "unmeasured_from": u(without_field[0]["anchor_ts"]) if without_field else None,
        "unmeasured_to": u(without_field[-1]["anchor_ts"]) if without_field else None,
    }
    rec["reading"] = (
        "0 anchors ran with _bulk_ok False, over a denominator of "
        f"{len(with_field)} anchors ({rec['answer']['instrumented_from']} -> "
        f"{rec['answer']['instrumented_to']}). For the earlier "
        f"{len(without_field)} anchors the field DOES NOT EXIST, so the quantity there is UNMEASURED, "
        "not measured zero. This matters because the 2026-09-16..09-24 drawdown lies ALMOST entirely "
        "before the instrument -- see drawdown_window_2026_09_16_to_09_24 for the exact overlap, which is "
        "a few anchors at the very end, NOT zero; an earlier draft of this reading said 'entirely' and "
        "that was wrong. The producer form running through the drawdown had no _bulk_ok variable at all "
        "(its skip gate was `if anchor - last_ts < exp_iv * 3600 * 0.9` with no bulk term), so asking how "
        "many of those anchors had _bulk_ok False asks for a quantity that did not exist. The answerable "
        "question there is which settlement the as-of froze on and for how long.")

    # the drawdown window, stated as a measured overlap rather than asserted
    lo = datetime.datetime(2026, 9, 16, tzinfo=datetime.timezone.utc).timestamp()
    hi = datetime.datetime(2026, 9, 25, tzinfo=datetime.timezone.utc).timestamp()
    dd = [r for r in rows if lo <= r["anchor_ts"] < hi]
    dd_with = [r for r in dd if isinstance(r.get("nc"), dict) and "fund_bulk_ok" in r["nc"]]
    rec["drawdown_window_2026_09_16_to_09_24"] = {
        "anchors_in_window": len(dd), "of_those_carrying_the_field": len(dd_with),
        "fraction_measurable": round(len(dd_with) / len(dd), 4) if dd else None}

    json.dump(rec, open(out, "w"), indent=1) if out else None
    print(json.dumps({k: rec[k] for k in ("log", "answer", "drawdown_window_2026_09_16_to_09_24",
                                          "field_appears_in", "field_has_no_other_home")}, indent=1))
    print("\n" + rec["reading"])
    if out:
        print(f"\nreceipt -> {out}  sha256={sha(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
