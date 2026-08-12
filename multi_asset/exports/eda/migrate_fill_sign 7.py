"""0C — migrate `orders.filled_notional` from the UNSIGNED to the SIGNED convention, in place.

> created 2026-07-27 | Session: 0C | 状态: one-shot migration + its own proof | 作废条件: 迁移完成并复核后

WHY THIS AND NOT A REGENERATION
-------------------------------
The approved plan was to regenerate the shadow log from `(code, panel, seed)`, on the strength of a
determinism measurement I made: two runs, 17/17 files byte-identical. **That measurement certified
the wrong property.** It shows the generator is deterministic *holding today's panel fixed*; it does
NOT show the historical tree is reproducible, because the panel is an input and it has moved. A full
regeneration measured against the live tree differs in eleven more fields:

    anchors.panel_hash        41c0cf7afed8b1f8 -> bd1b55b2edfd6f9f     <- the input itself changed
    anchors.mid_at_anchor_vector / realized_gross / target_vector_hash / n_names_skipped
    position_readback.symbol (330 rows) / venue_position_notional (652 rows)
    funding.funding_paid / position_notional_at_settlement
    daily_nav.nav / realised_pnl
    ... plus row-count changes (20260723: 217 -> 1291 orders — the live tree has partial days)

So regeneration would replace the log with a DIFFERENT EVALUATION of the same function, not a
re-signed copy of the same one — and it would silently violate the obligation that only the sign
column may change.

A convention change is a **relabelling of one column**. This does exactly that and nothing else:
each line is edited textually, so every other byte on every other line is unchanged by construction
rather than by hope. Everything except `orders.jsonl` is copied verbatim.

WHAT IT DOES
------------
For every row in `orders.jsonl`:  side == "sell" and filled_notional is a non-zero number
                                  -> replace that ONE numeric token with its negation.
`None` and `0.0` are left alone — same three branches as the write-time assertion: unknown is not a
violation and a measured zero has no direction.

Usage:
    python migrate_fill_sign.py --src <tree> --dst <tree>        # migrate
    python migrate_fill_sign.py --verify <old_tree> <new_tree>   # prove only the sign column moved
    python migrate_fill_sign.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys

KEY = "filled_notional"
# The token as `json.dumps` writes it: `"filled_notional": -123.45` / `: null` / `: 0.0`
TOKEN = re.compile(r'("' + KEY + r'":\s*)(-?\d+\.?\d*(?:[eE][-+]?\d+)?|null)')


def flip_line(line):
    """Return (new_line, changed). Only the filled_notional numeric token may move."""
    row = json.loads(line)
    if str(row.get("side", "")).lower() != "sell":
        return line, False
    f = row.get(KEY)
    if f is None or float(f) == 0.0:
        return line, False
    if float(f) < 0:
        return line, False                       # already signed; idempotent
    m = TOKEN.search(line)
    if not m:
        raise ValueError(f"row has {KEY}={f!r} but no matching token in the raw line")
    new = line[:m.start(2)] + "-" + m.group(2) + line[m.end(2):]
    # verify the edit did exactly what it claims, on this very line, before returning it
    a, b = json.loads(line), json.loads(new)
    assert b[KEY] == -a[KEY], f"token edit did not negate the value: {a[KEY]} -> {b[KEY]}"
    a.pop(KEY); b.pop(KEY)
    assert a == b, "token edit disturbed another field"
    return new, True


def migrate(src, dst):
    if os.path.exists(dst):
        raise SystemExit(f"refusing to overwrite an existing tree: {dst}")
    shutil.copytree(src, dst)
    n_files = n_rows = n_flipped = 0
    for day in sorted(os.listdir(dst)):
        p = os.path.join(dst, day, "orders.jsonl")
        if not os.path.exists(p):
            continue
        n_files += 1
        out = []
        for line in open(p):
            if not line.strip():
                out.append(line); continue
            new, changed = flip_line(line.rstrip("\n"))
            n_rows += 1
            n_flipped += int(changed)
            out.append(new + "\n")
        open(p, "w").writelines(out)
    print(f"migrated {n_files} orders.jsonl file(s): {n_rows} rows, {n_flipped} sign flips -> {dst}")
    return n_flipped


def verify(old, new):
    """Prove the ONLY difference is the sign of orders.filled_notional. Exit 1 otherwise."""
    problems = []
    days_o, days_n = sorted(os.listdir(old)), sorted(os.listdir(new))
    if days_o != days_n:
        problems.append(f"day sets differ: {set(days_o) ^ set(days_n)}")
    n_flip = n_same = 0
    for day in days_o:
        do, dn = os.path.join(old, day), os.path.join(new, day)
        fo = sorted(os.listdir(do)) if os.path.isdir(do) else []
        fn = sorted(os.listdir(dn)) if os.path.isdir(dn) else []
        if fo != fn:
            problems.append(f"{day}: file sets differ {set(fo) ^ set(fn)}")
            continue
        for fname in fo:
            po, pn = os.path.join(do, fname), os.path.join(dn, fname)
            bo, bn = open(po, "rb").read(), open(pn, "rb").read()
            if fname != "orders.jsonl":
                # every other stream must be BYTE-identical — no parsing, no tolerance
                if bo != bn:
                    problems.append(f"{day}/{fname}: bytes differ and must not")
                continue
            lo, ln = bo.decode().splitlines(), bn.decode().splitlines()
            if len(lo) != len(ln):
                problems.append(f"{day}/{fname}: {len(lo)} vs {len(ln)} rows")
                continue
            for i, (a, b) in enumerate(zip(lo, ln)):
                if a == b:
                    n_same += 1
                    continue
                ra, rb = json.loads(a), json.loads(b)
                if ra.get(KEY) is None or rb.get(KEY) is None or rb[KEY] != -ra[KEY]:
                    problems.append(f"{day}/{fname}:{i}: {KEY} {ra.get(KEY)} -> {rb.get(KEY)} "
                                    f"is not a negation")
                    continue
                ra.pop(KEY); rb.pop(KEY)
                if ra != rb:
                    diff = [k for k in set(ra) | set(rb) if ra.get(k) != rb.get(k)]
                    problems.append(f"{day}/{fname}:{i}: other fields changed: {diff}")
                    continue
                n_flip += 1
    print(f"rows byte-identical: {n_same}   rows differing ONLY by the negation of {KEY}: {n_flip}")
    print(f"non-orders streams compared BYTE-for-BYTE: "
          f"{'all identical' if not any('bytes differ' in p for p in problems) else 'MISMATCH'}")
    if problems:
        print(f"\n★ {len(problems)} PROBLEM(S):")
        for p in problems[:20]:
            print("   " + p)
        return 1
    print("\nVERDICT: only the sign of orders.filled_notional changed; everything else is "
          "byte-identical")
    return 0


def selftest():
    import tempfile
    d = tempfile.mkdtemp(prefix="mig_")
    src, dst = os.path.join(d, "src"), os.path.join(d, "dst")
    os.makedirs(os.path.join(src, "20260101"))
    rows = [
        {"anchor_ts": 1, "symbol": "A", "side": "sell", "filled_notional": 100.5, "fee_paid": 1.0},
        {"anchor_ts": 1, "symbol": "B", "side": "buy", "filled_notional": 200.0, "fee_paid": 2.0},
        {"anchor_ts": 1, "symbol": "C", "side": "sell", "filled_notional": None, "fee_paid": 0.0},
        {"anchor_ts": 1, "symbol": "D", "side": "sell", "filled_notional": 0.0, "fee_paid": 0.0},
        {"anchor_ts": 1, "symbol": "E", "side": "sell", "filled_notional": -7.5, "fee_paid": 0.5},
        {"anchor_ts": 1, "symbol": "F", "side": "none", "filled_notional": 0.0, "fee_paid": 0.0},
    ]
    with open(os.path.join(src, "20260101", "orders.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")
    with open(os.path.join(src, "20260101", "fills.jsonl"), "w") as f:
        f.write(json.dumps({"side": "sell", "fill_notional": 50.0}, default=str) + "\n")

    n = migrate(src, dst)
    out = [json.loads(l) for l in open(os.path.join(dst, "20260101", "orders.jsonl"))]
    checks = [
        ("C1 unsigned sell is negated", out[0]["filled_notional"] == -100.5),
        ("C2 buy untouched", out[1]["filled_notional"] == 200.0),
        ("C3 None untouched (unknown is not a violation)", out[2]["filled_notional"] is None),
        ("C4 0.0 untouched (a measured zero has no direction)", out[3]["filled_notional"] == 0.0),
        ("C5 already-signed sell untouched (idempotent)", out[4]["filled_notional"] == -7.5),
        ("C6 side='none' untouched", out[5]["filled_notional"] == 0.0),
        ("C7 only one flip counted", n == 1),
        ("C8 sibling fields survive", out[0]["fee_paid"] == 1.0 and out[0]["symbol"] == "A"),
        ("C9 ★ fills.fill_notional untouched (convention is a COLUMN property)",
         json.load(open(os.path.join(dst, "20260101", "fills.jsonl")))["fill_notional"] == 50.0),
        ("C10 verify() passes on its own output", verify(src, dst) == 0),
    ]
    # C11: verify() must be able to FAIL — corrupt one unrelated field and watch it catch it
    bad = os.path.join(d, "bad")
    shutil.copytree(dst, bad)
    p = os.path.join(bad, "20260101", "orders.jsonl")
    lines = open(p).read().splitlines()
    lines[1] = lines[1].replace('"fee_paid": 2.0', '"fee_paid": 2.5')
    open(p, "w").write("\n".join(lines) + "\n")
    checks.append(("C11 ★ verify() catches an unrelated field change", verify(src, bad) == 1))

    print()
    fails = [n for n, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
    print(f"\n{len(checks)-len(fails)} passed, {len(fails)} failed")
    shutil.rmtree(d, ignore_errors=True)
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src"); ap.add_argument("--dst")
    ap.add_argument("--verify", nargs=2, metavar=("OLD", "NEW"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if a.verify:
        sys.exit(verify(*a.verify))
    if not (a.src and a.dst):
        ap.error("need --src and --dst, or --verify OLD NEW, or --selftest")
    migrate(a.src, a.dst)
