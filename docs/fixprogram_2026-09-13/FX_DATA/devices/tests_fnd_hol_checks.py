#!/usr/bin/env python3
"""FP2-1: the three rebuilt checks, with the negative controls the reviewer asked for (finite→Inf, same values different mask,
one column written wrong, sub-tolerance perturbation) and the positive control that a legitimate output is unchanged."""
import os, sys, tempfile, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fnd_hol_checks import c1_diff_mask, c2_now_iv_from_stream, c2_compare_columns, c2_compare_columns_sourced, roundtrip_verify
FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:200]) if detail is not None else ""), flush=True)
rng = np.random.default_rng(7); A = rng.normal(size=(50, 6)); A[3, 2] = np.nan
print("[C1] exact + finite-support difference mask")
m, r = c1_diff_mask(A, A.copy()); check("★★★ identical arrays (incl. shared NaN) ⇒ zero differing cells", m.sum() == 0, r)
B = A.copy(); B[10, 1] += 5e-7; m, r = c1_diff_mask(B, A); check("★★★ a 5e-7 perturbation IS counted (exact compare, no 1e-6 tolerance)", m.sum() == 1 and r["value_differs_exact"] == 1, r)
B = A.copy(); B[7, 4] = np.inf; m, r = c1_diff_mask(B, A); check("★★★ finite→+Inf in the rebuild IS counted (finite-support gate)", m.sum() == 1 and r["finite_support_differs"] == 1 and r["inf_in_rebuild"] == 1, r)
Ai = A.copy(); Ai[7, 4] = np.inf; m, r = c1_diff_mask(Ai.copy(), Ai); check("★★ Inf in BOTH at the same cell ⇒ no difference, but reported as non-finite support (visible, not silent)", m.sum() == 0 and r["inf_in_incumbent"] == 1 and r["inf_in_rebuild"] == 1, r)
Bi = A.copy(); Bi[7, 4] = np.inf; Bf = A.copy(); Bf[7, 4] = 1.0
m, r = c1_diff_mask(Bf, Bi); check("★★★ incumbent has Inf, rebuild has a finite value ⇒ COUNTED (the old `|a-b| > Inf` was False here)", m.sum() == 1 and r["finite_support_differs"] == 1, r)
B = A.copy(); B[3, 2] = 0.0; m, r = c1_diff_mask(B, A); check("★★ NaN mask difference is counted", m.sum() == 1 and r["nan_mask_differs"] == 1, r)
print("\n[C2] all five columns rebuilt from the stream; a copied column can never be 'reproduced'")
ft = np.array([1000, 1000 + 8 * 3600, 1000 + 16 * 3600, 1000 + 24 * 3600]); fr = np.array([0.0001, 0.0002, -0.0001, 0.0003]); iv = np.array([8.0, 8.0, 8.0, 8.0])
tail = np.array([1000 + 4 * 3600, 1000 + 12 * 3600, 1000 + 20 * 3600, 1000 + 40 * 3600])          # last anchor is 16h after the last event
fn, fi = c2_now_iv_from_stream(ft, fr, iv, tail)
check("★★★ f_fund_now = last event at/before anchor; stale (>12h) ⇒ NaN", np.allclose(fn[:3], [0.0001, 0.0002, -0.0001]) and np.isnan(fn[3]) and np.allclose(fi[:3], 8.0) and np.isnan(fi[3]), (fn, fi))
inc = {"f_fund_now": fn.copy(), "f_fund_iv": fi.copy(), "f_fund_ema": np.array([1, 2, 3, 4], np.float32)}
reb_copy = {k: v.copy() for k, v in inc.items()}            # the OLD device: copied, then compared with itself
res = c2_compare_columns(reb_copy, inc, list(inc), rebuilt_from_stream={"f_fund_ema"})
check("★★★ columns NOT recomputed are reported SELF_COMPARE, never REPRODUCED (the old self-comparison cannot pass)", res["f_fund_now"]["verdict"] == "SELF_COMPARE" and res["f_fund_iv"]["verdict"] == "SELF_COMPARE" and res["f_fund_ema"]["verdict"] == "REPRODUCED", {k: v["verdict"] for k, v in res.items()})
reb = {"f_fund_now": fn.copy(), "f_fund_iv": fi.copy(), "f_fund_ema": inc["f_fund_ema"].copy()}
res = c2_compare_columns(reb, inc, list(inc), rebuilt_from_stream=set(inc))
check("★★★ all five recomputed and equal ⇒ REPRODUCED for every column (positive control)", all(v["verdict"] == "REPRODUCED" for v in res.values()), {k: v["verdict"] for k, v in res.items()})
reb2 = dict(reb); reb2["f_fund_iv"] = reb["f_fund_iv"].copy(); reb2["f_fund_iv"][1] = 4.0
res = c2_compare_columns(reb2, inc, list(inc), rebuilt_from_stream=set(inc))
check("★★ a recomputed column that differs is DIFFERS with maxabs reported", res["f_fund_iv"]["verdict"] == "DIFFERS" and res["f_fund_iv"]["maxabs"] == 4.0, res["f_fund_iv"])
print("\n[W] write round-trip over every payload")
out = {"ts": np.arange(5, dtype=np.int64), "symbols": np.array(["A", "B"]), "X": rng.normal(size=(5, 2)).astype(np.float32), "M": np.array([[1, np.nan], [2, 3], [4, 5], [6, 7], [8, 9]], np.float32)}
d = tempfile.mkdtemp(); p = os.path.join(d, "o.npz"); np.savez(p, **out); Z = np.load(p, allow_pickle=False)
ok, r = roundtrip_verify(Z, out); check("★★★ faithful write ⇒ round-trip OK (dtype/shape/NaN-mask/bytes for every key)", ok and r["n_keys_bad"] == 0, r["n_keys_bad"])
bad = {k: v.copy() for k, v in out.items()}; bad["X"][0, 0] = 999.0; p2 = os.path.join(d, "bad.npz"); np.savez(p2, **bad)
ok, r = roundtrip_verify(np.load(p2, allow_pickle=False), out); check("★★★ X[0,0] := 999 in the written file ⇒ round-trip FAILS naming X (the old keys+ts check passed this)", not ok and not r["per_key"]["X"]["ok"] and r["per_key"]["ts"]["ok"], r["per_key"]["X"])
bad2 = {k: v.copy() for k, v in out.items()}; bad2["M"][1, 1] = np.nan; p3 = os.path.join(d, "bad2.npz"); np.savez(p3, **bad2)
ok, r = roundtrip_verify(np.load(p3, allow_pickle=False), out); check("★★ same values, different NaN mask ⇒ FAILS naming M", not ok and not r["per_key"]["M"]["nan_mask_equal"], r["per_key"]["M"])
bad3 = {k: v.copy() for k, v in out.items()}; bad3["X"] = bad3["X"].astype(np.float64); p4 = os.path.join(d, "bad3.npz"); np.savez(p4, **bad3)
ok, r = roundtrip_verify(np.load(p4, allow_pickle=False), out); check("★★ dtype drift (float32 written as float64) ⇒ FAILS", not ok and not r["per_key"]["X"]["dtype_equal"], r["per_key"]["X"])
miss = {k: v for k, v in out.items() if k != "M"}; p5 = os.path.join(d, "miss.npz"); np.savez(p5, **miss)
ok, r = roundtrip_verify(np.load(p5, allow_pickle=False), out); check("★★ a missing key ⇒ FAILS naming it", not ok and r["keys_missing"] == ["M"], r["keys_missing"])
# ── F05 (independent review 2026-09-17): no-source symbols are COPIED_NO_SOURCE, never REPRODUCED, and cannot make a column pass ──
from fnd_hol_checks import c2_compare_columns_sourced as _c2s
_T, _N = 40, 6; _inc = {c: np.random.default_rng(5).normal(size=(_T, _N)) for c in ("a", "b")}; _hs = np.array([True, True, True, False, False, False])
for _label, _reb in (("identical copies", {c: _inc[c].copy() for c in _inc}),
                     ("altered finite values on no-source symbols", {c: np.where(np.arange(_N)[None, :] >= 3, _inc[c] + 1.0, _inc[c]) for c in _inc}),
                     ("all-NaN on no-source symbols", {c: np.where(np.arange(_N)[None, :] >= 3, np.nan, _inc[c]) for c in _inc})):
    _res, _ns = _c2s(_reb, _inc, ["a", "b"], rebuilt_from_stream={"a", "b"}, has_source=_hs)
    check(f"★★★ F05 {_label}: sourced symbols REPRODUCED, 3 symbols reported COPIED_NO_SOURCE, partial flag set, comparison over 3 symbols only",
          all(v["verdict"] == "REPRODUCED" and v["symbols_compared"] == 3 and v["symbols_copied_no_source"] == 3 for v in _res.values()) and _ns["verdict_no_source"] == "COPIED_NO_SOURCE" and _ns["independent_rebuild_partial"] is True and _ns["no_source_idx"] == [3, 4, 5], (_ns, {k: v["verdict"] for k, v in _res.items()}))
_reb_bad = {c: _inc[c].copy() for c in _inc}; _reb_bad["a"][2, 1] += 1e-7
_res, _ns = _c2s(_reb_bad, _inc, ["a", "b"], rebuilt_from_stream={"a", "b"}, has_source=_hs)
check("★★★ F05 a sourced symbol that differs ⇒ DIFFERS (the no-source copies cannot mask it)", _res["a"]["verdict"] == "DIFFERS" and _res["b"]["verdict"] == "REPRODUCED", {k: v["verdict"] for k, v in _res.items()})
_res, _ns = _c2s(_inc, _inc, ["a", "b"], rebuilt_from_stream={"a", "b"}, has_source=np.zeros(_N, bool))
check("★★★ F05 NO symbol has a source ⇒ every column UNAVAILABLE_NO_SOURCED_SYMBOL (a full copy can never read as reproduced)", all(v["verdict"] == "UNAVAILABLE_NO_SOURCED_SYMBOL" for v in _res.values()) and _ns["n_with_source"] == 0, {k: v["verdict"] for k, v in _res.items()})

print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
