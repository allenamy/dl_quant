#!/usr/bin/env python3
"""R25-01 census (independent review 7cbe907ba, lead ruling 2026-09-25): find the SAME CLASS as the H1 predicate defect in an executor tree.
The class: a verdict that appends / returns a violation only when a numeric comparison is True, on a quantity parsed with float() from a
record (x.get(...) / x[...]) — NaN makes every comparison False, so an unknown quantity reads as "no violation"; and the sibling
`float(x.get(k) or 0.0)`, which turns a MISSING quantity into a measured zero. READ-ONLY, static (ast); it LISTS candidate sites, it
does not triage them (a site is a defect only if the quantity can be unknown there and the verdict is a pass on False).
Per file: (A) `if <Compare>` tests whose operands contain float(<subscript or .get>) with no math.isfinite / _num-style guard in the same
function; (B) `float(<.get(...)> or 0...)` defaults. Output: one line per site `A|B file:line code`, then per-file counts and totals.
usage: /usr/bin/python3 census_quantity_gates.py <tree> [--glob 'live/*.py' --glob 'ops/*.py' ...] [--out F]"""
import ast, glob, os, sys


def is_record_read(n):
    return isinstance(n, ast.Subscript) or (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get")


def float_of_record(n):
    for s in ast.walk(n):
        if isinstance(s, ast.Call) and isinstance(s.func, ast.Name) and s.func.id == "float" and s.args:
            a = s.args[0]
            if is_record_read(a) or (isinstance(a, ast.BoolOp) and any(is_record_read(v) for v in a.values)):
                return True
    return False


def main():
    tree = os.path.abspath(sys.argv[1]); a = sys.argv[2:]
    globs = [a[i + 1] for i, x in enumerate(a) if x == "--glob"] or ["live/*.py", "ops/*.py", "scheduler/*.py", "signal/*.py"]
    out = a[a.index("--out") + 1] if "--out" in a else None
    files = sorted({f for g in globs for f in glob.glob(os.path.join(tree, g))})
    lines, per = [], {}
    for f in files:
        src = open(f).read(); rel = os.path.relpath(f, tree)
        try:
            T = ast.parse(src)
        except SyntaxError:
            lines.append(f"PARSE_ERROR {rel}"); continue
        src_l = src.splitlines(); nA = nB = 0
        funcs = [n for n in ast.walk(T) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))] + [T]
        seenA = set()
        for fn in funcs:
            guarded = "isfinite" in ast.unparse(fn) if hasattr(ast, "unparse") else False
            for n in ast.walk(fn):
                if isinstance(n, (ast.If, ast.IfExp)) and isinstance(n.test, (ast.Compare, ast.BoolOp, ast.UnaryOp)):
                    if any(isinstance(c, ast.Compare) and float_of_record(c) for c in ast.walk(n.test)) and not guarded and n.lineno not in seenA:
                        seenA.add(n.lineno); nA += 1; lines.append(f"A {rel}:{n.lineno} {src_l[n.lineno - 1].strip()[:150]}")
        for n in ast.walk(T):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "float" and n.args and isinstance(n.args[0], ast.BoolOp) \
                    and isinstance(n.args[0].op, ast.Or) and any(is_record_read(v) for v in n.args[0].values) \
                    and any(isinstance(v, ast.Constant) and v.value in (0, 0.0) for v in n.args[0].values):
                nB += 1; lines.append(f"B {rel}:{n.lineno} {src_l[n.lineno - 1].strip()[:150]}")
        if nA or nB: per[rel] = (nA, nB)
    lines.append("PER FILE (A comparisons on float(record) without an isfinite guard in the function, B float(record or 0) defaults):")
    for k, (x, y) in sorted(per.items(), key=lambda kv: -(kv[1][0] + kv[1][1])): lines.append(f"  {k}: A {x} B {y}")
    lines.append(f"CENSUS_QUANTITY_GATES files={len(files)} with_sites={len(per)} A={sum(v[0] for v in per.values())} B={sum(v[1] for v in per.values())}")
    print("\n".join(lines))
    if out: open(out, "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
