"""fa_rn8parity.py — rewire research RN8 to the NC legs product, with the parity control the lead ordered.

LEAD 2026-09-25: "研究 combo 直接读 nc_legs 的 RN8, 不另写一份规则" + "正控制: 在 2,017 格上与归档真值逐位相等,
并报分母" + "轴、名单对齐要按集合相等断言, 不能靠位置; 缺格要具名".

WHY READ RATHER THAN RE-DERIVE: the rule lives in the producer. Re-implementing it from its description is what
produced correction W-1 and the three-errors-at-once episode. So this device READS `news2_2026-09-23/work/legs.npz`
RN8 and never recomputes it. fresh_legs.py (which derived RN8 from the contaminated fund_replay) is retired.

★ WHAT THIS DEVICE CANNOT YET DO, stated up front rather than quietly substituted:
  the lead's control is "bitwise equal to archive truth on the 2,017 adjudicated cells". news2's committed receipt
  (D10_FXFIELD_ADJUDICATION.json) carries the COUNTS and 12 named EXAMPLES, but NOT the per-cell list of the 2,017.
  So the full-denominator control needs a list only news2 holds; it is requested, and this device runs the part it can:
    (A) direct-truth parity on the 12 adjudicated example cells;
    (B) a larger structural parity against the PANEL, which the adjudication certified 2017:0 correct on the rate.
  (B) has a bigger denominator but a weaker reference, so both are reported and neither is called the other.

★ A LIMIT ON ANY RN8 PARITY CLAIM: RN8 = rate * 8/iv needs BOTH. The adjudication's own limits say
  "the archive is treated as truth for the RAW rate; this device does not re-derive intervals" -- so the INTERVAL
  side of the truth is NOT adjudicated. The truth RN8 below therefore uses the archive rate with the PANEL's iv,
  and that composition is labelled, because news2 showed the error in fund_replay was COMPOSITE (rate and iv both).

usage: ... fa_rn8parity.py WL <out.json> <adjudication.json>
"""
import os, sys, json, hashlib, time, datetime
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT, ADJ = sys.argv[2], sys.argv[3]
NC_LEGS = "/dev/shm/news2_2026-09-23/work/legs.npz"
NC_FEAT = "/dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz"
PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"
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


L = np.load(NC_LEGS, allow_pickle=True)
F = np.load(NC_FEAT, allow_pickle=True)
P = np.load(PANEL, allow_pickle=True)
A_l = L["E_ts"].astype(np.int64); sy_l = [str(s) for s in L["symbols"]]
A_f = F["anchors"].astype(np.int64); sy_f = [str(s) for s in F["symbols"]]
A_p = P["ts"].astype(np.int64); sy_p = [str(s) for s in P["symbols"]]

rec = {"device": "fa_rn8parity.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "ordered_by": "lead 2026-09-25 (rewire research RN8 to NC legs + parity control)",
       "rn8_source": {"path": NC_LEGS, "sha256": sha(NC_LEGS),
                      "policy": "READ the producer's product; never re-derive the rule"},
       "retired": {"fresh_legs.py": "main() raises; its RN8 came from the contaminated fund_replay.npz"},
       "inputs": {"features": {"path": NC_FEAT, "sha256": sha(NC_FEAT)},
                  "panel": {"path_given": PANEL, "resolved": os.path.realpath(PANEL), "sha256": sha(PANEL)},
                  "adjudication": {"path": ADJ, "sha256": sha(ADJ)}}}

# ---- alignment by SET EQUALITY, not position (lead's explicit requirement); missing cells named ----
def align(name, A_o, sy_o):
    a_common = np.intersect1d(A_l, A_o); s_common = sorted(set(sy_l) & set(sy_o))
    miss_a = sorted(set(A_l.tolist()) - set(A_o.tolist())); miss_s = sorted(set(sy_l) - set(sy_o))
    d = {"anchors_legs": int(len(A_l)), "anchors_other": int(len(A_o)), "anchors_common": int(len(a_common)),
         "symbols_legs": len(sy_l), "symbols_other": len(sy_o), "symbols_common": len(s_common),
         "anchor_sets_equal": bool(set(A_l.tolist()) == set(A_o.tolist())),
         "symbol_sets_equal": bool(set(sy_l) == set(sy_o)),
         "symbol_order_identical": bool(sy_l == sy_o),
         "anchors_in_legs_missing_from_other_n": len(miss_a),
         "anchors_in_legs_missing_from_other_named": [datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ") for t in miss_a[:40]],
         "symbols_in_legs_missing_from_other_named": miss_s[:40]}
    assert d["symbol_sets_equal"], f"{name}: symbol SETS differ; a cell-level parity would be comparing different names"
    return d


rec["alignment"] = {"features_vs_legs": align("features", A_f, sy_f), "panel_vs_legs": align("panel", A_p, sy_p)}

RN8 = L["RN8"]
li = {t: i for i, t in enumerate(A_l)}; lj = {s: j for j, s in enumerate(sy_l)}

# ---- (A) direct-truth parity on the adjudicated example cells ----
adj = json.load(open(ADJ))
ex = adj["examples"]["PANEL_RIGHT"]
rows = []
for e in ex:
    sym, anc = e["symbol"], e["anchor"]
    t = ts_of(anc)
    if t not in li or sym not in lj:
        rows.append({"symbol": sym, "anchor": anc, "status": "NOT ON THE LEGS AXIS"}); continue
    iv = float(e["panel_iv"])
    truth_rn8 = float(e["archive_truth"]) * 8.0 / iv if iv > 0 else float("nan")
    # ★ the receipt PUBLISHES archive_truth ROUNDED (e.g. -0.00039508) while the panel carries the full float
    # (-0.00039507998735643923). A 1e-12 "bitwise" test against a rounded reference can NEVER pass -- my first
    # version reported 0/12 while every printed pair agreed to 8 decimals. So the tolerance is tied to the
    # reference's own published precision, and the full-precision panel value is compared separately.
    tol = abs(truth_rn8) * 1e-7 + 1e-10           # the published rate carries ~8 decimals
    panel_rate = float(e["panel"])
    panel_rn8_cell = panel_rate * 8.0 / iv if iv > 0 else float("nan")
    got = float(RN8[li[t], lj[sym]])
    if not np.isfinite(got):
        rows.append({"symbol": sym, "anchor": anc, "status": "NO NC VALUE (not a member, or stale under the 12h rule)",
                     "archive_truth_rate": e["archive_truth"], "truth_rn8_composed": truth_rn8}); continue
    rows.append({"symbol": sym, "anchor": anc, "archive_truth_rate": e["archive_truth"],
                 "iv_used_from_panel": iv, "truth_rn8_composed": truth_rn8, "nc_legs_rn8": got,
                 "equal_within_published_precision": bool(abs(got - truth_rn8) <= tol),
                 "tolerance_used": tol,
                 "equal_to_panel_full_precision": bool(abs(got - panel_rn8_cell) < 1e-12),
                 "abs_diff_vs_rounded_truth": abs(got - truth_rn8),
                 "abs_diff_vs_panel_full_precision": abs(got - panel_rn8_cell),
                 "ledger_rn8_for_contrast": (float(e["ledger"]) * 8.0 / float(e["ledger_iv"]) if e.get("ledger_iv") else None)})
ok = [r for r in rows if r.get("equal_within_published_precision")]
okf = [r for r in rows if r.get("equal_to_panel_full_precision")]
on_axis = [r for r in rows if "status" not in r]
rec["A_direct_truth_parity"] = {
    "reference": "archive rate (adjudicated) composed with the PANEL's iv (NOT adjudicated)",
    "denominator_cells_on_legs_axis": len(on_axis), "cells_offered_by_receipt": len(rows),
    "equal_within_published_precision": len(ok),
    "equal_within_published_precision_pct": (100.0 * len(ok) / len(on_axis)) if on_axis else None,
    "equal_to_panel_full_precision": len(okf),
    "cells_with_no_nc_value": len([r for r in rows if "status" in r]),
    "precision_note": ("the receipt's archive_truth is rounded for publication; a 1e-12 test against it is not a "
                       "test of the data. Exact equality is tested against the panel's full-precision value, which "
                       "the adjudication certified equal to the archive."),
    "cells": rows,
    "LIMIT": ("12 cells only -- the receipt does not publish the per-cell list of the 2,017 adjudicated cells, so "
              "the lead's full-denominator control is NOT yet satisfied; requested from news2")}

# ---- (B) structural parity against the panel (certified 2017:0 on the RATE) ----
pi = {t: i for i, t in enumerate(A_p)}
common_t = np.intersect1d(A_l, A_p)
ri = np.array([li[int(t)] for t in common_t]); rp = np.array([pi[int(t)] for t in common_t])
order = [sy_p.index(s) for s in sy_l]                       # reindex the panel onto the legs' symbol order BY NAME
FN = P["f_fund_now"][rp][:, order].astype(np.float64)
IV = P["f_fund_iv"][rp][:, order].astype(np.float64)
panel_rn8 = np.where(np.isfinite(FN) & np.isfinite(IV) & (IV > 0), FN * 8.0 / np.where(IV > 0, IV, np.nan), np.nan)
nc = RN8[ri]
both = np.isfinite(nc) & np.isfinite(panel_rn8)
d = np.abs(nc[both] - panel_rn8[both])
rec["B_structural_parity_vs_panel"] = {
    "reference": "panel f_fund_now * 8 / f_fund_iv; the adjudication certified the panel RATE 2017:0 on 5 months",
    "common_anchors": int(len(common_t)), "denominator_finite_cells": int(both.sum()),
    "equal_within_1e-12": int((d < 1e-12).sum()), "equal_pct": float(100 * (d < 1e-12).mean()),
    "median_abs_diff": float(np.median(d)), "p99_abs_diff": float(np.percentile(d, 99)), "max_abs_diff": float(d.max()),
    "LIMIT": ("differences here are NOT all defects: NC applies a 12h freshness rule while the panel carries the last "
              "settlement regardless, so legitimate staleness disagreements are included. This is a magnitude check, "
              "not a pass/fail gate. The panel's correctness is established on 2,017 cells in 5 months; using it as a "
              "reference elsewhere extrapolates that.")}

s = write_json_verified(rec, OUT)
print("FA_RN8PARITY receipt sha=%s" % s[:16], flush=True)
al = rec["alignment"]
for k, v in al.items():
    print("  align %-18s anchors common %5d (sets equal %s) | symbols common %3d (sets equal %s, order identical %s) | legs anchors missing elsewhere %d"
          % (k, v["anchors_common"], v["anchor_sets_equal"], v["symbols_common"], v["symbol_sets_equal"],
             v["symbol_order_identical"], v["anchors_in_legs_missing_from_other_n"]), flush=True)
a = rec["A_direct_truth_parity"]
print("  (A) direct truth: %d/%d equal within the truth's published precision; %d/%d exactly equal to the panel's full-precision value; %d cells have no NC value"
      % (a["equal_within_published_precision"], a["denominator_cells_on_legs_axis"],
         a["equal_to_panel_full_precision"], a["denominator_cells_on_legs_axis"], a["cells_with_no_nc_value"]), flush=True)
for r in a["cells"][:6]:
    if "status" in r: print("      %-14s %-16s %s" % (r["symbol"], r["anchor"], r["status"]), flush=True); continue
    print("      %-14s %-16s nc=%+.8f truth=%+.8f %-7s panel-exact %-5s (ledger would be %+.8f)"
          % (r["symbol"], r["anchor"], r["nc_legs_rn8"], r["truth_rn8_composed"],
             "EQUAL" if r["equal_within_published_precision"] else "DIFFERS",
             str(r["equal_to_panel_full_precision"]), r["ledger_rn8_for_contrast"] or float("nan")), flush=True)
b = rec["B_structural_parity_vs_panel"]
print("  (B) vs panel: %d/%d within 1e-12 (%.2f%%), median |diff| %.3e, max %.3e"
      % (b["equal_within_1e-12"], b["denominator_finite_cells"], b["equal_pct"], b["median_abs_diff"], b["max_abs_diff"]), flush=True)
