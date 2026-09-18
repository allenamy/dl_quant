#!/usr/bin/python3
"""Will this machine stay awake for the certification window? — answered by OBSERVATION.

★ WHY THIS IS NOT A SETTINGS CHECK (measured, 2026-07-26)
The obvious gate is `pmset -g`: read the sleep settings, refuse if the machine would sleep. On
THIS machine that gate passes and is wrong:

    pmset -g custom, AC Power:   sleep 0          <- "never sleep on AC"
    pmset -g log, 2026-07-25:    106 x "Entering Sleep state due to 'Maintenance Sleep'"
                                 spanning 00:10 -> 13:22 local, all on AC power,
                                 ending in "Wake ... due to EC.LidOpen"

So the machine slept 106 times on a day its settings said it never sleeps — because the lid was
closed, and lid-close sleep is not the idle sleep the setting governs. A settings check would
have certified a machine that was asleep through two anchor slots.

⇒ The verdict here is built on what the sleep LOG says happened, not on what the settings say
should happen. The settings are still printed — as an observation, labelled insufficient.

★ AND ON WHOSE ASSERTION
`pmset -g assertions` showing `PreventUserIdleSystemSleep 1` is not evidence that OUR agent is
alive: any tool can hold that assertion (one did — an unrelated `caffeinate` with a 300s timeout
was holding it while this file was being written). So the assertion is matched against the PID
launchd reports for our own job. Otherwise a borrowed assertion reads exactly like a working one.

★ WHAT THIS CANNOT DO
It cannot prove the machine will not sleep in the future — only that it has not, that the guard
is currently held by our process, and that the power source is one where the guard applies.
Lid-close behaviour with the guard held is NOT established here; it needs a physical test. That
is stated in the output rather than assumed, in either direction.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_LABEL = "com.dlquant.live.nosleep"
ANCHOR_LABEL = "com.dlquant.live.anchor"
# the guard we require to be held. -i is the one that matters for an unattended box; -s only
# applies on AC and -m keeps the disk up. -d (display) and -u (user active) are deliberately NOT
# used: -u turns the display ON and self-expires after 5s without -t, so it is worse than nothing.
REQUIRED_ASSERTION = "PreventUserIdleSystemSleep"


def min_evidence_h() -> float:
    """How much GUARDED, sleep-free time the window requires before it may start. Config, not a
    literal: it is a threshold that carries a verdict."""
    sys.path.insert(0, os.path.join(REPO, "live"))
    import book_config as BC
    v = BC.load().get("nosleep_min_evidence_h")
    if v is None:
        raise KeyError("config/book.json has no `nosleep_min_evidence_h`")
    return float(v)


def _run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 127, "", str(e)


# ── observations ────────────────────────────────────────────────────────────────────────────────
def agent_pid(label=AGENT_LABEL):
    """PID launchd reports for our own job, or None. Distinguishes 'not loaded' from 'loaded but
    not running' — the second is what KeepAlive is supposed to make impossible."""
    rc, out, _ = _run(["launchctl", "list", label])
    if rc != 0:
        return {"loaded": False, "pid": None}
    m = re.search(r'"PID"\s*=\s*(\d+)', out)
    return {"loaded": True, "pid": int(m.group(1)) if m else None}


_OWNER = re.compile(
    r"pid (\d+)\((\S+?)\): \[0x[0-9a-f]+\]\s+(\d+):(\d\d):(\d\d)\s+" + REQUIRED_ASSERTION)


def assertion_state():
    """Who holds the guard, for how long, and whether it expires by itself.

    ★ The 'for how long' is the whole point. It is our only evidence of how much guarded time has
    actually elapsed — without it a guard installed one second ago and a guard that has held for a
    week are the same reading, and "no sleep events since the guard started" becomes trivially
    true. ★ And 'expires by itself' matters because an unrelated `caffeinate -t 300` was holding
    this exact assertion while this file was written: `asserting for 300 secs` is not a guard,
    it is a countdown that reads like one.
    """
    rc, out, err = _run(["pmset", "-g", "assertions"])
    if rc != 0:
        return {"held": None, "error": err[:200], "owners": []}
    held = re.search(rf"{REQUIRED_ASSERTION}\s+(\d)", out)
    owners = []
    for blk in out.split("   pid ")[1:]:
        m = _OWNER.match("pid " + blk)
        if not m:
            continue
        owners.append({"pid": int(m.group(1)), "name": m.group(2),
                       "age_s": int(m.group(3)) * 3600 + int(m.group(4)) * 60 + int(m.group(5)),
                       "forever": "asserting forever" in blk.split("\n", 3)[1]
                                  if "\n" in blk else False})
    return {"held": bool(held and held.group(1) == "1"), "owners": owners,
            "owner_pids": [o["pid"] for o in owners],
            "owner_names": [o["name"] for o in owners]}


def power_source():
    rc, out, _ = _run(["pmset", "-g", "ps"])
    if rc != 0:
        return "UNKNOWN"
    if "'AC Power'" in out:
        return "AC"
    if "'Battery Power'" in out:
        return "BATTERY"
    return "UNKNOWN"


def stored_sleep_settings():
    """Reported for the record ONLY. Proven insufficient above — do not gate on it."""
    rc, out, _ = _run(["pmset", "-g", "custom"])
    if rc != 0:
        return {}
    cur, res = None, {}
    for line in out.splitlines():
        if line.strip().endswith("Power:"):
            cur = line.strip().rstrip(":").replace(" Power", "")
        elif cur:
            m = re.match(r"\s+(sleep|disksleep|standby|powernap|hibernatemode)\s+(\S+)", line)
            if m:
                res.setdefault(cur, {})[m.group(1)] = m.group(2)
    return res


ASL_DIR = "/var/log/powermanagement"     # powerd's own store; `pmset -g log` renders exactly these files (its first output line names the store)
SLEEP_DOMAIN = "[com.apple.iokit.domain Sleep]"


def _asl_files(since_epoch: float, asl_dir: str = ASL_DIR):
    """The per-day ASL files that can hold an event at or after `since_epoch`: a file whose last
    write is older than `since` cannot, so it is skipped without being read; the newest file is
    always read (it is the live one). None when the directory cannot be listed — UNKNOWN is a
    distinct value from 'no files'."""
    try:
        names = sorted(n for n in os.listdir(asl_dir) if n.endswith(".asl"))
    except Exception:
        return None
    paths = [os.path.join(asl_dir, n) for n in names]
    out = []
    for i, p in enumerate(paths):
        try:
            if i == len(paths) - 1 or os.path.getmtime(p) >= since_epoch:
                out.append(p)
        except Exception:
            continue
    return out


def parse_asl_raw(text: str, since_epoch: float):
    """Sleep entries from `syslog -F raw` lines: a record is a sleep entry when its powerd domain
    is Sleep (`[com.apple.iokit.domain Sleep]`) or its message is the 'Entering Sleep state' text
    pmset renders; its time is the `[Time <epoch>]` key (UTC seconds, no timezone parsing)."""
    evs = []
    for line in text.splitlines():
        if SLEEP_DOMAIN not in line and "Entering Sleep state" not in line:
            continue
        m = re.search(r"\[Time (\d+)\]", line)
        if not m:
            continue
        t = float(m.group(1))
        if t < since_epoch:
            continue
        r = re.search(r"due to '([^']+)'", line)
        evs.append({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t)),
                    "epoch": t, "reason": r.group(1) if r else "?"})
    evs.sort(key=lambda e: e["epoch"])
    return evs


def sleep_events_detail(since_epoch: float, asl_dir: str = ASL_DIR, per_file_timeout: float = 60.0):
    """Actual sleep entries since `since_epoch`, plus a note naming the source that was read.

    ★ NOSLEEP-1 (2026-09-17): `pmset -g log` renders the WHOLE store — 185 MB / 825k lines / 74 s
    on this machine by 09-17 (assertion spam from nsurlsessiond) — against the 60 s timeout this
    reader had, so from 09-14 the read timed out intermittently and from 09-16 04:47Z on every
    anchor: sleep_log_verified=False, guard red, with the machine never having slept. The bounded
    reader below opens only the per-day files that can hold the window (`syslog -f`, ~1 s per
    26 MB file) and parses the raw keys; the pmset path is kept only as a fallback for a store
    that cannot be listed, with a timeout wide enough to finish.

    Returns (events, note). events is None (not []) when the log could not be read: an EMPTY LIST
    MEANS 'IT DID NOT SLEEP' and must never be produced by a failure to look."""
    files = _asl_files(since_epoch, asl_dir)
    if files is None:
        evs = sleep_events_pmset(since_epoch)
        return evs, ("pmset (asl store unlistable)" if evs is not None else "UNREADABLE: asl store unlistable and pmset failed")
    if not files:
        return None, "UNREADABLE: asl store holds no .asl file"
    t0 = time.time(); evs = []
    for p in files:
        rc, out, err = _run(["syslog", "-f", p, "-F", "raw"], timeout=per_file_timeout)
        if rc != 0:
            return None, f"UNREADABLE: syslog -f {os.path.basename(p)} rc={rc} {err.strip()[:80]}"
        evs.extend(parse_asl_raw(out, since_epoch))
    evs.sort(key=lambda e: e["epoch"])
    return evs, f"asl:{len(files)} file(s) {os.path.basename(files[0])}..{os.path.basename(files[-1])} in {time.time() - t0:.1f}s"


def sleep_events(since_epoch: float):
    """Compatibility wrapper: events or None (see sleep_events_detail)."""
    return sleep_events_detail(since_epoch)[0]


def sleep_events_pmset(since_epoch: float, timeout: float = 240.0):
    """The original reader: `pmset -g log` rendered lines. Whole-store dump, minutes on a large
    store — fallback only. None when it fails or times out."""
    rc, out, err = _run(["pmset", "-g", "log"], timeout=timeout)
    if rc != 0:
        return None
    evs = []
    for line in out.splitlines():
        if "Entering Sleep state" not in line:
            continue
        m = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ([+-]\d{4})", line)
        if not m:
            continue
        try:
            dt = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone(timedelta(hours=int(m.group(2)[:3]),
                                          minutes=int(m.group(2)[0] + m.group(2)[3:]))))
        except Exception:
            continue
        if dt.timestamp() < since_epoch:
            continue
        r = re.search(r"due to '([^']+)'", line)
        evs.append({"utc": dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "epoch": dt.timestamp(), "reason": r.group(1) if r else "?"})
    return evs


# ── verdict ─────────────────────────────────────────────────────────────────────────────────────
def collect(lookback_h: float = 24.0, read_log: bool = True) -> dict:
    """Everything this machine can tell us. Separated from the verdict so the DECISION can be
    tested against synthetic observations — a suite that goes red because someone unplugged the
    laptop is a suite people learn to ignore."""
    now = time.time()
    evs, src = (sleep_events_detail(now - lookback_h * 3600) if read_log else ("NOT_READ", "not read (--quick)"))
    return {"now": now, "agent": agent_pid(), "assertion": assertion_state(),
            "power_source": power_source(), "lookback_h": lookback_h,
            "sleep_events": evs, "sleep_log_source": src,
            "stored": stored_sleep_settings()}


def verdict(obs: dict) -> dict:
    now = obs.get("now") or time.time()
    ag, asrt, ps = obs["agent"], obs["assertion"], obs["power_source"]
    lookback_h, evs = obs.get("lookback_h", 24.0), obs["sleep_events"]
    read_log = evs != "NOT_READ"

    blocking, notes = [], []
    if not ag["loaded"]:
        blocking.append(f"the anti-sleep agent {AGENT_LABEL} is NOT loaded "
                        f"(install: bash ops/install_nosleep.sh)")
    elif ag["pid"] is None:
        blocking.append(f"{AGENT_LABEL} is loaded but has NO PID — it is not running, which is "
                        f"what KeepAlive exists to prevent. Check state/nosleep_err.log.")
    ours = next((o for o in asrt.get("owners", []) if o["pid"] == ag.get("pid")), None)
    guard_age_h = (ours["age_s"] / 3600.0) if ours else 0.0
    if asrt.get("held") is None:
        blocking.append(f"could not read pmset assertions ({asrt.get('error')}) — UNKNOWN, "
                        f"which is not a pass")
    elif not asrt.get("held"):
        blocking.append(f"{REQUIRED_ASSERTION} is NOT held by anything")
    elif ag["pid"] is not None and ours is None:
        blocking.append(
            f"{REQUIRED_ASSERTION} is held, but by {asrt.get('owner_names')} "
            f"(pids {asrt.get('owner_pids')}), NOT by our agent (pid {ag['pid']}). A borrowed "
            f"assertion reads exactly like a working one and disappears without warning.")
    elif ours is not None and not ours["forever"]:
        blocking.append(
            f"our assertion is TIMED, not permanent (pid {ours['pid']}) — it expires on its own "
            f"and then nothing is holding anything. caffeinate must run without -t.")
    if ps == "BATTERY":
        blocking.append("power source is BATTERY: the stored setting is sleep=10min there, and "
                        "caffeinate -s is documented to apply on AC only. Plug it in.")
    elif ps != "AC":
        blocking.append(f"power source is {ps} — we could not read it, so we cannot say the "
                        f"sleep guard applies. UNKNOWN is not a pass.")
    # ★ SPLIT AT THE GUARD, and require the guarded stretch to be long enough to mean something.
    # Sleeps from BEFORE the guard existed are why the guard exists; blocking on them would make
    # the gate permanently red for a condition that has been fixed. But "no sleeps since the
    # guard started" is trivially true one second after installing it — so the evidence window
    # must also be long enough to have contained a sleep if one were coming. Both halves are
    # needed; either alone is a gate that cannot fail.
    min_ev = obs.get("min_evidence_h")
    min_ev = min_evidence_h() if min_ev is None else float(min_ev)
    since_guard, before_guard = [], []
    if read_log and evs:
        cut = now - (guard_age_h * 3600.0)
        since_guard = [e for e in evs if e["epoch"] >= cut]
        before_guard = [e for e in evs if e["epoch"] < cut]
    if read_log:
        if evs is None:
            blocking.append("could not read the sleep log — cannot tell whether it slept; UNKNOWN")
        else:
            if since_guard:
                reasons = sorted({e["reason"] for e in since_guard})
                blocking.append(
                    f"the machine SLEPT {len(since_guard)}x WHILE THE GUARD WAS HELD "
                    f"({', '.join(reasons)}; most recent {since_guard[-1]['utc']}) — the guard "
                    f"does not cover this cause. If the lid was closed, it must stay OPEN.")
            if guard_age_h < min_ev and not blocking:
                blocking.append(
                    f"the guard has held for only {guard_age_h:.2f}h; {min_ev:g}h of guarded, "
                    f"sleep-free time is required before the window may start. "
                    f"(Zero sleeps in zero hours is not evidence.)")
            if before_guard:
                notes.append(f"{len(before_guard)} sleep event(s) recorded BEFORE the guard "
                             f"started (most recent {before_guard[-1]['utc']}) — context, not a "
                             f"failure: they are the reason the guard exists.")
    notes.append("lid-close behaviour WITH the guard held is not established by this check; it "
                 "needs a physical test. Treat a closed lid as unproven, not as safe.")
    notes.append("both jobs are LaunchAGENTs: after a reboot with no login, neither the anchor "
                 "nor this guard runs. A reboot during the window ends the window.")

    return {"ok": not blocking, "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "agent": ag, "assertion": asrt, "power_source": ps,
            "guard_age_h": round(guard_age_h, 3), "min_evidence_h": min_ev,
            "n_sleep_since_guard": (None if not read_log or evs is None else len(since_guard)),
            "n_sleep_before_guard": (None if not read_log or evs is None else len(before_guard)),
            "sleep_events_lookback_h": lookback_h,
            # ★ THREE STATES, NOT TWO. `ok` from a --quick run means "nothing detectably wrong
            # RIGHT NOW"; it does NOT mean the machine has not been sleeping, because the log was
            # never read. A consumer that gates on `ok` alone would read the cheap check as the
            # expensive one — the exact shape of "a reading, but not of the quantity you asked
            # about". The start gate requires sleep_log_verified.
            "sleep_log_verified": bool(read_log and evs is not None),
            "sleep_log_source": obs.get("sleep_log_source"),      # NOSLEEP-1: which reader produced the verdict's evidence (asl files / pmset / UNREADABLE …)
            "n_sleep_events": (None if evs in (None, "NOT_READ") else len(evs)),
            "sleep_events": (evs if evs in (None, "NOT_READ") else evs[-5:]),
            "stored_settings_INSUFFICIENT": obs.get("stored"),
            "blocking": blocking, "notes": notes}


def _marker_path() -> str:
    root = os.environ.get("LIVE_PILOT_LOG")
    base = os.path.dirname(root) if root else os.path.join(REPO, "state")
    return os.path.join(base, "nosleep_last_check.json")


def since_last_check_h(default_h: float = 4.5) -> float:
    """Hours since this checker last ran, so the sleep-log window is exactly the gap between
    anchors rather than a fixed guess. Falls back to a little over one anchor interval, and
    NEVER shrinks below it: a short window would under-report sleeps, which is the direction
    that hides the thing we are looking for."""
    try:
        prev = json.load(open(_marker_path())).get("checked_epoch")
        if prev:
            gap = (time.time() - float(prev)) / 3600.0
            return max(default_h, min(gap * 1.1, 48.0))
    except Exception:
        pass
    return default_h


def _write_marker():
    try:
        p = _marker_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump({"checked_epoch": time.time(),
                   "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                  open(p, "w"))
    except Exception:
        pass


def report(lookback_h: float = 24.0, read_log: bool = True) -> dict:
    r = verdict(collect(lookback_h, read_log))
    if read_log:
        _write_marker()
    return r


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    gate = "--gate" in sys.argv          # start-of-window gate: the LOG must have been read
    lb = 24.0
    for i, a in enumerate(sys.argv):
        if a == "--lookback-h" and i + 1 < len(sys.argv):
            lb = float(sys.argv[i + 1])
    rep = report(lookback_h=lb, read_log=not quick)
    if gate and not rep["sleep_log_verified"]:
        # ★ a --quick verdict is "nothing wrong right now", NOT "it has not been sleeping". The
        # gate must not be satisfiable by the cheap reading of a different quantity.
        print("防休眠门: 未读取休眠日志 —— --quick 的结论不构成'机器没睡过'的证据, 拒绝起算")
        sys.exit(1)
    if "--json" in sys.argv:
        print(json.dumps(rep, indent=1, ensure_ascii=False))
    else:
        print(f"防休眠: {'OK' if rep['ok'] else '不合格'}  "
              f"(电源 {rep['power_source']}, agent pid {rep['agent']['pid']}, "
              f"断言 {rep['assertion'].get('held')})")
        for b in rep["blocking"]:
            print(f"  ✗ {b}")
        for n in rep["notes"]:
            print(f"  · {n}")
    sys.exit(0 if rep["ok"] else 1)
