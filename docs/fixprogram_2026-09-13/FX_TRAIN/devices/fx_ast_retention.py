"""fx_ast_retention.py — FIXPROGRAM §0.3 '旧断言逐字保留(AST 核)' for FX-TRAIN edits of a test file.
Every top-level statement of the OLD file must reappear in the NEW file with the same ast.dump and in the same relative order; statements that differ
must be listed in the EXPECTED_CHANGED json (name -> reason) given on the command line, exactly. Added statements are reported.
usage: python fx_ast_retention.py <old.py> <new.py> [expected_changed.json]   exit 0 iff changed set == expected set"""
import ast, json, sys
old_p, new_p = sys.argv[1], sys.argv[2]; exp = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
ot, nt = ast.parse(open(old_p).read()), ast.parse(open(new_p).read())
nd = [ast.dump(n) for n in nt.body]; j = 0; changed = []; used = set()
def name(n, src):
    s = ast.get_source_segment(src, n) or ""
    return f"{type(n).__name__}@L{n.lineno}: {s.splitlines()[0][:100] if s else ''}"
osrc = open(old_p).read(); nsrc = open(new_p).read()
for n in ot.body:
    d = ast.dump(n); k = next((q for q in range(j, len(nd)) if nd[q] == d), None)
    if k is None: changed.append(name(n, osrc))
    else: used.add(k); j = k + 1
added = [name(nt.body[q], nsrc) for q in range(len(nt.body)) if q not in used]
ok = sorted(changed) == sorted(exp)
print(json.dumps({"old": old_p, "new": new_p, "old_top_level": len(ot.body), "new_top_level": len(nt.body), "retained_in_order": len(ot.body) - len(changed),
                  "changed": changed, "expected_changed": exp, "added": added, "PASS": ok}, indent=1))
print(f"SUMMARY fx_ast_retention old={len(ot.body)} retained={len(ot.body) - len(changed)} changed={len(changed)} expected={len(exp)} added={len(added)} PASS={ok}")
sys.exit(0 if ok else 1)
