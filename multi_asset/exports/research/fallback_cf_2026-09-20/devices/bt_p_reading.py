#!/usr/bin/env python3
"""bt_p_reading.py — reading P ("按实盘风控政策"), AMENDMENT 2 (docs/AMENDMENT_2_baseline_tables_certified_2026-09-20.md, 9bbd850ac, sha
52ae1969). Post-processing of the per-path NAV series that the runs already wrote; NO re-simulation, nothing about the runs changes.

The live watchdog §4-4 (`~/dl_quant_live/live/watchdog.py` L131 DRAWDOWN_LIMIT_PCT = -25.0) measures the CUMULATIVE return from STARTING
equity (not a peak-relative drawdown), and on a breach cancels, flattens, sets the account reduce-only and waits for a human. The main
reading assumes it never fires. Reading P asks the other question.

  P-halt (AMENDMENT 2 §1), per fill path and per base start:
      cum_k = navm1_k / navm0_base − 1            (main-reading NAV, the same series the tables use; window ends = "anchor ends")
      halt  = the FIRST k with cum_k < THRESHOLD  (strictly below; THRESHOLD = −0.2500 from the config, the live constant, not rescaled)
      after the halt the path does not trade and its NAV is held flat ⇒ the P-halt window-end return IS the cumulative return at the halt;
      no manual resume is modelled (a human decision is outside the model, and no assumed resume rule may replace it).
  P-start (AMENDMENT 2 §2): the frozen list of quarterly start dates in the config; for each, whether it breaches by the config's
      `breach_by` date, the first breach time, and the window-end return under BOTH calibers (no-halt and P-halt), as the path mean with
      the 5 / 95 percentiles.
Bases reported for P-halt: every entry of config `p_reading.bases` (the run window's start per AMENDMENT 2 §1, and the FULL_RECIPE window
start, which is the base the lead's independent check used and the base of the published headline).
MEAN PATH: besides the 32 fill paths, the same rule is applied to the tables' MEAN PATH (the per-window mean of the path returns,
compounded — the series every published headline number is computed on). AMENDMENT 2 prescribes the per-path reading; the mean path is
reported beside it because the lead's independent check was made on it, and a minority-of-paths breach is invisible on the mean path.
GRANULARITY: AMENDMENT 2 prescribes the ANCHOR ends, and that is the main reading here. The live watchdog evaluates once a day
(`watchdog.py` L1862: `cum = prod(1 + r_d) - 1 ; trigger: cum < DRAWDOWN_LIMIT_PCT`, daily returns), so a second, clearly labelled
sensitivity is reported on UTC DAY ends only (the 20:00Z anchors, whose windows close at 24:00Z). The anchor-end reading can halt earlier
within a day than the live daily check; neither is "the live P&L", because the live account is not this book.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B bt_p_reading.py PATH,HOME,LC_CTYPE <p_config.json> <out.json>
"""
import os, sys, json, time, calendar, hashlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_agg as AG                                   # AMENDMENT 4 aggregation contract

T0 = time.time()
H4 = 14400

# AMENDMENT 4 §A2: the named reasons a member of the path population has no measurement for a given quantity
NO_ANCHOR = "this window contains no anchor at or after the base, so the path has no window-end return here"
NO_BREACH = "this path did not breach the threshold in this window, so it has no cumulative return at a halt"
NBLOCKS = [0]


def _blk(*a, **kw):
    """a contract block whose MEASURED figures are also mirrored at the top level, so the legacy key layout
    (block["mean"], block["median"], block["n"]) keeps working while n_eff / population_n now sit beside them (A4)"""
    NBLOCKS[0] += 1
    b = AG.block(*a, **kw)
    return dict(b, n=b["measured"]["n_eff"], **b["measured"])


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(iso): return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def pct(v, q): return None if not len(v) else float(np.percentile(np.asarray(v, float), q))


class PReadingError(Exception):
    pass


def load_paths(run_dir, n_seeds):
    """per-path (A, navm0, navm1) from the PATH npz files, sha-checked against their own json"""
    tag = os.path.basename(run_dir.rstrip("/")); out = []
    for s in range(n_seeds):
        st = os.path.join(run_dir, f"PATH_{tag}_seed_{s:02d}")
        J = json.load(open(st + ".json"))
        if J.get("npz_sha256") != sha(st + ".npz"): raise PReadingError(f"npz sha != its json: {st}")
        Z = np.load(st + ".npz")
        out.append({"seed": s, "A": Z["A"].astype(np.int64), "navm0": Z["navm0"].astype(np.float64), "navm1": Z["navm1"].astype(np.float64)})
    if not out: raise PReadingError("no paths")
    for p in out[1:]:
        if not np.array_equal(p["A"], out[0]["A"]): raise PReadingError("paths do not share one anchor axis")
    return out


def mean_path(paths):
    """the tables' mean path: per-window MEAN of the path returns, compounded (bt_tables.series_mean caliber)"""
    R = np.mean([p["navm1"] / p["navm0"] - 1.0 for p in paths], axis=0)
    nav = 1.0 * np.cumprod(1.0 + R)
    return {"seed": "mean_path", "A": paths[0]["A"].copy(), "navm1": nav, "navm0": np.concatenate([[1.0], nav[:-1]])}


DAY_END_ANCHOR_S = 72000          # the 20:00Z anchor: its 4h window closes at 24:00Z, so its end is a UTC day end


def halt_of(p, base_i, threshold, upto_i=None, day_end_only=False):
    """the first eligible window end whose cumulative return from navm0[base_i] is strictly below threshold"""
    A, n0, n1 = p["A"], p["navm0"], p["navm1"]
    hi = len(A) if upto_i is None else upto_i + 1
    cum = n1[base_i:hi] / n0[base_i] - 1.0
    below = cum < threshold
    if day_end_only: below = below & (A[base_i:hi] % 86400 == DAY_END_ANCHOR_S)
    k = np.nonzero(below)[0]
    end_nohalt = float(cum[-1]) if len(cum) else None
    if not len(k):
        return {"fired": False, "halt_index": None, "halt_anchor": None, "cum_at_halt": None, "end_return_nohalt": end_nohalt,
                "end_return_phalt": end_nohalt, "anchors_after_halt": 0, "share_anchors_after_halt": 0.0}
    j = int(k[0]); g = base_i + j
    return {"fired": True, "halt_index": g, "halt_anchor": iso(A[g]), "cum_at_halt": float(cum[j]), "end_return_nohalt": end_nohalt,
            "end_return_phalt": float(cum[j]), "anchors_after_halt": int(hi - 1 - g), "share_anchors_after_halt": float((hi - 1 - g) / max(hi - base_i, 1))}


def spread(vals, keys=("end_return_nohalt", "end_return_phalt", "cum_at_halt"), pop="fill paths"):
    """AMENDMENT 4 §A: a closed population, a NAMED no-measurement subset per quantity, and n_eff beside every statistic.
    The numbers themselves are unchanged — reading P never substituted a value for a missing one (`halt_of` always returns a
    computed cumulative return, and `cum_at_halt` is simply absent for a path that did not breach)."""
    V = list(vals); pn = f"{len(V)} {pop}"
    why = {"end_return_nohalt": (lambda x: None if x.get("end_return_nohalt") is not None else NO_ANCHOR),
           "end_return_phalt": (lambda x: None if x.get("end_return_phalt") is not None else NO_ANCHOR),
           "cum_at_halt": (lambda x: None if x["fired"] else NO_BREACH)}
    out = {k: _blk(k, V, (lambda x, kk=k: x.get(kk)), why[k], population_name=pn) for k in keys}
    t = [x["halt_index"] for x in vals if x["fired"]]
    out["fired_paths"] = sum(1 for x in vals if x["fired"]); out["n_paths"] = len(vals)
    out["halt_index"] = {"min": (min(t) if t else None), "median_element": (sorted(t)[len(t) // 2] if t else None),
                         "max": (max(t) if t else None), "n_eff": len(t), "population_n": len(V)}
    return out


def run(cfg_p, outp):
    NBLOCKS[0] = 0
    CFG = json.load(open(cfg_p)); PR = CFG["p_reading"]
    thr = float(PR["threshold_cum_return"]); n_seeds = int(CFG["paths_R"])
    out = {"device": "bt_p_reading.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "config": {"path": cfg_p, "sha256": sha(cfg_p)}, "amendment_2": CFG["pins"]["prereg_amendment_2"], "rule": PR, "runs": {}}
    for r in CFG["runs"]:
        P = load_paths(r["dir"], n_seeds); A = P[0]["A"]; row = {int(a): i for i, a in enumerate(A)}
        MP = mean_path(P)
        res = {"dir": r["dir"], "n_paths": len(P), "window": [iso(A[0]), iso(A[-1])], "bases": {}, "p_start": {}, "mean_path": {"bases": {}, "p_start": {}}}
        for b in PR["bases"]:
            t = ts(b["anchor"])
            if t not in row: raise PReadingError(f"base {b['anchor']} is not an anchor of {r['dir']}")
            res["mean_path"]["bases"][b["label"] + " @ " + b["anchor"]] = dict(halt_of(MP, row[t], thr), utc_day_ends_only=halt_of(MP, row[t], thr, day_end_only=True))
            per = [dict(halt_of(p, row[t], thr), seed=p["seed"]) for p in P]
            per_d = [dict(halt_of(p, row[t], thr, day_end_only=True), seed=p["seed"]) for p in P]
            res["bases"][b["label"] + " @ " + b["anchor"]] = {"per_path": per, "summary": spread(per),
                                                             "sensitivity_utc_day_ends_only (the live watchdog's daily cadence)": {"per_path": per_d, "summary": spread(per_d)}}
        upto = ts(PR["breach_by"]); upto_i = int(np.searchsorted(A, upto, "right")) - 1
        if upto_i < 0: raise PReadingError(f"breach_by {PR['breach_by']} is before the first anchor")
        for st_iso in PR["starts"]:
            t = ts(st_iso)
            if t not in row:
                res["p_start"][st_iso] = {"status": "start is not an anchor of this run window", "in_window": False}; continue
            i0 = row[t]
            if i0 > upto_i:
                res["p_start"][st_iso] = {"status": "start is after breach_by", "in_window": False}; continue
            per_b = [halt_of(p, i0, thr, upto_i) for p in P]                     # breach judged up to breach_by (AMENDMENT 2 §2)
            per_e = [halt_of(p, i0, thr, None) for p in P]                       # returns to the run window end
            res["mean_path"]["p_start"][st_iso] = dict(halt_of(MP, i0, thr, upto_i), to_window_end=halt_of(MP, i0, thr))
            per_d = [halt_of(p, i0, thr, upto_i, day_end_only=True) for p in P]
            res["p_start"][st_iso] = {"in_window": True, "start_index": i0, "anchors_to_breach_by": int(upto_i - i0 + 1),
                                      "sensitivity_utc_day_ends_only": {"fired_paths": sum(1 for x in per_d if x["fired"]),
                                                                        "first_breach_median": (sorted([x["halt_anchor"] for x in per_d if x["fired"]])[len([x for x in per_d if x["fired"]]) // 2] if any(x["fired"] for x in per_d) else None)},
                                      "breach_by_" + PR["breach_by"][:10]: spread(per_b), "to_window_end": spread(per_e),
                                      "first_breach_utc": {"min": min([x["halt_anchor"] for x in per_b if x["fired"]], default=None),
                                                           "median": (sorted([x["halt_anchor"] for x in per_b if x["fired"]])[len([x for x in per_b if x["fired"]]) // 2] if any(x["fired"] for x in per_b) else None),
                                                           "max": max([x["halt_anchor"] for x in per_b if x["fired"]], default=None),
                                                           "n_eff": sum(1 for x in per_b if x["fired"]), "population_n": len(per_b),
                                                           "not_applicable": {"n": sum(1 for x in per_b if not x["fired"]), "reason": NO_BREACH}}}
        out["runs"][r["label"]] = res
    out["runtime_s"] = round(time.time() - T0, 1)
    receipt = AG.write_json_checked(out, outp, min_blocks=2 * NBLOCKS[0])
    n_in_doc = AG.count_contract_blocks(out)
    if n_in_doc != NBLOCKS[0]:
        raise PReadingError("aggregate census: %d contract blocks are in the document but %d were built — one was dropped on the "
                            "way in, or created outside the contract" % (n_in_doc, NBLOCKS[0]))
    br = {lbl: sum(1 for k, v in R["p_start"].items() if v.get("in_window") and v["breach_by_" + json.load(open(cfg_p))["p_reading"]["breach_by"][:10]]["fired_paths"] > 0) for lbl, R in out["runs"].items()}
    print("BT_P_READING written", outp, sha(outp)[:16], "| quarterly starts that breach on at least one path:", json.dumps(br), flush=True)
    return out


if __name__ == "__main__":                       # the env whitelist is asserted only when this file is EXECUTED (its test imports it as a library)
    WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
    assert WL, "env whitelist (argv[1]) must be non-empty"
    extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
    run(sys.argv[2], sys.argv[3])
