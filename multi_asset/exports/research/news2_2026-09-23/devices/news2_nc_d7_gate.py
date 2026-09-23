"""DESIGN §E4(a) admission gate, on the nc tree: is F8_TREND_ROWS="last" allowed?

"last" computes the stable trend only for the anchor row the mini pipeline extracts. It is admissible
only if the EXTRACTED row is bitwise equal to the row "all" produces. Arms differ in the SHIPPED TEXT
(nc built with NC_TREND_ROWS=last vs =all), never in an environment variable, so the comparison cannot
degenerate into a setting against itself.

Arms carry the D5+D6 floor: the nc A-part King block references `c7`, introduced by B's member-screen
rewrite, so a subset without D5/D6 crashes at the first anchor (receipts/ARM_VIABILITY.json).
  floor        D5,D6              -- the base the D7 signal is measured against
  floorD7      D5,D6,D7  last     -- the deployable setting
  floorD7all   D5,D6,D7  all      -- the researcher's text, every anchor row

Three ways this could pass while proving nothing, all of them refused or reported:
  * the two signal anchors absent from the sample   -> the gate REFUSES to run
  * no anchor where D7 moves the served row         -> PASS(NO-SIGNAL), named
  * the default member history not matching the arm -> reported per anchor; pass 2 comparisons are
    only counted where the arm's own pass-1 members equal the history's, so the shared history is
    exact for the compared rows rather than assumed to be

usage: python news2_nc_d7_gate.py <arms_root> <nc_devices> <cfg> <members_hist.npz> <work> <out.json> <anchor> [...]
"""
import hashlib, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from news2_nc_adapter import Replay

# Which anchors carry signal is a property of the CONTRACT, not a constant: the two anchors that
# carried it on the old contract (1685520000 / 1742428800) carry none on the new one, while the
# predictor finds 960 others. So the requirement is driven by the predictor receipt, not hardcoded.
MIN_SIGNAL_ANCHORS = 4
ARMS = {"floor": "floor", "all": "floorD7all", "last": "floorD7"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def diff(a, b):
    if a is None or b is None:
        return None
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    if a.shape != b.shape:
        return -1
    return int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum())


def main():
    arms_root, nc_dev, cfg, mh_path, pred_path, work, out_path = sys.argv[1:8]
    anchors = sorted(set(int(x) for x in sys.argv[8:]))
    # the sample must contain anchors the predictor says can differ, or the comparison has no resolution
    P = json.load(open(pred_path))
    pred_signal = set(P.get("suggested_gate_anchors", []))
    pred_examples = set(int(k) for k in P.get("examples", {}))
    predicted = pred_signal | pred_examples
    in_sample = sorted(a for a in anchors if a in predicted)
    assert len(in_sample) >= MIN_SIGNAL_ANCHORS, (
        f"refusing: need >= {MIN_SIGNAL_ANCHORS} anchors the predictor marks as able to differ; "
        f"sample has {len(in_sample)} ({in_sample}). Predictor: {pred_path}")
    t0 = time.time()

    with np.load(mh_path) as z:
        MH = {int(a): z["idx"][z["off"][i]:z["off"][i + 1]].astype(np.int64) for i, a in enumerate(z["anchors"])}

    R = {}
    declared = {}
    for tag, arm in ARMS.items():
        tree = os.path.join(arms_root, f"tree_{arm}")
        rec = json.load(open(os.path.join(tree, "PATCH_RECEIPT.json")))
        declared[tag] = rec.get("trend_rows_declared")
        R[tag] = Replay(nc_dev, tree, cfg, os.path.join(work, tag), mh_path)
    assert declared["all"] == "all" and declared["last"] == "last", ("arms do not declare what they should", declared)

    rows, timing = [], {}
    for A in anchors:
        out, rec = {}, {"anchor": A, "declared": declared}
        for tag in ("floor", "all", "last"):
            t1 = time.time()
            r = R[tag].at(A)
            timing.setdefault(tag, {})[str(A)] = round(time.time() - t1, 2)
            out[tag] = r
            print(f"{time.strftime('%H:%M:%S', time.gmtime())} {tag:5s} {A} "
                  f"members={len(r['m']) if r.get('m') is not None else None} "
                  f"X89={'yes' if r.get('X89') is not None else 'no'} {timing[tag][str(A)]}s", flush=True)
        if any(out[t].get("X89") is None for t in ("floor", "all", "last")):
            rec["status"] = "UNAVAILABLE"
            rec["why"] = {t: out[t].get("unavailable") for t in out if out[t].get("unavailable")}
            rows.append(rec); continue
        # the shared member history is only valid for an arm whose own pass-1 members match it
        hist = MH.get(A)
        rec["history_matches_arm_members"] = {t: (hist is not None and np.array_equal(np.sort(out[t]["m"]), np.sort(hist)))
                                              for t in ("floor", "all", "last")}
        rec["status"] = "OK"
        rec["n_members"] = int(len(out["floor"]["m"]))
        rec["same_members_all_vs_last"] = bool(np.array_equal(out["all"]["m"], out["last"]["m"]))
        rec["D7_moves_the_row"] = diff(out["floor"]["X89"], out["all"]["X89"])
        rec["all_vs_last_X89"] = diff(out["all"]["X89"], out["last"]["X89"])
        rec["all_vs_last_X82"] = diff(out["all"]["X82"], out["last"]["X82"])
        rec["all_vs_last_kingX78"] = diff(out["all"]["king_X78"], out["last"]["king_X78"])
        rows.append(rec)
        print(f"   {A} D7_moves_row={rec['D7_moves_the_row']} all_vs_last X89={rec['all_vs_last_X89']} "
              f"X82={rec['all_vs_last_X82']} king={rec['all_vs_last_kingX78']} "
              f"hist_ok={all(rec['history_matches_arm_members'].values())}", flush=True)

    ok = [r for r in rows if r.get("status") == "OK"]
    # only rows whose shared history matches every arm's own members are admissible evidence
    usable = [r for r in ok if all(r["history_matches_arm_members"].values())]
    bad = [r for r in usable if r["all_vs_last_X89"] or r["all_vs_last_X82"] or r["all_vs_last_kingX78"]
           or not r["same_members_all_vs_last"]]
    signal = [r for r in usable if (r["D7_moves_the_row"] or 0) > 0]
    if not usable:
        verdict = "UNAVAILABLE(no anchor with a matching member history)"
    elif bad:
        verdict = "FAIL"
    elif not signal:
        verdict = "PASS(NO-SIGNAL: no anchor in this sample is one where D7 moves the served row)"
    else:
        verdict = "PASS"
    med = lambda d: round(float(np.median(list(d.values()))), 2) if d else None
    rec = {"device": "news2_nc_d7_gate.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "design_ref": "DESIGN E4(a) admission gate, rebuilt on the nc tree",
           "arms": ARMS, "declared_trend_rows": declared, "floor": "D5,D6",
           "members_hist": {"path": mh_path, "sha256": sha(mh_path)},
           "min_signal_anchors_required": MIN_SIGNAL_ANCHORS,
           "predictor": {"path": pred_path, "sha256": sha(pred_path),
                         "n_anchors_with_signal": P.get("n_anchors_with_signal")},
           "sample_anchors_predicted_to_differ": in_sample, "anchors": anchors,
           "rows": rows, "n_ok": len(ok), "n_usable": len(usable),
           "n_anchors_where_D7_moves_the_row": len(signal),
           "median_seconds": {k: med(v) for k, v in timing.items()}, "seconds_per_anchor": timing,
           "VERDICT": verdict, "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_NC_D7_GATE VERDICT={verdict} usable={len(usable)} with_signal={len(signal)} "
          f"median_all={rec['median_seconds'].get('all')}s median_last={rec['median_seconds'].get('last')}s "
          f"receipt_sha256={sha(out_path)}", flush=True)
    sys.exit(0 if verdict.startswith("PASS") else 1)


if __name__ == "__main__":
    main()
