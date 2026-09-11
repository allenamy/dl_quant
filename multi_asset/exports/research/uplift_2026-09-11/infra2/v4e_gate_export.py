"""v4e_gate_export.py — the PHYSICAL BUNDLE_export gate (INFRA2, round 2, 2026-09-11).

WHY IT EXISTS. ELIGIBILITY_CONTRACT.json says: "BUNDLE_export is empty because the physical export
gate does not exist yet (pod_export_bundle_v4.py prints guard PASS/FAIL and never calls finalize)."
That is exactly right: the exporter's three guards (fold IC 2024/2025 |Δ|<=0.004, pinned 2026 IC
|Δ|<=0.006, baseline Sharpe band [2.27,2.57]) are sys.exit(3) branches inside the producer, so their
only trace is a printed word in a log — the thing v4_gate_common's header calls "not evidence".
This gate re-derives all three from the SHIPPED ARTIFACTS, adds the book contract, and finalize()s a
receipt bound to (gate name, this source's sha, every registered input, the arm, the arm's four books).

WHAT IT RE-COMPUTES (no number is read from the exporter's own provenance and believed):
  E1 MANIFEST integrity      every file in the bundle hashes to MANIFEST.json; no extra, none missing.
  E2 config parity           config.json params == the frozen live params; keep_names and symbols_live
                             == live_pins.json (Δ4/Δ5 of the exporter, re-checked after the fact).
  E3 IC gates RE-DERIVED     slow_pred_pinned.npy carries the 2024 and 2025 walk-forward folds as well
                             as the pinned 2026 fold, so all three fold ICs are recomputable from the
                             shipped file against BUNDLE_META's y4 — no retrain, fully deterministic.
                             Thresholds verbatim from pod_export_bundle_v4.py L70 (0.004) and L81 (0.006).
  E4 baseline guard RE-RUN   block (2) of the exporter (v1iv pinned replay) re-executed from
                             slow_pred_pinned.npy + EXPORT_PANEL + BUNDLE_META; Sharpe(2024on) must
                             land in [BUNDLE_GUARD_LO, BUNDLE_GUARD_HI] AND match the value the
                             bundle's own provenance claims to 2 dp.
  E5 book contract           the arm's four judged books: cols == the frozen COLS, symbols present, W
                             (n, n_symbols) finite, frozen axis an exact 4h grid of N_FROZEN anchors
                             identical across all four, gross_total finite and > 0 on that window.
  E6 book config binding     each book's self-reported config_json must equal the pinned book env
                             (CAL/LEGS/PHI/LOOK/WRULE/MEMBERS_TOPN/FTRIM/UMASK_SCOPE/COST_B), carry
                             W3FIX iff seat==fix, carry the matching FSEED, and declare the APPROVED
                             replay device sha (DEVICE_SHA256 below). A book made by another program,
                             or at another caliber, is not this arm's book.
  E7 signal provenance       if a book injected a fund-leg matrix (FEMAT_NPZ), that file must exist and
                             is hashed into the receipt, and the signal-layer bitwise receipt
                             (SIGNAL_RECEIPT, GATE_signal_parity.json) must be present and PASS.

ENV — every one EXPLICIT, no silent default for anything that selects data (E-0826-D):
  EXPORT_ARM BUNDLE_OUT BUNDLE_FEA BUNDLE_META BUNDLE_BASE EXPORT_PANEL BUNDLE_CACHE FUND_AUG
  LIVE_PINS JUDGE_HC V4CHAIN_DIR SIGNAL_RECEIPT EXPORT_GATE_OUT
  [BUNDLE_GUARD_LO BUNDLE_GUARD_HI JUDGE_N_FROZEN — frozen defaults, printed into the receipt]
Exit 0 iff PASS, else 3 (v4_gate_common.finalize).
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
from scipy.stats import rankdata, spearmanr

REQ = ["EXPORT_ARM", "BUNDLE_OUT", "BUNDLE_FEA", "BUNDLE_META", "BUNDLE_BASE", "EXPORT_PANEL",
       "BUNDLE_CACHE", "FUND_AUG", "LIVE_PINS", "JUDGE_HC", "V4CHAIN_DIR", "SIGNAL_RECEIPT", "EXPORT_GATE_OUT"]
E = {}
for k in REQ:
    v = os.environ.get(k)
    if not v: print(f"EXPORT_GATE_REFUSED: env {k} not set (E-0826-D: a gate that guesses its inputs binds nothing)", flush=True); sys.exit(2)
    E[k] = v
sys.path.insert(0, E["V4CHAIN_DIR"])
from v4_gate_common import finalize, sha256_file, CONTRACT_PATH, load_contract, REQUIRED_INPUTS   # noqa: E402

ARM = E["EXPORT_ARM"]; OUT = E["BUNDLE_OUT"]; HC = E["JUDGE_HC"]
GLO = float(os.environ.get("BUNDLE_GUARD_LO", "2.27")); GHI = float(os.environ.get("BUNDLE_GUARD_HI", "2.57"))
N_FROZEN = int(os.environ.get("JUDGE_N_FROZEN", "3168"))
DEVICE_SHA256 = "8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d"   # w10_health.py, the archived replay device
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}


def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))


FROZEN = (T(2025, 3, 1), T(2026, 8, 10, 20) + 1)
PINNED_BOOK_ENV = {"CAL": "log", "LEGS": "101", "PHI": 0.45, "LOOK": 900, "WRULE": "msharpe",
                   "MEMBERS_TOPN": 829, "FTRIM": "zero", "UMASK_SCOPE": "m1"}
FROZEN_PARAMS = {"NTOP": 400, "cov_min": 0.95, "vol_min": 1e-4, "qv4h_min": 2.5e5, "cap_mult": 2.5,
                 "alpha": 0.1, "band": 2.5e-4, "msharpe_look": 900, "fund_caliber": "v1 normfix HL3d",
                 "carry": "rate*4/iv", "cost_scen": "b", "sel_min": 80, "anchor_offset_min": 6}
R = {"arm": ARM, "env": {k: E[k] for k in REQ}, "guard_band": [GLO, GHI], "n_frozen": N_FROZEN,
     "contract_path": CONTRACT_PATH, "contract_sha256": sha256_file(CONTRACT_PATH) if os.path.exists(CONTRACT_PATH) else None,
     "device_sha256_required": DEVICE_SHA256, "checks": {}}
_c, _cerr = load_contract()
R["contract_schema"] = (_c or {}).get("contract_schema"); R["contract_error"] = _cerr
fails = []


def chk(name, ok, detail):
    R["checks"][name] = {"ok": bool(ok), **detail}
    print(("  OK   " if ok else "  FAIL ") + name + " " + json.dumps(detail, default=str)[:400], flush=True)
    if not ok: fails.append(name)


# ---------- E1 manifest integrity ----------
man = json.load(open(f"{OUT}/MANIFEST.json"))
onfile = sorted(f for f in os.listdir(OUT) if f != "MANIFEST.json")
bad = {f: "missing" for f in man if not os.path.exists(f"{OUT}/{f}")}
for f in man:
    if f in bad: continue
    h = sha256_file(f"{OUT}/{f}")
    if h != man[f]: bad[f] = f"{h[:12]} != manifest {str(man[f])[:12]}"
extra = [f for f in onfile if f not in man]
chk("E1_manifest", not bad and not extra, {"n_files": len(man), "mismatched": bad, "unlisted_files": extra})

# ---------- E2 config parity ----------
cfg = json.load(open(f"{OUT}/config.json")); pins = json.load(open(E["LIVE_PINS"]))
pdiff = {k: [cfg.get("params", {}).get(k), v] for k, v in FROZEN_PARAMS.items() if cfg.get("params", {}).get(k) != v}
chk("E2_config", (not pdiff) and cfg.get("keep_names") == pins["keep_names"] and cfg.get("symbols_live") == pins["symbols_live"],
    {"param_diffs": pdiff, "keep_names_equal": cfg.get("keep_names") == pins["keep_names"],
     "symbols_live_equal": cfg.get("symbols_live") == pins["symbols_live"], "n_live": len(pins["symbols_live"])})

# ---------- E3 fold ICs re-derived from the shipped pinned predictions ----------
MT = np.load(E["BUNDLE_META"], allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
PRED = np.load(f"{OUT}/slow_pred_pinned.npy")
BASE = json.load(open(E["BUNDLE_BASE"]))
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts)


def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]


ic = {}
for Y in (2024, 2025, 2026):
    ics = []
    for a in np.nonzero(yrs == Y)[0]:
        m = members[a]; okm = np.isfinite(y4[a, m])
        if okm.sum() < 30: continue
        ics.append(sp(PRED[a, m[okm]], y4[a, m[okm]]))
    ic[Y] = float(np.nanmean(ics)) if ics else float("nan")
tol = {2024: 0.004, 2025: 0.004, 2026: 0.006}
dd = {Y: float(ic[Y] - float(BASE["ic"][str(Y)])) for Y in ic}
chk("E3_ic_gates", all(np.isfinite(dd[Y]) and abs(dd[Y]) <= tol[Y] for Y in dd),
    {"recomputed_ic": {str(k): round(v, 5) for k, v in ic.items()}, "base_ic": BASE["ic"],
     "delta": {str(k): round(v, 5) for k, v in dd.items()}, "tolerance": {str(k): v for k, v in tol.items()},
     "provenance_claimed": {k: cfg.get("provenance", {}).get(k) for k in ("fold_ic_2024", "fold_ic_2025", "pinned_ic2026")}})

# ---------- E4 baseline guard: block (2) of the exporter, re-run ----------
PW = np.load(E["EXPORT_PANEL"], allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]; FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
NW = 829
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]


def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan); n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out


def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t


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
sh = float(arr.mean() / (arr.std() + 1e-12) * np.sqrt(6 * 365))
claimed = cfg.get("provenance", {}).get("pinned_sharpe_full_b")
chk("E4_baseline_guard", (GLO <= sh <= GHI) and (claimed is None or abs(sh - float(claimed)) <= 0.005),
    {"recomputed_sharpe_2024on": round(sh, 4), "band": [GLO, GHI], "provenance_claimed": claimed,
     "n_anchors": len(rec), "mean_net_bps": round(float(arr.mean()), 4)})

# ---------- E5/E6/E7 book contract ----------
BOOKS = {f"book_{seat}_s{s}": f"{HC}/dev_v4/probe_artifacts/w10_ablation_series_V4_{ARM}_{seat}_s{s}.npz"
         for seat in ("dyn", "fix") for s in ("42", "2027")}
bk = {}; sym_ref = None; ax_ref = None; femats = {}
for nm, p in sorted(BOOKS.items()):
    seat = nm.split("_")[1]; seed = nm.split("_s")[1]
    d = {"path": p}
    if not os.path.exists(p): d["err"] = "missing"; bk[nm] = d; continue
    A = np.load(p, allow_pickle=True); keys = set(A.files)
    rec_ = np.asarray(A["d30_n2_c42_rec"], float) if "d30_n2_c42_rec" in keys else None
    d["has_rec"] = rec_ is not None
    d["cols_ok"] = "cols" in keys and [str(x) for x in np.asarray(A["cols"]).ravel()] == COLS
    d["symbols_present"] = "symbols" in keys
    syms = [str(x) for x in np.asarray(A["symbols"]).ravel()] if "symbols" in keys else None
    if sym_ref is None: sym_ref = syms
    d["symbols_match"] = syms == sym_ref
    W = np.asarray(A["d30_n2_c42_W"], float) if "d30_n2_c42_W" in keys else None
    d["W_shape_ok"] = W is not None and rec_ is not None and W.ndim == 2 and W.shape == (rec_.shape[0], len(syms or []))
    d["W_finite"] = bool(W is not None and np.isfinite(W).all())
    ts_ = np.round(rec_[:, 0]).astype(np.int64) if rec_ is not None else np.array([], np.int64)
    a = ts_[(ts_ >= FROZEN[0]) & (ts_ < FROZEN[1])]
    d["n_frozen"] = int(len(a))
    d["frozen_axis_ok"] = bool(len(a) == N_FROZEN and (len(a) == 0 or int(a[0]) == FROZEN[0]) and (len(a) < 2 or (np.diff(a) == 14400).all()))
    if ax_ref is None: ax_ref = a
    d["frozen_axis_shared"] = bool(np.array_equal(a, ax_ref))
    gt = rec_[:, C["gross_total"]][(ts_ >= FROZEN[0]) & (ts_ < FROZEN[1])] if rec_ is not None else np.array([])
    d["gross_finite_pos"] = bool(len(gt) and np.isfinite(gt).all() and (gt > 0).all())
    cj = json.loads(str(A["config_json"])) if "config_json" in keys else {}
    d["cfg_diffs"] = {k: [cj.get(k), v] for k, v in PINNED_BOOK_ENV.items() if cj.get(k) != v}
    d["seat_ok"] = (cj.get("W3FIX") == "0.21,0,0.79") if seat == "fix" else (cj.get("W3FIX") in (None, ""))
    d["seed_ok"] = str(cj.get("FSEED")) == seed
    d["device_sha_ok"] = (cj.get("HEALTH") or {}).get("device_sha256") == DEVICE_SHA256
    d["device_sha"] = (cj.get("HEALTH") or {}).get("device_sha256")
    d["FEMAT_NPZ"] = cj.get("FEMAT_NPZ")
    if cj.get("FEMAT_NPZ"):
        femats[nm] = cj["FEMAT_NPZ"]
        d["femat_exists"] = os.path.exists(cj["FEMAT_NPZ"])
        d["femat_sha256"] = sha256_file(cj["FEMAT_NPZ"]) if d["femat_exists"] else None
    d["ok"] = bool(d.get("has_rec") and d["cols_ok"] and d["symbols_present"] and d["symbols_match"] and d["W_shape_ok"]
                   and d["W_finite"] and d["frozen_axis_ok"] and d["frozen_axis_shared"] and d["gross_finite_pos"]
                   and not d["cfg_diffs"] and d["seat_ok"] and d["seed_ok"] and d["device_sha_ok"]
                   and (not cj.get("FEMAT_NPZ") or d.get("femat_exists")))
    bk[nm] = d
chk("E5_E6_books", all(v.get("ok") for v in bk.values()), {k: {kk: vv for kk, vv in v.items() if kk != "path"} for k, v in bk.items()})
sig_ok = os.path.exists(E["SIGNAL_RECEIPT"])
sig = json.load(open(E["SIGNAL_RECEIPT"])) if sig_ok else {}
femat_one = len(set(femats.values())) <= 1
chk("E7_signal_provenance", (not femats or (sig.get("PASS") is True and femat_one)),
    {"femat_per_book": femats, "one_femat_for_all_cells": femat_one,
     "signal_receipt_present": sig_ok, "signal_receipt_PASS": sig.get("PASS"),
     "signal_receipt_sha256": sha256_file(E["SIGNAL_RECEIPT"]) if sig_ok else None,
     "signal_gate": sig.get("gate")})

R["PASS"] = bool(not fails); R["failed_checks"] = fails
R["registered_inputs"] = REQUIRED_INPUTS.get("BUNDLE_export")
R["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
print(("EXPORT_GATE PASS " if R["PASS"] else "EXPORT_GATE FAIL ") + str(fails), flush=True)
INPUTS = {"wide_fea_v4": E["BUNDLE_FEA"], "wide_fea_v4_meta": E["BUNDLE_META"], "bundle_base": E["BUNDLE_BASE"],
          "export_panel": E["EXPORT_PANEL"], "bundle_cache": E["BUNDLE_CACHE"], "fund_aug": E["FUND_AUG"],
          "live_pins": E["LIVE_PINS"], **BOOKS}
finalize("BUNDLE_export", R, E["EXPORT_GATE_OUT"], INPUTS)
