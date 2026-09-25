#!/usr/bin/env python3
"""d10_nc_fundnow_vs_archive.py -- is the LIVE producer's own fund_now right, or is it on the wrong side?

lead's priority target, part (2): "查明在役生产者(NC)的资金费腿消费的是哪一个来源, 引用那一行代码".

THE LINEAGE, cited rather than inferred:
  * shadow_loop_v3.py:619   fe_v[j], fn_v[j], iv_v[j], _rn8 = NC.funding_asof(st.ema.get(s), led[-1], anchor)
        -> the live producer's fund_now comes from nc_contract.funding_asof over the LEDGER tail.
  * nc_contract.py:84-98    funding_asof returns (ema, rate, iv, rate*8/iv), NaN unless anchor - ft <= FRESH_S.
  * shadow_loop_v3.py:624   FE_ANCH[:, 81] = np.nan_to_num(fn_v[m], nan=0)   -> fund_now enters the feature
        matrix at column 81 and NaN becomes 0.
  * bundle_config.json keep_names (78 cols) contains 'fund_ema' and 'fund_now' -> fund_now IS a King input.
  * the funding LEG is a different consumer: nc_legs.py:71 ranks fe_v (the EMA), and nc_legs.py:73-74 takes
        RN8 from NC.funding_asof(...)[3]. Neither reads the wide panel's f_fund_now.

WHY THIS DEVICE EXISTS. The adjudication showed the wide panel right and fund_replay.npz's last_rate wrong
on 2,017 of 2,017 judged cells. The live producer uses the SAME RULE FAMILY as that replay (funding_asof
over the ledger), so it is tempting to conclude the live book is on the wrong side. That would be an
inference from a shared rule, not a measurement: the replay is a separate artifact and its ledger input may
differ from the live producer's. This device compares the LIVE producer's own fn_v, as stored in
NEWS_FEATURES, against the archive on the same cells. An inference becomes a reading.
"""
import argparse, collections, csv, datetime, glob, hashlib, io, json, os, sys, zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import d10_manifest_gate as GATE   # R25-11: checksum_match must be True, set equality, per-file re-hash
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__)))), "common"))
import fund_replay_guard as FRG   # records the replay artifact's provenance state in the receipt

FRESH_S = 43200


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


def iso(t):
    return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True)
    ap.add_argument("--panel", required=True)
    ap.add_argument("--replay", required=True)
    ap.add_argument("--zips-root", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    panel_real = os.path.realpath(a.panel)
    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           # the archive gate is load-bearing for every number below it, so the receipt names
           # WHICH gate signed it (R25-11): a conclusion and its judging device share a lifetime.
           "gate_sha256": sha(os.path.realpath(GATE.__file__)),
           "python": sys.executable, "numpy": np.__version__,
           "task": "does the LIVE producer's own fund_now match the archive on the disputed cells",
           "lineage_cited": {
               "live_fund_now": "shadow_loop_v3.py:619 NC.funding_asof(st.ema.get(s), led[-1], anchor) -> ledger",
               "funding_asof": "nc_contract.py:84-98, returns (ema, rate, iv, rate*8/iv), NaN if anchor-ft > FRESH_S",
               "enters_features_at": "shadow_loop_v3.py:624 FE_ANCH[:, 81] = nan_to_num(fn_v, nan=0)",
               "is_a_king_input": "bundle_config.json keep_names contains 'fund_now'",
               "funding_leg_is_a_different_consumer": "nc_legs.py:71 ranks fe_v (EMA); nc_legs.py:73-74 RN8 = funding_asof(...)[3]"},
           "why": "the replay and the live producer share a rule family; sharing a rule is not evidence of sharing a value",
           "inputs": {"features": {"path": a.features, "sha256": sha(a.features)},
                      "panel": {"resolved": panel_real, "sha256": sha(panel_real)},
                      "replay": {"path": a.replay, "sha256": sha(a.replay)},
                      "inventory": {"path": a.inventory, "sha256": sha(a.inventory)}}}

    F = np.load(a.features, allow_pickle=True)
    anchors = F["anchors"].astype(np.int64); off = F["off"].astype(np.int64)
    mem = F["m"].astype(np.int64); fnv = np.asarray(F["fn_v"], np.float64)
    fsyms = [str(s) for s in F["symbols"]]

    rec["replay_provenance"] = FRG.require_clean_fund_replay(
        a.replay, allow=(FRG.DEFECTIVE, FRG.UNSTAMPED, FRG.CLEAN))   # record, do not refuse: judging it is the job
    P = np.load(panel_real, allow_pickle=True); R = np.load(a.replay, allow_pickle=True)
    pt = P["ts"].astype(np.int64); rt = R["anchors"].astype(np.int64)
    ps = [str(s) for s in P["symbols"]]; rs = [str(s) for s in R["symbols"]]
    ti = np.intersect1d(pt, rt); si = [s for s in ps if s in set(rs)]
    pr = np.searchsorted(pt, ti); rr = np.searchsorted(rt, ti)
    FN = P["f_fund_now"][np.ix_(pr, [ps.index(s) for s in si])]
    LR = R["last_rate"][np.ix_(rr, [rs.index(s) for s in si])]
    bad = np.isfinite(FN) & np.isfinite(LR) & (FN != LR.astype(np.float32))
    assert int(bad.sum()) == 5613, ("must reproduce fresh's 5,613", int(bad.sum()))

    # archive truth
    have, arc = set(), collections.defaultdict(list)
    for mdir in sorted(glob.glob(os.path.join(a.zips_root, "*-*"))):
        month = os.path.basename(mdir)
        gv = GATE.verify_month(mdir, month)
        if not gv["ok"]:
            rec.setdefault("months_skipped", []).append({"month": month, "verdict": gv["verdict"]})
            continue
        rec.setdefault("months_verified", []).append(
            {"month": month, "zip_entries": gv["n_zip_entries"], "rehashed": gv["n_rehashed"],
             "manifest_sha256": gv["manifest_sha256"]})
        have.add(month)
        for zp in glob.glob(os.path.join(mdir, "*-fundingRate-*.zip")):
            s = os.path.basename(zp).split("-fundingRate-")[0]
            z = zipfile.ZipFile(zp)
            for row in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8"))):
                if row and row[0].strip().isdigit():
                    arc[s].append((int(round(int(row[0]) / 1000.0)), float(row[2])))
    for s in arc:
        arc[s].sort()
    inv = json.load(open(a.inventory))["inventory"]
    win = {s: (lambda m: (m[0], m[-1]) if m else None)(sorted(d["months"])) for s, d in inv.items()}

    # live producer's fn_v, keyed by (symbol, anchor)
    live = {}
    apos = {int(t): i for i, t in enumerate(anchors)}
    for i in range(len(anchors)):
        t = int(anchors[i])
        for k in range(off[i], off[i + 1]):
            live[(fsyms[int(mem[k])], t)] = float(fnv[k])

    counts = collections.Counter(); by_name = collections.defaultdict(collections.Counter)
    ex = collections.defaultdict(list)
    for i in np.flatnonzero(bad.any(1)):
        anchor = int(ti[i]); month = datetime.datetime.fromtimestamp(anchor, datetime.timezone.utc).strftime("%Y-%m")
        if month not in have:
            continue
        for j in np.flatnonzero(bad[i]):
            s = si[j]
            w = win.get(s)
            k = None
            for t, r in reversed(arc.get(s, [])):
                if t <= anchor:
                    k = (t, r); break
            if k is None or anchor - k[0] > FRESH_S:
                if w is None or month > w[1] or month < w[0]:
                    continue                      # no truth here; already bucketed by the other device
                truth = float("nan")
            else:
                truth = k[1]
            if not np.isfinite(truth):
                continue
            lv = live.get((s, anchor))
            if lv is None:
                counts["LIVE_CELL_ABSENT_symbol_not_a_member_that_anchor"] += 1
                by_name[s]["LIVE_CELL_ABSENT_symbol_not_a_member_that_anchor"] += 1
                continue
            v = ("LIVE_MATCHES_ARCHIVE" if np.float32(lv) == np.float32(truth)
                 else "LIVE_DISAGREES_WITH_ARCHIVE")
            counts[v] += 1; by_name[s][v] += 1
            if len(ex[v]) < 12:
                ex[v].append({"symbol": s, "anchor": iso(anchor), "live_fn_v": lv,
                              "archive_truth": truth, "panel": float(FN[i, j]),
                              "replay_last_rate": float(LR[i, j]),
                              "live_equals_replay": bool(np.float32(lv) == np.float32(LR[i, j])),
                              "live_equals_panel": bool(np.float32(lv) == np.float32(FN[i, j]))})
    tot = sum(counts.values())
    rec["counts"] = dict(counts)
    rec["cells_with_archive_truth_and_a_live_value"] = tot
    if tot:
        rec["live_disagreement_rate_pct"] = round(100.0 * counts["LIVE_DISAGREES_WITH_ARCHIVE"] / tot, 3)
    rec["top10_names"] = [{"symbol": s, "total": sum(c.values()), "by_verdict": dict(c)}
                          for s, c in sorted(by_name.items(), key=lambda kv: -sum(kv[1].values()))[:10]]
    rec["examples"] = dict(ex)
    same_as_replay = sum(1 for v in ex.values() for e in v if e["live_equals_replay"])
    rec["examples_note"] = (f"of the {sum(len(v) for v in ex.values())} examples kept, {same_as_replay} have the "
                            "live value equal to the replay's last_rate; that is the check on whether the live "
                            "producer really sits on the replay's side or only shares its rule")
    rec["verdict"] = "MEASURED"
    rec["limits"] = ["only cells that have archive truth AND a live member value are counted",
                     "this measures fund_now, a King INPUT column; the funding LEG consumes fe_v and RN8 instead "
                     "(nc_legs.py:71, 73-74), so a defect here is a model-input defect, not directly a leg defect"]
    with open(a.out, "w") as f:
        json.dump(rec, f, indent=2)

    print("LIVE PRODUCER fund_now vs ARCHIVE, on the disputed cells")
    print(f"  cells with archive truth and a live value: {tot}")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"     {k:52s} {v}")
    if tot:
        print(f"  live disagreement rate: {rec['live_disagreement_rate_pct']}%")
    print(f"  {rec['examples_note']}")
    for k, v in ex.items():
        for e in v[:4]:
            print(f"     [{k}] {e['symbol']:12s} {e['anchor']}  live={e['live_fn_v']:+.8f}"
                  f"  archive={e['archive_truth']:+.8f}  panel={e['panel']:+.8f}"
                  f"  replay={e['replay_last_rate']:+.8f}  live==replay:{e['live_equals_replay']}"
                  f"  live==panel:{e['live_equals_panel']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
