"""news_p2_build_guarded.py — the ONLY sanctioned entry point to news_p2_build.py.

WHY A WRAPPER RATHER THAN AN EDIT (lead ruling 2026-09-26). `news_p2_build.py` is pinned by the FRESH and NEW_S
`work/f10_s*/TRAIN_RECEIPT.json` files. I wired `require_clean_fund_replay` INTO it, which changed its bytes, and
`fa_ladder.py` L206 (`training source drift`) then refused the FRESH ladder end -- the second time in one session
that I edited a pinned source in place. A pinned file must stay byte-identical; the gate goes in front of it.

WHAT THIS DOES
  1. resolves the same `fund_replay.npz` path the pinned module would read (W from news_hist_features, exactly as
     `news_p2_build.py` L11 does -- not a re-declared constant that could drift from it);
  2. calls `require_clean_fund_replay(path)` with **NO `allow` argument**. This path writes `fund_now` into the F10
     features, i.e. it is how the fund_replay defect reached trained models. A measurement device may name a dirty
     state and proceed; a PRODUCER may not;
  3. only then executes the pinned file, unmodified, via runpy, forwarding argv so `worker N` / `merge` still work.

The pinned file's sha is asserted before execution, so this wrapper also fails if someone edits it in place again.

RED CONTROL (--red): points the guard at the current (unstamped) artifact and requires a refusal; it does not
execute the pinned module. A gate that has not been seen to refuse is not known to refuse.

usage: ... news_p2_build_guarded.py WL worker <N> | merge | --red
"""
import os, sys, json, hashlib, runpy, time

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PINNED = os.path.join(HERE, "news_p2_build.py")
PINNED_SHA = "809c0c4afaa95baaca1b3ee573a0403d"      # first 32 hex; what the training receipts pin
GUARD_SHA = "9113d28a49b858df83c916c295ce0bc8286950b1d28b767dd07b61c9047ced25"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


_g = os.path.join(HERE, "fund_replay_guard.py")
assert sha(_g) == GUARD_SHA, "fund_replay_guard.py drifted from the pinned sha"
from fund_replay_guard import require_clean_fund_replay, fund_replay_status

cur = sha(PINNED)
assert cur.startswith(PINNED_SHA), (
    f"news_p2_build.py is NOT the pinned file (current {cur[:32]}, pinned {PINNED_SHA}). It must stay "
    "byte-identical: the FRESH/NEW_S training receipts pin it, and editing it in place breaks the provenance "
    "chain -- see test_pinned_sources_intact.py")

# the same path the pinned module resolves (its L11 is `W = H.W`), taken from the same module rather than re-declared
import news_hist_features as H
FR = os.path.join(H.W, "work", "fund_replay.npz")

RED = "--red" in sys.argv[2:]
if RED:
    st = fund_replay_status(FR)
    print("NEWS_P2_BUILD_GUARDED red control: artifact state = %s" % st["state"], flush=True)
    fired = False
    try:
        require_clean_fund_replay(FR)
    except RuntimeError as e:
        fired = True
        print("  gate REFUSED as designed: %s" % str(e)[:110], flush=True)
    rec = {"device": "news_p2_build_guarded.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "pinned_file": PINNED, "pinned_sha256": cur, "fund_replay": FR,
           "artifact_state": st["state"], "gate_refused": fired,
           "note": "red control only -- the pinned module was NOT executed"}
    out = os.path.join(HERE, "NEWS_P2_BUILD_GUARDED_REDCONTROL.json")
    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=1); f.flush(); os.fsync(f.fileno())
    with open(tmp) as f:
        assert json.load(f) == json.loads(json.dumps(rec)), "receipt did not read back equal"
    os.replace(tmp, out)
    assert fired, "RED CONTROL FAILED: the gate did not refuse an unstamped artifact -- it is decorative"
    print("  red control PASSED (refusal observed, pinned module not run)", flush=True)
    sys.exit(0)

# ---- the gate: no `allow`, because this is the producer path ----
st = require_clean_fund_replay(FR)
print("NEWS_P2_BUILD_GUARDED gate passed: %s (%s)" % (st["state"], FR), flush=True)

# ---- execute the pinned file, unmodified ----
sys.argv = [PINNED] + sys.argv[2:]
runpy.run_path(PINNED, run_name="__main__")
