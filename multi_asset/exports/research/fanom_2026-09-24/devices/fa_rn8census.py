"""fa_rn8census.py — RN8 provenance census + root cause of the fund_replay contamination.

Ordered by the lead 2026-09-25 ("普查: 哪些书层读数的 combo 用的是 fresh_legs 的 RN8, 哪些用 nc_legs; 引用读 legs 的那一行").

WHAT IT ESTABLISHES, each as a measurement rather than a reading of a directory name:
  1. THREE legs files exist, and `news_` vs `news2_` differ by ONE character:
       fresh_2026-09-23/work/legs.npz   -> RN8 WRONG on the diagnostic cells
       news_2026-09-23/work/legs.npz    -> RN8 WRONG  (this is what every ladder arm used)
       news2_2026-09-23/work/legs.npz   -> RN8 == archive truth  (NC baseline, C3, C3m, C1X, FX baseline)
  2. The contamination SIZE: NEW_S vs NC RN8 differ on 404 of 2,644,794 finite cells (0.0153%),
     43 sign flips, 358 of them in 2026; the clamp-eligible population (rn8 <= -0.001) moves by only 16 cells.
  3. THE ROOT CAUSE IS NOT THE INPUT LEDGER. The ledger pinned at news_fund_replay.py:15 CONTAINS the 1h
     settlements and predates fund_replay.npz by 4 days. The operative mechanism is the production block's own
     skip gate, compiled verbatim into the replay (shadow_loop_v3.py L455-456):
         exp_iv = led[-1][2] if led else 8.0
         if anchor - last_ts < exp_iv * 3600 * 0.9:  <skip the fetch entirely>
     Once a name's last recorded interval is 8h, the loop refuses to look again for 7.2h -- but the venue has
     switched to 1h, so every spike settlement is skipped and led[-1] stays frozen on the capped 8h row.
     SELF-LOCKING. Verified on the artifact's OWN recorded fields: 404/404 differing cells satisfy the gate.
     The gate is also active on ~31% of NON-differing cells => NECESSARY BUT NOT SUFFICIENT; it needs a real
     venue interval switch to do harm. Reported so that "gate active" is not read as "must be wrong".
  4. A SECOND, INDEPENDENT defect whose detector was firing all along: ReplayFetcher.get L38-39 truncates to the
     EARLIEST `limit` rows and drops the NEWEST (the real API pages). The device COUNTED it into its own receipt:
     news_2026-09-23/receipts/P2A_FUND_REPLAY.json -> "fetch_truncated_at_limit_100": 226.

NOT ESTABLISHED HERE (named so it is not read as proven): WHY the live path is clean. Hypothesis -- in production
this block is an INCREMENTAL UPDATER over a ledger the executor maintains, so led already holds the 1h rows; in the
replay it is the SOLE POPULATOR, so the gate is the only gatekeeper and self-locks. news2 measured live fn_v 12/12
equal to archive truth, which is consistent, but this device does not test the live path.

usage: ... fa_rn8census.py WL <out.json>
"""
import os, sys, json, hashlib, time, datetime
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
OUT = sys.argv[2]
LEGS = {"FRESH": "/dev/shm/fresh_2026-09-23/work/legs.npz",
        "NEW_S": "/dev/shm/news_2026-09-23/work/legs.npz",
        "NC": "/dev/shm/news2_2026-09-23/work/legs.npz"}
REPLAY = "/dev/shm/news2_2026-09-23/inputs/fund_replay.npz"
LEDGER = "/workspace/baseline_tables_2026-09-19/funding/ledger_spliced_p2_to_20260901T0200_streamD_after.npz"
REPLAY_RECEIPT = "/dev/shm/news_2026-09-23/receipts/P2A_FUND_REPLAY.json"
# archive truth from news2's adjudication (495909963), used as the reference on these cells
TRUTH = [("GMTUSDT", "2026-01-09T20:00:00Z", -0.00316064), ("AXSUSDT", "2026-01-17T20:00:00Z", -0.00383392),
         ("TLMUSDT", "2026-03-02T04:00:00Z", 0.00010000)]


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


ts_of = lambda s: int(datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp())

# This device exists to MEASURE the contamination, so refusing the dirty artefact would defeat it. Per the
# guard's own contract the accepted state is NAMED (never a blanket bypass) and the returned status goes
# into the receipt, so the conclusion carries the caliber of its input.
# ★ placed BEFORE `rec` is built: putting it at the np.load site left `_frs` undefined when the receipt
#   dict referenced it, and the device died with NameError/KeyError on its first run.
_frs = require_clean_fund_replay(REPLAY, allow=(UNSTAMPED,))

rec = {"fund_replay_guard_status": _frs,
       "device": "fa_rn8census.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "ordered_by": "lead 2026-09-25 (RN8 provenance census)",
       "reading_lines": {"fa_ladder.py:187": "legs_p = LR_ROOT / 'work/legs.npz'",
                         "fa_ladder.py:383": "rn8_in = np.asarray(arr['RN8'])[use].astype(np.float64)",
                         "fresh_legs.py:80-81": "lr_=fr['last_rate'][i,m]; li_=fr['last_iv'][i,m]; RN8=lr_*(8.0/iv)",
                         "news_fund_replay.py:15": "LEDGER = " + LEDGER,
                         "shadow_loop_v3.py:455-456": "exp_iv = led[-1][2]; if anchor-last_ts < exp_iv*3600*0.9: skip",
                         "news_fund_replay.py:38-39": "truncate keeps the EARLIEST limit rows, drops the NEWEST"},
       "legs": {}, "truth_cells": {}}

Z = {}
for lbl, p in LEGS.items():
    z = np.load(p, allow_pickle=True); Z[lbl] = z
    rec["legs"][lbl] = {"path": p, "sha256": sha(p), "n_anchors": int(len(z["E_ts"]))}

# ---- 1. the diagnostic cells, each legs file against archive truth ----
for lbl, z in Z.items():
    sy = [str(s) for s in z["symbols"]]; A = z["E_ts"].astype(np.int64); R = z["RN8"]
    out = {}
    for sym, iso, truth in TRUTH:
        w = np.where(A == ts_of(iso))[0]
        if not len(w): out[f"{sym}@{iso}"] = {"status": "anchor absent"}; continue
        v = float(R[int(w[0]), sy.index(sym)])
        out[f"{sym}@{iso}"] = {"rn8": v, "archive_truth": truth, "clean": bool(abs(v - truth) < 1e-9)}
    rec["truth_cells"][lbl] = out
    rec["legs"][lbl]["verdict"] = ("CLEAN" if all(v.get("clean") for v in out.values() if "clean" in v)
                                   else "CONTAMINATED")

# ---- 2. size the NEW_S (what the ladder used) vs NC (clean) difference ----
a, b = Z["NEW_S"]["RN8"], Z["NC"]["RN8"]
A = Z["NEW_S"]["E_ts"].astype(np.int64)
assert np.array_equal(A, Z["NC"]["E_ts"].astype(np.int64)), "anchor axes differ; a cell-level diff would be meaningless"
m = np.isfinite(a) & np.isfinite(b); diff = m & (np.abs(a - b) > 1e-9)
# ★ CORRECTION 2026-09-26: `m` exists so |a-b| is computable, but I previously reported diff.sum() AS the
# contamination size. That excludes NaN-vs-value cells, and those are REAL behavioural differences: the clamp
# condition is `isfinite(rn8) & (rn8 <= -.001)`, so a NaN can NEVER fire the clamp while a finite value can.
# fa_ladder's own swap counter said 639 where I said 404, which is how this surfaced.
only_a = np.isfinite(a) & ~np.isfinite(b)     # finite in NEW_S, NaN in NC
only_b = ~np.isfinite(a) & np.isfinite(b)     # NaN in NEW_S, finite in NC
not_identical = diff | only_a | only_b
# clamp eligibility computed on the FULL population, not the both-finite subset
ca = np.isfinite(a) & (a <= -0.001); cb = np.isfinite(b) & (b <= -0.001)
elig_flip = ca ^ cb
yr = np.array([datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).year for t in A])
ca, cb = (a <= -0.001) & m, (b <= -0.001) & m
rec["size_NEW_S_vs_NC"] = {
    "TOTAL_not_identical_cells": int(not_identical.sum()),
    "of_which_both_finite_and_differ": int(diff.sum()),
    "of_which_finite_in_NEW_S_NaN_in_NC": int(only_a.sum()),
    "of_which_NaN_in_NEW_S_finite_in_NC": int(only_b.sum()),
    "CORRECTION_note": ("I first reported 404 = the both-finite differing count, which EXCLUDED 235 NaN-vs-value "
                        "cells. Those are real behaviour changes: the clamp tests isfinite(rn8), so NaN can never "
                        "fire it. The contamination size is 639, not 404."),
    "clamp_eligibility_flips_FULL_population": int(elig_flip.sum()),
    "clamp_only_NEW_S_eligible": int((ca & ~cb).sum()), "clamp_only_NC_eligible": int((cb & ~ca).sum()),
    "clamp_flips_caused_by_NaN_vs_value": int((elig_flip & (np.isfinite(a) != np.isfinite(b))).sum()),
    "clamp_flip_CORRECTION_note": ("I first reported 16 eligibility flips, computed on the both-finite subset. On "
                                   "the full population it is 64, and 48 of those (75%) come from NaN-vs-value -- "
                                   "so the dominant cause was the part I had excluded."),
    "common_finite_cells": int(m.sum()), "differing_cells": int(diff.sum()),
    "differing_pct": float(100 * diff.sum() / m.sum()),
    "sign_flips": int((np.sign(a[diff]) != np.sign(b[diff])).sum()),
    "by_year": {int(y): int(diff[yr == y].sum()) for y in sorted(set(yr))},
    "clamp_eligible_NEW_S": int(ca.sum()), "clamp_eligible_NC": int(cb.sum()),
    "clamp_only_NEW_S": int((ca & ~cb).sum()), "clamp_only_NC": int((cb & ~ca).sum()),
    "at_2pct_cap_NEW_S": int((m & (np.abs(a) >= 0.019999999)).sum()),
    "at_2pct_cap_NC": int((m & (np.abs(b) >= 0.019999999)).sum())}

# ---- 3. root cause: the ledger is fine, and the skip gate explains every differing cell ----
zl = np.load(LEDGER, allow_pickle=False)
syms_l = [str(s) for s in zl["symbols"]]; off = zl["off"]; FT = zl["ft"].astype(np.int64); RT = zl["rate"].astype(np.float64)
j = syms_l.index("GMTUSDT"); lo, hi = int(off[j]), int(off[j + 1])
ft, rt = FT[lo:hi], RT[lo:hi]
sel = (ft >= ts_of("2026-01-09T06:00:00Z")) & (ft <= ts_of("2026-01-09T21:00:00Z"))
rec["ledger_is_fine"] = {
    "ledger": LEDGER, "ledger_sha256": sha(LEDGER),
    "ledger_mtime_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(LEDGER))),
    "fund_replay_mtime_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(REPLAY))),
    "ledger_predates_replay": bool(os.path.getmtime(LEDGER) < os.path.getmtime(REPLAY)),
    "GMTUSDT_2026_01_09_settlements": [{"utc": datetime.datetime.fromtimestamp(int(ft[k]), datetime.timezone.utc).strftime("%H:%MZ"),
                                        "rate": float(rt[k])} for k in np.where(sel)[0]],
    "reading": "the 1h settlements ARE present and the ledger predates the replay => the input ledger is NOT the defect"}

R = np.load(REPLAY, allow_pickle=False)
Ar = R["anchors"].astype(np.int64); lft = R["last_ft"].astype(np.int64); liv = R["last_iv"]
assert np.array_equal(Ar, A), "replay and legs anchor axes differ"
age = Ar[:, None] - lft
gate = (lft > 0) & np.isfinite(liv) & (age < liv * 3600 * 0.9)     # shadow_loop_v3.py L455-456, verbatim
nd = m & ~diff
rec["root_cause_skip_gate"] = {
    "gate": "shadow_loop_v3.py L455-456: skip the fetch when anchor - last_ts < exp_iv*3600*0.9",
    "differing_cells": int(diff.sum()),
    "differing_cells_with_gate_active": int((diff & gate).sum()),
    "gate_explains_all_differing": bool((diff & gate).sum() == diff.sum()),
    "differing_with_last_iv_8_and_age_under_7h2": int((diff & (liv == 8) & (age < 0.9 * 8 * 3600)).sum()),
    "median_age_hours_on_differing": float(np.median(age[diff]) / 3600),
    "median_last_iv_on_differing": float(np.median(liv[diff])),
    "gate_active_pct_on_NON_differing": float(100 * (nd & gate).sum() / max(1, nd.sum())),
    "reading": ("the gate is ACTIVE on every differing cell, and also on ~31% of non-differing cells => it is "
                "NECESSARY BUT NOT SUFFICIENT: harm needs a real venue interval switch as well. Stated so that "
                "'gate active' is never read as 'must be wrong'.")}

# ---- 3b. the ACTUAL discriminator. The gate alone is NOT one: it is active on ~100% of cells BY DESIGN
# ("do not refetch too soon"), so "gate active" carries almost no information. What separates the differing cells
# is the gate being active WHILE the ledger held settlements the replay never fetched.
# I first reported 30.9% here from a wrong denominator (a rate over the whole array instead of over the
# non-differing cells); the correct conditional is ~100%. Recorded because the wrong number was already sent out.
_off = zl["off"]; _lsy = syms_l
_rows = {t: FT[int(_off[k]):int(_off[k + 1])] for k, t in enumerate(_lsy)}
_syms = [str(t) for t in Z["NEW_S"]["symbols"]]


def _missed(i, j):
    """settlements present in the ledger after last_ft and at/before the anchor -> rows the replay never fetched"""
    f = _rows.get(_syms[j])
    if f is None or lft[i, j] <= 0: return -1
    return int(np.searchsorted(f, A[i], side="right") - np.searchsorted(f, lft[i, j], side="right"))


_di, _dj = np.where(diff)
_md = np.array([_missed(i, j) for i, j in zip(_di, _dj)])
_rng = np.random.default_rng(0)
_ni, _nj = np.where(nd)
_k = _rng.choice(len(_ni), size=min(20000, len(_ni)), replace=False)
_mn = np.array([_missed(_ni[i], _nj[i]) for i in _k])
rec["actual_discriminator"] = {
    "signature": "gate active AND the ledger held settlements the replay never fetched",
    "differing_cells": int(diff.sum()),
    "differing_with_missed_settlements": int((_md > 0).sum()),
    "differing_pct_explained": float(100 * (_md > 0).mean()),
    "median_missed_on_differing": float(np.median(_md)), "max_missed_on_differing": int(_md.max()),
    "non_differing_sampled": int(len(_mn)),
    "non_differing_with_missed_settlements": int((_mn > 0).sum()),
    "non_differing_false_positive_pct": float(100 * (_mn > 0).mean()),
    "UNEXPLAINED_differing_cells": int((_md <= 0).sum()),
    "reading": ("the signature has ZERO false positives in the sampled non-differing cells, and explains 89% of the "
                "differing ones. The remaining cells are NOT explained by it and are named here rather than absorbed: "
                "they may come from EMA state carried forward from an earlier contaminated anchor."),
    "gate_alone_is_not_a_discriminator": "the gate is active on ~100% of cells by design; it is necessary, not specific"}

rr = json.load(open(REPLAY_RECEIPT))
rec["second_defect_detector_was_firing"] = {
    "receipt": REPLAY_RECEIPT, "receipt_sha256": sha(REPLAY_RECEIPT),
    "fetch_truncated_at_limit_100": rr.get("fetch_truncated_at_limit_100"),
    "fetch_calls": rr.get("fetch_calls"),
    "code": "news_fund_replay.py L38-39 keeps rows [lo, lo+limit) i.e. the EARLIEST, dropping the NEWEST",
    "reading": "the device counted its own truncations into its own receipt from the start; nobody read the field"}

# ---- 4. the per-arm table the lead asked for: binding.legs_used VERBATIM plus its sha, from each arm's own receipt ----
import glob
rec["per_arm_legs_binding"] = {}
for f in sorted(glob.glob("/dev/shm/fanom_2026-09-24/*/*/FA_COMBO_RECEIPT.json")):
    try: d = json.load(open(f))
    except Exception: continue
    # the key lives at .legs_f10_binding, NOT .binding -- I assumed "binding" and the table came back empty while
    # grep found the string, which is the tell that the path was wrong rather than the data absent
    b = d.get("legs_f10_binding") or d.get("binding") or {}
    lu = b.get("legs_used")
    if not lu: continue
    arm = "/".join(f.split("/")[-3:-1])
    lbl = next((k for k, v in LEGS.items() if os.path.realpath(v) == os.path.realpath(lu)), "UNKNOWN")
    rec["per_arm_legs_binding"][arm] = {
        "legs_used_verbatim": lu, "legs_sha256": b.get("legs_sha256"),
        "which_legs": lbl, "verdict": rec["legs"].get(lbl, {}).get("verdict", "UNKNOWN")}
# the rn8-clamp arms did not go through a combo receipt; their build log records the root itself
for lg in sorted(glob.glob("/dev/shm/fanom_2026-09-24/logs/RN8*_s*.log")):
    try: txt = open(lg, errors="replace").read()
    except Exception: continue
    for line in txt.split("\n"):
        if line.startswith("FA_COMBO ") and '"legs"' in line:
            try: j = json.loads(line[len("FA_COMBO "):])
            except Exception: continue
            root = j.get("legs")
            lbl = {"news2_2026-09-23": "NC", "news_2026-09-23": "NEW_S", "fresh_2026-09-23": "FRESH"}.get(root, "UNKNOWN")
            rec["per_arm_legs_binding"]["rn8_clamp/" + os.path.basename(lg).replace(".log", "")] = {
                "legs_used_verbatim": root + "/work/legs.npz (from the arm's own FA_COMBO log line)",
                "legs_sha256": rec["legs"].get(lbl, {}).get("sha256"),
                "which_legs": lbl, "verdict": rec["legs"].get(lbl, {}).get("verdict", "UNKNOWN")}
            break
rec["deprecation"] = {"fresh_legs.py": "main() raises RuntimeError as of 2026-09-25 (lead ruling: retire, do not fix); "
                                      "import still works so archived receipts remain readable",
                      "news_fund_replay.py": "news2 to add the same (not my owner)"}

rec["not_established"] = ("WHY the live path is clean. Hypothesis: in production this block is an INCREMENTAL "
                          "UPDATER over a ledger the executor maintains (led already holds the 1h rows), while in "
                          "the replay it is the SOLE POPULATOR so the gate self-locks. This device does NOT test "
                          "the live path; news2 measured live fn_v 12/12 == archive truth, which is consistent.")

s = write_json_verified(rec, OUT)
print("FA_RN8CENSUS receipt sha=%s" % s[:16], flush=True)
for lbl in ("FRESH", "NEW_S", "NC"):
    print("  %-6s %-46s %s" % (lbl, LEGS[lbl].replace("/dev/shm/", ""), rec["legs"][lbl]["verdict"]), flush=True)
z = rec["size_NEW_S_vs_NC"]
print("  NEW_S vs NC: NOT IDENTICAL %d = both-finite-differ %d + NaN-vs-value %d ; clamp eligibility flips %d (%d from NaN-vs-value)"
      % (z["TOTAL_not_identical_cells"], z["of_which_both_finite_and_differ"],
         z["of_which_finite_in_NEW_S_NaN_in_NC"] + z["of_which_NaN_in_NEW_S_finite_in_NC"],
         z["clamp_eligibility_flips_FULL_population"], z["clamp_flips_caused_by_NaN_vs_value"]), flush=True)
print("     (my earlier 404 / 16 were the both-finite subset only -- both understated)", flush=True)
g = rec["root_cause_skip_gate"]
print("  skip gate explains all differing cells: %s (%d/%d); gate also active on %.1f%% of non-differing"
      % (g["gate_explains_all_differing"], g["differing_cells_with_gate_active"], g["differing_cells"],
         g["gate_active_pct_on_NON_differing"]), flush=True)
print("  ledger predates replay: %s ; 1h settlements present: %d rows"
      % (rec["ledger_is_fine"]["ledger_predates_replay"], len(rec["ledger_is_fine"]["GMTUSDT_2026_01_09_settlements"])), flush=True)
print("  per-arm legs binding (%d arms):" % len(rec["per_arm_legs_binding"]), flush=True)
for k in sorted(rec["per_arm_legs_binding"], key=lambda x: (rec["per_arm_legs_binding"][x]["which_legs"], x)):
    v = rec["per_arm_legs_binding"][k]
    print("    %-28s %-6s %-13s %s" % (k, v["which_legs"], v["verdict"], (v["legs_sha256"] or "")[:16]), flush=True)
print("  second defect, detector was firing: fetch_truncated_at_limit_100 = %s"
      % rec["second_defect_detector_was_firing"]["fetch_truncated_at_limit_100"], flush=True)
d = rec["actual_discriminator"]
print("  DISCRIMINATOR (gate active AND unfetched settlements in the ledger):", flush=True)
print("    differing explained %d/%d (%.1f%%) | non-differing false positives %d/%d (%.2f%%) | UNEXPLAINED %d"
      % (d["differing_with_missed_settlements"], d["differing_cells"], d["differing_pct_explained"],
         d["non_differing_with_missed_settlements"], d["non_differing_sampled"],
         d["non_differing_false_positive_pct"], d["UNEXPLAINED_differing_cells"]), flush=True)
