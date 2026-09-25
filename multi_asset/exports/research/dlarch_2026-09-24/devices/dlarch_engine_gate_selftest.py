#!/usr/bin/env python3
"""dlarch_engine_gate_selftest.py -- does the engine run gate count OTHER engine groups correctly?

WHY: the gate enforces a shared-resource rule (at most N cells in parallel across all agents). If it
under-counts, I start an over-quota cell and can cause the OOM the rule exists to prevent. fresh
flagged a plausible defect: a `bt_launch` whose argv contains no RUN_CONFIG*.json would be invisible
to an argv-matching counter. That defect is real -- for an argv-matching counter. This selftest proves
which quantity the gate actually keys on, against synthetic `ps` output, so the answer does not rest on
anyone reading the source and believing a claim.

THE THREE CANDIDATE COUNTING METHODS, and what each gives on the same synthetic table:
  count PIDs        -> 5  (one launcher's workers each counted; the gate would never open: starvation)
  match argv .json  -> 1  (the config-less group vanishes: FALSE NEGATIVE, over-quota parallelism)
  count PGIDs       -> 2  (one per launcher, regardless of how its command line is written)  <-- correct
A launcher's workers share its PGID, so "distinct foreign PGIDs" == "distinct foreign engine groups".
The config path is kept only as a LABEL (with an explicit "<config not in argv>" fallback), because
"who is running" is worth reporting even when it cannot be determined.

Read-only: builds a synthetic process table in memory, never inspects or signals real processes.
usage: dlarch_engine_gate_selftest.py <env-whitelist> <dlarch_chain_run.py path>
"""
import importlib.util
import os
import subprocess
import sys


def main():
    wl = set(sys.argv[1].split(","))
    extra = sorted(set(os.environ) - wl)
    assert not extra, f"env outside whitelist: {extra}"
    target = sys.argv[2]

    spec = importlib.util.spec_from_file_location("cr", target)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    mine = os.getpgid(0)

    synth = "\n".join([
        "  PID  PGID COMMAND",
        "  100  100 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE /dev/shm/a/RUN_CONFIG.json --resume x",
        "  101  100 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE /dev/shm/a/RUN_CONFIG.json --resume x",
        "  200  200 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE --resume config_not_in_argv",
        "  201  200 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE --resume config_not_in_argv",
        "  202  200 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE --resume config_not_in_argv",
        f"  300 {mine} /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE /mine/RUN_CONFIG.json",
        "  400  400 /workspace/venv/bin/python -B some_other_tool.py  # not an engine at all",
    ]) + "\n"

    class Res:
        stdout = synth

    real_run = subprocess.run
    subprocess.run = lambda *a, **k: Res()
    try:
        g = m.foreign_engines()
    finally:
        subprocess.run = real_run

    # what the two wrong methods would have given, on the same table
    eng = [l for l in synth.splitlines()[1:] if "bt_launch.py" in l]
    n_pids = len([l for l in eng if int(l.split()[1]) != mine])
    n_argv = len({l.split()[1] for l in eng
                  if int(l.split()[1]) != mine and any(t.endswith(".json") for t in l.split())})

    print(f"synthetic table: 2 foreign launchers (one with 2 workers, one with 3 and NO config in argv),")
    print(f"                 1 launcher of my own (pgid {mine}), 1 non-engine process")
    print(f"gate counted    : {len(g)}   {dict((str(k), v) for k, v in g.items())}")
    print(f"count PIDs would give   : {n_pids}   (starvation: the gate could never open)")
    print(f"match argv .json would  : {n_argv}   (FALSE NEGATIVE: the config-less group vanishes)")
    print(f"count PGIDs (gate)      : {len(g)}   (one per launcher)")

    checks = [
        ("group with a config counted exactly once", 100 in g and len(g) == 2),
        ("group WITHOUT a config in argv IS counted", 200 in g),
        ("its label says so rather than dropping it", g.get(200) == "<config not in argv>"),
        ("my own process group is excluded", mine not in g),
        ("non-engine processes ignored", 400 not in g),
        ("count is GROUPS not PIDs", len(g) == 2 and n_pids == 5),
        ("argv-matching would have under-counted", n_argv < len(g)),
    ]
    ok = True
    for name, val in checks:
        print(f"  {'ok ' if val else '!! '}{name}")
        ok &= bool(val)
    print(f"DLARCH_ENGINE_GATE_SELFTEST={'GREEN' if ok else 'RED'} keyed_on=PGID label_only=config_path")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
