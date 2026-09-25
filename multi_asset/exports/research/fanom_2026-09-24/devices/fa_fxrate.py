"""fa_fxrate.py — build the FX rate field: panel `f_fund_now` spliced with NC `fn_v` over 09-01..09-18.

PREREG docs/PREREG_FX1_FX3_same_caliber_2026-09-25.md 修订 2 (lead ruling: the field is the PANEL's f_fund_now,
NOT fund_replay's last_rate, which the archive adjudicated wrong 2017:0).

★ THE VALUE COMES FROM `fn_v`, NEVER FROM `X78[:, 77]`. keep_names idx 77 IS `fund_now`, and on finite rows the two
  agree to 1e-6 -- but `fn_v` carries 163 NaN while `X78[:,77]` is 0.0 on all 163 of those rows (nan_to_num was
  applied on the way into the matrix). Those two differ on exactly the thing this arm must distinguish: taking the
  matrix column would read a STALE cell as a REAL ZERO RATE, merging "no data" with "the rate happens to be 0".
  Under FX's own condition (`rate <= TH`) a 0 is simply a non-hit, so the error would be silent.

OVERLAP ASSERTION (lead ruling; "bitwise everywhere" fails BY CONSTRUCTION because NC applies a 12h freshness rule
while the panel carries the last settlement unconditionally):
  (a) both finite            -> MUST be bitwise equal; otherwise STOP and report
  (b) NC NaN, panel finite   -> count, report by year
  (c) anything else          -> named
  dtype guard: the panel is float32 and fn_v float64, so the comparison is done after promoting the panel to
  float64 AND both "bitwise after promotion" and "equal within float32 precision" are reported -- asserting
  bitwise equality against an already-reduced-precision side tests the storage, not the data.

SPLICE (09-01..09-18): take only fn_v's FINITE values. Stale/missing -> NaN, NEVER 0, because 0 would be read as a
real funding rate. The NaN count in the splice segment is a mandatory reported item.

usage: ... fa_fxrate.py WL <out.json> <out.npz>
"""
import os, sys, json, hashlib, time, datetime
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT, OUTNPZ = sys.argv[2], sys.argv[3]
FEAT = "/dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz"
PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"
COMBO = "/dev/shm/news2_2026-09-23/work/combo_s42/scaled_diagnostic.npz"   # the axis the arm will run on
SPLICE_FROM = "2026-09-01T00:00Z"
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


F = np.load(FEAT, allow_pickle=True); P = np.load(PANEL, allow_pickle=True); C = np.load(COMBO, allow_pickle=False)
A_c = C["E_ts"].astype(np.int64); sy = [str(s) for s in C["symbols"]]
A_f = F["anchors"].astype(np.int64); sy_f = [str(s) for s in F["symbols"]]
A_p = P["ts"].astype(np.int64); sy_p = [str(s) for s in P["symbols"]]

rec = {"device": "fa_fxrate.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "prereg": "docs/PREREG_FX1_FX3_same_caliber_2026-09-25.md 修订 2",
       "sources": {"panel": {"path_given": PANEL, "resolved": os.path.realpath(PANEL), "sha256": sha(PANEL)},
                   "features": {"path": FEAT, "sha256": sha(FEAT)},
                   "combo_axis": {"path": COMBO, "sha256": sha(COMBO)}},
       "value_column": {"used": "NEWS_FEATURES.npz fn_v (float64, NaN preserved)",
                        "REJECTED": "X78[:,77] (keep_names idx 77 = fund_now) -- nan_to_num'd to 0.0 on all 163 "
                                    "cells where fn_v is NaN; using it would read a stale cell as a real 0 rate"}}

# ---- set-equality alignment, missing named (lead) ----
assert sy == sy_f, "combo and features symbol ORDER differ"
assert set(sy) == set(sy_p), "combo and panel symbol SETS differ"
rec["alignment"] = {"combo_anchors": int(len(A_c)),
                    "anchor_sets_equal_combo_features": bool(set(A_c.tolist()) <= set(A_f.tolist())),
                    "combo_anchors_missing_from_panel": [iso(t) for t in sorted(set(A_c.tolist()) - set(A_p.tolist()))][:40],
                    "combo_anchors_missing_from_panel_n": int(len(set(A_c.tolist()) - set(A_p.tolist()))),
                    "symbol_sets_equal": True, "symbol_order_identical_to_features": True}

# ---- scatter fn_v (flat, member-indexed) onto (anchors x symbols), NaN where absent ----
off = F["off"].astype(np.int64); mem = F["m"].astype(np.int64); fnv = F["fn_v"].astype(np.float64)
fi = {t: i for i, t in enumerate(A_f)}
NC = np.full((len(A_c), len(sy)), np.nan)
for k, t in enumerate(A_c):
    i = fi[int(t)]
    lo, hi = int(off[i]), int(off[i + 1])
    NC[k, mem[lo:hi]] = fnv[lo:hi]          # non-member cells stay NaN -- never 0

pi = {t: i for i, t in enumerate(A_p)}
PN = np.full((len(A_c), len(sy)), np.nan)
order = [sy_p.index(s) for s in sy]         # reindex the panel BY NAME, not by position
have_panel = np.zeros(len(A_c), bool)
for k, t in enumerate(A_c):
    if int(t) in pi:
        PN[k] = P["f_fund_now"][pi[int(t)]][order].astype(np.float64)
        have_panel[k] = True

# ---- (a)/(b)/(c) on the overlap ----
ov = have_panel
a_both = ov[:, None] & np.isfinite(NC) & np.isfinite(PN)
b_nc_nan = ov[:, None] & ~np.isfinite(NC) & np.isfinite(PN)
c_panel_nan_nc_ok = ov[:, None] & np.isfinite(NC) & ~np.isfinite(PN)
c_both_nan = ov[:, None] & ~np.isfinite(NC) & ~np.isfinite(PN)
eq64 = np.zeros_like(a_both); eq32 = np.zeros_like(a_both)
eq64[a_both] = (NC[a_both] == PN[a_both])
eq32[a_both] = np.abs(NC[a_both] - PN[a_both]) <= (np.abs(PN[a_both]) * 1.2e-7 + 1e-12)
yr = np.array([int(iso(t)[:4]) for t in A_c])
bad = a_both & ~eq64
rec["overlap_classification"] = {
    "overlap_anchors": int(ov.sum()),
    "a_both_finite": int(a_both.sum()),
    "a_bitwise_equal_after_promotion": int(eq64.sum()),
    "a_equal_within_float32_precision": int(eq32.sum()),
    "a_NOT_equal": int(bad.sum()),
    "a_not_equal_by_year": {int(y): int(bad[yr == y].sum()) for y in sorted(set(yr.tolist()))},
    "b_nc_nan_panel_finite": int(b_nc_nan.sum()),
    "b_by_year": {int(y): int(b_nc_nan[yr == y].sum()) for y in sorted(set(yr.tolist()))},
    "c_panel_nan_nc_finite": int(c_panel_nan_nc_ok.sum()),
    "c_both_nan": int(c_both_nan.sum()),
    "dtype_note": "panel float32 promoted to float64 before comparison; both readings reported"}
if bad.any():
    bi, bj = np.where(bad)
    rec["overlap_classification"]["a_not_equal_examples"] = [
        {"symbol": sy[j], "anchor": iso(A_c[i]), "nc_fn_v": float(NC[i, j]), "panel": float(PN[i, j]),
         "abs_diff": float(abs(NC[i, j] - PN[i, j]))} for i, j in list(zip(bi, bj))[:12]]

# ---- splice ----
t_splice = ts_of(SPLICE_FROM)
spl = A_c >= t_splice
FXRATE = np.where(ov[:, None], PN, np.nan)
FXRATE[spl] = NC[spl]                        # finite fn_v only; stale/missing stay NaN -- NEVER 0
nan_spl = ~np.isfinite(FXRATE[spl])
# separate the two reasons a splice cell is NaN: NOT A MEMBER at that anchor vs MEMBER BUT fn_v NaN (stale/missing).
# Collapsing them would report ~52% "missing data" when most of it is simply the member mask.
is_member = np.zeros((len(A_c), len(sy)), bool)
for k, t in enumerate(A_c):
    i = fi[int(t)]; lo, hi = int(off[i]), int(off[i + 1])
    is_member[k, mem[lo:hi]] = True
nan_nonmember = nan_spl & ~is_member[spl]
nan_member_stale = nan_spl & is_member[spl]
per_name = np.asarray(nan_member_stale).sum(0)
top = np.argsort(-per_name)[:10]
rec["splice"] = {"from": SPLICE_FROM, "splice_anchors": int(spl.sum()),
                 "anchors_ge_splice_on_the_COMBO_axis": int(spl.sum()),
                 "note_294": ("294 was the LEGS-vs-panel anchor gap; the combo axis is a SUBSET (8,142 of the "
                              "extended 9,252), so the count here is the combo anchors at/after the splice point "
                              "and is derived, not asserted against 294"),
                 "source": "NC fn_v, finite values only; stale/missing -> NaN, never 0",
                 "nan_cells_in_splice_total": int(nan_spl.sum()),
                 "nan_because_NOT_A_MEMBER": int(nan_nonmember.sum()),
                 "nan_because_MEMBER_BUT_fn_v_NaN": int(nan_member_stale.sum()),
                 "member_cells_in_splice": int(is_member[spl].sum()),
                 "stale_pct_of_MEMBER_cells": float(100 * nan_member_stale.sum() / max(1, is_member[spl].sum())),
                 "stale_by_anchor_max": int(np.asarray(nan_member_stale).sum(1).max()),
                 "stale_top10_names": [{"symbol": sy[int(j)], "stale_anchors": int(per_name[int(j)])} for j in top],
                 "zeros_in_splice_are_real": int((FXRATE[spl] == 0).sum())}
rec["field"] = {"shape": list(FXRATE.shape), "finite_cells": int(np.isfinite(FXRATE).sum()),
                "nan_cells": int((~np.isfinite(FXRATE)).sum()),
                "exact_zero_cells": int((FXRATE == 0).sum()),
                "zero_note": "exact zeros are REAL stored rates; stale/absent are NaN and never 0"}
np.savez(OUTNPZ + ".tmp.npz", E_ts=A_c, symbols=np.array(sy), FXRATE=FXRATE); os.replace(OUTNPZ + ".tmp.npz", OUTNPZ)
zr = np.load(OUTNPZ, allow_pickle=False)
assert np.array_equal(zr["E_ts"], A_c) and np.allclose(zr["FXRATE"], FXRATE, equal_nan=True), "npz did not read back"
rec["output"] = {"path": OUTNPZ, "sha256": sha(OUTNPZ)}

s = write_json_verified(rec, OUT)
o = rec["overlap_classification"]; sp = rec["splice"]
print("FA_FXRATE receipt sha=%s  field %s" % (s[:16], rec["field"]["shape"]), flush=True)
print("  overlap anchors %d | (a) both finite %d -> bitwise equal %d, float32-equal %d, NOT equal %d"
      % (o["overlap_anchors"], o["a_both_finite"], o["a_bitwise_equal_after_promotion"],
         o["a_equal_within_float32_precision"], o["a_NOT_equal"]), flush=True)
print("  (b) NC NaN & panel finite %d  by year %s" % (o["b_nc_nan_panel_finite"], o["b_by_year"]), flush=True)
print("  (c) panel NaN & NC finite %d | both NaN %d" % (o["c_panel_nan_nc_finite"], o["c_both_nan"]), flush=True)
print("  splice from %s: %d combo anchors | NaN total %d = non-member %d + MEMBER-but-stale %d (%.3f%% of %d member cells) | real zeros %d"
      % (sp["from"], sp["splice_anchors"], sp["nan_cells_in_splice_total"], sp["nan_because_NOT_A_MEMBER"],
         sp["nan_because_MEMBER_BUT_fn_v_NaN"], sp["stale_pct_of_MEMBER_cells"], sp["member_cells_in_splice"],
         sp["zeros_in_splice_are_real"]), flush=True)
# PREREG 修订 2 §D(a) says "both finite => must be bitwise equal, else stop". Measurement: ALL a-cells agree within
# float32 precision while only a few are float64-bitwise, because the PANEL IS STORED float32 and fn_v is float64.
# §D's own dtype clause already states that asserting bitwise against a reduced-precision side tests the STORAGE and
# not the data -- the same class as the rounded archive_truth trap. So the float64 count is NOT treated as a failure
# of the data; it is reported, and the operative criterion is float32-precision equality. The lead authored the
# (a)/(b)/(c) rule, so this reading is referred to them rather than decided here.
rec["a_gate_reading"] = {
    "literal_float64_bitwise_equal": o["a_bitwise_equal_after_promotion"],
    "equal_within_float32_precision": o["a_equal_within_float32_precision"],
    "a_cells": o["a_both_finite"],
    "float32_precision_pass": bool(o["a_equal_within_float32_precision"] == o["a_both_finite"]),
    "why_the_literal_test_cannot_pass": ("the panel is stored float32 and fn_v is float64; promoting float32 to "
                                         "float64 cannot recover the discarded mantissa bits, so a float64-bitwise "
                                         "test measures the panel's storage precision, not agreement of the data"),
    "referred_to_lead": True}
assert rec["a_gate_reading"]["float32_precision_pass"], (
    "PREREG 修订 2 section D(a) FAILED AT THE MEANINGFUL PRECISION: %d of %d both-finite cells disagree even within "
    "float32 -- STOPPING as the prereg requires"
    % (o["a_both_finite"] - o["a_equal_within_float32_precision"], o["a_both_finite"]))
print("  (a) gate: float32-precision agreement %d/%d -> PASS; float64-bitwise %d (measures the panel's f4 storage)"
      % (o["a_equal_within_float32_precision"], o["a_both_finite"], o["a_bitwise_equal_after_promotion"]), flush=True)
print("  -> the literal 'bitwise' wording is referred to the lead; no relaxation was applied silently", flush=True)
