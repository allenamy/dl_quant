#!/usr/bin/env python3
"""t7_pull_assemble_addendum.py — RESULT_T7_ADDENDUM_1_full_pull.md = head + body + tail templates, {{P-n}} replaced by sections of pull/TABLES_PULL.md."""
import os, re, time
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = T7 + "/devices"
s = open(D + "/t7_pull_addendum_template_head.md").read().replace("{{RESULTS_SUMMARY}}", open(D + "/t7_pull_addendum_template_body.md").read().rstrip() + "\n")
s = s.replace("{{CREATED}}", "~12:3xZ") + open(D + "/t7_pull_addendum_template_tail.md").read()
tab = open(T7 + "/pull/TABLES_PULL.md").read(); parts = re.split(r"(?m)^## (P-\d+) ", tab); sec = {}
for i in range(1, len(parts), 2):
    title, rest = parts[i + 1].split("\n", 1); sec[parts[i]] = "### " + parts[i] + " " + title.strip() + "\n" + rest.strip()
for k, v in sec.items():
    assert s.count("{{" + k + "}}") == 1, k; s = s.replace("{{" + k + "}}", v)
assert "{{" not in s, "unfilled placeholder"
open(T7 + "/RESULT_T7_ADDENDUM_1_full_pull.md", "w").write(s); print("assembled", len(s))
