#!/usr/bin/env python3
"""venue_quiet_window 的行为测试(纯本地夹具, 不读真实锚日志, 不联网)。"""
import calendar, os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import venue_quiet_window as V

T = lambda s: calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
N = T("2026-09-19T08:00:00Z")
res = []


def log(lines):
    fd, p = tempfile.mkstemp(suffix=".log"); os.write(fd, ("\n".join(lines) + "\n").encode()); os.close(fd); return p


def check(name, cond, detail=""):
    res.append((name, bool(cond))); print(("[PASS] " if cond else "[FAIL] ") + name + (f" — {detail}" if detail else ""))


done_log = log(["2026-09-19T08:00:00Z anchor start mode=LIVE", '2026-09-19T08:24:46Z phase_A: {"note": "x anchor done y"}', "2026-09-19T08:55:09Z anchor done rc=0"])
run_log = log(["2026-09-19T04:53:36Z anchor done rc=0", "2026-09-19T08:00:00Z anchor start mode=LIVE", '2026-09-19T08:24:46Z phase_A: {"q": " anchor done "}'])
os.environ.pop("VENUE_QUIET_WINDOW_OVERRIDE", None)

s = V.quiet_window_status(N + 30 * 60, done_log); check("inside anchor span (N+30m) ⇒ closed", not s["open"], s["reason"])
s = V.quiet_window_status(N + 70 * 60, done_log); check("after done, N+70m ⇒ open", s["open"], s["reason"])
s = V.quiet_window_status(N + 70 * 60, run_log); check("start without done (N+70m, <90m) ⇒ closed; quoted 'anchor done' in JSON not counted", not s["open"] and s["anchor_in_progress"], s["reason"])
s = V.quiet_window_status(N + 100 * 60, run_log); check("start without done >90m ⇒ open with stale flag", s["open"] and s["stale_start"], s["reason"])
s = V.quiet_window_status(N + 225 * 60, done_log); check("N+3:45 ⇒ closed (next anchor near)", not s["open"], s["reason"])
s = V.quiet_window_status(N + 70 * 60, "/nonexistent/anchor_runs.log"); check("unreadable log ⇒ closed (unknown is not open)", not s["open"], s["reason"])
empty = log(["2026-09-19T08:24:46Z phase_A: {}"]); s = V.quiet_window_status(N + 70 * 60, empty); check("no start line ⇒ closed", not s["open"], s["reason"])
try:
    V.require_quiet_window(20, N + 210 * 60, done_log); check("require: 10 min left < 20 ⇒ refused", False)
except SystemExit as e:
    check("require: 10 min left < 20 ⇒ refused", "only" in str(e), str(e))
try:
    V.require_quiet_window(20, N + 30 * 60, done_log); check("require: inside anchor ⇒ refused", False)
except SystemExit as e:
    check("require: inside anchor ⇒ refused", "REFUSED" in str(e))
st = V.require_quiet_window(20, N + 80 * 60, done_log); check("require: N+80m ⇒ allowed", st["open"])
os.environ["VENUE_QUIET_WINDOW_OVERRIDE"] = "test override"
s = V.quiet_window_status(N + 30 * 60, done_log); check("override opens and is recorded", s["open"] and s["override"] == "test override")
os.environ.pop("VENUE_QUIET_WINDOW_OVERRIDE")
clock = [N + 30 * 60]
st = V.wait_for_quiet_window(5, 60, done_log, _sleep=lambda d: clock.__setitem__(0, clock[0] + d), _now=lambda: clock[0])
check("wait: sleeps from N+30m until the window opens at N+60m", st["open"] and st["waited_s"] == 1800, f"waited {st['waited_s']} s")
# mutation: a guard that ignores the in-progress rule must fail the 'start without done' case
orig = V._last_start_done
V._last_start_done = lambda p: (orig(p)[0], orig(p)[0] + 1)      # pretend every start is done
s = V.quiet_window_status(N + 70 * 60, run_log); check("mutation (ignore in-progress) would open — so the in-progress test can fail", s["open"])
V._last_start_done = orig

# wiring: the real fetchers' get() must call the guard BEFORE credentials / network (E-0919-V)
FP3 = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../docs/fixprogram_2026-09-13/FP3_devices"))
sys.path.insert(0, FP3)
import importlib
class _GuardHit(Exception): pass
class _CredHit(Exception): pass
for modname, call in (("fetch_trades", lambda m: m.get("/fapi/v1/userTrades", {"symbol": "X"})), ("fetch_income_paged", lambda m: m.get({"startTime": 0}))):
    m = importlib.import_module(modname)
    orig_wait, orig_cred = V.wait_for_quiet_window, m.credentials
    V.wait_for_quiet_window = lambda *a, **k: (_ for _ in ()).throw(_GuardHit())
    m.credentials = lambda: (_ for _ in ()).throw(_CredHit())
    try:
        call(m); check(f"{modname}.get calls the guard first", False, "no exception")
    except _GuardHit:
        check(f"{modname}.get calls the guard first", True)
    except _CredHit:
        check(f"{modname}.get calls the guard first", False, "credentials reached before the guard")
    finally:
        V.wait_for_quiet_window, m.credentials = orig_wait, orig_cred
n_fail = sum(1 for _, ok in res if not ok)
print(f"venue_quiet_window: {'ALL PASS' if not n_fail else 'FAILURES'} {len(res) - n_fail}/{len(res)} checks")
sys.exit(1 if n_fail else 0)
