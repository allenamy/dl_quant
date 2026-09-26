"""fa_rn8stall.py — classify MY 404 contaminated RN8 cells with news2's four-class as-of decomposition.

WHY THIS EXISTS: my earlier signature ("gate active AND the ledger held settlements never fetched") explained
360/404 and left 44 UNEXPLAINED. news2 ran a DIFFERENT instrument on a DIFFERENT population (their 5,613
panel-vs-replay rate cells) and got STALE_ASOF 5,613/5,613 = 100.0% with ZERO residual, so they suspect my 44 are a
second-order effect of the same mechanism (EMA state carried from an earlier poisoned anchor) rather than a third
mechanism. Their four classes need only `last_ft` and a truth as-of, so they can be applied to my population.

★ news2 deliberately did NOT run my signature on their cells, and they were right: my 404 are RN8 differences
  between two LEGS files, theirs are rate differences between panel and replay. Different populations -- running
  one population's signature on another compares different quantities. For the same reason I do not re-implement
  their verdicts; I recompute the CLASSIFICATION (a definition, not a caliber) and CONTROL it against their
  published per-cell CSV on the cells the two populations share.

CLASSES (news2, D10_FX_STALL_DECOMPOSITION.json):
  STALE_ASOF            replay's as-of is EARLIER than the truth as-of   -> the gate never advanced
  SAME_ASOF_DIFF_VALUE  same as-of second, different value               -> caliber/state, NOT a stuck fetch
  REPLAY_AHEAD          replay's as-of is LATER than truth               -> causality violation
  NO_REPLAY_ASOF        replay has no as-of at all
  The SAME_ASOF_DIFF_VALUE class is not hypothetical: news2 caught exactly one (ONEUSDT 2026-09-22, same as-of
  second, same rate, iv 2.0 vs the ledger's 4.0). A detector that has fired elsewhere makes its silence here mean
  something.

usage: ... fa_rn8stall.py WL <out.json> <p2_ledger.npz> <news2_cells.csv>
"""
import os, sys, json, hashlib, time, datetime, csv
import numpy as np

# ---- D10 stage 2 §5: consumer-side gate on fund_replay.npz (news2 fund_replay_guard.py, lead-mandated) ----
# A gate on the PRODUCER is not a gate on the CONSUMERS: the defect reaches conclusions through the consumers.
import hashlib as _hl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_GSHA = "9113d28a49b858df83c916c295ce0bc8286950b1d28b767dd07b61c9047ced25"
_gp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fund_replay_guard.py")
with open(_gp, "rb") as _f:
    assert _hl.sha256(_f.read()).hexdigest() == _GSHA, "fund_replay_guard.py drifted from the pinned sha"
from fund_replay_guard import require_clean_fund_replay, fund_replay_status, UNSTAMPED

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT, LEDGER, N2CSV = sys.argv[2], sys.argv[3], sys.argv[4]
NEWS = "/dev/shm/news_2026-09-23/work/legs.npz"
NC = "/dev/shm/news2_2026-09-23/work/legs.npz"
REPLAY = "/dev/shm/news2_2026-09-23/inputs/fund_replay.npz"
iso = lambda t: datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
ts_of = lambda s: int(datetime.datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=datetime.timezone.utc).timestamp())


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def write_json_verified(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=float); f.flush(); os.fsync(f.fileno())
    with open(tmp) as f:
        assert json.load(f) == json.loads(json.dumps(obj, default=float)), "receipt did not read back equal"
    s = sha(tmp); os.replace(tmp, path); return s


NS = np.load(NEWS, allow_pickle=True); NCz = np.load(NC, allow_pickle=True); R = np.load(REPLAY, allow_pickle=False)
L = np.load(LEDGER, allow_pickle=False)
A = NS["E_ts"].astype(np.int64); sy = [str(s) for s in NS["symbols"]]
a, b = NS["RN8"], NCz["RN8"]
m = np.isfinite(a) & np.isfinite(b); diff = m & (np.abs(a - b) > 1e-9)
lft = R["last_ft"].astype(np.int64)
assert np.array_equal(R["anchors"].astype(np.int64), A), "replay and legs axes differ"

lsy = [str(s) for s in L["symbols"]]; off = L["off"].astype(np.int64); FT = L["ft"].astype(np.int64)
rows_l = {s: FT[int(off[k]):int(off[k + 1])] for k, s in enumerate(lsy)}


def truth_asof(sym, anchor):
    """the last settlement in the P2 ledger at or before the anchor -- the same as-of rule the producer uses"""
    f = rows_l.get(sym)
    if f is None or not len(f): return None
    i = int(np.searchsorted(f, anchor, side="right")) - 1
    return int(f[i]) if i >= 0 else None


def classify(sym, anchor, replay_ft):
    t = truth_asof(sym, anchor)
    if replay_ft is None or replay_ft <= 0: return "NO_REPLAY_ASOF", None
    if t is None: return "NO_TRUTH_ASOF", None
    if replay_ft < t: return "STALE_ASOF", t - replay_ft
    if replay_ft > t: return "REPLAY_AHEAD", replay_ft - t
    return "SAME_ASOF_DIFF_VALUE", 0



# This device exists to MEASURE the contamination, so refusing the dirty artefact would defeat it. Per the
# guard's own contract the accepted state is NAMED (never a blanket bypass) and the returned status goes
# into the receipt, so the conclusion carries the caliber of its input.
# ★ placed BEFORE `rec` is built: putting it at the np.load site left `_frs` undefined when the receipt
#   dict referenced it, and the device died with NameError/KeyError on its first run.
_frs = require_clean_fund_replay(REPLAY, allow=(UNSTAMPED,))

rec = {"fund_replay_guard_status": _frs,
       "device": "fa_rn8stall.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "borrowed_from": "news2 D10_FX_STALL_DECOMPOSITION.json (four-class as-of decomposition)",
       "population": "MY 404 cells = NEW_S legs RN8 != NC legs RN8 (NOT news2's 5,613 panel-vs-replay rate cells)",
       "inputs": {"news_legs": sha(NEWS), "nc_legs": sha(NC), "replay": sha(REPLAY),
                  "p2_ledger": {"path": LEDGER, "sha256": sha(LEDGER)},
                  "news2_cells_csv": {"path": N2CSV, "sha256": sha(N2CSV)}}}

# ---- POSITIVE CONTROL: reproduce news2's own as-of on the cells our two populations share ----
n2 = []
with open(N2CSV) as f:
    for line in f:
        if not line.startswith("#"): n2.append(line)
n2rows = list(csv.DictReader(n2))
n2map = {(r["symbol"], r["anchor_utc"]): r for r in n2rows}
di, dj = np.where(diff)
mine = [(sy[j], iso(A[i]), int(i), int(j)) for i, j in zip(di, dj)]
shared = [x for x in mine if (x[0], x[1]) in n2map]
agree = 0; disagree = []
for sym, anc, i, j in shared:
    mine_t = truth_asof(sym, int(A[i]))
    theirs_t = ts_of(n2map[(sym, anc)]["asof_event_utc"])
    if mine_t == theirs_t: agree += 1
    elif len(disagree) < 8:
        disagree.append({"symbol": sym, "anchor": anc, "my_truth_asof": iso(mine_t) if mine_t else None,
                         "news2_asof_event_utc": n2map[(sym, anc)]["asof_event_utc"]})
rec["positive_control_vs_news2"] = {
    "my_cells": len(mine), "shared_with_news2_population": len(shared),
    "my_truth_asof_equals_theirs": agree, "disagreements": disagree,
    "reading": ("my as-of computation is checked against news2's PUBLISHED per-cell as-of on the shared cells "
                "BEFORE I use it on the cells only I have. If the populations barely overlap the control is weak "
                "and that is stated rather than hidden.")}
assert not disagree, f"as-of disagrees with news2 on {len(disagree)} shared cells -- refusing to extend"

# ---- classify all of my 404 ----
counts = {}; behind = []; examples = {}
per = []
for sym, anc, i, j in mine:
    cls, bh = classify(sym, int(A[i]), int(lft[i, j]))
    counts[cls] = counts.get(cls, 0) + 1
    if bh: behind.append(bh)
    examples.setdefault(cls, [])
    if len(examples[cls]) < 4:
        examples[cls].append({"symbol": sym, "anchor": anc,
                              "replay_asof": iso(lft[i, j]) if lft[i, j] > 0 else None,
                              "truth_asof": iso(truth_asof(sym, int(A[i]))) if truth_asof(sym, int(A[i])) else None,
                              "behind_s": bh, "news_rn8": float(a[i, j]), "nc_rn8": float(b[i, j])})
    per.append({"symbol": sym, "anchor": anc, "class": cls, "behind_s": bh})
rec["counts"] = counts
rec["cells"] = int(len(mine))
rec["closure"] = {"sum_of_classes": int(sum(counts.values())), "equals_cells": bool(sum(counts.values()) == len(mine))}
assert rec["closure"]["equals_cells"], "class counts do not close on the cell count"
if behind:
    bh = np.array(behind, np.int64)
    rec["behind_s"] = {"median": int(np.median(bh)), "min": int(bh.min()), "max": int(bh.max()),
                       "median_hours": float(np.median(bh) / 3600), "median_days": float(np.median(bh) / 86400)}
rec["examples"] = examples
rec["shape_reading"] = ("news2's point: a distribution that piles up at ONE interval means 'one anchor late'; a "
                        "median of days with a multi-hundred-day tail means SELF-LOCKING (the predicted-interval "
                        "gate stops advancing once a name is recorded at 8h). Compare the spread below against that.")
s = write_json_verified(rec, OUT)
print("FA_RN8STALL receipt sha=%s  my cells=%d" % (s[:16], rec["cells"]), flush=True)
pc = rec["positive_control_vs_news2"]
print("  positive control: shared with news2 %d/%d ; my truth as-of == theirs on %d"
      % (pc["shared_with_news2_population"], pc["my_cells"], pc["my_truth_asof_equals_theirs"]), flush=True)
for k, v in sorted(counts.items(), key=lambda x: -x[1]):
    print("  %-22s %5d (%.1f%%)" % (k, v, 100.0 * v / rec["cells"]), flush=True)
if "behind_s" in rec:
    print("  behind: median %d s = %.1f h = %.1f d | min %d | max %d"
          % (rec["behind_s"]["median"], rec["behind_s"]["median_hours"], rec["behind_s"]["median_days"],
             rec["behind_s"]["min"], rec["behind_s"]["max"]), flush=True)
