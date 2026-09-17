#!/usr/bin/env python3
"""E-0917-B regression: the exporter's atomic write block, executed VERBATIM (AST-extracted from pod_f10_np_export_v4.py) on a tiny fixture.
Red capability: the pre-fix statement `tmp = NP_OUT + ".tmp"` followed by np.savez leaves "<out>.tmp.npz" and os.replace fails."""
import ast, os, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:200]) if detail is not None else ""), flush=True)
src = open(f"{HERE}/pod_f10_np_export_v4.py").read(); tree = ast.parse(src)
stmts = [n for n in tree.body if isinstance(n, (ast.Assign, ast.Expr, ast.Assert)) and n.lineno >= 1]
i0 = next(i for i, n in enumerate(stmts) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "tmp" for t in n.targets))
block = stmts[i0:i0 + 4]; code = compile(ast.Module(body=block, type_ignores=[]), "np_export_write_block", "exec")
d = tempfile.mkdtemp(); NP_OUT = f"{d}/f10_live_s42_np.npz"; ns = {"np": np, "os": os, "NP_OUT": NP_OUT, "ARRS": {"w": np.zeros(3, np.float32)}, "META": {"generation": "t"}}
exec(code, ns)
check("★★★ W1 the real write block (4 statements, AST-extracted) writes NP_OUT and leaves no temp file", os.path.isfile(NP_OUT) and not [f for f in os.listdir(d) if ".tmp" in f], os.listdir(d))
check("W2 the written npz round-trips its arrays and meta", np.load(NP_OUT)["w"].shape == (3,) and str(np.load(NP_OUT)["generation"]) == "t")
d2 = tempfile.mkdtemp(); NP2 = f"{d2}/f10_live_s42_np.npz"; ns2 = {"np": np, "os": os, "NP_OUT": NP2, "ARRS": {"w": np.zeros(3, np.float32)}, "META": {}}
try:
    exec(compile("tmp = NP_OUT + '.tmp'\nnp.savez(tmp, **ARRS)\nos.replace(tmp, NP_OUT)", "prefix", "exec"), ns2); red = "no error"
except FileNotFoundError as e: red = "FileNotFoundError"
check("★★★ W3 RED capability: the PRE-FIX statement (`NP_OUT + '.tmp'`) leaves '<out>.tmp.npz' and os.replace raises FileNotFoundError — the 11:42:58Z failure reproduced", red == "FileNotFoundError" and os.path.isfile(NP2 + ".tmp.npz") and not os.path.isfile(NP2), (red, os.listdir(d2)))
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
