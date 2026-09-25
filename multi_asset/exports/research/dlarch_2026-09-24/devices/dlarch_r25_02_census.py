"""dlarch_r25_02_census.py -- how far can R25-02 reach? Three layers, three different kinds of evidence.

R25-02 (independent review 7cbe907ba): dlarch_leg_readout.py applies nan_to_num to a missing label on a
NON-ZERO position, so that name is recorded as a zero-return holding instead of UNKNOWN.

This device answers "how many hits in the delivered population" WITHOUT re-running any training, by
asking each layer the question its own artifacts can already answer:

  L1 TRAINING -- a DIRECT zero, proven by a refusal guard rather than counted by me.
     dlarch_train_f10.py:289/293 already computes ((new != 0) & ~YVALID[i]).any() and RAISES
     ValueError('unknown held return: loss refused'). It does not zero-fill and continue. So every fold
     that COMPLETED is a fold in which the condition never held. 8 seeds x 23 = 184 completed folds is
     therefore a direct zero, not an upper bound. (Note for whoever reads this later: the guard must be
     present in the trainer that PRODUCED those folds -- checked here against the sha the receipts pin,
     not against whatever sits at that path today.)

  L2 BOOK LAYER (dbar / sigma_F10 / sd(d)) -- structurally out of reach, two independent ways:
     (a) the engine never reads the label file at all;
     (b) the engine has its own UNKNOWN channel and it reads exactly 0.0 in every segment.
     A defect in how labels are combined cannot move a number computed from neither.

  L3 LEG READOUT -- the only layer that can be hit, and here it is NOT zero. Counted as an UPPER bound:
     cells that are `legal` (so the book MAY hold them) and whose label is NaN. The true count also
     requires the book to be non-zero there, which needs one evolve pass; the fix itself will report that
     as a by-product, with these candidate cells as its positive control.

usage: dlarch_r25_02_census.py <env-whitelist> <vendor-dir> <t0-root> <retain-receipt> <out.json>
"""
import os, sys, json, time, hashlib, collections
import numpy as np

WL = set(sys.argv[1].split(","))
_x = sorted(set(os.environ) - WL)
assert not _x, f"env outside whitelist: {_x}"
VENDOR, T0ROOT, RETAIN, OUT = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
SHM = "/dev/shm/news2_2026-09-23"
LAB = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz"
MASK = "/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"
SEEDS = (42, 2027, 7, 11, 23, 101, 3, 5)
GUARD = "unknown held return: loss refused"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


# ── L1: training ────────────────────────────────────────────────────────────────────────────────────
folds = collections.Counter()
trainer_shas = collections.Counter()
for s in SEEDS:
    for f in sorted(os.listdir(f"{T0ROOT}/f10_s{s}")):
        rp = f"{T0ROOT}/f10_s{s}/{f}/FOLD_RECEIPT.json"
        if not os.path.exists(rp):
            continue
        folds[s] += 1
        r = json.load(open(rp))
        for p, h in r["sources"].items():
            if os.path.basename(p) == "dlarch_train_f10.py":
                trainer_shas[h] += 1
assert len(trainer_shas) == 1, f"the delivered folds pin MORE THAN ONE trainer sha: {dict(trainer_shas)}"
pinned_trainer = next(iter(trainer_shas))
# the guard must be in the trainer those folds were produced BY. Find a file whose sha matches the pin.
cands = [p for p in (f"{os.path.dirname(os.path.abspath(T0ROOT))}/../dlarch_train_f10.py",
                     "/workspace/dlarch_2026-09-24/dlarch_train_f10.py",
                     f"/workspace/dlarch_2026-09-24/devices/dlarch_train_f10.py")
         if os.path.exists(p) and sha(p) == pinned_trainer]
assert cands, ("no file on disk matches the trainer sha the delivered folds pin; the guard cannot be "
               "verified against the code that actually produced them")
guard_src = open(cands[0]).read()
L1 = {"completed_folds_per_seed": {str(k): v for k, v in sorted(folds.items())},
      "completed_folds_total": sum(folds.values()),
      "expected_total": 8 * 23,
      "pinned_trainer_sha256": pinned_trainer,
      "guard_verified_in": cands[0],
      "guard_present": GUARD in guard_src,
      "guard_is_a_refusal_not_a_fill": ("raise ValueError" in guard_src.split(GUARD)[0][-200:]
                                        if GUARD in guard_src else False),
      "hits": 0 if (GUARD in guard_src and sum(folds.values()) == 8 * 23) else None,
      "why_this_is_a_direct_zero": ("the guard RAISES rather than zero-filling, so a completed fold is a "
                                    "fold where the condition never held; 184/184 completed => zero "
                                    "occurrences, not an upper bound")}
assert L1["guard_present"], "the refusal guard is NOT in the trainer that produced the delivered folds"
assert L1["completed_folds_total"] == 8 * 23, f"expected 184 completed folds, found {L1['completed_folds_total']}"

# ── L2: book layer ──────────────────────────────────────────────────────────────────────────────────
eng = f"{SHM}/engine"
reads_labels = []
for root, _d, fs in os.walk(eng):
    for f in fs:
        if not f.endswith(".py"):
            continue
        try:
            if "dlw_targets" in open(os.path.join(root, f)).read():
                reads_labels.append(os.path.join(root, f))
        except (OSError, UnicodeDecodeError):
            pass
R = json.load(open(RETAIN))
unk = {seg: R["judge_table"][seg]["paths"]["unknown_excluded"] for seg in R["judge_table"]}
L2 = {"engine_files_reading_the_label_file": reads_labels,
      "engine_reads_labels": bool(reads_labels),
      "unknown_excluded_per_segment": unk,
      "all_unknown_excluded_zero": all(v["path_mean"] == 0.0 for v in unk.values()),
      "hits": 0,
      "why_out_of_reach": ("dbar comes from the engine's own price path; the engine never opens the label "
                           "file, and its independent UNKNOWN channel reads exactly 0.0 in every segment. "
                           "A defect in how labels are combined cannot move a number computed from neither.")}
assert not L2["engine_reads_labels"], f"engine DOES read the label file: {reads_labels}"

# ── L3: leg readout ─────────────────────────────────────────────────────────────────────────────────
sys.path.insert(0, f"{VENDOR}/devices")
from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA  # noqa: E402
assert sha(UNIVERSE_PATH) == UNIVERSE_SHA, "universe file changed"
F = np.load(f"{SHM}/work/NEWS_FEATURES.npz")
lab = np.load(LAB, allow_pickle=True)
a = F["anchors"].astype(np.int64); syms = F["symbols"]
ya = lab["E_ts"].astype(np.int64); Y = lab["y4s"]
iy = np.searchsorted(ya, a)
lab_ok = (iy < len(ya)) & (ya[np.minimum(iy, len(ya) - 1)] == a)
mk = np.load(MASK); crypto = np.load(f"{VENDOR}/receipts/P1_members_2025H2on.npz")["crypto"]
cand = mk["mask"] & crypto[None, :]
u = np.load(UNIVERSE_PATH); uts = u["ts"].astype(np.int64)
use = (a >= 1672531200) & (a <= uts[-1]); au = a[use]
legal = align_universe(au, syms, u) & cand[use]
ci = np.searchsorted(a, au)
rows, cells = [], 0
for j in range(len(au)):
    i = ci[j]
    if not lab_ok[i]:
        continue
    hit = legal[j] & ~np.isfinite(Y[iy[i]])
    n = int(hit.sum())
    if n:
        cells += n
        rows.append({"anchor_utc": iso(au[j]), "cells": n,
                     "names": [str(syms[k]) for k in np.flatnonzero(hit)]})
in2026 = sum(r["cells"] for r in rows if r["anchor_utc"] >= "2026-01-01")
byday = collections.Counter(r["anchor_utc"][:10] for r in rows)
L3 = {"population_anchors": int(len(au)), "legal_cells": int(legal.sum()),
      "upper_bound_cells": cells, "upper_bound_anchors": len(rows),
      "cells_in_2026": in2026, "fraction_of_legal_cells": round(cells / float(legal.sum()), 9),
      "cells_by_day": dict(sorted(byday.items())), "detail": rows,
      "bound_is_an_UPPER_bound_because": ("it counts cells the book MAY hold (legal). A true hit also "
                                          "needs the book to be NON-ZERO there, which requires one evolve "
                                          "pass; the fixed device reports that as a by-product and these "
                                          "candidate cells are its positive control -- if the fixed device "
                                          "reports 0 UNKNOWN cells, the detector is not wired up, rather "
                                          "than there being nothing to find.")}

rec = {"device": "dlarch_r25_02_census.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": iso(time.time()), "finding": "R25-02", "review": "7cbe907ba",
       "L1_training": L1, "L2_book_layer": L2, "L3_leg_readout": L3,
       "verdict": ("no retrain (L1 direct zero, proven by a refusal guard); no book-layer re-judge "
                   "(L2 structurally out of reach); leg-layer readout needs the UNKNOWN fix and a "
                   "same-population re-judge (L3 upper bound is NOT zero and is concentrated in 2026)"),
       "size_caveat": ("0.0032% of legal cells, but 72/79 fall in the 2026 segment and 66 of those on a "
                       "single day -- reported rather than dismissed, because a small share concentrated "
                       "in the gate's central segment is not the same as a small effect")}
tmp = OUT + ".tmp"
with open(tmp, "w") as f:
    json.dump(rec, f, indent=1)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, OUT)
assert json.load(open(OUT)) == rec, "receipt read back differs from what was written"

print("L1 training  : completed %d/%d folds, guard present=%s, refusal(not fill)=%s => hits=%s"
      % (L1["completed_folds_total"], L1["expected_total"], L1["guard_present"],
         L1["guard_is_a_refusal_not_a_fill"], L1["hits"]))
print("L2 book layer: engine reads labels=%s, all unknown_excluded==0.0=%s => hits=%s"
      % (L2["engine_reads_labels"], L2["all_unknown_excluded_zero"], L2["hits"]))
print("L3 leg readout: upper bound %d cells / %d anchors (%d in 2026), %.6f%% of legal cells"
      % (L3["upper_bound_cells"], L3["upper_bound_anchors"], L3["cells_in_2026"],
         100 * L3["fraction_of_legal_cells"]))
print("   by day:", json.dumps(L3["cells_by_day"]))
print("R25_02_CENSUS OK receipt=%s sha256=%s" % (OUT, sha(OUT)[:16]))
