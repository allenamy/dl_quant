#!/usr/bin/env python3
"""fill a gates TEMPLATE: python3 fill_template.py <template> <out> KEY=VALUE ... (every <KEY> must be filled; refuses otherwise)"""
import json, re, sys
t = open(sys.argv[1]).read()
for kv in sys.argv[3:]:
    k, v = kv.split("=", 1); t = t.replace(f"<{k}>", v)
left = re.findall(r"<[A-Z_]+>", t)
assert not left, f"unfilled placeholders: {left}"
json.loads(t); open(sys.argv[2], "x").write(t); print("FILLED", sys.argv[2])
