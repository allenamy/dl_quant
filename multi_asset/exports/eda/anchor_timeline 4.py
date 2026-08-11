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

  4. ★ STALENESS IS A PROPERTY THAT RINGS ON ITS OWN (team-lead, 2026-07-26; tenth failure form).
     See the block below.

★ THE TENTH FAILURE FORM, AND WHY IT NEEDED A MECHANISM RATHER THAN A HABIT
The coverage table recorded: "`anchor_loop:_universe_gate` executed on real venue data at
2026-07-26T00:01:22Z" — observation correct, condition true, timing fine, attribution fine. Then a
ninth step (the `maxNotionalValue == 0` withholding) landed INSIDE that function at 00:56:39Z
(`bcfa1b5`), 55 minutes after its last and only execution. **The verdict now certified a function
that no longer existed**, and nothing in the table could notice: the step IDs are stable by design,
the count still read "9 steps", and only a diff would have shown it.

  Mirror of failure form 3: there the VERIFICATION ENVIRONMENT changed between observation and
  check; here the VERIFIED OBJECT did. The positive tell, when there is one, is an ABSENCE: the
  00:01Z log line has no `n_zero_cap_withheld` key, while the current return dict always emits one.

So: every function carries `func_last_commit` (per FUNCTION, via `git log -L <lines>:<file>` — a
file-level timestamp would invalidate every verdict on every commit, and a check that cries wolf
daily is a check nobody reads). A verdict whose `evidence_utc` predates that commit is
AUTO-DOWNGRADED to UNKNOWN. Nobody has to remember to ask.

Two directions this refuses to fold into the benign value, per this project's standing rule:
  - `git log -L` fails / file untracked / not a repo  ⇒ UNKNOWN, never "fresh".
  - the file has UNCOMMITTED changes                  ⇒ UNKNOWN for every function in it. Git
    history cannot see the working tree, so a clean-looking `func_last_commit` would otherwise
    certify code that is not the code on disk.

Usage:
    python anchor_timeline.py --repo ~/dl_quant_live            # generate + diff vs stored
    python anchor_timeline.py --repo ~/dl_quant_live --json out.json
    python anchor_timeline.py --evidence anchor_coverage_evidence.json   # staleness audit
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
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


def _utc(ts: int) -> str:
    import datetime as _dt
    return _dt.datetime.fromtimestamp(ts, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(s: str) -> Optional[int]:
    import datetime as _dt
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ", "%Y-%m-%d"):
        try:
            return int(_dt.datetime.strptime(s, fmt).replace(tzinfo=_dt.timezone.utc).timestamp())
        except ValueError:
            continue
    return None


class Deriver:
    def __init__(self, repo: str):
        self.repo = os.path.abspath(os.path.expanduser(repo))
        self.dirs = [os.path.join(self.repo, d) for d in ("scheduler", "live", "signal", "ops")]
        self.mods: Dict[str, ast.Module] = {}
        self.src: Dict[str, List[str]] = {}
        self.relpath: Dict[str, str] = {}
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
                        self.relpath[f[:-3]] = os.path.relpath(p, self.repo)
                    except SyntaxError:
                        pass
        self.steps: List[Dict[str, Any]] = []
        self.gaveup: List[Dict[str, Any]] = []
        self._seen: set = set()
        self._reached: Dict[Tuple[str, str], str] = {}
        self._touch: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._dirty = self._dirty_files()

    # ── git: when was THIS FUNCTION last changed ─────────────────────────────────────────────
    def _git(self, *args) -> Optional[str]:
        try:
            r = subprocess.run(("git", "-C", self.repo) + args, capture_output=True, text=True,
                               timeout=30)
            return r.stdout if r.returncode == 0 else None
        except Exception:
            return None

    def _dirty_files(self) -> Optional[set]:
        """Uncommitted paths. None = we could not find out, which is NOT the same as 'clean'."""
        out = self._git("status", "--porcelain")
        if out is None:
            return None
        return {ln[3:].strip() for ln in out.splitlines() if ln.strip()}

    def func_last_commit(self, mod: str, fn: str) -> Dict[str, Any]:
        """Newest commit touching this function's OWN line range. Any failure -> unknown=True."""
        key = (mod, fn)
        if key in self._touch:
            return self._touch[key]
        rel, node = self.relpath.get(mod), self._func(mod, fn)
        if rel is None or node is None:
            res = {"unknown": True, "why": "module or function not resolved"}
            self._touch[key] = res
            return res
        # decorators belong to the function: a changed decorator changes what the function does
        lo = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        hi = getattr(node, "end_lineno", None) or lo
        if self._dirty is None:
            res = {"unknown": True, "why": "git status unavailable — cannot rule out uncommitted "
                                           "edits, and history alone would look clean"}
        elif rel in self._dirty:
            res = {"unknown": True, "why": f"{rel} has UNCOMMITTED changes — git history cannot "
                                           f"see the working tree"}
        else:
            out = self._git("log", "-L", f"{lo},{hi}:{rel}", "--format=%H%x09%ct%x09%s", "-s",
                            "-n", "1")
            if not out or "\t" not in out:
                res = {"unknown": True, "why": "git log -L returned nothing (untracked / no "
                                               "history / range not followable)"}
            else:
                sha, ts, subj = out.splitlines()[0].split("\t", 2)
                res = {"unknown": False, "sha": sha[:7], "ts": int(ts), "subject": subj[:80],
                       "utc": _utc(int(ts)), "lines": f"{lo}-{hi}"}
        self._touch[key] = res
        return res

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
        # per-FUNCTION last-touch, attached to every one of its steps
        funcs: Dict[str, Dict[str, Any]] = {}
        for s in self.steps:
            f = f"{s['module']}:{s['function']}"
            if f not in funcs:
                funcs[f] = self.func_last_commit(s["module"], s["function"])
            s["func_last_commit"] = funcs[f]
        return {"repo": self.repo, "entries": [f"{m}:{f}" for m, f in ENTRIES],
                "n_steps": len(self.steps), "steps": self.steps,
                "n_exception_steps": sum(1 for s in self.steps if s["exception_branch"]),
                "functions": funcs, "n_functions": len(funcs),
                "n_functions_unknown_age": sum(1 for v in funcs.values() if v.get("unknown")),
                "working_tree_dirty": (None if self._dirty is None else sorted(self._dirty)),
                "unresolved_call_sites": gu, "n_unresolved": len(gu),
                "n_unresolved_local": sum(1 for g in gu if g.get("kind") == "LOCAL_UNFOLLOWED"),
                "n_unresolved_external": sum(1 for g in gu if g.get("kind") == "external_or_builtin")}


# ── staleness audit: the tenth failure form, mechanised ─────────────────────────────────────────
def last_green_suite_run(repo: str, suite: str) -> Dict[str, Any]:
    """Latest acceptance log for `suite`, and whether it ended ALL PASS.

    ★ A suite that RAN is not a suite that PASSED, and a red run pins nothing. The filename
    carries the UTC stamp (`<YYYYMMDDTHHMMSSZ>_<suite>.log`); the verdict has to come from the
    file's contents, because a run that crashed halfway still leaves a log."""
    d = os.path.join(os.path.expanduser(repo), "state", "acceptance")
    if not os.path.isdir(d):
        return {"unknown": True, "why": "no state/acceptance directory"}
    logs = sorted(f for f in os.listdir(d) if f.endswith(f"_{suite}.log"))
    if not logs:
        return {"unknown": True, "why": f"no acceptance log for {suite}"}
    # ★ AN IN-FLIGHT LOG IS NOT A FAILED RUN. Reading the newest file unconditionally caught a
    # suite mid-write (the tail stopped at an assertion, no terminal marker) and reported
    # "NOT ALL PASS" — a definite negative for a run that had not finished. These logs carry no
    # distinct failure marker, so "incomplete" and "failed" are indistinguishable by content;
    # the only honest move is to scan back to the newest COMPLETED run and report how many
    # newer, unfinished ones were skipped. Silently preferring an older green would hide a suite
    # that dies halfway every time, so the count travels with the answer.
    incomplete = []
    for name in reversed(logs):
        try:
            tail = open(os.path.join(d, name), errors="replace").read()[-4000:]
        except Exception as e:
            return {"unknown": True, "why": f"could not read {name}: {e}"}
        if "ALL PASS" not in tail:
            incomplete.append(name)
            continue
        stamp = name.split("_")[0]
        ts = _parse_utc(f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:"
                        f"{stamp[13:15]}Z")
        return {"unknown": False, "suite": suite, "log": name, "ts": ts,
                "utc": _utc(ts) if ts else None, "green": True,
                "n_newer_without_terminal_marker": len(incomplete),
                "newer_incomplete": incomplete[:3]}
    return {"unknown": True, "why": f"{suite}: no completed run found among {len(logs)} log(s) — "
                                    f"every one lacks a terminal marker (in flight, or dying "
                                    f"before the end)"}


def latest_log_hit(repo: str, logpath: str, match: str) -> Dict[str, Any]:
    """Newest line of `logpath` containing `match`, with its leading ISO timestamp.

    ★ THE THIRD EVIDENCE CLASS (team-lead, 2026-07-26): suites are not the only thing that runs
    at HEAD — so does production. A function with no suite can still be pinned by a log line its
    own execution produced, PROVIDED the line postdates the function's last change.

    ★ AND THE LIMIT THAT TRAVELS WITH IT: a production log line is EXECUTION evidence. It says
    the code ran and returned; it says nothing about whether what it returned is CORRECT. Suites
    and parity fixtures speak to correctness; log lines do not. Folding the two together would
    silently upgrade "it ran" into "it works" — so `proves` is mandatory and `residual` exists to
    keep the correctness gap visible after the cell turns green.

    Re-derived from the log on every run rather than hand-entered: a timestamp typed into the
    ledger is stale the moment it is typed, which is the exact failure this whole mechanism
    exists to catch."""
    p = os.path.join(os.path.expanduser(repo), logpath)
    if not os.path.exists(p):
        return {"unknown": True, "why": f"log not found: {logpath}"}
    newest, n = None, 0
    try:
        with open(p, errors="replace") as fh:
            for ln in fh:
                if match in ln:
                    n += 1
                    newest = ln
    except Exception as e:
        return {"unknown": True, "why": f"could not read {logpath}: {e}"}
    if newest is None:
        return {"unknown": True, "why": f"no line matching {match!r} in {logpath}"}
    ts = _parse_utc(newest[:20].strip())
    if ts is None:
        return {"unknown": True, "why": f"matched line has no parseable leading timestamp: "
                                        f"{newest[:40]!r}"}
    return {"unknown": False, "ts": ts, "utc": _utc(ts), "n_hits": n, "log": logpath}


def _gap(res) -> str:
    """residual may be a bare string (legacy) or the full object; only the gap text belongs in
    a one-line `why`. Printing the whole dict there buried the sentence inside its own metadata."""
    return (res or {}).get("gap", "") if isinstance(res, dict) else str(res or "")


def _probe(repo: str, probe: Dict[str, Any]) -> Dict[str, Any]:
    """Is this residual's closure condition satisfied RIGHT NOW?

    ★ team-lead, 2026-07-26: a residual that is only displayed is one more list nobody returns
    to. So each one carries a DECIDABLE closure condition, and where the condition is mechanical
    the tool checks it every run — the item then closes itself and says so, instead of waiting
    for someone to remember it exists."""
    import glob as _glob
    import re as _re
    pat, g = probe.get("pattern"), probe.get("glob")
    if not pat or not g:
        return {"unknown": True, "why": "probe needs both `glob` and `pattern`"}
    files = sorted(_glob.glob(os.path.join(os.path.expanduser(repo), g)))
    if not files:
        # ★ ZERO FILES IS NOT ZERO MATCHES. glob returns [] for "the path does not exist" and the
        # scan returns [] for "it exists and nothing matched" — folding them gave a definite
        # `satisfied: False` for a file that may have been renamed or never existed. Conservative
        # in DIRECTION (the item stays open), wrong in STATE, and this tool exists to refuse
        # exactly that trade. Caught by probing a deliberately absent path.
        return {"unknown": True, "why": f"glob {g!r} matched no file under the repo — "
                                        f"cannot distinguish 'absent' from 'present and unmatched'"}
    hits = []
    for f in files:
        try:
            for i, ln in enumerate(open(f, errors="replace"), 1):
                if _re.search(pat, ln):
                    hits.append(f"{os.path.relpath(f, os.path.expanduser(repo))}:{i}")
        except Exception:
            continue
    return {"unknown": False, "satisfied": bool(hits), "hits": hits[:5], "n_hits": len(hits)}


def staleness(cur: Dict[str, Any], evidence: Dict[str, Any], repo: str = "") -> Dict[str, Any]:
    """Compare each recorded verdict's `evidence_utc` against its function's last-touch commit.

    ★ The default when anything is missing is UNKNOWN, never OK. Three separate outcomes, because
    they call for three different actions and collapsing them would hide the third:
      FRESH        evidence postdates the last change to that function.
      STALE        the function changed AFTER the evidence was taken -> verdict auto-downgraded.
      UNDETERMINED the function's age could not be established (uncommitted / untracked / no git).
    Plus two bookkeeping outcomes that are about the EVIDENCE FILE rather than the code:
      NO_EVIDENCE  a function in the timeline that no verdict covers  (= an unfilled cell).
      ORPHAN       a verdict for a function no longer in the timeline (= a row about dead code).
    """
    funcs = cur.get("functions", {})
    rows, orphan = [], []
    for fid, rec in sorted(evidence.get("verdicts", {}).items()):
        ev = _parse_utc(str(rec.get("evidence_utc", "")))
        channels: List[str] = []
        touch = funcs.get(fid)
        if touch is None:
            orphan.append({"function": fid, "verdict": rec.get("verdict"),
                           "why": "no longer appears in the derived timeline — deleted, renamed, "
                                  "or moved behind an unresolved call site"})
            continue
        if ev is None:
            out, why = "UNDETERMINED", "evidence_utc missing or unparseable"
        elif touch.get("unknown"):
            out, why = "UNDETERMINED", touch.get("why", "function age unknown")
        elif touch["ts"] > ev:
            out, why = "STALE", (f"function changed at {touch['utc']} ({touch['sha']}) — "
                                 f"{(touch['ts'] - ev) / 60:.0f} min AFTER the evidence")
            # ★ RE-PINNING (team-lead, 2026-07-26). When the evidence is the TAIL of a chain
            # whose HEAD link is re-run continuously, a change to the pilot-side function does
            # not invalidate the tail — provided a suite that actually covers it went green
            # AFTER the change. Then the code is re-pinned to the same reference the tail was
            # taken against, and the correct outcome is RE-PINNED, not STALE.
            #
            # ★ TWO THINGS THIS DELIBERATELY REFUSES TO DO:
            #  - It does NOT move `evidence_utc` forward to the suite run. A conjunctive chain is
            #    as stale as its STALEST link; dating it by its freshest one is how a frozen
            #    middle link (here: the fixture, and the upstream that produced it) disappears
            #    from view. The tail keeps its own date; the suite only neutralises head-side
            #    churn. See `chain` in the evidence file for the middle link's own audit.
            #  - It does NOT accept `pinned_by` without `pins`. "A suite covers it" is not a
            #    fact until someone says WHAT it pins: `refresh_preds` is exercised only on its
            #    three refusal paths, so its success path is not re-pinned by that green run.
            pin = rec.get("pinned_by")
            if pin:
                s, what = pin.get("suite"), pin.get("pins")
                run = last_green_suite_run(repo or cur.get("repo", ""), s) if s else {"unknown": True,
                        "why": "pinned_by has no `suite`"}
                if not what:
                    out, why = "STALE", (why + " | pinned_by present but `pins` missing — a suite "
                                                "name alone does not say what it pins")
                elif run.get("unknown"):
                    out, why = "STALE", why + f" | pinning suite unusable: {run.get('why')}"
                elif not run.get("green"):
                    out, why = "STALE", why + f" | {s} last completed run {run['utc']} not green"
                elif run["ts"] < touch["ts"]:
                    out, why = "STALE", (why + f" | {s} last green {run['utc']} PREDATES the "
                                               f"change — the suite is behind the code")
                else:
                    out = "RE-PINNED"
                    channels.append("suite")
                    _inc = run.get("n_newer_without_terminal_marker") or 0
                    why = (f"changed at {touch['utc']} ({touch['sha']}), but {s} went green at "
                           f"{run['utc']} after it — pins: {what}"
                           + (f" | ⚠ {_inc} 次更新的运行没有终止标记 (在途或中途死亡), "
                              f"本判定用的是它们之前那次完成的运行" if _inc else ""))
            # ★ THIRD CHANNEL, AND IT IS ADDITIVE, NOT A FALLBACK. `refresh_preds` is the case
            # that forced this: the suite pins its three REFUSAL paths and production pins its
            # SUCCESS path — complementary halves of one function. Stopping at the first channel
            # that clears the cell would report "re-pinned by suite" and silently drop the fact
            # that the other half is now covered too. A cell can be pinned by both; the ledger
            # has to be able to say so, because "which half" is the whole content of `pins`.
            obs = rec.get("observed_in_production")
            if obs:
                hit = latest_log_hit(repo or cur.get("repo", ""), obs.get("log", ""),
                                     obs.get("match", ""))
                if not obs.get("proves"):
                    _p = "observed_in_production present but `proves` missing"
                elif hit.get("unknown"):
                    _p = f"production evidence unusable: {hit.get('why')}"
                elif hit["ts"] < touch["ts"]:
                    _p = f"newest matching log line {hit['utc']} PREDATES the change"
                else:
                    _p = None
                    channels.append("production_log")
                    _w = (f"production emitted {hit['n_hits']} line(s), newest {hit['utc']}, "
                          f"after the change — proves: {obs['proves']}"
                          + (f" | 残余: {_gap(obs.get('residual'))}" if obs.get("residual") else ""))
                    why = (f"{why} || {_w}") if out == "RE-PINNED" else (
                        f"changed at {touch['utc']} ({touch['sha']}), but {_w}")
                    out = "RE-PINNED"
                if _p and out != "RE-PINNED":
                    out, why = "STALE", why + " | " + _p
        else:
            out, why = "FRESH", f"unchanged since {touch['utc']} ({touch['sha']})"
        rows.append({"function": fid, "recorded_verdict": rec.get("verdict"),
                     "evidence_utc": rec.get("evidence_utc"), "outcome": out, "why": why,
                     "repin_channels": channels or None, "pinned_by": rec.get("pinned_by"),
                     "observed_in_production": rec.get("observed_in_production"),
                     # ★ the downgrade is APPLIED here, not left as advice
                     "effective_verdict": (rec.get("verdict")
                                           if out in ("FRESH", "RE-PINNED") else "UNKNOWN"),
                     "note": rec.get("note", "")})
    # ── residual -> OPEN ITEMS ──────────────────────────────────────────────────────────────
    # ★ A residual does NOT downgrade the verdict: staleness and incompleteness are two
    # dimensions, and folding them into one state is the exact merge this project spent a night
    # pulling apart. They get their OWN counter and their OWN list instead.
    open_items, n_resid, n_unclosable = [], 0, 0
    for r in rows:
        for src_key in ("pinned_by", "observed_in_production"):
            src = r.get(src_key) or {}
            res = src.get("residual")
            if not res or res in ("无", "none", "None"):
                continue
            n_resid += 1
            if isinstance(res, str):
                res = {"gap": res}
            item = {"function": r["function"], "from": src_key, "gap": res.get("gap"),
                    "owner": res.get("owner") or "UNASSIGNED",
                    "closes_when": res.get("closes_when"),
                    "verdict_kept": r["effective_verdict"]}
            if not res.get("closes_when"):
                n_unclosable += 1
                item["★"] = ("residual with no decidable closure condition — it cannot be "
                             "tracked, only re-read")
            pr = res.get("closes_when_probe")
            if pr:
                item["probe"] = _probe(repo or cur.get("repo", ""), pr)
            # ★ TWO SUPERVISORS, AND THEIR DISAGREEMENT IS THE SIGNAL (team-lead, 2026-07-26).
            # The same item is watched from both ends: the owning repo's OPEN_ITEMS.md reports how
            # long it has been open; this probe reports when it may be closed. Neither can see the
            # other's failure — so the ledger also checks that the item ACTUALLY LANDED over
            # there. An item that lives only here means the routing was lost in transit, which is
            # invisible from both supervisors individually and is exactly what a hand-off drops.
            tr = res.get("tracked_in")
            if tr:
                item["tracked"] = _probe(repo or cur.get("repo", ""),
                                         {"glob": tr.get("file", ""), "pattern": tr.get("pattern")})
                item["tracked_in"] = tr.get("file")
            open_items.append(item)

    covered = {r["function"] for r in rows} | {o["function"] for o in orphan}
    no_ev = sorted(set(funcs) - covered)
    return {"rows": rows, "orphan_verdicts": orphan, "functions_without_verdict": no_ev,
            "n_stale": sum(1 for r in rows if r["outcome"] == "STALE"),
            "n_repinned": sum(1 for r in rows if r["outcome"] == "RE-PINNED"),
            "n_repinned_by_suite": sum(1 for r in rows if "suite" in (r.get("repin_channels") or [])),
            "n_repinned_by_production": sum(1 for r in rows
                                            if "production_log" in (r.get("repin_channels") or [])),
            "n_undetermined": sum(1 for r in rows if r["outcome"] == "UNDETERMINED"),
            "n_fresh": sum(1 for r in rows if r["outcome"] == "FRESH"),
            "n_orphan": len(orphan), "n_without_verdict": len(no_ev),
            "open_items": open_items, "n_residual": n_resid,
            "n_residual_without_closure": n_unclosable,
            "n_residual_now_satisfied": sum(1 for i in open_items
                                            if (i.get("probe") or {}).get("satisfied")),
            "n_residual_not_tracked_elsewhere": sum(
                1 for i in open_items
                if "satisfied" in (i.get("tracked") or {}) and not i["tracked"]["satisfied"]),
            "rule": "evidence_utc < func_last_commit.ts => UNKNOWN, UNLESS a covering suite went "
                    "green after the change (RE-PINNED). The suite never advances evidence_utc: a "
                    "chain is as stale as its stalest link, and the frozen middle link is audited "
                    "separately (see `chain` in the evidence file)."}


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
    ap.add_argument("--evidence", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                       "anchor_coverage_evidence.json"))
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

    # ── 陈旧性审计 (第十形态) ────────────────────────────────────────────────────────────────
    print(f"\n{'='*78}\n陈旧性审计 —— 规则: 证据时刻 < 该函数最后改动时刻 ⇒ 该格自动降为 UNKNOWN")
    if cur["working_tree_dirty"]:
        print(f"  ⚠ 工作区有未提交改动 {len(cur['working_tree_dirty'])} 处 ⇒ 其中的函数一律 "
              f"UNDETERMINED (git 历史看不见工作区)")
    if cur["n_functions_unknown_age"]:
        print(f"  ⚠ {cur['n_functions_unknown_age']}/{cur['n_functions']} 个函数的年龄无法确定")
    if os.path.exists(a.evidence):
        ev = json.load(open(a.evidence))
        st = staleness(cur, ev, repo=a.repo)
        cur["staleness_audit"] = st
        # ★ 汇总行是这张表的嘴。缺口在格子里可见、在头条里不可见 = 正门挂牌侧门没挂。
        print(f"  证据格 {len(st['rows'])}: FRESH {st['n_fresh']} / "
              f"RE-PINNED {st['n_repinned']} (**{st['n_residual']} 带 residual**) / "
              f"**STALE {st['n_stale']}** / UNDETERMINED {st['n_undetermined']}; "
              f"孤儿格 {st['n_orphan']}; 无证据的函数 {st['n_without_verdict']}")
        for r in st["rows"]:
            if r["outcome"] == "RE-PINNED":
                print(f"    RE-PINNED[{'+'.join(c[:4] for c in (r.get('repin_channels') or ['?']))}] "
                      f"{r['function']:44s} {r['recorded_verdict']} (保留)")
                print(f"      {r['why']}")
        for r in st["rows"]:
            if r["outcome"] not in ("FRESH", "RE-PINNED"):
                print(f"  {'★' if r['outcome']=='STALE' else ' '} {r['outcome']:13s} "
                      f"{r['function']:44s} {r['recorded_verdict']} -> {r['effective_verdict']}")
                print(f"      {r['why']}")
        for o in st["orphan_verdicts"]:
            print(f"    ORPHAN        {o['function']:44s} {o['why']}")
        if st["open_items"]:
            print(f"\n  ── OPEN ITEMS ({st['n_residual']}) —— residual 不降级判定, 但必须有归属"
                  f"与可判定的闭合条件")
            for i in st["open_items"]:
                pr = i.get("probe") or {}
                mark = ("★闭合条件现已满足, 请复核后移除" if pr.get("satisfied") else
                        ("探针未匹配 — 仍开着" if "satisfied" in pr else ""))
                tk = i.get("tracked") or {}
                if "satisfied" in tk and not tk["satisfied"]:
                    mark += "  ⚠**尚未出现在 " + str(i.get("tracked_in")) + " —— 派工可能在途中丢失**"
                print(f"   [{i['owner']}] {i['function']} ({i['verdict_kept']} 保留) {mark}")
                print(f"       缺口: {i['gap'][:150]}")
                print(f"       闭合: {i['closes_when'] or '★未写 —— 不可跟踪, 只能被重读'}")
                if pr.get("hits"):
                    print(f"       探针命中: {', '.join(pr['hits'])}")
            if st["n_residual_without_closure"]:
                print(f"   ⚠ {st['n_residual_without_closure']} 条 residual 没有可判定的闭合条件")
        if st["n_without_verdict"]:
            print(f"    (另有 {st['n_without_verdict']} 个函数在时序表里但没有任何证据格 —— "
                  f"那是**未填的格**, 不是'已确认无人碰过')")
    else:
        # ★ 没有证据文件时不能静默通过 —— 那正是这条检查要防的形状
        print(f"  ⚠ 未找到证据文件 {a.evidence} ⇒ 全部 {cur['n_functions']} 个函数 UNKNOWN。"
              f"缺席不产生绿灯。")
        cur["staleness_audit"] = {"error": "evidence file absent — all verdicts UNKNOWN",
                                  "path": a.evidence}

    json.dump(cur, open(a.json, "w"), indent=1, ensure_ascii=False)
    print(f"\n-> {a.json}")
