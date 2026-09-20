#!/usr/bin/env python3
"""at_prerun.py — BEFORE-RUNNING gate for the 2026-vs-history attribution (PREREG …2026-09-20, sha 40a72981).

It verifies every pinned input by sha256, checks the structural facts the later devices assume (they are
facts about the FILE LAYOUT, not results), and only then writes the frozen run configuration
RUN_CONFIG_attrib_2026-09-20.json, which carries every definition, bin edge, window and hypothesis of the
family. Any failed check ⇒ VERDICT REFUSED, no config is written, nothing downstream may run.

usage: python at_prerun.py <ENV_WHITELIST_CSV> <OUT_DIR>
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import at_lib as L

T0 = time.time()
ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{L.ROOT}/receipts"
os.makedirs(OUT, exist_ok=True)
chk = L.Checks(T0)
rec = L.rec_head("at_prerun.py", sys.argv)
rec["prereg"] = {"doc": "docs/PREREG_attribution_2026_vs_history_2026-09-20.md", "commit": "174250770",
                 "sha256": "40a72981"}

extra_env = sorted(set(rec["env"]) - ENV_OK)
chk("env.whitelist", not extra_env, {"whitelist": sorted(ENV_OK), "extra": extra_env})

rec["inputs"] = L.verify_pins(chk)
if chk.fails:
    L.write_receipt(rec, chk, f"{OUT}/AT_PRERUN.json", {"VERDICT_NOTE": "REFUSED before any structural check"})
    print("AT_PRERUN VERDICT=REFUSED failed=%s" % chk.fails, flush=True)
    sys.exit(3)

# ── 1. the extension target / record files are a strict bitwise extension of the main ones ───────────
TM = np.load(L.PINS["TARGETS_A0_MAIN"][0], allow_pickle=True)
TX = np.load(L.PINS["TARGETS_A0_EXT"][0], allow_pickle=True)
am, ax = TM["anchor"].astype(np.int64), TX["anchor"].astype(np.int64)
nm = len(am)
chk("targets.ext_is_extension", len(ax) > nm and np.array_equal(ax[:nm], am), {"n_main": nm, "n_ext": len(ax)})
for pref in ("scaled", "lit", "scaled_l333_only"):
    k_ok = np.array_equal(TX[pref + "_kind"][:nm], TM[pref + "_kind"])
    o_ok = np.array_equal(TX[pref + "_off"][:nm + 1], TM[pref + "_off"])
    n_nz = int(TM[pref + "_off"][nm])
    v_ok = (np.array_equal(TX[pref + "_idx"][:n_nz], TM[pref + "_idx"])
            and np.array_equal(TX[pref + "_val"][:n_nz].view(np.uint64), TM[pref + "_val"].view(np.uint64)))
    chk(f"targets.prefix_bitwise.{pref}", bool(k_ok and o_ok and v_ok), {"kind": bool(k_ok), "off": bool(o_ok), "csr": bool(v_ok), "nnz": n_nz})

PM = np.load(L.PINS["P3VEC_A0_MAIN"][0], allow_pickle=True)
PX = np.load(L.PINS["P3VEC_A0_EXT"][0], allow_pickle=True)
chk("p3.anchor_axis_equals_targets", np.array_equal(PM["anchor"].astype(np.int64), am))
for pref in ("king", "kc", "fc", "king_file", "combo"):
    n_nz = int(PM[pref + "_off"][nm])
    ok = (np.array_equal(PX[pref + "_off"][:nm + 1], PM[pref + "_off"])
          and np.array_equal(PX[pref + "_idx"][:n_nz], PM[pref + "_idx"])
          and np.array_equal(PX[pref + "_val"][:n_nz].view(np.uint64), PM[pref + "_val"].view(np.uint64)))
    chk(f"p3.prefix_bitwise.{pref}", bool(ok), {"nnz": n_nz})
n_pm = int(PM["pm_off"][nm])
chk("p3.prefix_bitwise.pm", bool(np.array_equal(PX["pm_off"][:nm + 1], PM["pm_off"]) and np.array_equal(PX["pm"][:n_pm], PM["pm"])), {"nnz": n_pm})

# ── 2. one symbol axis for every table ───────────────────────────────────────────────────────────────
SY = [str(s) for s in np.load(L.PINS["UNIVERSE_EXT"][0], allow_pickle=True)["symbols"]]
PME = np.load(L.PINS["PRICE_META"][0], allow_pickle=True)
LED = np.load(L.PINS["LEDGER_SPLICED"][0], allow_pickle=True)
PAN = np.load(L.PINS["PANEL_X0918"][0], allow_pickle=True)
CZ = np.load(L.PINS["CACHE_X0918R"][0], allow_pickle=True)
chk("symbols.n", len(SY) == L.NW, {"n": len(SY)})
for nmz, arr in (("price_meta", PME["symbols"]), ("ledger", LED["symbols"]), ("panel", PAN["symbols"]), ("cache", CZ["symbols"])):
    chk(f"symbols.equal.{nmz}", [str(s) for s in arr] == SY)
chk("cache.channels", [str(c) for c in CZ["ch"]] == ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"],
    [str(c) for c in CZ["ch"]])

# ── 3. grids: the price table, the cache and the panel all carry every anchor the run uses ───────────
AGG = np.load(L.PINS["AGG_A0"][0], allow_pickle=True)
A = AGG["A"].astype(np.int64)
chk("run.anchors", len(A) == 9139 and L.utc(A[0]) == "2022-06-30T00:00:00Z" and L.utc(A[-1]) == "2026-08-31T00:00:00Z",
    {"n": len(A), "first": L.utc(A[0]), "last": L.utc(A[-1])})
chk("run.anchors_subset_of_targets", bool(np.isin(A, ax).all()))
chk("run.anchor_step_4h", bool((np.diff(A) == L.H4).all()))
G = PME["grid"].astype(np.int64)
chk("price.grid_step_5m", bool((np.diff(G) == 300).all()), {"rows": len(G), "first": L.utc(G[0]), "last": L.utc(G[-1])})
grow = {int(t): i for i, t in enumerate(G)}
need = np.concatenate([A, A + L.H4])
chk("price.covers_every_anchor_and_exit", all(int(t) in grow for t in need),
    {"missing": int(sum(int(t) not in grow for t in need))})
CTS = CZ["ts"].astype(np.int64)
chk("cache.grid_step_5m", bool((np.diff(CTS) == 300).all()), {"rows": len(CTS), "first": L.utc(CTS[0]), "last": L.utc(CTS[-1])})
crow = {int(t): i for i, t in enumerate(CTS)}
chk("cache.covers_every_anchor", all(int(t) in crow for t in A))
chk("cache.bucket_alignment", all(crow[int(t)] % 48 == 0 for t in A[:200]),
    {"note": "anchor rows are multiples of 48 ⇒ a 24h window is exactly 6 aligned 48-row buckets"})
PTS = PAN["ts"].astype(np.int64)
prow = {int(t): i for i, t in enumerate(PTS)}
chk("panel.covers_every_anchor", all(int(t) in prow for t in ax[np.isin(ax, A)]))

# ── 4. the 32 fill paths are all present and are what the published table read ───────────────────────
paths = sorted(f for f in os.listdir(L.RUN_A0) if f.startswith("PATH_") and f.endswith(".npz"))
chk("run.32_paths", len(paths) == 32, {"n": len(paths)})
rec["path_sha256"] = {f: L.sha(f"{L.RUN_A0}/{f}") for f in paths}
Z0 = np.load(f"{L.RUN_A0}/{paths[0]}", allow_pickle=True)
chk("path.anchor_axis", np.array_equal(Z0["A"].astype(np.int64), A))
chk("path.cash_identity", float(np.abs(Z0["nav1"] - Z0["nav0"] - (Z0["price_trade"] + Z0["funding"] - Z0["fee"])).max()) < 1e-6,
    {"max_abs_usdt": float(np.abs(Z0["nav1"] - Z0["nav0"] - (Z0["price_trade"] + Z0["funding"] - Z0["fee"])).max())})

# ── 5. the producer records carry the seats the leg split needs ──────────────────────────────────────
P3 = json.load(open(L.PINS["P3JSON_A0_MAIN"][0]))
recs = P3["records"]
chk("p3json.n_records", len(recs) == nm, {"n": len(recs)})
idx_in_run = np.nonzero(np.isin(am, A))[0]
miss_meta = [i for i in idx_in_run if not (recs[i]["combo"].get("combo_meta") or {}).get("w3_masked")]
kinds = TM["scaled_kind"][idx_in_run]
miss_meta_combo = [i for i in miss_meta if int(TM["scaled_kind"][i]) == 2]
chk("p3json.w3_masked_present_on_every_combo_anchor", not miss_meta_combo,
    {"n_missing_any": len(miss_meta), "n_missing_on_kind2": len(miss_meta_combo)})
chk("p3json.kind_in_{1,2}", set(int(k) for k in kinds) <= {1, 2}, {"kinds": sorted(set(int(k) for k in kinds))})
chk("p3json.mid_seat_is_zero", all(abs(float((recs[i]["combo"]["combo_meta"])["w3_masked"][1])) < 1e-12 for i in idx_in_run if (recs[i]["combo"].get("combo_meta") or {}).get("w3_masked")),
    {"note": "w3_masked = [king, mid, fund]; mid is masked out over the whole window"})

# ── 6. the frozen configuration ──────────────────────────────────────────────────────────────────────
CFG = {
    "created_utc": L.utc(time.time()),
    "status": "FROZEN before any number of this stream; written by at_prerun.py after every check above passed",
    "prereg": rec["prereg"],
    "object": "certified production path = object B, arm A0, reading `scaled` (B-scaled, the baseline table's main reading)",
    "window": {"main": [L.utc(A[0]), L.utc(A[-1])], "n_anchors": int(len(A)),
               "extension_describe_only": ["2026-08-31T04:00:00Z", "2026-09-18T20:00:00Z"]},
    "units": "bps per anchor per unit TARGET gross (denominator gm·NAV(A), gm = 2.0) — the baseline table's unit",
    "layers": {"L1_realised": "simulator per-anchor cash, 32 fill paths, path mean (the only layer for NAV / Sharpe / drawdown / g)",
               "L2_paper": "target book reshaped as the executor reshapes it, marked to the certified price table + spliced funding ledger (the only layer that can be cut per name)",
               "reconciliation": "L2 − L1 reported per period in the same unit; never absorbed"},
    "paper_book": "pop = non-zero entries of the written `scaled` CSR row; v -= mean(v); v /= Σ|v| (legs.py 1e655daf reshape_after_withhold, redemean+rescale); pops / force_flat / clamps NOT modelled (they are execution and fall in L2−L1)",
    "leg_split": {"seats": "combo_meta.w3_masked = [king, mid(=0), fund] of P3.json; kind 1 (king file written) ⇒ φ_king=1, φ_fund=0, kc:=king_file, fc:=0",
                  "a_i": "φ_king·(kc_i − mean over pop_mix of kc)", "b_i": "φ_fund·(fc_i − mean over pop_mix of fc)",
                  "A1": "1e4·Σ(a_i/L)·x and 1e4·Σ(b_i/L)·x, L = Σ|a+b| — the MIX book (no FTRIM / EMA / band)",
                  "A2": "s_i = a_i/(a_i+b_i) if |a_i+b_i| ≥ 1e-12 else φ_king/(φ_king+φ_fund); 1e4·Σ s_i·W_i·x and 1e4·Σ(1−s_i)·W_i·x — sums to the traded book exactly",
                  "A2b": "A1 + named residual 1e4·Σ(W_i − (a_i+b_i)/L)·x = the reshaping (FTRIM / EMA / band / renormalisation)",
                  "disagreement_rule": "name every period with |A1_leg − A2_leg| > 0.05·max(|A1_total|, |A2_total|)"},
    "returns": "RET_i(E) = exp(P[row(E+4h),i] − P[row(E),i]) − 1 on price_full_raw_x0918r 23af32bd; out-of-life (outside [first_fin, last_fin]) is identically 0 and its weight share is reported",
    "funding": "FUNDPAID_i(E) = Σ rate_i over settlements with ft ∈ (E, E+4h] of the spliced ledger 073088e5; POSITIVE = the book pays when long",
    "fee_per_name": "fee_i(E) = realised L1 fee(E)·|ΔW_i|/Σ|ΔW_j| (ΔW against the previous anchor of the axis); Σ_i fee_i = the realised fee exactly",
    "net_per_name": "net_i = price_i − funding_paid_i − fee_i; realised g − Σ_i net_i = the execution residual, reported per period, never absorbed",
    "market_vs_selection": "ȳ(E) = equal-weight mean RET over the producer member list pm ∩ in-life; the priced set Q = in-life names; market_i = W_i·ȳ on Q, selection_i = W_i·(RET_i − ȳ) on Q, both 0 off Q; market + selection = price identically",
    "characteristics": {"source": "same channels and same missing-data handling as c0_chars.py f4c13d76",
                        "AGE": "(E − first cache bar with log_cnt finite and > 0)/86400, cache ch 4, x0918r 08bb2957; left-censored flagged",
                        "RN8": "panel f_fund_now·8/f_fund_iv (iv NaN or ≤0 → 8) at the anchor row, panel e5fcb419",
                        "MOM30": "exp(P[row(E)] − P[row(E−720h)]) − 1 on the certified price table (= Π(1+y4)−1 over 180 4h intervals, RAW), NaN unless in life over the whole 30 days; cross-checked against meta_newprod_v4 y4 and against panel f_mom_30d",
                        "LIQ": "log(Σ expm1(log_qv)·288/n) over the 288 bars closing in (E−24h, E], n = finite log_qv, NaN if n < 144 (cache ch 3)",
                        "TBF": "simple mean of cache ch 6 over the bars of that window with log_cnt > 0 and finite tbf, NaN if < 48",
                        "holefix": "INCL (filled bars used), c0's primary"},
    "groups": {name: list(bins) for name, bins in L.GROUP_SPECS},
    "group_rules": {"AGE": "fixed, left-closed: <90 | [90,180) | [180,365) | [365,730) | >=730 days",
                    "FUND": "fixed on RN8 in bp/8h: <=-10 | (-10,0) | [0,0.999) | [0.999,1.001] | (1.001,5] | >5",
                    "MOM30/LIQ/TBF": "per-anchor terciles inside the member set over finite values: q = np.quantile(v,[1/3,2/3]); L: v<q⅓; H: v>q⅔; M: the closed middle",
                    "DIR": "sign(W_i); W_i = 0 contributes nothing", "NA": "characteristic NaN"},
    "n_group_tests": int(L.N_GROUP_TESTS),
    "conditions": list(L.COND_NAMES),
    "conditions_from_g0": L.COND_FROM_G0,
    "conditions_extra_not_in_family": list(L.COND_EXTRA),
    "condition_labels": "the six from G0 use G0's own frozen LAB_EXCL (expanding-window terciles, 1,080-anchor warm-up); UBAR and TURN are labelled by the same rule re-implemented on this device's axis",
    "statistics": {"bootstrap": "moving-block on UTC days, non-circular, B = 10,000, block 5 days main (1 and 10 sensitivity), rng numpy.random.default_rng([20260920, k])",
                   "per_anchor_mean": "resampled as Σ(day sums)/Σ(day counts)",
                   "family": "22 group tests (2026 vs HIST mean net contribution) + 8 condition tests (top tercile g − bottom tercile g on FULL_RECIPE) = 30, Holm at 0.05",
                   "p": "two-sided centred p = (1 + #{|Δ*−Δ̂| ≥ |Δ̂|})/(B+1)",
                   "no_marks_on": ["§2-E", "§2-F", "§2-G"]},
    "periods": [{"name": n, "from": a, "to": b, "partial_recipe": p} for n, a, b, p in L.PERIODS],
    "extremes": {"tail": "top and bottom 1 % of anchors by REALISED per-anchor g inside FULL_RECIPE (6,948 ⇒ 69 + 69)",
                 "detail": "written book kind, both legs, top-10 names by |paper net|, the anchor's 8 conditions + TREND, stop / halt / flatten counts",
                 "runs": "also the extreme 3-consecutive-anchor and 24h (6-anchor) cumulative segments"},
    "forbidden": ["changing a bin edge, a window, a group or a definition after seeing a number",
                  "any per-arm execution outcome (blind protocol) — arm counts only",
                  "any forward claim, any statement that a regime has ended or will persist",
                  "reusing the numbers or conclusions of RESULT_c0_attribution / RESULT_regime_g0 (old research book)"],
    "inputs": rec["inputs"],
    "path_sha256": rec["path_sha256"],
}
if not chk.fails:
    p = f"{L.ROOT}/RUN_CONFIG_attrib_2026-09-20.json"
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(CFG, f, indent=1, sort_keys=False, default=str)
    os.replace(tmp, p)
    rec["config_written"] = {"path": p, "sha256": L.sha(p)}

v = L.write_receipt(rec, chk, f"{OUT}/AT_PRERUN.json", {"peak_rss_gb": L.rss_gb()})
print("AT_PRERUN VERDICT=%s checks=%d failed=%s" % (v, len(chk.rows), chk.fails), flush=True)
sys.exit(0 if v == "PASS" else 3)
