"""R9 — F10/V2MAIN monthly-walk-forward FORWARD INFERENCE DEVICE + GATE X-P (bitwise).

WHAT THIS IS. The v4 F10 monthly walk-forward trainer
  /workspace/review_scratch/pod_f10_train_monthly_v4.py  (self_sha256 2147a7dd128be180...)
saves, per fold, ONLY a bare state_dict (models/mE1cX7_<YM>.pt: keys a, f.0.*, f.3.*, f.6.*) and the
fold's raw scores for every anchor >= first_te (preds_fold/mE1cX7_<YM>.npz key "P").
It does NOT save the per-fold standardisation (mu/sd). This device REBUILDS mu/sd by re-running the
trainer's own calibration arithmetic (trainer L317-L328, copied verbatim below) and then re-runs the
trainer's own scoring line (L423-L424, copied verbatim) so the serving operator order is identical.

GATE X-P (HARD, BITWISE): the rebuilt device must reproduce the fold's stored P EXACTLY (maxabs 0.0
AND identical NaN pattern). If it does not, the device is not the same object and STOPS here.

ENV WHITELIST (E-0826-D): EMPTY SET. This script consults NO environment variable. Every path,
every constant is a literal below, and the whole CONFIG dict + this file's own sha256 are written
into the output receipt.
"""
import os, sys, json, time, hashlib
import numpy as np
import torch, torch.nn as nn

# ─────────── E-0826-D: env whitelist = EMPTY SET, asserted ───────────
READ_ENV = []
assert READ_ENV == [], "this device must read no environment variable"
# the trainer's knobs, asserted absent-or-irrelevant: this device hardcodes all of them
_TRAINER_KNOBS = ["ARM","V2","SEED","COST","LDD","AFIX","LDC","CTXA","REC","PLE","EPOCHS","LR","NCOL",
                  "EXTRA","LPP","F10_DLW","F10_OUT","MWF_OUT","EMBARGO","MWF_TAG","MONTHS","FORCE",
                  "BEST_EP_FLOOR","BEST_EP_FIX","F10_GATE_JSON","MWF_ROOT"]
_ENV_PRESENT = {k: os.environ.get(k) for k in _TRAINER_KNOBS if os.environ.get(k) is not None}
assert _ENV_PRESENT == {}, f"E-0826-D: trainer knobs leaked into this process env: {_ENV_PRESENT}"

CONFIG = {
    "device": "r9_f10_mwf_forward",
    "purpose": "rebuild the v4 F10 monthly-WF forward scorer; GATE X-P bitwise vs the fold's own P",
    "chain": "v4 RAW (dlw_v4raw targets, holefix2 5m cache, raw_patch) — CALIBER_PIN_v4_2026-09-11",
    "fold": 202608, "seed": 42, "tag": "mE1cX7", "embargo_anchors": 1, "best_epoch_rule": "fix7",
    "arch": {"d": 171, "h": 256, "dropout": 0.1, "layers": "Linear-GELU-Drop-Linear-GELU-Drop-Linear"},
    "calib_rule": "trainer L317-L328 verbatim: tr_idx=[i<first_te-EMB with ST[i+1]-ST[i]>=50]; "
                  "cut=int(0.85*len); tr1=tr_idx[:cut]; rowsel=concat(arange(ST[i],ST[i+1]) for i in tr1[::7]); "
                  "mu=nan_to_num(XT[rowsel[::3]]).mean(0); sd=...std(0)+1e-6",
    "score_rule": "trainer L423-L424 verbatim: x=clamp((XT[a0:b0]-mu)/sd,-5,5); mdl.f(nan_to_num(x)).squeeze(-1)",
    "trainer": "/workspace/review_scratch/pod_f10_train_monthly_v4.py",
    "ckpt":    "/workspace/f8_v4/mwf/RAW_s42/shard3/models/mE1cX7_202608.pt",
    "ckpt_config": "/workspace/f8_v4/mwf/RAW_s42/shard3/models/mE1cX7_202608_config.json",
    "preds_fold": "/workspace/f8_v4/mwf/RAW_s42/shard3/preds_fold/mE1cX7_202608.npz",
    "inc_targets": "/workspace/dlw_v4raw/data/dlw_targets.npz",
    "inc_fea82":   "/workspace/dlw_v4raw/data/dlw_fea82.npz",
    "inc_fea89":   "/workspace/f8_v4/data/f8_fea89.npz",
    "ext_targets": "/workspace/uplift_2026-09-11/r6/out/dlw_targets_x0910.npz",
    "ext_fea82":   "/workspace/uplift_2026-09-11/r6/out/dlw_hf3_x0910/data/dlw_fea82.npz",
    "ext_fea89":   "/workspace/uplift_2026-09-11/r6/out/f8_v4_x0910/data/f8_fea89.npz",
    "out_dir":     "/workspace/uplift_2026-09-11/r9/out",
    "torch_device": "cuda",
}
SELF = os.path.abspath(__file__)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
CONFIG["self_sha256"] = sha(SELF)
def iso(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
REC = {"config": CONFIG, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

DEV = "cuda" if torch.cuda.is_available() else "cpu"
assert DEV == "cuda", "the fold was trained+scored on GPU; a CPU rerun cannot be bitwise"
REC["runtime"] = {"torch": torch.__version__, "cuda": torch.version.cuda,
                  "gpu": torch.cuda.get_device_name(0), "device": DEV,
                  "allow_tf32_matmul": bool(torch.backends.cuda.matmul.allow_tf32),
                  "allow_tf32_cudnn": bool(torch.backends.cudnn.allow_tf32),
                  "float32_matmul_precision": torch.get_float32_matmul_precision()}
log("runtime", json.dumps(REC["runtime"]))

# ─────────── the fold's own config: the identity we must match ───────────
FC = json.load(open(CONFIG["ckpt_config"]))
REC["fold_config"] = FC
assert FC["tag"] == "mE1cX7" and FC["fold"] == 202608 and FC["seed_fold"] == 42
assert FC["embargo_anchors"] == 1 and FC["best_epoch_rule"] == "fix7" and FC["best_epoch"] == 7
assert FC["torch"] == torch.__version__, (FC["torch"], torch.__version__)
assert FC["gpu"] == torch.cuda.get_device_name(0), (FC["gpu"], torch.cuda.get_device_name(0))
# input identity, hashed (CLAUDE.md rule 6 + E-0826-D)
IN_SHA = {"targets": sha(CONFIG["inc_targets"]), "fea82": sha(CONFIG["inc_fea82"]), "fea89": sha(CONFIG["inc_fea89"]),
          "trainer": sha(CONFIG["trainer"]), "ckpt": sha(CONFIG["ckpt"]), "preds_fold": sha(CONFIG["preds_fold"])}
REC["input_sha256"] = IN_SHA
assert IN_SHA["targets"] == FC["targets_sha256"], "targets sha != fold's recorded targets sha"
assert IN_SHA["fea82"] == FC["fea82_sha256"], "fea82 sha != fold's recorded fea82 sha"
assert IN_SHA["fea89"] == FC["fea89_sha256"], "fea89 sha != fold's recorded fea89 sha"
assert IN_SHA["trainer"] == FC["self_sha256"], "trainer sha != fold's recorded self_sha256"
log("input identity OK (targets/fea82/fea89/trainer sha256 == fold config)")

# ─────────── data (incumbent axis), built with the trainer's own operator order ───────────
TG = np.load(CONFIG["inc_targets"], allow_pickle=True)
E_ts = TG["E_ts"].astype(np.int64); y4s = TG["y4s"]; nA, NW = y4s.shape
assert np.all(np.diff(E_ts) == 14400)
FE = np.load(CONFIG["inc_fea82"], allow_pickle=True)
X82 = FE["X"]; pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
F9 = np.load(CONFIG["inc_fea89"], allow_pickle=True)
assert np.array_equal(F9["pair_a"].astype(np.int64), pa)
assert np.all(np.diff(pa) >= 0), "pairs must be anchor-sorted"
XL = np.concatenate([X82, F9["X"]], 1).astype(np.float32)
del X82, FE, F9
assert XL.shape[1] == 171, XL.shape
ST = np.searchsorted(pa, np.arange(nA + 1))
XT = torch.from_numpy(XL).to(DEV); del XL
PST = torch.from_numpy(ps).to(DEV)
log(f"incumbent: anchors {nA} ({iso(E_ts[0])}..{iso(E_ts[-1])}) rows {len(pa)} cols {XT.shape[1]}")

# ─────────── fold reconstruction (trainer L314-L328 verbatim arithmetic) ───────────
EMBM = 1
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E_ts])
YM = 202608
te = np.where(ym == YM)[0]; assert te.size > 0 and np.all(np.diff(te) == 1)
first_te, last_te = int(te[0]), int(te[-1])
tr_idx = np.array([i for i in range(first_te - EMBM) if ST[i + 1] - ST[i] >= 50])
max_tr = int(tr_idx[-1]); max_label_end = int(E_ts[max_tr]) + 48 * 300; cutoff = int(E_ts[first_te]) - EMBM * 14400
assert max_tr < first_te - EMBM and max_label_end <= cutoff
cut = int(len(tr_idx) * 0.85); tr1, va1 = tr_idx[:cut], tr_idx[cut:]
REC["fold_rebuild"] = {"first_te": first_te, "last_te": last_te, "n_test": int(te.size),
                       "n_train": int(len(tr_idx)), "n_val": int(len(va1)), "max_train_idx": max_tr,
                       "max_train_label_end": iso(max_label_end), "cutoff": iso(cutoff),
                       "first_test": iso(E_ts[first_te]), "last_test": iso(E_ts[last_te])}
# each of these is an independent check that the rebuilt fold IS the stored fold
for k, v in [("n_test", int(te.size)), ("n_train", int(len(tr_idx))), ("n_val", int(len(va1))),
             ("max_train_idx", max_tr)]:
    assert FC[k] == v, f"fold rebuild mismatch {k}: config {FC[k]} vs rebuilt {v}"
assert FC["first_test"] == time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(E_ts[first_te])))
assert FC["cutoff"] == time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(cutoff)))
assert FC["max_train_label_end"] == time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(max_label_end)))
log("fold rebuild matches stored config:", json.dumps(REC["fold_rebuild"]))

rowsel = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1[::7]])
XS = XT[torch.from_numpy(rowsel[::3]).to(DEV)]
mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6
del XS
REC["calibration"] = {"n_rowsel": int(len(rowsel)), "n_rowsel_used": int(len(rowsel[::3])),
                      "mu_sha16": hashlib.sha256(mu.cpu().numpy().tobytes()).hexdigest()[:16],
                      "sd_sha16": hashlib.sha256(sd.cpu().numpy().tobytes()).hexdigest()[:16],
                      "mu_first5": [float(v) for v in mu[:5].cpu().numpy()],
                      "sd_first5": [float(v) for v in sd[:5].cpu().numpy()]}
log("calibration rebuilt:", json.dumps(REC["calibration"]))

# ─────────── the model (trainer's Net, inference subset) ───────────
class Net(nn.Module):
    def __init__(s, d=171, h=256, p=0.1):
        super().__init__()
        s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p),
                            nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
        s.a = nn.Parameter(torch.tensor(-2.303))
    def alpha(s): return 0.02 + 0.88 * torch.sigmoid(s.a)

state = torch.load(CONFIG["ckpt"], map_location="cpu", weights_only=True)
REC["ckpt_keys"] = sorted(list(state.keys()))
mdl = Net(int(XT.shape[1])).to(DEV)
missing, unexpected = mdl.load_state_dict(state, strict=True), None
mdl.eval()
REC["alpha_from_ckpt"] = float(mdl.alpha())
assert abs(REC["alpha_from_ckpt"] - FC["alpha_final"]) < 5e-4, (REC["alpha_from_ckpt"], FC["alpha_final"])
log(f"ckpt loaded strict; keys {REC['ckpt_keys']}; alpha {REC['alpha_from_ckpt']:.4f} (config {FC['alpha_final']})")

def score_range(i_lo, i_hi, ST_, XT_, PST_, NW_, mu_, sd_):
    """trainer L416-L424 verbatim (diagnostic PA block)."""
    out = np.full((i_hi - i_lo, NW_), np.nan, np.float32)
    with torch.no_grad():
        for i in range(i_lo, i_hi):
            a0, b0 = int(ST_[i]), int(ST_[i + 1])
            if b0 - a0 < 50:
                continue
            x = torch.clamp((XT_[a0:b0] - mu_) / sd_, -5, 5)
            out[i - i_lo, PST_[a0:b0].cpu().numpy()] = mdl.f(torch.nan_to_num(x)).squeeze(-1).cpu().numpy()
    return out

# ═══════════ GATE X-P : bitwise reproduction of the fold's own P ═══════════
log("GATE X-P: re-inferring anchors %d..%d (%s..%s)" % (first_te, nA - 1, iso(E_ts[first_te]), iso(E_ts[nA - 1])))
PA_new = score_range(first_te, nA, ST, XT, PST, NW, mu, sd)
Z = np.load(CONFIG["preds_fold"]); P_old = Z["P"]
assert int(Z["first_te"]) == first_te and int(Z["last_te"]) == last_te
assert P_old.shape == PA_new.shape, (P_old.shape, PA_new.shape)
fo, fn = np.isfinite(P_old), np.isfinite(PA_new)
both = fo & fn
maxabs = float(np.abs(P_old[both] - PA_new[both]).max()) if both.any() else float("nan")
bitwise = bool(np.array_equal(P_old, PA_new, equal_nan=True))
GATE_XP = {"n_rows": int(P_old.shape[0]), "n_cols": int(P_old.shape[1]),
           "nan_pattern_equal": bool(np.array_equal(fo, fn)),
           "n_cells_both_finite": int(both.sum()),
           "n_cells_finite_old_only": int((fo & ~fn).sum()), "n_cells_finite_new_only": int((~fo & fn).sum()),
           "maxabs": maxabs, "bitwise_equal": bitwise,
           "P_old_sha16": hashlib.sha256(P_old.tobytes()).hexdigest()[:16],
           "P_new_sha16": hashlib.sha256(PA_new.tobytes()).hexdigest()[:16],
           "VERDICT": "PASS" if (bitwise and maxabs == 0.0) else "FAIL"}
REC["GATE_X_P"] = GATE_XP
log("GATE X-P:", json.dumps(GATE_XP))
os.makedirs(CONFIG["out_dir"], exist_ok=True)
json.dump(REC, open(f"{CONFIG['out_dir']}/RECEIPT_r9_gateXP.json", "w"), indent=1, default=float)
if GATE_XP["VERDICT"] != "PASS":
    log("GATE X-P FAILED — STOPPING. No extension is produced. A failed gate is a valid result.")
    sys.exit(3)
np.save(f"{CONFIG['out_dir']}/mu_202608_s42.npy", mu.cpu().numpy())
np.save(f"{CONFIG['out_dir']}/sd_202608_s42.npy", sd.cpu().numpy())
log("GATE X-P PASSED. mu/sd persisted.")
print("GATE_XP_DONE", flush=True)
