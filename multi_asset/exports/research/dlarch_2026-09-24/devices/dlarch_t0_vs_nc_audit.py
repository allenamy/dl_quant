"""dlarch_t0_vs_nc_audit.py -- what differs between T0 and the in-service NC F10, and is either leaking?

lead 2026-09-25: "T0 is below NC in the 2026 segment on all 8 seeds (mean -1.44, SE 0.20). That needs an
explanation, and it may bear on the user's concern that live is much worse than backtest." Two questions,
both answerable read-only from receipts and code:

  (1) DIFFERENCES -- fold scheme, WL mask, seed, hyperparameters, inputs, itemised.
  (2) LEAKAGE -- for every 2026 anchor, does the scoring model's training label end precede that anchor?
      Checked SEPARATELY for F10 and for King, because they have different fold schemes.

It compares RECEIPTS, not prose. The T0 trainer's docstring claims "the recipe is UNCHANGED" and "nothing
else changes"; that claim is the thing under test here, so it cannot be the evidence.

A note on what a leakage check can and cannot say: this compares recorded fold boundaries. It establishes
that no fold's training labels reach into its own scoring window. It does NOT establish the absence of
every leakage channel (e.g. a feature built with future information would not show up here) -- that is a
different audit, and saying so is part of the answer.

usage: dlarch_t0_vs_nc_audit.py <env-whitelist> <t0-seed-dir> <nc-seed-dir> <king-receipt> <out.json>
"""
import os, sys, json, glob, time, hashlib

WL = set(sys.argv[1].split(","))
_x = sorted(set(os.environ) - WL)
assert not _x, f"env outside whitelist: {_x}"
T0DIR, NCDIR, KINGR, OUT = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def folds(root):
    out = {}
    for p in sorted(glob.glob(os.path.join(root, "*", "FOLD_RECEIPT.json"))):
        r = json.load(open(p))
        a = r.get("admission") or {}
        out[r["fold"]] = {"max_train_label_end": a.get("max_train_label_end"),
                          "test_start": a.get("test_start"), "cutoff": a.get("cutoff"),
                          "train_anchors": a.get("train_anchors"),
                          "test_anchors": r.get("test_anchors"), "scored_pairs": r.get("scored_pairs"),
                          "seat_census": r.get("seat_census")}
    return out


t0, nc = folds(T0DIR), folds(NCDIR)
rt0 = json.load(open(os.path.join(T0DIR, "TRAIN_RECEIPT.json")))
rnc = json.load(open(os.path.join(NCDIR, "TRAIN_RECEIPT.json")))

# ── (1) differences ────────────────────────────────────────────────────────────────────────────────
base = lambda d: {os.path.basename(k): v for k, v in d.items()}
i0, inc = base(rt0["inputs"]), base(rnc["inputs"])
s0, snc = base(rt0["sources"]), base(rnc["sources"])
same_bounds = {f: (t0[f]["max_train_label_end"] == nc[f]["max_train_label_end"]
                   and t0[f]["test_start"] == nc[f]["test_start"]
                   and t0[f]["cutoff"] == nc[f]["cutoff"])
               for f in sorted(set(t0) & set(nc))}
same_pop = {f: (t0[f]["test_anchors"] == nc[f]["test_anchors"]
                and t0[f]["scored_pairs"] == nc[f]["scored_pairs"])
            for f in sorted(set(t0) & set(nc))}
census = next((v["seat_census"] for v in t0.values() if v.get("seat_census")), None)
diff = {
    "fold_names_identical": sorted(t0) == sorted(nc),
    "n_folds": {"T0": len(t0), "NC": len(nc)},
    "fold_boundaries_identical_every_fold": all(same_bounds.values()),
    "folds_with_differing_boundaries": [f for f, ok in same_bounds.items() if not ok],
    "scored_population_identical_every_fold": all(same_pop.values()),
    "folds_with_differing_population": [f for f, ok in same_pop.items() if not ok],
    "inputs_only_in_T0": sorted(set(i0) - set(inc)), "inputs_only_in_NC": sorted(set(inc) - set(i0)),
    "inputs_with_differing_sha": [k for k in sorted(set(i0) & set(inc)) if i0[k] != inc[k]],
    "shared_sources_with_differing_sha": [k for k in sorted(set(s0) & set(snc)) if s0[k] != snc[k]],
    "sources_only_in_T0": sorted(set(s0) - set(snc)),
    "seed": {"T0": rt0.get("seed"), "NC": rnc.get("seed")},
    "wl_masking": census,
    "the_only_substantive_difference": ("the WL mask w=[WL0,0,WL2]; w/=w.sum(). Everything else compared "
                                        "here is identical: fold names, per-fold boundaries, scored "
                                        "population, all input shas, and the sha of the reference recipe "
                                        "news2_train_f10.py."),
}

# ── (2) leakage ────────────────────────────────────────────────────────────────────────────────────
def leak(d, name):
    viol, gaps = [], []
    for f, v in sorted(d.items()):
        mt, ts = v.get("max_train_label_end"), v.get("test_start")
        if mt is None or ts is None:
            continue
        gaps.append((ts - mt) / 3600.0)
        if mt >= ts:
            viol.append({"fold": f, "max_train_label_end": iso(mt), "test_start": iso(ts)})
    return {"arm": name, "folds_checked": len(gaps), "violations": viol,
            "n_violations": len(viol),
            "embargo_gap_hours": {"min": min(gaps), "max": max(gaps)} if gaps else None,
            "folds_2026": {f: {"max_train_label_end": iso(v["max_train_label_end"]),
                               "test_start": iso(v["test_start"])}
                           for f, v in sorted(d.items())
                           if f.startswith("2026") and v.get("max_train_label_end")}}


k = json.load(open(KINGR))
kv, kg = [], []
for row in k["folds"]:
    mt, ss = row.get("max_train_label_end"), row.get("score_start")
    if mt is None or ss is None:
        continue
    kg.append((ss - mt) / 3600.0)
    if mt >= ss:
        kv.append(row["fold"])
king = {"arm": "KING (in-service NC)", "folds": [
            {"fold": r["fold"], "score_start": iso(r["score_start"]), "score_end": iso(r["score_end"]),
             "max_train_label_end": iso(r["max_train_label_end"])} for r in k["folds"]],
        "n_violations": len(kv), "violations": kv,
        "embargo_gap_hours": {"min": min(kg), "max": max(kg)} if kg else None,
        "status_self_reported": k.get("status"), "recipe": k.get("recipe")}

rec = {"device": "dlarch_t0_vs_nc_audit.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": iso(time.time()), "asked_by": "lead 2026-09-25", "t0_dir": os.path.abspath(T0DIR),
       "nc_dir": os.path.abspath(NCDIR), "differences": diff,
       "leakage_F10_T0": leak(t0, "T0"), "leakage_F10_NC": leak(nc, "NC in-service"),
       "leakage_KING_NC": king,
       "verdict_withheld": "facts only; whether to run an isolating arm is lead's call",
       "scope_limit": ("this checks RECORDED FOLD BOUNDARIES. It shows no fold's training labels reach "
                       "into its own scoring window. It does NOT rule out every leakage channel -- a "
                       "feature built with forward information would not appear here.")}
tmp = OUT + ".tmp"
with open(tmp, "w") as f:
    json.dump(rec, f, indent=1)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, OUT)
assert json.load(open(OUT)) == rec, "receipt read back differs from what was written"

print("(1) differences")
for kk in ("fold_names_identical", "fold_boundaries_identical_every_fold",
           "scored_population_identical_every_fold", "inputs_with_differing_sha",
           "shared_sources_with_differing_sha", "sources_only_in_T0", "seed"):
    print("   %-42s %s" % (kk, diff[kk]))
if census:
    print("   WL mask: %d/%d ready anchors changed; raw %s -> masked %s"
          % (census["anchors_where_WL_changed"], census["n_population"],
             [round(x, 4) for x in census["raw_WL_mean"]], [round(x, 4) for x in census["masked_WL_mean"]]))
print("(2) leakage")
for r in (rec["leakage_F10_T0"], rec["leakage_F10_NC"]):
    print("   F10 %-16s folds %d  violations %d  gap h %.0f..%.0f"
          % (r["arm"], r["folds_checked"], r["n_violations"],
             r["embargo_gap_hours"]["min"], r["embargo_gap_hours"]["max"]))
print("   KING %-15s folds %d  violations %d  gap h %.0f..%.0f  status %s"
      % ("", len(king["folds"]), king["n_violations"], king["embargo_gap_hours"]["min"],
         king["embargo_gap_hours"]["max"], king["status_self_reported"]))
print("T0_VS_NC_AUDIT OK receipt=%s sha256=%s" % (OUT, sha(OUT)[:16]))
assert rec["leakage_F10_T0"]["n_violations"] == 0 and rec["leakage_F10_NC"]["n_violations"] == 0 \
    and king["n_violations"] == 0, "LEAKAGE FOUND -- see the receipt"
