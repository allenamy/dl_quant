"""Acceptance: can every module on the daily chain actually be LOADED?

★ WHY THIS EXISTS
On 2026-07-25 a portability refactor (`ef2ddbb`, "derive all paths from __file__") moved
`MA = os.path.dirname(...)` BELOW its first use in three files — `build_tail.py`, `paper_pnl.py`,
`monitor.py`. All three raised `NameError: name 'MA' is not defined` at import AND as scripts
(measured rc=1). `build_tail` is step 1 of run_daily.sh, and that runner aborts the whole chain on
any step failure, so the next scheduled run would have advanced ZERO anchors — silently, while the
last log on disk said `done`, because it was written by the pre-refactor build.

Six acceptance suites were green throughout. Not one of them executed these modules' top level.

    ★ "The component is correct" is not "the component can be loaded."

This bug required no domain knowledge whatsoever to find. It only required someone to try loading
the module once. That is the entire content of check (1) below.

Two checks, deliberately different in kind:

  (1) IMPORT SMOKE — import every module the production runner actually invokes. The target list is
      PARSED OUT OF run_daily.sh, never hand-maintained: a hand-written list drifts away from the
      chain it is supposed to cover, and the drift is invisible precisely when it matters.

  (2) STATIC SCAN — module-level use-before-assignment across engine/ and factory/. Import smoke
      only covers what the runner calls today; the scan covers the whole tree, including modules
      that are only imported on a branch. Finding one instance of a defect class should always be
      followed by "how many more are there?", and the answer must come from a machine.

Both checks are exercised against a KNOWN-BAD fixture first (`--selftest` runs it unconditionally),
because a checker never observed failing is an unverified claim — our own rule, applied here.

Usage:
    python engine/live/tests_import_smoke.py            # both checks + the red-capability proof
"""
from __future__ import annotations

import ast
import glob
import importlib
import os
import re
import sys
import tempfile
import traceback

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
RUNNER = os.path.join(MA, "engine", "live", "run_daily.sh")
SCAN_ROOTS = [os.path.join(MA, "engine"), os.path.join(MA, "factory")]

_fails: list[str] = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {'PASS' if ok else '★FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        _fails.append(f"{name}: {detail}")
    return ok


# ── (2) static: module-level use-before-assignment ───────────────────────────────────────────────
_NESTED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda,
                  ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def _module_level_names(node):
    """Names in `node` that really execute in module scope NOW.

    ★ `ast.walk` is breadth-first over the WHOLE subtree, so `continue`-ing on a Lambda node does
    not stop you from visiting its body — that mistake made this scanner report `lambda rec:
    rec[...]` as 'rec used before assignment' against an unrelated local 100 lines away. Nested
    scopes must be excluded by SUBTREE, not by node.
    """
    skip = set()
    for n in ast.walk(node):
        if isinstance(n, _NESTED_SCOPES):
            for inner in ast.walk(n):
                skip.add(id(inner))
    return [n for n in ast.walk(node) if isinstance(n, ast.Name) and id(n) not in skip]


def scan_use_before_assign(path: str):
    """Names LOADED at module level before their module-level Store. Deferred scopes (functions,
    classes, lambdas, comprehensions) do not execute now and are excluded whole."""
    try:
        tree = ast.parse(open(path, encoding="utf-8").read(), path)
    except SyntaxError as e:
        return [f"SyntaxError: {e}"]
    top_assign: dict[str, int] = {}
    for node in tree.body:                       # module-level assignments only
        if isinstance(node, _NESTED_SCOPES):
            continue
        for t in _module_level_names(node):
            if isinstance(t.ctx, ast.Store):
                top_assign.setdefault(t.id, node.lineno)
    found, done = [], set()
    for node in tree.body:
        if isinstance(node, _NESTED_SCOPES):
            continue
        for t in _module_level_names(node):
            if isinstance(t.ctx, ast.Load):
                if t.id in top_assign and top_assign[t.id] > node.lineno and t.id not in done:
                    done.add(t.id)
                    found.append(f"'{t.id}' used at line {node.lineno}, assigned at line "
                                 f"{top_assign[t.id]}")
            elif isinstance(t.ctx, ast.Store):
                done.discard(t.id)
    return found


# ── (1) import smoke, over the modules the RUNNER invokes ────────────────────────────────────────
def chain_modules() -> list[str]:
    """Parsed from run_daily.sh so this list cannot drift away from the production chain."""
    try:
        txt = open(RUNNER, encoding="utf-8").read()
    except Exception:
        return []
    mods = re.findall(r'engine/live/([A-Za-z_][A-Za-z0-9_]*)\.py', txt)
    seen, out = set(), []
    for m in mods:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


BAD_FIXTURE = "import os\nimport sys\nsys.path.insert(0, MA)\nMA = os.path.dirname(__file__)\n"


def main() -> int:
    print("== red-capability proof (a checker never seen failing is an unverified claim) ==")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "known_bad.py")
        open(p, "w").write(BAD_FIXTURE)
        hits = scan_use_before_assign(p)
        check("static scan flags a known-bad fixture", bool(hits), str(hits[:1]))
        good = os.path.join(d, "known_good.py")
        open(good, "w").write("import os\nMA = os.path.dirname(__file__)\nX = MA + '/x'\n")
        check("static scan does NOT flag a known-good fixture", not scan_use_before_assign(good))

    print("\n== (1) import smoke: every module run_daily.sh invokes ==")
    mods = chain_modules()
    check("run_daily.sh yielded a non-empty module list", bool(mods),
          f"parsed {len(mods)}: {', '.join(mods)}")
    sys.path.insert(0, MA)
    sys.path.insert(0, os.path.join(MA, "engine", "live"))
    for m in mods:
        try:
            importlib.import_module(m)
            check(f"import {m}", True)
        except Exception as e:
            check(f"import {m}", False, f"{type(e).__name__}: {e}")
            traceback.print_exc(limit=2)

    print("\n== (2) static scan: module-level use-before-assignment (engine/ + factory/) ==")
    n_files, offenders = 0, []
    for root in SCAN_ROOTS:
        for f in sorted(glob.glob(os.path.join(root, "**", "*.py"), recursive=True)):
            n_files += 1
            for msg in scan_use_before_assign(f):
                offenders.append(f"{os.path.relpath(f, MA)}: {msg}")
    check(f"no module-level use-before-assignment in {n_files} files", not offenders,
          "; ".join(offenders[:4]))

    print(f"\n{'ALL PASS' if not _fails else '★ ' + str(len(_fails)) + ' FAILURE(S)'}")
    for f in _fails:
        print(f"  - {f}")
    return 0 if not _fails else 1


if __name__ == "__main__":
    sys.exit(main())
