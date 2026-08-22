"""GUARD CALIBER PROPERTY TESTS — every §4 watchdog quantity re-derived BY HAND from ACCOUNT TRUTH,
plus the three caliber properties, each with a "must go red" in-memory mutant of the production source.

*** MOCK ONLY: no account, no credentials, no venue contacted. Every tree is a tempdir. Production
    sources are READ (and mutated in memory only); `sys.dont_write_bytecode` is set before the first
    import so the suite leaves nothing behind in the live repo. ***

WHY (docs/DESIGN_optimization_path_2026-08-21.md §2.2, ERROR_LEDGER E-0821-A)
  The 2026-08-21 12:16Z false trip: §4-2 read (realised_today + unrealised_now)/nav = -4.52% while the
  account's equity had moved -2.96%, because yesterday's unrealised loss was already in today's equity
  and was counted again. FIVE suites were green: their fixtures were written by the same mind as the
  guard — the loss lived only in the P&L columns, nav never moved. So the guard and its tests agreed
  about a quantity that was not the account. The repair is structural: (1) every fixture here is built
  from ACCOUNT TRUTH by one identity, nav_t = nav_{t-1} + d_realised + d_unrealised + d_flow (the
  producer's own semantics: scheduler/anchor_loop.py daily_nav writer; docs/FIELD_CALIBERS_2026-08-19.md);
  (2) the expected number is written as an explicit formula beside the assertion, not produced by a
  second copy of the guard; (3) every property carries a mutant that re-installs a plausible defect and
  is REQUIRED to go red — a property that no mutant can violate is decoration.

THE THREE PROPERTIES (P1-P3), stated once, applied to §4-2 (cond2) and §4-4 (cond4)
  P1 DAY-SPLIT INVARIANCE  the same equity path read through 1 / 3 / 6 snapshot rows per day gives the
     same reading (cond2, cond4); and for cond4 the cumulative return from start is invariant to WHERE the
     day boundaries are cut (telescoping: prod(nav_d/nav_{d-1}) = nav_end/nav_start), the start day pinned.
     Not claimed: cond2's worst-day over a RE-CUT path (a different partition is a different rule), and
     cut-invariance ACROSS a transfer day (B33 prices a transfer day as a daily approximation by design).
  P2 TRANSFER INVARIANCE   insert a deposit / a withdrawal (nav jumps, external_flow_usdt != 0, P&L
     columns unchanged) into a RETURN path: cond2 names the day UNKNOWN and every other day's reading is
     unchanged; cond4's cumulative is unchanged (the transfer day is priced from P&L, the chain continues
     from the post-transfer nav). P2b: the recorded flow AMOUNT is deliberately WRONG (half the truth,
     ERROR_LEDGER B-family "unreliable on deposit days") and nothing changes — the amount never enters.
  P3 CARRY INVARIANCE      yesterday's unrealised -X carried into today with no change today reads 0 for
     today, not -X/nav (E-0821-A exactly); appending N flat days to a path changes cond4 by nothing.

WHAT IS ASSERTED PER GUARD (section letter in the output)
  [A] cond2  hand-derived 5-day account path (funding day, multi-row day, deposit day, truncated day,
             multi-row day) — worst / n_priced / flow_days / truncated_days / per-day readings via a
             2-day probe; plus the 2026-08-21 incident replay (-2.96%, not -4.52%: alert, no trip).
  [B] cond2  P1 (mutants: read the day's FIRST row [B31]; SUM the day's rows [FIELD_CALIBERS misread]),
             P2 (mutants: transfers ignored; prev-close not advanced on a transfer day),
             P3 (mutant: the retired (realised+unrealised)/nav caliber — E-0821-A).
  [C] cond4  hand-derived same 5-day path: cum = (9800/10000)*(1+98/9800)*(14454/14898) - 1 etc.
  [D] cond4  P1 (mutants: level-sum accumulator [the retired cond4]; first row per day),
             P2 (mutants: nav-ratio on a transfer day; flow AMOUNT enters; transfer day skipped),
             P3 (mutant: level-sum accumulator).
  [E] cond4b hand-derived (target 2.0x from config: alert 3.0x / halt 5.0x; legacy rows out of scope;
             last row of the day) + property UNIT INVARIANCE (nav and gross scaled together by 1e-3 /
             1e3 leave the reading unchanged) — mutant: gross taken from the retired P0 constant 25000.
  [F] per_name_stop  hand-derived (depth = unrealised/|notional|, a SHORT at -30%, a dust name, the
             -25% boundary, 2-anchor persistence, exit -> cool-off timestamp) + properties: a single
             needle does not trigger / only consecutive anchors do / recovery resets to ZERO / a missing
             readback resets — mutants: sticky counter; unseen names not reset; signed notional
             (kills the short side); single-anchor trigger.
  [G] cond1  hand-derived per-day net c (fee + SIGNED slip / filled notional): 10.0 / 4.0 / 9.0 bps
             days; unpriced tail day keeps the streak — mutants: `>=` at the limit; calendar-day streak.
  [H] cond3  hand-derived notional-weighted adverse markout on stress anchors only (15.0 / 17.5 bps,
             coverage 4/5) and a 27.5 bps trip — mutant: min-selector (the 2026-07-29 defect).
  [I] cond5  5a outage event; 5b hand-derived quantity residual (clean / within-tolerance / 300 USDT
             anomaly, unexplained_frac 300/700) — mutant: sign on expected_qty (reconcile); 5c reject
             fraction over SUBMITTED orders only (6/10, 5/10 => 2-anchor hit) — mutants: never-sent rows
             in the denominator; `>` at the 0.5 line; 5e hand-derived dev 100/1000, split can_speak,
             underfill 10%, and a 250 USDT ghost => unauth 25% => flatten via split_unauth.
  [J] cond6  hand-derived corr = 1 - mawe*100 per ELIGIBLE anchor (N=40: 1.0 / 0.8), pooled -0.35 on a
             mixed day, 3-day underfill breach = ALARM with the firing-order premise checked — mutant:
             eligibility on every anchor (halted anchor pooled in).
  [K] cond7  hand-derived fail-rate streak incl. the 0.05 boundary, drift tri-state, and
             derive_ops_stats from a tree (2/20 = 0.10 with never-sent rows excluded) — mutants: `>=`
             at the limit; never-sent rows in the denominator.
  [Z] the on-disk sources are byte-identical before and after (mutants are in-memory only).

NOT COVERED HERE (stated, not hidden): §4-5d (out of the realtime layer by design); §4-5c error-code
fast path (no producer — the watchdog itself says so); cond3/cond5e/cond6 get hand-derived tests but
their PROPERTY set is the P1-P3 trio only where the quantity is an equity path; the four flow/truncation
edge cases already pinned by tests_watchdog [4] / tests_numerator_honesty are not duplicated.

Exit 0 = all pass.  Run from live/ (`python3 tests_guard_calibers.py`) or from anywhere with
PYTHONPATH=<live>:<repo>.
"""
import sys
sys.dont_write_bytecode = True          # ★ before the first import: this suite writes NOTHING into live/
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                 # when this file lives in live/ (the battery layout)
import pilot_log as PL                   # noqa: E402
import pilot_metrics as PM               # noqa: E402
import watchdog as WD                    # noqa: E402
import watchdog_inputs as WI             # noqa: E402
import reconcile as RC                   # noqa: E402
import position_break as PB              # noqa: E402
import per_name_stop as PNS              # noqa: E402

WD_PATH, RC_PATH, WI_PATH, PNS_PATH = (os.path.abspath(m.__file__) for m in (WD, RC, WI, PNS))
LIVE_DIR = os.path.dirname(WD_PATH)
REPO = os.path.dirname(LIVE_DIR)
BOOK_CFG = os.path.join(REPO, "config", "book.json")

FAILS, N = [], [0]
TMPS = []
MUTANT_LEDGER = []                       # (mutant name, went red?)


def check(name, cond, extra=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(extra)) if extra != '' else ''}",
          flush=True)
    if not cond:
        FAILS.append(name)


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


SHA0 = {p: _sha(p) for p in (WD_PATH, RC_PATH, WI_PATH, PNS_PATH)}


def _pyc_snapshot():
    """{pyc filename: mtime} under live/__pycache__ — this run must not add to or touch it."""
    d = os.path.join(LIVE_DIR, "__pycache__")
    if not os.path.isdir(d):
        return {}
    return {f: os.path.getmtime(os.path.join(d, f)) for f in sorted(os.listdir(d))}


PYC0 = _pyc_snapshot()


def mutant(path, edits, name):
    """The production source, mutated IN MEMORY (never on disk), loaded as a fresh module.

    `edits` = [(find, replace), ...]; every `find` must match exactly once, so a drifted anchor
    string makes the suite raise instead of silently testing an unmutated module (the same reason
    tests_numerator_honesty asserts the match count). Lifted from that suite, generalised to N edits."""
    src = open(path).read()
    for find, repl in edits:
        n = src.count(find)
        if n != 1:
            raise AssertionError(f"mutant {name!r}: anchor matched {n} times, not 1: {find[:70]!r}")
        src = src.replace(find, repl)
    spec = importlib.util.spec_from_file_location(f"_mut_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"_mut_{name}"] = mod
    exec(compile(src, path, "exec"), mod.__dict__)
    return mod


def must_red(name, prop, mod, extra=""):
    """A property test run against a mutant MUST fail (or crash). Crash counts as red, and is named."""
    try:
        ok, det = prop(mod)
        red = not ok
        why = det
    except Exception as e:                                         # noqa: BLE001
        red, why = True, f"(mutant crashed: {type(e).__name__}: {str(e)[:60]})"
    MUTANT_LEDGER.append((name, red))
    check(f"★ mutant {name!r} goes RED", red, f"{why}{('  ' + str(extra)) if extra else ''}")


def must_hold(name, prop, mod=WD):
    ok, det = prop(mod)
    check(name, ok, det)


def near(a, b, tol=1e-9):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


# ══════════════════════════════════════════════════════════════════════════════════════════════
# fixtures: daily_nav rows FROM ACCOUNT TRUTH
# ══════════════════════════════════════════════════════════════════════════════════════════════
T0 = 1785542400.0            # 2026-07-31T16:00:00Z; each row gets a later nav_ts so position = time
D = ["20260801", "20260802", "20260803", "20260804", "20260805", "20260806", "20260807",
     "20260808", "20260809", "20260810"]


def write_nav(root, day, rows):
    lg = PL.PilotLogger(root, day=day)
    try:
        for r in rows:
            lg.daily_nav(**r)
    finally:
        lg.close()


def truth_tree(start_nav, days, *, start_unreal=0.0, gross_mult=2.0, policy="constant_leverage_2.00",
               flow_record=None):
    """Write daily_nav rows obeying the ACCOUNT IDENTITY  nav_t = nav_{t-1} + d_real + d_unreal + d_flow.

    days  = [(day, steps[, opts])]; steps = [(d_real, d_unreal, d_flow), ...] — one ROW per step;
            [] writes ONE flat snapshot (a 00:16Z row on a day nothing has moved yet).
    Columns follow the producer: realised_pnl and external_flow_usdt are SINCE-MIDNIGHT cumulatives
    (reset at each day), unrealised_pnl and nav are LEVELS, nav_ts increases row by row.
    `flow_record(true_cum_flow) -> recorded value` lets a test record an UNRELIABLE flow amount (P2b).
    Returns (root, truth) with truth[day] = {open, close, unreal_close, real, flow, trunc, n_rows}."""
    root = tempfile.mkdtemp(prefix="gc_")
    TMPS.append(root)
    nav, unreal = float(start_nav), float(start_unreal)
    truth, k = {}, 0
    for spec in days:
        day, steps = spec[0], list(spec[1]) or [(0.0, 0.0, 0.0)]
        opts = spec[2] if len(spec) > 2 else {}
        trunc = bool(opts.get("trunc", False))
        real_cum = flow_cum = 0.0
        opening, rows = nav, []
        for d_real, d_unreal, d_flow in steps:
            real_cum += d_real
            unreal += d_unreal
            flow_cum += d_flow
            nav = nav + d_real + d_unreal + d_flow
            k += 1
            rows.append(dict(day=day, target_gross=gross_mult * nav, nav=nav,
                             realised_pnl=real_cum, unrealised_pnl=unreal,
                             external_flow_usdt=(flow_cum if flow_record is None
                                                 else flow_record(flow_cum)),
                             realised_truncated=trunc, sizing_policy=policy,
                             nav_ts=T0 + k * 3600.0))
        write_nav(root, day, rows)
        truth[day] = {"open": opening, "close": nav, "unreal_close": unreal, "real": real_cum,
                      "flow": flow_cum, "trunc": trunc, "n_rows": len(rows)}
    return root, truth


def halve(steps):
    """Each step split into two half-steps: the same end-of-day state through twice the rows."""
    out = []
    for a, b, c in steps:
        out.append((a / 2.0, b / 2.0, c / 2.0))
        out.append((a / 2.0, b / 2.0, c / 2.0))
    return out


def last_only(steps):
    """One row per day: the end-of-day state only (the sum of the steps)."""
    return [(sum(s[0] for s in steps), sum(s[1] for s in steps), sum(s[2] for s in steps))]


def ev(mod, root, ve=None, ops=None):
    return mod.evaluate(root, venue_events=(ve or []), ops_stats=(ops or []))


def c2c4(mod, root):
    e = ev(mod, root)
    return e["conditions"]["cond2_day_loss"], e["conditions"]["cond4_drawdown"], e


def probe_day(mod, root, prev_day, day):
    """ONE day's §4-2 reading, isolated: a 2-day sub-tree [prev_day's LAST row, day's rows].

    cond2 publishes only `worst_day_pct`, so the per-day value is read through this probe: the
    window's first day reads its intraday change (one row => 0.0, or UNKNOWN if it is a transfer /
    truncated day), and the second day reads (its last nav - prev last nav)/prev — the same number it
    has inside the full window. worst = min over the priced pair."""
    sub = tempfile.mkdtemp(prefix="gc_probe_")
    TMPS.append(sub)
    write_nav(sub, prev_day, [PL.read_day(root, prev_day)["daily_nav"][-1]])
    write_nav(sub, day, PL.read_day(root, day)["daily_nav"])
    return ev(mod, sub)["conditions"]["cond2_day_loss"]


print("[0] sources under test")
print(f"  watchdog={WD_PATH}\n  reconcile={RC_PATH}\n  watchdog_inputs={WI_PATH}\n  per_name_stop={PNS_PATH}")
_cfg = json.load(open(BOOK_CFG))
check("target_leverage and per_name_stop are read from the live config (read-only) — the hand "
      "derivations below use THESE numbers", _cfg.get("target_leverage") == 2.0
      and (_cfg.get("per_name_stop") or {}).get("depth_pct") == -0.25
      and (_cfg.get("per_name_stop") or {}).get("consecutive_anchors") == 2,
      f"target_leverage={_cfg.get('target_leverage')} per_name_stop={_cfg.get('per_name_stop')}")

# ══════════════════════════════════════════════════════════════════════════════════════════════
# [A] cond2 — hand-derived from a 5-day ACCOUNT path
# ══════════════════════════════════════════════════════════════════════════════════════════════
print("\n[A] §4-2 cond2 — the 5-day account path, hand-derived")
# D1 funding day: 0 -> 10,000 by TRANSFER (the pilot's own first day: priced as 0 / a flow day)
# D2 three rows: flat 00:16Z; 08:16Z -40 realised -60 unrealised (nav 9,900); 20:16Z a further
#    -10/-90 (nav 9,800: realised since midnight -50, unrealised level -150)
# D3 deposit day: flat row; then +98 realised AND +5,000 TRANSFER in one snapshot (nav 14,898)
# D4 truncated day (income ledger hit the page cap): one row, -100 / -198 => nav 14,600, flagged
# D5 two rows: flat; then -46 realised, unrealised -348 -> -448 => nav 14,454
_root5, _t5 = truth_tree(0.0, [
    (D[0], [(0.0, 0.0, 10000.0)]),
    (D[1], [(0.0, 0.0, 0.0), (-40.0, -60.0, 0.0), (-10.0, -90.0, 0.0)]),
    (D[2], [(0.0, 0.0, 0.0), (98.0, 0.0, 5000.0)]),
    (D[3], [(-100.0, -198.0, 0.0)], {"trunc": True}),
    (D[4], [(0.0, 0.0, 0.0), (-46.0, -100.0, 0.0)]),
])
check("PRE-ASSERT the fixture IS the path described (closes 10000 / 9800 / 14898 / 14600 / 14454)",
      [_t5[d]["close"] for d in D[:5]] == [10000.0, 9800.0, 14898.0, 14600.0, 14454.0],
      [_t5[d]["close"] for d in D[:5]])
_c2, _c4, _ev5 = c2c4(WD, _root5)
# hand derivation, cond2 caliber [B32] = (last nav of day - last nav of previous day)/previous:
#   D1 transfer -> UNKNOWN (named);  D2 (9800-10000)/10000 = -2.00%;  D3 transfer -> UNKNOWN;
#   D4 truncated -> UNKNOWN (named; its nav 14600 still becomes the next day's base);
#   D5 (14454-14600)/14600 = -1.00%   => worst -2.00, priced 2 of 5
EXP_D2, EXP_D5 = (9800.0 - 10000.0) / 10000.0 * 100.0, (14454.0 - 14600.0) / 14600.0 * 100.0
check("★★ worst_day_pct = -2.00% (D2), NOT the day with the biggest realised loss and NOT -3.42% "
      "((-46-448)/14454, the retired caliber on D5)", near(_c2["worst_day_pct"], EXP_D2),
      f"worst={_c2['worst_day_pct']} expected={EXP_D2}")
check("   2 priced days of 5; transfer days NAMED [D1, D3]; truncated day NAMED [D4]",
      _c2["n_priced_days"] == 2 and _c2["n_days"] == 5 and _c2["flow_days"] == [D[0], D[2]]
      and _c2["truncated_days"] == [D[3]] and _c2["n_days_flow_excluded"] == 2,
      {k: _c2[k] for k in ("n_priced_days", "flow_days", "truncated_days")})
check("   no trip (-2.00 > -4.0), no investigate (-2.00 > -2.68), degraded (a truncated day exists)",
      _c2["triggered"] is False and _c2["investigate"] is False and _c2["degraded"] is True
      and _c2["blind"] is False and _c2["partial"] is True,
      {k: _c2[k] for k in ("triggered", "investigate", "degraded", "blind", "partial")})
# per-day, through the 2-day probe. expected worst of [prev last row, day]:
#   prev contributes 0.0 (one row => intraday 0) unless prev is a transfer/truncated day (UNKNOWN)
_probe_exp = {D[1]: min(0.0, EXP_D2),       # D1 is a transfer day => UNKNOWN; D2 alone => -2.00
              D[2]: 0.0,                    # D2 one-row 0.0; D3 transfer => UNKNOWN => worst 0.0, priced 1
              D[3]: 0.0,                    # D3 UNKNOWN (transfer); D4 truncated UNKNOWN => nothing priced
              D[4]: EXP_D5}                 # D4 UNKNOWN (truncated); D5 = -1.00 exactly
for _prev, _day in zip(D[:4], D[1:5]):
    _p = probe_day(WD, _root5, _prev, _day)
    _e = _probe_exp[_day]
    if _day == D[3]:
        check(f"   probe [{_prev},{_day}]: transfer then truncated => nothing priced (blind), both named",
              _p["blind"] is True and _p["flow_days"] == [D[2]] and _p["truncated_days"] == [D[3]],
              {k: _p[k] for k in ("worst_day_pct", "flow_days", "truncated_days")})
    else:
        check(f"   probe [{_prev},{_day}]: worst = {_e:+.4f}% by hand",
              near(_p["worst_day_pct"], _e), f"worst={_p['worst_day_pct']}")

print("\n[A] §4-2 — the 2026-08-21 12:16Z incident, replayed on the account's numbers")
# prev close 15,889.5; day start unrealised -329.0; at 12:16Z realised -108.9, unrealised -587.8,
# equity 15,418.6. The account moved (15418.6-15889.5)/15889.5 = -2.9636%: INVESTIGATE, no trip.
# The retired caliber read (-108.9-587.8)/15418.6 = -4.5185% and flattened 108 names.
_inc = tempfile.mkdtemp(prefix="gc_inc_")
TMPS.append(_inc)
write_nav(_inc, "20260820", [dict(day="20260820", target_gross=31779.0, nav=15889.5, realised_pnl=-60.0,
                                  unrealised_pnl=-329.0, external_flow_usdt=0.0, nav_ts=T0 + 1.0)])
write_nav(_inc, "20260821", [dict(day="20260821", target_gross=31760.0, nav=15880.0, realised_pnl=0.0,
                                  unrealised_pnl=-320.0, external_flow_usdt=0.0, nav_ts=T0 + 2.0),
                             dict(day="20260821", target_gross=30837.0, nav=15418.6, realised_pnl=-108.9,
                                  unrealised_pnl=-587.8, external_flow_usdt=0.0, nav_ts=T0 + 3.0)])
_ci = ev(WD, _inc)["conditions"]["cond2_day_loss"]
INC_EXP = (15418.6 - 15889.5) / 15889.5 * 100.0
check("★★★ the incident day reads -2.9636% (equity day change), not -4.5185%",
      near(_ci["worst_day_pct"], INC_EXP, 1e-9), f"worst={_ci['worst_day_pct']} expected={INC_EXP:.4f}")
check("★★★ => ALERT (investigate, < -2.68) and NO TRIP (> -4.0) — the book stays",
      _ci["investigate"] is True and _ci["triggered"] is False,
      {k: _ci[k] for k in ("investigate", "triggered")})

# ══════════════════════════════════════════════════════════════════════════════════════════════
# [B] cond2 — properties P1 / P2 / P3 and their mutants
# ══════════════════════════════════════════════════════════════════════════════════════════════
print("\n[B] §4-2 cond2 — P1 day-split invariance (1 / 3 / 6 rows per day, same end-of-day state)")
# a path with intraday texture on every day, realised and unrealised both moving, both signs
STEPS = {D[1]: [(-30.0, -70.0, 0.0), (20.0, -10.0, 0.0), (-60.0, 15.0, 0.0)],      # -135 => 9865
         D[2]: [(0.0, -120.0, 0.0), (45.0, 30.0, 0.0), (-10.0, -5.0, 0.0)],         # -60  => 9805
         D[3]: [(-80.0, -40.0, 0.0), (25.0, -5.0, 0.0), (10.0, 90.0, 0.0)]}         # 0    => 9805


def split_trees(transform):
    return truth_tree(10000.0, [(D[0], [])] + [(d, transform(STEPS[d])) for d in (D[1], D[2], D[3])])


def prop_c2_P1(mod):
    """cond2 readings identical for 1 / 3 / 6 rows per day; and equal to the hand value."""
    outs = []
    for tf in (last_only, lambda s: s, halve):
        root, _ = split_trees(tf)
        c = ev(mod, root)["conditions"]["cond2_day_loss"]
        outs.append((c["worst_day_pct"], c["n_priced_days"], c["triggered"], c["investigate"]))
    # by hand: D1 one row => 0.0; D2 (9865-10000)/10000 = -1.35; D3 (9805-9865)/9865; D4 0.0
    exp = min(0.0, -1.35, (9805.0 - 9865.0) / 9865.0 * 100.0, 0.0)
    same = all(near(o[0], outs[0][0]) and o[1:] == outs[0][1:] for o in outs)
    ok = same and near(outs[0][0], exp) and outs[0][1] == 4
    return ok, f"1/3/6 rows -> {[round(o[0], 6) for o in outs]} priced={[o[1] for o in outs]} hand={exp:.6f}"


must_hold("★★ P1 holds: 1 / 3 / 6 rows per day read the same worst (-1.35%) and the same 4 priced days",
          prop_c2_P1)
_m_first = mutant(WD_PATH, [("            n0 = nav[-1]", "            n0 = nav[0]")], "cond2_first_row_B31")
must_red("cond2_first_row_B31 (the day's FIRST snapshot: the 2026-07-28 staleness defect)", prop_c2_P1, _m_first)
_m_sum = mutant(WD_PATH, [(
    "                per_day_loss.append((float(_navv) - float(_prev_day_nav)) / float(_prev_day_nav) * 100.0)",
    "                per_day_loss.append(sum((float(_r[\"nav\"]) - float(_prev_day_nav)) for _r in nav "
    "if _r.get(\"nav\") is not None) / float(_prev_day_nav) * 100.0)")], "cond2_sum_rows")
must_red("cond2_sum_rows (adds the day's progress snapshots: the 08-20 misread in FIELD_CALIBERS)",
         prop_c2_P1, _m_sum)

print("\n[B] §4-2 cond2 — P2 transfer invariance (deposit, withdrawal, and an unreliable flow amount)")
# a RETURN path: D1 start 10,000; D2 -1.5%; D3 +0.8%; D4 -0.4%; D5 -2.2%  (worst = D5, never D3)
RET = [None, -0.015, +0.008, -0.004, -0.022]
ALPHA = [None, 0.40, 0.30, 0.25, 0.50]          # realised share of each day's P&L; the rest unrealised


def return_path(flow_on_d3=0.0, flow_record=None):
    """Steps derived from RETURNS so that a transfer on D3 leaves every day's return unchanged."""
    nav, days = 10000.0, [(D[0], [])]
    for i in range(1, 5):
        pnl = RET[i] * nav
        steps = [(ALPHA[i] * pnl, (1.0 - ALPHA[i]) * pnl, flow_on_d3 if i == 2 else 0.0)]
        days.append((D[i], steps))
        nav = nav + pnl + (flow_on_d3 if i == 2 else 0.0)
    return truth_tree(10000.0, days, flow_record=flow_record)


def prop_c2_P2(mod, flow, flow_record=None):
    rA, _ = return_path()
    rB, tB = return_path(flow, flow_record)
    a = ev(mod, rA)["conditions"]["cond2_day_loss"]
    b = ev(mod, rB)["conditions"]["cond2_day_loss"]
    exp = -2.2                                   # the worst day is D5 in both trees, by construction
    ok = (near(a["worst_day_pct"], exp) and near(b["worst_day_pct"], exp)
          and a["n_priced_days"] == 5 and b["n_priced_days"] == 4
          and a["flow_days"] == [] and b["flow_days"] == [D[2]]
          and a["triggered"] is False and b["triggered"] is False
          and a["investigate"] is False and b["investigate"] is False)
    return ok, (f"no-transfer worst={a['worst_day_pct']:.4f} priced={a['n_priced_days']} | "
                f"transfer {flow:+.0f} worst={b['worst_day_pct']} priced={b['n_priced_days']} "
                f"flow_days={b['flow_days']} trig={b['triggered']}")


must_hold("★★ P2 deposit +5,000 on D3: D3 UNKNOWN and named, worst unchanged (-2.2% = D5), 5 -> 4 priced",
          lambda m: prop_c2_P2(m, +5000.0))
must_hold("★★ P2 withdrawal -2,955 (-30%) on D3: same — the day after reads from the post-withdrawal nav",
          lambda m: prop_c2_P2(m, -2955.0))
must_hold("★ P2b the recorded flow amount is HALF the truth: reading unchanged (the amount never enters)",
          lambda m: prop_c2_P2(m, +5000.0, flow_record=lambda f: 0.5 * f))
_m_noflow = mutant(WD_PATH, [(
    "                _flow_day = any(abs(float(_r.get(\"external_flow_usdt\") or 0.0)) > 1e-9 for _r in nav)",
    "                _flow_day = False")], "cond2_transfers_ignored")
must_red("cond2_transfers_ignored on a DEPOSIT (the day is priced at +51% and not named)",
         lambda m: prop_c2_P2(m, +5000.0), _m_noflow)
must_red("cond2_transfers_ignored on a WITHDRAWAL (reads -29% and TRIPS — the dangerous direction)",
         lambda m: prop_c2_P2(m, -2955.0), _m_noflow)
_m_prev = mutant(WD_PATH, [(
    "            if _navv is not None:\n                _prev_day_nav = float(_navv)",
    "            if _navv is not None and not _flow_day:\n                _prev_day_nav = float(_navv)")],
    "cond2_prev_not_advanced_on_transfer")
must_red("cond2_prev_not_advanced_on_transfer (the day AFTER a withdrawal reads -29.5% against the old base)",
         lambda m: prop_c2_P2(m, -2955.0), _m_prev)

print("\n[B] §4-2 cond2 — P3 carry invariance (yesterday's unrealised is not today's loss)")


def prop_c2_P3(mod):
    # D1: one row, unrealised -300 already in equity (nav 9,700). D2: nothing moves.
    rA, _ = truth_tree(9700.0, [(D[0], []), (D[1], [])], start_unreal=-300.0)
    # E-0821-A shape: D2 CLOSES the position: realised -300, unrealised 0, nav unchanged
    rB, _ = truth_tree(9700.0, [(D[0], []), (D[1], [(-300.0, 300.0, 0.0)])], start_unreal=-300.0)
    a = ev(mod, rA)["conditions"]["cond2_day_loss"]
    b = ev(mod, rB)["conditions"]["cond2_day_loss"]
    ok = (near(a["worst_day_pct"], 0.0) and near(b["worst_day_pct"], 0.0)
          and a["triggered"] is False and b["triggered"] is False
          and a["investigate"] is False and b["investigate"] is False)
    return ok, f"carried: worst={a['worst_day_pct']} | closed-out: worst={b['worst_day_pct']}"


must_hold("★★★ P3 holds: carried -300 unrealised reads 0.0% today; closing it out reads 0.0% too", prop_c2_P3)
_m_old2 = mutant(WD_PATH, [(
    "                per_day_loss.append((float(_navv) - float(_prev_day_nav)) / float(_prev_day_nav) * 100.0)",
    "                per_day_loss.append((float(real) + float(unreal)) / float(_navv) * 100.0)")],
    "cond2_retired_caliber_E0821A")
must_red("cond2_retired_caliber_E0821A ((realised+unrealised)/nav: reads -3.09% on a day nothing moved)",
         prop_c2_P3, _m_old2)
must_red("cond2_retired_caliber_E0821A also breaks the hand-derived 5-day path (D2 -2.04 / D5 -3.42)",
         lambda m: (near(ev(m, _root5)["conditions"]["cond2_day_loss"]["worst_day_pct"], EXP_D2),
                    ev(m, _root5)["conditions"]["cond2_day_loss"]["worst_day_pct"]), _m_old2)
must_red("cond2_retired_caliber_E0821A trips the incident replay (-4.52% < -4.0)",
         lambda m: (ev(m, _inc)["conditions"]["cond2_day_loss"]["triggered"] is False,
                    ev(m, _inc)["conditions"]["cond2_day_loss"]["worst_day_pct"]), _m_old2)

# ══════════════════════════════════════════════════════════════════════════════════════════════
# [C] cond4 — hand-derived on the same 5-day path
# ══════════════════════════════════════════════════════════════════════════════════════════════
print("\n[C] §4-4 cond4 — the same 5-day account path, hand-derived (B33: TWR from STARTING equity)")
# start = D1 close 10,000 (the funding day is the first priced day, prices as 0);
# D2 ordinary: 9800/10000;  D3 TRANSFER: (realised 98 + unrealised -150 - prev unrealised -150)/9800
#    = +1.00% (NOT the +52% nav jump);  D4 truncated: withheld, the chain spans it by nav ratio;
# D5: 14454/14898 across the hole.   cum = 0.98 * 1.01 * 14454/14898 - 1
EXP_CUM = ((9800.0 / 10000.0) * (1.0 + 98.0 / 9800.0) * (14454.0 / 14898.0) - 1.0) * 100.0
check(f"★★ cum_return_from_start_pct = {EXP_CUM:.4f}% by hand",
      near(_c4["cum_return_from_start_pct"], EXP_CUM, 1e-3) and near(_c4["max_drawdown_pct"], EXP_CUM, 1e-3),
      f"cum={_c4['cum_return_from_start_pct']} judged={_c4['max_drawdown_pct']}")
check("   4 of 5 days priced (coverage 0.8, not thin), truncated D4 withheld and NAMED, chain intact",
      _c4["priced_coverage"] == 0.8 and _c4["coverage_thin"] is False and _c4["chain_broken"] is False
      and _c4["n_days_truncated_withheld"] == 1 and _c4["truncated_days_withheld"] == [D[3]]
      and _c4["unpriced_flow_days"] == [],
      {k: _c4[k] for k in ("priced_coverage", "coverage_thin", "chain_broken", "truncated_days_withheld")})
check("   no trip, not blind; peak-DD info equals cum here (the path never rose above start)",
      _c4["triggered"] is False and _c4["blind"] is False
      and near(_c4["max_drawdown_from_peak_pct_INFO"], EXP_CUM, 1e-3),
      {k: _c4[k] for k in ("triggered", "blind", "max_drawdown_from_peak_pct_INFO")})
check("   the trigger text names the caliber nowhere (nothing fired) and the detail names it",
      "STARTING" in _c4["drawdown_caliber"] and not any("§4-4 " in t for t in _ev5["triggers"]),
      _ev5["triggers"])

# ══════════════════════════════════════════════════════════════════════════════════════════════
# [D] cond4 — properties P1 / P2 / P3 and their mutants
# ══════════════════════════════════════════════════════════════════════════════════════════════
print("\n[D] §4-4 cond4 — P1 cut invariance (the same path cut into different days; start day pinned)")
PATH9 = STEPS[D[1]] + STEPS[D[2]] + STEPS[D[3]]            # nine steps, net -195 => 9805


def cut_tree(cut):
    """Day 1 = the start snapshot alone (the START is the first priced day's close, so it is pinned);
    the nine steps are then partitioned by `cut` (a list of day lengths summing to 9)."""
    days, i, k = [(D[0], [])], 0, 1
    for n in cut:
        days.append((D[k], PATH9[i:i + n]))
        i += n
        k += 1
    assert i == 9, cut
    return truth_tree(10000.0, days)


def prop_c4_P1(mod):
    outs = []
    for cut in ([9], [3, 3, 3], [1] * 9, [4, 5], [2, 2, 2, 2, 1]):
        root, _ = cut_tree(cut)
        outs.append(ev(mod, root)["conditions"]["cond4_drawdown"]["cum_return_from_start_pct"])
    exp = (9805.0 / 10000.0 - 1.0) * 100.0                 # telescoping: nav_end / nav_start
    ok = all(near(o, outs[0], 1e-6) for o in outs) and near(outs[0], exp, 1e-3)
    return ok, f"cuts [9]/[3,3,3]/[1]*9/[4,5]/[2,2,2,2,1] -> {outs} hand={exp:.4f}"


def prop_c4_P1_rows(mod):
    outs = []
    for tf in (last_only, lambda s: s, halve):
        root, _ = split_trees(tf)
        outs.append(ev(mod, root)["conditions"]["cond4_drawdown"]["cum_return_from_start_pct"])
    exp = (9805.0 / 10000.0 - 1.0) * 100.0
    ok = all(near(o, outs[0], 1e-6) for o in outs) and near(outs[0], exp, 1e-3)
    return ok, f"1/3/6 rows per day -> {outs} hand={exp:.4f}"


must_hold("★★ P1 holds: five different day cuts of one path give one cumulative (-1.95%)", prop_c4_P1)
must_hold("★★ P1 holds: 1 / 3 / 6 rows per day give one cumulative (-1.95%)", prop_c4_P1_rows)
_m_levels = mutant(WD_PATH, [(
    "                _rd = float(_navv) / _pn - 1.0",
    "                _rd = (float(_r3.get(\"realised_pnl\") or 0.0) + float(_r3.get(\"unrealised_pnl\") or 0.0)) / float(_navv)")],
    "cond4_level_sum_accumulator")
must_red("cond4_level_sum_accumulator (the retired cond4: (realised_d + unrealised LEVEL_d)/nav_d — counts "
         "the carried unrealised once per cut day)", prop_c4_P1, _m_levels)
_m_first4 = mutant(WD_PATH, [("        _by_day[str(_r0[\"day\"])] = _r0",
                              "        _by_day.setdefault(str(_r0[\"day\"]), _r0)")], "cond4_first_row_per_day")
must_red("cond4_first_row_per_day (the day's FIRST snapshot is not its close)", prop_c4_P1_rows, _m_first4)

print("\n[D] §4-4 cond4 — P2 transfer invariance")


def prop_c4_P2(mod, flow, flow_record=None):
    rA, _ = return_path()
    rB, _ = return_path(flow, flow_record)
    a = ev(mod, rA)["conditions"]["cond4_drawdown"]
    b = ev(mod, rB)["conditions"]["cond4_drawdown"]
    exp = ((1 - 0.015) * (1 + 0.008) * (1 - 0.004) * (1 - 0.022) - 1.0) * 100.0
    ok = (near(a["cum_return_from_start_pct"], exp, 1e-3) and near(b["cum_return_from_start_pct"], exp, 1e-3)
          and a["chain_broken"] is False and b["chain_broken"] is False
          and b["unpriced_flow_days"] == [] and b["blind"] is False and b["triggered"] is False)
    return ok, (f"no-transfer cum={a['cum_return_from_start_pct']} | transfer {flow:+.0f} "
                f"cum={b['cum_return_from_start_pct']} hand={exp:.4f} broken={b['chain_broken']}")


must_hold("★★ P2 deposit +5,000 on D3: cum unchanged (-3.28%); D3's own +0.8% priced from P&L",
          lambda m: prop_c4_P2(m, +5000.0))
must_hold("★★ P2 withdrawal -2,955 on D3: cum unchanged", lambda m: prop_c4_P2(m, -2955.0))
must_hold("★ P2b the recorded flow amount is HALF the truth: cum unchanged (the amount never enters)",
          lambda m: prop_c4_P2(m, +5000.0, flow_record=lambda f: 0.5 * f))
_m_navratio = mutant(WD_PATH, [("                _rd = (float(_re) + float(_un) - float(_pu)) / _pn",
                                "                _rd = float(_navv) / _pn - 1.0")], "cond4_nav_ratio_on_transfer_day")
must_red("cond4_nav_ratio_on_transfer_day (prices the +5,000 jump as +51.6% return)",
         lambda m: prop_c4_P2(m, +5000.0), _m_navratio)
_m_amount = mutant(WD_PATH, [("                _rd = (float(_re) + float(_un) - float(_pu)) / _pn",
                              "                _rd = (float(_navv) - _flow) / _pn - 1.0")], "cond4_flow_amount_enters")
must_red("cond4_flow_amount_enters (correct only while the ledger's amount is exact; wrong on P2b)",
         lambda m: prop_c4_P2(m, +5000.0, flow_record=lambda f: 0.5 * f), _m_amount)
_m_skip = mutant(WD_PATH, [("                _rd = (float(_re) + float(_un) - float(_pu)) / _pn",
                            "                _rd = 0.0")], "cond4_transfer_day_skipped")
must_red("cond4_transfer_day_skipped (treats the deposit day like a hole: its +0.8% P&L vanishes)",
         lambda m: prop_c4_P2(m, +5000.0), _m_skip)

print("\n[D] §4-4 cond4 — P3 carry invariance")


def prop_c4_P3(mod):
    # D1 10,000 / D2 -300 unrealised (nav 9,700) / D3..D6 nothing moves, -300 carried every day
    r2, _ = truth_tree(10000.0, [(D[0], []), (D[1], [(0.0, -300.0, 0.0)])])
    r6, _ = truth_tree(10000.0, [(D[0], []), (D[1], [(0.0, -300.0, 0.0)])] + [(D[i], []) for i in range(2, 6)])
    a = ev(mod, r2)["conditions"]["cond4_drawdown"]["cum_return_from_start_pct"]
    b = ev(mod, r6)["conditions"]["cond4_drawdown"]["cum_return_from_start_pct"]
    ok = near(a, -3.0, 1e-6) and near(b, -3.0, 1e-6)
    return ok, f"2-day cum={a} | +4 flat days cum={b} (hand: -3.0 both; level-sum would read -15.37)"


must_hold("★★★ P3 holds: -300 carried over four flat days is -3.0%, not -3.0% x 5", prop_c4_P3)
must_red("cond4_level_sum_accumulator (re-counts the carried -300 every day: -15.4%)", prop_c4_P3, _m_levels)
must_red("cond4_level_sum_accumulator breaks the hand-derived 5-day path too",
         lambda m: (near(ev(m, _root5)["conditions"]["cond4_drawdown"]["cum_return_from_start_pct"], EXP_CUM, 1e-3),
                    ev(m, _root5)["conditions"]["cond4_drawdown"]["cum_return_from_start_pct"]), _m_levels)
must_red("cond4_nav_ratio_on_transfer_day breaks the hand-derived 5-day path (D3 +52%)",
         lambda m: (near(ev(m, _root5)["conditions"]["cond4_drawdown"]["cum_return_from_start_pct"], EXP_CUM, 1e-3),
                    ev(m, _root5)["conditions"]["cond4_drawdown"]["cum_return_from_start_pct"]), _m_navratio)
_m_trunc4 = mutant(WD_PATH, [("    _nav_use = [r for r in _nav_all if not r.get(\"realised_truncated\")]",
                              "    _nav_use = list(_nav_all)")], "cond4_truncation_ignored")
# ★ this mutant cannot move the NUMBER on this path: D4's nav is exact and the chain spans the hole by nav
#   ratio, so pricing D4 telescopes to the same cum. What it moves is the COVERAGE (4/5 -> 5/5): a
#   withheld day that is silently priced reads as full coverage. Asserted on that field, honestly.
must_red("cond4_truncation_ignored (D4 silently priced: priced_coverage 0.8 -> 1.0; the cum itself is "
         "unchanged here because the nav chain spans the hole exactly — tests_numerator_honesty's claim, re-asserted)",
         lambda m: (ev(m, _root5)["conditions"]["cond4_drawdown"]["priced_coverage"] == 0.8,
                    ev(m, _root5)["conditions"]["cond4_drawdown"]["priced_coverage"]), _m_trunc4)

# ══════════════════════════════════════════════════════════════════════════════════════════════
# [E] cond4b — effective leverage: hand-derived + unit invariance
# ══════════════════════════════════════════════════════════════════════════════════════════════
print("\n[E] §4-4b cond4b — effective leverage, hand-derived (target 2.0x => alert 3.0x / halt 5.0x)")
LEV_TGT = float(_cfg["target_leverage"])


def lev_tree(scale=1.0, d3_gross=44800.0):
    """D1 legacy constant-GROSS row (25,000 on 4,600 = 5.43x): OUT OF SCOPE by policy stamp.
    D2 two rows: 30,000/15,000 = 2.000 then 30,000/14,500 = 2.069 (the LAST row is the day's).
    D3 d3_gross/14,000 (44,800 => 3.2x: above alert 3.0, below halt 5.0)."""
    root = tempfile.mkdtemp(prefix="gc_lev_")
    TMPS.append(root)
    write_nav(root, D[0], [dict(day=D[0], target_gross=25000.0 * scale, nav=4600.0 * scale, realised_pnl=0.0,
                                unrealised_pnl=0.0, sizing_policy="constant_gross_legacy", nav_ts=T0 + 1)])
    write_nav(root, D[1], [dict(day=D[1], target_gross=30000.0 * scale, nav=15000.0 * scale, realised_pnl=0.0,
                                unrealised_pnl=0.0, sizing_policy="constant_leverage_2.00", nav_ts=T0 + 2),
                           dict(day=D[1], target_gross=30000.0 * scale, nav=14500.0 * scale, realised_pnl=-500.0 * scale,
                                unrealised_pnl=0.0, sizing_policy="constant_leverage_2.00", nav_ts=T0 + 3)])
    write_nav(root, D[2], [dict(day=D[2], target_gross=d3_gross * scale, nav=14000.0 * scale, realised_pnl=-500.0 * scale,
                                unrealised_pnl=0.0, sizing_policy="constant_leverage_2.00", nav_ts=T0 + 4)])
    return root


def lev_of(mod, root):
    return ev(mod, root)["conditions"]["cond4b_leverage"]


_lv = lev_of(WD, lev_tree())
check("★★ actual_leverage = 44800/14000 = 3.2 (the newest in-scope row), target read as 2.0",
      near(_lv["actual_leverage"], round(44800.0 / 14000.0, 3), 1e-9) and _lv["target_leverage"] == LEV_TGT,
      {k: _lv[k] for k in ("actual_leverage", "target_leverage")})
check("   alert_above = 2.0 x 1.5 = 3.0 and halt_above = 2.0 x 2.5 = 5.0 => investigate, NOT triggered",
      _lv["alert_above"] == round(LEV_TGT * 1.5, 2) and _lv["halt_above"] == round(LEV_TGT * 2.5, 2)
      and _lv["investigate"] is True and _lv["triggered"] is False and _lv["blind"] is False,
      {k: _lv[k] for k in ("alert_above", "halt_above", "investigate", "triggered")})
check("   per_day = [(D2, 2.069 = 30000/14500 — the LAST row, not 2.0), (D3, 3.2)]; legacy D1 out of scope, named",
      [tuple(x) for x in _lv["per_day"]] == [(D[1], round(30000.0 / 14500.0, 3)), (D[2], round(44800.0 / 14000.0, 3))]
      and _lv["n_days_out_of_scope"] == 1 and _lv["out_of_scope_days"] == [D[0]],
      {k: _lv[k] for k in ("per_day", "out_of_scope_days")})
_lvh = ev(WD, lev_tree(d3_gross=71400.0))
check("   71400/14000 = 5.1 > 5.0 => TRIGGERED and the trigger names §4-4b (and nothing else fires on this tree)",
      _lvh["conditions"]["cond4b_leverage"]["triggered"] is True
      and any("§4-4b" in t for t in _lvh["triggers"]) and len(_lvh["triggers"]) == 1, _lvh["triggers"])


def prop_lev_units(mod):
    """nav and target_gross scaled together by 1e-3 and 1e3: every published field identical."""
    base = lev_of(mod, lev_tree(1.0))
    outs = [lev_of(mod, lev_tree(s)) for s in (1e-3, 1e3)]
    keys = ("actual_leverage", "investigate", "triggered", "blind", "n_days_out_of_scope")
    ok = all(o[k] == base[k] for o in outs for k in keys) and all(
        [tuple(x) for x in o["per_day"]] == [tuple(x) for x in base["per_day"]] for o in outs)
    return ok, f"x1 {base['actual_leverage']} | x1e-3 {outs[0]['actual_leverage']} | x1e3 {outs[1]['actual_leverage']}"


must_hold("★★ UNIT INVARIANCE holds: the account in milli-units or kilo-units reads the same leverage",
          prop_lev_units)
_m_p0 = mutant(WD_PATH, [("        _lev_rows.append((str(_r4.get(\"day\")), float(_g4) / float(_n4)))",
                          "        _lev_rows.append((str(_r4.get(\"day\")), 25000.0 / float(_n4)))")],
               "cond4b_gross_from_retired_P0_constant")
must_red("cond4b_gross_from_retired_P0_constant (gross_usdt_pilot_p0 instead of the row's gross: a unit-bearing "
         "constant — reads 1786x in milli-units)", prop_lev_units, _m_p0)
_m_scope = mutant(WD_PATH, [("        if not str(_r4.get(\"sizing_policy\") or \"\").startswith(\"constant_leverage\"):",
                             "        if False:")], "cond4b_scope_dropped")
must_red("cond4b_scope_dropped (the 5.43x constant-gross row enters per_day and is no longer named out of scope)",
         lambda m: (lev_of(m, lev_tree())["n_days_out_of_scope"] == 1 and len(lev_of(m, lev_tree())["per_day"]) == 2,
                    lev_of(m, lev_tree())["per_day"]), _m_scope)
must_red("cond4_first_row_per_day also breaks cond4b (D2 would read 2.000, the opening row)",
         lambda m: ([tuple(x) for x in lev_of(m, lev_tree())["per_day"]][0] == (D[1], round(30000.0 / 14500.0, 3)),
                    lev_of(m, lev_tree())["per_day"]), _m_first4)

# ══════════════════════════════════════════════════════════════════════════════════════════════
# [F] per_name_stop — hand-derived + properties
# ══════════════════════════════════════════════════════════════════════════════════════════════
print("\n[F] per_name_stop — depth = unrealised/|notional|, -25% on 2 consecutive final-anchor readbacks")
# ★ 2026-08-22: the hand derivations below are for the BASE clause (−25% × 2 × 7d). per_name_stop now
#   carries profiles (active_profile=wide ⇒ −30% for the wide book — a PRODUCTION switch). The base
#   profile is INJECTED here instead of reading whatever profile the disk happens to activate: a
#   suite whose subject flips with the operator's switch would lock the switch out. The wide profile
#   itself is asserted in tests_external_book [P] (−28%×2 does not fire, −31%×2 does).
CFG = PNS.resolve_profile(dict(json.load(open(BOOK_CFG))["per_name_stop"], active_profile=None))
S0 = {"counters": {}, "stopped": {}, "cooldown": {}}


def snap(notional, unreal):
    return {"positions_notional": dict(notional), "positions_unrealized": dict(unreal)}


# anchor 1: AAA long 100 at -30 (-30%: counts); BBB SHORT -200 at -40 (-20%: does not); CCC 10 at -9
#           (-90% but |notional| < 20 => dust, ignored); DDD 300 at -75 (-25.0% exactly: <= line, counts)
A1 = snap({"AAAUSDT": 100.0, "BBBUSDT": -200.0, "CCCUSDT": 10.0, "DDDUSDT": 300.0},
          {"AAAUSDT": -30.0, "BBBUSDT": -40.0, "CCCUSDT": -9.0, "DDDUSDT": -75.0})
# anchor 2: AAA -26 (-26%: 2nd consecutive => STOP); BBB -60 (-30%: 1st); DDD -60 (-20%: recovered => reset)
A2 = snap({"AAAUSDT": 100.0, "BBBUSDT": -200.0, "CCCUSDT": 10.0, "DDDUSDT": 300.0},
          {"AAAUSDT": -26.0, "BBBUSDT": -60.0, "CCCUSDT": -9.0, "DDDUSDT": -60.0})
# anchor 3: AAA still held (stopped, untouched); BBB -52 (-26%: 2nd => STOP, the SHORT side)
A3 = snap({"AAAUSDT": 100.0, "BBBUSDT": -200.0, "DDDUSDT": 300.0},
          {"AAAUSDT": -40.0, "BBBUSDT": -52.0, "DDDUSDT": -10.0})
# anchor 4: AAA gone (|notional| 0 < 20) => cool-off until now + 7d; BBB still held
A4 = snap({"BBBUSDT": -200.0, "DDDUSDT": 300.0}, {"BBBUSDT": -52.0, "DDDUSDT": -10.0})


def run_pns(mod, snaps, cfg=CFG, t0=1000.0):
    st, evs = S0, []
    for i, s in enumerate(snaps):
        st, e = mod.evaluate(s, st, cfg, t0 + i * 14400.0)
        evs.append(e)
    return st, evs


st1, e1 = run_pns(PNS, [A1])
check("★★ anchor 1: counters {AAA:1, DDD:1} — the short at -20% does not count, dust does not count, "
      "-25.0% exactly counts (<=)", st1["counters"] == {"AAAUSDT": 1, "DDDUSDT": 1} and not st1["stopped"] and not e1[0],
      st1)
st2, e2 = run_pns(PNS, [A1, A2])
check("★★ anchor 2: AAA STOPPED (2 consecutive), DDD reset to nothing (recovered), BBB counter 1",
      set(st2["stopped"]) == {"AAAUSDT"} and st2["counters"] == {"BBBUSDT": 1}
      and any("AAAUSDT" in x and "触发" in x for x in e2[1]), st2)
st3, e3 = run_pns(PNS, [A1, A2, A3])
check("★★ anchor 3: the SHORT BBB stops at -52/|-200| = -26% (depth uses |notional|); AAA stays stopped, "
      "no second event for it", set(st3["stopped"]) == {"AAAUSDT", "BBBUSDT"} and st3["counters"] == {}
      and sum(1 for x in e3[2] if "AAAUSDT" in x) == 0 and any("BBBUSDT" in x for x in e3[2]), st3)
st4, e4 = run_pns(PNS, [A1, A2, A3, A4])
check("   anchor 4: AAA exited => cool-off until now + 7 x 86400 exactly; BBB still stopped",
      "AAAUSDT" in st4["cooldown"] and near(st4["cooldown"]["AAAUSDT"], 1000.0 + 3 * 14400.0 + 7 * 86400.0)
      and set(st4["stopped"]) == {"BBBUSDT"} and any("AAAUSDT" in x and "出场" in x for x in e4[3]), st4)
_act = PNS.active_sets(st4, 1000.0 + 3 * 14400.0 + 1.0)
check("   active_sets: stop={BBB}, cooldown={AAA} (for the planner)",
      _act == {"stop": {"BBBUSDT"}, "cooldown": {"AAAUSDT"}}, _act)


def prop_pns_single_needle(mod):
    """-30%, -10%, -30%: a single needle never triggers; recovery resets the counter to ZERO."""
    st, _ = run_pns(mod, [snap({"X": 100.0}, {"X": -30.0}), snap({"X": 100.0}, {"X": -10.0}),
                          snap({"X": 100.0}, {"X": -30.0})])
    ok = not st["stopped"] and st["counters"].get("X") == 1
    return ok, f"stopped={st['stopped']} counters={st['counters']}"


def prop_pns_consecutive(mod):
    """-30%, -26%: triggers at exactly the 2nd consecutive anchor, not before."""
    st_a, _ = run_pns(mod, [snap({"X": 100.0}, {"X": -30.0})])
    st_b, _ = run_pns(mod, [snap({"X": 100.0}, {"X": -30.0}), snap({"X": 100.0}, {"X": -26.0})])
    ok = not st_a["stopped"] and "X" in st_b["stopped"]
    return ok, f"after1={st_a['stopped']} after2={st_b['stopped']}"


def prop_pns_missing_readback(mod):
    """-30%, (absent), -30%: a missing readback breaks continuity — counter restarts at 1."""
    st, _ = run_pns(mod, [snap({"X": 100.0}, {"X": -30.0}), snap({}, {}), snap({"X": 100.0}, {"X": -30.0})])
    ok = not st["stopped"] and st["counters"].get("X") == 1
    return ok, f"stopped={st['stopped']} counters={st['counters']}"


def prop_pns_short_side(mod):
    """a SHORT at -30% twice stops (depth over |notional|)."""
    st, _ = run_pns(mod, [snap({"X": -100.0}, {"X": -30.0}), snap({"X": -100.0}, {"X": -30.0})])
    return "X" in st["stopped"], f"stopped={st['stopped']} counters={st['counters']}"


must_hold("★★ single needle never triggers; recovery resets to zero", prop_pns_single_needle, PNS)
must_hold("★★ only consecutive anchors trigger (exactly at the 2nd)", prop_pns_consecutive, PNS)
must_hold("★ a missing readback breaks continuity", prop_pns_missing_readback, PNS)
must_hold("★ the short side stops too", prop_pns_short_side, PNS)
_m_sticky = mutant(PNS_PATH, [("        else:\n            st[\"counters\"].pop(s, None)",
                               "        else:\n            pass")], "pns_sticky_counter")
must_red("pns_sticky_counter (recovery does not reset: two needles a day apart would stop the name)",
         prop_pns_single_needle, _m_sticky)
_m_unseen = mutant(PNS_PATH, [("    for s in list(st[\"counters\"]):\n        if s not in seen:\n            del st[\"counters\"][s]",
                               "    for s in list(st[\"counters\"]):\n        if False:\n            del st[\"counters\"][s]")],
                   "pns_unseen_not_reset")
must_red("pns_unseen_not_reset (a missing readback keeps the count alive)", prop_pns_missing_readback, _m_unseen)
_m_signed = mutant(PNS_PATH, [("        n = abs(float(notional))", "        n = float(notional)")], "pns_signed_notional")
must_red("pns_signed_notional (depth = -30/-100 = +30%: the short side can never stop)", prop_pns_short_side, _m_signed)
_m_one = mutant(PNS_PATH, [("            if c >= need:", "            if c >= 1:")], "pns_single_anchor_trigger")
must_red("pns_single_anchor_trigger (stops on the first needle)", prop_pns_consecutive, _m_one)

# ══════════════════════════════════════════════════════════════════════════════════════════════
# [G] cond1 — net cost, hand-derived per day
# ══════════════════════════════════════════════════════════════════════════════════════════════
print("\n[G] §4-1 cond1 — per-day net c = (sum fee + sum SIGNED slip)/sum |filled| in bps, hand-derived")
A0 = 1785600000.0


def cost_tree(day_legs):
    """day_legs = [[(side, notional, mid, fill_px, fee), ...] per day]; [] = a day with no fills."""
    root = tempfile.mkdtemp(prefix="gc_c1_")
    TMPS.append(root)
    for i, legs in enumerate(day_legs):
        lg = PL.PilotLogger(root, D[i])
        ats = A0 + i * 86400.0
        lg.anchor(anchor_ts=ats, target_vector_hash="h", realized_gross=2000.0, target_gross=2000.0,
                  n_names_skipped=0, regime_at_anchor="normal", mid_at_anchor_vector={"X": 100.0},
                  factor_version="f", panel_hash="p")
        if not legs:
            lg.order(anchor_ts=ats, symbol="XUSDT", side="buy", target_w=0.5, prev_w=0.5, intended_notional=1000.0,
                     order_type="maker", submit_ts=ats + 1, price_submit=100.0, mid_at_submit=100.0, mid_at_anchor=100.0,
                     filled_notional=0.0, avg_fill_px=None, first_fill_ts=None, last_fill_ts=None, cancel_ts=ats + 900,
                     fee_paid=0.0, rebalance_id=f"R{i}", attempt_idx=1, terminal_reason="partial_expired",
                     notional_currency="USDT")
        for j, (side, notional, mid, px, fee) in enumerate(legs):
            lg.order(anchor_ts=ats, symbol=f"S{j}USDT", side=side, target_w=0.5, prev_w=0.0,
                     intended_notional=(notional if side == "buy" else -notional), order_type="maker",
                     submit_ts=ats + 1, price_submit=mid, mid_at_submit=mid, mid_at_anchor=mid,
                     filled_notional=(notional if side == "buy" else -notional), avg_fill_px=px,
                     first_fill_ts=ats + 2, last_fill_ts=ats + 3, cancel_ts=None, fee_paid=fee,
                     rebalance_id=f"R{i}", attempt_idx=1, terminal_reason="filled", notional_currency="USDT")
        lg.close()
    return root


def c_by_hand(legs):
    fee = sum(l[4] for l in legs)
    slip = sum(((l[3] - l[2]) / l[2]) * (1 if l[0] == "buy" else -1) * l[1] for l in legs)
    den = sum(l[1] for l in legs)
    return round((fee + slip) / den * 1e4, 4) if den else None


TEN = [("buy", 1000.0, 100.0, 100.06, 0.4)]                       # (0.4 + 0.6)/1000 = 10.0 bps
FOUR = [("buy", 1000.0, 100.0, 100.06, 0.4), ("sell", 1000.0, 100.0, 100.06, 0.4)]   # 0.6 - 0.6 + 0.8 => 4.0
NINE = [("buy", 1000.0, 100.0, 100.05, 0.4)]                      # (0.4 + 0.5)/1000 = 9.0 bps exactly
check("PRE-ASSERT hand formulas: 10.0 / 4.0 / 9.0", (c_by_hand(TEN), c_by_hand(FOUR), c_by_hand(NINE)) == (10.0, 4.0, 9.0))


def c1_of(mod, days):
    return ev(mod, cost_tree(days))["conditions"]["cond1_c_persist"]


_g1 = c1_of(WD, [TEN] * 5)
check("★★ five days at 10.0 bps: per_day_c == [10.0]*5 and it TRIPS", _g1["per_day_c"] == [10.0] * 5 and _g1["triggered"] is True,
      _g1["per_day_c"])
_g2 = c1_of(WD, [TEN, TEN, FOUR, TEN, TEN])
check("★★ a day whose SELL above mid is a credit reads 4.0 (fee 0.8 / 2000) and breaks the streak; its "
      "dispersion reads 6.0 (|0.6|+|0.6| / 2000)", _g2["per_day_c"] == [10.0, 10.0, 4.0, 10.0, 10.0]
      and _g2["triggered"] is False and _g2["per_day_dispersion_bps"][2] == 6.0,
      {k: _g2[k] for k in ("per_day_c", "per_day_dispersion_bps")})


def prop_c1_boundary(mod):
    c = c1_of(mod, [TEN, TEN, NINE, TEN, TEN])
    return (c["per_day_c"][2] == 9.0 and c["triggered"] is False), f"per_day_c={c['per_day_c']} trig={c['triggered']}"


def prop_c1_unpriced_tail(mod):
    c = c1_of(mod, [TEN] * 5 + [[]])
    return (c["triggered"] is True and c["n_unpriced_days_in_window"] == 1 and c["per_day_c"][-1] is None), \
        f"per_day_c={c['per_day_c']} trig={c['triggered']}"


must_hold("★ a day at exactly 9.0 is NOT a breach (the rule is >)", prop_c1_boundary)
must_hold("★ an unpriced trailing day neither breaks nor extends the streak (5 priced days at 10 still trip)",
          prop_c1_unpriced_tail)
_m_ge = mutant(WD_PATH, [("                                    lambda c: c > C_LIMIT_BPS, C_PERSIST_DAYS)",
                          "                                    lambda c: c >= C_LIMIT_BPS, C_PERSIST_DAYS)")], "cond1_ge_at_limit")
must_red("cond1_ge_at_limit (9.0 counts as a breach)", prop_c1_boundary, _m_ge)
_m_cal = mutant(WD_PATH, [("    hit, _n_unpriced = _persist_hit(per_day_c, [c is not None for c in per_day_c],",
                           "    hit, _n_unpriced = _persist_hit(per_day_c, [True for c in per_day_c],"),
                          ("                                    lambda c: c > C_LIMIT_BPS, C_PERSIST_DAYS)",
                           "                                    lambda c: c is not None and c > C_LIMIT_BPS, C_PERSIST_DAYS)")],
                "cond1_calendar_streak")
must_red("cond1_calendar_streak (an unpriced day reads as 'cost was fine' and clears the streak)",
         prop_c1_unpriced_tail, _m_cal)

# ══════════════════════════════════════════════════════════════════════════════════════════════
# [H] cond3 — crash-day markout, hand-derived
# ══════════════════════════════════════════════════════════════════════════════════════════════
print("\n[H] §4-3 cond3 — notional-weighted adverse markout over MAKER fills inside STRESS anchors")


def mk_tree(d3_buy_mark):
    """D1 stress: buy 1000@100 mark 99.70 (+30 adverse), sell 3000@100 mark 100.10 (+10), one PENDING mark
       => day markout (30*1000 + 10*3000)/4000 = 15.0, marked 2 / unmarked 1.
    D2 calm: buy 1000@100 mark 99.00 (+100) — NOT judged (regime), but counted in window coverage.
    D3 stress: buy 500@100 mark d3_buy_mark; sell 500@100 mark 99.95 (-5, favourable)."""
    root = tempfile.mkdtemp(prefix="gc_c3_")
    TMPS.append(root)
    plan = [("stress", [("buy", 1000.0, 100.0, 99.70), ("sell", 3000.0, 100.0, 100.10), ("buy", 500.0, 100.0, None)]),
            ("calm", [("buy", 1000.0, 100.0, 99.00)]),
            ("stress", [("buy", 500.0, 100.0, d3_buy_mark), ("sell", 500.0, 100.0, 99.95)])]
    for i, (regime, fills) in enumerate(plan):
        lg = PL.PilotLogger(root, D[i])
        ats = A0 + i * 86400.0
        lg.anchor(anchor_ts=ats, target_vector_hash="h", realized_gross=5000.0, target_gross=5000.0,
                  n_names_skipped=0, regime_at_anchor=regime, mid_at_anchor_vector={"X": 100.0},
                  factor_version="f", panel_hash="p")
        for j, (side, notional, px, mark) in enumerate(fills):
            lg.fill(anchor_ts=ats, symbol=f"S{j}USDT", side=side, order_type="maker", attempt_idx=1,
                    fill_ts=ats + 10, fill_px=px, fill_notional=notional, mid_at_fill_plus_60s=mark,
                    rebalance_id=f"R{i}")
        lg.close()
    return root


def adverse(side, px, mark):
    return (-(1.0 if side == "buy" else -1.0) * (mark - px) / px * 1e4)


_d1 = (adverse("buy", 100.0, 99.70) * 1000.0 + adverse("sell", 100.0, 100.10) * 3000.0) / 4000.0
_d3 = (adverse("buy", 100.0, 99.60) * 500.0 + adverse("sell", 100.0, 99.95) * 500.0) / 1000.0
_d3t = (adverse("buy", 100.0, 99.40) * 500.0 + adverse("sell", 100.0, 99.95) * 500.0) / 1000.0
check("PRE-ASSERT hand values: D1 15.0, D3 17.5, D3-trip 27.5", (round(_d1, 4), round(_d3, 4), round(_d3t, 4)) == (15.0, 17.5, 27.5))
_h = ev(WD, mk_tree(99.60))["conditions"]["cond3_crash_markout"]
check("★★ worst_adverse_bps = 17.5 = max(15.0, 17.5) over the two stress days; the calm day's 100 bps is ignored",
      near(_h["worst_adverse_bps"], 17.5) and _h["triggered"] is False and _h["n_stress_anchors"] == 2,
      {k: _h[k] for k in ("worst_adverse_bps", "triggered", "n_stress_anchors")})
check("   coverage = marked/(marked+unmarked) over stress fills = 4/5 = 0.8; window coverage 5/6; state OK",
      _h["coverage"] == 0.8 and _h["n_marked_stress_fills"] == 4 and _h["n_unmarked_stress_fills"] == 1
      and _h["coverage_all_fills"] == round(5.0 / 6.0, 4) and _h["state"] == "OK",
      {k: _h[k] for k in ("coverage", "n_marked_stress_fills", "n_unmarked_stress_fills", "coverage_all_fills", "state")})


def prop_c3_trip(mod):
    e = ev(mod, mk_tree(99.40))
    c = e["conditions"]["cond3_crash_markout"]
    ok = near(c["worst_adverse_bps"], 27.5) and c["triggered"] is True and any("§4-3" in t for t in e["triggers"])
    return ok, f"worst={c['worst_adverse_bps']} trig={c['triggered']}"


must_hold("★★ D3 at 27.5 bps adverse (> 25) TRIPS and the worst is the WORST day, not the best", prop_c3_trip)
_m_min = mutant(WD_PATH, [("                worst_mk = mk if worst_mk is None else max(worst_mk, mk)",
                           "                worst_mk = mk if worst_mk is None else min(worst_mk, mk)")], "cond3_min_selector")
must_red("cond3_min_selector (the 2026-07-29 defect: the benign 15.0 day disarms the stop)", prop_c3_trip, _m_min)

# ══════════════════════════════════════════════════════════════════════════════════════════════
# [I] cond5 — 5a / 5b / 5c / 5e hand-derived
# ══════════════════════════════════════════════════════════════════════════════════════════════
print("\n[I] §4-5 cond5")
_emp = tempfile.mkdtemp(prefix="gc_c5a_")
TMPS.append(_emp)
write_nav(_emp, D[0], [dict(day=D[0], target_gross=200.0, nav=100.0, realised_pnl=0.0, unrealised_pnl=0.0)])
_5a = ev(WD, _emp, ve=[{"kind": "outage", "severity": "stop"}])
_5w = ev(WD, _emp, ve=[{"kind": "public_path_unreachable", "severity": "warn"}])
check("5a: an outage event trips §4-5a; a public_path_unreachable WARN does not (deliberately unconsumed)",
      _5a["conditions"]["cond5_venue_event"]["5a_outage"]["triggered"] is True and any("§4-5a" in t for t in _5a["triggers"])
      and _5w["conditions"]["cond5_venue_event"]["triggered"] is False, _5w["triggers"])

print("  5b — quantity residual: expected_qty = qty(T1) + sum dq_fills vs qty(T2), priced at T2's mark")
T1, T2 = A0, A0 + 14400.0


def tree_5b(filled_notional):
    """T1 readback 10 contracts @100 (1,000 USDT); one SELL between (filled_notional, px 100 => dq);
    T2 readback 4 contracts @100 (400 USDT)."""
    root = tempfile.mkdtemp(prefix="gc_c5b_")
    TMPS.append(root)
    lg = PL.PilotLogger(root, D[0])
    lg.position_readback(anchor_ts=T1, symbol="AAAUSDT", venue_position_notional=1000.0, venue_position_qty=10.0,
                         source="mock", read_ts=T1 + 900)
    lg.order(anchor_ts=T2, symbol="AAAUSDT", side="sell", target_w=0.4, prev_w=1.0, intended_notional=-600.0,
             order_type="maker", submit_ts=T2 + 1, price_submit=100.0, mid_at_submit=100.0, mid_at_anchor=100.0,
             filled_notional=filled_notional, avg_fill_px=100.0, first_fill_ts=T2 + 2, last_fill_ts=T2 + 3,
             cancel_ts=None, fee_paid=0.1, rebalance_id="R1", attempt_idx=1,
             terminal_reason=("filled" if filled_notional == -600.0 else "partial_expired"), notional_currency="USDT")
    lg.position_readback(anchor_ts=T2, symbol="AAAUSDT", venue_position_notional=400.0, venue_position_qty=4.0,
                         source="mock", read_ts=T2 + 900)
    lg.daily_nav(day=D[0], target_gross=2000.0, nav=1000.0, realised_pnl=0.0, unrealised_pnl=0.0)
    lg.close()
    return root


def rec_of(mod, root):
    return mod.reconcile([(D[0], PL.read_day(root, D[0]))])


_rc_ok = rec_of(RC, tree_5b(-600.0))
_5b_ok = ev(WD, tree_5b(-600.0))["conditions"]["cond5_venue_event"]["5b_liquidation_anomaly"]
check("★★ sold 600 (dq -6): expected 10-6 = 4 = observed => residual 0 => CLEAN, nothing at the latest anchor",
      not _rc_ok["latest"] and _rc_ok["n_reconciled_anchors"] == 1 and _5b_ok["state"] == "CLEAN" and _5b_ok["n"] == 0,
      {"latest": _rc_ok["latest"], "state": _5b_ok["state"]})
_rc_tol = rec_of(RC, tree_5b(-590.0))
check("★ sold 590 (dq -5.9): residual 0.1 contract = 10 USDT <= max(10% x 410, 5) = 41 => within tolerance, CLEAN",
      not _rc_tol["latest"] and abs(_rc_tol["residual_by_anchor"][T2]["by_symbol"]["AAAUSDT"]["residual_qty"] - (-0.1)) < 1e-9,
      _rc_tol["residual_by_anchor"][T2]["by_symbol"])
_rc_bad = rec_of(RC, tree_5b(-300.0))
_5b_bad = ev(WD, tree_5b(-300.0))["conditions"]["cond5_venue_event"]["5b_liquidation_anomaly"]
_an = (_rc_bad["latest"] or [{}])[0]
check("★★ sold 300 (dq -3): expected 7, observed 4, residual -3 x mark 100 = 300 USDT > max(70, 5) => ANOMALY; "
      "expected 700 / observed 400 / unexplained_frac 300/700 = 0.4286",
      len(_rc_bad["latest"]) == 1 and _an.get("residual_qty") == -3.0 and _an.get("residual_usdt") == 300.0
      and _an.get("expected") == 700.0 and _an.get("observed") == 400.0 and _an.get("unexplained_frac") == round(300.0 / 700.0, 4)
      and _5b_bad["state"] == "ANOMALOUS" and _5b_bad["triggered"] is True, _an)
_m_sign = mutant(RC_PATH, [("                    expected_qty = q1 + _win.get(sym, 0.0)",
                            "                    expected_qty = q1 - _win.get(sym, 0.0)")], "reconcile_sign_on_expected")
must_red("reconcile_sign_on_expected (the fill sign re-applied: the clean sale reads 16 expected vs 4 observed)",
         lambda m: (not rec_of(m, tree_5b(-600.0))["latest"], rec_of(m, tree_5b(-600.0))["latest"]), _m_sign)

print("  5c — venue_reject fraction over orders we actually SENT, >= 0.5 on 2 consecutive anchors")


def tree_5c(rejects_per_anchor, never_sent=20):
    root = tempfile.mkdtemp(prefix="gc_c5c_")
    TMPS.append(root)
    lg = PL.PilotLogger(root, D[0])
    for a, n_rej in enumerate(rejects_per_anchor):
        ats = A0 + a * 14400.0
        for i in range(10):
            rej = i < n_rej
            lg.order(anchor_ts=ats, symbol=f"S{i}USDT", side="buy", target_w=0.1, prev_w=0.0, intended_notional=100.0,
                     order_type="maker", submit_ts=ats + 1, price_submit=100.0, mid_at_submit=100.0, mid_at_anchor=100.0,
                     filled_notional=(0.0 if rej else 100.0), avg_fill_px=(None if rej else 100.0),
                     first_fill_ts=(None if rej else ats + 2), last_fill_ts=(None if rej else ats + 2), cancel_ts=None,
                     fee_paid=(0.0 if rej else 0.02), rebalance_id=f"R{a}", attempt_idx=1,
                     terminal_reason=("venue_reject" if rej else "filled"), notional_currency="USDT")
    # rows that NEVER left the process, labelled venue_reject (the pre-fix history shape): not sent => not counted
    for i in range(never_sent):
        lg.order(anchor_ts=A0, symbol=f"N{i}USDT", side="buy", target_w=0.1, prev_w=0.0, intended_notional=100.0,
                 order_type="maker", submit_ts=None, price_submit=None, mid_at_submit=None, mid_at_anchor=100.0,
                 filled_notional=0.0, avg_fill_px=None, first_fill_ts=None, last_fill_ts=None, cancel_ts=None,
                 fee_paid=0.0, rebalance_id="R0", attempt_idx=1, terminal_reason="venue_reject", notional_currency="USDT")
    lg.daily_nav(day=D[0], target_gross=2000.0, nav=1000.0, realised_pnl=0.0, unrealised_pnl=0.0)
    lg.close()
    return root


def c5c_of(mod, rej):
    return ev(mod, tree_5c(rej))["conditions"]["cond5_venue_event"]["5c_account_restriction"]


def prop_5c(mod):
    a = c5c_of(mod, [6, 5])          # 0.6 and 0.5 (>= line) on two consecutive anchors => hit
    b = c5c_of(mod, [6, 4])          # 0.6 then 0.4 => no
    c = c5c_of(mod, [6, 3, 6])       # T F T => not consecutive => no
    ok = (a["n_submitted_orders"] == 20 and a["behavioural_anchor_hit"] is True and a["triggered"] is True
          and b["n_submitted_orders"] == 20 and b["behavioural_anchor_hit"] is False
          and c["n_submitted_orders"] == 30 and c["behavioural_anchor_hit"] is False)
    return ok, (f"[6,5] n={a['n_submitted_orders']} hit={a['behavioural_anchor_hit']} | [6,4] hit={b['behavioural_anchor_hit']} "
                f"| [6,3,6] n={c['n_submitted_orders']} hit={c['behavioural_anchor_hit']}")


must_hold("★★ 6/10 then 5/10 rejected => hit (>= 0.5 on 2 anchors); 6/10 then 4/10 => no; the 20 never-sent "
          "venue_reject rows are not in the denominator (20 = 2 x 10 sent)", prop_5c)
_m_den = mutant(WD_PATH, [("            if o.get(\"submit_ts\") is None:\n                continue                      # never left this process; says nothing about the venue",
                           "            if False:\n                continue")], "cond5c_never_sent_in_denominator")
must_red("cond5c_never_sent_in_denominator (n_submitted 40 and the never-sent anchor reads 26/30 rejected)", prop_5c, _m_den)
_m_gt = mutant(WD_PATH, [("            anchor_reject_flags.append(len(rows) > 0 and rej / len(rows) >= REJECT_FRAC_LIMIT)",
                          "            anchor_reject_flags.append(len(rows) > 0 and rej / len(rows) > REJECT_FRAC_LIMIT)")],
               "cond5c_gt_at_half")
must_red("cond5c_gt_at_half (exactly half rejected no longer flags the anchor)", prop_5c, _m_gt)

print("  5e — position break: venue vs INTENDED, in money, with the split (unauth / underfill)")
G5 = 1000.0
NAMES5 = ["AAAUSDT", "BBBUSDT", "CCCUSDT", "DDDUSDT"]
W5 = {"AAAUSDT": 0.25, "BBBUSDT": -0.25, "CCCUSDT": 0.25, "DDDUSDT": -0.25}


def tree_5e(c_venue, c_filled=150.0):
    """T0: a flat readback for the four names (the predecessor). T1: orders for all four (submitted;
    A/B/D fill in full, C fills `c_filled` of its 250) and the readback: A 250, B -250, C `c_venue`, D -250.
    Everything priced at 1.0 so qty == notional."""
    root = tempfile.mkdtemp(prefix="gc_c5e_")
    TMPS.append(root)
    lg = PL.PilotLogger(root, D[0])
    lg.anchor(anchor_ts=T1, target_vector_hash="h", realized_gross=0.0, target_gross=G5, n_names_skipped=0,
              regime_at_anchor="normal", mid_at_anchor_vector={s: 1.0 for s in NAMES5}, factor_version="f", panel_hash="p")
    for s in NAMES5:
        lg.position_readback(anchor_ts=T1, symbol=s, venue_position_notional=0.0, venue_position_qty=0.0,
                             source="mock", read_ts=T1 + 900)
    lg.anchor(anchor_ts=T2, target_vector_hash="h", realized_gross=G5, target_gross=G5, n_names_skipped=0,
              regime_at_anchor="normal", mid_at_anchor_vector={s: 1.0 for s in NAMES5}, factor_version="f", panel_hash="p")
    venue = {"AAAUSDT": 250.0, "BBBUSDT": -250.0, "CCCUSDT": c_venue, "DDDUSDT": -250.0}
    for s in NAMES5:
        tgt = W5[s] * G5
        filled = c_filled if s == "CCCUSDT" else tgt
        lg.order(anchor_ts=T2, symbol=s, side=("buy" if tgt > 0 else "sell"), target_w=W5[s], prev_w=0.0,
                 intended_notional=tgt, order_type="maker", submit_ts=T2 + 1, price_submit=1.0, mid_at_submit=1.0,
                 mid_at_anchor=1.0, filled_notional=filled, avg_fill_px=1.0, first_fill_ts=T2 + 2, last_fill_ts=T2 + 3,
                 cancel_ts=None, fee_paid=0.01, rebalance_id="R1", attempt_idx=1,
                 terminal_reason=("filled" if filled == tgt else "partial_expired"), notional_currency="USDT")
        lg.position_readback(anchor_ts=T2, symbol=s, venue_position_notional=venue[s], venue_position_qty=venue[s],
                             source="mock", read_ts=T2 + 900)
    lg.daily_nav(day=D[0], target_gross=G5, nav=500.0, realised_pnl=0.0, unrealised_pnl=0.0)
    lg.close()
    return root


_e5 = ev(WD, tree_5e(150.0))
_pb = _e5["conditions"]["cond5_venue_event"]["5e_position_break"]
_lat = _pb["latest"]
_sv = _lat["split_verdict"]
check("★★ dev = |250-250|+|-250+250|+|150-250|+|-250+250| = 100 USDT = 10.0% of 1,000; 4/4 compared; CLEAN",
      _lat["portfolio_dev_usdt"] == 100.0 and _lat["portfolio_dev_frac"] == 0.1 and _lat["n_compared"] == 4
      and _lat["coverage"] == 1.0 and _lat["state"] == "CLEAN" and _pb["triggered"] is False
      and _lat["worst_symbol"] == "CCCUSDT" and _lat["worst_symbol_dev_usdt"] == -100.0,
      {k: _lat[k] for k in ("portfolio_dev_usdt", "portfolio_dev_frac", "n_compared", "state", "worst_symbol")})
check("★★ the split speaks (coverage 1.0): unauth 0 (every fill explains the book), underfill 100 = 10% of gross "
      "(< 40% alarm); gate = split_unauth", _sv["can_speak"] is True and _sv["unauth_frac"] == 0.0
      and near(_sv["underfill_frac"], 0.1) and _sv["underfill_triggered"] is False and _lat["trip_gate"] == "split_unauth",
      {k: _sv[k] for k in ("can_speak", "unauth_frac", "underfill_frac", "action")})
_e5g = ev(WD, tree_5e(330.0))
_latg = _e5g["conditions"]["cond5_venue_event"]["5e_position_break"]["latest"]
_svg = _latg["split_verdict"]
check("★★ GHOST: C holds 330 on a 150 fill => unauth 180 = 18% of gross > 5% (and >= C's floor) => FLATTEN via "
      "split_unauth; the legacy rule (dev 80 = 8% < 25%, per-name 80 < 100) would NOT have fired",
      _latg["triggered"] is True and _latg["trip_gate"] == "split_unauth"
      and near(_svg["unauth_frac"], 0.18) and _svg["unauth_names"] == ["CCCUSDT"] and _latg["dev_triggered_legacy"] is False
      and _latg["portfolio_dev_frac"] == 0.08, {k: _svg[k] for k in ("unauth_frac", "unauth_names", "action")})
check("   ...and the trip text names §4-5e [split_unauth] AND §4-5b sees the same 180 (the two gates agree)",
      any("§4-5e position break [split_unauth]" in t for t in _e5g["triggers"]) and any("§4-5b" in t for t in _e5g["triggers"])
      and _e5g["conditions"]["cond5_venue_event"]["5b_liquidation_anomaly"]["examples"][0]["residual_usdt"] == 180.0,
      [t[:60] for t in _e5g["triggers"]])

# ══════════════════════════════════════════════════════════════════════════════════════════════
# [J] cond6 — weight fidelity, hand-derived
# ══════════════════════════════════════════════════════════════════════════════════════════════
print("\n[J] §4-6 cond6 — corr = 1 - mawe x 100 over ELIGIBLE anchors (submitted > 0), per day")
N6, G6 = 40, 1000.0
SYM6 = [f"S{i:03d}USDT" for i in range(N6)]
W6 = {s: (1.0 / N6) * (1 if i % 2 == 0 else -1) for i, s in enumerate(SYM6)}


def write_anchor6(lg, ats, kind):
    """traded: orders fill the target from flat, readback = target (mawe 0)  | halted: nothing submitted,
    flat readback (mawe 1/N) | under: orders fill 92% from flat, readback 92% (mawe 0.002) | under_hold:
    orders submitted, nothing fills, readback stays at 92% (mawe 0.002, eligible)."""
    lg.anchor(anchor_ts=ats, target_vector_hash="h", realized_gross=G6, target_gross=G6, n_names_skipped=0,
              regime_at_anchor="normal", mid_at_anchor_vector="v", factor_version="f", panel_hash="p")
    for s in SYM6:
        w = W6[s]
        tgt = w * G6
        submitted = kind != "halted"
        filled = {"traded": tgt, "under": 0.92 * tgt}.get(kind, 0.0)
        held = {"traded": tgt, "under": 0.92 * tgt, "under_hold": 0.92 * tgt}.get(kind, 0.0)
        lg.order(anchor_ts=ats, symbol=s, side=("buy" if w > 0 else "sell"), target_w=w, prev_w=0.0,
                 intended_notional=tgt, order_type="maker", submit_ts=(ats + 1 if submitted else None),
                 price_submit=(1.0 if submitted else None), mid_at_submit=1.0, mid_at_anchor=1.0,
                 filled_notional=filled, avg_fill_px=(1.0 if filled else None),
                 first_fill_ts=(ats + 2 if filled else None), last_fill_ts=(ats + 2 if filled else None),
                 cancel_ts=None, fee_paid=0.0, rebalance_id=f"A{int(ats)}", attempt_idx=1,
                 terminal_reason=("filled" if filled == tgt and filled else "partial_expired" if submitted else "blocked_by_halt"),
                 notional_currency="USDT")
        lg.position_readback(anchor_ts=ats, symbol=s, venue_position_notional=held, venue_position_qty=held,
                             source="test", held=bool(held), targeted=True, read_ts=ats + 5)


def tree6(days):
    root = tempfile.mkdtemp(prefix="gc_c6_")
    TMPS.append(root)
    for i, kinds in enumerate(days):
        lg = PL.PilotLogger(root, D[i])
        for j, k in enumerate(kinds):
            write_anchor6(lg, A0 + i * 86400.0 + j * 14400.0, k)
        lg.daily_nav(day=D[i], target_gross=G6, nav=500.0, realised_pnl=0.0, unrealised_pnl=0.0)
        lg.close()
    return root


def c6_of(mod, days):
    return ev(mod, tree6(days))["conditions"]["cond6_weight_fidelity"]


MAWE_U = 0.08 * (1.0 / N6)                                   # |0.92w - w| = 0.002
CORR_U = round(1.0 - MAWE_U * 100.0, 4)                       # 0.8
POOLED_MIXED = round(1.0 - ((1.0 / N6) * N6 + MAWE_U * N6) / (2 * N6) * 100.0, 4)   # (0.025 + 0.002)/2 => -0.35
check("PRE-ASSERT hand values: corr(under) 0.8, pooled(mixed) -0.35", (CORR_U, POOLED_MIXED) == (0.8, -0.35))


def prop_c6(mod):
    c = c6_of(mod, [["traded"], ["halted", "under"], ["under_hold"], ["under_hold"]])
    ok = (c["per_day"] == [1.0, CORR_U, CORR_U, CORR_U] and c["n_comparisons_per_day"] == [N6] * 4
          and c["per_day_pooled_all_anchors"] == [1.0, POOLED_MIXED, CORR_U, CORR_U]
          and c["n_anchors_excluded_not_traded"] == 1 and c["n_anchors_eligible"] == 4
          and c["underfill_persistent_breach"] is True and c["triggered"] is False
          and c["split_line_order_ok"] is True and c["implied_break_frac_limit"] == round(0.15 * N6 / 100.0, 6))
    return ok, {k: c[k] for k in ("per_day", "per_day_pooled_all_anchors", "n_anchors_excluded_not_traded",
                                  "underfill_persistent_breach", "triggered", "split_line_order_ok", "implied_break_frac_limit")}


must_hold("★★ per_day [1.0, 0.8, 0.8, 0.8] (the halted anchor excluded), pooled -0.35 on the mixed day, 3-day "
          "underfill breach = ALARM not halt (firing-order premise 0.06 > 0.05 holds at N=40)", prop_c6)
_m_elig = mutant(WD_PATH, [("        eligible = sub > 0", "        eligible = True")], "cond6_every_anchor_eligible")
must_red("cond6_every_anchor_eligible (the halted anchor's 1/N is pooled in: day 2 reads -0.35)", prop_c6, _m_elig)

# ══════════════════════════════════════════════════════════════════════════════════════════════
# [K] cond7 — ops: fail-rate streak and drift tri-state
# ══════════════════════════════════════════════════════════════════════════════════════════════
print("\n[K] §4-7 cond7 — rebalance fail rate > 0.05 for 3 days; un-recovered drift is a STATE")


def c7_of(mod, rates, drift=False):
    ops = [{"rebalance_fail_rate": r} for r in rates]
    ops[-1]["unrecovered_position_drift"] = drift
    e = ev(mod, _emp, ops=ops)
    return e["conditions"]["cond7_ops"], e["triggers"]


def prop_c7(mod):
    a, _ = c7_of(mod, [0.0, 0.06, 0.051, 0.05])          # tail [0.06, 0.051, 0.05]: 0.05 is NOT > 0.05
    b, tb = c7_of(mod, [0.0, 0.06, 0.051, 0.0501])       # all three > 0.05 => hit
    c, tc = c7_of(mod, [0.0, 0.0, 0.0], drift=True)
    d, _ = c7_of(mod, [0.0], drift=None)
    ok = (a["triggered"] is False and a["drift_state"] == "CLEAN" and a["blind"] is False
          and b["triggered"] is True and any("failure rate" in t for t in tb)
          and c["triggered"] is True and c["drift_state"] == "DRIFT" and any("drift" in t for t in tc)
          and d["drift_state"] == "UNKNOWN" and d["blind"] is True and d["triggered"] is False)
    return ok, {"boundary": a["triggered"], "streak": b["triggered"], "drift": c["drift_state"], "unknown": d["drift_state"]}


must_hold("★★ [.06,.051,.05] no trip (0.05 is not > 0.05); [.06,.051,.0501] trips; drift True trips; drift None = UNKNOWN/blind",
          prop_c7)
_m_ge7 = mutant(WD_PATH, [("    hit_rate = _consecutive_tail([x > FAIL_RATE_LIMIT for x in fr], FAIL_PERSIST_DAYS)",
                           "    hit_rate = _consecutive_tail([x >= FAIL_RATE_LIMIT for x in fr], FAIL_PERSIST_DAYS)")], "cond7_ge_at_limit")
must_red("cond7_ge_at_limit (0.05 counts: the boundary series trips)", prop_c7, _m_ge7)


def tree7():
    """20 SENT orders, 2 venue_reject => 0.10; plus 5 never-sent venue_reject rows and 3 skipped_min_notional
    rows, none of which are rebalance failures."""
    root = tempfile.mkdtemp(prefix="gc_c7_")
    TMPS.append(root)
    lg = PL.PilotLogger(root, D[0])
    for i in range(20):
        rej = i < 2
        lg.order(anchor_ts=A0, symbol=f"S{i}USDT", side="buy", target_w=0.05, prev_w=0.0, intended_notional=100.0,
                 order_type="maker", submit_ts=A0 + 1, price_submit=100.0, mid_at_submit=100.0, mid_at_anchor=100.0,
                 filled_notional=(0.0 if rej else 100.0), avg_fill_px=(None if rej else 100.0),
                 first_fill_ts=(None if rej else A0 + 2), last_fill_ts=(None if rej else A0 + 2), cancel_ts=None,
                 fee_paid=0.0, rebalance_id="R0", attempt_idx=1, terminal_reason=("venue_reject" if rej else "filled"),
                 notional_currency="USDT")
    for i in range(5):
        lg.order(anchor_ts=A0, symbol=f"N{i}USDT", side="buy", target_w=0.05, prev_w=0.0, intended_notional=100.0,
                 order_type="maker", submit_ts=None, price_submit=None, mid_at_submit=None, mid_at_anchor=100.0,
                 filled_notional=0.0, avg_fill_px=None, first_fill_ts=None, last_fill_ts=None, cancel_ts=None,
                 fee_paid=0.0, rebalance_id="R0", attempt_idx=1, terminal_reason="venue_reject", notional_currency="USDT")
    for i in range(3):
        lg.order(anchor_ts=A0, symbol=f"M{i}USDT", side="buy", target_w=0.001, prev_w=0.0, intended_notional=2.0,
                 order_type="maker", submit_ts=None, price_submit=None, mid_at_submit=None, mid_at_anchor=100.0,
                 filled_notional=0.0, avg_fill_px=None, first_fill_ts=None, last_fill_ts=None, cancel_ts=None,
                 fee_paid=0.0, rebalance_id="R0", attempt_idx=1, terminal_reason="skipped_min_notional", notional_currency="USDT")
    lg.close()
    return root


def prop_c7_derive(mod):
    o = mod.derive_ops_stats(tree7())[-1]
    ok = o["n_orders"] == 20 and o["n_venue_side_failures"] == 2 and near(o["rebalance_fail_rate"], 0.10)
    return ok, {k: o[k] for k in ("n_orders", "n_venue_side_failures", "rebalance_fail_rate")}


must_hold("★★ derive_ops_stats: 2 venue_reject of 20 SENT = 0.10; never-sent and skipped_min_notional rows excluded",
          prop_c7_derive, WI)
_m_den7 = mutant(WI_PATH, [("                  and o.get(\"submit_ts\") is not None]", "                  and True]")],
                 "ops_stats_never_sent_in_denominator")
must_red("ops_stats_never_sent_in_denominator (7/25 = 0.28: our own halted rows become venue failures)",
         prop_c7_derive, _m_den7)

# ══════════════════════════════════════════════════════════════════════════════════════════════
# [Z] nothing on disk changed; summary
# ══════════════════════════════════════════════════════════════════════════════════════════════
print("\n[Z] the on-disk sources are byte-identical after all mutants")
check("watchdog.py / reconcile.py / watchdog_inputs.py / per_name_stop.py unchanged on disk",
      all(_sha(p) == SHA0[p] for p in SHA0), {os.path.basename(p): SHA0[p][:12] for p in SHA0})
check("no bytecode was written beside the sources by this run (live/__pycache__ listing unchanged)",
      _pyc_snapshot() == PYC0, f"before={len(PYC0)} after={len(_pyc_snapshot())} dont_write_bytecode={sys.dont_write_bytecode}")

for _t in TMPS:
    shutil.rmtree(_t, ignore_errors=True)

print("\n  mutant ledger (every mutant must be RED):")
for _n, _r in MUTANT_LEDGER:
    print(f"    {'RED  ' if _r else 'ALIVE'}  {_n}")
_alive = [n for n, r in MUTANT_LEDGER if not r]
print(f"\n  {N[0]} checks run; {len(MUTANT_LEDGER)} mutants, {len(MUTANT_LEDGER) - len(_alive)} red, {len(_alive)} alive")
if N[0] == 0:
    print("  FAIL  ZERO CHECKS RAN — an empty suite is a RED, not a pass")
    sys.exit(1)
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}")
sys.exit(0 if not FAILS else 1)
