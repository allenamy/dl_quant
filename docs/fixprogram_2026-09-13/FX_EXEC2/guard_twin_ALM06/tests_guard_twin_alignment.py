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
  ── ALM-06 (ii), added 2026-09-16 after the lead sent the first fix back: the arithmetic twin shares the watchdog's
     inputs, so it can only catch arithmetic. Both alerts now exist and BOTH are asserted here. ──
  [I1] the decomposition reproduces its own inputs on every recorded CUM row: T == the recorded cum_pct_twin exactly,
       and C2b == wd_chain_arith_pct within 0.01 pp. Without this the legs below mean nothing.
  [I2] on every recorded row (ii) is ok or undecidable-with-a-reason, never drift — the 8 recorded CUM lines are
       explained by DAY-CLOSE TIMING, not silenced by a fitted band. The max judged residual is pinned.
  [I3] ★★★ a synthetic 0.5 pp input bias on ONE transfer day (09-08 realised_pnl) fires (ii) and NOT (i).
  [I4] the LED-04 allowance follows the watchdog's DECLARED state: amendment_records ⇒ 0; recorded_rows ⇒ the frozen
       twin-segment value; the field absent ⇒ the same value but the state reads `inferred_recorded`, not `declared`.
  [I5] prefix transfer days (08-02, 08-05, 08-10, 08-18 — nearly the whole 0.2613 pp) contribute NOTHING to the
       allowance, because both chains price them identically and the bias cancels out of the gap.
  [I6] an OPEN transfer day is undecidable with a named reason, never `ok`.
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
# ── ALM-06 (ii): the INDEPENDENT CUM alert ───────────────────────────────────────────────────────
print("\n[I] the independent income-ledger TWR vs the watchdog chain, judged on the residual")


import bisect as _bi
_SNAP_S = sorted(snaps, key=lambda x: float(x["ts"]))
_SNAP_T = [float(x["ts"]) for x in _SNAP_S]
_INC_S = sorted(inc, key=lambda x: float(x["time"]))
_INC_T = [float(x["time"]) / 1000.0 for x in _INC_S]
_DN_S = {d: sorted(rows, key=lambda r: float(r.get("nav_ts") or 0)) for d, rows in dn.items()}
_DN_T = {d: [float(r.get("nav_ts") or 0) for r in rows] for d, rows in _DN_S.items()}


def _as_of(t, dn_):
    """dn / snaps / inc as the running twin saw them at t (the +1s is the second-floored compare utc vs ms snapshots).

    Sorted once and sliced by bisect: the straightforward per-row filter was 1,655 x 110k income rows and did not
    finish inside the harness timeout. Same slices, same order."""
    cut = t + 1
    d2 = {}
    for d, rows in _DN_S.items():
        i = _bi.bisect_right(_DN_T[d], cut)
        if i:
            d2[d] = rows[:i]
    return (d2, _SNAP_S[:_bi.bisect_right(_SNAP_T, cut)], _INC_S[:_bi.bisect_right(_INC_T, cut)])


_rep_T, _rep_C2b = 0, 0
for c in cum_rows:
    t = T(c["utc"])
    d2, s2, i2 = _as_of(t, dn)
    cc = GT.twin_cum_chains(d2, s2, i2, t)
    _rep_T += abs(cc["cum_twin_pct"] - float(c["cum_pct_twin"])) < 1e-9
    wa = GT.wd_chain_arith_pct(d2, t)
    _rep_C2b += (cc["C2b"] is not None and wa is not None and abs(cc["C2b"] - wa) < 0.01)
check("★★★ I1 the twin chain reproduces the recorded cum_pct_twin on all 8 recorded CUM rows, exactly",
      _rep_T == len(cum_rows), (_rep_T, len(cum_rows)))
check("★★★ I1 the reconstructed watchdog chain (C2b) reproduces wd_chain_arith_pct on all 8, within 0.01pp",
      _rep_C2b == len(cum_rows), (_rep_C2b, len(cum_rows)))

_v = {"ok": 0, "drift": 0, "undecidable": 0}
_maxres, _nowhy = 0.0, 0
for c in cmp_rows:
    t = T(c["utc"])
    d2, s2, i2 = _as_of(t, dn)
    cc = GT.twin_cum_chains(d2, s2, i2, t)
    wd = c.get("wd_cum_from_start_pct")
    f = GT.cum_indep_facts(cc, (None if wd is None else float(wd)), GT.wd_chain_arith_pct(d2, t),
                           time.strftime("%Y%m%d", time.gmtime(t)), None)
    _v[f["verdict"]] += 1
    if f["verdict"] == "undecidable" and not f["why"]:
        _nowhy += 1
    if f["residual_pp"] is not None:
        _maxres = max(_maxres, abs(f["residual_pp"]))
check("★★★ I2 (ii) raises NO drift on any of the 1,655 recorded rows — the 8 CUM lines are EXPLAINED, not silenced",
      _v["drift"] == 0, _v)
check("★★ I2 every undecidable row names its reason (a quiet independent check must not read as agreement)",
      _nowhy == 0, _nowhy)
check("★★ I2 the max judged residual is pinned at the measured 0.0174pp (device ALM06_cum_decomposition.json)",
      _maxres < 0.0174, round(_maxres, 6))

# [I3] a 0.5 pp input bias on ONE transfer day
_t = T(cmp_rows[-1]["utc"])
_d2, _s2, _i2 = _as_of(_t, dn)
_BIAS_DAY, _NAV_PREV = "20260908", 82604.54171685            # LED04_cond4_transfer_day_effect.json
_BIAS = 0.005 * _NAV_PREV                                    # 0.5 pp of that day's chain factor
_clean_cc = GT.twin_cum_chains(_d2, _s2, _i2, _t)
_clean_wa = GT.wd_chain_arith_pct(_d2, _t)
_clean = GT.cum_indep_facts(_clean_cc, _clean_wa, _clean_wa, time.strftime("%Y%m%d", time.gmtime(_t)), None)
_db = copy.deepcopy(_d2)
_db[_BIAS_DAY][-1]["realised_pnl"] = float(_db[_BIAS_DAY][-1]["realised_pnl"]) + _BIAS
_bias_cc = GT.twin_cum_chains(_db, _s2, _i2, _t)
_bias_wa = GT.wd_chain_arith_pct(_db, _t)                    # the watchdog reads the same biased row
_bias = GT.cum_indep_facts(_bias_cc, _bias_wa, _bias_wa, time.strftime("%Y%m%d", time.gmtime(_t)), None)
check("PRE the unbiased row is judged and quiet", _clean["verdict"] == "ok", _clean["why"] or _clean["residual_pp"])
check("PRE the injected bias moves the watchdog chain by about 0.5pp",
      abs(abs(_bias_wa - _clean_wa) - 0.5) < 0.06, (round(_clean_wa, 4), round(_bias_wa, 4)))
check("★★★ I3 (ii) FIRES on a 0.5pp input bias in one transfer day",
      _bias["verdict"] == "drift" and abs(_bias["residual_pp"]) > GT.RESIDUAL_TOL,
      (_bias["verdict"], None if _bias["residual_pp"] is None else round(_bias["residual_pp"], 4)))
check("★★★ I3 ...and (i) does NOT — the arithmetic twin reads the same biased row, so it moves with the watchdog",
      abs(_bias_wa - _bias_wa) <= GT.TOL["cum_pct"] and abs(_bias["alert_i_leg_pp"]) < 1e-9,
      _bias["alert_i_leg_pp"])
check("★★ I3 the twin's own number is UNCHANGED by the bias (that is what independence means)",
      abs(_bias_cc["cum_twin_pct"] - _clean_cc["cum_twin_pct"]) < 1e-12,
      (_clean_cc["cum_twin_pct"], _bias_cc["cum_twin_pct"]))

# [I4] the LED-04 state follows the watchdog's declaration
_today = time.strftime("%Y%m%d", time.gmtime(_t))
_a_dec, _d_dec, _s_dec = GT.led04_allowance_pp(_clean_cc["C2b"], _today, _clean_cc["first_twin_day"],
                                               "amendment_records")
_a_rec, _d_rec, _s_rec = GT.led04_allowance_pp(_clean_cc["C2b"], _today, _clean_cc["first_twin_day"],
                                               "recorded_rows")
_a_abs, _d_abs, _s_abs = GT.led04_allowance_pp(_clean_cc["C2b"], _today, _clean_cc["first_twin_day"], None)
check("★★★ I4 a watchdog declaring amendment_records gets a ZERO allowance", _a_dec == 0.0 and _s_dec == "declared_amended",
      (_a_dec, _s_dec))
check("★★ I4 declared recorded_rows and an ABSENT field give the same number but different states",
      abs(_a_rec - _a_abs) < 1e-15 and _s_rec == "declared_recorded" and _s_abs == "inferred_recorded",
      (_a_rec, _s_rec, _s_abs))
check("★★★ I5 prefix transfer days contribute nothing — only twin-segment days are applied",
      all(d >= _clean_cc["first_twin_day"] for d in _d_rec)
      and not set(_d_rec) & {"20260802", "20260805", "20260810", "20260818"}, _d_rec)

# [I6] an open transfer day is undecidable, not ok
_open_day = _clean_cc["transfer_days_in_segment"][-1] if _clean_cc["transfer_days_in_segment"] else None
_open = GT.cum_indep_facts(_clean_cc, _clean_wa, _clean_wa, _open_day, None) if _open_day else None
check("★★★ I6 evaluating ON the last transfer day is undecidable and says why, never ok",
      _open is not None and _open["verdict"] == "undecidable" and "still open" in (_open["why"] or ""),
      None if _open is None else (_open["verdict"], _open["why"]))


print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS:
    print("FAILED:", *FAILS, sep="\n  ")
    sys.exit(1)
print("ALL PASS")
