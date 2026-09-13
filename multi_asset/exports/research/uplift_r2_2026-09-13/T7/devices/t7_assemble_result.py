#!/usr/bin/env python3
"""t7_assemble_result.py — RESULT_T7_feasibility.md = devices/t7_result_prose_template.md with {{T-n}} replaced by sections of receipts/TABLES_T7.md."""
import os, re
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s = open(T7 + "/devices/t7_result_prose_template.md").read(); tab = open(T7 + "/receipts/TABLES_T7.md").read()
parts = re.split(r"(?m)^## (T-\d) ", tab); sec = {}
for i in range(1, len(parts), 2):
    title, rest = parts[i + 1].split("\n", 1); sec[parts[i]] = "**" + parts[i] + " " + title.strip() + "**\n" + rest.strip()
for k, v in sec.items():
    assert s.count("{{" + k + "}}") == 1, k; s = s.replace("{{" + k + "}}", v)
assert "{{" not in s
open(T7 + "/RESULT_T7_feasibility.md", "w").write(s); print("assembled", len(s))
