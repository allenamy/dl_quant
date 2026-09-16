"""F10 numpy export, v4 (FX-TRAIN TRN-03 + TRN-14, 2026-09-16; AUDIT_TRAIN 7e1ecf9a; FACT_TABLE_TRN §TRN-03/§TRN-14).
Ancestor kept beside this file as pod_f10_np_export_v4.r0_3e304c27.py (= T/pod_f10_np_export.py, the September program, byte-identical).

WHAT THE ANCESTOR DID WRONG (measured, FACT_TABLE 03.1-03.3, 03.10):
  * three silent defaults — SEED=42, F10_OUT=/workspace/f8_ext, F10_DLW=/workspace/dlw_ext — so a bare call read the PREVIOUS
    generation and wrote into the IN-SERVICE models directory (the R1 family, removed from the refit on 2026-09-12, never here);
  * it ran `np.savez(...)` UNCONDITIONALLY and only then printed V1_PASS/V1_FAIL and exited 0/3, so a FAILED gate still left a
    complete, loadable deployment artifact at the live path — the gate existed, its verdict did not control the write;
  * `trained_through` was max(E_ts) of the targets file, i.e. the DATA AXIS END — a third quantity, further from what the
    optimiser saw than either the training pool end or the label cutoff, both of which the refit sidecar already records.

WHAT THIS PROGRAM DOES:
  1. Every locator is REQUIRED and refused (rc 2) BEFORE torch is imported: F10_OUT F10_DLW SEED F10_NP_OUT F10_SIDECAR
     F10_NP_RECEIPT F10_GENERATION F10_BEST_EP_RULE. There is no default anywhere, so no call can mean the previous generation.
  2. The checkpoint is bound to the refit sidecar BEFORE anything is computed: the complete key set must be present (a missing
     key is a refusal, never a skipped check), the .pt's sha is RECOMPUTED here and must equal the sidecar's pt_sha256, the
     expected seed must agree across `seed` / `env_given.SEED` / the .pt filename / the sidecar filename, and `best_ep_rule`
     must equal F10_BEST_EP_RULE (the month contract's rule). The chain additionally runs chain_lib's prereq_refit_sidecar,
     which is the SAME contract from the driver's side — this program does not reimplement it, it refuses without it.
  3. VERDICT BEFORE WRITE. V1 (np vs torch on real feature rows: median Spearman >= V1_RHO and maxabs <= V1_MAX) is computed
     first. On FAIL nothing is written at all and the program exits 3 with a PASS=false receipt. On PASS the npz is written to
     a temp path and os.replace'd into F10_NP_OUT, and an EXISTING F10_NP_OUT is refused unless F10_NP_REPLACE_SHA256 names the
     sha of the file being replaced (so overwriting the live artifact is an explicit, checked act).
  4. TRN-14: the npz carries trained_through_label_utc / trained_through_pool_end_utc / trained_through_tr1_end_utc /
     data_axis_end_utc / best_ep_rule / pt_sha256 / generation / self_sha256, and KEEPS the legacy `trained_through` key with
     the ancestor's value so no existing reader breaks — plus `trained_through_meaning` naming it as the data axis end.
  5. Receipt through v4_gate_common.finalize (gate F10_NP_EXPORT; inputs pt / sidecar / targets / fea82 / fea89 / npz), so the
     swap step can `require` it instead of trusting that a file exists.

LEGACY COMPARE MODE (F10_SIDECAR=NONE_LEGACY_ARTIFACT): for the positive control on a checkpoint produced BEFORE the sidecar
existed (the in-service f10_live_s42.pt has none — FACT_TABLE 03.6). It runs V1 and, with F10_NP_COMPARE=<npz>, compares every
array with that file, and it REFUSES TO WRITE ANY npz whatever the verdict. It exists so the control can be run at all; it is
never a path to producing a deployable file.
usage: env F10_OUT=... F10_DLW=... SEED=42 F10_SIDECAR=... F10_NP_OUT=... F10_NP_RECEIPT=... F10_GENERATION=v4_2026-10 \
           F10_BEST_EP_RULE=fix7 python3 pod_f10_np_export_v4.py
"""
import hashlib
import json
import os
import re
import sys
import time

_REQ = ("F10_OUT", "F10_DLW", "SEED", "F10_NP_OUT", "F10_SIDECAR", "F10_NP_RECEIPT", "F10_GENERATION", "F10_BEST_EP_RULE")
_missing = [k for k in _REQ if not os.environ.get(k)]
if _missing:
    print(f"NP_EXPORT_REFUSED: env {_missing} not set — pod_f10_np_export_v4.py has NO defaults (the ancestor's SEED=42 / "
          f"F10_OUT=/workspace/f8_ext / F10_DLW=/workspace/dlw_ext defaults are the reason this file exists); pass every "
          f"locator explicitly (chain_v4_monthly.sh does)", flush=True)
    sys.exit(2)

OUT = os.environ["F10_OUT"]
DLW = os.environ["F10_DLW"]
SEED = int(os.environ["SEED"])
NP_OUT = os.environ["F10_NP_OUT"]
SIDECAR = os.environ["F10_SIDECAR"]
RECEIPT = os.environ["F10_NP_RECEIPT"]
GENERATION = os.environ["F10_GENERATION"]
BEST_EP_RULE = os.environ["F10_BEST_EP_RULE"]
REPLACE_SHA = os.environ.get("F10_NP_REPLACE_SHA256", "")
COMPARE = os.environ.get("F10_NP_COMPARE", "")
LEGACY = SIDECAR == "NONE_LEGACY_ARTIFACT"
V1_RHO, V1_MAX, V1_ROWS = 0.99999, 1e-5, 30000      # the ancestor's criterion, verbatim (PREREG addendum §A V1)
CK = f"{OUT}/models/f10_live_s{SEED}.pt"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4_gate_common import finalize, sha256_file                                    # noqa: E402

INPUTS = {"pt": CK, "refit_sidecar": None if LEGACY else SIDECAR,
          "targets": f"{DLW}/data/dlw_targets.npz", "fea82": f"{DLW}/data/dlw_fea82.npz", "fea89": f"{OUT}/data/f8_fea89.npz"}


def refuse(why, detail):
    print(f"NP_EXPORT_REFUSED {why} {json.dumps(detail, default=str)[:600]}", flush=True)
    finalize("F10_NP_EXPORT", {"PASS": False, "REFUSED": {"why": why, **detail}, "wrote_npz": False,
                               "generation": GENERATION, "seed": SEED}, RECEIPT, INPUTS)


# ── (a) inputs exist ────────────────────────────────────────────────────────────────────────────────────────────────────────
_absent = {k: v for k, v in INPUTS.items() if v is not None and not os.path.isfile(v)}
if _absent:
    refuse("missing_inputs", {"missing": _absent})
if COMPARE and not os.path.isfile(COMPARE):
    refuse("missing_compare_file", {"F10_NP_COMPARE": COMPARE})

# ── (b) the output path is decided before anything is computed ─────────────────────────────────────────────────────────────
if LEGACY:
    if COMPARE == "":
        refuse("legacy_mode_without_compare", {"why2": "F10_SIDECAR=NONE_LEGACY_ARTIFACT exists only to CHECK an existing "
                                                       "artifact; without F10_NP_COMPARE it would compute a verdict about "
                                                       "nothing and write nothing"})
elif os.path.exists(NP_OUT):
    _cur = sha256_file(NP_OUT)
    if REPLACE_SHA != _cur:
        refuse("output_exists", {"F10_NP_OUT": NP_OUT, "current_sha256": _cur,
                                 "F10_NP_REPLACE_SHA256": REPLACE_SHA or None,
                                 "why2": "replacing an existing deployment artifact must name the sha it replaces "
                                         "(the ancestor overwrote the in-service file by default, and did so even on a FAILED gate)"})

# ── (c) the checkpoint is bound to the refit sidecar, before torch ─────────────────────────────────────────────────────────
side = {}
if not LEGACY:
    try:
        side = json.load(open(SIDECAR))
    except Exception as e:
        refuse("sidecar_unreadable", {"sidecar": SIDECAR, "error": f"{type(e).__name__}: {e}"})
    if not isinstance(side, dict):
        refuse("sidecar_not_an_object", {"sidecar": SIDECAR, "type": type(side).__name__})
    _need = ("seed", "best_ep_rule", "best_ep_kept", "env_given", "inputs", "inputs_sha256", "pt", "pt_sha256",
             "self_sha256", "trained_through", "trained_through_label_utc", "trained_through_pool_end_utc",
             "trained_through_tr1_end_utc", "data_axis_end_utc")
    _miss = [k for k in _need if k not in side or side[k] in (None, "", {}, [])]
    if _miss:
        refuse("sidecar_incomplete", {"missing_keys": _miss, "why2": "a missing key is a refusal, never a skipped check"})
    _bad = {}
    if int(side["seed"]) != SEED:
        _bad["sidecar_seed"] = side["seed"]
    if str(side["env_given"].get("SEED")) != str(SEED):
        _bad["env_given_SEED"] = side["env_given"].get("SEED")
    if os.path.basename(SIDECAR) != f"f10_live_s{SEED}.json":
        _bad["sidecar_filename"] = os.path.basename(SIDECAR)
    if os.path.basename(str(side["pt"])) != f"f10_live_s{SEED}.pt":
        _bad["sidecar_pt_filename"] = side["pt"]
    if _bad:
        _bad["expected_seed"] = SEED
        refuse("seed_disagreement", _bad)
    if not _HEX64.match(str(side["pt_sha256"]).lower()):
        refuse("sidecar_pt_sha_not_a_digest", {"pt_sha256": side["pt_sha256"]})
    _ck_sha = sha256_file(CK)
    if _ck_sha != str(side["pt_sha256"]).lower():
        refuse("pt_sha_mismatch", {"pt": CK, "recomputed": _ck_sha, "sidecar_pt_sha256": side["pt_sha256"],
                                   "why2": "the sidecar is a claim about WHICH checkpoint; it is verified by recomputing the sha"})
    if str(side["best_ep_rule"]) != BEST_EP_RULE:
        refuse("best_ep_rule_mismatch", {"sidecar": side["best_ep_rule"], "F10_BEST_EP_RULE": BEST_EP_RULE})

# ── (d) only now the heavy imports ─────────────────────────────────────────────────────────────────────────────────────────
import numpy as np                                                                  # noqa: E402
import torch                                                                        # noqa: E402
import torch.nn as nn                                                               # noqa: E402
from scipy.special import erf                                                       # noqa: E402
from scipy.stats import spearmanr                                                   # noqa: E402

t0 = time.time()
ck = torch.load(CK, map_location="cpu", weights_only=False)
sd = ck["state_dict"]
mu = ck["mu"].numpy().astype(np.float64)
sdv = ck["sd"].numpy().astype(np.float64)
alpha = float(ck["alpha"])
W = {"w0": sd["f.0.weight"].numpy(), "b0": sd["f.0.bias"].numpy(),
     "w1": sd["f.3.weight"].numpy(), "b1": sd["f.3.bias"].numpy(),
     "w2": sd["f.6.weight"].numpy(), "b2": sd["f.6.bias"].numpy()}
if not (W["w0"].shape == (256, 171) and W["w2"].shape == (1, 256)):                 # the ancestor's assert, as a refusal
    refuse("unexpected_shapes", {k: list(v.shape) for k, v in W.items()})

TG = np.load(INPUTS["targets"], allow_pickle=True)
data_axis_end = int(TG["E_ts"].astype(np.int64).max())                              # = the ancestor's `trained_through` (FACT 03.10)

# ── (e) V1: np vs torch on real feature rows — computed BEFORE any write ───────────────────────────────────────────────────
FE = np.load(INPUTS["fea82"], allow_pickle=True)
F9 = np.load(INPUTS["fea89"], allow_pickle=True)
rng = np.random.default_rng(0)
sel = rng.choice(FE["X"].shape[0], V1_ROWS, replace=False)
XL = np.concatenate([FE["X"][sel].astype(np.float32), F9["X"][sel].astype(np.float32)], 1)
xz = np.nan_to_num(np.clip((XL - mu) / sdv, -5, 5)).astype(np.float64)


def gelu(x):
    return 0.5 * x * (1 + erf(x / np.sqrt(2)))


h = gelu(xz @ W["w0"].T.astype(np.float64) + W["b0"].astype(np.float64))
h = gelu(h @ W["w1"].T.astype(np.float64) + W["b1"].astype(np.float64))
s_np = (h @ W["w2"].T.astype(np.float64) + W["b2"].astype(np.float64)).squeeze(-1)


class Net(nn.Module):
    def __init__(s, d=171, hh=256, p=0.1):
        super().__init__()
        s.f = nn.Sequential(nn.Linear(d, hh), nn.GELU(), nn.Dropout(p),
                            nn.Linear(hh, hh), nn.GELU(), nn.Dropout(p), nn.Linear(hh, 1))

    def forward(s, x):
        return s.f(x).squeeze(-1)


net = Net()
net.load_state_dict({k: v for k, v in sd.items() if k.startswith("f.")}, strict=False)
net.eval()
with torch.no_grad():
    s_t = net(torch.from_numpy(xz.astype(np.float32))).numpy().astype(np.float64)
rho = float(spearmanr(s_np, s_t).correlation)
mx = float(np.abs(s_np - s_t).max())
v1_ok = bool(rho >= V1_RHO and mx <= V1_MAX)
print(f"V1 s{SEED}: spearman {rho:.7f} maxabs {mx:.2e} (criterion >={V1_RHO}, <={V1_MAX}) -> {'PASS' if v1_ok else 'FAIL'}", flush=True)

ARRS = {**W, "mu": mu.astype(np.float32), "sd_": sdv.astype(np.float32),
        "alpha": np.float32(alpha), "n_cols": np.int64(171), "trained_through": np.int64(data_axis_end)}
res = {"PASS": False, "wrote_npz": False, "generation": GENERATION, "seed": SEED, "legacy_compare_mode": LEGACY,
       "V1": {"spearman": rho, "maxabs": mx, "rows": V1_ROWS, "criterion_rho": V1_RHO, "criterion_maxabs": V1_MAX, "ok": v1_ok},
       "pt": CK, "pt_sha256": sha256_file(CK), "data_axis_end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(data_axis_end)),
       "wall_s": round(time.time() - t0, 1), "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

# ── (f) legacy compare mode: never writes, whatever the verdict ────────────────────────────────────────────────────────────
if LEGACY:
    Z = np.load(COMPARE, allow_pickle=True)
    cmp_ = {}
    for k, v in ARRS.items():
        if k not in Z.files:
            cmp_[k] = "absent_in_compare_file"
            continue
        a, b = np.asarray(v), np.asarray(Z[k])
        cmp_[k] = {"bitwise_identical": bool(a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()),
                   "dtype": [str(a.dtype), str(b.dtype)], "shape": [list(a.shape), list(b.shape)]}
    extra = [k for k in Z.files if k not in ARRS]
    res["compare"] = {"file": COMPARE, "file_sha256": sha256_file(COMPARE), "per_key": cmp_,
                      "keys_only_in_compare_file": extra,
                      "all_bitwise_identical": all(isinstance(c, dict) and c["bitwise_identical"] for c in cmp_.values())}
    res["PASS"] = bool(v1_ok and res["compare"]["all_bitwise_identical"])
    print("NP_EXPORT_LEGACY_COMPARE " + json.dumps({"all_bitwise_identical": res["compare"]["all_bitwise_identical"],
                                                    "extra_keys": extra, "V1": v1_ok}), flush=True)
    print("NP_EXPORT_NO_WRITE (legacy compare mode never writes an npz)", flush=True)
    finalize("F10_NP_EXPORT", res, RECEIPT, INPUTS)

# ── (g) verdict decides the write ──────────────────────────────────────────────────────────────────────────────────────────
if not v1_ok:
    print(f"V1_FAIL s{SEED}: NOTHING WRITTEN (the ancestor wrote the npz before this line and exited 3 with a complete "
          f"deployable file on disk)", flush=True)
    res["REFUSED"] = {"why": "V1_FAIL", "spearman": rho, "maxabs": mx}
    finalize("F10_NP_EXPORT", res, RECEIPT, INPUTS)

META = {"trained_through_meaning": "data axis end = max(E_ts) of the targets file; NOT the training pool end and NOT the last "
                                   "loss label (FACT_TABLE_TRN 03.10) — kept only so existing readers do not break",
        "data_axis_end_utc": res["data_axis_end_utc"], "generation": GENERATION, "seed": str(SEED),
        "pt_sha256": res["pt_sha256"], "best_ep_rule": BEST_EP_RULE,
        "self_sha256": sha256_file(os.path.abspath(__file__)), "built_utc": res["built_utc"]}
for k in ("trained_through_label_utc", "trained_through_pool_end_utc", "trained_through_tr1_end_utc", "best_ep_kept",
          "validation_span_utc", "refit_self_sha256"):
    if k == "refit_self_sha256":
        META[k] = str(side.get("self_sha256"))
    elif k in side:
        META[k] = json.dumps(side[k]) if isinstance(side[k], (list, dict)) else str(side[k])

os.makedirs(os.path.dirname(os.path.abspath(NP_OUT)), exist_ok=True)
tmp = NP_OUT + ".tmp"
np.savez(tmp, **ARRS, **{k: np.array(v) for k, v in META.items()})
os.replace(tmp, NP_OUT)
res["PASS"] = True
res["wrote_npz"] = True
res["npz_sha256"] = sha256_file(NP_OUT)
res["npz_keys"] = sorted(list(ARRS) + list(META))
res["metadata"] = META
INPUTS["npz"] = NP_OUT
print(f"V1_PASS s{SEED} -> {NP_OUT} sha {res['npz_sha256'][:12]} generation {GENERATION} "
      f"label cutoff {META.get('trained_through_label_utc')} (axis end {res['data_axis_end_utc']})", flush=True)
print("NP_EXPORT_DONE " + json.dumps({"npz": NP_OUT, "sha256": res["npz_sha256"][:16], "V1": res["V1"]}), flush=True)
finalize("F10_NP_EXPORT", res, RECEIPT, INPUTS)
