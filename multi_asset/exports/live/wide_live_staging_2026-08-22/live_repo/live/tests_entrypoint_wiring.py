"""Production-entry-point wiring: does run_anchor.py actually CALL the protections?

★ WHY THIS SUITE EXISTS
The watchdog was ported, unit-tested, and green for days — while the local entry point never
called it. It appeared only in a docstring line ("6. watchdog evaluate §4 conditions"). Every
existing test invoked watchdog.run() directly, so nothing could see the gap: it was not inside
any component, it was BETWEEN a component and whoever was supposed to call it.

First real invocation failed immediately (collect() returns a 3-tuple, was consumed as a dict) —
a mistake no component test could catch, because both sides were individually correct.

So this suite asserts the CALL, from the production file, by source inspection plus a real run.
A stop-loss nobody invokes is indistinguishable from no stop-loss.
"""
import calendar
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FAILS = 0


def check(name, cond, extra=""):
    global FAILS
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(extra)) if extra else ''}")
    if not cond:
        FAILS += 1
    return cond


src = open(os.path.join(REPO, "scheduler", "run_anchor.py")).read()

print("[A] the entry point references every protection layer")
for name, token in (("watchdog", "WD.run("), ("watchdog inputs", "WI.collect("),
                    ("kill switch (via loop)", "run_anchor"), ("telegram", "TelegramNotifier"),
                    ("phase B top-up", "complete_anchor(")):
    check(f"{name} is CALLED, not merely mentioned", token in src, token)

print("\n[B] a watchdog that cannot evaluate must alarm, never be swallowed")
check("evaluation is wrapped and failure raises a CRITICAL alarm",
      "watchdog FAILED to evaluate" in src and 'alarm("CRITICAL"' in src)

print("\n[C] real run: the entry point executes end to end and the watchdog leaves state")
# ★ opt IN to the fast k window, explicitly and only here. The real window is 900s and the
# certification run must use it — a 1s window measures process lifetime 16x off (lock contention,
# the anchor_max_seconds self-kill, how long a halt survives). This suite only needs the wiring to
# execute end to end. The scheduled path never sets LIVE_FAST_K, so it cannot inherit this.
# ★ AND AN ISOLATED LOCK. This suite runs the production entry point for real; on the production
# lock file, a suite started at :59 would still hold it at :00 and the SCHEDULED anchor would take
# the SKIP branch — §2.5 losing a completion to a test run. It also means acceptance can be run
# while an anchor is in flight without either one corrupting the other's verdict.
_lockdir = tempfile.mkdtemp()
# ★★ AND IT MUST NOT PAGE A HUMAN. This suite runs the production entry point FOR REAL, and
# run_anchor builds a live TelegramNotifier from .env — so every acceptance battery run sent the
# operator's phone whatever that anchor alarmed about. Measured 2026-07-26: 70 alerts in four
# hours, clustered on the exact minutes the battery ran; the user complained twice and the cause
# was THIS FILE, not the system under test. The verification apparatus was the incident.
# ⇒ Suppression is explicit and audited separately (status SUPPRESSED, its own column) rather than
#   done by unsetting the credentials: "we deliberately did not page" and "we tried and had no
#   credentials" are different facts, and the second is one the delivery audit is meant to shout
#   about. The audit file is redirected too, so the harness never writes into the production one.
env = dict(os.environ, LIVE_MODE="DRY_RUN", LIVE_FAST_K="1",
           LIVE_ALARM_SUPPRESS="1",
           LIVE_NOTIFY_AUDIT=os.path.join(_lockdir, "notify_audit.jsonl"),
           LIVE_ANCHOR_LOCK=os.path.join(_lockdir, "anchor.lock"))
_started_utc = time.time()
r = subprocess.run([sys.executable, os.path.join(REPO, "scheduler", "run_anchor.py")],
                   capture_output=True, text=True, env=env, timeout=180)
check("entry point exits 0", r.returncode == 0, r.returncode)
out = r.stdout
check("the watchdog line is present in the run log", "watchdog: tripped=" in out,
      [l for l in out.splitlines() if "watchdog" in l][:1])
check("it did NOT fail to evaluate", "watchdog FAILED" not in out)
wd_state = os.path.join(REPO, "state", "watchdog", "last_eval.json")
check("watchdog persisted its evaluation (not in-memory only)", os.path.exists(wd_state))
if os.path.exists(wd_state):
    ev = json.load(open(wd_state))
    check("the persisted evaluation names its conditions", isinstance(ev, dict) and len(ev) > 0)

# ★★ THIS SUITE DID NOT GUARD WHAT IT CLAIMED, AND AN INJECTION PROVED IT (2026-07-26).
# Injection 5c replaced the call with `(...) if True else WD.run(...)` — the literal `WD.run(`
# still in the source, the `watchdog: tripped=` line still logged, and the watchdog never
# evaluated anything. THE SUITE STAYED GREEN. It was checking two proxies:
#     (a) the string "WD.run(" appears in the file  -> defeated by keeping the token
#     (b) a line was printed to the run log         -> defeated by printing it anyway
# and both survive a watchdog that does nothing. That is the exact failure this file was written
# to prevent ("ported, tested, green for days, never called").
# ⇒ The fix is the rule that was already in our own notes and not applied here: pair "the process
# ran" with "its SUBJECT advanced", and take the advance from the subject itself. `watchdog.run`
# stamps `evaluated_utc` into last_eval.json; requiring it to be NEWER than this run's start
# cannot be satisfied by a string in the source or a line in a log.
# (calendar.timegm, not time.mktime — a UTC string parsed as local was a false alarm earlier.)
_t0 = _started_utc
_fresh, _age = None, None
if os.path.exists(wd_state):
    _stamp = (json.load(open(wd_state)) or {}).get("evaluated_utc")
    if _stamp:
        _ts = calendar.timegm(time.strptime(_stamp, "%Y-%m-%dT%H:%M:%SZ"))
        _age = round(_ts - _t0, 1)
        _fresh = _ts >= _t0 - 2          # 2s slack for clock granularity, not for staleness
check("★★ the watchdog EVALUATED during this run — evidence produced by the watchdog itself, "
      "not by a string in the source or a line in a log", _fresh is True,
      f"evaluated_utc is {_age}s after this run started (must be >= 0)")

print("\n[D] the clock gate and the anti-sleep guard are reached by the REAL entry point")
check("the anti-sleep guard was checked this run", "nosleep: ok=" in out,
      [l for l in out.splitlines() if "nosleep:" in l][:1])
# ★ THIS ASSERTION USED TO REQUIRE THE OPPOSITE, AND THE CHANGE IS THE POINT.
# It read: "it says so explicitly when it did NOT read the sleep log". That was the honest thing
# to assert while the per-anchor check only asked "is the guard held right now" — a reading that
# can DETECT a sleep (a completion goes missing) but cannot ATTRIBUTE it: "one short" looks the
# same whether the machine slept, lost a lock race, or crashed. With 30-of-30 and zero tolerance a
# failed window has to be diagnosable AT THE TIME, because the evidence does not exist afterwards.
# ⇒ The log is now read every anchor, over exactly the gap since the last check (3.1s measured,
#   against a 1500s budget), and the claim is upgraded from "nothing detectably wrong at this
#   instant" to "the machine did not sleep during this interval". The two used to print
#   identically, which is what made the weaker one feel like the stronger one.
_nsl = [l for l in out.splitlines() if "nosleep:" in l]
check("★ the sleep LOG was read this run, over a stated interval (not just 'the guard is held')",
      _nsl and "log_verified=True" in _nsl[-1] and "interval=" in _nsl[-1], _nsl[-1:])
check("...and the sleeps are attributed to both sides of the guard, so a failure is diagnosable",
      _nsl and "slept_since_guard=" in _nsl[-1] and "slept_before_guard=" in _nsl[-1], _nsl[-1:])
_pa = [l for l in out.splitlines() if "phase_A:" in l]
check("phase A records the schedule decision", _pa and '"schedule"' in _pa[-1], _pa[-1][:120] if _pa else "")
if _pa:
    _j = json.loads(_pa[-1].split("phase_A:", 1)[1])
    # ★ CONDITIONAL ON PURPOSE: this suite runs whenever someone runs it, so whether it is on
    # schedule is not ours to choose. The IMPLICATION is what must hold either way — and it is
    # the property the gate exists for, not a restatement of the clock.
    if _j.get("book_source") == "external" and _j.get("action") != "TRADE":
        # ★ 2026-08-22 external book: a DRY battery run at an arbitrary wall-clock minute will
        #   usually find no verified target for the nearest slot (the producer lands ~N+22) ⇒ the
        #   loop HOLDS by design: no target vector, no plan, no orders, reason named. That is the
        #   property to assert here — `n_planned > 0` cannot hold on a HOLD anchor and must not
        #   be demanded of it (the TRADE branch below still demands it when the file IS there).
        check("★ external book unavailable ⇒ HOLD with a NAMED reason and no plan",
              _j.get("action") in ("HOLD", "DERISK", "FLATTEN")
              and bool((_j.get("external_book") or {}).get("reason"))
              and "n_planned" not in _j,
              f"action={_j.get('action')} external_book={_j.get('external_book')}")
    elif _j.get("off_schedule_halt"):
        # ★ 2026-08-21: 守门对象精确化为【开仓】单(n_live_opening); reduce-only/flatten 路径按设计
        #   在 off-schedule 仍放行(off_schedule_halt.note), 且自 per_name_stop 上线后 live 状态里可合法
        #   存在 stopped 名 ⇒ 排练会产生 flatten 单。断言键缺失 = 旧代码 = 红(不回退到 n_live)。
        check("★ off-schedule => ZERO OPENING orders went live (planned > 0, live_opening == 0; reduce-only 路径放行)",
              "n_live_opening" in _j and _j.get("n_live_opening") == 0 and (_j.get("n_planned") or 0) > 0,
              f"planned={_j.get('n_planned')} live={_j.get('n_live')} live_opening={_j.get('n_live_opening')} "
              f"reduce_only={_j.get('live_reduce_only_syms')} offset={_j['off_schedule_halt']['offset_min']}min")
    else:
        check("on-schedule => the gate did not halt", _j.get("schedule", {}).get("on_schedule"),
              _j.get("schedule"))

print("\n[E] ★★ the funding ledger RAN — and the evidence comes from the ledger, not the log")
# `FundingLedger` was complete, tested, and never constructed on the production path:
# `binance_funding` was imported only by its own test suite, so funding.jsonl's zero rows were
# never "no settlement yet". This is that call site's guard.
#
# ★ AND IT IS DELIBERATELY NOT "the funding: line is in the run log". That is the proxy injection
# 5c defeated tonight — token present, line printed, component inert. The ledger stamps its own
# `evaluated_utc` on BOTH exits (including the empty one, which is the branch DRY_RUN takes), and
# a stamp newer than this run's start cannot be produced by a string in the source.
_fp = os.path.join(REPO, "state", "funding_last_pull.json")
_ffresh, _fage, _fdoc = None, None, None
if os.path.exists(_fp):
    _fdoc = json.load(open(_fp)) or {}
    _fs = _fdoc.get("evaluated_utc")
    if _fs:
        _fage = round(calendar.timegm(time.strptime(_fs, "%Y-%m-%dT%H:%M:%SZ")) - _started_utc, 1)
        _ffresh = _fage >= -2
check("★★ the ledger pulled during THIS run (its own stamp, newer than the run start)",
      _ffresh is True, f"evaluated_utc is {_fage}s after this run started; file={_fp}")
check("...and the stamp says what it found, so 'ran and found nothing' is distinguishable "
      "from 'never ran'",
      isinstance(_fdoc, dict) and "n_income" in _fdoc and "rows_written" in _fdoc,
      {k: (_fdoc or {}).get(k) for k in ("n_income", "rows_written", "skipped_no_position")})
check("the run log carries the line too (weak on its own, useful beside the stamp)",
      "funding: income=" in out, [l for l in out.splitlines() if "funding:" in l][:1])

print(f"\n{'ALL PASS' if FAILS == 0 else str(FAILS) + ' FAIL'}")
sys.exit(1 if FAILS else 0)
