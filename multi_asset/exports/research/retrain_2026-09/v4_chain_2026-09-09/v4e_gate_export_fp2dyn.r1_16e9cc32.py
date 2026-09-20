"""v4e_gate_export_v2.py — PROPOSED replacement for the physical BUNDLE_export gate (r20 gate closure, 2026-09-12).

WHY A v2. The independent reviewer (codex_uplift_review_2026-09-12/contracts/RESULT.md §1) showed with the ORIGINAL gate
(v4e_gate_export.py, sha f814c728…) and the real require(): a PASS string from the WRONG gate is accepted (E7 read a boolean);
a book built with a different COST model or an injected knob is accepted (E6 pinned 8 of the device's 27 knobs); all-zero W and
a non-finite pnl are accepted (E5 checked shapes, not content); and require() stays PASS after the SHIPPED prediction file is
mutated (the 11 registered inputs did not include the bundle). r20 reproduced all six probes (RECEIPT_probe_original_gate.json).

WHAT v2 BINDS (reviewer §4, accepted by the lead):
  (a) the shipped bundle's FULL closure — MANIFEST + every file it lists is a registered input (bundle/<file>), so require()
      re-hashes the exported predictions, model, config, ledgers;
  (b) the signal-gate RECEIPT as an identity, not a word: approved gate name + approved gate-source sha + arm + the FEMAT it
      hashed (equal to the FEMAT the books injected, re-hashed now) + PASS RE-DERIVED from its recorded statistics against its
      recorded thresholds, which must equal the approved thresholds;
  (c) cost model and intervention parameters: COSTB_JSON file sha + resolved COST_B tiers, UMASK_NPZ sha, and EVERY device knob
      (27-key config_json, exact key set, pinned values) equal to the approved baseline's;
  (d) the approved baseline identity and the thresholds themselves come from the FROZEN CONTRACT block
      gates.BUNDLE_export.approved_baseline (never from the caller's env; env overrides of the guard band / N_FROZEN are refused).
  CONTENT gates on the four judged books, all exact identities of the replay device (verified on the genuine A0/A1/A3/XIB books to
  <=1.5e-8, r20 RESULT §3): sum|W_t| = gross_total_t; sum|W_t - W_{t-1}| = turnover_t (row 0: sum|W_0|); sum W_t / sum|W_t| =
  netlong_t; net = pnl - carry - cost and net_ex = pnl_ex - carry_ex - cost_ex to 1e-9; every rec/W value finite; 0 < gross <= 1;
  cost > 0 and cost_ex > 0 on every frozen anchor; cost <= turnover * max tier rate; per-anchor gross ratio to the approved
  baseline book (same seat, same seed) inside a band, median inside a tighter band.

CHECK NAMES (every one a named boolean in receipt["checks"]; a FAIL lists them in failed_checks):
  E0_contract_baseline  E1_manifest  E2_config  E2b_pins_identity  E3_ic_gates  E4_baseline_guard  E5_books_shape
  E6_books_config  E7_signal_receipt  E8_books_content  E9_gross_band_vs_baseline
E1–E4 are the ORIGINAL gate's code, verbatim except that the band / N_FROZEN / IC tolerances are read from the contract block.

TWO MODES (same env, same derivation of every path — the receipt is never the source of a path):
  python v4e_gate_export_v2.py                    gate:    run every check, finalize() the receipt (exit 0 iff PASS, else 3)
  python v4e_gate_export_v2.py require <receipt>  require: v4_gate_common.require over the FULL floor (identity, approval, every
                                                  registered input re-hashed) AND re-run every content gate from the files on disk.
                                                  E3/E4 are sha-bound (PRED/META/BASE/PANEL) and re-computed only when
                                                  REQUIRE_RECOMPUTE_GUARDS=1. Exit 0 iff everything holds, else 3.
ENV (all explicit, no silent default selects data — E-0826-D):
  EXPORT_ARM BUNDLE_OUT BUNDLE_FEA BUNDLE_META BUNDLE_BASE EXPORT_PANEL BUNDLE_CACHE FUND_AUG LIVE_PINS JUDGE_HC V4CHAIN_DIR
  SIGNAL_RECEIPT EXPORT_GATE_OUT  [require mode: REQUIRE_OUT REQUIRE_RECOMPUTE_GUARDS]
  BUNDLE_GUARD_LO / BUNDLE_GUARD_HI / JUDGE_N_FROZEN, if present, must EQUAL the contract values or the gate refuses (exit 2).
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
from scipy.stats import rankdata, spearmanr

GATE = "BUNDLE_export"
REQ = ["EXPORT_ARM", "BUNDLE_OUT", "BUNDLE_FEA", "BUNDLE_META", "BUNDLE_BASE", "EXPORT_PANEL",
       "BUNDLE_CACHE", "FUND_AUG", "LIVE_PINS", "JUDGE_HC", "V4CHAIN_DIR", "SIGNAL_RECEIPT", "EXPORT_GATE_OUT"]
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}
# the replay device's self-reported config (w10_health.py sha 8684d9a9…, _CFG at L51-54): EXACT key set, nothing more, nothing less
DEVICE_CFG_KEYS = ["COSTB_JSON", "COST_B", "UMASK_SCOPE", "REF_SKIP", "KMOD_F10", "KMOD_L", "KMOD_AGREE", "SEATF10", "KTAIL", "KMOD", "SEATNET",
                   "FUNDSCALE", "FEMAT_NPZ", "SLOW_NPY", "W3FIX", "MEMBERS_TOPN", "TRADE_TOPN", "FTRIM", "UMASK_NPZ", "LOOK", "WRULE", "CAL",
                   "LEGS", "PHI", "FSEED", "FPRED", "HEALTH"]
PER_CELL_KEYS = {"FSEED", "W3FIX"}                                   # differ by construction across the four cells
FILE_KEYS = {"COSTB_JSON", "COST_B", "UMASK_NPZ", "SLOW_NPY", "FEMAT_NPZ", "FPRED", "HEALTH"}   # bound by file sha / device sha, not by value
FROZEN_PARAMS = {"NTOP": 400, "cov_min": 0.95, "vol_min": 1e-4, "qv4h_min": 2.5e5, "cap_mult": 2.5,
                 "alpha": 0.1, "band": 2.5e-4, "msharpe_look": 900, "fund_caliber": "v1 normfix HL3d",
                 "carry": "rate*4/iv", "cost_scen": "b", "sel_min": 80, "anchor_offset_min": 6}
AB_REQUIRED = ["device_sha256", "costb_json_sha256", "costb_tiers", "umask_npz_sha256", "live_pins_sha256", "bundle_base_sha256",
               "baseline_arm", "baseline_books_sha256", "book_env", "thresholds", "signal_gates"]
TH_REQUIRED = ["guard_band", "n_frozen", "frozen_window_utc", "ic_tol", "sharpe_claim_tol", "identity_tol", "w_gross_tol", "turnover_tol",
               "netlong_tol", "gross_max", "gross_ratio_band", "gross_ratio_median_band"]
SEATS = (("dyn", "42"), ("dyn", "2027"), ("fix", "42"), ("fix", "2027"))
# ★ fp2dyn VARIANT (2026-09-17, user word「线上的策略都是动态席位, 回测应该也是动态的」; PROPOSED5): every book is still LOADED, HASHED and shape-checked
#   (E5/E6/E7 unchanged, the 28-name input floor unchanged), but the BOOK-CONTENT verdicts E8/E9 fold only the IN-SERVICE seat(s) into the gate
#   verdict — NARROWED after independent review round 4: for a seat outside CHECK_SEATS only the two invariants the tradable regime breaks are
#   informational (the K6 gross CEILING gt ≤ gross_max; the E9 gross-ratio band) — K6 positivity (frozen-window gross > 0, gross ≥ 0) stays hard. Its ACCOUNTING IDENTITIES (K1 Σ|W|=gross, K2 turnover, K3 netlong, K4 net identity,
#   K7 cost bounds) and the E9 BASELINE IDENTITY (baseline book sha approved, axis covers the frozen window) still fold into the verdict: a
#   diagnostic book must still be an honest book. This is an after-the-fact change of the gate's acceptance domain (old file: v2 FAIL, variant
#   PASS), not a mere identity correction. The fix seat is a September control (E-0902-D: the replay's dynamic
#   seat then did not track live); in the v4 chain the replay's dynamic seat tracks the live seat (0.32–0.37 vs 0.36–0.38, AMENDMENT 11).
CHECK_SEATS = {"dyn"}


def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))


def sha256_file(p, chunk=16 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""): h.update(b)
    return h.hexdigest()


def refuse(msg):
    print("EXPORT_GATE_REFUSED: " + msg, flush=True); sys.exit(2)


def parse_utc(s):
    t = time.strptime(s, "%Y-%m-%dT%H:%MZ"); return calendar.timegm(t)


# ----------------------------------------------------------------------------------------------------------------------- setup
def read_env():
    E = {}
    for k in REQ:
        v = os.environ.get(k)
        if not v: refuse(f"env {k} not set (E-0826-D: a gate that guesses its inputs binds nothing)")
        E[k] = v
    return E


def load_ab(E):
    """The approved baseline + thresholds block of the FROZEN contract beside v4_gate_common. Refuse if absent or incomplete."""
    sys.path.insert(0, E["V4CHAIN_DIR"])
    import v4_gate_common as gc  # noqa: E402
    c, err = gc.load_contract()
    if c is None: refuse(f"frozen contract: {err}")
    g = (c.get("gates") or {}).get(GATE) or {}
    ab = g.get("approved_baseline")
    if not isinstance(ab, dict): refuse(f"contract gates.{GATE}.approved_baseline missing: the approved baseline identity and thresholds must be FROZEN there, never supplied by the caller")
    miss = [k for k in AB_REQUIRED if k not in ab]
    if miss: refuse(f"contract approved_baseline incomplete, missing {miss}")
    th = ab["thresholds"]; miss = [k for k in TH_REQUIRED if k not in th]
    if miss: refuse(f"contract approved_baseline.thresholds incomplete, missing {miss}")
    # env overrides of frozen thresholds are refused unless identical (the reviewer: 'recording the chosen threshold is not checking the approved one')
    for k, v in (("BUNDLE_GUARD_LO", th["guard_band"][0]), ("BUNDLE_GUARD_HI", th["guard_band"][1]), ("JUDGE_N_FROZEN", th["n_frozen"])):
        ev = os.environ.get(k)
        if ev is not None and abs(float(ev) - float(v)) > 1e-12: refuse(f"env {k}={ev} disagrees with the frozen contract value {v}: thresholds are not the caller's to set")
    fw = th["frozen_window_utc"]; frozen = (parse_utc(fw[0]), parse_utc(fw[1]) + 1)
    return gc, c, ab, th, frozen


def derive_paths(E, ab):
    """Every path the gate reads, derived from env + the frozen contract — the receipt is never a source of paths."""
    HC = E["JUDGE_HC"]; ARM = E["EXPORT_ARM"]; base_arm = ab["baseline_arm"]
    books = {f"book_{seat}_s{s}": f"{HC}/dev_v4/probe_artifacts/w10_ablation_series_V4_{ARM}_{seat}_s{s}.npz" for seat, s in SEATS}
    bases = {f"base_{seat}_s{s}": f"{HC}/dev_v4/probe_artifacts/w10_ablation_series_V4_{base_arm}_{seat}_s{s}.npz" for seat, s in SEATS}
    return books, bases


class Ctx:
    def __init__(self, E):
        self.E = E; self.gc, self.contract, self.ab, self.th, self.frozen = load_ab(E)
        self.books, self.bases = derive_paths(E, self.ab)
        self.R = {"arm": E["EXPORT_ARM"], "env": {k: E[k] for k in REQ}, "contract_path": self.gc.CONTRACT_PATH,
                  "contract_sha256": sha256_file(self.gc.CONTRACT_PATH), "contract_schema": self.contract.get("contract_schema"),
                  "approved_baseline_used": {k: self.ab[k] for k in ("device_sha256", "costb_json_sha256", "umask_npz_sha256", "live_pins_sha256", "bundle_base_sha256", "baseline_arm")},
                  "thresholds_used": self.th, "checks": {}}
        self.fails = []; self.inputs = {}; self.OUT = E["BUNDLE_OUT"]
        self.cfg = {}; self.femat = None; self.B = {}; self.BASE = {}; self.MT = None; self.PRED = None

    def chk(self, name, ok, detail):
        self.R["checks"][name] = {"ok": bool(ok), **detail}
        print(("  OK   " if ok else "  FAIL ") + name + " " + json.dumps(detail, default=str)[:400], flush=True)
        if not ok: self.fails.append(name)
        return bool(ok)


# --------------------------------------------------------------------------------------------------------------- checks
def E0_contract_baseline(cx):
    ab = cx.ab; th = cx.th; ok = True; why = []
    hex64 = lambda s: isinstance(s, str) and len(s) == 64 and all(ch in "0123456789abcdef" for ch in s)
    for k in ("device_sha256", "costb_json_sha256", "umask_npz_sha256", "live_pins_sha256", "bundle_base_sha256"):
        if not hex64(ab[k]): ok = False; why.append(f"{k} not a sha256")
    if sorted(ab["baseline_books_sha256"]) != sorted(f"{seat}_s{s}" for seat, s in SEATS) or not all(hex64(v) for v in ab["baseline_books_sha256"].values()):
        ok = False; why.append("baseline_books_sha256 must name the four cells with sha256 values")
    if not (isinstance(ab["costb_tiers"], list) and len(ab["costb_tiers"]) == 3 and all(len(t) == 3 for t in ab["costb_tiers"])): ok = False; why.append("costb_tiers must be 3 tiers of (maker,taker,share)")
    if not (isinstance(th["guard_band"], list) and len(th["guard_band"]) == 2 and th["guard_band"][0] < th["guard_band"][1]): ok = False; why.append("guard_band malformed")
    if not (th["gross_ratio_band"][0] < 1 < th["gross_ratio_band"][1] and th["gross_ratio_median_band"][0] < 1 < th["gross_ratio_median_band"][1]): ok = False; why.append("gross bands must bracket 1")
    need_env = set(DEVICE_CFG_KEYS) - PER_CELL_KEYS - FILE_KEYS
    if set(ab["book_env"]) != need_env: ok = False; why.append(f"book_env must pin exactly {sorted(need_env)}; got {sorted(ab['book_env'])}")
    cx.inputs["eligibility_contract"] = cx.gc.CONTRACT_PATH
    return cx.chk("E0_contract_baseline", ok, {"why": why, "contract_sha256": cx.R["contract_sha256"]})


def E1_manifest(cx):
    OUT = cx.OUT; mp = f"{OUT}/MANIFEST.json"
    if not os.path.exists(mp): return cx.chk("E1_manifest", False, {"why": "MANIFEST.json missing"})
    man = json.load(open(mp)); onfile = sorted(f for f in os.listdir(OUT) if f != "MANIFEST.json")
    bad = {f: "missing" for f in man if not os.path.exists(f"{OUT}/{f}")}
    for f in man:
        if f in bad: continue
        h = sha256_file(f"{OUT}/{f}")
        if h != man[f]: bad[f] = f"{h[:12]} != manifest {str(man[f])[:12]}"
    extra = [f for f in onfile if f not in man]
    cx.inputs["bundle_manifest"] = mp                                      # (a) the FULL closure is registered: manifest + every listed file
    for f in man: cx.inputs[f"bundle/{f}"] = f"{OUT}/{f}"
    return cx.chk("E1_manifest", not bad and not extra, {"n_files": len(man), "mismatched": bad, "unlisted_files": extra})


def E2_config(cx):
    E = cx.E; cp = f"{cx.OUT}/config.json"
    if not (os.path.exists(cp) and os.path.exists(E["LIVE_PINS"])): return cx.chk("E2_config", False, {"why": "config.json or LIVE_PINS missing"})
    cfg = json.load(open(cp)); pins = json.load(open(E["LIVE_PINS"])); cx.cfg = cfg
    pdiff = {k: [cfg.get("params", {}).get(k), v] for k, v in FROZEN_PARAMS.items() if cfg.get("params", {}).get(k) != v}
    cx.chk("E2_config", (not pdiff) and cfg.get("keep_names") == pins["keep_names"] and cfg.get("symbols_live") == pins["symbols_live"],
           {"param_diffs": pdiff, "keep_names_equal": cfg.get("keep_names") == pins["keep_names"],
            "symbols_live_equal": cfg.get("symbols_live") == pins["symbols_live"], "n_live": len(pins["symbols_live"])})
    # (d) the reference files the caller names must BE the approved ones (reviewer: BUNDLE_BASE was the caller's choice)
    sp_ = sha256_file(E["LIVE_PINS"]); sb = sha256_file(E["BUNDLE_BASE"]) if os.path.exists(E["BUNDLE_BASE"]) else None
    return cx.chk("E2b_pins_identity", sp_ == cx.ab["live_pins_sha256"] and sb == cx.ab["bundle_base_sha256"],
                  {"live_pins_sha256": sp_, "approved": cx.ab["live_pins_sha256"], "bundle_base_sha256": sb, "approved_base": cx.ab["bundle_base_sha256"]})


def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]


def e3_ic(PRED, MT):
    """Fold ICs re-derived from the shipped pinned predictions (original E3, verbatim)."""
    E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
    yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); ic = {}
    for Y in (2024, 2025, 2026):
        ics = []
        for a in np.nonzero(yrs == Y)[0]:
            m = members[a]; okm = np.isfinite(y4[a, m])
            if okm.sum() < 30: continue
            ics.append(sp(PRED[a, m[okm]], y4[a, m[okm]]))
        ic[Y] = float(np.nanmean(ics)) if ics else float("nan")
    return ic


def E3_ic_gates(cx):
    E = cx.E; MT = np.load(E["BUNDLE_META"], allow_pickle=True); cx.MT = MT
    PRED = np.load(f"{cx.OUT}/slow_pred_pinned.npy"); cx.PRED = PRED; BASE = json.load(open(E["BUNDLE_BASE"]))
    ic = e3_ic(PRED, MT); tol = {int(k): float(v) for k, v in cx.th["ic_tol"].items()}
    dd = {Y: float(ic[Y] - float(BASE["ic"][str(Y)])) for Y in ic}
    return cx.chk("E3_ic_gates", all(np.isfinite(dd[Y]) and abs(dd[Y]) <= tol[Y] for Y in dd),
                  {"recomputed_ic": {str(k): round(v, 5) for k, v in ic.items()}, "base_ic": BASE["ic"],
                   "delta": {str(k): round(v, 5) for k, v in dd.items()}, "tolerance": {str(k): v for k, v in tol.items()},
                   "provenance_claimed": {k: cx.cfg.get("provenance", {}).get(k) for k in ("fold_ic_2024", "fold_ic_2025", "pinned_ic2026")}})


def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan); n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out


def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t


def e4_sharpe(PRED, MT, PW):
    """Block (2) of pod_export_bundle_v4.py re-run from the shipped pinned predictions (original E4, verbatim). Returns (sharpe_2024on, n_anchors, mean_net)."""
    E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]; nA = len(E_ts)
    pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
    R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]; FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
    NW = 829
    COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
    LR = {leg: [] for leg in ("king", "rev24", "fund")}; idx = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]; sc = {"king": PRED[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
        ok = np.isfinite(y4[i, m])
        for leg in LR:
            z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
            g = np.abs(z).sum()
            LR[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
        idx.append(i)
    LRa = {k: np.array(v) for k, v in LR.items()}; pos = {int(i): p for p, i in enumerate(idx)}

    def msharpe_w(i_pos):
        look = 900
        if i_pos < look: return (1 / 3, 1 / 3, 1 / 3)
        sl = slice(i_pos - look, i_pos)
        r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
        shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
        return tuple(shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3))

    H = np.zeros(NW, np.float64); rec = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]; sc = {"king": PRED[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
        wk, wr, wf = msharpe_w(pos.get(int(i), 0))
        z = wk * np.nan_to_num(xz(sc["king"])) + wr * np.nan_to_num(xz(sc["rev24"])) + wf * np.nan_to_num(xz(sc["fund"]))
        ok = np.isfinite(y4[i, m]); qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        if sel.sum() < 80: continue
        w = np.where(sel, z, 0.0); w -= w[sel].mean(); g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g; capw = 2.5 / max(sel.sum(), 1); w = np.clip(w, -capw, capw)
        g2_ = np.abs(w).sum()
        if g2_ > 1e-9: w /= g2_
        tgt = np.zeros(NW); tgt[m] = w
        sm = H + 0.1 * (tgt - H); trade = sm - H
        sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H
        qvf = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48; trm = tier_of(qvf); tabs = np.abs(trade[m])
        cb = sum(tabs[trm == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))
        yv = np.nan_to_num(y4[i, m], nan=0.0); fnow = np.nan_to_num(FN[j, m], nan=0.0)
        ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
        car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4
        rec.append((int(E_ts[i]), float((sm[m] * yv).sum() * 1e4 - car - cb))); H = sm
    arr = np.array([n for t, n in rec if time.gmtime(t).tm_year >= 2024])
    sh = float(arr.mean() / (arr.std() + 1e-12) * np.sqrt(6 * 365)) if len(arr) else float("nan")
    return sh, len(rec), (float(arr.mean()) if len(arr) else float("nan"))


def E4_baseline_guard(cx):
    PW = np.load(cx.E["EXPORT_PANEL"], allow_pickle=True)
    sh, n, mn = e4_sharpe(cx.PRED, cx.MT, PW); GLO, GHI = cx.th["guard_band"]
    claimed = cx.cfg.get("provenance", {}).get("pinned_sharpe_full_b"); ctol = float(cx.th["sharpe_claim_tol"])
    return cx.chk("E4_baseline_guard", np.isfinite(sh) and (GLO <= sh <= GHI) and (claimed is None or abs(sh - float(claimed)) <= ctol),
                  {"recomputed_sharpe_2024on": round(sh, 4), "band": [GLO, GHI], "provenance_claimed": claimed, "n_anchors": n, "mean_net_bps": round(mn, 4)})


def load_book(p):
    A = np.load(p, allow_pickle=True); keys = set(A.files)
    rec = np.asarray(A["d30_n2_c42_rec"], float) if "d30_n2_c42_rec" in keys else None
    W = np.asarray(A["d30_n2_c42_W"], np.float64) if "d30_n2_c42_W" in keys else None
    cols = [str(x) for x in np.asarray(A["cols"]).ravel()] if "cols" in keys else None
    syms = [str(x) for x in np.asarray(A["symbols"]).ravel()] if "symbols" in keys else None
    cj = json.loads(str(A["config_json"])) if "config_json" in keys else None
    return {"rec": rec, "W": W, "cols": cols, "symbols": syms, "cfg": cj}


def E5_books_shape(cx):
    """Shape contract (original E5) + every rec value finite + symbols identical across books AND equal to the baseline books'."""
    F0, F1 = cx.frozen; N_FROZEN = int(cx.th["n_frozen"]); bk = {}; ax_ref = None; cx.B = {}; cx.BASE = {}
    for nm, p in sorted(cx.bases.items()):
        cx.inputs[nm] = p
        cx.BASE[nm] = load_book(p) if os.path.exists(p) else None
    base_syms = next((b["symbols"] for b in cx.BASE.values() if b and b["symbols"]), None)
    for nm, p in sorted(cx.books.items()):
        cx.inputs[nm] = p; d = {}
        if not os.path.exists(p): d["err"] = "missing"; d["ok"] = False; bk[nm] = d; continue
        b = load_book(p); cx.B[nm] = b; rec_, W, syms = b["rec"], b["W"], b["symbols"]
        d["has_rec"] = rec_ is not None; d["cols_ok"] = b["cols"] == COLS; d["symbols_present"] = syms is not None
        d["symbols_match_baseline"] = syms is not None and syms == base_syms
        d["rec_finite"] = bool(rec_ is not None and rec_.ndim == 2 and rec_.shape[1] == len(COLS) and np.isfinite(rec_).all())
        d["W_shape_ok"] = W is not None and rec_ is not None and W.ndim == 2 and W.shape == (rec_.shape[0], len(syms or []))
        d["W_finite"] = bool(W is not None and np.isfinite(W).all())
        ts_ = np.round(rec_[:, 0]).astype(np.int64) if rec_ is not None else np.array([], np.int64)
        a = ts_[(ts_ >= F0) & (ts_ < F1)]; d["n_frozen"] = int(len(a))
        d["frozen_axis_ok"] = bool(len(a) == N_FROZEN and (len(a) == 0 or int(a[0]) == F0) and (len(a) < 2 or (np.diff(a) == 14400).all()))
        if ax_ref is None: ax_ref = a
        d["frozen_axis_shared"] = bool(np.array_equal(a, ax_ref))
        d["ts_grid_4h"] = bool(len(ts_) > 1 and (np.diff(ts_) == 14400).all())
        d["ok"] = all(d[k] for k in ("has_rec", "cols_ok", "symbols_present", "symbols_match_baseline", "rec_finite", "W_shape_ok", "W_finite", "frozen_axis_ok", "frozen_axis_shared", "ts_grid_4h"))
        bk[nm] = d
    return cx.chk("E5_books_shape", all(v.get("ok") for v in bk.values()) and len(bk) == 4, {"n_baseline_symbols": len(base_syms or []), **bk})


def E6_books_config(cx):
    """(c) EVERY device knob pinned; exact key set; cost model + mask + king file + FEMAT bound by file; device sha; seat/seed per cell."""
    ab = cx.ab; per = {}; ok_all = True; shared = {k: set() for k in ("COSTB_JSON", "UMASK_NPZ", "SLOW_NPY", "FEMAT_NPZ")}
    for nm in sorted(cx.books):
        b = cx.B.get(nm); seat = nm.split("_")[1]; seed = nm.split("_s")[1]; d = {}
        cj = (b or {}).get("cfg")
        if not isinstance(cj, dict): d["err"] = "config_json missing/unreadable"; d["ok"] = False; per[nm] = d; ok_all = False; continue
        d["key_set_exact"] = sorted(cj) == sorted(DEVICE_CFG_KEYS)
        d["unknown_keys"] = sorted(set(cj) - set(DEVICE_CFG_KEYS)); d["missing_keys"] = sorted(set(DEVICE_CFG_KEYS) - set(cj))
        d["cfg_diffs"] = {k: [cj.get(k), v] for k, v in ab["book_env"].items() if cj.get(k) != v}
        d["seat_ok"] = (cj.get("W3FIX") == "0.21,0,0.79") if seat == "fix" else (cj.get("W3FIX") in (None, ""))
        d["seed_ok"] = str(cj.get("FSEED")) == seed
        d["device_sha_ok"] = (cj.get("HEALTH") or {}).get("device_sha256") == ab["device_sha256"]
        d["cost_tiers_ok"] = [list(map(float, t)) for t in (cj.get("COST_B") or [])] == [list(map(float, t)) for t in ab["costb_tiers"]]
        for k in shared: shared[k].add(cj.get(k))
        d["FPRED"] = cj.get("FPRED")
        d["ok"] = d["key_set_exact"] and not d["cfg_diffs"] and d["seat_ok"] and d["seed_ok"] and d["device_sha_ok"] and d["cost_tiers_ok"]
        ok_all &= d["ok"]; per[nm] = d
    files = {}
    for k, approved in (("COSTB_JSON", ab["costb_json_sha256"]), ("UMASK_NPZ", ab["umask_npz_sha256"]), ("SLOW_NPY", None), ("FEMAT_NPZ", None)):
        vals = shared[k]; f = {"one_value_for_all_cells": len(vals) == 1, "value": sorted(map(str, vals))}
        p = next(iter(vals)) if len(vals) == 1 else None
        if k == "FEMAT_NPZ" and p in (None, ""): f["exists"] = None; f["sha256"] = None; f["ok"] = f["one_value_for_all_cells"]; cx.femat = None
        else:
            f["exists"] = bool(p) and os.path.exists(p); f["sha256"] = sha256_file(p) if f["exists"] else None
            f["ok"] = f["one_value_for_all_cells"] and f["exists"] and (approved is None or f["sha256"] == approved)
            if approved is not None: f["approved"] = approved
            if f["exists"]: cx.inputs[{"COSTB_JSON": "costb_json", "UMASK_NPZ": "umask_npz", "SLOW_NPY": "slow_npy", "FEMAT_NPZ": "femat"}[k]] = p
            if k == "FEMAT_NPZ": cx.femat = p
        files[k] = f; ok_all &= f["ok"]
    # the cost json on disk must resolve to the pinned tiers too (a file whose sha matches but is read differently is impossible; a file that matches the tiers but not the sha is a different file)
    if files["COSTB_JSON"].get("exists"):
        try:
            cj_ = json.load(open(next(iter(shared["COSTB_JSON"])))); tiers = cj_["tiers"] if isinstance(cj_, dict) else cj_
            res = [[float(t["maker_bps"]), float(t["taker_bps"]), float(t["maker_share"])] if isinstance(t, dict) else [float(t[0]), float(t[1]), float(t[2])] for t in tiers]
            files["COSTB_JSON"]["resolves_to_approved_tiers"] = res == [list(map(float, t)) for t in ab["costb_tiers"]]
        except Exception as e:  # noqa: BLE001
            files["COSTB_JSON"]["resolves_to_approved_tiers"] = False; files["COSTB_JSON"]["resolve_error"] = f"{type(e).__name__}: {e}"
        ok_all &= files["COSTB_JSON"]["resolves_to_approved_tiers"]
    return cx.chk("E6_books_config", ok_all, {"files": files, **per})


def E7_signal_receipt(cx):
    """(b) if the books injected a FEMAT, the signal-gate receipt must be an IDENTITY: approved gate + approved source sha + this arm +
    the FEMAT it hashed == the FEMAT on disk now + PASS re-derived from recorded statistics against recorded thresholds == approved."""
    femat = getattr(cx, "femat", None); ab = cx.ab; E = cx.E
    if not femat:
        return cx.chk("E7_signal_receipt", True, {"applicable": False, "reason": "no FEMAT injection in any judged book; the king signal is bound by E3 (fold ICs re-derived from the shipped predictions)", "signal_receipt_consulted": False})
    d = {"applicable": True, "signal_receipt_path": E["SIGNAL_RECEIPT"], "signal_receipt_present": os.path.exists(E["SIGNAL_RECEIPT"])}
    if not d["signal_receipt_present"]: return cx.chk("E7_signal_receipt", False, d)
    cx.inputs["signal_receipt"] = E["SIGNAL_RECEIPT"]; d["signal_receipt_sha256"] = sha256_file(E["SIGNAL_RECEIPT"])
    try: sig = json.load(open(E["SIGNAL_RECEIPT"]))
    except Exception as e:  # noqa: BLE001
        d["err"] = f"unreadable: {type(e).__name__}: {e}"; return cx.chk("E7_signal_receipt", False, d)
    g = sig.get("gate"); spec = (ab["signal_gates"] or {}).get(g) if isinstance(g, str) else None
    d["gate"] = g; d["gate_approved"] = spec is not None
    ss = sig.get("self_sha256"); d["self_sha256"] = ss
    d["source_approved"] = bool(spec) and isinstance(ss, str) and ss in (spec.get("approved_source_sha256") or [])
    d["arm_bound"] = sig.get("arm") == E["EXPORT_ARM"]; d["receipt_arm"] = sig.get("arm")
    cur = sha256_file(femat); rec_f = (sig.get("inputs_sha256") or {}).get("femat")
    d["femat_sha_now"] = cur; d["femat_sha_in_receipt"] = rec_f; d["femat_bound"] = rec_f == cur
    stats = sig.get("stats") or {}; thr = sig.get("thresholds") or {}; ok_rule = bool(spec)
    if spec:
        rule = spec.get("thresholds") or {}
        d["thresholds_equal_approved"] = thr == rule
        re_eval = {}
        for k, v in rule.items():                       # threshold "<stat>_max" / "<stat>_min" bounds the recorded statistic "<stat>"; other keys must equal
            if k.endswith("_max"): s = stats.get(k[:-4]); re_eval[k] = isinstance(s, (int, float)) and not isinstance(s, bool) and s <= v
            elif k.endswith("_min"): s = stats.get(k[:-4]); re_eval[k] = isinstance(s, (int, float)) and not isinstance(s, bool) and s >= v
            else: re_eval[k] = stats.get(k) == v
        d["re_evaluated"] = re_eval; d["PASS_re_derived"] = all(re_eval.values()) and bool(re_eval)
        d["PASS_as_written"] = sig.get("PASS")
        ok_rule = d["thresholds_equal_approved"] and d["PASS_re_derived"]
    ok = d["gate_approved"] and d["source_approved"] and d["arm_bound"] and d["femat_bound"] and ok_rule
    return cx.chk("E7_signal_receipt", ok, d)


def E8_books_content(cx):
    """Exact identities of the replay device, re-derived from the shipped arrays (never from stored words)."""
    th = cx.th; F0, F1 = cx.frozen; per = {}; ok_all = True
    rate_max = max(fr * mk + (1 - fr) * tk for mk, tk, fr in [list(map(float, t)) for t in cx.ab["costb_tiers"]])
    for nm in sorted(cx.books):
        b = cx.B.get(nm); d = {}
        if not b or b["rec"] is None or b["W"] is None or not np.isfinite(b["rec"]).all() or not np.isfinite(b["W"]).all():
            d["err"] = "book missing or non-finite (see E5)"; d["ok"] = False; per[nm] = d; ok_all = False; continue
        R, W = b["rec"], b["W"]; ts = np.round(R[:, 0]).astype(np.int64); fm = (ts >= F0) & (ts < F1)
        sw = np.abs(W).sum(1); gt = R[:, C["gross_total"]]
        d["K1_sum_absW_eq_gross_maxdev"] = float(np.abs(sw - gt).max()); d["K1_ok"] = d["K1_sum_absW_eq_gross_maxdev"] <= th["w_gross_tol"]
        dW = np.abs(np.diff(W, axis=0)).sum(1); to = R[:, C["turnover"]]
        d["K2_turnover_eq_sum_absdW_maxdev"] = float(max(np.abs(dW - to[1:]).max() if len(to) > 1 else 0.0, abs(sw[0] - to[0])))
        d["K2_ok"] = d["K2_turnover_eq_sum_absdW_maxdev"] <= th["turnover_tol"]
        with np.errstate(all="ignore"): nl = np.where(sw > 0, W.sum(1) / np.where(sw > 0, sw, 1.0), 0.0)
        d["K3_netlong_eq_sumW_over_gross_maxdev"] = float(np.abs(nl - R[:, C["netlong"]]).max()); d["K3_ok"] = d["K3_netlong_eq_sumW_over_gross_maxdev"] <= th["netlong_tol"]
        i1 = R[:, C["net"]] - (R[:, C["pnl"]] - R[:, C["carry"]] - R[:, C["cost"]])
        i2 = R[:, C["net_ex"]] - (R[:, C["pnl_ex"]] - R[:, C["carry_ex"]] - R[:, C["cost_ex"]])
        d["K4_identity_net_maxdev"] = float(np.abs(i1).max()); d["K4_identity_net_ex_maxdev"] = float(np.abs(i2).max())
        d["K4_ok"] = max(d["K4_identity_net_maxdev"], d["K4_identity_net_ex_maxdev"]) <= th["identity_tol"]
        d["K6_gross_min_frozen"] = float(gt[fm].min()) if fm.any() else None; d["K6_gross_max_all"] = float(gt.max())
        d["K6_ok"] = bool(fm.any() and (gt[fm] > 0).all() and (gt <= th["gross_max"]).all() and (gt >= 0).all())
        cost = R[:, C["cost"]]; cex = R[:, C["cost_ex"]]
        d["K7_cost_pos_frozen"] = bool(fm.any() and (cost[fm] > 0).all() and (cex[fm] > 0).all())
        d["K7_cost_le_turnover_x_ratemax_violations"] = int((cost > to * rate_max * (1 + 1e-6) + 1e-9).sum()); d["K7_rate_max"] = rate_max
        d["K7_ok"] = d["K7_cost_pos_frozen"] and d["K7_cost_le_turnover_x_ratemax_violations"] == 0
        d["ok"] = all(d[k] for k in ("K1_ok", "K2_ok", "K3_ok", "K4_ok", "K6_ok", "K7_ok")); d["informational_seat"] = nm.split("_")[1] not in CHECK_SEATS
        d["K6_positivity_ok"] = bool(fm.any() and (gt[fm] > 0).all() and (gt >= 0).all()); d["K6_ceiling_ok"] = bool((gt <= th["gross_max"]).all())   # rev3 (review round 5): K6 split
        d["identities_ok"] = all(d[k] for k in ("K1_ok", "K2_ok", "K3_ok", "K4_ok", "K7_ok", "K6_positivity_ok"))                                 # only the CEILING is exempt for a non-checked seat
        ok_all &= (d["ok"] if not d["informational_seat"] else d["identities_ok"]); per[nm] = d   # fp2dyn (narrowed): non-checked seat — identities still fold, only K6 is informational
    return cx.chk("E8_books_content", ok_all, per)


def E9_gross_band_vs_baseline(cx):
    """(d) the approved baseline books (A0, same seat & seed) hash to the contract; per-anchor gross ratio inside the band, median inside the tighter band."""
    ab = cx.ab; th = cx.th; F0, F1 = cx.frozen; per = {}; ok_all = True; lo, hi = th["gross_ratio_band"]; mlo, mhi = th["gross_ratio_median_band"]
    for (seat, s) in SEATS:
        bn = f"base_{seat}_s{s}"; kn = f"book_{seat}_s{s}"; p = cx.bases[bn]; d = {"baseline_path": p}
        d["baseline_exists"] = os.path.exists(p); d["baseline_sha256"] = sha256_file(p) if d["baseline_exists"] else None
        d["baseline_sha_ok"] = d["baseline_sha256"] == ab["baseline_books_sha256"][f"{seat}_s{s}"]
        b = cx.B.get(kn); base = cx.BASE.get(bn)
        if not (b and base and b["rec"] is not None and base["rec"] is not None and d["baseline_sha_ok"]):
            d["ok"] = False; d["informational_seat"] = seat not in CHECK_SEATS; per[kn] = d; ok_all = False; continue   # fp2dyn (narrowed): baseline identity / missing book folds for EVERY seat
        R, RB = b["rec"], base["rec"]; ts = np.round(R[:, 0]).astype(np.int64); tsb = np.round(RB[:, 0]).astype(np.int64)
        gb = dict(zip(tsb.tolist(), RB[:, C["gross_total"]].tolist())); fm = (ts >= F0) & (ts < F1)
        bt = np.array([gb.get(int(t), np.nan) for t in ts[fm]]); ga = R[fm, C["gross_total"]]
        with np.errstate(all="ignore"): ratio = ga / bt
        d["n_frozen_compared"] = int(np.isfinite(ratio).sum()); d["baseline_axis_covers_frozen"] = bool(np.isfinite(ratio).all() and fm.any())
        if d["n_frozen_compared"]:
            d["ratio_min"] = float(np.nanmin(ratio)); d["ratio_median"] = float(np.nanmedian(ratio)); d["ratio_max"] = float(np.nanmax(ratio))
            d["n_anchors_outside_band"] = int(((ratio < lo) | (ratio > hi)).sum())
            d["band_ok"] = d["n_anchors_outside_band"] == 0 and mlo <= d["ratio_median"] <= mhi
        else: d["band_ok"] = False
        d["ok"] = d["baseline_sha_ok"] and d["baseline_axis_covers_frozen"] and d["band_ok"]; d["informational_seat"] = seat not in CHECK_SEATS
        d["identity_ok"] = d["baseline_sha_ok"] and d["baseline_axis_covers_frozen"]
        ok_all &= (d["ok"] if not d["informational_seat"] else d["identity_ok"]); per[kn] = d   # fp2dyn (narrowed): non-checked seat — identity folds, only the band is informational
    return cx.chk("E9_gross_band_vs_baseline", ok_all, {"band": [lo, hi], "median_band": [mlo, mhi], "baseline_arm": ab["baseline_arm"], **per})


def safe(cx, fn):
    """A check that raises is a named FAIL, never a silent traceback (a crashed gate that writes no receipt is 'no permission', but the
    failing check must still be NAMED in the receipt)."""
    try: fn(cx)
    except SystemExit: raise
    except Exception as e:  # noqa: BLE001
        cx.chk(fn.__name__, False, {"exception": f"{type(e).__name__}: {e}"})


def run_all(cx, guards=True):
    for fn in (E0_contract_baseline, E1_manifest, E2_config): safe(cx, fn)
    if guards:
        for fn in (E3_ic_gates, E4_baseline_guard): safe(cx, fn)
    for fn in (E5_books_shape, E6_books_config, E7_signal_receipt, E8_books_content, E9_gross_band_vs_baseline): safe(cx, fn)
    E = cx.E
    cx.inputs.update({"wide_fea_v4": E["BUNDLE_FEA"], "wide_fea_v4_meta": E["BUNDLE_META"], "bundle_base": E["BUNDLE_BASE"],
                      "export_panel": E["EXPORT_PANEL"], "bundle_cache": E["BUNDLE_CACHE"], "fund_aug": E["FUND_AUG"], "live_pins": E["LIVE_PINS"]})


# ----------------------------------------------------------------------------------------------------------------- modes
def gate_main():
    E = read_env(); cx = Ctx(E); run_all(cx, guards=True)
    R = cx.R; R["PASS"] = bool(not cx.fails); R["failed_checks"] = cx.fails
    R["registered_inputs"] = sorted(cx.inputs); R["registered_floor_v4_gate_common"] = cx.gc.REQUIRED_INPUTS.get(GATE)
    R["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); R["gate_version"] = "v2 (r20 gate closure 2026-09-12) + fp2dyn variant rev3 (2026-09-17: for seats outside CHECK_SEATS only the K6 gross CEILING and the E9 band are informational; K6 positivity, K1–K4/K7 identities and baseline identity fold)"; R["seats_checked"] = sorted(CHECK_SEATS); R["seats_informational"] = sorted({s for s, _ in SEATS} - CHECK_SEATS)
    print(("EXPORT_GATE_V2 PASS " if R["PASS"] else "EXPORT_GATE_V2 FAIL ") + str(cx.fails), flush=True)
    cx.gc.finalize(GATE, R, E["EXPORT_GATE_OUT"], cx.inputs)


def require_main(receipt_path):
    """Identity + full-floor sha re-verification (v4_gate_common.require) AND content gates re-run from the files. Nothing is read from the receipt but the shas."""
    E = read_env(); cx = Ctx(E); recompute = os.environ.get("REQUIRE_RECOMPUTE_GUARDS") == "1"
    run_all(cx, guards=recompute)                      # derives the full input set from disk (books -> costb/umask/slow/femat; manifest -> bundle/*)
    me = sha256_file(os.path.abspath(__file__))
    ok_id, why = cx.gc.require(receipt_path, cx.inputs, expected_gate=GATE, expected_self_sha=me)
    out = {"mode": "require", "receipt": receipt_path, "gate_self_sha256": me, "identity_and_inputs": {"ok": bool(ok_id), "why": why, "n_inputs_declared": len(cx.inputs), "inputs": sorted(cx.inputs)},
           "content_checks": cx.R["checks"], "content_failed": cx.fails, "guards_recomputed": recompute,
           "guards_binding_when_not_recomputed": "E3/E4 inputs (bundle/slow_pred_pinned.npy, wide_fea_v4_meta, bundle_base, export_panel, bundle/config.json) are sha-verified above; set REQUIRE_RECOMPUTE_GUARDS=1 to recompute",
           "env": {k: E[k] for k in REQ}, "contract_sha256": cx.R["contract_sha256"], "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    ok = bool(ok_id) and not cx.fails; out["REQUIRE_OK"] = ok
    ro = os.environ.get("REQUIRE_OUT")
    if ro:
        os.makedirs(os.path.dirname(os.path.abspath(ro)), exist_ok=True); json.dump(out, open(ro, "w"), indent=1, default=str)
    print(("REQUIRE_OK " if ok else "REQUIRE_FAIL ") + f"identity={ok_id} ({why}) content_failed={cx.fails}", flush=True)
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "require": require_main(sys.argv[2])
    elif len(sys.argv) >= 3 and sys.argv[1] == "sha":
        for p in sys.argv[2:]: print(sha256_file(p), p)
    elif len(sys.argv) == 1 or sys.argv[1] == "gate": gate_main()
    else: print(__doc__); sys.exit(2)
