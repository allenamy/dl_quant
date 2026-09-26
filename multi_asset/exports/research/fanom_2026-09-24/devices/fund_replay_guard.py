#!/usr/bin/env python3
"""fund_replay_guard.py -- one line for any consumer of fund_replay.npz to refuse a contaminated artifact.

WHY THIS EXISTS, and what it admits. On 2026-09-25 I added a deprecation guard to the PRODUCER
(news_fund_replay.py): it refuses to execute a funding block whose interval skip gate lacks the `_bulk_ok`
term, and stamps `skip_gate_guard` into any npz produced deliberately anyway. That covers regeneration and
nothing else. The artifact that ALREADY exists carries no stamp, and a census of its consumers found roughly
fifteen devices reading it with no contamination check of any kind -- including all three copies of
news_p2_build.py, which is the path that feeds `fund_now` into the F10 features. A gate on the producer is
not a gate on the consumers: the defect reaches conclusions through the consumers.

So this module is the consumer half, kept deliberately small and adoption-cheap:

    from fund_replay_guard import require_clean_fund_replay
    require_clean_fund_replay(path)      # raises unless the artifact is stamped guarded

    # or, for a device that must keep running on a known-dirty artifact on purpose:
    st = fund_replay_status(path)        # never raises; returns the status for the receipt

Three states, and the middle one is the honest part:
    CLEAN         the npz carries skip_gate_guard with skip_gate_guarded True
    DEFECTIVE     the npz carries a stamp saying the skip gate was unguarded
    UNSTAMPED     no stamp at all -- produced before the guard existed. This is NOT clean: every artifact
                  built before 2026-09-25 is unstamped, and the one known such artifact is contaminated on
                  ~5,613 cells. Absence of a mark is absence of evidence, so UNSTAMPED is refused by default
                  rather than waved through, which is the same absent-key-means-pass error the manifest gate
                  had until R25-11.

`allow` lets a caller proceed on a named state, but it must name it, and the returned status belongs in that
device's receipt so the conclusion carries the caliber of its input.

I did not edit the fifteen consumers myself: they live in three other agents' export directories, and adding
a mandatory step to someone else's pipeline is how legal early-exit paths acquire new failure modes. This is
offered for adoption, and the exposure is reported rather than left implicit.
"""
import json
import os

CLEAN = "CLEAN"
DEFECTIVE = "DEFECTIVE_UNGUARDED_SKIP_GATE"
UNSTAMPED = "UNSTAMPED_PROVENANCE_UNKNOWN"
MISSING = "FILE_MISSING"

_WHY = {
    DEFECTIVE: ("the npz says its funding block ran with an unguarded interval skip gate: from a cold start "
                "the as-of self-locks and never advances past the settlement that triggered an interval "
                "switch, so ~5,613 cells hold a real but stale rate"),
    UNSTAMPED: ("the npz carries no skip_gate_guard stamp, so it predates the guard (2026-09-25). Unstamped "
                "is not clean: the one known artifact of this kind is contaminated. Absence of a mark is not "
                "evidence of cleanliness"),
    MISSING: "the artifact is not on disk",
}


def fund_replay_status(path):
    """Never raises. Returns {state, why, stamp, path}."""
    if not os.path.exists(path):
        return {"state": MISSING, "why": _WHY[MISSING], "stamp": None, "path": path}
    stamp = None
    try:
        import numpy as np
        z = np.load(path, allow_pickle=False)
        if "skip_gate_guard" in getattr(z, "files", []):
            raw = z["skip_gate_guard"]
            stamp = json.loads(str(raw.item() if getattr(raw, "shape", ()) == () else raw))
    except Exception as e:  # a read failure is unknown, and unknown is not clean
        return {"state": UNSTAMPED, "why": f"{_WHY[UNSTAMPED]} (read failed: {e!r}" + ")",
                "stamp": None, "path": path}
    if stamp is None:
        return {"state": UNSTAMPED, "why": _WHY[UNSTAMPED], "stamp": None, "path": path}
    if stamp.get("skip_gate_guarded") is True:
        return {"state": CLEAN, "why": "the producer's skip gate carried the _bulk_ok term",
                "stamp": stamp, "path": path}
    return {"state": DEFECTIVE, "why": _WHY[DEFECTIVE], "stamp": stamp, "path": path}


def require_clean_fund_replay(path, allow=()):
    """Raise unless the artifact is CLEAN, or its state is explicitly named in `allow`.

    `allow` must name states, never be a blanket True: a caller that wants to read a known-dirty artifact has
    to say which kind of dirty it accepts, and the returned status goes in its receipt.
    """
    st = fund_replay_status(path)
    if st["state"] == CLEAN or st["state"] in tuple(allow):
        return st
    raise RuntimeError(
        f"fund_replay artifact refused: {st['state']} -- {st['why']}. path={path}. "
        "Rebuild it with a producer whose skip gate carries `_bulk_ok` (news_fund_replay.py now refuses "
        "otherwise), or pass allow=(...) naming this state and record the returned status in your receipt. "
        "Receipts: D10_ROOTCAUSE_last_rate.json + D10_ROOTCAUSE_last_rate_CORRECTION_2026-09-25.json.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        sys.exit(64)
    bad = 0
    for p in sys.argv[1:]:
        st = fund_replay_status(p)
        bad += 0 if st["state"] == CLEAN else 1
        print(f"{st['state']:34s} {p}")
        if st["state"] != CLEAN:
            print(f"    {st['why']}")
    sys.exit(0 if bad == 0 else 2)
