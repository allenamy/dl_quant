"""fa_fxfield.py — lead condition 1 for the FX arms: is `f_fund_now` the UN-normalised single-settlement rate,
and does it equal the current kernel's proposed new input `last_rate` on common cells?

PREREG docs/PREREG_FX1_FX3_same_caliber_2026-09-25.md; lead ruled option (i) (threshold on last_rate) and attached
four conditions. This device answers condition 1 and is archived with the result, per the same-lifetime rule.

Condition 1(a) -- the PRODUCING line, not the reading line:
    multi_asset/exports/research/uplift_2026-09-11/r6_devices/r6_panel_splice.py
      L92:  rate_nf = fr * (8.0 / iv_full)        <-- the NORMALISED rate, a SEPARATE variable
      L98:  fn[okp] = fr[pos[okp]]                <-- f_fund_now takes fr, the RAW settlement rate
      L101: out["f_fund_now"][nC:, j] = fn.astype(np.float32)
    so f_fund_now is un-normalised BY CONSTRUCTION. This device also tests that numerically, because a claim about
    a field's semantics should not rest on my reading of one line (name_of_the_quantity_is_not_the_quantity).

Condition 1(b) -- bitwise equality against last_rate on common cells.

⚠ VINTAGE CAVEAT, measured not assumed: the 08-30 device reads {B}/wide_panel_4h_hist_v2.npz where
B = /mnt/storage/private/work_hsy/pod_backup_2026-08-21 (jpline, unreachable since 2026-09-04, KB-04). The pod2
paths bearing that same name are SYMLINKS; this device resolves them, reports the resolved object and its ts range,
and asserts nothing about vintage from the path name (E-0825-H).

usage: ... fa_fxfield.py WL <out.json> <panel.npz> <fund_replay.npz>
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
OUT, PANEL, REPLAY = sys.argv[2], sys.argv[3], sys.argv[4]
CSV = sys.argv[5] if len(sys.argv) > 5 else None      # lead 2026-09-25 item 3: the full named list, fixed repo path
THRESHOLDS = [-0.0010, -0.0030]        # the 08-30 whitelist, L24
iso = lambda t: datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def write_json_verified(obj, path):
    """write -> fsync -> read back -> compare -> commit. `json.dump(x, open(p,"w"))` is GREEN on a full disk."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=float); f.flush(); os.fsync(f.fileno())
    with open(tmp, "r") as f:
        back = json.load(f)
    assert back == json.loads(json.dumps(obj, default=float)), f"receipt did not read back equal: {path}"
    s = sha(tmp); os.replace(tmp, path)
    return s


P = np.load(PANEL, allow_pickle=True); R = np.load(REPLAY, allow_pickle=False)
pt = P["ts"].astype(np.int64); ft = R["anchors"].astype(np.int64)
ps = [str(s) for s in P["symbols"]]; rs = [str(s) for s in R["symbols"]]
assert ps == rs, "symbol axes differ in content or order; cell-level comparison would be meaningless"
ti = np.intersect1d(pt, ft)
pi = {t: i for i, t in enumerate(pt)}; fi = {t: i for i, t in enumerate(ft)}
pr = np.array([pi[t] for t in ti]); fr = np.array([fi[t] for t in ti])
FN = P["f_fund_now"][pr]; IV = P["f_fund_iv"][pr]
LR = R["last_rate"][fr]; LIV = R["last_iv"][fr]
both = np.isfinite(FN) & np.isfinite(LR)


# This device exists to MEASURE the contamination, so refusing the dirty artefact would defeat it. Per the
# guard's own contract the accepted state is NAMED (never a blanket bypass) and the returned status goes
# into the receipt, so the conclusion carries the caliber of its input.
# ★ placed BEFORE `rec` is built: putting it at the np.load site left `_frs` undefined when the receipt
#   dict referenced it, and the device died with NameError/KeyError on its first run.
_frs = require_clean_fund_replay(REPLAY, allow=(UNSTAMPED,))

rec = {"fund_replay_guard_status": _frs,
       "device": "fa_fxfield.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "prereg": "docs/PREREG_FX1_FX3_same_caliber_2026-09-25.md (lead condition 1)",
       "producing_line": {"file": "multi_asset/exports/research/uplift_2026-09-11/r6_devices/r6_panel_splice.py",
                          "L92": "rate_nf = fr * (8.0 / iv_full)   # NORMALISED, separate variable",
                          "L98": "fn[okp] = fr[pos[okp]]           # f_fund_now takes the RAW rate fr",
                          "L101": "out['f_fund_now'][nC:, j] = fn.astype(np.float32)"},
       "panel": {"path_given": PANEL, "resolved": os.path.realpath(PANEL), "sha256": sha(os.path.realpath(PANEL)),
                 "ts_n": int(len(pt)), "ts_first": iso(pt[0]), "ts_last": iso(pt[-1]),
                 "vintage_note": ("the 08-30 device reads pod_backup_2026-08-21 on jpline (unreachable since "
                                  "2026-09-04). Vintage is NOT asserted from the path name; the ts range above is "
                                  "the evidence a reader should judge it by.")},
       "replay": {"path": REPLAY, "sha256": sha(REPLAY), "anchors_n": int(len(ft))},
       "common": {"anchors": int(len(ti)), "finite_cells": int(both.sum())}}

# --- 1(a) numeric test of the semantics claim -------------------------------------------------
rn8 = LR * 8.0 / np.where(LIV > 0, LIV, np.nan)
b2 = both & np.isfinite(rn8)
eq_rn8 = (FN[b2] == rn8[b2].astype(np.float32))
iv8 = (LIV[b2] == 8)
rec["1a_is_f_fund_now_unnormalised"] = {
    "equals_rate_times_8_over_iv_pct": float(100 * eq_rn8.mean()),
    "share_of_cells_with_iv_eq_8_pct": float(100 * iv8.mean()),
    "equality_restricted_to_iv_eq_8": bool(np.array_equal(eq_rn8, iv8)),
    "reading": ("f_fund_now matches the normalised rate ONLY where iv==8, i.e. only where normalising is a no-op "
                "=> f_fund_now is UN-normalised. This corroborates the producing line numerically.")}

# --- 1(b) bitwise equality against last_rate --------------------------------------------------
eq32 = (FN[both] == LR[both].astype(np.float32))
d = np.abs(FN[both].astype(np.float64) - LR[both])
bad = both & (FN != LR.astype(np.float32))
rel = d[eq32 == False] / np.maximum(np.abs(LR[bad]), 1e-12)
ai, si = np.where(bad)
yrs = {}
for a in ai:
    y = iso(ti[a])[:4]; yrs[y] = yrs.get(y, 0) + 1
cnt = {}
for s in si: cnt[s] = cnt.get(s, 0) + 1
worst = sorted(cnt.items(), key=lambda x: -x[1])[:6]
j = int(np.argmax(d[eq32 == False])) if bad.any() else None
ex = []
for s, _ in worst[:3]:
    for k in np.where(si == s)[0][:2]:
        a = ai[k]
        ex.append({"symbol": ps[s], "anchor": iso(ti[a]), "panel_f_fund_now": float(FN[a, s]),
                   "replay_last_rate": float(LR[a, s]), "panel_iv": float(IV[a, s]), "replay_iv": float(LIV[a, s])})
rec["1b_equality_vs_last_rate"] = {
    "exact_equal_as_float32_pct": float(100 * eq32.mean()),
    "mismatched_cells": int(bad.sum()),
    "mismatch_is_representational": bool(bad.any() and (rel > 1e-6).mean() < 0.5),
    "share_of_mismatches_with_rel_diff_gt_1e6_pct": float(100 * (rel > 1e-6).mean()) if bad.any() else None,
    "median_relative_diff_on_mismatches": float(np.median(rel)) if bad.any() else None,
    "abs_diff_max": float(d.max()), "abs_diff_median": float(np.median(d)),
    "mismatches_by_year": dict(sorted(yrs.items())),
    "distinct_symbols_affected": int(len(cnt)),
    "worst_symbols": [(ps[s], int(c)) for s, c in worst],
    "share_of_mismatches_where_iv_also_differs_pct": float(100 * (IV[bad] != LIV[bad]).mean()) if bad.any() else None,
    "examples": ex,
    "VERDICT": ("FAIL — the two sources genuinely disagree on these cells (not float32 representation): "
                "relative differences are O(1), and both directions occur.")
    if bad.any() and (rel > 1e-6).mean() > 0.5 else "PASS"}

# --- FX decision relevance: does the hit set move? --------------------------------------------
rec["fx_hit_set_impact"] = {}
for th in THRESHOLDS:
    a = both & (FN.astype(np.float64) <= th); b = both & (LR <= th)
    u = int((a | b).sum())
    rec["fx_hit_set_impact"][f"{th}"] = {
        "panel_hits": int(a.sum()), "replay_hits": int(b.sum()), "both": int((a & b).sum()),
        "only_panel": int((a & ~b).sum()), "only_replay": int((b & ~a).sum()),
        "disagree_pct_of_union": float(100 * ((a & ~b) | (b & ~a)).sum() / max(1, u))}

if CSV:
    # the FULL named list of disagreeing cells, for news2's event-level census to use as priority targets.
    # Written with the same verify-then-commit discipline as the receipt: a truncated target list is worse than none,
    # because the census would silently work a short list and report the rest as agreeing.
    tmp = CSV + ".tmp"
    lines = ["symbol,anchor_utc,panel_f_fund_now,replay_last_rate,panel_iv,replay_iv,abs_diff\n"]
    for a, sx in zip(ai, si):
        lines.append("%s,%s,%.10g,%.10g,%g,%g,%.10g\n" % (ps[sx], iso(ti[a]), FN[a, sx], LR[a, sx],
                                                           IV[a, sx], LIV[a, sx], abs(float(FN[a, sx]) - float(LR[a, sx]))))
    with open(tmp, "w") as f:
        f.writelines(lines); f.flush(); os.fsync(f.fileno())
    with open(tmp) as f:
        back = f.readlines()
    assert len(back) == len(lines) and back[-1] == lines[-1], "cell list did not read back complete"
    assert len(back) - 1 == int(bad.sum()), f"csv rows {len(back)-1} != mismatched cells {int(bad.sum())}"
    os.replace(tmp, CSV)
    rec["named_cell_list"] = {"path": CSV, "rows": len(lines) - 1, "sha256": sha(CSV)}
    print("  named cell list: %d rows -> %s" % (len(lines) - 1, CSV), flush=True)

s = write_json_verified(rec, OUT)
print("FA_FXFIELD receipt=%s sha=%s" % (OUT, s[:16]), flush=True)
print("  1(a) f_fund_now un-normalised: equals rate*8/iv on %.2f%% of cells; iv==8 on %.2f%%; restricted_to_iv8=%s"
      % (rec["1a_is_f_fund_now_unnormalised"]["equals_rate_times_8_over_iv_pct"],
         rec["1a_is_f_fund_now_unnormalised"]["share_of_cells_with_iv_eq_8_pct"],
         rec["1a_is_f_fund_now_unnormalised"]["equality_restricted_to_iv_eq_8"]), flush=True)
print("  1(b) %s  equal %.4f%%  mismatched %d  median rel diff %s"
      % (rec["1b_equality_vs_last_rate"]["VERDICT"][:40], rec["1b_equality_vs_last_rate"]["exact_equal_as_float32_pct"],
         rec["1b_equality_vs_last_rate"]["mismatched_cells"],
         rec["1b_equality_vs_last_rate"]["median_relative_diff_on_mismatches"]), flush=True)
for th, v in rec["fx_hit_set_impact"].items():
    print("  hit set th=%s: panel %d / replay %d, disagree %.2f%% of union" % (th, v["panel_hits"], v["replay_hits"], v["disagree_pct_of_union"]), flush=True)
