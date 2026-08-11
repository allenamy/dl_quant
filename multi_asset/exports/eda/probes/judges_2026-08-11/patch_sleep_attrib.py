"""Per-anchor sleep attribution. PREPARED while waiting; applied only after the anchor clears.

Diagnostic gap (team-lead): the per-anchor nosleep check reads the agent pid and the power source
but not the sleep log. So a sleep during the window is DETECTED (a completion goes missing) and
not ATTRIBUTABLE — we would see "one short" and be unable to say whether it slept, lost a lock
race, or crashed. With 30-of-30 and zero tolerance, a window that fails must be diagnosable on the
spot, or the second window can repeat the same cause.

Cost measured: `pmset -g log` = 3.1s. Against a 1500s anchor budget that is noise, so the full
version is used rather than the kern.boottime fallback — only the full version names the CAUSE
(Maintenance Sleep / Clamshell / …), which is the half being asked for.
"""
import os

REPO = "/Users/haosiyu/dl_quant_live"

# ── 1. check_nosleep: remember when we last looked, so the interval is exactly anchor-to-anchor
P1 = os.path.join(REPO, "ops", "check_nosleep.py")
s1 = open(P1).read()
OLD1 = '''def report(lookback_h: float = 24.0, read_log: bool = True) -> dict:
    return verdict(collect(lookback_h, read_log))'''
NEW1 = '''def _marker_path() -> str:
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
    return r'''
assert s1.count(OLD1) == 1, "report() anchor not found"
s1 = s1.replace(OLD1, NEW1, 1)
open(P1, "w").write(s1)

# ── 2. run_anchor: read the log over that interval, record, do not judge
P2 = os.path.join(REPO, "scheduler", "run_anchor.py")
s2 = open(P2).read()
OLD2 = '''    try:
        import check_nosleep as CNS
        _ns = CNS.report(read_log=False)
        log(f"nosleep: ok={_ns['ok']} agent_pid={_ns['agent']['pid']} "
            f"guard_age_h={_ns['guard_age_h']} power={_ns['power_source']} "
            f"(sleep log NOT read this run)")'''
NEW2 = '''    # ★ THE SLEEP LOG IS NOW READ EVERY ANCHOR, over exactly the gap since the last check.
    # Before this, the per-anchor reading answered "is the guard held right now" and the window
    # could therefore DETECT a sleep (a completion goes missing) without being able to ATTRIBUTE
    # it — "one short" reads the same whether the machine slept, lost a lock race, or crashed.
    # With 30-of-30 and zero tolerance, a failed window has to be diagnosable at the time; the
    # evidence does not exist retroactively. Cost measured at 3.1s against a 1500s budget.
    # ⇒ It also UPGRADES the claim: `sleep_log_verified` goes False -> True, i.e. from "nothing
    # detectably wrong at this instant" to "the machine did not sleep during this interval".
    # Those are different strengths and they used to be printed identically.
    # Recording, not judging (per the ruling): the only alarm remains the pre-existing one —
    # clock started AND a sleep occurred while our guard was held, which says the guard does not
    # cover that cause.
    try:
        import check_nosleep as CNS
        _lb = CNS.since_last_check_h()
        _ns = CNS.report(lookback_h=_lb, read_log=True)
        _reasons = sorted({e["reason"] for e in (_ns.get("sleep_events") or [])
                           if isinstance(e, dict)})
        log(f"nosleep: ok={_ns['ok']} agent_pid={_ns['agent']['pid']} "
            f"guard_age_h={_ns['guard_age_h']} power={_ns['power_source']} "
            f"| interval={_lb:.1f}h log_verified={_ns['sleep_log_verified']} "
            f"slept_since_guard={_ns['n_sleep_since_guard']} "
            f"slept_before_guard={_ns['n_sleep_before_guard']}"
            f"{' reasons=' + str(_reasons) if _reasons else ''}")'''
assert s2.count(OLD2) == 1, "nosleep block anchor not found"
s2 = s2.replace(OLD2, NEW2, 1)
open(P2, "w").write(s2)

print("applied: check_nosleep marker + run_anchor full-log reading")
