"""Step 3, the part that is feasible today: the two FUNDING RANK BASES, per anchor, as name sets.

lead 2026-09-24 point 1: the semantic difference ("the researcher's base omits crypto / axis /
fresh-known-EMA") may be an EMPTY difference in data -- the researcher's `legal` may already exclude
TRADIFI_PERPETUAL, the 829 axis is a construction premise, and funding may already be NaN when stale.
So compare the two base NAME SETS per anchor, not only the downstream output.

  researcher base (combo_legs.py L37): legal & isfinite(funding)
  NC base        (nc_legs.py L65):     isfinite(NC_FEATURES base_val)   [legal & crypto & axis & fresh EMA]

Why this is a SAMPLE and not the full axis, stated rather than glossed: the researcher's base needs the
full-width `legal` mask, and NC does not persist it -- it exists only inside pass1. Deriving it for all
10,333 anchors is a full-axis pass-1 replay, ~2.47 s/anchor => ~7 h. This runs a named anchor sample.

What this does NOT do: it does not run `causal_legs`. That function carries a 900-anchor seat history, so
WL and LR are meaningless on a short sample; they need the full axis. Named, not quietly skipped.

usage: python news2_legs_base_diff.py <nc_devices> <tree> <cfg> <work> <members_hist> <out.json> <anchor>...
"""
import hashlib, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

W = "/dev/shm/news2_2026-09-23"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def main():
    nc_dev, tree, cfg, work, mh, out_json = sys.argv[1:7]
    anchors = [int(x) for x in sys.argv[7:]]
    t0 = time.time()
    from news2_nc_adapter import Replay

    F = np.load(f"{W}/work/NEWS_FEATURES.npz")
    syms = [str(s) for s in F["symbols"]]
    fa = F["anchors"].astype(np.int64)
    base_val = F["base_val"]
    pos = {int(a): i for i, a in enumerate(fa)}

    R = Replay(nc_dev, tree, cfg, work, mh)
    rows, unavailable = [], []
    for A in anchors:
        if A not in pos:
            unavailable.append({"anchor": A, "why": "anchor absent from NEWS_FEATURES"})
            continue
        i = pos[A]
        try:
            r = R.at(A)
        except Exception as e:
            unavailable.append({"anchor": A, "why": f"{type(e).__name__}: {e}"})
            continue
        scr = r.get("screen") or {}
        legal = scr.get("legal")
        if legal is None:
            unavailable.append({"anchor": A, "why": "pass1 produced no screen.legal"})
            continue
        legal = np.asarray(legal, bool)
        # full-width funding EMA, as the researcher's `funding` argument would be
        ema, led = R.I.funding(A)
        fund = np.array([ema.get(s, np.nan) if ema.get(s) is not None else np.nan for s in syms], float)
        res_base = np.flatnonzero(legal & np.isfinite(fund))
        nc_base = np.flatnonzero(np.isfinite(base_val[i]))
        sres, snc = set(res_base.tolist()), set(nc_base.tolist())
        only_res = sorted(sres - snc)
        only_nc = sorted(snc - sres)
        rows.append({
            "anchor": A,
            "n_researcher_base": len(sres), "n_nc_base": len(snc),
            "n_intersection": len(sres & snc),
            "n_only_researcher": len(only_res), "n_only_nc": len(only_nc),
            "symmetric_difference": len(only_res) + len(only_nc),
            "identical": not only_res and not only_nc,
            "only_researcher_names": [syms[j] for j in only_res[:25]],
            "only_nc_names": [syms[j] for j in only_nc[:25]],
            "n_legal": int(legal.sum()), "n_finite_funding": int(np.isfinite(fund).sum()),
            "n_members": (None if r.get("m") is None else int(len(r["m"]))),
        })
        print(f"  {A} researcher_base={len(sres):4d} nc_base={len(snc):4d} "
              f"symdiff={len(only_res)+len(only_nc):4d} (only_res {len(only_res)}, only_nc {len(only_nc)})",
              flush=True)

    measured = [x for x in rows]
    rec = {"device": "news2_legs_base_diff.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "argv": list(sys.argv),
           "question": "lead point 1: is the semantic difference in the funding rank base an EMPTY "
                       "difference in data?",
           "researcher_base_rule": "legal & isfinite(funding)   [combo_legs.py L37]",
           "nc_base_rule": "isfinite(NC_FEATURES base_val)   [nc_legs.py L65; legal & crypto & axis & fresh EMA]",
           "SAMPLE_NOT_FULL_AXIS": ("the researcher base needs the full-width `legal` mask, which NC does not "
                                    "persist (it lives inside pass1). Full axis would be ~2.47 s/anchor x "
                                    "10,333 = ~7 h. These are named sample anchors."),
           "not_done": ("causal_legs itself is NOT run here: it carries a 900-anchor seat history, so WL and "
                        "LR are meaningless on a short sample and need the full axis."),
           "anchors_requested": anchors, "rows": rows, "unavailable": unavailable,
           "n_measured": len(measured),
           "all_identical": (bool(measured) and all(x["identical"] for x in measured)),
           "VERDICT": ("NO-MEASUREMENT: no anchor measured" if not measured else
                       ("BASES_IDENTICAL on all %d sampled anchors" % len(measured)
                        if all(x["identical"] for x in measured) else
                        "BASES_DIFFER on %d of %d sampled anchors"
                        % (sum(1 for x in measured if not x["identical"]), len(measured)))),
           "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(out_json, "w"), indent=1)
    print(f"LEGS_BASE_DIFF VERDICT={rec['VERDICT']} measured={len(measured)} "
          f"unavailable={len(unavailable)} receipt={sha(out_json)[:16]}", flush=True)


if __name__ == "__main__":
    main()
