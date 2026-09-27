"""Verify the append-only ledger: every line parses, anchors strictly increase, and each line's prev_line_sha256 is the sha of the line
before it. exit 0 OK / 5 BROKEN (prints the first bad line). usage: shadow_ab_verify_ledger.py <ledger.jsonl>"""
import sys, json, hashlib, os
p = sys.argv[1]
if not os.path.exists(p): print("LEDGER_OK empty"); sys.exit(0)
lines = open(p).read().splitlines(); prev = None; last = -1
for i, l in enumerate(lines):
    try: d = json.loads(l)
    except Exception as e: print(f"LEDGER_BROKEN line {i + 1}: {e}"); sys.exit(5)
    if d.get("prev_line_sha256") != prev: print(f"LEDGER_BROKEN line {i + 1}: prev sha mismatch"); sys.exit(5)
    if d["anchor"] <= last: print(f"LEDGER_BROKEN line {i + 1}: anchor not increasing"); sys.exit(5)
    prev = hashlib.sha256(l.encode()).hexdigest(); last = d["anchor"]
print(f"LEDGER_OK lines={len(lines)} last_anchor={last}")
