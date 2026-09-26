#!/usr/bin/env python3
"""Red control for producer_services.ready (E-0926-B): the 2026-09-26 09:00:15Z race state — new pid already in shadow.lock, loop.out's
last line still the OLD process's 'next' line — must NOT be ready (rev 0 released it). Pure function; nothing is started or stopped."""
import importlib.util, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
s = importlib.util.spec_from_file_location("ps", os.path.join(HERE, "producer_services.py")); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
A = 1790413210
cases = [("BASELINE: fresh 'next' line written after --after, lock == new pid ⇒ ready", (23543, "23543", "next 2026-09-26T12:12:00+00:00 in 11502s", A + 7, A), True),
         ("RED CONTROL (the 09:00Z race): new pid in the lock, last line = the OLD process's 'next' line written before --after ⇒ must WAIT", (23543, "23543", "next 2026-09-26T12:12:00+00:00 in 14368s", A - 3600, A), False),
         ("lock still names the old pid", (23543, "70541", "next x", A + 7, A), False),
         ("no pid yet", (None, "", "next x", A + 7, A), False),
         ("last line not a 'next' line (e.g. a traceback) ⇒ not ready", (23543, "23543", "Traceback (most recent call last):", A + 7, A), False),
         ("loop.out missing ⇒ not ready", (23543, "23543", "", None, A), False)]
bad = 0
for name, args, exp in cases:
    got = m.ready(*args); ok = got == exp; bad += not ok
    print(f"  {'OK  ' if ok else 'FAIL'}  {name} -> {got}")
rc0 = m.ready.__doc__ and "rev 1" in m.ready.__doc__
print(f"{len(cases) - bad}/{len(cases)} checks passed")
print("READY_SELFTEST " + ("ALL GREEN" if not bad else f"RED {bad}"))
sys.exit(1 if bad else 0)
