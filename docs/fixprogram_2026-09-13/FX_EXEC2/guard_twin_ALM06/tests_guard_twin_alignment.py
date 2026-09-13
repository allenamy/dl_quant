"""ALM-06 (FX-EXEC2, 2026-09-13): guard_twin compares DAY over the SAME two time points for both twins, and CUM between the
arithmetic twin (the watchdog's own chain on daily_nav) and the watchdog; the watchdog's history-worst day is named so.

*** OFFLINE, NO VENUE: imports guard_twin.py from THIS directory (a copy) and calls only its pure helpers; never main().
    Inputs are copies: state/compare.jsonl (the rows the RUNNING twin wrote — the old code's outputs), state/snapshots.jsonl,
    state/income.jsonl (guard_twin copy 14:44Z) and daily_nav rows of the 14:27Z ledger copy (argv[1] = its pilot_log). ***

ASSERTED:
  [PRE] the recorded rows of the running (old) twin carry 37 DAY and 8 CUM disagreement lines — the red evidence.
  [D1] for every recorded DAY line, the aligned comparator on the inputs that existed at that run gives |twin − arith| ≤ TOL
       (or is not alignable, named) ⇒ 0 DAY lines.
  [D2] sensitivity: a real 1% equity gap at the end reference still fires.
  [C1] the arithmetic twin of the watchdog chain reproduces the watchdog's recorded cum at every recorded CUM line (8/8)
       ⇒ 0 CUM lines.
  [C2] sensitivity: a daily_nav row the watchdog did not see (nav −2%) makes the arithmetic twin disagree.
  [F] compare records carry wd_worst_day_pct_history and wd_recent_day_pct; the shadow block reads recent_day_pct.
Exit 0 = all pass.
"""
import calendar, copy, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import guard_twin as GT   # noqa: E402  (module import creates nothing but ST if absent; main() is never called)
ROOT = sys.argv[1]
FAILS, N = [], [0]


def check(name, cond, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(detail)[:300]) if detail != '' else ''}", flush=True)
    if not cond:
        FAILS.append(name)


def jl(p): return [json.loads(l) for l in open(p) if l.strip()]
cmp_rows = jl(os.path.join(HERE, "state", "compare.jsonl"))
snaps = jl(os.path.join(HERE, "state", "snapshots.jsonl"))
inc = jl(os.path.join(HERE, "state", "income.jsonl"))
dn = {}
for d in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, d, "daily_nav.jsonl")
    if d.isdigit() and os.path.exists(p):
        dn[d] = jl(p)
T = lambda u: calendar.timegm(time.strptime(u, "%Y-%m-%dT%H:%M:%SZ"))   # noqa: E731
day_rows = [c for c in cmp_rows if any(x.startswith("DAY") for x in c.get("disagreements") or [])]
cum_rows = [c for c in cmp_rows if any(x.startswith("CUM") for x in c.get("disagreements") or [])]
print("[PRE] recorded outputs of the running twin")
check("PRE the running twin wrote 37 DAY and 8 CUM disagreement lines", len(day_rows) == 37 and len(cum_rows) == 8,
      (len(day_rows), len(cum_rows)))

print("\n[D] DAY over aligned time points")
fire, na, worst = 0, 0, 0.0
for c in day_rows:
    t = T(c["utc"])
    tw, ar, det = GT.aligned_day_pct([s for s in snaps if s["ts"] <= t + 1], dn, time.strftime("%Y%m%d", time.gmtime(t)), t, inc)
    if tw is None or ar is None:
        na += 1
        continue
    worst = max(worst, abs(tw - ar))
    fire += abs(tw - ar) > GT.TOL["day_pct"]
check("★★★ D1 0 of the recorded DAY lines survive alignment (not alignable, named: ≤2)", fire == 0 and na <= 2,
      {"fire": fire, "not_alignable": na, "max_abs_diff_pp": round(worst, 3)})
c = [r for r in day_rows if r["utc"] == "2026-09-12T12:59:54Z"][0]
t = T(c["utc"])
sub = [s for s in snaps if s["ts"] <= t + 1]
tw0, ar0, det0 = GT.aligned_day_pct(sub, dn, "20260912", t, inc)
end = GT.nearest_snapshot(sub, [r for r in dn["20260912"] if r["nav_ts"] <= t][-1]["nav_ts"])
bumped = [dict(s, equity=s["equity"] * 0.99) if s is end else s for s in sub]
tw1, ar1, _ = GT.aligned_day_pct(bumped, dn, "20260912", t, inc)
check("★★ D2 a real 1% equity gap at the end reference still fires (and the unperturbed case does not)",
      abs(tw0 - ar0) <= GT.TOL["day_pct"] and abs(tw1 - ar1) > GT.TOL["day_pct"], (round(tw0 - ar0, 3), round(tw1 - ar1, 3), det0))

print("\n[C] CUM: arithmetic twin of the watchdog chain")
match = [(r["utc"], GT.wd_chain_arith_pct(dn, T(r["utc"])), r["wd_cum_from_start_pct"]) for r in cum_rows]
check("★★★ C1 the arithmetic twin reproduces the watchdog's recorded cum at every recorded CUM line ⇒ 0 CUM lines",
      all(a is not None and abs(a - w) <= GT.TOL["cum_pct"] and abs(a - w) < 1e-3 for _, a, w in match), match)
dn2 = copy.deepcopy(dn)
t8 = T(cum_rows[-1]["utc"])
_endday = max(d for d in dn2 if any(float(r["nav_ts"]) <= t8 for r in dn2[d] if r.get("nav_ts") is not None))
_endrow = [r for r in dn2[_endday] if float(r["nav_ts"]) <= t8][-1]
_endrow["nav"] = float(_endrow["nav"]) * 0.98      # the chain telescopes, so only an END close (or a flow day) moves it
check("★★ C2 a final daily_nav close the watchdog did not see (−2%) makes the arithmetic twin disagree",
      abs(GT.wd_chain_arith_pct(dn2, t8) - cum_rows[-1]["wd_cum_from_start_pct"]) > GT.TOL["cum_pct"],
      GT.wd_chain_arith_pct(dn2, t8))

print("\n[F] field names")
src = open(os.path.join(HERE, "guard_twin.py")).read()
check("F1 the compare record names the history-worst day and today's day; the shadow block reads recent_day_pct",
      '"wd_worst_day_pct_history": c2.get("worst_day_pct")' in src and '"wd_recent_day_pct": c2.get("recent_day_pct")' in src
      and '_wd_day = c2.get("recent_day_pct")' in src)
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS:
    print("FAILED:", *FAILS, sep="\n  ")
    sys.exit(1)
print("ALL PASS")
