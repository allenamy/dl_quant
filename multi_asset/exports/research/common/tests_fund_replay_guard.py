#!/usr/bin/env python3
"""tests_fund_replay_guard.py -- the consumer guard must DISCRIMINATE across all four states.

The load-bearing case is CLEAN being ACCEPTED: a guard that refused everything would pass every refusal test
while making the artifact unusable, and only the accept case separates the two. UNSTAMPED must be REFUSED --
treating a missing mark as permission is the exact absent-key-means-pass error the archive manifest gate
carried until R25-11.

  python3 -B tests_fund_replay_guard.py
"""
import json
import os
import shutil
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fund_replay_guard as G


def _mk(d, name, stamp):
    p = os.path.join(d, name)
    kw = dict(anchors=np.arange(3), symbols=np.array(["AUSDT"]))
    if stamp is not None:
        kw["skip_gate_guard"] = np.array(json.dumps(stamp))
    np.savez_compressed(p, **kw)
    return p


def run():
    d = tempfile.mkdtemp(prefix="frg_test_")
    fails = 0
    try:
        cases = [("clean.npz", {"skip_gate_guarded": True}, G.CLEAN, True),
                 ("dirty.npz", {"skip_gate_guarded": False, "deliberately_allowed": True}, G.DEFECTIVE, False),
                 ("nostamp.npz", None, G.UNSTAMPED, False)]
        print("★ the load-bearing case is CLEAN being ACCEPTED; a guard that refuses all would pass the rest")
        for name, stamp, want, should_accept in cases:
            p = _mk(d, name, stamp)
            st = G.fund_replay_status(p)
            try:
                G.require_clean_fund_replay(p)
                accepted = True
            except RuntimeError:
                accepted = False
            ok = (st["state"] == want) and (accepted == should_accept)
            fails += 0 if ok else 1
            print(f"  [{'PASS' if ok else 'FAIL'}] {name:12s} state={st['state']:32s} "
                  f"accepted={accepted} (want {should_accept})")

        st = G.fund_replay_status(os.path.join(d, "absent.npz"))
        ok = st["state"] == G.MISSING
        fails += 0 if ok else 1
        print(f"  [{'PASS' if ok else 'FAIL'}] an absent artifact is named FILE_MISSING, not treated as clean")

        p = _mk(d, "dirty2.npz", {"skip_gate_guarded": False})
        try:
            G.require_clean_fund_replay(p, allow=(G.DEFECTIVE,)); a = True
        except RuntimeError:
            a = False
        try:
            G.require_clean_fund_replay(p, allow=(G.UNSTAMPED,)); b = True
        except RuntimeError:
            b = False
        ok = a and not b
        fails += 0 if ok else 1
        print(f"  [{'PASS' if ok else 'FAIL'}] allow permits ONLY the state it names "
              f"(named={a}, other_state={b})")

        total = 5
        print(f"\ntests_fund_replay_guard: {total - fails}/{total} {'ALL PASS' if not fails else 'FAILURES'}")
        return 1 if fails else 0
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(run())
