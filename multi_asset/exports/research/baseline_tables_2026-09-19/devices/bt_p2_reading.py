#!/usr/bin/env python3
"""bt_p2_reading.py — reading P2 (AMENDMENT 3, docs/AMENDMENT_3_baseline_tables_reading_P2_2026-09-20.md, sha 4ea9b1c5): BOTH live stop
rules together, with a named resume assumption. Post-processing of the per-path window ledgers; NO re-simulation.

  §4-2 daily stop, live-like resume: at every day-stop flatten (time t, taken from the simulator's own `flatten_log`) the path stops trading
       until the FIRST ANCHOR ≥ t + H; a withheld anchor's window return is 0 (a flat book earns no price P&L, no funding, no fees).
       H = 12 h is the main reading; H ∈ {8, 20} h is the sensitivity (the observed band); H = "sim" is the simulator's own rule (resume at
       the next 00Z), which reproduces the published reading P; H = "never" is the strict lower bound — the first day-stop ends the path,
       which is the literal reading of a policy that requires a human to resume (round-6 review R6-03).
  §4-4 cumulative −25 % from the base's starting equity, strictly below, NO resume — identical to reading P.
  Both rules are active at once; whichever fires first stops the path.
  FLATTEN COSTS: for every flatten window the turnover attributed to the flatten (`turnover_flatten`, over gross) and that window's fee
       (bps of gross) are reported, because neither P nor P2 subtracts an exit cost at the halt — the halt level is a mark, not a fill.

AMENDMENT 4 (docs/AMENDMENT_4_baseline_tables_aggregation_contract_2026-09-20.md), after E-0920-C:
  §B WINDOW SLICING is now EXPLICIT and BOTH readings are reported, per base, per H:
      W_ENTRY (MAIN) — the base anchor is an ENTRY POINT: only day-stops at or after the base anchor withhold anything; a halt that began
                       before the window is NOT inherited. This is the reading that shares its clock with §4-4, whose −25 % counter also
                       restarts at the base (cum = navm1/navm0_base − 1).
      W_CARRY        — the window is a viewing slice of one continuous path: a halt that began before it and never resumed is carried in.
                       This is what the pre-fix device computed, without ever saying so.
      B4-a/B4-b assertions: at a base that IS the path start, and at H = "sim", the two readings must agree BIT FOR BIT, or the device
                       refuses. (Under W_CARRY at the FULL_RECIPE base this is exactly where E-0920-C lived: seeds 3/5/12/17 had their
                       first day-stop before the window, so all 6,948 window anchors were withheld and the window return was identically
                       0 — which the pre-fix summary averaged in as though it were a small loss.)
  §A AGGREGATION CONTRACT: every aggregate goes through bt_agg.block() — a closed population, a NAMED no-measurement subset that never
      enters a mean, the measured figure AND the whole-population figure under a named convention, and n_eff beside every persisted mean.
      A structural sweep of the WHOLE document runs before it is written; nothing is written if it fails.
usage: /workspace/venv/bin/python -B bt_p2_reading.py PATH,HOME,LC_CTYPE <p2_config.json> <out.json>
"""
import os, sys, json, time, calendar, hashlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_p_reading as PR
import bt_agg as AG

T0 = time.time()
H4 = 14400

SEMANTICS = ("W_ENTRY", "W_CARRY")
SEM_PROSE = {"W_ENTRY": "entry point: only day-stops at or after the base anchor withhold; a halt that began before the window is NOT inherited (MAIN, AMENDMENT 4 §B-3)",
             "W_CARRY": "path-continuous: the window is a slice of one path, so a halt that began before it and never resumed is carried in (what the pre-fix device computed)"}
# the ONE declared convention under which a whole-population figure exists at all for a window-end return (AMENDMENT 4 §A3')
FLAT_BOOK_CONVENTION = {"name": "a path whose every window anchor was withheld contributes its flat-book window return of exactly 0 "
                                "(true of a flat book, but it is the absence of trading, not an outcome of the strategy from this entry point)",
                        "value_for_unmeasured": 0.0}

NBLOCKS = [0]                                   # how many bt_agg.block() aggregates this run built; checked against the sweep


def blk(*a, **kw):
    NBLOCKS[0] += 1
    return AG.block(*a, **kw)


class P2Error(Exception):
    pass


def load_paths2(run_dir, n_seeds):
    """(A, navm0, navm1, status, turnover_flatten, fee, nav0, flatten times) per path, sha-checked against each path's own json"""
    tag = os.path.basename(run_dir.rstrip("/")); out = []
    for s in range(n_seeds):
        st = os.path.join(run_dir, f"PATH_{tag}_seed_{s:02d}")
        J = json.load(open(st + ".json"))
        if J.get("npz_sha256") != PR.sha(st + ".npz"): raise P2Error(f"npz sha != its json: {st}")
        Z = np.load(st + ".npz")
        fl = [(PR.ts(t if t.endswith("Z") else t + "Z"), why) for t, why in J.get("flatten_log", [])]
        out.append({"seed": s, "A": Z["A"].astype(np.int64), "navm0": Z["navm0"].astype(np.float64), "navm1": Z["navm1"].astype(np.float64),
                    "status": Z["status"].astype(np.int8), "turn_flat": Z["turnover_flatten"].astype(np.float64), "fee": Z["fee"].astype(np.float64),
                    "nav0": Z["nav0"].astype(np.float64), "gross0": Z["gross0"].astype(np.float64), "flatten": fl})
    if not out: raise P2Error("no paths")
    for p in out[1:]:
        if not np.array_equal(p["A"], out[0]["A"]): raise P2Error("paths do not share one anchor axis")
    return out


def flattens_in_scope(p, base_t, sem):
    """AMENDMENT 4 §B: which day-stops the resume rule is allowed to see, given the window-slicing semantics"""
    if sem == "W_CARRY": return list(p["flatten"])
    if sem == "W_ENTRY": return [(t, w) for t, w in p["flatten"] if t >= base_t]
    raise P2Error(f"unknown window semantics {sem!r}")


def withheld_mask(p, H, base_t, sem):
    """which anchors the live-like resume rule withholds; H in hours, or 'sim' (no extra withholding) or 'never'"""
    A = p["A"]; m = np.zeros(len(A), bool); per_event = []
    fl = flattens_in_scope(p, base_t, sem)
    if H == "sim" or not fl:
        return m, per_event
    if H == "never":
        t0 = min(t for t, _ in fl); m |= (A >= t0)
        per_event.append({"flatten_utc": PR.iso(t0), "anchors_withheld": int(m.sum()), "rule": "never resumes", "window_semantics": sem})
        return m, per_event
    for t, _why in sorted(fl):
        w = (A >= t) & (A < t + int(float(H) * 3600))
        per_event.append({"flatten_utc": PR.iso(t), "anchors_withheld": int(w.sum()),
                          "resume_anchor": (PR.iso(A[A >= t + int(float(H) * 3600)][0]) if np.any(A >= t + int(float(H) * 3600)) else None)})
        m |= w
    return m, per_event


def p2_returns(p, H, base_t, sem):
    """the per-window returns after the live-like resume rule: withheld anchors earn exactly 0"""
    r = p["navm1"] / p["navm0"] - 1.0
    m, per_event = withheld_mask(p, H, base_t, sem)
    return np.where(m, 0.0, r), m, per_event


def p2_of(p, base_i, thr, H, sem, upto_i=None, series=None, traded_members=None):
    """the P2 path: withheld anchors earn 0, then §4-4 halts for good at the first window end strictly below the threshold.

    A path that traded NO anchor of this window has NO window-end return. It is NOT recorded as 0.0 (E-0920-C): `end_return_P2` is
    None and `no_measurement_reason` names why, so the aggregator can keep it out of the headline mean.

    THE MEAN PATH is a different object and needs `traded_members`: its series is the per-anchor MEAN over all paths, in which a
    withheld path contributes its own flat-book 0 — so it is a WHOLE-POPULATION quantity under the same named convention, and its
    own "≥ half the paths withhold this anchor" mask does NOT decide whether it has a measurement. It has one iff at least one
    member path traded, and the census beside it says how many did. (Reading it off its own mask would have re-created E-0920-C in
    the mean path: on the late quarterly starts the pre-fix device printed a mean-path number for windows in which 28-32 of the 32
    members never traded, and 0.0 for windows in which none did.)"""
    A = p["A"]; hi = len(A) if upto_i is None else upto_i + 1
    r = p["navm1"] / p["navm0"] - 1.0
    if series is None:
        r2_full, m, per_event = p2_returns(p, H, A[base_i], sem)
    else:
        r2_full, m, per_event = series                       # a pre-built series (the mean path: the per-window mean of the path r2)
    r2 = r2_full[base_i:hi]; mw = m[base_i:hi]
    n_win = int(hi - base_i); traded = int((~mw).sum())
    nav = np.cumprod(1.0 + r2)                                    # NAV relative to the base's starting equity
    cum = nav - 1.0
    k = np.nonzero(cum < thr)[0]
    fired44 = bool(len(k)); j = int(k[0]) if fired44 else None
    if traded_members is None:                                    # a single path: it is measured iff it traded an anchor
        measured = bool(n_win > 0 and traded > 0)
    else:                                                         # the mean path: measured iff at least one MEMBER path traded
        measured = bool(n_win > 0 and int(traded_members) > 0)
    reason = None
    if not measured:
        fl = flattens_in_scope(p, A[base_i], sem)
        t0 = (min(t for t, _ in fl) if fl else None)
        reason = (("no member path traded a single anchor of this window, so the mean path has no window end either (%d anchors, "
                   "semantics %s)" % (n_win, sem)) if traded_members is not None else
                  ("no anchor of this window was ever traded: the resume rule withheld all %d of them (first day-stop in scope %s, "
                   "window starts %s, semantics %s)" % (n_win, (PR.iso(t0) if t0 is not None else "none"), PR.iso(A[base_i]), sem)))
    end_p2 = None
    if measured:
        end_p2 = float(cum[j]) if fired44 else (float(cum[-1]) if len(cum) else None)
    return {"window_semantics": sem,
            "resume_rule": ("sim (next 00Z) = reading P" if H == "sim" else ("never resumes" if H == "never" else f"{H} h")),
            "anchors_in_window": n_win, "anchors_traded_in_window": traded,
            "anchors_withheld_by_day_stop": int(mw.sum()),
            "day_stop_events_in_window": int(sum(1 for t, _ in p["flatten"] if A[base_i] <= t <= A[hi - 1])),
            "day_stop_events_in_scope": len(flattens_in_scope(p, A[base_i], sem)),
            "per_event": per_event, "fired_day_stop": bool(np.any(mw)),
            "has_measurement": measured, "no_measurement_reason": reason,
            "fired_cum25": (fired44 if measured else False),
            "cum25_anchor": (PR.iso(A[base_i + j]) if (fired44 and measured) else None),
            "cum25_anchor_epoch": (float(A[base_i + j]) if (fired44 and measured) else None),
            "cum_at_cum25": (float(cum[j]) if (fired44 and measured) else None),
            "end_return_P2": end_p2,
            "end_return_no_halt": (float(np.prod(1.0 + r[base_i:hi]) - 1.0) if hi > base_i else None),
            # E-0921-B: which anchor this terminal value was read at, and what that anchor is supposed to be. Derived from
            # the slice actually taken, so the label cannot drift from the arithmetic. PR.assert_window_ends checks it.
            "window_last_anchor": (PR.iso(A[hi - 1]) if hi - 1 >= 0 else None), "window_last_index": int(hi - 1),
            "window_scope": ("run_window_end" if upto_i is None else "configured_cutoff")}


def mean_p2_series(paths, H, base_t, sem):
    """the tables' mean-path caliber applied to P2: the per-window MEAN over paths of the P2-adjusted returns (not of the raw returns).
    A withheld anchor contributes its own flat-book 0 here, which IS that path's return at that anchor — the per-anchor mean is a mean
    over a fully measured population. What the census below reports is how many paths traded nothing at all in the window, because the
    mean path of a population in which some members never traded is a different object from the mean path of one where all did."""
    R = np.stack([p2_returns(p, H, base_t, sem)[0] for p in paths]); M = np.stack([p2_returns(p, H, base_t, sem)[1] for p in paths])
    return R.mean(0), M.mean(0) >= 0.5, [{"note": "mean path: an anchor counts as withheld when at least half the paths withhold it"}]


def flatten_costs(p, lo_t=None, hi_t=None):
    """what each flatten cost inside its own window: the flatten turnover over gross and that window's fee in bps of gross.
    lo_t/hi_t restrict it to a reporting window (AMENDMENT 4 §B-5: the pre-fix device walked the WHOLE path while the result doc quoted
    the number as a full-recipe-window fact)."""
    idx = np.nonzero(p["turn_flat"] > 0)[0]; gm_nav = 2.0 * p["nav0"]
    out = []
    for i in idx.tolist():
        t = int(p["A"][i])
        if lo_t is not None and t < lo_t: continue
        if hi_t is not None and t > hi_t: continue
        out.append({"anchor": PR.iso(p["A"][i]), "turnover_flatten_over_gross": float(p["turn_flat"][i] / gm_nav[i]),
                    "window_fee_bps_of_gross": float(1e4 * p["fee"][i] / gm_nav[i])})
    return out


NO_FLATTEN = "this path had no day-stop event in this window, so a per-event flatten cost is not applicable to it"


def flatten_cost_block(paths, scope_name, lo_t=None, hi_t=None):
    """the flatten-cost aggregates under the contract: the population is all paths (A1), and a path with no day-stop event is a NAMED
    subset (A2) instead of a member a comprehension quietly dropped."""
    ev = {p["seed"]: flatten_costs(p, lo_t, hi_t) for p in paths}
    applic = lambda p: (None if ev[p["seed"]] else NO_FLATTEN)                                                         # noqa: E731
    mean_of = lambda key: (lambda p: (float(np.mean([c[key] for c in ev[p["seed"]]])) if ev[p["seed"]] else None))     # noqa: E731
    return {"scope": scope_name,
            "events_per_path": blk("day_stop_events_per_path", list(paths), lambda p: float(len(ev[p["seed"]])), lambda p: None,
                                   population_name=f"{len(paths)} fill paths, {scope_name}", id_of=lambda p: p["seed"], unit="events"),
            "turnover_flatten_over_gross": blk("turnover_flatten_over_gross (per-path mean over its own events)", list(paths),
                                               mean_of("turnover_flatten_over_gross"), applic,
                                               population_name=f"{len(paths)} fill paths, {scope_name}", id_of=lambda p: p["seed"]),
            "window_fee_bps_of_gross": blk("window_fee_bps_of_gross (per-path mean over its own events)", list(paths),
                                           mean_of("window_fee_bps_of_gross"), applic,
                                           population_name=f"{len(paths)} fill paths, {scope_name}", id_of=lambda p: p["seed"]),
            "example_path_seed00": ev[paths[0]["seed"]][:10]}


NOT_TRADED = "this path traded no anchor of this window, so it has no window-end return to summarise"
NOT_BREACHED = "this path did not breach −25 % in this window, so it has no breach anchor"


def summarise(per, pop_name):
    """every aggregate of one (base, H, semantics) cell, under the contract"""
    P = list(per)
    unmeasured = lambda x: (None if x["has_measurement"] else NOT_TRADED)                                              # noqa: E731
    no_breach = lambda x: (NOT_TRADED if not x["has_measurement"] else (None if x["fired_cum25"] else NOT_BREACHED))   # noqa: E731
    return {
        "paths_that_hit_the_day_stop": AG.count_block("paths whose window contained a withheld anchor", P, lambda x: x["fired_day_stop"],
                                                      population_name=pop_name, id_of=lambda x: x["seed"]),
        "paths_that_hit_cum25": AG.count_block("paths that breached −25 % in this window", P, lambda x: x["fired_cum25"],
                                               population_name=pop_name, id_of=lambda x: x["seed"], applicability=unmeasured),
        "anchors_withheld": blk("anchors_withheld_by_day_stop", P, lambda x: float(x["anchors_withheld_by_day_stop"]), lambda x: None,
                                population_name=pop_name, id_of=lambda x: x["seed"], unit="anchors"),
        "anchors_traded": blk("anchors_traded_in_window", P, lambda x: float(x["anchors_traded_in_window"]), lambda x: None,
                              population_name=pop_name, id_of=lambda x: x["seed"], unit="anchors"),
        "end_return_P2": blk("end_return_P2", P, lambda x: x["end_return_P2"], unmeasured, population_name=pop_name,
                             id_of=lambda x: x["seed"], whole_population_convention=FLAT_BOOK_CONVENTION),
        "end_return_no_halt": blk("end_return_no_halt", P, lambda x: x["end_return_no_halt"], lambda x: None, population_name=pop_name,
                                  id_of=lambda x: x["seed"]),
        "cum25_anchor_epoch": blk("cum25_anchor_epoch", P, lambda x: x["cum25_anchor_epoch"], no_breach, population_name=pop_name,
                                  id_of=lambda x: x["seed"], unit="epoch seconds"),
    }


def cum25_median_iso(per):
    """the median BREACH ANCHOR, by the published element rule sorted(fired)[k // 2] — an actual anchor, not the interpolated
    percentile of the epoch block beside it (which can land between two anchors)"""
    v = sorted(x["cum25_anchor"] for x in per if x["cum25_anchor"])
    return v[len(v) // 2] if v else None


def cum25_median_block(per):
    """the same median, carrying its own effective sample size (AMENDMENT 4 §A4). It used to be persisted as a BARE SCALAR beside
    the summary — 118 of them per document — and the pre-fix sweep never saw it because its key is `cum25_anchor_median_utc` and
    the trigger was the whitelist (mean, median, p05, p95). Round-7 review G-05: the trigger is now inverted, and this is one of the
    two real instances it found in the committed receipts."""
    v = sorted(x["cum25_anchor"] for x in per if x["cum25_anchor"])
    return AG.one_value_block(v[len(v) // 2] if v else None, len(v), len(per),
                              "the median breach anchor by the published element rule sorted(fired)[k // 2]",
                              not_applicable={"n": len(per) - len(v), "reason": NOT_BREACHED})


def run(cfg_p, outp):
    NBLOCKS[0] = 0                                    # the census counts the aggregates of THIS document, not of the process
    CFG = json.load(open(cfg_p)); P = CFG["p_reading"]; P2 = CFG["p2_reading"]
    thr = float(P["threshold_cum_return"]); n_seeds = int(CFG["paths_R"])
    Hs = [P2["resume_hours_main"]] + list(P2["resume_hours_sensitivity"]) + (["sim"] if P2.get("include_sim_rule") else []) + (["never"] if P2.get("include_never") else [])
    out = {"device": "bt_p2_reading.py", "self_sha256": PR.sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "config": {"path": cfg_p, "sha256": PR.sha(cfg_p)}, "amendment_3": CFG["pins"]["prereg_amendment_3"],
           "amendment_4": {"doc": "docs/AMENDMENT_4_baseline_tables_aggregation_contract_2026-09-20.md",
                           "window_semantics_main": "W_ENTRY", "window_semantics_reported": list(SEMANTICS), "prose": SEM_PROSE,
                           "bt_agg_sha256": PR.sha(os.path.join(HERE, "bt_agg.py"))},
           "rule": {"p_reading": P, "p2_reading": P2, "H_list": Hs}, "assertions": [], "runs": {}}
    for r in CFG["runs"]:
        PP = load_paths2(r["dir"], n_seeds); A = PP[0]["A"]; row = {int(a): i for i, a in enumerate(A)}
        pop_name = f"{len(PP)} fill paths of {r['label']}"
        res = {"dir": r["dir"], "n_paths": len(PP), "window": [PR.iso(A[0]), PR.iso(A[-1])], "bases": {},
               "flatten_costs_per_path_WHOLE_PATH": flatten_cost_block(PP, "whole simulated path " + PR.iso(A[0]) + " → " + PR.iso(A[-1]))}
        for b in P["bases"]:
            t = PR.ts(b["anchor"])
            if t not in row: raise P2Error(f"base {b['anchor']} is not an anchor of {r['dir']}")
            i0 = row[t]; block = {}
            for H in Hs:
                cell = {}
                for sem in SEMANTICS:
                    MPr = mean_p2_series(PP, H, A[i0], sem)
                    MP = dict(PP[0], navm0=np.ones(len(A)), navm1=np.ones(len(A)), flatten=[])   # only A / shape are used; the mean
                    per = [dict(p2_of(p, i0, thr, H, sem), seed=p["seed"]) for p in PP]          # path has no flatten log of its own
                    n_traded = sum(1 for x in per if x["has_measurement"])
                    mp = {k: v for k, v in p2_of(MP, i0, thr, H, sem, series=MPr, traded_members=n_traded).items() if k != "per_event"}
                    mp["caliber"] = ("WHOLE POPULATION: the per-anchor mean over all %d paths, a withheld path contributing its "
                                     "flat-book 0 (AMENDMENT 4 §A3' convention). Read it beside the census below, never alone." % len(PP))
                    cell[sem] = {"semantics_prose": SEM_PROSE[sem],
                                 "per_path": [{k: v for k, v in x.items() if k != "per_event"} for x in per],
                                 "summary": summarise(per, pop_name),
                                 "mean_path": dict(mp, census_of_the_paths_it_averages={
                                     "population_n": len(PP), "paths_with_no_traded_anchor_in_window": sum(1 for x in per if not x["has_measurement"]),
                                     "seeds_with_no_traded_anchor": [x["seed"] for x in per if not x["has_measurement"]]}),
                                 "per_event_example_seed00": per[0]["per_event"][:8]}
                    cell[sem]["summary"]["cum25_anchor_median_utc"] = cum25_median_block(per)
                # AMENDMENT 4 §B-4: the two readings MUST agree bit for bit where they are the same question
                e_entry = [x["end_return_P2"] for x in cell["W_ENTRY"]["per_path"]]
                e_carry = [x["end_return_P2"] for x in cell["W_CARRY"]["per_path"]]
                same = (e_entry == e_carry)
                if i0 == 0 and not same:
                    raise P2Error(f"B4-a: at a base that IS the path start ({b['anchor']}, H={H}) W_ENTRY and W_CARRY must be identical")
                if H == "sim" and not same:
                    raise P2Error(f"B4-b: at H='sim' nothing is withheld, so W_ENTRY and W_CARRY must be identical (base {b['anchor']})")
                out["assertions"].append({"run": r["label"], "base": b["anchor"], "H": str(H), "base_index": i0,
                                          "clause": ("B4-a (base is the path start)" if i0 == 0 else ("B4-b (H=sim)" if H == "sim" else "—")),
                                          "W_ENTRY_equals_W_CARRY": bool(same)})
                block[str(H)] = cell
            res["bases"][b["label"] + " @ " + b["anchor"]] = block
            res.setdefault("flatten_costs_per_path_BY_BASE", {})[b["label"] + " @ " + b["anchor"]] = \
                flatten_cost_block(PP, "base window " + b["anchor"] + " → " + PR.iso(A[-1]), lo_t=int(A[i0]), hi_t=int(A[-1]))
        # the quarterly starts, main H and the strict bound, mean path and per path (AMENDMENT 3 §4), under BOTH semantics
        upto_i = int(np.searchsorted(A, PR.ts(P["breach_by"]), "right")) - 1
        CUT_KEY = "breach_by_" + P["breach_by"][:10]
        res["p_start"] = {}
        for st_iso in P["starts"]:
            t = PR.ts(st_iso)
            if t not in row or row[t] > upto_i:
                res["p_start"][st_iso] = {"in_window": False}; continue
            i0 = row[t]; e = {}
            for H in [P2["resume_hours_main"], "never", "sim"]:
                e[str(H)] = {}
                for sem in SEMANTICS:
                    MPr = mean_p2_series(PP, H, A[i0], sem)
                    MP = dict(PP[0], navm0=np.ones(len(A)), navm1=np.ones(len(A)), flatten=[])
                    # E-0921-B: the two uses are SEPARATE, exactly as the sibling bt_p_reading already separates them.
                    #   CUT_KEY        the configured cutoff decides WHETHER a breach happened by that date
                    #   to_window_end  the terminal VALUE, read at the run's own last anchor
                    # Before this fix only the first existed and the renderer printed it in a column headed "window end";
                    # on the extended A0 run that truncated 23 of 34 rows at 2026-08-31 while the run reaches 2026-09-18T20Z.
                    cell2 = {}
                    for key, up in ((CUT_KEY, upto_i), ("to_window_end", None)):
                        per = [dict(p2_of(p, i0, thr, H, sem, up), seed=p["seed"]) for p in PP]
                        sm = summarise(per, pop_name)                         # the WHOLE summary is emitted: a block built but not
                        sm["cum25_anchor_median_utc"] = cum25_median_block(per)  # persisted would fail the census
                        n_traded = sum(1 for x in per if x["has_measurement"])
                        cell2[key] = dict(sm, mean_path=dict({k: v for k, v in p2_of(MP, i0, thr, H, sem, up, series=MPr, traded_members=n_traded).items() if k != "per_event"},
                                                             caliber="WHOLE POPULATION: the per-anchor mean over all %d paths, a withheld path contributing its flat-book 0" % len(PP)),
                                          census_of_the_paths_it_averages={"population_n": len(PP),
                                                                           "paths_with_no_traded_anchor_in_window": sum(1 for x in per if not x["has_measurement"]),
                                                                           "seeds_with_no_traded_anchor": [x["seed"] for x in per if not x["has_measurement"]]})
                    cell2["reading_rule"] = ("AMENDMENT 2 §2 + E-0921-B: %r is judged up to the configured breach_by and answers "
                                             "WHETHER a breach happened by that date; 'to_window_end' answers WHAT THE WINDOW-END "
                                             "VALUE IS and is read at this run's own last anchor %s" % (CUT_KEY, PR.iso(A[-1])))
                    e[str(H)][sem] = cell2
            res["p_start"][st_iso] = dict(e, in_window=True)
        res["window_end_contract"] = dict(PR.assert_window_ends(res, A, PR.iso(A[upto_i]), f"bt_p2_reading run {r['label']!r}"),
                                          quarterly=PR.assert_every_quarterly_start_reports_both(res["p_start"], f"bt_p2_reading run {r['label']!r}"))
        out["runs"][r["label"]] = res
    out["runtime_s"] = round(time.time() - T0, 1)
    receipt = AG.write_json_checked(out, outp, min_blocks=2 * NBLOCKS[0])
    n_in_doc = AG.count_contract_blocks(out)
    if n_in_doc != NBLOCKS[0]:
        raise P2Error("aggregate census: %d contract blocks are in the document but %d were built — one was dropped on the way in, "
                      "or created outside the contract" % (n_in_doc, NBLOCKS[0]))
    print("BT_P2_READING written", outp, PR.sha(outp)[:16], "| H list:", Hs, "| semantics:", list(SEMANTICS),
          "| contract: %d aggregates, %d statistic blocks swept, 0 violations" % (NBLOCKS[0], receipt["aggregate_blocks_swept"]), flush=True)
    return out


if __name__ == "__main__":
    WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
    assert WL, "env whitelist (argv[1]) must be non-empty"
    extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
    run(sys.argv[2], sys.argv[3])
