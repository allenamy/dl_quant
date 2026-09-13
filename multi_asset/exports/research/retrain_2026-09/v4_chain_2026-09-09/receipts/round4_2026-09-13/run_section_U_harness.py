"""Harness: run ONLY the [U] section, with the helper definitions taken verbatim (AST) from tests_pipeline_gates.py."""
import ast, json, os, subprocess, sys, tempfile, hashlib as _hl, re as _re, shutil as _shu, glob as _glob
import numpy as np
HERE = sys.argv[1]; SECTION = sys.argv[2]
sys.dont_write_bytecode = True
T = ast.parse(open(f"{HERE}/tests_pipeline_gates.py").read())
FUNCS = {"check", "run", "_sha", "_bash", "_members", "_base", "_write_month", "_env1", "_env2", "_none_env", "_g"}
NAMES = {"PY", "_T0", "_NWm", "_KP", "_NA_REF", "_NA_NEW", "_N82", "_N89", "_SYM", "_KEYS"}
nodes = []
for n in T.body:
    if isinstance(n, ast.FunctionDef) and n.name in FUNCS: nodes.append(n)
    elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in NAMES for t in n.targets): nodes.append(n)
    elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Tuple) and [e.id for e in t.elts] == ["FAILS", "N"] for t in n.targets): nodes.append(n)
g = {"__name__": "section_U_harness", "json": json, "os": os, "subprocess": subprocess, "sys": sys, "tempfile": tempfile, "_hl": _hl, "_re": _re, "_shu": _shu, "_glob": _glob, "np": np, "HERE": HERE}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "tests_pipeline_gates_helpers", "exec"), g)
print("helpers:", sorted(n.name if isinstance(n, ast.FunctionDef) else ast.unparse(n.targets[0]) for n in nodes))
exec(compile(open(SECTION).read(), SECTION, "exec"), g)
print(f"\n{'ALL PASS' if not g['FAILS'] else 'FAILURES: ' + str(len(g['FAILS']))}  ({g['N'][0]} checks)")
sys.exit(1 if g["FAILS"] else 0)
