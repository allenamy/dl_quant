"""R9 — forward extension of the v4 F10/V2MAIN monthly-WF DL leg, with the gates decomposed.

ENV WHITELIST (E-0826-D): EMPTY SET. No environment variable is consulted. Everything is a literal
in CONFIG; CONFIG + this file's sha256 are written into the receipt.

GATES (all bitwise; every exemption is ENUMERATED and independently checkable — r6 §11 lesson:
"an assertion never catches an error in the constant that defines its own scope; what catches it is
the gate printing the detail"):
  X-P     : re-infer the fold's own stored P from the bare state_dict + rebuilt mu/sd -> maxabs 0.0   [run in r9_extend.py, re-run here]
  X-OVLP-B: the DEPLOYED f10_v4RAW array must carry that P bitwise                                    [re-run here]
  X-PRE   : the r6 extended feature matrix must be a bitwise prefix-extension of the incumbent
            X-PRE/strict     : whole prefix                     (KNOWN TO FAIL -> reported, not hidden)
            X-PRE/calib      : only the rows mu/sd is built from (must PASS: else the device drifts)
            X-PRE/disjoint   : the differing rows must be disjoint from every row this device reads
            X-PRE/exempt     : the differing cells must be exactly the enumerated E-0911-B set
  X-OVLP-A: literal task gate — device output vs the archived f10_A0_s{42,2027}                        [different lineage; reported]
"""
import os, sys, json, time, hashlib
import numpy as np
import torch, torch.nn as nn

READ_ENV = []
assert READ_ENV == []
_KNOBS = ["ARM","V2","SEED","COST","LDD","AFIX","LDC","CTXA","REC","PLE","EPOCHS","LR","NCOL","EXTRA","LPP",
          "F10_DLW","F10_OUT","MWF_OUT","EMBARGO","MWF_TAG","MONTHS","FORCE","BEST_EP_FLOOR","BEST_EP_FIX",
          "F10_GATE_JSON","MWF_ROOT","PHI","LOOK","FPRED","FSEED","LEGS","CAL","SLOW_NPY","F171_PANEL"]
_LEAK = {k: os.environ.get(k) for k in _KNOBS if os.environ.get(k) is not None}
assert _LEAK == {}, f"E-0826-D: knobs leaked into env: {_LEAK}"

OUT = "/workspace/uplift_2026-09-11/r9/out"
# The E-0911-B exemption, declared BEFORE it is used, as anchor timestamps + column names (not indices):
E0911B_ANCHORS = ["2026-08-31 04:00Z", "2026-08-31 08:00Z", "2026-08-31 12:00Z",
                  "2026-08-31 16:00Z", "2026-08-31 20:00Z"]
E0911B_COLS = ["fund_ema", "fund_now"]
E0911B_MECHANISM = ("pod_dlw_features_ext.py L93: `X[sl, col] = 0.0 if j is None else ...` — when the 4h "
                    "panel has no row for the anchor, BOTH funding columns are written as hard 0.0 with no "
                    "flag. The incumbent v3splice panel ends 2026-08-31 00:00Z while the DL axis runs to "
                    "2026-08-31 20:00Z => the last 5 anchors got fund_ema=fund_now=0.0 for every member. "
                    "The r6 extended panel (to 2026-09-10 00:00Z) has those rows, so the extended fea82 "
                    "carries real values there. The difference is a REPAIR of a known defect, not a new one.")
CONFIG = {
    "device": "r9_f10_mwf_forward_extend_v2", "caliber": "v4 chain 2026-09-09 (CALIBER_PIN_v4_2026-09-11)",
    "fold": 202608, "tag": "mE1cX7", "embargo_anchors": 1, "best_epoch_rule": "fix7",
    "arch": {"d": 171, "h": 256, "dropout": 0.1},
    "folds": [
        {"name": "mwf_v4b_RAW_s42",  "seed": 42,   "dir": "/workspace/f8_v4/mwf_v4b/RAW_s42/shard3",
         "deployed": "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s42.npy"},
        {"name": "mwf_v4b_RAW_s2027","seed": 2027, "dir": "/workspace/f8_v4/mwf_v4b/RAW_s2027/shard3",
         "deployed": "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s2027.npy"},
    ],
    "inc": {"targets": "/workspace/dlw_v4raw/data/dlw_targets.npz",
            "fea82":   "/workspace/dlw_v4raw/data/dlw_fea82.npz",
            "fea89":   "/workspace/f8_v4/data/f8_fea89.npz"},
    "ext": {"targets": "/workspace/uplift_2026-09-11/r6/out/dlw_targets_x0910.npz",
            "fea82":   "/workspace/uplift_2026-09-11/r6/out/dlw_hf3_x0910/data/dlw_fea82.npz",
            "fea89":   "/workspace/uplift_2026-09-11/r6/out/f8_v4_x0910/data/f8_fea89.npz"},
    "A0_lineage": {"42":   "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy",
                   "2027": "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s2027.npy"},
    "trainer": "/workspace/review_scratch/pod_f10_train_monthly_v4.py",
    "fea_builder": "/workspace/pod_dlw_features_ext.py",
    "E0911B_exemption": {"anchors": E0911B_ANCHORS, "columns": E0911B_COLS, "mechanism": E0911B_MECHANISM},
    "out_dir": OUT, "torch_device": "cuda",
}
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
CONFIG["self_sha256"] = sha(os.path.abspath(__file__))
def iso(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
R = {"config": CONFIG, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
DEV = "cuda"; assert torch.cuda.is_available()
R["runtime"] = {"torch": torch.__version__, "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0),
                "allow_tf32_matmul": bool(torch.backends.cuda.matmul.allow_tf32),
                "float32_matmul_precision": torch.get_float32_matmul_precision()}
log("runtime", json.dumps(R["runtime"]))

class Net(nn.Module):
    def __init__(s, d=171, h=256, p=0.1):
        super().__init__()
        s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p),
                            nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
        s.a = nn.Parameter(torch.tensor(-2.303))
    def alpha(s): return 0.02 + 0.88 * torch.sigmoid(s.a)

def score_range(mdl, i_lo, i_hi, ST_, XT_, PST_, NW_, mu_, sd_):
    """verbatim pod_f10_train_monthly_v4.py L416-L424."""
    out = np.full((i_hi - i_lo, NW_), np.nan, np.float32); skipped = []
    with torch.no_grad():
        for i in range(i_lo, i_hi):
            a0, b0 = int(ST_[i]), int(ST_[i + 1])
            if b0 - a0 < 50:
                skipped.append(i); continue
            x = torch.clamp((XT_[a0:b0] - mu_) / sd_, -5, 5)
            out[i - i_lo, PST_[a0:b0].cpu().numpy()] = mdl.f(torch.nan_to_num(x)).squeeze(-1).cpu().numpy()
    return out, skipped

def build(tgt_p, f82_p, f89_p):
    TG = np.load(tgt_p, allow_pickle=True); E = TG["E_ts"].astype(np.int64); nA, NW = TG["y4s"].shape
    assert np.all(np.diff(E) == 14400)
    FE = np.load(f82_p, allow_pickle=True); pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
    F9 = np.load(f89_p, allow_pickle=True)
    assert np.array_equal(F9["pair_a"].astype(np.int64), pa) and np.all(np.diff(pa) >= 0)
    XL = np.concatenate([FE["X"], F9["X"]], 1).astype(np.float32); assert XL.shape[1] == 171
    names = json.loads(str(FE["meta_json"]))["names"]
    ST = np.searchsorted(pa, np.arange(nA + 1))
    return E, nA, NW, pa, ps, ST, XL, names

# ═══════════ PHASE 1: incumbent, calibration, GATE X-P + X-OVLP-B ═══════════
E_inc, nA_i, NW, pa_i, ps_i, ST_i, XL_i, NAMES82 = build(**{"tgt_p": CONFIG["inc"]["targets"], "f82_p": CONFIG["inc"]["fea82"], "f89_p": CONFIG["inc"]["fea89"]})
log(f"incumbent axis {nA_i} ({iso(E_inc[0])}..{iso(E_inc[-1])}) rows {len(pa_i)}")
XT = torch.from_numpy(XL_i).to(DEV); PST = torch.from_numpy(ps_i).to(DEV)
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E_inc])
te = np.where(ym == 202608)[0]; first_te, last_te = int(te[0]), int(te[-1])
tr_idx = np.array([i for i in range(first_te - 1) if ST_i[i + 1] - ST_i[i] >= 50])
cut = int(len(tr_idx) * 0.85); tr1, va1 = tr_idx[:cut], tr_idx[cut:]
rowsel = np.concatenate([np.arange(ST_i[i], ST_i[i + 1]) for i in tr1[::7]])
rowsel_used = rowsel[::3]
XS = XT[torch.from_numpy(rowsel_used).to(DEV)]
mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6; del XS
R["calibration"] = {"n_train": int(len(tr_idx)), "n_val": int(len(va1)), "first_te": first_te, "last_te": last_te,
                    "n_rows_used": int(len(rowsel_used)), "max_row_used": int(rowsel_used.max()),
                    "mu_sha16": hashlib.sha256(mu.cpu().numpy().tobytes()).hexdigest()[:16],
                    "sd_sha16": hashlib.sha256(sd.cpu().numpy().tobytes()).hexdigest()[:16]}
log("calibration", json.dumps(R["calibration"]))

R["GATE_X_P"] = {}; R["GATE_X_OVERLAP_B_lineage_correct"] = {}; MODELS = {}
for F in CONFIG["folds"]:
    d = F["dir"]; ckp, cfp, pfp = f"{d}/models/mE1cX7_202608.pt", f"{d}/models/mE1cX7_202608_config.json", f"{d}/preds_fold/mE1cX7_202608.npz"
    C = json.load(open(cfp))
    assert C["fold"] == 202608 and C["seed_fold"] == F["seed"] and C["embargo_anchors"] == 1
    assert C["best_epoch_rule"] == "fix7" and C["best_epoch"] == 7 and C["causality_ok"]
    assert C["targets_sha256"] == sha(CONFIG["inc"]["targets"]) and C["fea82_sha256"] == sha(CONFIG["inc"]["fea82"]) \
       and C["fea89_sha256"] == sha(CONFIG["inc"]["fea89"]) and C["self_sha256"] == sha(CONFIG["trainer"])
    assert C["torch"] == torch.__version__ and C["gpu"] == torch.cuda.get_device_name(0)
    assert C["n_train"] == int(len(tr_idx)) and C["n_val"] == int(len(va1)) and C["n_test"] == int(te.size)
    mdl = Net(171).to(DEV); mdl.load_state_dict(torch.load(ckp, map_location="cpu", weights_only=True), strict=True); mdl.eval()
    with torch.no_grad(): assert abs(float(mdl.alpha()) - C["alpha_final"]) < 5e-4
    PA_new, sk = score_range(mdl, first_te, nA_i, ST_i, XT, PST, NW, mu, sd)
    Z = np.load(pfp); P_old = Z["P"]
    assert int(Z["first_te"]) == first_te and int(Z["last_te"]) == last_te and P_old.shape == PA_new.shape
    fo, fn = np.isfinite(P_old), np.isfinite(PA_new); both = fo & fn
    mx = float(np.abs(P_old[both] - PA_new[both]).max()) if both.any() else float("nan")
    bw = bool(np.array_equal(P_old, PA_new, equal_nan=True))
    R["GATE_X_P"][F["name"]] = {"fold_dir": d, "seed": F["seed"], "ckpt_sha256": sha(ckp),
        "preds_fold_sha256": sha(pfp), "fold_legs_sha256": C["legs_sha256"], "cutoff": C["cutoff"],
        "test_window": f'{C["first_test"]}..{C["last_test"]}', "n_rows": int(P_old.shape[0]),
        "n_cells_both_finite": int(both.sum()), "nan_pattern_equal": bool(np.array_equal(fo, fn)),
        "maxabs": mx, "bitwise_equal": bw, "P_sha16": hashlib.sha256(PA_new.tobytes()).hexdigest()[:16],
        "VERDICT": "PASS" if (bw and mx == 0.0) else "FAIL"}
    log("GATE X-P", F["name"], R["GATE_X_P"][F["name"]]["VERDICT"], "maxabs", mx)
    DEP = np.load(F["deployed"]); seg = DEP[first_te:last_te + 1]
    fo2, fn2 = np.isfinite(seg), np.isfinite(PA_new); b2 = fo2 & fn2
    mx2 = float(np.abs(seg[b2] - PA_new[b2]).max()) if b2.any() else float("nan")
    R["GATE_X_OVERLAP_B_lineage_correct"][F["name"]] = {"deployed": F["deployed"], "deployed_sha256": sha(F["deployed"]),
        "window": f"{iso(E_inc[first_te])}..{iso(E_inc[last_te])}", "n_anchors": int(last_te - first_te + 1),
        "n_cells_both_finite": int(b2.sum()), "nan_pattern_equal": bool(np.array_equal(fo2, fn2)), "maxabs": mx2,
        "bitwise_equal": bool(np.array_equal(seg, PA_new, equal_nan=True)),
        "VERDICT": "PASS" if (mx2 == 0.0 and np.array_equal(fo2, fn2)) else "FAIL"}
    log("GATE X-OVLP-B", F["name"], R["GATE_X_OVERLAP_B_lineage_correct"][F["name"]]["VERDICT"], "maxabs", mx2)
    MODELS[F["name"]] = mdl; del DEP
assert all(v["VERDICT"] == "PASS" for v in R["GATE_X_P"].values()), "GATE X-P FAILED"
np.save(f"{OUT}/mu_202608.npy", mu.cpu().numpy()); np.save(f"{OUT}/sd_202608.npy", sd.cpu().numpy())
del XT; torch.cuda.empty_cache()

# ═══════════ PHASE 2: GATE X-PRE, decomposed ═══════════
E_ext, nA_e, NW_e, pa_e, ps_e, ST_e, XL_e, NAMES82e = build(**{"tgt_p": CONFIG["ext"]["targets"], "f82_p": CONFIG["ext"]["fea82"], "f89_p": CONFIG["ext"]["fea89"]})
assert NW_e == NW and NAMES82e == NAMES82
n_i = len(pa_i)
same = np.array_equal(XL_i, XL_e[:n_i], equal_nan=True)
dif = ~((XL_i == XL_e[:n_i]) | (np.isnan(XL_i) & np.isnan(XL_e[:n_i])))
rows_d = np.nonzero(dif.any(1))[0]; cols_d = np.nonzero(dif.any(0))[0]
anch_d = np.unique(np.searchsorted(ST_e, rows_d, side="right") - 1) if rows_d.size else np.array([], int)
XPRE = {"strict": {"E_prefix_equal": bool(np.array_equal(E_inc, E_ext[:nA_i])),
                   "pair_a_prefix_equal": bool(np.array_equal(pa_i, pa_e[:n_i])),
                   "pair_s_prefix_equal": bool(np.array_equal(ps_i, ps_e[:n_i])),
                   "ST_prefix_equal": bool(np.array_equal(ST_i, ST_e[:nA_i + 1])),
                   "X_prefix_bitwise_equal": bool(same),
                   "X_prefix_maxabs": float(np.nanmax(np.abs(XL_i - XL_e[:n_i]))),
                   "VERDICT": "PASS" if same else "FAIL"}}
# the exemption, printed in full detail so it can be re-derived by hand
col_names171 = NAMES82 + [f"fea89_c{k}" for k in range(89)]
XPRE["exemption_detail"] = {
    "n_diff_cells": int(dif.sum()), "n_diff_rows": int(len(rows_d)),
    "columns_touched": [{"idx": int(c), "name": col_names171[int(c)],
                         "n_diff_cells": int(dif[:, c].sum()),
                         "maxabs": float(np.nanmax(np.abs(XL_i[dif[:, c], c] - XL_e[:n_i][dif[:, c], c])))} for c in cols_d],
    "anchors_touched": [iso(E_inc[i]) for i in anch_d],
    "anchor_idx_touched": [int(i) for i in anch_d],
    "arithmetic_check": {"n_anchors": int(len(anch_d)), "members_per_anchor": [int(ST_e[i + 1] - ST_e[i]) for i in anch_d],
                         "n_cols": int(len(cols_d)),
                         "upper_bound_cells": int(sum(int(ST_e[i + 1] - ST_e[i]) for i in anch_d) * len(cols_d)),
                         "actual_cells": int(dif.sum()),
                         "unchanged_because_both_exactly_zero": int(sum(int(ST_e[i + 1] - ST_e[i]) for i in anch_d) * len(cols_d) - int(dif.sum()))},
    "matches_declared_E0911B": bool(sorted([iso(E_inc[i]) for i in anch_d]) == sorted(E0911B_ANCHORS)
                                    and sorted(col_names171[int(c)] for c in cols_d) == sorted(E0911B_COLS))}
XPRE["exempt"] = {"VERDICT": "PASS" if XPRE["exemption_detail"]["matches_declared_E0911B"] else "FAIL",
                  "meaning": "every differing cell is inside the pre-declared E-0911-B set (5 anchors x {fund_ema,fund_now})"}
# calibration rows must be bitwise identical
cal_ok = bool(np.array_equal(XL_i[rowsel_used], XL_e[rowsel_used], equal_nan=True))
XPRE["calib"] = {"n_rows": int(len(rowsel_used)), "max_row": int(rowsel_used.max()),
                 "bitwise_equal": cal_ok, "VERDICT": "PASS" if cal_ok else "FAIL"}
# disjointness: rows this device reads vs rows that differ
read_lo, read_hi = int(ST_e[nA_i]), int(ST_e[nA_e])
disj = bool(len(rows_d) == 0 or (rows_d.min() >= read_hi or rows_d.max() < read_lo))
XPRE["disjoint"] = {"forward_rows": [read_lo, read_hi], "diff_rows_min": int(rows_d.min()) if rows_d.size else None,
                    "diff_rows_max": int(rows_d.max()) if rows_d.size else None,
                    "calib_rows_max": int(rowsel_used.max()),
                    "forward_disjoint_from_diff": disj,
                    "calib_disjoint_from_diff": bool(not np.isin(rowsel_used, rows_d).any()),
                    "VERDICT": "PASS" if (disj and not np.isin(rowsel_used, rows_d).any()) else "FAIL"}
R["GATE_X_PRE"] = XPRE
log("GATE X-PRE", json.dumps({k: (v.get("VERDICT") if isinstance(v, dict) else v) for k, v in XPRE.items()}))
log("  exemption", json.dumps(XPRE["exemption_detail"]))
json.dump(R, open(f"{OUT}/RECEIPT_r9_gates.json", "w"), indent=1, default=float)
for g in ("exempt", "calib", "disjoint"):
    assert XPRE[g]["VERDICT"] == "PASS", f"GATE X-PRE/{g} FAILED — STOP"
del XL_i
XT = torch.from_numpy(XL_e).to(DEV); PST = torch.from_numpy(ps_e).to(DEV); del XL_e
rowsel2 = np.concatenate([np.arange(ST_e[i], ST_e[i + 1]) for i in tr1[::7]])
assert np.array_equal(rowsel, rowsel2)
XS = XT[torch.from_numpy(rowsel2[::3]).to(DEV)]
mu2 = torch.nan_to_num(XS).mean(0); sd2 = torch.nan_to_num(XS).std(0) + 1e-6; del XS
R["calibration_recomputed_on_extended_matrix_identical"] = bool(torch.equal(mu, mu2) and torch.equal(sd, sd2))
assert R["calibration_recomputed_on_extended_matrix_identical"]
log("calibration on extended matrix: bitwise identical")

# ═══════════ PHASE 3: forward extension ═══════════
memb = (ST_e[1:] - ST_e[:-1])
R["new_anchor_inventory"] = [{"anchor": iso(E_ext[i]), "n_member_rows": int(memb[i])} for i in range(nA_i, nA_e)]
R["EXTENSION"] = {}; R["EXTENSION_repair5_VARIANT"] = {}
for F in CONFIG["folds"]:
    mdl = MODELS[F["name"]]
    NEW, sk_new = score_range(mdl, nA_i, nA_e, ST_e, XT, PST, NW, mu, sd)
    DEP = np.load(F["deployed"]); assert DEP.shape == (nA_i, NW)
    A = np.full((nA_e, NW), np.nan, np.float32); A[:nA_i] = DEP; A[nA_i:] = NEW
    assert np.array_equal(A[:nA_i], DEP, equal_nan=True)
    p = f"{OUT}/f10_v4RAWx_s{F['seed']}.npy"; np.save(p, A)
    fr = np.isfinite(A).any(1)
    R["EXTENSION"][F["name"]] = {"out": p, "out_sha256": sha(p), "shape": list(A.shape),
        "source_deployed": F["deployed"], "source_sha256": sha(F["deployed"]),
        "prefix_rows_bitwise_copied": int(nA_i),
        "scoring_fold": "mE1cX7_202608, cutoff 2026-07-31 20:00Z, embargo 1 (causal for every new anchor; STALE by one month vs the monthly-WF rule)",
        "new_anchors_total": int(nA_e - nA_i), "new_anchors_scored": int(np.isfinite(NEW).any(1).sum()),
        "new_anchors_left_NaN": [iso(E_ext[i]) for i in sk_new],
        "first_new_anchor": iso(E_ext[nA_i]), "last_new_anchor": iso(E_ext[nA_e - 1]),
        "last_finite_anchor": iso(E_ext[np.nonzero(fr)[0][-1]]),
        "finite_cells_per_new_anchor": [int(np.isfinite(NEW[k]).sum()) for k in range(NEW.shape[0])]}
    log("EXTENSION", F["name"], json.dumps({k: R["EXTENSION"][F["name"]][k] for k in ("out_sha256","new_anchors_scored","new_anchors_total","last_finite_anchor")}))
    # ---- repair5 VARIANT (changes 5 EXISTING rows -> book caliber -> USER RULING REQUIRED) ----
    i0 = int(anch_d.min()); i1 = int(anch_d.max()) + 1
    REP, sk_r = score_range(mdl, i0, i1, ST_e, XT, PST, NW, mu, sd)
    B = A.copy(); B[i0:i1] = REP
    q = f"{OUT}/f10_v4RAWx_repair5_s{F['seed']}.npy"; np.save(q, B)
    chg = ~((A[i0:i1] == REP) | (np.isnan(A[i0:i1]) & np.isnan(REP)))
    assert np.array_equal(np.delete(B, np.arange(i0, i1), axis=0), np.delete(A, np.arange(i0, i1), axis=0), equal_nan=True)
    R["EXTENSION_repair5_VARIANT"][F["name"]] = {"out": q, "out_sha256": sha(q),
        "rows_changed": [iso(E_ext[i]) for i in range(i0, i1)], "n_cells_changed": int(chg.sum()),
        "maxabs_change": float(np.nanmax(np.abs(A[i0:i1][chg] - REP[chg]))) if chg.any() else 0.0,
        "all_other_rows_bitwise_unchanged": True,
        "RULING_REQUIRED": "changes 5 EXISTING anchors of the deployed DL leg => book-behaviour caliber => user must rule; this round does not choose."}
    log("REPAIR5 VARIANT", F["name"], json.dumps(R["EXTENSION_repair5_VARIANT"][F["name"]]))
    del DEP

# ═══════════ PHASE 4: GATE X-OVERLAP-A (literal task gate, vs archived f10_A0) ═══════════
R["GATE_X_OVERLAP_A_literal_vs_f10_A0"] = {}
for F in CONFIG["folds"]:
    a0p = CONFIG["A0_lineage"][str(F["seed"])]; A0 = np.load(a0p)
    NEWX = np.load(f"{OUT}/f10_v4RAWx_s{F['seed']}.npy")[:nA_i]
    fo, fn = np.isfinite(A0), np.isfinite(NEWX); both = fo & fn
    mx = float(np.abs(A0[both] - NEWX[both]).max()) if both.any() else float("nan")
    rho = float(np.corrcoef(A0[both], NEWX[both])[0, 1]) if both.sum() > 10 else None
    R["GATE_X_OVERLAP_A_literal_vs_f10_A0"][F["name"]] = {"f10_A0": a0p, "f10_A0_sha256": sha(a0p),
        "n_cells_both_finite": int(both.sum()), "nan_pattern_equal": bool(np.array_equal(fo, fn)),
        "maxabs": mx, "pearson": rho, "bitwise_equal": bool(np.array_equal(A0, NEWX, equal_nan=True)),
        "VERDICT": "PASS" if (mx == 0.0 and np.array_equal(fo, fn)) else "FAIL",
        "WHY": "f10_A0 is the YEARLY 4-fold chain trained by /workspace/pod_f10_train_ext.py on the FORBIDDEN "
               "_ext lineage (dlw_ext targets 31d043e8..., axis 10206, cache 72eb7849...); that trainer never "
               "saves a per-fold model, so its 2026 fold weights do not exist anywhere on disk. No device can "
               "reproduce it bitwise. This gate cannot be met by construction, and its failure says nothing "
               "about the device that passed X-P."}
    log("GATE X-OVLP-A", F["name"], R["GATE_X_OVERLAP_A_literal_vs_f10_A0"][F["name"]]["VERDICT"], "maxabs", mx, "rho", rho)
R["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(R, open(f"{OUT}/RECEIPT_r9_gates.json", "w"), indent=1, default=float)
print("R9_EXTEND2_DONE", flush=True)
