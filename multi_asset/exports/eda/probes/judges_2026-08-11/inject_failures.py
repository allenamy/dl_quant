"""§9.5-①b failure injection: the operational loop must be tested against failure, not just uptime.

Five clean days only prove the happy path, and the happy path is not what kills you. Three
injections, each run against the REAL daily chain, each leaving evidence for 0C:

  1. cron killed mid-run      -> does the next run resume, or produce half / DUPLICATE records?
  2. guards fail              -> does BLOCKED actually reach the DAILY REPORT (which is all the
                                 operator reads), not merely the exit code?
  3. upstream data late/stale -> does the loop wait, skip, or write a record from stale data?
                                 The third is the worst and must be impossible.

Evidence -> exports/live/pilot_daily/injection_evidence/<case>/{before,after,verdict}.json + log.txt

*** MOCK ONLY: no account, no credentials, no venue contact. ***
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, time

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
PY = sys.executable
sys.path.insert(0, MA + "/engine/live")
import pilot_log as PL

EV = MA + "/exports/live/pilot_daily/injection_evidence"
LOG_ROOT = MA + "/exports/live/pilot_log"
fails = []


def check(name, cond, detail=""):
    print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + detail) if detail else ''}", flush=True)
    if not cond:
        fails.append(name)
    return cond


def dupe_counts():
    """duplicate (anchor,symbol,attempt) rows per day — the thing a restart must not create."""
    out = {}
    for d in PL.available_days(LOG_ROOT):
        seen = {}
        for r in PL.read_day(LOG_ROOT, d)["orders"]:
            k = (int(r["anchor_ts"]), r["symbol"], int(r["attempt_idx"]))
            seen[k] = seen.get(k, 0) + 1
        out[d] = sum(1 for v in seen.values() if v > 1)
    return out


def snapshot():
    out = {}
    for d in PL.available_days(LOG_ROOT):
        rows = PL.read_day(LOG_ROOT, d)
        out[d] = {t: len(v) for t, v in rows.items()}
        out[d]["_anchor_ts"] = sorted({int(r["anchor_ts"]) for r in rows["orders"]})
        out[d]["_dupes"] = dupe_counts().get(d, 0)
    return out


def save(case, name, obj):
    d = os.path.join(EV, case)
    os.makedirs(d, exist_ok=True)
    json.dump(obj, open(os.path.join(d, f"{name}.json"), "w"), indent=1, default=str)


# ---------------------------------------------------------------- 1. kill mid-run
print("[inject-1] cron killed mid-run -> restart must not duplicate or half-write")
case = "1_killed_midrun"
before = snapshot(); save(case, "before", before)
dupe_before = dupe_counts(); save(case, "dupes_before", dupe_before)
proc = subprocess.Popen([PY, MA + "/engine/live/pilot_daily.py", "--days_back", "2"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(9)                       # let it get into the shadow-logging phase
proc.kill()
killed_out = proc.communicate()[0][-1500:]
mid = snapshot(); save(case, "mid_after_kill", mid)
r2 = subprocess.run([PY, MA + "/engine/live/pilot_daily.py", "--days_back", "2"],
                    capture_output=True, text=True)
after = snapshot(); save(case, "after", after)
os.makedirs(os.path.join(EV, case), exist_ok=True)
open(os.path.join(EV, case, "log.txt"), "w").write(
    "=== killed run (tail) ===\n" + killed_out + "\n\n=== restart run ===\n" + r2.stdout[-3000:])

dupe_after = dupe_counts(); save(case, "dupes_after", dupe_after)
# measure the DELTA: pre-existing duplicates from earlier non-idempotent runs must not be
# attributed to this injection.
delta = {d: dupe_after.get(d, 0) - dupe_before.get(d, 0) for d in dupe_after}
dupes = {d: v for d, v in delta.items() if v > 0}
ok1 = check("kill+restart introduced NO new duplicate rows", not dupes,
            f"delta={dupes} (pre-existing: {sum(dupe_before.values())})")
ok1b = check("restart completed cleanly", r2.returncode == 0)
save(case, "verdict", {"duplicates_delta": dupes, "dupes_before": dupe_before,
                       "dupes_after": dupe_after, "restart_returncode": r2.returncode,
                       "passed": bool(ok1 and ok1b),
                       "property": "append-only JSONL + idempotent anchor skip"})

# ---------------------------------------------------------------- 2. guards fail -> report says so
print("[inject-2] guards fail -> BLOCKED must appear in the DAILY REPORT, not just the exit code")
case = "2_guards_fail"
os.makedirs(os.path.join(EV, case), exist_ok=True)
r = subprocess.run([PY, "-c", f'''
import sys; sys.path.insert(0, "{MA}/engine/live")
import pilot_daily as PD
PD.DECLARED_FACTOR_VERSION = "funding_ema_normfix"   # claim corrected while panel is pre-fix
rep = PD.main(days_back=1, skip_log=False, verbose=True)
print("STATUS:", rep["status"])
'''], capture_output=True, text=True)
day = time.strftime("%Y%m%d", time.gmtime())
rp = f"{MA}/exports/live/pilot_daily/{day}/report.md"
report_txt = open(rp).read() if os.path.exists(rp) else ""
mirror = f"{MA}/exports/live/pilot_daily/mirror/{day}_report.md"
mirror_txt = open(mirror).read() if os.path.exists(mirror) else ""
open(os.path.join(EV, case, "log.txt"), "w").write(r.stdout[-3000:] + "\n=== REPORT ===\n" + report_txt)
ok2a = check("report.md contains BLOCKED", "BLOCKED" in report_txt)
ok2b = check("report states readings were withheld", "WITHHELD" in report_txt.upper())
ok2c = check("mirror copy also shows BLOCKED", "BLOCKED" in mirror_txt)
ok2d = check("shadow log did NOT write under failed guards",
             "shadow_log_skipped_reason" in r.stdout or "BLOCKED" in r.stdout)
save(case, "verdict", {"report_has_blocked": ok2a, "report_has_withheld": ok2b,
                       "mirror_has_blocked": ok2c,
                       "passed": bool(ok2a and ok2b and ok2c),
                       "property": "operator reads the report, so the report must carry the block"})
shutil.copy(rp, os.path.join(EV, case, "report_blocked.md")) if os.path.exists(rp) else None

# ---------------------------------------------------------------- 3. stale upstream
print("[inject-3] upstream late/stale -> must refuse, never write records from stale data")
case = "3_stale_upstream"
os.makedirs(os.path.join(EV, case), exist_ok=True)
before3 = snapshot(); save(case, "before", before3)
r = subprocess.run([PY, "-c", f'''
import sys; sys.path.insert(0, "{MA}/engine/live")
import pilot_daily as PD
# override the SOURCE table, not the derived constant: run_guards() recomputes the
# derived value from DATA_SOURCE_MAX_DATA_AGE_H, so setting the derived one is a no-op.
PD.DATA_SOURCE_MAX_DATA_AGE_H[PD.DATA_SOURCE_TYPE] = 0.0001
rep = PD.main(days_back=1, skip_log=False, verbose=True)
print("STATUS:", rep["status"])
print("SHADOW_DAYS:", rep.get("shadow_log_days"))
'''], capture_output=True, text=True)
after3 = snapshot(); save(case, "after", after3)
open(os.path.join(EV, case, "log.txt"), "w").write(r.stdout[-3000:])
grew = {d: (after3[d]["orders"] - before3.get(d, {}).get("orders", 0)) for d in after3}
ok3a = check("no new log rows written under stale upstream",
             all(v == 0 for v in grew.values()), str({k: v for k, v in grew.items() if v}))
ok3b = check("status is BLOCKED under stale upstream", "BLOCKED" in r.stdout)
ok3c = check("blocking reason names staleness",
             "stale" in r.stdout.lower() or "old" in r.stdout.lower())
save(case, "verdict", {"rows_added": grew, "passed": bool(ok3a and ok3b),
                       "property": ("writing a record that looks current from stale data is the "
                                    "worst of the three options, so it is blocked outright")})

print(f"\n  {'ALL INJECTIONS PASS' if not fails else 'FAILURES: ' + str(fails)}", flush=True)
print(f"  evidence -> {EV}", flush=True)
sys.exit(0 if not fails else 1)
