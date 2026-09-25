#!/usr/bin/env python3
"""tests_news_fund_replay_guard.py -- the guard in news_fund_replay.py must DISCRIMINATE, not merely refuse.

A deprecation guard that raises on everything passes the obvious test (run it on the defective source, watch
it refuse) while being useless: it would also refuse the fixed source, and nobody would be able to tell the
difference from that one observation. So the load-bearing case here is the FIRST one -- the live producer's
guarded line must PASS. Runs anywhere: news_hist_features is stubbed, since only the pure line-checking
function is under test.

  python3 -B tests_news_fund_replay_guard.py
"""
import importlib.util
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))

# the device imports a pod2-only module at file scope; stub it so the pure function can be tested anywhere
_stub = types.ModuleType("news_hist_features")
_stub.SHADOW_SRC = "/nonexistent"
_stub.SHADOW_SHA = "0" * 64
_stub.W = "/nonexistent"
_stub.sha = lambda p: "0" * 64
sys.modules.setdefault("news_hist_features", _stub)

_spec = importlib.util.spec_from_file_location("nfr", os.path.join(HERE, "news_fund_replay.py"))
NFR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NFR)

# the live producer's form (shadow_loop_v3.py L633-634, sha 52baf979) and the pinned one (L456, 60800739)
GUARDED = ["        exp_iv = led[-1][2] if led else 8.0",
           "        if not _bulk_ok and anchor - last_ts < exp_iv * 3600 * 0.9:   # NC A4: under bulk, never skip",
           "            continue"]
UNGUARDED = ["        exp_iv = led[-1][2] if led else 8.0",
             "        if anchor - last_ts < exp_iv * 3600 * 0.9:",
             "            continue"]
NO_GATE = ["        x = 1", "        y = 2"]


def run():
    fails = 0

    def check(name, fn, want_pass):
        nonlocal fails
        try:
            r = fn()
            got_pass, detail = True, r
        except RuntimeError as e:
            got_pass, detail = False, str(e)[:80]
        ok = got_pass == want_pass
        fails += 0 if ok else 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        print(f"          want={'accept' if want_pass else 'refuse'}  "
              f"got={'accept' if got_pass else 'refuse'}  {detail}")

    os.environ.pop(NFR.ALLOW_ENV, None)
    print("★ the load-bearing case: a guard that refuses EVERYTHING would pass the refusal tests alone")
    check("live producer's GUARDED gate is accepted", lambda: NFR.check_skip_gate_guarded(GUARDED), True)
    check("pinned UNGUARDED gate is refused", lambda: NFR.check_skip_gate_guarded(UNGUARDED), False)
    check("a block with NO recognisable gate is refused (unknown is not permission)",
          lambda: NFR.check_skip_gate_guarded(NO_GATE), False)

    os.environ[NFR.ALLOW_ENV] = "please"
    check("a WRONG token does not open the gate", lambda: NFR.check_skip_gate_guarded(UNGUARDED), False)

    os.environ[NFR.ALLOW_ENV] = NFR.ALLOW_TOKEN
    r = NFR.check_skip_gate_guarded(UNGUARDED)
    ok = (r.get("skip_gate_guarded") is False and r.get("deliberately_allowed") is True)
    fails += 0 if ok else 1
    print(f"  [{'PASS' if ok else 'FAIL'}] the exact token proceeds AND stamps the artifact: {r}")

    # the stamp must record a FALSE guard, or a deliberately defective run would be indistinguishable
    # from a clean one in the npz and the receipt
    g = NFR.check_skip_gate_guarded(GUARDED)
    ok2 = g.get("skip_gate_guarded") is True and "deliberately_allowed" not in g
    fails += 0 if ok2 else 1
    print(f"  [{'PASS' if ok2 else 'FAIL'}] a clean run's stamp is distinguishable from a stamped defective one")
    os.environ.pop(NFR.ALLOW_ENV, None)

    total = 6
    print(f"\ntests_news_fund_replay_guard: {total - fails}/{total} {'ALL PASS' if not fails else 'FAILURES'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
