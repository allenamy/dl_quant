"""PREREG_v4 §2.5 judge (frozen §4 of PREREG_king_clip_label_ablation, verbatim rules; AMENDMENT 1 item 5: RAW accounting => recorded g, no clip correction).
Arms on the dev_v4 tree: A0 (v3 king + in-service F10 yearly OOS), A1 (king v4 + F10 v4 RAW/FIX7), A2 (king v4 + F10 v4 CLIP/FIX7), A3 (king v4 + in-service F10).
g = net_ex/gross_total [bps/anchor per gross]; frozen window 2025-03-01 -> 2026-08-10 20Z; UTC-day block bootstrap 2000; base seed 20260905 with a
per-contrast sub-stream (judge_ci_depends_on_arm_set): rng = default_rng([20260905, contrast_index]). Verdict per (contrast, seat) over both seeds:
(A) point>0 and CI lower>0 on both; (B) CI upper<0 on both; (C) otherwise UNDECIDED (never 'non-inferior'). Levels: full-cycle yearly table (negative years explicit,
maxDD includes the window start (E-0909-C), worst UTC day, worst calendar month), extension window 08-11->08-30 and 08-31 reported separately.
Reproduction check first (#20): A0 dyn vs the published RAW_M1_UCRYPTO arm (dev_raw: v3 king + in-service F10, RAW accounting on _ext+patch).

★ ROUND 3 (independent review 31fa3e4e §3, 2026-09-10) — the judge's PRECONDITIONS are program conditions, and its OUTPUT states its own standing:
  · reproduction (#20) requires BOTH seeds' A0p references (was: any one), each paired max|Δ| finite and <= JUDGE_REPRO_TOL      -> exit 3
  · the frozen window is an EXACT TIME SET: every arm's frozen axis has JUDGE_N_FROZEN anchors, starts at the window start, is strictly 4h-spaced
    (no duplicate, no gap) and is identical across arms (was: a count)                                                                  -> exit 2
  · every g on the frozen window and every reference is finite (NaN/inf used to slip through `NaN > tol`)                             -> exit 3
  · JUDGE_ALLOW_PARTIAL=1 is EXPLORATION: the JSON carries exploratory=true and no verdict can be a PROMOTE
  · eligibility comes from the export gate: missing or not PASS => eligibility="informational" and an (A) reads "(A) INFO" (the judge cannot promote
    what the export gate refused)
  · the extended-window count is computed, not typed.

★ ROUND 4 (researcher round-3 extra cases judge_minimal_PASS / judge_unrelated_stale_PASS / judge_A1e_gate_promotes_other_arm, 2026-09-10) —
  eligibility is PER ARM and IDENTITY-BOUND, not a global boolean read off a bare {"PASS": true}:
  · JUDGE_ELIGIBILITY = JSON (inline or a file path) {arm: {"receipt": path, "gate": name, "self_sha": sha256, "inputs": {name: path}[, "profile": stage]}};
    every entry is put through v4_gate_common.require (gate name equal, gate source sha equal, PASS, every input registered for the gate in
    REQUIRED_INPUTS declared, every declared input's sha equal to the file on disk);
    an arm without a bound PASS is "informational" and its (A) cells read "(A) INFO"; a PASS bound to arm X never promotes arm Y
  · JUDGE_EXPORT_GATE is a DEPRECATED alias: recorded under out["export_gate"] for information, prints a warning, and can no longer make any arm eligible."""
import numpy as np, json, calendar, time, os, sys
HC = os.environ.get("JUDGE_HC", "/workspace/review_scratch/health_check")   # review b0a573a1 R4: parametrised so refusal paths can be tested
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}; APY = 2190
def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))
FROZEN = (T(2025, 3, 1), T(2026, 8, 10, 20) + 1); EXT = (T(2025, 3, 1), T(2026, 8, 31, 20) + 1)   # AMENDMENT 4: extended window = secondary reading (verdict stays on FROZEN)
WIN = {"2022": (T(2022, 1, 1), T(2023, 1, 1)), "2023": (T(2023, 1, 1), T(2024, 1, 1)), "2024": (T(2024, 1, 1), T(2025, 1, 1)), "2025": (T(2025, 1, 1), T(2026, 1, 1)), "2026→08-10 20Z": (T(2026, 1, 1), T(2026, 8, 10, 20) + 1),
       "frozen 2025-03-01→2026-08-10 20Z": FROZEN, "2024-01→2026-08-10 20Z": (T(2024, 1, 1), T(2026, 8, 10, 20) + 1), "ext 08-11→08-30 20Z": (T(2026, 8, 11), T(2026, 8, 30, 20) + 1), "08-31 (6)": (T(2026, 8, 31), T(2026, 9, 1)),
       "2026→08-31 20Z (all)": (T(2026, 1, 1), T(2026, 8, 31, 20) + 1), "EXTENDED 2025-03-01→2026-08-31 20Z": EXT, "2024-01→2026-08-31 20Z": (T(2024, 1, 1), T(2026, 8, 31, 20) + 1)}
PARTIAL = os.environ.get("JUDGE_ALLOW_PARTIAL") == "1"
def load(path):
    A = np.load(path, allow_pickle=True); R = A["d30_n2_c42_rec"]; ts = R[:, 0].astype(np.int64); g = R[:, C["net_ex"]] / R[:, C["gross_total"]]
    return ts, g, R
def boot(v, days, rng):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    if nd < 3: return (float("nan"), float("nan"), float("nan"))
    S = np.bincount(inv, weights=v, minlength=nd); N = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(2000, nd)); mn = S[idx].sum(1) / N[idx].sum(1)
    return float(np.percentile(mn, 2.5)), float(np.percentile(mn, 97.5)), float((mn > 0).mean())
def levels(ts, g, R):
    out = {}
    for w, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi)
        if not m.any(): continue
        v = g[m]; c = np.concatenate([[0.0], np.cumsum(v)]); dd = float(np.max(np.maximum.accumulate(c) - c))
        days = ts[m] // 86400; ud, inv = np.unique(days, return_inverse=True); dsum = np.bincount(inv, weights=v); mon = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in ts[m]]); um, im = np.unique(mon, return_inverse=True); msum = np.bincount(im, weights=v)
        out[w] = {"n": int(m.sum()), "mean_bps": float(v.mean()), "sharpe": float(v.mean() / v.std(ddof=1) * np.sqrt(APY)) if m.sum() > 2 and v.std(ddof=1) > 0 else float("nan"), "maxdd_bps": dd,
                  "worst_day_bps": float(dsum.min()), "worst_day": time.strftime("%F", time.gmtime(int(ud[dsum.argmin()]) * 86400)), "worst_month_bps": float(msum.min()), "worst_month": str(um[msum.argmin()]),
                  "n_neg_months": int((msum < 0).sum()), "n_months": int(len(um)), "gross_total_mean": float(R[m, C["gross_total"]].mean()), "nsel_mean": float(R[m, C["nsel"]].mean()), "w3_king_mean": float(R[m, C["w3_king"]].mean()), "turnover_mean": float(R[m, C["turnover"]].mean()),
                  "annual_pct_per_gross": float(v.mean() * APY / 1e4 * 100), "negative_year": bool(v.sum() < 0)}
    return out
def frozen_axis_check(ts, n_expected):
    """(ok, why): the frozen window of this arm is an exact 4h grid of n_expected anchors starting at FROZEN[0]."""
    a = ts[(ts >= FROZEN[0]) & (ts < FROZEN[1])]
    if len(a) != n_expected: return False, f"n={len(a)} != {n_expected}"
    if len(a) and int(a[0]) != FROZEN[0]: return False, f"first anchor {int(a[0])} != window start {FROZEN[0]}"
    if len(a) > 1:
        d = np.diff(a)
        if (d != 14400).any():
            bad = int(np.argmax(d != 14400)); return False, f"not a strict 4h grid at index {bad}: diff {int(d[bad])} s (duplicate or gap)"
    return True, "exact 4h grid"
ARMS = {}; missing = []
for arm in ("A0", "A0p", "A1", "A1s", "A1e", "A2", "A3"):
    for seat in ("dyn", "fix"):
        for s in ("42", "2027"):
            p = f"{HC}/dev_v4/probe_artifacts/w10_ablation_series_V4_{arm}_{seat}_s{s}.npz"
            if os.path.exists(p): ARMS[(arm, seat, s)] = load(p)
            else: missing.append(f"{arm}_{seat}_s{s}")
print("arms loaded:", sorted("_".join(k) for k in ARMS), "| missing:", missing)
out = {"arms": sorted("_".join(k) for k in ARMS), "missing": missing, "levels": {}, "contrasts": {}, "verdicts": {}, "reproduction": {}, "exploratory": bool(PARTIAL)}
# --- eligibility (round 4): PER ARM and IDENTITY-BOUND. The promoted arm of a contrast may read "(A) PROMOTE" only if an export-gate receipt BOUND TO THAT
#     ARM passes v4_gate_common.require — the same (gate name, gate source sha, input shas) contract the chains dispatch on. A bare {"PASS": true}, a receipt
#     from another gate, a receipt whose inputs have changed, or a receipt bound to another arm makes nothing eligible (researcher cases minimal_PASS /
#     unrelated_stale_PASS / A1e_gate_promotes_other_arm). JUDGE_EXPORT_GATE (round 3) is a deprecated alias: information only, promotes nothing.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4_gate_common import require as _require   # noqa: E402  (returns (ok, why) without exiting)
def _json_inline_or_path(s):
    """JUDGE_ELIGIBILITY may be a path to a JSON file or the JSON text itself. Returns (obj, error)."""
    if s is None or s == "": return None, None
    if os.path.exists(s):
        try: return json.load(open(s)), None
        except Exception as e: return None, f"JUDGE_ELIGIBILITY file unreadable ({s}): {type(e).__name__}: {e}"   # noqa: BLE001
    try: return json.loads(s), None
    except Exception as e: return None, f"JUDGE_ELIGIBILITY is neither an existing file nor JSON: {type(e).__name__}: {e}"   # noqa: BLE001
_el_raw = os.environ.get("JUDGE_ELIGIBILITY"); _el_map, _el_err = _json_inline_or_path(_el_raw)
if _el_raw and not isinstance(_el_map, dict): _el_map, _el_err = {}, (_el_err or "JUDGE_ELIGIBILITY must be a JSON object {arm: {receipt, gate, self_sha, inputs}}")
_elig = {}
for _arm, _spec in sorted((_el_map or {}).items()):
    if not isinstance(_spec, dict) or not _spec.get("receipt"):
        _elig[_arm] = {"ok": False, "why": "entry is not {receipt, gate, self_sha, inputs}", "receipt": None, "gate": None}; continue
    _ok, _why = _require(str(_spec["receipt"]), dict(_spec.get("inputs") or {}), expected_gate=_spec.get("gate"), expected_self_sha=_spec.get("self_sha"), profile=_spec.get("profile"))
    _elig[_arm] = {"ok": bool(_ok), "why": _why, "receipt": _spec["receipt"], "gate": _spec.get("gate"), "self_sha": _spec.get("self_sha"), "inputs": sorted((_spec.get("inputs") or {}).keys())}
_eligible_arms = sorted(a for a, r in _elig.items() if r["ok"])
out["eligibility_by_arm"] = _elig; out["eligible_arms"] = _eligible_arms; out["eligibility_error"] = _el_err
out["eligibility"] = "candidate" if _eligible_arms else "informational"
_eg_path = os.environ.get("JUDGE_EXPORT_GATE"); _eg = None   # deprecated alias, information only
if _eg_path and os.path.exists(_eg_path):
    try: _eg = json.load(open(_eg_path))
    except Exception as _e: _eg = {"unreadable": f"{type(_e).__name__}: {_e}"}   # noqa: BLE001
out["export_gate"] = {"path": _eg_path, "present": bool(_eg), "gate": (_eg or {}).get("gate"), "PASS": (_eg or {}).get("PASS"), "utc": (_eg or {}).get("utc"), "deprecated": True,
                      "effect": "information only (round 4): a bare receipt is bound to no gate source, no inputs and no arm, so it cannot make an arm eligible; use JUDGE_ELIGIBILITY"}
if _eg_path: print("WARNING: JUDGE_EXPORT_GATE is DEPRECATED (round 4) — recorded for information only, it makes NO arm eligible; bind per arm with JUDGE_ELIGIBILITY={arm:{receipt,gate,self_sha,inputs}}", flush=True)
if _el_err: print("WARNING: JUDGE_ELIGIBILITY ignored:", _el_err, flush=True)
print(f"eligibility: {out['eligibility']} | eligible arms {_eligible_arms} | per arm { {a: r['ok'] for a, r in _elig.items()} } | deprecated export gate {_eg_path!r}: PASS={out['export_gate']['PASS']!r} | exploratory={PARTIAL}", flush=True)
for _arm, _r in _elig.items(): print(f"   eligibility[{_arm}]: {'BOUND PASS' if _r['ok'] else 'NOT eligible'} — {_r['why']}", flush=True)
# --- reproduction check first (#20): A0 dyn vs published RAW_M1_UCRYPTO (dev_raw), frozen window
_nonfinite = []
for arm0 in ("A0p", "A0"):   # A0p = same F10 vintage as the published RAW_M1 arm (port_w10 08-22 preds aligned to the v4 axis) -> the like-for-like reproduction; A0 = in-service 09-01 vintage
  for s in ("42", "2027"):
    p = f"{HC}/dev_raw/probe_artifacts/w10_ablation_series_RAW_M1_UCRYPTO_s{s}.npz"
    if (arm0, "dyn", s) in ARMS and os.path.exists(p):
        t0, g0, _ = ARMS[(arm0, "dyn", s)]; t1, g1, _ = load(p); com = np.intersect1d(t0, t1); i0 = np.searchsorted(t0, com); i1 = np.searchsorted(t1, com); m = (com >= FROZEN[0]) & (com < FROZEN[1])
        if not np.isfinite(g1[i1][m]).all(): _nonfinite.append(f"RAW_M1_s{s} reference (frozen window)")
        d = g0[i0][m] - g1[i1][m]; m26 = (com >= T(2026, 1, 1)) & (com < FROZEN[1]); d26 = g0[i0][m26] - g1[i1][m26]
        out["reproduction"][f"{arm0}_dyn_s{s}_vs_RAW_M1"] = {"n": int(m.sum()), "arm_mean": float(g0[i0][m].mean()), "RAW_M1_mean": float(g1[i1][m].mean()), "paired_mean": float(d.mean()), "paired_maxabs": float(np.abs(d).max()) if m.any() else float("nan"), "share_exact": float(np.mean(np.abs(d) < 1e-9)), "share_lt_1e-3": float(np.mean(np.abs(d) < 1e-3)), "paired_maxabs_2026": float(np.abs(d26).max()) if m26.any() else float("nan")}
        print(f"REPRO {arm0} dyn s{s} vs RAW_M1 (frozen): {g0[i0][m].mean():+.4f} vs {g1[i1][m].mean():+.4f} | paired Δ {d.mean():+.4f} max|Δ| {np.abs(d).max() if m.any() else float('nan'):.4f} share<1e-3 {np.mean(np.abs(d) < 1e-3):.3f} | 2026 max|Δ| {np.abs(d26).max() if m26.any() else float('nan'):.4f}")
# ★ review b0a573a1 R4 + round 3: the reproduction (#20) is a GATE — BOTH seeds' A0p references must exist and each paired max|Δ| must be FINITE and <= JUDGE_REPRO_TOL; else exit 3.
_tol = float(os.environ.get("JUDGE_REPRO_TOL", "1e-6"))
_rep_need = [f"A0p_dyn_s{s}_vs_RAW_M1" for s in ("42", "2027")]
_rep_missing = [k for k in _rep_need if k not in out["reproduction"]]
_rep_bad = {k: out["reproduction"][k]["paired_maxabs"] for k in _rep_need if k in out["reproduction"] and not (np.isfinite(out["reproduction"][k]["paired_maxabs"]) and out["reproduction"][k]["paired_maxabs"] <= _tol)}
if (_rep_bad or _rep_missing) and not PARTIAL:
    print("JUDGE_REFUSED reproduction (#20):", {"missing_reference": _rep_missing, "paired_maxabs_bad_or_nonfinite": _rep_bad}, flush=True); sys.exit(3)
# --- axis + finiteness gates (round 3): exact frozen time set, identical across arms; every frozen g finite
N_FROZEN = int(os.environ.get("JUDGE_N_FROZEN", "3168"))
_axis_bad = {}; _ref_axis = None
for k, (ts, g, R) in sorted(ARMS.items()):
    ok, why = frozen_axis_check(ts, N_FROZEN)
    if not ok: _axis_bad["_".join(k)] = why; continue
    a = ts[(ts >= FROZEN[0]) & (ts < FROZEN[1])]
    if _ref_axis is None: _ref_axis = a
    elif not np.array_equal(a, _ref_axis): _axis_bad["_".join(k)] = "frozen axis differs from the first loaded arm"
    if not np.isfinite(g[(ts >= FROZEN[0]) & (ts < FROZEN[1])]).all(): _nonfinite.append("_".join(k) + " (frozen window g)")
out["frozen_axis_bad"] = _axis_bad; out["nonfinite"] = _nonfinite
if _nonfinite and not PARTIAL:
    print("JUDGE_REFUSED non-finite g/reference:", _nonfinite, flush=True); sys.exit(3)
# --- levels
print("\n== LEVELS (bps/anchor per gross; annual % per gross = mean*2190/1e4; at 2.0x gross multiply by 2) ==")
for k, (ts, g, R) in sorted(ARMS.items()):
    L = levels(ts, g, R); out["levels"]["_".join(k)] = L
    print(f"\n-- {'_'.join(k)} --"); print("%-34s %5s %8s %6s %8s %9s %11s %9s %11s %6s %6s %5s" % ("window", "n", "bps/anch", "Shp", "ann%/g", "maxDD", "worst day", "wd bps", "worst month", "negM", "w3k", "NEG"))
    for w, r in L.items(): print("%-34s %5d %+8.4f %6.2f %+8.2f %9.1f %11s %+9.1f %11s %3d/%2d %6.3f %5s" % (w, r["n"], r["mean_bps"], r["sharpe"], r["annual_pct_per_gross"], r["maxdd_bps"], r["worst_day"], r["worst_day_bps"], r["worst_month"], r["n_neg_months"], r["n_months"], r["w3_king_mean"], "NEG" if r["negative_year"] else ""))
# --- contrasts (frozen), per-contrast RNG sub-stream
CON = [("A1", "A0"), ("A2", "A0"), ("A3", "A0"), ("A1", "A2"), ("A1", "A3"), ("A1s", "A0"), ("A1s", "A1"), ("A1e", "A1"), ("A1e", "A0")]   # A1e = king clock E-version (PREREG_king_clock_E)
# ★ review b0a573a1 R4: required inputs + coverage are PROGRAM CONDITIONS. Every arm a contrast needs must be loaded for both seeds and both seats, and every
#   loaded arm must cover the whole frozen window as an EXACT 4h grid (round 3: identical time set, no duplicates/gaps); otherwise exit 2. JUDGE_ALLOW_PARTIAL=1 only for exploration.
_need = [(a, seat, s) for pair in CON for a in pair for seat in ("dyn", "fix") for s in ("42", "2027")]
_miss = sorted({"_".join(k) for k in _need if k not in ARMS})
_cov = {"_".join(k): int(((ARMS[k][0] >= FROZEN[0]) & (ARMS[k][0] < FROZEN[1])).sum()) for k in ARMS}; _short = {k: v for k, v in _cov.items() if v != N_FROZEN}
out["required_arms_missing"] = _miss; out["frozen_coverage"] = _cov; out["n_frozen_expected"] = N_FROZEN
if (_miss or _short or _axis_bad) and not PARTIAL:
    print("JUDGE_REFUSED missing arms:", _miss, "| frozen-window coverage !=", N_FROZEN, ":", _short, "| frozen axis not an exact shared 4h grid:", _axis_bad, flush=True); sys.exit(2)
print("\n== CONTRASTS (frozen 2025-03-01→2026-08-10 20Z; paired per anchor; UTC-day block bootstrap 2000; rng [20260905, k]) ==")
print("%-10s %-4s %-5s %9s %22s %6s | %s" % ("contrast", "seat", "seed", "Δ bps", "CI95", "P>0", "levels base -> arm"))
for ci, (a, b) in enumerate(CON):
    for seat in ("dyn", "fix"):
        for s in ("42", "2027"):
            if (a, seat, s) not in ARMS or (b, seat, s) not in ARMS: continue
            ta, ga, _ = ARMS[(a, seat, s)]; tb, gb, _ = ARMS[(b, seat, s)]; assert np.array_equal(ta, tb), "axis mismatch"
            m = (ta >= FROZEN[0]) & (ta < FROZEN[1]); d = (ga - gb)[m]; rng = np.random.default_rng([20260905, ci]); lo, hi, p = boot(d, ta[m] // 86400, rng)
            out["contrasts"][f"{a}-{b}|{seat}|s{s}"] = {"delta": float(d.mean()), "ci95": [lo, hi], "p_gt0": p, "n": int(m.sum()), "level_base": float(gb[m].mean()), "level_arm": float(ga[m].mean()), "rng": [20260905, ci]}
            print("%-10s %-4s %-5s %+9.4f [%+8.4f,%+8.4f] %6.3f | %+7.4f -> %+7.4f" % (f"{a}-{b}", seat, s, d.mean(), lo, hi, p, gb[m].mean(), ga[m].mean()))
_ref_ts = next(iter(ARMS.values()))[0] if ARMS else np.array([], dtype=np.int64)
_n_ext_more = int(((_ref_ts >= EXT[0]) & (_ref_ts < EXT[1])).sum() - ((_ref_ts >= FROZEN[0]) & (_ref_ts < FROZEN[1])).sum())
out["n_extended_more_anchors"] = _n_ext_more
print(f"\n== SECONDARY (AMENDMENT 4): same contrasts on the EXTENDED window 2025-03-01→2026-08-31 20Z (repaired August included; {_n_ext_more} more anchors than the frozen window in the loaded arms; NOT the verdict window) ==")
out["contrasts_extended"] = {}
for ci, (a, b) in enumerate(CON):
    for seat in ("dyn", "fix"):
        for s in ("42", "2027"):
            if (a, seat, s) not in ARMS or (b, seat, s) not in ARMS: continue
            ta, ga, _ = ARMS[(a, seat, s)]; tb, gb, _ = ARMS[(b, seat, s)]; m = (ta >= EXT[0]) & (ta < EXT[1]); d = (ga - gb)[m]; rng = np.random.default_rng([20260905, 100 + ci]); lo, hi, p = boot(d, ta[m] // 86400, rng)
            out["contrasts_extended"][f"{a}-{b}|{seat}|s{s}"] = {"delta": float(d.mean()), "ci95": [lo, hi], "p_gt0": p, "n": int(m.sum()), "level_base": float(gb[m].mean()), "level_arm": float(ga[m].mean()), "rng": [20260905, 100 + ci]}
            print("%-10s %-4s %-5s %+9.4f [%+8.4f,%+8.4f] %6.3f | %+7.4f -> %+7.4f  (n=%d)" % (f"{a}-{b}", seat, s, d.mean(), lo, hi, p, gb[m].mean(), ga[m].mean(), m.sum()))
print("\n== VERDICTS (frozen §4: (A) both seeds point>0 & CI lower>0; (B) both CI upper<0; (C) otherwise UNDECIDED = '未过否决线', never '不劣') ==")
if PARTIAL: print("   ★ EXPLORATORY RUN (JUDGE_ALLOW_PARTIAL=1): inputs incomplete — no verdict is issued, nothing can PROMOTE")
if not _eligible_arms: print("   ★ eligibility = informational (no arm has a bound export-gate PASS): an (A) reads as INFO, never PROMOTE")
else: print(f"   ★ eligible arms (bound export-gate PASS): {_eligible_arms} — only THEIR (A) cells may read PROMOTE")
for a, b in CON:
    for seat in ("dyn", "fix"):
        r = [out["contrasts"].get(f"{a}-{b}|{seat}|s{s}") for s in ("42", "2027")]
        if any(x is None for x in r): continue
        if PARTIAL:
            v = "EXPLORATORY (partial inputs; no verdict issued)"
        else:
            v = "(A) PROMOTE" if all(x["delta"] > 0 and x["ci95"][0] > 0 for x in r) else ("(B) REJECT" if all(x["ci95"][1] < 0 for x in r) else "(C) UNDECIDED")
            if v == "(A) PROMOTE" and a not in _eligible_arms: v = f"(A) INFO — no bound export-gate PASS for arm {a}: informational only, no promotion"
        out["verdicts"][f"{a}-{b}|{seat}"] = v; print(f"  {a}-{b:3s} {seat}: {v}")
out["utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); _jo = os.environ.get("JUDGE_OUT", "/workspace/review_scratch/v4_gates/JUDGE_v4.json"); os.makedirs(os.path.dirname(_jo), exist_ok=True); json.dump(out, open(_jo, "w"), indent=1); print("JUDGE_V4_DONE")
sys.exit(0)
