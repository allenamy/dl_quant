"""Every module on the production path must IMPORT. That is the whole test.

★ WHY IT EARNS A SUITE OF ITS OWN
A "path portability" refactor moved `MA = ...` below its first use in three modules of the daily
shadow chain; each raised `NameError` at import time, `run_daily.sh` aborts on the first failure,
and the failing module was step 1 — so the entire chain would have died the next morning. Six
acceptance suites were green, because they exercise FUNCTIONS and none of them ever loaded those
top levels.

    "the component is correct"  ≠  "the component can be loaded"

This bug needed no domain knowledge whatsoever. It needed someone to try importing the file once.
Cost here: milliseconds. Cost of missing it: one dead scheduled run per module, discovered by
absence.

★ It is deliberately dumb. It asserts nothing about behaviour — behaviour is what the other
suites are for. Adding cleverness here would let it fail for reasons that are not "this file
cannot be loaded", which is the one thing it exists to detect.
"""
from __future__ import annotations

import importlib
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for d in ("live", "signal", "scheduler", "ops", "vendor"):
    sys.path.insert(0, os.path.join(REPO, d))

# Every module reachable from the scheduled entry point, plus the ops tools it invokes.
PRODUCTION_MODULES = [
    # entry point and loop
    "run_anchor", "anchor_loop",
    # execution stack
    "binance_broker", "binance_executor", "venue_fills", "venue_error_codes",
    "watchdog", "watchdog_inputs", "pilot_log", "pilot_metrics", "telegram_notify",
    "per_name_stop",  # 逐名止损条款 cf40ea21(2026-08-20 全面启用)
    "external_book",  # 外部书适配器 (DESIGN_wide_live_deployment_2026-08-22 §1): anchor_loop imports it
    "universe", "state_root", "book_config", "rate_budget", "binance_funding",
    # `reduce_only_reject` joined 2026-08-01: resolves a -2022 against the position readback.
    # The drift assertion named it before I did — fifth time.
    "reduce_only_reject",
    # `order_disposition` joined 2026-08-02: the terminal-state matrix and the known-gap
    # ledger. Sixth time the drift assertion named a module before a human did.
    "order_disposition",
    # `alarm_policy` joined 2026-08-02: owns the alarm rules table; telegram_notify consults it.
    "alarm_policy",
    # `chase_policy` joined 2026-08-03: the neutrality fill rule and the chase experiment's arm
    # assignment. SEVENTH time the drift assertion named a module before a human did — and this
    # one matters more than most, because `topup()` imports it inside a try/except: an import
    # failure would leave `_chase_experiment` None and every name chased, i.e. the experiment
    # would silently not exist while the anchor stayed green. This census is what makes that
    # loud.
    "chase_policy",
    # `placement_bandit` joined 2026-08-12 (PREREG f657efde): ε-bandit arm assignment + tick-grid
    # shift. Fifth time this census named a module before a human did.
    "placement_bandit",
    # `rebalance_id` joined 2026-07-27 (§2.5.9): the ONE rehearsal predicate + the id minter.
    # Added because THIS check went red on it, which is the fourth time the drift assertion has
    # named a module before a human did.
    # `frozen_inputs` joined 2026-07-28 (B27) — and again this check named it before a human did,
    # which is now the fifth time. The census is on the production path because the anchor blocks
    # on it, so a module that fails to import would disarm a blocking guard silently.
    "rebalance_id", "universe_guard", "frozen_inputs",
    # ★ `rate_budget` and `regime_classifier` were reachable from run_anchor for as long as they
    # have existed and were never on this list — found by the drift check below on its first run,
    # not by anyone reading the file. `binance_funding` joined them the same night. Three modules
    # whose loadability the "every module on the production path must import" suite was not
    # actually checking, in a suite whose entire purpose is that check.
    # signal stack
    "fapi_source", "panel_build", "funding_panel", "assert_funding_dim", "live_panel",
    "inference", "legs", "compute_preds", "regime_classifier",
    # ops invoked by the anchor
    "assert_anchor_artifacts", "check_factor_health", "dryrun_ledger", "check_nosleep",
    "check_scheduled_mode", "gate_coverage", "check_prewindow_state",
    # ★ `guard_reach` joined 2026-08-03 — the guards' REACH census (what each cannot stop). Like
    #   `gate_coverage` beside it, the anchor does not call it; it is import-reachable and it is
    #   listed for the same reason the two neighbours are: **a census that fails to import is a
    #   census that does not run**, and its silence is indistinguishable from a clean pass. Eighth
    #   time this drift check has named a module before a human did.
    "guard_reach",
    # ★ `income_callers` joined 2026-08-03 — the /fapi/v1/income caller census. Same reason as
    #   its two neighbours: a census that fails to import is a census that does not run, and its
    #   silence is indistinguishable from a clean pass. Ninth time this drift check has named a
    #   module before a human did.
    "income_callers",
    "check_funding_span", "check_metrics_freeze", "alarm_episode", "reconcile", "backfill_markout",
    # §4-5e producer: the direct position-break measurement, wired BESIDE §4-5b (never instead
    # of it). A module that failed to import would disarm a halt-level gate silently.
    "position_break",
    # ★ reachable from run_anchor via position_break: the flat-intent gate READS the
    #   human-written ack file through it. It is production-reachable and write-free —
    #   only ops/ack_stuck_position.py's __main__ writes, and nothing on this path calls
    #   that. This guard caught the addition on its first run, which is what it is for.
    "ack_stuck_position",
    # ★ invoked BY install_launchd.sh (three times: delta, --n-symbols, --preflight),
    #   so the graph walker finds it through the script-invocation scan, not through
    #   an import. Read-only: it prints and fingerprints, and writes nothing.
    "live_install_delta",
    # ★ THE FOUR BELOW WERE INVISIBLE UNTIL OPERATOR_SCRIPTS STOPPED BEING HAND-TYPED, and two
    #   of them are not new: `check_upstream_drift` (run_acceptance.sh) and `red_capability` have
    #   been invoked by scripts outside the old four-entry scope for as long as those scripts have
    #   existed. The guard could not see them, and nothing said so — the blind spot and a clean
    #   report were the same output.
    "check_upstream_drift",
    "red_capability",
    "setup_live_account",       # ops/live_dry_pass.sh, read-only unless --apply
    "live_readiness_sheet",     # ops/live_dry_pass.sh, read-only
    "redeliver_alarms",         # run_anchor, one retry pass per anchor
    # B34: the clock-start step that asks whether §4-3 can see its own input
    "check_markout_readiness",
    # ★ named by ops/live_dry_pass.sh (the route it writes into the seeded halt) and by
    #   ops/resume_from_trip.sh (which refuses a seeded halt and hands it over), so the
    #   script-invocation scan reaches it. THE LOADABILITY CHECK IS THE POINT HERE, not the
    #   bookkeeping: it is the only way out of a first-day LIVE tree, so a module that failed to
    #   import would leave the halt unclearable by either tool — and it is reached exactly when
    #   someone is already trying to get unstuck. Import-time it is constants only; it writes
    #   nothing unless __main__ is given an operator and a reason.
    "unseed_rehearsal_halt",
    # ★ reached from the anchor through binance_executor's cancel path: it is where an order the
    #   venue would not let us cancel gets written down. An import failure there would be silent
    #   in the worst way — the cancel path already has an `except` around the pin write, so a
    #   broken module would degrade into "recorded nowhere" at exactly the moment a live maker
    #   order is sitting on the book.
    "stuck_orders",
    # ★ the shared `.env` loader. Reached at module load by run_anchor and by every ops tool
    #   that can page; an import failure there would take the alarm channel down at the one
    #   moment it is used — the loader's whole reason for existing is a page that was
    #   composed and never sent.
    "envfile",
    # ★ named by ops/live_dry_pass.sh, so the script-invocation scan reaches it. Tiny and
    #   read-only: it prints one rebalance_id. Its loadability matters because a failure
    #   there makes the sheet UNSCOPED, and an unscoped sheet is the defect it exists to fix.
    "_sheet_subject",
]

fails = []
print(f"[IMP] loading {len(PRODUCTION_MODULES)} production modules")
for name in PRODUCTION_MODULES:
    try:
        importlib.import_module(name)
        print(f"  OK   {name}")
    except Exception as e:
        fails.append(name)
        print(f"  FAIL {name} — {type(e).__name__}: {e}")
        traceback.print_exc()

# ────────────────────────────────────────────────────────────────────────────────────────────────
# ★★ THE LIST MUST NOT DRIFT FROM THE CODE, AND A HAND-WRITTEN LIST ALWAYS DOES.
#
# Everything above tests that the modules NAMED HERE can be loaded. It says nothing about whether
# the names here are the modules the entry point actually reaches — and the list is maintained by
# hand, so the failure mode is silent by construction: a new production module is simply absent,
# its import is never attempted, and the suite stays green while reporting a smaller number.
# It happened while this very block was being written: `binance_funding` became a production
# module at 02:2xZ (run_anchor step 5c) and the list did not mention it. Nothing went red.
#
# ⇒ The set is DERIVED: walk the import graph from the scheduled entry point, keep every module
#   whose file lives in this repo's source directories, and require the two sets to be equal.
#   Reachability from the entry point is what "production module" MEANS; the list is a cache of
#   that, and a cache with no invalidation is a stale answer waiting to be believed.
import ast                                                                     # noqa: E402

SRC_DIRS = ("live", "signal", "scheduler", "ops")
ENTRY_POINTS = [os.path.join(REPO, "scheduler", "run_anchor.py")]

# ★ THE OPERATOR SCRIPTS ARE NAMED, AND `run_acceptance.sh` IS DELIBERATELY NOT AMONG THEM.
# Globbing every *.sh pulled in the whole test battery — 15 `tests_*` modules reported as
# "production modules never import-checked", which is backwards: they are the checkers. The
# boundary is not "which files are shell scripts" but "which scripts LAUNCH OR INSTALL THE
# RUNNING SYSTEM". A hand-written list reappears here, one level up — but a list of four
# launchers is a far more stable thing to maintain than a list of thirty modules, and a new
# launcher is a deliberate act by a person, whereas a new module is a side effect of any edit.
# ★★★ DERIVED, NOT TYPED (2026-07-30). This was a hand-written tuple of four scripts, and on the
# day `ops/live_dry_pass.sh` was added it silently invoked `setup_live_account.py` without the
# graph noticing — I had predicted the guard would demand that module be listed, and it did not.
# **The file list was computed by grep and the SEARCH SCOPE was typed by hand**, which is the
# same defect this repo already paid for once in a census: zero hits outside the typed scope is a
# FACT about where you looked, never a guarantee about the repo.
# ⇒ Every shell script in the tree is scanned. A new operator script is covered the day it exists,
#   and adding one can now only make the guard STRICTER, never blinder.
def _operator_scripts():
    out = []
    for d in ("ops", ""):
        base = os.path.join(REPO, d) if d else REPO
        if not os.path.isdir(base):
            continue
        for f in sorted(os.listdir(base)):
            if f.endswith(".sh"):
                out.append(os.path.join(d, f) if d else f)
    return tuple(out)


OPERATOR_SCRIPTS = _operator_scripts()


def _module_file(name: str):
    for d in SRC_DIRS:
        p = os.path.join(REPO, d, f"{name}.py")
        if os.path.exists(p):
            return p
    return None


def _imports_in(path: str):
    """Every module name imported by this file, INCLUDING inside functions and try blocks.

    A top-level-only scan would miss exactly the imports this repo uses for its optional and
    late-bound components — `import binance_funding as BF` sits inside a try inside main(), which
    is where a wiring omission lives.
    """
    try:
        tree = ast.parse(open(path).read())
    except Exception:
        return set()
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.add(node.module.split(".")[0])
    return out


def _script_invocations():
    """Modules the repo's SHELL scripts run as programs.

    ★ THE SECOND MECHANISM, AND WITHOUT IT THE ASSERTION ACCUSES HEALTHY CODE. The first version
    of this block reported `gate_coverage`, `check_scheduled_mode` and `check_prewindow_state` as
    "listed by hand but unreachable" — all three are real production tools, invoked as
    `python3 ops/<name>.py` from run_acceptance.sh / install_launchd.sh / start_dryrun_clock.sh.
    An import graph cannot see a subprocess. A drift check that flags correct code as drift gets
    an exemption bolted onto it within a week, so the fix is to model the second mechanism rather
    than to widen the tolerance.
    """
    import re as _re
    out = set()
    for sh in OPERATOR_SCRIPTS:
        try:
            txt = open(os.path.join(REPO, sh)).read()
        except Exception:
            continue
        for m in _re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\.py\b", txt):
            out.add(m.group(1))
        # embedded python heredocs import the same tools by name
        for m in _re.finditer(r"^\s*import\s+([a-z_][a-z0-9_]*)", txt, _re.M):
            out.add(m.group(1))
    # ★ A TEST SUITE IS NOT A PRODUCTION MODULE, WHOEVER INVOKES IT. Widening the script scan to
    #   every .sh pulled in run_acceptance.sh, which names all 69 suites — so the first run of the
    #   derived version accused every test in the repo of being undeclared production code. The
    #   filter is a PROPERTY of the module (its name says what it is), not another hand-typed
    #   exemption list: an exemption list would need an entry per suite and would go stale by one
    #   every time a suite is added, which is the failure this whole change is undoing.
    return {n for n in out if _module_file(n) and not n.startswith("tests_")}


# the entry points are production modules by definition; nothing imports them, they ARE the root
derived = {os.path.splitext(os.path.basename(p))[0] for p in ENTRY_POINTS}
derived |= _script_invocations()
queue = list(ENTRY_POINTS) + [p for p in (_module_file(n) for n in derived) if p]
seen_files = set()
while queue:
    f = queue.pop()
    if f in seen_files:
        continue
    seen_files.add(f)
    for name in _imports_in(f):
        p = _module_file(name)
        if p and name not in derived:
            derived.add(name)
            queue.append(p)

hand = set(PRODUCTION_MODULES)
missing_from_list = sorted(derived - hand)      # reachable from the entry point, never imported here
absent_from_code = sorted(hand - derived)       # named here, not reachable — dead or reached elsewhere
print(f"\n[DRIFT] import graph from {len(ENTRY_POINTS)} entry point(s): "
      f"{len(derived)} modules reachable, {len(hand)} listed by hand")
if missing_from_list:
    print(f"  FAIL ★ reachable from run_anchor but NOT in PRODUCTION_MODULES: {missing_from_list}"
          f"\n       (these are production modules whose loadability is never checked — the exact"
          f"\n        silence this suite exists to break)")
    fails.extend(missing_from_list)
if absent_from_code:
    print(f"  FAIL ★ listed by hand but NOT reachable from run_anchor: {absent_from_code}"
          f"\n       (either dead code still being vouched for, or reached by a path this walk"
          f"\n        does not know about — both mean the list has stopped describing the system)")
    fails.extend(absent_from_code)
if not missing_from_list and not absent_from_code:
    print("  OK   the hand-written list and the import graph agree exactly")

# ────────────────────────────────────────────────────────────────────────────────────────────────
# ★ THE SAME DRIFT CHECK, ONE SUBJECT OVER: docs/API_SEMANTICS.md vs the endpoints in the code.
# That document ends with a sentence admitting its own weakest point — "the endpoint set was
# obtained by one grep, and the mechanism keeping it in sync with the code is THIS SENTENCE".
# A sentence does not go red. Same reasoning as PRODUCTION_MODULES above, same fix: derive the set
# and require the document to contain every member. It is deliberately ONE-DIRECTIONAL — the doc
# may mention endpoints the code does not call (§3 is a list of things we deliberately do NOT
# use, and that section is the most valuable one), but an endpoint we CALL and never wrote down
# is a semantic we never stated.
import re as _re                                                               # noqa: E402

API_DOC = os.path.join(REPO, "docs", "API_SEMANTICS.md")
_eps = set()
for _d in ("live", "signal", "scheduler", "ops"):
    _dir = os.path.join(REPO, _d)
    if not os.path.isdir(_dir):
        continue
    for _f in os.listdir(_dir):
        if not _f.endswith(".py") or _f.startswith("tests_"):
            continue
        try:
            _eps |= set(_re.findall(r'"(/fapi/v[0-9]/[A-Za-z/]+)"',
                                    open(os.path.join(_dir, _f)).read()))
        except Exception:
            continue
print(f"\n[API] {len(_eps)} fapi endpoint(s) referenced in code")
if not os.path.exists(API_DOC):
    print(f"  FAIL docs/API_SEMANTICS.md is missing — the endpoint semantics are undocumented")
    fails.append("API_SEMANTICS.md missing")
else:
    _doc = open(API_DOC).read()
    _undoc = sorted(e for e in _eps if e.split("/fapi/")[-1].split("/", 1)[-1] not in _doc
                    and e not in _doc)
    if _undoc:
        print(f"  FAIL ★ called in code, absent from docs/API_SEMANTICS.md: {_undoc}"
              f"\n       (an endpoint we call and never wrote down is a semantic we never stated)")
        fails.extend(_undoc)
    else:
        print("  OK   every endpoint the code calls is documented")

print(f"\n  {'ALL PASS' if not fails else 'FAILURES: ' + str(fails)}", flush=True)
sys.exit(0 if not fails else 1)
