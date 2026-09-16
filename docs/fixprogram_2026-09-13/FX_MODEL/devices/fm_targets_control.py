#!/usr/bin/env python3
"""fm_targets_control.py -- queue item 3 control for fm_dlw_targets_asof.py against its base pod_dlw_targets_raw.py.

  T1 SOURCE DIFF     recorded, not gated (behaviour is the gate).
  T2 LEGACY BITWISE  base vs new with FMT_MEMBER_CLOCK=legacy_Em1, FMT_FORWARD_TERM=legacy_isfinite, FMT_TRADABLE=off:
                     every array the BASE writes must be BITWISE identical. Floats are compared through an integer
                     view so NaN payloads must match too (y4s / YR4s / YRZ are NaN-heavy by construction, so a float
                     comparison with NaN leniency would be far too weak). meta_json is excluded: it necessarily names
                     the device that wrote it.
  T3 ONE KNOB AT A TIME  with the legacy arm certified, flip exactly one knob per run and report member-population
                     counts -- and in particular whether removing the forward term INCREASES the dead-but-kept rows,
                     which is the TRN-06 coupling. Counts only; not a model or book claim.

  The base is read from the COMMITTED blob, not the working tree: FX-TRAIN has an in-flight TRN-02 change to the same
  file, so the working-tree copy is a moving target.

Safety: no subprocess / os.system / bash / requests; no network, no venue; nothing under ~/wide_shadow or
~/dl_quant_live. Outside the FIXPROGRAM 14.1 battery rule.

Usage: FM_TCTL_OUT=<receipt.json> FM_TCTL_TMP=<scratchdir> FM_TCTL_BASE=<path to the committed-blob copy> python3 ...
"""
import os, sys, json, time, hashlib, difflib, traceback
import numpy as np

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
BASE = os.environ["FM_TCTL_BASE"]
NEW = os.path.join(HERE, "fm_dlw_targets_asof.py")
OUT = os.environ["FM_TCTL_OUT"]
TMP = os.environ["FM_TCTL_TMP"]
TRADE_ART = os.path.join(REPO, "docs", "fixprogram_2026-09-13", "FX_DATA", "artifacts", "tradability_v1.npz")
os.makedirs(TMP, exist_ok=True)
os.environ.setdefault("FM_RED_OUT", os.path.join(TMP, "_unused.json"))
os.environ.setdefault("FM_RED_TMP", TMP)
sys.path.insert(0, HERE)
import fm_red_builders as FX   # noqa: E402


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def bitwise(a, b):
    if a.shape != b.shape or a.dtype != b.dtype:
        return False, {"shape_a": list(a.shape), "shape_b": list(b.shape),
                       "dtype_a": str(a.dtype), "dtype_b": str(b.dtype)}
    if a.dtype == object:
        bad = sum(0 if np.array_equal(x, y) else 1 for x, y in zip(a, b))
        return bad == 0 and len(a) == len(b), {"differing_rows": bad, "rows": len(a), "as": "per-row array_equal"}
    if a.dtype in (np.float16, np.float32, np.float64):
        iv = {np.dtype(np.float16): np.uint16, np.dtype(np.float32): np.uint32, np.dtype(np.float64): np.uint64}[a.dtype]
        d = int((a.view(iv) != b.view(iv)).sum())
        return d == 0, {"differing": d, "total": int(a.size), "as": "%s view (true bitwise)" % np.dtype(iv).name}
    d = int((a != b).sum())
    return d == 0, {"differing": d, "total": int(a.size), "as": str(a.dtype)}


def run(src, outdir, cache, panel, env_extra):
    os.makedirs(os.path.join(outdir, "data"), exist_ok=True)
    os.makedirs(os.path.join(outdir, "results"), exist_ok=True)
    e = {"DLWT_CACHE": cache, "DLWT_PANEL": panel, "DLWT_OUT": outdir}
    e.update(env_extra)
    ok, so, err = FX.run_builder(src, e)
    return os.path.join(outdir, "data", "dlw_targets.npz"), ok, so, err


def popstats(npz, ts, data):
    """Member-population counts. dead_kept = members whose forward window is entirely frozen (finite, all zero)."""
    Z = np.load(npz, allow_pickle=True)
    E_row = Z["E_row"].astype(np.int64)
    r5 = data[:, :, 0]
    dead = 0
    pairs = 0
    for i, r in enumerate(E_row):
        m = Z["members"][i]
        pairs += len(m)
        seg = r5[r + 1:r + 49][:, m]
        frozen = np.isfinite(seg).all(0) & (seg == 0).all(0)
        dead += int(frozen.sum())
    return {"n_anchors": int(len(E_row)), "member_pairs": int(pairs),
            "mean_members": round(pairs / max(len(E_row), 1), 3), "dead_kept_pairs": dead}


def main():
    rc = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)),
          "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "python": sys.version.split()[0], "numpy": np.__version__,
          "base": {"path": BASE, "sha256": sha(BASE), "note": "COMMITTED blob, not the working tree"},
          "new": {"path": os.path.relpath(NEW, REPO), "sha256": sha(NEW)},
          "tradability_artifact": {"path": os.path.relpath(TRADE_ART, REPO), "sha256": sha(TRADE_ART)},
          "shells_out": False, "network": False}

    a, b = open(BASE).read().splitlines(), open(NEW).read().splitlines()
    hunks = [{"tag": t, "base": [i1 + 1, i2], "new": [j1 + 1, j2]}
             for t, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if t != "equal"]
    rc["T1_source_diff"] = {"n_changed_hunks": len(hunks), "hunks": hunks,
                            "note": "recorded, not gated: identical BEHAVIOUR is the gate (T2)"}
    print("T1 changed hunks: %d" % len(hunks), flush=True)

    d = os.path.join(TMP, "t")
    os.makedirs(d, exist_ok=True)
    cache = os.path.join(d, "cache.npz")
    # Real venue names, taken from the pinned tradability artifact, so the symbol-axis join is a real join and not a
    # stub. BTCUSDT is forced in because the base builder indexes it. The artifact's anchor grid starts 2022-01-01
    # 00:00Z at 14400 s spacing, which is exactly this fixture's grid, so all of its anchors are covered.
    _tz = np.load(TRADE_ART, allow_pickle=True)
    _ts_all = [str(s) for s in _tz["symbols"]]
    _pick = ["BTCUSDT"] + [s for s in _ts_all if s != "BTCUSDT"][:FX.NW - 1]
    ts, syms, data = FX.make_cache(cache, seed=31, freeze_from=(5000, 17), symbols=_pick)   # one contract dies mid-axis
    panel = os.path.join(d, "panel.npz")
    FX.make_panel(panel, ts, syms, data)

    fb, okb, sob, eb = run(BASE, os.path.join(d, "base"), cache, panel, {})
    fl, okl, sol, el = run(NEW, os.path.join(d, "leg"), cache, panel,
                           {"FMT_MEMBER_CLOCK": "legacy_Em1", "FMT_FORWARD_TERM": "legacy_isfinite", "FMT_TRADABLE": "off"})
    if not (okb and okl) or not (os.path.exists(fb) and os.path.exists(fl)):
        rc["T2_legacy_bitwise"] = {"outcome": "INVALID", "base_ok": okb, "new_ok": okl, "error": eb or el,
                                   "stdout_tail": (sob + sol)[-900:]}
        rc["gate_T2_pass"] = False
    else:
        A, B = np.load(fb, allow_pickle=True), np.load(fl, allow_pickle=True)
        keys = [k for k in A.files if k != "meta_json"]
        per, allok = {}, True
        for k in keys:
            eq, det = bitwise(A[k], B[k])
            per[k] = {"bitwise_equal": eq, **det}
            allok = allok and eq
        rc["T2_legacy_bitwise"] = {"outcome": "PASS" if allok else "FAIL", "keys_compared": keys,
                                   "excluded": ["meta_json (names the writing device by construction)"],
                                   "per_array": per}
        rc["gate_T2_pass"] = allok
        print("T2 legacy bitwise: %s" % ("PASS" if allok else "FAIL"), flush=True)

    rc["T3_one_knob_at_a_time"] = {"note": "member-population counts only; NOT a model or book claim"}
    if rc.get("gate_T2_pass"):
        rc["T3_one_knob_at_a_time"]["legacy"] = popstats(fb, ts, data)
        arms = (("member_clock_serve_E", {"FMT_MEMBER_CLOCK": "serve_E", "FMT_FORWARD_TERM": "legacy_isfinite", "FMT_TRADABLE": "off"}),
                ("T1_trailing_only", {"FMT_MEMBER_CLOCK": "legacy_Em1", "FMT_FORWARD_TERM": "trailing_only", "FMT_TRADABLE": "off"}),
                ("T2_trailing_plus_tradable", {"FMT_MEMBER_CLOCK": "legacy_Em1", "FMT_FORWARD_TERM": "trailing_only",
                                               "FMT_TRADABLE": TRADE_ART, "FMT_TRADABLE_SHA": sha(TRADE_ART)}))
        for tag, knobs in arms:
            f2, ok2, so2, e2 = run(NEW, os.path.join(d, tag), cache, panel, knobs)
            if ok2 and os.path.exists(f2):
                s = popstats(f2, ts, data)
                s["knobs"] = {k: (os.path.basename(v) if k == "FMT_TRADABLE" and v != "off" else v)
                              for k, v in knobs.items() if k != "FMT_TRADABLE_SHA"}
                base_s = rc["T3_one_knob_at_a_time"]["legacy"]
                s["delta_member_pairs"] = s["member_pairs"] - base_s["member_pairs"]
                s["delta_dead_kept_pairs"] = s["dead_kept_pairs"] - base_s["dead_kept_pairs"]
                rc["T3_one_knob_at_a_time"][tag] = s
                print("T3 %-28s pairs %6d (%+d)  dead_kept %4d (%+d)"
                      % (tag, s["member_pairs"], s["delta_member_pairs"], s["dead_kept_pairs"],
                         s["delta_dead_kept_pairs"]), flush=True)
            else:
                rc["T3_one_knob_at_a_time"][tag] = {"outcome": "INVALID", "error": e2, "stdout_tail": so2[-600:]}
                print("T3 %-28s INVALID" % tag, flush=True)
    else:
        rc["T3_one_knob_at_a_time"]["skipped"] = "T2 did not pass; an uncertified builder's readings are meaningless"

    rc["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rc["wall_s"] = round(time.time() - T0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    json.dump(rc, open(OUT, "w"), indent=1, default=float)
    print("SUMMARY T2=%s hunks=%d wall=%.1fs" % (rc.get("gate_T2_pass"), len(hunks), rc["wall_s"]), flush=True)
    return 0


if __name__ == "__main__":
    try:
        _rc = main()
    except Exception:
        traceback.print_exc()
        _rc = 1
    sys.exit(_rc)
