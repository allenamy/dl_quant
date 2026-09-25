#!/usr/bin/env python3
"""Per-anchor acceptance item (lead 2026-09-25): FORWARD-LOG FRESHNESS. For each forward run log (dlarch's long `parabolic_onset_forward` and
the short queue; a directory means <dir>/run_log.jsonl), the time of its LAST line must be < --max-age-h (default 30) hours before now.
Read-only and hang-proof: the research repo is iCloud-synced and its files are evicted to placeholders (measured 2026-09-25: reads blocked
for > 10 min) — a placeholder (SF_DATALESS) is reported UNREADABLE without reading it, and the tail is read in a child process with a timeout.
The line's time is its `run_utc` (the key the forward runner writes; `utc` / `ts` accepted as fallbacks, named in the output).
Output: one line per log `FRESHNESS <path> FRESH|STALE|UNREADABLE age_h=… key=… last=…`, then `FORWARD_FRESHNESS OK|RED n_red=k`; exit 0 / 1.
A non-empty launchd.err next to the log (dlarch: the short queue's start-up self-check fails into it) is REPORTED on the log's line (not a red by itself).
Paths (2026-09-25): short queue ~/parabolic_onset_forward_short/run_log.jsonl (launchd com.hsy.onsetfwd_short, daily 07:22Z); long queue
~/Desktop/quant_research/multi_asset/exports/live/parabolic_onset_forward/run_log.jsonl until dlarch moves it to
~/pof_long/multi_asset/exports/live/parabolic_onset_forward/run_log.jsonl (then REPLACE, never keep both — the old path stops updating).
usage: /usr/bin/python3 nc_forward_freshness.py <path> [<path> ...] [--max-age-h 30] [--timeout 10]"""
import calendar, json, os, subprocess, sys, time

SF_DATALESS = 0x40000000
TAIL = ("import sys\nf = open(sys.argv[1], 'rb'); f.seek(0, 2); n = f.tell(); f.seek(max(0, n - 65536)); b = f.read()\n"
        "ls = [l for l in b.decode('utf-8', 'replace').splitlines() if l.strip()]\nprint(ls[-1] if ls else '')")


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
    line = r.stdout.strip()
    if r.returncode != 0 or not line:
        return "UNREADABLE", f"no last line (rc {r.returncode}) {r.stderr.strip()[:120]}"
    try:
        d = json.loads(line)
    except ValueError:
        return "UNREADABLE", "last line is not JSON"
    key = next((k for k in ("run_utc", "utc", "ts") if k in d), None)
    if key is None:
        return "UNREADABLE", f"last line has no run_utc/utc/ts (keys {sorted(d)[:12]})"
    age_h = (time.time() - parse_utc(d[key])) / 3600.0
    return ("FRESH" if age_h < max_h else "STALE"), f"age_h={age_h:.2f} key={key} last={d[key]}"


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
            detail += f" | REPORT launchd.err non-empty ({os.path.getsize(e)} B)"
        print(f"FRESHNESS {p} {v} {detail}", flush=True)
    print(f"FORWARD_FRESHNESS {'OK' if not red else 'RED'} n_red={red} max_age_h={max_h:g} now={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    return 0 if not red else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
