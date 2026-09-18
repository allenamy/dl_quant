"""The anti-sleep verdict — tested on SYNTHETIC observations, never on this machine's state.

A suite that goes red because someone unplugged the laptop teaches people to ignore red. So the
machine-reading half (`collect`) is exercised by ops/install_nosleep.sh at install time, and the
DECISION half (`verdict`) — which is where the failure modes live — is exercised here against
observations we construct, including the ones that are hard to arrange on purpose.

★ The case worth the file on its own: `PreventUserIdleSystemSleep 1` held by SOMEBODY ELSE.
While this was being written, an unrelated `caffeinate` (300-second timeout) was holding exactly
that assertion. Any check that stops at "is the assertion held?" would have certified the guard
as working with our agent not installed at all — and then gone quietly red when that other
process exited. Borrowed protection reads exactly like protection.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_REPO, "ops"))
import check_nosleep as CN   # noqa: E402

FAILS = 0


def check(name, cond, extra=""):
    global FAILS
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(extra)) if extra else ''}")
    if not cond:
        FAILS += 1


NOW = 1.0e9
GUARD_H = 12.0                        # our guard has been held for 12h in the healthy fixture


def owners(pid=4242, age_s=int(GUARD_H * 3600), forever=True, name="caffeinate"):
    return {"held": True, "owner_pids": [pid], "owner_names": [name],
            "owners": [{"pid": pid, "name": name, "age_s": age_s, "forever": forever}]}


def obs(**kw):
    base = {"now": NOW, "agent": {"loaded": True, "pid": 4242}, "assertion": owners(),
            "power_source": "AC", "lookback_h": 24.0, "sleep_events": [], "stored": {},
            "min_evidence_h": 6.0}
    base.update(kw)
    return base


def slept(hours_ago):
    return {"utc": "fixture", "epoch": NOW - hours_ago * 3600, "reason": "Maintenance Sleep"}


print("[N] the healthy shape")
v = CN.verdict(obs())
check("everything in place -> ok", v["ok"], v["blocking"])
check("and it says the sleep log WAS read", v["sleep_log_verified"] is True)

print("\n[N] each failure blocks, and says which one")
cases = [
    ("agent not installed", obs(agent={"loaded": False, "pid": None}), "NOT loaded"),
    ("loaded but not running (KeepAlive's job)", obs(agent={"loaded": True, "pid": None}),
     "NO PID"),
    ("nothing holds the assertion",
     obs(assertion={"held": False, "owner_pids": [], "owner_names": [], "owners": []}),
     "NOT held"),
    ("★ assertion held by SOMEBODY ELSE's process", obs(assertion=owners(pid=999)),
     "NOT by our agent"),
    ("★ our assertion is TIMED (caffeinate -t) — a countdown that reads like a guard",
     obs(assertion=owners(forever=False)), "TIMED, not permanent"),
    ("pmset unreadable -> UNKNOWN, not a pass",
     obs(assertion={"held": None, "error": "boom", "owners": []}), "UNKNOWN"),
    ("on battery", obs(power_source="BATTERY"), "power source is BATTERY"),
    ("power source unknown -> UNKNOWN is not a pass (and does not claim 'battery')",
     obs(power_source="UNKNOWN"), "we could not read it"),
    ("★ it slept WHILE THE GUARD WAS HELD", obs(sleep_events=[slept(2)]),
     "SLEPT 1x WHILE THE GUARD"),
    ("★ sleep log unreadable -> UNKNOWN, never 'it did not sleep'",
     obs(sleep_events=None), "cannot tell"),
    ("★ zero sleeps in zero guarded hours is not evidence",
     obs(assertion=owners(age_s=60)), "only 0.02h"),
]
for name, o, frag in cases:
    vv = CN.verdict(o)
    check(name, (not vv["ok"]) and any(frag in b for b in vv["blocking"]),
          vv["blocking"][:1] or "NO BLOCKING REASON")

print("\n[N] ★ the split at the guard: old sleeps are context, new ones are failures")
v_old = CN.verdict(obs(sleep_events=[slept(20), slept(18)]))     # both older than the 12h guard
check("sleeps from BEFORE the guard do not block (they are why it exists)", v_old["ok"],
      v_old["blocking"])
check("but they are REPORTED, not dropped", v_old["n_sleep_before_guard"] == 2
      and any("BEFORE the guard" in n for n in v_old["notes"]))
v_mix = CN.verdict(obs(sleep_events=[slept(20), slept(2)]))
check("★ one sleep inside the guarded window blocks even though the older one does not",
      (not v_mix["ok"]) and v_mix["n_sleep_since_guard"] == 1
      and v_mix["n_sleep_before_guard"] == 1, v_mix["blocking"])
check("the two halves are BOTH required: a young guard with no sleeps still fails",
      not CN.verdict(obs(assertion=owners(age_s=3600)))["ok"])

print("\n[N] the cheap check must not be mistaken for the expensive one")
q = CN.verdict(obs(sleep_events="NOT_READ"))
check("--quick can still be ok (nothing detectably wrong right now)", q["ok"])
check("★ but it reports sleep_log_verified=False, so a gate cannot read it as 'it did not sleep'",
      q["sleep_log_verified"] is False)
check("and the count is None rather than 0 (absence is not zero)", q["n_sleep_events"] is None)

print("\n[N] the notes state what this check CANNOT establish")
n = " ".join(CN.verdict(obs())["notes"])
check("lid-close is called unproven rather than safe", "lid-close" in n and "unproven" in n)
check("the LaunchAgent-after-reboot hole is stated", "reboot" in n)


print("\n[ASL] NOSLEEP-1 (2026-09-17): the sleep log is read from the per-day store files, bounded, and UNKNOWN stays distinct from 'did not sleep'")
# Key layout copied from a REAL powerd assertion record on this machine (2026-09-17, `syslog -f ... -F raw`). No sleep record exists in the store's
# retained 15 days (the guard held throughout; pmset's own 825k-line render of the same store has zero Sleep-typed lines), so the sleep shape below is a
# FIXTURE on the real keys: domain `Sleep` (the store's `com.apple.iokit.domain` key, which pmset prints as the type column) + the message text pmset renders.
import tempfile as _tf, time as _tm, os as _os
_ASSERT = "[ASLMessageID 1624015] [Time {t}] [TimeNanoSec 49097000] [Level 5] [PID 117] [UID 0] [GID 0] [ReadGID 80] [Host h] [Sender powerd] [Facility com.apple.iokit.power] [Message [System: PrevIdle PrevSleep kCPU]] [AssertType MaintenanceWake] [AssertName com.apple.obc] [AssertAge 00:00:00 ] [RetainCount 0] [ProcessName PowerUIAgent] [Process 240] [AssertId 0xd00009021] [Action Created] [com.apple.iokit.domain Assertions]"
_SLEEP = "[ASLMessageID 1624016] [Time {t}] [TimeNanoSec 0] [Level 5] [PID 117] [UID 0] [GID 0] [ReadGID 80] [Host h] [Sender powerd] [Facility com.apple.iokit.power] [Message Entering Sleep state due to 'Maintenance Sleep':TCPKeepAlive=active Using AC (Charge:0%)] [com.apple.iokit.domain Sleep]"
_DOMAIN_ONLY = "[ASLMessageID 1624017] [Time {t}] [Sender powerd] [Message opaque] [com.apple.iokit.domain Sleep]"
_MSG_ONLY = "[ASLMessageID 1624018] [Time {t}] [Sender powerd] [Message Entering Sleep state due to 'Clamshell Sleep'] [com.apple.iokit.domain Assertions]"
_TEXT = "\n".join([_ASSERT.format(t=1000), _SLEEP.format(t=2000), _DOMAIN_ONLY.format(t=3000), _MSG_ONLY.format(t=4000), "garbage line without keys"])
ev = CN.parse_asl_raw(_TEXT, 0)
check("A1 parse: sleep-domain and 'Entering Sleep state' records are events (3), the assertion record is not; reason from the message, time from [Time]",
      [e["epoch"] for e in ev] == [2000.0, 3000.0, 4000.0] and [e["reason"] for e in ev] == ["Maintenance Sleep", "?", "Clamshell Sleep"] and ev[0]["utc"] == "1970-01-01T00:33:20Z", ev)
check("A2 since filter is on the record time", [e["epoch"] for e in CN.parse_asl_raw(_TEXT, 2500)] == [3000.0, 4000.0])
with _tf.TemporaryDirectory() as d:
    now = _tm.time()
    for n, age_d in (("2026.09.01.asl", 10), ("2026.09.08.asl", 3), ("2026.09.11.asl", 0)):
        open(f"{d}/{n}", "w").write("x"); _os.utime(f"{d}/{n}", (now - age_d * 86400, now - age_d * 86400))
    open(f"{d}/StoreData", "w").write("x")
    sel = lambda since: [_os.path.basename(x) for x in CN._asl_files(since, d)]
    check("A3 file selection by last-write time: only files that can hold the window are read, the newest always; a 1-day window reads one file, a 5-day window two",
          sel(now - 86400) == ["2026.09.11.asl"] and sel(now - 5 * 86400) == ["2026.09.08.asl", "2026.09.11.asl"] and sel(now - 30 * 86400) == ["2026.09.01.asl", "2026.09.08.asl", "2026.09.11.asl"] and sel(now + 3600) == ["2026.09.11.asl"], (sel(now - 86400), sel(now - 5 * 86400)))
    _real_run = CN._run
    # records placed relative to NOW so that the same `since` selects exactly the newest fixture file (a 1-day window) and filters records
    _NOWTEXT = "\n".join([_ASSERT.format(t=int(now - 100)), _SLEEP.format(t=int(now - 3000)), _DOMAIN_ONLY.format(t=int(now - 2000)), _MSG_ONLY.format(t=int(now - 1000))])
    try:
        CN._run = lambda cmd, timeout=20: (0, _NOWTEXT, "") if cmd[:2] == ["syslog", "-f"] else _real_run(cmd, timeout)
        evs, note = CN.sleep_events_detail(now - 2500, asl_dir=d)
        check("A4 end to end on a store dir: only the newest file is read for a 1-day window, records before `since` dropped, note names the source and the file",
              [e["epoch"] for e in evs] == [float(int(now - 2000)), float(int(now - 1000))] and note.startswith("asl:1 file(s) 2026.09.11.asl..2026.09.11.asl"), (evs, note))
        CN._run = lambda cmd, timeout=20: (1, "", "boom") if cmd[:2] == ["syslog", "-f"] else _real_run(cmd, timeout)
        evs, note = CN.sleep_events_detail(now - 2500, asl_dir=d)
        check("★ A5 a failed read is None + UNREADABLE, never [] (absence of evidence is its own value)", evs is None and note.startswith("UNREADABLE: syslog -f 2026.09.11.asl rc=1"), (evs, note))
        CN._run = lambda cmd, timeout=20: (127, "", "timed out") if cmd[:3] == ["pmset", "-g", "log"] else _real_run(cmd, timeout)
        evs, note = CN.sleep_events_detail(2500, asl_dir=f"{d}/does_not_exist")
        check("A6 store unlistable ⇒ pmset fallback; pmset failing too ⇒ None + UNREADABLE", evs is None and "pmset failed" in note, (evs, note))
    finally:
        CN._run = _real_run
with _tf.TemporaryDirectory() as d:
    evs, note = CN.sleep_events_detail(0, asl_dir=d)
    check("A7 an empty store dir is UNREADABLE (None), not 'no sleeps'", evs is None and "no .asl file" in note, (evs, note))
v_src = CN.verdict(obs(sleep_events=None, sleep_log_source="UNREADABLE: test"))
check("A8 the verdict carries the source note and an unreadable log still blocks as UNKNOWN", v_src["sleep_log_source"] == "UNREADABLE: test" and not v_src["ok"] and any("could not read the sleep log" in b for b in v_src["blocking"]), v_src["blocking"])
_t0 = _tm.time(); evs, note = CN.sleep_events_detail(_tm.time() - 4.5 * 3600); _dt = _tm.time() - _t0
check("★★★ A9 THIS MACHINE (the condition production reported red for two days): a 4.5 h window reads as a LIST from the store files in under 20 s",
      isinstance(evs, list) and note.startswith("asl:") and _dt < 20, (type(evs).__name__, note, round(_dt, 1)))
_t0 = _tm.time(); old = CN.sleep_events_pmset(_tm.time() - 3600, timeout=0.5); _dt = _tm.time() - _t0
check("★★ A10 RED CAPABILITY, the old reader's failure shape: `pmset -g log` under a timeout it cannot meet returns None (UNKNOWN) — the whole-store render is what timed out",
      old is None and _dt < 5, (old, round(_dt, 1)))

print(f"\n{'ALL PASS' if FAILS == 0 else str(FAILS) + ' FAIL'}")
sys.exit(1 if FAILS else 0)
