#!/usr/bin/env python3
"""d10_item2_stalled_asof.py -- lead's item 2, per PREREG_item2_stalled_asof_quantification_2026-09-25.md.

Did the producer's funding as-of STALL at each anchor, and on which book cells?

The criteria, population, denominator and classes are frozen in the prereg (including revision 1, which
moved the population SOURCE from members_hist.npz -- present in only 9 of 49 snapshots -- to aux.json
prev_rec, present in all 49, with the definition unchanged). This device implements that document and adds
nothing to it.

TWO COMPARED QUANTITIES, each bound to the line that defines it:
  used    = the as-of row from snap/<A>/aux.json ledger_tail[sym], i.e. what the producer HAD at anchor A
  correct = the as-of row from the CURRENT ~/wide_shadow/state/aux.json ledger_tail[sym], limited to ft<=A
  as-of semantics from nc_contract.py:84-98 funding_asof: the last row with ft <= anchor, NaN unless
  anchor - ft <= FRESH_S (43200) and the EMA is finite; rn8 = rate*8/iv.

REFERENCE CALIBER AND ITS OWN WEAKNESS (prereg §2): `correct` is the same producer's LATER ledger, not an
independent third party. It catches "this anchor failed to read a settlement that was known later"; it
CANNOT catch "the producer never received that settlement at all". So every verdict says "relative to the
later-known ledger", never "relative to exchange truth". September has no published archive yet, which is
the October runbook item.

The EMA: funding_asof returns NaN when the EMA state is not finite. The EMA state at anchor A is only in
that anchor's snapshot, so BOTH sides use the snapshot's EMA. That is deliberate -- item 2 asks whether the
LEDGER's as-of stalled, not whether the EMA differed -- and it means the NaN gating is identical on both
sides, so a difference can only come from the ledger.

Modes:
  (default)            the audit
  --baseline-same-input   prereg §5.1: take `used` AND `correct` both from the current aux.json, i.e. the
                          same input twice. MUST return 100% AGREE / STALE=0. A comparator that manufactures
                          differences would make the window numbers meaningless, and this is the only step
                          that can show it.
  --positive-control      prereg §5.2: three perturbations, each of which must redden ITS OWN class.
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
import sys

import numpy as np

FRESH_S = 43200  # nc_contract.py:21
SNAP = os.path.expanduser("~/wide_shadow/state/snap")
LIVE_AUX = os.path.expanduser("~/wide_shadow/state/aux.json")
BUNDLE_CFG = os.path.expanduser("~/wide_shadow/shadow_bundle/config.json")
BUNDLE_AXIS = os.path.expanduser("~/wide_shadow/shadow_bundle/crypto_axis.json")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def u(ts):
    return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def asof(rows, A):
    """The last ledger row with ft <= A. rows are [ft, rate, iv?] as stored in aux.json ledger_tail."""
    best = None
    for r in rows:
        ft = int(r[0])
        if ft <= A and (best is None or ft > int(best[0])):
            best = r
    return best


def value_of(row, A, ema_finite):
    """(ft, rate, iv, rn8) under funding_asof's gates, or (ft, nan, nan, nan) when gated off."""
    if row is None:
        return None, float("nan"), float("nan"), float("nan")
    ft = int(row[0])
    rate = float(row[1])
    iv = float(row[2]) if len(row) > 2 and row[2] is not None else float("nan")
    if not ema_finite or (A - ft) > FRESH_S or not np.isfinite(iv) or iv == 0:
        return ft, rate, iv, float("nan")
    return ft, rate, iv, rate * 8.0 / iv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lo", default="2026-09-17T12:00Z")
    ap.add_argument("--hi", default="2026-09-24T20:00Z")
    ap.add_argument("--out", default=None)
    ap.add_argument("--baseline-same-input", action="store_true")
    ap.add_argument("--positive-control", action="store_true")
    a = ap.parse_args()

    def p(s):
        return int(datetime.datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(
            tzinfo=datetime.timezone.utc).timestamp())

    lo, hi = p(a.lo), p(a.hi)
    live = json.load(open(LIVE_AUX))
    live_tail = live["ledger_tail"]

    # prev_rec["members"] and ["sm_idx"] index the PANEL axis (observed max 827), NOT base_syms (530).
    # The consuming line in the producer is shadow_loop_v3.py:880  cfg["symbols_panel"][j] for j in m.
    # The snapshots do not store that axis, so it comes from the bundle -- and if the axis had shifted
    # during the window every index would silently name the wrong symbol. config.json (which holds it) was
    # last modified before the window; recorded and asserted here rather than assumed.
    panel = json.load(open(BUNDLE_CFG))["symbols_panel"]
    axis = json.load(open(BUNDLE_AXIS))
    axis_matches = list(axis.get("symbols", [])) == list(panel)

    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "prereg": "docs/PREREG_item2_stalled_asof_quantification_2026-09-25.md (incl. revision 1)",
           "mode": ("BASELINE_SAME_INPUT" if a.baseline_same_input else
                    ("POSITIVE_CONTROL" if a.positive_control else "AUDIT")),
           "window": [a.lo, a.hi],
           "reference_caliber": ("`correct` is the same producer's LATER ledger, not an independent source: "
                                 "it catches an anchor failing to read a later-known settlement, not a "
                                 "settlement the producer never received. Verdicts say 'relative to the "
                                 "later-known ledger', never 'relative to exchange truth'."),
           "live_aux": {"path": LIVE_AUX, "sha256": sha(LIVE_AUX), "symbols": len(live_tail)},
           "panel_axis": {"source": BUNDLE_CFG, "sha256": sha(BUNDLE_CFG), "n": None,
                          "config_mtime_utc": None, "crypto_axis_matches_panel": None,
                          "why_it_matters": ("members/sm_idx are PANEL indices; a shifted axis would make "
                                             "every index name the wrong symbol, silently")},
           "ema_note": ("both sides use the snapshot's EMA, so the NaN gating is identical and a difference "
                        "can only come from the ledger"),
           "anchors": [], "excluded_anchors": []}

    rec["panel_axis"].update({
        "n": len(panel), "crypto_axis_matches_panel": bool(axis_matches),
        "config_mtime_utc": datetime.datetime.fromtimestamp(
            os.path.getmtime(BUNDLE_CFG), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")})
    assert axis_matches, "crypto_axis.json axis differs from symbols_panel (shadow_loop_v3.py:326-327)"
    assert os.path.getmtime(BUNDLE_CFG) < lo, (
        "the panel axis file was modified inside the audit window; index->symbol mapping is not trustworthy",
        rec["panel_axis"]["config_mtime_utc"], a.lo)

    ts = sorted(int(x) for x in os.listdir(SNAP) if x.isdigit())
    inwin = [t for t in ts if lo <= t <= hi]
    rec["snapshots"] = {"total": len(ts), "in_window": len(inwin),
                        "retained_span": [u(ts[0]), u(ts[-1])],
                        "window_not_retained_before": u(ts[0]),
                        "note": ("lead's window starts 09-11; no per-anchor state is retained before "
                                 f"{u(ts[0])}, so that half is UNMEASURED, not undone")}

    tot = collections.Counter()
    stale_cells = []
    other_cells = []
    memcheck = {"compared": 0, "identical": 0, "differing": []}
    ctrl = {"placed": []} if a.positive_control else None

    for A in inwin:
        sdir = os.path.join(SNAP, str(A))
        try:
            snap = json.load(open(os.path.join(sdir, "aux.json")))
        except Exception as e:
            rec["excluded_anchors"].append({"anchor": u(A), "why": f"aux.json unreadable: {e!r}"[:120]})
            continue
        pr = snap.get("prev_rec") or {}
        if int(pr.get("anchor_ts", -1)) != A:
            rec["excluded_anchors"].append({"anchor": u(A), "why": "SNAP_ANCHOR_MISMATCH",
                                            "prev_rec_anchor_ts": pr.get("anchor_ts")})
            continue
        base = panel          # PANEL axis, not snap["base_syms"] -- see the note above
        members = [int(i) for i in pr["members"]]
        if members and max(members) >= len(panel):
            rec["excluded_anchors"].append({"anchor": u(A), "why": "member index beyond the panel axis",
                                            "max_index": max(members), "panel_n": len(panel)})
            continue
        sm = {int(j): float(w) for j, w in zip(pr["sm_idx"], pr["sm"])}
        ema = snap.get("ema") or {}
        snap_tail = snap["ledger_tail"]

        # prereg 6b: where both sources exist, the member sets must be element-wise identical
        mh = os.path.join(sdir, "members_hist.npz")
        if os.path.exists(mh):
            try:
                z = np.load(mh, allow_pickle=True)
                for k in z.files:
                    arr = z[k]
                    if arr.ndim == 1 and arr.dtype.kind in "iu" and arr.size == len(members):
                        memcheck["compared"] += 1
                        if list(int(x) for x in arr) == members:
                            memcheck["identical"] += 1
                        else:
                            memcheck["differing"].append({"anchor": u(A), "key": k})
                        break
            except Exception as e:
                memcheck.setdefault("errors", []).append({"anchor": u(A), "err": repr(e)[:80]})

        c = collections.Counter()
        for j in members:
            s = base[j]
            e = ema.get(s)
            ema_finite = isinstance(e, dict) and np.isfinite(float(e.get("acc", float("nan")) or float("nan")))
            rows_used = snap_tail.get(s)
            rows_corr = live_tail.get(s)
            if a.baseline_same_input:
                rows_used = rows_corr           # same input twice
            if rows_used is None or rows_corr is None:
                c["OUT_OF_TAIL"] += 1
                continue
            # the rolling 400-row tail can have truncated this anchor's window away
            if rows_corr and int(min(int(r[0]) for r in rows_corr)) > A:
                c["OUT_OF_TAIL"] += 1
                continue
            ru = asof(rows_used, A)
            rc = asof(rows_corr, A)
            uft, urate, uiv, urn8 = value_of(ru, A, ema_finite)
            cft, crate, civ, crn8 = value_of(rc, A, ema_finite)

            if a.positive_control and len(ctrl["placed"]) < 3 and ru is not None and rc is not None:
                kinds = [x["kind"] for x in ctrl["placed"]]
                prev = [r for r in rows_used if int(r[0]) < (uft or 0)]
                if "stale_substitution" not in kinds and prev:
                    p2 = max(prev, key=lambda r: int(r[0]))
                    uft, urate, uiv, urn8 = value_of(p2, A, ema_finite)
                    ctrl["placed"].append({"kind": "stale_substitution", "anchor": u(A), "symbol": s,
                                           "expect_class": "STALE"})
                elif "ulp" not in kinds and np.isfinite(urn8):
                    urn8 = float(np.nextafter(np.float64(urn8), np.inf))
                    assert urn8 != crn8 or not np.isfinite(crn8), "ULP collapsed; control vacuous"
                    ctrl["placed"].append({"kind": "ulp", "anchor": u(A), "symbol": s,
                                           "expect_class": "OTHER_DIFF"})
                elif "correct_side_deletion" not in kinds and rc is not None:
                    keep = [r for r in rows_corr if int(r[0]) != int(rc[0])]
                    cft, crate, civ, crn8 = value_of(asof(keep, A), A, ema_finite)
                    ctrl["placed"].append({"kind": "correct_side_deletion", "anchor": u(A), "symbol": s,
                                           "expect_class": "STALE_or_OTHER_DIFF (correct moves earlier)"})

            same = ((uft == cft) and ((urn8 == crn8) or (not np.isfinite(urn8) and not np.isfinite(crn8))))
            if ru is None and rc is None:
                c["NO_ASOF"] += 1
            elif same:
                c["AGREE"] += 1
            elif not np.isfinite(urn8) and not np.isfinite(crn8):
                c["NOT_FRESH_BOTH"] += 1
            elif not np.isfinite(urn8) and np.isfinite(crn8):
                c["USED_NAN_CORRECT_FINITE"] += 1
            elif np.isfinite(urn8) and not np.isfinite(crn8):
                c["USED_FINITE_CORRECT_NAN"] += 1
            elif uft is not None and cft is not None and uft < cft:
                c["STALE"] += 1
                if len(stale_cells) < 400:
                    stale_cells.append({"anchor": u(A), "symbol": s, "used_ft": u(uft),
                                        "correct_ft": u(cft), "behind_s": cft - uft,
                                        "used_rate": urate, "used_iv": uiv, "used_rn8": urn8,
                                        "correct_rate": crate, "correct_iv": civ, "correct_rn8": crn8,
                                        "book_weight": sm.get(j, 0.0),
                                        "side": ("short" if sm.get(j, 0.0) < 0 else
                                                 ("long" if sm.get(j, 0.0) > 0 else "flat"))})
            else:
                c["OTHER_DIFF"] += 1
                if len(other_cells) < 100:
                    other_cells.append({"anchor": u(A), "symbol": s, "used_ft": u(uft) if uft else None,
                                        "correct_ft": u(cft) if cft else None,
                                        "used_rate": urate, "used_iv": uiv, "used_rn8": urn8,
                                        "correct_rate": crate, "correct_iv": civ, "correct_rn8": crn8,
                                        "book_weight": sm.get(j, 0.0),
                                        "same_asof_timestamp": (uft == cft),
                                        "why_not_stale": "same as-of second, so the value differs, not the age"})

        n = len(members)
        closes = sum(c.values()) == n
        rec["anchors"].append({"anchor": u(A), "members": n, "classes": {k: int(v) for k, v in c.items()},
                               "closes": bool(closes)})
        assert closes, (f"classification does not close at {u(A)}", n, dict(c))
        for k, v in c.items():
            tot[k] += v
        tot["DENOM"] += n

    rec["totals"] = {k: int(v) for k, v in tot.items()}
    rec["member_source_crosscheck"] = memcheck
    denom = tot["DENOM"]
    rec["denominator"] = int(denom)
    rec["closure_all_anchors"] = bool(sum(v for k, v in tot.items() if k != "DENOM") == denom)
    rec["stale_cells"] = stale_cells
    rec["other_diff_cells"] = other_cells
    if tot["STALE"]:
        beh = sorted(x["behind_s"] for x in stale_cells)
        nz = [x for x in stale_cells if x["book_weight"] != 0.0]
        rec["stale_summary"] = {
            "n": int(tot["STALE"]), "pct_of_denominator": round(100.0 * tot["STALE"] / denom, 4) if denom else None,
            "behind_s_median": beh[len(beh) // 2] if beh else None,
            "behind_s_max": beh[-1] if beh else None,
            "with_nonzero_book_weight": len(nz),
            "short": sum(1 for x in nz if x["side"] == "short"),
            "long": sum(1 for x in nz if x["side"] == "long"),
            "caveat": "counts and weights only; weight x subsequent return is a PROJECTION and is NOT reported here (R25-04)"}

    print(f"item 2: stalled as-of, {a.lo}..{a.hi}   mode={rec['mode']}")
    print(f"  snapshots in window {len(inwin)} of {len(ts)} retained ({u(ts[0])}..{u(ts[-1])})")
    print(f"  DENOMINATOR (sum of per-anchor book members) = {denom}")
    print(f"  totals {rec['totals']}")
    print(f"  closure across anchors: {rec['closure_all_anchors']}")
    print(f"  member-source crosscheck: {memcheck['identical']}/{memcheck['compared']} identical"
          f"  differing={len(memcheck['differing'])}")
    if "stale_summary" in rec:
        print(f"  STALE {rec['stale_summary']}")

    if a.baseline_same_input:
        ok = (tot["STALE"] == 0 and tot["OTHER_DIFF"] == 0 and tot["USED_NAN_CORRECT_FINITE"] == 0
              and tot["USED_FINITE_CORRECT_NAN"] == 0)
        rec["baseline_result"] = {"verdict": "BASELINE_GREEN" if ok else "BASELINE_RED",
                                  "meaning": ("same input on both sides: any non-AGREE class here is the "
                                              "comparator manufacturing a difference, and would invalidate "
                                              "the window numbers")}
        rec["verdict"] = rec["baseline_result"]["verdict"]
        print(f"  BASELINE {rec['verdict']}")
    elif a.positive_control:
        got = collections.Counter()
        for x in ctrl["placed"]:
            got[x["kind"]] += 1
        seen_stale = tot["STALE"] >= 1
        seen_other = tot["OTHER_DIFF"] >= 1
        rec["positive_control"] = ctrl
        rec["positive_control_result"] = {
            "placed": [x["kind"] for x in ctrl["placed"]],
            "stale_class_reddened": bool(seen_stale), "other_diff_class_reddened": bool(seen_other),
            "verdict": "CONTROL_PASS" if (seen_stale and seen_other) else "CONTROL_FAIL",
            "meaning": "every red counter in this run is my own injected perturbation"}
        rec["verdict"] = "POSITIVE_CONTROL_RUN_NOT_AN_AUDIT"
        print(f"  CONTROL {rec['positive_control_result']['verdict']} placed={rec['positive_control_result']['placed']}")
    else:
        rec["verdict"] = ("NO_STALLED_ASOF_IN_RETAINED_WINDOW" if tot["STALE"] == 0
                          else "STALLED_ASOF_PRESENT")
        print(f"  VERDICT {rec['verdict']}")
    print("  NOTE 4h subsequent return per stale cell is NOT in this run; counts/weights/sides only.")

    if a.out:
        json.dump(rec, open(a.out, "w"), indent=1)
        print(f"  receipt -> {a.out}  sha256={sha(a.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
