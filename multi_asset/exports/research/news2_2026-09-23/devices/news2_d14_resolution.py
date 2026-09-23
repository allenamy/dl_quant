"""D14 resolution: could the stable tie-break have changed the member set at all?

The reach gate's `floorD14` arm moved nothing on its 5 anchors and was therefore reported
NO-MEASUREMENT, not PASS -- correctly, because an arm that changes nothing is indistinguishable from an
arm that is not wired. A bigger anchor sample would not settle it either: D14 is
`argsort(-qvm[m], kind="stable")` (shipping tree L580), so it can only change the selection when the
sort key TIES across the NTOP cut. Sampling more anchors in the hope of catching a tie is not a
measurement of whether ties occur.

So this measures the thing the arm cannot: per anchor, whether a tie across the cut is even possible.

  n_cand <= NTOP                -> the producer never executes the cut (`if len(m) > P["NTOP"]`),
                                   so D14 is structurally inert at this anchor, for a reason that has
                                   nothing to do with ties.
  cut_value                     = min qvm among the selected members (the 400th key).
  n_members_at_cut              = selected members sharing that exact key.
  n_superset_at_cut             = symbols with legal AND crypto sharing that exact key.
  tie_possible                  = n_superset_at_cut > n_members_at_cut

Soundness of the superset step: the candidate set C is a SUBSET of (legal AND crypto) -- candidacy also
requires the c7 / v7 thresholds. `members` = the top-NTOP of C by -qvm, so a different tie-break can
change the outcome only if some c in C \\ members has qvm exactly equal to cut_value. Counting over the
superset can therefore OVER-report a tie but never miss one, which is the safe direction for a gate:
this device is allowed to say "a tie might be possible" when it is not, and is not allowed to say
"no tie is possible" when one is.

Nothing here reconstructs the producer's screen. It reads only what pass1_anchor already returns
(`m`, `qvm` over members, and `screen` with candidate-level qvm / legal), because a reimplementation of
the screen would be a twin, and the twin would be the thing under test.

Red control (`--selftest`): a synthetic anchor where a non-member symbol is given exactly the cut key.
The detector must report tie_possible=True. Without that cell a run of all-False is unfalsifiable.

usage: python news2_d14_resolution.py <nc_devices> <tree> <cfg> <work> <members_hist|-> <out.json> <anchor>...
       python news2_d14_resolution.py --selftest <out.json>
"""
import hashlib, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

REQUIRED_ENV = ("NC_WS",)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def resolve(m, qvm_members, qvm_all, legal, crypto, ntop, n_cand):
    """The measurement, isolated from the replay so --selftest can drive it on constructed input."""
    m = np.asarray(m).ravel()
    out = {"n_members": int(m.size), "n_cand": (None if n_cand is None else int(n_cand)), "NTOP": int(ntop)}
    if n_cand is not None and int(n_cand) <= int(ntop):
        out.update({"cut_executed": False, "tie_possible": False,
                    "why": "n_cand <= NTOP: the producer does not execute the cut at this anchor"})
        return out
    out["cut_executed"] = True
    qm = np.asarray(qvm_members, np.float64).ravel()
    fin = np.isfinite(qm)
    if not fin.any():
        # No finite key among members: report it, do not fold it into a False.
        out.update({"tie_possible": None, "why": "no finite qvm among members; not measurable here"})
        return out
    cut = float(qm[fin].min())
    sup = np.asarray(legal, bool).ravel() & np.asarray(crypto, bool).ravel()
    qa = np.asarray(qvm_all, np.float64).ravel()
    n_sup = int(np.sum(sup & (qa == cut)))
    n_mem = int(np.sum(qm == cut))
    out.update({"cut_value": cut, "n_members_at_cut": n_mem, "n_superset_at_cut": n_sup,
                "tie_possible": bool(n_sup > n_mem),
                "why": ("a legal AND crypto symbol outside the member set holds the cut key exactly"
                        if n_sup > n_mem else
                        "the cut key is held only by selected members, over a SUPERSET of the candidates")})
    return out


def selftest(out_path):
    cells, t0 = [], time.time()

    def cell(tag, ok, want, got):
        cells.append({"cell": tag, "verdict": "PASS" if ok else "FAIL", "expected": want, "observed": got})
        print(f"  {tag:26s} {'PASS' if ok else 'FAIL':5s} expected={want}  observed={got}", flush=True)

    N, NTOP = 10, 4
    qvm = np.array([90., 80., 70., 60., 60., 50., 40., 30., 20., 10.])   # 60.0 tied across the cut
    legal = np.ones(N, bool); crypto = np.ones(N, bool)
    m = np.array([0, 1, 2, 3])                                            # cut key = 60.0, index 4 also 60.0
    r = resolve(m, qvm[m], qvm, legal, crypto, NTOP, n_cand=N)
    cell("RED.tie_across_cut", r["tie_possible"] is True and r["n_superset_at_cut"] == 2 and r["n_members_at_cut"] == 1,
         "tie_possible=True, superset 2 vs members 1", f"{r['tie_possible']} {r.get('n_superset_at_cut')}/{r.get('n_members_at_cut')}")

    qvm2 = np.array([90., 80., 70., 60., 55., 50., 40., 30., 20., 10.])   # nothing ties the cut
    r2 = resolve(m, qvm2[m], qvm2, legal, crypto, NTOP, n_cand=N)
    cell("GREEN.no_tie", r2["tie_possible"] is False and r2["n_superset_at_cut"] == 1,
         "tie_possible=False, superset 1", f"{r2['tie_possible']} {r2.get('n_superset_at_cut')}")

    # the tied symbol is ILLEGAL -> it is not a candidate, so no tie is possible
    legal3 = legal.copy(); legal3[4] = False
    r3 = resolve(m, qvm[m], qvm, legal3, crypto, NTOP, n_cand=N)
    cell("GREEN.tied_but_illegal", r3["tie_possible"] is False,
         "tie_possible=False (the tied symbol is outside legal AND crypto)", f"{r3['tie_possible']}")

    # cut never executed
    r4 = resolve(m, qvm[m], qvm, legal, crypto, NTOP, n_cand=NTOP)
    cell("GREEN.cut_not_executed", r4["cut_executed"] is False and r4["tie_possible"] is False,
         "cut_executed=False", f"{r4['cut_executed']}")

    bad = [c for c in cells if c["verdict"] != "PASS"]
    rec = {"device": "news2_d14_resolution.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mode": "selftest",
           "cells": cells, "n_cells": len(cells), "n_not_pass": len(bad),
           "VERDICT": "PASS" if not bad else "FAIL", "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_D14_RESOLUTION VERDICT={rec['VERDICT']} mode=selftest cells={len(cells)} "
          f"not_pass={len(bad)} receipt_sha256={sha(out_path)}", flush=True)
    sys.exit(0 if not bad else 1)


def main():
    if sys.argv[1] == "--selftest":
        selftest(os.path.abspath(sys.argv[2]))
        return
    nc_devices, tree, cfg, work, mh, out_path = sys.argv[1:7]
    anchors = [int(x) for x in sys.argv[7:]]
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        print(f"NEWS2_D14_RESOLUTION VERDICT=REFUSED missing_env={missing}", flush=True)
        sys.exit(4)
    t0 = time.time()
    from news2_nc_adapter import Replay
    R = Replay(nc_devices, tree, cfg, work, (None if mh == "-" else mh))
    NTOP = int(R.P["NTOP"])
    rows = []
    for A in anchors:
        r = R.at(A)
        if r.get("m") is None:
            rows.append({"anchor": A, "unavailable": r.get("unavailable", "pass1 produced no members")})
            print(f"  {A} UNAVAILABLE {rows[-1]['unavailable']}", flush=True)
            continue
        scr = r.get("screen") or {}
        row = {"anchor": A}
        row.update(resolve(r["m"], r.get("qvm"), scr.get("qvm"), scr.get("legal"),
                           R.I.crypto, NTOP, r.get("n_cand")))
        rows.append(row)
        print(f"  {A} n_cand={row.get('n_cand')} members={row.get('n_members')} "
              f"cut_executed={row.get('cut_executed')} tie_possible={row.get('tie_possible')} "
              f"superset_at_cut={row.get('n_superset_at_cut')} members_at_cut={row.get('n_members_at_cut')}", flush=True)

    measured = [r for r in rows if "tie_possible" in r]
    unknown = [r for r in measured if r["tie_possible"] is None]
    ties = [r for r in measured if r["tie_possible"] is True]
    # ★ Zero anchors measured is not agreement. Nor is "all None": a column of not-measurable is
    # reported as such rather than averaged into a benign False.
    if not measured or unknown:
        verdict = (f"NO-MEASUREMENT: measured={len(measured)} not_measurable={len(unknown)} "
                   f"of {len(anchors)} anchors")
    elif ties:
        verdict = f"TIE_POSSIBLE at {len(ties)}/{len(measured)} anchors: D14 can move the member set here"
    else:
        verdict = (f"NO_TIE_POSSIBLE at all {len(measured)} anchors: the stable tie-break cannot change "
                   f"the member set at these anchors, which explains the reach arm's zero")
    rec = {"device": "news2_d14_resolution.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "argv": list(sys.argv), "rerun_command": " ".join([sys.executable, os.path.abspath(__file__)] + sys.argv[1:]),
           "env": {k: os.environ.get(k) for k in ("NC_W", "NC_WS", "NC_CFG", "NC_TREE")},
           "tree": tree, "tree_shadow_loop_sha256": sha(os.path.join(tree, "shadow_loop_v3.py")),
           "NTOP": NTOP, "anchors": anchors, "rows": rows,
           "n_measured": len(measured), "n_not_measurable": len(unknown), "n_tie_possible": len(ties),
           "soundness": ("counted over legal AND crypto, a SUPERSET of the candidate set: this can "
                         "over-report a possible tie, never miss one"),
           "VERDICT": verdict, "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_D14_RESOLUTION VERDICT={verdict} anchors={len(anchors)} receipt_sha256={sha(out_path)}", flush=True)
    sys.exit(0 if verdict.startswith("NO_TIE_POSSIBLE") or verdict.startswith("TIE_POSSIBLE") else 1)


if __name__ == "__main__":
    main()
