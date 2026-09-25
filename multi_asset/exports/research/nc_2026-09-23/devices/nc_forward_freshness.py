#!/usr/bin/env python3
"""Per-anchor acceptance item (lead 2026-09-25): FORWARD-LOG FRESHNESS. For each forward run log (dlarch's long `parabolic_onset_forward` and
the short queue; a directory means <dir>/run_log.jsonl), the time of its LAST line must be < --max-age-h (default 30) hours before now.
Read-only and hang-proof: the research repo is iCloud-synced and its files are evicted to placeholders (measured 2026-09-25: reads blocked
for > 10 min) — a placeholder (SF_DATALESS) is reported UNREADABLE without reading it, and the tail is read in a child process with a timeout.
The line's time is its `run_utc` (the key the forward runner writes; `utc` / `ts` accepted as fallbacks, named in the output).
Output: one line per log `FRESHNESS <path> FRESH|STALE|UNREADABLE age_h=… key=… last=…`, then `FORWARD_FRESHNESS OK|RED n_red=k`; exit 0 / 1.
PROGRESS (lead 2026-09-25, dlarch's measurement): a run that processed nothing still writes a fresh line (anchors_new 0 — legitimate for a
second run the same day, and exactly what the long queue would do forever behind the launchd/iCloud TCC wall, which makes os.listdir return []).
So, in parallel with freshness: `anchors_total_logged` must have INCREASED within the same window — the latest line's total vs the last line
written at or before (now − max_age_h); compared across the TIME WINDOW, never run to run (two same-day runs legitimately have equal totals;
measured recent totals [115, 121, 121, 126, 144]). No line old enough to anchor the window ⇒ YOUNG_LOG (named, counted, not a pass).
launchd.err next to the log: non-empty is REPORTED; content containing Traceback / AssertionError / "Error:" is a RED (the short queue's
start-up self-check writes "AssertionError: cannot enumerate ..." there); a plain warning is not.
Paths (2026-09-25): short queue ~/parabolic_onset_forward_short/run_log.jsonl (launchd com.hsy.onsetfwd_short, daily 07:22Z); long queue
~/Desktop/quant_research/multi_asset/exports/live/parabolic_onset_forward/run_log.jsonl until dlarch moves it to
~/pof_long/multi_asset/exports/live/parabolic_onset_forward/run_log.jsonl (then REPLACE, never keep both — the old path stops updating).
usage: /usr/bin/python3 nc_forward_freshness.py <path> [<path> ...] [--max-age-h 30] [--timeout 10]"""
import calendar, json, os, subprocess, sys, time

SF_DATALESS = 0x40000000
TAIL = ("import sys\nb = open(sys.argv[1], 'rb').read()\n"
        "ls = [l for l in b.decode('utf-8', 'replace').splitlines() if l.strip()]\nprint('\\n'.join(ls[-400:]))")


def parse_utc(s):
    s = str(s).replace("Z", "")[:19]
    return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%S"))


def one(path, max_h, timeout):
    p = os.path.join(path, "run_log.jsonl") if os.path.isdir(path) else path
    if not os.path.exists(p):
        return "UNREADABLE", f"missing {p}"
    if getattr(os.stat(p), "st_flags", 0) & SF_DATALESS:
        return "UNREADABLE", f"iCloud placeholder (materialise: brctl download \"{p}\"; cat \"{p}\" > /dev/null)"
    try:
        r = subprocess.run([sys.executable, "-c", TAIL, p], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "UNREADABLE", f"tail read timed out after {timeout:.0f} s"
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    if r.returncode != 0 or not lines:
        return "UNREADABLE", f"no last line (rc {r.returncode}) {r.stderr.strip()[:120]}"
    try:
        rows = [json.loads(l) for l in lines]
    except ValueError:
        return "UNREADABLE", "a run_log line is not JSON"
    d = rows[-1]
    key = next((k for k in ("run_utc", "utc", "ts") if k in d), None)
    if key is None:
        return "UNREADABLE", f"last line has no run_utc/utc/ts (keys {sorted(d)[:12]})"
    now = time.time(); age_h = (now - parse_utc(d[key])) / 3600.0
    if age_h >= max_h:
        return "STALE", f"age_h={age_h:.2f} key={key} last={d[key]}"
    # progress across the window: total now vs the last line written at or before now - max_h
    if "anchors_total_logged" not in d:
        return "UNREADABLE", f"age_h={age_h:.2f} but the last line has no anchors_total_logged (progress cannot be judged)"
    old = [x for x in rows if key in x and parse_utc(x[key]) <= now - max_h * 3600 and "anchors_total_logged" in x]
    if not old:
        return "YOUNG_LOG", (f"age_h={age_h:.2f}; no line older than {max_h:g} h in the last 400 lines to anchor the progress window — progress "
                             f"cannot be judged yet (a known state for a new queue; still counted, not a pass)")
    t_new, t_old = int(d["anchors_total_logged"]), int(old[-1]["anchors_total_logged"])
    if t_new <= t_old:
        return "STALE_NO_PROGRESS", (f"age_h={age_h:.2f} key={key} last={d[key]} but anchors_total_logged {t_old} (at {old[-1][key]}) -> {t_new}: "
                                     f"no new anchor in {max_h:g} h — the runner is writing lines without doing anything")
    return "FRESH", f"age_h={age_h:.2f} key={key} last={d[key]} total {t_old} (at {old[-1][key]}) -> {t_new}"


def main(argv):
    args = [a for a in argv[1:]]
    max_h = float(args[args.index("--max-age-h") + 1]) if "--max-age-h" in args else 30.0
    timeout = float(args[args.index("--timeout") + 1]) if "--timeout" in args else 10.0
    paths = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--max-age-h", "--timeout"))]
    if not paths:
        print("FORWARD_FRESHNESS RED n_red=1 (no path given — an empty check is not a pass)"); return 1
    red = 0
    for p in paths:
        v, detail = one(p, max_h, timeout)
        red += v != "FRESH"
        d = p if os.path.isdir(p) else os.path.dirname(p)
        e = os.path.join(d, "launchd.err")                      # dlarch 2026-09-25: a non-empty launchd.err (start-up self-check) is worth reporting
        if os.path.isfile(e) and not (getattr(os.stat(e), "st_flags", 0) & SF_DATALESS) and os.path.getsize(e) > 0:
            txt = open(e, "rb").read()[-200000:].decode("utf-8", "replace")
            hard = [w for w in ("Traceback", "AssertionError", "Error:") if w in txt]
            detail += f" | launchd.err non-empty ({os.path.getsize(e)} B)" + (f" RED: contains {hard}" if hard else " (warnings only, reported)")
            if hard and v == "FRESH":
                v = "ERR_CONTENT"; red += 1
        print(f"FRESHNESS {p} {v} {detail}", flush=True)
    print(f"FORWARD_FRESHNESS {'OK' if not red else 'RED'} n_red={red} max_age_h={max_h:g} now={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    return 0 if not red else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
