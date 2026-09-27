"""Insert ab_hook_block.py into the SANDBOX copy of combo_stage.py right after the unique '④ COMBO 落盘' log line.
Fail-closed (exit 3) unless that line occurs exactly once and the hook's required names are all assigned before it.
usage: shadow_ab_insert_hook.py <sandbox combo_stage.py> <ab_hook_block.py> <HOOK.json>"""
import sys, json, hashlib
stage, block, out = sys.argv[1:4]
src = open(stage, encoding="utf-8").read(); hook = open(block, encoding="utf-8").read()
lines = src.split("\n")
idx = [i for i, l in enumerate(lines) if l.startswith('log(f"④ COMBO 落盘')]
REQ = ("legz", "zf", "w3m", "rn8_m", "FTRIM_HI", "chain", "exec_reshape", "H_kc_prev", "H_fc_prev", "sm_kc", "sm_fc", "combo",
       "kc_src", "fc_src", "syms", "NW", "A", "H")
rec = {"stage_sha256_before": hashlib.sha256(src.encode()).hexdigest(), "hook_sha256": hashlib.sha256(hook.encode()).hexdigest(),
       "insertion_line_matches": len(idx)}
if len(idx) != 1:
    rec["STATUS"] = "UNAVAILABLE: insertion point not unique"; json.dump(rec, open(out, "w"), indent=1); print(rec["STATUS"]); sys.exit(3)
before = "\n".join(lines[:idx[0] + 1])
import ast
_bound = set()
for node in ast.walk(ast.parse(before)):          # every name BOUND at module level before the insertion point (assign/def/import/for)
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)): _bound.add(node.name)
    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store): _bound.add(node.id)
    elif isinstance(node, (ast.Import, ast.ImportFrom)): _bound.update((a.asname or a.name).split(".")[0] for a in node.names)
missing = [n for n in REQ if n not in _bound]
rec["required_names_not_assigned_before_insertion"] = missing
if missing:
    rec["STATUS"] = "UNAVAILABLE: hook names missing"; json.dump(rec, open(out, "w"), indent=1); print(rec["STATUS"], missing); sys.exit(3)
new = "\n".join(lines[:idx[0] + 1] + [hook] + lines[idx[0] + 1:])
open(stage, "w", encoding="utf-8").write(new)
rec["stage_sha256_after"] = hashlib.sha256(new.encode()).hexdigest(); rec["insert_after_line"] = idx[0] + 1; rec["STATUS"] = "OK"
json.dump(rec, open(out, "w"), indent=1); print("HOOK_INSERTED after line", idx[0] + 1)
