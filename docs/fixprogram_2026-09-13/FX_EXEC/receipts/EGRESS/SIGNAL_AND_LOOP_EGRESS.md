# TEST-01/§8 follow-up: tests_signal_and_loop reaches the venue  2026-09-16T04:46:57Z
# reported by FX-W6C; verified here independently, not accepted on report

## VERIFICATION (dead-proxy control, FX-W6C's method — safe by construction, nothing can leave)
  tests_signal_and_loop   deadproxy rc=1   <- depends on reaching the network
  tests_venue_fills       deadproxy rc=0
  tests_reconcile_carry   deadproxy rc=0
  code path: live/tests_signal_and_loop.py builds real BB.BinanceBroker() and arms them;
             binance_broker.py:1840 GETs /fapi/v1/ticker/bookTicker (weight 5, _WEIGHTS:850)

## HOW MANY REQUESTS (counting listener on 127.0.0.1:8899; accepts and closes, no egress)
  OUTBOUND_CONNECTION_ATTEMPTS = 6 per run
  ★ CAVEAT, STATED: under a proxy that REFUSES, the transport layer retries. So 6 is the
    number of connection ATTEMPTS under refusal, NOT necessarily 6 successful GETs in a
    normal run. It bounds the call sites, not the satisfied requests.
  If all six were bookTicker at weight 5, that is <= 30 weight per run against a 2400/min
  budget whose observed 00Z peak was 847.

## MY OWN EXPOSURE — four out-of-window runs, all today, all before I knew
  03:16:25Z  inside the accidental run_acceptance (already reported; its own log was 25,781 B)
  03:44:17Z  the 137-suite dry battery
  04:16:18Z  the neighbour run after the signal/legs.py wording correction
  04:22:31Z  the aborted state-write sweep
  04:44:37Z  dead-proxy control — NO egress, does not count
  04:47Z     counting-listener run  — NO egress, does not count

## WHY MY OWN RULE DID NOT CATCH IT
After the 03:16Z incident I adopted 'grep each suite for subprocess/bash/os.system/requests
before running it'. That rule finds a suite that SHELLS OUT to the battery. It does not find
a suite that builds a real broker and calls it — no subprocess, no 'requests' module, just
urllib inside our own client. The textual rule was the wrong instrument for the property;
FX-W6C's dead-proxy sweep is a BEHAVIOURAL one and finds the class by construction.
⇒ Same shape as KB-73 (a guard asserting a substring instead of the behaviour) and as EXE-05
  (a cell asserting injected state instead of production reachability). Third instance today.
