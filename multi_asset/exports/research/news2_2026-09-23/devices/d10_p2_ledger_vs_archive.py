#!/usr/bin/env python3
"""d10_p2_ledger_vs_archive.py -- does the BACKTEST's funding ledger contain the switch-window settlements?

The live producer's ledger was audited for 2026-08 (D10_LIVE_LEDGER_VS_ARCHIVE_2026-08, 305/305 complete).
This asks the same question of the OTHER ledger: the one every historical replay prices funding from.

WHAT THE BACKTEST ACTUALLY READS, cited rather than inferred from the file name:
  r_hist_sim.py:115  Z = np.load(ledger_npz); off = Z["off"]; ft = Z["ft"]; rt = Z["rate"]
  r_hist_sim.py:117  jj = np.repeat(np.arange(len(syms)), np.diff(off)); m = (ft > t_lo) & (ft <= t_hi)
  r_hist_sim.py:118  self.rate = RateMap(ft[m][o], jj[m][o], rt[m][o], list(syms))
So HistFunding consumes off/ft/rate/symbols ONLY. It never reads `src` and never reads `zip_iv`: the
interval column is provenance, not an input to the pricing. That is why this device audits EVENT PRESENCE
(is each settlement there, at its own second, with its own rate) and reports src composition separately as
provenance -- not as a correctness measure.

WHAT src AND zip_iv MEAN, from the builder that writes them (p2_prep_inputs.py L7, L70-77, L89):
  src 1 = API (fund_aug) only, 2 = zip only, 3 = both present and equal, 4 = both present and UNEQUAL
          (the API rate is kept); union is by second (t_ms // 1000); zip_iv is NaN exactly when the row is
          not in the zip, i.e. NaN <=> src == 1, BY CONSTRUCTION -- so a NaN zip_iv is not a missing
          interval, it is an API-only row. (I have had a retraction for reading zip_iv as a measurement.)

POPULATION GUARDS -- without these, coverage masquerades as missing data. This is the same shape as the
371 cells I once misclassified because a symbol's archive simply ended:
  1. only symbols on BOTH the ledger's 829 axis and the month's archive are comparable; the rest are
     reported by count and reason, never silently dropped;
  2. a symbol whose LEDGER rows do not span the window (its own first/last row) is out-of-coverage for
     that window, not missing -- classified separately;
  3. the reverse direction is counted too: ledger rows in a window with no archive counterpart. Those are
     expected (the union adds API rows the monthly zip lacks) and are NOT errors, but an audit that only
     looks one way cannot tell a superset from a match.

The archive side is read only through the R25-11 gate: an unverified month is refused, not skipped.
"""
import argparse
import collections
import csv
import datetime
import glob
import hashlib
import io
import json
import math
import os
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import d10_manifest_gate as GATE
for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW  # every file this device writes goes through it (news2 class fix 2026-09-27)

WIN = 24 * 3600


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def u(ts):
    return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def month_bounds(m):
    lo = datetime.datetime.strptime(m, "%Y-%m").replace(tzinfo=datetime.timezone.utc)
    hi = (lo + datetime.timedelta(days=32)).replace(day=1)
    return int(lo.timestamp()), int(hi.timestamp())


def read_month(zipdir, month):
    """archive events for one verified month: symbol -> sorted [(sec, iv_hours, rate)]"""
    GATE.require_verified(zipdir, month, what=f"p2-ledger-audit {month}")
    arc = {}
    for zp in sorted(glob.glob(os.path.join(zipdir, f"*-fundingRate-{month}.zip"))):
        s = os.path.basename(zp).split("-fundingRate-")[0]
        z = zipfile.ZipFile(zp)
        ev = []
        for row in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8"))):
            if row and row[0].strip().isdigit():
                ev.append((int(row[0]) // 1000, float(row[1]), float(row[2]), int(row[0])))
        ev.sort()
        arc[s] = ev
    return arc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--ledger-sha", default=None, help="the pinned sha256; asserted, not trusted")
    ap.add_argument("--zips-root", required=True)
    ap.add_argument("--months", required=True, help="comma separated, e.g. 2026-01,2026-02")
    ap.add_argument("--out", default=None)
    ap.add_argument("--positive-control", action="store_true",
                    help="perturb a few archive values and assert the comparison SEES them. A bitwise-equal "
                         "result across 100k values is only meaningful if the comparison could have failed: "
                         "otherwise 'the two chains agree' is indistinguishable from 'my comparison compares "
                         "a value to itself'. The control must detect 1 ULP.")
    a = ap.parse_args()
    months = [m.strip() for m in a.months.split(",") if m.strip()]

    lsha = sha(a.ledger)
    if a.ledger_sha:
        assert lsha.startswith(a.ledger_sha), ("ledger is not the pinned artifact", lsha, a.ledger_sha)

    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "gate_sha256": sha(os.path.realpath(GATE.__file__)), "argv": sys.argv[1:],
           "question": "does P2 ledger_full.npz contain the settlements in +/-24h interval-switch windows?",
           "ledger": {"path": a.ledger, "sha256": lsha, "pin_asserted": bool(a.ledger_sha)},
           "ledger_key": None,
           "consumed_by": ["r_hist_sim.py:115-118 HistFunding reads off/ft/rate/symbols only",
                           "src and zip_iv are provenance; the pricing never reads them"],
           "src_codes": {"1": "API(fund_aug) only", "2": "zip only", "3": "both equal",
                         "4": "both unequal, API kept", "source": "p2_prep_inputs.py L7,L70-77"},
           "months": months}

    Z = np.load(a.ledger, allow_pickle=True)
    # Accept either artifact: the OLD ledger keys by SECONDS (`ft`), the NEW one by MILLISECONDS (`ft_ms`,
    # lead's revision 1). Detected by which key is present and RECORDED in the receipt, never guessed --
    # reading a millisecond array as seconds puts every event ~55,000 years ahead and would still "run".
    if "ft_ms" in Z.files:
        ledger_key = "ft_ms"
        ft = Z["ft_ms"].astype(np.int64) // 1000      # floor, as p2_prep_inputs.py does
    elif "ft" in Z.files:
        ledger_key = "ft"
        ft = Z["ft"].astype(np.int64)
    else:
        raise KeyError(f"ledger has neither ft nor ft_ms: {list(Z.files)}")
    assert int(ft.max()) < 2_000_000_000, (
        "ledger timestamps do not look like seconds after conversion; refusing to compare", ledger_key)
    rec["ledger_key"] = ledger_key
    off, rate, src = Z["off"].astype(np.int64), Z["rate"].astype(np.float64), Z["src"].astype(np.int8)
    zip_iv = Z["zip_iv"].astype(np.float64)
    syms = [str(s) for s in Z["symbols"]]
    idx = {s: j for j, s in enumerate(syms)}
    rec["ledger"].update({"symbols": len(syms), "rows": int(ft.size),
                          "ft_min_utc": u(ft.min()), "ft_max_utc": u(ft.max())})
    # NaN zip_iv <=> src==1, asserted rather than assumed (it is the builder's construction)
    rec["ledger"]["nan_zip_iv_iff_src1"] = bool(np.array_equal(~np.isfinite(zip_iv), src == 1))

    per_sym_sec = {}
    per_sym_span = {}
    for s, j in idx.items():
        seg = ft[off[j]:off[j + 1]]
        per_sym_sec[s] = set(int(x) for x in seg)
        per_sym_span[s] = (int(seg[0]), int(seg[-1])) if seg.size else None

    rec["per_month"] = {}
    tot = collections.Counter()
    worst = []
    for m in months:
        zd = os.path.join(a.zips_root, m)
        arc = read_month(zd, m)
        lo, hi = month_bounds(m)

        ctrl = None
        if a.positive_control:
            # perturb the ARCHIVE side in memory: 1 ULP, then a small relative nudge, then a dropped event.
            # Each must be SEEN, otherwise the bitwise-equal headline is an instrument ceiling.
            ctrl = {"perturbed": [], "dropped": []}
            picks = [s for s in sorted(set(arc) & set(idx)) if arc[s]][:3]
            for k, s in enumerate(picks):
                ev = list(arc[s])
                i = len(ev) // 2
                sec, iv, r = ev[i]
                if k == 0:
                    r2 = math.nextafter(r, math.inf) if r == r else r      # exactly 1 ULP
                    kind = "1_ulp"
                elif k == 1:
                    r2 = r + 1e-9                                          # tiny but not minimal
                    kind = "plus_1e-9"
                else:
                    continue            # the dropped-event control runs AFTER switch detection, below
                ev[i] = (sec, iv, r2)
                arc[s] = ev
                ctrl["perturbed"].append({"symbol": s, "utc": u(sec), "kind": kind,
                                          "from": r, "to": r2, "delta": r2 - r})

        shared = sorted(set(arc) & set(idx))
        only_arc = sorted(set(arc) - set(idx))
        only_led = 0  # counted below over the month window
        c = collections.Counter()
        absent_examples = []
        by_symbol_absent = collections.Counter()

        # switch events from the verified archive
        switches = {}
        for s in shared:
            ev = arc[s]
            sw = [ev[i][0] for i in range(1, len(ev)) if ev[i][1] != ev[i - 1][1]]
            if sw:
                switches[s] = sw
        n_sw = sum(len(v) for v in switches.values())

        if a.positive_control:
            # The headline of this device is ABSENT_from_ledger == 0, and the FIRST version of this control
            # failed to exercise it: I removed the event from the ARCHIVE, which is the side that DEFINES
            # the population, so the window count merely shrank (832 -> 830) and no absence appeared. To
            # create a detectable absence the event must be removed from the side that is SEARCHED -- the
            # ledger's own second-set. Same shape as perturbing a null by moving the population instead of
            # the value: the denominator moves and the detector is a no-op.
            done = False
            for s in sorted(switches):
                if done:
                    break
                bounds = set(switches[s])
                for sw in switches[s]:
                    cand = [e for e in arc[s]
                            if sw - WIN <= e[0] <= sw + WIN and e[0] not in bounds and e[0] in per_sym_sec[s]]
                    if len(cand) >= 2:
                        victim = cand[len(cand) // 2]
                        per_sym_sec[s] = set(per_sym_sec[s])      # do not mutate a shared object
                        per_sym_sec[s].discard(victim[0])         # the LEDGER no longer has it
                        ctrl["dropped"].append({"symbol": s, "utc": u(victim[0]), "sec": victim[0],
                                                "removed_from": "ledger second-set (the searched side)",
                                                "inside_switch_window_of": u(sw),
                                                "expect": "ABSENT_from_ledger >= 1"})
                        done = True
                        break
            ctrl["in_window_drop_placed"] = done

        for s, sws in switches.items():
            span = per_sym_span[s]
            secs = per_sym_sec[s]
            ev = arc[s]
            for sw in sws:
                w_lo, w_hi = sw - WIN, sw + WIN
                inwin = [e for e in ev if w_lo <= e[0] <= w_hi]
                for (sec, iv, r, ms) in inwin:
                    c["archive_events_in_windows"] += 1
                    if span is None or not (span[0] <= sec <= span[1]):
                        c["out_of_ledger_coverage"] += 1          # guard 2: coverage, not absence
                    elif sec in secs:
                        c["present_in_ledger"] += 1
                    else:
                        c["ABSENT_from_ledger"] += 1
                        by_symbol_absent[s] += 1
                        if len(absent_examples) < 25:
                            absent_examples.append({"symbol": s, "utc": u(sec), "sec": sec,
                                                    "archive_iv_h": iv, "archive_rate": r,
                                                    "switch_utc": u(sw),
                                                    "ledger_span": [u(span[0]), u(span[1])] if span else None})
        # closure: the three classes must exhaust the population
        assert (c["present_in_ledger"] + c["ABSENT_from_ledger"] + c["out_of_ledger_coverage"]
                == c["archive_events_in_windows"]), "switch-window classification does not close"

        # reverse direction + src composition, over the whole month on the shared axis
        comp = collections.Counter()
        led_month_rows = 0
        led_not_in_archive = 0
        for s in shared:
            j = idx[s]
            seg_ft = ft[off[j]:off[j + 1]]
            seg_src = src[off[j]:off[j + 1]]
            sel = (seg_ft >= lo) & (seg_ft < hi)
            led_month_rows += int(sel.sum())
            for v, n in zip(*np.unique(seg_src[sel], return_counts=True)):
                comp[int(v)] += int(n)
            asec = {e[0] for e in arc[s]}
            led_not_in_archive += int(sum(1 for t in seg_ft[sel] if int(t) not in asec))

        arc_month_events = sum(1 for s in shared for e in arc[s] if lo <= e[0] < hi)

        # RATE agreement on the shared seconds. Event presence is weaker than agreement: two sources can
        # list the same settlements and disagree on what was paid, and the rate is what prices the
        # backtest. This matters most where the ledger has NO zip corroboration (src==1 everywhere), because
        # then the builder's own src==4 check had nothing to compare against and cannot speak.
        n_cmp = n_exact = 0
        worst_d = 0.0
        worst_where = None
        rate_mismatch = []
        for s in shared:
            j = idx[s]
            seg_ft = ft[off[j]:off[j + 1]]
            seg_rt = rate[off[j]:off[j + 1]]
            sel = (seg_ft >= lo) & (seg_ft < hi)
            # ★ Key the rate comparison by MILLISECOND when the ledger carries ms. Comparing two
            # second-keyed projections is not a comparison of the data: the two sides resolve a
            # within-second collision differently (the ledger takes the LATER ms per lead's rule, the
            # archive read took the first encountered), which showed up as 2 spurious "differences" on
            # exactly the MSFT/AAPL seconds. With both sides on ms the ambiguity cannot arise.
            if ledger_key == "ft_ms":
                seg_ms = Z["ft_ms"].astype(np.int64)[off[j]:off[j + 1]][sel]
                lmap = {int(t): float(r) for t, r in zip(seg_ms, seg_rt[sel])}
                pairs = [(ms, r) for (sec, iv, r, ms) in arc[s] if lo <= sec < hi]
            else:
                lmap = {int(t): float(r) for t, r in zip(seg_ft[sel], seg_rt[sel])}
                pairs = [(sec, r) for (sec, iv, r, ms) in arc[s] if lo <= sec < hi]
            for (key_t, r) in pairs:
                sec = key_t if ledger_key != "ft_ms" else key_t // 1000
                if key_t not in lmap:
                    continue
                n_cmp += 1
                d = abs(lmap[key_t] - r)
                if lmap[key_t] == r:
                    n_exact += 1
                elif len(rate_mismatch) < 20:
                    rate_mismatch.append({"symbol": s, "utc": u(sec), "key": int(key_t),
                                          "ledger": lmap[key_t],
                                          "archive": r, "abs_diff": d})
                if d > worst_d:
                    worst_d, worst_where = d, f"{s}@{u(sec)} ledger={lmap[key_t]!r} archive={r!r}"
        rec["per_month"][m] = {
            "archive_symbols": len(arc), "shared_symbols": len(shared),
            "archive_symbols_not_on_ledger_axis": len(only_arc),
            "archive_symbols_not_on_ledger_axis_examples": only_arc[:10],
            "switch_events": n_sw, "symbols_with_a_switch": len(switches),
            "switch_windows": {k: int(v) for k, v in c.items()},
            "absent_rate_pct": round(100.0 * c["ABSENT_from_ledger"] / c["archive_events_in_windows"], 4)
                               if c["archive_events_in_windows"] else None,
            "absent_by_symbol_top10": by_symbol_absent.most_common(10),
            "absent_examples": absent_examples,
            "month_totals_shared_axis": {
                "archive_events": arc_month_events, "ledger_rows": led_month_rows,
                "ledger_rows_with_no_archive_event": led_not_in_archive,
                "note": "ledger is a union (zip u API), so rows the monthly zip lacks are EXPECTED, not errors"},
            "src_composition": {"1_api_only": comp[1], "2_zip_only": comp[2],
                                "3_both_equal": comp[3], "4_both_unequal_api_kept": comp[4]},
            "positive_control": ctrl,
            "rate_key": ("MILLISECOND" if ledger_key == "ft_ms" else "SECOND"),
            "rate_agreement_on_shared_seconds": {
                "compared": n_cmp, "bitwise_equal": n_exact, "differing": n_cmp - n_exact,
                "max_abs_diff": worst_d, "max_abs_diff_where": worst_where,
                "examples": rate_mismatch,
                "why_it_matters": ("the rate is what prices the backtest; and where src==1 everywhere the "
                                  "builder's own src==4 check had no zip to compare against, so only this "
                                  "comparison can speak")},
        }
        for k, v in c.items():
            tot[k] += v
        if c["ABSENT_from_ledger"]:
            worst.append((c["ABSENT_from_ledger"], m))

    rec["all_months"] = {k: int(v) for k, v in tot.items()}
    n = tot["archive_events_in_windows"]
    rec["verdict"] = ("P2_LEDGER_COMPLETE_IN_SWITCH_WINDOWS" if tot["ABSENT_from_ledger"] == 0 and n
                      else ("NO_COMPARABLE_EVENTS" if not n else "P2_LEDGER_HAS_ABSENT_SETTLEMENTS"))
    rec["absent_rate_pct_all"] = round(100.0 * tot["ABSENT_from_ledger"] / n, 4) if n else None

    if a.positive_control:
        # This MUST come after the verdict is computed, or it gets clobbered by it -- it did, in the first
        # run: the control receipt's verdict field read "P2_LEDGER_HAS_ABSENT_SETTLEMENTS", which is
        # quotable as a real finding about the data when it is nothing but my own injected perturbation.
        seen_absent = tot["ABSENT_from_ledger"] >= 1
        seen_rate = any(rec["per_month"][m]["rate_agreement_on_shared_seconds"]["differing"] >= 1 for m in months)
        rec["positive_control_result"] = {
            "absent_channel_detected_the_dropped_in_window_event": bool(seen_absent),
            "rate_channel_detected_1_ULP_and_1e-9": bool(seen_rate),
            "verdict": "CONTROL_PASS" if (seen_absent and seen_rate) else "CONTROL_FAIL",
            "data_verdict_this_run_would_have_reported": rec["verdict"],
            "meaning": ("with the control on this run is NOT an audit of the data: every red counter here is "
                        "an injected perturbation. It measures whether the comparison can see a difference "
                        "at all. The clean run's 0-ABSENT / bitwise-equal headline is meaningful only "
                        "because this run is red.")}
        rec["verdict"] = "POSITIVE_CONTROL_RUN_NOT_AN_AUDIT"
        rec["absent_rate_pct_all"] = None

    print(f"P2 ledger vs archive, +/-24h around interval switches, months={','.join(months)}")
    print(f"  ledger {a.ledger}")
    print(f"    sha {lsha[:16]}  pin_asserted={bool(a.ledger_sha)}  symbols={len(syms)} rows={ft.size}")
    print(f"    span {rec['ledger']['ft_min_utc']} .. {rec['ledger']['ft_max_utc']}   "
          f"NaN zip_iv <=> src==1: {rec['ledger']['nan_zip_iv_iff_src1']}")
    for m in months:
        d = rec["per_month"][m]
        w = d["switch_windows"]
        print(f"  {m}: archive_syms={d['archive_symbols']} shared={d['shared_symbols']} "
              f"not_on_axis={d['archive_symbols_not_on_ledger_axis']}  switches={d['switch_events']} "
              f"in {d['symbols_with_a_switch']} syms")
        print(f"       windows: events={w.get('archive_events_in_windows',0)} "
              f"present={w.get('present_in_ledger',0)} ABSENT={w.get('ABSENT_from_ledger',0)} "
              f"out_of_coverage={w.get('out_of_ledger_coverage',0)}  absent_rate={d['absent_rate_pct']}%")
        sc = d["src_composition"]
        t = sum(sc.values()) or 1
        print(f"       src: api_only={sc['1_api_only']} ({100.0*sc['1_api_only']/t:.1f}%)  "
              f"zip_only={sc['2_zip_only']}  both_equal={sc['3_both_equal']} "
              f"({100.0*sc['3_both_equal']/t:.1f}%)  both_UNEQUAL={sc['4_both_unequal_api_kept']}")
        mt = d["month_totals_shared_axis"]
        print(f"       month: archive_events={mt['archive_events']} ledger_rows={mt['ledger_rows']} "
              f"ledger_rows_with_no_archive_event={mt['ledger_rows_with_no_archive_event']}")
        ra = d["rate_agreement_on_shared_seconds"]
        print(f"       rates: compared={ra['compared']} bitwise_equal={ra['bitwise_equal']} "
              f"differing={ra['differing']} max_abs_diff={ra['max_abs_diff']:.3e}")
        if ra["max_abs_diff_where"]:
            print(f"              worst: {ra['max_abs_diff_where']}")
    print(f"  ALL: {rec['all_months']}")
    print(f"  VERDICT {rec['verdict']}  absent_rate={rec['absent_rate_pct_all']}%")

    if a.out:
        print(f"  receipt -> {a.out}  sha256={DW.write_json(a.out, rec, indent=1, allow_nan=True)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
