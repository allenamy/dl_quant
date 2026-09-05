#!/usr/bin/env python
"""s1_decompose.py — PREREG_f10_caliber_sensitivity_2026-09-05 §1 (frozen): per-anchor, per-leg unit-gross rank-book return under three labels.
Book construction = w10_health.py legs() verbatim under the primary arm configuration (MEMBERS_TOPN=829 members rebuilt from qvk, UMASK_SCOPE=m1 with
masks/umask_UPIT.npz, fund z = rank in the 829 base (FZB), king/F10 z = rank within members (xz), z masked to label-finite members, demeaned, unit gross,
return = Σ z/g · y · 1e4 with NaN y → 0, CAL=log = no transform). Legs: king (slow_pred_pinned) / F10 s42 / F10 s2027 / fund (f_fund_ema_v1).
Labels (rebuilt in-process by labels_lib.build_labels(), the same function s0 used for the parity receipts; no intermediate file — volume at quota):
(i) Σ-simple [E,E+47] = meta y4 (asserted bitwise here); (ii) Σ-simple [E+1,E+48]; (iii) Π(1+r)−1 [E+1,E+48] = dlw y4s.
window term = (ii) − (i); compounding term = (iii) − (ii); exposure parts of the window term: book·r_E and book·r_{E+48} (label-(ii) mask).
Spearman over members per anchor: corr(score, r_{E+k}) k=−3..+3 (offset spectrum; k=0 is row E = the bar closing at N), corr(score, r_{E+48}), corr(score, (Σr)²−Σr² over [E+1,E+48]).
Bootstrap: UTC-day blocks, 2000 resamples, seed 20260905 (fresh generator per cell), s.e. = std of resampled means, CI95 = 2.5/97.5 pct.
Frozen reading (§1): |window| ≥ 2·|compounding| ⇒ H1 (one-bar window offset) dominates; |compounding| ≥ 2·|window| ⇒ H2 (convexity) dominates; else both.
Receipts: (i)/(iii) king+fund series bitwise vs health_check M1_UPIT_{log,prod}_s42_ccal legs_king/legs_fund; F10 series bitwise vs seat_round2 B1_{log,prod}_s{42,2027} legs_f10.
Read-only inputs; writes only results/s1_*.{npz,json,md}.
"""
import numpy as np, time, json, hashlib, os, calendar, sys
from scipy.stats import rankdata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from labels_lib import build_labels, CACHE
ROOT = "/workspace/review_scratch/f10_caliber"
META = "/workspace/data/wide_fea_v2ext_meta.npz"; PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"
UMASK = f"{ROOT}/masks/umask_UPIT.npz"; SLOWP = "/workspace/shadow_bundle_v3/slow_pred_pinned.npy"
PRED = {"f10_s42": "/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s42.npy", "f10_s2027": "/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy"}
DLW = "/workspace/port_w10/dlw_2026-08-22/data/dlw_targets.npz"
HC = "/workspace/review_scratch/health_check"; SR2 = "/workspace/review_scratch/seat_round2"
NB = 2000; SEED = 20260905; MEMBERS_TOPN = 829; NW = 829
T_START = calendar.timegm((2024, 1, 1, 0, 0, 0)); T_END = calendar.timegm((2026, 8, 10, 20, 0, 0))
LEGS = ["king", "f10_s42", "f10_s2027", "fund"]; LABS = ["i", "ii", "iii"]; LAGS = list(range(-3, 4))
t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
CFG = {"self_sha256": sha(os.path.abspath(__file__)), "labels_lib_sha256": sha(os.path.join(os.path.dirname(os.path.abspath(__file__)), "labels_lib.py")),
       "inputs": {k: sha(p) for k, p in (("cache", CACHE), ("meta", META), ("panel", PANEL), ("umask", UMASK), ("slow", SLOWP), ("f10_s42", PRED["f10_s42"]), ("f10_s2027", PRED["f10_s2027"]), ("dlw", DLW))},
       "book": "w10_health.py legs() verbatim; MEMBERS_TOPN=829; UMASK_SCOPE=m1; fund z = FZB (829 base); CAL=log (no transform)", "NB": NB, "SEED": SEED,
       "window": "2024-01-01 00:00Z .. 2026-08-10 20:00Z (last finite F10 row)", "reading_rule": "|window| >= 2|comp| -> H1; |comp| >= 2|window| -> H2; else both"}
print("CONFIG " + json.dumps(CFG), flush=True)
Lb = build_labels(log); E_ts = Lb["E_ts"]; nA = len(E_ts)
Y = {"i": Lb["oldsum"], "ii": Lb["newsum"], "iii": Lb["newprod"]}; RK = Lb["rk"]; RE48 = Lb["rE48"]; CONV = Lb["conv"]
MT = np.load(META, allow_pickle=True); assert np.array_equal(MT["E_ts"].astype(np.int64), E_ts); qvk = MT["qvk"]
assert np.array_equal(MT["y4"], Y["i"], equal_nan=True), "label (i) must be the meta y4 bitwise"
NPz = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz", allow_pickle=True); assert np.array_equal(NPz["y4"], Y["iii"], equal_nan=True), "label (iii) must be meta_newprod y4 bitwise"; del NPz
print("LABEL_RECEIPT (i) == meta y4 bitwise: True; (iii) == refute_C6_2 meta_newprod y4 bitwise: True", flush=True)
_mem2 = np.empty(nA, dtype=object)   # verbatim from w10_health.py (MEMBERS_TOPN branch)
for _i in range(nA):
    _q = np.nan_to_num(qvk[_i], nan=-1.0); _ord = np.argsort(-_q); _ord = _ord[_q[_ord] > -0.5]
    _mem2[_i] = np.sort(_ord[:MEMBERS_TOPN]).astype(np.int64)
members = _mem2
PW = np.load(PANEL, allow_pickle=True); pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}; FE = PW["f_fund_ema_v1"]; WSYM = [str(s) for s in PW["symbols"]]
assert WSYM == Lb["symbols"]
_uz = np.load(UMASK, allow_pickle=True); assert [str(x) for x in _uz["symbols"]] == WSYM, "umask symbols mismatch"
_umap = {int(t): k for k, t in enumerate(_uz["ts"].astype(np.int64))}; _UM = np.asarray(_uz["mask"]); _pwts_u = PW["ts"].astype(np.int64)
UMASK_ROW = {}
for _j, _t in enumerate(_pwts_u):
    _k = _umap.get(int(_t))
    if _k is not None: UMASK_ROW[_j] = _UM[_k]
SLOW = np.load(SLOWP); assert SLOW.shape == (nA, NW)
def load_f10(path):   # verbatim alignment from w10_health.py (PHI>0 branch)
    F10P = np.full((nA, NW), np.nan, np.float32)
    _pd = np.load(path); _TG = np.load(DLW, allow_pickle=True); _dts = _TG["E_ts"].astype(np.int64); _dsy = [str(x) for x in _TG["symbols"]]
    _rmap = {int(t): k for k, t in enumerate(_dts)}; _cmap = {s: k for k, s in enumerate(_dsy)}
    _cols = np.array([_cmap.get(s, -1) for s in WSYM], np.int64); _okc = _cols >= 0; _nrow = 0
    for _i in range(nA):
        _k = _rmap.get(int(E_ts[_i]))
        if _k is None: continue
        F10P[_i, _okc] = _pd[_k, _cols[_okc]]; _nrow += 1
    log(f"F10 aligned {path}: rows {_nrow}/{nA} cols {_okc.sum()}/{NW} finite {np.isfinite(F10P).mean():.4f}")
    return F10P
F10 = {k: load_f10(p) for k, p in PRED.items()}
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
def FZB(j, m): return xz(FE[j, :])[m]
def spearman(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 10: return np.nan
    rx = rankdata(x[ok]); ry = rankdata(y[ok]); rx = rx - rx.mean(); ry = ry - ry.mean(); d = np.sqrt((rx * rx).sum() * (ry * ry).sum())
    return float((rx * ry).sum() / d) if d > 0 else np.nan
LR = {(leg, lab): [] for leg in LEGS for lab in LABS}; PART = {(leg, nm): [] for leg in LEGS for nm in ("rE", "rE48")}
COR = {(leg, nm): [] for leg in LEGS for nm in [f"k{k:+d}" for k in LAGS] + ["rE48", "conv"]}
NOK = {lab: [] for lab in LABS}; NMEM = []; idx = []
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    _mk = UMASK_ROW.get(j)
    if _mk is not None: m = m[_mk[m]]
    sc = {"king": SLOW[i, m], "fund": FE[j, m], "f10_s42": F10["f10_s42"][i, m], "f10_s2027": F10["f10_s2027"][i, m]}
    zs = {leg: (FZB(j, m) if leg == "fund" else xz(sc[leg])) for leg in LEGS}
    for lab in LABS:
        y = Y[lab][i, m]; ok = np.isfinite(y); NOK[lab].append(int(ok.sum()))
        for leg in LEGS:
            z = np.nan_to_num(zs[leg]); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
            g = np.abs(z).sum()
            _yy = np.nan_to_num(y, nan=0.0)
            _lr = float((z / g * _yy).sum() * 1e4) if g > 1e-9 else 0.0
            LR[(leg, lab)].append(_lr)
            if lab == "ii":
                PART[(leg, "rE")].append(float((z / g * np.nan_to_num(RK[3][i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
                PART[(leg, "rE48")].append(float((z / g * np.nan_to_num(RE48[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
    for leg in LEGS:
        s = zs[leg]
        for kk, k in enumerate(LAGS): COR[(leg, f"k{k:+d}")].append(spearman(s, RK[kk][i, m]))
        COR[(leg, "rE48")].append(spearman(s, RE48[i, m])); COR[(leg, "conv")].append(spearman(s, CONV[i, m]))
    NMEM.append(int(len(m))); idx.append(i)
    if i % 2000 == 0: log(f"anchor {i}/{nA}")
idx = np.array(idx); legs_ts = E_ts[idx]; nL = len(idx)
LR = {k: np.array(v) for k, v in LR.items()}; PART = {k: np.array(v) for k, v in PART.items()}; COR = {k: np.array(v) for k, v in COR.items()}
NOK = {k: np.array(v) for k, v in NOK.items()}; NMEM = np.array(NMEM)
log(f"legs done: {nL} anchors with panel row; members mean {NMEM.mean():.1f}; label-finite members mean (i) {NOK['i'].mean():.1f} (ii) {NOK['ii'].mean():.1f} (iii) {NOK['iii'].mean():.1f}; anchors where (i)/(ii) finite sets differ {(NOK['i'] != NOK['ii']).sum()}, (ii)/(iii) {(NOK['ii'] != NOK['iii']).sum()}")
# ---- receipts vs the health_check / seat_round2 artifacts (legs() series saved there)
REC = {}
def receipt(name, path, key, mine):
    z = np.load(path, allow_pickle=True); cfg = json.loads(str(z["config_json"])); lts = z["legs_ts"].astype(np.int64)
    same_ts = bool(np.array_equal(lts, legs_ts)); a = z[key]
    eq = bool(same_ts and np.array_equal(a, mine)); maxd = float(np.max(np.abs(a - mine))) if same_ts else float("nan")
    sub = {k: cfg.get(k) for k in ("CAL", "LEGS", "PHI", "FSEED", "MEMBERS_TOPN", "UMASK_SCOPE", "SEATF10", "FTRIM", "LOOK", "WRULE")}; sub["UMASK_NPZ"] = os.path.basename(str(cfg.get("UMASK_NPZ")))
    REC[name] = {"artifact": path, "artifact_sha16": sha(path)[:16], "key": key, "n": int(len(mine)), "legs_ts_equal": same_ts, "bitwise_equal": eq, "max_abs_diff": maxd, "artifact_config": sub}
    print(f"RECEIPT {name}: bitwise_equal={eq} max|diff|={maxd:.3e} ts_equal={same_ts} cfg={json.dumps(sub)}", flush=True)
receipt("(i) king vs HC M1_UPIT_log_s42_ccal legs_king", f"{HC}/dev/probe_artifacts/w10_ablation_series_M1_UPIT_log_s42_ccal.npz", "legs_king", LR[("king", "i")])
receipt("(i) fund vs HC M1_UPIT_log_s42_ccal legs_fund", f"{HC}/dev/probe_artifacts/w10_ablation_series_M1_UPIT_log_s42_ccal.npz", "legs_fund", LR[("fund", "i")])
receipt("(iii) king vs HC M1_UPIT_prod_s42_ccal legs_king", f"{HC}/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_ccal.npz", "legs_king", LR[("king", "iii")])
receipt("(iii) fund vs HC M1_UPIT_prod_s42_ccal legs_fund", f"{HC}/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_ccal.npz", "legs_fund", LR[("fund", "iii")])
for seed in ("42", "2027"):
    receipt(f"(i) f10_s{seed} vs SR2 B1_log_s{seed} legs_f10", f"{SR2}/dev/probe_artifacts/w10_ablation_series_B1_log_s{seed}.npz", "legs_f10", LR[(f"f10_s{seed}", "i")])
    receipt(f"(iii) f10_s{seed} vs SR2 B1_prod_s{seed} legs_f10", f"{SR2}/dev_alt/probe_artifacts/w10_ablation_series_B1_prod_s{seed}.npz", "legs_f10", LR[(f"f10_s{seed}", "iii")])
# ---- windows, bootstrap, tables
yrs = np.array([time.gmtime(int(t)).tm_year for t in legs_ts]); days = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in legs_ts])
inw = (legs_ts >= T_START) & (legs_ts <= T_END)
WIN = {"2024": inw & (yrs == 2024), "2025": inw & (yrs == 2025), "2026<=08-10": inw & (yrs == 2026), "2024->26": inw, "2025->26": inw & (yrs >= 2025)}
def boot(x, m):
    x = x[m]; dd = days[m]; ok = np.isfinite(x); x = x[ok]; dd = dd[ok]
    ud, inv = np.unique(dd, return_inverse=True); nd = len(ud)
    if nd < 2 or len(x) < 2: return {"mean": float(x.mean()) if len(x) else float("nan"), "se": float("nan"), "lo": float("nan"), "hi": float("nan"), "p_gt0": float("nan"), "n": int(len(x)), "n_days": int(nd)}
    sums = np.bincount(inv, weights=x, minlength=nd); cnts = np.bincount(inv, minlength=nd)
    rng = np.random.default_rng(SEED); idx_ = rng.integers(0, nd, size=(NB, nd)); means = sums[idx_].sum(1) / cnts[idx_].sum(1)
    return {"mean": float(x.mean()), "se": float(means.std(ddof=1)), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5)), "p_gt0": float((means > 0).mean()), "n": int(len(x)), "n_days": int(nd)}
def reading(w, c):
    aw, ac = abs(w), abs(c)
    if aw >= 2 * ac: return "H1 dominates (window)"
    if ac >= 2 * aw: return "H2 dominates (compounding)"
    return "both (same order)"
OUT = {"config": CFG, "receipts": REC, "n_anchors_with_panel_row": int(nL), "windows": {w: int(m.sum()) for w, m in WIN.items()}, "levels": {}, "decomp": {}, "parts": {}, "corr": {}, "spectrum": {}, "identity_check": {}}
md = []; P = md.append
P("### §1.1 Levels — unit-gross rank-book return per leg (bps/anchor per unit gross), mean by window under the three labels; s.e. = UTC-day-block bootstrap 2000, seed 20260905")
P(""); P("| leg | window | n | (i) Σ-simple [E,E+47] (= meta y4) | (ii) Σ-simple [E+1,E+48] | (iii) Π(1+r)−1 [E+1,E+48] (= dlw y4s) |"); P("|---|---|---|---|---|---|")
for leg in LEGS:
    for w, m in WIN.items():
        b = {lab: boot(LR[(leg, lab)], m) for lab in LABS}; OUT["levels"][f"{leg}/{w}"] = b
        P(f"| {leg} | {w} | {b['i']['n']} | " + " | ".join(f"{b[lab]['mean']:+.3f} ± {b[lab]['se']:.3f}" for lab in LABS) + " |")
P(""); P("### §1.2 Decomposition — window term = (ii)−(i); compounding term = (iii)−(ii); paired per anchor; cell = mean ± s.e. [CI95]; frozen reading rule applied per cell")
P(""); P("| leg | window | window term (ii)−(i) | compounding term (iii)−(ii) | total (iii)−(i) | \\|window\\|/\\|comp\\| | reading |"); P("|---|---|---|---|---|---|---|")
for leg in LEGS:
    for w, m in WIN.items():
        bw = boot(LR[(leg, "ii")] - LR[(leg, "i")], m); bc = boot(LR[(leg, "iii")] - LR[(leg, "ii")], m); bt = boot(LR[(leg, "iii")] - LR[(leg, "i")], m)
        rd = reading(bw["mean"], bc["mean"]); ratio = abs(bw["mean"]) / abs(bc["mean"]) if abs(bc["mean"]) > 1e-12 else float("inf")
        OUT["decomp"][f"{leg}/{w}"] = {"window": bw, "comp": bc, "total": bt, "ratio_abs_window_over_comp": ratio, "reading": rd}
        P(f"| {leg} | {w} | {bw['mean']:+.3f} ± {bw['se']:.3f} [{bw['lo']:+.3f},{bw['hi']:+.3f}] | {bc['mean']:+.3f} ± {bc['se']:.3f} [{bc['lo']:+.3f},{bc['hi']:+.3f}] | {bt['mean']:+.3f} ± {bt['se']:.3f} [{bt['lo']:+.3f},{bt['hi']:+.3f}] | {ratio:.2f} | {rd} |")
P(""); P("### §1.3 Exposure parts of the window term — book·r_E (the bar closing at N, row E; inside the F10 feature window, outside king's) and book·r_{E+48} (the bar closing at N+4h); window term = part_{E+48} − part_E when the finite sets coincide")
P(""); P("| leg | window | book·r_E (bps) | book·r_{E+48} (bps) | part_{E+48} − part_E | window term (from §1.2) | max\\|dev\\| per anchor |"); P("|---|---|---|---|---|---|---|")
for leg in LEGS:
    for w, m in WIN.items():
        be = boot(PART[(leg, "rE")], m); b48 = boot(PART[(leg, "rE48")], m); bd = boot(PART[(leg, "rE48")] - PART[(leg, "rE")], m); bw = OUT["decomp"][f"{leg}/{w}"]["window"]
        dev = float(np.max(np.abs((PART[(leg, "rE48")] - PART[(leg, "rE")]) - (LR[(leg, "ii")] - LR[(leg, "i")]))[m]))
        OUT["parts"][f"{leg}/{w}"] = {"rE": be, "rE48": b48, "diff": bd, "max_abs_dev_vs_window_term": dev}
        P(f"| {leg} | {w} | {be['mean']:+.3f} ± {be['se']:.3f} | {b48['mean']:+.3f} ± {b48['se']:.3f} | {bd['mean']:+.3f} ± {bd['se']:.3f} | {bw['mean']:+.3f} | {dev:.2e} |")
P(""); P("### §1.4 Direct exposures — Spearman over members per anchor, mean by window ± day-block s.e.: corr(score, r_E) (row E), corr(score, r_{E+48}), corr(score, (Σr)²−Σr² over [E+1,E+48])")
P(""); P("| leg | window | corr(score, r_E) | corr(score, r_{E+48}) | corr(score, convexity) |"); P("|---|---|---|---|---|")
for leg in LEGS:
    for w, m in WIN.items():
        b0 = boot(COR[(leg, "k+0")], m); b48 = boot(COR[(leg, "rE48")], m); bc = boot(COR[(leg, "conv")], m)
        OUT["corr"][f"{leg}/{w}"] = {"rE": b0, "rE48": b48, "conv": bc}
        P(f"| {leg} | {w} | {b0['mean']:+.4f} ± {b0['se']:.4f} | {b48['mean']:+.4f} ± {b48['se']:.4f} | {bc['mean']:+.4f} ± {bc['se']:.4f} |")
P(""); P("### §1.5 Offset spectrum (context) — mean Spearman corr(score, r_{E+k}) over members, 5-minute lags k = −3..+3 around the anchor row E (k=0 = the bar closing at N; F10 features end at row E, king/fund panel features end at row E−1)")
P(""); P("| leg | window | " + " | ".join(f"k={k:+d}" for k in LAGS) + " |"); P("|---|---|" + "---|" * len(LAGS))
for leg in LEGS:
    for w in ("2024", "2025", "2026<=08-10", "2024->26"):
        m = WIN[w]; vals = {f"k{k:+d}": float(np.nanmean(COR[(leg, f'k{k:+d}')][m])) for k in LAGS}; OUT["spectrum"][f"{leg}/{w}"] = vals
        P(f"| {leg} | {w} | " + " | ".join(f"{vals[f'k{k:+d}']:+.4f}" for k in LAGS) + " |")
OUT["identity_check"] = {"anchors_(i)_(ii)_finite_sets_differ": int((NOK["i"] != NOK["ii"]).sum()), "anchors_(ii)_(iii)_finite_sets_differ": int((NOK["ii"] != NOK["iii"]).sum())}
np.savez(f"{ROOT}/results/s1_series.npz", legs_ts=legs_ts, legs_idx=idx, **{f"LR_{leg}_{lab}": LR[(leg, lab)] for leg in LEGS for lab in LABS}, **{f"PART_{leg}_{nm}": PART[(leg, nm)] for leg in LEGS for nm in ("rE", "rE48")},
         **{f"COR_{leg}_{nm}": COR[(leg, nm)] for leg in LEGS for nm in [f"k{k:+d}" for k in LAGS] + ["rE48", "conv"]}, nmem=NMEM, **{f"nok_{lab}": NOK[lab] for lab in LABS})
json.dump(OUT, open(f"{ROOT}/results/s1_tables.json", "w"), indent=1)
open(f"{ROOT}/results/s1_tables.md", "w").write("\n".join(md) + "\n")
print("\n".join(md), flush=True)
log("DONE")
