#!/usr/bin/python3
"""ALM-06 (ii) — decompose the CUM gap between the twin's INDEPENDENT income-ledger TWR and the watchdog's
start-equity chain, CAUSE BY CAUSE, on the rows the running twin actually wrote. Offline, read-only, no venue.

WHY. The 16:2xZ ruling sent back the first ALM-06 fix: making the CUM alert compare an ARITHMETIC twin that reads the
same daily_nav inputs as the watchdog leaves it able to catch only arithmetic bugs — precisely the LED-04 class of
input bias becomes invisible. Both alerts must survive: (i) arithmetic twin vs watchdog at a tight tolerance, and
(ii) the independent income-ledger TWR vs the watchdog chain, judged against a band derived cause by cause from the
MEASURED caliber gap — not a constant fitted to make the 8 recorded lines go away.

THE DECOMPOSITION. Only the twin SEGMENT of the chain can differ: days before the twin's first snapshot day are
daily_nav-based in both chains. Over the twin segment four chains are computed on the SAME days:
  T   the twin as it runs: day closes from its own snapshots, transfers from its own income ledger
  C1  the same, but each day's close taken from daily_nav's last row of that day   ⇒ T − C1 = DAY-CLOSE TIMING
  C2a C1, but a transfer day priced by the WATCHDOG's formula (realised + Δunrealised)/nav_prev with the realised
      taken from the twin's own INCOME ledger                                      ⇒ C1 − C2a = TRANSFER-DAY FORMULA
  C2b C2a, but the realised taken from daily_nav's RECORDED realised_pnl           ⇒ C2a − C2b = INPUT BIAS
and C2b must reproduce the deployed `wd_chain_arith_pct` — an identity check on the whole construction, not an
assumption. What is left after the two CALIBER causes and the frozen LED-04 allowance is the residual that (ii) judges.

THE LED-04 ALLOWANCE IS FROZEN, NOT RE-DERIVED LIVE — and that distinction is the whole point. If the allowance were
recomputed from income on every run it would absorb ANY input bias, including a new one, and (ii) would be blind
again for the second time. So it is the per-transfer-day table measured once by led04_cond4_transfer_day_effect.py
(receipt LED04_cond4_transfer_day_effect.json, from the sha-pinned 250 amendment records), applied only for transfer
days at or before the evaluation time.

Usage:
  /usr/bin/python3 alm06_cum_decomposition.py <guard_twin_state_dir> <pilot_log_root_copy> <cond4_receipt.json> <out.json>
"""
import calendar
import hashlib
import json
import os
import sys
import time

STATE, PLOG, COND4, OUT = sys.argv[1:5]

REALISED_TYPES = ("REALIZED_PNL", "COMMISSION", "FUNDING_FEE")


def sha(p):
    raw = open(p, "rb").read()
    assert len(raw) == os.stat(p).st_size, f"short read {p}"
    return hashlib.sha256(raw).hexdigest()


def jl(p):
    out = []
    for l in open(p):
        l = l.strip()
        if l:
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    return out


def day_of_ms(ms):
    return time.strftime("%Y%m%d", time.gmtime(ms / 1000))


import bisect

snaps_all = jl(os.path.join(STATE, "snapshots.jsonl"))
inc_all = jl(os.path.join(STATE, "income.jsonl"))
cmp_all = jl(os.path.join(STATE, "compare.jsonl"))
cond4 = json.load(open(COND4))

# frozen LED-04 per-transfer-day table: the watchdog chain's factor for that day, recorded vs amended
LED04 = {r["day"]: (r["r_recorded_pct"] / 100.0, r["r_amended_pct"] / 100.0) for r in cond4["transfer_days"]}

dn_all = {}
for d in sorted(x for x in os.listdir(PLOG) if x.isdigit() and len(x) == 8):
    p = os.path.join(PLOG, d, "daily_nav.jsonl")
    if os.path.exists(p):
        rows = jl(p)
        if rows:
            dn_all[d] = rows


def dn_as_of(now_ts):
    out = {}
    for d, rows in dn_all.items():
        keep = [r for r in rows if r.get("nav_ts") is not None and float(r["nav_ts"]) <= now_ts]
        if keep:
            out[d] = keep
    return out


def wd_chain_arith_pct(dn, now_ts):
    """VERBATIM re-implementation of guard_twin.wd_chain_arith_pct (which itself mirrors watchdog cond4)."""
    prev, cum, n = None, 1.0, 0
    for d in sorted(dn):
        rows = [r for r in dn[d] if r.get("nav_ts") is not None and float(r["nav_ts"]) <= now_ts]
        if not rows:
            continue
        last = rows[-1]
        if last.get("realised_truncated") or not last.get("nav"):
            continue
        flow = any(abs(float(r.get("external_flow_usdt") or 0.0)) > 1e-9 for r in rows)
        if prev is not None:
            if flow:
                if last.get("realised_pnl") is None or last.get("unrealised_pnl") is None or prev[1] is None:
                    return None
                rd = (float(last["realised_pnl"]) + float(last["unrealised_pnl"]) - float(prev[1])) / prev[0]
            else:
                rd = float(last["nav"]) / prev[0] - 1.0
            cum *= 1.0 + rd
            n += 1
        prev = (float(last["nav"]), last.get("unrealised_pnl"))
    return round((cum - 1.0) * 100.0, 4) if n else None


# income indexed by day and bucket, with prefix sums, so a per-day figure "as of now_ts" is two bisects
_INC = {}
for _r in inc_all:
    _d = day_of_ms(_r["time"])
    if _r["type"] == "TRANSFER":
        _b = "TRANSFER"
    elif _r["type"] in REALISED_TYPES and _r.get("asset") == "USDT":
        _b = "REALISED"
    else:
        continue
    _INC.setdefault((_d, _b), []).append((float(_r["time"]), float(_r["income"])))
_INCP = {}
for _k, _v in _INC.items():
    _v.sort()
    _ts = [x[0] for x in _v]
    _cs, _acc = [], 0.0
    for _x in _v:
        _acc += _x[1]
        _cs.append(_acc)
    _INCP[_k] = (_ts, _cs)


def _inc_upto(day, bucket, now_ts):
    e = _INCP.get((day, bucket))
    if not e:
        return 0.0
    ts, cs = e
    i = bisect.bisect_right(ts, now_ts * 1000.0)
    return cs[i - 1] if i else 0.0


def chains(now_ts):
    """T / C1 / C2a / C2b as of now_ts, plus the shared prefix. Mirrors guard_twin's cum_twin_pct construction."""
    dn = dn_as_of(now_ts)
    snaps = [s for s in snaps_all if float(s["ts"]) <= now_ts]
    days = sorted(dn)
    twin_days = sorted({s["day"] for s in snaps})
    first_twin_day = twin_days[0] if twin_days else None
    if not first_twin_day:
        return None

    # ── shared prefix: identical in every chain (guard_twin's own loop, verbatim) ──
    twr, prev = 1.0, None
    prefix_flow_mismatch = []
    for d in days:
        if d >= first_twin_day:
            break
        r = dn[d][-1]
        nav = r.get("nav")
        if not nav:
            continue
        try:
            flow = float(r.get("external_flow_usdt") or 0.0)
        except Exception:
            flow = 0.0
        any_flow = any(abs(float(x.get("external_flow_usdt") or 0.0)) > 1e-9 for x in dn[d])
        if (abs(flow) > 1e-9) != any_flow:
            prefix_flow_mismatch.append(d)
        if prev is not None:
            if abs(flow) > 1e-9:
                re_, un = r.get("realised_pnl"), r.get("unrealised_pnl")
                if re_ is None or un is None or prev[1] is None:
                    prev = (float(nav), r.get("unrealised_pnl"))
                    continue
                rd = (float(re_) + float(un) - float(prev[1])) / prev[0]
            else:
                rd = float(nav) / prev[0] - 1.0
            twr *= 1 + rd
        prev = (float(nav), r.get("unrealised_pnl"))
    if prev is None:
        return None
    prefix_twr, prefix_prev = twr, prev

    by_day = {}
    for s in snaps:
        by_day[s["day"]] = s                      # last per day, as guard_twin does

    # ★ per-day prefix sums over the income ledger, built ONCE (109k rows); the first version rescanned the whole
    #   ledger per day per compare row (1,655 x ~44 x 109k) and did not finish. Same arithmetic, indexed.
    def transfers(d):
        return _inc_upto(d, "TRANSFER", now_ts)

    def realised_income(d):
        return _inc_upto(d, "REALISED", now_ts)

    # T: the twin as it runs
    t_twr, p_eq = prefix_twr, prefix_prev[0]
    for d in twin_days:
        e = by_day[d]["equity"]
        t_twr *= 1 + (e - p_eq - transfers(d)) / p_eq
        p_eq = e
    T = (t_twr - 1.0) * 100.0

    # C1 / C2a / C2b: daily_nav day closes over the SAME twin days
    def dn_last(d):
        return dn[d][-1] if d in dn else None

    c1, c2a, c2b = prefix_twr, prefix_twr, prefix_twr
    p1 = p2a = p2b = prefix_prev[0]
    p_un = prefix_prev[1]
    detail = []
    incomplete = None
    for d in twin_days:
        last = dn_last(d)
        if last is None or not last.get("nav"):
            incomplete = f"no daily_nav row for twin day {d} at or before now"
            break
        nav = float(last["nav"])
        any_flow = any(abs(float(x.get("external_flow_usdt") or 0.0)) > 1e-9 for x in dn[d])
        r1 = (nav - p1 - transfers(d)) / p1
        if any_flow:
            un, re_rec = last.get("unrealised_pnl"), last.get("realised_pnl")
            if un is None or re_rec is None or p_un is None:
                incomplete = f"transfer day {d} unpriceable for the watchdog formula"
                break
            r2a = (realised_income(d) + float(un) - float(p_un)) / p2a
            r2b = (float(re_rec) + float(un) - float(p_un)) / p2b
        else:
            r2a = nav / p2a - 1.0
            r2b = nav / p2b - 1.0
        c1 *= 1 + r1
        c2a *= 1 + r2a
        c2b *= 1 + r2b
        detail.append({"day": d, "is_transfer": any_flow, "r_T_pct": None, "r_C1_pct": r1 * 100.0,
                       "r_C2a_pct": r2a * 100.0, "r_C2b_pct": r2b * 100.0,
                       "realised_income_usdt": (realised_income(d) if any_flow else None),
                       "realised_recorded_usdt": (float(last["realised_pnl"]) if any_flow else None)})
        p1, p2a, p2b, p_un = nav, nav, nav, last.get("unrealised_pnl")
    return {"T": T, "C1": (c1 - 1.0) * 100.0, "C2a": (c2a - 1.0) * 100.0, "C2b": (c2b - 1.0) * 100.0,
            "wd_arith": wd_chain_arith_pct(dn, now_ts), "first_twin_day": first_twin_day,
            "n_twin_days": len(twin_days), "prefix_flow_mismatch_days": prefix_flow_mismatch,
            "incomplete": incomplete, "per_day": detail}


def led04_allowance_pp(wd_pct, now_ts):
    """How much the watchdog's cum would move if its pre-fix transfer days were priced from the amendment records.
    FROZEN table; applied only for transfer days at or before now_ts. None when the watchdog value is unreadable."""
    if wd_pct is None:
        return None, []
    ratio, used = 1.0, []
    for d, (r_rec, r_am) in sorted(LED04.items()):
        day_end = calendar.timegm(time.strptime(d + " 235959", "%Y%m%d %H%M%S"))
        if day_end > now_ts:
            continue
        ratio *= (1.0 + r_am) / (1.0 + r_rec)
        used.append(d)
    return ((1.0 + wd_pct / 100.0) * ratio - 1.0) * 100.0 - wd_pct, used


rows_out, cum_rows = [], []
for c in cmp_all:
    ts = c.get("ts") or c.get("utc")
    if isinstance(ts, str):
        # ★ calendar.timegm, NOT time.mktime(...) - time.timezone: the latter reads the struct as LOCAL time and the
        #   correction is only right when tm_isdst == 0, which strptime does not set. The first run used it and T
        #   reproduced the recorded twin on 0 of 1,654 rows.
        ts = calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
    if ts is None:
        continue
    twin_rec, wd_rec = c.get("cum_pct_twin"), c.get("wd_cum_from_start_pct")
    if twin_rec is None or wd_rec is None:
        continue
    ch = chains(float(ts))
    if ch is None:
        continue
    gap = float(twin_rec) - float(wd_rec)
    timing = ch["T"] - ch["C1"]
    formula = ch["C1"] - ch["C2a"]
    inp = ch["C2a"] - ch["C2b"]
    identity = (ch["C2b"] - ch["wd_arith"]) if ch["wd_arith"] is not None else None
    arith_gap = (ch["wd_arith"] - float(wd_rec)) if ch["wd_arith"] is not None else None
    allow, allow_days = led04_allowance_pp(float(wd_rec), float(ts))
    residual = None if allow is None else gap - timing - formula - allow
    one = {"utc": c.get("utc"), "ts": ts, "comparable": c.get("comparable"),
           "cum_pct_twin_recorded": twin_rec, "wd_cum_recorded": wd_rec, "gap_pp": gap,
           "T_reproduced": ch["T"], "T_minus_recorded_pp": ch["T"] - float(twin_rec),
           "reproduces_recorded_twin": abs(ch["T"] - float(twin_rec)) < 1e-6,
           "C1": ch["C1"], "C2a": ch["C2a"], "C2b": ch["C2b"], "wd_chain_arith": ch["wd_arith"],
           "cause_day_close_timing_pp": timing, "cause_transfer_day_formula_pp": formula,
           "cause_input_bias_pp": inp, "identity_C2b_minus_wd_arith_pp": identity,
           "alert_i_arith_vs_wd_pp": arith_gap,
           "led04_allowance_pp": allow, "led04_days_applied": allow_days,
           "residual_pp": residual, "incomplete": ch["incomplete"],
           "prefix_flow_mismatch_days": ch["prefix_flow_mismatch_days"], "n_twin_days": ch["n_twin_days"]}
    rows_out.append(one)

fin = [r for r in rows_out if r["residual_pp"] is not None]
rec = {"device": os.path.basename(__file__),
       "device_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "inputs": {"snapshots.jsonl": sha(os.path.join(STATE, "snapshots.jsonl")),
                  "income.jsonl": sha(os.path.join(STATE, "income.jsonl")),
                  "compare.jsonl": sha(os.path.join(STATE, "compare.jsonl")),
                  "cond4_receipt": sha(COND4), "pilot_log_root": PLOG},
       "n_compare_rows": len(cmp_all), "n_decomposed": len(rows_out),
       "n_reproducing_recorded_twin": sum(1 for r in rows_out if r["reproduces_recorded_twin"]),
       "led04_frozen_table_days": sorted(LED04),
       "summary": {
           "max_abs_T_minus_recorded_pp": max((abs(r["T_minus_recorded_pp"]) for r in rows_out), default=None),
           "max_abs_identity_pp": max((abs(r["identity_C2b_minus_wd_arith_pp"]) for r in rows_out
                                       if r["identity_C2b_minus_wd_arith_pp"] is not None), default=None),
           "max_abs_residual_pp": max((abs(r["residual_pp"]) for r in fin), default=None),
           "max_abs_alert_i_pp": max((abs(r["alert_i_arith_vs_wd_pp"]) for r in rows_out
                                      if r["alert_i_arith_vs_wd_pp"] is not None), default=None)},
       "rows": rows_out}
json.dump(rec, open(OUT, "w"), ensure_ascii=False, indent=1)

print(f"compare rows {len(cmp_all)} | decomposed {len(rows_out)} | "
      f"T reproduces recorded twin {rec['n_reproducing_recorded_twin']}/{len(rows_out)}")
print(f"max |T - recorded twin|      {rec['summary']['max_abs_T_minus_recorded_pp']}")
print(f"max |identity C2b - wd_arith| {rec['summary']['max_abs_identity_pp']}")
print(f"max |alert (i) arith - wd|    {rec['summary']['max_abs_alert_i_pp']}")
print(f"max |residual (ii)|           {rec['summary']['max_abs_residual_pp']}")
print(f"receipt -> {OUT}")
