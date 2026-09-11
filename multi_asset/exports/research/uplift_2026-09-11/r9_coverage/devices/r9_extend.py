"""R9 — GATE X-P (all canonical folds) + GATE X-PRE + forward extension + GATE X-OVERLAP.

ENV WHITELIST (E-0826-D): EMPTY SET. No environment variable is consulted; every path and constant
is a literal in CONFIG below; CONFIG + this file's sha256 go into the receipt.

LINEAGE NOTE (E-0825-G/H: never infer semantics from a directory name — this was verified from code):
  * /workspace/f8_v4/mwf      RAW_s42 was trained with legs sha 561fc1475bfd  (superseded; cf. /workspace/f8_v4/models/bad_legs_20260909)
  * /workspace/f8_v4/mwf_v4b  RAW_s{42,2027} trained with legs sha c535decd6524 = /workspace/f8_v4/data/f10v2_legs.npz
    and merge_mwf_v4b.py wrote them into dev_v4/f8_2026-08-22/preds/f10_v4RAW_s{42,2027}.npy
    (merge.json splice sha 58d64a6ff9684589 / 47046ccd6dc7937c == the arrays on disk). ==> mwf_v4b is canonical.
  * dev_v4/.../f10_A0_s{42,2027}.npy is a DIFFERENT lineage: build_dev_v4.py aligns
    /workspace/f8_ext/preds/f10_V2MAIN_s{seed}.npy (the YEARLY 4-fold walk-forward from
    /workspace/pod_f10_train_ext.py) onto the v4 axis. That trainer never saves a per-fold model.
"""
import os, sys, json, time, hashlib
import numpy as np
import torch, torch.nn as nn

READ_ENV = []
assert READ_ENV == []
_KNOBS = ["ARM","V2","SEED","COST","LDD","AFIX","LDC","CTXA","REC","PLE","EPOCHS","LR","NCOL","EXTRA","LPP",
          "F10_DLW","F10_OUT","MWF_OUT","EMBARGO","MWF_TAG","MONTHS","FORCE","BEST_EP_FLOOR","BEST_EP_FIX",
          "F10_GATE_JSON","MWF_ROOT","PHI","LOOK","FPRED","FSEED","LEGS","CAL","SLOW_NPY"]
_LEAK = {k: os.environ.get(k) for k in _KNOBS if os.environ.get(k) is not None}
assert _LEAK == {}, f"E-0826-D: knobs leaked into env: {_LEAK}"

OUT = "/workspace/uplift_2026-09-11/r9/out"
CONFIG = {
    "device": "r9_f10_mwf_forward_extend", "caliber": "v4 chain 2026-09-09 (CALIBER_PIN_v4_2026-09-11)",
    "fold": 202608, "tag": "mE1cX7", "embargo_anchors": 1, "best_epoch_rule": "fix7",
    "arch": {"d": 171, "h": 256, "dropout": 0.1},
    "folds": [
        {"name": "mwf_v4b_RAW_s42",  "seed": 42,   "dir": "/workspace/f8_v4/mwf_v4b/RAW_s42/shard3",
         "deployed": "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s42.npy",   "canonical": True},
        {"name": "mwf_v4b_RAW_s2027","seed": 2027, "dir": "/workspace/f8_v4/mwf_v4b/RAW_s2027/shard3",
         "deployed": "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s2027.npy", "canonical": True},
        {"name": "mwf_RAW_s42",      "seed": 42,   "dir": "/workspace/f8_v4/mwf/RAW_s42/shard3",
         "deployed": None, "canonical": False},
    ],
    "inc": {"targets": "/workspace/dlw_v4raw/data/dlw_targets.npz",
            "fea82":   "/workspace/dlw_v4raw/data/dlw_fea82.npz",
            "fea89":   "/workspace/f8_v4/data/f8_fea89.npz"},
    "ext": {"targets": "/workspace/uplift_2026-09-11/r6/out/dlw_targets_x0910.npz",
            "fea82":   "/workspace/uplift_2026-09-11/r6/out/dlw_hf3_x0910/data/dlw_fea82.npz",
            "fea89":   "/workspace/uplift_2026-09-11/r6/out/f8_v4_x0910/data/f8_fea89.npz"},
    "A0_lineage": {"s42":   "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy",
                   "s2027": "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s2027.npy"},
    "trainer": "/workspace/review_scratch/pod_f10_train_monthly_v4.py",
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
    """verbatim pod_f10_train_monthly_v4.py L416-L424 (the fold's own diagnostic scoring block)."""
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
    TG = np.load(tgt_p, allow_pickle=True)
    E = TG["E_ts"].astype(np.int64); nA, NW = TG["y4s"].shape
    assert np.all(np.diff(E) == 14400)
    FE = np.load(f82_p, allow_pickle=True); X82 = FE["X"]; pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
    F9 = np.load(f89_p, allow_pickle=True); X89 = F9["X"]
    assert np.array_equal(F9["pair_a"].astype(np.int64), pa) and np.all(np.diff(pa) >= 0)
    XL = np.concatenate([X82, X89], 1).astype(np.float32)
    assert XL.shape[1] == 171
    del FE, F9, X82, X89
    ST = np.searchsorted(pa, np.arange(nA + 1))
    return E, nA, NW, pa, ps, ST, XL

# ═══════════ PHASE 1: incumbent axis, calibration, GATE X-P for every fold ═══════════
E_inc, nA_i, NW, pa_i, ps_i, ST_i, XL_i = build(CONFIG["inc"]["targets"], CONFIG["inc"]["fea82"], CONFIG["inc"]["fea89"])
log(f"incumbent axis {nA_i} ({iso(E_inc[0])}..{iso(E_inc[-1])}) rows {len(pa_i)}")
XT = torch.from_numpy(XL_i).to(DEV); PST = torch.from_numpy(ps_i).to(DEV)
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E_inc])
te = np.where(ym == 202608)[0]; first_te, last_te = int(te[0]), int(te[-1])
tr_idx = np.array([i for i in range(first_te - 1) if ST_i[i + 1] - ST_i[i] >= 50])
cut = int(len(tr_idx) * 0.85); tr1, va1 = tr_idx[:cut], tr_idx[cut:]
rowsel = np.concatenate([np.arange(ST_i[i], ST_i[i + 1]) for i in tr1[::7]])
XS = XT[torch.from_numpy(rowsel[::3]).to(DEV)]
mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6; del XS
MU_SHA = hashlib.sha256(mu.cpu().numpy().tobytes()).hexdigest()[:16]
SD_SHA = hashlib.sha256(sd.cpu().numpy().tobytes()).hexdigest()[:16]
R["calibration_incumbent"] = {"n_train": int(len(tr_idx)), "n_val": int(len(va1)), "first_te": first_te,
                              "last_te": last_te, "mu_sha16": MU_SHA, "sd_sha16": SD_SHA}
log("calibration", json.dumps(R["calibration_incumbent"]))

R["GATE_X_P"] = {}; MODELS = {}
for F in CONFIG["folds"]:
    d = F["dir"]; ckp = f"{d}/models/mE1cX7_202608.pt"; cfp = f"{d}/models/mE1cX7_202608_config.json"
    pfp = f"{d}/preds_fold/mE1cX7_202608.npz"
    C = json.load(open(cfp))
    assert C["fold"] == 202608 and C["seed_fold"] == F["seed"] and C["embargo_anchors"] == 1
    assert C["best_epoch_rule"] == "fix7" and C["best_epoch"] == 7
    assert C["targets_sha256"] == sha(CONFIG["inc"]["targets"]) and C["fea82_sha256"] == sha(CONFIG["inc"]["fea82"]) \
       and C["fea89_sha256"] == sha(CONFIG["inc"]["fea89"]) and C["self_sha256"] == sha(CONFIG["trainer"])
    assert C["torch"] == torch.__version__ and C["gpu"] == torch.cuda.get_device_name(0)
    assert C["n_train"] == int(len(tr_idx)) and C["n_val"] == int(len(va1)) and C["n_test"] == int(te.size)
    mdl = Net(171).to(DEV); mdl.load_state_dict(torch.load(ckp, map_location="cpu", weights_only=True), strict=True); mdl.eval()
    with torch.no_grad(): al = float(mdl.alpha())
    assert abs(al - C["alpha_final"]) < 5e-4
    PA_new, sk = score_range(mdl, first_te, nA_i, ST_i, XT, PST, NW, mu, sd)
    Z = np.load(pfp); P_old = Z["P"]
    assert int(Z["first_te"]) == first_te and int(Z["last_te"]) == last_te and P_old.shape == PA_new.shape
    fo, fn = np.isfinite(P_old), np.isfinite(PA_new); both = fo & fn
    mx = float(np.abs(P_old[both] - PA_new[both]).max()) if both.any() else float("nan")
    bw = bool(np.array_equal(P_old, PA_new, equal_nan=True))
    g = {"fold_dir": d, "seed": F["seed"], "canonical": F["canonical"],
         "ckpt_sha256": sha(ckp), "preds_fold_sha256": sha(pfp), "fold_legs_sha256": C["legs_sha256"],
         "n_rows": int(P_old.shape[0]), "n_cells_both_finite": int(both.sum()),
         "nan_pattern_equal": bool(np.array_equal(fo, fn)),
         "n_anchors_skipped_lt50_members": len(sk),
         "maxabs": mx, "bitwise_equal": bw,
         "P_old_sha16": hashlib.sha256(P_old.tobytes()).hexdigest()[:16],
         "P_new_sha16": hashlib.sha256(PA_new.tobytes()).hexdigest()[:16],
         "VERDICT": "PASS" if (bw and mx == 0.0) else "FAIL"}
    R["GATE_X_P"][F["name"]] = g
    log("GATE X-P", F["name"], json.dumps({k: g[k] for k in ("maxabs", "bitwise_equal", "VERDICT")}))
    MODELS[F["name"]] = mdl
    # GATE X-OVERLAP-B (lineage-correct): does the DEPLOYED array carry this fold's P bitwise?
    if F["deployed"]:
        DEP = np.load(F["deployed"])
        seg = DEP[first_te:last_te + 1]
        fo2, fn2 = np.isfinite(seg), np.isfinite(PA_new)
        b2 = fo2 & fn2
        mx2 = float(np.abs(seg[b2] - PA_new[b2]).max()) if b2.any() else float("nan")
        R.setdefault("GATE_X_OVERLAP_B_lineage_correct", {})[F["name"]] = {
            "deployed": F["deployed"], "deployed_sha256": sha(F["deployed"]),
            "window": f"{iso(E_inc[first_te])}..{iso(E_inc[last_te])}", "n_anchors": int(last_te - first_te + 1),
            "nan_pattern_equal": bool(np.array_equal(fo2, fn2)), "n_cells_both_finite": int(b2.sum()),
            "maxabs": mx2, "bitwise_equal": bool(np.array_equal(seg, PA_new, equal_nan=True)),
            "VERDICT": "PASS" if (mx2 == 0.0 and np.array_equal(fo2, fn2)) else "FAIL"}
        log("GATE X-OVERLAP-B", F["name"], json.dumps(R["GATE_X_OVERLAP_B_lineage_correct"][F["name"]]))
        del DEP
json.dump(R, open(f"{OUT}/RECEIPT_r9_gates_partial.json", "w"), indent=1, default=float)
if not all(v["VERDICT"] == "PASS" for v in R["GATE_X_P"].values()):
    log("GATE X-P FAILED on at least one fold — STOP. No extension produced.")
    sys.exit(3)
np.save(f"{OUT}/mu_202608.npy", mu.cpu().numpy()); np.save(f"{OUT}/sd_202608.npy", sd.cpu().numpy())
del XT; torch.cuda.empty_cache()

# ═══════════ PHASE 2: GATE X-PRE — the extended feature matrix must be a bitwise prefix-extension ═══════════
E_ext, nA_e, NW_e, pa_e, ps_e, ST_e, XL_e = build(CONFIG["ext"]["targets"], CONFIG["ext"]["fea82"], CONFIG["ext"]["fea89"])
assert NW_e == NW
n_i = len(pa_i)
PRE = {"inc_rows": int(n_i), "ext_rows": int(len(pa_e)), "new_rows": int(len(pa_e) - n_i),
       "inc_anchors": int(nA_i), "ext_anchors": int(nA_e), "new_anchors": int(nA_e - nA_i),
       "E_prefix_equal": bool(np.array_equal(E_inc, E_ext[:nA_i])),
       "pair_a_prefix_equal": bool(np.array_equal(pa_i, pa_e[:n_i])),
       "pair_s_prefix_equal": bool(np.array_equal(ps_i, ps_e[:n_i])),
       "X_prefix_bitwise_equal": bool(np.array_equal(XL_i, XL_e[:n_i], equal_nan=True)),
       "X_prefix_maxabs": float(np.nanmax(np.abs(XL_i - XL_e[:n_i]))) if n_i else 0.0,
       "ST_prefix_equal": bool(np.array_equal(ST_i[:nA_i], ST_e[:nA_i]))}
PRE["VERDICT"] = "PASS" if (PRE["E_prefix_equal"] and PRE["pair_a_prefix_equal"] and PRE["pair_s_prefix_equal"]
                            and PRE["X_prefix_bitwise_equal"] and PRE["ST_prefix_equal"]) else "FAIL"
R["GATE_X_PRE"] = PRE
log("GATE X-PRE", json.dumps(PRE))
del XL_i
json.dump(R, open(f"{OUT}/RECEIPT_r9_gates_partial.json", "w"), indent=1, default=float)
if PRE["VERDICT"] != "PASS":
    log("GATE X-PRE FAILED — STOP."); sys.exit(4)

XT = torch.from_numpy(XL_e).to(DEV); PST = torch.from_numpy(ps_e).to(DEV); del XL_e
# mu/sd must be identical when recomputed on the extended matrix (training rows are all in the prefix)
rowsel2 = np.concatenate([np.arange(ST_e[i], ST_e[i + 1]) for i in tr1[::7]])
assert np.array_equal(rowsel, rowsel2)
XS = XT[torch.from_numpy(rowsel2[::3]).to(DEV)]
mu2 = torch.nan_to_num(XS).mean(0); sd2 = torch.nan_to_num(XS).std(0) + 1e-6; del XS
R["calibration_on_extended_matrix"] = {
    "mu_sha16": hashlib.sha256(mu2.cpu().numpy().tobytes()).hexdigest()[:16],
    "sd_sha16": hashlib.sha256(sd2.cpu().numpy().tobytes()).hexdigest()[:16],
    "equal_to_incumbent": bool(torch.equal(mu, mu2) and torch.equal(sd, sd2))}
assert R["calibration_on_extended_matrix"]["equal_to_incumbent"], "calibration drifted on the extended matrix"
log("calibration on extended matrix bitwise identical")

# ═══════════ PHASE 3: forward extension, new anchors only ═══════════
memb = (ST_e[1:] - ST_e[:-1])
R["new_anchor_inventory"] = [{"i": int(i), "anchor": iso(E_ext[i]), "n_member_rows": int(memb[i])} for i in range(nA_i, nA_e)]
R["EXTENSION"] = {}
for F in CONFIG["folds"]:
    if not F["canonical"]:
        continue
    mdl = MODELS[F["name"]]
    NEW, sk = score_range(mdl, nA_i, nA_e, ST_e, XT, PST, NW, mu, sd)
    DEP = np.load(F["deployed"])
    assert DEP.shape == (nA_i, NW)
    OUTA = np.full((nA_e, NW), np.nan, np.float32)
    OUTA[:nA_i] = DEP                       # incumbent rows: bitwise copy
    OUTA[nA_i:] = NEW                       # new anchors: device; NaN stays NaN (never interpolated)
    assert np.array_equal(OUTA[:nA_i], DEP, equal_nan=True), "prefix not bitwise preserved"
    p = f"{OUT}/f10_v4RAWx_s{F['seed']}.npy"; np.save(p, OUTA)
    finrow = np.isfinite(OUTA).any(1)
    R["EXTENSION"][F["name"]] = {
        "out": p, "out_sha256": sha(p), "shape": list(OUTA.shape),
        "source_deployed": F["deployed"], "source_sha256": sha(F["deployed"]),
        "scoring_fold": "mE1cX7_202608 (cutoff 2026-07-31 20:00Z, embargo 1) — STALE by 1 month vs the monthly rule",
        "new_anchors_scored": int(np.isfinite(NEW).any(1).sum()), "new_anchors_total": int(nA_e - nA_i),
        "new_anchors_left_NaN": [iso(E_ext[i]) for i in sk],
        "new_finite_cells_per_anchor": [int(np.isfinite(NEW[k]).sum()) for k in range(NEW.shape[0])],
        "prefix_bitwise_preserved": True,
        "first_new_anchor": iso(E_ext[nA_i]), "last_new_anchor": iso(E_ext[nA_e - 1]),
        "last_finite_anchor": iso(E_ext[np.nonzero(finrow)[0][-1]])}
    log("EXTENSION", F["name"], json.dumps({k: R["EXTENSION"][F["name"]][k] for k in
        ("out_sha256", "new_anchors_scored", "new_anchors_total", "last_finite_anchor")}))

# ═══════════ PHASE 4: GATE X-OVERLAP-A — literal, against the archived f10_A0 arrays ═══════════
R["GATE_X_OVERLAP_A_literal_vs_f10_A0"] = {}
for F in CONFIG["folds"]:
    if not F["canonical"]:
        continue
    a0p = CONFIG["A0_lineage"][f"s{F['seed']}"]
    A0 = np.load(a0p)
    NEWX = np.load(f"{OUT}/f10_v4RAWx_s{F['seed']}.npy")[:nA_i]
    fo, fn = np.isfinite(A0), np.isfinite(NEWX); both = fo & fn
    mx = float(np.abs(A0[both] - NEWX[both]).max()) if both.any() else float("nan")
    rho = float(np.corrcoef(A0[both], NEWX[both])[0, 1]) if both.sum() > 10 else None
    R["GATE_X_OVERLAP_A_literal_vs_f10_A0"][F["name"]] = {
        "f10_A0": a0p, "f10_A0_sha256": sha(a0p),
        "n_cells_both_finite": int(both.sum()), "nan_pattern_equal": bool(np.array_equal(fo, fn)),
        "maxabs": mx, "pearson": rho,
        "bitwise_equal": bool(np.array_equal(A0, NEWX, equal_nan=True)),
        "VERDICT": "PASS" if (mx == 0.0 and np.array_equal(fo, fn)) else "FAIL"}
    log("GATE X-OVERLAP-A", F["name"], json.dumps(R["GATE_X_OVERLAP_A_literal_vs_f10_A0"][F["name"]]))
R["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(R, open(f"{OUT}/RECEIPT_r9_gates.json", "w"), indent=1, default=float)
print("R9_EXTEND_DONE", flush=True)
