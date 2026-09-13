"""List every `a or b` BoolOp and every bare truthiness test (if / ifexp / comprehension-if / while /
`not x`) in a Python file, with line numbers and source text. Read-only."""
import ast, sys
path = sys.argv[1]
src = open(path).read()
tree = ast.parse(src)
seg = lambda n: (ast.get_source_segment(src, n) or "").replace("\n", " ")[:150]
rows = []
def bare(test):
    # a truthiness test that is not a comparison / isinstance / boolean-valued call we recognise
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return bare(test.operand)
    if isinstance(test, ast.BoolOp):
        return any(bare(v) for v in test.values)
    return isinstance(test, (ast.Name, ast.Attribute, ast.Subscript, ast.Call)) and not (
        isinstance(test, ast.Call) and isinstance(test.func, ast.Name) and test.func.id in ("isinstance", "any", "all", "bool", "callable", "hasattr"))
for n in ast.walk(tree):
    if isinstance(n, ast.BoolOp) and isinstance(n.op, ast.Or):
        rows.append((n.lineno, "OR   ", seg(n)))
    elif isinstance(n, (ast.If, ast.IfExp, ast.While)) and bare(n.test):
        rows.append((n.lineno, "TRUTH", seg(n.test)))
    elif isinstance(n, ast.comprehension):
        for t in n.ifs:
            if bare(t):
                rows.append((t.lineno, "TRUTH", seg(t)))
    elif isinstance(n, ast.Compare) and any(isinstance(o, (ast.In, ast.NotIn)) for o in n.ops) and any(
            isinstance(c, ast.Tuple) and any(isinstance(e, ast.Constant) and e.value in (0, 0.0) and not isinstance(e.value, bool) for e in c.elts) for c in n.comparators):
        rows.append((n.lineno, "IN0  ", seg(n)))
for ln, kind, s in sorted(set(rows)):
    print(f"{ln:4d} {kind} {s}")
