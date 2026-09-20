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
Reported per base start, per H: how many paths fired which rule, when, the window-end return under P2 / under §4-4 only / with no halt at all,
the anchors withheld per event and in total, and the same for the tables' MEAN PATH (kept separate from the per-path numbers, R6-12).
usage: /workspace/venv/bin/python -B bt_p2_reading.py PATH,HOME,LC_CTYPE <p2_config.json> <out.json>
"""
import os, sys, json, time, calendar, hashlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_p_reading as PR

T0 = time.time()
H4 = 14400


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


def withheld_mask(p, H):
    """which anchors the live-like resume rule withholds; H in hours, or 'sim' (no extra withholding) or 'never'"""
    A = p["A"]; m = np.zeros(len(A), bool); per_event = []
    if H == "sim" or not p["flatten"]:
        return m, per_event
    if H == "never":
        t0 = min(t for t, _ in p["flatten"]); m |= (A >= t0)
        per_event.append({"flatten_utc": PR.iso(t0), "anchors_withheld": int(m.sum()), "rule": "never resumes"})
        return m, per_event
    for t, _why in sorted(p["flatten"]):
        w = (A >= t) & (A < t + int(float(H) * 3600))
        per_event.append({"flatten_utc": PR.iso(t), "anchors_withheld": int(w.sum()),
                          "resume_anchor": (PR.iso(A[A >= t + int(float(H) * 3600)][0]) if np.any(A >= t + int(float(H) * 3600)) else None)})
        m |= w
    return m, per_event


def p2_returns(p, H):
    """the per-window returns after the live-like resume rule: withheld anchors earn exactly 0"""
    r = p["navm1"] / p["navm0"] - 1.0
    m, per_event = withheld_mask(p, H)
    return np.where(m, 0.0, r), m, per_event


def p2_of(p, base_i, thr, H, upto_i=None, series=None):
    """the P2 path: withheld anchors earn 0, then §4-4 halts for good at the first window end strictly below the threshold"""
    A = p["A"]; hi = len(A) if upto_i is None else upto_i + 1
    r = p["navm1"] / p["navm0"] - 1.0
    if series is None:
        r2_full, m, per_event = p2_returns(p, H)
    else:
        r2_full, m, per_event = series                       # a pre-built series (the mean path: the per-window mean of the path r2)
    r2 = r2_full[base_i:hi]
    nav = np.cumprod(1.0 + r2)                                    # NAV relative to the base's starting equity
    cum = nav - 1.0
    k = np.nonzero(cum < thr)[0]
    fired44 = bool(len(k)); j = int(k[0]) if fired44 else None
    end_p2 = float(cum[j]) if fired44 else (float(cum[-1]) if len(cum) else None)
    fired42 = bool(np.any(m[base_i:hi])) if m is not None else None
    return {"resume_rule": ("sim (next 00Z) = reading P" if H == "sim" else ("never resumes" if H == "never" else f"{H} h")),
            "anchors_withheld_by_day_stop": int(m[base_i:hi].sum()), "day_stop_events_in_window": int(sum(1 for t, _ in p["flatten"] if A[base_i] <= t <= A[hi - 1])),
            "per_event": per_event, "fired_day_stop": fired42,
            "fired_cum25": fired44, "cum25_anchor": (PR.iso(A[base_i + j]) if fired44 else None), "cum_at_cum25": (float(cum[j]) if fired44 else None),
            "end_return_P2": end_p2, "end_return_no_halt": (float(np.prod(1.0 + r[base_i:hi]) - 1.0) if hi > base_i else None)}


def mean_p2_series(paths, H):
    """the tables' mean-path caliber applied to P2: the per-window MEAN over paths of the P2-adjusted returns (not of the raw returns)"""
    R = np.stack([p2_returns(p, H)[0] for p in paths]); M = np.stack([p2_returns(p, H)[1] for p in paths])
    return R.mean(0), M.mean(0) >= 0.5, [{"note": "mean path: an anchor counts as withheld when at least half the paths withhold it"}]


def flatten_costs(p):
    """what each flatten cost inside its own window: the flatten turnover over gross and that window's fee in bps of gross"""
    idx = np.nonzero(p["turn_flat"] > 0)[0]; gm_nav = 2.0 * p["nav0"]
    return [{"anchor": PR.iso(p["A"][i]), "turnover_flatten_over_gross": float(p["turn_flat"][i] / gm_nav[i]),
             "window_fee_bps_of_gross": float(1e4 * p["fee"][i] / gm_nav[i])} for i in idx.tolist()]


def agg(vals, key):
    v = [x[key] for x in vals if x.get(key) is not None]
    return {"mean": (float(np.mean(v)) if v else None), "p05": PR.pct(v, 5), "median": PR.pct(v, 50), "p95": PR.pct(v, 95), "n": len(v)}


def run(cfg_p, outp):
    CFG = json.load(open(cfg_p)); P = CFG["p_reading"]; P2 = CFG["p2_reading"]
    thr = float(P["threshold_cum_return"]); n_seeds = int(CFG["paths_R"])
    Hs = [P2["resume_hours_main"]] + list(P2["resume_hours_sensitivity"]) + (["sim"] if P2.get("include_sim_rule") else []) + (["never"] if P2.get("include_never") else [])
    out = {"device": "bt_p2_reading.py", "self_sha256": PR.sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "config": {"path": cfg_p, "sha256": PR.sha(cfg_p)}, "amendment_3": CFG["pins"]["prereg_amendment_3"], "rule": {"p_reading": P, "p2_reading": P2, "H_list": Hs},
           "runs": {}}
    for r in CFG["runs"]:
        PP = load_paths2(r["dir"], n_seeds); A = PP[0]["A"]; row = {int(a): i for i, a in enumerate(A)}
        MPr = {}                                             # the mean path's P2 return series, per H
        for H in Hs: MPr[str(H)] = mean_p2_series(PP, H)
        MP = dict(PP[0], navm0=np.ones(len(A)), navm1=np.ones(len(A)))        # only A / shape are used for the mean path; its returns come from MPr
        res = {"dir": r["dir"], "n_paths": len(PP), "window": [PR.iso(A[0]), PR.iso(A[-1])], "bases": {},
               "flatten_costs_per_path": {"events_per_path": agg([{"n": len(flatten_costs(p))} for p in PP], "n"),
                                          "turnover_flatten_over_gross": agg([{"v": float(np.mean([c["turnover_flatten_over_gross"] for c in flatten_costs(p)]))} for p in PP if flatten_costs(p)], "v"),
                                          "window_fee_bps_of_gross": agg([{"v": float(np.mean([c["window_fee_bps_of_gross"] for c in flatten_costs(p)]))} for p in PP if flatten_costs(p)], "v"),
                                          "example_path_seed00": flatten_costs(PP[0])[:10]}}
        for b in P["bases"]:
            t = PR.ts(b["anchor"])
            if t not in row: raise P2Error(f"base {b['anchor']} is not an anchor of {r['dir']}")
            i0 = row[t]; block = {}
            for H in Hs:
                per = [dict(p2_of(p, i0, thr, H), seed=p["seed"]) for p in PP]
                block[str(H)] = {"per_path": [{k: v for k, v in x.items() if k != "per_event"} for x in per],
                                 "summary": {"paths_that_hit_the_day_stop": sum(1 for x in per if x["fired_day_stop"]),
                                             "paths_that_hit_cum25": sum(1 for x in per if x["fired_cum25"]),
                                             "anchors_withheld": agg(per, "anchors_withheld_by_day_stop"),
                                             "end_return_P2": agg(per, "end_return_P2"), "end_return_no_halt": agg(per, "end_return_no_halt"),
                                             "cum25_anchor_median": (sorted([x["cum25_anchor"] for x in per if x["fired_cum25"]])[sum(1 for x in per if x["fired_cum25"]) // 2]
                                                                     if any(x["fired_cum25"] for x in per) else None)},
                                 "mean_path": {k: v for k, v in p2_of(MP, i0, thr, H, series=MPr[str(H)]).items() if k != "per_event"},
                                 "per_event_example_seed00": per[0]["per_event"][:8]}
            res["bases"][b["label"] + " @ " + b["anchor"]] = block
        # the quarterly starts, main H and the strict bound, mean path and per path (AMENDMENT 3 §4)
        upto_i = int(np.searchsorted(A, PR.ts(P["breach_by"]), "right")) - 1
        res["p_start"] = {}
        for st_iso in P["starts"]:
            t = PR.ts(st_iso)
            if t not in row or row[t] > upto_i:
                res["p_start"][st_iso] = {"in_window": False}; continue
            i0 = row[t]; e = {}
            for H in [P2["resume_hours_main"], "never", "sim"]:
                per = [p2_of(p, i0, thr, H, upto_i) for p in PP]
                e[str(H)] = {"paths_day_stopped": sum(1 for x in per if x["fired_day_stop"]), "paths_cum25": sum(1 for x in per if x["fired_cum25"]),
                             "end_return_P2": agg(per, "end_return_P2"), "mean_path": {k: v for k, v in p2_of(MP, i0, thr, H, upto_i, series=MPr[str(H)]).items() if k != "per_event"}}
            res["p_start"][st_iso] = dict(e, in_window=True)
        out["runs"][r["label"]] = res
    out["runtime_s"] = round(time.time() - T0, 1)
    json.dump(out, open(outp + ".tmp", "w"), indent=1, default=float); os.replace(outp + ".tmp", outp)
    print("BT_P2_READING written", outp, PR.sha(outp)[:16], "| H list:", Hs, flush=True)
    return out


if __name__ == "__main__":
    WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
    assert WL, "env whitelist (argv[1]) must be non-empty"
    extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
    run(sys.argv[2], sys.argv[3])
