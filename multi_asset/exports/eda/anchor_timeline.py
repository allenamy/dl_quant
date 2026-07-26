#!/usr/bin/env python3
"""Derive the anchor's execution timeline FROM THE CODE, then diff it against the previous run.

★ WHY THIS EXISTS
A coverage table asks "which step was verified, by whom, with what evidence?" — and that question
needs a list of steps. If a human writes the list, it inherits that human's blind spots: they omit
the steps they don't know exist, which are exactly the steps nobody has checked. The same argument
already retired two hand-maintained lists in this project (the acceptance suite's module list, now
parsed from the runner; the "which modules does the daily chain touch" list). This applies it to
the anchor's own control flow.

★ THE THREE PROPERTIES THAT MAKE IT WORTH BUILDING (all requested by team-lead, 2026-07-25)

  1. STABLE IDENTITY. A step is `module:function:branch-path`, never a line number or an ordinal.
     Line numbers move on every edit; an ordinal shifts when anything is inserted above. Either
     would make every diff report "the whole table changed", which is the same as reporting nothing.

  2. REGENERABLE AND DIFFABLE. Re-run after a code change and it prints what APPEARED and what
     DISAPPEARED. Those two are not symmetric: a step that vanished may have been deleted, or it
     may have moved into a construct this parser cannot follow — and the consequences differ
     completely. So they are reported separately, never as a single "changed" count.

  3. ★ THE GIVE-UP LIST IS A FIRST-CLASS OUTPUT, not a footnote. Every call site this parser
     declines to follow (dynamic import, getattr, a call on a value it cannot resolve) is listed
     with its reason. Without it, "not in the table" and "the parser couldn't see it" collapse
     into the same appearance — and a coverage table's most dangerous reading is
     "what isn't listed doesn't exist".

Usage:
    python anchor_timeline.py --repo ~/dl_quant_live            # generate + diff vs stored
    python anchor_timeline.py --repo ~/dl_quant_live --json out.json
"""
from __future__ import annotations

import argparse
import ast
import json
import os
from typing import Any, Dict, List, Optional, Tuple

# entry points of one anchor, in the order the process runs them
ENTRIES = [("run_anchor", "main"), ("anchor_loop", "run_anchor"), ("anchor_loop", "complete_anchor")]
MAX_DEPTH = 3

# ★ DECLARED INJECTION MAP. The anchor loop takes its broker / executor / logger / notifier as
# constructor arguments, so `self.broker.submit()` cannot be resolved statically — and those are
# precisely the calls that place orders. Leaving them in the give-up list would mean the table
# covers the ORCHESTRATION and misses the MONEY. So the binding is DECLARED here rather than
# inferred, and the declaration is part of the table's provenance: if an injection is rebound to a
# different class, this map is wrong and the table silently follows the wrong code. Reviewed
# against scheduler/run_anchor.py's construction site whenever the table is regenerated.
INJECTED = {
    "self.broker":   "binance_broker",     # run_anchor.py: BB.BinanceBroker(mode=mode)
    "self.executor": "binance_executor",   # run_anchor.py: EX.RebalanceExecutor(b)
    "self.log":      "pilot_log",          # run_anchor.py: PLOG.PilotLogger(log_root)
    "self.src":      "fapi_source",        # anchor_loop.py: FS.FapiSource()
    "self.filters":  "binance_executor",   # executor.SymbolFilters(broker)
}


class Deriver:
    def __init__(self, repo: str):
        self.repo = os.path.abspath(os.path.expanduser(repo))
        self.dirs = [os.path.join(self.repo, d) for d in ("scheduler", "live", "signal", "ops")]
        self.mods: Dict[str, ast.Module] = {}
        self.src: Dict[str, List[str]] = {}
        for d in self.dirs:
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                if f.endswith(".py"):
                    p = os.path.join(d, f)
                    try:
                        text = open(p, encoding="utf-8").read()
                        self.mods[f[:-3]] = ast.parse(text, p)
                        self.src[f[:-3]] = text.splitlines()
                    except SyntaxError:
                        pass
        self.steps: List[Dict[str, Any]] = []
        self.gaveup: List[Dict[str, Any]] = []
        self._seen: set = set()
        self._reached: Dict[Tuple[str, str], str] = {}

    # ── helpers ─────────────────────────────────────────────────────────────────────────────
    def _func(self, mod: str, fn: str) -> Optional[ast.AST]:
        tree = self.mods.get(mod)
        if tree is None:
            return None
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fn:
                return n
        return None

    def _alias_map(self, mod: str) -> Dict[str, str]:
        """`import watchdog as WD` -> {'WD': 'watchdog'}; also plain `import x`."""
        out = {}
        tree = self.mods.get(mod)
        if tree is None:
            return out
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    base = a.name.split(".")[-1]
                    if base in self.mods:
                        out[a.asname or base] = base
        return out

    def _resolve(self, call: ast.Call, mod: str, aliases: Dict[str, str]) -> Tuple[Optional[str], Optional[str], str]:
        """(target_module, target_fn, label). label is what we print for the step."""
        f = call.func
        # self.<injected>.method()  — resolved through the DECLARED map above
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Attribute) \
                and isinstance(f.value.value, ast.Name) and f.value.value.id == "self":
            owner = f"self.{f.value.attr}"
            if owner in INJECTED:
                return INJECTED[owner], f.attr, f"{owner}.{f.attr}()"
            return None, None, f"{owner}.{f.attr}()"
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            owner, name = f.value.id, f.attr
            if owner in aliases:
                return aliases[owner], name, f"{aliases[owner]}.{name}()"
            if owner == "self":
                return mod, name, f"self.{name}()"
            return None, None, f"{owner}.{name}()"
        if isinstance(f, ast.Name):
            if self._func(mod, f.id) is not None:
                return mod, f.id, f"{f.id}()"
            return None, None, f"{f.id}()"
        return None, None, ast.unparse(f)[:60] if hasattr(ast, "unparse") else "<expr>"

    # ── the walk ────────────────────────────────────────────────────────────────────────────
    def walk(self, mod: str, fn: str, path: Tuple[str, ...] = (), depth: int = 0,
             reached_via: str = "entry"):
        key = (mod, fn)
        if depth > MAX_DEPTH:
            self.gaveup.append({"where": f"{mod}:{fn}", "reason": f"depth > {MAX_DEPTH}"})
            return
        if key in self._seen:
            return
        self._seen.add(key)
        node = self._func(mod, fn)
        if node is None:
            self.gaveup.append({"where": f"{mod}:{fn}", "reason": "function not found in parsed modules"})
            return
        aliases = self._alias_map(mod)
        self._reached[(mod, fn)] = reached_via
        self._body(node.body, mod, fn, path, depth, aliases)

    def _body(self, body, mod, fn, path, depth, aliases):
        for st in body:
            if isinstance(st, ast.Try):
                for sub in st.body:
                    self._body([sub], mod, fn, path + ("try",), depth, aliases)
                for h in st.handlers:
                    exc = ast.unparse(h.type)[:30] if h.type is not None and hasattr(ast, "unparse") else "Exception"
                    self._body(h.body, mod, fn, path + (f"except:{exc}",), depth, aliases)
                if st.orelse:
                    self._body(st.orelse, mod, fn, path + ("else",), depth, aliases)
                if st.finalbody:
                    self._body(st.finalbody, mod, fn, path + ("finally",), depth, aliases)
                continue
            if isinstance(st, ast.If):
                cond = ast.unparse(st.test)[:48] if hasattr(ast, "unparse") else "?"
                self._body(st.body, mod, fn, path + (f"if:{cond}",), depth, aliases)
                if st.orelse:
                    self._body(st.orelse, mod, fn, path + (f"else:{cond}",), depth, aliases)
                continue
            if isinstance(st, (ast.For, ast.While)):
                self._body(st.body, mod, fn, path + ("loop",), depth, aliases)
                continue
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue                       # defined here, not executed here
            for c in [n for n in ast.walk(st) if isinstance(n, ast.Call)]:
                tmod, tfn, label = self._resolve(c, mod, aliases)
                sid = f"{mod}:{fn}:" + ("/".join(path) if path else "-") + f"::{label}"
                if tmod is None:
                    # not followed — say so, with the reason, as a first-class record
                    owner = label.split(".")[0].split("(")[0]
                    EXTERNAL = {"np", "pd", "numpy", "pandas", "torch", "json", "os", "time",
                                "sys", "math", "re", "glob", "urllib", "hashlib", "hmac",
                                "subprocess", "shutil", "tempfile", "calendar", "datetime",
                                "collections", "itertools", "print", "len", "str", "int",
                                "float", "bool", "list", "dict", "set", "sorted", "sum", "min",
                                "max", "abs", "round", "open", "range", "zip", "enumerate",
                                "any", "all", "type", "isinstance", "getattr", "repr"}
                    kind = "external_or_builtin" if owner in EXTERNAL else "LOCAL_UNFOLLOWED"
                    self.gaveup.append({"where": f"{mod}:{fn}", "call": label, "kind": kind,
                                        "reason": ("stdlib/3rd-party — not our coverage surface"
                                                   if kind == "external_or_builtin" else
                                                   "attribute call on a value this parser cannot "
                                                   "resolve (self.<obj>.m() / injected dependency)")})
                    continue
                self.steps.append({"id": sid, "module": mod, "function": fn,
                                   "branch": "/".join(path) if path else "-",
                                   "calls": label, "target": f"{tmod}:{tfn}",
                                   "exception_branch": any(p.startswith("except") for p in path),
                                   "fn_reached_via": self._reached.get((mod, fn), "entry")})
                # ★ the branch path RESETS on entering the callee. Carrying the caller's condition
                # down would label every step inside compute_preds with run_anchor's `if LIVE_
                # COMPUTE_PREDS` — a step's branch must describe where it sits in ITS OWN function.
                # How it was reached is a separate fact, recorded as `reached_via`.
                self.walk(tmod, tfn, (), depth + 1, reached_via=("/".join(path) if path else "-"))

    def run(self) -> Dict[str, Any]:
        for mod, fn in ENTRIES:
            self.walk(mod, fn)
        # dedupe give-ups
        seen, gu = set(), []
        for g in self.gaveup:
            k = (g.get("where"), g.get("call"), g["reason"])
            if k not in seen:
                seen.add(k)
                gu.append(g)
        return {"repo": self.repo, "entries": [f"{m}:{f}" for m, f in ENTRIES],
                "n_steps": len(self.steps), "steps": self.steps,
                "n_exception_steps": sum(1 for s in self.steps if s["exception_branch"]),
                "unresolved_call_sites": gu, "n_unresolved": len(gu),
                "n_unresolved_local": sum(1 for g in gu if g.get("kind") == "LOCAL_UNFOLLOWED"),
                "n_unresolved_external": sum(1 for g in gu if g.get("kind") == "external_or_builtin")}


def diff(prev: Dict[str, Any], cur: Dict[str, Any]) -> Dict[str, Any]:
    """Appeared and disappeared are reported SEPARATELY and never summed: a step that vanished may
    have been deleted, or may have moved somewhere this parser cannot follow."""
    p = {s["id"] for s in prev.get("steps", [])}
    c = {s["id"] for s in cur["steps"]}
    return {"appeared": sorted(c - p), "disappeared": sorted(p - c),
            "n_appeared": len(c - p), "n_disappeared": len(p - c),
            "note": ("a disappeared step is EITHER deleted OR moved into a construct the parser "
                     "cannot follow — check `unresolved_call_sites` before concluding it is gone")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="~/dl_quant_live")
    ap.add_argument("--json", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                   "anchor_timeline.json"))
    a = ap.parse_args()
    cur = Deriver(a.repo).run()

    prev = None
    if os.path.exists(a.json):
        try:
            prev = json.load(open(a.json))
        except Exception:
            prev = None

    print(f"锚点时序: {cur['n_steps']} 步 (其中 {cur['n_exception_steps']} 步在异常分支内)")
    print(f"未解析的调用点: {cur['n_unresolved']} —— 其中 **本地代码但未跟进 {cur['n_unresolved_local']}**"
          f" (真盲区), 外部/内建 {cur['n_unresolved_external']} (不属覆盖面)")
    print()
    last = None
    for s in cur["steps"]:
        head = f"{s['module']}:{s['function']}"
        if head != last:
            print(f"── {head}")
            last = head
        mark = "!" if s["exception_branch"] else " "
        print(f"  {mark} [{s['branch'][:46]:46s}] {s['calls']:38s} -> {s['target']}")
    print("\n未解析 (parser 主动放弃的调用点 —— '不在表上' 与 '看不见' 必须可区分):")
    loc = [g for g in cur["unresolved_call_sites"] if g.get("kind") == "LOCAL_UNFOLLOWED"]
    for g in loc[:30]:
        print(f"  {g['where']:32s} {g.get('call','-'):36s} {g['reason'][:60]}")
    if len(loc) > 30:
        print(f"  … 另有 {len(loc)-30} 处本地未跟进 (见 JSON)")

    if prev is not None:
        d = diff(prev, cur)
        print(f"\n与上一版比较: 新增 {d['n_appeared']} 步, 消失 {d['n_disappeared']} 步")
        for s in d["appeared"]:
            print(f"  + {s}")
        for s in d["disappeared"]:
            print(f"  - {s}")
        if d["n_disappeared"]:
            print(f"  ★ {d['note']}")
        cur["diff_vs_previous"] = d
    else:
        print("\n(无上一版, 本次为首次生成 —— 不是'零变化')")

    json.dump(cur, open(a.json, "w"), indent=1, ensure_ascii=False)
    print(f"\n-> {a.json}")
