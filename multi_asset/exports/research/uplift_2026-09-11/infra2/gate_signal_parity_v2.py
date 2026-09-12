"""gate_signal_parity_v2.py — S_BITWISE_signal gate as a BOUND RECEIPT (companion of v4e_gate_export_v2 E7; r20, 2026-09-12).

Same statistic as gate_signal_parity.py (sha 19b7419f…): the injected PARITY matrix must re-rank to the device's own fund z
BITWISE on every panel row (RZ == xz row-wise), and the round-1 ORDINAL builder must FAIL the same test — a gate that cannot fail is
not a gate. What v1 lacked (reviewer §1 row 1): a gate-source sha, the arm, the FEMAT it validated, and recorded thresholds, so the
export gate could only read the word PASS. v2 writes through v4_gate_common.finalize: {gate, arm, self_sha256, inputs_sha256{export_panel,
femat}, stats, thresholds, PASS}. The export gate re-derives PASS from stats vs thresholds and demands thresholds == the contract's.

ENV (explicit): SIG_PANEL (the panel the DEVICE reads for f_fund_ema_v1) SIG_FEMAT (the injected matrix npz: symbols, ts, mat)
                SIG_ARM V4CHAIN_DIR SIGGATE_OUT
Exit 0 iff PASS, else 3.
"""
import os, sys, json
import numpy as np
from scipy.stats import rankdata

REQ = ["SIG_PANEL", "SIG_FEMAT", "SIG_ARM", "V4CHAIN_DIR", "SIGGATE_OUT"]
E = {}
for k in REQ:
    v = os.environ.get(k)
    if not v: print(f"SIGNAL_GATE_REFUSED: env {k} not set", flush=True); sys.exit(2)
    E[k] = v
sys.path.insert(0, E["V4CHAIN_DIR"])
from v4_gate_common import finalize  # noqa: E402

THRESHOLDS = {"NEW_rankdata_rows_failing_rerank_identity_max": 0, "OLD_argsort_rows_failing_rerank_identity_min": 1,
              "NEW_float32_roundtrip_rows_failing_max": 0, "femat_ts_aligned": True, "femat_symbols_aligned": True, "rows_min": 1}


def xz(v):
    """VERBATIM from w10_health.py L122-125 (the device's cross-sectional rank)."""
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out


def RZ(M, mask=None):
    M = np.asarray(M, float)
    if mask is not None: M = np.where(mask, M, np.nan)
    out = np.full(M.shape, np.nan)
    for i in range(M.shape[0]): out[i] = xz(M[i])
    return out


def rz_old(M):
    out = np.full(M.shape, np.nan)
    for i in range(M.shape[0]):
        v = M[i]; ok = np.isfinite(v); n = ok.sum()
        if n >= 10: out[i, ok] = np.argsort(np.argsort(v[ok])) / max(n - 1, 1) - 0.5
    return out


def eq(a, b):
    na = np.isnan(a); nb = np.isnan(b)
    return np.array_equal(na, nb) and np.array_equal(a[~na], b[~nb])


PW = np.load(E["SIG_PANEL"], allow_pickle=True)
FE1 = np.asarray(PW["f_fund_ema_v1"], float); B = np.isfinite(FE1)
ZF_new = RZ(FE1, B); ZF_old = rz_old(np.where(B, FE1, np.nan))


def rerank_fail_rows(Z, cast=None):
    bad = []
    for i in range(Z.shape[0]):
        z = Z[i] if cast is None else Z[i].astype(cast).astype(np.float64)
        if not eq(xz(z), xz(FE1[i])): bad.append(i)
    return bad


bn = rerank_fail_rows(ZF_new); bo = rerank_fail_rows(ZF_old); b32 = rerank_fail_rows(ZF_new, np.float32)
FZ = np.load(E["SIG_FEMAT"], allow_pickle=True)
ts_ok = np.array_equal(np.asarray(FZ["ts"]).astype(np.int64), np.asarray(PW["ts"]).astype(np.int64))
sym_ok = [str(x) for x in FZ["symbols"]] == [str(x) for x in PW["symbols"]]
mat = np.asarray(FZ["mat"], float)
stats = {"rows": int(FE1.shape[0]), "NEW_rankdata_rows_failing_rerank_identity": len(bn), "OLD_argsort_rows_failing_rerank_identity": len(bo),
         "NEW_float32_roundtrip_rows_failing": len(b32), "femat_ts_aligned": bool(ts_ok), "femat_symbols_aligned": bool(sym_ok),
         "femat_shape": list(mat.shape), "femat_finite_frac": float(np.isfinite(mat).mean())}
PASS = (stats["NEW_rankdata_rows_failing_rerank_identity"] <= THRESHOLDS["NEW_rankdata_rows_failing_rerank_identity_max"]
        and stats["OLD_argsort_rows_failing_rerank_identity"] >= THRESHOLDS["OLD_argsort_rows_failing_rerank_identity_min"]
        and stats["NEW_float32_roundtrip_rows_failing"] <= THRESHOLDS["NEW_float32_roundtrip_rows_failing_max"]
        and stats["femat_ts_aligned"] == THRESHOLDS["femat_ts_aligned"] and stats["femat_symbols_aligned"] == THRESHOLDS["femat_symbols_aligned"]
        and stats["rows"] >= THRESHOLDS["rows_min"])
R = {"arm": E["SIG_ARM"], "env": E, "stats": stats, "thresholds": THRESHOLDS, "NEW_first_bad": bn[:5], "OLD_first_bad": bo[:5], "PASS": bool(PASS),
     "gate_version": "v2 (r20, bound receipt)"}
print(json.dumps({k: R[k] for k in ("arm", "stats", "PASS")}, indent=1), flush=True)
finalize("S_BITWISE_signal", R, E["SIGGATE_OUT"], {"export_panel": E["SIG_PANEL"], "femat": E["SIG_FEMAT"]})
