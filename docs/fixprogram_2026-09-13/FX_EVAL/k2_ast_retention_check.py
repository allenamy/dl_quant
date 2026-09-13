#!/usr/bin/env python3
"""k2_ast_retention_check.py — FIXPROGRAM §0.3 '旧断言逐字保留(AST 核)' for the K2 test file.
Compares the test file committed at C2 (efc2412a) with the working copy: every C2 top-level statement, and every statement inside the
module-only block, must reappear unchanged (same ast.dump) and in order, except the nodes declared in EXPECTED_CHANGED. Reports added
nodes. Exit 0 only when the changed set equals EXPECTED_CHANGED exactly.
"""
import ast, json, subprocess, sys, difflib
REPO = "/Users/haosiyu/Desktop/quant_research"; REL = "multi_asset/exports/research/common/tests_equivalence_labels.py"; C2 = "efc2412a"
EXPECTED_CHANGED = {
    "top:FunctionDef module_cat": "test-author error found at the first green run: 'gap detected' also matched 'no gap detected' (module-mode classifier only)",
    "module:check M06_one_sided": "test-author error found at the first green run: last case put lo exactly on the line; strict boundary makes INCONCLUSIVE correct (module-only check)",
}


def name_of(n, text):
    if isinstance(n, (ast.FunctionDef, ast.ClassDef)): return "%s %s" % (type(n).__name__, n.name)
    if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name) and n.value.args and isinstance(n.value.args[0], ast.Constant):
        return "%s %s" % (n.value.func.id, n.value.args[0].value)
    if isinstance(n, ast.Assign): return "Assign %s" % ",".join(ast.unparse(t) for t in n.targets)
    if isinstance(n, ast.If): return "If %s" % ast.unparse(n.test)[:60]
    return "%s@%d" % (type(n).__name__, n.lineno)


def module_block(tree):
    c = [n for n in tree.body if isinstance(n, ast.If) and ast.unparse(n.test) == "IMPL == 'module'" and any(isinstance(b, ast.FunctionDef) and b.name == "raises" for b in n.body)]
    assert len(c) == 1, "module-only block not unique"; return c[0]


def compare(old_nodes, new_nodes, old_text, new_text, scope, skip_old=()):
    changed, added = {}, []
    new_dumps = [ast.dump(n) for n in new_nodes]; j = 0; matched_new = set()
    for n in old_nodes:
        if n in skip_old: continue
        d = ast.dump(n); k = next((q for q in range(j, len(new_nodes)) if new_dumps[q] == d), None)
        if k is None:
            nm = name_of(n, old_text); cand = [m for m in new_nodes if name_of(m, new_text) == nm]
            diff = "\n".join(difflib.unified_diff(ast.get_source_segment(old_text, n).split("\n"), ast.get_source_segment(new_text, cand[0]).split("\n") if cand else [], lineterm="", n=0)) if cand else "(no node with the same name in the new file)"
            changed["%s:%s" % (scope, nm)] = diff
            if cand: matched_new.add(id(cand[0]))
        else:
            matched_new.add(id(new_nodes[k])); j = k + 1
    added = ["%s:%s" % (scope, name_of(m, new_text)) for m in new_nodes if id(m) not in matched_new]
    return changed, added


def main():
    old_text = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (C2, REL)], capture_output=True, text=True, check=True).stdout
    new_text = open("%s/%s" % (REPO, REL), encoding="utf-8").read()
    ot, nt = ast.parse(old_text), ast.parse(new_text)
    ob, nb = module_block(ot), module_block(nt)
    ch_top, add_top = compare(ot.body, nt.body, old_text, new_text, "top", skip_old=(ob,))
    ch_mod, add_mod = compare(ob.body, nb.body, old_text, new_text, "module")
    changed = dict(ch_top, **ch_mod); added = [a for a in add_top if not a.startswith("top:If IMPL == 'module'")] + add_mod
    ok = set(changed) == set(EXPECTED_CHANGED)
    out = dict(c2=C2, file=REL, changed=changed, expected_changed=EXPECTED_CHANGED, added=added, retained_top=len([n for n in ot.body if n is not ob]) - len(ch_top), retained_module_block=len(ob.body) - len(ch_mod), PASS=ok)
    print(json.dumps(out, indent=1, ensure_ascii=False))
    print("SUMMARY k2_ast_retention_check changed=%d expected=%d added=%d PASS=%s" % (len(changed), len(EXPECTED_CHANGED), len(added), ok))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
