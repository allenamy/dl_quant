#!/usr/bin/env python3
"""fcf_p_unsaturated.py — reading P, reported on the quantities that DO NOT SATURATE.

WHY THIS DEVICE EXISTS. Reading P's `end_return_phalt` is bounded below by the threshold: once a path breaches −25 % it stops trading
and its NAV is held flat, so its window-end return IS the cumulative return at the halt, i.e. ≈ −0.25 for EVERY breaching path no
matter how good or bad the arm is. Two arms that both breach therefore print the same number — and that sameness is a property of the
STATISTIC, not of the arms. Reporting "no difference" from a saturated statistic is the instrument's ceiling impersonating a result
(same family as "an endpoint identity cannot certify a path", E-... 2026-09-19).

So this device reports, per arm and per base, the quantities that still have resolution:
  · survival     — days from the base anchor to the halt. NO-MEASUREMENT for a path that never halts: such a path is carried in a
                   NAMED subset with its own count and is NEVER encoded as "the whole window" or as 0 (E-0920-C).
  · no-halt end  — the window-end return with §4-4 switched off. Defined for every path, saturates nowhere.
  · breach share — how many of the 32 paths breach at all.
usage: fcf_p_unsaturated.py <FCF_P_READING.json> <out.json>
"""
import calendar, hashlib, json, sys, time

import numpy as np

DAY = 86400.0


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(x): return calendar.timegm(time.strptime(x, "%Y-%m-%dT%H:%M:%SZ"))


def stat(v, n_pop, na_reason, n_na):
    v = np.asarray(v, float)
    if len(v) == 0:
        return {"n_population": n_pop, "n_measured": 0, "median": None, "mean": None, "p05": None, "p95": None,
                "no_measurement": {"n": n_na, "reason": na_reason}}
    return {"n_population": n_pop, "n_measured": int(len(v)), "median": float(np.median(v)), "mean": float(v.mean()),
            "p05": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95)), "min": float(v.min()), "max": float(v.max()),
            "no_measurement": {"n": n_na, "reason": na_reason}}


P = json.load(open(sys.argv[1]))
out = {"device": "fcf_p_unsaturated.py", "self_sha256": sha(__file__), "source": {"path": sys.argv[1], "sha256": sha(sys.argv[1])},
       "why": "reading P's end_return_phalt saturates at the threshold; two arms that both breach print the same number and that is the "
              "statistic's property, not the arms'. These are the quantities that keep their resolution.",
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "bases": {}}
for B in sorted(next(iter(P["runs"].values()))["bases"]):
    b_ts = ts(B.split("@")[-1].strip())
    out["bases"][B] = {"base_anchor_utc": B.split("@")[-1].strip(), "arms": {}}
    for nm, r in P["runs"].items():
        arm = nm.split("arm ")[-1].rstrip(")")
        s = r["bases"][B]["summary"]
        mem = s["end_return_phalt"]["population"]["members"]
        fired = [m for m in mem if m.get("fired")]
        surv = [(ts(m["halt_anchor"]) - b_ts) / DAY for m in fired]
        out["bases"][B]["arms"][arm] = {
            "paths_breaching": len(fired), "n_paths": len(mem),
            "survival_days_to_halt": stat(surv, len(mem), "this path never breached in this window, so it has no time-to-halt", len(mem) - len(fired)),
            "end_return_no_halt": {k: s["end_return_nohalt"]["measured"][k] for k in ("mean", "median", "p05", "p95", "n_eff", "population_n")},
            "end_return_P_halt_SATURATED": {k: s["end_return_phalt"]["measured"][k] for k in ("mean", "median", "n_eff")},
            "saturation_note": ("end_return_P_halt is bounded at the threshold for every breaching path; compare arms on "
                                "survival_days_to_halt and end_return_no_halt instead")}
json.dump(out, open(sys.argv[2] + ".tmp", "w"), indent=1); import os; os.replace(sys.argv[2] + ".tmp", sys.argv[2])
for B, d in out["bases"].items():
    print("\n### base", d["base_anchor_utc"])
    print("  arm   breach   survival days to halt (median / mean, n_measured)      no-halt end return (mean)   P-halt end (SATURATED)")
    for a, v in d["arms"].items():
        sv = v["survival_days_to_halt"]
        print("  %-4s  %2d/%2d   %s / %s  (n=%d, never-halt n=%d)   %+.4f   %+.4f" % (
            a, v["paths_breaching"], v["n_paths"],
            ("%.1f" % sv["median"]) if sv["median"] is not None else "—",
            ("%.1f" % sv["mean"]) if sv["mean"] is not None else "—",
            sv["n_measured"], sv["no_measurement"]["n"],
            v["end_return_no_halt"]["mean"], v["end_return_P_halt_SATURATED"]["mean"]))
print("\nFCF_P_UNSATURATED written", sys.argv[2], "sha256", sha(sys.argv[2]))
